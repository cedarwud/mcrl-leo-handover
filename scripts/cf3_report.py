"""CF3PILOT aggregation: eval JSONs + training status -> summary JSON.

Applies the addendum's operational reading (X > Y iff seed-mean pooled EE
higher AND X beats Y on >= 2 of 3 same-index seed pairs) and the C-S cluster
bootstrap (clusters = the 24 evaluation episodes, paired across arms by
per-episode reseeding; 10,000 resamples; percentile 95%).

Usage: cf3_report.py --eval-dir DIR --root DIR --out FILE
       (eval files named <ARM>s<K>.json, e.g. A2s0.json)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ARMS = ("A0", "A1", "A2", "A3")
NAMES = {"A0": "BASELINE", "A1": "OFF", "A2": "CF3", "A3": "NULL3"}
H_CAP = 0.6016
CS_MARGIN = -0.005


def beats(x: dict, y: dict) -> bool:
    mx, my = np.mean(list(x.values())), np.mean(list(y.values()))
    wins = sum(x[k] > y[k] for k in x)
    return bool(mx > my and wins >= 2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", type=Path, required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ev = {arm: {k: json.loads((a.eval_dir / f"{arm}s{k}.json").read_text())
                for k in range(3)} for arm in ARMS}
    # ---- pairing checks
    epochs = {(arm, k): [r["epoch"] for r in ev[arm][k]["episodes"]] for arm in ARMS for k in range(3)}
    hashes = {(arm, k): [r["t0_obs_sha256"] for r in ev[arm][k]["episodes"]] for arm in ARMS for k in range(3)}
    ref_e, ref_h = epochs[("A1", 0)], hashes[("A1", 0)]
    pairing = {
        "all_arms_same_epochs": all(v == ref_e for v in epochs.values()),
        "all_arms_same_t0_obs": all(v == ref_h for v in hashes.values()),
        "determinism_placebo": {f"{arm}s{k}": ev[arm][k].get("determinism_placebo_bit_identical")
                                for arm in ARMS for k in range(3)},
        "tle": sorted({ev[arm][k]["tle_file_set_sha256"] for arm in ARMS for k in range(3)}),
        "commits": sorted({str(ev[arm][k].get("commit")) for arm in ARMS for k in range(3)}),
    }
    # ---- per seed
    per = {}
    for arm in ARMS:
        per[arm] = {}
        for k in range(3):
            e = ev[arm][k]
            c2 = e.get("c2_activation")
            st = json.loads((a.root / f"{arm}-{NAMES[arm]}-s{k}" / "status.json").read_text())
            logs_p = a.root / f"{arm}-{NAMES[arm]}-s{k}" / "episode-logs.json"
            lam_pos = None
            if arm != "A0" and logs_p.is_file():
                logs = json.loads(logs_p.read_text())
                lam_pos = float(np.mean([r["lambda"] > 0 for r in logs]))
            per[arm][k] = {
                "ee": e["ee"], "bits": e["bits"], "joules": e["joules"],
                "h_inter": e["h_inter"], "h_intra": e["h_intra"], "served": e["served"],
                "beams": e["beams"], "sem_ee_ep": float(np.std(e["ee_ep"]) / np.sqrt(len(e["ee_ep"]))),
                "checkpoint_sha256": e["checkpoint_sha256"], "checkpoint": e["checkpoint"],
                "eta": e["meta"].get("eta"), "lambda": e["meta"].get("lambda"),
                "c2_changed_fraction": (c2["changed_without_QH"] / c2["decisions"]) if c2 else None,
                "lambda_pos_episode_fraction": lam_pos,
                "dual_trajectory": [
                    {kk: r.get(kk) for kk in ("episode", "kind", "eta", "lambda", "measured_ee",
                                              "measured_h_inter", "applied")}
                    for r in (st.get("dual_trajectory") or e["meta"].get("dual_trajectory") or [])
                ],
                "training_status": st.get("status"),
            }
    means = {arm: {q: float(np.mean([per[arm][k][q] for k in range(3)]))
                   for q in ("ee", "bits", "joules", "h_inter", "h_intra", "served", "beams")}
             for arm in ARMS}
    ee = {arm: {k: per[arm][k]["ee"] for k in range(3)} for arm in ARMS}
    comp = {}
    for x in ARMS:
        for y in ARMS:
            if x != y:
                comp[f"{x}>{y}"] = beats(ee[x], ee[y])
    # ---- C-S cluster bootstrap vs A1
    rng = np.random.default_rng(0)
    n_ep = len(ev["A1"][0]["episodes"])

    def served_counts(arm):
        s = np.zeros(n_ep); u = np.zeros(n_ep)
        for k in range(3):
            for i, r in enumerate(ev[arm][k]["episodes"]):
                s[i] += r["served"]; u[i] += r["user_steps"]
        return s, u

    s1, u1 = served_counts("A1")
    cs = {}
    draws = rng.integers(0, n_ep, size=(10_000, n_ep))
    for arm in ("A0", "A2", "A3"):
        s, u = served_counts(arm)
        point = s.sum() / u.sum() - s1.sum() / u1.sum()
        boot = s[draws].sum(1) / u[draws].sum(1) - s1[draws].sum(1) / u1[draws].sum(1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        cs[arm] = {"diff_pp": 100 * point, "ci95_pp": [100 * lo, 100 * hi],
                   "non_inferior": bool(lo > CS_MARGIN),
                   "per_seed_diff_pp": [100 * (per[arm][k]["served"] - per["A1"][k]["served"])
                                        for k in range(3)]}
    ch = {arm: {"mean_h_inter": means[arm]["h_inter"], "met": means[arm]["h_inter"] <= H_CAP,
                "per_seed": [per[arm][k]["h_inter"] for k in range(3)]} for arm in ARMS}
    # ---- declared reading
    a2a3, a2a1, a3a1 = comp["A2>A3"], comp["A2>A1"], comp["A3>A1"]
    a3a2 = comp["A3>A2"]
    if a2a3 and a2a1 and ch["A2"]["met"] and cs["A2"]["non_inferior"]:
        branch = "1: A2 > A3 and A2 > A1, C-H met, C-S non-inferior -> directional three-catfish signal"
    elif (not a2a3 and not a3a2) and a2a1 and a3a1:
        branch = "2: A2 ~ A3 > A1 -> the gain is extra experience, not the demonstrators"
    elif not a2a1:
        branch = "3: A1 >= A2 -> no catfish effect at pilot scale"
    else:
        branch = "none of the declared branches"
    c2_inactive = {k: (all(r["lambda"] == 0.0 for r in per["A2"][k]["dual_trajectory"] if r.get("lambda") is not None)
                       and (per["A2"][k]["c2_changed_fraction"] or 0.0) < 0.01) for k in range(3)}
    out = {"pairing": pairing, "per_seed": per, "arm_means": means, "comparisons": comp,
           "C_S_vs_A1": cs, "C_H": ch, "branch": branch, "c2_head_inactive_A2": c2_inactive,
           "A1_vs_A0": comp["A1>A0"], "A0_vs_A1": comp["A0>A1"], "A2_vs_A0": comp["A2>A0"]}
    Path(a.out).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({"means": means, "comparisons": comp, "branch": branch, "C_S": cs,
                      "C_H": ch, "pairing": pairing}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
