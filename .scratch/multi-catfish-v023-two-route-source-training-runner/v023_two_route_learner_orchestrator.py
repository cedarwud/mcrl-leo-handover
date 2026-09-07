"""C1/C2-only source-ablation learner orchestrator for the V0.23 successor."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import importlib.util
from pathlib import Path
import re
import sys
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ee_axis_two_route_model import (
    EEAxisTwoRouteConfig,
    EEAxisTwoRouteModel,
    ROUTES,
    TWO_ROUTE_ALGORITHM,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014NormalizedPairBatch
from mcrl.errors import MCRLContractError


HETEROGENEOUS_TRAINER_PATH = (
    HERE.parent
    / "multi-catfish-v023-heterogeneous-trainer"
    / "v023_heterogeneous_trainer.py"
)
ORCHESTRATOR_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-two-route-learner-orchestrator-v1"
)
IMPLEMENTATION_ONLY_CLAIM = (
    "TRAIN_DEVELOPMENT_C1C2_SUCCESSOR_SOURCE_TRAINING_NO_C3_NO_TEST_NO_EFFICACY"
)
ARMS = ("FULL2", "DROP_C1", "DROP_C2")
ROUTE_ORDER = ROUTES
SOURCE_ORDER = ("neutral", "informed")
UPDATES_PER_SOURCE_TRAINING_EPOCH = 2
FORMAL_CHECKPOINT_CADENCE_EPOCHS = 100
FORMAL_CHECKPOINT_CADENCE_UPDATES = 200
SOURCE_ABLATION_MAP: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "FULL2": MappingProxyType({"C1": "informed", "C2": "informed"}),
        "DROP_C1": MappingProxyType({"C1": "neutral", "C2": "informed"}),
        "DROP_C2": MappingProxyType({"C1": "informed", "C2": "neutral"}),
    }
)


class V023TwoRouteOrchestratorError(MCRLContractError):
    """The closed C1/C2 orchestration contract was violated."""


def _load_existing_trainer_type() -> type[Any]:
    """Import the existing C1/C2 update implementation without copying it."""

    if HETEROGENEOUS_TRAINER_PATH.is_symlink() or not HETEROGENEOUS_TRAINER_PATH.is_file():
        raise V023TwoRouteOrchestratorError("existing heterogeneous trainer is unavailable")
    spec = importlib.util.spec_from_file_location(
        "v023_heterogeneous_trainer_two_route_base",
        HETEROGENEOUS_TRAINER_PATH,
    )
    if spec is None or spec.loader is None:
        raise V023TwoRouteOrchestratorError("cannot import existing heterogeneous trainer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trainer = getattr(module, "V023HeterogeneousTrainer", None)
    if not isinstance(trainer, type):
        raise V023TwoRouteOrchestratorError("existing trainer type is missing")
    return trainer


_ExistingHeterogeneousTrainer = _load_existing_trainer_type()


class V023TwoRouteTrainer(_ExistingHeterogeneousTrainer):
    """Reuse the existing C1/C2 methods against an exactly two-head model."""

    def __init__(self, model: EEAxisTwoRouteModel) -> None:
        if not isinstance(model, EEAxisTwoRouteModel):
            raise TypeError("model must be EEAxisTwoRouteModel")
        self.model = model
        self._validate_parameter_and_optimizer_isolation()

    def _validate_parameter_and_optimizer_isolation(self) -> None:
        if len(self.model.q_networks) != 2 or len(self.model.optimizers) != 2:
            raise V023TwoRouteOrchestratorError("trainer requires exactly two heads")
        self.model._assert_isolation()
        expected_rates = (self.model.config.q1.learning_rate, self.model.config.q2.learning_rate)
        for index, (optimizer, rate) in enumerate(
            zip(self.model.optimizers, expected_rates, strict=True)
        ):
            if len(optimizer.param_groups) != 1 or float(optimizer.param_groups[0]["lr"]) != float(rate):
                raise V023TwoRouteOrchestratorError(
                    f"optimizer {index} learning rate drifts from route config"
                )

    def update_route(
        self,
        route: str,
        batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch,
        *,
        surfaces: object = None,
    ) -> dict[str, float | int | str]:
        if surfaces is not None:
            raise V023TwoRouteOrchestratorError("C3 surfaces are forbidden")
        if route == "C1":
            return self.update_c1(batch)  # type: ignore[arg-type]
        if route == "C2":
            return self.update_c2(batch)  # type: ignore[arg-type]
        raise V023TwoRouteOrchestratorError("route must be C1 or C2; C3 is forbidden")

    def checkpoint_state(
        self, *, update_count: int, route_update_counts: Mapping[str, int]
    ) -> dict[str, Any]:
        return self.model.checkpoint_state(
            update_count=update_count,
            route_update_counts=route_update_counts,
        )

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        count = self.model.load_checkpoint_state(state)
        self._validate_parameter_and_optimizer_isolation()
        self._clear_all_gradients()
        return count


@dataclass(frozen=True, slots=True)
class ProvidedRouteBatch:
    route: str
    source: str
    file_id: str
    batch: EEAxisPairBatch | EEAxisV014NormalizedPairBatch

    def __post_init__(self) -> None:
        if self.route not in ROUTE_ORDER:
            raise ValueError("route must be C1 or C2")
        if self.source not in SOURCE_ORDER:
            raise ValueError("source must be neutral or informed")
        if not isinstance(self.file_id, str) or not self.file_id or self.file_id != self.file_id.strip():
            raise ValueError("file_id must be a nonempty trimmed identifier")
        if "TEST" in re.split(r"[/\\]+", self.file_id.upper()):
            raise ValueError("TEST source paths are forbidden")
        if self.route == "C1" and not isinstance(self.batch, EEAxisPairBatch):
            raise TypeError("C1 provider batch must be EEAxisPairBatch")
        if self.route == "C2" and not isinstance(self.batch, EEAxisV014NormalizedPairBatch):
            raise TypeError("C2 provider batch must be normalized OPS-3 Q2")


@runtime_checkable
class DeterministicRouteBatchProvider(Protocol):
    def next_batch(self, *, route: str, source: str, update_cursor: int) -> object: ...
    def sampler_state(self) -> Mapping[str, Any]: ...
    def load_sampler_state(self, state: Mapping[str, Any]) -> None: ...


@dataclass(frozen=True, slots=True)
class V023TwoRouteOrchestratorConfig:
    model_config: EEAxisTwoRouteConfig
    train_seed: int
    lineage: str = "v023-c1c2-successor-two-route"
    checkpoint_cadence_updates: int = FORMAL_CHECKPOINT_CADENCE_UPDATES
    formal_use: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.model_config, EEAxisTwoRouteConfig):
            raise TypeError("model_config must be EEAxisTwoRouteConfig")
        if isinstance(self.train_seed, bool) or not isinstance(self.train_seed, int):
            raise TypeError("train_seed must be an integer")
        if not isinstance(self.lineage, str) or not self.lineage or self.lineage != self.lineage.strip():
            raise ValueError("lineage must be a nonempty trimmed string")
        if isinstance(self.checkpoint_cadence_updates, bool) or not isinstance(self.checkpoint_cadence_updates, int) or self.checkpoint_cadence_updates < 1:
            raise ValueError("checkpoint cadence must be a positive integer")
        if self.formal_use and self.checkpoint_cadence_updates != 200:
            raise ValueError("formal use requires exactly 100 C1/C2 epochs = 200 updates")

    @classmethod
    def formal(
        cls, *, model_config: EEAxisTwoRouteConfig, train_seed: int
    ) -> "V023TwoRouteOrchestratorConfig":
        return cls(model_config=model_config, train_seed=train_seed, formal_use=True)


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
    update_cursor: int
    route: str
    source_files: tuple[tuple[str, str], ...]
    arm_updates: tuple[ArmUpdateReceipt, ...]
    claim_ceiling: str = IMPLEMENTATION_ONLY_CLAIM


def _source_map_payload() -> dict[str, dict[str, str]]:
    return {arm: dict(SOURCE_ABLATION_MAP[arm]) for arm in ARMS}


def _torch_bytes(value: object) -> bytes:
    stream = BytesIO()
    torch.save(value, stream)
    return stream.getvalue()


def _identity_payload(provider: object) -> object:
    candidate = getattr(provider, "provider_identity_payload", None)
    return candidate() if callable(candidate) else candidate


def _listed_routes(value: object, *, route_context: bool = False) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_context = route_context or "route" in str(key).lower()
            found.extend(_listed_routes(item, route_context=key_context))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            found.extend(_listed_routes(item, route_context=route_context))
    elif route_context and isinstance(value, str) and value.upper().startswith("C"):
        found.append(value.upper())
    return found


def _contains_test_path(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_test_path(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_test_path(item) for item in value)
    if isinstance(value, str) and ("/" in value or "\\" in value):
        return "TEST" in re.split(r"[/\\]+", value.upper())
    return False


def validate_two_route_provider_identity(provider: object) -> None:
    """Reject any provider identity/attribute that declares a third route."""

    candidates = [
        _identity_payload(provider),
        getattr(provider, "routes", None),
        getattr(provider, "route_order", None),
        getattr(provider, "route_names", None),
    ]
    for candidate in candidates:
        if _contains_test_path(candidate):
            raise V023TwoRouteOrchestratorError("provider identity contains a TEST path")
        routes = _listed_routes(candidate, route_context=not isinstance(candidate, Mapping))
        if any(route not in ROUTE_ORDER for route in routes):
            raise V023TwoRouteOrchestratorError("provider identity lists a third route")


class V023TwoRouteLearnerOrchestrator:
    """Three independent learners advanced in the fixed C1 -> C2 cycle."""

    def __init__(
        self,
        config: V023TwoRouteOrchestratorConfig,
        provider: DeterministicRouteBatchProvider,
    ) -> None:
        if not isinstance(config, V023TwoRouteOrchestratorConfig):
            raise TypeError("config must be V023TwoRouteOrchestratorConfig")
        if not isinstance(provider, DeterministicRouteBatchProvider):
            raise TypeError("provider does not satisfy DeterministicRouteBatchProvider")
        validate_two_route_provider_identity(provider)
        self.config = config
        self.provider = provider
        template = EEAxisTwoRouteModel(config.model_config, train_seed=config.train_seed)
        self._initialization_bytes = _torch_bytes(
            template.checkpoint_state(update_count=0, route_update_counts={"C1": 0, "C2": 0})
        )
        self._initialization_sha256 = sha256(self._initialization_bytes).hexdigest()
        self.models: dict[str, EEAxisTwoRouteModel] = {}
        self._trainers: dict[str, V023TwoRouteTrainer] = {}
        for arm in ARMS:
            model = EEAxisTwoRouteModel(config.model_config, train_seed=config.train_seed)
            initial = torch.load(BytesIO(self._initialization_bytes), map_location="cpu", weights_only=False)
            model.load_checkpoint_state(initial)
            self.models[arm] = model
            self._trainers[arm] = V023TwoRouteTrainer(model)
        self._assert_cross_arm_isolation()
        self.update_cursor = 0
        self._next_route_index = 0
        self._file_order: list[dict[str, Any]] = []

    @property
    def initialization_sha256(self) -> str:
        return self._initialization_sha256

    @property
    def next_route(self) -> str:
        return ROUTE_ORDER[self._next_route_index]

    @property
    def completed_source_training_epochs(self) -> int:
        return self.update_cursor // 2

    @property
    def route_update_counts(self) -> dict[str, int]:
        completed, remainder = divmod(self.update_cursor, 2)
        return {"C1": completed + int(remainder > 0), "C2": completed}

    def _assert_cross_arm_isolation(self) -> None:
        owners: dict[int, str] = {}
        for arm, model in self.models.items():
            for network in model.q_networks:
                for parameter in network.parameters():
                    pointer = parameter.detach().untyped_storage().data_ptr()
                    if pointer in owners:
                        raise V023TwoRouteOrchestratorError(
                            f"arms {owners[pointer]} and {arm} share parameter storage"
                        )
                    owners[pointer] = arm

    @staticmethod
    def _checked_batch(provided: object, *, route: str, source: str) -> ProvidedRouteBatch:
        try:
            converted = ProvidedRouteBatch(
                route=getattr(provided, "route"),
                source=getattr(provided, "source"),
                file_id=getattr(provided, "file_id"),
                batch=getattr(provided, "batch"),
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise V023TwoRouteOrchestratorError("provider returned an invalid C1/C2 batch") from error
        if converted.route != route or converted.source != source:
            raise V023TwoRouteOrchestratorError("provider batch route/source mismatch")
        if hasattr(provided, "c3_surfaces") and getattr(provided, "c3_surfaces"):
            raise V023TwoRouteOrchestratorError("provider batch carries forbidden C3 surfaces")
        return converted

    def advance(self) -> UpdateRoundReceipt:
        route = self.next_route
        provided_by_source = {
            source: self._checked_batch(
                self.provider.next_batch(
                    route=route, source=source, update_cursor=self.update_cursor
                ),
                route=route,
                source=source,
            )
            for source in SOURCE_ORDER
        }
        arm_updates = []
        for arm in ARMS:
            source = SOURCE_ABLATION_MAP[arm][route]
            provided = provided_by_source[source]
            arm_updates.append(
                ArmUpdateReceipt(
                    arm=arm,
                    route=route,
                    source=source,
                    file_id=provided.file_id,
                    update=deepcopy(
                        self._trainers[arm].update_route(route, provided.batch)
                    ),
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
        )
        self._file_order.append(
            {"update_cursor": self.update_cursor, "route": route, "source_files": list(source_files)}
        )
        self.update_cursor += 1
        self._next_route_index = self.update_cursor % 2
        return receipt

    def advance_many(self, updates: int) -> tuple[UpdateRoundReceipt, ...]:
        if isinstance(updates, bool) or not isinstance(updates, int) or updates < 0:
            raise ValueError("updates must be a nonnegative integer")
        return tuple(self.advance() for _ in range(updates))

    def checkpoint_state(self) -> dict[str, Any]:
        sampler = self.provider.sampler_state()
        if not isinstance(sampler, Mapping):
            raise TypeError("provider sampler_state must return a mapping")
        counts = self.route_update_counts
        return deepcopy(
            {
                "schema": ORCHESTRATOR_SCHEMA,
                "claim_ceiling": IMPLEMENTATION_ONLY_CLAIM,
                "config": asdict(self.config),
                "arm_order": list(ARMS),
                "route_order": list(ROUTE_ORDER),
                "source_ablation_map": _source_map_payload(),
                "initialization": {
                    "sha256": self._initialization_sha256,
                    "bytes": self._initialization_bytes,
                },
                "formal_checkpoint_cadence_epochs": 100,
                "formal_checkpoint_cadence_updates": 200,
                "updates_per_source_training_epoch": 2,
                "completed_source_training_epochs": self.completed_source_training_epochs,
                "update_cursor": self.update_cursor,
                "next_route_index": self._next_route_index,
                "route_update_counts": counts,
                "file_order": self._file_order,
                "provider_sampler_state": dict(sampler),
                "arms": {
                    arm: self._trainers[arm].checkpoint_state(
                        update_count=self.update_cursor,
                        route_update_counts=counts,
                    )
                    for arm in ARMS
                },
            }
        )

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> None:
        expected = {
            "schema", "claim_ceiling", "config", "arm_order", "route_order",
            "source_ablation_map", "initialization", "formal_checkpoint_cadence_epochs",
            "formal_checkpoint_cadence_updates", "updates_per_source_training_epoch",
            "completed_source_training_epochs", "update_cursor", "next_route_index",
            "route_update_counts", "file_order", "provider_sampler_state", "arms",
        }
        if not isinstance(state, Mapping) or set(state) != expected:
            raise V023TwoRouteOrchestratorError("orchestrator checkpoint schema drifted")
        if state["schema"] != ORCHESTRATOR_SCHEMA or state["claim_ceiling"] != IMPLEMENTATION_ONLY_CLAIM:
            raise V023TwoRouteOrchestratorError("orchestrator checkpoint identity drifted")
        if state["config"] != asdict(self.config):
            raise V023TwoRouteOrchestratorError("orchestrator config mismatch")
        if state["arm_order"] != list(ARMS) or state["route_order"] != list(ROUTE_ORDER):
            raise V023TwoRouteOrchestratorError("arm or route order drifted")
        if state["source_ablation_map"] != _source_map_payload():
            raise V023TwoRouteOrchestratorError("source map drifted")
        if state["initialization"] != {"sha256": self._initialization_sha256, "bytes": self._initialization_bytes}:
            raise V023TwoRouteOrchestratorError("initialization bytes mismatch")
        if (
            state["formal_checkpoint_cadence_epochs"] != 100
            or state["formal_checkpoint_cadence_updates"] != 200
            or state["updates_per_source_training_epoch"] != 2
        ):
            raise V023TwoRouteOrchestratorError("checkpoint cadence drifted")
        cursor = state["update_cursor"]
        if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor < 0:
            raise V023TwoRouteOrchestratorError("update cursor is invalid")
        if state["next_route_index"] != cursor % 2:
            raise V023TwoRouteOrchestratorError("next route cursor drifted")
        completed, remainder = divmod(cursor, 2)
        counts = {"C1": completed + int(remainder > 0), "C2": completed}
        if state["completed_source_training_epochs"] != completed or state["route_update_counts"] != counts:
            raise V023TwoRouteOrchestratorError("route update counts drifted")
        file_order = state["file_order"]
        if not isinstance(file_order, list) or len(file_order) != cursor:
            raise V023TwoRouteOrchestratorError("file order is invalid")
        for index, entry in enumerate(file_order):
            if (
                not isinstance(entry, Mapping)
                or entry.get("update_cursor") != index
                or entry.get("route") != ROUTE_ORDER[index % 2]
                or not isinstance(entry.get("source_files"), list)
            ):
                raise V023TwoRouteOrchestratorError("file order drifted")
        arms = state["arms"]
        if not isinstance(arms, Mapping) or tuple(arms) != ARMS:
            raise V023TwoRouteOrchestratorError("arm states drifted")
        for arm in ARMS:
            if arms[arm].get("algorithm") != TWO_ROUTE_ALGORITHM:
                raise V023TwoRouteOrchestratorError("non-two-route arm checkpoint rejected")
            if self._trainers[arm].load_checkpoint_state(arms[arm]) != cursor:
                raise V023TwoRouteOrchestratorError("arm update cursor drifted")
        sampler = state["provider_sampler_state"]
        if not isinstance(sampler, Mapping):
            raise V023TwoRouteOrchestratorError("provider sampler state is invalid")
        self.provider.load_sampler_state(deepcopy(dict(sampler)))
        self.update_cursor = cursor
        self._next_route_index = cursor % 2
        self._file_order = deepcopy(file_order)
        self._assert_cross_arm_isolation()


__all__ = [
    "ARMS", "DeterministicRouteBatchProvider", "FORMAL_CHECKPOINT_CADENCE_EPOCHS",
    "FORMAL_CHECKPOINT_CADENCE_UPDATES", "IMPLEMENTATION_ONLY_CLAIM",
    "ORCHESTRATOR_SCHEMA", "ProvidedRouteBatch", "ROUTE_ORDER", "SOURCE_ABLATION_MAP",
    "SOURCE_ORDER", "UPDATES_PER_SOURCE_TRAINING_EPOCH", "V023TwoRouteLearnerOrchestrator",
    "V023TwoRouteOrchestratorConfig", "V023TwoRouteOrchestratorError",
    "validate_two_route_provider_identity",
]
