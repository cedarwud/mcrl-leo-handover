#!/usr/bin/env python3
"""Run the frozen V0.14 Q2/Q3 supervised learnability gate.

This runner is deliberately narrower than an experiment driver.  It consumes
already-authenticated compact ``source.npz`` shards, assigns complete worlds
to TRAIN or VALIDATION, fits two independent route-local heads, and reports
only the pre-registered learnability diagnostics.  It never opens TEST data,
never advances the simulator, and never runs an episode policy.

The production defaults are the V0.14 contract:

* train worlds ``2026108001``--``2026108004``;
* validation worlds ``2026108005``--``2026108007``;
* three initialisations and update rungs ``(3, 10, 30, 100, 300, 1000, 3000)``;
* Q2 state ``448`` and Q3 state ``287``;
* one generic masked mean/max action-set scorer per route.

The command is intentionally source-path based so that the caller can launch
one process after the parallel source harvest has finished.  Checkpoints and
the final receipt are write-once files; a rerun must use a new output
directory.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_v014_head import (  # noqa: E402
    EEAxisV014HeadConfig,
    EEAxisV014PairwiseLearner,
)
from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_v014_gate import (  # noqa: E402
    adjudicate_head,
    adjudicate_joint,
    select_head_rung,
)
from mcrl.runtime.ee_axis_v014_learnability import (  # noqa: E402
    CompactHeadSurfaceDataset,
    compact_balanced_generalization,
    joint_teacher_student_diagnostics,
)
from mcrl.runtime.ee_axis_v014_q2_state import (  # noqa: E402
    V014_Q2_STATE_DIM,
    V014_Q2_STATE_SCHEMA,
)
from mcrl.runtime.ee_axis_v014_q3_state import (  # noqa: E402
    V014_Q3_STATE_DIM,
    V014_Q3_STATE_SCHEMA,
)


SOURCE_RUNNER_PATH = HERE / "run_v014_source_shard.py"
_SOURCE_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v014_source_shard_for_gate", SOURCE_RUNNER_PATH
)
if _SOURCE_SPEC is None or _SOURCE_SPEC.loader is None:
    raise RuntimeError(f"cannot load V0.14 source runner: {SOURCE_RUNNER_PATH}")
_SOURCE_MODULE = importlib.util.module_from_spec(_SOURCE_SPEC)
sys.modules[_SOURCE_SPEC.name] = _SOURCE_MODULE
_SOURCE_SPEC.loader.exec_module(_SOURCE_MODULE)

CompactSourceArrays = _SOURCE_MODULE.CompactSourceArrays
V014SourceShardError = _SOURCE_MODULE.V014SourceShardError
read_source_shard = _SOURCE_MODULE.read_source_shard


RUNNER_SCHEMA = "multi-catfish-mcrl-v014-supervised-learnability-gate-v1"
AUTHORITY_SCHEMA = "multi-catfish-mcrl-v014-supervised-learnability-authority-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v014-supervised-learnability-result-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v014-supervised-learnability-checkpoint-v1"
RESULT_SEAL_SCHEMA = "multi-catfish-mcrl-v014-supervised-learnability-result-seal-v1"
CLAIM_CEILING = "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM"

ACTION_DIM = 28
DEFAULT_TRAIN_WORLD_SEEDS = (2026108001, 2026108002, 2026108003, 2026108004)
DEFAULT_VALIDATION_WORLD_SEEDS = (2026108005, 2026108006, 2026108007)
DEFAULT_INITIALIZATION_SEEDS = (2026108101, 2026108102, 2026108103)
DEFAULT_SOURCE_LINEAGES = (2026092101, 2026092102, 2026092103)
DEFAULT_UPDATE_RUNGS = (3, 10, 30, 100, 300, 1000, 3000)
DEFAULT_BATCH_SIZE = 512
DEFAULT_HIDDEN_LAYERS = (100, 50, 50)
DEFAULT_ACTIVATION = "tanh"
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_BETA = 0.1


class V014GateRunnerError(MCRLContractError):
    """A V0.14 source, contract, training, or receipt boundary failed."""


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
        raise V014GateRunnerError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V014GateRunnerError(f"expected a regular file: {source}")
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


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise V014GateRunnerError(f"{field} must be a positive integer")
    result = int(value)
    if result <= 0:
        raise V014GateRunnerError(f"{field} must be a positive integer")
    return result


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V014GateRunnerError(f"{field} must be a lowercase SHA-256")
    return value


def _readonly(value: object, *, dtype: np.dtype[Any], field: str) -> np.ndarray:
    try:
        result = np.array(value, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise V014GateRunnerError(f"{field} has an invalid array value") from error
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class V014GateSpec:
    """All choices fixed before the supervised gate is launched."""

    initialization_seeds: tuple[int, int, int] = DEFAULT_INITIALIZATION_SEEDS
    source_lineages: tuple[int, int, int] = DEFAULT_SOURCE_LINEAGES
    update_rungs: tuple[int, ...] = DEFAULT_UPDATE_RUNGS
    train_world_seeds: tuple[int, ...] = DEFAULT_TRAIN_WORLD_SEEDS
    validation_world_seeds: tuple[int, ...] = DEFAULT_VALIDATION_WORLD_SEEDS
    batch_size: int = DEFAULT_BATCH_SIZE
    q2_hidden_layers: tuple[int, ...] = DEFAULT_HIDDEN_LAYERS
    q3_hidden_layers: tuple[int, ...] = DEFAULT_HIDDEN_LAYERS
    activation: str = DEFAULT_ACTIVATION
    learning_rate: float = DEFAULT_LEARNING_RATE
    beta: float = DEFAULT_BETA
    kappa_bits: float = OPS3_KAPPA_BITS
    device: str = "cpu"

    def verify(self) -> None:
        if len(self.initialization_seeds) != 3 or len(set(self.initialization_seeds)) != 3:
            raise V014GateRunnerError("exactly three distinct initialisation seeds are required")
        for index, seed in enumerate(self.initialization_seeds):
            _positive_int(seed, field=f"initialization_seeds[{index}]")
        if len(self.source_lineages) != 3 or len(set(self.source_lineages)) != 3:
            raise V014GateRunnerError("exactly three distinct frozen source lineages are required")
        for index, lineage in enumerate(self.source_lineages):
            _positive_int(lineage, field=f"source_lineages[{index}]")
        for field, values in (
            ("update_rungs", self.update_rungs),
            ("train_world_seeds", self.train_world_seeds),
            ("validation_world_seeds", self.validation_world_seeds),
        ):
            if not values or len(set(values)) != len(values):
                raise V014GateRunnerError(f"{field} must contain distinct values")
            for index, value in enumerate(values):
                _positive_int(value, field=f"{field}[{index}]")
        if tuple(sorted(self.update_rungs)) != self.update_rungs:
            raise V014GateRunnerError("update_rungs must be in increasing order")
        if set(self.train_world_seeds) & set(self.validation_world_seeds):
            raise V014GateRunnerError("train and validation worlds must be disjoint")
        if self.batch_size < 1:
            raise V014GateRunnerError("batch_size must be positive")
        for field, layers in (
            ("q2_hidden_layers", self.q2_hidden_layers),
            ("q3_hidden_layers", self.q3_hidden_layers),
        ):
            if not layers or any(
                isinstance(width, bool) or not isinstance(width, int) or width < 1
                for width in layers
            ):
                raise V014GateRunnerError(f"{field} must contain positive widths")
        if self.activation not in {"tanh", "relu"}:
            raise V014GateRunnerError("activation must be tanh or relu")
        if not math.isfinite(float(self.learning_rate)) or self.learning_rate <= 0.0:
            raise V014GateRunnerError("learning_rate must be finite and positive")
        if not math.isfinite(float(self.beta)) or self.beta < 0.0:
            raise V014GateRunnerError("beta must be finite and nonnegative")
        if not math.isfinite(float(self.kappa_bits)) or self.kappa_bits <= 0.0:
            raise V014GateRunnerError("kappa_bits must be finite and positive")
        if float(self.kappa_bits).hex() != float(OPS3_KAPPA_BITS).hex():
            raise V014GateRunnerError("kappa_bits must equal the frozen OPS3 scale")
        if self.device != "cpu":
            raise V014GateRunnerError("the supervised gate is sealed to deterministic CPU execution")

    def q2_config(self) -> EEAxisV014HeadConfig:
        self.verify()
        return EEAxisV014HeadConfig(
            action_dim=ACTION_DIM,
            local_feature_dim=16,
            global_feature_dim=0,
            hidden_layers=tuple(self.q2_hidden_layers),
            activation=self.activation,
            learning_rate=float(self.learning_rate),
            kappa_bits=float(self.kappa_bits),
            beta=float(self.beta),
        )

    def q3_config(self) -> EEAxisV014HeadConfig:
        self.verify()
        return EEAxisV014HeadConfig(
            action_dim=ACTION_DIM,
            local_feature_dim=10,
            global_feature_dim=7,
            hidden_layers=tuple(self.q3_hidden_layers),
            activation=self.activation,
            learning_rate=float(self.learning_rate),
            kappa_bits=float(self.kappa_bits),
            beta=float(self.beta),
        )

    def as_dict(self) -> dict[str, object]:
        self.verify()
        payload = asdict(self)
        payload["q2_config"] = asdict(self.q2_config())
        payload["q3_config"] = asdict(self.q3_config())
        payload["q2_state_schema"] = V014_Q2_STATE_SCHEMA
        payload["q2_state_dim"] = V014_Q2_STATE_DIM
        payload["q3_state_schema"] = V014_Q3_STATE_SCHEMA
        payload["q3_state_dim"] = V014_Q3_STATE_DIM
        payload["action_dim"] = ACTION_DIM
        payload["update_rungs"] = list(self.update_rungs)
        payload["initialization_seeds"] = list(self.initialization_seeds)
        payload["source_lineages"] = list(self.source_lineages)
        payload["train_world_seeds"] = list(self.train_world_seeds)
        payload["validation_world_seeds"] = list(self.validation_world_seeds)
        payload["kappa_bits_hex"] = float(self.kappa_bits).hex()
        payload["learning_rate_hex"] = float(self.learning_rate).hex()
        payload["beta_hex"] = float(self.beta).hex()
        return payload


@dataclass(frozen=True)
class V014SplitData:
    """Merged compact source rows for one complete-world split."""

    q1_values: np.ndarray
    q2: CompactHeadSurfaceDataset
    q3: CompactHeadSurfaceDataset
    q3_compatibility: np.ndarray
    world_seeds: np.ndarray
    lineages: np.ndarray
    shard_keys: tuple[tuple[int, int], ...]

    def verify(self, *, kappa_bits: float) -> None:
        q1 = np.asarray(self.q1_values)
        if q1.shape != (self.q2.rows, ACTION_DIM) or not np.all(np.isfinite(q1)):
            raise V014GateRunnerError("split q1_values are malformed")
        if self.q2.rows != self.q3.rows or self.q2.action_dim != ACTION_DIM or self.q3.action_dim != ACTION_DIM:
            raise V014GateRunnerError("split Q2/Q3 rows or action dimensions disagree")
        compatibility = np.asarray(self.q3_compatibility)
        if compatibility.shape != (self.q3.rows, ACTION_DIM) or compatibility.dtype != np.bool_:
            raise V014GateRunnerError("split Q3 compatibility labels are malformed")
        if np.any(compatibility & ~np.asarray(self.q3.masks)):
            raise V014GateRunnerError("split Q3 compatibility is true outside the safe mask")
        for name, values in (("world_seeds", self.world_seeds), ("lineages", self.lineages)):
            array = np.asarray(values)
            if array.shape != (self.q2.rows,) or not np.issubdtype(array.dtype, np.integer):
                raise V014GateRunnerError(f"split {name} metadata is malformed")
        if len(self.shard_keys) < 1:
            raise V014GateRunnerError("split has no source shard")
        if float(kappa_bits).hex() != float(OPS3_KAPPA_BITS).hex():
            raise V014GateRunnerError("split scale is not the frozen OPS3 scale")


@dataclass(frozen=True)
class V014LoadedSource:
    """Both source splits plus the authenticated shard digest index."""

    train: V014SplitData
    validation: V014SplitData
    shard_receipts: tuple[dict[str, object], ...]
    source_sha256: str
    kappa_bits: float

    def verify(self) -> None:
        self.train.verify(kappa_bits=self.kappa_bits)
        self.validation.verify(kappa_bits=self.kappa_bits)
        if not self.shard_receipts:
            raise V014GateRunnerError("source closure is empty")
        _digest(self.source_sha256, field="source_sha256")
        if canonical_sha256(list(self.shard_receipts)) != self.source_sha256:
            raise V014GateRunnerError("source receipt digest disagrees with its closure")


def _normalise_path(path: str | Path) -> Path:
    value = Path(path)
    if value.is_symlink() or not value.is_dir():
        raise V014GateRunnerError(f"source shard must be a regular directory: {value}")
    return value.resolve()


def _authenticate_train_metadata(path: Path) -> dict[str, object]:
    """Check the source receipt's split boundary before loading arrays."""

    metadata_path = path / "metadata.json"
    if metadata_path.is_symlink() or not metadata_path.is_file():
        raise V014GateRunnerError(f"source metadata must be a regular file: {metadata_path}")
    try:
        payload = json.loads(metadata_path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V014GateRunnerError(f"source metadata is unreadable: {metadata_path}") from error
    if not isinstance(payload, dict):
        raise V014GateRunnerError("source metadata must be an object")
    if payload.get("schema") != _SOURCE_MODULE.SOURCE_SCHEMA:
        raise V014GateRunnerError("source metadata schema is stale")
    if payload.get("split") != "TRAIN":
        raise V014GateRunnerError("the V0.14 learner gate may open TRAIN source only")
    for field in ("test_split_opened", "episode_training", "learner_update"):
        if payload.get(field) is not False:
            raise V014GateRunnerError(f"source metadata violates {field} boundary")
    if payload.get("world_seed") is None or payload.get("lineage") is None:
        raise V014GateRunnerError("source metadata lacks world/lineage identity")
    return payload


def _concat(values: Sequence[np.ndarray], *, dtype: np.dtype[Any]) -> np.ndarray:
    if not values:
        raise V014GateRunnerError("cannot concatenate an empty source split")
    result = np.concatenate([np.asarray(value) for value in values], axis=0)
    result = np.array(result, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _make_split(
    sources: Sequence[tuple[CompactSourceArrays, int, int]],
    *,
    kappa_bits: float,
) -> V014SplitData:
    if not sources:
        raise V014GateRunnerError("source split is empty")
    q1 = _concat([source.q1_values for source, _world, _lineage in sources], dtype=np.dtype(np.float64))
    q2_states = _concat([source.q2_states for source, _world, _lineage in sources], dtype=np.dtype(np.float32))
    q2_masks = _concat([source.q2_masks for source, _world, _lineage in sources], dtype=np.dtype(np.bool_))
    q2_refs = _concat(
        [source.q2_reference_actions for source, _world, _lineage in sources], dtype=np.dtype(np.int64)
    )
    q2_targets = _concat([source.q2_target_bits for source, _world, _lineage in sources], dtype=np.dtype(np.float64))
    q3_states = _concat([source.q3_states for source, _world, _lineage in sources], dtype=np.dtype(np.float32))
    q3_masks = _concat([source.q3_masks for source, _world, _lineage in sources], dtype=np.dtype(np.bool_))
    q3_refs = _concat(
        [source.q3_reference_actions for source, _world, _lineage in sources], dtype=np.dtype(np.int64)
    )
    q3_targets = _concat([source.q3_target_bits for source, _world, _lineage in sources], dtype=np.dtype(np.float64))
    compatibility = _concat(
        [source.q3_compatibility for source, _world, _lineage in sources], dtype=np.dtype(np.bool_)
    )
    source_seeds = _concat([source.source_seeds for source, _world, _lineage in sources], dtype=np.dtype(np.int64))
    anchors = _concat([source.anchor_sha256s for source, _world, _lineage in sources], dtype=np.dtype("S64"))
    worlds = _concat(
        [np.full(source.q1_values.shape[0], world, dtype=np.int64) for source, world, _lineage in sources],
        dtype=np.dtype(np.int64),
    )
    lineages = _concat(
        [np.full(source.q1_values.shape[0], lineage, dtype=np.int64) for source, _world, lineage in sources],
        dtype=np.dtype(np.int64),
    )
    if not np.array_equal(source_seeds, worlds):
        raise V014GateRunnerError("source_seeds disagree with their shard world")
    if not np.array_equal(q2_masks, q3_masks):
        raise V014GateRunnerError("Q2 and Q3 safe masks disagree")
    # The route-local gauges are intentionally different: OPS3/Q2 is
    # centered on the frozen Q1 reference, whereas ZR/Q3 is centered on the
    # frozen Q1+OPS3 background action.  Requiring equal references would
    # reject precisely the anchors on which C2 changes the decision.
    q2 = CompactHeadSurfaceDataset(
        states=q2_states,
        masks=q2_masks,
        reference_actions=q2_refs,
        target_surfaces_bits=q2_targets,
        source_seeds=source_seeds,
        anchor_sha256s=anchors,
    )
    q3 = CompactHeadSurfaceDataset(
        states=q3_states,
        masks=q3_masks,
        reference_actions=q3_refs,
        target_surfaces_bits=q3_targets,
        source_seeds=source_seeds,
        anchor_sha256s=anchors,
    )
    result = V014SplitData(
        q1_values=q1,
        q2=q2,
        q3=q3,
        q3_compatibility=compatibility,
        world_seeds=worlds,
        lineages=lineages,
        shard_keys=tuple((int(world), int(lineage)) for _source, world, lineage in sources),
    )
    result.verify(kappa_bits=kappa_bits)
    return result


def load_source_shards(
    paths: Sequence[str | Path],
    *,
    train_world_seeds: Sequence[int] = DEFAULT_TRAIN_WORLD_SEEDS,
    validation_world_seeds: Sequence[int] = DEFAULT_VALIDATION_WORLD_SEEDS,
    kappa_bits: float = OPS3_KAPPA_BITS,
    lineage: int | None = None,
) -> V014LoadedSource:
    """Load and merge one frozen lineage without mixing a world across splits.

    When ``lineage`` is omitted, all lineages present in ``paths`` are merged
    (useful for a source census).  The production gate supplies one lineage
    per learner initialisation, so the three Q2/Q3 fits remain independent of
    one another while each still pools its four TRAIN and three VALIDATION
    worlds.
    """

    train_worlds = tuple(int(seed) for seed in train_world_seeds)
    validation_worlds = tuple(int(seed) for seed in validation_world_seeds)
    if not train_worlds or not validation_worlds or set(train_worlds) & set(validation_worlds):
        raise V014GateRunnerError("train/validation world declarations are invalid")
    if float(kappa_bits).hex() != float(OPS3_KAPPA_BITS).hex():
        raise V014GateRunnerError("source merge must use the frozen OPS3 scale")
    normalised = sorted({_normalise_path(path) for path in paths}, key=lambda value: str(value))
    if not normalised:
        raise V014GateRunnerError("at least one source shard is required")
    if lineage is not None:
        target_lineage = _positive_int(lineage, field="lineage")
    else:
        target_lineage = None
    seen_keys: set[tuple[int, int]] = set()
    train: list[tuple[CompactSourceArrays, int, int]] = []
    validation: list[tuple[CompactSourceArrays, int, int]] = []
    receipts: list[dict[str, object]] = []
    for path in normalised:
        metadata = _authenticate_train_metadata(path)
        try:
            source = read_source_shard(path)
        except (V014SourceShardError, OSError, ValueError, TypeError) as error:
            raise V014GateRunnerError(f"cannot authenticate source shard {path}") from error
        world = int(source.world_seed)
        shard_lineage = int(source.lineage)
        if int(metadata["world_seed"]) != world or int(metadata["lineage"]) != shard_lineage:
            raise V014GateRunnerError("source metadata identity disagrees with its arrays")
        if target_lineage is not None and shard_lineage != target_lineage:
            continue
        key = (world, shard_lineage)
        if key in seen_keys:
            raise V014GateRunnerError(f"duplicate source shard world/lineage: {key}")
        seen_keys.add(key)
        if world in train_worlds:
            split = "train"
            train.append((source, world, shard_lineage))
        elif world in validation_worlds:
            split = "validation"
            validation.append((source, world, shard_lineage))
        else:
            raise V014GateRunnerError(f"source world {world} is outside the declared splits")
        receipts.append(
            {
                "path": str(path),
                "world_seed": world,
                "lineage": shard_lineage,
                "split": split,
                "row_count": int(source.q1_values.shape[0]),
                "arrays_sha256": source.arrays_sha256(),
                "field_root_digest": source.field_root_digest,
            }
        )
        if float(source.kappa_bits).hex() != float(kappa_bits).hex():
            raise V014GateRunnerError("source shards mix kappa_bits")
    if {world for _source, world, _lineage in train} != set(train_worlds):
        raise V014GateRunnerError("train source closure does not cover every declared world")
    if {world for _source, world, _lineage in validation} != set(validation_worlds):
        raise V014GateRunnerError("validation source closure does not cover every declared world")
    train.sort(key=lambda row: (row[1], row[2]))
    validation.sort(key=lambda row: (row[1], row[2]))
    receipts.sort(key=lambda row: (int(row["world_seed"]), int(row["lineage"])))
    loaded = V014LoadedSource(
        train=_make_split(train, kappa_bits=float(kappa_bits)),
        validation=_make_split(validation, kappa_bits=float(kappa_bits)),
        shard_receipts=tuple(receipts),
        source_sha256=canonical_sha256(receipts),
        kappa_bits=float(kappa_bits),
    )
    loaded.verify()
    return loaded


def _code_manifest() -> dict[str, object]:
    paths = (
        Path(__file__),
        SOURCE_RUNNER_PATH,
        REPO / "src" / "mcrl" / "algorithms" / "ee_axis_v014_head.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v014_gate.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v014_learnability.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v014_q2_state.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v014_q3_state.py",
    )
    if any(not path.is_file() for path in paths):
        raise V014GateRunnerError("V0.14 code closure is incomplete")
    files = [
        {"path": str(path.resolve().relative_to(REPO.resolve())), "sha256": _file_sha256(path)}
        for path in sorted(paths, key=lambda value: str(value))
    ]
    body = {"schema": "multi-catfish-mcrl-v014-code-manifest-v1", "files": files}
    return {**body, "manifest_sha256": canonical_sha256(body)}


def _write_once_bytes(path: Path, payload: bytes) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V014GateRunnerError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, destination)
        except FileExistsError as error:
            raise V014GateRunnerError(f"refusing to overwrite {destination}") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return _file_sha256(destination)


def _write_once_json(path: Path, payload: Mapping[str, object]) -> str:
    return _write_once_bytes(
        path,
        (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii"),
    )


def _write_status(path: Path, payload: Mapping[str, object]) -> None:
    """Write progress status; unlike results, status is intentionally mutable."""

    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("ascii")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _write_once_torch(path: Path, payload: Mapping[str, object]) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V014GateRunnerError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    try:
        torch.save(dict(payload), temporary_name)
        with open(temporary_name, "rb") as handle:
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, destination)
        except FileExistsError as error:
            raise V014GateRunnerError(f"refusing to overwrite {destination}") from error
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return _file_sha256(destination)


def _batch_indices(*, rows: int, batch_size: int, update: int) -> np.ndarray:
    """Return the preregistered deterministic cyclic mini-batch.

    Update ``u`` starts at ``((u - 1) * batch_size) mod N`` and takes
    ``batch_size`` consecutive row indices, wrapping modulo the fixed TRAIN
    row count ``N``.  No RNG, shuffle, replacement choice, or outcome enters
    this schedule; Q2 and Q3 receive the same indices at each update.
    """
    if rows < 1 or batch_size < 1 or update < 1:
        raise V014GateRunnerError("invalid deterministic batch schedule")
    start = ((update - 1) * batch_size) % rows
    return (start + np.arange(batch_size, dtype=np.int64)) % rows


def _head_report(
    learner: EEAxisV014PairwiseLearner,
    *,
    train: CompactHeadSurfaceDataset,
    validation: CompactHeadSurfaceDataset,
    kappa_bits: float,
) -> Any:
    surface = learner.q_values(validation.states, validation.masks)
    return compact_balanced_generalization(
        train=train,
        validation=validation,
        validation_q_surface=surface,
        kappa_bits=kappa_bits,
    )


def _joint_report_with_compatibility(
    q2: EEAxisV014PairwiseLearner,
    q3: EEAxisV014PairwiseLearner,
    *,
    validation: V014SplitData,
    compatibility: np.ndarray,
    kappa_bits: float,
) -> dict[str, float | int]:
    """Compute the joint diagnostic with the source's teacher support labels."""

    q2_hat = q2.q_values(validation.q2.states, validation.q2.masks)
    q3_hat = q3.q_values(validation.q3.states, validation.q3.masks)
    return joint_teacher_student_diagnostics(
        q1_values=validation.q1_values,
        q2_target_bits=validation.q2.target_surfaces_bits,
        q3_target_bits=validation.q3.target_surfaces_bits,
        q2_hat=q2_hat,
        q3_hat=q3_hat,
        masks=validation.q2.masks,
        q3_compatibility=compatibility,
        kappa_bits=kappa_bits,
    )


def select_common_rung(
    q2_reports: Mapping[int, Mapping[int, Any]],
    q3_reports: Mapping[int, Mapping[int, Any]],
    *,
    initialization_seeds: Sequence[int],
    update_rungs: Sequence[int],
) -> tuple[int, dict[int, float]]:
    """Select one common deployment rung from both route-local ratios."""

    seeds = tuple(int(seed) for seed in initialization_seeds)
    rungs = tuple(int(rung) for rung in update_rungs)
    if set(q2_reports) != set(seeds) or set(q3_reports) != set(seeds):
        raise V014GateRunnerError("route reports do not match initialisation seeds")
    means: dict[int, float] = {}
    for rung in rungs:
        values: list[float] = []
        for seed in seeds:
            for reports in (q2_reports, q3_reports):
                report = reports[seed].get(rung)
                ratio = float(getattr(report, "model_to_strongest_null_mae_ratio"))
                if not math.isfinite(ratio) or ratio < 0.0:
                    raise V014GateRunnerError("common-rung report ratio is invalid")
                values.append(ratio)
        means[rung] = float(np.mean(values))
    selected = min(rungs, key=lambda rung: (means[rung], rung))
    return selected, means


def _train_initialization(
    *,
    spec: V014GateSpec,
    train: V014SplitData,
    validation: V014SplitData,
    seed: int,
    output_dir: Path,
    run_spec_sha256: str,
    source_sha256: str,
    code_manifest_sha256: str,
    status_callback: Any,
) -> tuple[dict[int, Any], dict[int, Any], dict[int, dict[str, object]], dict[int, str]]:
    q2 = EEAxisV014PairwiseLearner(spec.q2_config(), train_seed=seed, device=spec.device)
    q3 = EEAxisV014PairwiseLearner(spec.q3_config(), train_seed=seed, device=spec.device)
    q2_reports: dict[int, Any] = {}
    q3_reports: dict[int, Any] = {}
    joint_reports: dict[int, dict[str, object]] = {}
    checkpoint_hashes: dict[int, str] = {}
    completed = 0
    for rung in spec.update_rungs:
        for update in range(completed + 1, rung + 1):
            indices = _batch_indices(rows=train.q2.rows, batch_size=spec.batch_size, update=update)
            q2.update_surfaces(
                train.q2.states[indices],
                train.q2.masks[indices],
                train.q2.reference_actions[indices],
                train.q2.target_surfaces_bits[indices],
            )
            q3.update_surfaces(
                train.q3.states[indices],
                train.q3.masks[indices],
                train.q3.reference_actions[indices],
                train.q3.target_surfaces_bits[indices],
            )
        completed = rung
        q2_report = _head_report(q2, train=train.q2, validation=validation.q2, kappa_bits=spec.kappa_bits)
        q3_report = _head_report(q3, train=train.q3, validation=validation.q3, kappa_bits=spec.kappa_bits)
        joint = _joint_report_with_compatibility(
            q2,
            q3,
            validation=validation,
            compatibility=validation.q3_compatibility,
            kappa_bits=spec.kappa_bits,
        )
        q2_reports[rung] = q2_report
        q3_reports[rung] = q3_report
        joint_reports[rung] = dict(joint)
        checkpoint = {
            "schema": CHECKPOINT_SCHEMA,
            "runner_schema": RUNNER_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "run_spec_sha256": run_spec_sha256,
            "source_sha256": source_sha256,
            "code_manifest_sha256": code_manifest_sha256,
            "initialization_seed": int(seed),
            "update_rung": int(rung),
            "q2_report": q2_report.as_dict(),
            "q3_report": q3_report.as_dict(),
            "joint_report": dict(joint),
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
            "q2": q2.checkpoint_state(update_count=rung),
            "q3": q3.checkpoint_state(update_count=rung),
        }
        checkpoint_path = output_dir / "checkpoints" / f"init-{seed}-rung-{rung:06d}.pt"
        checkpoint_hashes[rung] = _write_once_torch(checkpoint_path, checkpoint)
        status_callback(seed=seed, rung=rung, q2_report=q2_report, q3_report=q3_report, joint=joint)
    return q2_reports, q3_reports, joint_reports, checkpoint_hashes


def run(
    *,
    source_paths: Sequence[str | Path],
    output_dir: str | Path,
    spec: V014GateSpec | None = None,
) -> dict[str, object]:
    """Execute the source-only V0.14 supervised learnability gate."""

    gate_spec = spec or V014GateSpec()
    gate_spec.verify()
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise V014GateRunnerError(f"refusing to overwrite gate output: {destination}")
    sources_by_seed = {
        int(seed): load_source_shards(
            source_paths,
            train_world_seeds=gate_spec.train_world_seeds,
            validation_world_seeds=gate_spec.validation_world_seeds,
            kappa_bits=gate_spec.kappa_bits,
            lineage=int(lineage),
        )
        for seed, lineage in zip(
            gate_spec.initialization_seeds, gate_spec.source_lineages, strict=True
        )
    }
    source_panel_sha256 = canonical_sha256(
        {
            str(seed): {
                "source_sha256": loaded.source_sha256,
                "lineage": int(lineage),
            }
            for seed, lineage, loaded in zip(
                gate_spec.initialization_seeds,
                gate_spec.source_lineages,
                (sources_by_seed[int(seed)] for seed in gate_spec.initialization_seeds),
                strict=True,
            )
        }
    )
    code_manifest = _code_manifest()
    authority_body = {
        "schema": AUTHORITY_SCHEMA,
        "runner_schema": RUNNER_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "spec": gate_spec.as_dict(),
        "source_panel_sha256": source_panel_sha256,
        "source_by_initialization": {
            str(seed): {
                "lineage": int(lineage),
                "source_sha256": sources_by_seed[int(seed)].source_sha256,
                "source_shards": list(sources_by_seed[int(seed)].shard_receipts),
            }
            for seed, lineage in zip(
                gate_spec.initialization_seeds, gate_spec.source_lineages, strict=True
            )
        },
        "code_manifest": code_manifest,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    authority_body["authority_sha256"] = canonical_sha256(authority_body)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "checkpoints").mkdir()
    authority_sha256 = _write_once_json(destination / "authority.json", authority_body)
    run_spec_sha256 = canonical_sha256(
        {
            "spec": gate_spec.as_dict(),
            "authority_sha256": authority_body["authority_sha256"],
            "source_panel_sha256": source_panel_sha256,
        }
    )
    started = torch.get_num_threads()
    _write_status(
        destination / "status.json",
        {
            "schema": RUNNER_SCHEMA,
            "status": "running",
            "run_spec_sha256": run_spec_sha256,
            "authority_file_sha256": authority_sha256,
            "source_panel_sha256": source_panel_sha256,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "episode_training": False,
            "completed_initializations": 0,
            "torch_num_threads": started,
        },
    )
    q2_reports_by_seed: dict[int, dict[int, Any]] = {}
    q3_reports_by_seed: dict[int, dict[int, Any]] = {}
    joint_reports_by_seed: dict[int, dict[int, dict[str, object]]] = {}
    checkpoint_hashes_by_seed: dict[int, dict[int, str]] = {}

    def status_callback(*, seed: int, rung: int, q2_report: Any, q3_report: Any, joint: Mapping[str, object]) -> None:
        _write_status(
            destination / "status.json",
            {
                "schema": RUNNER_SCHEMA,
                "status": "running",
                "run_spec_sha256": run_spec_sha256,
                "authority_file_sha256": authority_sha256,
                "source_panel_sha256": source_panel_sha256,
                "test_split_opened": False,
                "held_out_ee_evaluated": False,
                "episode_training": False,
                "completed_initializations": len(q2_reports_by_seed),
                "active_initialization_seed": int(seed),
                "last_completed_rung": int(rung),
                "last_q2_skill": float(q2_report.skill_vs_strongest_null),
                "last_q3_skill": float(q3_report.skill_vs_strongest_null),
                "last_joint_agreement": float(joint["all_anchor_argmax_agreement"]),
            },
        )

    for seed in gate_spec.initialization_seeds:
        source = sources_by_seed[int(seed)]
        q2, q3, joint, checkpoints = _train_initialization(
            spec=gate_spec,
            train=source.train,
            validation=source.validation,
            seed=int(seed),
            output_dir=destination,
            run_spec_sha256=run_spec_sha256,
            source_sha256=source.source_sha256,
            code_manifest_sha256=str(code_manifest["manifest_sha256"]),
            status_callback=status_callback,
        )
        q2_reports_by_seed[int(seed)] = q2
        q3_reports_by_seed[int(seed)] = q3
        joint_reports_by_seed[int(seed)] = joint
        checkpoint_hashes_by_seed[int(seed)] = checkpoints

    common_rung, common_means = select_common_rung(
        q2_reports_by_seed,
        q3_reports_by_seed,
        initialization_seeds=gate_spec.initialization_seeds,
        update_rungs=gate_spec.update_rungs,
    )
    q2_selected, q2_means = select_head_rung(
        q2_reports_by_seed,
        initialization_seeds=gate_spec.initialization_seeds,
        update_rungs=gate_spec.update_rungs,
    )
    q3_selected, q3_means = select_head_rung(
        q3_reports_by_seed,
        initialization_seeds=gate_spec.initialization_seeds,
        update_rungs=gate_spec.update_rungs,
    )
    q2_decision = adjudicate_head(
        q2_reports_by_seed,
        selected_rung=common_rung,
        initialization_seeds=gate_spec.initialization_seeds,
    )
    q3_decision = adjudicate_head(
        q3_reports_by_seed,
        selected_rung=common_rung,
        initialization_seeds=gate_spec.initialization_seeds,
    )
    joint_decision = adjudicate_joint(
        {
            int(seed): joint_reports_by_seed[int(seed)][common_rung]
            for seed in gate_spec.initialization_seeds
        },
        initialization_seeds=gate_spec.initialization_seeds,
    )
    passed = bool(q2_decision["passed"] and q3_decision["passed"] and joint_decision["passed"])
    result = {
        "schema": RESULT_SCHEMA,
        "runner_schema": RUNNER_SCHEMA,
        "status": "PASS_LEARNABILITY_GATE" if passed else "STOP_LEARNABILITY_GATE",
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority_body["authority_sha256"],
        "run_spec_sha256": run_spec_sha256,
        "source_panel_sha256": source_panel_sha256,
        "source_by_initialization": {
            str(seed): {
                "lineage": int(lineage),
                "source_sha256": sources_by_seed[int(seed)].source_sha256,
                "source_shards": list(sources_by_seed[int(seed)].shard_receipts),
            }
            for seed, lineage in zip(
                gate_spec.initialization_seeds, gate_spec.source_lineages, strict=True
            )
        },
        "spec": gate_spec.as_dict(),
        "q2_reports": {
            str(seed): {str(rung): report.as_dict() for rung, report in reports.items()}
            for seed, reports in q2_reports_by_seed.items()
        },
        "q3_reports": {
            str(seed): {str(rung): report.as_dict() for rung, report in reports.items()}
            for seed, reports in q3_reports_by_seed.items()
        },
        "joint_reports": {
            str(seed): {str(rung): dict(report) for rung, report in reports.items()}
            for seed, reports in joint_reports_by_seed.items()
        },
        "selection": {
            "deployment_rung": common_rung,
            "q2_diagnostic_best_rung": q2_selected,
            "q2_mean_ratios": {str(rung): value for rung, value in q2_means.items()},
            "q3_diagnostic_best_rung": q3_selected,
            "q3_mean_ratios": {str(rung): value for rung, value in q3_means.items()},
            "common_joint_rung": common_rung,
            "common_mean_ratios": {str(rung): value for rung, value in common_means.items()},
        },
        "q2_decision": q2_decision,
        "q3_decision": q3_decision,
        "joint_decision": joint_decision,
        "checkpoint_file_sha256s": {
            str(seed): {str(rung): digest for rung, digest in rows.items()}
            for seed, rows in checkpoint_hashes_by_seed.items()
        },
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "episode_training": False,
    }
    result_file_sha256 = _write_once_json(destination / "result.json", result)
    result_seal = {
        "schema": RESULT_SEAL_SCHEMA,
        "result_file_sha256": result_file_sha256,
        "authority_sha256": authority_body["authority_sha256"],
        "run_spec_sha256": run_spec_sha256,
    }
    result_seal_file_sha256 = _write_once_json(destination / "result-seal.json", result_seal)
    _write_status(destination / "status.json", {**result, "result_file_sha256": result_file_sha256})
    return {
        **result,
        "result_file_sha256": result_file_sha256,
        "result_seal_file_sha256": result_seal_file_sha256,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, action="append", required=True, help="one authenticated source shard directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--train-world-seed",
        type=int,
        action="append",
        default=None,
        help="repeat once per TRAIN world (defaults to the frozen V0.14 panel)",
    )
    parser.add_argument(
        "--validation-world-seed",
        type=int,
        action="append",
        default=None,
        help="repeat once per VALIDATION world (defaults to the frozen V0.14 panel)",
    )
    parser.add_argument(
        "--initialization-seed",
        type=int,
        action="append",
        default=None,
        help="repeat exactly three times for the learner initialisations",
    )
    parser.add_argument(
        "--source-lineage",
        type=int,
        action="append",
        default=None,
        help="repeat exactly three times, one frozen Q1 lineage per initialisation",
    )
    parser.add_argument(
        "--update-rung",
        type=int,
        action="append",
        default=None,
        help="repeat in increasing order (defaults to 3,10,30,100,300,1000,3000)",
    )
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    spec = V014GateSpec(
        initialization_seeds=tuple(args.initialization_seed or DEFAULT_INITIALIZATION_SEEDS),
        source_lineages=tuple(args.source_lineage or DEFAULT_SOURCE_LINEAGES),
        update_rungs=tuple(args.update_rung or DEFAULT_UPDATE_RUNGS),
        train_world_seeds=tuple(args.train_world_seed or DEFAULT_TRAIN_WORLD_SEEDS),
        validation_world_seeds=tuple(args.validation_world_seed or DEFAULT_VALIDATION_WORLD_SEEDS),
        batch_size=args.batch_size,
        device=args.device,
    )
    result = run(source_paths=args.source, output_dir=args.output, spec=spec)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
