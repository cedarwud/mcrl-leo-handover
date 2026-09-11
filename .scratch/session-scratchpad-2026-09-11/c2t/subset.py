#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Arithmetic on the oracle-EE worker outputs: 22-anchor subset, who FULL follows,
score-scale accounting, per-anchor log-ratio summary, tie-break reading."""

from __future__ import annotations

import json
import math
from pathlib import Path
import resource
import statistics

D = Path("/home/sat/mcrl-v025-c2target-ws/.scratch/c2target")
recs = []
for w in range(3):
    recs += json.loads((D / f"oracle-ee-93-w{w}.json").read_text())["records"]
recs.sort(key=lambda r: (r["world_index"], r["global_anchor_index"]))
ARMS = ("BASE", "C1_ONLY", "FULL", "C2_ONLY", "EE_B0_BEST")


def pooled(rows, arm):
    b = math.fsum(r["arms"][arm]["bits"] for r in rows)
    j = math.fsum(r["arms"][arm]["joules"] for r in rows)
    u = sum(r["arms"][arm]["users"] for r in rows)
    return {
        "ee": b / j / 1e6,
        "served": sum(r["arms"][arm]["served_users"] for r in rows) / u,
        "attained": sum(r["arms"][arm]["attained_users"] for r in rows) / u,
    }


out = {}
sub22 = [r for r in recs if r["world_index"] == 1 and r["global_anchor_index"] <= 21]
assert len(sub22) == 22
for name, rows in (("all93", recs), ("sub22_digest_3dd10c17", sub22)):
    p = {arm: pooled(rows, arm) for arm in ARMS}
    out[name] = {
        "pooled": p,
        "FULL_minus_C1_ONLY_mbit_per_j": p["FULL"]["ee"] - p["C1_ONLY"]["ee"],
        "FULL_rel_C1_ONLY": p["FULL"]["ee"] / p["C1_ONLY"]["ee"] - 1,
        "anchors_full_differs": sum(r["full_differs_from_c1_only"] for r in rows),
    }

differs = [r for r in recs if r["full_differs_from_c1_only"]]
follows_c2 = sum(r["arms"]["FULL"]["configuration_id"] == r["arms"]["C2_ONLY"]["configuration_id"] for r in differs)
c1_loss, c2_gain = [], []
for r in differs:
    s1 = r["arm_scores"]["C1_ONLY"]
    s2 = r["arm_scores"]["C2_ONLY"]
    c1_loss.append(s1["c1_only_pick_score"] - s1["full_pick_score"])
    c2_gain.append(s2["full_pick_score"] - s2["c1_only_pick_score"])
logr = [math.log(r["arms"]["FULL"]["ee_bits_per_j"] / r["arms"]["C1_ONLY"]["ee_bits_per_j"]) for r in recs]
logr_d = [math.log(r["arms"]["FULL"]["ee_bits_per_j"] / r["arms"]["C1_ONLY"]["ee_bits_per_j"]) for r in differs]
# realised boundary-0 direction: among differing anchors, which pick is better at b0?
b0_full_better = sum(
    r["arms"]["FULL"]["boundary_0"]["ee_bits_per_j"] > r["arms"]["C1_ONLY"]["boundary_0"]["ee_bits_per_j"]
    for r in differs
)
end_full_better = sum(r["arms"]["FULL"]["ee_bits_per_j"] > r["arms"]["C1_ONLY"]["ee_bits_per_j"] for r in differs)
# low- vs high-EE regime split of the differing anchors, by C1_ONLY endpoint EE
low = [r for r in differs if r["arms"]["C1_ONLY"]["ee_bits_per_j"] / 1e6 < 40]
high = [r for r in differs if r["arms"]["C1_ONLY"]["ee_bits_per_j"] / 1e6 >= 40]
out["differs"] = {
    "n": len(differs),
    "full_equals_c2_only": follows_c2,
    "median_c1_score_given_up_kappa_units": statistics.median(c1_loss),
    "median_c2_score_gained_kappa_units": statistics.median(c2_gain),
    "b0_realised_full_better": b0_full_better,
    "endpoint_full_better": end_full_better,
    "low_ee_regime_n": len(low),
    "low_ee_full_better": sum(r["arms"]["FULL"]["ee_bits_per_j"] > r["arms"]["C1_ONLY"]["ee_bits_per_j"] for r in low),
    "high_ee_regime_n": len(high),
    "high_ee_full_better": sum(r["arms"]["FULL"]["ee_bits_per_j"] > r["arms"]["C1_ONLY"]["ee_bits_per_j"] for r in high),
    "kinds_c1_to_full": sorted({(r["arms"]["C1_ONLY"]["kind"], r["arms"]["FULL"]["kind"]) for r in differs}),
}
out["per_anchor_log_ratio_full_over_c1"] = {
    "mean_all93": statistics.fmean(logr),
    "mean_where_differs": statistics.fmean(logr_d),
    "geometric_mean_ratio_all93_minus_1": math.exp(statistics.fmean(logr)) - 1,
}
ties = []
for w in range(3):
    p = D / f"ties-93-w{w}.json"
    if p.exists():
        ties += json.loads(p.read_text())["records"]
if ties:
    c1_pick = {(r["world_index"], r["global_anchor_index"]): r["arms"]["C1_ONLY"]["configuration_id"] for r in recs}
    out["tie_break_reading"] = {
        "anchors": len(ties),
        "tie_set_size_counts": {str(k): sum(1 for t in ties if t["c1_tie_set_size"] == k) for k in sorted({t["c1_tie_set_size"] for t in ties})},
        "tie_break_changes_pick": sum(t["tie_break_changes_pick"] for t in ties),
        "c1_only_pick_matches_oracle_ee_run": sum(
            t["c1_only_pick"] == c1_pick[(t["world_index"], t["global_anchor_index"])] for t in ties
        ),
        "min_relative_gap_top_vs_runner_up": min(
            (t["c1_max"] - t["c1_runner_up"]) / abs(t["c1_max"]) for t in ties if t["c1_runner_up"] is not None
        ),
    }
(D / "subset-analysis.json").write_text(json.dumps(out, indent=1, sort_keys=True, default=list))
print(json.dumps(out, indent=1, sort_keys=True, default=list))
print(f"PEAK_RSS_KB={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}")
