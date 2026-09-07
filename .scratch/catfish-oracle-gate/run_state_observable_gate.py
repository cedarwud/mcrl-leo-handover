#!/usr/bin/env python3
"""Run the frozen focal-state-only R2/R3 Catfish opportunity gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import run_oracle_gate as v1  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402


SPEC = HERE / "SPEC-v2-STATE-ONLY.md"
SPEC_SHA256 = "9a0a70dac4f8f892a29a5162692b0464406899d7deb6b8ea6327a17ac369a760"
EXPECTED_CHECKPOINT_SHA256 = v1.EXPECTED_CHECKPOINT_SHA256
DEFAULT_OUTPUT = HERE / "state-only-pilot-seed-2026082401-k2-v2.json"
FAMILIES = (
    "r2_access_exact_stay",
    "r3_prev_inactive_split",
    "r3_prev_active_lower_load",
)
R2_FAMILY = FAMILIES[0]


PhysicalKey = v1.PhysicalKey
CandidateChoice = v1.CandidateChoice


@dataclass(frozen=True)
class StateProposal:
    family: str
    choice: CandidateChoice | None
    reason: str
    reference_prior_demand: float | None
    visible_incumbent_action: int | None
    selection_candidates: tuple[tuple[int, PhysicalKey, float, float], ...]


def _key_for_action(table: Any, action: int) -> PhysicalKey | None:
    association = table.association(action)
    if isinstance(association, Association):
        return (association.norad_id, association.cell_id)
    return None


def state_only_proposal(
    family: str,
    *,
    baseline_action: int,
    baseline_key: PhysicalKey | None,
    candidates: Sequence[CandidateChoice],
    access_vector: np.ndarray,
) -> StateProposal:
    """Build one proposal without another user's state/action or an outcome."""
    if family not in FAMILIES:
        raise ValueError(f"unknown state-only family: {family}")
    access = np.asarray(access_vector, dtype=np.float64)
    visible = np.flatnonzero(access > 0.5)
    if visible.size > 1:
        raise RuntimeError("access_vector contains more than one incumbent action")
    visible_action = int(visible[0]) if visible.size else None
    by_action = {candidate.action: candidate for candidate in candidates}
    by_key = {candidate.key: candidate for candidate in candidates}
    baseline = by_key.get(baseline_key) if baseline_key is not None else None
    baseline_load = baseline.prior_demand if baseline is not None else None
    selection_candidates = tuple(
        (
            candidate.action,
            candidate.key,
            candidate.prior_demand,
            candidate.candidate_sinr,
        )
        for candidate in sorted(candidates, key=lambda row: row.action)
    )

    def proposal(
        choice: CandidateChoice | None,
        reason: str,
        *,
        visible_incumbent_action: int | None = visible_action,
    ) -> StateProposal:
        return StateProposal(
            family=family,
            choice=choice,
            reason=reason,
            reference_prior_demand=baseline_load,
            visible_incumbent_action=visible_incumbent_action,
            selection_candidates=selection_candidates,
        )

    if family == R2_FAMILY:
        if visible_action is None:
            return proposal(
                None, "incumbent_not_visible", visible_incumbent_action=None
            )
        incumbent = by_action.get(visible_action)
        if incumbent is None:
            raise RuntimeError("visible incumbent action is not a valid physical candidate")
        if incumbent.key == baseline_key:
            return proposal(None, "reference_already_exact_stay")
        return proposal(incumbent, "eligible")

    alternatives = [candidate for candidate in candidates if candidate.key != baseline_key]
    if family == "r3_prev_inactive_split":
        matches = [candidate for candidate in alternatives if candidate.prior_demand == 0.0]
        if not matches:
            return proposal(None, "no_previous_inactive_candidate")
        selected = min(matches, key=lambda row: (-row.candidate_sinr, row.action))
        return proposal(selected, "eligible")

    if baseline_load is None:
        return proposal(None, "reference_has_no_physical_candidate")
    matches = [
        candidate
        for candidate in alternatives
        if 0.0 < candidate.prior_demand < baseline_load
    ]
    if not matches:
        return proposal(None, "no_previous_active_lower_load_candidate")
    selected = min(
        matches,
        key=lambda row: (row.prior_demand, -row.candidate_sinr, row.action),
    )
    return proposal(selected, "eligible")


def _selection_candidate_fields(proposal: StateProposal) -> list[dict[str, Any]]:
    """Return every focal observation needed to replay canonical selection."""
    return [
        {
            "action": action,
            "key": v1._json_key(key),
            "prior_demand": prior_demand,
            "candidate_sinr": candidate_sinr,
        }
        for action, key, prior_demand, candidate_sinr in proposal.selection_candidates
    ]


def r3_role_labels(family: str, row: dict[str, Any]) -> dict[str, bool]:
    """Apply the frozen R3 topology and load endpoints to an evaluated row."""
    if family not in FAMILIES[1:]:
        raise ValueError(f"not an R3 state-only family: {family}")
    added = len(row["realised_active_beams_added"])
    effective_delta = int(row["alternative_effective_beams"]) - int(
        row["reference_effective_beams"]
    )
    if family == "r3_prev_inactive_split":
        topology_positive = bool(
            row["realised_proposed_beam_opening"]
            and added == 1
            and effective_delta == 1
        )
    else:
        topology_positive = added == 0
    load_positive = float(row["delta_load_relief"]) > 0.0
    return {
        "load_endpoint_positive": load_positive,
        "topology_endpoint_positive": topology_positive,
        "role_positive": bool(topology_positive and load_positive),
    }


def _ineligible_row(
    *,
    seed: int,
    step: int,
    focal_user: int,
    proposal: StateProposal,
    baseline_action: int,
    baseline_key: PhysicalKey | None,
) -> dict[str, Any]:
    return {
        "evaluation_seed": seed,
        "step_index": step,
        "focal_user": focal_user,
        "family": proposal.family,
        "status": "ineligible",
        "reason": proposal.reason,
        "reference_action": baseline_action,
        "reference_key": v1._json_key(baseline_key),
        "reference_prior_demand": proposal.reference_prior_demand,
        "visible_incumbent_action": proposal.visible_incumbent_action,
        "proposal_action": None,
        "proposal_key": None,
        "proposal_input_scope": "focal_user_live_observation_only",
        "selection_candidates": _selection_candidate_fields(proposal),
    }


def _absolute_fields(
    baseline: Any, alternative: Any, focal_user: int
) -> dict[str, float | int]:
    reference_other = float(baseline.link_rate_bps.sum() - baseline.link_rate_bps[focal_user])
    alternative_other = float(
        alternative.link_rate_bps.sum() - alternative.link_rate_bps[focal_user]
    )
    return {
        "reference_focal_rate_bps": float(baseline.link_rate_bps[focal_user]),
        "alternative_focal_rate_bps": float(alternative.link_rate_bps[focal_user]),
        "reference_other_users_rate_bps": reference_other,
        "alternative_other_users_rate_bps": alternative_other,
        "reference_system_throughput_bps": float(
            baseline.energy.system_throughput_bps
        ),
        "alternative_system_throughput_bps": float(
            alternative.energy.system_throughput_bps
        ),
        "reference_system_power_w": float(baseline.energy.system_consumed_power_w),
        "alternative_system_power_w": float(
            alternative.energy.system_consumed_power_w
        ),
        "reference_system_ee_bits_per_j": float(baseline.energy.system_ee_bits_per_j),
        "alternative_system_ee_bits_per_j": float(
            alternative.energy.system_ee_bits_per_j
        ),
    }


def _evaluated_row(
    *,
    seed: int,
    step: int,
    focal_user: int,
    proposal: StateProposal,
    previous: object,
    baseline_action: int,
    baseline_key: PhysicalKey | None,
    baseline_intent: set[PhysicalKey],
    other_user_intent: set[PhysicalKey],
    baseline: Any,
    alternative: Any,
    q1_reference: float | None,
) -> dict[str, Any]:
    if proposal.choice is None:
        raise ValueError("cannot evaluate an empty state proposal")
    proxy_family = "r2_exact_stay" if proposal.family == R2_FAMILY else proposal.family
    proxy = v1.Proposal(proxy_family, proposal.choice, proposal.reason)
    row = v1._evaluated_row(
        seed=seed,
        step=step,
        focal_user=focal_user,
        proposal=proxy,
        previous=previous,
        baseline_action=baseline_action,
        baseline_key=baseline_key,
        baseline_intent=baseline_intent,
        other_user_intent=other_user_intent,
        baseline=baseline,
        alternative=alternative,
        q1_reference=q1_reference,
    )
    row["family"] = proposal.family
    row["proposal_input_scope"] = "focal_user_live_observation_only"
    row["reference_prior_demand"] = proposal.reference_prior_demand
    row["visible_incumbent_action"] = proposal.visible_incumbent_action
    row["selection_candidates"] = _selection_candidate_fields(proposal)
    row.update(_absolute_fields(baseline, alternative, focal_user))

    if proposal.family != R2_FAMILY:
        labels = r3_role_labels(proposal.family, row)
        row.update(labels)
        row["jointly_positive"] = bool(
            labels["role_positive"] and row["ee_positive"] and row["service_safe"]
        )
    else:
        row["load_endpoint_positive"] = None
        row["topology_endpoint_positive"] = None
    return row


def _summaries(
    rows: Sequence[dict[str, Any]], *, confirmation: bool
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for family in FAMILIES:
        sampled = [row for row in rows if row["family"] == family]
        eligible = [row for row in sampled if row["status"] == "evaluated"]
        by_seed: dict[str, Any] = {}
        for seed in sorted({int(row["evaluation_seed"]) for row in sampled}):
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
        fraction = float(joint / len(eligible)) if eligible else 0.0
        seed_coverage = sum(
            int(seed_row["jointly_positive"]) > 0 for seed_row in by_seed.values()
        )
        passed = bool(
            confirmation
            and len(eligible) >= 30
            and seed_coverage >= 8
            and fraction >= 0.10
        )
        borderline = bool(
            confirmation and not passed and 0.09 <= fraction < 0.10
        )
        if not confirmation:
            decision = "PILOT_ONLY_NO_ROLE_DECISION"
        elif passed and family == R2_FAMILY:
            decision = "ADVANCE_TO_PHYSICAL_HANDOVER_PARAMETER_GATE_ONLY"
        elif passed:
            decision = "ADVANCE_TO_HELD_OUT_STATE_LEARNABILITY_TEST_ONLY"
        else:
            decision = "DROP_OR_REDESIGN_BEFORE_TRAINING"
        output[family] = {
            "sampled_rows": len(sampled),
            "eligible": len(eligible),
            "ineligible": len(sampled) - len(eligible),
            "role_positive": sum(bool(row["role_positive"]) for row in eligible),
            "ee_positive": sum(bool(row["ee_positive"]) for row in eligible),
            "jointly_positive": joint,
            "jointly_positive_fraction_of_eligible": fraction,
            "seeds_with_jointly_positive": seed_coverage,
            "by_seed": by_seed,
            "threshold_pass": passed,
            "borderline_within_one_percentage_point": borderline,
            "decision": decision,
        }
    return output


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
    states, wrapped_masks, observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    rows: list[dict[str, Any]] = []
    baseline_steps: list[dict[str, Any]] = []

    while True:
        masks = np.stack([wrapped.mask for wrapped in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = v1.masked_greedy_actions(q1, masks)
        focal_users = [
            int(uid)
            for uid in action_rng.choice(
                environment.num_users, size=focal_users_per_step, replace=False
            ).tolist()
        ]
        prebuilt: list[tuple[int, PhysicalKey | None, StateProposal]] = []
        for focal_user in focal_users:
            table = observation.candidates.slot_tables[focal_user]
            baseline_action = int(baseline_actions[focal_user])
            baseline_key = _key_for_action(table, baseline_action)
            candidates = v1._physical_candidates(
                table,
                prior_demand=observation.user_states[focal_user].beam_loads,
                candidate_sinr=observation.candidate_sinr[focal_user],
                q1=q1[focal_user],
            )
            for family in FAMILIES:
                prebuilt.append(
                    (
                        focal_user,
                        baseline_key,
                        state_only_proposal(
                            family,
                            baseline_action=baseline_action,
                            baseline_key=baseline_key,
                            candidates=candidates,
                            access_vector=observation.user_states[
                                focal_user
                            ].access_vector,
                        ),
                    )
                )

        # Other users' physical intents and all current-slot outcomes are
        # deliberately unavailable until every focal proposal is frozen.
        baseline_keys = v1.physical_action_keys(
            baseline_actions, observation.candidates.slot_tables
        )
        baseline_intent = {key for key in baseline_keys if key is not None}
        step_environment = environment.environment
        baseline = step_environment.evaluate_actions(baseline_actions, env_rng)
        baseline_snapshot = v1._evaluation_snapshot(
            baseline,
            num_users=environment.num_users,
            beam_bandwidth_hz=step_environment.physics.beam_bandwidth_hz,
        )

        for focal_user, baseline_key, proposal in prebuilt:
            baseline_action = int(baseline_actions[focal_user])
            if proposal.choice is None:
                rows.append(
                    _ineligible_row(
                        seed=evaluation_seed,
                        step=int(observation.step_index),
                        focal_user=focal_user,
                        proposal=proposal,
                        baseline_action=baseline_action,
                        baseline_key=baseline_key,
                    )
                )
                continue
            alternative_actions = baseline_actions.copy()
            alternative_actions[focal_user] = proposal.choice.action
            alternative_keys = v1.physical_action_keys(
                alternative_actions, observation.candidates.slot_tables
            )
            changed = [
                uid
                for uid, (reference, alternative) in enumerate(
                    zip(baseline_keys, alternative_keys, strict=True)
                )
                if reference != alternative
            ]
            if changed != [focal_user]:
                raise RuntimeError(
                    f"state proposal changed physical users {changed}, expected {[focal_user]}"
                )
            alternative = step_environment.evaluate_actions(alternative_actions, env_rng)
            other_user_intent = {
                key
                for uid, key in enumerate(baseline_keys)
                if uid != focal_user and key is not None
            }
            previous = step_environment._ledgers[focal_user].previous
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
        v1._assert_full_preview_parity(baseline, outcome)
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
    parser.add_argument("--input-dir", type=Path, default=v1.DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=v1.DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
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
    if v1._sha256(SPEC) != SPEC_SHA256:
        raise RuntimeError("frozen state-only specification digest changed")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if args.users < 1 or not 1 <= args.focal_users_per_step <= args.users:
        raise ValueError("invalid users/focal-users-per-step")
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("seeds must be unique")
    if any(seed not in P6_EVALUATION_SEEDS for seed in args.seeds):
        raise ValueError("every seed must belong to the frozen evaluation set")

    record = read_prereg(args.prereg)
    current_code_sha = _code_sha256(_default_code_paths())
    with tempfile.TemporaryDirectory(prefix="mcrl-catfish-state-only-") as temp:
        archive = v1._frozen_archive(record, args.tle_root, Path(temp) / "frozen-tle")
        trainer, checkpoint = v1._verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=args.users,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint digest differs from the frozen specification")
        rollouts = []
        for seed in args.seeds:
            environment = v1._make_environment(archive, users=args.users)
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
        "schema": "mcrl-catfish-state-observable-gate-v2",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "stage": "confirmation" if confirmation else "engineering_pilot",
        "mode": "evaluation-only; focal-state proposal generation; no training",
        "claim_boundary": (
            "one-focal-user immediate opportunity screen; no other-user current "
            "state/action enters proposal generation; not learnability or composition"
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
        "evaluation_seeds": list(args.seeds),
        "users": args.users,
        "focal_users_per_step": args.focal_users_per_step,
        "independent_unit": "evaluation seed; user-step rows are clustered",
        "sampling": (
            "data-blind without-replacement draws from all user IDs before role "
            "eligibility; no replacement draws for ineligible users"
        ),
        "common_random_number_contract": (
            "all alternatives use evaluate_actions from the same pre-decision state "
            "and a clone of the same environment RNG; only the Q1 projection commits"
        ),
        "proposal_input_scope": "focal_user_live_observation_only",
        "same_satellite_r2_status": (
            "excluded: current all-zero access vector cannot identify incumbent "
            "satellite; requires explicit state-extension decision"
        ),
        "baseline_preview_equals_committed_step_every_time": True,
        "fractional_ee_identity_pass_every_time": True,
        "exactly_one_focal_physical_action_changed_every_time": True,
        "family_summary": _summaries(rows, confirmation=confirmation),
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
