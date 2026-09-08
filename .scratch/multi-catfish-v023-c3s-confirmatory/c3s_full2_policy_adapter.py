#!/usr/bin/env python3
"""Frozen FULL2 policy adapter for the two-arm C3-S confirmatory ladder.

The adapter intentionally delegates snapshot construction and coordination to
the sealed screen implementation.  Its disabled and enabled forms therefore
share the same float32 Q1+Q2 proposal path; the only difference is whether the
screen's frozen coordinator is allowed to replace that proposal.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCREEN_DIR = REPO / ".scratch" / "multi-catfish-v023-c3s-screen"
STAGEC_PHYSICAL_DIR = (
    REPO / ".scratch" / "multi-catfish-v023-c1c2-successor-physical-evaluation"
)
PHYSICAL_DIR = REPO / ".scratch" / "multi-catfish-v023-physical"
SOURCE_RUNNER_DIR = REPO / ".scratch" / "multi-catfish-v023-two-route-source-training-runner"
for _path in (SCREEN_DIR, STAGEC_PHYSICAL_DIR, PHYSICAL_DIR, SOURCE_RUNNER_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import c3s_policy  # noqa: E402


ARMS = ("FULL2", "FULL2+C3-S")
USERS = 100
STEPS = 10
INTERVAL_SECONDS = 30.08


class C3SFull2AdapterError(RuntimeError):
    """A frozen-policy, snapshot, or episode integrity check failed."""


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise C3SFull2AdapterError(f"cannot import required module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


_stagec_physical = _load_module(
    STAGEC_PHYSICAL_DIR / "v023_c1c2_successor_physical_runner.py",
    "c3s_confirm_stagec_physical",
)
_nominal_physical = _load_module(
    PHYSICAL_DIR / "v023_physical_episode_runner.py",
    "c3s_confirm_nominal_physical",
)


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise C3SFull2AdapterError(f"required regular file is absent or symlinked: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_full2_export(path: str | Path, expected_sha256: str) -> Any:
    """Authenticate and load the producer's epoch-100 FULL2 export."""

    return _stagec_physical.load_learned_two_route_checkpoint(
        path,
        arm="FULL2",
        expected_sha256=expected_sha256,
        training_provenance=None,
    )


def _base_only_decision(snapshot: Any, _evaluator: Any) -> Any:
    """Return the proposal from the same detached snapshot used by C3-S."""

    base = np.asarray(snapshot.base_actions, dtype=np.int64)
    return c3s_policy.DecisionResult(
        actions=base.copy(),
        base_actions=base.copy(),
        profile_id="BASE",
        catalog_size=1,
        counts={"base": 1, "unilateral": 0, "joint": 0},
        nominal={},
        phase_wall_seconds={"q_inference": float(snapshot.q_inference_seconds)},
        unique_nominal_evaluations=0,
    )


class C3SFull2PolicyAdapter:
    """Stage-C-shaped fixed policy with optional frozen C3-S coordination."""

    def __init__(
        self,
        *,
        frozen_full2: Any,
        coordinator_enabled: bool,
        catalog: str,
        eta_config: str | Path = SCREEN_DIR / "c3s_config.json",
        nominal_physical: Any = _nominal_physical,
    ) -> None:
        if type(coordinator_enabled) is not bool:
            raise C3SFull2AdapterError("coordinator_enabled must be Boolean")
        if catalog not in ("lite", "full"):
            raise C3SFull2AdapterError("catalog must be 'lite' or 'full'")
        if getattr(frozen_full2, "arm", None) != "FULL2":
            raise C3SFull2AdapterError("adapter requires the authenticated FULL2 export")
        verify = getattr(frozen_full2, "verify", None)
        if not callable(verify):
            raise C3SFull2AdapterError("FULL2 export lacks its verifier")
        verify()
        self.frozen_full2 = frozen_full2
        self.coordinator_enabled = coordinator_enabled
        self.catalog = catalog
        self.arm = ARMS[1] if coordinator_enabled else ARMS[0]
        self.eta_config = Path(eta_config)
        self._delegate = c3s_policy.C3SPolicyAdapter(
            physical=nominal_physical,
            frozen=frozen_full2,
            eta_config=Path(eta_config),
            catalog=catalog,
            decision_function=None if coordinator_enabled else _base_only_decision,
        )

    @property
    def decision_records(self) -> list[dict[str, object]]:
        return self._delegate.decision_records

    def verify(self) -> None:
        self.frozen_full2.verify()
        expected = c3s_policy.load_eta_ref(self.eta_config)
        if self._delegate.eta_ref != expected or self._delegate.catalog != self.catalog:
            raise C3SFull2AdapterError("coordinator config or eta_ref drifted")

    def binding(self) -> dict[str, object]:
        self.verify()
        source = self.frozen_full2.binding()
        return {
            "arm": self.arm,
            "policy_family": "C1C2_SUCCESSOR_FULL2_WITH_OPTIONAL_FROZEN_C3S",
            "full2_export_path": source["checkpoint_path"],
            "full2_export_sha256": source["checkpoint_sha256"],
            "q1_parameter_sha256": source["q1_parameter_sha256"],
            "q2_parameter_sha256": source["q2_parameter_sha256"],
            "update_count": source["update_count"],
            "routes": source["routes"],
            "coordinator_enabled": self.coordinator_enabled,
            "catalog": self.catalog,
            "eta_ref": c3s_policy.fraction_payload(self._delegate.eta_ref),
            "coordinator_code": {
                "path": str((SCREEN_DIR / "c3s_policy.py").resolve()),
                "sha256": file_sha256(SCREEN_DIR / "c3s_policy.py"),
            },
            "coordinator_config": {
                "path": str((SCREEN_DIR / "c3s_config.json").resolve()),
                "sha256": file_sha256(SCREEN_DIR / "c3s_config.json"),
            },
            "proposal_rule": "FLOAT32_UNWEIGHTED_MASKED_Q1_PLUS_Q2_LOWEST_SLOT_TIE_NOOP_ON_EMPTY",
            "fixed_policy": True,
        }

    def select_actions(
        self, step_environment: Any, observation: Any, rng: np.random.Generator,
    ) -> np.ndarray:
        """Select one complete action vector using snapshot-only C3-S inputs."""

        self.verify()
        return self._delegate.select_actions(step_environment, observation, rng)


@dataclass(frozen=True)
class EpisodeExecution:
    arm: str
    total_bits: float
    total_energy_j: float
    served_user_steps: int
    service_opportunities: int
    action_trace_sha256: str
    initial_state_sha256: str
    decision_records: tuple[Mapping[str, object], ...]


def _array_digest(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


class FixedPolicyEpisodeAdapter:
    """Run the stage-C ten-decision episode loop without arm-specific branches."""

    def __init__(self, policy: C3SFull2PolicyAdapter, *, users: int = USERS, steps: int = STEPS) -> None:
        if users != USERS or steps != STEPS:
            raise C3SFull2AdapterError("confirmatory episodes require 100 users and 10 steps")
        policy.verify()
        self.policy = policy
        self.users = users
        self.steps = steps

    def run_episode(
        self,
        environment: Any,
        *,
        environment_rng: np.random.Generator,
        mobility_rng: np.random.Generator,
    ) -> EpisodeExecution:
        if not isinstance(environment_rng, np.random.Generator) or not isinstance(
            mobility_rng, np.random.Generator
        ):
            raise C3SFull2AdapterError("episode RNGs must be NumPy Generators")
        states, masks, observation = environment.reset(environment_rng, mobility_rng)
        del states
        from mcrl.runtime.ee_axis_state import encode_ee_axis_state

        step_environment = getattr(environment, "environment", environment)
        native = encode_ee_axis_state(step_environment, observation)
        native.verify()
        initial_state = hashlib.sha256(
            (_array_digest(native.state_matrix) + _array_digest(native.action_masks)).encode("ascii")
        ).hexdigest()
        trace = hashlib.sha256()
        bits: list[float] = []
        energy: list[float] = []
        served = 0
        first_record = len(self.policy.decision_records)
        for step_index in range(self.steps):
            actions = np.asarray(
                self.policy.select_actions(step_environment, observation, environment_rng)
            )
            mask_values = np.stack([np.asarray(mask.mask, dtype=np.bool_) for mask in masks])
            if actions.shape != (self.users,) or actions.dtype.kind not in "iu":
                raise C3SFull2AdapterError("policy did not return a complete integer action vector")
            rows = np.arange(self.users)
            if np.any(actions < 0) or np.any(actions >= mask_values.shape[1]) or np.any(
                ~mask_values[rows, actions]
            ):
                raise C3SFull2AdapterError("policy returned an illegal action")
            trace.update(actions.astype(np.int64, copy=False).tobytes(order="C"))
            result = environment.step(actions, environment_rng)
            outcome = environment.last_outcome
            rate = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            interval = float(
                getattr(
                    getattr(getattr(step_environment, "driver", None), "config", None),
                    "ephemeris",
                    type("E", (), {"time_step_s": INTERVAL_SECONDS})(),
                ).time_step_s
            )
            step_bits = interval * float(np.sum(rate, dtype=np.float64))
            step_energy = interval * power
            if not math.isfinite(step_bits) or step_bits < 0 or not math.isfinite(step_energy) or step_energy <= 0:
                raise C3SFull2AdapterError("committed endpoint is non-finite or outside its domain")
            bits.append(step_bits)
            energy.append(step_energy)
            resolution = np.asarray(getattr(outcome, "resolution", rate > 0))
            served += int(np.count_nonzero(resolution))
            done = bool(getattr(outcome, "done", getattr(result, "done", False)))
            if done != (step_index == self.steps - 1):
                raise C3SFull2AdapterError("environment termination differs from ten committed steps")
            masks = list(result.action_masks)
            observation = outcome.observation
        self.policy.verify()
        return EpisodeExecution(
            arm=self.policy.arm,
            total_bits=math.fsum(bits),
            total_energy_j=math.fsum(energy),
            served_user_steps=served,
            service_opportunities=self.users * self.steps,
            action_trace_sha256=trace.hexdigest(),
            initial_state_sha256=initial_state,
            decision_records=tuple(self.policy.decision_records[first_record:]),
        )


__all__ = [
    "ARMS",
    "C3SFull2AdapterError",
    "C3SFull2PolicyAdapter",
    "EpisodeExecution",
    "FixedPolicyEpisodeAdapter",
    "load_full2_export",
]
