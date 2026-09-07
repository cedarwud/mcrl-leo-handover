"""Read-only adapter for the authenticated pre-Catfish Main MODQN policy.

This module deliberately owns only checkpoint admission, native state
encoding, and deployment-time action selection.  It does not construct a
trainer, an optimizer, an environment, or any training state.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np
import torch

from mcrl.env.action_contract import NO_OP_ACTION
from mcrl.env.step_types import ActionMask, UserState
from mcrl.runtime.q_network import DQNNetwork
from mcrl.runtime.state_encoding import encode_state


class BaselineAdapterError(RuntimeError):
    """Raised when a protected baseline input is missing or has drifted."""


EXPECTED_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
EXPECTED_STATE_DIM = 112
EXPECTED_ACTION_DIM = 28
EXPECTED_EPISODES = 9000
EXPECTED_CHECKPOINT_EPISODE = EXPECTED_EPISODES - 1
EXPECTED_HIDDEN_LAYERS = (100, 50, 50)
EXPECTED_ACTIVATION = "tanh"
EXPECTED_OBJECTIVE_WEIGHTS = (0.5, 0.3, 0.2)

_REPO_ROOT = Path(__file__).absolute().parents[2]
DEFAULT_CHECKPOINT_PATH = (
    _REPO_ROOT
    / "artifacts"
    / "training-2026-08-25-rerun01"
    / "main"
    / "final-checkpoint.pt"
)
DEFAULT_STATUS_PATH = DEFAULT_CHECKPOINT_PATH.with_name("status.json")

EXPECTED_CHECKPOINT_RULE = MappingProxyType(
    {
        "assumption_id": "ASSUME-MODQN-REP-015",
        "primary_report": "final-episode-policy",
        "secondary_report": "best-weighted-reward-on-eval",
        "secondary_implemented": False,
        "secondary_status": (
            "not-yet-implemented: no eval loop / best-eval checkpoint in this training run"
        ),
    }
)

# This is the complete resolved trainer_config carried by the authenticated
# checkpoint.  Keeping the expected mapping here prevents a future loader
# from silently accepting a different state transform, objective row, or run
# protocol while still reusing the same network dimensions.
EXPECTED_TRAINER_CONFIG = MappingProxyType(
    {
        "hidden_layers": (100, 50, 50),
        "activation": "tanh",
        "learning_rate": 0.001,
        "discount_factor": 0.9,
        "batch_size": 128,
        "episodes": 9000,
        "objective_weights": (0.5, 0.3, 0.2),
        "epsilon_start": 1.0,
        "epsilon_end": 0.01,
        "epsilon_decay_episodes": 2000,
        "target_update_every_episodes": 50,
        "replay_capacity": 50000,
        "policy_sharing_mode": "shared",
        "snr_encoding": "log1p",
        "theta_encoding": "raw_radians",
        "offset_scale_km": 100.0,
        "load_normalization": "divide_by_num_users",
        "checkpoint_assumption_id": "ASSUME-MODQN-REP-015",
        "checkpoint_primary_report": "final-episode-policy",
        "checkpoint_secondary_report": "best-weighted-reward-on-eval",
        "training_experiment_kind": "baseline",
        "training_experiment_id": "",
        "method_family": "MODQN-baseline",
        "phase": "baseline",
        "comparison_role": "not-applicable",
        "r1_reward_label": "system-energy-efficiency",
        "r1_reward_provenance": "paper eq. (3.25): r1 = sum_{s,v} x * eta",
        "reward_calibration_enabled": True,
        "reward_calibration_mode": "divide-by-fixed-scales",
        "reward_calibration_source": "probe-P3-and-analytic-bound",
        "reward_calibration_scales": (2029238.4328742754, 1.0, 6.0),
        "reward_normalization_mode": "raw-unscaled",
        "load_balance_calibration_mode": "baseline-paper-weight",
        "device": "cpu",
    }
)

_EXPECTED_PAYLOAD_KEYS = frozenset(
    {
        "format_version",
        "checkpoint_kind",
        "episode",
        "train_seed",
        "env_seed",
        "mobility_seed",
        "state_dim",
        "action_dim",
        "trainer_config",
        "checkpoint_rule",
        "q_networks",
        "target_networks",
        "optimizers",
        "last_episode_log",
    }
)
_NETWORK_STATE_SHAPES = MappingProxyType(
    {
        "net.0.weight": (100, 112),
        "net.0.bias": (100,),
        "net.2.weight": (50, 100),
        "net.2.bias": (50,),
        "net.4.weight": (50, 50),
        "net.4.bias": (50,),
        "net.6.weight": (28, 50),
        "net.6.bias": (28,),
    }
)
_EXPECTED_RUN_FINGERPRINT = MappingProxyType(
    {
        "environment_seed": 1337,
        "learning_rate": 0.001,
        "mobility_seed": 7,
        "role": "main-training",
        "train_seed": 42,
    }
)
_EXPECTED_TRAINER_CONFIG_SHA256 = (
    "b69f6f46add80619178a650026b5de2fae8402f2bb9f809995727ac580a2d654"
)


@dataclass(frozen=True, slots=True)
class _EncodingConfig:
    """The state-encoding subset copied from the admitted checkpoint config."""

    snr_encoding: str
    theta_encoding: str
    offset_scale_km: float
    load_normalization: str


def _exact_value(actual: Any, expected: Any) -> bool:
    """Compare nested checkpoint values without coercing types."""

    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            return False
        if set(actual) != set(expected):
            return False
        return all(_exact_value(actual[key], expected[key]) for key in expected)
    if isinstance(expected, tuple):
        return (
            type(actual) is tuple
            and len(actual) == len(expected)
            and all(_exact_value(a, e) for a, e in zip(actual, expected))
        )
    if type(actual) is not type(expected):
        return False
    return actual == expected


def _read_regular_file(path: str | Path, *, label: str) -> bytes:
    """Read one regular, non-symlink file through a no-follow descriptor."""

    candidate = Path(path)
    absolute = Path(os.path.abspath(candidate))
    resolved = Path(os.path.realpath(candidate))
    if resolved != absolute:
        raise BaselineAdapterError(f"{label} path contains a symlink: {candidate}")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(os.fspath(candidate), flags)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise BaselineAdapterError(f"{label} must be a regular file: {candidate}")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            return stream.read()
    except BaselineAdapterError:
        raise
    except OSError as exc:
        raise BaselineAdapterError(f"could not read {label}: {candidate}") from exc
    finally:
        if descriptor != -1:
            os.close(descriptor)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _parse_status(status_bytes: bytes) -> dict[str, Any]:
    try:
        status = json.loads(
            status_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise BaselineAdapterError("status.json is not strict UTF-8 JSON") from exc
    if type(status) is not dict:
        raise BaselineAdapterError("status.json root must be an object")
    return status


def _require_exact_field(
    mapping: Mapping[str, Any], field: str, expected: Any, *, label: str
) -> None:
    if field not in mapping or not _exact_value(mapping[field], expected):
        actual = mapping.get(field, "<missing>")
        raise BaselineAdapterError(
            f"{label}.{field} drifted: expected {expected!r}, got {actual!r}"
        )


def _validate_status(
    status: Mapping[str, Any], *, checkpoint_path: Path
) -> None:
    """Admit only the completed 9000-episode Main status receipt."""

    for field, expected in (
        ("status", "complete"),
        ("episodes_completed", EXPECTED_EPISODES),
        ("checkpoint_sha256", EXPECTED_CHECKPOINT_SHA256),
        ("role", "main-training"),
        ("resumed", False),
        ("resume_next_episode", EXPECTED_EPISODES),
    ):
        _require_exact_field(status, field, expected, label="status")

    checkpoint_ref = status.get("checkpoint")
    if type(checkpoint_ref) is not str:
        raise BaselineAdapterError("status.checkpoint must be a string")
    if Path(checkpoint_ref).name != checkpoint_path.name:
        raise BaselineAdapterError(
            "status.checkpoint does not identify the requested final checkpoint"
        )

    collapse_summary = status.get("collapse_summary")
    if not isinstance(collapse_summary, Mapping):
        raise BaselineAdapterError("status.collapse_summary must be an object")
    _require_exact_field(
        collapse_summary,
        "episodes",
        EXPECTED_EPISODES,
        label="status.collapse_summary",
    )

    fingerprint = status.get("run_fingerprint")
    if not isinstance(fingerprint, Mapping):
        raise BaselineAdapterError("status.run_fingerprint must be an object")
    _require_exact_field(
        fingerprint,
        "trainer_config_sha256",
        _EXPECTED_TRAINER_CONFIG_SHA256,
        label="status.run_fingerprint",
    )
    run = fingerprint.get("run")
    if not isinstance(run, Mapping) or not _exact_value(
        run, _EXPECTED_RUN_FINGERPRINT
    ):
        raise BaselineAdapterError("status.run_fingerprint.run drifted")


def _validate_network_state(state: Any, *, label: str) -> None:
    if not isinstance(state, Mapping):
        raise BaselineAdapterError(f"{label} must be a state mapping")
    if set(state) != set(_NETWORK_STATE_SHAPES):
        raise BaselineAdapterError(f"{label} keys do not match 112x28 DQN")
    for key, expected_shape in _NETWORK_STATE_SHAPES.items():
        tensor = state[key]
        if not isinstance(tensor, torch.Tensor):
            raise BaselineAdapterError(f"{label}.{key} is not a tensor")
        if tensor.dtype is not torch.float32:
            raise BaselineAdapterError(
                f"{label}.{key} dtype drifted: expected torch.float32, "
                f"got {tensor.dtype}"
            )
        if tuple(tensor.shape) != expected_shape:
            raise BaselineAdapterError(
                f"{label}.{key} shape drifted: expected {expected_shape}, "
                f"got {tuple(tensor.shape)}"
            )
        if not bool(torch.isfinite(tensor).all().item()):
            raise BaselineAdapterError(f"{label}.{key} contains nonfinite values")


def _validate_payload(payload: Any) -> dict[str, Any]:
    """Validate the complete checkpoint contract before touching a network."""

    if type(payload) is not dict:
        raise BaselineAdapterError("checkpoint root must be a dictionary")
    if set(payload) != _EXPECTED_PAYLOAD_KEYS:
        raise BaselineAdapterError("checkpoint fields drifted from format v1")

    for field, expected in (
        ("format_version", 1),
        ("checkpoint_kind", "final-episode-policy"),
        ("episode", EXPECTED_CHECKPOINT_EPISODE),
        ("train_seed", 42),
        ("env_seed", 1337),
        ("mobility_seed", 7),
        ("state_dim", EXPECTED_STATE_DIM),
        ("action_dim", EXPECTED_ACTION_DIM),
    ):
        _require_exact_field(payload, field, expected, label="checkpoint")

    trainer_config = payload.get("trainer_config")
    if not isinstance(trainer_config, Mapping) or not _exact_value(
        trainer_config, EXPECTED_TRAINER_CONFIG
    ):
        raise BaselineAdapterError("checkpoint.trainer_config drifted")
    if not _exact_value(payload.get("checkpoint_rule"), EXPECTED_CHECKPOINT_RULE):
        raise BaselineAdapterError("checkpoint.checkpoint_rule drifted")

    q_networks = payload.get("q_networks")
    target_networks = payload.get("target_networks")
    if type(q_networks) is not list or len(q_networks) != 3:
        raise BaselineAdapterError("checkpoint must contain exactly three q_networks")
    if type(target_networks) is not list or len(target_networks) != 3:
        raise BaselineAdapterError(
            "checkpoint must contain exactly three target_networks"
        )
    for index, state in enumerate(q_networks):
        _validate_network_state(state, label=f"q_networks[{index}]")
    for index, state in enumerate(target_networks):
        _validate_network_state(state, label=f"target_networks[{index}]")

    optimizers = payload.get("optimizers")
    if type(optimizers) is not list or len(optimizers) != 3:
        raise BaselineAdapterError(
            "checkpoint optimizers field must contain three entries"
        )
    if type(payload.get("last_episode_log")) is not dict:
        raise BaselineAdapterError("checkpoint.last_episode_log must be an object")

    return payload


def _load_payload(checkpoint_bytes: bytes) -> dict[str, Any]:
    try:
        payload = torch.load(
            io.BytesIO(checkpoint_bytes),
            map_location="cpu",
            weights_only=True,
        )
    except Exception as exc:
        raise BaselineAdapterError("checkpoint could not be deserialized") from exc
    return _validate_payload(payload)


def _validate_user_count(num_users: int) -> int:
    if type(num_users) is not int or num_users < 1:
        raise BaselineAdapterError(
            f"num_users must be a positive integer, got {num_users!r}"
        )
    return num_users


def _validate_user_state(user_state: UserState) -> None:
    if not isinstance(user_state, UserState):
        raise BaselineAdapterError(
            f"state must be native UserState, got {type(user_state).__name__}"
        )
    if user_state.contract_fields is not None:
        raise BaselineAdapterError(
            "contract_fields are not part of the native 112-D state"
        )

    arrays = {
        "access_vector": user_state.access_vector,
        "channel_quality": user_state.channel_quality,
        "beam_offsets": user_state.beam_offsets,
        "beam_loads": user_state.beam_loads,
    }
    for field, value in arrays.items():
        if type(value) is not np.ndarray:
            raise BaselineAdapterError(f"state.{field} must be a numpy array")
        if value.shape != (EXPECTED_ACTION_DIM,):
            raise BaselineAdapterError(
                f"state.{field} must have shape ({EXPECTED_ACTION_DIM},), "
                f"got {value.shape}"
            )
        if value.dtype.kind not in "biuf":
            raise BaselineAdapterError(
                f"state.{field} must have a real numeric dtype, got {value.dtype}"
            )
        if not bool(np.isfinite(value).all()):
            raise BaselineAdapterError(f"state.{field} contains nonfinite values")

    access = user_state.access_vector
    if not bool(np.isin(access, (0, 1)).all()):
        raise BaselineAdapterError("state.access_vector must be binary")
    if int(np.count_nonzero(access)) > 1:
        raise BaselineAdapterError("state.access_vector must be one-hot or empty")
    if bool(np.any(user_state.channel_quality < 0)):
        raise BaselineAdapterError("state.channel_quality must be non-negative")
    if bool(np.any(user_state.beam_loads < 0)):
        raise BaselineAdapterError("state.beam_loads must be non-negative")


def _validate_action_mask(action_mask: ActionMask) -> np.ndarray:
    if not isinstance(action_mask, ActionMask):
        raise BaselineAdapterError(
            f"mask must be native ActionMask, got {type(action_mask).__name__}"
        )
    mask = action_mask.mask
    if type(mask) is not np.ndarray or mask.dtype != np.dtype(bool):
        raise BaselineAdapterError("mask must be a boolean numpy array")
    if mask.shape != (EXPECTED_ACTION_DIM,):
        raise BaselineAdapterError(
            f"mask must have shape ({EXPECTED_ACTION_DIM},), got {mask.shape}"
        )
    # An all-false native mask is an outage/no-op decision, not a fallback to
    # action zero.  It is admitted so selection remains identical to MODQN.
    return mask.copy()


class BaselineAdapter:
    """Authenticated, inference-only view of the pre-Catfish Main policy."""

    __slots__ = (
        "_checkpoint_path",
        "_status_path",
        "_checkpoint_sha256",
        "_trainer_config",
        "_encoding_config",
        "_objective_weights",
        "_q_networks",
    )

    def __init__(
        self,
        *,
        checkpoint_path: Path,
        status_path: Path,
        checkpoint_sha256: str,
        trainer_config: Mapping[str, Any],
        q_networks: tuple[torch.nn.Module, ...],
    ) -> None:
        self._checkpoint_path = checkpoint_path
        self._status_path = status_path
        self._checkpoint_sha256 = checkpoint_sha256
        config = dict(trainer_config)
        self._trainer_config = MappingProxyType(config)
        self._encoding_config = _EncodingConfig(
            snr_encoding=config["snr_encoding"],
            theta_encoding=config["theta_encoding"],
            offset_scale_km=config["offset_scale_km"],
            load_normalization=config["load_normalization"],
        )
        self._objective_weights = EXPECTED_OBJECTIVE_WEIGHTS
        self._q_networks = q_networks

    @classmethod
    def from_artifacts(
        cls,
        checkpoint_path: str | Path = DEFAULT_CHECKPOINT_PATH,
        status_path: str | Path = DEFAULT_STATUS_PATH,
    ) -> "BaselineAdapter":
        """Authenticate and load the exact completed Main checkpoint."""

        checkpoint_path = Path(checkpoint_path)
        status_path = Path(status_path)
        checkpoint_bytes = _read_regular_file(
            checkpoint_path, label="checkpoint"
        )
        checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
        if checkpoint_sha256 != EXPECTED_CHECKPOINT_SHA256:
            raise BaselineAdapterError(
                "checkpoint SHA-256 mismatch: expected "
                f"{EXPECTED_CHECKPOINT_SHA256}, got {checkpoint_sha256}"
            )

        status = _parse_status(
            _read_regular_file(status_path, label="status.json")
        )
        _validate_status(status, checkpoint_path=checkpoint_path)
        payload = _load_payload(checkpoint_bytes)

        q_networks: list[torch.nn.Module] = []
        for index, state in enumerate(payload["q_networks"]):
            network = DQNNetwork(
                EXPECTED_STATE_DIM,
                EXPECTED_ACTION_DIM,
                EXPECTED_HIDDEN_LAYERS,
                EXPECTED_ACTIVATION,
            )
            try:
                network.load_state_dict(state, strict=True)
            except (RuntimeError, TypeError) as exc:
                raise BaselineAdapterError(
                    f"q_networks[{index}] failed strict loading"
                ) from exc
            network.eval()
            for parameter in network.parameters():
                parameter.requires_grad_(False)
            q_networks.append(network)

        return cls(
            checkpoint_path=checkpoint_path,
            status_path=status_path,
            checkpoint_sha256=checkpoint_sha256,
            trainer_config=payload["trainer_config"],
            q_networks=tuple(q_networks),
        )

    @property
    def checkpoint_sha256(self) -> str:
        return self._checkpoint_sha256

    @property
    def checkpoint_path(self) -> Path:
        return self._checkpoint_path

    @property
    def status_path(self) -> Path:
        return self._status_path

    @property
    def trainer_config(self) -> Mapping[str, Any]:
        return self._trainer_config

    @property
    def state_dim(self) -> int:
        return EXPECTED_STATE_DIM

    @property
    def action_dim(self) -> int:
        return EXPECTED_ACTION_DIM

    @property
    def objective_weights(self) -> tuple[float, float, float]:
        return self._objective_weights

    def encode_user_state(
        self, user_state: UserState, *, num_users: int
    ) -> np.ndarray:
        """Encode one native UserState with the admitted checkpoint config."""

        _validate_user_count(num_users)
        _validate_user_state(user_state)
        try:
            encoded = encode_state(
                user_state,
                num_users,
                self._encoding_config,
                include_contract_block=False,
            )
        except Exception as exc:
            raise BaselineAdapterError("native UserState encoding failed") from exc
        encoded = np.asarray(encoded, dtype=np.float32)
        if encoded.shape != (EXPECTED_STATE_DIM,):
            raise BaselineAdapterError(
                f"encoded state must have shape ({EXPECTED_STATE_DIM},), "
                f"got {encoded.shape}"
            )
        if not bool(np.isfinite(encoded).all()):
            raise BaselineAdapterError("encoded state contains nonfinite values")
        return encoded.copy()

    def encode_states(self, states: Sequence[UserState]) -> np.ndarray:
        """Encode a non-empty native state batch using its user count."""

        if not isinstance(states, (list, tuple)) or not states:
            raise BaselineAdapterError("states must be a non-empty list or tuple")
        num_users = len(states)
        encoded = np.stack(
            [
                self.encode_user_state(state, num_users=num_users)
                for state in states
            ],
            axis=0,
        ).astype(np.float32, copy=False)
        if encoded.shape != (num_users, EXPECTED_STATE_DIM):
            raise BaselineAdapterError("encoded state batch shape drifted")
        if not bool(np.isfinite(encoded).all()):
            raise BaselineAdapterError("encoded state batch contains nonfinite values")
        return encoded.copy()

    def _objective_q_values(self, encoded: np.ndarray) -> np.ndarray:
        if encoded.ndim != 2 or encoded.shape[1] != EXPECTED_STATE_DIM:
            raise BaselineAdapterError("encoded state batch is not 112-dimensional")
        if not bool(np.isfinite(encoded).all()):
            raise BaselineAdapterError("encoded state batch contains nonfinite values")

        state_tensor = torch.tensor(encoded, dtype=torch.float32, device="cpu")
        with torch.inference_mode():
            rows = [network(state_tensor) for network in self._q_networks]
        q_values = []
        for index, row in enumerate(rows):
            if tuple(row.shape) != (encoded.shape[0], EXPECTED_ACTION_DIM):
                raise BaselineAdapterError(
                    f"q_networks[{index}] emitted the wrong action dimension"
                )
            array = row.detach().cpu().numpy()
            if not bool(np.isfinite(array).all()):
                raise BaselineAdapterError(
                    f"q_networks[{index}] emitted nonfinite values"
                )
            q_values.append(array)
        return np.stack(q_values, axis=0)

    def _scalarized_q_values(self, encoded: np.ndarray) -> np.ndarray:
        q_values = self._objective_q_values(encoded)
        scalarized = sum(
            weight * q_values[index]
            for index, weight in enumerate(self._objective_weights)
        )
        if not bool(np.isfinite(scalarized).all()):
            raise BaselineAdapterError("scalarized Q values are nonfinite")
        return scalarized

    @staticmethod
    def _masked_argmax(scalarized_row: np.ndarray, mask: np.ndarray) -> int:
        valid = np.flatnonzero(mask)
        if valid.size == 0:
            return int(NO_OP_ACTION)
        masked = scalarized_row.copy()
        masked[~mask] = -np.inf
        if not bool(np.isfinite(masked[mask]).all()):
            raise BaselineAdapterError("valid masked scalarized Q is nonfinite")
        # This is MODQN's original weighted masked argmax: invalid actions are
        # -inf and numpy's argmax supplies the lowest-index tie break.
        return int(np.argmax(masked))

    def select_action(
        self,
        user_state: UserState,
        action_mask: ActionMask,
        *,
        num_users: int,
    ) -> int:
        """Select one greedy masked action, or the native no-op sentinel."""

        encoded = self.encode_user_state(user_state, num_users=num_users)
        mask = _validate_action_mask(action_mask)
        scalarized = self._scalarized_q_values(encoded[None, :])
        return self._masked_argmax(scalarized[0], mask)

    def select_actions(
        self,
        states: Sequence[UserState],
        masks: Sequence[ActionMask],
    ) -> np.ndarray:
        """Select the original weighted masked argmax for each native user."""

        if not isinstance(masks, (list, tuple)):
            raise BaselineAdapterError("masks must be a list or tuple")
        if len(states) != len(masks):
            raise BaselineAdapterError(
                f"state/mask count mismatch: {len(states)} != {len(masks)}"
            )
        encoded = self.encode_states(states)
        validated_masks = [_validate_action_mask(mask) for mask in masks]
        scalarized = self._scalarized_q_values(encoded)
        actions = np.empty(len(validated_masks), dtype=np.int64)
        for index, mask in enumerate(validated_masks):
            actions[index] = self._masked_argmax(scalarized[index], mask)
        return actions


__all__ = [
    "BaselineAdapter",
    "BaselineAdapterError",
    "DEFAULT_CHECKPOINT_PATH",
    "DEFAULT_STATUS_PATH",
    "EXPECTED_ACTION_DIM",
    "EXPECTED_ACTIVATION",
    "EXPECTED_CHECKPOINT_SHA256",
    "EXPECTED_EPISODES",
    "EXPECTED_HIDDEN_LAYERS",
    "EXPECTED_OBJECTIVE_WEIGHTS",
    "EXPECTED_STATE_DIM",
    "EXPECTED_TRAINER_CONFIG",
]
