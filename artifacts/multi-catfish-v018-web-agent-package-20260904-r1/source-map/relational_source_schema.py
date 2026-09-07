"""Pure structured source seam for the provisional V0.18 relational Q3 gate.

This module is preparation only.  It stores predecision features and exact-ZR
labels in a no-pickle NPZ closure, but it never opens a simulator or creates a
source row.  A future learner contract must bind the concrete worlds,
lineages, and target-production runner before this seam is used.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np


SOURCE_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-source-v1"
SOURCE_SCHEMA_VERSION = 1
ACTION_DIM = 28
ACTION_CONTEXT_DIM = 7
VICTIM_TOKEN_DIM = 6
NPZ_FILENAME = "source.npz"
METADATA_FILENAME = "metadata.json"
RECEIPT_FILENAME = "source.sha256"
ARRAY_NAMES = (
    "action_context",
    "victim_tokens",
    "action_mask",
    "victim_mask",
    "positive_credit_compatible",
    "reference_actions",
    "target_surface_bits",
)
FEATURE_FIELDS = ("action_context", "victim_tokens")
ALLOWED_SPLITS = frozenset({"TRAIN", "VALIDATION"})
FROZEN_STATUS = "FROZEN_BEFORE_OUTCOME"

# A source payload is intentionally closed over the two feature tensors.  The
# denylist remains a second guard against callers labelling an outcome-bearing
# field as a feature in metadata or in a future adapter.
FORBIDDEN_FEATURE_TOKENS = frozenset(
    {
        "action_evaluation",
        "actionevaluation",
        "realized",
        "realised",
        "outcome",
        "future",
        "fading",
        "shadow",
        "sinr",
        "rate",
        "energy",
        "power",
        "interference",
        "teacher",
        "target",
        "selected_action",
        "rng",
    }
)


class RelationalSourceError(ValueError):
    """The structured source closure is malformed or violates its seam."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RelationalSourceError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise RelationalSourceError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalSourceError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _owned_array(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise RelationalSourceError(f"{field} cannot be materialised") from error
    result.setflags(write=False)
    return result


def _finite(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    result = _owned_array(value, dtype=dtype, field=field)
    if not np.all(np.isfinite(result)):
        raise RelationalSourceError(f"{field} must be finite")
    return result


def _boolean(value: object, *, shape: tuple[int, ...], field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype != np.bool_:
        raise RelationalSourceError(f"{field} must be Boolean shape {shape}")
    return _owned_array(raw, dtype=np.dtype(np.bool_), field=field)


def _references(value: object, *, rows: int) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (rows,) or not np.issubdtype(raw.dtype, np.integer):
        raise RelationalSourceError(f"reference_actions must be integer shape ({rows},)")
    result = _owned_array(raw, dtype=np.dtype(np.int64), field="reference_actions")
    if np.any(result < 0) or np.any(result >= ACTION_DIM):
        raise RelationalSourceError("reference_actions contains an out-of-range action")
    return result


def validate_feature_fields(fields: Sequence[str]) -> tuple[str, ...]:
    """Validate the closed feature list before any source bytes are written."""

    try:
        values = tuple(str(field) for field in fields)
    except (TypeError, ValueError) as error:
        raise RelationalSourceError("feature_fields must be a sequence of strings") from error
    if values != FEATURE_FIELDS:
        raise RelationalSourceError(
            f"feature_fields must be exactly {FEATURE_FIELDS}, got {values}"
        )
    for field in values:
        normalised = "".join(character.lower() if character.isalnum() else "_" for character in field)
        if any(token in normalised for token in FORBIDDEN_FEATURE_TOKENS):
            raise RelationalSourceError(f"forbidden feature field: {field}")
    return values


def validate_feature_manifest(manifest: Mapping[str, object]) -> tuple[str, ...]:
    """Reject unknown or outcome-bearing feature declarations."""

    if not isinstance(manifest, Mapping):
        raise RelationalSourceError("feature manifest must be a mapping")
    return validate_feature_fields(tuple(manifest.keys()))


@dataclass(frozen=True)
class RelationalZRC3Source:
    """One immutable complete source closure for the structured Q3 learner."""

    action_context: np.ndarray
    victim_tokens: np.ndarray
    action_mask: np.ndarray
    victim_mask: np.ndarray
    positive_credit_compatible: np.ndarray
    reference_actions: np.ndarray
    target_surface_bits: np.ndarray
    world_seed: int
    lineage: int
    split: str
    field_root_digest: str
    kappa_bits: float
    feature_fields: tuple[str, ...] = FEATURE_FIELDS
    schema: str = SOURCE_SCHEMA

    def __post_init__(self) -> None:
        context = _finite(
            self.action_context,
            dtype=np.dtype(np.float64),
            field="action_context",
        )
        if context.ndim != 3 or context.shape[1:] != (ACTION_DIM, ACTION_CONTEXT_DIM):
            raise RelationalSourceError(
                f"action_context must have shape (N,{ACTION_DIM},{ACTION_CONTEXT_DIM})"
            )
        rows = int(context.shape[0])
        if rows < 1:
            raise RelationalSourceError("source closure must contain at least one row")
        victims = _finite(
            self.victim_tokens,
            dtype=np.dtype(np.float64),
            field="victim_tokens",
        )
        if victims.ndim != 4 or victims.shape[0] != rows or victims.shape[1] != ACTION_DIM or victims.shape[3] != VICTIM_TOKEN_DIM:
            raise RelationalSourceError(
                f"victim_tokens must have shape (N,{ACTION_DIM},V,{VICTIM_TOKEN_DIM})"
            )
        victim_count = int(victims.shape[2])
        if victim_count < 1:
            raise RelationalSourceError("victim_tokens must contain at least one victim slot")
        action_mask = _boolean(
            self.action_mask,
            shape=(rows, ACTION_DIM),
            field="action_mask",
        )
        victim_mask = _boolean(
            self.victim_mask,
            shape=(rows, ACTION_DIM, victim_count),
            field="victim_mask",
        )
        compatible = _boolean(
            self.positive_credit_compatible,
            shape=(rows, ACTION_DIM),
            field="positive_credit_compatible",
        )
        references = _references(self.reference_actions, rows=rows)
        row_index = np.arange(rows, dtype=np.int64)
        if not np.all(action_mask[row_index, references]):
            raise RelationalSourceError("every reference action must be legal")
        targets = _finite(
            self.target_surface_bits,
            dtype=np.dtype(np.float64),
            field="target_surface_bits",
        )
        if targets.shape != (rows, ACTION_DIM):
            raise RelationalSourceError(
                f"target_surface_bits must have shape ({rows},{ACTION_DIM})"
            )
        if self.schema != SOURCE_SCHEMA:
            raise RelationalSourceError("unsupported relational source schema")
        if self.split not in ALLOWED_SPLITS:
            raise RelationalSourceError(f"split must be one of {sorted(ALLOWED_SPLITS)}")
        if isinstance(self.world_seed, bool) or not isinstance(self.world_seed, int) or self.world_seed <= 0:
            raise RelationalSourceError("world_seed must be a positive integer")
        if isinstance(self.lineage, bool) or not isinstance(self.lineage, int) or self.lineage <= 0:
            raise RelationalSourceError("lineage must be a positive integer")
        _digest(self.field_root_digest, field="field_root_digest")
        try:
            kappa = float(self.kappa_bits)
        except (TypeError, ValueError, OverflowError) as error:
            raise RelationalSourceError("kappa_bits must be finite and positive") from error
        if not math.isfinite(kappa) or kappa <= 0.0:
            raise RelationalSourceError("kappa_bits must be finite and positive")
        features = validate_feature_fields(self.feature_fields)

        if not np.all(np.any(action_mask, axis=1)):
            raise RelationalSourceError("each source row needs a legal action")
        if np.any(compatible & ~action_mask):
            raise RelationalSourceError("compatibility cannot widen the native action mask")
        if np.any(~action_mask[:, :, None] & victim_mask):
            raise RelationalSourceError("victim_mask cannot widen the native action mask")
        # Victim slots are deliberately opaque at this seam: their mapping to
        # focal-user ids is owned by the future source encoder.  Do not infer a
        # diagonal from array positions (the number of rows and victim slots
        # need not match); the encoder may enforce a no-self-victim invariant
        # when it has that identity information.
        if np.any(context[~action_mask] != 0.0):
            raise RelationalSourceError("illegal action context rows must be zero")
        if np.any(victims[~victim_mask] != 0.0):
            raise RelationalSourceError("masked victim tokens must be zero")
        if np.any(targets[~action_mask] != 0.0):
            raise RelationalSourceError("target surface is nonzero outside the native mask")
        if np.any(targets[row_index, references] != 0.0):
            raise RelationalSourceError("reference target must be exactly zero")
        object.__setattr__(self, "action_context", context)
        object.__setattr__(self, "victim_tokens", victims)
        object.__setattr__(self, "action_mask", action_mask)
        object.__setattr__(self, "victim_mask", victim_mask)
        object.__setattr__(self, "positive_credit_compatible", compatible)
        object.__setattr__(self, "reference_actions", references)
        object.__setattr__(self, "target_surface_bits", targets)
        object.__setattr__(self, "feature_fields", features)
        object.__setattr__(self, "kappa_bits", kappa)

    @property
    def rows(self) -> int:
        return int(self.action_context.shape[0])

    @property
    def victim_count(self) -> int:
        return int(self.victim_tokens.shape[2])

    def arrays_as_mapping(self) -> dict[str, np.ndarray]:
        return {name: np.asarray(getattr(self, name)) for name in ARRAY_NAMES}

    def arrays_sha256(self) -> str:
        return canonical_sha256(
            {name: _array_sha256(value) for name, value in self.arrays_as_mapping().items()}
        )

    def metadata_body(self, *, npz_sha256: str) -> dict[str, object]:
        _digest(npz_sha256, field="npz_sha256")
        return {
            "schema": self.schema,
            "schema_version": SOURCE_SCHEMA_VERSION,
            "npz_filename": NPZ_FILENAME,
            "npz_sha256": npz_sha256,
            "arrays_sha256": self.arrays_sha256(),
            "array_sha256": {
                name: _array_sha256(value) for name, value in self.arrays_as_mapping().items()
            },
            "row_count": self.rows,
            "victim_count": self.victim_count,
            "world_seed": self.world_seed,
            "lineage": self.lineage,
            "split": self.split,
            "field_root_digest": self.field_root_digest,
            "kappa_bits_hex": float(self.kappa_bits).hex(),
            "feature_fields": list(self.feature_fields),
            "label_fields": ["positive_credit_compatible", "target_surface_bits"],
            "target_semantics": "exact-ZR-centered-surface-label-only",
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
        }

    def metadata(self, *, npz_sha256: str) -> dict[str, object]:
        body = self.metadata_body(npz_sha256=npz_sha256)
        return {**body, "metadata_sha256": canonical_sha256(body)}


def validate_world_split(records: Sequence[Mapping[str, object] | RelationalZRC3Source]) -> dict[int, str]:
    """Ensure no complete world is assigned to both TRAIN and VALIDATION."""

    assignments: dict[int, str] = {}
    for index, record in enumerate(records):
        if isinstance(record, RelationalZRC3Source):
            world = record.world_seed
            split = record.split
        elif isinstance(record, Mapping):
            try:
                world = int(record["world_seed"])
                split = str(record["split"])
            except (KeyError, TypeError, ValueError) as error:
                raise RelationalSourceError(f"world split record {index} is malformed") from error
        else:
            raise RelationalSourceError(f"world split record {index} is not a mapping/source")
        if world <= 0 or split not in ALLOWED_SPLITS:
            raise RelationalSourceError(f"world split record {index} has invalid identity")
        previous = assignments.get(world)
        if previous is not None and previous != split:
            raise RelationalSourceError(
                f"world {world} appears in both {previous} and {split} splits"
            )
        assignments[world] = split
    if not assignments:
        raise RelationalSourceError("world split closure must not be empty")
    return assignments


def write_source_shard(output_dir: str | Path, source: RelationalZRC3Source) -> dict[str, str]:
    """Write NPZ, canonical metadata, and receipt exactly once."""

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise RelationalSourceError(f"refusing to overwrite {destination}")
    source.arrays_sha256()
    destination.mkdir(parents=True, exist_ok=False)
    npz_path = destination / NPZ_FILENAME
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{NPZ_FILENAME}.", suffix=".tmp.npz", dir=destination
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        np.savez_compressed(
            temporary,
            **{name: np.asarray(value) for name, value in source.arrays_as_mapping().items()},
        )
        os.link(temporary, npz_path)
    except FileExistsError as error:
        raise RelationalSourceError(f"refusing to overwrite {npz_path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    npz_sha256 = file_sha256(npz_path)
    metadata_path = destination / METADATA_FILENAME
    metadata_payload = source.metadata(npz_sha256=npz_sha256)
    metadata_bytes = _canonical_bytes(metadata_payload)
    if metadata_path.exists() or metadata_path.is_symlink():
        raise RelationalSourceError(f"refusing to overwrite {metadata_path}")
    metadata_path.write_bytes(metadata_bytes)
    receipt_path = destination / RECEIPT_FILENAME
    receipt = (
        f"schema={SOURCE_SCHEMA}\n"
        f"npz_sha256={npz_sha256}\n"
        f"metadata_sha256={file_sha256(metadata_path)}\n"
        f"arrays_sha256={source.arrays_sha256()}\n"
    ).encode("ascii")
    if receipt_path.exists() or receipt_path.is_symlink():
        raise RelationalSourceError(f"refusing to overwrite {receipt_path}")
    receipt_path.write_bytes(receipt)
    return {
        "output_dir": str(destination),
        "npz": str(npz_path),
        "metadata": str(metadata_path),
        "receipt": str(receipt_path),
        "npz_sha256": npz_sha256,
        "metadata_sha256": file_sha256(metadata_path),
        "arrays_sha256": source.arrays_sha256(),
    }


def _read_metadata(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise RelationalSourceError(f"missing metadata file: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RelationalSourceError(f"metadata is not canonical JSON: {path}") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise RelationalSourceError(f"metadata is not canonical JSON: {path}")
    supplied = payload.get("metadata_sha256")
    _digest(supplied, field="metadata_sha256")
    body = {key: value for key, value in payload.items() if key != "metadata_sha256"}
    if canonical_sha256(body) != supplied:
        raise RelationalSourceError("metadata digest disagrees with its body")
    return payload


def _read_receipt(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise RelationalSourceError(f"missing source receipt: {path}")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise RelationalSourceError(f"source receipt is not ASCII: {path}") from error
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise RelationalSourceError("source receipt contains a malformed line")
        key, value = line.split("=", 1)
        if key in values or key not in {"schema", "npz_sha256", "metadata_sha256", "arrays_sha256"}:
            raise RelationalSourceError("source receipt contains an unknown or duplicate field")
        values[key] = value
    if set(values) != {"schema", "npz_sha256", "metadata_sha256", "arrays_sha256"}:
        raise RelationalSourceError("source receipt is incomplete")
    _digest(values["npz_sha256"], field="receipt.npz_sha256")
    _digest(values["metadata_sha256"], field="receipt.metadata_sha256")
    _digest(values["arrays_sha256"], field="receipt.arrays_sha256")
    if values["schema"] != SOURCE_SCHEMA:
        raise RelationalSourceError("source receipt schema is stale")
    return values


def read_source_shard(output_dir: str | Path) -> RelationalZRC3Source:
    """Read and fully authenticate one no-pickle source shard."""

    root = Path(output_dir)
    metadata = _read_metadata(root / METADATA_FILENAME)
    receipt = _read_receipt(root / RECEIPT_FILENAME)
    npz_path = root / NPZ_FILENAME
    if npz_path.is_symlink() or not npz_path.is_file():
        raise RelationalSourceError(f"missing NPZ source file: {npz_path}")
    expected_npz = _digest(metadata.get("npz_sha256"), field="npz_sha256")
    if file_sha256(npz_path) != expected_npz:
        raise RelationalSourceError("NPZ digest disagrees with metadata")
    if receipt["npz_sha256"] != expected_npz:
        raise RelationalSourceError("source receipt disagrees with metadata NPZ digest")
    if receipt["metadata_sha256"] != file_sha256(root / METADATA_FILENAME):
        raise RelationalSourceError("source receipt disagrees with metadata file digest")
    if (
        metadata.get("schema") != SOURCE_SCHEMA
        or metadata.get("schema_version") != SOURCE_SCHEMA_VERSION
        or metadata.get("npz_filename") != NPZ_FILENAME
    ):
        raise RelationalSourceError("source schema is stale")
    if metadata.get("test_split_opened") is not False or metadata.get("episode_training") is not False or metadata.get("learner_update") is not False:
        raise RelationalSourceError("source metadata crosses the learner boundary")
    if tuple(metadata.get("feature_fields", ())) != FEATURE_FIELDS:
        raise RelationalSourceError("source feature field list is not closed")
    validate_feature_fields(tuple(metadata["feature_fields"]))
    if metadata.get("label_fields") != ["positive_credit_compatible", "target_surface_bits"]:
        raise RelationalSourceError("source label field list is not closed")
    if metadata.get("target_semantics") != "exact-ZR-centered-surface-label-only":
        raise RelationalSourceError("source target semantics are stale")
    array_digests = metadata.get("array_sha256")
    if not isinstance(array_digests, dict) or set(array_digests) != set(ARRAY_NAMES):
        raise RelationalSourceError("source array digest map is incomplete")
    for name in ARRAY_NAMES:
        _digest(array_digests[name], field=f"array_sha256.{name}")
    try:
        kappa = float.fromhex(str(metadata["kappa_bits_hex"]))
        with np.load(npz_path, allow_pickle=False) as loaded:
            if set(loaded.files) != set(ARRAY_NAMES):
                raise RelationalSourceError("NPZ contains unexpected or missing arrays")
            arrays = {name: np.array(loaded[name], copy=True) for name in ARRAY_NAMES}
    except (KeyError, OSError, ValueError, TypeError) as error:
        raise RelationalSourceError("source NPZ is malformed or uses pickle") from error
    source = RelationalZRC3Source(
        **arrays,
        world_seed=int(metadata["world_seed"]),
        lineage=int(metadata["lineage"]),
        split=str(metadata["split"]),
        field_root_digest=str(metadata["field_root_digest"]),
        kappa_bits=kappa,
        feature_fields=tuple(metadata["feature_fields"]),
    )
    if source.rows != int(metadata.get("row_count", -1)) or source.victim_count != int(metadata.get("victim_count", -1)):
        raise RelationalSourceError("source row/victim count disagrees with metadata")
    if source.arrays_sha256() != metadata.get("arrays_sha256"):
        raise RelationalSourceError("source array digest disagrees with metadata")
    if receipt["arrays_sha256"] != source.arrays_sha256():
        raise RelationalSourceError("source receipt disagrees with array digest")
    for name in ARRAY_NAMES:
        digest = array_digests[name]
        if digest != _array_sha256(source.arrays_as_mapping()[name]):
            raise RelationalSourceError(f"source array digest disagrees for {name}")
    return source


def read_and_validate_world_split(paths: Sequence[str | Path]) -> tuple[RelationalZRC3Source, ...]:
    """Read a source closure and apply the complete-world split rule."""

    sources = tuple(read_source_shard(path) for path in paths)
    validate_world_split(sources)
    return sources


__all__ = [
    "ACTION_CONTEXT_DIM",
    "ACTION_DIM",
    "ALLOWED_SPLITS",
    "ARRAY_NAMES",
    "FEATURE_FIELDS",
    "FROZEN_STATUS",
    "NPZ_FILENAME",
    "RelationalSourceError",
    "RelationalZRC3Source",
    "SOURCE_SCHEMA",
    "VICTIM_TOKEN_DIM",
    "canonical_sha256",
    "file_sha256",
    "read_and_validate_world_split",
    "read_source_shard",
    "validate_feature_fields",
    "validate_feature_manifest",
    "validate_world_split",
    "write_source_shard",
]
