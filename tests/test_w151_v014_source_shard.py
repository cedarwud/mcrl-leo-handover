"""W-151 -- compact V0.14 source-shard assembly and receipt boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO / ".scratch" / "multi-catfish-v014-learner" / "run_v014_source_shard.py"
SPEC = importlib.util.spec_from_file_location("mcrl_v014_source_shard", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def _arrays(*, mismatch_masks: bool = False) -> dict[str, object]:
    rows = 4
    q2_masks = np.zeros((rows, 28), dtype=np.bool_)
    q2_masks[:, [0, 2, 5]] = True
    q3_masks = q2_masks.copy()
    if mismatch_masks:
        q3_masks[0, 7] = True
    q2_targets = np.zeros((rows, 28), dtype=np.float64)
    q2_targets[:, 0] = [1.0, 2.0, 3.0, 4.0]
    q2_targets[:, 2] = [5.0, 6.0, 7.0, 8.0]
    q3_targets = np.zeros((rows, 28), dtype=np.float64)
    q3_targets[:, 2] = [-3.0, 2.0, -1.0, 4.0]
    compatibility = np.zeros((rows, 28), dtype=np.bool_)
    compatibility[:, [0, 2]] = True
    return {
        "q1_values": np.arange(rows * 28, dtype=np.float64).reshape(rows, 28),
        "q2_states": np.zeros((rows, RUNNER.V014_Q2_STATE_DIM), dtype=np.float32),
        "q2_masks": q2_masks,
        "q2_reference_actions": np.zeros(rows, dtype=np.int64),
        "q2_target_bits": q2_targets,
        "q3_states": np.zeros((rows, RUNNER.V014_Q3_STATE_DIM), dtype=np.float32),
        "q3_masks": q3_masks,
        "q3_reference_actions": np.zeros(rows, dtype=np.int64),
        "q3_target_bits": q3_targets,
        "q3_compatibility": compatibility,
        "source_seeds": np.full(rows, 77, dtype=np.int64),
        "anchor_sha256s": np.asarray(["a" * 64, "a" * 64, "b" * 64, "b" * 64], dtype="S64"),
        "step_indices": np.asarray([0, 0, 1, 1], dtype=np.int64),
        "user_indices": np.asarray([0, 1, 0, 1], dtype=np.int64),
        "world_seed": 77,
        "lineage": 88,
        "field_root_digest": "c" * 64,
        "kappa_bits": 10.0,
    }


def test_compact_assembly_keeps_all_signed_teacher_surfaces() -> None:
    source = RUNNER.assemble_source_arrays(**_arrays())
    assert source.q1_values.shape == (4, 28)
    assert source.q2_states.shape == (4, 448)
    assert source.q3_states.shape == (4, 287)
    assert source.q3_target_bits[:, 2].tolist() == [-3.0, 2.0, -1.0, 4.0]
    assert source.q2_target_bits[:, 0].tolist() == [1.0, 2.0, 3.0, 4.0]
    assert source.verify() == source.arrays_sha256()
    assert not source.q2_states.flags.writeable
    assert not source.q3_target_bits.flags.writeable


def test_write_read_roundtrip_uses_standard_npz_keys_without_pickle(tmp_path: Path) -> None:
    source = RUNNER.assemble_source_arrays(**_arrays())
    output = tmp_path / "source-shard"
    receipt = RUNNER.write_source_shard(output, source)
    assert Path(receipt["npz"]).name == "source.npz"
    assert Path(receipt["metadata"]).name == "metadata.json"
    with np.load(output / "source.npz", allow_pickle=False) as loaded:
        assert set(loaded.files) == set((*RUNNER.ARRAY_NAMES, "kappa_bits"))
        assert loaded["q1_values"].shape == (4, 28)
        assert loaded["q3_compatibility"].dtype == np.bool_
        assert loaded["anchor_sha256s"].dtype.kind == "S"
    restored = RUNNER.read_source_shard(output)
    assert restored.arrays_sha256() == source.arrays_sha256()
    np.testing.assert_array_equal(restored.q3_target_bits, source.q3_target_bits)
    np.testing.assert_array_equal(restored.q1_values, source.q1_values)


def test_write_is_write_once(tmp_path: Path) -> None:
    source = RUNNER.assemble_source_arrays(**_arrays())
    output = tmp_path / "source-shard"
    RUNNER.write_source_shard(output, source)
    with pytest.raises(RUNNER.V014SourceShardError, match="overwrite"):
        RUNNER.write_source_shard(output, source)


def test_validation_rejects_mask_mismatch_and_q3_support_outside_mask() -> None:
    with pytest.raises(RUNNER.V014SourceShardError, match="masks disagree"):
        RUNNER.assemble_source_arrays(**_arrays(mismatch_masks=True))
    bad = _arrays()
    bad["q3_compatibility"] = np.eye(28, dtype=np.bool_)[:4]
    with pytest.raises(RUNNER.V014SourceShardError, match="outside"):
        RUNNER.assemble_source_arrays(**bad)


def test_validation_rejects_noncanonical_anchor_and_illegal_reference() -> None:
    bad_anchor = _arrays()
    bad_anchor["anchor_sha256s"] = np.asarray(["not-an-anchor"] * 4, dtype="U13")
    with pytest.raises(RUNNER.V014SourceShardError, match="anchor_sha256s"):
        RUNNER.assemble_source_arrays(**bad_anchor)
    bad_reference = _arrays()
    bad_reference["q3_reference_actions"] = np.full(4, 7, dtype=np.int64)
    with pytest.raises(RUNNER.V014SourceShardError, match="reference action"):
        RUNNER.assemble_source_arrays(**bad_reference)
