#!/usr/bin/env python3
"""T0-REPR step 4d -- read-only aggregation of the result JSONs (no rollout, no fit).

R_repr = (EE(clone) - EE(A m=2dB)) / (EE(T0) - EE(A m=2dB)) per episode set, pooled ratio-of-sums EE, with
EE(T0) and EE(A m=2dB) from my placebo-verified rollouts on the SAME set.  Episode sets are never mixed.
Supplementary (not the declared metric): paired per-episode relative EE differences (mean +/- sem, wins) and a
10,000-resample episode-cluster bootstrap of R_repr (resample the 24 episodes with replacement, same indices
for all three arms, recompute the three pooled EEs; percentile 95 % interval).
Usage: t0_aggregate.py BC SOFT-tau<x>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tree" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import t0_common as T  # noqa: E402

import numpy as np  # noqa: E402

SETS = ("evaluation", "calibration")
B = 10_000
BOOT_SEED = 20260912


def ep_arrays(roll):
    return (np.array([r["bits"] for r in roll["episodes"]]), np.array([r["joules"] for r in roll["episodes"]]))


def paired(a, b):
    d = np.asarray(a) / np.asarray(b) - 1.0
    return {"mean": float(d.mean()), "sem": float(d.std(ddof=1) / np.sqrt(len(d))), "wins": int((d > 0).sum()),
            "n": int(len(d))}


def arm_row(roll, ref):
    return {"ee": roll["ee"], "pct_vs_ref": roll["ee"] / ref["ee"] - 1.0, "bits": roll["bits"], "joules": roll["joules"],
            "bits_over_ref": roll["bits"] / ref["bits"], "joules_over_ref": roll["joules"] / ref["joules"],
            "served": roll["served"], "beams": roll["beams"], "h_inter": roll["h_inter"], "h_intra": roll["h_intra"],
            "ho_per_user_min": roll["ho_per_user_min"],
            "rate_mean_bps": roll["per_served_user_rate_mean_bps"], "rate_p10_bps": roll["per_served_user_rate_p10_bps"],
            "rate_min_bps": roll["per_served_user_rate_min_bps"],
            "p10_over_ref": roll["per_served_user_rate_p10_bps"] / ref["per_served_user_rate_p10_bps"],
            "served_user_steps": roll["served_user_steps"], "user_steps": roll["user_steps"]}


def main() -> int:
    # usage: t0_aggregate.py [--out FILE.json] [--declared A,B] CLONE [CLONE ...]
    args = sys.argv[1:]
    out_name, declared = "AGGREGATE.json", None
    while args and args[0].startswith("--"):
        if args[0] == "--out":
            out_name, args = args[1], args[2:]
        elif args[0] == "--declared":
            declared, args = args[1].split(","), args[2:]
        else:
            raise SystemExit(f"unknown option {args[0]}")
    clones = args
    declared = declared or clones
    res = T.WS / "results"
    agg = {"sets": {}, "clones": {}, "code": T.code_ident()}
    ep_keys = {}
    for s in SETS:
        pl = json.loads((res / f"PLACEBO-{s}.json").read_text())
        assert pl["ok"], s
        t0r, ref = pl["T0"], pl["REF_A_m2dB"]
        ep_keys[s] = {(r["epoch"], r["t0_obs112_sha256"]) for r in t0r["episodes"]}
        S = {"T0": arm_row(t0r, ref), "A_m2dB": arm_row(ref, ref), "clones": {},
             "T0_gain_over_ref_pct": t0r["ee"] / ref["ee"] - 1.0}
        bt, jt = ep_arrays(t0r)
        br, jr = ep_arrays(ref)
        rng = np.random.default_rng(BOOT_SEED)
        idx = rng.integers(0, len(bt), size=(B, len(bt)))
        ee_t = bt[idx].sum(1) / jt[idx].sum(1)
        ee_r = br[idx].sum(1) / jr[idx].sum(1)
        for c in clones:
            cl = json.loads((res / f"CLOSED-{c}-{s}.json").read_text())
            roll = cl["rollout"]
            # the clone meets the same episodes (same start epoch + t=0 observation) as T0 and the reference
            same_eps = [(r["epoch"], r["t0_obs112_sha256"]) for r in roll["episodes"]] == \
                       [(r["epoch"], r["t0_obs112_sha256"]) for r in t0r["episodes"]]
            r_repr = (roll["ee"] - ref["ee"]) / (t0r["ee"] - ref["ee"])
            bc_, jc_ = ep_arrays(roll)
            ee_c = bc_[idx].sum(1) / jc_[idx].sum(1)
            rb = (ee_c - ee_r) / (ee_t - ee_r)
            row = arm_row(roll, ref)
            row.update({"R_repr": r_repr, "same_episodes_as_T0": bool(same_eps),
                        "paired_vs_T0": paired(roll["ee_ep"], t0r["ee_ep"]),
                        "paired_vs_ref": paired(roll["ee_ep"], ref["ee_ep"]),
                        "R_repr_bootstrap": {"B": B, "seed": BOOT_SEED, "p2.5": float(np.percentile(rb, 2.5)),
                                             "p50": float(np.percentile(rb, 50)), "p97.5": float(np.percentile(rb, 97.5)),
                                             "frac_ge_0.5": float((rb >= 0.5).mean())},
                        "onpolicy": {k: v for k, v in cl["onpolicy"].items() if k != "raw"},
                        "model_sha256": cl["model_sha256"], "tau": cl["tau"], "best_epoch": cl["model_best_epoch"]})
            S["clones"][c] = row
        S["T0_paired_vs_ref"] = paired(t0r["ee_ep"], ref["ee_ep"])
        agg["sets"][s] = S
    for c in clones:
        cj = json.loads((res / f"CLONE-{c}.json").read_text())
        agg["clones"][c] = {"test": cj["test"], "val_at_best": cj["val_at_best"], "train": cj["train"],
                            "best_epoch": cj["best_epoch"], "tau": cj["tau"], "counts": cj["counts"],
                            "model_sha256": cj["model_sha256"]}
        agg["clones"][c]["admitted_both_sets"] = all(agg["sets"][s]["clones"][c]["R_repr"] >= 0.5 for s in SETS)
    agg["admission"] = {"rule": "R_repr >= 0.5 for at least one clone on both episode sets (Amendment 3 §3)",
                        "read_on_declared_clones": declared,
                        "admitted": any(agg["clones"][c]["admitted_both_sets"] for c in declared),
                        "per_clone": {c: agg["clones"][c]["admitted_both_sets"] for c in clones}}
    coll = []
    for j in range(3):
        m = json.loads((T.WS / "data" / f"T0-collect-triple{j}.json").read_text())
        coll.append(m)
    ckeys = {(r["epoch"], r["t0_obs112_sha256"]) for m in coll for r in m["episode_rows"]}
    cepochs = {r["epoch"] for m in coll for r in m["episode_rows"]}
    agg["collection"] = {
        "episodes": sum(m["episodes"] for m in coll), "decisions": sum(m["decisions"] for m in coll),
        "empty_mask": sum(m["empty_mask_decisions"] for m in coll),
        "T0_pooled_ee_per_triple": [m["T0_pooled_ee_on_these_episodes"] for m in coll],
        "npz_sha256": [m["npz_sha256"] for m in coll],
        "seed_rule_check": coll[0]["seed_rule_check"]["single_env_vs_fresh_env_with_carried_age_state_identical"]
        if coll[0]["seed_rule_check"] else None,
        "overlap_epoch_and_t0hash_with_evaluation": len(ckeys & ep_keys["evaluation"]),
        "overlap_epoch_and_t0hash_with_calibration": len(ckeys & ep_keys["calibration"]),
        "overlap_start_epoch_only_with_evaluation": len(cepochs & {k[0] for k in ep_keys["evaluation"]}),
        "overlap_start_epoch_only_with_calibration": len(cepochs & {k[0] for k in ep_keys["calibration"]}),
        "distinct_start_epochs": len(cepochs)}
    ent = res / "ENTROPY.json"
    if ent.exists():
        agg["entropy"] = {k: v for k, v in json.loads(ent.read_text()).items() if k != "code"}
    T.write_json(res / out_name, agg)
    for s in SETS:
        S = agg["sets"][s]
        print(f"== {s}: T0 {S['T0']['ee']:.2f} ({S['T0_gain_over_ref_pct'] * 100:+.3f} % vs A m=2dB {S['A_m2dB']['ee']:.2f})")
        for c in clones:
            r = S["clones"][c]
            print(f"   {c}: ee={r['ee']:.2f} R_repr={r['R_repr']:.4f} boot95=[{r['R_repr_bootstrap']['p2.5']:.3f},"
                  f"{r['R_repr_bootstrap']['p97.5']:.3f}] served={r['served']:.5f} beams={r['beams']:.3f} "
                  f"agree={r['onpolicy']['onpolicy_agree_T0']:.4f} same_eps={r['same_episodes_as_T0']}")
    print("admission:", agg["admission"])
    print("collection:", {k: v for k, v in agg["collection"].items() if k != "npz_sha256"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
