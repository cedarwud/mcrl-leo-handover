"""Validation-only training ladder for the no-EE E1 instrument gate.

E1 trains exactly three independent pairwise Q functions on frozen training
rows.  This module deliberately receives no test batch and no environment, so
neither held-out test results nor EE can influence the selected update rung.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
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
    EEAxisPairwiseConfig,
    EEAxisPairwiseTrainer,
    ROUTE_NAMES,
)
from ..errors import MCRLContractError
from .ee_axis_instrument_validity import (
    EEAxisActionGraphCoverageError,
    compute_pair_generalization,
)


E1_LADDER_SCHEMA = "multi-catfish-mcrl-v03-e1-validation-ladder-v1"
E1_LADDER_CHECKPOINT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-validation-ladder-checkpoint-v1"
)
E1_UPDATE_RUNGS = (10, 100, 1_000, 10_000)
E1_CLAIM_CEILING = "NO_EE_INSTRUMENT_VALIDITY_ONLY"


class E1LadderError(MCRLContractError):
    """The E1 ladder, its validation data, or a checkpoint is invalid."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise E1LadderError(f"{field} must be lowercase SHA-256")
    return value


def learner_config_sha256(config: EEAxisPairwiseConfig) -> str:
    if not isinstance(config, EEAxisPairwiseConfig):
        raise E1LadderError("config must be an EEAxisPairwiseConfig")
    encoded = json.dumps(
        asdict(config),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise E1LadderError(f"{field} must be a nonnegative integer")
    return value


def _array_digest(array: np.ndarray) -> str:
    value = np.ascontiguousarray(np.asarray(array))
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(json.dumps(value.shape, separators=(",", ":")).encode("ascii"))
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def pair_batch_digest(batch: EEAxisPairBatch) -> str:
    """Return a deterministic digest over one immutable learner view."""

    if not isinstance(batch, EEAxisPairBatch):
        raise E1LadderError("E1 split contains a non-pair batch")
    payload = {
        "states": _array_digest(batch.states),
        "reference_actions": _array_digest(batch.reference_actions),
        "candidate_actions": _array_digest(batch.candidate_actions),
        "target_surplus_bits": _array_digest(batch.target_surplus_bits),
        "action_masks": _array_digest(batch.action_masks),
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class E1LadderBatches:
    """Frozen train/validation learner views in canonical C1/C2/C3 order."""

    train: tuple[EEAxisPairBatch, EEAxisPairBatch, EEAxisPairBatch]
    validation: tuple[EEAxisPairBatch, EEAxisPairBatch, EEAxisPairBatch]

    def verify(self, config: EEAxisPairwiseConfig) -> None:
        if not isinstance(config, EEAxisPairwiseConfig):
            raise E1LadderError("config must be an EEAxisPairwiseConfig")
        if len(self.train) != 3 or len(self.validation) != 3:
            raise E1LadderError("E1 requires exactly C1/C2/C3 train and validation batches")
        for split_name, batches in (
            ("train", self.train),
            ("validation", self.validation),
        ):
            for route, batch in zip(ROUTE_NAMES, batches, strict=True):
                if not isinstance(batch, EEAxisPairBatch):
                    raise E1LadderError(f"{split_name}/{route} is not a pair batch")
                try:
                    batch.validate(
                        state_dim=config.state_dim,
                        action_dim=config.action_dim,
                    )
                except (MCRLContractError, TypeError, ValueError) as error:
                    raise E1LadderError(
                        f"{split_name}/{route} batch is invalid: {error}"
                    ) from error
                if np.asarray(batch.states).shape[0] < 1:
                    raise E1LadderError(f"{split_name}/{route} batch is empty")
        digests = self.digests()
        for route in ROUTE_NAMES:
            if digests["train"][route] == digests["validation"][route]:
                raise E1LadderError(
                    f"{route} train and validation learner batches are identical"
                )

    def batch(self, split: str, route: str) -> EEAxisPairBatch:
        if split not in {"train", "validation"}:
            raise E1LadderError("ladder may access only train or validation")
        try:
            route_index = ROUTE_NAMES.index(route)
        except ValueError as error:
            raise E1LadderError(f"unknown route {route!r}") from error
        return (self.train if split == "train" else self.validation)[route_index]

    def digests(self) -> dict[str, dict[str, str]]:
        return {
            split: {
                route: pair_batch_digest(self.batch(split, route))
                for route in ROUTE_NAMES
            }
            for split in ("train", "validation")
        }


@dataclass(frozen=True)
class E1LadderSpec:
    """All choices that must be fixed before validation learning starts."""

    run_id: str
    initialization_seeds: tuple[int, int, int]
    source_prereg_sha256: str
    source_manifest_sha256: str
    checkpoint_sha256: str
    source_receipt_file_sha256: str
    ladder_index_file_sha256: str
    learner_config_sha256: str
    train_source_seeds: tuple[int, int, int]
    validation_source_seeds: tuple[int]
    train_batch_sha256s: tuple[str, str, str]
    validation_batch_sha256s: tuple[str, str, str]
    update_rungs: tuple[int, int, int, int] = E1_UPDATE_RUNGS
    route_order: tuple[str, str, str] = ROUTE_NAMES
    claim_ceiling: str = E1_CLAIM_CEILING

    def verify(self) -> None:
        if (
            not isinstance(self.run_id, str)
            or not self.run_id.strip()
            or self.run_id != self.run_id.strip()
        ):
            raise E1LadderError("run_id must be a nonempty trimmed string")
        if (
            len(self.initialization_seeds) != 3
            or len(set(self.initialization_seeds)) != 3
        ):
            raise E1LadderError("E1 requires exactly three distinct initialization seeds")
        for index, seed in enumerate(self.initialization_seeds):
            _exact_nonnegative_int(seed, field=f"initialization_seeds[{index}]")
        for field in (
            "source_prereg_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "source_receipt_file_sha256",
            "ladder_index_file_sha256",
            "learner_config_sha256",
        ):
            _digest(getattr(self, field), field=field)
        if len(self.train_source_seeds) != 3 or len(set(self.train_source_seeds)) != 3:
            raise E1LadderError("E1 ladder requires three distinct train source seeds")
        if len(self.validation_source_seeds) != 1:
            raise E1LadderError("E1 ladder requires exactly one validation source seed")
        for field, seeds in (
            ("train_source_seeds", self.train_source_seeds),
            ("validation_source_seeds", self.validation_source_seeds),
        ):
            for index, seed in enumerate(seeds):
                _exact_nonnegative_int(seed, field=f"{field}[{index}]")
        if set(self.train_source_seeds) & set(self.validation_source_seeds):
            raise E1LadderError("train and validation source seeds overlap")
        for field in ("train_batch_sha256s", "validation_batch_sha256s"):
            values = getattr(self, field)
            if len(values) != 3:
                raise E1LadderError(f"{field} must bind C1/C2/C3")
            for index, value in enumerate(values):
                _digest(value, field=f"{field}[{index}]")
        if any(
            train == validation
            for train, validation in zip(
                self.train_batch_sha256s,
                self.validation_batch_sha256s,
                strict=True,
            )
        ):
            raise E1LadderError("a train batch is identical to its validation batch")
        if self.update_rungs != E1_UPDATE_RUNGS:
            raise E1LadderError(
                f"E1 update_rungs must equal the sealed ladder {E1_UPDATE_RUNGS}"
            )
        if tuple(sorted(self.route_order)) != tuple(sorted(ROUTE_NAMES)):
            raise E1LadderError("route_order must contain C1, C2, and C3 exactly once")
        if self.claim_ceiling != E1_CLAIM_CEILING:
            raise E1LadderError("E1 ladder claim ceiling cannot be widened")


def _validation_metrics(
    trainer: EEAxisPairwiseTrainer,
    batches: E1LadderBatches,
) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for route_index, route in enumerate(ROUTE_NAMES):
        train = batches.batch("train", route)
        validation = batches.batch("validation", route)
        q_surface = trainer.q_values(validation.states)[route_index]
        try:
            report = compute_pair_generalization(
                train_reference_actions=train.reference_actions,
                train_candidate_actions=train.candidate_actions,
                train_targets=np.asarray(train.target_surplus_bits, dtype=np.float64)
                / float(trainer.config.kappa_bits),
                heldout_reference_actions=validation.reference_actions,
                heldout_candidate_actions=validation.candidate_actions,
                heldout_targets=np.asarray(
                    validation.target_surplus_bits, dtype=np.float64
                )
                / float(trainer.config.kappa_bits),
                heldout_q_surface=q_surface,
                action_dim=trainer.config.action_dim,
            )
        except EEAxisActionGraphCoverageError as error:
            raise E1LadderError(
                f"INSUFFICIENT_COVERAGE: {route} validation action graph"
            ) from error
        baseline = float(report.action_only_baseline_mae)
        model = float(report.model_mae)
        if not math.isfinite(baseline) or baseline <= 0.0:
            raise E1LadderError(
                f"validation action-only baseline has no positive error for {route}"
            )
        ratio = model / baseline
        if not math.isfinite(ratio):
            raise E1LadderError(f"validation MAE ratio is non-finite for {route}")
        result[route] = {
            "model_mae": model,
            "action_only_baseline_mae": baseline,
            "model_to_action_only_mae_ratio": float(ratio),
        }
    return result


def select_common_validation_rung(
    rung_receipts: Mapping[int, Mapping[int, Mapping[str, Mapping[str, float]]]],
    *,
    expected_initialization_seeds: tuple[int, int, int],
    expected_rungs: tuple[int, int, int, int] = E1_UPDATE_RUNGS,
) -> tuple[int, dict[int, float]]:
    """Select one common rung using validation ratios only.

    The outer key is initialization seed, the second key is rung, and each
    route payload must contain ``model_to_action_only_mae_ratio``.  Exact ties
    are resolved toward the smaller rung as preregistered.
    """

    if set(rung_receipts) != set(expected_initialization_seeds):
        raise E1LadderError("validation receipts do not match initialization seeds")
    means: dict[int, float] = {}
    for rung in expected_rungs:
        values: list[float] = []
        for seed in expected_initialization_seeds:
            seed_receipts = rung_receipts[seed]
            if set(seed_receipts) != set(expected_rungs):
                raise E1LadderError("validation receipts do not cover every sealed rung")
            routes = seed_receipts[rung]
            if set(routes) != set(ROUTE_NAMES):
                raise E1LadderError("validation receipt does not contain C1/C2/C3")
            for route in ROUTE_NAMES:
                value = routes[route].get("model_to_action_only_mae_ratio")
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    raise E1LadderError("validation receipt contains a non-finite MAE ratio")
                values.append(float(value))
        means[rung] = float(np.mean(values))
    selected = min(expected_rungs, key=lambda rung: (means[rung], rung))
    return selected, means


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
        raise E1LadderError(f"refusing to overwrite E1 checkpoint: {path}")
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


def run_e1_validation_ladder(
    *,
    config: EEAxisPairwiseConfig,
    batches: E1LadderBatches,
    spec: E1LadderSpec,
    output_dir: str | Path,
    device: str = "cpu",
) -> dict[str, Any]:
    """Train all three initializations and select a validation-only rung."""

    spec.verify()
    batches.verify(config)
    if spec.learner_config_sha256 != learner_config_sha256(config):
        raise E1LadderError("runtime learner config disagrees with sealed E1 spec")
    observed_digests = batches.digests()
    observed_train = tuple(observed_digests["train"][route] for route in ROUTE_NAMES)
    observed_validation = tuple(
        observed_digests["validation"][route] for route in ROUTE_NAMES
    )
    if (
        observed_train != spec.train_batch_sha256s
        or observed_validation != spec.validation_batch_sha256s
    ):
        raise E1LadderError("runtime train/validation batches disagree with sealed E1 spec")
    destination = Path(output_dir)
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise E1LadderError("E1 ladder output directory already exists") from error
    checkpoints = destination / "checkpoints"
    checkpoints.mkdir()
    batch_digests = batches.digests()
    started = time.perf_counter()
    receipts: dict[int, dict[int, dict[str, dict[str, float]]]] = {}
    _write_json_atomic(
        destination / "status.json",
        {
            "schema": E1_LADDER_SCHEMA,
            "status": "running",
            "spec": asdict(spec),
            "config": asdict(config),
            "batch_digests": batch_digests,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "completed_initializations": 0,
            "completed_updates_per_head": 0,
        },
    )
    for seed_index, seed in enumerate(spec.initialization_seeds):
        trainer = EEAxisPairwiseTrainer(config, train_seed=seed, device=device)
        seed_receipts: dict[int, dict[str, dict[str, float]]] = {}
        completed = 0
        for rung in spec.update_rungs:
            for update in range(completed + 1, rung + 1):
                for route in spec.route_order:
                    trainer.update_route(route, batches.batch("train", route))
                if update % 100 == 0 and update != rung:
                    _write_json_atomic(
                        destination / "status.json",
                        {
                            "schema": E1_LADDER_SCHEMA,
                            "status": "running",
                            "spec": asdict(spec),
                            "config": asdict(config),
                            "batch_digests": batch_digests,
                            "test_split_opened": False,
                            "held_out_ee_evaluated": False,
                            "completed_initializations": seed_index,
                            "active_initialization_seed": seed,
                            "completed_updates_per_head": update,
                            "last_completed_rung": completed,
                            "elapsed_s": time.perf_counter() - started,
                        },
                    )
            completed = rung
            metrics = _validation_metrics(trainer, batches)
            seed_receipts[rung] = metrics
            _save_checkpoint(
                checkpoints / f"init-{seed}-rung-{rung:06d}.pt",
                {
                    "schema": E1_LADDER_CHECKPOINT_SCHEMA,
                    "spec": asdict(spec),
                    "batch_digests": batch_digests,
                    "initialization_seed": seed,
                    "completed_updates_per_head": rung,
                    "validation_metrics": metrics,
                    "trainer": trainer.checkpoint_state(update_count=rung * 3),
                    "test_split_opened": False,
                    "held_out_ee_evaluated": False,
                },
            )
            _write_json_atomic(
                destination / "status.json",
                {
                    "schema": E1_LADDER_SCHEMA,
                    "status": "running",
                    "spec": asdict(spec),
                    "config": asdict(config),
                    "batch_digests": batch_digests,
                    "test_split_opened": False,
                    "held_out_ee_evaluated": False,
                    "completed_initializations": seed_index,
                    "active_initialization_seed": seed,
                    "completed_updates_per_head": rung,
                    "validation_receipts": {
                        str(key): value for key, value in seed_receipts.items()
                    },
                    "elapsed_s": time.perf_counter() - started,
                },
            )
        receipts[seed] = seed_receipts
    selected_rung, mean_ratios = select_common_validation_rung(
        receipts,
        expected_initialization_seeds=spec.initialization_seeds,
        expected_rungs=spec.update_rungs,
    )
    final = {
        "schema": E1_LADDER_SCHEMA,
        "status": "complete",
        "spec": asdict(spec),
        "config": asdict(config),
        "batch_digests": batch_digests,
        "validation_receipts": {
            str(seed): {str(rung): value for rung, value in seed_rows.items()}
            for seed, seed_rows in receipts.items()
        },
        "mean_validation_model_to_action_only_mae_ratio": {
            str(rung): value for rung, value in mean_ratios.items()
        },
        "selected_common_rung": selected_rung,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "elapsed_s": time.perf_counter() - started,
    }
    _write_json_atomic(destination / "status.json", final)
    return final


__all__ = [
    "E1_CLAIM_CEILING",
    "E1_LADDER_CHECKPOINT_SCHEMA",
    "E1_LADDER_SCHEMA",
    "E1_UPDATE_RUNGS",
    "E1LadderBatches",
    "E1LadderError",
    "E1LadderSpec",
    "pair_batch_digest",
    "learner_config_sha256",
    "run_e1_validation_ladder",
    "select_common_validation_rung",
]
