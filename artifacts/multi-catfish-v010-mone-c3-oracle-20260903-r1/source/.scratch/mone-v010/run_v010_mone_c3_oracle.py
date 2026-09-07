#!/usr/bin/env python3
"""V0.10 two-arm exact matched-opening (MONE) C3 oracle gate.

This executable opens only the preregistered TRAIN world.  It performs no
learner update and exposes no TEST path.  The binding comparison is
``FULL = Q1 + O2 + O3`` against ``DROP_C3 = Q1 + O2``.  O3 is evaluated once
per state around the C3-free ``Q1 + O2`` joint action and is never recentered
for an ablation arm.
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
SCRATCH = REPO / ".scratch" / "c3-v04"
for _path in (SCRATCH, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_v04_c3_500_update_screen as screen  # noqa: E402
import run_v04_c3_learnability_gate as old_gate  # noqa: E402
from mcrl.algorithms.ee_axis_v04_hybrid import (  # noqa: E402
    extract_frozen_meanmax_head,
)
from mcrl.env.action_contract import Association, NUM_ACTIONS  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_matched_opening import (  # noqa: E402
    MATCHED_OPENING_SCHEMA,
    build_matched_opening_surfaces,
)
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
from mcrl.runtime.prereg import read_prereg  # noqa: E402


RESULT_SCHEMA = "multi-catfish-mcrl-v010-mone-c3-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v010-mone-c3-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v010-mone-c3-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v010-mone-c3-oracle-contract-v1"

WORLD_SEED = 2026104601
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = ("FULL", "DROP_C3")
USERS = 100
STEPS_PER_EPISODE = 10
FIELD_COMPONENT = "MCRL_V010_MONE_C3_ORACLE_V1"
FIELD_EXCLUDES = ("arm", "initialization_seed", "policy_label")
CONTRACT_PATH = (
    REPO
    / "docs"
    / "MULTI-CATFISH-MCRL-V010-MONE-C3-ORACLE-PREREG-2026-09-03.md"
)
RUNTIME_PATHS = (
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_matched_opening.py",
)


class V010OracleError(RuntimeError):
    """A V0.10 input, receipt, mechanic, or gate condition failed closed."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V010OracleError("payload is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V010OracleError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(*values: object) -> str:
    digest = hashlib.sha256()
    for value in values:
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(repr(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def field_for_world() -> KeyedFadingField:
    return KeyedFadingField.from_components(FIELD_COMPONENT, WORLD_SEED)


def contract_receipt() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "world_seed": WORLD_SEED,
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "arm_heads": {
            "FULL": ["Q1", "O2_OPS3", "O3_MONE"],
            "DROP_C3": ["Q1", "O2_OPS3"],
        },
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(ARMS) * len(LINEAGES),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "background": "MASKED_ARGMAX_Q1_PLUS_O2",
        "background_shared_at_anchor": True,
        "q3_recentered_by_arm": False,
        "summation": "left_to_right_unweighted",
        "selection": "one_common_mask_one_argmax_one_action",
        "field_components": [FIELD_COMPONENT, WORLD_SEED],
        "field_excludes": list(FIELD_EXCLUDES),
        "matched_opening_schema": MATCHED_OPENING_SCHEMA,
        "ops3_live_schema": OPS3_LIVE_SCHEMA,
        "lambda_bits_per_j_hex": OPS3_LAMBDA_BITS_PER_J.hex(),
        "kappa_bits_hex": OPS3_KAPPA_BITS.hex(),
        "gate": {
            "pooled_full_strictly_above_drop_c3": True,
            "positive_lineages_minimum": 2,
            "pooled_service_noninferior": True,
            "service_noninferior_lineages_minimum": 2,
            "one_user_step_shortfall_fails": True,
            "nonzero_c3_spread": True,
            "nonzero_action_exposure": True,
            "joint_reversal_strict_majority_hard_stop": True,
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
        raise V010OracleError("lineage is outside the frozen V0.10 set")
    config, _ = old_gate._config_pair()
    spec = old_gate._spec_for_seed(Path(v03_root), int(lineage))
    network, receipt = extract_frozen_meanmax_head(
        spec, config, head_index=0, device="cpu"
    )
    network.eval()
    network.requires_grad_(False)
    if any(parameter.requires_grad for parameter in network.parameters()):
        raise V010OracleError("frozen Q1 still has trainable parameters")
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
        raise V010OracleError("Q1 surface is malformed")
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
        raise V010OracleError(
            f"mask must be a Boolean matrix with {NUM_ACTIONS} native actions"
        )
    if any(value.shape != legal.shape or not np.all(np.isfinite(value)) for value in arrays):
        raise V010OracleError("head surfaces are nonfinite or misaligned")
    if not np.all(np.any(legal, axis=1)):
        raise V010OracleError("each user must have a legal native action")
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
    ):
        digest.update(name.encode("ascii"))
        if isinstance(value, np.ndarray):
            digest.update(array_sha256(value).encode("ascii"))
        else:
            digest.update(repr(value).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._previous_association)).encode("utf-8"))
    digest.update(repr(copy.deepcopy(step_env._segments)).encode("utf-8"))
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
                np.stack([table.norad_ids for table in observation.candidates.slot_tables])
            ),
            "cells": array_sha256(
                np.stack([table.cell_ids for table in observation.candidates.slot_tables])
            ),
        }
    )


def _rankdata(values: np.ndarray) -> np.ndarray:
    data = np.asarray(values, dtype=np.float64)
    order = np.argsort(data, kind="mergesort")
    ranks = np.empty(data.size, dtype=np.float64)
    start = 0
    while start < data.size:
        end = start + 1
        while end < data.size and data[order[end]] == data[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1)
        start = end
    return ranks


def _spearman(left: np.ndarray, right: np.ndarray) -> float | None:
    if left.size < 2 or right.size != left.size:
        return None
    x = _rankdata(left)
    y = _rankdata(right)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _q1_o1_diagnostic(
    q1: np.ndarray, o1: np.ndarray, mask: np.ndarray
) -> dict[str, Any]:
    compared = 0
    agreed = 0
    rhos: list[float] = []
    top_equal = 0
    top_total = 0
    regrets: list[float] = []
    for uid in range(mask.shape[0]):
        legal = np.flatnonzero(mask[uid])
        if legal.size < 2:
            continue
        q = q1[uid, legal]
        oracle = o1[uid, legal]
        rho = _spearman(q, oracle)
        if rho is not None:
            rhos.append(rho)
        q_top = int(legal[int(np.argmax(q))])
        o_top = int(legal[int(np.argmax(oracle))])
        top_total += 1
        top_equal += int(q_top == o_top)
        regrets.append(float(np.max(oracle) - o1[uid, q_top]))
        for left in range(legal.size):
            for right in range(left + 1, legal.size):
                q_delta = float(q[left] - q[right])
                o_delta = float(oracle[left] - oracle[right])
                if q_delta == 0.0 or o_delta == 0.0:
                    continue
                compared += 1
                agreed += int((q_delta > 0.0) == (o_delta > 0.0))
    return {
        "pairwise_compared": compared,
        "pairwise_agreed": agreed,
        "pairwise_agreement": agreed / compared if compared else None,
        "spearman_count": len(rhos),
        "spearman_sum": float(math.fsum(rhos)),
        "mean_spearman": float(np.mean(rhos)) if rhos else None,
        "top_count": top_total,
        "top_agreed": top_equal,
        "top_agreement": top_equal / top_total if top_total else None,
        "oracle_regret_count": len(regrets),
        "oracle_regret_sum": float(math.fsum(regrets)),
        "mean_oracle_regret": float(np.mean(regrets)) if regrets else None,
    }


def _joint_diagnostic(
    step_env: Any,
    rng: np.random.Generator,
    background: np.ndarray,
    full: np.ndarray,
    matched: Any,
    interval_s: float,
) -> dict[str, Any]:
    changed = np.flatnonzero(background != full)
    if changed.size == 0:
        return {"status": "NO_EXPOSURE", "changed_users": 0}
    before = _live_digest(step_env, rng)
    reference = step_env.evaluate_actions(background, rng)
    candidate = step_env.evaluate_actions(full, rng)
    after = _live_digest(step_env, rng)
    if before != after:
        raise V010OracleError("joint diagnostic mutated environment or RNG")
    rate_delta = np.asarray(candidate.link_rate_bps) - np.asarray(reference.link_rate_bps)
    actual = float(interval_s) * math.fsum(float(value) for value in rate_delta)
    actual -= OPS3_LAMBDA_BITS_PER_J * float(interval_s) * (
        float(candidate.system_power_w) - float(reference.system_power_w)
    )
    additive = math.fsum(
        float(matched.system_surplus_bits[uid, int(full[uid])])
        for uid in changed.tolist()
    )
    reversal = bool(
        actual != 0.0
        and additive != 0.0
        and ((actual > 0.0) != (additive > 0.0))
    )
    return {
        "status": "OBSERVED",
        "changed_users": int(changed.size),
        "actual_joint_surplus_bits": actual,
        "sum_unilateral_surplus_bits": float(additive),
        "interaction_residual_bits": float(actual - additive),
        "direction_reversal": reversal,
    }


def _hold_rate(step_env: Any, observation: Any, actions: np.ndarray) -> float | None:
    held = 0
    eligible = 0
    previous = tuple(step_env._previous_association)
    for uid, action in enumerate(actions.tolist()):
        if previous[uid] is None:
            continue
        association = observation.candidates.slot_tables[uid].association(int(action))
        if not isinstance(association, Association):
            continue
        eligible += 1
        held += int(previous[uid] == association)
    return held / eligible if eligible else None


def evaluate_episode(
    *,
    q1: Any,
    q1_receipt: Mapping[str, Any],
    archive: Any,
    field: KeyedFadingField,
    lineage: int,
    arm: str,
) -> dict[str, Any]:
    if arm not in ARMS or int(lineage) not in LINEAGES:
        raise V010OracleError("episode arm/lineage is outside the frozen panel")
    if field.root_digest != field_for_world().root_digest:
        raise V010OracleError("episode does not use the frozen common field")
    environment = screen._make_environment(archive, users=USERS)
    environment.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = screen._evaluation_rngs(
        WORLD_SEED
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
    c3_spread = 0
    action_flips = 0
    diagnostics: list[dict[str, Any]] = []
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
            background = select_actions(
                q1_values, o2, zero, mask, include_c3=False
            )
            matched = build_matched_opening_surfaces(
                step_env,
                observation=observation,
                reference_joint_actions=background,
                rng=env_rng,
                lambda_bits_per_j=OPS3_LAMBDA_BITS_PER_J,
                interval_s=interval_s,
                kappa_bits=OPS3_KAPPA_BITS,
            )
            o3 = np.asarray(matched.q3_values, dtype=np.float64)
            full_actions = select_actions(
                q1_values, o2, o3, mask, include_c3=True
            )
            after = _live_digest(environment, env_rng)

            reference_zero = all(
                float(o2[uid, int(q1_reference[uid])]) == 0.0
                and float(o3[uid, int(background[uid])]) == 0.0
                for uid in range(USERS)
            )
            base_evaluation = step_env.evaluate_actions(background, env_rng)
            opening_equal = all(
                bool(ops3[uid].opening_service_feasible[int(background[uid])])
                == bool(base_evaluation.resolution.served[uid])
                for uid in range(USERS)
            )
            mechanics = {
                "live_state_unchanged": before == after,
                "common_mask": np.array_equal(matched.legal_mask, mask)
                and all(np.array_equal(surface.legal_mask, mask[uid]) for uid, surface in enumerate(ops3)),
                "reference_rows_exact_zero": reference_zero,
                "opening_service_gate_equal": opening_equal,
                "identity_max_abs_bits": float(
                    np.max(np.abs(matched.identity_residual_bits))
                ),
                "background_sha256": array_sha256(background),
            }
            mechanics["passed"] = bool(
                mechanics["live_state_unchanged"]
                and mechanics["common_mask"]
                and mechanics["reference_rows_exact_zero"]
                and mechanics["opening_service_gate_equal"]
            )
            if not mechanics["passed"]:
                raise V010OracleError("binding per-step mechanics failed")

            selected = full_actions if arm == "FULL" else background
            flips = int(np.count_nonzero(full_actions != background))
            action_flips += flips
            c3_spread += sum(
                int(np.ptp(o3[uid, np.flatnonzero(mask[uid])]) > 0.0)
                for uid in range(USERS)
            )
            diagnostic = {
                "step_index": step_index,
                "q1_vs_oracle_o1": _q1_o1_diagnostic(
                    q1_values, matched.q1_values, mask
                ),
                "joint_interaction": _joint_diagnostic(
                    step_env,
                    env_rng,
                    background,
                    full_actions,
                    matched,
                    interval_s,
                ),
            }
            diagnostics.append(diagnostic)
            hold_rate = _hold_rate(step_env, observation, selected)
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
                raise V010OracleError("canonical EE inputs are malformed")
            bits = interval_s * math.fsum(float(value) for value in rates)
            energy = interval_s * power
            total_bits += bits
            total_energy += energy
            served_steps += int(outcome.resolution.served_count)
            per_step.append(
                {
                    "step_index": step_index,
                    "total_bits": float(bits),
                    "total_energy_j": float(energy),
                    "served_user_steps": int(outcome.resolution.served_count),
                    "hold_rate": hold_rate,
                    "active_beam_count": int(np.asarray(outcome.radiating.norad_ids).size),
                    "full_vs_drop_c3_action_flips": flips,
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
                }
            )
            if result.done:
                if step_index != STEPS_PER_EPISODE - 1:
                    raise V010OracleError("episode terminated before ten steps")
                break
            observation = outcome.observation

    q1_after = _q1_parameter_sha256(q1)
    if q1_before != q1_after:
        raise V010OracleError("frozen Q1 changed during oracle episode")
    return {
        "schema": EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": int(lineage),
        "world_seed": WORLD_SEED,
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
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
        "c3_legal_spread_count": c3_spread,
        "full_vs_drop_c3_action_flips": action_flips,
        "mechanics_passed": all(step["mechanics"]["passed"] for step in per_step),
        "diagnostics": diagnostics,
        "per_step": per_step,
        "elapsed_s": time.perf_counter() - started,
    }


def run_shard(
    *,
    arm: str,
    lineage: int,
    output_dir: Path,
    tle_root: Path,
    prereg_path: Path,
    v03_root: Path,
) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V010OracleError(f"refusing to overwrite {output}")
    record = read_prereg(prereg_path)
    q1, q1_receipt = load_frozen_q1(v03_root, lineage)
    field = field_for_world()
    with tempfile.TemporaryDirectory(prefix="mcrl-v010-mone-tle-") as temporary:
        archive = screen._frozen_archive(
            record, Path(tle_root), Path(temporary) / "frozen-tle"
        )
        row = evaluate_episode(
            q1=q1,
            q1_receipt=q1_receipt,
            archive=archive,
            field=field,
            lineage=int(lineage),
            arm=arm,
        )
    contract = contract_receipt()
    payload = {
        "schema": SHARD_SCHEMA,
        "shard_id": f"{arm}-{int(lineage)}",
        "contract": contract,
        "contract_sha256": canonical_sha256(contract),
        "contract_file_sha256": file_sha256(CONTRACT_PATH),
        "runner_file_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_file_sha256": {
            str(path.relative_to(REPO)): file_sha256(path) for path in RUNTIME_PATHS
        },
        "row": row,
    }
    payload["row_sha256"] = canonical_sha256(row)
    output.mkdir(parents=True, exist_ok=False)
    (output / "shard.json").write_bytes(_canonical_bytes(payload))
    print(
        f"{arm}/{lineage}: EE={row['ratio_of_sums_ee_bits_per_j']:.9g} "
        f"elapsed={row['elapsed_s']:.1f}s"
    )
    return payload


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
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
    }


def merge_shards(shard_files: Sequence[Path], output_dir: Path) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V010OracleError(f"refusing to overwrite {output}")
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in shard_files]
    if len(payloads) != len(ARMS) * len(LINEAGES):
        raise V010OracleError("merge needs exactly six shard files")
    expected_pairs = {(arm, lineage) for arm in ARMS for lineage in LINEAGES}
    observed_pairs: set[tuple[str, int]] = set()
    first = payloads[0]
    for payload in payloads:
        if payload.get("schema") != SHARD_SCHEMA:
            raise V010OracleError("shard schema drifted")
        row = payload.get("row")
        if not isinstance(row, Mapping) or canonical_sha256(row) != payload.get("row_sha256"):
            raise V010OracleError("shard row digest failed")
        if any(
            payload.get(field) != first.get(field)
            for field in (
                "contract",
                "contract_sha256",
                "contract_file_sha256",
                "runner_file_sha256",
                "runtime_file_sha256",
            )
        ):
            raise V010OracleError("shard authority hashes disagree")
        observed_pairs.add((str(row["arm"]), int(row["initialization_seed"])))
    if observed_pairs != expected_pairs:
        raise V010OracleError("shard arm/lineage coverage is not exact")
    rows = [payload["row"] for payload in payloads]
    if {str(row["field_root_digest"]) for row in rows} != {field_for_world().root_digest}:
        raise V010OracleError("shards do not share the frozen field")
    if len({str(row["initial_world_sha256"]) for row in rows}) != 1:
        raise V010OracleError("shards do not share one initial world")

    by_arm = {
        arm: [row for row in rows if row["arm"] == arm]
        for arm in ARMS
    }
    pooled = {arm: _pool(by_arm[arm]) for arm in ARMS}
    full_ee = float(pooled["FULL"]["ratio_of_sums_ee_bits_per_j"])
    drop_ee = float(pooled["DROP_C3"]["ratio_of_sums_ee_bits_per_j"])
    lineage_rows = {
        (str(row["arm"]), int(row["initialization_seed"])): row for row in rows
    }
    lineage_contrasts: dict[str, Any] = {}
    positive = 0
    service_noninferior = 0
    for lineage in LINEAGES:
        full = lineage_rows[("FULL", lineage)]
        drop = lineage_rows[("DROP_C3", lineage)]
        delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(
            drop["ratio_of_sums_ee_bits_per_j"]
        )
        service_delta = int(full["served_user_steps"]) - int(drop["served_user_steps"])
        positive += int(delta > 0.0)
        service_noninferior += int(service_delta >= 0)
        lineage_contrasts[str(lineage)] = {
            "delta_ee_bits_per_j": delta,
            "relative_delta_ee": delta
            / float(drop["ratio_of_sums_ee_bits_per_j"]),
            "delta_served_user_steps": service_delta,
        }

    joint = [
        diagnostic["joint_interaction"]
        for row in rows
        for diagnostic in row["diagnostics"]
        if diagnostic["joint_interaction"]["status"] == "OBSERVED"
    ]
    reversals = sum(int(bool(value["direction_reversal"])) for value in joint)
    reversal_fraction = reversals / len(joint) if joint else None
    spread = sum(int(row["c3_legal_spread_count"]) for row in rows)
    exposure = sum(int(row["full_vs_drop_c3_action_flips"]) for row in rows)
    mechanics = all(bool(row["mechanics_passed"]) for row in rows)
    pooled_service = int(pooled["FULL"]["served_user_steps"]) >= int(
        pooled["DROP_C3"]["served_user_steps"]
    )
    hard_stops: list[str] = []
    if not mechanics:
        hard_stops.append("binding mechanics failed")
    if spread <= 0:
        hard_stops.append("MONE has zero legal-action spread")
    if exposure <= 0:
        hard_stops.append("FULL and DROP_C3 have no action exposure")
    if not full_ee > drop_ee:
        hard_stops.append("pooled FULL EE is not strictly above DROP_C3")
    if positive < 2:
        hard_stops.append("fewer than two of three lineages have positive C3 margin")
    if not pooled_service:
        hard_stops.append("pooled service guard failed")
    if service_noninferior < 2:
        hard_stops.append("fewer than two service-noninferior lineage contrasts")
    if not joint:
        hard_stops.append("joint interaction diagnostic has no exposure")
    elif reversal_fraction is not None and reversal_fraction > 0.5:
        hard_stops.append("joint direction reversal is a strict majority")

    result = {
        "schema": RESULT_SCHEMA,
        "claim_ceiling": "ONE_TRAIN_WORLD_ORACLE_DIRECTION_ONLY_NO_LEARNER_NO_TEST",
        "contract": first["contract"],
        "contract_sha256": first["contract_sha256"],
        "contract_file_sha256": first["contract_file_sha256"],
        "runner_file_sha256": first["runner_file_sha256"],
        "runtime_file_sha256": first["runtime_file_sha256"],
        "field_root_digest": field_for_world().root_digest,
        "initial_world_sha256": rows[0]["initial_world_sha256"],
        "rows": sorted(
            rows,
            key=lambda row: (
                ARMS.index(str(row["arm"])),
                LINEAGES.index(int(row["initialization_seed"])),
            ),
        ),
        "summaries": {
            "pooled_by_arm": pooled,
            "c3_pooled": {
                "delta_ee_bits_per_j": full_ee - drop_ee,
                "relative_delta_ee": (full_ee - drop_ee) / drop_ee,
                "delta_served_user_steps": int(pooled["FULL"]["served_user_steps"])
                - int(pooled["DROP_C3"]["served_user_steps"]),
            },
            "c3_by_lineage": lineage_contrasts,
        },
        "gate": {
            "decision": "GO_MONE_C3_LEARNER" if not hard_stops else "FAIL_MONE_C3_ORACLE",
            "positive_lineages": positive,
            "service_noninferior_lineages": service_noninferior,
            "pooled_service_noninferior": pooled_service,
            "c3_legal_spread_count": spread,
            "full_vs_drop_c3_action_flips": exposure,
            "joint_interaction_samples": len(joint),
            "joint_direction_reversals": reversals,
            "joint_direction_reversal_fraction": reversal_fraction,
            "mechanics_passed": mechanics,
            "hard_stops": hard_stops,
        },
    }
    result["result_sha256"] = canonical_sha256(result)
    output.mkdir(parents=True, exist_ok=False)
    (output / "result.json").write_bytes(_canonical_bytes(result))
    print(
        f"decision={result['gate']['decision']} "
        f"relative_C3={result['summaries']['c3_pooled']['relative_delta_ee']:+.6%}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--json", action="store_true")
    shard = sub.add_parser("shard")
    shard.add_argument("--arm", choices=ARMS, required=True)
    shard.add_argument("--lineage", type=int, choices=LINEAGES, required=True)
    shard.add_argument("--output", type=Path, required=True)
    shard.add_argument("--tle-root", type=Path, default=screen.DEFAULT_TLE_ROOT)
    shard.add_argument("--prereg", type=Path, default=screen.DEFAULT_PREREG)
    shard.add_argument("--v03-root", type=Path, default=screen.DEFAULT_V03_ROOT)
    merge = sub.add_parser("merge")
    merge.add_argument("--shards", type=Path, nargs="+", required=True)
    merge.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        payload = contract_receipt()
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else canonical_sha256(payload))
    elif args.command == "shard":
        run_shard(
            arm=args.arm,
            lineage=args.lineage,
            output_dir=args.output,
            tle_root=args.tle_root,
            prereg_path=args.prereg,
            v03_root=args.v03_root,
        )
    else:
        merge_shards(args.shards, args.output)


if __name__ == "__main__":
    main()
