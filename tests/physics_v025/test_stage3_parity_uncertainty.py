"""Stage-3 parity, shortlist, diagnostics, and uncertainty KATs."""

from __future__ import annotations

import importlib.util
import inspect
import math
from dataclasses import replace
from pathlib import Path
import sys
import json
import subprocess

import numpy as np
import pytest

from mcrl.physics_v025.parity import (
    DecisionProfile,
    common_action_bootstrap,
    declared_c3_oracle,
    demand_cap_profiles,
    production_c3,
    reoptimize_joint_by_regime,
    reward_endpoint_identity,
    trace_declared_target_decoder_parity,
)


REPO = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"


def _runner():
    spec = importlib.util.spec_from_file_location("v025_stage3_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _profiles() -> tuple[DecisionProfile, ...]:
    return tuple(
        DecisionProfile.build(label, bits=(5, 5), energy_j=energy, served=(True, True))
        for label, energy in zip(("00", "10", "01", "11"), (10, 10, 10, 8), strict=True)
    )


@pytest.mark.parametrize(
    "producer",
    [declared_c3_oracle, production_c3, trace_declared_target_decoder_parity, reward_endpoint_identity],
)
def test_parity_producers_require_all_three_calibration_values(producer) -> None:
    signature = inspect.signature(producer)
    for name in ("lambda_bits_per_j", "eta_ref", "kappa_bits_per_user_s"):
        assert signature.parameters[name].default is inspect.Parameter.empty


def test_declared_target_decoder_cross_product_reaches_physical_endpoints() -> None:
    profiles = _profiles()
    declared = declared_c3_oracle(
        *profiles, lambda_bits_per_j=1, eta_ref=1, kappa_bits_per_user_s=2
    )
    production = production_c3(
        *profiles, lambda_bits_per_j=1, eta_ref=1, kappa_bits_per_user_s=2
    )
    assert declared.unilateral_c3 == production.unilateral_c3 == (0, 0)
    assert declared.psi == production.psi == 2
    assert declared.lcsrs_shares == production.lcsrs_shares == (1, 1)

    trace = trace_declared_target_decoder_parity(
        *profiles, lambda_bits_per_j=1, eta_ref=1, kappa_bits_per_user_s=2
    )
    assert set(trace.raw_state_endpoints) == {"00", "10", "01", "11"}
    for label, endpoint in trace.raw_state_endpoints.items():
        expected = profiles[("00", "10", "01", "11").index(label)]
        assert endpoint.action == label
        assert endpoint.bits == expected.bits
        assert endpoint.energy_j == expected.energy_j
        assert endpoint.served == expected.served
    assert trace.production_formula_matches_declared
    assert trace.additive_execution.action == trace.atomic_execution.action == "11"
    assert trace.atomic_execution.energy_j == 8


def test_whole_network_c1_leaves_no_unilateral_externality_in_c3() -> None:
    profiles = (
        DecisionProfile.build("00", bits=(10, 20), energy_j=5, served=(True, True)),
        DecisionProfile.build("10", bits=(12, 23), energy_j=6, served=(True, True)),
        DecisionProfile.build("01", bits=(14, 19), energy_j=7, served=(True, True)),
        DecisionProfile.build("11", bits=(16, 22), energy_j=8, served=(True, True)),
    )
    declared = declared_c3_oracle(
        *profiles, lambda_bits_per_j=2, eta_ref=2, kappa_bits_per_user_s=3
    )
    production = production_c3(
        *profiles, lambda_bits_per_j=2, eta_ref=2, kappa_bits_per_user_s=3
    )
    assert declared == production
    assert declared.unilateral_c3 == (0, 0)
    assert declared.lcsrs_shares == (declared.psi / 2, declared.psi / 2)


def test_nonbinding_demand_cap_and_per_regime_joint_reoptimization() -> None:
    profiles = _profiles()
    capped = demand_cap_profiles(
        profiles,
        demand_cap_bits=100,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
    )
    assert capped == profiles
    choices = reoptimize_joint_by_regime(
        {
            "bits-first": profiles,
            "energy-first": (
                profiles[0],
                DecisionProfile.build("10", bits=(20, 5), energy_j=30, served=(True, True)),
                profiles[2],
                DecisionProfile.build("11", bits=(5, 5), energy_j=20, served=(True, True)),
            ),
        },
        lambda_by_regime={"bits-first": 0.1, "energy-first": 2},
        eta_ref_by_regime={"bits-first": 0.1, "energy-first": 2},
        kappa_bits_per_user_s_by_regime={"bits-first": 2, "energy-first": 2},
    )
    assert choices == {"bits-first": "11", "energy-first": "00"}


def test_common_action_bootstrap_never_builds_unattainable_headwise_action() -> None:
    result = common_action_bootstrap(
        ((10, 0), (0, 9)),
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=1,
    )
    assert result.action_index == 0
    assert result.selected_heads == (10, 0)
    assert result.scalarized_value == 10
    assert result.selected_heads != (10, 9)


def test_probe_dry_run_wires_formula_decoder_and_reward_endpoint_parity() -> None:
    completed = subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--dry-run"],
        cwd=REPO,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    parity = payload["declared_target_decoder_parity"]
    assert payload["reward_endpoint_identity_checked"] is True
    assert parity["production_formula_matches_declared"] is True
    assert parity["additive_executed_action"] == parity["atomic_executed_action"] == "11"
    assert parity["production_decoder_paths"] == ["_independent_proposal", "_set_select"]
    assert parity["executed_endpoint_energy_j"] == 8
    assert parity["formula_decoder_cross"] == {
        formula: {
            decoder: {
                "executed_action": "11",
                "bits": [5.0, 5.0],
                "joules": 8.0,
                "served": [True, True],
            }
            for decoder in ("additive", "atomic")
        }
        for formula in ("declared", "production")
    }
    assert parity["t3_energy_used"] is False


def test_shortlist_is_a_superset_and_receipts_report_zero_misses() -> None:
    runner = _runner()
    counts = runner.synthetic_shortlist_miss_counts()
    assert counts == {1: 0, 2: 0, 3: 0, 4: 0}
    receipt = runner.run_unit(setting=runner._setting("a-r0"), world_index=1, executed_steps=1)
    assert receipt["candidate_shortlist_miss_count"] == 0
    assert receipt["steps"][0]["e1_certificate"]["candidate_shortlist_miss_count"] == 0


def test_shortlist_census_detects_a_legal_candidate_exclusion() -> None:
    runner = _runner()
    tape = runner.build_world_tape(
        domain=runner.PROBE_WORLD_DOMAINS[0],
        provider=runner.TinySyntheticProvider(),
        steps=1,
        start_time_s=0.0,
    )
    boundary = tape.steps[0].boundaries[0]
    target = next(row for row in boundary.candidates if row.legal)
    candidates = tuple(
        replace(row, coarse_shortlisted=False) if row is target else row
        for row in boundary.candidates
    )
    bad_boundary = replace(boundary, candidates=candidates)
    bad_step = replace(tape.steps[0], boundaries=(bad_boundary, *tape.steps[0].boundaries[1:]))
    bad_tape = replace(tape, steps=(bad_step,))
    base = runner._base_configuration(bad_tape, 0, "nearest-eligible")
    _catalogue, census = runner._catalogue_with_census(bad_tape, 0, base)
    assert census["candidate_shortlist_miss_count"] == 1


def test_receipt_has_successor_usable_energy_range_diagnostic() -> None:
    runner = _runner()
    receipt = runner.run_unit(setting=runner._setting("a-r0"), world_index=1, executed_steps=1)
    diagnostic = receipt["successor_usable_energy_range"]
    assert diagnostic["selected_acm_mode_counts"]
    assert 0 <= diagnostic["se_plateau_user_step_share"] <= 1
    assert 0 <= diagnostic["rf_cap_transmission_share"] <= 1
    assert diagnostic["best_feasible_reassignment_dc_energy_change_j_by_beam"]
    assert all(
        math.isfinite(value)
        for value in diagnostic["best_feasible_reassignment_dc_energy_change_j_by_beam"].values()
    )
    assert diagnostic["thresholds_applied"] is False


def test_treatment_t_receipt_reports_left_snapshot_beside_same_instant_integral() -> None:
    runner = _runner()
    receipt = runner.run_unit(setting=runner._setting("a-rT"), world_index=1, executed_steps=1)
    for arm in receipt["steps"][0]["arms"]:
        comparison = arm["treatment_t_same_instant_comparison"]
        assert comparison["snapshot_convention"].startswith("left-endpoint")
        assert comparison["left_snapshot"]["bits"] == pytest.approx(arm["bits"])
        assert comparison["same_instant_integral"]["bits"] >= 0


def test_h_treatment_removes_useful_time_during_candidate_scoring() -> None:
    runner = _runner()
    tape = runner.build_world_tape(
        domain=runner.PROBE_WORLD_DOMAINS[0],
        provider=runner.TinySyntheticProvider(),
        steps=1,
        start_time_s=0.0,
    )
    base = runner._base_configuration(tape, 0, "nearest-eligible")
    catalog = runner._catalogue(tape, 0, base)
    changed = next(row for row in catalog if row.changed_users == 1)
    control = runner.StepEvaluator(
        tape, runner._setting("a-r0"), 0, transition_from=base
    ).evaluate(changed)
    interrupted = runner.StepEvaluator(
        tape, runner._setting("a-rH"), 0, transition_from=base
    ).evaluate(changed)
    assert interrupted.bits < control.bits
    assert interrupted.joules == pytest.approx(control.joules)
    assert sum(interrupted.score.useful_time_s.values()) < sum(
        control.score.useful_time_s.values()
    )


def test_rekey_estimator_is_derived_from_receipt_ledger_and_handles_no_boundary() -> None:
    runner = _runner()
    receipt = runner.run_unit(setting=runner._setting("a-r0"), world_index=1, executed_steps=1)
    by_arm = receipt["failure_analysis"]["corrected_boundary_conditional_rekey_by_arm"]
    for row in by_arm.values():
        assert row == {
            "rekeys": 0,
            "eligible_user_boundaries": 0,
            "rate": None,
            "numerator_source": "physical event ledger",
        }

    refresh_receipt = runner.run_unit(
        setting=runner._setting("a-r0"), world_index=1, executed_steps=5
    )
    neutral = refresh_receipt["failure_analysis"][
        "corrected_boundary_conditional_rekey_by_arm"
    ][runner.ALL_NEUTRAL_CONTROL]
    assert neutral == {
        "rekeys": 1,
        "eligible_user_boundaries": 2,
        "rate": 0.5,
        "numerator_source": "physical event ledger",
    }


def _iid_blocks() -> tuple[dict[str, float | str | int], ...]:
    rng = np.random.default_rng(20260908)
    rows = []
    for index in range(400):
        energy = 90.0 + rng.uniform(0.0, 20.0)
        comparator_energy = 85.0 + rng.uniform(0.0, 20.0)
        rows.append(
            {
                "tle_date": f"2026-08-{1 + index % 20:02d}",
                "training_seed": index // 20,
                "full_bits": 1.08 * energy + rng.normal(0.0, 2.0),
                "full_joules": energy,
                "comparator_bits": comparator_energy + rng.normal(0.0, 2.0),
                "comparator_joules": comparator_energy,
                "full_qos": 1.0,
                "comparator_qos": 1.0,
                "full_phi": 0.0,
                "comparator_phi": 0.0,
                "full_handover_rate": 0.0,
                "comparator_handover_rate": 0.0,
            }
        )
    return tuple(rows)


def test_three_uncertainty_intervals_finite_and_delta_agrees_on_iid_blocks() -> None:
    runner = _runner()
    blocks = _iid_blocks()
    primary = runner.pooled_ratio_cluster_bootstrap(blocks, draws=4000, seed=91)
    delta = runner.delta_method_log_contrast(blocks)
    pigeonhole = runner.two_way_pigeonhole_bootstrap(blocks, draws=2000, seed=92)
    intervals = (
        (primary["contrast_lower_95_percentage_points"], primary["contrast_upper_95_percentage_points"]),
        (delta["lower_95_percentage_points"], delta["upper_95_percentage_points"]),
        (pigeonhole["lower_95_percentage_points"], pigeonhole["upper_95_percentage_points"]),
    )
    assert all(math.isfinite(value) for interval in intervals for value in interval)
    primary_width = intervals[0][1] - intervals[0][0]
    delta_width = intervals[1][1] - intervals[1][0]
    assert abs(delta_width / primary_width - 1.0) < 0.10


def test_pooled_ratio_and_paired_log_intervals_are_distinct() -> None:
    runner = _runner()
    blocks = _iid_blocks()[:20]
    result = runner.pooled_ratio_cluster_bootstrap(blocks, draws=1000, seed=7)
    paired = result["supplementary_paired_world_log_ee"]
    assert result["contrast_lower_95_percentage_points"] != pytest.approx(
        paired["lower_95_percentage_points"]
    )
