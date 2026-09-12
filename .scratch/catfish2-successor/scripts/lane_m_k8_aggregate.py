"""LANE-M: aggregate and read the k = 8 pairwise causal matrix.  No verdict.

Controller record ``716f104e`` sections 5 and 8, and Amendment 15 sections 7 and 8.
The gates are FROZEN and none is invented here:

    FULL - T0-only      >= +1.0 %   relative pooled EE   (delta_DEV)
    FULL - T_NEXT-only  >= +1.0 %   relative pooled EE
    FULL >  matched null            pooled EE
    served >= D0_served - 0.005     (>= -0.5 pp vs D0)
    p10    >= 0.5 * D0_p10
    bits   >= 0.95 * D0_bits

Also reported, per controller record section 3: the realised FULL ``|A_CF| = 1``
rate and its PER-STEP breakdown, against the frozen ``p_singleton = 9395/24000``
and against the null's own realised singleton rate.  ``p_singleton`` is a marginal
estimated on the P0 (T0-committed) state distribution, while the FULL arm visits
the learner's own states; both known sources of divergence are printed side by
side and neither is adjudicated here.

Usage::

    lane_m_k8_aggregate.py --root DIR --episode 100 --out RESULT.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TREE / "src"))
sys.path.insert(0, str(TREE / "scripts"))

import numpy as np  # noqa: E402

import dev_e0_common as D  # noqa: E402

DELTA_DEV = 0.01
CELLS = (
    ("D0", 1, None, None, False),
    ("T0-only", 4, None, None, False),
    ("T_NEXT-only", 8, ("T_NEXT",), None, False),
    ("FULL{T0,T_NEXT}", 8, ("T0", "T_NEXT"), None, False),
    ("2-null-bernoulli", 9, None, 2, True),
)


def _load(root: Path, name: str, arm: int, teachers, n_proposals, bern, episode: int):
    run = root / f"{D.arm_name(arm, teachers, n_proposals=n_proposals, bernoulli=bern)}-k8"
    devval = run / f"devval-ep{episode:05d}.json"
    status = run / "status.json"
    logs = run / "episode-logs.json"
    out = {"cell": name, "arm": arm, "run_dir": str(run),
           "present": devval.is_file()}
    if status.is_file():
        st = json.loads(status.read_text())
        out.update(status=st.get("status"),
                   episodes_completed=st.get("episodes_completed"),
                   wall_s=st.get("wall_s"), rss_gb=st.get("rss_gb"),
                   config_hash=st.get("fingerprint", {}).get("config_hash"),
                   code_commit=st.get("fingerprint", {}).get("code", {}).get("commit"),
                   multi_spec=st.get("fingerprint", {}).get("multi_spec"))
    if not devval.is_file():
        return out
    d = json.loads(devval.read_text())
    out.update(
        ee=float(d["ee"]), bits=float(d["bits"]), joules=float(d["joules"]),
        served=float(d["served"]),
        p10=float(d["per_served_user_rate_p10_bps"]),
        rate_min=float(d["per_served_user_rate_min_bps"]),
        ho_per_user_min=float(d["ho_per_user_min"]),
        h_inter=float(d["h_inter"]), h_intra=float(d["h_intra"]),
        beams=float(d["beams"]), t0_agreement=float(d.get("t0_agreement", float("nan"))),
        ee_ep=[float(x) for x in d["ee_ep"]],
        devval_episodes=int(d["n_episodes"]),
    )
    if logs.is_file():
        rows = json.loads(logs.read_text())[:episode]
        multi = [r for r in rows if "multi_set_cardinality_hist" in r]
        if multi:
            hist = np.sum([r["multi_set_cardinality_hist"] for r in multi], axis=0)
            per_dec = np.sum([r["multi_decisions_per_step"] for r in multi], axis=0)
            per_one = np.sum([r["multi_singletons_per_step"] for r in multi], axis=0)
            live = int(hist[1:].sum())
            out.update(
                multi_cardinality_hist=[int(x) for x in hist],
                multi_singleton_rate=float(hist[1] / max(live, 1)),
                multi_duplicate_fraction=float(np.mean(
                    [r["multi_duplicate_fraction"] for r in multi])),
                multi_decisions_per_step=[int(x) for x in per_dec],
                multi_singleton_rate_per_step=[
                    (float(a / b) if b else None) for a, b in zip(per_one, per_dec)],
                multi_p_singleton_declared=multi[-1].get("multi_p_singleton_declared"),
                multi_teachers=multi[-1].get("multi_teachers"),
                multi_null_id=multi[-1].get("multi_null_id"),
                multi_mechanism_id=multi[-1].get("multi_mechanism_id"),
            )
    return out


def read(root: Path, episode: int) -> dict:
    cells = {c[0]: _load(root, *c, episode) for c in CELLS}
    missing = [n for n, c in cells.items() if not c["present"]]
    result = {
        "lane": "CF2S-LANE-M k = 8 reading (development lane; NOT formal evidence)",
        "governing": "Amendment 15 sections 7-8; controller record 716f104e",
        "root": str(root), "episode": episode, "seed_index": 8,
        "delta_dev_relative_pooled_ee": DELTA_DEV,
        "cells": cells, "missing": missing,
    }
    if missing:
        result["gates"] = None
        return result

    d0, t0, tn = cells["D0"], cells["T0-only"], cells["T_NEXT-only"]
    full, null = cells["FULL{T0,T_NEXT}"], cells["2-null-bernoulli"]

    def rel(a, b):
        return (a["ee"] - b["ee"]) / b["ee"]

    paired = {}
    for name, other in (("vs_T0_only", t0), ("vs_T_NEXT_only", tn),
                        ("vs_2null", null), ("vs_D0", d0)):
        a = np.asarray(full["ee_ep"], dtype=float)
        b = np.asarray(other["ee_ep"], dtype=float)
        n = min(a.size, b.size)
        paired[name] = {"wins": int((a[:n] > b[:n]).sum()), "of": int(n),
                        "mean_relative": float(np.mean((a[:n] - b[:n]) / b[:n]))}

    gates = {
        "FULL_minus_T0only_rel_ee": rel(full, t0),
        "FULL_minus_T0only_pass": rel(full, t0) >= DELTA_DEV,
        "FULL_minus_TNEXTonly_rel_ee": rel(full, tn),
        "FULL_minus_TNEXTonly_pass": rel(full, tn) >= DELTA_DEV,
        "FULL_gt_matched_null": full["ee"] > null["ee"],
        "FULL_vs_null_rel_ee": rel(full, null),
        "served_delta_pp_vs_D0": (full["served"] - d0["served"]) * 100.0,
        "served_pass": (full["served"] - d0["served"]) >= -0.005,
        "p10_ratio_vs_D0": full["p10"] / d0["p10"],
        "p10_pass": full["p10"] >= 0.5 * d0["p10"],
        "bits_ratio_vs_D0": full["bits"] / d0["bits"],
        "bits_pass": full["bits"] >= 0.95 * d0["bits"],
    }
    gates["all_pass"] = all(gates[k] for k in
                            ("FULL_minus_T0only_pass", "FULL_minus_TNEXTonly_pass",
                             "FULL_gt_matched_null", "served_pass", "p10_pass",
                             "bits_pass"))
    result["gates"] = gates
    result["paired_devval_episodes"] = paired
    result["cardinality_reading"] = {
        "p_singleton_frozen": D.P_SINGLETON_TNEXT,
        "p_singleton_rational": f"{D.P_SINGLETON_TNEXT_NUM}/{D.P_SINGLETON_TNEXT_DEN}",
        "FULL_realised_singleton_rate": full.get("multi_singleton_rate"),
        "null_realised_singleton_rate": null.get("multi_singleton_rate"),
        "FULL_singleton_rate_per_step": full.get("multi_singleton_rate_per_step"),
        "null_singleton_rate_per_step": null.get("multi_singleton_rate_per_step"),
        "FULL_cardinality_hist": full.get("multi_cardinality_hist"),
        "null_cardinality_hist": null.get("multi_cardinality_hist"),
        "FULL_duplicate_fraction": full.get("multi_duplicate_fraction"),
        "caveat": (
            "p_singleton is a MARGINAL frozen on the P0 (T0-committed) state "
            "distribution; the FULL arm visits the learner's own states, and the "
            "singleton rate is not uniform across the episode (t = 0 -> 0.2825, "
            "t = 1..8 -> 0.3290, t = 9 -> 1.0000 by construction, T_NEXT's mandatory "
            "final-step T0 fallback).  A uniform Bernoulli at 0.3915 therefore "
            "over-produces singletons at t = 0..8 and under-produces at t = 9.  Both "
            "divergences are reported, neither is adjudicated here."
        ),
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--episode", type=int, default=100)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = read(a.root, a.episode)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=2, default=str) + "\n")
    if res["missing"]:
        print("MISSING:", res["missing"])
        return 2
    print(f"k = 8 DEVVAL at episode {a.episode}  (development lane, no verdict)")
    for name, c in res["cells"].items():
        print(f"  {name:<18} ee={c['ee']:.6e} bits={c['bits']:.4e} "
              f"served={c['served']:.5f} p10={c['p10']:.4e} "
              f"ho/user/min={c['ho_per_user_min']:.4f}")
    g = res["gates"]
    print(f"  FULL-T0only   {g['FULL_minus_T0only_rel_ee']*100:+.3f} %  "
          f"pass={g['FULL_minus_T0only_pass']}")
    print(f"  FULL-TNEXTonly{g['FULL_minus_TNEXTonly_rel_ee']*100:+.3f} %  "
          f"pass={g['FULL_minus_TNEXTonly_pass']}")
    print(f"  FULL>null     {g['FULL_gt_matched_null']}  "
          f"({g['FULL_vs_null_rel_ee']*100:+.3f} %)")
    print(f"  served {g['served_delta_pp_vs_D0']:+.4f} pp pass={g['served_pass']}; "
          f"p10 x{g['p10_ratio_vs_D0']:.4f} pass={g['p10_pass']}; "
          f"bits x{g['bits_ratio_vs_D0']:.4f} pass={g['bits_pass']}")
    print(f"  ALL FROZEN GATES PASS: {g['all_pass']}")
    cr = res["cardinality_reading"]
    print(f"  |A_CF|=1  FULL {cr['FULL_realised_singleton_rate']}  "
          f"null {cr['null_realised_singleton_rate']}  "
          f"frozen p_singleton {cr['p_singleton_frozen']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
