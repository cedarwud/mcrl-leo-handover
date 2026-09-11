#!/usr/bin/env python3
"""B2-REPR diagnostic (NON-DEPLOYABLE, open-loop only): the teacher's own full context block.

At user u's turn the sequential oracle best-responds to V = [chosen_0..chosen_{u-1}, ref_u..ref_99].
The B2 student sees only the first part.  This script builds the block the TEACHER effectively sees,

    ctxfull[u,a] = ( # users v != u whose V-action realises u's slot-a beam ) / num_users
                   (chosen for v < u, reference for v > u)

so a clone on [obs113 | ctx28 | ctxfull28] can answer: is the shortfall a *missing-information*
problem (the student cannot see the rest of the joint action) or a function-class / physics problem
(even the teacher's own context does not determine its action)?  It is never rolled in closed loop.

Usage: b2_ctxfull.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_common as B  # noqa: E402

import numpy as np  # noqa: E402

import cf3_common as C  # noqa: E402
from mcrl.algorithms import cf_ratio as cfr  # noqa: E402

TAG = "calibration"


def block(sim, users, chosen, ref):
    ctx = B.Ctx(B.beam_ids(sim, users), users)
    # start from the reference joint action of every user
    for v in range(users):
        ctx.commit(v, int(ref[v]))
    out = np.zeros((users, B.N_ACT), dtype=np.float32)
    for u in range(users):
        ids = ctx.slot_id[u]
        cur = ctx.count.copy()
        cur[int(ctx.slot_id[u, int(ref[u])])] -= 1.0        # drop u's own reference entry
        v = cur[ids] / users
        v[ctx.invalid[ids]] = 0.0
        out[u] = v.astype(np.float32)
        # u now commits its chosen action in place of its reference one
        ctx.count[int(ctx.slot_id[u, int(ref[u])])] -= 1.0
        ctx.commit(u, int(chosen[u]))
    return out


def main() -> int:
    tle = B.boot()
    cfg = B.learner_config()
    out_path = B.WS / "data" / f"B2-ctxfull-{TAG}.npz"
    if out_path.exists():
        print(f"[skip:exists] {out_path.name}", flush=True)
        return 0
    factory = C.env_factory()
    seeds = B.seeds_for(TAG)
    rows, idx = [], []
    t0 = time.time()
    for ep in range(24):
        rec = json.loads((B.ORACLE_DIR / f"{B.TEACHER_STEM.format(tag=TAG, i=ep)}.json").read_text())

        def decide(_e, t, env, sim, enc, masks, states, _rec=rec, _ep=ep):
            users = len(masks)
            chosen = np.asarray(_rec["joint_chosen"][t], dtype=np.int32)
            ref = np.asarray(_rec["joint_ref"][t], dtype=np.int32)
            rows.append(block(sim, users, chosen, ref))
            idx.append(np.stack([np.full(users, _ep), np.full(users, t), np.arange(users)], axis=1))
            return chosen

        B.rollout(decide, env_factory=factory,
                  encode=lambda s, t: cfr.encode_with_time(s, t, 100, cfg, 10), seeds=[seeds[ep]])
    ii = np.concatenate(idx)
    d = {"ctxfull": np.concatenate(rows).astype(np.float32),
         "episode": ii[:, 0].astype(np.int16), "step": ii[:, 1].astype(np.int16),
         "user": ii[:, 2].astype(np.int16)}
    base = np.load(B.WS / "data" / f"B2-train-{TAG}.npz")
    for k in ("episode", "step", "user"):
        if not np.array_equal(base[k], d[k]):
            raise RuntimeError(f"ctxfull index mismatch on {k}")
    tmp = out_path.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **d)
    tmp.replace(out_path)
    meta = {"rows": int(len(d["ctxfull"])), "sha256": B.sha256_file(out_path),
            "nonzero_frac": float((d["ctxfull"] > 0).mean()), "max": float(d["ctxfull"].max()),
            "row_sum_mean": float(d["ctxfull"].sum(1).mean()), "wall_s": time.time() - t0,
            "tle_file_set_sha256": tle}
    B.write_json(B.WS / "data" / f"B2-ctxfull-{TAG}-meta.json", meta)
    print(f"CTXFULL {meta}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
