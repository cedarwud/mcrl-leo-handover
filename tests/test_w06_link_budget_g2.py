"""W-06 / G-2 — the link budget placed against TR 38.821 Table 6.1.3.3-1.

G-2: "鏈路預算落在合理包絡 | 對照 TR 38.821 Table 6.1.3.3-1 的 LEO Ka DL
案例,列出逐項 delta ledger".

Comparator selection follows the rule already pre-registered in the source
project (``01-env-validation-standard-sdd.md`` L2-2): the row minimising
|Δaltitude| then |Δfrequency|, ties broken by source-table order.  Our
measured altitude is ~485 km, so among {LEO-600, LEO-1200, GEO} the
LEO-600 20 GHz DL rows win, and the tie-break takes the first of them —
**SC 6**.

The ledger is not decoration.  Every term is written out, the residual
between "comparator CNR + Σdeltas" and our own computed CNR is asserted to
close, and the reading of the table's columns is itself validated by
reproducing the table's own published CNR from its own inputs.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from mcrl.env.antenna import G0_DBI, RX_GAIN_MAX_DBI
from mcrl.env.link_budget import (
    BEAM_BANDWIDTH_HZ,
    BEAM_POWER_MAX_W,
    BOLTZMANN_DBW_PER_K_PER_HZ,
    SYSTEM_TEMPERATURE_K,
    atmospheric_loss_db,
    carrier_to_noise_db,
    eirp_dbw,
    free_space_loss_db,
    g_over_t_db_per_k,
    noise_power_w,
    noise_psd_dbm_per_hz,
    shannon_rate_bps,
)
from mcrl.errors import MCRLContractError

# TR 38.821 Table 6.1.3.3-1, row "SC 6, DL" — LEO-600, Ka, VSAT.
SC6 = {
    "frequency_ghz": 20.0,
    "eirp_dbm": 60.0,
    "g_over_t_db_per_k": 15.9,
    "bandwidth_mhz": 400.0,
    "free_space_loss_db": 179.1,
    "atmospheric_loss_db": 0.5,
    "shadowing_margin_db": 0.0,
    "scintillation_loss_db": 0.3,
    "additional_losses_db": 0.0,
    "polarisation_loss_db": 0.0,
    "cnr_db": 8.5,
}

COMPARATOR_ELEVATION_DEG = 30.0
"""TR 38.821's LEO link budgets are quoted at 30° elevation."""


def _sc6_other_losses_db() -> float:
    return (
        SC6["atmospheric_loss_db"]
        + SC6["shadowing_margin_db"]
        + SC6["scintillation_loss_db"]
        + SC6["additional_losses_db"]
        + SC6["polarisation_loss_db"]
    )


def test_the_column_reading_reproduces_the_tables_own_CNR():
    """Validate the reading of a mangled markdown table before trusting it."""
    computed = carrier_to_noise_db(
        eirp_dbw=SC6["eirp_dbm"] - 30.0,
        free_space_loss_db=SC6["free_space_loss_db"],
        other_losses_db=_sc6_other_losses_db(),
        g_over_t_db_per_k=SC6["g_over_t_db_per_k"],
        bandwidth_hz=SC6["bandwidth_mhz"] * 1e6,
    )
    assert computed == pytest.approx(SC6["cnr_db"], abs=0.1)


def test_our_fspl_reproduces_the_comparators_free_space_loss():
    """Independent check of the FSPL implementation against 3GPP's number."""
    # Invert their FSL to the slant range it implies, then feed ours.
    frequency_hz = SC6["frequency_ghz"] * 1e9
    slant_m = 10.0 ** (
        (SC6["free_space_loss_db"] - 20.0 * math.log10(frequency_hz) + 147.55)
        / 20.0
    )
    slant_km = slant_m / 1000.0
    # A LEO-600 pass at 30° elevation.
    assert 1000.0 < slant_km < 1150.0
    assert float(free_space_loss_db(np.array(slant_km))) == pytest.approx(
        SC6["free_space_loss_db"], abs=0.05
    )


def _our_budget(slant_km: float) -> dict[str, float]:
    return {
        "eirp_dbw": eirp_dbw(BEAM_POWER_MAX_W, G0_DBI),
        "free_space_loss_db": float(free_space_loss_db(np.array(slant_km))),
        "atmospheric_loss_db": float(
            atmospheric_loss_db(np.array(COMPARATOR_ELEVATION_DEG))
        ),
        "g_over_t_db_per_k": g_over_t_db_per_k(RX_GAIN_MAX_DBI),
        "bandwidth_hz": BEAM_BANDWIDTH_HZ,
    }


def test_G2_delta_ledger_closes_against_SC6():
    """Every difference itemised; the residual must vanish."""
    frequency_hz = SC6["frequency_ghz"] * 1e9
    slant_km = (
        10.0
        ** (
            (SC6["free_space_loss_db"] - 20.0 * math.log10(frequency_hz) + 147.55)
            / 20.0
        )
    ) / 1000.0
    ours = _our_budget(slant_km)

    ledger = {
        # We radiate 1.65 W into a 33.01 dBi beam; SC 6 assumes 60 dBm EIRP.
        "eirp": ours["eirp_dbw"] - (SC6["eirp_dbm"] - 30.0),
        # Same slant and frequency, so this must be zero by construction.
        "free_space_loss": -(
            ours["free_space_loss_db"] - SC6["free_space_loss_db"]
        ),
        # Our slab model at 30° gives 1.0 dB against their 0.5 dB.
        "atmosphere": -(
            ours["atmospheric_loss_db"] - SC6["atmospheric_loss_db"]
        ),
        # We model no scintillation, shadowing, polarisation or extra losses.
        "unmodelled_losses": (
            SC6["scintillation_loss_db"]
            + SC6["shadowing_margin_db"]
            + SC6["additional_losses_db"]
            + SC6["polarisation_loss_db"]
        ),
        # 35 dBi over T_sys = 242.3 K is 11.16 dB/K, not 15.9.
        "g_over_t": ours["g_over_t_db_per_k"] - SC6["g_over_t_db_per_k"],
        # A third of 500 MHz is less noise than their 400 MHz.
        "bandwidth": 10.0
        * math.log10(SC6["bandwidth_mhz"] * 1e6 / ours["bandwidth_hz"]),
    }

    our_cnr = carrier_to_noise_db(
        eirp_dbw=ours["eirp_dbw"],
        free_space_loss_db=ours["free_space_loss_db"],
        other_losses_db=ours["atmospheric_loss_db"],
        g_over_t_db_per_k=ours["g_over_t_db_per_k"],
        bandwidth_hz=ours["bandwidth_hz"],
    )
    # Compare against the comparator's CNR recomputed from its own inputs, so
    # the table's own 0.1 dB rounding does not leak into the residual.
    comparator_cnr = carrier_to_noise_db(
        eirp_dbw=SC6["eirp_dbm"] - 30.0,
        free_space_loss_db=SC6["free_space_loss_db"],
        other_losses_db=_sc6_other_losses_db(),
        g_over_t_db_per_k=SC6["g_over_t_db_per_k"],
        bandwidth_hz=SC6["bandwidth_mhz"] * 1e6,
    )

    residual = our_cnr - (comparator_cnr + sum(ledger.values()))
    assert abs(residual) < 0.01, f"ledger does not close: {residual:.4f} dB\n{ledger}"

    # And the placement is an envelope check, not an exact match: we sit a
    # few dB above SC 6, driven by the narrower per-colour bandwidth and the
    # higher EIRP, partly given back by the lower G/T.
    assert 0.0 < our_cnr - comparator_cnr < 10.0
    assert ledger["eirp"] > 0.0
    assert ledger["g_over_t"] < 0.0
    assert ledger["bandwidth"] > 0.0


def test_our_operating_CNR_is_physically_plausible():
    """Across the real slant range, C/N must stay in a usable band."""
    for slant_km, elevation_deg in ((485.0, 90.0), (748.0, 25.0), (1100.0, 21.8)):
        ours = _our_budget(slant_km)
        cnr = carrier_to_noise_db(
            eirp_dbw=ours["eirp_dbw"],
            free_space_loss_db=float(free_space_loss_db(np.array(slant_km))),
            other_losses_db=float(atmospheric_loss_db(np.array(elevation_deg))),
            g_over_t_db_per_k=ours["g_over_t_db_per_k"],
            bandwidth_hz=ours["bandwidth_hz"],
        )
        assert 0.0 < cnr < 40.0, (slant_km, elevation_deg, cnr)


def test_lower_altitude_raises_CNR_by_the_expected_amount():
    """SDD F3: 780 -> 550 km is 3.03 dB of FSPL.  780 -> 485 km is 4.13 dB."""
    at_780 = float(free_space_loss_db(np.array(780.0)))
    at_550 = float(free_space_loss_db(np.array(550.0)))
    at_485 = float(free_space_loss_db(np.array(485.0)))
    assert at_780 - at_550 == pytest.approx(3.03, abs=0.01)
    assert at_780 - at_485 == pytest.approx(4.13, abs=0.01)


# -- component sanity ------------------------------------------------------


def test_system_temperature_matches_the_parameter_spec():
    assert SYSTEM_TEMPERATURE_K == pytest.approx(242.294, abs=0.001)
    assert g_over_t_db_per_k(RX_GAIN_MAX_DBI) == pytest.approx(11.155, abs=0.01)


def test_noise_psd_sits_just_below_the_290K_reference():
    """Table I quotes −174 dBm/Hz at 290 K; ours is at 242.3 K."""
    assert noise_psd_dbm_per_hz() == pytest.approx(-174.76, abs=0.01)
    reference_290k = 10.0 * math.log10(1.380649e-23 * 290.0) + 30.0
    assert reference_290k == pytest.approx(-173.98, abs=0.01)
    assert noise_psd_dbm_per_hz() < reference_290k


def test_noise_power_matches_kTB():
    assert noise_power_w() == pytest.approx(
        1.380649e-23 * SYSTEM_TEMPERATURE_K * BEAM_BANDWIDTH_HZ
    )
    assert 10.0 * math.log10(noise_power_w()) == pytest.approx(
        BOLTZMANN_DBW_PER_K_PER_HZ
        + 10.0 * math.log10(SYSTEM_TEMPERATURE_K)
        + 10.0 * math.log10(BEAM_BANDWIDTH_HZ)
    )


def test_beam_bandwidth_is_a_third_of_the_system_bandwidth():
    assert BEAM_BANDWIDTH_HZ == pytest.approx(166.667e6, rel=1e-5)


def test_shannon_rate_and_the_QoS_floor():
    """TS 22.261 §6.17.2 sets a 1 Mbit/s floor; find the SINR that meets it."""
    assert float(shannon_rate_bps(np.array(0.0), beam_load=np.array(1.0))) == 0.0
    required_sinr = 2.0 ** (1e6 / BEAM_BANDWIDTH_HZ) - 1.0
    assert float(
        shannon_rate_bps(np.array(required_sinr), beam_load=np.array(1.0))
    ) == pytest.approx(1e6, rel=1e-9)
    assert required_sinr < 0.01, "1 Mbit/s over 166 MHz is a very low bar"


def test_the_rate_is_divided_by_the_beam_load():
    """Eq. (3.14): the beam is time-shared among its U users."""
    sinr = np.array(3.0)
    alone = float(shannon_rate_bps(sinr, beam_load=np.array(1.0)))
    shared = float(shannon_rate_bps(sinr, beam_load=np.array(4.0)))
    assert shared == pytest.approx(alone / 4.0)
    assert alone == pytest.approx(BEAM_BANDWIDTH_HZ * 2.0)


def test_the_load_cannot_be_omitted():
    """It used to default away, returning a rate U times too high in silence."""
    with pytest.raises(TypeError):
        shannon_rate_bps(np.array(1.0))


def test_a_dark_beam_carries_no_rate():
    assert float(shannon_rate_bps(np.array(5.0), beam_load=np.array(0.0))) == 0.0


def test_negative_inputs_are_refused():
    with pytest.raises(MCRLContractError, match="SINR must be non-negative"):
        shannon_rate_bps(np.array(-0.1), beam_load=np.array(1.0))
    with pytest.raises(MCRLContractError, match="load must be non-negative"):
        shannon_rate_bps(np.array(1.0), beam_load=np.array(-1.0))


def test_eirp_is_undefined_for_a_dark_beam():
    with pytest.raises(MCRLContractError, match="zero transmit power"):
        eirp_dbw(0.0, G0_DBI)
