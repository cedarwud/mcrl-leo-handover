"""CAPPENALTY re-run at larger n: why does the cap move pooled EE?

Triggered by a surprise (declared in the report): coordinator erratum 28 says
beam count cancels at first order on this harness (EE ~ B x SE / power per
beam), yet the 24-episode evaluation measured CAP3 EE well above uncapped.
This script re-evaluates at n = 96 episodes (the first 24 are the same
episodes as the main evaluation, by construction of the RNG streams; the
other 72 are new) and decomposes pooled EE into

    EE = (bits per beam-step) / (joules per beam-step)

with bits per beam-step further read through the served users' spectral
efficiency log2(1 + SINR), their SINR and their interference power.  Same
harness as eval_cap_cells.py: fresh env per cell, greedy, unpenalised.
Read-only on everything; consumes no RNG beyond the rollout itself.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _find_src() -> Path:
    for base in Path(__file__).resolve().parents:
        if (base / "src" / "mcrl").is_dir():
            return base / "src"
    raise SystemExit("could not locate src/mcrl above this script")


sys.path.insert(0, str(_find_src()))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.constants import DECISION_STEP_S
from mcrl.runtime.collapse_penalty import PenaltyConfig
from mcrl.runtime.trainer_spec import TrainerConfig

from beam_cap import make_capped_training_environment

DT = float(DECISION_STEP_S)
PENALTYARM_RUNS = Path("/home/sat/mcrl-v025-penalty-arm-ws/runs")


def run(checkpoint: Path, beam_cap, n_ep: int) -> dict:
    env = make_capped_training_environment(users=100, beam_cap=beam_cap)
    trainer = MODQNTrainer(env, TrainerConfig(learning_rate=0.001, episodes=1),
                           train_seed=42, env_seed=1337, mobility_seed=7,
                           penalty_config=PenaltyConfig())
    trainer.load_checkpoint(str(checkpoint), load_optimizers=False)
    steps = env.config.steps_per_episode
    bits = joules = fixed_j = 0.0
    beam_steps = served_steps = 0
    se_sum = sinr_db_sum = interf_sum = wanted_sum = 0.0
    beam_mean_se_sum = 0.0
    ee_first24_bits = ee_first24_j = 0.0
    for ep in range(n_ep):
        states, masks, _ = env.reset(trainer._env_rng, trainer._mobility_rng)
        enc = trainer._encode_states(states)
        for _t in range(steps):
            actions = trainer.select_actions(enc, masks, 0.0)
            result = env.step(actions, trainer._env_rng)
            o = env.last_outcome
            b = float(o.energy.system_throughput_bps) * DT
            j = float(o.energy.system_consumed_power_w) * DT
            bits += b
            joules += j
            if ep < 24:
                ee_first24_bits += b
                ee_first24_j += j
            fixed_j += float(o.fixed_power_w) * DT
            res = o.resolution
            served = np.asarray(res.served, dtype=bool)
            sinr = np.asarray(o.link_sinr, dtype=np.float64)
            se = np.log2(1.0 + sinr)
            itot = np.asarray(o.interference.total_w, dtype=np.float64)
            served_steps += int(served.sum())
            se_sum += float(se[served].sum())
            sinr_db_sum += float((10.0 * np.log10(np.maximum(sinr[served], 1e-300))).sum())
            interf_sum += float(itot[served].sum())
            beams: dict[tuple[int, int], list[float]] = {}
            for uid in np.flatnonzero(served):
                key = (int(res.serving_satellite[uid]), int(res.serving_cell[uid]))
                beams.setdefault(key, []).append(float(se[uid]))
            beam_steps += len(beams)
            beam_mean_se_sum += float(sum(np.mean(v) for v in beams.values()))
            states = result.user_states
            enc = trainer._encode_states(states)
            masks = result.action_masks
            if result.done:
                break
    return {
        "checkpoint": str(checkpoint), "beam_cap": beam_cap, "episodes": n_ep,
        "pooled_bits": bits, "pooled_joules": joules,
        "pooled_ee_bit_per_j": bits / joules,
        "pooled_ee_first24_episodes": ee_first24_bits / ee_first24_j,
        "fixed_joules": fixed_j,
        "beam_steps": beam_steps, "served_user_steps": served_steps,
        "bits_per_beam_step": bits / beam_steps,
        "joules_per_beam_step": joules / beam_steps,
        "served_users_per_beam": served_steps / beam_steps,
        "mean_se_served_user_bit_per_hz": se_sum / served_steps,
        "mean_of_beam_mean_se_bit_per_hz": beam_mean_se_sum / beam_steps,
        "mean_sinr_db_served_user": sinr_db_sum / served_steps,
        "mean_interference_w_served_user": interf_sum / served_steps,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="OFFw_nocap,OFFw_cap3,CAP3w_cap3,CAP3w_nocap")
    ap.add_argument("--episodes", type=int, default=96)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    spec = {
        "OFFw_nocap": (PENALTYARM_RUNS / "OFF" / "checkpoint-ep00500.pt", None),
        "OFFw_cap3": (PENALTYARM_RUNS / "OFF" / "checkpoint-ep00500.pt", 3),
        "CAP3w_cap3": (Path("runs/CAP3_OFF/checkpoint-ep00500.pt"), 3),
        "CAP3w_nocap": (Path("runs/CAP3_OFF/checkpoint-ep00500.pt"), None),
    }
    out = {}
    t0 = time.time()
    for name in args.cells.split(","):
        ck, cap = spec[name]
        r = run(ck, cap, args.episodes)
        out[name] = r
        print(f"{name:12s} EE={r['pooled_ee_bit_per_j']:,.2f} (first24 {r['pooled_ee_first24_episodes']:,.2f}) "
              f"bits={r['pooled_bits']:.6e} J={r['pooled_joules']:.6e} "
              f"bits/beam-step={r['bits_per_beam_step']:.4e} J/beam-step={r['joules_per_beam_step']:.2f} "
              f"users/beam={r['served_users_per_beam']:.3f} SE_user={r['mean_se_served_user_bit_per_hz']:.4f} "
              f"SE_beam={r['mean_of_beam_mean_se_bit_per_hz']:.4f} SINRdB={r['mean_sinr_db_served_user']:.3f} "
              f"I_W={r['mean_interference_w_served_user']:.4e} fixedJ={r['fixed_joules']:.4e}",
              flush=True)
        Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"# wall {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
