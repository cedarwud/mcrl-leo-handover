#!/usr/bin/env python3
"""CONVSCORE analysis: pure arithmetic on unmodified-scorer outputs.

Usage: analyse.py CONFIG.json OUT.json
CONFIG = {"runs": {tag: path/to/dual-axis-scores.json, ...},
          "pairs": [[tag_a, tag_b, "note"], ...]}      # paired marginal a-b by seed

Per run: per-seed arm rows (F6 row_type == arm), pooled-across-seeds arms
(sum bits / sum joules), route marginals FULL - X with the relative marginal's
denominator = comparator arm X's pooled EE, per-seed range and sign counts.
F8 (certified fixed point / anytime incumbent) is NOT read: contaminated axes.
"""
import json, math, resource, sys
from pathlib import Path

ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL")
COMPS = ("DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL")


def sign_counts(vals):
    pos = sum(v > 0 for v in vals); neg = sum(v < 0 for v in vals); zero = sum(v == 0 for v in vals)
    n = len(vals)
    status = ("ALL_POSITIVE" if pos == n else "ALL_NEGATIVE" if neg == n else
              "ALL_ZERO" if zero == n else "SIGN_FLIPS_ACROSS_SEEDS")
    return pos, neg, zero, status


def load_run(path):
    doc = json.loads(Path(path).read_text())
    rows = {}
    for r in doc["tables"]["F6_ablation"]:
        if r["row_type"] != "arm":
            continue
        rows.setdefault(r["learner_seed"], {})[r["arm"]] = r
    ck = {c["checkpoint"]["learner_seed"]: {
        "path": c["checkpoint"]["path"], "sha256": c["checkpoint"]["sha256"],
        "completed_source_epochs": c["checkpoint"]["completed_source_epochs"],
        "knockout_differing_anchors": c["knockout_check"]["differing_anchor_count"],
        "knockout_anchor_count": c["knockout_check"]["anchor_count"],
    } for c in doc["checkpoints"]}
    seeds = sorted(rows)
    run = {"scores_path": str(path), "scorer_sha256": doc["scorer_sha256"],
           "panel_path": doc["panel"]["path"], "panel_sha256": doc["panel"]["sha256"],
           "panel_anchors": doc["panel"]["identity"]["anchors"],
           "primary_contrast_interpretation": doc["primary_contrast_interpretation"],
           "neutral_and_knockout_coincide_everywhere": doc["neutral_and_knockout_coincide_everywhere"],
           "seeds": seeds, "checkpoints": ck,
           "epochs_present": sorted({v["completed_source_epochs"] for v in ck.values()}),
           "scorer_peak_rss_bytes": doc.get("resource_limits", {}).get("peak_rss_bytes")}
    per_seed = {}
    for s in seeds:
        e = {}
        for arm in ARMS:
            r = rows[s][arm]
            e[arm] = {k: r[k] for k in ("pooled_ee_bits_per_j", "full_buffer_bits", "joules",
                                        "service_available", "service_opportunities",
                                        "rate_target_attained", "rate_target_opportunities",
                                        "handovers", "handover_opportunities")}
        e["marginals"] = {}
        for c in COMPS:
            a = e["FULL"]["pooled_ee_bits_per_j"]; b = e[c]["pooled_ee_bits_per_j"]
            e["marginals"][f"FULL-minus-{c}"] = {"abs": a - b, "rel_to_comparator": (a - b) / b if b else None}
        per_seed[str(s)] = e
    run["per_seed"] = per_seed
    pooled = {}
    for arm in ARMS:
        bits = math.fsum(per_seed[str(s)][arm]["full_buffer_bits"] for s in seeds)
        joules = math.fsum(per_seed[str(s)][arm]["joules"] for s in seeds)
        ees = [per_seed[str(s)][arm]["pooled_ee_bits_per_j"] for s in seeds]
        sa = sum(per_seed[str(s)][arm]["service_available"] for s in seeds)
        so = sum(per_seed[str(s)][arm]["service_opportunities"] for s in seeds)
        pooled[arm] = {"pooled_ee_bits_per_j": bits / joules, "bits": bits, "joules": joules,
                       "served": sa, "service_opportunities": so, "service_availability": sa / so if so else None,
                       "per_seed_ee_min": min(ees), "per_seed_ee_max": max(ees),
                       "per_seed_ee_mean": math.fsum(ees) / len(ees)}
    run["pooled"] = pooled
    marg = {}
    for c in COMPS:
        k = f"FULL-minus-{c}"
        per = [per_seed[str(s)]["marginals"][k]["abs"] for s in seeds]
        rel = [per_seed[str(s)]["marginals"][k]["rel_to_comparator"] for s in seeds]
        pos, neg, zero, status = sign_counts(per)
        a = pooled["FULL"]["pooled_ee_bits_per_j"]; b = pooled[c]["pooled_ee_bits_per_j"]
        marg[k] = {"pooled_abs_bits_per_j": a - b, "pooled_rel_denominator_comparator": (a - b) / b,
                   "comparator_pooled_ee_bits_per_j": b,
                   "per_seed_min": min(per), "per_seed_max": max(per), "per_seed_mean": math.fsum(per) / len(per),
                   "per_seed_rel_min": min(rel), "per_seed_rel_max": max(rel),
                   "seeds_pos": pos, "seeds_neg": neg, "seeds_zero": zero, "n": len(per), "status": status}
    run["marginals"] = marg
    return run


def paired(ra, rb, note):
    common = sorted(set(ra["seeds"]) & set(rb["seeds"]))
    out = {"n_common_seeds": len(common), "identical_seed_sets": set(ra["seeds"]) == set(rb["seeds"]),
           "same_panel_sha256": ra["panel_sha256"] == rb["panel_sha256"], "note": note, "marginals": {},
           "arm_levels": {}}
    for c in COMPS:
        k = f"FULL-minus-{c}"
        d = [ra["per_seed"][str(s)]["marginals"][k]["abs"] - rb["per_seed"][str(s)]["marginals"][k]["abs"]
             for s in common]
        pos, neg, zero, status = sign_counts(d)
        out["marginals"][k] = {"per_seed_mean_diff": math.fsum(d) / len(d), "min": min(d), "max": max(d),
                               "seeds_a_larger": pos, "seeds_a_smaller": neg, "seeds_equal": zero,
                               "status": status,
                               "pooled_marginal_diff": ra["marginals"][k]["pooled_abs_bits_per_j"]
                               - rb["marginals"][k]["pooled_abs_bits_per_j"]}
    if out["same_panel_sha256"]:
        for arm in ARMS:
            d = [ra["per_seed"][str(s)][arm]["pooled_ee_bits_per_j"] - rb["per_seed"][str(s)][arm]["pooled_ee_bits_per_j"]
                 for s in common]
            pos, neg, zero, status = sign_counts(d)
            out["arm_levels"][arm] = {"per_seed_mean_diff": math.fsum(d) / len(d), "min": min(d), "max": max(d),
                                      "seeds_a_larger": pos, "seeds_a_smaller": neg, "seeds_equal": zero,
                                      "status": status}
    return out


def main():
    cfg = json.loads(Path(sys.argv[1]).read_text())
    out = {"config": cfg, "runs": {}, "pairs": {}}
    for tag, p in cfg["runs"].items():
        out["runs"][tag] = load_run(p)
    for a, b, note in cfg.get("pairs", []):
        out["pairs"][f"{a}__minus__{b}"] = paired(out["runs"][a], out["runs"][b], note)
    out["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, sort_keys=True))
    for tag, r in out["runs"].items():
        print(f"== {tag} epochs={r['epochs_present']} seeds={len(r['seeds'])} panel={r['panel_sha256'][:12]}")
        for arm, v in r["pooled"].items():
            print(f"  {arm:20s} EE={v['pooled_ee_bits_per_j']/1e6:.6f} Mbit/J  served={v['served']}/{v['service_opportunities']}")
        for k, m in r["marginals"].items():
            print(f"  {k:32s} {m['pooled_abs_bits_per_j']/1e6:+.6f} ({100*m['pooled_rel_denominator_comparator']:+.4f}%) "
                  f"+{m['seeds_pos']}/-{m['seeds_neg']}/0{m['seeds_zero']} {m['status']}")
    for k, p in out["pairs"].items():
        print(f"== pair {k} same_panel={p['same_panel_sha256']} n={p['n_common_seeds']}")
        for mk, m in p["marginals"].items():
            print(f"  {mk:32s} mean {m['per_seed_mean_diff']/1e6:+.6f} [{m['min']/1e6:+.6f},{m['max']/1e6:+.6f}] "
                  f"a>b {m['seeds_a_larger']} a<b {m['seeds_a_smaller']} {m['status']}")
    print(f"PEAK_RSS_BYTES={out['peak_rss_bytes']}")


if __name__ == "__main__":
    main()
