#!/usr/bin/env python3
"""Harvest V0.16-O origin-aware C3 source rows.

This module is the source-only boundary for the V0.16 C3 learnability gate.
It opens one declared TRAIN world and one frozen Q1/Q2 lineage, materialises
the three detached base-head contexts ``h=12, 1, 2`` at every predecision
anchor, and writes one compact row per ``(anchor, user, context)``.

The only environment action committed by :func:`harvest_source_shard` is the
full-context ``Q1 + learned-Q2`` background action.  The three C3 reference
passes are physics-only counterfactual measurements; they must leave the live
environment and RNG unchanged.  This command never trains a learner, opens
TEST, or evaluates a trajectory EE result.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any

import numpy as np


REPO = Path(__file__).resolve().parents[2]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    BEAM_POWER_MAX_W,
    SEGMENT_START_POWER_W,
    recurrence_power_w,
)
from mcrl.runtime.ee_axis_ops3 import (  # noqa: E402
    OPS3_KAPPA_BITS,
    opening_service_feasibility_surface,
)
from mcrl.runtime.ee_axis_zero_marginal_c3 import (  # noqa: E402
    assert_surface_identity,
    build_zr_surface,
)
from mcrl.runtime.ee_axis_v016_c3_origin_state import (  # noqa: E402
    V016_C3_ORIGIN_STATE_DIM,
    V016_C3_ORIGIN_STATE_SCHEMA,
    encode_ee_axis_v016_c3_origin_state,
)


SOURCE_SCHEMA = "multi-catfish-mcrl-v016-c3-origin-gate-source-v1"
SOURCE_SCHEMA_VERSION = 1
NPZ_FILENAME = "source.npz"
METADATA_FILENAME = "metadata.json"
SHA256_FILENAME = "source.sha256"
CONTRACT_PATH = (
    REPO
    / "artifacts"
    / "multi-catfish-v016-c3-origin-gate-20260903-r1"
    / "contracts"
    / "MULTI-CATFISH-MCRL-V016-C3-ORIGIN-GATE-PREREG-2026-09-03.md"
)
CONTRACT_SHA256 = (
    "4dfeb9154983ee12ec6690e61c92a19e6893b27c811b0b84352a5d52c28b6784"
)
CONTRACT_RECEIPT_PATH = CONTRACT_PATH.with_name("prereg.sha256")

TRAIN_WORLD_SEEDS = (
    2026111001,
    2026111002,
    2026111003,
    2026111004,
    2026111005,
    2026111006,
)
LINEAGES = (2026092101, 2026092102, 2026092103)
CONTEXT_CODES = (12, 1, 2)
USERS = 100
STEPS_PER_EPISODE = 10
ACTION_DIM = 28
# This component intentionally excludes lineage, policy, action, target, and
# outcome.  It is shared by all three lineages within one world and is not
# consumed by the source arrays or learner.
FIELD_COMPONENT = "MCRL_V016_C3_ORIGIN_GATE_V1"

ARRAY_NAMES = (
    "q3_states",
    "action_masks",
    "q1_values",
    "learned_q2_values",
    "z3_target_bits",
    "q3_compatibility",
    "context_codes",
    "reference_actions",
    "source_seeds",
    "lineages",
    "anchor_sha256s",
    "step_indices",
    "user_indices",
)


class V016OriginSourceError(ValueError):
    """A source shard violates the V0.16-O storage or causal boundary."""


def canonical_json_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V016OriginSourceError(
            "payload is not finite canonical JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V016OriginSourceError(f"expected a regular file: {source}")
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
        raise V016OriginSourceError(f"{field} must be lowercase SHA-256")
    return value


def _readonly(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise V016OriginSourceError(f"{field} has an invalid value") from error
    result.setflags(write=False)
    return result


def _finite_matrix(
    value: object,
    *,
    field: str,
    shape_tail: tuple[int, ...],
    dtype: np.dtype[Any],
) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise V016OriginSourceError(f"{field} is not an array") from error
    if raw.ndim != 1 + len(shape_tail) or raw.shape[1:] != shape_tail:
        raise V016OriginSourceError(
            f"{field} must have shape (N,{','.join(map(str, shape_tail))})"
        )
    result = _readonly(raw, dtype=dtype, field=field)
    if result.shape[0] < 1 or not np.all(np.isfinite(result)):
        raise V016OriginSourceError(f"{field} must be nonempty and finite")
    return result


def _integer_vector(
    value: object,
    *,
    field: str,
    allow_negative_one: bool = False,
) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise V016OriginSourceError(f"{field} is not an array") from error
    if raw.ndim != 1 or raw.dtype.kind not in "iu":
        raise V016OriginSourceError(
            f"{field} must be a one-dimensional integer vector"
        )
    result = _readonly(raw, dtype=np.dtype(np.int64), field=field)
    if allow_negative_one:
        if np.any(result < -1):
            raise V016OriginSourceError(f"{field} contains an invalid sentinel")
    elif np.any(result < 0):
        raise V016OriginSourceError(f"{field} must be nonnegative")
    return result


def _boolean_matrix(value: object, *, field: str) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise V016OriginSourceError(f"{field} is not an array") from error
    if raw.ndim != 2 or raw.shape[1:] != (ACTION_DIM,) or raw.dtype != np.bool_:
        raise V016OriginSourceError(
            f"{field} must be Boolean shape (N,{ACTION_DIM})"
        )
    return _readonly(raw, dtype=np.dtype(np.bool_), field=field)


def _anchor_vector(value: object, *, field: str) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise V016OriginSourceError(f"{field} is not an array") from error
    if raw.ndim != 1:
        raise V016OriginSourceError(f"{field} must be one-dimensional")
    decoded: list[str] = []
    for item in raw.tolist():
        if isinstance(item, bytes):
            try:
                text = item.decode("ascii")
            except UnicodeDecodeError as error:
                raise V016OriginSourceError(
                    f"{field} contains non-ASCII bytes"
                ) from error
        else:
            text = str(item)
        _digest(text, field=field)
        decoded.append(text)
    result = _readonly(np.asarray(decoded, dtype="S64"), dtype=np.dtype("S64"), field=field)
    return result


def _row_count(arrays: Mapping[str, np.ndarray]) -> int:
    if not arrays:
        raise V016OriginSourceError("source array set is empty")
    counts = {name: int(value.shape[0]) for name, value in arrays.items()}
    if len(set(counts.values())) != 1 or next(iter(counts.values())) < 1:
        raise V016OriginSourceError(f"source arrays disagree on row count: {counts}")
    return next(iter(counts.values()))


def _ordered_anchor_groups(
    *,
    context_codes: np.ndarray,
    source_seeds: np.ndarray,
    anchor_sha256s: np.ndarray,
    step_indices: np.ndarray,
    user_indices: np.ndarray,
) -> list[tuple[int, str, int]]:
    """Validate the deterministic anchor -> context -> user row order."""

    rows = int(context_codes.size)
    expected_group = np.concatenate(
        [np.full(USERS, code, dtype=np.int64) for code in CONTEXT_CODES]
    )
    expected_users = np.tile(np.arange(USERS, dtype=np.int64), len(CONTEXT_CODES))
    groups: list[tuple[int, str, int]] = []
    cursor = 0
    while cursor < rows:
        if cursor + expected_group.size > rows:
            raise V016OriginSourceError(
                "rows do not contain complete 12/1/2 context groups"
            )
        world = int(source_seeds[cursor])
        anchor = bytes(anchor_sha256s[cursor]).decode("ascii")
        step = int(step_indices[cursor])
        end = cursor + expected_group.size
        if not np.all(source_seeds[cursor:end] == world):
            raise V016OriginSourceError("one anchor group mixes world seeds")
        if not np.all(anchor_sha256s[cursor:end] == anchor.encode("ascii")):
            raise V016OriginSourceError("one anchor group mixes anchor digests")
        if not np.all(step_indices[cursor:end] == step):
            raise V016OriginSourceError("one anchor group mixes step indices")
        if not np.array_equal(context_codes[cursor:end], expected_group):
            raise V016OriginSourceError(
                "each anchor must be ordered by contexts h=12, h=1, h=2"
            )
        if not np.array_equal(user_indices[cursor:end], expected_users):
            raise V016OriginSourceError(
                "each context must be ordered by user index 0..U-1"
            )
        groups.append((world, anchor, step))
        cursor = end
    return groups


@dataclass(frozen=True)
class ReferenceSourceArrays:
    """Immutable one-row-per-user-anchor-context source representation."""

    q3_states: np.ndarray
    action_masks: np.ndarray
    q1_values: np.ndarray
    learned_q2_values: np.ndarray
    z3_target_bits: np.ndarray
    q3_compatibility: np.ndarray
    context_codes: np.ndarray
    reference_actions: np.ndarray
    source_seeds: np.ndarray
    lineages: np.ndarray
    anchor_sha256s: np.ndarray
    step_indices: np.ndarray
    user_indices: np.ndarray
    world_seed: int
    lineage: int
    field_root_digest: str
    kappa_bits: float
    # Frozen parameter receipts are shard-level provenance, not NPZ arrays.
    # They are populated by ``read_source_shard`` from metadata so the gate
    # loader can authenticate Q1/Q2 lineage pairing without opening a second
    # sidecar format.
    q1_checkpoint_sha256: str
    q2_checkpoint_sha256: str
    q1_parameter_sha256: str
    q2_parameter_sha256: str
    schema: str = SOURCE_SCHEMA

    def arrays_as_mapping(self) -> dict[str, np.ndarray]:
        return {name: np.asarray(getattr(self, name)) for name in ARRAY_NAMES}

    def arrays_sha256(self) -> str:
        return canonical_sha256(
            {name: _array_sha256(value) for name, value in self.arrays_as_mapping().items()}
        )

    @property
    def rows(self) -> int:
        return int(np.asarray(self.q3_states).shape[0])

    def observed_step_indices(self) -> tuple[int, ...]:
        """Return the contiguous zero-based steps represented by this shard."""

        values = tuple(
            sorted({int(value) for value in np.asarray(self.step_indices).tolist()})
        )
        if values != tuple(range(len(values))):
            raise V016OriginSourceError(
                "observed step indices must be contiguous starting at zero"
            )
        return values

    def verify(self) -> str:
        if self.schema != SOURCE_SCHEMA:
            raise V016OriginSourceError("source schema is stale")
        arrays = self.arrays_as_mapping()
        rows = _row_count(arrays)
        expected_shapes = {
            "q3_states": (rows, V016_C3_ORIGIN_STATE_DIM),
            "action_masks": (rows, ACTION_DIM),
            "q1_values": (rows, ACTION_DIM),
            "learned_q2_values": (rows, ACTION_DIM),
            "z3_target_bits": (rows, ACTION_DIM),
            "q3_compatibility": (rows, ACTION_DIM),
            "context_codes": (rows,),
            "reference_actions": (rows,),
            "source_seeds": (rows,),
            "lineages": (rows,),
            "anchor_sha256s": (rows,),
            "step_indices": (rows,),
            "user_indices": (rows,),
        }
        for name, shape in expected_shapes.items():
            if arrays[name].shape != shape:
                raise V016OriginSourceError(
                    f"{name} must have shape {shape}, got {arrays[name].shape}"
                )
        for name in (
            "q3_states",
            "q1_values",
            "learned_q2_values",
            "z3_target_bits",
        ):
            if not np.all(np.isfinite(arrays[name])):
                raise V016OriginSourceError(f"{name} must be finite")
        if arrays["q3_states"].dtype != np.float32:
            raise V016OriginSourceError("q3_states must be float32")
        if arrays["action_masks"].dtype != np.bool_ or arrays["q3_compatibility"].dtype != np.bool_:
            raise V016OriginSourceError("mask/compatibility arrays must be Boolean")
        for name in ("context_codes", "reference_actions", "source_seeds", "lineages", "step_indices", "user_indices"):
            if not np.issubdtype(arrays[name].dtype, np.integer):
                raise V016OriginSourceError(f"{name} must be an integer array")
        if not np.all(np.any(arrays["action_masks"], axis=1)):
            raise V016OriginSourceError(
                "source rows must have a legal native action for ZR measurement"
            )
        if np.any(~np.isin(arrays["context_codes"], CONTEXT_CODES)):
            raise V016OriginSourceError("context_codes must be exactly 12, 1, or 2")
        refs = arrays["reference_actions"]
        if np.any(refs < 0) or np.any(refs >= ACTION_DIM):
            raise V016OriginSourceError("reference_actions contain an illegal action")
        row_index = np.arange(rows, dtype=np.int64)
        if not np.all(arrays["action_masks"][row_index, refs]):
            raise V016OriginSourceError("reference_actions are not native legal")
        if np.any(arrays["z3_target_bits"][~arrays["action_masks"]] != 0.0):
            raise V016OriginSourceError("z3 target is nonzero outside the native mask")
        if np.any(arrays["z3_target_bits"][row_index, refs] != 0.0):
            raise V016OriginSourceError("ZR reference target is not exact zero")
        if np.any(arrays["q3_compatibility"][~arrays["action_masks"]]):
            raise V016OriginSourceError("compatibility is true outside the native mask")
        if not np.all(arrays["q3_compatibility"][row_index, refs]):
            raise V016OriginSourceError("every native reference must be compatible")
        seeds = arrays["source_seeds"]
        lineages = arrays["lineages"]
        if not np.all(seeds > 0) or not np.all(lineages > 0):
            raise V016OriginSourceError("source world/lineage identifiers must be positive")
        _anchor_vector(arrays["anchor_sha256s"], field="anchor_sha256s")
        if not np.all(arrays["step_indices"] < STEPS_PER_EPISODE):
            raise V016OriginSourceError("step_indices exceed the canonical ten-step episode")
        self.observed_step_indices()
        if not np.all(arrays["user_indices"] < USERS):
            raise V016OriginSourceError("user_indices exceed the declared user count")
        if not np.all(seeds == int(self.world_seed)):
            raise V016OriginSourceError("source_seeds disagree with world_seed metadata")
        if not np.all(lineages == int(self.lineage)):
            raise V016OriginSourceError("lineages disagree with shard lineage metadata")
        if int(self.world_seed) not in TRAIN_WORLD_SEEDS:
            raise V016OriginSourceError("world_seed is outside the V0.16-O TRAIN declaration")
        if int(self.lineage) not in LINEAGES:
            raise V016OriginSourceError("lineage is outside the frozen Q1/Q2 declaration")
        _digest(self.field_root_digest, field="field_root_digest")
        for name in (
            "q1_checkpoint_sha256",
            "q2_checkpoint_sha256",
            "q1_parameter_sha256",
            "q2_parameter_sha256",
        ):
            value = getattr(self, name)
            _digest(value, field=name)
        if not math.isfinite(float(self.kappa_bits)) or float(self.kappa_bits) <= 0.0:
            raise V016OriginSourceError("kappa_bits must be finite and positive")
        _ordered_anchor_groups(
            context_codes=arrays["context_codes"],
            source_seeds=seeds,
            anchor_sha256s=arrays["anchor_sha256s"],
            step_indices=arrays["step_indices"],
            user_indices=arrays["user_indices"],
        )
        for value in arrays.values():
            if value.flags.writeable:
                raise V016OriginSourceError("source arrays must be immutable")
        return self.arrays_sha256()


def assemble_source_arrays(
    *,
    q3_states: object,
    action_masks: object,
    q1_values: object,
    learned_q2_values: object,
    z3_target_bits: object,
    q3_compatibility: object,
    context_codes: object,
    reference_actions: object,
    source_seeds: object,
    lineages: object,
    anchor_sha256s: object,
    step_indices: object,
    user_indices: object,
    world_seed: int,
    lineage: int,
    field_root_digest: str,
    kappa_bits: float,
    q1_checkpoint_sha256: str,
    q2_checkpoint_sha256: str,
    q1_parameter_sha256: str,
    q2_parameter_sha256: str,
) -> ReferenceSourceArrays:
    """Construct and validate one immutable source shard."""

    source = ReferenceSourceArrays(
        q3_states=_finite_matrix(
            q3_states,
            field="q3_states",
            shape_tail=(V016_C3_ORIGIN_STATE_DIM,),
            dtype=np.dtype(np.float32),
        ),
        action_masks=_boolean_matrix(action_masks, field="action_masks"),
        q1_values=_finite_matrix(
            q1_values,
            field="q1_values",
            shape_tail=(ACTION_DIM,),
            dtype=np.dtype(np.float64),
        ),
        learned_q2_values=_finite_matrix(
            learned_q2_values,
            field="learned_q2_values",
            shape_tail=(ACTION_DIM,),
            dtype=np.dtype(np.float64),
        ),
        z3_target_bits=_finite_matrix(
            z3_target_bits,
            field="z3_target_bits",
            shape_tail=(ACTION_DIM,),
            dtype=np.dtype(np.float64),
        ),
        q3_compatibility=_boolean_matrix(
            q3_compatibility, field="q3_compatibility"
        ),
        context_codes=_integer_vector(context_codes, field="context_codes"),
        reference_actions=_integer_vector(
            reference_actions, field="reference_actions"
        ),
        source_seeds=_integer_vector(source_seeds, field="source_seeds"),
        lineages=_integer_vector(lineages, field="lineages"),
        anchor_sha256s=_anchor_vector(anchor_sha256s, field="anchor_sha256s"),
        step_indices=_integer_vector(step_indices, field="step_indices"),
        user_indices=_integer_vector(user_indices, field="user_indices"),
        world_seed=int(world_seed),
        lineage=int(lineage),
        field_root_digest=str(field_root_digest),
        kappa_bits=float(kappa_bits),
        q1_checkpoint_sha256=str(q1_checkpoint_sha256),
        q2_checkpoint_sha256=str(q2_checkpoint_sha256),
        q1_parameter_sha256=str(q1_parameter_sha256),
        q2_parameter_sha256=str(q2_parameter_sha256),
    )
    source.verify()
    return source


def validate_source_arrays(source: ReferenceSourceArrays) -> str:
    if not isinstance(source, ReferenceSourceArrays):
        raise V016OriginSourceError("source must be ReferenceSourceArrays")
    return source.verify()


def _write_once_bytes(path: Path, payload: bytes) -> None:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V016OriginSourceError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_name, destination)
    except FileExistsError as error:
        raise V016OriginSourceError(f"refusing to overwrite {destination}") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def write_source_shard(
    output_dir: str | Path,
    source: ReferenceSourceArrays,
    *,
    metadata_extra: Mapping[str, object] | None = None,
) -> dict[str, str]:
    """Write NPZ, metadata, and receipt exactly once."""

    validate_source_arrays(source)
    observed_steps = source.observed_step_indices()
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V016OriginSourceError(f"refusing to overwrite {output}")
    output.mkdir(parents=True, exist_ok=False)
    npz_path = output / NPZ_FILENAME
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{NPZ_FILENAME}.", suffix=".tmp.npz", dir=output
    )
    os.close(descriptor)
    try:
        np.savez_compressed(
            temporary_name,
            **{
                name: np.asarray(value)
                for name, value in source.arrays_as_mapping().items()
            },
        )
        # Persist the complete compressed archive before publishing its
        # immutable name.  This keeps a power-loss boundary from exposing a
        # linked but incompletely flushed NPZ.
        with open(temporary_name, "rb") as handle:
            os.fsync(handle.fileno())
        os.link(temporary_name, npz_path)
    except FileExistsError as error:
        raise V016OriginSourceError(f"refusing to overwrite {npz_path}") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass

    npz_digest = file_sha256(npz_path)
    body: dict[str, object] = {
        "schema": SOURCE_SCHEMA,
        "schema_version": SOURCE_SCHEMA_VERSION,
        "npz_filename": NPZ_FILENAME,
        "npz_sha256": npz_digest,
        "arrays_sha256": source.arrays_sha256(),
        "array_sha256": {
            name: _array_sha256(value)
            for name, value in source.arrays_as_mapping().items()
        },
        "row_count": source.rows,
        "world_seed": int(source.world_seed),
        "lineage": int(source.lineage),
        "field_component": FIELD_COMPONENT,
        "field_root_digest": source.field_root_digest,
        "kappa_bits_hex": float(source.kappa_bits).hex(),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "users": USERS,
        "steps": len(observed_steps),
        "observed_step_indices": list(observed_steps),
        "contexts": list(CONTEXT_CODES),
        "rows_per_anchor": USERS * len(CONTEXT_CODES),
        "row_semantics": "one-user-anchor-context-native-zr-surface",
        "row_order": "anchor-then-h-12-1-2-then-user-ascending",
        "q3_state_schema": V016_C3_ORIGIN_STATE_SCHEMA,
        "q3_state_dim": V016_C3_ORIGIN_STATE_DIM,
        "q3_target_semantics": "unchanged-ZR-z3-bits-surface",
        "q3_compatibility_semantics": "exact-ZR-physics-support",
        "contract_path": str(CONTRACT_PATH),
        "contract_sha256": CONTRACT_SHA256,
        "q1_checkpoint_sha256": source.q1_checkpoint_sha256,
        "q2_checkpoint_sha256": source.q2_checkpoint_sha256,
        "q1_parameter_sha256": source.q1_parameter_sha256,
        "q2_parameter_sha256": source.q2_parameter_sha256,
    }
    if metadata_extra is not None:
        if not isinstance(metadata_extra, Mapping):
            raise V016OriginSourceError("metadata_extra must be a mapping")
        for key, value in metadata_extra.items():
            if not isinstance(key, str) or key in body:
                raise V016OriginSourceError(
                    f"metadata_extra contains a reserved/non-string key: {key!r}"
                )
            body[key] = value
    metadata_digest = canonical_sha256(body)
    metadata_payload = dict(body)
    metadata_payload["metadata_sha256"] = metadata_digest
    metadata_path = output / METADATA_FILENAME
    _write_once_bytes(metadata_path, canonical_json_bytes(metadata_payload) + b"\n")
    receipt = (
        f"schema={SOURCE_SCHEMA}\n"
        f"npz_sha256={npz_digest}\n"
        f"metadata_sha256={file_sha256(metadata_path)}\n"
        f"arrays_sha256={source.arrays_sha256()}\n"
        f"observed_step_indices={','.join(str(value) for value in observed_steps)}\n"
    ).encode("ascii")
    _write_once_bytes(output / SHA256_FILENAME, receipt)
    return {
        "output_dir": str(output),
        "npz": str(npz_path),
        "metadata": str(metadata_path),
        "npz_sha256": npz_digest,
        "metadata_sha256": file_sha256(metadata_path),
        "arrays_sha256": source.arrays_sha256(),
    }


def _read_source_receipt(
    path: Path,
    *,
    expected_npz_sha256: str,
    expected_metadata_sha256: str,
    expected_arrays_sha256: str,
    expected_steps: tuple[int, ...],
) -> None:
    """Validate the small text receipt next to an NPZ/metadata pair."""

    receipt_path = Path(path)
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise V016OriginSourceError(
            f"source digest receipt is missing: {receipt_path}"
        )
    entries: dict[str, str] = {}
    try:
        lines = receipt_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        raise V016OriginSourceError("source digest receipt is unreadable") from error
    for line in lines:
        if "=" not in line:
            raise V016OriginSourceError("source digest receipt has a malformed line")
        key, value = line.split("=", 1)
        if not key or key in entries:
            raise V016OriginSourceError("source digest receipt has duplicate fields")
        entries[key] = value
    expected = {
        "schema": SOURCE_SCHEMA,
        "npz_sha256": expected_npz_sha256,
        "metadata_sha256": expected_metadata_sha256,
        "arrays_sha256": expected_arrays_sha256,
        "observed_step_indices": ",".join(str(value) for value in expected_steps),
    }
    if entries != expected:
        raise V016OriginSourceError(
            "source digest receipt disagrees with metadata or source arrays"
        )


def read_source_shard(output_dir: str | Path) -> ReferenceSourceArrays:
    """Read and verify an immutable NPZ source shard without pickle."""

    output = Path(output_dir)
    metadata_path = output / METADATA_FILENAME
    npz_path = output / NPZ_FILENAME
    try:
        metadata = json.loads(metadata_path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V016OriginSourceError("source metadata is unreadable") from error
    if not isinstance(metadata, dict):
        raise V016OriginSourceError("source metadata must be an object")
    supplied = metadata.get("metadata_sha256")
    _digest(supplied, field="metadata_sha256")
    body = {key: value for key, value in metadata.items() if key != "metadata_sha256"}
    if canonical_sha256(body) != supplied:
        raise V016OriginSourceError("metadata digest disagrees with its body")
    if metadata.get("schema") != SOURCE_SCHEMA:
        raise V016OriginSourceError("source metadata schema is stale")
    if metadata.get("split") != "TRAIN":
        raise V016OriginSourceError("source metadata split must be TRAIN")
    for field in ("test_split_opened", "episode_training", "learner_update"):
        if metadata.get(field) is not False:
            raise V016OriginSourceError(
                f"source metadata violates {field} boundary"
            )
    if metadata.get("contract_sha256") != CONTRACT_SHA256:
        raise V016OriginSourceError("source metadata contract digest is stale")
    if metadata.get("q3_state_schema") != V016_C3_ORIGIN_STATE_SCHEMA:
        raise V016OriginSourceError("source metadata Q3 state schema is stale")
    if metadata.get("q3_state_dim") != V016_C3_ORIGIN_STATE_DIM:
        raise V016OriginSourceError("source metadata Q3 state dimension is stale")
    if metadata.get("field_component") != FIELD_COMPONENT:
        raise V016OriginSourceError("source metadata field component is stale")
    world_value = metadata.get("world_seed")
    lineage_value = metadata.get("lineage")
    if (
        type(world_value) is not int
        or world_value not in TRAIN_WORLD_SEEDS
        or type(lineage_value) is not int
        or lineage_value not in LINEAGES
    ):
        raise V016OriginSourceError(
            "source metadata world/lineage is outside the V0.16-O declaration"
        )
    if metadata.get("npz_filename") != NPZ_FILENAME:
        raise V016OriginSourceError("source metadata NPZ filename is stale")
    observed_raw = metadata.get("observed_step_indices")
    if (
        not isinstance(observed_raw, list)
        or any(type(value) is not int for value in observed_raw)
        or tuple(observed_raw) != tuple(range(len(observed_raw)))
        or not observed_raw
        or any(value >= STEPS_PER_EPISODE for value in observed_raw)
    ):
        raise V016OriginSourceError(
            "source metadata observed step indices are malformed"
        )
    if metadata.get("steps") != len(observed_raw):
        raise V016OriginSourceError("source metadata steps disagrees with observed indices")
    for field in (
        "q1_checkpoint_sha256",
        "q2_checkpoint_sha256",
        "q1_parameter_sha256",
        "q2_parameter_sha256",
    ):
        _digest(metadata.get(field), field=field)
    for prefix in ("q1", "q2"):
        nested = metadata.get(f"{prefix}_checkpoint")
        # The four top-level digests are the canonical authenticated
        # provenance fields: they are covered by metadata_sha256, and the
        # metadata file hash is covered by source.sha256.  A nested receipt is
        # optional convenience provenance (the full harvester emits it), but
        # a hand-built or gate test shard need not duplicate the same bytes.
        if nested is None:
            continue
        if not isinstance(nested, Mapping):
            raise V016OriginSourceError(
                f"source metadata lacks authenticated {prefix.upper()} checkpoint receipt"
            )
        if nested.get("checkpoint_sha256") != metadata.get(f"{prefix}_checkpoint_sha256"):
            raise V016OriginSourceError(
                f"source metadata {prefix.upper()} checkpoint digest disagrees"
            )
        if nested.get("parameter_sha256") != metadata.get(f"{prefix}_parameter_sha256"):
            raise V016OriginSourceError(
                f"source metadata {prefix.upper()} parameter digest disagrees"
            )
    expected_npz = _digest(metadata.get("npz_sha256"), field="npz_sha256")
    if file_sha256(npz_path) != expected_npz:
        raise V016OriginSourceError("NPZ digest disagrees with metadata")
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            if set(loaded.files) != set(ARRAY_NAMES):
                raise V016OriginSourceError("source NPZ keys are unexpected")
            arrays = {name: np.array(loaded[name], copy=True) for name in ARRAY_NAMES}
    except (OSError, ValueError) as error:
        raise V016OriginSourceError("source NPZ is malformed") from error
    source = assemble_source_arrays(
        **arrays,
        world_seed=world_value,
        lineage=lineage_value,
        field_root_digest=str(metadata.get("field_root_digest")),
        kappa_bits=float.fromhex(str(metadata.get("kappa_bits_hex"))),
        q1_checkpoint_sha256=metadata["q1_checkpoint_sha256"],
        q2_checkpoint_sha256=metadata["q2_checkpoint_sha256"],
        q1_parameter_sha256=metadata["q1_parameter_sha256"],
        q2_parameter_sha256=metadata["q2_parameter_sha256"],
    )
    if source.arrays_sha256() != metadata.get("arrays_sha256"):
        raise V016OriginSourceError("source array digest disagrees with metadata")
    _read_source_receipt(
        output / SHA256_FILENAME,
        expected_npz_sha256=expected_npz,
        expected_metadata_sha256=file_sha256(metadata_path),
        expected_arrays_sha256=source.arrays_sha256(),
        expected_steps=source.observed_step_indices(),
    )
    return source


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise V016OriginSourceError(f"cannot load helper module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_v013_runner() -> ModuleType:
    return _load_module(
        REPO / ".scratch" / "zero-energy-c3-v013" / "run_v013_zero_energy_c3_oracle.py",
        "mcrl_v013_reference_source_helpers",
    )


def _load_learned_context_runner() -> ModuleType:
    return _load_module(
        REPO
        / ".scratch"
        / "multi-catfish-v015-c3-learned-context"
        / "run_v015_c3_learned_context_oracle.py",
        "mcrl_v015_reference_source_learned_helpers",
    )


def validate_frozen_contract(path: str | Path = CONTRACT_PATH) -> None:
    """Authenticate the pre-outcome contract before opening an environment."""

    source = Path(path)
    if file_sha256(source) != CONTRACT_SHA256:
        raise V016OriginSourceError("V0.16-O contract hash drifted")
    receipt = CONTRACT_RECEIPT_PATH
    if not receipt.is_file() or receipt.is_symlink():
        raise V016OriginSourceError("V0.16-O contract receipt is missing")
    first = receipt.read_text(encoding="ascii").split()
    if not first or first[0] != CONTRACT_SHA256:
        raise V016OriginSourceError("V0.16-O contract receipt disagrees")
    text = source.read_text(encoding="utf-8")
    for phrase in (
        "Status: PRE-OUTCOME CONTRACT",
        "402-dimensional origin-aware state",
        "Detached reference and one executed action",
        "2026111001",
        "No TEST world may be opened",
        "STOP_C3_B402_STRUCTURALLY",
    ):
        if phrase not in text:
            raise V016OriginSourceError(
                f"V0.16-O contract is missing required binding: {phrase}"
            )


def _parameter_sha256(network: Any) -> str:
    digest = hashlib.sha256()
    for name, value in network.state_dict().items():
        tensor = value.detach().cpu()
        digest.update(str(name).encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _q_values(network: Any, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    import torch

    values = network(
        torch.tensor(np.asarray(states, dtype=np.float32)),
        torch.tensor(np.asarray(masks, dtype=np.bool_), dtype=torch.bool),
    ).detach().cpu().numpy()
    result = np.asarray(values, dtype=np.float64)
    if result.shape != np.asarray(masks).shape or not np.all(np.isfinite(result)):
        raise V016OriginSourceError("Q surface is malformed")
    return result


def masked_argmax(scores: object, masks: object) -> np.ndarray:
    """Deterministic native-mask argmax used for detached context references."""

    values = np.asarray(scores, dtype=np.float64)
    legal = np.asarray(masks)
    if values.ndim != 2 or values.shape[1] != ACTION_DIM or not np.all(np.isfinite(values)):
        raise V016OriginSourceError("scores must be finite shape (U,28)")
    if legal.dtype != np.bool_ or legal.shape != values.shape:
        raise V016OriginSourceError("masks must be Boolean and action-aligned")
    if not np.all(np.any(legal, axis=1)):
        raise V016OriginSourceError("each context row needs one native action")
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(np.int64)


def context_base_values(
    q1_values: object, learned_q2_values: object
) -> dict[int, np.ndarray]:
    """Return detached base surfaces for h=12, h=1, and h=2."""

    q1 = np.asarray(q1_values, dtype=np.float64)
    q2 = np.asarray(learned_q2_values, dtype=np.float64)
    if q1.shape != q2.shape or q1.ndim != 2 or q1.shape[1] != ACTION_DIM:
        raise V016OriginSourceError("Q1 and learned-Q2 surfaces are not (U,28)")
    if not np.all(np.isfinite(q1)) or not np.all(np.isfinite(q2)):
        raise V016OriginSourceError("Q1 and learned-Q2 surfaces are non-finite")
    return {
        12: np.asarray(q1 + q2, dtype=np.float64),
        1: np.asarray(q1, dtype=np.float64).copy(),
        2: np.asarray(q2, dtype=np.float64).copy(),
    }


def context_reference_actions(
    q1_values: object,
    learned_q2_values: object,
    action_masks: object,
) -> dict[int, np.ndarray]:
    """Materialise every user reference before any focal state is encoded."""

    masks = np.asarray(action_masks)
    bases = context_base_values(q1_values, learned_q2_values)
    return {
        context: masked_argmax(base, masks)
        for context, base in bases.items()
    }


def current_required_power_and_opening(
    *,
    current_gain_linear: object,
    segment_start_gain_linear: object,
    action_masks: object,
    pmax_w: float = BEAM_POWER_MAX_W,
    p0_w: float = SEGMENT_START_POWER_W,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute current h=0 recurrence power and its canonical service gate.

    This deliberately uses current gain plus committed segment-start gain.
    It never reads the OPS3 projected ``required_power_w`` surface (which is
    an h>=1 future quantity).
    """

    current = np.asarray(current_gain_linear, dtype=np.float64)
    starts = np.asarray(segment_start_gain_linear, dtype=np.float64)
    legal = np.asarray(action_masks)
    if (
        current.ndim != 2
        or starts.shape != current.shape
        or legal.dtype != np.bool_
        or legal.shape != current.shape
        or current.shape[1] != ACTION_DIM
        or not np.all(np.isfinite(current))
        or not np.all(np.isfinite(starts))
        or np.any(current < 0.0)
        or np.any(starts < 0.0)
    ):
        raise V016OriginSourceError("current gain/start gain/mask matrix is malformed")
    if not math.isfinite(float(pmax_w)) or float(pmax_w) <= 0.0:
        raise V016OriginSourceError("pmax_w must be finite and positive")
    if not math.isfinite(float(p0_w)) or not 0.0 < float(p0_w) <= float(pmax_w):
        raise V016OriginSourceError("p0_w must be positive and no greater than pmax_w")
    required = np.zeros_like(current, dtype=np.float64)
    positive = legal & (current > 0.0) & (starts > 0.0)
    if bool(np.any(positive)):
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            try:
                required[positive] = recurrence_power_w(
                    starts[positive], current[positive], p0_w=float(p0_w)
                )
            except (FloatingPointError, ValueError, RuntimeError) as error:
                raise V016OriginSourceError(
                    "current recurrence power is not finite"
                ) from error
    if not np.all(np.isfinite(required)):
        raise V016OriginSourceError("current recurrence power is non-finite")
    # Use the canonical pure helper for the actual opening predicate.  The
    # duplicate recurrence above is intentional: it makes the stored matrix
    # auditable and ensures it is the h=0 current matrix, not a future OPS3
    # projection.
    opening = np.stack(
        [
            opening_service_feasibility_surface(
                legal_mask=legal[uid],
                segment_start_gain_linear=starts[uid],
                current_gain_linear=current[uid],
                p0_w=float(p0_w),
                pmax_w=float(pmax_w),
            )
            for uid in range(current.shape[0])
        ]
    )
    return required, np.asarray(opening, dtype=np.bool_)


def _build_zr_surfaces(measurements: Any, interval_s: float, kappa_bits: float) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Convert one exact live measurement into ZR z3 bits and support."""

    targets: list[np.ndarray] = []
    compatibility: list[np.ndarray] = []
    identities = True
    measurement_arrays: list[object] = [
        measurements.reference_actions,
        measurements.legal_mask,
        measurements.reference_rate_bps,
        measurements.candidate_rate_bps,
        measurements.replacement_delta_bits,
        measurements.compatible,
        measurements.served_equal,
        measurements.active_beams_equal,
        measurements.active_satellites_equal,
        measurements.rf_power_equal,
        measurements.network_power_equal,
    ]
    for uid in range(int(measurements.reference_actions.size)):
        surface = build_zr_surface(
            baseline_rate_bps=measurements.reference_rate_bps[uid],
            candidate_rate_bps=measurements.candidate_rate_bps[uid],
            compatibility=measurements.compatible[uid],
            legal_mask=measurements.legal_mask[uid],
            reference_action=int(measurements.reference_actions[uid]),
            interval_s=float(interval_s),
            kappa_bits=float(kappa_bits),
        )
        identities = identities and bool(assert_surface_identity(surface).passed)
        targets.append(np.asarray(surface.z3_bits, dtype=np.float64))
        compatibility.append(np.asarray(surface.compatibility, dtype=np.bool_))
    if measurements.removed_rate_bps is not None:
        measurement_arrays.append(measurements.removed_rate_bps)
    if measurements.insertion_delta_bits is not None:
        measurement_arrays.append(measurements.insertion_delta_bits)
    target_matrix = np.stack(targets)
    support_matrix = np.stack(compatibility)
    return target_matrix, support_matrix, {
        "identity_passed": bool(identities),
        "reference_signature_sha256": str(measurements.reference_signature_sha256),
        "measurements_sha256": _array_sha256(np.asarray(measurements.replacement_delta_bits)),
        "counterfactual_evaluations": int(measurements.counterfactual_evaluations),
        "positive_target_count": int(np.count_nonzero(target_matrix > 0.0)),
        "supported_positive_target_count": int(
            np.count_nonzero((target_matrix > 0.0) & support_matrix)
        ),
    }


def _live_digest(learned: ModuleType, environment: Any, rng: np.random.Generator) -> str:
    return str(learned._live_digest(environment, rng))


def enforce_harvest_step_boundary(*, done: bool, step_index: int, steps: int) -> None:
    """Apply the episode-boundary rule without changing partial-smoke semantics.

    A short source smoke may stop before the simulator's natural ten-step
    boundary, so ``done=False`` is allowed for ``steps < 10``.  The canonical
    ten-step source, however, is only publishable when the final committed
    action reports ``done=True``; silently accepting a truncated canonical
    shard would make its ``steps`` metadata look complete while omitting an
    episode tail.
    """

    if isinstance(step_index, bool) or not isinstance(step_index, int):
        raise V016OriginSourceError("step_index must be an integer")
    if isinstance(steps, bool) or not isinstance(steps, int) or not 0 < steps <= STEPS_PER_EPISODE:
        raise V016OriginSourceError("steps must be in 1..10")
    if bool(done) and step_index != steps - 1:
        raise V016OriginSourceError("environment ended before requested harvest steps")
    # The natural ten-step boundary is checked only after the final requested
    # commit.  Checking this at every loop iteration would reject a healthy
    # canonical episode at step zero before it had a chance to finish.
    if (
        steps == STEPS_PER_EPISODE
        and step_index == steps - 1
        and not bool(done)
    ):
        raise V016OriginSourceError(
            "canonical ten-step harvest did not reach the episode boundary"
        )


def harvest_source_shard(
    *,
    world_seed: int,
    lineage: int,
    output_dir: str | Path,
    steps: int = STEPS_PER_EPISODE,
    tle_root: str | Path | None = None,
    prereg_path: str | Path | None = None,
    v03_root: str | Path | None = None,
    q2_root: str | Path | None = None,
    contract_path: str | Path = CONTRACT_PATH,
) -> dict[str, str]:
    """Harvest one declared TRAIN world/lineage without learner updates."""

    validate_frozen_contract(contract_path)
    world = int(world_seed)
    lineage_value = int(lineage)
    if world not in TRAIN_WORLD_SEEDS:
        raise V016OriginSourceError("world seed is outside the V0.16-O TRAIN declaration")
    if lineage_value not in LINEAGES:
        raise V016OriginSourceError("lineage is outside the frozen Q1/Q2 declaration")
    if isinstance(steps, bool) or not isinstance(steps, int) or not 0 < steps <= STEPS_PER_EPISODE:
        raise V016OriginSourceError("steps must be in 1..10")
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V016OriginSourceError(f"refusing to overwrite {output}")

    learned = _load_learned_context_runner()
    teacher = _load_v013_runner()
    target_prereg = Path(prereg_path) if prereg_path is not None else teacher.screen.DEFAULT_PREREG
    target_tle_root = Path(tle_root) if tle_root is not None else teacher.screen.DEFAULT_TLE_ROOT
    target_v03_root = Path(v03_root) if v03_root is not None else teacher.screen.DEFAULT_V03_ROOT
    target_q2_root = Path(q2_root) if q2_root is not None else learned.V014_GATE_ROOT
    record = teacher.read_prereg(target_prereg)
    q1, q1_receipt = learned.load_frozen_q1(target_v03_root, lineage_value)
    q2_gate_receipt = learned.validate_v014_gate_receipts(target_q2_root)
    q2, q2_receipt = learned.load_frozen_q2(
        target_q2_root, lineage=lineage_value, gate_receipt=q2_gate_receipt
    )
    expected_field = KeyedFadingField.from_components(FIELD_COMPONENT, world)

    q1_before = _parameter_sha256(q1)
    q2_before = _parameter_sha256(q2)
    source_rows: dict[str, list[Any]] = {name: [] for name in ARRAY_NAMES}
    anchor_receipts: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v016-origin-source-tle-") as temporary:
        archive = teacher.screen._frozen_archive(
            record, target_tle_root, Path(temporary) / "frozen-tle"
        )
        environment = teacher.screen._make_environment(archive, users=teacher.USERS)
        env_rng, mobility_rng, _action_rng, _control_rng = teacher.screen._evaluation_rngs(world)
        _states, _masks, observation = environment.reset(env_rng, mobility_rng)
        step_env = environment.environment
        step_env._fading_field = expected_field
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        for step_index in range(steps):
            native = teacher.encode_ee_axis_state(step_env, observation)
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            if masks.shape != (teacher.USERS, ACTION_DIM) or not np.all(np.any(masks, axis=1)):
                raise V016OriginSourceError("native source mask is not a nonempty 100x28 matrix")
            q1_values = learned._q1_values(q1, native.state_matrix, masks)
            q1_reference = learned.select_actions(
                q1_values, np.zeros_like(q1_values), np.zeros_like(q1_values), masks, include_c3=False
            )

            # OPS3 is used only as the frozen Q2 deployable-state carrier.
            anchor = learned.snapshot_ops3_anchor(step_env, observation)
            projection = learned.project_ops3_anchor(anchor)
            ops3_surfaces = learned.build_ops3_live_surfaces(anchor, projection, q1_reference)
            q2_state = learned.encode_ee_axis_v014_q2_states(ops3_surfaces)
            q2_state.verify()
            if not np.array_equal(q2_state.action_masks, masks):
                raise V016OriginSourceError("Q2 carrier mask differs from native mask")
            learned_q2_values = learned._q2_values(q2, q2_state.state_matrix, q2_state.action_masks)
            bases = context_base_values(q1_values, learned_q2_values)
            references = {
                context: masked_argmax(base, masks)
                for context, base in bases.items()
            }
            required_power, opening = current_required_power_and_opening(
                current_gain_linear=anchor.current_gain_linear,
                segment_start_gain_linear=anchor.segment_start_gain_linear,
                action_masks=masks,
                pmax_w=BEAM_POWER_MAX_W,
                p0_w=SEGMENT_START_POWER_W,
            )
            premeasurement_digest = _live_digest(learned, environment, env_rng)
            context_receipts: list[dict[str, object]] = []
            # All reference vectors are already materialised.  Encode and
            # measure contexts in the declared order; none can feed back.
            for context in CONTEXT_CODES:
                reference = references[context]
                state = encode_ee_axis_v016_c3_origin_state(
                    step_env,
                    observation,
                    reference_actions=reference,
                    current_required_power_w=required_power,
                    opening_service_feasible=opening,
                    interval_s=interval_s,
                    kappa_bits=OPS3_KAPPA_BITS,
                    pmax_w=BEAM_POWER_MAX_W,
                )
                state.verify()
                if not np.array_equal(state.action_masks, masks):
                    raise V016OriginSourceError("C3 state mask differs from native mask")
                measurements = learned.measure_zero_marginal_c3(
                    step_env,
                    observation=observation,
                    reference_actions=reference,
                    rng=env_rng,
                    include_insertion=False,
                    interval_s=interval_s,
                )
                z3, compatibility, target_receipt = _build_zr_surfaces(
                    measurements, interval_s, OPS3_KAPPA_BITS
                )
                if not np.array_equal(measurements.legal_mask, masks):
                    raise V016OriginSourceError("ZR measurement mask differs from native mask")
                users = int(observation.num_users)
                for uid in range(users):
                    source_rows["q3_states"].append(np.asarray(state.state_matrix[uid], dtype=np.float32))
                    source_rows["action_masks"].append(np.asarray(masks[uid], dtype=np.bool_))
                    source_rows["q1_values"].append(np.asarray(q1_values[uid], dtype=np.float64))
                    source_rows["learned_q2_values"].append(np.asarray(learned_q2_values[uid], dtype=np.float64))
                    source_rows["z3_target_bits"].append(np.asarray(z3[uid], dtype=np.float64))
                    source_rows["q3_compatibility"].append(np.asarray(compatibility[uid], dtype=np.bool_))
                    source_rows["context_codes"].append(context)
                    source_rows["reference_actions"].append(int(reference[uid]))
                    source_rows["source_seeds"].append(world)
                    source_rows["lineages"].append(lineage_value)
                    source_rows["anchor_sha256s"].append(anchor.anchor_sha256)
                    source_rows["step_indices"].append(step_index)
                    source_rows["user_indices"].append(uid)
                context_receipts.append(
                    {
                        "context_code": int(context),
                        "reference_actions_sha256": _array_sha256(reference),
                        "q3_state_sha256": state.state_sha256,
                        "required_power_sha256": _array_sha256(required_power),
                        "opening_service_sha256": _array_sha256(opening),
                        "z3_target_sha256": _array_sha256(z3),
                        "compatibility_sha256": _array_sha256(compatibility),
                        "measurement": target_receipt,
                    }
                )
            postmeasurement_digest = _live_digest(learned, environment, env_rng)
            if premeasurement_digest != postmeasurement_digest:
                raise V016OriginSourceError(
                    "counterfactual source measurement changed live state or RNG"
                )
            background12 = references[12]
            step_result = environment.step(background12, env_rng)
            enforce_harvest_step_boundary(
                done=bool(step_result.done), step_index=step_index, steps=steps
            )
            anchor_receipts.append(
                {
                    "anchor_sha256": anchor.anchor_sha256,
                    "step_index": int(step_index),
                    "context_order": list(CONTEXT_CODES),
                    "background12_sha256": _array_sha256(background12),
                    "q1_sha256": _array_sha256(q1_values),
                    "learned_q2_sha256": _array_sha256(learned_q2_values),
                    "current_required_power_sha256": _array_sha256(required_power),
                    "opening_service_sha256": _array_sha256(opening),
                    "contexts": context_receipts,
                    "premeasurement_live_sha256": premeasurement_digest,
                    "postmeasurement_live_sha256": postmeasurement_digest,
                    "committed_action_count": 1,
                }
            )
            if not step_result.done:
                observation = environment.last_outcome.observation

    if _parameter_sha256(q1) != q1_before:
        raise V016OriginSourceError("frozen Q1 changed during source harvest")
    if _parameter_sha256(q2) != q2_before:
        raise V016OriginSourceError("frozen learned Q2 changed during source harvest")
    if not source_rows["q3_states"]:
        raise V016OriginSourceError("source harvest emitted no rows")
    source = assemble_source_arrays(
        **{
            "q3_states": np.stack(source_rows["q3_states"]),
            "action_masks": np.stack(source_rows["action_masks"]),
            "q1_values": np.stack(source_rows["q1_values"]),
            "learned_q2_values": np.stack(source_rows["learned_q2_values"]),
            "z3_target_bits": np.stack(source_rows["z3_target_bits"]),
            "q3_compatibility": np.stack(source_rows["q3_compatibility"]),
            "context_codes": np.asarray(source_rows["context_codes"], dtype=np.int64),
            "reference_actions": np.asarray(source_rows["reference_actions"], dtype=np.int64),
            "source_seeds": np.asarray(source_rows["source_seeds"], dtype=np.int64),
            "lineages": np.asarray(source_rows["lineages"], dtype=np.int64),
            "anchor_sha256s": np.asarray(source_rows["anchor_sha256s"], dtype="S64"),
            "step_indices": np.asarray(source_rows["step_indices"], dtype=np.int64),
            "user_indices": np.asarray(source_rows["user_indices"], dtype=np.int64),
        },
        world_seed=world,
        lineage=lineage_value,
        field_root_digest=expected_field.root_digest,
        kappa_bits=float(OPS3_KAPPA_BITS),
        q1_checkpoint_sha256=str(q1_receipt["checkpoint_sha256"]),
        q2_checkpoint_sha256=str(q2_receipt["checkpoint_sha256"]),
        q1_parameter_sha256=q1_before,
        q2_parameter_sha256=q2_before,
    )
    return write_source_shard(
        output,
        source,
        metadata_extra={
            "q1_checkpoint": dict(q1_receipt),
            "q2_checkpoint": dict(q2_receipt),
            "q2_gate_receipt": dict(q2_gate_receipt),
            "anchor_receipts": anchor_receipts,
            "source_runner_path": str(Path(__file__).resolve()),
            "source_runner_sha256": file_sha256(Path(__file__).resolve()),
            "claim_ceiling": "TRAIN_SOURCE_ONLY_NO_LEARNER_NO_TEST_NO_EFFICACY_CLAIM",
        },
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("harvest", nargs="?", default="harvest")
    parser.add_argument("--world-seed", type=int, required=True)
    parser.add_argument("--lineage", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=STEPS_PER_EPISODE)
    parser.add_argument("--tle-root", type=Path, default=None)
    parser.add_argument("--prereg", type=Path, default=None)
    parser.add_argument("--v03-root", type=Path, default=None)
    parser.add_argument("--q2-root", type=Path, default=None)
    parser.add_argument("--contract", type=Path, default=CONTRACT_PATH)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    receipt = harvest_source_shard(
        world_seed=args.world_seed,
        lineage=args.lineage,
        output_dir=args.output,
        steps=args.steps,
        tle_root=args.tle_root,
        prereg_path=args.prereg,
        v03_root=args.v03_root,
        q2_root=args.q2_root,
        contract_path=args.contract,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
