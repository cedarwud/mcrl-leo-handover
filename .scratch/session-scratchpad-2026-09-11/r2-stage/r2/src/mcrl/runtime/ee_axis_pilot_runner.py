"""Bounded source-epoch runner for the V0.3 learnability pilot.

One pilot episode is defined here as exactly one diagonal C1/C2/C3 update
cycle over frozen source batches.  This runner measures plumbing, numerical
learnability, checkpointing, and runtime only.  Held-out ratio-of-sums EE is
an external evaluation gate and is deliberately not inferred from pair loss.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Mapping

import numpy as np
import torch

from ..algorithms.ee_axis_pairwise import (
    EEAxisPairBatch,
    EEAxisPairwiseTrainer,
    ROUTE_NAMES,
)
from ..errors import MCRLContractError
from .ee_axis_training_schedule import (
    EEAxisThreeRouteBatches,
    update_three_route_cycle,
)


PILOT_RUN_SCHEMA = "multi-catfish-mcrl-v03-bounded-pilot-run-v1"
PILOT_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v03-bounded-pilot-checkpoint-v1"


class EEAxisPilotRunnerError(MCRLContractError):
    """The bounded pilot schedule or checkpoint violates its contract."""


@dataclass(frozen=True)
class EEAxisPilotRunSpec:
    """Frozen engineering schedule; it does not encode an efficacy threshold."""

    run_id: str
    episodes: int
    checkpoint_every_episodes: int = 100
    route_order: tuple[str, str, str] = ROUTE_NAMES
    claim_ceiling: str = "BOUNDED_LEARNABILITY_AND_RUNTIME_ONLY_NOT_EE_EFFICACY"

    def verify(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id.strip() or self.run_id != self.run_id.strip():
            raise EEAxisPilotRunnerError("run_id must be a nonempty trimmed string")
        if type(self.episodes) is not int or not 1 <= self.episodes <= 20:
            raise EEAxisPilotRunnerError("bounded pilot episodes must be in [1,20]")
        if type(self.checkpoint_every_episodes) is not int or self.checkpoint_every_episodes <= 0:
            raise EEAxisPilotRunnerError("checkpoint cadence must be positive")
        if tuple(sorted(self.route_order)) != tuple(sorted(ROUTE_NAMES)):
            raise EEAxisPilotRunnerError("route_order must contain C1, C2, C3 exactly once")
        if self.claim_ceiling != "BOUNDED_LEARNABILITY_AND_RUNTIME_ONLY_NOT_EE_EFFICACY":
            raise EEAxisPilotRunnerError("bounded pilot claim ceiling cannot be widened")


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
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


def _save_checkpoint(path: Path, payload: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise EEAxisPilotRunnerError(f"refusing to overwrite checkpoint: {path}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(dict(payload), temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _batch_digests(batches: EEAxisThreeRouteBatches) -> dict[str, str]:
    return {
        "C1": batches.c1.verify(),
        "C2": batches.c2.verify(),
        "C3": batches.c3.verify(),
    }


def _pair_fit(
    trainer: EEAxisPairwiseTrainer,
    *,
    route: str,
    batch: EEAxisPairBatch,
) -> dict[str, float]:
    batch.validate(
        state_dim=trainer.config.state_dim,
        action_dim=trainer.config.action_dim,
    )
    route_index = ROUTE_NAMES.index(route)
    values = trainer.q_values(batch.states)[route_index]
    indices = np.arange(values.shape[0])
    predicted = (
        values[indices, np.asarray(batch.candidate_actions)]
        - values[indices, np.asarray(batch.reference_actions)]
    )
    targets = np.asarray(batch.target_surplus_bits, dtype=np.float64) / float(
        trainer.config.kappa_bits
    )
    residual = np.asarray(predicted, dtype=np.float64) - targets
    mse = float(np.mean(np.square(residual)))
    mae = float(np.mean(np.abs(residual)))
    if not math.isfinite(mse) or not math.isfinite(mae):
        raise EEAxisPilotRunnerError(f"{route} fit diagnostic is non-finite")
    return {"pair_mse": mse, "pair_mae": mae}


def _all_fit(
    trainer: EEAxisPairwiseTrainer,
    batches: EEAxisThreeRouteBatches,
) -> dict[str, dict[str, float]]:
    return {
        "C1": _pair_fit(trainer, route="C1", batch=batches.c1.pair_batch),
        "C2": _pair_fit(trainer, route="C2", batch=batches.c2.pair_batch),
        "C3": _pair_fit(trainer, route="C3", batch=batches.c3.pair_batch),
    }


def load_pairwise_pilot_checkpoint(
    path: str | Path,
    *,
    trainer: EEAxisPairwiseTrainer,
    expected_spec: EEAxisPilotRunSpec,
    expected_batch_digests: Mapping[str, str],
) -> int:
    expected_spec.verify()
    try:
        payload = torch.load(Path(path), map_location=trainer.device, weights_only=False)
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        raise EEAxisPilotRunnerError("cannot load V0.3 pilot checkpoint") from error
    if not isinstance(payload, Mapping) or payload.get("schema") != PILOT_CHECKPOINT_SCHEMA:
        raise EEAxisPilotRunnerError("checkpoint is not a V0.3 pilot checkpoint")
    if payload.get("spec") != asdict(expected_spec):
        raise EEAxisPilotRunnerError("pilot checkpoint schedule disagrees")
    if payload.get("batch_digests") != dict(expected_batch_digests):
        raise EEAxisPilotRunnerError("pilot checkpoint source batches disagree")
    completed = payload.get("completed_episodes")
    if type(completed) is not int or not 0 <= completed <= expected_spec.episodes:
        raise EEAxisPilotRunnerError("pilot checkpoint episode is invalid")
    trainer_state = payload.get("trainer")
    if not isinstance(trainer_state, Mapping):
        raise EEAxisPilotRunnerError("pilot checkpoint lacks trainer state")
    update_count = trainer.load_checkpoint_state(trainer_state)
    if update_count != completed * len(ROUTE_NAMES):
        raise EEAxisPilotRunnerError("pilot checkpoint update count disagrees")
    return completed


def run_pairwise_pilot(
    trainer: EEAxisPairwiseTrainer,
    batches: EEAxisThreeRouteBatches,
    *,
    spec: EEAxisPilotRunSpec,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Run a new, write-once bounded pilot and return its final status."""

    if not isinstance(trainer, EEAxisPairwiseTrainer):
        raise EEAxisPilotRunnerError("trainer must be EEAxisPairwiseTrainer")
    if not isinstance(batches, EEAxisThreeRouteBatches):
        raise EEAxisPilotRunnerError("batches must be EEAxisThreeRouteBatches")
    spec.verify()
    batches.verify(trainer)
    destination = Path(output_dir)
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise EEAxisPilotRunnerError("pilot output directory already exists") from error
    checkpoints = destination / "checkpoints"
    checkpoints.mkdir()
    digests = _batch_digests(batches)
    initial_fit = _all_fit(trainer, batches)
    started = time.perf_counter()
    metrics: list[dict[str, Any]] = []
    _write_json_atomic(
        destination / "status.json",
        {
            "schema": PILOT_RUN_SCHEMA,
            "status": "running",
            "spec": asdict(spec),
            "batch_digests": digests,
            "episodes_completed": 0,
            "updates_completed": 0,
            "initial_fit": initial_fit,
        },
    )
    for episode in range(1, spec.episodes + 1):
        episode_started = time.perf_counter()
        receipts = update_three_route_cycle(
            trainer, batches, order=spec.route_order
        )
        fit = _all_fit(trainer, batches)
        metrics.append(
            {
                "episode": episode,
                "updates_completed": episode * len(ROUTE_NAMES),
                "receipts": [dict(receipt) for receipt in receipts],
                "fit": fit,
                "elapsed_s": time.perf_counter() - episode_started,
            }
        )
        if episode % spec.checkpoint_every_episodes == 0 or episode == spec.episodes:
            _save_checkpoint(
                checkpoints / f"checkpoint-episode-{episode:06d}.pt",
                {
                    "schema": PILOT_CHECKPOINT_SCHEMA,
                    "spec": asdict(spec),
                    "batch_digests": digests,
                    "completed_episodes": episode,
                    "trainer": trainer.checkpoint_state(
                        update_count=episode * len(ROUTE_NAMES)
                    ),
                },
            )
        _write_json_atomic(
            destination / "status.json",
            {
                "schema": PILOT_RUN_SCHEMA,
                "status": "running" if episode < spec.episodes else "complete",
                "spec": asdict(spec),
                "batch_digests": digests,
                "episodes_completed": episode,
                "updates_completed": episode * len(ROUTE_NAMES),
                "initial_fit": initial_fit,
                "final_fit": fit,
                "metrics": metrics,
                "elapsed_s": time.perf_counter() - started,
                "held_out_ee_evaluated": False,
            },
        )
    return json.loads((destination / "status.json").read_text(encoding="ascii"))


__all__ = [
    "EEAxisPilotRunSpec",
    "EEAxisPilotRunnerError",
    "PILOT_CHECKPOINT_SCHEMA",
    "PILOT_RUN_SCHEMA",
    "load_pairwise_pilot_checkpoint",
    "run_pairwise_pilot",
]
