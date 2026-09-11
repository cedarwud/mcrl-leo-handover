"""CF3PILOT pre-launch, NO training: calibration + source re-measurement.

Arms (Amendment 1 item 4, plus the declaration's eta_0 and the coordinator's
random reference), each 24 episodes on the CALIBRATION seeds with
per-episode reseeding, pinned archive:

  MAX_NOMINAL_GAIN  -> eta_0 = pooled bits / pooled joules; s_B, s_E
  RANDOM_MASKED     -> the learning-check reference
  TRAINED           -> frozen e6b063ef checkpoint, greedy
  C1_A_m2dB, C2_A_m12dB, C3_B1_NO_NEW_BEAM -> the three sources
  HARNESS_PLACEBO   -> RANDOM via the B0 harness convention (one env, stream
                       42/1337/7, MODQNTrainer(train_seed=42).select_actions
                       eps=1) must give 52,420,510.0956937 bit/J exactly

Usage: cf3_premeasure.py --arm NAME --out DIR     (one arm per process)
       cf3_premeasure.py --merge --out DIR        (writes calibration.json)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cf3_common as C

import numpy as np
import torch

from mcrl.algorithms.cf_ratio import pooled_rollout
from mcrl.runtime import training_pipeline as tp

ARMS = ("MAX_NOMINAL_GAIN", "RANDOM_MASKED", "TRAINED", "C1_A_m2dB", "C2_A_m12dB",
        "C3_B1_NO_NEW_BEAM", "HARNESS_PLACEBO")
HARNESS_RANDOM_PINNED = 52420510.0956937


def run_arm(name: str) -> dict:
    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.runtime.trainer_spec import TrainerConfig

    factory = C.env_factory()
    cfg = TrainerConfig(learning_rate=0.001, episodes=1)
    probe = MODQNTrainer(factory(), cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    encode = lambda states, t: probe._encode_states(states)  # noqa: E731
    if name == "HARNESS_PLACEBO":
        tr = probe
        return pooled_rollout(lambda i: (lambda enc, m, s: tr.select_actions(enc, m, 1.0)),
                              env_factory=factory, encode=encode,
                              stream=(1337, 7, 24))
    if name == "RANDOM_MASKED":
        pf = C.random_policy_factory()
    elif name == "TRAINED":
        probe.load_checkpoint(C.TRAINED_CKPT, load_optimizers=False)
        pol = C.modqn_greedy(probe)
        pf = lambda i: pol  # noqa: E731
    else:
        pol = C.rule_policy(name)
        pf = lambda i: pol  # noqa: E731
    return pooled_rollout(pf, env_factory=factory, encode=encode, seeds=C.cal_seeds())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    if a.merge:
        rows = {n: json.loads((a.out / f"{n}.json").read_text()) for n in ARMS}
        mng = rows["MAX_NOMINAL_GAIN"]
        placebo_ok = rows["HARNESS_PLACEBO"]["ee"] == HARNESS_RANDOM_PINNED
        out = {
            "eta0_bit_per_J": mng["ee"],
            "bits_scale": mng["bits_per_user_step"],
            "joules_scale": mng["joules_per_user_step"],
            "random_reference_ee": rows["RANDOM_MASKED"]["ee"],
            "harness_placebo_ee": rows["HARNESS_PLACEBO"]["ee"],
            "harness_placebo_expected": HARNESS_RANDOM_PINNED,
            "harness_placebo_bit_identical": placebo_ok,
            "tle_file_set_sha256": rows["MAX_NOMINAL_GAIN"]["tle_file_set_sha256"],
            "calibration_seeds": [list(x) for x in C.cal_seeds()],
            "arms": {n: {k: rows[n][k] for k in ("ee", "bits", "joules", "h_inter",
                                                  "h_intra", "served", "beams")}
                     for n in ARMS},
        }
        C.write_json(a.out / "calibration.json", out)
        print(json.dumps(out, indent=1))
        return 0 if placebo_ok else 3
    tle = tp.assert_tle_archive_pinned()
    t0 = time.time()
    res = run_arm(a.arm)
    res.update(arm=a.arm, tle_file_set_sha256=tle, tle_root=str(tp.resolve_tle_root()),
               wall_s=time.time() - t0)
    if a.arm == "TRAINED":
        res["checkpoint_sha256"] = C.sha256_file(C.TRAINED_CKPT)
    C.write_json(a.out / f"{a.arm}.json", res)
    print(a.arm, res["ee"], res["h_inter"], res["served"], res["beams"], res["wall_s"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
