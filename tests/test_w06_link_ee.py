"""Eq. (3.17)/(3.25) — the per-link EE display quantity and r1.

Ruling C-7 (2026-08-22) withdrew the per-link ``kappa`` power share: (3.17)
divides by the COMMON system power, and the paper says the result "不宣稱為
private-power 的 true per-user EE".  ``tests/test_w06_per_ue_ee.py`` tested
the withdrawn closure and was removed with it.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime import energy_efficiency
from mcrl.runtime.energy_efficiency import (
    link_energy_efficiency,
    r1_energy_efficiency,
)


def test_the_kappa_closure_is_gone():
    """C-7: not disabled, removed — a share layer is a different quantity."""
    assert not hasattr(energy_efficiency, "per_ue_energy_efficiency")
    assert not hasattr(energy_efficiency, "PerLinkEnergyEfficiency")
    assert not hasattr(energy_efficiency, "EPSILON_NUM")


def test_eta_is_the_rate_over_the_common_system_power():
    rates = np.array([1.0e7, 2.0e7, 0.0])
    eta = link_energy_efficiency(rates, 4.0)
    assert np.allclose(eta, rates / 4.0)


def test_r1_is_additive_across_users_by_construction():
    """Summing r1 recovers the system EE exactly — the decomposition property."""
    rates = np.array([1.0e7, 2.5e7, 0.0, 4.0e6])
    power = 3.3
    r1 = r1_energy_efficiency(rates, power)
    assert float(r1.sum()) == pytest.approx(float(rates.sum()) / power, rel=1e-12)


def test_an_unserved_user_contributes_nothing():
    r1 = r1_energy_efficiency(np.array([0.0, 1.0e7]), 2.0)
    assert r1[0] == 0.0


def test_zero_power_with_throughput_raises():
    """P-7 again: the same policy per link as per system."""
    with pytest.raises(MCRLContractError, match="zero system power"):
        link_energy_efficiency(np.array([1.0e6]), 0.0)


def test_zero_over_zero_is_zero_not_an_epsilon_inflated_number():
    assert float(link_energy_efficiency(np.array([0.0]), 0.0)[0]) == 0.0


def test_no_epsilon_appears_in_the_denominator():
    import inspect

    source = inspect.getsource(link_energy_efficiency)
    assert "1e-12" not in source
    assert "epsilon" not in source.lower() or "forbids" in source.lower()


def test_negative_and_non_finite_inputs_are_refused():
    with pytest.raises(MCRLContractError, match="finite and non-negative"):
        link_energy_efficiency(np.array([-1.0]), 1.0)
    with pytest.raises(MCRLContractError, match="finite and non-negative"):
        link_energy_efficiency(np.array([float("nan")]), 1.0)
    with pytest.raises(MCRLContractError, match="system power"):
        link_energy_efficiency(np.array([1.0]), -1.0)
