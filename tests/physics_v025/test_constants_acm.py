"""Independent arithmetic fixtures for the frozen ACM/constants surface."""

from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest

from mcrl.physics_v025.acm import (
    ACMRate,
    ACM_MODES,
    UncappedShannonDiagnosticRate,
    select_mode,
    served_phy,
)
from mcrl.physics_v025.channel import noise_power_w
from mcrl.physics_v025.constants_v025 import (
    ACM_TABLE,
    ACM_TABLE_SHA256,
    BEAM_BANDWIDTH_HZ,
    DECISION_INTERVAL_S,
    IMPLEMENTATION_MARGIN_DB,
    POWER_CONTROL_TARGET_LINEAR,
    ROLL_OFF,
    SINR_MIN,
    SYSTEM_TEMPERATURE_K,
    VERIFY_SOURCE,
    PROVENANCE,
    constant_manifest,
)


def test_table_has_28_rows_and_frozen_hash() -> None:
    """Hash arithmetic: SHA256(canonical JSON of 28 rows) is the frozen digest."""

    encoded = json.dumps(ACM_TABLE, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    assert len(ACM_TABLE) == 28
    assert hashlib.sha256(encoded).hexdigest() == ACM_TABLE_SHA256


@pytest.mark.parametrize(
    ("name", "expected_se", "expected_threshold_db"),
    (
        ("QPSK 1/4", 0.490243 / 1.20, -2.35 + 1.7 - 10 * math.log10(1.20)),
        ("8PSK 2/3", 1.980636 / 1.20, 6.62 + 1.7 - 10 * math.log10(1.20)),
        ("32APSK 9/10", 4.453027 / 1.20, 16.05 + 1.7 - 10 * math.log10(1.20)),
    ),
)
def test_profile_anchor_unit_conversion(name: str, expected_se: float, expected_threshold_db: float) -> None:
    """SE=e/1.20 and gamma=g+1.7-10log10(1.20), each exactly once."""

    mode = next(mode for mode in ACM_MODES if mode.name == name)
    assert mode.spectral_efficiency_bit_per_s_hz == pytest.approx(expected_se, abs=5e-13)
    assert mode.threshold_db == pytest.approx(expected_threshold_db, abs=5e-13)


def test_three_published_profile_anchors() -> None:
    """Rounded anchors are 0.408535833/1.650530000/3.710855833 and -1.441812460/7.528187540/16.958187540."""

    anchors = [ACM_MODES[0], next(m for m in ACM_MODES if m.name == "8PSK 2/3"), ACM_MODES[-1]]
    assert [m.spectral_efficiency_bit_per_s_hz for m in anchors] == pytest.approx(
        [0.408535833, 1.650530000, 3.710855833], abs=5e-10
    )
    assert [m.threshold_db for m in anchors] == pytest.approx(
        [-1.441812460, 7.528187540, 16.958187540], abs=5e-10
    )
    assert POWER_CONTROL_TARGET_LINEAR == pytest.approx(5.660030272, abs=5e-10)


def test_acm_ceiling_and_greatest_efficiency_selection() -> None:
    """At huge SINR the greatest table efficiency is 4.453027/1.20, despite dominated row order."""

    mode = select_mode(1.0e12)
    assert mode is not None and mode.name == "32APSK 9/10"
    assert ACMRate().rate_bps(1.0e12, 1.0) == pytest.approx(4.453027 / 1.20)
    # At 14.0 dB model SINR, 32APSK 3/4 beats lower-efficiency eligible modes.
    selected = select_mode(10.0 ** (14.0 / 10.0))
    assert selected is not None and selected.name == "32APSK 3/4"


def test_service_boundary_is_inclusive_and_adjacent_float_below_fails() -> None:
    """served iff gamma>=10^(-1.441812460/10); nextafter below is unserved."""

    assert served_phy(SINR_MIN)
    assert not served_phy(np.nextafter(SINR_MIN, -math.inf))
    assert not served_phy(SINR_MIN, allocated=False)  # NULL is unserved.
    assert ACMRate().rate_bps(np.nextafter(SINR_MIN, -math.inf), 12.0) == 0.0


def test_two_user_acm_bits_apply_airtime_rolloff_and_duration_once() -> None:
    """12 Hz * (1.980636/1.20) * (1/2 airtime) * 2 s = 19.80636 bits/user."""

    target = next(mode for mode in ACM_MODES if mode.name == "8PSK 2/3")
    full_slot_rate = ACMRate().rate_bps(target.threshold_linear, 12.0)
    per_user_bits = full_slot_rate * 0.5 * 2.0
    assert per_user_bits == pytest.approx(19.80636, abs=1e-12)
    assert 2 * per_user_bits == pytest.approx(39.61272, abs=1e-12)


def test_uncapped_shannon_is_separately_named_margin_off_diagnostic() -> None:
    """At gamma=3 and B=8, U gives 8*log2(4)=16 bit/s; gamma=0 gives zero."""

    diagnostic = UncappedShannonDiagnosticRate()
    assert diagnostic.name == "U_UNCAPPED_SHANNON_MARGIN_OFF"
    assert diagnostic.rate_bps(3.0, 8.0) == 16.0
    assert diagnostic.rate_bps(0.0, 8.0) == 0.0
    assert diagnostic.rate_bps(1.0e12, 1.0) > max(m.spectral_efficiency_bit_per_s_hz for m in ACM_MODES)


def test_clock_band_noise_and_temperature_arithmetic() -> None:
    """T=150+290(10^.12-1), W=500e6/3, dt=47*.640, and N=kTW."""

    expected_temperature = 150.0 + 290.0 * (10.0**0.12 - 1.0)
    expected_noise = 1.380649e-23 * expected_temperature * (500.0e6 / 3.0)
    assert SYSTEM_TEMPERATURE_K == expected_temperature
    assert BEAM_BANDWIDTH_HZ == 500.0e6 / 3.0
    assert DECISION_INTERVAL_S == 47 * 0.640
    assert DECISION_INTERVAL_S == pytest.approx(30.08, abs=1e-14)
    assert noise_power_w(BEAM_BANDWIDTH_HZ) == pytest.approx(expected_noise, rel=1e-15)
    assert expected_noise == pytest.approx(5.5754e-13, rel=2e-5)
    assert ROLL_OFF == 0.20 and IMPLEMENTATION_MARGIN_DB == 1.7


def test_all_explicit_round3_verify_source_flags_are_live() -> None:
    """The seven hardware/proxy applicability questions remain visibly unresolved."""

    assert len(VERIFY_SOURCE) == 7
    assert all(VERIFY_SOURCE.values())


def test_every_manifest_constant_has_value_and_provenance() -> None:
    """The source receipt is a bijection: every bound §2 name has both its value and provenance."""

    manifest = constant_manifest()
    assert set(manifest["values"]) == set(PROVENANCE)
    assert set(manifest["provenance"]) == set(PROVENANCE)
    assert all(manifest["provenance"].values())
