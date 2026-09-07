"""W-132 -- pure projected non-focal externality (PNFE) C3 target."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_pnfe import (
    PNFEFormulaError,
    PNFEOffset,
    build_pnfe_surface,
)


def _offset(
    baseline: list[float],
    inserted: dict[int, list[float]],
    *,
    active: tuple[int, ...] | None = None,
) -> PNFEOffset:
    victims = len(baseline)
    with_focal = np.tile(np.asarray(baseline, dtype=np.float64), (NUM_ACTIONS, 1))
    for action, rates in inserted.items():
        with_focal[action] = np.asarray(rates, dtype=np.float64)
    focal_active = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    focal_active[list(inserted if active is None else active)] = True
    return PNFEOffset(
        background_rate_bps=np.asarray(baseline, dtype=np.float64),
        inserted_rate_bps=with_focal,
        focal_active=focal_active,
    )


def _legal() -> np.ndarray:
    result = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    result[:3] = True
    return result


def test_pdf_ruling_uses_opening_plus_mean_of_available_future_offsets() -> None:
    opening = _offset([10.0, 20.0], {0: [9.0, 18.0], 1: [8.0, 17.0], 2: [10.0, 20.0]})
    future_1 = _offset([12.0, 22.0], {0: [11.0, 20.0], 1: [9.0, 20.0], 2: [12.0, 22.0]})
    future_2 = _offset([14.0, 24.0], {0: [13.0, 21.0], 1: [12.0, 20.0], 2: [14.0, 24.0]})

    surface = build_pnfe_surface(
        legal_mask=_legal(),
        reference_action=0,
        opening=opening,
        future=(future_1, future_2),
        step_index=0,
        total_steps=3,
        interval_s=2.0,
        kappa_bits=10.0,
    )

    # e0 = (-6, -10, 0), mean future = ((-6 + -8)/2,
    # (-10 + -12)/2, 0), so X = (-13, -21, 0) bit.
    np.testing.assert_allclose(surface.x3_bits[:3], [-13.0, -21.0, 0.0])
    np.testing.assert_allclose(surface.z3_bits[:3], [0.0, -8.0, 13.0])
    np.testing.assert_allclose(surface.q3_values[:3], [0.0, -0.8, 1.3])
    assert surface.horizon == 2
    assert surface.reference_action == 0


def test_terminal_anchor_uses_opening_only_and_keeps_raw_negative_sign() -> None:
    opening = _offset([5.0], {0: [4.0], 1: [3.0], 2: [5.0]})
    surface = build_pnfe_surface(
        legal_mask=_legal(),
        reference_action=1,
        opening=opening,
        future=(),
        step_index=4,
        total_steps=5,
        interval_s=3.0,
        kappa_bits=6.0,
    )

    np.testing.assert_allclose(surface.x3_bits[:3], [-3.0, -6.0, 0.0])
    np.testing.assert_allclose(surface.q3_values[:3], [0.5, 0.0, 1.0])
    assert surface.horizon == 0


def test_inactive_focal_segment_has_exactly_zero_externality() -> None:
    opening = _offset(
        [10.0],
        {0: [1.0], 1: [2.0], 2: [3.0]},
        active=(0, 2),
    )
    surface = build_pnfe_surface(
        legal_mask=_legal(),
        reference_action=0,
        opening=opening,
        future=(),
        step_index=0,
        total_steps=1,
        interval_s=1.0,
        kappa_bits=1.0,
    )

    assert surface.externality_bits[0, 1] == 0.0
    assert surface.x3_bits[1] == 0.0


def test_identical_background_branches_are_neutral_and_illegal_rows_zero() -> None:
    opening = _offset([7.0, 11.0], {0: [7.0, 11.0], 1: [7.0, 11.0], 2: [7.0, 11.0]})
    surface = build_pnfe_surface(
        legal_mask=_legal(),
        reference_action=0,
        opening=opening,
        future=(),
        step_index=0,
        total_steps=1,
    )

    assert np.array_equal(surface.q3_values, np.zeros(NUM_ACTIONS))
    assert np.array_equal(surface.x3_bits, np.zeros(NUM_ACTIONS))


def test_formula_rejects_missing_future_offsets_and_bad_reference() -> None:
    opening = _offset([1.0], {0: [1.0], 1: [1.0], 2: [1.0]})
    with pytest.raises(PNFEFormulaError, match="every required future offset"):
        build_pnfe_surface(
            legal_mask=_legal(),
            reference_action=0,
            opening=opening,
            future=(),
            step_index=0,
            total_steps=2,
        )
    with pytest.raises(PNFEFormulaError, match="legal reference"):
        build_pnfe_surface(
            legal_mask=_legal(),
            reference_action=4,
            opening=opening,
            future=(),
            step_index=0,
            total_steps=1,
        )


def test_offset_rejects_negative_or_misaligned_rates() -> None:
    with pytest.raises(PNFEFormulaError, match="non-negative"):
        PNFEOffset(
            background_rate_bps=np.array([-1.0]),
            inserted_rate_bps=np.zeros((NUM_ACTIONS, 1)),
            focal_active=np.zeros(NUM_ACTIONS, dtype=np.bool_),
        )
    with pytest.raises(PNFEFormulaError, match="inserted_rate_bps"):
        PNFEOffset(
            background_rate_bps=np.array([1.0]),
            inserted_rate_bps=np.zeros((NUM_ACTIONS - 1, 1)),
            focal_active=np.zeros(NUM_ACTIONS, dtype=np.bool_),
        )
