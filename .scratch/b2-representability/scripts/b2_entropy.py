#!/usr/bin/env python3
"""B2-REPR: the teacher's conditional action entropy given the B2 observation (Amendment 3 §3).

Unlike T0 (an exact function of the student's observation), T_SEQ is defined by counterfactual
evaluations of the JOINT action, so no exact decoder is expected; this script reports what can be
measured on the sample:
  - marginal H(a_T) and the uniform-over-legal entropy (two scales for reading the numbers);
  - the well-sampled conditional H(a_T | a_ref) (28 x 28 plug-in, Miller-Madow corrected);
  - variational UPPER bounds on H(a_T | observation) from the clones' held-out cross-entropy,
    with the B2 observation (141) and without the ctx block (113); their difference is the
    ctx block's measured contribution in bits per decision (a difference of two upper bounds);
  - the fine-binning check (identical float32 observation + mask), expected degenerate;
  - a duplicate-observation ambiguity check: do any two decisions share an observation and differ
    in the teacher's action (which would PROVE positive conditional entropy)?
Usage: b2_entropy.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_common as B  # noqa: E402

import numpy as np  # noqa: E402


def plug_in_entropy(counts):
    c = np.asarray([v for v in counts if v > 0], dtype=np.float64)
    n = c.sum()
    p = c / n
    h = float(-(p * np.log2(p)).sum())
    mm = h + (len(c) - 1) / (2.0 * n * np.log(2.0))     # Miller-Madow
    return h, mm, int(n), int(len(c))


def main() -> int:
    tle = B.boot()
    d = dict(np.load(B.WS / "data" / "B2-train-calibration.npz"))
    y = d["action"].astype(np.int64)
    base = d["ref_action"].astype(np.int64)
    M = d["mask"]
    obs = d["obs"].astype(np.float32)
    ctx = d["ctx"].astype(np.float32)
    n = len(y)

    h_marg, h_marg_mm, _, k = plug_in_entropy(np.bincount(y, minlength=28))
    h_unif = float(np.mean(np.log2(M.sum(1))))

    # H(a_T | a_ref), plug-in over the 28 x 28 joint
    hcond = hcond_mm = 0.0
    for a in range(28):
        sel = base == a
        if not sel.any():
            continue
        h, mm, m, _ = plug_in_entropy(np.bincount(y[sel], minlength=28))
        hcond += (m / n) * h
        hcond_mm += (m / n) * mm

    # variational upper bounds from the clones' held-out cross-entropy
    bounds = {}
    for name in ("BC", "BC-noctx", "SOFT-tau0.3", "SOFT-tau0.3-noctx"):
        p = B.WS / "results" / f"CLONE-{name}.json"
        if p.exists():
            r = json.loads(p.read_text())
            bounds[name] = {"test_ce_bits": r["test"]["ce_bits_mean"], "test_top1": r["test"]["top1"],
                            "test_n": r["test"]["n"]}

    # fine binning: identical float32 observation + mask
    def bin_counts(mat):
        c = Counter()
        for i in range(n):
            c[hashlib.sha256(np.ascontiguousarray(mat[i]).tobytes()).hexdigest()] += 1
        return c

    full = np.concatenate([obs, ctx, M.astype(np.float32)], axis=1)
    fine = bin_counts(full)
    coarse = bin_counts(np.round(full / 0.05) * 0.05)

    # ambiguity: same observation bin, different teacher action
    by_bin: dict[str, set] = {}
    for i in range(n):
        h = hashlib.sha256(np.ascontiguousarray(full[i]).tobytes()).hexdigest()
        by_bin.setdefault(h, set()).add(int(y[i]))
    ambiguous = sum(1 for v in by_bin.values() if len(v) > 1)

    out = {
        "n_decisions": int(n),
        "marginal_H_a_teacher_bits": h_marg, "marginal_H_miller_madow": h_marg_mm, "support": k,
        "uniform_over_legal_bits": h_unif,
        "H_a_teacher_given_a_ref_bits": hcond, "H_a_teacher_given_a_ref_miller_madow": hcond_mm,
        "teacher_eq_ref_frac": float((y == base).mean()),
        "variational_upper_bounds_test_ce_bits": bounds,
        "ctx_block_bits_gained_test_ce": (bounds["BC-noctx"]["test_ce_bits"] - bounds["BC"]["test_ce_bits"])
        if "BC" in bounds and "BC-noctx" in bounds else None,
        "fine_bins": {"n_bins": len(fine), "share_in_shared_bin": float(
            sum(v for v in fine.values() if v > 1) / n)},
        "coarse_bins_0p05": {"n_bins": len(coarse), "share_in_shared_bin": float(
            sum(v for v in coarse.values() if v > 1) / n)},
        "ambiguous_bins": ambiguous,
        "note": ("T_SEQ is not a function of the student's observation by construction (it is an argmax over "
                 "counterfactual joint evaluations), so no exact decoder is expected and none is claimed; the "
                 "entropy is bounded above, not pinned."),
        "tle_file_set_sha256": tle, "code": B.code_ident(),
    }
    B.write_json(B.WS / "results" / "ENTROPY.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "code"}, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
