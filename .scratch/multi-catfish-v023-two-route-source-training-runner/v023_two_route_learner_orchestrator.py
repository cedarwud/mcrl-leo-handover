"""C1/C2-only source-ablation learner orchestrator for the V0.23 successor."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import importlib
import json
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
    FORMAL_TRAIN_SEED,
    FROZEN_MODEL_CONFIG_SHA256,
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
FACTORY_V3_DIR = HERE.parent / "multi-catfish-v023-c1c2-provider-factory-v3"
if str(FACTORY_V3_DIR) not in sys.path:
    sys.path.insert(0, str(FACTORY_V3_DIR))
from v023_c1c2_provider_factory_v3 import (
    PROVIDER_IDENTITY_FIELDS as FACTORY_V3_IDENTITY_FIELDS,
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
    directory = str(HETEROGENEOUS_TRAINER_PATH.parent)
    sys.path.insert(0, directory)
    try:
        module = importlib.import_module("v023_heterogeneous_trainer")
    except Exception as error:
        raise V023TwoRouteOrchestratorError(
            "cannot import existing heterogeneous trainer"
        ) from error
    finally:
        if sys.path and sys.path[0] == directory:
            sys.path.pop(0)
        else:
            sys.path.remove(directory)
    if Path(module.__file__).resolve(strict=True) != HETEROGENEOUS_TRAINER_PATH.resolve(strict=True):
        raise V023TwoRouteOrchestratorError(
            "existing heterogeneous trainer has an unexpected natural origin"
        )
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
    model_config_sha256: str
    lineage: str = "v023-c1c2-successor-two-route"
    checkpoint_cadence_updates: int = FORMAL_CHECKPOINT_CADENCE_UPDATES
    formal_use: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.model_config, EEAxisTwoRouteConfig):
            raise TypeError("model_config must be EEAxisTwoRouteConfig")
        if type(self.train_seed) is not int:
            raise TypeError("train_seed must be an integer")
        if type(self.formal_use) is not bool:
            raise TypeError("formal_use must be a Boolean")
        if not isinstance(self.lineage, str) or not self.lineage or self.lineage != self.lineage.strip():
            raise ValueError("lineage must be a nonempty trimmed string")
        if isinstance(self.checkpoint_cadence_updates, bool) or not isinstance(self.checkpoint_cadence_updates, int) or self.checkpoint_cadence_updates < 1:
            raise ValueError("checkpoint cadence must be a positive integer")
        if self.formal_use:
            if self.checkpoint_cadence_updates != 200:
                raise ValueError("formal use requires exactly 100 C1/C2 epochs = 200 updates")
            if self.train_seed != FORMAL_TRAIN_SEED:
                raise ValueError(f"formal train seed must be exactly {FORMAL_TRAIN_SEED}")
            if self.model_config_sha256 != FROZEN_MODEL_CONFIG_SHA256:
                raise ValueError("formal model configuration digest drifted")

    @classmethod
    def formal(
        cls,
        *,
        model_config: EEAxisTwoRouteConfig,
        train_seed: int,
        model_config_sha256: str,
    ) -> "V023TwoRouteOrchestratorConfig":
        return cls(
            model_config=model_config,
            train_seed=train_seed,
            model_config_sha256=model_config_sha256,
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


FACTORY_V3_IDENTITY_SCHEMA = (
    "multi-catfish-mcrl-v023-c1c2-successor-provider-identity-v3"
)
FACTORY_V3_SCHEMA = "multi-catfish-mcrl-v023-c1c2-successor-provider-factory-v3"
NONFORMAL_REHEARSAL_IDENTITY_FIELDS = FACTORY_V3_IDENTITY_FIELDS - {
    "predecessor_manifest_sha256",
    "prereg_sha256",
    "scientific_declaration_sha256",
    "tle_file_set_sha256",
}


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise V023TwoRouteOrchestratorError(
            "provider identity is not canonical finite JSON"
        ) from error
    return sha256(encoded).hexdigest()


def _identity_tokens(value: str) -> list[str]:
    denial_safe = re.sub(
        r"(?<![A-Z0-9])NO(?:[_ -]+)(?:R7|Q3|C3|TEST)(?![A-Z0-9])",
        "",
        value.upper(),
    )
    return re.split(r"[^A-Z0-9]+", denial_safe)


def _semantic_identity_field(field: str) -> bool:
    tokens = set(re.split(r"[^a-z0-9]+", field.lower()))
    return bool(
        tokens
        & {
            "route", "routes", "arm", "arms", "source", "sources",
            "schema", "claim", "claims", "config", "split",
        }
    )


def _identity_path_or_digest_field(field: str) -> bool:
    normalized = field.lower()
    return (
        normalized.endswith("sha256")
        or "digest" in normalized
        or any(
            token in set(re.split(r"[^a-z0-9]+", normalized))
            for token in {"path", "paths", "file", "files", "module", "loaded"}
        )
    )


def _reject_forbidden_identity_fields(
    value: object, *, field: str = "", closure_context: bool = False
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            child_closure = closure_context or normalized in {
                "learner_runtime", "bindings", "manifest_files", "consumed_files",
            }
            if not child_closure and any(
                token in {"R7", "Q3", "C3"}
                for token in _identity_tokens(str(key))
            ):
                raise V023TwoRouteOrchestratorError(
                    "provider identity contains a forbidden R7/Q3/C3 field"
                )
            _reject_forbidden_identity_fields(
                item, field=str(key), closure_context=child_closure
            )
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            _reject_forbidden_identity_fields(
                item, field=field, closure_context=closure_context
            )
    elif (
        isinstance(value, str)
        and not closure_context
        and not _identity_path_or_digest_field(field)
        and _semantic_identity_field(field)
    ):
        tokens = _identity_tokens(value)
        if any(token in {"R7", "Q3", "C3"} for token in tokens):
            raise V023TwoRouteOrchestratorError(
                "provider identity contains a forbidden R7/Q3/C3 value"
            )
        if "TEST" in tokens:
            raise V023TwoRouteOrchestratorError(
                "provider identity contains the closed TEST split"
            )


def _authenticate_provider_identity(
    provider: object,
    *,
    expected_train_seed: int,
    expected_epoch_budget: int,
    expected_model_config_sha256: str,
    required_fields: frozenset[str],
) -> Mapping[str, Any]:
    payload = _identity_payload(provider)
    identity = getattr(provider, "provider_identity", None)
    identity = identity() if callable(identity) else identity
    if not isinstance(payload, Mapping) or set(payload) != required_fields:
        raise V023TwoRouteOrchestratorError(
            "provider is not an authenticated factory-v3 identity"
        )
    _reject_forbidden_identity_fields(payload)
    if (
        payload.get("schema") != FACTORY_V3_IDENTITY_SCHEMA
        or payload.get("routes") != ["C1", "C2"]
        or payload.get("sources") != ["neutral", "informed"]
        or payload.get("epoch_budget") != expected_epoch_budget
        or payload.get("train_seed") != expected_train_seed
        or payload.get("model_config_sha256") != expected_model_config_sha256
    ):
        raise V023TwoRouteOrchestratorError(
            "factory-v3 provider identity boundary drifted"
        )
    expected_identity = f"{FACTORY_V3_SCHEMA}:{_canonical_sha256(payload)}"
    if identity != expected_identity:
        raise V023TwoRouteOrchestratorError(
            "factory-v3 provider identity digest is unauthenticated"
        )
    return deepcopy(dict(payload))


def authenticate_factory_v3_provider_identity(
    provider: object,
    *,
    expected_train_seed: int,
    expected_model_config_sha256: str,
) -> Mapping[str, Any]:
    if expected_train_seed != FORMAL_TRAIN_SEED:
        raise V023TwoRouteOrchestratorError(
            f"formal train seed must be exactly {FORMAL_TRAIN_SEED}"
        )
    return _authenticate_provider_identity(
        provider,
        expected_train_seed=expected_train_seed,
        expected_epoch_budget=100,
        expected_model_config_sha256=expected_model_config_sha256,
        required_fields=FACTORY_V3_IDENTITY_FIELDS,
    )


def authenticate_nonformal_rehearsal_provider_identity(
    provider: object,
    *,
    expected_train_seed: int,
    expected_epoch_budget: int,
    expected_model_config_sha256: str,
) -> Mapping[str, Any]:
    if type(expected_train_seed) is not int:
        raise TypeError("non-formal train seed must be an integer")
    if (
        isinstance(expected_epoch_budget, bool)
        or not isinstance(expected_epoch_budget, int)
        or expected_epoch_budget < 1
    ):
        raise ValueError("non-formal epoch budget must be a positive integer")
    return _authenticate_provider_identity(
        provider,
        expected_train_seed=expected_train_seed,
        expected_epoch_budget=expected_epoch_budget,
        expected_model_config_sha256=expected_model_config_sha256,
        required_fields=NONFORMAL_REHEARSAL_IDENTITY_FIELDS,
    )


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
        if config.formal_use:
            authenticate_factory_v3_provider_identity(
                provider,
                expected_train_seed=config.train_seed,
                expected_model_config_sha256=config.model_config_sha256,
            )
        else:
            identity_payload = _identity_payload(provider)
            budget = (
                identity_payload.get("epoch_budget")
                if isinstance(identity_payload, Mapping)
                else None
            )
            declared_budget = getattr(provider, "planned_epoch_budget", None)
            declared_budget = (
                declared_budget() if callable(declared_budget) else declared_budget
            )
            if declared_budget is not None and declared_budget != budget:
                raise V023TwoRouteOrchestratorError(
                    "non-formal provider epoch-budget declaration drifted"
                )
            authenticate_nonformal_rehearsal_provider_identity(
                provider,
                expected_train_seed=config.train_seed,
                expected_epoch_budget=budget,
                expected_model_config_sha256=config.model_config_sha256,
            )
        authenticated_sampler = provider.sampler_state()
        if (
            not isinstance(authenticated_sampler, Mapping)
            or authenticated_sampler.get("next_update_cursor") != 0
            or authenticated_sampler.get("next_source_index") != 0
            or authenticated_sampler.get("consumed_file_order") != []
            or any(
                value != 0
                for value in authenticated_sampler.get("cursors", {}).values()
            )
        ):
            raise V023TwoRouteOrchestratorError(
                "learner construction requires authenticated fresh provider state"
            )
        self.config = config
        self.provider = provider
        template = EEAxisTwoRouteModel(
            config.model_config,
            train_seed=config.train_seed,
            formal=config.formal_use,
        )
        self._initialization_bytes = _torch_bytes(
            template.checkpoint_state(update_count=0, route_update_counts={"C1": 0, "C2": 0})
        )
        self._initialization_sha256 = sha256(self._initialization_bytes).hexdigest()
        self.models: dict[str, EEAxisTwoRouteModel] = {}
        self._trainers: dict[str, V023TwoRouteTrainer] = {}
        for arm in ARMS:
            model = EEAxisTwoRouteModel(
                config.model_config,
                train_seed=config.train_seed,
                formal=config.formal_use,
            )
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
        sampler = state["provider_sampler_state"]
        if not isinstance(sampler, Mapping):
            raise V023TwoRouteOrchestratorError("provider sampler state is invalid")
        consumed = sampler.get("consumed_file_order")
        if not isinstance(consumed, list) or len(consumed) != cursor * len(SOURCE_ORDER):
            raise V023TwoRouteOrchestratorError(
                "provider consumed-file history length drifted"
            )
        for index, entry in enumerate(file_order):
            route = ROUTE_ORDER[index % len(ROUTE_ORDER)]
            paired = consumed[index * len(SOURCE_ORDER):(index + 1) * len(SOURCE_ORDER)]
            expected_files = [list(item) for item in entry["source_files"]]
            observed_files = []
            for source, record in zip(SOURCE_ORDER, paired, strict=True):
                if (
                    not isinstance(record, Mapping)
                    or record.get("update_cursor") != index
                    or record.get("route") != route
                    or record.get("source") != source
                    or not isinstance(record.get("file_id"), str)
                ):
                    raise V023TwoRouteOrchestratorError(
                        "provider consumed-file history drifted"
                    )
                observed_files.append([source, record["file_id"]])
            if observed_files != expected_files:
                raise V023TwoRouteOrchestratorError(
                    "orchestrator and provider file histories disagree"
                )
        arms = state["arms"]
        if not isinstance(arms, Mapping) or tuple(arms) != ARMS:
            raise V023TwoRouteOrchestratorError("arm states drifted")
        for arm in ARMS:
            if (
                arms[arm].get("algorithm") != TWO_ROUTE_ALGORITHM
                or arms[arm].get("route_update_counts") != counts
                or arms[arm].get("train_seed") != self.config.train_seed
                or arms[arm].get("config") != asdict(self.config.model_config)
            ):
                raise V023TwoRouteOrchestratorError("non-two-route arm checkpoint rejected")
            if self._trainers[arm].load_checkpoint_state(arms[arm]) != cursor:
                raise V023TwoRouteOrchestratorError("arm update cursor drifted")
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
    "authenticate_factory_v3_provider_identity", "validate_two_route_provider_identity",
]
