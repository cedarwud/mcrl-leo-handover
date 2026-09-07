#!/usr/bin/env python3
"""No-training C3 pilot for the V0.2 fixed-lambda EE-axis design.

The first pass freezes one Q1-reference ratio-of-sums multiplier.  The second
pass evaluates unilateral focal actions with copied RNG and decomposes their
immediate system surplus into isolated-direct ``z1`` and shared-system ``z3``.
Nothing updates replay, an optimizer, a checkpoint, or environment policy.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LEGACY = REPO / ".scratch" / "catfish-oracle-gate"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(LEGACY))

from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.step import ActionEvaluation  # noqa: E402
from mcrl.runtime.ee_surplus_targets import ee_surplus_axis_targets  # noqa: E402
from mcrl.runtime.head_pivotality import (  # noqa: E402
    masked_greedy_actions,
    physical_action_keys,
)
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS  # noqa: E402
from mcrl.runtime.training_pipeline import _evaluation_rngs  # noqa: E402
from run_oracle_gate import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_PREREG,
    EXPECTED_CHECKPOINT_SHA256,
    _active_keys,
    _frozen_archive,
    _load_stats,
    _make_environment,
    _physical_candidates,
    _sha256,
    _verify_and_load_trainer,
)


DEFAULT_OUTPUT = HERE / "c3-unilateral-oracle-pilot-v02.json"


def _isolated_evaluation(
    environment: Any,
    *,
    focal_user: int,
    action: int,
    rng: np.random.Generator,
) -> ActionEvaluation:
    """Evaluate only one focal association through the canonical physics.

    Non-focal users are structurally absent in this training-only isolated
    world.  This intentionally bypasses the live rule that a user with a
    non-empty mask must choose an action, while preserving the environment's
    single load semantics and all link/power/EE calculations.
    """

    step_environment = environment.environment
    decision = step_environment._candidates
    if decision is None:
        raise RuntimeError("isolated evaluation requires a current candidate table")
    selected = np.full(environment.num_users, NO_OP_ACTION, dtype=np.int64)
    if action != NO_OP_ACTION:
        # Validate the focal mapping without invoking the live all-user action
        # contract, which intentionally rejects structural non-focal no-ops.
        decision.slot_tables[focal_user].association(action)
        selected[focal_user] = int(action)

    local_rng = copy.deepcopy(rng)
    segments = step_environment._segments.copy()
    try:
        physics = step_environment._resolve_physics(decision, selected, local_rng)
    finally:
        step_environment._segments = segments
    rewards, handovers = step_environment._rewards(
        decision, selected, physics, commit=False
    )
    return ActionEvaluation(
        rewards=rewards,
        resolution=physics["resolution"],
        energy=physics["energy"],
        interference=physics["interference"],
        radiating=physics["radiating"],
        link_power_w=physics["link_power_w"],
        link_sinr=physics["sinr"],
        link_rate_bps=physics["rate"],
        handovers=handovers,
        system_power_w=float(physics["system_power_w"]),
        fixed_power_w=float(physics["fixed_power_w"]),
        diagnostics=step_environment._diagnostics(physics),
    )


def _freeze_lambda(
    trainer: Any,
    environment: Any,
    *,
    seed: int,
) -> dict[str, float | int]:
    env_rng, mobility_rng, _action_rng, _perturb_rng = _evaluation_rngs(seed)
    states, wrapped_masks, _observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    useful_bits = 0.0
    energy_j = 0.0
    steps = 0
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    while True:
        masks = np.stack([wrapped.mask for wrapped in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        actions = masked_greedy_actions(q1, masks)
        result = environment.step(actions, env_rng)
        outcome = environment.last_outcome
        useful_bits += float(np.asarray(outcome.link_rate_bps).sum()) * interval_s
        energy_j += float(outcome.system_power_w) * interval_s
        steps += 1
        if result.done:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        encoded = trainer.encode_states(states)
    if energy_j <= 0.0 or useful_bits <= 0.0:
        raise RuntimeError("reference calibration rollout must have positive bits/energy")
    return {
        "calibration_seed": int(seed),
        # Retained for old receipts; new V0.3 consumers use calibration_seed.
        "evaluation_seed": int(seed),
        "steps": int(steps),
        "interval_s": interval_s,
        "useful_bits": useful_bits,
        "energy_j": energy_j,
        "lambda_bits_per_j": useful_bits / energy_j,
    }


def _action_row(
    *,
    seed: int,
    step: int,
    focal_user: int,
    reference_action: int,
    candidate_action: int,
    reference_key: tuple[int, int] | None,
    candidate_key: tuple[int, int],
    baseline: ActionEvaluation,
    candidate: ActionEvaluation,
    isolated_reference: ActionEvaluation,
    isolated_candidate: ActionEvaluation,
    multiplier: float,
    interval_s: float,
    candidate_q1: float,
    reference_q1: float | None,
) -> dict[str, Any]:
    targets = ee_surplus_axis_targets(
        lambda_bits_per_j=multiplier,
        interval_s=interval_s,
        reference_system_rates_bps=np.asarray(baseline.link_rate_bps)[None, :],
        reference_system_power_w=np.array([baseline.system_power_w]),
        candidate_system_rates_bps=np.asarray(candidate.link_rate_bps)[None, :],
        candidate_system_power_w=np.array([candidate.system_power_w]),
        reference_isolated_rate_bps=float(
            isolated_reference.link_rate_bps[focal_user]
        ),
        reference_isolated_power_w=float(isolated_reference.system_power_w),
        candidate_isolated_rate_bps=float(isolated_candidate.link_rate_bps[focal_user]),
        candidate_isolated_power_w=float(isolated_candidate.system_power_w),
    )
    reference_load = _load_stats(baseline)
    candidate_load = _load_stats(candidate)
    base_active = _active_keys(baseline)
    candidate_active = _active_keys(candidate)
    focal_was_served = bool(baseline.resolution.served[focal_user])
    focal_is_served = bool(candidate.resolution.served[focal_user])
    service_safe = bool(
        candidate.resolution.served_count >= baseline.resolution.served_count
        and (not focal_was_served or focal_is_served)
    )
    reference_ee = float(baseline.energy.system_ee_bits_per_j)
    candidate_ee = float(candidate.energy.system_ee_bits_per_j)
    reference_system_rate = float(np.asarray(baseline.link_rate_bps).sum())
    candidate_system_rate = float(np.asarray(candidate.link_rate_bps).sum())
    reference_isolated_rate = float(isolated_reference.link_rate_bps[focal_user])
    candidate_isolated_rate = float(isolated_candidate.link_rate_bps[focal_user])
    nonfocal = np.ones(np.asarray(isolated_candidate.link_rate_bps).shape, dtype=np.bool_)
    nonfocal[focal_user] = False
    if np.any(np.asarray(isolated_reference.link_rate_bps)[nonfocal] != 0.0) or np.any(
        np.asarray(isolated_candidate.link_rate_bps)[nonfocal] != 0.0
    ):
        raise RuntimeError("isolated evaluation produced non-focal throughput")
    return {
        "evaluation_seed": int(seed),
        "step_index": int(step),
        "focal_user": int(focal_user),
        "reference_action": int(reference_action),
        "candidate_action": int(candidate_action),
        "reference_key": list(reference_key) if reference_key is not None else None,
        "candidate_key": list(candidate_key),
        "reference_q1": reference_q1,
        "candidate_q1": float(candidate_q1),
        "service_safe": service_safe,
        "reference_served": int(baseline.resolution.served_count),
        "candidate_served": int(candidate.resolution.served_count),
        "reference_system_ee_bits_per_j": reference_ee,
        "candidate_system_ee_bits_per_j": candidate_ee,
        "delta_immediate_ee_bits_per_j": candidate_ee - reference_ee,
        "lambda_bits_per_j": multiplier,
        "interval_s": interval_s,
        "reference_system_rate_bps": reference_system_rate,
        "candidate_system_rate_bps": candidate_system_rate,
        "reference_system_power_w": float(baseline.system_power_w),
        "candidate_system_power_w": float(candidate.system_power_w),
        "reference_isolated_rate_bps": reference_isolated_rate,
        "candidate_isolated_rate_bps": candidate_isolated_rate,
        "reference_isolated_power_w": float(isolated_reference.system_power_w),
        "candidate_isolated_power_w": float(isolated_candidate.system_power_w),
        "delta_system_bits": interval_s
        * (candidate_system_rate - reference_system_rate),
        "delta_system_energy_j": interval_s
        * (float(candidate.system_power_w) - float(baseline.system_power_w)),
        "delta_isolated_bits": interval_s
        * (candidate_isolated_rate - reference_isolated_rate),
        "delta_isolated_energy_j": interval_s
        * (
            float(isolated_candidate.system_power_w)
            - float(isolated_reference.system_power_w)
        ),
        "z1_direct_surplus_bits": targets.z1_direct_surplus_bits,
        "z2_temporal_surplus_bits": targets.z2_temporal_surplus_bits,
        "z3_spatial_surplus_bits": targets.z3_spatial_surplus_bits,
        "system_surplus_bits": targets.system_window_surplus_bits,
        "identity_residual_bits": targets.identity_residual_bits,
        "reference_effective_beams": int(baseline.energy.eff_beams),
        "candidate_effective_beams": int(candidate.energy.eff_beams),
        "active_beams_added": [
            list(key) for key in sorted(candidate_active - base_active)
        ],
        "active_beams_removed": [
            list(key) for key in sorted(base_active - candidate_active)
        ],
        "sum_squared_load_delta": float(
            candidate_load["sum_squared_beam_load"]
            - reference_load["sum_squared_beam_load"]
        ),
    }


def _anchor_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[0]
    reference = {
        "candidate_action": first["reference_action"],
        "candidate_key": first["reference_key"],
        "z1_direct_surplus_bits": 0.0,
        "z3_spatial_surplus_bits": 0.0,
        "system_surplus_bits": 0.0,
        "service_safe": True,
    }
    eligible = [reference] + [row for row in rows if row["service_safe"]]
    direct_best = max(
        eligible,
        key=lambda row: (
            float(row["z1_direct_surplus_bits"]),
            -int(row["candidate_action"]),
        ),
    )
    system_best = max(
        eligible,
        key=lambda row: (
            float(row["system_surplus_bits"]),
            -int(row["candidate_action"]),
        ),
    )
    gain = float(system_best["system_surplus_bits"]) - float(
        direct_best["system_surplus_bits"]
    )
    pivotal = int(direct_best["candidate_action"]) != int(
        system_best["candidate_action"]
    )
    return {
        "evaluation_seed": first["evaluation_seed"],
        "step_index": first["step_index"],
        "focal_user": first["focal_user"],
        "candidate_count": len(rows),
        "service_safe_candidate_count": sum(bool(row["service_safe"]) for row in rows),
        "direct_best_action": int(direct_best["candidate_action"]),
        "system_best_action": int(system_best["candidate_action"]),
        "c3_oracle_pivotal": pivotal,
        "c3_oracle_system_surplus_gain_bits": gain,
        "c3_positive_headroom": bool(pivotal and gain > 1e-9),
    }


def _run_candidate_pass(
    trainer: Any,
    environment: Any,
    *,
    seed: int,
    multiplier: float,
    focal_users_per_step: int,
    max_steps: int,
    max_alternatives: int,
) -> dict[str, Any]:
    env_rng, mobility_rng, action_rng, _perturb_rng = _evaluation_rngs(seed)
    states, wrapped_masks, observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    interval_s = float(environment.environment.driver.config.ephemeris.time_step_s)
    rows: list[dict[str, Any]] = []
    anchors: list[dict[str, Any]] = []

    for _ in range(max_steps):
        masks = np.stack([wrapped.mask for wrapped in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = masked_greedy_actions(q1, masks)
        baseline_keys = physical_action_keys(
            baseline_actions, observation.candidates.slot_tables
        )
        focal_users = [
            int(uid)
            for uid in action_rng.choice(
                environment.num_users,
                size=focal_users_per_step,
                replace=False,
            ).tolist()
        ]
        frozen: list[tuple[int, list[Any]]] = []
        for focal_user in focal_users:
            table = observation.candidates.slot_tables[focal_user]
            candidates = _physical_candidates(
                table,
                prior_demand=observation.user_states[focal_user].beam_loads,
                candidate_sinr=observation.candidate_sinr[focal_user],
                q1=q1[focal_user],
            )
            alternatives = [
                candidate
                for candidate in candidates
                if candidate.key != baseline_keys[focal_user]
            ]
            alternatives.sort(key=lambda row: row.action)
            if max_alternatives > 0:
                alternatives = alternatives[:max_alternatives]
            frozen.append((focal_user, alternatives))

        baseline = environment.environment.evaluate_actions(baseline_actions, env_rng)
        for focal_user, alternatives in frozen:
            if not alternatives:
                continue
            reference_action = int(baseline_actions[focal_user])
            isolated_reference = _isolated_evaluation(
                environment,
                focal_user=focal_user,
                action=reference_action,
                rng=env_rng,
            )
            anchor_rows: list[dict[str, Any]] = []
            for alternative in alternatives:
                candidate_actions = baseline_actions.copy()
                candidate_actions[focal_user] = alternative.action
                candidate = environment.environment.evaluate_actions(
                    candidate_actions, env_rng
                )
                isolated_candidate = _isolated_evaluation(
                    environment,
                    focal_user=focal_user,
                    action=alternative.action,
                    rng=env_rng,
                )
                reference_q1 = (
                    float(q1[focal_user, reference_action])
                    if reference_action != NO_OP_ACTION
                    else None
                )
                row = _action_row(
                    seed=seed,
                    step=int(observation.step_index),
                    focal_user=focal_user,
                    reference_action=reference_action,
                    candidate_action=alternative.action,
                    reference_key=baseline_keys[focal_user],
                    candidate_key=alternative.key,
                    baseline=baseline,
                    candidate=candidate,
                    isolated_reference=isolated_reference,
                    isolated_candidate=isolated_candidate,
                    multiplier=multiplier,
                    interval_s=interval_s,
                    candidate_q1=alternative.q1,
                    reference_q1=reference_q1,
                )
                rows.append(row)
                anchor_rows.append(row)
            anchors.append(_anchor_summary(anchor_rows))

        result = environment.step(baseline_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = environment.last_outcome.observation
        encoded = trainer.encode_states(states)

    return {"rows": rows, "anchors": anchors, "interval_s": interval_s}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument("--seed", type=int, default=P6_EVALUATION_SEEDS[0])
    parser.add_argument("--focal-users-per-step", type=int, default=2)
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--max-alternatives", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if args.seed not in P6_EVALUATION_SEEDS:
        raise ValueError("--seed must belong to the frozen P6 evaluation pool")
    if args.users < 1 or not 1 <= args.focal_users_per_step <= args.users:
        raise ValueError("invalid user or focal-user count")
    if args.max_steps < 1 or args.max_alternatives < 0:
        raise ValueError("invalid pilot bound")

    from mcrl.runtime.prereg import read_prereg

    record = read_prereg(args.prereg)
    with tempfile.TemporaryDirectory(prefix="mcrl-ee-axis-c3-pilot-") as temp:
        archive = _frozen_archive(record, args.tle_root, Path(temp) / "frozen-tle")
        trainer, checkpoint = _verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=args.users,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint differs from the frozen oracle input")
        lambda_environment = _make_environment(archive, users=args.users)
        calibration = _freeze_lambda(trainer, lambda_environment, seed=args.seed)
        pilot_environment = _make_environment(archive, users=args.users)
        pilot = _run_candidate_pass(
            trainer,
            pilot_environment,
            seed=args.seed,
            multiplier=float(calibration["lambda_bits_per_j"]),
            focal_users_per_step=args.focal_users_per_step,
            max_steps=args.max_steps,
            max_alternatives=args.max_alternatives,
        )

    rows = pilot["rows"]
    anchors = pilot["anchors"]
    safe = [row for row in rows if row["service_safe"]]
    payload = {
        "schema": "multi-catfish-ee-axis-c3-unilateral-pilot-v02",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "mode": "no training; Q1 reference plus discarded unilateral counterfactuals",
        "claim_ceiling": (
            "formula/physics opportunity pilot only; not learnability, efficacy, "
            "statistical confirmation, or deployment proof"
        ),
        "design_contract": "docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.2-2026-08-31.md",
        "analysis_path": str(Path(__file__).resolve()),
        "analysis_sha256": _sha256(Path(__file__).resolve()),
        "checkpoint": checkpoint,
        "calibration": calibration,
        "pilot_bounds": {
            "users": args.users,
            "seed": args.seed,
            "max_steps": args.max_steps,
            "focal_users_per_step": args.focal_users_per_step,
            "max_alternatives": args.max_alternatives,
        },
        "summary": {
            "anchors": len(anchors),
            "evaluated_candidates": len(rows),
            "service_safe_candidates": len(safe),
            "positive_z3_candidates": sum(
                float(row["z3_spatial_surplus_bits"]) > 0.0 for row in safe
            ),
            "positive_total_surplus_candidates": sum(
                float(row["system_surplus_bits"]) > 0.0 for row in safe
            ),
            "anchors_with_c3_oracle_pivotality": sum(
                bool(anchor["c3_oracle_pivotal"]) for anchor in anchors
            ),
            "anchors_with_positive_c3_headroom": sum(
                bool(anchor["c3_positive_headroom"]) for anchor in anchors
            ),
            "max_identity_residual_bits": max(
                (abs(float(row["identity_residual_bits"])) for row in rows),
                default=0.0,
            ),
        },
        "anchors": anchors,
        "rows": rows,
    }
    if not all(math.isfinite(float(value)) for value in payload["summary"].values()):
        raise RuntimeError("pilot summary contains non-finite values")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
