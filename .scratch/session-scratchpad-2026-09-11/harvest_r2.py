"""Round-2 harvest: BASELINE_EQ16 and SHARED_BOOTSTRAP training logs + frozen eps 0-499."""
import json
import math
import sys

import numpy as np

SP = sys.argv[1]
W = np.array([0.5, 0.3, 0.2])
FROZEN = "/home/u24/papers/mcrl-leo-handover/artifacts/training-2026-08-25-rerun01/main/episode-logs.json"
arms = {
    "BASELINE_EQ16": json.load(open(f"{SP}/r2pilot/BASELINE_EQ16/episode-logs.json")),
    "SHARED_BOOTSTRAP": json.load(open(f"{SP}/r2pilot/SHARED_BOOTSTRAP/episode-logs.json")),
    "FROZEN[0:500] (no D-2)": json.load(open(FROZEN))[:500],
}


def calib(r):
    return np.array([r["r1_mean_calibrated"], r["r2_mean_calibrated"], r["r3_mean_calibrated"]])


print("== counts", {k: len(v) for k, v in arms.items()})
print("\n== stability")
for name, L in arms.items():
    losses = np.array([r["losses"] for r in L], dtype=float)
    finite = all(math.isfinite(x) for r in L for x in (r["r1_mean"], r["r2_mean"], r["r3_mean"], *r["losses"]))
    print(f"{name:24s} finite={finite} loss max={np.array2string(losses.max(0), precision=4)} "
          f"mean0-100={np.array2string(losses[:100].mean(0), precision=4)} "
          f"mean400-500={np.array2string(losses[400:500].mean(0), precision=4)}")

print("\n== training-time windows (epsilon-greedy)")
print(f"{'arm':24s} {'win':>9s} {'eps':>6s} | {'r1c':>7s} {'r2c':>8s} {'r3c':>8s} | {'scal_cal':>8s} | {'ho/us':>6s} {'out/us':>7s}")
for name, L in arms.items():
    for a, b in [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500)]:
        s = L[a:b]
        c = np.array([calib(r) for r in s])
        ho = np.mean([r["total_handovers"] for r in s]) / 1000
        out = np.mean([r.get("outage_user_steps", float("nan")) for r in s]) / 1000
        print(f"{name:24s} {a:>4d}-{b:<4d} {s[-1]['epsilon']:6.3f} | {c[:,0].mean():7.4f} {c[:,1].mean():8.4f} {c[:,2].mean():8.4f} |"
              f" {(c @ W).mean():8.4f} | {ho:6.4f} {out:7.4f}")
    print()

for name in ("BASELINE_EQ16", "SHARED_BOOTSTRAP"):
    L = arms[name]
    tot = sum(r["outage_user_steps"] for r in L)
    print(f"{name}: training outage user-steps total {tot} / {len(L) * 1000} = {tot / (len(L) * 1000):.4%}")

# ep-0 identity check: at epsilon = 1 actions do not depend on Q, so r1 and handovers
# at episode 0 must equal the frozen run's; r2/r3 differ only by the floor.
B, F = arms["BASELINE_EQ16"], arms["FROZEN[0:500] (no D-2)"]
print("\nep0 BASELINE vs FROZEN: r1 equal", B[0]["r1_mean"] == F[0]["r1_mean"],
      "handovers equal", B[0]["total_handovers"] == F[0]["total_handovers"],
      "| r2", B[0]["r2_mean"], F[0]["r2_mean"], "| r3", B[0]["r3_mean"], F[0]["r3_mean"],
      "| outages", B[0]["outage_user_steps"])
first = next((i for i, (b, f) in enumerate(zip(B, F)) if b["r1_mean"] != f["r1_mean"]), None)
print("first episode where BASELINE_EQ16 r1 departs from frozen:", first)
S = arms["SHARED_BOOTSTRAP"]
first2 = next((i for i, (b, s) in enumerate(zip(B, S)) if b["r1_mean"] != s["r1_mean"]), None)
print("first episode where SHARED_BOOTSTRAP r1 departs from BASELINE_EQ16:", first2)
