#!/usr/bin/env python3
"""Production seam for the admitted V0.23 real five-arm episode runner.

This module contains no TLE loading, training, or launch command.  Its factory
requires an already-admitted five-arm request and five loaded policy objects.
The concrete policy-object/artifact binding is intentionally typed rather than
guessed: callers must expose an arm plus the frozen checkpoint/source digests.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any, Protocol

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EPISODE_RUNNER = REPO / ".scratch/multi-catfish-v023-episode-screen/v023_real_five_arm_episode_runner.py"
RESULTS = REPO / ".scratch/multi-catfish-v023-five-arm-evaluation/v023_five_arm_eval_results.py"
PHYSICAL = REPO / ".scratch/multi-catfish-v023-physical/v023_physical_episode_runner.py"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load sibling module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_runner = _load("v023_real_five_arm_runner_adapter", EPISODE_RUNNER)
_results = _load("v023_five_arm_results_adapter", RESULTS)
_physical = _load("v023_physical_runner_adapter", PHYSICAL)

ARMS = _runner.ARMS
REAL_ADAPTER_IDENTITY = _runner.REAL_ADAPTER_IDENTITY


class RealFiveArmExecutionAdapterError(RuntimeError):
    """A real five-arm environment/policy binding failed closed."""


class LoadedFiveArmPolicy(Protocol):
    """Required loaded-policy binding; runtime must not infer this from bytes."""

    arm: str
    checkpoint_sha256: str
    source_arm_sha256: str
    policy_family: str
    head_drop: bool

    def select_actions(
        self,
        *,
        native_state: object,
        c3_view: object,
        native_observation_event_digest: str,
    ) -> Sequence[int] | np.ndarray: ...


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RealFiveArmExecutionAdapterError(f"{field} is not a lowercase SHA-256")
    return value


def _canonical(value: object) -> bytes:
    import json
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _observation_digest(native: Any) -> str:
    try:
        states = np.asarray(native.state_matrix, dtype=np.float32)
        masks = np.asarray(native.action_masks, dtype=np.bool_)
    except (AttributeError, TypeError, ValueError) as error:
        raise RealFiveArmExecutionAdapterError("native state lacks state/mask arrays") from error
    if states.ndim != 2 or masks.shape != (states.shape[0], 28):
        raise RealFiveArmExecutionAdapterError("native state shape is not user-by-28")
    return hashlib.sha256(_canonical({"state": states.tobytes().hex(), "mask": masks.tobytes().hex()})).hexdigest()


class RealFiveArmExecutionAdapter:
    """Run one explicit fixed policy on one keyed physical world.

    Every arm receives a fresh real ``TrainerEnvironment`` initialized with the
    same frozen TLE archive and keyed field for its declared world.  The only
    arm-specific input is its explicitly loaded policy object.
    """

    identity = REAL_ADAPTER_IDENTITY
    is_test_fixture = False

    def __init__(
        self,
        *,
        admission: Any,
        policies: Mapping[str, LoadedFiveArmPolicy],
        tle_archive: Any,
        environment_factory: Callable[[Any, int], Any],
        rng_factory: Callable[[int], Sequence[np.random.Generator]],
        encode_native_state: Callable[[Any, Any], Any],
        c3_view_factory: Callable[[Any, Any, str], Any],
        field_factory: Callable[[str, int], Any] | None = None,
        trainer_environment_type: type[Any] | None = None,
        users: int = 100,
        steps: int = 10,
    ) -> None:
        if tle_archive is None:
            raise RealFiveArmExecutionAdapterError("frozen TLE archive is required")
        if users != 100 or steps != 10:
            raise RealFiveArmExecutionAdapterError("real five-arm episodes are fixed at 100 users x 10 steps")
        for callback, label in ((environment_factory, "environment_factory"), (rng_factory, "rng_factory"), (encode_native_state, "encode_native_state"), (c3_view_factory, "c3_view_factory")):
            if not callable(callback):
                raise RealFiveArmExecutionAdapterError(f"{label} is required")
        binding = getattr(getattr(admission, "request", None), "binding", None)
        if binding is None or not callable(getattr(binding, "verify", None)):
            raise RealFiveArmExecutionAdapterError("current five-arm gate admission/binding is absent")
        # Reverify at factory time; an unsealed or stale gate cannot be used.
        try:
            self.binding_sha256 = str(binding.verify())
        except Exception as error:
            raise RealFiveArmExecutionAdapterError("current five-arm binding is not admitted") from error
        bound_policies = {item.arm: item for item in getattr(binding, "policies", ())}
        if tuple(getattr(item, "arm", None) for item in getattr(binding, "policies", ())) != ARMS:
            raise RealFiveArmExecutionAdapterError("five-arm binding policy order is absent or stale")
        if set(policies) != set(ARMS):
            raise RealFiveArmExecutionAdapterError("loaded policies must cover exactly the current five arms")
        for arm in ARMS:
            policy = policies[arm]
            if getattr(policy, "arm", None) != arm or not callable(getattr(policy, "select_actions", None)):
                raise RealFiveArmExecutionAdapterError(f"policy.{arm} lacks explicit current-policy routing")
            # This is the intentionally required interface that current raw
            # artifact bindings do not by themselves provide.
            if _digest(getattr(policy, "checkpoint_sha256", None), field=f"policy.{arm}.checkpoint_sha256") != bound_policies[arm].checkpoint_sha256:
                raise RealFiveArmExecutionAdapterError(f"policy.{arm} checkpoint does not bind its loaded object")
            if _digest(getattr(policy, "source_arm_sha256", None), field=f"policy.{arm}.source_arm_sha256") != bound_policies[arm].source_arm_sha256:
                raise RealFiveArmExecutionAdapterError(f"policy.{arm} source arm does not bind its loaded object")
            if getattr(policy, "policy_family", None) != bound_policies[arm].policy_family:
                raise RealFiveArmExecutionAdapterError(f"policy.{arm} family does not bind its loaded object")
            if getattr(policy, "head_drop", None) is not False:
                raise RealFiveArmExecutionAdapterError(f"policy.{arm} uses a forbidden head-drop shortcut")
        self.admission = admission
        self.policies = dict(policies)
        self.tle_archive = tle_archive
        self.environment_factory = environment_factory
        self.rng_factory = rng_factory
        self.encode_native_state = encode_native_state
        self.c3_view_factory = c3_view_factory
        self.field_factory = field_factory or (lambda component, seed: _physical.KeyedFadingField.from_components(component, seed))
        self.trainer_environment_type = trainer_environment_type or _physical.TrainerEnvironment
        self.users = users
        self.steps = steps
        self._resume_by_arm: dict[str, Mapping[str, object]] = {}

    def resume_state_for(self, arm: str) -> Mapping[str, object] | None:
        if arm not in ARMS:
            raise RealFiveArmExecutionAdapterError(f"unknown five-arm policy: {arm}")
        return self._resume_by_arm.get(arm)

    def restore_resume_states(self, states: Mapping[str, object]) -> None:
        if not isinstance(states, Mapping) or set(states) != set(ARMS):
            raise RealFiveArmExecutionAdapterError("resume requires exactly one state per five-arm policy")
        restored: dict[str, Mapping[str, object]] = {}
        for arm in ARMS:
            value = states[arm]
            if value is not None and not isinstance(value, Mapping):
                raise RealFiveArmExecutionAdapterError(f"resume state for {arm} is malformed")
            if isinstance(value, Mapping):
                if value.get("schema") != "multi-catfish-mcrl-v023-five-arm-real-resume-v1" or value.get("arm") != arm:
                    raise RealFiveArmExecutionAdapterError(f"resume state for {arm} has stale schema/arm")
                if value.get("policy_checkpoint_sha256") != self.policies[arm].checkpoint_sha256:
                    raise RealFiveArmExecutionAdapterError(f"resume state for {arm} policy digest drifted")
                restored[arm] = dict(value)
        self._resume_by_arm = restored

    def _field(self, world: Any) -> Any:
        try:
            field = self.field_factory(_physical.FIELD_COMPONENT, int(world.world_seed))
            expected = _physical.KeyedFadingField.from_components(_physical.FIELD_COMPONENT, int(world.world_seed))
        except Exception as error:
            raise RealFiveArmExecutionAdapterError("cannot construct the keyed common world") from error
        if not isinstance(field, _physical.KeyedFadingField) or field.root_digest != expected.root_digest or field.root_digest != world.field_root_digest:
            raise RealFiveArmExecutionAdapterError("matched keyed world binding drifted")
        return field

    def _environment(self, field: Any) -> Any:
        try:
            environment = self.environment_factory(self.tle_archive, self.users)
        except Exception as error:
            raise RealFiveArmExecutionAdapterError("TrainerEnvironment factory failed") from error
        if not isinstance(environment, self.trainer_environment_type):
            raise RealFiveArmExecutionAdapterError("environment_factory must return TrainerEnvironment")
        step_environment = getattr(environment, "environment", None)
        if step_environment is None or not hasattr(step_environment, "_fading_field"):
            raise RealFiveArmExecutionAdapterError("TrainerEnvironment lacks keyed-fading boundary")
        step_environment._fading_field = field
        config = getattr(environment, "config", None)
        if config is None or config.num_users != self.users or config.steps_per_episode != self.steps:
            raise RealFiveArmExecutionAdapterError("TrainerEnvironment dimensions drifted")
        return environment, step_environment

    def run_episode(self, *, arm: str, world: Any, policy: Any, resume_state: Mapping[str, object] | None) -> Any:
        if arm not in ARMS or policy is not self.policies.get(arm):
            raise RealFiveArmExecutionAdapterError("runner did not route the explicit arm policy")
        if getattr(world, "episode_index", None) is None:
            raise RealFiveArmExecutionAdapterError("world binding is absent")
        if resume_state is not None and resume_state is not self._resume_by_arm.get(arm):
            raise RealFiveArmExecutionAdapterError("runner supplied a non-deterministic resume state")
        field = self._field(world)
        environment, step_environment = self._environment(field)
        rngs = tuple(self.rng_factory(int(world.world_seed)))
        if len(rngs) < 2 or any(not isinstance(rng, np.random.Generator) for rng in rngs[:2]):
            raise RealFiveArmExecutionAdapterError("rng_factory must return environment/mobility NumPy generators")
        if resume_state is not None:
            loader = getattr(environment, "load_training_state_dict", None) or getattr(environment, "load_resume_state_dict", None)
            if not callable(loader) or not isinstance(resume_state.get("environment_training_state"), Mapping):
                raise RealFiveArmExecutionAdapterError("TrainerEnvironment cannot restore deterministic resume state")
            loader(dict(resume_state["environment_training_state"]))
        try:
            reset = environment.reset(rngs[0], rngs[1])
            _states, _masks, observation = reset
            interval_s = float(step_environment.driver.config.ephemeris.time_step_s)
        except Exception as error:
            raise RealFiveArmExecutionAdapterError("canonical TrainerEnvironment reset/interval failed") from error
        if not math.isfinite(interval_s) or interval_s <= 0:
            raise RealFiveArmExecutionAdapterError("decision interval is invalid")
        total_bits = total_energy = 0.0
        served_total = 0
        trace = hashlib.sha256()
        initial_digest: str | None = None
        for step in range(self.steps):
            native = self.encode_native_state(step_environment, observation)
            observation_digest = _observation_digest(native)
            if initial_digest is None:
                initial_digest = observation_digest
            c3_view = self.c3_view_factory(step_environment, observation, observation_digest)
            actions = np.asarray(policy.select_actions(native_state=native, c3_view=c3_view, native_observation_event_digest=observation_digest), dtype=np.int64)
            if actions.shape != (self.users,):
                raise RealFiveArmExecutionAdapterError("policy did not select one joint action per user")
            trace.update(actions.tobytes(order="C"))
            try:
                environment.step(actions, rngs[0])
                outcome = environment.last_outcome
                rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
                power = float(outcome.system_power_w)
                served = int(outcome.resolution.served_count)
            except Exception as error:
                raise RealFiveArmExecutionAdapterError("real environment step lacks physical outcome") from error
            if rates.shape != (self.users,) or not np.all(np.isfinite(rates)) or np.any(rates < 0) or not math.isfinite(power) or power <= 0 or not 0 <= served <= self.users:
                raise RealFiveArmExecutionAdapterError("physical outcome is invalid")
            total_bits += interval_s * math.fsum(float(rate) for rate in rates)
            total_energy += interval_s * power
            served_total += served
            if step < self.steps - 1:
                if bool(getattr(outcome, "done", False)):
                    raise RealFiveArmExecutionAdapterError("environment ended before ten steps")
                observation = outcome.observation
            elif not bool(getattr(outcome, "done", False)):
                raise RealFiveArmExecutionAdapterError("environment did not end after ten steps")
        state_fn = getattr(environment, "training_state_dict", None)
        if not callable(state_fn):
            raise RealFiveArmExecutionAdapterError("TrainerEnvironment lacks deterministic resume state")
        saved = state_fn()
        if not isinstance(saved, Mapping) or initial_digest is None:
            raise RealFiveArmExecutionAdapterError("environment resume state is malformed")
        self._resume_by_arm[arm] = {
            "schema": "multi-catfish-mcrl-v023-five-arm-real-resume-v1",
            "arm": arm,
            "episode_index": int(world.episode_index),
            "world_id": str(world.world_id),
            "world_seed": int(world.world_seed),
            "field_root_digest": str(world.field_root_digest),
            "policy_checkpoint_sha256": self.policies[arm].checkpoint_sha256,
            "environment_training_state": dict(saved),
        }
        return _results.FiveArmEpisodeReceipt(
            schema=_results.RECEIPT_SCHEMA, arm=arm, episode_index=int(world.episode_index),
            world_id=str(world.world_id), world_seed=int(world.world_seed), field_root_digest=field.root_digest,
            initial_world_sha256=initial_digest, policy_checkpoint_sha256=self.policies[arm].checkpoint_sha256,
            source_arm_sha256=self.policies[arm].source_arm_sha256, evaluation_binding_sha256=self.binding_sha256,
            action_trace_sha256=trace.hexdigest(), total_bits=total_bits, total_energy_j=total_energy,
            ratio_of_sums_ee_bits_per_j=total_bits / total_energy, served_user_steps=served_total,
            service_opportunities=self.users * self.steps, service_fraction=served_total / (self.users * self.steps),
            fixed_policy=True, learner_update=False, episode_training=False, test_split_opened=False, head_drop=False,
        )


def build_real_five_arm_execution_adapter(*, request: Any, **kwargs: Any) -> RealFiveArmExecutionAdapter:
    """Admit the current request before constructing a production adapter.

    ``V023RealFiveArmRequest.admit()`` is the only accepted source of the
    sealed C3/five-arm gate admission.  Calling this factory with an absent or
    pre-admission request fails before a TLE-backed environment can be made.
    """
    admit = getattr(request, "admit", None)
    if not callable(admit):
        raise RealFiveArmExecutionAdapterError("current C3/five-arm gate admission request is absent")
    try:
        admission = admit()
    except Exception as error:
        raise RealFiveArmExecutionAdapterError("current C3/five-arm gate admission failed") from error
    return RealFiveArmExecutionAdapter(admission=admission, **kwargs)
