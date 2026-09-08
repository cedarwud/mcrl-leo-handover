"""Detached B2 rate-target, summed-power physics override.

The override is intentionally not installed into :mod:`mcrl.env.step`.  It
scores a frozen predecision action vector and leaves the original environment
responsible for continuation.  Passing ``enabled=False`` delegates directly
to the production evaluator, which is the byte-identical control seam.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import math
from types import SimpleNamespace
from typing import Any, Callable

import numpy as np

from mcrl.env.action_contract import (
    NO_OP_ACTION,
    assert_selected_actions_valid,
    decode_action,
)
from mcrl.env.antenna import RX_GAIN_MAX_DBI
from mcrl.env.interference import (
    InterferenceBreakdown,
    beam_field_at_users,
    boresight_separation_deg,
    build_radiating_beams,
    received_power_terms,
)
from mcrl.env.link_budget import (
    BEAM_BANDWIDTH_HZ,
    BEAM_POWER_MAX_W,
    BASEBAND_POWER_PER_SATELLITE_W,
    BOLTZMANN_J_PER_K,
    CIRCUIT_POWER_PER_BEAM_W,
    PA_MAX_EFFICIENCY,
    PA_OUTPUT_BACKOFF_DB,
    PA_SATURATION_POWER_W,
    SYSTEM_TEMPERATURE_K,
    fixed_power_w,
    pa_efficiency,
    supply_power_w,
    system_power_w,
)
from mcrl.env.service import resolve_service
from mcrl.env.step import _elevation_by_norad
from mcrl.runtime.energy_efficiency import additive_system_ee


OVERRIDE_ID = "B2_RATE_TARGET_SUM_POWER"  # Provenance: Astra iteration-2 skeleton item 1.
RATE_TARGET_BPS = 50.0e6  # Provenance: Astra iteration-2 skeleton item 3; magnitude inherited from the V0.24 memo.
POWER_RESIDUAL_TOLERANCE_W = 1.0e-10  # Provenance: Astra iteration-2 skeleton item 5.
POWER_ITERATION_LIMIT = 4_096  # Provenance: Astra iteration-2 skeleton item 5.
RATE_ATTAINMENT_FRACTION = 0.95  # Provenance: Astra iteration-2 skeleton items 7 and 12.
RX_GAIN_MAX_LINEAR = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)  # Provenance: canonical receiver boresight gain in mcrl.env.antenna.


class RateTargetPhysicsError(RuntimeError):
    """The detached override inputs or fixed-point mechanics are invalid."""


class RateTargetNonconvergence(RateTargetPhysicsError):
    """The declared 4,096 iterations did not reach the declared residual."""


@dataclass(frozen=True)
class RateTargetConfig:
    """The single declared B2 operating point, with inherited hardware."""

    rate_target_bps: float = RATE_TARGET_BPS
    beam_bandwidth_hz: float = BEAM_BANDWIDTH_HZ
    boltzmann_j_per_k: float = BOLTZMANN_J_PER_K
    system_temperature_k: float = SYSTEM_TEMPERATURE_K
    beam_power_cap_w: float = BEAM_POWER_MAX_W
    pa_max_efficiency: float = PA_MAX_EFFICIENCY
    pa_saturation_power_w: float = PA_SATURATION_POWER_W
    residual_tolerance_w: float = POWER_RESIDUAL_TOLERANCE_W
    iteration_limit: int = POWER_ITERATION_LIMIT

    def __post_init__(self) -> None:
        numeric = (
            self.rate_target_bps,
            self.beam_bandwidth_hz,
            self.boltzmann_j_per_k,
            self.system_temperature_k,
            self.beam_power_cap_w,
            self.pa_max_efficiency,
            self.pa_saturation_power_w,
            self.residual_tolerance_w,
        )
        if any(not math.isfinite(float(value)) or float(value) <= 0.0 for value in numeric):
            raise RateTargetPhysicsError("rate-target configuration values must be finite and positive")
        if type(self.iteration_limit) is not int or self.iteration_limit < 1:
            raise RateTargetPhysicsError("iteration_limit must be a positive exact integer")

    @property
    def noise_psd_w_per_hz(self) -> float:
        return self.boltzmann_j_per_k * self.system_temperature_k

    def as_receipt(self) -> dict[str, object]:
        return {
            "override_id": OVERRIDE_ID,
            "rate_target_bps_hex": self.rate_target_bps.hex(),
            "beam_bandwidth_hz_hex": self.beam_bandwidth_hz.hex(),
            "boltzmann_j_per_k_hex": self.boltzmann_j_per_k.hex(),
            "system_temperature_k_hex": self.system_temperature_k.hex(),
            "noise_psd_w_per_hz_hex": self.noise_psd_w_per_hz.hex(),
            "beam_power_cap_w_hex": self.beam_power_cap_w.hex(),
            "pa_max_efficiency_hex": self.pa_max_efficiency.hex(),
            "pa_output_backoff_db_hex": PA_OUTPUT_BACKOFF_DB.hex(),
            "pa_saturation_power_w_hex": self.pa_saturation_power_w.hex(),
            "circuit_power_per_beam_w_hex": CIRCUIT_POWER_PER_BEAM_W.hex(),
            "baseband_power_per_satellite_w_hex": BASEBAND_POWER_PER_SATELLITE_W.hex(),
            "residual_tolerance_w_hex": self.residual_tolerance_w.hex(),
            "iteration_limit": self.iteration_limit,
            "allocation": "UNIFORMLY_INTERLEAVED_OFDMA_W_OVER_SCHEDULED_ELIGIBLE_N",
            "interference": "BEAM_AVERAGE_PSD_TIMES_VICTIM_OVERLAP_EXCLUDING_SERVING_BEAM",
            "csi": "IDEAL_INSTANTANEOUS_INSIDE_PHY_POWER_CONTROL",
            "cap_allocation": "PROPORTIONAL_TO_UNCAPPED_Q_NO_REMOVAL_NO_REPACKING",
        }


@dataclass(frozen=True)
class SumPowerSolution:
    """Fixed point and the proportional per-user allocation."""

    target_sinr: np.ndarray
    user_bandwidth_hz: np.ndarray
    required_user_power_w: np.ndarray
    allocated_user_power_w: np.ndarray
    beam_power_w: np.ndarray
    interference_w: np.ndarray
    iterations: int
    residual_w: float


def _vector(value: object, *, field: str, size: int | None = None) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise RateTargetPhysicsError(f"{field} must be a numeric vector") from error
    if result.ndim != 1 or (size is not None and result.shape != (size,)):
        raise RateTargetPhysicsError(f"{field} has the wrong shape")
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise RateTargetPhysicsError(f"{field} must be finite and nonnegative")
    return np.array(result, dtype=np.float64, copy=True)


def solve_sum_power(
    *,
    desired_gain: object,
    cross_gain: object,
    serving_beam: object,
    beam_colors: object,
    config: RateTargetConfig = RateTargetConfig(),
) -> SumPowerSolution:
    """Solve the declared capped standard-interference fixed point from zero."""

    gain = _vector(desired_gain, field="desired_gain")
    users = int(gain.size)
    raw_beam = np.asarray(serving_beam)
    raw_colors = np.asarray(beam_colors)
    if raw_beam.shape != (users,) or raw_beam.dtype.kind not in "iu":
        raise RateTargetPhysicsError("serving_beam must be an integer user vector")
    beam = np.asarray(raw_beam, dtype=np.int64)
    if np.any(beam < 0):
        raise RateTargetPhysicsError("solve_sum_power accepts scheduled users only")
    beam_count = int(raw_colors.size)
    if raw_colors.ndim != 1 or raw_colors.dtype.kind not in "iu" or np.any(beam >= beam_count):
        raise RateTargetPhysicsError("beam colors or serving indices are malformed")
    colors = np.asarray(raw_colors, dtype=np.int64)
    cross = np.asarray(cross_gain, dtype=np.float64)
    if cross.shape != (users, beam_count) or not np.all(np.isfinite(cross)) or np.any(cross < 0.0):
        raise RateTargetPhysicsError("cross_gain must be finite nonnegative shape (users, beams)")
    if np.any(gain <= 0.0):
        raise RateTargetPhysicsError("every scheduled user needs strictly positive desired gain")

    load = np.bincount(beam, minlength=beam_count).astype(np.float64)
    bandwidth = config.beam_bandwidth_hz / load[beam]
    exponent = config.rate_target_bps / bandwidth
    if np.any(exponent > math.log2(np.finfo(np.float64).max)):
        raise RateTargetPhysicsError("rate-derived SINR overflowed")
    gamma = np.exp2(exponent) - 1.0
    noise = config.noise_psd_w_per_hz * bandwidth
    same_color = colors[None, :] == colors[beam, None]
    not_serving = np.arange(beam_count)[None, :] != beam[:, None]
    overlap = bandwidth[:, None] / config.beam_bandwidth_hz
    coupling = cross * same_color * not_serving * overlap

    power = np.zeros(beam_count, dtype=np.float64)
    residual = math.inf
    required = np.zeros(users, dtype=np.float64)
    for iteration in range(1, config.iteration_limit + 1):
        interference = coupling @ power
        required = gamma * (noise + interference) / gain
        requested = np.bincount(beam, weights=required, minlength=beam_count)
        updated = np.minimum(config.beam_power_cap_w, requested)
        residual = float(np.max(np.abs(updated - power))) if beam_count else 0.0
        power = updated
        if residual <= config.residual_tolerance_w:
            break
    else:
        raise RateTargetNonconvergence(
            f"sum-power fixed point exceeded {config.iteration_limit} iterations; residual={residual!r} W"
        )

    interference = coupling @ power
    required = gamma * (noise + interference) / gain
    requested = np.bincount(beam, weights=required, minlength=beam_count)
    final_updated = np.minimum(config.beam_power_cap_w, requested)
    final_residual = float(np.max(np.abs(final_updated - power))) if beam_count else 0.0
    if final_residual > config.residual_tolerance_w:
        raise RateTargetNonconvergence(
            f"sum-power final fixed-point residual={final_residual!r} W exceeds "
            f"{config.residual_tolerance_w!r} W"
        )
    scale = np.ones(beam_count, dtype=np.float64)
    positive = requested > 0.0
    scale[positive] = power[positive] / requested[positive]
    allocated = required * scale[beam]
    conserved = np.bincount(beam, weights=allocated, minlength=beam_count)
    if not np.allclose(conserved, power, rtol=0.0, atol=config.residual_tolerance_w):
        raise RateTargetPhysicsError("proportional cap allocation does not conserve beam power")
    return SumPowerSolution(
        target_sinr=gamma,
        user_bandwidth_hz=bandwidth,
        required_user_power_w=required,
        allocated_user_power_w=allocated,
        beam_power_w=power,
        interference_w=interference,
        iterations=iteration,
        residual_w=final_residual,
    )


def _satellite_positions(decision: Any) -> dict[int, np.ndarray]:
    result: dict[int, np.ndarray] = {}
    positions = np.asarray(decision.window_satellite_ecef_km, dtype=np.float64)
    for user, row in enumerate(np.asarray(decision.window_norad_ids, dtype=np.int64)):
        for slot, norad in enumerate(row.tolist()):
            if norad >= 0:
                result.setdefault(int(norad), positions[user, slot])
    return result


def evaluate_actions(
    environment: Any,
    actions: object,
    rng: np.random.Generator,
    *,
    enabled: bool = True,
    config: RateTargetConfig = RateTargetConfig(),
    pa_dc_power: Callable[[object], object] | None = None,
    override_id: str = OVERRIDE_ID,
) -> Any:
    """Evaluate one frozen anchor; disabled mode is the original-physics control."""

    if not enabled:
        return environment.evaluate_actions(np.asarray(actions), rng)
    if not getattr(environment, "_started", False) or environment._candidates is None:
        raise RateTargetPhysicsError("the environment has not been reset")
    decision = environment._candidates
    selected = assert_selected_actions_valid(np.asarray(actions), decision.slot_tables)
    users = int(environment.num_users)
    resolution = resolve_service(selected, decision.slot_tables, np.zeros(users, dtype=np.bool_))
    scheduled = np.flatnonzero(resolution.served)
    if scheduled.size == 0:
        return environment.evaluate_actions(selected, rng)

    beam_keys = list(resolution.active_beams)
    beam_index_of_key = {key: index for index, key in enumerate(beam_keys)}
    beam_index = np.full(users, -1, dtype=np.int64)
    for user in scheduled.tolist():
        key = (int(resolution.serving_satellite[user]), int(resolution.serving_cell[user]))
        beam_index[user] = beam_index_of_key[key]

    grid = environment.driver.grid
    satellites = _satellite_positions(decision)
    unit_radiating = build_radiating_beams(
        beam_norad_ids=np.asarray([key[0] for key in beam_keys], dtype=np.int64),
        beam_cell_ids=np.asarray([key[1] for key in beam_keys], dtype=np.int64),
        beam_power_w=np.ones(len(beam_keys), dtype=np.float64),
        satellite_ecef_by_norad=satellites,
        grid=grid,
    )
    local_rng = copy.deepcopy(rng)
    fading, shadow = environment._draw_fading(
        satellites,
        local_rng,
        _elevation_by_norad(decision),
        event="physics",
    )
    user_ecef = environment.driver.user_ecef_km()
    field = beam_field_at_users(
        user_ecef_km=user_ecef,
        radiating=unit_radiating,
        fading_by_norad=fading,
        shadow_db_by_norad=shadow,
    )
    fallback_position = next(iter(satellites.values()))
    boresight = np.stack([
        satellites[int(resolution.serving_satellite[user])]
        if resolution.served[user]
        else fallback_position
        for user in range(users)
    ])
    terms = received_power_terms(
        field,
        unit_radiating,
        user_ecef_km=user_ecef,
        boresight_satellite_ecef_km=boresight,
        boresight_norad_ids=np.asarray(resolution.serving_satellite, dtype=np.int64),
    )
    desired = terms[scheduled, beam_index[scheduled]]
    colors = grid.colors[np.asarray([key[1] for key in beam_keys], dtype=np.int64)]
    solved = solve_sum_power(
        desired_gain=desired,
        cross_gain=terms[scheduled],
        serving_beam=beam_index[scheduled],
        beam_colors=colors,
        config=config,
    )

    link_power = np.zeros(users, dtype=np.float64)
    link_power[scheduled] = solved.allocated_user_power_w
    sinr = np.zeros(users, dtype=np.float64)
    sinr[scheduled] = solved.allocated_user_power_w * desired / (
        config.noise_psd_w_per_hz * solved.user_bandwidth_hz + solved.interference_w
    )
    rate = np.zeros(users, dtype=np.float64)
    rate[scheduled] = solved.user_bandwidth_hz * np.log2(1.0 + sinr[scheduled])
    actual_radiating = build_radiating_beams(
        beam_norad_ids=unit_radiating.norad_ids,
        beam_cell_ids=unit_radiating.cell_ids,
        beam_power_w=solved.beam_power_w,
        satellite_ecef_by_norad=satellites,
        grid=grid,
    )
    same_satellite = unit_radiating.norad_ids[None, :] == resolution.serving_satellite[scheduled, None]
    contribution = (
        terms[scheduled]
        * solved.beam_power_w[None, :]
        * (solved.user_bandwidth_hz[:, None] / config.beam_bandwidth_hz)
        * (colors[None, :] == colors[beam_index[scheduled], None])
        * (np.arange(len(beam_keys))[None, :] != beam_index[scheduled, None])
    )
    intra = np.zeros(users, dtype=np.float64)
    inter = np.zeros(users, dtype=np.float64)
    intra[scheduled] = np.sum(contribution * same_satellite, axis=1)
    inter[scheduled] = np.sum(contribution * ~same_satellite, axis=1)
    interference = InterferenceBreakdown(intra_w=intra, inter_w=inter)

    if pa_dc_power is None:
        efficiency = pa_efficiency(
            solved.beam_power_w,
            max_efficiency=config.pa_max_efficiency,
            saturation_power_w=config.pa_saturation_power_w,
        )
        supply = supply_power_w(solved.beam_power_w, efficiency)
    else:
        supply = np.asarray(pa_dc_power(solved.beam_power_w), dtype=np.float64)
        if supply.shape != solved.beam_power_w.shape or not np.all(np.isfinite(supply)) or np.any(supply < 0.0):
            raise RateTargetPhysicsError("detached PA DC model returned an invalid beam-power vector")
    satellite_ids = sorted({key[0] for key in beam_keys})
    beams_by_satellite = np.asarray(
        [sum(key[0] == norad for key in beam_keys) for norad in satellite_ids],
        dtype=np.float64,
    )
    fixed = fixed_power_w(beams_by_satellite)
    total = system_power_w(supply, beams_by_satellite)
    loads = np.asarray([resolution.eligible_load_by_beam[key] for key in beam_keys], dtype=np.float64)
    energy = additive_system_ee(
        rate,
        total,
        serving_beam_u=beam_index,
        beam_load_b=loads,
        beam_active_b=loads > 0.0,
    )
    interval_s = float(environment.driver.config.ephemeris.time_step_s)
    return SimpleNamespace(
        resolution=resolution,
        radiating=actual_radiating,
        link_power_w=link_power,
        link_sinr=sinr,
        link_rate_bps=rate,
        capacity_bits=rate * interval_s,
        delivered_bits=rate * interval_s,
        system_power_w=total,
        fixed_power_w=fixed,
        energy=energy,
        interference=interference,
        diagnostics={
            "override_id": override_id,
            "iterations": solved.iterations,
            "residual_w": solved.residual_w,
            "required_user_power_w": solved.required_user_power_w,
            "allocated_user_power_w": solved.allocated_user_power_w,
            "target_sinr": solved.target_sinr,
            "beam_power_w": solved.beam_power_w,
            "pa_dc_power_w": supply,
            "fixed_circuit_power_w": fixed,
            "target_attained": rate[scheduled] >= RATE_ATTAINMENT_FRACTION * config.rate_target_bps,
            "ideal_instantaneous_csi": True,
        },
        separation_deg=boresight_separation_deg(
            user_ecef_km=user_ecef,
            radiating=actual_radiating,
            boresight_satellite_ecef_km=boresight,
        ),
    )


__all__ = [
    "OVERRIDE_ID",
    "POWER_ITERATION_LIMIT",
    "POWER_RESIDUAL_TOLERANCE_W",
    "RATE_ATTAINMENT_FRACTION",
    "RATE_TARGET_BPS",
    "RateTargetConfig",
    "RateTargetNonconvergence",
    "RateTargetPhysicsError",
    "SumPowerSolution",
    "evaluate_actions",
    "solve_sum_power",
]
