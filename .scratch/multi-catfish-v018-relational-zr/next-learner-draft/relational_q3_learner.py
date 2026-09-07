"""Source-only relational Q3 learner adapter for the provisional V0.18 seam.

The adapter intentionally owns one and only one Q3 network and one optimizer.
It consumes an authenticated :class:`RelationalZRC3Source` (or an equivalent
mapping), fits the reference-centred surface with the fixed pairwise
zero-bootstrap objective, and exposes no policy, simulator, Q1/Q2, or target
network.  A future frozen learner contract must supply the production source
paths, update schedule, and acceptance rule.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
import torch
from torch import nn

from mcrl.algorithms.ee_axis_relational_zr_c3_head import (
    RELATIONAL_ZR_C3_HEAD_ALGORITHM,
    RELATIONAL_ZR_C3_HEAD_VERSION,
    RelationalZRC3NetworkConfig,
    RelationalZRC3QNetwork,
)

try:
    from .relational_source_schema import (
        ACTION_CONTEXT_DIM,
        ACTION_DIM,
        RelationalSourceError,
        RelationalZRC3Source,
        VICTIM_TOKEN_DIM,
    )
except ImportError:  # Loaded as a stand-alone draft module by a future runner.
    from relational_source_schema import (  # type: ignore[no-redef]
        ACTION_CONTEXT_DIM,
        ACTION_DIM,
        RelationalSourceError,
        RelationalZRC3Source,
        VICTIM_TOKEN_DIM,
    )


RELATIONAL_ZR_C3_LEARNER_ALGORITHM = "multi-catfish-mcrl-v018-relational-zr-c3-pairwise-learner"
RELATIONAL_ZR_C3_LEARNER_VERSION = 1
CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v018-relational-zr-c3-checkpoint-v1"
CHECKPOINT_VERSION = 1
REQUIRED_CHECKPOINT_UPDATES = 100


class RelationalLearnerError(ValueError):
    """A source, learner, or checkpoint boundary failed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RelationalLearnerError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalLearnerError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _finite_scalar(value: object, *, field: str, positive: bool = False) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalLearnerError(f"{field} must be finite") from error
    if not math.isfinite(number) or (positive and number <= 0.0):
        suffix = " and positive" if positive else ""
        raise RelationalLearnerError(f"{field} must be finite{suffix}")
    return number


def _state_digest(state: Mapping[str, Any]) -> str:
    """Digest a torch state dict without serialising it through pickle."""

    digest = hashlib.sha256()
    for name in sorted(state):
        value = state[name]
        if not isinstance(value, torch.Tensor):
            # Adam state contains scalar step tensors in current torch.  If a
            # future optimizer emits a non-tensor object, make the format
            # explicit rather than silently hashing its repr.
            digest.update(name.encode("utf-8"))
            digest.update(b"\\0json\\0")
            digest.update(_canonical_bytes(value))
            continue
        tensor = value.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(b"\\0tensor\\0")
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def _as_readonly_source(source: RelationalZRC3Source | Mapping[str, object]) -> RelationalZRC3Source:
    if isinstance(source, RelationalZRC3Source):
        return source
    if not isinstance(source, Mapping):
        raise RelationalLearnerError("source must be a RelationalZRC3Source or mapping")
    try:
        return RelationalZRC3Source(
            action_context=source["action_context"],
            victim_tokens=source["victim_tokens"],
            action_mask=source["action_mask"],
            victim_mask=source["victim_mask"],
            positive_credit_compatible=source["positive_credit_compatible"],
            reference_actions=source["reference_actions"],
            target_surface_bits=source["target_surface_bits"],
            world_seed=int(source["world_seed"]),
            lineage=int(source["lineage"]),
            split=str(source["split"]),
            field_root_digest=str(source["field_root_digest"]),
            kappa_bits=float(source["kappa_bits"]),
            feature_fields=tuple(source.get("feature_fields", ("action_context", "victim_tokens"))),
        )
    except (KeyError, TypeError, ValueError, RelationalSourceError) as error:
        raise RelationalLearnerError("source mapping is malformed") from error


@dataclass(frozen=True)
class RelationalZRC3LearnerConfig:
    """Learner choices that must be fixed by a future frozen contract."""

    action_dim: int = ACTION_DIM
    action_context_dim: int = ACTION_CONTEXT_DIM
    victim_token_dim: int = VICTIM_TOKEN_DIM
    hidden_layers: tuple[int, ...] = (32, 16)
    activation: str = "tanh"
    learning_rate: float = 0.001
    kappa_bits: float = 1.0
    beta: float = 0.0

    def __post_init__(self) -> None:
        if self.action_dim != ACTION_DIM:
            raise RelationalLearnerError("V0.18 action_dim must match the structured source schema")
        for field in ("action_context_dim", "victim_token_dim"):
            if isinstance(getattr(self, field), bool) or not isinstance(getattr(self, field), int) or getattr(self, field) < 1:
                raise RelationalLearnerError(f"{field} must be a positive integer")
        if any(isinstance(width, bool) or not isinstance(width, int) or width < 1 for width in self.hidden_layers):
            raise RelationalLearnerError("hidden_layers must contain positive widths")
        if self.activation not in {"tanh", "relu"}:
            raise RelationalLearnerError("activation must be tanh or relu")
        _finite_scalar(self.learning_rate, field="learning_rate", positive=True)
        _finite_scalar(self.kappa_bits, field="kappa_bits", positive=True)
        beta = _finite_scalar(self.beta, field="beta")
        if beta != 0.0:
            raise RelationalLearnerError(
                "beta must be zero because the Q3 head is structurally centred"
            )

    def network_config(self) -> RelationalZRC3NetworkConfig:
        return RelationalZRC3NetworkConfig(
            action_dim=self.action_dim,
            action_context_dim=self.action_context_dim,
            victim_token_dim=self.victim_token_dim,
            hidden_layers=tuple(self.hidden_layers),
            activation=self.activation,
            kappa_bits=float(self.kappa_bits),
        )


class RelationalZRC3PairwiseLearner:
    """One source-only Q3 head with a fixed zero-bootstrap objective."""

    def __init__(
        self,
        config: RelationalZRC3LearnerConfig,
        *,
        train_seed: int,
        device: str = "cpu",
    ) -> None:
        if isinstance(train_seed, bool) or not isinstance(train_seed, int):
            raise RelationalLearnerError("train_seed must be an integer")
        if device != "cpu":
            raise RelationalLearnerError("the draft learner is sealed to deterministic CPU execution")
        self.config = config
        self.train_seed = train_seed
        self.device = torch.device("cpu")
        self.update_count = 0
        torch.manual_seed(train_seed)
        self.q3 = RelationalZRC3QNetwork(config.network_config()).to(self.device)
        self.optimizer = torch.optim.Adam(
            self.q3.parameters(), lr=float(config.learning_rate)
        )

    def _arrays(
        self,
        source: RelationalZRC3Source | Mapping[str, object],
        indices: Sequence[int] | np.ndarray | None = None,
    ) -> tuple[RelationalZRC3Source, dict[str, np.ndarray]]:
        validated = _as_readonly_source(source)
        if float(validated.kappa_bits).hex() != float(self.config.kappa_bits).hex():
            raise RelationalLearnerError("source kappa_bits disagrees with learner config")
        if indices is None:
            selected = np.arange(validated.rows, dtype=np.int64)
        else:
            raw = np.asarray(indices)
            if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
                raise RelationalLearnerError("indices must be a one-dimensional integer array")
            selected = np.array(raw, dtype=np.int64, copy=True)
            if selected.size == 0 or np.any(selected < 0) or np.any(selected >= validated.rows):
                raise RelationalLearnerError("indices must select at least one source row")
        arrays = {
            name: np.asarray(getattr(validated, name))[selected]
            for name in (
                "action_context",
                "victim_tokens",
                "action_mask",
                "victim_mask",
                "positive_credit_compatible",
                "reference_actions",
                "target_surface_bits",
            )
        }
        return validated, arrays

    def _surface_loss(
        self,
        arrays: Mapping[str, np.ndarray],
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, int]:
        action_context = torch.tensor(arrays["action_context"], dtype=torch.float32, device=self.device)
        victim_tokens = torch.tensor(arrays["victim_tokens"], dtype=torch.float32, device=self.device)
        action_mask = torch.tensor(arrays["action_mask"], dtype=torch.bool, device=self.device)
        victim_mask = torch.tensor(arrays["victim_mask"], dtype=torch.bool, device=self.device)
        compatible = torch.tensor(arrays["positive_credit_compatible"], dtype=torch.bool, device=self.device)
        references = torch.tensor(arrays["reference_actions"], dtype=torch.int64, device=self.device)
        targets = torch.tensor(
            arrays["target_surface_bits"], dtype=torch.float32, device=self.device
        ) / float(self.config.kappa_bits)
        surface = self.q3(
            action_context,
            victim_tokens,
            action_mask,
            victim_mask,
            compatible,
            references,
        )
        rows = torch.arange(surface.shape[0], device=self.device)
        q_reference = surface[rows, references]
        target_reference = targets[rows, references]
        residual = surface - q_reference[:, None] - (
            targets - target_reference[:, None]
        )
        comparisons = action_mask.clone()
        comparisons[rows, references] = False
        if not bool(torch.any(comparisons)):
            raise RelationalLearnerError("source batch contains no non-reference comparison")
        pair_mse = torch.mean(residual[comparisons].square())
        # The forward head fixes the gauge structurally by subtracting the
        # reference action before returning.  Retain this diagnostic to detect
        # a head regression, but do not pretend that a redundant penalty trains
        # an already exact-zero quantity.
        gauge_mse = torch.mean(q_reference[:, None].expand_as(surface)[comparisons].square())
        loss = pair_mse
        return loss, pair_mse, gauge_mse, int(torch.count_nonzero(comparisons))

    @staticmethod
    def _finite_parameters(module: nn.Module) -> None:
        for parameter in module.parameters():
            if not bool(torch.isfinite(parameter).all()):
                raise RelationalLearnerError("learner parameters became non-finite")
            if parameter.grad is not None and not bool(torch.isfinite(parameter.grad).all()):
                raise RelationalLearnerError("learner gradients became non-finite")

    def measure(
        self,
        source: RelationalZRC3Source | Mapping[str, object],
        *,
        indices: Sequence[int] | np.ndarray | None = None,
    ) -> dict[str, float | int]:
        _validated, arrays = self._arrays(source, indices)
        self.q3.eval()
        with torch.no_grad():
            loss, pair_mse, gauge_mse, comparisons = self._surface_loss(arrays)
        return {
            "batch_size": comparisons,
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
            "update_count": self.update_count,
        }

    def update(
        self,
        source: RelationalZRC3Source | Mapping[str, object],
        *,
        indices: Sequence[int] | np.ndarray | None = None,
    ) -> dict[str, float | int]:
        _validated, arrays = self._arrays(source, indices)
        self.q3.train()
        loss, pair_mse, gauge_mse, comparisons = self._surface_loss(arrays)
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if not bool(torch.isfinite(loss)):
            raise RelationalLearnerError("learner loss became non-finite")
        self._finite_parameters(self.q3)
        self.optimizer.step()
        self._finite_parameters(self.q3)
        self.update_count += 1
        return {
            "batch_size": comparisons,
            "loss": float(loss.detach().cpu()),
            "pair_mse": float(pair_mse.detach().cpu()),
            "gauge_mse": float(gauge_mse.detach().cpu()),
            "update_count": self.update_count,
        }

    def q_values(self, source: RelationalZRC3Source | Mapping[str, object]) -> np.ndarray:
        _validated, arrays = self._arrays(source)
        tensors = {
            "action_context": torch.tensor(arrays["action_context"], dtype=torch.float32, device=self.device),
            "victim_tokens": torch.tensor(arrays["victim_tokens"], dtype=torch.float32, device=self.device),
            "action_mask": torch.tensor(arrays["action_mask"], dtype=torch.bool, device=self.device),
            "victim_mask": torch.tensor(arrays["victim_mask"], dtype=torch.bool, device=self.device),
            "positive_credit_compatible": torch.tensor(arrays["positive_credit_compatible"], dtype=torch.bool, device=self.device),
            "reference_actions": torch.tensor(arrays["reference_actions"], dtype=torch.int64, device=self.device),
        }
        self.q3.eval()
        with torch.no_grad():
            values = self.q3(**tensors)
        return values.cpu().numpy()

    def parameter_sha256(self) -> str:
        return _state_digest(self.q3.state_dict())

    def checkpoint_state(
        self,
        *,
        contract_sha256: str,
        source_sha256: str,
        code_manifest_sha256: str,
    ) -> dict[str, Any]:
        if self.update_count != REQUIRED_CHECKPOINT_UPDATES:
            raise RelationalLearnerError(
                f"checkpoint requires exactly {REQUIRED_CHECKPOINT_UPDATES} updates"
            )
        contract = _digest(contract_sha256, field="contract_sha256")
        source = _digest(source_sha256, field="source_sha256")
        code_manifest = _digest(
            code_manifest_sha256, field="code_manifest_sha256"
        )
        q_state = {name: tensor.detach().cpu().clone() for name, tensor in self.q3.state_dict().items()}
        optimizer_state = self.optimizer.state_dict()
        return {
            "schema": CHECKPOINT_SCHEMA,
            "format_version": CHECKPOINT_VERSION,
            "algorithm": RELATIONAL_ZR_C3_LEARNER_ALGORITHM,
            "head_algorithm": RELATIONAL_ZR_C3_HEAD_ALGORITHM,
            "head_version": RELATIONAL_ZR_C3_HEAD_VERSION,
            "config": asdict(self.config),
            "train_seed": self.train_seed,
            "update_count": self.update_count,
            "contract_sha256": contract,
            "source_sha256": source,
            "code_manifest_sha256": code_manifest,
            "test_split_opened": False,
            "episode_training": False,
            "parameter_sha256": _state_digest(q_state),
            "q3": q_state,
            "optimizer": optimizer_state,
        }

    def save_checkpoint(
        self,
        path: str | Path,
        *,
        contract_sha256: str,
        source_sha256: str,
        code_manifest_sha256: str,
    ) -> dict[str, str]:
        destination = Path(path)
        if destination.exists() or destination.is_symlink():
            raise RelationalLearnerError(f"refusing to overwrite checkpoint: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = self.checkpoint_state(
            contract_sha256=contract_sha256,
            source_sha256=source_sha256,
            code_manifest_sha256=code_manifest_sha256,
        )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            torch.save(payload, temporary)
            os.link(temporary, destination)
        except FileExistsError as error:
            raise RelationalLearnerError(f"refusing to overwrite checkpoint: {destination}") from error
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "path": str(destination),
            "parameter_sha256": str(payload["parameter_sha256"]),
            "checkpoint_sha256": _file_sha256(destination),
        }

    def load_checkpoint_state(
        self,
        payload: Mapping[str, Any],
        *,
        contract_sha256: str,
        source_sha256: str,
        code_manifest_sha256: str,
    ) -> int:
        if not isinstance(payload, Mapping):
            raise RelationalLearnerError("checkpoint must be a mapping")
        contract = _digest(contract_sha256, field="contract_sha256")
        source = _digest(source_sha256, field="source_sha256")
        code_manifest = _digest(
            code_manifest_sha256, field="code_manifest_sha256"
        )
        expected = {
            "schema": CHECKPOINT_SCHEMA,
            "format_version": CHECKPOINT_VERSION,
            "algorithm": RELATIONAL_ZR_C3_LEARNER_ALGORITHM,
            "head_algorithm": RELATIONAL_ZR_C3_HEAD_ALGORITHM,
            "head_version": RELATIONAL_ZR_C3_HEAD_VERSION,
            "config": asdict(self.config),
            "train_seed": self.train_seed,
            "contract_sha256": contract,
            "source_sha256": source,
            "code_manifest_sha256": code_manifest,
            "test_split_opened": False,
            "episode_training": False,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise RelationalLearnerError(f"checkpoint {key} mismatch")
        update_count = payload.get("update_count")
        if update_count != REQUIRED_CHECKPOINT_UPDATES:
            raise RelationalLearnerError(
                f"checkpoint update_count must be exactly {REQUIRED_CHECKPOINT_UPDATES}"
            )
        q_state = payload.get("q3")
        optimizer_state = payload.get("optimizer")
        parameter_digest = _digest(payload.get("parameter_sha256"), field="parameter_sha256")
        if not isinstance(q_state, Mapping) or not isinstance(optimizer_state, Mapping):
            raise RelationalLearnerError("checkpoint q3/optimizer state is malformed")
        if _state_digest(q_state) != parameter_digest:
            raise RelationalLearnerError("checkpoint parameter digest disagrees with q3 state")
        try:
            self.q3.load_state_dict(q_state, strict=True)
            self.optimizer.load_state_dict(optimizer_state)
        except (KeyError, TypeError, ValueError, RuntimeError) as error:
            raise RelationalLearnerError("malformed relational Q3 checkpoint") from error
        self._finite_parameters(self.q3)
        self.update_count = update_count
        return update_count

    def load_checkpoint(
        self,
        path: str | Path,
        *,
        contract_sha256: str,
        source_sha256: str,
        code_manifest_sha256: str,
    ) -> int:
        checkpoint = Path(path)
        if checkpoint.is_symlink() or not checkpoint.is_file():
            raise RelationalLearnerError(f"expected a regular checkpoint file: {checkpoint}")
        try:
            payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        except (OSError, EOFError, RuntimeError, ValueError, TypeError) as error:
            raise RelationalLearnerError("checkpoint could not be decoded") from error
        return self.load_checkpoint_state(
            payload,
            contract_sha256=contract_sha256,
            source_sha256=source_sha256,
            code_manifest_sha256=code_manifest_sha256,
        )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


__all__ = [
    "CHECKPOINT_SCHEMA",
    "CHECKPOINT_VERSION",
    "REQUIRED_CHECKPOINT_UPDATES",
    "RelationalLearnerError",
    "RelationalZRC3LearnerConfig",
    "RelationalZRC3PairwiseLearner",
    "canonical_sha256",
]
