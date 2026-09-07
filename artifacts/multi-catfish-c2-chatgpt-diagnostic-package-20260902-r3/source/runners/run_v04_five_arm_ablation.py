#!/usr/bin/env python3
"""Frozen five-arm V0.4 route-ablation evaluator.

This consumer is deliberately separate from the sealed C3 confirmatory
consumer.  It authenticates the already-confirmed C3 candidate, the frozen
Main checkpoint, and the three gate-selected hybrid checkpoints before
opening a TRAIN-only physical world.  It has explicit ``prepare``, ``run``,
and ``verify`` phases.  ``prepare`` and ``verify`` are receipt-only; only
``run`` may open the TLE view and simulator.

The four Catfish arms use one call to ``q_values_by_route`` followed by a
fixed route sum and one common-mask argmax.  Main is an independent call to
the authoritative source-runner ``_main_decision`` seam.  There is no
training, optimizer step, replay write, coordinator, auction, or TEST path.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Mapping, Sequence
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any, Callable

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_learnability_gate as gate  # noqa: E402
import run_v04_c3_source as source  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_v04_c3_state import (  # noqa: E402
    encode_ee_axis_v04_c3_state,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402


# Frozen five-arm protocol --------------------------------------------------

PREPARE_SCHEMA = "multi-catfish-mcrl-v04-five-arm-ablation-prepare-v1"
PREPARE_SEAL_SCHEMA = "multi-catfish-mcrl-v04-five-arm-ablation-prepare-seal-v1"
CODE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v04-five-arm-ablation-code-manifest-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v04-five-arm-ablation-result-v1"
RESULT_SEAL_SCHEMA = "multi-catfish-mcrl-v04-five-arm-ablation-result-seal-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v04-five-arm-ablation-episode-v1"

STATUS_PREPARED = "PREPARED_NO_EPISODE"
STATUS_COMPLETE = "FIVE_ARM_COMPLETE"
STATUS_CONFIRM = "CONFIRM_MULTI_CATFISH"
STATUS_NOT_CONFIRMED = "MULTI_CATFISH_NOT_ALL_CONFIRMED"

ROUTE_ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3")
ARMS = (*ROUTE_ARMS, "MAIN")
ROUTE_NAMES = ("C1", "C2", "C3")
ACTIVE_ROUTES: dict[str, tuple[str, ...]] = {
    "FULL": ("C1", "C2", "C3"),
    "DROP_C1": ("C2", "C3"),
    "DROP_C2": ("C1", "C3"),
    "DROP_C3": ("C1", "C2"),
}

EVALUATION_SEEDS = tuple(range(2026092601, 2026092631))
INITIALIZATION_SEEDS = tuple(gate.INITIALIZATION_SEEDS)
SELECTED_Q3_RUNG = 100
USERS = 100
STEPS_PER_EPISODE = 10
EVALUATION_SPLIT = "TRAIN"
TEST_SPLIT_OPENED = False
HELD_OUT_EE_EVALUATED = True
EPISODE_TRAINING = False
FIELD_COMPONENT = "V04_FIVE_ARM_ABLATION_V1"
FIELD_KEY_AXES = (FIELD_COMPONENT, "c3_confirm_result_sha256", "evaluation_seed")
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEEDS = {
    "C1": 2026092691,
    "C2": 2026092692,
    "C3": 2026092693,
    "MAIN": 2026092694,
}

EXPECTED_C3_CONFIRM_RESULT_SHA256 = (
    "bb1a46a8a782a5fb6d3c37391c17866ac0dbbb9bcc7c42bd2c9d8a9f0dd396dd"
)
EXPECTED_C3_CONFIRM_RESULT_SEAL_SHA256 = (
    "d569049cf648d5d261306ad27d850755070b851a8aecf723f0ebd60d085ee54b"
)
EXPECTED_PRIOR_SCREEN_RESULT_SHA256 = (
    "ab232f72e562e5a9aa4b68ec8074c5556691ffb1272ae92ec5efd651e76a2177"
)
EXPECTED_PRIOR_SCREEN_RESULT_SEAL_SHA256 = (
    "2a3636733f908a3c68e97b2aba2b63a4d6d5f66993a8dd5857b2e9da2af9450b"
)
EXPECTED_PRIOR_PRIMARY_RECEIPT_SHA256 = (
    "822630c75aaa2681bcda23eb007df62128b818a6fde63d050acfe90c18e1e9d5"
)
EXPECTED_GATE_AUTHORITY_SHA256 = (
    "5c26a4dc87ab8dc791d6e9bc6edfea2cd1a7dca2b7c9de8a04d48f47e696f46c"
)
EXPECTED_GATE_AUTHORITY_FILE_SHA256 = (
    "b62d193a04080f21b6437c6c4af0f998cdff8b1ffa8438b619214f7c00d1f573"
)
EXPECTED_GATE_AUTHORITY_SEAL_FILE_SHA256 = (
    "fa4b4155a569e25f914d977f571c62b04de19c3a5f5d557fc6d57893a58e228e"
)
EXPECTED_GATE_RESULT_SHA256 = (
    "e2548a6f77cea33689b64a5b8aee5bf23e9e2f7be3a0a5893c51bdc8d0ae8379"
)
EXPECTED_GATE_RESULT_SEAL_SHA256 = (
    "d8bd1aa6dd51f79506c4c46e54b44ef85c992bcf866f3545515530f867e847f4"
)
EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "38fd17f534241175c70515a21777b2afc9c8059a44558fc812d5ca861db9bad2"
)
EXPECTED_SCHEDULE_SHA256 = (
    "c9465e60afb2533b59f10106756fdab2b176a90b288f8e6222da9b34fcd8c1d2"
)
EXPECTED_TRAIN_SURFACE_SHA256 = (
    "66c8cefdc57b2383cbf0623f937c4c8614f4f7b83d8b44783d6da8463e431193"
)
EXPECTED_MAIN_STATUS_FILE_SHA256 = (
    "3e980bc8c47087ff313c5f5589dab053e0f52440fff692d0c88153af4cce7fa1"
)
EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256 = (
    "635e375fe04e890d22aed41eebd40c808b41635a2f15bdadfc4e85b5580769f0"
)
EXPECTED_MAIN_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
EXPECTED_HYBRID_FILE_SHA256 = {
    2026092101: "efc460a785194d189d085df794dc47292798b606871587beb36f073f91ea2171",
    2026092102: "019e2160ed7c3802c142a92d4b391d63a0d2e3c0b7cfc0478ab6dbfd0b1178fc",
    2026092103: "c0da537690a1ce1be1992ed62ea1972cf34cd6f86553bbe4e0065fd40d3fe377",
}
EXPECTED_PREREG_FILE_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)

DEFAULT_GATE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-learnability-20260901-r2"
DEFAULT_SOURCE_DIR = REPO / "artifacts" / "multi-catfish-v04-c3-source-20260901-r2"
DEFAULT_C3_CONFIRM_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-confirmatory-20260901-r1"
)
DEFAULT_PRIOR_SCREEN_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-c3-500-update-screen-20260901-r1"
)
DEFAULT_V03_ROOT = (
    REPO / "artifacts" / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
)
DEFAULT_MAIN_DIR = REPO / "artifacts" / "training-2026-08-25-rerun01" / "main"
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_WORK_ORDER = (
    REPO / "docs" / "MULTI-CATFISH-MCRL-V04-FIVE-ARM-ABLATION-PREREG-2026-09-01.md"
)
EXPECTED_WORK_ORDER_SHA256 = (
    "d58224c63e8a09e82b44e455af9c34454596660d15ddd1e91bad1ec4bb5a3eac"
)
DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle").expanduser()
DEFAULT_OUTPUT_DIR = (
    REPO / "artifacts" / "multi-catfish-v04-five-arm-ablation-20260901-r1"
)


class V04FiveArmError(RuntimeError):
    """A frozen five-arm authority, physics, or receipt failed closed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return (
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V04FiveArmError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise V04FiveArmError(f"{field} is not a lowercase SHA-256 digest")
    return value


def _file_sha256(path: Path) -> str:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise V04FiveArmError(f"missing regular artifact: {candidate}")
    digest = hashlib.sha256()
    with candidate.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise V04FiveArmError(f"missing regular JSON artifact: {candidate}")
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V04FiveArmError(f"cannot read canonical JSON: {candidate}") from error
    if not isinstance(payload, dict):
        raise V04FiveArmError(f"JSON payload must be an object: {candidate}")
    if _canonical_bytes(payload) != candidate.read_bytes():
        raise V04FiveArmError(f"JSON artifact is not canonical: {candidate}")
    return payload


def _write_once_json(path: Path, payload: object) -> str:
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise V04FiveArmError(f"refusing to overwrite write-once artifact: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload)
    temporary = destination.with_name(
        f".{destination.name}.tmp-{os.getpid()}-{time.time_ns()}"
    )
    if temporary.exists() or temporary.is_symlink():
        raise V04FiveArmError(f"temporary write path already exists: {temporary}")
    try:
        temporary.write_bytes(encoded)
        if destination.exists() or destination.is_symlink():
            raise V04FiveArmError(f"write-once target appeared: {destination}")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _relative(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(Path(path).resolve())


def _regular_dir(path: Path, *, field: str, basename: str | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_dir():
        raise V04FiveArmError(f"{field} must be a regular directory: {candidate}")
    if basename is not None and candidate.name != basename:
        raise V04FiveArmError(
            f"{field} must have basename {basename!r}, got {candidate.name!r}"
        )
    return candidate


def _require_false(payload: Mapping[str, Any], field: str, *, label: str) -> None:
    if payload.get(field) is not False:
        raise V04FiveArmError(f"{label}.{field} must be exactly false")


def _positive_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 1:
        raise V04FiveArmError(f"{field} must be an integer >= 1")
    return value


def _finite_nonnegative(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V04FiveArmError(f"{field} must be a finite nonnegative number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise V04FiveArmError(f"{field} must be a finite nonnegative number")
    return result


def _array_sha256(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in arrays:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _field_for_seed(evaluation_seed: int) -> KeyedFadingField:
    seed = _positive_int(evaluation_seed, field="evaluation_seed")
    return KeyedFadingField.from_components(
        FIELD_COMPONENT,
        EXPECTED_C3_CONFIRM_RESULT_SHA256,
        seed,
    )


def common_field_receipt(evaluation_seed: int) -> dict[str, Any]:
    field = _field_for_seed(evaluation_seed)
    return {
        "components": [FIELD_COMPONENT, EXPECTED_C3_CONFIRM_RESULT_SHA256, int(evaluation_seed)],
        "excluded_components": ["initialization_seed", "policy_label"],
        "root_digest": field.root_digest,
    }


def route_actions(
    trainer: Any,
    states_v03: np.ndarray,
    states_v04: np.ndarray,
    masks: np.ndarray,
    policy_label: str,
) -> np.ndarray:
    """Return one route-set action vector from one Q-surface call."""

    if policy_label not in ROUTE_ARMS:
        raise V04FiveArmError(f"unsupported route arm: {policy_label}")
    surfaces = trainer.q_values_by_route(states_v03, states_v04, masks)
    if not isinstance(surfaces, tuple) or len(surfaces) != len(ROUTE_NAMES):
        raise V04FiveArmError("q_values_by_route must return exactly three surfaces")
    arrays = tuple(np.asarray(surface) for surface in surfaces)
    if any(array.ndim != 2 for array in arrays):
        raise V04FiveArmError("route Q surfaces must be two-dimensional")
    if any(array.shape != arrays[0].shape for array in arrays[1:]):
        raise V04FiveArmError("route Q surfaces must share one shape")
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise V04FiveArmError("route Q surfaces must be finite")
    legal = np.asarray(masks)
    if legal.dtype != np.bool_ or legal.shape != arrays[0].shape:
        raise V04FiveArmError("common legal mask must be Boolean and match Q surfaces")
    if not np.all(np.any(legal, axis=1)):
        raise V04FiveArmError("common legal mask must admit one action per user")

    active = ACTIVE_ROUTES[policy_label]
    indices = tuple(ROUTE_NAMES.index(route) for route in active)
    # Preserve the declared left-to-right route order and Q dtype.  No route
    # count normalization is allowed: a drop arm is a literal head omission.
    scores = np.array(arrays[indices[0]], copy=True)
    for index in indices[1:]:
        scores = scores + arrays[index]
    if not np.all(np.isfinite(scores)):
        raise V04FiveArmError("summed route scores are non-finite")
    actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    actions[eligible] = np.argmax(
        np.where(legal[eligible], scores[eligible], -np.inf), axis=1
    )
    return actions


def _deep_state(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, Mapping):
        return {key: _deep_state(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_deep_state(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_deep_state(item) for item in value)
    return copy.deepcopy(value)


def _state_equal(left: Any, right: Any) -> bool:
    if isinstance(left, torch.Tensor) or isinstance(right, torch.Tensor):
        return (
            isinstance(left, torch.Tensor)
            and isinstance(right, torch.Tensor)
            and torch.equal(left.detach().cpu(), right.detach().cpu())
        )
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return (
            isinstance(left, Mapping)
            and isinstance(right, Mapping)
            and set(left) == set(right)
            and all(_state_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        return (
            isinstance(left, type(right))
            and len(left) == len(right)
            and all(_state_equal(a, b) for a, b in zip(left, right, strict=True))
        )
    return left == right


def _snapshot_hybrid(trainer: Any) -> dict[str, Any]:
    q_nets = getattr(trainer, "q_nets", None)
    if q_nets is None or len(q_nets) != 3:
        raise V04FiveArmError("hybrid must expose exactly three Q networks")
    optimizer = getattr(trainer, "q3_optimizer", None)
    if optimizer is None:
        raise V04FiveArmError("hybrid must expose its Q3 optimizer boundary")
    return {
        "q_networks": [
            {
                str(name): value.detach().cpu().clone()
                for name, value in network.state_dict().items()
            }
            for network in q_nets
        ],
        "q3_optimizer": _deep_state(optimizer.state_dict()),
        "q3_update_count": getattr(trainer, "q3_update_count", None),
        "training_flags": [bool(network.training) for network in q_nets],
        "gradients": [
            {
                str(index): None
                if parameter.grad is None
                else parameter.grad.detach().cpu().clone()
                for index, parameter in enumerate(network.parameters())
            }
            for network in q_nets
        ],
    }


def _assert_hybrid_unchanged(trainer: Any, before: Mapping[str, Any]) -> None:
    after = _snapshot_hybrid(trainer)
    for field in ("q_networks", "q3_optimizer", "q3_update_count", "training_flags", "gradients"):
        if not _state_equal(after[field], before[field]):
            raise V04FiveArmError(f"hybrid changed during frozen evaluation: {field}")


def _prepare_hybrid(trainer: Any) -> None:
    if not isinstance(trainer, screen.EEAxisV04HybridTrainer):
        raise V04FiveArmError("route evaluation requires the V0.4 hybrid trainer")
    if (
        trainer.selected_q3_rung != SELECTED_Q3_RUNG
        or trainer.q3_update_count != SELECTED_Q3_RUNG
        or len(trainer.q_nets) != 3
    ):
        raise V04FiveArmError("only the selected rung-100 hybrid is admissible")
    if any(
        parameter.requires_grad
        for network in trainer.q_nets[:2]
        for parameter in network.parameters()
    ):
        raise V04FiveArmError("Q1/Q2 must remain frozen")
    for network in trainer.q_nets:
        network.eval()


def _validate_physics(outcome: Any, *, interval_s: float) -> tuple[np.ndarray, float]:
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    power = float(outcome.system_power_w)
    system_rate = float(math.fsum(float(value) for value in rates))
    if (
        rates.shape != (USERS,)
        or not np.all(np.isfinite(rates))
        or np.any(rates < 0.0)
        or not math.isfinite(power)
        or power < 0.0
        or (power == 0.0 and system_rate > 0.0)
        or not math.isfinite(interval_s)
        or interval_s <= 0.0
    ):
        raise V04FiveArmError("episode produced malformed physical EE inputs")
    return rates, power


def _action_trace_sha256(
    *, policy_label: str, initialization_seed: int | None, evaluation_seed: int, actions: Sequence[Sequence[int]]
) -> str:
    return canonical_sha256(
        {
            "schema": "multi-catfish-mcrl-v04-five-arm-action-trace-v1",
            "policy_label": policy_label,
            "initialization_seed": initialization_seed,
            "evaluation_seed": evaluation_seed,
            "actions": actions,
        }
    )


def _common_row_fields(
    *,
    policy_label: str,
    initialization_seed: int | None,
    evaluation_seed: int,
    start_epoch: str,
    initial_world_sha256: str,
    initial_state_sha256: str,
    initial_mask_sha256: str,
    field: KeyedFadingField,
    total_bits: float,
    total_energy: float,
    served_user_steps: int,
    steps: int,
    actions: Sequence[Sequence[int]],
) -> dict[str, Any]:
    if total_energy <= 0.0:
        raise V04FiveArmError("episode must consume positive total energy")
    decision_count = steps * USERS
    if decision_count <= 0 or served_user_steps < 0 or served_user_steps > decision_count:
        raise V04FiveArmError("episode service counts are non-physical")
    return {
        "schema": EPISODE_SCHEMA,
        "policy_label": policy_label,
        "evaluation_split": EVALUATION_SPLIT,
        "initialization_seed": initialization_seed,
        "evaluation_seed": int(evaluation_seed),
        "selected_q3_rung": SELECTED_Q3_RUNG if policy_label != "MAIN" else None,
        "total_q3_update_count": SELECTED_Q3_RUNG if policy_label != "MAIN" else None,
        "steps": int(steps),
        "users": USERS,
        "decision_count": int(decision_count),
        "start_epoch": start_epoch,
        "initial_world_sha256": initial_world_sha256,
        "initial_state_sha256": initial_state_sha256,
        "initial_mask_sha256": initial_mask_sha256,
        "fading_field_sha256": field.root_digest,
        "fading_field_components": [
            FIELD_COMPONENT,
            EXPECTED_C3_CONFIRM_RESULT_SHA256,
            int(evaluation_seed),
        ],
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy),
        "served_user_steps": int(served_user_steps),
        "served_fraction": float(served_user_steps / decision_count),
        "outage_fraction": float(1.0 - served_user_steps / decision_count),
        "action_trace_sha256": _action_trace_sha256(
            policy_label=policy_label,
            initialization_seed=initialization_seed,
            evaluation_seed=evaluation_seed,
            actions=actions,
        ),
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": HELD_OUT_EE_EVALUATED,
        "episode_training": EPISODE_TRAINING,
    }


def _encode_world(
    environment: Any,
    observation: Any,
    *,
    interval_s: float,
    kappa_bits: float,
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray, str, str, str], str]:
    legacy = encode_ee_axis_state(environment.environment, observation)
    v04 = encode_ee_axis_v04_c3_state(
        environment.environment,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    if not np.array_equal(legacy.action_masks, v04.action_masks):
        raise V04FiveArmError("V0.3/V0.4 deployment masks differ")
    legacy_state = np.asarray(legacy.state_matrix)
    v04_state = np.asarray(v04.state_matrix)
    masks = np.asarray(v04.action_masks)
    if masks.dtype != np.bool_ or masks.shape != (USERS, 28):
        raise V04FiveArmError("deployment masks have an unexpected shape")
    initial_state_sha = _array_sha256(legacy_state, v04_state)
    initial_mask_sha = _array_sha256(masks)
    start_epoch = str(environment.epoch.isoformat())
    initial_world_sha = canonical_sha256(
        {
            "start_epoch": start_epoch,
            "initial_state_sha256": initial_state_sha,
            "initial_mask_sha256": initial_mask_sha,
        }
    )
    return (
        legacy_state,
        v04_state,
        masks,
        start_epoch,
        initial_world_sha,
        initial_state_sha,
    ), initial_mask_sha


def evaluate_route_episode(
    trainer: Any,
    archive: Any,
    *,
    evaluation_seed: int,
    initialization_seed: int,
    policy_label: str,
    field: KeyedFadingField,
) -> dict[str, Any]:
    """Evaluate one frozen route arm without changing the hybrid."""

    if policy_label not in ROUTE_ARMS:
        raise V04FiveArmError(f"unsupported route policy: {policy_label}")
    _positive_int(initialization_seed, field="initialization_seed")
    _positive_int(evaluation_seed, field="evaluation_seed")
    _prepare_hybrid(trainer)
    expected_field = _field_for_seed(evaluation_seed)
    if field.root_digest != expected_field.root_digest:
        raise V04FiveArmError("route episode field is not the frozen common field")
    before = _snapshot_hybrid(trainer)
    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(
        evaluation_seed
    )
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise V04FiveArmError("TRAIN interval is not finite and positive")

    kappa_bits = float(trainer.v04_config.kappa_bits)
    encoded = _encode_world(
        environment,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    (
        _legacy_state,
        _v04_state,
        _initial_masks,
        start_epoch,
        initial_world_sha,
        initial_state_sha,
    ), initial_mask_sha = encoded

    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    steps = 0
    action_trace: list[list[int]] = []
    with torch.no_grad():
        while True:
            legacy = encode_ee_axis_state(environment.environment, observation)
            v04 = encode_ee_axis_v04_c3_state(
                environment.environment,
                observation,
                interval_s=interval_s,
                kappa_bits=kappa_bits,
            )
            if not np.array_equal(legacy.action_masks, v04.action_masks):
                raise V04FiveArmError("V0.3/V0.4 deployment masks differ during episode")
            actions = route_actions(
                trainer,
                np.asarray(legacy.state_matrix),
                np.asarray(v04.state_matrix),
                np.asarray(v04.action_masks),
                policy_label,
            )
            action_trace.append([int(value) for value in actions.tolist()])
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates, power = _validate_physics(outcome, interval_s=interval_s)
            total_bits += float(math.fsum(float(value) for value in rates)) * interval_s
            total_energy += power * interval_s
            served_user_steps += int(outcome.resolution.served_count)
            steps += 1
            if result.done:
                break
            observation = outcome.observation
    _assert_hybrid_unchanged(trainer, before)
    if steps != STEPS_PER_EPISODE:
        raise V04FiveArmError(
            f"TRAIN episode length drifted: expected {STEPS_PER_EPISODE}, got {steps}"
        )
    return _common_row_fields(
        policy_label=policy_label,
        initialization_seed=initialization_seed,
        evaluation_seed=evaluation_seed,
        start_epoch=start_epoch,
        initial_world_sha256=initial_world_sha,
        initial_state_sha256=initial_state_sha,
        initial_mask_sha256=initial_mask_sha,
        field=field,
        total_bits=total_bits,
        total_energy=total_energy,
        served_user_steps=served_user_steps,
        steps=steps,
        actions=action_trace,
    )


def evaluate_main_episode(
    trainer: Any,
    archive: Any,
    *,
    runtime: Any,
    evaluation_seed: int,
    field: KeyedFadingField,
    kappa_bits: float,
) -> dict[str, Any]:
    """Evaluate the independent frozen Main policy once per world."""

    _positive_int(evaluation_seed, field="evaluation_seed")
    expected_field = _field_for_seed(evaluation_seed)
    if field.root_digest != expected_field.root_digest:
        raise V04FiveArmError("Main episode field is not the frozen common field")
    if not hasattr(runtime, "main_actions") or not callable(runtime.main_actions):
        raise V04FiveArmError("Main runtime lacks the authoritative action seam")
    before = runtime.network_snapshot(trainer)
    replay_before = int(runtime.replay_size(trainer))
    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(
        evaluation_seed
    )
    states, masks, observation = environment.reset(env_rng, mobility_rng)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    if not math.isfinite(interval_s) or interval_s <= 0.0:
        raise V04FiveArmError("TRAIN interval is not finite and positive")

    encoded = _encode_world(
        environment,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    (
        _legacy_state,
        _v04_state,
        _initial_masks,
        start_epoch,
        initial_world_sha,
        initial_state_sha,
    ), initial_mask_sha = encoded

    total_bits = 0.0
    total_energy = 0.0
    served_user_steps = 0
    steps = 0
    action_trace: list[list[int]] = []
    with torch.no_grad():
        while True:
            actions = np.asarray(
                runtime.main_actions(
                    trainer,
                    environment,
                    states,
                    masks,
                    observation,
                    env_rng,
                ),
                dtype=np.int64,
            )
            if actions.shape != (USERS,):
                raise V04FiveArmError("authoritative Main action vector has wrong shape")
            action_trace.append([int(value) for value in actions.tolist()])
            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            rates, power = _validate_physics(outcome, interval_s=interval_s)
            total_bits += float(math.fsum(float(value) for value in rates)) * interval_s
            total_energy += power * interval_s
            served_user_steps += int(outcome.resolution.served_count)
            steps += 1
            if result.done:
                break
            states = result.user_states
            masks = result.action_masks
            observation = outcome.observation
    if not runtime.networks_equal(trainer, before):
        raise V04FiveArmError("Main network parameters changed during evaluation")
    if int(runtime.replay_size(trainer)) != replay_before:
        raise V04FiveArmError("Main replay changed during evaluation")
    if steps != STEPS_PER_EPISODE:
        raise V04FiveArmError(
            f"TRAIN episode length drifted: expected {STEPS_PER_EPISODE}, got {steps}"
        )
    return _common_row_fields(
        policy_label="MAIN",
        initialization_seed=None,
        evaluation_seed=evaluation_seed,
        start_epoch=start_epoch,
        initial_world_sha256=initial_world_sha,
        initial_state_sha256=initial_state_sha,
        initial_mask_sha256=initial_mask_sha,
        field=field,
        total_bits=total_bits,
        total_energy=total_energy,
        served_user_steps=served_user_steps,
        steps=steps,
        actions=action_trace,
    )


def _manifest_paths() -> tuple[Path, ...]:
    paths: list[Path] = [
        Path(__file__).resolve(),
        Path(screen.__file__).resolve(),
        Path(gate.__file__).resolve(),
        Path(source.__file__).resolve(),
        REPO / "src/mcrl/algorithms/ee_axis_v04_hybrid.py",
        REPO / "src/mcrl/algorithms/ee_axis_pairwise.py",
        REPO / "src/mcrl/runtime/ee_axis_state.py",
        REPO / "src/mcrl/runtime/ee_axis_v04_c3_state.py",
        REPO / "src/mcrl/env/keyed_fading.py",
    ]
    # The Main loader's source runner declares the complete src/mcrl closure
    # (including the loader helper and launcher authority).  Include that
    # closure so the sealed evaluator cannot silently run against a changed
    # trainer/runtime module that was omitted from a hand-maintained list.
    source_paths = getattr(source, "_source_paths", None)
    if callable(source_paths):
        paths.extend(Path(path) for path in source_paths())
    unique: dict[str, Path] = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise V04FiveArmError(f"code manifest path is missing: {path}")
        unique[str(path.resolve())] = path.resolve()
    return tuple(sorted(unique.values(), key=lambda item: _relative(item)))


def build_code_manifest() -> dict[str, Any]:
    files = {_relative(path): _file_sha256(path) for path in _manifest_paths()}
    body = {"schema": CODE_MANIFEST_SCHEMA, "files": files}
    return {**body, "manifest_sha256": canonical_sha256(body)}


def _validate_code_manifest(payload: Mapping[str, Any], *, current: bool) -> str:
    if payload.get("schema") != CODE_MANIFEST_SCHEMA:
        raise V04FiveArmError("five-arm code manifest schema drifted")
    files = payload.get("files")
    if not isinstance(files, Mapping) or not files:
        raise V04FiveArmError("five-arm code manifest files are missing")
    body = {"schema": payload["schema"], "files": dict(files)}
    observed = _digest(payload.get("manifest_sha256"), field="manifest_sha256")
    if canonical_sha256(body) != observed:
        raise V04FiveArmError("five-arm code manifest digest is invalid")
    for name, digest in files.items():
        if not isinstance(name, str):
            raise V04FiveArmError("five-arm code manifest path is malformed")
        _digest(digest, field=f"manifest.files[{name}]")
        if current:
            path = Path(name)
            if not path.is_absolute():
                path = REPO / path
            if _file_sha256(path) != digest:
                raise V04FiveArmError(f"five-arm code changed after manifest seal: {name}")
    return observed


def _authenticate_prior_screen(
    prior_screen_dir: Path,
    *,
    gate_receipt: Mapping[str, Any],
) -> dict[str, str]:
    """Authenticate the exact pre-confirmation screen and primary receipt."""

    root = _regular_dir(
        prior_screen_dir,
        field="prior_screen_dir",
        basename="multi-catfish-v04-c3-500-update-screen-20260901-r1",
    )
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    primary_path = root / "primary-evaluation.json"
    result_sha = _file_sha256(result_path)
    seal_sha = _file_sha256(seal_path)
    primary_sha = _file_sha256(primary_path)
    if result_sha != EXPECTED_PRIOR_SCREEN_RESULT_SHA256:
        raise V04FiveArmError("prior screen result bytes are not the sealed primary result")
    if seal_sha != EXPECTED_PRIOR_SCREEN_RESULT_SEAL_SHA256:
        raise V04FiveArmError("prior screen result seal bytes are not sealed")
    if primary_sha != EXPECTED_PRIOR_PRIMARY_RECEIPT_SHA256:
        raise V04FiveArmError("prior screen primary receipt bytes are not sealed")
    result = _read_json(result_path)
    seal = _read_json(seal_path)
    primary = _read_json(primary_path)
    lineage = {
        "gate_authority_sha256": gate_receipt.get("authority_sha256"),
        "gate_result_file_sha256": gate_receipt.get("result_file_sha256"),
        "source_manifest_sha256": gate_receipt.get("source_manifest_sha256"),
        "schedule_sha256": gate_receipt.get("schedule_sha256"),
    }
    if (
        result.get("schema") != "multi-catfish-mcrl-v04-c3-500-update-screen-result-v1"
        or result.get("status") != "SCREEN_COMPLETE"
        or result.get("gate_status") != "GO_500EP_SCREEN_ONLY"
        or result.get("gate_selected_q3_rung") != SELECTED_Q3_RUNG
        or result.get("evaluation_split") != EVALUATION_SPLIT
        or result.get("primary_screen_updates_completed") != 0
        or result.get("primary_receipt_file_sha256") != primary_sha
        or any(result.get(key) != value for key, value in lineage.items())
        or seal.get("schema")
        != "multi-catfish-mcrl-v04-c3-500-update-screen-result-seal-v1"
        or seal.get("result_file_sha256") != result_sha
        or seal.get("primary_receipt_file_sha256") != primary_sha
        or seal.get("gate_authority_sha256") != gate_receipt.get("authority_sha256")
        or seal.get("held_out_ee_evaluated") is not True
        or primary.get("schema") != "multi-catfish-mcrl-v04-c3-primary-evaluation-receipt-v1"
        or primary.get("status") != "PRIMARY_EVALUATION_COMPLETE"
        or primary.get("gate_authority_sha256") != gate_receipt.get("authority_sha256")
        or primary.get("gate_result_file_sha256") != gate_receipt.get("result_file_sha256")
        or primary.get("gate_selected_q3_rung") != SELECTED_Q3_RUNG
        or primary.get("screen_updates_completed") != 0
        or primary.get("total_q3_update_count") != SELECTED_Q3_RUNG
        or primary.get("evaluation_split") != EVALUATION_SPLIT
        or primary.get("held_out_ee_evaluated") is not True
    ):
        raise V04FiveArmError("prior screen or primary receipt is not the sealed rung-100 screen")
    _require_false(result, "test_split_opened", label="prior screen result")
    _require_false(seal, "test_split_opened", label="prior screen seal")
    _require_false(primary, "test_split_opened", label="prior primary receipt")
    if result.get("episode_training") is not False:
        raise V04FiveArmError("prior screen episode_training is not false")
    return {
        "result_file_sha256": result_sha,
        "result_seal_file_sha256": seal_sha,
        "primary_receipt_file_sha256": primary_sha,
    }


def _authenticate_c3_confirmatory(confirm_dir: Path) -> dict[str, str]:
    root = _regular_dir(
        confirm_dir,
        field="c3_confirmatory_dir",
        basename="multi-catfish-v04-c3-confirmatory-20260901-r1",
    )
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    result_sha = _file_sha256(result_path)
    seal_sha = _file_sha256(seal_path)
    if result_sha != EXPECTED_C3_CONFIRM_RESULT_SHA256:
        raise V04FiveArmError("C3 confirmatory result bytes are not the sealed result")
    if seal_sha != EXPECTED_C3_CONFIRM_RESULT_SEAL_SHA256:
        raise V04FiveArmError("C3 confirmatory result seal bytes are not sealed")
    result = _read_json(result_path)
    seal = _read_json(seal_path)
    if (
        result.get("schema") != "multi-catfish-mcrl-v04-c3-confirmatory-result-v1"
        or result.get("status") != "CONFIRMATORY_COMPLETE"
        or result.get("scientific_status") != "CONFIRM_C3"
        or result.get("arms") != ["FULL", "DROP_C3"]
        or result.get("selected_q3_rung") != SELECTED_Q3_RUNG
        or result.get("test_split_opened") is not False
        or result.get("episode_training") is not False
        or result.get("held_out_ee_evaluated") is not True
        or seal.get("schema")
        != "multi-catfish-mcrl-v04-c3-confirmatory-result-seal-v1"
        or seal.get("result_file_sha256") != result_sha
        or seal.get("test_split_opened") is not False
        or seal.get("episode_training") is not False
    ):
        raise V04FiveArmError("C3 confirmatory result is not the sealed CONFIRM_C3 result")
    authority = result.get("authority")
    if not isinstance(authority, Mapping):
        raise V04FiveArmError("C3 confirmatory authority is missing")
    return {
        "result_file_sha256": result_sha,
        "result_seal_file_sha256": seal_sha,
        "gate_authority_sha256": _digest(
            authority.get("gate_authority_sha256"),
            field="c3_confirm.authority.gate_authority_sha256",
        ),
        "gate_result_file_sha256": _digest(
            authority.get("gate_result_file_sha256"),
            field="c3_confirm.authority.gate_result_file_sha256",
        ),
        "source_manifest_sha256": _digest(
            authority.get("source_manifest_sha256"),
            field="c3_confirm.authority.source_manifest_sha256",
        ),
        "schedule_sha256": _digest(
            authority.get("schedule_sha256"),
            field="c3_confirm.authority.schedule_sha256",
        ),
        "train_surface_sha256": _digest(
            authority.get("train_surface_sha256"),
            field="c3_confirm.authority.train_surface_sha256",
        ),
        "prior_screen_result_file_sha256": _digest(
            authority.get("prior_screen_result_file_sha256"),
            field="c3_confirm.authority.prior_screen_result_file_sha256",
        ),
        "prior_screen_result_seal_file_sha256": _digest(
            authority.get("prior_screen_result_seal_file_sha256"),
            field="c3_confirm.authority.prior_screen_result_seal_file_sha256",
        ),
        "prior_primary_receipt_file_sha256": _digest(
            authority.get("prior_primary_receipt_file_sha256"),
            field="c3_confirm.authority.prior_primary_receipt_file_sha256",
        ),
    }


def authenticate_current_authority(
    *,
    gate_dir: Path,
    source_dir: Path,
    confirm_dir: Path,
    prior_screen_dir: Path = DEFAULT_PRIOR_SCREEN_DIR,
    main_dir: Path,
    prereg_path: Path,
    work_order_path: Path = DEFAULT_WORK_ORDER,
) -> dict[str, Any]:
    """Authenticate every fixed artifact without opening TLE or episodes."""

    prereg_sha = _file_sha256(Path(prereg_path))
    if prereg_sha != EXPECTED_PREREG_FILE_SHA256:
        raise V04FiveArmError("base PREREG bytes are not the frozen authority")
    work_order_sha = _file_sha256(Path(work_order_path))
    if work_order_sha != EXPECTED_WORK_ORDER_SHA256:
        raise V04FiveArmError("five-arm work-order bytes are not the frozen authority")
    gate_root = _regular_dir(
        gate_dir,
        field="gate_dir",
        basename="multi-catfish-v04-c3-learnability-20260901-r2",
    )
    source_root = _regular_dir(
        source_dir,
        field="source_dir",
        basename="multi-catfish-v04-c3-source-20260901-r2",
    )
    gate_receipt = screen.authenticate_gate(
        gate_root,
        source_dir=source_root,
        prereg_path=Path(prereg_path),
    )
    gate_result_seal_sha = _file_sha256(gate_root / "result-seal.json")
    if (
        gate_receipt.get("authority_sha256") != EXPECTED_GATE_AUTHORITY_SHA256
        or gate_receipt.get("authority_file_sha256")
        != EXPECTED_GATE_AUTHORITY_FILE_SHA256
        or gate_receipt.get("authority_seal_file_sha256")
        != EXPECTED_GATE_AUTHORITY_SEAL_FILE_SHA256
        or gate_receipt.get("result_file_sha256") != EXPECTED_GATE_RESULT_SHA256
        or gate_result_seal_sha != EXPECTED_GATE_RESULT_SEAL_SHA256
        or gate_receipt.get("source_manifest_sha256")
        != EXPECTED_SOURCE_MANIFEST_SHA256
        or gate_receipt.get("schedule_sha256") != EXPECTED_SCHEDULE_SHA256
        or gate_receipt.get("train_surface_sha256")
        != EXPECTED_TRAIN_SURFACE_SHA256
        or gate_receipt.get("selected_q3_rung") != SELECTED_Q3_RUNG
    ):
        raise V04FiveArmError("V0.4 gate lineage is not the exact selected rung-100 authority")

    prior = _authenticate_prior_screen(
        Path(prior_screen_dir), gate_receipt=gate_receipt
    )
    confirm = _authenticate_c3_confirmatory(Path(confirm_dir))
    if (
        confirm["gate_authority_sha256"] != gate_receipt["authority_sha256"]
        or confirm["gate_result_file_sha256"] != gate_receipt["result_file_sha256"]
        or confirm["source_manifest_sha256"] != gate_receipt["source_manifest_sha256"]
        or confirm["schedule_sha256"] != gate_receipt["schedule_sha256"]
        or confirm["train_surface_sha256"] != gate_receipt["train_surface_sha256"]
        or confirm["prior_screen_result_file_sha256"] != prior["result_file_sha256"]
        or confirm["prior_screen_result_seal_file_sha256"]
        != prior["result_seal_file_sha256"]
        or confirm["prior_primary_receipt_file_sha256"]
        != prior["primary_receipt_file_sha256"]
    ):
        raise V04FiveArmError("C3 confirmatory result lineage differs from current gate")

    main_authority = source._authenticate_main_authority(Path(main_dir))
    if main_authority != {
        "status_file_sha256": EXPECTED_MAIN_STATUS_FILE_SHA256,
        "episode_logs_file_sha256": EXPECTED_MAIN_EPISODE_LOGS_FILE_SHA256,
        "checkpoint_file_sha256": EXPECTED_MAIN_CHECKPOINT_SHA256,
    }:
        raise V04FiveArmError("Main status/log/checkpoint lineage is not frozen")

    selected_paths = gate_receipt.get("selected_hybrid_paths")
    if not isinstance(selected_paths, Mapping):
        raise V04FiveArmError("gate selected hybrid paths are missing")
    hybrid_paths: dict[str, str] = {}
    hybrid_hashes: dict[str, str] = {}
    expected_seeds = {str(seed) for seed in INITIALIZATION_SEEDS}
    if set(selected_paths) != expected_seeds:
        raise V04FiveArmError("gate selected hybrids do not contain exactly three initializations")
    for seed in INITIALIZATION_SEEDS:
        path_value = selected_paths[str(seed)]
        path = Path(path_value)
        file_sha = _file_sha256(path)
        expected_sha = EXPECTED_HYBRID_FILE_SHA256[seed]
        if file_sha != expected_sha:
            raise V04FiveArmError(f"selected hybrid SHA drifted for initialization {seed}")
        hybrid_paths[str(seed)] = _relative(path)
        hybrid_hashes[str(seed)] = file_sha

    return {
        "prereg_file_sha256": prereg_sha,
        "work_order_file_sha256": work_order_sha,
        "gate_authority_sha256": gate_receipt["authority_sha256"],
        "gate_authority_file_sha256": gate_receipt["authority_file_sha256"],
        "gate_authority_seal_file_sha256": gate_receipt["authority_seal_file_sha256"],
        "gate_result_file_sha256": gate_receipt["result_file_sha256"],
        "gate_result_seal_file_sha256": gate_result_seal_sha,
        "source_manifest_sha256": gate_receipt["source_manifest_sha256"],
        "schedule_sha256": gate_receipt["schedule_sha256"],
        "train_surface_sha256": gate_receipt["train_surface_sha256"],
        "selected_q3_rung": SELECTED_Q3_RUNG,
        "c3_confirm_result_file_sha256": confirm["result_file_sha256"],
        "c3_confirm_result_seal_file_sha256": confirm["result_seal_file_sha256"],
        "prior_screen_result_file_sha256": prior["result_file_sha256"],
        "prior_screen_result_seal_file_sha256": prior["result_seal_file_sha256"],
        "prior_primary_receipt_file_sha256": prior["primary_receipt_file_sha256"],
        "main_authority": main_authority,
        "selected_hybrid_paths": hybrid_paths,
        "selected_hybrid_file_sha256": hybrid_hashes,
        "test_split_opened": False,
        "episode_training": False,
    }


def _validate_episode_row(
    row: Mapping[str, Any],
    *,
    policy_label: str | None = None,
) -> None:
    if row.get("schema") != EPISODE_SCHEMA:
        raise V04FiveArmError("five-arm episode schema drifted")
    policy = row.get("policy_label")
    if policy not in ARMS or (policy_label is not None and policy != policy_label):
        raise V04FiveArmError("five-arm episode policy label drifted")
    if row.get("evaluation_split") != EVALUATION_SPLIT:
        raise V04FiveArmError("five-arm episode is not TRAIN-only")
    if row.get("test_split_opened") is not False or row.get("episode_training") is not False:
        raise V04FiveArmError("five-arm episode opened TEST or trained")
    if row.get("held_out_ee_evaluated") is not True:
        raise V04FiveArmError("five-arm episode must declare the TRAIN EE endpoint")
    seed = row.get("evaluation_seed")
    if type(seed) is not int or seed not in EVALUATION_SEEDS:
        raise V04FiveArmError("five-arm evaluation seed is outside the frozen block")
    if row.get("steps") != STEPS_PER_EPISODE or row.get("users") != USERS:
        raise V04FiveArmError("five-arm episode dimensions drifted")
    if row.get("decision_count") != USERS * STEPS_PER_EPISODE:
        raise V04FiveArmError("five-arm decision count drifted")
    if policy == "MAIN":
        if row.get("initialization_seed") is not None:
            raise V04FiveArmError("Main row must be initialization-independent")
        if row.get("selected_q3_rung") is not None or row.get("total_q3_update_count") is not None:
            raise V04FiveArmError("Main row must not carry a Q3 rung")
    else:
        init = row.get("initialization_seed")
        if type(init) is not int or init not in INITIALIZATION_SEEDS:
            raise V04FiveArmError("route row initialization seed is outside the frozen block")
        if row.get("selected_q3_rung") != SELECTED_Q3_RUNG or row.get("total_q3_update_count") != SELECTED_Q3_RUNG:
            raise V04FiveArmError("route row is not frozen at selected rung 100")
    for field in (
        "initial_world_sha256",
        "initial_state_sha256",
        "initial_mask_sha256",
        "fading_field_sha256",
        "action_trace_sha256",
    ):
        _digest(row.get(field), field=f"row.{field}")
    if row.get("fading_field_components") != [
        FIELD_COMPONENT,
        EXPECTED_C3_CONFIRM_RESULT_SHA256,
        seed,
    ]:
        raise V04FiveArmError("five-arm fading field components drifted")
    expected_field = _field_for_seed(seed)
    if row.get("fading_field_sha256") != expected_field.root_digest:
        raise V04FiveArmError("five-arm fading field digest drifted")
    served = row.get("served_user_steps")
    if type(served) is not int or served < 0 or served > row["decision_count"]:
        raise V04FiveArmError("five-arm service count is malformed")
    served_fraction = row.get("served_fraction")
    outage_fraction = row.get("outage_fraction")
    if (
        not isinstance(served_fraction, (int, float))
        or isinstance(served_fraction, bool)
        or not math.isfinite(float(served_fraction))
        or not math.isclose(
            float(served_fraction), served / row["decision_count"], rel_tol=1e-12, abs_tol=1e-12
        )
        or not isinstance(outage_fraction, (int, float))
        or isinstance(outage_fraction, bool)
        or not math.isfinite(float(outage_fraction))
        or not math.isclose(
            float(outage_fraction), 1.0 - served / row["decision_count"], rel_tol=1e-12, abs_tol=1e-12
        )
    ):
        raise V04FiveArmError("five-arm service fractions are inconsistent")
    bits = _finite_nonnegative(row.get("total_bits"), field="row.total_bits")
    energy = _finite_nonnegative(row.get("total_energy_j"), field="row.total_energy_j")
    ee = _finite_nonnegative(
        row.get("ratio_of_sums_ee_bits_per_j"),
        field="row.ratio_of_sums_ee_bits_per_j",
    )
    if energy <= 0.0 or not math.isclose(ee, bits / energy, rel_tol=1e-12, abs_tol=1e-12):
        raise V04FiveArmError("five-arm row EE is not bits divided by positive energy")
    if not isinstance(row.get("start_epoch"), str) or not row["start_epoch"]:
        raise V04FiveArmError("five-arm start epoch is malformed")


def _validate_arm_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    policy_label: str,
) -> None:
    expected = len(EVALUATION_SEEDS) if policy_label == "MAIN" else len(EVALUATION_SEEDS) * len(INITIALIZATION_SEEDS)
    if len(rows) != expected:
        raise V04FiveArmError(
            f"{policy_label} requires exactly {expected} rows, got {len(rows)}"
        )
    keys: list[tuple[int, ...]] = []
    for row in rows:
        _validate_episode_row(row, policy_label=policy_label)
        if policy_label == "MAIN":
            keys.append((int(row["evaluation_seed"]),))
        else:
            keys.append((int(row["initialization_seed"]), int(row["evaluation_seed"])))
    if len(set(keys)) != len(keys):
        raise V04FiveArmError(f"{policy_label} contains duplicate world rows")
    expected_keys = (
        {(seed,) for seed in EVALUATION_SEEDS}
        if policy_label == "MAIN"
        else {
            (init, seed)
            for init in INITIALIZATION_SEEDS
            for seed in EVALUATION_SEEDS
        }
    )
    if set(keys) != expected_keys:
        raise V04FiveArmError(f"{policy_label} row key set is incomplete")


def _validate_common_world_identity(
    rows_by_arm: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    world_rows: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for policy, rows in rows_by_arm.items():
        for row in rows:
            _validate_episode_row(row, policy_label=policy)
            world_rows[int(row["evaluation_seed"])].append(row)
    if set(world_rows) != set(EVALUATION_SEEDS):
        raise V04FiveArmError("five-arm physical-world seed set is incomplete")
    for seed in EVALUATION_SEEDS:
        rows = world_rows[seed]
        expected_count = len(ROUTE_ARMS) * len(INITIALIZATION_SEEDS) + 1
        if len(rows) != expected_count:
            raise V04FiveArmError(f"world {seed} does not contain all five arms")
        fields = (
            "start_epoch",
            "initial_world_sha256",
            "initial_state_sha256",
            "initial_mask_sha256",
            "fading_field_sha256",
            "fading_field_components",
        )
        for field in fields:
            if len({repr(row[field]) for row in rows}) != 1:
                raise V04FiveArmError(f"world {seed} is not common in {field}")


def aggregate_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V04FiveArmError("cannot aggregate an empty five-arm arm")
    for row in rows:
        _validate_episode_row(row)
    bits = float(math.fsum(float(row["total_bits"]) for row in rows))
    energy = float(math.fsum(float(row["total_energy_j"]) for row in rows))
    decisions = int(sum(int(row["decision_count"]) for row in rows))
    served = int(sum(int(row["served_user_steps"]) for row in rows))
    if not math.isfinite(bits) or not math.isfinite(energy) or energy <= 0.0:
        raise V04FiveArmError("five-arm aggregate has non-positive energy")
    return {
        "rows": len(rows),
        "decision_count": decisions,
        "served_user_steps": served,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
        "total_bits": bits,
        "total_energy_j": energy,
        "pooled_ratio_of_sums_ee_bits_per_j": bits / energy,
    }


def _group_by_seed(
    rows: Sequence[Mapping[str, Any]],
) -> dict[int, list[Mapping[str, Any]]]:
    groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[int(row["evaluation_seed"])].append(row)
    return dict(groups)


def _group_by_init(
    rows: Sequence[Mapping[str, Any]],
) -> dict[int, list[Mapping[str, Any]]]:
    groups: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        init = row.get("initialization_seed")
        if type(init) is int:
            groups[int(init)].append(row)
    return dict(groups)


def _per_initialization_route(
    full_rows: Sequence[Mapping[str, Any]],
    drop_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    full_groups = _group_by_init(full_rows)
    drop_groups = _group_by_init(drop_rows)
    result: dict[str, dict[str, Any]] = {}
    for init in INITIALIZATION_SEEDS:
        full = aggregate_rows(full_groups[init])
        drop = aggregate_rows(drop_groups[init])
        full_ee = float(full["pooled_ratio_of_sums_ee_bits_per_j"])
        drop_ee = float(drop["pooled_ratio_of_sums_ee_bits_per_j"])
        result[str(init)] = {
            "full": full,
            "drop": drop,
            "ee_difference_bits_per_j": full_ee - drop_ee,
            "ee_difference_percent": _percent_contrast(
                full_ee, drop_ee, label=f"initialization_{init}"
            ),
            "served_fraction_difference": float(full["served_fraction"] - drop["served_fraction"]),
        }
    return result


def _per_world_route(
    full_rows: Sequence[Mapping[str, Any]],
    drop_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    full_groups = _group_by_seed(full_rows)
    drop_groups = _group_by_seed(drop_rows)
    if set(full_groups) != set(drop_groups) or set(full_groups) != set(EVALUATION_SEEDS):
        raise V04FiveArmError("route comparison world groups are incomplete")
    result: list[dict[str, Any]] = []
    for seed in EVALUATION_SEEDS:
        full = aggregate_rows(full_groups[seed])
        drop = aggregate_rows(drop_groups[seed])
        full_ee = float(full["pooled_ratio_of_sums_ee_bits_per_j"])
        drop_ee = float(drop["pooled_ratio_of_sums_ee_bits_per_j"])
        result.append(
            {
                "evaluation_seed": seed,
                "full_ee_bits_per_j": full_ee,
                "drop_ee_bits_per_j": drop_ee,
                "ee_difference_bits_per_j": full_ee - drop_ee,
                "full_served_user_steps": full["served_user_steps"],
                "drop_served_user_steps": drop["served_user_steps"],
                "served_difference": full["served_user_steps"] - drop["served_user_steps"],
            }
        )
    return result


def _per_initialization_main(
    full_rows: Sequence[Mapping[str, Any]],
    main_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    full_groups = _group_by_init(full_rows)
    main_by_seed = _group_by_seed(main_rows)
    result: dict[str, dict[str, Any]] = {}
    for init in INITIALIZATION_SEEDS:
        full = aggregate_rows(full_groups[init])
        main = aggregate_rows([main_by_seed[seed][0] for seed in EVALUATION_SEEDS])
        full_ee = float(full["pooled_ratio_of_sums_ee_bits_per_j"])
        main_ee = float(main["pooled_ratio_of_sums_ee_bits_per_j"])
        result[str(init)] = {
            "full": full,
            "main": main,
            "ee_difference_bits_per_j": full_ee - main_ee,
            "ee_difference_percent": _percent_contrast(
                full_ee, main_ee, label=f"initialization_{init}_main"
            ),
            "served_fraction_difference": float(full["served_fraction"] - main["served_fraction"]),
        }
    return result


def _per_world_main(
    full_rows: Sequence[Mapping[str, Any]],
    main_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    full_groups = _group_by_seed(full_rows)
    main_groups = _group_by_seed(main_rows)
    if set(full_groups) != set(main_groups) or set(full_groups) != set(EVALUATION_SEEDS):
        raise V04FiveArmError("FULL/MAIN world groups are incomplete")
    result: list[dict[str, Any]] = []
    for seed in EVALUATION_SEEDS:
        full = aggregate_rows(full_groups[seed])
        main = aggregate_rows(main_groups[seed])
        full_ee = float(full["pooled_ratio_of_sums_ee_bits_per_j"])
        main_ee = float(main["pooled_ratio_of_sums_ee_bits_per_j"])
        result.append(
            {
                "evaluation_seed": seed,
                "full_ee_bits_per_j": full_ee,
                "main_ee_bits_per_j": main_ee,
                "ee_difference_bits_per_j": full_ee - main_ee,
                "full_served_user_steps": full["served_user_steps"],
                "main_served_user_steps_raw": main["served_user_steps"],
                "main_served_user_steps_weighted": main["served_user_steps"]
                * len(INITIALIZATION_SEEDS),
                "full_served_fraction": full["served_fraction"],
                "main_served_fraction": main["served_fraction"],
                # Main is one episode per world while FULL has three.  Use
                # fractions (and a 3x weighted count) for a fair diagnostic.
                "served_difference": full["served_user_steps"]
                - main["served_user_steps"] * len(INITIALIZATION_SEEDS),
                "served_fraction_difference": full["served_fraction"]
                - main["served_fraction"],
            }
        )
    return result


def _strict_positive(value: object, *, field: str) -> float:
    """Return a finite positive denominator or fail closed."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V04FiveArmError(f"{field} must be a finite positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise V04FiveArmError(f"{field} must be a finite positive number")
    return result


def _percent_contrast(full_ee: float, other_ee: float, *, label: str) -> float:
    denominator = _strict_positive(other_ee, field=f"{label}.other_ee")
    value = (float(full_ee) / denominator - 1.0) * 100.0
    if not math.isfinite(value):
        raise V04FiveArmError(f"{label} percentage contrast is non-finite")
    return float(value)


def paired_world_bootstrap(
    full_rows: Sequence[Mapping[str, Any]],
    other_rows: Sequence[Mapping[str, Any]],
    *,
    comparison_label: str | None = None,
    seed: int | None = None,
    replicates: int = BOOTSTRAP_REPLICATES,
    main: bool = False,
) -> dict[str, Any]:
    """Bootstrap 30 paired physical worlds, retaining all route inits.

    ``FULL`` has three initialization rows per route world.  Against ``MAIN``
    the one Main row is multiplied by three at the world-total level so that
    the pooled estimator has the same initialization weight on both sides.
    No division is attempted until every sampled energy and the sampled
    comparison denominator has passed a strict positivity guard.
    """

    if type(replicates) is not int or replicates != BOOTSTRAP_REPLICATES:
        raise V04FiveArmError("bootstrap replicate count is frozen at 10000")
    label = str(comparison_label or ("MAIN" if main else "C1"))
    if label == "MAIN":
        main = True
    if label not in (*ROUTE_NAMES, "MAIN"):
        raise V04FiveArmError(f"unknown bootstrap comparison label: {label}")
    expected_seed = BOOTSTRAP_SEEDS[label]
    if seed is None:
        seed = expected_seed
    if type(seed) is not int or seed != expected_seed:
        raise V04FiveArmError(f"bootstrap seed is not frozen for {label}")

    full_policy = "FULL"
    other_policy = "MAIN" if main else f"DROP_{label}"
    _validate_arm_rows(full_rows, policy_label=full_policy)
    _validate_arm_rows(other_rows, policy_label=other_policy)
    full_by_world = _group_by_seed(full_rows)
    other_by_world = _group_by_seed(other_rows)
    worlds = tuple(EVALUATION_SEEDS)
    if set(full_by_world) != set(worlds) or set(other_by_world) != set(worlds):
        raise V04FiveArmError("bootstrap world clusters are incomplete")
    expected_rows = 1 if main else len(INITIALIZATION_SEEDS)
    if any(len(full_by_world[world]) != len(INITIALIZATION_SEEDS) for world in worlds):
        raise V04FiveArmError("bootstrap FULL world clusters do not retain all initializations")
    if any(len(other_by_world[world]) != expected_rows for world in worlds):
        raise V04FiveArmError("bootstrap comparison world clusters have the wrong size")

    def world_totals(groups: Mapping[int, Sequence[Mapping[str, Any]]]) -> tuple[np.ndarray, np.ndarray]:
        bits = np.asarray(
            [math.fsum(float(row["total_bits"]) for row in groups[world]) for world in worlds],
            dtype=np.float64,
        )
        energy = np.asarray(
            [math.fsum(float(row["total_energy_j"]) for row in groups[world]) for world in worlds],
            dtype=np.float64,
        )
        return bits, energy

    full_bits, full_energy = world_totals(full_by_world)
    other_bits, other_energy = world_totals(other_by_world)
    if main:
        # Equalize initialization weight only after physical-world pooling.
        other_bits = other_bits * len(INITIALIZATION_SEEDS)
        other_energy = other_energy * len(INITIALIZATION_SEEDS)
    for values, field in (
        (full_bits, "FULL world bits"),
        (other_bits, f"{label} world bits"),
        (full_energy, "FULL world energy"),
        (other_energy, f"{label} world energy"),
    ):
        if not np.all(np.isfinite(values)) or ("energy" not in field and np.any(values < 0.0)):
            raise V04FiveArmError(f"bootstrap {field} are non-finite or negative")
    if np.any(full_energy <= 0.0) or np.any(other_energy <= 0.0):
        raise V04FiveArmError("bootstrap FULL/DROP energy must be strictly positive")

    rng = np.random.default_rng(seed)
    sampled = rng.integers(0, len(worlds), size=(replicates, len(worlds)))
    sampled_full_bits = np.sum(full_bits[sampled], axis=1, dtype=np.float64)
    sampled_full_energy = np.sum(full_energy[sampled], axis=1, dtype=np.float64)
    sampled_other_bits = np.sum(other_bits[sampled], axis=1, dtype=np.float64)
    sampled_other_energy = np.sum(other_energy[sampled], axis=1, dtype=np.float64)
    if (
        not np.all(np.isfinite(sampled_full_energy))
        or not np.all(np.isfinite(sampled_other_energy))
        or np.any(sampled_full_energy <= 0.0)
        or np.any(sampled_other_energy <= 0.0)
    ):
        raise V04FiveArmError("bootstrap sampled FULL/DROP energy must be strictly positive")
    # This guard is deliberately before the percentage division.  It also
    # catches a zero-bit comparison arm, for which the percentage endpoint is
    # undefined rather than silently reported as negative infinity.
    sampled_other_ee = sampled_other_bits / sampled_other_energy
    if not np.all(np.isfinite(sampled_other_ee)) or np.any(sampled_other_ee <= 0.0):
        raise V04FiveArmError("bootstrap DROP EE denominator must be strictly positive")
    sampled_full_ee = sampled_full_bits / sampled_full_energy
    if not np.all(np.isfinite(sampled_full_ee)):
        raise V04FiveArmError("bootstrap FULL EE is non-finite")
    absolute_values = sampled_full_ee - sampled_other_ee
    percent_values = (sampled_full_ee / sampled_other_ee - 1.0) * 100.0
    if not np.all(np.isfinite(absolute_values)) or not np.all(np.isfinite(percent_values)):
        raise V04FiveArmError("bootstrap produced non-finite EE contrasts")
    return {
        "comparison": label,
        "replicates": replicates,
        "seed": seed,
        "world_count": len(worlds),
        "resampling_unit": "physical_world_seed_with_all_three_initializations",
        "lower_bits_per_j": float(np.percentile(absolute_values, 2.5)),
        "upper_bits_per_j": float(np.percentile(absolute_values, 97.5)),
        "median_bits_per_j": float(np.percentile(absolute_values, 50.0)),
        "lower_percent": float(np.percentile(percent_values, 2.5)),
        "upper_percent": float(np.percentile(percent_values, 97.5)),
        "median_percent": float(np.percentile(percent_values, 50.0)),
        "samples_sha256": hashlib.sha256(percent_values.tobytes()).hexdigest(),
        "absolute_samples_sha256": hashlib.sha256(absolute_values.tobytes()).hexdigest(),
    }


# A private spelling keeps the implementation seam discoverable to tests and
# future reviewers without creating a second estimator.
_paired_world_bootstrap = paired_world_bootstrap


def apply_route_decision(
    *,
    route_name: str,
    full_summary: Mapping[str, Any],
    drop_summary: Mapping[str, Any],
    per_initialization: Mapping[str, Mapping[str, Any]],
    per_world: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the preregistered marginal route gate without retuning."""

    if route_name not in ROUTE_NAMES:
        raise V04FiveArmError(f"unknown route decision: {route_name}")
    # Zero FULL EE is a valid (albeit failing) scientific endpoint; only the
    # comparison denominator must be strictly positive for the percentage
    # contrast and preregistered bootstrap.
    full_ee = _finite_nonnegative(
        full_summary.get("pooled_ratio_of_sums_ee_bits_per_j"),
        field="FULL pooled EE",
    )
    drop_ee = _strict_positive(
        drop_summary.get("pooled_ratio_of_sums_ee_bits_per_j"),
        field=f"DROP_{route_name} pooled EE",
    )
    init_ee_positive = sum(
        float(per_initialization[str(seed)]["ee_difference_bits_per_j"]) > 0.0
        for seed in INITIALIZATION_SEEDS
    )
    init_service_nonnegative = sum(
        float(per_initialization[str(seed)]["served_fraction_difference"]) >= 0.0
        for seed in INITIALIZATION_SEEDS
    )
    world_differences = [float(row["ee_difference_bits_per_j"]) for row in per_world]
    if len(world_differences) != len(EVALUATION_SEEDS) or not np.all(
        np.isfinite(np.asarray(world_differences, dtype=np.float64))
    ):
        raise V04FiveArmError(f"{route_name} world contrast block is malformed")
    median_world = float(np.median(np.asarray(world_differences, dtype=np.float64)))
    positive_worlds = sum(value > 0.0 for value in world_differences)
    pooled_difference = full_ee - drop_ee
    checks = {
        "pooled_full_ee_greater": pooled_difference > 0.0,
        "at_least_two_initializations_ee_positive": init_ee_positive >= 2,
        "median_per_world_ee_positive": median_world > 0.0,
        "bootstrap_lower_bound_positive": float(bootstrap.get("lower_percent", float("nan"))) > 0.0,
        "pooled_service_noninferior": float(full_summary["served_fraction"])
        >= float(drop_summary["served_fraction"]),
        "at_least_two_initializations_service_nonnegative": init_service_nonnegative >= 2,
    }
    return {
        "comparison": f"FULL_vs_DROP_{route_name}",
        "route": route_name,
        "status": f"CONFIRM_{route_name}" if all(checks.values()) else f"{route_name}_NOT_CONFIRMED",
        "checks": checks,
        "pooled_ee_difference_bits_per_j": pooled_difference,
        "pooled_ee_difference_percent": _percent_contrast(
            full_ee, drop_ee, label=f"{route_name}.pooled"
        ),
        "median_per_world_ee_difference_bits_per_j": median_world,
        "positive_per_world_ee_count": positive_worlds,
        "positive_initializations": init_ee_positive,
        "service_nonnegative_initializations": init_service_nonnegative,
        "per_world_service_loss_count": sum(
            int(float(row["served_difference"]) < 0.0) for row in per_world
        ),
    }


def apply_main_decision(
    *,
    full_summary: Mapping[str, Any],
    main_summary: Mapping[str, Any],
    per_world: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the preregistered FULL-versus-frozen-Main gate."""

    full_ee = _finite_nonnegative(
        full_summary.get("pooled_ratio_of_sums_ee_bits_per_j"),
        field="FULL pooled EE",
    )
    main_ee = _strict_positive(
        main_summary.get("pooled_ratio_of_sums_ee_bits_per_j"),
        field="MAIN pooled EE",
    )
    differences = [float(row["ee_difference_bits_per_j"]) for row in per_world]
    if len(differences) != len(EVALUATION_SEEDS) or not np.all(
        np.isfinite(np.asarray(differences, dtype=np.float64))
    ):
        raise V04FiveArmError("Main world contrast block is malformed")
    median_world = float(np.median(np.asarray(differences, dtype=np.float64)))
    checks = {
        "pooled_full_ee_greater": full_ee > main_ee,
        "median_per_world_ee_positive": median_world > 0.0,
        "bootstrap_lower_bound_positive": float(bootstrap.get("lower_percent", float("nan"))) > 0.0,
        "pooled_service_noninferior": float(full_summary["served_fraction"])
        >= float(main_summary["served_fraction"]),
    }
    return {
        "comparison": "FULL_vs_MAIN",
        "status": "FULL_BEATS_MAIN" if all(checks.values()) else "FULL_NOT_BETTER_THAN_MAIN",
        "checks": checks,
        "pooled_ee_difference_bits_per_j": full_ee - main_ee,
        "pooled_ee_difference_percent": _percent_contrast(
            full_ee, main_ee, label="MAIN.pooled"
        ),
        "median_per_world_ee_difference_bits_per_j": median_world,
        "positive_per_world_ee_count": sum(value > 0.0 for value in differences),
        "per_world_service_loss_count": sum(
            int(float(row["served_difference"]) < 0.0) for row in per_world
        ),
    }


def apply_decision_rule(
    *,
    full_summary: Mapping[str, Any],
    drop_summary: Mapping[str, Any],
    per_initialization: Mapping[str, Mapping[str, Any]],
    per_world: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
    route_name: str = "C1",
) -> dict[str, Any]:
    """Compatibility wrapper for a route decision in synthetic audits."""

    return apply_route_decision(
        route_name=route_name,
        full_summary=full_summary,
        drop_summary=drop_summary,
        per_initialization=per_initialization,
        per_world=per_world,
        bootstrap=bootstrap,
    )


def _prepare_payload(
    *,
    authority: Mapping[str, Any],
    manifest_file_sha256: str,
    manifest_sha256: str,
    gate_dir: Path,
    source_dir: Path,
    confirm_dir: Path,
    prior_screen_dir: Path,
    main_dir: Path,
    prereg_path: Path,
    work_order_path: Path,
) -> dict[str, Any]:
    return {
        "schema": PREPARE_SCHEMA,
        "status": STATUS_PREPARED,
        "claim_ceiling": "FROZEN_FIVE_ARM_TRAIN_EE_NO_TEST_NO_TRAINING",
        "authority": dict(authority),
        "gate_dir_basename": Path(gate_dir).name,
        "source_dir_basename": Path(source_dir).name,
        "c3_confirm_dir_basename": Path(confirm_dir).name,
        "prior_screen_dir_basename": Path(prior_screen_dir).name,
        "main_dir_basename": Path(main_dir).name,
        "prereg_file_sha256": _file_sha256(Path(prereg_path)),
        "work_order_file_sha256": _file_sha256(Path(work_order_path)),
        "evaluator_code_manifest_file_sha256": manifest_file_sha256,
        "evaluator_code_manifest_sha256": manifest_sha256,
        "arms": list(ARMS),
        "route_arms": list(ROUTE_ARMS),
        "active_routes": {key: list(value) for key, value in ACTIVE_ROUTES.items()},
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "selected_q3_rung": SELECTED_Q3_RUNG,
        "evaluation_split": EVALUATION_SPLIT,
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": {
            "route": len(EVALUATION_SEEDS) * len(INITIALIZATION_SEEDS) * len(ROUTE_ARMS),
            "main": len(EVALUATION_SEEDS),
            "total": len(EVALUATION_SEEDS) * (len(INITIALIZATION_SEEDS) * len(ROUTE_ARMS) + 1),
        },
        "common_keyed_field": {
            "components": [FIELD_COMPONENT, EXPECTED_C3_CONFIRM_RESULT_SHA256, "evaluation_seed"],
            "excluded_components": ["initialization_seed", "policy_label"],
        },
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seeds": dict(BOOTSTRAP_SEEDS),
            "resampling_unit": "physical_world_seed_with_all_three_initializations",
        },
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": False,
        "episode_training": EPISODE_TRAINING,
        "gate_dir": str(Path(gate_dir).resolve()),
        "source_dir": str(Path(source_dir).resolve()),
        "c3_confirm_dir": str(Path(confirm_dir).resolve()),
        "prior_screen_dir": str(Path(prior_screen_dir).resolve()),
        "main_dir": str(Path(main_dir).resolve()),
        "prereg_path": str(Path(prereg_path).resolve()),
        "work_order_path": str(Path(work_order_path).resolve()),
    }


def prepare_five_arm(
    *,
    gate_dir: Path = DEFAULT_GATE_DIR,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    confirm_dir: Path = DEFAULT_C3_CONFIRM_DIR,
    prior_screen_dir: Path = DEFAULT_PRIOR_SCREEN_DIR,
    main_dir: Path = DEFAULT_MAIN_DIR,
    prereg_path: Path = DEFAULT_PREREG,
    work_order_path: Path = DEFAULT_WORK_ORDER,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    """Authenticate and seal the five-arm protocol without opening episodes."""

    destination = Path(output_dir)
    if destination.exists() or destination.is_symlink():
        raise V04FiveArmError(f"refusing to overwrite five-arm output: {destination}")
    authority = authenticate_current_authority(
        gate_dir=Path(gate_dir),
        source_dir=Path(source_dir),
        confirm_dir=Path(confirm_dir),
        prior_screen_dir=Path(prior_screen_dir),
        main_dir=Path(main_dir),
        prereg_path=Path(prereg_path),
        work_order_path=Path(work_order_path),
    )
    manifest = build_code_manifest()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.prepare-", dir=destination.parent)
    )
    try:
        manifest_file_sha = _write_once_json(
            temporary / "evaluator-code-manifest.json", manifest
        )
        manifest_sha = _validate_code_manifest(manifest, current=True)
        payload = _prepare_payload(
            authority=authority,
            manifest_file_sha256=manifest_file_sha,
            manifest_sha256=manifest_sha,
            gate_dir=Path(gate_dir),
            source_dir=Path(source_dir),
            confirm_dir=Path(confirm_dir),
            prior_screen_dir=Path(prior_screen_dir),
            main_dir=Path(main_dir),
            prereg_path=Path(prereg_path),
            work_order_path=Path(work_order_path),
        )
        prepare_file_sha = _write_once_json(temporary / "prepare.json", payload)
        prepare_seal = {
            "schema": PREPARE_SEAL_SCHEMA,
            "prepare_file_sha256": prepare_file_sha,
            "evaluator_code_manifest_file_sha256": manifest_file_sha,
            "evaluator_code_manifest_sha256": manifest_sha,
            "work_order_file_sha256": payload["work_order_file_sha256"],
            "test_split_opened": TEST_SPLIT_OPENED,
            "held_out_ee_evaluated": False,
            "episode_training": EPISODE_TRAINING,
        }
        prepare_seal_file_sha = _write_once_json(
            temporary / "prepare-seal.json", prepare_seal
        )
        # All three receipts are complete before the directory becomes
        # visible at its final name.  Keep the caller's destination absent on
        # any validation/write failure.
        if destination.exists() or destination.is_symlink():
            raise V04FiveArmError(f"prepare destination appeared during publish: {destination}")
        os.rename(temporary, destination)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)
    return {
        "status": STATUS_PREPARED,
        "output_dir": str(destination.resolve()),
        "prepare_file_sha256": prepare_file_sha,
        "prepare_seal_file_sha256": prepare_seal_file_sha,
        "evaluator_code_manifest_file_sha256": manifest_file_sha,
        "evaluator_code_manifest_sha256": manifest_sha,
        "work_order_file_sha256": payload["work_order_file_sha256"],
        "episode_opened": False,
    }


def _load_prepared(
    output_dir: Path,
    *,
    require_current_code: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the no-episode prepare receipts and validate frozen protocol."""

    root = _regular_dir(Path(output_dir), field="output_dir")
    manifest_path = root / "evaluator-code-manifest.json"
    prepare_path = root / "prepare.json"
    seal_path = root / "prepare-seal.json"
    manifest = _read_json(manifest_path)
    prepare = _read_json(prepare_path)
    seal = _read_json(seal_path)
    manifest_sha = _validate_code_manifest(manifest, current=require_current_code)
    manifest_file_sha = _file_sha256(manifest_path)
    prepare_sha = _file_sha256(prepare_path)
    if (
        prepare.get("schema") != PREPARE_SCHEMA
        or prepare.get("status") != STATUS_PREPARED
        or prepare.get("evaluator_code_manifest_file_sha256") != manifest_file_sha
        or prepare.get("evaluator_code_manifest_sha256") != manifest_sha
        or prepare.get("prereg_file_sha256") != EXPECTED_PREREG_FILE_SHA256
        or prepare.get("work_order_file_sha256") != EXPECTED_WORK_ORDER_SHA256
        or prepare.get("prior_screen_dir_basename")
        != "multi-catfish-v04-c3-500-update-screen-20260901-r1"
        or tuple(prepare.get("arms", [])) != ARMS
        or tuple(prepare.get("route_arms", [])) != ROUTE_ARMS
        or tuple(prepare.get("evaluation_seeds", [])) != EVALUATION_SEEDS
        or tuple(prepare.get("initialization_seeds", [])) != INITIALIZATION_SEEDS
        or prepare.get("selected_q3_rung") != SELECTED_Q3_RUNG
        or prepare.get("evaluation_split") != EVALUATION_SPLIT
        or prepare.get("users") != USERS
        or prepare.get("steps_per_episode") != STEPS_PER_EPISODE
        or prepare.get("test_split_opened") is not False
        or prepare.get("held_out_ee_evaluated") is not False
        or prepare.get("episode_training") is not False
    ):
        raise V04FiveArmError("five-arm prepare receipt is not authenticated")
    expected_episodes = {
        "route": 360,
        "main": 30,
        "total": 390,
    }
    if prepare.get("episodes") != expected_episodes:
        raise V04FiveArmError("five-arm episode budget drifted")
    if prepare.get("active_routes") != {
        key: list(value) for key, value in ACTIVE_ROUTES.items()
    }:
        raise V04FiveArmError("five-arm route adapter map drifted")
    if prepare.get("bootstrap") != {
        "replicates": BOOTSTRAP_REPLICATES,
        "seeds": dict(BOOTSTRAP_SEEDS),
        "resampling_unit": "physical_world_seed_with_all_three_initializations",
    }:
        raise V04FiveArmError("five-arm bootstrap protocol drifted")
    if (
        seal.get("schema") != PREPARE_SEAL_SCHEMA
        or seal.get("prepare_file_sha256") != prepare_sha
        or seal.get("evaluator_code_manifest_file_sha256") != manifest_file_sha
        or seal.get("evaluator_code_manifest_sha256") != manifest_sha
        or seal.get("work_order_file_sha256") != EXPECTED_WORK_ORDER_SHA256
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not False
        or seal.get("episode_training") is not False
    ):
        raise V04FiveArmError("five-arm prepare seal is invalid")
    authority = prepare.get("authority")
    if not isinstance(authority, Mapping):
        raise V04FiveArmError("five-arm prepare authority is missing")
    if authority.get("work_order_file_sha256") != EXPECTED_WORK_ORDER_SHA256:
        raise V04FiveArmError("five-arm authority lacks work-order authentication")
    for field in (
        "prior_screen_result_file_sha256",
        "prior_screen_result_seal_file_sha256",
        "prior_primary_receipt_file_sha256",
    ):
        _digest(authority.get(field), field=f"prepare.authority.{field}")
    return prepare, dict(authority)


def _compare_authority(expected: Mapping[str, Any], observed: Mapping[str, Any]) -> None:
    if dict(expected) != dict(observed):
        raise V04FiveArmError("current authority differs from sealed prepare authority")


def _arm_block(
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    return {"summary": dict(summary), "rows": [dict(row) for row in rows]}


def _result_payload(
    *,
    prepare: Mapping[str, Any],
    authority: Mapping[str, Any],
    rows_by_arm: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    full_rows: Sequence[Mapping[str, Any]] | None = None,
    drop_rows: Sequence[Mapping[str, Any]] | None = None,
    main_rows: Sequence[Mapping[str, Any]] | None = None,
    elapsed_s: float,
) -> dict[str, Any]:
    """Recompute all five-arm endpoints from exact frozen episode rows."""

    if rows_by_arm is None:
        if full_rows is None or drop_rows is None or main_rows is None:
            raise V04FiveArmError("five-arm result requires all five arm rows")
        # ``drop_rows`` is accepted as a compact synthetic seam only when it
        # is already a mapping; production always supplies rows_by_arm.
        if isinstance(drop_rows, Mapping):
            rows_by_arm = {
                "FULL": full_rows,
                **{str(key): value for key, value in drop_rows.items()},
                "MAIN": main_rows,
            }
        else:
            raise V04FiveArmError("five-arm result requires DROP_C1/DROP_C2/DROP_C3 rows")
    rows = {str(key): value for key, value in rows_by_arm.items()}
    if set(rows) != set(ARMS):
        raise V04FiveArmError("five-arm result must contain exactly five arms")
    for arm in ARMS:
        _validate_arm_rows(rows[arm], policy_label=arm)
    _validate_common_world_identity(rows)
    summaries = {arm: aggregate_rows(rows[arm]) for arm in ARMS}

    comparisons: dict[str, dict[str, Any]] = {}
    for route_name in ROUTE_NAMES:
        drop_arm = f"DROP_{route_name}"
        per_initialization = _per_initialization_route(
            rows["FULL"], rows[drop_arm]
        )
        per_world = _per_world_route(rows["FULL"], rows[drop_arm])
        bootstrap = paired_world_bootstrap(
            rows["FULL"],
            rows[drop_arm],
            comparison_label=route_name,
        )
        decision = apply_route_decision(
            route_name=route_name,
            full_summary=summaries["FULL"],
            drop_summary=summaries[drop_arm],
            per_initialization=per_initialization,
            per_world=per_world,
            bootstrap=bootstrap,
        )
        comparisons[route_name] = {
            "full": summaries["FULL"],
            "drop": summaries[drop_arm],
            "per_initialization": per_initialization,
            "per_world": per_world,
            "bootstrap": bootstrap,
            "decision": decision,
        }
    main_per_initialization = _per_initialization_main(
        rows["FULL"], rows["MAIN"]
    )
    main_per_world = _per_world_main(rows["FULL"], rows["MAIN"])
    main_bootstrap = paired_world_bootstrap(
        rows["FULL"], rows["MAIN"], comparison_label="MAIN", main=True
    )
    main_decision = apply_main_decision(
        full_summary=summaries["FULL"],
        main_summary=summaries["MAIN"],
        per_world=main_per_world,
        bootstrap=main_bootstrap,
    )
    comparisons["MAIN"] = {
        "full": summaries["FULL"],
        "main": summaries["MAIN"],
        "per_initialization": main_per_initialization,
        "per_world": main_per_world,
        "bootstrap": main_bootstrap,
        "decision": main_decision,
    }
    failed = [
        route for route in ROUTE_NAMES
        if comparisons[route]["decision"]["status"] != f"CONFIRM_{route}"
    ]
    if main_decision["status"] != "FULL_BEATS_MAIN":
        failed.append("FULL_vs_MAIN")
    overall_status = STATUS_CONFIRM if not failed else STATUS_NOT_CONFIRMED
    return {
        "schema": RESULT_SCHEMA,
        "status": STATUS_COMPLETE,
        "scientific_status": overall_status,
        "claim_ceiling": "FROZEN_FIVE_ARM_TRAIN_EE_NO_TEST_NO_TRAINING",
        "authority": dict(authority),
        "arms": list(ARMS),
        "route_arms": list(ROUTE_ARMS),
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "initialization_seeds": list(INITIALIZATION_SEEDS),
        "selected_q3_rung": SELECTED_Q3_RUNG,
        "evaluation_split": EVALUATION_SPLIT,
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "expected_episode_count": 390,
        "episode_count": sum(len(rows[arm]) for arm in ARMS),
        "arms_data": {
            arm: _arm_block(rows[arm], summaries[arm]) for arm in ARMS
        },
        # Named blocks make the receipt readable without changing the one
        # canonical source of row data in ``arms_data``.
        "full": _arm_block(rows["FULL"], summaries["FULL"]),
        "drop_c1": _arm_block(rows["DROP_C1"], summaries["DROP_C1"]),
        "drop_c2": _arm_block(rows["DROP_C2"], summaries["DROP_C2"]),
        "drop_c3": _arm_block(rows["DROP_C3"], summaries["DROP_C3"]),
        "main": _arm_block(rows["MAIN"], summaries["MAIN"]),
        "comparisons": comparisons,
        "decision": {
            "route_statuses": {
                route: comparisons[route]["decision"]["status"]
                for route in ROUTE_NAMES
            },
            "main_status": main_decision["status"],
            "failed_comparisons": failed,
            "status": overall_status,
        },
        "elapsed_s": float(elapsed_s),
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": HELD_OUT_EE_EVALUATED,
        "episode_training": EPISODE_TRAINING,
        "evaluator_code_manifest_file_sha256": prepare[
            "evaluator_code_manifest_file_sha256"
        ],
        "evaluator_code_manifest_sha256": prepare["evaluator_code_manifest_sha256"],
        "work_order_file_sha256": EXPECTED_WORK_ORDER_SHA256,
    }


def _load_gate_receipt(
    *,
    gate_dir: Path,
    source_dir: Path,
    prereg_path: Path,
) -> Mapping[str, Any]:
    receipt = screen.authenticate_gate(
        Path(gate_dir),
        source_dir=Path(source_dir),
        prereg_path=Path(prereg_path),
    )
    if receipt.get("selected_q3_rung") != SELECTED_Q3_RUNG:
        raise V04FiveArmError("gate receipt is not selected rung 100")
    return receipt


def run_five_arm(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    gate_dir: Path | None = None,
    source_dir: Path | None = None,
    confirm_dir: Path | None = None,
    prior_screen_dir: Path | None = None,
    main_dir: Path | None = None,
    v03_root: Path = DEFAULT_V03_ROOT,
    prereg_path: Path = DEFAULT_PREREG,
    work_order_path: Path | None = None,
    tle_root: Path = DEFAULT_TLE_ROOT,
    runtime: Any | None = None,
) -> dict[str, Any]:
    """Run exactly 390 TRAIN-only episodes under the sealed policies."""

    started = time.perf_counter()
    prepare, prepared_authority = _load_prepared(Path(output_dir), require_current_code=True)
    gate_path = Path(gate_dir) if gate_dir is not None else Path(prepare["gate_dir"])
    source_path = Path(source_dir) if source_dir is not None else Path(prepare["source_dir"])
    confirm_path = Path(confirm_dir) if confirm_dir is not None else Path(prepare["c3_confirm_dir"])
    prior_screen_path = (
        Path(prior_screen_dir)
        if prior_screen_dir is not None
        else Path(prepare["prior_screen_dir"])
    )
    main_path = Path(main_dir) if main_dir is not None else Path(prepare["main_dir"])
    prereg_path = Path(prereg_path)
    work_order = Path(work_order_path) if work_order_path is not None else Path(prepare["work_order_path"])
    if _file_sha256(work_order) != prepare["work_order_file_sha256"]:
        raise V04FiveArmError("five-arm work-order bytes changed after prepare")
    current_authority = authenticate_current_authority(
        gate_dir=gate_path,
        source_dir=source_path,
        confirm_dir=confirm_path,
        prior_screen_dir=prior_screen_path,
        main_dir=main_path,
        prereg_path=prereg_path,
        work_order_path=work_order,
    )
    _compare_authority(prepared_authority, current_authority)
    if _file_sha256(prereg_path) != prepare["prereg_file_sha256"]:
        raise V04FiveArmError("base PREREG bytes changed after prepare")
    result_path = Path(output_dir) / "result.json"
    seal_path = Path(output_dir) / "result-seal.json"
    if (
        result_path.exists()
        or result_path.is_symlink()
        or seal_path.exists()
        or seal_path.is_symlink()
    ):
        raise V04FiveArmError("refusing to overwrite five-arm result or seal")

    # The only calls below that can open a simulator are after every sealed
    # authority, code, and no-TEST guard above has passed.
    active_runtime = source._default_runtime() if runtime is None else runtime
    record = read_prereg(prereg_path)
    gate_receipt = _load_gate_receipt(
        gate_dir=gate_path,
        source_dir=source_path,
        prereg_path=prereg_path,
    )
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-five-arm-tle-") as temporary:
        archive = active_runtime.frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        main_trainer, main_meta = active_runtime.load_trainer(
            record,
            archive,
            run_dir=main_path,
            users=USERS,
        )
        if not isinstance(main_meta, Mapping) or main_meta.get(
            "checkpoint_sha256"
        ) != EXPECTED_MAIN_CHECKPOINT_SHA256:
            raise V04FiveArmError("loaded Main checkpoint is not the exact frozen checkpoint")
        main_before = active_runtime.network_snapshot(main_trainer)
        main_replay_before = int(active_runtime.replay_size(main_trainer))

        hybrids: dict[int, Any] = {}
        hybrid_before: dict[int, dict[str, Any]] = {}
        for initialization_seed in INITIALIZATION_SEEDS:
            trainer = screen.load_gate_selected_hybrid(
                gate_receipt,
                v03_root=Path(v03_root),
                initialization_seed=initialization_seed,
            )
            _prepare_hybrid(trainer)
            hybrids[initialization_seed] = trainer
            hybrid_before[initialization_seed] = _snapshot_hybrid(trainer)

        route_rows: dict[str, list[dict[str, Any]]] = {
            arm: [] for arm in ROUTE_ARMS
        }
        main_rows: list[dict[str, Any]] = []
        kappa_bits = float(gate._config_pair()[1].kappa_bits)
        for evaluation_seed in EVALUATION_SEEDS:
            field = _field_for_seed(evaluation_seed)
            main_row = evaluate_main_episode(
                main_trainer,
                archive,
                runtime=active_runtime,
                evaluation_seed=evaluation_seed,
                field=field,
                kappa_bits=kappa_bits,
            )
            _validate_episode_row(main_row, policy_label="MAIN")
            main_rows.append(main_row)
            for initialization_seed in INITIALIZATION_SEEDS:
                trainer = hybrids[initialization_seed]
                for arm in ROUTE_ARMS:
                    row = evaluate_route_episode(
                        trainer,
                        archive,
                        evaluation_seed=evaluation_seed,
                        initialization_seed=initialization_seed,
                        policy_label=arm,
                        field=field,
                    )
                    _validate_episode_row(row, policy_label=arm)
                    route_rows[arm].append(row)

        if not active_runtime.networks_equal(main_trainer, main_before):
            raise V04FiveArmError("Main network parameters changed during five-arm evaluation")
        if int(active_runtime.replay_size(main_trainer)) != main_replay_before:
            raise V04FiveArmError("Main replay changed during five-arm evaluation")
        for initialization_seed, trainer in hybrids.items():
            _assert_hybrid_unchanged(trainer, hybrid_before[initialization_seed])

    rows_by_arm: dict[str, Sequence[Mapping[str, Any]]] = {
        **route_rows,
        "MAIN": main_rows,
    }
    if sum(len(rows_by_arm[arm]) for arm in ARMS) != 390:
        raise V04FiveArmError("five-arm episode count is not exactly 390")
    manifest = _read_json(Path(output_dir) / "evaluator-code-manifest.json")
    _validate_code_manifest(manifest, current=True)
    elapsed_s = time.perf_counter() - started
    result = _result_payload(
        prepare=prepare,
        authority=current_authority,
        rows_by_arm=rows_by_arm,
        elapsed_s=elapsed_s,
    )
    result_file_sha = _write_once_json(result_path, result)
    seal = {
        "schema": RESULT_SEAL_SCHEMA,
        "result_file_sha256": result_file_sha,
        "prepare_file_sha256": _file_sha256(Path(output_dir) / "prepare.json"),
        "prepare_seal_file_sha256": _file_sha256(Path(output_dir) / "prepare-seal.json"),
        "evaluator_code_manifest_file_sha256": prepare[
            "evaluator_code_manifest_file_sha256"
        ],
        "evaluator_code_manifest_sha256": prepare["evaluator_code_manifest_sha256"],
        "work_order_file_sha256": prepare["work_order_file_sha256"],
        "episode_count": 390,
        "test_split_opened": TEST_SPLIT_OPENED,
        "held_out_ee_evaluated": HELD_OUT_EE_EVALUATED,
        "episode_training": EPISODE_TRAINING,
    }
    seal_file_sha = _write_once_json(seal_path, seal)
    return {
        "status": result["scientific_status"],
        "result_file_sha256": result_file_sha,
        "result_seal_file_sha256": seal_file_sha,
        "episodes": 390,
        "episode_training": False,
        "test_split_opened": False,
    }


def _verify_result_envelope(
    *,
    result: Mapping[str, Any],
    seal: Mapping[str, Any],
    prepare: Mapping[str, Any],
    authority: Mapping[str, Any],
    result_sha: str,
    root: Path,
) -> None:
    if (
        result.get("schema") != RESULT_SCHEMA
        or result.get("status") != STATUS_COMPLETE
        or result.get("authority") != dict(authority)
        or tuple(result.get("arms", [])) != ARMS
        or tuple(result.get("route_arms", [])) != ROUTE_ARMS
        or tuple(result.get("evaluation_seeds", [])) != EVALUATION_SEEDS
        or tuple(result.get("initialization_seeds", [])) != INITIALIZATION_SEEDS
        or result.get("selected_q3_rung") != SELECTED_Q3_RUNG
        or result.get("evaluation_split") != EVALUATION_SPLIT
        or result.get("users") != USERS
        or result.get("steps_per_episode") != STEPS_PER_EPISODE
        or result.get("expected_episode_count") != 390
        or result.get("episode_count") != 390
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not True
        or result.get("episode_training") is not False
        or result.get("work_order_file_sha256") != EXPECTED_WORK_ORDER_SHA256
    ):
        raise V04FiveArmError("five-arm result envelope is invalid")
    if (
        seal.get("schema") != RESULT_SEAL_SCHEMA
        or seal.get("result_file_sha256") != result_sha
        or seal.get("prepare_file_sha256") != _file_sha256(root / "prepare.json")
        or seal.get("prepare_seal_file_sha256")
        != _file_sha256(root / "prepare-seal.json")
        or seal.get("evaluator_code_manifest_file_sha256")
        != prepare["evaluator_code_manifest_file_sha256"]
        or seal.get("evaluator_code_manifest_sha256")
        != prepare["evaluator_code_manifest_sha256"]
        or seal.get("work_order_file_sha256") != EXPECTED_WORK_ORDER_SHA256
        or seal.get("episode_count") != 390
        or seal.get("test_split_opened") is not False
        or seal.get("held_out_ee_evaluated") is not True
        or seal.get("episode_training") is not False
    ):
        raise V04FiveArmError("five-arm result seal is invalid")


def verify_five_arm(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Receipt-only verification; never opens TLE, trainer, or episodes."""

    root = _regular_dir(Path(output_dir), field="output_dir")
    prepare, authority = _load_prepared(root, require_current_code=True)
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    result = _read_json(result_path)
    seal = _read_json(seal_path)
    result_sha = _file_sha256(result_path)
    _verify_result_envelope(
        result=result,
        seal=seal,
        prepare=prepare,
        authority=authority,
        result_sha=result_sha,
        root=root,
    )
    arm_blocks = result.get("arms_data")
    if not isinstance(arm_blocks, Mapping) or set(arm_blocks) != set(ARMS):
        raise V04FiveArmError("five-arm result arm blocks are incomplete")
    rows_by_arm: dict[str, Sequence[Mapping[str, Any]]] = {}
    for arm in ARMS:
        block = arm_blocks[arm]
        if not isinstance(block, Mapping) or not isinstance(block.get("rows"), list):
            raise V04FiveArmError(f"five-arm {arm} rows are missing")
        rows_by_arm[arm] = block["rows"]
        if result.get(arm.lower()) != block:
            raise V04FiveArmError(f"five-arm {arm} named block drifted")
    recomputed = _result_payload(
        prepare=prepare,
        authority=authority,
        rows_by_arm=rows_by_arm,
        elapsed_s=float(result.get("elapsed_s")),
    )
    if recomputed != result:
        raise V04FiveArmError("five-arm endpoint, decision, or row receipt changed")
    return {
        "status": result["scientific_status"],
        "result_file_sha256": result_sha,
        "rows_per_route_arm": 90,
        "rows_main": 30,
        "episodes": 390,
        "episode_opened": False,
        "receipt_only": True,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)
    prepare = subparsers.add_parser("prepare", help="authenticate and seal without episodes")
    prepare.add_argument("--gate-dir", type=Path, default=DEFAULT_GATE_DIR)
    prepare.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    prepare.add_argument("--confirm-dir", type=Path, default=DEFAULT_C3_CONFIRM_DIR)
    prepare.add_argument("--prior-screen-dir", type=Path, default=DEFAULT_PRIOR_SCREEN_DIR)
    prepare.add_argument("--main-dir", type=Path, default=DEFAULT_MAIN_DIR)
    prepare.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    prepare.add_argument("--work-order", type=Path, default=DEFAULT_WORK_ORDER)
    prepare.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

    run = subparsers.add_parser("run", help="run the 390 frozen TRAIN episodes")
    run.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    run.add_argument("--gate-dir", type=Path, default=None)
    run.add_argument("--source-dir", type=Path, default=None)
    run.add_argument("--confirm-dir", type=Path, default=None)
    run.add_argument("--prior-screen-dir", type=Path, default=None)
    run.add_argument("--main-dir", type=Path, default=None)
    run.add_argument("--v03-root", type=Path, default=DEFAULT_V03_ROOT)
    run.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    run.add_argument("--work-order", type=Path, default=None)
    run.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)

    verify = subparsers.add_parser("verify", help="receipt-only verification")
    verify.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    if args.phase == "prepare":
        receipt = prepare_five_arm(
            gate_dir=args.gate_dir,
            source_dir=args.source_dir,
            confirm_dir=args.confirm_dir,
            prior_screen_dir=args.prior_screen_dir,
            main_dir=args.main_dir,
            prereg_path=args.prereg,
            work_order_path=args.work_order,
            output_dir=args.output_dir,
        )
    elif args.phase == "run":
        receipt = run_five_arm(
            output_dir=args.output_dir,
            gate_dir=args.gate_dir,
            source_dir=args.source_dir,
            confirm_dir=args.confirm_dir,
            prior_screen_dir=args.prior_screen_dir,
            main_dir=args.main_dir,
            v03_root=args.v03_root,
            prereg_path=args.prereg,
            work_order_path=args.work_order,
            tle_root=args.tle_root,
        )
    else:
        receipt = verify_five_arm(args.output_dir)
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - production CLI
    raise SystemExit(main())
