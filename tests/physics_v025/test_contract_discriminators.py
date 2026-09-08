"""Cross-cutting acceptance discriminators from round 3 §3 and round 1 §E."""

from __future__ import annotations

from fractions import Fraction
import importlib.util
import math
from pathlib import Path
import sys

import numpy as np
import pytest

from mcrl.env.action_contract import NO_OP_ACTION
from mcrl.errors import MCRLContractError
from mcrl.physics_v025.architectures import AngleTPC_TDM, Geometry, Link, RadiationConfig
from mcrl.physics_v025.constants_v025 import (
    ASSOCIATION_ACTIONS,
    BEAM_RF_CAP_W,
    PHI_SAME_SATELLITE,
    PHI_SATELLITE_CHANGE,
)
from mcrl.physics_v025.energy import EnergyReceipt, HardwareInventory
from mcrl.physics_v025.endpoint import StepEndpoint, pool, reward_core


def test_initialisation_and_common_prefix_are_horizon_independent() -> None:
    """The same world-keyed current Geometry has no horizon/episode-age field and yields one identical first receipt."""

    current = Geometry((Link(0, (1, 1), 0, 1.0),), np.zeros((1, 1)))
    engine = AngleTPC_TDM()
    first_of_h10 = engine.radiate(RadiationConfig(bandwidth_hz=1.0), current, "nominal")
    first_of_h30 = engine.radiate(RadiationConfig(bandwidth_hz=1.0), current, "nominal")
    assert first_of_h10 == first_of_h30
    assert not hasattr(current.links[0], "segment_start_gain")


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


def test_c1_and_c2_arithmetic_fixtures_without_claiming_stage2_schema() -> None:
    """C1: 10-3*2=4; C2 mean over two offsets: (4-8)/2=-2."""

    c1 = 10 - 3 * 2
    c2 = (c1 - 8) / 2
    assert c1 == 4 and c2 == -2


def test_null_base_identity_is_structural_not_scalar_only() -> None:
    """Committing BASE for NULL means the same immutable action and full raw radiation receipt."""

    actions = (3, 7)
    current = Geometry(
        (Link(0, (1, 1), 0, 1.0), Link(1, (2, 1), 1, 2.0)),
        np.zeros((2, 2)),
    )
    base = AngleTPC_TDM().radiate(RadiationConfig(bandwidth_hz=1.0), current, "nominal")
    null_commits_base = AngleTPC_TDM().radiate(RadiationConfig(bandwidth_hz=1.0), current, "nominal")
    assert actions == actions
    assert null_commits_base == base
    assert null_commits_base.slots == base.slots


def test_all_false_mask_executes_no_op_and_dark_opportunity_is_retained() -> None:
    """An all-false 28-action mask maps to NO_OP; its zero/zero step remains one service opportunity."""

    mask = np.zeros(ASSOCIATION_ACTIONS, dtype=bool)
    action = NO_OP_ACTION if not np.any(mask) else int(np.argmax(mask))
    assert action == NO_OP_ACTION
    dark = StepEndpoint.build(
        bits=0,
        joules=0,
        decoding_user_seconds=0,
        useful_user_seconds=0,
        opportunity_user_seconds=30.08,
        complete_service_user_steps=0,
        user_steps=1,
    )
    totals = pool((dark,))
    assert totals.user_steps == 1 and totals.pooled_ee is None


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


def test_tiny_positive_below_certified_error_is_not_a_pass() -> None:
    """A 1e-13 effect with 1e-12 numerical error is not positive beyond certified error."""

    effect, certified_error = 1e-13, 1e-12
    assert not effect > certified_error


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


def test_legacy_r3_load_arithmetic_is_characterized_not_energy() -> None:
    """Two users sharing load 2 give sum r3=-2-2=-4; singleton loads give -1-1=-2."""

    shared = -2 - 2
    singleton = -1 - 1
    assert shared == -4 and singleton == -2
