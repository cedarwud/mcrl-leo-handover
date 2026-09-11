#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""MULTISTEP analysis.  Pure arithmetic over the endpoint receipts; no physics.

usage: analyze.py <panel.json> <panel-rerun.json> <oracle-w0.json> [<oracle-w1.json> ...]
                  --rerun <oracle-rerun-w0.json> ... (optional)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
import sys

POLICIES = ("b_rss", "b_base", "a_hold")
SEGMENTS = {"t": (0,), "t+1": (1,), "t+2": (2,), "t+3": (3,), "future": (1, 2, 3), "cum": (0, 1, 2, 3)}
REPS = 2000
SEED = 20260911


def pool(records, arm, policy, offsets):
    rows = [r["arms"][arm][policy][k] for r in records for k in offsets]
    if any(row["invalid"] for row in rows):
        raise RuntimeError(f"invalid profile in {arm}/{policy}")
    bits = math.fsum(row["bits"] for row in rows)
    joules = math.fsum(row["joules"] for row in rows)
    users = sum(row["users"] for row in rows)
    return {
        "bits": bits,
        "joules": joules,
        "ee_mbit_per_j": bits / joules / 1e6,
        "served_fraction": sum(row["served"] for row in rows) / users,
        "attainment_fraction": sum(row["attained"] for row in rows) / users,
        "served": sum(row["served"] for row in rows),
        "attained": sum(row["attained"] for row in rows),
        "user_slots": users,
        "association_changes": sum(row["association_changes"] for row in rows),
        "satellite_changes": sum(row["counts"].get("satellite_change", 0) for row in rows),
        "beam_changes": sum(row["counts"].get("beam_change", 0) for row in rows),
        "phi_qos_preference": math.fsum(row["phi_qos_preference"] for row in rows),
    }


def ee(b, j):
    return b / j / 1e6


def split(records, a, r, policy):
    """Two-factor Shapley split of the cumulative pooled-EE difference a - r into
    a step-t part and a t+1..t+3 part.  Exact: parts sum to the total."""
    at, af = pool(records, a, policy, (0,)), pool(records, a, policy, (1, 2, 3))
    rt, rf = pool(records, r, policy, (0,)), pool(records, r, policy, (1, 2, 3))

    def mix(x, y):
        return ee(x["bits"] + y["bits"], x["joules"] + y["joules"])

    aa, ar, ra, rr = mix(at, af), mix(at, rf), mix(rt, af), mix(rt, rf)
    part_t = 0.5 * ((ar - rr) + (aa - ra))
    part_f = 0.5 * ((ra - rr) + (aa - ar))
    return {"total_mbit_per_j": aa - rr, "step_t_part": part_t, "future_part": part_f,
            "relative_total": aa / rr - 1.0,
            "step_t_part_relative_to_ref_cum": part_t / rr,
            "future_part_relative_to_ref_cum": part_f / rr}


def contrast(records, a, r, policy):
    out = {}
    for name, offsets in SEGMENTS.items():
        pa, pr = pool(records, a, policy, offsets), pool(records, r, policy, offsets)
        out[name] = {
            "delta_mbit_per_j": pa["ee_mbit_per_j"] - pr["ee_mbit_per_j"],
            "relative": pa["ee_mbit_per_j"] / pr["ee_mbit_per_j"] - 1.0,
            "delta_bits": pa["bits"] - pr["bits"],
            "delta_joules": pa["joules"] - pr["joules"],
            "delta_served": pa["served"] - pr["served"],
            "delta_attained": pa["attained"] - pr["attained"],
        }
    out["shapley"] = split(records, a, r, policy)
    return out


def future_identical(records, arms, policy):
    """Count anchors whose t+1..t+3 bits AND joules are bit-identical across arms."""
    same = 0
    for r in records:
        ref = [(row["bits"], row["joules"]) for row in r["arms"][arms[0]][policy][1:]]
        if all([(row["bits"], row["joules"]) for row in r["arms"][arm][policy][1:]] == ref for arm in arms[1:]):
            same += 1
    return same


def per_anchor_signs(records, a, r, policy, offsets):
    better = worse = equal = 0
    for rec in records:
        pa = pool([rec], a, policy, offsets)["ee_mbit_per_j"]
        pr = pool([rec], r, policy, offsets)["ee_mbit_per_j"]
        if pa > pr:
            better += 1
        elif pa < pr:
            worse += 1
        else:
            equal += 1
    return {"better": better, "worse": worse, "equal": equal}


def bootstrap(records, a, r, policy):
    clusters = {}
    for rec in records:
        clusters.setdefault((rec["world_index"], rec["step_index"]), []).append(rec)
    keys = sorted(clusters)
    rng = random.Random(SEED)
    stats = {"rel_t": [], "rel_future": [], "rel_cum": [], "shapley_t": [], "shapley_future": [],
             "delta_future": []}
    for _ in range(REPS):
        sample = [rec for _k in keys for rec in clusters[keys[rng.randrange(len(keys))]]]
        c = contrast(sample, a, r, policy)
        stats["rel_t"].append(c["t"]["relative"])
        stats["rel_future"].append(c["future"]["relative"])
        stats["rel_cum"].append(c["cum"]["relative"])
        stats["shapley_t"].append(c["shapley"]["step_t_part"])
        stats["shapley_future"].append(c["shapley"]["future_part"])
        stats["delta_future"].append(c["future"]["delta_mbit_per_j"])
    out = {"clusters": len(keys), "reps": REPS, "seed": SEED,
           "cluster_unit": "(world, step): the carrier anchors of one decision instant"}
    for name, values in stats.items():
        values.sort()
        out[name] = [values[int(0.025 * REPS)], values[int(0.975 * REPS) - 1]]
    return out


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(math.fsum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(math.fsum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            out[order[k]] = average
        i = j + 1
    return out


def spearman(xs, ys):
    return pearson(ranks(xs), ranks(ys))


FORECAST_PROFILES = ("RSS_MAX", "C1_ONLY", "FULL", "C2_ONLY", "C2_WORST")


def forecast_stats(records):
    """Predicted (nominal boundary-0 snapshot) versus realised (full-48) change
    of the same held profiles, per v1.6 section 2(b)."""
    rows = []
    for rec in records:
        block = rec["forecast"]
        for name in FORECAST_PROFILES:
            for entry in block["per_offset"][name]:
                rows.append({
                    "anchor": rec["global_anchor_index"], "profile": name, "offset": entry["offset"],
                    "predicted": entry["delta_f_nominal_b0"], "realised": entry["delta_f_realised_48"],
                    "error_total": entry["error_total"],
                    "error_integration": entry["error_integration"],
                    "error_fading": entry["error_fading"],
                    "error_fading_at_b0": entry["error_fading_at_b0"],
                    "error_integration_realised": entry["error_integration_realised"],
                    "pred_valid": entry["surfaces"]["nominal_b0"]["valid"],
                    "real_valid": entry["surfaces"]["realised_48"]["valid"],
                    "pred_survives": entry["surfaces"]["nominal_b0"]["survives"],
                    "real_survives": entry["surfaces"]["realised_48"]["survives"],
                })

    def block_stats(subset):
        if not subset:
            return None
        pred = [r["predicted"] for r in subset]
        real = [r["realised"] for r in subset]
        err = [p - q for p, q in zip(pred, real)]
        n = len(subset)
        return {
            "n": n,
            "pearson": pearson(pred, real),
            "spearman": spearman(pred, real),
            "mean_predicted": sum(pred) / n,
            "mean_realised": sum(real) / n,
            "bias_pred_minus_real": sum(err) / n,
            "mean_abs_error": sum(abs(e) for e in err) / n,
            "rmse": math.sqrt(math.fsum(e * e for e in err) / n),
            "sd_realised": math.sqrt(math.fsum((r - sum(real) / n) ** 2 for r in real) / max(1, n - 1)),
            "mean_error_integration": math.fsum(r["error_integration"] for r in subset) / n,
            "mean_error_fading": math.fsum(r["error_fading"] for r in subset) / n,
            "mean_abs_error_integration": math.fsum(abs(r["error_integration"]) for r in subset) / n,
            "mean_abs_error_fading": math.fsum(abs(r["error_fading"]) for r in subset) / n,
            "mean_abs_error_fading_at_b0": math.fsum(abs(r["error_fading_at_b0"]) for r in subset) / n,
            "mean_abs_error_integration_realised": math.fsum(
                abs(r["error_integration_realised"]) for r in subset) / n,
            "sign_agreement": sum(1 for p, q in zip(pred, real) if (p > 0) == (q > 0)) / n,
            "predicted_positive": sum(1 for p in pred if p > 0),
            "realised_positive": sum(1 for q in real if q > 0),
            "survival_agreement": sum(1 for r in subset if r["pred_survives"] == r["real_survives"]) / n,
            "predicted_survives": sum(1 for r in subset if r["pred_survives"]),
            "realised_survives": sum(1 for r in subset if r["real_survives"]),
            "predicted_invalid": sum(1 for r in subset if not r["pred_valid"]),
            "realised_invalid": sum(1 for r in subset if not r["real_valid"]),
        }

    out = {
        "pooled": block_stats(rows),
        "by_offset": {str(k): block_stats([r for r in rows if r["offset"] == k]) for k in (1, 2, 3)},
        "by_profile": {name: block_stats([r for r in rows if r["profile"] == name])
                       for name in FORECAST_PROFILES},
    }

    # C2 label level: predicted (nominal_b0) versus realised (realised_48)
    label_rows = []
    per_anchor_rank = []
    for rec in records:
        labels = rec["forecast"]["c2_labels"]
        pred = [labels[name]["nominal_b0"]["normalized_total_kappa"] for name in FORECAST_PROFILES]
        real = [labels[name]["realised_48"]["normalized_total_kappa"] for name in FORECAST_PROFILES]
        for name, p, q in zip(FORECAST_PROFILES, pred, real):
            label_rows.append({
                "anchor": rec["global_anchor_index"], "profile": name, "predicted": p, "realised": q,
                "pred_lost": labels[name]["nominal_b0"]["lost_offsets"],
                "real_lost": labels[name]["realised_48"]["lost_offsets"],
            })
        rho = spearman(pred, real)
        best_pred = FORECAST_PROFILES[max(range(len(pred)), key=lambda i: pred[i])]
        best_real = FORECAST_PROFILES[max(range(len(real)), key=lambda i: real[i])]
        worst_pred = FORECAST_PROFILES[min(range(len(pred)), key=lambda i: pred[i])]
        worst_real = FORECAST_PROFILES[min(range(len(real)), key=lambda i: real[i])]
        per_anchor_rank.append({
            "anchor": rec["global_anchor_index"], "spearman": rho,
            "top1_agree": best_pred == best_real, "bottom1_agree": worst_pred == worst_real,
            "best_predicted": best_pred, "best_realised": best_real,
        })
    pred = [r["predicted"] for r in label_rows]
    real = [r["realised"] for r in label_rows]
    n = len(label_rows)
    rhos = [r["spearman"] for r in per_anchor_rank if r["spearman"] is not None]
    out["c2_label"] = {
        "n": n,
        "pearson": pearson(pred, real),
        "spearman": spearman(pred, real),
        "bias_pred_minus_real_kappa": math.fsum(p - q for p, q in zip(pred, real)) / n,
        "mean_abs_error_kappa": math.fsum(abs(p - q) for p, q in zip(pred, real)) / n,
        "mean_predicted_kappa": sum(pred) / n,
        "mean_realised_kappa": sum(real) / n,
        "sign_agreement": sum(1 for p, q in zip(pred, real) if (p > 0) == (q > 0)) / n,
        "lost_offsets_agreement": sum(1 for r in label_rows if r["pred_lost"] == r["real_lost"]) / n,
        "predicted_lost_total": sum(r["pred_lost"] for r in label_rows),
        "realised_lost_total": sum(r["real_lost"] for r in label_rows),
        "within_anchor_rank": {
            "anchors": len(per_anchor_rank),
            "anchors_with_defined_spearman": len(rhos),
            "mean_spearman": (sum(rhos) / len(rhos)) if rhos else None,
            "median_spearman": sorted(rhos)[len(rhos) // 2] if rhos else None,
            "top1_agreement": sum(1 for r in per_anchor_rank if r["top1_agree"]) / len(per_anchor_rank),
            "bottom1_agreement": sum(1 for r in per_anchor_rank if r["bottom1_agree"]) / len(per_anchor_rank),
        },
        "per_anchor": per_anchor_rank,
    }
    return out


def arm_tables(records, arms):
    return {
        policy: {
            arm: {seg: pool(records, arm, policy, offs) for seg, offs in SEGMENTS.items()}
            for arm in arms
        }
        for policy in POLICIES
    }


def compare_runs(a_records, b_records):
    key = lambda rec: rec["global_anchor_index"]
    a_map, b_map = {key(r): r for r in a_records}, {key(r): r for r in b_records}
    if set(a_map) != set(b_map):
        return {"identical": False, "reason": "anchor sets differ"}
    mismatches = 0
    compared = 0
    for index, ra in a_map.items():
        rb = b_map[index]
        for arm, policies in ra["arms"].items():
            for policy, rows in policies.items():
                for x, y in zip(rows, rb["arms"][arm][policy], strict=True):
                    compared += 1
                    if (x["bits"], x["joules"], x["served"], x["attained"], x["cid_sha256"]) != (
                        y["bits"], y["joules"], y["served"], y["attained"], y["cid_sha256"]
                    ):
                        mismatches += 1
    return {"identical": mismatches == 0, "compared_rows": compared, "mismatched_rows": mismatches}


def main(argv):
    args = list(argv)
    rerun = []
    if "--rerun" in args:
        i = args.index("--rerun")
        rerun = args[i + 1:]
        args = args[:i]
    panel_a, panel_b, *oracle_paths = args
    pa = json.loads(Path(panel_a).read_text())
    pb = json.loads(Path(panel_b).read_text())
    panel = pa["records"]
    result = {"panel": {
        "parity": pa["parity"],
        "parity_rerun": pb["parity"],
        "determinism": compare_runs(pa["records"], pb["records"]),
        "scalar_calls": [pa["scalar_evaluate_calls"], pb["scalar_evaluate_calls"]],
        "invariance_probes": [pa["invariance_probes_all_equal"], pa["invariance_probe_count"]],
        "peak_rss_bytes": [pa["peak_rss_bytes"], pb["peak_rss_bytes"]],
        "tables": arm_tables(panel, ("BASE", "RSS_MAX", "CROWDED")),
        "future_identical_anchors": {
            policy: future_identical(panel, ("BASE", "RSS_MAX", "CROWDED"), policy) for policy in POLICIES
        },
        "contrasts": {
            policy: {
                "CROWDED_vs_RSS_MAX": contrast(panel, "CROWDED", "RSS_MAX", policy),
                "CROWDED_vs_BASE": contrast(panel, "CROWDED", "BASE", policy),
                "RSS_MAX_vs_BASE": contrast(panel, "RSS_MAX", "BASE", policy),
            }
            for policy in POLICIES
        },
        "per_anchor_signs_CROWDED_vs_RSS": {
            policy: {seg: per_anchor_signs(panel, "CROWDED", "RSS_MAX", policy, offs)
                     for seg, offs in SEGMENTS.items()}
            for policy in POLICIES
        },
        "per_anchor_a_hold": [
            {
                "anchor": rec["global_anchor_index"], "step": rec["step_index"], "carrier": rec["carrier"],
                **{f"{arm}_{k}": rec["arms"][arm]["a_hold"][k]["bits"] / rec["arms"][arm]["a_hold"][k]["joules"] / 1e6
                   for arm in ("RSS_MAX", "CROWDED", "BASE") for k in range(4)},
            }
            for rec in panel
        ],
    }}
    if oracle_paths:
        records = []
        rss = []
        calls = 0
        probes = []
        for path in oracle_paths:
            payload = json.loads(Path(path).read_text())
            records.extend(payload["records"])
            rss.append(payload["peak_rss_bytes"])
            calls += payload["scalar_evaluate_calls"]
            probes.append([payload["invariance_probes_all_equal"], payload["invariance_probe_count"]])
        records.sort(key=lambda rec: rec["global_anchor_index"])
        if len({rec["global_anchor_index"] for rec in records}) != len(records):
            raise RuntimeError("duplicate anchors")
        arms = ("BASE", "C1_ONLY", "FULL", "C2_ONLY", "C2_WORST", "RSS_MAX")
        subsets = {
            "all_93": records,
            "subset_22": [rec for rec in records if rec["world_index"] == 1 and rec["global_anchor_index"] < 22],
            "panel_12": [rec for rec in records if rec["world_index"] == 1 and rec["global_anchor_index"] < 12],
            "changed_30": [rec for rec in records if rec["full_differs_from_c1_only"]],
        }
        oracle = {
            "anchors": len(records),
            "scalar_calls": calls,
            "invariance_probes": probes,
            "peak_rss_bytes": rss,
            "future_identical_anchors": {
                policy: future_identical(records, arms, policy) for policy in POLICIES
            },
            "subsets": {},
        }
        for name, subset in subsets.items():
            entry = {
                "anchors": len(subset),
                "global_anchor_indices": [rec["global_anchor_index"] for rec in subset],
                "tables": arm_tables(subset, arms),
                "FULL_vs_C1_ONLY": {policy: contrast(subset, "FULL", "C1_ONLY", policy) for policy in POLICIES},
                "C2_ONLY_vs_C1_ONLY": {policy: contrast(subset, "C2_ONLY", "C1_ONLY", policy) for policy in POLICIES},
                "C1_ONLY_vs_RSS_MAX": {policy: contrast(subset, "C1_ONLY", "RSS_MAX", policy) for policy in POLICIES},
                "signs_FULL_vs_C1_ONLY": {
                    policy: {seg: per_anchor_signs(subset, "FULL", "C1_ONLY", policy, offs)
                             for seg, offs in SEGMENTS.items()}
                    for policy in POLICIES
                },
            }
            if name in ("all_93", "subset_22"):
                entry["bootstrap_FULL_vs_C1_ONLY"] = {
                    policy: bootstrap(subset, "FULL", "C1_ONLY", policy) for policy in ("b_rss", "a_hold")
                }
            entry["forecast_validity"] = forecast_stats(subset)
            oracle["subsets"][name] = entry
        if rerun:
            rr = []
            for path in rerun:
                rr.extend(json.loads(Path(path).read_text())["records"])
            oracle["determinism"] = compare_runs(records, rr)
        result["oracle"] = oracle
    out = Path("/home/sat/mcrl-v025-multistep-ws/out/analysis.json")
    out.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
