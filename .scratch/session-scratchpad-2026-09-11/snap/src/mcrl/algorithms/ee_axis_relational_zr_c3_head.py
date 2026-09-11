"""One victim-relational Q3 scorer for the V0.18 design seam.

This module is deliberately pure.  It consumes an already authenticated
predecision relational observation and returns one reference-centred Q3
surface.  It owns no simulator, action selection, source labels, optimizer,
or other Q head.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import torch
import torch.nn as nn


RELATIONAL_ZR_C3_HEAD_ALGORITHM = "multi-catfish-mcrl-v018-relational-zr-c3-head"
RELATIONAL_ZR_C3_HEAD_VERSION = 1


@dataclass(frozen=True)
class RelationalZRC3NetworkConfig:
    """Frozen tensor widths and output normalization for one Q3 module."""

    action_dim: int
    action_context_dim: int
    victim_token_dim: int
    hidden_layers: tuple[int, ...]
    activation: str
    kappa_bits: float

    def __post_init__(self) -> None:
        for name in ("action_dim", "action_context_dim", "victim_token_dim"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if any(
            isinstance(width, bool) or not isinstance(width, int) or width < 1
            for width in self.hidden_layers
        ):
            raise ValueError("hidden_layers must contain positive integer widths")
        if self.activation not in {"tanh", "relu"}:
            raise ValueError("activation must be 'tanh' or 'relu'")
        if not math.isfinite(float(self.kappa_bits)) or float(self.kappa_bits) <= 0.0:
            raise ValueError("kappa_bits must be finite and positive")


class RelationalZRC3QNetwork(nn.Module):
    """Score masked victims with one shared MLP and sum them per action."""

    def __init__(self, config: RelationalZRC3NetworkConfig) -> None:
        super().__init__()
        activation = nn.Tanh if config.activation == "tanh" else nn.ReLU
        widths = (
            config.action_context_dim + config.victim_token_dim,
            *config.hidden_layers,
            1,
        )
        layers: list[nn.Module] = []
        for left, right in zip(widths[:-2], widths[1:-1], strict=True):
            layers.extend((nn.Linear(left, right), activation()))
        layers.append(nn.Linear(widths[-2], widths[-1]))
        self.victim_scorer = nn.Sequential(*layers)
        self.config = config

    def _validate(
        self,
        action_context: torch.Tensor,
        victim_tokens: torch.Tensor,
        action_mask: torch.Tensor,
        victim_mask: torch.Tensor,
        positive_credit_compatible: torch.Tensor,
        reference_actions: torch.Tensor,
    ) -> tuple[int, int, int]:
        values = (
            action_context,
            victim_tokens,
            action_mask,
            victim_mask,
            positive_credit_compatible,
            reference_actions,
        )
        if not all(isinstance(value, torch.Tensor) for value in values):
            raise TypeError("relational Q3 inputs must be torch tensors")
        devices = {value.device for value in values}
        if len(devices) != 1:
            raise ValueError("relational Q3 inputs must share one device")
        if action_context.ndim != 3:
            raise ValueError("action_context must have shape (N,A,C)")
        batch, actions, context_width = action_context.shape
        if (
            batch < 1
            or actions != self.config.action_dim
            or context_width != self.config.action_context_dim
        ):
            raise ValueError("action_context shape disagrees with the Q3 config")
        if victim_tokens.ndim != 4:
            raise ValueError("victim_tokens must have shape (N,A,V,T)")
        victims = int(victim_tokens.shape[2])
        if victims < 1 or victim_tokens.shape != (
            batch,
            actions,
            victims,
            self.config.victim_token_dim,
        ):
            raise ValueError("victim_tokens shape disagrees with the Q3 config")
        if action_mask.dtype != torch.bool or action_mask.shape != (batch, actions):
            raise ValueError("action_mask must be Boolean shape (N,A)")
        if victim_mask.dtype != torch.bool or victim_mask.shape != (
            batch,
            actions,
            victims,
        ):
            raise ValueError("victim_mask must be Boolean shape (N,A,V)")
        if (
            positive_credit_compatible.dtype != torch.bool
            or positive_credit_compatible.shape != (batch, actions)
        ):
            raise ValueError(
                "positive_credit_compatible must be Boolean shape (N,A)"
            )
        if reference_actions.dtype != torch.int64 or reference_actions.shape != (batch,):
            raise ValueError("reference_actions must be int64 shape (N,)")
        if not action_context.is_floating_point() or not victim_tokens.is_floating_point():
            raise ValueError("relational Q3 features must be floating point")
        if not bool(torch.isfinite(action_context).all()) or not bool(
            torch.isfinite(victim_tokens).all()
        ):
            raise ValueError("relational Q3 features must be finite")
        if not bool(torch.any(action_mask, dim=1).all()):
            raise ValueError("each relational Q3 row needs a legal action")
        if bool(torch.any(victim_mask & ~action_mask.unsqueeze(2))):
            raise ValueError("victim_mask cannot widen the native action mask")
        if bool(torch.any(positive_credit_compatible & ~action_mask)):
            raise ValueError("compatibility cannot widen the native action mask")
        rows = torch.arange(batch, device=reference_actions.device)
        if bool(torch.any(reference_actions < 0)) or bool(
            torch.any(reference_actions >= actions)
        ) or not bool(action_mask[rows, reference_actions].all()):
            raise ValueError("every reference action must be legal")
        return batch, actions, victims

    def forward(
        self,
        action_context: torch.Tensor,
        victim_tokens: torch.Tensor,
        action_mask: torch.Tensor,
        victim_mask: torch.Tensor,
        positive_credit_compatible: torch.Tensor,
        reference_actions: torch.Tensor,
    ) -> torch.Tensor:
        batch, actions, _victims = self._validate(
            action_context,
            victim_tokens,
            action_mask,
            victim_mask,
            positive_credit_compatible,
            reference_actions,
        )
        selected = torch.nonzero(victim_mask, as_tuple=False)
        if selected.shape[0] == 0:
            aggregate = action_context.new_zeros((batch, actions))
        else:
            row_index = selected[:, 0]
            action_index = selected[:, 1]
            victim_index = selected[:, 2]
            features = torch.cat(
                (
                    action_context[row_index, action_index],
                    victim_tokens[row_index, action_index, victim_index],
                ),
                dim=1,
            )
            predicted = self.victim_scorer(features).squeeze(1)
            zero = torch.zeros_like(predicted)
            compatible = positive_credit_compatible[
                row_index, action_index
            ].to(dtype=predicted.dtype)
            contribution = torch.minimum(predicted, zero) + compatible * torch.maximum(
                predicted, zero
            )
            flat_index = row_index * actions + action_index
            aggregate = contribution.new_zeros(batch * actions).scatter_add(
                0, flat_index, contribution
            ).reshape(batch, actions)
        rows = torch.arange(batch, device=reference_actions.device)
        centred = (
            aggregate - aggregate[rows, reference_actions].unsqueeze(1)
        ) / float(self.config.kappa_bits)
        return torch.where(action_mask, centred, torch.zeros_like(centred))


__all__ = [
    "RELATIONAL_ZR_C3_HEAD_ALGORITHM",
    "RELATIONAL_ZR_C3_HEAD_VERSION",
    "RelationalZRC3NetworkConfig",
    "RelationalZRC3QNetwork",
]
