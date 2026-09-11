#!/usr/bin/env python3
"""B2-REPR: tau selection on VAL only, by the criterion declared in PROGRESS.md D4.

min mean teacher-advantage regret at each tau's VAL-selected epoch; tie -> max VAL top-1 -> smallest tau.
Written BEFORE any closed-loop run.  Usage: b2_select_tau.py [--noctx]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_common as B  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--noctx", action="store_true")
    a = ap.parse_args()
    sfx = "-noctx" if a.noctx else ""
    rows = []
    for p in sorted((B.WS / "results").glob(f"CLONE-SOFT-tau*{sfx}.json")):
        if (not a.noctx) and "-noctx" in p.name:
            continue
        if "-e" in p.stem.split("tau")[-1]:
            continue
        r = json.loads(p.read_text())
        v = r["val_at_best"]
        rows.append({"tau": r["tau"], "name": r["name"], "epoch": r["best_epoch"],
                     "val_regret_mean": v["regret_mean"], "val_top1": v["top1"],
                     "val_top3": v["top3"], "val_disallowed_pick_frac": v["disallowed_pick_frac"],
                     "test_top1": r["test"]["top1"], "test_regret_mean": r["test"]["regret_mean"]})
    rows.sort(key=lambda d: (d["val_regret_mean"], -d["val_top1"], d["tau"]))
    sel = rows[0]
    out = {"criterion": "min VAL mean teacher-advantage regret; tie -> max VAL top-1 -> smallest tau",
           "grid": sorted(d["tau"] for d in rows), "rows": rows, "selected": sel, "noctx": bool(a.noctx)}
    B.write_json(B.WS / "results" / f"TAU-SELECTION{sfx}.json", out)
    for d in rows:
        print(f"tau={d['tau']:<6g} epoch={d['epoch']:<4d} VAL regret={d['val_regret_mean']:.6f} "
              f"top1={d['val_top1']:.4f} top3={d['val_top3']:.4f}", flush=True)
    print(f"SELECTED tau={sel['tau']:g} ({sel['name']})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
