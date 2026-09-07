#!/usr/bin/env python3
"""Bounded real-environment smoke for the C3 V3 shadow support bridge.

This is an engineering probe only.  It loads the corrected Main checkpoint,
resets one canonical 100-user environment, and asks the development-only
backend to scan at most one focal user and two current-table candidates.  It
does not train, write replay, route a transition, reveal a formal seed result,
or claim scientific efficacy.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

import c3_reward_aligned_v3_trainer_backend as backend  # noqa: E402
import run_c3_stage0 as legacy  # noqa: E402
import scripts.run_head_pivotality_probe as checkpoint_loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402


DEVELOPMENT_SEED = 2026082701
USERS = 100
CHECKPOINT_SHA256 = legacy.EXPECTED_CHECKPOINT_SHA256
DEFAULT_TLE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument("--steps-remaining", type=int, default=10)
    return parser.parse_args()


def _receipt_summary(result: backend.TrainerC3V3SupportScan) -> dict[str, Any]:
    return {
        "schema": result.schema,
        "status": result.status,
        "step_index": result.step_index,
        "steps_remaining": result.steps_remaining,
        "scanned_focal_users": list(result.scanned_focal_users),
        "scanned_candidates": result.scanned_candidates,
        "support_physical_ids_by_focal": {
            str(user): [list(value) for value in values]
            for user, values in result.support_physical_ids_by_focal.items()
        },
        "support_action_indices_by_focal": {
            str(user): {
                str(list(physical_id)): int(action)
                for physical_id, action in values.items()
            }
            for user, values in result.support_action_indices_by_focal.items()
        },
        "receipt_statuses_by_focal": {
            str(user): [receipt.status for receipt in receipts]
            for user, receipts in result.receipts_by_focal.items()
        },
        "receipt_reasons_by_focal": {
            str(user): [list(receipt.reasons) for receipt in receipts]
            for user, receipts in result.receipts_by_focal.items()
        },
        "candidate_wall_seconds_by_focal": {
            str(user): [float(value) for value in values]
            for user, values in result.candidate_wall_seconds_by_focal.items()
        },
        "fork_policy": (
            "each candidate certifies on two fresh branches made from the already "
            "materialized live anchor (no fresh-init+prefix replay is needed at the "
            "current anchor); immutable TLE archive is shared and no learner/replay "
            "state is written"
        ),
        "reasons": list(result.reasons),
        "claim_ceiling": result.claim_ceiling,
    }


def run_smoke(*, tle_root: Path, steps_remaining: int = 10) -> dict[str, Any]:
    if type(steps_remaining) is not int or steps_remaining < 0:
        raise ValueError("steps_remaining must be a nonnegative exact integer")

    started = time.perf_counter()
    prereg = read_prereg(REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json")
    with tempfile.TemporaryDirectory(prefix="c3-v3-trainer-backend-smoke-") as temporary:
        archive = checkpoint_loader._frozen_archive(
            prereg, tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = checkpoint_loader._verify_and_load_trainer(
            prereg,
            archive,
            run_dir=REPO / "artifacts/training-2026-08-25-rerun01/main",
            users=USERS,
        )
        if checkpoint["checkpoint_sha256"] != CHECKPOINT_SHA256:
            raise RuntimeError("corrected Main checkpoint digest changed")
        wrapped = checkpoint_loader._make_environment(archive, users=USERS)
        env_rng, mobility_rng, _action_rng, _control_rng = (
            checkpoint_loader._evaluation_rngs(DEVELOPMENT_SEED)
        )
        states, masks, observation = wrapped.reset(env_rng, mobility_rng)
        scan_started = time.perf_counter()
        result = backend.scan_current_support(
            wrapped=wrapped,
            states=states,
            masks=masks,
            observation=observation,
            env_rng=env_rng,
            trainer=trainer,
            checkpoint_sha256=CHECKPOINT_SHA256,
            steps_remaining=steps_remaining,
            max_focal_users=1,
            max_candidates_per_focal=2,
            scheduled_anchor=True,
        )
        scan_elapsed = time.perf_counter() - scan_started

    return {
        "schema": "smc-er-c3-v3-trainer-backend-development-smoke-v1",
        "status": "engineering_smoke_complete",
        "formal_seed_reveal": False,
        "scientific_pass": False,
        "training": False,
        "routing": False,
        "learner_updated": False,
        "development_seed": DEVELOPMENT_SEED,
        "users": USERS,
        "steps_remaining": steps_remaining,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "scan_wall_seconds": round(scan_elapsed, 6),
        "total_wall_seconds": round(time.perf_counter() - started, 6),
        "result": _receipt_summary(result),
        "claim_ceiling": (
            "engineering seam only; no formal C3 result, scientific efficacy, "
            "Main routing, deployment, or training authorization"
        ),
    }


def main() -> int:
    args = _arguments()
    payload = run_smoke(tle_root=args.tle_root, steps_remaining=args.steps_remaining)
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
