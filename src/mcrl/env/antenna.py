"""Transmit and receive antenna patterns (SDD §3.4b, §3.7 P-2/P-10, G-7/G-10).

Two patterns, two entirely different failure modes, and both of them silent.

**Transmit — the half-angle convention (P-2).**  ``θ_3dB = 3.32°`` is
registered as the **full** HPBW, while the Bessel pattern's parameter is the
one-sided half-power angle.  Live code passes ``θ_3dB/2``
(``family_b_geometry.py:361-369``, ``family_b_step.py:482-484``) but the
specification only ever used the halving for the cell radius, never for the
gain.  Passing the full HPBW quietly doubles the beamwidth, and until G-10
there was no ``G^T`` anchor test at all.

**Receive — degrees, not radians (G-7).**  The ITU-R S.465-6 envelope is
``32 − 25·log₁₀(θ)`` with θ in **degrees**.  Feeding it radians inflates the
gain by ``25·log₁₀(180/π) ≈ 43.95 dB`` and silently saturates most of the
pattern at ``G_R,max``.  A parity test between two implementations cannot
catch this — both sides would be wrong together — which is why G-7 demands
absolute anchors plus an end-to-end vector proving the geometry layer emits
degrees.

**Receive — the same-satellite override (P-10).**  The envelope argument is
the angle **at the user between two satellites**, not between two beams.
Every beam of one satellite arrives from the same direction, so the terminal
antenna cannot discriminate them: they all get the full boresight gain.
Applying the envelope to the inter-beam angle instead would report a
co-satellite interferer 15-45 dB weaker than it is.
"""

from __future__ import annotations

import math

import numpy as np

from ..errors import MCRLContractError
from ..runtime.bessel import bessel_j

# ---------------------------------------------------------------------------
# Transmit pattern (HOBS eq. (3))
# ---------------------------------------------------------------------------

THETA_3DB_DEG: float = 3.32
"""**P'** — HOBS, registered as the FULL half-power beamwidth."""

G0_LINEAR: float = 2000.0
"""**P'** — 2000 linear, 33.010 dBi.  **Not HOBS Table I's 40 dBi.**

The paper now rejects that value: HOBS Table I's aperture, gain and
beamwidth are mutually inconsistent, and under either dimensionally legal
reading 40 dBi demands an aperture efficiency above 1 (2.53 on the radius
reading, 10.13 on the diameter reading).

Re-derived instead from an aperture consistent with the beamwidth,
``D = 1.0275 λ / θ_3dB = 17.7 λ``, with the Ka-band aperture efficiency
0.639-0.645 back-computed from TR 38.821's rows, giving ``G_0 = 2000``
(ruling C-14).
"""

G0_DBI: float = 10.0 * math.log10(G0_LINEAR)

_BESSEL_MU_COEFFICIENT: float = 2.07123
"""HOBS eq. (3): ``μ = 2.07123·sin θ / sin θ_half``."""


def mu_of(theta_deg: np.ndarray, *, theta_3db_deg: float = THETA_3DB_DEG) -> np.ndarray:
    """Bessel argument for an off-axis angle in **degrees**.

    ``theta_3db_deg`` is the FULL HPBW; it is halved here, once, so no caller
    can forget to (P-2).
    """
    if theta_3db_deg <= 0.0:
        raise ValueError("theta_3db_deg must be positive")
    theta = np.asarray(theta_deg, dtype=np.float64)
    half_power_rad = math.radians(theta_3db_deg / 2.0)
    return _BESSEL_MU_COEFFICIENT * np.sin(np.radians(theta)) / math.sin(
        half_power_rad
    )


def transmit_gain_linear(
    theta_deg: np.ndarray,
    *,
    g0_linear: float = G0_LINEAR,
    theta_3db_deg: float = THETA_3DB_DEG,
) -> np.ndarray:
    """``G_T(θ) = G₀·[J₁(μ)/(2μ) + 36·J₃(μ)/μ³]²``, θ in **degrees**.

    The Bessel calls go through :func:`mcrl.runtime.bessel.bessel_j`, which
    routes ``|μ| > 34`` to Miller recursion (P-1).  ``μ`` reaches 67.3 at the
    horizon under this paper's conventions, so that routing is load-bearing
    for every side-lobe evaluation.
    """
    if g0_linear <= 0.0:
        raise ValueError("g0_linear must be positive")
    theta = np.asarray(theta_deg, dtype=np.float64)
    if not np.all(np.isfinite(theta)):
        raise MCRLContractError("off-axis angles must be finite")

    mu = mu_of(theta, theta_3db_deg=theta_3db_deg)
    gains = np.empty(mu.shape, dtype=np.float64)
    for index in np.ndindex(mu.shape):
        mu_value = float(mu[index])
        if abs(mu_value) < 1e-10:
            gains[index] = float(g0_linear)
            continue
        j1 = bessel_j(1, mu_value)
        j3 = bessel_j(3, mu_value)
        bracket = j1 / (2.0 * mu_value) + 36.0 * j3 / (mu_value**3)
        gains[index] = float(g0_linear) * bracket * bracket
    return gains


def transmit_gain_dbi(
    theta_deg: np.ndarray,
    *,
    g0_linear: float = G0_LINEAR,
    theta_3db_deg: float = THETA_3DB_DEG,
    floor_dbi: float = -100.0,
) -> np.ndarray:
    """:func:`transmit_gain_linear` in dBi, with a reporting floor at nulls."""
    linear = transmit_gain_linear(
        theta_deg, g0_linear=g0_linear, theta_3db_deg=theta_3db_deg
    )
    with np.errstate(divide="ignore"):
        return np.maximum(10.0 * np.log10(np.maximum(linear, 1e-300)), floor_dbi)


# ---------------------------------------------------------------------------
# Receive pattern (ITU-R S.465-6 recommends 2, + Mendonça et al. 2025)
# ---------------------------------------------------------------------------

RX_ENVELOPE_A_DBI: float = 32.0
"""**P'** — ITU-R S.465-6 ``recommends 2``: ``G = A − B·log₁₀(θ_deg)``."""

RX_ENVELOPE_B: float = 25.0
"""**P'** — same."""

RX_GAIN_MAX_DBI: float = 35.0
"""**P'** — Mendonça et al., IEEE OJ-COMS 2025, 0.6 m terminal (C8 closed)."""

RX_GAIN_FLOOR_DBI: float = -10.0
"""**P'** — S.465-6 envelope floor; the 48° continuation joins here."""

RX_ENVELOPE_SATURATION_DEG: float = 10.0 ** (
    (RX_ENVELOPE_A_DBI - RX_GAIN_MAX_DBI) / RX_ENVELOPE_B
)
"""**D** — where the envelope first reaches ``G_R,max``: 0.759°."""

RX_ENVELOPE_FLOOR_DEG: float = 10.0 ** (
    (RX_ENVELOPE_A_DBI - RX_GAIN_FLOOR_DBI) / RX_ENVELOPE_B
)
"""**D** — where the envelope reaches the floor: 48.0°."""

_BORESIGHT_TOLERANCE_DEG: float = 1e-9


def receive_gain_dbi(separation_deg: np.ndarray) -> np.ndarray:
    """Terminal receive gain in dBi for an off-boresight angle in **degrees**.

    ``separation_deg`` is the angle **at the user** between the serving
    satellite and the interferer.  Passing radians here is the G-7 failure
    mode; :func:`assert_degrees_not_radians` exists to make that loud.
    """
    separation = np.asarray(separation_deg, dtype=np.float64)
    if not np.all(np.isfinite(separation)):
        raise MCRLContractError("separations must be finite")
    if np.any(separation < 0.0):
        raise MCRLContractError("separations must be non-negative")

    with np.errstate(divide="ignore"):
        envelope = RX_ENVELOPE_A_DBI - RX_ENVELOPE_B * np.log10(
            np.maximum(separation, 1e-9)
        )
    envelope = np.clip(envelope, RX_GAIN_FLOOR_DBI, RX_GAIN_MAX_DBI)
    return np.where(
        separation <= _BORESIGHT_TOLERANCE_DEG, RX_GAIN_MAX_DBI, envelope
    )


def receive_gain_linear(separation_deg: np.ndarray) -> np.ndarray:
    return 10.0 ** (receive_gain_dbi(separation_deg) / 10.0)


def apply_same_satellite_override(
    receive_linear: np.ndarray,
    satellite_slot_of_beam: np.ndarray,
    serving_slot: np.ndarray,
) -> np.ndarray:
    """P-10 — co-satellite beams get full boresight gain, not the envelope.

    ``receive_linear`` is ``(U, B)``, ``satellite_slot_of_beam`` is ``(B,)``,
    and ``serving_slot`` is ``(U,)``.  Every beam radiated by the user's own
    serving satellite arrives from the same direction as the wanted signal,
    so the terminal antenna gives it ``G_R,max``.

    Skipping this under-states co-satellite interference by 15 dB at one
    cell spacing and by up to ~45 dB at the edge of the pattern.
    """
    gains = np.array(receive_linear, dtype=np.float64, copy=True)
    beams_slot = np.asarray(satellite_slot_of_beam, dtype=np.int64)
    serving = np.asarray(serving_slot, dtype=np.int64)
    if gains.ndim != 2:
        raise MCRLContractError("receive_linear must have shape (U, B)")
    users, beams = gains.shape
    if beams_slot.shape != (beams,):
        raise MCRLContractError("satellite_slot_of_beam must have shape (B,)")
    if serving.shape != (users,):
        raise MCRLContractError("serving_slot must have shape (U,)")

    served = serving >= 0
    same_satellite = np.zeros_like(gains, dtype=bool)
    same_satellite[served] = beams_slot[None, :] == serving[served, None]
    gains[same_satellite] = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
    return gains


def assert_degrees_not_radians(separation_deg: np.ndarray) -> np.ndarray:
    """G-7(b) — reject an angle array that is plainly in radians.

    Any separation the geometry layer produces is bounded by 180°.  A
    radian-valued array of angles that ought to span the sky never exceeds
    π ≈ 3.14, so it looks like a legal sub-degree pattern and saturates
    almost everywhere at ``G_R,max`` — silently, and ~44 dB too high.

    The check is a **distributional** one, not a bound: if nothing in a
    wide-angle set exceeds π, the units are wrong.
    """
    separation = np.asarray(separation_deg, dtype=np.float64)
    if separation.size == 0:
        return separation
    if np.any(separation > 180.0):
        raise MCRLContractError(
            f"separation {float(separation.max()):.3f} exceeds 180°: not an angle"
        )
    return separation
