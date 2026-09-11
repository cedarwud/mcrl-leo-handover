#!/usr/bin/env python3
"""Q-row collinearity and penultimate effective-rank diagnostic for V0.25 Stage-C.

Read-only.  Reads only the 22 TRAIN development anchors named by each live
training run's launch receipt and the frozen epoch-500 checkpoints.  It never
discovers or opens an evaluation shard, and never writes into a training
output directory.

Instruments are the sibling project's own module, imported verbatim from
ref/penalties.py:
  * q_row_decorrelation_penalty(Q)  -> mean |off-diagonal Pearson| of user rows
  * mean_offdiag_row_pearson_torch  -> signed variant (the NumPy readout)
  * srank_diagnostic(Phi, 0.01)     -> Kumar effective rank on MEAN-CENTERED Phi
  * srank_penalty(Phi)              -> Kumar Eq.(6) sigma_max^2 - sigma_min^2 on RAW Phi
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import importlib.util
import json
import math
from hashlib import sha256
from pathlib import Path
import resource
import statistics
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import torch

WORKSPACE = Path("/home/sat/mcrl-v025-rawdup-ws")
REF = WORKSPACE / "ref" / "penalties.py"

RUNS = (
    {
        "name": "v1-nonz",
        "label": "Q1 v1 (non-z)",
        "directory": Path("/home/sat/mcrl-v025-retrain-ws/artifacts/firstrun-500ep-20260910T1355Z"),
        "corpus_digest": "23814e63d9300fe049bd730897b7e07ef880e5fe21f7a5624c1fee4a9d5eb20c",
    },
    {
        "name": "v2-nonz",
        "label": "Q1 v2 (non-z)",
        "directory": Path("/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2-500ep-20260910T1425Z"),
        "corpus_digest": "ab81d942993d005e6eab964e4e1011a8b85cfed49d47fac7448a39e729514016",
    },
    {
        "name": "v2z",
        "label": "Q1 v2z (live cross-user z view)",
        "directory": Path("/home/sat/mcrl-v025-design-ws/artifacts/firstrun-v2z-500ep-20260910T1512Z"),
        "corpus_digest": "ef3dc0c66b89b185b9395b1d9f2e063319de1e24014123594cb2ef902278af31",
    },
    {
        "name": "v2d",
        "label": "Q1 v2d (raw || verbatim raw duplicate; width control)",
        "directory": Path("/home/sat/mcrl-v025-rawdup-ws/artifacts/firstrun-v2d-500ep-20260910T1900Z"),
        "corpus_digest": "a3ae7fcd49124d1a591a849f1eaaf1dceceb52ff3d2c6c623d35ba1f0fcbb206",
    },
)

EXPECTED_ANCHORS = 22
EXPECTED_USERS = 100
TARGET_EPOCH = 500
ARM = "FULL"


class ProbeFailure(RuntimeError):
    pass


def load_ref() -> Any:
    spec = importlib.util.spec_from_file_location("sibling_penalties", REF)
    if spec is None or spec.loader is None:
        raise ProbeFailure("cannot import sibling penalties module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P = load_ref()


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verified_json(path: Path) -> dict[str, Any]:
    encoded = path.read_bytes()
    actual = sha256(encoded).hexdigest()
    sidecar = path.with_name(path.name + ".sha256")
    if sidecar.is_file():
        fields = sidecar.read_text(encoding="ascii").split()
        if not fields or fields[0] != actual:
            raise ProbeFailure(f"SHA-256 sidecar mismatch: {path}")
    value = json.loads(encoded)
    if not isinstance(value, dict):
        raise ProbeFailure(f"JSON root is not an object: {path}")
    return value, actual


def hexf(values: Sequence[str]) -> list[float]:
    return [float.fromhex(str(v)) for v in values]


def load_anchor_tables(receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return per-anchor packed arrays.  TRAIN development anchors only."""
    corpus = receipt["corpus"]
    root = Path(corpus["root"])
    source_files = [row for row in corpus["files"] if "exact-source" in str(row["path"])]
    if len(source_files) != EXPECTED_ANCHORS:
        raise ProbeFailure("launch receipt does not name exactly 22 source shards")
    anchors: dict[str, dict[str, Any]] = {}
    total_rows = 0
    for binding in source_files:
        path = (root / Path(binding["path"])).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ProbeFailure("source shard escapes launch-receipt corpus root")
        if file_sha256(path) != binding["sha256"]:
            raise ProbeFailure(f"source shard digest mismatch: {path}")
        lines = path.read_bytes().splitlines()
        header = json.loads(lines[0])
        material = [json.loads(line) for line in lines[1:]]
        if header.get("row_count") != len(material):
            raise ProbeFailure(f"source shard row count mismatch: {path}")
        total_rows += len(material)
        by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
        anchor_ids = set()
        for row in material:
            if row.get("split") != "TRAIN":
                raise ProbeFailure("probe encountered a non-TRAIN row")
            if row.get("world_id") != "V025_PROBE/world/1":
                raise ProbeFailure("probe encountered a non-development world")
            anchor_ids.add(str(row["anchor_id"]))
            by_user[int(row["user_id"])].append(row)
        if len(anchor_ids) != 1:
            raise ProbeFailure(f"shard is not a single anchor: {path}")
        anchor_id = anchor_ids.pop()
        if set(by_user) != set(range(EXPECTED_USERS)):
            raise ProbeFailure(f"anchor roster mismatch: {anchor_id}")

        user_of: list[int] = []
        slot_of: list[int] = []
        legal_of: list[bool] = []
        null_of: list[bool] = []
        q1_rows: list[list[float]] = []
        q2_rows: list[list[float]] = []
        slots_per_user: list[int] = []
        legal_per_user: list[int] = []
        null_slot_per_user: list[int] = []
        for user in range(EXPECTED_USERS):
            ordered = sorted(by_user[user], key=lambda r: int(r["action_index"]))
            indices = tuple(int(r["action_index"]) for r in ordered)
            if indices != tuple(range(len(ordered))):
                raise ProbeFailure(f"non-contiguous action indices: {anchor_id}, user {user}")
            masks = {tuple(bool(v) for v in r["action_mask"]) for r in ordered}
            if len(masks) != 1 or len(next(iter(masks))) != len(ordered):
                raise ProbeFailure(f"action mask mismatch: {anchor_id}, user {user}")
            mask = next(iter(masks))
            if sum(bool(r["reference_action"]) for r in ordered) != 1:
                raise ProbeFailure(f"BASE multiplicity mismatch: {anchor_id}, user {user}")
            slots_per_user.append(len(ordered))
            legal_per_user.append(sum(mask))
            nulls = [i for i, r in enumerate(ordered) if bool(r["null_action"])]
            null_slot_per_user.append(nulls[0] if len(nulls) == 1 else -1)
            for slot, r in enumerate(ordered):
                user_of.append(user)
                slot_of.append(slot)
                legal_of.append(mask[slot])
                null_of.append(bool(r["null_action"]))
                q1_rows.append(hexf(r["q1_state"]))
                q2_rows.append(hexf(r["q2_state"]))
        anchors[anchor_id] = {
            "user": np.asarray(user_of, dtype=np.int32),
            "slot": np.asarray(slot_of, dtype=np.int32),
            "legal": np.asarray(legal_of, dtype=bool),
            "null": np.asarray(null_of, dtype=bool),
            "q1": np.asarray(q1_rows, dtype=np.float64),
            "q2": np.asarray(q2_rows, dtype=np.float64),
            "slots_per_user": slots_per_user,
            "legal_per_user": legal_per_user,
            "null_slot_per_user": null_slot_per_user,
            "shard": str(path),
            "shard_sha256": binding["sha256"],
        }
    if total_rows != int(corpus["source_rows"]):
        raise ProbeFailure("source-row total disagrees with launch receipt")
    if len(anchors) != EXPECTED_ANCHORS:
        raise ProbeFailure("corpus does not contain exactly 22 anchors")
    return anchors


def decode_head(head: Mapping[str, Any]) -> tuple[list[np.ndarray], list[np.ndarray], str]:
    weights = [np.asarray([[float.fromhex(str(c)) for c in row] for row in layer], dtype=np.float64)
               for layer in head["weights_hex"]]
    biases = [np.asarray([float.fromhex(str(c)) for c in layer], dtype=np.float64)
              for layer in head["biases_hex"]]
    return weights, biases, str(head["activation"])


def forward(head: tuple[list[np.ndarray], list[np.ndarray], str], states: np.ndarray):
    """Return (scores (n,), penultimate Phi (n, hidden))."""
    weights, biases, activation = head
    current = np.asarray(states, dtype=np.float64)
    phi = None
    for index, (w, b) in enumerate(zip(weights, biases, strict=True)):
        if index == len(weights) - 1:
            phi = current
            current = current @ w + b
        else:
            pre = current @ w + b
            current = np.maximum(pre, 0.0) if activation == "relu" else np.tanh(pre)
    if current.shape[1] != 1:
        raise ProbeFailure("head output is not scalar")
    return current[:, 0], phi


def checkpoint_inventory(directory: Path) -> list[dict[str, Any]]:
    found: dict[int, list[int]] = defaultdict(list)
    selected: list[dict[str, Any]] = []
    for path in sorted((directory / "checkpoints").glob("learner-*-epoch-*.json")):
        stem = path.name.removesuffix(".json")
        learner_text, epoch_text = stem.removeprefix("learner-").split("-epoch-")
        seed, epoch = int(learner_text), int(epoch_text)
        found[seed].append(epoch)
        if epoch == TARGET_EPOCH:
            selected.append({"seed": seed, "epoch": epoch, "path": path})
    if not selected:
        raise ProbeFailure(f"no epoch-{TARGET_EPOCH} checkpoints in {directory}")
    return sorted(selected, key=lambda r: r["seed"]), {str(k): sorted(v) for k, v in sorted(found.items())}


# ---------------------------------------------------------------- estimators


def complete_block(matrix: np.ndarray) -> np.ndarray:
    """Rows of `matrix` (users x slots, NaN = absent/illegal) with no NaN."""
    keep = ~np.isnan(matrix).any(axis=1)
    return matrix[keep], int(keep.sum())


def sibling_pearson(block: np.ndarray) -> tuple[float, float, int]:
    """Sibling module, verbatim, on a complete (users x slots) block."""
    t = torch.from_numpy(np.ascontiguousarray(block))
    absolute = float(P.q_row_decorrelation_penalty(t).item())
    signed = float(P.mean_offdiag_row_pearson_torch(t, absolute=False).item())
    off = P._row_pearson_offdiag(t)
    return absolute, signed, int(off.numel())


def pairwise_complete_pearson(matrix: np.ndarray) -> tuple[float, float, int, int]:
    """Mean |off-diag Pearson| over every user pair, using each pair's common
    defined slots.  Identical to the sibling function when no slot is absent."""
    rows = matrix.shape[0]
    values: list[float] = []
    dropped = 0
    defined = ~np.isnan(matrix)
    for i in range(rows):
        for j in range(i + 1, rows):
            common = defined[i] & defined[j]
            n = int(common.sum())
            if n < 2:
                dropped += 1
                continue
            a = matrix[i, common]
            b = matrix[j, common]
            a = a - a.mean()
            b = b - b.mean()
            na = math.sqrt(float(a @ a))
            nb = math.sqrt(float(b @ b))
            if na <= 0.0 or nb <= 0.0:
                dropped += 1
                continue
            values.append(float(a @ b) / (na * nb))
    if len(values) < 1:
        return float("nan"), float("nan"), 0, dropped
    arr = np.asarray(values)
    return float(np.abs(arr).mean()), float(arr.mean()), len(values), dropped


def spectra(phi: np.ndarray) -> dict[str, Any]:
    t = torch.from_numpy(np.ascontiguousarray(phi))
    srank = int(P.srank_diagnostic(t, delta=0.01))
    penalty = float(P.srank_penalty(t).item())
    with torch.no_grad():
        s_raw = torch.linalg.svdvals(t)
        c = t - t.mean(dim=0, keepdim=True)
        s_cen = torch.linalg.svdvals(c)
    return {
        "srank_diagnostic_centered": srank,
        "hidden_width": int(phi.shape[1]),
        "srank_fraction_of_hidden": srank / int(phi.shape[1]),
        "srank_penalty_raw_smax2_minus_smin2": penalty,
        "sigma_max_raw": float(s_raw[0].item()),
        "sigma_min_raw": float(s_raw[-1].item()),
        "sigma_max_centered": float(s_cen[0].item()),
        "sigma_min_centered": float(s_cen[-1].item()),
        "batch_rows": int(phi.shape[0]),
    }


def summarize(values: Sequence[float]) -> dict[str, Any]:
    clean = [float(v) for v in values if not (isinstance(v, float) and math.isnan(v))]
    nan_count = len(values) - len(clean)
    if not clean:
        return {"n": 0, "nan": nan_count, "mean": float("nan"), "min": float("nan"), "max": float("nan")}
    return {
        "n": len(clean),
        "nan": nan_count,
        "mean": statistics.fmean(clean),
        "min": min(clean),
        "max": max(clean),
        "sd": statistics.pstdev(clean) if len(clean) > 1 else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--runs", default="")
    args = parser.parse_args()

    wanted = set(args.runs.split(",")) if args.runs else None
    report: dict[str, Any] = {
        "schema": "mcrl-v025-qcollinear-diagnostic-v1",
        "instrument_source": str(REF),
        "instrument_sha256": file_sha256(REF),
        "arm": ARM,
        "target_epoch": TARGET_EPOCH,
        "runs": {},
    }

    for run in RUNS:
        if wanted and run["name"] not in wanted:
            continue
        receipt_path = run["directory"] / "launch-receipt.json"
        receipt, receipt_sha = verified_json(receipt_path)
        if receipt["corpus"]["digest"] != run["corpus_digest"]:
            raise ProbeFailure(f"corpus digest mismatch for {run['name']}")
        print(f"[{run['name']}] loading source corpus ...", flush=True)
        anchors = load_anchor_tables(receipt)
        anchor_ids = sorted(anchors)
        checkpoints, epoch_inventory = checkpoint_inventory(run["directory"])
        print(f"[{run['name']}] {len(anchors)} anchors, {len(checkpoints)} epoch-{TARGET_EPOCH} checkpoints", flush=True)

        cells: list[dict[str, Any]] = []
        for ck in checkpoints:
            payload, ck_sha = verified_json(ck["path"])
            if set(payload.get("arms", {})) != {"FULL", "DROP_C1", "DROP_C2", "DROP_C3", "ALL_NEUTRAL_CONTROL"}:
                raise ProbeFailure(f"checkpoint arm inventory mismatch: {ck['path']}")
            if int(payload.get("completed_source_epochs", -1)) != TARGET_EPOCH:
                raise ProbeFailure(f"checkpoint epoch mismatch: {ck['path']}")
            if int(payload.get("learner_seed", -1)) != ck["seed"]:
                raise ProbeFailure(f"checkpoint seed mismatch: {ck['path']}")
            model = payload["arms"][ARM]
            c1 = decode_head(model["C1"])
            c2 = decode_head(model["C2"])
            del payload
            for anchor_id in anchor_ids:
                tab = anchors[anchor_id]
                s1, phi1 = forward(c1, tab["q1"])
                s2, phi2 = forward(c2, tab["q2"])
                total = s1 + s2
                users = tab["user"]
                slots = tab["slot"]
                legal = tab["legal"]
                width = int(slots.max()) + 1
                mats = {}
                for name, vec in (("sum", total), ("q1", s1), ("q2", s2)):
                    m = np.full((EXPECTED_USERS, width), np.nan, dtype=np.float64)
                    m[users[legal], slots[legal]] = vec[legal]
                    mats[name] = m
                entry: dict[str, Any] = {
                    "seed": ck["seed"],
                    "epoch": TARGET_EPOCH,
                    "checkpoint_sha256": ck_sha,
                    "anchor_id": anchor_id,
                    "slot_width": width,
                    "rows_in_anchor": int(tab["q1"].shape[0]),
                    "legal_rows_in_anchor": int(legal.sum()),
                }
                for name in ("sum", "q1", "q2"):
                    block, kept = complete_block(mats[name])
                    if kept >= 2:
                        a, s, npairs = sibling_pearson(block)
                    else:
                        a, s, npairs = float("nan"), float("nan"), 0
                    pa, ps, pn, pd = pairwise_complete_pearson(mats[name])
                    entry[name] = {
                        "complete_users": kept,
                        "sibling_abs_mean_offdiag_pearson": a,
                        "sibling_signed_mean_offdiag_pearson": s,
                        "sibling_pairs": npairs,
                        "pairwise_complete_abs_mean": pa,
                        "pairwise_complete_signed_mean": ps,
                        "pairwise_complete_pairs": pn,
                        "pairwise_complete_dropped_pairs": pd,
                    }
                entry["phi_c1"] = spectra(phi1[legal])
                entry["phi_c2"] = spectra(phi2[legal])
                cells.append(entry)
            print(f"[{run['name']}] seed {ck['seed']} done "
                  f"(rss {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss} KiB)", flush=True)

        agg: dict[str, Any] = {}
        for name in ("sum", "q1", "q2"):
            for field in ("sibling_abs_mean_offdiag_pearson", "sibling_signed_mean_offdiag_pearson",
                          "pairwise_complete_abs_mean", "pairwise_complete_signed_mean"):
                agg[f"{name}.{field}"] = summarize([c[name][field] for c in cells])
        for head in ("phi_c1", "phi_c2"):
            for field in ("srank_diagnostic_centered", "srank_fraction_of_hidden",
                          "srank_penalty_raw_smax2_minus_smin2", "sigma_max_raw", "sigma_min_raw"):
                agg[f"{head}.{field}"] = summarize([c[head][field] for c in cells])
        per_anchor: dict[str, Any] = {}
        for anchor_id in anchor_ids:
            sub = [c for c in cells if c["anchor_id"] == anchor_id]
            per_anchor[anchor_id] = {
                "seeds": len(sub),
                "sum_abs": summarize([c["sum"]["sibling_abs_mean_offdiag_pearson"] for c in sub]),
                "q1_abs": summarize([c["q1"]["sibling_abs_mean_offdiag_pearson"] for c in sub]),
                "q2_abs": summarize([c["q2"]["sibling_abs_mean_offdiag_pearson"] for c in sub]),
                "phi_c1_srank": summarize([c["phi_c1"]["srank_diagnostic_centered"] for c in sub]),
                "phi_c2_srank": summarize([c["phi_c2"]["srank_diagnostic_centered"] for c in sub]),
            }

        report["runs"][run["name"]] = {
            "label": run["label"],
            "directory": str(run["directory"]),
            "launch_receipt_sha256": receipt_sha,
            "corpus_root": receipt["corpus"]["root"],
            "corpus_digest": receipt["corpus"]["digest"],
            "feature_schema": receipt["feature_schema"],
            "q1_width": int(receipt["feature_schema"]["q1_width"]),
            "q2_width": int(receipt["feature_schema"]["q2_width"]),
            "seeds": [c["seed"] for c in checkpoints],
            "seed_count": len(checkpoints),
            "checkpoint_epoch_inventory": epoch_inventory,
            "anchors": anchor_ids,
            "pooled": agg,
            "per_anchor": per_anchor,
            "cells": cells,
        }
        del anchors

    report["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    Path(args.out).write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    print("peak RSS KiB:", report["peak_rss_kib"])
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
