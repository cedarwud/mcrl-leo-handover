#!/usr/bin/env python3
"""Run the frozen v4 activation-regularised load-potential shadow gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import run_oracle_gate as v1  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.link_budget import (  # noqa: E402
    CIRCUIT_POWER_PER_BEAM_W,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
    SEGMENT_START_POWER_W,
    pa_efficiency,
    supply_power_w,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC = HERE / "SPEC-v4-ARLP-SHADOW.md"
SPEC_SHA256 = "a5400b970812eaf2a8489f5ff70e083e78a28eef6cc78794ae3a2e6ffe6f4f2d"
EXPECTED_CHECKPOINT_SHA256 = v1.EXPECTED_CHECKPOINT_SHA256
V4_EVALUATION_SEEDS = tuple(range(2026082601, 2026082611))
PILOT_SEEDS = (2026082401,)
USERS = 100
STEPS_PER_SEED = 10
PILOT_FOCAL_USERS = 2
CONFIRMATION_FOCAL_USERS = 10
LOAD_SCALE = 6.0
T975_DF9 = 2.2621571628540993
EXPECTED_ACTIVATION_POWER_ANCHOR_W = 6.265900454219554
DEFAULT_OUTPUT = HERE / "arlp-shadow-pilot-seed-2026082401-k2-v4.json"


PhysicalKey = v1.PhysicalKey


@dataclass(frozen=True)
class ARLPCandidate:
    """One de-duplicated physical candidate without any Q value."""

    action: int
    key: PhysicalKey
    prior_demand: float
    candidate_sinr: float


@dataclass(frozen=True)
class ProjectedCandidate:
    """One candidate after removing the focal user from its incumbent."""

    choice: ARLPCandidate
    other_demand: float
    activation_indicator: int
    marginal_cost: float


@dataclass(frozen=True)
class ARLPProposal:
    """The outcome-blind ARLP proposal and its replay inputs."""

    choice: ARLPCandidate
    visible_incumbent_key: PhysicalKey | None
    candidates: tuple[ProjectedCandidate, ...]


@dataclass(frozen=True)
class RandomControl:
    """A uniform matched control frozen before any current-slot outcome."""

    choice: ARLPCandidate
    pool: tuple[ARLPCandidate, ...]
    draw_index: int


def _key_for_action(table: Any, action: int) -> PhysicalKey | None:
    association = table.association(action)
    if isinstance(association, Association):
        return (association.norad_id, association.cell_id)
    return None


def physical_candidates(
    table: Any,
    *,
    prior_demand: np.ndarray,
    candidate_sinr: np.ndarray,
) -> tuple[ARLPCandidate, ...]:
    """Return one deterministic candidate per physical key, with no Q1 input."""
    shape = table.mask.shape
    demand = np.asarray(prior_demand, dtype=np.float64)
    sinr = np.asarray(candidate_sinr, dtype=np.float64)
    if demand.shape != shape or sinr.shape != shape:
        raise ValueError("prior demand and candidate SINR must match the action mask")

    by_key: dict[PhysicalKey, ARLPCandidate] = {}
    for action in np.flatnonzero(table.mask).tolist():
        association = table.association(action)
        if not isinstance(association, Association):
            raise RuntimeError("a valid action did not map to a physical association")
        key = (association.norad_id, association.cell_id)
        row = ARLPCandidate(
            action=int(action),
            key=key,
            prior_demand=float(demand[action]),
            candidate_sinr=float(sinr[action]),
        )
        if (
            not math.isfinite(row.prior_demand)
            or not math.isfinite(row.candidate_sinr)
            or row.prior_demand < 0.0
            or not math.isclose(
                row.prior_demand,
                round(row.prior_demand),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise RuntimeError("valid ARLP candidate has invalid observation fields")
        if key in by_key:
            raise RuntimeError("duplicate physical keys are forbidden by frozen v4")
        by_key[key] = row
    rows = tuple(sorted(by_key.values(), key=lambda item: item.action))
    if not rows or len({row.key for row in rows}) != len(rows):
        raise RuntimeError("ARLP candidate set is empty or contains duplicate keys")
    return rows


def visible_incumbent(
    table: Any, access_vector: np.ndarray
) -> tuple[int | None, PhysicalKey | None]:
    """Decode the one visible incumbent allowed by the live state contract."""
    access = np.asarray(access_vector, dtype=np.float64)
    if access.shape != table.mask.shape or not np.all(np.isfinite(access)):
        raise ValueError("access vector must be finite and match the action table")
    visible = np.flatnonzero(access > 0.5)
    if visible.size > 1:
        raise RuntimeError("access vector contains more than one incumbent action")
    if not visible.size:
        return None, None
    action = int(visible[0])
    key = _key_for_action(table, action)
    if key is None:
        raise RuntimeError("visible incumbent did not map to a physical association")
    return action, key


def marginal_cost(other_demand: float) -> float:
    """Projected C3 increment from adding the focal user to a candidate."""
    value = float(other_demand)
    if value < 0.0 or not math.isfinite(value):
        raise ValueError("other demand must be finite and non-negative")
    return (2.0 * value + 1.0) / LOAD_SCALE + float(value == 0.0)


def arlp_proposal(
    *,
    candidates: Sequence[ARLPCandidate],
    visible_incumbent_key: PhysicalKey | None,
) -> ARLPProposal:
    """Select by marginal load/activation cost, then SINR and action index."""
    if not candidates or len({row.key for row in candidates}) != len(candidates):
        raise ValueError("proposal needs a non-empty, de-duplicated candidate set")
    projected: list[ProjectedCandidate] = []
    for candidate in candidates:
        other = candidate.prior_demand
        if candidate.key == visible_incumbent_key:
            if other < 1.0:
                raise RuntimeError("visible incumbent demand does not include focal user")
            other -= 1.0
        projected.append(
            ProjectedCandidate(
                choice=candidate,
                other_demand=float(other),
                activation_indicator=int(other == 0.0),
                marginal_cost=marginal_cost(other),
            )
        )
    selected = min(
        projected,
        key=lambda row: (
            row.marginal_cost,
            -row.choice.candidate_sinr,
            row.choice.action,
        ),
    )
    return ARLPProposal(
        choice=selected.choice,
        visible_incumbent_key=visible_incumbent_key,
        candidates=tuple(sorted(projected, key=lambda row: row.choice.action)),
    )


def draw_random_control(
    candidates: Sequence[ARLPCandidate],
    *,
    reference_key: PhysicalKey | None,
    rng: np.random.Generator,
) -> RandomControl | None:
    """Uniformly draw one valid physical alternative to the Q1 reference."""
    pool = tuple(
        sorted(
            (candidate for candidate in candidates if candidate.key != reference_key),
            key=lambda row: row.action,
        )
    )
    if not pool:
        return None
    draw_index = int(rng.integers(0, len(pool)))
    return RandomControl(choice=pool[draw_index], pool=pool, draw_index=draw_index)


def arlp_potential(loads: Mapping[PhysicalKey, int | float]) -> float:
    """C3 = sum U_b^2 / 6 + number of positive-load beams."""
    positive: list[float] = []
    for value in loads.values():
        load = float(value)
        if load < 0.0 or not math.isfinite(load):
            raise ValueError("beam loads must be finite and non-negative")
        if load > 0.0:
            positive.append(load)
    return float(sum(value * value for value in positive) / LOAD_SCALE + len(positive))


def arlp_difference_reward(served_beam_load: int | float) -> float:
    """Negative focal difference in C3 for one served user."""
    load = float(served_beam_load)
    if load < 1.0 or not math.isfinite(load):
        raise ValueError("served beam load must be finite and at least one")
    return -((2.0 * load - 1.0) / LOAD_SCALE + float(load == 1.0))


def activation_power_anchor() -> dict[str, float]:
    """Compute the spec's minimum one-beam consumed-power anchor."""
    output = np.asarray([SEGMENT_START_POWER_W], dtype=np.float64)
    efficiency = pa_efficiency(
        output,
        max_efficiency=PA_MAX_EFFICIENCY,
        saturation_power_w=PA_SATURATION_POWER_W,
    )
    supply = supply_power_w(output, efficiency)
    return {
        "segment_start_output_power_w": float(output[0]),
        "pa_efficiency": float(efficiency[0]),
        "pa_supply_power_w": float(supply[0]),
        "circuit_power_per_beam_w": float(CIRCUIT_POWER_PER_BEAM_W),
        "minimum_active_beam_consumed_power_w": float(
            supply[0] + CIRCUIT_POWER_PER_BEAM_W
        ),
    }


def _json_key(key: PhysicalKey | None) -> list[int] | None:
    return None if key is None else [int(key[0]), int(key[1])]


def _candidate_fields(candidate: ARLPCandidate) -> dict[str, Any]:
    return {
        "action": candidate.action,
        "key": _json_key(candidate.key),
        "prior_demand": candidate.prior_demand,
        "candidate_sinr": candidate.candidate_sinr,
    }


def _selection_fields(proposal: ARLPProposal) -> list[dict[str, Any]]:
    return [
        _candidate_fields(row.choice)
        | {
            "other_demand": row.other_demand,
            "activation_indicator": row.activation_indicator,
            "marginal_cost": row.marginal_cost,
        }
        for row in proposal.candidates
    ]


def _potential_certificate(evaluation: Any, focal_user: int) -> dict[str, Any]:
    loads = {
        (int(key[0]), int(key[1])): int(value)
        for key, value in evaluation.resolution.eligible_load_by_beam.items()
    }
    potential = arlp_potential(loads)
    served = bool(evaluation.resolution.served[focal_user])
    focal_key: PhysicalKey | None = None
    focal_load = 0
    reward = 0.0
    without = dict(loads)
    if served:
        focal_key = (
            int(evaluation.resolution.serving_satellite[focal_user]),
            int(evaluation.resolution.serving_cell[focal_user]),
        )
        focal_load = int(loads[focal_key])
        reward = arlp_difference_reward(focal_load)
        if focal_load == 1:
            del without[focal_key]
        else:
            without[focal_key] = focal_load - 1
    without_potential = arlp_potential(without)
    marginal = potential - without_potential
    residual = -reward - marginal
    if not math.isclose(residual, 0.0, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError("ARLP difference-reward identity failed")
    return {
        "c3": potential,
        "eligible_loads": [
            {"key": _json_key(key), "load": value}
            for key, value in sorted(loads.items())
        ],
        "focal_beam_key": _json_key(focal_key),
        "focal_beam_load": focal_load,
        "focal_difference_reward": reward,
        "c3_without_focal": without_potential,
        "focal_marginal_c3": marginal,
        "difference_reward_identity_residual": residual,
        "difference_reward_identity_pass": True,
    }


def _snapshot(evaluation: Any, *, num_users: int, beam_bandwidth_hz: float, focal_user: int) -> dict[str, Any]:
    snapshot = v1._evaluation_snapshot(
        evaluation,
        num_users=num_users,
        beam_bandwidth_hz=beam_bandwidth_hz,
    )
    snapshot.update(_potential_certificate(evaluation, focal_user))
    snapshot.update(
        {
            "focal_served": bool(evaluation.resolution.served[focal_user]),
            "focal_outage_infeasible": bool(
                evaluation.resolution.outage_infeasible[focal_user]
            ),
            "focal_rate_bps": float(evaluation.link_rate_bps[focal_user]),
            "focal_handover": evaluation.handovers[focal_user].value,
        }
    )
    if not math.isclose(
        float(snapshot["sum_squared_beam_load"]) / LOAD_SCALE
        + float(snapshot["eff_beams"]),
        float(snapshot["c3"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError("C3 snapshot does not match load and activation fields")
    if int(snapshot["eff_beams"]) != len(snapshot["eligible_loads"]):
        raise RuntimeError("effective beam count differs from positive-load beams")
    if sum(int(row["load"]) for row in snapshot["eligible_loads"]) != int(
        snapshot["served"]
    ):
        raise RuntimeError("eligible loads do not sum to served users")
    return snapshot


CONTRAST_FIELDS = (
    "system_ee_bits_per_j",
    "system_throughput_bps",
    "system_power_w",
    "served",
    "eff_beams",
    "active_satellites",
    "sum_squared_beam_load",
    "c3",
    "focal_rate_bps",
)


def _contrast(
    reference: dict[str, Any], alternative: dict[str, Any]
) -> dict[str, Any]:
    certificate = v1.ee_certificate(
        baseline_throughput_bps=float(reference["system_throughput_bps"]),
        baseline_power_w=float(reference["system_power_w"]),
        alternative_throughput_bps=float(alternative["system_throughput_bps"]),
        alternative_power_w=float(alternative["system_power_w"]),
    )
    return {
        "alternative_minus_reference": {
            field: float(alternative[field]) - float(reference[field])
            for field in CONTRAST_FIELDS
        },
        "ee_certificate": certificate,
        "service_unsafe": bool(
            int(alternative["served"]) < int(reference["served"])
            or not bool(alternative["focal_served"])
        ),
    }


def _assert_one_focal_change(
    reference_actions: np.ndarray,
    alternative_actions: np.ndarray,
    tables: Sequence[Any],
    *,
    focal_user: int,
) -> None:
    reference_keys = v1.physical_action_keys(reference_actions, tables)
    alternative_keys = v1.physical_action_keys(alternative_actions, tables)
    changed = [
        uid
        for uid, (reference, alternative) in enumerate(
            zip(reference_keys, alternative_keys, strict=True)
        )
        if reference != alternative
    ]
    if changed != [focal_user]:
        raise RuntimeError(
            f"counterfactual changed physical users {changed}, expected {[focal_user]}"
        )


def _base_row(
    *,
    seed: int,
    step: int,
    focal_user: int,
    visible_action: int | None,
    proposal: ARLPProposal,
    reference_action: int,
    reference_key: PhysicalKey | None,
    reference_q1: float | None,
) -> dict[str, Any]:
    return {
        "evaluation_seed": seed,
        "step_index": step,
        "focal_user": focal_user,
        "proposal_input_scope": "focal_live_state_without_q1_or_outcome",
        "proposal_frozen_before_q1_reference": True,
        "visible_incumbent_action": visible_action,
        "visible_incumbent_key": _json_key(proposal.visible_incumbent_key),
        "selection_candidates": _selection_fields(proposal),
        "proposal_action": proposal.choice.action,
        "proposal_key": _json_key(proposal.choice.key),
        "proposal_marginal_cost": next(
            row.marginal_cost
            for row in proposal.candidates
            if row.choice.key == proposal.choice.key
        ),
        "reference_action": reference_action,
        "reference_key": _json_key(reference_key),
        "reference_q1": reference_q1,
    }


def _metric_gate(
    rows: Sequence[dict[str, Any]],
    *,
    seeds: Sequence[int],
    value: Any,
    confirmation: bool,
) -> dict[str, Any]:
    pooled_values = [float(value(row)) for row in rows]
    by_seed: dict[str, dict[str, Any]] = {}
    seed_means: list[float] = []
    for seed in seeds:
        values = [
            float(value(row))
            for row in rows
            if int(row["evaluation_seed"]) == int(seed)
        ]
        mean = float(statistics.fmean(values)) if values else None
        by_seed[str(seed)] = {"n": len(values), "mean": mean}
        if mean is not None:
            seed_means.append(mean)
    pooled_mean = (
        float(statistics.fmean(pooled_values)) if pooled_values else None
    )
    interval: dict[str, float] | None = None
    if len(seed_means) >= 2:
        mean = float(statistics.fmean(seed_means))
        standard_error = float(statistics.stdev(seed_means) / math.sqrt(len(seed_means)))
        half_width = T975_DF9 * standard_error
        interval = {
            "mean_of_seed_means": mean,
            "standard_error": standard_error,
            "t_critical": T975_DF9,
            "lower": mean - half_width,
            "upper": mean + half_width,
        }
    positive_seeds = sum(
        row["mean"] is not None and float(row["mean"]) > 0.0
        for row in by_seed.values()
    )
    passed = bool(
        confirmation
        and pooled_mean is not None
        and pooled_mean > 0.0
        and len(seed_means) == 10
        and positive_seeds >= 8
        and interval is not None
        and interval["lower"] > 0.0
    )
    return {
        "n": len(pooled_values),
        "pooled_mean": pooled_mean,
        "positive_seed_means": positive_seeds,
        "by_seed": by_seed,
        "seed_t95": interval,
        "pass": passed,
    }


def summarize_gate(
    rows: Sequence[dict[str, Any]],
    *,
    seeds: Sequence[int],
    confirmation: bool,
) -> dict[str, Any]:
    eligible = [row for row in rows if row["status"] == "evaluated"]
    eligible_by_seed = {
        str(seed): sum(int(row["evaluation_seed"]) == int(seed) for row in eligible)
        for seed in seeds
    }
    coverage_pass = bool(
        confirmation
        and len(rows) == 1000
        and len(eligible) >= 100
        and all(count >= 5 for count in eligible_by_seed.values())
    )
    c3_gate = _metric_gate(
        eligible,
        seeds=seeds,
        value=lambda row: float(row["reference"]["c3"])
        - float(row["arlp"]["c3"]),
        confirmation=confirmation,
    )
    ee_reference_gate = _metric_gate(
        eligible,
        seeds=seeds,
        value=lambda row: row["arlp_vs_reference"]["alternative_minus_reference"][
            "system_ee_bits_per_j"
        ],
        confirmation=confirmation,
    )
    ee_random_gate = _metric_gate(
        eligible,
        seeds=seeds,
        value=lambda row: row["arlp_minus_random"]["alternative_minus_reference"][
            "system_ee_bits_per_j"
        ],
        confirmation=confirmation,
    )
    arlp_unsafe = sum(bool(row["arlp_vs_reference"]["service_unsafe"]) for row in eligible)
    random_unsafe = sum(
        bool(row["random_vs_reference"]["service_unsafe"]) for row in eligible
    )
    denominator = len(eligible)
    arlp_rate = float(arlp_unsafe / denominator) if denominator else None
    random_rate = float(random_unsafe / denominator) if denominator else None
    safety_pass = bool(
        confirmation
        and arlp_rate is not None
        and random_rate is not None
        and arlp_rate <= 0.01 + 1e-15
        and arlp_rate <= random_rate + 0.005 + 1e-15
    )
    conditions = {
        "engineering_and_coverage": coverage_pass,
        "realised_c3_improvement": bool(c3_gate["pass"]),
        "arlp_vs_q1_ee": bool(ee_reference_gate["pass"]),
        "arlp_vs_random_ee": bool(ee_random_gate["pass"]),
        "service_safety": safety_pass,
    }
    if not confirmation:
        decision = "PILOT_ONLY_NO_SCIENTIFIC_DECISION"
    elif all(conditions.values()):
        decision = "PASS_ADVANCE_TO_R3_IMPLEMENTATION_AUDIT_ONLY"
    else:
        decision = "FAIL_DROP_ARLP_R3_DIRECTION"
    return {
        "sampled_rows": len(rows),
        "eligible_rows": len(eligible),
        "coverage_fraction": float(len(eligible) / len(rows)) if rows else 0.0,
        "eligible_by_seed": eligible_by_seed,
        "c3_reference_minus_arlp": c3_gate,
        "ee_arlp_minus_reference_bits_per_j": ee_reference_gate,
        "ee_arlp_minus_random_bits_per_j": ee_random_gate,
        "service_safety": {
            "arlp_unsafe": arlp_unsafe,
            "random_unsafe": random_unsafe,
            "arlp_unsafe_rate": arlp_rate,
            "random_unsafe_rate": random_rate,
            "pass": safety_pass,
        },
        "frozen_conditions": conditions,
        "all_conditions_pass": bool(confirmation and all(conditions.values())),
        "decision": decision,
    }


def run_rollout(
    trainer: Any,
    environment: Any,
    *,
    evaluation_seed: int,
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    action_rng: np.random.Generator,
    control_rng: np.random.Generator,
    focal_users_per_step: int,
) -> dict[str, Any]:
    """Freeze ARLP and matched controls before evaluating any current outcome."""
    states, wrapped_masks, observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    rows: list[dict[str, Any]] = []
    baseline_steps: list[dict[str, Any]] = []

    while True:
        masks = np.stack([wrapped.mask for wrapped in wrapped_masks])
        focal_users = [
            int(uid)
            for uid in action_rng.choice(
                environment.num_users, size=focal_users_per_step, replace=False
            ).tolist()
        ]

        # ARLP uses only live focal observations.  Every proposal for the
        # step is frozen before the checkpoint's Q1 reference is computed.
        prebuilt: list[
            tuple[int, int | None, tuple[ARLPCandidate, ...], ARLPProposal]
        ] = []
        for focal_user in focal_users:
            table = observation.candidates.slot_tables[focal_user]
            candidates = physical_candidates(
                table,
                prior_demand=observation.user_states[focal_user].beam_loads,
                candidate_sinr=observation.candidate_sinr[focal_user],
            )
            incumbent_action, incumbent_key = visible_incumbent(
                table, observation.user_states[focal_user].access_vector
            )
            proposal = arlp_proposal(
                candidates=candidates, visible_incumbent_key=incumbent_key
            )
            prebuilt.append((focal_user, incumbent_action, candidates, proposal))

        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = v1.masked_greedy_actions(q1, masks)
        tables = observation.candidates.slot_tables
        baseline_keys = v1.physical_action_keys(baseline_actions, tables)

        # Reference-dependent eligibility and the uniform matched draw are
        # also frozen before any call to evaluate_actions.
        prepared: list[
            tuple[
                int,
                int | None,
                ARLPProposal,
                int,
                PhysicalKey | None,
                float | None,
                RandomControl | None,
            ]
        ] = []
        for focal_user, incumbent_action, candidates, proposal in prebuilt:
            reference_action = int(baseline_actions[focal_user])
            reference_key = baseline_keys[focal_user]
            reference_q1 = (
                float(q1[focal_user, reference_action])
                if reference_action >= 0
                else None
            )
            control = None
            if proposal.choice.key != reference_key:
                control = draw_random_control(
                    candidates, reference_key=reference_key, rng=control_rng
                )
                if control is None:
                    raise RuntimeError("eligible ARLP row lacks a random alternative")
            prepared.append(
                (
                    focal_user,
                    incumbent_action,
                    proposal,
                    reference_action,
                    reference_key,
                    reference_q1,
                    control,
                )
            )

        step_environment = environment.environment
        baseline = step_environment.evaluate_actions(baseline_actions, env_rng)
        baseline_step_snapshot = v1._evaluation_snapshot(
            baseline,
            num_users=environment.num_users,
            beam_bandwidth_hz=step_environment.physics.beam_bandwidth_hz,
        )
        for (
            focal_user,
            incumbent_action,
            proposal,
            reference_action,
            reference_key,
            reference_q1,
            control,
        ) in prepared:
            row = _base_row(
                seed=evaluation_seed,
                step=int(observation.step_index),
                focal_user=focal_user,
                visible_action=incumbent_action,
                proposal=proposal,
                reference_action=reference_action,
                reference_key=reference_key,
                reference_q1=reference_q1,
            )
            reference_snapshot = _snapshot(
                baseline,
                num_users=environment.num_users,
                beam_bandwidth_hz=step_environment.physics.beam_bandwidth_hz,
                focal_user=focal_user,
            )
            if control is None:
                row.update(
                    {
                        "status": "ineligible",
                        "reason": "proposal_matches_q1_reference",
                        "random_control": None,
                        "reference": reference_snapshot,
                        "arlp": None,
                        "random": None,
                    }
                )
                rows.append(row)
                continue

            arlp_actions = baseline_actions.copy()
            arlp_actions[focal_user] = proposal.choice.action
            random_actions = baseline_actions.copy()
            random_actions[focal_user] = control.choice.action
            _assert_one_focal_change(
                baseline_actions, arlp_actions, tables, focal_user=focal_user
            )
            _assert_one_focal_change(
                baseline_actions, random_actions, tables, focal_user=focal_user
            )
            arlp_evaluation = step_environment.evaluate_actions(arlp_actions, env_rng)
            random_evaluation = step_environment.evaluate_actions(random_actions, env_rng)
            arlp_snapshot = _snapshot(
                arlp_evaluation,
                num_users=environment.num_users,
                beam_bandwidth_hz=step_environment.physics.beam_bandwidth_hz,
                focal_user=focal_user,
            )
            random_snapshot = _snapshot(
                random_evaluation,
                num_users=environment.num_users,
                beam_bandwidth_hz=step_environment.physics.beam_bandwidth_hz,
                focal_user=focal_user,
            )
            row.update(
                {
                    "status": "evaluated",
                    "reason": "eligible",
                    "random_control": {
                        "draw_index": control.draw_index,
                        "pool": [_candidate_fields(item) for item in control.pool],
                        "action": control.choice.action,
                        "key": _json_key(control.choice.key),
                        "frozen_before_outcome": True,
                    },
                    "reference": reference_snapshot,
                    "arlp": arlp_snapshot,
                    "random": random_snapshot,
                    "arlp_vs_reference": _contrast(
                        reference_snapshot, arlp_snapshot
                    ),
                    "random_vs_reference": _contrast(
                        reference_snapshot, random_snapshot
                    ),
                    "arlp_minus_random": _contrast(
                        random_snapshot, arlp_snapshot
                    ),
                    "exactly_one_focal_physical_action_changed": True,
                    "common_random_number_contract_verified": True,
                }
            )
            rows.append(row)

        result = environment.step(baseline_actions, env_rng)
        outcome = environment.last_outcome
        v1._assert_full_preview_parity(baseline, outcome)
        baseline_steps.append(
            {
                "step_index": int(outcome.step_index),
                "focal_users": focal_users,
                "metrics": baseline_step_snapshot,
                "preview_commit_parity": True,
            }
        )
        if result.done:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = outcome.observation
        encoded = trainer.encode_states(states)

    return {
        "evaluation_seed": int(evaluation_seed),
        "baseline_steps": baseline_steps,
        "proposal_rows": rows,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("pilot", "confirmation"), default="pilot")
    parser.add_argument("--input-dir", type=Path, default=v1.DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=v1.DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if v1._sha256(SPEC) != SPEC_SHA256:
        raise RuntimeError("frozen v4 specification digest changed")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    anchor = activation_power_anchor()
    if not math.isclose(
        anchor["minimum_active_beam_consumed_power_w"],
        EXPECTED_ACTIVATION_POWER_ANCHOR_W,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError("activation-power anchor differs from frozen v4 spec")

    confirmation = args.stage == "confirmation"
    seeds = V4_EVALUATION_SEEDS if confirmation else PILOT_SEEDS
    focal_users_per_step = (
        CONFIRMATION_FOCAL_USERS if confirmation else PILOT_FOCAL_USERS
    )
    record = read_prereg(args.prereg)
    current_code_sha = _code_sha256(_default_code_paths())
    with tempfile.TemporaryDirectory(prefix="mcrl-catfish-arlp-") as temp:
        archive = v1._frozen_archive(record, args.tle_root, Path(temp) / "frozen-tle")
        trainer, checkpoint = v1._verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=USERS,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint digest differs from frozen v4 spec")
        rollouts = []
        for seed in seeds:
            environment = v1._make_environment(archive, users=USERS)
            env_rng, mobility_rng, action_rng, control_rng = _evaluation_rngs(seed)
            rollouts.append(
                run_rollout(
                    trainer,
                    environment,
                    evaluation_seed=seed,
                    env_rng=env_rng,
                    mobility_rng=mobility_rng,
                    action_rng=action_rng,
                    control_rng=control_rng,
                    focal_users_per_step=focal_users_per_step,
                )
            )

    rows = [row for rollout in rollouts for row in rollout["proposal_rows"]]
    gate_summary = summarize_gate(
        rows, seeds=seeds, confirmation=confirmation
    )
    payload = {
        "schema": "mcrl-catfish-arlp-shadow-gate-v4",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "stage": args.stage,
        "mode": "evaluation-only shadow gate; no fitting, RL training, or coordination",
        "claim_boundary": (
            "one-focal-user immediate matched counterfactual only; pass permits an "
            "implementation/state audit and separately frozen short RL pilot only"
        ),
        "spec_path": str(SPEC),
        "spec_sha256": SPEC_SHA256,
        "analysis_path": str(Path(__file__).resolve()),
        "analysis_sha256": v1._sha256(Path(__file__).resolve()),
        "analysis_code_sha256": current_code_sha,
        "analysis_source_matches_training": (
            current_code_sha == checkpoint["launched_code_sha256"]
        ),
        "checkpoint": checkpoint,
        "prereg_path": str(args.prereg),
        "prereg_digest": record.digest,
        "prereg_file_sha256": v1._sha256(args.prereg),
        "frozen_tle_contract_verified": True,
        "evaluation_seeds": list(seeds),
        "users": USERS,
        "steps_per_seed": STEPS_PER_SEED,
        "focal_users_per_step": focal_users_per_step,
        "independent_unit": "evaluation seed; user-step rows are clustered",
        "sampling": (
            "data-blind without-replacement focal users before Q1 and outcomes; "
            "ineligible rows retained without replacement"
        ),
        "proposal_timing": (
            "ARLP frozen before Q1 reference; matched random frozen after Q1 "
            "reference but before any current-slot outcome"
        ),
        "common_random_number_contract": (
            "reference, ARLP, and random use evaluate_actions from the same "
            "pre-decision state and cloned environment RNG; only Q1 commits"
        ),
        "load_scale": LOAD_SCALE,
        "activation_power_anchor": anchor,
        "baseline_preview_equals_committed_step_every_time": True,
        "fractional_ee_identity_pass_every_time": True,
        "difference_reward_identity_pass_every_time": True,
        "exactly_one_focal_physical_action_changed_every_eligible_row": True,
        "gate_summary": gate_summary,
        "rollouts": rollouts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
