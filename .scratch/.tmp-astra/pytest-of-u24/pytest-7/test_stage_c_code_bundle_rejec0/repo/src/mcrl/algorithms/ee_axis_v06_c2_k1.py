"""Dedicated, bounded Q2-only learner for Multi-Catfish V0.6 C2-k1.

The class owns exactly one fresh Q2.  It cannot construct, optimize, or sum a
Q1, Q3, or resident legacy Q2.  Its constructor and update budget are fixed
before the T1 source verdict is opened.
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
from ..runtime.ee_axis_state import EE_AXIS_STATE_DIM
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


V06_C2_K1_ALGORITHM = "multi-catfish-mcrl-ee-axis-v06-c2-k1-q2-only"
V06_C2_K1_CHECKPOINT_VERSION = 1
V06_C2_K1_Q2_SEEDS = (2026102101, 2026102102, 2026102103)
V06_C2_K1_LINEAGES = ("q13-a", "q13-b", "q13-c")
V06_C2_K1_SEED_BY_LINEAGE = dict(
    zip(V06_C2_K1_LINEAGES, V06_C2_K1_Q2_SEEDS, strict=True)
)
V06_C2_K1_ACTION_DIM = 28
V06_C2_K1_ROWS = 12 * V06_C2_K1_ACTION_DIM
V06_C2_K1_UPDATES = 100
V06_C2_K1_CHECKPOINTS = (0, 100)
V06_C2_K1_TORCH_NUM_THREADS = 1
V06_C2_K1_KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
V06_C2_K1_BETA = float.fromhex("0x1.999999999999ap-4")
V06_C2_K1_ADAM = {
    "lr": 0.001,
    "betas": (0.9, 0.999),
    "eps": 1e-8,
    "weight_decay": 0.0,
    "amsgrad": False,
}


def frozen_q2_config() -> EEAxisMaskedMeanMaxConfig:
    """Return the sole admissible V0.6 C2-k1 Q2 configuration."""

    return EEAxisMaskedMeanMaxConfig(
        state_dim=EE_AXIS_STATE_DIM,
        action_dim=V06_C2_K1_ACTION_DIM,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=V06_C2_K1_ADAM["lr"],
        kappa_bits=V06_C2_K1_KAPPA_BITS,
        beta=V06_C2_K1_BETA,
        loss_weights=(1.0, 1.0, 1.0),
    )


def _canonical_sha256(payload: object) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise MCRLContractError("V0.6 Q2 payload is not canonical JSON") from error
    return hashlib.sha256(encoded).hexdigest()


def q2_parameter_sha256(network: MaskedMeanMaxQNetwork) -> str:
    """Hash named Q2 parameter tensors independent of checkpoint packaging."""

    digest = hashlib.sha256()
    for name, value in sorted(network.state_dict().items(), key=lambda item: item[0]):
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


def _batch_sha256(batch: EEAxisPairBatch) -> str:
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


class EEAxisV06C2K1Trainer:
    """One deterministic fresh Q2 and one exact full-batch optimizer."""

    def __init__(
        self,
        *,
        lineage: str,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        if lineage not in V06_C2_K1_LINEAGES:
            raise ValueError("lineage must be one frozen q13-a/q13-b/q13-c value")
        if type(train_seed) is not int or train_seed != V06_C2_K1_SEED_BY_LINEAGE[lineage]:
            raise ValueError("train_seed disagrees with the frozen V0.6 lineage")
        if device != "cpu":
            raise ValueError("V0.6 C2-k1 permits only the deterministic CPU path")
        self.lineage = lineage
        self.train_seed = train_seed
        self.device = torch.device("cpu")
        self.config = frozen_q2_config()
        torch.use_deterministic_algorithms(True)
        torch.set_num_threads(V06_C2_K1_TORCH_NUM_THREADS)
        # This is deliberately the first and only stochastic construction.
        torch.manual_seed(train_seed)
        self.q2 = MaskedMeanMaxQNetwork(self.config).to(self.device)
        self.optimizer = optim.Adam(
            self.q2.parameters(),
            lr=V06_C2_K1_ADAM["lr"],
            betas=V06_C2_K1_ADAM["betas"],
            eps=V06_C2_K1_ADAM["eps"],
            weight_decay=V06_C2_K1_ADAM["weight_decay"],
            amsgrad=V06_C2_K1_ADAM["amsgrad"],
        )
        self.update_count = 0
        self._batch_sha256: str | None = None
        self.update0_parameter_sha256 = q2_parameter_sha256(self.q2)

    @staticmethod
    def _validate_canonical_batch(batch: EEAxisPairBatch) -> str:
        batch.validate(
            state_dim=EE_AXIS_STATE_DIM,
            action_dim=V06_C2_K1_ACTION_DIM,
        )
        states = np.asarray(batch.states)
        references = np.asarray(batch.reference_actions)
        candidates = np.asarray(batch.candidate_actions)
        masks = np.asarray(batch.action_masks)
        targets = np.asarray(batch.target_surplus_bits)
        if (
            states.shape != (V06_C2_K1_ROWS, EE_AXIS_STATE_DIM)
            or references.shape != (V06_C2_K1_ROWS,)
            or candidates.shape != (V06_C2_K1_ROWS,)
            or masks.shape != (V06_C2_K1_ROWS, V06_C2_K1_ACTION_DIM)
            or targets.shape != (V06_C2_K1_ROWS,)
        ):
            raise ValueError("V0.6 Q2 batch must contain exactly 336 rows")
        expected_candidates = np.tile(
            np.arange(V06_C2_K1_ACTION_DIM, dtype=np.int64), 12
        )
        if not np.array_equal(candidates, expected_candidates):
            raise ValueError("V0.6 Q2 candidate rows are not canonical action 0..27")
        for block in range(12):
            start = block * V06_C2_K1_ACTION_DIM
            stop = start + V06_C2_K1_ACTION_DIM
            if not np.all(references[start:stop] == references[start]):
                raise ValueError("V0.6 Q2 reference action drifted within an anchor")
            if not np.all(states[start:stop] == states[start]):
                raise ValueError("V0.6 Q2 state drifted within an anchor")
            if not np.all(masks[start:stop] == masks[start]):
                raise ValueError("V0.6 Q2 mask drifted within an anchor")
        if masks.dtype != np.bool_ or not bool(np.all(masks)):
            raise ValueError("V0.6 Q2 fit requires complete 28-action masks")
        if not np.all(np.isfinite(states)) or not np.all(np.isfinite(targets)):
            raise ValueError("V0.6 Q2 batch contains nonfinite data")
        return _batch_sha256(batch)

    def q2_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        """Evaluate only users with legal actions; empty rows remain zero."""

        values = np.asarray(states, dtype=np.float32)
        legal = np.asarray(masks)
        if values.ndim != 2 or values.shape[1] != EE_AXIS_STATE_DIM:
            raise ValueError("states must have shape (batch,228)")
        if legal.shape != (values.shape[0], V06_C2_K1_ACTION_DIM) or legal.dtype != np.bool_:
            raise ValueError("masks must be Boolean shape (batch,28)")
        if not np.all(np.isfinite(values)):
            raise ValueError("states must be finite")
        result = np.zeros(
            (values.shape[0], V06_C2_K1_ACTION_DIM), dtype=np.float32
        )
        eligible = np.any(legal, axis=1)
        if bool(np.any(eligible)):
            with torch.no_grad():
                state_tensor = torch.tensor(
                    values[eligible], dtype=torch.float32, device=self.device
                )
                mask_tensor = torch.tensor(
                    legal[eligible], dtype=torch.bool, device=self.device
                )
                result[eligible] = self.q2(state_tensor, mask_tensor).cpu().numpy()
        return result

    def update(self, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        """Apply one of exactly 100 identical-order full-batch updates."""

        if self.update_count >= V06_C2_K1_UPDATES:
            raise MCRLContractError("V0.6 Q2 update budget is exhausted")
        batch_digest = self._validate_canonical_batch(batch)
        if self._batch_sha256 is None:
            self._batch_sha256 = batch_digest
        elif self._batch_sha256 != batch_digest:
            raise MCRLContractError("V0.6 Q2 batch changed across optimizer steps")
        states, reference, candidate, masks, target = self._batch_tensors(batch)
        surface = self.q2(states, masks)
        q_reference = surface.gather(1, reference[:, None]).squeeze(1)
        q_candidate = surface.gather(1, candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - target
        pair_mse = torch.mean(residual.square())
        gauge_mse = torch.mean(q_reference.square())
        loss = pair_mse + V06_C2_K1_BETA * gauge_mse
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=2)
        assert_finite_gradients(self.q2.parameters(), objective=2)
        self.optimizer.step()
        assert_finite_parameters((self.q2,))
        self.update_count += 1
        return {
            "algorithm": V06_C2_K1_ALGORITHM,
            "lineage": self.lineage,
            "update_count": self.update_count,
            "batch_size": V06_C2_K1_ROWS,
            "batch_sha256": batch_digest,
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
            "parameter_sha256": q2_parameter_sha256(self.q2),
        }

    def _batch_tensors(
        self, batch: EEAxisPairBatch
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
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
            / V06_C2_K1_KAPPA_BITS,
            dtype=torch.float32,
            device=self.device,
        )
        return states, reference, candidate, masks, target

    def loss_diagnostics(self, batch: EEAxisPairBatch) -> dict[str, float | int | str]:
        """Measure the frozen loss without a gradient or optimizer step."""

        batch_digest = self._validate_canonical_batch(batch)
        with torch.no_grad():
            states, reference, candidate, masks, target = self._batch_tensors(batch)
            surface = self.q2(states, masks)
            q_reference = surface.gather(1, reference[:, None]).squeeze(1)
            q_candidate = surface.gather(1, candidate[:, None]).squeeze(1)
            residual = q_candidate - q_reference - target
            pair_mse = torch.mean(residual.square())
            gauge_mse = torch.mean(q_reference.square())
            loss = pair_mse + V06_C2_K1_BETA * gauge_mse
        assert_finite_loss(loss, objective=2)
        return {
            "algorithm": V06_C2_K1_ALGORITHM,
            "lineage": self.lineage,
            "update_count": self.update_count,
            "batch_size": V06_C2_K1_ROWS,
            "batch_sha256": batch_digest,
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
            "parameter_sha256": q2_parameter_sha256(self.q2),
        }

    def checkpoint_state(self) -> dict[str, Any]:
        if self.update_count not in V06_C2_K1_CHECKPOINTS:
            raise MCRLContractError("only update-0 and update-100 may be checkpointed")
        return {
            "format_version": V06_C2_K1_CHECKPOINT_VERSION,
            "algorithm": V06_C2_K1_ALGORITHM,
            "lineage": self.lineage,
            "train_seed": self.train_seed,
            "update_count": self.update_count,
            "config": asdict(self.config),
            "adam": {
                "lr": V06_C2_K1_ADAM["lr"],
                "betas": list(V06_C2_K1_ADAM["betas"]),
                "eps": V06_C2_K1_ADAM["eps"],
                "weight_decay": V06_C2_K1_ADAM["weight_decay"],
                "amsgrad": V06_C2_K1_ADAM["amsgrad"],
            },
            "determinism": {
                "deterministic_algorithms": True,
                "torch_num_threads": V06_C2_K1_TORCH_NUM_THREADS,
                "device": "cpu",
            },
            "batch_sha256": self._batch_sha256,
            "update0_parameter_sha256": self.update0_parameter_sha256,
            "parameter_sha256": q2_parameter_sha256(self.q2),
            "q2_network": self.q2.state_dict(),
            "q2_optimizer": self.optimizer.state_dict(),
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if state.get("format_version") != V06_C2_K1_CHECKPOINT_VERSION or state.get("algorithm") != V06_C2_K1_ALGORITHM:
            raise MCRLContractError("checkpoint is not V0.6 C2-k1 Q2-only")
        if state.get("lineage") != self.lineage or state.get("train_seed") != self.train_seed:
            raise MCRLContractError("V0.6 Q2 checkpoint lineage drifted")
        if state.get("config") != asdict(self.config):
            raise MCRLContractError("V0.6 Q2 checkpoint config drifted")
        expected_adam = {
            "lr": V06_C2_K1_ADAM["lr"],
            "betas": list(V06_C2_K1_ADAM["betas"]),
            "eps": V06_C2_K1_ADAM["eps"],
            "weight_decay": V06_C2_K1_ADAM["weight_decay"],
            "amsgrad": V06_C2_K1_ADAM["amsgrad"],
        }
        if state.get("adam") != expected_adam:
            raise MCRLContractError("V0.6 Q2 checkpoint Adam contract drifted")
        if state.get("determinism") != {
            "deterministic_algorithms": True,
            "torch_num_threads": V06_C2_K1_TORCH_NUM_THREADS,
            "device": "cpu",
        }:
            raise MCRLContractError("V0.6 Q2 checkpoint determinism drifted")
        update_count = state.get("update_count")
        if update_count not in V06_C2_K1_CHECKPOINTS:
            raise MCRLContractError("V0.6 Q2 checkpoint is not update 0 or 100")
        if state.get("update0_parameter_sha256") != self.update0_parameter_sha256:
            raise MCRLContractError("V0.6 Q2 update-0 authority drifted")
        network = state.get("q2_network")
        optimizer = state.get("q2_optimizer")
        if not isinstance(network, Mapping) or not isinstance(optimizer, Mapping):
            raise MCRLContractError("V0.6 Q2 checkpoint payload is malformed")
        self.q2.load_state_dict(network, strict=True)
        self.optimizer.load_state_dict(optimizer)
        self.update_count = int(update_count)
        batch_digest = state.get("batch_sha256")
        if batch_digest is not None and (
            not isinstance(batch_digest, str) or len(batch_digest) != 64
        ):
            raise MCRLContractError("V0.6 Q2 checkpoint batch digest is malformed")
        self._batch_sha256 = batch_digest
        if state.get("parameter_sha256") != q2_parameter_sha256(self.q2):
            raise MCRLContractError("V0.6 Q2 checkpoint parameter digest drifted")
        assert_finite_parameters((self.q2,))
        return self.update_count


__all__ = [
    "EEAxisV06C2K1Trainer",
    "V06_C2_K1_ACTION_DIM",
    "V06_C2_K1_ADAM",
    "V06_C2_K1_ALGORITHM",
    "V06_C2_K1_BETA",
    "V06_C2_K1_CHECKPOINTS",
    "V06_C2_K1_CHECKPOINT_VERSION",
    "V06_C2_K1_KAPPA_BITS",
    "V06_C2_K1_LINEAGES",
    "V06_C2_K1_Q2_SEEDS",
    "V06_C2_K1_ROWS",
    "V06_C2_K1_SEED_BY_LINEAGE",
    "V06_C2_K1_UPDATES",
    "frozen_q2_config",
    "q2_parameter_sha256",
]
