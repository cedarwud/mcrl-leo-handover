"""CATFISH2-DISCOVERY Stage 0: value-weighted complementarity against T0.

Measurement only -- no learner, no optimizer step, no committed action other
than T0's own.  The trajectory is T0's DEVVAL rollout; on every decision where a
candidate picks a different legal action from T0, all other users are held at
T0's joint action for that step and ``StepEnvironment.evaluate_actions`` scores
the unilateral deviation under common random numbers (it deep-copies the
caller's generator and never advances it, ``env/step.py:700``).

Recorded per deviating decision (brief section 2):
  d_bits, d_joules, delta = d_bits - eta0 * d_joules,
  whether the candidate raises the moving user's own predicted share r_hat,
  and whether the move is QoS-invalid.

**QoS-invalid, declared here before any counted run**: the existing project
convention, ported verbatim from
``.scratch/h4-probe/scripts/oracle_cells.py::best_response_step`` (lines 190-215)
with the reference R = **T0's joint action at that same step** (the counterfactual
holds every other user at it):
  * service-floor rejection -- some user served under R is unserved under the move; or
  * rate-floor rejection    -- some user served under R has realised rate below
    ``0.5 x`` its rate under R at the same step.
No new threshold is introduced: the 0.5 factor is the project's existing one.

Sharding is by DEVVAL episode index; shards are disjoint and idempotent.

Usage: cf2_diag.py --out FILE [--rmin BPS] [--shard k --nshards N] [--n 24]
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
from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_teacher as cft
from mcrl.algorithms.cf_ratio import DT_S
from mcrl.runtime import training_pipeline as tp

FLOOR_FRACTION = 0.5  # oracle_cells.py convention, not a new constant


def _energy(ev):
    return (float(ev.energy.system_throughput_bps) * DT_S,
            float(ev.energy.system_consumed_power_w) * DT_S)


def _served_rates(ev, users: int):
    served = np.asarray(ev.resolution.served, dtype=bool)
    rates = np.array([float(ev.rewards[u].r1_throughput) for u in range(users)],
                     dtype=np.float64)
    return served, rates


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rmin", type=float, default=None)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
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
    mine = [i for i in range(len(seeds)) if i % a.nshards == a.shard]
    pol = X.raw_policies(a.rmin)
    # C-Q'-global (Amendment 11) is not deployable: its q10(t) needs the service
    # resolution of T0's own joint action at that step, which is exactly the
    # `ev_ref` this loop already computes.  It is therefore built inside the step.
    names = [n for n in pol if n != "T0_LP_prev_c1_m0"] + ["C_Q_global"]

    recs: dict[str, dict] = {
        n: {"deltas": [], "d_bits": [], "d_joules": [], "rhat_up": 0,
            "qos_invalid": 0, "n_disagree": 0, "n_decisions": 0,
            "n_agree_maxgain": 0}
        for n in names
    }
    q10_global_seen: list[float] = []
    n_eval = 0
    t_start = time.time()

    for i in mine:
        env = factory()
        env_rng = np.random.default_rng(seeds[i][0])
        mob_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        states, masks, _ = env.reset(env_rng, mob_rng)
        for t in range(steps):
            _, a_t0, legal = cft.t0_scores(states, masks)
            a_t0 = np.asarray(a_t0, dtype=np.int64)
            has_legal = np.array([bool(legal[u].any()) for u in range(users)])
            acts = {n: np.asarray(pol[n](states, masks), dtype=np.int64)
                    for n in names if n in pol}
            mg = acts["MAX_NOMINAL_GAIN"]

            ev_ref = env.environment.evaluate_actions(a_t0, env_rng)
            n_eval += 1
            bits_R, j_R = _energy(ev_ref)
            served_R, rate_R = _served_rates(ev_ref, users)
            q_glob = X.q10_global(states, a_t0, served_R)
            q10_global_seen.append(q_glob)
            acts["C_Q_global"] = np.asarray(
                X.cq_global_actions(states, masks, q_glob), dtype=np.int64)

            # unique (user, action) deviations, shared across candidates
            cache: dict[tuple[int, int], tuple[float, float, bool]] = {}
            for n in names:
                for u in range(users):
                    if not has_legal[u] or int(acts[n][u]) == int(a_t0[u]):
                        continue
                    key = (u, int(acts[n][u]))
                    if key in cache:
                        continue
                    dev = np.array(a_t0, dtype=np.int64)
                    dev[u] = key[1]
                    ev = env.environment.evaluate_actions(dev, env_rng)
                    n_eval += 1
                    b, jj = _energy(ev)
                    s, r = _served_rates(ev, users)
                    bad = bool(np.any(served_R & ~s)) or bool(
                        np.any(served_R & s & (r < FLOOR_FRACTION * rate_R)))
                    cache[key] = (b - bits_R, jj - j_R, bad)

            for n in names:
                rec = recs[n]
                for u in range(users):
                    if not has_legal[u]:
                        continue
                    rec["n_decisions"] += 1
                    rec["n_agree_maxgain"] += int(int(acts[n][u]) == int(mg[u]))
                    if int(acts[n][u]) == int(a_t0[u]):
                        continue
                    rec["n_disagree"] += 1
                    db, dj, bad = cache[(u, int(acts[n][u]))]
                    rec["d_bits"].append(db)
                    rec["d_joules"].append(dj)
                    rec["deltas"].append(db - X.ETA0 * dj)
                    rec["qos_invalid"] += int(bad)
                    gain = np.asarray(states[u].channel_quality, dtype=np.float64)
                    load = np.asarray(states[u].beam_loads, dtype=np.float64)
                    rh = X.r_hat(gain, load)
                    rec["rhat_up"] += int(rh[int(acts[n][u])] > rh[int(a_t0[u])])

            res = env.step(a_t0, env_rng)
            states, masks = res.user_states, res.action_masks
            if res.done:
                break
        print(f"[ep {i}] evals={n_eval} wall={time.time() - t_start:.0f}s", flush=True)

    out = {
        "lane": "CATFISH2-DISCOVERY Stage 0 (Amendment 9): development, not formal evidence",
        "set": "DEVVAL", "trajectory": "T0 = LP-prev(c=1, m=0) greedy",
        "episodes": mine, "shard": a.shard, "nshards": a.nshards,
        "tle_file_set_sha256": tle, "eta0_bit_per_J": X.ETA0,
        "r_min_bps": a.rmin, "b_w_hz": X.B_W_HZ,
        "floor_fraction": FLOOR_FRACTION,
        "qos_invalid_definition":
            "oracle_cells.py::best_response_step convention with R = T0's joint "
            "action at the same step: some user served under R unserved, or some "
            "user served under R below 0.5 x its rate under R",
        "n_evaluate_actions": n_eval,
        "q10_global_bps_seen": q10_global_seen,
        "wall_s": time.time() - t_start,
        "code": D.code_manifest(),
        "candidates": {n: {k: (v if not isinstance(v, list) else v)
                           for k, v in recs[n].items()} for n in names},
    }
    C.write_json(a.out, out)
    for n in names:
        r = recs[n]
        d = np.asarray(r["deltas"], dtype=np.float64)
        pos = float(d[d > 0].sum()) if d.size else 0.0
        neg = float(-d[d < 0].sum()) if d.size else 0.0
        print(f"{n}: dis={r['n_disagree']}/{r['n_decisions']} "
              f"({r['n_disagree'] / max(r['n_decisions'], 1):.4f}) "
              f"better={float((d > 0).mean()) if d.size else float('nan'):.4f} "
              f"CR={pos / neg if neg > 0 else float('inf'):.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
