from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_c1_source_gate", HERE / "run_c1_source_gate.py"
)
assert SPEC is not None and SPEC.loader is not None
G = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = G
SPEC.loader.exec_module(G)


def seed_row(delta: float, *, local_service: float = 0.95, control_service: float = 0.95):
    return {
        "delta_ee_bits_per_j": delta,
        "local_served_fraction": local_service,
        "control_served_fraction": control_service,
    }


def test_gate_pass_requires_positive_mean_four_seeds_and_service_guard():
    result = G.decide_gate(
        [seed_row(value) for value in (4.0, 3.0, 2.0, 1.0, -0.5)],
        guard_failures=(),
    )
    assert result["status"] == "PASS"
    assert result["positive_seed_count"] == 4
    assert all(result["checks"].values())


@pytest.mark.parametrize(
    "rows,guards,failed_check",
    [
        (
            [seed_row(value) for value in (4.0, 3.0, -1.0, -1.0, -1.0)],
            (),
            "positive_seeds_at_least_4_of_5",
        ),
        (
            [
                seed_row(value, local_service=0.94, control_service=0.95)
                for value in (4.0, 3.0, 2.0, 1.0, -0.5)
            ],
            (),
            "served_fraction_noninferior",
        ),
        (
            [seed_row(value) for value in (4.0, 3.0, 2.0, 1.0, -0.5)],
            ("anchor_mutated",),
            "all_guards_pass",
        ),
    ],
)
def test_gate_fails_closed_on_each_frozen_condition(rows, guards, failed_check):
    result = G.decide_gate(rows, guard_failures=guards)
    assert result["status"] == "FAIL"
    assert result["checks"][failed_check] is False


def test_control_rng_is_domain_repeatable_and_fresh():
    first = G.control_rng(77)
    second = G.control_rng(77)
    third = G.control_rng(78)
    assert first is not second
    assert first.integers(0, 2**31) == second.integers(0, 2**31)
    assert first.integers(0, 2**31) != third.integers(0, 2**31)


def test_metrics_uses_ratio_of_sums_not_mean_of_ratios():
    rows = [
        {
            "throughput_bps": 100.0,
            "power_w": 10.0,
            "served": 1,
            "users": 2,
            "reward_sum": [0.0, 0.0, 0.0],
        },
        {
            "throughput_bps": 100.0,
            "power_w": 30.0,
            "served": 2,
            "users": 2,
            "reward_sum": [0.0, 0.0, 0.0],
        },
    ]
    metrics = G._metrics(rows)
    assert metrics.ee_bits_per_j == pytest.approx(5.0)
    assert metrics.ee_bits_per_j != pytest.approx((10.0 + 100.0 / 30.0) / 2.0)
    assert metrics.served_fraction == pytest.approx(0.75)


def test_gate_rejects_wrong_seed_denominator():
    with pytest.raises(ValueError, match="exactly five"):
        G.decide_gate([seed_row(1.0)] * 4, guard_failures=())
