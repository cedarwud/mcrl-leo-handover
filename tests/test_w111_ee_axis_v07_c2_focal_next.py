"""W-111 -- formula-first V0.7 C2 focal-next target."""

from __future__ import annotations

from dataclasses import asdict
import math

import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_v07_c2_focal_next import (
    V07_C2_TARGET_SCHEMA,
    focal_next_surplus_target,
)


def _target(**overrides: float):
    values = {
        "lambda_bits_per_j": 10.0,
        "interval_s": 2.0,
        "candidate_focal_rate_bps": 18.0,
        "reference_focal_rate_bps": 10.0,
        "candidate_full_power_w": 30.0,
        "candidate_without_focal_power_w": 24.0,
        "reference_full_power_w": 25.0,
        "reference_without_focal_power_w": 21.0,
    }
    values.update(overrides)
    return focal_next_surplus_target(**values)


def test_focal_next_target_uses_rate_and_marginal_power_differences() -> None:
    target = _target()

    assert target.schema == V07_C2_TARGET_SCHEMA
    assert target.candidate_focal_rate_bps == pytest.approx(18.0)
    assert target.reference_focal_rate_bps == pytest.approx(10.0)
    assert target.candidate_focal_marginal_power_w == pytest.approx(6.0)
    assert target.reference_focal_marginal_power_w == pytest.approx(4.0)
    assert target.focal_next_rate_delta_bits == pytest.approx(16.0)
    assert target.focal_next_marginal_energy_delta_j == pytest.approx(4.0)
    assert target.z2_focal_next_surplus_bits == pytest.approx(-24.0)


def test_branch_swap_reverses_every_signed_component() -> None:
    forward = _target()
    reverse = focal_next_surplus_target(
        lambda_bits_per_j=10.0,
        interval_s=2.0,
        candidate_focal_rate_bps=10.0,
        reference_focal_rate_bps=18.0,
        candidate_full_power_w=25.0,
        candidate_without_focal_power_w=21.0,
        reference_full_power_w=30.0,
        reference_without_focal_power_w=24.0,
    )

    assert reverse.focal_next_rate_delta_bits == -forward.focal_next_rate_delta_bits
    assert (
        reverse.focal_next_marginal_energy_delta_j
        == -forward.focal_next_marginal_energy_delta_j
    )
    assert reverse.z2_focal_next_surplus_bits == -forward.z2_focal_next_surplus_bits


def test_matched_branches_produce_exact_zero_control() -> None:
    target = _target(
        candidate_focal_rate_bps=10.0,
        candidate_full_power_w=25.0,
        candidate_without_focal_power_w=21.0,
    )

    assert target.focal_next_rate_delta_bits == 0.0
    assert target.focal_next_marginal_energy_delta_j == 0.0
    assert target.z2_focal_next_surplus_bits == 0.0


def test_negative_marginal_power_is_retained_instead_of_clipped() -> None:
    target = _target(
        candidate_full_power_w=20.0,
        candidate_without_focal_power_w=22.0,
    )

    assert target.candidate_focal_marginal_power_w == -2.0
    assert target.z2_focal_next_surplus_bits > target.focal_next_rate_delta_bits


@pytest.mark.parametrize(
    "field,value",
    [
        ("lambda_bits_per_j", 0.0),
        ("interval_s", -1.0),
        ("candidate_focal_rate_bps", -1.0),
        ("reference_focal_rate_bps", math.inf),
        ("candidate_full_power_w", math.nan),
        ("candidate_without_focal_power_w", -0.1),
        ("reference_full_power_w", -0.1),
        ("reference_without_focal_power_w", math.inf),
    ],
)
def test_invalid_public_inputs_fail_closed(field: str, value: float) -> None:
    with pytest.raises(MCRLContractError, match=field):
        _target(**{field: value})


def test_public_receipt_contains_only_scalar_formula_terms() -> None:
    payload = asdict(_target())

    assert set(payload) == {
        "z2_focal_next_surplus_bits",
        "focal_next_rate_delta_bits",
        "focal_next_marginal_energy_delta_j",
        "candidate_focal_rate_bps",
        "reference_focal_rate_bps",
        "candidate_focal_marginal_power_w",
        "reference_focal_marginal_power_w",
        "candidate_full_power_w",
        "candidate_without_focal_power_w",
        "reference_full_power_w",
        "reference_without_focal_power_w",
        "lambda_bits_per_j",
        "interval_s",
        "schema",
    }
    assert all(
        isinstance(value, (int, float, str))
        for value in payload.values()
    )
