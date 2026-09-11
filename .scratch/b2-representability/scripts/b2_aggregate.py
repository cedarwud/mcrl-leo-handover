#!/usr/bin/env python3
"""B2-REPR step 5-6: R_repr, the degeneracy check and the reading.

R_repr = (EE(clone) - EE(A m=2dB)) / (EE(T_SEQ) - EE(A m=2dB)), all three pooled Sigma bits / Sigma J
on the SAME episode set.  Degeneracy (declared): served >= 0.995, bits ratio >= 0.95,
per-served-user p10 >= 0.5 x the rule's on the same set.
Bootstrap: 10,000 resamples of the 24 episodes, the SAME indices for clone, teacher and reference,
seed 20260912 (supplementary; the declared metric is the pooled point estimate).
Usage: b2_aggregate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_common as B  # noqa: E402

import numpy as np  # noqa: E402

SETS = ("evaluation", "calibration")
BOOT_N, BOOT_SEED = 10_000, 20260912


def ep_arrays(rows):
    return (np.array([r["bits"] for r in rows], dtype=np.float64),
            np.array([r["joules"] for r in rows], dtype=np.float64))


def teacher_eps(tag):
    bits, joules = [], []
    for i in range(24):
        r = json.loads((B.ORACLE_DIR / f"{B.TEACHER_STEM.format(tag=tag, i=i)}.json").read_text())
        bits.append(r["bits"])
        joules.append(r["joules"])
    return np.array(bits), np.array(joules)


def main() -> int:
    tle = B.boot()
    out = {"tle_file_set_sha256": tle, "code": B.code_ident(),
           "bootstrap": {"n": BOOT_N, "seed": BOOT_SEED,
                         "note": "episode-cluster resample, same indices for all three arms"},
           "sets": {}}
    for tag in SETS:
        ref = json.loads((B.WS / "results" / f"PLACEBO-REF-{tag}.json").read_text())
        refr = ref["result"]
        tea = json.loads((B.WS / "results" / f"TEACHER-{tag}.json").read_text())
        rb, rj = ep_arrays(refr["episodes"])
        tb, tj = teacher_eps(tag)
        assert abs(tb.sum() / tj.sum() - tea["ee"]) < 1e-6
        arms = {}
        for p in sorted((B.WS / "results").glob(f"CLOSED-*-{tag}.json")) + \
                sorted((B.WS / "results").glob(f"CLOSED-*-{tag}-rev.json")):
            rec = json.loads(p.read_text())
            r = rec["result"]
            cb, cj = ep_arrays(r["episodes"])
            ee_c, ee_t, ee_r = r["ee"], tea["ee"], refr["ee"]
            rr = (ee_c - ee_r) / (ee_t - ee_r)
            # paired per-episode % vs reference
            pe = 100.0 * (np.array(r["ee_ep"]) / np.array(refr["ee_ep"]) - 1.0)
            pt = 100.0 * (np.array(tea["ee_ep"]) / np.array(refr["ee_ep"]) - 1.0)
            g = np.random.default_rng(BOOT_SEED)
            idx = g.integers(0, 24, size=(BOOT_N, 24))
            bc = cb[idx].sum(1) / cj[idx].sum(1)
            bt = tb[idx].sum(1) / tj[idx].sum(1)
            br = rb[idx].sum(1) / rj[idx].sum(1)
            rr_b = (bc - br) / (bt - br)
            served_ok = r["served"] >= 0.995
            bits_ratio = r["bits"] / refr["bits"]
            p10_ratio = r["per_served_user_rate_p10_bps"] / refr["per_served_user_rate_p10_bps"]
            arms[rec["clone"] + ("-rev" if rec["order"] == "rev" else "")] = {
                "clone": rec["clone"], "order": rec["order"], "use_ctx": rec["use_ctx"],
                "state_dim": rec["state_dim"], "tau": rec["tau"], "best_epoch": rec["best_epoch"],
                "ee": ee_c, "pct_vs_rule": 100.0 * (ee_c / ee_r - 1.0),
                "R_repr": rr,
                "R_repr_boot_lo95": float(np.percentile(rr_b, 2.5)),
                "R_repr_boot_hi95": float(np.percentile(rr_b, 97.5)),
                "R_repr_boot_share_ge_0.5": float((rr_b >= 0.5).mean()),
                "paired_pct_vs_rule_mean": float(pe.mean()),
                "paired_pct_vs_rule_sem": float(pe.std(ddof=1) / np.sqrt(len(pe))),
                "paired_pct_vs_rule_n_positive": int((pe > 0).sum()),
                "served": r["served"], "served_ok_ge_0.995": bool(served_ok),
                "bits": r["bits"], "bits_ratio_vs_rule": bits_ratio,
                "bits_ratio_ok_ge_0.95": bool(bits_ratio >= 0.95),
                "joules_ratio_vs_rule": r["joules"] / refr["joules"],
                "beams": r["beams"], "h_inter": r["h_inter"], "h_intra": r["h_intra"],
                "ho_per_user_min": r["ho_per_user_min"],
                "rate_mean_bps": r["per_served_user_rate_mean_bps"],
                "rate_p10_bps": r["per_served_user_rate_p10_bps"],
                "rate_min_bps": r["per_served_user_rate_min_bps"],
                "p10_ratio_vs_rule": p10_ratio, "p10_ok_ge_0.5": bool(p10_ratio >= 0.5),
                "throughput_degenerate": bool(not (served_ok and bits_ratio >= 0.95 and p10_ratio >= 0.5)),
                "passes_condition3_on_this_set": bool(
                    rr >= 0.5 and served_ok and bits_ratio >= 0.95 and p10_ratio >= 0.5),
                "ee_ep": r["ee_ep"], "wall_s": rec["wall_s"], "model_sha256": rec["model_sha256"],
            }
        out["sets"][tag] = {
            "reference": {"arm": "C1_A_m2dB", "ee": refr["ee"], "served": refr["served"],
                          "bits": refr["bits"], "joules": refr["joules"], "beams": refr["beams"],
                          "h_inter": refr["h_inter"], "h_intra": refr["h_intra"],
                          "ho_per_user_min": refr["ho_per_user_min"],
                          "rate_mean_bps": refr["per_served_user_rate_mean_bps"],
                          "rate_p10_bps": refr["per_served_user_rate_p10_bps"],
                          "rate_min_bps": refr["per_served_user_rate_min_bps"],
                          "ee_ep": refr["ee_ep"],
                          "placebo_all_fields_equal": ref["comparison"]["all_equal"]},
            "teacher": {"arm": "B-real-floor-R1 (T_SEQ)", "ee": tea["ee"], "served": tea["served"],
                        "bits": tea["bits"], "joules": tea["joules"], "beams": tea["beams"],
                        "h_inter": tea["h_inter"], "h_intra": tea["h_intra"],
                        "ho_per_user_min": tea["ho_per_user_min"],
                        "rate_mean_bps": tea["per_served_user_rate_mean_bps"],
                        "rate_p10_bps": tea["per_served_user_rate_p10_bps"],
                        "rate_min_bps": tea["per_served_user_rate_min_bps"],
                        "pct_vs_rule": 100.0 * (tea["ee"] / refr["ee"] - 1.0),
                        "bits_ratio_vs_rule": tea["bits"] / refr["bits"],
                        "p10_ratio_vs_rule": tea["per_served_user_rate_p10_bps"] /
                        refr["per_served_user_rate_p10_bps"],
                        "ee_ep": tea["ee_ep"]},
            "arms": arms,
        }
    declared = ("BC", "SOFT-tau0.3")
    out["verdict"] = {
        "declared_clones": list(declared),
        "R_repr": {tag: {c: out["sets"][tag]["arms"][c]["R_repr"] for c in declared if c in out["sets"][tag]["arms"]}
                   for tag in SETS},
        "condition3_met": bool(any(
            all(c in out["sets"][t]["arms"] and out["sets"][t]["arms"][c]["passes_condition3_on_this_set"]
                for t in SETS) for c in declared)),
        "rule": "at least one declared clone with R_repr >= 0.5 on BOTH sets and not throughput-degenerate",
    }
    B.write_json(B.WS / "results" / "AGGREGATE.json", out)
    for tag in SETS:
        s = out["sets"][tag]
        print(f"\n== {tag} ==  rule {s['reference']['ee']:.2f}  teacher {s['teacher']['ee']:.2f} "
              f"(+{s['teacher']['pct_vs_rule']:.3f} %)")
        for k, v in s["arms"].items():
            print(f"  {k:<24s} ee={v['ee']:.2f} ({v['pct_vs_rule']:+.3f} %) R_repr={v['R_repr']:.4f} "
                  f"[{v['R_repr_boot_lo95']:.3f},{v['R_repr_boot_hi95']:.3f}] served={v['served']:.5f} "
                  f"bits={v['bits_ratio_vs_rule']:.4f} p10x={v['p10_ratio_vs_rule']:.3f} "
                  f"degen={v['throughput_degenerate']}")
    print(f"\nCONDITION 3 MET: {out['verdict']['condition3_met']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
