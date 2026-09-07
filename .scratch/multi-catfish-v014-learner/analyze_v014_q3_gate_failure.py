#!/usr/bin/env python3
"""Recompute descriptive Q3 source/gate diagnostics without fitting a model."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np


SCHEMA = "multi-catfish-mcrl-v014-q3-postgate-census-v1"
CLAIM_CEILING = "POSTHOC_DESCRIPTIVE_DIAGNOSIS_ONLY"
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")


def _empty() -> dict[str, float | int]:
    return {
        "anchors": 0,
        "comparisons": 0,
        "positive_comparisons": 0,
        "negative_comparisons": 0,
        "zero_comparisons": 0,
        "compatible_comparisons": 0,
        "positive_compatible_comparisons": 0,
        "opportunity_anchors": 0,
        "multiple_positive_anchors": 0,
        "teacher_action_changes": 0,
        "reference_background_mismatches": 0,
        "positive_squared_target": 0.0,
        "negative_squared_target": 0.0,
    }


def _add(target: dict[str, float | int], source: dict[str, float | int]) -> None:
    for key, value in source.items():
        target[key] += value


def _finish(row: dict[str, float | int]) -> dict[str, float | int]:
    anchors = int(row["anchors"])
    comparisons = int(row["comparisons"])
    squared = float(row["positive_squared_target"]) + float(
        row["negative_squared_target"]
    )
    result = dict(row)
    result.update(
        {
            "positive_comparison_rate": int(row["positive_comparisons"]) / comparisons,
            "negative_comparison_rate": int(row["negative_comparisons"]) / comparisons,
            "zero_comparison_rate": int(row["zero_comparisons"]) / comparisons,
            "opportunity_anchor_rate": int(row["opportunity_anchors"]) / anchors,
            "teacher_action_change_rate": int(row["teacher_action_changes"]) / anchors,
            "positive_squared_loss_share_under_uniform_mse": (
                float(row["positive_squared_target"]) / squared if squared else 0.0
            ),
            "negative_squared_loss_share_under_uniform_mse": (
                float(row["negative_squared_target"]) / squared if squared else 0.0
            ),
        }
    )
    return result


def analyze(source_root: str | Path, gate_result: str | Path) -> dict[str, object]:
    root = Path(source_root)
    result_path = Path(gate_result)
    gate = json.loads(result_path.read_text(encoding="ascii"))
    if gate.get("status") != "STOP_LEARNABILITY_GATE":
        raise ValueError("this census expects the completed frozen STOP gate")
    train_worlds = set(int(v) for v in gate["spec"]["train_world_seeds"])
    validation_worlds = set(int(v) for v in gate["spec"]["validation_world_seeds"])
    pooled = _empty()
    splits = {"TRAIN": _empty(), "VALIDATION": _empty()}
    lineages: dict[int, dict[str, float | int]] = defaultdict(_empty)
    positive_values: list[np.ndarray] = []
    negative_values: list[np.ndarray] = []
    positive_actions_per_opportunity: list[np.ndarray] = []
    shard_count = 0

    for shard in sorted(root.iterdir()):
        if shard.is_symlink() or not shard.is_dir():
            continue
        with np.load(shard / "source.npz", allow_pickle=False) as loaded:
            masks = np.asarray(loaded["q3_masks"], dtype=np.bool_)
            references = np.asarray(loaded["q3_reference_actions"], dtype=np.int64)
            targets = np.asarray(loaded["q3_target_bits"], dtype=np.float64)
            compatible = np.asarray(loaded["q3_compatibility"], dtype=np.bool_)
            q1 = np.asarray(loaded["q1_values"], dtype=np.float64)
            q2 = np.asarray(loaded["q2_target_bits"], dtype=np.float64)
            worlds = np.asarray(loaded["source_seeds"], dtype=np.int64)
        if len(set(worlds.tolist())) != 1:
            raise ValueError(f"mixed worlds in {shard}")
        world = int(worlds[0])
        if world in train_worlds:
            split = "TRAIN"
        elif world in validation_worlds:
            split = "VALIDATION"
        else:
            raise ValueError(f"undeclared world {world}")
        lineage = int(shard.name.rsplit("-", 1)[1])
        rows = np.arange(references.size)
        comparisons = np.array(masks, copy=True)
        comparisons[rows, references] = False
        centered = targets - targets[rows, references, None]
        values = centered[comparisons] / KAPPA_BITS
        support = compatible[comparisons]
        positive = values > 0.0
        negative = values < 0.0
        positive_matrix = (centered > 0.0) & comparisons
        positive_counts = positive_matrix.sum(axis=1)
        background = np.argmax(
            np.where(masks, q1 + q2 / KAPPA_BITS, -np.inf), axis=1
        )
        teacher = np.argmax(
            np.where(masks, q1 + q2 / KAPPA_BITS + targets / KAPPA_BITS, -np.inf),
            axis=1,
        )
        row = {
            "anchors": int(references.size),
            "comparisons": int(values.size),
            "positive_comparisons": int(np.count_nonzero(positive)),
            "negative_comparisons": int(np.count_nonzero(negative)),
            "zero_comparisons": int(np.count_nonzero(values == 0.0)),
            "compatible_comparisons": int(np.count_nonzero(support)),
            "positive_compatible_comparisons": int(
                np.count_nonzero(positive & support)
            ),
            "opportunity_anchors": int(np.count_nonzero(positive_counts > 0)),
            "multiple_positive_anchors": int(np.count_nonzero(positive_counts > 1)),
            "teacher_action_changes": int(np.count_nonzero(teacher != background)),
            "reference_background_mismatches": int(
                np.count_nonzero(references != background)
            ),
            "positive_squared_target": float(np.sum(np.square(values[positive]))),
            "negative_squared_target": float(np.sum(np.square(values[negative]))),
        }
        _add(pooled, row)
        _add(splits[split], row)
        _add(lineages[lineage], row)
        positive_values.append(values[positive])
        negative_values.append(values[negative])
        positive_actions_per_opportunity.append(positive_counts[positive_counts > 0])
        shard_count += 1

    positive = np.concatenate(positive_values)
    negative = np.concatenate(negative_values)
    opportunity_counts = np.concatenate(positive_actions_per_opportunity)
    if int(pooled["positive_comparisons"]) != int(
        pooled["positive_compatible_comparisons"]
    ):
        raise ValueError("a positive Q3 comparison lacks frozen compatibility support")
    if int(pooled["reference_background_mismatches"]) != 0:
        raise ValueError("Q3 reference does not equal the oracle Q1+OPS3 background")

    return {
        "schema": SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "source_shards": shard_count,
        "pooled": {
            **_finish(pooled),
            "positive_target_kappa_median": float(np.median(positive)),
            "positive_target_kappa_p95": float(np.quantile(positive, 0.95)),
            "negative_target_kappa_median": float(np.median(negative)),
            "negative_target_kappa_p05": float(np.quantile(negative, 0.05)),
            "positive_actions_per_opportunity_mean": float(
                np.mean(opportunity_counts)
            ),
            "positive_actions_per_opportunity_p95": float(
                np.quantile(opportunity_counts, 0.95)
            ),
        },
        "by_split": {key: _finish(value) for key, value in splits.items()},
        "by_lineage": {
            str(key): _finish(value) for key, value in sorted(lineages.items())
        },
        "gate": {
            "status": gate["status"],
            "deployment_rung": gate["selection"]["deployment_rung"],
            "q2_decision": gate["q2_decision"],
            "q3_decision": gate["q3_decision"],
            "joint_decision": gate["joint_decision"],
        },
        "interpretation_boundary": (
            "Class imbalance is a verified source fact; it does not by itself "
            "prove that objective rebalancing will improve learned-policy EE."
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("gate_result", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = analyze(args.source_root, args.gate_result)
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError(f"refusing to overwrite {args.output}")
        args.output.write_text(encoded, encoding="ascii")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

