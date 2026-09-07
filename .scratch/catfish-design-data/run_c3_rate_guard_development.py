#!/usr/bin/env python3
"""Attach frozen pre-outcome rate proxies to the read C3 development seed."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

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


SPEC = HERE / "C3-RATE-GUARD-DEVELOPMENT-SPEC-2026-08-27.md"
SPEC_SHA256 = "06381604216a8e734d66a2f0e82d00943d99de2ea6889df08839f5eb0fbd3945"
INPUT = HERE / "c3-intra-bottleneck-shadow-seed-2026082701-v1.json"
INPUT_SHA256 = "15c8399b22f027cc20f44bccb43b78b2d9feee48bfff23d53e39c52fde922a72"
DEFAULT_OUTPUT = HERE / "c3-rate-guard-development-seed-2026082701-v1.json"


def _proxy_throughput(
    *,
    actions: np.ndarray,
    keys: list[base.PhysicalKey | None],
    served: np.ndarray,
    loads: dict[base.PhysicalKey, int],
    candidate_sinr: np.ndarray,
    bandwidth_hz: float,
) -> float:
    total = 0.0
    for uid in np.flatnonzero(served).tolist():
        key = keys[uid]
        if key is None or key not in loads or loads[key] < 1:
            raise RuntimeError("served proxy row has no positive beam load")
        action = int(actions[uid])
        gamma = float(candidate_sinr[uid, action])
        if not math.isfinite(gamma) or gamma < 0.0:
            raise RuntimeError("candidate SINR proxy must be finite and non-negative")
        total += bandwidth_hz / loads[key] * math.log2(1.0 + gamma)
    return float(total)


def _summarize(
    rows: list[dict[str, Any]], selector: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    selected = [row for row in rows if selector(row)]
    rejected = [row for row in rows if not selector(row)]
    ee = [float(row["realised_delta_ee_bits_per_j"]) for row in selected]
    rate = [float(row["realised_delta_throughput_bps"]) for row in selected]
    return {
        "selected": len(selected),
        "rejected": len(rejected),
        "coverage_fraction": float(len(selected) / len(rows)) if rows else 0.0,
        "selected_realised_ee_positive": sum(value > 0.0 for value in ee),
        "selected_realised_ee_negative": sum(value < 0.0 for value in ee),
        "selected_realised_ee_positive_precision": (
            float(sum(value > 0.0 for value in ee) / len(ee)) if ee else None
        ),
        "selected_mean_delta_ee_bits_per_j": (
            float(statistics.fmean(ee)) if ee else None
        ),
        "selected_median_delta_ee_bits_per_j": (
            float(statistics.median(ee)) if ee else None
        ),
        "selected_realised_throughput_positive": sum(value > 0.0 for value in rate),
        "selected_realised_throughput_negative": sum(value < 0.0 for value in rate),
        "selected_mean_delta_throughput_bps": (
            float(statistics.fmean(rate)) if rate else None
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
    }


def run_development(
    trainer: Any,
    wrapped: Any,
    certified_input: list[dict[str, Any]],
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
        baseline_keys = base.v1.physical_action_keys(
            baseline_actions, observation.candidates.slot_tables
        )
        environment = wrapped.environment
        baseline = environment.evaluate_actions(baseline_actions, env_rng)
        step = int(observation.step_index)
        loads = {
            (int(key[0]), int(key[1])): int(value)
            for key, value in baseline.resolution.eligible_load_by_beam.items()
        }
        reference_proxy = _proxy_throughput(
            actions=baseline_actions,
            keys=baseline_keys,
            served=baseline.resolution.served,
            loads=loads,
            candidate_sinr=observation.candidate_sinr,
            bandwidth_hz=environment.physics.beam_bandwidth_hz,
        )

        for original in by_step.get(step, []):
            uid = int(original["focal_user"])
            if int(original["reference_action"]) != int(baseline_actions[uid]):
                raise RuntimeError("development replay reference action drifted")
            source = baseline_keys[uid]
            candidate = tuple(int(value) for value in original["candidate_key"])
            if source != tuple(int(value) for value in original["reference_key"]):
                raise RuntimeError("development replay reference key drifted")
            candidate_action = int(original["candidate_action"])
            actions = baseline_actions.copy()
            actions[uid] = candidate_action
            keys = list(baseline_keys)
            keys[uid] = candidate
            candidate_loads = dict(loads)
            if source is None or candidate not in candidate_loads:
                raise RuntimeError("certified development row lacks source/destination")
            candidate_loads[source] -= 1
            candidate_loads[candidate] += 1
            if candidate_loads[source] < 1:
                raise RuntimeError("certified source unexpectedly deactivated")
            candidate_proxy = _proxy_throughput(
                actions=actions,
                keys=keys,
                served=baseline.resolution.served,
                loads=candidate_loads,
                candidate_sinr=observation.candidate_sinr,
                bandwidth_hz=environment.physics.beam_bandwidth_hz,
            )
            delta_proxy = candidate_proxy - reference_proxy
            reference_power = float(original["reference_system_power_w"])
            delta_power = float(original["realised_delta_system_power_w"])
            eta_proxy = reference_proxy / reference_power
            g_ee = delta_proxy - eta_proxy * delta_power
            output.append(
                {
                    "step_index": step,
                    "focal_user": uid,
                    "reference_action": int(baseline_actions[uid]),
                    "candidate_action": candidate_action,
                    "reference_key": original["reference_key"],
                    "candidate_key": original["candidate_key"],
                    "reference_proxy_throughput_bps": reference_proxy,
                    "candidate_proxy_throughput_bps": candidate_proxy,
                    "g_rate_proxy_bps": delta_proxy,
                    "reference_proxy_ee_bits_per_j": eta_proxy,
                    "g_ee_proxy_bps": g_ee,
                    "rate_noninferior_selected": bool(delta_proxy >= 0.0),
                    "proxy_ee_positive_selected": bool(g_ee > 0.0),
                    "delta_system_power_w": delta_power,
                    "realised_delta_throughput_bps": float(
                        original["delta_throughput_bps"]
                    ),
                    "realised_delta_ee_bits_per_j": float(
                        original["delta_ee_bits_per_j"]
                    ),
                    "proxy_reads_current_outcome": False,
                }
            )

        result = wrapped.step(baseline_actions, env_rng)
        base.v1._assert_full_preview_parity(baseline, wrapped.last_outcome)
        if result.done:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = wrapped.last_outcome.observation
        encoded = trainer.encode_states(states)

    if len(output) != len(certified_input):
        raise RuntimeError("not every certified development candidate was replayed")
    return output


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
        raise RuntimeError("development specification digest changed")
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
    with tempfile.TemporaryDirectory(prefix="mcrl-c3-rate-dev-") as temp:
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

    summaries = {
        "POWER_ONLY": _summarize(rows, lambda _row: True),
        "RATE_NONINFERIOR": _summarize(
            rows, lambda row: bool(row["rate_noninferior_selected"])
        ),
        "PROXY_EE_POSITIVE": _summarize(
            rows, lambda row: bool(row["proxy_ee_positive_selected"])
        ),
    }
    qualifying = [
        name
        for name in ("RATE_NONINFERIOR", "PROXY_EE_POSITIVE")
        if int(summaries[name]["selected"]) >= 2
        and float(summaries[name]["selected_mean_delta_ee_bits_per_j"]) > 0.0
    ]
    chosen = (
        "RATE_NONINFERIOR"
        if "RATE_NONINFERIOR" in qualifying
        else (qualifying[0] if qualifying else None)
    )
    decision = (
        "FREEZE_CHOSEN_RULE_FOR_DIFFERENT_SEED_GATE"
        if chosen is not None
        else "NO_RATE_GUARD_ADVANCES"
    )
    payload = {
        "schema": "mcrl-c3-rate-guard-development-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "mode": "already-read development seed; not validation",
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
        "summaries": summaries,
        "qualifying_rules": qualifying,
        "chosen_rule": chosen,
        "decision": decision,
        "claim_boundary": (
            "guard selection only; chosen rule needs frozen different-seed "
            "validation before any implementation or training"
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
