#!/usr/bin/env python3
"""B2-REPR step 4 -- closed loop: roll a clone SEQUENTIALLY on one episode set.

At every step the users decide in the given order; user u's input is
[113-dim observation | ctx28 built from the choices the clone has ALREADY made this step].
Greedy masked argmax over legal slots, first index on ties, no generator consumed.
Fresh env per episode, per-episode reseeding, pinned archive.

Usage: b2_closed.py --clone BC --set evaluation [--order fwd|rev]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_common as B  # noqa: E402

import numpy as np  # noqa: E402

import cf3_common as C  # noqa: E402
from mcrl.algorithms import cf_ratio as cfr  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", required=True)
    ap.add_argument("--set", dest="tag", choices=("evaluation", "calibration"), required=True)
    ap.add_argument("--order", choices=("fwd", "rev"), default="fwd")
    a = ap.parse_args()
    tle = B.boot()
    cfg = B.learner_config()
    osfx = "" if a.order == "fwd" else "-rev"
    out = B.WS / "results" / f"CLOSED-{a.clone}-{a.tag}{osfx}.json"
    if out.exists():
        print(f"[skip:exists] {out.name}", flush=True)
        return 0
    net, ck = B.load_clone(B.WS / "models" / f"{a.clone}.pt", cfg)
    use_ctx = not bool(ck.get("noctx", False))
    if use_ctx and int(ck["state_dim"]) != 141:
        raise RuntimeError(f"ctx clone must be 141-dim, got {ck['state_dim']}")
    if (not use_ctx) and int(ck["state_dim"]) != 113:
        raise RuntimeError(f"noctx clone must be 113-dim, got {ck['state_dim']}")
    factory = C.env_factory()
    t0 = time.time()
    r = B.rollout(B.clone_decider(net, a.order, use_ctx), env_factory=factory,
                  encode=lambda s, t: cfr.encode_with_time(s, t, 100, cfg, 10),
                  seeds=B.seeds_for(a.tag))
    rec = {"clone": a.clone, "episode_set": a.tag, "order": a.order, "use_ctx": use_ctx,
           "state_dim": int(ck["state_dim"]), "best_epoch": ck.get("best_epoch"),
           "tau": ck.get("tau"), "model_sha256": B.sha256_file(B.WS / "models" / f"{a.clone}.pt"),
           "result": r, "wall_s": time.time() - t0,
           "tle_file_set_sha256": tle, "code": B.code_ident()}
    B.write_json(out, rec)
    print(f"CLOSED {a.clone} {a.tag} {a.order}: ee={r['ee']:.2f} served={r['served']:.5f} "
          f"beams={r['beams']:.3f} p10={r['per_served_user_rate_p10_bps']/1e6:.2f}M "
          f"wall={rec['wall_s']:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
