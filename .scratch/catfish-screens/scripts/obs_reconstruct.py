"""CFSCREEN screen 1, information ceiling: is each source's action an exact function of the
learner's OWN encoded observation (plus the legal mask the learner's argmax also uses)?

Decode the 112-dim float32 encoding back to rule inputs -- snr = expm1(block 2) (encoding is
log1p(snr_linear), state_encoding.py:68-70), loads = block 4 * num_users (100;
state_encoding.py:96-98), incumbent = the 1 in block 1 -- apply each rule, and count how
often the decoded rule reproduces the logged action.  Pure analysis; no rollout, no training.
"""
from pathlib import Path

import numpy as np

RAW = Path(__file__).resolve().parent.parent / "raw"
SRC = ["A0", "A2", "A9", "A12", "B1", "B2"]
MARG = {"A0": 0.0, "A2": 2.0, "A9": 9.0, "A12": 12.0}
lines = []


def rule(tag, snr, load, inc, mask):
    n = len(snr)
    rows = np.arange(n)
    if tag in MARG:
        g = 10.0 * np.log10(np.maximum(snr, 1e-300))
        ok = inc >= 0
        ok[ok] = mask[rows[ok], inc[ok]]
        if MARG[tag] > 0:
            g[rows[ok], inc[ok]] += MARG[tag]
        return np.where(mask, g, -np.inf).argmax(1)
    if tag == "B1":
        allowed = load > 0.5
    else:
        occ = load.copy()
        r = inc >= 0
        occ[rows[r], inc[r]] -= 1.0
        strong = occ > 0.5
        allowed = np.where((strong & mask).any(1)[:, None], strong, load > 0.5)
    allowed = allowed & mask
    allowed[~allowed.any(1)] = mask[~allowed.any(1)]
    return np.where(allowed, snr, -np.inf).argmax(1)


for tag in SRC:
    d = np.load(RAW / f"{tag}.npz")
    obs, mask, act = d["obs"], d["mask"], d["act"]
    snr = np.expm1(obs[:, 28:56].astype(np.float64))
    load = np.rint(obs[:, 84:112].astype(np.float64) * 100.0)
    acc = obs[:, :28]
    inc = np.where((acc > 0.5).any(1), acc.argmax(1), -1)
    g = d["gain"]
    rel = np.abs(snr - g) / np.maximum(np.abs(g), 1e-30)
    assert np.array_equal(inc, d["inc"]), tag
    assert np.array_equal(load, d["load"]), tag
    keep = mask.any(1)
    rec = rule(tag, snr, load, inc, mask)
    agree = float((rec[keep] == act[keep]).mean())
    lines.append(f"{tag:4s} decoded-from-obs rule == logged action: {agree:.5f} "
                 f"({int((rec[keep] != act[keep]).sum())} of {int(keep.sum())} differ); "
                 f"snr decode max rel err {rel[mask].max():.2e}; incumbent and loads decode exact")
print("\n".join(lines))
(RAW / "obs_reconstruct.out").write_text("\n".join(lines) + "\n")
