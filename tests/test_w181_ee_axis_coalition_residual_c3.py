"""W-181 -- pure V0.22 named-coalition C3 residual mechanics."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_coalition_residual_c3 import (
    COALITION_RESIDUAL_C3_SCHEMA,
    CoalitionResidualC3Error,
    CoalitionResidualC3Result,
    build_coalition_residual_c3,
)


def _public_good_kwargs() -> dict[str, object]:
    """Only the two-user move together can retire the shared source beam."""

    legal = np.zeros((2, 4), dtype=np.bool_)
    legal[:, 0] = True
    legal[0, 1] = True
    legal[1, 2] = True
    return {
        "B0_v": np.asarray([100.0, 100.0]),
        "E0": 10.0,
        # Either unilateral move loses ten own bits and leaves energy unchanged:
        # the other user still keeps the shared source beam active.
        "Bu": np.asarray([[90.0, 100.0], [100.0, 90.0]]),
        "Eu": np.asarray([10.0, 10.0]),
        # Only the joint move retires the beam and saves five joules.
        "BC": np.asarray([100.0, 100.0]),
        "EC": 5.0,
        "coalition_user_ids": np.asarray([0, 1], dtype=np.int64),
        "proposed_actions": np.asarray([1, 2], dtype=np.int64),
        "lambda_bits_per_j": 1.0,
        "kappa_bits": 2.0,
        "action_count": 4,
        "reference_actions": np.asarray([0, 0], dtype=np.int64),
        "legal_mask": legal,
    }


def _three_user_kwargs() -> dict[str, object]:
    """A two-member coalition with one non-member row for sparse-surface tests."""

    legal = np.zeros((3, 5), dtype=np.bool_)
    legal[:, 0] = True
    legal[0, 1] = True
    legal[2, 3] = True
    return {
        "B0_v": np.asarray([100.0, 80.0, 60.0]),
        "E0": 10.0,
        "Bu": np.asarray([[90.0, 100.0, 60.0], [100.0, 75.0, 70.0]]),
        "Eu": np.asarray([8.0, 9.0]),
        "BC": np.asarray([95.0, 95.0, 74.0]),
        "EC": 7.0,
        "coalition_user_ids": np.asarray([0, 2], dtype=np.int64),
        "proposed_actions": np.asarray([1, 3], dtype=np.int64),
        "lambda_bits_per_j": 2.0,
        "kappa_bits": 5.0,
        "action_count": 5,
        "reference_actions": np.asarray([0, 0, 0], dtype=np.int64),
        "legal_mask": legal,
    }


def _physical_scale_cancellation_kwargs() -> dict[str, object]:
    """A valid identity whose large intermediate terms nearly cancel.

    These values are a minimized deterministic reproduction of the V0.23
    source-gate failure class.  The final joint surplus is only about 2.85e4
    bits while the underlying per-user bit totals are O(1e11).  IEEE-754
    roundoff therefore has to be bounded from the arithmetic work scale, not
    only from the small final ``lhs`` and ``rhs`` values.
    """

    legal = np.zeros((2, 4), dtype=np.bool_)
    legal[:, 0] = True
    legal[0, 1] = True
    legal[1, 2] = True
    return {
        "B0_v": np.asarray([605035526899.4789, 35818623467.93558]),
        "E0": 1000.0,
        "Bu": np.asarray(
            [
                [605022863453.9861, 35831688300.729614],
                [605063155861.6459, 35824157607.71982],
            ]
        ),
        "Eu": np.asarray([1000.804215736796, 1000.9537805128198]),
        "BC": np.asarray([605040645185.1671, 35834419392.13486]),
        "EC": 1000.1763631196809,
        "coalition_user_ids": np.asarray([0, 1], dtype=np.int64),
        "proposed_actions": np.asarray([1, 2], dtype=np.int64),
        "lambda_bits_per_j": 118424222.8550065,
        "kappa_bits": 10097071012.757404,
        "action_count": 4,
        "reference_actions": np.asarray([0, 0], dtype=np.int64),
        "legal_mask": legal,
    }


def _build(values: dict[str, object]) -> CoalitionResidualC3Result:
    return build_coalition_residual_c3(**values)


def test_exact_two_user_public_good_beam_shutdown_numeric_example() -> None:
    result = _build(_public_good_kwargs())

    np.testing.assert_allclose(result.own_bits, [-10.0, -10.0])
    np.testing.assert_allclose(result.nonfocal_bits, [0.0, 0.0])
    np.testing.assert_allclose(result.d_bits, [-10.0, -10.0])
    assert result.joint_delta_bits == pytest.approx(0.0)
    assert result.joint_delta_energy_j == pytest.approx(-5.0)
    assert result.joint_surplus_bits == pytest.approx(5.0)
    assert result.interaction_bits == pytest.approx(20.0)
    assert result.interaction_energy_j == pytest.approx(-5.0)
    assert result.interaction_surplus_bits == pytest.approx(25.0)
    assert result.equal_share_bits == pytest.approx(12.5)
    np.testing.assert_allclose(result.z3_bits, [12.5, 12.5])
    np.testing.assert_allclose(result.combined_bits, [2.5, 2.5])


def test_z3_equals_exact_two_player_shapley_value_of_residual_game() -> None:
    result = _build(_public_good_kwargs())

    # Residual game: V(empty)=0, V({i})=e_i, and the full coalition owns the
    # joint surplus after removing the two focal/own terms l_i.  The standard
    # two-player Shapley formula is
    # phi_i = 1/2 * (V({i}) - V(empty) + V({1,2}) - V({other})).
    v_empty = 0.0
    v_single = np.asarray(result.nonfocal_bits, dtype=np.float64)
    v_full = float(result.joint_surplus_bits - np.sum(result.own_bits))
    shapley = np.asarray(
        [
            0.5 * (v_single[0] - v_empty + v_full - v_single[1]),
            0.5 * (v_single[1] - v_empty + v_full - v_single[0]),
        ],
        dtype=np.float64,
    )

    np.testing.assert_allclose(result.z3_bits, shapley)
    np.testing.assert_allclose(result.z3_bits, v_single + result.equal_share_bits)


def test_interaction_bits_and_energy_split_and_identity() -> None:
    result = _build(_public_good_kwargs())

    assert result.interaction_bits == pytest.approx(
        result.joint_delta_bits
        - sum(
            float(np.sum(row - result.reference_bits))
            for row in result.unilateral_bits
        )
    )
    assert result.interaction_energy_j == pytest.approx(
        result.joint_delta_energy_j
        - sum(float(energy - result.reference_energy_j) for energy in result.unilateral_energy_j)
    )
    assert result.interaction_surplus_bits == pytest.approx(
        result.interaction_bits
        - result.lambda_bits_per_j * result.interaction_energy_j
    )
    assert sum(result.combined_bits) == pytest.approx(result.joint_surplus_bits)
    assert result.verify() == pytest.approx(result.identity_residual_bits)
    assert result.identity_residual_bits == pytest.approx(0.0, abs=1e-12)
    assert result.schema == COALITION_RESIDUAL_C3_SCHEMA


def test_sparse_surface_has_only_member_proposals_and_exact_zero_fill() -> None:
    result = _build(_three_user_kwargs())
    q3 = result.q3_values

    assert q3.shape == (3, 5)
    assert q3[0, 1] == pytest.approx(result.z3_bits[0] / result.kappa_bits)
    assert q3[2, 3] == pytest.approx(result.z3_bits[1] / result.kappa_bits)
    assert q3[0, 0] == 0.0  # member reference cell
    assert q3[2, 0] == 0.0  # member reference cell
    assert np.all(q3[1] == 0.0)  # non-member row
    assert q3[0, 2] == 0.0  # other action
    assert q3[2, 1] == 0.0  # other action
    assert np.all(q3[~result.legal_mask] == 0.0)  # illegal cells
    assert np.all(np.isfinite(q3))


def test_result_is_frozen_and_all_arrays_are_input_independent_read_only() -> None:
    values = _three_user_kwargs()
    before = np.array(values["B0_v"], copy=True)
    result = _build(values)

    values["B0_v"][0] = 9999.0  # type: ignore[index]
    np.testing.assert_array_equal(result.reference_bits, before)
    with pytest.raises(FrozenInstanceError):
        result.kappa_bits = 9.0  # type: ignore[misc]
    for field in (
        "reference_bits",
        "unilateral_bits",
        "unilateral_energy_j",
        "joint_bits",
        "coalition_user_ids",
        "proposed_actions",
        "reference_actions",
        "legal_mask",
        "own_bits",
        "nonfocal_bits",
        "d_bits",
        "z3_bits",
        "combined_bits",
        "q3_values",
    ):
        array = getattr(result, field)
        assert not array.flags.writeable, field
        with pytest.raises(ValueError):
            array.flat[0] = array.flat[0]


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        (
            "coalition_user_ids",
            np.asarray([0, 0], dtype=np.int64),
            "unique",
        ),
        (
            "coalition_user_ids",
            np.asarray([0], dtype=np.int64),
            "at least two",
        ),
        (
            "proposed_actions",
            np.asarray([0, 2], dtype=np.int64),
            "differ",
        ),
        (
            "proposed_actions",
            np.asarray([3, 2], dtype=np.int64),
            "illegal",
        ),
        (
            "Bu",
            np.asarray([[90.0, 100.0, 0.0], [100.0, 90.0, 0.0]]),
            "shape",
        ),
        (
            "legal_mask",
            np.zeros((2, 3), dtype=np.bool_),
            "shape",
        ),
    ],
)
def test_validation_rejects_coalition_and_shape_errors(
    field: str, replacement: object, message: str
) -> None:
    values = _public_good_kwargs()
    values[field] = replacement
    with pytest.raises(CoalitionResidualC3Error, match=message):
        _build(values)


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("B0_v", np.asarray([np.nan, 100.0]), "finite"),
        ("Bu", np.asarray([[np.inf, 100.0], [100.0, 90.0]]), "finite"),
        ("BC", np.asarray([100.0, np.nan]), "finite"),
        ("E0", np.nan, "finite"),
        ("B0_v", np.asarray([-1.0, 100.0]), "non-negative"),
        ("Bu", np.asarray([[-1.0, 100.0], [100.0, 90.0]]), "non-negative"),
        ("BC", np.asarray([100.0, -1.0]), "non-negative"),
        ("E0", 0.0, "positive"),
        ("Eu", np.asarray([0.0, 5.0]), "positive"),
        ("EC", -1.0, "positive"),
        ("lambda_bits_per_j", 0.0, "positive"),
        ("kappa_bits", -1.0, "positive"),
    ],
)
def test_validation_rejects_nonfinite_domain_and_scale_errors(
    field: str, replacement: object, message: str
) -> None:
    values = _public_good_kwargs()
    values[field] = replacement
    with pytest.raises(CoalitionResidualC3Error, match=message):
        _build(values)


def test_action_width_alias_defaults_to_native_num_actions() -> None:
    values = _public_good_kwargs()
    values.pop("action_count")
    legal = np.zeros((2, NUM_ACTIONS), dtype=np.bool_)
    legal[:, 0] = True
    legal[0, 1] = True
    legal[1, 2] = True
    values["legal_mask"] = legal
    result = build_coalition_residual_c3(**values, A=NUM_ACTIONS)
    assert result.action_count == NUM_ACTIONS
    assert result.q3_values.shape == (2, NUM_ACTIONS)


def test_positive_joint_surplus_can_leave_one_negative_member_combined_score() -> None:
    values = _public_good_kwargs()
    values.update(
        {
            "Bu": np.asarray([[80.0, 100.0], [100.0, 100.0]]),
            "Eu": np.asarray([10.0, 10.0]),
            "BC": np.asarray([105.0, 105.0]),
            "EC": 9.0,
            "lambda_bits_per_j": 1.0,
        }
    )
    result = _build(values)

    assert result.joint_surplus_bits > 0.0
    assert result.combined_bits[0] < 0.0
    assert result.combined_bits[1] > 0.0
    # This is a valid coalition identity; the negative member score is a
    # diagnostic outcome, not a reason for verify() to reject the target.
    assert result.verify() == pytest.approx(result.identity_residual_bits)


def test_physical_scale_cancellation_is_not_misclassified_as_identity_corruption() -> None:
    result = _build(_physical_scale_cancellation_kwargs())

    assert abs(result.identity_residual_bits) < 1.0e-6
    assert result.verify() == result.identity_residual_bits


def test_material_combined_value_corruption_still_fails_closed() -> None:
    result = _build(_public_good_kwargs())
    corrupted = np.array(result.combined_bits, copy=True)
    corrupted[0] += 1.0

    with pytest.raises(CoalitionResidualC3Error, match="combined_bits"):
        replace(result, combined_bits=corrupted)
