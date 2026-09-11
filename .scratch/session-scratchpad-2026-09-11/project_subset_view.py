#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""Emit any added-field subset as a view by column projection of the 'both' view.

No physics, labels or geometry are read: only the 'both' corpus.  Q1 vectors
(source rows and both member vectors of every coalition row) are projected by
the family's index list; the row's q1_schema_sha256 becomes the subset digest;
visible_primitives_sha256 becomes a projection lineage over the parent row's
digest; every other field is copied unchanged and checked.

usage: project_subset_view.py <out_dir> <added_field> [<added_field> ...]  (or 'NONE')
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import sys

ROOT = Path("/home/sat/mcrl-v025-q1v4-ws")
FAMILY = ROOT / "artifacts/q1v4-schema-family.json"
RECEIPT = ROOT / "artifacts/q1v4-build-verification.json"
BOTH_DIGEST_KEY = "both"


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str]) -> int:
    if os.getpriority(os.PRIO_PROCESS, 0) < 16:
        raise RuntimeError("niceness below 16")
    out = Path(argv[0]).resolve()
    if not str(out).startswith(str(ROOT / "artifacts")) or out.exists():
        raise RuntimeError("output must be a new directory under the q1v4 workspace artifacts")
    added = [] if argv[1:] == ["NONE"] else argv[1:]
    family = json.loads(FAMILY.read_text())
    receipt = json.loads(RECEIPT.read_text())
    match = [e for e in family["all_subsets"] if e["added_fields"] == added]
    if len(match) != 1:
        raise RuntimeError(f"not a canonical-order subset: {added}")
    entry = match[0]
    indices, digest = entry["projection_indices_into_stored_vector"], entry["q1_schema_sha256"]
    both = Path(receipt["named_subsets"][BOTH_DIGEST_KEY]["corpus_root"])
    both_digest = receipt["named_subsets"][BOTH_DIGEST_KEY]["q1_schema_sha256"]
    files = sorted(p for p in (both / "views").rglob("*.jsonl"))
    inventory = []
    for path in files:
        sidecar = path.with_suffix(".jsonl.sha256").read_text().split()
        raw = path.read_bytes()
        if sidecar[0] != sha_bytes(raw):
            raise RuntimeError(f"both-view sidecar mismatch: {path}")
        inventory.append({"path": path.relative_to(both).as_posix(), "sha256": sidecar[0]})
        lines = [json.loads(line) for line in raw.splitlines()]
        header, rows = lines[0], lines[1:]
        if header["schema"] == "mcrl-v025-exact-source-view-shard-v1":
            new_rows = []
            for row in rows:
                if row["q1_schema_sha256"] != both_digest or len(row["q1_state"]) != 19:
                    raise RuntimeError("parent is not the v4 'both' view")
                child = dict(row)
                child["q1_state"] = [row["q1_state"][i] for i in indices]
                child["q1_schema_sha256"] = digest
                child["visible_primitives_sha256"] = sha_bytes(canonical({
                    "schema": "mcrl-v025-stagec-q1-v4-projection-lineage-v1",
                    "parent_both_visible_primitives_sha256": row["visible_primitives_sha256"],
                    "added_fields": added, "projection_indices": indices}))
                new_rows.append(child)
            new_header = {**header, "q1_slots": entry["q1_width"]}
        else:
            new_rows = []
            for row in rows:
                child = json.loads(json.dumps(row))
                for member in child["context"]["members"]:
                    for key in ("selected_q1_row_hex", "incumbent_q1_row_hex"):
                        if len(member[key]) != 19:
                            raise RuntimeError("coalition member vector is not v4 'both'")
                        member[key] = [member[key][i] for i in indices]
                new_rows.append(child)
            new_header = {**header,
                          "context_payloads_sha256": sha_bytes(canonical([r["context"] for r in new_rows])),
                          "rows_sha256": sha_bytes(canonical(new_rows))}
        destination = out / path.relative_to(both)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = b"".join(canonical(v) + b"\n" for v in [new_header, *new_rows])
        destination.write_bytes(payload)
        destination.with_suffix(".jsonl.sha256").write_text(f"{sha_bytes(payload)}  {destination.name}\n")
    if sha_bytes(canonical(inventory)) != receipt["named_subsets"][BOTH_DIGEST_KEY]["corpus_digest"]:
        raise RuntimeError("the 'both' view drifted from its build receipt")
    out_inventory = [{"path": p.relative_to(out).as_posix(), "sha256": sha_bytes(p.read_bytes())}
                     for p in sorted((out / "views").rglob("*.jsonl"))]
    print(json.dumps({"subset_added_fields": added, "q1_schema_sha256": digest, "q1_width": entry["q1_width"],
                      "c3_width": entry["c3_width"], "corpus_digest": sha_bytes(canonical(out_inventory)),
                      "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
