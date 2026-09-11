"""B0 pilot driver: a SHORT smoke/sanity run of the frozen MODQN recipe.

This is **not** an experimental arm and **not** a claim.  It trains the
frozen main-run recipe (PREREG-FROZEN-2026-08-25-R2, learning rate 0.001,
seeds train=42 / env=1337 / mobility=7) for a declared, short episode count
and keeps a loadable checkpoint every 100 episodes.

The ONLY departure from the frozen main-run config is ``episodes``.  The
epsilon schedule (``epsilon_decay_episodes``) is left at its frozen value, so
episode ``k`` of this run sees the same exploration rate as episode ``k`` of
the frozen 9,000-episode run -- which is what makes a same-episode-count
comparison against the frozen run's own episode logs meaningful.

It is deliberately code-agnostic: the same file drives the corrected tree
(B0) and the unfixed tree (the matched control), so the two runs differ in
the trainer code and in nothing the driver does.

Idempotent and resumable:
  * ``status.json`` with ``status == "complete"`` -> exit 0 immediately;
  * ``resume-checkpoint.pt`` whose fingerprint matches -> resume from it;
  * every 100 episodes: overwrite the resume checkpoint, write a PRESERVED
    ``checkpoint-epNNNNN.pt`` (loadable by ``MODQNTrainer.load_checkpoint``),
    rewrite ``episode-logs.json`` and ``status.json``.

Usage::

    run_b0_pilot.py --out-dir DIR --episodes 500 --label B0
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import torch  # noqa: E402

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.runtime import training_pipeline as tp  # noqa: E402

CANONICAL_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
CORRECTED_PROBE_SUMMARY = (
    REPO / "artifacts" / "probes-2026-08-25-rerun01" / "summary.json"
)
FROZEN_MAIN_LEARNING_RATE = 0.001
"""The frozen main run's learning rate, from its own status.json."""

CHECKPOINT_EVERY = 100


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, payload: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    tmp.replace(path)


def _rss_gb() -> float:
    try:
        with open("/proc/self/status") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return float("nan")


def _finite_log(row: dict) -> bool:
    def walk(value: object) -> bool:
        if isinstance(value, float):
            return math.isfinite(value)
        if isinstance(value, dict):
            return all(walk(item) for item in value.values())
        if isinstance(value, (list, tuple)):
            return all(walk(item) for item in value)
        return True

    return walk(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--label", type=str, required=True)
    parser.add_argument("--rss-cap-gb", type=float, default=5.0)
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=CHECKPOINT_EVERY,
        help="smoke runs only; the pilot uses the default of 100",
    )
    parser.add_argument(
        "--td-bootstrap-mode",
        default="eq16-per-head-max",
        help=(
            "eq16-per-head-max (DEFAULT, B1 baseline MODQN) or "
            "shared-continuation-argmax (successor target)"
        ),
    )
    parser.add_argument(
        "--local-smoke",
        action="store_true",
        help=(
            "SMOKE ONLY: skip the live-ephemeris-vs-frozen-record guard, which "
            "fails on a host whose TLE archive is not the frozen one.  The "
            "pilot itself must never pass this."
        ),
    )
    args = parser.parse_args()

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    status_path = out / "status.json"
    logs_path = out / "episode-logs.json"
    resume_path = out / "resume-checkpoint.pt"

    if status_path.is_file():
        previous = json.loads(status_path.read_text())
        if previous.get("status") == "complete":
            print(f"[{args.label}] already complete; nothing to do")
            return 0

    torch.set_num_threads(1)
    if args.local_smoke:
        record = tp.read_prereg(CANONICAL_PREREG)
    else:
        record = tp.validate_server_setup(
            CANONICAL_PREREG, probe_summary_path=CORRECTED_PROBE_SUMMARY
        )
    frozen_config = tp._trainer_config(
        record, learning_rate=FROZEN_MAIN_LEARNING_RATE
    )
    # Declared departures from the frozen main run: a short horizon, and the
    # TD-bootstrap mode (whose default IS the frozen eq. (16) behaviour).
    config = dataclasses.replace(
        frozen_config,
        episodes=int(args.episodes),
        td_bootstrap_mode=str(args.td_bootstrap_mode),
    )
    # Host pin (ruling 2026-09-11): refuse any archive but the frozen one.
    tle_file_set_sha256 = tp.assert_tle_archive_pinned()

    fingerprint = tp.build_run_fingerprint(
        record,
        role=f"b0-pilot-{args.label}-{args.episodes}ep-{args.td_bootstrap_mode}",
        learning_rate=FROZEN_MAIN_LEARNING_RATE,
        train_seed=tp.MAIN_TRAIN_SEED,
        env_seed=tp.MAIN_ENV_SEED,
        mobility_seed=tp.MAIN_MOBILITY_SEED,
    )

    environment = tp.make_training_environment(users=100)
    environment.assert_ready_to_train()
    trainer = MODQNTrainer(
        environment,
        config,
        train_seed=tp.MAIN_TRAIN_SEED,
        env_seed=tp.MAIN_ENV_SEED,
        mobility_seed=tp.MAIN_MOBILITY_SEED,
        device="cpu",
    )

    start_episode = 0
    initial_logs: list = []
    if resume_path.is_file():
        start_episode, initial_logs = tp._load_resume_checkpoint(
            resume_path,
            trainer=trainer,
            expected_fingerprint=fingerprint,
            expected_episodes=config.episodes,
        )
        print(f"[{args.label}] resuming at episode {start_episode}")

    observed = list(initial_logs)
    started = time.time()
    status = {
        "status": "running",
        "label": args.label,
        "episodes_target": config.episodes,
        "frozen_config_departure": {
            "episodes": [frozen_config.episodes, config.episodes],
            "td_bootstrap_mode": [
                frozen_config.td_bootstrap_mode, config.td_bootstrap_mode
            ],
        },
        "tle_root": str(tp.resolve_tle_root()),
        "tle_file_set_sha256": tle_file_set_sha256,
        "learning_rate": FROZEN_MAIN_LEARNING_RATE,
        "seeds": {
            "train": tp.MAIN_TRAIN_SEED,
            "environment": tp.MAIN_ENV_SEED,
            "mobility": tp.MAIN_MOBILITY_SEED,
        },
        "objective_weights": list(config.objective_weights),
        "reward_calibration_scales": list(config.reward_calibration_scales),
        "prereg_digest": record.digest,
        "run_fingerprint": fingerprint,
        "server_setup_validated": not args.local_smoke,
        "pid": os.getpid(),
        "started_utc": _utc(),
        "resumed_from_episode": start_episode,
        "checkpoints": {},
    }
    if status_path.is_file():
        try:
            prior = json.loads(status_path.read_text())
            status["checkpoints"] = dict(prior.get("checkpoints", {}))
        except (OSError, json.JSONDecodeError):
            pass
    _write_json(status_path, status)

    def observe(log) -> None:
        observed.append(log)
        episode_done = log.episode + 1
        row = asdict(log)
        if not _finite_log(row):
            raise FloatingPointError(
                f"non-finite value in episode {log.episode} log: {row}"
            )
        rss = _rss_gb()
        if rss > args.rss_cap_gb:
            raise MemoryError(f"RSS {rss:.2f} GB exceeds cap {args.rss_cap_gb}")
        if episode_done % args.checkpoint_every == 0:
            sha = tp._write_resume_checkpoint(
                resume_path,
                trainer=trainer,
                logs=observed,
                run_fingerprint=fingerprint,
            )
            preserved = out / f"checkpoint-ep{episode_done:05d}.pt"
            tmp = preserved.with_suffix(".pt.tmp")
            trainer.save_checkpoint(
                tmp,
                episode=log.episode,
                checkpoint_kind=config.checkpoint_primary_report,
                logs=observed,
            )
            tmp.replace(preserved)
            _write_json(logs_path, [asdict(item) for item in observed])
            status["checkpoints"][str(episode_done)] = {
                "path": str(preserved),
                "sha256": tp._file_sha256(preserved),
            }
            status.update({
                "episodes_completed": episode_done,
                "resume_checkpoint_sha256": sha,
                "episode_logs_sha256": tp._file_sha256(logs_path),
                "rss_gb": rss,
                "outage_user_steps_so_far": int(
                    sum(getattr(item, "outage_user_steps", 0) for item in observed)
                ),
                "wall_s": time.time() - started,
                "updated_utc": _utc(),
            })
            _write_json(status_path, status)
            print(
                f"[{args.label}] ep {episode_done} ckpt written; "
                f"rss {rss:.2f} GB; wall {time.time() - started:.0f}s",
                flush=True,
            )

    try:
        trainer.train(
            progress_every=50,
            start_episode=start_episode,
            initial_logs=initial_logs,
            episode_callback=observe,
        )
    except Exception as error:  # record, then re-raise
        status |= {
            "status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "episodes_observed": len(observed),
            "failed_utc": _utc(),
        }
        if observed:
            _write_json(logs_path, [asdict(item) for item in observed])
        _write_json(status_path, status)
        raise

    _write_json(logs_path, [asdict(item) for item in observed])
    status |= {
        "status": "complete",
        "episodes_completed": len(observed),
        "masking_diagnostics": trainer.get_masking_diagnostics(),
        "outage_user_steps_total": int(
            sum(getattr(item, "outage_user_steps", 0) for item in observed)
        ),
        "finished_utc": _utc(),
        "wall_s": time.time() - started,
        "episode_logs_sha256": tp._file_sha256(logs_path),
    }
    _write_json(status_path, status)
    print(f"[{args.label}] complete: {len(observed)} episodes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
