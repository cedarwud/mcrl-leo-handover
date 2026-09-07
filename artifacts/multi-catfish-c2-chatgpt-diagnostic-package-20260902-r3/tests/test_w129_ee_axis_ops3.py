"""W-129 -- OPS-3 formula-only mechanics gate.

These tests intentionally stop at the formula/adapter boundary.  They do not
open TLE outcomes, run an episode, train Q2, or make an EE efficacy claim.
The physical rate/SINR values in the fixtures are already action-aligned
adapter outputs; recurrence and network power are computed through the
canonical environment helpers by :mod:`mcrl.runtime.ee_axis_ops3`.
"""

from __future__ import annotations

import copy
import inspect

import numpy as np
import pytest

from mcrl.env.link_budget import BASEBAND_POWER_PER_SATELLITE_W
from mcrl.runtime.ee_axis_ops3 import (
    OPS3_FEATURE_DIM,
    OPS3_HORIZON,
    OPS3_INTERVAL_S,
    OPS3_KAPPA_BITS,
    OPS3_LAMBDA_BITS_PER_J,
    OPS3FormulaError,
    OPS3FrozenBackground,
    OPS3Offset,
    build_ops3_surface,
    canonical_network_power_w,
    collect_ops3_offsets,
    marginal_network_power_surface,
    segment_start_gain_surface,
)


NATIVE = 28
LEGAL_ACTIONS = np.array([0, 1, 7, 8], dtype=np.int64)


def _action_identity() -> tuple[np.ndarray, np.ndarray]:
    """Four physical actions: same beam, same satellite/new beam, new sat."""

    norad = np.full(NATIVE, -1, dtype=np.int64)
    cell = np.full(NATIVE, -1, dtype=np.int64)
    norad[0], cell[0] = 100, 1  # existing background beam
    norad[1], cell[1] = 100, 2  # new beam on an active satellite
    norad[7], cell[7] = 101, 1  # new beam and new satellite
    norad[8], cell[8] = 101, 2  # another new beam on the new satellite
    return norad, cell


def _legal_mask() -> np.ndarray:
    mask = np.zeros(NATIVE, dtype=np.bool_)
    mask[LEGAL_ACTIONS] = True
    return mask


def _background() -> OPS3FrozenBackground:
    return OPS3FrozenBackground(
        norad_ids=np.array([100], dtype=np.int64),
        cell_ids=np.array([1], dtype=np.int64),
        load=np.array([2], dtype=np.int64),
        power_w=np.array([0.5], dtype=np.float64),
    )


def _offsets(*, failing_action: int | None = None) -> tuple[OPS3Offset, ...]:
    """Small deterministic adapter receipts with one deliberately negative row."""

    d2 = np.zeros(NATIVE, dtype=np.bool_)
    visible = np.zeros(NATIVE, dtype=np.bool_)
    d2[LEGAL_ACTIONS] = True
    visible[LEGAL_ACTIONS] = True
    gains = np.zeros(NATIVE, dtype=np.float64)
    gains[0], gains[1], gains[7], gains[8] = 0.8, 0.7, 0.6, 0.5
    rates = np.zeros(NATIVE, dtype=np.float64)
    rates[0], rates[1], rates[7], rates[8] = 10.0, 9.0, 7.0, 0.01
    sinr = np.zeros(NATIVE, dtype=np.float64)
    sinr[LEGAL_ACTIONS] = [1.0, 2.0, 3.0, 4.0]
    first = OPS3Offset(gains, d2, visible, rates, sinr)

    second_d2 = d2.copy()
    if failing_action is not None:
        second_d2[failing_action] = False
    second = OPS3Offset(
        gains * 0.95,
        second_d2,
        visible,
        rates,
        sinr,
    )
    third_d2 = d2.copy()
    third = OPS3Offset(
        gains * 0.90,
        third_d2,
        visible,
        rates,
        sinr,
    )
    return (first, second, third)


def _surface(
    *,
    step_index: int = 0,
    total_steps: int = 4,
    reference_action: int = 0,
    offsets: tuple[OPS3Offset, ...] | None = None,
    lambda_bits_per_j: float = 1.0,
    kappa_bits: float = 100.0,
    interval_s: float = 1.0,
    p0_w: float = 0.5,
    pmax_w: float = 1.0,
):
    norad, cell = _action_identity()
    return build_ops3_surface(
        legal_mask=_legal_mask(),
        reference_action=reference_action,
        candidate_norad_ids=norad,
        candidate_cell_ids=cell,
        segment_start_gain_linear=np.where(_legal_mask(), 1.0, 0.0),
        offsets=_offsets() if offsets is None else offsets,
        background=_background(),
        user_count=4,
        step_index=step_index,
        total_steps=total_steps,
        p0_w=p0_w,
        pmax_w=pmax_w,
        lambda_bits_per_j=lambda_bits_per_j,
        kappa_bits=kappa_bits,
        interval_s=interval_s,
    )


def test_terminal_horizon_is_all_zero_legal_surface():
    surface = _surface(step_index=3, total_steps=4, offsets=())
    assert surface.horizon == 0
    assert np.all(surface.z2_bits == 0.0)
    assert np.all(surface.q2_values == 0.0)
    assert np.all(surface.features == 0.0)
    assert np.all(surface.required_power_w == 0.0)


def test_reference_row_is_exact_zero_and_candidate_reference_is_safe():
    surface = _surface(reference_action=0)
    assert surface.q2_values[0] == 0.0
    assert np.isfinite(surface.z2_bits[0])
    assert surface.features.shape == (NATIVE, OPS3_FEATURE_DIM)
    assert all(not array.flags.writeable for array in (
        surface.z2_bits,
        surface.q2_values,
        surface.features,
    ))


def test_changing_gauge_action_changes_only_a_constant_on_legal_rows():
    first = _surface(reference_action=0)
    second = _surface(reference_action=1)
    delta = second.q2_values[LEGAL_ACTIONS] - first.q2_values[LEGAL_ACTIONS]
    np.testing.assert_allclose(delta, delta[0], rtol=0, atol=1e-15)
    np.testing.assert_allclose(first.z2_bits, second.z2_bits, rtol=0, atol=0)


def test_absorbing_loss_is_exactly_minus_kappa_and_no_energy_credit():
    offsets = _offsets(failing_action=7)
    surface = _surface(offsets=offsets, kappa_bits=100.0, interval_s=1.0)
    assert surface.persistence[:, 7].tolist() == [1.0, 0.0, 0.0]
    # The final two offsets are outage terms; each is exactly -kappa after
    # averaging, while the successful first term is positive here.
    assert surface.rate_bps[2, 7] == 0.0
    assert surface.marginal_power_w[2, 7] == 0.0
    assert surface.sinr_linear[2, 7] == 0.0
    assert surface.z2_bits[7] < 0.0
    assert surface.z2_bits[7] != pytest.approx(-100.0)

    all_fail = _surface(offsets=_offsets(failing_action=0), kappa_bits=100.0)
    # Action 0 has a positive first forecast; use an explicit all-failure
    # receipt to pin the exact no-credit penalty.
    failed = []
    for value in _offsets():
        failed.append(
            OPS3Offset(
                value.projected_gain_linear,
                np.zeros(NATIVE, dtype=np.bool_),
                value.cell_visible,
                value.focal_rate_bps,
                value.focal_sinr_linear,
            )
        )
    all_fail = _surface(offsets=tuple(failed), kappa_bits=100.0)
    assert all_fail.z2_bits[0] == -100.0
    assert all_fail.marginal_power_w[:, 0].tolist() == [0.0, 0.0, 0.0]


def test_horizon_mean_and_frozen_constants_are_numerically_pinned():
    assert OPS3_LAMBDA_BITS_PER_J.hex() == "0x1.443a8f481639ap+26"
    assert OPS3_KAPPA_BITS.hex() == "0x1.2cea89d260f2ap+33"
    assert OPS3_INTERVAL_S.hex() == "0x1.e147ae147ae14p+4"

    failed = tuple(
        OPS3Offset(
            value.projected_gain_linear,
            np.zeros(NATIVE, dtype=np.bool_),
            value.cell_visible,
            value.focal_rate_bps,
            value.focal_sinr_linear,
        )
        for value in _offsets()
    )
    surface = _surface(offsets=failed, kappa_bits=100.0)
    # Three identical -kappa offset terms remain -kappa after the required
    # 1/H mean.  A sum implementation would incorrectly return -300 here.
    assert surface.z2_bits[0] == -100.0


def test_over_ceiling_power_is_retained_in_feature_and_service_fails():
    first = _offsets()[0]
    gains = first.projected_gain_linear.copy()
    gains[0] = 0.2  # p_hat = 0.5 * 1.0 / 0.2 = 2.5 > pmax 1.0
    over = OPS3Offset(
        gains,
        first.d2_eligible,
        first.cell_visible,
        first.focal_rate_bps,
        first.focal_sinr_linear,
    )
    surface = _surface(
        step_index=0,
        total_steps=2,
        offsets=(over,),
        kappa_bits=100.0,
    )
    assert surface.required_power_w[0, 0] == pytest.approx(2.5)
    assert surface.features[0, 6] == pytest.approx(2.5)
    assert surface.persistence[0, 0] == 0.0
    assert surface.rate_bps[0, 0] == 0.0
    assert surface.sinr_linear[0, 0] == 0.0
    assert surface.marginal_power_w[0, 0] == 0.0
    assert surface.z2_bits[0] == -100.0


@pytest.mark.parametrize(
    ("step_index", "offset_count", "zero_from"),
    ((2, 1, 8), (1, 2, 12)),
)
def test_near_terminal_horizon_zero_fills_unavailable_feature_blocks(
    step_index: int,
    offset_count: int,
    zero_from: int,
):
    surface = _surface(
        step_index=step_index,
        total_steps=4,
        offsets=_offsets()[:offset_count],
    )
    assert surface.horizon == offset_count
    assert np.all(surface.features[:, zero_from:] == 0.0)
    assert np.all(surface.required_power_w[offset_count:] == 0.0)
    assert np.all(surface.persistence[offset_count:] == 0.0)


def test_null_gain_keeps_zero_required_power_without_creating_a_beam():
    values = list(_offsets())
    for index, value in enumerate(values):
        gains = value.projected_gain_linear.copy()
        if index == 0:
            gains[8] = 0.0
        values[index] = OPS3Offset(
            gains,
            value.d2_eligible,
            value.cell_visible,
            value.focal_rate_bps,
            value.focal_sinr_linear,
        )
    surface = _surface(offsets=tuple(values))
    assert surface.required_power_w[0, 8] == 0.0
    assert surface.persistence[0, 8] == 0.0
    assert surface.marginal_power_w[0, 8] == 0.0


def test_service_loss_is_absorbing_even_when_later_offset_recovers():
    offsets = list(_offsets(failing_action=1))
    recovered_d2 = np.ones(NATIVE, dtype=np.bool_)
    recovered_visible = np.ones(NATIVE, dtype=np.bool_)
    offsets[2] = OPS3Offset(
        offsets[2].projected_gain_linear,
        recovered_d2,
        recovered_visible,
        offsets[2].focal_rate_bps,
        offsets[2].focal_sinr_linear,
    )
    surface = _surface(offsets=tuple(offsets))
    assert surface.persistence[:, 1].tolist() == [1.0, 0.0, 0.0]
    assert surface.rate_bps[2, 1] == 0.0
    assert surface.sinr_linear[2, 1] == 0.0


def test_shared_beam_max_and_new_beam_satellite_activation_use_canonical_power():
    norad, cell = _action_identity()
    legal = _legal_mask()
    powers = np.zeros(NATIVE, dtype=np.float64)
    powers[LEGAL_ACTIONS] = 0.5
    delta = marginal_network_power_surface(
        background=_background(),
        candidate_norad_ids=norad,
        candidate_cell_ids=cell,
        candidate_power_w=powers,
        legal_mask=legal,
    )
    # Existing beam max(0.5,0.5) leaves RF/PA power unchanged.
    assert delta[0] == 0.0
    assert delta[1] > 0.0  # new beam, same active satellite
    assert delta[7] > delta[1]  # new beam plus new satellite baseband
    assert delta[7] - delta[1] == pytest.approx(BASEBAND_POWER_PER_SATELLITE_W)
    assert canonical_network_power_w(_background()) > 0.0


def test_deterministic_median_channel_uses_no_rng_and_collects_only_future_offsets():
    calls: list[int] = []
    state = {"counter": 17, "payload": [1, 2, 3]}
    before = copy.deepcopy(state)

    class Provider:
        def project_offset(self, offset: int, *, action_count: int) -> OPS3Offset:
            calls.append(offset)
            assert action_count == NATIVE
            return _offsets()[offset - 1]

    provider = Provider()
    rng = np.random.default_rng(902)
    rng_state = copy.deepcopy(rng.bit_generator.state)
    offsets = collect_ops3_offsets(provider, action_count=NATIVE)
    surface = _surface(offsets=offsets)
    assert calls == [1, 2, 3]
    assert state == before
    assert rng.bit_generator.state == rng_state
    np.testing.assert_array_equal(surface.q2_values, _surface(offsets=offsets).q2_values)


def test_formula_evaluation_does_not_touch_cloned_d2_adapter_state():
    # The actual TLE/D2 clone belongs to the external provider.  This test
    # pins the explicit seam: once immutable receipts are handed to the
    # formula, live provider state is not read or mutated by build_ops3_surface.
    class Provider:
        def __init__(self):
            self.live_tracker = {"latched": np.array([[True, False]]), "seen": 12}

        def project_offset(self, offset: int, *, action_count: int) -> OPS3Offset:
            return _offsets()[offset - 1]

    provider = Provider()
    before = copy.deepcopy(provider.live_tracker)
    receipts = collect_ops3_offsets(provider, action_count=NATIVE)
    _surface(offsets=receipts)
    assert provider.live_tracker["seen"] == before["seen"]
    np.testing.assert_array_equal(provider.live_tracker["latched"], before["latched"])


def test_every_legal_row_is_finite_negative_signs_are_retained_and_mask_is_safe():
    surface = _surface()
    assert np.all(np.isfinite(surface.z2_bits))
    assert np.all(np.isfinite(surface.q2_values))
    assert np.all(np.isfinite(surface.features))
    assert np.any(surface.z2_bits[LEGAL_ACTIONS] < 0.0)
    assert np.all(surface.q2_values[~_legal_mask()] == 0.0)
    chosen = int(np.argmax(np.where(_legal_mask(), surface.q2_values, -np.inf)))
    assert bool(_legal_mask()[chosen])
    with pytest.raises(OPS3FormulaError, match="duplicate physical"):
        norad, cell = _action_identity()
        cell[1] = cell[0]
        build_ops3_surface(
            legal_mask=_legal_mask(),
            reference_action=0,
            candidate_norad_ids=norad,
            candidate_cell_ids=cell,
            segment_start_gain_linear=np.where(_legal_mask(), 1.0, 0.0),
            offsets=_offsets(),
            background=_background(),
            user_count=4,
            step_index=0,
            total_steps=4,
        )


def test_segment_start_uses_committed_gain_only_for_continuing_physical_link():
    norad, cell = _action_identity()
    gains = np.zeros(NATIVE, dtype=np.float64)
    gains[LEGAL_ACTIONS] = [0.9, 0.8, 0.7, 0.6]
    result = segment_start_gain_surface(
        candidate_norad_ids=norad,
        candidate_cell_ids=cell,
        current_gain_linear=gains,
        current_association=(100, 1),
        committed_start_gain_linear=0.42,
        legal_mask=_legal_mask(),
    )
    assert result[0] == 0.42
    assert result[1] == 0.8
    assert result[7] == 0.7
    assert result[8] == 0.6


def test_no_h0_future_action_or_fallback_enters_formula_boundary():
    source = inspect.getsource(collect_ops3_offsets)
    assert "range(1, horizon + 1)" in source
    assert "project_offset(0" not in source
    assert "fallback" not in inspect.getsource(build_ops3_surface).lower()
    class Provider:
        def __init__(self):
            self.offsets: list[int] = []

        def project_offset(self, offset: int, *, action_count: int) -> OPS3Offset:
            self.offsets.append(offset)
            return _offsets()[offset - 1]

    provider = Provider()
    collect_ops3_offsets(provider, action_count=NATIVE, horizon=2)
    assert provider.offsets == [1, 2]
    assert OPS3_HORIZON == 3


def test_invalid_inputs_fail_closed_before_formula_output():
    with pytest.raises(OPS3FormulaError, match="native 28"):
        build_ops3_surface(
            legal_mask=np.ones(4, dtype=np.bool_),
            reference_action=0,
            candidate_norad_ids=np.arange(4),
            candidate_cell_ids=np.arange(4),
            segment_start_gain_linear=np.ones(4),
            offsets=(OPS3Offset.zeros(4),),
            background=_background(),
            user_count=1,
            step_index=0,
            total_steps=4,
        )
    with pytest.raises(OPS3FormulaError, match="p0_w must be positive"):
        _surface(p0_w=0.0)
