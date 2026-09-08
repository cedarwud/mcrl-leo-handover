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
    slant_km: np.ndarray,
    elevation_deg: np.ndarray,
    *,
    shadow_fading_db: np.ndarray | float = 0.0,
) -> np.ndarray:
    """Paper eq. (3.10b): ``L = L_f + L_g + L_c + L_s``, all in dB.

    ``L_s`` is keyword-only and defaults to zero because it is a **draw**,
    not a function of the geometry — the caller owns the generator, and a
    default that silently produced its own would make two callers with the
    same seed disagree.  Passing nothing gives the deterministic budget,
    which is what the G-2 ledger and the anchor tests want.
    """
    return (
        free_space_loss_db(slant_km)
        + atmospheric_loss_db(elevation_deg)
        + scintillation_loss_db(elevation_deg)
        + np.asarray(shadow_fading_db, dtype=np.float64)
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


