"""Fail-closed loader for one V0.23 LC-SRS JSON/NPZ source artifact."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from ..errors import MCRLContractError
from .ee_axis_lcsrs_c3_dataset import (
    LCSRS_ROW_SUPPORTED,
    LCSRSAnchorRecord,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from .ee_axis_lcsrs_c3_state import assemble_c3_view
from .ee_axis_lcsrs_c3_placebo import build_lcsrs_matched_placebo


V023_SOURCE_ARTIFACT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1"
V023_SOURCE_ARTIFACT_VERSION = 1
V023_SOURCE_SHARD_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-shard"
)
V023_CONTRACT_SHA256 = (
    "1e69a2e7242198adce97e6357e4205a29fe6d1fb06a48dc7e1839a675529811a"
)
V023_SOURCE_CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
V023_EXECUTION_ADDENDUM_SHA256 = (
    "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
)
V023_PLACEBO_KEY_SHA256 = (
    "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
)
V023_PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
V023_WORLDS = tuple(range(2026121705, 2026121713))
V023_PHASES = tuple(range(1, 10))

_RECONSTRUCTION_ARRAYS = {
    "anchor_phase",
    "anchor_retained",
    "anchor_view_content_digest",
    "action_context",
    "tokens",
    "token_mask",
    "action_mask",
    "reference_actions",
    "opening_feasibility",
    "physical_keys",
    "q1_values",
    "q2_values",
    "q12_values",
    "q2_state_matrix",
    "q2_feature_surface",
    "q2_teacher_values",
    "q2_persistence",
    "q2_rate_bps",
    "q2_marginal_power_w",
    "q2_required_power_w",
    "q2_horizon",
    "pair_anchor_index",
    "pair_id",
    "pair_user_ids",
    "pair_action_ids",
    "pair_target_by_draw",
    "pair_target_mean",
    "pair_class",
}


class LCSRSC3SourceArtifactError(MCRLContractError):
    """A source artifact is incomplete, stale, unsafe, or unreconstructable."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise LCSRSC3SourceArtifactError(f"expected a regular artifact file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise LCSRSC3SourceArtifactError(f"{field} is not a lowercase SHA-256")
    return value


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(b"source-array-v1")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _read_canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise LCSRSC3SourceArtifactError("source index is missing or is a symlink")
    raw = source.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LCSRSC3SourceArtifactError("source index is not ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise LCSRSC3SourceArtifactError("source index is not canonical JSON")
    seal = _digest(payload.get("receipt_sha256"), field="receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if _canonical_sha256(unsigned) != seal:
        raise LCSRSC3SourceArtifactError("source index receipt seal disagrees")
    return payload


def _decode_fixed_ascii(value: object, *, field: str) -> str:
    scalar = np.asarray(value)
    if scalar.shape != () or scalar.dtype.kind != "S":
        raise LCSRSC3SourceArtifactError(f"{field} is not fixed-width ASCII")
    try:
        result = bytes(scalar.item()).rstrip(b"\0").decode("ascii")
    except UnicodeDecodeError as error:
        raise LCSRSC3SourceArtifactError(f"{field} is not ASCII") from error
    if not result:
        raise LCSRSC3SourceArtifactError(f"{field} is empty")
    return result


def _verify_array_metadata(
    arrays: Mapping[str, np.ndarray], metadata: Mapping[str, Any]
) -> None:
    if set(arrays) != set(metadata):
        raise LCSRSC3SourceArtifactError("NPZ members and array metadata differ")
    if not _RECONSTRUCTION_ARRAYS.issubset(arrays):
        missing = sorted(_RECONSTRUCTION_ARRAYS - set(arrays))
        raise LCSRSC3SourceArtifactError(
            "source sidecar omits reconstruction arrays: " + ", ".join(missing)
        )
    for name in sorted(arrays):
        array = np.asarray(arrays[name])
        if array.dtype == object:
            raise LCSRSC3SourceArtifactError(f"array {name} has forbidden object dtype")
        entry = metadata[name]
        if not isinstance(entry, Mapping):
            raise LCSRSC3SourceArtifactError(f"array metadata {name} is malformed")
        if entry.get("dtype") != array.dtype.str:
            raise LCSRSC3SourceArtifactError(f"array {name} dtype disagrees")
        if entry.get("shape") != list(array.shape):
            raise LCSRSC3SourceArtifactError(f"array {name} shape disagrees")
        if _digest(entry.get("sha256"), field=f"{name}.sha256") != _array_digest(
            array
        ):
            raise LCSRSC3SourceArtifactError(f"array {name} digest disagrees")


@dataclass(frozen=True)
class V023WorldSourceArtifact:
    """One verified world index and its reconstructed fitting records."""

    world: int
    index_path: Path
    index_sha256: str
    sidecar_path: Path
    sidecar_sha256: str
    records: tuple[LCSRSAnchorRecord, ...]
    pair_count: int
    supported_count: int
    placebo_eligible_count: int
    index: Mapping[str, Any]


def _reconstruct_records(
    *,
    world: int,
    payload: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
) -> tuple[LCSRSAnchorRecord, ...]:
    anchors = payload.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != len(V023_PHASES):
        raise LCSRSC3SourceArtifactError("source index does not contain phases 1..9")
    phases = np.asarray(arrays["anchor_phase"], dtype=np.int64)
    retained = np.asarray(arrays["anchor_retained"])
    if phases.shape != (9,) or tuple(phases.tolist()) != V023_PHASES:
        raise LCSRSC3SourceArtifactError("anchor phase array is not exact 1..9")
    if retained.dtype != np.bool_ or retained.shape != (9,):
        raise LCSRSC3SourceArtifactError("anchor retained array is malformed")
    pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
    pair_ids = np.asarray(arrays["pair_id"])
    pair_users = np.asarray(arrays["pair_user_ids"])
    pair_actions = np.asarray(arrays["pair_action_ids"])
    pair_draws = np.asarray(arrays["pair_target_by_draw"])
    pair_means = np.asarray(arrays["pair_target_mean"])
    pair_classes = np.asarray(arrays["pair_class"])
    pair_count = pair_anchor.size
    expected_pair_shapes = (
        pair_ids.shape == (pair_count,)
        and pair_users.shape == (pair_count, 2)
        and pair_actions.shape == (pair_count, 2)
        and pair_draws.shape == (pair_count, 32, 2)
        and pair_means.shape == (pair_count, 2)
        and pair_classes.shape == (pair_count, 2)
    )
    if not expected_pair_shapes or np.any(pair_anchor < 0) or np.any(pair_anchor >= 9):
        raise LCSRSC3SourceArtifactError("pair arrays are malformed")
    if np.any(pair_classes != LCSRS_ROW_SUPPORTED):
        raise LCSRSC3SourceArtifactError("pair class is not exact SUPPORTED")
    if not np.array_equal(np.mean(pair_draws, axis=1), pair_means):
        raise LCSRSC3SourceArtifactError("pair means disagree with 32 draws")

    records: list[LCSRSAnchorRecord] = []
    seen_pair_ids: set[str] = set()
    for anchor_index, (phase, entry) in enumerate(zip(V023_PHASES, anchors, strict=True)):
        if not isinstance(entry, Mapping):
            raise LCSRSC3SourceArtifactError("anchor index entry is malformed")
        anchor_id = entry.get("anchor_id")
        if entry.get("phase") != phase or not isinstance(anchor_id, str) or not anchor_id:
            raise LCSRSC3SourceArtifactError("anchor identity disagrees with phase order")
        view = assemble_c3_view(
            action_context=arrays["action_context"][anchor_index],
            tokens=arrays["tokens"][anchor_index],
            token_mask=arrays["token_mask"][anchor_index],
            action_mask=arrays["action_mask"][anchor_index],
            reference_actions=arrays["reference_actions"][anchor_index],
        )
        expected_view_digest = _decode_fixed_ascii(
            arrays["anchor_view_content_digest"][anchor_index],
            field="anchor_view_content_digest",
        )
        if view.content_digest != expected_view_digest:
            raise LCSRSC3SourceArtifactError("reconstructed C3View digest disagrees")
        q1 = np.asarray(arrays["q1_values"][anchor_index], dtype=np.float32)
        q2 = np.asarray(arrays["q2_values"][anchor_index], dtype=np.float32)
        q12 = np.asarray(arrays["q12_values"][anchor_index], dtype=np.float32)
        if not np.array_equal(q12, np.asarray(q1 + q2, dtype=np.float32)):
            raise LCSRSC3SourceArtifactError("stored Q12 is not the exact float32 Q1+Q2 sum")
        if bool(entry.get("retained_for_fitting")) != bool(retained[anchor_index]):
            raise LCSRSC3SourceArtifactError("anchor retention JSON/array mismatch")
        selected_pair_rows = np.flatnonzero(pair_anchor == anchor_index)
        topology = entry.get("topology")
        topology_pairs = topology.get("pairs") if isinstance(topology, Mapping) else None
        if not isinstance(topology_pairs, list):
            raise LCSRSC3SourceArtifactError("anchor topology pair list is missing")
        if len(topology_pairs) != selected_pair_rows.size:
            raise LCSRSC3SourceArtifactError("topology and pair sidecar counts disagree")
        pairs: list[LCSRSPairTargets] = []
        for pair_offset, row in enumerate(selected_pair_rows.tolist()):
            pair_id = _decode_fixed_ascii(pair_ids[row], field="pair_id")
            topology_pair = topology_pairs[pair_offset]
            if not isinstance(topology_pair, Mapping) or topology_pair.get("pair_id") != pair_id:
                raise LCSRSC3SourceArtifactError("topology and sidecar pair order disagree")
            if pair_id in seen_pair_ids:
                raise LCSRSC3SourceArtifactError("source artifact repeats a pair id")
            seen_pair_ids.add(pair_id)
            pairs.append(
                LCSRSPairTargets(
                    pair_id=pair_id,
                    user_ids=pair_users[row],
                    action_ids=pair_actions[row],
                    normalized_targets_by_draw=pair_draws[row],
                )
            )
        if not bool(retained[anchor_index]):
            continue
        if not pairs:
            raise LCSRSC3SourceArtifactError("retained anchor has no pair target")
        surface = assemble_lcsrs_anchor_surface(view, pairs)
        surface_entry = entry.get("surface")
        record_entry = (
            surface_entry.get("record") if isinstance(surface_entry, Mapping) else None
        )
        if not isinstance(record_entry, Mapping):
            raise LCSRSC3SourceArtifactError("retained anchor lacks a surface receipt")
        if surface.content_digest != record_entry.get("surface_digest"):
            raise LCSRSC3SourceArtifactError("reconstructed surface digest disagrees")
        record = LCSRSAnchorRecord(
            world_id=world,
            phase=phase,
            anchor_id=anchor_id,
            surface=surface,
            q12_values=np.asarray(q12, dtype=np.float64),
        )
        if record.content_digest != record_entry.get("content_digest"):
            raise LCSRSC3SourceArtifactError("reconstructed anchor record digest disagrees")
        records.append(record)
    return tuple(records)


def load_v023_world_source_artifact(
    index_path: Path,
    *,
    expected_world: int | None = None,
    expected_preflight_sha256: str | None = None,
) -> V023WorldSourceArtifact:
    """Authenticate one source shard and reconstruct every fitting anchor."""

    unresolved_source = Path(index_path)
    if unresolved_source.is_symlink() or not unresolved_source.is_file():
        raise LCSRSC3SourceArtifactError("source index is missing or is a symlink")
    source = unresolved_source.resolve()
    payload = _read_canonical_json(source)
    if payload.get("schema") != V023_SOURCE_SHARD_SCHEMA:
        raise LCSRSC3SourceArtifactError("source shard schema drifted")
    if payload.get("contract_sha256") != V023_CONTRACT_SHA256:
        raise LCSRSC3SourceArtifactError("source contract digest drifted")
    world = payload.get("world")
    if type(world) is not int or world not in V023_WORLDS:
        raise LCSRSC3SourceArtifactError("source world is outside the frozen panel")
    if expected_world is not None and world != expected_world:
        raise LCSRSC3SourceArtifactError("source world disagrees with requested shard")
    if payload.get("source_artifact_schema") != V023_SOURCE_ARTIFACT_SCHEMA:
        raise LCSRSC3SourceArtifactError("source artifact schema drifted")
    if payload.get("source_artifact_version") != V023_SOURCE_ARTIFACT_VERSION:
        raise LCSRSC3SourceArtifactError("source artifact version drifted")
    if payload.get("claim_ceiling") != V023_SOURCE_CLAIM_CEILING:
        raise LCSRSC3SourceArtifactError("source claim ceiling drifted")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise LCSRSC3SourceArtifactError("source artifact is not TRAIN_DEVELOPMENT")
    if (
        payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
    ):
        raise LCSRSC3SourceArtifactError("source artifact crossed a closed boundary")
    if payload.get("execution_addendum_sha256") != V023_EXECUTION_ADDENDUM_SHA256:
        raise LCSRSC3SourceArtifactError("source artifact does not bind the addendum")
    if payload.get("placebo_key_sha256") != V023_PLACEBO_KEY_SHA256:
        raise LCSRSC3SourceArtifactError("source artifact placebo-key digest drifted")
    preflight = _digest(
        payload.get("preflight_manifest_sha256"), field="preflight_manifest_sha256"
    )
    if expected_preflight_sha256 is not None and preflight != expected_preflight_sha256:
        raise LCSRSC3SourceArtifactError("source preflight digest disagrees")

    array_receipt = payload.get("arrays")
    if not isinstance(array_receipt, Mapping) or array_receipt.get("allow_pickle") is not False:
        raise LCSRSC3SourceArtifactError("source array receipt is malformed")
    relative = array_receipt.get("npz_relative_path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise LCSRSC3SourceArtifactError("source NPZ path is unsafe")
    unresolved_sidecar = source.parent / relative
    if unresolved_sidecar.is_symlink() or not unresolved_sidecar.is_file():
        raise LCSRSC3SourceArtifactError("source NPZ is missing or is a symlink")
    sidecar = unresolved_sidecar.resolve()
    if not sidecar.is_relative_to(source.parent.resolve()):
        raise LCSRSC3SourceArtifactError("source NPZ path escapes its shard directory")
    sidecar_sha = _file_sha256(sidecar)
    if sidecar_sha != _digest(array_receipt.get("npz_sha256"), field="npz_sha256"):
        raise LCSRSC3SourceArtifactError("source NPZ byte digest disagrees")
    digest_file = sidecar.with_name(sidecar.name + ".sha256")
    declared_digest_file = array_receipt.get("npz_sha256_file")
    if declared_digest_file not in (None, digest_file.name):
        raise LCSRSC3SourceArtifactError("source NPZ digest-file name disagrees")
    expected_digest_line = f"{sidecar_sha}  {sidecar.name}\n".encode("ascii")
    if digest_file.is_symlink() or not digest_file.is_file() or digest_file.read_bytes() != expected_digest_line:
        raise LCSRSC3SourceArtifactError("source NPZ digest file disagrees")
    metadata = array_receipt.get("array_metadata")
    if not isinstance(metadata, Mapping):
        raise LCSRSC3SourceArtifactError("source array metadata is missing")
    try:
        with np.load(sidecar, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError, KeyError) as error:
        raise LCSRSC3SourceArtifactError("source NPZ cannot be safely loaded") from error
    _verify_array_metadata(arrays, metadata)
    records = _reconstruct_records(world=world, payload=payload, arrays=arrays)
    supported_count = sum(
        int(np.count_nonzero(record.surface.row_class == LCSRS_ROW_SUPPORTED))
        for record in records
    )
    if payload.get("record_count") != len(records):
        raise LCSRSC3SourceArtifactError("source record count disagrees")
    if payload.get("supported_count") != supported_count:
        raise LCSRSC3SourceArtifactError("source supported-row count disagrees")
    pair_count = payload.get("pair_count")
    placebo_eligible = payload.get("placebo_eligible_count")
    if type(pair_count) is not int or pair_count < 0:
        raise LCSRSC3SourceArtifactError("source pair count is malformed")
    if pair_count != int(np.asarray(arrays["pair_anchor_index"]).size):
        raise LCSRSC3SourceArtifactError("source pair count disagrees with sidecar")
    if type(placebo_eligible) is not int or not 0 <= placebo_eligible <= supported_count:
        raise LCSRSC3SourceArtifactError("source placebo-eligible count is malformed")
    expected_placebo_eligible = 0
    if records:
        placebo = build_lcsrs_matched_placebo(
            records,
            placebo_key=V023_PLACEBO_KEY,
        )
        if placebo.placebo_key_sha256 != V023_PLACEBO_KEY_SHA256:
            raise LCSRSC3SourceArtifactError("reconstructed placebo key drifted")
        expected_placebo_eligible = placebo.eligible_supported_rows
    if placebo_eligible != expected_placebo_eligible:
        raise LCSRSC3SourceArtifactError(
            "source placebo-eligible count disagrees with reconstructed strata"
        )
    return V023WorldSourceArtifact(
        world=world,
        index_path=source,
        index_sha256=_file_sha256(source),
        sidecar_path=sidecar,
        sidecar_sha256=sidecar_sha,
        records=records,
        pair_count=pair_count,
        supported_count=supported_count,
        placebo_eligible_count=placebo_eligible,
        index=payload,
    )


__all__ = [
    "V023_SOURCE_ARTIFACT_SCHEMA",
    "V023_SOURCE_ARTIFACT_VERSION",
    "V023_SOURCE_SHARD_SCHEMA",
    "V023_CONTRACT_SHA256",
    "V023_SOURCE_CLAIM_CEILING",
    "V023_EXECUTION_ADDENDUM_SHA256",
    "V023_PLACEBO_KEY_SHA256",
    "V023_PLACEBO_KEY",
    "V023_WORLDS",
    "V023_PHASES",
    "LCSRSC3SourceArtifactError",
    "V023WorldSourceArtifact",
    "load_v023_world_source_artifact",
]
