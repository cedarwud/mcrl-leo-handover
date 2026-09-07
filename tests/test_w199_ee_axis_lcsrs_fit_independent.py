"""W-199 -- independent V0.23 fit-artifact verification.

The fixtures are deliberately numeric-only and synthetic.  They exercise the
fit receipt boundary without importing a project adapter, opening a simulator,
performing a learner update, or touching the TEST split.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-c3-observability"
    / "verify_v023_lcsrs_fit_independent.py"
)
SPEC = importlib.util.spec_from_file_location("v023_fit_independent_test", VERIFIER_PATH)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


PRE_FLIGHT = "2" * 64


def test_frozen_placebo_key_digest_is_independently_authenticated() -> None:
    """Keep the addendum key digest independent of the production constant."""

    key = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
    expected = hashlib.sha256(key.encode("utf-8")).hexdigest()
    assert expected == (
        "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
    )
    assert verifier.V023_PLACEBO_KEY_SHA256 == expected


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _array_digest(value: np.ndarray, *, domain: str) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _write_npz(
    root: Path,
    name: str,
    arrays: dict[str, np.ndarray],
    *,
    domain: str,
) -> dict[str, object]:
    path = root / name
    np.savez_compressed(path, **arrays)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / f"{name}.sha256").write_text(
        f"{digest}  {name}\n", encoding="ascii"
    )
    return {
        "allow_pickle": False,
        "npz_relative_path": name,
        "npz_sha256": digest,
        "npz_sha256_file": f"{name}.sha256",
        "array_metadata": {
            key: {
                "dtype": value.dtype.str,
                "shape": list(value.shape),
                "sha256": _array_digest(value, domain=domain),
            }
            for key, value in arrays.items()
        },
    }


def _seal(payload: dict[str, object]) -> dict[str, object]:
    result = dict(payload)
    result["receipt_sha256"] = verifier.canonical_sha256(result)
    return result


def _source_world(root: Path, world: int) -> Path:
    users, actions, anchors = 4, 28, 9
    context = np.zeros((anchors, users, actions, 29), dtype=np.float32)
    context[:, :, :4, 3] = 1.0  # legal and opening for four synthetic actions
    context[:, 0:2, 1, 27] = np.float32(1.0 / users)
    context[:, 2:4, 2, 27] = np.float32(1.0 / users)
    tokens = np.zeros(
        (anchors, users, actions, users + 1, 38), dtype=np.float32
    )
    token_mask = np.zeros(
        (anchors, users, actions, users + 1), dtype=np.bool_
    )
    action_mask = np.zeros((anchors, users, actions), dtype=np.bool_)
    action_mask[:, :, :4] = True
    token_mask[:, :, :, users] = action_mask
    tokens[:, :, :, users, 1] = action_mask.astype(np.float32)
    tokens[:, 0:2, 1, users, 2:5] = 1.0
    tokens[:, 2:4, 2, users, 2:5] = 1.0
    reference = np.zeros((anchors, users), dtype=np.int64)
    q1 = np.zeros((anchors, users, actions), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q12 = q1 + q2
    physical = np.zeros((anchors, users, actions, 2), dtype=np.int64)
    physical[..., 0] = 10
    physical[..., 1] = np.arange(actions, dtype=np.int64)
    pair_anchor: list[int] = []
    pair_ids: list[bytes] = []
    pair_users: list[list[int]] = []
    pair_actions: list[list[int]] = []
    pair_draws: list[np.ndarray] = []
    for anchor in range(anchors):
        for pair_offset, (members, proposed) in enumerate(
            (((0, 1), (1, 1)), ((2, 3), (2, 2)))
        ):
            value = float(anchor + 1 + pair_offset * 0.25)
            pair_anchor.append(anchor)
            pair_ids.append(f"w{world}-t{anchor + 1}-p{pair_offset}".encode("ascii"))
            pair_users.append(list(members))
            pair_actions.append(list(proposed))
            pair_draws.append(
                np.tile(np.asarray([[value, -value]], dtype=np.float64), (32, 1))
            )
    pair_draw_array = np.stack(pair_draws)
    arrays = {
        "anchor_phase": np.arange(1, 10, dtype=np.int64),
        "anchor_status": np.ones(anchors, dtype=np.uint8),
        "anchor_retained": np.ones(anchors, dtype=np.bool_),
        "anchor_content_digest": np.asarray(
            [hashlib.sha256(f"capture-{world}-{index}".encode("ascii")).hexdigest().encode("ascii") for index in range(anchors)],
            dtype="S64",
        ),
        "anchor_view_content_digest": np.asarray(
            [
                verifier._c3_view_digest(
                    context[index],
                    tokens[index],
                    token_mask[index],
                    action_mask[index],
                    reference[index],
                ).encode("ascii")
                for index in range(anchors)
            ],
            dtype="S64",
        ),
        "anchor_topology_content_digest": np.asarray(
            [b"b" * 64] * anchors, dtype="S64"
        ),
        "action_context": context,
        "tokens": tokens,
        "token_mask": token_mask,
        "action_mask": action_mask,
        "opening_feasibility": action_mask.copy(),
        "reference_actions": reference,
        "physical_keys": physical,
        "q1_values": q1,
        "q2_values": q2,
        "q12_values": q12,
        "pair_anchor_index": np.asarray(pair_anchor, dtype=np.int64),
        "pair_id": np.asarray(pair_ids, dtype="S256"),
        "pair_user_ids": np.asarray(pair_users, dtype=np.int64),
        "pair_action_ids": np.asarray(pair_actions, dtype=np.int64),
        "pair_target_by_draw": pair_draw_array,
        "pair_target_mean": np.mean(pair_draw_array, axis=1, dtype=np.float64),
        "pair_class": np.full((len(pair_ids), 2), 3, dtype=np.uint8),
        "pair_retained": np.ones(len(pair_ids), dtype=np.bool_),
    }
    sidecar = _write_npz(
        root,
        f"world-{world}.arrays.npz",
        arrays,
        domain=verifier.V023_SOURCE_ARRAY_DOMAIN,
    )
    sidecar.update(
        {
            "schema": f"{verifier.V023_SOURCE_ARTIFACT_SCHEMA}-arrays-v1",
            "array_count": len(arrays),
            "profile_order": ["00", "10", "01", "11"],
            "draw_count": verifier.V023_DRAW_COUNT,
        }
    )
    anchor_entries: list[dict[str, object]] = []
    for anchor in range(anchors):
        pair_start = 2 * anchor
        anchor_id = f"w{world}:t{anchor + 1}"
        predecision_digest = hashlib.sha256(
            f"capture-{world}-{anchor}".encode("ascii")
        ).hexdigest()
        view_digest = verifier._c3_view_digest(
            context[anchor],
            tokens[anchor],
            token_mask[anchor],
            action_mask[anchor],
            reference[anchor],
        )
        target_surface = np.zeros((users, actions), dtype=np.float32)
        row_class = np.zeros((users, actions), dtype=np.uint8)
        row_class[action_mask[anchor]] = 2
        row_class[np.arange(users), reference[anchor]] = 1
        pair_records = []
        for pair_raw in (pair_start, pair_start + 1):
            pair_mean = np.asarray(pair_draw_array[pair_raw].mean(axis=0), dtype=np.float32)
            for member, (user, action) in enumerate(
                zip(pair_users[pair_raw], pair_actions[pair_raw], strict=True)
            ):
                target_surface[int(user), int(action)] = pair_mean[member]
                row_class[int(user), int(action)] = 3
            pair_records.append(
                (
                    pair_ids[pair_raw].decode("ascii"),
                    np.asarray(pair_users[pair_raw], dtype=np.int64),
                    np.asarray(pair_actions[pair_raw], dtype=np.int64),
                    np.asarray(pair_draw_array[pair_raw], dtype=np.float64),
                )
            )
        surface_digest = verifier._surface_digest(
            view_digest, target_surface, row_class, pair_records
        )
        record_digest = verifier._anchor_record_digest(
            world=world,
            phase=anchor + 1,
            anchor_id=anchor_id,
            surface_digest=surface_digest,
            q12=np.asarray(q12[anchor], dtype=np.float64),
        )
        anchor_entries.append(
            {
                "anchor_id": anchor_id,
                "phase": anchor + 1,
                "predecision_sha256": predecision_digest,
                "retained_for_fitting": True,
                "topology": {
                    "content_digest": "b" * 64,
                    "pairs": [
                        {"pair_id": pair_ids[pair_start].decode("ascii")},
                        {"pair_id": pair_ids[pair_start + 1].decode("ascii")},
                    ]
                },
                "surface": {
                    "record": {
                        "world_id": world,
                        "phase": anchor + 1,
                        "anchor_id": anchor_id,
                        "surface_digest": surface_digest,
                        "content_digest": record_digest,
                    }
                },
            }
        )
    payload: dict[str, object] = {
        "schema": verifier.V023_SOURCE_SHARD_SCHEMA,
        "status": "PASS",
        "claim_ceiling": verifier.V023_CLAIM_CEILING,
        "contract_sha256": verifier.V023_CONTRACT_SHA256,
        "preflight_manifest_sha256": PRE_FLIGHT,
        "execution_addendum_sha256": verifier.V023_EXECUTION_ADDENDUM_SHA256,
        "placebo_key_sha256": verifier.V023_PLACEBO_KEY_SHA256,
        "split": "TRAIN_DEVELOPMENT",
        "world": world,
        "source_artifact_schema": verifier.V023_SOURCE_ARTIFACT_SCHEMA,
        "source_artifact_version": verifier.V023_SOURCE_ARTIFACT_VERSION,
        "world_receipt": {
            "world": world,
            "phase_count": anchors,
            "anchor_ids": [f"w{world}:t{anchor + 1}" for anchor in range(anchors)],
            "test_split_opened": False,
            "learner_update": False,
            "episode_training": False,
        },
        "q12_background": {
            "q12_unit": "authenticated-normalized-q1-plus-q2-float32"
        },
        "anchors": anchor_entries,
        "enumeration": {"schema": "synthetic-enumeration", "world": world},
        "topology": {"schema": "synthetic-topology", "world": world},
        "teacher": {"schema": "synthetic-teacher", "world": world},
        "surface": {"schema": "synthetic-surface", "world": world},
        "arrays": sidecar,
        "record_count": anchors,
        "pair_count": len(pair_ids),
        "supported_count": len(pair_ids) * 2,
        "placebo_eligible_count": len(pair_ids) * 2,
        "placebo_key": verifier.V023_PLACEBO_KEY,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    for name in ("enumeration", "topology", "teacher", "surface"):
        payload[f"{name}_sha256"] = verifier.canonical_sha256(payload[name])
    index = root / f"world-{world}.json"
    index.write_bytes(_canonical(_seal(payload)))
    return index


def _source_panel(tmp_path: Path) -> tuple[Path, list[Path], str]:
    root = tmp_path / "sources"
    source_dir = root / "source"
    source_dir.mkdir(parents=True)
    paths = [_source_world(source_dir, world) for world in verifier.V023_GATE_WORLDS]
    entries = [
        {
            "world": world,
            "relative_name": f"source/world-{world}.json",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for world, path in zip(verifier.V023_GATE_WORLDS, paths, strict=True)
    ]
    body: dict[str, object] = {
        "schema": verifier.V023_SOURCE_MANIFEST_SCHEMA,
        "status": "PASS",
        "claim_ceiling": verifier.V023_CLAIM_CEILING,
        "contract_sha256": verifier.V023_CONTRACT_SHA256,
        "preflight_manifest_sha256": PRE_FLIGHT,
        "split": "TRAIN_DEVELOPMENT",
        "worlds": list(verifier.V023_GATE_WORLDS),
        "source_count": 8,
        "shards": [
            {"world": world, "relative_name": f"source/world-{world}.json"}
            for world in verifier.V023_GATE_WORLDS
        ],
        "entries": entries,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    body["source_manifest_sha256"] = verifier.canonical_sha256(body)
    body["manifest_sha256"] = verifier.canonical_sha256(body)
    manifest = root / "source-manifest.json"
    manifest.write_bytes(_canonical(body))
    return manifest, paths, str(body["source_manifest_sha256"])


def _prediction_digest(
    identities: list[tuple[int, str, int, int]],
    prediction: np.ndarray,
    target: np.ndarray,
) -> str:
    return verifier._prediction_digest(identities, prediction, target)


def _fit_artifact(
    tmp_path: Path,
    *,
    arm: str = "INFORMED",
    mutate_target: bool = False,
    missing_identity: bool = False,
    object_model: bool = False,
) -> tuple[Path, Path, list[Path]]:
    manifest, source_paths, source_hash = _source_panel(tmp_path)
    worlds = tuple(
        verifier._load_source_world(path, world=world, preflight=PRE_FLIGHT)
        for world, path in zip(verifier.V023_GATE_WORLDS, source_paths, strict=True)
    )
    heldout = verifier.V023_GATE_WORLDS[0]
    fold = verifier._make_fold(worlds, held_out_world=heldout)
    fit_root = tmp_path / "fit"
    fit_root.mkdir()
    metrics_npz_name = "informed.metrics.npz"
    model_name = "informed.model.npz"
    fit_name = "informed.fit-receipt.json"
    metrics_name = "informed.metrics.json"
    placebo_name = "informed.placebo.json"
    model_array = (
        np.asarray([b"unsafe"], dtype=object)
        if object_model
        else np.asarray([0.25, -0.5], dtype=np.float32)
    )
    model_binding = _write_npz(
        fit_root,
        model_name,
        {"tensor_0000": model_array},
        domain=verifier.V023_FIT_MODEL_ARRAY_DOMAIN,
    )
    model_state = {
        "schema": verifier.V023_FIT_MODEL_SCHEMA,
        "path": model_name,
        "npz_sha256": model_binding["npz_sha256"],
        "npz_sha256_file": model_binding["npz_sha256_file"],
        "logical_network_sha256": "3" * 64,
        "array_domain": verifier.V023_FIT_MODEL_ARRAY_DOMAIN,
        "arrays": {
            "q3.weight": {
                "npz_key": "tensor_0000",
                "dtype": model_array.dtype.str,
                "shape": list(model_array.shape),
                "sha256": _array_digest(
                    model_array, domain=verifier.V023_FIT_MODEL_ARRAY_DOMAIN
                ),
            }
        },
        "no_pickle": True,
    }
    identities = [
        (row.world, row.anchor_id, row.user, row.action)
        for row in fold.heldout_rows
    ]
    target = np.asarray([row.target for row in fold.heldout_rows], dtype=np.float64)
    if mutate_target:
        target = target.copy()
        target[0] += 99.0
    prediction = target * 2.0
    if missing_identity:
        identity_arrays = {
            "identity_world": np.asarray([row[0] for row in identities], dtype=np.int64),
            "identity_anchor": np.asarray([row[1].encode("ascii") for row in identities], dtype="S256"),
            "identity_user": np.asarray([row[2] for row in identities], dtype=np.int64),
            # Deliberately omit identity_action.
            "prediction": prediction,
            "target": target,
            "loss": np.zeros(2000, dtype=np.float64),
        }
    else:
        identity_arrays = {
            "identity_world": np.asarray([row[0] for row in identities], dtype=np.int64),
            "identity_anchor": np.asarray([row[1].encode("ascii") for row in identities], dtype="S256"),
            "identity_user": np.asarray([row[2] for row in identities], dtype=np.int64),
            "identity_action": np.asarray([row[3] for row in identities], dtype=np.int64),
            "prediction": prediction,
            "target": target,
            "loss": np.zeros(2000, dtype=np.float64),
        }
    metrics_binding = _write_npz(
        fit_root,
        metrics_npz_name,
        identity_arrays,
        domain=verifier.V023_FIT_PREDICTION_ARRAY_DOMAIN,
    )
    metrics_identities = [
        {"world": world, "anchor_id": anchor, "user": user, "action": action}
        for world, anchor, user, action in identities
    ]
    rho = verifier.tie_aware_spearman(prediction, target)
    sign = verifier.sign_receipt(prediction, target)
    metrics_body: dict[str, object] = {
        "schema": verifier.V023_FIT_METRICS_SCHEMA,
        "claim_ceiling": verifier.V023_CLAIM_CEILING,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": heldout,
        "student_seed": verifier.V023_STUDENT_SEEDS[0],
        "arm": arm,
        "source_manifest_sha256": source_hash,
        "training_worlds": [world for world in verifier.V023_GATE_WORLDS if world != heldout],
        "training_anchor_count": len(fold.training_anchors),
        "heldout_anchor_count": len(fold.heldout_anchors),
        "heldout_supported_rows": len(identities),
        "heldout_prediction_content_digest": _prediction_digest(identities, prediction, target),
        "spearman": rho,
        "sign": sign,
        "denominators": {
            "spearman_rows": len(identities),
            "sign_total_rows": sign["total_rows"],
            "sign_evaluated_rows": sign["evaluated_rows"],
            "sign_excluded_rows": sign["excluded_rows"],
            "heldout_world_count": 1,
            "heldout_anchor_count": len(fold.heldout_anchors),
            "training_world_count": 7,
        },
        "identities": metrics_identities,
        "sidecar": {
            "npz_relative_name": metrics_npz_name,
            "npz_sha256": metrics_binding["npz_sha256"],
            "array_domain": verifier.V023_FIT_PREDICTION_ARRAY_DOMAIN,
        },
        "fit_receipt_final_network_sha256": "3" * 64,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": True,
        "arrays": metrics_binding["array_metadata"],
    }
    metrics_path = fit_root / metrics_name
    metrics_path.write_bytes(_canonical(metrics_body))
    metrics_sha = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
    target_arrays = fold.informed_targets if arm == "INFORMED" else fold.placebo_targets
    target_source_hash = verifier._target_source_digest(fold.training_anchors, target_arrays)
    loss = np.zeros(2000, dtype=np.float64)
    fit_body: dict[str, object] = {
        "schema": verifier.V023_FIT_RECEIPT_SCHEMA,
        "arm": arm,
        "student_seed": verifier.V023_STUDENT_SEEDS[0],
        "source_anchor_sha256s": [anchor.content_digest for anchor in fold.training_anchors],
        "target_source_sha256": target_source_hash,
        "initial_network_sha256": verifier.V023_INITIAL_NETWORK_SHA256_BY_SEED[
            verifier.V023_STUDENT_SEEDS[0]
        ],
        "final_network_sha256": "3" * 64,
        "config_sha256": verifier.V023_LEARNER_CONFIG_SHA256,
        "updates": 2000,
        "batch_size": 256,
        "losses_count": 2000,
        "losses_sha256": _array_digest(
            loss, domain=verifier.V023_FIT_PREDICTION_ARRAY_DOMAIN
        ),
        "losses": loss.tolist(),
    }
    fit_path = fit_root / fit_name
    fit_path.write_bytes(_canonical(fit_body))
    fit_sha = hashlib.sha256(fit_path.read_bytes()).hexdigest()
    metrics_body["fit_receipt_sidecar"] = {
        "relative_name": fit_name,
        "sha256": fit_sha,
    }
    metrics_path.write_bytes(_canonical(metrics_body))
    metrics_sha = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
    placebo_body: dict[str, object] = {
        "schema": verifier.V023_FIT_PLACEBO_SCHEMA,
        "claim_ceiling": verifier.V023_CLAIM_CEILING,
        "held_out_world": heldout,
        "arm": arm,
        "student_seed": verifier.V023_STUDENT_SEEDS[0],
        "source_manifest_sha256": source_hash,
        "placebo_key": verifier.V023_PLACEBO_KEY,
        "placebo_key_sha256": verifier.V023_PLACEBO_KEY_SHA256,
        "content_digest": fold.placebo_digest,
        "eligible_supported_rows": fold.placebo_eligible,
        "total_supported_rows": fold.placebo_total,
        "coverage": fold.placebo_eligible / fold.placebo_total,
        "meets_coverage_gate": True,
        "training_anchor_identities": [
            {
                "world": anchor.world,
                "anchor_id": anchor.anchor_id,
                "content_digest": anchor.content_digest,
            }
            for anchor in fold.training_anchors
        ],
        "mappings": list(fold.mappings),
        "target_source_sha256": target_source_hash,
        "target_array_count": len(target_arrays),
        "target_array_shapes": [list(target.shape) for target in target_arrays],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": True,
    }
    placebo_path = fit_root / placebo_name
    placebo_path.write_bytes(_canonical(placebo_body))
    placebo_sha = hashlib.sha256(placebo_path.read_bytes()).hexdigest()
    identity_outer = metrics_identities
    outer_metrics = {
        "schema": verifier.V023_FIT_METRICS_SCHEMA,
        "path": metrics_name,
        "sha256": metrics_sha,
        "npz_path": metrics_npz_name,
        "npz_sha256": metrics_binding["npz_sha256"],
        "npz_sha256_file": metrics_binding["npz_sha256_file"],
        "content_digest": metrics_body["heldout_prediction_content_digest"],
        "spearman": rho,
        "sign": sign,
        "denominators": metrics_body["denominators"],
        "heldout_supported_rows": len(identities),
        "identities": identity_outer,
    }
    outer_fit = dict(fit_body)
    outer_fit.update({"path": fit_name, "sha256": fit_sha})
    outer_placebo = dict(placebo_body)
    outer_placebo.update({"path": placebo_name, "sha256": placebo_sha})
    receipt: dict[str, object] = {
        "schema": verifier.V023_FIT_SCHEMA,
        "status": "PASS",
        "claim_ceiling": verifier.V023_CLAIM_CEILING,
        "contract_sha256": verifier.V023_CONTRACT_SHA256,
        "preflight_manifest_sha256": PRE_FLIGHT,
        "source_manifest_sha256": source_hash,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": heldout,
        "student_seed": verifier.V023_STUDENT_SEEDS[0],
        "arm": arm,
        "update_count": 2000,
        "learner_update": True,
        "episode_training": False,
        "test_split_opened": False,
        "test_worlds": [],
        "source_panel": {
            "schema": verifier.V023_SOURCE_ARTIFACT_SCHEMA,
            "version": verifier.V023_SOURCE_ARTIFACT_VERSION,
            "worlds": list(verifier.V023_GATE_WORLDS),
            "source_manifest_sha256": source_hash,
            "source_manifest_path": manifest.name,
            "source_pair_count": 8 * 18,
            "source_anchor_count": 8 * 9,
            "source_index_sha256s": {
                str(world): hashlib.sha256(path.read_bytes()).hexdigest()
                for world, path in zip(verifier.V023_GATE_WORLDS, source_paths, strict=True)
            },
        },
        "fold": {
            "held_out_world": heldout,
            "training_worlds": [world for world in verifier.V023_GATE_WORLDS if world != heldout],
            "training_anchor_count": len(fold.training_anchors),
            "heldout_anchor_count": len(fold.heldout_anchors),
            "training_anchor_sha256s": [anchor.content_digest for anchor in fold.training_anchors],
            "heldout_anchor_sha256s": [anchor.content_digest for anchor in fold.heldout_anchors],
            "heldout_anchor_ids": [anchor.anchor_id for anchor in fold.heldout_anchors],
            "heldout_is_untouched": True,
        },
        "placebo": outer_placebo,
        "fit_receipt": outer_fit,
        "model_state": model_state,
        "model_sha256": model_binding["npz_sha256"],
        "network_sha256": "3" * 64,
        "metrics": outer_metrics,
        "metrics_sha256": metrics_sha,
        "denominators": metrics_body["denominators"],
        "no_rescue": {
            "early_stopping": False,
            "best_checkpoint_selection": False,
            "outcome_weighting": False,
            "heldout_target_permutation": False,
        },
    }
    receipt_path = fit_root / "informed.json"
    receipt_path.write_bytes(_canonical(_seal(receipt)))
    return receipt_path, manifest, source_paths


def test_verifier_has_only_stdlib_and_numpy_imports() -> None:
    tree = ast.parse(VERIFIER_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
    )
    assert imported <= {
        "dataclasses",
        "hashlib",
        "json",
        "math",
        "pathlib",
        "struct",
        "typing",
        "numpy",
        "__future__",
    }


def test_valid_fit_is_verified_but_logical_network_hash_remains_an_explicit_gap(
    tmp_path: Path,
) -> None:
    receipt, manifest, paths = _fit_artifact(tmp_path)
    report = verifier.verify_v023_fit_artifact(
        receipt,
        source_manifest_path=manifest,
        source_index_paths=paths,
        preflight_manifest_sha256=PRE_FLIGHT,
    )
    assert report["integrity_status"] == "VERIFIED"
    assert report["status"] == "FIT_ARTIFACT_VERIFIED_WITH_GAPS"
    assert report["gate_ready"] is False
    assert report["scientific_claim"] is False
    assert report["logical_network_hash_verified"] is False
    assert any("LOGICAL_NETWORK_HASH" in gap["code"] for gap in report["gaps"])
    assert report["heldout_supported_rows"] == 36


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("model", "model"),
        ("metrics", "metrics"),
        ("fit", "fit receipt"),
        ("placebo", "placebo"),
    ],
)
def test_tampering_is_rejected_even_when_sidecar_bytes_are_resealed(
    tmp_path: Path, mutation: str, match: str
) -> None:
    receipt, manifest, paths = _fit_artifact(tmp_path)
    payload = json.loads(receipt.read_text(encoding="ascii"))
    if mutation == "model":
        target = receipt.parent / payload["model_state"]["path"]
        target.write_bytes(target.read_bytes() + b"tamper")
    elif mutation == "metrics":
        target = receipt.parent / payload["metrics"]["npz_path"]
        target.write_bytes(target.read_bytes() + b"tamper")
    elif mutation == "fit":
        target = receipt.parent / payload["fit_receipt"]["path"]
        body = json.loads(target.read_text(encoding="ascii"))
        body["losses"][0] = 7.0
        target.write_bytes(_canonical(body))
    else:
        target = receipt.parent / payload["placebo"]["path"]
        body = json.loads(target.read_text(encoding="ascii"))
        body["coverage"] = 0.5
        target.write_bytes(_canonical(body))
    with pytest.raises(verifier.V023FitIndependentVerificationError, match=match):
        verifier.verify_v023_fit_artifact(
            receipt,
            source_manifest_path=manifest,
            source_index_paths=paths,
            preflight_manifest_sha256=PRE_FLIGHT,
        )


def test_arbitrary_self_consistent_labels_cannot_replace_authenticated_source_targets(
    tmp_path: Path,
) -> None:
    receipt, manifest, paths = _fit_artifact(tmp_path, mutate_target=True)
    with pytest.raises(
        verifier.V023FitIndependentVerificationError,
        match="target leaks|source S rows",
    ):
        verifier.verify_v023_fit_artifact(
            receipt,
            source_manifest_path=manifest,
            source_index_paths=paths,
            preflight_manifest_sha256=PRE_FLIGHT,
        )


def test_heldout_leakage_in_fold_and_placebo_is_rejected(tmp_path: Path) -> None:
    receipt, manifest, paths = _fit_artifact(tmp_path)
    payload = json.loads(receipt.read_text(encoding="ascii"))
    payload["fold"]["training_worlds"] = list(verifier.V023_GATE_WORLDS)
    receipt.write_bytes(_canonical(_seal({key: value for key, value in payload.items() if key != "receipt_sha256"})))
    with pytest.raises(verifier.V023FitIndependentVerificationError, match="LOO|held-out"):
        verifier.verify_v023_fit_artifact(
            receipt,
            source_manifest_path=manifest,
            source_index_paths=paths,
            preflight_manifest_sha256=PRE_FLIGHT,
        )


def test_model_object_dtype_and_missing_identity_are_custom_errors(tmp_path: Path) -> None:
    receipt, manifest, paths = _fit_artifact(tmp_path, object_model=True)
    with pytest.raises(verifier.V023FitIndependentVerificationError, match="object|model"):
        verifier.verify_v023_fit_artifact(
            receipt,
            source_manifest_path=manifest,
            source_index_paths=paths,
            preflight_manifest_sha256=PRE_FLIGHT,
        )
    receipt, manifest, paths = _fit_artifact(tmp_path / "missing", missing_identity=True)
    with pytest.raises(verifier.V023FitIndependentVerificationError, match="keys|identity"):
        verifier.verify_v023_fit_artifact(
            receipt,
            source_manifest_path=manifest,
            source_index_paths=paths,
            preflight_manifest_sha256=PRE_FLIGHT,
        )


def test_placebo_arm_binds_fold_local_targets_and_world_local_mapping(tmp_path: Path) -> None:
    receipt, manifest, paths = _fit_artifact(tmp_path, arm="MATCHED_PLACEBO")
    report = verifier.verify_v023_fit_artifact(
        receipt,
        source_manifest_path=manifest,
        source_index_paths=paths,
        preflight_manifest_sha256=PRE_FLIGHT,
    )
    assert report["arm"] == "MATCHED_PLACEBO"
    assert report["placebo"]["coverage"] == 1.0
    assert report["placebo"]["mappings"] == report["placebo"]["total_supported_rows"]


def test_missing_authenticated_source_panel_fails_closed(tmp_path: Path) -> None:
    receipt, _manifest, _paths = _fit_artifact(tmp_path)
    with pytest.raises(verifier.V023FitIndependentVerificationError, match="source manifest"):
        verifier.verify_v023_fit_artifact(receipt)
