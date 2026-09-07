from __future__ import annotations

import math

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_targets import ee_axis_targets


def test_axis_targets_reconstruct_horizon_ee_change() -> None:
    targets = ee_axis_targets(
        reference_rates_bps=np.array([[10.0, 20.0], [11.0, 19.0]]),
        reference_power_w=np.array([10.0, 10.0]),
        candidate_rates_bps=np.array([[12.0, 19.0], [14.0, 18.0]]),
        candidate_power_w=np.array([10.0, 10.0]),
        focal_user=0,
        interval_s=1.0,
    )

    assert targets.z1_immediate_focal_bits_per_j == pytest.approx(0.2)
    assert targets.z3_immediate_nonfocal_bits_per_j == pytest.approx(-0.1)
    assert targets.z2_horizon_residual_bits_per_j == pytest.approx(0.05)
    assert targets.delta_horizon_ee_bits_per_j == pytest.approx(0.15)
    assert targets.reconstructed_delta_ee_bits_per_j == pytest.approx(0.15)
    assert targets.identity_residual_bits_per_j == pytest.approx(0.0, abs=1e-15)


def test_axis_targets_remain_exact_when_candidate_power_changes() -> None:
    targets = ee_axis_targets(
        reference_rates_bps=np.array([[10.0, 20.0], [10.0, 20.0]]),
        reference_power_w=np.array([10.0, 10.0]),
        candidate_rates_bps=np.array([[13.0, 20.0], [14.0, 21.0]]),
        candidate_power_w=np.array([11.0, 12.0]),
        focal_user=0,
        interval_s=0.5,
    )

    assert math.isclose(
        targets.z1_immediate_focal_bits_per_j
        + targets.z2_horizon_residual_bits_per_j
        + targets.z3_immediate_nonfocal_bits_per_j,
        targets.delta_horizon_ee_bits_per_j,
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def test_one_step_trace_has_zero_horizon_residual() -> None:
    targets = ee_axis_targets(
        reference_rates_bps=np.array([[10.0, 20.0, 30.0]]),
        reference_power_w=np.array([20.0]),
        candidate_rates_bps=np.array([[11.0, 18.0, 34.0]]),
        candidate_power_w=np.array([21.0]),
        focal_user=2,
        interval_s=2.0,
    )

    assert targets.z2_horizon_residual_bits_per_j == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reference_power_w", np.array([0.0])),
        ("candidate_power_w", np.array([float("nan")])),
        ("reference_rates_bps", np.array([[-1.0, 2.0]])),
    ],
)
def test_axis_targets_fail_closed_on_invalid_physics(field: str, value: np.ndarray) -> None:
    kwargs = {
        "reference_rates_bps": np.array([[1.0, 2.0]]),
        "reference_power_w": np.array([3.0]),
        "candidate_rates_bps": np.array([[2.0, 2.0]]),
        "candidate_power_w": np.array([3.0]),
        "focal_user": 0,
        "interval_s": 1.0,
    }
    kwargs[field] = value
    with pytest.raises(MCRLContractError):
        ee_axis_targets(**kwargs)
