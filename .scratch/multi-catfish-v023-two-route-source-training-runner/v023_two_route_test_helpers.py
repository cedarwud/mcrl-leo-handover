"""Small deterministic producer-style fixtures for the two-route tests only."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014NormalizedPairBatch,
)
from ee_axis_two_route_model import EEAxisTwoRouteConfig
from v023_two_route_learner_orchestrator import ProvidedRouteBatch, ROUTE_ORDER, SOURCE_ORDER


def model_config() -> EEAxisTwoRouteConfig:
    q1 = EEAxisActionSharedConfig(
        state_dim=228,
        action_dim=28,
        hidden_layers=(2,),
        activation="relu",
        learning_rate=1.0e-2,
        kappa_bits=10.0,
        beta=0.2,
        loss_weights=(1.0, 2.0, 3.0),
    )
    q2 = EEAxisV014HeadConfig(
        action_dim=28,
        local_feature_dim=16,
        global_feature_dim=0,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=1.0e-3,
        kappa_bits=10.0,
        beta=0.1,
    )
    return EEAxisTwoRouteConfig(q1=q1, q2=q2)


def c1_batch(target: float) -> EEAxisPairBatch:
    states = np.zeros((2, 228), dtype=np.float32)
    states[:, 0] = (0.25, -0.5)
    states[:, 1] = (-0.75, 0.5)
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray((0, 1), dtype=np.int64),
        candidate_actions=np.asarray((1, 2), dtype=np.int64),
        target_surplus_bits=np.asarray((target, target + 0.25), dtype=np.float64),
        action_masks=np.ones((2, 28), dtype=np.bool_),
    )


def c2_batch(target: float) -> EEAxisV014NormalizedPairBatch:
    features = np.zeros((2, 16, 28), dtype=np.float32)
    features[:, 0, 0] = (0.25, -0.5)
    features[:, 0, 1] = (-0.75, 0.5)
    return EEAxisV014NormalizedPairBatch(
        states=features.reshape(2, 448),
        reference_actions=np.asarray((0, 1), dtype=np.int64),
        candidate_actions=np.asarray((1, 2), dtype=np.int64),
        normalized_target_deltas=np.asarray((target, target + 0.25), dtype=np.float64),
        action_masks=np.ones((2, 28), dtype=np.bool_),
    )


class StubDeterministicRouteBatchProvider:
    """Orchestrator-local stub with exact route/source cursors and identity."""

    def __init__(self, *, routes: tuple[str, ...] = ROUTE_ORDER, budget: int = 100) -> None:
        self.routes = routes
        self.planned_epoch_budget = budget
        self.provider_identity = "c1c2-stub-provider-v1"
        self.provider_identity_payload = {"schema": "c1c2-stub-v1", "routes": list(routes)}
        self._positions = {
            (route, source): 0 for route in ROUTE_ORDER for source in SOURCE_ORDER
        }
        self.calls: list[tuple[str, str, int]] = []

    def next_batch(self, *, route: str, source: str, update_cursor: int) -> ProvidedRouteBatch:
        key = (route, source)
        position = self._positions[key]
        self._positions[key] = position + 1
        self.calls.append((route, source, update_cursor))
        target = 2.0 if source == "informed" else -1.0
        return ProvidedRouteBatch(
            route=route,
            source=source,
            file_id=f"{route.lower()}-{source}-{position:04d}",
            batch=c1_batch(target) if route == "C1" else c2_batch(target),
        )

    def sampler_state(self) -> dict[str, Any]:
        return {"positions": deepcopy(self._positions)}

    def load_sampler_state(self, state: dict[str, Any]) -> None:
        self._positions = deepcopy(state["positions"])


def stub_provider(**kwargs: Any) -> StubDeterministicRouteBatchProvider:
    return StubDeterministicRouteBatchProvider(**kwargs)

