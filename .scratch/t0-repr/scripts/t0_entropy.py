#!/usr/bin/env python3
"""T0-REPR step 4c -- T0's conditional action entropy given the student's observation (no training).

(i)  exact decoder: T0's action recomputed from the observation alone, a_hat = masked argmax of
     block_snr / ln2 - 1 * [block_load == 0] (first legal index on ties), vs T0's logged action on every
     collected decision.  Agreement 1.0 => T0 is a deterministic function of (o, mask) on the sample => H = 0.
(ii) plug-in H(a | bin(o, mask)) in bits with bin = identical float32 observation (113 dims) + mask bits
     ("finest"), and bin = every observation dim rounded to 0.05 encoded units + mask ("coarse"); reported with
     the number of bins, the fraction of decisions that share a bin, and the Miller-Madow corrected value.
Writes results/ENTROPY.json.  Usage: t0_entropy.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tree" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import t0_common as T  # noqa: E402

import numpy as np  # noqa: E402


def cond_entropy(keys: np.ndarray, y: np.ndarray) -> dict:
    """keys: (N, B) uint8 row keys; y actions.  Plug-in and Miller-Madow H(y | key) in bits."""
    N = len(y)
    kv = np.ascontiguousarray(keys).view(np.dtype((np.void, keys.shape[1]))).ravel()
    _, inv, cnt = np.unique(kv, return_inverse=True, return_counts=True)
    order = np.lexsort((y, inv))
    inv_s, y_s = inv[order], y[order]
    # counts per (bin, action)
    change = np.ones(N, dtype=bool)
    change[1:] = (inv_s[1:] != inv_s[:-1]) | (y_s[1:] != y_s[:-1])
    starts = np.flatnonzero(change)
    n_ba = np.diff(np.append(starts, N))
    b_of = inv_s[starts]
    n_b = cnt[b_of]
    p = n_ba / n_b
    H_nats = float(-(n_ba / N * np.log(p)).sum())
    K_b = np.bincount(b_of, minlength=len(cnt))
    mm = float((K_b[K_b > 0] - 1).sum() / (2.0 * N))
    shared = cnt[inv] >= 2
    return {"n_decisions": int(N), "n_bins": int(len(cnt)), "frac_decisions_in_shared_bins": float(shared.mean()),
            "n_bins_with_ge2": int((cnt >= 2).sum()), "n_bins_with_ge2_actions": int((K_b >= 2).sum()),
            "H_plugin_bits": float(H_nats / np.log(2.0)) + 0.0, "H_miller_madow_bits": float((H_nats + mm) / np.log(2.0)) + 0.0}


def main() -> int:
    T.boot()
    out = T.WS / "results" / "ENTROPY.json"
    if out.exists():
        print(out.read_text())
        return 0
    parts = [np.load(T.WS / "data" / f"T0-collect-triple{j}.npz") for j in range(3)]
    obs = np.concatenate([p["obs"] for p in parts])
    M = np.concatenate([p["mask"] for p in parts])
    y = np.concatenate([p["act"] for p in parts]).astype(np.int64)
    S = np.concatenate([p["score"] for p in parts])
    keep = M.any(1)
    obs, M, y, S = obs[keep], M[keep], y[keep], S[keep]
    dec = np.where(M, T.decoder_scores_from_obs(obs), -np.inf).argmax(1)
    mism = np.flatnonzero(dec != y)
    gaps = (S[mism, y[mism]] - S[mism, dec[mism]]).tolist() if mism.size else []
    Mb = np.packbits(M, axis=1)
    fine = np.concatenate([obs.view(np.uint8).reshape(len(obs), -1), Mb], axis=1)
    q = np.round(obs.astype(np.float64) / 0.05).astype(np.int32)
    coarse = np.concatenate([q.view(np.uint8).reshape(len(q), -1), Mb], axis=1)
    pa = np.bincount(y, minlength=28) / len(y)
    res = {"n_decisions": int(len(y)), "empty_mask_excluded": int((~keep).sum()),
           "decoder_agreement": float((dec == y).mean()), "decoder_mismatches": int(mism.size),
           "decoder_mismatch_T0_score_gaps": gaps[:50],
           "finest_binning": cond_entropy(fine, y), "coarse_binning_0p05": cond_entropy(coarse, y),
           "H_marginal_action_bits": float(-(pa[pa > 0] * np.log2(pa[pa > 0])).sum()),
           "mean_log2_legal_set_size_bits": float(np.log2(M.sum(1)).mean()),
           "code": T.code_ident()}
    T.write_json(out, res)
    print({k: v for k, v in res.items() if k != "code"}, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
