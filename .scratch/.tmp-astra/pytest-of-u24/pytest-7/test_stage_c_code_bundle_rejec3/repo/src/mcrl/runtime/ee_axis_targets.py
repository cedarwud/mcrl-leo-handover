"""Candidate EE-axis targets for the Multi-Catfish formula-first gate.

This module is deliberately not wired into the trainer.  It turns one matched
candidate/reference trace pair into three finite-horizon action advantages
whose sum is exactly the canonical ratio-of-sums EE change:

* ``z1``: immediate focal-user EE-contribution change;
* ``z2``: full-horizon EE change beyond the immediate system change;
* ``z3``: immediate non-focal EE-contribution change.

The names describe an accounting partition.  Calling ``z2`` temporal and
``z3`` spatial additionally requires axis-restricted intervention grammars and
the observability/local-execution gates in the redesign contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..errors import MCRLContractError


@dataclass(frozen=True)
class EEAxisTargets:
    """Three matched EE advantages and their exact-identity diagnostics."""

    z1_immediate_focal_bits_per_j: float
    z2_horizon_residual_bits_per_j: float
    z3_immediate_nonfocal_bits_per_j: float
    reference_immediate_ee_bits_per_j: float
    candidate_immediate_ee_bits_per_j: float
    reference_horizon_ee_bits_per_j: float
    candidate_horizon_ee_bits_per_j: float
    delta_horizon_ee_bits_per_j: float
    reconstructed_delta_ee_bits_per_j: float
    identity_residual_bits_per_j: float


def _validated_trace(
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
    if not np.all(np.isfinite(power)) or np.any(power <= 0.0):
        raise MCRLContractError(f"{name} power must be finite and strictly positive")
    return rates, power


def ee_axis_targets(
    *,
    reference_rates_bps: np.ndarray,
    reference_power_w: np.ndarray,
    candidate_rates_bps: np.ndarray,
    candidate_power_w: np.ndarray,
    focal_user: int,
    interval_s: float,
) -> EEAxisTargets:
    """Compute the exact direct/residual/externality accounting partition.

    Candidate and reference must cover the same users, offsets, and interval.
    The interval cancels from each EE ratio but remains explicit so callers
    cannot accidentally compare traces with an unspecified time basis.
    """

    reference_rates, reference_power = _validated_trace(
        reference_rates_bps, reference_power_w, name="reference"
    )
    candidate_rates, candidate_power = _validated_trace(
        candidate_rates_bps, candidate_power_w, name="candidate"
    )
    if candidate_rates.shape != reference_rates.shape:
        raise MCRLContractError(
            "candidate and reference rates must have identical (H, U) shape"
        )
    if isinstance(focal_user, bool) or not isinstance(focal_user, (int, np.integer)):
        raise MCRLContractError("focal_user must be an integer")
    focal = int(focal_user)
    if not 0 <= focal < reference_rates.shape[1]:
        raise MCRLContractError("focal_user is outside the trace user axis")
    interval = float(interval_s)
    if not math.isfinite(interval) or interval <= 0.0:
        raise MCRLContractError("interval_s must be finite and strictly positive")

    reference_immediate_contributions = reference_rates[0] / reference_power[0]
    candidate_immediate_contributions = candidate_rates[0] / candidate_power[0]
    reference_immediate_ee = float(reference_immediate_contributions.sum())
    candidate_immediate_ee = float(candidate_immediate_contributions.sum())
    delta_immediate_ee = candidate_immediate_ee - reference_immediate_ee

    reference_bits_u = interval * reference_rates.sum(axis=0)
    candidate_bits_u = interval * candidate_rates.sum(axis=0)
    reference_energy = interval * float(reference_power.sum())
    candidate_energy = interval * float(candidate_power.sum())
    reference_horizon_contributions = reference_bits_u / reference_energy
    candidate_horizon_contributions = candidate_bits_u / candidate_energy
    reference_horizon_ee = float(reference_horizon_contributions.sum())
    candidate_horizon_ee = float(candidate_horizon_contributions.sum())
    delta_horizon_ee = candidate_horizon_ee - reference_horizon_ee

    z1 = float(
        candidate_immediate_contributions[focal]
        - reference_immediate_contributions[focal]
    )
    nonfocal = np.ones(reference_rates.shape[1], dtype=np.bool_)
    nonfocal[focal] = False
    z3 = float(
        candidate_immediate_contributions[nonfocal].sum()
        - reference_immediate_contributions[nonfocal].sum()
    )
    z2 = float(delta_horizon_ee - delta_immediate_ee)
    reconstructed = float(z1 + z2 + z3)
    residual = float(reconstructed - delta_horizon_ee)
    tolerance = max(
        64.0 * math.ulp(max(abs(delta_horizon_ee), 1.0)),
        1e-12 * max(abs(delta_horizon_ee), 1.0),
    )
    if not math.isclose(reconstructed, delta_horizon_ee, rel_tol=0.0, abs_tol=tolerance):
        raise MCRLContractError("EE-axis target sum lost the exact accounting identity")

    return EEAxisTargets(
        z1_immediate_focal_bits_per_j=z1,
        z2_horizon_residual_bits_per_j=z2,
        z3_immediate_nonfocal_bits_per_j=z3,
        reference_immediate_ee_bits_per_j=reference_immediate_ee,
        candidate_immediate_ee_bits_per_j=candidate_immediate_ee,
        reference_horizon_ee_bits_per_j=reference_horizon_ee,
        candidate_horizon_ee_bits_per_j=candidate_horizon_ee,
        delta_horizon_ee_bits_per_j=delta_horizon_ee,
        reconstructed_delta_ee_bits_per_j=reconstructed,
        identity_residual_bits_per_j=residual,
    )
