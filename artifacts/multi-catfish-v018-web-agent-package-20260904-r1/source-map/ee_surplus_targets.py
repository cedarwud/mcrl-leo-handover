"""Formula-only Multi-Catfish fixed-lambda EE-surplus decompositions.

The module has no trainer integration.  It consumes already matched physical
traces.  The isolated-world V0.2 function is retained only so its frozen
receipts remain interpretable.  New work uses the V0.3 focal/non-focal/horizon
decomposition, which keeps every component in one physical system.

V0.2 verifies

    z1_direct + z2_temporal + z3_spatial = total fixed-lambda EE surplus.

V0.3 verifies

    z1_focal + z2_temporal + z3_nonfocal = total fixed-lambda EE surplus.

The caller remains responsible for the causal contracts: branches may initially
differ only in the focal action, use common random numbers, and be sealed before
their outcomes are inspected.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..errors import MCRLContractError


@dataclass(frozen=True)
class EESurplusAxisTargets:
    """Native-bit targets for the three EE-axis Q routes."""

    z1_direct_surplus_bits: float
    z2_temporal_surplus_bits: float
    z3_spatial_surplus_bits: float
    system_step_surplus_bits: tuple[float, ...]
    system_window_surplus_bits: float
    reconstructed_window_surplus_bits: float
    identity_residual_bits: float
    lambda_bits_per_j: float
    interval_s: float


@dataclass(frozen=True)
class EESurplusAxisTargetsV03:
    """Native-bit V0.3 targets from one matched multi-user physical system."""

    z1_focal_surplus_bits: float
    z2_temporal_surplus_bits: float
    z3_nonfocal_externality_bits: float
    system_step_surplus_bits: tuple[float, ...]
    system_window_surplus_bits: float
    reconstructed_window_surplus_bits: float
    identity_residual_bits: float
    focal_user: int
    lambda_bits_per_j: float
    interval_s: float


def _trace(
    rates_bps: np.ndarray,
    power_w: np.ndarray,
    *,
    name: str,
) -> tuple[np.ndarray, np.ndarray]:
    rates = np.asarray(rates_bps, dtype=np.float64)
    power = np.asarray(power_w, dtype=np.float64)
    if rates.ndim != 2 or rates.shape[0] < 1 or rates.shape[1] < 1:
        raise MCRLContractError(f"{name} rates must have shape (H, U), H,U >= 1")
    if power.shape != (rates.shape[0],):
        raise MCRLContractError(
            f"{name} power must have shape ({rates.shape[0]},), got {power.shape}"
        )
    if not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
        raise MCRLContractError(f"{name} rates must be finite and non-negative")
    if not np.all(np.isfinite(power)) or np.any(power < 0.0):
        raise MCRLContractError(f"{name} power must be finite and non-negative")
    positive_bits_on_dark = (power == 0.0) & (rates.sum(axis=1) > 0.0)
    if np.any(positive_bits_on_dark):
        raise MCRLContractError(f"{name} has positive throughput at zero power")
    return rates, power


def _isolated_point(rate_bps: float, power_w: float, *, name: str) -> tuple[float, float]:
    rate = float(rate_bps)
    power = float(power_w)
    if not math.isfinite(rate) or rate < 0.0:
        raise MCRLContractError(f"{name} rate must be finite and non-negative")
    if not math.isfinite(power) or power < 0.0:
        raise MCRLContractError(f"{name} power must be finite and non-negative")
    if power == 0.0 and rate > 0.0:
        raise MCRLContractError(f"{name} has positive throughput at zero power")
    return rate, power


def ee_surplus_axis_targets(
    *,
    lambda_bits_per_j: float,
    interval_s: float,
    reference_system_rates_bps: np.ndarray,
    reference_system_power_w: np.ndarray,
    candidate_system_rates_bps: np.ndarray,
    candidate_system_power_w: np.ndarray,
    reference_isolated_rate_bps: float,
    reference_isolated_power_w: float,
    candidate_isolated_rate_bps: float,
    candidate_isolated_power_w: float,
) -> EESurplusAxisTargets:
    """Compute the fixed-global-multiplier direct/temporal/spatial targets."""

    multiplier = float(lambda_bits_per_j)
    interval = float(interval_s)
    if not math.isfinite(multiplier) or multiplier <= 0.0:
        raise MCRLContractError(
            "lambda_bits_per_j must be finite and strictly positive"
        )
    if not math.isfinite(interval) or interval <= 0.0:
        raise MCRLContractError("interval_s must be finite and strictly positive")

    reference_rates, reference_power = _trace(
        reference_system_rates_bps,
        reference_system_power_w,
        name="reference system",
    )
    candidate_rates, candidate_power = _trace(
        candidate_system_rates_bps,
        candidate_system_power_w,
        name="candidate system",
    )
    if candidate_rates.shape != reference_rates.shape:
        raise MCRLContractError(
            "candidate and reference system rates must have identical (H, U) shape"
        )

    reference_iso_rate, reference_iso_power = _isolated_point(
        reference_isolated_rate_bps,
        reference_isolated_power_w,
        name="reference isolated",
    )
    candidate_iso_rate, candidate_iso_power = _isolated_point(
        candidate_isolated_rate_bps,
        candidate_isolated_power_w,
        name="candidate isolated",
    )

    # Subtract matched per-user rates before summing.  ``sum(C)-sum(M)`` loses
    # several bits of precision when both systems carry O(1e10) bit/s and the
    # unilateral effect is comparatively small.
    delta_rates_by_user = candidate_rates - reference_rates
    delta_bits_by_step = np.asarray(
        [
            interval * math.fsum(float(value) for value in row)
            for row in delta_rates_by_user
        ],
        dtype=np.float64,
    )
    delta_energy_by_step = interval * (candidate_power - reference_power)
    system_step_surplus = delta_bits_by_step - multiplier * delta_energy_by_step

    z1 = interval * (
        (candidate_iso_rate - reference_iso_rate)
        - multiplier * (candidate_iso_power - reference_iso_power)
    )
    immediate_system_surplus = float(system_step_surplus[0])
    z3 = immediate_system_surplus - z1
    z2 = float(math.fsum(float(value) for value in system_step_surplus[1:]))
    total = float(math.fsum(float(value) for value in system_step_surplus))
    reconstructed = float(z1 + z2 + z3)
    residual = reconstructed - total
    tolerance = max(1e-9, 128.0 * math.ulp(max(abs(total), 1.0)))
    if not math.isclose(reconstructed, total, rel_tol=0.0, abs_tol=tolerance):
        raise MCRLContractError("EE-surplus target sum lost the V0.2 identity")

    return EESurplusAxisTargets(
        z1_direct_surplus_bits=float(z1),
        z2_temporal_surplus_bits=float(z2),
        z3_spatial_surplus_bits=float(z3),
        system_step_surplus_bits=tuple(
            float(value) for value in system_step_surplus.tolist()
        ),
        system_window_surplus_bits=total,
        reconstructed_window_surplus_bits=reconstructed,
        identity_residual_bits=float(residual),
        lambda_bits_per_j=multiplier,
        interval_s=interval,
    )


def ee_surplus_axis_targets_v03(
    *,
    lambda_bits_per_j: float,
    interval_s: float,
    focal_user: int,
    reference_system_rates_bps: np.ndarray,
    reference_system_power_w: np.ndarray,
    candidate_system_rates_bps: np.ndarray,
    candidate_system_power_w: np.ndarray,
) -> EESurplusAxisTargetsV03:
    """Compute the V0.3 focal/temporal/non-focal EE-surplus targets.

    At offset zero, all system energy change is attributed to ``z1`` because
    the focal action is the only intervention.  ``z3`` is therefore the rate
    externality on non-focal users and is invariant to the chosen multiplier.
    Every system effect after offset zero belongs to the temporal target.
    """

    multiplier = float(lambda_bits_per_j)
    interval = float(interval_s)
    if not math.isfinite(multiplier) or multiplier <= 0.0:
        raise MCRLContractError(
            "lambda_bits_per_j must be finite and strictly positive"
        )
    if not math.isfinite(interval) or interval <= 0.0:
        raise MCRLContractError("interval_s must be finite and strictly positive")

    reference_rates, reference_power = _trace(
        reference_system_rates_bps,
        reference_system_power_w,
        name="reference system",
    )
    candidate_rates, candidate_power = _trace(
        candidate_system_rates_bps,
        candidate_system_power_w,
        name="candidate system",
    )
    if candidate_rates.shape != reference_rates.shape:
        raise MCRLContractError(
            "candidate and reference system rates must have identical (H, U) shape"
        )
    focal = int(focal_user)
    if focal != focal_user or not 0 <= focal < reference_rates.shape[1]:
        raise MCRLContractError("focal_user must index the trace user dimension")

    # Subtract matched per-user rates before summing.  ``sum(C)-sum(M)`` loses
    # precision when the common system rate is much larger than the unilateral
    # effect being attributed.
    delta_rates_by_user = candidate_rates - reference_rates
    delta_bits_by_step = np.asarray(
        [
            interval * math.fsum(float(value) for value in row)
            for row in delta_rates_by_user
        ],
        dtype=np.float64,
    )
    delta_energy_by_step = interval * (candidate_power - reference_power)
    system_step_surplus = delta_bits_by_step - multiplier * delta_energy_by_step

    focal_delta_bits = interval * delta_rates_by_user[0, focal]
    opening_delta_energy = float(delta_energy_by_step[0])
    z1 = float(focal_delta_bits - multiplier * opening_delta_energy)

    nonfocal_mask = np.ones(reference_rates.shape[1], dtype=np.bool_)
    nonfocal_mask[focal] = False
    z3 = float(
        interval
        * math.fsum(
            float(value)
            for value in delta_rates_by_user[0, nonfocal_mask]
        )
    )
    z2 = float(math.fsum(float(value) for value in system_step_surplus[1:]))
    total = float(math.fsum(float(value) for value in system_step_surplus))
    reconstructed = float(math.fsum((z1, z3, z2)))
    residual = reconstructed - total

    # The terms can be O(1e11) bits while their signed sum is near zero.  The
    # tolerance therefore follows the floating-point error scale of the terms,
    # not only the (possibly cancelled) result.
    magnitude = max(
        1.0,
        abs(total),
        abs(z1) + abs(z2) + abs(z3),
        float(np.abs(system_step_surplus).sum()),
    )
    tolerance = 512.0 * np.finfo(np.float64).eps * magnitude
    if abs(residual) > tolerance:
        raise MCRLContractError("EE-surplus target sum lost the V0.3 identity")

    return EESurplusAxisTargetsV03(
        z1_focal_surplus_bits=z1,
        z2_temporal_surplus_bits=z2,
        z3_nonfocal_externality_bits=z3,
        system_step_surplus_bits=tuple(
            float(value) for value in system_step_surplus.tolist()
        ),
        system_window_surplus_bits=total,
        reconstructed_window_surplus_bits=reconstructed,
        identity_residual_bits=float(residual),
        focal_user=focal,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
    )
