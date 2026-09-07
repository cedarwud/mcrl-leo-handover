"""Executable LR-selection tests for the V0.3A developmental trend."""

from __future__ import annotations

import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_v03a_lr_selector as selector  # noqa: E402


def _summary(path: Path, values: dict[str, float]) -> Path:
    rows = [
        {"arm": selector.ARM_LABELS[arm], "users": 100, "mean_ee_bits_per_j": ee}
        for arm, ee in values.items()
    ]
    path.write_text(json.dumps({"summary": rows}), encoding="utf-8")
    return path


def test_selects_only_lr_with_all_positive_catfish_marginals(tmp_path):
    weak = _summary(
        tmp_path / "weak.json",
        {"B000": 100.0, "F111": 99.0, "A011": 90.0, "A101": 90.0, "A110": 90.0},
    )
    strong = _summary(
        tmp_path / "strong.json",
        {"B000": 100.0, "F111": 110.0, "A011": 105.0, "A101": 106.0, "A110": 107.0},
    )

    result = selector.select_learning_rate(weak, strong)

    assert result["decision"] == "SELECT_AND_RUN_FRESH_3000"
    assert result["selected_learning_rate"] == 0.01


def test_tie_prefers_lr0p001_only_after_both_are_eligible(tmp_path):
    first = _summary(
        tmp_path / "first.json",
        {"B000": 100.0, "F111": 110.0, "A011": 105.0, "A101": 106.0, "A110": 107.0},
    )
    second = _summary(
        tmp_path / "second.json",
        {"B000": 100.0, "F111": 112.0, "A011": 105.0, "A101": 106.0, "A110": 107.0},
    )

    result = selector.select_learning_rate(first, second)

    assert result["tie_relative_percent"] < 4.0
    assert result["selected_learning_rate"] == 0.001


def test_stops_when_neither_lr_meets_three_catfish_goal(tmp_path):
    values = {
        "B000": 100.0,
        "F111": 110.0,
        "A011": 105.0,
        "A101": 111.0,
        "A110": 107.0,
    }
    first = _summary(tmp_path / "first.json", values)
    second = _summary(tmp_path / "second.json", values)

    result = selector.select_learning_rate(first, second)

    assert result["decision"] == "STOP_BEFORE_3000"
    assert result["selected_learning_rate"] is None
