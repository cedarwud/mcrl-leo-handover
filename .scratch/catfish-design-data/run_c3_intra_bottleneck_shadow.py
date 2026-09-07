#!/usr/bin/env python3
"""Run the frozen exploratory C3 intra-satellite bottleneck census."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ORACLE_DIR = REPO / ".scratch" / "catfish-oracle-gate"
sys.path.insert(0, str(ORACLE_DIR))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import run_oracle_gate as v1  # noqa: E402
from mcrl.env.action_contract import Association, HandoverClass  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.link_budget import pa_efficiency, supply_power_w  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC = HERE / "C3-INTRA-BOTTLENECK-SHADOW-SPEC-2026-08-27.md"
SPEC_SHA256 = "570fd476c42733fc91b1691501c682e2f8dcc21209c627682886d2955d4461f3"
EXPECTED_CHECKPOINT_SHA256 = v1.EXPECTED_CHECKPOINT_SHA256
EVALUATION_SEED = 2026082701
USERS = 100
POWER_TOLERANCE_W = 1e-10
STRICT_MAX_TOLERANCE_W = 1e-12
DEFAULT_OUTPUT = HERE / "c3-intra-bottleneck-shadow-seed-2026082701-v1.json"


PhysicalKey = tuple[int, int]


def _json_key(key: PhysicalKey | None) -> list[int] | None:
    return None if key is None else [int(key[0]), int(key[1])]


def _served_key(evaluation: Any, uid: int) -> PhysicalKey | None:
    if not bool(evaluation.resolution.served[uid]):
        return None
    return (
        int(evaluation.resolution.serving_satellite[uid]),
        int(evaluation.resolution.serving_cell[uid]),
    )


def _users_on(evaluation: Any, key: PhysicalKey) -> list[int]:
    return [
        uid
        for uid in range(evaluation.resolution.served.shape[0])
        if _served_key(evaluation, uid) == key
    ]


def _physical_actions(table: Any) -> list[tuple[int, PhysicalKey]]:
    by_key: dict[PhysicalKey, int] = {}
    for action in np.flatnonzero(table.mask).tolist():
        association = table.association(action)
        if not isinstance(association, Association):
            raise RuntimeError("valid action did not map to an association")
        key = (int(association.norad_id), int(association.cell_id))
        by_key[key] = min(int(action), by_key.get(key, int(action)))
    return [(action, key) for key, action in sorted(by_key.items())]


def _supply(power_w: float, physics: Any) -> float:
    power = np.asarray([float(power_w)], dtype=np.float64)
    efficiency = pa_efficiency(
        power,
        max_efficiency=physics.pa_max_efficiency,
        saturation_power_w=physics.pa_saturation_power_w,
    )
    return float(supply_power_w(power, efficiency)[0])


def _source_qualification(
    *,
    environment: Any,
    observation: Any,
    baseline_actions: np.ndarray,
    baseline_keys: list[PhysicalKey | None],
    baseline: Any,
    focal_user: int,
) -> tuple[dict[str, Any], list[tuple[int, PhysicalKey]]]:
    source = baseline_keys[focal_user]
    base = {
        "focal_user": int(focal_user),
        "reference_action": int(baseline_actions[focal_user]),
        "reference_key": _json_key(source),
        "reference_handover": baseline.handovers[focal_user].value,
    }
    if source is None or not bool(baseline.resolution.served[focal_user]):
        return base | {"status": "source_ineligible", "reason": "reference_unserved"}, []

    previous = environment._previous_association[focal_user]
    segment = environment._segments[focal_user]
    continuing = bool(
        isinstance(previous, Association)
        and segment is not None
        and (previous.norad_id, previous.cell_id) == source
        and segment.continues(previous)
    )
    if not continuing or baseline.handovers[focal_user] is not HandoverClass.NONE:
        return base | {
            "status": "source_ineligible",
            "reason": "reference_not_continuing_incumbent",
        }, []

    source_users = _users_on(baseline, source)
    if len(source_users) < 2:
        return base | {"status": "source_ineligible", "reason": "source_load_lt_2"}, []
    other_source_users = [uid for uid in source_users if uid != focal_user]
    focal_power = float(baseline.link_power_w[focal_user])
    next_power = max(float(baseline.link_power_w[uid]) for uid in other_source_users)
    if not focal_power > next_power + STRICT_MAX_TOLERANCE_W:
        return base | {
            "status": "source_ineligible",
            "reason": "focal_not_strict_unique_source_max",
            "source_load": len(source_users),
            "focal_power_w": focal_power,
            "source_next_power_w": next_power,
        }, []

    active = {tuple(map(int, key)) for key in baseline.resolution.active_beams}
    table = observation.candidates.slot_tables[focal_user]
    candidates = [
        (action, key)
        for action, key in _physical_actions(table)
        if key != source and key[0] == source[0] and key in active
    ]
    if not candidates:
        return base | {
            "status": "source_qualified_no_destination",
            "reason": "no_active_same_satellite_destination",
            "source_load": len(source_users),
            "focal_power_w": focal_power,
            "source_next_power_w": next_power,
        }, []
    return base | {
        "status": "source_qualified",
        "reason": "candidate_scan_required",
        "source_load": len(source_users),
        "focal_power_w": focal_power,
        "source_next_power_w": next_power,
        "candidate_count_pre_certificate": len(candidates),
    }, candidates


def _certify_candidate(
    *,
    environment: Any,
    baseline_actions: np.ndarray,
    baseline_keys: list[PhysicalKey | None],
    baseline: Any,
    focal_user: int,
    candidate_action: int,
    candidate_key: PhysicalKey,
    source_row: dict[str, Any],
    rng: np.random.Generator,
) -> dict[str, Any]:
    source_key_raw = baseline_keys[focal_user]
    if source_key_raw is None:
        raise RuntimeError("certification received an unserved source")
    source_key = source_key_raw
    destination_users = _users_on(baseline, candidate_key)
    if not destination_users:
        raise RuntimeError("pre-filtered destination is not active")
    destination_max = max(
        float(baseline.link_power_w[uid]) for uid in destination_users
    )

    alternative_actions = baseline_actions.copy()
    alternative_actions[focal_user] = int(candidate_action)
    alternative = environment.evaluate_actions(alternative_actions, rng)

    invariant_failures: list[str] = []
    if not bool(alternative.resolution.served[focal_user]):
        invariant_failures.append("candidate_focal_unserved")
    if alternative.handovers[focal_user] is not HandoverClass.INTRA_SATELLITE:
        invariant_failures.append("candidate_not_intra_satellite")
    if not np.array_equal(
        alternative.resolution.served, baseline.resolution.served
    ):
        invariant_failures.append("served_vector_changed")
    base_active = {tuple(map(int, key)) for key in baseline.resolution.active_beams}
    alt_active = {tuple(map(int, key)) for key in alternative.resolution.active_beams}
    if alt_active != base_active:
        invariant_failures.append("active_beam_set_changed")
    if _served_key(alternative, focal_user) != candidate_key:
        invariant_failures.append("focal_not_served_on_candidate")

    nonfocal = np.ones(USERS, dtype=bool)
    nonfocal[focal_user] = False
    if not np.allclose(
        alternative.link_power_w[nonfocal],
        baseline.link_power_w[nonfocal],
        rtol=0.0,
        atol=0.0,
        equal_nan=True,
    ):
        invariant_failures.append("nonfocal_link_power_changed")

    candidate_power = float(alternative.link_power_w[focal_user])
    if candidate_power > destination_max + POWER_TOLERANCE_W:
        return {
            "status": "candidate_ineligible",
            "reason": "candidate_exceeds_destination_max",
            "candidate_action": int(candidate_action),
            "candidate_key": _json_key(candidate_key),
            "candidate_power_w": candidate_power,
            "destination_max_power_w": destination_max,
        }
    if invariant_failures:
        return {
            "status": "certificate_failure",
            "reason": "invariant_failure",
            "invariant_failures": invariant_failures,
            "candidate_action": int(candidate_action),
            "candidate_key": _json_key(candidate_key),
            "candidate_power_w": candidate_power,
            "destination_max_power_w": destination_max,
        }

    source_next = float(source_row["source_next_power_w"])
    source_max = float(source_row["focal_power_w"])
    predicted_delta = _supply(source_next, environment.physics) - _supply(
        source_max, environment.physics
    )
    realised_delta = float(alternative.system_power_w - baseline.system_power_w)
    residual = realised_delta - predicted_delta
    certificate_pass = bool(
        predicted_delta < 0.0
        and realised_delta < 0.0
        and abs(residual) <= POWER_TOLERANCE_W
    )
    if not certificate_pass:
        return {
            "status": "certificate_failure",
            "reason": "power_identity_failure",
            "candidate_action": int(candidate_action),
            "candidate_key": _json_key(candidate_key),
            "predicted_delta_system_power_w": predicted_delta,
            "realised_delta_system_power_w": realised_delta,
            "identity_residual_w": residual,
        }

    ee = v1.ee_certificate(
        baseline_throughput_bps=float(baseline.energy.system_throughput_bps),
        baseline_power_w=float(baseline.system_power_w),
        alternative_throughput_bps=float(alternative.energy.system_throughput_bps),
        alternative_power_w=float(alternative.system_power_w),
    )
    return {
        "status": "certified",
        "reason": "all_pre_outcome_physics_invariants_pass",
        "candidate_action": int(candidate_action),
        "candidate_key": _json_key(candidate_key),
        "source_key": _json_key(source_key),
        "source_load_reference": len(_users_on(baseline, source_key)),
        "destination_load_reference": len(destination_users),
        "source_max_power_w": source_max,
        "source_next_power_w": source_next,
        "candidate_power_w": candidate_power,
        "destination_max_power_w": destination_max,
        "reference_handover": baseline.handovers[focal_user].value,
        "candidate_handover": alternative.handovers[focal_user].value,
        "predicted_delta_system_power_w": predicted_delta,
        "realised_delta_system_power_w": realised_delta,
        "identity_residual_w": residual,
        "reference_system_power_w": float(baseline.system_power_w),
        "candidate_system_power_w": float(alternative.system_power_w),
        "delta_throughput_bps": float(
            alternative.energy.system_throughput_bps
            - baseline.energy.system_throughput_bps
        ),
        "delta_ee_bits_per_j": float(ee["delta_ee_bits_per_j"]),
        "ee_identity_residual_bits_per_j": float(
            ee["identity_residual_bits_per_j"]
        ),
        "eligibility_reads_rate_reward_ee_or_successor": False,
        "post_retention_outcomes_are_descriptive_only": True,
    }


def run_rollout(trainer: Any, wrapped: Any, *, seed: int) -> dict[str, Any]:
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    states, wrapped_masks, observation = wrapped.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    source_rows: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    baseline_steps: list[dict[str, Any]] = []

    while True:
        masks = np.stack([row.mask for row in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = v1.masked_greedy_actions(q1, masks)
        baseline_keys = v1.physical_action_keys(
            baseline_actions, observation.candidates.slot_tables
        )
        environment = wrapped.environment
        baseline = environment.evaluate_actions(baseline_actions, env_rng)
        step_index = int(observation.step_index)
        baseline_steps.append(
            {
                "step_index": step_index,
                "served": int(baseline.resolution.served_count),
                "active_beams": len(baseline.resolution.active_beams),
                "system_power_w": float(baseline.system_power_w),
                "system_throughput_bps": float(
                    baseline.energy.system_throughput_bps
                ),
                "system_ee_bits_per_j": float(baseline.energy.system_ee_bits_per_j),
            }
        )

        for focal_user in range(USERS):
            source_row, scan = _source_qualification(
                environment=environment,
                observation=observation,
                baseline_actions=baseline_actions,
                baseline_keys=baseline_keys,
                baseline=baseline,
                focal_user=focal_user,
            )
            source_row["evaluation_seed"] = int(seed)
            source_row["step_index"] = step_index
            source_rows.append(source_row)
            for action, key in scan:
                row = _certify_candidate(
                    environment=environment,
                    baseline_actions=baseline_actions,
                    baseline_keys=baseline_keys,
                    baseline=baseline,
                    focal_user=focal_user,
                    candidate_action=action,
                    candidate_key=key,
                    source_row=source_row,
                    rng=env_rng,
                )
                row.update(
                    {
                        "evaluation_seed": int(seed),
                        "step_index": step_index,
                        "focal_user": int(focal_user),
                        "reference_action": int(baseline_actions[focal_user]),
                        "reference_key": source_row["reference_key"],
                    }
                )
                candidates.append(row)

        result = wrapped.step(baseline_actions, env_rng)
        v1._assert_full_preview_parity(baseline, wrapped.last_outcome)
        if result.done:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = wrapped.last_outcome.observation
        encoded = trainer.encode_states(states)

    return {
        "baseline_steps": baseline_steps,
        "source_rows": source_rows,
        "candidate_rows": candidates,
        "encoded_state_shape_last": list(encoded.shape),
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
        raise RuntimeError("frozen C3 shadow specification digest changed")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")

    record = read_prereg(args.prereg)
    current_code_sha = _code_sha256(_default_code_paths())
    with tempfile.TemporaryDirectory(prefix="mcrl-c3-intra-shadow-") as temp:
        archive = v1._frozen_archive(record, args.tle_root, Path(temp) / "frozen-tle")
        trainer, checkpoint = v1._verify_and_load_trainer(
            record, archive, run_dir=args.input_dir / "main", users=USERS
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint digest differs from frozen shadow input")
        wrapped = v1._make_environment(archive, users=USERS)
        rollout = run_rollout(trainer, wrapped, seed=EVALUATION_SEED)

    source_rows = rollout["source_rows"]
    candidate_rows = rollout["candidate_rows"]
    certified = [row for row in candidate_rows if row["status"] == "certified"]
    failures = [
        row for row in candidate_rows if row["status"] == "certificate_failure"
    ]
    source_qualified = [
        row for row in source_rows if row["status"] == "source_qualified"
    ]
    if failures:
        classification = "CERTIFICATE_FAILURE"
    elif certified:
        classification = "SUPPORT_PRESENT_SHADOW_ONLY"
    else:
        classification = "ZERO_SUPPORT"

    payload = {
        "schema": "mcrl-c3-intra-bottleneck-shadow-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "mode": "evaluation-only legacy-narrow sensitivity; no training or coordination",
        "claim_boundary": (
            "support and exact immediate power identity only; no learnability, "
            "held-out EE, causal Catfish, or Multi-Catfish claim"
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
        "evaluation_seed": EVALUATION_SEED,
        "users": USERS,
        "steps": len(rollout["baseline_steps"]),
        "census_user_steps": len(source_rows),
        "source_qualified_rows": len(source_qualified),
        "candidate_rows_scanned": len(candidate_rows),
        "certified_candidates": len(certified),
        "certificate_failures": len(failures),
        "classification": classification,
        "certificate_input_visibility": {
            "main_state_dimension": int(rollout["encoded_state_shape_last"][-1]),
            "main_state_contains_segment_start_gain": False,
            "main_state_contains_current_exact_link_or_beam_power": False,
            "exact_training_only_mask_required": True,
            "main_transfer_requires_separate_representability_gate": True,
        },
        "baseline_preview_equals_committed_step_every_time": True,
        "rollout": rollout,
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
