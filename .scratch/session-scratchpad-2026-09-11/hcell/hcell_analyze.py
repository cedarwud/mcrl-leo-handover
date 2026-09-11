#!/usr/bin/env python3
"""HCELL analysis: derived arithmetic on the verified receipts (no physics).

Writes one file per (setting, configuration) under .scratch/hcell/results/
and a single analysis JSON used by the report.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hcell_common as hc  # noqa: E402

MAIN = hc.SCRATCH / "hcell-main-receipt.json"
HSEARCH = hc.SCRATCH / "hcell-hsearch-receipt.json"
C2 = hc.SCRATCH / "hcell-c2-receipt.json"
KAT = hc.SCRATCH / "hcell-kat-receipt.json"
RESULTS = hc.SCRATCH / "results"
OUT = hc.SCRATCH / "hcell-analysis.json"
FOCUS = ("NEAREST_ELIGIBLE", "RSS_MAX", "MYOPIC_GREEDY", "FIRST_IMPROVEMENT_FP", "CROWDED")
ETA_REF_HEX = "0x1.4df5240780e6fp+23"
KAPPA_HEX = "0x1.97459ee759205p+29"


def load(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "COMPLETE":
        raise RuntimeError(f"{path} not complete")
    if payload["receipt_sha256"] != hc.canonical_digest(payload):
        raise RuntimeError(f"{path} digest failed")
    return payload


def ordering(values: dict) -> list:
    return sorted(values, key=lambda k: -values[k])


def main() -> int:
    main_r = load(MAIN)
    pooled = main_r["pooled"]
    arms = list(pooled)
    eta = float.fromhex(ETA_REF_HEX)
    kappa = float.fromhex(KAPPA_HEX)
    analysis = {"eta_ref_bits_per_j": eta, "kappa_bits": kappa}

    settings = {}
    for arm in arms:
        p = pooled[arm]
        n = p["events"]["h_events"]
        rows = {"a0": dict(p["a0"]), "aH": dict(p["aH"])}
        for e in hc.E_HO_VALUES_J:
            for base in ("a0", "aH"):
                src = p[base]
                rows[f"{base}+EHO{e:g}J"] = {
                    **src,
                    "joules_physics": src["joules"],
                    "joules_eho_added": n * e,
                    "joules": src["joules"] + n * e,
                    "ee_mbit_per_j": src["bits"] / (src["joules"] + n * e) / 1e6,
                    "accounting": "post-hoc ledger term, not physics",
                }
        for setting, row in rows.items():
            row = {**row, "configuration": arm, "setting": setting, "h_events": n,
                   "events": p["events"],
                   "reference": "same configuration under a0 (primary, H off)",
                   "information_class": "development, learner-free, 12 frozen anchors, realised full-48 endpoint",
                   "estimand": "pooled EE of the configuration at the anchor step, open loop",
                   "numerator": "full-buffer decoded information bits (H: minus blackout bits) / joules (EHO: + N x E_HO)"}
            settings.setdefault(setting, {})[arm] = row
            path = RESULTS / setting / f"{arm}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(row, indent=1, sort_keys=True) + "\n")

    # --- Q2: size of H ---
    q2 = {}
    for arm in arms:
        a0, aH = settings["a0"][arm], settings["aH"][arm]
        n = pooled[arm]["events"]["h_events"]
        removed = pooled[arm]["h_removed_bits"]
        d_ee = aH["ee_mbit_per_j"] - a0["ee_mbit_per_j"]
        q2[arm] = {
            "ee_a0": a0["ee_mbit_per_j"], "ee_aH": aH["ee_mbit_per_j"],
            "d_ee_mbit_per_j": d_ee, "d_ee_rel": aH["ee_mbit_per_j"] / a0["ee_mbit_per_j"] - 1.0,
            "bits_a0": a0["bits"], "bits_aH": aH["bits"], "joules": a0["joules"],
            "served": a0["served_count"], "served_aH": aH["served_count"],
            "attained_a0": a0["rate_target_attained_count"], "attained_aH": aH["rate_target_attained_count"],
            "users": a0["user_count"],
            "events": pooled[arm]["events"],
            "h_removed_bits": removed,
            "h_removed_bits_by_kind": pooled[arm]["h_removed_bits_by_kind"],
            "removed_bits_per_event": None if n == 0 else removed / n,
            "d_ee_per_event_bit_per_j": None if n == 0 else d_ee * 1e6 / n,
            "removed_fraction_of_bits": removed / a0["bits"],
        }
        bk = pooled[arm]["h_removed_bits_by_kind"]
        ev = pooled[arm]["events"]
        q2[arm]["removed_bits_per_beam_event"] = (
            None if ev["beam_change"] + ev["cell_rekey"] == 0
            else bk["same_satellite_beam_change"] / (ev["beam_change"] + ev["cell_rekey"]))
        q2[arm]["removed_bits_per_satellite_event"] = (
            None if ev["satellite_change"] == 0 else bk["satellite_change"] / ev["satellite_change"])
    analysis["q2"] = q2
    for setting in settings:
        analysis.setdefault("orderings", {})[setting] = ordering(
            {a: settings[setting][a]["ee_mbit_per_j"] for a in arms})
        analysis.setdefault("orderings_focus", {})[setting] = ordering(
            {a: settings[setting][a]["ee_mbit_per_j"] for a in FOCUS})
    analysis["ordering_changes_vs_a0"] = {
        s: analysis["orderings"][s] != analysis["orderings"]["a0"] for s in settings}
    analysis["focus_ordering_changes_vs_a0"] = {
        s: analysis["orderings_focus"][s] != analysis["orderings_focus"]["a0"] for s in settings}
    all_events = sum(pooled[a]["events"]["h_events"] for a in FOCUS)
    all_removed = math.fsum(pooled[a]["h_removed_bits"] for a in FOCUS)
    analysis["focus_mean_removed_bits_per_event"] = all_removed / all_events if all_events else None

    # smallest adjacent gap in a0 ordering (focus) vs largest H change
    order = analysis["orderings_focus"]["a0"]
    gaps = [(order[i], order[i + 1], q2[order[i]]["ee_a0"] - q2[order[i + 1]]["ee_a0"])
            for i in range(len(order) - 1)]
    analysis["focus_a0_adjacent_gaps"] = gaps
    analysis["focus_max_abs_d_ee"] = max(abs(q2[a]["d_ee_mbit_per_j"]) for a in FOCUS)

    # --- Q3: persistence lever ---
    def pair(a, b):
        A, B = pooled[a], pooled[b]
        nA, nB = A["events"]["h_events"], B["events"]["h_events"]
        gap0 = A["a0"]["ee_mbit_per_j"] - B["a0"]["ee_mbit_per_j"]
        gapH = A["aH"]["ee_mbit_per_j"] - B["aH"]["ee_mbit_per_j"]
        # H scale s at which EE ties, removal linear in s (valid only while blackouts stay
        # inside the first 0.640-s subinterval, i.e. s < 4.5 for 142 ms)
        bA, jA, xA = A["a0"]["bits"], A["a0"]["joules"], A["h_removed_bits"]
        bB, jB, xB = B["a0"]["bits"], B["a0"]["joules"], B["h_removed_bits"]
        denom = xA * jB - xB * jA
        s_star = None if denom == 0 else (bA * jB - bB * jA) / denom
        # E_HO at which EE ties: bA/(jA+nA E) = bB/(jB+nB E)
        denom_e = bA * nB - bB * nA
        e_star = None if denom_e == 0 else (bB * jA - bA * jB) / denom_e
        out = {"a": a, "b": b, "events_a": nA, "events_b": nB,
               "ee_gap_a0": gap0, "ee_gap_aH": gapH, "gap_change": gapH - gap0,
               "h_cost_a": A["a0"]["ee_mbit_per_j"] - A["aH"]["ee_mbit_per_j"],
               "h_cost_b": B["a0"]["ee_mbit_per_j"] - B["aH"]["ee_mbit_per_j"],
               "h_scale_for_tie": s_star,
               "e_ho_for_tie_j": e_star}
        for e in hc.E_HO_VALUES_J:
            out[f"ee_gap_a0+EHO{e:g}J"] = (settings[f"a0+EHO{e:g}J"][a]["ee_mbit_per_j"]
                                           - settings[f"a0+EHO{e:g}J"][b]["ee_mbit_per_j"])
            out[f"ee_gap_aH+EHO{e:g}J"] = (settings[f"aH+EHO{e:g}J"][a]["ee_mbit_per_j"]
                                           - settings[f"aH+EHO{e:g}J"][b]["ee_mbit_per_j"])
        return out

    analysis["q3"] = [pair("RSS_MAX", "STAY_ELSE_RSS"), pair("RSS_MAX", "NEAREST_ELIGIBLE"),
                      pair("CROWDED", "STAY_ELSE_RSS"), pair("FIRST_IMPROVEMENT_FP", "STAY_ELSE_RSS"),
                      pair("MYOPIC_GREEDY", "STAY_ELSE_RSS"), pair("CROWDED", "RSS_MAX")]
    # per-anchor STAY vs RSS
    per_anchor = []
    for a in main_r["anchors"]:
        r, s = a["arms"]["RSS_MAX"], a["arms"]["STAY_ELSE_RSS"]
        per_anchor.append({
            "anchor": a["global_anchor_index"], "step": a["step_index"], "carrier": a["carrier"],
            "rss_events": r["events"]["h_events"], "stay_events": s["events"]["h_events"],
            "rss_ee_a0": r["a0"]["bits"] / r["a0"]["joules"] / 1e6,
            "stay_ee_a0": s["a0"]["bits"] / s["a0"]["joules"] / 1e6,
            "rss_ee_aH": r["aH"]["bits"] / r["aH"]["joules"] / 1e6,
            "stay_ee_aH": s["aH"]["bits"] / s["aH"]["joules"] / 1e6,
            "stay_kept": s.get("users_kept_on_incumbent"),
            "same_config": r["configuration_id"] == s["configuration_id"]})
    analysis["q3_per_anchor"] = per_anchor

    # --- price comparisons (derived) ---
    beam_bits = [q2[a]["removed_bits_per_beam_event"] for a in FOCUS if q2[a]["removed_bits_per_beam_event"]]
    sat_bits = [q2[a]["removed_bits_per_satellite_event"] for a in FOCUS if q2[a]["removed_bits_per_satellite_event"]]
    analysis["prices"] = {
        "phi_beam_change_bits": 0.5 * kappa, "phi_satellite_change_bits": 1.0 * kappa,
        "h_beam_event_bits_range": [min(beam_bits), max(beam_bits)] if beam_bits else None,
        "h_satellite_event_bits_range": [min(sat_bits), max(sat_bits)] if sat_bits else None,
        "e_ho_bits_at_eta_ref": {f"{e:g}J": e * eta for e in hc.E_HO_VALUES_J},
    }

    # --- E_HO table ---
    eho = {}
    for arm in arms:
        eho[arm] = {s: {"ee": settings[s][arm]["ee_mbit_per_j"],
                        "rel_vs_a0": settings[s][arm]["ee_mbit_per_j"] / settings["a0"][arm]["ee_mbit_per_j"] - 1.0,
                        "added_fraction": (settings[s][arm].get("joules_eho_added", 0.0)
                                           / settings["a0"][arm]["joules"])}
                    for s in settings}
    analysis["eho"] = eho

    # --- H-reselected searches ---
    if HSEARCH.exists():
        hs = load(HSEARCH)
        analysis["hsearch"] = {"pooled": hs["pooled"],
                               "scalar_evaluate_calls": hs["scalar_evaluate_calls"],
                               "peak_rss_bytes": hs["runtime"]["peak_rss_bytes"]}
    if C2.exists():
        c2 = load(C2)
        P = c2["pooled"]
        analysis["c2"] = {
            "pooled": P,
            "full_vs_c1_a0_endpoint_a0_labels": P["FULL"]["a0"]["ee_mbit_per_j"] / P["C1_ONLY"]["a0"]["ee_mbit_per_j"] - 1,
            "full_vs_c1_aH_endpoint_a0_labels": P["FULL"]["aH"]["ee_mbit_per_j"] / P["C1_ONLY"]["aH"]["ee_mbit_per_j"] - 1,
            "fullh_vs_c1h_aH_endpoint_h_labels": P["FULLH"]["aH"]["ee_mbit_per_j"] / P["C1H_ONLY"]["aH"]["ee_mbit_per_j"] - 1,
            "anchors_full_differs": sum(a["full_differs_from_c1_only"] for a in c2["anchors"]),
            "anchors_fullh_differs": sum(a["fullh_differs_from_c1h_only"] for a in c2["anchors"]),
            "anchors_c1h_changes_c1": sum(a["c1h_changes_c1_pick"] for a in c2["anchors"]),
            "anchors_fullh_changes_full": sum(a["fullh_changes_full_pick"] for a in c2["anchors"]),
            "parity_ids": sum(all(p["configuration_id_match"] for p in a["parity_vs_c2target"].values())
                              for a in c2["anchors"]),
            "parity_max_abs_bits_delta": max(abs(p["bits_delta"]) for a in c2["anchors"]
                                             for p in a["parity_vs_c2target"].values()),
            "core_exact": sum(a["c1_core_exact_fraction_matches"] for a in c2["anchors"]),
            "core_rows": sum(a["relabel_rows"] for a in c2["anchors"]),
            "core_max_abs_diff": max((a["c1_core_max_abs_diff_bits"] or 0.0) for a in c2["anchors"]),
            "scalar_evaluate_calls": c2["scalar_evaluate_calls"],
            "peak_rss_bytes": c2["runtime"]["peak_rss_bytes"],
        }
    if KAT.exists():
        analysis["kat"] = load(KAT)
    analysis["main_meta"] = {k: main_r[k] for k in ("scalar_evaluate_calls", "parity_all_ok", "wall_seconds",
                                                    "runtime", "world_tape", "sources")}
    OUT.write_text(json.dumps(analysis, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({"q2": {a: [round(q2[a]["ee_a0"], 6), round(q2[a]["ee_aH"], 6),
                                 f"{q2[a]['d_ee_rel']:.4%}", q2[a]["events"]["h_events"]] for a in arms},
                      "ordering_changes": analysis["ordering_changes_vs_a0"],
                      "q3": analysis["q3"][0]}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
