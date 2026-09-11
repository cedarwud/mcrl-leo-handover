"""Audit of the declared JSRL coverage measure: WHICH observation block carries
the novelty?  Reads the state dump written by `jsrl.py 24 <npz>`; no rollout.

Blocks (state_encoding.py: concatenate([access, snr, theta, loads])):
  access  x_u(t-1) one-hot in the current candidate ordering   -- the incumbent
  snr     per-candidate SINR, previous-step interference       -- partly endogenous
  theta   per-candidate off-axis angle                         -- geometry
  loads   N_u(t-1), previous step's ungated demand per beam    -- endogenous
"""
import sys

import numpy as np

d = np.load(sys.argv[1])
base, handed = d["base"].astype(np.float64), d["handed"].astype(np.float64)
T = base.shape[0]
allb = base.reshape(-1, base.shape[-1])
mu, sd = allb.mean(0), allb.std(0)
sd[sd < 1e-12] = 1.0
BLK = {"access": slice(0, 28), "snr": slice(28, 56),
       "theta": slice(56, 84), "loads": slice(84, 112)}


def d2mat(q, p):
    return np.maximum((q ** 2).sum(1)[:, None] + (p ** 2).sum(1)[None, :]
                      - 2.0 * q @ p.T, 0.0)


print("# (1) declared measure reproduced from the dump (must match jsrl.out)")
print(f"# {'h':>3s} {'R(h)':>8s} {'out95':>8s}")
for h in range(T):
    P = (base[h] - mu) / sd
    Dpp = d2mat(P, P); np.fill_diagonal(Dpp, np.inf)
    loo = np.sqrt(Dpp.min(1)); thr = np.percentile(loo, 95)
    dd = loo if h == 0 else np.sqrt(d2mat((handed[h - 1] - mu) / sd, P).min(1))
    print(f"  {h:>3d} {dd.mean() / loo.mean():8.4f} {(dd > thr).mean():8.4f}")

print("\n# (2) share of squared full-space 1-NN distance carried by each block")
print(f"# {'h':>3s} " + " ".join(f"{b:>8s}" for b in BLK))
for h in range(1, T):
    P = (base[h] - mu) / sd
    Q = (handed[h - 1] - mu) / sd
    j = d2mat(Q, P).argmin(1)
    diff2 = (Q - P[j]) ** 2
    tot = diff2.sum(1)
    tot[tot == 0] = np.nan
    sh = [np.nanmean(diff2[:, s].sum(1) / tot) for s in BLK.values()]
    print(f"  {h:>3d} " + " ".join(f"{x:8.4f}" for x in sh))

print("\n# (3) block-restricted novelty ratio R_b(h) and out95_b(h)")
print(f"# {'h':>3s} " + " ".join(f"{b + ' R':>9s} {b + ' o95':>10s}" for b in BLK))
for h in range(1, T):
    row = []
    for s in BLK.values():
        P = ((base[h] - mu) / sd)[:, s]
        Q = ((handed[h - 1] - mu) / sd)[:, s]
        Dpp = d2mat(P, P); np.fill_diagonal(Dpp, np.inf)
        loo = np.sqrt(Dpp.min(1))
        thr = np.percentile(loo, 95)
        dd = np.sqrt(d2mat(Q, P).min(1))
        m = loo.mean()
        row.append(f"{(dd.mean() / m if m > 0 else float('nan')):9.4f} "
                   f"{(dd > thr).mean():10.4f}")
    print(f"  {h:>3d} " + " ".join(row))

print("\n# (4) paired: fraction of (episode,user) rows whose block is EXACTLY "
      "equal to the h=0 rollout's row at the same step index")
print(f"# {'h':>3s} " + " ".join(f"{b:>8s}" for b in BLK) + f" {'whole':>8s}")
for h in range(1, T):
    A, Bm = handed[h - 1], base[h]
    eq = [np.all(A[:, s] == Bm[:, s], axis=1).mean() for s in BLK.values()]
    print(f"  {h:>3d} " + " ".join(f"{x:8.4f}" for x in eq)
          + f" {np.all(A == Bm, axis=1).mean():8.4f}")

# (5) same-incumbent subset: is there novelty when the incumbent slot is the same?
print("\n# (5) 1-NN novelty restricted to rows whose access block is IDENTICAL "
      "to the h=0 row (same incumbent slot) -- does novelty survive?")
print(f"# {'h':>3s} {'n_same':>7s} {'R_same':>8s} {'o95_same':>9s} "
      f"{'n_diff':>7s} {'R_diff':>8s} {'o95_diff':>9s}")
for h in range(1, T):
    P = (base[h] - mu) / sd
    Dpp = d2mat(P, P); np.fill_diagonal(Dpp, np.inf)
    loo = np.sqrt(Dpp.min(1)); thr = np.percentile(loo, 95); m = loo.mean()
    Q = (handed[h - 1] - mu) / sd
    dd = np.sqrt(d2mat(Q, P).min(1))
    same = np.all(handed[h - 1][:, :28] == base[h][:, :28], axis=1)
    f = lambda k: (f"{k.sum():7d} {dd[k].mean() / m:8.4f} {(dd[k] > thr).mean():9.4f}"
                   if k.any() else f"{0:7d} {'n/a':>8s} {'n/a':>9s}")
    print(f"  {h:>3d} {f(same)} {f(~same)}")
