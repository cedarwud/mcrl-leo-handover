from __future__ import annotations

import inspect
from dataclasses import replace

import numpy as np

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_ops3 import (
    OPS3FrozenBackground,
    OPS3Offset,
    build_ops3_surface,
)

from target_parity_suite.declared_c3_oracle import (
    DecisionProfile,
    declared_c3_oracle,
    executed_unilateral_c3,
)
from target_parity_suite.ops3_parity import build_ops3_surface_explicit
from target_parity_suite.physics_extractor import assert_reward_endpoint_identity


REPRICED_LAMBDA = float.fromhex("0x1.c3c0a7b6b86d3p+26")
OLD_LAMBDA = float.fromhex("0x1.443a8f481639ap+26")
KAPPA = float.fromhex("0x1.2cea89d260f2ap+33")


def astra_lambda_fixture() -> dict[str, object]:
    """The fixed-rate, energy-only OPS-3 fixture behind C.3."""

    required_power_w = 0.8816077060513188
    legal = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    legal[:2] = True
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    norads[:2] = 100
    cells[:2] = (1, 2)
    gains = np.zeros(NUM_ACTIONS, dtype=np.float64)
    gains[:2] = 1.0
    rates = np.zeros(NUM_ACTIONS, dtype=np.float64)
    rates[:2] = 1.0e9
    eligible = legal.copy()
    sinr = gains.copy()
    offsets = tuple(
        OPS3Offset(gains, eligible, eligible, rates, sinr) for _ in range(3)
    )
    return {
        "legal_mask": legal,
        "opening_service_feasible": legal,
        "reference_action": 0,
        "candidate_norad_ids": norads,
        "candidate_cell_ids": cells,
        "segment_start_gain_linear": gains,
        "offsets": offsets,
        "background": OPS3FrozenBackground(
            np.array([100], dtype=np.int64),
            np.array([1], dtype=np.int64),
            np.array([1], dtype=np.int64),
            np.array([required_power_w], dtype=np.float64),
        ),
        "user_count": 2,
        "step_index": 0,
        "total_steps": 4,
        "p0_w": required_power_w,
        "pmax_w": 1.65,
        "kappa_bits": KAPPA,
        "interval_s": 30.08,
    }


def nonbinding_demand_cap(inputs: dict[str, object], demand_bps: float = 2.0e9) -> dict[str, object]:
    """Apply the oracle's rate cap transform; this fixture remains unchanged."""

    capped = dict(inputs)
    capped["offsets"] = tuple(
        replace(offset, focal_rate_bps=np.minimum(offset.focal_rate_bps, demand_bps))
        for offset in inputs["offsets"]
    )
    for before, after in zip(inputs["offsets"], capped["offsets"], strict=True):
        np.testing.assert_array_equal(before.focal_rate_bps, after.focal_rate_bps)
    return capped


def test_legacy_default_reproduces_nonbinding_cap_lambda_defect() -> None:
    inputs = astra_lambda_fixture()
    uncapped = build_ops3_surface(**inputs)
    nonbinding_cap = build_ops3_surface(
        **nonbinding_demand_cap(inputs), lambda_bits_per_j=REPRICED_LAMBDA
    )
    np.testing.assert_allclose(uncapped.q2_values[1], -1.637204, rtol=0, atol=5e-7)
    np.testing.assert_allclose(nonbinding_cap.q2_values[1], -2.281140, rtol=0, atol=5e-7)
    assert uncapped.q2_values[1] != nonbinding_cap.q2_values[1]


def test_successor_requires_explicit_lambda_and_nonbinding_cap_is_invariant() -> None:
    parameter = inspect.signature(build_ops3_surface_explicit).parameters[
        "lambda_bits_per_j"
    ]
    assert parameter.default is inspect.Parameter.empty
    inputs = astra_lambda_fixture()
    uncapped = build_ops3_surface_explicit(
        **inputs, lambda_bits_per_j=REPRICED_LAMBDA
    )
    nonbinding_cap = build_ops3_surface_explicit(
        **nonbinding_demand_cap(inputs), lambda_bits_per_j=REPRICED_LAMBDA
    )
    np.testing.assert_array_equal(uncapped.q2_values, nonbinding_cap.q2_values)


def test_declared_c3_fixture_and_atomic_selection() -> None:
    profiles = tuple(
        DecisionProfile(bits=np.array([0.0, 0.0]), energy_j=energy)
        for energy in (10.0, 10.0, 10.0, 8.0)
    )
    result = declared_c3_oracle(*profiles, lambda_bits_per_j=1.0, users=(0, 1))
    np.testing.assert_array_equal(executed_unilateral_c3(*profiles[:3], users=(0, 1)), [0.0, 0.0])
    assert result.f00 == -10.0
    assert result.psi == 2.0
    np.testing.assert_array_equal(result.z3, [1.0, 1.0])
    assert result.atomic_selection.profile == "11"
    assert result.atomic_selection.users == (0, 1)


def test_declared_matches_executed_when_interaction_is_zero() -> None:
    p00 = DecisionProfile(np.array([10.0, 20.0]), 5.0)
    p10 = DecisionProfile(np.array([12.0, 23.0]), 6.0)
    p01 = DecisionProfile(np.array([14.0, 19.0]), 7.0)
    p11 = DecisionProfile(np.array([16.0, 22.0]), 8.0)
    result = declared_c3_oracle(p00, p10, p01, p11, lambda_bits_per_j=2.0)
    np.testing.assert_array_equal(
        result.z3, executed_unilateral_c3(p00, p10, p01, users=(0, 1))
    )


def test_reward_endpoint_identity() -> None:
    assert_reward_endpoint_identity(
        step_bits=[10.0, 20.0, 5.0],
        step_energy_j=[1.0, 3.0, 2.0],
        step_rewards=[8.0, 14.0, 1.0],
        eta_bits_per_j=2.0,
        endpoint_bits=35.0,
        endpoint_energy_j=6.0,
    )
