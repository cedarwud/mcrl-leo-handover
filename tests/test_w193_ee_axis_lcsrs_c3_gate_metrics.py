"""W-193 -- pure metric and decision recomputation for the V0.23 gate."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_lcsrs_c3_gate_metrics import (
    LCSRSC3GateMetricError,
    V023_REQUIRED_PREDICATES,
    adjudicate_c3,
    comparison_tolerance,
    context_status,
    ratio_of_sums_direction,
    sign_accuracy,
    strict_direction,
    tie_aware_spearman,
)


def _passing_predicates() -> dict[str, bool]:
    return {name: True for name in V023_REQUIRED_PREDICATES}


def test_tolerance_and_ratio_direction_use_cross_products() -> None:
    assert comparison_tolerance(1.0, 2.0) >= 1.0e-12
    assert strict_direction(1.0, 1.0) == 0
    result = ratio_of_sums_direction(
        left_bits=120.0,
        left_energy_j=2.0,
        right_bits=100.0,
        right_energy_j=2.0,
    )
    assert result.direction == 1
    assert result.cross_product == pytest.approx(40.0)
    assert result.left_ee == pytest.approx(60.0)
    with pytest.raises(LCSRSC3GateMetricError, match="positive energy"):
        ratio_of_sums_direction(
            left_bits=1.0,
            left_energy_j=0.0,
            right_bits=1.0,
            right_energy_j=1.0,
        )


def test_spearman_is_tie_aware_and_constant_vectors_fail_closed() -> None:
    assert tie_aware_spearman([1.0, 2.0, 2.0], [1.0, 2.0, 3.0]) == pytest.approx(
        0.8660254037844387
    )
    assert tie_aware_spearman([1.0, 1.0], [1.0, 2.0]) is None
    assert tie_aware_spearman([1.0], [1.0]) is None
    assert tie_aware_spearman([1.0, np.nan], [1.0, 2.0]) is None


def test_sign_accuracy_preserves_all_denominators_and_zero_prediction_fails() -> None:
    receipt = sign_accuracy(
        predictions=[1.0, 0.0, -1.0, 1.0],
        targets=[0.03, -0.02, -0.01, -0.5],
    )
    assert receipt.total_rows == 4
    assert receipt.evaluated_rows == 3
    assert receipt.excluded_rows == 1
    assert receipt.correct_rows == 1
    assert receipt.accuracy == pytest.approx(1.0 / 3.0)
    empty = sign_accuracy([1.0], [0.019])
    assert empty.evaluated_rows == 0 and empty.accuracy is None


def test_context_status_is_independent_and_exhaustive() -> None:
    assert context_status(c1_pass=True, c2_pass=True) == "CONTEXT_DIAGNOSTICS_PASS"
    assert context_status(c1_pass=False, c2_pass=True) == "HOLD_C1"
    assert context_status(c1_pass=True, c2_pass=False) == "HOLD_C2"
    assert context_status(c1_pass=False, c2_pass=False) == "HOLD_C1_C2"


@pytest.mark.parametrize(
    ("failed", "expected"),
    [
        ("pair_coverage", "INSUFFICIENT_PAIRS"),
        ("mechanics", "STOP_PHYSICS"),
        ("physical_signature", "STOP_PHYSICS"),
        ("teacher_composition", "STOP_PHYSICS"),
        ("interface_a", "STOP_OBSERVABILITY"),
        ("held_out_learner", "STOP_OBSERVABILITY"),
        ("world_stability", "STOP_OBSERVABILITY"),
        ("action_exposure", "REDESIGN_INTERFACE"),
        ("topology_consistency", "REDESIGN_INTERFACE"),
        ("service", "REDESIGN_INTERFACE"),
    ],
)
def test_decision_precedence_maps_each_frozen_predicate_group(
    failed: str, expected: str
) -> None:
    predicates = _passing_predicates()
    predicates[failed] = False
    assert adjudicate_c3(predicates, integrity_pass=True) == expected


def test_decision_precedence_is_fail_closed_and_requires_complete_exact_table() -> None:
    passing = _passing_predicates()
    assert (
        adjudicate_c3(passing, integrity_pass=True)
        == "GO_FIXED_LEARNER_SCREEN_CONTRACT"
    )
    assert adjudicate_c3({}, integrity_pass=False) == "INVALID_RUN"
    missing = dict(passing)
    missing.pop("service")
    with pytest.raises(LCSRSC3GateMetricError, match="not exact"):
        adjudicate_c3(missing, integrity_pass=True)
    extra = dict(passing, undeclared=True)
    with pytest.raises(LCSRSC3GateMetricError, match="not exact"):
        adjudicate_c3(extra, integrity_pass=True)
