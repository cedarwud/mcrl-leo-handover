"""W-18 / ruling C-8 (revised) — ``L_c`` and ``L_s`` from TR 38.811.

Both were a declared **0.0** for one day.  The revised C-8 models them from
the NTN tables instead, so what is pinned here is the transcription (a
mis-typed table row is the failure mode a formula test cannot catch), the
two exclusions that are the specification's own, and the fact that ``L_s``
is a draw while ``L_c`` is not.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.link_budget import (
    RICIAN_K_FACTOR_DB,
    atmospheric_loss_db,
    link_power_factor,
    rician_fading_gain,
    scintillation_loss_db,
    shadow_fading_db,
    shadow_fading_sigma_db,
    total_path_loss_db,
)
from mcrl.errors import MCRLContractError

# TR 38.811 Table 6.6.6.2.1-1, 20 GHz tropospheric scintillation.
SCINTILLATION = {
    10: 1.08, 20: 0.48, 30: 0.30, 40: 0.22,
    50: 0.17, 60: 0.13, 70: 0.12, 80: 0.12, 90: 0.12,
}
# TR 38.811 Table 6.6.2-3, Ka band, LOS shadow-fading sigma.
SHADOW_SIGMA = {
    10: 1.9, 20: 1.6, 30: 1.9, 40: 2.3,
    50: 2.7, 60: 3.1, 70: 3.0, 80: 3.6, 90: 0.4,
}


@pytest.mark.parametrize("elevation,expected", sorted(SCINTILLATION.items()))
def test_the_scintillation_table_is_transcribed_exactly(elevation, expected):
    assert float(scintillation_loss_db(np.array(float(elevation)))) == pytest.approx(
        expected, abs=1e-12
    )


@pytest.mark.parametrize("elevation,expected", sorted(SHADOW_SIGMA.items()))
def test_the_shadow_sigma_table_is_transcribed_exactly(elevation, expected):
    assert float(shadow_fading_sigma_db(np.array(float(elevation)))) == pytest.approx(
        expected, abs=1e-12
    )


def test_the_90_degree_shadow_sigma_discontinuity_is_preserved():
    """3.6 dB at 80°, 0.4 dB at 90°.  The spec prints it; do not smooth it.

    It is the one sharp edge in this model and it is not ours.  A reader who
    "fixes" it to 3.8 or interpolates it away has changed a published table.
    """
    assert float(shadow_fading_sigma_db(np.array(80.0))) == 3.6
    assert float(shadow_fading_sigma_db(np.array(90.0))) == 0.4
    midpoint = float(shadow_fading_sigma_db(np.array(85.0)))
    assert midpoint == pytest.approx(2.0, abs=1e-9), "linear across the step"


def test_scintillation_is_monotonic_and_deterministic():
    """No RNG argument at all: ``L_c`` is a table lookup, not a draw."""
    elevations = np.linspace(10.0, 90.0, 200)
    values = scintillation_loss_db(elevations)
    assert np.all(np.diff(values) <= 1e-12), "loss must fall with elevation"
    assert np.array_equal(values, scintillation_loss_db(elevations))


def test_below_the_table_the_value_is_held_not_extrapolated():
    """The curve steepens below 10°; a linear continuation would understate it."""
    assert float(scintillation_loss_db(np.array(5.0))) == 1.08
    assert float(scintillation_loss_db(np.array(0.0))) == 1.08
    assert float(shadow_fading_sigma_db(np.array(0.0))) == 1.9


def test_shadow_fading_is_a_zero_mean_dB_gaussian():
    rng = np.random.default_rng(0)
    draws = np.array(
        [float(shadow_fading_db(rng, np.array(60.0))) for _ in range(20_000)]
    )
    assert draws.mean() == pytest.approx(0.0, abs=0.05)
    assert draws.std() == pytest.approx(SHADOW_SIGMA[60], rel=0.03)


def test_zero_mean_in_dB_is_not_zero_mean_in_linear_power():
    """Stated in the docstring, checked here so nobody rediscovers it.

    A dB-Gaussian is lognormal in power, so the mean linear gain exceeds 1.
    Normalising it away would silently redefine what "0 dB shadowing" means
    against every published NTN budget, so it is disclosed instead.
    """
    rng = np.random.default_rng(1)
    sigma = SHADOW_SIGMA[60]
    draws = np.array(
        [float(shadow_fading_db(rng, np.array(60.0))) for _ in range(50_000)]
    )
    mean_linear = np.mean(10.0 ** (-draws / 10.0))
    predicted = np.exp((sigma * np.log(10.0) / 10.0) ** 2 / 2.0)
    assert mean_linear == pytest.approx(predicted, rel=0.02)
    assert 10.0 * np.log10(predicted) == pytest.approx(1.0, abs=0.2)


def test_the_two_random_terms_are_the_only_ones_and_share_a_generator():
    """C-8: ``L_s`` and ``K_R`` are the model's whole stochastic surface."""
    one = np.random.default_rng(42)
    two = np.random.default_rng(42)
    assert float(shadow_fading_db(one, np.array(45.0))) == float(
        shadow_fading_db(two, np.array(45.0))
    )
    assert float(rician_fading_gain(one, (1,), k_factor_db=RICIAN_K_FACTOR_DB)[0]) == (
        float(rician_fading_gain(two, (1,), k_factor_db=RICIAN_K_FACTOR_DB)[0])
    )


def test_the_four_term_path_loss_adds_up():
    """(3.10b) ``L = L_f + L_g + L_c + L_s``, with L_s supplied not drawn."""
    slant, elevation = np.array(700.0), np.array(30.0)
    deterministic = float(total_path_loss_db(slant, elevation))
    with_shadow = float(
        total_path_loss_db(slant, elevation, shadow_fading_db=2.5)
    )
    assert with_shadow - deterministic == pytest.approx(2.5)
    # L_c is now in there and is not zero.
    assert deterministic > float(
        20.0 * np.log10(700e3 * 4 * np.pi / (299792458.0 / 20e9))
    ) + float(atmospheric_loss_db(elevation))


def test_shadow_fading_defaults_to_zero_rather_than_drawing_its_own():
    """A default draw would make two callers with one seed disagree."""
    slant, elevation = np.array(700.0), np.array(30.0)
    assert float(total_path_loss_db(slant, elevation)) == float(
        total_path_loss_db(slant, elevation, shadow_fading_db=0.0)
    )
    assert float(link_power_factor(slant, elevation, np.array(1.0))) == float(
        link_power_factor(slant, elevation, np.array(1.0), shadow_fading_db=0.0)
    )


def test_an_impossible_elevation_is_refused():
    with pytest.raises(MCRLContractError, match="elevation"):
        scintillation_loss_db(np.array(120.0))
    with pytest.raises(MCRLContractError, match="elevation"):
        shadow_fading_sigma_db(np.array(-120.0))
