#!/usr/bin/env python3
"""Small, pinned checkpoint identity boundary for the R7 500-EP route."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import torch


class R7500CheckpointError(ValueError):
    """Raised when a checkpoint does not match its declared R7 identity."""


def canonical_json_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as error:
        raise R7500CheckpointError("value cannot form a canonical JSON identity") from error
    return hashlib.sha256(encoded).hexdigest()


def _same_float(value: Any, expected: float) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and math.isclose(float(value), expected, rel_tol=0.0, abs_tol=1e-15)
    )


def _digest_state_value(digest: Any, value: Any) -> None:
    if isinstance(value, Mapping):
        digest.update(b"{")
        for key in sorted(value, key=str):
            digest.update(str(key).encode("utf-8"))
            digest.update(b"\0")
            _digest_state_value(digest, value[key])
        digest.update(b"}")
        return
    if isinstance(value, (list, tuple)):
        digest.update(b"[")
        for item in value:
            _digest_state_value(digest, item)
        digest.update(b"]")
        return
    if hasattr(value, "detach") and hasattr(value, "cpu"):
        array = np.asarray(value.detach().cpu())
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(str(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
        return
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(str(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
        return
    try:
        digest.update(json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError, OverflowError) as error:
        raise R7500CheckpointError(
            f"checkpoint state contains unsupported {type(value).__name__}"
        ) from error


def checkpoint_policy_sha256(payload: Any) -> str:
    networks = getattr(payload, "q_networks", None)
    if not isinstance(networks, list) or len(networks) != 3:
        raise R7500CheckpointError(
            "checkpoint must contain exactly three Main Q networks"
        )
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-main-online-policy-v1\0")
    _digest_state_value(digest, networks)
    return digest.hexdigest()


def assert_finite_state(value: Any, *, label: str) -> None:
    if isinstance(value, torch.Tensor):
        if not bool(torch.isfinite(value).all().item()):
            raise R7500CheckpointError(f"{label} contains non-finite tensor values")
        return
    if isinstance(value, np.ndarray):
        if not bool(np.isfinite(value).all()):
            raise R7500CheckpointError(f"{label} contains non-finite array values")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            assert_finite_state(item, label=f"{label}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_finite_state(item, label=f"{label}[{index}]")
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise R7500CheckpointError(f"{label} contains a non-finite scalar")


def validate_checkpoint_payload(
    payload: Any,
    *,
    validated: Mapping[str, Any],
    trainer_config: Mapping[str, Any],
    episode_index: int,
    checkpoint_kind: str,
    label: str,
) -> dict[str, Any]:
    seeds = validated.get("seeds")
    if not isinstance(seeds, Mapping):
        raise R7500CheckpointError(f"{label} validated authority lacks seeds")
    exact = {
        "episode": episode_index,
        "checkpoint_kind": checkpoint_kind,
        "train_seed": seeds.get("training"),
        "env_seed": seeds.get("environment"),
        "mobility_seed": seeds.get("mobility"),
    }
    for field, expected in exact.items():
        if getattr(payload, field, None) != expected:
            raise R7500CheckpointError(f"{label} payload {field} mismatch")
    if (
        type(getattr(payload, "state_dim", None)) is not int
        or payload.state_dim < 1
        or type(getattr(payload, "action_dim", None)) is not int
        or payload.action_dim < 1
    ):
        raise R7500CheckpointError(f"{label} payload dimensions are invalid")
    networks = getattr(payload, "q_networks", None)
    targets = getattr(payload, "target_networks", None)
    optimizers = getattr(payload, "optimizers", None)
    if not isinstance(networks, list) or len(networks) != 3:
        raise R7500CheckpointError(f"{label} must contain exactly three Main Q networks")
    if not isinstance(targets, list) or len(targets) != 3:
        raise R7500CheckpointError(f"{label} must contain exactly three target networks")
    if optimizers is None:
        raise R7500CheckpointError(f"{label} lacks optimizer state")
    payload_config = getattr(payload, "trainer_config", None)
    if not isinstance(payload_config, Mapping):
        raise R7500CheckpointError(f"{label} trainer config is missing")
    if canonical_json_sha256(payload_config) != canonical_json_sha256(trainer_config):
        raise R7500CheckpointError(f"{label} trainer config identity mismatch")
    if not _same_float(payload_config.get("learning_rate"), float(validated["learning_rate"])):
        raise R7500CheckpointError(f"{label} learning rate mismatch")
    for field, value in (
        ("q_networks", networks),
        ("target_networks", targets),
        ("optimizers", optimizers),
    ):
        assert_finite_state(value, label=f"{label}.{field}")
    return {
        "episode_index": episode_index,
        "checkpoint_kind": checkpoint_kind,
        "train_seed": int(payload.train_seed),
        "env_seed": int(payload.env_seed),
        "mobility_seed": int(payload.mobility_seed),
        "state_dim": int(payload.state_dim),
        "action_dim": int(payload.action_dim),
        "trainer_config_sha256": canonical_json_sha256(payload_config),
        "online_policy_sha256": checkpoint_policy_sha256(payload),
        "finite_state": "PASS",
    }


__all__ = [
    "R7500CheckpointError",
    "assert_finite_state",
    "canonical_json_sha256",
    "checkpoint_policy_sha256",
    "validate_checkpoint_payload",
]
