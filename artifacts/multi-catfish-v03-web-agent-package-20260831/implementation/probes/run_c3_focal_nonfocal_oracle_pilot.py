#!/usr/bin/env python3
"""No-training C3 falsifier for the V0.3 EE-axis design.

One frozen Q1 reference policy supplies the global Dinkelbach multiplier and
the live baseline path.  At selected anchors, every retained candidate differs
only in one focal user's opening action.  The preview is discarded: no replay,
optimizer, checkpoint, or policy state is updated.
"""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(HERE))

from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.step import ActionEvaluation  # noqa: E402
from mcrl.runtime.ee_surplus_targets import (  # noqa: E402
    ee_surplus_axis_targets_v03,
)
from mcrl.runtime.head_pivotality import (  # noqa: E402
    masked_greedy_actions,
    physical_action_keys,
)
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS  # noqa: E402
from mcrl.runtime.training_pipeline import _evaluation_rngs  # noqa: E402
from run_c3_unilateral_oracle_pilot import _freeze_lambda  # noqa: E402
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


DEFAULT_OUTPUT = HERE / "c3-focal-nonfocal-oracle-pilot-v03.json"


def _targets(
    *,
    baseline: ActionEvaluation,
    candidate: ActionEvaluation,
    focal_user: int,
    multiplier: float,
    interval_s: float,
):
    return ee_surplus_axis_targets_v03(
        lambda_bits_per_j=multiplier,
        interval_s=interval_s,
        focal_user=focal_user,
        reference_system_rates_bps=np.asarray(baseline.link_rate_bps)[None, :],
        reference_system_power_w=np.array([baseline.system_power_w]),
        candidate_system_rates_bps=np.asarray(candidate.link_rate_bps)[None, :],
        candidate_system_power_w=np.array([candidate.system_power_w]),
    )


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
    multiplier: float,
    interval_s: float,
    candidate_q1: float,
    reference_q1: float | None,
) -> dict[str, Any]:
    targets = _targets(
        baseline=baseline,
        candidate=candidate,
        focal_user=focal_user,
        multiplier=multiplier,
        interval_s=interval_s,
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
    reference_rates = np.asarray(baseline.link_rate_bps, dtype=np.float64)
    candidate_rates = np.asarray(candidate.link_rate_bps, dtype=np.float64)
    nonfocal = np.ones(reference_rates.shape, dtype=np.bool_)
    nonfocal[focal_user] = False
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
        "reference_system_ee_bits_per_j": float(
            baseline.energy.system_ee_bits_per_j
        ),
        "candidate_system_ee_bits_per_j": float(
            candidate.energy.system_ee_bits_per_j
        ),
        "lambda_bits_per_j": multiplier,
        "interval_s": interval_s,
        "reference_focal_rate_bps": float(reference_rates[focal_user]),
        "candidate_focal_rate_bps": float(candidate_rates[focal_user]),
        "reference_nonfocal_rate_bps": float(reference_rates[nonfocal].sum()),
        "candidate_nonfocal_rate_bps": float(candidate_rates[nonfocal].sum()),
        "reference_system_rate_bps": float(reference_rates.sum()),
        "candidate_system_rate_bps": float(candidate_rates.sum()),
        "reference_system_power_w": float(baseline.system_power_w),
        "candidate_system_power_w": float(candidate.system_power_w),
        "delta_system_energy_j": interval_s
        * (float(candidate.system_power_w) - float(baseline.system_power_w)),
        "z1_focal_surplus_bits": targets.z1_focal_surplus_bits,
        "z2_temporal_surplus_bits": targets.z2_temporal_surplus_bits,
        "z3_nonfocal_externality_bits": targets.z3_nonfocal_externality_bits,
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
        "z1_focal_surplus_bits": 0.0,
        "z3_nonfocal_externality_bits": 0.0,
        "system_surplus_bits": 0.0,
        "service_safe": True,
    }
    eligible = [reference] + [row for row in rows if row["service_safe"]]
    direct_best = max(
        eligible,
        key=lambda row: (
            float(row["z1_focal_surplus_bits"]),
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
    max_p2_residual = 0.0

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
            same = _targets(
                baseline=baseline,
                candidate=baseline,
                focal_user=focal_user,
                multiplier=multiplier,
                interval_s=interval_s,
            )
            max_p2_residual = max(
                max_p2_residual,
                abs(same.z1_focal_surplus_bits),
                abs(same.z2_temporal_surplus_bits),
                abs(same.z3_nonfocal_externality_bits),
            )
            reference_action = int(baseline_actions[focal_user])
            anchor_rows: list[dict[str, Any]] = []
            for alternative in alternatives:
                candidate_actions = baseline_actions.copy()
                candidate_actions[focal_user] = alternative.action
                candidate = environment.environment.evaluate_actions(
                    candidate_actions, env_rng
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

    return {
        "rows": rows,
        "anchors": anchors,
        "interval_s": interval_s,
        "max_identical_branch_target_bits": max_p2_residual,
    }


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + end - 1)
        start = end
    return ranks


def _distinctness(rows: list[dict[str, Any]]) -> dict[str, float | None]:
    if len(rows) < 2:
        return {
            "spearman_z1_z3": None,
            "affine_r_squared_z3_from_z1": None,
            "affine_normalized_rmse_z3_from_z1": None,
        }
    z1 = np.asarray([row["z1_focal_surplus_bits"] for row in rows], dtype=np.float64)
    z3 = np.asarray(
        [row["z3_nonfocal_externality_bits"] for row in rows], dtype=np.float64
    )
    rank1 = _rankdata(z1)
    rank3 = _rankdata(z3)
    if np.std(rank1) == 0.0 or np.std(rank3) == 0.0:
        spearman = None
    else:
        spearman = float(np.corrcoef(rank1, rank3)[0, 1])
    design = np.column_stack((np.ones(z1.size), z1))
    fitted = design @ np.linalg.lstsq(design, z3, rcond=None)[0]
    residual = z3 - fitted
    ss_res = float(np.dot(residual, residual))
    centered = z3 - float(z3.mean())
    ss_tot = float(np.dot(centered, centered))
    if ss_tot == 0.0:
        r_squared = None
        normalized_rmse = None
    else:
        r_squared = float(1.0 - ss_res / ss_tot)
        normalized_rmse = float(math.sqrt(ss_res / z3.size) / np.std(z3))
    return {
        "spearman_z1_z3": spearman,
        "affine_r_squared_z3_from_z1": r_squared,
        "affine_normalized_rmse_z3_from_z1": normalized_rmse,
    }


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
    with tempfile.TemporaryDirectory(prefix="mcrl-ee-axis-c3-v03-") as temp:
        archive = _frozen_archive(record, args.tle_root, Path(temp) / "frozen-tle")
        trainer, checkpoint = _verify_and_load_trainer(
            record,
            archive,
            run_dir=args.input_dir / "main",
            users=args.users,
        )
        if checkpoint["checkpoint_sha256"] != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint differs from the frozen oracle input")
        calibration = _freeze_lambda(
            trainer, _make_environment(archive, users=args.users), seed=args.seed
        )
        pilot = _run_candidate_pass(
            trainer,
            _make_environment(archive, users=args.users),
            seed=args.seed,
            multiplier=float(calibration["lambda_bits_per_j"]),
            focal_users_per_step=args.focal_users_per_step,
            max_steps=args.max_steps,
            max_alternatives=args.max_alternatives,
        )

    rows = pilot["rows"]
    anchors = pilot["anchors"]
    safe = [row for row in rows if row["service_safe"]]
    summary: dict[str, Any] = {
        "anchors": len(anchors),
        "evaluated_candidates": len(rows),
        "service_safe_candidates": len(safe),
        "positive_z3_candidates": sum(
            float(row["z3_nonfocal_externality_bits"]) > 0.0 for row in safe
        ),
        "positive_total_surplus_candidates": sum(
            float(row["system_surplus_bits"]) > 0.0 for row in safe
        ),
        "nonzero_energy_mediation_candidates": sum(
            float(row["delta_system_energy_j"]) != 0.0 for row in safe
        ),
        "anchors_with_c3_oracle_pivotality": sum(
            bool(anchor["c3_oracle_pivotal"]) for anchor in anchors
        ),
        "anchors_with_positive_c3_headroom": sum(
            bool(anchor["c3_positive_headroom"]) for anchor in anchors
        ),
        "max_identity_residual_bits": max(
            (abs(float(row["identity_residual_bits"])) for row in rows), default=0.0
        ),
        "max_identical_branch_target_bits": pilot[
            "max_identical_branch_target_bits"
        ],
    }
    summary.update(_distinctness(safe))
    payload = {
        "schema": "multi-catfish-ee-axis-c3-focal-nonfocal-pilot-v03",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "mode": "no training; Q1 reference plus discarded unilateral counterfactuals",
        "claim_ceiling": (
            "formula/physics opportunity pilot only; not learnability, efficacy, "
            "statistical confirmation, or deployment proof"
        ),
        "design_contract": "docs/MULTI-CATFISH-EE-AXIS-REDESIGN-CONTRACT-V0.3-2026-08-31.md",
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
        "summary": summary,
        "anchors": anchors,
        "rows": rows,
    }
    finite_values = [
        value for value in summary.values() if value is not None
    ]
    if not all(math.isfinite(float(value)) for value in finite_values):
        raise RuntimeError("pilot summary contains non-finite values")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
