#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Merge the C2TARGET oracle-EE worker outputs.  Pure arithmetic; no physics."""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
import resource
import sys

OUTDIR = Path("/home/sat/mcrl-v025-c2target-ws/.scratch/c2target")
ARMS = ("BASE", "C1_ONLY", "FULL", "C2_ONLY", "EE_B0_BEST")


def pooled(records, arm):
    rows = [row["arms"][arm] for row in records if not row["arms"][arm]["invalid"]]
    bits = math.fsum(row["bits"] for row in rows)
    joules = math.fsum(row["joules"] for row in rows)
    users = sum(row["users"] for row in rows)
    return {
        "anchors": len(rows),
        "bits": bits,
        "joules": joules,
        "pooled_ee_mbit_per_j": bits / joules / 1e6,
        "served_fraction": sum(row["served_users"] for row in rows) / users,
        "rate_target_attainment_fraction": sum(row["attained_users"] for row in rows) / users,
    }


def rel(records, a, b):
    pa, pb = pooled(records, a), pooled(records, b)
    return pa["pooled_ee_mbit_per_j"] / pb["pooled_ee_mbit_per_j"] - 1.0


def cluster_bootstrap(records, a, b, reps=2000, seed=20260911):
    clusters = {}
    for row in records:
        clusters.setdefault((row["world_index"], row["step_index"]), []).append(row)
    keys = sorted(clusters)
    rng = random.Random(seed)
    values = []
    for _ in range(reps):
        sample = [row for _k in keys for row in clusters[keys[rng.randrange(len(keys))]]]
        values.append(rel(sample, a, b))
    values.sort()
    return {
        "clusters": len(keys),
        "cluster_unit": "(world, step): the three carrier anchors of one decision instant",
        "reps": reps,
        "p2_5": values[int(0.025 * reps)],
        "p97_5": values[int(0.975 * reps) - 1],
    }


def main() -> int:
    stem = sys.argv[1]
    workers = int(sys.argv[2])
    expected = int(sys.argv[3])
    records = []
    stub = {"selection": 0, "endpoint": 0}
    peaks = []
    for worker in range(workers):
        payload = json.loads((OUTDIR / f"{stem}-w{worker}.json").read_text())
        records.extend(payload["records"])
        for key in stub:
            stub[key] += int(payload["evaluate_stub_calls"][key])
        peaks.append(int(payload["peak_rss_kb"]))
    keys = [(row["world_index"], row["global_anchor_index"]) for row in records]
    if len(set(keys)) != len(keys) or len(keys) != expected:
        raise RuntimeError(f"anchor set wrong: {len(keys)} records, {len(set(keys))} unique")
    records.sort(key=lambda row: (row["world_index"], row["global_anchor_index"]))

    differs = [row for row in records if row["full_differs_from_c1_only"]]
    per_anchor = []
    for row in records:
        arms = row["arms"]
        per_anchor.append({
            "world": row["world_index"],
            "anchor": row["global_anchor_index"],
            "step": row["step_index"],
            "carrier": row["carrier"],
            "catalogue": row["catalogue_size"],
            "uncovered": row["catalogue_uncovered"],
            "full_differs_from_c1_only": row["full_differs_from_c1_only"],
            **{
                f"{arm}_ee": arms[arm].get("ee_bits_per_j", 0.0) / 1e6 for arm in ARMS
            },
            **{f"{arm}_served": arms[arm].get("served_fraction") for arm in ARMS},
            **{f"{arm}_attained": arms[arm].get("rate_target_attainment_fraction") for arm in ARMS},
            **{f"{arm}_kind": arms[arm].get("kind") for arm in ARMS},
            **{f"{arm}_changed": arms[arm].get("changed_users") for arm in ARMS},
            **{f"{arm}_b0rank": arms[arm]["boundary_0"]["rank_of_realised_b0_ee"] for arm in ARMS},
        })

    paired = []
    for row in differs:
        full = row["arms"]["FULL"]
        c1 = row["arms"]["C1_ONLY"]
        paired.append(full["ee_bits_per_j"] / c1["ee_bits_per_j"] - 1.0)

    worlds = sorted({row["world_index"] for row in records})
    result = {
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "anchors": len(records),
        "evaluate_stub_calls_total": stub,
        "worker_peak_rss_kb": peaks,
        "pooled": {arm: pooled(records, arm) for arm in ARMS},
        "pooled_by_world": {
            str(world): {arm: pooled([r for r in records if r["world_index"] == world], arm) for arm in ARMS}
            for world in worlds
        },
        "relative": {
            "FULL_vs_C1_ONLY": rel(records, "FULL", "C1_ONLY"),
            "C2_ONLY_vs_C1_ONLY": rel(records, "C2_ONLY", "C1_ONLY"),
            "FULL_vs_C2_ONLY": rel(records, "FULL", "C2_ONLY"),
            "C1_ONLY_vs_BASE": rel(records, "C1_ONLY", "BASE"),
            "FULL_vs_BASE": rel(records, "FULL", "BASE"),
            "C2_ONLY_vs_BASE": rel(records, "C2_ONLY", "BASE"),
            "EE_B0_BEST_vs_BASE": rel(records, "EE_B0_BEST", "BASE"),
            "FULL_vs_EE_B0_BEST": rel(records, "FULL", "EE_B0_BEST"),
            "C1_ONLY_vs_EE_B0_BEST": rel(records, "C1_ONLY", "EE_B0_BEST"),
        },
        "absolute_mbit_per_j": {
            "FULL_minus_C1_ONLY": pooled(records, "FULL")["pooled_ee_mbit_per_j"] - pooled(records, "C1_ONLY")["pooled_ee_mbit_per_j"],
            "C2_ONLY_minus_C1_ONLY": pooled(records, "C2_ONLY")["pooled_ee_mbit_per_j"] - pooled(records, "C1_ONLY")["pooled_ee_mbit_per_j"],
        },
        "bootstrap": {
            "FULL_vs_C1_ONLY": cluster_bootstrap(records, "FULL", "C1_ONLY"),
            "C2_ONLY_vs_C1_ONLY": cluster_bootstrap(records, "C2_ONLY", "C1_ONLY"),
        },
        "decision_changes": {
            "anchors_full_differs_from_c1_only": len(differs),
            "anchors_c2_only_differs_from_c1_only": sum(
                1 for row in records
                if row["arms"]["C2_ONLY"]["configuration_id"] != row["arms"]["C1_ONLY"]["configuration_id"]
            ),
            "anchors_c1_only_equals_ee_b0_best": sum(
                1 for row in records
                if row["arms"]["C1_ONLY"]["configuration_id"] == row["arms"]["EE_B0_BEST"]["configuration_id"]
            ),
            "anchors_full_equals_ee_b0_best": sum(
                1 for row in records
                if row["arms"]["FULL"]["configuration_id"] == row["arms"]["EE_B0_BEST"]["configuration_id"]
            ),
            "paired_full_over_c1_only_where_differs": {
                "n": len(paired),
                "positive": sum(1 for v in paired if v > 0),
                "negative": sum(1 for v in paired if v < 0),
                "zero": sum(1 for v in paired if v == 0),
                "min": min(paired) if paired else None,
                "max": max(paired) if paired else None,
            },
        },
        "catalogue": {
            "total": sum(row["catalogue_size"] for row in records),
            "uncovered": sum(row["catalogue_uncovered"] for row in records),
        },
        "kinds": {
            arm: {
                kind: sum(1 for row in records if row["arms"][arm].get("kind") == kind)
                for kind in sorted({row["arms"][arm].get("kind") for row in records})
            }
            for arm in ARMS
        },
        "per_anchor": per_anchor,
    }
    out = OUTDIR / f"{stem}-merged.json"
    out.write_text(json.dumps(result, indent=1, sort_keys=True))
    printable = {k: v for k, v in result.items() if k != "per_anchor"}
    print(json.dumps(printable, indent=1, sort_keys=True))
    if stub["selection"] or stub["endpoint"]:
        raise RuntimeError(f"scalar evaluate was called: {stub}")
    print(f"PEAK_RSS_KB={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
