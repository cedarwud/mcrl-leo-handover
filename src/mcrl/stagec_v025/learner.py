"""Deterministic pairwise zero-bootstrap learner and six-arm orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

import numpy as np

from .canonical import (
    StageCContractError,
    canonical_sha256,
    float_hex,
    parse_float_hex,
    read_verified_json,
    write_once_json,
)
from .shards import SourceShard
from .state import Q1_SCHEMA_SHA256, Q2_SCHEMA_SHA256, SourceRow


Route = Literal["C1", "C2", "C3"]
ROUTES: tuple[Route, ...] = ("C1", "C2", "C3")
LEARNED_ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL")
ARM_ORDER = (*LEARNED_ARMS, "BASELINE")
SOURCE_MAP: Mapping[str, Mapping[Route, str]] = {
    "FULL": {"C1": "informed", "C2": "informed", "C3": "informed"},
    "DROP_C1": {"C1": "neutral", "C2": "informed", "C3": "informed"},
    "DROP_C2": {"C1": "informed", "C2": "neutral", "C3": "informed"},
    "DROP_C3": {"C1": "informed", "C2": "informed", "C3": "neutral"},
    "ALL_NEUTRAL": {"C1": "neutral", "C2": "neutral", "C3": "neutral"},
}
CHECKPOINT_SCHEMA = "mcrl-v025-stagec-lineage-checkpoint-v1-draft"
CHECKPOINT_EVERY_SOURCE_EPOCHS = 100


@dataclass(frozen=True, slots=True)
class PairwiseBatch:
    """A typed fixed aggregate batch. There is intentionally no next state."""

    route: Route
    reference_states: np.ndarray
    candidate_states: np.ndarray
    target_deltas: np.ndarray
    row_identities: tuple[str, ...]
    source_authority_sha256: str
    digest: str

    @classmethod
    def create(
        cls,
        route: Route,
        reference_states: Sequence[Sequence[float]],
        candidate_states: Sequence[Sequence[float]],
        target_deltas: Sequence[float],
        row_identities: Sequence[str],
        source_authority_sha256: str,
    ) -> "PairwiseBatch":
        reference = np.asarray(reference_states, dtype=np.float64)
        candidate = np.asarray(candidate_states, dtype=np.float64)
        targets = np.asarray(target_deltas, dtype=np.float64)
        identities = tuple(row_identities)
        if route not in ROUTES:
            raise StageCContractError("unknown pairwise route")
        if reference.ndim != 2 or candidate.shape != reference.shape:
            raise StageCContractError("pairwise state tensors must be equal rank-2 arrays")
        if targets.shape != (reference.shape[0],) or len(identities) != reference.shape[0]:
            raise StageCContractError("pairwise target/identity count drifted")
        if (
            reference.shape[0] < 1
            or not np.isfinite(reference).all()
            or not np.isfinite(candidate).all()
            or not np.isfinite(targets).all()
        ):
            raise StageCContractError("pairwise batch must be nonempty and finite")
        if len(source_authority_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in source_authority_sha256
        ):
            raise StageCContractError("source authority must be a lowercase SHA-256")
        payload = {
            "schema": "mcrl-v025-stagec-pairwise-batch-v1-draft",
            "route": route,
            "shape": list(reference.shape),
            "reference": [[float_hex(v) for v in row] for row in reference],
            "candidate": [[float_hex(v) for v in row] for row in candidate],
            "targets": [float_hex(v) for v in targets],
            "row_identities": list(identities),
            "source_authority_sha256": source_authority_sha256,
            "zero_bootstrap": True,
        }
        return cls(
            route,
            reference,
            candidate,
            targets,
            identities,
            source_authority_sha256,
            canonical_sha256(payload),
        )

    def neutral(self) -> "PairwiseBatch":
        return PairwiseBatch.create(
            self.route,
            self.reference_states,
            self.candidate_states,
            np.zeros_like(self.target_deltas),
            self.row_identities,
            self.source_authority_sha256,
        )


def _route_state(row: SourceRow, route: Route) -> tuple[float, ...]:
    if route == "C1":
        return row.q1_state
    if route == "C2":
        return row.q2_state
    return (*row.q1_state, *row.q2_state)


def _route_label(row: SourceRow, route: Route) -> float:
    field = {
        "C1": row.c1_label_normalized_hex,
        "C2": row.c2_label_normalized_hex,
        "C3": row.c3_label_normalized_hex,
    }[route]
    return parse_float_hex(field, field=f"{route}.normalized_label")


def build_pairwise_batches(shards: Sequence[SourceShard]) -> dict[Route, PairwiseBatch]:
    rows = tuple(row for shard in shards for row in shard.rows)
    source_authority_sha256 = canonical_sha256(
        {
            "schema": "mcrl-v025-stagec-source-authority-v1-draft",
            "shards": [shard.file_sha256 for shard in shards],
            "authorities": sorted(
                {
                    (
                        row.code_digest,
                        row.physics_digest,
                        row.launch_digest,
                        row.catalogue_digest,
                        row.provider_digest,
                        row.archive_digest,
                        row.setting_digest,
                        row.calibration_digest,
                        row.allocation_manifest_digest,
                        row.q1_schema_sha256,
                        row.q2_schema_sha256,
                    )
                    for row in rows
                }
            ),
        }
    )
    groups: dict[tuple[str, str, int], list[SourceRow]] = {}
    for row in rows:
        groups.setdefault((row.world_id, row.anchor_id, row.user_id), []).append(row)
    by_route: dict[Route, PairwiseBatch] = {}
    for route in ROUTES:
        references: list[tuple[float, ...]] = []
        candidates: list[tuple[float, ...]] = []
        targets: list[float] = []
        identities: list[str] = []
        for key in sorted(groups):
            ordered = sorted(groups[key], key=lambda row: row.action_index)
            shared_mask = ordered[0].action_mask
            if any(row.action_mask != shared_mask for row in ordered):
                raise StageCContractError("user-anchor rows disagree on the legal mask")
            expected_indices = [
                index for index, enabled in enumerate(shared_mask) if enabled
            ]
            if [row.action_index for row in ordered] != expected_indices:
                raise StageCContractError("user-anchor rows do not cover each legal action once")
            if sum(row.null_action for row in ordered) != 1:
                raise StageCContractError("user-anchor requires exactly one legal null action")
            reference_rows = [row for row in ordered if row.reference_action]
            if len(reference_rows) != 1:
                raise StageCContractError("every user-anchor requires exactly one BASE row")
            reference = reference_rows[0]
            for candidate in ordered:
                if candidate.reference_action or not candidate.action_mask[candidate.action_index]:
                    continue
                references.append(_route_state(reference, route))
                candidates.append(_route_state(candidate, route))
                targets.append(_route_label(candidate, route) - _route_label(reference, route))
                identities.append(
                    f"{candidate.world_id}|{candidate.anchor_id}|{candidate.user_id}|{candidate.action_index}"
                )
        by_route[route] = PairwiseBatch.create(
            route,
            references,
            candidates,
            targets,
            identities,
            source_authority_sha256,
        )
    return by_route


@dataclass(slots=True)
class LinearHead:
    weights: np.ndarray
    bias: float

    def clone(self) -> "LinearHead":
        return LinearHead(self.weights.copy(), float(self.bias))

    def score(self, state: Sequence[float]) -> float:
        values = np.asarray(state, dtype=np.float64)
        if values.shape != self.weights.shape:
            raise StageCContractError("learner state shape drifted")
        return float(values @ self.weights + self.bias)

    def update(self, batch: PairwiseBatch, *, learning_rate: float, gauge_weight: float) -> float:
        # Pairwise fixed-target regression with a reference-zero gauge. No
        # reward, next state, target network, discount, or bootstrap exists.
        reference_q = batch.reference_states @ self.weights + self.bias
        candidate_q = batch.candidate_states @ self.weights + self.bias
        residual = candidate_q - reference_q - batch.target_deltas
        count = float(batch.target_deltas.size)
        gradient_w = (2.0 / count) * ((batch.candidate_states - batch.reference_states).T @ residual)
        gradient_w += (2.0 * gauge_weight / count) * (batch.reference_states.T @ reference_q)
        gradient_b = float((2.0 * gauge_weight / count) * reference_q.sum())
        self.weights -= learning_rate * gradient_w
        self.bias -= learning_rate * gradient_b
        loss = float(np.mean(residual * residual) + gauge_weight * np.mean(reference_q * reference_q))
        if not np.isfinite(self.weights).all() or not np.isfinite(self.bias) or not np.isfinite(loss):
            raise StageCContractError("non-finite learner update")
        return loss


@dataclass(slots=True)
class ThreeRouteModel:
    heads: dict[Route, LinearHead]

    def clone(self) -> "ThreeRouteModel":
        return ThreeRouteModel({route: head.clone() for route, head in self.heads.items()})

    def score(self, route: Route, state: Sequence[float]) -> float:
        return self.heads[route].score(state)

    def payload(self) -> dict[str, object]:
        return {
            route: {
                "weights_hex": [float_hex(value) for value in self.heads[route].weights],
                "bias_hex": float_hex(self.heads[route].bias),
            }
            for route in ROUTES
        }


def _initial_model(seed: int, dimensions: Mapping[Route, int]) -> ThreeRouteModel:
    rng = np.random.default_rng(seed)
    return ThreeRouteModel(
        {
            route: LinearHead(rng.normal(0.0, 0.01, dimensions[route]), 0.0)
            for route in ROUTES
        }
    )


class LineageOrchestrator:
    """Five matched learned arms plus an external BASELINE policy."""

    def __init__(
        self,
        *,
        learner_seed: int,
        batches: Mapping[Route, PairwiseBatch],
        learning_rate: float = 0.02,
        gauge_weight: float = 0.01,
    ) -> None:
        if set(batches) != set(ROUTES):
            raise StageCContractError("orchestrator needs exactly C1/C2/C3 batches")
        self.learner_seed = int(learner_seed)
        self.batches = dict(batches)
        self.learning_rate = float(learning_rate)
        self.gauge_weight = float(gauge_weight)
        dimensions = {route: batch.reference_states.shape[1] for route, batch in batches.items()}
        template = _initial_model(self.learner_seed, dimensions)
        self.initialization_payload = template.payload()
        self.initialization_sha256 = canonical_sha256(self.initialization_payload)
        self.models = {arm: template.clone() for arm in LEARNED_ARMS}
        self.completed_source_epochs = 0
        self.route_update_count = 0
        self.loss_history: list[dict[str, object]] = []

    @property
    def batch_digests(self) -> dict[str, str]:
        return {route: self.batches[route].digest for route in ROUTES}

    @property
    def source_authority_sha256(self) -> str:
        authorities = {
            batch.source_authority_sha256 for batch in self.batches.values()
        }
        if len(authorities) != 1:
            raise StageCContractError("route batches disagree on source authority")
        return next(iter(authorities))

    def train_epoch(self) -> dict[str, dict[str, float]]:
        """One deterministic pass over C1, C2, C3 fixed aggregate batches."""

        epoch_losses: dict[str, dict[str, float]] = {arm: {} for arm in LEARNED_ARMS}
        for route in ROUTES:
            informed = self.batches[route]
            neutral = informed.neutral()
            for arm in LEARNED_ARMS:
                batch = informed if SOURCE_MAP[arm][route] == "informed" else neutral
                epoch_losses[arm][route] = self.models[arm].heads[route].update(
                    batch,
                    learning_rate=self.learning_rate,
                    gauge_weight=self.gauge_weight,
                )
            self.route_update_count += 1
        self.completed_source_epochs += 1
        self.loss_history.append({"epoch": self.completed_source_epochs, "losses": epoch_losses})
        return epoch_losses

    def train(self, epochs: int, *, checkpoint_directory: str | Path | None = None) -> None:
        if isinstance(epochs, bool) or epochs < 0:
            raise StageCContractError("epochs must be a nonnegative integer")
        for _ in range(epochs):
            self.train_epoch()
            if (
                checkpoint_directory is not None
                and self.completed_source_epochs % CHECKPOINT_EVERY_SOURCE_EPOCHS == 0
            ):
                path = Path(checkpoint_directory) / (
                    f"learner-{self.learner_seed}-epoch-{self.completed_source_epochs:06d}.json"
                )
                self.write_checkpoint(path)

    def checkpoint_payload(self) -> dict[str, object]:
        return {
            "schema": CHECKPOINT_SCHEMA,
            "learner_seed": self.learner_seed,
            "completed_source_epochs": self.completed_source_epochs,
            "route_update_count": self.route_update_count,
            "updates_per_source_epoch": len(ROUTES),
            "checkpoint_every_source_epochs": CHECKPOINT_EVERY_SOURCE_EPOCHS,
            "q1_schema_sha256": Q1_SCHEMA_SHA256,
            "q2_schema_sha256": Q2_SCHEMA_SHA256,
            "batch_digests": self.batch_digests,
            "source_authority_sha256": self.source_authority_sha256,
            "initialization_sha256": self.initialization_sha256,
            "initialization": self.initialization_payload,
            "arm_order": list(ARM_ORDER),
            "source_map": {arm: dict(SOURCE_MAP[arm]) for arm in LEARNED_ARMS},
            "arm_order": list(ARM_ORDER),
            "arms": {arm: self.models[arm].payload() for arm in LEARNED_ARMS},
            "optimizer": {
                "kind": "deterministic_full_batch_gradient_descent",
                "learning_rate_hex": float_hex(self.learning_rate),
                "gauge_weight_hex": float_hex(self.gauge_weight),
                "state": "stateless",
            },
            "zero_bootstrap": True,
        }

    def write_checkpoint(self, path: str | Path) -> str:
        return write_once_json(path, self.checkpoint_payload())

    def load_checkpoint(self, path: str | Path) -> None:
        payload = read_verified_json(path)
        if not isinstance(payload, dict) or payload.get("schema") != CHECKPOINT_SCHEMA:
            raise StageCContractError("unsupported checkpoint schema")
        fixed = {
            "learner_seed": self.learner_seed,
            "batch_digests": self.batch_digests,
            "source_authority_sha256": self.source_authority_sha256,
            "initialization_sha256": self.initialization_sha256,
            "initialization": self.initialization_payload,
            "arm_order": list(ARM_ORDER),
            "source_map": {arm: dict(SOURCE_MAP[arm]) for arm in LEARNED_ARMS},
            "arm_order": list(ARM_ORDER),
            "q1_schema_sha256": Q1_SCHEMA_SHA256,
            "q2_schema_sha256": Q2_SCHEMA_SHA256,
            "checkpoint_every_source_epochs": CHECKPOINT_EVERY_SOURCE_EPOCHS,
            "updates_per_source_epoch": len(ROUTES),
            "zero_bootstrap": True,
        }
        for field, expected in fixed.items():
            if payload.get(field) != expected:
                raise StageCContractError(f"checkpoint {field} mismatch")
        optimizer = payload.get("optimizer")
        expected_optimizer = {
            "kind": "deterministic_full_batch_gradient_descent",
            "learning_rate_hex": float_hex(self.learning_rate),
            "gauge_weight_hex": float_hex(self.gauge_weight),
            "state": "stateless",
        }
        if optimizer != expected_optimizer:
            raise StageCContractError("checkpoint optimizer state mismatch")
        completed = int(payload.get("completed_source_epochs", -1))
        updates = int(payload.get("route_update_count", -1))
        if completed < 0 or updates != completed * len(ROUTES):
            raise StageCContractError("checkpoint source-epoch cursor is invalid")
        arms = payload.get("arms")
        if not isinstance(arms, dict) or set(arms) != set(LEARNED_ARMS):
            raise StageCContractError("checkpoint arm inventory drifted")
        for arm in LEARNED_ARMS:
            arm_payload = arms[arm]
            if not isinstance(arm_payload, dict) or set(arm_payload) != set(ROUTES):
                raise StageCContractError("checkpoint head inventory drifted")
            for route in ROUTES:
                head_payload = arm_payload[route]
                if not isinstance(head_payload, dict):
                    raise StageCContractError("checkpoint head payload drifted")
                weights = np.asarray(
                    [parse_float_hex(value, field="weight") for value in head_payload["weights_hex"]],
                    dtype=np.float64,
                )
                if weights.shape != self.models[arm].heads[route].weights.shape:
                    raise StageCContractError("checkpoint head shape drifted")
                self.models[arm].heads[route].weights[:] = weights
                self.models[arm].heads[route].bias = parse_float_hex(
                    head_payload["bias_hex"], field="bias"
                )
        self.completed_source_epochs = completed
        self.route_update_count = updates


__all__ = [
    "ARM_ORDER", "CHECKPOINT_EVERY_SOURCE_EPOCHS", "LEARNED_ARMS", "LineageOrchestrator",
    "PairwiseBatch", "ROUTES", "SOURCE_MAP", "ThreeRouteModel", "build_pairwise_batches",
]
