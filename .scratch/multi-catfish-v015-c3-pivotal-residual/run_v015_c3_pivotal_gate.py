#!/usr/bin/env python3
"""Source-only V0.15 C3 pivotal residual-ranking gate.

This command is intentionally prepared but not launched by the development
task.  It consumes already authenticated V0.14 compact source shards and
frozen V0.14 Q2 rung-3000 checkpoints.  It never advances the simulator,
opens TEST, or evaluates a trajectory.  Only Q3 is learned; Q1 and the
learned Q2 surface form a detached background for source-label construction
and validation diagnostics.

The gate must receive a separately reviewed/frozen preregistration before a
server invocation.  Its defaults are only mechanical development defaults,
not an authorization to run a multi-lineage panel.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_v014_head import (  # noqa: E402
    EEAxisV014HeadConfig,
    V014ActionSetQNetwork,
)
from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_v015_c3_pivotal import (  # noqa: E402
    C3PivotalContractError,
    EEAxisV015C3PivotalLearner,
    V015C3PivotalPairs,
    build_pivotal_pairs,
    evaluate_pivotal_decisions,
)


# Reuse only the authenticated V0.14 source reader/merger.  Importing this
# module does not construct or advance an environment; the source paths are
# still verified as TRAIN-only by load_source_shards.
V014_GATE_PATH = REPO / ".scratch" / "multi-catfish-v014-learner" / "run_v014_learner_gate.py"
_V014_SPEC = importlib.util.spec_from_file_location("mcrl_v014_gate_source_reader", V014_GATE_PATH)
if _V014_SPEC is None or _V014_SPEC.loader is None:
    raise RuntimeError(f"cannot load V0.14 source reader: {V014_GATE_PATH}")
_V014_MODULE = importlib.util.module_from_spec(_V014_SPEC)
sys.modules[_V014_SPEC.name] = _V014_MODULE
_V014_SPEC.loader.exec_module(_V014_MODULE)
load_source_shards = _V014_MODULE.load_source_shards


RUNNER_SCHEMA = "multi-catfish-mcrl-v015-c3-pivotal-residual-ranking-gate-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v015-c3-pivotal-residual-ranking-result-v1"
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v015-c3-pivotal-residual-ranking-checkpoint-v1"
CLAIM_CEILING = "NO_DEPLOYED_EFFICACY_OR_EE_CLAIM"

ACTION_DIM = 28
DEFAULT_TRAIN_WORLD_SEEDS = (2026108001, 2026108002, 2026108003, 2026108004)
DEFAULT_VALIDATION_WORLD_SEEDS = (2026108005, 2026108006, 2026108007)
DEFAULT_INITIALIZATION_SEEDS = (2026108101, 2026108102, 2026108103)
DEFAULT_SOURCE_LINEAGES = (2026092101, 2026092102, 2026092103)
DEFAULT_UPDATE_RUNGS = (3, 10, 30, 100, 300, 1000, 3000)
DEFAULT_BATCH_SIZE = 512
DEFAULT_HIDDEN_LAYERS = (100, 50, 50)
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_BETA = 0.1

Q2_CHECKPOINT_ROOT = (
    REPO
    / "artifacts"
    / "multi-catfish-v014-learnability-20260903-r1"
    / "server-run"
    / "learner-gate"
    / "checkpoints"
)
Q2_CHECKPOINTS = {
    2026108101: (
        Q2_CHECKPOINT_ROOT / "init-2026108101-rung-003000.pt",
        "d981232a9e56e6ce71c8e8b1fda789efc69852d4a6a22e918a2992ddc58a533d",
    ),
    2026108102: (
        Q2_CHECKPOINT_ROOT / "init-2026108102-rung-003000.pt",
        "9a45f5bc125d6ba453d7d74dbc640ec3d2e927fffb161518e383e6b3aabbe8ef",
    ),
    2026108103: (
        Q2_CHECKPOINT_ROOT / "init-2026108103-rung-003000.pt",
        "8f9d2e5d1749515a0896137082b1430419ae1b8a794d28ea772a23c86648be81",
    ),
}


class V015C3PivotalGateError(MCRLContractError):
    """A source, checkpoint, or write-once gate boundary failed."""


@dataclass(frozen=True)
class FrozenQ2:
    initialization_seed: int
    path: Path
    sha256: str
    config: EEAxisV014HeadConfig
    network: V014ActionSetQNetwork

    def values(self, states: object, masks: object) -> np.ndarray:
        values = np.asarray(states, dtype=np.float32)
        legal = np.asarray(masks)
        if values.ndim != 2 or values.shape[1] != self.config.state_dim:
            raise V015C3PivotalGateError("Q2 states do not match the frozen checkpoint")
        if legal.dtype != np.bool_ or legal.shape != (values.shape[0], ACTION_DIM):
            raise V015C3PivotalGateError("Q2 masks do not match the frozen checkpoint")
        with torch.no_grad():
            state_tensor = torch.tensor(values, dtype=torch.float32)
            mask_tensor = torch.tensor(legal, dtype=torch.bool)
            return self.network(state_tensor, mask_tensor).cpu().numpy()


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise V015C3PivotalGateError(f"expected a regular checkpoint file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_frozen_q2(initialization_seed: int) -> FrozenQ2:
    try:
        path, expected_sha256 = Q2_CHECKPOINTS[int(initialization_seed)]
    except KeyError as error:
        raise V015C3PivotalGateError(
            f"no predeclared Q2 checkpoint for initialization {initialization_seed}"
        ) from error
    actual_sha256 = _file_sha256(path)
    if actual_sha256 != expected_sha256:
        raise V015C3PivotalGateError(
            f"Q2 checkpoint hash mismatch for initialization {initialization_seed}"
        )
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, TypeError, ValueError) as error:
        raise V015C3PivotalGateError(f"cannot load Q2 checkpoint {path}") from error
    if not isinstance(payload, Mapping):
        raise V015C3PivotalGateError("Q2 checkpoint must be a mapping")
    if payload.get("schema") != "multi-catfish-mcrl-v014-supervised-learnability-checkpoint-v1":
        raise V015C3PivotalGateError("Q2 checkpoint outer schema is stale")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise V015C3PivotalGateError("Q2 checkpoint claim ceiling drifted")
    if payload.get("initialization_seed") != int(initialization_seed) or payload.get("update_rung") != 3000:
        raise V015C3PivotalGateError("Q2 checkpoint identity/rung disagrees")
    if any(bool(payload.get(field, True)) for field in ("test_split_opened", "held_out_ee_evaluated", "episode_training")):
        raise V015C3PivotalGateError("Q2 checkpoint crossed a forbidden boundary")
    inner = payload.get("q2")
    if not isinstance(inner, Mapping):
        raise V015C3PivotalGateError("Q2 checkpoint lacks nested Q2 state")
    if inner.get("algorithm") != "multi-catfish-mcrl-v014-independent-action-set-head":
        raise V015C3PivotalGateError("nested Q2 algorithm is stale")
    if inner.get("format_version") != 1 or inner.get("update_count") != 3000:
        raise V015C3PivotalGateError("nested Q2 format/rung disagrees")
    if inner.get("train_seed") != int(initialization_seed):
        raise V015C3PivotalGateError("nested Q2 train seed disagrees")
    try:
        config = EEAxisV014HeadConfig(**dict(inner["config"]))
        if config.action_dim != ACTION_DIM or config.state_dim != 448:
            raise V015C3PivotalGateError("frozen Q2 state architecture is not V0.14")
        if float(config.kappa_bits).hex() != float(OPS3_KAPPA_BITS).hex():
            raise V015C3PivotalGateError("frozen Q2 kappa disagrees")
        network = V014ActionSetQNetwork(config)
        network.load_state_dict(inner["q"])
    except (KeyError, TypeError, ValueError, RuntimeError) as error:
        raise V015C3PivotalGateError("malformed nested Q2 ActionSet state") from error
    network.eval()
    network.requires_grad_(False)
    return FrozenQ2(
        initialization_seed=int(initialization_seed),
        path=path,
        sha256=actual_sha256,
        config=config,
        network=network,
    )


def _pairs_for_split(split: Any, frozen_q2: FrozenQ2) -> tuple[V015C3PivotalPairs, np.ndarray]:
    q2_values = frozen_q2.values(split.q2.states, split.q2.masks)
    if not np.array_equal(np.asarray(split.q2.masks), np.asarray(split.q3.masks)):
        raise V015C3PivotalGateError("source Q2/Q3 masks disagree")
    pairs = build_pivotal_pairs(
        split.q3.states,
        split.q3.masks,
        split.q1_values,
        q2_values,
        split.q3.target_surfaces_bits,
        kappa_bits=OPS3_KAPPA_BITS,
    )
    return pairs, q2_values


def _batch_indices(*, rows: int, batch_size: int, update: int) -> np.ndarray:
    if rows < 1 or batch_size < 1 or update < 1:
        raise V015C3PivotalGateError("invalid deterministic batch schedule")
    start = ((update - 1) * batch_size) % rows
    return (start + np.arange(batch_size, dtype=np.int64)) % rows


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    if isinstance(value, Path):
        return str(value)
    return value


def _write_once(path: Path, payload: object) -> str:
    if path.exists() or path.is_symlink():
        raise V015C3PivotalGateError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(_jsonable(payload), indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with open(descriptor, "wb", closefd=True) as handle:
            handle.write(content)
            handle.flush()
            import os

            os.fsync(handle.fileno())
        try:
            path.parent.joinpath(Path(temporary).name).replace(path)
        except FileExistsError as error:
            raise V015C3PivotalGateError(f"refusing to overwrite {path}") from error
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass
    return _file_sha256(path)


def _write_once_torch(path: Path, payload: Mapping[str, object]) -> str:
    if path.exists() or path.is_symlink():
        raise V015C3PivotalGateError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    import os

    os.close(descriptor)
    try:
        torch.save(dict(payload), temporary)
        with open(temporary, "rb") as handle:
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass
    return _file_sha256(path)


def _q3_config() -> EEAxisV014HeadConfig:
    return EEAxisV014HeadConfig(
        action_dim=ACTION_DIM,
        local_feature_dim=10,
        global_feature_dim=7,
        hidden_layers=DEFAULT_HIDDEN_LAYERS,
        activation="tanh",
        learning_rate=DEFAULT_LEARNING_RATE,
        kappa_bits=OPS3_KAPPA_BITS,
        beta=DEFAULT_BETA,
    )


def _train_initialization(
    *,
    train_pairs: V015C3PivotalPairs,
    validation_pairs: V015C3PivotalPairs,
    validation_split: Any,
    validation_q2_values: np.ndarray,
    seed: int,
    update_rungs: Sequence[int],
    batch_size: int,
    output_dir: Path,
    q2_checkpoint: FrozenQ2,
) -> dict[str, object]:
    learner = EEAxisV015C3PivotalLearner(_q3_config(), train_seed=int(seed), device="cpu")
    reports: dict[str, object] = {}
    completed = 0
    for rung in update_rungs:
        for update in range(completed + 1, int(rung) + 1):
            indices = _batch_indices(rows=train_pairs.rows, batch_size=batch_size, update=update)
            learner.update(train_pairs.take(indices))
        completed = int(rung)
        q3_validation = learner.q_values(validation_split.q3.states, validation_split.q3.masks)
        decision = evaluate_pivotal_decisions(
            q1_values=validation_split.q1_values,
            q2_values=validation_q2_values,
            z3_target_bits=validation_split.q3.target_surfaces_bits,
            q3_values=q3_validation,
            action_masks=validation_split.q3.masks,
            kappa_bits=OPS3_KAPPA_BITS,
        )
        learnability = learner.measure(validation_pairs)
        checkpoint = {
            "schema": CHECKPOINT_SCHEMA,
            "runner_schema": RUNNER_SCHEMA,
            "claim_ceiling": CLAIM_CEILING,
            "initialization_seed": int(seed),
            "update_rung": int(rung),
            "q2_checkpoint": {
                "path": str(q2_checkpoint.path),
                "sha256": q2_checkpoint.sha256,
                "initialization_seed": q2_checkpoint.initialization_seed,
                "update_rung": 3000,
            },
            "q3": learner.checkpoint_state(update_count=int(rung)),
            "validation_decision": decision,
            "validation_learnability": learnability,
            "test_split_opened": False,
            "episode_training": False,
        }
        checkpoint_path = output_dir / "checkpoints" / f"init-{seed}-rung-{int(rung):06d}.pt"
        checkpoint_sha256 = _write_once_torch(checkpoint_path, checkpoint)
        reports[str(int(rung))] = {
            "validation_decision": decision,
            "validation_learnability": learnability,
            "checkpoint": str(checkpoint_path),
            "checkpoint_sha256": checkpoint_sha256,
        }
    return {
        "initialization_seed": int(seed),
        "train_pairs": {
            "rows": train_pairs.rows,
            "pivotal_rows": train_pairs.pivotal_rows,
            "stable_rows": train_pairs.stable_rows,
        },
        "validation_pairs": {
            "rows": validation_pairs.rows,
            "pivotal_rows": validation_pairs.pivotal_rows,
            "stable_rows": validation_pairs.stable_rows,
        },
        "rungs": reports,
    }


def run(
    *,
    source_paths: Sequence[str | Path],
    output_dir: str | Path,
    initialization_seeds: Sequence[int] = DEFAULT_INITIALIZATION_SEEDS,
    source_lineages: Sequence[int] = DEFAULT_SOURCE_LINEAGES,
    train_world_seeds: Sequence[int] = DEFAULT_TRAIN_WORLD_SEEDS,
    validation_world_seeds: Sequence[int] = DEFAULT_VALIDATION_WORLD_SEEDS,
    update_rungs: Sequence[int] = DEFAULT_UPDATE_RUNGS,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Run the prepared source-only gate after an external prereg freeze."""

    seeds = tuple(int(value) for value in initialization_seeds)
    lineages = tuple(int(value) for value in source_lineages)
    if len(seeds) != 3 or len(lineages) != 3 or len(set(seeds)) != 3 or len(set(lineages)) != 3:
        raise V015C3PivotalGateError("exactly three distinct initialisations/lineages are required")
    if tuple(sorted(int(value) for value in update_rungs)) != tuple(int(value) for value in update_rungs):
        raise V015C3PivotalGateError("update_rungs must be increasing")
    if batch_size < 1:
        raise V015C3PivotalGateError("batch_size must be positive")
    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise V015C3PivotalGateError(f"refusing to overwrite output directory {destination}")
    destination.mkdir(parents=True, exist_ok=False)

    reports: dict[str, object] = {}
    for seed, lineage in zip(seeds, lineages, strict=True):
        frozen_q2 = _load_frozen_q2(seed)
        loaded = load_source_shards(
            source_paths,
            train_world_seeds=tuple(int(value) for value in train_world_seeds),
            validation_world_seeds=tuple(int(value) for value in validation_world_seeds),
            kappa_bits=OPS3_KAPPA_BITS,
            lineage=lineage,
        )
        train_pairs, _train_q2 = _pairs_for_split(loaded.train, frozen_q2)
        validation_pairs, validation_q2 = _pairs_for_split(loaded.validation, frozen_q2)
        reports[str(seed)] = _train_initialization(
            train_pairs=train_pairs,
            validation_pairs=validation_pairs,
            validation_split=loaded.validation,
            validation_q2_values=validation_q2,
            seed=seed,
            update_rungs=tuple(int(value) for value in update_rungs),
            batch_size=batch_size,
            output_dir=destination,
            q2_checkpoint=frozen_q2,
        )

    result = {
        "schema": RESULT_SCHEMA,
        "runner_schema": RUNNER_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "source_only": True,
        "test_split_opened": False,
        "episode_training": False,
        "initialization_seeds": list(seeds),
        "source_lineages": list(lineages),
        "train_world_seeds": list(int(value) for value in train_world_seeds),
        "validation_world_seeds": list(int(value) for value in validation_world_seeds),
        "update_rungs": list(int(value) for value in update_rungs),
        "batch_size": int(batch_size),
        "reports": reports,
        "decision": "PENDING_ROOT_REVIEW_AND_PREREG",
    }
    result_path = destination / "result.json"
    result_sha256 = _write_once(result_path, result)
    receipt = {
        "schema": "multi-catfish-mcrl-v015-c3-pivotal-residual-ranking-receipt-v1",
        "result_path": str(result_path),
        "result_sha256": result_sha256,
        "claim_ceiling": CLAIM_CEILING,
    }
    _write_once(destination / "receipt.json", receipt)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--train-world-seed", action="append", type=int, default=None)
    parser.add_argument("--validation-world-seed", action="append", type=int, default=None)
    parser.add_argument("--initialization-seed", action="append", type=int, default=None)
    parser.add_argument("--source-lineage", action="append", type=int, default=None)
    parser.add_argument("--update-rung", action="append", type=int, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run(
        source_paths=args.source,
        output_dir=args.output,
        initialization_seeds=tuple(args.initialization_seed or DEFAULT_INITIALIZATION_SEEDS),
        source_lineages=tuple(args.source_lineage or DEFAULT_SOURCE_LINEAGES),
        train_world_seeds=tuple(args.train_world_seed or DEFAULT_TRAIN_WORLD_SEEDS),
        validation_world_seeds=tuple(args.validation_world_seed or DEFAULT_VALIDATION_WORLD_SEEDS),
        update_rungs=tuple(args.update_rung or DEFAULT_UPDATE_RUNGS),
        batch_size=int(args.batch_size),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
