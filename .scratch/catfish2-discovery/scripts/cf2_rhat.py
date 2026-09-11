"""CATFISH2-DISCOVERY Stage 0: characterising the INSTRUMENT r_hat, not a result.

The brief's C-Q and C-RC are defined only once `R_min` is supplied by an
EXISTING declared project constant.  No such constant exists (see
`.scratch/catfish2-discovery/PROGRESS.md`, Finding 2), so neither candidate can
be counted.  This script produces the decision support the controller needs to
rule on `R_min`, and deliberately produces NOTHING ELSE:

  * the distribution of `r_hat(a) = (B_w / (n_a + 1)) * log2(1 + gamma_a)` over
    the LEGAL candidates seen on T0's own DEVVAL trajectory;
  * for a grid of hypothetical thresholds, the share of legal candidates the
    restriction would exclude, and the share of decisions at which T0's OWN
    chosen action fails the floor -- the degeneracy statistic: wherever T0's
    action clears the floor, C-Q is identically T0.
  * the induced ACTION disagreement of C-Q / C-RC against T0 per threshold.

No environment counterfactual, no energy, no EE, no candidate outcome is
computed here.  Choosing `R_min` by looking at a candidate's OUTCOME would
forfeit the prospective status of brief section 3; this file is written so that
temptation is not available from its output.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import torch

import cf3_common as C
import dev_e0_common as D

import cf2_common as X
from mcrl.algorithms import cf_teacher as cft
from mcrl.runtime import training_pipeline as tp

# A decade grid spanning the plausible range, declared here before running.
GRID = [1.0e6, 3.0e6, 1.0e7, 2.5e7, 5.0e7, 1.0e8, 1.5e8, 2.0e8, 3.0e8, 5.0e8]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=D.N_DEVVAL)
    a = ap.parse_args()
    torch.set_num_threads(1)
    tle = D.assert_environment()
    if a.out.is_file():
        print(f"[skip:exists] {a.out}")
        return 0
    tp.read_prereg(tp.CANONICAL_PREREG)
    factory = C.env_factory()
    seeds = D.devval_seeds(a.n)

    rhat_legal: list[float] = []
    rhat_t0_action: list[float] = []
    n_dec = 0
    excl = {g: 0 for g in GRID}          # legal candidates excluded
    n_legal_cands = 0
    t0_fails = {g: 0 for g in GRID}      # decisions where T0's own action fails
    empty_set = {g: 0 for g in GRID}     # decisions where NO legal candidate clears
    dis_cq = {g: 0 for g in GRID}
    dis_crc = {g: 0 for g in GRID}
    t_start = time.time()

    for i in range(len(seeds)):
        env = factory()
        env_rng = np.random.default_rng(seeds[i][0])
        mob_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        states, masks, _ = env.reset(env_rng, mob_rng)
        cq = {g: X.cq_rule(g) for g in GRID}
        crc = {g: X.crc_rule(g) for g in GRID}
        for t in range(steps):
            _, a_t0, legal = cft.t0_scores(states, masks)
            a_t0 = np.asarray(a_t0, dtype=np.int64)
            acq = {g: np.asarray(cq[g](states, masks), dtype=np.int64) for g in GRID}
            acrc = {g: np.asarray(crc[g](states, masks), dtype=np.int64) for g in GRID}
            for u in range(users):
                ok = np.flatnonzero(legal[u])
                if ok.size == 0:
                    continue
                n_dec += 1
                gain = np.asarray(states[u].channel_quality, dtype=np.float64)
                load = np.asarray(states[u].beam_loads, dtype=np.float64)
                rh = X.r_hat(gain, load)[ok]
                rhat_legal.extend(rh.tolist())
                n_legal_cands += int(ok.size)
                rhat_t0_action.append(float(X.r_hat(gain, load)[int(a_t0[u])]))
                for g in GRID:
                    clears = rh >= g
                    excl[g] += int((~clears).sum())
                    if not clears.any():
                        empty_set[g] += 1
                    if X.r_hat(gain, load)[int(a_t0[u])] < g:
                        t0_fails[g] += 1
                    dis_cq[g] += int(int(acq[g][u]) != int(a_t0[u]))
                    dis_crc[g] += int(int(acrc[g][u]) != int(a_t0[u]))
            res = env.step(a_t0, env_rng)
            states, masks = res.user_states, res.action_masks
            if res.done:
                break
        print(f"[ep {i}] decisions={n_dec} wall={time.time() - t_start:.0f}s", flush=True)

    arr = np.asarray(rhat_legal, dtype=np.float64)
    t0a = np.asarray(rhat_t0_action, dtype=np.float64)
    q = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    out = {
        "lane": "CATFISH2-DISCOVERY Stage 0 (Amendment 9): instrument characterisation only",
        "warning": "NOT a candidate result.  No EE, served, p10 or counterfactual value "
                   "is computed for any R_min.  Selecting R_min from a candidate OUTCOME "
                   "would forfeit the prospective status of brief section 3.",
        "set": "DEVVAL", "n_episodes": a.n, "trajectory": "T0 = LP-prev(c=1,m=0) greedy",
        "tle_file_set_sha256": tle, "b_w_hz": X.B_W_HZ,
        "n_decisions": n_dec, "n_legal_candidates": n_legal_cands,
        "rhat_legal_quantiles_bps": {f"p{p}": float(np.percentile(arr, p)) for p in q},
        "rhat_legal_min_bps": float(arr.min()), "rhat_legal_max_bps": float(arr.max()),
        "rhat_t0_action_quantiles_bps": {f"p{p}": float(np.percentile(t0a, p)) for p in q},
        "rhat_t0_action_min_bps": float(t0a.min()),
        "grid": {
            f"{g:.6g}": {
                "excluded_legal_candidate_share": excl[g] / max(n_legal_cands, 1),
                "decisions_where_T0_action_fails_floor": t0_fails[g] / max(n_dec, 1),
                "decisions_with_empty_clearing_set": empty_set[g] / max(n_dec, 1),
                "C_Q_action_disagreement_with_T0": dis_cq[g] / max(n_dec, 1),
                "C_RC_action_disagreement_with_T0": dis_crc[g] / max(n_dec, 1),
            }
            for g in GRID
        },
        "wall_s": time.time() - t_start,
        "code": D.code_manifest(),
    }
    C.write_json(a.out, out)
    print("r_hat legal quantiles:", {k: f"{v:.4e}" for k, v in out["rhat_legal_quantiles_bps"].items()})
    for g in GRID:
        r = out["grid"][f"{g:.6g}"]
        print(f"R_min={g:.4e}: excl={r['excluded_legal_candidate_share']:.4f} "
              f"T0_fails={r['decisions_where_T0_action_fails_floor']:.4f} "
              f"empty={r['decisions_with_empty_clearing_set']:.4f} "
              f"dis(C-Q)={r['C_Q_action_disagreement_with_T0']:.4f} "
              f"dis(C-RC)={r['C_RC_action_disagreement_with_T0']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
