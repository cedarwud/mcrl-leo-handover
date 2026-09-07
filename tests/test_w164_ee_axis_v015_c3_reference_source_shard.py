"""W-164 -- V0.15-R source-shard storage and causal helper boundaries."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v015-c3-reference-gate"
    / "run_v015_reference_source_shard.py"
)
SPEC = importlib.util.spec_from_file_location("v015_reference_source_shard", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def _source_arrays(*, anchors: int = 2) -> dict[str, np.ndarray | int | float | str]:
    rows = anchors * RUNNER.USERS * len(RUNNER.CONTEXT_CODES)
    contexts = np.tile(
        np.concatenate(
            [
                np.full(RUNNER.USERS, code, dtype=np.int64)
                for code in RUNNER.CONTEXT_CODES
            ]
        ),
        anchors,
    )
    users = np.tile(
        np.arange(RUNNER.USERS, dtype=np.int64), len(RUNNER.CONTEXT_CODES)
    )
    users = np.tile(users, anchors)
    step_indices = np.repeat(
        np.arange(anchors, dtype=np.int64),
        RUNNER.USERS * len(RUNNER.CONTEXT_CODES),
    )
    anchor_names = [chr(ord("a") + index) * 64 for index in range(anchors)]
    anchor_sha = np.repeat(
        np.asarray(anchor_names, dtype="S64"),
        RUNNER.USERS * len(RUNNER.CONTEXT_CODES),
    )
    masks = np.zeros((rows, RUNNER.ACTION_DIM), dtype=np.bool_)
    masks[:, :2] = True
    references = np.zeros(rows, dtype=np.int64)
    compatibility = np.zeros_like(masks)
    compatibility[:, :2] = True
    q1 = np.zeros((rows, RUNNER.ACTION_DIM), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q1[:, 0] = 1.0
    q2[:, 1] = 0.5
    return {
        "q3_states": np.zeros(
            (rows, RUNNER.V015_C3_REFERENCE_STATE_DIM), dtype=np.float32
        ),
        "action_masks": masks,
        "q1_values": q1,
        "learned_q2_values": q2,
        "z3_target_bits": np.zeros_like(q1),
        "q3_compatibility": compatibility,
        "context_codes": contexts,
        "reference_actions": references,
        "source_seeds": np.full(rows, 2026110001, dtype=np.int64),
        "lineages": np.full(rows, 2026092101, dtype=np.int64),
        "anchor_sha256s": anchor_sha,
        "step_indices": step_indices,
        "user_indices": users,
        "world_seed": 2026110001,
        "lineage": 2026092101,
        "field_root_digest": "f" * 64,
        "kappa_bits": float(RUNNER.OPS3_KAPPA_BITS),
        "q1_checkpoint_sha256": "1" * 64,
        "q2_checkpoint_sha256": "2" * 64,
        "q1_parameter_sha256": "3" * 64,
        "q2_parameter_sha256": "4" * 64,
    }


def _source(*, anchors: int = 2):
    return RUNNER.assemble_source_arrays(**_source_arrays(anchors=anchors))


def test_source_schema_roundtrip_and_write_once(tmp_path: Path) -> None:
    source = _source()
    output = tmp_path / "source"
    receipt = RUNNER.write_source_shard(
        output,
        source,
        metadata_extra={
            "test_receipt_note": "synthetic-roundtrip",
            "q1_checkpoint": {
                "checkpoint_sha256": "1" * 64,
                "parameter_sha256": "3" * 64,
            },
            "q2_checkpoint": {
                "checkpoint_sha256": "2" * 64,
                "parameter_sha256": "4" * 64,
            },
        },
    )
    assert receipt["arrays_sha256"] == source.arrays_sha256()
    metadata = json.loads((output / RUNNER.METADATA_FILENAME).read_text())
    assert metadata["steps"] == 2
    assert metadata["observed_step_indices"] == [0, 1]
    assert "observed_step_indices=0,1" in (
        output / RUNNER.SHA256_FILENAME
    ).read_text()
    restored = RUNNER.read_source_shard(output)
    assert restored.verify() == source.arrays_sha256()
    for name in RUNNER.ARRAY_NAMES:
        np.testing.assert_array_equal(
            restored.arrays_as_mapping()[name], source.arrays_as_mapping()[name]
        )
    with pytest.raises(RUNNER.V015ReferenceSourceError, match="overwrite"):
        RUNNER.write_source_shard(output, source)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("split", "TEST", "split"),
        ("test_split_opened", True, "test_split_opened"),
        ("contract_sha256", "0" * 64, "contract digest"),
        ("q3_state_dim", 287, "dimension"),
        ("field_component", "wrong", "field component"),
        ("q1_checkpoint_sha256", "", "q1_checkpoint_sha256"),
    ),
)
def test_read_rejects_stale_or_unauthenticated_metadata(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    source = _source()
    output = tmp_path / "source"
    RUNNER.write_source_shard(
        output,
        source,
        metadata_extra={
            "q1_checkpoint": {
                "checkpoint_sha256": "1" * 64,
                "parameter_sha256": "3" * 64,
            },
            "q2_checkpoint": {
                "checkpoint_sha256": "2" * 64,
                "parameter_sha256": "4" * 64,
            },
        },
    )
    path = output / RUNNER.METADATA_FILENAME
    metadata = json.loads(path.read_text())
    body = {key: item for key, item in metadata.items() if key != "metadata_sha256"}
    body[field] = value
    metadata[field] = value
    metadata["metadata_sha256"] = RUNNER.canonical_sha256(body)
    path.write_text(json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
    with pytest.raises(RUNNER.V015ReferenceSourceError, match=message):
        RUNNER.read_source_shard(output)


def test_context_rows_are_balanced_and_in_declared_order() -> None:
    source = _source(anchors=3)
    assert source.rows == 3 * RUNNER.USERS * 3
    groups = RUNNER._ordered_anchor_groups(
        context_codes=source.context_codes,
        source_seeds=source.source_seeds,
        anchor_sha256s=source.anchor_sha256s,
        step_indices=source.step_indices,
        user_indices=source.user_indices,
    )
    assert [(world, step) for world, _anchor, step in groups] == [
        (2026110001, 0),
        (2026110001, 1),
        (2026110001, 2),
    ]
    values = _source_arrays()
    values["context_codes"] = np.asarray(values["context_codes"]).copy()
    values["context_codes"][0], values["context_codes"][RUNNER.USERS] = (
        values["context_codes"][RUNNER.USERS],
        values["context_codes"][0],
    )
    with pytest.raises(RUNNER.V015ReferenceSourceError, match="ordered"):
        RUNNER.assemble_source_arrays(**values)


def test_detached_context_reference_helpers_use_native_mask_and_lowest_tie() -> None:
    q1 = np.zeros((2, RUNNER.ACTION_DIM), dtype=np.float64)
    q2 = np.zeros_like(q1)
    masks = np.zeros_like(q1, dtype=np.bool_)
    masks[:, :3] = True
    q1[0, 0] = 3.0
    q1[1, 1] = 3.0
    q2[0, 1] = 4.0
    q2[1, 0] = 4.0
    bases = RUNNER.context_base_values(q1, q2)
    references = RUNNER.context_reference_actions(q1, q2, masks)
    assert set(bases) == {12, 1, 2}
    np.testing.assert_array_equal(references[12], np.asarray([1, 0]))
    np.testing.assert_array_equal(references[1], np.asarray([0, 1]))
    np.testing.assert_array_equal(references[2], np.asarray([1, 0]))
    assert not np.shares_memory(bases[12], q1)
    assert not np.shares_memory(bases[12], q2)


def test_current_power_helper_is_h0_recurrence_not_future_surface() -> None:
    current = np.zeros((2, RUNNER.ACTION_DIM), dtype=np.float64)
    starts = np.zeros_like(current)
    masks = np.zeros_like(current, dtype=np.bool_)
    masks[:, :2] = True
    current[:, 0] = 1.0
    current[:, 1] = 0.5
    starts[:, 0] = 1.0
    starts[:, 1] = 2.0
    required, opening = RUNNER.current_required_power_and_opening(
        current_gain_linear=current,
        segment_start_gain_linear=starts,
        action_masks=masks,
        p0_w=1.0,
        pmax_w=4.0,
    )
    np.testing.assert_allclose(required[:, :2], np.asarray([[1.0, 4.0], [1.0, 4.0]]))
    assert np.all(opening[:, :2])
    assert np.all(required[:, 2:] == 0.0)
    assert np.all(~opening[:, 2:])


@pytest.mark.parametrize(
    ("done", "step_index", "steps", "valid"),
    (
        (False, 2, 3, True),   # partial smoke may stop before the natural boundary.
        (True, 2, 3, True),    # a partial smoke may also end exactly at its request.
        (True, 9, 10, True),   # canonical harvest must end on step nine.
        (True, 2, 10, False),  # early natural termination is a hard failure.
        (False, 9, 10, False), # canonical truncation is a hard failure.
    ),
)
def test_harvest_step_boundary_preserves_partial_smoke_and_guards_canonical(
    done: bool, step_index: int, steps: int, valid: bool
) -> None:
    if valid:
        RUNNER.enforce_harvest_step_boundary(
            done=done, step_index=step_index, steps=steps
        )
    else:
        with pytest.raises(RUNNER.V015ReferenceSourceError):
            RUNNER.enforce_harvest_step_boundary(
                done=done, step_index=step_index, steps=steps
            )


def test_source_runner_does_not_hardcode_reference_block_offsets() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8")
    # Layout ownership belongs to the public V0.15 encoder.  The harvester
    # records its returned state matrix and never slices the 371-D vector.
    assert "V015_C3_REFERENCE_BEAM_START" not in text
    assert "V015_C3_REFERENCE_GLOBAL_START" not in text
    assert "encode_ee_axis_v015_c3_reference_state" in text
    # The runner delegates counterfactual physics to the authenticated live
    # measurement helper; it must not call the evaluator directly or create a
    # second ad-hoc physics path.
    assert "evaluate_actions(" not in text
    assert "environment.step(" in text
    assert "canonical ten-step harvest did not reach the episode boundary" in text


def test_source_runner_cli_parser_accepts_declared_harvest_arguments() -> None:
    args = RUNNER._parser().parse_args(
        [
            "harvest",
            "--world-seed",
            "2026110001",
            "--lineage",
            "2026092101",
            "--output",
            "/tmp/v015-reference-source-parser-test",
            "--steps",
            "1",
        ]
    )
    assert args.world_seed == 2026110001
    assert args.lineage == 2026092101
    assert args.steps == 1
