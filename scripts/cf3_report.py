"""CF3PILOT aggregation: eval JSONs + training status/readings -> summary JSON.

Reading rule (addendum D): X > Y iff mean pooled EE over all of X's seeds >
mean over all of Y's seeds AND X beats Y on a majority of the same-index seed
pairs both arms have.  C-S: served-fraction difference vs A1 pooled over all
seeds, cluster bootstrap over the 24 evaluation episodes (paired by per-episode
reseeding), 10,000 resamples, percentile 95%, non-inferior iff lower > -0.5 pp.
C-H is information only (Amendment 2).  Learning-speed readings at
100/250/500/750/1000 with trapezoid AUC (addendum E).

Usage: cf3_report.py --eval-dir DIR --root DIR --out FILE
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

# Launch of 12 runs: every arm at seeds 0-2 (seeds 3-4 deferred; addendum H).
SEEDS = {"A0": (0, 1, 2), "A1": (0, 1, 2), "A2": (0, 1, 2), "A3": (0, 1, 2)}
NAMES = {"A0": "BASELINE", "A1": "OFF", "A2": "CF3", "A3": "NULL3"}
H_CAP = 0.6016
CS_MARGIN = -0.005
READ_EPS = (100, 250, 500, 750, 1000)
DT = 30.08


def beats(x: dict, y: dict) -> tuple[bool, int, int]:
    common = sorted(set(x) & set(y))
    wins = sum(x[k] > y[k] for k in common)
    ok = np.mean(list(x.values())) > np.mean(list(y.values())) and wins > len(common) / 2
    return bool(ok), int(wins), len(common)


def readings(run_dir: Path) -> dict:
    out = {}
    p = run_dir / "readings.jsonl"
    if not p.is_file():
        return out
    for line in p.read_text().splitlines():
        r = json.loads(line)
        if "gate" in r:
            continue
        ep = int(r["episode"])
        if ep in READ_EPS and ep not in out:
            out[ep] = {k: r.get(k) for k in ("measured_ee", "measured_h_inter",
                                             "measured_h_intra", "measured_served",
                                             "measured_beams", "kind", "eta", "lambda")}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-dir", type=Path, required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    ev = {arm: {k: json.loads((a.eval_dir / f"{arm}s{k}.json").read_text()) for k in ks}
          for arm, ks in SEEDS.items()}
    keys = [(arm, k) for arm, ks in SEEDS.items() for k in ks]
    epochs = {key: [r["epoch"] for r in ev[key[0]][key[1]]["episodes"]] for key in keys}
    hashes = {key: [r["t0_obs_sha256"] for r in ev[key[0]][key[1]]["episodes"]] for key in keys}
    pairing = {
        "all_runs_same_epochs": all(v == epochs[("A1", 0)] for v in epochs.values()),
        "all_runs_same_t0_obs": all(v == hashes[("A1", 0)] for v in hashes.values()),
        "determinism_placebo": {f"{arm}s{k}": ev[arm][k].get("determinism_placebo_bit_identical")
                                for arm, k in keys},
        "tle": sorted({ev[arm][k]["tle_file_set_sha256"] for arm, k in keys}),
        "commits": sorted({str(ev[arm][k].get("commit")) for arm, k in keys}),
    }
    per = {}
    for arm, ks in SEEDS.items():
        per[arm] = {}
        for k in ks:
            e = ev[arm][k]
            run = a.root / f"{arm}-{NAMES[arm]}-s{k}"
            st = json.loads((run / "status.json").read_text())
            rd = readings(run)
            curve = [(ep, rd[ep]["measured_ee"]) for ep in READ_EPS if ep in rd]
            auc = (float(np.trapezoid([c[1] for c in curve], [c[0] for c in curve]))
                   if len(curve) == len(READ_EPS) else None)
            lam_pos = None
            logs_p = run / "episode-logs.json"
            if arm != "A0" and logs_p.is_file():
                lam_pos = float(np.mean([r["lambda"] > 0 for r in json.loads(logs_p.read_text())]))
            per[arm][k] = {
                "ee": e["ee"], "bits": e["bits"], "joules": e["joules"],
                "h_inter": e["h_inter"], "h_intra": e["h_intra"],
                "ho_per_user_min": (e["h_inter"] + e["h_intra"]) * 60.0 / DT,
                "meets_former_C_H": e["h_inter"] <= H_CAP,
                "served": e["served"], "beams": e["beams"],
                "sem_ee_ep": float(np.std(e["ee_ep"]) / np.sqrt(len(e["ee_ep"]))),
                "checkpoint": e["checkpoint"], "checkpoint_sha256": e["checkpoint_sha256"],
                "eta": e["meta"].get("eta"), "lambda": e["meta"].get("lambda"),
                "lambda_star": e.get("c2_lambda_star"),
                "lambda_pos_episode_fraction": lam_pos,
                "dual_trajectory": [
                    {kk: r.get(kk) for kk in ("episode", "kind", "eta", "lambda", "measured_ee",
                                              "measured_h_inter", "applied")}
                    for r in (st.get("dual_trajectory") or [])],
                "readings": rd, "auc_100_1000": auc,
                "auc_mean_ee": None if auc is None else auc / 900.0,
                "training_status": st.get("status"),
                "learning_check": st.get("learning_check"),
            }
    qs = ("ee", "bits", "joules", "h_inter", "h_intra", "ho_per_user_min", "served", "beams")
    means = {}
    for arm in SEEDS:
        means[arm] = {q: float(np.mean([per[arm][k][q] for k in SEEDS[arm]])) for q in qs}
        aucs = [per[arm][k]["auc_mean_ee"] for k in SEEDS[arm]]
        means[arm]["auc_mean_ee"] = float(np.mean(aucs)) if None not in aucs else None
        means[arm]["readings_mean"] = {
            ep: float(np.mean([per[arm][k]["readings"][ep]["measured_ee"] for k in SEEDS[arm]]))
            for ep in READ_EPS if all(ep in per[arm][k]["readings"] for k in SEEDS[arm])}
    ee = {arm: {k: per[arm][k]["ee"] for k in SEEDS[arm]} for arm in SEEDS}
    comp = {}
    for x in SEEDS:
        for y in SEEDS:
            if x != y:
                ok, w, n = beats(ee[x], ee[y])
                comp[f"{x}>{y}"] = {"holds": ok, "seed_pair_wins": f"{w}/{n}",
                                    "mean_diff_rel": means[x]["ee"] / means[y]["ee"] - 1.0}
    rng = np.random.default_rng(0)
    n_ep = len(ev["A1"][0]["episodes"])

    def served_counts(arm):
        s = np.zeros(n_ep); u = np.zeros(n_ep)
        for k in SEEDS[arm]:
            for i, r in enumerate(ev[arm][k]["episodes"]):
                s[i] += r["served"]; u[i] += r["user_steps"]
        return s, u

    s1, u1 = served_counts("A1")
    draws = rng.integers(0, n_ep, size=(10_000, n_ep))
    cs = {}
    for arm in ("A0", "A2", "A3"):
        s, u = served_counts(arm)
        point = s.sum() / u.sum() - s1.sum() / u1.sum()
        boot = s[draws].sum(1) / u[draws].sum(1) - s1[draws].sum(1) / u1[draws].sum(1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        cs[arm] = {"diff_pp": 100 * point, "ci95_pp": [100 * lo, 100 * hi],
                   "non_inferior": bool(lo > CS_MARGIN),
                   "per_seed_diff_pp": {k: 100 * (per[arm][k]["served"] - per["A1"][k]["served"])
                                        for k in SEEDS[arm] if k in SEEDS["A1"]}}
    a2a3, a2a1, a3a1, a3a2 = (comp[c]["holds"] for c in ("A2>A3", "A2>A1", "A3>A1", "A3>A2"))
    if a2a3 and a2a1 and cs["A2"]["non_inferior"]:
        branch = "1: A2 > A3 and A2 > A1, C-S non-inferior -> directional three-catfish signal"
    elif (not a2a3 and not a3a2) and a2a1 and a3a1:
        branch = "2: A2 ~ A3 > A1 -> the gain is extra experience, not the demonstrators"
    elif not a2a1:
        branch = "3: A1 >= A2 -> no catfish effect at pilot scale"
    else:
        branch = "none of the declared branches"
    import subprocess
    here = Path(__file__).resolve()
    try:
        rep_commit = subprocess.run(["git", "-C", str(here.parent), "log", "-1", "--format=%H", "--",
                                     here.name], capture_output=True, text=True).stdout.strip() or None
    except OSError:
        rep_commit = None
    import hashlib
    out = {"report_script": {"path": str(here), "sha256": hashlib.sha256(here.read_bytes()).hexdigest(),
                             "git_commit": rep_commit},
           "pairing": pairing, "per_seed": per, "arm_means": means, "comparisons": comp,
           "C_S_vs_A1": cs, "branch": branch}
    Path(a.out).write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({"means": means, "comparisons": comp, "branch": branch, "C_S": cs,
                      "pairing": pairing}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
