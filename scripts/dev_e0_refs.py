"""The DEVVAL rule references, rolled ONCE (Amendment 6 section 6).

``A m=2dB``, ``LP-prev(c=1, m=0)`` (= the teacher T0), ``MAX_NOMINAL_GAIN`` and
``RANDOM`` (episode i draws from ``default_rng(9_221_000 + i)``) on the 24 DEVVAL
episodes: fresh environment per episode, per-episode reseeded, greedy, pooled
EE with bits and joules, served, per-served-user rate mean / p10 / min, lit beams,
H_inter / H_intra.  No training, no learner, no formal episode.

Usage: dev_e0_refs.py --out FILE [--n 24]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cf3_common as C
import dev_e0_common as D

import torch

from mcrl.algorithms import cf_dev as cfd
from mcrl.runtime import training_pipeline as tp


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
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    cfg = D.e0_config(record, D.EPISODES)
    factory = C.env_factory()
    probe = factory()
    users, steps = probe.config.num_users, probe.config.steps_per_episode
    del probe
    from mcrl.algorithms.cf_ratio import encode_with_time
    encode = lambda states, t: encode_with_time(states, t, users, cfg, steps)  # noqa: E731
    seeds = D.devval_seeds(a.n)

    out: dict[str, object] = {
        "set": "DEVVAL", "n_episodes": a.n,
        "seeds": [list(x) for x in seeds], "tle_file_set_sha256": tle,
        "lane": "E0-development (Amendment 6): not formal evidence",
        "code": D.code_manifest(), "arms": {},
    }
    jobs = list(D.reference_policies().items())
    jobs.append(("RANDOM", None))
    for name, pol in jobs:
        t0 = time.time()
        factory_i = (D.random_reference_factory() if pol is None else (lambda i: pol))
        res = cfd.dev_rollout(factory_i, env_factory=factory, encode=encode,
                              seeds=seeds, t0_agreement=True)
        res["wall_s"] = time.time() - t0
        out["arms"][name] = res
        print(f"{name}: ee={res['ee']:.6e} served={res['served']:.5f} "
              f"beams={res['beams']:.3f} h_inter={res['h_inter']:.5f} "
              f"rate_p10={res['per_served_user_rate_p10_bps']:.4e} "
              f"agreeT0={res['t0_agreement']:.4f} wall={res['wall_s']:.0f}s", flush=True)
    C.write_json(a.out, out)
    print(json.dumps({k: v["ee"] for k, v in out["arms"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
