#!/home/sat/mcrl-leo-handover/.venv/bin/python
"""OOSPANEL Step 1: mechanical disjointness of the OOS panel anchors.

Compares the declared OOS panel anchor list against every training corpus
anchor list found on the server:

* every ``launch-receipt.json`` under /home/sat/mcrl-v025-*/ (corpus.anchor_list);
* the EXACTGEN2 exact-source manifest (93 anchor_records);
* the sealed surrogate-label pilot corpora (per-shard anchor ids).

Key: (world_id, step_index, carrier).  Development anchors only; reads no
evaluation-only claim date.  Writes only out/disjointness.json.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oospanel as oos  # noqa: E402

EXACT_MANIFEST = Path("/home/sat/mcrl-v025-datepool-ws/artifacts/v025-exact-source-20260910-BUILD_NOT_CLAIM/BUILD_NOT_CLAIM-manifest.json")
PILOT_CORPORA = (
    Path("/home/sat/mcrl-v025-c1c2suff-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM"),
    Path("/home/sat/mcrl-v025-c1c2suff-ws/artifacts/v025-pilot-min-20260909-PILOT_NOT_CLAIM"),
    Path("/home/sat/mcrl-v025-selector-ws/artifacts/v025-pilot-c3-20260909-PILOT_NOT_CLAIM"),
    Path("/home/sat/mcrl-v025-selector-ws/artifacts/v025-pilot-min-20260909-PILOT_NOT_CLAIM"),
)
OUT = oos.WORKSPACE / "out/disjointness.json"


def key_of(world_id: str, step: int, carrier: str) -> tuple[str, int, str]:
    return (str(world_id), int(step), str(carrier))


def pilot_anchor_keys(root: Path) -> list[tuple[str, int, str]]:
    keys = set()
    for shard in sorted(root.glob("rows/world-*/*.jsonl")):
        with shard.open(encoding="ascii") as handle:
            next(handle)                      # shard header
            for line in handle:
                row = json.loads(line)
                anchor_id = row.get("anchor_id")
                if anchor_id is None:
                    continue
                world_id, step, carrier = anchor_id.split("|")
                keys.add(key_of(world_id, int(step), carrier.replace("BASE:", "")))
                break                          # one anchor per shard
    return sorted(keys)


def main() -> int:
    panel = oos.panel_specs()
    panel_keys = [key_of(s["world_id"], s["step_index"], s["carrier"]) for s in panel]
    if len(set(panel_keys)) != len(panel_keys):
        raise RuntimeError("panel anchors are not unique")
    corpora = []
    receipts = sorted(set(glob.glob("/home/sat/mcrl-v025-*/artifacts/*/launch-receipt.json")
                          + glob.glob("/home/sat/mcrl-v025-*/artifacts/*/*/launch-receipt.json")
                          + glob.glob("/home/sat/mcrl-v025-*/.scratch/*/launch-receipt.json")))
    for path in receipts:
        receipt = json.loads(Path(path).read_text(encoding="ascii"))
        anchors = (receipt.get("corpus") or {}).get("anchor_list")
        if not anchors:
            corpora.append({"name": path, "kind": "launch receipt", "anchor_list_present": False})
            continue
        if all(isinstance(a, str) for a in anchors):
            # synthetic fixture corpora list opaque source ids, not world anchors
            if any("V025_" in a for a in anchors):
                raise RuntimeError(f"unparsed world anchor strings in {path}")
            corpora.append({
                "name": path, "kind": "launch receipt corpus.anchor_list (synthetic fixture ids)",
                "anchor_list_present": True, "anchors": len(anchors), "keys": [],
                "fixture_ids": list(anchors),
                "q1_schema_sha256": receipt.get("feature_schema", {}).get("q1_schema_sha256"),
            })
            continue
        keys = [key_of(a["world_id"], a["step_index"], a["carrier"]) for a in anchors]
        corpora.append({
            "name": path, "kind": "launch receipt corpus.anchor_list",
            "anchor_list_present": True, "anchors": len(keys),
            "q1_schema_sha256": receipt.get("feature_schema", {}).get("q1_schema_sha256"),
            "global_ids": [a.get("global_anchor_index") for a in anchors],
            "keys": keys,
        })
    manifest = json.loads(EXACT_MANIFEST.read_text(encoding="ascii"))
    corpora.append({
        "name": str(EXACT_MANIFEST), "kind": "EXACTGEN2 exact-source manifest anchor_records",
        "anchor_list_present": True, "anchors": len(manifest["anchor_records"]),
        "global_ids": [r["global_anchor_index"] for r in manifest["anchor_records"]],
        "keys": [key_of(r["world_id"], r["step_index"], r["carrier"]) for r in manifest["anchor_records"]],
    })
    for root in PILOT_CORPORA:
        if not root.is_dir():
            continue
        keys = pilot_anchor_keys(root)
        corpora.append({"name": str(root), "kind": "sealed surrogate-label pilot corpus (shard anchor ids)",
                        "anchor_list_present": True, "anchors": len(keys), "keys": keys})
    panel_set = set(panel_keys)
    rows = []
    for corpus in corpora:
        if not corpus.get("anchor_list_present"):
            rows.append({k: v for k, v in corpus.items() if k != "keys"} | {"overlap": None})
            continue
        overlap = sorted(panel_set & set(corpus["keys"]))
        worlds = sorted({k[0] for k in corpus["keys"]})
        dates_shared = sorted({k[0] for k in overlap})
        rows.append({
            "name": corpus["name"], "kind": corpus["kind"], "anchors": corpus["anchors"],
            "q1_schema_sha256": corpus.get("q1_schema_sha256"),
            "worlds": worlds, "overlap": len(overlap), "overlap_keys": [list(k) for k in overlap],
            "shares_a_panel_world": sorted(set(worlds) & {k[0] for k in panel_keys}),
            "global_id_min_max": (
                [min(corpus["global_ids"]), max(corpus["global_ids"])] if corpus.get("global_ids") else None
            ),
        })
        _ = dates_shared
    named = {
        "22-anchor (exact22 launch receipt)": "/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-step-decay-16seed-4000-20260910/launch-receipt.json",
        "93-anchor (exact93 launch receipt)": "/home/sat/mcrl-v025-exact93-ws/artifacts/exact93-step-decay-16seed-4000-20260911/launch-receipt.json",
    }
    headline = {}
    for label, path in named.items():
        match = [row for row in rows if row["name"] == path]
        if len(match) != 1 or match[0]["overlap"] is None:
            raise RuntimeError(f"named training corpus not found: {path}")
        headline[label] = {"anchors": match[0]["anchors"], "overlap": match[0]["overlap"]}
    result = {
        "panel": [dict(s) for s in panel],
        "comparison_key": "(world_id, step_index, carrier)",
        "headline": headline,
        "max_overlap_any_corpus": max(row["overlap"] for row in rows if row["overlap"] is not None),
        "corpora": rows,
    }
    oos.streaming_json(OUT, result)
    for label, value in headline.items():
        print(label, value)
    for row in rows:
        print(row["overlap"], row.get("anchors"), row.get("worlds"), row["name"])
    print("MAX_OVERLAP_ANY_CORPUS", result["max_overlap_any_corpus"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
