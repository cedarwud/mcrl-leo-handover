"""W-134 -- bounded V0.9 integrated oracle runner contracts.

These tests are intentionally receipt/static/pure-function tests.  They must
not open a TLE world, execute an episode, read TEST, or train a learner.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


_ROOT = Path(__file__).resolve().parents[1]
_RUNNER_PATH = _ROOT / ".scratch" / "pnfe-v09" / "run_v09_integrated_oracle.py"
_SPEC = importlib.util.spec_from_file_location("run_v09_integrated_oracle", _RUNNER_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - collection guard
    raise RuntimeError(f"cannot load {_RUNNER_PATH}")
_RUNNER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_RUNNER)


def _row(arm: str, lineage: int, bits: float, energy: float, served: int) -> dict:
    return {
        "arm": arm,
        "initialization_seed": lineage,
        "total_bits": bits,
        "total_energy_j": energy,
        "served_user_steps": served,
        "decision_count": 10,
        "diagnostics": [{
            "step_index": 1,
            "h0_true_matched_nonfocal_ordering": {"status": "OBSERVED", "compared_pairs": 1},
            "simultaneous_cross_term": {
                "status": "OBSERVED",
                "direction_reversal": False,
            },
        }],
        "mechanics": {"passed": True},
        "c3_legal_spread_count": 1,
        "full_vs_drop_c3_action_flips": 1,
    }


def test_fixed_v09_contract_constants_and_arm_composition() -> None:
    assert _RUNNER.WORLD_SEED == 2026104501
    assert _RUNNER.LINEAGES == (2026092101, 2026092102, 2026092103)
    assert _RUNNER.STEPS_PER_EPISODE == 10
    assert _RUNNER.EPISODES_PER_ARM == 3
    assert _RUNNER.ARMS == ("FULL", "DROP_C2", "DROP_C3", "DROP_C1")
    assert _RUNNER.ARM_HEADS == {
        "FULL": ("Q1", "O2_EXACT", "O3_PNFE"),
        "DROP_C2": ("Q1", "O3_PNFE"),
        "DROP_C3": ("Q1", "O2_EXACT"),
        "DROP_C1": ("O2_EXACT", "O3_PNFE"),
    }


def test_select_actions_is_one_common_mask_left_to_right_unweighted_argmax() -> None:
    legal = np.zeros((2, _RUNNER.NUM_ACTIONS), dtype=np.bool_)
    legal[0, :2] = True
    legal[1, [0, 2]] = True
    q1 = np.zeros_like(legal, dtype=np.float64)
    o2 = np.zeros_like(q1)
    o3 = np.zeros_like(q1)
    q1[0, :3] = [1.0, 2.0, 100.0]
    o2[1, 2] = 3.0
    o3[1, 1] = 4.0
    surfaces = {
        "Q1": q1,
        "O2_EXACT": o2,
        "O3_PNFE": o3,
    }
    assert np.array_equal(
        _RUNNER.select_actions(surfaces, legal, "FULL"),
        np.array([1, 2], dtype=np.int64),
    )
    assert np.array_equal(
        _RUNNER.select_actions(surfaces, legal, "DROP_C2"),
        np.array([1, 0], dtype=np.int64),
    )
    with pytest.raises(_RUNNER.RunnerContractError, match="common legal mask"):
        _RUNNER.select_actions(surfaces, legal.astype(np.int8), "FULL")


def test_gate_requires_all_three_pooled_and_lineage_margins_and_diagnostics() -> None:
    rows: dict[str, list[dict]] = {arm: [] for arm in _RUNNER.ARMS}
    for lineage in _RUNNER.LINEAGES:
        rows["FULL"].append(_row("FULL", lineage, 120.0, 1.0, 10))
        rows["DROP_C2"].append(_row("DROP_C2", lineage, 110.0, 1.0, 10))
        rows["DROP_C3"].append(_row("DROP_C3", lineage, 109.0, 1.0, 10))
        rows["DROP_C1"].append(_row("DROP_C1", lineage, 108.0, 1.0, 10))
    decision = _RUNNER.adjudicate_gate(rows)
    assert decision["decision"] == "PASS_ORACLE_GATE"
    assert all(decision["pooled_margins"].values())
    assert decision["diagnostics_complete"] is True


def test_missing_required_diagnostic_fails_closed_even_with_positive_ee() -> None:
    rows: dict[str, list[dict]] = {arm: [] for arm in _RUNNER.ARMS}
    for lineage in _RUNNER.LINEAGES:
        for arm, bits in (("FULL", 120.0), ("DROP_C2", 110.0), ("DROP_C3", 109.0), ("DROP_C1", 108.0)):
            row = _row(arm, lineage, bits, 1.0, 10)
            row["diagnostics"][0]["h0_true_matched_nonfocal_ordering"] = {"status": "MISSING"}
            rows[arm].append(row)
    decision = _RUNNER.adjudicate_gate(rows)
    assert decision["decision"] == "FAIL_ORACLE_GATE"
    assert decision["diagnostics_complete"] is False
    assert any("required diagnostic" in stop for stop in decision["hard_stops"])


def test_unscheduled_diagnostic_rows_are_ignored_but_scheduled_rows_are_required() -> None:
    rows: dict[str, list[dict]] = {arm: [] for arm in _RUNNER.ARMS}
    for lineage in _RUNNER.LINEAGES:
        for arm, bits in (("FULL", 120.0), ("DROP_C2", 110.0), ("DROP_C3", 109.0), ("DROP_C1", 108.0)):
            row = _row(arm, lineage, bits, 1.0, 10)
            row["diagnostics"] = [
                {
                    "step_index": 0,
                    "h0_true_matched_nonfocal_ordering": {"status": "NOT_SCHEDULED"},
                    "simultaneous_cross_term": {"status": "NOT_SCHEDULED"},
                },
                {
                    "step_index": 1,
                    "h0_true_matched_nonfocal_ordering": {"status": "OBSERVED", "compared_pairs": 1},
                    "simultaneous_cross_term": {"status": "OBSERVED", "direction_reversal": False},
                },
            ]
            rows[arm].append(row)
    decision = _RUNNER.adjudicate_gate(rows)
    assert decision["diagnostics_complete"] is True
    assert decision["cross_term_reversal"]["evaluable_samples"] == 12

    for arm_rows in rows.values():
        for row in arm_rows:
            row["diagnostics"] = [{
                "step_index": 0,
                "h0_true_matched_nonfocal_ordering": {"status": "NOT_SCHEDULED"},
                "simultaneous_cross_term": {"status": "NOT_SCHEDULED"},
            }]
    blocked = _RUNNER.adjudicate_gate(rows)
    assert blocked["diagnostics_complete"] is False
    assert any("no comparable sample" in stop for stop in blocked["hard_stops"])
    assert any("no evaluable sample" in stop for stop in blocked["hard_stops"])


def test_one_cross_term_reversal_is_not_systematic() -> None:
    rows: dict[str, list[dict]] = {arm: [] for arm in _RUNNER.ARMS}
    for index, lineage in enumerate(_RUNNER.LINEAGES):
        for arm, bits in (("FULL", 120.0), ("DROP_C2", 110.0), ("DROP_C3", 109.0), ("DROP_C1", 108.0)):
            row = _row(arm, lineage, bits, 1.0, 10)
            row["diagnostics"][0]["simultaneous_cross_term"]["direction_reversal"] = index == 0
            rows[arm].append(row)
    decision = _RUNNER.adjudicate_gate(rows)
    assert decision["cross_term_reversal"]["evaluable_samples"] == 12
    assert decision["cross_term_reversal"]["reversal_samples"] == 4
    assert decision["cross_term_reversal"]["systematic_reversal"] is False

    for arm_rows in rows.values():
        for row in arm_rows:
            row["diagnostics"][0]["simultaneous_cross_term"]["direction_reversal"] = True
    blocked = _RUNNER.adjudicate_gate(rows)
    assert blocked["cross_term_reversal"]["systematic_reversal"] is True
    assert any("systematic" in stop for stop in blocked["hard_stops"])


def test_runner_source_has_no_old_multi_head_query_or_training_path() -> None:
    source = _RUNNER_PATH.read_text(encoding="utf-8")
    assert "q_values_by_route" not in source
    assert "q2_values_by_route" not in source
    assert "optimizer.step" not in source
    assert "TEST_SPLIT_OPENED = False" in source
    assert "EPISODE_TRAINING = False" in source
    assert "StepEnvironment._evaluate_selected_actions" in source
    assert "multi_removal_receipts" in source
    assert "state_unchanged" in source
    assert "rng_unchanged" in source


def _shard_payload(arm: str, lineage: int, *, world: str = "world") -> dict:
    trace = [[] for _ in range(_RUNNER.STEPS_PER_EPISODE)]
    row = {
        "schema": _RUNNER.EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": lineage,
        "world_seed": _RUNNER.WORLD_SEED,
        "evaluation_split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "steps": _RUNNER.STEPS_PER_EPISODE,
        "decision_count": _RUNNER.USERS * _RUNNER.STEPS_PER_EPISODE,
        "initial_world_sha256": world,
        "fading_field_sha256": _RUNNER.field_for_world().root_digest,
        "fading_field_components": [_RUNNER.FIELD_COMPONENT, _RUNNER.WORLD_SEED],
        "total_bits": 120.0 if arm == "FULL" else 110.0,
        "total_energy_j": 1.0,
        "ratio_of_sums_ee_bits_per_j": 120.0 if arm == "FULL" else 110.0,
        "served_user_steps": 1000,
        "served_fraction": 1.0,
        "action_trace": trace,
        "action_trace_sha256": _RUNNER._action_trace_sha256(arm, lineage, trace),
        "q1_parameter_sha256_before": "a" * 64,
        "q1_parameter_sha256_after": "a" * 64,
        "diagnostics": [
            {
                "step_index": 1,
                "h0_true_matched_nonfocal_ordering": {"status": "OBSERVED", "compared_pairs": 1},
                "simultaneous_cross_term": {
                    "status": "OBSERVED",
                    "direction_reversal": False,
                },
            }
        ]
        + [
            {
                "step_index": index,
                "h0_true_matched_nonfocal_ordering": {"status": "NOT_SCHEDULED"},
                "simultaneous_cross_term": {"status": "NOT_SCHEDULED"},
            }
            for index in [0, *range(2, _RUNNER.STEPS_PER_EPISODE)]
        ],
        "mechanics": {
            "passed": True,
            "no_learner_update": True,
            "no_future_policy_query": True,
            "old_heads_queried": False,
        },
        "c3_legal_spread_count": 1,
        "full_vs_drop_c3_action_flips": 1,
    }
    contract = _RUNNER.contract_receipt()
    return {
        "schema": _RUNNER.SHARD_SCHEMA,
        "shard_id": f"{arm}-{lineage}",
        "arm": arm,
        "initialization_seed": lineage,
        "world_seed": _RUNNER.WORLD_SEED,
        "contract": contract,
        "contract_sha256": _RUNNER.canonical_sha256(contract),
        "contract_file_sha256": _RUNNER.file_sha256(_RUNNER.CONTRACT_PATH),
        "runner_file_sha256": _RUNNER.file_sha256(_RUNNER_PATH),
        "runtime_file_sha256": {
            str(path.relative_to(_RUNNER.REPO)): _RUNNER.file_sha256(path)
            for path in _RUNNER.RUNTIME_PATHS
        },
        "field_root_digest": _RUNNER.field_for_world().root_digest,
        "row_sha256": _RUNNER.canonical_sha256(row),
        "row": row,
        "diagnostics_enabled": True,
    }


def test_merge_requires_exactly_one_complete_shard_per_arm_lineage(tmp_path: Path) -> None:
    shard_root = tmp_path / "shards"
    shard_root.mkdir()
    identities = [
        (arm, lineage)
        for arm in _RUNNER.ARMS
        for lineage in _RUNNER.LINEAGES
    ]
    for arm, lineage in identities[:-1]:
        directory = shard_root / f"{arm}-{lineage}"
        directory.mkdir()
        (directory / "shard.json").write_text(
            json.dumps(_shard_payload(arm, lineage), sort_keys=True), encoding="utf-8"
        )
    with pytest.raises(_RUNNER.RunnerContractError, match="expected 12 shards"):
        _RUNNER.merge_shards(shard_dir=shard_root, output_dir=tmp_path / "out-incomplete")

    arm, lineage = identities[-1]
    directory = shard_root / f"{arm}-{lineage}"
    directory.mkdir()
    (directory / "shard.json").write_text(
        json.dumps(_shard_payload(arm, lineage), sort_keys=True), encoding="utf-8"
    )
    result = _RUNNER.merge_shards(
        shard_dir=shard_root, output_dir=tmp_path / "out-complete"
    )
    assert result["source_mode"] == "INDEPENDENT_EPISODE_SHARDS_MERGE"
    assert result["episode_count"] == 12
    assert result["arm_row_counts"] == {arm: 3 for arm in _RUNNER.ARMS}
    assert (tmp_path / "out-complete" / "result.json").is_file()


def test_merge_rejects_cross_world_shards_before_gate(tmp_path: Path) -> None:
    shard_root = tmp_path / "shards"
    shard_root.mkdir()
    for arm in _RUNNER.ARMS:
        for lineage in _RUNNER.LINEAGES:
            directory = shard_root / f"{arm}-{lineage}"
            directory.mkdir()
            world = "other-world" if (arm, lineage) == ("FULL", _RUNNER.LINEAGES[0]) else "world"
            (directory / "shard.json").write_text(
                json.dumps(_shard_payload(arm, lineage, world=world), sort_keys=True),
                encoding="utf-8",
            )
    with pytest.raises(_RUNNER.RunnerContractError, match="one initial TRAIN world"):
        _RUNNER.merge_shards(shard_dir=shard_root, output_dir=tmp_path / "out")


def test_merge_rejects_shard_from_another_runner_before_gate(tmp_path: Path) -> None:
    shard_root = tmp_path / "shards"
    shard_root.mkdir()
    for arm in _RUNNER.ARMS:
        for lineage in _RUNNER.LINEAGES:
            directory = shard_root / f"{arm}-{lineage}"
            directory.mkdir()
            payload = _shard_payload(arm, lineage)
            if (arm, lineage) == ("FULL", _RUNNER.LINEAGES[0]):
                payload["runner_file_sha256"] = "0" * 64
            (directory / "shard.json").write_text(
                json.dumps(payload, sort_keys=True), encoding="utf-8"
            )
    with pytest.raises(_RUNNER.RunnerContractError, match="runner file hash mismatch"):
        _RUNNER.merge_shards(shard_dir=shard_root, output_dir=tmp_path / "out")
