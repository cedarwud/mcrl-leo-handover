"""Small, red-capable regression checks used by the differential audit."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np

from mcrl.env.antenna import RX_ENVELOPE_MIN_DEG, receive_gain_linear
from mcrl.env.interference import RadiatingBeams, co_channel_interference
from mcrl.env.link_budget import BEAM_BANDWIDTH_HZ, noise_power_w, shannon_rate_bps
from mcrl.runtime.ee_axis_ops3 import OPS3_LAMBDA_BITS_PER_J
from mcrl.runtime.energy_efficiency import r1_energy_efficiency

import reference_physics as ref


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TARGET = Path("/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8")
REPRICED = float.fromhex("0x1.c3c0a7b6b86d3p+26")


def test_receive_pattern_uses_correct_s465_branch_and_literal_near_axis_gain() -> None:
    assert ref.RX_TERMINAL_DIAMETER_M / (ref.SPEED_OF_LIGHT_M_S / ref.CARRIER_FREQ_HZ) < 50.0
    assert 2.0 < ref.s465_minimum_angle_deg() < 2.1
    assert RX_ENVELOPE_MIN_DEG > 2.4  # records the implementation's wrong branch
    angles = np.array([0.0, 0.5, 1.0, ref.s465_minimum_angle_deg(), RX_ENVELOPE_MIN_DEG])
    np.testing.assert_allclose(receive_gain_linear(angles), ref.receive_pattern_gain(angles), rtol=1e-15)


def test_interference_membership_excludes_only_serving_physical_beam() -> None:
    radiating = RadiatingBeams(
        norad_ids=np.array([10, 10, 20, 20]),
        cell_ids=np.array([7, 8, 7, 9]),
        satellite_ecef_km=np.zeros((4, 3)),
        cell_centre_ecef_km=np.zeros((4, 3)),
        colors=np.array([0, 0, 0, 1]),
        power_w=np.ones(4),
    )
    result = co_channel_interference(
        np.array([[1.0, 2.0, 4.0, 8.0]]), radiating,
        wanted_norad_ids=np.array([10]), wanted_cell_ids=np.array([7]), wanted_colors=np.array([0]),
    )
    np.testing.assert_array_equal(result.intra_w, [2.0])
    np.testing.assert_array_equal(result.inter_w, [4.0])  # same cell, other satellite


def test_noise_uses_whole_beam_bandwidth_while_rate_splits_bandwidth() -> None:
    assert noise_power_w() == ref.noise_power_w(BEAM_BANDWIDTH_HZ)
    rates = shannon_rate_bps(np.array([3.0, 3.0]), beam_load=np.array([1.0, 2.0]))
    assert rates[0] == 2.0 * rates[1]


def test_rician_is_unit_mean_and_shadow_is_zero_mean_db() -> None:
    rng = np.random.default_rng(4815162342)
    i, q = rng.normal(size=(2, 400_000))
    gain = ref.rician_power_gain_from_standard_normals(i, q)
    assert abs(float(gain.mean()) - 1.0) < 0.003
    shadow = ref.shadow_loss_db_from_standard_normal(30.0, rng.normal(size=400_000))
    assert abs(float(shadow.mean())) < 0.01


def test_repriced_labels_are_live_but_ops3_generator_default_is_stale() -> None:
    payload = json.loads(sorted(TARGET.glob("c2-informed-*.json"))[0].read_text())
    assert float.fromhex(payload["lambda_bits_per_j"]) == REPRICED
    assert OPS3_LAMBDA_BITS_PER_J != REPRICED


def test_modqn_bootstraps_each_head_from_its_own_target_network() -> None:
    source = (REPO / "src/mcrl/algorithms/modqn.py").read_text()
    tree = ast.parse(source)
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Subscript)
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "target_nets"
    ]
    assert any(isinstance(call.func.slice, ast.Name) and call.func.slice.id == "obj_idx" for call in calls)


def test_r1_sum_of_contributions_is_instantaneous_ratio_of_sums() -> None:
    rates = np.array([10.0, 20.0, 0.0, 5.0])
    power = 7.0
    contributions = r1_energy_efficiency(rates, power)
    assert float(contributions.sum()) == float(rates.sum() / power)
    # Averaging per-link efficiencies would be a different and wrong endpoint.
    assert float(contributions.mean()) != float(rates.sum() / power)
