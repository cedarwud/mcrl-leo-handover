"""CF3PILOT: render the summary JSON from cf3_report.py as markdown tables.

Numbers are copied from the summary JSON only (nothing typed by hand).

Usage: cf3_render.py SUMMARY_JSON OUT_MD
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ARMS = ("A0", "A1", "A2", "A3")
NAMES = {"A0": "BASELINE (MODQN eq.16)", "A1": "OFF", "A2": "CF3", "A3": "NULL3"}


def m(x):
    return f"{x / 1e6:,.2f}"


def main() -> int:
    s = json.loads(Path(sys.argv[1]).read_text())
    per, means = s["per_seed"], s["arm_means"]
    L = []
    L.append(f"Declared branch: **{s['branch']}**\n")
    L.append("## Final checkpoint, 24 evaluation episodes (per-episode reseeded), greedy\n")
    L.append("| arm | seed | pooled EE (M bit/J) | bits | joules | H_inter | H_intra | ho / user-min | "
             "meets former C-H 0.6016 | served | active beams | per-episode EE sem (M) |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|")
    for arm in ARMS:
        for k, r in sorted(per[arm].items(), key=lambda kv: int(kv[0])):
            L.append(f"| {arm} {NAMES[arm]} | {k} | {m(r['ee'])} | {r['bits']:.4e} | {r['joules']:.4e} | "
                     f"{r['h_inter']:.4f} | {r['h_intra']:.4f} | {r['ho_per_user_min']:.3f} | "
                     f"{'yes' if r['meets_former_C_H'] else 'no'} | {r['served']:.5f} | {r['beams']:.2f} | "
                     f"{r['sem_ee_ep'] / 1e6:.2f} |")
        a = means[arm]
        L.append(f"| **{arm} mean** | 0-2 | **{m(a['ee'])}** | {a['bits']:.4e} | {a['joules']:.4e} | "
                 f"{a['h_inter']:.4f} | {a['h_intra']:.4f} | {a['ho_per_user_min']:.3f} | "
                 f"{'yes' if a['h_inter'] <= 0.6016 else 'no'} | {a['served']:.5f} | {a['beams']:.2f} | |")
    L.append("\n## Pairwise reading rule (seed-mean higher AND >= 2 of 3 same-index seed pairs)\n")
    L.append("| comparison | holds | seed-pair wins | relative mean difference |")
    L.append("|---|---|---|---:|")
    for c, v in s["comparisons"].items():
        L.append(f"| {c} | {v['holds']} | {v['seed_pair_wins']} | {100 * v['mean_diff_rel']:+.2f}% |")
    L.append("\n## C-S (served fraction vs A1; 95% cluster bootstrap over the 24 paired episodes)\n")
    L.append("| arm | diff (pp) | 95% CI (pp) | non-inferior at -0.5 pp | per-seed diff (pp) |")
    L.append("|---|---:|---|---|---|")
    for arm, v in s["C_S_vs_A1"].items():
        ps = ", ".join(f"s{k}: {d:+.3f}" for k, d in v["per_seed_diff_pp"].items())
        L.append(f"| {arm} | {v['diff_pp']:+.3f} | [{v['ci95_pp'][0]:+.3f}, {v['ci95_pp'][1]:+.3f}] | "
                 f"{v['non_inferior']} | {ps} |")
    L.append("\n## Learning-speed readings (greedy, 24 calibration episodes): pooled EE (M bit/J) at 100/250/500/750/1000 and AUC/900\n")
    L.append("| arm | seed | 100 | 250 | 500 | 750 | 1000 | AUC/900 |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for arm in ARMS:
        for k, r in sorted(per[arm].items(), key=lambda kv: int(kv[0])):
            rd = r["readings"]
            cells = [m(rd[str(e)]["measured_ee"]) if str(e) in rd else "n/a" for e in (100, 250, 500, 750, 1000)]
            auc = "n/a" if r["auc_mean_ee"] is None else m(r["auc_mean_ee"])
            L.append(f"| {arm} | {k} | " + " | ".join(cells) + f" | {auc} |")
        rm = means[arm]["readings_mean"]
        cells = [m(rm[str(e)]) if str(e) in rm else "n/a" for e in (100, 250, 500, 750, 1000)]
        auc = "n/a" if means[arm]["auc_mean_ee"] is None else m(means[arm]["auc_mean_ee"])
        L.append(f"| **{arm} mean** | 0-2 | " + " | ".join(cells) + f" | {auc} |")
    L.append("\n## H_inter / H_intra at the readings (calibration episodes)\n")
    L.append("| arm | seed | 100 | 250 | 500 | 750 | 1000 |")
    L.append("|---|---|---|---|---|---|---|")
    for arm in ARMS:
        for k, r in sorted(per[arm].items(), key=lambda kv: int(kv[0])):
            rd = r["readings"]
            cells = [f"{rd[str(e)]['measured_h_inter']:.3f} / {rd[str(e)]['measured_h_intra']:.3f}"
                     if str(e) in rd and rd[str(e)].get("measured_h_intra") is not None else "n/a"
                     for e in (100, 250, 500, 750, 1000)]
            L.append(f"| {arm} | {k} | " + " | ".join(cells) + " |")
    L.append("\n## eta trajectory (bit/J; lambda fixed 0) and lambda* diagnostic (A1-A3)\n")
    L.append("| arm | seed | eta_0 | eta set at 500 | eta set at 750 (deployed) | measured at 1000 (not applied) | lambda* | decisions changed at lambda* |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for arm in ("A1", "A2", "A3"):
        for k, r in sorted(per[arm].items(), key=lambda kv: int(kv[0])):
            tr = {(x.get("kind"), x.get("episode")): x for x in r["dual_trajectory"]}
            def g(key, field):
                x = tr.get(key)
                return "n/a" if x is None or x.get(field) is None else m(x[field])
            ls = r.get("lambda_star") or {}
            chg = ls.get("changed_fraction", 0.0 if ls.get("lambda_star") == 0.0 else None)
            L.append(f"| {arm} | {k} | {g(('initial', 0), 'eta')} | {g(('quarter', 500), 'eta')} | "
                     f"{g(('quarter', 750), 'eta')} | {g(('final-diagnostic', 1000), 'measured_ee')} | "
                     f"{ls.get('lambda_star')} | {chg} |")
    L.append("\n## Checks\n")
    p = s["pairing"]
    L.append(f"- all runs same evaluation epochs: {p['all_runs_same_epochs']}; same t=0 observations: {p['all_runs_same_t0_obs']}")
    L.append(f"- determinism placebo (each checkpoint evaluated twice, bit-identical): {p['determinism_placebo']}")
    L.append(f"- TLE: {p['tle']}; eval commits: {p['commits']}")
    L.append(f"- pool re-verification: ok={s['pool_verify']['ok']}, pools {s['pool_verify']['pools_checked']}, "
             f"run bindings {s['pool_verify']['run_pool_bindings_checked']}")
    L.append(f"- report script: {s.get('report_script')}")
    Path(sys.argv[2]).write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
