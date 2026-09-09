"""Deterministic pairwise zero-bootstrap learner and six-arm orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

import numpy as np
from mcrl.physics_v025.tapes import seed_from_domain

from .canonical import (
    StageCContractError,
    canonical_sha256,
    file_sha256,
    float_hex,
    parse_float_hex,
    read_verified_json,
    write_once_json,
)
from .shards import SourceShard
from .state import Q1_SCHEMA_SHA256, Q2_SCHEMA_SHA256, SourceRow
from .coalitions import CoalitionContext, CoalitionShard


Route = Literal["C1", "C2", "C3"]
ROUTES: tuple[Route, ...] = ("C1", "C2", "C3")
LEARNED_ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL")
ARM_ORDER = (*LEARNED_ARMS, "BASELINE")
SOURCE_MAP: Mapping[str, Mapping[Route, str]] = {
    "FULL": {"C1": "informed", "C2": "informed", "C3": "informed"},
    "DROP_C1": {"C1": "neutral", "C2": "informed", "C3": "informed"},
    "DROP_C2": {"C1": "informed", "C2": "neutral", "C3": "informed"},
    "DROP_C3": {"C1": "informed", "C2": "informed", "C3": "neutral"},
    "ALL_NEUTRAL_CONTROL": {"C1": "neutral", "C2": "neutral", "C3": "neutral"},
}
CHECKPOINT_SCHEMA = "mcrl-v025-stagec-lineage-checkpoint-v1"
CHECKPOINT_EVERY_SOURCE_EPOCHS = 100
LEGACY_EPOCH_BUDGET = 2000
LEARNER_SEED_DOMAINS = tuple(f"V025_LEARNER/seed/{index}" for index in range(1, 13))
LEARNER_SEEDS = tuple(seed_from_domain(domain) for domain in LEARNER_SEED_DOMAINS)

# Literal copy of the heterogeneous V0.23 seam and the production classes it
# delegates to.  Only input_dim is supplied by the sealed Stage-C schemas.
LEGACY_TRAINER_LITERALS: Mapping[str, object] = {
    "C1": {
        "hidden_layers": (8,), "activation": "relu", "learning_rate": 1.0e-2,
        "adam_betas": (0.9, 0.999), "adam_epsilon": 1.0e-8,
        "weight_decay": 0.0, "gauge_beta": 0.2, "loss_weight": 1.0,
    },
    "C2": {
        "hidden_layers": (100, 50, 50), "activation": "tanh", "learning_rate": 1.0e-3,
        "adam_betas": (0.9, 0.999), "adam_epsilon": 1.0e-8,
        "weight_decay": 0.0, "gauge_beta": 0.1, "loss_weight": 1.0,
    },
    "C3": {
        "hidden_layers": (64, 64), "activation": "relu", "learning_rate": 1.0e-3,
        "adam_betas": (0.9, 0.999), "adam_epsilon": 1.0e-8,
        "weight_decay": 0.0, "loss_weight": 1.0,
    },
    "batch": "one_typed_deterministic_full_batch_update_per_route_per_source_epoch",
    "route_order": ROUTES,
    "epoch_budget": LEGACY_EPOCH_BUDGET,
    "stopping": "exact_epoch_budget_no_early_selection",
    "serialization": "all_heads_and_adam_state_with_authenticated_source_cursor",
}
LEGACY_TRAINER_LITERALS_SHA256 = canonical_sha256(LEGACY_TRAINER_LITERALS)


@dataclass(frozen=True, slots=True)
class PairwiseBatch:
    """A typed fixed aggregate batch. There is intentionally no next state."""

    route: Route
    reference_states: np.ndarray
    candidate_states: np.ndarray
    target_deltas: np.ndarray
    row_identities: tuple[str, ...]
    source_authority_sha256: str
    source_identity: str
    physics_digest: str
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
        *,
        source_identity: str = "informed",
        physics_digest: str,
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
        if len(physics_digest) != 64 or any(character not in "0123456789abcdef" for character in physics_digest):
            raise StageCContractError("pairwise batch physics digest is invalid")
        payload = {
            "schema": "mcrl-v025-stagec-pairwise-batch-v1",
            "route": route,
            "shape": list(reference.shape),
            "reference": [[float_hex(v) for v in row] for row in reference],
            "candidate": [[float_hex(v) for v in row] for row in candidate],
            "targets": [float_hex(v) for v in targets],
            "row_identities": list(identities),
            "source_authority_sha256": source_authority_sha256,
            "source_identity": source_identity,
            "physics_digest": physics_digest,
            "zero_bootstrap": True,
        }
        return cls(
            route,
            reference,
            candidate,
            targets,
            identities,
            source_authority_sha256,
            source_identity,
            physics_digest,
            canonical_sha256(payload),
        )

    def neutral(
        self, definition: "NeutralSourceDefinition | None" = None
    ) -> "PairwiseBatch":
        if definition is not None and definition.route != self.route:
            raise StageCContractError("neutral source route disagrees with batch")
        return PairwiseBatch.create(
            self.route,
            self.reference_states,
            self.candidate_states,
            np.zeros_like(self.target_deltas),
            self.row_identities,
            self.source_authority_sha256,
            source_identity=(
                "neutral:legacy"
                if definition is None
                else f"neutral:{definition.digest}"
            ),
            physics_digest=self.physics_digest,
        )


def _route_state(row: SourceRow, route: Route) -> tuple[float, ...]:
    if route == "C1":
        return row.q1_state
    if route == "C2":
        return row.q2_state
    return (*row.q1_state, *row.q2_state)


def _route_label(row: SourceRow, route: Route) -> float:
    if route == "C3":
        # Compatibility-only build-1 synthetic batch.  Contract-v1 training
        # uses CoalitionBatch and never consumes a per-action C3 label.
        return 0.0
    field = {
        "C1": row.c1_label_normalized_hex,
        "C2": row.c2_label_normalized_hex,
    }[route]
    return parse_float_hex(field, field=f"{route}.normalized_label")


def build_pairwise_batches(shards: Sequence[SourceShard]) -> dict[Route, PairwiseBatch]:
    rows = tuple(row for shard in shards for row in shard.rows)
    physics = {row.physics_digest for row in rows}
    if len(physics) != 1:
        raise StageCContractError("pairwise source shards mix physics digests")
    physics_digest = next(iter(physics))
    source_authority_sha256 = canonical_sha256(
        {
            "schema": "mcrl-v025-stagec-source-authority-v1",
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
            physics_digest=physics_digest,
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


@dataclass(frozen=True, slots=True)
class NeutralSourceDefinition:
    """C5 seal for one named neutral route/source identity."""

    route: Route
    generator: str
    labels: str
    support: str
    strata: tuple[str, ...]
    overlap: str
    row_weights: str
    optimization_dose: str

    def __post_init__(self) -> None:
        if self.route not in ROUTES or any(
            not value
            for value in (
                self.generator,
                self.labels,
                self.support,
                self.overlap,
                self.row_weights,
                self.optimization_dose,
            )
        ) or not self.strata:
            raise StageCContractError("neutral-source sealing fields must be complete")

    @property
    def digest(self) -> str:
        return canonical_sha256(
            {
                "schema": "mcrl-v025-stagec-neutral-source-v1",
                **asdict(self),
                "strata": list(self.strata),
            }
        )


def default_synthetic_neutral_sources() -> dict[Route, NeutralSourceDefinition]:
    """Fully specified synthetic-only C5 sources; not authority for real rows."""

    return {
        route: NeutralSourceDefinition(
            route=route,
            generator="matched_rows_replace_scalar_target_with_zero_v1",
            labels="exact_zero_normalized_bits_per_kappa",
            support="identical_context_and_action_or_coalition_support_within_route_identity",
            strata=("setting_id", "coalition_size" if route == "C3" else "action_count"),
            overlap="one_to_one_row_identity_overlap_with_informative_source",
            row_weights="identical_unit_weights_in_stable_row_order",
            optimization_dose="one_full_batch_update_per_source_epoch",
        )
        for route in ROUTES
    }


@dataclass(frozen=True, slots=True)
class CoalitionBatch:
    """Typed C3 scalar batch over complete set-conditioned contexts."""

    contexts: tuple[CoalitionContext, ...]
    invariant_states: np.ndarray
    target_psi: np.ndarray
    row_identities: tuple[str, ...]
    source_authority_sha256: str
    source_identity: str
    physics_digest: str
    member_width: int
    digest: str

    @classmethod
    def create(
        cls,
        shards: Sequence[CoalitionShard],
        *,
        source_identity: str = "informed",
        target_override: Sequence[float] | None = None,
    ) -> "CoalitionBatch":
        rows = tuple(row for shard in shards for row in shard.rows)
        if not rows:
            raise StageCContractError("C3 coalition batch cannot be empty")
        physics = {row.physics_digest for row in rows}
        if len(physics) != 1:
            raise StageCContractError("C3 coalition shards mix physics digests")
        physics_digest = next(iter(physics))
        widths = {len(member.invariant_features) for row in rows for member in row.context.members}
        if len(widths) != 1:
            raise StageCContractError("C3 coalition member width drifted")
        member_width = next(iter(widths))
        contexts = tuple(row.context for row in rows)
        states = np.stack(
            [context.invariant_vector(member_width=member_width) for context in contexts]
        )
        targets = np.asarray(
            [
                parse_float_hex(row.psi_normalized_hex, field="psi_normalized")
                for row in rows
            ]
            if target_override is None
            else target_override,
            dtype=np.float64,
        )
        if targets.shape != (len(rows),) or not np.isfinite(targets).all():
            raise StageCContractError("C3 scalar target shape drifted")
        identities = tuple(
            f"{row.world_id}|{row.anchor_id}|{','.join(map(str, row.context.changed_users))}"
            for row in rows
        )
        authority = canonical_sha256(
            {
                "schema": "mcrl-v025-stagec-c3-source-authority-v1",
                "shards": [shard.file_sha256 for shard in shards],
                "row_schemas": sorted({row.schema for row in rows}),
                "catalogues": sorted({row.catalogue_digest for row in rows}),
                "physics": sorted({row.physics_digest for row in rows}),
            }
        )
        payload = {
            "schema": "mcrl-v025-stagec-c3-coalition-batch-v1",
            "source_identity": source_identity,
            "shape": list(states.shape),
            "states": [[float_hex(value) for value in row] for row in states],
            "targets": [float_hex(value) for value in targets],
            "row_identities": list(identities),
            "source_authority_sha256": authority,
            "anchored_zero_empty_and_singleton": True,
            "physics_digest": physics_digest,
            "permutation_invariant": True,
        }
        return cls(
            contexts,
            states,
            targets,
            identities,
            authority,
            source_identity,
            physics_digest,
            member_width,
            canonical_sha256(payload),
        )

    def neutral(self, definition: NeutralSourceDefinition) -> "CoalitionBatch":
        if definition.route != "C3":
            raise StageCContractError("C3 batch requires the C3 neutral definition")
        # Preserve support, strata, weights, order, and dose exactly.  The
        # definition digest makes the source identity explicit in checkpoints.
        return CoalitionBatch(
            contexts=self.contexts,
            invariant_states=self.invariant_states.copy(),
            target_psi=np.zeros_like(self.target_psi),
            row_identities=self.row_identities,
            source_authority_sha256=self.source_authority_sha256,
            source_identity=f"neutral:{definition.digest}",
            physics_digest=self.physics_digest,
            member_width=self.member_width,
            digest=canonical_sha256(
                {
                    "informed_batch": self.digest,
                    "neutral_source_sha256": definition.digest,
                    "targets": [float_hex(0.0) for _ in self.target_psi],
                }
            ),
        )


@dataclass(slots=True)
class AdamMLPHead:
    """Legacy-shaped MLP trained by a literal Adam pairwise objective."""

    weights: list[np.ndarray]
    biases: list[np.ndarray]
    first_moment_w: list[np.ndarray]
    second_moment_w: list[np.ndarray]
    first_moment_b: list[np.ndarray]
    second_moment_b: list[np.ndarray]
    activation: str
    learning_rate: float
    beta1: float
    beta2: float
    epsilon: float
    weight_decay: float
    gauge_beta: float
    loss_weight: float
    adam_step: int = 0

    @classmethod
    def create(cls, input_dim: int, literal: Mapping[str, object], rng: np.random.Generator) -> "AdamMLPHead":
        widths = (input_dim, *tuple(int(value) for value in literal["hidden_layers"]), 1)
        weights = [
            rng.normal(0.0, np.sqrt(2.0 / max(1, left)), (left, right))
            for left, right in zip(widths[:-1], widths[1:], strict=True)
        ]
        biases = [np.zeros(right, dtype=np.float64) for right in widths[1:]]
        return cls(
            weights=weights,
            biases=biases,
            first_moment_w=[np.zeros_like(value) for value in weights],
            second_moment_w=[np.zeros_like(value) for value in weights],
            first_moment_b=[np.zeros_like(value) for value in biases],
            second_moment_b=[np.zeros_like(value) for value in biases],
            activation=str(literal["activation"]),
            learning_rate=float(literal["learning_rate"]),
            beta1=float(tuple(literal["adam_betas"])[0]),
            beta2=float(tuple(literal["adam_betas"])[1]),
            epsilon=float(literal["adam_epsilon"]),
            weight_decay=float(literal["weight_decay"]),
            gauge_beta=float(literal.get("gauge_beta", 0.0)),
            loss_weight=float(literal["loss_weight"]),
        )

    def clone(self) -> "AdamMLPHead":
        return AdamMLPHead(
            *(
                [[value.copy() for value in group] for group in (
                    self.weights, self.biases, self.first_moment_w, self.second_moment_w,
                    self.first_moment_b, self.second_moment_b,
                )]
            ),
            self.activation, self.learning_rate, self.beta1, self.beta2,
            self.epsilon, self.weight_decay, self.gauge_beta, self.loss_weight,
            self.adam_step,
        )

    def _forward(self, values: np.ndarray) -> tuple[np.ndarray, list[np.ndarray], list[np.ndarray]]:
        current = np.asarray(values, dtype=np.float64)
        activations = [current]
        preactivations: list[np.ndarray] = []
        for index, (weights, bias) in enumerate(zip(self.weights, self.biases, strict=True)):
            pre = current @ weights + bias
            preactivations.append(pre)
            if index == len(self.weights) - 1:
                current = pre
            elif self.activation == "relu":
                current = np.maximum(pre, 0.0)
            else:
                current = np.tanh(pre)
            activations.append(current)
        return current[:, 0], activations, preactivations

    def score(self, state: Sequence[float]) -> float:
        value, _, _ = self._forward(np.asarray(state, dtype=np.float64)[None, :])
        return float(value[0])

    def _backward(
        self, activations: list[np.ndarray], preactivations: list[np.ndarray], output_gradient: np.ndarray
    ) -> tuple[list[np.ndarray], list[np.ndarray]]:
        gradient = output_gradient[:, None]
        weight_gradients = [np.empty_like(value) for value in self.weights]
        bias_gradients = [np.empty_like(value) for value in self.biases]
        for index in reversed(range(len(self.weights))):
            weight_gradients[index] = activations[index].T @ gradient
            bias_gradients[index] = gradient.sum(axis=0)
            if index:
                gradient = gradient @ self.weights[index].T
                if self.activation == "relu":
                    gradient *= preactivations[index - 1] > 0.0
                else:
                    hidden = activations[index]
                    gradient *= 1.0 - hidden * hidden
        return weight_gradients, bias_gradients

    def _adam(self, grad_w: list[np.ndarray], grad_b: list[np.ndarray]) -> None:
        self.adam_step += 1
        for parameter, gradient, first, second in zip(
            self.weights, grad_w, self.first_moment_w, self.second_moment_w, strict=True
        ):
            gradient = gradient + self.weight_decay * parameter
            first *= self.beta1
            first += (1.0 - self.beta1) * gradient
            second *= self.beta2
            second += (1.0 - self.beta2) * gradient * gradient
            corrected_m = first / (1.0 - self.beta1**self.adam_step)
            corrected_v = second / (1.0 - self.beta2**self.adam_step)
            parameter -= self.learning_rate * corrected_m / (np.sqrt(corrected_v) + self.epsilon)
        for parameter, gradient, first, second in zip(
            self.biases, grad_b, self.first_moment_b, self.second_moment_b, strict=True
        ):
            first *= self.beta1
            first += (1.0 - self.beta1) * gradient
            second *= self.beta2
            second += (1.0 - self.beta2) * gradient * gradient
            parameter -= self.learning_rate * (first / (1.0 - self.beta1**self.adam_step)) / (
                np.sqrt(second / (1.0 - self.beta2**self.adam_step)) + self.epsilon
            )

    def update(self, batch: PairwiseBatch) -> float:
        reference, ref_a, ref_z = self._forward(batch.reference_states)
        candidate, cand_a, cand_z = self._forward(batch.candidate_states)
        residual = candidate - reference - batch.target_deltas
        count = float(len(residual))
        scale = 2.0 * self.loss_weight / count
        cand_w, cand_b = self._backward(cand_a, cand_z, scale * residual)
        ref_gradient = scale * (-residual + self.gauge_beta * reference)
        ref_w, ref_b = self._backward(ref_a, ref_z, ref_gradient)
        self._adam(
            [left + right for left, right in zip(cand_w, ref_w, strict=True)],
            [left + right for left, right in zip(cand_b, ref_b, strict=True)],
        )
        return float(self.loss_weight * np.mean(residual * residual + self.gauge_beta * reference * reference))

    def update_scalar(self, states: np.ndarray, targets: np.ndarray) -> float:
        prediction, activations, preactivations = self._forward(states)
        residual = prediction - targets
        scale = 2.0 * self.loss_weight / float(len(residual))
        gradients = self._backward(activations, preactivations, scale * residual)
        self._adam(*gradients)
        return float(self.loss_weight * np.mean(residual * residual))

    def payload(self) -> dict[str, object]:
        encode = lambda arrays: [
            [[float_hex(value) for value in row] for row in array]
            if array.ndim == 2 else [float_hex(value) for value in array]
            for array in arrays
        ]
        return {
            "kind": "legacy_heterogeneous_adam_mlp",
            "activation": self.activation,
            "weights_hex": encode(self.weights),
            "biases_hex": encode(self.biases),
            "adam_first_moment_weights_hex": encode(self.first_moment_w),
            "adam_second_moment_weights_hex": encode(self.second_moment_w),
            "adam_first_moment_biases_hex": encode(self.first_moment_b),
            "adam_second_moment_biases_hex": encode(self.second_moment_b),
            "adam_step": self.adam_step,
            "optimizer": {
                "kind": "Adam", "learning_rate": self.learning_rate,
                "betas": [self.beta1, self.beta2], "epsilon": self.epsilon,
                "weight_decay": self.weight_decay,
            },
            "gauge_beta": self.gauge_beta,
            "loss_weight": self.loss_weight,
        }


@dataclass(slots=True)
class AdamSetInteractionHead:
    network: AdamMLPHead
    member_width: int

    def clone(self) -> "AdamSetInteractionHead":
        return AdamSetInteractionHead(self.network.clone(), self.member_width)

    def score(self, context: CoalitionContext) -> float:
        if len(context.members) <= 1:
            return 0.0
        return self.network.score(context.invariant_vector(member_width=self.member_width))

    def update(self, batch: CoalitionBatch) -> float:
        return self.network.update_scalar(batch.invariant_states, batch.target_psi)

    def payload(self) -> dict[str, object]:
        return {
            **self.network.payload(),
            "kind": "permutation_invariant_set_conditioned_legacy_adam_mlp",
            "architecture": "two_hidden_layer_relu_mlp_on_sum_max_and_padded_resource_context",
            "member_width": self.member_width,
            "anchors": {"empty": 0.0, "singleton": 0.0},
        }


@dataclass(slots=True)
class SetInteractionHead:
    """Two-layer permutation-invariant scalar Psi MLP with hard zero anchors."""

    input_weights: np.ndarray
    input_bias: np.ndarray
    output_weights: np.ndarray
    output_bias: float
    member_width: int

    def clone(self) -> "SetInteractionHead":
        return SetInteractionHead(
            self.input_weights.copy(),
            self.input_bias.copy(),
            self.output_weights.copy(),
            float(self.output_bias),
            self.member_width,
        )

    def _hidden(self, values: np.ndarray) -> np.ndarray:
        if values.shape[-1] != self.input_weights.shape[1]:
            raise StageCContractError("set-interaction state shape drifted")
        return np.tanh(values @ self.input_weights.T + self.input_bias)

    def score(self, context: CoalitionContext) -> float:
        if len(context.members) <= 1:
            return 0.0
        values = context.invariant_vector(member_width=self.member_width)
        return float(self._hidden(values) @ self.output_weights + self.output_bias)

    def update(self, batch: CoalitionBatch, *, learning_rate: float) -> float:
        hidden = self._hidden(batch.invariant_states)
        predictions = hidden @ self.output_weights + self.output_bias
        residual = predictions - batch.target_psi
        count = float(batch.target_psi.size)
        scale = 2.0 / count
        output_weights_before = self.output_weights.copy()
        self.output_weights -= learning_rate * scale * (hidden.T @ residual)
        self.output_bias -= learning_rate * float(scale * residual.sum())
        hidden_gradient = residual[:, None] * output_weights_before[None, :] * (1.0 - hidden * hidden)
        self.input_weights -= learning_rate * scale * (hidden_gradient.T @ batch.invariant_states)
        self.input_bias -= learning_rate * scale * hidden_gradient.sum(axis=0)
        loss = float(np.mean(residual * residual))
        if not all(
            np.isfinite(value).all()
            for value in (self.input_weights, self.input_bias, self.output_weights)
        ) or not np.isfinite(self.output_bias):
            raise StageCContractError("non-finite C3 learner update")
        return loss

    def fit_closed_form(self, batch: CoalitionBatch, *, ridge: float = 1e-10) -> float:
        """Deterministic synthetic/KAT fit of the same scalar squared-error head."""

        hidden = self._hidden(batch.invariant_states)
        design = np.column_stack((hidden, np.ones(hidden.shape[0])))
        gram = design.T @ design + ridge * np.eye(design.shape[1])
        solution = np.linalg.solve(gram, design.T @ batch.target_psi)
        self.output_weights[:] = solution[:-1]
        self.output_bias = float(solution[-1])
        residual = design @ solution - batch.target_psi
        return float(np.mean(residual * residual))

    def payload(self) -> dict[str, object]:
        return {
            "kind": "permutation_invariant_set_conditioned_scalar",
            "architecture": "two_layer_tanh_mlp_on_sum_max_and_padded_resource_context",
            "input_weights_hex": [
                [float_hex(value) for value in row] for row in self.input_weights
            ],
            "input_bias_hex": [float_hex(value) for value in self.input_bias],
            "output_weights_hex": [float_hex(value) for value in self.output_weights],
            "output_bias_hex": float_hex(self.output_bias),
            "member_width": self.member_width,
            "anchors": {"empty": 0.0, "singleton": 0.0},
        }


@dataclass(slots=True)
class V1ThreeRouteModel:
    q1: LinearHead | AdamMLPHead
    q2: LinearHead | AdamMLPHead
    psi: SetInteractionHead | AdamSetInteractionHead
    checkpoint_sha256: str | None = None

    def clone(self) -> "V1ThreeRouteModel":
        return V1ThreeRouteModel(
            self.q1.clone(), self.q2.clone(), self.psi.clone(), self.checkpoint_sha256
        )

    def score(self, route: Route, state: Sequence[float]) -> float:
        if route == "C1":
            return self.q1.score(state)
        if route == "C2":
            return self.q2.score(state)
        raise StageCContractError("C3 requires complete coalition context")

    def interaction(self, context: CoalitionContext) -> float:
        return self.psi.score(context)

    def payload(self) -> dict[str, object]:
        return {
            "C1": self.q1.payload() if isinstance(self.q1, AdamMLPHead) else {
                "kind": "pairwise_zero_bootstrap_linear",
                "weights_hex": [float_hex(value) for value in self.q1.weights],
                "bias_hex": float_hex(self.q1.bias),
            },
            "C2": self.q2.payload() if isinstance(self.q2, AdamMLPHead) else {
                "kind": "pairwise_zero_bootstrap_linear",
                "weights_hex": [float_hex(value) for value in self.q2.weights],
                "bias_hex": float_hex(self.q2.bias),
            },
            "C3": self.psi.payload(),
        }


class V1LineageOrchestrator:
    """C7 matched five-arm learner with a scalar set-conditioned C3 route."""

    def __init__(
        self,
        *,
        learner_seed: int,
        q1_batch: PairwiseBatch,
        q2_batch: PairwiseBatch,
        c3_batch: CoalitionBatch,
        neutral_sources: Mapping[Route, NeutralSourceDefinition],
    ) -> None:
        if q1_batch.route != "C1" or q2_batch.route != "C2":
            raise StageCContractError("v1 action batches must be C1 then C2")
        if set(neutral_sources) != set(ROUTES) or any(
            neutral_sources[route].route != route for route in ROUTES
        ):
            raise StageCContractError("all three sealed neutral-source definitions are required")
        if len({q1_batch.physics_digest, q2_batch.physics_digest, c3_batch.physics_digest}) != 1:
            raise StageCContractError("C1/C2/C3 training physics digests disagree")
        self.learner_seed = int(learner_seed)
        self.q1_batch = q1_batch
        self.q2_batch = q2_batch
        self.c3_batch = c3_batch
        self.neutral_sources = dict(neutral_sources)
        self.physics_digest = q1_batch.physics_digest
        rng = np.random.default_rng(self.learner_seed)
        template = V1ThreeRouteModel(
            AdamMLPHead.create(
                q1_batch.reference_states.shape[1], LEGACY_TRAINER_LITERALS["C1"], rng
            ),
            AdamMLPHead.create(
                q2_batch.reference_states.shape[1], LEGACY_TRAINER_LITERALS["C2"], rng
            ),
            AdamSetInteractionHead(
                AdamMLPHead.create(
                    c3_batch.invariant_states.shape[1], LEGACY_TRAINER_LITERALS["C3"], rng
                ),
                c3_batch.member_width,
            ),
        )
        self.initialization_payload = template.payload()
        self.initialization_sha256 = canonical_sha256(self.initialization_payload)
        self.models = {arm: template.clone() for arm in LEARNED_ARMS}
        self.completed_source_epochs = 0
        self.route_update_count = 0

    def train_epoch(self) -> dict[str, dict[str, float]]:
        if self.completed_source_epochs >= LEGACY_EPOCH_BUDGET:
            raise StageCContractError("legacy exact epoch budget is already complete")
        losses: dict[str, dict[str, float]] = {arm: {} for arm in LEARNED_ARMS}
        for route, informed in (("C1", self.q1_batch), ("C2", self.q2_batch)):
            definition = self.neutral_sources[route]
            neutral = informed.neutral(definition)
            for arm in LEARNED_ARMS:
                batch = informed if SOURCE_MAP[arm][route] == "informed" else neutral
                head = self.models[arm].q1 if route == "C1" else self.models[arm].q2
                assert isinstance(head, AdamMLPHead)
                losses[arm][route] = head.update(batch)
            self.route_update_count += 1
        neutral_c3 = self.c3_batch.neutral(self.neutral_sources["C3"])
        for arm in LEARNED_ARMS:
            batch = self.c3_batch if SOURCE_MAP[arm]["C3"] == "informed" else neutral_c3
            head = self.models[arm].psi
            assert isinstance(head, AdamSetInteractionHead)
            losses[arm]["C3"] = head.update(batch)
        self.route_update_count += 1
        self.completed_source_epochs += 1
        return losses

    def train(self, epochs: int, *, checkpoint_directory: str | Path | None = None) -> None:
        if isinstance(epochs, bool) or not isinstance(epochs, int) or epochs < 0:
            raise StageCContractError("epochs must be a nonnegative integer")
        if self.completed_source_epochs + epochs > LEGACY_EPOCH_BUDGET:
            raise StageCContractError("legacy exact epoch budget would be exceeded")
        for _ in range(epochs):
            self.train_epoch()
            if (
                checkpoint_directory is not None
                and self.completed_source_epochs % CHECKPOINT_EVERY_SOURCE_EPOCHS == 0
            ):
                self.write_checkpoint(
                    Path(checkpoint_directory)
                    / f"learner-{self.learner_seed}-epoch-{self.completed_source_epochs:06d}.json"
                )

    def fit_to_budget(self, *, checkpoint_directory: str | Path) -> None:
        """Production fit: exhaust the frozen budget and checkpoint every 100 epochs."""

        self.train(
            LEGACY_EPOCH_BUDGET - self.completed_source_epochs,
            checkpoint_directory=checkpoint_directory,
        )

    def checkpoint_payload(self) -> dict[str, object]:
        return {
            "schema": "mcrl-v025-stagec-v1-lineage-checkpoint-v1",
            "learner_seed": self.learner_seed,
            "completed_source_epochs": self.completed_source_epochs,
            "route_update_count": self.route_update_count,
            "checkpoint_every_source_epochs": CHECKPOINT_EVERY_SOURCE_EPOCHS,
            "legacy_trainer_literals": dict(LEGACY_TRAINER_LITERALS),
            "legacy_trainer_literals_sha256": LEGACY_TRAINER_LITERALS_SHA256,
            "epoch_budget": LEGACY_EPOCH_BUDGET,
            "stopping_rule": "exact_epoch_budget_no_early_selection",
            "training_physics_digest": self.physics_digest,
            "batch_digests": {
                "C1": self.q1_batch.digest,
                "C2": self.q2_batch.digest,
                "C3": self.c3_batch.digest,
            },
            "neutral_source_digests": {
                route: self.neutral_sources[route].digest for route in ROUTES
            },
            "initialization": self.initialization_payload,
            "initialization_sha256": self.initialization_sha256,
            "source_map": {arm: dict(SOURCE_MAP[arm]) for arm in LEARNED_ARMS},
            "arms": {arm: self.models[arm].payload() for arm in LEARNED_ARMS},
            "optimizer": "route_local_legacy_Adam_state_serialized_inside_each_head",
            "zero_bootstrap": True,
        }

    def bind_checkpoint_identity(self) -> str:
        digest = canonical_sha256(self.checkpoint_payload())
        for model in self.models.values():
            model.checkpoint_sha256 = digest
        return digest

    def write_checkpoint(self, path: str | Path) -> str:
        if (
            self.completed_source_epochs == 0
            or self.completed_source_epochs % CHECKPOINT_EVERY_SOURCE_EPOCHS
        ):
            raise StageCContractError("automatic checkpoints are written only at 100-epoch boundaries")
        written = write_once_json(path, self.checkpoint_payload())
        for model in self.models.values():
            model.checkpoint_sha256 = written
        return written

    @staticmethod
    def _restore_adam_head(head: AdamMLPHead, payload: Mapping[str, object]) -> None:
        def decode(values: object, shapes: Sequence[tuple[int, ...]], field: str) -> list[np.ndarray]:
            if not isinstance(values, list) or len(values) != len(shapes):
                raise StageCContractError(f"checkpoint {field} layer inventory drifted")
            arrays: list[np.ndarray] = []
            for encoded, shape in zip(values, shapes, strict=True):
                array = np.asarray(encoded, dtype=object)
                flat = [parse_float_hex(value, field=field) for value in array.reshape(-1)]
                restored = np.asarray(flat, dtype=np.float64).reshape(shape)
                arrays.append(restored)
            return arrays
        mapping = (
            ("weights_hex", head.weights),
            ("biases_hex", head.biases),
            ("adam_first_moment_weights_hex", head.first_moment_w),
            ("adam_second_moment_weights_hex", head.second_moment_w),
            ("adam_first_moment_biases_hex", head.first_moment_b),
            ("adam_second_moment_biases_hex", head.second_moment_b),
        )
        for field, destination in mapping:
            restored = decode(payload.get(field), [value.shape for value in destination], field)
            for target, source in zip(destination, restored, strict=True):
                target[:] = source
        head.adam_step = int(payload.get("adam_step", -1))
        if head.adam_step < 0:
            raise StageCContractError("checkpoint Adam cursor drifted")

    def load_checkpoint(self, path: str | Path) -> None:
        payload = read_verified_json(path)
        expected_neutral = {
            route: self.neutral_sources[route].digest for route in ROUTES
        }
        expected_source_map = {
            arm: dict(SOURCE_MAP[arm]) for arm in LEARNED_ARMS
        }
        if (
            payload.get("schema") != "mcrl-v025-stagec-v1-lineage-checkpoint-v1"
            or payload.get("learner_seed") != self.learner_seed
            or payload.get("initialization_sha256") != self.initialization_sha256
            or canonical_sha256(payload.get("initialization")) != self.initialization_sha256
            or payload.get("legacy_trainer_literals_sha256") != LEGACY_TRAINER_LITERALS_SHA256
            or canonical_sha256(payload.get("legacy_trainer_literals"))
            != LEGACY_TRAINER_LITERALS_SHA256
            or payload.get("checkpoint_every_source_epochs")
            != CHECKPOINT_EVERY_SOURCE_EPOCHS
            or payload.get("epoch_budget") != LEGACY_EPOCH_BUDGET
            or payload.get("stopping_rule") != "exact_epoch_budget_no_early_selection"
            or payload.get("training_physics_digest") != self.physics_digest
            or payload.get("batch_digests") != {
                "C1": self.q1_batch.digest, "C2": self.q2_batch.digest, "C3": self.c3_batch.digest
            }
            or payload.get("neutral_source_digests") != expected_neutral
            or payload.get("source_map") != expected_source_map
            or payload.get("zero_bootstrap") is not True
        ):
            raise StageCContractError("checkpoint authority drifted")
        arms = payload.get("arms")
        if not isinstance(arms, dict) or set(arms) != set(LEARNED_ARMS):
            raise StageCContractError("checkpoint arm inventory drifted")
        for arm in LEARNED_ARMS:
            model_payload = arms[arm]
            if not isinstance(model_payload, dict):
                raise StageCContractError("checkpoint model payload drifted")
            q1, q2, psi = self.models[arm].q1, self.models[arm].q2, self.models[arm].psi
            assert isinstance(q1, AdamMLPHead) and isinstance(q2, AdamMLPHead)
            assert isinstance(psi, AdamSetInteractionHead)
            self._restore_adam_head(q1, model_payload["C1"])
            self._restore_adam_head(q2, model_payload["C2"])
            self._restore_adam_head(psi.network, model_payload["C3"])
        completed = int(payload.get("completed_source_epochs", -1))
        updates = int(payload.get("route_update_count", -1))
        if (
            completed <= 0
            or completed > LEGACY_EPOCH_BUDGET
            or completed % CHECKPOINT_EVERY_SOURCE_EPOCHS
            or updates != completed * len(ROUTES)
        ):
            raise StageCContractError("checkpoint source cursor drifted")
        self.completed_source_epochs = completed
        self.route_update_count = updates
        checkpoint_digest = file_sha256(path)
        for model in self.models.values():
            model.checkpoint_sha256 = checkpoint_digest


__all__ = [
    "AdamMLPHead", "AdamSetInteractionHead", "ARM_ORDER", "CHECKPOINT_EVERY_SOURCE_EPOCHS", "LEARNED_ARMS", "LineageOrchestrator",
    "CoalitionBatch", "LEARNER_SEED_DOMAINS", "LEARNER_SEEDS", "NeutralSourceDefinition", "PairwiseBatch", "ROUTES",
    "LEGACY_EPOCH_BUDGET", "LEGACY_TRAINER_LITERALS", "LEGACY_TRAINER_LITERALS_SHA256",
    "SOURCE_MAP", "SetInteractionHead", "ThreeRouteModel", "V1LineageOrchestrator",
    "V1ThreeRouteModel", "build_pairwise_batches", "default_synthetic_neutral_sources",
]
