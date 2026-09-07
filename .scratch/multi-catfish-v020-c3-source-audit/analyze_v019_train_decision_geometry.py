#!/usr/bin/env python3
"""Describe V0.19 C3 decision geometry on already-opened TRAIN shards only.

This script never loads VALIDATION or TEST data and performs no learner update.
It is a descriptive input to the V0.20 candidate-design freeze, not a gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(
    "artifacts/multi-catfish-v019-relational-q3-learner-20260904-r1/"
    "server-run/sources/TRAIN"
)


def _percentiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {"p05": 0.0, "p50": 0.0, "p95": 0.0}
    array = np.asarray(values, dtype=np.float64)
    return {
        "p05": float(np.percentile(array, 5)),
        "p50": float(np.percentile(array, 50)),
        "p95": float(np.percentile(array, 95)),
    }


def _empty() -> dict[str, Any]:
    return {
        "rows": 0,
        "legal_nonreference_actions": 0,
        "positive_targets": 0,
        "compatible_nonreference_actions": 0,
        "reference_argmax_mismatches": 0,
        "pivotal_rows": 0,
        "pivotal_teacher_positive": 0,
        "pivotal_teacher_compatible": 0,
        "pivotal_top_background_compatible_agreement": 0,
        "top_background_compatible_changes": 0,
        "top_background_compatible_supported": 0,
        "rows_without_compatible_nonreference": 0,
        "compatible_counts": [],
        "teacher_margin": [],
        "best_compatible_decision_margin": [],
    }


def _consume(total: dict[str, Any], source_path: Path) -> None:
    source = np.load(source_path)
    context = np.load(source_path.with_name("decision-context.npz"))
    metadata = json.loads(source_path.with_name("metadata.json").read_text())
    if metadata.get("split") != "TRAIN" or metadata.get("test_split_opened") is not False:
        raise RuntimeError(f"non-TRAIN source rejected: {source_path}")
    kappa = float.fromhex(str(metadata["kappa_bits_hex"]))
    mask = np.asarray(source["action_mask"], dtype=np.bool_)
    compatible = np.asarray(source["positive_credit_compatible"], dtype=np.bool_)
    reference = np.asarray(source["reference_actions"], dtype=np.int64)
    target = np.asarray(source["target_surface_bits"], dtype=np.float64) / kappa
    background = np.asarray(context["background_q12"], dtype=np.float64)
    context_mask = np.asarray(context["action_mask"], dtype=np.bool_)
    context_reference = np.asarray(context["reference_actions"], dtype=np.int64)
    if not np.array_equal(mask, context_mask) or not np.array_equal(reference, context_reference):
        raise RuntimeError(f"source/context identity mismatch: {source_path}")

    rows = mask.shape[0]
    row_index = np.arange(rows)
    masked_background = np.where(mask, background, -np.inf)
    base = np.argmax(masked_background, axis=1)
    total["reference_argmax_mismatches"] += int(np.count_nonzero(base != reference))
    teacher_score = np.where(mask, background + target, -np.inf)
    teacher = np.argmax(teacher_score, axis=1)

    nonreference = mask.copy()
    nonreference[row_index, reference] = False
    compatible_nonreference = compatible & nonreference
    positive = (target > 0.0) & nonreference
    pivotal = teacher != base

    total["rows"] += rows
    total["legal_nonreference_actions"] += int(np.count_nonzero(nonreference))
    total["positive_targets"] += int(np.count_nonzero(positive))
    total["compatible_nonreference_actions"] += int(
        np.count_nonzero(compatible_nonreference)
    )
    total["pivotal_rows"] += int(np.count_nonzero(pivotal))
    total["pivotal_teacher_positive"] += int(
        np.count_nonzero(pivotal & (target[row_index, teacher] > 0.0))
    )
    total["pivotal_teacher_compatible"] += int(
        np.count_nonzero(pivotal & compatible[row_index, teacher])
    )

    compatible_count = np.count_nonzero(compatible_nonreference, axis=1)
    total["compatible_counts"].extend(int(value) for value in compatible_count)
    total["rows_without_compatible_nonreference"] += int(
        np.count_nonzero(compatible_count == 0)
    )

    sorted_teacher = np.sort(teacher_score, axis=1)
    teacher_margin = sorted_teacher[:, -1] - sorted_teacher[:, -2]
    total["teacher_margin"].extend(float(value) for value in teacher_margin[pivotal])

    # Diagnostic only: conditional on a pivotal row, test how often the
    # highest-background compatible non-reference candidate is the teacher.
    candidate_background = np.where(compatible_nonreference, background, -np.inf)
    candidate = np.argmax(candidate_background, axis=1)
    has_candidate = compatible_count > 0
    agreement = pivotal & has_candidate & (candidate == teacher)
    total["pivotal_top_background_compatible_agreement"] += int(
        np.count_nonzero(agreement)
    )

    # This unconditional rule is not a proposed deployment policy.  It exposes
    # why a separate learned gain-versus-background-gap decision is required.
    changed = has_candidate & (candidate != base)
    supported = changed & (target[row_index, candidate] > 0.0)
    total["top_background_compatible_changes"] += int(np.count_nonzero(changed))
    total["top_background_compatible_supported"] += int(
        np.count_nonzero(supported)
    )

    decision_margin = (
        background[row_index, candidate]
        + target[row_index, candidate]
        - background[row_index, base]
    )
    total["best_compatible_decision_margin"].extend(
        float(value) for value in decision_margin[has_candidate]
    )


def _finalize(total: dict[str, Any]) -> dict[str, Any]:
    rows = int(total["rows"])
    comparisons = int(total["legal_nonreference_actions"])
    pivotal = int(total["pivotal_rows"])
    changes = int(total["top_background_compatible_changes"])
    result = {key: value for key, value in total.items() if not isinstance(value, list)}
    result.update(
        {
            "positive_target_fraction": total["positive_targets"] / comparisons,
            "compatible_nonreference_fraction": (
                total["compatible_nonreference_actions"] / comparisons
            ),
            "pivotal_row_fraction": pivotal / rows,
            "pivotal_teacher_positive_fraction": (
                total["pivotal_teacher_positive"] / pivotal if pivotal else 0.0
            ),
            "pivotal_teacher_compatible_fraction": (
                total["pivotal_teacher_compatible"] / pivotal if pivotal else 0.0
            ),
            "pivotal_top_background_compatible_agreement_fraction": (
                total["pivotal_top_background_compatible_agreement"] / pivotal
                if pivotal
                else 0.0
            ),
            "unconditional_top_background_compatible_support_fraction": (
                total["top_background_compatible_supported"] / changes
                if changes
                else 0.0
            ),
            "rows_without_compatible_nonreference_fraction": (
                total["rows_without_compatible_nonreference"] / rows
            ),
            "compatible_nonreference_count_percentiles": _percentiles(
                total["compatible_counts"]
            ),
            "pivotal_teacher_margin_percentiles": _percentiles(
                total["teacher_margin"]
            ),
            "best_compatible_decision_margin_percentiles": _percentiles(
                total["best_compatible_decision_margin"]
            ),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not ROOT.is_dir():
        raise SystemExit(f"missing V0.19 TRAIN root: {ROOT}")
    pooled = _empty()
    by_lineage: dict[str, dict[str, Any]] = {}
    by_world: dict[str, dict[str, Any]] = {}
    shards = sorted(ROOT.glob("*/source.npz"))
    if not shards:
        raise SystemExit("no TRAIN shards found")
    for source_path in shards:
        metadata = json.loads(source_path.with_name("metadata.json").read_text())
        lineage = str(metadata["lineage"])
        world = str(metadata["world_seed"])
        _consume(pooled, source_path)
        _consume(by_lineage.setdefault(lineage, _empty()), source_path)
        _consume(by_world.setdefault(world, _empty()), source_path)
    output = {
        "schema": "multi-catfish-v020-v019-train-decision-geometry-v1",
        "evidence_class": "OPENED_TRAIN_DESCRIPTIVE_ONLY",
        "source_root": str(ROOT),
        "shard_count": len(shards),
        "validation_loaded": False,
        "test_split_opened": False,
        "learner_update": False,
        "pooled": _finalize(pooled),
        "by_lineage": {
            key: _finalize(value) for key, value in sorted(by_lineage.items())
        },
        "by_world": {
            key: _finalize(value) for key, value in sorted(by_world.items())
        },
    }
    rendered = json.dumps(output, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
