#!/usr/bin/env python3
"""One-anchor engineering smoke for the capped C2 V3 support provider."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import c2_activation_churn_dev_support as support  # noqa: E402
import c2_activation_churn_runtime_adapter as adapter  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.env.action_contract import Association  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import assert_ephemeris_matches_record  # noqa: E402


USERS = 100
DEVELOPMENT_SEED = 2026082801


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    record = read_prereg(REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json")
    archive = TleArchive(Path("/tmp/mcrl-tle-frozen-20260820-v1"))
    assert_ephemeris_matches_record(record, archive=archive)
    trainer, checkpoint = loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=REPO / "artifacts/training-2026-08-25-rerun01/main",
        users=USERS,
    )
    wrapped = loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
        DEVELOPMENT_SEED
    )
    episode_env_rng = copy.deepcopy(env_rng)
    episode_mobility_rng = copy.deepcopy(mobility_rng)
    environment_training_state = copy.deepcopy(wrapped.training_state_dict())
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    prefix_actions: list[tuple[int, ...]] = []
    scanned = None
    scanned_step = None
    departure_users = 0
    for _ in range(7):
        decision = adapter.scalarized_main_decision(
            trainer,
            states,
            masks,
            slot_tables=observation.candidates.slot_tables,
        )
        assert decision.physical_actions is not None
        departure_users = sum(
            isinstance(incumbent, Association)
            and action is not None
            and action
            != (int(incumbent.norad_id), int(incumbent.cell_id))
            for incumbent, action in zip(
                wrapped.environment._previous_association,
                decision.physical_actions,
                strict=True,
            )
        )
        if departure_users and 10 - int(observation.step_index) >= 4:
            scanned_step = int(observation.step_index)
            scan_started = time.perf_counter()
            scanned = support.scan_c2_development_support(
                trainer,
                wrapped=wrapped,
                env_rng=env_rng,
                states=states,
                masks=masks,
                observation=observation,
                steps_remaining=10 - int(observation.step_index),
                replay_authority=support.EpisodeReplayAuthority(
                    environment_factory=lambda: loader._make_environment(
                        archive, users=USERS
                    ),
                    episode_env_rng=episode_env_rng,
                    episode_mobility_rng=episode_mobility_rng,
                    environment_training_state=environment_training_state,
                    prefix_actions=tuple(prefix_actions),
                ),
                max_focal_users=9,
                max_candidates_per_focal=8,
            )
            scan_elapsed_s = time.perf_counter() - scan_started
            break
        actions = np.asarray(decision.actions, dtype=np.int32)
        prefix_actions.append(tuple(int(value) for value in actions.tolist()))
        result = wrapped.step(actions, env_rng)
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = wrapped.last_outcome.observation
    if scanned is None:
        raise RuntimeError("development smoke found no scalarized-Main departure anchor")
    payload = {
                "schema": "c2-activation-churn-development-smoke-v1",
                "status": "complete",
                "scientific_pass": False,
                "routing": False,
                "checkpoint_sha256": checkpoint["checkpoint_sha256"],
                "development_seed": DEVELOPMENT_SEED,
                "step": scanned_step,
                "scan_elapsed_s": scan_elapsed_s,
                "departure_users": departure_users,
                "scanned_candidates": scanned.scanned_candidates,
                "certified_candidates": sum(
                    int(receipt.certified) for receipt in scanned.receipts
                ),
                "receipts": [
                    {
                        "focal_user": row.focal_user,
                        "candidate_id": list(row.candidate_id),
                        "certified": row.certified,
                        "first_failed_layer": row.first_failed_layer,
                        "reasons": list(row.reasons),
                        "hold_system_r2_delta": row.hold_system_r2_delta,
                        "full_system_r2_delta": row.full_system_r2_delta,
                    }
                    for row in scanned.receipts
                ],
            }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
