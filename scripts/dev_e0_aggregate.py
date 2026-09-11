"""Canonical development aggregator -- collision-safe result identity.

Controller directive 2026-09-11 22:40 UTC item D.  A development result's identity is
``(run_root, config_hash, seed_index, checkpoint_episode)``.  Keying by
``arm_name + seed_index + episode`` silently overwrites distinct versions: the tau sweep
is the demonstration (three different versions all called ``E0-2-D2-T0-equal_share``, all
at k = 0, all read at episode 100), and two independent first passes hit it.  This tool
refuses to merge two records that share the full identity but differ, and it prints the
identity in every row.

Reads only ``status.json`` / ``devval-ep*.json`` written by ``run_dev_e0.py`` plus the
optional DEVVAL references, so it needs nothing from the learner and can run anywhere.

Usage::

    dev_e0_aggregate.py --root RUNS_DIR [--root ...] [--references FILE]
                        [--baseline FILE] [--out JSON] [--markdown MD]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

COLUMNS = ("ee", "bits", "joules", "served", "per_served_user_rate_mean_bps",
           "per_served_user_rate_p10_bps", "per_served_user_rate_min_bps", "beams",
           "h_inter", "h_intra", "t0_agreement", "t0_score_regret")


def identity(root: Path, run_dir: Path, status: dict, reading: dict) -> dict:
    """The four fields that make a development result unique."""
    return {
        "run_root": root.name,
        "config_hash": status["fingerprint"]["config_hash"],
        "seed_index": int(status["seed_index"]),
        "checkpoint_episode": int(reading["episode"]),
    }


def key_of(ident: dict) -> str:
    return (f"{ident['run_root']}|{ident['config_hash']}|k{ident['seed_index']}"
            f"|ep{ident['checkpoint_episode']}")


def collect(roots: list[Path]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for root in roots:
        for status_path in sorted(root.glob("*/status.json")):
            run_dir = status_path.parent
            status = json.loads(status_path.read_text())
            for reading_path in sorted(run_dir.glob("devval-ep*.json")):
                reading = json.loads(reading_path.read_text())
                ident = identity(root, run_dir, status, reading)
                key = key_of(ident)
                row = {
                    **ident,
                    "arm": status["arm"], "arm_name": status["arm_name"],
                    "mechanism": status["mechanism"], "credit_mode": status["credit_mode"],
                    "tau": status["fingerprint"]["dev_settings"]["tau"],
                    "alpha": status["fingerprint"]["dev_settings"]["alpha"],
                    "margin": status["fingerprint"]["dev_settings"]["margin"],
                    "lambda_e": status["fingerprint"]["dev_settings"]["lambda_e"],
                    "null_key": status["fingerprint"]["dev_settings"]["null_key"],
                    "teacher": status["fingerprint"]["dev_settings"]["teacher"],
                    "episodes_target": status["episodes_target"],
                    "run_status": status["status"],
                    "commit": status["fingerprint"]["code"]["commit"],
                    "code_digest": status["fingerprint"]["code_digest"],
                    "path": str(reading_path),
                    "ee_ep": reading["ee_ep"],
                    **{c: reading[c] for c in COLUMNS},
                }
                if key in out and out[key]["ee"] != row["ee"]:
                    raise SystemExit(
                        f"identity collision on {key}: {out[key]['path']} vs {row['path']}"
                    )
                out[key] = row
    return out


def paired_wins(a: dict, b: dict) -> tuple[int, int]:
    pairs = list(zip(a["ee_ep"], b["ee_ep"]))
    return sum(1 for x, y in pairs if x > y), len(pairs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, action="append", required=True)
    ap.add_argument("--references", type=Path, default=None)
    ap.add_argument("--baseline", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--markdown", type=Path, default=None)
    a = ap.parse_args()

    rows = collect(a.root)
    refs: dict[str, float] = {}
    if a.references and a.references.is_file():
        refs = {name: arm["ee"]
                for name, arm in json.loads(a.references.read_text())["arms"].items()}
    if a.baseline and a.baseline.is_file():
        refs["BASELINE_MODQN_eq16"] = json.loads(a.baseline.read_text())["ee"]

    # the paired comparator of a row is D0 at the same seed index and depth
    d0 = {(r["seed_index"], r["checkpoint_episode"]): r
          for r in rows.values() if r["mechanism"] == "D0"}
    for r in rows.values():
        base = d0.get((r["seed_index"], r["checkpoint_episode"]))
        if base is not None and base is not r:
            wins, n = paired_wins(r, base)
            r["vs_paired_D0_ratio"] = r["ee"] / base["ee"]
            r["vs_paired_D0_wins"] = f"{wins}/{n}"
            r["vs_paired_D0_identity"] = key_of(base)
        for name, ee in refs.items():
            r[f"vs_{name}_ratio"] = r["ee"] / ee

    payload = {"identity_fields": ["run_root", "config_hash", "seed_index",
                                   "checkpoint_episode"],
               "references": refs,
               "rows": {k: {kk: vv for kk, vv in v.items() if kk != "ee_ep"}
                        for k, v in sorted(rows.items())}}
    if a.out:
        a.out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    lines = ["| identity (root / config hash / k / ep) | mechanism | tau | EE (bit/J) | "
             "served | p10 | min rate | beams | H_inter | H_intra | agree T0 | regret | "
             "vs paired D0 |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for k, r in sorted(rows.items(), key=lambda kv: (kv[1]["seed_index"],
                                                     kv[1]["checkpoint_episode"],
                                                     kv[1]["mechanism"])):
        lines.append(
            f"| `{r['run_root']}` / `{r['config_hash'][:12]}` / k{r['seed_index']} / "
            f"ep{r['checkpoint_episode']} | {r['mechanism']} | {r['tau']:g} | "
            f"{r['ee']:,.0f} | {r['served']:.5f} | {r['per_served_user_rate_p10_bps']:.3e} | "
            f"{r['per_served_user_rate_min_bps']:.3e} | {r['beams']:.2f} | "
            f"{r['h_inter']:.4f} | {r['h_intra']:.4f} | {r['t0_agreement']:.4f} | "
            f"{r['t0_score_regret']:.3f} | "
            + (f"{(r['vs_paired_D0_ratio'] - 1) * 100:+.2f} % ({r['vs_paired_D0_wins']})"
               if "vs_paired_D0_ratio" in r else "--") + " |")
    table = "\n".join(lines)
    if a.markdown:
        a.markdown.write_text(table + "\n")
    print(table)
    print(f"\n{len(rows)} results under the collision-safe identity "
          f"(run_root, config_hash, seed_index, checkpoint_episode)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
