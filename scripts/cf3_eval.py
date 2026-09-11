"""CF3PILOT evaluation of ONE checkpoint: greedy, pinned archive, 24 episodes on
the evaluation seeds with per-episode reseeding (addendum §Evaluation).

Usage: cf3_eval.py --label A2s0 --checkpoint PATH --kind cf|modqn --out FILE [--repeat]

``--repeat`` evaluates twice and records whether every per-episode row is
bit-identical (determinism placebo).  For cf checkpoints it also counts the
evaluation decisions whose greedy argmax changes when ``-lambda Q_H`` is
removed (Amendment 1 item 5).  No update(), no optimiser, no training RNG.
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


def build(kind: str, ckpt: Path, factory):
    if kind == "cf":
        payload = torch.load(ckpt, map_location="cpu", weights_only=False)
        cfg = cfr.trainer_config_from_payload(payload)
        st = dataclasses.replace(cfr.cf_settings_from_payload(payload), source_kind="none")
        tr = cfr.CFRatioTrainer(factory(), cfg, st, env_factory=None,
                                train_seed=payload["train_seed"], env_seed=payload["env_seed"],
                                mobility_seed=payload["mobility_seed"])
        tr.load_policy(ckpt)
        counts = {"decisions": 0, "changed_without_QH": 0}

        def pol(enc, masks, states):
            a = tr.greedy_actions(enc, masks)
            b = tr.greedy_actions(enc, masks, lam=0.0)
            valid = np.array([m.mask.any() for m in masks])
            counts["decisions"] += int(valid.sum())
            counts["changed_without_QH"] += int(np.sum((a != b) & valid))
            return a

        meta = {"eta": tr.eta, "lambda": tr.lam, "eta_tilde": tr.eta_tilde,
                "dual_trajectory": payload["dual_trajectory"], "episode": payload["episode"]}
        return pol, tr.encode_at, counts, meta
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
    return (C.modqn_greedy(tr), lambda states, t: tr._encode_states(states), None,
            {"episode": raw.episode})


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
    pol, enc, counts, meta = build(a.kind, a.checkpoint, factory)
    res = cfr.pooled_rollout(lambda i: pol, env_factory=factory, encode=enc,
                             seeds=C.eval_seeds(a.n))
    if a.repeat:
        pol2, enc2, _c, _m = build(a.kind, a.checkpoint, factory)
        res2 = cfr.pooled_rollout(lambda i: pol2, env_factory=factory, encode=enc2,
                                  seeds=C.eval_seeds(a.n))
        res["determinism_placebo_bit_identical"] = res2["episodes"] == res["episodes"]
    res.update(label=a.label, kind=a.kind, checkpoint=str(a.checkpoint),
               checkpoint_sha256=C.sha256_file(a.checkpoint), tle_file_set_sha256=tle,
               eval_seeds=[list(x) for x in C.eval_seeds(a.n)], meta=meta,
               c2_activation=counts, wall_s=time.time() - t0,
               commit=(C.REPO / "COMMIT").read_text().strip()
               if (C.REPO / "COMMIT").is_file() else None)
    C.write_json(a.out, res)
    print(a.label, res["ee"], res["h_inter"], res["served"], res["beams"],
          res.get("determinism_placebo_bit_identical"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
