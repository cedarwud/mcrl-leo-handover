#!/usr/bin/env python3
"""Independent, fail-closed verification of one V0.23 fit artifact.

The fit producer is deliberately outside this module.  This verifier reads
only canonical JSON and numeric NumPy sidecars and uses no project imports.
It authenticates the source manifest and all eight source shards, rebuilds the
held-out SUPPORTED-row identity/target table from the source arrays, and then
checks every fit-side binding (model, metrics, loss receipt, and placebo).

The serialized logical C3 parameter digest is retained as an *unverified*
assertion.  Its algorithm is owned by the production head and the fit schema
does not contain enough information to recompute it with stdlib + NumPy.  The
successful report therefore has a non-PASS status and an explicit gap; it is
never a scientific or gate decision.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any, Mapping, Sequence

import numpy as np


V023_GATE_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1"
V023_FIT_SCHEMA = f"{V023_GATE_SCHEMA}-fit-shard"
V023_SOURCE_MANIFEST_SCHEMA = f"{V023_GATE_SCHEMA}-source-manifest"
V023_SOURCE_SHARD_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-observability-gate-v1-source-shard"
)
V023_SOURCE_ARTIFACT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-source-artifact-v1"
V023_SOURCE_ARTIFACT_VERSION = 1
V023_FIT_MODEL_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-model-v1"
V023_FIT_METRICS_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-metrics-v1"
V023_FIT_PLACEBO_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-placebo-v1"
V023_FIT_RECEIPT_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-fit-receipt-v1"
V023_SOURCE_ARRAY_DOMAIN = "source-array-v1"
V023_FIT_MODEL_ARRAY_DOMAIN = "v023-fit-model-array-v1"
V023_FIT_PREDICTION_ARRAY_DOMAIN = "v023-fit-prediction-array-v1"
# These are copied from the versioned Interface-A contract rather than
# imported from the runtime state module.  Recomputing the view digest is
# independent of the production encoder and catches a resealed NPZ whose
# feature bytes no longer describe the authenticated view.
V023_C3_VIEW_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-c3-view-v1"
V023_C3_VIEW_SCHEMA_VERSION = 1
V023_C3_VIEW_SCHEMA_SHA256 = (
    "c1c455c7207048c29b3b58218a59dd67852ec8d2077c417181f1f7e07300cbe6"
)
V023_C3_VIEW_CONFIG_SHA256 = (
    "c406a6a2a0da78a855c8f850c45803cfa1763a3e7e40823693b39207f14c3324"
)
V023_PLACEBO_SCHEMA = "multi-catfish-mcrl-v023-matched-placebo-v1"
V023_PLACEBO_KEY = "MCRL_V023_LCSRS_MATCHED_PLACEBO_V1"
V023_PLACEBO_KEY_SHA256 = (
    "7dc54ab9323b60b30a1bfdbde60872b1f825e4b142dac2c0c0f2269d147a0825"
)
V023_CONTRACT_SHA256 = (
    "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5"
)
V023_EXECUTION_ADDENDUM_SHA256 = (
    "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
)
V023_CLAIM_CEILING = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
V023_GATE_WORLDS = tuple(range(2026121801, 2026121809))
V023_STUDENT_SEEDS = (2026135201, 2026135202, 2026135203)
V023_FIT_ARMS = ("INFORMED", "MATCHED_PLACEBO")
V023_PHASES = tuple(range(1, 10))
V023_ACTION_COUNT = 28
V023_DRAW_COUNT = 32
V023_FIT_UPDATE_COUNT = 2000
V023_FIT_BATCH_SIZE = 256
V023_LEARNER_CONFIG_SHA256 = (
    "6b1c31bb4ccddf19a9e07e13713d2ebb1a4d4555620299257a7a641f0f29111a"
)
V023_INITIAL_NETWORK_SHA256_BY_SEED = {
    2026135201: "106d23119468eb472babffe78a49c439296a232d8c5481d2aa8cb2890ec08a6f",
    2026135202: "c726537fd8a309249cbb9eb674ab6c22e663925400112fd01c7a4f790398f56b",
    2026135203: "016cebc7d0b69a6938a1547c4e400ce3afb2b1cf6e16ce8b6ca72408db427080",
}
V023_PLACEBO_MIN_COVERAGE = 0.80
V023_SIGN_THRESHOLD = 0.02


class V023FitIndependentVerificationError(RuntimeError):
    """A fit artifact cannot be independently authenticated."""


# Friendly aliases make the custom error discoverable without coupling callers
# to one spelling.  They all intentionally refer to the same type.
V023FitArtifactVerificationError = V023FitIndependentVerificationError
V023IndependentFitVerificationError = V023FitIndependentVerificationError


def _canonical_bytes(value: object) -> bytes:
    """Encode the exact canonical ASCII JSON representation."""

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = item
        return result

    try:
        # ``value`` is normally already parsed.  The hooks are used by the
        # parser below; allow_nan=False protects values introduced by callers.
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023FitIndependentVerificationError(
            "value is not finite canonical JSON"
        ) from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _parse_json(raw: bytes, *, field: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("ascii"),
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {token}")
            ),
            object_pairs_hook=lambda pairs: _unique_object(pairs),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise V023FitIndependentVerificationError(
            f"{field} is not finite ASCII JSON"
        ) from error
    if not isinstance(value, dict):
        raise V023FitIndependentVerificationError(f"{field} root is not an object")
    canonical = _canonical_bytes(value)
    if raw not in (canonical, canonical + b"\n"):
        raise V023FitIndependentVerificationError(f"{field} is not canonical JSON")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, item in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = item
    return result


def _load_json(path: Path, *, field: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023FitIndependentVerificationError(
            f"{field} is missing or is a symlink"
        )
    return _parse_json(target.read_bytes(), field=field)


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023FitIndependentVerificationError(
            f"{field} is not a lowercase SHA-256"
        )
    return value


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023FitIndependentVerificationError(f"expected regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_child(root: Path, relative: object, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise V023FitIndependentVerificationError(
            f"{field} is not a safe relative path"
        )
    base = Path(root).resolve()
    candidate = base / relative
    # Reject symlink components as well as a symlink at the final path.  A
    # resolved path which remains under base is not enough for an immutable
    # artifact boundary if an intermediate component is replaceable.
    current = base
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise V023FitIndependentVerificationError(f"{field} is a symlink")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(base):
        raise V023FitIndependentVerificationError(f"{field} escapes its root")
    return resolved


def _verify_receipt_seal(payload: Mapping[str, Any], *, field: str) -> None:
    declared = _digest(payload.get("receipt_sha256"), field=f"{field}.receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if canonical_sha256(unsigned) != declared:
        raise V023FitIndependentVerificationError(f"{field} receipt seal disagrees")


def _verify_digest_file(path: Path, *, digest: str, target_name: str, field: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise V023FitIndependentVerificationError(f"{field} digest sidecar is missing")
    expected = f"{digest}  {target_name}\n".encode("ascii")
    if path.read_bytes() != expected:
        raise V023FitIndependentVerificationError(
            f"{field} digest sidecar disagrees"
        )


def _array_digest(array: object, *, domain: str) -> str:
    value = np.ascontiguousarray(np.asarray(array))
    if value.dtype == object:
        raise V023FitIndependentVerificationError("object dtype is forbidden")
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(repr(tuple(value.shape)).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _digest_named_array(digest: "hashlib._Hash", name: str, value: np.ndarray) -> None:
    """Append one named array using the frozen C3View hash convention."""

    array = np.ascontiguousarray(value)
    digest.update(name.encode("ascii"))
    digest.update(b"\0")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _digest_dataset_array(
    digest: "hashlib._Hash", name: str, value: np.ndarray
) -> None:
    """Append one dataset array using the frozen surface/record convention.

    The C3View digest above deliberately inserts ``NUL`` after each field
    name.  The dataset module's historical ``_digest_array`` convention does
    not; keeping this helper separate is necessary for byte-for-byte parity
    with production ``LCSRSAnchorSurface`` and ``LCSRSAnchorRecord`` digests.
    """

    array = np.ascontiguousarray(value)
    digest.update(name.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _c3_view_digest(
    action_context: np.ndarray,
    tokens: np.ndarray,
    token_mask: np.ndarray,
    action_mask: np.ndarray,
    reference_actions: np.ndarray,
) -> str:
    """Recompute the Interface-A content digest without importing runtime code."""

    digest = hashlib.sha256()
    digest.update(V023_C3_VIEW_SCHEMA.encode("ascii"))
    digest.update(struct.pack(">I", V023_C3_VIEW_SCHEMA_VERSION))
    digest.update(V023_C3_VIEW_SCHEMA_SHA256.encode("ascii"))
    digest.update(V023_C3_VIEW_CONFIG_SHA256.encode("ascii"))
    for name, value in (
        ("action_context", action_context),
        ("tokens", tokens),
        ("token_mask", token_mask),
        ("action_mask", action_mask),
        ("reference_actions", reference_actions),
    ):
        _digest_named_array(digest, name, value)
    return digest.hexdigest()


def _verify_c3_view_arrays(
    action_context: np.ndarray,
    tokens: np.ndarray,
    token_mask: np.ndarray,
    action_mask: np.ndarray,
    reference_actions: np.ndarray,
    *,
    expected_digest: str,
) -> None:
    """Apply the pure C3View invariants to one source anchor.

    This mirrors the data-only portion of the production ``C3View.verify``
    implementation.  No model, simulator, or encoder is needed to check the
    shape, mask, sentinel, boundedness, and content-digest contract.
    """

    contexts = np.asarray(action_context)
    token_values = np.asarray(tokens)
    token_masks = np.asarray(token_mask)
    action_masks = np.asarray(action_mask)
    references = np.asarray(reference_actions)
    if (
        contexts.dtype != np.dtype(np.float32)
        or contexts.ndim != 3
        or contexts.shape[1:] != (V023_ACTION_COUNT, 29)
    ):
        raise V023FitIndependentVerificationError("C3View action_context is malformed")
    users = int(contexts.shape[0])
    if users < 1:
        raise V023FitIndependentVerificationError("C3View has no users")
    if token_values.dtype != np.dtype(np.float32) or token_values.shape != (
        users,
        V023_ACTION_COUNT,
        users + 1,
        38,
    ):
        raise V023FitIndependentVerificationError("C3View tokens are malformed")
    if token_masks.dtype != np.dtype(np.bool_) or token_masks.shape != (
        users,
        V023_ACTION_COUNT,
        users + 1,
    ):
        raise V023FitIndependentVerificationError("C3View token_mask is malformed")
    if action_masks.dtype != np.dtype(np.bool_) or action_masks.shape != (
        users,
        V023_ACTION_COUNT,
    ):
        raise V023FitIndependentVerificationError("C3View action_mask is malformed")
    if references.dtype != np.dtype(np.int64) or references.shape != (users,):
        raise V023FitIndependentVerificationError("C3View reference_actions are malformed")
    _check_array_numeric(contexts, field="C3View action_context")
    _check_array_numeric(token_values, field="C3View tokens")
    if np.any(~np.any(action_masks, axis=1)):
        raise V023FitIndependentVerificationError("C3View user has no legal action")
    if np.any(references < 0) or np.any(references >= V023_ACTION_COUNT):
        raise V023FitIndependentVerificationError("C3View reference action is out of range")
    if not np.all(action_masks[np.arange(users), references]):
        raise V023FitIndependentVerificationError("C3View reference action is illegal")
    if not np.array_equal(token_masks[:, :, users], action_masks):
        raise V023FitIndependentVerificationError("C3View pair-token mask disagrees")
    if np.any(token_masks[:, :, :users] & ~action_masks[:, :, None]):
        raise V023FitIndependentVerificationError("C3View ordinary-token mask widens action mask")
    if np.any(contexts[~action_masks] != 0.0) or np.any(token_values[~action_masks] != 0.0):
        raise V023FitIndependentVerificationError("C3View illegal rows are not zero-filled")
    if np.any(token_values[~token_masks] != 0.0):
        raise V023FitIndependentVerificationError("C3View masked tokens are not zero-filled")
    bounded = np.float32(1.0 + 32.0 * np.finfo(np.float32).eps)
    if np.any(np.abs(contexts[action_masks]) > bounded) or np.any(
        np.abs(token_values[token_masks]) > bounded
    ):
        raise V023FitIndependentVerificationError("C3View features are outside [-1,1]")
    context_binary = contexts[:, :, [3, *range(4, 11), 12, 13, 16, 17, 22]][action_masks]
    if np.any((context_binary != 0.0) & (context_binary != 1.0)):
        raise V023FitIndependentVerificationError("C3View Boolean context is not binary")
    relation = contexts[:, :, 4:10][action_masks]
    if np.any(np.sum(relation, axis=1) > 1.0):
        raise V023FitIndependentVerificationError("C3View candidate relation is not one-hot")
    ordinary = token_masks[:, :, :users]
    ordinary_values = token_values[:, :, :users, :]
    if np.any(ordinary_values[:, :, :, 0][ordinary] != 1.0) or np.any(
        ordinary_values[:, :, :, 1][ordinary] != 0.0
    ):
        raise V023FitIndependentVerificationError("C3View ordinary token type drifted")
    ordinary_binary = ordinary_values[:, :, :, [*range(0, 8), *range(22, 28), *range(30, 33)]][ordinary]
    if np.any((ordinary_binary != 0.0) & (ordinary_binary != 1.0)):
        raise V023FitIndependentVerificationError("C3View ordinary token Boolean field drifted")
    pair = token_values[:, :, users, :]
    if np.any(pair[:, :, 0][action_masks] != 0.0) or np.any(
        pair[:, :, 1][action_masks] != 1.0
    ):
        raise V023FitIndependentVerificationError("C3View pair token type drifted")
    status = pair[:, :, 2:5]
    legal_status = status[action_masks]
    if np.any((legal_status != 0.0) & (legal_status != 1.0)):
        raise V023FitIndependentVerificationError("C3View pair status is not binary")
    pair_binary = pair[:, :, [*range(0, 8), *range(16, 19), *range(22, 25)]][action_masks]
    if np.any((pair_binary != 0.0) & (pair_binary != 1.0)):
        raise V023FitIndependentVerificationError("C3View pair Boolean field drifted")
    if np.any(legal_status[:, 1] > legal_status[:, 0]) or np.any(
        legal_status[:, 2] > legal_status[:, 1]
    ):
        raise V023FitIndependentVerificationError("C3View pair status sentinels are inconsistent")
    no_partner = action_masks & (status[:, :, 0] == 0.0)
    unsupported = action_masks & (status[:, :, 0] == 1.0) & (status[:, :, 1] == 0.0)
    if np.any(pair[no_partner, 2:] != 0.0) or np.any(pair[unsupported, 5:] != 0.0):
        raise V023FitIndependentVerificationError("C3View pair status sentinel is not zero-filled")
    actual_digest = _c3_view_digest(
        contexts, token_values, token_masks, action_masks, references
    )
    if actual_digest != expected_digest:
        raise V023FitIndependentVerificationError("reconstructed C3View digest disagrees")


def _surface_digest(
    view_digest: str,
    targets: np.ndarray,
    row_class: np.ndarray,
    pairs: Sequence[tuple[str, np.ndarray, np.ndarray, np.ndarray]],
) -> str:
    """Recompute the immutable anchor-surface digest from numeric S rows."""

    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-anchor-surface-v1")
    digest.update(view_digest.encode("ascii"))
    _digest_dataset_array(digest, "targets", targets)
    _digest_dataset_array(digest, "row_class", row_class)
    for pair_id, users, actions, draws in pairs:
        encoded = pair_id.encode("utf-8")
        digest.update(struct.pack(">I", len(encoded)))
        digest.update(encoded)
        _digest_dataset_array(digest, "pair_users", users)
        _digest_dataset_array(digest, "pair_actions", actions)
        _digest_dataset_array(digest, "pair_draw_targets", draws)
    return digest.hexdigest()


def _anchor_record_digest(
    *, world: int, phase: int, anchor_id: str, surface_digest: str, q12: np.ndarray
) -> str:
    """Recompute the source record digest used in fit/placebo identities."""

    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-anchor-record-v1")
    digest.update(struct.pack(">QI", world, phase))
    encoded = anchor_id.encode("utf-8")
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)
    digest.update(surface_digest.encode("ascii"))
    _digest_dataset_array(digest, "q12", q12)
    return digest.hexdigest()


def _json_float_array(value: object, *, shape: tuple[int, ...], field: str) -> np.ndarray:
    """Materialise a finite JSON numeric matrix for optional source receipts."""

    try:
        array = np.array(value, dtype=np.float64, copy=True, order="C")
    except (TypeError, ValueError, OverflowError) as error:
        raise V023FitIndependentVerificationError(f"{field} is not numeric") from error
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise V023FitIndependentVerificationError(f"{field} shape/value is malformed")
    return array


def _check_array_numeric(array: np.ndarray, *, field: str) -> None:
    if array.dtype == object:
        raise V023FitIndependentVerificationError(f"{field} contains object dtype")
    if not array.flags.c_contiguous:
        raise V023FitIndependentVerificationError(f"{field} is not C-contiguous")
    if not np.issubdtype(array.dtype, np.number):
        # Fixed ASCII identity arrays are checked separately and are not sent
        # through this helper.
        raise V023FitIndependentVerificationError(f"{field} is not numeric")
    try:
        finite = np.all(np.isfinite(array))
    except TypeError as error:
        raise V023FitIndependentVerificationError(
            f"{field} cannot be checked for finiteness"
        ) from error
    if not finite:
        raise V023FitIndependentVerificationError(f"{field} contains non-finite values")


def _decode_ascii(value: object, *, field: str) -> str:
    array = np.asarray(value)
    if array.shape != () or array.dtype.kind != "S":
        raise V023FitIndependentVerificationError(
            f"{field} is not fixed-width ASCII"
        )
    raw = bytes(array.item()).rstrip(b"\0")
    if not raw:
        raise V023FitIndependentVerificationError(f"{field} is empty")
    try:
        result = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise V023FitIndependentVerificationError(f"{field} is not ASCII") from error
    if "\0" in result:
        raise V023FitIndependentVerificationError(f"{field} contains an embedded NUL")
    return result


def _fixed_int(array: np.ndarray, *, field: str) -> np.ndarray:
    value = np.asarray(array)
    if value.dtype == object or not np.issubdtype(value.dtype, np.integer):
        raise V023FitIndependentVerificationError(f"{field} is not an integer array")
    if not value.flags.c_contiguous:
        raise V023FitIndependentVerificationError(f"{field} is not C-contiguous")
    return value


def _assert_scalar(actual: object, expected: object, *, field: str) -> None:
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        raise V023FitIndependentVerificationError(f"{field} is not numeric")
    try:
        left = float(actual)
        right = float(expected)
    except (TypeError, ValueError, OverflowError) as error:
        raise V023FitIndependentVerificationError(
            f"{field} is not numeric"
        ) from error
    if not math.isfinite(left) or not math.isfinite(right):
        raise V023FitIndependentVerificationError(f"{field} is non-finite")
    tolerance = max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * max(1.0, abs(left), abs(right)))
    if abs(left - right) > tolerance:
        raise V023FitIndependentVerificationError(f"{field} disagrees")


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise V023FitIndependentVerificationError(f"{field} is not an object")
    return value


def _int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise V023FitIndependentVerificationError(f"{field} is not an integer")
    return value


def _float(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V023FitIndependentVerificationError(f"{field} is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise V023FitIndependentVerificationError(f"{field} is non-finite")
    return result


def _bool(value: object, *, field: str) -> bool:
    if type(value) is not bool:
        raise V023FitIndependentVerificationError(f"{field} is not a boolean")
    return value


def _load_npz(
    *,
    root: Path,
    binding: Mapping[str, Any],
    domain: str,
    field: str,
    exact_keys: set[str] | None = None,
) -> tuple[Path, str, dict[str, np.ndarray], Mapping[str, Any]]:
    if binding.get("allow_pickle") is not False:
        raise V023FitIndependentVerificationError(f"{field} does not forbid pickle")
    path = _safe_child(root, binding.get("npz_relative_path"), field=f"{field} path")
    digest = _digest(binding.get("npz_sha256"), field=f"{field} SHA-256")
    actual = file_sha256(path)
    if actual != digest:
        raise V023FitIndependentVerificationError(f"{field} byte hash disagrees")
    digest_name = binding.get("npz_sha256_file")
    if not isinstance(digest_name, str) or digest_name != f"{path.name}.sha256":
        raise V023FitIndependentVerificationError(f"{field} digest path drifted")
    digest_path = _safe_child(root, digest_name, field=f"{field} digest")
    _verify_digest_file(digest_path, digest=digest, target_name=path.name, field=field)
    metadata = _mapping(binding.get("array_metadata"), field=f"{field} metadata")
    try:
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True, order="C") for name in archive.files}
    except Exception as error:
        raise V023FitIndependentVerificationError(
            f"{field} NPZ cannot be loaded safely"
        ) from error
    if exact_keys is not None and set(arrays) != exact_keys:
        raise V023FitIndependentVerificationError(f"{field} keys drifted")
    if set(arrays) != set(metadata):
        raise V023FitIndependentVerificationError(f"{field} keys disagree with metadata")
    for name, array in arrays.items():
        if array.dtype == object:
            raise V023FitIndependentVerificationError(f"{field} array {name} contains object dtype")
        if not array.flags.c_contiguous:
            raise V023FitIndependentVerificationError(f"{field} array {name} is not C-contiguous")
        entry = _mapping(metadata[name], field=f"{field} metadata[{name}]")
        if entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023FitIndependentVerificationError(f"{field} array {name} shape/dtype disagrees")
        if entry.get("sha256") != _array_digest(array, domain=domain):
            raise V023FitIndependentVerificationError(f"{field} array {name} digest disagrees")
    return path, digest, arrays, metadata


def _load_source_npz(
    index_path: Path,
    binding: Mapping[str, Any],
) -> tuple[Path, str, dict[str, np.ndarray], Mapping[str, Any]]:
    """Source variant: metadata is nested under ``arrays`` in the index."""

    if binding.get("schema") != f"{V023_SOURCE_ARTIFACT_SCHEMA}-arrays-v1":
        raise V023FitIndependentVerificationError("source arrays schema drifted")
    if type(binding.get("array_count")) is not int:
        raise V023FitIndependentVerificationError("source arrays count is malformed")
    if binding.get("profile_order") != ["00", "10", "01", "11"]:
        raise V023FitIndependentVerificationError("source profile order drifted")
    if binding.get("draw_count") != V023_DRAW_COUNT:
        raise V023FitIndependentVerificationError("source draw count drifted")

    result = _load_npz(
        root=Path(index_path).parent,
        binding=binding,
        domain=V023_SOURCE_ARRAY_DOMAIN,
        field="source arrays",
    )
    if binding["array_count"] != len(result[2]):
        raise V023FitIndependentVerificationError("source arrays count disagrees")
    return result


@dataclass(frozen=True)
class _SourceRow:
    world: int
    anchor_index: int
    anchor_id: str
    phase: int
    user: int
    action: int
    target: float
    anchor_digest: str
    reference_action: int
    q12: np.ndarray
    context: np.ndarray
    action_mask: bool
    opening: bool


@dataclass(frozen=True)
class _SourceAnchor:
    world: int
    anchor_index: int
    anchor_id: str
    phase: int
    content_digest: str
    surface_digest: str
    target_surface: np.ndarray
    supported_rows: tuple[_SourceRow, ...]
    q12: np.ndarray
    context: np.ndarray
    action_mask: np.ndarray
    opening: np.ndarray
    reference: np.ndarray


@dataclass(frozen=True)
class _SourceWorld:
    world: int
    path: Path
    index_digest: str
    payload: Mapping[str, Any]
    anchors: tuple[_SourceAnchor, ...]
    pair_count: int
    supported_count: int


def _validate_source_identity(
    payload: Mapping[str, Any], *, world: int, preflight: str
) -> None:
    if payload.get("schema") != V023_SOURCE_SHARD_SCHEMA:
        raise V023FitIndependentVerificationError("source shard schema drifted")
    if payload.get("status") != "PASS":
        raise V023FitIndependentVerificationError("source shard is not PASS")
    if payload.get("claim_ceiling") != V023_CLAIM_CEILING:
        raise V023FitIndependentVerificationError("source claim ceiling drifted")
    if payload.get("contract_sha256") != V023_CONTRACT_SHA256:
        raise V023FitIndependentVerificationError("source contract hash drifted")
    if payload.get("preflight_manifest_sha256") != preflight:
        raise V023FitIndependentVerificationError("source preflight hash drifted")
    if payload.get("world") != world or world not in V023_GATE_WORLDS:
        raise V023FitIndependentVerificationError("source world identity drifted")
    if payload.get("source_artifact_schema") != V023_SOURCE_ARTIFACT_SCHEMA:
        raise V023FitIndependentVerificationError("source artifact schema drifted")
    if payload.get("source_artifact_version") != V023_SOURCE_ARTIFACT_VERSION:
        raise V023FitIndependentVerificationError("source artifact version drifted")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023FitIndependentVerificationError("source split drifted")
    if payload.get("execution_addendum_sha256") != V023_EXECUTION_ADDENDUM_SHA256:
        raise V023FitIndependentVerificationError("source addendum hash drifted")
    if payload.get("placebo_key_sha256") != V023_PLACEBO_KEY_SHA256:
        raise V023FitIndependentVerificationError("source placebo key hash drifted")
    if payload.get("placebo_key") != V023_PLACEBO_KEY:
        raise V023FitIndependentVerificationError("source placebo key drifted")
    for name in ("enumeration", "topology", "teacher", "surface"):
        value = _mapping(payload.get(name), field=f"source {name}")
        declared = _digest(payload.get(f"{name}_sha256"), field=f"source {name} sha256")
        if canonical_sha256(value) != declared:
            raise V023FitIndependentVerificationError(f"source {name} canonical digest disagrees")
    world_receipt = _mapping(payload.get("world_receipt"), field="source world receipt")
    if (
        world_receipt.get("world") != world
        or world_receipt.get("phase_count") != 9
        or world_receipt.get("test_split_opened") is not False
        or world_receipt.get("learner_update") is not False
        or world_receipt.get("episode_training") is not False
    ):
        raise V023FitIndependentVerificationError("source world receipt identity/boundary drifted")
    q12_background = _mapping(payload.get("q12_background"), field="source Q1/Q2 background")
    if q12_background.get("q12_unit") != "authenticated-normalized-q1-plus-q2-float32":
        raise V023FitIndependentVerificationError("source Q1/Q2 unit drifted")
    if (
        payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
    ):
        raise V023FitIndependentVerificationError("source crossed a closed boundary")


def _require_source_arrays(arrays: Mapping[str, np.ndarray]) -> None:
    required = {
        "anchor_phase",
        "anchor_status",
        "anchor_retained",
        "anchor_content_digest",
        "anchor_view_content_digest",
        "anchor_topology_content_digest",
        "action_context",
        "tokens",
        "token_mask",
        "action_mask",
        "opening_feasibility",
        "reference_actions",
        "physical_keys",
        "q1_values",
        "q2_values",
        "q12_values",
        "pair_anchor_index",
        "pair_id",
        "pair_user_ids",
        "pair_action_ids",
        "pair_target_by_draw",
        "pair_target_mean",
        "pair_class",
        "pair_retained",
    }
    missing = sorted(required - set(arrays))
    if missing:
        raise V023FitIndependentVerificationError(
            f"source arrays omit required fields: {missing}"
        )


def _source_array_shape_checks(
    arrays: Mapping[str, np.ndarray], *, field: str
) -> tuple[int, int, int]:
    _require_source_arrays(arrays)
    phases = arrays["anchor_phase"]
    if phases.dtype != np.dtype(np.int64) or phases.shape != (9,) or tuple(phases.tolist()) != V023_PHASES:
        raise V023FitIndependentVerificationError("source anchor phase array is not 1..9")
    retained = arrays["anchor_retained"]
    if retained.dtype != np.bool_ or retained.shape != (9,):
        raise V023FitIndependentVerificationError("source anchor retained array is malformed")
    status = arrays["anchor_status"]
    if status.dtype != np.dtype(np.uint8) or status.shape != (9,) or not np.array_equal(status, retained.astype(np.uint8)):
        raise V023FitIndependentVerificationError("source anchor status/retention array disagrees")
    anchor_count = 9
    action_count = V023_ACTION_COUNT
    context = arrays["action_context"]
    if context.dtype != np.dtype(np.float32) or context.ndim != 4 or context.shape[0] != anchor_count:
        raise V023FitIndependentVerificationError("source action_context shape/dtype drifted")
    if context.shape[2:] != (action_count, 29):
        raise V023FitIndependentVerificationError("source action_context shape drifted")
    users = int(context.shape[1])
    expected = {
        "tokens": ((anchor_count, users, action_count, users + 1, 38), np.float32),
        "token_mask": ((anchor_count, users, action_count, users + 1), np.bool_),
        "action_mask": ((anchor_count, users, action_count), np.bool_),
        "opening_feasibility": ((anchor_count, users, action_count), np.bool_),
        "reference_actions": ((anchor_count, users), np.int64),
        "physical_keys": ((anchor_count, users, action_count, 2), np.int64),
    }
    for name, (shape, dtype) in expected.items():
        value = arrays[name]
        if value.dtype != np.dtype(dtype) or value.shape != shape:
            raise V023FitIndependentVerificationError(
                f"source {name} shape/dtype drifted"
            )
    for name in ("q1_values", "q2_values", "q12_values"):
        value = arrays[name]
        if value.dtype != np.dtype(np.float64) or value.shape != (anchor_count, users, action_count):
            raise V023FitIndependentVerificationError(f"source {name} shape/dtype drifted")
        _check_array_numeric(value, field=f"source {name}")
    for name in ("anchor_content_digest", "anchor_view_content_digest", "anchor_topology_content_digest"):
        value = arrays[name]
        if value.dtype != np.dtype("S64") or value.shape != (9,):
            raise V023FitIndependentVerificationError(f"source {name} array is malformed")
        for index, item in enumerate(value):
            _digest(_decode_ascii(item, field=f"source {name}[{index}]"), field=f"source {name}[{index}]")
    if not np.array_equal(arrays["opening_feasibility"], arrays["action_mask"] & (context[:, :, :, 3] == 1.0)):
        raise V023FitIndependentVerificationError("source opening feasibility is not predecision")
    for name in ("action_context", "tokens"):
        _check_array_numeric(arrays[name], field=f"source {name}")
    pair_count = int(np.asarray(arrays["pair_anchor_index"]).size)
    pair_shape = {
        "pair_anchor_index": ((pair_count,), np.int64),
        "pair_id": ((pair_count,), np.dtype("S256")),
        "pair_user_ids": ((pair_count, 2), np.int64),
        "pair_action_ids": ((pair_count, 2), np.int64),
        "pair_target_by_draw": ((pair_count, V023_DRAW_COUNT, 2), np.float64),
        "pair_target_mean": ((pair_count, 2), np.float64),
        "pair_class": ((pair_count, 2), np.uint8),
        "pair_retained": ((pair_count,), np.bool_),
    }
    for name, (shape, dtype) in pair_shape.items():
        value = arrays[name]
        if isinstance(dtype, str):
            okay = value.dtype.kind == dtype
        else:
            okay = value.dtype == np.dtype(dtype)
        if not okay or value.shape != shape:
            raise V023FitIndependentVerificationError(f"source {name} shape/dtype drifted")
    for name in ("pair_target_by_draw", "pair_target_mean"):
        _check_array_numeric(arrays[name], field=f"source {name}")
    return users, action_count, pair_count


def _source_surface_digest_from_index(
    anchor_entry: Mapping[str, Any], *, world: int, phase: int
) -> str:
    if anchor_entry.get("phase") != phase:
        raise V023FitIndependentVerificationError("source anchor phase identity drifted")
    anchor_id = anchor_entry.get("anchor_id")
    if not isinstance(anchor_id, str) or not anchor_id:
        raise V023FitIndependentVerificationError("source anchor identity is missing")
    surface = _mapping(anchor_entry.get("surface"), field="source anchor surface")
    record = _mapping(surface.get("record"), field="source anchor record")
    if record.get("world_id") != world or record.get("phase") != phase or record.get("anchor_id") != anchor_id:
        raise V023FitIndependentVerificationError("source anchor record identity drifted")
    _digest(record.get("surface_digest"), field="source surface digest")
    return _digest(record.get("content_digest"), field="source anchor content digest")


def _load_source_world(index_path: Path, *, world: int, preflight: str) -> _SourceWorld:
    path = Path(index_path)
    payload = _load_json(path, field=f"source world {world}")
    _verify_receipt_seal(payload, field=f"source world {world}")
    _validate_source_identity(payload, world=world, preflight=preflight)
    binding = _mapping(payload.get("arrays"), field=f"source world {world} arrays")
    _sidecar_path, _sidecar_digest, arrays, _metadata = _load_source_npz(path, binding)
    users, action_count, pair_count = _source_array_shape_checks(arrays, field=f"source world {world}")
    anchors_payload = payload.get("anchors")
    if not isinstance(anchors_payload, list) or len(anchors_payload) != 9:
        raise V023FitIndependentVerificationError("source anchor table is not nine phases")
    anchor_ids: list[str] = []
    retained = arrays["anchor_retained"]
    reference = arrays["reference_actions"]
    action_mask = arrays["action_mask"]
    tokens = arrays["tokens"]
    token_mask = arrays["token_mask"]
    q1 = arrays["q1_values"]
    q2 = arrays["q2_values"]
    q12 = arrays["q12_values"]
    context = arrays["action_context"]
    opening = arrays["opening_feasibility"]
    # The source writer widens the already frozen float32 Q1/Q2 outputs to
    # float64 for the NPZ.  Recreate the float32 sum before widening; adding
    # the widened values would spuriously reject legitimate rounding.
    expected_q12 = np.asarray(
        np.asarray(q1, dtype=np.float32) + np.asarray(q2, dtype=np.float32),
        dtype=q12.dtype,
    )
    if not np.array_equal(q12, expected_q12):
        raise V023FitIndependentVerificationError("source Q12 is not exact float32 Q1+Q2")
    view_digests: list[str] = []
    for anchor_index, (phase, entry) in enumerate(zip(V023_PHASES, anchors_payload, strict=True)):
        if not isinstance(entry, Mapping):
            raise V023FitIndependentVerificationError("source anchor entry is malformed")
        if entry.get("phase") != phase or int(arrays["anchor_phase"][anchor_index]) != phase:
            raise V023FitIndependentVerificationError("source anchor phase identity drifted")
        anchor_id = entry.get("anchor_id")
        if not isinstance(anchor_id, str) or not anchor_id or anchor_id in anchor_ids:
            raise V023FitIndependentVerificationError("source anchor identity is missing/duplicated")
        anchor_ids.append(anchor_id)
        if type(entry.get("retained_for_fitting")) is not bool:
            raise V023FitIndependentVerificationError("source anchor retention flag is missing")
        if entry.get("retained_for_fitting") != bool(retained[anchor_index]):
            raise V023FitIndependentVerificationError("source anchor retention drifted")
        expected_view_digest = _digest(
            _decode_ascii(
                arrays["anchor_view_content_digest"][anchor_index],
                field="source anchor view digest",
            ),
            field="source anchor view digest",
        )
        view_digests.append(expected_view_digest)
        _verify_c3_view_arrays(
            context[anchor_index],
            tokens[anchor_index],
            token_mask[anchor_index],
            action_mask[anchor_index],
            reference[anchor_index],
            expected_digest=expected_view_digest,
        )
        predecision = _digest(
            entry.get("predecision_sha256"),
            field="source predecision digest",
        )
        if predecision != _decode_ascii(
            arrays["anchor_content_digest"][anchor_index],
            field="source anchor content digest",
        ):
            raise V023FitIndependentVerificationError("source predecision/content digest disagrees")
        topology_payload = _mapping(entry.get("topology"), field="source anchor topology")
        topology_digest = _digest(
            topology_payload.get("content_digest"),
            field="source topology content digest",
        )
        if topology_digest != _decode_ascii(
            arrays["anchor_topology_content_digest"][anchor_index],
            field="source anchor topology digest",
        ):
            raise V023FitIndependentVerificationError("source topology/content digest disagrees")
        for object_name, digest_name in (
            ("enumeration", "enumeration_sha256"),
            ("topology", "topology_sha256"),
            ("teachers", "teacher_sha256"),
            ("surface", "surface_sha256"),
        ):
            if digest_name in entry:
                value = _mapping(entry.get(object_name), field=f"source anchor {object_name}")
                declared = _digest(entry.get(digest_name), field=f"source anchor {digest_name}")
                if canonical_sha256(value) != declared:
                    raise V023FitIndependentVerificationError(
                        f"source anchor {object_name} canonical digest disagrees"
                    )
        if np.any(reference[anchor_index] < 0) or np.any(reference[anchor_index] >= action_count):
            raise V023FitIndependentVerificationError("source reference action is out of range")
        expected_reference = np.argmax(
            np.where(action_mask[anchor_index], q12[anchor_index], -np.inf), axis=1
        ).astype(np.int64)
        if not np.array_equal(reference[anchor_index], expected_reference):
            raise V023FitIndependentVerificationError("source reference action is not native argmax")
        q12_anchor = np.asarray(q12[anchor_index], dtype=np.float32)
        q12_record = np.asarray(q12_anchor, dtype=np.float64)
        margins = q12_record - q12_record[np.arange(users), reference[anchor_index]][:, None]
        encoded_margins = np.asarray(np.tanh(margins), dtype=np.float32)
        if not np.allclose(
            encoded_margins[action_mask[anchor_index]],
            context[anchor_index, :, :, 23][action_mask[anchor_index]],
            rtol=0.0,
            atol=2.0 * np.finfo(np.float32).eps,
        ):
            raise V023FitIndependentVerificationError("source Q12 margin features disagree")
        selected = np.flatnonzero(arrays["pair_anchor_index"] == anchor_index)
        topology = _mapping(entry.get("topology"), field="source anchor topology")
        topology_pairs = topology.get("pairs")
        if not isinstance(topology_pairs, list) or len(topology_pairs) != selected.size:
            raise V023FitIndependentVerificationError("source topology/pair table disagrees")
        if "pair_count" in entry and entry.get("pair_count") != int(selected.size):
            raise V023FitIndependentVerificationError("source anchor pair count disagrees")
        if "draw_count" in entry and entry.get("draw_count") != V023_DRAW_COUNT:
            raise V023FitIndependentVerificationError("source anchor draw count drifted")
        if "profile_count" in entry and entry.get("profile_count") != int(selected.size) * V023_DRAW_COUNT * 4:
            raise V023FitIndependentVerificationError("source anchor profile count disagrees")
        if "topology_status" in entry and not isinstance(entry.get("topology_status"), str):
            raise V023FitIndependentVerificationError("source topology status is malformed")
        if "retention_status" in entry and not isinstance(entry.get("retention_status"), str):
            raise V023FitIndependentVerificationError("source retention status is malformed")
        if not bool(retained[anchor_index]):
            continue
        _source_surface_digest_from_index(entry, world=world, phase=phase)
    world_receipt = _mapping(payload.get("world_receipt"), field="source world receipt")
    if world_receipt.get("anchor_ids") != anchor_ids:
        raise V023FitIndependentVerificationError("source world anchor identity list drifted")
    source_anchors: list[_SourceAnchor] = []
    pair_anchor = arrays["pair_anchor_index"]
    pair_ids = arrays["pair_id"]
    pair_users = arrays["pair_user_ids"]
    pair_actions = arrays["pair_action_ids"]
    pair_draws = arrays["pair_target_by_draw"]
    pair_means = arrays["pair_target_mean"]
    pair_classes = arrays["pair_class"]
    pair_retained = arrays["pair_retained"]
    # Validate the complete enumerated pair table, including non-retained
    # anchors.  A fit may use only retained anchors, but an independent
    # verifier must not silently accept a malformed excluded row.
    if np.any(pair_anchor < 0) or np.any(pair_anchor >= 9):
        raise V023FitIndependentVerificationError("source pair anchor index is out of range")
    all_pair_ids: set[str] = set()
    for pair_raw in range(pair_count):
        pair_id = _decode_ascii(pair_ids[pair_raw], field="source pair id")
        if pair_id in all_pair_ids:
            raise V023FitIndependentVerificationError("source pair id is duplicated")
        all_pair_ids.add(pair_id)
        anchor_index = int(pair_anchor[pair_raw])
        if bool(pair_retained[pair_raw]) != bool(retained[anchor_index]):
            raise V023FitIndependentVerificationError("source pair retention drifted")
        if pair_classes[pair_raw].tolist() != [3, 3]:
            raise V023FitIndependentVerificationError("source pair class is not SUPPORTED")
        if not np.array_equal(
            np.mean(pair_draws[pair_raw], axis=0, dtype=np.float64), pair_means[pair_raw]
        ):
            raise V023FitIndependentVerificationError("source pair means disagree with 32 draws")
        users_pair = [int(value) for value in pair_users[pair_raw].tolist()]
        actions_pair = [int(value) for value in pair_actions[pair_raw].tolist()]
        if len(set(users_pair)) != 2 or any(
            not 0 <= user < users or not 0 <= action < action_count
            for user, action in zip(users_pair, actions_pair, strict=True)
        ):
            raise V023FitIndependentVerificationError("source pair members are malformed")
    for anchor_index, entry in enumerate(anchors_payload):
        topology = _mapping(entry.get("topology"), field="source anchor topology")
        topology_pairs = topology.get("pairs")
        selected = np.flatnonzero(pair_anchor == anchor_index)
        if not isinstance(topology_pairs, list) or len(topology_pairs) != selected.size:
            raise V023FitIndependentVerificationError("source topology/pair table disagrees")
        for offset, pair_raw in enumerate(selected.tolist()):
            topo = topology_pairs[offset]
            pair_id = _decode_ascii(pair_ids[pair_raw], field="source pair id")
            if not isinstance(topo, Mapping) or topo.get("pair_id") != pair_id:
                raise V023FitIndependentVerificationError("source topology pair identity drifted")
            users_pair = [int(value) for value in pair_users[pair_raw].tolist()]
            actions_pair = [int(value) for value in pair_actions[pair_raw].tolist()]
            # Production topology receipts carry the complete destination
            # identity.  Keep the small synthetic fixture compatible while
            # checking every field whenever the richer v1 form is present.
            topology_fields = {
                "source_key",
                "member_users",
                "designated_actions",
                "destination_keys",
            }
            if topology_fields.intersection(topo):
                if (
                    topo.get("member_users") != users_pair
                    or topo.get("designated_actions") != actions_pair
                ):
                    raise V023FitIndependentVerificationError(
                        "source topology member/action identity disagrees"
                    )
                source_key = [
                    int(value)
                    for value in arrays["physical_keys"][anchor_index, users_pair[0], reference[anchor_index, users_pair[0]]].tolist()
                ]
                source_key_second = [
                    int(value)
                    for value in arrays["physical_keys"][anchor_index, users_pair[1], reference[anchor_index, users_pair[1]]].tolist()
                ]
                if source_key != source_key_second or topo.get("source_key") != source_key:
                    raise V023FitIndependentVerificationError(
                        "source topology source-key identity disagrees"
                    )
                expected_destinations = [
                    [
                        int(value)
                        for value in arrays["physical_keys"][anchor_index, user, action].tolist()
                    ]
                    for user, action in zip(users_pair, actions_pair, strict=True)
                ]
                if topo.get("destination_keys") != expected_destinations:
                    raise V023FitIndependentVerificationError(
                        "source topology destination identity disagrees"
                    )
                eligible_actions = topo.get("eligible_actions_by_member")
                if not isinstance(eligible_actions, list) or len(eligible_actions) != 2:
                    raise V023FitIndependentVerificationError(
                        "source topology eligible-action receipt is malformed"
                    )
                for member, user in enumerate(users_pair):
                    if not isinstance(eligible_actions[member], list):
                        raise V023FitIndependentVerificationError(
                            "source topology eligible-action receipt is malformed"
                        )
                    if actions_pair[member] not in eligible_actions[member]:
                        raise V023FitIndependentVerificationError(
                            "source topology designated action is not eligible"
                        )
                if topo.get("content_digest") is not None:
                    _digest(topo.get("content_digest"), field="source pair topology digest")
            teachers_payload = entry.get("teachers")
            if isinstance(teachers_payload, Mapping):
                teacher_pairs = teachers_payload.get("pairs")
                if not isinstance(teacher_pairs, list) or len(teacher_pairs) != selected.size:
                    raise V023FitIndependentVerificationError("source teacher pair table disagrees")
                teacher_item = teacher_pairs[offset]
                if not isinstance(teacher_item, Mapping) or teacher_item.get("pair_id") != pair_id:
                    raise V023FitIndependentVerificationError("source teacher pair identity drifted")
                if teacher_item.get("member_users") != users_pair or teacher_item.get("proposed_actions") != actions_pair:
                    raise V023FitIndependentVerificationError("source teacher member/action identity disagrees")
                teacher_draws = _json_float_array(
                    teacher_item.get("pair_targets_by_draw"),
                    shape=(V023_DRAW_COUNT, 2),
                    field="source teacher pair targets",
                )
                if not np.array_equal(teacher_draws, pair_draws[pair_raw]):
                    raise V023FitIndependentVerificationError("source teacher targets disagree with NPZ")
                teacher_mean = _json_float_array(
                    teacher_item.get("pair_target_mean"),
                    shape=(2,),
                    field="source teacher pair mean",
                )
                if not np.array_equal(teacher_mean, pair_means[pair_raw]):
                    raise V023FitIndependentVerificationError("source teacher mean disagrees with NPZ")
                _digest(teacher_item.get("content_digest"), field="source teacher content digest")
    for anchor_index, (phase, entry) in enumerate(zip(V023_PHASES, anchors_payload, strict=True)):
        if not bool(retained[anchor_index]):
            continue
        anchor_id = str(entry["anchor_id"])
        expected_view_digest = view_digests[anchor_index]
        q12_record = np.asarray(
            np.asarray(q12[anchor_index], dtype=np.float32), dtype=np.float64
        )
        surface = _mapping(entry.get("surface"), field="source anchor surface")
        record = _mapping(surface.get("record"), field="source anchor record")
        content_digest = _digest(record.get("content_digest"), field="source anchor content digest")
        surface_digest = _digest(record.get("surface_digest"), field="source surface digest")
        target_surface = np.zeros((users, action_count), dtype=np.float32)
        row_class = np.zeros((users, action_count), dtype=np.uint8)
        row_class[action_mask[anchor_index]] = np.uint8(2)  # CONTROL
        row_class[np.arange(users), reference[anchor_index]] = np.uint8(1)  # REFERENCE
        selected = np.flatnonzero(pair_anchor == anchor_index)
        seen_users: set[int] = set()
        supported: list[tuple[int, int, float, str]] = []
        pair_records: list[tuple[str, np.ndarray, np.ndarray, np.ndarray]] = []
        topology_pairs = _mapping(entry.get("topology"), field="source anchor topology").get("pairs")
        if not isinstance(topology_pairs, list):
            raise V023FitIndependentVerificationError(
                "source topology pair table is malformed"
            )
        for offset, pair_raw in enumerate(selected.tolist()):
            pair_id = _decode_ascii(pair_ids[pair_raw], field="source pair id")
            topo = topology_pairs[offset]
            if not isinstance(topo, Mapping) or topo.get("pair_id") != pair_id:
                raise V023FitIndependentVerificationError("source topology pair identity drifted")
            if pair_classes[pair_raw].tolist() != [3, 3]:
                raise V023FitIndependentVerificationError("source pair class is not SUPPORTED")
            if bool(pair_retained[pair_raw]) != bool(retained[anchor_index]):
                raise V023FitIndependentVerificationError("source pair retention drifted")
            draws = pair_draws[pair_raw]
            means = pair_means[pair_raw]
            if not np.array_equal(np.mean(draws, axis=0, dtype=np.float64), means):
                raise V023FitIndependentVerificationError("source pair means disagree with 32 draws")
            pair_records.append(
                (
                    pair_id,
                    np.asarray(pair_users[pair_raw], dtype=np.int64),
                    np.asarray(pair_actions[pair_raw], dtype=np.int64),
                    np.asarray(draws, dtype=np.float64),
                )
            )
            for member in range(2):
                user = int(pair_users[pair_raw, member])
                action = int(pair_actions[pair_raw, member])
                if not 0 <= user < users or not 0 <= action < action_count:
                    raise V023FitIndependentVerificationError("source pair cell is out of range")
                if user in seen_users or not bool(action_mask[anchor_index, user, action]):
                    raise V023FitIndependentVerificationError("source pairs are not user/cell disjoint legal rows")
                if action == int(reference[anchor_index, user]):
                    raise V023FitIndependentVerificationError("source supported cell is reference")
                if row_class[user, action] != np.uint8(2):
                    raise V023FitIndependentVerificationError("source supported cell overwrites a source class")
                if not bool(opening[anchor_index, user, action]) or context[anchor_index, user, action, 3] != 1.0:
                    raise V023FitIndependentVerificationError("source supported cell is not opening-feasible")
                pair_token = context[anchor_index, user, action]
                # Pair-support flags live in the pair token, not in the scalar
                # action context.  Validate its native mask and exact type.
                token_slot = users
                token = arrays["tokens"][anchor_index, user, action, token_slot]
                if not np.array_equal(token[2:5], np.ones(3, dtype=np.float32)):
                    raise V023FitIndependentVerificationError("source supported cell lacks pair token")
                if user in seen_users or target_surface[user, action] != 0.0:
                    raise V023FitIndependentVerificationError("source supported cell is duplicated")
                target_surface[user, action] = np.float32(means[member])
                row_class[user, action] = np.uint8(3)  # SUPPORTED
                supported.append((user, action, float(means[member]), pair_id))
                seen_users.add(user)
        if not np.any(row_class == np.uint8(3)):
            raise V023FitIndependentVerificationError("retained source anchor has no SUPPORTED class")
        if not np.any(row_class == np.uint8(1)) or not np.any(row_class == np.uint8(2)):
            raise V023FitIndependentVerificationError("retained source anchor lacks S/R/C class")
        if surface.get("retained_for_fitting") is not None and surface.get("retained_for_fitting") is not True:
            raise V023FitIndependentVerificationError("source surface retention status drifted")
        expected_class_counts = {
            "S": int(np.count_nonzero(row_class == np.uint8(3))),
            "R": int(np.count_nonzero(row_class == np.uint8(1))),
            "C": int(np.count_nonzero(row_class == np.uint8(2))),
            "MASKED": int(np.count_nonzero(row_class == np.uint8(0))),
        }
        if entry.get("class_counts") is not None and entry.get("class_counts") != expected_class_counts:
            raise V023FitIndependentVerificationError("source anchor class counts disagree")
        if record.get("class_counts") is not None and record.get("class_counts") != expected_class_counts:
            raise V023FitIndependentVerificationError("source surface class counts disagree")
        expected_surface_digest = _surface_digest(
            expected_view_digest,
            target_surface,
            row_class,
            pair_records,
        )
        if expected_surface_digest != surface_digest:
            raise V023FitIndependentVerificationError("reconstructed source surface digest disagrees")
        expected_record_digest = _anchor_record_digest(
            world=world,
            phase=phase,
            anchor_id=anchor_id,
            surface_digest=surface_digest,
            q12=q12_record,
        )
        if expected_record_digest != content_digest:
            raise V023FitIndependentVerificationError("reconstructed source anchor record digest disagrees")
        rows = tuple(
            _SourceRow(
                world=world,
                anchor_index=anchor_index,
                anchor_id=anchor_id,
                phase=phase,
                user=user,
                action=action,
                target=float(target_surface[user, action]),
                anchor_digest=content_digest,
                reference_action=int(reference[anchor_index, user]),
                q12=np.asarray(q12[anchor_index], dtype=np.float64),
                context=np.asarray(context[anchor_index], dtype=np.float32),
                action_mask=True,
                opening=True,
            )
            for user, action, _target, _pair in sorted(supported)
        )
        source_anchors.append(
            _SourceAnchor(
                world=world,
                anchor_index=anchor_index,
                anchor_id=anchor_id,
                phase=phase,
                content_digest=content_digest,
                surface_digest=surface_digest,
                target_surface=target_surface,
                supported_rows=rows,
                q12=np.asarray(q12[anchor_index], dtype=np.float64),
                context=np.asarray(context[anchor_index], dtype=np.float32),
                action_mask=np.asarray(action_mask[anchor_index], dtype=np.bool_),
                opening=np.asarray(opening[anchor_index], dtype=np.bool_),
                reference=np.asarray(reference[anchor_index], dtype=np.int64),
            )
        )
    # Production v1 repeats the per-anchor receipts in world-level aggregate
    # objects.  If those richer objects are present, bind them to the exact
    # ordered anchor entries; a stale aggregate must not be accepted merely
    # because its own canonical hash was resealed.
    for object_name, entry_name in (
        ("enumeration", "enumeration"),
        ("topology", "topology"),
        ("teacher", "teachers"),
        ("surface", "surface"),
    ):
        aggregate = payload.get(object_name)
        if isinstance(aggregate, Mapping) and "anchors" in aggregate:
            anchors = aggregate.get("anchors")
            expected_aggregate = [entry.get(entry_name) for entry in anchors_payload]
            if anchors != expected_aggregate:
                raise V023FitIndependentVerificationError(
                    f"source {object_name} aggregate disagrees with anchors"
                )
    expected_record_count = len(source_anchors)
    expected_supported_count = sum(len(anchor.supported_rows) for anchor in source_anchors)
    if type(payload.get("record_count")) is not int or payload.get("record_count") != expected_record_count:
        raise V023FitIndependentVerificationError("source record count disagrees")
    if type(payload.get("pair_count")) is not int or payload.get("pair_count") != pair_count:
        raise V023FitIndependentVerificationError("source pair count disagrees")
    if type(payload.get("supported_count")) is not int or payload.get("supported_count") != expected_supported_count:
        raise V023FitIndependentVerificationError("source supported count disagrees")
    expected_fitting_pair_count = int(np.count_nonzero(pair_retained))
    for field, expected in (
        ("enumerated_pair_count", pair_count),
        ("fitting_pair_count", expected_fitting_pair_count),
        ("fitting_supported_count", expected_supported_count),
    ):
        if payload.get(field) is not None and (
            type(payload.get(field)) is not int or payload.get(field) != expected
        ):
            raise V023FitIndependentVerificationError(f"source {field} disagrees")
    # The source writer also emits a world-local placebo-strata receipt.  The
    # fit verifier can reconstruct the same fold mapping from the S rows, but
    # when this optional aggregate is present it must not be a stale,
    # self-consistent JSON copy detached from those rows.
    placebo_strata = payload.get("placebo_strata")
    if placebo_strata is not None:
        _verify_source_placebo_strata(
            placebo_strata,
            source_anchors=tuple(source_anchors),
            expected_total=expected_supported_count,
        )
    placebo_groups: dict[tuple[int, int, int, int, int, int], int] = {}
    for anchor in source_anchors:
        for row in anchor.supported_rows:
            key = _placebo_stratum(row)
            placebo_groups[key] = placebo_groups.get(key, 0) + 1
    expected_placebo_eligible = sum(
        count for count in placebo_groups.values() if count >= 2
    )
    declared_placebo = payload.get("placebo_eligible_count")
    if type(declared_placebo) is not int or declared_placebo != expected_placebo_eligible:
        raise V023FitIndependentVerificationError(
            "source placebo-eligible count disagrees with authenticated S rows"
        )
    if not source_anchors:
        raise V023FitIndependentVerificationError(f"source world {world} has no retained anchor")
    return _SourceWorld(
        world=world,
        path=Path(index_path).resolve(),
        index_digest=file_sha256(index_path),
        payload=payload,
        anchors=tuple(source_anchors),
        pair_count=pair_count,
        supported_count=expected_supported_count,
    )


def _verify_source_manifest(
    manifest_path: Path,
    *,
    preflight: str,
    expected_digest: str | None,
    source_index_paths: Sequence[Path] | None,
) -> tuple[dict[str, Any], tuple[_SourceWorld, ...]]:
    payload = _load_json(manifest_path, field="source manifest")
    if payload.get("schema") != V023_SOURCE_MANIFEST_SCHEMA or payload.get("status") != "PASS":
        raise V023FitIndependentVerificationError("source manifest schema/status drifted")
    if payload.get("claim_ceiling") != V023_CLAIM_CEILING:
        raise V023FitIndependentVerificationError("source manifest claim ceiling drifted")
    if payload.get("contract_sha256") != V023_CONTRACT_SHA256:
        raise V023FitIndependentVerificationError("source manifest contract hash drifted")
    if payload.get("preflight_manifest_sha256") != preflight:
        raise V023FitIndependentVerificationError("source manifest preflight hash drifted")
    if payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023FitIndependentVerificationError("source manifest split drifted")
    if payload.get("worlds") != list(V023_GATE_WORLDS) or payload.get("source_count") != 8:
        raise V023FitIndependentVerificationError("source manifest world panel drifted")
    if (
        payload.get("test_split_opened") is not False
        or payload.get("episode_training") is not False
        or payload.get("learner_update") is not False
    ):
        raise V023FitIndependentVerificationError("source manifest crossed a closed boundary")
    expected_shards = [
        {"world": world, "relative_name": f"source/world-{world}.json"}
        for world in V023_GATE_WORLDS
    ]
    if payload.get("shards") != expected_shards:
        raise V023FitIndependentVerificationError("source manifest shard schedule drifted")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != 8:
        raise V023FitIndependentVerificationError("source manifest entries are incomplete")
    root = Path(manifest_path).parent.resolve()
    child_paths: list[Path] = []
    for actual, expected in zip(entries, expected_shards, strict=True):
        if not isinstance(actual, Mapping) or actual.get("world") != expected["world"] or actual.get("relative_name") != expected["relative_name"]:
            raise V023FitIndependentVerificationError("source manifest entry identity drifted")
        declared = _digest(actual.get("sha256"), field="source manifest child sha256")
        child = _safe_child(root, expected["relative_name"], field="source manifest child")
        if file_sha256(child) != declared:
            raise V023FitIndependentVerificationError("source manifest child byte hash disagrees")
        child_paths.append(child)
    source_digest = _digest(payload.get("source_manifest_sha256"), field="source_manifest_sha256")
    unsigned = dict(payload)
    unsigned.pop("source_manifest_sha256", None)
    unsigned.pop("manifest_sha256", None)
    if canonical_sha256(unsigned) != source_digest:
        raise V023FitIndependentVerificationError("source manifest body hash disagrees")
    manifest_digest = _digest(payload.get("manifest_sha256"), field="manifest_sha256")
    unsigned_manifest = dict(payload)
    unsigned_manifest.pop("manifest_sha256", None)
    if canonical_sha256(unsigned_manifest) != manifest_digest:
        raise V023FitIndependentVerificationError("source manifest seal disagrees")
    if expected_digest is not None and source_digest != _digest(expected_digest, field="expected source manifest hash"):
        raise V023FitIndependentVerificationError("source manifest hash disagrees with expected hash")
    if source_index_paths is not None:
        supplied = tuple(Path(path).resolve() for path in source_index_paths)
        if len(supplied) != 8 or supplied != tuple(child_paths):
            raise V023FitIndependentVerificationError("source paths are not the exact manifest panel")
    worlds = tuple(
        _load_source_world(path, world=world, preflight=preflight)
        for world, path in zip(V023_GATE_WORLDS, child_paths, strict=True)
    )
    return payload, worlds


def _phase_bin(phase: int) -> int:
    return (phase - 1) // 3


def _comparison_tolerance(left: float, right: float) -> float:
    return max(
        1.0e-12,
        1024.0 * np.finfo(np.float64).eps * max(1.0, abs(left), abs(right)),
    )


def _placebo_stratum(row: _SourceRow) -> tuple[int, int, int, int, int, int]:
    if not row.action_mask or not row.opening or row.context[row.user, row.action, 3] != 1.0:
        raise V023FitIndependentVerificationError("SUPPORTED row is not legal-and-opening")
    users = row.q12.shape[0]
    occupancy_raw = float(row.context[row.user, row.action, 27]) * users
    occupancy = int(round(occupancy_raw))
    if occupancy < 1 or not math.isclose(occupancy_raw, occupancy, rel_tol=0.0, abs_tol=2.0e-6 * users):
        raise V023FitIndependentVerificationError("SUPPORTED destination occupancy is malformed")
    active = float(row.context[row.user, row.action, 12])
    if active not in (0.0, 1.0):
        raise V023FitIndependentVerificationError("SUPPORTED destination activity is malformed")
    gap = float(row.q12[row.user, row.reference_action] - row.q12[row.user, row.action])
    tolerance = _comparison_tolerance(float(row.q12[row.user, row.reference_action]), float(row.q12[row.user, row.action]))
    if abs(gap) <= tolerance:
        gap = 0.0
    if gap < 0.0:
        raise V023FitIndependentVerificationError("SUPPORTED base gap is negative")
    gap_bin = 0 if gap < 0.01 else 1 if gap < 0.05 else 2 if gap < 0.20 else 3
    return (
        row.world,
        _phase_bin(row.phase),
        1,
        1 if occupancy == 1 else 2,
        int(active),
        gap_bin,
    )


def _placebo_shift(stratum: tuple[int, int, int, int, int, int], size: int) -> int:
    if size < 2:
        raise V023FitIndependentVerificationError("placebo stratum has fewer than two cells")
    encoded = _canonical_bytes({"key": V023_PLACEBO_KEY, "stratum": list(stratum)})
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big") % (size - 1) + 1


def _mapping_payload(stratum: tuple[int, int, int, int, int, int], source: tuple[int, int, int], destination: tuple[int, int, int], shift: int) -> dict[str, Any]:
    return {
        "stratum": {
            "world_id": int(stratum[0]),
            "phase_bin": int(stratum[1]),
            "legal_opening": int(stratum[2]),
            "destination_occupancy_bin": int(stratum[3]),
            "committed_destination_active": int(stratum[4]),
            "base_gap_bin": int(stratum[5]),
        },
        "source_anchor": int(source[0]),
        "source_user": int(source[1]),
        "source_action": int(source[2]),
        "destination_anchor": int(destination[0]),
        "destination_user": int(destination[1]),
        "destination_action": int(destination[2]),
        "shift": int(shift),
    }


@dataclass(frozen=True)
class _Fold:
    held_out_world: int
    training_anchors: tuple[_SourceAnchor, ...]
    heldout_anchors: tuple[_SourceAnchor, ...]
    training_rows: tuple[_SourceRow, ...]
    heldout_rows: tuple[_SourceRow, ...]
    placebo_targets: tuple[np.ndarray, ...]
    informed_targets: tuple[np.ndarray, ...]
    mappings: tuple[dict[str, Any], ...]
    placebo_digest: str
    placebo_eligible: int
    placebo_total: int


def _placebo_digest(
    anchors: Sequence[_SourceAnchor],
    targets: Sequence[np.ndarray],
    mappings: Sequence[Mapping[str, Any]],
) -> str:
    digest = hashlib.sha256()
    digest.update(V023_PLACEBO_SCHEMA.encode("ascii"))
    digest.update(V023_PLACEBO_KEY_SHA256.encode("ascii"))
    for anchor, target in zip(anchors, targets, strict=True):
        # The production placebo digest is the runtime record digest plus the
        # target bytes.  This is intentionally distinct from the fit receipt's
        # target-source digest, which uses the surface digest.
        digest.update(anchor.content_digest.encode("ascii"))
        digest.update(np.ascontiguousarray(target, dtype=np.float32).tobytes(order="C"))
    for mapping in mappings:
        s = _mapping(mapping.get("stratum"), field="placebo mapping stratum")
        key = (
            _int(s.get("world_id"), field="placebo world"),
            _int(s.get("phase_bin"), field="placebo phase"),
            _int(s.get("legal_opening"), field="placebo legal"),
            _int(s.get("destination_occupancy_bin"), field="placebo occupancy"),
            _int(s.get("committed_destination_active"), field="placebo active"),
            _int(s.get("base_gap_bin"), field="placebo gap"),
        )
        shift = _int(mapping.get("shift"), field="placebo shift")
        digest.update(struct.pack(">6qI", *key, shift))
        digest.update(
            struct.pack(
                ">6q",
                _int(mapping.get("source_anchor"), field="placebo source anchor"),
                _int(mapping.get("source_user"), field="placebo source user"),
                _int(mapping.get("source_action"), field="placebo source action"),
                _int(mapping.get("destination_anchor"), field="placebo destination anchor"),
                _int(mapping.get("destination_user"), field="placebo destination user"),
                _int(mapping.get("destination_action"), field="placebo destination action"),
            )
        )
    return digest.hexdigest()


def _build_world_placebo(
    anchors: Sequence[_SourceAnchor],
) -> tuple[
    tuple[np.ndarray, ...],
    tuple[dict[str, Any], ...],
    int,
    int,
    str,
    list[dict[str, Any]],
]:
    """Rebuild the source writer's optional world-local placebo receipt.

    The fit fold uses the same construction over seven worlds.  Keeping this
    small variant here lets us bind a production ``placebo_strata`` aggregate
    to the authenticated source rows when the aggregate is present, without
    importing the runtime placebo module.
    """

    frozen = tuple(anchors)
    if not frozen:
        raise V023FitIndependentVerificationError("placebo needs a retained source anchor")
    targets = [
        np.ascontiguousarray(anchor.target_surface, dtype=np.float32).copy()
        for anchor in frozen
    ]
    groups: dict[tuple[int, int, int, int, int, int], list[tuple[int, int, int]]] = {}
    for anchor_index, anchor in enumerate(frozen):
        for row in anchor.supported_rows:
            groups.setdefault(_placebo_stratum(row), []).append(
                (anchor_index, row.user, row.action)
            )
    total = sum(len(cells) for cells in groups.values())
    if total <= 0:
        raise V023FitIndependentVerificationError("placebo needs a SUPPORTED source row")
    mappings: list[dict[str, Any]] = []
    eligible = 0
    strata: list[dict[str, Any]] = []
    for stratum in sorted(groups):
        cells = sorted(
            groups[stratum],
            key=lambda cell: (
                frozen[cell[0]].world,
                frozen[cell[0]].anchor_id,
                cell[1],
                cell[2],
            ),
        )
        strata.append(
            {
                "stratum": list(stratum),
                "rows": [
                    {
                        "anchor_index": int(anchor_index),
                        "world": int(frozen[anchor_index].world),
                        "anchor_id": frozen[anchor_index].anchor_id,
                        "user": int(user),
                        "action": int(action),
                    }
                    for anchor_index, user, action in cells
                ],
                "count": len(cells),
                "placebo_eligible": len(cells) >= 2,
            }
        )
        if len(cells) < 2:
            continue
        eligible += len(cells)
        shift = _placebo_shift(stratum, len(cells))
        original = [
            float(targets[anchor_index][user, action])
            for anchor_index, user, action in cells
        ]
        for destination_index, destination in enumerate(cells):
            source_index = (destination_index - shift) % len(cells)
            source = cells[source_index]
            destination_anchor, destination_user, destination_action = destination
            targets[destination_anchor][destination_user, destination_action] = np.float32(
                original[source_index]
            )
            mappings.append(_mapping_payload(stratum, source, destination, shift))
    target_tuple = tuple(
        np.ascontiguousarray(target, dtype=np.float32) for target in targets
    )
    mapping_tuple = tuple(mappings)
    return (
        target_tuple,
        mapping_tuple,
        eligible,
        total,
        _placebo_digest(frozen, target_tuple, mapping_tuple),
        strata,
    )


def _verify_source_placebo_strata(
    payload: object,
    *,
    source_anchors: Sequence[_SourceAnchor],
    expected_total: int,
) -> None:
    """Check the source shard's optional world-local placebo aggregate."""

    receipt = _mapping(payload, field="source placebo strata")
    if receipt.get("schema") != f"{V023_SOURCE_ARTIFACT_SCHEMA}-placebo-strata-v1":
        raise V023FitIndependentVerificationError("source placebo strata schema drifted")
    if receipt.get("placebo_key") != V023_PLACEBO_KEY or receipt.get("placebo_key_sha256") != V023_PLACEBO_KEY_SHA256:
        raise V023FitIndependentVerificationError("source placebo strata key drifted")
    if receipt.get("within_world_only") is not True or receipt.get("outcome_filter_applied") is not False:
        raise V023FitIndependentVerificationError("source placebo strata crossed a closed boundary")
    _targets, mappings, eligible, total, content_digest, strata = _build_world_placebo(
        source_anchors
    )
    if total != expected_total:
        raise V023FitIndependentVerificationError("source placebo strata total disagrees")
    source_mappings = []
    for mapping in mappings:
        stratum = _mapping(mapping.get("stratum"), field="source placebo mapping stratum")
        source_mappings.append(
            {
                **dict(mapping),
                "stratum": [
                    _int(stratum.get("world_id"), field="source placebo world"),
                    _int(stratum.get("phase_bin"), field="source placebo phase"),
                    _int(stratum.get("legal_opening"), field="source placebo legal"),
                    _int(stratum.get("destination_occupancy_bin"), field="source placebo occupancy"),
                    _int(stratum.get("committed_destination_active"), field="source placebo active"),
                    _int(stratum.get("base_gap_bin"), field="source placebo gap"),
                ],
            }
        )
    if receipt.get("strata") != strata or receipt.get("mappings") != source_mappings:
        raise V023FitIndependentVerificationError("source placebo strata mapping disagrees")
    if receipt.get("supported_count") != total or receipt.get("placebo_eligible_count") != eligible:
        raise V023FitIndependentVerificationError("source placebo strata counts disagree")
    coverage = _float(receipt.get("coverage"), field="source placebo strata coverage")
    if abs(coverage - eligible / total) > 1.0e-12:
        raise V023FitIndependentVerificationError("source placebo strata coverage disagrees")
    if receipt.get("content_digest") != content_digest:
        raise V023FitIndependentVerificationError("source placebo strata content digest disagrees")


def _target_source_digest(anchors: Sequence[_SourceAnchor], targets: Sequence[np.ndarray]) -> str:
    if len(anchors) != len(targets):
        raise V023FitIndependentVerificationError("target/source anchor count disagrees")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-fitting-source-v1")
    for anchor, target in zip(anchors, targets, strict=True):
        # The adapter binds learner targets to the authenticated surface
        # digest.  ``content_digest`` is the enclosing anchor-record digest
        # used by the fit receipt's identity list and is a different field.
        digest.update(anchor.surface_digest.encode("ascii"))
        value = np.ascontiguousarray(target, dtype=np.float32)
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _make_fold(worlds: Sequence[_SourceWorld], *, held_out_world: int) -> _Fold:
    if tuple(world.world for world in worlds) != V023_GATE_WORLDS:
        raise V023FitIndependentVerificationError("source panel is not exact eight-world order")
    heldout_world = next((world for world in worlds if world.world == held_out_world), None)
    if heldout_world is None:
        raise V023FitIndependentVerificationError("held-out source world is missing")
    training_anchors = tuple(anchor for world in worlds if world.world != held_out_world for anchor in world.anchors)
    heldout_anchors = tuple(heldout_world.anchors)
    training_rows = tuple(row for anchor in training_anchors for row in anchor.supported_rows)
    heldout_rows = tuple(row for anchor in heldout_anchors for row in anchor.supported_rows)
    if not heldout_rows:
        raise V023FitIndependentVerificationError("held-out world has no SUPPORTED rows")
    informed_targets = tuple(np.array(anchor.target_surface, copy=True, dtype=np.float32, order="C") for anchor in training_anchors)
    placebo_targets = [np.array(target, copy=True, dtype=np.float32, order="C") for target in informed_targets]
    groups: dict[tuple[int, int, int, int, int, int], list[tuple[int, int, int]]] = {}
    for anchor_index, anchor in enumerate(training_anchors):
        for row in anchor.supported_rows:
            groups.setdefault(_placebo_stratum(row), []).append((anchor_index, row.user, row.action))
    mappings: list[dict[str, Any]] = []
    eligible = 0
    for stratum in sorted(groups):
        cells = sorted(groups[stratum], key=lambda cell: (training_anchors[cell[0]].world, training_anchors[cell[0]].anchor_id, cell[1], cell[2]))
        if len(cells) < 2:
            continue
        eligible += len(cells)
        shift = _placebo_shift(stratum, len(cells))
        original = [float(informed_targets[a][u, action]) for a, u, action in cells]
        for destination_index, destination in enumerate(cells):
            source_index = (destination_index - shift) % len(cells)
            source = cells[source_index]
            da, du, dx = destination
            placebo_targets[da][du, dx] = np.float32(original[source_index])
            mappings.append(_mapping_payload(stratum, source, destination, shift))
    placebo_tuple = tuple(np.ascontiguousarray(target, dtype=np.float32) for target in placebo_targets)
    return _Fold(
        held_out_world=held_out_world,
        training_anchors=training_anchors,
        heldout_anchors=heldout_anchors,
        training_rows=training_rows,
        heldout_rows=heldout_rows,
        placebo_targets=placebo_tuple,
        informed_targets=tuple(informed_targets),
        mappings=tuple(mappings),
        placebo_digest=_placebo_digest(training_anchors, placebo_tuple, mappings),
        placebo_eligible=eligible,
        placebo_total=len(training_rows),
    )


def _prediction_digest(identities: Sequence[tuple[int, str, int, int]], prediction: np.ndarray, target: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-mcrl-v023-lcsrs-heldout-predictions-v1")
    for world, anchor, user, action in identities:
        digest.update(struct.pack(">QII", int(world), int(user), int(action)))
        encoded = str(anchor).encode("utf-8")
        digest.update(struct.pack(">I", len(encoded)))
        digest.update(encoded)
    for name, array in (("prediction", prediction), ("target", target)):
        value = np.ascontiguousarray(array, dtype=np.float64)
        encoded = name.encode("utf-8")
        digest.update(struct.pack(">I", len(encoded)))
        digest.update(encoded)
        digest.update(value.dtype.str.encode("ascii"))
        digest.update(struct.pack(">I", value.size))
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _midranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1) + 1.0
        start = end
    return ranks


def tie_aware_spearman(prediction: np.ndarray, target: np.ndarray) -> float | None:
    left = np.asarray(prediction, dtype=np.float64)
    right = np.asarray(target, dtype=np.float64)
    if left.ndim != 1 or right.shape != left.shape or left.size < 2:
        return None
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise V023FitIndependentVerificationError("Spearman inputs are non-finite")
    a = _midranks(left)
    b = _midranks(right)
    a -= float(np.mean(a))
    b -= float(np.mean(b))
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    if denominator == 0.0 or not math.isfinite(denominator):
        return None
    result = float(np.dot(a, b) / denominator)
    return result if math.isfinite(result) else None


def sign_receipt(prediction: np.ndarray, target: np.ndarray) -> dict[str, Any]:
    left = np.asarray(prediction, dtype=np.float64)
    right = np.asarray(target, dtype=np.float64)
    if left.ndim != 1 or right.shape != left.shape:
        raise V023FitIndependentVerificationError("sign inputs are not aligned")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise V023FitIndependentVerificationError("sign inputs are non-finite")
    eligible = np.abs(right) >= V023_SIGN_THRESHOLD
    evaluated = int(np.count_nonzero(eligible))
    positive = eligible & (right > 0.0)
    negative = eligible & (right < 0.0)
    positive_denominator = int(np.count_nonzero(positive))
    negative_denominator = int(np.count_nonzero(negative))
    correct_positive = int(np.count_nonzero(positive & (left > 0.0)))
    correct_negative = int(np.count_nonzero(negative & (left < 0.0)))
    correct = correct_positive + correct_negative
    positive_recall = None if positive_denominator == 0 else correct_positive / positive_denominator
    negative_recall = None if negative_denominator == 0 else correct_negative / negative_denominator
    return {
        "threshold": V023_SIGN_THRESHOLD,
        "total_rows": int(right.size),
        "evaluated_rows": evaluated,
        "excluded_rows": int(right.size - evaluated),
        "correct_rows": correct,
        "accuracy": None if evaluated == 0 else correct / evaluated,
        "raw_correct_rows": correct,
        "raw_sign_accuracy": None if evaluated == 0 else correct / evaluated,
        "positive_denominator": positive_denominator,
        "negative_denominator": negative_denominator,
        "correct_positive": correct_positive,
        "correct_negative": correct_negative,
        "positive_recall": positive_recall,
        "negative_recall": negative_recall,
        "balanced_accuracy": None
        if positive_recall is None or negative_recall is None
        else (positive_recall + negative_recall) / 2.0,
        "decision_role": "RAW_SERIALIZED_BALANCED_AGGREGATED_AT_FINAL_R7",
    }


def _verify_model(
    receipt_root: Path,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    model_state = _mapping(receipt.get("model_state"), field="model_state")
    if model_state.get("schema") != V023_FIT_MODEL_SCHEMA:
        raise V023FitIndependentVerificationError("model schema drifted")
    if model_state.get("array_domain") != V023_FIT_MODEL_ARRAY_DOMAIN or model_state.get("no_pickle") is not True:
        raise V023FitIndependentVerificationError("model array boundary drifted")
    model_path = _safe_child(receipt_root, model_state.get("path"), field="model sidecar")
    digest_name = model_state.get("npz_sha256_file")
    if digest_name != f"{model_path.name}.sha256":
        raise V023FitIndependentVerificationError("model digest sidecar name drifted")
    digest_path = _safe_child(receipt_root, digest_name, field="model digest sidecar")
    model_digest = _digest(model_state.get("npz_sha256"), field="model NPZ sha256")
    if file_sha256(model_path) != model_digest or model_digest != _digest(receipt.get("model_sha256"), field="model_sha256"):
        raise V023FitIndependentVerificationError("model NPZ byte hash disagrees")
    _verify_digest_file(digest_path, digest=model_digest, target_name=model_path.name, field="model")
    metadata = _mapping(model_state.get("arrays"), field="model tensor metadata")
    if not metadata:
        raise V023FitIndependentVerificationError("model tensor metadata is empty")
    try:
        with np.load(model_path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True, order="C") for name in archive.files}
    except Exception as error:
        raise V023FitIndependentVerificationError("model NPZ cannot be loaded safely") from error
    expected_keys: set[str] = set()
    npz_key_seen: set[str] = set()
    for name, entry_raw in metadata.items():
        if not isinstance(name, str) or not name:
            raise V023FitIndependentVerificationError("model tensor name is missing")
        entry = _mapping(entry_raw, field=f"model tensor metadata[{name}]")
        key = entry.get("npz_key")
        if not isinstance(key, str) or not key or key in npz_key_seen:
            raise V023FitIndependentVerificationError("model tensor NPZ key is duplicated/missing")
        npz_key_seen.add(key)
        expected_keys.add(key)
    if set(arrays) != expected_keys:
        raise V023FitIndependentVerificationError("model tensor keys disagree with metadata")
    for name, entry_raw in metadata.items():
        entry = _mapping(entry_raw, field=f"model tensor metadata[{name}]")
        array = arrays[str(entry["npz_key"])]
        if array.dtype == object:
            raise V023FitIndependentVerificationError("model NPZ contains object dtype")
        if not np.issubdtype(array.dtype, np.number):
            raise V023FitIndependentVerificationError("model NPZ contains a nonnumeric tensor")
        if not np.all(np.isfinite(array)):
            raise V023FitIndependentVerificationError("model NPZ contains non-finite tensor")
        if entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023FitIndependentVerificationError("model tensor shape/dtype disagrees")
        if entry.get("sha256") != _array_digest(array, domain=V023_FIT_MODEL_ARRAY_DOMAIN):
            raise V023FitIndependentVerificationError("model tensor digest disagrees")
    logical = _digest(model_state.get("logical_network_sha256"), field="logical_network_sha256")
    if logical != _digest(receipt.get("network_sha256"), field="network_sha256"):
        raise V023FitIndependentVerificationError("logical network hash disagrees with receipt")
    return {
        "model_npz_sha256": model_digest,
        "network_sha256": logical,
        "tensor_count": len(arrays),
        "logical_network_hash_verified": False,
    }


def _compare_identity_json(
    metrics: Mapping[str, Any],
    identities: Sequence[tuple[int, str, int, int]],
) -> None:
    declared = metrics.get("identities")
    if not isinstance(declared, list) or len(declared) != len(identities):
        raise V023FitIndependentVerificationError("metrics identity list is missing/incomplete")
    for index, (expected, raw) in enumerate(zip(identities, declared, strict=True)):
        item = _mapping(raw, field=f"metrics identity[{index}]")
        actual = (
            _int(item.get("world"), field=f"metrics identity[{index}].world"),
            item.get("anchor_id"),
            _int(item.get("user"), field=f"metrics identity[{index}].user"),
            _int(item.get("action"), field=f"metrics identity[{index}].action"),
        )
        if not isinstance(actual[1], str) or not actual[1] or actual != expected:
            raise V023FitIndependentVerificationError("metrics identity disagrees with source rows")


def _verify_metrics(
    receipt_root: Path,
    receipt: Mapping[str, Any],
    fold: _Fold,
    *,
    source_manifest_sha256: str,
    arm: str,
    student_seed: int,
) -> dict[str, Any]:
    binding = _mapping(receipt.get("metrics"), field="metrics binding")
    if binding.get("schema") != V023_FIT_METRICS_SCHEMA:
        raise V023FitIndependentVerificationError("metrics schema drifted")
    metrics_path = _safe_child(receipt_root, binding.get("path"), field="metrics JSON")
    metrics_digest = _digest(binding.get("sha256"), field="metrics JSON sha256")
    if file_sha256(metrics_path) != metrics_digest or metrics_digest != _digest(receipt.get("metrics_sha256"), field="metrics_sha256"):
        raise V023FitIndependentVerificationError("metrics JSON byte hash disagrees")
    metrics = _load_json(metrics_path, field="fit metrics JSON")
    if metrics.get("schema") != V023_FIT_METRICS_SCHEMA or metrics.get("claim_ceiling") != V023_CLAIM_CEILING:
        raise V023FitIndependentVerificationError("metrics schema/claim ceiling drifted")
    metrics_fit_sidecar = _mapping(
        metrics.get("fit_receipt_sidecar"),
        field="metrics fit-receipt sidecar binding",
    )
    nested_fit = _mapping(receipt.get("fit_receipt"), field="fit_receipt binding")
    if (
        metrics_fit_sidecar.get("relative_name") != nested_fit.get("path")
        or metrics_fit_sidecar.get("sha256") != nested_fit.get("sha256")
    ):
        raise V023FitIndependentVerificationError(
            "metrics fit-receipt sidecar binding disagrees"
        )
    if metrics.get("split") != "TRAIN_DEVELOPMENT" or metrics.get("held_out_world") != fold.held_out_world or metrics.get("student_seed") != student_seed or metrics.get("arm") != arm:
        raise V023FitIndependentVerificationError("metrics identity drifted")
    if metrics.get("source_manifest_sha256") != source_manifest_sha256:
        raise V023FitIndependentVerificationError("metrics source manifest drifted")
    expected_training_worlds = [
        world for world in V023_GATE_WORLDS if world != fold.held_out_world
    ]
    if (
        metrics.get("training_worlds") != expected_training_worlds
        or metrics.get("training_anchor_count") != len(fold.training_anchors)
        or metrics.get("heldout_anchor_count") != len(fold.heldout_anchors)
    ):
        raise V023FitIndependentVerificationError("metrics LOO denominator identity drifted")
    if metrics.get("test_split_opened") is not False or metrics.get("episode_training") is not False or metrics.get("learner_update") is not True:
        raise V023FitIndependentVerificationError("metrics crossed a closed boundary")
    npz_binding = _mapping(metrics.get("sidecar"), field="metrics sidecar binding")
    npz_path, npz_digest, arrays, metadata = _load_npz(
        root=receipt_root,
        binding={
            "allow_pickle": False,
            "npz_relative_path": binding.get("npz_path"),
            "npz_sha256": binding.get("npz_sha256"),
            "npz_sha256_file": binding.get("npz_sha256_file"),
            "array_metadata": metrics.get("arrays"),
        },
        domain=V023_FIT_PREDICTION_ARRAY_DOMAIN,
        field="metrics NPZ",
        exact_keys={"identity_world", "identity_anchor", "identity_user", "identity_action", "prediction", "target", "loss"},
    )
    if (
        npz_binding.get("npz_relative_name") != npz_path.name
        or npz_binding.get("npz_sha256") != npz_digest
        or npz_binding.get("array_domain") != V023_FIT_PREDICTION_ARRAY_DOMAIN
    ):
        raise V023FitIndependentVerificationError("metrics NPZ nested binding drifted")
    for name in ("identity_world", "identity_user", "identity_action"):
        value = _fixed_int(arrays[name], field=f"metrics {name}")
        if value.dtype != np.dtype(np.int64):
            raise V023FitIndependentVerificationError(
                f"metrics {name} must use int64 identity dtype"
            )
    anchor_array = arrays["identity_anchor"]
    if anchor_array.dtype != np.dtype("S256") or anchor_array.ndim != 1:
        raise V023FitIndependentVerificationError("metrics identity_anchor is missing/malformed")
    prediction = arrays["prediction"]
    target = arrays["target"]
    loss = arrays["loss"]
    for name, value in (("prediction", prediction), ("target", target), ("loss", loss)):
        _check_array_numeric(value, field=f"metrics {name}")
    if prediction.dtype != np.dtype(np.float64) or target.dtype != np.dtype(np.float64) or prediction.ndim != 1 or target.shape != prediction.shape:
        raise V023FitIndependentVerificationError("metrics prediction/target shape/dtype drifted")
    if loss.dtype != np.dtype(np.float64) or loss.shape != (V023_FIT_UPDATE_COUNT,):
        raise V023FitIndependentVerificationError("metrics loss count/dtype drifted")
    identities: list[tuple[int, str, int, int]] = []
    if arrays["identity_world"].shape != prediction.shape or arrays["identity_user"].shape != prediction.shape or arrays["identity_action"].shape != prediction.shape or anchor_array.shape != prediction.shape:
        raise V023FitIndependentVerificationError("metrics identity arrays are not aligned")
    for world, anchor, user, action in zip(arrays["identity_world"], anchor_array, arrays["identity_user"], arrays["identity_action"], strict=True):
        identities.append((int(world), _decode_ascii(anchor, field="metrics anchor identity"), int(user), int(action)))
    expected_identities = tuple((row.world, row.anchor_id, row.user, row.action) for row in fold.heldout_rows)
    if tuple(identities) != expected_identities:
        raise V023FitIndependentVerificationError("metrics identity arrays do not exactly match held-out S rows")
    expected_targets = np.asarray([row.target for row in fold.heldout_rows], dtype=np.float64)
    if not np.array_equal(target, expected_targets):
        raise V023FitIndependentVerificationError("metrics target leaks or disagrees with authenticated source S rows")
    content_digest = _prediction_digest(identities, prediction, target)
    if metrics.get("heldout_prediction_content_digest") != content_digest or binding.get("content_digest") != content_digest:
        raise V023FitIndependentVerificationError("metrics content digest disagrees")
    _digest(
        metrics.get("fit_receipt_final_network_sha256"),
        field="metrics final network hash",
    )
    spearman = tie_aware_spearman(prediction, target)
    reported_spearman = metrics.get("spearman")
    if (reported_spearman is None) != (spearman is None):
        raise V023FitIndependentVerificationError("reported Spearman nullability drifted")
    if spearman is not None:
        _assert_scalar(reported_spearman, spearman, field="metrics Spearman")
    sign = sign_receipt(prediction, target)
    reported_sign = _mapping(metrics.get("sign"), field="metrics sign")
    for key, expected in sign.items():
        actual = reported_sign.get(key)
        if expected is None:
            if actual is not None:
                raise V023FitIndependentVerificationError(f"metrics sign {key} nullability drifted")
        elif isinstance(expected, float):
            _assert_scalar(actual, expected, field=f"metrics sign {key}")
        elif actual != expected:
            raise V023FitIndependentVerificationError(f"metrics sign {key} drifted")
    if metrics.get("heldout_supported_rows") != len(expected_identities):
        raise V023FitIndependentVerificationError("metrics held-out row count drifted")
    denominators = _mapping(metrics.get("denominators"), field="metrics denominators")
    expected_denominators = {
        "spearman_rows": len(expected_identities),
        "sign_total_rows": sign["total_rows"],
        "sign_evaluated_rows": sign["evaluated_rows"],
        "sign_excluded_rows": sign["excluded_rows"],
        "sign_positive_rows": sign["positive_denominator"],
        "sign_negative_rows": sign["negative_denominator"],
        "heldout_world_count": 1,
        "heldout_anchor_count": len(fold.heldout_anchors),
        "training_world_count": 7,
    }
    if dict(denominators) != expected_denominators:
        raise V023FitIndependentVerificationError("metrics denominators drifted")
    _compare_identity_json(metrics, expected_identities)
    if binding.get("schema") != metrics.get("schema"):
        raise V023FitIndependentVerificationError("nested metrics schema disagrees")
    if binding.get("content_digest") != metrics.get("heldout_prediction_content_digest"):
        raise V023FitIndependentVerificationError("nested metrics content digest disagrees")
    if binding.get("spearman") != metrics.get("spearman"):
        raise V023FitIndependentVerificationError("nested metrics Spearman disagrees")
    if binding.get("sign") != metrics.get("sign"):
        raise V023FitIndependentVerificationError("nested metrics sign disagrees")
    if binding.get("denominators") != metrics.get("denominators"):
        raise V023FitIndependentVerificationError("nested metrics denominators disagrees")
    if binding.get("heldout_supported_rows") != metrics.get("heldout_supported_rows"):
        raise V023FitIndependentVerificationError("nested metrics row count disagrees")
    if binding.get("identities") != metrics.get("identities"):
        raise V023FitIndependentVerificationError("nested metrics identities disagrees")
    return {
        "metrics_sha256": metrics_digest,
        "metrics_npz_sha256": npz_digest,
        "rows": len(expected_identities),
        "prediction": prediction,
        "target": target,
        "loss": loss,
        "identities": tuple(identities),
        "content_digest": content_digest,
        "spearman": spearman,
        "sign": sign,
        "denominators": expected_denominators,
        "metadata": metadata,
        "final_network_sha256": metrics.get("fit_receipt_final_network_sha256"),
    }


def _verify_fit_receipt_sidecar(
    receipt_root: Path,
    receipt: Mapping[str, Any],
    fold: _Fold,
    *,
    arm: str,
    student_seed: int,
    metrics_loss: np.ndarray,
) -> dict[str, Any]:
    nested = _mapping(receipt.get("fit_receipt"), field="fit_receipt binding")
    if nested.get("schema") != V023_FIT_RECEIPT_SCHEMA:
        raise V023FitIndependentVerificationError("fit receipt schema drifted")
    path = _safe_child(receipt_root, nested.get("path"), field="fit receipt sidecar")
    digest = _digest(nested.get("sha256"), field="fit receipt sidecar sha256")
    if file_sha256(path) != digest:
        raise V023FitIndependentVerificationError("fit receipt sidecar byte hash disagrees")
    sidecar = _load_json(path, field="fit receipt sidecar")
    body = dict(nested)
    body.pop("path", None)
    body.pop("sha256", None)
    if sidecar != body:
        raise V023FitIndependentVerificationError("fit receipt sidecar disagrees with nested body")
    for key, expected in (("arm", arm), ("student_seed", student_seed), ("updates", V023_FIT_UPDATE_COUNT), ("batch_size", V023_FIT_BATCH_SIZE), ("schema", V023_FIT_RECEIPT_SCHEMA)):
        if sidecar.get(key) != expected:
            raise V023FitIndependentVerificationError(f"fit receipt {key} drifted")
    hashes = sidecar.get("source_anchor_sha256s")
    expected_hashes = [anchor.content_digest for anchor in fold.training_anchors]
    if hashes != expected_hashes:
        raise V023FitIndependentVerificationError("fit receipt training anchors drifted")
    _digest(sidecar.get("target_source_sha256"), field="fit target source sha256")
    target_arrays = fold.informed_targets if arm == "INFORMED" else fold.placebo_targets
    expected_target_digest = _target_source_digest(fold.training_anchors, target_arrays)
    if sidecar.get("target_source_sha256") != expected_target_digest:
        raise V023FitIndependentVerificationError("fit receipt arm-specific target source drifted")
    for key in ("initial_network_sha256", "final_network_sha256", "config_sha256"):
        _digest(sidecar.get(key), field=f"fit receipt {key}")
    if sidecar.get("config_sha256") != V023_LEARNER_CONFIG_SHA256:
        raise V023FitIndependentVerificationError("fit receipt learner config hash drifted")
    if sidecar.get("initial_network_sha256") != V023_INITIAL_NETWORK_SHA256_BY_SEED.get(
        student_seed
    ):
        raise V023FitIndependentVerificationError(
            "fit receipt initial parameter digest disagrees with the frozen seed"
        )
    losses = sidecar.get("losses")
    if not isinstance(losses, list) or len(losses) != V023_FIT_UPDATE_COUNT:
        raise V023FitIndependentVerificationError("fit receipt losses are not exactly 2000")
    try:
        receipt_losses = np.asarray(losses, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise V023FitIndependentVerificationError("fit receipt losses are malformed") from error
    if receipt_losses.shape != (V023_FIT_UPDATE_COUNT,) or not np.all(np.isfinite(receipt_losses)):
        raise V023FitIndependentVerificationError("fit receipt losses are non-finite/incomplete")
    if not np.array_equal(receipt_losses, metrics_loss):
        raise V023FitIndependentVerificationError("fit receipt losses disagree with metrics NPZ")
    losses_digest = _array_digest(metrics_loss, domain=V023_FIT_PREDICTION_ARRAY_DOMAIN)
    if sidecar.get("losses_count") != V023_FIT_UPDATE_COUNT or sidecar.get("losses_sha256") != losses_digest:
        raise V023FitIndependentVerificationError("fit receipt loss digest disagrees")
    return {
        "fit_receipt_sha256": digest,
        "target_source_sha256": expected_target_digest,
        "losses_sha256": losses_digest,
        "initial_network_sha256": sidecar.get("initial_network_sha256"),
        "final_network_sha256": sidecar.get("final_network_sha256"),
    }


def _verify_placebo(
    receipt_root: Path,
    receipt: Mapping[str, Any],
    fold: _Fold,
    *,
    source_manifest_sha256: str,
    arm: str,
    student_seed: int,
) -> dict[str, Any]:
    nested = _mapping(receipt.get("placebo"), field="placebo binding")
    if nested.get("schema") != V023_FIT_PLACEBO_SCHEMA:
        raise V023FitIndependentVerificationError("placebo schema drifted")
    path = _safe_child(receipt_root, nested.get("path"), field="placebo sidecar")
    digest = _digest(nested.get("sha256"), field="placebo sha256")
    if file_sha256(path) != digest:
        raise V023FitIndependentVerificationError("placebo byte hash disagrees")
    sidecar = _load_json(path, field="placebo sidecar")
    body = dict(nested)
    body.pop("path", None)
    body.pop("sha256", None)
    if sidecar != body:
        raise V023FitIndependentVerificationError("placebo sidecar disagrees with nested body")
    if sidecar.get("schema") != V023_FIT_PLACEBO_SCHEMA or sidecar.get("claim_ceiling") != V023_CLAIM_CEILING:
        raise V023FitIndependentVerificationError("placebo schema/claim ceiling drifted")
    if sidecar.get("held_out_world") != fold.held_out_world or sidecar.get("arm") != arm or sidecar.get("student_seed") != student_seed:
        raise V023FitIndependentVerificationError("placebo identity drifted")
    if sidecar.get("source_manifest_sha256") != source_manifest_sha256:
        raise V023FitIndependentVerificationError("placebo source manifest drifted")
    if sidecar.get("placebo_key") != V023_PLACEBO_KEY or sidecar.get("placebo_key_sha256") != V023_PLACEBO_KEY_SHA256:
        raise V023FitIndependentVerificationError("placebo key drifted")
    _digest(sidecar.get("content_digest"), field="placebo content digest")
    eligible = _int(sidecar.get("eligible_supported_rows"), field="placebo eligible rows")
    total = _int(sidecar.get("total_supported_rows"), field="placebo total rows")
    if total != fold.placebo_total or eligible != fold.placebo_eligible or total <= 0 or not 0 <= eligible <= total:
        raise V023FitIndependentVerificationError("placebo coverage denominators drifted")
    coverage = _float(sidecar.get("coverage"), field="placebo coverage")
    if abs(coverage - eligible / total) > 1.0e-12:
        raise V023FitIndependentVerificationError("placebo coverage disagrees")
    if coverage < V023_PLACEBO_MIN_COVERAGE:
        raise V023FitIndependentVerificationError("placebo coverage is below 80 percent")
    if sidecar.get("meets_coverage_gate") is not True:
        raise V023FitIndependentVerificationError("placebo coverage gate drifted")
    identities = sidecar.get("training_anchor_identities")
    expected_identities = [
        {"world": anchor.world, "anchor_id": anchor.anchor_id, "content_digest": anchor.content_digest}
        for anchor in fold.training_anchors
    ]
    if identities != expected_identities:
        raise V023FitIndependentVerificationError("placebo training anchor identities drifted")
    mappings = sidecar.get("mappings")
    if not isinstance(mappings, list) or mappings != list(fold.mappings):
        raise V023FitIndependentVerificationError("placebo mapping is not the fold-local expected mapping")
    if sidecar.get("content_digest") != fold.placebo_digest:
        raise V023FitIndependentVerificationError("placebo content digest disagrees")
    target_arrays = fold.informed_targets if arm == "INFORMED" else fold.placebo_targets
    expected_target_digest = _target_source_digest(fold.training_anchors, target_arrays)
    if sidecar.get("target_source_sha256") != expected_target_digest:
        raise V023FitIndependentVerificationError("placebo arm target source disagrees")
    if sidecar.get("target_array_count") != len(target_arrays) or sidecar.get("target_array_shapes") != [list(target.shape) for target in target_arrays]:
        raise V023FitIndependentVerificationError("placebo target array metadata drifted")
    if sidecar.get("test_split_opened") is not False or sidecar.get("episode_training") is not False or sidecar.get("learner_update") is not True:
        raise V023FitIndependentVerificationError("placebo crossed a closed boundary")
    return {
        "placebo_sha256": digest,
        "content_digest": fold.placebo_digest,
        "eligible_supported_rows": eligible,
        "total_supported_rows": total,
        "coverage": coverage,
        "mappings": len(mappings),
    }


def _check_top_level(
    receipt: Mapping[str, Any],
    *,
    preflight: str | None,
) -> tuple[int, int, str, str]:
    if receipt.get("schema") != V023_FIT_SCHEMA or receipt.get("status") != "PASS":
        raise V023FitIndependentVerificationError("fit schema/status drifted")
    if receipt.get("claim_ceiling") != V023_CLAIM_CEILING or receipt.get("contract_sha256") != V023_CONTRACT_SHA256:
        raise V023FitIndependentVerificationError("fit claim/contract hash drifted")
    if receipt.get("split") != "TRAIN_DEVELOPMENT" or receipt.get("test_split_opened") is not False or receipt.get("episode_training") is not False or receipt.get("learner_update") is not True or receipt.get("test_worlds") != []:
        raise V023FitIndependentVerificationError("fit crossed a closed boundary")
    heldout = _int(receipt.get("held_out_world"), field="held_out_world")
    seed = _int(receipt.get("student_seed"), field="student_seed")
    arm = receipt.get("arm")
    if heldout not in V023_GATE_WORLDS or seed not in V023_STUDENT_SEEDS or arm not in V023_FIT_ARMS:
        raise V023FitIndependentVerificationError("fit LOO identity is outside frozen panel")
    if receipt.get("update_count") != V023_FIT_UPDATE_COUNT:
        raise V023FitIndependentVerificationError("fit update count is not exactly 2000")
    no_rescue = _mapping(receipt.get("no_rescue"), field="fit no-rescue receipt")
    expected_no_rescue = {
        "early_stopping": False,
        "best_checkpoint_selection": False,
        "outcome_weighting": False,
        "heldout_target_permutation": False,
    }
    if dict(no_rescue) != expected_no_rescue:
        raise V023FitIndependentVerificationError("fit no-rescue receipt drifted")
    fit_preflight = _digest(receipt.get("preflight_manifest_sha256"), field="fit preflight hash")
    if preflight is not None and fit_preflight != _digest(preflight, field="expected preflight hash"):
        raise V023FitIndependentVerificationError("fit preflight hash disagrees with expected")
    source_manifest = _digest(receipt.get("source_manifest_sha256"), field="fit source manifest hash")
    _verify_receipt_seal(receipt, field="fit receipt")
    return heldout, seed, str(arm), source_manifest


def verify_v023_fit_artifact(
    receipt_path: Path,
    *,
    source_manifest_path: Path | None = None,
    source_manifest: Path | None = None,
    source_index_paths: Sequence[Path] | None = None,
    source_paths: Sequence[Path] | None = None,
    expected_source_manifest_sha256: str | None = None,
    preflight_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify one sealed fit artifact against an authenticated eight-world panel.

    ``source_manifest_path`` and ``source_manifest`` are aliases.  The
    verifier intentionally requires the manifest (and therefore the exact
    source panel) instead of inferring source bytes from a fit receipt.  The
    successful return is explicitly *not* ``PASS`` because the production
    schema does not make the logical network digest independently recomputable
    without the typed model-head algorithm.
    """

    if source_manifest_path is not None and source_manifest is not None and Path(source_manifest_path).resolve() != Path(source_manifest).resolve():
        raise V023FitIndependentVerificationError("source manifest aliases disagree")
    manifest_path = source_manifest_path or source_manifest
    if manifest_path is None:
        raise V023FitIndependentVerificationError("authenticated source manifest is required")
    if source_index_paths is not None and source_paths is not None and tuple(Path(p).resolve() for p in source_index_paths) != tuple(Path(p).resolve() for p in source_paths):
        raise V023FitIndependentVerificationError("source path aliases disagree")
    index_paths = source_index_paths if source_index_paths is not None else source_paths
    receipt_file = Path(receipt_path)
    receipt = _load_json(receipt_file, field="fit receipt")
    heldout, seed, arm, source_manifest_digest = _check_top_level(receipt, preflight=preflight_manifest_sha256)
    if expected_source_manifest_sha256 is not None and source_manifest_digest != _digest(expected_source_manifest_sha256, field="expected source manifest hash"):
        raise V023FitIndependentVerificationError("fit source manifest hash disagrees with expected")
    manifest_payload, worlds = _verify_source_manifest(
        Path(manifest_path),
        preflight=_digest(receipt.get("preflight_manifest_sha256"), field="fit preflight hash"),
        expected_digest=source_manifest_digest,
        source_index_paths=index_paths,
    )
    if manifest_payload.get("source_manifest_sha256") != source_manifest_digest:
        raise V023FitIndependentVerificationError("fit/source manifest binding disagrees")
    root = receipt_file.parent.resolve()
    source_panel = _mapping(receipt.get("source_panel"), field="source panel")
    if source_panel.get("schema") != V023_SOURCE_ARTIFACT_SCHEMA or source_panel.get("version") != V023_SOURCE_ARTIFACT_VERSION or source_panel.get("worlds") != list(V023_GATE_WORLDS) or source_panel.get("source_manifest_sha256") != source_manifest_digest or source_panel.get("source_manifest_path") != Path(manifest_path).name:
        raise V023FitIndependentVerificationError("fit source panel identity drifted")
    if (
        source_panel.get("source_pair_count")
        != sum(world.pair_count for world in worlds)
        or source_panel.get("source_anchor_count")
        != sum(len(world.anchors) for world in worlds)
    ):
        raise V023FitIndependentVerificationError("fit source panel counts drifted")
    expected_index_hashes = {str(world.world): world.index_digest for world in worlds}
    if source_panel.get("source_index_sha256s") != expected_index_hashes:
        raise V023FitIndependentVerificationError("fit source index hashes drifted")
    fold = _make_fold(worlds, held_out_world=heldout)
    fold_payload = _mapping(receipt.get("fold"), field="fit fold")
    expected_training_worlds = [world for world in V023_GATE_WORLDS if world != heldout]
    if fold_payload.get("held_out_world") != heldout or fold_payload.get("training_worlds") != expected_training_worlds or fold_payload.get("training_anchor_count") != len(fold.training_anchors) or fold_payload.get("heldout_anchor_count") != len(fold.heldout_anchors) or fold_payload.get("training_anchor_sha256s") != [anchor.content_digest for anchor in fold.training_anchors] or fold_payload.get("heldout_anchor_sha256s") != [anchor.content_digest for anchor in fold.heldout_anchors] or fold_payload.get("heldout_anchor_ids") != [anchor.anchor_id for anchor in fold.heldout_anchors] or fold_payload.get("heldout_is_untouched") is not True:
        raise V023FitIndependentVerificationError("fit LOO identities or held-out isolation drifted")
    model = _verify_model(root, receipt)
    metrics = _verify_metrics(root, receipt, fold, source_manifest_sha256=source_manifest_digest, arm=arm, student_seed=seed)
    if receipt.get("denominators") != metrics["denominators"]:
        # ``denominators`` is duplicated at the runner-owned top level; it is
        # an identity receipt, not an independently trusted summary.
        raise V023FitIndependentVerificationError("fit top-level denominators drifted")
    fit = _verify_fit_receipt_sidecar(root, receipt, fold, arm=arm, student_seed=seed, metrics_loss=metrics["loss"])
    if metrics["final_network_sha256"] != fit["final_network_sha256"]:
        raise V023FitIndependentVerificationError(
            "metrics final network hash disagrees with fit receipt"
        )
    if model["network_sha256"] != fit["final_network_sha256"]:
        raise V023FitIndependentVerificationError(
            "model logical network hash disagrees with fit receipt"
        )
    placebo = _verify_placebo(root, receipt, fold, source_manifest_sha256=source_manifest_digest, arm=arm, student_seed=seed)
    return {
        "status": "FIT_ARTIFACT_VERIFIED_WITH_GAPS",
        "integrity_status": "VERIFIED",
        "scientific_claim": False,
        "gate_ready": False,
        "held_out_world": heldout,
        "student_seed": seed,
        "arm": arm,
        "source_manifest_sha256": source_manifest_digest,
        "heldout_supported_rows": metrics["rows"],
        "spearman": metrics["spearman"],
        "sign": metrics["sign"],
        "model": model,
        "metrics": {
            "metrics_sha256": metrics["metrics_sha256"],
            "metrics_npz_sha256": metrics["metrics_npz_sha256"],
            "content_digest": metrics["content_digest"],
        },
        "fit_receipt": fit,
        "placebo": placebo,
        "logical_network_hash_verified": False,
        "gaps": [
            {
                "code": "LOGICAL_NETWORK_HASH_NOT_INDEPENDENTLY_RECOMPUTABLE",
                "detail": "The production model NPZ has tensor bytes but no independent head-algorithm/schema contract; the logical network SHA-256 is retained and cross-bound only, never recomputed with stdlib+NumPy.",
            }
        ],
    }


def verify_fit_artifact(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Short alias for :func:`verify_v023_fit_artifact`."""

    return verify_v023_fit_artifact(*args, **kwargs)


def verify_v023_fit_panel(
    receipt_paths: Sequence[Path],
    *,
    source_manifest_path: Path | None = None,
    source_manifest: Path | None = None,
    source_index_paths: Sequence[Path] | None = None,
    source_paths: Sequence[Path] | None = None,
    expected_source_manifest_sha256: str | None = None,
    preflight_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify the exact 8 x 3 x 2 fit schedule and retain the model gap."""

    expected = {(world, seed, arm) for world in V023_GATE_WORLDS for seed in V023_STUDENT_SEEDS for arm in V023_FIT_ARMS}
    reports = [
        verify_v023_fit_artifact(
            Path(path),
            source_manifest_path=source_manifest_path,
            source_manifest=source_manifest,
            source_index_paths=source_index_paths,
            source_paths=source_paths,
            expected_source_manifest_sha256=expected_source_manifest_sha256,
            preflight_manifest_sha256=preflight_manifest_sha256,
        )
        for path in receipt_paths
    ]
    identities = {(int(report["held_out_world"]), int(report["student_seed"]), str(report["arm"])) for report in reports}
    if len(reports) != 48 or identities != expected:
        raise V023FitIndependentVerificationError("fit panel is not the exact 8 x 3 x 2 schedule")
    return {
        "status": "FIT_PANEL_VERIFIED_WITH_GAPS",
        "integrity_status": "VERIFIED",
        "scientific_claim": False,
        "gate_ready": False,
        "fit_count": len(reports),
        "identities": sorted(identities),
        "logical_network_hash_verified": False,
        "gaps": [
            {
                "code": "LOGICAL_NETWORK_HASH_NOT_INDEPENDENTLY_RECOMPUTABLE",
                "detail": "Each model's logical network digest is only cross-bound; independent tensor-to-head hashing requires a missing head algorithm/schema contract.",
            }
        ],
    }


__all__ = [
    "V023_GATE_SCHEMA",
    "V023_FIT_SCHEMA",
    "V023_SOURCE_MANIFEST_SCHEMA",
    "V023_SOURCE_SHARD_SCHEMA",
    "V023_SOURCE_ARTIFACT_SCHEMA",
    "V023_SOURCE_ARTIFACT_VERSION",
    "V023_FIT_MODEL_SCHEMA",
    "V023_FIT_METRICS_SCHEMA",
    "V023_FIT_PLACEBO_SCHEMA",
    "V023_FIT_RECEIPT_SCHEMA",
    "V023_GATE_WORLDS",
    "V023_STUDENT_SEEDS",
    "V023_FIT_ARMS",
    "V023_FIT_UPDATE_COUNT",
    "V023_FIT_BATCH_SIZE",
    "V023_PLACEBO_KEY",
    "V023_PLACEBO_KEY_SHA256",
    "V023_CONTRACT_SHA256",
    "V023_CLAIM_CEILING",
    "V023FitIndependentVerificationError",
    "V023FitArtifactVerificationError",
    "V023IndependentFitVerificationError",
    "canonical_sha256",
    "file_sha256",
    "tie_aware_spearman",
    "sign_receipt",
    "verify_v023_fit_artifact",
    "verify_fit_artifact",
    "verify_v023_fit_panel",
]
