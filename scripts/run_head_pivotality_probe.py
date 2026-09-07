#!/usr/bin/env python3
"""Run an evaluation-only Q2/Q3 head-pivotality checkpoint probe."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import statistics
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
)
from mcrl.env.mobility import MobilityConfig  # noqa: E402
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver  # noqa: E402
from mcrl.env.step import StepEnvironment  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.head_pivotality import (  # noqa: E402
    EFFECT_METRICS,
    HEAD_INDICES,
    run_head_pivotality_rollout,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS  # noqa: E402
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
    _trainer_config,
    assert_ephemeris_matches_record,
)


DEFAULT_INPUT = REPO / "artifacts" / "training-2026-08-25-rerun01"
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
DEFAULT_OUTPUT = (
    REPO
    / ".scratch"
    / "catfish-pivotality-probe"
    / "main-final-seed-2026082401.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _frozen_archive(record: Any, source_root: Path, target_root: Path) -> TleArchive:
    rows = record.sections["ephemeris"]["frozen_files"]
    target_root.mkdir(parents=True, exist_ok=False)
    for row in rows:
        source = source_root / str(row["file"])
        target = target_root / str(row["file"])
        if not source.is_file():
            raise RuntimeError(f"frozen TLE source file is missing: {source}")
        try:
            os.link(source, target)
        except OSError:
            target.symlink_to(source)
    archive = TleArchive(target_root)
    assert_ephemeris_matches_record(record, archive=archive)
    return archive


def _make_environment(archive: TleArchive, *, users: int) -> TrainerEnvironment:
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=users)),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def _verify_and_load_trainer(
    record: Any,
    archive: TleArchive,
    *,
    run_dir: Path,
    users: int,
) -> tuple[MODQNTrainer, dict[str, Any]]:
    status_path = run_dir / "status.json"
    checkpoint_path = run_dir / "final-checkpoint.pt"
    status = _read_json(status_path)
    if status.get("status") != "complete" or status.get("episodes_completed") != 9000:
        raise RuntimeError("main training status is not a complete 9000-episode run")
    if not checkpoint_path.is_file():
        raise RuntimeError(f"final checkpoint is missing: {checkpoint_path}")
    checkpoint_sha = _sha256(checkpoint_path)
    if checkpoint_sha != status.get("checkpoint_sha256"):
        raise RuntimeError("final checkpoint SHA-256 differs from status.json")
    if status.get("role") != "main-training":
        raise RuntimeError("checkpoint status is not the main-training role")

    checkpoint = read_checkpoint(checkpoint_path, map_location="cpu")
    seeds = status.get("seeds")
    if not isinstance(seeds, Mapping):
        raise RuntimeError("main status has no seed mapping")
    if (
        checkpoint.episode != 8999
        or checkpoint.train_seed != int(seeds["train"])
        or checkpoint.env_seed != int(seeds["environment"])
        or checkpoint.mobility_seed != int(seeds["mobility"])
    ):
        raise RuntimeError("checkpoint episode/seed metadata differs from status.json")

    environment = _make_environment(archive, users=users)
    trainer = MODQNTrainer(
        environment,
        _trainer_config(record, learning_rate=float(status["learning_rate"])),
        train_seed=int(seeds["train"]),
        env_seed=int(seeds["environment"]),
        mobility_seed=int(seeds["mobility"]),
        device="cpu",
    )
    loaded = trainer.load_checkpoint(checkpoint_path, load_optimizers=False)
    if loaded["episode"] != 8999:
        raise RuntimeError("loaded checkpoint is not the final episode")
    return trainer, {
        "status_path": str(status_path),
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "checkpoint_episode": int(checkpoint.episode),
        "training_role": status["role"],
        "training_seeds": dict(seeds),
        "learning_rate": float(status["learning_rate"]),
        "launched_code_sha256": status["run_fingerprint"]["code_sha256"],
    }


def _aggregate(rollouts: list[dict[str, Any]]) -> dict[str, Any]:
    all_steps = [step for rollout in rollouts for step in rollout["steps"]]
    decision_user_steps = sum(int(step["decision_users"]) for step in all_steps)
    heads: dict[str, Any] = {}
    for head in HEAD_INDICES:
        rows = [step["heads"][head] for step in all_steps]
        changed = [row for row in rows if row["physical_action_flips"]]

        def means(selected: list[dict[str, Any]]) -> dict[str, float]:
            if not selected:
                return {key: 0.0 for key in EFFECT_METRICS}
            return {
                key: float(
                    statistics.fmean(
                        float(row["full_minus_ablated"][key]) for row in selected
                    )
                )
                for key in EFFECT_METRICS
            }

        physical_flips = sum(int(row["physical_action_flips"]) for row in rows)
        heads[head] = {
            "total_action_index_flips": sum(
                int(row["action_index_flips"]) for row in rows
            ),
            "total_physical_action_flips": physical_flips,
            "total_index_only_flips": sum(int(row["index_only_flips"]) for row in rows),
            "physical_pivotality_rate": (
                float(physical_flips / decision_user_steps)
                if decision_user_steps
                else 0.0
            ),
            "steps_with_physical_flips": len(changed),
            "mean_full_minus_ablated": means(rows),
            "changed_steps_mean_full_minus_ablated": means(changed),
        }
    return {
        "evaluation_seeds": [int(row["evaluation_seed"]) for row in rollouts],
        "rollouts": len(rollouts),
        "steps": len(all_steps),
        "decision_user_steps": decision_user_steps,
        "heads": heads,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--users", type=int, default=100)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=[P6_EVALUATION_SEEDS[0]],
        help="matched evaluation seeds (default: first frozen P6 seed)",
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.users < 1:
        raise ValueError("--users must be positive")
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("--seeds must be unique")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")

    record = read_prereg(args.prereg)
    current_code_sha = _code_sha256(_default_code_paths())
    with tempfile.TemporaryDirectory(prefix="mcrl-head-pivotality-") as temporary:
        archive = _frozen_archive(
            record, args.tle_root, Path(temporary) / "frozen-tle"
        )
        run_dir = args.input_dir / "main"
        trainer, checkpoint_receipt = _verify_and_load_trainer(
            record, archive, run_dir=run_dir, users=args.users
        )
        rollouts = []
        for seed in args.seeds:
            environment = _make_environment(archive, users=args.users)
            env_rng, mobility_rng, _action_rng, _perturb_rng = _evaluation_rngs(seed)
            rollouts.append(
                run_head_pivotality_rollout(
                    trainer,
                    environment,
                    evaluation_seed=seed,
                    env_rng=env_rng,
                    mobility_rng=mobility_rng,
                )
            )

    payload = {
        "schema": "mcrl-head-pivotality-receipt-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "mode": "evaluation-only; no optimizer or training update",
        "prereg_path": str(args.prereg),
        "prereg_digest": record.digest,
        "prereg_file_sha256": _sha256(args.prereg),
        "tle_root": str(args.tle_root),
        "frozen_tle_contract_verified": True,
        "users": int(args.users),
        "checkpoint": checkpoint_receipt,
        "analysis_code_sha256": current_code_sha,
        "analysis_source_matches_training": (
            current_code_sha == checkpoint_receipt["launched_code_sha256"]
        ),
        "analysis_source_drift_reason": (
            "evaluation-only non-mutating counterfactual seam and head-pivotality "
            "reporter added after training; checkpoint weights and deployed reward "
            "configuration are loaded unchanged"
        ),
        "common_random_number_contract": (
            "every full/Q2-removed/Q3-removed action vector is evaluated from the "
            "same current environment state and an identical copy of the pre-step "
            "environment RNG; only the full action advances the episode"
        ),
        "baseline_preview_equals_committed_step_every_time": True,
        "aggregate": _aggregate(rollouts),
        "rollouts": rollouts,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
