#!/usr/bin/env python3
"""Prospective, no-training C2 V0.3 opportunity/cost census.

The census follows an unchanged Main-only TLE trajectory.  At each eligible
anchor it forecasts the complete predeclared incumbent-hold schedule (ascending
departure-user ID, capped before any forecast), validates the K=0/1/K>=2
selection support, then advances the live environment with Main.  It never
executes a C2 live option, updates a network, or writes replay.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STAGE0 = HERE.parent / "catfish-stage0"
SMC = HERE.parent / "smc-er-short-ep"
for path in (HERE, STAGE0, SMC, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_temporal_fork_core as core  # noqa: E402
import c2_temporal_fork_selection as selection  # noqa: E402
import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import run_c2_v03_real_backend_smoke as smoke  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    assert_ephemeris_matches_record,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _departure_users(wrapped, main_physical) -> list[int]:
    users: list[int] = []
    for uid, (incumbent, physical) in enumerate(
        zip(wrapped.environment._previous_association, main_physical, strict=True)
    ):
        if (
            isinstance(incumbent, Association)
            and physical is not None
            and physical != (int(incumbent.norad_id), int(incumbent.cell_id))
        ):
            users.append(uid)
    return users


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "artifacts" / "c2-v03-multianchor-census-20260829.json",
    )
    parser.add_argument("--max-candidates", type=int, default=9)
    parser.add_argument("--max-anchors", type=int, default=3)
    parser.add_argument("--seed", type=int, default=smoke.DEVELOPMENT_SEED)
    args = parser.parse_args()
    if args.max_candidates <= 0 or args.max_anchors <= 0 or args.seed < 0:
        raise ValueError("candidate/anchor caps must be positive and seed nonnegative")

    record = read_prereg(REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json")
    archive = TleArchive(Path("/tmp/mcrl-tle-frozen-20260820-v1"))
    assert_ephemeris_matches_record(record, archive=archive)
    trainer, checkpoint = loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=REPO / "artifacts/training-2026-08-25-rerun01/main",
        users=smoke.USERS,
    )
    environment_source_sha256 = _code_sha256(_default_code_paths())
    reward_source_sha256 = _sha256(REPO / "src/mcrl/env/step.py")
    wrapped = loader._make_environment(archive, users=smoke.USERS)
    env_rng, mobility_rng, action_rng, _control_rng = loader._evaluation_rngs(
        args.seed
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    networks_before = smoke._network_snapshot(trainer)
    replay_before = len(trainer.replay)
    anchors: list[dict[str, object]] = []
    started = time.perf_counter()

    while int(observation.step_index) <= smoke.MAX_ANCHOR_STEP:
        main_actions, main_physical = smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        departures = _departure_users(wrapped, main_physical)
        if departures and 10 - int(observation.step_index) >= core.HOLD_STEPS + 1:
            scheduled = departures[: args.max_candidates]
            rows: list[dict[str, object]] = []
            prepared_candidates = []
            anchor_started = time.perf_counter()
            for uid in scheduled:
                candidate_started = time.perf_counter()
                try:
                    service = backend.C2TemporalForkTrainerBackend(
                        wrapped=wrapped,
                        states=states,
                        masks=masks,
                        observation=observation,
                        env_rng=env_rng,
                        trainer=trainer,
                        checkpoint_sha256=checkpoint["checkpoint_sha256"],
                        environment_source_sha256=environment_source_sha256,
                        reward_source_sha256=reward_source_sha256,
                        evaluation_seed=args.seed,
                        focal_user=uid,
                    )
                    prepared = service.prepare_incumbent_hold(focal_user=uid)
                    built = prepared.run_forecast()
                    prepared_candidates.append(prepared)
                    rows.append(
                        {
                            "focal_user": uid,
                            "candidate_key": list(prepared.candidate_key),
                            "passed": built.certificate.passed,
                            "failures": [
                                failure.value for failure in built.certificate.failures
                            ],
                            "ee_surplus_bits": built.certificate.ee_surplus_bits,
                            "ee_surplus_floor_bits": (
                                built.certificate.ee_surplus_floor_bits
                            ),
                            "hold_r2_margin": built.certificate.hold_r2_margin,
                            "full_r2_margin": built.certificate.full_r2_margin,
                            "elapsed_s": time.perf_counter() - candidate_started,
                        }
                    )
                except Exception as error:
                    rows.append(
                        {
                            "focal_user": uid,
                            "passed": False,
                            "contract_error": f"{type(error).__name__}: {error}",
                            "elapsed_s": time.perf_counter() - candidate_started,
                        }
                    )
            choice = selection.select_prepared_fork(
                prepared_candidates,
                behavior_rng=action_rng,
                mode=selection.CHOICE_MODE_RANDOM,
                epsilon=0.0,
                preoutcome_timestamp_ns=time.time_ns(),
            )
            selection.assert_prepared_selection_bound(choice)
            k = len(choice.receipt.support)
            anchors.append(
                {
                    "step_index": int(observation.step_index),
                    "departure_user_count": len(departures),
                    "scheduled_focal_users": scheduled,
                    "attempted_count": len(rows),
                    "forecast_complete_count": len(prepared_candidates),
                    "passed_count": k,
                    "choice_class": "K0" if k == 0 else "K1" if k == 1 else "K_GE_2",
                    "selection_receipt": asdict(choice.receipt),
                    "candidates": rows,
                    "elapsed_s": time.perf_counter() - anchor_started,
                }
            )
            if len(anchors) >= args.max_anchors:
                break

        result = wrapped.step(main_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation

    counts = {"K0": 0, "K1": 0, "K_GE_2": 0}
    candidate_times: list[float] = []
    passed_total = 0
    attempts_total = 0
    complete_total = 0
    for anchor in anchors:
        counts[str(anchor["choice_class"])] += 1
        passed_total += int(anchor["passed_count"])
        attempts_total += int(anchor["attempted_count"])
        complete_total += int(anchor["forecast_complete_count"])
        candidate_times.extend(
            float(row["elapsed_s"])
            for row in anchor["candidates"]
            if "elapsed_s" in row
        )
    unchanged = smoke._networks_equal(trainer, networks_before)
    payload = {
        "schema": "c2-v03-multianchor-opportunity-census-v1",
        "status": "PASS" if unchanged and len(trainer.replay) == replay_before else "FAIL",
        "claim_ceiling": "OPPORTUNITY_AND_WALLTIME_ONLY_NOT_TRAINING_OR_EE_EFFICACY",
        "training_or_replay_write": False,
        "candidate_schedule": {
            "rule": "ascending_departure_user_incumbent_hold_only_no_early_stop",
            "max_candidates_per_anchor": args.max_candidates,
            "max_anchors": args.max_anchors,
        },
        "seed": args.seed,
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "anchors": anchors,
        "summary": {
            "anchor_count": len(anchors),
            "choice_class_counts": counts,
            "attempted_candidates": attempts_total,
            "forecast_complete_candidates": complete_total,
            "passed_candidates": passed_total,
            "multi_choice_anchor_fraction": (
                0.0 if not anchors else counts["K_GE_2"] / len(anchors)
            ),
            "mean_candidate_elapsed_s": (
                None if not candidate_times else float(np.mean(candidate_times))
            ),
            "max_candidate_elapsed_s": (
                None if not candidate_times else float(np.max(candidate_times))
            ),
        },
        "main_networks_bitwise_unchanged": unchanged,
        "main_replay_length_before": replay_before,
        "main_replay_length_after": len(trainer.replay),
        "elapsed_s": time.perf_counter() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
