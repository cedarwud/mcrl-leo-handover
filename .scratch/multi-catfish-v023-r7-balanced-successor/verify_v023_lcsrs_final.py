#!/usr/bin/env python3
"""Independent final-panel verifier for the V0.23 LC-SRS gate.

This module is deliberately a *consumer* of immutable evidence.  It does not
import the production source, fit, composition, simulator, learner, or
torch modules and it never opens TEST or performs an update.  The source and
fit panels are rechecked through the two independent numeric verifiers, while
the composition panel is reopened and checked here with only the standard
library and NumPy.

The public entry point returns a receipt even on failure.  Integrity failures
always return ``c3_decision == "INVALID_RUN"``; no scientific token is
created before every source, fit, composition, identity, and sidecar check
has passed.  A successful return is still TRAIN development evidence and not
an efficacy claim.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np


V023_GATE_WORLDS = tuple(range(2026121801, 2026121809))
V023_STUDENT_SEEDS = (2026135201, 2026135202, 2026135203)
V023_FIT_ARMS = ("INFORMED", "MATCHED_PLACEBO")
V023_COMPOSITION_SCHEMA = (
    "multi-catfish-mcrl-v023-lcsrs-composition-artifact-v1"
)
V023_COMPOSITION_CLAIM = (
    "TRAIN_DEVELOPMENT_SOURCE_AND_LEARNER_GATE_NO_TEST_NO_EPISODE_TRAINING_NO_EFFICACY"
)
V023_CONTRACT_SHA256 = (
    "027e09a75a2e775b81b570cd49f6637dd10d55220d3ace2cf26a5b37ab002be5"
)
V023_EXECUTION_ADDENDUM_SHA256 = (
    "486568d017de84bfba5aa8bb65f634998446ac4b3ad471795b9055085e8f5070"
)
V023_DRAW_COUNT = 32
V023_PHASES = tuple(range(1, 10))
V023_ACTION_COUNT = 28
V023_SIGN_THRESHOLD = 0.02
V023_SERVICE_MARGIN = 0.01
V023_ARRAY_DOMAIN = "v023-composition-array-v1"
V023_PROFILE_ACTION_DOMAIN = "multi-catfish-mcrl-v023-profile-actions-v1"
V023_ROLE_ORDER = ("ZERO_SURFACE_B", "INFORMED", "TEACHER_ORACLE")
V023_REQUIRED_NONMUTATION = frozenset(
    {"environment", "rng", "q1", "q2", "q3", "matched_field"}
)
V023_TOLERANCE_FLOOR = 1.0e-12
V023_Q2_STATE_SCHEMA = "multi-catfish-mcrl-v014-ops3-q2-state-v1"
V023_Q2_STATE_SCHEMA_SHA256 = "440f98a87b8a91be647e28a15a2509853f8566864a2be560b8602421185efc50"
V023_Q2_STATE_DIM = 448
V023_Q2_FEATURE_DIM = 16
V023_OPS3_HORIZON = 3
# The native D2 clock is the simulator decision interval (47 * 0.64 s).
# Preserve the frozen binary float rather than replacing it with the decimal
# spelling ``30.08``.
V023_OPS3_INTERVAL_S = float.fromhex("0x1.e147ae147ae15p+4")
V023_LAMBDA_BITS_PER_J = float.fromhex("0x1.c3c0a7b6b86d3p+26")
V023_KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")

_HERE = Path(__file__).resolve().parent
_SCIENTIFIC_PATH = _HERE / "verify_v023_lcsrs_scientific.py"
_FIT_INDEPENDENT_PATH = _HERE / "verify_v023_lcsrs_fit_independent.py"
_R7_DECISION_PATH = _HERE / "r7_balanced_successor_gate.py"


class V023FinalVerificationError(RuntimeError):
    """The final evidence panel is incomplete, tampered, or unrecomputable."""


@dataclass(frozen=True)
class _CompositionShard:
    path: Path
    payload: Mapping[str, Any]
    arrays: Mapping[str, np.ndarray]
    world: int
    seed: int
    arm: str


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023FinalVerificationError("value is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _json_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise V023FinalVerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023FinalVerificationError(f"{label} is missing or is a symlink")
    raw = target.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"), object_pairs_hook=_json_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise V023FinalVerificationError(f"{label} is not canonical ASCII JSON") from error
    if not isinstance(payload, dict) or raw not in (
        _canonical_bytes(payload),
        _canonical_bytes(payload) + b"\n",
    ):
        raise V023FinalVerificationError(f"{label} is not canonical JSON")
    return payload


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023FinalVerificationError(f"expected regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise V023FinalVerificationError(f"{label} is not a lowercase SHA-256")
    return value


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise V023FinalVerificationError(f"{label} is not an object")
    return value


def _array_digest(value: np.ndarray, *, domain: str) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype == object:
        raise V023FinalVerificationError("object arrays are forbidden")
    digest = hashlib.sha256()
    digest.update(domain.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _safe_child(root: Path, relative: object, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise V023FinalVerificationError(f"{label} path is unsafe")
    base = Path(root).resolve()
    target = (base / relative).resolve()
    if target.is_symlink() or not target.is_file() or not target.is_relative_to(base):
        raise V023FinalVerificationError(f"{label} is missing or escapes its root")
    return target


def _verify_seal(payload: Mapping[str, Any], *, label: str) -> None:
    declared = _digest(payload.get("receipt_sha256"), label=f"{label}.receipt_sha256")
    unsigned = dict(payload)
    unsigned.pop("receipt_sha256", None)
    if canonical_sha256(unsigned) != declared:
        raise V023FinalVerificationError(f"{label} receipt seal disagrees")


def _load_npz(root: Path, binding: Mapping[str, Any], *, label: str) -> dict[str, np.ndarray]:
    if binding.get("allow_pickle") is not False:
        raise V023FinalVerificationError(f"{label} must set allow_pickle=false")
    path = _safe_child(root, binding.get("npz_relative_path"), label=f"{label} NPZ")
    expected = _digest(binding.get("npz_sha256"), label=f"{label} NPZ sha256")
    if file_sha256(path) != expected:
        raise V023FinalVerificationError(f"{label} NPZ byte hash disagrees")
    digest_path = _safe_child(root, binding.get("npz_sha256_file"), label=f"{label} NPZ digest")
    if digest_path.read_bytes() != f"{expected}  {path.name}\n".encode("ascii"):
        raise V023FinalVerificationError(f"{label} NPZ digest sidecar disagrees")
    try:
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True, order="C") for name in archive.files}
    except Exception as error:
        raise V023FinalVerificationError(f"{label} NPZ cannot be loaded safely") from error
    metadata = _mapping(binding.get("array_metadata"), label=f"{label} array metadata")
    if set(arrays) != set(metadata) or binding.get("array_count") != len(arrays):
        raise V023FinalVerificationError(f"{label} NPZ members disagree with metadata")
    for name, array in arrays.items():
        entry = _mapping(metadata[name], label=f"{label} metadata[{name}]")
        if array.dtype == object or entry.get("dtype") != array.dtype.str or entry.get("shape") != list(array.shape):
            raise V023FinalVerificationError(f"{label} array {name} dtype/shape disagrees")
        if entry.get("sha256") != _array_digest(array, domain=V023_ARRAY_DOMAIN):
            raise V023FinalVerificationError(f"{label} array {name} digest disagrees")
    return arrays


def _comparison_tolerance(left: float, right: float) -> float:
    return max(
        V023_TOLERANCE_FLOOR,
        1024.0 * np.finfo(np.float64).eps * max(1.0, abs(float(left)), abs(float(right))),
    )


def strict_direction(left: float, right: float) -> int:
    tolerance = _comparison_tolerance(left, right)
    return 1 if left - right > tolerance else -1 if left - right < -tolerance else 0


def _profile_action_sha256(actions: np.ndarray) -> str:
    values = np.ascontiguousarray(np.asarray(actions, dtype=np.int64))
    if values.ndim != 1:
        raise V023FinalVerificationError("profile action vector is not one-dimensional")
    digest = hashlib.sha256()
    digest.update(V023_PROFILE_ACTION_DOMAIN.encode("ascii"))
    digest.update(struct.pack(">I", int(values.size)))
    digest.update(values.tobytes(order="C"))
    return digest.hexdigest()


def _decode_ascii(value: object, *, label: str) -> str:
    try:
        raw = bytes(value) if not isinstance(value, str) else value.encode("ascii")
        result = raw.rstrip(b"\0").decode("ascii")
    except (TypeError, ValueError, UnicodeDecodeError) as error:
        raise V023FinalVerificationError(f"{label} is not ASCII") from error
    if not result:
        raise V023FinalVerificationError(f"{label} is empty")
    return result


def _assert_equal(actual: object, expected: object, *, label: str) -> None:
    left = np.asarray(actual)
    right = np.asarray(expected)
    if left.shape != right.shape or left.dtype != right.dtype or not np.array_equal(left, right):
        raise V023FinalVerificationError(f"{label} differs")


def _assert_numeric_equal(actual: object, expected: object, *, label: str) -> None:
    """Compare finite numeric evidence under the frozen reporting tolerance."""

    left = np.asarray(actual, dtype=np.float64)
    right = np.asarray(expected, dtype=np.float64)
    if left.shape != right.shape or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise V023FinalVerificationError(f"{label} is nonfinite or has the wrong shape")
    tolerance = np.maximum(
        V023_TOLERANCE_FLOOR,
        1024.0 * np.finfo(np.float64).eps * np.maximum(1.0, np.maximum(np.abs(left), np.abs(right))),
    )
    if not np.all(np.abs(left - right) <= tolerance):
        raise V023FinalVerificationError(f"{label} differs")


def _q1_masked_argmax(q1: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Reconstruct the detached Q1 reference with the native lowest-index tie rule."""

    values = np.asarray(q1, dtype=np.float64)
    legal = np.asarray(mask, dtype=np.bool_)
    if values.ndim != 3 or values.shape != legal.shape or values.shape[-1] != V023_ACTION_COUNT:
        raise V023FinalVerificationError("Q1 reference surface shape drifted")
    result = np.empty(values.shape[:2], dtype=np.int64)
    for anchor in range(values.shape[0]):
        for user in range(values.shape[1]):
            choices = np.flatnonzero(legal[anchor, user])
            if choices.size == 0:
                raise V023FinalVerificationError("Q1 reference has no legal action")
            scores = values[anchor, user, choices]
            result[anchor, user] = int(choices[int(np.argmax(scores))])
    return result


def _q12_masked_argmax(q12: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Reconstruct native Q1+Q2 references from the float32 carrier.

    V0.23 stores the detached Q1/Q2 surfaces as the float32 model outputs and
    selects the background action from their exact float32 sum.  The source
    ``reference_actions`` array is therefore an authenticated witness, not an
    input to this selection; recompute it here with the native lowest-index
    exact-tie rule.
    """

    values = np.asarray(q12, dtype=np.float32)
    legal = np.asarray(mask, dtype=np.bool_)
    if (
        values.ndim != 3
        or values.shape != legal.shape
        or values.shape[-1] != V023_ACTION_COUNT
        or not np.all(np.isfinite(values))
    ):
        raise V023FinalVerificationError("Q1+Q2 reference surface shape drifted")
    result = np.empty(values.shape[:2], dtype=np.int64)
    for anchor in range(values.shape[0]):
        for user in range(values.shape[1]):
            choices = np.flatnonzero(legal[anchor, user])
            if choices.size == 0:
                raise V023FinalVerificationError("Q1+Q2 reference has no legal action")
            scores = values[anchor, user, choices]
            result[anchor, user] = int(choices[int(np.argmax(scores))])
    return result


def _validated_q12(q1: np.ndarray, q2: np.ndarray, q12: np.ndarray) -> np.ndarray:
    """Return the exact float32 Q1+Q2 carrier after checking its witness."""

    first = np.asarray(q1, dtype=np.float32)
    second = np.asarray(q2, dtype=np.float32)
    stored = np.asarray(q12, dtype=np.float32)
    if first.shape != second.shape or first.shape != stored.shape:
        raise V023FinalVerificationError("Q1/Q2/Q1+Q2 carrier shapes disagree")
    if not np.all(np.isfinite(first)) or not np.all(np.isfinite(second)) or not np.all(np.isfinite(stored)):
        raise V023FinalVerificationError("Q1/Q2/Q1+Q2 carrier is nonfinite")
    expected = (first + second).astype(np.float32)
    if not np.array_equal(stored, expected):
        raise V023FinalVerificationError("source Q1+Q2 float32 carrier identity drifted")
    return expected


def _verify_q2_state_digest_receipt(
    context: Mapping[str, Any], state: np.ndarray, mask: np.ndarray, *, label: str
) -> None:
    """Bind the Q2 state digest at its canonical ``q2_context`` location."""

    expected = _q2_state_sha256(state, mask)
    if context.get("q2_state_sha256") != expected:
        raise V023FinalVerificationError(f"{label} Q2 state digest disagrees")


def _transition_class(
    physical_keys: np.ndarray, *, user: int, reference: int, candidate: int
) -> str:
    """Classify a retained move from its authenticated physical keys."""

    values = np.asarray(physical_keys, dtype=np.int64)
    if values.ndim != 3 or values.shape[-1] != 2:
        raise V023FinalVerificationError("source physical-key surface shape drifted")
    reference_key = tuple(int(value) for value in values[user, reference])
    candidate_key = tuple(int(value) for value in values[user, candidate])
    if reference_key == candidate_key:
        return "SAME_PHYSICAL_LINK"
    if reference_key[0] == candidate_key[0]:
        return "INTRA_SATELLITE_BEAM_MOVE"
    return "INTER_SATELLITE_MOVE"


def _parse_utc_sequence(value: object, *, label: str) -> tuple[dt.datetime, ...]:
    """Parse the canonical timezone-aware timing receipts without production imports."""

    if not isinstance(value, list):
        raise V023FinalVerificationError(f"{label} is not a timestamp list")
    parsed: list[dt.datetime] = []
    for item in value:
        if not isinstance(item, str):
            raise V023FinalVerificationError(f"{label} contains a non-string timestamp")
        try:
            timestamp = dt.datetime.fromisoformat(item)
        except ValueError as error:
            raise V023FinalVerificationError(f"{label} contains invalid ISO time") from error
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise V023FinalVerificationError(f"{label} timestamp is not timezone-aware")
        parsed.append(timestamp)
    return tuple(parsed)


def _verify_q2_timing(
    context: Mapping[str, Any], *, phase: int, horizon: int, label: str
) -> None:
    """Verify native D2 substeps and 640 ms decision-endpoint timing.

    One projected decision contributes 47 native D2 substeps.  The final
    anchor has horizon zero and consequently must carry three empty timing
    lists; requiring a non-empty list or exactly three indices would reject a
    valid phase-9 source shard.
    """

    expected_horizon = min(V023_OPS3_HORIZON, max(0, 9 - int(phase)))
    if int(horizon) != expected_horizon:
        raise V023FinalVerificationError(
            f"{label} horizon does not match phase schedule"
        )
    indices = context.get("future_d2_indices")
    if not isinstance(indices, list) or any(type(value) is not int for value in indices):
        raise V023FinalVerificationError(f"{label} future D2 indices are malformed")
    expected_indices = list(
        range((int(phase) + 1) * 47, (int(phase) + 1 + expected_horizon) * 47)
    )
    if indices != expected_indices:
        raise V023FinalVerificationError(f"{label} future D2 index schedule drifted")

    sample_raw = context.get("sample_times_utc")
    offset_raw = context.get("offset_times_utc")
    sample = _parse_utc_sequence(sample_raw, label=f"{label} sample_times_utc")
    offsets = _parse_utc_sequence(offset_raw, label=f"{label} offset_times_utc")
    if len(sample) != expected_horizon * 47 or len(offsets) != expected_horizon:
        raise V023FinalVerificationError(f"{label} projection timestamp count drifted")
    if expected_horizon == 0:
        if indices or sample or offsets:
            raise V023FinalVerificationError(
                f"{label} horizon-zero timing lists must all be empty"
            )
        return
    if any(
        abs((right - left).total_seconds() - 0.640) > 1.0e-9
        for left, right in zip(sample, sample[1:], strict=False)
    ):
        raise V023FinalVerificationError(f"{label} projection clock is not native 640 ms")
    expected_offsets = tuple(sample[(index + 1) * 47 - 1] for index in range(expected_horizon))
    if offsets != expected_offsets:
        raise V023FinalVerificationError(
            f"{label} offset timestamps are not decision endpoints"
        )


def _recompute_ops3_target(
    persistence: np.ndarray,
    rate: np.ndarray,
    power: np.ndarray,
    *,
    q1_reference: np.ndarray,
    mask: np.ndarray,
    horizon: int,
) -> np.ndarray:
    """Recompute one anchor's repriced target from raw ``(U,H,A)`` terms."""

    chi = np.asarray(persistence, dtype=np.float64)
    rates = np.asarray(rate, dtype=np.float64)
    powers = np.asarray(power, dtype=np.float64)
    references = np.asarray(q1_reference, dtype=np.int64)
    legal = np.asarray(mask, dtype=np.bool_)
    if (
        chi.ndim != 3
        or rates.shape != chi.shape
        or powers.shape != chi.shape
        or references.shape != (chi.shape[0],)
        or legal.shape != (chi.shape[0], chi.shape[2])
        or chi.shape[1] != V023_OPS3_HORIZON
        or not 0 <= int(horizon) <= V023_OPS3_HORIZON
        or not np.all(np.isfinite(chi))
        or not np.all(np.isfinite(rates))
        or not np.all(np.isfinite(powers))
    ):
        raise V023FinalVerificationError("OPS-3 target inputs are malformed")
    if int(horizon) == 0:
        return np.zeros_like(rates[:, 0, :], dtype=np.float64)
    terms = chi[:, : int(horizon), :] * V023_OPS3_INTERVAL_S * (
        rates[:, : int(horizon), :] - V023_LAMBDA_BITS_PER_J * powers[:, : int(horizon), :]
    ) - (1.0 - chi[:, : int(horizon), :]) * V023_KAPPA_BITS
    # ``terms`` is (U,H,A).  The projected horizon is the only averaging
    # axis; averaging over actions would change the target's shape and meaning.
    z2 = np.mean(terms, axis=1, dtype=np.float64)
    centered = z2 - z2[np.arange(chi.shape[0]), references][:, None]
    return np.where(legal, centered / V023_KAPPA_BITS, 0.0)


def _diagnostic_rows(diag: object, *, label: str) -> tuple[Mapping[str, Any], list[object]]:
    """Read the single C2 diagnostic object and its row list."""

    if not isinstance(diag, Mapping):
        raise V023FinalVerificationError(f"{label} diagnostic must be an object")
    rows = diag.get("rows")
    if not isinstance(rows, list):
        raise V023FinalVerificationError(f"{label} diagnostic rows must be a list")
    return diag, rows


def _target_sign_rank(
    prediction: np.ndarray, target: np.ndarray
) -> tuple[float | None, float | None, int]:
    """Return C2 sign/rank diagnostics with the frozen target threshold."""

    predicted = np.asarray(prediction, dtype=np.float64)
    truth = np.asarray(target, dtype=np.float64)
    if predicted.ndim != 1 or truth.shape != predicted.shape or not np.all(np.isfinite(predicted)) or not np.all(np.isfinite(truth)):
        raise V023FinalVerificationError("C2 target sign/rank inputs are malformed")
    eligible = np.abs(truth) >= V023_SIGN_THRESHOLD
    count = int(np.count_nonzero(eligible))
    sign = None if count == 0 else float(np.mean(np.sign(predicted[eligible]) == np.sign(truth[eligible])))
    # tie_aware_spearman is defined below and resolved when this function is
    # called after module initialization.
    return sign, tie_aware_spearman(predicted, truth), count


def _q2_state_sha256(states: np.ndarray, masks: np.ndarray) -> str:
    """Recompute the V0.14 state payload digest without importing production code."""

    state = np.asarray(states, dtype=np.float32)
    legal = np.asarray(masks, dtype=np.bool_)
    payload = {
        "schema_sha256": V023_Q2_STATE_SCHEMA_SHA256,
        "state_float32_hex": [float(value).hex() for value in state.ravel()],
        "masks": legal.astype(np.uint8).tolist(),
    }
    return canonical_sha256(payload)


def _load_independent(path: Path, name: str) -> ModuleType:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise V023FinalVerificationError(f"independent verifier is missing: {target}")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise V023FinalVerificationError(f"cannot load independent verifier: {target}")
    module = importlib.util.module_from_spec(spec)
    # Do not expose the module under a production package name.  The verifier
    # files themselves use only stdlib and NumPy.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise V023FinalVerificationError(f"independent verifier import failed: {target}") from error
    return module


def _read_manifest(path: Path) -> tuple[dict[str, Any], str]:
    manifest_path = Path(path)
    payload = _read_json(manifest_path, label="source manifest")
    declared = _digest(payload.get("source_manifest_sha256"), label="source_manifest_sha256")
    unsigned = dict(payload)
    unsigned.pop("source_manifest_sha256", None)
    unsigned.pop("manifest_sha256", None)
    if canonical_sha256(unsigned) != declared:
        raise V023FinalVerificationError("source manifest body seal disagrees")
    manifest_seal = _digest(payload.get("manifest_sha256"), label="manifest_sha256")
    body = dict(payload)
    body.pop("manifest_sha256", None)
    if canonical_sha256(body) != manifest_seal:
        raise V023FinalVerificationError("source manifest seal disagrees")
    if payload.get("worlds") != list(V023_GATE_WORLDS) or payload.get("split") != "TRAIN_DEVELOPMENT":
        raise V023FinalVerificationError("source manifest world/split panel drifted")
    if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
        raise V023FinalVerificationError("source manifest crossed a closed boundary")
    if payload.get("contract_sha256") != V023_CONTRACT_SHA256 or payload.get("learner_update") is not False:
        raise V023FinalVerificationError("source manifest authority/boundary drifted")
    expected_shards = [
        {"world": world, "relative_name": f"source/world-{world}.json"}
        for world in V023_GATE_WORLDS
    ]
    if payload.get("source_count") != len(expected_shards) or payload.get("shards") != expected_shards:
        raise V023FinalVerificationError("source manifest shard schedule drifted")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(expected_shards):
        raise V023FinalVerificationError("source manifest entries are incomplete")
    for entry, expected in zip(entries, expected_shards, strict=True):
        item = _mapping(entry, label="source manifest entry")
        if item.get("world") != expected["world"] or item.get("relative_name") != expected["relative_name"]:
            raise V023FinalVerificationError("source manifest entry schedule drifted")
        declared_file = _digest(item.get("sha256"), label="source manifest entry sha256")
        bound_path = _safe_child(manifest_path.parent, item.get("relative_name"), label="source manifest entry")
        if file_sha256(bound_path) != declared_file:
            raise V023FinalVerificationError("source manifest entry byte hash disagrees")
    return payload, declared


def _source_raw_identity(source_paths: Sequence[Path]) -> dict[int, tuple[dict[str, Any], dict[str, np.ndarray]]]:
    result: dict[int, tuple[dict[str, Any], dict[str, np.ndarray]]] = {}
    for path in source_paths:
        payload = _read_json(Path(path), label=f"source {path}")
        _verify_seal(payload, label=f"source {path}")
        world = payload.get("world")
        if type(world) is not int or world not in V023_GATE_WORLDS or world in result:
            raise V023FinalVerificationError("source world panel is not exact and unique")
        arrays = _load_npz(Path(path).parent, _mapping(payload.get("arrays"), label="source arrays"), label=f"source {world}")
        result[world] = (payload, arrays)
    if set(result) != set(V023_GATE_WORLDS):
        raise V023FinalVerificationError("source panel is not the exact eight worlds")
    return result


def _verify_composition_shard(path: Path) -> _CompositionShard:
    payload = _read_json(path, label=f"composition {path}")
    _verify_seal(payload, label=f"composition {path}")
    if payload.get("schema") != V023_COMPOSITION_SCHEMA or payload.get("status") != "PASS_COMPOSITION_EVIDENCE":
        raise V023FinalVerificationError("composition schema/status drifted")
    if payload.get("claim_ceiling") != V023_COMPOSITION_CLAIM or payload.get("contract_sha256") != V023_CONTRACT_SHA256:
        raise V023FinalVerificationError("composition authority drifted")
    if payload.get("split") != "TRAIN_DEVELOPMENT" or payload.get("test_split_opened") is not False or payload.get("episode_training") is not False or payload.get("learner_update") is not False or payload.get("scientific_decision_opened") is not False or payload.get("c3_decision") is not None:
        raise V023FinalVerificationError("composition crossed a closed boundary")
    world, seed, arm = payload.get("held_out_world"), payload.get("student_seed"), payload.get("arm")
    if type(world) is not int or world not in V023_GATE_WORLDS or type(seed) is not int or seed not in V023_STUDENT_SEEDS or arm not in V023_FIT_ARMS:
        raise V023FinalVerificationError("composition identity is outside the frozen panel")
    arrays = _load_npz(Path(path).parent, _mapping(payload.get("arrays"), label="composition arrays"), label=f"composition {world}/{seed}/{arm}")
    required = {
        "anchor_phase", "anchor_id", "anchor_predecision_sha256", "anchor_state_schema_sha256", "anchor_state_sha256",
        "anchor_q12_snapshot_sha256", "anchor_q12_model_sha256", "anchor_q12_source_state_sha256", "anchor_q12_event_sha256",
        "anchor_view_sha256", "anchor_topology_sha256", "anchor_reference_actions_sha256", "q1", "q2", "q12", "q3",
        "teacher_q3", "action_mask", "physical_keys", "baseline_actions", "learned_actions", "teacher_actions",
        "baseline_exact_tie_count", "learned_exact_tie_count", "teacher_exact_tie_count", "physical_role", "physical_actions",
        "physical_action_sha256", "physical_draw_index", "physical_total_bits", "physical_per_user_bits", "physical_energy_j",
        "physical_served", "physical_served_count", "physical_service_denominator", "physical_active_beam_counts", "physical_active_beam_keys",
        "physical_beam_power_w", "physical_active_satellite_counts", "physical_active_satellites", "physical_common_field_digest",
        "physical_nonmutation_name", "physical_nonmutation_before_sha256", "physical_nonmutation_after_sha256", "physical_nonmutation_flags",
        "physical_ratio_cross_product_vs_b", "physical_ratio_cross_product_tolerance", "physical_ratio_direction_vs_b",
        "pair_anchor_index", "pair_id", "pair_member_users", "pair_designated_actions", "pair_source_key", "pair_destination_keys",
        "pair_profile_actions", "pair_profile_bits", "pair_profile_energy_j", "pair_profile_served", "pair_common_field_digest",
        "learned_pair_class", "teacher_pair_class", "pair_action_change", "pair_literal_11", "pair_harmful_partial_evaluated", "pair_harmful_partial",
        "pair_partial_ratio_cross_product", "pair_partial_ratio_tolerance", "pair_partial_ratio_direction", "pair_topology_evaluated",
        "pair_topology_consistent", "pair_selected_source_empty", "pair_destination_persist_by_nonmember", "pair_collateral_changed_count",
        "pair_collateral_denominator", "pair_profile_served_count", "pair_profile_service_denominator", "pair_collateral_changed_by_user", "full_roster_learned_action_changed", "full_roster_teacher_action_changed",
    }
    missing = sorted(required - set(arrays))
    if missing:
        raise V023FinalVerificationError("composition NPZ omits required arrays: " + ", ".join(missing))
    _validate_composition_arrays(payload, arrays, world=int(world), seed=int(seed), arm=str(arm))
    return _CompositionShard(Path(path), payload, arrays, int(world), int(seed), str(arm))


def _validate_composition_arrays(payload: Mapping[str, Any], arrays: Mapping[str, np.ndarray], *, world: int, seed: int, arm: str) -> None:
    phases = np.asarray(arrays["anchor_phase"])
    if phases.dtype != np.dtype("<i8") or phases.shape != (9,) or not np.array_equal(phases, np.arange(1, 10, dtype=np.int64)):
        raise V023FinalVerificationError("composition anchor phase schedule drifted")
    users = int(np.asarray(arrays["baseline_actions"]).shape[1]) if np.asarray(arrays["baseline_actions"]).ndim == 2 else -1
    if users <= 0 or users > 10000:
        raise V023FinalVerificationError("composition roster size is malformed")
    def shape(name: str, expected: tuple[int, ...], dtype: np.dtype | str | None = None) -> np.ndarray:
        value = np.asarray(arrays[name])
        if value.shape != expected or (dtype is not None and value.dtype != np.dtype(dtype)):
            raise V023FinalVerificationError(f"composition {name} shape/dtype drifted")
        return value
    anchor_ids = shape("anchor_id", (9,))
    if anchor_ids.dtype.kind != "S" or len({_decode_ascii(v, label="anchor id") for v in anchor_ids}) != 9:
        raise V023FinalVerificationError("composition anchor IDs are not unique ASCII")
    for name in ("anchor_predecision_sha256", "anchor_state_schema_sha256", "anchor_state_sha256", "anchor_q12_snapshot_sha256", "anchor_q12_model_sha256", "anchor_q12_source_state_sha256", "anchor_q12_event_sha256", "anchor_view_sha256", "anchor_topology_sha256", "anchor_reference_actions_sha256"):
        value = shape(name, (9,))
        if value.dtype.kind != "S":
            raise V023FinalVerificationError(f"composition {name} is not fixed-width ASCII")
        for item in value.tolist():
            _digest(_decode_ascii(item, label=name), label=name)
    q1 = shape("q1", (9, users, V023_ACTION_COUNT), np.float32)
    q2 = shape("q2", q1.shape, np.float32)
    q12 = shape("q12", q1.shape, np.float32)
    q3 = shape("q3", q1.shape, np.float32)
    teacher_q3 = shape("teacher_q3", q1.shape, np.float32)
    for name, value in (("q1", q1), ("q2", q2), ("q12", q12), ("q3", q3), ("teacher_q3", teacher_q3)):
        if not np.all(np.isfinite(value)):
            raise V023FinalVerificationError(f"composition {name} contains non-finite values")
    _assert_equal(q12, np.asarray(q1 + q2, dtype=np.float32), label="composition Q1+Q2")
    mask = shape("action_mask", q1.shape, np.bool_)
    if not np.all(np.any(mask, axis=2)):
        raise V023FinalVerificationError("composition action mask has an empty row")
    reference = shape("baseline_actions", (9, users), np.int64)
    learned = shape("learned_actions", (9, users), np.int64)
    teacher = shape("teacher_actions", (9, users), np.int64)
    physical_keys = shape("physical_keys", (9, users, V023_ACTION_COUNT, 2), np.int64)
    if np.any(physical_keys[~mask] != -1):
        raise V023FinalVerificationError("composition illegal physical-key cells are not -1 padded")
    for anchor in range(9):
        for user in range(users):
            legal_keys = physical_keys[anchor, user, mask[anchor, user]]
            if np.any(legal_keys < 0) or len({tuple(int(value) for value in row) for row in legal_keys.tolist()}) != legal_keys.shape[0]:
                raise V023FinalVerificationError("composition legal physical keys are malformed or repeated")
    for name, actions in (("baseline_actions", reference), ("learned_actions", learned), ("teacher_actions", teacher)):
        if np.any(actions < 0) or np.any(actions >= V023_ACTION_COUNT):
            raise V023FinalVerificationError(f"composition {name} contains an out-of-range action")
        if np.any(~mask[np.arange(9)[:, None], np.arange(users)[None, :], actions]):
            raise V023FinalVerificationError(f"composition {name} contains an illegal action")
    ties = {
        "baseline_exact_tie_count": shape("baseline_exact_tie_count", (9, users), np.int64),
        "learned_exact_tie_count": shape("learned_exact_tie_count", (9, users), np.int64),
        "teacher_exact_tie_count": shape("teacher_exact_tie_count", (9, users), np.int64),
    }
    scores = {"baseline": q12, "learned": np.asarray(q12 + q3, dtype=np.float32), "teacher": np.asarray(q12 + teacher_q3, dtype=np.float32)}
    for key, actions in (("baseline", reference), ("learned", learned), ("teacher", teacher)):
        tie = ties[f"{key}_exact_tie_count"]
        if np.any(tie < 1):
            raise V023FinalVerificationError(f"composition {key} tie denominator is invalid")
        expected = np.zeros_like(tie)
        for a in range(9):
            for user in range(users):
                selected = int(actions[a, user])
                expected[a, user] = int(np.count_nonzero(mask[a, user] & (scores[key][a, user] == scores[key][a, user, selected])))
        _assert_equal(tie, expected, label=f"composition {key} exact-tie count")
    physical_actions = shape("physical_actions", (9, 3, users), np.int64)
    _assert_equal(physical_actions[:, 0], reference, label="composition B actions")
    _assert_equal(physical_actions[:, 1], learned, label="composition learned actions")
    _assert_equal(physical_actions[:, 2], teacher, label="composition teacher actions")
    _assert_equal(
        arrays["full_roster_learned_action_changed"],
        learned != reference,
        label="composition learned action-change sidecar",
    )
    _assert_equal(
        arrays["full_roster_teacher_action_changed"],
        teacher != reference,
        label="composition teacher action-change sidecar",
    )
    draw_index = shape("physical_draw_index", (9, 3, V023_DRAW_COUNT), np.int64)
    if not np.all(draw_index == np.arange(V023_DRAW_COUNT, dtype=np.int64)[None, None, :]):
        raise V023FinalVerificationError("composition draw identity is not exactly 0..31")
    physical_total = shape("physical_total_bits", (9, 3, V023_DRAW_COUNT), np.float64)
    physical_bits = shape("physical_per_user_bits", (9, 3, V023_DRAW_COUNT, users), np.float64)
    physical_energy = shape("physical_energy_j", (9, 3, V023_DRAW_COUNT), np.float64)
    physical_served = shape("physical_served", (9, 3, V023_DRAW_COUNT, users), np.bool_)
    for name, value in (("physical_total_bits", physical_total), ("physical_per_user_bits", physical_bits), ("physical_energy_j", physical_energy)):
        if not np.all(np.isfinite(value)):
            raise V023FinalVerificationError(f"composition {name} contains non-finite values")
    if np.any(physical_bits < 0.0) or np.any(physical_energy <= 0.0):
        raise V023FinalVerificationError("composition physical bits/energy domain failed")
    _assert_equal(physical_total, np.sum(physical_bits, axis=3, dtype=np.float64), label="composition total bits")
    names = shape("physical_nonmutation_name", (np.asarray(arrays["physical_nonmutation_name"]).size,))
    if names.dtype.kind != "S":
        raise V023FinalVerificationError("composition nonmutation names are malformed")
    nonmutation_names = tuple(_decode_ascii(v, label="nonmutation name") for v in names.tolist())
    if len(set(nonmutation_names)) != len(nonmutation_names) or not V023_REQUIRED_NONMUTATION.issubset(nonmutation_names):
        raise V023FinalVerificationError("composition nonmutation names omit frozen fields")
    n = len(nonmutation_names)
    before = shape("physical_nonmutation_before_sha256", (9, 3, V023_DRAW_COUNT, n))
    after = shape("physical_nonmutation_after_sha256", before.shape)
    flags = shape("physical_nonmutation_flags", before.shape, np.bool_)
    if before.dtype.kind != "S" or after.dtype.kind != "S":
        raise V023FinalVerificationError("composition nonmutation digest arrays are malformed")
    for digest in np.concatenate((before.reshape(-1), after.reshape(-1))):
        _digest(_decode_ascii(digest, label="nonmutation digest"), label="nonmutation digest")
    _assert_equal(flags, before == after, label="composition nonmutation flags")
    if not np.all(flags):
        raise V023FinalVerificationError("composition physical evaluation mutated frozen state")
    common = shape("physical_common_field_digest", (9, 3, V023_DRAW_COUNT))
    if common.dtype.kind != "S":
        raise V023FinalVerificationError("composition common field digest array malformed")
    for a in range(9):
        for d in range(V023_DRAW_COUNT):
            values = tuple(_decode_ascii(common[a, role, d], label="common field digest") for role in range(3))
            if len(set(values)) != 1:
                raise V023FinalVerificationError("composition arms do not share the matched common field")
    beam_counts = shape("physical_active_beam_counts", (9, 3, V023_DRAW_COUNT), np.int64)
    beam_keys = np.asarray(arrays["physical_active_beam_keys"])
    beam_power = np.asarray(arrays["physical_beam_power_w"])
    satellite_counts = shape("physical_active_satellite_counts", (9, 3, V023_DRAW_COUNT), np.int64)
    satellites = np.asarray(arrays["physical_active_satellites"])
    if beam_keys.dtype != np.dtype("<i8") or beam_keys.ndim != 5 or beam_keys.shape[:3] != (9, 3, V023_DRAW_COUNT) or beam_keys.shape[-1] != 2:
        raise V023FinalVerificationError("composition active-beam keys are malformed")
    if beam_power.dtype != np.dtype("<f8") or beam_power.shape != beam_keys.shape[:-1] or np.any(~np.isfinite(beam_power)) or np.any(beam_power < 0.0):
        raise V023FinalVerificationError("composition beam-power array is malformed")
    if satellites.dtype != np.dtype("<i8") or satellites.ndim != 4 or satellites.shape[:3] != (9, 3, V023_DRAW_COUNT):
        raise V023FinalVerificationError("composition active-satellite array is malformed")
    if np.any(beam_counts < 0) or np.any(beam_counts > beam_keys.shape[3]) or np.any(satellite_counts < 0) or np.any(satellite_counts > satellites.shape[3]):
        raise V023FinalVerificationError("composition active-set count exceeds padding")
    for anchor in range(9):
        for role in range(3):
            for draw in range(V023_DRAW_COUNT):
                beam_count = int(beam_counts[anchor, role, draw])
                sat_count = int(satellite_counts[anchor, role, draw])
                if np.any(beam_keys[anchor, role, draw, beam_count:] != -1) or np.any(beam_power[anchor, role, draw, beam_count:] != 0.0):
                    raise V023FinalVerificationError("composition active-beam padding sentinel drifted")
                if np.any(satellites[anchor, role, draw, sat_count:] != -1):
                    raise V023FinalVerificationError("composition active-satellite padding sentinel drifted")
                valid_beams = beam_keys[anchor, role, draw, :beam_count]
                valid_sats = satellites[anchor, role, draw, :sat_count]
                if valid_beams.size and (np.any(valid_beams < 0) or len({tuple(int(value) for value in row) for row in valid_beams.tolist()}) != beam_count):
                    raise V023FinalVerificationError("composition active beam keys are repeated or negative")
                if valid_sats.size and (np.any(valid_sats < 0) or len(set(int(value) for value in valid_sats.tolist())) != sat_count):
                    raise V023FinalVerificationError("composition active satellite IDs are repeated or negative")
    action_hash = shape("physical_action_sha256", (9, 3))
    if action_hash.dtype.kind != "S":
        raise V023FinalVerificationError("composition action digest array malformed")
    for a in range(9):
        for role in range(3):
            _digest(_decode_ascii(action_hash[a, role], label="action digest"), label="action digest")
            expected = _profile_action_sha256(physical_actions[a, role])
            if _decode_ascii(action_hash[a, role], label="action digest") != expected:
                raise V023FinalVerificationError("composition action digest disagrees")
    served_count = shape("physical_served_count", (9, 3), np.int64)
    service_denominator = shape("physical_service_denominator", (9, 3), np.int64)
    _assert_equal(served_count, np.count_nonzero(physical_served, axis=(2, 3)).astype(np.int64), label="composition served count")
    if np.any(service_denominator != V023_DRAW_COUNT * users):
        raise V023FinalVerificationError("composition service denominator drifted")
    _validate_ratio_arrays(arrays, physical_total, physical_energy)
    _validate_pair_arrays(arrays, reference, learned, physical_keys, users)
    declared_roles = [_decode_ascii(value, label="physical role") for value in np.asarray(arrays["physical_role"]).tolist()]
    if tuple(declared_roles) != ("ZERO_SURFACE_B", arm, "TEACHER_ORACLE"):
        raise V023FinalVerificationError("composition physical role order drifted")
    denom = _mapping(payload.get("denominators"), label="composition denominators")
    pair_count = int(np.asarray(arrays["pair_anchor_index"]).size)
    if denom.get("pair_total") != pair_count or denom.get("action_change") != pair_count or denom.get("literal_11") != pair_count:
        raise V023FinalVerificationError("composition pair denominator drifted")


def _validate_ratio_arrays(arrays: Mapping[str, np.ndarray], total: np.ndarray, energy: np.ndarray) -> None:
    stored_cross = np.asarray(arrays["physical_ratio_cross_product_vs_b"], dtype=np.float64)
    stored_tol = np.asarray(arrays["physical_ratio_cross_product_tolerance"], dtype=np.float64)
    stored_direction = np.asarray(arrays["physical_ratio_direction_vs_b"], dtype=np.int8)
    if stored_cross.shape != (9, 3) or stored_tol.shape != stored_cross.shape or stored_direction.shape != stored_cross.shape:
        raise V023FinalVerificationError("composition physical ratio arrays are malformed")
    base_bits = np.sum(total[:, 0], axis=1, dtype=np.float64)
    base_energy = np.sum(energy[:, 0], axis=1, dtype=np.float64)
    for a in range(9):
        for role in range(3):
            left = float(np.sum(total[a, role], dtype=np.float64) * base_energy[a])
            right = float(base_bits[a] * np.sum(energy[a, role], dtype=np.float64))
            tolerance = _comparison_tolerance(left, right)
            if stored_cross[a, role] != left - right or stored_tol[a, role] != tolerance:
                raise V023FinalVerificationError("composition ratio cross-product/tolerance disagrees")
            expected = strict_direction(left, right)
            if int(stored_direction[a, role]) != expected:
                raise V023FinalVerificationError("composition ratio direction disagrees")


def _validate_pair_arrays(arrays: Mapping[str, np.ndarray], reference: np.ndarray, learned: np.ndarray, physical_keys: np.ndarray, users: int) -> None:
    pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
    pair_ids = np.asarray(arrays["pair_id"])
    pair_users = np.asarray(arrays["pair_member_users"], dtype=np.int64)
    designated = np.asarray(arrays["pair_designated_actions"], dtype=np.int64)
    source_keys = np.asarray(arrays["pair_source_key"], dtype=np.int64)
    destination_keys = np.asarray(arrays["pair_destination_keys"], dtype=np.int64)
    pair_count = pair_anchor.size
    if pair_ids.dtype.kind != "S" or pair_ids.shape != (pair_count,) or len({_decode_ascii(v, label="pair id") for v in pair_ids.tolist()}) != pair_count:
        raise V023FinalVerificationError("composition pair IDs are not unique")
    if pair_users.shape != (pair_count, 2) or designated.shape != pair_users.shape or source_keys.shape != (pair_count, 2) or destination_keys.shape != (pair_count, 2, 2):
        raise V023FinalVerificationError("composition pair identity shapes drifted")
    if np.any(designated < 0) or np.any(designated >= V023_ACTION_COUNT) or np.any(source_keys < 0) or np.any(destination_keys < 0):
        raise V023FinalVerificationError("composition pair identity contains out-of-range actions or keys")
    profile_bits = np.asarray(arrays["pair_profile_bits"], dtype=np.float64)
    profile_energy = np.asarray(arrays["pair_profile_energy_j"], dtype=np.float64)
    profile_actions = np.asarray(arrays["pair_profile_actions"], dtype=np.int64)
    profile_served = np.asarray(arrays["pair_profile_served"], dtype=np.bool_)
    if profile_actions.shape != (pair_count, V023_DRAW_COUNT, 4, users) or profile_bits.shape != profile_actions.shape or profile_energy.shape != (pair_count, V023_DRAW_COUNT, 4) or profile_served.shape != profile_actions.shape:
        raise V023FinalVerificationError("composition pair profile shapes drifted")
    if np.any(profile_actions < 0) or np.any(profile_actions >= V023_ACTION_COUNT) or not np.all(np.isfinite(profile_bits)) or np.any(profile_bits < 0.0) or not np.all(np.isfinite(profile_energy)) or np.any(profile_energy <= 0.0):
        raise V023FinalVerificationError("composition pair profile physical domain failed")
    served_count = np.asarray(arrays["pair_profile_served_count"], dtype=np.int64)
    service_denominator = np.asarray(arrays["pair_profile_service_denominator"], dtype=np.int64)
    collateral_by_user = np.asarray(arrays["pair_collateral_changed_by_user"], dtype=np.bool_)
    if served_count.shape != (pair_count, 4) or service_denominator.shape != (pair_count, 4) or collateral_by_user.shape != (pair_count, users):
        raise V023FinalVerificationError("composition pair service/collateral shapes drifted")
    _assert_equal(served_count, np.count_nonzero(profile_served, axis=(1, 3)).astype(np.int64), label="composition pair served count")
    if np.any(service_denominator != V023_DRAW_COUNT * users):
        raise V023FinalVerificationError("composition pair service denominator drifted")
    values = {name: np.asarray(arrays[name]) for name in ("learned_pair_class", "teacher_pair_class", "pair_action_change", "pair_literal_11", "pair_harmful_partial_evaluated", "pair_harmful_partial", "pair_partial_ratio_cross_product", "pair_partial_ratio_tolerance", "pair_partial_ratio_direction", "pair_topology_evaluated", "pair_topology_consistent", "pair_selected_source_empty", "pair_destination_persist_by_nonmember", "pair_collateral_changed_count", "pair_collateral_denominator")}
    for name, value in values.items():
        expected_shape = (pair_count, 2) if name == "pair_destination_persist_by_nonmember" else (pair_count,)
        if value.shape != expected_shape:
            raise V023FinalVerificationError(f"composition {name} shape drifted")
    for p in range(pair_count):
        anchor = int(pair_anchor[p])
        if not 0 <= anchor < 9 or np.any(pair_users[p] < 0) or np.any(pair_users[p] >= users) or pair_users[p, 0] == pair_users[p, 1]:
            raise V023FinalVerificationError("composition pair identity is malformed")
        members = pair_users[p]
        selected = learned[anchor, members]
        base = reference[anchor, members]
        des = designated[p]
        expected_source_keys = physical_keys[anchor, members, reference[anchor, members]]
        if not np.all(expected_source_keys == source_keys[p][None, :]) or not np.array_equal(physical_keys[anchor, members, des], destination_keys[p]):
            raise V023FinalVerificationError("composition pair physical key identity disagrees")
        expected_profiles = np.tile(reference[anchor], (4, 1))
        expected_profiles[1, int(members[0])] = int(des[0])
        expected_profiles[2, int(members[1])] = int(des[1])
        expected_profiles[3, members] = des
        if not np.array_equal(profile_actions[p], expected_profiles[None, :, :]):
            raise V023FinalVerificationError("composition pair profile actions disagree")
        first_base, second_base = bool(selected[0] == base[0]), bool(selected[1] == base[1])
        first_des, second_des = bool(selected[0] == des[0]), bool(selected[1] == des[1])
        if first_base and second_base:
            class_code = 0
        elif first_des and second_base:
            class_code = 1
        elif first_base and second_des:
            class_code = 2
        elif first_des and second_des:
            class_code = 3
        else:
            class_code = 4
        if int(values["learned_pair_class"][p]) != class_code:
            raise V023FinalVerificationError("composition pair class disagrees with selected actions")
        if "teacher_pair_class" in values and values["teacher_pair_class"].shape == (pair_count,):
            teacher_selected = np.asarray(arrays["teacher_actions"], dtype=np.int64)[anchor, members]
            teacher_base = base
            teacher_first_base, teacher_second_base = bool(teacher_selected[0] == teacher_base[0]), bool(teacher_selected[1] == teacher_base[1])
            teacher_first_des, teacher_second_des = bool(teacher_selected[0] == des[0]), bool(teacher_selected[1] == des[1])
            if teacher_first_base and teacher_second_base:
                teacher_class_code = 0
            elif teacher_first_des and teacher_second_base:
                teacher_class_code = 1
            elif teacher_first_base and teacher_second_des:
                teacher_class_code = 2
            elif teacher_first_des and teacher_second_des:
                teacher_class_code = 3
            else:
                teacher_class_code = 4
            if int(values["teacher_pair_class"][p]) != teacher_class_code:
                raise V023FinalVerificationError("composition teacher pair class disagrees with selected actions")
        action_change = bool(np.any(selected != base))
        literal = class_code == 3
        if bool(values["pair_action_change"][p]) != action_change or bool(values["pair_literal_11"][p]) != literal:
            raise V023FinalVerificationError("composition pair action predicates disagree")
        partial = class_code in (1, 2)
        if bool(values["pair_harmful_partial_evaluated"][p]) != partial:
            raise V023FinalVerificationError("composition partial denominator disagrees")
        partial_cross = float(values["pair_partial_ratio_cross_product"][p])
        partial_tol = float(values["pair_partial_ratio_tolerance"][p])
        if partial:
            profile = class_code
            b0 = float(np.sum(profile_bits[p, :, 0], dtype=np.float64))
            e0 = float(np.sum(profile_energy[p, :, 0], dtype=np.float64))
            bp = float(np.sum(profile_bits[p, :, profile], dtype=np.float64))
            ep = float(np.sum(profile_energy[p, :, profile], dtype=np.float64))
            expected_cross = bp * e0 - b0 * ep
            expected_tol = _comparison_tolerance(bp * e0, b0 * ep)
            expected_dir = strict_direction(bp * e0, b0 * ep)
        else:
            expected_cross, expected_tol, expected_dir = 0.0, 0.0, 0
        if partial_cross != expected_cross or partial_tol != expected_tol:
            raise V023FinalVerificationError("composition partial ratio evidence disagrees")
        if int(values["pair_partial_ratio_direction"][p]) != expected_dir:
            raise V023FinalVerificationError("composition partial ratio direction disagrees")
        if bool(values["pair_harmful_partial"][p]) != bool(partial and expected_dir < 0):
            raise V023FinalVerificationError("composition harmful-partial predicate disagrees")
        selected_keys = physical_keys[anchor, np.arange(users), learned[anchor]]
        source = source_keys[p]
        source_empty = not bool(np.any(np.all(selected_keys == source[None, :], axis=1)))
        nonmembers = np.ones(users, dtype=np.bool_)
        nonmembers[members] = False
        nonmember_keys = selected_keys[nonmembers]
        persist = np.asarray([bool(np.any(np.all(nonmember_keys == dest[None, :], axis=1))) for dest in destination_keys[p]], dtype=np.bool_)
        topology_eval = literal
        topology = bool(topology_eval and source_empty and np.all(persist))
        collateral = int(np.count_nonzero(learned[anchor, nonmembers] != reference[anchor, nonmembers]))
        expected_collateral_by_user = np.zeros(users, dtype=np.bool_)
        expected_collateral_by_user[nonmembers] = learned[anchor, nonmembers] != reference[anchor, nonmembers]
        if not np.array_equal(collateral_by_user[p], expected_collateral_by_user):
            raise V023FinalVerificationError("composition collateral-by-user predicate disagrees")
        if bool(values["pair_topology_evaluated"][p]) != topology_eval or bool(values["pair_topology_consistent"][p]) != topology or bool(values["pair_selected_source_empty"][p]) != source_empty or not np.array_equal(values["pair_destination_persist_by_nonmember"][p], persist) or int(values["pair_collateral_changed_count"][p]) != collateral or int(values["pair_collateral_denominator"][p]) != users - 2:
            raise V023FinalVerificationError("composition topology/collateral predicates disagree")


def _join_composition_source(shard: _CompositionShard, source: tuple[dict[str, Any], dict[str, np.ndarray]]) -> None:
    payload, arrays = source
    c = shard.arrays
    if shard.payload.get("preflight_manifest_sha256") != payload.get("preflight_manifest_sha256"):
        raise V023FinalVerificationError("composition/source preflight identity disagrees")
    for name in ("reference_actions", "action_mask", "physical_keys"):
        source_name = {"reference_actions": "reference_actions", "action_mask": "action_mask", "physical_keys": "physical_keys"}[name]
        comp_name = {"reference_actions": "baseline_actions", "action_mask": "action_mask", "physical_keys": "physical_keys"}[name]
        expected = np.asarray(arrays[source_name])
        actual = np.asarray(c[comp_name])
        if name == "reference_actions" and actual.shape != (9, expected.shape[1]):
            raise V023FinalVerificationError("composition/source roster shape disagrees")
        if name == "physical_keys" and actual.shape != expected.shape:
            raise V023FinalVerificationError("composition/source physical-key shape disagrees")
        _assert_equal(actual, expected, label=f"composition/source {name}")
    source_q1 = np.asarray(arrays["q1_values"], dtype=np.float32)
    source_q2 = np.asarray(arrays["q2_values"], dtype=np.float32)
    source_q12 = np.asarray(arrays["q12_values"], dtype=np.float32)
    _assert_equal(c["q1"], source_q1, label="composition/source Q1")
    _assert_equal(c["q2"], source_q2, label="composition/source Q2")
    _assert_equal(c["q12"], source_q12, label="composition/source Q1+Q2")
    for field in ("anchor_id", "anchor_predecision_sha256", "anchor_state_schema_sha256", "anchor_state_sha256", "anchor_q12_snapshot_sha256", "anchor_q12_model_sha256", "anchor_q12_source_state_sha256", "anchor_q12_event_sha256", "anchor_view_sha256", "anchor_topology_sha256", "anchor_reference_actions_sha256"):
        for index in range(9):
            source_entry = _mapping(payload["anchors"][index], label="source anchor")
            if field == "anchor_id":
                expected = str(source_entry.get("anchor_id"))
            else:
                source_field = field.removeprefix("anchor_")
                if field == "anchor_view_sha256":
                    expected = _decode_ascii(arrays["anchor_view_content_digest"][index], label="source view digest")
                elif field == "anchor_topology_sha256":
                    expected = _decode_ascii(arrays["anchor_topology_content_digest"][index], label="source topology digest")
                else:
                    expected = str(source_entry.get(source_field))
            actual = _decode_ascii(c[field][index], label=f"composition {field}")
            if actual != expected:
                raise V023FinalVerificationError(f"composition/source {field} disagrees")
    source_pair_ids = np.asarray(arrays["pair_id"])
    comp_pair_ids = np.asarray(c["pair_id"])
    if source_pair_ids.shape != comp_pair_ids.shape or not np.array_equal(source_pair_ids, comp_pair_ids):
        raise V023FinalVerificationError("composition/source pair ID panel disagrees")
    for name in ("pair_anchor_index", "pair_user_ids", "pair_action_ids", "pair_source_key", "pair_destination_keys", "pair_target_by_draw", "pair_profile_actions", "pair_profile_bits", "pair_profile_energy_j", "pair_profile_served", "common_field_digest"):
        if name == "common_field_digest":
            source_name, comp_name = "common_field_digest", "pair_common_field_digest"
        elif name == "pair_user_ids":
            source_name, comp_name = "pair_user_ids", "pair_member_users"
        elif name == "pair_action_ids":
            source_name, comp_name = "pair_action_ids", "pair_designated_actions"
        elif name in {"pair_source_key", "pair_destination_keys"}:
            source_name, comp_name = name, name
        elif name == "pair_profile_actions":
            source_name, comp_name = "profile_actions", name
        elif name == "pair_profile_bits":
            source_name, comp_name = "profile_bits", name
        elif name == "pair_profile_energy_j":
            source_name, comp_name = "profile_energy_j", name
        elif name == "pair_profile_served":
            source_name, comp_name = "profile_served", name
        else:
            source_name, comp_name = name, name
        if source_name not in arrays or comp_name not in c:
            raise V023FinalVerificationError(f"composition/source identity array missing: {name}")
        expected = np.asarray(arrays[source_name])
        if name in {"pair_profile_actions", "pair_profile_bits", "pair_profile_energy_j", "pair_profile_served", "common_field_digest"}:
            pair_count = int(np.asarray(arrays["pair_anchor_index"]).size)
            draw_pair = np.asarray(arrays["draw_pair_index"], dtype=np.int64)
            draw_index = np.asarray(arrays["draw_index"], dtype=np.int64)
            if draw_pair.shape != (pair_count * V023_DRAW_COUNT,) or draw_index.shape != draw_pair.shape:
                raise V023FinalVerificationError("source pair/draw identity is unavailable for composition join")
            order = {(int(p), int(d)): i for i, (p, d) in enumerate(zip(draw_pair.tolist(), draw_index.tolist(), strict=True))}
            if len(order) != pair_count * V023_DRAW_COUNT:
                raise V023FinalVerificationError("source pair/draw identity is not unique")
            rows = [order[(p, d)] for p in range(pair_count) for d in range(V023_DRAW_COUNT)]
            expected = expected[np.asarray(rows, dtype=np.int64)]
            expected = expected.reshape((pair_count, V023_DRAW_COUNT, *expected.shape[1:]))
        _assert_equal(c[comp_name], expected, label=f"composition/source {name}")


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


def tie_aware_spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    if a.ndim != 1 or b.shape != a.shape or a.size < 2 or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        return None
    ra, rb = _midranks(a), _midranks(b)
    ra -= np.mean(ra)
    rb -= np.mean(rb)
    denom = math.sqrt(float(np.dot(ra, ra)) * float(np.dot(rb, rb)))
    return None if denom == 0.0 or not math.isfinite(denom) else float(np.dot(ra, rb) / denom)


def _context_status(source_payloads: Mapping[int, tuple[dict[str, Any], dict[str, np.ndarray]]]) -> tuple[str, dict[str, Any]]:
    """Recompute the independent C1/C2 context diagnostics.

    C1 is reconstructed from the raw unilateral profile rows.  C2 is checked
    from the target-free OPS-3 surfaces, masks, persistence rows, and the
    serialized per-pair provenance flags.  A missing or non-recomputable C2
    field is an integrity gap, not a weak scientific result; the caller must
    therefore reject the final panel before emitting a scientific token.
    """
    c1_truth: list[float] = []
    c1_pred: list[float] = []
    c2_delta: list[float] = []
    c2_target_delta: list[float] = []
    c2_complete = True
    c2_gaps: list[str] = []
    c2_checks: dict[str, int] = {
        "opening_feasibility": 0,
        "absorbing_persistence": 0,
        "terminal_zero": 0,
        "frozen_background": 0,
        "target_free": 0,
    }
    for world in V023_GATE_WORLDS:
        payload, arrays = source_payloads[world]
        reference_raw = np.asarray(arrays["reference_actions"])
        mask_raw = np.asarray(arrays["action_mask"])
        opening_raw = np.asarray(arrays["opening_feasibility"])
        reference = np.asarray(reference_raw, dtype=np.int64)
        mask = np.asarray(mask_raw, dtype=np.bool_)
        opening = np.asarray(opening_raw, dtype=np.bool_)
        q1 = np.asarray(arrays["q1_values"], dtype=np.float64)
        q2 = np.asarray(arrays["q2_values"], dtype=np.float64)
        q12 = np.asarray(arrays["q12_values"], dtype=np.float64)
        q2_state = np.asarray(arrays.get("q2_state_matrix"), dtype=np.float32)
        q2_features = np.asarray(arrays.get("q2_feature_surface"), dtype=np.float64)
        q2_teacher = np.asarray(arrays.get("q2_teacher_values"), dtype=np.float64)
        q2_persistence = np.asarray(arrays.get("q2_persistence"), dtype=np.float64)
        q2_rate = np.asarray(arrays.get("q2_rate_bps"), dtype=np.float64)
        q2_power = np.asarray(arrays.get("q2_marginal_power_w"), dtype=np.float64)
        q2_required = np.asarray(arrays.get("q2_required_power_w"), dtype=np.float64)
        q2_horizon = np.asarray(arrays.get("q2_horizon"), dtype=np.int64)
        retained = np.asarray(arrays["pair_retained"], dtype=np.bool_)
        pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
        pair_users = np.asarray(arrays["pair_user_ids"], dtype=np.int64)
        pair_actions = np.asarray(arrays["pair_action_ids"], dtype=np.int64)
        anchors = payload.get("anchors")
        if not isinstance(anchors, list) or len(anchors) != len(V023_PHASES):
            raise V023FinalVerificationError("source anchor diagnostics are missing")
        if reference_raw.dtype != np.dtype("<i8") or mask_raw.dtype != np.bool_ or opening_raw.dtype != np.bool_ or reference.ndim != 2 or mask.shape != (reference.shape[0], reference.shape[1], V023_ACTION_COUNT) or opening.shape != mask.shape or q1.shape != mask.shape or q2.shape != mask.shape or q12.shape != mask.shape or not np.all(np.isfinite(q1)) or not np.all(np.isfinite(q2)) or not np.all(np.isfinite(q12)):
            raise V023FinalVerificationError("source C2 mask/opening surface shape drifted")
        anchor_count, users = reference.shape
        expected_q12 = _validated_q12(q1, q2, q12)
        expected_q2_shapes = {
            "q2_state_matrix": (anchor_count, users, V023_Q2_STATE_DIM),
            "q2_feature_surface": (anchor_count, users, V023_ACTION_COUNT, V023_Q2_FEATURE_DIM),
            "q2_teacher_values": (anchor_count, users, V023_ACTION_COUNT),
            "q2_persistence": (anchor_count, users, V023_OPS3_HORIZON, V023_ACTION_COUNT),
            "q2_rate_bps": (anchor_count, users, V023_OPS3_HORIZON, V023_ACTION_COUNT),
            "q2_marginal_power_w": (anchor_count, users, V023_OPS3_HORIZON, V023_ACTION_COUNT),
            "q2_required_power_w": (anchor_count, users, V023_OPS3_HORIZON, V023_ACTION_COUNT),
            "q2_horizon": (anchor_count,),
        }
        q2_arrays = {
            "q2_state_matrix": q2_state,
            "q2_feature_surface": q2_features,
            "q2_teacher_values": q2_teacher,
            "q2_persistence": q2_persistence,
            "q2_rate_bps": q2_rate,
            "q2_marginal_power_w": q2_power,
            "q2_required_power_w": q2_required,
            "q2_horizon": q2_horizon,
        }
        for name, value in q2_arrays.items():
            if value.shape != expected_q2_shapes[name] or not np.all(np.isfinite(value)):
                c2_complete = False
                c2_gaps.append(f"world={world}: {name} is absent, malformed, or nonfinite")
        if q2_state.shape == expected_q2_shapes["q2_state_matrix"]:
            expected_state = q2_features.astype(np.float32).transpose(0, 1, 3, 2).reshape(anchor_count, users, V023_Q2_STATE_DIM)
            if not np.array_equal(q2_state, expected_state):
                c2_complete = False
                c2_gaps.append(f"world={world}: q2 state is not the feature-major target-free surface")
        q1_reference = _q1_masked_argmax(q1.reshape(anchor_count, users, V023_ACTION_COUNT), mask)
        q12_reference = _q12_masked_argmax(
            expected_q12.reshape(
                anchor_count, users, V023_ACTION_COUNT
            ),
            mask,
        )
        if not np.array_equal(reference, q12_reference):
            raise V023FinalVerificationError(
                "source reference_actions is not native masked argmax(Q1+Q2 float32)"
            )
        if (
            retained.shape != pair_anchor.shape
            or pair_users.shape != (pair_anchor.size, 2)
            or pair_actions.shape != (pair_anchor.size, 2)
            or np.any(pair_anchor < 0)
            or np.any(pair_anchor >= anchor_count)
        ):
            raise V023FinalVerificationError("source C2 pair identity shape drifted")
        if q2_horizon.shape == (anchor_count,):
            for anchor in range(anchor_count):
                h = int(q2_horizon[anchor])
                expected_h = min(V023_OPS3_HORIZON, max(0, 9 - (anchor + 1)))
                if h != expected_h:
                    c2_complete = False
                    c2_gaps.append(
                        f"world={world},phase={anchor+1}: horizon does not match phase schedule"
                    )
                    continue
                c2_checks["opening_feasibility"] += 1
                persistence = q2_persistence[anchor]
                if np.any((persistence != 0.0) & (persistence != 1.0)) or np.any(np.diff(persistence, axis=1) > 0.0):
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={anchor+1}: persistence is not absorbing")
                else:
                    c2_checks["absorbing_persistence"] += 1
                if (
                    np.any(q2_rate[anchor] < 0.0)
                    or np.any(q2_power[anchor] < 0.0)
                    or np.any(q2_required[anchor] < 0.0)
                ):
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={anchor+1}: projected physics is negative")
                if h > 0 and np.any(persistence[:, 0, :] > opening[anchor]):
                    c2_complete = False
                    c2_gaps.append(
                        f"world={world},phase={anchor+1}: persistence bypasses opening feasibility"
                    )
                if h < V023_OPS3_HORIZON and any(np.any(value[anchor, :, h:] != 0.0) for value in (q2_persistence, q2_rate, q2_power, q2_required)):
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={anchor+1}: OPS-3 values leak beyond horizon")
                elif h < V023_OPS3_HORIZON:
                    c2_checks["terminal_zero"] += 1
                if h == 0 and (np.any(q2_features[anchor] != 0.0) or np.any(q2_teacher[anchor] != 0.0)):
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={anchor+1}: terminal Q2 surface is not zero")
                elif h == 0:
                    c2_checks["terminal_zero"] += 1
                expected_target = _recompute_ops3_target(
                    q2_persistence[anchor],
                    q2_rate[anchor],
                    q2_power[anchor],
                    q1_reference=q1_reference[anchor],
                    mask=mask[anchor],
                    horizon=h,
                )
                _assert_numeric_equal(q2_teacher[anchor], expected_target, label=f"world={world},phase={anchor+1} repriced OPS-3 target")
                c2_checks["frozen_background"] += 1
                for user in range(users):
                    if int(q12_reference[anchor, user]) != int(reference[anchor, user]):
                        # This is redundant with the panel-level check above,
                        # but keep it anchor-local so a future partial source
                        # cannot hide which background row drifted.
                        c2_complete = False
                        c2_gaps.append(
                            f"world={world},phase={anchor+1}: Q1+Q2 reference drifted"
                        )
                    if not bool(mask[anchor, user, int(q12_reference[anchor, user])]):
                        c2_complete = False
                        c2_gaps.append(f"world={world},phase={anchor+1}: Q1+Q2 reference is masked")
                    if np.any(q2_teacher[anchor, user, ~mask[anchor, user]] != 0.0):
                        c2_complete = False
                        c2_gaps.append(f"world={world},phase={anchor+1}: masked Q2 target is nonzero")
        for index, entry_raw in enumerate(anchors):
            entry = _mapping(entry_raw, label="source anchor diagnostic")
            q2_context = _mapping(entry.get("q2_context"), label="source q2 context")
            if q2_context.get("schema") != "multi-catfish-mcrl-v023-q2-context-v1" or q2_context.get("q2_state_schema") != V023_Q2_STATE_SCHEMA or q2_context.get("q2_state_schema_sha256") != V023_Q2_STATE_SCHEMA_SHA256:
                c2_complete = False
                c2_gaps.append(f"world={world},phase={index+1}: Q2 context provenance is missing")
            else:
                c2_checks["target_free"] += 1
            if q2_horizon.shape == (anchor_count,) and q2_horizon[index] != q2_context.get("horizon"):
                c2_complete = False
                c2_gaps.append(f"world={world},phase={index+1}: serialized Q2 horizon disagrees")
            if q2_state.shape == expected_q2_shapes["q2_state_matrix"]:
                try:
                    _verify_q2_state_digest_receipt(
                        q2_context,
                        q2_state[index],
                        mask[index],
                        label=f"world={world},phase={index+1}",
                    )
                except V023FinalVerificationError as error:
                    c2_complete = False
                    c2_gaps.append(str(error))
            if q1.shape == reference.shape and q1_reference.shape == reference.shape:
                q1_reference_digest = _array_digest(q1_reference[index], domain="v023-q1-reference-actions")
                q12_reference_digest = _array_digest(q12_reference[index], domain="v023-reference-actions")
                if q2_context.get("q1_reference_actions_sha256") != q1_reference_digest or q2_context.get("q12_reference_actions_sha256") != q12_reference_digest:
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={index+1}: Q1/Q12 reference digest disagrees")
            for field, value, domain in (
                ("target_values_sha256", q2_teacher[index], "v023-repriced-ops3-target-values"),
                ("feature_surface_sha256", q2_features[index], "v023-ops3-feature-surface"),
                ("persistence_sha256", q2_persistence[index], "v023-ops3-persistence"),
            ):
                declared = q2_context.get(field)
                if not isinstance(declared, str) or declared != _array_digest(value, domain=domain):
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={index+1}: Q2 {field} disagrees")
            try:
                _verify_q2_timing(
                    q2_context,
                    phase=index + 1,
                    horizon=int(q2_horizon[index]),
                    label=f"world={world},phase={index+1}",
                )
            except V023FinalVerificationError as error:
                c2_complete = False
                c2_gaps.append(str(error))
            try:
                diag, rows = _diagnostic_rows(
                    entry.get("c2_diagnostic"),
                    label=f"world={world},phase={index+1}",
                )
            except V023FinalVerificationError as error:
                c2_complete = False
                c2_gaps.append(str(error))
                continue
            if (
                diag.get("kind") != "C2_REPRICED_OPS3_CONTEXT_DIAGNOSTIC"
                or diag.get("target_filter_applied") is not False
                or diag.get("target_free_inference") is not True
                or diag.get("runtime_default_lambda_used_for_target") is not False
                or diag.get("diagnostic_lambda_bits_per_j_hex")
                != V023_LAMBDA_BITS_PER_J.hex()
            ):
                c2_complete = False
                c2_gaps.append(f"world={world},phase={index+1}: C2 target-free/multiplier receipt drifted")
            expected_rows: dict[tuple[tuple[int, int], tuple[int, int]], int] = {}
            for pair in np.flatnonzero((pair_anchor == index) & retained):
                key = (
                    tuple(int(value) for value in pair_users[pair]),
                    tuple(int(value) for value in pair_actions[pair]),
                )
                if key in expected_rows:
                    raise V023FinalVerificationError(
                        f"world={world},phase={index+1}: C2 pair identity repeats"
                    )
                expected_rows[key] = int(pair)
            seen_rows: set[tuple[tuple[int, int], tuple[int, int]]] = set()
            if len(rows) != len(expected_rows):
                c2_complete = False
                c2_gaps.append(
                    f"world={world},phase={index+1}: C2 row count disagrees with retained pairs"
                )
            for row_raw in rows:
                row = _mapping(row_raw, label="source C2 diagnostic row")
                if row.get("row_granularity") != "ONE_PER_RETAINED_PAIR_MEMBER_NOT_PER_DRAW":
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={index+1}: C2 row granularity drifted")
                    continue
                user_values = row.get("user_ids")
                candidate_values = row.get("candidate_actions")
                reference_values = row.get("reference_actions")
                q2_values = row.get("q2_delta")
                target_values = row.get("ops3_target_delta")
                transition_values = row.get("transition_class")
                if not all(
                    isinstance(value, list) and len(value) == 2
                    for value in (
                        user_values,
                        candidate_values,
                        reference_values,
                        q2_values,
                        target_values,
                        transition_values,
                    )
                ):
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={index+1}: C2 row fields are malformed")
                    continue
                try:
                    users_row = tuple(int(value) for value in user_values)
                    actions_row = tuple(int(value) for value in candidate_values)
                except (TypeError, ValueError, OverflowError) as error:
                    raise V023FinalVerificationError(
                        f"world={world},phase={index+1}: C2 row identity is malformed"
                    ) from error
                key = (users_row, actions_row)
                if key in seen_rows or key not in expected_rows:
                    c2_complete = False
                    c2_gaps.append(f"world={world},phase={index+1}: C2 row identity disagrees")
                    continue
                seen_rows.add(key)
                expected_pair = expected_rows[key]
                expected_refs = tuple(
                    int(q12_reference[index, user]) for user in users_row
                )
                if tuple(int(value) for value in reference_values) != expected_refs:
                    c2_complete = False
                    c2_gaps.append(
                        f"world={world},phase={index+1}: C2 row reference is not native Q1+Q2"
                    )
                expected_q2_delta = np.asarray(
                    [
                        q2[index, user, action] - q2[index, user, reference]
                        for user, action, reference in zip(
                            users_row, actions_row, expected_refs, strict=True
                        )
                    ],
                    dtype=np.float64,
                )
                expected_target_delta = np.asarray(
                    [
                        q2_teacher[index, user, action]
                        - q2_teacher[index, user, reference]
                        for user, action, reference in zip(
                            users_row, actions_row, expected_refs, strict=True
                        )
                    ],
                    dtype=np.float64,
                )
                try:
                    _assert_numeric_equal(
                        q2_values,
                        expected_q2_delta,
                        label=f"world={world},phase={index+1} C2 q2 delta",
                    )
                    _assert_numeric_equal(
                        target_values,
                        expected_target_delta,
                        label=f"world={world},phase={index+1} C2 target delta",
                    )
                except V023FinalVerificationError as error:
                    c2_complete = False
                    c2_gaps.append(str(error))
                expected_transition = tuple(
                    _transition_class(
                        np.asarray(arrays["physical_keys"])[index],
                        user=user,
                        reference=reference,
                        candidate=action,
                    )
                    for user, action, reference in zip(
                        users_row, actions_row, expected_refs, strict=True
                    )
                )
                if tuple(str(value) for value in transition_values) != expected_transition:
                    c2_complete = False
                    c2_gaps.append(
                        f"world={world},phase={index+1}: C2 transition class disagrees"
                    )
            if seen_rows != set(expected_rows):
                c2_complete = False
                c2_gaps.append(f"world={world},phase={index+1}: C2 rows are incomplete")
        retained = np.asarray(arrays["pair_retained"], dtype=np.bool_)
        pair_anchor = np.asarray(arrays["pair_anchor_index"], dtype=np.int64)
        pair_users = np.asarray(arrays["pair_user_ids"], dtype=np.int64)
        pair_actions = np.asarray(arrays["pair_action_ids"], dtype=np.int64)
        profile_bits = np.asarray(arrays["profile_bits"], dtype=np.float64)
        profile_energy = np.asarray(arrays["profile_energy_j"], dtype=np.float64)
        draw_pair = np.asarray(arrays["draw_pair_index"], dtype=np.int64)
        draw_index = np.asarray(arrays["draw_index"], dtype=np.int64)
        for pair in np.flatnonzero(retained):
            users_pair = pair_users[pair]
            rows = np.flatnonzero(draw_pair == pair)
            if rows.size != V023_DRAW_COUNT or set(draw_index[rows].tolist()) != set(range(V023_DRAW_COUNT)):
                raise V023FinalVerificationError("source C1/C2 draw identity is incomplete")
            for member in range(2):
                user, action = int(users_pair[member]), int(pair_actions[pair, member])
                anchor = int(pair_anchor[pair])
                ref = int(reference[anchor, user])
                profile = member + 1
                own = (profile_bits[rows, profile, user] - profile_bits[rows, 0, user]) - V023_LAMBDA_BITS_PER_J * (profile_energy[rows, profile] - profile_energy[rows, 0])
                c1_truth.append(float(np.mean(own, dtype=np.float64) / V023_KAPPA_BITS))
                c1_pred.append(float(q1[anchor, user, action] - q1[anchor, user, ref]))
                c2_reference = int(q12_reference[anchor, user])
                c2_delta.append(float(q2[anchor, user, action] - q2[anchor, user, c2_reference]))
                c2_target_delta.append(
                    float(
                        q2_teacher[anchor, user, action]
                        - q2_teacher[anchor, user, c2_reference]
                    )
                )
    c1_target = np.asarray(c1_truth, dtype=np.float64)
    c1_prediction = np.asarray(c1_pred, dtype=np.float64)
    nontrivial = np.abs(c1_target) >= V023_SIGN_THRESHOLD
    c1_sign = None if not np.any(nontrivial) else float(np.mean(np.sign(c1_prediction[nontrivial]) == np.sign(c1_target[nontrivial])))
    c1_rho = tie_aware_spearman(c1_prediction, c1_target)
    c1_pass = c1_rho is not None and c1_rho >= 0.20 and int(np.count_nonzero(nontrivial)) >= 24 and c1_sign is not None and c1_sign >= 0.55
    c2_values = np.asarray(c2_delta, dtype=np.float64)
    c2_targets = np.asarray(c2_target_delta, dtype=np.float64)
    c2_exposure = None if c2_values.size == 0 else float(np.mean(np.abs(c2_values) >= V023_SIGN_THRESHOLD))
    c2_target_sign, c2_target_rank, c2_target_nontrivial_count = _target_sign_rank(
        c2_values, c2_targets
    )
    c2_pass = c2_complete and c2_exposure is not None and c2_exposure >= 0.10
    if c1_pass and c2_pass:
        status = "CONTEXT_DIAGNOSTICS_PASS"
    elif c1_pass:
        status = "HOLD_C2"
    elif c2_pass:
        status = "HOLD_C1"
    else:
        status = "HOLD_C1_C2"
    return status, {
        "c1": {"rows": int(c1_target.size), "nontrivial_rows": int(np.count_nonzero(nontrivial)), "spearman": c1_rho, "sign_accuracy": c1_sign, "passes": bool(c1_pass)},
        "c2": {"rows": int(c2_values.size), "nontrivial_rows": int(np.count_nonzero(np.abs(c2_values) >= V023_SIGN_THRESHOLD)), "exposure": c2_exposure, "target_nontrivial_rows": c2_target_nontrivial_count, "target_sign_accuracy": c2_target_sign, "target_rank_spearman": c2_target_rank, "passes": bool(c2_pass), "schema_complete": bool(c2_complete), "checks": c2_checks, "gaps": c2_gaps},
        "recomputed_from_raw_arrays": True,
    }


def _fit_panel_metrics(reports: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    r7 = _load_independent(_R7_DECISION_PATH, "v023_final_r7_balanced_decision")
    expected = {
        (world, seed, arm)
        for world in V023_GATE_WORLDS
        for seed in V023_STUDENT_SEEDS
        for arm in V023_FIT_ARMS
    }
    by_key: dict[tuple[int, int, str], Mapping[str, Any]] = {}
    for report in reports:
        key = (
            int(report["held_out_world"]),
            int(report["student_seed"]),
            str(report["arm"]),
        )
        if key in by_key or key not in expected:
            raise V023FinalVerificationError(
                "fit panel has duplicate or out-of-panel identity"
            )
        by_key[key] = report
    if set(by_key) != expected:
        raise V023FinalVerificationError("fit panel is not exact 8 x 3 x 2")

    def row_identities(report: Mapping[str, Any]) -> list[tuple[int, str, int, int]]:
        raw = report.get("identity")
        if not isinstance(raw, list):
            raise V023FinalVerificationError("fit report lacks held-out row identities")
        try:
            return [
                (
                    int(item["world"]),
                    str(item["anchor"]),
                    int(item["user"]),
                    int(item["action"]),
                )
                for item in raw
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise V023FinalVerificationError(
                "fit held-out row identity is malformed"
            ) from error

    for world in V023_GATE_WORLDS:
        reference = by_key[(world, V023_STUDENT_SEEDS[0], "INFORMED")]
        reference_ids = row_identities(reference)
        reference_target = np.asarray(reference["target"], dtype=np.float64)
        if len(reference_ids) != reference_target.size:
            raise V023FinalVerificationError(
                "fit held-out identities and labels are not aligned"
            )
        for seed in V023_STUDENT_SEEDS:
            for arm in V023_FIT_ARMS:
                report = by_key[(world, seed, arm)]
                if row_identities(report) != reference_ids or not np.array_equal(
                    np.asarray(report["target"], dtype=np.float64), reference_target
                ):
                    raise V023FinalVerificationError(
                        "fit held-out identities/labels disagree across arms or seeds"
                    )
    shards = [
        r7.HeldOutShard(
            world=world,
            seed=seed,
            arm=arm,
            predictions=np.asarray(report["prediction"], dtype=np.float64),
            targets=np.asarray(report["target"], dtype=np.float64),
            spearman=report["spearman"],
        )
        for world in V023_GATE_WORLDS
        for seed in V023_STUDENT_SEEDS
        for arm in V023_FIT_ARMS
        for report in (by_key[(world, seed, arm)],)
    ]
    try:
        balanced = r7.evaluate_r7_panel(shards)
    except Exception as error:
        raise V023FinalVerificationError(
            f"R7 balanced learner panel failed closed: {error}"
        ) from error
    first_seed = V023_STUDENT_SEEDS[0]
    targets = np.concatenate(
        [
            np.asarray(
                next(
                    shard.targets
                    for shard in shards
                    if shard.world == world
                    and shard.seed == first_seed
                    and shard.arm == "INFORMED"
                ),
                dtype=np.float64,
            )
            for world in V023_GATE_WORLDS
        ]
    )
    target_support_count = int(
        np.count_nonzero(np.abs(targets) >= V023_SIGN_THRESHOLD)
    )
    predicates = dict(balanced["predicates"])
    predicates["target_support"] = target_support_count >= 24
    return {
        "status": "PASS_R7_BALANCED_FIT_PANEL_NUMERIC_RECOMPUTATION",
        "scientific_claim": False,
        "fit_count": len(shards),
        **balanced,
        "target_support_count": target_support_count,
        "predicates": predicates,
    }


def _composition_metrics(shards: Mapping[tuple[int, int, str], _CompositionShard]) -> dict[str, Any]:
    # All metrics are recomputed from raw physical arrays; no persisted
    # summary/boolean is used.
    arm_world: dict[tuple[int, str], list[_CompositionShard]] = {}
    for (world, seed, arm), shard in shards.items():
        arm_world.setdefault((world, arm), []).append(shard)
    def arm_value(world: int, seed: int, arm: str, role: int) -> tuple[float, float, float, float]:
        arr = shards[(world, seed, arm)].arrays
        total = np.asarray(arr["physical_total_bits"], dtype=np.float64)[:, role].sum(dtype=np.float64)
        energy = np.asarray(arr["physical_energy_j"], dtype=np.float64)[:, role].sum(dtype=np.float64)
        if not math.isfinite(float(total)) or not math.isfinite(float(energy)) or energy <= 0.0:
            raise V023FinalVerificationError("composition EE denominator is missing or nonpositive")
        served = np.asarray(arr["physical_served"], dtype=np.bool_)[:, role]
        return float(total / energy), float(total), float(energy), float(np.mean(served))
    world_values: dict[str, Any] = {}
    informed_learned: list[float] = []
    teacher_values: list[float] = []
    baseline_values: list[float] = []
    learned_world_positive = 0
    teacher_world_positive = 0
    for world in V023_GATE_WORLDS:
        w_entry: dict[str, Any] = {}
        for arm in V023_FIT_ARMS:
            seed_values = [arm_value(world, seed, arm, 1) for seed in V023_STUDENT_SEEDS]
            w_entry[arm] = {"seed_ee": [v[0] for v in seed_values], "seed_bits": [v[1] for v in seed_values], "seed_energy": [v[2] for v in seed_values], "seed_served": [v[3] for v in seed_values], "mean_ee": float(np.mean([v[0] for v in seed_values])), "mean_served": float(np.mean([v[3] for v in seed_values]))}
        b_values = [arm_value(world, seed, "INFORMED", 0) for seed in V023_STUDENT_SEEDS]
        t_values = [arm_value(world, seed, "INFORMED", 2) for seed in V023_STUDENT_SEEDS]
        baseline_ee = float(np.mean([v[0] for v in b_values]))
        teacher_ee = float(np.mean([v[0] for v in t_values]))
        learned_ee = float(w_entry["INFORMED"]["mean_ee"])
        teacher_world_positive += int(strict_direction(teacher_ee, baseline_ee) == 1)
        learned_world_positive += int(strict_direction(learned_ee, baseline_ee) == 1)
        baseline_values.append(baseline_ee)
        teacher_values.append(teacher_ee)
        informed_learned.append(learned_ee)
        w_entry["baseline_mean_ee"] = baseline_ee
        w_entry["teacher_strictly_above_baseline"] = bool(strict_direction(teacher_ee, baseline_ee) == 1)
        w_entry["learned_strictly_above_baseline"] = bool(strict_direction(learned_ee, baseline_ee) == 1)
        # Section 10 compares the learned INFORMED arm with B=Q1+Q2, not
        # with the placebo learner.  B is role 0 in every INFORMED shard.
        learned_served = float(np.mean([v[3] for v in [arm_value(world, seed, "INFORMED", 1) for seed in V023_STUDENT_SEEDS]]))
        baseline_served = float(np.mean([v[3] for v in b_values]))
        w_entry["baseline_mean_served"] = baseline_served
        w_entry["learned_mean_served"] = learned_served
        w_entry["service_guard"] = bool(learned_served >= baseline_served - V023_SERVICE_MARGIN)
        world_values[str(world)] = w_entry
    # Pair-level predicates use every declared INFORMED seed.  The same pair
    # identity is joined across seeds, but learned selections are intentionally
    # not assumed to be identical; seed pooling is therefore recomputed here.
    ref_pairs = [
        shards[(world, seed, "INFORMED")].arrays
        for world in V023_GATE_WORLDS
        for seed in V023_STUDENT_SEEDS
    ]
    all_action = np.concatenate([np.asarray(a["pair_action_change"], dtype=np.bool_) for a in ref_pairs])
    all_literal = np.concatenate([np.asarray(a["pair_literal_11"], dtype=np.bool_) for a in ref_pairs])
    all_harmful = np.concatenate([np.asarray(a["pair_harmful_partial"], dtype=np.bool_) for a in ref_pairs])
    all_selected_11 = all_literal
    all_topology = np.concatenate([np.asarray(a["pair_topology_consistent"], dtype=np.bool_) for a in ref_pairs])
    pair_total = int(all_action.size)
    topology_den = int(np.count_nonzero(all_selected_11))
    topology_num = int(np.count_nonzero(all_selected_11 & all_topology))
    topology_value = None if topology_den == 0 else topology_num / topology_den
    collat_denom = int(np.sum([np.sum(np.asarray(a["pair_collateral_denominator"], dtype=np.int64)) for a in ref_pairs], dtype=np.int64))
    collat_num = int(np.sum([np.sum(np.asarray(a["pair_collateral_changed_count"], dtype=np.int64)) for a in ref_pairs], dtype=np.int64))
    literal_worlds = sum(
        int(
            any(
                np.count_nonzero(np.asarray(shards[(world, seed, "INFORMED")].arrays["pair_literal_11"], dtype=np.bool_)) > 0
                for seed in V023_STUDENT_SEEDS
            )
        )
        for world in V023_GATE_WORLDS
    )
    composition_predicates = {"action_exposure": pair_total > 0 and float(np.mean(all_action)) >= 0.10, "literal_11": pair_total > 0 and float(np.mean(all_literal)) >= 0.25 and literal_worlds >= 4, "harmful_partial": pair_total > 0 and float(np.mean(all_harmful)) <= 0.05, "topology_consistency": topology_den > 0 and topology_value is not None and topology_value >= 0.80}
    # Pooled ratio-of-sums is computed per seed first, then averaged across
    # the three declared seeds.  Averaging world EE values would be a
    # different estimand and is forbidden by Section 12.
    pooled_by_role: dict[str, list[tuple[float, float, float]]] = {}
    for role_name, role_index in (("baseline", 0), ("learned", 1), ("teacher", 2)):
        seed_totals: list[tuple[float, float, float]] = []
        for seed in V023_STUDENT_SEEDS:
            bits = energy = served = 0.0
            for world in V023_GATE_WORLDS:
                ee, b, e, s = arm_value(world, seed, "INFORMED", role_index)
                bits += b
                energy += e
                served += s
            seed_totals.append((float(bits / energy), bits, energy))
        pooled_by_role[role_name] = seed_totals
    baseline_pooled = float(np.mean([v[0] for v in pooled_by_role["baseline"]]))
    teacher_pooled = float(np.mean([v[0] for v in pooled_by_role["teacher"]]))
    learned_pooled = float(np.mean([v[0] for v in pooled_by_role["learned"]]))
    physical_predicates = {"teacher_composition": strict_direction(teacher_pooled, baseline_pooled) == 1 and teacher_world_positive >= 4, "learned_composition": strict_direction(learned_pooled, baseline_pooled) == 1 and learned_world_positive >= 4, "service": all(bool(e["service_guard"]) for e in world_values.values())}
    return {"worlds": world_values, "physical": physical_predicates, "composition": composition_predicates, "pair_denominators": {"pair_total": pair_total, "selected_11": topology_den, "literal_worlds": literal_worlds, "topology_consistency": {"numerator": topology_num, "denominator": topology_den, "value": topology_value}, "collateral": {"numerator": collat_num, "denominator": collat_denom}}, "pooled": {"baseline_ee": baseline_pooled, "teacher_ee": teacher_pooled, "learned_ee": learned_pooled, "teacher_world_positive": teacher_world_positive, "learned_world_positive": learned_world_positive, "by_seed": pooled_by_role}}


def verify_cross_arm_identity(informed: _CompositionShard, placebo: _CompositionShard) -> None:
    """Require exact shared identity while permitting arm-local learned physics.

    Composition role order is ``(baseline, learned, teacher)``.  The
    ``MATCHED_PLACEBO`` arm is intentionally allowed to choose a different
    learned action, so its role-1 physical outcome can differ from the
    ``INFORMED`` arm.  Baseline (role 0) and teacher (role 2) remain the
    matched physical controls and must be byte-identical across arms.
    """
    if (informed.world, informed.seed) != (placebo.world, placebo.seed):
        raise V023FinalVerificationError("cross-arm world/seed identity disagrees")
    if informed.arm != "INFORMED" or placebo.arm != "MATCHED_PLACEBO":
        raise V023FinalVerificationError("cross-arm labels are not informed/placebo")
    # These arrays contain an explicit role axis at axis 1.  Only the shared
    # baseline and teacher surfaces are part of the cross-arm identity; role 1
    # is the arm's learned result and is expected to differ when the learners
    # select different actions.
    for name in (
        "physical_actions", "physical_total_bits", "physical_per_user_bits",
        "physical_energy_j", "physical_served",
    ):
        informed_value = np.asarray(informed.arrays[name])
        placebo_value = np.asarray(placebo.arrays[name])
        if informed_value.ndim < 2 or placebo_value.ndim < 2:
            raise V023FinalVerificationError(
                f"cross-arm {name} is missing its physical role axis"
            )
        if informed_value.shape[0] != placebo_value.shape[0] or informed_value.shape[1] < 3 or placebo_value.shape[1] < 3:
            raise V023FinalVerificationError(
                f"cross-arm {name} role surface shape disagrees"
            )
        _assert_equal(
            informed_value[:, (0, 2), ...],
            placebo_value[:, (0, 2), ...],
            label=f"cross-arm {name} baseline/teacher",
        )
    for name in (
        "anchor_id", "anchor_phase", "baseline_actions", "teacher_actions", "q1", "q2", "q12",
        "physical_common_field_digest", "pair_id", "pair_anchor_index",
        "pair_member_users", "pair_designated_actions", "pair_profile_actions", "pair_profile_bits",
        "pair_profile_energy_j", "pair_profile_served", "pair_common_field_digest",
    ):
        _assert_equal(informed.arrays[name], placebo.arrays[name], label=f"cross-arm {name}")


def adjudicate_section14(*, integrity: bool, pair_coverage: bool, mechanics: bool, physical_signature: bool, target_support: bool, held_out_learner: bool, world_stability: bool, action_exposure: bool, literal_11: bool, harmful_partial: bool, topology_consistency: bool, teacher_composition: bool, learned_composition: bool, service: bool) -> str:
    """Apply full Section 14 precedence through the R7 decision module."""

    r7 = _load_independent(_R7_DECISION_PATH, "v023_final_r7_section14")
    return str(
        r7.adjudicate_section14_r7(
            integrity=integrity,
            pair_coverage=pair_coverage,
            mechanics=mechanics,
            physical_signature=physical_signature,
            teacher_composition=teacher_composition,
            target_support=target_support,
            held_out_learner=held_out_learner,
            world_stability=world_stability,
            action_exposure=action_exposure,
            literal_11=literal_11,
            harmful_partial=harmful_partial,
            topology_consistency=topology_consistency,
            learned_composition=learned_composition,
            service=service,
        )
    )


def _invalid(reason: str, *, errors: Sequence[str] = ()) -> dict[str, Any]:
    return {"schema": "multi-catfish-mcrl-v023-lcsrs-r7-balanced-final-verification-v1", "status": "INVALID_RUN", "c3_decision": "INVALID_RUN", "scientific_claim": False, "claim_ceiling": V023_COMPOSITION_CLAIM, "context_status": None, "integrity_status": "INVALID", "errors": [reason, *errors], "no_scientific_token_before_integrity": True, "test_split_opened": False, "episode_training": False}


def verify_v023_final_gate(*, source_paths: Sequence[Path], fit_paths: Sequence[Path], composition_paths: Sequence[Path], source_manifest_path: Path | None = None, expected_preflight_manifest_sha256: str | None = None, expected_source_manifest_sha256: str | None = None, raise_on_invalid: bool = False) -> dict[str, Any]:
    """Verify exact V0.23 source/fit/composition panels and adjudicate once.

    The manifest path is mandatory because a fit receipt may not retroactively
    define its own input panel.  All paths are read-only.  ``raise_on_invalid``
    is useful to callers that want an exception, but the default receipt form
    is safer for a runner because it serializes ``INVALID_RUN`` explicitly.
    """
    try:
        if source_manifest_path is None:
            raise V023FinalVerificationError("authenticated source manifest is required")
        if len(source_paths) != 8 or len(fit_paths) != 48 or len(composition_paths) != 48:
            raise V023FinalVerificationError("final panel requires exactly 8 source, 48 fit, and 48 composition shards")
        manifest, source_manifest_sha = _read_manifest(Path(source_manifest_path))
        if expected_source_manifest_sha256 is not None and source_manifest_sha != _digest(expected_source_manifest_sha256, label="expected source manifest sha256"):
            raise V023FinalVerificationError("source manifest hash disagrees with caller")
        manifest_root = Path(source_manifest_path).parent.resolve()
        expected_source_paths = {
            world: (manifest_root / "source" / f"world-{world}.json").resolve()
            for world in V023_GATE_WORLDS
        }
        supplied_source_paths = {Path(path).resolve() for path in source_paths}
        if supplied_source_paths != set(expected_source_paths.values()):
            raise V023FinalVerificationError("supplied source paths do not exactly match the sealed manifest")
        ordered_source_paths = tuple(expected_source_paths[world] for world in V023_GATE_WORLDS)
        source_raw = _source_raw_identity(ordered_source_paths)
        source_path_by_world = {
            int(_read_json(Path(path), label=f"source {path}").get("world")): Path(path)
            for path in ordered_source_paths
        }
        scientific = _load_independent(_SCIENTIFIC_PATH, "v023_final_scientific")
        fit_independent = _load_independent(_FIT_INDEPENDENT_PATH, "v023_final_fit_independent")
        source_panel = scientific.verify_source_panel_science([Path(p) for p in ordered_source_paths])
        if source_panel.get("status") != "VERIFIED_SOURCE_PANEL_NUMERICS":
            raise V023FinalVerificationError("independent source panel did not verify")
        preflight_sha = str(source_panel["preflight_manifest_sha256"])
        _digest(preflight_sha, label="source preflight sha256")
        if expected_preflight_manifest_sha256 is not None and preflight_sha != _digest(expected_preflight_manifest_sha256, label="expected preflight sha256"):
            raise V023FinalVerificationError("source preflight hash disagrees with caller")
        fit_reports: list[Mapping[str, Any]] = []
        fit_scientific_reports: list[Mapping[str, Any]] = []
        for path in fit_paths:
            report = fit_independent.verify_v023_fit_artifact(Path(path), source_manifest_path=Path(source_manifest_path), source_index_paths=[Path(p) for p in ordered_source_paths], expected_source_manifest_sha256=source_manifest_sha, preflight_manifest_sha256=preflight_sha)
            fit_reports.append(report)
            fit_scientific_reports.append(scientific.verify_fit_science(Path(path)))
        fit_metrics = _fit_panel_metrics(fit_scientific_reports)
        fit_report_by_key = {
            (int(report["held_out_world"]), int(report["student_seed"]), str(report["arm"])): report
            for report in fit_reports
        }
        # The fit-side independent reports must agree on panel identity and arm
        # without trusting their success booleans.
        if {(int(r["held_out_world"]), int(r["student_seed"]), str(r["arm"])) for r in fit_reports} != {(w, s, a) for w in V023_GATE_WORLDS for s in V023_STUDENT_SEEDS for a in V023_FIT_ARMS}:
            raise V023FinalVerificationError("fit independent panel identity is incomplete")
        shard_list = [_verify_composition_shard(Path(path)) for path in composition_paths]
        comp_by_key: dict[tuple[int, int, str], _CompositionShard] = {}
        for shard in shard_list:
            key = (shard.world, shard.seed, shard.arm)
            if key in comp_by_key:
                raise V023FinalVerificationError("composition panel has duplicate identity")
            comp_by_key[key] = shard
            _join_composition_source(shard, source_raw[shard.world])
            if shard.payload.get("source_manifest_sha256") != source_manifest_sha or shard.payload.get("preflight_manifest_sha256") != preflight_sha:
                raise V023FinalVerificationError("composition source manifest/preflight binding disagrees")
            source_payload = source_raw[shard.world][0]
            source_index_sha = file_sha256(source_path_by_world[shard.world])
            if shard.payload.get("source_index_sha256") != source_index_sha:
                raise V023FinalVerificationError("composition/source index digest disagrees")
            if shard.payload.get("source_field_root_sha256") != source_payload.get("world_receipt", {}).get("field_root_digest"):
                raise V023FinalVerificationError("composition/source field-root digest disagrees")
            fit_path = next((Path(p) for p in fit_paths if _fit_identity(Path(p)) == key), None)
            if fit_path is None or shard.payload.get("fit_receipt_sha256") != file_sha256(fit_path):
                raise V023FinalVerificationError("composition/fit receipt identity disagrees")
            # The composition adapter calls this field
            # ``fit_receipt_content_sha256`` but stores the sealed fit
            # receipt's declared content digest (the top-level
            # ``receipt_sha256``), not the byte hash of the fit JSON.  Bind it
            # explicitly to the independently checked fit receipt rather than
            # trusting a copied composition scalar.
            fit_payload = _read_json(fit_path, label=f"fit {fit_path}")
            fit_content_sha = _digest(
                fit_payload.get("receipt_sha256"),
                label="fit receipt content sha256",
            )
            if shard.payload.get("fit_receipt_content_sha256") != fit_content_sha:
                raise V023FinalVerificationError(
                    "composition/fit receipt content digest disagrees"
                )
            fit_report = fit_report_by_key[key]
            model_report = _mapping(fit_report.get("model"), label="fit model report")
            if shard.payload.get("fit_model_bytes_sha256") != model_report.get("model_npz_sha256") or shard.payload.get("fit_model_sha256") != model_report.get("network_sha256"):
                raise V023FinalVerificationError("composition/fit model digest disagrees")
            if shard.payload.get("fit_update_count") != 2000 or shard.payload.get("fit_already_completed") is not True:
                raise V023FinalVerificationError("composition fit update provenance disagrees")
        expected_comp = {(w, s, a) for w in V023_GATE_WORLDS for s in V023_STUDENT_SEEDS for a in V023_FIT_ARMS}
        if set(comp_by_key) != expected_comp:
            raise V023FinalVerificationError("composition panel is not exact 8 x 3 x 2")
        # Informed and placebo must have one exact B/teacher surface and exact
        # anchor/draw identity.  Only their fitted Q3 arm is allowed to differ.
        for world in V023_GATE_WORLDS:
            for seed in V023_STUDENT_SEEDS:
                informed, placebo = comp_by_key[(world, seed, "INFORMED")], comp_by_key[(world, seed, "MATCHED_PLACEBO")]
                verify_cross_arm_identity(informed, placebo)
        comp_metrics = _composition_metrics(comp_by_key)
        context_status, context = _context_status(source_raw)
        if not bool(context["c2"]["schema_complete"]):
            gaps = context["c2"].get("gaps", [])
            raise V023FinalVerificationError(
                "C2 context diagnostics are not independently recomputable: "
                + "; ".join(str(item) for item in gaps[:8])
            )
        decision_predicates = {
            "pair_coverage": bool(source_panel["predicates"].get("pair_coverage")),
            "mechanics": bool(source_panel["predicates"].get("mechanics")),
            "physical_signature": bool(source_panel["predicates"].get("physical_signature")),
            "target_support": bool(fit_metrics["predicates"]["target_support"]),
            "held_out_learner": bool(fit_metrics["predicates"]["held_out_learner"]),
            "world_stability": bool(fit_metrics["predicates"]["world_stability"]),
            "action_exposure": bool(comp_metrics["composition"]["action_exposure"]),
            "literal_11": bool(comp_metrics["composition"]["literal_11"]),
            "harmful_partial": bool(comp_metrics["composition"]["harmful_partial"]),
            "topology_consistency": bool(comp_metrics["composition"]["topology_consistency"]),
            "teacher_composition": bool(comp_metrics["physical"]["teacher_composition"]),
            "learned_composition": bool(comp_metrics["physical"]["learned_composition"]),
            "service": bool(comp_metrics["physical"]["service"]),
        }
        decision = adjudicate_section14(integrity=True, **decision_predicates)
        predicates = {
            **decision_predicates,
            "finite_nonzero_class_denominators": bool(
                fit_metrics["predicates"]["finite_nonzero_class_denominators"]
            ),
            "pooled_class_support": bool(
                fit_metrics["predicates"]["pooled_class_support"]
            ),
            "raw_sign_accuracy_reported_nondecisive": bool(
                fit_metrics["predicates"]["raw_sign_accuracy_reported_nondecisive"]
            ),
        }
        return {"schema": "multi-catfish-mcrl-v023-lcsrs-r7-balanced-final-verification-v1", "status": "PASS_FINAL_INTEGRITY", "integrity_status": "VERIFIED", "scientific_claim": False, "claim_ceiling": V023_COMPOSITION_CLAIM, "contract_sha256": V023_CONTRACT_SHA256, "execution_addendum_sha256": V023_EXECUTION_ADDENDUM_SHA256, "preflight_manifest_sha256": preflight_sha, "source_manifest_sha256": source_manifest_sha, "source_count": 8, "fit_count": 48, "composition_count": 48, "context_status": context_status, "context": context, "source_panel": source_panel, "fit_panel": fit_metrics, "composition": comp_metrics, "predicates": predicates, "c3_decision": decision, "test_split_opened": False, "episode_training": False, "no_rescue": True, "no_scientific_token_before_integrity": True}
    except Exception as error:
        if raise_on_invalid:
            raise
        return _invalid(str(error))


def _fit_identity(path: Path) -> tuple[int, int, str]:
    payload = _read_json(path, label=f"fit {path}")
    return int(payload.get("held_out_world")), int(payload.get("student_seed")), str(payload.get("arm"))


verify_final_gate = verify_v023_final_gate


__all__ = [
    "V023FinalVerificationError",
    "canonical_sha256",
    "file_sha256",
    "strict_direction",
    "tie_aware_spearman",
    "verify_cross_arm_identity",
    "adjudicate_section14",
    "verify_v023_final_gate",
    "verify_final_gate",
]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs=8, type=Path, required=True)
    parser.add_argument("--fit", nargs=48, type=Path, required=True)
    parser.add_argument("--composition", nargs=48, type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify_v023_final_gate(source_paths=args.source, fit_paths=args.fit, composition_paths=args.composition, source_manifest_path=args.source_manifest)
    args.output.write_bytes(_canonical_bytes(result) + b"\n")
    print(result["c3_decision"])
