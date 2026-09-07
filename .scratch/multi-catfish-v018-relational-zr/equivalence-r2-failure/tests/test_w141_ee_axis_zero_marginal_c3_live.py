"""W-141 -- live current-slot measurements for V0.12 zero-energy C3."""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_zero_marginal_c3_live import (
    CurrentPhysicsSignature,
    measure_zero_marginal_c3,
)
from mcrl.runtime.ee_axis_zero_marginal_c3 import (
    assert_surface_identity,
    build_hr_surface,
    build_zr_surface,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _signature() -> CurrentPhysicsSignature:
    return CurrentPhysicsSignature(
        served_users=np.asarray([True, True, False], dtype=np.bool_),
        active_beam_keys=np.asarray([[11, 2], [12, 3]], dtype=np.int64),
        active_satellites=np.asarray([11, 12], dtype=np.int64),
        beam_power_w=np.asarray([0.825, 1.0], dtype=np.float64),
        system_power_w=123.0,
    )


def test_signature_compatibility_is_bit_exact_for_every_component() -> None:
    reference = _signature()
    assert reference.bit_exact_equal(_signature())
    assert reference.sha256 == _signature().sha256

    cases = (
        CurrentPhysicsSignature(
            served_users=np.asarray([True, False, False], dtype=np.bool_),
            active_beam_keys=reference.active_beam_keys,
            active_satellites=reference.active_satellites,
            beam_power_w=reference.beam_power_w,
            system_power_w=reference.system_power_w,
        ),
        CurrentPhysicsSignature(
            served_users=reference.served_users,
            active_beam_keys=np.asarray([[11, 2], [12, 4]], dtype=np.int64),
            active_satellites=reference.active_satellites,
            beam_power_w=reference.beam_power_w,
            system_power_w=reference.system_power_w,
        ),
        CurrentPhysicsSignature(
            served_users=reference.served_users,
            active_beam_keys=np.asarray([[11, 2], [13, 3]], dtype=np.int64),
            active_satellites=np.asarray([11, 13], dtype=np.int64),
            beam_power_w=reference.beam_power_w,
            system_power_w=reference.system_power_w,
        ),
        CurrentPhysicsSignature(
            served_users=reference.served_users,
            active_beam_keys=reference.active_beam_keys,
            active_satellites=reference.active_satellites,
            beam_power_w=np.asarray(
                [np.nextafter(0.825, np.inf), 1.0], dtype=np.float64
            ),
            system_power_w=reference.system_power_w,
        ),
        CurrentPhysicsSignature(
            served_users=reference.served_users,
            active_beam_keys=reference.active_beam_keys,
            active_satellites=reference.active_satellites,
            beam_power_w=reference.beam_power_w,
            system_power_w=np.nextafter(reference.system_power_w, np.inf),
        ),
    )
    assert all(not reference.bit_exact_equal(value) for value in cases)


def _environment(users: int = 3) -> StepEnvironment:
    return StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=users)),
        ),
        fading_field=KeyedFadingField.from_components(
            "test-w141-v012-zero-energy-c3", "b" * 64, users
        ),
    )


def _state(environment: StepEnvironment) -> tuple[object, ...]:
    radiating = environment._previous_radiating
    tracker = getattr(environment.driver, "_tracker", None)
    return (
        environment._step_index,
        environment.driver.step_index,
        tuple(environment._segments),
        repr(copy.deepcopy(environment._pending_segment_age)),
        tuple(environment._previous_association),
        environment._previous_link_power_w.tobytes(order="C"),
        environment._previous_served_rate_bps.tobytes(order="C"),
        environment.driver.user_ecef_km().tobytes(order="C"),
        repr(copy.deepcopy(environment._previous_demand)),
        tuple(ledger.previous for ledger in environment._ledgers),
        radiating.norad_ids.tobytes(order="C"),
        radiating.cell_ids.tobytes(order="C"),
        radiating.power_w.tobytes(order="C"),
        id(environment._candidates),
        environment.driver._start_utc,
        repr(copy.deepcopy(tracker.__dict__)) if tracker is not None else None,
    )


@requires_archive
@pytest.mark.parametrize("include_insertion", [False, True])
def test_live_measurement_is_focal_only_masked_and_state_neutral(
    include_insertion: bool,
) -> None:
    environment = _environment()
    rng = np.random.default_rng(2026090301)
    observation = environment.reset(START, rng)
    assert np.all(np.any(observation.masks, axis=1))
    reference = np.asarray(
        [int(np.flatnonzero(row)[0]) for row in observation.masks],
        dtype=np.int64,
    )
    state_before = _state(environment)
    rng_before = copy.deepcopy(rng.bit_generator.state)

    measured = measure_zero_marginal_c3(
        environment,
        observation=observation,
        reference_actions=reference,
        rng=rng,
        include_insertion=include_insertion,
    )

    state_after = _state(environment)
    assert state_before == state_after
    assert rng.bit_generator.state == rng_before
    assert measured.reference_actions.tolist() == reference.tolist()
    assert measured.legal_mask.shape == (3, 28)
    assert measured.reference_rate_bps.shape == (3, 3)
    assert measured.candidate_rate_bps.shape == (3, 28, 3)
    assert measured.replacement_delta_bits.shape == (3, 28, 3)
    assert np.all(measured.replacement_delta_bits[~measured.legal_mask] == 0.0)
    assert not np.any(measured.compatible[~measured.legal_mask])
    for uid, action in enumerate(reference.tolist()):
        assert np.all(measured.replacement_delta_bits[uid, action] == 0.0)
        assert bool(measured.compatible[uid, action])
        assert bool(measured.served_equal[uid, action])
        assert bool(measured.active_beams_equal[uid, action])
        assert bool(measured.active_satellites_equal[uid, action])
        assert bool(measured.rf_power_equal[uid, action])
        assert bool(measured.network_power_equal[uid, action])
        assert np.all(measured.replacement_delta_bits[uid, :, uid] == 0.0)
        assert measured.reference_rate_bps[uid, uid] == 0.0
        assert np.all(measured.candidate_rate_bps[uid, :, uid] == 0.0)
    expected = 1 + int(np.count_nonzero(observation.masks)) - 3
    if include_insertion:
        expected += 3
        assert measured.insertion_delta_bits is not None
        assert measured.removed_rate_bps is not None
        for uid in range(3):
            assert np.all(measured.insertion_delta_bits[uid, :, uid] == 0.0)
            assert measured.removed_rate_bps[uid, uid] == 0.0
    else:
        assert measured.insertion_delta_bits is None
        assert measured.removed_rate_bps is None
    assert measured.counterfactual_evaluations == expected
    assert not measured.reference_actions.flags.writeable
    assert not measured.reference_rate_bps.flags.writeable
    assert not measured.candidate_rate_bps.flags.writeable
    assert not measured.replacement_delta_bits.flags.writeable
    assert not measured.compatible.flags.writeable

    surfaces = []
    for uid, action in enumerate(reference.tolist()):
        if include_insertion:
            assert measured.removed_rate_bps is not None
            surface = build_hr_surface(
                baseline_rate_bps=measured.removed_rate_bps[uid],
                candidate_rate_bps=measured.candidate_rate_bps[uid],
                compatibility=measured.compatible[uid],
                legal_mask=measured.legal_mask[uid],
                reference_action=action,
                interval_s=30.08,
                kappa_bits=1.0,
            )
        else:
            surface = build_zr_surface(
                baseline_rate_bps=measured.reference_rate_bps[uid],
                candidate_rate_bps=measured.candidate_rate_bps[uid],
                compatibility=measured.compatible[uid],
                legal_mask=measured.legal_mask[uid],
                reference_action=action,
                interval_s=30.08,
                kappa_bits=1.0,
            )
        surfaces.append(surface)
        assert_surface_identity(surface)
        assert surface.q3_values[action] == 0.0
        assert np.all(surface.q3_values[(~measured.compatible[uid]) & measured.legal_mask[uid]] <= 0.0)
    assert len(surfaces) == 3
