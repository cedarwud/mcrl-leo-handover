#!/usr/bin/env python3
"""V0.12 zero-energy-supported C3 TRAIN-only oracle gate.

The runner keeps frozen learned Q1 and exact execution-equivalent OPS3 O2,
then compares their shared action against two ordered current-slot C3 teacher
surfaces.  It performs no learner/optimizer update and has no TEST path.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np
import torch


REPO = Path(__file__).resolve().parents[2]
OLD_SCRATCH = REPO / ".scratch" / "c3-v04"
for _path in (OLD_SCRATCH, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_learnability_gate as old_gate  # noqa: E402
from mcrl.algorithms.ee_axis_v04_hybrid import (  # noqa: E402
    extract_frozen_meanmax_head,
)
from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import (  # noqa: E402
    OPS3_KAPPA_BITS,
    OPS3_LAMBDA_BITS_PER_J,
)
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    OPS3_LIVE_SCHEMA,
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_zero_marginal_c3 import (  # noqa: E402
    ZERO_MARGINAL_C3_SCHEMA,
    assert_surface_identity,
    build_hr_surface,
    build_zr_surface,
)
from mcrl.runtime.ee_axis_zero_marginal_c3_live import (  # noqa: E402
    ZERO_MARGINAL_C3_LIVE_SCHEMA,
    measure_zero_marginal_c3,
    physics_signature,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402


RESULT_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v012-zero-energy-c3-oracle-contract-v1"

WORLD_SEEDS = (2026104801, 2026104802)
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = ("DROP_C3", "FULL_ZR", "FULL_HR")
USERS = 100
STEPS_PER_EPISODE = 10
FIELD_COMPONENT = "MCRL_V012_ZERO_ENERGY_C3_ORACLE_V1"
FIELD_EXCLUDES = (
    "arm",
    "initialization_seed",
    "policy_label",
    "action",
    "target",
    "outcome",
)
CONTRACT_PATH = (
    REPO
    / "docs"
    / "MULTI-CATFISH-MCRL-V012-ZERO-ENERGY-C3-ORACLE-PREREG-2026-09-03.md"
)
RUNTIME_PATHS = (
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_zero_marginal_c3_live.py",
)
PYTHON_SOURCE_ROOTS = (REPO / "src" / "mcrl", OLD_SCRATCH, REPO / "scripts")
FROZEN_STATUS = "Status: **FROZEN BEFORE OUTCOME ACCESS**"


class V012OracleError(RuntimeError):
    """A V0.12 authority, mechanics, or acceptance condition failed closed."""


def _canonical_json_default(value: object) -> bool | int | float:
    """Normalize finite NumPy scalars without admitting arrays or objects."""

    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("NumPy floating scalar is not finite")
        return result
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
            default=_canonical_json_default,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V012OracleError("payload is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V012OracleError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def python_source_authority() -> dict[str, Any]:
    """Seal every Python source file reachable through the V0.12 import roots."""

    files: list[Path] = []
    for root in PYTHON_SOURCE_ROOTS:
        if root.is_symlink() or not root.is_dir():
            raise V012OracleError(f"expected a regular source directory: {root}")
        files.extend(
            path
            for path in root.rglob("*.py")
            if path.is_file() and not path.is_symlink()
        )
    relative_hashes = {
        str(path.relative_to(REPO)): file_sha256(path)
        for path in sorted(files, key=lambda item: str(item.relative_to(REPO)))
    }
    if not relative_hashes:
        raise V012OracleError("Python source authority set is empty")
    return {
        "python_source_file_count": len(relative_hashes),
        "python_source_file_set_sha256": canonical_sha256(relative_hashes),
    }


def assert_contract_frozen() -> None:
    if FROZEN_STATUS not in CONTRACT_PATH.read_text(encoding="utf-8"):
        raise V012OracleError(
            "V0.12 contract is not frozen; refusing to open an oracle outcome"
        )


def array_sha256(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def field_for_world(world_seed: int) -> KeyedFadingField:
    if int(world_seed) not in WORLD_SEEDS:
        raise V012OracleError("world seed is outside the frozen V0.12 panel")
    return KeyedFadingField.from_components(FIELD_COMPONENT, int(world_seed))


def contract_receipt() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "world_seeds": list(WORLD_SEEDS),
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "arm_heads": {
            "DROP_C3": ["Q1", "O2_OPS3"],
            "FULL_ZR": ["Q1", "O2_OPS3", "O3_ZR"],
            "FULL_HR": ["Q1", "O2_OPS3", "O3_HR"],
        },
        "candidate_order": ["ZR", "HR"],
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(WORLD_SEEDS) * len(LINEAGES) * len(ARMS),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "background": "MASKED_ARGMAX_Q1_PLUS_O2",
        "summation": "left_to_right_unweighted",
        "selection": "one_common_mask_one_argmax_one_action",
        "compatibility": {
            "role": "teacher_target_support_not_action_mask",
            "tolerance": 0.0,
            "components": [
                "served_vector",
                "active_beam_set",
                "active_satellite_set",
                "per_beam_rf_power",
                "canonical_network_power",
            ],
        },
        "field_components": [FIELD_COMPONENT, "world_seed"],
        "field_excludes": list(FIELD_EXCLUDES),
        "zero_marginal_c3_schema": ZERO_MARGINAL_C3_SCHEMA,
        "zero_marginal_c3_live_schema": ZERO_MARGINAL_C3_LIVE_SCHEMA,
        "ops3_live_schema": OPS3_LIVE_SCHEMA,
        "lambda_bits_per_j_hex": OPS3_LAMBDA_BITS_PER_J.hex(),
        "kappa_bits_hex": OPS3_KAPPA_BITS.hex(),
        "gate": {
            "pooled_full_strictly_above_drop_c3": True,
            "every_world_strictly_above_drop_c3": True,
            "positive_lineages_per_world_minimum": 2,
            "service_noninferior_pooled_and_every_world": True,
            "service_noninferior_lineages_per_world_minimum": 2,
            "one_user_step_shortfall_fails": True,
            "active_beam_steps_not_above_pooled_or_world": True,
            "active_satellite_steps_not_above_pooled_or_world": True,
            "nonzero_supported_positive_spread": True,
            "nonzero_executed_action_exposure": True,
            "every_changed_action_compatible": True,
            "executed_joint_adds_no_beam_or_satellite": True,
            "executed_joint_network_power_nonincrease": True,
        },
        "selection_table": {
            "ZR": "GO_ZR_C3_LEARNABILITY_PREREG_ONLY",
            "not_ZR_and_HR": "GO_HR_C3_LEARNABILITY_PREREG_ONLY",
            "none": "STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM",
        },
    }


def _q1_parameter_sha256(network: Any) -> str:
    digest = hashlib.sha256()
    for name, value in network.state_dict().items():
        tensor = value.detach().cpu()
        digest.update(str(name).encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest()


def load_frozen_q1(v03_root: Path, lineage: int) -> tuple[Any, dict[str, Any]]:
    if int(lineage) not in LINEAGES:
        raise V012OracleError("lineage is outside the frozen V0.12 set")
    config, _ = old_gate._config_pair()
    spec = old_gate._spec_for_seed(Path(v03_root), int(lineage))
    network, receipt = extract_frozen_meanmax_head(
        spec, config, head_index=0, device="cpu"
    )
    network.eval()
    network.requires_grad_(False)
    if any(parameter.requires_grad for parameter in network.parameters()):
        raise V012OracleError("frozen Q1 still has trainable parameters")
    payload = receipt.as_dict()
    payload["parameter_sha256"] = _q1_parameter_sha256(network)
    return network, payload


def _q1_values(network: Any, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
    values = network(
        torch.tensor(np.asarray(states, dtype=np.float32)),
        torch.tensor(np.asarray(masks, dtype=np.bool_)),
    ).detach().cpu().numpy()
    result = np.asarray(values, dtype=np.float64)
    if result.shape != masks.shape or not np.all(np.isfinite(result)):
        raise V012OracleError("Q1 surface is malformed")
    return result


def select_actions(
    q1: np.ndarray,
    o2: np.ndarray,
    o3: np.ndarray,
    mask: np.ndarray,
    *,
    include_c3: bool,
) -> np.ndarray:
    legal = np.asarray(mask)
    arrays = tuple(np.asarray(value, dtype=np.float64) for value in (q1, o2, o3))
    if legal.dtype != np.bool_ or legal.ndim != 2 or legal.shape[1] != NUM_ACTIONS:
        raise V012OracleError(
            f"mask must be a Boolean matrix with {NUM_ACTIONS} native actions"
        )
    if any(
        value.shape != legal.shape or not np.all(np.isfinite(value))
        for value in arrays
    ):
        raise V012OracleError("head surfaces are nonfinite or misaligned")
    if not np.all(np.any(legal, axis=1)):
        raise V012OracleError("each user must have a legal native action")
    scores = arrays[0] + arrays[1]
    if include_c3:
        scores = scores + arrays[2]
    return np.argmax(np.where(legal, scores, -np.inf), axis=1).astype(np.int64)


def _live_digest(environment: Any, rng: np.random.Generator) -> str:
    step_env = environment.environment if hasattr(environment, "environment") else environment
    digest = hashlib.sha256()
    for name, value in (
        ("step", step_env._step_index),
        ("driver_step", step_env.driver.step_index),
        ("previous_power", step_env._previous_link_power_w),
        ("previous_rate", step_env._previous_served_rate_bps),
        ("pending_age", step_env._pending_segment_age),
        ("user_ecef", step_env.driver.user_ecef_km()),
        ("candidate_identity", id(step_env._candidates)),
        ("driver_start_utc", step_env.driver._start_utc),
    ):
        digest.update(name.encode("ascii"))
        if isinstance(value, np.ndarray):
            digest.update(array_sha256(value).encode("ascii"))
        else:
            digest.update(repr(value).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._previous_association)).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._segments)).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._previous_demand)).encode("utf-8"))
    digest.update(
        repr(tuple(ledger.previous for ledger in step_env._ledgers)).encode("utf-8")
    )
    previous_radiating = step_env._previous_radiating
    for name, value in (
        ("previous_radiating_norad", previous_radiating.norad_ids),
        ("previous_radiating_cell", previous_radiating.cell_ids),
        ("previous_radiating_power", previous_radiating.power_w),
    ):
        digest.update(name.encode("ascii"))
        digest.update(array_sha256(value).encode("ascii"))
    digest.update(repr(copy.deepcopy(rng.bit_generator.state)).encode("utf-8"))
    tracker = getattr(step_env.driver, "_tracker", None)
    if tracker is not None:
        digest.update(repr(copy.deepcopy(tracker.__dict__)).encode("utf-8"))
    return digest.hexdigest()


def _initial_world_sha(environment: Any, observation: Any) -> str:
    return canonical_sha256(
        {
            "epoch": environment.epoch.isoformat(),
            "state": array_sha256(observation.state_matrix),
            "mask": array_sha256(observation.masks),
            "norads": array_sha256(
                np.stack(
                    [table.norad_ids for table in observation.candidates.slot_tables]
                )
            ),
            "cells": array_sha256(
                np.stack(
                    [table.cell_ids for table in observation.candidates.slot_tables]
                )
            ),
        }
    )


def _spread_count(values: np.ndarray, mask: np.ndarray) -> int:
    return sum(
        int(np.ptp(values[uid, np.flatnonzero(mask[uid])]) > 0.0)
        for uid in range(mask.shape[0])
    )


def _build_c3_surfaces(
    *,
    formula: str,
    measurements: Any,
    interval_s: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    if float(measurements.interval_s).hex() != float(interval_s).hex():
        raise V012OracleError("live measurement interval drifted from the anchor")
    users = measurements.reference_actions.size
    o3 = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    identity_passed = True
    positive_count = 0
    positive_supported = 0
    unsupported_positive = 0
    for uid in range(users):
        kwargs = {
            "candidate_rate_bps": measurements.candidate_rate_bps[uid],
            "compatibility": measurements.compatible[uid],
            "legal_mask": measurements.legal_mask[uid],
            "reference_action": int(measurements.reference_actions[uid]),
            "interval_s": float(interval_s),
            "kappa_bits": OPS3_KAPPA_BITS,
        }
        if formula == "ZR":
            surface = build_zr_surface(
                baseline_rate_bps=measurements.reference_rate_bps[uid], **kwargs
            )
        elif formula == "HR":
            if measurements.removed_rate_bps is None:
                raise V012OracleError("HR measurements omit focal-removed rates")
            surface = build_hr_surface(
                baseline_rate_bps=measurements.removed_rate_bps[uid], **kwargs
            )
        else:
            raise V012OracleError("unknown C3 formula")
        identity = assert_surface_identity(surface)
        identity_passed = identity_passed and bool(identity.passed)
        row_positive = surface.q3_values > 0.0
        positive_count += int(np.count_nonzero(row_positive))
        positive_supported += int(
            np.count_nonzero(row_positive & measurements.compatible[uid])
        )
        unsupported_positive += int(
            np.count_nonzero(row_positive & ~measurements.compatible[uid])
        )
        o3[uid] = surface.q3_values
    if unsupported_positive:
        raise V012OracleError("a positive C3 target escaped compatibility support")
    components = {
        "served": int(np.count_nonzero(measurements.served_equal)),
        "active_beams": int(np.count_nonzero(measurements.active_beams_equal)),
        "active_satellites": int(
            np.count_nonzero(measurements.active_satellites_equal)
        ),
        "rf_power": int(np.count_nonzero(measurements.rf_power_equal)),
        "network_power": int(np.count_nonzero(measurements.network_power_equal)),
        "all": int(np.count_nonzero(measurements.compatible)),
    }
    hashed_measurements: list[object] = [
        measurements.reference_actions,
        measurements.legal_mask,
        measurements.reference_rate_bps,
        measurements.candidate_rate_bps,
        measurements.replacement_delta_bits,
        measurements.compatible,
        measurements.served_equal,
        measurements.active_beams_equal,
        measurements.active_satellites_equal,
        measurements.rf_power_equal,
        measurements.network_power_equal,
    ]
    if measurements.removed_rate_bps is not None:
        hashed_measurements.append(measurements.removed_rate_bps)
    if measurements.insertion_delta_bits is not None:
        hashed_measurements.append(measurements.insertion_delta_bits)
    return o3, {
        "formula": formula,
        "identity_passed": identity_passed,
        "positive_target_count": positive_count,
        "supported_positive_target_count": positive_supported,
        "unsupported_positive_target_count": unsupported_positive,
        "compatibility_component_counts": components,
        "counterfactual_evaluations": int(
            measurements.counterfactual_evaluations
        ),
        "reference_signature_sha256": measurements.reference_signature_sha256,
        "measurements_sha256": array_sha256(*hashed_measurements),
    }


def _joint_support_receipt(
    step_env: Any,
    rng: np.random.Generator,
    reference: np.ndarray,
    selected: np.ndarray,
    interval_s: float,
) -> dict[str, Any]:
    changed = int(np.count_nonzero(reference != selected))
    if changed == 0:
        return {
            "status": "NO_EXPOSURE",
            "changed_users": 0,
            "no_new_active_beam": True,
            "no_new_active_satellite": True,
            "network_power_nonincrease": True,
            "passed": True,
        }
    before = _live_digest(step_env, rng)
    baseline = step_env.evaluate_actions(reference, rng)
    treatment = step_env.evaluate_actions(selected, rng)
    after = _live_digest(step_env, rng)
    if before != after:
        raise V012OracleError("joint support diagnostic mutated environment or RNG")
    base_signature = physics_signature(baseline)
    full_signature = physics_signature(treatment)
    base_beams = {
        tuple(int(value) for value in row)
        for row in base_signature.active_beam_keys.tolist()
    }
    full_beams = {
        tuple(int(value) for value in row)
        for row in full_signature.active_beam_keys.tolist()
    }
    base_satellites = set(int(value) for value in base_signature.active_satellites)
    full_satellites = set(int(value) for value in full_signature.active_satellites)
    tolerance = 1024.0 * np.finfo(np.float64).eps * max(
        1.0,
        abs(base_signature.system_power_w),
        abs(full_signature.system_power_w),
    )
    no_new_beam = full_beams <= base_beams
    no_new_satellite = full_satellites <= base_satellites
    power_nonincrease = (
        full_signature.system_power_w
        <= base_signature.system_power_w + tolerance
    )
    delta_bits = float(interval_s) * math.fsum(
        float(value)
        for value in (
            np.asarray(treatment.link_rate_bps, dtype=np.float64)
            - np.asarray(baseline.link_rate_bps, dtype=np.float64)
        )
    )
    delta_energy = float(interval_s) * (
        float(treatment.system_power_w) - float(baseline.system_power_w)
    )
    return {
        "status": "OBSERVED",
        "changed_users": changed,
        "delta_bits": delta_bits,
        "delta_energy_j": delta_energy,
        "baseline_active_beams": len(base_beams),
        "selected_active_beams": len(full_beams),
        "baseline_active_satellites": len(base_satellites),
        "selected_active_satellites": len(full_satellites),
        "baseline_network_power_w": base_signature.system_power_w,
        "selected_network_power_w": full_signature.system_power_w,
        "power_tolerance_w": tolerance,
        "new_active_beams": sorted(full_beams - base_beams),
        "new_active_satellites": sorted(full_satellites - base_satellites),
        "no_new_active_beam": no_new_beam,
        "no_new_active_satellite": no_new_satellite,
        "network_power_nonincrease": power_nonincrease,
        "passed": bool(no_new_beam and no_new_satellite and power_nonincrease),
    }


def evaluate_episode(
    *,
    q1: Any,
    q1_receipt: Mapping[str, Any],
    archive: Any,
    world_seed: int,
    field: KeyedFadingField,
    lineage: int,
    arm: str,
) -> dict[str, Any]:
    if arm not in ARMS or int(lineage) not in LINEAGES:
        raise V012OracleError("episode arm/lineage is outside the frozen panel")
    if int(world_seed) not in WORLD_SEEDS:
        raise V012OracleError("episode world is outside the frozen panel")
    if field.root_digest != field_for_world(world_seed).root_digest:
        raise V012OracleError("episode does not use its frozen common field")

    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(
        int(world_seed)
    )
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    step_env = environment.environment
    interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    initial_world = _initial_world_sha(environment, observation)
    q1_before = _q1_parameter_sha256(q1)
    started = time.perf_counter()

    total_bits = 0.0
    total_energy = 0.0
    served_steps = 0
    active_beam_steps = 0
    active_satellite_steps = 0
    c3_spread = 0
    positive_targets = 0
    supported_positive_targets = 0
    action_exposure = 0
    compatible_action_count = 0
    changed_actions_compatible = True
    joint_support_passed = True
    method_passed = True
    per_step: list[dict[str, Any]] = []

    with torch.no_grad():
        for step_index in range(STEPS_PER_EPISODE):
            native = encode_ee_axis_state(step_env, observation)
            mask = np.asarray(native.action_masks, dtype=np.bool_)
            q1_values = _q1_values(q1, native.state_matrix, mask)
            zero = np.zeros_like(q1_values)
            q1_reference = select_actions(
                q1_values, zero, zero, mask, include_c3=False
            )
            before = _live_digest(environment, env_rng)
            anchor = snapshot_ops3_anchor(step_env, observation)
            projection = project_ops3_anchor(anchor)
            ops3 = build_ops3_live_surfaces(anchor, projection, q1_reference)
            o2 = np.stack(
                [np.asarray(surface.q2_values, dtype=np.float64) for surface in ops3]
            )
            o2_sha_before = array_sha256(o2)
            background = select_actions(
                q1_values, o2, zero, mask, include_c3=False
            )
            selected = np.array(background, dtype=np.int64, copy=True)
            o3 = np.zeros_like(q1_values)
            method: dict[str, Any] = {
                "kind": "DROP_C3",
                "identity_passed": True,
                "positive_target_count": 0,
                "supported_positive_target_count": 0,
                "compatibility_component_counts": {
                    name: 0
                    for name in (
                        "served",
                        "active_beams",
                        "active_satellites",
                        "rf_power",
                        "network_power",
                        "all",
                    )
                },
            }
            measurements = None

            if arm in {"FULL_ZR", "FULL_HR"}:
                formula = "ZR" if arm == "FULL_ZR" else "HR"
                measurements = measure_zero_marginal_c3(
                    step_env,
                    observation=observation,
                    reference_actions=background,
                    rng=env_rng,
                    include_insertion=formula == "HR",
                    interval_s=interval_s,
                )
                o3, method = _build_c3_surfaces(
                    formula=formula,
                    measurements=measurements,
                    interval_s=interval_s,
                )
                selected = select_actions(
                    q1_values, o2, o3, mask, include_c3=True
                )

            reference_zero = all(
                float(o2[uid, int(q1_reference[uid])]) == 0.0
                for uid in range(USERS)
            ) and all(
                float(o3[uid, int(background[uid])]) == 0.0
                for uid in range(USERS)
            )
            illegal_zero = bool(np.all(o3[~mask] == 0.0))
            base_evaluation = step_env.evaluate_actions(background, env_rng)
            opening_equal = all(
                bool(ops3[uid].opening_service_feasible[int(background[uid])])
                == bool(base_evaluation.resolution.served[uid])
                for uid in range(USERS)
            )
            after = _live_digest(environment, env_rng)
            changed = np.flatnonzero(selected != background)
            step_changed_compatible = True
            changed_positive = True
            if measurements is not None:
                for uid_raw in changed.tolist():
                    uid = int(uid_raw)
                    action = int(selected[uid])
                    step_changed_compatible = step_changed_compatible and bool(
                        measurements.compatible[uid, action]
                    )
                    changed_positive = changed_positive and bool(o3[uid, action] > 0.0)
            elif changed.size:
                raise V012OracleError("DROP_C3 changed from its own background")
            if not step_changed_compatible or not changed_positive:
                raise V012OracleError(
                    "a changed production action lacks positive compatible C3 credit"
                )
            joint_support = _joint_support_receipt(
                step_env, env_rng, background, selected, interval_s
            )
            mechanics = {
                "live_state_and_rng_unchanged": before == after,
                "common_mask": all(
                    np.array_equal(surface.legal_mask, mask[uid])
                    for uid, surface in enumerate(ops3)
                )
                and (measurements is None or np.array_equal(measurements.legal_mask, mask)),
                "reference_rows_exact_zero": reference_zero,
                "illegal_rows_exact_zero": illegal_zero,
                "opening_service_gate_equal": opening_equal,
                "o2_immutable": o2_sha_before == array_sha256(o2),
                "changed_actions_compatible": step_changed_compatible,
                "changed_actions_strictly_positive_c3": changed_positive,
                "joint_support_passed": bool(joint_support["passed"]),
                "background_sha256": array_sha256(background),
            }
            mechanics["passed"] = bool(
                all(
                    value
                    for key, value in mechanics.items()
                    if key
                    not in {
                        "background_sha256",
                        # This is a binding outcome gate, not a plumbing
                        # assertion.  Retain and execute the safe production
                        # action so a failing shard yields a complete receipt.
                        "joint_support_passed",
                        "passed",
                    }
                )
            )
            if not mechanics["passed"]:
                raise V012OracleError("binding per-step mechanics failed")

            flips = int(changed.size)
            action_exposure += flips
            c3_spread += _spread_count(o3, mask)
            positive_targets += int(method["positive_target_count"])
            supported_positive_targets += int(
                method["supported_positive_target_count"]
            )
            compatible_action_count += int(
                method["compatibility_component_counts"]["all"]
            )
            changed_actions_compatible = (
                changed_actions_compatible and step_changed_compatible
            )
            joint_support_passed = joint_support_passed and bool(
                joint_support["passed"]
            )
            method_passed = method_passed and bool(method["identity_passed"])

            result = environment.step(selected, env_rng)
            outcome = environment.last_outcome
            rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
            power = float(outcome.system_power_w)
            if (
                rates.shape != (USERS,)
                or not np.all(np.isfinite(rates))
                or np.any(rates < 0.0)
                or not math.isfinite(power)
                or power <= 0.0
            ):
                raise V012OracleError("canonical EE inputs are malformed")
            bits = interval_s * math.fsum(float(value) for value in rates)
            energy = interval_s * power
            active_beams = int(outcome.radiating.count)
            active_satellites = len(
                {int(value) for value in outcome.radiating.norad_ids.tolist()}
            )
            total_bits += bits
            total_energy += energy
            served_steps += int(outcome.resolution.served_count)
            active_beam_steps += active_beams
            active_satellite_steps += active_satellites
            per_step.append(
                {
                    "step_index": step_index,
                    "total_bits": float(bits),
                    "total_energy_j": float(energy),
                    "served_user_steps": int(outcome.resolution.served_count),
                    "active_beam_count": active_beams,
                    "active_satellite_count": active_satellites,
                    "action_exposure": flips,
                    "selected_actions": [int(value) for value in selected.tolist()],
                    "surface_sha256": {
                        "q1": array_sha256(q1_values),
                        "o2": array_sha256(o2),
                        "o3": array_sha256(o3),
                        "mask": array_sha256(mask),
                        "q1_reference": array_sha256(q1_reference),
                        "background": array_sha256(background),
                    },
                    "mechanics": mechanics,
                    "method": method,
                    "joint_support": joint_support,
                }
            )
            if result.done:
                if step_index != STEPS_PER_EPISODE - 1:
                    raise V012OracleError("episode terminated before ten steps")
                break
            observation = outcome.observation

    q1_after = _q1_parameter_sha256(q1)
    if q1_before != q1_after:
        raise V012OracleError("frozen Q1 changed during oracle episode")
    return {
        "schema": EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": int(lineage),
        "world_seed": int(world_seed),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "users": USERS,
        "steps": STEPS_PER_EPISODE,
        "initial_world_sha256": initial_world,
        "field_root_digest": field.root_digest,
        "q1_checkpoint": dict(q1_receipt),
        "q1_parameter_sha256_before": q1_before,
        "q1_parameter_sha256_after": q1_after,
        "total_bits": float(total_bits),
        "total_energy_j": float(total_energy),
        "ratio_of_sums_ee_bits_per_j": float(total_bits / total_energy),
        "served_user_steps": served_steps,
        "served_fraction": served_steps / (USERS * STEPS_PER_EPISODE),
        "active_beam_steps": active_beam_steps,
        "active_satellite_steps": active_satellite_steps,
        "c3_legal_spread_count": c3_spread,
        "positive_target_count": positive_targets,
        "supported_positive_target_count": supported_positive_targets,
        "compatible_action_count": compatible_action_count,
        "action_exposure": action_exposure,
        "changed_actions_compatible": changed_actions_compatible,
        "joint_support_passed": joint_support_passed,
        "method_passed": method_passed,
        "candidate_specific_identity_passed": method_passed,
        "mechanics_passed": all(step["mechanics"]["passed"] for step in per_step),
        "per_step": per_step,
        "elapsed_s": time.perf_counter() - started,
    }


def run_shard(
    *,
    world_seed: int,
    arm: str,
    lineage: int,
    output_dir: Path,
    tle_root: Path,
    prereg_path: Path,
    v03_root: Path,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V012OracleError(f"refusing to overwrite {output}")
    assert_contract_frozen()
    record = read_prereg(prereg_path)
    q1, q1_receipt = load_frozen_q1(v03_root, lineage)
    field = field_for_world(world_seed)
    with tempfile.TemporaryDirectory(prefix="mcrl-v012-zero-energy-tle-") as temporary:
        archive = screen._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        row = evaluate_episode(
            q1=q1,
            q1_receipt=q1_receipt,
            archive=archive,
            world_seed=int(world_seed),
            field=field,
            lineage=int(lineage),
            arm=arm,
        )
    contract = contract_receipt()
    ephemeris = record.sections.get("ephemeris", {})
    if not isinstance(ephemeris, Mapping) or not isinstance(
        ephemeris.get("file_set_sha256"), str
    ):
        raise V012OracleError("frozen prereg omits the TLE file-set digest")
    source_authority = {
        "prereg_file_sha256": file_sha256(Path(prereg_path)),
        "prereg_record_digest": str(record.digest),
        "tle_file_set_sha256": str(ephemeris["file_set_sha256"]),
        **python_source_authority(),
    }
    payload = {
        "schema": SHARD_SCHEMA,
        "shard_id": f"{int(world_seed)}-{arm}-{int(lineage)}",
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "contract_file_sha256": file_sha256(CONTRACT_PATH),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
        },
        "source_authority": source_authority,
        "row": row,
    }
    payload["row_sha256"] = canonical_sha256(row)
    output.mkdir(parents=True, exist_ok=False)
    (output / "shard.json").write_bytes(_canonical_bytes(payload))
    print(
        f"{world_seed}/{arm}/{lineage}: "
        f"EE={row['ratio_of_sums_ee_bits_per_j']:.9g} "
        f"elapsed={row['elapsed_s']:.1f}s"
    )
    return payload


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise V012OracleError("cannot pool an empty row set")
    bits = math.fsum(float(row["total_bits"]) for row in rows)
    energy = math.fsum(float(row["total_energy_j"]) for row in rows)
    served = sum(int(row["served_user_steps"]) for row in rows)
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_fraction": served / (len(rows) * USERS * STEPS_PER_EPISODE),
        "active_beam_steps": sum(int(row["active_beam_steps"]) for row in rows),
        "active_satellite_steps": sum(
            int(row["active_satellite_steps"]) for row in rows
        ),
        "c3_legal_spread_count": sum(
            int(row["c3_legal_spread_count"]) for row in rows
        ),
        "supported_positive_target_count": sum(
            int(row["supported_positive_target_count"]) for row in rows
        ),
        "compatible_action_count": sum(
            int(row["compatible_action_count"]) for row in rows
        ),
        "action_exposure": sum(int(row["action_exposure"]) for row in rows),
    }


def _pair_gate(
    *,
    label: str,
    full_arm: str,
    rows: Sequence[Mapping[str, Any]],
    pooled_by_arm: Mapping[str, Mapping[str, Any]],
    pooled_by_world_and_arm: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    drop_arm = "DROP_C3"
    indexed = {
        (
            int(row["world_seed"]),
            str(row["arm"]),
            int(row["initialization_seed"]),
        ): row
        for row in rows
    }
    full_pool = pooled_by_arm[full_arm]
    drop_pool = pooled_by_arm[drop_arm]
    full_ee = float(full_pool["ratio_of_sums_ee_bits_per_j"])
    drop_ee = float(drop_pool["ratio_of_sums_ee_bits_per_j"])
    pooled_delta = full_ee - drop_ee
    by_world: dict[str, Any] = {}
    every_world_positive = True
    every_world_service = True
    every_world_beams = True
    every_world_satellites = True
    every_world_lineages = True
    every_world_service_lineages = True

    for world in WORLD_SEEDS:
        full_world = pooled_by_world_and_arm[str(world)][full_arm]
        drop_world = pooled_by_world_and_arm[str(world)][drop_arm]
        world_delta = float(full_world["ratio_of_sums_ee_bits_per_j"]) - float(
            drop_world["ratio_of_sums_ee_bits_per_j"]
        )
        positive_lineages = 0
        service_lineages = 0
        lineage_receipts: dict[str, Any] = {}
        for lineage in LINEAGES:
            full = indexed[(world, full_arm, lineage)]
            drop = indexed[(world, drop_arm, lineage)]
            delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(
                drop["ratio_of_sums_ee_bits_per_j"]
            )
            service_delta = int(full["served_user_steps"]) - int(
                drop["served_user_steps"]
            )
            positive_lineages += int(delta > 0.0)
            service_lineages += int(service_delta >= 0)
            lineage_receipts[str(lineage)] = {
                "delta_ee_bits_per_j": delta,
                "relative_delta_ee": delta
                / float(drop["ratio_of_sums_ee_bits_per_j"]),
                "delta_served_user_steps": service_delta,
                "delta_active_beam_steps": int(full["active_beam_steps"])
                - int(drop["active_beam_steps"]),
                "delta_active_satellite_steps": int(
                    full["active_satellite_steps"]
                )
                - int(drop["active_satellite_steps"]),
            }
        world_service = int(full_world["served_user_steps"]) >= int(
            drop_world["served_user_steps"]
        )
        world_beams = int(full_world["active_beam_steps"]) <= int(
            drop_world["active_beam_steps"]
        )
        world_satellites = int(full_world["active_satellite_steps"]) <= int(
            drop_world["active_satellite_steps"]
        )
        every_world_positive = every_world_positive and world_delta > 0.0
        every_world_service = every_world_service and world_service
        every_world_beams = every_world_beams and world_beams
        every_world_satellites = every_world_satellites and world_satellites
        every_world_lineages = every_world_lineages and positive_lineages >= 2
        every_world_service_lineages = (
            every_world_service_lineages and service_lineages >= 2
        )
        by_world[str(world)] = {
            "delta_ee_bits_per_j": world_delta,
            "relative_delta_ee": world_delta
            / float(drop_world["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": int(full_world["served_user_steps"])
            - int(drop_world["served_user_steps"]),
            "delta_active_beam_steps": int(full_world["active_beam_steps"])
            - int(drop_world["active_beam_steps"]),
            "delta_active_satellite_steps": int(
                full_world["active_satellite_steps"]
            )
            - int(drop_world["active_satellite_steps"]),
            "positive_lineages": positive_lineages,
            "service_noninferior_lineages": service_lineages,
            "pooled_service_noninferior": world_service,
            "active_beam_steps_not_above": world_beams,
            "active_satellite_steps_not_above": world_satellites,
            "by_lineage": lineage_receipts,
        }

    full_rows = [row for row in rows if str(row["arm"]) == full_arm]
    drop_rows = [row for row in rows if str(row["arm"]) == drop_arm]
    mechanics = all(
        bool(row["mechanics_passed"]) for row in (*full_rows, *drop_rows)
    )
    method = all(bool(row["method_passed"]) for row in full_rows)
    identity = all(
        bool(row["candidate_specific_identity_passed"]) for row in full_rows
    )
    spread = int(full_pool["c3_legal_spread_count"])
    supported_positive = int(full_pool["supported_positive_target_count"])
    exposure = int(full_pool["action_exposure"])
    changed_compatible = all(
        bool(row["changed_actions_compatible"]) for row in full_rows
    )
    joint_support = all(bool(row["joint_support_passed"]) for row in full_rows)
    pooled_service = int(full_pool["served_user_steps"]) >= int(
        drop_pool["served_user_steps"]
    )
    pooled_beams = int(full_pool["active_beam_steps"]) <= int(
        drop_pool["active_beam_steps"]
    )
    pooled_satellites = int(full_pool["active_satellite_steps"]) <= int(
        drop_pool["active_satellite_steps"]
    )

    hard_stops: list[str] = []
    for passed, message in (
        (mechanics, f"{label} mechanics failed"),
        (method, f"{label} formula method failed"),
        (identity, f"{label} formula identity failed"),
        (spread > 0, f"{label} has zero legal-action C3 spread"),
        (
            supported_positive > 0,
            f"{label} has zero supported-positive targets",
        ),
        (exposure > 0, f"{label} has zero executed-action exposure"),
        (
            changed_compatible,
            f"{label} changed an action outside compatibility support",
        ),
        (
            joint_support,
            f"{label} joint action expanded current energy support",
        ),
        (pooled_delta > 0.0, f"{label} pooled EE is not strictly positive"),
        (
            every_world_positive,
            f"{label} is not EE-positive in every frozen world",
        ),
        (
            every_world_lineages,
            f"{label} has fewer than two positive lineages in a world",
        ),
        (pooled_service, f"{label} pooled service guard failed"),
        (every_world_service, f"{label} per-world service guard failed"),
        (
            every_world_service_lineages,
            f"{label} has fewer than two service-safe lineages in a world",
        ),
        (pooled_beams, f"{label} pooled active-beam guard failed"),
        (every_world_beams, f"{label} per-world active-beam guard failed"),
        (
            pooled_satellites,
            f"{label} pooled active-satellite guard failed",
        ),
        (
            every_world_satellites,
            f"{label} per-world active-satellite guard failed",
        ),
    ):
        if not passed:
            hard_stops.append(message)

    return {
        "label": label,
        "full_arm": full_arm,
        "drop_arm": drop_arm,
        "passed": not hard_stops,
        "pooled": {
            "delta_ee_bits_per_j": pooled_delta,
            "relative_delta_ee": pooled_delta / drop_ee,
            "delta_served_user_steps": int(full_pool["served_user_steps"])
            - int(drop_pool["served_user_steps"]),
            "delta_active_beam_steps": int(full_pool["active_beam_steps"])
            - int(drop_pool["active_beam_steps"]),
            "delta_active_satellite_steps": int(
                full_pool["active_satellite_steps"]
            )
            - int(drop_pool["active_satellite_steps"]),
        },
        "by_world": by_world,
        "mechanics_passed": mechanics,
        "method_passed": method,
        "candidate_specific_identity_passed": identity,
        "c3_legal_spread_count": spread,
        "supported_positive_target_count": supported_positive,
        "action_exposure": exposure,
        "changed_actions_compatible": changed_compatible,
        "joint_support_passed": joint_support,
        "pooled_service_noninferior": pooled_service,
        "pooled_active_beam_steps_not_above": pooled_beams,
        "pooled_active_satellite_steps_not_above": pooled_satellites,
        "hard_stops": hard_stops,
    }


def ordered_decision(*, passed_zr: bool, passed_hr: bool) -> str:
    """Apply the frozen order without comparing observed magnitudes."""

    if passed_zr:
        return "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"
    if passed_hr:
        return "GO_HR_C3_LEARNABILITY_PREREG_ONLY"
    return "STOP_C3_ORACLE_REDESIGN_REVIEW_SEAM"


def _assert_current_authority(
    payload: Mapping[str, Any], expected: Mapping[str, Any]
) -> None:
    """Reject mutually consistent shards that are stale against current files."""

    for field, value in expected.items():
        if payload.get(field) != value:
            raise V012OracleError(
                f"shard authority {field} does not match the current file state"
            )


def merge_shards(
    shard_files: Sequence[Path],
    output_dir: Path,
    *,
    tle_root: Path = screen.DEFAULT_TLE_ROOT,
    prereg_path: Path = screen.DEFAULT_PREREG,
    v03_root: Path = screen.DEFAULT_V03_ROOT,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V012OracleError(f"refusing to overwrite {output}")
    assert_contract_frozen()
    expected_contract = contract_receipt()
    expected_runtime_hashes = {
        str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
    }
    record = read_prereg(prereg_path)
    ephemeris = record.sections.get("ephemeris", {})
    if not isinstance(ephemeris, Mapping) or not isinstance(
        ephemeris.get("file_set_sha256"), str
    ):
        raise V012OracleError("current prereg omits the TLE file-set digest")
    expected_source_authority = {
        "prereg_file_sha256": file_sha256(Path(prereg_path)),
        "prereg_record_digest": str(record.digest),
        "tle_file_set_sha256": str(ephemeris["file_set_sha256"]),
        **python_source_authority(),
    }
    # Re-authenticate the current TLE source rather than trusting mutually
    # agreeing shard receipts from an older or foreign filesystem state.
    with tempfile.TemporaryDirectory(prefix="mcrl-v012-merge-tle-") as temporary:
        screen._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
    payloads = [
        json.loads(Path(path).read_text(encoding="utf-8")) for path in shard_files
    ]
    expected_count = len(WORLD_SEEDS) * len(ARMS) * len(LINEAGES)
    if len(payloads) != expected_count:
        raise V012OracleError(f"merge needs exactly {expected_count} shard files")
    expected_pairs = {
        (world, arm, lineage)
        for world in WORLD_SEEDS
        for arm in ARMS
        for lineage in LINEAGES
    }
    observed_pairs: set[tuple[int, str, int]] = set()
    first = payloads[0]
    expected_authority = {
        "contract": expected_contract,
        "contract_sha256": canonical_sha256(expected_contract),
        "contract_file_sha256": file_sha256(CONTRACT_PATH),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": expected_runtime_hashes,
        "source_authority": expected_source_authority,
    }
    _assert_current_authority(first, expected_authority)
    for payload in payloads:
        if payload.get("schema") != SHARD_SCHEMA:
            raise V012OracleError("shard schema drifted")
        row = payload.get("row")
        if not isinstance(row, Mapping) or canonical_sha256(row) != payload.get(
            "row_sha256"
        ):
            raise V012OracleError("shard row digest failed")
        if any(
            payload.get(field) != first.get(field)
            for field in (
                "contract",
                "contract_sha256",
                "contract_file_sha256",
                "runner_file_sha256",
                "runtime_file_sha256",
                "source_authority",
            )
        ):
            raise V012OracleError("shard authority hashes disagree")
        observed_pairs.add(
            (
                int(row["world_seed"]),
                str(row["arm"]),
                int(row["initialization_seed"]),
            )
        )
    if observed_pairs != expected_pairs:
        raise V012OracleError("shard world/arm/lineage coverage is not exact")

    rows = [payload["row"] for payload in payloads]
    for lineage in LINEAGES:
        current_q1, current_receipt = load_frozen_q1(v03_root, lineage)
        current_parameter_sha = _q1_parameter_sha256(current_q1)
        lineage_rows = [
            row for row in rows if int(row["initialization_seed"]) == lineage
        ]
        if not lineage_rows or any(
            str(row["q1_parameter_sha256_before"]) != current_parameter_sha
            or str(row["q1_parameter_sha256_after"]) != current_parameter_sha
            or row["q1_checkpoint"] != current_receipt
            for row in lineage_rows
        ):
            raise V012OracleError(
                f"lineage {lineage} Q1 receipt does not match the current checkpoint"
            )
    for world in WORLD_SEEDS:
        world_rows = [row for row in rows if int(row["world_seed"]) == world]
        if {str(row["field_root_digest"]) for row in world_rows} != {
            field_for_world(world).root_digest
        }:
            raise V012OracleError("world shards do not share their frozen field")
        if len({str(row["initial_world_sha256"]) for row in world_rows}) != 1:
            raise V012OracleError("world shards do not share one initial world")
    if field_for_world(WORLD_SEEDS[0]).root_digest == field_for_world(
        WORLD_SEEDS[1]
    ).root_digest:
        raise V012OracleError("two frozen worlds unexpectedly share one field")

    by_arm = {arm: [row for row in rows if str(row["arm"]) == arm] for arm in ARMS}
    pooled_by_arm = {arm: _pool(by_arm[arm]) for arm in ARMS}
    pooled_by_world_and_arm = {
        str(world): {
            arm: _pool(
                [
                    row
                    for row in rows
                    if int(row["world_seed"]) == world and str(row["arm"]) == arm
                ]
            )
            for arm in ARMS
        }
        for world in WORLD_SEEDS
    }
    gates = {
        "ZR": _pair_gate(
            label="ZR",
            full_arm="FULL_ZR",
            rows=rows,
            pooled_by_arm=pooled_by_arm,
            pooled_by_world_and_arm=pooled_by_world_and_arm,
        ),
        "HR": _pair_gate(
            label="HR",
            full_arm="FULL_HR",
            rows=rows,
            pooled_by_arm=pooled_by_arm,
            pooled_by_world_and_arm=pooled_by_world_and_arm,
        ),
    }
    passed_zr = bool(gates["ZR"]["passed"])
    passed_hr = bool(gates["HR"]["passed"])
    decision = ordered_decision(passed_zr=passed_zr, passed_hr=passed_hr)
    initial_worlds = {
        str(world): next(
            str(row["initial_world_sha256"])
            for row in rows
            if int(row["world_seed"]) == world
        )
        for world in WORLD_SEEDS
    }
    result = {
        "schema": RESULT_SCHEMA,
        "claim_ceiling": "TWO_TRAIN_WORLD_ORDERED_ORACLE_NO_LEARNER_NO_TEST",
        "contract": first["contract"],
        "contract_sha256": first["contract_sha256"],
        "contract_file_sha256": first["contract_file_sha256"],
        "runner_file_sha256": first["runner_file_sha256"],
        "runtime_file_sha256": first["runtime_file_sha256"],
        "source_authority": first["source_authority"],
        "field_root_digest_by_world": {
            str(world): field_for_world(world).root_digest for world in WORLD_SEEDS
        },
        "initial_world_sha256": initial_worlds,
        "rows": sorted(
            rows,
            key=lambda row: (
                WORLD_SEEDS.index(int(row["world_seed"])),
                ARMS.index(str(row["arm"])),
                LINEAGES.index(int(row["initialization_seed"])),
            ),
        ),
        "summaries": {
            "pooled_by_arm": pooled_by_arm,
            "pooled_by_world_and_arm": pooled_by_world_and_arm,
            "candidate_gates": gates,
        },
        "gate": {
            "decision": decision,
            "pass_zr": passed_zr,
            "pass_hr": passed_hr,
            "ordered_selection_zr_before_hr": True,
        },
    }
    result["result_sha256"] = canonical_sha256(result)
    output.mkdir(parents=True, exist_ok=False)
    (output / "result.json").write_bytes(_canonical_bytes(result))
    print(
        f"decision={decision} "
        f"ZR={gates['ZR']['pooled']['relative_delta_ee']:+.6%} "
        f"HR={gates['HR']['pooled']['relative_delta_ee']:+.6%}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--json", action="store_true")
    shard = sub.add_parser("shard")
    shard.add_argument("--world", type=int, choices=WORLD_SEEDS, required=True)
    shard.add_argument("--arm", choices=ARMS, required=True)
    shard.add_argument("--lineage", type=int, choices=LINEAGES, required=True)
    shard.add_argument("--output", type=Path, required=True)
    shard.add_argument("--tle-root", type=Path, default=screen.DEFAULT_TLE_ROOT)
    shard.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    shard.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    merge = sub.add_parser("merge")
    merge.add_argument("--shards", type=Path, nargs="+", required=True)
    merge.add_argument("--output", type=Path, required=True)
    merge.add_argument("--tle-root", type=Path, default=screen.DEFAULT_TLE_ROOT)
    merge.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    merge.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    args = parser.parse_args()
    if args.command == "plan":
        payload = contract_receipt()
        print(
            json.dumps(payload, indent=2, sort_keys=True)
            if args.json
            else canonical_sha256(payload)
        )
    elif args.command == "shard":
        run_shard(
            world_seed=args.world,
            arm=args.arm,
            lineage=args.lineage,
            output_dir=args.output,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
        )
    else:
        merge_shards(
            args.shards,
            args.output,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
        )


if __name__ == "__main__":
    main()
