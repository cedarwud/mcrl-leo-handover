"""Mechanical runner for the V0.19 normalized-output relational-Q3 learner.

This module is intentionally below the scientific gate.  It consumes source
closures that were already authenticated by ``relational_source_bridge`` and
an explicit external configuration.  It does not choose worlds, lineages,
initialisation seeds, learning rates, thresholds, or a scientific decision.

For each externally declared initialisation it updates exactly 100 steps on
the supplied batch schedule, saves one strict Q3 checkpoint, writes raw
validation predictions in a no-pickle NPZ, and reloads the checkpoint to check
bitwise equality.  Q1 and Q2 are represented only by caller-supplied digest
bindings; this module never loads either checkpoint.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np


_R2_ROOT = Path(__file__).resolve().parent
_DRAFT_ROOT = _R2_ROOT
_REPO_ROOT = _R2_ROOT.parents[2]
_SOURCE_ROOT = _REPO_ROOT / "src"
if str(_R2_ROOT) not in sys.path:
    sys.path.insert(0, str(_R2_ROOT))
if str(_DRAFT_ROOT) not in sys.path:
    sys.path.insert(0, str(_DRAFT_ROOT))
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from relational_q3_learner_v019 import (  # noqa: E402
    NORMALIZED_BITS_PER_KAPPA,
    OUTPUT_UNIT_MODES,
    RAW_BITS,
    RelationalZRC3LearnerConfig,
    RelationalZRC3PairwiseLearner,
)
from relational_source_bridge import (  # noqa: E402
    read_source_closure,
)
from relational_source_schema import (  # noqa: E402
    RelationalZRC3Source,
    validate_world_split,
)


RUNNER_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-mechanical-run-v1"
RUNNER_VERSION = 1
CONFIG_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-mechanical-config-v1"
CONFIG_VERSION = 1
REQUIRED_UPDATES = 100
PREDICTION_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-validation-predictions-v1"
PREDICTION_METADATA_FILENAME = "validation-predictions.json"
PREDICTION_NPZ_FILENAME = "validation-predictions.npz"
PREDICTION_RECEIPT_FILENAME = "validation-predictions.sha256"
PREDICTION_RECEIPT_FIELDS = (
    "schema",
    "metadata_sha256",
    "npz_sha256",
    "arrays_sha256",
    "prediction_metadata_sha256",
)


class RelationalLearnerRunnerError(ValueError):
    """A source, configuration, checkpoint, or prediction boundary failed."""


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
        raise RelationalLearnerRunnerError(
            "runner payload is not finite canonical JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalLearnerRunnerError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RelationalLearnerRunnerError(f"{field} must be a positive integer")
    return value


def _finite_positive(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalLearnerRunnerError(
            f"{field} must be finite and positive"
        ) from error
    if not math.isfinite(result) or result <= 0.0:
        raise RelationalLearnerRunnerError(f"{field} must be finite and positive")
    return result


def _array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _write_once(path: Path, payload: bytes) -> str:
    if path.exists() or path.is_symlink():
        raise RelationalLearnerRunnerError(f"refusing to overwrite {path}")
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
        raise RelationalLearnerRunnerError(f"refusing to overwrite {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return _file_sha256(path)


def _file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise RelationalLearnerRunnerError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_positive_ints(values: Sequence[int], *, field: str) -> tuple[int, ...]:
    result = tuple(values)
    if not result:
        raise RelationalLearnerRunnerError(f"{field} must not be empty")
    for value in result:
        _positive_int(value, field=field)
    if len(set(result)) != len(result):
        raise RelationalLearnerRunnerError(f"{field} contains duplicates")
    return result


def _digest_pairs(
    values: Sequence[tuple[int, str]], *, field: str
) -> tuple[tuple[int, str], ...]:
    if not values:
        raise RelationalLearnerRunnerError(f"{field} must not be empty")
    pairs: list[tuple[int, str]] = []
    for lineage, digest in values:
        pairs.append((_positive_int(lineage, field=f"{field}.lineage"), _digest(digest, field=f"{field}.sha256")))
    if len({lineage for lineage, _digest_value in pairs}) != len(pairs):
        raise RelationalLearnerRunnerError(f"{field} contains duplicate lineages")
    return tuple(sorted(pairs))


@dataclass(frozen=True)
class LearnerBatchSpec:
    """One externally fixed optimizer batch location."""

    initialization_seed: int
    world_seed: int
    lineage: int
    row_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        _positive_int(self.initialization_seed, field="batch.initialization_seed")
        _positive_int(self.world_seed, field="batch.world_seed")
        _positive_int(self.lineage, field="batch.lineage")
        if not self.row_indices:
            raise RelationalLearnerRunnerError("batch.row_indices must not be empty")
        if any(
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            for index in self.row_indices
        ):
            raise RelationalLearnerRunnerError(
                "batch.row_indices must contain nonnegative integers"
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "initialization_seed": self.initialization_seed,
            "world_seed": self.world_seed,
            "lineage": self.lineage,
            "row_indices": list(self.row_indices),
        }


@dataclass(frozen=True)
class RelationalLearnerRunConfig:
    """All mechanical choices supplied by the future frozen contract."""

    contract_sha256: str
    code_manifest_sha256: str
    train_worlds: tuple[int, ...]
    validation_worlds: tuple[int, ...]
    initialization_lineages: tuple[tuple[int, int], ...]
    q1_checkpoint_sha256_by_lineage: tuple[tuple[int, str], ...]
    q2_checkpoint_sha256_by_lineage: tuple[tuple[int, str], ...]
    batch_schedule: tuple[LearnerBatchSpec, ...]
    batch_size: int
    update_count: int
    action_dim: int
    action_context_dim: int
    victim_token_dim: int
    hidden_layers: tuple[int, ...]
    activation: str
    learning_rate: float
    kappa_bits: float
    beta: float
    output_unit_mode: str

    def __post_init__(self) -> None:
        _digest(self.contract_sha256, field="contract_sha256")
        _digest(self.code_manifest_sha256, field="code_manifest_sha256")
        _unique_positive_ints(self.train_worlds, field="train_worlds")
        _unique_positive_ints(self.validation_worlds, field="validation_worlds")
        if set(self.train_worlds) & set(self.validation_worlds):
            raise RelationalLearnerRunnerError(
                "train_worlds and validation_worlds must be disjoint"
            )
        if not self.initialization_lineages:
            raise RelationalLearnerRunnerError(
                "initialization_lineages must not be empty"
            )
        seeds: list[int] = []
        lineages: list[int] = []
        for seed, lineage in self.initialization_lineages:
            seeds.append(_positive_int(seed, field="initialization seed"))
            lineages.append(_positive_int(lineage, field="initialization lineage"))
        if len(set(seeds)) != len(seeds):
            raise RelationalLearnerRunnerError(
                "initialization_lineages contains duplicate seeds"
            )
        if len(set(lineages)) != len(lineages):
            raise RelationalLearnerRunnerError(
                "initialization_lineages contains duplicate lineages"
            )
        _digest_pairs(
            self.q1_checkpoint_sha256_by_lineage,
            field="q1_checkpoint_sha256_by_lineage",
        )
        _digest_pairs(
            self.q2_checkpoint_sha256_by_lineage,
            field="q2_checkpoint_sha256_by_lineage",
        )
        expected_lineages = set(lineages)
        if {
            lineage for lineage, _digest_value in self.q1_checkpoint_sha256_by_lineage
        } != expected_lineages:
            raise RelationalLearnerRunnerError(
                "Q1 digest bindings do not cover initialization lineages"
            )
        if {
            lineage for lineage, _digest_value in self.q2_checkpoint_sha256_by_lineage
        } != expected_lineages:
            raise RelationalLearnerRunnerError(
                "Q2 digest bindings do not cover initialization lineages"
            )
        if self.update_count != REQUIRED_UPDATES:
            raise RelationalLearnerRunnerError(
                f"update_count must be exactly {REQUIRED_UPDATES}"
            )
        _positive_int(self.batch_size, field="batch_size")
        expected_batches = self.update_count * len(self.initialization_lineages)
        if not self.batch_schedule or len(self.batch_schedule) != expected_batches:
            raise RelationalLearnerRunnerError(
                f"batch_schedule must contain exactly {expected_batches} batches"
            )
        initialization_by_seed = self.initialization_lineage_map
        schedule_counts = {seed: 0 for seed in initialization_by_seed}
        for batch in self.batch_schedule:
            if not isinstance(batch, LearnerBatchSpec):
                raise RelationalLearnerRunnerError(
                    "batch_schedule contains a malformed batch"
                )
            if batch.initialization_seed not in initialization_by_seed:
                raise RelationalLearnerRunnerError(
                    "batch_schedule contains an undeclared initialization seed"
                )
            if batch.lineage != initialization_by_seed[batch.initialization_seed]:
                raise RelationalLearnerRunnerError(
                    "batch lineage disagrees with its initialization binding"
                )
            if len(batch.row_indices) > self.batch_size:
                raise RelationalLearnerRunnerError(
                    "a batch contains more rows than batch_size"
                )
            schedule_counts[batch.initialization_seed] += 1
        if set(schedule_counts.values()) != {self.update_count}:
            raise RelationalLearnerRunnerError(
                "each initialization must have exactly 100 scheduled batches"
            )
        if isinstance(self.action_dim, bool) or not isinstance(self.action_dim, int) or self.action_dim < 1:
            raise RelationalLearnerRunnerError("action_dim must be a positive integer")
        if isinstance(self.action_context_dim, bool) or not isinstance(self.action_context_dim, int) or self.action_context_dim < 1:
            raise RelationalLearnerRunnerError(
                "action_context_dim must be a positive integer"
            )
        if isinstance(self.victim_token_dim, bool) or not isinstance(self.victim_token_dim, int) or self.victim_token_dim < 1:
            raise RelationalLearnerRunnerError(
                "victim_token_dim must be a positive integer"
            )
        if not self.hidden_layers or any(
            isinstance(width, bool) or not isinstance(width, int) or width < 1
            for width in self.hidden_layers
        ):
            raise RelationalLearnerRunnerError(
                "hidden_layers must contain positive integer widths"
            )
        if self.activation not in {"tanh", "relu"}:
            raise RelationalLearnerRunnerError(
                "activation must be 'tanh' or 'relu'"
            )
        _finite_positive(self.learning_rate, field="learning_rate")
        _finite_positive(self.kappa_bits, field="kappa_bits")
        if self.output_unit_mode not in OUTPUT_UNIT_MODES:
            raise RelationalLearnerRunnerError(
                "output_unit_mode must be explicitly set to raw_bits or normalized_bits_per_kappa"
            )
        try:
            beta = float(self.beta)
        except (TypeError, ValueError, OverflowError) as error:
            raise RelationalLearnerRunnerError("beta must be finite") from error
        if not math.isfinite(beta) or beta != 0.0:
            raise RelationalLearnerRunnerError(
                "beta must be exactly zero for the structurally centred Q3 head"
            )

    @property
    def initialization_seeds(self) -> tuple[int, ...]:
        return tuple(seed for seed, _lineage in self.initialization_lineages)

    @property
    def initialization_lineage_map(self) -> dict[int, int]:
        return {
            int(seed): int(lineage)
            for seed, lineage in self.initialization_lineages
        }

    @property
    def q1_digest_map(self) -> dict[int, str]:
        return {
            int(lineage): digest
            for lineage, digest in self.q1_checkpoint_sha256_by_lineage
        }

    @property
    def q2_digest_map(self) -> dict[int, str]:
        return {
            int(lineage): digest
            for lineage, digest in self.q2_checkpoint_sha256_by_lineage
        }

    def learner_config(self) -> RelationalZRC3LearnerConfig:
        return RelationalZRC3LearnerConfig(
            action_dim=self.action_dim,
            action_context_dim=self.action_context_dim,
            victim_token_dim=self.victim_token_dim,
            hidden_layers=tuple(self.hidden_layers),
            activation=self.activation,
            learning_rate=float(self.learning_rate),
            kappa_bits=float(self.kappa_bits),
            beta=float(self.beta),
            output_unit_mode=self.output_unit_mode,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_sha256": self.contract_sha256,
            "code_manifest_sha256": self.code_manifest_sha256,
            "output_unit_mode": self.output_unit_mode,
            "train_worlds": list(self.train_worlds),
            "validation_worlds": list(self.validation_worlds),
            "initialization_lineages": [
                {"initialization_seed": seed, "lineage": lineage}
                for seed, lineage in self.initialization_lineages
            ],
            "q1_checkpoint_sha256_by_lineage": [
                {"lineage": lineage, "sha256": digest}
                for lineage, digest in self.q1_checkpoint_sha256_by_lineage
            ],
            "q2_checkpoint_sha256_by_lineage": [
                {"lineage": lineage, "sha256": digest}
                for lineage, digest in self.q2_checkpoint_sha256_by_lineage
            ],
            "batch_schedule": [batch.as_dict() for batch in self.batch_schedule],
            "batch_size": self.batch_size,
            "update_count": self.update_count,
            "network": {
                "action_dim": self.action_dim,
                "action_context_dim": self.action_context_dim,
                "victim_token_dim": self.victim_token_dim,
                "hidden_layers": list(self.hidden_layers),
                "activation": self.activation,
                "learning_rate": float(self.learning_rate),
                "kappa_bits_hex": float(self.kappa_bits).hex(),
                "beta": float(self.beta),
                "output_unit_mode": self.output_unit_mode,
            },
        }

    def batch_schedule_for(
        self, initialization_seed: int
    ) -> tuple[LearnerBatchSpec, ...]:
        seed = _positive_int(initialization_seed, field="initialization_seed")
        if seed not in self.initialization_lineage_map:
            raise RelationalLearnerRunnerError(
                "initialization_seed is not present in external configuration"
            )
        schedule = tuple(
            batch
            for batch in self.batch_schedule
            if batch.initialization_seed == seed
        )
        if len(schedule) != self.update_count:
            raise RelationalLearnerRunnerError(
                "initialization schedule does not contain exactly 100 batches"
            )
        return schedule


_CONFIG_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "contract_sha256",
        "code_manifest_sha256",
        "output_unit_mode",
        "train_worlds",
        "validation_worlds",
        "initialization_lineages",
        "q1_checkpoint_sha256_by_lineage",
        "q2_checkpoint_sha256_by_lineage",
        "batch_schedule",
        "batch_size",
        "update_count",
        "network",
        "train_source_paths",
        "validation_source_paths",
    }
)
_NETWORK_FIELDS = frozenset(
    {
        "action_dim",
        "action_context_dim",
        "victim_token_dim",
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits_hex",
        "beta",
        "output_unit_mode",
    }
)


def _mapping_field(payload: Mapping[str, object], field: str) -> Mapping[str, object]:
    value = payload.get(field)
    if not isinstance(value, Mapping):
        raise RelationalLearnerRunnerError(f"config field {field} must be an object")
    return value


def _path_list(
    payload: Mapping[str, object], field: str, *, base: Path | None = None
) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise RelationalLearnerRunnerError(
            f"config field {field} must be a nonempty path list"
        )
    paths: list[str] = []
    for raw in value:
        if not isinstance(raw, str) or not raw:
            raise RelationalLearnerRunnerError(
                f"config field {field} contains a malformed path"
            )
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts:
            raise RelationalLearnerRunnerError(
                f"config field {field} must stay below the isolated run root"
            )
        if base is None:
            paths.append(raw)
        else:
            paths.append(str((Path(base) / path).absolute()))
    if len(set(paths)) != len(paths):
        raise RelationalLearnerRunnerError(
            f"config field {field} contains duplicate paths"
        )
    return tuple(paths)


def _config_pairs(
    payload: Mapping[str, object], field: str
) -> tuple[tuple[int, str], ...]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        raise RelationalLearnerRunnerError(f"config field {field} must be a list")
    pairs: list[tuple[int, str]] = []
    for item in raw:
        if not isinstance(item, Mapping) or set(item) != {"lineage", "sha256"}:
            raise RelationalLearnerRunnerError(
                f"config field {field} contains a malformed digest binding"
            )
        lineage = _positive_int(item.get("lineage"), field=f"{field}.lineage")
        digest = _digest(item.get("sha256"), field=f"{field}.sha256")
        pairs.append((lineage, digest))
    return tuple(pairs)


def _config_initializations(
    payload: Mapping[str, object],
) -> tuple[tuple[int, int], ...]:
    raw = payload.get("initialization_lineages")
    if not isinstance(raw, list) or not raw:
        raise RelationalLearnerRunnerError(
            "config field initialization_lineages must be a nonempty list"
        )
    pairs: list[tuple[int, int]] = []
    for item in raw:
        if not isinstance(item, Mapping) or set(item) != {
            "initialization_seed",
            "lineage",
        }:
            raise RelationalLearnerRunnerError(
                "config initialization_lineages contains a malformed entry"
            )
        pairs.append(
            (
                _positive_int(
                    item.get("initialization_seed"),
                    field="initialization_seed",
                ),
                _positive_int(item.get("lineage"), field="lineage"),
            )
        )
    return tuple(pairs)


def _config_batches(payload: Mapping[str, object]) -> tuple[LearnerBatchSpec, ...]:
    raw = payload.get("batch_schedule")
    if not isinstance(raw, list) or not raw:
        raise RelationalLearnerRunnerError(
            "config field batch_schedule must be a nonempty list"
        )
    batches: list[LearnerBatchSpec] = []
    for item in raw:
        if not isinstance(item, Mapping) or set(item) != {
            "initialization_seed",
            "world_seed",
            "lineage",
            "row_indices",
        }:
            raise RelationalLearnerRunnerError(
                "config batch_schedule contains a malformed entry"
            )
        rows = item.get("row_indices")
        if not isinstance(rows, list):
            raise RelationalLearnerRunnerError(
                "config batch row_indices must be a list"
            )
        batches.append(
            LearnerBatchSpec(
                initialization_seed=_positive_int(
                    item.get("initialization_seed"),
                    field="batch.initialization_seed",
                ),
                world_seed=_positive_int(
                    item.get("world_seed"), field="batch.world_seed"
                ),
                lineage=_positive_int(item.get("lineage"), field="batch.lineage"),
                row_indices=tuple(rows),
            )
        )
    return tuple(batches)


def read_run_config(
    path: str | Path,
) -> tuple[RelationalLearnerRunConfig, tuple[str, ...], tuple[str, ...]]:
    """Read one strict, externally authored mechanical-run configuration."""

    payload = _read_canonical_json(Path(path))
    if set(payload) != _CONFIG_FIELDS:
        raise RelationalLearnerRunnerError(
            "run config contains unknown or missing top-level fields"
        )
    if payload.get("schema") != CONFIG_SCHEMA or payload.get("schema_version") != CONFIG_VERSION:
        raise RelationalLearnerRunnerError("run config schema is stale")
    network = _mapping_field(payload, "network")
    if set(network) != _NETWORK_FIELDS:
        raise RelationalLearnerRunnerError(
            "run config network contains unknown or missing fields"
        )
    try:
        hidden_layers = tuple(network["hidden_layers"])
        kappa_bits = float.fromhex(str(network["kappa_bits_hex"]))
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise RelationalLearnerRunnerError("run config network is malformed") from error
    try:
        config = RelationalLearnerRunConfig(
            contract_sha256=str(payload["contract_sha256"]),
            code_manifest_sha256=str(payload["code_manifest_sha256"]),
            train_worlds=tuple(payload["train_worlds"]),  # type: ignore[arg-type]
            validation_worlds=tuple(payload["validation_worlds"]),  # type: ignore[arg-type]
            initialization_lineages=_config_initializations(payload),
            q1_checkpoint_sha256_by_lineage=_config_pairs(
                payload, "q1_checkpoint_sha256_by_lineage"
            ),
            q2_checkpoint_sha256_by_lineage=_config_pairs(
                payload, "q2_checkpoint_sha256_by_lineage"
            ),
            batch_schedule=_config_batches(payload),
            batch_size=payload["batch_size"],  # type: ignore[arg-type]
            update_count=payload["update_count"],  # type: ignore[arg-type]
            action_dim=network["action_dim"],  # type: ignore[arg-type]
            action_context_dim=network["action_context_dim"],  # type: ignore[arg-type]
            victim_token_dim=network["victim_token_dim"],  # type: ignore[arg-type]
            hidden_layers=hidden_layers,  # type: ignore[arg-type]
            activation=str(network["activation"]),
            learning_rate=network["learning_rate"],  # type: ignore[arg-type]
            kappa_bits=kappa_bits,
            beta=network["beta"],  # type: ignore[arg-type]
            output_unit_mode=payload["output_unit_mode"],  # type: ignore[arg-type]
        )
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        if isinstance(error, RelationalLearnerRunnerError):
            raise
        raise RelationalLearnerRunnerError("run config is malformed") from error
    if config.output_unit_mode != network["output_unit_mode"]:
        raise RelationalLearnerRunnerError(
            "run config output_unit_mode disagrees between top-level and network"
        )
    source_base = Path(path).absolute().parent
    train_paths = _path_list(payload, "train_source_paths", base=source_base)
    validation_paths = _path_list(
        payload, "validation_source_paths", base=source_base
    )
    return config, train_paths, validation_paths


@dataclass(frozen=True)
class VerifiedSourceClosure:
    """One authenticated source shard plus its stable bridge identity."""

    path: Path
    source: RelationalZRC3Source
    bridge_metadata: dict[str, object]

    def __post_init__(self) -> None:
        root = Path(self.path)
        if root.is_symlink() or not root.is_dir():
            raise RelationalLearnerRunnerError(
                f"source closure root is not a regular directory: {root}"
            )
        if self.source.world_seed != int(self.bridge_metadata["world_seed"]):
            raise RelationalLearnerRunnerError("source/bridge world mismatch")
        if self.source.lineage != int(self.bridge_metadata["lineage"]):
            raise RelationalLearnerRunnerError("source/bridge lineage mismatch")
        if self.source.split != str(self.bridge_metadata["split"]):
            raise RelationalLearnerRunnerError("source/bridge split mismatch")
        bridge_digest = self.bridge_metadata.get("bridge_metadata_sha256")
        _digest(bridge_digest, field="bridge_metadata_sha256")

    @property
    def identity(self) -> tuple[str, int, int]:
        return (
            self.source.split,
            int(self.source.world_seed),
            int(self.source.lineage),
        )

    def manifest_entry(self) -> dict[str, object]:
        return {
            "split": self.source.split,
            "world_seed": self.source.world_seed,
            "lineage": self.source.lineage,
            "rows": self.source.rows,
            "victim_count": self.source.victim_count,
            "source_arrays_sha256": self.source.arrays_sha256(),
            "source_npz_sha256": self.bridge_metadata["source_npz_sha256"],
            "source_metadata_sha256": self.bridge_metadata["source_metadata_sha256"],
            "bridge_metadata_sha256": self.bridge_metadata["bridge_metadata_sha256"],
        }


@dataclass(frozen=True)
class VerifiedSourcePanel:
    """Rectangular authenticated TRAIN/VALIDATION source closure."""

    train: tuple[VerifiedSourceClosure, ...]
    validation: tuple[VerifiedSourceClosure, ...]

    def __post_init__(self) -> None:
        if not self.train or not self.validation:
            raise RelationalLearnerRunnerError(
                "source panel needs nonempty TRAIN and VALIDATION closures"
            )
        identities = [closure.identity for closure in (*self.train, *self.validation)]
        if len(set(identities)) != len(identities):
            raise RelationalLearnerRunnerError("source panel contains duplicate closures")
        validate_world_split([closure.source for closure in (*self.train, *self.validation)])

    @property
    def train_worlds(self) -> tuple[int, ...]:
        return tuple(sorted({closure.source.world_seed for closure in self.train}))

    @property
    def validation_worlds(self) -> tuple[int, ...]:
        return tuple(sorted({closure.source.world_seed for closure in self.validation}))

    @property
    def lineages(self) -> tuple[int, ...]:
        return tuple(
            sorted(
                {
                    closure.source.lineage
                    for closure in (*self.train, *self.validation)
                }
            )
        )

    def lookup(self, *, split: str, world_seed: int, lineage: int) -> VerifiedSourceClosure:
        if split not in {"TRAIN", "VALIDATION"}:
            raise RelationalLearnerRunnerError(f"unsupported source split: {split}")
        candidates = self.train if split == "TRAIN" else self.validation
        matches = tuple(
            closure
            for closure in candidates
            if closure.source.world_seed == world_seed
            and closure.source.lineage == lineage
        )
        if len(matches) != 1:
            raise RelationalLearnerRunnerError(
                f"expected one {split} source for world/lineage {world_seed}/{lineage}"
            )
        return matches[0]

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "multi-catfish-mcrl-v019-relational-zr-source-panel-v1",
            "train": [
                closure.manifest_entry()
                for closure in sorted(self.train, key=lambda item: item.identity)
            ],
            "validation": [
                closure.manifest_entry()
                for closure in sorted(self.validation, key=lambda item: item.identity)
            ],
            "test_split_opened": False,
            "episode_training": False,
            "learner_update": False,
        }

    @property
    def source_sha256(self) -> str:
        return canonical_sha256(self.manifest())


def _load_closures(
    paths: Sequence[str | Path], *, expected_split: str
) -> tuple[VerifiedSourceClosure, ...]:
    if not paths:
        raise RelationalLearnerRunnerError(
            f"{expected_split} source path list must not be empty"
        )
    closures: list[VerifiedSourceClosure] = []
    for path_value in paths:
        root = Path(path_value)
        if root.is_symlink() or not root.is_dir():
            raise RelationalLearnerRunnerError(
                f"source closure root is not a regular directory: {root}"
            )
        try:
            source, bridge = read_source_closure(root)
        except Exception as error:
            if isinstance(error, RelationalLearnerRunnerError):
                raise
            raise RelationalLearnerRunnerError(
                f"cannot authenticate source closure: {root}"
            ) from error
        if source.split != expected_split:
            raise RelationalLearnerRunnerError(
                f"source split {source.split!r} disagrees with {expected_split!r} path list"
            )
        closures.append(
            VerifiedSourceClosure(
                path=root,
                source=source,
                bridge_metadata=bridge,
            )
        )
    return tuple(sorted(closures, key=lambda item: item.identity))


def load_verified_source_panel(
    train_paths: Sequence[str | Path],
    validation_paths: Sequence[str | Path],
    *,
    train_worlds: Sequence[int],
    validation_worlds: Sequence[int],
    lineages: Sequence[int],
) -> VerifiedSourcePanel:
    """Load a complete source panel without selecting any identity."""

    expected_train_worlds = set(_unique_positive_ints(train_worlds, field="train_worlds"))
    expected_validation_worlds = set(
        _unique_positive_ints(validation_worlds, field="validation_worlds")
    )
    expected_lineages = set(_unique_positive_ints(lineages, field="lineages"))
    if expected_train_worlds & expected_validation_worlds:
        raise RelationalLearnerRunnerError(
            "train_worlds and validation_worlds must be disjoint"
        )
    train = _load_closures(train_paths, expected_split="TRAIN")
    validation = _load_closures(validation_paths, expected_split="VALIDATION")
    if {
        closure.source.world_seed for closure in train
    } != expected_train_worlds:
        raise RelationalLearnerRunnerError("TRAIN source worlds do not match declaration")
    if {
        closure.source.world_seed for closure in validation
    } != expected_validation_worlds:
        raise RelationalLearnerRunnerError(
            "VALIDATION source worlds do not match declaration"
        )
    expected_train_keys = {
        (world, lineage)
        for world in expected_train_worlds
        for lineage in expected_lineages
    }
    expected_validation_keys = {
        (world, lineage)
        for world in expected_validation_worlds
        for lineage in expected_lineages
    }
    if {
        (closure.source.world_seed, closure.source.lineage) for closure in train
    } != expected_train_keys:
        raise RelationalLearnerRunnerError(
            "TRAIN source panel is not a complete world/lineage rectangle"
        )
    if {
        (closure.source.world_seed, closure.source.lineage)
        for closure in validation
    } != expected_validation_keys:
        raise RelationalLearnerRunnerError(
            "VALIDATION source panel is not a complete world/lineage rectangle"
        )
    return VerifiedSourcePanel(train=train, validation=validation)


def verify_harvest_source_panel_bindings(
    panel: VerifiedSourcePanel,
    config: RelationalLearnerRunConfig,
    source_paths: Sequence[str | Path],
) -> str:
    """Re-authenticate production harvester receipts against the run config.

    ``read_source_closure`` proves the persisted arrays, but it intentionally
    does not carry the simulator contract or frozen Q1/Q2 identities.  The
    production entry point therefore also requires every source directory to
    be a complete harvester closure and binds those receipts to this learner
    contract before the first optimizer update.
    """

    if not isinstance(panel, VerifiedSourcePanel):
        raise RelationalLearnerRunnerError("panel must be VerifiedSourcePanel")
    if not isinstance(config, RelationalLearnerRunConfig):
        raise RelationalLearnerRunnerError("config must be RelationalLearnerRunConfig")
    paths = tuple(Path(value) for value in source_paths)
    expected_closures = (*panel.train, *panel.validation)
    if len(paths) != len(expected_closures) or len(set(paths)) != len(paths):
        raise RelationalLearnerRunnerError(
            "production source path list is incomplete or duplicated"
        )
    expected_roots = {closure.path.absolute() for closure in expected_closures}
    if {path.absolute() for path in paths} != expected_roots:
        raise RelationalLearnerRunnerError(
            "production source paths differ from the authenticated panel"
        )

    # Lazy import avoids making the low-level source/learner seam depend on a
    # simulator harvester when it is exercised directly by synthetic tests.
    try:
        from relational_source_harvester import read_harvest_closure
    except ImportError as error:  # pragma: no cover - packaging failure
        raise RelationalLearnerRunnerError(
            "production source harvester reader is unavailable"
        ) from error

    q1_by_lineage = config.q1_digest_map
    q2_by_lineage = config.q2_digest_map
    parameter_bindings: dict[int, tuple[str, str]] = {}
    field_by_world: dict[int, str] = {}
    entries: list[dict[str, object]] = []
    for root in sorted(paths, key=lambda value: str(value.absolute())):
        try:
            harvest = read_harvest_closure(root)
        except Exception as error:
            if isinstance(error, RelationalLearnerRunnerError):
                raise
            raise RelationalLearnerRunnerError(
                f"cannot authenticate production harvest closure: {root}"
            ) from error
        source = harvest.source
        metadata = harvest.metadata
        closure = panel.lookup(
            split=source.split,
            world_seed=source.world_seed,
            lineage=source.lineage,
        )
        if closure.source.arrays_sha256() != source.arrays_sha256():
            raise RelationalLearnerRunnerError(
                "harvester/source-panel array digest mismatch"
            )
        if metadata.get("contract_sha256") != config.contract_sha256:
            raise RelationalLearnerRunnerError(
                "source harvester contract differs from learner contract"
            )
        if metadata.get("code_manifest_sha256") != config.code_manifest_sha256:
            raise RelationalLearnerRunnerError(
                "source harvester code manifest differs from learner config"
            )
        lineage = int(source.lineage)
        if metadata.get("q1_checkpoint_sha256") != q1_by_lineage[lineage]:
            raise RelationalLearnerRunnerError(
                "source harvester Q1 checkpoint differs from learner config"
            )
        if metadata.get("q2_checkpoint_sha256") != q2_by_lineage[lineage]:
            raise RelationalLearnerRunnerError(
                "source harvester Q2 checkpoint differs from learner config"
            )
        if metadata.get("kappa_bits_hex") != float(config.kappa_bits).hex():
            raise RelationalLearnerRunnerError(
                "source harvester kappa differs from learner config"
            )
        if float(source.kappa_bits).hex() != float(config.kappa_bits).hex():
            raise RelationalLearnerRunnerError(
                "source array kappa differs from learner config"
            )
        for field in (
            "config_sha256",
            "field_root_digest",
            "q1_parameter_sha256",
            "q2_parameter_sha256",
            "harvest_metadata_sha256",
        ):
            _digest(metadata.get(field), field=f"source harvest {field}")
        parameter_pair = (
            str(metadata["q1_parameter_sha256"]),
            str(metadata["q2_parameter_sha256"]),
        )
        previous_parameters = parameter_bindings.setdefault(lineage, parameter_pair)
        if previous_parameters != parameter_pair:
            raise RelationalLearnerRunnerError(
                "source harvester parameter identity changes within a lineage"
            )
        world = int(source.world_seed)
        field_digest = str(metadata["field_root_digest"])
        previous_field = field_by_world.setdefault(world, field_digest)
        if previous_field != field_digest:
            raise RelationalLearnerRunnerError(
                "source harvester keyed field changes within a world"
            )
        entries.append(
            {
                "path": str(root.absolute()),
                "split": source.split,
                "world_seed": world,
                "lineage": lineage,
                "source_arrays_sha256": source.arrays_sha256(),
                "config_sha256": metadata["config_sha256"],
                "code_manifest_sha256": metadata["code_manifest_sha256"],
                "field_root_digest": field_digest,
                "q1_checkpoint_sha256": metadata["q1_checkpoint_sha256"],
                "q2_checkpoint_sha256": metadata["q2_checkpoint_sha256"],
                "q1_parameter_sha256": parameter_pair[0],
                "q2_parameter_sha256": parameter_pair[1],
                "harvest_metadata_sha256": metadata["harvest_metadata_sha256"],
            }
        )
    return canonical_sha256(entries)


def _prediction_manifest(
    predictions: Sequence[tuple[VerifiedSourceClosure, np.ndarray]],
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for index, (closure, values) in enumerate(predictions):
        array = np.ascontiguousarray(values)
        if array.ndim != 2 or array.shape != (closure.source.rows, 28):
            raise RelationalLearnerRunnerError(
                f"validation prediction shape disagrees for {closure.identity}"
            )
        if not np.issubdtype(array.dtype, np.floating) or not np.all(np.isfinite(array)):
            raise RelationalLearnerRunnerError(
                f"validation prediction is non-finite for {closure.identity}"
            )
        entries.append(
            {
                "key": f"q_values_{index:04d}",
                "split": closure.source.split,
                "world_seed": closure.source.world_seed,
                "lineage": closure.source.lineage,
                "rows": int(array.shape[0]),
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "array_sha256": _array_sha256(array),
            }
        )
    return entries


def _write_validation_predictions(
    output_dir: Path,
    predictions: Sequence[tuple[VerifiedSourceClosure, np.ndarray]],
    *,
    initialization_seed: int,
    lineage: int,
    source_sha256: str,
    parameter_sha256: str,
    output_unit_mode: str,
) -> dict[str, object]:
    if output_unit_mode not in OUTPUT_UNIT_MODES:
        raise RelationalLearnerRunnerError(
            "prediction output_unit_mode must be explicit and recognized"
        )
    entries = _prediction_manifest(predictions)
    arrays = {
        str(entry["key"]): np.ascontiguousarray(values)
        for entry, (_closure, values) in zip(entries, predictions, strict=True)
    }
    npz_path = output_dir / PREDICTION_NPZ_FILENAME
    if npz_path.exists() or npz_path.is_symlink():
        raise RelationalLearnerRunnerError(f"refusing to overwrite {npz_path}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{PREDICTION_NPZ_FILENAME}.", suffix=".tmp.npz", dir=output_dir
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        np.savez_compressed(temporary, **arrays)
        os.link(temporary, npz_path)
    except FileExistsError as error:
        raise RelationalLearnerRunnerError(f"refusing to overwrite {npz_path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    npz_sha256 = _file_sha256(npz_path)
    body = {
        "schema": PREDICTION_SCHEMA,
        "schema_version": 1,
        "initialization_seed": initialization_seed,
        "lineage": lineage,
        "source_sha256": source_sha256,
        "parameter_sha256": parameter_sha256,
        "output_unit_mode": output_unit_mode,
        "npz_filename": PREDICTION_NPZ_FILENAME,
        "npz_sha256": npz_sha256,
        "arrays": entries,
        "arrays_sha256": canonical_sha256(entries),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": True,
    }
    payload = {**body, "prediction_metadata_sha256": canonical_sha256(body)}
    metadata_path = output_dir / PREDICTION_METADATA_FILENAME
    metadata_sha256 = _write_once(metadata_path, _canonical_bytes(payload))
    receipt_values = {
        "schema": PREDICTION_SCHEMA,
        "metadata_sha256": metadata_sha256,
        "npz_sha256": npz_sha256,
        "arrays_sha256": body["arrays_sha256"],
        "prediction_metadata_sha256": payload["prediction_metadata_sha256"],
    }
    receipt_bytes = "".join(
        f"{field}={receipt_values[field]}\n"
        for field in PREDICTION_RECEIPT_FIELDS
    ).encode("ascii")
    receipt_path = output_dir / PREDICTION_RECEIPT_FILENAME
    receipt_sha256 = _write_once(receipt_path, receipt_bytes)
    return {
        "metadata": str(metadata_path),
        "npz": str(npz_path),
        "receipt": str(receipt_path),
        "metadata_sha256": metadata_sha256,
        "npz_sha256": npz_sha256,
        "arrays_sha256": str(body["arrays_sha256"]),
        "prediction_metadata_sha256": str(payload["prediction_metadata_sha256"]),
        "receipt_sha256": receipt_sha256,
        "entries": entries,
    }


def _read_canonical_json(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise RelationalLearnerRunnerError(f"missing prediction metadata: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RelationalLearnerRunnerError("prediction metadata is not JSON") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise RelationalLearnerRunnerError("prediction metadata is not canonical JSON")
    return payload


def _read_prediction_receipt(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise RelationalLearnerRunnerError(f"missing prediction receipt: {path}")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise RelationalLearnerRunnerError("prediction receipt is not ASCII") from error
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise RelationalLearnerRunnerError("prediction receipt contains malformed line")
        key, value = line.split("=", 1)
        if key in values or key not in PREDICTION_RECEIPT_FIELDS:
            raise RelationalLearnerRunnerError("prediction receipt contains unknown field")
        values[key] = value
    if tuple(values) != PREDICTION_RECEIPT_FIELDS:
        raise RelationalLearnerRunnerError("prediction receipt fields are incomplete")
    for field in PREDICTION_RECEIPT_FIELDS[1:]:
        _digest(values[field], field=f"prediction receipt {field}")
    if values["schema"] != PREDICTION_SCHEMA:
        raise RelationalLearnerRunnerError("prediction receipt schema is stale")
    return values


def read_validation_predictions(
    output_dir: str | Path,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    """Authenticate and load raw validation predictions without pickle."""

    root = Path(output_dir)
    metadata = _read_canonical_json(root / PREDICTION_METADATA_FILENAME)
    receipt = _read_prediction_receipt(root / PREDICTION_RECEIPT_FILENAME)
    body = {
        key: value
        for key, value in metadata.items()
        if key != "prediction_metadata_sha256"
    }
    prediction_digest = _digest(
        metadata.get("prediction_metadata_sha256"),
        field="prediction_metadata_sha256",
    )
    if canonical_sha256(body) != prediction_digest:
        raise RelationalLearnerRunnerError("prediction metadata self-digest failed")
    expected_keys = {
        "schema",
        "schema_version",
        "initialization_seed",
        "lineage",
        "source_sha256",
        "parameter_sha256",
        "output_unit_mode",
        "npz_filename",
        "npz_sha256",
        "arrays",
        "arrays_sha256",
        "test_split_opened",
        "episode_training",
        "learner_update",
        "prediction_metadata_sha256",
    }
    if set(metadata) != expected_keys:
        raise RelationalLearnerRunnerError(
            "prediction metadata contains unknown or missing fields"
        )
    npz_path = root / PREDICTION_NPZ_FILENAME
    if metadata["npz_filename"] != PREDICTION_NPZ_FILENAME:
        raise RelationalLearnerRunnerError("prediction NPZ filename is stale")
    if metadata["schema"] != PREDICTION_SCHEMA or metadata["schema_version"] != 1:
        raise RelationalLearnerRunnerError("prediction schema is stale")
    _positive_int(metadata["initialization_seed"], field="prediction.initialization_seed")
    _positive_int(metadata["lineage"], field="prediction.lineage")
    _digest(metadata["source_sha256"], field="prediction.source_sha256")
    _digest(metadata["parameter_sha256"], field="prediction.parameter_sha256")
    if metadata["output_unit_mode"] not in OUTPUT_UNIT_MODES:
        raise RelationalLearnerRunnerError(
            "prediction output_unit_mode is unknown"
        )
    actual_npz = _file_sha256(npz_path)
    if receipt["npz_sha256"] != actual_npz or metadata["npz_sha256"] != actual_npz:
        raise RelationalLearnerRunnerError("prediction NPZ digest mismatch")
    if receipt["metadata_sha256"] != _file_sha256(root / PREDICTION_METADATA_FILENAME):
        raise RelationalLearnerRunnerError("prediction metadata file digest mismatch")
    if receipt["arrays_sha256"] != metadata["arrays_sha256"]:
        raise RelationalLearnerRunnerError("prediction array manifest digest mismatch")
    if receipt["prediction_metadata_sha256"] != prediction_digest:
        raise RelationalLearnerRunnerError("prediction self-digest receipt mismatch")
    if (
        metadata["test_split_opened"] is not False
        or metadata["episode_training"] is not False
        or metadata["learner_update"] is not True
    ):
        raise RelationalLearnerRunnerError("prediction metadata crosses evaluation boundary")
    raw_entries = metadata.get("arrays")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise RelationalLearnerRunnerError("prediction array manifest is empty")
    if canonical_sha256(raw_entries) != metadata["arrays_sha256"]:
        raise RelationalLearnerRunnerError("prediction array manifest self-digest failed")
    arrays: dict[str, np.ndarray] = {}
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            if set(loaded.files) != {str(entry["key"]) for entry in raw_entries}:
                raise RelationalLearnerRunnerError("prediction NPZ keys disagree with metadata")
            for entry in raw_entries:
                key = str(entry["key"])
                value = np.array(loaded[key], copy=True)
                if value.dtype.str != str(entry["dtype"]):
                    raise RelationalLearnerRunnerError(
                        f"prediction dtype mismatch for {key}"
                    )
                if list(value.shape) != list(entry["shape"]):
                    raise RelationalLearnerRunnerError(
                        f"prediction shape mismatch for {key}"
                    )
                if _array_sha256(value) != entry["array_sha256"]:
                    raise RelationalLearnerRunnerError(
                        f"prediction array digest mismatch for {key}"
                    )
                if not np.all(np.isfinite(value)):
                    raise RelationalLearnerRunnerError(
                        f"prediction contains non-finite values for {key}"
                    )
                arrays[key] = value
    except (OSError, ValueError, TypeError) as error:
        if isinstance(error, RelationalLearnerRunnerError):
            raise
        raise RelationalLearnerRunnerError("prediction NPZ is malformed") from error
    return arrays, metadata


def _prediction_digest(
    predictions: Sequence[tuple[VerifiedSourceClosure, np.ndarray]],
) -> str:
    return canonical_sha256(_prediction_manifest(predictions))


def _predictions_bitwise_equal(
    left: Sequence[tuple[VerifiedSourceClosure, np.ndarray]],
    right: Sequence[tuple[VerifiedSourceClosure, np.ndarray]],
) -> bool:
    if len(left) != len(right):
        return False
    for (left_closure, left_values), (right_closure, right_values) in zip(
        left, right, strict=True
    ):
        if left_closure.identity != right_closure.identity:
            return False
        if left_values.dtype != right_values.dtype or left_values.shape != right_values.shape:
            return False
        if left_values.tobytes(order="C") != right_values.tobytes(order="C"):
            return False
    return True


def _write_result(output_dir: Path, result: Mapping[str, object]) -> dict[str, object]:
    body = dict(result)
    payload = {**body, "result_sha256": canonical_sha256(body)}
    _write_once(output_dir / "result.json", _canonical_bytes(payload))
    return payload


def run_initialization(
    panel: VerifiedSourcePanel,
    config: RelationalLearnerRunConfig,
    *,
    initialization_seed: int,
    output_dir: str | Path,
) -> dict[str, object]:
    """Run one external initialization through exactly 100 mechanical updates."""

    if not isinstance(panel, VerifiedSourcePanel):
        raise RelationalLearnerRunnerError("panel must be VerifiedSourcePanel")
    if not isinstance(config, RelationalLearnerRunConfig):
        raise RelationalLearnerRunnerError("config must be RelationalLearnerRunConfig")
    seed = _positive_int(initialization_seed, field="initialization_seed")
    lineage = config.initialization_lineage_map.get(seed)
    if lineage is None:
        raise RelationalLearnerRunnerError(
            "initialization_seed is not present in external configuration"
        )
    for world in config.train_worlds:
        panel.lookup(split="TRAIN", world_seed=world, lineage=lineage)
    for world in config.validation_worlds:
        panel.lookup(split="VALIDATION", world_seed=world, lineage=lineage)
    q1_digest = config.q1_digest_map[lineage]
    q2_digest = config.q2_digest_map[lineage]
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise RelationalLearnerRunnerError(
            f"refusing to overwrite learner output: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=False)
    learner = RelationalZRC3PairwiseLearner(
        config.learner_config(),
        train_seed=seed,
        device="cpu",
    )
    schedule = config.batch_schedule_for(seed)
    update_reports: list[dict[str, object]] = []
    for update_number, batch in enumerate(schedule, start=1):
        source_closure = panel.lookup(
            split="TRAIN", world_seed=batch.world_seed, lineage=batch.lineage
        )
        indices = np.asarray(batch.row_indices, dtype=np.int64)
        report = learner.update(source_closure.source, indices=indices)
        if int(report["update_count"]) != update_number:
            raise RelationalLearnerRunnerError(
                "learner update count diverged from the external batch schedule"
            )
        update_reports.append({str(key): value for key, value in report.items()})
    if learner.update_count != REQUIRED_UPDATES:
        raise RelationalLearnerRunnerError(
            f"learner completed {learner.update_count} updates, expected {REQUIRED_UPDATES}"
        )
    source_sha256 = panel.source_sha256
    checkpoint = learner.save_checkpoint(
        destination / "checkpoint.pt",
        contract_sha256=config.contract_sha256,
        source_sha256=source_sha256,
        code_manifest_sha256=config.code_manifest_sha256,
    )
    parameter_sha256 = learner.parameter_sha256()
    validation = tuple(
        (
            closure,
            np.ascontiguousarray(learner.q_values(closure.source)),
        )
        for closure in sorted(panel.validation, key=lambda item: item.identity)
        if closure.source.lineage == lineage
    )
    prediction_receipt = _write_validation_predictions(
        destination,
        validation,
        initialization_seed=seed,
        lineage=lineage,
        source_sha256=source_sha256,
        parameter_sha256=parameter_sha256,
        output_unit_mode=config.output_unit_mode,
    )
    restored = RelationalZRC3PairwiseLearner(
        config.learner_config(),
        train_seed=seed,
        device="cpu",
    )
    restored_updates = restored.load_checkpoint(
        checkpoint["path"],
        contract_sha256=config.contract_sha256,
        source_sha256=source_sha256,
        code_manifest_sha256=config.code_manifest_sha256,
    )
    reloaded_parameter_sha256 = restored.parameter_sha256()
    reloaded_validation = tuple(
        (
            closure,
            np.ascontiguousarray(restored.q_values(closure.source)),
        )
        for closure in sorted(panel.validation, key=lambda item: item.identity)
        if closure.source.lineage == lineage
    )
    validation_digest = _prediction_digest(validation)
    reloaded_validation_digest = _prediction_digest(reloaded_validation)
    bitwise_equal = (
        parameter_sha256 == reloaded_parameter_sha256
        and validation_digest == reloaded_validation_digest
        and _predictions_bitwise_equal(validation, reloaded_validation)
    )
    if not bitwise_equal or restored_updates != REQUIRED_UPDATES:
        raise RelationalLearnerRunnerError(
            "checkpoint reload is not bitwise-identical to the saved Q3 learner"
        )
    result_body = {
        "schema": RUNNER_SCHEMA,
        "version": RUNNER_VERSION,
        "status": "MECHANICAL_ARTIFACT_WRITTEN",
        "initialization_seed": seed,
        "lineage": lineage,
        "output_unit_mode": config.output_unit_mode,
        "config": config.as_dict(),
        "schedule_sha256": canonical_sha256(
            [batch.as_dict() for batch in schedule]
        ),
        "source_panel_sha256": source_sha256,
        "q1_q2_digest_binding": {
            "q1_checkpoint_sha256": q1_digest,
            "q2_checkpoint_sha256": q2_digest,
            "loaded": False,
            "modified": False,
        },
        "updates": update_reports,
        "update_count": learner.update_count,
        "checkpoint": checkpoint,
        "parameter_sha256": parameter_sha256,
        "validation_prediction_digest": validation_digest,
        "reloaded_parameter_sha256": reloaded_parameter_sha256,
        "reloaded_validation_prediction_digest": reloaded_validation_digest,
        "reload_bitwise_equal": bitwise_equal,
        "restored_update_count": restored_updates,
        "validation_predictions": prediction_receipt,
        "test_split_opened": False,
        "episode_training": False,
        "scientific_gate_evaluated": False,
    }
    return _write_result(destination, result_body)


def run_initialization_panel(
    panel: VerifiedSourcePanel,
    config: RelationalLearnerRunConfig,
    *,
    output_root: str | Path,
) -> dict[int, dict[str, object]]:
    """Run all externally declared initialisations; no seed is inferred."""

    destination = Path(output_root)
    if destination.exists() or destination.is_symlink():
        raise RelationalLearnerRunnerError(
            f"refusing to overwrite learner panel output: {destination}"
        )
    destination.mkdir(parents=True, exist_ok=False)
    results: dict[int, dict[str, object]] = {}
    for seed in config.initialization_seeds:
        results[seed] = run_initialization(
            panel,
            config,
            initialization_seed=seed,
            output_dir=destination / f"init-{seed}",
        )
    return results


def _verify_frozen_contract(path: str | Path, expected_sha256: str) -> str:
    contract = Path(path)
    if contract.is_symlink() or not contract.is_file():
        raise RelationalLearnerRunnerError(
            f"expected a regular learner contract file: {contract}"
        )
    expected = _digest(expected_sha256, field="contract_sha256")
    actual = _file_sha256(contract)
    if actual != expected:
        raise RelationalLearnerRunnerError(
            "learner contract digest disagrees with run config"
        )
    try:
        text = contract.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise RelationalLearnerRunnerError("learner contract is not readable text") from error
    if "FROZEN_BEFORE_OUTCOME" not in text:
        raise RelationalLearnerRunnerError(
            "learner contract is not marked FROZEN_BEFORE_OUTCOME"
        )
    return actual


def run_from_config_file(
    *,
    contract_path: str | Path,
    config_path: str | Path,
    output_root: str | Path,
) -> dict[str, object]:
    """Execute the declared mechanical panel from an external config file."""

    config_file = Path(config_path)
    if config_file.is_symlink() or not config_file.is_file():
        raise RelationalLearnerRunnerError(
            f"expected a regular run config file: {config_file}"
        )
    config, train_paths, validation_paths = read_run_config(config_file)
    contract_sha256 = _verify_frozen_contract(
        contract_path, config.contract_sha256
    )
    panel = load_verified_source_panel(
        train_paths,
        validation_paths,
        train_worlds=config.train_worlds,
        validation_worlds=config.validation_worlds,
        lineages=tuple(lineage for _seed, lineage in config.initialization_lineages),
    )
    harvest_bindings_sha256 = verify_harvest_source_panel_bindings(
        panel,
        config,
        (*train_paths, *validation_paths),
    )
    results = run_initialization_panel(panel, config, output_root=output_root)
    root = Path(output_root)
    panel_body = {
        "schema": f"{RUNNER_SCHEMA}-panel",
        "version": RUNNER_VERSION,
        "status": "MECHANICAL_ARTIFACT_WRITTEN",
        "contract_sha256": contract_sha256,
        "config_sha256": _file_sha256(config_file),
        "code_manifest_sha256": config.code_manifest_sha256,
        "output_unit_mode": config.output_unit_mode,
        "source_panel_sha256": panel.source_sha256,
        "harvest_bindings_sha256": harvest_bindings_sha256,
        "initializations": [
            {
                "initialization_seed": seed,
                "lineage": config.initialization_lineage_map[seed],
                "result": f"init-{seed}/result.json",
                "checkpoint_sha256": result["checkpoint"]["checkpoint_sha256"],
                "parameter_sha256": result["parameter_sha256"],
                "validation_prediction_digest": result[
                    "validation_prediction_digest"
                ],
            }
            for seed, result in sorted(results.items())
        ],
        "test_split_opened": False,
        "episode_training": False,
        "scientific_gate_evaluated": False,
    }
    return _write_result(root, panel_body)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, help="frozen learner contract")
    parser.add_argument("--config", required=True, help="external run config JSON")
    parser.add_argument("--output", required=True, help="new output root")
    arguments = parser.parse_args(argv)
    try:
        run_from_config_file(
            contract_path=arguments.contract,
            config_path=arguments.config,
            output_root=arguments.output,
        )
    except (OSError, RelationalLearnerRunnerError) as error:
        parser.error(str(error))
    return 0


__all__ = [
    "LearnerBatchSpec",
    "CONFIG_SCHEMA",
    "CONFIG_VERSION",
    "PREDICTION_METADATA_FILENAME",
    "PREDICTION_NPZ_FILENAME",
    "PREDICTION_RECEIPT_FILENAME",
    "REQUIRED_UPDATES",
    "RUNNER_SCHEMA",
    "RelationalLearnerRunConfig",
    "RelationalLearnerRunnerError",
    "VerifiedSourceClosure",
    "VerifiedSourcePanel",
    "canonical_sha256",
    "load_verified_source_panel",
    "read_validation_predictions",
    "read_run_config",
    "run_initialization",
    "run_initialization_panel",
    "run_from_config_file",
    "verify_harvest_source_panel_bindings",
]


if __name__ == "__main__":  # pragma: no cover - exercised by a future server
    raise SystemExit(_main())
