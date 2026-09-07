#!/usr/bin/env python3
"""Read-only probe: does float32 writer arithmetic explain 'C2 q2 delta differs'?

For every world and every c2_diagnostic row: compare the serialised q2_delta with
(a) the frozen verifier's float64 recomputation and (b) a float32 writer-style
recomputation, under the frozen tolerance max(1e-12, 1024*eps*max(1,|x|)).
"""
import json, sys
from pathlib import Path
import numpy as np
root = Path(sys.argv[1])
worlds = range(2026121801, 2026121809)
floor = float(sys.argv[2]) if len(sys.argv) > 2 else 1e-12
def tol(a, b):
    return np.maximum(floor, 1024.0 * np.finfo(np.float64).eps * np.maximum(1.0, np.maximum(np.abs(a), np.abs(b))))
grand = {"rows": 0, "f64_fail": 0, "f32_fail": 0, "f64_maxdiff": 0.0, "f32_maxdiff": 0.0, "target_f64_fail": 0}
for w in worlds:
    src = json.loads((root / f"source/world-{w}.json").read_text())
    with np.load(root / f"source/world-{w}.arrays.npz") as z:
        q2 = np.asarray(z["q2_values"], dtype=np.float64)          # (A,U,28) widened float32
        q2t = np.asarray(z["q2_teacher_values"], dtype=np.float64)
        ref = np.asarray(z["reference_actions"], dtype=np.int64)
    exact_f32 = np.array_equal(q2, q2.astype(np.float32).astype(np.float64))
    stats = {"rows": 0, "f64_fail": 0, "f32_fail": 0, "f64_maxdiff": 0.0, "f32_maxdiff": 0.0, "target_f64_fail": 0, "q2_is_exact_float32": bool(exact_f32)}
    for a, anchor in enumerate(src["anchors"]):
        diag = anchor.get("c2_diagnostic")
        elements = diag if isinstance(diag, list) else [diag]
        for el in elements:
            for row in el.get("rows", []):
                users = row["user_ids"]; acts = row["candidate_actions"]; refs = row["reference_actions"]
                ser = np.asarray(row["q2_delta"], dtype=np.float64)
                sert = np.asarray(row["ops3_target_delta"], dtype=np.float64)
                f64 = np.asarray([q2[a, u, c] - q2[a, u, r] for u, c, r in zip(users, acts, refs)], dtype=np.float64)
                f32 = np.asarray([float(np.float32(q2[a, u, c]) - np.float32(q2[a, u, r])) for u, c, r in zip(users, acts, refs)], dtype=np.float64)
                t64 = np.asarray([q2t[a, u, c] - q2t[a, u, r] for u, c, r in zip(users, acts, refs)], dtype=np.float64)
                stats["rows"] += 1
                d64 = np.abs(ser - f64); d32 = np.abs(ser - f32); dt = np.abs(sert - t64)
                stats["f64_maxdiff"] = max(stats["f64_maxdiff"], float(d64.max())); stats["f32_maxdiff"] = max(stats["f32_maxdiff"], float(d32.max()))
                stats["f64_fail"] += int(np.any(d64 > tol(ser, f64))); stats["f32_fail"] += int(np.any(d32 > tol(ser, f32))); stats["target_f64_fail"] += int(np.any(dt > tol(sert, t64)))
    print(json.dumps({"world": w, **stats}))
    for k in ("rows", "f64_fail", "f32_fail", "target_f64_fail"): grand[k] += stats[k]
    grand["f64_maxdiff"] = max(grand["f64_maxdiff"], stats["f64_maxdiff"]); grand["f32_maxdiff"] = max(grand["f32_maxdiff"], stats["f32_maxdiff"])
print("PROBE_Q2_DELTA_PRECISION_DONE", json.dumps(grand))
