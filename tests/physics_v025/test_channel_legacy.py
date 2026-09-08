"""Propagation, antenna, fading, numerics, and old-physics regression KATs."""

from __future__ import annotations

import math

import mpmath
import numpy as np
import pytest

from mcrl.env.link_budget import recurrence_power_w, system_power_w
from mcrl.physics_v025.channel import (
    db_loss_gain,
    free_space_path_gain,
    keyed_component_seed,
    receive_gain_dbi,
    rician_power_gain,
    shadow_linear_mean,
    transmit_gain_linear,
)
from mcrl.physics_v025.constants_v025 import RX_S465_THETA_MIN_DEG


def test_propagation_quarter_power_and_ten_db_loss() -> None:
    """FSPL gain is proportional to d^-2, and 10^(-10/10)=0.1."""

    first, doubled = free_space_path_gain(np.array([500.0, 1000.0]))
    assert doubled / first == pytest.approx(0.25, rel=1e-15)
    assert float(db_loss_gain(10.0)) == pytest.approx(0.1, rel=1e-15)


def test_transmit_gain_absolute_anchors() -> None:
    """Ideal pattern gives G_T(0)=2000 and its half-power point G_T(1.66deg)~=1000."""

    values = transmit_gain_linear(np.array([0.0, 1.66]))
    assert values[0] == 2000.0
    assert values[1] == pytest.approx(1000.0, abs=0.002)


def test_receive_pattern_and_correct_s465_branch() -> None:
    """clip(32-25log10(theta),-10,35) gives 35/32/24.47425 dBi at 0/1/2 deg."""

    assert receive_gain_dbi(np.array([0.0, 1.0, 2.0])) == pytest.approx(
        [35.0, 32.0, 24.4742501084], abs=1e-10
    )
    assert RX_S465_THETA_MIN_DEG == pytest.approx(2.043298703, abs=1e-12)


def test_rician_unit_mean_and_db_shadow_linear_mean() -> None:
    """Rician construction has E|h|^2=1; sigma=3 dB gives exp((3 ln10/10)^2/2)=1.269452."""

    draw = rician_power_gain(np.random.default_rng(12345), (400_000,))
    assert draw.mean() == pytest.approx(1.0, abs=0.001)
    expected = math.exp(0.5 * (3.0 * math.log(10.0) / 10.0) ** 2)
    assert shadow_linear_mean(3.0) == pytest.approx(expected, rel=1e-15)
    assert expected == pytest.approx(1.269452, abs=5e-7)


def test_action_history_free_component_key() -> None:
    """world/user/NORAD/absolute-time/component fixes the seed; ordering and renewal labels are absent."""

    key = keyed_component_seed(7, 2, 12345, 99_000_000, "rician")
    reordered = [
        keyed_component_seed(7, user, 12345, 99_000_000, "rician")
        for user in (9, 2, 1)
    ]
    assert reordered[1] == key
    assert keyed_component_seed(7, 2, 12345, 99_000_000, "shadow") != key


def test_bessel_accuracy_around_mu_34() -> None:
    """Independent mpmath J1/J3 reference at mu=34 matches the V0.25 gain formula."""

    mpmath.mp.dps = 60
    mu = mpmath.mpf(34)
    half_power = mpmath.radians(mpmath.mpf("3.32") / 2)
    theta = mpmath.degrees(mpmath.asin(mu * mpmath.sin(half_power) / mpmath.mpf("2.07123")))
    bracket = mpmath.besselj(1, mu) / (2 * mu) + 36 * mpmath.besselj(3, mu) / mu**3
    expected = 2000 * bracket**2
    actual = float(transmit_gain_linear(float(theta)))
    assert actual == pytest.approx(float(expected), rel=2e-10, abs=1e-15)


def test_old_system_and_recurrence_outputs_unchanged() -> None:
    """Historical p=.825*(2/1)=1.65 and P=5.927900454+.338+.2=6.465900454 remain byte-path controls."""

    required = recurrence_power_w(np.array([2.0]), np.array([1.0]), p0_w=0.825)
    assert required.tolist() == [1.65]
    power = system_power_w(np.array([5.927900454219553]), np.array([1.0]))
    assert power == pytest.approx(6.465900454219553, abs=1e-14)
