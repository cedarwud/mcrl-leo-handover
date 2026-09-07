"""W-136 -- frozen mechanics for the V0.10 MONE C3 oracle runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO / ".scratch" / "mone-v010" / "run_v010_mone_c3_oracle.py"
SPEC = importlib.util.spec_from_file_location("run_v010_mone_c3_oracle", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_contract_contains_only_clean_c3_marginal_arms() -> None:
    contract = RUNNER.contract_receipt()
    assert RUNNER.ARMS == ("FULL", "DROP_C3")
    assert contract["arm_heads"] == {
        "FULL": ["Q1", "O2_OPS3", "O3_MONE"],
        "DROP_C3": ["Q1", "O2_OPS3"],
    }
    assert contract["background"] == "MASKED_ARGMAX_Q1_PLUS_O2"
    assert contract["background_shared_at_anchor"] is True
    assert contract["q3_recentered_by_arm"] is False
    assert contract["episode_training"] is False
    assert contract["test_split_opened"] is False


def test_world_field_and_panel_are_frozen_and_arm_independent() -> None:
    assert RUNNER.WORLD_SEED == 2026104601
    assert RUNNER.LINEAGES == (2026092101, 2026092102, 2026092103)
    assert RUNNER.USERS == 100
    assert RUNNER.STEPS_PER_EPISODE == 10
    first = RUNNER.field_for_world()
    second = RUNNER.field_for_world()
    assert first.root_digest == second.root_digest
    assert "arm" in RUNNER.FIELD_EXCLUDES
    assert "initialization_seed" in RUNNER.FIELD_EXCLUDES


def test_masked_argmax_is_unweighted_left_to_right_with_native_ties() -> None:
    mask = np.zeros((2, 28), dtype=np.bool_)
    mask[0, [0, 1, 3]] = True
    mask[1, [1, 2]] = True
    q1 = np.zeros((2, 28), dtype=np.float64)
    o2 = np.zeros_like(q1)
    o3 = np.zeros_like(q1)
    q1[0, [0, 1, 2, 3]] = [1.0, 0.0, 99.0, 1.0]
    q1[1, [0, 1, 2, 3]] = [99.0, 0.0, 1.0, 99.0]
    o2[0, 1] = 2.0
    o2[1, 1] = 1.0
    o3[0, 3] = 3.0
    o3[1, 2] = 2.0
    background = RUNNER.select_actions(q1, o2, o3, mask, include_c3=False)
    full = RUNNER.select_actions(q1, o2, o3, mask, include_c3=True)
    assert background.tolist() == [1, 1]
    assert full.tolist() == [3, 2]

    zeros = np.zeros_like(q1)
    tied = RUNNER.select_actions(zeros, zeros, zeros, mask, include_c3=True)
    assert tied.tolist() == [0, 1]


def test_selector_rejects_empty_or_misaligned_safe_masks() -> None:
    q = np.zeros((2, 28), dtype=np.float64)
    empty = np.zeros((2, 28), dtype=np.bool_)
    empty[0, 0] = True
    with pytest.raises(RUNNER.V010OracleError, match="legal native action"):
        RUNNER.select_actions(q, q, q, empty, include_c3=True)
    with pytest.raises(RUNNER.V010OracleError, match="misaligned"):
        RUNNER.select_actions(q, q[:, :3], q, np.ones_like(q, dtype=np.bool_), include_c3=True)


def test_contract_and_source_paths_are_real_and_hashed() -> None:
    assert RUNNER.CONTRACT_PATH.is_file()
    assert len(RUNNER.file_sha256(RUNNER.CONTRACT_PATH)) == 64
    assert len(RUNNER.file_sha256(RUNNER_PATH)) == 64
    assert all(path.is_file() for path in RUNNER.RUNTIME_PATHS)
