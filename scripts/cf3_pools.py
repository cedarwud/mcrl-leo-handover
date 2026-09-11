"""CF3PILOT Amendment 3: pre-generate one source pool (no training).

Usage: cf3_pools.py --seed-index K --kind cf3|null3 --source-index J --out POOLS_ROOT
       [--episodes 100]

Writes ``POOLS_ROOT/s{K}/{name}.npz`` (+ ``.json`` metadata).  Episode i runs
on a FRESH env with the declared pool seeds (``cf3_common.pool_seeds``); the
cf3 and null3 pools of the same K use the SAME seeds and differ only in the
policy (null3 draws uniform legal actions from default_rng((9_151_000, K, J, i))).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
from pathlib import Path

import cf3_common as C

import numpy as np
import torch

from mcrl.algorithms import cf_ratio as cfr
from mcrl.algorithms import cf_sources as cfs
from mcrl.runtime import training_pipeline as tp


def policy_factory(kind: str, k: int, j: int):
    if kind == "cf3":
        name = cfr.CF3_SPECS[j][0]
        rule = cfs.cf3_policies()[name]
        return lambda i: rule
    return lambda i: cfs.random_legal(np.random.default_rng((C.POOL_NULL_BASE, k, j, i)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed-index", type=int, required=True, choices=(0, 1, 2, 3, 4))
    ap.add_argument("--kind", choices=("cf3", "null3"), required=True)
    ap.add_argument("--source-index", type=int, choices=(0, 1, 2), required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--episodes", type=int, default=C.POOL_EPISODES)
    a = ap.parse_args()
    torch.set_num_threads(1)
    tle = tp.assert_tle_archive_pinned()
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    config = C.pilot_config(record, "A2", C.EPISODES)
    name, head = cfr.source_names(a.kind)[a.source_index]
    t0 = time.time()
    seeds = C.pool_seeds(a.seed_index, a.episodes)
    arrays = cfr.generate_pool(policy_factory(a.kind, a.seed_index, a.source_index),
                               env_factory=C.env_factory(), seeds=seeds, config=config)
    path = C.pool_path(a.out, a.seed_index, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    np.savez(buf, **{f: arrays[f] for f in cfr.POOL_FIELDS})
    tmp = path.with_suffix(".npz.tmp")
    tmp.write_bytes(buf.getvalue())
    tmp.replace(path)
    raw = arrays["rewards_raw"]
    meta = {"name": name, "head": head, "kind": a.kind, "seed_index": a.seed_index,
            "source_index": a.source_index, "episodes": a.episodes,
            "seeds": [list(x) for x in seeds], "transitions": int(len(raw)),
            "t0_obs_sha256": arrays["t0_obs_sha256"].tolist(),
            "pool_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "raw_mean_B_E_H": raw.mean(0).tolist(),
            "pool_ee": float(raw[:, 0].sum() / raw[:, 1].sum()),
            "h_inter_rate": float(raw[:, 2].mean()),
            "state_dim": int(arrays["states"].shape[1]),
            "tle_file_set_sha256": tle, "code_commit": C.code_manifest()["commit"],
            "wall_s": time.time() - t0}
    C.write_json(path.with_suffix(".json"), meta)
    print(name, a.seed_index, meta["transitions"], meta["pool_ee"], meta["wall_s"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
