#!/usr/bin/env python3
"""Bounded real-TLE/checkpoint smoke for the C2 V0.3 backend.

This scans at most one incumbent-hold candidate for each detached-Main
departure user at the first eligible anchor.  It performs no training and no
replay write.  If a certificate passes, it commits exactly the chronology-
gated opening live step and then stops; completing the remaining option is a
separate runner-integration gate.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STAGE0 = HERE.parent / "catfish-stage0"
SMC = HERE.parent / "smc-er-short-ep"
for path in (HERE, STAGE0, SMC, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_temporal_fork_core as core  # noqa: E402
import c2_temporal_fork_option_runner as option_runner  # noqa: E402
import c2_temporal_fork_selection as selection  # noqa: E402
import c2_temporal_fork_trainer_backend as backend  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    assert_ephemeris_matches_record,
)


USERS = 100
DEVELOPMENT_SEED = 2026082801
MAX_ANCHOR_STEP = 6


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _network_snapshot(trainer) -> tuple[dict[str, torch.Tensor], ...]:
    return tuple(
        {name: value.detach().cpu().clone() for name, value in net.state_dict().items()}
        for net in trainer.q_nets
    )


def _networks_equal(trainer, before: tuple[dict[str, torch.Tensor], ...]) -> bool:
    return all(
        all(torch.equal(net.state_dict()[name].detach().cpu(), value) for name, value in saved.items())
        for net, saved in zip(trainer.q_nets, before, strict=True)
    )


def _main_decision(trainer, wrapped, states, masks, observation, env_rng):
    branch = backend.C2ForecastBranch(
        wrapped=wrapped,
        env_rng=env_rng,
        mobility_rng=wrapped.environment._mobility_rng,
        states=list(states),
        masks=list(masks),
        observation=observation,
        trainer=trainer,
        focal_user=0,
        role="live-anchor-scan",
    )
    return backend._main_actions(trainer, branch)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "artifacts" / "c2-v03-real-backend-smoke-20260829.json",
    )
    parser.add_argument("--max-candidates", type=int, default=9)
    parser.add_argument("--commit-full-option", action="store_true")
    args = parser.parse_args()
    if args.max_candidates <= 0:
        raise ValueError("--max-candidates must be positive")

    record = read_prereg(REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json")
    archive = TleArchive(Path("/tmp/mcrl-tle-frozen-20260820-v1"))
    assert_ephemeris_matches_record(record, archive=archive)
    trainer, checkpoint = loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=REPO / "artifacts/training-2026-08-25-rerun01/main",
        users=USERS,
    )
    environment_source_sha256 = _code_sha256(_default_code_paths())
    reward_source_sha256 = _sha256(REPO / "src/mcrl/env/step.py")
    wrapped = loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, action_rng, _control_rng = loader._evaluation_rngs(
        DEVELOPMENT_SEED
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    network_before = _network_snapshot(trainer)
    replay_before = len(trainer.replay)
    candidates: list[dict[str, object]] = []
    selected_prepared = None
    prepared_candidates = []
    selection_result = None
    anchor_step = None
    departure_users: list[int] = []
    started = time.perf_counter()

    for _ in range(MAX_ANCHOR_STEP + 1):
        main_actions, main_physical = _main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        departure_users = []
        for uid, (incumbent, physical) in enumerate(
            zip(wrapped.environment._previous_association, main_physical, strict=True)
        ):
            if (
                isinstance(incumbent, Association)
                and physical is not None
                and physical != (int(incumbent.norad_id), int(incumbent.cell_id))
            ):
                departure_users.append(uid)
        if departure_users and 10 - int(observation.step_index) >= core.HOLD_STEPS + 1:
            anchor_step = int(observation.step_index)
            for uid in departure_users[: args.max_candidates]:
                row_started = time.perf_counter()
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
                        evaluation_seed=DEVELOPMENT_SEED,
                        focal_user=uid,
                    )
                    prepared = service.prepare_incumbent_hold(focal_user=uid)
                    built = prepared.run_forecast()
                    row = {
                        "focal_user": uid,
                        "candidate_key": list(prepared.candidate_key),
                        "passed": built.certificate.passed,
                        "failures": [failure.value for failure in built.certificate.failures],
                        "reference_bits": built.evidence.reference_useful_bits,
                        "candidate_bits": built.evidence.candidate_useful_bits,
                        "reference_energy_j": built.evidence.reference_energy_j,
                        "candidate_energy_j": built.evidence.candidate_energy_j,
                        "ee_surplus_bits": built.certificate.ee_surplus_bits,
                        "hold_r2_margin": built.certificate.hold_r2_margin,
                        "full_r2_margin": built.certificate.full_r2_margin,
                        "elapsed_s": time.perf_counter() - row_started,
                    }
                    candidates.append(row)
                    prepared_candidates.append(prepared)
                except Exception as error:  # fail closed, preserve diagnostic
                    candidates.append(
                        {
                            "focal_user": uid,
                            "passed": False,
                            "contract_error": f"{type(error).__name__}: {error}",
                            "elapsed_s": time.perf_counter() - row_started,
                        }
                    )
            break
        result = wrapped.step(main_actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation

    if prepared_candidates:
        selection_result = selection.select_prepared_fork(
            prepared_candidates,
            behavior_rng=action_rng,
            mode=selection.CHOICE_MODE_RANDOM,
            epsilon=0.0,
            preoutcome_timestamp_ns=time.time_ns(),
        )
        selected_prepared = selection_result.selected_prepared_fork

    live_receipt = None
    full_option_receipt = None
    if selected_prepared is not None and selection_result is not None:
        if args.commit_full_option:
            unit = option_runner.commit_prepared_option(
                selected_prepared,
                opening_behavior_probability=selection_result.behavior_probability,
                discount_factor=float(trainer.config.discount_factor),
                block_id=0,
                selection_receipt_sha256=selection_result.receipt.receipt_sha256,
            )
            opening_payload = unit.committed_payloads[0]
            live_receipt = {
                "action_indices": list(opening_payload.executed_actions),
                "physical_actions": [
                    None if key is None else list(key)
                    for key in opening_payload.executed_physical_actions
                ],
                "chronology_receipt_sha256": unit.closure.plan.chronology_receipt_sha256,
                "live_rng_unchanged_during_forecast": (
                    unit.chronology_receipt.live_rng_unchanged_during_forecast
                ),
                "forecast_sequence": list(unit.chronology_receipt.forecast_sequence),
            }
            full_option_receipt = {
                "admitted": unit.closure.plan.admitted,
                "disposition": unit.closure.plan.disposition,
                "committed_steps": len(unit.committed_payloads),
                "main_focal_actions": list(unit.closure.plan.main_focal_actions),
                "bundle_ids": list(unit.closure.plan.main_bundle_ids),
                "sequence_sha256": (
                    None if unit.sequence is None else unit.sequence.sequence_sha256
                ),
                "transition_sha256": (
                    None if unit.transition is None else unit.transition.sequence_sha256
                ),
                "q2f_bootstrap_discount": (
                    None if unit.transition is None else unit.transition.bootstrap_discount
                ),
                "termination_reason": unit.termination_reason,
            }
        else:
            live_step, receipt = selected_prepared.run_live_step()
            live_receipt = {
                "action_indices": list(live_step.action_indices),
                "physical_actions": [
                    None if key is None else list(key) for key in live_step.physical_actions
                ],
                "chronology_receipt_sha256": core._chronology_receipt_sha256(
                    receipt, certificate=selected_prepared.build.certificate
                ),
                "live_rng_unchanged_during_forecast": receipt.live_rng_unchanged_during_forecast,
                "forecast_sequence": list(receipt.forecast_sequence),
            }

    payload = {
        "schema": "c2-v03-real-backend-smoke-v1",
        "status": (
            "PASS"
            if selected_prepared is not None
            else "COMPLETE_NO_CERTIFIED_CANDIDATE"
        ),
        "claim_ceiling": backend.CLAIM_CEILING,
        "training_or_replay_write": False,
        "full_option_committed": bool(full_option_receipt is not None),
        "full_option": full_option_receipt,
        "evaluation_seed": DEVELOPMENT_SEED,
        "checkpoint_sha256": checkpoint["checkpoint_sha256"],
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "anchor_step": anchor_step,
        "departure_users": departure_users,
        "candidate_schedule": {
            "rule": "ascending_departure_user_incumbent_hold_only_no_early_stop",
            "cap": args.max_candidates,
            "scheduled_focal_users": departure_users[: args.max_candidates],
            "attempted_count": len(candidates),
            "forecast_complete_count": len(prepared_candidates),
        },
        "candidates": candidates,
        "selection": (
            None if selection_result is None else asdict(selection_result.receipt)
        ),
        "selected_live_opening": live_receipt,
        "main_networks_bitwise_unchanged": _networks_equal(trainer, network_before),
        "main_replay_length_before": replay_before,
        "main_replay_length_after": len(trainer.replay),
        "elapsed_s": time.perf_counter() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["main_networks_bitwise_unchanged"] and len(trainer.replay) == replay_before else 1


if __name__ == "__main__":
    raise SystemExit(main())
