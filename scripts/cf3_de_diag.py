"""CF3PILOT no-training diagnostic (Amendment 1 item 7): the local energy
contrast C3 actually offers.

Roll out C3 (B1_NO_NEW_BEAM) on calibration episodes (per-episode reseeded).
At every step, for every user whose incumbent is legal and differs from C3's
choice, evaluate the step twice with the environment's counterfactual
``evaluate_actions`` (common random numbers, no state committed): C3's action
vector, and the same vector with that one user moved back to its incumbent.
dE_sys = E(C3 choice) - E(incumbent), joules per step.  Reported only.

Usage: cf3_de_diag.py --out FILE [--episodes 3]
"""

from __future__ import annotations

import argparse
import time

import cf3_common as C

import numpy as np
import torch

from mcrl.algorithms import cf_sources as cfs
from mcrl.algorithms.cf_ratio import DT_S
from mcrl.runtime import training_pipeline as tp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--episodes", type=int, default=3)
    a = ap.parse_args()
    torch.set_num_threads(1)
    tle = tp.assert_tle_archive_pinned()
    factory = C.env_factory()
    rule = cfs.cf3_policies()["C3_B1_NO_NEW_BEAM"]
    de, rel, step_j = [], [], []
    n_moves = n_users = 0
    t0 = time.time()
    for env_seed, mob_seed in C.cal_seeds(a.episodes):
        env = factory()
        env_rng, mob_rng = np.random.default_rng(env_seed), np.random.default_rng(mob_seed)
        states, masks, _ = env.reset(env_rng, mob_rng)
        for _t in range(env.config.steps_per_episode):
            acts = rule(states, masks)
            base = env.environment.evaluate_actions(acts, env_rng)
            e_base = float(base.energy.system_consumed_power_w) * DT_S
            step_j.append(e_base)
            for u, s in enumerate(states):
                n_users += 1
                inc = cfs.incumbent_slot(s)
                if inc < 0 or not masks[u].mask[inc] or inc == int(acts[u]):
                    continue
                alt = np.array(acts, copy=True)
                alt[u] = inc
                ev = env.environment.evaluate_actions(alt, env_rng)
                d = e_base - float(ev.energy.system_consumed_power_w) * DT_S
                de.append(d)
                rel.append(d / e_base)
                n_moves += 1
            res = env.step(acts, env_rng)
            states, masks = res.user_states, res.action_masks
    de_a, rel_a = np.array(de), np.array(rel)
    q = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    out = {
        "episodes": a.episodes, "user_steps": n_users, "moves_differing_from_incumbent": n_moves,
        "dE_J_quantiles": dict(zip(map(str, q), np.quantile(de_a, q).tolist())) if n_moves else None,
        "dE_rel_quantiles": dict(zip(map(str, q), np.quantile(rel_a, q).tolist())) if n_moves else None,
        "dE_J_mean": float(de_a.mean()) if n_moves else None,
        "share_abs_rel_below_1pct": float(np.mean(np.abs(rel_a) < 0.01)) if n_moves else None,
        "share_exactly_zero": float(np.mean(de_a == 0.0)) if n_moves else None,
        "share_negative": float(np.mean(de_a < 0.0)) if n_moves else None,
        "step_joules_mean": float(np.mean(step_j)),
        "per_user_equal_share_J": float(np.mean(step_j)) / env.config.num_users,
        "tle_file_set_sha256": tle, "wall_s": time.time() - t0,
    }
    C.write_json(__import__("pathlib").Path(a.out), out)
    print(out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
