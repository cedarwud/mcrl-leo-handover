"""Deterministic parametric primitive worlds for the V0.25 mechanism map.

This module deliberately stops at :mod:`mcrl.physics_v025.tapes` primitives.
It does not construct an environment, actions, radiation, or outcomes.
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable

import numpy as np

from mcrl.errors import MCRLContractError

from .channel import (
    db_loss_gain,
    free_space_path_gain,
    keyed_fading_gain,
    scintillation_loss_db,
    transmit_gain_linear,
)
from .constants_v025 import (
    D2_HYSTERESIS_KM,
    D2_MEASUREMENT_STEP_S,
    D2_SUBINTERVALS,
    D2_THRESHOLD_KM,
    DECISION_INTERVAL_S,
    MINIMUM_ELEVATION_DEG,
    RX_GAIN_MAX_DBI,
    ZENITH_GASEOUS_LOSS_DB,
)
from .tapes import PrimitiveBoundary, PrimitiveCandidate, UserLayout, digest_payload


EARTH_RADIUS_KM = 6_371.0
ALTITUDE_KM = 550.0
MAP_STEPS = 30
MAP_LAST_BOUNDARY_S = (MAP_STEPS - 1) * DECISION_INTERVAL_S + D2_SUBINTERVALS * D2_MEASUREMENT_STEP_S
_DECLARED_OCCUPANCIES = (1.5, 4.0, 8.0)
_DECLARED_SATELLITE_COUNTS = (2, 4)


def slant_range_km(elevation_deg: float, *, altitude_km: float = ALTITUDE_KM) -> float:
    """Spherical-Earth slant range for a surface observer."""

    elevation = math.radians(float(elevation_deg))
    radius = EARTH_RADIUS_KM
    orbit_radius = radius + float(altitude_km)
    return -radius * math.sin(elevation) + math.sqrt(
        orbit_radius**2 - radius**2 * math.cos(elevation) ** 2
    )


def entry_elevation_deg(
    *, altitude_km: float = ALTITUDE_KM, entry_slant_km: float = D2_THRESHOLD_KM - D2_HYSTERESIS_KM
) -> float:
    """Elevation where an ascending pass enters the D2 hysteresis boundary."""

    radius = EARTH_RADIUS_KM
    orbit_radius = radius + float(altitude_km)
    slant = float(entry_slant_km)
    sine = (orbit_radius**2 - radius**2 - slant**2) / (2.0 * radius * slant)
    return math.degrees(math.asin(max(-1.0, min(1.0, sine))))


class ParametricSyntheticProvider:
    """Primitive-only 550-km drifting-pass provider.

    ``seed`` is experiment key material and is mixed with the tape builder's
    domain-derived ``world_seed``.  This makes three map seeds and the two
    calibration domains disjoint while retaining the stage-2 domain rule.
    """

    def __init__(
        self,
        users_per_beam: float,
        sats_per_user: int,
        coupling_db: float,
        seed: int,
    ) -> None:
        occupancy = float(users_per_beam)
        if occupancy not in _DECLARED_OCCUPANCIES:
            raise MCRLContractError("users_per_beam is outside the declared synthetic grid")
        if sats_per_user not in _DECLARED_SATELLITE_COUNTS:
            raise MCRLContractError("sats_per_user is outside the declared synthetic grid")
        if not math.isfinite(coupling_db) or coupling_db > 0.0:
            raise MCRLContractError("coupling_db must be finite and nonpositive")
        if type(seed) is not int or seed < 0:
            raise MCRLContractError("seed must be a nonnegative exact integer")
        self.users_per_beam = occupancy
        self.sats_per_user = sats_per_user
        self.coupling_db = float(coupling_db)
        self.seed = seed
        # LOW uses two populated chains (2 + 1 users); MID/HIGH use one.
        self.beam_count = 2 if occupancy == 1.5 else 1
        self.user_count = int(round(occupancy * self.beam_count))
        self._norads = tuple(90_001 + index for index in range(sats_per_user))
        self._inventory = tuple(
            (norad, chain) for norad in self._norads for chain in range(self.beam_count)
        )
        self._entry_elevation_deg = entry_elevation_deg()

    @property
    def parameter_digest(self) -> str:
        return digest_payload(
            {
                "altitude_km": ALTITUDE_KM,
                "coupling_db": self.coupling_db,
                "sats_per_user": self.sats_per_user,
                "seed": self.seed,
                "users_per_beam": self.users_per_beam,
            }
        )

    def inventory(self, *, world_seed: int) -> Iterable[tuple[int, int]]:
        del world_seed
        return self._inventory

    def cluster_identity(self, *, world_seed: int) -> tuple[str, int]:
        return ("synthetic-550km", self._mixed_seed(world_seed))

    def user_layout(self, *, world_seed: int) -> Iterable[UserLayout]:
        rng = np.random.default_rng(self._mixed_seed(world_seed))
        rows = []
        for user in range(self.user_count):
            chain = self._chain_for_user(user)
            chain_center = -0.22 if self.beam_count == 2 and chain == 0 else 0.22
            rows.append(
                UserLayout(
                    user,
                    35.0 + chain_center + float(rng.uniform(-0.025, 0.025)),
                    -120.0 + float(rng.uniform(-0.025, 0.025)),
                )
            )
        return tuple(rows)

    def boundary(
        self,
        *,
        world_seed: int,
        step_index: int,
        boundary_index: int,
        absolute_time_s: float,
    ) -> PrimitiveBoundary:
        del step_index, boundary_index
        mixed_seed = self._mixed_seed(world_seed)
        time_ns = int(round(absolute_time_s * 1.0e9))
        cross_ratio = 10.0 ** (self.coupling_db / 10.0)
        rx_peak = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
        rows: list[PrimitiveCandidate] = []
        for user in range(self.user_count):
            chain = self._chain_for_user(user)
            for satellite_index, norad in enumerate(self._norads):
                peak_fraction = self._peak_fraction(satellite_index, mixed_seed)
                elevation = self._elevation(absolute_time_s, peak_fraction)
                slant = slant_range_km(elevation)
                off_axis = self._off_axis_deg(user, satellite_index, mixed_seed)
                deterministic_loss_db = ZENITH_GASEOUS_LOSS_DB + float(
                    scintillation_loss_db(elevation)
                )
                nominal = (
                    float(free_space_path_gain(slant))
                    * float(transmit_gain_linear(off_axis))
                    * rx_peak
                    * float(db_loss_gain(deterministic_loss_db))
                )
                realised = nominal * keyed_fading_gain(
                    world=mixed_seed,
                    # Users on one physical beam are deliberately
                    # exchangeable, enabling an exact occupancy-vector cache.
                    user=chain,
                    norad=norad,
                    absolute_time_ns=time_ns,
                    elevation_deg=elevation,
                )
                nominal_cross = tuple(
                    (aggressor, nominal * cross_ratio) for aggressor in self._norads
                )
                realised_cross = tuple(
                    (aggressor, realised * cross_ratio) for aggressor in self._norads
                )
                descent_crossing_s = self._descending_crossing_s(
                    self._entry_elevation_deg, peak_fraction
                )
                visible = elevation >= MINIMUM_ELEVATION_DEG
                eligible = elevation >= self._entry_elevation_deg
                rows.append(
                    PrimitiveCandidate(
                        user_id=user,
                        identity=(norad, chain),
                        color=0,
                        elevation_deg=elevation,
                        d2_entry_elevation_deg=self._entry_elevation_deg,
                        slant_km=slant,
                        d2_distance_km=slant,
                        visible=visible,
                        d2_eligible=eligible,
                        nominal_gain=nominal,
                        realised_gain=realised,
                        nominal_cross_gain_by_norad=nominal_cross,
                        realised_cross_gain_by_norad=realised_cross,
                        remaining_visibility_s=(
                            max(0.0, MAP_LAST_BOUNDARY_S - absolute_time_s) if visible else 0.0
                        ),
                        remaining_d2_s=(
                            max(0.0, descent_crossing_s - absolute_time_s) if eligible else 0.0
                        ),
                    )
                )
        return PrimitiveBoundary(float(absolute_time_s), tuple(rows))

    def occupancy_by_beam(self, boundary: PrimitiveBoundary) -> dict[tuple[int, int], int]:
        """Visible user census used by provider KATs and map provenance."""

        result: dict[tuple[int, int], int] = {}
        for row in boundary.candidates:
            if row.visible:
                result[row.identity] = result.get(row.identity, 0) + 1
        return result

    def off_axis_deg(self, *, user: int, satellite_index: int, world_seed: int) -> float:
        """Return the deterministic beam-relative angle used in direct gain."""

        return self._off_axis_deg(user, satellite_index, self._mixed_seed(world_seed))

    def _mixed_seed(self, world_seed: int) -> int:
        material = f"V025_SYNTH|{self.seed}|{int(world_seed)}".encode("ascii")
        return int.from_bytes(hashlib.sha256(material).digest()[:8], "big") & ((1 << 63) - 1)

    def _chain_for_user(self, user: int) -> int:
        return user % self.beam_count

    @staticmethod
    def _peak_fraction(satellite_index: int, mixed_seed: int) -> float:
        keyed = (mixed_seed >> (satellite_index * 7 % 49)) & 0x7F
        return 0.46 + 0.08 * (keyed / 127.0)

    @staticmethod
    def _elevation(absolute_time_s: float, peak_fraction: float) -> float:
        if absolute_time_s <= 0.0 or absolute_time_s >= MAP_LAST_BOUNDARY_S:
            return MINIMUM_ELEVATION_DEG
        fraction = absolute_time_s / MAP_LAST_BOUNDARY_S
        if fraction <= peak_fraction:
            progress = fraction / peak_fraction
        else:
            progress = (1.0 - fraction) / (1.0 - peak_fraction)
        return MINIMUM_ELEVATION_DEG + 50.0 * max(0.0, min(1.0, progress))

    def _off_axis_deg(self, user: int, satellite_index: int, mixed_seed: int) -> float:
        # A 550-km footprint displacement of roughly 3--14 km: small relative
        # to slant range and inside the retained 3.32-degree full HPBW.
        keyed = hashlib.sha256(
            f"{mixed_seed}|{self._chain_for_user(user)}|{satellite_index}|off-axis".encode("ascii")
        ).digest()
        return 0.30 + 0.95 * (int.from_bytes(keyed[:2], "big") / 65_535.0)

    @staticmethod
    def _descending_crossing_s(elevation_deg: float, peak_fraction: float) -> float:
        progress = (elevation_deg - MINIMUM_ELEVATION_DEG) / 50.0
        return MAP_LAST_BOUNDARY_S * (1.0 - progress * (1.0 - peak_fraction))


__all__ = [
    "ALTITUDE_KM",
    "EARTH_RADIUS_KM",
    "MAP_LAST_BOUNDARY_S",
    "MAP_STEPS",
    "ParametricSyntheticProvider",
    "entry_elevation_deg",
    "slant_range_km",
]
