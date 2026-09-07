"""Masked mean/max context scorer for the single bounded V0.3 fallback.

This module is deliberately separate from :mod:`ee_axis_action_shared`.  The
ordinary action-shared scorer remains the primary E1 learner and its sealed
authority is not rewritten.  The fallback adds only permutation-equivariant
candidate-set context:

``Q_j(s, a) = f_{theta_j}(x_a, g, mean_m(x), max_m(x))``.

The legal-action mask is supplied explicitly by each pair batch or deployment
call.  It is never inferred from an observation feature (the state access
block can disagree with the deployment mask in a diagnostic fixture).  No Q
output is shared between C1, C2, and C3.  This is an instrument-level
fallback; it does not change the physical Catfish targets, source rows,
deployment rule, or EE endpoint.
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
from .ee_axis_action_shared import (
    ACTION_ALIGNED_FEATURES,
    GLOBAL_FEATURES,
)
from .ee_axis_pairwise import EEAxisPairBatch, ROUTE_NAMES


MASKED_MEANMAX_ALGORITHM = (
    "multi-catfish-mcrl-ee-axis-v03-action-shared-masked-meanmax"
)
MASKED_MEANMAX_CHECKPOINT_VERSION = 1
MASKED_MEANMAX_CONTEXT_FEATURES = ACTION_ALIGNED_FEATURES * 2


@dataclass(frozen=True)
class EEAxisMaskedMeanMaxConfig:
    """Frozen learner choices for the one predeclared mean/max fallback."""

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
                "masked mean/max state_dim must equal "
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


class MaskedMeanMaxQNetwork(nn.Module):
    """Apply one scalar MLP to every action with legal-set context."""

    def __init__(self, config: EEAxisMaskedMeanMaxConfig) -> None:
        super().__init__()
        activation = nn.Tanh if config.activation == "tanh" else nn.ReLU
        widths = (
            ACTION_ALIGNED_FEATURES + GLOBAL_FEATURES + MASKED_MEANMAX_CONTEXT_FEATURES,
            *config.hidden_layers,
            1,
        )
        layers: list[nn.Module] = []
        for left, right in zip(widths[:-2], widths[1:-1], strict=True):
            layers.extend((nn.Linear(left, right), activation()))
        layers.append(nn.Linear(widths[-2], widths[-1]))
        self.scorer = nn.Sequential(*layers)
        self.action_dim = config.action_dim

    def _features(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        if states.ndim != 2:
            raise ValueError("masked mean/max input must be a state matrix")
        if masks.ndim != 2 or masks.dtype != torch.bool:
            raise ValueError("masked mean/max masks must be a Boolean matrix")
        batch = states.shape[0]
        aligned_width = ACTION_ALIGNED_FEATURES * self.action_dim
        expected = aligned_width + GLOBAL_FEATURES
        if states.shape[1] != expected:
            raise ValueError(
                f"masked mean/max input width must be {expected}, got {states.shape[1]}"
            )
        if masks.shape != (batch, self.action_dim):
            raise ValueError(
                "masked mean/max masks must have shape "
                f"({batch}, {self.action_dim})"
            )
        if not torch.all(torch.any(masks, dim=1)):
            raise ValueError("masked mean/max masks must admit at least one action")
        # State layout is [feature_0(action slots), ..., feature_7(action
        # slots), temporal globals].  The explicit deployment mask—not any
        # state feature—defines the legal candidate set for context pooling.
        local = states[:, :aligned_width].reshape(
            batch, ACTION_ALIGNED_FEATURES, self.action_dim
        ).transpose(1, 2)
        global_features = states[:, aligned_width:].unsqueeze(1).expand(
            -1, self.action_dim, -1
        )
        legal = masks.unsqueeze(2)
        count = legal.to(local.dtype).sum(dim=1, keepdim=True)
        safe_count = torch.clamp(count, min=1.0)
        masked_local = torch.where(legal, local, torch.zeros_like(local))
        mean_context = masked_local.sum(dim=1, keepdim=True) / safe_count
        negative_inf = torch.full_like(local, -torch.inf)
        max_context = torch.where(legal, local, negative_inf).amax(dim=1, keepdim=True)
        max_context = torch.where(count > 0.0, max_context, torch.zeros_like(max_context))
        mean_context = mean_context.expand(-1, self.action_dim, -1)
        max_context = max_context.expand(-1, self.action_dim, -1)
        return torch.cat(
            (local, global_features, mean_context, max_context), dim=2
        )

    def forward(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        return self.scorer(self._features(states, masks)).squeeze(2)


class EEAxisMaskedMeanMaxTrainer:
    """Three independent route-local Q functions for the bounded fallback."""

    def __init__(
        self,
        config: EEAxisMaskedMeanMaxConfig,
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
            [MaskedMeanMaxQNetwork(config).to(self.device) for _ in ROUTE_NAMES]
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
            raise RuntimeError("V0.3 fallback Q functions may not share parameters")

    @staticmethod
    def _route_index(route: str) -> int:
        try:
            return ROUTE_NAMES.index(route)
        except ValueError as exc:
            raise ValueError(f"route must be one of {ROUTE_NAMES}, got {route!r}") from exc

    @staticmethod
    def _validate_masks(
        masks: np.ndarray, *, batch: int, action_dim: int
    ) -> np.ndarray:
        values = np.asarray(masks)
        if values.dtype != np.bool_ or values.shape != (batch, action_dim):
            raise ValueError(
                "masks must be Boolean with shape "
                f"({batch}, {action_dim})"
            )
        if not np.all(np.any(values, axis=1)):
            raise ValueError("masks must admit at least one action per row")
        return values

    def q_values(
        self, states: np.ndarray, masks: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        values = np.asarray(states, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != self.config.state_dim:
            raise ValueError(f"states must have shape (batch, {self.config.state_dim})")
        if not np.all(np.isfinite(values)):
            raise ValueError("states must be finite")
        mask_values = self._validate_masks(
            masks, batch=values.shape[0], action_dim=self.config.action_dim
        )
        with torch.no_grad():
            tensor = torch.tensor(values, dtype=torch.float32, device=self.device)
            mask_tensor = torch.tensor(mask_values, dtype=torch.bool, device=self.device)
            outputs = tuple(
                network(tensor, mask_tensor).cpu().numpy() for network in self.q_nets
            )
        return outputs  # type: ignore[return-value]

    def deployment_scores(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        q1, q2, q3 = self.q_values(states, masks)
        return q1 + q2 + q3

    def select_greedy_actions(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        masks_array = np.asarray(masks)
        scores = self.deployment_scores(states, masks_array)
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
        masks = torch.tensor(
            np.asarray(batch.action_masks, dtype=np.bool_),
            dtype=torch.bool,
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
        q_surface = network(states, masks)
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
            "format_version": MASKED_MEANMAX_CHECKPOINT_VERSION,
            "algorithm": MASKED_MEANMAX_ALGORITHM,
            "update_count": update_count,
            "train_seed": self.train_seed,
            "config": asdict(self.config),
            "q_networks": [network.state_dict() for network in self.q_nets],
            "optimizers": [optimizer.state_dict() for optimizer in self.optimizers],
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if state.get("algorithm") != MASKED_MEANMAX_ALGORITHM:
            raise MCRLContractError("checkpoint is not a masked mean/max fallback checkpoint")
        if state.get("format_version") != MASKED_MEANMAX_CHECKPOINT_VERSION:
            raise MCRLContractError("unsupported masked mean/max checkpoint version")
        if state.get("train_seed") != self.train_seed:
            raise MCRLContractError("masked mean/max checkpoint train_seed mismatch")
        if state.get("config") != asdict(self.config):
            raise MCRLContractError("masked mean/max checkpoint config mismatch")
        networks = state.get("q_networks")
        optimizers = state.get("optimizers")
        if not isinstance(networks, list) or len(networks) != 3:
            raise MCRLContractError("fallback checkpoint must contain three Q networks")
        if not isinstance(optimizers, list) or len(optimizers) != 3:
            raise MCRLContractError("fallback checkpoint must contain three optimizers")
        update_count = state.get("update_count")
        if isinstance(update_count, bool) or not isinstance(update_count, int) or update_count < 0:
            raise MCRLContractError("invalid masked mean/max checkpoint update_count")
        for network, payload in zip(self.q_nets, networks, strict=True):
            network.load_state_dict(payload)
        for optimizer, payload in zip(self.optimizers, optimizers, strict=True):
            optimizer.load_state_dict(payload)
        assert_finite_parameters(self.q_nets)
        return update_count


def config_from_action_shared(
    config: Any,
) -> EEAxisMaskedMeanMaxConfig:
    """Copy frozen scalar hyperparameters while changing only the scorer label."""

    return EEAxisMaskedMeanMaxConfig(
        state_dim=int(config.state_dim),
        action_dim=int(config.action_dim),
        hidden_layers=tuple(int(width) for width in config.hidden_layers),
        activation=str(config.activation),
        learning_rate=float(config.learning_rate),
        kappa_bits=float(config.kappa_bits),
        beta=float(config.beta),
        loss_weights=tuple(float(weight) for weight in config.loss_weights),
    )


__all__ = [
    "MASKED_MEANMAX_ALGORITHM",
    "MASKED_MEANMAX_CHECKPOINT_VERSION",
    "EEAxisMaskedMeanMaxConfig",
    "MaskedMeanMaxQNetwork",
    "EEAxisMaskedMeanMaxTrainer",
    "config_from_action_shared",
]
