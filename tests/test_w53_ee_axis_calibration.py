"""W-53 -- shared TRAIN-only lambda/kappa calibration."""

from __future__ import annotations

from dataclasses import replace

import pytest

from mcrl.runtime.ee_axis_calibration import (
    EEAxisCalibrationError,
    calibrate_ee_axis_pilot,
)
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM


def _calibration():
    return calibrate_ee_axis_pilot(
        calibration_seed=2026082401,
        useful_bits=10_097_071_012_757.404,
        energy_j=118_796.588289354,
        steps=10,
        users=100,
    )


def test_main_window_freezes_one_lambda_and_one_bits_per_decision_kappa():
    calibration = _calibration()
    assert calibration.decision_count == 1000
    assert calibration.lambda_bits_per_j == pytest.approx(84_994_621.12635651)
    assert calibration.kappa_bits == pytest.approx(10_097_071_012.757404)
    assert calibration.loss_weights == (1.0, 1.0, 1.0)
    assert calibration.verify()


def test_calibration_builds_current_three_q_config_for_either_pilot_lr():
    calibration = _calibration()
    for learning_rate in (0.001, 0.01):
        config = calibration.pairwise_config(learning_rate=learning_rate)
        assert config.state_dim == EE_AXIS_STATE_DIM
        assert config.hidden_layers == (100, 50, 50)
        assert config.activation == "tanh"
        assert config.learning_rate == learning_rate


def test_calibration_rejects_formula_drift():
    with pytest.raises(EEAxisCalibrationError, match="decision_count"):
        replace(_calibration(), decision_count=999).verify()
    with pytest.raises(EEAxisCalibrationError, match="kappa"):
        replace(_calibration(), kappa_bits=1.0).verify()
