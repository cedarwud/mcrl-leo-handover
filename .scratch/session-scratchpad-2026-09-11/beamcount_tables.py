#!/usr/bin/env python3
"""Print report tables from a BEAMCOUNT project receipt (no physics)."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

path = Path(sys.argv[1])
d = json.loads(path.read_text())
P = d["pooled"]
anchors = d["anchors"]


def pooled_subset(label, rows):
    bits = math.fsum(r["endpoints"][label]["bits"] for r in rows)
    joules = math.fsum(r["endpoints"][label]["joules"] for r in rows)
    served = sum(r["endpoints"][label]["served_phy"] for r in rows)
    att = sum(r["endpoints"][label]["rate_target_attained"] for r in rows)
    act = sum(r["endpoints"][label]["active_beams_mapping"] for r in rows) / len(rows)
    return bits / joules / 1e6, served, att, act


def line(label, name=None):
    r = P[label]
    return (f"| {name or label} | {r['ee_mbit_per_j']:.6f} | {r['bits']:.6e} | {r['joules']:,.3f} | "
            f"{r['served_phy']}/{r['user_count']} | {r['rate_target_attained']}/{r['user_count']} "
            f"({100*r['rate_target_attained']/r['user_count']:.3f}%) | {r['modal_frac']:.6f} | "
            f"{r['active_beams_mapping_mean']:.3f} {r['active_beams_mapping_range']} | "
            f"{r['mean_radiating_beams_mean']:.3f} | {r['null_users']} |")


print("STATUS", d["status"], "rehearsal", d["rehearsal_not_reportable"], "scalar", d.get("scalar_evaluate_calls"))
print("PARITY", json.dumps(d["parity"], indent=1))
print("CROSS", d.get("cross_pass_rss_max_consistency"))
print("SHARDS", json.dumps(d.get("shards"), indent=1))
print("RUNTIME", d["runtime"])
print()
print("## feasibility")
for s, row in d["feasibility"]["per_step"].items():
    print(s, "floor", row["minimum_legal_beam_set_cover"], "greedy", row["greedy_cover_size"],
          "rank", row["maximum_distinct_beam_matching_rank"], "beams", row["distinct_legal_beams"],
          "sats", row["satellite_count"], "opts", row["legal_options_per_user"],
          "nolegal", row["users_without_legal_option"])
    print("   uncons cover per sat", {k: v for k, v in row["unconstrained_cover_beams_per_satellite"].items() if v})
    print("   cover", row["cover_beams"])
    for k, e in row["per_satellite_cap"].items():
        print("   persat", k, e["exact_status"], e["exact_minimum_cover_size"], "universe",
              e["system_wide_beam_universe"], {a: b for a, b in (e["cover_beams_per_satellite"] or {}).items() if b},
              "nodes", e["search_nodes"])
print()
hdr = ("| arm | pooled EE (Mbit/J) | pooled bits | pooled J | served PHY | rate-target attained | "
       "modal_frac | mapping-active mean [range] | mean radiating beams | null users |")
sep = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
print("## references")
print(hdr); print(sep)
for lbl, name in (("BASE_CARRIER", "carrier BASE"), ("PARITY_RSS_MAX", "RSS_MAX"),
                  ("PARITY_CROWDED_MIN_COVER", "crowded (min cover, CROWDCOST rule)"),
                  ("UNCAPPED_NATURAL", "uncapped b0-search, seeds BASE/RSS_MAX"),
                  ("UNCAPPED_BEST_KNOWN", "uncapped b0-search, best known")):
    print(line(lbl, name))
print()
print("## boundary-0-selected cap winners (mandated selection)")
print(hdr); print(sep)
caps = d["feasibility"]["evaluated_caps"]
for c in caps:
    print(line(f"CAP_{c:03d}", f"C={c} b0-selected"))
print()
print("## declared-rule frontier (post hoc best of 9 declared rules, full-48)")
print(hdr); print(sep)
for c in caps:
    fr = d["cap_frontier"][str(c)]
    declared = {k: v for k, v in fr["members"].items() if "__" in k}
    best = max(declared, key=lambda k: declared[k]["ee_mbit_per_j"])
    print(line(best, f"C={c} {best.split('__')[1]}"))
print()
print("## canonical CROWDCOST rule S1|A1 at each cap")
print(hdr); print(sep)
for c in caps:
    print(line(f"CAP_{c:03d}__S1_ascending_coverage|A1_coverage_first", f"C={c} S1|A1"))
print()
print("## A2 (max nominal gain) rule, per beam-set rule, EE / served / attained")
for c in caps:
    parts = []
    for s in ("S1_ascending_coverage", "S2_descending_coverage", "S3_descending_nominal_gain"):
        for a in ("A1_coverage_first", "A2_max_nominal_gain", "A3_least_loaded"):
            r = P[f"CAP_{c:03d}__{s}|{a}"]
            parts.append(f"{s[:2]}{a[:2]}={r['ee_mbit_per_j']:.3f}/{r['served_phy']}/{r['rate_target_attained']}")
    print(c, " ".join(parts))
print()
print("## per-satellite caps")
print(hdr); print(sep)
for lbl in sorted(k for k in P if k.startswith("PERSAT_")):
    print(line(lbl))
print()
print("## per physical step (3 carrier anchors pooled): EE / served / attained / active")
steps = defaultdict(list)
for r in anchors:
    steps[r["step_index"]].append(r)
keys = ["BASE_CARRIER", "PARITY_RSS_MAX", "PARITY_CROWDED_MIN_COVER", "UNCAPPED_NATURAL",
        "UNCAPPED_BEST_KNOWN"] + [f"CAP_{c:03d}" for c in caps] + [
        "PERSAT_3__A1_coverage_first", "PERSAT_3__A2_max_nominal_gain"]
for k in keys:
    if k not in P:
        continue
    cells = []
    for s in sorted(steps):
        ee, sv, at, ac = pooled_subset(k, steps[s])
        cells.append(f"s{s}: {ee:.3f} / {sv} / {at} / {ac:.1f}")
    print(f"{k}: " + " | ".join(cells))
print()
print("## carrier invariance check (same mapping label across carriers at one step)")
bad = 0
for s, rows in steps.items():
    for k in keys:
        if k == "BASE_CARRIER" or k not in rows[0]["endpoints"]:
            continue
        vals = {round(r["endpoints"][k]["ee_bit_per_j"], 3) for r in rows}
        if len(vals) > 1:
            bad += 1
            print("differs", s, k, vals)
print("carrier-differing label-steps:", bad)
print()
print("## search detail per anchor: winner start, b0 EE, full-48 EE, active")
for r in anchors:
    cells = []
    for c in caps:
        sd = r["search"][f"CAP_{c:03d}"]
        cells.append(f"C{c}:{sd['winner_start'][:22]}:{sd['winner_boundary0_ee_bit_per_j']/1e6:.1f}->"
                     f"{r['endpoints'][f'CAP_{c:03d}']['ee_bit_per_j']/1e6:.1f}:{sd['winner_realised_active_beams']}"
                     f"{'' if sd['guard_satisfied'] else '!'}")
    print(r["anchor_id"], " ".join(cells))
    un = r["search"]["UNCAPPED_NATURAL_SEEDS"]
    print("   uncapped natural", [(x["seed"], round(x["boundary0_ee_bit_per_j"] / 1e6, 2), x["moves"], x["passes"]) for x in un["seeds"]],
          "->", round(r["endpoints"]["UNCAPPED_NATURAL"]["ee_bit_per_j"] / 1e6, 2),
          "rss full48", round(r["endpoints"]["PARITY_RSS_MAX"]["ee_bit_per_j"] / 1e6, 2))
print()
HAS_PROJ = "projection" in d
PP = d["projection"]["pooled"] if HAS_PROJ else {}
print("## projection onto C* =", d["projection"]["target_cap"] if HAS_PROJ else "NOT YET")
print(hdr); print(sep)
for lbl in ("RSS_MAX", "RSS_MAX_PROJECTED", "RSS_MAX_OWN_FOOTPRINT", "A0_ALL_SEEDS",
            "A0_ALL_SEEDS_PROJECTED", "A0_ALL_SEEDS_OWN_FOOTPRINT"):
    if lbl not in PP:
        continue
    r = PP[lbl]
    print(f"| {lbl} | {r['ee_mbit_per_j']:.6f} | {r['bits']:.6e} | {r['joules']:,.3f} | {r['served_phy']}/{r['user_count']} | "
          f"{r['rate_target_attained']}/{r['user_count']} ({100*r['rate_target_attained']/r['user_count']:.3f}%) | "
          f"{r['modal_frac']:.6f} | {r['active_beams_mapping_mean']:.3f} {r['active_beams_mapping_range']} | "
          f"{r['mean_radiating_beams_mean']:.3f} | {r['null_users']} |")
print()
print("## projections at every cap: EE / served / attained / mapping-active / nulls")
for c in caps:
    cells = []
    for lbl in (f"RSS_MAX_PROJECTED_C{c:03d}", f"RSS_MAX_OWN_FOOTPRINT_C{c:03d}",
                f"A0_ALL_SEEDS_PROJECTED_C{c:03d}", f"A0_ALL_SEEDS_OWN_FOOTPRINT_C{c:03d}"):
        if lbl not in PP:
            continue
        r = PP[lbl]
        cells.append(f"{lbl.replace(f'_C{c:03d}', '')}={r['ee_mbit_per_j']:.4f}/{r['served_phy']}/"
                     f"{r['rate_target_attained']}/{r['active_beams_mapping_mean']:.2f}/{r['null_users']}")
    print(f"C={c}: " + " | ".join(cells))
per_cap_moves = defaultdict(lambda: defaultdict(int))
for a in (d["projection"]["anchors"] if HAS_PROJ else []):
    for lbl, row in a["rows"].items():
        if "_C0" not in lbl:
            continue
        fam = "RSS" if lbl.startswith("RSS") else "A0"
        cap = int(lbl.rsplit("_C", 1)[1])
        kind = "PROJ" if "PROJECTED" in lbl else "OWN"
        for f in ("kept", "moved", "rescued_from_null", "stranded_users"):
            if f in row:
                per_cap_moves[(fam, kind, cap)][f] += int(row[f])
        if "own_footprint_covers_all_users" in row and not row["own_footprint_covers_all_users"]:
            per_cap_moves[(fam, kind, cap)]["anchor_profiles_not_covered"] += 1
for key in sorted(per_cap_moves):
    print(key, dict(per_cap_moves[key]))
kept = defaultdict(int)
for a in (d["projection"]["anchors"] if HAS_PROJ else []):
    for lbl, row in a["rows"].items():
        for f in ("kept", "moved", "rescued_from_null", "stranded_users"):
            if f in row:
                fam = "RSS" if lbl.startswith("RSS") else "A0"
                kept[(fam, lbl.split("_")[-1] if lbl.startswith("RSS") else lbl.rsplit("_", 1)[-1], f)] += int(row[f])
        if "own_footprint_covers_all_users" in row and not row["own_footprint_covers_all_users"]:
            kept[("uncovered", lbl.startswith("RSS"), "count")] += 1
print(dict(kept))
print()
print("## per seed a0: seed, EE, EE projected, EE own, served, att, active, nulls")
seeds = sorted({int(k.split("_")[2]) for k in PP if k.startswith("A0_SEED_")})
for s in seeds:
    a, b, c = PP[f"A0_SEED_{s}"], PP[f"A0_SEED_{s}_PROJECTED"], PP[f"A0_SEED_{s}_OWN_FOOTPRINT"]
    print(s, f"{a['ee_mbit_per_j']:.4f}", f"{b['ee_mbit_per_j']:.4f}", f"{c['ee_mbit_per_j']:.4f}",
          a["served_phy"], b["served_phy"], c["served_phy"], a["rate_target_attained"], b["rate_target_attained"],
          c["rate_target_attained"], f"{a['active_beams_mapping_mean']:.2f}", f"{b['active_beams_mapping_mean']:.2f}",
          a["null_users"], c["null_users"])
print()
print("## learned arm")
la = d["learned_arm"]
if la: print({k: v for k, v in la.items() if k not in ("checkpoints", "development_shards", "shortlist_audit")})
if la: print("shortlist", {(r["corpus_actions_per_user_min"], r["corpus_actions_per_user_max"]) for r in la["shortlist_audit"]})
print()
print("## beams per satellite (parsed from configuration_id): label -> mean over anchors of max beams on one satellite; anchors with any satellite > 3 beams")


def per_sat(cfg_id):
    beams = set()
    for tok in cfg_id.removeprefix("CFG:").split(";"):
        parts = tok.split(":")
        if len(parts) == 3:
            beams.add((int(parts[1]), int(parts[2])))
    counts = defaultdict(int)
    for norad, _ in beams:
        counts[norad] += 1
    return max(counts.values(), default=0), len(counts)


for lbl in ["PARITY_RSS_MAX", "PARITY_CROWDED_MIN_COVER", "UNCAPPED_NATURAL", "UNCAPPED_BEST_KNOWN"] + [
        f"CAP_{c:03d}" for c in caps] + ["PERSAT_3__A1_coverage_first", "PERSAT_3__A2_max_nominal_gain"]:
    vals = [per_sat(a["endpoints"][lbl]["configuration_id"]) for a in anchors if lbl in a["endpoints"]]
    if not vals:
        continue
    print(f"{lbl}: mean max-beams-per-sat {sum(v[0] for v in vals)/len(vals):.2f}, "
          f"range {min(v[0] for v in vals)}-{max(v[0] for v in vals)}, anchors >3: {sum(v[0] > 3 for v in vals)}/{len(vals)}, "
          f"active sats mean {sum(v[1] for v in vals)/len(vals):.2f}")
for a0lbl in ("A0_SEED_", ):
    vals = []
    for a in (d["projection"]["anchors"] if HAS_PROJ else []):
        for lbl, row in a["rows"].items():
            if lbl.startswith("A0_SEED_") and lbl.count("_") == 2:
                vals.append(per_sat(row["configuration_id"]))
    if vals:
        print(f"a0 raw (all seeds x anchors): mean max-beams-per-sat {sum(v[0] for v in vals)/len(vals):.2f}, "
              f"range {min(v[0] for v in vals)}-{max(v[0] for v in vals)}, profiles >3: {sum(v[0] > 3 for v in vals)}/{len(vals)}")
