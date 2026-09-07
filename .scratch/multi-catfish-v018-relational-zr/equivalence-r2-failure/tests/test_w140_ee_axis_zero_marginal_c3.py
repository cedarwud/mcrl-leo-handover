"""W-140 -- V0.12 pure zero-marginal C3 formula mechanics."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.runtime.ee_axis_zero_marginal_c3 import (
    ZeroMarginalC3Error,
    assert_surface_identity,
    build_bit_exact_compatibility,
    build_hr_surface,
    build_zr_surface,
    compatibility_falsifiers,
    validate_surface_identity,
)


def _panel(*, victims: int = 2):
    baseline = np.zeros(victims, dtype=np.float64)
    candidate = np.zeros((28, victims), dtype=np.float64)
    legal = np.zeros(28, dtype=np.bool_)
    legal[:5] = True
    compatible = np.zeros(28, dtype=np.bool_)
    compatible[[0, 2, 4]] = True
    return baseline, candidate, legal, compatible


def test_zr_splits_negative_and_positive_rate_deltas_and_centres_reference() -> None:
    baseline, candidate, legal, compatible = _panel()
    baseline[:] = [10.0, 20.0]
    candidate[0] = [10.0, 20.0]  # exact reference row
    candidate[1] = [9.0, 22.0]   # -1 + gated +2 => -1 when g is false
    candidate[2] = [12.0, 21.0]  # +3 + +1, both credited when g is true
    candidate[3] = [8.0, 18.0]   # illegal row must be zero in the surface

    surface = build_zr_surface(
        baseline_rate_bps=baseline,
        candidate_rate_bps=candidate,
        compatibility=compatible,
        legal_mask=legal,
        reference_action=0,
        interval_s=2.0,
        kappa_bits=2.0,
    )

    np.testing.assert_allclose(surface.delta_bits[:3], [[0.0, 0.0], [-2.0, 4.0], [4.0, 2.0]])
    np.testing.assert_allclose(surface.negative_bits[:3], [0.0, -2.0, 0.0])
    np.testing.assert_allclose(surface.positive_bits[:3], [0.0, 4.0, 6.0])
    np.testing.assert_allclose(surface.raw_bits[:3], [0.0, -2.0, 6.0])
    np.testing.assert_allclose(surface.z3_bits[:3], [0.0, -2.0, 6.0])
    np.testing.assert_allclose(surface.q3_values[:3], [0.0, -1.0, 3.0])
    assert np.all(surface.raw_bits[~compatible & legal] <= 0.0)
    assert np.all(surface.z3_bits[~legal] == 0.0)
    assert surface.formula == "ZR"
    assert_surface_identity(surface)


def test_hr_keeps_negative_relief_but_gates_positive_relief() -> None:
    baseline, candidate, legal, compatible = _panel()
    baseline[:] = [10.0, 10.0]
    candidate[0] = [9.0, 10.0]   # reference harm L=1
    candidate[1] = [10.0, 10.0]  # relief +1, but g=false => no positive credit
    candidate[2] = [8.0, 10.0]   # relief -1, retained even though g=false
    candidate[3] = [10.0, 10.0]
    candidate[4] = [10.0, 10.0]  # relief +1 and g=true => positive credit

    surface = build_hr_surface(
        baseline_rate_bps=baseline,
        candidate_rate_bps=candidate,
        compatibility=compatible,
        legal_mask=legal,
        reference_action=0,
        kappa_bits=2.0,
    )

    np.testing.assert_allclose(surface.harm_bits[:5], [1.0, 0.0, 2.0, 0.0, 0.0])
    np.testing.assert_allclose(surface.relief_bits[:5], [0.0, 1.0, -1.0, 1.0, 1.0])
    np.testing.assert_allclose(surface.z3_bits[:5], [0.0, 0.0, -1.0, 0.0, 1.0])
    np.testing.assert_allclose(surface.q3_values[:5], [0.0, 0.0, -0.5, 0.0, 0.5])
    assert np.all(surface.z3_bits[(~compatible) & legal] <= 0.0)
    assert_surface_identity(surface)


def test_compatibility_is_bit_exact_and_preserves_order() -> None:
    served = np.array([1, 0], dtype=np.int8)
    candidate_served = np.repeat(served[None, :], 28, axis=0)
    beams = np.array([4, 1], dtype=np.int64)
    candidate_beams = np.repeat(beams[None, :], 28, axis=0)
    sats = np.array([91, 33], dtype=np.int64)
    candidate_sats = np.repeat(sats[None, :], 28, axis=0)
    rf = np.array([1.5, 2.5], dtype=np.float64)
    candidate_rf = np.repeat(rf[None, :], 28, axis=0)
    power = np.full(28, 7.0, dtype=np.float64)

    result = build_bit_exact_compatibility(
        baseline_served=served,
        candidate_served=candidate_served,
        baseline_active_beams=beams,
        candidate_active_beams=candidate_beams,
        baseline_active_sats=sats,
        candidate_active_sats=candidate_sats,
        baseline_rf_power=rf,
        candidate_rf_power=candidate_rf,
        baseline_network_power=7.0,
        candidate_network_power=power,
    )
    assert np.all(result.g)

    candidate_beams[1] = [1, 4]  # same set, different order: must falsify g
    candidate_sats[2] = [91, 34]
    candidate_rf[3, 1] = np.nextafter(2.5, 3.0)
    power[4] = np.nextafter(7.0, 8.0)
    rf[0] = 0.0
    candidate_rf[:, 0] = 0.0
    candidate_rf[5, 0] = -0.0
    changed = build_bit_exact_compatibility(
        baseline_served=served,
        candidate_served=candidate_served,
        baseline_active_beams=beams,
        candidate_active_beams=candidate_beams,
        baseline_active_sats=sats,
        candidate_active_sats=candidate_sats,
        baseline_rf_power=rf,
        candidate_rf_power=candidate_rf,
        baseline_network_power=7.0,
        candidate_network_power=power,
    )
    assert changed.g.tolist()[1:5] == [False, False, False, False]
    assert not changed.active_beams_equal[1]
    assert not changed.active_sats_equal[2]
    assert not changed.rf_equal[3]
    assert not changed.network_power_equal[4]
    assert not changed.rf_equal[5]
    falsifiers = compatibility_falsifiers(changed)
    assert all(not falsifiers[name][0] for name in (
        "served_vector", "active_beams", "active_sats", "per_beam_rf_vector", "network_power", "g"
    ))
    assert falsifiers["active_beams"][1]
    assert falsifiers["g"][1]


def test_surface_and_compatibility_arrays_are_copied_and_read_only() -> None:
    baseline, candidate, legal, compatible = _panel()
    baseline[:] = [1.0, 2.0]
    candidate[0] = baseline
    candidate[1] = [0.5, 2.5]
    surface = build_zr_surface(
        baseline_rate_bps=baseline,
        candidate_rate_bps=candidate,
        compatibility=compatible,
        legal_mask=legal,
        reference_action=0,
    )
    baseline[0] = 999.0
    candidate[1, 0] = 999.0
    legal[0] = False
    compatible[0] = False
    assert surface.baseline_rate_bps[0] == 1.0
    assert surface.candidate_rate_bps[1, 0] == 0.5
    assert bool(surface.legal_mask[0])
    for value in (
        surface.baseline_rate_bps,
        surface.candidate_rate_bps,
        surface.delta_bits,
        surface.negative_bits,
        surface.positive_bits,
        surface.harm_bits,
        surface.raw_bits,
        surface.relief_bits,
        surface.z3_bits,
        surface.q3_values,
        surface.compatibility,
        surface.legal_mask,
    ):
        assert not value.flags.writeable


def test_malformed_inputs_fail_closed() -> None:
    baseline, candidate, legal, compatible = _panel()
    with pytest.raises(ZeroMarginalC3Error, match="non-negative"):
        bad = baseline.copy()
        bad[0] = -1.0
        build_zr_surface(
            baseline_rate_bps=bad,
            candidate_rate_bps=candidate,
            compatibility=compatible,
            legal_mask=legal,
            reference_action=0,
        )
    with pytest.raises(ZeroMarginalC3Error, match="shape"):
        build_zr_surface(
            baseline_rate_bps=baseline,
            candidate_rate_bps=np.zeros((27, 2)),
            compatibility=compatible,
            legal_mask=legal,
            reference_action=0,
        )
    with pytest.raises(ZeroMarginalC3Error, match="Boolean"):
        build_zr_surface(
            baseline_rate_bps=baseline,
            candidate_rate_bps=candidate,
            compatibility=np.zeros(28, dtype=np.int8),
            legal_mask=legal,
            reference_action=0,
        )
    with pytest.raises(ZeroMarginalC3Error, match="outside legal_mask"):
        bad_gate = compatible.copy()
        bad_gate[27] = True
        build_zr_surface(
            baseline_rate_bps=baseline,
            candidate_rate_bps=candidate,
            compatibility=bad_gate,
            legal_mask=legal,
            reference_action=0,
        )
    with pytest.raises(ZeroMarginalC3Error, match="legal native reference"):
        build_zr_surface(
            baseline_rate_bps=baseline,
            candidate_rate_bps=candidate,
            compatibility=compatible,
            legal_mask=legal,
            reference_action=6,
        )
    with pytest.raises(ZeroMarginalC3Error, match="empty safe mask"):
        build_zr_surface(
            baseline_rate_bps=baseline,
            candidate_rate_bps=candidate,
            compatibility=compatible,
            legal_mask=np.zeros(28, dtype=np.bool_),
            reference_action=0,
        )


def test_identity_helpers_report_reference_and_illegal_zero_conventions() -> None:
    baseline, candidate, legal, compatible = _panel(victims=1)
    candidate[0, 0] = 1.0
    surface = build_hr_surface(
        baseline_rate_bps=baseline,
        candidate_rate_bps=candidate,
        compatibility=compatible,
        legal_mask=legal,
        reference_action=0,
    )
    report = validate_surface_identity(surface)
    assert report.passed
    assert not any(surface_falsifier for surface_falsifier in (
        report.reference_zero is False,
        report.illegal_zero is False,
        report.finite is False,
        report.compatibility_identity is False,
        report.positive_gate_identity is False,
    ))
    assert_surface_identity(surface)
