"""Offline frozen-Main action probe for E1 sample-burden diagnosis.

The probe is discarded after audit.  It is not a Q function, never enters the
deployment score, and never updates Main or a Catfish learner.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Sequence

import numpy as np
import torch
import torch.nn.functional as functional
import torch.optim as optim

from ..errors import MCRLContractError
from .ee_axis_e1_statistics import (
    ClusterBootstrapInterval,
    bootstrap_relative_error_reduction,
)
from .finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from .q_network import DQNNetwork


E1_REFERENCE_PROBE_SCHEMA = "multi-catfish-mcrl-v03-e1-reference-action-probe-v1"
E1_REFERENCE_PROBE_HIDDEN_LAYERS = (100, 50, 50)


class E1ReferenceProbeError(MCRLContractError):
    """Reference-action probe data or configuration violate E1."""


@dataclass(frozen=True)
class E1ReferenceProbeConfig:
    state_dim: int
    action_dim: int
    learning_rate: float = 1e-3
    updates: int = 1000
    activation: str = "tanh"
    bootstrap_replications: int = 2000
    bootstrap_confidence: float = 0.95

    def verify(self) -> None:
        if type(self.state_dim) is not int or self.state_dim < 1:
            raise E1ReferenceProbeError("state_dim must be a positive integer")
        if type(self.action_dim) is not int or self.action_dim < 2:
            raise E1ReferenceProbeError("action_dim must be an integer >= 2")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0.0:
            raise E1ReferenceProbeError("learning_rate must be finite and positive")
        if type(self.updates) is not int or self.updates < 1:
            raise E1ReferenceProbeError("updates must be a positive integer")
        if self.activation not in ("tanh", "relu"):
            raise E1ReferenceProbeError("activation must be tanh or relu")
        if type(self.bootstrap_replications) is not int or self.bootstrap_replications < 100:
            raise E1ReferenceProbeError("bootstrap_replications must be >= 100")
        if not math.isfinite(self.bootstrap_confidence) or not 0.5 < self.bootstrap_confidence < 1.0:
            raise E1ReferenceProbeError("bootstrap_confidence must lie in (0.5,1)")


@dataclass(frozen=True)
class E1ReferenceProbeResult:
    train_seed: int
    train_rows: int
    test_rows: int
    initial_cross_entropy: float
    final_cross_entropy: float
    probe_top1_accuracy: float
    action_prior_top1_accuracy: float
    relative_error_reduction: float
    relative_error_reduction_interval: ClusterBootstrapInterval
    schema: str = E1_REFERENCE_PROBE_SCHEMA

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["relative_error_reduction_interval"] = (
            self.relative_error_reduction_interval.as_dict()
        )
        return payload


def _classification_data(
    states: np.ndarray,
    masks: np.ndarray,
    actions: np.ndarray,
    *,
    state_dim: int,
    action_dim: int,
    label: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    state_values = np.asarray(states, dtype=np.float32)
    mask_values = np.asarray(masks)
    action_values = np.asarray(actions)
    if state_values.ndim != 2 or state_values.shape[1] != state_dim or state_values.shape[0] < 1:
        raise E1ReferenceProbeError(
            f"{label} states must be nonempty shape (rows,{state_dim})"
        )
    if not np.all(np.isfinite(state_values)):
        raise E1ReferenceProbeError(f"{label} states must be finite")
    if mask_values.shape != (state_values.shape[0], action_dim) or mask_values.dtype != np.bool_:
        raise E1ReferenceProbeError(
            f"{label} masks must be boolean shape (rows,{action_dim})"
        )
    if np.any(~np.any(mask_values, axis=1)):
        raise E1ReferenceProbeError(f"{label} probe rows may not be all-dark")
    if action_values.shape != (state_values.shape[0],) or not np.issubdtype(
        action_values.dtype, np.integer
    ):
        raise E1ReferenceProbeError(f"{label} actions must be a row-aligned integer vector")
    if np.any(action_values < 0) or np.any(action_values >= action_dim):
        raise E1ReferenceProbeError(f"{label} action lies outside action_dim")
    action_values = action_values.astype(np.int64, copy=False)
    if not np.all(mask_values[np.arange(action_values.size), action_values]):
        raise E1ReferenceProbeError(f"{label} reference action violates its mask")
    return state_values, mask_values, action_values


def run_reference_action_probe(
    *,
    train_states: np.ndarray,
    train_masks: np.ndarray,
    train_reference_actions: np.ndarray,
    test_states: np.ndarray,
    test_masks: np.ndarray,
    test_reference_actions: np.ndarray,
    test_cluster_ids: Sequence[str] | np.ndarray,
    config: E1ReferenceProbeConfig,
    train_seed: int,
    bootstrap_seed: int,
    device: str = "cpu",
) -> E1ReferenceProbeResult:
    """Fit one fixed-budget masked classifier and evaluate it once on test."""

    if not isinstance(config, E1ReferenceProbeConfig):
        raise E1ReferenceProbeError("config must be E1ReferenceProbeConfig")
    config.verify()
    if type(train_seed) is not int or train_seed < 0:
        raise E1ReferenceProbeError("train_seed must be a nonnegative integer")
    train_x, train_m, train_y = _classification_data(
        train_states,
        train_masks,
        train_reference_actions,
        state_dim=config.state_dim,
        action_dim=config.action_dim,
        label="train",
    )
    test_x, test_m, test_y = _classification_data(
        test_states,
        test_masks,
        test_reference_actions,
        state_dim=config.state_dim,
        action_dim=config.action_dim,
        label="test",
    )

    target_device = torch.device(device)
    torch.manual_seed(train_seed)
    network = DQNNetwork(
        config.state_dim,
        config.action_dim,
        E1_REFERENCE_PROBE_HIDDEN_LAYERS,
        config.activation,
    ).to(target_device)
    optimizer = optim.Adam(network.parameters(), lr=config.learning_rate)
    tensor_x = torch.tensor(train_x, dtype=torch.float32, device=target_device)
    tensor_m = torch.tensor(train_m, dtype=torch.bool, device=target_device)
    tensor_y = torch.tensor(train_y, dtype=torch.int64, device=target_device)

    def loss_value() -> torch.Tensor:
        logits = network(tensor_x)
        masked = logits.masked_fill(~tensor_m, torch.finfo(logits.dtype).min)
        return functional.cross_entropy(masked, tensor_y)

    with torch.no_grad():
        initial_loss = float(loss_value().detach().cpu())
    for _update in range(config.updates):
        loss = loss_value()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective="E1-reference-action-probe")
        assert_finite_gradients(
            network.parameters(), objective="E1-reference-action-probe"
        )
        optimizer.step()
        assert_finite_parameters([network])
    with torch.no_grad():
        final_loss = float(loss_value().detach().cpu())
        test_tensor = torch.tensor(test_x, dtype=torch.float32, device=target_device)
        test_mask_tensor = torch.tensor(test_m, dtype=torch.bool, device=target_device)
        logits = network(test_tensor).masked_fill(
            ~test_mask_tensor, torch.finfo(torch.float32).min
        )
        predictions = torch.argmax(logits, dim=1).cpu().numpy()

    prior_counts = np.bincount(train_y, minlength=config.action_dim).astype(np.float64)
    prior_scores = np.broadcast_to(prior_counts, test_m.shape)
    prior_predictions = np.argmax(np.where(test_m, prior_scores, -np.inf), axis=1)
    probe_correct = np.asarray(predictions == test_y, dtype=np.bool_)
    baseline_correct = np.asarray(prior_predictions == test_y, dtype=np.bool_)
    interval = bootstrap_relative_error_reduction(
        probe_correct=probe_correct,
        baseline_correct=baseline_correct,
        cluster_ids=test_cluster_ids,
        replications=config.bootstrap_replications,
        confidence=config.bootstrap_confidence,
        bootstrap_seed=bootstrap_seed,
    )
    return E1ReferenceProbeResult(
        train_seed=train_seed,
        train_rows=int(train_x.shape[0]),
        test_rows=int(test_x.shape[0]),
        initial_cross_entropy=initial_loss,
        final_cross_entropy=final_loss,
        probe_top1_accuracy=float(np.mean(probe_correct)),
        action_prior_top1_accuracy=float(np.mean(baseline_correct)),
        relative_error_reduction=float(interval.estimate),
        relative_error_reduction_interval=interval,
    )


__all__ = [
    "E1_REFERENCE_PROBE_HIDDEN_LAYERS",
    "E1_REFERENCE_PROBE_SCHEMA",
    "E1ReferenceProbeConfig",
    "E1ReferenceProbeError",
    "E1ReferenceProbeResult",
    "run_reference_action_probe",
]

