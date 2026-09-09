"""Three-Q zero-bootstrap learner for Multi-Catfish MCRL V0.3.

This module is deliberately separate from :mod:`mcrl.algorithms.modqn`.
Legacy MODQN learns three Bellman rewards with target networks; V0.3 learns
fixed-horizon pairwise EE-surplus differences.  Sharing either replay rows or
checkpoint formats between those estimators would mix incompatible units.
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
from ..runtime.q_network import DQNNetwork


PAIRWISE_ALGORITHM = "multi-catfish-mcrl-ee-axis-v03-pairwise"
PAIRWISE_CHECKPOINT_VERSION = 1
ROUTE_NAMES = ("C1", "C2", "C3")


@dataclass(frozen=True)
class EEAxisPairwiseConfig:
    """All trainable choices for Pilot 1; no legacy reward weight exists."""

    state_dim: int
    action_dim: int
    hidden_layers: tuple[int, ...]
    activation: str
    learning_rate: float
    kappa_bits: float
    beta: float
    loss_weights: tuple[float, float, float]

    def __post_init__(self) -> None:
        if self.state_dim < 1 or self.action_dim < 1:
            raise ValueError("state_dim and action_dim must be positive")
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


@dataclass(frozen=True)
class EEAxisPairBatch:
    """One atomic batch of same-anchor candidate/reference comparisons."""

    states: np.ndarray
    reference_actions: np.ndarray
    candidate_actions: np.ndarray
    target_surplus_bits: np.ndarray
    action_masks: np.ndarray

    def validate(self, *, state_dim: int, action_dim: int) -> None:
        states = np.asarray(self.states)
        reference = np.asarray(self.reference_actions)
        candidate = np.asarray(self.candidate_actions)
        target = np.asarray(self.target_surplus_bits)
        masks = np.asarray(self.action_masks)
        if states.ndim != 2 or states.shape[1] != state_dim:
            raise ValueError(
                f"states must have shape (batch, {state_dim}), got {states.shape}"
            )
        batch = states.shape[0]
        for name, value in (
            ("reference_actions", reference),
            ("candidate_actions", candidate),
            ("target_surplus_bits", target),
        ):
            if value.shape != (batch,):
                raise ValueError(f"{name} must have shape ({batch},), got {value.shape}")
        if masks.shape != (batch, action_dim) or masks.dtype != np.bool_:
            raise ValueError(
                f"action_masks must be boolean shape ({batch}, {action_dim})"
            )
        if not np.all(np.isfinite(states)) or not np.all(np.isfinite(target)):
            raise ValueError("pairwise states and targets must be finite")
        if not np.issubdtype(reference.dtype, np.integer) or not np.issubdtype(
            candidate.dtype, np.integer
        ):
            raise TypeError("pairwise actions must be integer arrays")
        for name, actions in (("reference", reference), ("candidate", candidate)):
            if np.any(actions < 0) or np.any(actions >= action_dim):
                raise ValueError(f"{name} action lies outside [0, {action_dim})")
            if batch and not np.all(masks[np.arange(batch), actions]):
                raise MCRLContractError(
                    f"{name} action is invalid under its stored decision mask"
                )


class EEAxisPairwiseTrainer:
    """Exactly three independent online Q functions in common surplus units."""

    def __init__(
        self,
        config: EEAxisPairwiseConfig,
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
            [
                DQNNetwork(
                    config.state_dim,
                    config.action_dim,
                    config.hidden_layers,
                    config.activation,
                ).to(self.device)
                for _ in ROUTE_NAMES
            ]
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
        values = np.asarray(states, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != self.config.state_dim:
            raise ValueError(
                f"states must have shape (batch, {self.config.state_dim})"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("states must be finite")
        with torch.no_grad():
            # Source records are intentionally immutable.  ``torch.as_tensor``
            # aliases a read-only NumPy buffer and emits an undefined-behavior
            # warning, so cross the learner boundary with an owned copy.
            tensor = torch.tensor(values, dtype=torch.float32, device=self.device)
            outputs = tuple(network(tensor).cpu().numpy() for network in self.q_nets)
        return outputs  # type: ignore[return-value]

    def deployment_scores(self, states: np.ndarray) -> np.ndarray:
        q1, q2, q3 = self.q_values(states)
        return q1 + q2 + q3

    def select_greedy_actions(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        masks_array = np.asarray(masks)
        scores = self.deployment_scores(states)
        if masks_array.shape != scores.shape or masks_array.dtype != np.bool_:
            raise ValueError("masks must be boolean and match the Q surface shape")
        actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
        for row in range(scores.shape[0]):
            if not np.any(masks_array[row]):
                continue
            masked = np.where(masks_array[row], scores[row], -np.inf)
            actions[row] = int(np.argmax(masked))
        return actions

    def update_route(self, route: str, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        route_index = self._route_index(route)
        batch.validate(
            state_dim=self.config.state_dim,
            action_dim=self.config.action_dim,
        )
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
        normalized_target = torch.tensor(
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
        residual = q_candidate - q_reference - normalized_target
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
            "format_version": PAIRWISE_CHECKPOINT_VERSION,
            "algorithm": PAIRWISE_ALGORITHM,
            "update_count": update_count,
            "train_seed": self.train_seed,
            "config": asdict(self.config),
            "q_networks": [network.state_dict() for network in self.q_nets],
            "optimizers": [optimizer.state_dict() for optimizer in self.optimizers],
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if state.get("algorithm") != PAIRWISE_ALGORITHM:
            raise MCRLContractError(
                "checkpoint is not a Multi-Catfish V0.3 pairwise checkpoint"
            )
        if state.get("format_version") != PAIRWISE_CHECKPOINT_VERSION:
            raise MCRLContractError("unsupported V0.3 pairwise checkpoint version")
        if state.get("config") != asdict(self.config):
            raise MCRLContractError("V0.3 pairwise checkpoint config mismatch")
        networks = state.get("q_networks")
        optimizers = state.get("optimizers")
        if not isinstance(networks, list) or len(networks) != 3:
            raise MCRLContractError("V0.3 checkpoint must contain exactly three Q networks")
        if not isinstance(optimizers, list) or len(optimizers) != 3:
            raise MCRLContractError("V0.3 checkpoint must contain three optimizer states")
        for network, payload in zip(self.q_nets, networks, strict=True):
            network.load_state_dict(payload)
        for optimizer, payload in zip(self.optimizers, optimizers, strict=True):
            optimizer.load_state_dict(payload)
        update_count = state.get("update_count")
        if isinstance(update_count, bool) or not isinstance(update_count, int) or update_count < 0:
            raise MCRLContractError("invalid V0.3 checkpoint update_count")
        assert_finite_parameters(self.q_nets)
        return update_count
