"""Read-only runtime bridge for the current V0.23 d40 Q1/Q2 checkpoint.

The V0.23 target generator and the historical C2 temporal backend expose
different inference interfaces.  The source adapter already owns the
authenticated d40 load and the native Q1+Q2 surface; this module supplies the
small compatibility seam needed by the legacy backend without changing its
formula, chronology, or authority files.

This adapter is intentionally launch-lane local.  It never trains, writes a
replay, updates a network, opens a simulator, or falls back to the legacy e6
checkpoint.  The backend hook delegates every non-d40 trainer to the original
implementation unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np


D40_CHECKPOINT_SCHEMA = "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-checkpoint"
D40_CHECKPOINT_SHA256 = "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
D40_LINEAGE = 2026092101
D40_Q2_INITIALIZATION = 2026108101
D40_Q1_UPDATE_COUNT = 10
D40_Q2_UPDATE_COUNT = 3000
D40_Q1_STATE_DIM = 228
D40_Q2_STATE_DIM = 448
D40_ACTION_DIM = 28
D40_STATE_DIM = 112
D40_ADAPTER_SCHEMA = "multi-catfish-mcrl-v023-d40-q1-q2-runtime-adapter-v1"


class D40AdapterError(RuntimeError):
    """The d40 runtime compatibility seam failed closed."""


def _sha256_file(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise D40AdapterError(f"expected regular checkpoint file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise D40AdapterError(f"{field} must be a lowercase SHA-256 digest")
    return value


def authenticate_d40_checkpoint(
    path: Path, *, expected_sha256: str = D40_CHECKPOINT_SHA256
) -> dict[str, Any]:
    """Authenticate the copied d40 checkpoint and its schema metadata.

    The function is deliberately independent of the simulator.  It is used by
    the target generator as a second local binding check and by the isolated
    copied-bundle test.  Weight tensors are not reconstructed here; the
    canonical V0.20 loader remains responsible for loading the two frozen
    heads after its own authority checks.
    """

    expected = _require_sha256(expected_sha256, field="expected_sha256")
    source = Path(path)
    actual = _sha256_file(source)
    if actual != expected:
        raise D40AdapterError(
            f"d40 checkpoint hash mismatch: expected {expected}, got {actual}"
        )
    try:
        import torch  # noqa: PLC0415

        payload = torch.load(source, map_location="cpu", weights_only=False)
    except Exception as error:  # pragma: no cover - torch I/O error is environment-specific
        raise D40AdapterError("d40 checkpoint is not readable") from error
    if not isinstance(payload, Mapping):
        raise D40AdapterError("d40 checkpoint root is not a mapping")
    expected_top = {
        "schema": D40_CHECKPOINT_SCHEMA,
        "lineage": D40_LINEAGE,
        "q2_initialization": D40_Q2_INITIALIZATION,
        "q1_update_count": D40_Q1_UPDATE_COUNT,
        "q2_update_count": D40_Q2_UPDATE_COUNT,
        "q1_head_index": 0,
        "test_split_opened": False,
        "simulator_run": False,
        "episode_training": False,
    }
    for field, expected_value in expected_top.items():
        if payload.get(field) != expected_value:
            raise D40AdapterError(
                f"d40 checkpoint metadata drifted at {field}: "
                f"expected {expected_value!r}, got {payload.get(field)!r}"
            )
    q1 = payload.get("q1")
    q2 = payload.get("q2")
    if not isinstance(q1, Mapping) or not isinstance(q2, Mapping):
        raise D40AdapterError("d40 checkpoint lacks Q1/Q2 mappings")
    q1_config = q1.get("config")
    q2_config = q2.get("config")
    if not isinstance(q1_config, Mapping) or not isinstance(q2_config, Mapping):
        raise D40AdapterError("d40 Q1/Q2 configs are malformed")
    if (
        q1_config.get("state_dim") != D40_Q1_STATE_DIM
        or q1_config.get("action_dim") != D40_ACTION_DIM
        or q2_config.get("local_feature_dim") != 16
        or q2_config.get("global_feature_dim") != 0
        or q2_config.get("action_dim") != D40_ACTION_DIM
    ):
        raise D40AdapterError("d40 Q1/Q2 model dimensions drifted")
    if not isinstance(q1.get("q_networks"), Sequence) or len(q1["q_networks"]) != 3:
        raise D40AdapterError("d40 Q1 checkpoint must contain the three frozen heads")
    if not isinstance(q2.get("q"), Mapping):
        raise D40AdapterError("d40 Q2 checkpoint lacks its action-set head")
    return {
        "schema": D40_ADAPTER_SCHEMA,
        "checkpoint_schema": D40_CHECKPOINT_SCHEMA,
        "checkpoint_path": str(source.resolve()),
        "checkpoint_sha256": actual,
        "lineage": D40_LINEAGE,
        "q2_initialization": D40_Q2_INITIALIZATION,
        "q1_update_count": D40_Q1_UPDATE_COUNT,
        "q2_update_count": D40_Q2_UPDATE_COUNT,
        "q1_state_dim": D40_Q1_STATE_DIM,
        "q2_state_dim": D40_Q2_STATE_DIM,
        "simulator_run": False,
        "episode_training": False,
    }


@dataclass(frozen=True)
class D40CheckpointRuntimeAdapter:
    """Expose d40 native Q1+Q2 inference through the C2 backend seam."""

    source_adapter: Any
    v018: Any
    q1: Any
    q2: Any
    model_digest: str
    checkpoint_sha256: str

    def __post_init__(self) -> None:
        _require_sha256(self.checkpoint_sha256, field="checkpoint_sha256")
        _require_sha256(self.model_digest, field="model_digest")
        if self.checkpoint_sha256 != D40_CHECKPOINT_SHA256:
            raise D40AdapterError("runtime checkpoint is not the binding d40 digest")
        object.__setattr__(
            self,
            "config",
            SimpleNamespace(
                # This is metadata consumed by the legacy anchor payload.  The
                # actual scores below are the canonical d40 Q1+Q2 surface.
                objective_weights=(1.0, 1.0, 0.0),
                snr_encoding="log1p",
                theta_encoding="raw_radians",
                offset_scale_km=100.0,
                load_normalization="divide_by_num_users",
                state_dim=D40_STATE_DIM,
                action_dim=D40_ACTION_DIM,
                checkpoint_schema=D40_CHECKPOINT_SCHEMA,
            ),
        )
        # Existing read-only network snapshot helpers only require q_nets.
        # Keeping the two frozen modules visible also makes accidental mutation
        # checks cover both d40 heads.
        object.__setattr__(self, "q_nets", (self.q1, self.q2))
        object.__setattr__(
            self,
            "checkpoint_receipt",
            {
                "schema": D40_ADAPTER_SCHEMA,
                "checkpoint_schema": D40_CHECKPOINT_SCHEMA,
                "checkpoint_sha256": self.checkpoint_sha256,
                "lineage": D40_LINEAGE,
                "q2_initialization": D40_Q2_INITIALIZATION,
                "q1_update_count": D40_Q1_UPDATE_COUNT,
                "q2_update_count": D40_Q2_UPDATE_COUNT,
            },
        )

    def encode_states(self, states: Sequence[Any]) -> np.ndarray:
        """Encode live UserState rows exactly as the 112-D observation block."""

        from mcrl.runtime.state_encoding import encode_state  # noqa: PLC0415

        rows = np.asarray(
            [
                encode_state(state, len(states), self.config)
                for state in states
            ],
            dtype=np.float32,
        )
        if rows.shape != (len(states), D40_STATE_DIM) or not np.all(np.isfinite(rows)):
            raise D40AdapterError("d40 live state encoder did not produce U-by-112")
        return rows

    def main_actions_for_branch(
        self, branch: Any, *, physical_vector: Any
    ) -> tuple[np.ndarray, tuple[Any, ...]]:
        """Return the source adapter's authenticated d40 Q1+Q2 argmax."""

        users = len(branch.states)
        data = self.source_adapter._native_q12_anchor(
            v018=self.v018,
            q1=self.q1,
            q2=self.q2,
            step_env=branch.wrapped.environment,
            observation=branch.observation,
            model_digest=self.model_digest,
        )
        q12 = np.asarray(data.get("q12"), dtype=np.float32)
        masks = np.asarray(data.get("masks"))
        if (
            q12.shape != (users, D40_ACTION_DIM)
            or masks.dtype != np.bool_
            or masks.shape != q12.shape
            or not np.all(np.isfinite(q12))
            or not np.all(np.any(masks, axis=1))
        ):
            raise D40AdapterError("d40 native Q1+Q2 surface is malformed")
        actions = np.argmax(np.where(masks, q12, -np.inf), axis=1).astype(np.int32)
        physical = physical_vector(actions.tolist(), branch.observation, users=users)
        return actions, tuple(physical)


def install_backend_hook(backend_module: Any) -> None:
    """Install the launch-local d40 dispatch while preserving legacy callers."""

    marker = "_mcrl_v023_d40_backend_hook"
    if getattr(backend_module, marker, False):
        return
    original = backend_module._main_actions

    def _main_actions(trainer: Any, branch: Any):
        if isinstance(trainer, D40CheckpointRuntimeAdapter):
            return trainer.main_actions_for_branch(
                branch, physical_vector=backend_module._physical_vector
            )
        return original(trainer, branch)

    backend_module._main_actions = _main_actions
    setattr(backend_module, marker, True)


__all__ = [
    "D40_ADAPTER_SCHEMA",
    "D40AdapterError",
    "D40CheckpointRuntimeAdapter",
    "D40_CHECKPOINT_SCHEMA",
    "D40_CHECKPOINT_SHA256",
    "authenticate_d40_checkpoint",
    "install_backend_hook",
]
