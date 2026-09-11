"""Harvest the B0 / UNFIXED 500-episode pilots and the frozen run's eps 0-499."""
import json
import math
import sys

import numpy as np

SP = sys.argv[1]
W = np.array([0.5, 0.3, 0.2])
FROZEN = "/home/u24/papers/mcrl-leo-handover/artifacts/training-2026-08-25-rerun01/main/episode-logs.json"


def load(path):
    return json.load(open(path))


arms = {
    "B0": load(f"{SP}/pilot/b0/episode-logs.json"),
    "UNFIXED": load(f"{SP}/pilot/unfixed/episode-logs.json"),
    "FROZEN[0:500]": load(FROZEN)[:500],
}


def calib(r):
    return np.array([r["r1_mean_calibrated"], r["r2_mean_calibrated"], r["r3_mean_calibrated"]])


print("== episode counts:", {k: len(v) for k, v in arms.items()})

# --- stability ---------------------------------------------------------
print("\n== stability (every episode) ==")
for name, L in arms.items():
    losses = np.array([r["losses"] for r in L], dtype=float)
    finite = all(
        all(math.isfinite(x) for x in (r["r1_mean"], r["r2_mean"], r["r3_mean"], *r["losses"]))
        for r in L
    )
    print(f"{name:14s} all finite={finite}  loss max per head={np.array2string(losses.max(0), precision=4)}"
          f"  loss mean ep400-500={np.array2string(losses[400:500].mean(0), precision=4)}"
          f"  loss mean ep0-100={np.array2string(losses[:100].mean(0), precision=4)}")
    # blowup indicator: last-100 mean over first-100 mean, per head
    ratio = losses[400:500].mean(0) / np.maximum(losses[:100].mean(0), 1e-12)
    print(f"{'':14s} last100/first100 loss ratio per head={np.array2string(ratio, precision=2)}"
          f"  max single-episode loss / median per head="
          f"{np.array2string(losses.max(0) / np.median(losses, 0), precision=1)}")

# --- windows -----------------------------------------------------------
print("\n== training-time windows (epsilon-greedy, NOT greedy) ==")
hdr = f"{'arm':14s} {'window':>9s} {'eps_end':>7s} | {'r1c':>7s} {'r2c':>8s} {'r3c':>8s} | {'scalar_cal':>10s} | {'ho/user-step':>12s} | losses"
print(hdr)
for name, L in arms.items():
    for a, b in [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500)]:
        s = L[a:b]
        c = np.array([calib(r) for r in s])
        sc = c @ W
        ho = np.mean([r["total_handovers"] for r in s]) / 1000.0
        loss = np.array([r["losses"] for r in s]).mean(0)
        print(f"{name:14s} {a:>4d}-{b:<4d} {s[-1]['epsilon']:7.4f} | {c[:,0].mean():7.4f} {c[:,1].mean():8.4f} {c[:,2].mean():8.4f} |"
              f" {sc.mean():10.4f} | {ho:12.4f} | {np.array2string(loss, precision=4)}")
    print()

# --- D-3: what the old headline would have shown -------------------------
print("== D-3: headline curves over eps 400-500 ==")
for name, L in arms.items():
    s = L[400:500]
    if "scalar_reward_calibrated" in s[0]:
        cal = np.mean([r["scalar_reward_calibrated"] for r in s])
        unc = np.mean([r["scalar_reward_uncalibrated_deprecated"] for r in s])
    else:
        cal = np.mean([calib(r) @ W for r in s])
        unc = np.mean([r["scalar_reward"] for r in s])
    r1half = np.mean([0.5 * r["r1_mean"] for r in s])
    print(f"{name:14s} calibrated={cal:.4f}  uncalibrated(deprecated)={unc:.6e}  0.5*r1_raw={r1half:.6e}"
          f"  (unc-0.5*r1)/unc={(unc - r1half) / unc:.2e}")

# --- UNFIXED vs FROZEN reproduction -------------------------------------
print("\n== UNFIXED vs FROZEN episode logs: reproduction check ==")
U, F = arms["UNFIXED"], arms["FROZEN[0:500]"]
keys = ["r1_mean", "r2_mean", "r3_mean", "total_handovers", "replay_size", "epsilon"]
first_exact = None
first_tol = None
for i, (u, f) in enumerate(zip(U, F)):
    if first_exact is None and any(u[k] != f[k] for k in keys):
        first_exact = i
    if first_tol is None and any(
        not math.isclose(float(u[k]), float(f[k]), rel_tol=1e-6, abs_tol=1e-9) for k in keys
    ):
        first_tol = i
print(f"first episode with any EXACT difference on {keys}: {first_exact}")
print(f"first episode differing beyond rel 1e-6: {first_tol}")
if first_exact is not None:
    i = first_exact
    print("   at that episode:", {k: (U[i][k], F[i][k]) for k in keys if U[i][k] != F[i][k]})
w = slice(400, 500)
for k in ["r1_mean_calibrated", "r2_mean_calibrated", "r3_mean_calibrated"]:
    uu = np.mean([r[k] for r in U[w]]); ff = np.mean([r[k] for r in F[w]])
    print(f"   eps400-500 {k}: UNFIXED {uu:.4f} vs FROZEN {ff:.4f}  diff {uu-ff:+.4f}")
