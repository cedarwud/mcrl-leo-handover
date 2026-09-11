#!/usr/bin/env python3
"""SOLO Level 2 -- scoring-time route knockouts on trained FULL heads (IN-SAMPLE panels).

For each checkpoint, the FULL arm's deployed score is decomposed into its three
route contributions exactly as the unmodified scorer's _profile_score accumulates
them (C1 pairs, then C2 pairs, then C3 if coalition_size > 1).  ONLY_X keeps
route X's terms and sets the other two to exact zero; the empty subset is the
all-routes knockout (catalogue-order-0 BASE).  Catalogue order and the first
strict maximum tie rule are the scorer's.  The shared scorer is imported
read-only (SHA-256 checked) and never edited.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import resource
import sys
import time

SCORER = Path("/home/sat/mcrl-v025-selector-ws/scripts/score_stagec_checkpoints.py")
SCORER_SHA256 = "8a83bc9865fdbf665fe3815197059fc68c11efd73c319d96bcc412b5a8c5ed9d"
PYTHON = "/home/sat/mcrl-leo-handover/.venv/bin/python"
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS")
ROUTES = ("C1", "C2", "C3")
LATTICE = tuple(tuple(r for r, keep in zip(ROUTES, bits) if keep)
                for bits in itertools.product((0, 1), repeat=3))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def peak_rss() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def check_runtime():
    if sys.executable != PYTHON:
        raise RuntimeError("wrong interpreter")
    if os.getpriority(os.PRIO_PROCESS, 0) < 15:
        raise RuntimeError("niceness below 15")
    bad = {k: os.environ.get(k) for k in THREAD_VARS if os.environ.get(k) != "1"}
    if bad:
        raise RuntimeError(f"thread pins {bad}")
    if peak_rss() >= 5_000_000_000:
        raise MemoryError("peak RSS >= 5 GB")


def load_scorer():
    if sha256(SCORER) != SCORER_SHA256:
        raise RuntimeError("scorer bytes drifted")
    spec = importlib.util.spec_from_file_location("solo_shared_scorer", SCORER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["solo_shared_scorer"] = mod
    spec.loader.exec_module(mod)
    return mod


def name_of(subset):
    return "+".join(subset) if subset else "NONE"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--panel", required=True)
    ap.add_argument("--panel-receipt", required=True)
    ap.add_argument("--panel-sha256", required=True)
    ap.add_argument("--epoch", type=int, required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    check_runtime()
    out = Path(args.out)
    if out.exists():
        raise RuntimeError("refusing to overwrite output")
    scorer = load_scorer()
    run_dir = Path(args.run_dir)
    launch = json.loads((run_dir / "launch-receipt.json").read_text())
    prec = json.loads(Path(args.panel_receipt).read_text())
    fs, eb = launch["feature_schema"], prec["encoder_binding"]
    panel_path = Path(args.panel)
    panel_sha = sha256(panel_path)
    gate = {
        "q1_match": fs["q1_schema_sha256"] == eb["q1_schema_sha256"],
        "q2_match": fs["q2_schema_sha256"] == eb["q2_schema_sha256"],
        "panel_sha_match": panel_sha == args.panel_sha256 == prec["panel_sha256"],
        "q1_schema_sha256": fs["q1_schema_sha256"], "q2_schema_sha256": fs["q2_schema_sha256"],
        "panel_sha256": panel_sha,
    }
    if not (gate["q1_match"] and gate["q2_match"] and gate["panel_sha_match"]):
        raise RuntimeError(f"schema/panel gate failed: {gate}")
    ep = f"{args.epoch:06d}"
    ck_paths = []
    missing = []
    for seed in launch["seed_list"]:
        p = run_dir / "checkpoints" / f"learner-{seed}-epoch-{ep}.json"
        if p.exists():
            want = (p.with_name(p.name + ".sha256")).read_text().split()[0]
            got = sha256(p)
            if want != got:
                raise RuntimeError(f"sidecar mismatch {p}")
            ck_paths.append(p)
        else:
            missing.append(seed)
    print(f"{args.tag}: {len(ck_paths)} checkpoints at epoch {args.epoch}; missing seeds {len(missing)}", flush=True)
    if not ck_paths:
        raise RuntimeError("no checkpoints at requested epoch")
    first = scorer._load_checkpoint(ck_paths[0])
    widths = first["widths"]
    panel = scorer._validate_panel(scorer._read_json(panel_path), widths, panel_path)
    anchors = panel["anchors"]
    print(f"panel loaded: {len(anchors)} anchors peak RSS {peak_rss()/2**30:.3f} GiB", flush=True)
    results = []
    for ci, path in enumerate(ck_paths, 1):
        ck = first if ci == 1 else scorer._load_checkpoint(path)
        if ck["widths"] != widths:
            raise RuntimeError("width drift across checkpoints")
        model = ck["models"]["FULL"]
        sel_outcomes = {name_of(s): [] for s in LATTICE}
        sel_ids = {name_of(s): [] for s in LATTICE}
        full_verify_mismatch = 0
        base_check_fail = 0
        for ai, anchor in enumerate(anchors, 1):
            profiles = anchor["profiles"]
            terms = []
            for prof in profiles:
                t = {}
                for route in ("C1", "C2"):
                    t[route] = [model[route].score(pair["selected"]) - model[route].score(pair["reference"])
                                for pair in prof[route]]
                t["C3"] = [model["C3"].score(prof["C3"]["invariant_state"])] if prof["C3"]["coalition_size"] > 1 else []
                terms.append(t)
            for subset in LATTICE:
                best_i, best_s = 0, None
                for i, t in enumerate(terms):
                    total = 0.0
                    for route in ROUTES:           # scorer accumulation order
                        if route in subset:
                            for value in t[route]:
                                total += value
                    if best_s is None or total > best_s:
                        best_i, best_s = i, total
                sel_outcomes[name_of(subset)].append(profiles[best_i]["outcome"])
                sel_ids[name_of(subset)].append(profiles[best_i]["profile_id"])
            # verification against the unmodified scorer's own FULL selection and knockout
            full = scorer._select(model, profiles)
            if full["profile_id"] != sel_ids["C1+C2+C3"][-1]:
                full_verify_mismatch += 1
            ko = scorer._select(model, profiles, knockout_all=True)
            if ko["profile_id"] != sel_ids["NONE"][-1] or ko["profile_id"] != anchor["base_profile_id"]:
                base_check_fail += 1
        pools = {k: scorer._pool(v) for k, v in sel_outcomes.items()}
        none_ee = pools["NONE"]["pooled_ee_bits_per_j"]
        rows = {}
        for k, pl in pools.items():
            rows[k] = {
                "pooled_ee_mbit_per_j": pl["pooled_ee_bits_per_j"] / 1e6,
                "relative_vs_NONE": (pl["pooled_ee_bits_per_j"] - none_ee) / none_ee,
                "bits": pl["full_buffer_bits"], "joules": pl["joules"],
                "served": pl["service_available"], "service_opportunities": pl["service_opportunities"],
                "rate_target_attained": pl["rate_target_attained"],
                "rate_target_opportunities": pl["rate_target_opportunities"],
                "handovers": pl["handovers"],
                "anchors_differing_from_NONE": sum(a != b for a, b in zip(sel_ids[k], sel_ids["NONE"])),
                "selected_profile_ids": sel_ids[k],
            }
        results.append({
            "checkpoint": ck["path"], "checkpoint_sha256": ck["sha256"], "learner_seed": ck["learner_seed"],
            "completed_source_epochs": ck["completed_source_epochs"],
            "full_selection_mismatch_vs_unmodified_scorer": full_verify_mismatch,
            "knockout_base_check_failures": base_check_fail, "lattice": rows,
        })
        check_runtime()
        print(f"checkpoint {ci}/{len(ck_paths)} seed={ck['learner_seed']} "
              + " ".join(f"{k}={rows[k]['pooled_ee_mbit_per_j']:.4f}" for k in rows)
              + f" fullmismatch={full_verify_mismatch} peak RSS {peak_rss()/2**30:.3f} GiB", flush=True)
    payload = {
        "schema": "mcrl-v025-solo-level2-knockout-v1", "label": "IN-SAMPLE",
        "tag": args.tag, "run_dir": str(run_dir), "epoch": args.epoch,
        "launch_receipt_sha256": sha256(run_dir / "launch-receipt.json"),
        "training_schedule": launch.get("training_schedule"), "gate": gate,
        "panel": str(panel_path), "panel_anchor_ids": [a["anchor_id"] for a in anchors],
        "missing_seeds_at_epoch": missing, "checkpoints": results,
        "scorer": str(SCORER), "scorer_sha256": SCORER_SHA256,
        "script_sha256": sha256(Path(__file__)), "peak_rss_bytes": peak_rss(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, sort_keys=True, indent=1) + "\n")
    print(f"DONE {args.tag} PEAK_RSS_BYTES={peak_rss()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
