#!/usr/bin/env python3
"""TRIOBJ merge: pooled analysis of items 2, 4, 5 from shard rows.  No physics
evaluation happens here; every number is arithmetic over the dense-evaluator rows
the shards wrote.  DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

OUTDIR = Path("/home/sat/mcrl-v025-triobj-ws/.scratch/triobj")
ETA_REF = 14235186615308645000000 / 1300834130903823
KAPPA = 8541111969185187 / 10000000
EXPECTED_PARITY = {"RSS_MAX": 41.621560, "CROWDED": 46.110374}


def load(prefix: str):
    rows = []
    metas = []
    for path in sorted(OUTDIR.glob(f"{prefix}-rows-steps*.jsonl")):
        with path.open() as h:
            rows.extend(json.loads(line) for line in h)
    for path in sorted(OUTDIR.glob(f"{prefix}-meta-steps*.json")):
        metas.append(json.loads(path.read_text()))
    return rows, metas


def by_anchor(rows):
    out = {}
    for r in rows:
        out.setdefault(r["anchor_index"], []).append(r)
    return dict(sorted(out.items()))


def is_base(r):
    return "BASE" in r["tags"]


def in_pool(r, pool):
    if pool == "EXT":
        return True
    if pool == "CAT":
        return bool({"BASE", "CATALOGUE"} & set(r["tags"]))
    if pool == "MIX":
        return any(t in ("RSS_MAX", "CROWDED", "MINCOVER_LQ") or t.startswith(("DROP_", "ADD_", "CROWD_FAMILY_"))
                   for t in r["tags"])
    raise ValueError(pool)


def ee(r, horizon="f48"):
    return r[horizon]["bits"] / r[horizon]["joules"]


def pooled(sel):
    bits = math.fsum(r["f48"]["bits"] for r in sel)
    joules = math.fsum(r["f48"]["joules"] for r in sel)
    hbits = math.fsum(r["f48"]["bits"] - r["h_removed_bits_derived"] for r in sel)
    b0b = math.fsum(r["b0"]["bits"] for r in sel)
    b0j = math.fsum(r["b0"]["joules"] for r in sel)
    return {
        "anchors": len(sel),
        "bits": bits, "joules": joules, "ee_mbit_per_j": bits / joules / 1e6,
        "served": sum(r["f48"]["served"] for r in sel), "users": 100 * len(sel),
        "attained": sum(r["f48"]["attained"] for r in sel),
        "beams_decision_mean": sum(r["beams"] for r in sel) / len(sel),
        "radiating_beams_mean": sum(r["f48"]["mean_radiating_beams"] for r in sel) / len(sel),
        "phi_cost_bits": math.fsum(r["phi_cost_bits"] for r in sel),
        "phi_cost_share_of_f48_bits": math.fsum(r["phi_cost_bits"] for r in sel) / bits if bits else None,
        "events": {k: sum(r["events"].get(k, 0) for r in sel)
                   for k in ("satellite_change", "beam_change", "exit", "initial_entry", "reentry", "unchanged")},
        "h_adjusted_ee_mbit_per_j_derived": hbits / joules / 1e6,
        "h_removed_share_of_bits_derived": (bits - hbits) / bits if bits else None,
        "b0_ee_mbit_per_j": b0b / b0j / 1e6,
        "changed_vs_base_mean": sum(r["changed_vs_base"] for r in sel) / len(sel),
        "null_users": sum(r["null_users"] for r in sel),
        "tags": [sorted(r["tags"])[:4] for r in sel],
    }


def obj(r, name):
    return {"LQ": r["LQ"], "BC": -r["beams"], "P": r["P"], "S": float(r["S"])}[name]


def argmax(cands, keyfn, tol=0.0):
    best = max(keyfn(r) for r in cands)
    ties = [r for r in cands if keyfn(r) >= best - tol]
    pick = min(ties, key=lambda r: (r["changed_vs_base"], r["configuration_id_sha256"]))
    return pick, ties


def guard_ok(r, base, horizon="f48"):
    return r[horizon]["served"] >= base[horizon]["served"]


def alone(anchors, pool, name, guard):
    picks, lo, hi, tie_sizes = [], [], [], []
    for idx, rows in anchors.items():
        base = next(r for r in rows if is_base(r))
        cands = [r for r in rows if in_pool(r, pool)]
        if guard == "f48":
            cands = [r for r in cands if guard_ok(r, base, "f48")]
        elif guard == "b0":
            cands = [r for r in cands if guard_ok(r, base, "b0")]
        tol = 1e-9 if name == "LQ" else 0.0
        pick, ties = argmax(cands, lambda r: obj(r, name), tol)
        picks.append(pick)
        tie_sizes.append(len(ties))
        lo.append(min(ties, key=ee))
        hi.append(max(ties, key=ee))
    out = pooled(picks)
    out["tie_set_sizes"] = tie_sizes
    out["tie_set_worst_ee_pooled"] = pooled(lo)["ee_mbit_per_j"]
    out["tie_set_best_ee_pooled"] = pooled(hi)["ee_mbit_per_j"]
    out["per_anchor_ee"] = [ee(r) / 1e6 for r in picks]
    out["per_anchor_served"] = [r["f48"]["served"] for r in picks]
    return out


def guarded_sets(anchors, pool):
    sets = {}
    for idx, rows in anchors.items():
        base = next(r for r in rows if is_base(r))
        sets[idx] = [r for r in rows if in_pool(r, pool) and guard_ok(r, base, "f48")]
    return sets


def dinkelbach(sets, horizon="f48", phi=False, per_anchor=False, max_iter=100):
    trace = []

    def score(r, eta):
        v = r[horizon]["bits"] - eta * r[horizon]["joules"]
        return v - (r["phi_cost_bits"] if phi else 0.0)

    if per_anchor:
        picks = []
        for idx, cands in sets.items():
            eta = ETA_REF
            for _ in range(max_iter):
                pick = max(cands, key=lambda r: (score(r, eta), -r["changed_vs_base"], r["configuration_id_sha256"]))
                new = pick[horizon]["bits"] / pick[horizon]["joules"]
                if abs(new - eta) <= 1e-9 * max(1.0, abs(eta)):
                    break
                eta = new
            picks.append(pick)
        return picks, None
    eta = ETA_REF
    for it in range(max_iter):
        picks = [max(c, key=lambda r: (score(r, eta), -r["changed_vs_base"], r["configuration_id_sha256"]))
                 for c in sets.values()]
        new = math.fsum(r[horizon]["bits"] for r in picks) / math.fsum(r[horizon]["joules"] for r in picks)
        trace.append({"iteration": it, "eta_mbit_per_j": eta / 1e6, "next_eta_mbit_per_j": new / 1e6})
        if abs(new - eta) <= 1e-12 * max(1.0, abs(eta)):
            break
        eta = new
    return picks, trace


def fixed_physical(sets, eta, horizon, phi):
    return [max(c, key=lambda r: (r[horizon]["bits"] - eta * r[horizon]["joules"] - (r["phi_cost_bits"] if phi else 0.0),
                                  -r["changed_vs_base"], r["configuration_id_sha256"])) for c in sets.values()]


def pooled_ee_max_bruteforce_check(sets, picks):
    # Dinkelbach optimality certificate: no anchor can raise sum(B - eta* E) at eta* = pooled EE of picks.
    bits = math.fsum(r["f48"]["bits"] for r in picks)
    joules = math.fsum(r["f48"]["joules"] for r in picks)
    eta = bits / joules
    slack = 0.0
    for (idx, cands), pick in zip(sets.items(), picks):
        best = max(r["f48"]["bits"] - eta * r["f48"]["joules"] for r in cands)
        slack = max(slack, best - (pick["f48"]["bits"] - eta * pick["f48"]["joules"]))
    return slack


def normalizers(anchors, pool, names):
    norm = {}
    for idx, rows in anchors.items():
        cands = [r for r in rows if in_pool(r, pool)]
        norm[idx] = {n: (min(obj(r, n) for r in cands), max(obj(r, n) for r in cands)) for n in names}
    return norm


def scal(r, weights, norm_a):
    total = 0.0
    for n, w in weights.items():
        lo, hi = norm_a[n]
        total += w * ((obj(r, n) - lo) / (hi - lo) if hi > lo else 0.0)
    return total


def weight_sweep(anchors, sets, pool, names, grid):
    norm = normalizers(anchors, pool, names)
    rows = []
    for weights in grid:
        picks = [max(c, key=lambda r: (scal(r, weights, norm[idx]), -r["changed_vs_base"], r["configuration_id_sha256"]))
                 for idx, c in sets.items()]
        p = pooled(picks)
        p.pop("tags")
        rows.append({"weights": weights, **p, "picks_tags": [sorted(r["tags"])[:3] for r in picks]})
    return rows


def rankdata(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(x, y):
    rx, ry = rankdata(x), rankdata(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def pareto_front(cands):
    front = []
    for r in cands:
        dominated = any(
            (o["f48"]["bits"] >= r["f48"]["bits"] and o["f48"]["joules"] <= r["f48"]["joules"]
             and (o["f48"]["bits"] > r["f48"]["bits"] or o["f48"]["joules"] < r["f48"]["joules"]))
            for o in cands
        )
        if not dominated:
            front.append(r)
    return front


def main(prefix: str) -> int:
    rows, metas = load(prefix)
    anchors = by_anchor(rows)
    result = {"schema": "mcrl-v025-triobj-merge-v1", "prefix": prefix, "anchors": list(anchors),
              "row_count": len(rows), "shard_meta": [{k: m.get(k) for k in ("steps", "status", "scalar_evaluate_calls",
                                                                               "peak_rss_bytes", "wall_seconds", "rows_sha256",
                                                                               "runner_sha256")} for m in metas]}
    # reference rows
    ref = {}
    for tag in ("BASE", "RSS_MAX", "CROWDED", "MINCOVER_LQ", "SURV_LQ", "HOLD_MIN", "HOLD_NULL"):
        sel = []
        for idx, rs in anchors.items():
            hit = [r for r in rs if tag in r["tags"]]
            if hit:
                sel.append(hit[0])
        if sel:
            p = pooled(sel)
            p.pop("tags")
            ref[tag] = p
    result["references"] = ref
    if len(anchors) == 12:
        for name, expected in EXPECTED_PARITY.items():
            got = ref[name]["ee_mbit_per_j"]
            if round(got, 6) != round(expected, 6):
                raise RuntimeError(f"STOP parity {name}: {got}")
        result["parity"] = "PASS"

    # item 2: each objective alone
    item2 = {}
    for pool in ("CAT", "EXT"):
        for name in ("LQ", "BC", "P", "S"):
            for guard in ("f48", "b0", "none"):
                a = alone(anchors, pool, name, guard)
                a.pop("tags")
                item2[f"{pool}|{name}|guard={guard}"] = a
    result["item2_alone"] = item2

    # EE maxima (oracle references) per pool, guarded
    peaks = {}
    for pool in ("CAT", "MIX", "EXT"):
        sets = guarded_sets(anchors, pool)
        picks, trace = dinkelbach(sets, "f48")
        p = pooled(picks)
        p["dinkelbach_trace"] = trace
        p["optimality_slack_bits"] = pooled_ee_max_bruteforce_check(sets, picks)
        peaks[f"{pool}|pooled_dinkelbach_f48"] = p
        pa, _ = dinkelbach(sets, "f48", per_anchor=True)
        peaks[f"{pool}|per_anchor_ee_max_f48"] = pooled(pa)
        pb, tb = dinkelbach(sets, "b0")
        q = pooled(pb)
        q["dinkelbach_trace_b0"] = tb
        peaks[f"{pool}|pooled_dinkelbach_b0_scored_f48"] = q
        pc, tc = dinkelbach(sets, "f48", phi=True)
        q = pooled(pc)
        q["dinkelbach_trace_with_phi"] = tc
        peaks[f"{pool}|pooled_dinkelbach_f48_with_phi"] = q
        pd, td = dinkelbach(sets, "b0", phi=True)
        q = pooled(pd)
        q["dinkelbach_trace_b0_with_phi"] = td
        peaks[f"{pool}|pooled_dinkelbach_b0_with_phi_scored_f48"] = q
        for horizon in ("b0", "f48"):
            for phi in (False, True):
                peaks[f"{pool}|fixed_eta_ref|{horizon}|phi={phi}"] = pooled(fixed_physical(sets, ETA_REF, horizon, phi))
        # unguarded pooled EE max for context
        ug = {idx: [r for r in rs if in_pool(r, pool)] for idx, rs in anchors.items()}
        pu, _ = dinkelbach(ug, "f48")
        peaks[f"{pool}|pooled_dinkelbach_f48_UNGUARDED"] = pooled(pu)
    for v in peaks.values():
        v.pop("tags", None)
    result["peaks_and_physical_combinations"] = peaks

    # item 4: bits vs energy on MIX
    mix_sets = guarded_sets(anchors, "MIX")
    grid2 = [{"LQ": round(1 - w / 100, 2), "BC": round(w / 100, 2)} for w in range(101)]
    sweep2 = weight_sweep(anchors, mix_sets, "MIX", ("LQ", "BC"), grid2)
    result["item4_mix_weight_sweep"] = sweep2
    best2 = max(sweep2, key=lambda r: r["ee_mbit_per_j"])
    result["item4_best_fixed_weight"] = {k: best2[k] for k in ("weights", "ee_mbit_per_j", "served", "attained",
                                                                 "bits", "joules", "beams_decision_mean")}
    conflict = []
    for idx, rs in anchors.items():
        base = next(r for r in rs if is_base(r))
        cands = [r for r in rs if in_pool(r, "MIX") and guard_ok(r, base)]
        lq_pick, _ = argmax(cands, lambda r: obj(r, "LQ"), 1e-9)
        bc_pick, bc_ties = argmax(cands, lambda r: obj(r, "BC"))
        eepick = max(cands, key=ee)
        front = pareto_front(cands)
        conflict.append({
            "anchor_index": idx,
            "lq_opt": {"tags": lq_pick["tags"][:3], "bits": lq_pick["f48"]["bits"], "joules": lq_pick["f48"]["joules"],
                       "ee": ee(lq_pick) / 1e6, "beams": lq_pick["beams"]},
            "bc_opt": {"tags": bc_pick["tags"][:3], "bits": bc_pick["f48"]["bits"], "joules": bc_pick["f48"]["joules"],
                       "ee": ee(bc_pick) / 1e6, "beams": bc_pick["beams"], "tie_set": len(bc_ties)},
            "distinct": lq_pick["configuration_id_sha256"] != bc_pick["configuration_id_sha256"],
            "lq_more_bits": lq_pick["f48"]["bits"] > bc_pick["f48"]["bits"],
            "lq_more_joules": lq_pick["f48"]["joules"] > bc_pick["f48"]["joules"],
            "ee_peak": {"tags": eepick["tags"][:3], "ee": ee(eepick) / 1e6, "beams": eepick["beams"],
                        "LQ": eepick["LQ"], "served": eepick["f48"]["served"], "attained": eepick["f48"]["attained"]},
            "ee_peak_interior": eepick["configuration_id_sha256"] not in (lq_pick["configuration_id_sha256"], bc_pick["configuration_id_sha256"]),
            "pareto_front_size": len(front), "mix_guarded": len(cands),
            "lq_on_front": any(f["configuration_id_sha256"] == lq_pick["configuration_id_sha256"] for f in front),
            "bc_on_front": any(f["configuration_id_sha256"] == bc_pick["configuration_id_sha256"] for f in front),
            "ee_peak_on_front": any(f["configuration_id_sha256"] == eepick["configuration_id_sha256"] for f in front),
        })
    result["item4_conflict_per_anchor"] = conflict

    # proxy validity (Spearman over guarded EXT per anchor)
    proxy = []
    for idx, rs in anchors.items():
        base = next(r for r in rs if is_base(r))
        c = [r for r in rs if guard_ok(r, base)]
        proxy.append({
            "anchor_index": idx, "n": len(c),
            "LQ_vs_bits": spearman([r["LQ"] for r in c], [r["f48"]["bits"] for r in c]),
            "BC_vs_minus_joules": spearman([-r["beams"] for r in c], [-r["f48"]["joules"] for r in c]),
            "P_vs_EE": spearman([r["P"] for r in c], [ee(r) for r in c]),
            "LQ_vs_EE": spearman([r["LQ"] for r in c], [ee(r) for r in c]),
            "BC_vs_EE": spearman([-r["beams"] for r in c], [ee(r) for r in c]),
            "S_vs_EE": spearman([r["S"] for r in c], [ee(r) for r in c]),
        })
    result["proxy_spearman_guarded_ext"] = proxy

    # item 5: three-objective fixed simplex on EXT
    ext_sets = guarded_sets(anchors, "EXT")
    grid3 = []
    for i in range(21):
        for j in range(21 - i):
            k = 20 - i - j
            grid3.append({"LQ": i / 20, "BC": j / 20, "P": k / 20})
    sweep3 = weight_sweep(anchors, ext_sets, "EXT", ("LQ", "BC", "P"), grid3)
    result["item5_three_objective_sweep"] = [{k: r[k] for k in ("weights", "ee_mbit_per_j", "served", "attained",
                                                                "beams_decision_mean", "phi_cost_share_of_f48_bits")}
                                             for r in sweep3]
    best3 = max(sweep3, key=lambda r: r["ee_mbit_per_j"])
    result["item5_best_three_objective_weight"] = {k: best3[k] for k in ("weights", "ee_mbit_per_j", "served", "attained",
                                                                          "bits", "joules", "beams_decision_mean",
                                                                          "phi_cost_share_of_f48_bits", "picks_tags")}
    # does any time weight help: best EE among w_P > 0 vs w_P == 0
    result["item5_best_with_P_zero"] = max((r for r in sweep3 if r["weights"]["P"] == 0), key=lambda r: r["ee_mbit_per_j"])["ee_mbit_per_j"]
    result["item5_best_with_P_positive"] = max((r for r in sweep3 if r["weights"]["P"] > 0), key=lambda r: r["ee_mbit_per_j"])["ee_mbit_per_j"]
    # 2-objective sweep also on EXT for comparison
    sweep2e = weight_sweep(anchors, ext_sets, "EXT", ("LQ", "BC"), grid2)
    result["item5_ext_two_objective_best"] = {k: max(sweep2e, key=lambda r: r["ee_mbit_per_j"])[k]
                                              for k in ("weights", "ee_mbit_per_j", "served", "attained")}

    # time vs each (persistence ladders), guarded, per ladder position pooled
    ladders = {}
    for prefix_tag in ("HOLD_TO_RSS_", "HOLD_TO_CROWDED_", "HOLD_LADDER_"):
        names = sorted({t for r in rows for t in r["tags"] if t.startswith(prefix_tag)})
        for t in ["HOLD_NULL", "HOLD_MIN"] + names:
            sel = []
            for idx, rs in anchors.items():
                hit = [r for r in rs if t in r["tags"]]
                if hit:
                    sel.append(hit[0])
            if len(sel) == len(anchors):
                p = pooled(sel)
                p.pop("tags")
                p["P_mean"] = sum(r["P"] for r in sel) / len(sel)
                p["LQ_mean"] = sum(r["LQ"] for r in sel) / len(sel)
                p["guard_pass_anchors"] = sum(guard_ok(r, next(b for b in anchors[r["anchor_index"]] if is_base(b))) for r in sel)
                ladders[t] = p
    result["time_ladders"] = ladders

    # carrier-invariance of physics under different transition_from (b0 selection evaluators)
    inv_check = {"compared": 0, "max_rel_bits": 0.0, "max_rel_joules": 0.0}
    by_step = {}
    for r in rows:
        if any(t in ("RSS_MAX", "CROWDED", "MINCOVER_LQ", "SURV_LQ") or t.startswith(("DROP_", "ADD_", "CROWD_FAMILY_")) for t in r["tags"]):
            by_step.setdefault((r["step_index"], r["configuration_id_sha256"]), []).append(r)
    for key, rs in by_step.items():
        if len(rs) < 2:
            continue
        for a, b in itertools.combinations(rs, 2):
            inv_check["compared"] += 1
            inv_check["max_rel_bits"] = max(inv_check["max_rel_bits"], abs(a["b0"]["bits"] - b["b0"]["bits"]) / max(1.0, abs(a["b0"]["bits"])))
            inv_check["max_rel_joules"] = max(inv_check["max_rel_joules"], abs(a["b0"]["joules"] - b["b0"]["joules"]) / max(1e-12, abs(a["b0"]["joules"])))
            if a["events"] != b["events"]:
                inv_check["event_ledgers_differ"] = inv_check.get("event_ledgers_differ", 0) + 1
    result["transition_invariance_check_b0"] = inv_check

    payload = json.dumps(result, sort_keys=True, indent=1, allow_nan=True)
    out = OUTDIR / f"{prefix}-merge-receipt.json"
    out.write_text(payload + "\n")
    print(f"wrote {out} sha256 {hashlib.sha256(payload.encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "shard"))
