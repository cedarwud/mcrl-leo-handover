#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Characterise the C2 value -3.0 at which exact and surrogate coincide. No EE."""
from fractions import Fraction
from collections import Counter
import json, os, random, resource
from pathlib import Path
assert os.getpriority(os.PRIO_PROCESS, 0) >= 15
resource.setrlimit(resource.RLIMIT_AS, (4_900_000_000, 4_900_000_000))
CORPUS = Path("/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910")
OUT = Path("/home/sat/mcrl-v025-exact93-ws/.scratch/exact93/c2-floor-check.json")
F = lambda p: Fraction(int(p["fraction"][0]), int(p["fraction"][1]))
FLOOR = float.hex(-3.0)
files = {}
for path in sorted((CORPUS / "views").rglob("*.jsonl")):
    with path.open() as h:
        hd = json.loads(next(h))
    if hd.get("schema") == "mcrl-v025-exact-source-view-shard-v1":
        files[int(hd["global_anchor_index"])] = path
frame = []
for i in sorted(files):
    for line in files[i].open().read().splitlines()[1:]:
        r = json.loads(line)
        if r["reference_action"]:
            continue
        c2 = r["exact_source_view"]["c2_persistence_forecast"]
        kappa = Fraction.from_float(float.fromhex(r["kappa_normalization_bits_hex"]))
        surplus, penalty = F(c2["forecast_surplus_bits"]), F(c2["persistence_penalty_bits"])
        frame.append({
            "exact": r["c2_label_normalized_hex"],
            "sur": r["exact_source_view"]["surrogate"]["c2_normalized_total_hex"],
            "surplus_zero": surplus == 0, "lost": int(c2["lost_offsets"]),
            "penalty_over_kappa": float(penalty / kappa),
            "surplus_over_kappa": float(surplus / kappa),
            "null": bool(r["null_action"]), "outage": bool(r["outage"]),
        })
assert len(frame) == 81638
floor_state = [r for r in frame if r["surplus_zero"] and r["lost"] == 3]
exact_at_floor = [r for r in frame if r["exact"] == FLOOR]
sur_at_floor = [r for r in frame if r["sur"] == FLOOR]
match = [r for r in frame if r["exact"] == r["sur"]]
not_floor = [r for r in frame if r["exact"] != FLOOR]
res = {
    "frame_rows": len(frame),
    "lost_offsets_distribution_all": dict(Counter(r["lost"] for r in frame)),
    "penalty_over_kappa_by_lost": {str(k): sorted({round(r["penalty_over_kappa"], 12) for r in frame if r["lost"] == k})[:5] for k in sorted({r["lost"] for r in frame})},
    "floor_state_rows(surplus==0 & lost==3)": len(floor_state),
    "floor_state_exact_is_minus3": sum(r["exact"] == FLOOR for r in floor_state),
    "floor_state_surrogate_is_minus3": sum(r["sur"] == FLOOR for r in floor_state),
    "exact_minus3_rows": len(exact_at_floor),
    "exact_minus3_not_floor_state": [
        {"surplus_over_kappa": r["surplus_over_kappa"], "lost": r["lost"]}
        for r in exact_at_floor if not (r["surplus_zero"] and r["lost"] == 3)],
    "surrogate_minus3_rows": len(sur_at_floor),
    "surrogate_minus3_but_exact_not": sum(r["exact"] != FLOOR for r in sur_at_floor),
    "exact_minus3_but_surrogate_not": sum(r["sur"] != FLOOR for r in exact_at_floor),
    "all_matches": len(match),
    "matches_at_minus3": sum(r["exact"] == FLOOR for r in match),
    "matches_off_minus3": sum(r["exact"] != FLOOR for r in match),
    "rows_off_minus3": len(not_floor),
    "floor_state_null_action": dict(Counter(r["null"] for r in floor_state)),
    "floor_state_outage": dict(Counter(r["outage"] for r in floor_state)),
}
# Restricted sample rate: replay EXACTTRAIN's sample, drop rows whose exact label is -3.
sample = random.Random("EXACTTRAIN/20260910/C2").sample(frame, 2000)
res["sample_matches"] = sum(r["exact"] == r["sur"] for r in sample)
kept = [r for r in sample if r["exact"] != FLOOR]
res["sample_restricted_rows"] = len(kept)
res["sample_restricted_matches"] = sum(r["exact"] == r["sur"] for r in kept)
res["sample_exact_minus3"] = sum(r["exact"] == FLOOR for r in sample)
res["sample_exact_minus3_surrogate_not"] = sum(r["exact"] == FLOOR and r["sur"] != FLOOR for r in sample)
res["peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
OUT.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n")
print(json.dumps(res, indent=1, sort_keys=True))
