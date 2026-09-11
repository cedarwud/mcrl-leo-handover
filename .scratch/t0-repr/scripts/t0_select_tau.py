#!/usr/bin/env python3
"""T0-REPR step 3b -- choose tau for the soft clone on the VAL split only (declared rule):
min VAL mean T0-score regret at each tau's selected epoch; tie -> max VAL top-1 -> smaller tau.
TEST and closed-loop numbers are not read.  Writes results/TAU-SELECTION.json (idempotent)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tree" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import t0_common as T  # noqa: E402

TAUS = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)


def main() -> int:
    out = T.WS / "results" / "TAU-SELECTION.json"
    if out.exists():
        print(out.read_text())
        return 0
    rows = []
    for tau in TAUS:
        r = json.loads((T.WS / "results" / f"CLONE-SOFT-tau{tau:g}.json").read_text())
        v = r["val_at_best"]
        rows.append({"tau": tau, "name": r["name"], "best_epoch": r["best_epoch"], "val_regret_mean": v["regret_mean"],
                     "val_top1": v["top1"], "val_top3": v["top3"], "val_ce_bits": v["ce_bits_mean"],
                     "model_sha256": r["model_sha256"]})
    best = min(rows, key=lambda x: (x["val_regret_mean"], -x["val_top1"], x["tau"]))
    payload = {"rule": "min VAL mean T0-score regret; tie -> max VAL top-1 -> smaller tau", "grid": rows,
               "selected_tau": best["tau"], "selected_name": best["name"], "code": T.code_ident()}
    T.write_json(out, payload)
    for x in rows:
        print(f"tau={x['tau']:<5g} epoch={x['best_epoch']:3d} VAL regret={x['val_regret_mean']:.6f} "
              f"top1={x['val_top1']:.4f} top3={x['val_top3']:.4f}")
    print(f"SELECTED tau={best['tau']:g} ({best['name']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
