#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Pair the main C1VSGAIN arms with the nine declared BEAMCOUNT rules and
bootstrap the C1 contrasts against the declared-rule reference class.
Pure arithmetic; no physics."""

from __future__ import annotations

import json
import math
from pathlib import Path
import random

D = Path("/home/sat/mcrl-v025-c1vsgain-ws/.scratch/c1vsgain")
RULES = [
    f"{s}|{a}"
    for s in ("S1_ascending_coverage", "S2_descending_coverage", "S3_descending_nominal_gain")
    for a in ("A1_coverage_first", "A2_max_nominal_gain", "A3_least_loaded")
] + ["RSS_MAX"]

main = json.loads((D / "c1vsgain-93-merged.json").read_text())
declared = []
for w in range(3):
    declared += json.loads((D / f"declared-93-w{w}.json").read_text())["records"]
by_anchor = {int(r["global_anchor_index"]): r for r in declared}

rows = []
for row in main["per_anchor"]:
    d = by_anchor[int(row["anchor"])]
    entry = {"world": row["world"], "step": row["step"], "anchor": row["anchor"]}
    for arm in ("BASE", "C1_ONLY", "C1_PSI", "RSS_MAX", "S0_TOP1_UNCONDITIONAL",
                "GAIN_IN_SET", "GAIN_IN_SET_LADDER", "CATALOGUE_ORACLE"):
        entry[arm] = None
    rows.append(entry)

# rebuild bits/joules per arm from the worker records (per_anchor only holds EE)
records = []
for w in range(3):
    records += json.loads((D / f"c1vsgain-93-w{w}.json").read_text())["records"]
main_by_anchor = {int(r["global_anchor_index"]): r for r in records}

ARMS = ("BASE", "C1_ONLY", "C1_PSI", "S0_TOP1_UNCONDITIONAL", "S0_TOP2_BEST",
        "RSS_MAX", "GAIN_IN_SET", "GAIN_IN_SET_LADDER", "CATALOGUE_ORACLE")

table = []
for anchor, row in sorted(main_by_anchor.items()):
    d = by_anchor[anchor]
    entry = {"anchor": anchor, "world": row["world_index"], "step": row["step_index"], "arms": {}}
    for arm in ARMS:
        a = row["arms"][arm]
        entry["arms"][arm] = (a["bits"], a["joules"], a["served_users"], a["attained_users"], a["users"])
    for name in RULES:
        r = d["rules"][name]
        entry["arms"][f"DECLARED::{name}"] = (
            r["bits"], r["joules"], r["served_users"], r["attained_users"], r["users"]
        )
    table.append(entry)


def pooled(sample, arm):
    bits = math.fsum(row["arms"][arm][0] for row in sample)
    joules = math.fsum(row["arms"][arm][1] for row in sample)
    users = math.fsum(row["arms"][arm][4] for row in sample)
    return {
        "ee_mbit": bits / joules / 1e6,
        "served": math.fsum(row["arms"][arm][2] for row in sample) / users,
        "attain": math.fsum(row["arms"][arm][3] for row in sample) / users,
    }


def contrast(a, b, reps=2000, seed=20260911):
    clusters = {}
    for row in table:
        clusters.setdefault((row["world"], row["step"]), []).append(row)
    keys = sorted(clusters)
    rng = random.Random(seed)
    rels, abss = [], []
    for _ in range(reps):
        sample = [r for _k in keys for r in clusters[keys[rng.randrange(len(keys))]]]
        pa, pb = pooled(sample, a), pooled(sample, b)
        rels.append(pa["ee_mbit"] / pb["ee_mbit"] - 1.0)
        abss.append(pa["ee_mbit"] - pb["ee_mbit"])
    rels.sort()
    abss.sort()
    pa, pb = pooled(table, a), pooled(table, b)
    wins = sum(
        1 for row in table
        if row["arms"][a][0] / row["arms"][a][1] > row["arms"][b][0] / row["arms"][b][1]
    )
    return {
        "a": a, "b": b,
        "a_ee": pa["ee_mbit"], "b_ee": pb["ee_mbit"],
        "absolute": pa["ee_mbit"] - pb["ee_mbit"],
        "relative": pa["ee_mbit"] / pb["ee_mbit"] - 1.0,
        "rel_ci": [rels[int(0.025 * reps)], rels[int(0.975 * reps) - 1]],
        "abs_ci": [abss[int(0.025 * reps)], abss[int(0.975 * reps) - 1]],
        "a_better_anchors": wins, "anchors": len(table),
        "a_served": pa["served"], "b_served": pb["served"],
        "a_attain": pa["attain"], "b_attain": pb["attain"],
    }


out = {
    "pooled": {arm: pooled(table, arm) for arm in ARMS},
    "pooled_declared": {f"DECLARED::{n}": pooled(table, f"DECLARED::{n}") for n in RULES},
    "contrasts": [
        contrast("C1_ONLY", "DECLARED::S2_descending_coverage|A2_max_nominal_gain"),
        contrast("C1_ONLY", "DECLARED::S3_descending_nominal_gain|A2_max_nominal_gain"),
        contrast("C1_ONLY", "DECLARED::RSS_MAX"),
        contrast("C1_ONLY", "GAIN_IN_SET"),
        contrast("C1_ONLY", "GAIN_IN_SET_LADDER"),
        contrast("C1_PSI", "DECLARED::S2_descending_coverage|A2_max_nominal_gain"),
        contrast("GAIN_IN_SET_LADDER", "DECLARED::S2_descending_coverage|A2_max_nominal_gain"),
    ],
    "rss_parity": {
        "main_arm": pooled(table, "RSS_MAX")["ee_mbit"],
        "declared_pass": pooled(table, "DECLARED::RSS_MAX")["ee_mbit"],
    },
}
(D / "combined-93.json").write_text(json.dumps(out, indent=1, sort_keys=True))
for row in out["contrasts"]:
    print(
        f"{row['a']} vs {row['b']}: {row['a_ee']:.4f} vs {row['b_ee']:.4f} "
        f"abs={row['absolute']:+.4f} rel={row['relative']*100:+.3f}% "
        f"CI_rel=[{row['rel_ci'][0]*100:+.2f}%,{row['rel_ci'][1]*100:+.2f}%] "
        f"CI_abs=[{row['abs_ci'][0]:+.3f},{row['abs_ci'][1]:+.3f}] "
        f"a_wins={row['a_better_anchors']}/{row['anchors']} "
        f"served {row['a_served']:.4f} vs {row['b_served']:.4f} "
        f"attain {row['a_attain']:.4f} vs {row['b_attain']:.4f}"
    )
print("RSS parity:", out["rss_parity"])
