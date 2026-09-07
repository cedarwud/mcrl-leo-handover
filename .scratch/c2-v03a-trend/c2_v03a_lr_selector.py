#!/usr/bin/env python3
"""Select the 3,000EP learning rate from two completed 1,500EP sweeps."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
import sys

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from c2_v03a_trend_authority import LR_SELECTION_RULE  # noqa: E402
from c2_v03a_trend_matrix import ARM_LABELS  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-lr-selection-v1"


class LRSelectionError(RuntimeError):
    """Raised when a sweep cannot support the frozen LR decision."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LRSelectionError(f"sweep summary is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise LRSelectionError("sweep summary must be a JSON object")
    return value


def _u100_scores(summary: Mapping[str, Any]) -> dict[str, float]:
    rows = summary.get("summary")
    if not isinstance(rows, list):
        raise LRSelectionError("sweep summary rows are missing")
    labels = set(ARM_LABELS.values())
    scores: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, Mapping) or row.get("users") != LR_SELECTION_RULE["endpoint_users"]:
            continue
        label = row.get("arm")
        value = row.get(LR_SELECTION_RULE["endpoint_metric"])
        if label in labels and isinstance(value, (int, float)) and not isinstance(value, bool):
            scores[str(label)] = float(value)
    if set(scores) != labels or any(value <= 0.0 for value in scores.values()):
        raise LRSelectionError("U100 sweep lacks finite positive scores for all five arms")
    return scores


def _assessment(summary: Mapping[str, Any], *, learning_rate: float) -> dict[str, Any]:
    scores = _u100_scores(summary)
    full = scores[ARM_LABELS["F111"]]
    comparisons = {
        "full_vs_baseline_percent": 100.0 * (full / scores[ARM_LABELS["B000"]] - 1.0),
        "c1_marginal_percent": 100.0 * (full / scores[ARM_LABELS["A011"]] - 1.0),
        "c2_marginal_percent": 100.0 * (full / scores[ARM_LABELS["A101"]] - 1.0),
        "c3_marginal_percent": 100.0 * (full / scores[ARM_LABELS["A110"]] - 1.0),
    }
    return {
        "learning_rate": float(learning_rate),
        "endpoint_arm": "F111",
        "endpoint_users": 100,
        "endpoint_ee_bits_per_j": full,
        "comparisons": comparisons,
        "eligible": all(value > 0.0 for value in comparisons.values()),
    }


def select_learning_rate(
    lr0p001_summary: Path, lr0p01_summary: Path
) -> dict[str, Any]:
    paths = {
        0.001: Path(lr0p001_summary).expanduser().resolve(),
        0.01: Path(lr0p01_summary).expanduser().resolve(),
    }
    assessments = {
        learning_rate: _assessment(_read(path), learning_rate=learning_rate)
        for learning_rate, path in paths.items()
    }
    eligible = [row for row in assessments.values() if row["eligible"]]
    if not eligible:
        decision = "STOP_BEFORE_3000"
        selected = None
        tie_relative_percent = None
    elif len(eligible) == 1:
        decision = "SELECT_AND_RUN_FRESH_3000"
        selected = eligible[0]["learning_rate"]
        tie_relative_percent = None
    else:
        first = assessments[0.001]["endpoint_ee_bits_per_j"]
        second = assessments[0.01]["endpoint_ee_bits_per_j"]
        tie_relative_percent = 100.0 * abs(first - second) / max(first, second)
        selected = (
            LR_SELECTION_RULE["tie_preference"]
            if tie_relative_percent <= LR_SELECTION_RULE["tie_band_relative_percent"]
            else max(eligible, key=lambda row: row["endpoint_ee_bits_per_j"])[
                "learning_rate"
            ]
        )
        decision = "SELECT_AND_RUN_FRESH_3000"
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "decision": decision,
        "selected_learning_rate": selected,
        "tie_relative_percent": tie_relative_percent,
        "rule": LR_SELECTION_RULE,
        "assessments": {str(key): value for key, value in assessments.items()},
        "inputs": {
            str(key): {"path": str(path), "sha256": _sha256(path)}
            for key, path in paths.items()
        },
        "claim_ceiling": (
            "one-training-seed developmental LR decision only; not formal efficacy, "
            "Chapter-5 evidence, deployment, auction, or coordination authorization"
        ),
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lr0p001-summary", type=Path, required=True)
    parser.add_argument("--lr0p01-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    result = select_learning_rate(args.lr0p001_summary, args.lr0p01_summary)
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite LR selection receipt: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
