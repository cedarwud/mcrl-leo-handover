#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Cross-user correlation structure of the Q1-v4 added fields (no training).

Instrument: the sibling module used by Q-ROW-COLLINEARITY-2026-09-10, imported
byte-identically (SHA-256 checked), function ``q_row_decorrelation_penalty``:
mean |off-diagonal Pearson| between user rows, degenerate (constant) rows dropped.
Matrix per anchor and field: rows = users with a complete 10-slot table, columns
= that user's own action_index slots (the layout the deployed argmax consumes).
Screening thresholds are declared here, before this script is run:
  STRUCTURALLY_WEAK       constant-row fraction (pooled) >= 0.90
  COLLINEAR_ACROSS_USERS  pooled excess over the within-row permutation null > 0.30
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys

import numpy as np

ROOT = Path("/home/sat/mcrl-v025-q1v4-ws")
TABLE = ROOT / "artifacts/q1v4-feature-table.npz"
RECEIPT = ROOT / "artifacts/q1v4-build-verification.json"
OUT = ROOT / "artifacts/q1v4-added-field-correlation.json"
PENALTIES = Path("/home/sat/mcrl-v025-qcollinear-ws/ref/penalties.py")
PENALTIES_SHA256 = "d1ca8dc89ffc71762369b361498e80b91dffe719916ef52556ac77243b486411"
PERMUTATIONS = 64
WEAK_CONSTANT_FRACTION = 0.90
COLLINEAR_EXCESS = 0.30


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if os.getpriority(os.PRIO_PROCESS, 0) < 16 or any(os.environ.get(v) != "1" for v in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")):
        raise RuntimeError("runtime caps not applied")
    if OUT.exists():
        raise RuntimeError("refusing to overwrite")
    receipt = json.loads(RECEIPT.read_text())
    if sha(TABLE) != receipt["feature_table"]["sha256"]:
        raise RuntimeError("feature table drifted from build receipt")
    if sha(PENALTIES) != PENALTIES_SHA256:
        raise RuntimeError("sibling instrument drifted")
    import importlib.util
    import torch
    torch.set_num_threads(1)
    spec = importlib.util.spec_from_file_location("sibling_penalties", PENALTIES)
    pen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pen)

    def rho(mat: np.ndarray) -> float:
        value = pen.q_row_decorrelation_penalty(torch.as_tensor(mat, dtype=torch.float64))
        return float(value)

    # instrument self-test on the degenerate paths
    rank1 = np.outer(np.arange(1, 6), np.arange(1, 11)).astype(float)
    assert abs(rho(rank1) - 1.0) < 1e-9
    assert math.isnan(rho(np.ones((5, 10))))

    data = np.load(TABLE, allow_pickle=False)
    table, columns = data["table"], [str(c) for c in data["columns"]]
    col = {name: i for i, name in enumerate(columns)}
    added = ["decision_boundary_log_nominal_gain_db",
             "incumbent_isolated_cap_bound_count_before_join",
             "incumbent_isolated_cap_bound_count_added_by_join",
             "incumbent_isolated_max_rf_over_cap_after_join"]
    references = ["background_occupancy_excluding_focal", "off_axis_angle", "focal_link_elevation",
                  "nominal_sinr_margin_at_rate_target", "remaining_visibility_time"]
    subsets = {"gain_only": added[:1], "congestion_only": added[1:], "both": added}
    rng = np.random.default_rng(20260911)

    anchors = np.unique(table[:, col["anchor"]]).astype(int)
    per_field = {name: {"with_null": [], "no_null": [], "null_with": [], "null_no": [],
                        "constant_rows": 0, "rows": 0, "anchors_defined": 0} for name in added + references}
    per_subset = {name: {"with_null": [], "null_with": []} for name in subsets}
    complete_users_total = 0

    for anchor in anchors:
        block = table[table[:, col["anchor"]] == anchor]
        users = []
        for user in np.unique(block[:, col["user"]]).astype(int):
            rows = block[block[:, col["user"]] == user]
            if int(rows[0, col["table_len"]]) != 10 or len(rows) != 10:
                continue
            order = np.argsort(rows[:, col["action_index"]])
            rows = rows[order]
            if not np.array_equal(rows[:, col["action_index"]], np.arange(10)) or rows[9, col["null"]] != 1:
                raise RuntimeError("complete-block user table is not slots 0..9 with null last")
            users.append(rows)
        complete_users_total += len(users)
        if len(users) < 2:
            continue
        cube = np.stack(users)  # U x 10 x columns
        for name in added + references:
            mat = cube[:, :, col[name]]
            constant = np.all(mat == mat[:, :1], axis=1)
            stats = per_field[name]
            stats["constant_rows"] += int(constant.sum())
            stats["rows"] += int(len(mat))
            for key, m, nkey in (("with_null", mat, "null_with"), ("no_null", mat[:, :9], "null_no")):
                value = rho(m)
                if math.isnan(value):
                    continue
                perms = []
                for _ in range(PERMUTATIONS):
                    shuffled = np.apply_along_axis(rng.permutation, 1, m)
                    pv = rho(shuffled)
                    if not math.isnan(pv):
                        perms.append(pv)
                stats[key].append(value)
                stats[nkey].append(float(np.mean(perms)))
            stats["anchors_defined"] += 1
        for sname, fields in subsets.items():
            pieces = []
            for name in fields:
                vals = cube[:, :, col[name]]
                sd = vals.std()
                if sd > 0:
                    pieces.append((vals - vals.mean()) / sd)
            if not pieces:
                continue
            mat = np.concatenate(pieces, axis=1)
            value = rho(mat)
            if math.isnan(value):
                continue
            perms = [rho(np.apply_along_axis(rng.permutation, 1, mat)) for _ in range(PERMUTATIONS)]
            per_subset[sname]["with_null"].append(value)
            per_subset[sname]["null_with"].append(float(np.nanmean(perms)))
        print(f"anchor {int(anchor)+1}/{len(anchors)} complete_users={len(users)} "
              f"peak_rss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}", flush=True)

    def summarize(values, nulls):
        if not values:
            return None
        v = np.asarray(values); n = np.asarray(nulls)
        return {"anchors": len(v), "mean": float(v.mean()), "median": float(np.median(v)), "min": float(v.min()),
                "max": float(v.max()), "anchors_gt_0.7": int((v > 0.7).sum()), "anchors_gt_0.9": int((v > 0.9).sum()),
                "permutation_null_mean": float(n.mean()), "excess_over_null": float(v.mean() - n.mean())}

    fields_out = {}
    for name, stats in per_field.items():
        const_frac = stats["constant_rows"] / stats["rows"]
        with_null = summarize(stats["with_null"], stats["null_with"])
        no_null = summarize(stats["no_null"], stats["null_no"])
        flags = []
        if const_frac >= WEAK_CONSTANT_FRACTION:
            flags.append("STRUCTURALLY_WEAK")
        if with_null and with_null["excess_over_null"] > COLLINEAR_EXCESS:
            flags.append("COLLINEAR_ACROSS_USERS")
        fields_out[name] = {"role": "added" if name in added else "reference(v2)",
                            "constant_row_fraction": const_frac, "rows": stats["rows"],
                            "ten_slot": with_null, "nine_slot_null_dropped": no_null,
                            "screen_flags": flags}

    # row-level redundancy against the stored v2 coordinates (legal rows only)
    legal = table[table[:, col["null"]] == 0]
    v2_names = columns[6:21]
    redundancy = {}
    for name in added:
        y = legal[:, col[name]]
        entry = {"pearson_vs": {}}
        for other in v2_names + [a for a in added if a != name]:
            x = legal[:, col[other]]
            entry["pearson_vs"][other] = None if x.std() == 0 or y.std() == 0 else float(np.corrcoef(x, y)[0, 1])
        predictors = [legal[:, col[c]] for c in v2_names if legal[:, col[c]].std() > 0]
        if name != added[0]:
            predictors.append(legal[:, col[added[0]]])
        X = np.column_stack([np.ones(len(y)), *predictors])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        r2 = 1.0 - float(resid.var() / y.var()) if y.var() > 0 else None
        entry["linear_r2_on_v2" + ("" if name == added[0] else "_plus_gain")] = r2
        entry["vif"] = None if r2 is None or r2 >= 1 else 1.0 / (1.0 - r2)
        redundancy[name] = entry

    constant_v2 = [c for c in v2_names if legal[:, col[c]].std() == 0]
    result = {
        "schema": "mcrl-v025-q1v4-added-field-correlation-v1", "no_training": True, "no_ee": True,
        "instrument": {"path": str(PENALTIES), "sha256": PENALTIES_SHA256,
                       "function": "q_row_decorrelation_penalty", "permutations_per_cell": PERMUTATIONS},
        "gaussian_floor_reference": {"10_columns": 0.273525, "9_columns": 0.291000,
                                     "source": "Q-ROW-COLLINEARITY-2026-09-10.md section 3 (transcribed)"},
        "screen_thresholds": {"STRUCTURALLY_WEAK": WEAK_CONSTANT_FRACTION, "COLLINEAR_ACROSS_USERS": COLLINEAR_EXCESS},
        "complete_block_users_total": complete_users_total, "anchors": int(len(anchors)),
        "fields": fields_out,
        "subsets": {s: summarize(v["with_null"], v["null_with"]) for s, v in per_subset.items()},
        "row_level_redundancy_legal_rows": redundancy,
        "v2_coordinates_exactly_constant_on_legal_rows": constant_v2,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("ANALYSIS COMPLETE", flush=True)
    print(f"PEAK_RSS_BYTES={result['peak_rss_bytes']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
