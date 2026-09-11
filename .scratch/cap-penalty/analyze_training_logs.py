"""CAPPENALTY: training-time readouts for all four cells from their episode logs.

srank_delta per head (PENALTYARM's estimator, logged per episode by the
trainer's read-only diagnostic), in 100-episode windows; the penalty's own
raw value; calibrated head means; handovers per episode; and, for the CAP3
arms, the trainer's training-time G-3 samples (greedy, step 0 and last step).
Pure JSON reading -- no torch, no RNG.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

CELLS = {
    "OFF": Path("/home/sat/mcrl-v025-penalty-arm-ws/runs/OFF/episode-logs.json"),
    "PENALTY": Path("/home/sat/mcrl-v025-penalty-arm-ws/runs/PENALTY/episode-logs.json"),
    "CAP3_OFF": Path("/home/sat/mcrl-v025-cap-penalty-ws/runs/CAP3_OFF/episode-logs.json"),
    "CAP3_PENALTY": Path("/home/sat/mcrl-v025-cap-penalty-ws/runs/CAP3_PENALTY/episode-logs.json"),
}
WINDOWS = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500)]


def main() -> int:
    out: dict[str, dict] = {}
    for name, path in CELLS.items():
        rows = json.loads(path.read_text())
        n = len(rows)
        srank = np.array([r["penalty"]["srank_diagnostic_mean"] for r in rows])
        pen = np.array([r["penalty"]["penalty_raw_mean"] for r in rows])
        cal = np.array([[r["r1_mean_calibrated"], r["r2_mean_calibrated"],
                         r["r3_mean_calibrated"]] for r in rows])
        ho = np.array([r["total_handovers"] for r in rows], dtype=float)
        cell = {"episodes_logged": n, "windows": {}}
        for lo, hi in WINDOWS:
            if hi > n:
                continue
            key = f"ep{lo + 1}-{hi}"
            w = {
                "srank_delta_per_head": srank[lo:hi].mean(axis=0).tolist(),
                "srank_delta_min_episode_per_head": srank[lo:hi].min(axis=0).tolist(),
                "penalty_raw_per_head": pen[lo:hi].mean(axis=0).tolist(),
                "calibrated_r1_r2_r3": cal[lo:hi].mean(axis=0).tolist(),
                "handovers_per_episode": float(ho[lo:hi].mean()),
            }
            if "g3_train_last" in rows[0]:
                for point in ("g3_train_first", "g3_train_last"):
                    samples = [r[point] for r in rows[lo:hi] if r.get(point)]
                    if samples:
                        w[point] = {
                            k: float(np.mean([s[k] for s in samples]))
                            for k in ("active_beam_count", "argmax_agreement",
                                      "q_margin", "q_entropy",
                                      "active_beam_count_executed",
                                      "argmax_agreement_executed")
                        }
            cell["windows"][key] = w
        cell["srank_delta_episode1_per_head"] = srank[0].tolist()
        cell["srank_delta_global_min_per_head"] = srank.min(axis=0).tolist()
        out[name] = cell
        print(f"== {name} ({n} episodes)")
        for key, w in cell["windows"].items():
            s = w["srank_delta_per_head"]
            print(f"  {key:10s} srank=({s[0]:.2f}, {s[1]:.2f}, {s[2]:.2f}) "
                  f"min=({', '.join(f'{x:.1f}' for x in w['srank_delta_min_episode_per_head'])}) "
                  f"pen_raw=({', '.join(f'{x:.2f}' for x in w['penalty_raw_per_head'])}) "
                  f"cal=({', '.join(f'{x:+.4f}' for x in w['calibrated_r1_r2_r3'])}) "
                  f"ho/ep={w['handovers_per_episode']:.1f}"
                  + (f" G3last slots={w['g3_train_last']['active_beam_count']:.2f} "
                     f"agree={w['g3_train_last']['argmax_agreement']:.3f} "
                     f"margin={w['g3_train_last']['q_margin']:.4f} "
                     f"ent={w['g3_train_last']['q_entropy']:.4f}"
                     if "g3_train_last" in w else ""))
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
