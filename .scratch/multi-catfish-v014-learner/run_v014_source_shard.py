#!/usr/bin/env python3
"""Harvest compact V0.14 Q2/Q3 teacher surfaces from one TRAIN shard.

This runner is deliberately a source collector, not a learner or an
evaluation script.  It follows the frozen Q1 + OPS3 background policy through
the canonical simulator, records one row per ``(predecision anchor, user)``,
and keeps the teacher surfaces beside (rather than inside) the deployable
states.  The expanded legal-action pair rows are produced later by the public
V0.14 pair builders.

The command line is intentionally seed-configurable.  No world or lineage
panel is frozen here.  A caller must supply an existing frozen Q1 lineage and
an output directory that does not already exist.
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
for _path in (REPO / ".scratch" / "c3-v04", REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import (  # noqa: E402
    OPS3_KAPPA_BITS,
    OPS3_LAMBDA_BITS_PER_J,
)
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v014_q2_state import (  # noqa: E402
    V014_Q2_STATE_DIM,
    V014_Q2_STATE_SCHEMA,
    encode_ee_axis_v014_q2_states,
)
from mcrl.runtime.ee_axis_v014_q3_state import (  # noqa: E402
    V014_Q3_STATE_DIM,
    V014_Q3_STATE_SCHEMA,
    encode_ee_axis_v014_q3_state,
)
from mcrl.runtime.ee_axis_zero_marginal_c3 import (  # noqa: E402
    ZERO_MARGINAL_C3_SCHEMA,
    build_zr_surface,
)
from mcrl.runtime.ee_axis_zero_marginal_c3_live import (  # noqa: E402
    measure_zero_marginal_c3,
)


SOURCE_SCHEMA = "multi-catfish-mcrl-v014-compact-source-shard-v1"
SOURCE_SCHEMA_VERSION = 1
NPZ_FILENAME = "source.npz"
METADATA_FILENAME = "metadata.json"
SHA256_FILENAME = "source.sha256"
ARRAY_NAMES = (
    "q1_values",
    "q2_states",
    "q2_masks",
    "q2_reference_actions",
    "q2_target_bits",
    "q3_states",
    "q3_masks",
    "q3_reference_actions",
    "q3_target_bits",
    "q3_compatibility",
    "source_seeds",
    "anchor_sha256s",
    "step_indices",
    "user_indices",
)


class V014SourceShardError(ValueError):
    """A compact source shard is malformed or would overwrite evidence."""


def canonical_json_bytes(payload: object) -> bytes:
    """Encode finite canonical JSON without a trailing newline."""

    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V014SourceShardError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V014SourceShardError(f"expected a regular file: {source}")
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
        raise V014SourceShardError(f"{field} must be lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V014SourceShardError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise V014SourceShardError(f"{field} must be a positive integer")
    return result


def _positive_float(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise V014SourceShardError(f"{field} must be positive and finite") from error
    if not math.isfinite(result) or result <= 0.0:
        raise V014SourceShardError(f"{field} must be positive and finite")
    return result


def _readonly(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    try:
        array = np.asarray(value)
        result = np.array(array, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise V014SourceShardError(f"{field} has an invalid array value") from error
    result.setflags(write=False)
    return result


def _finite_matrix(
    value: object,
    *,
    field: str,
    shape_tail: tuple[int, ...],
    dtype: np.dtype[Any],
) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 1 + len(shape_tail) or raw.shape[1:] != shape_tail:
        raise V014SourceShardError(
            f"{field} must have shape (N,{','.join(map(str, shape_tail))})"
        )
    result = _readonly(raw, dtype=dtype, field=field)
    if not np.all(np.isfinite(result)):
        raise V014SourceShardError(f"{field} must be finite")
    return result


def _integer_vector(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
        raise V014SourceShardError(f"{field} must be a one-dimensional integer array")
    result = _readonly(raw, dtype=np.dtype(np.int64), field=field)
    if np.any(result < 0):
        raise V014SourceShardError(f"{field} must be nonnegative")
    return result


def _boolean_matrix(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 2 or raw.shape[1] != 28 or raw.dtype != np.bool_:
        raise V014SourceShardError(f"{field} must be Boolean shape (N,28)")
    return _readonly(raw, dtype=np.dtype(np.bool_), field=field)


def _anchor_vector(value: object, *, field: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.ndim != 1:
        raise V014SourceShardError(f"{field} must be one-dimensional")
    if raw.dtype.kind == "S":
        decoded = [item.decode("ascii") for item in raw.tolist()]
    else:
        decoded = [str(item) for item in raw.tolist()]
    for index, item in enumerate(decoded):
        _digest(item, field=f"{field}[{index}]")
    # S64 is intentional: the NPZ has fixed-width ASCII anchor IDs and does
    # not require object arrays or pickle when loaded.
    return _readonly(np.asarray(decoded, dtype="S64"), dtype=np.dtype("S64"), field=field)


def _same_row_count(arrays: Mapping[str, np.ndarray]) -> int:
    counts = {name: int(value.shape[0]) for name, value in arrays.items()}
    if not counts or len(set(counts.values())) != 1:
        raise V014SourceShardError(f"source arrays disagree on row count: {counts}")
    count = next(iter(counts.values()))
    if count < 1:
        raise V014SourceShardError("source shard must contain at least one user-anchor row")
    return count


@dataclass(frozen=True)
class CompactSourceArrays:
    """One compact row per ``(anchor, user)``; no legal-action expansion."""

    q1_values: np.ndarray
    q2_states: np.ndarray
    q2_masks: np.ndarray
    q2_reference_actions: np.ndarray
    q2_target_bits: np.ndarray
    q3_states: np.ndarray
    q3_masks: np.ndarray
    q3_reference_actions: np.ndarray
    q3_target_bits: np.ndarray
    q3_compatibility: np.ndarray
    source_seeds: np.ndarray
    anchor_sha256s: np.ndarray
    step_indices: np.ndarray
    user_indices: np.ndarray
    world_seed: int
    lineage: int
    field_root_digest: str
    kappa_bits: float
    schema: str = SOURCE_SCHEMA

    def verify(self) -> str:
        if self.schema != SOURCE_SCHEMA:
            raise V014SourceShardError("unsupported compact source schema")
        arrays = {
            "q1_values": np.asarray(self.q1_values),
            "q2_states": np.asarray(self.q2_states),
            "q2_masks": np.asarray(self.q2_masks),
            "q2_reference_actions": np.asarray(self.q2_reference_actions),
            "q2_target_bits": np.asarray(self.q2_target_bits),
            "q3_states": np.asarray(self.q3_states),
            "q3_masks": np.asarray(self.q3_masks),
            "q3_reference_actions": np.asarray(self.q3_reference_actions),
            "q3_target_bits": np.asarray(self.q3_target_bits),
            "q3_compatibility": np.asarray(self.q3_compatibility),
            "source_seeds": np.asarray(self.source_seeds),
            "anchor_sha256s": np.asarray(self.anchor_sha256s),
            "step_indices": np.asarray(self.step_indices),
            "user_indices": np.asarray(self.user_indices),
        }
        count = _same_row_count(arrays)
        expected_shapes = {
            "q1_values": (count, 28),
            "q2_states": (count, V014_Q2_STATE_DIM),
            "q2_masks": (count, 28),
            "q2_reference_actions": (count,),
            "q2_target_bits": (count, 28),
            "q3_states": (count, V014_Q3_STATE_DIM),
            "q3_masks": (count, 28),
            "q3_reference_actions": (count,),
            "q3_target_bits": (count, 28),
            "q3_compatibility": (count, 28),
            "source_seeds": (count,),
            "anchor_sha256s": (count,),
            "step_indices": (count,),
            "user_indices": (count,),
        }
        for name, shape in expected_shapes.items():
            if arrays[name].shape != shape:
                raise V014SourceShardError(
                    f"{name} must have shape {shape}, got {arrays[name].shape}"
                )
        for name in (
            "q1_values",
            "q2_states",
            "q2_target_bits",
            "q3_states",
            "q3_target_bits",
        ):
            if not np.all(np.isfinite(arrays[name])):
                raise V014SourceShardError(f"{name} must be finite")
        for name in ("q2_masks", "q3_masks", "q3_compatibility"):
            if arrays[name].dtype != np.bool_:
                raise V014SourceShardError(f"{name} must have Boolean dtype")
        for name in (
            "q2_reference_actions",
            "q3_reference_actions",
            "source_seeds",
            "step_indices",
            "user_indices",
        ):
            if not np.issubdtype(arrays[name].dtype, np.integer):
                raise V014SourceShardError(f"{name} must have integer dtype")
            if np.any(arrays[name] < 0):
                raise V014SourceShardError(f"{name} must be nonnegative")
        if arrays["q2_masks"].dtype != arrays["q3_masks"].dtype:
            raise V014SourceShardError("Q2/Q3 mask dtypes disagree")
        if not np.array_equal(arrays["q2_masks"], arrays["q3_masks"]):
            raise V014SourceShardError("Q2 and Q3 masks disagree at an anchor")
        for name, masks in (("q2", arrays["q2_masks"]), ("q3", arrays["q3_masks"])):
            references = arrays[f"{name}_reference_actions"]
            if not np.all(np.any(masks, axis=1)):
                raise V014SourceShardError(f"every {name} row needs a legal action")
            if np.any(references >= 28) or not np.all(
                masks[np.arange(count), references]
            ):
                raise V014SourceShardError(f"{name} reference action is not legal")
        if np.any(arrays["q2_target_bits"][~arrays["q2_masks"]] != 0.0):
            raise V014SourceShardError("Q2 target surface is nonzero outside the safe mask")
        if np.any(arrays["q3_target_bits"][~arrays["q3_masks"]] != 0.0):
            raise V014SourceShardError("Q3 target surface is nonzero outside the safe mask")
        if np.any(arrays["q3_compatibility"] & ~arrays["q3_masks"]):
            raise V014SourceShardError("Q3 compatibility is true outside the safe mask")
        q3_rows = np.arange(count)
        if np.any(
            arrays["q3_target_bits"][q3_rows, arrays["q3_reference_actions"]] != 0.0
        ):
            raise V014SourceShardError("Q3 reference target must be exact zero")
        anchors = _anchor_vector(arrays["anchor_sha256s"], field="anchor_sha256s")
        if np.asarray(anchors).shape != (count,):
            raise V014SourceShardError("anchor_sha256s has the wrong row count")
        if _positive_int(self.world_seed, field="world_seed") != self.world_seed:
            raise V014SourceShardError("world_seed is malformed")
        if _positive_int(self.lineage, field="lineage") != self.lineage:
            raise V014SourceShardError("lineage is malformed")
        _digest(self.field_root_digest, field="field_root_digest")
        _positive_float(self.kappa_bits, field="kappa_bits")
        for value in arrays.values():
            if value.flags.writeable:
                raise V014SourceShardError("source arrays must be immutable")
        return self.arrays_sha256()

    def arrays_as_mapping(self) -> dict[str, np.ndarray]:
        return {name: np.asarray(getattr(self, name)) for name in ARRAY_NAMES}

    def arrays_sha256(self) -> str:
        self_mapping = self.arrays_as_mapping()
        return canonical_sha256(
            {name: _array_sha256(self_mapping[name]) for name in ARRAY_NAMES}
        )

    def metadata_body(self, *, npz_sha256: str) -> dict[str, object]:
        self.verify()
        return {
            "schema": self.schema,
            "schema_version": SOURCE_SCHEMA_VERSION,
            "npz_filename": NPZ_FILENAME,
            "npz_sha256": _digest(npz_sha256, field="npz_sha256"),
            "arrays_sha256": self.arrays_sha256(),
            "array_sha256": {
                name: _array_sha256(self.arrays_as_mapping()[name])
                for name in ARRAY_NAMES
            },
            "row_count": int(np.asarray(self.q1_values).shape[0]),
            "world_seed": int(self.world_seed),
            "lineage": int(self.lineage),
            "field_root_digest": self.field_root_digest,
            "kappa_bits_hex": float(self.kappa_bits).hex(),
            "split": "TRAIN",
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
            "row_semantics": "one-user-anchor-no-legal-action-expansion",
            "q1_values_semantics": "label-only-frozen-Q1-surface-not-a-state-input",
            "q2_target_semantics": "uncentered-OPS3-z2-bits-surface",
            "q3_target_semantics": "centered-ZR-z3-bits-surface-native-bits",
            "q3_compatibility_semantics": "label-only-teacher-support-not-action-mask",
            "q2_state_schema": V014_Q2_STATE_SCHEMA,
            "q2_state_dim": V014_Q2_STATE_DIM,
            "q3_state_schema": V014_Q3_STATE_SCHEMA,
            "q3_state_dim": V014_Q3_STATE_DIM,
            "ops3_lambda_bits_per_j_hex": float(OPS3_LAMBDA_BITS_PER_J).hex(),
            "zero_marginal_c3_schema": ZERO_MARGINAL_C3_SCHEMA,
        }


def assemble_source_arrays(
    *,
    q1_values: object,
    q2_states: object,
    q2_masks: object,
    q2_reference_actions: object,
    q2_target_bits: object,
    q3_states: object,
    q3_masks: object,
    q3_reference_actions: object,
    q3_target_bits: object,
    q3_compatibility: object,
    source_seeds: object,
    anchor_sha256s: object,
    step_indices: object,
    user_indices: object,
    world_seed: int,
    lineage: int,
    field_root_digest: str,
    kappa_bits: float,
) -> CompactSourceArrays:
    """Build and fully validate the compact per-user source surface."""

    result = CompactSourceArrays(
        q1_values=_finite_matrix(
            q1_values, field="q1_values", shape_tail=(28,), dtype=np.dtype(np.float64)
        ),
        q2_states=_finite_matrix(
            q2_states,
            field="q2_states",
            shape_tail=(V014_Q2_STATE_DIM,),
            dtype=np.dtype(np.float32),
        ),
        q2_masks=_boolean_matrix(q2_masks, field="q2_masks"),
        q2_reference_actions=_integer_vector(
            q2_reference_actions, field="q2_reference_actions"
        ),
        q2_target_bits=_finite_matrix(
            q2_target_bits,
            field="q2_target_bits",
            shape_tail=(28,),
            dtype=np.dtype(np.float64),
        ),
        q3_states=_finite_matrix(
            q3_states,
            field="q3_states",
            shape_tail=(V014_Q3_STATE_DIM,),
            dtype=np.dtype(np.float32),
        ),
        q3_masks=_boolean_matrix(q3_masks, field="q3_masks"),
        q3_reference_actions=_integer_vector(
            q3_reference_actions, field="q3_reference_actions"
        ),
        q3_target_bits=_finite_matrix(
            q3_target_bits,
            field="q3_target_bits",
            shape_tail=(28,),
            dtype=np.dtype(np.float64),
        ),
        q3_compatibility=_boolean_matrix(
            q3_compatibility, field="q3_compatibility"
        ),
        source_seeds=_integer_vector(source_seeds, field="source_seeds"),
        anchor_sha256s=_anchor_vector(anchor_sha256s, field="anchor_sha256s"),
        step_indices=_integer_vector(step_indices, field="step_indices"),
        user_indices=_integer_vector(user_indices, field="user_indices"),
        world_seed=int(world_seed),
        lineage=int(lineage),
        field_root_digest=str(field_root_digest),
        kappa_bits=float(kappa_bits),
    )
    result.verify()
    return result


def validate_source_arrays(source: CompactSourceArrays) -> str:
    """Public pure validation helper returning the array-set digest."""

    if not isinstance(source, CompactSourceArrays):
        raise V014SourceShardError("source must be CompactSourceArrays")
    return source.verify()


def _write_once_bytes(path: Path, payload: bytes) -> None:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V014SourceShardError(f"refusing to overwrite {destination}")
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
        raise V014SourceShardError(f"refusing to overwrite {destination}") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def write_source_shard(output_dir: str | Path, source: CompactSourceArrays) -> dict[str, str]:
    """Write one NPZ, canonical metadata, and a digest receipt write-once."""

    validate_source_arrays(source)
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V014SourceShardError(f"refusing to overwrite {output}")
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
                name: np.asarray(source.arrays_as_mapping()[name])
                for name in ARRAY_NAMES
            },
            kappa_bits=np.asarray([source.kappa_bits], dtype=np.float64),
        )
        os.link(temporary_name, npz_path)
    except FileExistsError as error:
        raise V014SourceShardError(f"refusing to overwrite {npz_path}") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass

    npz_digest = file_sha256(npz_path)
    body = source.metadata_body(npz_sha256=npz_digest)
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


def read_source_shard(output_dir: str | Path) -> CompactSourceArrays:
    """Read and verify one compact source shard without pickle."""

    output = Path(output_dir)
    metadata_path = output / METADATA_FILENAME
    npz_path = output / NPZ_FILENAME
    try:
        metadata = json.loads(metadata_path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V014SourceShardError("source metadata is not readable canonical JSON") from error
    if not isinstance(metadata, dict):
        raise V014SourceShardError("source metadata must be an object")
    supplied_metadata_digest = metadata.get("metadata_sha256")
    _digest(supplied_metadata_digest, field="metadata_sha256")
    body = {key: value for key, value in metadata.items() if key != "metadata_sha256"}
    if canonical_sha256(body) != supplied_metadata_digest:
        raise V014SourceShardError("metadata digest disagrees with its body")
    if metadata.get("schema") != SOURCE_SCHEMA:
        raise V014SourceShardError("source metadata schema is stale")
    expected_npz = _digest(metadata.get("npz_sha256"), field="npz_sha256")
    if file_sha256(npz_path) != expected_npz:
        raise V014SourceShardError("NPZ digest disagrees with metadata")
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            if set(loaded.files) != set((*ARRAY_NAMES, "kappa_bits")):
                raise V014SourceShardError("source NPZ keys are unexpected")
            arrays = {name: np.array(loaded[name], copy=True) for name in ARRAY_NAMES}
            kappa_array = np.asarray(loaded["kappa_bits"])
    except (OSError, ValueError) as error:
        raise V014SourceShardError("source NPZ is malformed") from error
    if kappa_array.shape != (1,) or not np.isfinite(kappa_array[0]):
        raise V014SourceShardError("kappa_bits NPZ value is malformed")
    source = assemble_source_arrays(
        **arrays,
        world_seed=int(metadata.get("world_seed")),
        lineage=int(metadata.get("lineage")),
        field_root_digest=str(metadata.get("field_root_digest")),
        kappa_bits=float(kappa_array[0]),
    )
    if source.arrays_sha256() != metadata.get("arrays_sha256"):
        raise V014SourceShardError("source array digest disagrees with metadata")
    return source


def _load_v013_runner() -> ModuleType:
    """Load the frozen V0.13 setup lazily, keeping pure tests simulator-free."""

    path = REPO / ".scratch" / "zero-energy-c3-v013" / "run_v013_zero_energy_c3_oracle.py"
    spec = importlib.util.spec_from_file_location("mcrl_v013_source_authority", path)
    if spec is None or spec.loader is None:
        raise V014SourceShardError(f"cannot load frozen V0.13 runner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def harvest_source_shard(
    *,
    world_seed: int,
    lineage: int,
    output_dir: str | Path,
    tle_root: str | Path | None = None,
    prereg_path: str | Path | None = None,
    v03_root: str | Path | None = None,
    steps: int | None = None,
) -> dict[str, str]:
    """Collect one configurable TRAIN episode under frozen Q1+OPS3 behavior."""

    teacher = _load_v013_runner()
    world = _positive_int(world_seed, field="world_seed")
    lineage_value = _positive_int(lineage, field="lineage")
    step_count = teacher.STEPS_PER_EPISODE if steps is None else _positive_int(steps, field="steps")
    if step_count > teacher.STEPS_PER_EPISODE:
        raise V014SourceShardError("steps cannot exceed the canonical episode length")
    target_tle_root = Path(tle_root) if tle_root is not None else teacher.screen.DEFAULT_TLE_ROOT
    target_prereg = Path(prereg_path) if prereg_path is not None else teacher.screen.DEFAULT_PREREG
    target_v03_root = Path(v03_root) if v03_root is not None else teacher.screen.DEFAULT_V03_ROOT
    record = teacher.read_prereg(target_prereg)
    q1, _q1_receipt = teacher.load_frozen_q1(target_v03_root, lineage_value)
    field = KeyedFadingField.from_components(teacher.FIELD_COMPONENT, world)
    q1_values_rows: list[np.ndarray] = []
    q2_states_rows: list[np.ndarray] = []
    q2_masks_rows: list[np.ndarray] = []
    q2_reference_rows: list[int] = []
    q2_target_rows: list[np.ndarray] = []
    q3_states_rows: list[np.ndarray] = []
    q3_masks_rows: list[np.ndarray] = []
    q3_reference_rows: list[int] = []
    q3_target_rows: list[np.ndarray] = []
    q3_compatibility_rows: list[np.ndarray] = []
    source_seeds: list[int] = []
    anchor_ids: list[str] = []
    step_indices: list[int] = []
    user_indices: list[int] = []
    with tempfile.TemporaryDirectory(prefix="mcrl-v014-source-tle-") as temporary:
        archive = teacher.screen._frozen_archive(
            record, target_tle_root, Path(temporary) / "frozen-tle"
        )
        environment = teacher.screen._make_environment(archive, users=teacher.USERS)
        env_rng, mobility_rng, _action_rng, _control_rng = teacher.screen._evaluation_rngs(world)
        _states, _masks, observation = environment.reset(env_rng, mobility_rng)
        step_env = environment.environment
        step_env._fading_field = field
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
        for step_index in range(step_count):
            native = encode_ee_axis_state(step_env, observation)
            mask = np.asarray(native.action_masks, dtype=np.bool_)
            q1_values = teacher._q1_values(q1, native.state_matrix, mask)
            q1_reference = teacher.select_actions(
                q1_values,
                np.zeros_like(q1_values),
                np.zeros_like(q1_values),
                mask,
                include_c3=False,
            )
            anchor = snapshot_ops3_anchor(step_env, observation)
            projection = project_ops3_anchor(anchor)
            ops3 = build_ops3_live_surfaces(anchor, projection, q1_reference)
            q2_state = encode_ee_axis_v014_q2_states(ops3)
            o2 = np.stack([np.asarray(surface.q2_values, dtype=np.float64) for surface in ops3])
            background = teacher.select_actions(
                q1_values,
                o2,
                np.zeros_like(o2),
                mask,
                include_c3=False,
            )
            q3_state = encode_ee_axis_v014_q3_state(
                step_env,
                observation,
                interval_s=interval_s,
                kappa_bits=OPS3_KAPPA_BITS,
            )
            measurements = measure_zero_marginal_c3(
                step_env,
                observation=observation,
                reference_actions=background,
                rng=env_rng,
                include_insertion=False,
                interval_s=interval_s,
            )
            q3_surfaces = tuple(
                build_zr_surface(
                    baseline_rate_bps=measurements.reference_rate_bps[uid],
                    candidate_rate_bps=measurements.candidate_rate_bps[uid],
                    compatibility=measurements.compatible[uid],
                    legal_mask=measurements.legal_mask[uid],
                    reference_action=int(measurements.reference_actions[uid]),
                    interval_s=interval_s,
                    kappa_bits=OPS3_KAPPA_BITS,
                )
                for uid in range(teacher.USERS)
            )
            users = int(observation.num_users)
            for uid in range(users):
                q1_values_rows.append(np.asarray(q1_values[uid], dtype=np.float64))
                q2_states_rows.append(np.asarray(q2_state.state_matrix[uid], dtype=np.float32))
                q2_masks_rows.append(np.asarray(q2_state.action_masks[uid], dtype=np.bool_))
                q2_reference_rows.append(int(ops3[uid].reference_action))
                q2_target_rows.append(np.asarray(ops3[uid].z2_bits, dtype=np.float64))
                q3_states_rows.append(np.asarray(q3_state.state_matrix[uid], dtype=np.float32))
                q3_masks_rows.append(np.asarray(q3_state.action_masks[uid], dtype=np.bool_))
                q3_reference_rows.append(int(q3_surfaces[uid].reference_action))
                q3_target_rows.append(np.asarray(q3_surfaces[uid].z3_bits, dtype=np.float64))
                q3_compatibility_rows.append(np.asarray(q3_surfaces[uid].compatibility, dtype=np.bool_))
                source_seeds.append(world)
                anchor_ids.append(anchor.anchor_sha256)
                step_indices.append(step_index)
                user_indices.append(uid)
            result = environment.step(background, env_rng)
            if result.done:
                if step_index != step_count - 1:
                    raise V014SourceShardError("environment ended before requested harvest steps")
                break
            # ``TrainerEnvironment.step`` intentionally returns the compact
            # trainer-facing ``StepResult``.  The canonical next observation
            # remains on the committed ``StepOutcome`` sidecar.
            observation = environment.last_outcome.observation
    source = assemble_source_arrays(
        q1_values=np.stack(q1_values_rows),
        q2_states=np.stack(q2_states_rows),
        q2_masks=np.stack(q2_masks_rows),
        q2_reference_actions=np.asarray(q2_reference_rows, dtype=np.int64),
        q2_target_bits=np.stack(q2_target_rows),
        q3_states=np.stack(q3_states_rows),
        q3_masks=np.stack(q3_masks_rows),
        q3_reference_actions=np.asarray(q3_reference_rows, dtype=np.int64),
        q3_target_bits=np.stack(q3_target_rows),
        q3_compatibility=np.stack(q3_compatibility_rows),
        source_seeds=np.asarray(source_seeds, dtype=np.int64),
        anchor_sha256s=np.asarray(anchor_ids, dtype="S64"),
        step_indices=np.asarray(step_indices, dtype=np.int64),
        user_indices=np.asarray(user_indices, dtype=np.int64),
        world_seed=world,
        lineage=lineage_value,
        field_root_digest=field.root_digest,
        kappa_bits=float(OPS3_KAPPA_BITS),
    )
    return write_source_shard(output_dir, source)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    harvest = sub.add_parser("harvest", help="collect one compact TRAIN source shard")
    harvest.add_argument("--world-seed", type=int, required=True)
    harvest.add_argument("--lineage", type=int, required=True)
    harvest.add_argument("--output", type=Path, required=True)
    harvest.add_argument("--steps", type=int, default=None)
    harvest.add_argument("--tle-root", type=Path, default=None)
    harvest.add_argument("--prereg", type=Path, default=None)
    harvest.add_argument("--v03-root", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "harvest":
        receipt = harvest_source_shard(
            world_seed=args.world_seed,
            lineage=args.lineage,
            output_dir=args.output,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
            steps=args.steps,
        )
        print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
