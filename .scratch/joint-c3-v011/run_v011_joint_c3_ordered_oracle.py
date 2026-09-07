#!/usr/bin/env python3
"""V0.11 ordered joint-C3 oracle gate.

This executable opens only the preregistered TRAIN world.  It performs no
learner update and exposes no TEST path.  One shared Q1+O2 comparator is
tested against two preordered C3 teachers: self-consistent M1-D and
antithetic-permutation MONE.  Exact-O1 arms are diagnostic only.
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
from mcrl.env.action_contract import (  # noqa: E402
    Association,
    NO_OP_ACTION,
    NUM_ACTIONS,
)
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_matched_opening import MATCHED_OPENING_SCHEMA  # noqa: E402
from mcrl.runtime.ee_axis_joint_c3 import (  # noqa: E402
    JOINT_C3_SCHEMA,
    build_ap_mone_surface,
    solve_exact_o1_joint_c3,
    solve_m1d_joint_c3,
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


RESULT_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-result-v1"
EPISODE_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-episode-v1"
SHARD_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-shard-v1"
CONTRACT_SCHEMA = "multi-catfish-mcrl-v011-joint-c3-ordered-oracle-contract-v1"

WORLD_SEED = 2026104701
LINEAGES = (2026092101, 2026092102, 2026092103)
ARMS = (
    "DROP_C3",
    "FULL_M1D",
    "FULL_AP",
    "DIAG_O_DROP",
    "DIAG_O_FULL",
)
USERS = 100
STEPS_PER_EPISODE = 10
MAX_SWEEPS = 5
FIELD_COMPONENT = "MCRL_V011_JOINT_C3_ORDERED_ORACLE_V1"
FIELD_EXCLUDES = ("arm", "initialization_seed", "policy_label")
CONTRACT_PATH = (
    REPO
    / "docs"
    / "MULTI-CATFISH-MCRL-V011-JOINT-C3-ORDERED-ORACLE-PREREG-2026-09-03.md"
)
RUNTIME_PATHS = (
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_ops3_live.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_matched_opening.py",
    REPO / "src" / "mcrl" / "runtime" / "ee_axis_joint_c3.py",
)


class V011OracleError(RuntimeError):
    """A V0.11 input, receipt, mechanic, or gate condition failed closed."""


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
        raise V011OracleError("payload is not finite canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V011OracleError(f"expected a regular file: {source}")
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


def permutation_for_step(step_index: int) -> np.ndarray:
    """Return the frozen hash-ranked AP order, independent of arm/lineage."""

    if type(step_index) is not int or not 0 <= step_index < STEPS_PER_EPISODE:
        raise V011OracleError("step_index is outside the frozen episode")
    keyed: list[tuple[bytes, int]] = []
    for uid in range(USERS):
        payload = (
            f"{FIELD_COMPONENT}|{WORLD_SEED}|AP_PERMUTATION|{step_index}|{uid}"
        ).encode("ascii")
        keyed.append((hashlib.sha256(payload).digest(), uid))
    return np.asarray([uid for _digest, uid in sorted(keyed)], dtype=np.int64)


def contract_receipt() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "world_seed": WORLD_SEED,
        "lineages": list(LINEAGES),
        "arms": list(ARMS),
        "arm_heads": {
            "DROP_C3": ["Q1", "O2_OPS3"],
            "FULL_M1D": ["Q1", "O2_OPS3", "O3_M1D"],
            "FULL_AP": ["Q1", "O2_OPS3", "O3_AP_MONE"],
            "DIAG_O_DROP": ["O1_EXACT", "O2_OPS3"],
            "DIAG_O_FULL": ["O1_EXACT", "O2_OPS3", "O3_EXACT"],
        },
        "users": USERS,
        "steps_per_episode": STEPS_PER_EPISODE,
        "episodes": len(ARMS) * len(LINEAGES),
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "background": "MASKED_ARGMAX_Q1_PLUS_O2",
        "candidate_order": ["AP_MONE", "M1D"],
        "max_complete_gauss_seidel_sweeps": MAX_SWEEPS,
        "gauss_seidel_user_order": list(range(USERS)),
        "ap_permutations": "ONE_KEYED_ORDER_AND_EXACT_REVERSE",
        "summation": "left_to_right_unweighted",
        "selection": "one_common_mask_one_argmax_one_action",
        "field_components": [FIELD_COMPONENT, WORLD_SEED],
        "field_excludes": list(FIELD_EXCLUDES),
        "matched_opening_schema": MATCHED_OPENING_SCHEMA,
        "joint_c3_schema": JOINT_C3_SCHEMA,
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
            "m1d_every_anchor_fixed_point": True,
            "m1d_final_one_pass_exact": True,
            "exact_o_diagnostic_nonbinding": True,
        },
        "selection_table": {
            "A_and_M_or_O": "GO_AP_MONE_LEARNABILITY_PREREG_ONLY",
            "not_A_and_M": "GO_M1D_LEARNABILITY_PREREG_ONLY",
            "A_only": "INCONSISTENT_AP_ONLY_NO_LEARNER_REVIEW",
            "O_only": "C1_ALIGNMENT_BLOCKS_C3_NO_LEARNER",
            "none": "JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED",
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
        raise V011OracleError("lineage is outside the frozen V0.11 set")
    config, _ = old_gate._config_pair()
    spec = old_gate._spec_for_seed(Path(v03_root), int(lineage))
    network, receipt = extract_frozen_meanmax_head(
        spec, config, head_index=0, device="cpu"
    )
    network.eval()
    network.requires_grad_(False)
    if any(parameter.requires_grad for parameter in network.parameters()):
        raise V011OracleError("frozen Q1 still has trainable parameters")
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
        raise V011OracleError("Q1 surface is malformed")
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
        raise V011OracleError(
            f"mask must be a Boolean matrix with {NUM_ACTIONS} native actions"
        )
    if any(value.shape != legal.shape or not np.all(np.isfinite(value)) for value in arrays):
        raise V011OracleError("head surfaces are nonfinite or misaligned")
    if not np.all(np.any(legal, axis=1)):
        raise V011OracleError("each user must have a legal native action")
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
        raise V011OracleError("joint diagnostic mutated environment or RNG")
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


def _joint_opening_change(
    step_env: Any,
    rng: np.random.Generator,
    reference: np.ndarray,
    candidate: np.ndarray,
    interval_s: float,
) -> dict[str, Any]:
    changed = int(np.count_nonzero(reference != candidate))
    if changed == 0:
        return {
            "status": "NO_EXPOSURE",
            "changed_users": 0,
            "delta_bits": 0.0,
            "delta_energy_j": 0.0,
            "fixed_lambda_surplus_bits": 0.0,
        }
    before = _live_digest(step_env, rng)
    baseline = step_env.evaluate_actions(reference, rng)
    treatment = step_env.evaluate_actions(candidate, rng)
    after = _live_digest(step_env, rng)
    if before != after:
        raise V011OracleError("joint opening diagnostic mutated environment or RNG")
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
        "fixed_lambda_surplus_bits": delta_bits
        - OPS3_LAMBDA_BITS_PER_J * delta_energy,
    }


def _spread_count(values: np.ndarray, mask: np.ndarray) -> int:
    return sum(
        int(np.ptp(values[uid, np.flatnonzero(mask[uid])]) > 0.0)
        for uid in range(mask.shape[0])
    )


def _ap_execution_receipt(
    surface: Any,
    background: np.ndarray,
    selected: np.ndarray,
    mask: np.ndarray,
    fixed_lambda_surplus_bits: float,
) -> dict[str, Any]:
    """Record AP distances and the credited sum for the executed profile.

    The telescoping identity is asserted by ``build_ap_mone_surface`` for
    the teacher proposal ``p``.  The binding one-pass action may differ from
    that proposal, so its realised joint surplus must be recorded separately
    from the antithetic per-user credited sum evaluated at the executed
    actions.  This is a diagnostic receipt; it does not turn the executed
    profile into a second identity claim.
    """

    proposal = np.asarray(surface.proposal_actions)
    reference = np.asarray(background)
    actions = np.asarray(selected)
    legal = np.asarray(mask)
    if (
        proposal.ndim != 1
        or reference.shape != proposal.shape
        or actions.shape != proposal.shape
        or legal.shape != (proposal.size, NUM_ACTIONS)
        or not np.issubdtype(proposal.dtype, np.integer)
        or not np.issubdtype(reference.dtype, np.integer)
        or not np.issubdtype(actions.dtype, np.integer)
        or legal.dtype != np.bool_
    ):
        raise V011OracleError("AP execution receipt has misaligned action surfaces")
    if not math.isfinite(float(fixed_lambda_surplus_bits)):
        raise V011OracleError("AP realised opening surplus is non-finite")
    z1 = np.asarray(surface.z1_bits, dtype=np.float64)
    z3 = np.asarray(surface.z3_bits, dtype=np.float64)
    if (
        z1.shape != (proposal.size, NUM_ACTIONS)
        or z3.shape != z1.shape
        or not np.all(np.isfinite(z1))
        or not np.all(np.isfinite(z3))
    ):
        raise V011OracleError("AP execution receipt has malformed credited surfaces")

    credited_terms: list[float] = []
    for uid, action_raw in enumerate(actions.tolist()):
        action = int(action_raw)
        if bool(np.any(legal[uid])):
            if not 0 <= action < NUM_ACTIONS or not bool(legal[uid, action]):
                raise V011OracleError("AP execution receipt contains an unsafe action")
            credited_terms.append(
                float(z1[uid, action]) + float(z3[uid, action])
            )
        elif action != NO_OP_ACTION:
            raise V011OracleError("AP execution receipt needs no-op for an empty row")

    credited = float(math.fsum(credited_terms))
    realised = float(fixed_lambda_surplus_bits)
    return {
        "proposal_flips_from_background": int(
            np.count_nonzero(proposal != reference)
        ),
        "executed_flips_from_background": int(
            np.count_nonzero(actions != reference)
        ),
        "executed_flips_from_proposal": int(
            np.count_nonzero(actions != proposal)
        ),
        "executed_antithetic_credited_sum_bits": credited,
        "executed_joint_surplus_bits": realised,
        "executed_joint_minus_credited_bits": realised - credited,
    }


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
        raise V011OracleError("episode arm/lineage is outside the frozen panel")
    if field.root_digest != field_for_world().root_digest:
        raise V011OracleError("episode does not use the frozen common field")
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
    action_exposure = 0
    joint_exposed = 0
    joint_negative = 0
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
            background = select_actions(
                q1_values, o2, zero, mask, include_c3=False
            )
            selected = np.array(background, copy=True)
            comparison = np.array(background, copy=True)
            o1 = np.zeros_like(q1_values)
            o3 = np.zeros_like(q1_values)
            step_method_passed = True
            method: dict[str, Any] = {"kind": arm, "status": "BASE"}

            if arm == "FULL_M1D":
                solved = solve_m1d_joint_c3(
                    step_env,
                    observation=observation,
                    initial_actions=background,
                    q1_values=q1_values,
                    o2_values=o2,
                    rng=env_rng,
                    lambda_bits_per_j=OPS3_LAMBDA_BITS_PER_J,
                    interval_s=interval_s,
                    kappa_bits=OPS3_KAPPA_BITS,
                    max_sweeps=MAX_SWEEPS,
                )
                step_method_passed = bool(solved.converged)
                method = {
                    "kind": "M1D",
                    "status": solved.status,
                    "sweep_count": int(solved.sweep_count),
                    "changed_per_sweep": [
                        int(value) for value in solved.changed_per_sweep.tolist()
                    ],
                    "final_iterate_sha256": array_sha256(
                        solved.final_iterate_actions
                    ),
                    "production_sha256": array_sha256(solved.production_actions),
                    "cycles_detected": solved.status == "FAIL_M1D_CYCLE",
                    "identity_passed": bool(solved.converged),
                }
                if solved.converged:
                    assert solved.surfaces is not None
                    selected = np.array(solved.production_actions, copy=True)
                    o1 = np.asarray(solved.surfaces.q1_values, dtype=np.float64)
                    o3 = np.asarray(solved.surfaces.q3_values, dtype=np.float64)
                    method["q1_vs_exact_o1"] = _q1_o1_diagnostic(
                        q1_values, o1, mask
                    )
            elif arm == "FULL_AP":
                permutation = permutation_for_step(step_index)
                surface = build_ap_mone_surface(
                    step_env,
                    observation=observation,
                    reference_actions=background,
                    q1_values=q1_values,
                    o2_values=o2,
                    permutation=permutation,
                    rng=env_rng,
                    lambda_bits_per_j=OPS3_LAMBDA_BITS_PER_J,
                    interval_s=interval_s,
                    kappa_bits=OPS3_KAPPA_BITS,
                )
                o1 = np.asarray(surface.q1_values, dtype=np.float64)
                o3 = np.asarray(surface.q3_values, dtype=np.float64)
                selected = select_actions(
                    q1_values, o2, o3, mask, include_c3=True
                )
                method = {
                    "kind": "AP_MONE",
                    "status": "CONSTRUCTED",
                    "permutation_sha256": array_sha256(permutation),
                    "proposal_sha256": array_sha256(surface.proposal_actions),
                    "proposal_flips_from_background": int(
                        np.count_nonzero(surface.proposal_actions != background)
                    ),
                    "selected_flips_from_proposal": int(
                        np.count_nonzero(selected != surface.proposal_actions)
                    ),
                    "identity_passed": True,
                    "order_credited_sum_bits": [
                        float(value) for value in surface.order_credited_sum_bits
                    ],
                    "order_joint_surplus_bits": [
                        float(value) for value in surface.order_joint_surplus_bits
                    ],
                    "order_identity_residual_bits": [
                        float(value)
                        for value in surface.order_identity_residual_bits
                    ],
                }
            elif arm in {"DIAG_O_DROP", "DIAG_O_FULL"}:
                exact_drop = solve_exact_o1_joint_c3(
                    step_env,
                    observation=observation,
                    initial_actions=background,
                    o2_values=o2,
                    include_c3=False,
                    rng=env_rng,
                    lambda_bits_per_j=OPS3_LAMBDA_BITS_PER_J,
                    interval_s=interval_s,
                    kappa_bits=OPS3_KAPPA_BITS,
                    max_sweeps=MAX_SWEEPS,
                )
                result_o = exact_drop
                method = {
                    "kind": "EXACT_O1_DROP",
                    "drop_status": exact_drop.status,
                    "drop_sweep_count": int(exact_drop.sweep_count),
                    "drop_changed_per_sweep": [
                        int(value) for value in exact_drop.changed_per_sweep.tolist()
                    ],
                }
                if arm == "DIAG_O_FULL" and exact_drop.converged:
                    exact_full = solve_exact_o1_joint_c3(
                        step_env,
                        observation=observation,
                        initial_actions=exact_drop.production_actions,
                        o2_values=o2,
                        include_c3=True,
                        rng=env_rng,
                        lambda_bits_per_j=OPS3_LAMBDA_BITS_PER_J,
                        interval_s=interval_s,
                        kappa_bits=OPS3_KAPPA_BITS,
                        max_sweeps=MAX_SWEEPS,
                    )
                    result_o = exact_full
                    method.update(
                        {
                            "kind": "EXACT_O1_FULL",
                            "full_status": exact_full.status,
                            "full_sweep_count": int(exact_full.sweep_count),
                            "full_changed_per_sweep": [
                                int(value)
                                for value in exact_full.changed_per_sweep.tolist()
                            ],
                            "monotonicity_violations": int(
                                np.count_nonzero(
                                    exact_full.monotonicity_violations
                                )
                            ),
                        }
                    )
                elif arm == "DIAG_O_FULL":
                    method.update(
                        {
                            "kind": "EXACT_O1_FULL",
                            "full_status": "NOT_RUN_DROP_FAILED",
                        }
                    )
                step_method_passed = bool(
                    exact_drop.converged
                    and (arm == "DIAG_O_DROP" or result_o.converged)
                )
                # A failed diagnostic must execute and be compared from the
                # shared b0 fail-closed receipt.  Only a converged O-full arm
                # is eligible to compare its exact-O3 action to O-drop.
                if arm == "DIAG_O_FULL" and step_method_passed:
                    comparison = np.array(
                        exact_drop.production_actions, copy=True
                    )
                method["identity_passed"] = bool(step_method_passed)
                if step_method_passed:
                    assert result_o.surfaces is not None
                    selected = np.array(result_o.production_actions, copy=True)
                    o1 = np.asarray(result_o.surfaces.q1_values, dtype=np.float64)
                    if arm == "DIAG_O_FULL":
                        o3 = np.asarray(
                            result_o.surfaces.q3_values, dtype=np.float64
                        )

            after = _live_digest(environment, env_rng)

            reference_zero = all(
                float(o2[uid, int(q1_reference[uid])]) == 0.0
                for uid in range(USERS)
            )
            if arm == "FULL_AP":
                reference_zero = reference_zero and all(
                    float(o1[uid, int(background[uid])]) == 0.0
                    and float(o3[uid, int(background[uid])]) == 0.0
                    for uid in range(USERS)
                )
            elif arm in {"FULL_M1D", "DIAG_O_DROP", "DIAG_O_FULL"} and step_method_passed:
                reference_zero = reference_zero and all(
                    float(o1[uid, int(selected[uid])]) == 0.0
                    and float(o3[uid, int(selected[uid])]) == 0.0
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
                "common_mask": all(
                    np.array_equal(surface.legal_mask, mask[uid])
                    for uid, surface in enumerate(ops3)
                ),
                "reference_rows_exact_zero": reference_zero,
                "opening_service_gate_equal": opening_equal,
                "background_sha256": array_sha256(background),
            }
            mechanics["passed"] = bool(
                mechanics["live_state_unchanged"]
                and mechanics["common_mask"]
                and mechanics["reference_rows_exact_zero"]
                and mechanics["opening_service_gate_equal"]
            )
            if not mechanics["passed"]:
                raise V011OracleError("binding per-step mechanics failed")

            method_passed = method_passed and step_method_passed
            flips = int(np.count_nonzero(selected != comparison))
            action_exposure += flips
            c3_spread += _spread_count(o3, mask)
            opening = _joint_opening_change(
                step_env, env_rng, comparison, selected, interval_s
            )
            if arm == "FULL_AP":
                method.update(
                    _ap_execution_receipt(
                        surface,
                        background,
                        selected,
                        mask,
                        float(opening["fixed_lambda_surplus_bits"]),
                    )
                )
            elif arm == "FULL_M1D":
                method["g_bm_minus_g_b0_bits"] = (
                    float(opening["fixed_lambda_surplus_bits"])
                    if step_method_passed
                    else None
                )
            if opening["status"] == "OBSERVED":
                joint_exposed += 1
                joint_negative += int(opening["fixed_lambda_surplus_bits"] < 0.0)
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
                raise V011OracleError("canonical EE inputs are malformed")
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
                    "action_exposure": flips,
                    "selected_actions": [int(value) for value in selected.tolist()],
                    "surface_sha256": {
                        "q1": array_sha256(q1_values),
                        "o2": array_sha256(o2),
                        "o1": array_sha256(o1),
                        "o3": array_sha256(o3),
                        "mask": array_sha256(mask),
                        "q1_reference": array_sha256(q1_reference),
                        "background": array_sha256(background),
                    },
                    "mechanics": mechanics,
                    "method": method,
                    "joint_opening": opening,
                }
            )
            if result.done:
                if step_index != STEPS_PER_EPISODE - 1:
                    raise V011OracleError("episode terminated before ten steps")
                break
            observation = outcome.observation

    q1_after = _q1_parameter_sha256(q1)
    if q1_before != q1_after:
        raise V011OracleError("frozen Q1 changed during oracle episode")
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
        "action_exposure": action_exposure,
        "joint_opening_exposed_count": joint_exposed,
        "joint_opening_negative_count": joint_negative,
        "method_passed": method_passed,
        "candidate_specific_identity_passed": all(
            bool(step["method"].get("identity_passed", False))
            for step in per_step
        )
        if arm != "DROP_C3"
        else True,
        "mechanics_passed": all(step["mechanics"]["passed"] for step in per_step),
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
        raise V011OracleError(f"refusing to overwrite {output}")
    record = read_prereg(prereg_path)
    q1, q1_receipt = load_frozen_q1(v03_root, lineage)
    field = field_for_world()
    with tempfile.TemporaryDirectory(prefix="mcrl-v011-joint-tle-") as temporary:
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


def _pair_gate(
    *,
    label: str,
    full_arm: str,
    drop_arm: str,
    rows: Sequence[Mapping[str, Any]],
    pooled: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    lineage_rows = {
        (str(row["arm"]), int(row["initialization_seed"])): row for row in rows
    }
    full_pool = pooled[full_arm]
    drop_pool = pooled[drop_arm]
    full_ee = float(full_pool["ratio_of_sums_ee_bits_per_j"])
    drop_ee = float(drop_pool["ratio_of_sums_ee_bits_per_j"])
    by_lineage: dict[str, Any] = {}
    positive = 0
    service_noninferior = 0
    for lineage in LINEAGES:
        full = lineage_rows[(full_arm, lineage)]
        drop = lineage_rows[(drop_arm, lineage)]
        delta = float(full["ratio_of_sums_ee_bits_per_j"]) - float(
            drop["ratio_of_sums_ee_bits_per_j"]
        )
        service_delta = int(full["served_user_steps"]) - int(
            drop["served_user_steps"]
        )
        positive += int(delta > 0.0)
        service_noninferior += int(service_delta >= 0)
        by_lineage[str(lineage)] = {
            "delta_ee_bits_per_j": delta,
            "relative_delta_ee": delta / float(
                drop["ratio_of_sums_ee_bits_per_j"]
            ),
            "delta_served_user_steps": service_delta,
        }

    full_rows = [row for row in rows if row["arm"] == full_arm]
    drop_rows = [row for row in rows if row["arm"] == drop_arm]
    mechanics = all(
        bool(row["mechanics_passed"]) for row in (*full_rows, *drop_rows)
    )
    method = all(bool(row["method_passed"]) for row in (*full_rows, *drop_rows))
    identity = all(
        bool(row.get("candidate_specific_identity_passed", False))
        for row in (*full_rows, *drop_rows)
    )
    spread = sum(int(row["c3_legal_spread_count"]) for row in full_rows)
    exposure = sum(int(row["action_exposure"]) for row in full_rows)
    joint_exposed = sum(int(row["joint_opening_exposed_count"]) for row in full_rows)
    joint_negative = sum(int(row["joint_opening_negative_count"]) for row in full_rows)
    pooled_service = int(full_pool["served_user_steps"]) >= int(
        drop_pool["served_user_steps"]
    )
    hard_stops: list[str] = []
    if not mechanics:
        hard_stops.append(f"{label} mechanics failed")
    if not method:
        hard_stops.append(f"{label} method-specific gate failed")
    if not identity:
        hard_stops.append(f"{label} candidate-specific identity gate failed")
    if spread <= 0:
        hard_stops.append(f"{label} has zero legal-action C3 spread")
    if exposure <= 0:
        hard_stops.append(f"{label} has zero executed-action exposure")
    if not full_ee > drop_ee:
        hard_stops.append(f"{label} pooled EE is not strictly positive")
    if positive < 2:
        hard_stops.append(f"{label} has fewer than two positive lineages")
    if not pooled_service:
        hard_stops.append(f"{label} pooled service guard failed")
    if service_noninferior < 2:
        hard_stops.append(f"{label} has fewer than two service-safe lineages")
    if joint_exposed <= 0:
        hard_stops.append(f"{label} has no joint-opening exposure")
    elif 2 * joint_negative > joint_exposed:
        hard_stops.append(f"{label} joint-opening direction is negative in a majority")
    return {
        "label": label,
        "full_arm": full_arm,
        "drop_arm": drop_arm,
        "passed": not hard_stops,
        "pooled": {
            "delta_ee_bits_per_j": full_ee - drop_ee,
            "relative_delta_ee": (full_ee - drop_ee) / drop_ee,
            "delta_served_user_steps": int(full_pool["served_user_steps"])
            - int(drop_pool["served_user_steps"]),
        },
        "by_lineage": by_lineage,
        "positive_lineages": positive,
        "service_noninferior_lineages": service_noninferior,
        "pooled_service_noninferior": pooled_service,
        "mechanics_passed": mechanics,
        "method_passed": method,
        "candidate_specific_identity_passed": identity,
        "c3_legal_spread_count": spread,
        "action_exposure": exposure,
        "joint_opening_exposed_count": joint_exposed,
        "joint_opening_negative_count": joint_negative,
        "hard_stops": hard_stops,
    }


def ordered_decision(*, passed_ap: bool, passed_m1d: bool, passed_o: bool) -> str:
    """Apply the preregistered candidate order without comparing magnitudes."""

    if passed_ap and (passed_m1d or passed_o):
        return "GO_AP_MONE_LEARNABILITY_PREREG_ONLY"
    if (not passed_ap) and passed_m1d:
        return "GO_M1D_LEARNABILITY_PREREG_ONLY"
    if passed_ap and (not passed_m1d) and (not passed_o):
        return "INCONSISTENT_AP_ONLY_NO_LEARNER_REVIEW"
    if (not passed_ap) and (not passed_m1d) and passed_o:
        return "C1_ALIGNMENT_BLOCKS_C3_NO_LEARNER"
    return "JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED"


def merge_shards(shard_files: Sequence[Path], output_dir: Path) -> dict[str, Any]:
    output = Path(output_dir)
    if output.exists() or output.is_symlink():
        raise V011OracleError(f"refusing to overwrite {output}")
    payloads = [
        json.loads(Path(path).read_text(encoding="utf-8")) for path in shard_files
    ]
    expected_count = len(ARMS) * len(LINEAGES)
    if len(payloads) != expected_count:
        raise V011OracleError(f"merge needs exactly {expected_count} shard files")
    expected_pairs = {(arm, lineage) for arm in ARMS for lineage in LINEAGES}
    observed_pairs: set[tuple[str, int]] = set()
    first = payloads[0]
    for payload in payloads:
        if payload.get("schema") != SHARD_SCHEMA:
            raise V011OracleError("shard schema drifted")
        row = payload.get("row")
        if not isinstance(row, Mapping) or canonical_sha256(row) != payload.get(
            "row_sha256"
        ):
            raise V011OracleError("shard row digest failed")
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
            raise V011OracleError("shard authority hashes disagree")
        observed_pairs.add((str(row["arm"]), int(row["initialization_seed"])))
    if observed_pairs != expected_pairs:
        raise V011OracleError("shard arm/lineage coverage is not exact")
    rows = [payload["row"] for payload in payloads]
    if {str(row["field_root_digest"]) for row in rows} != {
        field_for_world().root_digest
    }:
        raise V011OracleError("shards do not share the frozen field")
    if len({str(row["initial_world_sha256"]) for row in rows}) != 1:
        raise V011OracleError("shards do not share one initial world")

    by_arm = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    pooled = {arm: _pool(by_arm[arm]) for arm in ARMS}
    gates = {
        "AP": _pair_gate(
            label="AP",
            full_arm="FULL_AP",
            drop_arm="DROP_C3",
            rows=rows,
            pooled=pooled,
        ),
        "M1D": _pair_gate(
            label="M1D",
            full_arm="FULL_M1D",
            drop_arm="DROP_C3",
            rows=rows,
            pooled=pooled,
        ),
        "O": _pair_gate(
            label="O",
            full_arm="DIAG_O_FULL",
            drop_arm="DIAG_O_DROP",
            rows=rows,
            pooled=pooled,
        ),
    }
    passed_a = bool(gates["AP"]["passed"])
    passed_m = bool(gates["M1D"]["passed"])
    passed_o = bool(gates["O"]["passed"])
    decision = ordered_decision(
        passed_ap=passed_a, passed_m1d=passed_m, passed_o=passed_o
    )

    result = {
        "schema": RESULT_SCHEMA,
        "claim_ceiling": "ONE_TRAIN_WORLD_ORDERED_ORACLE_NO_LEARNER_NO_TEST",
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
        "summaries": {"pooled_by_arm": pooled, "candidate_gates": gates},
        "gate": {
            "decision": decision,
            "pass_ap": passed_a,
            "pass_m1d": passed_m,
            "pass_exact_o": passed_o,
            "ordered_selection_ap_before_m1d": True,
        },
    }
    result["result_sha256"] = canonical_sha256(result)
    output.mkdir(parents=True, exist_ok=False)
    (output / "result.json").write_bytes(_canonical_bytes(result))
    print(
        f"decision={decision} "
        f"AP={gates['AP']['pooled']['relative_delta_ee']:+.6%} "
        f"M1D={gates['M1D']['pooled']['relative_delta_ee']:+.6%} "
        f"O={gates['O']['pooled']['relative_delta_ee']:+.6%}"
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
