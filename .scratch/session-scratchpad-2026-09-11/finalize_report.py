#!/usr/bin/env python3
"""Fill the completion section of SEEDPAR-2026-09-11.md from the helper's outputs.

Reads only files under the SEEDPAR workspace.  Replaces the text between the
two completion markers; everything else in the report is left as written.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

WS = Path("/home/sat/mcrl-v025-seedpar-ws")
REPORT = WS / "SEEDPAR-2026-09-11.md"
BEGIN, END = "<!-- COMPLETION-BEGIN -->", "<!-- COMPLETION-END -->"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return None


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    lines = [BEGIN, "", f"## 8. Completion (filled automatically by the helper at {now})", ""]
    lines += ["### 8a. Training processes [V]", "",
              "| Output directory | Seed indices | training-result.json | Seconds per seed | s/update | Peak RSS (B) |",
              "|---|---|---|---|---:|---:|"]
    for row in (WS / ".scratch/training-pids.tsv").read_text().splitlines():
        pid, directory, indices = row.split("\t")
        result = load(WS / "artifacts" / directory / "training-result.json")
        if result is None:
            lines.append(f"| `{directory}` | {indices} | **MISSING** | - | - | - |")
            continue
        per_seed = ", ".join(f"{t['seconds']:.0f}" for t in result["seed_timings"])
        rate = result["training_seconds"] / len(result["seed_timings"]) / 4000
        lines.append(f"| `{directory}` | {indices} | present ({len(result['checkpoints'])} checkpoints) | "
                     f"{per_seed} | {rate:.2f} | {result['peak_rss_bytes']:,} |")
    lines += ["", "### 8b. Bit-for-bit checks at completion [V]", ""]
    for label, name in (("Seed 1, all common cadence points, sequential vs v3", "seed01-full-sequential-vs-v3.json"),
                        ("Seed 2, every checkpoint the sequential run wrote before retirement, vs v3",
                         "seed02-overlap-sequential-vs-v3.json")):
        data = load(WS / ".scratch/equivalence" / name)
        if data is None:
            lines.append(f"- {label}: **no result file**")
            continue
        identical = sum(1 for p in data["pairs"] if p["bytes_identical"])
        lines.append(f"- {label}: **{data['verdict']}**, {identical}/{len(data['pairs'])} pairs byte-identical "
                     f"(epochs {data['epochs_compared'][0] if data['pairs'] else '-'}"
                     f"..{data['epochs_compared'][-1] if data['pairs'] else '-'}); file `.scratch/equivalence/{name}`.")
        for p in data["pairs"]:
            if p["epoch"] in (100, 2000, 2100, 4000):
                lines.append(f"  - update {p['epoch']}: `{p['reference_sha256']}` / `{p['candidate_sha256']}`")
    lines += ["", "### 8c. Scored checkpoints per seed [V]", ""]
    scored = WS / ".scratch/stopping/scored-checkpoints.md"
    lines += (scored.read_text(encoding="ascii").splitlines() if scored.exists()
              else ["**scored-checkpoints.md missing; see .scratch/helper.log**"])
    lines += ["", "Seed 1 is analysed on the sequential run's own checkpoints (the reference); seeds 2-16 on the "
              "SEEDPAR v3 outputs. The fit metrics are in-sample (no held-out split): this is a convergence "
              "check, never a quality claim. No EE quantity was computed.", "", END]
    text = REPORT.read_text(encoding="utf-8")
    start, stop = text.index(BEGIN), text.index(END) + len(END)
    REPORT.write_text(text[:start] + "\n".join(lines) + text[stop:], encoding="utf-8")
    print("report completion section written", now)


if __name__ == "__main__":
    main()
