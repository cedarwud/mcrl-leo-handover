#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""C2TARGET Q3 / Q1 label analysis over the sealed 22-anchor exact-label corpus.

Read-only.  No physics, no learner, no EE.  Verifies every shard against its
shipped .sha256 sidecar first, then computes:

  * exact-vs-surrogate argmax disagreement (reproduces the published
    C1 51.6818% / C2 55.2727% figures as an instrument check),
  * exact C1 vs exact C2 correlation and argmax agreement,
  * how often adding exact C2 to exact C1 changes the per-user argmax,
  * tie structure of the exact C2 delta.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys

CORPUS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-corpus-20260910")
OUT = Path("/home/sat/mcrl-v025-c2target-ws/.scratch/c2target") / (sys.argv[2] if len(sys.argv) > 2 else "labels.json")
EXPECTED = int(sys.argv[3]) if len(sys.argv) > 3 else 22
PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python").resolve()
THREAD_VARS = (
    "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
)
MAX_AS_BYTES = 4_900_000_000


def enforce() -> None:
    if Path(sys.executable).resolve() != PYTHON:
        raise RuntimeError(f"wrong interpreter: {sys.executable}")
    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
        raise RuntimeError("niceness below 16")
    bad = {n: os.environ.get(n) for n in THREAD_VARS if os.environ.get(n) != "1"}
    if bad:
        raise RuntimeError(f"thread pins drifted: {bad}")
    _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = MAX_AS_BYTES if hard == resource.RLIM_INFINITY else min(MAX_AS_BYTES, hard)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mx = math.fsum(xs) / n
    my = math.fsum(ys) / n
    sxy = math.fsum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = math.fsum((x - mx) ** 2 for x in xs)
    syy = math.fsum((y - my) ** 2 for y in ys)
    if sxx <= 0.0 or syy <= 0.0:
        return None
    return sxy / math.sqrt(sxx * syy)


def rankdata(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    return ranks


def spearman(xs, ys):
    return pearson(rankdata(xs), rankdata(ys))


def argmax_index(pairs):
    """pairs: list of (score, action_index).  Deterministic: max score, then
    lowest action_index."""
    best = None
    for score, action_index in pairs:
        key = (-score, action_index)
        if best is None or key < best[0]:
            best = (key, action_index)
    return best[1]


def main() -> int:
    enforce()
    shards = sorted(CORPUS.glob("views/world-*/BUILD_NOT_CLAIM-exact-source-anchor-*.jsonl"))
    if len(shards) != EXPECTED:
        raise RuntimeError(f"expected {EXPECTED} source shards, found {len(shards)}")

    sidecar_checks = []
    for shard in shards:
        expected = (shard.parent / (shard.name + ".sha256")).read_text().split()[0].strip()
        actual = sha256(shard)
        sidecar_checks.append({"shard": shard.name, "ok": expected == actual, "sha256": actual})
    if not all(row["ok"] for row in sidecar_checks):
        raise RuntimeError("shard sidecar mismatch")

    per_anchor = []
    all_c1, all_c2 = [], []
    all_dc1, all_dc2 = [], []
    tot = {
        "rows": 0, "users": 0,
        "c1_argmax_disagree": 0, "c2_argmax_disagree": 0,
        "c1c2_argmax_same": 0,
        "c1_vs_c1c2_same": 0,
        "c2_vs_c1c2_same": 0,
        "dc2_zero_rows": 0, "nonref_rows": 0,
        "c1_argmax_is_base": 0, "c1c2_argmax_is_base": 0, "c2_argmax_is_base": 0,
    }

    for shard in shards:
        with shard.open() as handle:
            header = json.loads(handle.readline())
            rows = [json.loads(line) for line in handle]
        by_user = {}
        for row in rows:
            view = row["exact_source_view"]
            entry = {
                "action_index": int(row["action_index"]),
                "reference": bool(row["reference_action"]),
                "c1": float.fromhex(row["c1_label_normalized_hex"]),
                "c2": float.fromhex(row["c2_label_normalized_hex"]),
                "s1": float.fromhex(view["surrogate"]["c1_normalized_total_hex"]),
                "s2": float.fromhex(view["surrogate"]["c2_normalized_total_hex"]),
            }
            by_user.setdefault(int(row["user_id"]), []).append(entry)

        a = {
            "anchor": header["global_anchor_index"],
            "world_index": header["world_index"],
            "step_index": header["step_index"],
            "carrier": header["carrier"],
            "rows": len(rows), "users": len(by_user),
            "c1_argmax_disagree": 0, "c2_argmax_disagree": 0,
            "c1c2_argmax_same": 0, "c1_vs_c1c2_same": 0, "c2_vs_c1c2_same": 0,
        }
        for user, entries in by_user.items():
            ref = [e for e in entries if e["reference"]]
            if len(ref) != 1:
                raise RuntimeError(f"user {user} has {len(ref)} reference rows")
            base_c1, base_c2 = ref[0]["c1"], ref[0]["c2"]
            ex1 = argmax_index([(e["c1"], e["action_index"]) for e in entries])
            ex2 = argmax_index([(e["c2"], e["action_index"]) for e in entries])
            su1 = argmax_index([(e["s1"], e["action_index"]) for e in entries])
            su2 = argmax_index([(e["s2"], e["action_index"]) for e in entries])
            ex12 = argmax_index([(e["c1"] + e["c2"], e["action_index"]) for e in entries])
            a["c1_argmax_disagree"] += int(ex1 != su1)
            a["c2_argmax_disagree"] += int(ex2 != su2)
            a["c1c2_argmax_same"] += int(ex1 == ex2)
            a["c1_vs_c1c2_same"] += int(ex1 == ex12)
            a["c2_vs_c1c2_same"] += int(ex2 == ex12)
            tot["c1_argmax_is_base"] += int(ex1 == ref[0]["action_index"])
            tot["c2_argmax_is_base"] += int(ex2 == ref[0]["action_index"])
            tot["c1c2_argmax_is_base"] += int(ex12 == ref[0]["action_index"])
            for e in entries:
                all_c1.append(e["c1"])
                all_c2.append(e["c2"])
                if not e["reference"]:
                    d1 = e["c1"] - base_c1
                    d2 = e["c2"] - base_c2
                    all_dc1.append(d1)
                    all_dc2.append(d2)
                    tot["nonref_rows"] += 1
                    tot["dc2_zero_rows"] += int(d2 == 0.0)
        for key in ("c1_argmax_disagree", "c2_argmax_disagree", "c1c2_argmax_same",
                    "c1_vs_c1c2_same", "c2_vs_c1c2_same"):
            tot[key] += a[key]
        tot["rows"] += a["rows"]
        tot["users"] += a["users"]
        per_anchor.append(a)

    result = {
        "status": "DIAGNOSTIC_NOT_CLAIM",
        "corpus": str(CORPUS),
        "shard_sidecar_checks": sidecar_checks,
        "anchors": len(per_anchor),
        "totals": tot,
        "rates": {
            "c1_exact_vs_surrogate_argmax_disagreement": tot["c1_argmax_disagree"] / tot["users"],
            "c2_exact_vs_surrogate_argmax_disagreement": tot["c2_argmax_disagree"] / tot["users"],
            "c1_c2_exact_argmax_agreement": tot["c1c2_argmax_same"] / tot["users"],
            "c1_vs_c1plusc2_argmax_agreement": tot["c1_vs_c1c2_same"] / tot["users"],
            "c2_vs_c1plusc2_argmax_agreement": tot["c2_vs_c1c2_same"] / tot["users"],
            "c1_argmax_is_incumbent": tot["c1_argmax_is_base"] / tot["users"],
            "c2_argmax_is_incumbent": tot["c2_argmax_is_base"] / tot["users"],
            "c1plusc2_argmax_is_incumbent": tot["c1c2_argmax_is_base"] / tot["users"],
            "delta_c2_exactly_zero_over_nonincumbent_rows": tot["dc2_zero_rows"] / tot["nonref_rows"],
        },
        "correlations": {
            "raw_labels_pearson": pearson(all_c1, all_c2),
            "raw_labels_spearman": spearman(all_c1, all_c2),
            "delta_labels_pearson": pearson(all_dc1, all_dc2),
            "delta_labels_spearman": spearman(all_dc1, all_dc2),
            "raw_n": len(all_c1),
            "delta_n": len(all_dc1),
        },
        "per_anchor": per_anchor,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps(result["rates"], indent=1, sort_keys=True))
    print(json.dumps(result["correlations"], indent=1, sort_keys=True))
    print(json.dumps({"anchors": len(per_anchor), "rows": tot["rows"], "users": tot["users"]}))
    print(f"PEAK_RSS_KB={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
