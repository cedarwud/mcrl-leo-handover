#!/usr/bin/env python3
"""Reprice all sealed V0.14 Q2 source shards without running physics.

This runner is deliberately limited to the 21 already opened source shards
declared by the 2026-09-04 Q1/Q2 repricing contract.  It authenticates the
Cartesian world/lineage panel, delegates the per-shard reconstruction to
``reconstruct_v014_q2_from_state.py``, and writes a compact aggregate receipt.
It does not import or call a simulator, train a learner, or open TEST.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RECONSTRUCTION_PATH = HERE / "reconstruct_v014_q2_from_state.py"
CONTRACT_PATH = (
    HERE / "Q1-Q2-LAMBDA-REPRICING-PREOUTCOME-CONTRACT-2026-09-04.md"
)
DEFAULT_SOURCE_ROOT = (
    REPO
    / "artifacts"
    / "multi-catfish-v014-learnability-20260903-r1"
    / "server-run"
    / "source-panel"
    / "shards"
)
DEFAULT_OUTPUT = HERE / "q2-batch-repricing"
NEW_LAMBDA = float.fromhex("0x1.c3c0a7b6b86d3p+26")
EXPECTED_WORLDS = tuple(range(2026108001, 2026108008))
TRAIN_WORLDS = frozenset(range(2026108001, 2026108005))
VALIDATION_WORLDS = frozenset(range(2026108005, 2026108008))
EXPECTED_LINEAGES = (2026092101, 2026092102, 2026092103)
SHARD_RE = re.compile(r"^(?P<world>[0-9]{10})-(?P<lineage>[0-9]{10})$")


def _load_reconstruction_module() -> Any:
    spec = importlib.util.spec_from_file_location("v020_q2_reconstruction", RECONSTRUCTION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {RECONSTRUCTION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _counts(values: np.ndarray) -> dict[str, int]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "negative": int(np.count_nonzero(array < 0.0)),
        "zero": int(np.count_nonzero(array == 0.0)),
        "positive": int(np.count_nonzero(array > 0.0)),
    }


def _finite_stats(values: np.ndarray) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64).ravel()
    if array.size == 0 or not np.all(np.isfinite(array)):
        raise ValueError("statistics require a non-empty finite array")
    return {
        "count": int(array.size),
        "min": float(np.min(array)),
        "median": float(np.median(array)),
        "mean": float(np.mean(array)),
        "max": float(np.max(array)),
        "p05": float(np.percentile(array, 5.0)),
        "p95": float(np.percentile(array, 95.0)),
    }


def run(*, source_root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite {output_dir}")
    expected = {
        (world, lineage)
        for world in EXPECTED_WORLDS
        for lineage in EXPECTED_LINEAGES
    }
    discovered: dict[tuple[int, int], Path] = {}
    for path in sorted(source_root.iterdir()):
        if not path.is_dir() or path.is_symlink():
            continue
        match = SHARD_RE.fullmatch(path.name)
        if match is None:
            continue
        key = (int(match.group("world")), int(match.group("lineage")))
        discovered[key] = path
    if set(discovered) != expected:
        raise ValueError(
            "source shard Cartesian panel changed: "
            f"missing={sorted(expected - set(discovered))}, "
            f"extra={sorted(set(discovered) - expected)}"
        )

    module = _load_reconstruction_module()
    output_dir.mkdir(parents=True)
    shards_dir = output_dir / "shards"
    shards_dir.mkdir()
    per_shard: list[dict[str, Any]] = []
    old_by_partition: dict[str, list[np.ndarray]] = {"TRAIN": [], "VALIDATION": []}
    new_by_partition: dict[str, list[np.ndarray]] = {"TRAIN": [], "VALIDATION": []}
    all_old: list[np.ndarray] = []
    all_new: list[np.ndarray] = []
    gate_failures: list[str] = []

    for (world, lineage), shard in sorted(discovered.items()):
        partition = "TRAIN" if world in TRAIN_WORLDS else "VALIDATION"
        shard_output = shards_dir / shard.name
        shard_output.mkdir()
        output_json = shard_output / "audit.json"
        output_npy = shard_output / "q2_target_bits_repriced.npy"
        audit = module._audit(
            source_path=shard / "source.npz",
            metadata_path=shard / "metadata.json",
            output_json=output_json,
            repriced_output=output_npy,
            user_count=100,
            total_steps=10,
            lambda_new=NEW_LAMBDA,
        )
        with np.load(shard / "source.npz", allow_pickle=False) as source:
            masks = np.asarray(source["q2_masks"], dtype=np.bool_)
            old = np.asarray(source["q2_target_bits"], dtype=np.float64)[masks]
        new = np.asarray(np.load(output_npy, allow_pickle=False), dtype=np.float64)[masks]
        if old.shape != new.shape or not np.all(np.isfinite(new)):
            gate_failures.append(f"{shard.name}: repriced target shape/finiteness failed")
        absolute_max = float(
            audit["error_metrics_on_legal_entries"]["absolute_bits"]["max"]
        )
        relative_scale_max = float(
            audit["error_metrics_on_legal_entries"]
            ["relative_to_max_abs_target_scale"]["max"]
        )
        affine_max = float(
            audit["repricing"]["affine_reconstruction_absolute_bits"]["max"]
        )
        if audit["source_receipt_matches"] is not True:
            gate_failures.append(f"{shard.name}: source receipt mismatch")
        if audit["source_metadata"]["split"] != "TRAIN":
            gate_failures.append(f"{shard.name}: source metadata no longer says TRAIN")
        if audit["source_metadata"]["test_split_opened"] is not False:
            gate_failures.append(f"{shard.name}: TEST boundary changed")
        if absolute_max > 2500.0:
            gate_failures.append(f"{shard.name}: absolute reconstruction error {absolute_max}")
        if relative_scale_max >= 1.0e-6:
            gate_failures.append(
                f"{shard.name}: relative reconstruction error {relative_scale_max}"
            )
        if affine_max > 1.0e-3:
            gate_failures.append(f"{shard.name}: affine repricing error {affine_max}")
        sign_flip = (old < 0.0) & (new > 0.0) | (old > 0.0) & (new < 0.0)
        per_shard.append(
            {
                "world": world,
                "lineage": lineage,
                "partition": partition,
                "shard": shard.name,
                "source_npz_sha256": audit["source_sha256"],
                "audit_json_sha256": _sha256(output_json),
                "repriced_npy_sha256": _sha256(output_npy),
                "legal_entries": int(old.size),
                "old_sign_counts": _counts(old),
                "new_sign_counts": _counts(new),
                "strict_sign_flip_count": int(np.count_nonzero(sign_flip)),
                "absolute_reconstruction_error_max_bits": absolute_max,
                "relative_to_target_scale_error_max": relative_scale_max,
                "affine_repricing_error_max_bits": affine_max,
            }
        )
        old_by_partition[partition].append(old)
        new_by_partition[partition].append(new)
        all_old.append(old)
        all_new.append(new)

    old_all = np.concatenate(all_old)
    new_all = np.concatenate(all_new)
    strict_flip = (old_all < 0.0) & (new_all > 0.0) | (
        (old_all > 0.0) & (new_all < 0.0)
    )
    by_partition: dict[str, Any] = {}
    for partition in ("TRAIN", "VALIDATION"):
        old = np.concatenate(old_by_partition[partition])
        new = np.concatenate(new_by_partition[partition])
        flips = (old < 0.0) & (new > 0.0) | (old > 0.0) & (new < 0.0)
        by_partition[partition] = {
            "legal_entries": int(old.size),
            "old_target_bits": _finite_stats(old),
            "new_target_bits": _finite_stats(new),
            "old_sign_counts": _counts(old),
            "new_sign_counts": _counts(new),
            "strict_sign_flip_count": int(np.count_nonzero(flips)),
            "strict_sign_flip_fraction": float(np.mean(flips)),
        }

    payload: dict[str, Any] = {
        "schema": "multi-catfish-mcrl-v020-q2-batch-repricing-result-v1",
        "status": "PASS_OFFLINE_Q2_REPRICING" if not gate_failures else "FAIL_OFFLINE_Q2_REPRICING",
        "claim_ceiling": "SOURCE_REUSE_ONLY_NO_SIMULATOR_NO_TRAINING_NO_TEST_NO_EFFICACY",
        "contract": {
            "path": str(CONTRACT_PATH.relative_to(REPO)),
            "sha256": _sha256(CONTRACT_PATH),
        },
        "implementation": {
            "batch_runner_sha256": _sha256(Path(__file__)),
            "reconstruction_sha256": _sha256(RECONSTRUCTION_PATH),
        },
        "lambda": {
            "new_bits_per_j": NEW_LAMBDA,
            "new_bits_per_j_hex": NEW_LAMBDA.hex(),
        },
        "panel": {
            "worlds": list(EXPECTED_WORLDS),
            "train_worlds": sorted(TRAIN_WORLDS),
            "validation_worlds": sorted(VALIDATION_WORLDS),
            "lineages": list(EXPECTED_LINEAGES),
            "shard_count": len(per_shard),
        },
        "aggregate": {
            "legal_entries": int(old_all.size),
            "old_target_bits": _finite_stats(old_all),
            "new_target_bits": _finite_stats(new_all),
            "old_sign_counts": _counts(old_all),
            "new_sign_counts": _counts(new_all),
            "strict_sign_flip_count": int(np.count_nonzero(strict_flip)),
            "strict_sign_flip_fraction": float(np.mean(strict_flip)),
            "maximum_absolute_reconstruction_error_bits": max(
                row["absolute_reconstruction_error_max_bits"] for row in per_shard
            ),
            "maximum_relative_to_target_scale_error": max(
                row["relative_to_target_scale_error_max"] for row in per_shard
            ),
            "maximum_affine_repricing_error_bits": max(
                row["affine_repricing_error_max_bits"] for row in per_shard
            ),
        },
        "by_partition": by_partition,
        "per_shard": per_shard,
        "gate_failures": gate_failures,
        "test_split_opened": False,
        "simulator_run": False,
        "learner_update": False,
        "episode_training": False,
    }
    result_path = output_dir / "result.json"
    result_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    (output_dir / "result.sha256").write_text(
        f"{_sha256(result_path)}  result.json\n", encoding="ascii"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(source_root=args.source_root, output_dir=args.output_dir)
    print(
        json.dumps(
            {
                "status": result["status"],
                "shards": result["panel"]["shard_count"],
                "legal_entries": result["aggregate"]["legal_entries"],
                "strict_sign_flip_fraction": result["aggregate"][
                    "strict_sign_flip_fraction"
                ],
                "gate_failures": result["gate_failures"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS_OFFLINE_Q2_REPRICING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
