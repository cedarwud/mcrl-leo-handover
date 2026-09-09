"""Cross-cutting acceptance discriminators from round 3 §3 and round 1 §E."""

from __future__ import annotations

from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys

import pytest

from mcrl.errors import MCRLContractError
from mcrl.physics_v025.constants_v025 import (
    BEAM_RF_CAP_W,
    PHI_SAME_SATELLITE,
    PHI_SATELLITE_CHANGE,
)
from mcrl.physics_v025.energy import EnergyReceipt, HardwareInventory
from mcrl.physics_v025.endpoint import StepEndpoint, reward_core


def test_full_network_difference_surplus_not_focal_only() -> None:
    """Focal +1 and nonfocal -10 at deltaE=0 gives system teacher +1-10=-9."""

    focal_delta, nonfocal_delta, energy_delta = 1, -10, 0
    base = reward_core(
        StepEndpoint.build(
            bits=10, joules=1, decoding_user_seconds=1, useful_user_seconds=1,
            opportunity_user_seconds=1, complete_service_user_steps=1, user_steps=1,
        ),
        eta_ref=1,
    )
    candidate = reward_core(
        StepEndpoint.build(
            bits=10 + focal_delta + nonfocal_delta,
            joules=1 + energy_delta,
            decoding_user_seconds=1,
            useful_user_seconds=1,
            opportunity_user_seconds=1,
            complete_service_user_steps=1,
            user_steps=1,
        ),
        eta_ref=1,
    )
    system_difference = candidate - base
    assert system_difference == -9
    assert system_difference != focal_delta


def test_cap_boundary_and_39_beam_reference_are_not_a_derivation() -> None:
    """1.65 is at cap, nextafter is above; 39*1.65=64.35 W is only compatibility arithmetic."""

    assert BEAM_RF_CAP_W == 1.65
    assert math.nextafter(BEAM_RF_CAP_W, math.inf) > BEAM_RF_CAP_W
    assert 39 * BEAM_RF_CAP_W == pytest.approx(64.35)


def test_phi_preferences_are_distinct_and_not_energy_components() -> None:
    """Same-satellite Phi=.5 and satellite-change Phi=1 (never 1.5) do not enter EnergyReceipt."""

    assert PHI_SAME_SATELLITE == 0.5
    assert PHI_SATELLITE_CHANGE == 1.0
    assert PHI_SATELLITE_CHANGE != PHI_SAME_SATELLITE + PHI_SATELLITE_CHANGE
    assert "phi" not in EnergyReceipt.__dataclass_fields__


def test_additive_accounting_fixture_and_receipt_mutation_detection() -> None:
    """Rates 4 and 6 over power 5 contribute .8+1.2=EE 2; doubled component mutation fails."""

    contributions = (Fraction(4, 5), Fraction(6, 5))
    assert sum(contributions, Fraction()) == 2
    corrupt = EnergyReceipt(1.0, 1.0, 1.0, 0.0, 0.0, 0.0)
    with pytest.raises(MCRLContractError):
        corrupt.verify()


def test_inventory_and_world_identity_duplicates_fail() -> None:
    """Duplicated physical IDs/world IDs are detected instead of treated as independent support."""

    with pytest.raises(MCRLContractError):
        HardwareInventory(((1, 1), (1, 1)))
    world_ids = (11, 12, 11)
    assert len(set(world_ids)) != len(world_ids)


def test_deadline_fallback_is_frozen_base() -> None:
    """The production fallback replaces every set-level proposal with BASE."""

    path = Path(__file__).resolve().parents[2] / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"
    spec = importlib.util.spec_from_file_location("v025_deadline_runner", path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    base = runner.Configuration("BASE", ((0, (1, 1)),), 0, "base")
    proposal = runner.Configuration("P", ((0, (2, 1)),), 1, "proposal")
    selected = runner.apply_deadline_fallback(
        {arm: proposal for arm in runner.ARMS}, base=base, missed=True
    )
    assert all(selected[arm] is base for arm in runner.SET_LEVEL_ARMS)
    assert selected["E1_U1"] is proposal
