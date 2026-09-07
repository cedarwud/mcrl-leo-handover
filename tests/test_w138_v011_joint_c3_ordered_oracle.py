"""W-138 -- frozen control-plane mechanics for the V0.11 joint-C3 gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "joint-c3-v011"
    / "run_v011_joint_c3_ordered_oracle.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_v011_joint_c3_ordered_oracle", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_contract_freezes_five_arms_and_predeclared_order() -> None:
    contract = RUNNER.contract_receipt()
    assert RUNNER.ARMS == (
        "DROP_C3",
        "FULL_M1D",
        "FULL_AP",
        "DIAG_O_DROP",
        "DIAG_O_FULL",
    )
    assert contract["arm_heads"] == {
        "DROP_C3": ["Q1", "O2_OPS3"],
        "FULL_M1D": ["Q1", "O2_OPS3", "O3_M1D"],
        "FULL_AP": ["Q1", "O2_OPS3", "O3_AP_MONE"],
        "DIAG_O_DROP": ["O1_EXACT", "O2_OPS3"],
        "DIAG_O_FULL": ["O1_EXACT", "O2_OPS3", "O3_EXACT"],
    }
    assert contract["candidate_order"] == ["AP_MONE", "M1D"]
    assert contract["max_complete_gauss_seidel_sweeps"] == 5
    assert contract["gauss_seidel_user_order"] == list(range(100))
    assert contract["episode_training"] is False
    assert contract["test_split_opened"] is False


@pytest.mark.parametrize(
    ("a", "m", "o", "expected"),
    [
        (True, True, True, "GO_AP_MONE_LEARNABILITY_PREREG_ONLY"),
        (True, True, False, "GO_AP_MONE_LEARNABILITY_PREREG_ONLY"),
        (True, False, True, "GO_AP_MONE_LEARNABILITY_PREREG_ONLY"),
        (False, True, True, "GO_M1D_LEARNABILITY_PREREG_ONLY"),
        (False, True, False, "GO_M1D_LEARNABILITY_PREREG_ONLY"),
        (True, False, False, "INCONSISTENT_AP_ONLY_NO_LEARNER_REVIEW"),
        (False, False, True, "C1_ALIGNMENT_BLOCKS_C3_NO_LEARNER"),
        (False, False, False, "JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED"),
    ],
)
def test_ordered_decision_never_compares_observed_magnitudes(
    a: bool, m: bool, o: bool, expected: str
) -> None:
    assert RUNNER.ordered_decision(
        passed_ap=a, passed_m1d=m, passed_o=o
    ) == expected


def test_world_field_and_panel_are_frozen_and_arm_independent() -> None:
    assert RUNNER.WORLD_SEED == 2026104701
    assert RUNNER.LINEAGES == (2026092101, 2026092102, 2026092103)
    assert RUNNER.USERS == 100
    assert RUNNER.STEPS_PER_EPISODE == 10
    assert RUNNER.MAX_SWEEPS == 5
    assert RUNNER.field_for_world().root_digest == RUNNER.field_for_world().root_digest
    assert "arm" in RUNNER.FIELD_EXCLUDES
    assert "initialization_seed" in RUNNER.FIELD_EXCLUDES
    order = RUNNER.permutation_for_step(0)
    assert sorted(order.tolist()) == list(range(100))
    np.testing.assert_array_equal(order, RUNNER.permutation_for_step(0))
    assert not np.array_equal(order, RUNNER.permutation_for_step(1))


def test_masked_argmax_is_unweighted_and_uses_native_tie_break() -> None:
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


def test_selector_and_authority_paths_fail_closed() -> None:
    q = np.zeros((2, 28), dtype=np.float64)
    empty = np.zeros((2, 28), dtype=np.bool_)
    empty[0, 0] = True
    with pytest.raises(RUNNER.V011OracleError, match="legal native action"):
        RUNNER.select_actions(q, q, q, empty, include_c3=True)
    assert RUNNER.CONTRACT_PATH.is_file()
    assert len(RUNNER.file_sha256(RUNNER.CONTRACT_PATH)) == 64
    assert len(RUNNER.file_sha256(RUNNER_PATH)) == 64
    assert all(path.is_file() for path in RUNNER.RUNTIME_PATHS)


def test_ap_execution_receipt_records_distances_and_executed_credit() -> None:
    mask = np.zeros((2, RUNNER.NUM_ACTIONS), dtype=np.bool_)
    mask[:, [0, 1]] = True
    proposal = np.asarray([1, 0], dtype=np.int64)
    background = np.asarray([0, 0], dtype=np.int64)
    selected = np.asarray([0, 1], dtype=np.int64)
    z1 = np.zeros_like(mask, dtype=np.float64)
    z3 = np.zeros_like(mask, dtype=np.float64)
    z1[0, 0], z3[0, 0] = 2.0, 3.0
    z1[1, 1], z3[1, 1] = -1.0, 4.0
    surface = SimpleNamespace(
        proposal_actions=proposal,
        z1_bits=z1,
        z3_bits=z3,
    )

    receipt = RUNNER._ap_execution_receipt(
        surface, background, selected, mask, fixed_lambda_surplus_bits=10.0
    )

    assert receipt == {
        "proposal_flips_from_background": 1,
        "executed_flips_from_background": 1,
        "executed_flips_from_proposal": 2,
        "executed_antithetic_credited_sum_bits": 8.0,
        "executed_joint_surplus_bits": 10.0,
        "executed_joint_minus_credited_bits": 2.0,
    }


def test_ap_execution_receipt_rejects_unsafe_executed_action() -> None:
    mask = np.zeros((1, RUNNER.NUM_ACTIONS), dtype=np.bool_)
    mask[0, 0] = True
    surface = SimpleNamespace(
        proposal_actions=np.asarray([0], dtype=np.int64),
        z1_bits=np.zeros((1, RUNNER.NUM_ACTIONS), dtype=np.float64),
        z3_bits=np.zeros((1, RUNNER.NUM_ACTIONS), dtype=np.float64),
    )
    with pytest.raises(RUNNER.V011OracleError, match="unsafe action"):
        RUNNER._ap_execution_receipt(
            surface,
            np.asarray([0], dtype=np.int64),
            np.asarray([1], dtype=np.int64),
            mask,
            fixed_lambda_surplus_bits=0.0,
        )
