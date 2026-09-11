"""CATFISH2-DISCOVERY Stage 0: DEVVAL rollout for a policy that needs the env.

C-Q'-global (Amendment 11 section 2) is **not deployable**: its threshold
``q10(t)`` is the 10th percentile of ``r_hat`` over the users T0's own joint
action serves at that step, a cross-user order statistic that needs the
environment's service resolution for T0's joint action.  ``cf_dev.dev_rollout``
gives a policy no access to the environment, so this file mirrors its loop
**statement for statement** and hands the policy the env and its generator.

The mirror is VERIFIED, not asserted: ``--arm T0`` re-rolls T0 through this loop
and the run must reproduce ``DEVVAL-REFERENCES.json``'s ``LP_prev_c1_m0`` row
exactly.  Any drift in the estimand shows up there.

Measurement only.  No training, no optimizer step.

Usage: cf2_priv.py --arm {T0,C_Q_global} --out FILE [--n 24]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch

import cf3_common as C
import dev_e0_common as D

import cf2_common as X
from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_teacher as cft
from mcrl.algorithms.cf_ratio import DT_S, encode_with_time
from mcrl.env.action_contract import HandoverClass
from mcrl.runtime import training_pipeline as tp

LP_GRID_DT_S = cfd.LP_GRID_DT_S


def priv_rollout(step_policy, *, env_factory, encode, seeds):
    """``cf_dev.dev_rollout`` with ``t0_agreement=True``, mirrored, with the
    policy signature widened to ``(enc, masks, states, env, env_rng) -> actions``.
    Every accumulation below is copied from ``cf_dev.dev_rollout`` unchanged."""
    cfd.assert_dev_seed_pairs(seeds, "priv_rollout")
    rows: list[dict] = []
    rates: list[float] = []
    agree = regret = 0.0
    decisions = 0
    extra = {"q10_global": [], "n_ref_evals": 0}
    for i in range(len(seeds)):
        env = env_factory()
        env_rng = np.random.default_rng(seeds[i][0])
        mobility_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        states, masks, _ = env.reset(env_rng, mobility_rng)
        enc = encode(states, 0)
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "h_inter": 0, "h_intra": 0, "beams": 0.0, "steps": 0,
               "epoch": str(getattr(env, "epoch", None)),
               "t0_obs112_sha256": hashlib.sha256(
                   np.ascontiguousarray(np.asarray(enc)[:, :112]).tobytes()
               ).hexdigest()}
        for t in range(steps):
            actions = step_policy(enc, masks, states, env, env_rng, extra)
            scores, t0_acts, legal = cft.t0_scores(states, masks)
            for u in range(users):
                if not bool(legal[u].any()):
                    continue
                decisions += 1
                agree += float(int(actions[u]) == int(t0_acts[u]))
                if 0 <= int(actions[u]) < scores.shape[1]:
                    regret += float(scores[u, int(t0_acts[u])] - scores[u, int(actions[u])])
            res = env.step(actions, env_rng)
            out = env.last_outcome
            e = out.energy
            row["bits"] += float(e.system_throughput_bps) * DT_S
            row["joules"] += float(e.system_consumed_power_w) * DT_S
            row["served"] += int(e.served)
            row["beams"] += float(e.eff_beams)
            row["steps"] += 1
            row["user_steps"] += users
            for cls in out.handovers:
                row["h_inter"] += int(cls is HandoverClass.INTER_SATELLITE)
                row["h_intra"] += int(cls is HandoverClass.INTRA_SATELLITE)
            if res.served is not None:
                for uid in range(users):
                    if bool(res.served[uid]):
                        rates.append(float(res.rewards[uid].r1_throughput))
            states, masks = res.user_states, res.action_masks
            enc = encode(states, t + 1)
            if res.done:
                break
        rows.append(row)
    bits = joules = beams_total = 0.0
    for r in rows:
        bits += r["bits"]
        joules += r["joules"]
        beams_total += r["beams"]
    us = sum(r["user_steps"] for r in rows)
    out_d = {
        "bits": bits, "joules": joules, "ee": bits / joules,
        "h_inter": sum(r["h_inter"] for r in rows) / us,
        "h_intra": sum(r["h_intra"] for r in rows) / us,
        "served": sum(r["served"] for r in rows) / us,
        "beams": beams_total / sum(r["steps"] for r in rows),
        "user_steps": us,
        "ee_ep": [r["bits"] / r["joules"] if r["joules"] > 0 else float("nan") for r in rows],
        "n_episodes": len(rows),
        "episodes": rows,
    }
    out_d.update(cfd._rate_stats(rates))
    out_d["ho_per_user_min"] = (out_d["h_inter"] + out_d["h_intra"]) * 60.0 / LP_GRID_DT_S
    out_d["t0_agreement"] = agree / max(decisions, 1)
    out_d["t0_score_regret"] = regret / max(decisions, 1)
    out_d["t0_decisions"] = decisions
    q = np.asarray([v for v in extra["q10_global"] if np.isfinite(v)], dtype=np.float64)
    if q.size:
        out_d["q10_global_bps"] = {
            "mean": float(q.mean()), "min": float(q.min()), "max": float(q.max()),
            "p10": float(np.percentile(q, 10)), "p50": float(np.percentile(q, 50)),
            "p90": float(np.percentile(q, 90)), "n_steps": int(q.size),
        }
    out_d["n_reference_evaluations"] = extra["n_ref_evals"]
    return out_d


def t0_step_policy(enc, masks, states, env, env_rng, extra):
    return np.asarray(cft.t0_scores(states, masks)[1], dtype=np.int64)


def cq_global_step_policy(enc, masks, states, env, env_rng, extra):
    a_t0 = np.asarray(cft.t0_scores(states, masks)[1], dtype=np.int64)
    ev = env.environment.evaluate_actions(a_t0, env_rng)
    extra["n_ref_evals"] += 1
    served_ref = np.asarray(ev.resolution.served, dtype=bool)
    q = X.q10_global(states, a_t0, served_ref)
    extra["q10_global"].append(q)
    return np.asarray(X.cq_global_actions(states, masks, q), dtype=np.int64)


POLICIES = {"T0": t0_step_policy, "C_Q_global": cq_global_step_policy}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(POLICIES))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=D.N_DEVVAL)
    a = ap.parse_args()
    torch.set_num_threads(1)
    tle = D.assert_environment()
    if a.out.is_file():
        print(f"[skip:exists] {a.out}")
        return 0
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    cfg = D.e0_config(record, D.EPISODES)
    factory = C.env_factory()
    probe = factory()
    users, steps = probe.config.num_users, probe.config.steps_per_episode
    del probe
    encode = lambda st, t: encode_with_time(st, t, users, cfg, steps)  # noqa: E731
    seeds = D.devval_seeds(a.n)
    t0 = time.time()
    res = priv_rollout(POLICIES[a.arm], env_factory=factory, encode=encode, seeds=seeds)
    res["wall_s"] = time.time() - t0
    out = {
        "lane": "CATFISH2-DISCOVERY Stage 0 (Amendment 9 + 11): development, not formal evidence",
        "set": "DEVVAL", "n_episodes": a.n, "arm": a.arm,
        "seeds": [list(x) for x in seeds], "tle_file_set_sha256": tle,
        "deployable": a.arm != "C_Q_global",
        "code": D.code_manifest(), "arms": {a.arm: res},
    }
    C.write_json(a.out, out)
    print(f"{a.arm}: ee={res['ee']:.6e} bits={res['bits']:.6e} J={res['joules']:.6e} "
          f"served={res['served']:.5f} beams={res['beams']:.3f} "
          f"p10={res['per_served_user_rate_p10_bps']:.4e} "
          f"min={res['per_served_user_rate_min_bps']:.4e} "
          f"mean={res['per_served_user_rate_mean_bps']:.4e} "
          f"agreeT0={res['t0_agreement']:.4f} wall={res['wall_s']:.0f}s")
    if "q10_global_bps" in res:
        print("q10(t):", json.dumps(res["q10_global_bps"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
