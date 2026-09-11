"""PENALTYARM greedy evaluation: pooled EE and service for each arm's pilot.

Harness and estimand REUSED, not reimplemented, from
`.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md` and the
script it ran (`anchor_ablation.py`):

  * ESTIMAND: pooled EE = **ratio of sums** -- two running totals, pooled
    decoded bits over pooled system joules, divided ONCE at the end.  Bits and
    joules are reported separately.  Per-episode ratios are kept only to give
    a sem; they are never the headline number.
  * `_age_rng` CONFOUND (surface doc, "Placebo" subsection): `StepEnvironment`
    spawns `_age_rng` from the env RNG on first reset (`env/step.py:534-536`)
    and carries it across episodes, so a SHARED environment gives whichever
    arm runs second different step-0 segment-age draws.  **Every cell here
    builds a FRESH environment**, so `_age_rng` is spawned from the same state
    in every cell and the arms are exactly matched.
  * dt = `DECISION_STEP_S`; bits and joules come from the env's own
    `energy.system_throughput_bps` / `system_consumed_power_w`, not
    reconstructed.

EVALUATION IS UNPENALISED AND UNPERTURBED.  The trainer is constructed with
the DEFAULT `PenaltyConfig()` (kind="none") whatever arm's weights it loads,
and `update()` is never called, so no penalty term and no gradient
perturbation can be active at evaluation time.  Greedy: epsilon = 0.

**500 EPISODES IS NOT CONVERGENCE.**  Every number below is a 500-episode
pilot checkpoint.  None of them may be compared against the 9000-episode
frozen checkpoint.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path


def _find_src() -> Path:
    for base in Path(__file__).resolve().parents:
        if (base / "src" / "mcrl").is_dir():
            return base / "src"
    raise SystemExit("could not locate src/mcrl above this script")


sys.path.insert(0, str(_find_src()))

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import HandoverClass
from mcrl.env.constants import DECISION_STEP_S
from mcrl.runtime.collapse_penalty import PenaltyConfig
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

DT = float(DECISION_STEP_S)
N_EP = 24  # same episode count as the surface doc's panel
TRAIN_SEED, ENV_SEED, MOBILITY_SEED = 42, 1337, 7


def evaluate(checkpoint: Path | None, n_ep: int = N_EP) -> dict:
    """One cell: fresh env, greedy (eps=0), no penalty, no perturbation."""
    env = make_training_environment(users=100)
    cfg = TrainerConfig(learning_rate=0.001, episodes=1)
    # Default PenaltyConfig => kind="none": inert at evaluation time.
    trainer = MODQNTrainer(
        env, cfg,
        train_seed=TRAIN_SEED, env_seed=ENV_SEED, mobility_seed=MOBILITY_SEED,
        penalty_config=PenaltyConfig(),
    )
    assert not trainer._penalty.active, "evaluation must be unpenalised"
    if checkpoint is not None:
        trainer.load_checkpoint(str(checkpoint), load_optimizers=False)

    users = env.config.num_users
    steps = env.config.steps_per_episode

    bits = joules = 0.0
    served = usersteps = 0
    ho_intra = ho_inter = 0
    beam_count_sum = 0.0
    beam_steps = 0
    ee_ep: list[float] = []

    for _ in range(n_ep):
        states, masks, _ = env.reset(trainer._env_rng, trainer._mobility_rng)
        enc = trainer._encode_states(states)
        eb = ej = 0.0
        for _t in range(steps):
            actions = trainer.select_actions(enc, masks, 0.0)  # GREEDY
            result = env.step(actions, trainer._env_rng)
            outcome = env.last_outcome
            e = outcome.energy
            eb += float(e.system_throughput_bps) * DT
            ej += float(e.system_consumed_power_w) * DT
            served += int(e.served)
            usersteps += users
            for cls in outcome.handovers:
                if cls is HandoverClass.INTRA_SATELLITE:
                    ho_intra += 1
                elif cls is HandoverClass.INTER_SATELLITE:
                    ho_inter += 1
            beam_count_sum += float(len(outcome.resolution.active_beams))
            beam_steps += 1
            states = result.user_states
            enc = trainer._encode_states(states)
            masks = result.action_masks
            if result.done:
                break
        bits += eb
        joules += ej
        ee_ep.append(eb / ej if ej > 0 else float("nan"))

    return {
        "episodes": n_ep,
        "pooled_bits": bits,
        "pooled_joules": joules,
        "pooled_ee_bit_per_j": bits / joules,
        "pooled_ee_sem": st.pstdev(ee_ep) / len(ee_ep) ** 0.5,
        "mean_of_episode_ratios": float(np.mean(ee_ep)),
        "served_fraction": served / usersteps,
        "handover_rate_total": (ho_intra + ho_inter) / usersteps,
        "handover_rate_intra_satellite": ho_intra / usersteps,
        "handover_rate_inter_satellite": ho_inter / usersteps,
        "mean_active_beams": beam_count_sum / beam_steps,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--arms", default="OFF,PENALTY,NULL_PENALTY")
    ap.add_argument("--checkpoint", default="checkpoint-ep00500.pt")
    ap.add_argument("--episodes", type=int, default=N_EP)
    ap.add_argument("--out", default="")
    ap.add_argument("--include-untrained", action="store_true",
                    help="also evaluate the untrained init as a floor")
    args = ap.parse_args()

    runs = Path(args.runs_dir)
    cells: list[tuple[str, Path | None]] = []
    if args.include_untrained:
        cells.append(("UNTRAINED_INIT", None))
    for arm in args.arms.split(","):
        cells.append((arm, runs / arm / args.checkpoint))

    print(f"# pooled EE = sum(bits)/sum(joules), divided once. "
          f"{args.episodes} episodes/cell, seeds (42/1337/7), dt={DT}s.")
    print("# greedy eps=0; penalty and perturbation INERT at evaluation time.")
    print("# fresh env per cell -> _age_rng matched across arms.")
    print("# 500 EPISODES IS NOT CONVERGENCE.\n")

    out: dict[str, dict] = {}
    t0 = time.time()
    for name, ckpt in cells:
        if ckpt is not None and not ckpt.is_file():
            print(f"{name:16s} MISSING {ckpt}")
            continue
        res = evaluate(ckpt, args.episodes)
        res["checkpoint"] = str(ckpt) if ckpt else "untrained-init"
        out[name] = res
        print(
            f"{name:16s} bits={res['pooled_bits']:.6e} "
            f"J={res['pooled_joules']:.6e} "
            f"EE={res['pooled_ee_bit_per_j']:,.2f} "
            f"sem={res['pooled_ee_sem']:,.1f} "
            f"served={res['served_fraction']:.4f} "
            f"ho={res['handover_rate_total']:.4f} "
            f"(intra {res['handover_rate_intra_satellite']:.4f} / "
            f"inter {res['handover_rate_inter_satellite']:.4f}) "
            f"beams={res['mean_active_beams']:.2f}",
            flush=True,
        )

    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"\n# wall {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
