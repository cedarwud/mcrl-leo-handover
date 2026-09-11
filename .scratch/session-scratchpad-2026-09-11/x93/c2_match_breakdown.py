#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Break down the C2 exact-label rows that are bit-equal to the sealed surrogate.

Replays EXACTTRAIN's C2 sample exactly (same frame order, same RNG domain)
over the assembled 93-anchor corpus. No EE quantity is computed.
"""
from __future__ import annotations
from collections import Counter
from fractions import Fraction
import json, os, random, resource, sys
from pathlib import Path

CORPUS = Path("/home/sat/mcrl-v025-exact93-ws/artifacts/exact-label-corpus-93-20260910")
OUT = Path("/home/sat/mcrl-v025-exact93-ws/.scratch/exact93/c2-surrogate-match-breakdown.json")
SOURCE_SCHEMA = "mcrl-v025-exact-source-view-shard-v1"
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
assert os.getpriority(os.PRIO_PROCESS, 0) >= 15
assert all(os.environ.get(n) == "1" for n in THREADS)
resource.setrlimit(resource.RLIMIT_AS, (4_900_000_000, 4_900_000_000))


def frac(p):
    n, d = p["fraction"]
    v = Fraction(int(n), int(d))
    assert p["float_hex"] == float.hex(float(v))
    return v


def akey(a):
    return (a["norad_id"], a["beam_chain_id"])


# Same inventory order as EXACTTRAIN: sorted by global anchor index.
files = {}
for path in sorted((CORPUS / "views").rglob("*.jsonl")):
    with path.open() as h:
        header = json.loads(next(h))
    if header.get("schema") == SOURCE_SCHEMA:
        files[int(header["global_anchor_index"])] = path

frame = []
for index in sorted(files):
    rows = [json.loads(l) for l in files[index].open().read().splitlines()[1:]]
    ref = {r["user_id"]: r for r in rows if r["reference_action"]}
    for r in rows:
        if r["reference_action"]:
            continue
        e = r["exact_source_view"]
        c2 = e["c2_persistence_forecast"]
        s = e["surrogate"]
        base = ref[r["user_id"]]
        label_bits = frac(c2["label_bits"])
        surplus = frac(c2["forecast_surplus_bits"])
        penalty = frac(c2["persistence_penalty_bits"])
        identity = (frac(c2["decomposition_residual"]) == 0 and label_bits == surplus - penalty)
        train_vs_exact = abs(float.fromhex(r["c2_label_normalized_hex"]) - float(frac(c2["normalized_total"])))
        frame.append({
            "anchor": index, "user": r["user_id"], "action_index": r["action_index"],
            "null_action": bool(r["null_action"]), "outage": bool(r["outage"]),
            "same_physical_action_as_base": akey(r["action"]) == akey(base["action"]),
            "exact_hex": r["c2_label_normalized_hex"],
            "surrogate_hex": s["c2_normalized_total_hex"],
            "exact_bits_hex": r["c2_label_bits_hex"],
            "surrogate_bits_hex": s["c2_label_bits_hex"],
            "exact_zero": label_bits == 0,
            "surplus_zero": surplus == 0, "penalty_zero": penalty == 0,
            "lost_offsets": int(c2["lost_offsets"]),
            "base_exact_c2_zero": float.fromhex(base["c2_label_bits_hex"]) == 0.0,
            "identity": identity, "train_vs_exact_residual": train_vs_exact,
        })
assert len(frame) == 81638, len(frame)
sample = random.Random("EXACTTRAIN/20260910/C2").sample(frame, 2000)
matches = [r for r in sample if r["exact_hex"] == r["surrogate_hex"]]
assert len(matches) == 453, len(matches)
full_matches = [r for r in frame if r["exact_hex"] == r["surrogate_hex"]]


def breakdown(rows):
    keys = ("null_action", "outage", "same_physical_action_as_base", "exact_zero",
            "surplus_zero", "penalty_zero", "base_exact_c2_zero", "identity")
    out = {k: Counter(str(r[k]) for r in rows) for k in keys}
    out["lost_offsets"] = Counter(str(r["lost_offsets"]) for r in rows)
    out["exact_value_hex"] = Counter(r["exact_hex"] for r in rows).most_common(5)
    out["bits_equal_too"] = Counter(str(r["exact_bits_hex"] == r["surrogate_bits_hex"]) for r in rows)
    out["joint_null_exactzero"] = Counter(f"null={r['null_action']}|zero={r['exact_zero']}" for r in rows)
    out["max_train_vs_exact_residual"] = max((r["train_vs_exact_residual"] for r in rows), default=0.0)
    return {k: dict(v) if isinstance(v, Counter) else v for k, v in out.items()}


by_construction = lambda r: r["exact_zero"] and (r["null_action"] or r["same_physical_action_as_base"])
restricted_sample = [r for r in sample if not by_construction(r)]
restricted_matches = [r for r in restricted_sample if r["exact_hex"] == r["surrogate_hex"]]
nonzero_frame = [r for r in frame if not r["exact_zero"]]
nonzero_matches = [r for r in nonzero_frame if r["exact_hex"] == r["surrogate_hex"]]
result = {
    "schema": "mcrl-v025-exact93-c2-surrogate-match-breakdown-v1",
    "not_a_claim": True,
    "frame_rows": len(frame), "sample_size": len(sample), "sample_matches": len(matches),
    "sample_breakdown_matching": breakdown(matches),
    "sample_breakdown_all": breakdown(sample),
    "full_frame_matches": len(full_matches),
    "full_frame_breakdown_matching": breakdown(full_matches),
    "full_frame_breakdown_all": breakdown(frame),
    "by_construction_definition": "exact C2 label_bits == 0 AND (null action OR candidate physically identical to BASE)",
    "sample_restricted": {"rows": len(restricted_sample), "matches": len(restricted_matches)},
    "full_frame_nonzero_exact": {"rows": len(nonzero_frame), "matches": len(nonzero_matches)},
    "matching_rows_failing_exact_identity": sum(not r["identity"] for r in full_matches),
    "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
}
OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({k: result[k] for k in ("sample_matches", "full_frame_matches", "sample_restricted",
      "full_frame_nonzero_exact", "matching_rows_failing_exact_identity", "peak_rss_bytes")}))
print("SAMPLE_MATCHING", json.dumps(result["sample_breakdown_matching"]))
print("FULL_MATCHING", json.dumps(result["full_frame_breakdown_matching"]))
print("FULL_ALL", json.dumps({k: result["full_frame_breakdown_all"][k] for k in ("null_action", "exact_zero", "same_physical_action_as_base", "joint_null_exactzero")}))
