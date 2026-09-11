#!/usr/bin/env python3
"""Re-price COORDVALUE's verified candidate rows: which of price / Phi / horizon
produces its F-vs-EE sign disagreements?  Read-only over sealed rows; no
evaluator is constructed, nothing physical is recomputed.  Output is written
only to the ETAFIX workspace."""

from __future__ import annotations

import hashlib
import json
import os
import resource
from pathlib import Path

ROWS = Path("/home/sat/mcrl-v025-coord-ws/.scratch/coordvalue/candidates.jsonl")
ROWS_SHA = "79546806b891b73fefe56ae708f9c61972062fefb2eb2787ad7f931c7955a1a2"
RECEIPT = Path("/home/sat/mcrl-v025-coord-ws/.scratch/coordvalue/coordvalue-receipt.json")
OUT = Path("/home/sat/mcrl-v025-etafix-ws/.scratch/etafix/coordvalue-repricing.json")
ETA_REF = 14235186615308645000000 / 1300834130903823
ETA_STAR = 5512041955422222500000000 / 132432373501572239


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 15
    if sha(ROWS) != ROWS_SHA:
        raise RuntimeError("COORDVALUE candidate log changed")
    rec = json.loads(RECEIPT.read_text())
    starts = {}
    for a in rec["anchors"]:
        for name, s in a["starts"].items():
            st = s["start"]
            starts[(int(a["global_anchor_index"]), name)] = {
                "b48": float(st["bits"]), "e48": float(st["joules"]),
                "b0": float(st["selection_boundary0_bits"]), "e0": float(st["selection_boundary0_joules"]),
                "phi": float(st["phi_cost_bits"]["float"]), "f": float(st["f"]["float"]),
            }
    rows = []
    stored = {"ee_up_f_down": 0, "f_up_ee_down": 0}
    with ROWS.open() as f:
        for line in f:
            r = json.loads(line)
            if not r["guarded"]:
                continue
            s = starts[(int(r["anchor_index"]), r["start"])]
            stored["ee_up_f_down"] += bool(r["ee_improves_f_decreases"])
            stored["f_up_ee_down"] += bool(r["f_improves_ee_decreases"])
            rows.append((r["start"], s,
                         float(r["bits"]), float(r["joules"]),
                         float(r["selection_boundary0_bits"]), float(r["selection_boundary0_joules"]),
                         float(r["phi_cost_bits"]["float"]), float(r["delta_ee_mbit_per_j"]),
                         float(r["delta_f"]["float"])))

    def deltas(row, horizon, with_phi):
        start, s, b48, e48, b0, e0, phi, dee, _ = row
        if horizon == "full48":
            dnum, de = b48 - s["b48"], e48 - s["e48"]
        else:
            dnum, de = b0 - s["b0"], e0 - s["e0"]
        if with_phi:
            dnum -= (phi - s["phi"])
        return dnum, de, dee

    def count(horizon, with_phi, eta_rule):
        out = {"RSS_MAX": [0, 0], "CROWDED": [0, 0]}
        for row in rows:
            start, s = row[0], row[1]
            dnum, de, dee = deltas(row, horizon, with_phi)
            if eta_rule == "ref":
                eta = ETA_REF
            elif eta_rule == "star":
                eta = ETA_STAR
            elif eta_rule == "start_own":
                eta = (s["b48"] / s["e48"]) if horizon == "full48" else (s["b0"] / s["e0"])
            else:
                eta = eta_rule
            df = dnum - eta * de
            if dee > 0 and df < 0:
                out[start][0] += 1
            if df > 0 and dee < 0:
                out[start][1] += 1
        tot = [out["RSS_MAX"][0] + out["CROWDED"][0], out["RSS_MAX"][1] + out["CROWDED"][1]]
        return {"by_start": {k: {"ee_up_f_down": v[0], "f_up_ee_down": v[1]} for k, v in out.items()},
                "ee_up_f_down": tot[0], "f_up_ee_down": tot[1], "total_disagreements": tot[0] + tot[1]}

    def best_global_eta(horizon, with_phi):
        """Exact minimum of total disagreements over one global eta >= 0."""
        base = 0
        events = []  # (eta, +1/-1) change in disagreement count as eta increases through it
        for row in rows:
            dnum, de, dee = deltas(row, horizon, with_phi)
            if dee == 0:
                continue
            want_pos = dee > 0

            def disagree(eta):
                df = dnum - eta * de
                return (want_pos and df < 0) or ((not want_pos) and df > 0)
            base += disagree(0.0)
            if de != 0:
                x = dnum / de
                if x > 0:
                    before, after = disagree(x * (1 - 1e-12)), disagree(x * (1 + 1e-12))
                    if before != after:
                        events.append((x, 1 if after else -1))
        events.sort()
        best, best_lo, cur = base, 0.0, base
        best_hi = events[0][0] if events else float("inf")
        for i, (x, d) in enumerate(events):
            cur += d
            nxt = events[i + 1][0] if i + 1 < len(events) else float("inf")
            if cur < best:
                best, best_lo, best_hi = cur, x, nxt
        return {"min_total_disagreements": best,
                "argmin_eta_interval_mbit_per_j": [best_lo / 1e6, best_hi / 1e6 if best_hi != float("inf") else None],
                "disagreements_at_eta_0": base, "guarded_rows": len(rows)}

    variants = {}
    for label, horizon, phi, rule in (
        ("V0_deployed_boundary0_phi_eta_ref", "boundary0", True, "ref"),
        ("V1_boundary0_nophi_eta_ref", "boundary0", False, "ref"),
        ("V2_full48_phi_eta_ref", "full48", True, "ref"),
        ("V3_full48_nophi_eta_ref", "full48", False, "ref"),
        ("V4_full48_nophi_eta_start_own_full48_EE", "full48", False, "start_own"),
        ("V5_boundary0_nophi_eta_start_own_boundary0_EE", "boundary0", False, "start_own"),
        ("V6_full48_nophi_eta_star", "full48", False, "star"),
        ("V7_boundary0_nophi_eta_star", "boundary0", False, "star"),
        ("V8_boundary0_phi_eta_star", "boundary0", True, "star"),
        ("V9_full48_phi_eta_star", "full48", True, "star"),
        ("V10_full48_phi_eta_start_own_full48_EE", "full48", True, "start_own"),
        ("V11_boundary0_phi_eta_start_own_boundary0_EE", "boundary0", True, "start_own"),
    ):
        variants[label] = count(horizon, phi, rule)
        print(label, variants[label]["ee_up_f_down"], variants[label]["f_up_ee_down"], flush=True)
    sweeps = {f"{h}_{'phi' if p else 'nophi'}": best_global_eta(h, p)
              for h in ("boundary0", "full48") for p in (True, False)}
    for k, v in sweeps.items():
        print("sweep", k, v, flush=True)
    # Reproduce COORDVALUE's own F from row fields as an integrity check.
    recon_max_rel = 0.0
    for row in rows[:5000]:
        start, s, b48, e48, b0, e0, phi, dee, dfs = row
        df = (b0 - s["b0"]) - ETA_REF * (e0 - s["e0"]) - (phi - s["phi"])
        recon_max_rel = max(recon_max_rel, abs(df - dfs) / max(1.0, abs(dfs)))
    payload = {
        "schema": "etafix-coordvalue-repricing-v1", "source_rows": str(ROWS), "source_rows_sha256": ROWS_SHA,
        "source_receipt_sha256_field": rec["receipt_sha256"], "guarded_rows": len(rows),
        "coordvalue_stored_flag_counts_guarded": stored,
        "delta_f_reconstruction_max_relative_error_first_5000": recon_max_rel,
        "eta_ref": ETA_REF, "eta_star": ETA_STAR, "variants": variants, "global_eta_sweeps": sweeps,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    }
    OUT.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print("stored", stored, "recon", recon_max_rel, "peak RSS GiB", payload["peak_rss_bytes"] / 2**30, flush=True)


if __name__ == "__main__":
    main()
