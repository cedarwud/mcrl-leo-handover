"""CF3PILOT pool provenance re-verification (run at evaluation time; no training).

Checks, failing loudly (exit 1) on any mismatch:
* every pool sidecar ``.json`` and ``.npz`` still has the sha256 recorded in
  ``POOL-SIDECAR-HASHES.json`` (written 11:2x UTC, after launch, before any result);
* every ``.npz`` hash equals the run root's ``RUN-MANIFEST.json`` entry;
* for every A2/A3 run: each loaded pool (status fingerprint ``pool_sha256``)
  is the sidecar's pool, and the sidecar's kind / head / source_index /
  seed_index match what that run should load, with transitions == 100000.

Usage: cf3_verify_pools.py --pools DIR --root DIR --out FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HEADS = {"C1_A_m2dB": 0, "C2_A_m12dB": 2, "C3_B1_NO_NEW_BEAM": 1}
SPECS = [("C1_A_m2dB", 0), ("C2_A_m12dB", 2), ("C3_B1_NO_NEW_BEAM", 1)]


def names(kind):
    if kind == "cf3":
        return SPECS
    return [(f"NULL{j + 1}_for_{n}", h) for j, (n, h) in enumerate(SPECS)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pools", type=Path, required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rec = json.loads((a.pools / "POOL-SIDECAR-HASHES.json").read_text())
    man = json.loads((a.root / "RUN-MANIFEST.json").read_text())
    errors, checked = [], 0
    for rel, h in rec["pools"].items():
        side, npz = a.pools / rel, a.pools / (rel[:-5] + ".npz")
        if sha(side) != h["sidecar_sha256"]:
            errors.append(f"sidecar hash changed: {rel}")
        if sha(npz) != h["npz_sha256"]:
            errors.append(f"npz hash changed: {rel}")
        if man["pools"].get(rel[:-5] + ".npz") != h["npz_sha256"]:
            errors.append(f"npz not in RUN-MANIFEST with recorded hash: {rel}")
    for arm, kind in (("A2", "cf3"), ("A3", "null3")):
        for k in (0, 1, 2):
            st = json.loads((a.root / f"{arm}-{'CF3' if arm == 'A2' else 'NULL3'}-s{k}"
                             / "status.json").read_text())
            loaded = st["fingerprint"]["pool_sha256"]
            for j, (name, head) in enumerate(names(kind)):
                rel = f"s{k}/{name}.json"
                m = json.loads((a.pools / rel).read_text())
                want = {"kind": kind, "head": head, "source_index": j, "seed_index": k,
                        "transitions": 100000, "name": name}
                got = {key: m.get(key) for key in want}
                if got != want:
                    errors.append(f"{arm}s{k} {rel}: sidecar {got} != expected {want}")
                if loaded.get(name) != m["pool_sha256"] or m["pool_sha256"] != rec["pools"][rel]["npz_sha256"]:
                    errors.append(f"{arm}s{k} loaded {name} {loaded.get(name)} != sidecar {m['pool_sha256']}")
                checked += 1
    out = {"ok": not errors, "errors": errors, "pools_checked": len(rec["pools"]),
           "run_pool_bindings_checked": checked,
           "record_sha256": sha(a.pools / "POOL-SIDECAR-HASHES.json")}
    a.out.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
