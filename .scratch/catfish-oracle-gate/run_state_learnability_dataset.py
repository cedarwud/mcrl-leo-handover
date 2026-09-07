#!/usr/bin/env python3
"""Collect frozen focal-state/action rows for the R3 separability gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import run_oracle_gate as v1  # noqa: E402
import run_state_observable_gate as v2  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC = HERE / "SPEC-v3-HELDOUT-STATE-LEARNABILITY.md"
SPEC_SHA256 = "8c2ac86ea93e6e4b2f433afdf8643d286aaaa909af15c01c31a4ef281663f7fd"
AMENDMENT = HERE / "SPEC-v3.1-INDEPENDENT-AUDIT-AMENDMENT.md"
AMENDMENT_SHA256 = "e31227e740f8663b3f55bc534827642a34c2e3920c90b2cf39af52a500f14d8e"
SOURCE_V2_SHA256 = "cd88d8c5b17d163a957d8c2e56c2995080c4bb1636cbcc93fae13b234ba50658"
EXPECTED_CHECKPOINT_SHA256 = v1.EXPECTED_CHECKPOINT_SHA256
DEVELOPMENT_SEEDS = tuple(range(2026082401, 2026082411))
HELDOUT_SEEDS = tuple(range(2026082501, 2026082511))
R3_FAMILY = "r3_prev_inactive_split"
STATE_DIM = 112


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--partition", choices=("pilot", "development", "heldout"), required=True
    )
    parser.add_argument("--input-dir", type=Path, default=v1.DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=v1.DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument(
        "--source-v2-receipt",
        type=Path,
        default=HERE / "state-only-confirmation-seeds-10-k10-v2.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _state_fields(encoded_state: np.ndarray, mask: np.ndarray) -> dict[str, Any]:
    encoded = np.asarray(encoded_state, dtype=np.float32)
    valid = np.asarray(mask, dtype=bool)
    if encoded.shape != (STATE_DIM,) or not np.all(np.isfinite(encoded)):
        raise RuntimeError("focal encoded state is not finite shape (112,)")
    if valid.shape != (28,):
        raise RuntimeError("focal action mask is not shape (28,)")
    return {
        "focal_encoded_state": [float(value) for value in encoded.tolist()],
        "focal_action_mask": [bool(value) for value in valid.tolist()],
        "state_input_scope": "exact_live_q_head_input_only",
    }


def _apply_strict_split_labels(row: dict[str, Any]) -> None:
    """Apply v3.1's explicit net-+1 topology contract in place."""
    added = len(row["realised_active_beams_added"])
    removed = len(row["realised_active_beams_removed"])
    effective_delta = int(row["alternative_effective_beams"]) - int(
        row["reference_effective_beams"]
    )
    topology_positive = bool(
        row["realised_proposed_beam_opening"]
        and added == 1
        and removed == 0
        and effective_delta == 1
    )
    load_positive = float(row["delta_load_relief"]) > 0.0
    role_positive = bool(topology_positive and load_positive)
    row.update(
        {
            "topology_contract": "strict_net_plus_one_added_1_removed_0",
            "topology_endpoint_positive": topology_positive,
            "load_endpoint_positive": load_positive,
            "role_positive": role_positive,
            "jointly_positive": bool(
                role_positive and row["ee_positive"] and row["service_safe"]
            ),
        }
    )


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
        prebuilt: list[
            tuple[
                int,
                v1.PhysicalKey | None,
                v2.StateProposal,
                np.ndarray,
                np.ndarray,
            ]
        ] = []
        for focal_user in focal_users:
            table = observation.candidates.slot_tables[focal_user]
            baseline_action = int(baseline_actions[focal_user])
            baseline_key = v2._key_for_action(table, baseline_action)
            candidates = v1._physical_candidates(
                table,
                prior_demand=observation.user_states[focal_user].beam_loads,
                candidate_sinr=observation.candidate_sinr[focal_user],
                q1=q1[focal_user],
            )
            proposal = v2.state_only_proposal(
                R3_FAMILY,
                baseline_action=baseline_action,
                baseline_key=baseline_key,
                candidates=candidates,
                access_vector=observation.user_states[focal_user].access_vector,
            )
            prebuilt.append(
                (
                    focal_user,
                    baseline_key,
                    proposal,
                    np.asarray(encoded[focal_user]).copy(),
                    masks[focal_user].copy(),
                )
            )

        # All focal proposals and classifier inputs are frozen before any
        # other-user intent diagnostic or current-slot outcome is computed.
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

        for focal_user, baseline_key, proposal, state_row, mask_row in prebuilt:
            baseline_action = int(baseline_actions[focal_user])
            state_fields = _state_fields(state_row, mask_row)
            if proposal.choice is None:
                row = v2._ineligible_row(
                    seed=evaluation_seed,
                    step=int(observation.step_index),
                    focal_user=focal_user,
                    proposal=proposal,
                    baseline_action=baseline_action,
                    baseline_key=baseline_key,
                )
                row.update(state_fields)
                rows.append(row)
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
                    f"learnability proposal changed physical users {changed}"
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
            row = v2._evaluated_row(
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
            _apply_strict_split_labels(row)
            row.update(state_fields)
            rows.append(row)

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


def _strip_state_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key
        not in {
            "focal_encoded_state",
            "focal_action_mask",
            "state_input_scope",
            "topology_contract",
        }
    }


def _assert_development_parity(
    rollouts: Sequence[dict[str, Any]], source_path: Path
) -> dict[str, Any]:
    if v1._sha256(source_path) != SOURCE_V2_SHA256:
        raise RuntimeError("source v2 receipt digest changed")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_rollouts = source["rollouts"]
    if [row["evaluation_seed"] for row in rollouts] != [
        row["evaluation_seed"] for row in source_rollouts
    ]:
        raise RuntimeError("development rollout seeds differ from source v2")
    compared = 0
    for observed, expected in zip(rollouts, source_rollouts, strict=True):
        if observed["baseline_steps"] != expected["baseline_steps"]:
            raise RuntimeError("development baseline steps differ from source v2")
        expected_rows = [
            row for row in expected["proposal_rows"] if row["family"] == R3_FAMILY
        ]
        if len(observed["proposal_rows"]) != len(expected_rows):
            raise RuntimeError("development row count differs from source v2")
        for observed_row, expected_row in zip(
            observed["proposal_rows"], expected_rows, strict=True
        ):
            if _strip_state_fields(observed_row) != expected_row:
                raise RuntimeError("development physics row differs from source v2")
            compared += 1
    return {
        "source_receipt": str(source_path),
        "source_receipt_sha256": SOURCE_V2_SHA256,
        "rows_exactly_reproduced": compared,
        "status": "exact",
    }


def _label_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [row for row in rows if row["status"] == "evaluated"]
    by_seed: dict[str, Any] = {}
    for seed in sorted({int(row["evaluation_seed"]) for row in rows}):
        seed_rows = [
            row for row in evaluated if int(row["evaluation_seed"]) == seed
        ]
        by_seed[str(seed)] = {
            "eligible": len(seed_rows),
            "role_positive": sum(bool(row["role_positive"]) for row in seed_rows),
            "ee_positive": sum(bool(row["ee_positive"]) for row in seed_rows),
            "jointly_positive": sum(
                bool(row["jointly_positive"]) for row in seed_rows
            ),
            "service_unsafe": sum(not bool(row["service_safe"]) for row in seed_rows),
        }
    return {
        "sampled": len(rows),
        "eligible": len(evaluated),
        "ineligible": len(rows) - len(evaluated),
        "role_positive": sum(bool(row["role_positive"]) for row in evaluated),
        "ee_positive": sum(bool(row["ee_positive"]) for row in evaluated),
        "jointly_positive": sum(bool(row["jointly_positive"]) for row in evaluated),
        "service_unsafe": sum(not bool(row["service_safe"]) for row in evaluated),
        "by_seed": by_seed,
    }


def main() -> int:
    args = _arguments()
    if v1._sha256(SPEC) != SPEC_SHA256:
        raise RuntimeError("frozen v3 learnability specification digest changed")
    if v1._sha256(AMENDMENT) != AMENDMENT_SHA256:
        raise RuntimeError("frozen v3.1 audit amendment digest changed")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if args.partition == "pilot":
        seeds = (DEVELOPMENT_SEEDS[0],)
        focal_users_per_step = 2
    elif args.partition == "development":
        seeds = DEVELOPMENT_SEEDS
        focal_users_per_step = 10
    else:
        seeds = HELDOUT_SEEDS
        focal_users_per_step = 10

    record = read_prereg(args.prereg)
    current_code_sha = _code_sha256(_default_code_paths())
    with tempfile.TemporaryDirectory(prefix="mcrl-catfish-learnability-") as temp:
        archive = v1._frozen_archive(record, args.tle_root, Path(temp) / "frozen-tle")
        trainer, checkpoint = v1._verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=100,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint digest differs from frozen v3 spec")
        rollouts = []
        for seed in seeds:
            environment = v1._make_environment(archive, users=100)
            env_rng, mobility_rng, action_rng, _perturb_rng = _evaluation_rngs(seed)
            rollouts.append(
                run_rollout(
                    trainer,
                    environment,
                    evaluation_seed=seed,
                    env_rng=env_rng,
                    mobility_rng=mobility_rng,
                    action_rng=action_rng,
                    focal_users_per_step=focal_users_per_step,
                )
            )

    development_parity = None
    if args.partition == "development":
        development_parity = _assert_development_parity(
            rollouts, args.source_v2_receipt
        )
    rows = [row for rollout in rollouts for row in rollout["proposal_rows"]]
    payload = {
        "schema": "mcrl-catfish-r3-state-learnability-dataset-v3",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "partition": args.partition,
        "mode": "evaluation-only dataset collection; no fitting and no RL training",
        "claim_boundary": (
            "state/action supervised separability input only; not a deployment gate, "
            "Q-learning result, composition result, or long-horizon result"
        ),
        "spec_path": str(SPEC),
        "spec_sha256": SPEC_SHA256,
        "amendment_path": str(AMENDMENT),
        "amendment_sha256": AMENDMENT_SHA256,
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
        "focal_users_per_step": focal_users_per_step,
        "users": 100,
        "steps_per_seed": 10,
        "state_dim": STATE_DIM,
        "model_input_contract": (
            "focal_encoded_state only; proposal_action indexes the Q-shaped output; "
            "Q1 and outcome fields forbidden to the fitter"
        ),
        "sampling": (
            "data-blind without-replacement focal draws before eligibility; no "
            "replacement for ineligible rows"
        ),
        "common_random_number_contract": (
            "reference and alternatives use neutral evaluate_actions from the same "
            "pre-decision state and RNG; only Q1 reference commits"
        ),
        "development_source_parity": development_parity,
        "baseline_preview_equals_committed_step_every_time": True,
        "fractional_ee_identity_pass_every_time": True,
        "exactly_one_focal_physical_action_changed_every_time": True,
        "label_summary": _label_summary(rows),
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
