"""W-195 -- fail-closed JSON/NPZ loading for V0.23 source shards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRSAnchorRecord,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_source_artifact import (
    LCSRSC3SourceArtifactError,
    V023_CONTRACT_SHA256,
    V023_EXECUTION_ADDENDUM_SHA256,
    V023_PLACEBO_KEY_SHA256,
    V023_SOURCE_ARTIFACT_SCHEMA,
    V023_SOURCE_CLAIM_CEILING,
    load_v023_world_source_artifact,
)
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


WORLD = 2026121705
EXECUTION_ADDENDUM = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
)
Q2_ARRAY_SHAPES = {
    "q2_state_matrix": (9, 3, 448),
    "q2_feature_surface": (9, 3, 28, 16),
    "q2_teacher_values": (9, 3, 28),
    "q2_persistence": (9, 3, 3, 28),
    "q2_rate_bps": (9, 3, 3, 28),
    "q2_marginal_power_w": (9, 3, 3, 28),
    "q2_required_power_w": (9, 3, 3, 28),
    "q2_horizon": (9,),
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _array_digest(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(b"source-array-v1")
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def test_execution_addendum_digest_is_bound_to_real_authority() -> None:
    assert hashlib.sha256(EXECUTION_ADDENDUM.read_bytes()).hexdigest() == (
        V023_EXECUTION_ADDENDUM_SHA256
    )


def _source_fixture(tmp_path: Path) -> Path:
    users, actions, anchors = 3, 28, 9
    contexts = np.zeros((anchors, users, actions, 29), dtype=np.float32)
    tokens = np.zeros((anchors, users, actions, users + 1, 38), dtype=np.float32)
    masks = np.zeros((anchors, users, actions), dtype=np.bool_)
    masks[:, :, :3] = True
    token_masks = np.zeros((anchors, users, actions, users + 1), dtype=np.bool_)
    token_masks[:, :, :, users] = masks
    tokens[:, :, :, users, 1][masks] = 1.0
    tokens[:, 0:2, 1, users, 2:5] = 1.0
    contexts[:, 0:2, 1, 3] = 1.0
    contexts[:, 0:2, 1, 27] = np.float32(1.0 / users)
    q12 = np.zeros((anchors, users, actions), dtype=np.float32)
    q12[:, :, 1:] = -0.005
    contexts[:, :, :3, 23] = np.asarray(
        np.tanh(q12[:, :, :3] - q12[:, :, [0]]), dtype=np.float32
    )
    views = [
        assemble_c3_view(
            action_context=contexts[index],
            tokens=tokens[index],
            token_mask=token_masks[index],
            action_mask=masks[index],
            reference_actions=np.zeros(users, dtype=np.int64),
        )
        for index in range(anchors)
    ]
    pair_draws = np.stack(
        [
            np.tile(
                np.asarray([[float(index + 1), -float(index + 1)]], dtype=np.float64),
                (LCSRS_DRAW_COUNT, 1),
            )
            for index in range(anchors)
        ]
    )
    pair_ids = [f"w{WORLD}-t{index + 1}-p0" for index in range(anchors)]
    records: list[LCSRSAnchorRecord] = []
    for index, view in enumerate(views):
        pair = LCSRSPairTargets(
            pair_id=pair_ids[index],
            user_ids=np.asarray([0, 1], dtype=np.int64),
            action_ids=np.asarray([1, 1], dtype=np.int64),
            normalized_targets_by_draw=pair_draws[index],
        )
        surface = assemble_lcsrs_anchor_surface(view, [pair])
        records.append(
            LCSRSAnchorRecord(
                world_id=WORLD,
                phase=index + 1,
                anchor_id=f"w{WORLD}:t{index + 1}",
                surface=surface,
                q12_values=np.asarray(q12[index], dtype=np.float64),
            )
        )
    physical_keys = np.zeros((anchors, users, actions, 2), dtype=np.int64)
    physical_keys[..., 0] = 10
    physical_keys[..., 1] = np.arange(actions, dtype=np.int64)
    arrays = {
        "anchor_phase": np.arange(1, 10, dtype=np.int64),
        "anchor_retained": np.ones(anchors, dtype=np.bool_),
        "anchor_view_content_digest": np.asarray(
            [view.content_digest.encode("ascii") for view in views], dtype="S64"
        ),
        "action_context": contexts,
        "tokens": tokens,
        "token_mask": token_masks,
        "action_mask": masks,
        "reference_actions": np.zeros((anchors, users), dtype=np.int64),
        "opening_feasibility": masks.copy(),
        "physical_keys": physical_keys,
        "q1_values": np.asarray(q12, dtype=np.float64),
        "q2_values": np.zeros_like(q12, dtype=np.float64),
        "q12_values": np.asarray(q12, dtype=np.float64),
        # Target-free Q2 context and the raw repricing inputs are part of the
        # V0.23 source-artifact reconstruction contract.  Keep the fixture
        # deliberately neutral; the loader must authenticate their exact
        # names, dtypes, shapes, and digests even when this test does not
        # exercise the scientific C2 formula.
        "q2_state_matrix": np.zeros(Q2_ARRAY_SHAPES["q2_state_matrix"], dtype=np.float32),
        "q2_feature_surface": np.zeros(Q2_ARRAY_SHAPES["q2_feature_surface"], dtype=np.float64),
        "q2_teacher_values": np.zeros(Q2_ARRAY_SHAPES["q2_teacher_values"], dtype=np.float64),
        "q2_persistence": np.zeros(Q2_ARRAY_SHAPES["q2_persistence"], dtype=np.float64),
        "q2_rate_bps": np.zeros(Q2_ARRAY_SHAPES["q2_rate_bps"], dtype=np.float64),
        "q2_marginal_power_w": np.zeros(Q2_ARRAY_SHAPES["q2_marginal_power_w"], dtype=np.float64),
        "q2_required_power_w": np.zeros(Q2_ARRAY_SHAPES["q2_required_power_w"], dtype=np.float64),
        "q2_horizon": np.full(Q2_ARRAY_SHAPES["q2_horizon"], 3, dtype=np.int64),
        "pair_anchor_index": np.arange(anchors, dtype=np.int64),
        "pair_id": np.asarray([value.encode("ascii") for value in pair_ids], dtype="S256"),
        "pair_user_ids": np.tile(np.asarray([[0, 1]], dtype=np.int64), (anchors, 1)),
        "pair_action_ids": np.ones((anchors, 2), dtype=np.int64),
        "pair_target_by_draw": pair_draws,
        "pair_target_mean": np.mean(pair_draws, axis=1),
        "pair_class": np.full((anchors, 2), 3, dtype=np.uint8),
    }
    sidecar = tmp_path / f"world-{WORLD}.arrays.npz"
    np.savez_compressed(sidecar, **arrays)
    sidecar_sha = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    (tmp_path / f"{sidecar.name}.sha256").write_text(
        f"{sidecar_sha}  {sidecar.name}\n", encoding="ascii"
    )
    metadata = {
        name: {
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "sha256": _array_digest(value),
        }
        for name, value in arrays.items()
    }
    anchor_entries = []
    for index, record in enumerate(records):
        anchor_entries.append(
            {
                "anchor_id": record.anchor_id,
                "phase": index + 1,
                "retained_for_fitting": True,
                "topology": {"pairs": [{"pair_id": pair_ids[index]}]},
                "surface": {
                    "record": {
                        "surface_digest": record.surface.content_digest,
                        "content_digest": record.content_digest,
                    }
                },
            }
        )
    payload = {
        "schema": "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-shard",
        "status": "PASS",
        "claim_ceiling": V023_SOURCE_CLAIM_CEILING,
        "contract_sha256": V023_CONTRACT_SHA256,
        "preflight_manifest_sha256": "2" * 64,
        "execution_addendum_sha256": V023_EXECUTION_ADDENDUM_SHA256,
        "placebo_key_sha256": V023_PLACEBO_KEY_SHA256,
        "split": "TRAIN_DEVELOPMENT",
        "world": WORLD,
        "source_artifact_schema": V023_SOURCE_ARTIFACT_SCHEMA,
        "source_artifact_version": 1,
        "anchors": anchor_entries,
        "arrays": {
            "allow_pickle": False,
            "npz_relative_path": sidecar.name,
            "npz_sha256": sidecar_sha,
            "array_metadata": metadata,
        },
        "record_count": anchors,
        "pair_count": anchors,
        "supported_count": anchors * 2,
        "placebo_eligible_count": anchors * 2,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    payload["receipt_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
    index = tmp_path / f"world-{WORLD}.json"
    index.write_bytes(_canonical(payload))
    return index


def test_source_artifact_reconstructs_all_retained_records(tmp_path: Path) -> None:
    index = _source_fixture(tmp_path)
    artifact = load_v023_world_source_artifact(
        index,
        expected_world=WORLD,
        expected_preflight_sha256="2" * 64,
    )
    assert artifact.world == WORLD
    assert len(artifact.records) == 9
    assert artifact.supported_count == 18
    assert [record.phase for record in artifact.records] == list(range(1, 10))


def test_source_artifact_rejects_npz_byte_tampering(tmp_path: Path) -> None:
    index = _source_fixture(tmp_path)
    sidecar = tmp_path / f"world-{WORLD}.arrays.npz"
    sidecar.write_bytes(sidecar.read_bytes() + b"tamper")
    with pytest.raises(LCSRSC3SourceArtifactError, match="byte digest"):
        load_v023_world_source_artifact(index)


def test_source_artifact_rejects_receipt_seal_tampering(tmp_path: Path) -> None:
    index = _source_fixture(tmp_path)
    payload = json.loads(index.read_text(encoding="ascii"))
    payload["supported_count"] = 17
    index.write_bytes(_canonical(payload))
    with pytest.raises(LCSRSC3SourceArtifactError, match="receipt seal"):
        load_v023_world_source_artifact(index)
