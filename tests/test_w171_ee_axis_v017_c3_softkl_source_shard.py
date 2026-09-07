"""W-171 -- V0.17 fresh TRAIN source-shard storage and provenance seams."""

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
    / "multi-catfish-v017-c3-softkl-gate"
    / "run_v017_softkl_source_shard.py"
)
SPEC = importlib.util.spec_from_file_location(
    "mcrl_v017_softkl_source_shard_w171", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def _source_arrays(
    *,
    world_seed: int | None = None,
    lineage: int | None = None,
    anchors: int = 2,
) -> dict[str, np.ndarray | int | float | str]:
    """Build a complete, ordered synthetic shard with one-action rows."""

    world = RUNNER.TRAIN_WORLD_SEEDS[0] if world_seed is None else int(world_seed)
    source_lineage = RUNNER.LINEAGES[0] if lineage is None else int(lineage)
    rows_per_anchor = RUNNER.USERS * len(RUNNER.CONTEXT_CODES)
    rows = anchors * rows_per_anchor
    context_group = np.concatenate(
        [
            np.full(RUNNER.USERS, code, dtype=np.int64)
            for code in RUNNER.CONTEXT_CODES
        ]
    )
    contexts = np.tile(context_group, anchors)
    users = np.tile(
        np.tile(np.arange(RUNNER.USERS, dtype=np.int64), len(RUNNER.CONTEXT_CODES)),
        anchors,
    )
    step_indices = np.repeat(
        np.arange(anchors, dtype=np.int64), rows_per_anchor
    )
    anchor_sha = np.repeat(
        np.asarray(
            [chr(ord("a") + index) * 64 for index in range(anchors)],
            dtype="S64",
        ),
        rows_per_anchor,
    )

    masks = np.zeros((rows, RUNNER.ACTION_DIM), dtype=np.bool_)
    masks[:, :3] = True
    # User zero in every context/anchor is deliberately a one-action row.  It
    # must remain in both the source closure and the successor's full-row loss.
    for anchor in range(anchors):
        for context_offset in range(len(RUNNER.CONTEXT_CODES)):
            masks[
                anchor * rows_per_anchor
                + context_offset * RUNNER.USERS
            ] = False
            masks[
                anchor * rows_per_anchor
                + context_offset * RUNNER.USERS,
                1,
            ] = True

    q1 = np.zeros((rows, RUNNER.ACTION_DIM), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q1[:, 0] = 2.0
    q1[:, 1] = 1.0
    q2[:, 1] = 2.0
    q2[:, 2] = 1.0
    z3 = np.zeros_like(q1)
    compatibility = masks.copy()
    references = np.empty(rows, dtype=np.int64)
    for index, code in enumerate(contexts.tolist()):
        if np.count_nonzero(masks[index]) == 1:
            references[index] = 1
        elif code == 1:
            references[index] = 0
        else:
            references[index] = 1

    return {
        "q3_states": np.zeros(
            (rows, RUNNER.V016_C3_ORIGIN_STATE_DIM), dtype=np.float32
        ),
        "action_masks": masks,
        "q1_values": q1,
        "learned_q2_values": q2,
        "z3_target_bits": z3,
        "q3_compatibility": compatibility,
        "context_codes": contexts,
        "reference_actions": references,
        "source_seeds": np.full(rows, world, dtype=np.int64),
        "lineages": np.full(rows, source_lineage, dtype=np.int64),
        "anchor_sha256s": anchor_sha,
        "step_indices": step_indices,
        "user_indices": users,
        "world_seed": world,
        "lineage": source_lineage,
        "field_root_digest": "f" * 64,
        "kappa_bits": float(RUNNER.OPS3_KAPPA_BITS),
        "q1_checkpoint_sha256": "1" * 64,
        "q2_checkpoint_sha256": "2" * 64,
        "q1_parameter_sha256": "3" * 64,
        "q2_parameter_sha256": "4" * 64,
    }


def _source(*, anchors: int = 2, world_seed: int | None = None):
    return RUNNER.assemble_source_arrays(
        **_source_arrays(anchors=anchors, world_seed=world_seed)
    )


def _metadata_extra() -> dict[str, object]:
    return {
        "source_runner_sha256": RUNNER.file_sha256(RUNNER_PATH),
        "q1_checkpoint": {
            "checkpoint_sha256": "1" * 64,
            "parameter_sha256": "3" * 64,
        },
        "q2_checkpoint": {
            "checkpoint_sha256": "2" * 64,
            "parameter_sha256": "4" * 64,
        },
    }


def test_v017_schema_seed_and_contract_bindings_are_new_and_frozen() -> None:
    assert RUNNER.SOURCE_SCHEMA == "multi-catfish-mcrl-v017-c3-softkl-gate-source-v1"
    assert RUNNER.SOURCE_SCHEMA_VERSION == 1
    assert tuple(RUNNER.TRAIN_WORLD_SEEDS) == (
        2026112001,
        2026112002,
        2026112003,
        2026112004,
        2026112005,
        2026112006,
    )
    assert tuple(RUNNER.LINEAGES) == (2026092101, 2026092102, 2026092103)
    assert RUNNER.FIELD_COMPONENT == "MCRL_V017_C3_SOFTKL_GATE_V1"
    assert RUNNER.validate_frozen_contract() is None
    assert RUNNER.file_sha256(RUNNER.CONTRACT_PATH) == RUNNER.CONTRACT_SHA256
    receipt = RUNNER.CONTRACT_RECEIPT_PATH.read_text(encoding="ascii").split()
    assert receipt and receipt[0] == RUNNER.CONTRACT_SHA256


def test_source_roundtrip_preserves_full_rows_and_write_once_boundary(
    tmp_path: Path,
) -> None:
    source = _source()
    output = tmp_path / "source"
    receipt = RUNNER.write_source_shard(
        output,
        source,
        metadata_extra=_metadata_extra(),
    )
    assert receipt["arrays_sha256"] == source.arrays_sha256()
    metadata = json.loads(
        (output / RUNNER.METADATA_FILENAME).read_text(encoding="ascii")
    )
    assert metadata["schema"] == RUNNER.SOURCE_SCHEMA
    assert metadata["split"] == "TRAIN"
    assert metadata["q3_state_schema"] == RUNNER.V016_C3_ORIGIN_STATE_SCHEMA
    assert metadata["q3_state_dim"] == RUNNER.V016_C3_ORIGIN_STATE_DIM == 402
    assert metadata["row_semantics"] == "one-user-anchor-context-native-zr-surface"
    assert metadata["row_order"] == "anchor-then-h-12-1-2-then-user-ascending"
    assert metadata["test_split_opened"] is False
    assert metadata["episode_training"] is False
    assert metadata["learner_update"] is False
    assert metadata["observed_step_indices"] == [0, 1]
    assert "observed_step_indices=0,1" in (
        output / RUNNER.SHA256_FILENAME
    ).read_text(encoding="ascii")

    restored = RUNNER.read_source_shard(output)
    assert restored.verify() == source.arrays_sha256()
    for name in RUNNER.ARRAY_NAMES:
        np.testing.assert_array_equal(
            restored.arrays_as_mapping()[name], source.arrays_as_mapping()[name]
        )
        assert not np.asarray(getattr(restored, name)).flags.writeable
    with pytest.raises(RUNNER.V017SoftKLSourceError, match="overwrite"):
        RUNNER.write_source_shard(output, source)


def test_source_is_balanced_in_declared_order_and_keeps_one_action_rows() -> None:
    source = _source(anchors=3)
    assert source.rows == 3 * RUNNER.USERS * len(RUNNER.CONTEXT_CODES)
    counts = {
        code: int(np.count_nonzero(source.context_codes == code))
        for code in RUNNER.CONTEXT_CODES
    }
    assert counts == {12: 300, 1: 300, 2: 300}
    assert int(np.count_nonzero(np.sum(source.action_masks, axis=1) == 1)) == 9
    assert np.all(source.action_masks[np.arange(source.rows), source.reference_actions])
    assert source.observed_step_indices() == (0, 1, 2)
    groups = RUNNER._ordered_anchor_groups(
        context_codes=source.context_codes,
        source_seeds=source.source_seeds,
        anchor_sha256s=source.anchor_sha256s,
        step_indices=source.step_indices,
        user_indices=source.user_indices,
    )
    assert [(world, step) for world, _anchor, step in groups] == [
        (RUNNER.TRAIN_WORLD_SEEDS[0], 0),
        (RUNNER.TRAIN_WORLD_SEEDS[0], 1),
        (RUNNER.TRAIN_WORLD_SEEDS[0], 2),
    ]

    values = _source_arrays(anchors=2)
    contexts = np.asarray(values["context_codes"]).copy()
    contexts[0], contexts[RUNNER.USERS] = contexts[RUNNER.USERS], contexts[0]
    values["context_codes"] = contexts
    with pytest.raises(RUNNER.V017SoftKLSourceError, match="ordered"):
        RUNNER.assemble_source_arrays(**values)


def test_context_reference_helpers_materialize_detached_native_mask_argmax() -> None:
    q1 = np.zeros((2, RUNNER.ACTION_DIM), dtype=np.float64)
    q2 = np.zeros_like(q1)
    masks = np.zeros_like(q1, dtype=np.bool_)
    masks[:, :3] = True
    masks[1] = False
    masks[1, 1] = True
    q1[0, 0], q1[0, 1] = 3.0, 1.0
    q1[1, 0], q1[1, 1] = 3.0, 1.0
    q2[0, 1], q2[0, 2] = 4.0, 2.0
    q2[1, 1], q2[1, 2] = 4.0, 2.0
    bases = RUNNER.context_base_values(q1, q2)
    references = RUNNER.context_reference_actions(q1, q2, masks)
    assert set(bases) == {12, 1, 2}
    np.testing.assert_array_equal(references[12], [1, 1])
    np.testing.assert_array_equal(references[1], [0, 1])
    np.testing.assert_array_equal(references[2], [1, 1])
    assert not np.shares_memory(bases[12], q1)
    assert not np.shares_memory(bases[1], q1)
    assert not np.shares_memory(bases[2], q2)


def test_source_authentication_rejects_npz_or_metadata_digest_tampering(
    tmp_path: Path,
) -> None:
    source = _source(anchors=1)
    output = tmp_path / "source"
    RUNNER.write_source_shard(output, source, metadata_extra=_metadata_extra())

    npz = output / RUNNER.NPZ_FILENAME
    npz.write_bytes(npz.read_bytes() + b"tampered")
    with pytest.raises(RUNNER.V017SoftKLSourceError, match="NPZ digest"):
        RUNNER.read_source_shard(output)

    output = tmp_path / "metadata-tampered"
    RUNNER.write_source_shard(output, source, metadata_extra=_metadata_extra())
    metadata_path = output / RUNNER.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="ascii"))
    metadata["field_component"] = "MCRL_V016_ORIGIN_GATE"
    metadata_path.write_text(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="ascii",
    )
    with pytest.raises(RUNNER.V017SoftKLSourceError, match="metadata digest"):
        RUNNER.read_source_shard(output)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("split", "TEST", "split"),
        ("test_split_opened", True, "test_split_opened"),
        ("contract_sha256", "0" * 64, "contract digest"),
        ("q3_state_dim", 287, "dimension"),
        ("field_component", "MCRL_V016_ORIGIN_GATE", "field component"),
    ),
)
def test_source_metadata_boundary_is_rejected_before_payload_use(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    source = _source(anchors=1)
    output = tmp_path / "source"
    RUNNER.write_source_shard(output, source, metadata_extra=_metadata_extra())
    metadata_path = output / RUNNER.METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="ascii"))
    body = {key: item for key, item in metadata.items() if key != "metadata_sha256"}
    body[field] = value
    metadata[field] = value
    metadata["metadata_sha256"] = RUNNER.canonical_sha256(body)
    metadata_path.write_text(
        json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="ascii",
    )
    # Semantic boundaries are checked before the NPZ is opened.  Recomputing
    # metadata_sha256 alone cannot turn stale V0.17 fields into valid source.
    with pytest.raises(RUNNER.V017SoftKLSourceError, match=message):
        RUNNER.read_source_shard(output)


def test_source_runner_owns_new_namespace_and_never_opens_test() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8")
    assert "multi-catfish-mcrl-v017-c3-softkl-gate-source-v1" in text
    assert "MCRL_V017_C3_SOFTKL_GATE_V1" in text
    assert "split=\"TRAIN\"" not in text  # metadata is constructed as a field
    assert '"split": "TRAIN"' in text
    assert '"test_split_opened": False' in text
    assert '"episode_training": False' in text


def test_keyed_fading_is_bound_before_step_zero_observation_is_created() -> None:
    """The fresh world's common field must own reset-time fading as well."""

    text = RUNNER_PATH.read_text(encoding="utf-8")
    bind = text.index("step_env._fading_field = expected_field")
    reset = text.index("environment.reset(env_rng, mobility_rng)")
    assert bind < reset
