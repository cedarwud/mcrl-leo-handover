#!/usr/bin/env python3
"""Fail-closed V0.23 one-world, five-arm *plumbing* for future TRAIN work.

This is deliberately separate from the gate-admitted real-five-arm adapter.
It has no admission object, no result writer, no learner update path, and no
TEST path.  Its sole runtime purpose, once explicit current learner checkpoints
and a TLE root exist, is to prove that five fixed current policies can traverse
one keyed TRAIN world through five fresh ``TrainerEnvironment`` instances.

The old e2e vertical slice is intentionally not imported: it was a
domain-separated initial-network fixture whose Q1/Q2 background route is not a
current learned-policy loader.  Likewise, this module never calls a legacy
background loader.  Every accepted checkpoint must already be a complete
current ``EEAxisLCSRSThreeRoute`` checkpoint containing Q1, Q2, and structured
Q3.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHYSICAL_PATH = REPO / ".scratch/multi-catfish-v023-physical/v023_physical_episode_runner.py"
C3_PROVIDER_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-current-c3view-provider/current_c3view_provider.py"
)

ARMS: tuple[str, ...] = (
    "ALL_NEUTRAL_CONTROL",
    "FULL",
    "DROP_C1",
    "DROP_C2",
    "DROP_C3",
)
ROUTES: tuple[str, ...] = ("C1", "C2", "C3")
SOURCE_MAPPING: Mapping[str, Mapping[str, str]] = {
    "ALL_NEUTRAL_CONTROL": {"C1": "neutral", "C2": "neutral", "C3": "neutral"},
    "FULL": {"C1": "informed", "C2": "informed", "C3": "informed"},
    "DROP_C1": {"C1": "neutral", "C2": "informed", "C3": "informed"},
    "DROP_C2": {"C1": "informed", "C2": "neutral", "C3": "informed"},
    "DROP_C3": {"C1": "informed", "C2": "informed", "C3": "neutral"},
}

SCHEMA = "multi-catfish-mcrl-v023-real-one-world-plumbing-v2"
PLUMBING_BINDING_SCHEMA = f"{SCHEMA}-policy-binding"
PLUMBING_RECEIPT_SCHEMA = f"{SCHEMA}-receipt"
PLUMBING_STATUS = "PLUMBING_ONLY_FIXED_POLICY_TRAIN_NO_GATE_NO_EFFICACY"
PLUMBING_DOMAIN = "MCRL_V023_REAL_ONE_WORLD_PLUMBING_POLICY_V2"
TRAIN_FIELD_COMPONENT = "MCRL_V023_REAL_ONE_WORLD_PLUMBING_TRAIN_V1"
TRAIN_SPLIT = "TRAIN"
USERS = 100
STEPS = 10


class V023RealOneWorldPlumbingError(RuntimeError):
    """The current five-policy plumbing boundary was underspecified or crossed."""


def _load_module(name: str, path: Path) -> Any:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023RealOneWorldPlumbingError(f"required sibling source is absent: {source}")
    loaded = sys.modules.get(name)
    if loaded is not None:
        if Path(str(getattr(loaded, "__file__", ""))).resolve() != source.resolve():
            raise V023RealOneWorldPlumbingError(f"{name} was already loaded from another path")
        return loaded
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise V023RealOneWorldPlumbingError(f"cannot import sibling source: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_physical = _load_module("v023_real_one_world_physical_semantics", PHYSICAL_PATH)


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V023RealOneWorldPlumbingError("value is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V023RealOneWorldPlumbingError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str, zero_allowed: bool = False) -> int:
    minimum = 0 if zero_allowed else 1
    if type(value) is not int or value < minimum:
        raise V023RealOneWorldPlumbingError(f"{field} must be an exact integer >= {minimum}")
    return value


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V023RealOneWorldPlumbingError(f"checkpoint is not a regular file: {source}")
    digest = hashlib.sha256()
    try:
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise V023RealOneWorldPlumbingError(f"cannot read checkpoint: {source}") from error
    return digest.hexdigest()


def _source_mapping_for(arm: str) -> dict[str, str]:
    if arm not in ARMS:
        raise V023RealOneWorldPlumbingError(f"unknown five-arm label: {arm!r}")
    return dict(SOURCE_MAPPING[arm])


def _verify_source_mapping(arm: str, source_mapping: Mapping[str, str]) -> None:
    if not isinstance(source_mapping, Mapping) or dict(source_mapping) != _source_mapping_for(arm):
        raise V023RealOneWorldPlumbingError(f"{arm} source mapping is not the frozen five-arm mapping")


def _parameter_sha256(model: Any) -> str:
    digest = hashlib.sha256()
    digest.update(b"mcrl-v023-real-one-world-plumbing-parameter-state-v1")
    try:
        state = model.state_dict()
        items = sorted(state.items())
    except Exception as error:
        raise V023RealOneWorldPlumbingError("current model has no readable state") from error
    for name, tensor in items:
        try:
            array = tensor.detach().cpu().contiguous().numpy()
        except Exception as error:
            raise V023RealOneWorldPlumbingError("current model tensor is unreadable") from error
        digest.update(name.encode("utf-8"))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(struct.pack(">I", array.ndim))
        for extent in array.shape:
            digest.update(struct.pack(">Q", int(extent)))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _three_route_types() -> tuple[type[Any], type[Any], type[Any], type[Any], type[Any]]:
    try:
        from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
        from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3HeadConfig, LCSRSC3QNetwork
        from mcrl.algorithms.ee_axis_lcsrs_three_route import (
            EEAxisLCSRSThreeRoute,
            LCSRS_THREE_ROUTE_ALGORITHM,
            LCSRSThreeRouteConfig,
        )
    except ImportError as error:  # pragma: no cover - project dependency failure
        raise V023RealOneWorldPlumbingError("current V0.23 three-route classes are unavailable") from error
    del LCSRS_THREE_ROUTE_ALGORITHM
    return (
        EEAxisLCSRSThreeRoute,
        LCSRSThreeRouteConfig,
        EEAxisActionSharedConfig,
        LCSRSC3HeadConfig,
        LCSRSC3QNetwork,
    )


def _checkpoint_algorithm() -> str:
    try:
        from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRS_THREE_ROUTE_ALGORITHM
    except ImportError as error:  # pragma: no cover - project dependency failure
        raise V023RealOneWorldPlumbingError("current V0.23 checkpoint class is unavailable") from error
    return LCSRS_THREE_ROUTE_ALGORITHM


def _config_from_checkpoint_state(state: Mapping[str, Any]) -> Any:
    _model_type, config_type, q12_type, q3_type, _q3_network_type = _three_route_types()
    raw = state.get("config")
    if not isinstance(raw, Mapping):
        raise V023RealOneWorldPlumbingError("current checkpoint has no three-route config")
    q12_raw = raw.get("q12")
    q3_raw = raw.get("q3")
    if not isinstance(q12_raw, Mapping) or not isinstance(q3_raw, Mapping):
        raise V023RealOneWorldPlumbingError("current checkpoint Q1/Q2/Q3 config is malformed")
    q12_values = dict(q12_raw)
    q3_values = dict(q3_raw)
    for values, fields in ((q12_values, ("hidden_layers", "loss_weights")), (q3_values, ("hidden_layers",))):
        for field in fields:
            if isinstance(values.get(field), list):
                values[field] = tuple(values[field])
    try:
        config_values = dict(raw)
        config_values["q12"] = q12_type(**q12_values)
        config_values["q3"] = q3_type(**q3_values)
        return config_type(**config_values)
    except (TypeError, ValueError) as error:
        raise V023RealOneWorldPlumbingError("current checkpoint configuration is incompatible") from error


def load_current_model_checkpoint_state(state: Mapping[str, Any]) -> tuple[Any, int]:
    """Materialise one complete learned V0.23 model from an in-memory state.

    It rejects every non-three-route algorithm before constructing a model.
    In particular, a legacy D40-shaped state cannot be used as a Q1/Q2
    background here: this plumbing seam accepts no partial-load route.
    """

    if not isinstance(state, Mapping):
        raise V023RealOneWorldPlumbingError("policy checkpoint root must be a mapping")
    if state.get("algorithm") != _checkpoint_algorithm():
        raise V023RealOneWorldPlumbingError(
            "D40 or other non-current checkpoint rejected: a complete V0.23 three-route checkpoint is required"
        )
    update_count = _positive_int(state.get("update_count"), field="checkpoint.update_count")
    train_seed = state.get("train_seed")
    _positive_int(train_seed, field="checkpoint.train_seed", zero_allowed=True)
    model_type, _config_type, _q12_type, _q3_type, _q3_network_type = _three_route_types()
    model = model_type(_config_from_checkpoint_state(state), train_seed=train_seed, device="cpu")
    try:
        restored_count = model.load_checkpoint_state(state)
    except Exception as error:
        raise V023RealOneWorldPlumbingError("current three-route checkpoint failed verification") from error
    if restored_count != update_count:
        raise V023RealOneWorldPlumbingError("current checkpoint update count drifted during restore")
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    return model, update_count


def load_current_five_arm_models(checkpoint_paths: Mapping[str, str | Path]) -> dict[str, tuple[Any, str, int]]:
    """Load exactly five explicit learned checkpoints, never a partial background.

    This function performs no environment construction and no physical work.
    File paths containing a D40 identity are rejected before deserialisation;
    the deserialised root must then pass the complete current checkpoint check.
    """

    if tuple(checkpoint_paths) != ARMS or set(checkpoint_paths) != set(ARMS):
        raise V023RealOneWorldPlumbingError("five checkpoints must use the exact ALL_NEUTRAL_CONTROL/FULL/DROP_C1/DROP_C2/DROP_C3 order")
    try:
        import torch
    except ImportError as error:  # pragma: no cover - project dependency failure
        raise V023RealOneWorldPlumbingError("torch is required to read current checkpoints") from error
    loaded: dict[str, tuple[Any, str, int]] = {}
    for arm in ARMS:
        path = Path(checkpoint_paths[arm])
        if "d40" in path.name.lower():
            raise V023RealOneWorldPlumbingError("D40 checkpoint path rejected before any checkpoint load")
        digest = file_sha256(path)
        try:
            state = torch.load(path, map_location="cpu", weights_only=False)
        except Exception as error:
            raise V023RealOneWorldPlumbingError(f"cannot deserialize current checkpoint for {arm}") from error
        model, update_count = load_current_model_checkpoint_state(state)
        loaded[arm] = (model, digest, update_count)
    _assert_independent_models({arm: model for arm, (model, _digest, _count) in loaded.items()})
    return loaded


@dataclass(frozen=True, slots=True)
class PlumbingPolicyBinding:
    """Domain-separated, non-admission identity for one learned plumbing policy.

    It is intentionally not an evaluation-binding type.  Its digest says only
    that a complete fixed checkpoint was routed into this plumbing seam.
    """

    arm: str
    checkpoint_sha256: str
    update_count: int
    source_mapping: Mapping[str, str]
    model_algorithm: str
    fixed_policy: bool = True
    learner_update: bool = False
    episode_training: bool = False
    test_split_opened: bool = False
    head_drop: bool = False
    schema: str = PLUMBING_BINDING_SCHEMA
    domain: str = PLUMBING_DOMAIN
    binding_sha256: str = ""

    def __post_init__(self) -> None:
        if self.arm not in ARMS:
            raise V023RealOneWorldPlumbingError("plumbing binding has an unknown arm")
        _sha256(self.checkpoint_sha256, field=f"{self.arm}.checkpoint_sha256")
        _positive_int(self.update_count, field=f"{self.arm}.update_count")
        _verify_source_mapping(self.arm, self.source_mapping)
        if self.model_algorithm != _checkpoint_algorithm():
            raise V023RealOneWorldPlumbingError("plumbing binding is not a current three-route checkpoint")
        for field in ("fixed_policy", "learner_update", "episode_training", "test_split_opened", "head_drop"):
            if type(getattr(self, field)) is not bool:
                raise V023RealOneWorldPlumbingError(f"{self.arm}.{field} must be an exact bool")
        if not self.fixed_policy or self.learner_update or self.episode_training or self.test_split_opened or self.head_drop:
            raise V023RealOneWorldPlumbingError("plumbing policies must be fixed, complete, TRAIN-only, and head-preserving")
        if self.schema != PLUMBING_BINDING_SCHEMA or self.domain != PLUMBING_DOMAIN:
            raise V023RealOneWorldPlumbingError("plumbing binding schema/domain drifted")
        expected = canonical_sha256(self._payload_without_digest())
        if self.binding_sha256 not in ("", expected):
            raise V023RealOneWorldPlumbingError("plumbing binding digest drifted")
        object.__setattr__(self, "source_mapping", _source_mapping_for(self.arm))
        object.__setattr__(self, "binding_sha256", expected)

    def _payload_without_digest(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "domain": self.domain,
            "arm": self.arm,
            "checkpoint_sha256": self.checkpoint_sha256,
            "update_count": self.update_count,
            "source_mapping": _source_mapping_for(self.arm),
            "model_algorithm": self.model_algorithm,
            "fixed_policy": self.fixed_policy,
            "learner_update": self.learner_update,
            "episode_training": self.episode_training,
            "test_split_opened": self.test_split_opened,
            "head_drop": self.head_drop,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload_without_digest(), "binding_sha256": self.binding_sha256}


class CurrentStructuredC3ViewFactory:
    """Build a native, current LC-SRS C3View from the current provider seam."""

    def __init__(self, opening_feasibility_provider: Callable[[Any, Any], Any]) -> None:
        if not callable(opening_feasibility_provider):
            raise V023RealOneWorldPlumbingError("current structured C3View provider is required")
        self._opening_feasibility_provider = opening_feasibility_provider

    def __call__(
        self,
        *,
        step_environment: Any,
        observation: Any,
        native_state: Any,
        q12_snapshot: Any,
        world: "TrainWorldBinding",
    ) -> Any:
        try:
            from mcrl.runtime.ee_axis_lcsrs_c3_encoder import capture_lcsrs_c3_predecision
            from mcrl.runtime.ee_axis_lcsrs_c3_state import C3View
        except ImportError as error:  # pragma: no cover - project dependency failure
            raise V023RealOneWorldPlumbingError("current structured C3View classes are unavailable") from error
        try:
            masks = np.asarray(native_state.action_masks, dtype=np.bool_)
            if masks.shape != q12_snapshot.q12.shape or np.any(~np.any(masks, axis=1)):
                raise ValueError("native masks do not match current Q1/Q2 scores")
            references = np.argmax(np.where(masks, q12_snapshot.q12, -np.inf), axis=1).astype(np.int64)
            opening = self._opening_feasibility_provider(step_environment, observation)
            capture = capture_lcsrs_c3_predecision(
                step_environment,
                observation,
                world_id=world.world_index,
                anchor_id=f"{world.world_id}:t{getattr(observation, 'step_index', 'unknown')}",
                detached_q12=q12_snapshot,
                reference_actions=references,
                opening_feasibility_surface=opening,
            )
            view = capture.view
        except Exception as error:
            raise V023RealOneWorldPlumbingError("current structured C3View capture failed") from error
        if not isinstance(view, C3View):
            raise V023RealOneWorldPlumbingError("current provider did not produce a structured C3View")
        view.verify()
        return view


def load_current_structured_c3_view_factory() -> CurrentStructuredC3ViewFactory:
    """Use the dedicated current predecision provider, never an e2e fixture."""

    provider_module = _load_module("v023_real_one_world_current_c3_provider", C3_PROVIDER_PATH)
    try:
        provider = provider_module.CurrentOpeningFeasibilityProvider()
    except Exception as error:
        raise V023RealOneWorldPlumbingError("current structured C3View provider cannot be initialised") from error
    return CurrentStructuredC3ViewFactory(provider)


class CurrentV023FixedPolicy:
    """A fixed current three-route policy with no head-removal alternative."""

    def __init__(
        self,
        *,
        binding: PlumbingPolicyBinding,
        model: Any,
        c3_view_factory: Callable[..., Any],
    ) -> None:
        model_type, _config_type, _q12_type, _q3_type, q3_network_type = _three_route_types()
        if not isinstance(binding, PlumbingPolicyBinding):
            raise V023RealOneWorldPlumbingError("policy needs a domain-separated plumbing binding")
        if not isinstance(model, model_type) or len(model.q_networks) != 3 or not isinstance(model.q3, q3_network_type):
            raise V023RealOneWorldPlumbingError("policy must wrap a complete current Q1/Q2/structured-Q3 model")
        if not callable(c3_view_factory):
            raise V023RealOneWorldPlumbingError("policy needs a current structured C3View factory")
        self.binding = binding
        self.arm = binding.arm
        self.model = model
        self._c3_view_factory = c3_view_factory
        self.model.eval()
        for parameter in self.model.parameters():
            parameter.requires_grad_(False)
        self.select_call_count = 0

    @property
    def checkpoint_sha256(self) -> str:
        return self.binding.checkpoint_sha256

    def parameter_sha256(self) -> str:
        return _parameter_sha256(self.model)

    def select_actions(
        self,
        *,
        native_state: Any,
        step_environment: Any,
        observation: Any,
        native_observation_event_digest: str,
        world: "TrainWorldBinding",
    ) -> np.ndarray:
        """Evaluate Q1/Q2 once, build current C3View, then do one masked sum."""

        try:
            state_for_q12 = native_state
            if not hasattr(native_state, "verify") and hasattr(native_state, "state_matrix"):
                state_for_q12 = native_state.state_matrix
            snapshot = self.model.capture_q12(
                state_for_q12,
                native_observation_event_digest=native_observation_event_digest,
            )
            view = self._c3_view_factory(
                step_environment=step_environment,
                observation=observation,
                native_state=native_state,
                q12_snapshot=snapshot,
                world=world,
            )
            from mcrl.runtime.ee_axis_lcsrs_c3_state import C3View

            if not isinstance(view, C3View):
                raise TypeError("factory did not return C3View")
            view.verify()
            actions = self.model.select_greedy_actions(snapshot, view)
        except Exception as error:
            raise V023RealOneWorldPlumbingError(
                f"current fixed policy action selection failed for {self.arm}"
            ) from error
        self.select_call_count += 1
        return np.asarray(actions, dtype=np.int64)


def build_current_fixed_policies(
    checkpoint_paths: Mapping[str, str | Path],
    *,
    c3_view_factory: Callable[..., Any],
) -> dict[str, CurrentV023FixedPolicy]:
    """Bind five explicit complete checkpoint files into fixed plumbing policies."""

    if not callable(c3_view_factory):
        raise V023RealOneWorldPlumbingError("current structured C3View provider is missing")
    models = load_current_five_arm_models(checkpoint_paths)
    policies: dict[str, CurrentV023FixedPolicy] = {}
    for arm in ARMS:
        model, checkpoint_sha256, update_count = models[arm]
        binding = PlumbingPolicyBinding(
            arm=arm,
            checkpoint_sha256=checkpoint_sha256,
            update_count=update_count,
            source_mapping=_source_mapping_for(arm),
            model_algorithm=_checkpoint_algorithm(),
        )
        policies[arm] = CurrentV023FixedPolicy(
            binding=binding, model=model, c3_view_factory=c3_view_factory
        )
    _assert_independent_models({arm: policies[arm].model for arm in ARMS})
    return policies


def _assert_independent_models(models: Mapping[str, Any]) -> None:
    if tuple(models) != ARMS or set(models) != set(ARMS):
        raise V023RealOneWorldPlumbingError("current models must cover the exact five-arm order")
    model_ids = [id(models[arm]) for arm in ARMS]
    if len(set(model_ids)) != len(ARMS):
        raise V023RealOneWorldPlumbingError("five arms alias one current model instance")
    seen_parameters: set[int] = set()
    for arm in ARMS:
        try:
            parameter_ids = {id(parameter) for parameter in models[arm].parameters()}
        except Exception as error:
            raise V023RealOneWorldPlumbingError(f"{arm} model has no parameter surface") from error
        if not parameter_ids or parameter_ids & seen_parameters:
            raise V023RealOneWorldPlumbingError("five arms share model parameter storage")
        seen_parameters.update(parameter_ids)


@dataclass(frozen=True, slots=True)
class TrainWorldBinding:
    """One keyed TLE world identity shared by all five fresh environments."""

    world_index: int
    world_id: str
    world_seed: int
    field_root_digest: str
    split: str = TRAIN_SPLIT
    field_component: str = TRAIN_FIELD_COMPONENT

    def verify(self) -> None:
        _positive_int(self.world_index, field="world_index")
        if not isinstance(self.world_id, str) or not self.world_id.strip() or "TEST" in self.world_id.upper():
            raise V023RealOneWorldPlumbingError("world_id must be nonempty and TRAIN-only")
        _positive_int(self.world_seed, field="world_seed", zero_allowed=True)
        if self.split != TRAIN_SPLIT or "TEST" in self.split.upper():
            raise V023RealOneWorldPlumbingError("one-world plumbing permits only TRAIN")
        if self.field_component != TRAIN_FIELD_COMPONENT:
            raise V023RealOneWorldPlumbingError("keyed world field component drifted")
        expected = _physical.KeyedFadingField.from_components(self.field_component, self.world_seed).root_digest
        if _sha256(self.field_root_digest, field="field_root_digest") != expected:
            raise V023RealOneWorldPlumbingError("keyed TRAIN world root drifted")


def make_train_world(*, world_index: int, world_id: str, world_seed: int) -> TrainWorldBinding:
    _positive_int(world_index, field="world_index")
    _positive_int(world_seed, field="world_seed", zero_allowed=True)
    field = _physical.KeyedFadingField.from_components(TRAIN_FIELD_COMPONENT, world_seed)
    world = TrainWorldBinding(
        world_index=world_index,
        world_id=world_id,
        world_seed=world_seed,
        field_root_digest=field.root_digest,
    )
    world.verify()
    return world


def _observation_digest(native: Any) -> str:
    try:
        states = np.asarray(native.state_matrix, dtype=np.float32)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
    except (AttributeError, TypeError, ValueError) as error:
        raise V023RealOneWorldPlumbingError("native state lacks current state/mask arrays") from error
    if states.shape != (USERS, 228) or masks.shape != (USERS, 28):
        raise V023RealOneWorldPlumbingError("native current state/mask shape drifted")
    return hashlib.sha256(
        _canonical_bytes({"state": states.tobytes().hex(), "mask": masks.tobytes().hex()})
    ).hexdigest()


def _validate_actions(actions: Any, masks: Any) -> np.ndarray:
    result = np.asarray(actions, dtype=np.int64)
    legal = np.asarray(masks, dtype=np.bool_)
    if result.shape != (USERS,) or legal.shape != (USERS, 28):
        raise V023RealOneWorldPlumbingError("policy did not return one action per current user")
    if np.any(result < 0) or np.any(result >= legal.shape[1]) or not np.all(legal[np.arange(USERS), result]):
        raise V023RealOneWorldPlumbingError("policy chose an action outside the native current mask")
    return result


@dataclass(frozen=True, slots=True)
class PlumbingEpisodeReceipt:
    arm: str
    world_index: int
    world_id: str
    world_seed: int
    field_root_digest: str
    checkpoint_sha256: str
    policy_binding_sha256: str
    initial_world_sha256: str
    action_trace_sha256: str
    total_bits: float
    total_energy_j: float
    ratio_of_sums_ee_bits_per_j: float
    served_user_steps: int
    service_opportunities: int
    fixed_policy: bool = True
    learner_update: bool = False
    episode_training: bool = False
    test_split_opened: bool = False
    head_drop: bool = False
    status: str = PLUMBING_STATUS
    schema: str = PLUMBING_RECEIPT_SCHEMA

    def verify(self) -> None:
        if self.arm not in ARMS or self.schema != PLUMBING_RECEIPT_SCHEMA or self.status != PLUMBING_STATUS:
            raise V023RealOneWorldPlumbingError("plumbing receipt identity drifted")
        for field in (
            "field_root_digest",
            "checkpoint_sha256",
            "policy_binding_sha256",
            "initial_world_sha256",
            "action_trace_sha256",
        ):
            _sha256(getattr(self, field), field=field)
        if not all(math.isfinite(value) and value > 0.0 for value in (self.total_bits, self.total_energy_j)):
            raise V023RealOneWorldPlumbingError("plumbing receipt needs positive finite physical totals")
        if self.ratio_of_sums_ee_bits_per_j != self.total_bits / self.total_energy_j:
            raise V023RealOneWorldPlumbingError("plumbing receipt EE must remain a ratio of sums")
        if self.service_opportunities != USERS * STEPS or not 0 <= self.served_user_steps <= self.service_opportunities:
            raise V023RealOneWorldPlumbingError("plumbing receipt service accounting drifted")
        if not self.fixed_policy or self.learner_update or self.episode_training or self.test_split_opened or self.head_drop:
            raise V023RealOneWorldPlumbingError("plumbing receipt crossed a closed boundary")

    def to_dict(self) -> dict[str, object]:
        self.verify()
        return asdict(self)


class V023RealOneWorldPlumbingAdapter:
    """Physical run semantics without gate admission or artifact persistence."""

    def __init__(
        self,
        *,
        policies: Mapping[str, CurrentV023FixedPolicy],
        tle_root: Path,
        execute: bool,
        environment_factory: Callable[[Any, int], Any],
        rng_factory: Callable[[int], Sequence[np.random.Generator]],
        encode_native_state: Callable[[Any, Any], Any],
        trainer_environment_type: type[Any] | None = None,
    ) -> None:
        if tuple(policies) != ARMS or set(policies) != set(ARMS):
            raise V023RealOneWorldPlumbingError("adapter needs policies in the exact five-arm order")
        root = Path(tle_root)
        if root.is_symlink() or not root.is_dir():
            raise V023RealOneWorldPlumbingError("adapter needs an explicit regular TLE root")
        if type(execute) is not bool or not execute:
            raise V023RealOneWorldPlumbingError("physical adapter requires an explicit execute flag")
        if not callable(environment_factory) or not callable(rng_factory) or not callable(encode_native_state):
            raise V023RealOneWorldPlumbingError("adapter needs explicit physical callbacks")
        if any(not isinstance(policies[arm], CurrentV023FixedPolicy) or policies[arm].arm != arm for arm in ARMS):
            raise V023RealOneWorldPlumbingError("adapter needs one current fixed policy per exact arm")
        _assert_independent_models({arm: policies[arm].model for arm in ARMS})
        self.policies = dict(policies)
        self.tle_root = root
        self.environment_factory = environment_factory
        self.rng_factory = rng_factory
        self.encode_native_state = encode_native_state
        self.trainer_environment_type = trainer_environment_type or _physical.TrainerEnvironment
        self.created_environments: list[Any] = []

    def _environment(self, shared_field: Any) -> tuple[Any, Any]:
        try:
            environment = self.environment_factory(self.tle_root, USERS)
        except Exception as error:
            raise V023RealOneWorldPlumbingError("fresh TrainerEnvironment factory failed") from error
        if not isinstance(environment, self.trainer_environment_type):
            raise V023RealOneWorldPlumbingError("physical factory must return TrainerEnvironment")
        if any(environment is previous for previous in self.created_environments):
            raise V023RealOneWorldPlumbingError("each arm needs a fresh TrainerEnvironment")
        step_environment = getattr(environment, "environment", None)
        if step_environment is None or not hasattr(step_environment, "_fading_field"):
            raise V023RealOneWorldPlumbingError("TrainerEnvironment lacks keyed fading boundary")
        config = getattr(environment, "config", None)
        if config is None or getattr(config, "num_users", None) != USERS or getattr(config, "steps_per_episode", None) != STEPS:
            raise V023RealOneWorldPlumbingError("TrainerEnvironment dimensions are not current physical dimensions")
        step_environment._fading_field = shared_field
        self.created_environments.append(environment)
        return environment, step_environment

    def run_one_world(self, *, world: TrainWorldBinding) -> tuple[PlumbingEpisodeReceipt, ...]:
        """Run five fixed policies on one shared keyed TRAIN world; write nothing."""

        world.verify()
        self.created_environments = []
        shared_field = _physical.KeyedFadingField.from_components(TRAIN_FIELD_COMPONENT, world.world_seed)
        if shared_field.root_digest != world.field_root_digest:
            raise V023RealOneWorldPlumbingError("keyed world root does not match the requested TRAIN world")
        before = {arm: self.policies[arm].parameter_sha256() for arm in ARMS}
        receipts: list[PlumbingEpisodeReceipt] = []
        for arm in ARMS:
            policy = self.policies[arm]
            environment, step_environment = self._environment(shared_field)
            rngs = tuple(self.rng_factory(world.world_seed))
            if len(rngs) < 2 or any(not isinstance(rng, np.random.Generator) for rng in rngs[:2]):
                raise V023RealOneWorldPlumbingError("rng factory needs environment and mobility NumPy generators")
            try:
                _states, _masks, observation = environment.reset(rngs[0], rngs[1])
                interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
            except Exception as error:
                raise V023RealOneWorldPlumbingError("canonical physical reset/interval failed") from error
            if not math.isfinite(interval_s) or interval_s <= 0.0:
                raise V023RealOneWorldPlumbingError("physical decision interval is invalid")
            initial_digest: str | None = None
            action_digest = hashlib.sha256()
            total_bits = total_energy = 0.0
            served_user_steps = 0
            for step in range(STEPS):
                native = self.encode_native_state(step_environment, observation)
                observation_digest = _observation_digest(native)
                if initial_digest is None:
                    initial_digest = observation_digest
                actions = _validate_actions(
                    policy.select_actions(
                        native_state=native,
                        step_environment=step_environment,
                        observation=observation,
                        native_observation_event_digest=observation_digest,
                        world=world,
                    ),
                    native.action_masks,
                )
                action_digest.update(actions.tobytes(order="C"))
                try:
                    environment.step(actions, rngs[0])
                    outcome = environment.last_outcome
                    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
                    power = float(outcome.system_power_w)
                    served = int(outcome.resolution.served_count)
                except Exception as error:
                    raise V023RealOneWorldPlumbingError("physical step lacks the required realised outcome") from error
                if rates.shape != (USERS,) or not np.all(np.isfinite(rates)) or np.any(rates < 0.0) or not math.isfinite(power) or power <= 0.0 or not 0 <= served <= USERS:
                    raise V023RealOneWorldPlumbingError("physical outcome is malformed")
                total_bits += interval_s * math.fsum(float(rate) for rate in rates)
                total_energy += interval_s * power
                served_user_steps += served
                done = bool(getattr(outcome, "done", False))
                if step < STEPS - 1:
                    if done:
                        raise V023RealOneWorldPlumbingError("physical episode ended before ten steps")
                    observation = outcome.observation
                elif not done:
                    raise V023RealOneWorldPlumbingError("physical episode did not end at ten steps")
            if initial_digest is None:
                raise V023RealOneWorldPlumbingError("physical episode had no initial world state")
            receipt = PlumbingEpisodeReceipt(
                arm=arm,
                world_index=world.world_index,
                world_id=world.world_id,
                world_seed=world.world_seed,
                field_root_digest=shared_field.root_digest,
                checkpoint_sha256=policy.checkpoint_sha256,
                policy_binding_sha256=policy.binding.binding_sha256,
                initial_world_sha256=initial_digest,
                action_trace_sha256=action_digest.hexdigest(),
                total_bits=total_bits,
                total_energy_j=total_energy,
                ratio_of_sums_ee_bits_per_j=total_bits / total_energy,
                served_user_steps=served_user_steps,
                service_opportunities=USERS * STEPS,
            )
            receipt.verify()
            receipts.append(receipt)
        if any(self.policies[arm].parameter_sha256() != before[arm] for arm in ARMS):
            raise V023RealOneWorldPlumbingError("fixed policy parameters changed during physical plumbing")
        if tuple(row.arm for row in receipts) != ARMS or len(self.created_environments) != len(ARMS):
            raise V023RealOneWorldPlumbingError("one-world plumbing lost exact five-arm coverage")
        if len({id(item) for item in self.created_environments}) != len(ARMS):
            raise V023RealOneWorldPlumbingError("one-world plumbing reused an environment across arms")
        if len({row.field_root_digest for row in receipts}) != 1 or len({(row.world_index, row.world_id, row.world_seed) for row in receipts}) != 1:
            raise V023RealOneWorldPlumbingError("five arms did not share exactly one keyed TRAIN world")
        return tuple(receipts)


@dataclass(frozen=True, slots=True)
class PreflightRequest:
    """CLI-level future inputs; preflight is read-only and never runs a world."""

    checkpoint_paths: Mapping[str, Path]
    tle_root: Path | None
    execute: bool = False
    split: str = TRAIN_SPLIT
    world_index: int | None = None
    world_id: str | None = None
    world_seed: int | None = None

    def missing_inputs(self) -> tuple[str, ...]:
        missing: list[str] = []
        if tuple(self.checkpoint_paths) != ARMS or set(self.checkpoint_paths) != set(ARMS):
            missing.append("five explicit checkpoints in ALL_NEUTRAL_CONTROL/FULL/DROP_C1/DROP_C2/DROP_C3 order")
        else:
            for arm in ARMS:
                path = Path(self.checkpoint_paths[arm])
                if not path.is_file() or path.is_symlink():
                    missing.append(f"checkpoint.{arm}")
        if self.tle_root is None or not self.tle_root.is_dir() or self.tle_root.is_symlink():
            missing.append("explicit TLE root")
        if self.world_index is None or self.world_id is None or self.world_seed is None:
            missing.append("explicit TRAIN world index/id/seed")
        return tuple(missing)

    def verify_for_execution(self) -> None:
        if self.split != TRAIN_SPLIT or "TEST" in self.split.upper():
            raise V023RealOneWorldPlumbingError("preflight accepts only TRAIN")
        if not self.execute:
            raise V023RealOneWorldPlumbingError("physical execution requires an explicit --execute flag")
        missing = self.missing_inputs()
        if missing:
            raise V023RealOneWorldPlumbingError("physical execution is missing: " + ", ".join(missing))
        assert self.world_index is not None and self.world_id is not None and self.world_seed is not None
        make_train_world(world_index=self.world_index, world_id=self.world_id, world_seed=self.world_seed)


def preflight_payload(request: PreflightRequest) -> dict[str, object]:
    """Report only launch readiness.  It never deserialises a model or opens TLE."""

    if request.split != TRAIN_SPLIT or "TEST" in request.split.upper():
        raise V023RealOneWorldPlumbingError("dry-run preflight accepts only TRAIN")
    missing = request.missing_inputs()
    return {
        "schema": f"{SCHEMA}-preflight",
        "status": "DRY_RUN_ONLY",
        "claim_ceiling": PLUMBING_STATUS,
        "split": TRAIN_SPLIT,
        "execute_requested": request.execute,
        "physical_work_executed": False,
        "ready_for_explicit_host_execution": bool(request.execute and not missing),
        "missing_real_inputs": list(missing),
        "scientific_decision": None,
    }


def parse_checkpoint_arguments(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise V023RealOneWorldPlumbingError("--checkpoint requires ARM=PATH")
        arm, raw_path = value.split("=", 1)
        if arm not in ARMS or not raw_path or arm in result:
            raise V023RealOneWorldPlumbingError("--checkpoint arm/path is malformed or duplicated")
        result[arm] = Path(raw_path)
    return result


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="V0.23 real one-world plumbing dry-run/preflight (no physical execution)")
    parser.add_argument("preflight", nargs="?", default="preflight")
    parser.add_argument("--checkpoint", action="append", default=[], metavar="ARM=PATH")
    parser.add_argument("--tle-root", type=Path)
    parser.add_argument("--world-index", type=int)
    parser.add_argument("--world-id")
    parser.add_argument("--world-seed", type=int)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight != "preflight":
        parser.error("only the dry-run preflight command is available")
    try:
        request = PreflightRequest(
            checkpoint_paths=parse_checkpoint_arguments(args.checkpoint),
            tle_root=args.tle_root,
            execute=bool(args.execute),
            world_index=args.world_index,
            world_id=args.world_id,
            world_seed=args.world_seed,
        )
        # Even with --execute this process has no host environment factory and
        # therefore remains a preflight.  A server host must call the adapter
        # explicitly after verify_for_execution succeeds.
        payload = preflight_payload(request)
    except V023RealOneWorldPlumbingError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - never launched by tests
    raise SystemExit(_main())


__all__ = [
    "ARMS",
    "PLUMBING_DOMAIN",
    "PLUMBING_STATUS",
    "ROUTES",
    "SOURCE_MAPPING",
    "TRAIN_FIELD_COMPONENT",
    "TRAIN_SPLIT",
    "CurrentStructuredC3ViewFactory",
    "CurrentV023FixedPolicy",
    "PlumbingEpisodeReceipt",
    "PlumbingPolicyBinding",
    "PreflightRequest",
    "TrainWorldBinding",
    "V023RealOneWorldPlumbingAdapter",
    "V023RealOneWorldPlumbingError",
    "build_current_fixed_policies",
    "canonical_sha256",
    "file_sha256",
    "load_current_five_arm_models",
    "load_current_model_checkpoint_state",
    "load_current_structured_c3_view_factory",
    "make_train_world",
    "parse_checkpoint_arguments",
    "preflight_payload",
]
