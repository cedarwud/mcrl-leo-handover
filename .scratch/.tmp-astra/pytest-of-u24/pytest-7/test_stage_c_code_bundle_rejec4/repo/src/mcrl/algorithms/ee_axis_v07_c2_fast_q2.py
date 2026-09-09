"""Development-only Q2 fit for rapid V0.7 C2 falsification screens.

This module is intentionally smaller than the evidence-grade V0.7 trainer.
It is a CPU-only, Q2-only instrument for answering an engineering question
quickly: can a tiny, already materialised pair batch be fitted at all?  It
does not select anchors, run a simulator, create a source receipt, choose a
lineage, or establish efficacy.  Its outputs must not be used as EE evidence.

The learner still preserves the important deployment plumbing used by the
fresh Q2: the signed-motion V0.7 state schema, explicit Boolean native masks,
the action-shared masked mean/max network, and legal-set centering.  Unlike
the evidence trainer, a fit may contain any positive number of rows and each
row may expose only a partial legal action panel.  A fit is a deterministic
full-batch Adam loop with a hard cap of 100 updates.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
import hashlib
import json
from typing import Any

import numpy as np
import torch
import torch.optim as optim

from ..errors import MCRLContractError
from ..runtime.finiteness import (
    assert_finite_gradients,
    assert_finite_loss,
    assert_finite_parameters,
)
from ..runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)
from .ee_axis_action_shared_meanmax import (
    EEAxisMaskedMeanMaxConfig,
    MaskedMeanMaxQNetwork,
)
from .ee_axis_pairwise import EEAxisPairBatch
from .ee_axis_v07_c2_focal_next import V07_C2_KAPPA_BITS


FAST_Q2_ALGORITHM = "multi-catfish-mcrl-ee-axis-v07-c2-fast-q2-development"
FAST_Q2_CLAIM_CEILING = "development-only-not-efficacy-evidence"
FAST_Q2_ACTION_DIM = 28
FAST_Q2_MAX_UPDATES = 100
FAST_Q2_DEFAULT_UPDATES = 10
FAST_Q2_TORCH_NUM_THREADS = 1
FAST_Q2_LEARNING_RATE = 0.001
FAST_Q2_BETA = 0.001
# ``kappa`` is a physical bits/J scale, not a learning rate.  Keep the
# already-frozen V0.7 normalizer so rapid fits remain in the same target units.
FAST_Q2_KAPPA_BITS = V07_C2_KAPPA_BITS
FAST_Q2_ADAM = {
    "lr": FAST_Q2_LEARNING_RATE,
    "betas": (0.9, 0.999),
    "eps": 1e-8,
    "weight_decay": 0.0,
    "amsgrad": False,
}


def fast_q2_config(
    *,
    learning_rate: float = FAST_Q2_LEARNING_RATE,
    kappa_bits: float = FAST_Q2_KAPPA_BITS,
    beta: float = FAST_Q2_BETA,
) -> EEAxisMaskedMeanMaxConfig:
    """Return the bounded action-shared configuration used by :class:`FreshQ2`.

    The optional arguments are useful for a local numerical probe, but the
    defaults are fixed to the V0.7 rapid-screen values.  This class never
    constructs Q1 or Q3.
    """

    return EEAxisMaskedMeanMaxConfig(
        state_dim=V07_C2_Q2_STATE_DIM,
        action_dim=FAST_Q2_ACTION_DIM,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=float(learning_rate),
        kappa_bits=float(kappa_bits),
        beta=float(beta),
        loss_weights=(1.0, 1.0, 1.0),
    )


def _state_dict_sha256(state: Mapping[str, Any]) -> str:
    """Hash parameter tensors in stable name/dtype/shape/value order."""

    digest = hashlib.sha256()
    for name, value in sorted(state.items(), key=lambda item: item[0]):
        if not isinstance(name, str) or not isinstance(value, torch.Tensor):
            raise MCRLContractError("fast Q2 state_dict is malformed")
        array = np.ascontiguousarray(value.detach().cpu().numpy())
        digest.update(name.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(
            json.dumps(list(array.shape), separators=(",", ":")).encode("ascii")
        )
        digest.update(b"\0")
        digest.update(array.tobytes())
    return digest.hexdigest()


def q2_parameter_sha256(network: MaskedMeanMaxQNetwork) -> str:
    """Return a reproducible digest of one fresh Q2's parameters."""

    return _state_dict_sha256(network.state_dict())


def center_legal_surface(raw: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
    """Center each nonempty legal action set and zero all illegal slots."""

    if raw.ndim != 2 or masks.ndim != 2 or raw.shape != masks.shape:
        raise ValueError("raw Q2 values and masks must be matching matrices")
    if masks.dtype is not torch.bool:
        raise ValueError("Q2 masks must be Boolean")
    count = masks.sum(dim=1, keepdim=True)
    if not bool(torch.all(count > 0)):
        raise ValueError("centered Q2 rows must admit at least one legal action")
    legal = masks.to(dtype=raw.dtype)
    mean = (raw * legal).sum(dim=1, keepdim=True) / count.to(dtype=raw.dtype)
    return torch.where(masks, raw - mean, torch.zeros_like(raw))


def _batch_sha256(batch: EEAxisPairBatch) -> str:
    """Hash the exact small batch so accidental cross-fit drift is visible."""

    digest = hashlib.sha256()
    arrays = (
        ("states", np.asarray(batch.states, dtype=np.float32)),
        ("reference_actions", np.asarray(batch.reference_actions, dtype=np.int64)),
        ("candidate_actions", np.asarray(batch.candidate_actions, dtype=np.int64)),
        ("action_masks", np.asarray(batch.action_masks, dtype=np.bool_)),
        ("target_surplus_bits", np.asarray(batch.target_surplus_bits, dtype=np.float64)),
    )
    for name, array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(name.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(contiguous.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(
            json.dumps(list(contiguous.shape), separators=(",", ":")).encode("ascii")
        )
        digest.update(b"\0")
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


def _exact_updates(value: object, *, field: str = "updates") -> int:
    if type(value) is not int or not 1 <= value <= FAST_Q2_MAX_UPDATES:
        raise ValueError(f"{field} must be an integer in [1,{FAST_Q2_MAX_UPDATES}]")
    return value


class FreshQ2:
    """One deterministic, development-only Q2 for a tiny pair batch.

    The object deliberately has only ``q2`` and one optimizer.  ``fit`` uses
    the supplied rows as one full batch for every update; it does not shuffle,
    sample, bootstrap, or create a replay buffer.  This makes a failed
    candidate cheap to discard and a repeated candidate exactly reproducible.
    """

    state_schema = V07_C2_Q2_STATE_SCHEMA
    state_schema_sha256 = V07_C2_Q2_STATE_SCHEMA_SHA256
    algorithm = FAST_Q2_ALGORITHM
    claim_ceiling = FAST_Q2_CLAIM_CEILING

    def __init__(
        self,
        *,
        train_seed: int = 0,
        device: str = "cpu",
        learning_rate: float = FAST_Q2_LEARNING_RATE,
        kappa_bits: float = FAST_Q2_KAPPA_BITS,
        beta: float = FAST_Q2_BETA,
    ) -> None:
        if type(train_seed) is not int:
            raise TypeError("train_seed must be an integer")
        if device != "cpu":
            raise ValueError("development Q2 permits only the deterministic CPU path")
        self.train_seed = train_seed
        self.device = torch.device("cpu")
        self.config = fast_q2_config(
            learning_rate=learning_rate,
            kappa_bits=kappa_bits,
            beta=beta,
        )
        torch.use_deterministic_algorithms(True)
        torch.set_num_threads(FAST_Q2_TORCH_NUM_THREADS)
        torch.manual_seed(train_seed)
        self.q2 = MaskedMeanMaxQNetwork(self.config).to(self.device)
        self.optimizer = optim.Adam(
            self.q2.parameters(),
            lr=self.config.learning_rate,
            betas=FAST_Q2_ADAM["betas"],
            eps=FAST_Q2_ADAM["eps"],
            weight_decay=FAST_Q2_ADAM["weight_decay"],
            amsgrad=FAST_Q2_ADAM["amsgrad"],
        )
        self.update_count = 0
        self._batch_digest: str | None = None
        self.last_fit_diagnostics: dict[str, float | int | str] | None = None
        self.update0_parameter_sha256 = q2_parameter_sha256(self.q2)

    @staticmethod
    def _validate_batch(batch: EEAxisPairBatch) -> str:
        if not isinstance(batch, EEAxisPairBatch):
            raise TypeError("fast Q2 fit requires an EEAxisPairBatch")
        # Give the rapid-screen caller a useful failure before the generic
        # pair validator reports that the stored reference/candidate cannot be
        # gathered from an empty panel.
        raw_masks = np.asarray(batch.action_masks)
        if (
            raw_masks.ndim == 2
            and raw_masks.shape[1] == FAST_Q2_ACTION_DIM
            and raw_masks.dtype == np.bool_
            and raw_masks.shape[0] > 0
            and not np.all(np.any(raw_masks, axis=1))
        ):
            raise ValueError("fast Q2 fit requires at least one legal action per row")
        batch.validate(
            state_dim=V07_C2_Q2_STATE_DIM,
            action_dim=FAST_Q2_ACTION_DIM,
        )
        states = np.asarray(batch.states)
        references = np.asarray(batch.reference_actions)
        candidates = np.asarray(batch.candidate_actions)
        masks = np.asarray(batch.action_masks)
        targets = np.asarray(batch.target_surplus_bits)
        if states.shape[0] < 1:
            raise ValueError("fast Q2 fit requires a positive row count")
        if masks.dtype != np.bool_ or not np.all(np.any(masks, axis=1)):
            raise ValueError("fast Q2 fit requires at least one legal action per row")
        same_action = references == candidates
        if np.any(targets[same_action] != 0.0):
            raise MCRLContractError(
                "candidate-equals-reference rows must have exact zero target"
            )
        return _batch_sha256(batch)

    def _batch_tensors(
        self, batch: EEAxisPairBatch
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        return (
            torch.tensor(np.asarray(batch.states, dtype=np.float32), device=self.device),
            torch.tensor(
                np.asarray(batch.reference_actions, dtype=np.int64), device=self.device
            ),
            torch.tensor(
                np.asarray(batch.candidate_actions, dtype=np.int64), device=self.device
            ),
            torch.tensor(
                np.asarray(batch.action_masks, dtype=np.bool_), device=self.device
            ),
            torch.tensor(
                np.asarray(batch.target_surplus_bits, dtype=np.float32)
                / float(self.config.kappa_bits),
                device=self.device,
            ),
        )

    def _loss_terms(
        self, batch: EEAxisPairBatch
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        states, reference, candidate, masks, target = self._batch_tensors(batch)
        surface = center_legal_surface(self.q2(states, masks), masks)
        q_reference = surface.gather(1, reference[:, None]).squeeze(1)
        q_candidate = surface.gather(1, candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - target
        pair_mse = torch.mean(residual.square())
        gauge_mse = torch.mean(q_reference.square())
        loss = pair_mse + float(self.config.beta) * gauge_mse
        return loss, pair_mse, gauge_mse

    def _current_metrics(self, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        with torch.no_grad():
            loss, pair_mse, gauge_mse = self._loss_terms(batch)
        assert_finite_loss(loss, objective=2)
        targets = np.asarray(batch.target_surplus_bits, dtype=np.float64)
        return {
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
            "target_mean_bits": float(np.mean(targets)),
            "target_std_bits": float(np.std(targets)),
            "target_min_bits": float(np.min(targets)),
            "target_max_bits": float(np.max(targets)),
        }

    def q2_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        """Return centered Q2 values with illegal action slots exactly zero.

        Rows with no legal actions are treated as non-deployable and returned
        as all zero.  The fit path itself rejects such rows because a pair
        action cannot be gathered from an empty native mask.
        """

        values = np.asarray(states, dtype=np.float32)
        legal = np.asarray(masks)
        if values.ndim != 2 or values.shape[1] != V07_C2_Q2_STATE_DIM:
            raise ValueError(
                f"states must have shape (batch,{V07_C2_Q2_STATE_DIM})"
            )
        if legal.shape != (values.shape[0], FAST_Q2_ACTION_DIM) or legal.dtype != np.bool_:
            raise ValueError("masks must be Boolean shape (batch,28)")
        if not np.all(np.isfinite(values)):
            raise ValueError("states must be finite")
        result = np.zeros((values.shape[0], FAST_Q2_ACTION_DIM), dtype=np.float32)
        eligible = np.any(legal, axis=1)
        if bool(np.any(eligible)):
            with torch.no_grad():
                state_tensor = torch.tensor(
                    values[eligible], dtype=torch.float32, device=self.device
                )
                mask_tensor = torch.tensor(
                    legal[eligible], dtype=torch.bool, device=self.device
                )
                raw = self.q2(state_tensor, mask_tensor)
                result[eligible] = center_legal_surface(raw, mask_tensor).cpu().numpy()
        return result

    def fit(
        self,
        batch: EEAxisPairBatch,
        *,
        updates: int = FAST_Q2_DEFAULT_UPDATES,
    ) -> dict[str, float | int | str]:
        """Run exactly ``updates`` deterministic full-batch Adam updates.

        ``updates`` is bounded by 100 over the lifetime of this object.  A
        second fit may continue the same immutable batch, but changing its
        rows is rejected so a rapid result cannot silently mix candidates.
        """

        count = _exact_updates(updates)
        if self.update_count + count > FAST_Q2_MAX_UPDATES:
            raise MCRLContractError(
                f"fast Q2 update budget is exhausted at {FAST_Q2_MAX_UPDATES}"
            )
        batch_digest = self._validate_batch(batch)
        if self._batch_digest is None:
            self._batch_digest = batch_digest
        elif self._batch_digest != batch_digest:
            raise MCRLContractError("fast Q2 batch changed across optimizer steps")

        before = self._current_metrics(batch)
        for _ in range(count):
            loss, pair_mse, _gauge_mse = self._loss_terms(batch)
            self.optimizer.zero_grad(set_to_none=True)
            loss.backward()
            assert_finite_loss(loss, objective=2)
            assert_finite_gradients(self.q2.parameters(), objective=2)
            self.optimizer.step()
            assert_finite_parameters((self.q2,))
            self.update_count += 1
            # Retain the names to make the optimizer loop visibly pairwise;
            # the values are computed again after the final update below.
            _ = pair_mse
        after = self._current_metrics(batch)
        result: dict[str, float | int | str] = {
            "algorithm": self.algorithm,
            "claim_ceiling": self.claim_ceiling,
            "train_seed": self.train_seed,
            "update_count": self.update_count,
            "updates": count,
            "batch_size": int(np.asarray(batch.states).shape[0]),
            "batch_sha256": batch_digest,
            "state_schema": self.state_schema,
            "state_schema_sha256": self.state_schema_sha256,
            "initial_loss": before["loss"],
            "final_loss": after["loss"],
            "initial_pair_mse": before["pair_mse"],
            "final_pair_mse": after["pair_mse"],
            "initial_gauge_mse": before["gauge_mse"],
            "final_gauge_mse": after["gauge_mse"],
            "target_mean_bits": after["target_mean_bits"],
            "target_std_bits": after["target_std_bits"],
            "target_min_bits": after["target_min_bits"],
            "target_max_bits": after["target_max_bits"],
            "learning_rate": float(self.config.learning_rate),
            "kappa_bits": float(self.config.kappa_bits),
            "beta": float(self.config.beta),
            "parameter_sha256": q2_parameter_sha256(self.q2),
        }
        self.last_fit_diagnostics = result
        return result

    def train_full_batch(
        self,
        batch: EEAxisPairBatch,
        *,
        updates: int = FAST_Q2_DEFAULT_UPDATES,
    ) -> dict[str, float | int | str]:
        """Readable alias for :meth:`fit` used by rapid-screen runners."""

        return self.fit(batch, updates=updates)

    def update(self, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        """Apply one full-batch update; useful for a tiny progress probe."""

        return self.fit(batch, updates=1)

    def fit_diagnostics(
        self, batch: EEAxisPairBatch
    ) -> dict[str, float | int | str]:
        """Return current loss/target diagnostics without changing Q2."""

        batch_digest = self._validate_batch(batch)
        if self._batch_digest is not None and self._batch_digest != batch_digest:
            raise MCRLContractError("fast Q2 batch changed across optimizer steps")
        metrics = self._current_metrics(batch)
        return {
            "algorithm": self.algorithm,
            "claim_ceiling": self.claim_ceiling,
            "train_seed": self.train_seed,
            "update_count": self.update_count,
            "updates": 0,
            "batch_size": int(np.asarray(batch.states).shape[0]),
            "batch_sha256": batch_digest,
            "state_schema": self.state_schema,
            "state_schema_sha256": self.state_schema_sha256,
            **metrics,
            "learning_rate": float(self.config.learning_rate),
            "kappa_bits": float(self.config.kappa_bits),
            "beta": float(self.config.beta),
            "parameter_sha256": q2_parameter_sha256(self.q2),
        }


# Descriptive aliases keep callers from depending on one spelling while the
# implementation remains one Q2 class and never grows Q1/Q3 state.
EEAxisV07C2FastQ2Trainer = FreshQ2
EEAxisV07C2FastQ2 = FreshQ2


__all__ = [
    "EEAxisV07C2FastQ2",
    "EEAxisV07C2FastQ2Trainer",
    "FAST_Q2_ACTION_DIM",
    "FAST_Q2_ADAM",
    "FAST_Q2_ALGORITHM",
    "FAST_Q2_BETA",
    "FAST_Q2_CLAIM_CEILING",
    "FAST_Q2_DEFAULT_UPDATES",
    "FAST_Q2_KAPPA_BITS",
    "FAST_Q2_LEARNING_RATE",
    "FAST_Q2_MAX_UPDATES",
    "FreshQ2",
    "center_legal_surface",
    "fast_q2_config",
    "q2_parameter_sha256",
]
