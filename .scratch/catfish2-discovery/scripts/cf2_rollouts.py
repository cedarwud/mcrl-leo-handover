"""CATFISH2-DISCOVERY Stage 0: standalone DEVVAL rollouts (measurement only).

24 DEVVAL episodes, greedy, fresh environment per episode, pinned TLE archive.
No training, no optimizer step, no formal seed.  Idempotent: an existing output
file is left alone.

Usage: cf2_rollouts.py --arms A,B,C --out FILE [--rmin BPS] [--n 24]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch

import cf3_common as C
import dev_e0_common as D

import cf2_common as X
from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms.cf_ratio import encode_with_time
from mcrl.runtime import training_pipeline as tp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rmin", type=float, default=None)
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

    pol = X.raw_policies(a.rmin)
    out: dict[str, object] = {
        "lane": "CATFISH2-DISCOVERY Stage 0 (Amendment 9): development, not formal evidence",
        "set": "DEVVAL", "n_episodes": a.n,
        "seeds": [list(x) for x in seeds], "tle_file_set_sha256": tle,
        "r_min_bps": a.rmin, "eta0_bit_per_J": X.ETA0, "b_w_hz": X.B_W_HZ,
        "code": D.code_manifest(), "arms": {},
    }
    for name in a.arms.split(","):
        name = name.strip()
        if not name:
            continue
        fn = X.as_rollout_policy(pol[name])
        t0 = time.time()
        res = cfd.dev_rollout(lambda i: fn, env_factory=factory, encode=encode,
                              seeds=seeds, t0_agreement=True)
        res["wall_s"] = time.time() - t0
        out["arms"][name] = res
        print(f"{name}: ee={res['ee']:.6e} bits={res['bits']:.6e} J={res['joules']:.6e} "
              f"served={res['served']:.5f} beams={res['beams']:.3f} "
              f"p10={res['per_served_user_rate_p10_bps']:.4e} "
              f"min={res['per_served_user_rate_min_bps']:.4e} "
              f"mean={res['per_served_user_rate_mean_bps']:.4e} "
              f"agreeT0={res['t0_agreement']:.4f} wall={res['wall_s']:.0f}s", flush=True)
    C.write_json(a.out, out)
    print(json.dumps({k: v["ee"] for k, v in out["arms"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
