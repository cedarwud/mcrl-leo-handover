"""Regression checks for the offline V0.14-to-Q1 reconstruction audit."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "reconstruct_q1_state_from_v014.py"
SPEC = importlib.util.spec_from_file_location("q1_state_reconstruction", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_layout_reconstruction_uses_binary_satellite_or() -> None:
    """The compact surfaces recover all 228 blocks without producing 2 flags."""

    q2 = np.zeros((1, MODULE.Q2_STATE_DIM), dtype=np.float32)
    q3 = np.zeros((1, MODULE.Q3_STATE_DIM), dtype=np.float32)
    local = q3[:, : MODULE.Q3_LOCAL_WIDTH].reshape(
        1, MODULE.Q3_LOCAL_BLOCKS, MODULE.ACTION_COUNT
    )
    globals_ = q3[:, MODULE.Q3_LOCAL_WIDTH :]

    for block in range(4):
        local[0, block] = np.float32(block + 1)
    local[0, 5] = np.arange(MODULE.ACTION_COUNT, dtype=np.float32) + 10.0
    local[0, 6, 2] = 1.0
    local[0, 7] = np.arange(MODULE.ACTION_COUNT, dtype=np.float32) + 20.0
    local[0, 8, 7] = 1.0  # slot 7 belongs to satellite group 1 (actions 7..13)
    local[0, 9] = np.float32(3.0)
    globals_[0, :4] = np.arange(4, dtype=np.float32) + 30.0

    recovered = MODULE.reconstruct_q1_state(q2, q3)
    recovered_blocks = recovered[:, : 8 * MODULE.ACTION_COUNT].reshape(
        1, 8, MODULE.ACTION_COUNT
    )

    np.testing.assert_array_equal(recovered_blocks[0, :4], local[0, :4])
    expected_load = local[0, 9].copy()
    expected_load[7] += 1.0 / MODULE.USER_COUNT
    np.testing.assert_array_equal(recovered_blocks[0, 4], expected_load)
    np.testing.assert_array_equal(recovered_blocks[0, 5], local[0, 5])

    expected_satellite = np.zeros(MODULE.ACTION_COUNT, dtype=np.float32)
    expected_satellite[7:14] = 1.0  # focal continuation in group 1
    expected_satellite[2] = 1.0  # non-focal active-satellite signal
    np.testing.assert_array_equal(recovered_blocks[0, 6], expected_satellite)
    assert set(np.unique(recovered_blocks[0, 6])) == {0.0, 1.0}
    np.testing.assert_array_equal(recovered_blocks[0, 7], local[0, 7])
    np.testing.assert_array_equal(recovered[:, 8 * MODULE.ACTION_COUNT :], globals_[:, :4])


def test_all_authenticated_shards_reproduce_frozen_q1_surface() -> None:
    """Re-run the small offline audit over every allowed TRAIN/internal shard."""

    result = MODULE.run_audit()
    assert result["status"] == "PASS_EXACT_Q1_STATE_RECONSTRUCTION"
    assert result["scope"]["shard_count"] == 21
    assert result["scope"]["row_count"] == 21_000
    assert result["scope"]["test_split_opened"] is False
    assert result["scope"]["simulator_run"] is False
    assert result["scope"]["training_run"] is False
    assert result["pooled"]["action_argmax_agreement_count"] == 21_000
    assert result["pooled"]["action_argmax_row_count"] == 21_000
    assert result["pooled"]["action_argmax_agreement_fraction"] == 1.0
    assert result["pooled"]["q_value_absolute_max"] <= MODULE.MAX_ABS_TOLERANCE
    assert (
        result["pooled"]["q_value_relative_pointwise_max"]
        <= MODULE.MAX_POINTWISE_RELATIVE_TOLERANCE
    )
    assert all(shard["pass"] for shard in result["shards"])


def test_recorded_result_has_same_decision() -> None:
    """The checked-in receipt records the same bounded, non-efficacy claim."""

    result = json.loads((HERE / "RESULT.json").read_text(encoding="ascii"))
    assert result["status"] == "PASS_EXACT_Q1_STATE_RECONSTRUCTION"
    assert result["decision"]["source_regeneration_required"] is False
    assert result["claim_ceiling"] == "OFFLINE_Q1_STATE_RECONSTRUCTION_ONLY_NO_EE_EFFICACY"
