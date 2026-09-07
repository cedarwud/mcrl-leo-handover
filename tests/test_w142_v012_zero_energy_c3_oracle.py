"""W-142 -- frozen control plane for the V0.12 zero-energy C3 oracle."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "zero-energy-c3-v012"
    / "run_v012_zero_energy_c3_oracle.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_v012_zero_energy_c3_oracle", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_contract_freezes_exact_two_world_three_arm_panel_and_order() -> None:
    contract = RUNNER.contract_receipt()
    assert RUNNER.WORLD_SEEDS == (2026104801, 2026104802)
    assert RUNNER.LINEAGES == (2026092101, 2026092102, 2026092103)
    assert RUNNER.ARMS == ("DROP_C3", "FULL_ZR", "FULL_HR")
    assert contract["episodes"] == 18
    assert contract["candidate_order"] == ["ZR", "HR"]
    assert contract["arm_heads"] == {
        "DROP_C3": ["Q1", "O2_OPS3"],
        "FULL_ZR": ["Q1", "O2_OPS3", "O3_ZR"],
        "FULL_HR": ["Q1", "O2_OPS3", "O3_HR"],
    }
    assert contract["split"] == "TRAIN"
    assert contract["test_split_opened"] is False
    assert contract["episode_training"] is False
    assert contract["learner_update"] is False
    assert contract["compatibility"]["tolerance"] == 0.0
    assert contract["selection"] == "one_common_mask_one_argmax_one_action"


def test_world_fields_are_distinct_deterministic_and_arm_independent() -> None:
    left = RUNNER.field_for_world(RUNNER.WORLD_SEEDS[0])
    right = RUNNER.field_for_world(RUNNER.WORLD_SEEDS[1])
    assert left.root_digest == RUNNER.field_for_world(RUNNER.WORLD_SEEDS[0]).root_digest
    assert left.root_digest != right.root_digest
    assert "arm" in RUNNER.FIELD_EXCLUDES
    assert "initialization_seed" in RUNNER.FIELD_EXCLUDES
    with pytest.raises(RUNNER.V012OracleError, match="outside"):
        RUNNER.field_for_world(1)


def test_masked_sum_is_unweighted_and_uses_smallest_native_tie_break() -> None:
    mask = np.zeros((2, 28), dtype=np.bool_)
    mask[0, [0, 1, 3]] = True
    mask[1, [1, 2]] = True
    q1 = np.zeros((2, 28), dtype=np.float64)
    o2 = np.zeros_like(q1)
    o3 = np.zeros_like(q1)
    q1[0, [0, 1, 3]] = [1.0, 0.0, 1.0]
    q1[1, [1, 2]] = [0.0, 1.0]
    o2[0, 1] = 2.0
    o2[1, 1] = 1.0
    o3[0, 3] = 3.0
    o3[1, 2] = 2.0
    assert RUNNER.select_actions(
        q1, o2, o3, mask, include_c3=False
    ).tolist() == [1, 1]
    assert RUNNER.select_actions(
        q1, o2, o3, mask, include_c3=True
    ).tolist() == [3, 2]
    zeros = np.zeros_like(q1)
    assert RUNNER.select_actions(
        zeros, zeros, zeros, mask, include_c3=True
    ).tolist() == [0, 1]


@pytest.mark.parametrize(
    ("zr", "hr", "expected"),
    [
        (True, True, "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"),
        (True, False, "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"),
        (False, True, "GO_HR_C3_LEARNABILITY_PREREG_ONLY"),
        (False, False, "STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM"),
    ],
)
def test_ordered_decision_never_uses_observed_magnitude(
    zr: bool, hr: bool, expected: str
) -> None:
    assert RUNNER.ordered_decision(passed_zr=zr, passed_hr=hr) == expected


def _rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for world in RUNNER.WORLD_SEEDS:
        for arm in RUNNER.ARMS:
            for lineage in RUNNER.LINEAGES:
                is_drop = arm == "DROP_C3"
                rows.append(
                    {
                        "world_seed": world,
                        "arm": arm,
                        "initialization_seed": lineage,
                        "total_bits": 100.0 if is_drop else 110.0,
                        "total_energy_j": 10.0,
                        "ratio_of_sums_ee_bits_per_j": 10.0 if is_drop else 11.0,
                        "served_user_steps": 1000,
                        "active_beam_steps": 100 if is_drop else 90,
                        "active_satellite_steps": 30 if is_drop else 29,
                        "c3_legal_spread_count": 0 if is_drop else 10,
                        "supported_positive_target_count": 0 if is_drop else 5,
                        "compatible_action_count": 0 if is_drop else 20,
                        "action_exposure": 0 if is_drop else 2,
                        "changed_actions_compatible": True,
                        "joint_support_passed": True,
                        "method_passed": True,
                        "candidate_specific_identity_passed": True,
                        "mechanics_passed": True,
                    }
                )
    return rows


def _pools(rows: list[dict[str, object]]):
    by_arm = {
        arm: RUNNER._pool([row for row in rows if row["arm"] == arm])
        for arm in RUNNER.ARMS
    }
    by_world = {
        str(world): {
            arm: RUNNER._pool(
                [
                    row
                    for row in rows
                    if row["world_seed"] == world and row["arm"] == arm
                ]
            )
            for arm in RUNNER.ARMS
        }
        for world in RUNNER.WORLD_SEEDS
    }
    return by_arm, by_world


def _gate(rows: list[dict[str, object]], arm: str = "FULL_ZR"):
    by_arm, by_world = _pools(rows)
    return RUNNER._pair_gate(
        label=arm.removeprefix("FULL_"),
        full_arm=arm,
        rows=rows,
        pooled_by_arm=by_arm,
        pooled_by_world_and_arm=by_world,
    )


def test_pair_gate_accepts_only_complete_per_world_support_and_resource_pass() -> None:
    gate = _gate(_rows())
    assert gate["passed"]
    assert gate["pooled"]["relative_delta_ee"] == pytest.approx(0.1)
    assert all(value["positive_lineages"] == 3 for value in gate["by_world"].values())
    assert gate["supported_positive_target_count"] > 0
    assert gate["action_exposure"] > 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("joint_support_passed", False, "expanded current energy support"),
        ("changed_actions_compatible", False, "outside compatibility"),
        ("supported_positive_target_count", 0, "zero supported-positive"),
        ("action_exposure", 0, "zero executed-action exposure"),
        ("served_user_steps", 999, "service guard"),
        ("active_beam_steps", 101, "active-beam guard"),
        ("active_satellite_steps", 31, "active-satellite guard"),
    ],
)
def test_pair_gate_fails_closed_on_each_structural_guard(
    field: str, value: object, message: str
) -> None:
    rows = _rows()
    for row in rows:
        all_worlds = field in {
            "supported_positive_target_count",
            "action_exposure",
        }
        if row["arm"] == "FULL_ZR" and (
            all_worlds or row["world_seed"] == RUNNER.WORLD_SEEDS[0]
        ):
            row[field] = value
    gate = _gate(rows)
    assert not gate["passed"]
    assert any(message in stop for stop in gate["hard_stops"])


def test_pair_gate_requires_two_positive_lineages_inside_each_world() -> None:
    rows = _rows()
    world = RUNNER.WORLD_SEEDS[0]
    losing = set(RUNNER.LINEAGES[:2])
    for row in rows:
        if row["arm"] == "FULL_ZR" and row["world_seed"] == world and row["initialization_seed"] in losing:
            row["total_bits"] = 99.0
            row["ratio_of_sums_ee_bits_per_j"] = 9.9
    gate = _gate(rows)
    assert not gate["passed"]
    assert gate["by_world"][str(world)]["positive_lineages"] == 1
    assert any("fewer than two positive lineages" in stop for stop in gate["hard_stops"])


def test_authority_paths_exist_and_frozen_guard_is_explicit() -> None:
    assert RUNNER.CONTRACT_PATH.is_file()
    assert all(path.is_file() for path in RUNNER.RUNTIME_PATHS)
    assert len(RUNNER.file_sha256(RUNNER_PATH)) == 64
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert 'add_parser("shard")' in source
    assert 'add_parser("merge")' in source
    assert 'add_parser("train")' not in source
    assert 'add_parser("test")' not in source


def test_current_authority_check_rejects_mutually_consistent_stale_shards() -> None:
    expected = {
        "contract_sha256": "a" * 64,
        "runner_file_sha256": "b" * 64,
        "source_authority": {
            "prereg_file_sha256": "c" * 64,
            "prereg_record_digest": "d" * 64,
            "tle_file_set_sha256": "e" * 64,
        },
    }
    RUNNER._assert_current_authority(dict(expected), expected)
    stale = dict(expected)
    stale["runner_file_sha256"] = "f" * 64
    with pytest.raises(RUNNER.V012OracleError, match="current file state"):
        RUNNER._assert_current_authority(stale, expected)


def test_merge_reauthenticates_current_tle_prereg_and_q1_sources() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "assert_contract_frozen()" in source
    assert "screen._frozen_archive(" in source
    assert "read_prereg(prereg_path)" in source
    assert "load_frozen_q1(v03_root, lineage)" in source
    assert '"prereg_file_sha256"' in source
    assert '"tle_file_set_sha256"' in source
    assert "python_source_authority()" in source


def test_python_source_authority_is_complete_and_content_sensitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()
    module = source_root / "module.py"
    module.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(RUNNER, "REPO", tmp_path)
    monkeypatch.setattr(RUNNER, "PYTHON_SOURCE_ROOTS", (source_root,))
    first = RUNNER.python_source_authority()
    assert first["python_source_file_count"] == 1
    assert len(first["python_source_file_set_sha256"]) == 64
    module.write_text("VALUE = 2\n", encoding="utf-8")
    second = RUNNER.python_source_authority()
    assert second["python_source_file_count"] == 1
    assert second["python_source_file_set_sha256"] != first["python_source_file_set_sha256"]


def test_canonical_json_normalizes_only_finite_numpy_scalars() -> None:
    numpy_payload = {
        "bool": np.bool_(True),
        "float": np.float32(1.25),
        "int": np.int64(7),
    }
    python_payload = {"bool": True, "float": 1.25, "int": 7}
    assert RUNNER._canonical_bytes(numpy_payload) == RUNNER._canonical_bytes(
        python_payload
    )
    with pytest.raises(RUNNER.V012OracleError, match="finite canonical JSON"):
        RUNNER._canonical_bytes({"array": np.asarray([1, 2])})
    with pytest.raises(RUNNER.V012OracleError, match="finite canonical JSON"):
        RUNNER._canonical_bytes({"nan": np.float32(np.nan)})
