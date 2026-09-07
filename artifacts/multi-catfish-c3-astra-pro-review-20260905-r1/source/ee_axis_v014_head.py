"""Independent action-set learner used by the V0.14 Q2 and Q3 heads.

The oracle surfaces are not available to the deployed policy.  This module
provides the small shared *learner form* that distils either route from its
own decision-time state.  Instances never share parameters or optimizers and
this module does not construct, read, or update Q1.

States use a feature-major layout::

    [local_feature_0(all actions), ..., local_feature_L(all actions), globals]

Each action is scored by the same MLP from its local values, the state globals,
and legal-set mean/max context.  This makes the scorer equivariant to the
ordering of candidate actions while retaining the explicit deployment mask.
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
from .ee_axis_pairwise import EEAxisPairBatch


V014_HEAD_ALGORITHM = "multi-catfish-mcrl-v014-independent-action-set-head"
V014_HEAD_CHECKPOINT_VERSION = 1


@dataclass(frozen=True)
class EEAxisV014HeadConfig:
    """Architecture and optimization choices for one independent head."""

    action_dim: int
    local_feature_dim: int
    global_feature_dim: int
    hidden_layers: tuple[int, ...]
    activation: str
    learning_rate: float
    kappa_bits: float
    beta: float

    def __post_init__(self) -> None:
        for name in ("action_dim", "local_feature_dim"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.global_feature_dim, bool)
            or not isinstance(self.global_feature_dim, int)
            or self.global_feature_dim < 0
        ):
            raise ValueError("global_feature_dim must be a nonnegative integer")
        if not self.hidden_layers or any(
            isinstance(width, bool) or not isinstance(width, int) or width < 1
            for width in self.hidden_layers
        ):
            raise ValueError("hidden_layers must contain positive integer widths")
        if self.activation not in {"tanh", "relu"}:
            raise ValueError("activation must be 'tanh' or 'relu'")
        for name in ("learning_rate", "kappa_bits"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
        if not np.isfinite(self.beta) or self.beta < 0.0:
            raise ValueError("beta must be finite and nonnegative")

    @property
    def state_dim(self) -> int:
        return self.local_feature_dim * self.action_dim + self.global_feature_dim


class V014ActionSetQNetwork(nn.Module):
    """Score every action with one permutation-equivariant local MLP."""

    def __init__(self, config: EEAxisV014HeadConfig) -> None:
        super().__init__()
        activation = nn.Tanh if config.activation == "tanh" else nn.ReLU
        input_width = 3 * config.local_feature_dim + config.global_feature_dim
        widths = (input_width, *config.hidden_layers, 1)
        layers: list[nn.Module] = []
        for left, right in zip(widths[:-2], widths[1:-1], strict=True):
            layers.extend((nn.Linear(left, right), activation()))
        layers.append(nn.Linear(widths[-2], widths[-1]))
        self.scorer = nn.Sequential(*layers)
        self.config = config

    def _features(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        if states.ndim != 2 or states.shape[1] != self.config.state_dim:
            raise ValueError(
                "V0.14 head states must have shape "
                f"(batch, {self.config.state_dim})"
            )
        if (
            masks.ndim != 2
            or masks.dtype != torch.bool
            or masks.shape != (states.shape[0], self.config.action_dim)
        ):
            raise ValueError(
                "V0.14 head masks must be Boolean shape "
                f"(batch, {self.config.action_dim})"
            )
        if not bool(torch.all(torch.any(masks, dim=1))):
            raise ValueError("every V0.14 head row needs a legal action")

        batch = states.shape[0]
        local_width = self.config.local_feature_dim * self.config.action_dim
        local = states[:, :local_width].reshape(
            batch, self.config.local_feature_dim, self.config.action_dim
        ).transpose(1, 2)
        globals_ = states[:, local_width:].unsqueeze(1).expand(
            -1, self.config.action_dim, -1
        )
        legal = masks.unsqueeze(2)
        count = legal.to(local.dtype).sum(dim=1, keepdim=True)
        masked = torch.where(legal, local, torch.zeros_like(local))
        mean = (masked.sum(dim=1, keepdim=True) / count).expand(
            -1, self.config.action_dim, -1
        )
        negative_inf = torch.full_like(local, -torch.inf)
        maximum = torch.where(legal, local, negative_inf).amax(
            dim=1, keepdim=True
        ).expand(-1, self.config.action_dim, -1)
        return torch.cat((local, globals_, mean, maximum), dim=2)

    def forward(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        return self.scorer(self._features(states, masks)).squeeze(2)


class EEAxisV014PairwiseLearner:
    """Own and optimize exactly one route-local Q head."""

    def __init__(
        self,
        config: EEAxisV014HeadConfig,
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
        self.q = V014ActionSetQNetwork(config).to(self.device)
        self.optimizer = optim.Adam(
            self.q.parameters(), lr=float(config.learning_rate)
        )

    def _arrays(
        self, batch: EEAxisPairBatch
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        batch.validate(
            state_dim=self.config.state_dim, action_dim=self.config.action_dim
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
        target = torch.tensor(
            np.asarray(batch.target_surplus_bits, dtype=np.float32)
            / float(self.config.kappa_bits),
            dtype=torch.float32,
            device=self.device,
        )
        masks = torch.tensor(
            np.asarray(batch.action_masks, dtype=np.bool_),
            dtype=torch.bool,
            device=self.device,
        )
        return states, reference, candidate, target, masks

    def _loss(
        self, batch: EEAxisPairBatch
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        states, reference, candidate, target, masks = self._arrays(batch)
        surface = self.q(states, masks)
        rows = torch.arange(states.shape[0], device=self.device)
        q_reference = surface[rows, reference]
        q_candidate = surface[rows, candidate]
        pair_mse = torch.mean((q_candidate - q_reference - target).square())
        gauge_mse = torch.mean(q_reference.square())
        loss = pair_mse + float(self.config.beta) * gauge_mse
        return loss, pair_mse, gauge_mse

    def measure(self, batch: EEAxisPairBatch) -> dict[str, float | int]:
        self.q.eval()
        with torch.no_grad():
            loss, pair_mse, gauge_mse = self._loss(batch)
        return {
            "batch_size": int(np.asarray(batch.states).shape[0]),
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    def update(self, batch: EEAxisPairBatch) -> dict[str, float | int]:
        self.q.train()
        loss, pair_mse, gauge_mse = self._loss(batch)
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=0)
        assert_finite_gradients(self.q.parameters(), objective=0)
        self.optimizer.step()
        assert_finite_parameters([self.q])
        return {
            "batch_size": int(np.asarray(batch.states).shape[0]),
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    def _surface_arrays(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        reference_actions: np.ndarray,
        target_surfaces_bits: np.ndarray,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        values = np.asarray(states, dtype=np.float32)
        mask_values = np.asarray(masks)
        references = np.asarray(reference_actions)
        targets = np.asarray(target_surfaces_bits, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != self.config.state_dim:
            raise ValueError(
                f"states must have shape (anchors, {self.config.state_dim})"
            )
        anchors = int(values.shape[0])
        if anchors < 1 or not np.all(np.isfinite(values)):
            raise ValueError("surface states must be nonempty and finite")
        if (
            mask_values.dtype != np.bool_
            or mask_values.shape != (anchors, self.config.action_dim)
        ):
            raise ValueError("surface masks must be Boolean and action-aligned")
        if (
            references.shape != (anchors,)
            or not np.issubdtype(references.dtype, np.integer)
            or np.any(references < 0)
            or np.any(references >= self.config.action_dim)
            or not np.all(mask_values[np.arange(anchors), references])
        ):
            raise ValueError("every surface reference action must be legal")
        if targets.shape != (anchors, self.config.action_dim) or not np.all(
            np.isfinite(targets)
        ):
            raise ValueError("target surfaces must be finite and action-aligned")
        comparisons = np.array(mask_values, copy=True)
        comparisons[np.arange(anchors), references] = False
        if not bool(np.any(comparisons)):
            raise ValueError("surface batch contains no non-reference comparison")
        return (
            torch.tensor(values, dtype=torch.float32, device=self.device),
            torch.tensor(mask_values, dtype=torch.bool, device=self.device),
            torch.tensor(references, dtype=torch.int64, device=self.device),
            torch.tensor(
                targets / float(self.config.kappa_bits),
                dtype=torch.float32,
                device=self.device,
            ),
            torch.tensor(comparisons, dtype=torch.bool, device=self.device),
        )

    def _surface_loss(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        reference_actions: np.ndarray,
        target_surfaces_bits: np.ndarray,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, int]:
        state_t, mask_t, reference_t, target_t, comparisons = self._surface_arrays(
            states, masks, reference_actions, target_surfaces_bits
        )
        surface = self.q(state_t, mask_t)
        rows = torch.arange(state_t.shape[0], device=self.device)
        q_reference = surface[rows, reference_t]
        target_reference = target_t[rows, reference_t]
        residual = (
            surface
            - q_reference[:, None]
            - (target_t - target_reference[:, None])
        )
        pair_mse = torch.mean(residual[comparisons].square())
        # Repeat the gauge once per comparison, exactly as the expanded
        # EEAxisPairBatch representation does.
        gauge_mse = torch.mean(
            q_reference[:, None].expand_as(surface)[comparisons].square()
        )
        loss = pair_mse + float(self.config.beta) * gauge_mse
        return loss, pair_mse, gauge_mse, int(torch.count_nonzero(comparisons))

    def measure_surfaces(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        reference_actions: np.ndarray,
        target_surfaces_bits: np.ndarray,
    ) -> dict[str, float | int]:
        """Measure the expanded-pair objective while scoring each anchor once."""

        self.q.eval()
        with torch.no_grad():
            loss, pair_mse, gauge_mse, comparisons = self._surface_loss(
                states, masks, reference_actions, target_surfaces_bits
            )
        return {
            "batch_size": comparisons,
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    def update_surfaces(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        reference_actions: np.ndarray,
        target_surfaces_bits: np.ndarray,
    ) -> dict[str, float | int]:
        """Update from compact complete surfaces without repeating states."""

        self.q.train()
        loss, pair_mse, gauge_mse, comparisons = self._surface_loss(
            states, masks, reference_actions, target_surfaces_bits
        )
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=0)
        assert_finite_gradients(self.q.parameters(), objective=0)
        self.optimizer.step()
        assert_finite_parameters([self.q])
        return {
            "batch_size": comparisons,
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    def q_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        values = np.asarray(states, dtype=np.float32)
        mask_values = np.asarray(masks)
        if values.ndim != 2 or values.shape[1] != self.config.state_dim:
            raise ValueError(
                f"states must have shape (batch, {self.config.state_dim})"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("states must be finite")
        if (
            mask_values.dtype != np.bool_
            or mask_values.shape != (values.shape[0], self.config.action_dim)
        ):
            raise ValueError(
                "masks must be Boolean and align with states/action_dim"
            )
        self.q.eval()
        with torch.no_grad():
            return self.q(
                torch.tensor(values, dtype=torch.float32, device=self.device),
                torch.tensor(mask_values, dtype=torch.bool, device=self.device),
            ).cpu().numpy()

    def select_greedy_actions(
        self, states: np.ndarray, masks: np.ndarray
    ) -> np.ndarray:
        mask_values = np.asarray(masks)
        values = self.q_values(states, mask_values)
        actions = np.full(values.shape[0], NO_OP_ACTION, dtype=np.int64)
        eligible = np.any(mask_values, axis=1)
        actions[eligible] = np.argmax(
            np.where(mask_values[eligible], values[eligible], -np.inf), axis=1
        )
        return actions

    def checkpoint_state(self, *, update_count: int) -> dict[str, Any]:
        if (
            isinstance(update_count, bool)
            or not isinstance(update_count, int)
            or update_count < 0
        ):
            raise ValueError("update_count must be a nonnegative integer")
        return {
            "algorithm": V014_HEAD_ALGORITHM,
            "format_version": V014_HEAD_CHECKPOINT_VERSION,
            "config": asdict(self.config),
            "train_seed": self.train_seed,
            "update_count": update_count,
            "q": self.q.state_dict(),
            "optimizer": self.optimizer.state_dict(),
        }

    def load_checkpoint_state(self, payload: Mapping[str, Any]) -> int:
        if payload.get("algorithm") != V014_HEAD_ALGORITHM:
            raise MCRLContractError("checkpoint is not a V0.14 head checkpoint")
        if payload.get("format_version") != V014_HEAD_CHECKPOINT_VERSION:
            raise MCRLContractError("unsupported V0.14 head checkpoint version")
        if payload.get("config") != asdict(self.config):
            raise MCRLContractError("V0.14 head checkpoint config mismatch")
        if payload.get("train_seed") != self.train_seed:
            raise MCRLContractError("V0.14 head checkpoint train_seed mismatch")
        update_count = payload.get("update_count")
        if (
            isinstance(update_count, bool)
            or not isinstance(update_count, int)
            or update_count < 0
        ):
            raise MCRLContractError("invalid V0.14 head checkpoint update count")
        try:
            self.q.load_state_dict(payload["q"])
            self.optimizer.load_state_dict(payload["optimizer"])
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            raise MCRLContractError("malformed V0.14 head checkpoint") from error
        assert_finite_parameters([self.q])
        return update_count


__all__ = [
    "EEAxisV014HeadConfig",
    "EEAxisV014PairwiseLearner",
    "V014ActionSetQNetwork",
    "V014_HEAD_ALGORITHM",
    "V014_HEAD_CHECKPOINT_VERSION",
]
