from __future__ import annotations

from fractions import Fraction
import hashlib
import inspect
import math

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.physics_v025.calibration import (
    CalibrationObservation,
    NominalConfiguration,
    assert_calibration_prices,
    freeze_setting_calibration,
    nominal_greedy_reference,
)
from mcrl.physics_v025.channel import (
    interference_receive_gain_linear,
    keyed_fading_gain,
    receive_gain_dbi,
    shadow_sigma_db,
)
from mcrl.physics_v025.integration import (
    BoundarySample,
    integrate_47_subintervals,
    snapshot_left,
)
from mcrl.physics_v025.matrix import MATRIX_SETTINGS
from mcrl.physics_v025.state_v025 import (
    C2ActionState,
    ForecastOffsetState,
    SCHEMA_SHA256,
    STATE_SHAPE,
    encode_c2_state,
    schema_manifest,
)
from mcrl.physics_v025.tapes import (
    CALIBRATION_WORLD_DOMAINS,
    PROBE_WORLD_DOMAINS,
    REFERENCE_CARRIERS,
    TinySyntheticProvider,
    build_world_tape,
    corrected_boundary_rekey_rate,
    seed_from_domain,
)
from mcrl.physics_v025.targets import (
    NetworkOutcome,
    OffsetProjection,
    assert_reward_core_identity,
    c1_difference_surplus,
    c2_persistence_forecast,
    c3_lcsrs_interaction,
    classify_physical_transition,
    network_objective,
    project_three_offsets,
)
from mcrl.physics_v025.endpoint import StepEndpoint


def _outcome(bits: float, joules: float, *, phi: float = 0.0) -> NetworkOutcome:
    return NetworkOutcome.build(
        bits=bits,
        joules=joules,
        phi=phi,
        decoding_availability=1,
        useful_availability=1,
    )


def _projection(index: int, bits: float, joules: float, *, survives: bool = True) -> OffsetProjection:
    return OffsetProjection(
        index,
        True,
        survives,
        _outcome(bits, joules),
        True,
        1.0,
        1.65,
        3.0,
        1.0,
    )


def test_project_and_calibration_seed_domains_are_exact_and_disjoint() -> None:
    """The seed is the first SHA-256 u64 masked to 63 bits, not RNG state."""

    for domain in PROBE_WORLD_DOMAINS + CALIBRATION_WORLD_DOMAINS:
        expected = int.from_bytes(hashlib.sha256(domain.encode("ascii")).digest()[:8], "big") & ((1 << 63) - 1)
        assert seed_from_domain(domain) == expected
    assert set(PROBE_WORLD_DOMAINS).isdisjoint(CALIBRATION_WORLD_DOMAINS)


def test_tape_has_exact_47_interval_boundaries_and_fixed_manifests() -> None:
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=TinySyntheticProvider(),
        steps=2,
        start_time_s=0.0,
    )
    assert len(tape.steps[0].boundaries) == 48
    assert [row.absolute_time_s for row in tape.steps[0].boundaries] == pytest.approx(
        [index * 0.640 for index in range(48)], abs=1e-12
    )
    assert {row.carrier for row in tape.carriers} == set(REFERENCE_CARRIERS)
    assert tape.manifest()["cluster"] == {
        "tle_date": "synthetic-tle",
        "training_seed": tape.seed,
    }
    assert len(tape.inventory_digest) == len(tape.tape_digest) == len(tape.digest) == 64
    assert all(
        candidate.identity in tape.inventory.chains
        for step in tape.steps
        for boundary in step.boundaries
        for candidate in boundary.candidates
    )


def test_actual_elevation_changes_shadow_statistics_with_same_keys() -> None:
    """Register-B KAT: 10 and 60 deg must not share the legacy 10-deg sigma."""

    assert float(shadow_sigma_db(10.0)) == 1.9
    assert float(shadow_sigma_db(60.0)) == 3.1
    low = [
        10.0 * math.log10(
            keyed_fading_gain(world=7, user=i, norad=99, absolute_time_ns=1, elevation_deg=10.0)
        )
        for i in range(64)
    ]
    high = [
        10.0 * math.log10(
            keyed_fading_gain(world=7, user=i, norad=99, absolute_time_ns=1, elevation_deg=60.0)
        )
        for i in range(64)
    ]
    assert not np.array_equal(low, high)
    assert np.std(high) > np.std(low)


def test_s465_three_angles_match_independent_piecewise_formula() -> None:
    """Register-B KAT independent of the historical receive helper."""

    theta_min = 2.043298703
    angles = np.array([1.0, theta_min, 5.0])
    expected = np.array(
        [
            min(35.0, max(-10.0, 32.0 - 25.0 * math.log10(angle)))
            for angle in angles
        ]
    )
    assert receive_gain_dbi(angles) == pytest.approx(expected, abs=1e-12)
    interference = interference_receive_gain_linear(
        angles,
        same_satellite=np.array([False, False, False]),
    )
    assert 10.0 * np.log10(interference) == pytest.approx(expected, abs=1e-12)
    assert float(interference_receive_gain_linear(5.0, same_satellite=True)) == pytest.approx(
        10.0**3.5
    )


def test_power_and_bits_trapezoids_match_linear_closed_forms() -> None:
    """Register-A KAT: integrate both fields, never snapshot-times-duration."""

    points = []
    for index in range(48):
        time_s = index * 0.640
        points.append(
            BoundarySample(time_s, {0: 2.0 + 3.0 * time_s}, 5.0 + 0.25 * time_s, {0: True})
        )
    result = integrate_47_subintervals(points)
    duration = 30.08
    assert result.bits[0] == pytest.approx(2.0 * duration + 1.5 * duration**2)
    assert result.joules == pytest.approx(5.0 * duration + 0.125 * duration**2)
    left = snapshot_left(points[0], end_s=duration)
    assert left.bits[0] == pytest.approx(2.0 * duration)
    assert left.joules == pytest.approx(5.0 * duration)


def test_nominal_greedy_and_calibration_are_deterministic_per_setting() -> None:
    rows = (
        NominalConfiguration("b", ((0, (1, 1)),), 10.0, 2.0, 1),
        NominalConfiguration("a", ((0, (2, 1)),), 10.0, 1.0, 1),
    )
    assert nominal_greedy_reference(rows).configuration_id == "a"
    setting = MATRIX_SETTINGS[0]
    observations = tuple(
        CalibrationObservation.build(
            world_domain=domain,
            bits=100,
            joules=10,
            users=2,
            time_s=5,
            selected_configuration_id="a",
        )
        for domain in CALIBRATION_WORLD_DOMAINS
    )
    frozen = freeze_setting_calibration(setting=setting, observations=observations)
    assert frozen.eta_ref == frozen.lambda_bits_per_j == 10
    assert frozen.kappa_bits_per_user_s == 10
    assert freeze_setting_calibration(setting=setting, observations=observations).digest == frozen.digest


@pytest.mark.parametrize(
    "producer",
    [
        network_objective,
        c1_difference_surplus,
        c2_persistence_forecast,
        c3_lcsrs_interaction,
        project_three_offsets,
        assert_reward_core_identity,
        encode_c2_state,
    ],
)
def test_every_downstream_producer_has_no_default_energy_price(producer) -> None:
    signature = inspect.signature(producer)
    for name in ("lambda_bits_per_j", "eta_ref", "kappa_bits_per_user_s"):
        assert name in signature.parameters
        assert signature.parameters[name].default is inspect.Parameter.empty


def test_explicit_prices_fail_closed_on_missing_or_mismatch() -> None:
    with pytest.raises(TypeError):
        network_objective(_outcome(10, 1))
    with pytest.raises(MCRLContractError):
        assert_calibration_prices(lambda_bits_per_j=9, eta_ref=10, kappa_bits_per_user_s=1)


def test_c1_is_whole_network_difference_plus_explicit_phi() -> None:
    """Focal +1/nonfocal -10 is network -9, never a focal-only +1 label."""

    default = NetworkOutcome.build(
        bits=20,
        joules=2,
        phi=0,
        decoding_availability=1,
        useful_availability=1,
        per_user_bits={0: 10, 1: 10},
    )
    candidate = NetworkOutcome.build(
        bits=11,
        joules=2,
        phi=-0.5,
        decoding_availability=1,
        useful_availability=1,
        per_user_bits={0: 11, 1: 0},
    )
    label = c1_difference_surplus(
        candidate,
        default,
        lambda_bits_per_j=5,
        eta_ref=5,
        kappa_bits_per_user_s=1,
    )
    assert label.difference_surplus_bits == -9
    assert label.phi_difference == Fraction(-1, 2)
    assert label.normalized_total == Fraction(-19, 2)


def test_c2_charges_failed_attempt_then_applies_absorbing_three_offset_penalty() -> None:
    candidate = (
        _projection(1, 5, 2, survives=False),
        _projection(2, 100, 1),
        _projection(3, 100, 1),
    )
    default = tuple(_projection(index, 10, 1) for index in range(1, 4))
    label = c2_persistence_forecast(
        candidate,
        default,
        lambda_bits_per_j=2,
        eta_ref=2,
        kappa_bits_per_user_s=3,
    )
    assert label.forecast_surplus_bits == -7  # failed offset retains its +1 J attempt
    assert label.lost_offsets == 3
    assert label.persistence_penalty_bits == 9
    assert label.normalized_total == Fraction(-16, 3)


def test_c3_uses_declared_network_interaction_and_equal_split() -> None:
    interaction = c3_lcsrs_interaction(
        coalition_users=(0, 1),
        f00=_outcome(10, 1),
        f10=_outcome(14, 1),
        f01=_outcome(13, 1),
        f11=_outcome(22, 1),
        externality_e_by_user={0: 2, 1: -1},
        lambda_bits_per_j=5,
        eta_ref=5,
        kappa_bits_per_user_s=3,
    )
    # Energy cancels: Psi = 22 - 14 - 13 + 10 = 5.
    assert interaction.psi == 5
    assert dict(interaction.z3_by_user) == {0: Fraction(5, 2), 1: Fraction(5, 2)}


def test_reward_core_identity_is_exact() -> None:
    rows = [
        StepEndpoint.build(
            bits=bits,
            joules=joules,
            decoding_user_seconds=1,
            useful_user_seconds=1,
            opportunity_user_seconds=1,
            complete_service_user_steps=1,
            user_steps=1,
        )
        for bits, joules in ((10, 1), (20, 3))
    ]
    assert assert_reward_core_identity(
        rows,
        lambda_bits_per_j=4,
        eta_ref=4,
        kappa_bits_per_user_s=2,
    ) == 14


def test_c2_schema_has_new_features_frozen_shape_and_price_binding() -> None:
    manifest = schema_manifest()
    encoded = encode_c2_state(
        C2ActionState(
            3.0,
            -0.01,
            60.0,
            90.0,
            2,
            4,
            True,
            True,
            0.4,
            tuple(ForecastOffsetState(True, True, 2.0 - i, 1.2) for i in range(3)),
        ),
        architecture="a-r",
        lambda_bits_per_j=10,
        eta_ref=10,
        kappa_bits_per_user_s=3,
    )
    assert STATE_SHAPE == (21,)
    assert len(encoded.values) == 21
    assert encoded.schema_sha256 == SCHEMA_SHA256 == manifest["schema_sha256"]
    serialized = str(manifest["action_features"])
    assert "incumbent_nominal_decoding_margin" in serialized
    assert "previous_recurrence_power" not in serialized


def test_transition_ledger_uses_norad_and_chain_not_cell_slot() -> None:
    assert classify_physical_transition(
        user_id=0, before=(10, 1), after=(10, 2), cell_rekey=False, was_previously_served=True
    ).kind == "beam_change"
    assert classify_physical_transition(
        user_id=0, before=(10, 1), after=(11, 1), cell_rekey=False, was_previously_served=True
    ).kind == "satellite_change"
    assert classify_physical_transition(
        user_id=0, before=(10, 1), after=(10, 1), cell_rekey=True, was_previously_served=True
    ).kind == "cell_rekey"
    assert corrected_boundary_rekey_rate(rekeys=2, eligible_boundaries=4) == 0.5
