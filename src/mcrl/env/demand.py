"""Finite per-user offered demand and delivered-goodput accounting.

The model intentionally has one parameter. It caps each user's Shannon
capacity over a decision interval; it does not alter admission, bandwidth,
beam activation, transmit power, or interval duration.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class DemandModel:
    """A constant offered demand for every user, in bit/s.

    ``math.inf`` is the G0 full-buffer control and therefore the environment
    default. Finite values implement ``B_u = min(dt * R_u, dt * d_u)``.
    """

    demand_bits_per_s: float = math.inf

    def __post_init__(self) -> None:
        if isinstance(self.demand_bits_per_s, bool):
            raise ValueError("demand_bits_per_s must be positive or infinity")
        value = float(self.demand_bits_per_s)
        if math.isnan(value) or value <= 0.0:
            raise ValueError("demand_bits_per_s must be positive or infinity")

    def delivered_bits(
        self, capacity_rate_bits_per_s: object, *, interval_s: float
    ) -> np.ndarray:
        """Return the per-user interval goodput without changing capacity."""

        rates = np.asarray(capacity_rate_bits_per_s, dtype=np.float64)
        if rates.ndim != 1 or not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
            raise ValueError("capacity rates must be a finite nonnegative vector")
        if not math.isfinite(interval_s) or interval_s <= 0.0:
            raise ValueError("interval_s must be finite and positive")
        capacity = rates * float(interval_s)
        if math.isinf(float(self.demand_bits_per_s)):
            # Preserve the old multiplication bytes exactly in G0.
            return capacity
        offered = float(interval_s) * float(self.demand_bits_per_s)
        return np.minimum(capacity, offered)


__all__ = ["DemandModel"]
