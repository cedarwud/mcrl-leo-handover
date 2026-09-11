#!/usr/bin/env python3
"""H4 probe (measurement only, no training): for CF3PILOT final checkpoints,
measure

  (i)   the eta -> 0 argmax-flip fraction, evaluated on the DEPLOYED policy's
        own trajectory;
  (ii)  the closed-loop rollout under eta -> 0 vs deployed;
  (iii) the same for eta doubled (2 eta~), as a sensitivity;
  (iv)  the argmax-flip fraction between the deployed rule and the deployed
        rule with Q~_H included at lambda = 1 in the heads' units (a second
        sensitivity, report only) -- also evaluated on the deployed
        trajectory.

against the deployed rule Q~_B - eta~ Q~_E [- lambda Q~_H] (lambda is fixed
at 0 for A1-A3 per Amendment 2; asserted, not assumed).

This reuses cf3_common / cf3_eval / cf_ratio machinery VERBATIM (env_factory,
seeds, CFRatioTrainer.greedy_actions, cfr.pooled_rollout). It adds no new
physics and no new tie-breaking logic: all three score variants (deployed,
eta->0, lambda->1) go through the SAME tr.greedy_actions call, varying only
tr.eta (mutated immediately before the call and reset immediately after --
safe because eta_tilde is a @property read fresh each call, greedy_actions
consumes no RNG, and the trainer is never saved after mutation) and the
`lam` kwarg it already exposes. Comparing two DIFFERENT implementations
(e.g. mixing in cf3_common.masked_argmax) would risk counting a tie-break
implementation difference as a "flip"; this script never does that.

"Decision" = a user-step with masks[u].mask.any() (matches cf3_eval.py's own
cf_policy counting convention).

Usage: h4_sensitivity.py --arm A1|A2|A3 --results-dir DIR [--seeds 0,1,2]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = HERE.parent / "tree"
sys.path.insert(0, str(TREE / "src"))
sys.path.insert(0, str(TREE / "scripts"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

import cf3_common as C  # noqa: E402
import cf3_eval as E  # noqa: E402
from mcrl.algorithms import cf_ratio as cfr  # noqa: E402
from mcrl.runtime import training_pipeline as tp  # noqa: E402

EXPECTED_TLE_SHA = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
PILOT_WS = Path("/home/sat/mcrl-v025-cf3-pilot-ws")
ARM_DIR = {"A1": "OFF", "A2": "CF3", "A3": "NULL3"}
ROLLOUT_FIELDS = ("ee", "bits", "joules", "served", "h_inter", "h_intra", "beams")


def combined_policy(tr, eta_dep, counts):
    """Actual policy = deployed rule (eta=eta_dep, lam=0.0), which is what
    steps the env. At every decision ALSO scores (eta=0, lam=0) [-> (i)] and
    (eta=eta_dep, lam=1) [-> (iv)] with the SAME tr.greedy_actions function,
    and counts flips vs the deployed action among "decisions" (non-empty
    mask) only."""

    def pol(enc, masks, states):
        valid = np.array([m.mask.any() for m in masks])
        counts["decisions"] += int(valid.sum())
        tr.eta = eta_dep
        deployed = tr.greedy_actions(enc, masks, lam=0.0)
        tr.eta = 0.0
        eta0 = tr.greedy_actions(enc, masks, lam=0.0)
        tr.eta = eta_dep
        lam1 = tr.greedy_actions(enc, masks, lam=1.0)
        counts["changed_eta0"] += int(np.sum((deployed != eta0) & valid))
        counts["changed_lam1"] += int(np.sum((deployed != lam1) & valid))
        return deployed

    return pol


def eta_only_policy(tr, eta_value):
    """Closed-loop policy: greedy at (eta=eta_value, lam=0.0). The RETURNED
    actions are what steps the env (so divergence compounds through the
    trajectory), unlike combined_policy which always returns the deployed
    action."""

    def pol(enc, masks, states):
        tr.eta = eta_value
        return tr.greedy_actions(enc, masks, lam=0.0)

    return pol


def run_one(arm: str, seed: int, results_dir: Path) -> dict:
    label = f"{arm}s{seed}"
    out_path = results_dir / f"{label}-h4sensitivity.json"
    if out_path.exists():
        print(f"[skip:exists] {label}", flush=True)
        return json.loads(out_path.read_text())

    arm_dir = f"{arm}-{ARM_DIR[arm]}-s{seed}"
    ckpt = PILOT_WS / "runs" / arm_dir / "policy-ep01000.pt"
    if not ckpt.is_file():
        raise FileNotFoundError(ckpt)

    torch.set_num_threads(1)
    tle = tp.assert_tle_archive_pinned()
    if tle != EXPECTED_TLE_SHA:
        raise RuntimeError(f"TLE mismatch: {tle} != {EXPECTED_TLE_SHA}")

    factory = C.env_factory()
    t0 = time.time()
    tr, _pol, enc, meta = E.build("cf", ckpt, factory)
    if tr.lam != 0.0:
        raise RuntimeError(f"{label}: expected lambda fixed at 0 (Amendment 2), got {tr.lam}")
    eta_dep = tr.eta
    eta_tilde_dep = tr.eta_tilde

    seeds = C.eval_seeds()
    counts = {"decisions": 0, "changed_eta0": 0, "changed_lam1": 0}
    deployed_res = cfr.pooled_rollout(
        lambda i: combined_policy(tr, eta_dep, counts),
        env_factory=factory, encode=enc, seeds=seeds,
    )
    tr.eta = eta_dep  # restore (defensive; eta_only_policy sets it explicitly anyway)
    eta0_res = cfr.pooled_rollout(
        lambda i: eta_only_policy(tr, 0.0),
        env_factory=factory, encode=enc, seeds=seeds,
    )
    tr.eta = eta_dep
    eta2x_res = cfr.pooled_rollout(
        lambda i: eta_only_policy(tr, 2.0 * eta_dep),
        env_factory=factory, encode=enc, seeds=seeds,
    )
    tr.eta = eta_dep
    wall = time.time() - t0

    pilot_eval_path = PILOT_WS / "eval" / f"{label}.json"
    pilot_eval = json.loads(pilot_eval_path.read_text())
    cross_check = {f"{k}_bit_identical": bool(deployed_res[k] == pilot_eval[k]) for k in ROLLOUT_FIELDS}
    cross_check["all_bit_identical"] = all(cross_check.values())

    if counts["decisions"] == 0:
        raise RuntimeError(f"{label}: zero decisions counted -- something is wrong")

    payload = {
        "label": label,
        "arm": arm,
        "arm_dir": arm_dir,
        "seed": seed,
        "checkpoint": str(ckpt),
        "checkpoint_sha256": C.sha256_file(ckpt),
        "tle_file_set_sha256": tle,
        "meta": meta,
        "eta_deployed_bit_per_J": eta_dep,
        "eta_tilde_deployed_heads_units": eta_tilde_dep,
        "lambda_deployed": tr.lam,
        "decisions_total": counts["decisions"],
        "argmax_flip_fraction_eta_to_0": counts["changed_eta0"] / counts["decisions"],
        "argmax_flip_fraction_lambda_to_1": counts["changed_lam1"] / counts["decisions"],
        "deployed_rollout": {k: deployed_res[k] for k in ROLLOUT_FIELDS},
        "eta_to_0_closed_loop": {k: eta0_res[k] for k in ROLLOUT_FIELDS},
        "eta_doubled_closed_loop": {k: eta2x_res[k] for k in ROLLOUT_FIELDS},
        "eta_to_0_vs_deployed_relative_ee_change": (eta0_res["ee"] - deployed_res["ee"]) / deployed_res["ee"],
        "eta_doubled_vs_deployed_relative_ee_change": (eta2x_res["ee"] - deployed_res["ee"]) / deployed_res["ee"],
        "pilot_eval_reference": {k: pilot_eval[k] for k in ROLLOUT_FIELDS},
        "pilot_eval_cross_check": cross_check,
        "eval_seeds": [list(x) for x in seeds],
        "wall_s": wall,
    }
    C.write_json(out_path, payload)
    print(
        f"{label} flip_eta0={payload['argmax_flip_fraction_eta_to_0']:.6f} "
        f"flip_lam1={payload['argmax_flip_fraction_lambda_to_1']:.6f} "
        f"cross_check_ok={cross_check['all_bit_identical']} wall_s={wall:.1f}",
        flush=True,
    )
    if not cross_check["all_bit_identical"]:
        print(f"WARNING: {label} deployed rollout does not bit-match pilot eval JSON: {cross_check}", flush=True)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=("A1", "A2", "A3"))
    ap.add_argument("--seeds", default="0,1,2")
    ap.add_argument("--results-dir", type=Path, required=True)
    a = ap.parse_args()
    a.results_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in a.seeds.split(",")]
    any_bad = False
    for s in seeds:
        payload = run_one(a.arm, s, a.results_dir)
        if not payload["pilot_eval_cross_check"]["all_bit_identical"]:
            any_bad = True
    print(f"DONE arm={a.arm} seeds={seeds} any_cross_check_failed={any_bad}", flush=True)
    return 1 if any_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
