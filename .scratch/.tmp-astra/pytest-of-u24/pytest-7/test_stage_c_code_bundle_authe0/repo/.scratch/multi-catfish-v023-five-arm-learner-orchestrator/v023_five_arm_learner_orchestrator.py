"""Implementation-only V0.23 five-arm source-ablation learner orchestrator.

This isolated seam constructs five *independent* current
``EEAxisLCSRSThreeRoute`` models from one serialized initialization snapshot.
It never creates target data, starts a simulator, opens TEST, loads D40, or
changes a model head.  Every learner update is delegated to the existing
scratch ``V023HeterogeneousTrainer``.

The injected provider is intentionally the only target-data boundary.  Its
state is captured with the five model/optimizer states so an external target
batch adapter can later provide a deterministic resume-safe stream.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import importlib.util
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

import torch

from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    EEAxisLCSRSThreeRoute,
    LCSRSThreeRouteConfig,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014NormalizedPairBatch
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import LCSRSAnchorSurface
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch


ORCHESTRATOR_SCHEMA = "multi-catfish-mcrl-v023-five-arm-learner-orchestrator-v3"
IMPLEMENTATION_ONLY_CLAIM = "IMPLEMENTATION_ONLY_NO_EFFICACY_NO_SIMULATOR_NO_TEST"
UPDATES_PER_SOURCE_TRAINING_EPOCH = 3
FORMAL_CHECKPOINT_CADENCE_EPOCHS = 100
FORMAL_CHECKPOINT_CADENCE_UPDATES = (
    FORMAL_CHECKPOINT_CADENCE_EPOCHS * UPDATES_PER_SOURCE_TRAINING_EPOCH
)

ARMS = ("ALL_NEUTRAL_CONTROL", "FULL", "DROP_C1", "DROP_C2", "DROP_C3")
ROUTE_ORDER = ("C1", "C2", "C3")
SOURCE_ORDER = ("neutral", "informed")

# This mapping is deliberately closed: an ablation changes the *source batch*
# delivered to a current route, never the model topology or its parameters.
SOURCE_ABLATION_MAP: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "ALL_NEUTRAL_CONTROL": MappingProxyType(
            {"C1": "neutral", "C2": "neutral", "C3": "neutral"}
        ),
        "FULL": MappingProxyType(
            {"C1": "informed", "C2": "informed", "C3": "informed"}
        ),
        "DROP_C1": MappingProxyType(
            {"C1": "neutral", "C2": "informed", "C3": "informed"}
        ),
        "DROP_C2": MappingProxyType(
            {"C1": "informed", "C2": "neutral", "C3": "informed"}
        ),
        "DROP_C3": MappingProxyType(
            {"C1": "informed", "C2": "informed", "C3": "neutral"}
        ),
    }
)


def _source_ablation_map_payload() -> dict[str, dict[str, str]]:
    """Return the immutable mapping in checkpoint-safe plain-dict form."""

    return {arm: dict(routes) for arm, routes in SOURCE_ABLATION_MAP.items()}


class V023FiveArmOrchestratorError(MCRLContractError):
    """The isolated five-arm learner contract was violated."""


def _load_existing_trainer_type() -> type[Any]:
    """Load, rather than copy, the existing scratch update implementation."""

    trainer_path = (
        Path(__file__).resolve().parents[1]
        / "multi-catfish-v023-heterogeneous-trainer"
        / "v023_heterogeneous_trainer.py"
    )
    if not trainer_path.is_file():
        raise V023FiveArmOrchestratorError(
            "existing V023HeterogeneousTrainer scratch implementation is missing"
        )
    module_name = "v023_heterogeneous_trainer_for_five_arm_orchestrator"
    module = sys.modules.get(module_name)
    if module is None:
        spec = importlib.util.spec_from_file_location(module_name, trainer_path)
        if spec is None or spec.loader is None:
            raise V023FiveArmOrchestratorError(
                "cannot load existing V023HeterogeneousTrainer implementation"
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    trainer_type = getattr(module, "V023HeterogeneousTrainer", None)
    if not isinstance(trainer_type, type):
        raise V023FiveArmOrchestratorError(
            "existing scratch seam exposes no V023HeterogeneousTrainer"
        )
    return trainer_type


@dataclass(frozen=True, slots=True)
class ProvidedRouteBatch:
    """One provider-owned, typed route batch with a stable source-file identity."""

    route: str
    source: str
    file_id: str
    batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch | LCSRSC3SampledBatch
    c3_surfaces: tuple[LCSRSAnchorSurface, ...] = ()

    def __post_init__(self) -> None:
        if self.route not in ROUTE_ORDER:
            raise ValueError(f"route must be one of {ROUTE_ORDER}")
        if self.source not in SOURCE_ORDER:
            raise ValueError(f"source must be one of {SOURCE_ORDER}")
        if (
            not isinstance(self.file_id, str)
            or not self.file_id
            or self.file_id != self.file_id.strip()
        ):
            raise ValueError("file_id must be a nonempty trimmed stable identifier")
        if self.route == "C1":
            if not isinstance(self.batch, EEAxisPairBatch):
                raise TypeError("C1 provider batch must be EEAxisPairBatch")
            if self.c3_surfaces:
                raise ValueError("C1 provider batch may not carry C3 surfaces")
        elif self.route == "C2":
            if not isinstance(self.batch, EEAxisV014NormalizedPairBatch):
                raise TypeError("C2 provider batch must be normalized OPS-3 Q2")
            if self.c3_surfaces:
                raise ValueError("C2 provider batch may not carry C3 surfaces")
        else:
            if not isinstance(self.batch, LCSRSC3SampledBatch):
                raise TypeError("C3 provider batch must be LCSRSC3SampledBatch")
            if not self.c3_surfaces:
                raise ValueError("C3 provider batch requires typed LC-SRS surfaces")
            if any(not isinstance(surface, LCSRSAnchorSurface) for surface in self.c3_surfaces):
                raise TypeError("C3 provider surfaces must be LCSRSAnchorSurface")


@runtime_checkable
class DeterministicRouteBatchProvider(Protocol):
    """Minimal deterministic target-batch interface required by this seam.

    The orchestrator calls this once for each ``(route, source)`` at a cursor,
    then shares that immutable typed payload across every arm mapped to that
    source.  Implementations own all sampling and file selection.
    """

    def next_batch(
        self,
        *,
        route: str,
        source: str,
        update_cursor: int,
    ) -> ProvidedRouteBatch: ...

    def sampler_state(self) -> Mapping[str, Any]: ...

    def load_sampler_state(self, state: Mapping[str, Any]) -> None: ...


@dataclass(frozen=True, slots=True)
class V023FiveArmOrchestratorConfig:
    """Learner initialization and checkpoint timing; no target data lives here."""

    model_config: LCSRSThreeRouteConfig
    train_seed: int
    lineage: str = "v023-three-route"
    checkpoint_cadence_updates: int = FORMAL_CHECKPOINT_CADENCE_UPDATES
    formal_use: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.model_config, LCSRSThreeRouteConfig):
            raise TypeError("model_config must be LCSRSThreeRouteConfig")
        if isinstance(self.train_seed, bool) or not isinstance(self.train_seed, int):
            raise TypeError("train_seed must be an integer")
        if (
            not isinstance(self.lineage, str)
            or not self.lineage
            or self.lineage != self.lineage.strip()
        ):
            raise ValueError("lineage must be a nonempty trimmed string")
        if (
            isinstance(self.checkpoint_cadence_updates, bool)
            or not isinstance(self.checkpoint_cadence_updates, int)
            or self.checkpoint_cadence_updates < 1
        ):
            raise ValueError("checkpoint_cadence_updates must be a positive integer")
        if not isinstance(self.formal_use, bool):
            raise TypeError("formal_use must be a bool")
        if (
            self.formal_use
            and self.checkpoint_cadence_updates != FORMAL_CHECKPOINT_CADENCE_UPDATES
        ):
            raise ValueError(
                "formal V0.23 use requires 100 complete source-training epochs "
                "(300 C1/C2/C3 route updates) per checkpoint"
            )

    @classmethod
    def formal(
        cls,
        *,
        model_config: LCSRSThreeRouteConfig,
        train_seed: int,
        lineage: str = "v023-three-route",
    ) -> "V023FiveArmOrchestratorConfig":
        """Return the formal cadence: 100 complete C1->C2->C3 epochs."""

        return cls(
            model_config=model_config,
            train_seed=train_seed,
            lineage=lineage,
            checkpoint_cadence_updates=FORMAL_CHECKPOINT_CADENCE_UPDATES,
            formal_use=True,
        )


@dataclass(frozen=True, slots=True)
class ArmUpdateReceipt:
    arm: str
    route: str
    source: str
    file_id: str
    update: Mapping[str, float | int | str]
    claim_ceiling: str = IMPLEMENTATION_ONLY_CLAIM


@dataclass(frozen=True, slots=True)
class UpdateRoundReceipt:
    """One common route update applied once to each independent arm model."""

    update_cursor: int
    route: str
    source_files: tuple[tuple[str, str], ...]
    arm_updates: tuple[ArmUpdateReceipt, ...]
    claim_ceiling: str = IMPLEMENTATION_ONLY_CLAIM


def _checkpoint_bytes(model: EEAxisLCSRSThreeRoute) -> bytes:
    """Create the one in-memory initialization byte stream for every arm."""

    payload = BytesIO()
    torch.save(model.checkpoint_state(update_count=0), payload)
    return payload.getvalue()


def _checkpoint_from_bytes(payload: bytes) -> Mapping[str, Any]:
    try:
        state = torch.load(BytesIO(payload), map_location="cpu", weights_only=False)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise V023FiveArmOrchestratorError(
            "initialization bytes cannot be reopened"
        ) from error
    if not isinstance(state, Mapping):
        raise V023FiveArmOrchestratorError("initialization bytes contain no checkpoint")
    return state


def _assert_exact_keys(payload: Mapping[str, Any], expected: set[str]) -> None:
    if set(payload) != expected:
        raise V023FiveArmOrchestratorError("five-arm checkpoint schema drifted")


class V023FiveArmLearnerOrchestrator:
    """Five independent source-ablation learners over one fixed C1/C2/C3 order."""

    def __init__(
        self,
        config: V023FiveArmOrchestratorConfig,
        provider: DeterministicRouteBatchProvider,
    ) -> None:
        if not isinstance(config, V023FiveArmOrchestratorConfig):
            raise TypeError("config must be V023FiveArmOrchestratorConfig")
        if not isinstance(provider, DeterministicRouteBatchProvider):
            raise TypeError("provider does not satisfy DeterministicRouteBatchProvider")
        self.config = config
        self.provider = provider
        trainer_type = _load_existing_trainer_type()

        template = EEAxisLCSRSThreeRoute(
            config.model_config,
            train_seed=config.train_seed,
        )
        self._initialization_bytes = _checkpoint_bytes(template)
        self._initialization_sha256 = sha256(self._initialization_bytes).hexdigest()
        self.models: dict[str, EEAxisLCSRSThreeRoute] = {}
        self._trainers: dict[str, Any] = {}
        for arm in ARMS:
            model = EEAxisLCSRSThreeRoute(
                config.model_config,
                train_seed=config.train_seed,
            )
            model.load_checkpoint_state(_checkpoint_from_bytes(self._initialization_bytes))
            self.models[arm] = model
            self._trainers[arm] = trainer_type(model)
        self._assert_cross_arm_parameter_isolation()
        self.update_cursor = 0
        self._next_route_index = 0
        self._file_order: list[dict[str, Any]] = []

    @property
    def initialization_sha256(self) -> str:
        """Digest of the exact common initialization bytes used by all five arms."""

        return self._initialization_sha256

    @property
    def next_route(self) -> str:
        return ROUTE_ORDER[self._next_route_index]

    @property
    def completed_source_training_epochs(self) -> int:
        """Number of complete C1->C2->C3 update cycles."""

        return self.update_cursor // UPDATES_PER_SOURCE_TRAINING_EPOCH

    @property
    def file_order(self) -> tuple[Mapping[str, Any], ...]:
        """Immutable view of consumed provider identities in update order."""

        return tuple(deepcopy(self._file_order))

    def checkpoint_due(self) -> bool:
        return (
            self.update_cursor > 0
            and self._next_route_index == 0
            and self.update_cursor % self.config.checkpoint_cadence_updates == 0
        )

    def _assert_cross_arm_parameter_isolation(self) -> None:
        storage_owners: dict[int, tuple[str, int, int]] = {}
        for arm, model in self.models.items():
            for route_index, network in enumerate(model.q_networks):
                for parameter_index, parameter in enumerate(network.parameters()):
                    storage = parameter.detach().untyped_storage().data_ptr()
                    prior = storage_owners.get(storage)
                    if prior is not None:
                        raise V023FiveArmOrchestratorError(
                            "five arms share trainable parameter storage "
                            f"between {prior[0]} and {arm}"
                        )
                    storage_owners[storage] = (arm, route_index, parameter_index)

    @staticmethod
    def _checked_provided_batch(
        provided: object,
        *,
        route: str,
        source: str,
    ) -> ProvidedRouteBatch:
        if not isinstance(provided, ProvidedRouteBatch):
            raise TypeError("provider must return ProvidedRouteBatch")
        if provided.route != route or provided.source != source:
            raise V023FiveArmOrchestratorError(
                "provider batch route/source identity disagrees with requested mapping"
            )
        return provided

    def advance(self) -> UpdateRoundReceipt:
        """Advance exactly one route in C1 -> C2 -> C3 order across five arms."""

        route = self.next_route
        provided_by_source = {
            source: self._checked_provided_batch(
                self.provider.next_batch(
                    route=route,
                    source=source,
                    update_cursor=self.update_cursor,
                ),
                route=route,
                source=source,
            )
            for source in SOURCE_ORDER
        }
        arm_updates: list[ArmUpdateReceipt] = []
        for arm in ARMS:
            source = SOURCE_ABLATION_MAP[arm][route]
            provided = provided_by_source[source]
            update = self._trainers[arm].update_route(
                route,
                provided.batch,
                surfaces=provided.c3_surfaces or None,
            )
            arm_updates.append(
                ArmUpdateReceipt(
                    arm=arm,
                    route=route,
                    source=source,
                    file_id=provided.file_id,
                    update=deepcopy(update),
                    claim_ceiling=IMPLEMENTATION_ONLY_CLAIM,
                )
            )
        source_files = tuple(
            (source, provided_by_source[source].file_id) for source in SOURCE_ORDER
        )
        receipt = UpdateRoundReceipt(
            update_cursor=self.update_cursor,
            route=route,
            source_files=source_files,
            arm_updates=tuple(arm_updates),
            claim_ceiling=IMPLEMENTATION_ONLY_CLAIM,
        )
        self._file_order.append(
            {
                "update_cursor": self.update_cursor,
                "route": route,
                "source_files": list(source_files),
            }
        )
        self.update_cursor += 1
        self._next_route_index = self.update_cursor % len(ROUTE_ORDER)
        return receipt

    def advance_many(self, updates: int) -> tuple[UpdateRoundReceipt, ...]:
        if isinstance(updates, bool) or not isinstance(updates, int) or updates < 0:
            raise ValueError("updates must be a nonnegative integer")
        return tuple(self.advance() for _ in range(updates))

    def checkpoint_state(self) -> dict[str, Any]:
        """Capture exact model/optimizer and provider sampler state in memory.

        This produces a state mapping only.  It intentionally performs no
        checkpoint file or experiment-artifact write.
        """

        sampler_state = self.provider.sampler_state()
        if not isinstance(sampler_state, Mapping):
            raise TypeError("provider sampler_state must return a mapping")
        return deepcopy(
            {
                "schema": ORCHESTRATOR_SCHEMA,
                "claim_ceiling": IMPLEMENTATION_ONLY_CLAIM,
                "config": asdict(self.config),
                "formal_checkpoint_cadence_epochs": FORMAL_CHECKPOINT_CADENCE_EPOCHS,
                "formal_checkpoint_cadence_updates": FORMAL_CHECKPOINT_CADENCE_UPDATES,
                "updates_per_source_training_epoch": UPDATES_PER_SOURCE_TRAINING_EPOCH,
                "completed_source_training_epochs": self.completed_source_training_epochs,
                "arm_order": list(ARMS),
                "route_order": list(ROUTE_ORDER),
                "source_ablation_map": _source_ablation_map_payload(),
                "initialization": {
                    "lineage": self.config.lineage,
                    "sha256": self._initialization_sha256,
                    "bytes": self._initialization_bytes,
                },
                "update_cursor": self.update_cursor,
                "next_route_index": self._next_route_index,
                "file_order": self._file_order,
                "provider_sampler_state": dict(sampler_state),
                "arms": {
                    arm: self._trainers[arm].checkpoint_state(
                        update_count=self.update_cursor
                    )
                    for arm in ARMS
                },
            }
        )

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> None:
        """Restore a complete five-arm checkpoint and the provider sampler state."""

        if not isinstance(state, Mapping):
            raise TypeError("checkpoint state must be a mapping")
        _assert_exact_keys(
            state,
            {
                "schema",
                "claim_ceiling",
                "config",
                "formal_checkpoint_cadence_epochs",
                "formal_checkpoint_cadence_updates",
                "updates_per_source_training_epoch",
                "completed_source_training_epochs",
                "arm_order",
                "route_order",
                "source_ablation_map",
                "initialization",
                "update_cursor",
                "next_route_index",
                "file_order",
                "provider_sampler_state",
                "arms",
            },
        )
        if state["schema"] != ORCHESTRATOR_SCHEMA:
            raise V023FiveArmOrchestratorError("unsupported five-arm checkpoint schema")
        if state["claim_ceiling"] != IMPLEMENTATION_ONLY_CLAIM:
            raise V023FiveArmOrchestratorError("five-arm checkpoint claim ceiling drifted")
        if state["config"] != asdict(self.config):
            raise V023FiveArmOrchestratorError("five-arm checkpoint config mismatch")
        if state["formal_checkpoint_cadence_updates"] != FORMAL_CHECKPOINT_CADENCE_UPDATES:
            raise V023FiveArmOrchestratorError("formal checkpoint cadence drifted")
        if (
            state["formal_checkpoint_cadence_epochs"]
            != FORMAL_CHECKPOINT_CADENCE_EPOCHS
            or state["updates_per_source_training_epoch"]
            != UPDATES_PER_SOURCE_TRAINING_EPOCH
        ):
            raise V023FiveArmOrchestratorError("source-training epoch definition drifted")
        if state["arm_order"] != list(ARMS) or state["route_order"] != list(ROUTE_ORDER):
            raise V023FiveArmOrchestratorError("five-arm checkpoint arm or route order drifted")
        if state["source_ablation_map"] != _source_ablation_map_payload():
            raise V023FiveArmOrchestratorError("five-arm checkpoint source mapping drifted")
        initialization = state["initialization"]
        if not isinstance(initialization, Mapping) or set(initialization) != {
            "lineage",
            "sha256",
            "bytes",
        }:
            raise V023FiveArmOrchestratorError("initialization checkpoint schema drifted")
        if (
            initialization["lineage"] != self.config.lineage
            or initialization["sha256"] != self._initialization_sha256
            or initialization["bytes"] != self._initialization_bytes
        ):
            raise V023FiveArmOrchestratorError("five-arm initialization bytes mismatch")
        update_cursor = state["update_cursor"]
        next_route_index = state["next_route_index"]
        if (
            isinstance(update_cursor, bool)
            or not isinstance(update_cursor, int)
            or update_cursor < 0
            or isinstance(next_route_index, bool)
            or not isinstance(next_route_index, int)
            or next_route_index != update_cursor % len(ROUTE_ORDER)
        ):
            raise V023FiveArmOrchestratorError("five-arm checkpoint cursor is invalid")
        if state["completed_source_training_epochs"] != (
            update_cursor // UPDATES_PER_SOURCE_TRAINING_EPOCH
        ):
            raise V023FiveArmOrchestratorError(
                "completed source-training epoch count drifted"
            )
        file_order = state["file_order"]
        if not isinstance(file_order, list) or len(file_order) != update_cursor:
            raise V023FiveArmOrchestratorError("five-arm checkpoint file order is invalid")
        for cursor, entry in enumerate(file_order):
            if not isinstance(entry, Mapping) or set(entry) != {
                "update_cursor",
                "route",
                "source_files",
            }:
                raise V023FiveArmOrchestratorError("five-arm checkpoint file order schema drifted")
            expected_files = entry["source_files"]
            if (
                entry["update_cursor"] != cursor
                or entry["route"] != ROUTE_ORDER[cursor % len(ROUTE_ORDER)]
                or not isinstance(expected_files, list)
                or len(expected_files) != len(SOURCE_ORDER)
                or any(
                    not isinstance(pair, (list, tuple))
                    or len(pair) != 2
                    or pair[0] != source
                    or not isinstance(pair[1], str)
                    or not pair[1]
                    for source, pair in zip(SOURCE_ORDER, expected_files, strict=True)
                )
            ):
                raise V023FiveArmOrchestratorError("five-arm checkpoint file order drifted")
        sampler_state = state["provider_sampler_state"]
        if not isinstance(sampler_state, Mapping):
            raise V023FiveArmOrchestratorError("provider sampler state is invalid")
        arms = state["arms"]
        if not isinstance(arms, Mapping) or set(arms) != set(ARMS):
            raise V023FiveArmOrchestratorError("five-arm checkpoint arm states drifted")
        for arm in ARMS:
            loaded_count = self._trainers[arm].load_checkpoint_state(arms[arm])
            if loaded_count != update_cursor:
                raise V023FiveArmOrchestratorError(
                    "arm checkpoint update cursor disagrees with five-arm cursor"
                )
        self.provider.load_sampler_state(deepcopy(dict(sampler_state)))
        self.update_cursor = update_cursor
        self._next_route_index = next_route_index
        self._file_order = deepcopy(file_order)
        self._assert_cross_arm_parameter_isolation()


__all__ = [
    "ARMS",
    "FORMAL_CHECKPOINT_CADENCE_EPOCHS",
    "FORMAL_CHECKPOINT_CADENCE_UPDATES",
    "IMPLEMENTATION_ONLY_CLAIM",
    "ORCHESTRATOR_SCHEMA",
    "ROUTE_ORDER",
    "SOURCE_ABLATION_MAP",
    "SOURCE_ORDER",
    "UPDATES_PER_SOURCE_TRAINING_EPOCH",
    "ArmUpdateReceipt",
    "DeterministicRouteBatchProvider",
    "ProvidedRouteBatch",
    "UpdateRoundReceipt",
    "V023FiveArmLearnerOrchestrator",
    "V023FiveArmOrchestratorConfig",
    "V023FiveArmOrchestratorError",
]
