#!/usr/bin/env python3
"""Run the frozen evaluation-only local R2/R3 Catfish opportunity gate."""

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
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from mcrl.env.action_contract import (  # noqa: E402
    HANDOVER_COST,
    Association,
    SlotTable,
    UNSERVED,
)
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.step import ActionEvaluation, StepOutcome  # noqa: E402
from mcrl.runtime.head_pivotality import (  # noqa: E402
    _assert_preview_matches_outcome,
    action_evaluation_metrics,
    masked_greedy_actions,
    physical_action_keys,
)
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)
from scripts.run_head_pivotality_probe import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_PREREG,
    _frozen_archive,
    _make_environment,
    _sha256,
    _verify_and_load_trainer,
)


SPEC = HERE / "SPEC-v1-FROZEN-PILOT.md"
SPEC_SHA256 = "e0395bd7735649074fb4993e4a2ef4c6e42f9639b831cb8b4d88e7fef8de835b"
EXPECTED_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
DEFAULT_OUTPUT = HERE / "pilot-seed-2026082401-k2-v1.json"
FAMILIES = (
    "r2_exact_stay",
    "r2_same_satellite",
    "r3_reuse_intended",
    "r3_open_new_intent",
)
R2_FAMILIES = frozenset(FAMILIES[:2])


PhysicalKey = tuple[int, int]


@dataclass(frozen=True)
class CandidateChoice:
    """One de-duplicated pre-decision physical candidate."""

    action: int
    key: PhysicalKey
    prior_demand: float
    candidate_sinr: float
    q1: float


@dataclass(frozen=True)
class Proposal:
    """Canonical proposal or a pre-outcome reason why it is unavailable."""

    family: str
    choice: CandidateChoice | None
    reason: str


def _json_key(key: PhysicalKey | None) -> list[int] | None:
    return list(key) if key is not None else None


def _json_previous(previous: object) -> dict[str, Any]:
    if isinstance(previous, Association):
        return {"kind": "association", "key": [previous.norad_id, previous.cell_id]}
    if previous is UNSERVED:
        return {"kind": "unserved", "key": None}
    if previous is None:
        return {"kind": "episode_start", "key": None}
    raise TypeError(f"unexpected previous association: {previous!r}")


def _physical_candidates(
    table: SlotTable,
    *,
    prior_demand: np.ndarray,
    candidate_sinr: np.ndarray,
    q1: np.ndarray,
) -> list[CandidateChoice]:
    """Return one deterministic representative per physical key."""
    shape = table.mask.shape
    for name, values in (
        ("prior_demand", prior_demand),
        ("candidate_sinr", candidate_sinr),
        ("q1", q1),
    ):
        if np.asarray(values).shape != shape:
            raise ValueError(f"{name} must have shape {shape}")

    by_key: dict[PhysicalKey, CandidateChoice] = {}
    for action in np.flatnonzero(table.mask).tolist():
        association = table.association(action)
        if not isinstance(association, Association):
            raise RuntimeError("a valid action did not map to a physical association")
        key = (association.norad_id, association.cell_id)
        choice = CandidateChoice(
            action=int(action),
            key=key,
            prior_demand=float(prior_demand[action]),
            candidate_sinr=float(candidate_sinr[action]),
            q1=float(q1[action]),
        )
        if not all(
            math.isfinite(value)
            for value in (choice.prior_demand, choice.candidate_sinr, choice.q1)
        ):
            raise RuntimeError("valid physical candidate has non-finite state/Q1")
        previous = by_key.get(key)
        if previous is not None:
            if not math.isclose(
                choice.prior_demand, previous.prior_demand, rel_tol=0.0, abs_tol=0.0
            ) or not math.isclose(
                choice.candidate_sinr,
                previous.candidate_sinr,
                rel_tol=1e-12,
                abs_tol=1e-15,
            ):
                raise RuntimeError(
                    "duplicate physical action has inconsistent pre-decision state"
                )
            if choice.action < previous.action:
                by_key[key] = choice
        else:
            by_key[key] = choice
    return list(by_key.values())


def canonical_proposal(
    family: str,
    *,
    previous: object,
    baseline_key: PhysicalKey | None,
    candidates: Sequence[CandidateChoice],
    baseline_intent: set[PhysicalKey],
    other_user_intent: set[PhysicalKey],
) -> Proposal:
    """Select one proposal without observing any current-slot outcome."""
    if family not in FAMILIES:
        raise ValueError(f"unknown proposal family: {family}")

    if family in R2_FAMILIES:
        if not isinstance(previous, Association):
            reason = "episode_start" if previous is None else "previously_unserved"
            return Proposal(family, None, reason)
        incumbent = (previous.norad_id, previous.cell_id)

        if family == "r2_exact_stay":
            if baseline_key == incumbent:
                return Proposal(family, None, "reference_already_exact_stay")
            matches = [candidate for candidate in candidates if candidate.key == incumbent]
            if not matches:
                return Proposal(family, None, "incumbent_not_valid")
            return Proposal(family, min(matches, key=lambda row: row.action), "eligible")

        if baseline_key is None:
            return Proposal(family, None, "reference_unserved")
        if baseline_key[0] == incumbent[0]:
            return Proposal(family, None, "reference_already_same_satellite")
        matches = [
            candidate
            for candidate in candidates
            if candidate.key[0] == incumbent[0] and candidate.key != incumbent
        ]
        if not matches:
            return Proposal(family, None, "no_nonincumbent_same_satellite_candidate")
        selected = min(
            matches,
            key=lambda row: (
                -row.candidate_sinr,
                row.key[0],
                row.key[1],
                row.action,
            ),
        )
        return Proposal(family, selected, "eligible")

    alternatives = [candidate for candidate in candidates if candidate.key != baseline_key]
    if family == "r3_reuse_intended":
        matches = [candidate for candidate in alternatives if candidate.key in other_user_intent]
        unavailable = "no_other_user_intended_candidate"
    else:
        matches = [candidate for candidate in alternatives if candidate.key not in baseline_intent]
        unavailable = "no_new_intended_candidate"
    if not matches:
        return Proposal(family, None, unavailable)
    selected = min(
        matches,
        key=lambda row: (
            row.prior_demand,
            -row.candidate_sinr,
            row.key[0],
            row.key[1],
            row.action,
        ),
    )
    return Proposal(family, selected, "eligible")


def ee_certificate(
    *,
    baseline_throughput_bps: float,
    baseline_power_w: float,
    alternative_throughput_bps: float,
    alternative_power_w: float,
) -> dict[str, float | int | bool]:
    """Compute and verify the exact fractional EE identity."""
    if baseline_power_w <= 0.0 or alternative_power_w <= 0.0:
        raise ValueError("system powers must be positive")
    eta0 = baseline_throughput_bps / baseline_power_w
    delta_r = alternative_throughput_bps - baseline_throughput_bps
    delta_p = alternative_power_w - baseline_power_w
    g_eta = delta_r - eta0 * delta_p
    delta_ee = (
        alternative_throughput_bps / alternative_power_w
        - baseline_throughput_bps / baseline_power_w
    )
    identity_value = g_eta / alternative_power_w
    residual = delta_ee - identity_value
    tolerance = max(1e-9, 1e-10 * max(abs(delta_ee), 1.0))
    identity_pass = abs(residual) <= tolerance

    def sign(value: float) -> int:
        return 1 if value > 0.0 else (-1 if value < 0.0 else 0)

    sign_pass = sign(delta_ee) == sign(g_eta)
    if not identity_pass or not sign_pass:
        raise RuntimeError(
            "fractional EE identity failed: "
            f"DeltaEE={delta_ee}, g/Palt={identity_value}, residual={residual}"
        )
    return {
        "baseline_eta_bits_per_j": float(eta0),
        "delta_throughput_bps": float(delta_r),
        "delta_power_w": float(delta_p),
        "g_eta_bps": float(g_eta),
        "delta_ee_bits_per_j": float(delta_ee),
        "identity_value_bits_per_j": float(identity_value),
        "identity_residual_bits_per_j": float(residual),
        "identity_tolerance_bits_per_j": float(tolerance),
        "identity_pass": bool(identity_pass),
        "sign_pass": bool(sign_pass),
        "sign": sign(delta_ee),
    }


def _active_keys(evaluation: ActionEvaluation) -> set[PhysicalKey]:
    return set(evaluation.resolution.active_beams)


def _load_stats(evaluation: ActionEvaluation) -> dict[str, float]:
    loads = np.asarray(
        list(evaluation.resolution.eligible_load_by_beam.values()), dtype=np.float64
    )
    return {
        "sum_squared_beam_load": float(np.square(loads).sum()),
        "mean_beam_load": float(loads.mean()) if loads.size else 0.0,
        "max_beam_load": float(loads.max()) if loads.size else 0.0,
    }


def _evaluation_snapshot(
    evaluation: ActionEvaluation, *, num_users: int, beam_bandwidth_hz: float
) -> dict[str, Any]:
    metrics = action_evaluation_metrics(
        evaluation,
        num_users=num_users,
        beam_bandwidth_hz=beam_bandwidth_hz,
    )
    return metrics | {
        "active_beam_keys": [list(key) for key in sorted(_active_keys(evaluation))],
        "served_user_ids": np.flatnonzero(evaluation.resolution.served).tolist(),
        "outage_infeasible_user_ids": np.flatnonzero(
            evaluation.resolution.outage_infeasible
        ).tolist(),
    }


def _assert_full_preview_parity(
    preview: ActionEvaluation, outcome: StepOutcome
) -> None:
    _assert_preview_matches_outcome(preview, outcome)
    pairs = (
        (preview.resolution.served, outcome.resolution.served, "served"),
        (
            preview.resolution.serving_cell,
            outcome.resolution.serving_cell,
            "serving_cell",
        ),
        (
            preview.resolution.serving_satellite,
            outcome.resolution.serving_satellite,
            "serving_satellite",
        ),
        (
            preview.resolution.outage_infeasible,
            outcome.resolution.outage_infeasible,
            "outage_infeasible",
        ),
    )
    for expected, observed, name in pairs:
        if not np.array_equal(expected, observed):
            raise RuntimeError(f"counterfactual preview changed baseline {name}")
    if (
        preview.resolution.demand_by_beam != outcome.resolution.demand_by_beam
        or preview.resolution.eligible_load_by_beam
        != outcome.resolution.eligible_load_by_beam
    ):
        raise RuntimeError("counterfactual preview changed baseline beam loads")


def _ineligible_row(
    *,
    seed: int,
    step: int,
    focal_user: int,
    family: str,
    reason: str,
    previous: object,
    baseline_action: int,
    baseline_key: PhysicalKey | None,
) -> dict[str, Any]:
    return {
        "evaluation_seed": seed,
        "step_index": step,
        "focal_user": focal_user,
        "family": family,
        "status": "ineligible",
        "reason": reason,
        "previous": _json_previous(previous),
        "reference_action": baseline_action,
        "reference_key": _json_key(baseline_key),
        "proposal_action": None,
        "proposal_key": None,
    }


def _evaluated_row(
    *,
    seed: int,
    step: int,
    focal_user: int,
    proposal: Proposal,
    previous: object,
    baseline_action: int,
    baseline_key: PhysicalKey | None,
    baseline_intent: set[PhysicalKey],
    other_user_intent: set[PhysicalKey],
    baseline: ActionEvaluation,
    alternative: ActionEvaluation,
    q1_reference: float | None,
) -> dict[str, Any]:
    choice = proposal.choice
    if choice is None:
        raise ValueError("cannot evaluate an empty proposal")
    certificate = ee_certificate(
        baseline_throughput_bps=float(baseline.energy.system_throughput_bps),
        baseline_power_w=float(baseline.energy.system_consumed_power_w),
        alternative_throughput_bps=float(alternative.energy.system_throughput_bps),
        alternative_power_w=float(alternative.energy.system_consumed_power_w),
    )
    base_active = _active_keys(baseline)
    alt_active = _active_keys(alternative)
    baseline_loads = _load_stats(baseline)
    alternative_loads = _load_stats(alternative)
    delta_load_relief = (
        baseline_loads["sum_squared_beam_load"]
        - alternative_loads["sum_squared_beam_load"]
    )
    base_handover = baseline.handovers[focal_user]
    alt_handover = alternative.handovers[focal_user]
    if proposal.family in R2_FAMILIES:
        role_positive = HANDOVER_COST[alt_handover] < HANDOVER_COST[base_handover]
    else:
        role_positive = delta_load_relief > 0.0
    focal_served = bool(alternative.resolution.served[focal_user])
    service_safe = (
        alternative.resolution.served_count >= baseline.resolution.served_count
        and focal_served
    )
    ee_positive = int(certificate["sign"]) > 0
    jointly_positive = bool(role_positive and ee_positive and service_safe)
    focal_rate_delta = float(
        alternative.link_rate_bps[focal_user] - baseline.link_rate_bps[focal_user]
    )
    other_rate_delta = float(
        np.delete(alternative.link_rate_bps - baseline.link_rate_bps, focal_user).sum()
    )
    realised_opening = choice.key in alt_active and choice.key not in base_active
    alternative_intent = set(other_user_intent)
    alternative_intent.add(choice.key)

    row: dict[str, Any] = {
        "evaluation_seed": seed,
        "step_index": step,
        "focal_user": focal_user,
        "family": proposal.family,
        "status": "evaluated",
        "reason": proposal.reason,
        "previous": _json_previous(previous),
        "reference_action": baseline_action,
        "reference_key": _json_key(baseline_key),
        "proposal_action": choice.action,
        "proposal_key": _json_key(choice.key),
        "reference_q1": q1_reference,
        "proposal_q1": choice.q1,
        "proposal_prior_demand": choice.prior_demand,
        "proposal_candidate_sinr": choice.candidate_sinr,
        "proposal_in_reference_intent": choice.key in baseline_intent,
        "proposal_in_other_user_intent": choice.key in other_user_intent,
        "reference_intended_beams": [
            list(key) for key in sorted(baseline_intent)
        ],
        "alternative_intended_beams": [
            list(key) for key in sorted(alternative_intent)
        ],
        "intended_beams_added": [
            list(key) for key in sorted(alternative_intent - baseline_intent)
        ],
        "intended_beams_removed": [
            list(key) for key in sorted(baseline_intent - alternative_intent)
        ],
        "reference_active_beams": [list(key) for key in sorted(base_active)],
        "alternative_active_beams": [list(key) for key in sorted(alt_active)],
        "realised_active_beams_added": [
            list(key) for key in sorted(alt_active - base_active)
        ],
        "realised_active_beams_removed": [
            list(key) for key in sorted(base_active - alt_active)
        ],
        "realised_proposed_beam_opening": realised_opening,
        "reference_focal_handover": base_handover.value,
        "alternative_focal_handover": alt_handover.value,
        "reference_focal_served": bool(baseline.resolution.served[focal_user]),
        "alternative_focal_served": focal_served,
        "reference_focal_outage_infeasible": bool(
            baseline.resolution.outage_infeasible[focal_user]
        ),
        "alternative_focal_outage_infeasible": bool(
            alternative.resolution.outage_infeasible[focal_user]
        ),
        "reference_served": baseline.resolution.served_count,
        "alternative_served": alternative.resolution.served_count,
        "reference_effective_beams": int(baseline.energy.eff_beams),
        "alternative_effective_beams": int(alternative.energy.eff_beams),
        "reference_active_satellites": len({key[0] for key in base_active}),
        "alternative_active_satellites": len({key[0] for key in alt_active}),
        "service_safe": service_safe,
        "focal_rate_delta_bps": focal_rate_delta,
        "other_users_rate_delta_bps": other_rate_delta,
        "reference_load": baseline_loads,
        "alternative_load": alternative_loads,
        "delta_load_relief": float(delta_load_relief),
        "role_positive": bool(role_positive),
        "ee_positive": bool(ee_positive),
        "jointly_positive": jointly_positive,
    }
    row.update(certificate)
    if proposal.family in R2_FAMILIES:
        g_eta = float(certificate["g_eta_bps"])
        eta0 = float(certificate["baseline_eta_bits_per_j"])
        row.update(
            {
                "ee_claim_status": "diagnostic_only_unidentified_without_T_HO_E_HO",
                "required_avoided_handover_equivalent_bps": max(0.0, -g_eta),
                "required_avoided_handover_power_w": max(0.0, -g_eta / eta0),
            }
        )
    else:
        row["ee_claim_status"] = "immediate_local_opportunity_only"
    return row


def _family_summary(
    rows: Sequence[dict[str, Any]], *, confirmation: bool
) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for family in FAMILIES:
        all_rows = [row for row in rows if row["family"] == family]
        eligible = [row for row in all_rows if row["status"] == "evaluated"]
        by_seed: dict[str, Any] = {}
        for seed in sorted({int(row["evaluation_seed"]) for row in all_rows}):
            seed_rows = [row for row in eligible if int(row["evaluation_seed"]) == seed]
            by_seed[str(seed)] = {
                "eligible": len(seed_rows),
                "role_positive": sum(bool(row["role_positive"]) for row in seed_rows),
                "ee_positive": sum(bool(row["ee_positive"]) for row in seed_rows),
                "jointly_positive": sum(
                    bool(row["jointly_positive"]) for row in seed_rows
                ),
            }
        joint = sum(bool(row["jointly_positive"]) for row in eligible)
        role = sum(bool(row["role_positive"]) for row in eligible)
        ee = sum(bool(row["ee_positive"]) for row in eligible)
        positive_seed_coverage = sum(
            int(seed_row["jointly_positive"]) > 0 for seed_row in by_seed.values()
        )
        opportunity_fraction = float(joint / len(eligible)) if eligible else 0.0
        threshold_pass = bool(
            confirmation
            and len(eligible) >= 30
            and positive_seed_coverage >= 8
            and opportunity_fraction >= 0.10
        )
        if not confirmation:
            decision = "PILOT_ONLY_NO_ROLE_DECISION"
        elif threshold_pass and family in R2_FAMILIES:
            decision = "ADVANCE_TO_PHYSICAL_HANDOVER_PARAMETER_GATE_ONLY"
        elif threshold_pass:
            decision = "ADVANCE_TO_R3_LEARNABILITY_TEST_ONLY"
        else:
            decision = "DROP_OR_REDESIGN_BEFORE_TRAINING"
        summary: dict[str, Any] = {
            "sampled_rows": len(all_rows),
            "eligible": len(eligible),
            "ineligible": len(all_rows) - len(eligible),
            "role_positive": role,
            "ee_positive": ee,
            "jointly_positive": joint,
            "jointly_positive_fraction_of_eligible": opportunity_fraction,
            "seeds_with_jointly_positive": positive_seed_coverage,
            "by_seed": by_seed,
            "threshold_pass": threshold_pass,
            "decision": decision,
        }
        if family in R2_FAMILIES and eligible:
            burdens = [
                float(row["required_avoided_handover_equivalent_bps"])
                for row in eligible
            ]
            summary["r2_required_equivalent_bps"] = {
                "mean": float(statistics.fmean(burdens)),
                "median": float(statistics.median(burdens)),
                "max": float(max(burdens)),
            }
        summaries[family] = summary
    return summaries


def run_rollout(
    trainer: Any,
    environment: Any,
    *,
    evaluation_seed: int,
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    action_rng: np.random.Generator,
    focal_users_per_step: int,
) -> dict[str, Any]:
    """Advance only the Q1 projection while discarding local alternatives."""
    states, wrapped_masks, observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    rows: list[dict[str, Any]] = []
    baseline_steps: list[dict[str, Any]] = []

    while True:
        masks = np.stack([wrapped.mask for wrapped in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = masked_greedy_actions(q1, masks)
        baseline_keys = physical_action_keys(
            baseline_actions, observation.candidates.slot_tables
        )
        baseline_intent = {key for key in baseline_keys if key is not None}
        step_environment = environment.environment
        focal_users = [
            int(uid)
            for uid in action_rng.choice(
                environment.num_users, size=focal_users_per_step, replace=False
            ).tolist()
        ]
        prebuilt: list[
            tuple[
                int,
                object,
                PhysicalKey | None,
                set[PhysicalKey],
                Proposal,
            ]
        ] = []
        for focal_user in focal_users:
            table = observation.candidates.slot_tables[focal_user]
            previous = step_environment._ledgers[focal_user].previous
            candidates = _physical_candidates(
                table,
                prior_demand=observation.user_states[focal_user].beam_loads,
                candidate_sinr=observation.candidate_sinr[focal_user],
                q1=q1[focal_user],
            )
            baseline_key = baseline_keys[focal_user]
            other_user_intent = {
                key
                for uid, key in enumerate(baseline_keys)
                if uid != focal_user and key is not None
            }
            for family in FAMILIES:
                proposal = canonical_proposal(
                    family,
                    previous=previous,
                    baseline_key=baseline_key,
                    candidates=candidates,
                    baseline_intent=baseline_intent,
                    other_user_intent=other_user_intent,
                )
                prebuilt.append(
                    (
                        focal_user,
                        previous,
                        baseline_key,
                        other_user_intent,
                        proposal,
                    )
                )

        # No current-slot physics has been evaluated above this line.  The
        # proposal list is now frozen for this step.
        baseline = step_environment.evaluate_actions(baseline_actions, env_rng)
        baseline_snapshot = _evaluation_snapshot(
            baseline,
            num_users=environment.num_users,
            beam_bandwidth_hz=step_environment.physics.beam_bandwidth_hz,
        )
        for (
            focal_user,
            previous,
            baseline_key,
            other_user_intent,
            proposal,
        ) in prebuilt:
            if proposal.choice is None:
                rows.append(
                    _ineligible_row(
                        seed=evaluation_seed,
                        step=int(observation.step_index),
                        focal_user=focal_user,
                        family=proposal.family,
                        reason=proposal.reason,
                        previous=previous,
                        baseline_action=int(baseline_actions[focal_user]),
                        baseline_key=baseline_key,
                    )
                )
                continue

            alternative_actions = baseline_actions.copy()
            alternative_actions[focal_user] = proposal.choice.action
            alternative_keys = physical_action_keys(
                alternative_actions, observation.candidates.slot_tables
            )
            changed_users = [
                uid
                for uid, (reference, alternative) in enumerate(
                    zip(baseline_keys, alternative_keys, strict=True)
                )
                if reference != alternative
            ]
            if changed_users != [focal_user]:
                raise RuntimeError(
                    "proposal did not change exactly the focal physical action: "
                    f"expected {[focal_user]}, got {changed_users}"
                )
            alternative = step_environment.evaluate_actions(alternative_actions, env_rng)
            baseline_action = int(baseline_actions[focal_user])
            q1_reference = (
                float(q1[focal_user, baseline_action])
                if baseline_action >= 0
                else None
            )
            rows.append(
                _evaluated_row(
                    seed=evaluation_seed,
                    step=int(observation.step_index),
                    focal_user=focal_user,
                    proposal=proposal,
                    previous=previous,
                    baseline_action=baseline_action,
                    baseline_key=baseline_key,
                    baseline_intent=baseline_intent,
                    other_user_intent=other_user_intent,
                    baseline=baseline,
                    alternative=alternative,
                    q1_reference=q1_reference,
                )
            )

        result = environment.step(baseline_actions, env_rng)
        outcome = environment.last_outcome
        _assert_full_preview_parity(baseline, outcome)
        baseline_steps.append(
            {
                "step_index": int(outcome.step_index),
                "focal_users": focal_users,
                "metrics": baseline_snapshot,
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
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root",
        type=Path,
        default=Path(TLE_ROOT_DEFAULT).expanduser(),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--focal-users-per-step", type=int, default=2)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[P6_EVALUATION_SEEDS[0]]
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if _sha256(SPEC) != SPEC_SHA256:
        raise RuntimeError("frozen SPEC-v1 digest changed")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if args.users < 1:
        raise ValueError("--users must be positive")
    if not 1 <= args.focal_users_per_step <= args.users:
        raise ValueError("--focal-users-per-step must be within [1, users]")
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("--seeds must be unique")
    if any(seed not in P6_EVALUATION_SEEDS for seed in args.seeds):
        raise ValueError("every seed must belong to the frozen P6 evaluation set")

    from mcrl.runtime.prereg import read_prereg

    record = read_prereg(args.prereg)
    current_code_sha = _code_sha256(_default_code_paths())
    with tempfile.TemporaryDirectory(prefix="mcrl-catfish-oracle-gate-") as temp:
        archive = _frozen_archive(record, args.tle_root, Path(temp) / "frozen-tle")
        trainer, checkpoint = _verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=args.users,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint digest differs from the frozen specification")
        rollouts = []
        for seed in args.seeds:
            environment = _make_environment(archive, users=args.users)
            env_rng, mobility_rng, action_rng, _perturb_rng = _evaluation_rngs(seed)
            rollouts.append(
                run_rollout(
                    trainer,
                    environment,
                    evaluation_seed=seed,
                    env_rng=env_rng,
                    mobility_rng=mobility_rng,
                    action_rng=action_rng,
                    focal_users_per_step=args.focal_users_per_step,
                )
            )

    rows = [row for rollout in rollouts for row in rollout["proposal_rows"]]
    confirmation = bool(
        tuple(args.seeds) == P6_EVALUATION_SEEDS
        and args.focal_users_per_step == 10
        and args.users == 100
    )
    payload = {
        "schema": "mcrl-catfish-local-oracle-gate-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "mode": "evaluation-only; no optimizer, replay, reward, or training update",
        "claim_boundary": (
            "Q1-only projection reference with discarded one-focal-user immediate "
            "counterfactuals; not a trained R1-only arm, composability test, or "
            "deployable oracle"
        ),
        "stage": "confirmation" if confirmation else "engineering_pilot",
        "spec_path": str(SPEC),
        "spec_sha256": SPEC_SHA256,
        "analysis_path": str(Path(__file__).resolve()),
        "analysis_sha256": _sha256(Path(__file__).resolve()),
        "prereg_path": str(args.prereg),
        "prereg_digest": record.digest,
        "prereg_file_sha256": _sha256(args.prereg),
        "frozen_tle_contract_verified": True,
        "checkpoint": checkpoint,
        "analysis_code_sha256": current_code_sha,
        "analysis_source_matches_training": (
            current_code_sha == checkpoint["launched_code_sha256"]
        ),
        "evaluation_seeds": list(args.seeds),
        "users": args.users,
        "focal_users_per_step": args.focal_users_per_step,
        "sampling": (
            "data-blind without-replacement draws from all user IDs before role "
            "eligibility; no replacement draws for ineligible users"
        ),
        "common_random_number_contract": (
            "all alternatives use evaluate_actions from the same pre-decision state "
            "and a clone of the same environment RNG; only the Q1 projection commits"
        ),
        "baseline_preview_equals_committed_step_every_time": True,
        "fractional_ee_identity_pass_every_time": True,
        "exactly_one_focal_physical_action_changed_every_time": True,
        "independent_unit": "evaluation seed; user-step rows are clustered",
        "family_summary": _family_summary(rows, confirmation=confirmation),
        "rollouts": rollouts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
