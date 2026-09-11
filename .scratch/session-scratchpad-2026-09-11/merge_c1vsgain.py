#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Merge the C1VSGAIN worker outputs.  Pure arithmetic; no physics.

Derived from /home/sat/mcrl-v025-c2target-ws/.scratch/c2target/merge.py
(cluster bootstrap unit and reps unchanged).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random
import resource
import sys

OUTDIR = Path("/home/sat/mcrl-v025-c1vsgain-ws/.scratch/c1vsgain")
ARMS = (
    "BASE", "C1_ONLY", "C1_PSI", "S0_TOP1_UNCONDITIONAL", "S0_TOP2_BEST",
    "RSS_MAX", "GAIN_IN_SET", "GAIN_IN_SET_LADDER", "CATALOGUE_ORACLE",
)
CONTRASTS = (
    ("C1_ONLY", "GAIN_IN_SET_LADDER"),
    ("C1_ONLY", "GAIN_IN_SET"),
    ("C1_ONLY", "RSS_MAX"),
    ("C1_ONLY", "S0_TOP1_UNCONDITIONAL"),
    ("C1_ONLY", "S0_TOP2_BEST"),
    ("C1_PSI", "C1_ONLY"),
    ("C1_ONLY", "BASE"),
    ("RSS_MAX", "BASE"),
    ("S0_TOP1_UNCONDITIONAL", "BASE"),
    ("C1_ONLY", "CATALOGUE_ORACLE"),
    ("RSS_MAX", "CATALOGUE_ORACLE"),
    ("C1_PSI", "RSS_MAX"),
    ("C1_PSI", "GAIN_IN_SET_LADDER"),
    ("GAIN_IN_SET_LADDER", "GAIN_IN_SET"),
    ("GAIN_IN_SET", "RSS_MAX"),
    ("GAIN_IN_SET_LADDER", "CATALOGUE_ORACLE"),
    ("GAIN_IN_SET_LADDER", "BASE"),
)


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
    return pooled(records, a)["pooled_ee_mbit_per_j"] / pooled(records, b)["pooled_ee_mbit_per_j"] - 1.0


def absolute(records, a, b):
    return pooled(records, a)["pooled_ee_mbit_per_j"] - pooled(records, b)["pooled_ee_mbit_per_j"]


def cluster_bootstrap(records, a, b, reps=2000, seed=20260911):
    clusters = {}
    for row in records:
        clusters.setdefault((row["world_index"], row["step_index"]), []).append(row)
    keys = sorted(clusters)
    rng = random.Random(seed)
    rel_values = []
    abs_values = []
    for _ in range(reps):
        sample = [row for _k in keys for row in clusters[keys[rng.randrange(len(keys))]]]
        rel_values.append(rel(sample, a, b))
        abs_values.append(absolute(sample, a, b))
    rel_values.sort()
    abs_values.sort()
    return {
        "clusters": len(keys),
        "cluster_unit": "(world, step): the three carrier anchors of one decision instant",
        "reps": reps,
        "relative_p2_5": rel_values[int(0.025 * reps)],
        "relative_p97_5": rel_values[int(0.975 * reps) - 1],
        "absolute_mbit_per_j_p2_5": abs_values[int(0.025 * reps)],
        "absolute_mbit_per_j_p97_5": abs_values[int(0.975 * reps) - 1],
    }


def paired(records, a, b):
    values = []
    for row in records:
        left, right = row["arms"][a], row["arms"][b]
        if left["invalid"] or right["invalid"]:
            continue
        values.append({
            "anchor": row["global_anchor_index"],
            "world": row["world_index"],
            "step": row["step_index"],
            "carrier": row["carrier"],
            "a_ee_mbit": left["ee_bits_per_j"] / 1e6,
            "b_ee_mbit": right["ee_bits_per_j"] / 1e6,
            "absolute_mbit": (left["ee_bits_per_j"] - right["ee_bits_per_j"]) / 1e6,
            "relative": left["ee_bits_per_j"] / right["ee_bits_per_j"] - 1.0,
            "same_configuration": left["configuration_id"] == right["configuration_id"],
        })
    changed = [row for row in values if not row["same_configuration"]]
    ratios = sorted(row["relative"] for row in changed)
    geo = (
        None if not changed
        else math.exp(math.fsum(math.log1p(row["relative"]) for row in changed) / len(changed)) - 1.0
    )
    return {
        "anchors": len(values),
        "same_configuration": sum(1 for row in values if row["same_configuration"]),
        "different_configuration": len(changed),
        "a_better": sum(1 for row in changed if row["relative"] > 0),
        "b_better": sum(1 for row in changed if row["relative"] < 0),
        "tied": sum(1 for row in changed if row["relative"] == 0),
        "median_relative_where_different": None if not ratios else ratios[len(ratios) // 2],
        "geomean_relative_where_different": geo,
        "min_relative": None if not ratios else ratios[0],
        "max_relative": None if not ratios else ratios[-1],
        "rows": values,
    }


def main() -> int:
    stem = sys.argv[1]
    workers = int(sys.argv[2])
    expected = int(sys.argv[3])
    records = []
    stub = {"selection": 0, "endpoint": 0, "gain_in_set": 0}
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
            "c1_only_kind": row["c1_only_kind"],
            "c1_only_is_s0_proposal": row["c1_only_is_s0_proposal"],
            "c1_only_equals_rss": row["c1_only_equals_rss"],
            "rss_in_catalogue": row["rss_in_catalogue"],
            "rss_equals_base": row["rss_equals_base"],
            "rss_equals_s0_top1": row["rss_equals_s0_top1"],
            "rss_changed_users_vs_base": row["rss_changed_users_vs_base"],
            "psi_max_abs_on_unilaterals": row["psi_max_abs_on_unilaterals"],
            "c1_psi_differs_from_c1_only": row["c1_psi_differs_from_c1_only"],
            "s0_top2_best_is_rank": row["s0_top2_best_is_rank"],
            **{f"{arm}_ee": (arms[arm].get("ee_bits_per_j") or 0.0) / 1e6 for arm in ARMS},
            **{f"{arm}_served": arms[arm].get("served_fraction") for arm in ARMS},
            **{f"{arm}_attained": arms[arm].get("rate_target_attainment_fraction") for arm in ARMS},
            **{f"{arm}_kind": arms[arm].get("kind") for arm in ARMS},
            **{f"{arm}_changed": arms[arm].get("changed_users") for arm in ARMS},
            **{f"{arm}_rank": arms[arm].get("rank_of_realised_full48_ee") for arm in ARMS},
            **{f"{arm}_cid_eq_c1": arms[arm].get("configuration_id") == arms["C1_ONLY"].get("configuration_id") for arm in ARMS},
        })

    non_s0 = [row for row in records if not row["c1_only_is_s0_proposal"]]
    worlds = sorted({row["world_index"] for row in records})
    result = {
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "anchors": len(records),
        "evaluate_stub_calls_total": stub,
        "worker_peak_rss_kb": peaks,
        "ladder_caps": sorted({tuple(row["ladder_caps"]) for row in records})[0] if records else None,
        "beam_floor_values": sorted({row["beam_floor"] for row in records}),
        "gain_in_set_wall_s_total": math.fsum(row["gain_in_set_wall_s"] for row in records),
        "gain_in_set_ladder_beats_catalogue_oracle_anchors": sum(
            1 for row in records
            if row["arms"]["GAIN_IN_SET_LADDER"]["ee_bits_per_j"] > row["arms"]["CATALOGUE_ORACLE"]["ee_bits_per_j"]
        ),
        "psi_identity_max_abs_on_unilaterals": max(row["psi_max_abs_on_unilaterals"] for row in records),
        "pooled": {arm: pooled(records, arm) for arm in ARMS},
        "pooled_by_world": {
            str(world): {arm: pooled([r for r in records if r["world_index"] == world], arm) for arm in ARMS}
            for world in worlds
        },
        "contrasts": {
            f"{a}_vs_{b}": {
                "relative": rel(records, a, b),
                "absolute_mbit_per_j": absolute(records, a, b),
                "bootstrap": cluster_bootstrap(records, a, b),
                "paired": {k: v for k, v in paired(records, a, b).items() if k != "rows"},
            }
            for a, b in CONTRASTS
        },
        "paired_rows": {
            f"{a}_vs_{b}": paired(records, a, b)["rows"]
            for a, b in (("C1_ONLY", "RSS_MAX"), ("C1_ONLY", "S0_TOP1_UNCONDITIONAL"), ("C1_PSI", "C1_ONLY"))
        },
        "selection_structure": {
            "c1_only_kinds": {
                kind: sum(1 for row in records if row["c1_only_kind"] == kind)
                for kind in sorted({row["c1_only_kind"] for row in records})
            },
            "c1_only_is_s0_proposal": sum(1 for row in records if row["c1_only_is_s0_proposal"]),
            "c1_only_equals_rss": sum(1 for row in records if row["c1_only_equals_rss"]),
            "c1_only_equals_s0_top1": sum(
                1 for row in records
                if row["arms"]["C1_ONLY"]["configuration_id"] == row["arms"]["S0_TOP1_UNCONDITIONAL"]["configuration_id"]
            ),
            "c1_only_equals_s0_top2_best": sum(
                1 for row in records
                if row["arms"]["C1_ONLY"]["configuration_id"] == row["arms"]["S0_TOP2_BEST"]["configuration_id"]
            ),
            "c1_only_equals_catalogue_oracle": sum(
                1 for row in records
                if row["arms"]["C1_ONLY"]["configuration_id"] == row["arms"]["CATALOGUE_ORACLE"]["configuration_id"]
            ),
            "rss_in_catalogue": sum(1 for row in records if row["rss_in_catalogue"]),
            "rss_equals_base": sum(1 for row in records if row["rss_equals_base"]),
            "rss_equals_s0_top1": sum(1 for row in records if row["rss_equals_s0_top1"]),
            "s0_top2_best_is_rank1": sum(1 for row in records if row["s0_top2_best_is_rank"] == 1),
            "c1_psi_differs_from_c1_only": sum(1 for row in records if row["c1_psi_differs_from_c1_only"]),
            "s0_proposal_counts": {
                str(n): sum(1 for row in records if row["s0_proposal_count"] == n)
                for n in sorted({row["s0_proposal_count"] for row in records})
            },
        },
        "c1_only_non_s0_anchors": [
            {
                "world": row["world_index"],
                "anchor": row["global_anchor_index"],
                "step": row["step_index"],
                "carrier": row["carrier"],
                "kind": row["c1_only_kind"],
                "changed_users": row["arms"]["C1_ONLY"]["changed_users"],
                "c1_only_ee_mbit": row["arms"]["C1_ONLY"]["ee_bits_per_j"] / 1e6,
                "rss_ee_mbit": row["arms"]["RSS_MAX"]["ee_bits_per_j"] / 1e6,
                "s0_top1_ee_mbit": row["arms"]["S0_TOP1_UNCONDITIONAL"]["ee_bits_per_j"] / 1e6,
                "s0_top2_best_ee_mbit": row["arms"]["S0_TOP2_BEST"]["ee_bits_per_j"] / 1e6,
                "catalogue_oracle_ee_mbit": row["arms"]["CATALOGUE_ORACLE"]["ee_bits_per_j"] / 1e6,
                "gain_in_set_ee_mbit": row["arms"]["GAIN_IN_SET"]["ee_bits_per_j"] / 1e6,
                "gain_in_set_ladder_ee_mbit": row["arms"]["GAIN_IN_SET_LADDER"]["ee_bits_per_j"] / 1e6,
                "c1_only_served": row["arms"]["C1_ONLY"]["served_fraction"],
                "rss_served": row["arms"]["RSS_MAX"]["served_fraction"],
                "exact_c1_score_of_pick": row["arm_scores"]["C1_ONLY"]["exact_c1_score"],
                "exact_c1_score_of_s0_top1": row["arm_scores"]["S0_TOP1_UNCONDITIONAL"]["exact_c1_score"],
                "exact_c1_score_of_rss": row["arm_scores"]["RSS_MAX"]["exact_c1_score"],
            }
            for row in non_s0
        ],
        "pooled_on_non_s0_anchors": {
            arm: pooled(non_s0, arm) for arm in ARMS
        } if non_s0 else {},
        "per_anchor": per_anchor,
    }
    out = OUTDIR / f"{stem}-merged.json"
    out.write_text(json.dumps(result, indent=1, sort_keys=True))
    printable = {k: v for k, v in result.items() if k not in {"per_anchor", "paired_rows"}}
    print(json.dumps(printable, indent=1, sort_keys=True))
    if any(stub.values()):
        raise RuntimeError(f"scalar evaluate was called: {stub}")
    print(f"PEAK_RSS_KB={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
