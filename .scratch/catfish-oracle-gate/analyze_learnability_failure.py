#!/usr/bin/env python3
"""Exploratory diagnosis of the frozen v3.1 failure; never a gate rescue."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_state_learnability_dataset as dataset  # noqa: E402
import run_state_learnability_gate as gate  # noqa: E402
import verify_state_learnability_dataset as dataset_verify  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--heldout", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _mean(rows: Sequence[dict[str, Any]], field: str, scale: float = 1.0) -> float:
    return statistics.fmean(float(row[field]) / scale for row in rows)


def _label_metrics(
    rows: Sequence[dict[str, Any]], scores: np.ndarray, label: str
) -> dict[str, Any]:
    labels = np.asarray([float(bool(row[label])) for row in rows], dtype=np.float64)
    return {
        "label": label,
        "positives": int(labels.sum()),
        "prevalence": float(labels.mean()),
        "auroc": gate._auroc(labels, scores),
        "average_precision": gate._average_precision(labels, scores),
    }


def _subset_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"rows": 0}
    return {
        "rows": len(rows),
        "ee_positive": sum(bool(row["ee_positive"]) for row in rows),
        "ee_positive_rate": statistics.fmean(
            float(bool(row["ee_positive"])) for row in rows
        ),
        "role_positive": sum(bool(row["role_positive"]) for row in rows),
        "role_positive_rate": statistics.fmean(
            float(bool(row["role_positive"])) for row in rows
        ),
        "jointly_positive": sum(bool(row["jointly_positive"]) for row in rows),
        "jointly_positive_rate": statistics.fmean(
            float(bool(row["jointly_positive"])) for row in rows
        ),
        "mean_delta_ee_mbit_per_j": _mean(rows, "delta_ee_bits_per_j", 1e6),
        "mean_delta_throughput_gbit_per_s": _mean(
            rows, "delta_throughput_bps", 1e9
        ),
        "mean_delta_power_w": _mean(rows, "delta_power_w"),
    }


def _reference_load_group(row: dict[str, Any]) -> str:
    value = row["reference_prior_demand"]
    if value is None:
        return "missing"
    demand = float(value)
    if demand == 0.0:
        return "zero"
    if demand == 1.0:
        return "one"
    return "greater_than_one"


def _action_support(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(int(row["proposal_action"]) for row in rows)
    positives = Counter(
        int(row["proposal_action"])
        for row in rows
        if bool(row["jointly_positive"])
    )
    support = [counts.get(action, 0) for action in range(28)]
    return {
        "min_rows_per_output": min(support),
        "median_rows_per_output": statistics.median(support),
        "max_rows_per_output": max(support),
        "outputs_with_fewer_than_20_rows": sum(value < 20 for value in support),
        "by_action": {
            str(action): {
                "rows": counts.get(action, 0),
                "jointly_positive": positives.get(action, 0),
                "prevalence": (
                    positives.get(action, 0) / counts[action]
                    if counts.get(action, 0)
                    else None
                ),
            }
            for action in range(28)
        },
    }


def _partition_summary(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    role_positive = [row for row in rows if bool(row["role_positive"])]
    role_negative = [row for row in rows if not bool(row["role_positive"])]
    by_reference_load = {
        group: _subset_summary(
            [row for row in rows if _reference_load_group(row) == group]
        )
        for group in ("missing", "zero", "one", "greater_than_one")
    }
    return {
        "all": _subset_summary(rows),
        "role_positive": _subset_summary(role_positive),
        "role_negative": _subset_summary(role_negative),
        "ee_sign_risk_difference_role_positive_minus_negative": (
            _subset_summary(role_positive)["ee_positive_rate"]
            - _subset_summary(role_negative)["ee_positive_rate"]
        ),
        "reference_prior_demand_groups": by_reference_load,
        "q1_reference_differs_from_visible_incumbent": sum(
            row["visible_incumbent_action"] is None
            or int(row["reference_action"])
            != int(row["visible_incumbent_action"])
            for row in rows
        ),
        "action_support": _action_support(rows),
    }


def main() -> int:
    args = _arguments()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    development = json.loads(args.development.read_text(encoding="utf-8"))
    heldout = json.loads(args.heldout.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    development_verification = dataset_verify.verify(
        development, partition="development"
    )
    heldout_verification = dataset_verify.verify(heldout, partition="heldout")
    development_rows = gate._sorted_evaluated_rows(development)
    heldout_rows = gate._sorted_evaluated_rows(heldout)
    fit_rows = [
        row
        for row in development_rows
        if int(row["evaluation_seed"]) in gate.FIT_SEEDS
    ]
    calibration_rows = [
        row
        for row in development_rows
        if int(row["evaluation_seed"]) in gate.CALIBRATION_SEEDS
    ]
    predictions = result["heldout_predictions"]
    if len(predictions) != len(heldout_rows):
        raise RuntimeError("result prediction count differs from heldout rows")
    for row, prediction in zip(heldout_rows, predictions, strict=True):
        identity = (
            int(row["evaluation_seed"]),
            int(row["step_index"]),
            int(row["focal_user"]),
            int(row["proposal_action"]),
        )
        predicted_identity = (
            int(prediction["evaluation_seed"]),
            int(prediction["step_index"]),
            int(prediction["focal_user"]),
            int(prediction["proposal_action"]),
        )
        if identity != predicted_identity:
            raise RuntimeError("heldout prediction identity differs from dataset")
    model_scores = np.asarray(
        [float(row["score"]) for row in predictions], dtype=np.float64
    )
    sinr_scores = np.asarray(
        [float(row["proposal_candidate_sinr"]) for row in heldout_rows],
        dtype=np.float64,
    )
    hidden_reference_load_scores = np.asarray(
        [
            -1.0
            if row["reference_prior_demand"] is None
            else float(row["reference_prior_demand"])
            for row in heldout_rows
        ],
        dtype=np.float64,
    )
    labels = (
        "topology_endpoint_positive",
        "load_endpoint_positive",
        "role_positive",
        "ee_positive",
        "jointly_positive",
    )
    output = {
        "schema": "mcrl-catfish-r3-v3.1-failure-diagnostic-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete_exploratory_only",
        "claim_boundary": (
            "post-heldout exploratory failure diagnosis only; cannot rescue, "
            "retune, or replace the frozen v3.1 verdict"
        ),
        "development_verification": development_verification,
        "heldout_verification": heldout_verification,
        "frozen_decision": result["decision"],
        "development": _partition_summary(development_rows),
        "heldout": _partition_summary(heldout_rows),
        "fit_action_support": _action_support(fit_rows),
        "calibration_action_support": _action_support(calibration_rows),
        "heldout_target_metrics": {
            "frozen_q_head_proxy": {
                label: _label_metrics(heldout_rows, model_scores, label)
                for label in labels
            },
            "proposal_sinr_only": {
                label: _label_metrics(heldout_rows, sinr_scores, label)
                for label in labels
            },
            "forbidden_q1_reference_prior_demand_diagnostic": {
                label: _label_metrics(
                    heldout_rows, hidden_reference_load_scores, label
                )
                for label in labels
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
