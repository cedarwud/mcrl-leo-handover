"""CF3PILOT evaluation of ONE checkpoint: greedy, pinned archive, 24 episodes on
the evaluation seeds with per-episode reseeding (addendum §Evaluation).

Usage: cf3_eval.py --label A2s0 --checkpoint PATH --kind cf|modqn --out FILE [--repeat]

``--repeat`` evaluates twice and records whether every per-episode row is
bit-identical (determinism placebo).  For cf checkpoints it also runs the
Amendment 2 diagnostic (``lambda_star``: the smallest lambda meeting the
former C-H bound, and the fraction of decisions it would change).  No
update(), no optimiser, no training RNG.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path

import cf3_common as C

import numpy as np
import torch

from mcrl.algorithms import cf_ratio as cfr
from mcrl.runtime import training_pipeline as tp


H_CAP_INTER = 0.6016


def cf_policy(tr, lam_act, lam_cmp=None, counts=None):
    """Greedy at ``lam_act``; optionally count decisions differing at ``lam_cmp``."""
    def pol(enc, masks, states):
        a = tr.greedy_actions(enc, masks, lam=lam_act)
        if counts is not None:
            valid = np.array([m.mask.any() for m in masks])
            counts["decisions"] += int(valid.sum())
            if lam_cmp is not None:
                b = tr.greedy_actions(enc, masks, lam=lam_cmp)
                counts["changed"] += int(np.sum((a != b) & valid))
        return a
    return pol


def build(kind: str, ckpt: Path, factory):
    if kind == "cf":
        payload = torch.load(ckpt, map_location="cpu", weights_only=False)
        cfg = cfr.trainer_config_from_payload(payload)
        st = dataclasses.replace(cfr.cf_settings_from_payload(payload), source_kind="none")
        tr = cfr.CFRatioTrainer(factory(), cfg, st, env_factory=None,
                                train_seed=payload["train_seed"], env_seed=payload["env_seed"],
                                mobility_seed=payload["mobility_seed"])
        tr.load_policy(ckpt)
        meta = {"eta": tr.eta, "lambda": tr.lam, "eta_tilde": tr.eta_tilde,
                "dual_trajectory": payload["dual_trajectory"], "episode": payload["episode"]}
        return tr, cf_policy(tr, tr.lam), tr.encode_at, meta
    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.artifacts import read_checkpoint
    raw = read_checkpoint(ckpt, map_location="cpu")
    cfgd = dict(raw.trainer_config)
    for k in ("hidden_layers", "objective_weights", "reward_calibration_scales"):
        cfgd[k] = tuple(cfgd[k])
    from mcrl.runtime.trainer_spec import TrainerConfig
    tr = MODQNTrainer(factory(), TrainerConfig(**cfgd), train_seed=raw.train_seed,
                      env_seed=raw.env_seed, mobility_seed=raw.mobility_seed)
    tr.load_checkpoint(ckpt, load_optimizers=False)
    return (tr, C.modqn_greedy(tr), lambda states, t: tr._encode_states(states),
            {"episode": raw.episode})


def lambda_star(tr, factory, seeds, h0: float) -> dict:
    """Amendment 2 diagnostic: the smallest lambda (heads' units) whose greedy
    rule meets H_inter <= 0.6016 on the evaluation episodes (doubling from
    0.01, then 12 bisection steps), and the fraction of decisions on the
    lambda = 0 rollout that would change at that lambda.  Not a gate."""
    if h0 <= H_CAP_INTER:
        return {"lambda_star": 0.0, "h_inter_at_0": h0, "search": []}

    def h_at(lam):
        r = cfr.pooled_rollout(lambda i: cf_policy(tr, lam), env_factory=factory,
                               encode=tr.encode_at, seeds=seeds)
        return r["h_inter"]

    search, lo, hi = [], 0.0, 0.01
    while True:
        h = h_at(hi); search.append((hi, h))
        if h <= H_CAP_INTER or hi > 1e4:
            break
        lo, hi = hi, hi * 2
    for _ in range(12):
        mid = 0.5 * (lo + hi)
        h = h_at(mid); search.append((mid, h))
        if h <= H_CAP_INTER:
            hi = mid
        else:
            lo = mid
    counts = {"decisions": 0, "changed": 0}
    cfr.pooled_rollout(lambda i: cf_policy(tr, 0.0, hi, counts), env_factory=factory,
                       encode=tr.encode_at, seeds=seeds)
    return {"lambda_star": hi, "h_inter_at_0": h0, "search": search,
            "changed_fraction": counts["changed"] / max(counts["decisions"], 1),
            "decisions": counts["decisions"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--kind", choices=("cf", "modqn"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--repeat", action="store_true")
    ap.add_argument("--n", type=int, default=C.N_EVAL)
    a = ap.parse_args()
    torch.set_num_threads(1)
    tle = tp.assert_tle_archive_pinned()
    factory = C.env_factory()
    t0 = time.time()
    tr, pol, enc, meta = build(a.kind, a.checkpoint, factory)
    res = cfr.pooled_rollout(lambda i: pol, env_factory=factory, encode=enc,
                             seeds=C.eval_seeds(a.n))
    if a.repeat:
        _tr2, pol2, enc2, _m = build(a.kind, a.checkpoint, factory)
        res2 = cfr.pooled_rollout(lambda i: pol2, env_factory=factory, encode=enc2,
                                  seeds=C.eval_seeds(a.n))
        res["determinism_placebo_bit_identical"] = res2["episodes"] == res["episodes"]
    res["handovers_per_user_minute"] = (res["h_inter"] + res["h_intra"]) * 60.0 / cfr.DT_S
    res["meets_former_C_H"] = res["h_inter"] <= H_CAP_INTER
    counts = lambda_star(tr, factory, C.eval_seeds(a.n), res["h_inter"]) if a.kind == "cf" else None
    res.update(label=a.label, kind=a.kind, checkpoint=str(a.checkpoint),
               checkpoint_sha256=C.sha256_file(a.checkpoint), tle_file_set_sha256=tle,
               eval_seeds=[list(x) for x in C.eval_seeds(a.n)], meta=meta,
               c2_lambda_star=counts, wall_s=time.time() - t0,
               commit=(C.REPO / "COMMIT").read_text().strip()
               if (C.REPO / "COMMIT").is_file() else None)
    C.write_json(a.out, res)
    print(a.label, res["ee"], res["h_inter"], res["served"], res["beams"],
          res.get("determinism_placebo_bit_identical"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
