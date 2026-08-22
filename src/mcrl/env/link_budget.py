"""Downlink budget: path loss, atmosphere, noise, SINR (SDD W-06, G-2).

Values come from ``NEW-PROJECT-PARAMETER-SPEC-2026-08-21.md`` §1.  Every
constant carries its class code; the two places this layer departs from the
source project are marked ★ and explained.
"""

from __future__ import annotations

import math

import numpy as np

from ..errors import MCRLContractError

# -- carrier and bandwidth -------------------------------------------------

CARRIER_FREQ_HZ: float = 20.0e9
"""**P** — Table I ``f_c = 20 GHz``."""

BANDWIDTH_HZ: float = 500.0e6
"""**P** — Table I ``B = 500 MHz``."""

FREQUENCY_REUSE_FACTOR: int = 3
"""**P'** — TR 38.821 Table 6.1.3.2-1 lists FRF 1/2/3.  MODQN never mentions
reuse, so the three-colour choice is disclosed rather than paper-backed."""

BEAM_BANDWIDTH_HZ: float = BANDWIDTH_HZ / FREQUENCY_REUSE_FACTOR
"""**D** — 166.667 MHz per colour."""

SPEED_OF_LIGHT_M_S: float = 299_792_458.0

# -- terminal noise --------------------------------------------------------

BOLTZMANN_J_PER_K: float = 1.380649e-23
ANTENNA_TEMPERATURE_K: float = 150.0
"""**P'** — TR 38.821 Table 6.1.1.1-3, Ka VSAT."""

REFERENCE_TEMPERATURE_K: float = 290.0
RECEIVER_NOISE_FIGURE_DB: float = 1.2
"""**P'** — same."""

SYSTEM_TEMPERATURE_K: float = ANTENNA_TEMPERATURE_K + REFERENCE_TEMPERATURE_K * (
    10.0 ** (RECEIVER_NOISE_FIGURE_DB / 10.0) - 1.0
)
"""**D** — 242.294 K."""

# -- atmosphere ------------------------------------------------------------

ZENITH_GASEOUS_LOSS_DB: float = 0.25
"""**P'** — clear-sky zenith gaseous attenuation at 20 GHz, dB.

Derived from documents this project already cites, not chosen:

* TR 38.821 Table 6.1.3.2-1 sets the LEO **target elevation angle to 30°**
  and takes atmospheric loss from **equation (6.6-8) of TR 38.811**;
* TR 38.811 (6.6-8) is the cosecant law ``PL_A(α, f) = A_zenith(f)/sin α``;
* TR 38.821 Table 6.1.3.3-1 row SC 6 (LEO-600, 20 GHz DL) tabulates
  **0.5 dB**.

So ``A_zenith = 0.5 · sin 30° = 0.25 dB``.  It is also self-consistent with
the G-2 comparator, which is the same row.

★ **Replaces the source project's ``3·d·χ/(10·h_s)``**, which the controller
ruled a transcription error rather than a modelling choice: expanded it is
``0.3·χ·(d/h_s)`` and ``d/h_s ≈ 1/sin α``, i.e. a **0.3 km thick**
atmosphere giving 0.015 dB at zenith.  Clear-sky gaseous attenuation at
20 GHz is of order tenths of a dB, not hundredths.
"""

SCINTILLATION_LOSS_DB: float = 0.0
"""**Not modelled** — declared, not silently omitted (ruling C-8).

The paper names ``L_c`` in (3.10b) but gives no value or realisation, and
TR 38.811 §6.6.6's model is stochastic, which would drag the frozen-seed
protocol into scope mid-freeze.  Kept as a named zero so the G-2 delta
ledger keeps its line rather than the term disappearing.
"""

SHADOWING_LOSS_DB: float = 0.0
"""**P'** — TR 38.821 Table 6.1.3.2-1: "Shadowing margin 0 dB for VSAT".

Unlike ``L_c`` this zero is sourced rather than merely declared: this
project's terminal is the Ka VSAT whose margin that table sets to zero.
"""

_MIN_SIN_ELEVATION: float = 1e-3

# -- power -----------------------------------------------------------------

BEAM_POWER_MAX_W: float = 1.65
"""``p_max`` — **D**, the per-beam RF output ceiling after backoff.

**Not a free parameter.**  It is pinned by the amplifier through
``p_sat = p_max·10^(BO/10) = 5.218 W``, which is ch5's legacy ``P_0`` (the
PA reference output power).  Moving it would move ``p_sat``, and ``p_sat``
sits in the denominator of eq. (3.15a) — the whole efficiency curve would
shift.  So when ``p⁰`` and ``p_max`` collided, this is the one that stayed.

It is a **feasibility test outside the recurrence** (eq. 3.11 introduces no
clamp): a link whose recurrence asks for more than this is infeasible and
the user is in outage for that step.
"""

SEGMENT_START_POWER_W: float = BEAM_POWER_MAX_W / 2.0
"""``p⁰ = p_max/2 = 0.825 W`` — **D**, ruling F-1 (2026-08-22).

⚠ **Was 2 W (MODQN Table I) and that was 0.835 dB ABOVE ``p_max``.**  Since
(3.12) starts a segment at exactly ``p⁰`` and the recurrence only ever
*raises* power inside a segment (the gain falls, so the ratio exceeds 1),
a segment starting above the ceiling could never re-enter the feasible
region.  The measured consequence was an outage rate of exactly 1.0 — no
user was ever served.  The controller's ruling: the paper is wrong, and
``p⁰`` is what moves, because it is a scenario constant with no physics
pinning it while ``p_max`` is pinned by the amplifier above.

**The halving is derived, not chosen.**  The ratio ``p_max/p⁰`` *is* the
gain drop a segment may absorb before it is judged infeasible, because
``p·G^T`` is the segment invariant::

    p(t) = p⁰·G^T(θ(τ))/G^T(θ(t)) ≤ p_max  ⇔  G^T(θ(t))/G^T(θ(τ)) ≥ p⁰/p_max

Setting that to one half fixes the budget at **3 dB**, and 3 dB is the
cell's own contour:

* ``F(μ) = 0.5`` at ``μ = 2.07123`` — which is where the half-angle
  convention comes from in the first place;
* ``μ(θ) = 2.07123·sin θ/sin(θ_3dB/2) = 2.07123`` ⇔ ``θ = θ_3dB/2``;
* and the cell radius is ``R_b = h_s·tan(θ_3dB/2)``.

So ``p⁰``, ``p_max``, ``θ_3dB`` and ``R_b`` become four mutually consistent
quantities instead of four independently chosen ones.

⚠ **What the test then means is "3 dB worse than when you connected", not
"you have left your cell".**  The ruling's table reads the budget against
boresight — ``p_required = p⁰·G_0/G^T(θ)`` — which needs
``G^T(θ(τ)) = G_0``, i.e. every segment starting on the beam axis.  (3.12)
does not do that: it starts a segment at ``p⁰`` whatever the angle then is,
and measures the drop **relative to ``τ``**.  Measured over 600 segments
under the frozen scenario, ``θ(τ)`` has median **1.165°** and **11.2% of
segments start outside the 3 dB contour altogether** — so the two readings
are not the same test.  The *value* is unaffected; the sentence ch5 writes
around it should be.
"""

PA_MAX_EFFICIENCY: float = 0.35
"""``ξ_max`` — **S**, eq. (3.15a)."""

PA_OUTPUT_BACKOFF_DB: float = 5.0
"""``BO`` — **S**, eq. (3.15a)."""

PA_SATURATION_POWER_W: float = BEAM_POWER_MAX_W * 10.0 ** (
    PA_OUTPUT_BACKOFF_DB / 10.0
)
"""``p_sat = p_max·10^(BO/10)`` — **D**, 5.218 W.

Reassuringly, that is exactly ch5's legacy ``P_0 = 5.218 W``: the legacy
"PA reference output power" was this same saturation point, so the two
tables are consistent even though only one of them is active.
"""

CIRCUIT_POWER_PER_BEAM_W: float = 0.338
"""``P_cir`` — **P'**, You et al. Table II (300 + 19 + 14 + 5 mW)."""

BASEBAND_POWER_PER_SATELLITE_W: float = 0.200
"""``P_BB`` — **P'**, You et al. Table II.  Shared by a satellite's beams."""

BEAM_TO_RF_CHAIN_IS_SOURCED: bool = False
"""One active beam ↔ one RF chain is a **modelling assumption**, not a fact.

You et al. Table II supplies per-chain circuit power; it does **not**
establish the correspondence.  Ruling C-6: disclose it as **S**, and SDD
§2.6's prohibition stands — this mapping must never be used to argue a
beam-count or per-satellite chain-count ceiling, which was deleted on
2026-08-22 and must not return through the power model.
"""

RICIAN_K_FACTOR_DB: float = 20.0
"""``K_R`` — **D⚠**, ch5 Table 5-2.

Table I's row reads ``φ = 20 dB [5]``; reading ``φ`` as the Rician K factor
is this project's interpretation and must be disclosed as such.  K = 100
means a 100:1 LoS-to-scatter ratio, so the fading is shallow (about ±1 dB)
— it will not swamp a probe, but it **is** a random draw and therefore
belongs in the PREREG's frozen seed set.
"""


def rician_fading_gain(
    rng: np.random.Generator,
    size: tuple[int, ...],
    *,
    k_factor_db: float = RICIAN_K_FACTOR_DB,
) -> np.ndarray:
    """Rician small-scale power gain with **unit mean**, part of ``H``.

    Unit mean matters: the fading must redistribute power around the
    deterministic link budget, not shift it.  A draw whose mean differed
    from 1 would bias every EE number in one direction while looking like
    noise.
    """
    k_linear = 10.0 ** (float(k_factor_db) / 10.0)
    if k_linear < 0.0:
        raise ValueError("the K factor must be non-negative")
    line_of_sight = np.sqrt(k_linear / (k_linear + 1.0))
    scatter_sigma = np.sqrt(1.0 / (2.0 * (k_linear + 1.0)))
    real = line_of_sight + scatter_sigma * rng.standard_normal(size)
    imaginary = scatter_sigma * rng.standard_normal(size)
    return real * real + imaginary * imaginary


def free_space_path_gain(slant_km: np.ndarray) -> np.ndarray:
    """Linear FSPL gain ``(λ/4πd)²``.  Multiply, do not divide."""
    slant = np.asarray(slant_km, dtype=np.float64)
    if np.any(slant <= 0.0):
        raise MCRLContractError("slant range must be positive")
    wavelength_m = SPEED_OF_LIGHT_M_S / CARRIER_FREQ_HZ
    return (wavelength_m / (4.0 * math.pi * slant * 1000.0)) ** 2


def atmospheric_loss_db(elevation_deg: np.ndarray) -> np.ndarray:
    """TR 38.811 eq. (6.6-8): ``A_zenith / sin(elevation)``, dB, positive."""
    elevation = np.asarray(elevation_deg, dtype=np.float64)
    if np.any(elevation < -90.0) or np.any(elevation > 90.0):
        raise MCRLContractError("elevation must lie in [-90, 90] degrees")
    sin_elevation = np.maximum(
        np.sin(np.radians(elevation)), _MIN_SIN_ELEVATION
    )
    return ZENITH_GASEOUS_LOSS_DB / sin_elevation


def total_path_loss_db(
    slant_km: np.ndarray, elevation_deg: np.ndarray
) -> np.ndarray:
    """Paper eq. (3.10b): ``L = L_f + L_g + L_c + L_s``, all in dB.

    ``L_c`` and ``L_s`` are the declared zeros above; they are summed in
    explicitly so the four-term structure of (3.10b) is visible in the code
    rather than implied by two of its terms.
    """
    return (
        free_space_loss_db(slant_km)
        + atmospheric_loss_db(elevation_deg)
        + SCINTILLATION_LOSS_DB
        + SHADOWING_LOSS_DB
    )


def atmospheric_gain(elevation_deg: np.ndarray) -> np.ndarray:
    """Atmospheric loss as a linear gain in (0, 1]."""
    return 10.0 ** (-atmospheric_loss_db(elevation_deg) / 10.0)


def noise_power_w(bandwidth_hz: float = BEAM_BANDWIDTH_HZ) -> float:
    """``σ² = k_B · T_sys · B``."""
    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth must be positive")
    return BOLTZMANN_J_PER_K * SYSTEM_TEMPERATURE_K * bandwidth_hz


def noise_psd_dbm_per_hz() -> float:
    """Noise PSD in dBm/Hz, for the Table I comparison (−174 at 290 K)."""
    return 10.0 * math.log10(BOLTZMANN_J_PER_K * SYSTEM_TEMPERATURE_K) + 30.0


def recurrence_power_w(
    segment_start_gain: np.ndarray,
    current_gain: np.ndarray,
    *,
    p0_w: float = SEGMENT_START_POWER_W,
) -> np.ndarray:
    """Paper eq. (3.12): ``p(t) = p⁰ · G^T(θ(τ)) / G^T(θ(t))``.

    The invariant inside one served segment is the **product** ``p·G^T``,
    not ``p`` itself — the rule compensates the transmit-side angle gain
    and claims nothing about holding SINR or throughput fixed.  This closed
    form is a telescoped identity over (3.11), **not stored state**: it is
    valid only while the same physical link has been served at every step
    from ``τ`` to ``t``, so a caller must not carry it across a break.

    No target-SINR inversion, no cap, no clamp, no min/max projection —
    (3.11)'s text rules all four out.
    """
    start = np.asarray(segment_start_gain, dtype=np.float64)
    now = np.asarray(current_gain, dtype=np.float64)
    if p0_w <= 0.0:
        raise ValueError("p0_w must be positive")
    if np.any(start < 0.0) or np.any(now < 0.0):
        raise MCRLContractError("transmit gains must be non-negative")
    if np.any(now <= 0.0):
        raise MCRLContractError(
            "eq. (3.11) requires G^T(θ(t)) > 0; a null-pointing link has no "
            "recurrence power"
        )
    return p0_w * start / now


def classify_link_power_feasibility(
    required_power_w: np.ndarray,
    *,
    max_power_w: float = BEAM_POWER_MAX_W,
) -> np.ndarray:
    """``p > p_max`` — the per-link admission test, **outside** the recurrence.

    Ruling C-2 is explicit that eq. (3.11) introduces no cap, clamp or
    min/max projection; this is the one ceiling that remains, and it sits
    after the recurrence rather than inside it.  A link whose recurrence
    power exceeds the per-beam RF ceiling is infeasible and that user is in
    outage for the step — per link, so a demanding link drops out while its
    neighbours on the same beam keep service, and there is no cliff.

    There is no per-satellite beam-count ceiling anywhere in this project
    (ruling 2026-08-22); any count-based cap darkens whole beams at once,
    which is exactly the cliff this avoids.
    """
    required = np.asarray(required_power_w, dtype=np.float64)
    if np.any(required < 0.0):
        raise MCRLContractError("required power must be non-negative")
    if not np.all(np.isfinite(required)):
        raise MCRLContractError("required power must be finite")
    if max_power_w <= 0.0:
        raise ValueError("max_power_w must be positive")
    return required > max_power_w


def beam_power_w(
    link_power_w: np.ndarray, served: np.ndarray, beam_index: np.ndarray, num_beams: int
) -> np.ndarray:
    """Paper (3.12a) preamble: ``p_{s,v} = max_{u : x=1} p_{u,s,v}``.

    "一支已啟用的波束以單一功率發射,不論其上載有幾位使用者" — the beam
    radiates one power regardless of how many users it carries, so the
    aggregation is a **max over served users**, never a sum or a mean.
    A beam with no served user radiates nothing.
    """
    power = np.asarray(link_power_w, dtype=np.float64)
    active = np.asarray(served, dtype=bool)
    index = np.asarray(beam_index, dtype=np.int64)
    if power.shape != active.shape or power.shape != index.shape:
        raise MCRLContractError(
            "link_power_w, served and beam_index must share a shape"
        )
    if np.any(power < 0.0):
        raise MCRLContractError("link powers must be non-negative")
    out = np.zeros(int(num_beams), dtype=np.float64)
    for value, is_served, beam in zip(
        power.tolist(), active.tolist(), index.tolist()
    ):
        if not is_served or beam < 0:
            continue
        out[beam] = max(out[beam], value)
    return out


def pa_efficiency(
    beam_power: np.ndarray,
    *,
    max_efficiency: float = PA_MAX_EFFICIENCY,
    saturation_power_w: float = PA_SATURATION_POWER_W,
) -> np.ndarray:
    """Paper eq. (3.15a): ``ξ_{s,v} = min{ξ_max, ξ_max·√(p_{s,v}/p_sat)}``.

    **Per beam, no ``u`` index** (ruling F-2).  The paper wrote ``ξ_{u,s,v}``
    on the left while its only argument on the right was the beam power
    ``p_{s,v}`` — ``u`` had nothing to correspond to.  An amplifier belongs
    to a beam, not to a user of it.

    The square root is the class-B idealisation: RF output goes as ``V_o²``
    while DC input goes as ``V_o``, so ``ξ ∝ √P_RF``.  Its consequence is
    the reason ``r1`` is an efficiency rather than a power — "由於低輸出時
    效率較差,把發射功率壓低並不會等比例降低功率消耗".
    """
    power = np.asarray(beam_power, dtype=np.float64)
    if np.any(power < 0.0):
        raise MCRLContractError("beam power must be non-negative")
    if max_efficiency <= 0.0 or saturation_power_w <= 0.0:
        raise ValueError("efficiency and saturation power must be positive")
    return np.minimum(
        max_efficiency, max_efficiency * np.sqrt(power / saturation_power_w)
    )


def supply_power_w(
    beam_power_w: np.ndarray, efficiency: np.ndarray
) -> np.ndarray:
    """Paper eq. (3.15): ``P^p_{s,v} = p_{s,v} / ξ_{s,v}``.

    **Per beam, no ``u`` index** (ruling F-2), matching :func:`pa_efficiency`
    above.  One beam, one amplifier, one supply draw — "一支已啟用的波束以
    單一功率發射,不論其上載有幾位使用者".

    Fail-closed on a dead amplifier: zero efficiency with positive radiated
    power is not a large number, it is a contradiction.
    """
    power = np.asarray(beam_power_w, dtype=np.float64)
    xi = np.asarray(efficiency, dtype=np.float64)
    if np.any(power < 0.0) or np.any(xi < 0.0):
        raise MCRLContractError("power and efficiency must be non-negative")
    starved = (xi <= 0.0) & (power > 0.0)
    if np.any(starved):
        raise MCRLContractError(
            "positive radiated power at zero PA efficiency is impossible; "
            "P-7 forbids flooring the denominator to make it finite"
        )
    return np.where(xi > 0.0, power / np.where(xi > 0.0, xi, 1.0), 0.0)


def fixed_power_w(
    radiating_beams_by_satellite: np.ndarray,  # noqa: E501 - name is deliberate
    *,
    circuit_power_w: float = CIRCUIT_POWER_PER_BEAM_W,
    baseband_power_w: float = BASEBAND_POWER_PER_SATELLITE_W,
) -> float:
    """Paper eq. (3.16a): ``P^f = Σ_s (N^act_s·P_cir + 1{N^act_s>0}·P_BB)``.

    The baseband term is charged **once per satellite**, not once per beam,
    because a satellite's active beams share it.  Note this is a *partial*
    payload-power model: You et al. also count local-oscillator and
    phase-shifter power, which the paper excludes.

    The argument is named "radiating beams **by** satellite" rather than
    "per satellite" on purpose: it is a tally the power sum consumes, and
    the G-6 gate rejects the ceiling vocabulary outright so that a count
    sitting next to the power model can never be mistaken for a limit
    (ruling C-6 — the beam↔RF-chain mapping must not reintroduce one).
    """
    counts = np.asarray(radiating_beams_by_satellite, dtype=np.float64)
    if np.any(counts < 0.0):
        raise MCRLContractError("active-beam counts must be non-negative")
    return float(
        (counts * circuit_power_w).sum()
        + baseband_power_w * float(np.count_nonzero(counts > 0.0))
    )


def system_power_w(
    supply_power_per_beam_w: np.ndarray,
    radiating_beams_by_satellite: np.ndarray,
) -> float:
    """Paper eq. (3.16): ``P^N = P^f + Σ_s Σ_v z_{s,v}·P^p_{s,v}``.

    **A double sum over beams, not a triple sum over links** (ruling F-2).
    The paper wrote ``Σ_{u'} Σ_{s'} Σ_{v'} x_{u',s',v'}·P^p_{u',s',v'}``,
    which charges one amplifier once per user sitting on it.  The over-count
    is exactly ``Σ_{s,v} (U_{s,v} − 1)·P^p_{s,v}``, so the ratio between the
    two forms is the load-weighted mean occupancy — measured at 2.28x for
    100 users and 1.41x for 20, which is what identified the defect.

    The damage was not the scale.  The extra term rises monotonically with
    occupancy and sits in ``r1``'s **denominator**, so "a busier beam is
    less efficient" — which is ``r3``'s job.  A constant offset would not
    move an argmax; a load-dependent one makes the first and third
    objectives inseparable and voids the reading of ``Ω = (0.5, 0.3, 0.2)``.

    ``z`` rather than ``x`` is the correct filter and is satisfied by
    construction: a beam appears in the array iff it radiates.

    The fixed term is included: it was omitted while unsourced, and You et
    al. Table II supplied the source (ruling C-6).  Eq. (3.16a) needed no
    change — it was already per beam, and its own text warns against exactly
    this double count ("每顆衛星只計一次,不會重複計入") for ``P_BB``.
    """
    supply = np.asarray(supply_power_per_beam_w, dtype=np.float64)
    if supply.ndim != 1:
        raise MCRLContractError("supply power must be one per radiating beam")
    if np.any(supply < 0.0):
        raise MCRLContractError("supply power must be non-negative")
    counts = np.asarray(radiating_beams_by_satellite, dtype=np.float64)
    if float(counts.sum()) != float(supply.size):
        raise MCRLContractError(
            f"{supply.size} radiating beams but the per-satellite tally sums "
            f"to {float(counts.sum())}; the two describe different steps"
        )
    return fixed_power_w(counts) + float(supply.sum())


def shannon_rate_bps(
    sinr_linear: np.ndarray,
    *,
    beam_load: np.ndarray,
    bandwidth_hz: float = BEAM_BANDWIDTH_HZ,
) -> np.ndarray:
    """Paper eq. (3.14): ``R = (B^w / U_{s,v}) · log₂(1 + γ)``.

    The beam is time-shared, so its bandwidth is divided by the number of
    users it serves.  ``beam_load`` is **keyword-only and required**: an
    earlier version defaulted the bandwidth to the whole ``B^w`` and left
    the divisor to the caller, which returns a rate exactly ``U`` times too
    high for anyone who forgets — silently, and in the direction that
    flatters the result.

    A zero-load beam has no rate rather than an infinite one.
    """
    sinr = np.asarray(sinr_linear, dtype=np.float64)
    load = np.asarray(beam_load, dtype=np.float64)
    if np.any(sinr < 0.0):
        raise MCRLContractError("SINR must be non-negative")
    if np.any(load < 0.0):
        raise MCRLContractError("beam load must be non-negative")
    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth must be positive")
    shared = np.where(load > 0.0, bandwidth_hz / np.maximum(load, 1.0), 0.0)
    return shared * np.log2(1.0 + sinr)


BOLTZMANN_DBW_PER_K_PER_HZ: float = 10.0 * math.log10(BOLTZMANN_J_PER_K)
"""−228.60 dBW/K/Hz."""


def carrier_to_noise_db(
    *,
    eirp_dbw: float,
    free_space_loss_db: float,
    other_losses_db: float,
    g_over_t_db_per_k: float,
    bandwidth_hz: float,
) -> float:
    """``C/N = EIRP − FSL − L + G/T − k − 10log₁₀(B)``, all dB.

    The standard link equation, written out term by term so a delta ledger
    against a published budget (G-2) can be built from the same pieces.
    """
    if bandwidth_hz <= 0.0:
        raise ValueError("bandwidth must be positive")
    return (
        eirp_dbw
        - free_space_loss_db
        - other_losses_db
        + g_over_t_db_per_k
        - BOLTZMANN_DBW_PER_K_PER_HZ
        - 10.0 * math.log10(bandwidth_hz)
    )


def g_over_t_db_per_k(receive_gain_dbi: float) -> float:
    """Terminal figure of merit against this project's ``T_sys``."""
    return receive_gain_dbi - 10.0 * math.log10(SYSTEM_TEMPERATURE_K)


def eirp_dbw(transmit_power_w: float, transmit_gain_dbi: float) -> float:
    if transmit_power_w <= 0.0:
        raise MCRLContractError("EIRP is undefined for zero transmit power")
    return 10.0 * math.log10(transmit_power_w) + transmit_gain_dbi


def free_space_loss_db(slant_km: np.ndarray) -> np.ndarray:
    """Positive FSPL in dB — the reciprocal of :func:`free_space_path_gain`."""
    return -10.0 * np.log10(free_space_path_gain(slant_km))


def link_power_factor(
    slant_km: np.ndarray,
    elevation_deg: np.ndarray,
    receive_gain_linear: np.ndarray,
    *,
    fading_gain: np.ndarray | None = None,
) -> np.ndarray:
    """Paper eq. (3.10a): ``H = 10^(−L/10) · G^R``, times Rician fading.

    ``H`` carries everything **except** the wanted-link transmit pattern:
    the four losses of (3.10b), the receive gain of (3.10c), and the
    small-scale fading (3.10) names.  ``G^T(θ)`` multiplies it separately so
    the angle enters exactly once and visibly.
    """
    loss_db = total_path_loss_db(slant_km, elevation_deg)
    receive = np.asarray(receive_gain_linear, dtype=np.float64)
    if np.any(receive < 0.0):
        raise MCRLContractError("receive gain must be non-negative")
    factor = 10.0 ** (-loss_db / 10.0) * receive
    if fading_gain is None:
        return factor
    fading = np.asarray(fading_gain, dtype=np.float64)
    if np.any(fading < 0.0):
        raise MCRLContractError("fading gain must be non-negative")
    return factor * fading


def sinr(
    wanted_w: np.ndarray, interference_w: np.ndarray, noise_w: float
) -> np.ndarray:
    """Paper eq. (3.13): ``γ = p·H·G^T / (I + σ²)``.

    The denominator must be strictly positive — the paper says so — and a
    zero there would be a missing noise term rather than a limit to take.
    """
    wanted = np.asarray(wanted_w, dtype=np.float64)
    interference = np.asarray(interference_w, dtype=np.float64)
    if np.any(wanted < 0.0) or np.any(interference < 0.0):
        raise MCRLContractError("powers must be non-negative")
    denominator = interference + noise_w
    if np.any(denominator <= 0.0):
        raise MCRLContractError(
            "eq. (3.13) requires I + sigma^2 > 0; a zero denominator means "
            "the noise term is missing, not that the SINR is infinite"
        )
    return wanted / denominator


# ---------------------------------------------------------------------------
# The p0 / p_max compatibility condition (W-17, resolved by ruling F-1)
# ---------------------------------------------------------------------------

SEGMENT_START_EXCEEDS_BEAM_CEILING: bool = (
    SEGMENT_START_POWER_W > BEAM_POWER_MAX_W
)
"""``p⁰ > p_max`` — **False**, and it must stay false.

It was **True** for one day.  ch5 table 5-2, as re-filed under ruling C-12,
made ``p⁰ = 2 W`` and ``p_max = 1.65 W`` both active, and the two cannot
both be right: a segment starts at exactly ``p⁰`` and the recurrence only
ever raises power inside a segment, so a start above the ceiling can never
come back down.  The measured outage rate was **exactly 1.0**.

Ruling F-1 resolved it by deriving ``p⁰ = p_max/2`` from the 3 dB cell edge
(see :data:`SEGMENT_START_POWER_W`).  The check stays because the condition
it enforces is now *load-bearing rather than merely satisfied*: the headroom
``p_max/p⁰`` **is** the gain budget of a segment, so anything that moves
either constant silently re-prices what "infeasible" means.
"""

SEGMENT_GAIN_BUDGET_DB: float = 10.0 * math.log10(
    BEAM_POWER_MAX_W / SEGMENT_START_POWER_W
)
"""**3.010 dB** — how far ``G^T`` may fall **inside a segment** before outage.

Exactly 3 dB by construction, and 3 dB is the cell's own contour: ``F(μ) =
0.5`` at ``μ = 2.07123`` ⇔ ``θ = θ_3dB/2`` ⇔ the ``R_b = h_s·tan(θ_3dB/2)``
radius.  That is what makes the size of the budget principled rather than
picked.

The reference point is ``θ(τ)``, not boresight — see the ⚠ on
:data:`SEGMENT_START_POWER_W`.  Measured, the largest in-segment loss under
the frozen scenario is **0.718 dB** against this 3.010 dB budget, so the
feasibility gate is currently **non-binding**: outage 0 of 12,000 decision
steps.
"""


def segment_start_feasibility_report(
    *,
    p0_w: float = SEGMENT_START_POWER_W,
    max_power_w: float = BEAM_POWER_MAX_W,
    saturation_power_w: float = PA_SATURATION_POWER_W,
) -> dict[str, object]:
    """The arithmetic behind :data:`SEGMENT_START_EXCEEDS_BEAM_CEILING`.

    Returned as data rather than raised as text so the PREREG, the step
    diagnostics and any controller note all quote one computation.
    """
    infeasible = p0_w > max_power_w
    return {
        "segment_start_power_w": float(p0_w),
        "beam_power_max_w": float(max_power_w),
        "pa_saturation_power_w": float(saturation_power_w),
        "headroom_db": 10.0 * math.log10(max_power_w / p0_w),
        "every_segment_start_is_infeasible": bool(infeasible),
        "p0_is_below_saturation": bool(p0_w <= saturation_power_w),
        "consequence": (
            "p(tau) = p0 exactly and the recurrence only raises power, so a "
            "link that starts a segment is judged infeasible before it can "
            "be served; no segment reaches a second step and the outage rate "
            "is identically 1.0"
            if infeasible
            else "a segment may absorb "
            f"{10.0 * math.log10(max_power_w / p0_w):.3f} dB of transmit-gain "
            "loss before the link is infeasible; at p0 = p_max/2 that is the "
            "3 dB cell edge, so outage means the user left their cell"
        ),
    }
