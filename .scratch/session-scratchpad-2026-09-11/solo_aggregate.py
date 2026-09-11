#!/usr/bin/env python3
"""SOLO aggregation: Level 1 lattice, correlations, Pareto, panel parity; Level 2 knockout summaries."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import random
import resource
import sys
from collections import Counter, defaultdict

WS = Path("/home/sat/mcrl-v025-solo-ws")
PARTS = [WS / ".scratch/level1" / f"part-{x}.jsonl" for x in "ABC"]
L2DIR = WS / ".scratch/level2"
PANEL_Q1V1 = Path("/home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v1.json")
OUT = WS / ".scratch/solo-aggregate.json"
ROUTES = ("C1", "C2", "C3")
LATTICE = ["NONE", "C1", "C2", "C3", "C1+C2", "C1+C3", "C2+C3", "C1+C2+C3"]
DIAG = ["C1_phys", "C2_surplus", "C3_phys", "dF", "dF_phys"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss():
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    r = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = math.fsum(x) / n, math.fsum(y) / n
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.fsum((a - mx) ** 2 for a in x)
    syy = math.fsum((b - my) ** 2 for b in y)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def pool(rows):
    bits = math.fsum(r["bits"] for r in rows)
    joules = math.fsum(r["joules"] for r in rows)
    users = sum(r["users"] for r in rows)
    return {
        "bits": bits, "joules": joules, "ee": bits / joules / 1e6,
        "served": sum(r["served"] for r in rows), "rate_attained": sum(r["rate_attained"] for r in rows),
        "handovers": sum(r["handovers"] for r in rows), "users": users,
        "served_frac": sum(r["served"] for r in rows) / users,
        "rate_frac": sum(r["rate_attained"] for r in rows) / users,
    }


def pareto(points):
    """points: name -> (x, y), both higher-better. Returns dict name -> list of dominators."""
    dom = {}
    for a, (xa, ya) in points.items():
        dom[a] = [b for b, (xb, yb) in points.items()
                  if b != a and xb >= xa and yb >= ya and (xb > xa or yb > ya)]
    return dom


def combo_class(points_ee, combo):
    parts = combo.split("+")
    singles = [points_ee[p] for p in parts]
    v = points_ee[combo]
    if v > max(singles):
        return "a_above_every_constituent"
    if v >= min(singles):
        return "b_between_constituents"
    return "c_below_every_constituent" if v < min(singles) else "c"


def combo_class_strict(points_ee, combo):
    parts = combo.split("+")
    singles = [points_ee[p] for p in parts]
    v = points_ee[combo]
    best = max(singles)
    if v > best:
        return "(a) above best constituent"
    if v == best:
        return "(=) equal to best constituent"
    if v >= min(singles):
        return "(b) between constituents"
    return "(c) below every constituent"


def level1():
    anchors = []
    for part in PARTS:
        if not part.exists():
            continue
        with part.open() as fh:
            for line in fh:
                anchors.append(json.loads(line))
    anchors.sort(key=lambda a: a["global_anchor_index"])
    idx = [a["global_anchor_index"] for a in anchors]
    result = {"anchor_count": len(anchors), "global_indices": idx,
              "part_sha256": {p.name: sha256(p) for p in PARTS if p.exists()}}

    def sel_rows(anchor_list, key):
        rows = []
        for a in anchor_list:
            i = a["selections"][key]
            rows.append(a["profiles"][i])
        return rows

    def lattice_block(anchor_list, family="fresh"):
        block = {}
        none_rows = sel_rows(anchor_list, f"{family}:NONE")
        none = pool(none_rows)
        for name in LATTICE:
            key = f"{family}:{name}"
            if any(a["selections"].get(key) is None for a in anchor_list):
                block[name] = None
                continue
            rows = sel_rows(anchor_list, key)
            p = pool(rows)
            p["rel_vs_none"] = (p["ee"] - none["ee"]) / none["ee"]
            per_anchor = [(r["bits"] / r["joules"]) - (n["bits"] / n["joules"]) for r, n in zip(rows, none_rows)]
            p["anchors_ee_up"] = sum(d > 0 for d in per_anchor)
            p["anchors_ee_down"] = sum(d < 0 for d in per_anchor)
            p["anchors_equal_none"] = sum(a["selections"][key] == a["selections"][f"{family}:NONE"] for a in anchor_list)
            p["selected_k"] = dict(Counter(str(r["k"]) for r in rows))
            p["selected_kind"] = dict(Counter(r["kind"] for r in rows))
            block[name] = p
        return block

    subsets = {
        "all": anchors,
        "panel_000_019": [a for a in anchors if a["global_anchor_index"] <= 19],
        "exact22_000_021": [a for a in anchors if a["global_anchor_index"] <= 21],
        "outside_022_092": [a for a in anchors if a["global_anchor_index"] >= 22],
    }
    result["lattice_fresh"] = {k: lattice_block(v) for k, v in subsets.items() if v}
    result["lattice_label"] = {k: lattice_block(v, "label") for k, v in subsets.items() if v}
    # diagnostics
    diag = {}
    none_rows = sel_rows(anchors, "fresh:NONE")
    none = pool(none_rows)
    for name in DIAG:
        rows = sel_rows(anchors, f"diag:{name}")
        p = pool(rows)
        p["rel_vs_none"] = (p["ee"] - none["ee"]) / none["ee"]
        p["selected_k"] = dict(Counter(str(r["k"]) for r in rows))
        diag[name] = p
    result["diagnostic_selections"] = diag
    # fresh-vs-label agreement
    agree = {}
    for name in LATTICE:
        same = [a["selections"][f"fresh:{name}"] == a["selections"].get(f"label:{name}") for a in anchors]
        agree[name] = {"same_selection_anchors": sum(same), "anchors": len(anchors)}
    result["fresh_vs_label_selection_agreement"] = agree
    # parity
    par = defaultdict(float)
    flags = Counter()
    for a in anchors:
        for k in ("C1_max_abs", "C2_max_abs", "C3_max_abs", "C3_phys_max_abs"):
            v = a["parity"][k]
            if v is not None:
                par[k] = max(par[k], v)
        flags["coalition_set_equal"] += bool(a["parity"]["coalition_set_equals_catalogue_multi_user_set"])
        flags["label_missing_profiles"] += a["parity"]["label_missing_profiles"]
        flags["selection_invalid"] += a["selection_invalid"]
        flags["endpoint_invalid"] += a["endpoint_invalid"]
        flags["c2_reference_fresh_values"] += 0
    result["parity_max"] = dict(par)
    result["parity_flags"] = dict(flags)
    result["c2_reference_values"] = dict(Counter(str(a["parity"]["c2_reference_fresh"]) for a in anchors))
    result["catalogue_sizes"] = [a["catalogue"]["bounded_catalogue_count"] for a in anchors]
    result["peak_rss_workers"] = max(a["peak_rss_bytes"] for a in anchors)
    result["wall"] = {k: math.fsum(a["wall"][k] for a in anchors) for k in anchors[0]["wall"]}
    # instruments
    base_p = pool([a["base"] for a in anchors])
    rss_p = pool([a["rss_max"] for a in anchors])
    result["instruments"] = {"BASE": base_p, "RSS_MAX": rss_p}
    for name, sub in subsets.items():
        if sub:
            result["instruments"][f"BASE_{name}"] = pool([a["base"] for a in sub])
            result["instruments"][f"RSS_MAX_{name}"] = pool([a["rss_max"] for a in sub])
    # cluster bootstrap by (world, step) for rel vs none
    clusters = defaultdict(list)
    for a in anchors:
        clusters[(a["world_index"], a["step_index"])].append(a)
    keys = sorted(clusters)
    rng = random.Random(20260911)
    boot = {name: [] for name in LATTICE[1:]}
    for _ in range(2000):
        pick = [clusters[keys[rng.randrange(len(keys))]] for _ in keys]
        sample = [a for c in pick for a in c]
        nb = pool(sel_rows(sample, "fresh:NONE"))
        for name in LATTICE[1:]:
            pb = pool(sel_rows(sample, f"fresh:{name}"))
            boot[name].append((pb["ee"] - nb["ee"]) / nb["ee"])
    ci = {}
    for name, vals in boot.items():
        vals.sort()
        ci[name] = {"p2.5": vals[int(0.025 * len(vals))], "p97.5": vals[int(0.975 * len(vals)) - 1],
                    "fraction_positive": sum(v > 0 for v in vals) / len(vals)}
    result["bootstrap_rel_vs_none_world_step_clusters"] = {"clusters": len(keys), "resamples": 2000, "ci": ci}

    # correlations over catalogue rows (non-BASE, valid)
    corr = {}
    specs = [("C1", "all"), ("C1_phys", "all"), ("C2", "all"), ("C2_surplus", "all"),
             ("C3", "multi"), ("C3_phys", "multi"), ("C3", "all"), ("dF", "all"), ("dF_phys", "all"),
             ("C1+C2+C3", "all")]
    responses = ["dEE", "dbits", "djoules", "dF48_phys", "dserved"]
    table = defaultdict(lambda: defaultdict(list))
    per_anchor_sp = defaultdict(list)
    for a in anchors:
        b = a["base"]
        rows = [r for r in a["profiles"][1:] if "dEE" in r and "C1" in r]
        for r in rows:
            r["dbits"] = r["bits"] - b["bits"]
            r["djoules"] = r["joules"] - b["joules"]
            r["dserved"] = r["served"] - b["served"]
            r["C1+C2+C3"] = r["C1"] + r["C2"] + r["C3"]
        for target, scope in specs:
            use = [r for r in rows if scope == "all" or r["k"] >= 2]
            for r in use:
                table[(target, scope)]["x"].append(r[target])
                for resp in responses:
                    table[(target, scope)][resp].append(r[resp])
            if len(use) >= 5:
                sp = spearman([r[target] for r in use], [r["dEE"] for r in use])
                if sp is not None:
                    per_anchor_sp[(target, scope)].append(sp)
    for (target, scope), cols in table.items():
        entry = {"rows": len(cols["x"])}
        for resp in responses:
            entry[f"pearson_{resp}"] = pearson(cols["x"], cols[resp])
            entry[f"spearman_{resp}"] = spearman(cols["x"], cols[resp])
        sps = sorted(per_anchor_sp[(target, scope)])
        entry["per_anchor_spearman_dEE"] = {
            "anchors": len(sps), "median": sps[len(sps) // 2] if sps else None,
            "positive": sum(s > 0 for s in sps), "negative": sum(s < 0 for s in sps),
            "min": sps[0] if sps else None, "max": sps[-1] if sps else None}
        corr[f"{target}|{scope}"] = entry
    result["correlations"] = corr
    # top-1 agreement: does the target's argmax row also have dEE > 0?
    top = {}
    for target in ("C1", "C2", "C3", "dF"):
        up = sum(1 for a in anchors if (lambda r: r.get("dEE", 0) > 0)(a["profiles"][a["selections"][f"fresh:{target}" if target != "dF" else "diag:dF"]]))
        top[target] = {"anchors_argmax_has_dEE_gt_0": up, "anchors": len(anchors)}
    # EE-best catalogue row per anchor (context, not a gate)
    best_rows = []
    for a in anchors:
        valid = [r for r in a["profiles"] if "dEE" in r and "C1" in r]
        base_served = a["base"]["served"]
        best_rows.append(max(valid, key=lambda r: (r["bits"] / r["joules"], -r["order"])))
    result["catalogue_ee_best_context"] = pool(best_rows)
    result["argmax_dEE_positive"] = top
    # Pareto + combination classes on the main set
    lat = result["lattice_fresh"]["all"]
    ee = {k: lat[k]["ee"] for k in LATTICE}
    result["pareto_rate"] = pareto({k: (lat[k]["ee"], lat[k]["rate_frac"]) for k in LATTICE})
    result["pareto_served"] = pareto({k: (lat[k]["ee"], lat[k]["served_frac"]) for k in LATTICE})
    result["combination_class"] = {c: combo_class_strict(ee, c) for c in ("C1+C2", "C1+C3", "C2+C3", "C1+C2+C3")}
    return result, anchors


def panel_parity(anchors):
    raw = json.loads(PANEL_Q1V1.read_text())
    by_anchor = {a["anchor_id"]: a for a in raw["anchors"]}
    out = {"anchors_compared": 0, "profiles_compared": 0, "bits_max_rel": 0.0, "joules_max_rel": 0.0,
           "served_mismatch": 0, "rate_mismatch": 0, "handover_mismatch": 0,
           "catalogue_ids_subset_of_panel": 0, "panel_extras_per_anchor": [], "base_id_match": 0}
    for a in anchors:
        pa = by_anchor.get(a["anchor_id"])
        if pa is None:
            continue
        out["anchors_compared"] += 1
        pmap = {p["profile_id"]: p for p in pa["profiles"]}
        mine = {"profile:" + hashlib.sha256(r["id"].encode("ascii")).hexdigest(): r for r in a["profiles"]}
        base_pid = "profile:" + hashlib.sha256(a["base_id"].encode("ascii")).hexdigest()
        out["base_id_match"] += base_pid == pa["base_profile_id"]
        out["catalogue_ids_subset_of_panel"] += set(mine) <= set(pmap)
        out["panel_extras_per_anchor"].append(len(set(pmap) - set(mine)))
        for pid, r in mine.items():
            p = pmap.get(pid)
            if p is None or "bits" not in r:
                continue
            o = p["outcome"]
            out["profiles_compared"] += 1
            out["bits_max_rel"] = max(out["bits_max_rel"], abs(r["bits"] - o["full_buffer_bits"]) / max(1.0, o["full_buffer_bits"]))
            out["joules_max_rel"] = max(out["joules_max_rel"], abs(r["joules"] - o["joules"]) / o["joules"])
            out["served_mismatch"] += r["served"] != o["service_available"]
            out["rate_mismatch"] += r["rate_attained"] != o["rate_target_attained"]
            out["handover_mismatch"] += r["handovers"] != o["handovers"]
    del raw
    return out


def level2():
    runs = {}
    for path in sorted(L2DIR.glob("*.json")):
        d = json.loads(path.read_text())
        seeds = d["checkpoints"]
        lat = {}
        for name in LATTICE:
            bits = math.fsum(c["lattice"][name]["bits"] for c in seeds)
            joules = math.fsum(c["lattice"][name]["joules"] for c in seeds)
            served = sum(c["lattice"][name]["served"] for c in seeds)
            opp = sum(c["lattice"][name]["service_opportunities"] for c in seeds)
            rate = sum(c["lattice"][name]["rate_target_attained"] for c in seeds)
            ropp = sum(c["lattice"][name]["rate_target_opportunities"] for c in seeds)
            lat[name] = {"ee": bits / joules / 1e6, "served_frac": served / opp, "rate_frac": rate / ropp,
                         "per_seed_ee": [c["lattice"][name]["pooled_ee_mbit_per_j"] for c in seeds],
                         "anchors_differing_from_NONE_per_seed": [c["lattice"][name]["anchors_differing_from_NONE"] for c in seeds]}
        none = lat["NONE"]["ee"]
        for name in LATTICE:
            lat[name]["rel_vs_none"] = (lat[name]["ee"] - none) / none
            diffs = [x - y for x, y in zip(lat[name]["per_seed_ee"], lat["NONE"]["per_seed_ee"])]
            lat[name]["seeds_up_vs_none"] = sum(d > 0 for d in diffs)
            lat[name]["seeds_down_vs_none"] = sum(d < 0 for d in diffs)
        for pair in ("C1+C2+C3",):
            pass
        ee = {k: lat[k]["ee"] for k in LATTICE}
        runs[d["tag"]] = {
            "label": d["label"], "epoch": d["epoch"], "seeds": [c["learner_seed"] for c in seeds],
            "checkpoint_sha256": [c["checkpoint_sha256"] for c in seeds],
            "full_mismatch_total": sum(c["full_selection_mismatch_vs_unmodified_scorer"] for c in seeds),
            "knockout_base_failures": sum(c["knockout_base_check_failures"] for c in seeds),
            "missing_seeds": d["missing_seeds_at_epoch"], "gate": d["gate"], "panel": d["panel"],
            "training_schedule": d.get("training_schedule"), "lattice": lat,
            "pareto_rate": pareto({k: (lat[k]["ee"], lat[k]["rate_frac"]) for k in LATTICE}),
            "pareto_served": pareto({k: (lat[k]["ee"], lat[k]["served_frac"]) for k in LATTICE}),
            "combination_class": {c: combo_class_strict(ee, c) for c in ("C1+C2", "C1+C3", "C2+C3", "C1+C2+C3")},
            "file_sha256": sha256(path),
        }
    return runs


def main():
    l1, anchors = level1()
    l1["panel_q1v1_parity"] = panel_parity(anchors)
    out = {"level1": l1, "level2": level2(), "peak_rss_bytes": peak_rss(),
           "script_sha256": sha256(Path(__file__))}
    OUT.write_text(json.dumps(out, sort_keys=True, indent=1) + "\n")
    print(f"wrote {OUT} PEAK_RSS_BYTES={peak_rss()}")


if __name__ == "__main__":
    main()
