#!/usr/bin/env python3
"""CONVSCORE step 1: train/score anchor overlap check.

Reads (never writes) training launch receipts, training corpus view files,
panel construction receipts and panel JSON files. Writes one JSON result into
this workspace's out/ directory.
"""
import gc
import hashlib
import json
import resource
import sys
from pathlib import Path

WS = Path("/home/sat/mcrl-v025-convscore-ws")

RUNS = {
    # new, converged-schedule, exact-label runs
    "exact22": "/home/sat/mcrl-v025-exacttrain-ws/artifacts/exact-label-step-decay-16seed-4000-20260910",
    "q1v3": "/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-step-decay-16seed-4000-20260910",
    "q1v3_control": "/home/sat/mcrl-v025-q1v3-ws/artifacts/q1-v3-control-step-decay-16seed-4000-20260910",
    # earlier surrogate-label runs scored in Z-VIEW-SCORING-2026-09-10.md
    "zscore_q1v1": "/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z",
    "zscore_q1v2": "/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z",
    "zscore_q1v2z": "/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z",
}

PANELS = {
    "panel-q1v1": ("/home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v1.json",
                   "/home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v1.receipt.json"),
    "panel-q1v2": ("/home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v2.json",
                   "/home/sat/mcrl-v025-panelfix-ws/artifacts/panel-q1v2.receipt.json"),
    "panel-q1v3": ("/home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3.json",
                   "/home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3.receipt.json"),
    "panel-q1v3-control": ("/home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3-control.json",
                           "/home/sat/mcrl-v025-panelv3-ws/artifacts/panel-q1v3-control.receipt.json"),
    "panel-q1v2z": (None, None),  # located below from the Z-scoring logs if present
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def key(world, step, carrier):
    return f"{world}|{int(step)}|{carrier}"


def run_anchors(run_dir):
    rec = json.load(open(Path(run_dir) / "launch-receipt.json"))
    corpus = rec["corpus"]
    receipt_keys = [key(a["world_id"], a["step_index"], a["carrier"]) for a in corpus["anchor_list"]]
    gidx = [a["global_anchor_index"] for a in corpus["anchor_list"]]
    # Independently read the header + first data row of every source view file the
    # receipt binds, and check its sha256 against the receipt.
    root = Path(corpus["root"])
    file_rows = []
    sha_ok = 0
    sha_bad = []
    view_sha_by_key = {}
    for f in corpus["files"]:
        p = root / f["path"]
        actual = sha256(p)
        if actual == f["sha256"]:
            sha_ok += 1
        else:
            sha_bad.append(str(p))
        if "exact-source-anchor" not in f["path"]:
            continue
        with open(p) as fh:
            header = json.loads(fh.readline())
            first = json.loads(fh.readline())
            n_data = 1 + sum(1 for _ in fh)
        k = key(header["world_id"], header["step_index"], header["carrier"])
        file_rows.append({
            "path": str(p), "sha256": actual, "header_key": k,
            "global_anchor_index": header.get("global_anchor_index"),
            "first_row_anchor_id": first.get("anchor_id"),
            "first_row_decision_time_utc": first.get("decision_time_utc"),
            "header_row_count": header.get("row_count"), "data_rows": n_data,
        })
        view_sha_by_key[k] = actual
    return {
        "run_dir": run_dir,
        "launch_receipt_sha256": sha256(Path(run_dir) / "launch-receipt.json"),
        "feature_schema": rec["feature_schema"],
        "corpus_digest": corpus["digest"], "corpus_root": corpus["root"],
        "corpus_mode": corpus["mode"],
        "source_rows": corpus["source_rows"], "coalition_rows": corpus["coalition_rows"],
        "epochs": rec.get("epochs"), "training_schedule": rec.get("training_schedule"),
        "seed_list": rec.get("seed_list"),
        "receipt_anchor_keys": receipt_keys, "receipt_global_anchor_index": gidx,
        "corpus_file_sha_matches_receipt": f"{sha_ok}/{len(corpus['files'])}",
        "corpus_file_sha_mismatch": sha_bad,
        "source_view_files": file_rows,
        "view_sha_by_key": view_sha_by_key,
    }


def panel_anchors(panel_path, receipt_path):
    rec = json.load(open(receipt_path))
    enc = rec.get("encoder_binding", {})
    srcs = rec["run_identity"]["sources"]
    rec_keys = [key(s["world_id"], s["step_index"], s["carrier"]) for s in srcs]
    src_view = {key(s["world_id"], s["step_index"], s["carrier"]): (s.get("view_path"), s.get("view_sha256"))
                for s in srcs}
    panel_sha = sha256(panel_path)
    d = json.load(open(panel_path))
    anchors = []
    for a in d["anchors"]:
        anchors.append({
            "anchor_id": a["anchor_id"], "date": a.get("date"),
            "n_profiles": len(a.get("profiles", [])),
            **{k: a.get(k) for k in ("global_anchor_index", "world_id", "step_index", "carrier", "seed") if k in a},
        })
    top_keys = sorted(k for k in d.keys() if k != "anchors")
    top = {k: d[k] for k in top_keys if not isinstance(d[k], (list, dict)) or len(json.dumps(d[k])) < 400}
    del d
    gc.collect()
    return {
        "panel": panel_path, "panel_sha256": panel_sha,
        "receipt": receipt_path, "receipt_panel_sha256": rec.get("panel_sha256"),
        "encoder_binding": enc,
        "receipt_anchor_keys": rec_keys,
        "panel_anchor_ids": [a["anchor_id"] for a in anchors],
        "panel_anchor_meta": anchors,
        "panel_top_level_small_fields": top,
        "source_view_by_key": src_view,
    }


def main():
    out = {"runs": {}, "panels": {}, "overlap": {}}
    for name, rd in RUNS.items():
        print("run", name, flush=True)
        out["runs"][name] = run_anchors(rd)
    # locate the z panel from the Z-scoring workspace logs / scripts
    zp = Path("/home/sat/mcrl-v025-panelz-ws/artifacts/panel-q1v2z.json")
    zr = Path("/home/sat/mcrl-v025-panelz-ws/artifacts/panel-q1v2z.receipt.json")
    if zp.exists() and zr.exists():
        PANELS["panel-q1v2z"] = (str(zp), str(zr))
    else:
        del PANELS["panel-q1v2z"]
    for name, (pp, rp) in PANELS.items():
        print("panel", name, flush=True)
        out["panels"][name] = panel_anchors(pp, rp)
    # schema-digest pairing (never by width)
    pairing = {}
    for rn, r in out["runs"].items():
        fs = r["feature_schema"]
        matches = [pn for pn, p in out["panels"].items()
                   if p["encoder_binding"].get("q1_schema_sha256") == fs["q1_schema_sha256"]
                   and p["encoder_binding"].get("q2_schema_sha256") == fs["q2_schema_sha256"]]
        pairing[rn] = matches
    out["schema_digest_pairing"] = pairing
    # overlap: every run vs every panel (anchor identity = world|step|carrier)
    for rn, r in out["runs"].items():
        tr = set(r["receipt_anchor_keys"])
        tr_files = set(f["header_key"] for f in r["source_view_files"])
        for pn, p in out["panels"].items():
            pk = set(p["panel_anchor_ids"])
            prk = set(p["receipt_anchor_keys"])
            ov = sorted(tr & pk)
            same_file = [k for k in ov
                         if p["source_view_by_key"].get(k, (None, None))[1] is not None
                         and p["source_view_by_key"][k][1] == r["view_sha_by_key"].get(k)]
            out["overlap"][f"{rn}__{pn}"] = {
                "train_anchors": len(tr), "panel_anchors": len(pk),
                "overlap_count": len(ov),
                "overlap_via_corpus_file_headers": len(tr_files & pk),
                "panel_receipt_keys_equal_panel_ids": prk == pk,
                "panel_only": sorted(pk - tr), "train_only": sorted(tr - pk),
                "panel_view_file_sha_equals_training_view_file_sha": len(same_file),
            }
    for r in out["runs"].values():
        r.pop("view_sha_by_key")
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    out["peak_rss_bytes"] = peak
    dst = WS / "out" / "leakage-check.json"
    dst.write_text(json.dumps(out, indent=1, sort_keys=True))
    print("WROTE", dst, sha256(dst))
    for k, v in out["overlap"].items():
        print(k, v["overlap_count"], "/", v["panel_anchors"], "same_view_file", v["panel_view_file_sha_equals_training_view_file_sha"],
              "panel_only", v["panel_only"], "train_only", v["train_only"])
    print("pairing", json.dumps(pairing))
    print(f"PEAK_RSS_BYTES={peak}")


if __name__ == "__main__":
    sys.exit(main())
