from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).with_name("analyze_c3_v3_posthoc_support.py")
spec = importlib.util.spec_from_file_location("analyze_c3_v3_posthoc_support", MODULE_PATH)
screen = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = screen
spec.loader.exec_module(screen)


def test_historical_posthoc_support_and_alias_denominators_recompute_exactly():
    result = screen.analyze()
    assert result["claim_type"] == "historical-descriptive-not-v3-evidence"
    assert result["denominators"] == {
        "historical_user_steps": 5000,
        "historical_candidate_rows": 174,
        "load_bearing_candidate_rows": 136,
    }
    assert result["strict_load_posthoc"] == {
        "rows": 34,
        "anchors": 15,
        "anchors_with_at_least_two_choices": 10,
        "anchors_with_at_least_two_choices_and_nonconstant_lagged_gap": 9,
        "rows_also_retained_by_historical_median_guard": 1,
    }
    alias = result["lagged_demand_vs_current_eligible_strict_gap"]
    assert (alias["true_positive"], alias["false_positive"]) == (10, 43)
    assert (alias["false_negative"], alias["true_negative"]) == (24, 59)
    assert alias["agreement"] == pytest.approx(0.5073529411764706)
    assert alias["precision"] == pytest.approx(0.18867924528301888)
    assert alias["recall"] == pytest.approx(0.29411764705882354)
    assert alias["gap_correlation"] == pytest.approx(0.03485653855163874)


def test_input_hash_drift_fails_before_analysis(monkeypatch):
    original = screen._sha256
    monkeypatch.setattr(
        screen,
        "_sha256",
        lambda path: "0" * 64 if path == screen.RESULT else original(path),
    )
    with pytest.raises(RuntimeError, match="result hash drift"):
        screen.analyze()
