#!/usr/bin/env python3
"""T0-REPR step 4 -- closed-loop greedy rollout of one clone on one episode set (no training).

Same instrumented loop as the placebo (t0_common.rollout: fresh env per episode, per-episode reseeding,
plain left-to-right sums divided once).  The clone acts by masked argmax of its logits (first index on
ties, no generator) on the ratio learner's observation; T0 is queried on the clone's own states (observer,
no env / generator access) for on-policy agreement and T0-score regret.
Usage: t0_closed.py --clone NAME --set evaluation|calibration
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tree" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import t0_common as T  # noqa: E402

import numpy as np  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", required=True)
    ap.add_argument("--set", dest="tag", choices=("evaluation", "calibration"), required=True)
    a = ap.parse_args()
    tle = T.boot()
    out = T.WS / "results" / f"CLOSED-{a.clone}-{a.tag}.json"
    if out.exists():
        print(f"[skip:exists] {out}", flush=True)
        return 0
    placebo = T.WS / "results" / f"PLACEBO-{a.tag}.json"
    import json
    if not json.loads(placebo.read_text())["ok"]:
        raise SystemExit("placebo not passed on this set")
    cfg = T.learner_config()
    factory = T.C.env_factory()
    probe = factory()
    users, steps = probe.config.num_users, probe.config.steps_per_episode
    del probe
    encode = T.make_encoder(cfg, users, steps)
    mpath = T.WS / "models" / f"{a.clone}.pt"
    net, ck = T.load_clone(mpath, cfg)
    st = {"decisions": 0, "agree": 0, "regret_sum": 0.0, "price_active": 0, "agree_price_active": 0,
          "per_episode_agree": [0] * 24, "per_episode_decisions": [0] * 24}

    def observer(i, t, enc, masks, states, actions):
        S, a_t0, M = T.t0_scores(states, masks)
        amg = np.asarray(T.max_gain_actions(states, masks))
        acts = np.asarray(actions)
        has = M.any(1)
        idx = np.flatnonzero(has)
        st["decisions"] += int(has.sum())
        ag = acts[has] == a_t0[has]
        st["agree"] += int(ag.sum())
        st["regret_sum"] += float((S[idx, a_t0[idx]] - S[idx, acts[idx]]).sum())
        act = a_t0[has] != amg[has]
        st["price_active"] += int(act.sum())
        st["agree_price_active"] += int((ag & act).sum())
        st["per_episode_agree"][i] += int(ag.sum())
        st["per_episode_decisions"][i] += int(has.sum())

    t0 = time.time()
    res = T.rollout(lambda i: T.clone_policy(net), env_factory=factory, encode=encode, seeds=T.seeds_for(a.tag),
                    observer=observer)
    res["wall_s"] = time.time() - t0
    onp = {"onpolicy_agree_T0": st["agree"] / st["decisions"],
           "onpolicy_T0_score_regret_mean": st["regret_sum"] / st["decisions"],
           "onpolicy_price_active_frac": st["price_active"] / st["decisions"],
           "onpolicy_agree_T0_price_active": (st["agree_price_active"] / st["price_active"]) if st["price_active"] else None,
           "raw": st}
    payload = {"clone": a.clone, "episode_set": a.tag, "rollout": res, "onpolicy": onp,
               "model_sha256": T.sha256_file(mpath), "model_best_epoch": ck["best_epoch"], "tau": ck["tau"],
               "tle_file_set_sha256": tle, "code": T.code_ident()}
    T.write_json(out, payload)
    print(f"CLOSED {a.clone} {a.tag}: ee={res['ee']:.2f} served={res['served']:.5f} beams={res['beams']:.3f} "
          f"agree={onp['onpolicy_agree_T0']:.4f} wall={res['wall_s']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
