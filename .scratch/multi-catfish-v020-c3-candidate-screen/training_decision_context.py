"""Fail-closed V0.20 TRAIN-only loss-context conversion.

This module is deliberately model-independent.  It converts an authenticated
V0.19 evaluation-only decision-context sidecar into a new, closed artifact
containing only detached background scores, native legal masks, and row
identity.  It never imports the simulator, a learner, torch, or the V0.19
runtime.  The exact ZR label and the relational state stay outside this seam.

Conversion is intentionally not discoverable from sidecar metadata alone:
the caller must provide a :class:`TrainingDecisionContextBinding` containing
the expected source and context digests and the frozen world/lineage
identities.  This prevents a convenient but unbound sidecar from becoming a
training input by accident.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from types import MappingProxyType
from typing import Any

import numpy as np


LEGACY_DECISION_CONTEXT_SCHEMA = (
    "multi-catfish-mcrl-v018-relational-zr-decision-context-v1"
)
LEGACY_DECISION_CONTEXT_SCHEMA_VERSION = 1
TRAINING_CONTEXT_SCHEMA = "multi-catfish-mcrl-v020-training-decision-context-v1"
TRAINING_CONTEXT_SCHEMA_VERSION = 1

DECISION_CONTEXT_METADATA_FILENAME = "decision-context.json"
DECISION_CONTEXT_NPZ_FILENAME = "decision-context.npz"
DECISION_CONTEXT_RECEIPT_FILENAME = "decision-context.sha256"
TRAINING_CONTEXT_METADATA_FILENAME = "training-decision-context.json"
TRAINING_CONTEXT_NPZ_FILENAME = "training-decision-context.npz"
TRAINING_CONTEXT_RECEIPT_FILENAME = "training-decision-context.sha256"

SIDECAR_ARRAY_NAMES = (
    "background_q12",
    "action_mask",
    "reference_actions",
    "step_indices",
    "user_indices",
)
TRAINING_ARRAY_NAMES = SIDECAR_ARRAY_NAMES

EXPECTED_STEPS = 10
EXPECTED_USERS = 100
EXPECTED_ROWS = EXPECTED_STEPS * EXPECTED_USERS
ACTION_DIM = 28
TRAIN_SPLIT = "TRAIN"
SIDECAR_STATUS = "IMPLEMENTATION_ONLY_NO_OUTCOME"
TRAINING_CONTEXT_STATUS = "IMPLEMENTATION_ONLY_LOSS_CONTEXT"
BACKGROUND_SEMANTICS = "detached-Q1-plus-learned-Q2-native-surface"

_SIDECAR_RECEIPT_FIELDS = (
    "schema",
    "metadata_sha256",
    "npz_sha256",
    "arrays_sha256",
    "decision_context_sha256",
)
_TRAINING_RECEIPT_FIELDS = (
    "schema",
    "metadata_sha256",
    "npz_sha256",
    "arrays_sha256",
    "training_context_sha256",
)


class TrainingDecisionContextError(ValueError):
    """A sidecar, binding, or loss-context closure violated its seam."""


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
        raise TrainingDecisionContextError(
            "payload is not finite canonical JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    """Return the V0.19-compatible digest of canonical JSON."""

    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: str | Path) -> str:
    """Hash one regular, non-symlink file."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise TrainingDecisionContextError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def arrays_sha256(arrays: Mapping[str, object]) -> str:
    """Digest a closed mapping with the same byte contract as V0.19."""

    return canonical_sha256(
        {name: _array_sha256(value) for name, value in arrays.items()}
    )


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise TrainingDecisionContextError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TrainingDecisionContextError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise TrainingDecisionContextError(f"{field} must be a positive integer")
    return result


def _positive_float_hex(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise TrainingDecisionContextError(f"{field} must be a hexadecimal float string")
    try:
        parsed = float.fromhex(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise TrainingDecisionContextError(
            f"{field} must be a hexadecimal float string"
        ) from error
    if not math.isfinite(parsed) or parsed <= 0.0 or parsed.hex() != value:
        raise TrainingDecisionContextError(
            f"{field} must be a canonical finite positive hexadecimal float"
        )
    return value


def _require_bool(value: object, *, field: str, expected: bool) -> None:
    if value is not expected:
        raise TrainingDecisionContextError(
            f"{field} must be exactly {str(expected).lower()}"
        )


def _require_text(value: object, *, field: str, expected: str) -> None:
    if value != expected:
        raise TrainingDecisionContextError(f"{field} must be {expected!r}")


def _read_canonical_json(path: Path, *, field: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise TrainingDecisionContextError(f"{field} is not a regular file: {path}")
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TrainingDecisionContextError(f"{field} is not valid JSON") from error
    if not isinstance(value, dict):
        raise TrainingDecisionContextError(f"{field} must be a JSON object")
    if _canonical_bytes(value) != raw:
        raise TrainingDecisionContextError(f"{field} is not canonical JSON")
    return value


def _read_receipt(
    path: Path,
    *,
    expected_fields: tuple[str, ...],
    expected_schema: str,
) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise TrainingDecisionContextError(f"receipt is not a regular file: {path}")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise TrainingDecisionContextError("receipt is not ASCII") from error
    if len(lines) != len(expected_fields):
        raise TrainingDecisionContextError("receipt fields are not closed")
    result: dict[str, str] = {}
    for line in lines:
        key, separator, value = line.partition("=")
        if not separator or key in result or not value:
            raise TrainingDecisionContextError("receipt fields are malformed")
        result[key] = value
    if tuple(result) != expected_fields:
        raise TrainingDecisionContextError("receipt fields are not closed")
    if result["schema"] != expected_schema:
        raise TrainingDecisionContextError("receipt schema is stale")
    for field in expected_fields[1:]:
        _digest(result[field], field=f"receipt.{field}")
    return result


def _reject_symlinks(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise TrainingDecisionContextError(
            f"context root is not a regular directory: {root}"
        )
    try:
        paths = root.rglob("*")
    except OSError as error:
        raise TrainingDecisionContextError("context root cannot be walked") from error
    for path in paths:
        if path.is_symlink():
            raise TrainingDecisionContextError(f"context closure contains a symlink: {path}")


def _owned_array(
    value: object,
    *,
    dtype: np.dtype[Any],
    shape: tuple[int, ...],
    field: str,
    finite: bool = True,
) -> np.ndarray:
    try:
        array = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise TrainingDecisionContextError(f"{field} cannot be materialised") from error
    if array.shape != shape or array.dtype != dtype:
        raise TrainingDecisionContextError(
            f"{field} must have dtype {dtype} and shape {shape}"
        )
    if finite and np.issubdtype(dtype, np.number) and not np.all(np.isfinite(array)):
        raise TrainingDecisionContextError(f"{field} must be finite")
    array.setflags(write=False)
    return array


def _validate_context_arrays(
    arrays: Mapping[str, object],
    *,
    field_prefix: str,
) -> dict[str, np.ndarray]:
    if tuple(arrays) != SIDECAR_ARRAY_NAMES:
        raise TrainingDecisionContextError(
            f"{field_prefix} arrays are not closed: {tuple(arrays)}"
        )
    background = _owned_array(
        arrays["background_q12"],
        dtype=np.dtype(np.float64),
        shape=(EXPECTED_ROWS, ACTION_DIM),
        field=f"{field_prefix}.background_q12",
    )
    mask = _owned_array(
        arrays["action_mask"],
        dtype=np.dtype(np.bool_),
        shape=(EXPECTED_ROWS, ACTION_DIM),
        field=f"{field_prefix}.action_mask",
        finite=False,
    )
    references = _owned_array(
        arrays["reference_actions"],
        dtype=np.dtype(np.int64),
        shape=(EXPECTED_ROWS,),
        field=f"{field_prefix}.reference_actions",
        finite=False,
    )
    steps = _owned_array(
        arrays["step_indices"],
        dtype=np.dtype(np.int64),
        shape=(EXPECTED_ROWS,),
        field=f"{field_prefix}.step_indices",
        finite=False,
    )
    users = _owned_array(
        arrays["user_indices"],
        dtype=np.dtype(np.int64),
        shape=(EXPECTED_ROWS,),
        field=f"{field_prefix}.user_indices",
        finite=False,
    )
    if not np.all(np.any(mask, axis=1)):
        raise TrainingDecisionContextError(
            f"{field_prefix}.action_mask has a row without a legal action"
        )
    if np.any(references < 0) or np.any(references >= ACTION_DIM):
        raise TrainingDecisionContextError(
            f"{field_prefix}.reference_actions contains an out-of-range action"
        )
    row_index = np.arange(EXPECTED_ROWS, dtype=np.int64)
    if not np.all(mask[row_index, references]):
        raise TrainingDecisionContextError(
            f"{field_prefix}.reference_actions contains an illegal action"
        )
    expected_steps = np.repeat(np.arange(EXPECTED_STEPS, dtype=np.int64), EXPECTED_USERS)
    expected_users = np.tile(np.arange(EXPECTED_USERS, dtype=np.int64), EXPECTED_STEPS)
    if not np.array_equal(steps, expected_steps) or not np.array_equal(users, expected_users):
        raise TrainingDecisionContextError(
            f"{field_prefix} row ordering is not the exact 10x100 identity"
        )
    with np.errstate(over="raise", invalid="raise"):
        try:
            expected_references = np.argmax(
                np.where(mask, background, -np.inf), axis=1
            ).astype(np.int64, copy=False)
        except FloatingPointError as error:
            raise TrainingDecisionContextError(
                f"{field_prefix} background argmax is non-finite"
            ) from error
    if not np.array_equal(references, expected_references):
        raise TrainingDecisionContextError(
            f"{field_prefix}.reference_actions must equal the native masked argmax"
        )
    return {
        "background_q12": background,
        "action_mask": mask,
        "reference_actions": references,
        "step_indices": steps,
        "user_indices": users,
    }


def _check_digest_fields(metadata: Mapping[str, object], fields: tuple[str, ...], *, prefix: str) -> None:
    for field in fields:
        _digest(metadata.get(field), field=f"{prefix}.{field}")


@dataclass(frozen=True)
class TrainingDecisionContextBinding:
    """Explicit provenance required to convert one V0.19 sidecar.

    All digest fields are required rather than inferred from the input path.
    The source digest authenticates the detached Q1/Q2 source closure; the
    context digests authenticate the exact evaluation-only sidecar bytes,
    arrays, and row identity.
    """

    source_arrays_sha256: str
    decision_context_metadata_sha256: str
    decision_context_npz_sha256: str
    decision_context_arrays_sha256: str
    decision_context_sha256: str
    row_identity_sha256: str
    field_root_digest: str
    kappa_bits_hex: str
    world_seed: int
    lineage: int
    contract_sha256: str
    config_sha256: str
    code_manifest_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "source_arrays_sha256",
            "decision_context_metadata_sha256",
            "decision_context_npz_sha256",
            "decision_context_arrays_sha256",
            "decision_context_sha256",
            "row_identity_sha256",
            "field_root_digest",
            "contract_sha256",
            "config_sha256",
            "code_manifest_sha256",
        ):
            _digest(getattr(self, field), field=field)
        _positive_int(self.world_seed, field="world_seed")
        _positive_int(self.lineage, field="lineage")
        _positive_float_hex(self.kappa_bits_hex, field="kappa_bits_hex")


@dataclass(frozen=True)
class TrainingDecisionContext:
    """Immutable, model-independent arrays and authenticated provenance."""

    background_q12: np.ndarray
    action_mask: np.ndarray
    reference_actions: np.ndarray
    step_indices: np.ndarray
    user_indices: np.ndarray
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        arrays = _validate_context_arrays(
            {
                "background_q12": self.background_q12,
                "action_mask": self.action_mask,
                "reference_actions": self.reference_actions,
                "step_indices": self.step_indices,
                "user_indices": self.user_indices,
            },
            field_prefix="training_context",
        )
        for name, value in arrays.items():
            object.__setattr__(self, name, value)
        if not isinstance(self.metadata, Mapping):
            raise TrainingDecisionContextError("training_context metadata must be a mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def world_seed(self) -> int:
        return int(self.metadata["world_seed"])

    @property
    def lineage(self) -> int:
        return int(self.metadata["lineage"])

    @property
    def kappa_bits(self) -> float:
        return float.fromhex(str(self.metadata["kappa_bits_hex"]))


def _validate_binding(
    metadata: Mapping[str, object],
    *,
    binding: TrainingDecisionContextBinding,
    metadata_sha256: str,
    npz_sha256: str,
    arrays: Mapping[str, np.ndarray],
) -> None:
    if not isinstance(binding, TrainingDecisionContextBinding):
        raise TrainingDecisionContextError(
            "binding must be TrainingDecisionContextBinding"
        )
    _require_text(metadata.get("schema"), field="sidecar.schema", expected=LEGACY_DECISION_CONTEXT_SCHEMA)
    if metadata.get("schema_version") != LEGACY_DECISION_CONTEXT_SCHEMA_VERSION:
        raise TrainingDecisionContextError("sidecar schema version is stale")
    _require_text(metadata.get("status"), field="sidecar.status", expected=SIDECAR_STATUS)
    _require_bool(metadata.get("evaluation_only"), field="sidecar.evaluation_only", expected=True)
    _require_bool(metadata.get("learner_loadable"), field="sidecar.learner_loadable", expected=False)
    _require_bool(metadata.get("test_split_opened"), field="sidecar.test_split_opened", expected=False)
    _require_bool(metadata.get("episode_training"), field="sidecar.episode_training", expected=False)
    _require_bool(metadata.get("learner_update"), field="sidecar.learner_update", expected=False)
    _require_text(metadata.get("split"), field="sidecar.split", expected=TRAIN_SPLIT)
    _positive_float_hex(metadata.get("kappa_bits_hex"), field="sidecar.kappa_bits_hex")
    if metadata.get("kappa_bits_hex") != binding.kappa_bits_hex:
        raise TrainingDecisionContextError(
            "sidecar kappa_bits_hex does not match explicit binding"
        )
    _require_text(
        metadata.get("background_semantics"),
        field="sidecar.background_semantics",
        expected=BACKGROUND_SEMANTICS,
    )
    for field in (
        "source_arrays_sha256",
        "field_root_digest",
        "contract_sha256",
        "config_sha256",
        "code_manifest_sha256",
    ):
        _digest(metadata.get(field), field=f"sidecar.{field}")
    expected_metadata = {
        "source_arrays_sha256": binding.source_arrays_sha256,
        "field_root_digest": binding.field_root_digest,
        "contract_sha256": binding.contract_sha256,
        "config_sha256": binding.config_sha256,
        "code_manifest_sha256": binding.code_manifest_sha256,
    }
    for field, expected in expected_metadata.items():
        if metadata.get(field) != expected:
            raise TrainingDecisionContextError(
                f"sidecar {field} does not match explicit binding"
            )
    if metadata_sha256 != binding.decision_context_metadata_sha256:
        raise TrainingDecisionContextError(
            "sidecar metadata_sha256 does not match explicit binding"
        )
    if npz_sha256 != binding.decision_context_npz_sha256:
        raise TrainingDecisionContextError(
            "sidecar decision_context_npz_sha256 does not match explicit binding"
        )
    if metadata.get("arrays_sha256") != binding.decision_context_arrays_sha256:
        raise TrainingDecisionContextError(
            "sidecar decision_context_arrays_sha256 does not match explicit binding"
        )
    if metadata.get("decision_context_sha256") != binding.decision_context_sha256:
        raise TrainingDecisionContextError(
            "sidecar decision_context_sha256 does not match explicit binding"
        )
    if metadata.get("row_identity_sha256") != binding.row_identity_sha256:
        raise TrainingDecisionContextError(
            "sidecar row_identity_sha256 does not match explicit binding"
        )
    for field, expected in (("world_seed", binding.world_seed), ("lineage", binding.lineage)):
        if metadata.get(field) != expected:
            raise TrainingDecisionContextError(
                f"sidecar {field} does not match explicit binding"
            )
    if metadata.get("declared_worlds") != [binding.world_seed]:
        raise TrainingDecisionContextError("sidecar declared_worlds is not exact")
    if metadata.get("declared_lineages") != [binding.lineage]:
        raise TrainingDecisionContextError("sidecar declared_lineages is not exact")
    if metadata.get("rows") != EXPECTED_ROWS or metadata.get("steps") != EXPECTED_STEPS or metadata.get("users") != EXPECTED_USERS:
        raise TrainingDecisionContextError("sidecar row dimensions are not the V0.19 10x100 closure")
    if metadata.get("array_names") != list(SIDECAR_ARRAY_NAMES):
        raise TrainingDecisionContextError("sidecar array list is not closed")
    array_digests = metadata.get("array_sha256")
    if not isinstance(array_digests, Mapping) or set(array_digests) != set(SIDECAR_ARRAY_NAMES):
        raise TrainingDecisionContextError("sidecar array digest map is not closed")
    for name in SIDECAR_ARRAY_NAMES:
        _digest(array_digests.get(name), field=f"sidecar.array_sha256.{name}")
        if array_digests[name] != _array_sha256(arrays[name]):
            raise TrainingDecisionContextError(f"sidecar {name} array digest mismatch")
    if arrays_sha256(arrays) != metadata.get("arrays_sha256"):
        raise TrainingDecisionContextError("sidecar arrays_sha256 mismatch")
    expected_row_digest = arrays_sha256(
        {"step_indices": arrays["step_indices"], "user_indices": arrays["user_indices"]}
    )
    if expected_row_digest != metadata.get("row_identity_sha256"):
        raise TrainingDecisionContextError("sidecar row identity digest mismatch")
    if metadata.get("npz_filename") != DECISION_CONTEXT_NPZ_FILENAME:
        raise TrainingDecisionContextError("sidecar NPZ filename is not closed")


def _read_evaluation_sidecar(
    sidecar_dir: str | Path,
) -> tuple[dict[str, np.ndarray], dict[str, object], dict[str, str], str, str]:
    root = Path(sidecar_dir)
    _reject_symlinks(root)
    metadata_path = root / DECISION_CONTEXT_METADATA_FILENAME
    npz_path = root / DECISION_CONTEXT_NPZ_FILENAME
    receipt_path = root / DECISION_CONTEXT_RECEIPT_FILENAME
    metadata = _read_canonical_json(metadata_path, field="sidecar metadata")
    receipt = _read_receipt(
        receipt_path,
        expected_fields=_SIDECAR_RECEIPT_FIELDS,
        expected_schema=LEGACY_DECISION_CONTEXT_SCHEMA,
    )
    supplied_context_digest = _digest(
        metadata.get("decision_context_sha256"),
        field="sidecar.decision_context_sha256",
    )
    body = {
        key: value
        for key, value in metadata.items()
        if key != "decision_context_sha256"
    }
    if canonical_sha256(body) != supplied_context_digest:
        raise TrainingDecisionContextError("sidecar metadata self-digest failed")
    metadata_sha256 = file_sha256(metadata_path)
    npz_sha256 = file_sha256(npz_path)
    if receipt["metadata_sha256"] != metadata_sha256:
        raise TrainingDecisionContextError("sidecar metadata file digest mismatch")
    if receipt["npz_sha256"] != npz_sha256 or metadata.get("npz_sha256") != npz_sha256:
        raise TrainingDecisionContextError("sidecar NPZ digest mismatch")
    if receipt["decision_context_sha256"] != supplied_context_digest:
        raise TrainingDecisionContextError("sidecar context receipt digest mismatch")
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            if tuple(loaded.files) != SIDECAR_ARRAY_NAMES:
                raise TrainingDecisionContextError("sidecar NPZ keys are not closed")
            raw_arrays = {
                name: np.array(loaded[name], copy=True, order="C")
                for name in SIDECAR_ARRAY_NAMES
            }
    except TrainingDecisionContextError:
        raise
    except (OSError, ValueError, TypeError) as error:
        raise TrainingDecisionContextError("sidecar NPZ is malformed") from error
    arrays = _validate_context_arrays(raw_arrays, field_prefix="sidecar")
    if receipt["arrays_sha256"] != metadata.get("arrays_sha256"):
        raise TrainingDecisionContextError("sidecar receipt arrays digest mismatch")
    return arrays, metadata, receipt, metadata_sha256, npz_sha256


def _training_metadata_body(
    *,
    arrays: Mapping[str, np.ndarray],
    binding: TrainingDecisionContextBinding,
    npz_sha256: str,
) -> dict[str, object]:
    return {
        "array_names": list(TRAINING_ARRAY_NAMES),
        "array_sha256": {
            name: _array_sha256(arrays[name]) for name in TRAINING_ARRAY_NAMES
        },
        "arrays_sha256": arrays_sha256(arrays),
        "background_semantics": BACKGROUND_SEMANTICS,
        "code_manifest_sha256": binding.code_manifest_sha256,
        "config_sha256": binding.config_sha256,
        "contract_sha256": binding.contract_sha256,
        "declared_lineages": [binding.lineage],
        "declared_worlds": [binding.world_seed],
        "episode_training": False,
        "field_root_digest": binding.field_root_digest,
        "forward_input_fields": [],
        "gradient_input": False,
        "gradient_fields": [],
        "kappa_bits_hex": binding.kappa_bits_hex,
        "lineage": binding.lineage,
        "loss_context_loadable": True,
        "loss_context_fields": [
            "background_q12",
            "action_mask",
            "reference_actions",
        ],
        "loss_only": True,
        "model_input": False,
        "model_forward_loadable": False,
        "model_fields": [],
        "model_independent": True,
        "npz_filename": TRAINING_CONTEXT_NPZ_FILENAME,
        "npz_sha256": npz_sha256,
        "row_identity_sha256": binding.row_identity_sha256,
        "rows": EXPECTED_ROWS,
        "schema": TRAINING_CONTEXT_SCHEMA,
        "schema_version": TRAINING_CONTEXT_SCHEMA_VERSION,
        "source_arrays_sha256": binding.source_arrays_sha256,
        "source_context_arrays_sha256": binding.decision_context_arrays_sha256,
        "source_context_metadata_sha256": binding.decision_context_metadata_sha256,
        "source_context_npz_sha256": binding.decision_context_npz_sha256,
        "source_context_schema": LEGACY_DECISION_CONTEXT_SCHEMA,
        "source_context_sha256": binding.decision_context_sha256,
        "source_row_identity_sha256": binding.row_identity_sha256,
        "split": TRAIN_SPLIT,
        "state_input": False,
        "state_fields": [],
        "status": TRAINING_CONTEXT_STATUS,
        "steps": EXPECTED_STEPS,
        "test_split_opened": False,
        "users": EXPECTED_USERS,
        "world_seed": binding.world_seed,
    }


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise TrainingDecisionContextError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(payload)
        os.link(temporary, path)
    except FileExistsError as error:
        raise TrainingDecisionContextError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return file_sha256(path)


def _write_training_npz(root: Path, arrays: Mapping[str, np.ndarray]) -> str:
    path = root / TRAINING_CONTEXT_NPZ_FILENAME
    if path.exists() or path.is_symlink():
        raise TrainingDecisionContextError(f"refusing to overwrite {path}")
    root.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp.npz", dir=root
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as handle:
            np.savez_compressed(
                handle,
                **{name: np.ascontiguousarray(arrays[name]) for name in TRAINING_ARRAY_NAMES},
            )
        os.link(temporary, path)
    except FileExistsError as error:
        raise TrainingDecisionContextError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return file_sha256(path)


def convert_evaluation_sidecar(
    sidecar_dir: str | Path,
    output_dir: str | Path,
    *,
    binding: TrainingDecisionContextBinding,
) -> TrainingDecisionContext:
    """Convert one authenticated V0.19 TRAIN sidecar to a loss-only artifact.

    ``binding`` is keyword-only and has no default by design.  No candidate
    loss, learner, gradient, simulator, source state, or TEST access occurs.
    """

    arrays, metadata, receipt, metadata_sha256, npz_sha256 = _read_evaluation_sidecar(
        sidecar_dir
    )
    _validate_binding(
        metadata,
        binding=binding,
        metadata_sha256=metadata_sha256,
        npz_sha256=npz_sha256,
        arrays=arrays,
    )
    if receipt["arrays_sha256"] != metadata["arrays_sha256"]:
        raise TrainingDecisionContextError("sidecar arrays receipt is not bound")
    destination = Path(output_dir)
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise TrainingDecisionContextError(
            f"output root is not a regular directory: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise TrainingDecisionContextError(
            "output root must be empty for a closed training context"
        )
    output_npz_sha256 = _write_training_npz(destination, arrays)
    body = _training_metadata_body(
        arrays=arrays,
        binding=binding,
        npz_sha256=output_npz_sha256,
    )
    metadata_with_digest = {
        **body,
        "training_context_sha256": canonical_sha256(body),
    }
    output_metadata_path = destination / TRAINING_CONTEXT_METADATA_FILENAME
    output_metadata_sha256 = _write_once(
        output_metadata_path,
        _canonical_bytes(metadata_with_digest),
    )
    receipt_values = {
        "schema": TRAINING_CONTEXT_SCHEMA,
        "metadata_sha256": output_metadata_sha256,
        "npz_sha256": output_npz_sha256,
        "arrays_sha256": body["arrays_sha256"],
        "training_context_sha256": metadata_with_digest["training_context_sha256"],
    }
    _write_once(
        destination / TRAINING_CONTEXT_RECEIPT_FILENAME,
        "".join(f"{key}={receipt_values[key]}\n" for key in _TRAINING_RECEIPT_FIELDS).encode(
            "ascii"
        ),
    )
    return load_training_decision_context(destination)


def load_training_decision_context(
    context_dir: str | Path,
) -> TrainingDecisionContext:
    """Re-authenticate a V0.20 loss-only context artifact."""

    root = Path(context_dir)
    _reject_symlinks(root)
    expected_files = {
        TRAINING_CONTEXT_METADATA_FILENAME,
        TRAINING_CONTEXT_NPZ_FILENAME,
        TRAINING_CONTEXT_RECEIPT_FILENAME,
    }
    if {path.name for path in root.iterdir()} != expected_files:
        raise TrainingDecisionContextError("training context file closure is not exact")
    metadata_path = root / TRAINING_CONTEXT_METADATA_FILENAME
    npz_path = root / TRAINING_CONTEXT_NPZ_FILENAME
    metadata = _read_canonical_json(metadata_path, field="training context metadata")
    receipt = _read_receipt(
        root / TRAINING_CONTEXT_RECEIPT_FILENAME,
        expected_fields=_TRAINING_RECEIPT_FIELDS,
        expected_schema=TRAINING_CONTEXT_SCHEMA,
    )
    supplied = _digest(
        metadata.get("training_context_sha256"),
        field="training_context_sha256",
    )
    body = {key: value for key, value in metadata.items() if key != "training_context_sha256"}
    if canonical_sha256(body) != supplied:
        raise TrainingDecisionContextError("training context metadata self-digest failed")
    if metadata.get("schema") != TRAINING_CONTEXT_SCHEMA or metadata.get("schema_version") != TRAINING_CONTEXT_SCHEMA_VERSION:
        raise TrainingDecisionContextError("training context schema is stale")
    _require_text(metadata.get("status"), field="training context.status", expected=TRAINING_CONTEXT_STATUS)
    _require_text(metadata.get("split"), field="training context.split", expected=TRAIN_SPLIT)
    _require_text(metadata.get("source_context_schema"), field="source_context_schema", expected=LEGACY_DECISION_CONTEXT_SCHEMA)
    _require_text(
        metadata.get("background_semantics"),
        field="training context.background_semantics",
        expected=BACKGROUND_SEMANTICS,
    )
    _require_bool(metadata.get("model_independent"), field="model_independent", expected=True)
    for field in (
        "gradient_input",
        "model_input",
        "state_input",
        "model_forward_loadable",
        "episode_training",
        "test_split_opened",
    ):
        _require_bool(metadata.get(field), field=field, expected=False)
    for field in ("loss_context_loadable", "loss_only"):
        _require_bool(metadata.get(field), field=field, expected=True)
    for field in ("forward_input_fields", "gradient_fields", "model_fields", "state_fields"):
        if metadata.get(field) != []:
            raise TrainingDecisionContextError(f"{field} must be empty for a loss-only context")
    if metadata.get("loss_context_fields") != [
        "background_q12",
        "action_mask",
        "reference_actions",
    ]:
        raise TrainingDecisionContextError("loss_context_fields are not closed")
    if metadata.get("array_names") != list(TRAINING_ARRAY_NAMES):
        raise TrainingDecisionContextError("training context array list is not closed")
    if metadata.get("npz_filename") != TRAINING_CONTEXT_NPZ_FILENAME:
        raise TrainingDecisionContextError("training context NPZ filename is not closed")
    _check_digest_fields(
        metadata,
        (
            "source_arrays_sha256",
            "source_context_arrays_sha256",
            "source_context_metadata_sha256",
            "source_context_npz_sha256",
            "source_context_sha256",
            "source_row_identity_sha256",
            "row_identity_sha256",
            "field_root_digest",
            "contract_sha256",
            "config_sha256",
            "code_manifest_sha256",
        ),
        prefix="training_context",
    )
    world_seed = _positive_int(metadata.get("world_seed"), field="world_seed")
    lineage = _positive_int(metadata.get("lineage"), field="lineage")
    _positive_float_hex(metadata.get("kappa_bits_hex"), field="kappa_bits_hex")
    if metadata.get("declared_worlds") != [world_seed] or metadata.get("declared_lineages") != [lineage]:
        raise TrainingDecisionContextError("training context world/lineage declaration is not exact")
    if metadata.get("rows") != EXPECTED_ROWS or metadata.get("steps") != EXPECTED_STEPS or metadata.get("users") != EXPECTED_USERS:
        raise TrainingDecisionContextError("training context dimensions are not exact")
    metadata_sha256 = file_sha256(metadata_path)
    npz_sha256 = file_sha256(npz_path)
    if receipt["metadata_sha256"] != metadata_sha256:
        raise TrainingDecisionContextError("training context metadata digest mismatch")
    if receipt["npz_sha256"] != npz_sha256 or metadata.get("npz_sha256") != npz_sha256:
        raise TrainingDecisionContextError("training context NPZ digest mismatch")
    if receipt["training_context_sha256"] != supplied:
        raise TrainingDecisionContextError("training context receipt self-digest mismatch")
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            if tuple(loaded.files) != TRAINING_ARRAY_NAMES:
                raise TrainingDecisionContextError("training context NPZ keys are not closed")
            raw_arrays = {
                name: np.array(loaded[name], copy=True, order="C")
                for name in TRAINING_ARRAY_NAMES
            }
    except TrainingDecisionContextError:
        raise
    except (OSError, ValueError, TypeError) as error:
        raise TrainingDecisionContextError("training context NPZ is malformed") from error
    arrays = _validate_context_arrays(raw_arrays, field_prefix="training_context")
    array_digests = metadata.get("array_sha256")
    if not isinstance(array_digests, Mapping) or set(array_digests) != set(TRAINING_ARRAY_NAMES):
        raise TrainingDecisionContextError("training context array digest map is not closed")
    for name in TRAINING_ARRAY_NAMES:
        _digest(array_digests.get(name), field=f"training_context.array_sha256.{name}")
        if array_digests[name] != _array_sha256(arrays[name]):
            raise TrainingDecisionContextError(f"training context {name} digest mismatch")
    if arrays_sha256(arrays) != metadata.get("arrays_sha256") or receipt["arrays_sha256"] != metadata.get("arrays_sha256"):
        raise TrainingDecisionContextError("training context arrays digest mismatch")
    expected_row_digest = arrays_sha256(
        {"step_indices": arrays["step_indices"], "user_indices": arrays["user_indices"]}
    )
    if expected_row_digest != metadata.get("row_identity_sha256") or metadata.get("source_row_identity_sha256") != metadata.get("row_identity_sha256"):
        raise TrainingDecisionContextError("training context row identity digest mismatch")
    return TrainingDecisionContext(**arrays, metadata=metadata)


# A descriptive alias makes the conversion boundary easy to discover while
# retaining the explicit name used by the V0.19 sidecar contract.
convert_evaluation_decision_context = convert_evaluation_sidecar


__all__ = [
    "ACTION_DIM",
    "DECISION_CONTEXT_METADATA_FILENAME",
    "DECISION_CONTEXT_NPZ_FILENAME",
    "DECISION_CONTEXT_RECEIPT_FILENAME",
    "EXPECTED_ROWS",
    "EXPECTED_STEPS",
    "EXPECTED_USERS",
    "LEGACY_DECISION_CONTEXT_SCHEMA",
    "SIDECAR_ARRAY_NAMES",
    "TRAINING_ARRAY_NAMES",
    "TRAINING_CONTEXT_METADATA_FILENAME",
    "TRAINING_CONTEXT_NPZ_FILENAME",
    "TRAINING_CONTEXT_RECEIPT_FILENAME",
    "TRAINING_CONTEXT_SCHEMA",
    "TrainingDecisionContext",
    "TrainingDecisionContextBinding",
    "TrainingDecisionContextError",
    "arrays_sha256",
    "canonical_sha256",
    "convert_evaluation_decision_context",
    "convert_evaluation_sidecar",
    "file_sha256",
    "load_training_decision_context",
]
