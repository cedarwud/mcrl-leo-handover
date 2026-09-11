"""CAPPENALTY 500-episode pilot driver: one arm per invocation, detached.

A copy of PENALTYARM's ``penalty-arm/run_penalty_pilot.py`` with exactly two
changes: (1) the environment is ``make_capped_training_environment`` with
``beam_cap=3`` for the CAP3 arms -- A PHYSICS CHANGE, A DIFFERENT MDP; (2) the
per-episode row also persists the trainer's own training-time G-3 samples
(``collapse_first`` / ``collapse_last``).  Penalty construction, seeds, lr,
checkpoint cadence and the srank_delta diagnostic are PENALTYARM's, unchanged.

Usage:
  python run_cap_pilot.py --arm CAP3_OFF     --out runs/CAP3_OFF
  python run_cap_pilot.py --arm CAP3_PENALTY --out runs/CAP3_PENALTY

500 EPISODES IS NOT CONVERGENCE.  The frozen reference run is 9000 episodes.
Nothing produced here may be compared against a 9000-episode checkpoint.

Checkpoints every 100 episodes (``--checkpoint-every``), plus a final one.
Per-episode logs and per-episode penalty statistics are flushed at the same
cadence so an interruption resumes from the last durable checkpoint.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

def _find_src() -> Path:
    """Locate the tree's ``src/mcrl``: the local repo and the server workspace
    put this script at different depths, and the server's main checkout has a
    stale editable install, so the path must be pinned explicitly."""
    for base in Path(__file__).resolve().parents:
        candidate = base / "src" / "mcrl"
        if candidate.is_dir():
            return base / "src"
    raise SystemExit("could not locate src/mcrl above this script")


sys.path.insert(0, str(_find_src()))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.runtime.collapse_penalty import PenaltyConfig, preset_config
from mcrl.runtime.trainer_spec import TrainerConfig
from dataclasses import asdict

from beam_cap import make_capped_training_environment

# The cap value, matching the sibling's k_cap default (family_b_step.py:86).
BEAM_CAP_K = 3
ARM_TO_PENALTY_ARM = {"CAP3_OFF": "OFF", "CAP3_PENALTY": "PENALTY"}

# Frozen seeds, the same triple every other measurement on this harness uses.
TRAIN_SEED, ENV_SEED, MOBILITY_SEED = 42, 1337, 7
# Ruling C-13 makes learning_rate a controlled variable with no default; the
# main frozen run used 0.001, so the pilot uses 0.001.  Declared, not tuned.
LEARNING_RATE = 0.001
# The one preset run as the PENALTY arm.  Kumar's alpha verbatim (1e-3) and
# the sibling's own code default.  Declared before the run; no sweeping.
PENALTY_PRESET = "TB-SRANK-kumar"


def build_penalty(arm: str, null_norms: tuple[float, float, float]) -> PenaltyConfig:
    if arm == "OFF":
        # kind="none": no loss term, no perturbation.  Bit-identical to the
        # pre-port trainer; diagnostics are read-only and consume no RNG.
        return PenaltyConfig(diagnostics=True)
    if arm == "PENALTY":
        return preset_config(PENALTY_PRESET, diagnostics=True)
    if arm == "NULL_PENALTY":
        return PenaltyConfig(
            kind="null_grad",
            null_grad_norms=null_norms,
            diagnostics=True,
            preset="matched-to-PENALTY-measured-gradient-norm",
        )
    raise SystemExit(f"unknown arm {arm!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True,
                    choices=tuple(ARM_TO_PENALTY_ARM))
    ap.add_argument("--out", required=True)
    ap.add_argument("--episodes", type=int, default=500)
    ap.add_argument("--checkpoint-every", type=int, default=100)
    ap.add_argument("--null-grad-norms", default="0,0,0")
    args = ap.parse_args()

    torch.set_num_threads(1)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    norms = tuple(float(x) for x in args.null_grad_norms.split(","))
    assert len(norms) == 3
    penalty = build_penalty(ARM_TO_PENALTY_ARM[args.arm], norms)

    env = make_capped_training_environment(users=100, beam_cap=BEAM_CAP_K)
    assert env.environment.beam_cap == BEAM_CAP_K
    env.assert_ready_to_train()
    cfg = TrainerConfig(learning_rate=LEARNING_RATE, episodes=args.episodes)
    trainer = MODQNTrainer(
        env, cfg,
        train_seed=TRAIN_SEED, env_seed=ENV_SEED, mobility_seed=MOBILITY_SEED,
        penalty_config=penalty,
    )

    manifest = {
        "arm": args.arm,
        "episodes": args.episodes,
        "checkpoint_every": args.checkpoint_every,
        "learning_rate": LEARNING_RATE,
        "seeds": {"train": TRAIN_SEED, "env": ENV_SEED,
                  "mobility": MOBILITY_SEED},
        "penalty": {
            "kind": penalty.kind,
            "coefficient": penalty.coefficient,
            "preset": penalty.preset,
            "null_grad_norms": list(penalty.null_grad_norms),
            "diagnostics": penalty.diagnostics,
        },
        "beam_cap_k": BEAM_CAP_K,
        "PHYSICS_CHANGE": "per-satellite active-beam cap; a different MDP",
        "pid": os.getpid(),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "NOT_CONVERGENCE": "500 episodes is a pilot, not a converged run",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    episode_rows: list[dict] = []
    t0 = time.time()

    def flush() -> None:
        (out / "episode-logs.json").write_text(
            json.dumps(episode_rows, indent=1) + "\n"
        )

    def on_episode(log) -> None:
        stats = trainer.drain_penalty_stats()
        row = {
            "episode": log.episode,
            "epsilon": log.epsilon,
            "r1_mean": log.r1_mean,
            "r2_mean": log.r2_mean,
            "r3_mean": log.r3_mean,
            # The three CALIBRATED head means -- the quantity training uses.
            "r1_mean_calibrated": log.r1_mean_calibrated,
            "r2_mean_calibrated": log.r2_mean_calibrated,
            "r3_mean_calibrated": log.r3_mean_calibrated,
            "scalar_reward_raw": log.scalar_reward,
            "total_handovers": log.total_handovers,
            "replay_size": log.replay_size,
            "td_losses": list(log.losses),
            "penalty": stats,
            "g3_train_first": asdict(log.collapse_first)
            if log.collapse_first is not None else None,
            "g3_train_last": asdict(log.collapse_last)
            if log.collapse_last is not None else None,
        }
        episode_rows.append(row)
        n = log.episode + 1
        if n % args.checkpoint_every == 0 or n == args.episodes:
            trainer.save_training_state(out / f"state-ep{n:05d}.pt")
            trainer.save_checkpoint(
                out / f"checkpoint-ep{n:05d}.pt",
                episode=log.episode,
                checkpoint_kind="pilot-periodic",
            )
            flush()
            print(
                f"[{args.arm}] ep {n}/{args.episodes} "
                f"eps={log.epsilon:.4f} "
                f"cal=({log.r1_mean_calibrated:+.4f},"
                f"{log.r2_mean_calibrated:+.4f},{log.r3_mean_calibrated:+.4f}) "
                f"td={log.losses[0]:.4g} "
                f"pen_raw={stats['penalty_raw_mean'][0]:.4g} "
                f"pen_gn={stats['penalty_grad_norm_mean'][0]:.4g} "
                f"srank={stats['srank_diagnostic_mean']} "
                f"wall={time.time() - t0:.0f}s",
                flush=True,
            )

    trainer.train(progress_every=100, episode_callback=on_episode)
    flush()
    trainer.save_checkpoint(
        out / "final-checkpoint.pt",
        episode=args.episodes - 1,
        checkpoint_kind="pilot-final",
    )
    manifest["finished_utc"] = time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
    )
    manifest["wall_seconds"] = time.time() - t0
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"[{args.arm}] DONE wall={time.time() - t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
