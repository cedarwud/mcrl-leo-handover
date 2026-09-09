from __future__ import annotations

import copy
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import v023_c1c2_successor_physical_runner as runner


def _held_metrics(episodes: int = 3000) -> dict[str, dict[str, object]]:
    return {
        "FULL2": {
            "episodes": episodes,
            "ratio_of_sums_ee_bits_per_j": 5.0,
            "service_fraction": 1.0,
        },
        "DROP_C1": {
            "episodes": episodes,
            "ratio_of_sums_ee_bits_per_j": 4.0,
            "service_fraction": 1.0,
        },
        "DROP_C2": {
            "episodes": episodes,
            "ratio_of_sums_ee_bits_per_j": 3.0,
            "service_fraction": 1.0,
        },
        "BASELINE": {
            "episodes": episodes,
            "ratio_of_sums_ee_bits_per_j": 2.0,
            "service_fraction": 1.0,
        },
    }


def test_held_requires_every_contract_condition() -> None:
    result = runner.adjudicate_physical_disposition(
        _held_metrics(), completed_episodes=3000, expected_episodes=3000
    )
    assert result == {"overall_token": runner.HELD, "reasons": []}


@pytest.mark.parametrize(
    ("arm", "field", "value", "expected_reason"),
    [
        ("FULL2", "ratio_of_sums_ee_bits_per_j", 2.0, "FULL2_NOT_ABOVE_BASELINE"),
        ("DROP_C1", "ratio_of_sums_ee_bits_per_j", 2.0, "DROP_C1_NOT_ABOVE_BASELINE"),
        ("DROP_C2", "ratio_of_sums_ee_bits_per_j", 2.0, "DROP_C2_NOT_ABOVE_BASELINE"),
        ("DROP_C1", "ratio_of_sums_ee_bits_per_j", 5.0, "DROP_C1_NOT_BELOW_FULL2"),
        ("DROP_C2", "ratio_of_sums_ee_bits_per_j", 5.0, "DROP_C2_NOT_BELOW_FULL2"),
        ("FULL2", "service_fraction", 0.998, "SERVICE_NONINFERIORITY_FAILED:FULL2"),
        ("DROP_C1", "service_fraction", 0.998, "SERVICE_NONINFERIORITY_FAILED:DROP_C1"),
        ("DROP_C2", "service_fraction", 0.998, "SERVICE_NONINFERIORITY_FAILED:DROP_C2"),
    ],
)
def test_each_nonexclusive_falsifier_reason_is_reported(
    arm: str, field: str, value: float, expected_reason: str
) -> None:
    metrics = copy.deepcopy(_held_metrics())
    metrics[arm][field] = value
    result = runner.adjudicate_physical_disposition(
        metrics, completed_episodes=3000, expected_episodes=3000
    )
    assert result["overall_token"] == runner.FALSIFIED
    assert expected_reason in result["reasons"]


def test_reasons_are_nonexclusive() -> None:
    metrics = _held_metrics()
    metrics["FULL2"]["ratio_of_sums_ee_bits_per_j"] = 1.0
    metrics["DROP_C1"]["ratio_of_sums_ee_bits_per_j"] = 0.5
    metrics["DROP_C2"]["ratio_of_sums_ee_bits_per_j"] = 2.0
    metrics["DROP_C2"]["service_fraction"] = 0.0
    result = runner.adjudicate_physical_disposition(
        metrics, completed_episodes=3000, expected_episodes=3000
    )
    assert result["overall_token"] == runner.FALSIFIED
    assert result["reasons"] == [
        "FULL2_NOT_ABOVE_BASELINE",
        "DROP_C1_NOT_ABOVE_BASELINE",
        "DROP_C2_NOT_ABOVE_BASELINE",
        "DROP_C2_NOT_BELOW_FULL2",
        "SERVICE_NONINFERIORITY_FAILED:DROP_C2",
    ]


def test_integrity_failure_never_emits_a_scientific_token() -> None:
    result = runner.adjudicate_physical_disposition(
        _held_metrics(),
        completed_episodes=2999,
        expected_episodes=3000,
        integrity_ok=False,
    )
    assert result["overall_token"] == runner.INTEGRITY_STOP
    assert result["overall_token"] not in {runner.HELD, runner.FALSIFIED}
    assert result["reasons"] == []


def test_incomplete_receipts_are_integrity_not_science() -> None:
    result = runner.adjudicate_physical_disposition(
        _held_metrics(), completed_episodes=2999, expected_episodes=3000
    )
    assert result == {"overall_token": runner.INTEGRITY_STOP, "reasons": []}
