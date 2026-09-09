"""Independent KATs for the stage-4d real-anchor gate decisions."""

from __future__ import annotations

import copy
from dataclasses import replace
from fractions import Fraction
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.physics_v025.acm import rate_target_sinr
from mcrl.physics_v025.adapter import build_shared_tape, score_setting
import mcrl.physics_v025.adapter as adapter_module
from mcrl.physics_v025.architectures import (
    AngleRateTPC_TDM,
    Geometry,
    Link,
    RadiationConfig,
)
from mcrl.physics_v025.batch import evaluate_ar_tdm_catalogue
import mcrl.physics_v025.batch as batch_module
import mcrl.physics_v025.resolution as resolution_module
from mcrl.physics_v025.calibration import CalibrationValues
from mcrl.physics_v025.channel import noise_power_w
from mcrl.physics_v025.constants_v025 import BEAM_BANDWIDTH_HZ
from mcrl.physics_v025.energy import HardwareInventory
from mcrl.physics_v025.matrix import MATRIX_SETTINGS, run_setting_for
from mcrl.physics_v025.tapes import (
    CALIBRATION_WORLD_DOMAINS,
    KAT_WORLD_DOMAINS,
    PrimitiveStepArrays,
    TinySyntheticProvider,
    build_world_tape,
)
from mcrl.physics_v025.targets import NetworkOutcome, set_score_decomposition


REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"


def _load_runner(name: str):
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _outcome(value: int) -> NetworkOutcome:
    return NetworkOutcome.build(
        bits=100 + value,
        joules=100,
        phi=0,
        decoding_availability=1,
        useful_availability=1,
    )


def _three_user_arrays(rho: float, base_power_w: float) -> tuple[PrimitiveStepArrays, Geometry]:
    users = 3
    gamma = float(rate_target_sinr(50_000_000.0, BEAM_BANDWIDTH_HZ, 1))
    noise = noise_power_w(BEAM_BANDWIDTH_HZ)
    direct = gamma * noise / base_power_w
    cross = direct * rho / (gamma * (users - 1))
    identities = np.asarray([[100 + index, index] for index in range(users)], dtype=np.int64)
    shape = (48, users)
    cross_base = np.full((48, users, users), cross)
    cross_base[:, np.arange(users), np.arange(users)] = 0.0
    arrays = PrimitiveStepArrays(
        np.arange(48) * 0.640,
        np.arange(users, dtype=np.int64),
        np.arange(users, dtype=np.int64),
        np.arange(users, dtype=np.int64),
        identities,
        np.zeros(users, dtype=np.int64),
        np.full(shape, 45.0),
        np.full(shape, 20.0),
        np.full(shape, 1000.0),
        np.full(shape, 1000.0),
        np.ones(shape, dtype=bool),
        np.ones(shape, dtype=bool),
        np.ones(shape, dtype=bool),
        np.full(shape, direct),
        np.full(shape, direct),
        np.full(shape, 999.0),
        np.full(shape, 999.0),
        np.zeros(shape, dtype=bool),
        np.zeros(shape, dtype=bool),
        identities,
        np.zeros(users, dtype=np.int64),
        np.arange(users, dtype=np.int64),
        np.zeros(users, dtype=np.int64),
        cross_base,
        np.ones((48, users, users)),
        np.ones((48, users, 1, users)),
    )
    cross_matrix = np.full((users, users), cross)
    np.fill_diagonal(cross_matrix, 0.0)
    geometry = Geometry(
        tuple(
            Link(index, tuple(int(value) for value in identities[index]), 0, direct, direct)
            for index in range(users)
        ),
        cross_matrix,
    )
    return arrays, geometry


def test_large_set_decomposition_is_linear_and_has_no_credit_split() -> None:
    users = tuple(range(6))
    outcomes = {frozenset(): _outcome(0), frozenset(users): _outcome(40)}
    outcomes.update({frozenset((user,)): _outcome(user + 1) for user in users})
    result = set_score_decomposition(
        coalition_users=users,
        outcomes_by_subset=outcomes,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=1,
    )
    assert len(outcomes) == len(users) + 2
    assert dict(result.d_by_user) == {user: user + 1 for user in users}
    assert result.interaction_bits == 19
    assert result.shapley_interaction_by_user == ()
    assert result.credit_split == "NOT_COMPUTED_LARGE_SET"


def test_small_set_shapley_is_reporting_only_and_exact() -> None:
    values = {
        frozenset(): 0,
        frozenset({0}): 2,
        frozenset({1}): 3,
        frozenset({0, 1}): 9,
    }
    result = set_score_decomposition(
        coalition_users=(0, 1),
        outcomes_by_subset={key: _outcome(value) for key, value in values.items()},
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=1,
    )
    assert result.interaction_bits == 4
    assert dict(result.shapley_interaction_by_user) == {0: 2, 1: 2}
    assert result.credit_split == "EXACT_SHAPLEY_SMALL_SET"


def test_full_48_boundary_endpoint_matches_frozen_stage4b_bits() -> None:
    arrays, _geometry = _three_user_arrays(0.8, 1.0e-4)
    result = evaluate_ar_tdm_catalogue(
        arrays,
        np.asarray([[0, 1, 2]]),
        field="nominal",
        boundary_indices=tuple(range(48)),
    )
    assert float(result.bits.sum()).hex() == "0x0.0p+0"
    assert float(result.joules[0]).hex() == "0x1.edbf06821a358p+5"


def test_batch_and_scalar_slow_certificates_agree(monkeypatch: pytest.MonkeyPatch) -> None:
    arrays, geometry = _three_user_arrays(0.999, 1.0e-7)
    monkeypatch.setattr(batch_module, "POWER_SOLVER_ITERATION_CAP", 1000)
    batch = evaluate_ar_tdm_catalogue(
        arrays,
        np.asarray([[0, 1, 2]]),
        field="nominal",
        boundary_indices=(0,),
    )
    scalar = AngleRateTPC_TDM().radiate(
        RadiationConfig(solver_iteration_cap=1000, rate_target_bps=50_000_000.0),
        geometry,
        "nominal",
    )
    scalar_power = max(tx.rf_power_w for tx in scalar.slots[0].transmissions)
    assert scalar.certificate.status == "CONVERGED_SLOW"
    assert int(batch.certificate_status[0]) == 2
    assert float(batch.max_rf_power_w[0]) == pytest.approx(scalar_power, abs=1.0e-9)


def test_two_stage_top_m_reports_agreement_and_miss() -> None:
    runner = _load_runner("v025_stage4d_top_m")
    catalog = [runner.Configuration(f"c{i:02d}", ((0, None),), 0, "kat") for i in range(70)]
    factors = {
        row.configuration_id: {
            "C1": Fraction(100 - index),
            "C2": Fraction(200 if index == 60 else 0),
            "C3": Fraction(),
        }
        for index, row in enumerate(catalog)
    }
    shortlist, diagnostic = runner._stage2_shortlist(
        catalog=catalog,
        factors=factors,
        mandatory_ids={"c00"},
    )
    assert len(shortlist) == 64
    shortlist_result = runner._stage2_top1_diagnostic(
        stage1_top1_configuration=diagnostic["stage1_top1_configuration"],
        stage2_catalog=shortlist,
        factors=factors,
    )
    assert shortlist_result["stage2_top1_configuration"] == "c60"
    assert shortlist_result["stage1_stage2_top1_agree"] is False
    factors["c69"]["C2"] = Fraction(1000)
    full_result = runner._stage2_top1_diagnostic(
        stage1_top1_configuration=diagnostic["stage1_top1_configuration"],
        stage2_catalog=catalog,
        factors=factors,
    )
    missed_result = runner._stage2_top1_diagnostic(
        stage1_top1_configuration=diagnostic["stage1_top1_configuration"],
        stage2_catalog=shortlist,
        factors=factors,
    )
    assert full_result["stage2_top1_configuration"] == "c69"
    assert missed_result["stage2_top1_configuration"] == "c60"
    assert "c69" not in {row.configuration_id for row in shortlist}


def test_stage1_is_k0_stage2_is_five_boundaries_and_rows_are_bounded() -> None:
    runner = _load_runner("v025_stage4d_grid")
    run = run_setting_for("a-r0")
    tape = build_world_tape(
        domain=KAT_WORLD_DOMAINS[0],
        provider=TinySyntheticProvider(),
        steps=4,
        start_time_s=0.0,
    )
    eta = Fraction("16499883.12374797")
    kappa = Fraction("1071565931.2278317")
    bits = kappa * 100 * 5
    calibration = CalibrationValues(
        "a-r0", run.digest, eta, eta, kappa, bits, bits / eta, 100, 5,
        Fraction("150.4"), CALIBRATION_WORLD_DOMAINS, ("kat-1", "kat-2"),
    )
    row = runner.execute_step(
        tape=tape,
        setting=runner._setting("a-r0"),
        step_index=0,
        carrier="nearest-eligible",
        calibration=calibration,
        counter=runner.EvaluationCounter(),
        run_setting=run,
    )
    approximation = row["selection_approximations"]
    assert approximation["stage1_boundary_indices"] == [0]
    assert approximation["selection_boundary_indices"] == [0, 12, 24, 36, 47]
    assert row["phase_seconds"]["catalogue_row_count"] == row["e1_certificate"]["candidate_count"]
    assert row["e1_certificate"]["candidate_count"] <= 1500
    assert isinstance(approximation["stage1_stage2_top1_agree"], bool)


def test_s_uni_searches_full_legal_set_and_receipts_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner("v025_stage4d_s_uni")
    base = runner.Configuration("BASE", ((0, None),), 0, "reference")
    legal = tuple((100 + index, 1) for index in range(9))
    monkeypatch.setattr(
        runner,
        "_legal_options",
        lambda _tape, _step: ({0: legal}, {"full_successor_legal_count": 9}),
    )

    class Evaluator:
        def evaluate_many(self, _configs):
            return None

        def evaluate(self, config):
            identity = config.mapping[0]
            value = 0 if identity is None else identity[0] - 99
            outcome = _outcome(value)
            return SimpleNamespace(
                score=SimpleNamespace(served_phy={0: True}),
                outcome=lambda: outcome,
            )

    calibration = SimpleNamespace(
        lambda_bits_per_j=Fraction(1),
        eta_ref=Fraction(1),
        kappa_bits_per_user_step=Fraction(1),
    )
    selected, iterations, _wall, missed, certificate = runner._s_uni_select(
        base=base,
        incumbent=base,
        tape=object(),
        step_index=0,
        evaluator=Evaluator(),
        calibration=calibration,
        compute_budget_s=1.0,
        run_setting=run_setting_for("a-r0"),
    )
    assert selected.mapping[0] == legal[-1]
    assert iterations == 1
    assert missed is False
    assert certificate == "NO_IMPROVING_LEGAL_UNILATERAL"


def test_s_uni_uses_incumbent_relative_phi_in_k0_objective(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_runner("v025_stage4d_s_uni_phi")
    incumbent = runner.Configuration("INC", ((0, (100, 1)),), 0, "reference")
    base = runner.Configuration("BASE", ((0, (100, 1)),), 0, "reference")
    same_satellite = (100, 2)
    other_satellite = (101, 1)
    monkeypatch.setattr(
        runner,
        "_legal_options",
        lambda _tape, _step: (
            {0: (same_satellite, other_satellite)},
            {"full_successor_legal_count": 2},
        ),
    )

    class Evaluator:
        def evaluate_many(self, _configs):
            return None

        def evaluate(self, config):
            identity = config.mapping[0]
            bits = {
                (100, 1): Fraction(0),
                same_satellite: Fraction(1),
                other_satellite: Fraction(5, 4),
            }[identity]
            outcome = _outcome(bits)
            return SimpleNamespace(
                score=SimpleNamespace(served_phy={0: True}),
                outcome=lambda: outcome,
            )

    calibration = SimpleNamespace(
        lambda_bits_per_j=Fraction(1),
        eta_ref=Fraction(1),
        kappa_bits_per_user_step=Fraction(1),
    )
    selected, _iterations, _wall, missed, _certificate = runner._s_uni_select(
        base=base,
        incumbent=incumbent,
        tape=object(),
        step_index=0,
        evaluator=Evaluator(),
        calibration=calibration,
        compute_budget_s=1.0,
        run_setting=run_setting_for("a-r0"),
    )
    assert missed is False
    assert selected.mapping[0] == same_satellite


def test_matched_anchor_ledger_emits_all_five_physical_event_kinds() -> None:
    runner = _load_runner("v025_stage4d_events")
    first_before = runner.Configuration(
        "b0", ((0, None), (1, (1, 1))), 0, "kat"
    )
    first_after = runner.Configuration(
        "a0", ((0, (1, 1)), (1, None)), 2, "kat"
    )
    second_before = runner.Configuration(
        "b1", ((0, (1, 1)), (1, (2, 1))), 0, "kat"
    )
    second_after = runner.Configuration(
        "a1", ((0, (1, 2)), (1, (3, 1))), 2, "kat"
    )
    third = runner.Configuration("b2", ((0, (4, 1)),), 0, "kat")
    kinds = {
        event.kind
        for before, after, rekeys in (
            (first_before, first_after, ()),
            (second_before, second_after, ()),
            (third, third, (0,)),
        )
        for event in runner._physical_events(
            before, after, cell_rekeyed_users=rekeys
        )
    }
    assert kinds == {
        "initial_entry",
        "exit",
        "beam_change",
        "satellite_change",
        "cell_rekey",
    }


def test_reuse_mask_is_reciprocal_and_chain_colour_is_unique() -> None:
    arrays, _geometry = _three_user_arrays(0.5, 1.0e-4)
    fields = {
        name: getattr(arrays, name) for name in arrays.__dataclass_fields__
    }
    fields["colors"] = np.asarray([0, 1, 0])
    fields["aggressor_colors"] = np.asarray([0, 1, 0])
    coloured = PrimitiveStepArrays(**fields)
    geometry = coloured.geometry_at(
        boundary_index=0,
        assignments={0: (100, 0), 1: (101, 1), 2: (102, 2)},
    )
    mask = geometry.nominal_cross_gain > 0.0
    assert np.array_equal(mask, mask.T)
    assert not mask[0, 1] and not mask[1, 0]
    assert mask[0, 2] and mask[2, 0]
    assert len({tuple(identity): int(color) for identity, color in zip(
        coloured.identities, coloured.colors, strict=True
    )}) == 3


def test_zero_legal_user_is_null_in_every_nonbase_catalogue_row() -> None:
    runner = _load_runner("v025_stage4d_zero_legal")
    tape = build_world_tape(
        domain=KAT_WORLD_DOMAINS[1],
        provider=TinySyntheticProvider(),
        steps=1,
        start_time_s=0.0,
    )
    base = runner._base_configuration(tape, 0, "nearest-eligible")
    extra_identities = tuple((90_000 + index, 1) for index in range(12))
    changed_boundaries = []
    for boundary in tape.steps[0].boundaries:
        template = next(row for row in boundary.candidates if row.user_id == 1)
        candidates = tuple(
            replace(row, elevation_deg=0.0, visible=False, d2_eligible=False)
            if row.user_id == 0
            else row
            for row in boundary.candidates
        )
        candidates += tuple(
            replace(template, identity=identity) for identity in extra_identities
        )
        changed_boundaries.append(replace(boundary, candidates=candidates))
    bad_tape = replace(
        tape,
        inventory=HardwareInventory.fixed(
            tuple(tape.inventory.chains) + extra_identities
        ),
        steps=(replace(tape.steps[0], boundaries=tuple(changed_boundaries)),),
    )
    catalog, census = runner._catalogue_with_census(bad_tape, 0, base)
    assert census["null_action_users"] == 1
    assert len(catalog) - 1 >= 11
    assert all(row.mapping[0] is None for row in catalog[1:])


def test_conformance_rejects_opening_dependency_mutation() -> None:
    runner = _load_runner("v025_stage4d_conformance")
    receipt = runner.run_unit(
        setting=runner._setting("a-r0"), world_index=1, executed_steps=1
    )
    runner.assert_matrix_conformance(receipt)
    corrupted = copy.deepcopy(receipt)
    corrupted["steps"][0]["opening_state_certificate"][
        "dependency_allowlist"
    ].append("hidden_reset_age")
    with pytest.raises(runner.ProbeError, match="allowlist"):
        runner.assert_matrix_conformance(corrupted)


def test_reaggregation_rejects_payload_mutation_even_with_rehashed_row() -> None:
    runner = _load_runner("v025_stage4d_reaggregation")
    receipt = runner.run_unit(
        setting=runner._setting("a-r0"), world_index=1, executed_steps=1
    )
    rows = copy.deepcopy(receipt["canonical_step_rows"])
    target = next(row for row in rows if row["arm"] == "FULL")
    target["arm_payload"]["certificate_status"] = "INVALID"
    target["arm_payload_sha256"] = runner.digest_payload(target["arm_payload"])
    with pytest.raises(runner.ProbeError, match="certificates"):
        runner._verify_reaggregation(rows, receipt["failure_analysis"])


def test_reaggregation_recomputes_every_distribution_and_rekey_summary() -> None:
    runner = _load_runner("v025_stage4d_reaggregate_distributions")
    receipt = runner.run_unit(
        setting=runner._setting("a-r0"), world_index=1, executed_steps=1
    )
    for field, leaf, message in (
        ("decision_time_tail_s", "p95", "distribution field"),
        ("rate_tail", "p05_bps", "distribution field"),
        ("required_power_w_max_distribution", "max", "distribution field"),
        (
            "corrected_boundary_conditional_rekey",
            "eligible_user_boundaries",
            "corrected rekey",
        ),
    ):
        summary = copy.deepcopy(receipt["failure_analysis"])
        summary["arms"]["FULL"][field][leaf] += 1
        with pytest.raises(runner.ProbeError, match=message):
            runner._verify_reaggregation(receipt["canonical_step_rows"], summary)

    rows = copy.deepcopy(receipt["canonical_step_rows"])
    target = next(row for row in rows if row["arm"] == "FULL")
    target["arm_payload"]["complete_service_availability"] += 0.01
    target["arm_payload_sha256"] = runner.digest_payload(target["arm_payload"])
    with pytest.raises(runner.ProbeError, match="complete payload aggregate"):
        runner._verify_reaggregation(rows, receipt["failure_analysis"])

    rows = copy.deepcopy(receipt["canonical_step_rows"])
    target = next(row for row in rows if row["arm"] == "FULL")
    target["energy_hex"]["pa_j"] = "mutated"
    with pytest.raises(runner.ProbeError, match="wrappers"):
        runner._verify_reaggregation(rows, receipt["failure_analysis"])


def test_nonformal_and_smoke_world_indices_fail_closed() -> None:
    runner = _load_runner("v025_stage4d_domains")
    for index in (0, len(runner.DEVELOPMENT_WORLD_DOMAINS) + 1):
        with pytest.raises(runner.ProbeError, match="development domain"):
            runner.run_unit(
                setting=runner._setting("a-r0"),
                world_index=index,
                executed_steps=1,
            )
    with pytest.raises(runner.ProbeError, match="exactly one"):
        runner.run_unit(
            setting=runner._setting("a-r0"),
            world_index=2,
            executed_steps=1,
            smoke_not_matrix=True,
        )


def test_formal_world_tape_is_built_once_and_reused_across_settings(
    tmp_path: Path,
) -> None:
    runner = _load_runner("v025_stage4d_prepared_world")
    constructions = 0

    def factory(*, user_count: int = 100):
        nonlocal constructions
        constructions += 1
        assert user_count in {100, 150}
        return TinySyntheticProvider()

    module_name = "_v025_stage4d_counting_provider"
    sys.modules[module_name] = SimpleNamespace(factory=factory)
    runner.install_provider(f"{module_name}:factory", validate_instance=False)
    assert constructions == 0
    cache: dict[str, bytes] = {}
    manifest = runner.build_probe_world_manifest(
        executed_steps=1,
        tape_cache=cache,
    )
    # Eight probe profile/world tapes plus two separation-only calibration
    # tapes; the 31 settings do not trigger provider construction.
    assert constructions == 10
    for relative_path, encoded in cache.items():
        runner.write_immutable_bytes(tmp_path / relative_path, encoded)
    manifest_path = tmp_path / "world-manifest.json"
    runner.write_immutable(manifest_path, manifest)

    first = runner.load_prepared_world_tape(
        manifest_path, 1, run_setting_for("a-r0")
    )
    second = runner.load_prepared_world_tape(
        manifest_path, 1, run_setting_for("a-γ0")
    )
    assert constructions == 10
    assert first.digest == second.digest


def test_visibility_crossing_uses_the_exact_ten_degree_floor() -> None:
    tape = build_world_tape(
        domain=KAT_WORLD_DOMAINS[2],
        provider=TinySyntheticProvider(),
        steps=1,
        start_time_s=0.0,
    )
    candidate = tape.steps[0].boundaries[0].candidates[0]
    assert replace(candidate, elevation_deg=10.0, visible=True).visible is True
    with pytest.raises(MCRLContractError, match="10-degree floor"):
        replace(
            candidate,
            elevation_deg=np.nextafter(10.0, -np.inf),
            visible=True,
        )


def test_invalid_forecast_row_has_negative_margins_without_constructor_error() -> None:
    runner = _load_runner("v025_stage4d_invalid_forecast")
    row = runner._projection_from_profile(offset=2, profile=None, survives=False)
    assert row.valid is False
    assert row.survives is False
    assert row.required_power_w is None
    assert row.power_cap_w is None
    assert row.required_power_cap_margin_w is None
    assert row.min_decoding_margin_db == -100.0


def test_live_legality_stops_at_boundary_17_for_visibility_and_d2() -> None:
    arrays, _geometry = _three_user_arrays(0.0, 1.0e-4)
    for field in ("visible", "d2_eligible"):
        values = np.array(getattr(arrays, field), copy=True)
        values[17:, 0] = False
        changed = arrays.__class__(
            **{
                name: values if name == field else getattr(arrays, name)
                for name in arrays.__dataclass_fields__
            }
        )
        result = evaluate_ar_tdm_catalogue(
            changed,
            np.asarray([[0, -1, -1]]),
            field="nominal",
            boundary_indices=tuple(range(48)),
        )
        assert result.decoding_time_s[0, 0] == pytest.approx(10.56, abs=1.0e-12)


def test_committed_48_boundary_trajectories_match_scalar_resolution() -> None:
    arrays, geometry = _three_user_arrays(0.8, 1.0e-4)
    assignments = np.asarray(
        ((0, 1, 2), (0, 1, -1), (0, -1, -1)), dtype=np.int64
    )
    batch = evaluate_ar_tdm_catalogue(arrays, assignments, field="nominal")
    setting = next(row for row in MATRIX_SETTINGS if row.label == "a-r0")
    inventory = HardwareInventory.fixed(
        tuple((100 + index, index) for index in range(3))
    )
    for row_index, assignment in enumerate(assignments):
        active = np.flatnonzero(assignment >= 0)
        scalar_geometry = Geometry(
            tuple(geometry.links[index] for index in active),
            geometry.nominal_cross_gain[np.ix_(active, active)],
        )
        shared = build_shared_tape(
            "a-r",
            tuple((index * 0.640, scalar_geometry) for index in range(48)),
            inventory,
            field="nominal",
            roster=(0, 1, 2),
            config=RadiationConfig(rate_target_bps=50_000_000.0),
        )
        scalar = score_setting(shared, setting)
        assert float(batch.joules[row_index]) == pytest.approx(
            scalar.joules, abs=1.0e-9, rel=0.0
        )
        assert float(batch.bits[row_index].sum()) == pytest.approx(
            sum(scalar.bits.values()), abs=2.0e-6, rel=0.0
        )


def test_dense_and_scalar_evaluation_enter_through_common_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    arrays, geometry = _three_user_arrays(0.8, 1.0e-4)
    original = resolution_module.resolve_configuration
    calls: list[str] = []

    def traced(*args, **kwargs):
        calls.append("dense" if kwargs.get("batch_arrays") is not None else "scalar")
        return original(*args, **kwargs)

    monkeypatch.setattr(resolution_module, "resolve_configuration", traced)
    monkeypatch.setattr(adapter_module, "resolve_configuration", traced)
    evaluate_ar_tdm_catalogue(
        arrays,
        np.asarray([[0, 1, 2]]),
        field="nominal",
        boundary_indices=(0,),
    )
    build_shared_tape(
        "a-r",
        tuple((index * 0.640, geometry) for index in range(48)),
        HardwareInventory.fixed(tuple((100 + index, index) for index in range(3))),
        field="nominal",
        roster=(0, 1, 2),
        config=RadiationConfig(rate_target_bps=50_000_000.0),
    )
    assert calls[0] == "dense"
    assert calls.count("scalar") == 48


def test_common_resolver_rejects_mixed_mode_arguments() -> None:
    arrays, _ = _three_user_arrays(0.8, 1.0e-4)
    rows = np.asarray([[0, 1, 2]])

    with pytest.raises(ValueError, match="scalar-only"):
        resolution_module.resolve_configuration(
            batch_arrays=arrays,
            batch_selected_rows=rows,
            idle_power_w=1.0,
        )

    with pytest.raises(ValueError, match="require arrays"):
        resolution_module.resolve_configuration(batch_chunk_size=1)

    with pytest.raises(ValueError, match="require arrays"):
        resolution_module.resolve_configuration(batch_rate_target_bps=1.0)
