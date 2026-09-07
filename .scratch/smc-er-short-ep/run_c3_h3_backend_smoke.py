#!/usr/bin/env python3
"""Bounded live engineering smoke for the real C3 H3 TrainerEnvironment seam.

This is deliberately a development-only receipt.  It uses the existing
development seed ``2026082701`` and the corrected Main checkpoint, scans only
the first small pre-outcome support encountered, and calls
``certify_h3_candidate`` for at most a few physical destinations.  It never
loads a C3 seed manifest, routes a transition, updates a learner, or reports a
scientific/pass result.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

import c3_h3_runtime_adapter as h3  # noqa: E402
import c3_h3_trainer_backend as backend_module  # noqa: E402
import run_c3_stage0 as legacy  # noqa: E402
import scripts.run_head_pivotality_probe as checkpoint_loader  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402


DEVELOPMENT_SEED = 2026082701
USERS = 100
DEFAULT_MAX_STEPS = 4
DEFAULT_MAX_CANDIDATES = 3
CHECKPOINT_SHA256 = legacy.EXPECTED_CHECKPOINT_SHA256
DEFAULT_TLE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tle-root", type=Path, default=DEFAULT_TLE_ROOT)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument(
        "--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _prefix_tuple(prefix: list[np.ndarray]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(int(value) for value in np.asarray(actions, dtype=np.int32).tolist())
        for actions in prefix
    )


def _anchor_for_branch(
    backend: backend_module.TrainerEnvironmentH3Backend,
    *,
    seed: int,
    step_index: int,
    focal_user_id: int,
    source_id: tuple[int, int],
    prefix_actions: list[np.ndarray],
) -> h3.PreOutcomeAnchor:
    provisional = h3.PreOutcomeAnchor(
        checkpoint_sha256=CHECKPOINT_SHA256,
        # A provisional value is used only to reconstruct the branch.  The
        # bound anchor below replaces it with the backend's fresh fingerprint.
        expected_anchor_fingerprint_sha256="c" * 64,
        evaluation_seed=seed,
        step_index=step_index,
        focal_user_id=focal_user_id,
        source_id=source_id,
        prefix_actions=_prefix_tuple(prefix_actions),
    )
    branch = backend.replay_prefix(provisional)
    return replace(
        provisional,
        expected_anchor_fingerprint_sha256=backend.fingerprint(branch),
    )


def _receipt_summary(receipt: h3.H3AdapterReceipt) -> dict[str, Any]:
    evidence = receipt.candidate_evidence
    return {
        "status": receipt.status,
        "certified": bool(receipt.certified),
        "candidate_id": (
            None if receipt.candidate_id is None else list(receipt.candidate_id)
        ),
        "source_id": None if receipt.source_id is None else list(receipt.source_id),
        "reasons": list(receipt.reasons),
        "intervals": len(receipt.intervals),
        "nonfocal_equality_by_interval": list(
            receipt.nonfocal_equality_by_interval
        ),
        "fresh_branches": bool(receipt.replayed_fresh_branches),
        "distinct_forecast_rng_objects": bool(
            receipt.forecast_rng_objects_distinct
        ),
        "candidate_evidence": (
            None
            if evidence is None
            else {
                "hard_safe": bool(evidence.hard_safe),
                "strict_load": bool(evidence.strict_load),
                "persistent_power": bool(evidence.persistent_power),
                "joint": bool(evidence.joint),
                "reasons": list(evidence.reasons),
                "load_gap_score": int(evidence.load_gap_score),
                "power_relief_j": float(evidence.power_relief_j),
            }
        ),
    }


def _strict_load_candidates(
    baseline: Any,
    *,
    source_id: tuple[int, int],
    candidate_ids: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    """Keep only current-anchor moves with a strict canonical-R3 gain."""

    loads = {
        (int(key[0]), int(key[1])): int(value)
        for key, value in baseline.resolution.eligible_load_by_beam.items()
    }
    source_load = loads.get(source_id, 0)
    return tuple(
        candidate_id
        for candidate_id in candidate_ids
        if loads.get(candidate_id, 0) > 0
        and h3.core.strict_load_improvement(
            source_load, loads.get(candidate_id, 0)
        )
    )


def run_smoke(
    *,
    tle_root: Path,
    max_steps: int = DEFAULT_MAX_STEPS,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> dict[str, Any]:
    if type(max_steps) is not int or not 1 <= max_steps <= len(legacy.ANCHOR_STEPS):
        raise ValueError("max_steps must be an exact integer in [1,8]")
    if type(max_candidates) is not int or not 1 <= max_candidates <= 8:
        raise ValueError("max_candidates must be an exact integer in [1,8]")

    prereg = read_prereg(REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json")
    with tempfile.TemporaryDirectory(prefix="c3-h3-backend-smoke-") as temporary:
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
        environment = wrapped.environment
        env_rng, mobility_rng, _action_rng, _control_rng = (
            checkpoint_loader._evaluation_rngs(DEVELOPMENT_SEED)
        )
        states, masks, observation = wrapped.reset(env_rng, mobility_rng)
        backend = backend_module.TrainerEnvironmentH3Backend(archive, trainer)
        prefix: list[np.ndarray] = []
        step_receipts: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None

        for _ in range(max_steps):
            mask_block = np.stack([row.mask for row in masks])
            q_values = trainer.scalarized_q_values(
                trainer.encode_states(states),
                objective_weights=backend_module.MAIN_BEHAVIOR_WEIGHTS,
            )
            actions = legacy.masked_greedy_actions(q_values, mask_block)
            # Current-slot support is a pre-outcome scan.  Match the sealed
            # C3 reference path by evaluating it with fading disabled; using
            # the live fading draw here would let an unavailable stochastic
            # outcome decide which anchor enters the support.
            original_physics = environment.physics
            environment.physics = replace(original_physics, fading_enabled=False)
            try:
                baseline = environment.evaluate_actions(actions, env_rng)
            finally:
                environment.physics = original_physics
            baseline_keys = legacy._physical_key_rows(actions, observation)
            anchor_mapping = {
                "wrapped": wrapped,
                "states": states,
                "masks": masks,
                "observation": observation,
            }

            qualified: list[tuple[int, tuple[int, int], tuple[tuple[int, int], ...], dict[str, Any]]] = []
            strict_qualified = 0
            for focal_user in range(USERS):
                source_row, candidate_keys = legacy._source_qualification(
                    anchor_mapping,
                    trainer,
                    focal_user=focal_user,
                    baseline_actions=actions,
                    baseline=baseline,
                    baseline_keys=baseline_keys,
                )
                if not candidate_keys:
                    continue
                source = baseline_keys[focal_user]
                if source is None:
                    continue
                strict_candidate_keys = _strict_load_candidates(
                    baseline,
                    source_id=source,
                    candidate_ids=tuple(candidate_keys),
                )
                if not strict_candidate_keys:
                    continue
                strict_qualified += 1
                scan_rows, hard_safe_keys = legacy._hard_safe_candidates(
                    anchor_mapping,
                    focal_user=focal_user,
                    source_key=source,
                    baseline_actions=actions,
                    baseline=baseline,
                    candidate_keys=strict_candidate_keys[:max_candidates],
                )
                qualified.append(
                    (
                        focal_user,
                        source,
                        tuple(strict_candidate_keys[:max_candidates]),
                        source_row,
                    )
                )
                if selected is None and hard_safe_keys:
                    selected = {
                        "step_index": int(observation.step_index),
                        "focal_user": int(focal_user),
                        "source_id": list(source),
                        "source_row": source_row,
                        "scan_rows": scan_rows,
                        "hard_safe_ids": [list(key) for key in hard_safe_keys],
                        "candidate_ids_scanned": [
                            list(key)
                            for key in strict_candidate_keys[:max_candidates]
                        ],
                        "prefix_actions": prefix.copy(),
                    }
                    selected["anchor"] = _anchor_for_branch(
                        backend,
                        seed=DEVELOPMENT_SEED,
                        step_index=int(observation.step_index),
                        focal_user_id=focal_user,
                        source_id=source,
                        prefix_actions=prefix,
                    )
                    selected["candidate_ids"] = [
                        tuple(key) for key in hard_safe_keys
                    ][:max_candidates]
                    break

            step_receipts.append(
                {
                    "step_index": int(observation.step_index),
                    "served": int(baseline.resolution.served_count),
                    "source_qualified": len(qualified),
                    "strict_load_source_qualified": strict_qualified,
                }
            )
            if selected is not None:
                break
            result = wrapped.step(actions, env_rng)
            if result.done:
                break
            prefix.append(np.asarray(actions, dtype=np.int32).copy())
            states, masks = result.user_states, result.action_masks
            observation = wrapped.last_outcome.observation

        if selected is None:
            raise RuntimeError(
                "development smoke found no source-qualified pre-outcome support "
                f"within {max_steps} steps"
            )

        anchor = selected["anchor"]
        receipts: list[dict[str, Any]] = []
        for candidate_id in selected["candidate_ids"]:
            receipt = h3.certify_h3_candidate(
                backend,
                anchor=anchor,
                candidate_id=candidate_id,
                expected_user_count=USERS,
            )
            summary = _receipt_summary(receipt)
            receipts.append(summary)
            if receipt.status == "FAIL_CLOSED":
                raise RuntimeError(
                    "real TrainerEnvironment H3 backend failed closed: "
                    + "; ".join(receipt.reasons)
                )

    return {
        "schema": "smc-er-c3-h3-trainer-backend-development-smoke-v1",
        "status": "engineering_smoke_complete",
        "formal_seed_reveal": False,
        "scientific_pass": False,
        "routing": False,
        "learner_updated": False,
        "development_seed": DEVELOPMENT_SEED,
        "users": USERS,
        "max_steps": max_steps,
        "max_candidates": max_candidates,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "steps_scanned": step_receipts,
        "selected_anchor": {
            key: value
            for key, value in selected.items()
            if key not in {"anchor", "prefix_actions"}
        },
        "certificates": receipts,
        "claim_ceiling": (
            "engineering seam only; no formal C3 result, scientific efficacy, "
            "Main-routing, or deployment authorization"
        ),
    }


def main() -> int:
    args = _arguments()
    payload = run_smoke(
        tle_root=args.tle_root,
        max_steps=args.max_steps,
        max_candidates=args.max_candidates,
    )
    serialized = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        output = args.output.expanduser().resolve()
        if output.is_relative_to(REPO.resolve()):
            raise RuntimeError("development smoke receipt must live outside the repository")
        if output.exists():
            raise FileExistsError(f"refusing to overwrite {output}")
        output.write_text(serialized, encoding="utf-8")
        print(output)
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
