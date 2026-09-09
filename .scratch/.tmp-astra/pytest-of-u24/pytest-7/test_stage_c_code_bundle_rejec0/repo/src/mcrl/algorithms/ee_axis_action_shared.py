"""Permutation-equivariant three-Q learner for Multi-Catfish MCRL V0.3.

The original E1 prototype emitted 28 scores from fixed output neurons.  That
allowed a state-independent action-slot effect to dominate pair learning.
This module instead applies the same scalar scorer to every action-aligned
feature vector.  It keeps three independent route-local Q functions while
making action identity enter only through observed physical features.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from ..env.action_contract import NO_OP_ACTION
from ..errors import MCRLContractError
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from .ee_axis_pairwise import EEAxisPairBatch, ROUTE_NAMES


ACTION_SHARED_ALGORITHM = "multi-catfish-mcrl-ee-axis-v03-action-shared"
ACTION_SHARED_CHECKPOINT_VERSION = 1
ACTION_ALIGNED_FEATURES = 8
GLOBAL_FEATURES = 4


@dataclass(frozen=True)
class EEAxisActionSharedConfig:
    """Trainable choices for the local action-shared pairwise learner."""

    state_dim: int
    action_dim: int
    hidden_layers: tuple[int, ...]
    activation: str
    learning_rate: float
    kappa_bits: float
    beta: float
    loss_weights: tuple[float, float, float]

    def __post_init__(self) -> None:
        expected = ACTION_ALIGNED_FEATURES * self.action_dim + GLOBAL_FEATURES
        if self.action_dim < 1 or self.state_dim != expected:
            raise ValueError(
                "action-shared state_dim must equal "
                f"{ACTION_ALIGNED_FEATURES} * action_dim + {GLOBAL_FEATURES}"
            )
        if not self.hidden_layers or any(width < 1 for width in self.hidden_layers):
            raise ValueError("hidden_layers must contain positive widths")
        if self.activation not in {"tanh", "relu"}:
            raise ValueError("activation must be 'tanh' or 'relu'")
        for name in ("learning_rate", "kappa_bits"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        if not np.isfinite(self.beta) or self.beta < 0.0:
            raise ValueError("beta must be finite and nonnegative")
        if len(self.loss_weights) != 3 or any(
            not np.isfinite(weight) or weight <= 0.0
            for weight in self.loss_weights
        ):
            raise ValueError("loss_weights must be three finite positive values")


class ActionSharedQNetwork(nn.Module):
    """Apply one scalar MLP to every action's aligned local features."""

    def __init__(self, config: EEAxisActionSharedConfig) -> None:
        super().__init__()
        activation = nn.Tanh if config.activation == "tanh" else nn.ReLU
        widths = (
            ACTION_ALIGNED_FEATURES + GLOBAL_FEATURES,
            *config.hidden_layers,
            1,
        )
        layers: list[nn.Module] = []
        for left, right in zip(widths[:-2], widths[1:-1], strict=True):
            layers.extend((nn.Linear(left, right), activation()))
        layers.append(nn.Linear(widths[-2], widths[-1]))
        self.scorer = nn.Sequential(*layers)
        self.action_dim = config.action_dim

    def forward(self, states: torch.Tensor) -> torch.Tensor:
        if states.ndim != 2:
            raise ValueError("action-shared Q input must be a state matrix")
        batch = states.shape[0]
        aligned_width = ACTION_ALIGNED_FEATURES * self.action_dim
        expected = aligned_width + GLOBAL_FEATURES
        if states.shape[1] != expected:
            raise ValueError(
                f"action-shared Q input width must be {expected}, got {states.shape[1]}"
            )
        local = states[:, :aligned_width].reshape(
            batch, ACTION_ALIGNED_FEATURES, self.action_dim
        ).transpose(1, 2)
        global_features = states[:, aligned_width:].unsqueeze(1).expand(
            -1, self.action_dim, -1
        )
        features = torch.cat((local, global_features), dim=2)
        return self.scorer(features).squeeze(2)


class EEAxisActionSharedTrainer:
    """Exactly three independent, action-equivariant online Q functions."""

    def __init__(
        self,
        config: EEAxisActionSharedConfig,
        *,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        if isinstance(train_seed, bool) or not isinstance(train_seed, int):
            raise TypeError("train_seed must be an integer")
        self.config = config
        self.train_seed = train_seed
        self.device = torch.device(device)
        torch.manual_seed(train_seed)
        self.q_nets = nn.ModuleList(
            [ActionSharedQNetwork(config).to(self.device) for _ in ROUTE_NAMES]
        )
        self.optimizers = [
            optim.Adam(network.parameters(), lr=config.learning_rate)
            for network in self.q_nets
        ]
        parameter_ids = [
            {id(parameter) for parameter in network.parameters()}
            for network in self.q_nets
        ]
        if any(parameter_ids[i] & parameter_ids[j] for i in range(3) for j in range(i)):
            raise RuntimeError("V0.3 Q functions may not share trainable parameters")

    @staticmethod
    def _route_index(route: str) -> int:
        try:
            return ROUTE_NAMES.index(route)
        except ValueError as exc:
            raise ValueError(f"route must be one of {ROUTE_NAMES}, got {route!r}") from exc

    def q_values(self, states: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Evaluate every route on one shared state view (V0.3 API)."""

        return self.q_values_by_route({route: states for route in ROUTE_NAMES})

    def q_values_by_route(
        self,
        states_by_route: Mapping[str, np.ndarray],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Evaluate each independent Q on its own causal state view.

        V0.4 keeps the V0.3 view for Q1/Q2 and supplies only Q3 with the
        victim-burden view.  All views must describe the same user batch and
        retain the same 228-D/action-slot contract; only their causal feature
        contents may differ.
        """

        if not isinstance(states_by_route, Mapping) or set(states_by_route) != set(
            ROUTE_NAMES
        ):
            raise ValueError(f"states_by_route must contain exactly {ROUTE_NAMES}")
        values_by_route: list[np.ndarray] = []
        batch_size: int | None = None
        for route in ROUTE_NAMES:
            values = np.asarray(states_by_route[route], dtype=np.float32)
            if values.ndim != 2 or values.shape[1] != self.config.state_dim:
                raise ValueError(
                    f"{route} states must have shape (batch, {self.config.state_dim})"
                )
            if not np.all(np.isfinite(values)):
                raise ValueError(f"{route} states must be finite")
            if batch_size is None:
                batch_size = int(values.shape[0])
            elif values.shape[0] != batch_size:
                raise ValueError("route state views must share one batch dimension")
            values_by_route.append(values)
        with torch.no_grad():
            outputs = tuple(
                network(
                    torch.tensor(values, dtype=torch.float32, device=self.device)
                )
                .cpu()
                .numpy()
                for network, values in zip(
                    self.q_nets, values_by_route, strict=True
                )
            )
        return outputs  # type: ignore[return-value]

    def deployment_scores(self, states: np.ndarray) -> np.ndarray:
        q1, q2, q3 = self.q_values(states)
        return q1 + q2 + q3

    def deployment_scores_by_route(
        self,
        states_by_route: Mapping[str, np.ndarray],
    ) -> np.ndarray:
        """Sum the three route-local Q surfaces without a coordinator."""

        q1, q2, q3 = self.q_values_by_route(states_by_route)
        return q1 + q2 + q3

    def select_greedy_actions(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        masks_array = np.asarray(masks)
        scores = self.deployment_scores(states)
        if masks_array.shape != scores.shape or masks_array.dtype != np.bool_:
            raise ValueError("masks must be boolean and match the Q surface shape")
        actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
        eligible = np.any(masks_array, axis=1)
        actions[eligible] = np.argmax(
            np.where(masks_array[eligible], scores[eligible], -np.inf), axis=1
        )
        return actions

    def select_greedy_actions_by_route(
        self,
        states_by_route: Mapping[str, np.ndarray],
        masks: np.ndarray,
    ) -> np.ndarray:
        """Apply the one masked argmax to the route-view Q sum."""

        masks_array = np.asarray(masks)
        scores = self.deployment_scores_by_route(states_by_route)
        if masks_array.shape != scores.shape or masks_array.dtype != np.bool_:
            raise ValueError("masks must be boolean and match the Q surface shape")
        actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
        eligible = np.any(masks_array, axis=1)
        actions[eligible] = np.argmax(
            np.where(masks_array[eligible], scores[eligible], -np.inf), axis=1
        )
        return actions

    def update_route(self, route: str, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        route_index = self._route_index(route)
        batch.validate(state_dim=self.config.state_dim, action_dim=self.config.action_dim)
        states = torch.tensor(
            np.asarray(batch.states, dtype=np.float32),
            dtype=torch.float32,
            device=self.device,
        )
        reference = torch.tensor(
            np.asarray(batch.reference_actions, dtype=np.int64),
            dtype=torch.int64,
            device=self.device,
        )
        candidate = torch.tensor(
            np.asarray(batch.candidate_actions, dtype=np.int64),
            dtype=torch.int64,
            device=self.device,
        )
        target = torch.tensor(
            np.asarray(batch.target_surplus_bits, dtype=np.float32)
            / float(self.config.kappa_bits),
            dtype=torch.float32,
            device=self.device,
        )
        network = self.q_nets[route_index]
        optimizer = self.optimizers[route_index]
        q_surface = network(states)
        q_reference = q_surface.gather(1, reference[:, None]).squeeze(1)
        q_candidate = q_surface.gather(1, candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - target
        pair_mse = torch.mean(residual.square())
        gauge_mse = torch.mean(q_reference.square())
        loss = float(self.config.loss_weights[route_index]) * (
            pair_mse + float(self.config.beta) * gauge_mse
        )
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=route_index + 1)
        assert_finite_gradients(network.parameters(), objective=route_index + 1)
        optimizer.step()
        assert_finite_parameters(self.q_nets)
        return {
            "route": route,
            "batch_size": int(states.shape[0]),
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    def checkpoint_state(self, *, update_count: int) -> dict[str, Any]:
        if isinstance(update_count, bool) or not isinstance(update_count, int) or update_count < 0:
            raise ValueError("update_count must be a nonnegative integer")
        return {
            "format_version": ACTION_SHARED_CHECKPOINT_VERSION,
            "algorithm": ACTION_SHARED_ALGORITHM,
            "update_count": update_count,
            "train_seed": self.train_seed,
            "config": asdict(self.config),
            "q_networks": [network.state_dict() for network in self.q_nets],
            "optimizers": [optimizer.state_dict() for optimizer in self.optimizers],
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if state.get("algorithm") != ACTION_SHARED_ALGORITHM:
            raise MCRLContractError("checkpoint is not an action-shared V0.3 checkpoint")
        if state.get("format_version") != ACTION_SHARED_CHECKPOINT_VERSION:
            raise MCRLContractError("unsupported action-shared checkpoint version")
        if state.get("train_seed") != self.train_seed:
            raise MCRLContractError("action-shared checkpoint train_seed mismatch")
        if state.get("config") != asdict(self.config):
            raise MCRLContractError("action-shared checkpoint config mismatch")
        networks = state.get("q_networks")
        optimizers = state.get("optimizers")
        if not isinstance(networks, list) or len(networks) != 3:
            raise MCRLContractError("action-shared checkpoint must contain three Q networks")
        if not isinstance(optimizers, list) or len(optimizers) != 3:
            raise MCRLContractError("action-shared checkpoint must contain three optimizers")
        update_count = state.get("update_count")
        if isinstance(update_count, bool) or not isinstance(update_count, int) or update_count < 0:
            raise MCRLContractError("invalid action-shared checkpoint update_count")
        for network, payload in zip(self.q_nets, networks, strict=True):
            network.load_state_dict(payload)
        for optimizer, payload in zip(self.optimizers, optimizers, strict=True):
            optimizer.load_state_dict(payload)
        assert_finite_parameters(self.q_nets)
        return update_count
