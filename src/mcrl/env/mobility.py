"""User scatter and random-wandering mobility (MODQN §IV).

§IV gives three things and no more: 100 users, 30 km/h, and the phrase
"random wandering" over a 200 x 90 km service area at (40°N, 116°E).
Everything below that is **S** and disclosed here.

⚠ Two ported defaults did **not** match §IV and are not used:
``user_scatter_distribution="uniform-circular"`` with a 50 km radius (§IV
gives a 200 x 90 km rectangle) and ``mobility_model="deterministic-heading"``
(§IV says random wandering).  Both alternatives exist in ``StepConfig``; this
module implements the §IV pair.

**Boundary behaviour is not in any source, so it is declared.**  Users
reflect off the service-area edge.  The two alternatives were rejected for
reasons that would show up in the rewards:

* *wrap-around* teleports a user across the area, which breaks the
  continuity ``r2`` is defined on — the association ``(ρ, δ)`` would change
  for a reason that is not a handover;
* *clamping* piles users along the edge, which biases ``U_{s,v}`` and so
  contaminates the counting-form ``r3`` and P3's ``Σ U²``.

Reflection preserves both the speed and the population density.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError
from .constants import AREA_EW_KM, AREA_NS_KM

USER_SPEED_KMH: float = 30.0
"""**P** — MODQN §IV."""

MAX_TURN_RAD: float = math.pi / 4.0
"""**S** — ASSUME-MODQN-REP-023 bound on the per-slot heading change."""


@dataclass(frozen=True)
class MobilityConfig:
    """Frozen mobility settings.  All **S** except the speed and the area."""

    num_users: int = 100
    speed_kmh: float = USER_SPEED_KMH
    max_turn_rad: float = MAX_TURN_RAD
    area_ew_km: float = AREA_EW_KM
    area_ns_km: float = AREA_NS_KM
    time_step_s: float = 1.0

    def __post_init__(self) -> None:
        if self.num_users < 1:
            raise ValueError("num_users must be >= 1")
        if self.speed_kmh < 0.0:
            raise ValueError("speed must be non-negative")
        if not 0.0 <= self.max_turn_rad <= math.pi:
            raise ValueError("max_turn_rad must lie in [0, pi]")
        if self.area_ew_km <= 0.0 or self.area_ns_km <= 0.0:
            raise ValueError("the service area must have positive extent")

    @property
    def step_km(self) -> float:
        """Distance covered in one slot: 30 km/h for 1 s is 8.33 m."""
        return self.speed_kmh / 3600.0 * self.time_step_s

    @property
    def half_extent_km(self) -> np.ndarray:
        return np.array([self.area_ew_km / 2.0, self.area_ns_km / 2.0])

    def as_dict(self) -> dict[str, object]:
        return {
            "num_users": self.num_users,
            "speed_kmh": self.speed_kmh,
            "max_turn_rad": self.max_turn_rad,
            "area_ew_km": self.area_ew_km,
            "area_ns_km": self.area_ns_km,
            "scatter": "uniform over the 200 x 90 km rectangle (MODQN §IV)",
            "mobility": "random wandering, per-slot turn bounded by max_turn_rad",
            "boundary": "reflection",
            "step_km": self.step_km,
        }


class RandomWanderingUsers:
    """Users scattered uniformly in the service area, wandering and reflecting."""

    def __init__(self, config: MobilityConfig | None = None) -> None:
        self.config = config or MobilityConfig()
        self._xy_km: np.ndarray | None = None
        self._heading_rad: np.ndarray | None = None

    def reset(self, rng: np.random.Generator) -> np.ndarray:
        """Scatter users uniformly over the rectangle and draw headings."""
        half = self.config.half_extent_km
        self._xy_km = rng.uniform(-half, half, size=(self.config.num_users, 2))
        self._heading_rad = rng.uniform(
            0.0, 2.0 * math.pi, size=self.config.num_users
        )
        return self.positions_km

    @property
    def positions_km(self) -> np.ndarray:
        if self._xy_km is None:
            raise MCRLContractError("mobility has not been reset yet")
        return self._xy_km.copy()

    @property
    def headings_rad(self) -> np.ndarray:
        if self._heading_rad is None:
            raise MCRLContractError("mobility has not been reset yet")
        return self._heading_rad.copy()

    def step(self, rng: np.random.Generator) -> np.ndarray:
        """Advance one slot: bounded random turn, then move, then reflect."""
        if self._xy_km is None or self._heading_rad is None:
            raise MCRLContractError("mobility has not been reset yet")
        config = self.config

        turn = rng.uniform(
            -config.max_turn_rad, config.max_turn_rad, size=config.num_users
        )
        heading = (self._heading_rad + turn) % (2.0 * math.pi)
        step = config.step_km
        moved = self._xy_km + step * np.stack(
            [np.cos(heading), np.sin(heading)], axis=1
        )

        self._xy_km, self._heading_rad = _reflect(
            moved, heading, config.half_extent_km
        )
        return self.positions_km


def _reflect(
    xy_km: np.ndarray, heading_rad: np.ndarray, half_extent_km: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Mirror positions back inside the rectangle and flip the heading.

    Flipping the heading as well as the position matters: reflecting only
    the position would leave the user walking straight back out, so they
    would hug the boundary — the density bias that clamping was rejected for.
    """
    position = np.array(xy_km, dtype=np.float64, copy=True)
    heading = np.array(heading_rad, dtype=np.float64, copy=True)

    for axis in (0, 1):
        limit = half_extent_km[axis]
        over = position[:, axis] > limit
        under = position[:, axis] < -limit
        position[over, axis] = 2.0 * limit - position[over, axis]
        position[under, axis] = -2.0 * limit - position[under, axis]
        flipped = over | under
        if not np.any(flipped):
            continue
        if axis == 0:
            # Mirror about the north axis: heading -> pi - heading.
            heading[flipped] = (math.pi - heading[flipped]) % (2.0 * math.pi)
        else:
            # Mirror about the east axis: heading -> -heading.
            heading[flipped] = (-heading[flipped]) % (2.0 * math.pi)

    # A single reflection is enough for any step smaller than the area, which
    # holds by four orders of magnitude here; assert rather than loop.
    if np.any(np.abs(position) > half_extent_km + 1e-9):
        raise MCRLContractError(
            "a user left the service area by more than one reflection; the "
            "step size cannot exceed the area extent"
        )
    return position, heading
