#!/usr/bin/env python3
"""Bit-for-bit comparison of cadence checkpoints between two runner output directories.

Reads only.  For every requested epoch (or every epoch present in both when
--epochs is 'common'), computes the SHA-256 of both files from their bytes,
checks each against its .sha256 sidecar, and compares the raw bytes.  Also
checks that all five arms are present in the reference checkpoint payload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ARMS = ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sidecar(path: Path) -> str | None:
    side = path.with_name(path.name + ".sha256")
    if not side.is_file():
        return None
    return side.read_text(encoding="ascii").split()[0]


def epochs_in(directory: Path, seed: int) -> set[int]:
    pattern = re.compile(rf"^learner-{seed}-epoch-(\d{{6}})\.json$")
    return {int(m.group(1)) for p in (directory / "checkpoints").glob("*.json") if (m := pattern.match(p.name))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--epochs", required=True, help="comma list, or 'common'")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite {args.output}")
    if args.epochs == "common":
        epochs = sorted(epochs_in(args.reference, args.seed) & epochs_in(args.candidate, args.seed))
    else:
        epochs = [int(value) for value in args.epochs.split(",")]
    rows = []
    for epoch in epochs:
        name = f"learner-{args.seed}-epoch-{epoch:06d}.json"
        ref_path, cand_path = args.reference / "checkpoints" / name, args.candidate / "checkpoints" / name
        ref_bytes, cand_bytes = ref_path.read_bytes(), cand_path.read_bytes()
        ref_sha, cand_sha = sha256_bytes(ref_bytes), sha256_bytes(cand_bytes)
        payload = json.loads(ref_bytes)
        rows.append({
            "epoch": epoch,
            "reference_path": str(ref_path), "candidate_path": str(cand_path),
            "reference_sha256": ref_sha, "candidate_sha256": cand_sha,
            "reference_sidecar_agrees": sidecar(ref_path) == ref_sha,
            "candidate_sidecar_agrees": sidecar(cand_path) == cand_sha,
            "bytes_identical": ref_bytes == cand_bytes,
            "arms_in_payload": sorted(payload["arms"]),
            "all_five_arms_present": sorted(payload["arms"]) == sorted(ARMS),
            "learner_seed_in_payload": payload["learner_seed"],
            "completed_source_epochs_in_payload": payload["completed_source_epochs"],
        })
    verdict = (
        "IDENTICAL" if rows and all(
            r["bytes_identical"] and r["reference_sidecar_agrees"] and r["candidate_sidecar_agrees"]
            and r["all_five_arms_present"] and r["learner_seed_in_payload"] == args.seed
            and r["completed_source_epochs_in_payload"] == r["epoch"]
            for r in rows
        ) else ("NO_COMMON_EPOCHS" if not rows else "DIFFERENT")
    )
    result = {
        "schema": "seedpar-checkpoint-equivalence-v1",
        "reference": str(args.reference), "candidate": str(args.candidate),
        "seed": args.seed, "epochs_compared": epochs, "pairs": rows, "verdict": verdict,
        "no_ee_quantity_computed": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    for r in rows:
        print(f"{r['epoch']:>5} ref {r['reference_sha256']} cand {r['candidate_sha256']} "
              f"{'IDENTICAL' if r['bytes_identical'] else 'DIFFERENT'}")
    print(f"VERDICT {verdict} ({len(rows)} pairs)")
    return 0 if verdict == "IDENTICAL" else 1


if __name__ == "__main__":
    sys.exit(main())
