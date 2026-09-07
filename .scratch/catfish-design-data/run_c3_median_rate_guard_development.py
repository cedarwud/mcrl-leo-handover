#!/usr/bin/env python3
"""Evaluate the frozen median-channel C3 safety rule on the read dev seed."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / ".scratch" / "catfish-oracle-gate"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import run_c3_intra_bottleneck_shadow as base  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC = HERE / "C3-MEDIAN-RATE-GUARD-DEVELOPMENT-SPEC-2026-08-27.md"
SPEC_SHA256 = "19b07033127598da2a36f5f1e50406f6ba4cf719bb18ecad83ccf7b57c01cc73"
INPUT = HERE / "c3-intra-bottleneck-shadow-seed-2026082701-v1.json"
INPUT_SHA256 = "15c8399b22f027cc20f44bccb43b78b2d9feee48bfff23d53e39c52fde922a72"
DEFAULT_OUTPUT = HERE / "c3-median-rate-guard-development-seed-2026082701-v1.json"


def run_development(
    trainer: Any, wrapped: Any, certified_input: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_step: dict[int, list[dict[str, Any]]] = {}
    for row in certified_input:
        by_step.setdefault(int(row["step_index"]), []).append(row)

    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(
        base.EVALUATION_SEED
    )
    states, wrapped_masks, observation = wrapped.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    output: list[dict[str, Any]] = []

    while True:
        masks = np.stack([row.mask for row in wrapped_masks])
        q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
        baseline_actions = base.v1.masked_greedy_actions(q1, masks)
        environment = wrapped.environment
        baseline = environment.evaluate_actions(baseline_actions, env_rng)
        step = int(observation.step_index)

        original_physics = environment.physics
        environment.physics = replace(original_physics, fading_enabled=False)
        try:
            median_reference = environment.evaluate_actions(baseline_actions, env_rng)
            for original in by_step.get(step, []):
                uid = int(original["focal_user"])
                if int(original["reference_action"]) != int(baseline_actions[uid]):
                    raise RuntimeError("median replay reference action drifted")
                candidate_actions = baseline_actions.copy()
                candidate_actions[uid] = int(original["candidate_action"])
                median_candidate = environment.evaluate_actions(candidate_actions, env_rng)
                if not np.array_equal(
                    median_candidate.resolution.served,
                    median_reference.resolution.served,
                ):
                    raise RuntimeError("certified candidate changed median service")
                median_delta_rate = float(
                    median_candidate.energy.system_throughput_bps
                    - median_reference.energy.system_throughput_bps
                )
                median_delta_power = float(
                    median_candidate.system_power_w - median_reference.system_power_w
                )
                recorded_delta_power = float(original["realised_delta_system_power_w"])
                if abs(median_delta_power - recorded_delta_power) > base.POWER_TOLERANCE_W:
                    raise RuntimeError("median branch changed deterministic power identity")
                output.append(
                    {
                        "step_index": step,
                        "focal_user": uid,
                        "reference_action": int(baseline_actions[uid]),
                        "candidate_action": int(original["candidate_action"]),
                        "reference_key": original["reference_key"],
                        "candidate_key": original["candidate_key"],
                        "median_reference_throughput_bps": float(
                            median_reference.energy.system_throughput_bps
                        ),
                        "median_candidate_throughput_bps": float(
                            median_candidate.energy.system_throughput_bps
                        ),
                        "median_delta_throughput_bps": median_delta_rate,
                        "median_rate_noninferior_selected": bool(
                            median_delta_rate >= 0.0
                        ),
                        "delta_system_power_w": recorded_delta_power,
                        "realised_delta_throughput_bps": float(
                            original["delta_throughput_bps"]
                        ),
                        "realised_delta_ee_bits_per_j": float(
                            original["delta_ee_bits_per_j"]
                        ),
                        "guard_reads_actual_fading_rate_reward_ee_or_successor": False,
                    }
                )
        finally:
            environment.physics = original_physics

        result = wrapped.step(baseline_actions, env_rng)
        base.v1._assert_full_preview_parity(baseline, wrapped.last_outcome)
        if result.done:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = wrapped.last_outcome.observation
        encoded = trainer.encode_states(states)

    if len(output) != len(certified_input):
        raise RuntimeError("not every certified candidate was replayed")
    return output


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [row for row in rows if row["median_rate_noninferior_selected"]]
    rejected = [row for row in rows if not row["median_rate_noninferior_selected"]]
    ee = [float(row["realised_delta_ee_bits_per_j"]) for row in selected]
    rate = [float(row["realised_delta_throughput_bps"]) for row in selected]
    mean_ee = float(statistics.fmean(ee)) if ee else None
    mean_rate = float(statistics.fmean(rate)) if rate else None
    qualifies = bool(
        len(selected) >= 2
        and mean_ee is not None
        and mean_ee > 0.0
        and mean_rate is not None
        and mean_rate >= 0.0
    )
    return {
        "selected": len(selected),
        "rejected": len(rejected),
        "coverage_fraction": float(len(selected) / len(rows)) if rows else 0.0,
        "selected_realised_ee_positive": sum(value > 0.0 for value in ee),
        "selected_realised_ee_negative": sum(value < 0.0 for value in ee),
        "selected_realised_ee_positive_precision": (
            float(sum(value > 0.0 for value in ee) / len(ee)) if ee else None
        ),
        "selected_mean_delta_ee_bits_per_j": mean_ee,
        "selected_median_delta_ee_bits_per_j": (
            float(statistics.median(ee)) if ee else None
        ),
        "selected_realised_throughput_positive": sum(value > 0.0 for value in rate),
        "selected_realised_throughput_negative": sum(value < 0.0 for value in rate),
        "selected_mean_delta_throughput_bps": mean_rate,
        "selected_median_delta_throughput_bps": (
            float(statistics.median(rate)) if rate else None
        ),
        "ee_confusion": {
            "selected_positive": sum(
                float(row["realised_delta_ee_bits_per_j"]) > 0.0 for row in selected
            ),
            "selected_nonpositive": sum(
                float(row["realised_delta_ee_bits_per_j"]) <= 0.0 for row in selected
            ),
            "rejected_positive": sum(
                float(row["realised_delta_ee_bits_per_j"]) > 0.0 for row in rejected
            ),
            "rejected_nonpositive": sum(
                float(row["realised_delta_ee_bits_per_j"]) <= 0.0 for row in rejected
            ),
        },
        "qualifies_for_disjoint_seed_gate": qualifies,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=base.v1.DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=base.v1.DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if base.v1._sha256(SPEC) != SPEC_SHA256:
        raise RuntimeError("median guard specification digest changed")
    if base.v1._sha256(INPUT) != INPUT_SHA256:
        raise RuntimeError("frozen v1 C3 result digest changed")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite output: {args.output}")
    input_payload = json.loads(INPUT.read_text(encoding="utf-8"))
    certified = [
        row
        for row in input_payload["rollout"]["candidate_rows"]
        if row["status"] == "certified"
    ]

    record = read_prereg(args.prereg)
    current_code_sha = _code_sha256(_default_code_paths())
    with tempfile.TemporaryDirectory(prefix="mcrl-c3-median-dev-") as temp:
        archive = base.v1._frozen_archive(
            record, args.tle_root, Path(temp) / "frozen-tle"
        )
        trainer, checkpoint = base.v1._verify_and_load_trainer(
            record, archive, run_dir=args.input_dir / "main", users=base.USERS
        )
        if checkpoint["checkpoint_sha256"] != base.EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("checkpoint digest differs from development input")
        wrapped = base.v1._make_environment(archive, users=base.USERS)
        rows = run_development(trainer, wrapped, certified)

    summary = summarize(rows)
    decision = (
        "FREEZE_MEDIAN_RATE_RULE_FOR_DIFFERENT_SEED_GATE"
        if summary["qualifies_for_disjoint_seed_gate"]
        else "REJECT_MEDIAN_RATE_RULE"
    )
    payload = {
        "schema": "mcrl-c3-median-rate-guard-development-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "mode": "final guard development on already-read seed; not validation",
        "spec_path": str(SPEC),
        "spec_sha256": SPEC_SHA256,
        "input_path": str(INPUT),
        "input_sha256": INPUT_SHA256,
        "analysis_path": str(Path(__file__).resolve()),
        "analysis_sha256": base.v1._sha256(Path(__file__).resolve()),
        "analysis_code_sha256": current_code_sha,
        "analysis_source_matches_training": (
            current_code_sha == checkpoint["launched_code_sha256"]
        ),
        "checkpoint": checkpoint,
        "evaluation_seed": base.EVALUATION_SEED,
        "candidate_count": len(rows),
        "summary": summary,
        "decision": decision,
        "claim_boundary": (
            "development only; a qualifying rule needs disjoint-seed "
            "validation before implementation or training"
        ),
        "rows": rows,
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
