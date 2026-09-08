"""Clock, event, matrix-order, and shared-tape adapter known answers."""

from __future__ import annotations

import json

import numpy as np
import pytest

from mcrl.env.d2 import D2Config, D2Tracker
from mcrl.env.dwell import DwellConfig, segments_per_service_window
from mcrl.errors import MCRLContractError
from mcrl.physics_v025.adapter import (
    build_shared_tape,
    score_setting,
    track_b_regeneration_adapter,
)
from mcrl.physics_v025.architectures import Geometry, Link, RadiationConfig
from mcrl.physics_v025.channel import is_visible, noise_power_w
from mcrl.physics_v025.energy import HardwareInventory
from mcrl.physics_v025.integration import (
    BoundarySample,
    InterruptionEvent,
    integrate_47_subintervals,
    integrate_trapezoidal,
    snapshot_terminal,
)
from mcrl.physics_v025.matrix import MATRIX_SETTINGS, PhysicsSetting, shared_computation_plan


def sample(time_s: float, rate: float, power: float = 1.0, served: bool = True) -> BoundarySample:
    return BoundarySample(time_s, {0: rate}, power, {0: served})


def test_rate_t_integral_and_terminal_snapshot_known_answers() -> None:
    """Integral_0^30.08 t dt=30.08^2/2=452.4032; terminal hold=30.08^2=904.8064."""

    points = tuple(sample(index * 0.640, index * 0.640) for index in range(48))
    integrated = integrate_47_subintervals(points)
    terminal = snapshot_terminal(points[-1], start_s=0.0)
    assert integrated.bits[0] == pytest.approx(452.4032, abs=1e-10)
    assert terminal.bits[0] == pytest.approx(904.8064, abs=1e-10)


def test_round1_two_second_time_fixture() -> None:
    """For R(t)=2+t on [0,2], trapezoid=(2+4)/2*2=6; left snapshot=2*2=4."""

    receipt = integrate_trapezoidal((sample(0.0, 2.0), sample(2.0, 4.0)))
    assert receipt.bits[0] == 6.0
    assert 2.0 * 2.0 == 4.0


def test_explicit_duplicate_time_discontinuity_avoids_cross_jump_area() -> None:
    """A step 1->0 at t=.5 integrates 1*.5 + 0*.5=.5, not trapezoid 0.5 over all by accident."""

    points = (
        sample(0.0, 1.0, served=True),
        sample(0.5, 1.0, served=True),
        sample(0.5, 0.0, served=False),
        sample(1.0, 0.0, served=False),
    )
    receipt = integrate_trapezoidal(points)
    assert receipt.bits[0] == 0.5
    assert receipt.decoding_time_s[0] == 0.5


def test_interruption_is_union_clipped_once_and_keeps_rf_draw() -> None:
    """[0,.062] U [0.03,.172] removes .172*10=1.72 bits; energy stays 1 W*1 s."""

    events = (
        InterruptionEvent(0, 0.0, "same_satellite_beam_change"),
        InterruptionEvent(0, 0.03, "satellite_change"),
        InterruptionEvent(0, 0.2, "initial_entry"),
        InterruptionEvent(0, 0.3, "reentry"),
    )
    receipt = integrate_trapezoidal(
        (sample(0.0, 10.0), sample(1.0, 10.0)),
        interruptions=events,
        interruption_enabled=True,
    )
    assert receipt.bits[0] == pytest.approx(10.0 - 1.72)
    assert receipt.joules == 1.0
    assert receipt.useful_time_s[0] == pytest.approx(1.0 - 0.172)
    assert [event.kind for event in receipt.event_log][-2:] == ["initial_entry", "reentry"]


def test_d2_visibility_and_dwell_arithmetic() -> None:
    """After TTT, 1000->1100 km stays latched; 5<10 degrees; 378/(4*30.08)=3.141 periods."""

    tracker = D2Tracker(np.array([99]), 1, D2Config(ttt_steps=2))
    for step_index in range(3):
        state = tracker.update(
            step_index,
            slant_range_km=np.array([[1000.0]]),
            altitude_km=np.array([550.0]),
            range_rate_km_s=np.array([[0.0]]),
        )
    assert state.eligible[0, 0]
    held = tracker.update(
        3,
        slant_range_km=np.array([[1100.0]]),
        altitude_km=np.array([550.0]),
        range_rate_km_s=np.array([[0.0]]),
    )
    assert held.eligible[0, 0]
    assert not is_visible(5.0) and is_visible(10.0)
    assert segments_per_service_window(DwellConfig(4), service_window_s=378.0, time_step_s=30.08) == pytest.approx(3.141, abs=0.001)


def test_matrix_exact_sealed_order_digests_and_no_baseline_relabel() -> None:
    """15 eligible priorities are sealed; aU/bU/a'U append as diagnostic-only, totaling 18."""

    expected = [
        "a0", "b0", "a\u20320", "aS", "bS", "a\u2032S", "aH", "bH", "a\u2032H",
        "aSH", "bSH", "a\u2032SH", "aT", "bT", "a\u2032T", "aU", "bU", "a\u2032U",
    ]
    assert [setting.label for setting in MATRIX_SETTINGS] == expected
    assert len({setting.digest for setting in MATRIX_SETTINGS}) == 18
    plan = shared_computation_plan()
    assert plan["all_neutral_control_label"] == "ALL_NEUTRAL_CONTROL"
    assert "BASELINE" not in json.dumps(plan)


def test_matrix_rejects_undeclared_factorial_corner() -> None:
    """Snapshot+standby is outside the declared fractional 18-cell design."""

    setting = PhysicsSetting("a", "T", "f", "off", "ACM")
    with pytest.raises(MCRLContractError):
        _ = setting.treatment


def test_estimate_exposes_144_equivalent_shared_plan() -> None:
    """Three architectures*(one snapshot+47 intervals)=144, costing 144*302*4/3600=48.32 core-h."""

    plan = shared_computation_plan(q=2.0)
    assert plan["shared_physical_equivalents"] == 3 * (1 + 47) == 144
    assert plan["reference_core_hours"] == pytest.approx(48.32)
    assert plan["estimated_core_hours"] == pytest.approx(96.64)
    assert plan["rescore_from_integrated_tape"] == ["S", "H", "SH", "U"]


def test_shared_tape_rescores_standby_handover_and_u_without_reradiation() -> None:
    """S raises E; H removes 62 ms of bits only; U=log2(1+3) exceeds local ACM rate."""

    bandwidth = 8.0
    direct = 3.0 * noise_power_w(bandwidth) / 1.65
    current = Geometry((Link(0, (1, 1), 0, direct),), np.zeros((1, 1)))
    samples = tuple((index * 0.640, current) for index in range(48))
    inventory = HardwareInventory.fixed(((1, 1), (1, 2)))  # second chain exposes standby.
    tape = build_shared_tape("b", samples, inventory, config=RadiationConfig(bandwidth_hz=bandwidth))
    by_label = {setting.label: setting for setting in MATRIX_SETTINGS}
    zero = score_setting(tape, by_label["b0"])
    standby = score_setting(tape, by_label["bS"])
    interrupted = score_setting(
        tape,
        by_label["bH"],
        interruptions=(InterruptionEvent(0, 0.0, "same_satellite_beam_change"),),
    )
    upper = score_setting(tape, by_label["bU"])
    assert standby.joules > zero.joules
    assert interrupted.joules == pytest.approx(zero.joules)
    assert interrupted.bits[0] == pytest.approx(zero.bits[0] * (30.08 - 0.062) / 30.08)
    assert upper.bits[0] == pytest.approx(8.0 * 2.0 * 30.08)
    assert upper.bits[0] > zero.bits[0]


def test_track_b_dependency_injection_hook_returns_bound_profile() -> None:
    """The Track-B seam binds lever metadata while using the declared bT engine cell."""

    direct = 3.0 * noise_power_w(1.0) / 1.65
    current = Geometry((Link(0, (1, 1), 0, direct),), np.zeros((1, 1)))
    result = track_b_regeneration_adapter(
        lever_id="L1",
        identity="synthetic",
        keyed_fading_event="physics",
        continuation="ORIGINAL_PHYSICS_REFERENCE_ONLY",
        v025_setting=next(setting for setting in MATRIX_SETTINGS if setting.label == "bT"),
        v025_geometry_samples=tuple((index * 0.640, current) for index in range(48)),
        v025_inventory=HardwareInventory.fixed(((1, 1),)),
    )
    assert result["status"] == "COMPLETE"
    assert result["keyed_fading_event"] == "physics"
    assert result["profile"]["setting"]["treatment"] == "T"
