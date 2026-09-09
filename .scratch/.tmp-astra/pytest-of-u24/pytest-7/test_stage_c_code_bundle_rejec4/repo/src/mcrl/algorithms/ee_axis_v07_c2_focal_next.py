"""Fresh Q2-only learner for the V0.7 focal-next C2 target.

This module deliberately does not import or own Q1, Q3, or a legacy Q2.  It
fits one mask-explicit action-shared surface from a fixed pair batch.  The raw
surface is centered over the native legal action set before both training and
deployment; centering changes no candidate/reference difference and therefore
does not introduce a route weight.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
from dataclasses import asdict
import hashlib
import json
from typing import Any

import numpy as np
import torch
import torch.optim as optim

from ..errors import MCRLContractError
from ..runtime.ee_axis_v07_c2_dataset import (
    V07C2Dataset,
    build_v07_pair_batch,
)
from ..runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)
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


V07_C2_ALGORITHM = "multi-catfish-mcrl-ee-axis-v07-c2-focal-next-q2-only"
V07_C2_CHECKPOINT_VERSION = 1
V07_C2_ACTION_DIM = 28
V07_C2_LINEAGES = ("q13-a", "q13-b", "q13-c")
V07_C2_ROLES = ("provisional", "final")
V07_C2_SEED_BY_ROLE_LINEAGE = {
    "provisional": {
        "q13-a": 2026102201,
        "q13-b": 2026102202,
        "q13-c": 2026102203,
    },
    "final": {
        "q13-a": 2026102301,
        "q13-b": 2026102302,
        "q13-c": 2026102303,
    },
}
V07_C2_UPDATE_LADDER = (100, 500, 1500)
V07_C2_MAX_UPDATES = max(V07_C2_UPDATE_LADDER)
V07_C2_CHECKPOINTS = tuple(range(0, V07_C2_MAX_UPDATES + 1, 100))
V07_C2_TORCH_NUM_THREADS = 1
V07_C2_KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")
V07_C2_ADAM = {
    "lr": 0.001,
    "betas": (0.9, 0.999),
    "eps": 1e-8,
    "weight_decay": 0.0,
    "amsgrad": False,
}


def frozen_q2_config() -> EEAxisMaskedMeanMaxConfig:
    """Return the sole V0.7 scorer configuration.

    ``beta`` is zero because legal-set centering fixes the additive gauge and
    the public V0.7 loss contains only the pairwise residual.
    """

    return EEAxisMaskedMeanMaxConfig(
        state_dim=V07_C2_Q2_STATE_DIM,
        action_dim=V07_C2_ACTION_DIM,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=V07_C2_ADAM["lr"],
        kappa_bits=V07_C2_KAPPA_BITS,
        beta=0.0,
        loss_weights=(1.0, 1.0, 1.0),
    )


def _state_dict_sha256(state: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(state.items(), key=lambda item: item[0]):
        detach = getattr(value, "detach", None)
        if not isinstance(name, str) or not callable(detach):
            raise MCRLContractError("Q2 state_dict is malformed")
        array = np.ascontiguousarray(detach().cpu().numpy())
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
    """Hash named Q2 parameter tensors independent of checkpoint packaging."""

    return _state_dict_sha256(network.state_dict())


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


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


def center_legal_surface(raw: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
    """Subtract each row's legal-action mean and zero its illegal entries."""

    if raw.ndim != 2 or masks.shape != raw.shape or masks.dtype != torch.bool:
        raise ValueError("raw Q2 and Boolean masks must be matching matrices")
    if not torch.all(torch.any(masks, dim=1)):
        raise ValueError("centered Q2 rows must admit at least one legal action")
    legal = masks.to(raw.dtype)
    mean = (raw * legal).sum(dim=1, keepdim=True) / legal.sum(dim=1, keepdim=True)
    return torch.where(masks, raw - mean, torch.zeros_like(raw))


class EEAxisV07C2Trainer:
    """One deterministic fresh Q2 trained on one immutable variable-mask batch."""

    state_schema = V07_C2_Q2_STATE_SCHEMA
    state_schema_sha256 = V07_C2_Q2_STATE_SCHEMA_SHA256

    def __init__(
        self,
        *,
        lineage: str,
        role: str,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        if lineage not in V07_C2_LINEAGES:
            raise ValueError("lineage must be q13-a, q13-b, or q13-c")
        if role not in V07_C2_ROLES:
            raise ValueError("role must be provisional or final")
        expected_seed = V07_C2_SEED_BY_ROLE_LINEAGE[role][lineage]
        if type(train_seed) is not int or train_seed != expected_seed:
            raise ValueError("train_seed disagrees with the frozen V0.7 role/lineage")
        if device != "cpu":
            raise ValueError("V0.7 C2 permits only the deterministic CPU path")
        self.lineage = lineage
        self.role = role
        self.train_seed = train_seed
        self.device = torch.device("cpu")
        self.config = frozen_q2_config()
        torch.use_deterministic_algorithms(True)
        torch.set_num_threads(V07_C2_TORCH_NUM_THREADS)
        torch.manual_seed(train_seed)
        self.q2 = MaskedMeanMaxQNetwork(self.config).to(self.device)
        self.optimizer = optim.Adam(
            self.q2.parameters(),
            lr=V07_C2_ADAM["lr"],
            betas=V07_C2_ADAM["betas"],
            eps=V07_C2_ADAM["eps"],
            weight_decay=V07_C2_ADAM["weight_decay"],
            amsgrad=V07_C2_ADAM["amsgrad"],
        )
        self.update_count = 0
        self._batch_sha256: str | None = None
        self._corpus_sha256: str | None = None
        self.update0_parameter_sha256 = q2_parameter_sha256(self.q2)

    def _dataset_batch(self, dataset: V07C2Dataset) -> tuple[EEAxisPairBatch, str]:
        if not isinstance(dataset, V07C2Dataset):
            raise TypeError("V0.7 Q2 update requires a V07C2Dataset authority")
        expected_round = "bootstrap" if self.role == "provisional" else "refresh"
        lineages = {item.lineage for item in dataset.coverage}
        rounds = {item.refresh_round for item in dataset.coverage}
        if lineages != {self.lineage} or rounds != {expected_round}:
            raise MCRLContractError(
                "V0.7 Q2 dataset disagrees with trainer role/lineage"
            )
        dataset.verify()
        return build_v07_pair_batch(dataset), dataset.corpus_sha256

    @staticmethod
    def _validate_batch(batch: EEAxisPairBatch) -> str:
        batch.validate(state_dim=V07_C2_Q2_STATE_DIM, action_dim=V07_C2_ACTION_DIM)
        states = np.asarray(batch.states)
        references = np.asarray(batch.reference_actions)
        candidates = np.asarray(batch.candidate_actions)
        masks = np.asarray(batch.action_masks)
        targets = np.asarray(batch.target_surplus_bits)
        if states.shape[0] < 1:
            raise ValueError("V0.7 Q2 batch must contain at least one nonempty row")
        if masks.dtype != np.bool_ or not np.all(np.any(masks, axis=1)):
            raise ValueError("V0.7 Q2 fit accepts only nonempty native masks")
        same_action = references == candidates
        if np.any(targets[same_action] != 0.0):
            raise MCRLContractError(
                "candidate-equals-reference rows must have exact zero target"
            )
        return _batch_sha256(batch)

    @staticmethod
    def _centered(network: MaskedMeanMaxQNetwork, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        return center_legal_surface(network(states, masks), masks)

    def q2_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        """Return centered Q2 values; empty-mask users remain all-zero."""

        values = np.asarray(states, dtype=np.float32)
        legal = np.asarray(masks)
        if values.ndim != 2 or values.shape[1] != V07_C2_Q2_STATE_DIM:
            raise ValueError(
                f"states must have shape (batch,{V07_C2_Q2_STATE_DIM})"
            )
        if legal.shape != (values.shape[0], V07_C2_ACTION_DIM) or legal.dtype != np.bool_:
            raise ValueError("masks must be Boolean shape (batch,28)")
        if not np.all(np.isfinite(values)):
            raise ValueError("states must be finite")
        result = np.zeros((values.shape[0], V07_C2_ACTION_DIM), dtype=np.float32)
        eligible = np.any(legal, axis=1)
        if bool(np.any(eligible)):
            with torch.no_grad():
                state_tensor = torch.tensor(
                    values[eligible], dtype=torch.float32, device=self.device
                )
                mask_tensor = torch.tensor(
                    legal[eligible], dtype=torch.bool, device=self.device
                )
                result[eligible] = self._centered(
                    self.q2, state_tensor, mask_tensor
                ).cpu().numpy()
        return result

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
            / V07_C2_KAPPA_BITS,
            dtype=torch.float32,
            device=self.device,
        )
        return states, reference, candidate, masks, target

    def _loss_terms(
        self, batch: EEAxisPairBatch
    ) -> tuple[torch.Tensor, torch.Tensor, str]:
        batch_digest = self._validate_batch(batch)
        states, reference, candidate, masks, target = self._batch_tensors(batch)
        surface = self._centered(self.q2, states, masks)
        q_reference = surface.gather(1, reference[:, None]).squeeze(1)
        q_candidate = surface.gather(1, candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - target
        return torch.mean(residual.square()), surface, batch_digest

    def update(self, dataset: V07C2Dataset) -> dict[str, float | int | str]:
        """Apply one identical-order full-batch update, up to the 1500 rung."""

        if self.update_count >= V07_C2_MAX_UPDATES:
            raise MCRLContractError("V0.7 Q2 update budget is exhausted")
        batch, corpus_digest = self._dataset_batch(dataset)
        pair_mse, surface, batch_digest = self._loss_terms(batch)
        if self._batch_sha256 is None:
            self._batch_sha256 = batch_digest
            self._corpus_sha256 = corpus_digest
        elif self._batch_sha256 != batch_digest:
            raise MCRLContractError("V0.7 Q2 batch changed across optimizer steps")
        elif self._corpus_sha256 != corpus_digest:
            raise MCRLContractError("V0.7 Q2 corpus changed across optimizer steps")
        loss = pair_mse
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        assert_finite_loss(loss, objective=2)
        assert_finite_gradients(self.q2.parameters(), objective=2)
        self.optimizer.step()
        assert_finite_parameters((self.q2,))
        self.update_count += 1
        legal = torch.tensor(
            np.asarray(batch.action_masks, dtype=np.bool_), dtype=torch.bool
        )
        centered_legal_mean = float(
            torch.max(
                torch.abs(
                    (surface.detach().cpu() * legal).sum(dim=1)
                    / legal.sum(dim=1)
                )
            )
        )
        return {
            "algorithm": V07_C2_ALGORITHM,
            "lineage": self.lineage,
            "role": self.role,
            "update_count": self.update_count,
            "batch_size": int(np.asarray(batch.states).shape[0]),
            "batch_sha256": batch_digest,
            "corpus_sha256": corpus_digest,
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "max_abs_legal_mean": centered_legal_mean,
            "state_schema": self.state_schema,
            "state_schema_sha256": self.state_schema_sha256,
            "parameter_sha256": q2_parameter_sha256(self.q2),
        }

    def loss_diagnostics(self, dataset: V07C2Dataset) -> dict[str, float | int | str]:
        """Measure the frozen pairwise loss without an optimizer step."""

        batch, corpus_digest = self._dataset_batch(dataset)
        with torch.no_grad():
            pair_mse, _surface, batch_digest = self._loss_terms(batch)
        assert_finite_loss(pair_mse, objective=2)
        return {
            "algorithm": V07_C2_ALGORITHM,
            "lineage": self.lineage,
            "role": self.role,
            "update_count": self.update_count,
            "batch_size": int(np.asarray(batch.states).shape[0]),
            "batch_sha256": batch_digest,
            "corpus_sha256": corpus_digest,
            "loss": float(pair_mse.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "state_schema": self.state_schema,
            "state_schema_sha256": self.state_schema_sha256,
            "parameter_sha256": q2_parameter_sha256(self.q2),
        }

    def checkpoint_state(self) -> dict[str, Any]:
        if self.update_count not in V07_C2_CHECKPOINTS:
            raise MCRLContractError("V0.7 Q2 checkpoints are permitted every 100 updates")
        return {
            "format_version": V07_C2_CHECKPOINT_VERSION,
            "algorithm": V07_C2_ALGORITHM,
            "lineage": self.lineage,
            "role": self.role,
            "train_seed": self.train_seed,
            "update_count": self.update_count,
            "update_ladder": list(V07_C2_UPDATE_LADDER),
            "legal_mask_centering": True,
            "state_schema": self.state_schema,
            "state_schema_sha256": self.state_schema_sha256,
            "config": asdict(self.config),
            "adam": {
                "lr": V07_C2_ADAM["lr"],
                "betas": list(V07_C2_ADAM["betas"]),
                "eps": V07_C2_ADAM["eps"],
                "weight_decay": V07_C2_ADAM["weight_decay"],
                "amsgrad": V07_C2_ADAM["amsgrad"],
            },
            "determinism": {
                "deterministic_algorithms": True,
                "torch_num_threads": V07_C2_TORCH_NUM_THREADS,
                "device": "cpu",
            },
            "batch_sha256": self._batch_sha256,
            "corpus_sha256": self._corpus_sha256,
            "update0_parameter_sha256": self.update0_parameter_sha256,
            "parameter_sha256": q2_parameter_sha256(self.q2),
            # ``state_dict`` tensor values alias live parameters.  Snapshot
            # them so a saved update-0 authority cannot mutate during later
            # optimizer steps before serialization.
            "q2_network": copy.deepcopy(self.q2.state_dict()),
            "q2_optimizer": copy.deepcopy(self.optimizer.state_dict()),
        }

    def load_checkpoint_state(self, state: Mapping[str, Any]) -> int:
        if (
            state.get("format_version") != V07_C2_CHECKPOINT_VERSION
            or state.get("algorithm") != V07_C2_ALGORITHM
        ):
            raise MCRLContractError("checkpoint is not V0.7 focal-next Q2-only")
        if (
            state.get("lineage") != self.lineage
            or state.get("role") != self.role
            or state.get("train_seed") != self.train_seed
        ):
            raise MCRLContractError("V0.7 Q2 checkpoint identity drifted")
        if state.get("config") != asdict(self.config):
            raise MCRLContractError("V0.7 Q2 checkpoint config drifted")
        if state.get("update_ladder") != list(V07_C2_UPDATE_LADDER):
            raise MCRLContractError("V0.7 Q2 checkpoint update ladder drifted")
        if state.get("legal_mask_centering") is not True:
            raise MCRLContractError("V0.7 Q2 checkpoint lost legal-mask centering")
        if (
            state.get("state_schema") != self.state_schema
            or state.get("state_schema_sha256") != self.state_schema_sha256
        ):
            raise MCRLContractError("V0.7 Q2 checkpoint state schema drifted")
        expected_adam = {
            "lr": V07_C2_ADAM["lr"],
            "betas": list(V07_C2_ADAM["betas"]),
            "eps": V07_C2_ADAM["eps"],
            "weight_decay": V07_C2_ADAM["weight_decay"],
            "amsgrad": V07_C2_ADAM["amsgrad"],
        }
        if state.get("adam") != expected_adam:
            raise MCRLContractError("V0.7 Q2 checkpoint Adam contract drifted")
        if state.get("determinism") != {
            "deterministic_algorithms": True,
            "torch_num_threads": V07_C2_TORCH_NUM_THREADS,
            "device": "cpu",
        }:
            raise MCRLContractError("V0.7 Q2 checkpoint determinism drifted")
        update_count = state.get("update_count")
        if (
            type(update_count) is not int
            or update_count not in V07_C2_CHECKPOINTS
        ):
            raise MCRLContractError("V0.7 Q2 checkpoint is not on a 100-update rung")
        if state.get("update0_parameter_sha256") != self.update0_parameter_sha256:
            raise MCRLContractError("V0.7 Q2 update-0 authority drifted")
        network = state.get("q2_network")
        optimizer = state.get("q2_optimizer")
        if not isinstance(network, Mapping) or not isinstance(optimizer, Mapping):
            raise MCRLContractError("V0.7 Q2 checkpoint payload is malformed")
        parameter_digest = state.get("parameter_sha256")
        if not _valid_sha256(parameter_digest):
            raise MCRLContractError("V0.7 Q2 checkpoint parameter digest is malformed")
        if parameter_digest != _state_dict_sha256(network):
            raise MCRLContractError("V0.7 Q2 checkpoint parameter digest drifted")
        batch_digest = state.get("batch_sha256")
        if batch_digest is not None and not _valid_sha256(batch_digest):
            raise MCRLContractError("V0.7 Q2 checkpoint batch digest is malformed")
        corpus_digest = state.get("corpus_sha256")
        if corpus_digest is not None and not _valid_sha256(corpus_digest):
            raise MCRLContractError("V0.7 Q2 checkpoint corpus digest is malformed")
        if (update_count == 0) != (batch_digest is None and corpus_digest is None):
            raise MCRLContractError(
                "V0.7 Q2 checkpoint update count and source authority disagree"
            )
        if update_count > 0 and (batch_digest is None or corpus_digest is None):
            raise MCRLContractError(
                "V0.7 Q2 checkpoint lacks batch/corpus source authority"
            )
        network_before = copy.deepcopy(self.q2.state_dict())
        optimizer_before = copy.deepcopy(self.optimizer.state_dict())
        count_before = self.update_count
        batch_before = self._batch_sha256
        corpus_before = self._corpus_sha256
        try:
            self.q2.load_state_dict(network, strict=True)
            self.optimizer.load_state_dict(optimizer)
            if parameter_digest != q2_parameter_sha256(self.q2):
                raise MCRLContractError(
                    "V0.7 Q2 checkpoint parameter digest drifted on load"
                )
        except Exception as error:
            self.q2.load_state_dict(network_before, strict=True)
            self.optimizer.load_state_dict(optimizer_before)
            self.update_count = count_before
            self._batch_sha256 = batch_before
            self._corpus_sha256 = corpus_before
            if isinstance(error, MCRLContractError):
                raise
            raise MCRLContractError(
                "V0.7 Q2 checkpoint load was not transactional"
            ) from error
        self.update_count = update_count
        self._batch_sha256 = batch_digest
        self._corpus_sha256 = corpus_digest
        assert_finite_parameters((self.q2,))
        return self.update_count


__all__ = [
    "EEAxisV07C2Trainer",
    "V07_C2_ACTION_DIM",
    "V07_C2_ADAM",
    "V07_C2_ALGORITHM",
    "V07_C2_CHECKPOINTS",
    "V07_C2_CHECKPOINT_VERSION",
    "V07_C2_KAPPA_BITS",
    "V07_C2_LINEAGES",
    "V07_C2_MAX_UPDATES",
    "V07_C2_ROLES",
    "V07_C2_SEED_BY_ROLE_LINEAGE",
    "V07_C2_UPDATE_LADDER",
    "center_legal_surface",
    "frozen_q2_config",
    "q2_parameter_sha256",
]
