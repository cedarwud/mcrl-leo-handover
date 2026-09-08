"""Dense catalogue evaluation for the V0.25 rate-target TDM architecture.

This module is deliberately narrow: it implements the exact ``a-r`` radiation
and integration equations for a whole configuration catalogue backed by a
``PrimitiveStepArrays`` object.  The scalar object path remains the authority
used by KATs; this path removes per-row Python objects from real-world units.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from mcrl.errors import MCRLContractError

from .acm import ACM_MODES, rate_target_sinr
from .channel import noise_power_w
from .constants_v025 import (
    BASEBAND_POWER_PER_ACTIVE_SATELLITE_W,
    BEAM_BANDWIDTH_HZ,
    BEAM_RF_CAP_W,
    CIRCUIT_POWER_PER_CHAIN_W,
    D2_MEASUREMENT_STEP_S,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
    POWER_SOLVER_ITERATION_CAP,
    POWER_SOLVER_TOLERANCE_W,
    RATE_TARGET_BPS,
)
from .tapes import PrimitiveStepArrays


@dataclass(frozen=True)
class BatchARResult:
    bits: np.ndarray
    joules: np.ndarray
    pa_j: np.ndarray
    circuit_j: np.ndarray
    baseband_j: np.ndarray
    decoding_time_s: np.ndarray
    feasible: np.ndarray
    attained: np.ndarray
    residual_w: np.ndarray
    mode_counts: np.ndarray
    plateau_users: np.ndarray
    transmissions: np.ndarray
    cap_hits: np.ndarray
    valid: np.ndarray


def _readonly(value: np.ndarray) -> np.ndarray:
    result = np.asarray(value)
    result.setflags(write=False)
    return result


def _slot_grid(maximum_occupancy: int) -> tuple[np.ndarray, np.ndarray]:
    boundaries = {0.0, 1.0}
    for occupancy in range(1, maximum_occupancy + 1):
        boundaries.update(index / occupancy for index in range(1, occupancy))
    ordered = np.asarray(sorted(boundaries), dtype=np.float64)
    return (ordered[1:] - ordered[:-1], (ordered[1:] + ordered[:-1]) / 2.0)


def evaluate_ar_tdm_catalogue(
    arrays: PrimitiveStepArrays,
    selected_rows: np.ndarray,
    *,
    field: str = "realised",
    chunk_size: int = 256,
) -> BatchARResult:
    """Evaluate ``C x U`` selected candidate-row indices without row objects.

    A row index of ``-1`` is the explicit null action.  The common rational
    TDM partition is an exact refinement of every configuration's scalar slot
    partition, so splitting a constant slot cannot alter rates or energy.
    """

    rows_all = np.asarray(selected_rows, dtype=np.int64)
    if rows_all.ndim != 2 or rows_all.shape[1] != arrays.users.size:
        raise MCRLContractError("selected_rows must have shape (configurations, users)")
    if field not in {"nominal", "realised"}:
        raise MCRLContractError("batch field must be nominal or realised")
    configurations, users = rows_all.shape
    modes = ACM_MODES
    thresholds = np.asarray([row.threshold_linear for row in modes])
    efficiencies = np.asarray([row.spectral_efficiency_bit_per_s_hz for row in modes])
    gamma = np.asarray(
        [0.0]
        + [
            np.nan if rate_target_sinr(RATE_TARGET_BPS, BEAM_BANDWIDTH_HZ, n) is None
            else float(rate_target_sinr(RATE_TARGET_BPS, BEAM_BANDWIDTH_HZ, n))
            for n in range(1, users + 1)
        ],
        dtype=np.float64,
    )
    noise = noise_power_w(BEAM_BANDWIDTH_HZ)
    bits = np.zeros((configurations, users), dtype=np.float64)
    decoding = np.zeros_like(bits)
    feasible_all = np.ones((configurations, users), dtype=np.bool_)
    residual_max = np.zeros(configurations, dtype=np.float64)
    components = np.zeros((configurations, 3), dtype=np.float64)
    mode_counts = np.zeros((configurations, len(modes) + 1), dtype=np.int64)
    plateau = np.ones((configurations, users), dtype=np.bool_)
    seen = np.zeros((configurations, users), dtype=np.bool_)
    transmissions = np.zeros(configurations, dtype=np.int64)
    cap_hits = np.zeros(configurations, dtype=np.int64)
    valid_result = np.ones(configurations, dtype=np.bool_)
    row_to_aggressor = {
        (int(identity[0]), int(identity[1])): index
        for index, identity in enumerate(arrays.aggressor_identities)
    }
    row_aggressor = np.asarray(
        [
            row_to_aggressor.get((int(identity[0]), int(identity[1])), -1)
            for identity in arrays.identities
        ],
        dtype=np.int64,
    )
    beam_code_of = {
        identity: index
        for index, identity in enumerate(
            sorted({(int(row[0]), int(row[1])) for row in arrays.identities.tolist()})
        )
    }
    row_beam_code = np.asarray(
        [
            beam_code_of[(int(identity[0]), int(identity[1]))]
            for identity in arrays.identities
        ],
        dtype=np.int64,
    )
    # Keep rare high-occupancy evacuation profiles out of ordinary chunks;
    # otherwise one such row forces every neighbouring unilateral through a
    # much finer universal rational slot grid.
    initial_maximum = np.zeros(configurations, dtype=np.int64)
    for config_index, selected in enumerate(rows_all):
        selected_codes = row_beam_code[selected[selected >= 0]]
        if selected_codes.size:
            initial_maximum[config_index] = int(
                np.max(np.unique(selected_codes, return_counts=True)[1])
            )
    order = np.argsort(initial_maximum, kind="stable")
    inverse_order = np.argsort(order)
    rows_all = rows_all[order]
    satellite_of = {
        int(identity[0]): int(column)
        for identity, column in zip(
            arrays.aggressor_identities,
            arrays.aggressor_satellite_column,
            strict=True,
        )
    }
    row_satellite = np.asarray(
        [satellite_of.get(int(identity[0]), 0) for identity in arrays.identities],
        dtype=np.int64,
    )
    user_axis = np.arange(users, dtype=np.int64)
    lower_user = user_axis[None, None, :] < user_axis[None, :, None]

    for low in range(0, configurations, chunk_size):
        high = min(configurations, low + chunk_size)
        selected = rows_all[low:high]
        count = high - low
        valid_assignment = selected >= 0
        safe_rows = np.maximum(selected, 0)
        aggressor = row_aggressor[safe_rows]
        safe_aggressor = np.maximum(aggressor, 0)
        beam_code = row_beam_code[safe_rows]
        victim_color = arrays.colors[safe_rows]
        wanted_slot = arrays.row_wanted_slot[safe_rows]
        aggressor_color = victim_color
        aggressor_satellite = row_satellite[safe_rows]
        aggressor_norad = arrays.identities[safe_rows, 0]
        previous_rate = previous_decode = previous_energy = None

        for boundary in range(48):
            live = valid_assignment & arrays.visible[boundary, safe_rows] \
                & arrays.d2_eligible[boundary, safe_rows] \
                & arrays.cell_reachable[boundary, safe_rows]
            same_beam = beam_code[:, :, None] == beam_code[:, None, :]
            occupancy = np.sum(same_beam & live[:, None, :], axis=2)
            maximum = int(np.max(occupancy, initial=1))
            fractions, midpoints = _slot_grid(maximum)
            boundary_rate = np.zeros((count, users), dtype=np.float64)
            boundary_decode = np.zeros((count, users), dtype=np.bool_)
            boundary_feasible = np.zeros((count, users), dtype=np.bool_)
            boundary_energy = np.zeros((count, 3), dtype=np.float64)
            rank = np.sum(same_beam & live[:, None, :] & lower_user, axis=2)
            direct_nominal = arrays.nominal_gain[boundary, safe_rows]
            direct_field = (
                direct_nominal
                if field == "nominal"
                else arrays.realised_gain[boundary, safe_rows]
            )
            base_cross = arrays.cross_base_nominal[
                boundary,
                user_axis[None, :, None],
                safe_aggressor[:, None, :],
            ]
            receive = arrays.receive_gain_by_wanted_slot[
                boundary,
                user_axis[None, :, None],
                wanted_slot[:, :, None],
                aggressor_satellite[:, None, :],
            ]
            nominal_cross = base_cross * receive
            colour_mask = victim_color[:, :, None] == aggressor_color[:, None, :]
            available_aggressor = aggressor[:, None, :] >= 0
            nominal_cross *= colour_mask & ~same_beam & available_aggressor
            if field == "realised":
                field_cross = nominal_cross * arrays.fading_by_satellite[
                    boundary,
                    user_axis[None, :, None],
                    aggressor_satellite[:, None, :],
                ]
            else:
                field_cross = nominal_cross

            for fraction, midpoint in zip(fractions, midpoints, strict=True):
                active = live & (rank == np.floor(midpoint * occupancy).astype(np.int64))
                active_pair = active[:, :, None] & active[:, None, :]
                coupling = nominal_cross * active_pair
                targets = gamma[np.minimum(occupancy, users)]
                forced = active & np.isnan(targets)
                targets = np.nan_to_num(targets, nan=1.0)
                power = np.zeros((count, users), dtype=np.float64)
                residual = np.full(count, math.inf, dtype=np.float64)
                for _iteration in range(POWER_SOLVER_ITERATION_CAP):
                    interference = np.matmul(coupling, power[..., None])[..., 0]
                    updated = np.minimum(
                        BEAM_RF_CAP_W,
                        targets * (noise + interference) / direct_nominal,
                    )
                    updated = np.where(active, updated, 0.0)
                    updated[forced] = BEAM_RF_CAP_W
                    residual = np.max(np.abs(updated - power), axis=1)
                    power = updated
                    if bool(np.all(residual <= POWER_SOLVER_TOLERANCE_W)):
                        break
                final = np.minimum(
                    BEAM_RF_CAP_W,
                    targets
                    * (
                        noise
                        + np.matmul(coupling, power[..., None])[..., 0]
                    )
                    / direct_nominal,
                )
                final = np.where(active, final, 0.0)
                final[forced] = BEAM_RF_CAP_W
                residual = np.max(np.abs(final - power), axis=1)
                residual_max[low:high] = np.maximum(residual_max[low:high], residual)
                valid_result[low:high] &= residual <= POWER_SOLVER_TOLERANCE_W
                power = np.minimum(
                    BEAM_RF_CAP_W,
                    np.nextafter(final * (1.0 + 2.0e-9), np.inf),
                )
                power = np.where(active, power, 0.0)
                power[forced] = BEAM_RF_CAP_W
                realised_interference = np.matmul(
                    field_cross * active_pair, power[..., None]
                )[..., 0]
                sinr = np.where(
                    active,
                    power * direct_field / (noise + realised_interference),
                    0.0,
                )
                eligible_modes = sinr[:, :, None] >= thresholds[None, None, :]
                mode_index = np.argmax(
                    np.where(eligible_modes, efficiencies[None, None, :], -1.0),
                    axis=2,
                )
                served = active & np.any(eligible_modes, axis=2)
                chosen_efficiency = efficiencies[mode_index]
                slot_rate = np.where(served, chosen_efficiency * BEAM_BANDWIDTH_HZ, 0.0)
                boundary_rate += fraction * slot_rate
                boundary_decode |= served
                nominal_sinr = np.where(
                    active,
                    power
                    * direct_nominal
                    / (
                        noise
                        + np.matmul(coupling, power[..., None])[..., 0]
                    ),
                    0.0,
                )
                boundary_feasible |= active & ~forced & (nominal_sinr >= targets)
                flat_config, flat_user = np.nonzero(active)
                flat_modes = np.where(
                    served[flat_config, flat_user],
                    mode_index[flat_config, flat_user] + 1,
                    0,
                )
                np.add.at(mode_counts[low:high], (flat_config, flat_modes), 1)
                seen[low:high] |= active
                top_mode_index = int(np.argmax(efficiencies))
                plateau[low:high] &= ~active | (mode_index == top_mode_index)
                transmissions[low:high] += np.sum(active, axis=1)
                cap_hits[low:high] += np.sum(
                    active & (power >= BEAM_RF_CAP_W - 1.0e-9), axis=1
                )
                pa_w = np.sum(
                    np.where(
                        active & (power > 0.0),
                        np.sqrt(power * PA_SATURATION_POWER_W) / PA_MAX_EFFICIENCY,
                        0.0,
                    ),
                    axis=1,
                )
                circuit_w = np.sum(active & (power > 0.0), axis=1) * CIRCUIT_POWER_PER_CHAIN_W
                same_sat = aggressor_norad[:, :, None] == aggressor_norad[:, None, :]
                earlier_active_sat = np.any(
                    same_sat & (active[:, None, :] & lower_user), axis=2
                )
                active_satellites = np.sum(active & ~earlier_active_sat, axis=1)
                boundary_energy += fraction * np.stack(
                    (
                        pa_w,
                        circuit_w,
                        active_satellites * BASEBAND_POWER_PER_ACTIVE_SATELLITE_W,
                    ),
                    axis=1,
                )

            # The scalar roster path records a missing in-step transmission as
            # infeasible, rather than silently dropping that user.
            feasible_all[low:high] &= boundary_feasible
            if previous_rate is not None:
                bits[low:high] += 0.5 * (previous_rate + boundary_rate) * D2_MEASUREMENT_STEP_S
                decoding[low:high] += 0.5 * (
                    previous_decode.astype(np.float64) + boundary_decode.astype(np.float64)
                ) * D2_MEASUREMENT_STEP_S
                components[low:high] += 0.5 * (previous_energy + boundary_energy) * D2_MEASUREMENT_STEP_S
            previous_rate = boundary_rate
            previous_decode = boundary_decode
            previous_energy = boundary_energy

    joules = np.sum(components, axis=1)
    attained = bits >= RATE_TARGET_BPS * (47 * D2_MEASUREMENT_STEP_S)
    return BatchARResult(
        *(
            _readonly(value)
            for value in (
                bits[inverse_order],
                joules[inverse_order],
                components[inverse_order, 0],
                components[inverse_order, 1],
                components[inverse_order, 2],
                decoding[inverse_order],
                feasible_all[inverse_order],
                attained[inverse_order],
                residual_max[inverse_order],
                mode_counts[inverse_order],
                np.sum(plateau & seen, axis=1)[inverse_order],
                transmissions[inverse_order],
                cap_hits[inverse_order],
                valid_result[inverse_order],
            )
        )
    )


__all__ = ["BatchARResult", "evaluate_ar_tdm_catalogue"]
