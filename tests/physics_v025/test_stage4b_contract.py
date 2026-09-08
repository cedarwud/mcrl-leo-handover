from __future__ import annotations

from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.physics_v025.adapter import (
    build_shared_tape,
    discontinuities_from_event_ledger,
    score_setting,
)
from mcrl.physics_v025.architectures import Geometry, Link
from mcrl.physics_v025.energy import HardwareInventory
from mcrl.physics_v025.integration import BoundarySample, InterruptionEvent
from mcrl.physics_v025.matrix import (
    ALL_SEALED_RUN_SETTINGS,
    LAUNCH_RUN_ORDER,
    MATRIX_SETTINGS,
    REGIME_RUN_SETTINGS,
    run_setting_for,
    shared_computation_plan,
)
from mcrl.physics_v025.tapes import (
    PROBE_WORLD_DOMAINS,
    ProviderProtocolOutputs,
    TinySyntheticProvider,
    build_world_tape,
)
from mcrl.physics_v025.targets import NetworkOutcome, set_score_decomposition


REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"
FIGURE_BUILDER = REPO / ".scratch/multi-catfish-v025-physics-successor/probe/build_off_axis_figure.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _outcome(value: int) -> NetworkOutcome:
    return NetworkOutcome.build(
        bits=value + 100,
        joules=100,
        phi=0,
        decoding_availability=1,
        useful_availability=1,
    )


def test_v15_set_decomposition_and_factor_identity_are_exact() -> None:
    values = {
        frozenset(): 0,
        frozenset({0}): 2,
        frozenset({1}): 3,
        frozenset({2}): 5,
        frozenset({0, 1}): 8,
        frozenset({0, 2}): 11,
        frozenset({1, 2}): 13,
        frozenset({0, 1, 2}): 25,
    }
    result = set_score_decomposition(
        coalition_users=(0, 1, 2),
        outcomes_by_subset={key: _outcome(value) for key, value in values.items()},
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_s=2,
        phi_difference=Fraction(-1, 2),
    )
    assert dict(result.d_by_user) == {0: 2, 1: 3, 2: 5}
    assert result.interaction_bits == 15
    assert sum(dict(result.shapley_interaction_by_user).values(), Fraction()) == 15
    assert result.c1 + result.c3 == Fraction(25, 2)
    assert result.factor_c1 == result.c1 - Fraction(1, 2)


def test_regimes_are_sealed_after_31_and_launch_order_is_binding() -> None:
    assert [row.run_id for row in ALL_SEALED_RUN_SETTINGS[:31]] == [
        row.label for row in MATRIX_SETTINGS
    ]
    assert [row.run_id for row in REGIME_RUN_SETTINGS] == ["R1", "R2", "R3", "R4"]
    assert len({row.digest for row in ALL_SEALED_RUN_SETTINGS}) == len(ALL_SEALED_RUN_SETTINGS)
    assert [row.run_id for row in LAUNCH_RUN_ORDER[:9]] == [
        "a-r0", "R1", "R2", "R3", "R4", "a′-r0", "a-γ0", "C2-H1", "C2-H2"
    ]
    assert run_setting_for("R1").rate_target_bps == 100_000_000.0
    assert run_setting_for("R2").user_count == 150
    assert [run_setting_for(name).circuit_power_per_active_chain_w for name in ("R3", "R4")] == [1.0, 0.1]
    plan = shared_computation_plan()
    assert plan["only_primary_run_id"] == "a-r0"
    assert all(
        row["claim_classification"] == "EXPLORATORY_SENSITIVITY"
        for row in plan["sealed_run_settings"]
        if row["run_id"] != "a-r0"
    )


def _bootstrap_rows() -> tuple[dict[str, float | str | int], ...]:
    rows = []
    for date_index in range(4):
        for learner_seed in range(3):
            # Deliberately retain distinct date, learner-seed, and interaction
            # components so the one- and two-way resampling laws separate.
            full_bits = 110.0 + 8.0 * date_index + 20.0 * learner_seed
            full_bits += 15.0 * date_index * learner_seed
            rows.append(
                {
                    "tle_date": f"2026-07-{date_index + 1:02d}",
                    "learner_seed": learner_seed,
                    "full_bits": full_bits,
                    "full_joules": 100.0,
                    "comparator_bits": 100.0,
                    "comparator_joules": 100.0,
                    "full_availability_served": 90.0 + date_index,
                    "full_availability_opportunities": 100.0 + 10 * date_index,
                    "comparator_availability_served": 88.0 + date_index,
                    "comparator_availability_opportunities": 100.0 + 10 * date_index,
                    "full_phi_numerator": 1.0,
                    "full_phi_denominator": 100.0 + 10 * date_index,
                    "comparator_phi_numerator": 1.0,
                    "comparator_phi_denominator": 100.0 + 10 * date_index,
                    "full_handover_events": 2.0,
                    "full_handover_opportunities": 100.0 + 10 * date_index,
                    "comparator_handover_events": 2.0,
                    "comparator_handover_opportunities": 100.0 + 10 * date_index,
                }
            )
    return tuple(rows)


def test_qos_counts_pool_inside_draw_and_intervals_differ_by_estimator() -> None:
    runner = _load(RUNNER, "v025_stage4b_runner")
    rows = _bootstrap_rows()
    one_way = runner.uncertainty_estimate(
        rows, learner_experiment=False, draws=1000, seed=11
    )["primary"]
    two_way = runner.uncertainty_estimate(
        rows, learner_experiment=True, draws=1000, seed=11
    )["primary"]
    expected_qos = sum(float(row["full_availability_served"]) for row in rows) / sum(
        float(row["full_availability_opportunities"]) for row in rows
    ) - sum(float(row["comparator_availability_served"]) for row in rows) / sum(
        float(row["comparator_availability_opportunities"]) for row in rows
    )
    assert one_way["qos_availability_delta"] == pytest.approx(expected_qos)
    assert one_way["interval_convention"].startswith("central 95%")
    assert one_way["contrast_lower_95_relative"] != pytest.approx(
        two_way["contrast_lower_95_relative"]
    )
    dispatched = runner.uncertainty_estimate(
        rows, learner_experiment=True, draws=100, seed=4
    )
    assert dispatched["primary_estimator"] == "two-way-pigeonhole"


def test_zero_bit_cluster_keeps_primary_and_undefines_log_supplement() -> None:
    runner = _load(RUNNER, "v025_stage4b_zero_runner")
    rows = list(_bootstrap_rows()[:3])
    rows[0] = {**rows[0], "full_bits": 0.0, "comparator_bits": 0.0}
    result = runner.pooled_ratio_cluster_bootstrap(rows, draws=300, seed=8)
    assert math.isfinite(result["contrast_lower_95_relative"])
    assert result["supplementary_paired_world_log_ee"]["status"] == "UNDEFINED_ZERO_BIT_CLUSTER"


def test_admission_reads_a_r0_only_and_always_reports_regime_separately() -> None:
    runner = _load(RUNNER, "v025_stage4b_admission_runner")
    primary = {
        "physics_integrity": True,
        "u1_complete_certified": True,
        "j1_beyond_base_and_u_all": True,
        "s0_relative_gain": 0.011,
        "usable_energy_opportunity": True,
        "retained_factor_marginals": True,
    }
    result = runner.training_admission(
        primary_setting="a-r0",
        certificates=primary,
        regime_certificates={"R1": {**primary, "retained_factor_marginals": False}},
    )
    assert result["decision"] == "ADMIT"
    assert result["source_setting"] == "a-r0"
    assert result["regime_sensitivity_certificates"]["R1"]["label"] == "in regime R1"
    assert result["regime_sensitivity_certificates"]["R1"]["decision"] == "NOT_ADMITTED_IN_REGIME"
    with pytest.raises(runner.ProbeError, match="a-r0 only"):
        runner.training_admission(primary_setting="R1", certificates=primary)
    assert runner.report_schema() == {
        "only_primary_setting": "a-r0",
        "primary_claim": "conditional conjunction",
        "all_other_settings": "EXPLORATORY_SENSITIVITY",
        "panel": "TRAIN_ONLY",
    }


def test_provider_protocol_and_33_step_tape_are_mandatory() -> None:
    runner = _load(RUNNER, "v025_stage4b_allocation_runner")
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=TinySyntheticProvider(),
        steps=33,
        start_time_s=0.0,
    )
    manifest = tape.manifest()
    assert len(tape.steps) == manifest["steps"] == 33
    assert manifest["split"] == manifest["provider_protocol"]["split"] == "TRAIN"
    assert manifest["start_utc"].endswith("+00:00")
    assert manifest["tle_files"]
    assert len(manifest["split_rule_sha256"]) == len(manifest["provider_source_sha256"]) == 64
    identity = runner.world_allocation_identity(tape, role="PROBE", learner_seed=17)
    identity = {
        **identity,
        "tle_date": "2026-01-01",
        "start_utc": "2026-01-01T00:00:00+00:00",
    }
    roles = sorted(runner.SUCCESSOR_DEVELOPMENT_ROLES | {"CLAIM_PANEL"})
    identities = tuple(
        {
            **identity,
            "role": role,
            "tle_date": f"2026-01-{index + 1:02d}",
            "start_utc": f"2026-01-{index + 1:02d}T00:00:00+00:00",
        }
        for index, role in enumerate(roles)
    )
    allocation = runner.build_allocation_manifest(identities)
    assert allocation["role_wise_date_disjoint"] is True
    assert identity["world_domain"] == PROBE_WORLD_DOMAINS[0]
    collision = {**identity, "role": "CLAIM_PANEL"}
    with pytest.raises(runner.ProbeError, match="role-wise date collision"):
        runner.build_allocation_manifest((identity, collision))
    with pytest.raises(MCRLContractError, match=r"exactly \+00:00"):
        ProviderProtocolOutputs(
            split="TRAIN",
            start_utc="2026-01-01T01:00:00+01:00",
            tle_files=(("x.tle", "0" * 64),),
            split_rule_digest="1" * 64,
            provider_source_digest="2" * 64,
        )


def test_score_setting_wires_left_right_discontinuities() -> None:
    setting = next(row for row in MATRIX_SETTINGS if row.label == "b0")
    geometry = Geometry(
        (Link(0, (1, 1), 0, 1.0e-12, 1.0e-12),),
        np.zeros((1, 1)),
        np.zeros((1, 1)),
    )
    tape = build_shared_tape(
        "b",
        tuple((index * 0.640, geometry) for index in range(48)),
        HardwareInventory.fixed(((1, 1),)),
        roster=(0,),
    )
    plain = score_setting(tape, setting)
    discontinuities = (
        BoundarySample(0.32, {0: 0.0}, 0.0, {0: False}),
        BoundarySample(0.32, {0: 1.0e9}, 1.0, {0: True}),
    )
    wired = score_setting(tape, setting, discontinuities=discontinuities)
    assert wired.joules != plain.joules
    assert wired.bits != plain.bits
    ledger_limits = discontinuities_from_event_ledger(
        tape,
        (InterruptionEvent(0, 0.32, "same_satellite_beam_change"),),
        exact_limits_by_time={0.32: discontinuities},
    )
    assert len(ledger_limits) == 2
    assert ledger_limits[0].time_s == ledger_limits[1].time_s == 0.32
    from_ledger = score_setting(tape, setting, discontinuities=ledger_limits)
    assert from_ledger.bits == wired.bits
    assert from_ledger.joules == wired.joules


def test_sealed_off_axis_kat_uses_a_r0_and_changes_power_and_ee() -> None:
    builder = _load(FIGURE_BUILDER, "v025_off_axis_builder")
    rows = builder.off_axis_rows()
    assert all(
        left["required_power_w"] < right["required_power_w"]
        and left["pooled_ee_bits_per_j"] > right["pooled_ee_bits_per_j"]
        for left, right in zip(rows, rows[1:])
    )
    receipt = json.loads((FIGURE_BUILDER.parent / "figures/a-r0-off-axis-kat.json").read_text())
    assert receipt["setting"]["run_id"] == "a-r0"
    assert receipt["identities"] == {
        "pooled_ee_strictly_decreases": True,
        "required_power_strictly_increases": True,
    }
