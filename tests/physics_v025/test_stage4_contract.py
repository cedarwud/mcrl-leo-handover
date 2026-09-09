from __future__ import annotations

from fractions import Fraction
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import pytest

from mcrl.physics_v025.endpoint import calibration
from mcrl.errors import MCRLContractError
from mcrl.physics_v025.calibration import assert_calibration_world_separation
from mcrl.physics_v025.tapes import (
    CALIBRATION_WORLD_DOMAINS,
    PROBE_WORLD_DOMAINS,
    TinySyntheticProvider,
    build_world_tape,
)
from mcrl.physics_v025.targets import (
    NetworkOutcome,
    c1_difference_surplus,
    c3_lcsrs_interaction,
    c3_set_interaction,
)


REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"


def _outcome(bits: int, energy: int) -> NetworkOutcome:
    return NetworkOutcome.build(
        bits=bits,
        joules=energy,
        phi=0,
        decoding_availability=1,
        useful_availability=1,
    )


def _runner():
    spec = importlib.util.spec_from_file_location("v025_stage4_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_c3_is_interaction_only_for_binding_energy_fixture() -> None:
    interaction = c3_lcsrs_interaction(
        coalition_users=(3, 9),
        f00=_outcome(20, 10),
        f10=_outcome(20, 10),
        f01=_outcome(20, 10),
        f11=_outcome(20, 8),
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=1,
    )
    assert interaction.psi == 2
    assert interaction.z3_by_user == ((3, 1), (9, 1))


def test_whole_network_c1_plus_pair_c3_counts_joint_change_once() -> None:
    f00, f10, f01, f11 = (
        _outcome(20, 10),
        _outcome(23, 11),
        _outcome(24, 11),
        _outcome(30, 12),
    )
    c1_first = c1_difference_surplus(
        f10, f00, lambda_bits_per_j=1, eta_ref=1, kappa_bits_per_user_step=1
    )
    c1_second = c1_difference_surplus(
        f01, f00, lambda_bits_per_j=1, eta_ref=1, kappa_bits_per_user_step=1
    )
    c3 = c3_lcsrs_interaction(
        coalition_users=(0, 1),
        f00=f00,
        f10=f10,
        f01=f01,
        f11=f11,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=1,
    )
    asserted = c1_first.difference_surplus_bits + c1_second.difference_surplus_bits
    asserted += sum((value for _, value in c3.z3_by_user), Fraction())
    assert asserted == (f11.bits - f00.bits) - (f11.joules - f00.joules)


def test_three_user_shapley_interaction_is_asymmetric_and_conservative() -> None:
    values = {
        frozenset(): 0,
        frozenset({0}): 1,
        frozenset({1}): 2,
        frozenset({2}): 3,
        frozenset({0, 1}): 5,
        frozenset({0, 2}): 7,
        frozenset({1, 2}): 8,
        frozenset({0, 1, 2}): 15,
    }
    outcomes = {subset: _outcome(value + 20, 20) for subset, value in values.items()}
    result = c3_set_interaction(
        coalition_users=(0, 1, 2),
        outcomes_by_subset=outcomes,
        lambda_bits_per_j=1,
        eta_ref=1,
        kappa_bits_per_user_step=1,
    )
    credits = dict(result.z3_by_user)
    assert len(set(credits.values())) > 1
    assert sum(credits.values(), Fraction()) == result.set_interaction == 9


def test_kappa_is_per_user_decision_step_not_seconds() -> None:
    _eta, first = calibration(
        bits=1200,
        joules=12,
        users=3,
        decision_steps=4,
        time_s=30.08,
    )
    _eta, doubled_time = calibration(
        bits=1200,
        joules=12,
        users=3,
        decision_steps=4,
        time_s=60.16,
    )
    _eta, doubled_bits = calibration(
        bits=2400,
        joules=12,
        users=3,
        decision_steps=4,
        time_s=30.08,
    )
    assert first == 100
    assert doubled_time == first
    assert doubled_bits == 2 * first


def test_qos_gate_can_fail_only_availability_margin() -> None:
    runner = _runner()
    rows = tuple(
        {
            "full_bits": 101.0,
            "full_joules": 100.0,
            "comparator_bits": 100.0,
            "comparator_joules": 100.0,
            "full_qos": 0.89,
            "comparator_qos": 0.90,
            "full_phi_cost_per_user_step": 1.0,
            "comparator_phi_cost_per_user_step": 1.0,
            "full_handover_rate": 1.0,
            "comparator_handover_rate": 1.0,
        }
        for _ in range(4)
    )
    result = runner.pooled_ratio_cluster_bootstrap(rows, draws=128, seed=9)
    assert result["qos_availability_lower_95"] < -0.005
    assert result["phi_priced_handover_cost_relative_upper_95"] == 0
    assert result["handover_rate_relative_upper_95"] == 0
    assert result["qos_noninferior"] is False


def test_world_separation_rejects_provider_date_layout_collision() -> None:
    calibration_tapes = tuple(
        build_world_tape(
            domain=domain,
            provider=TinySyntheticProvider(),
            steps=1,
            start_time_s=0,
        )
        for domain in CALIBRATION_WORLD_DOMAINS
    )
    probe = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=TinySyntheticProvider(),
        steps=1,
        start_time_s=0,
    )
    collision = replace(
        probe,
        tle_date=calibration_tapes[0].tle_date,
        user_layout=calibration_tapes[0].user_layout,
    )
    with pytest.raises(MCRLContractError, match="colliding"):
        assert_calibration_world_separation(
            calibration_tapes=calibration_tapes,
            probe_tapes=(collision,),
        )
