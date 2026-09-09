"""Bounded Q2-only learners for the V0.4 parallel C2 design screen.

The physical C2 source is shared.  These learners differ only in the sealed
continuation lineage and, for P2, the residual penalty.  Q1 and Q3 are not
owned by this module and cannot receive gradients here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import torch
import torch.nn.functional as functional
import torch.optim as optim

from ..errors import MCRLContractError
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from .ee_axis_action_shared_meanmax import (
    EEAxisMaskedMeanMaxConfig,
    MaskedMeanMaxQNetwork,
)
from .ee_axis_pairwise import EEAxisPairBatch


C2_PARALLEL_ALGORITHM = "multi-catfish-mcrl-ee-axis-v04-c2-parallel"
C2_PARALLEL_CHECKPOINT_VERSION = 1
C2_MAIN_VALUE = "C2-P0-MAIN-VALUE"
C2_Q13_VALUE = "C2-P1-Q13-VALUE"
C2_Q13_HUBER = "C2-P2-Q13-HUBER"
C2_CANDIDATE_IDS = (C2_MAIN_VALUE, C2_Q13_VALUE, C2_Q13_HUBER)


@dataclass(frozen=True)
class C2ParallelCandidateSpec:
    """Pre-outcome identity of one bounded C2 learner candidate."""

    candidate_id: str
    continuation: str
    residual_loss: str
    huber_delta: float | None = None

    def __post_init__(self) -> None:
        expected = {
            C2_MAIN_VALUE: ("frozen-main", "mse", None),
            C2_Q13_VALUE: ("matched-frozen-q1-plus-q3", "mse", None),
            C2_Q13_HUBER: ("matched-frozen-q1-plus-q3", "huber", 1.0),
        }
        if self.candidate_id not in expected:
            raise ValueError("unknown V0.4 C2 candidate")
        if (self.continuation, self.residual_loss, self.huber_delta) != expected[
            self.candidate_id
        ]:
            raise ValueError("C2 candidate fields disagree with the frozen preregistration")


def frozen_c2_candidate_specs() -> tuple[C2ParallelCandidateSpec, ...]:
    """Return the three candidates in the fixed simplicity order."""

    return (
        C2ParallelCandidateSpec(C2_MAIN_VALUE, "frozen-main", "mse"),
        C2ParallelCandidateSpec(
            C2_Q13_VALUE,
            "matched-frozen-q1-plus-q3",
            "mse",
        ),
        C2ParallelCandidateSpec(
            C2_Q13_HUBER,
            "matched-frozen-q1-plus-q3",
            "huber",
            1.0,
        ),
    )


class EEAxisV04C2Trainer:
    """Exactly one trainable Q2 head for one preregistered candidate arm."""

    def __init__(
        self,
        config: EEAxisMaskedMeanMaxConfig,
        *,
        candidate: C2ParallelCandidateSpec,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        if not isinstance(candidate, C2ParallelCandidateSpec):
            raise TypeError("candidate must be a C2ParallelCandidateSpec")
        if isinstance(train_seed, bool) or not isinstance(train_seed, int):
            raise TypeError("train_seed must be an integer")
        self.config = config
        self.candidate = candidate
        self.train_seed = train_seed
        self.device = torch.device(device)
        torch.manual_seed(train_seed)
        self.q2 = MaskedMeanMaxQNetwork(config).to(self.device)
        self.optimizer = optim.Adam(self.q2.parameters(), lr=config.learning_rate)

    @staticmethod
    def _mask_array(
        masks: np.ndarray,
        *,
        batch: int,
        action_dim: int,
    ) -> np.ndarray:
        values = np.asarray(masks)
        if values.dtype != np.bool_ or values.shape != (batch, action_dim):
            raise ValueError(
                f"masks must be Boolean with shape ({batch}, {action_dim})"
            )
        if not np.all(np.any(values, axis=1)):
            raise ValueError("masks must admit at least one action per row")
        return values

    def q2_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        values = np.asarray(states, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] != self.config.state_dim:
            raise ValueError(
                f"states must have shape (batch, {self.config.state_dim})"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError("states must be finite")
        mask_values = self._mask_array(
            masks,
            batch=values.shape[0],
            action_dim=self.config.action_dim,
        )
        with torch.no_grad():
            state_tensor = torch.tensor(
                values,
                dtype=torch.float32,
                device=self.device,
            )
            mask_tensor = torch.tensor(
                mask_values,
                dtype=torch.bool,
                device=self.device,
            )
            return self.q2(state_tensor, mask_tensor).cpu().numpy()

    def update(self, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        """Apply one Q2-only update in normalized surplus units."""

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
        surface = self.q2(states, masks)
        q_reference = surface.gather(1, reference[:, None]).squeeze(1)
        q_candidate = surface.gather(1, candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - target
        pair_mse = torch.mean(residual.square())
        if self.candidate.residual_loss == "mse":
            pair_objective = pair_mse
        else:
            # Twice PyTorch's standard Huber keeps the local quadratic term
            # equal to r^2, matching the preregistered P1 MSE curvature.
            pair_objective = 2.0 * functional.huber_loss(
                residual,
                torch.zeros_like(residual),
                reduction="mean",
                delta=float(self.candidate.huber_delta),
            )
        gauge_mse = torch.mean(q_reference.square())
        loss = float(self.config.loss_weights[1]) * (
            pair_objective + float(self.config.beta) * gauge_mse
        )
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=2)
        assert_finite_gradients(self.q2.parameters(), objective=2)
        self.optimizer.step()
        assert_finite_parameters((self.q2,))
        return {
            "candidate_id": self.candidate.candidate_id,
            "batch_size": int(states.shape[0]),
            "loss": float(loss.detach().cpu()),
            "pair_objective": float(pair_objective.detach().cpu()),
            "pair_mse_diagnostic": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
        }

    def checkpoint_state(self, *, update_count: int) -> dict[str, Any]:
        if (
            isinstance(update_count, bool)
            or not isinstance(update_count, int)
            or update_count < 0
        ):
            raise ValueError("update_count must be a nonnegative integer")
        return {
            "format_version": C2_PARALLEL_CHECKPOINT_VERSION,
            "algorithm": C2_PARALLEL_ALGORITHM,
            "update_count": update_count,
            "train_seed": self.train_seed,
            "candidate": asdict(self.candidate),
            "config": asdict(self.config),
            "q2_network": self.q2.state_dict(),
            "q2_optimizer": self.optimizer.state_dict(),
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if state.get("algorithm") != C2_PARALLEL_ALGORITHM:
            raise MCRLContractError("checkpoint is not a V0.4 parallel C2 checkpoint")
        if state.get("format_version") != C2_PARALLEL_CHECKPOINT_VERSION:
            raise MCRLContractError("unsupported V0.4 parallel C2 checkpoint version")
        if state.get("train_seed") != self.train_seed:
            raise MCRLContractError("V0.4 parallel C2 train_seed mismatch")
        if state.get("candidate") != asdict(self.candidate):
            raise MCRLContractError("V0.4 parallel C2 candidate mismatch")
        if state.get("config") != asdict(self.config):
            raise MCRLContractError("V0.4 parallel C2 config mismatch")
        network = state.get("q2_network")
        optimizer = state.get("q2_optimizer")
        if not isinstance(network, Mapping) or not isinstance(optimizer, Mapping):
            raise MCRLContractError("V0.4 parallel C2 checkpoint payload is malformed")
        update_count = state.get("update_count")
        if (
            isinstance(update_count, bool)
            or not isinstance(update_count, int)
            or update_count < 0
        ):
            raise MCRLContractError("invalid V0.4 parallel C2 update_count")
        self.q2.load_state_dict(network, strict=True)
        self.optimizer.load_state_dict(optimizer)
        assert_finite_parameters((self.q2,))
        return update_count


__all__ = [
    "C2_CANDIDATE_IDS",
    "C2_MAIN_VALUE",
    "C2_PARALLEL_ALGORITHM",
    "C2_PARALLEL_CHECKPOINT_VERSION",
    "C2_Q13_HUBER",
    "C2_Q13_VALUE",
    "C2ParallelCandidateSpec",
    "EEAxisV04C2Trainer",
    "frozen_c2_candidate_specs",
]
