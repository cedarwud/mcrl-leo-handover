"""Reusable read-only physics capture and reward/endpoint parity checks."""

from __future__ import annotations

import copy
import math
from types import MethodType
from typing import Any, Sequence

import numpy as np


class PhysicsSnapshotExtractor:
    """Capture V0.23-compatible physics/fading without changing return values.

    Call ``close`` after use.  The wrapper keeps original bound methods and is
    intentionally duck-typed so the V0.25 engine can import it during parity
    work without taking a source dependency on V0.23 classes.
    """

    def __init__(self, environment: Any) -> None:
        self.environment = environment
        self.physics: dict[str, Any] | None = None
        self.fading: dict[int, np.ndarray] = {}
        self.shadow: dict[int, np.ndarray] = {}
        self._resolve = environment._resolve_physics
        self._draw = environment._draw_fading

        def draw(_instance: Any, *args: Any, **kwargs: Any) -> Any:
            fading, shadow = self._draw(*args, **kwargs)
            if kwargs.get("event", "direct") == "physics":
                self.fading = {int(key): np.array(value, copy=True) for key, value in fading.items()}
                self.shadow = {int(key): np.array(value, copy=True) for key, value in shadow.items()}
            return fading, shadow

        def resolve(_instance: Any, *args: Any, **kwargs: Any) -> Any:
            payload = self._resolve(*args, **kwargs)
            self.physics = {
                key: np.array(value, copy=True) if isinstance(value, np.ndarray) else copy.deepcopy(value)
                for key, value in payload.items()
            }
            return payload

        environment._draw_fading = MethodType(draw, environment)
        environment._resolve_physics = MethodType(resolve, environment)

    def close(self) -> None:
        self.environment._draw_fading = self._draw
        self.environment._resolve_physics = self._resolve

    def __enter__(self) -> "PhysicsSnapshotExtractor":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def reward_endpoint_residual(
    *,
    step_bits: Sequence[float],
    step_energy_j: Sequence[float],
    step_rewards: Sequence[float],
    eta_bits_per_j: float,
    endpoint_bits: float,
    endpoint_energy_j: float,
) -> float:
    if not (len(step_bits) == len(step_energy_j) == len(step_rewards)):
        raise ValueError("step arrays must have equal length")
    eta = float(eta_bits_per_j)
    expected_steps = math.fsum(
        float(bits) - eta * float(energy)
        for bits, energy in zip(step_bits, step_energy_j, strict=True)
    )
    recorded_steps = math.fsum(float(value) for value in step_rewards)
    endpoint = float(endpoint_bits) - eta * float(endpoint_energy_j)
    return max(abs(recorded_steps - expected_steps), abs(recorded_steps - endpoint))


def assert_reward_endpoint_identity(*, atol: float = 1e-9, **values: Any) -> None:
    residual = reward_endpoint_residual(**values)
    if residual > float(atol):
        raise AssertionError(f"reward-endpoint identity residual {residual:.17g} exceeds {atol:.17g}")
