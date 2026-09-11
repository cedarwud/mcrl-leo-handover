#!/usr/bin/env python3
"""Apply V025-CONTROLLER-DECLARATION-SCORED-CHECKPOINT-2026-09-11 to per-seed stopping analyses.

primary   = update 4,000 for every seed;
secondary = the first cadence point k at which C1, C2 and C3 are all admissible
            and stay admissible at every later cadence point (k..4,000);
            "non-persistent" when no such k exists.

Reads the per-seed stopping-analysis JSONs only.  Computes no EE quantity.
Fit metrics in those JSONs are in-sample (no held-out split): a convergence
check, never a quality claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

DECLARATION = "V025-CONTROLLER-DECLARATION-SCORED-CHECKPOINT-2026-09-11"
ROUTES = ("C1", "C2", "C3")
PRIMARY = 4000


def secondary(analysis: dict) -> tuple[object, list[int]]:
    checks = {route: {int(k): v["admissible"] for k, v in analysis["routes"][route]["checks"].items()}
              for route in ROUTES}
    cadence = sorted(set.intersection(*(set(c) for c in checks.values())))
    joint = [k for k in cadence if all(checks[r][k] for r in ROUTES)]
    first = None
    for index, k in enumerate(cadence):
        if all(all(checks[r][later] for r in ROUTES) for later in cadence[index:]):
            first = k
            break
    return (first if first is not None else "non-persistent"), joint


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", action="append", required=True,
                        help="seed_index=path/to/stopping-analysis.json (repeatable)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()
    for out in (args.output, args.markdown):
        if out.exists():
            raise SystemExit(f"refusing to overwrite {out}")
    rows = []
    for item in args.analysis:
        index, path = item.split("=", 1)
        analysis = json.loads(Path(path).read_text(encoding="ascii"))
        applied = analysis["applied_to"]
        if applied["seed_domain"] != f"V025_LEARNER/seed/{int(index)}":
            raise SystemExit(f"seed domain mismatch in {path}")
        second, joint = secondary(analysis)
        last = applied["last_checkpoint"]
        primary_entry = analysis["routes"]["C1"]["trajectory"].get(str(PRIMARY))
        rows.append({
            "seed_index": int(index), "seed": applied["seed"], "run": applied["run"],
            "checkpoints_analysed": applied["checkpoints_analysed"], "last_checkpoint": last,
            "primary_scored_checkpoint": PRIMARY if last == PRIMARY else None,
            "primary_checkpoint_sha256": primary_entry["checkpoint_sha256"] if primary_entry else None,
            "secondary_scored_checkpoint": second,
            "first_admissible_update": analysis["first_admissible_update"],
            "jointly_admissible_cadences": joint,
            "admissible_at_4000": {
                r: analysis["routes"][r]["checks"].get(str(PRIMARY), {}).get("admissible") for r in ROUTES
            },
            "analysis_path": path,
        })
    rows.sort(key=lambda r: r["seed_index"])
    numeric = [r["secondary_scored_checkpoint"] for r in rows if isinstance(r["secondary_scored_checkpoint"], int)]
    summary = {
        "schema": "seedpar-scored-checkpoints-v1", "declaration": DECLARATION,
        "primary_rule": "update 4000 for every seed",
        "secondary_rule": ("first cadence point where C1, C2 and C3 are simultaneously admissible and "
                           "remain admissible at every later cadence point; else non-persistent"),
        "in_sample_note": ("corpus has no held-out split; fit metrics are in-sample: a convergence "
                           "check, never a quality claim"),
        "no_ee_quantity_computed": True, "loss_values_are_not_ee_evidence": True,
        "seeds": rows,
        "secondary_persistent_count": len(numeric), "seed_count": len(rows),
        "secondary_min": min(numeric) if numeric else None,
        "secondary_max": max(numeric) if numeric else None,
        "secondary_median": (sorted(numeric)[len(numeric) // 2] if len(numeric) % 2 else
                             sum(sorted(numeric)[len(numeric) // 2 - 1: len(numeric) // 2 + 1]) / 2)
                            if numeric else None,
    }
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="ascii")
    lines = [
        f"Declaration `{DECLARATION}`. Primary = update 4,000; secondary = first persistent joint "
        "admissible cadence. In-sample convergence check only; not a quality claim; no EE.",
        "",
        "| Seed index | Seed | Checkpoints | Primary (sha256 prefix) | Secondary | First admissible C1 / C2 / C3 | Admissible at 4,000 C1/C2/C3 |",
        "|---:|---:|---:|---|---|---|---|",
    ]
    for r in rows:
        fa = r["first_admissible_update"]
        a4 = r["admissible_at_4000"]
        lines.append(
            f"| {r['seed_index']} | {r['seed']} | {r['checkpoints_analysed']} | "
            f"{r['primary_scored_checkpoint'] or 'MISSING'} (`{(r['primary_checkpoint_sha256'] or '')[:12]}`) | "
            f"{r['secondary_scored_checkpoint']} | {fa['C1']} / {fa['C2']} / {fa['C3']} | "
            f"{'/'.join('Y' if a4[x] else 'N' for x in ROUTES)} |"
        )
    lines += ["", f"Secondary persistent in {len(numeric)}/{len(rows)} seeds; "
              f"min {summary['secondary_min']}, median {summary['secondary_median']}, max {summary['secondary_max']}."]
    args.markdown.write_text("\n".join(lines) + "\n", encoding="ascii")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
