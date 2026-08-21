"""Global earth-fixed hexagonal cell lattice (SDD §4A.2).

The beam factor of an action indexes **cells**, not satellites:

    j = 0        the user's anchored cell
    j = 1..6     its six neighbours, in one fixed axial order
    cell_id(j)   depends only on j and the user's anchor — never on l

That orthogonality is what lets ``r2`` distinguish φ1 (same satellite, new
cell) from φ2 (new satellite) at all; see ``action_contract``.

The lattice geometry (axial coordinates, the six canonical directions, the
rectangular crop with a guard ring, the 3-colour reuse map) is carried over
from ``family_b_geometry.py:78-206``.  What changes is the **radius**: it is
``h·tan(θ_3dB/2)`` and ``h`` is no longer a constant, so it becomes an
explicit argument instead of a module-level default.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError
from .constants import (
    AREA_CENTER_LAT_DEG,
    AREA_CENTER_LON_DEG,
    AREA_EW_KM,
    AREA_NS_KM,
)
from .geometry import geodetic_to_ecef, local_km_to_geodetic

AXIAL_NEIGHBOR_DIRS: tuple[tuple[int, int], ...] = (
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
)
"""Fixed six-neighbour axial order (``family_b_geometry.py:78-85``).

SDD §4A.2 requires this order to be **fixed**: ``j`` is meaningless unless
the same ``j`` always names the same direction from the anchor.
"""

THETA_3DB_DEG: float = 3.32
"""**P'** — HOBS full HPBW.  Halved before use (SDD §3.4b, P-2)."""

NUM_NEIGHBORS: int = 6


def cell_radius_km(altitude_km: float, theta_3db_deg: float = THETA_3DB_DEG) -> float:
    """``R_b = h·tan(θ_3dB/2)`` — the HALF-angle convention (P-2)."""
    if altitude_km <= 0.0:
        raise ValueError("altitude must be positive")
    return altitude_km * math.tan(math.radians(theta_3db_deg) / 2.0)


@dataclass(frozen=True)
class CellGrid:
    """Rectangular-cropped axial hex lattice with a guard ring."""

    cell_radius_km: float
    pitch_km: float
    axial: np.ndarray
    """``(C, 2)`` axial (q, r) coordinates."""
    centers_km: np.ndarray
    """``(C, 2)`` local east/north km from the service-area centre."""
    centers_ecef_km: np.ndarray
    """``(C, 3)`` ECEF km — the global earth-fixed positions of §4A.2."""
    colors: np.ndarray
    in_area: np.ndarray
    serves_area: np.ndarray
    neighbor_ids: np.ndarray
    """``(C, 6)`` neighbour cell ids in ``AXIAL_NEIGHBOR_DIRS`` order, -1 if absent."""

    @property
    def count(self) -> int:
        return int(self.axial.shape[0])

    def centers_latlon(self) -> tuple[np.ndarray, np.ndarray]:
        return local_km_to_geodetic(
            self.centers_km[:, 0],
            self.centers_km[:, 1],
            center_lat_deg=AREA_CENTER_LAT_DEG,
            center_lon_deg=AREA_CENTER_LON_DEG,
        )

    def anchor_cell_ids(self, user_xy_km: np.ndarray) -> np.ndarray:
        """Nearest cell centre per user, in local-km Euclidean distance."""
        points = np.atleast_2d(np.asarray(user_xy_km, dtype=np.float64))
        if points.shape[-1] != 2:
            raise ValueError("user_xy_km must have shape (U, 2)")
        squared = (
            (points[:, None, :] - self.centers_km[None, :, :]) ** 2
        ).sum(axis=2)
        return squared.argmin(axis=1).astype(np.int64)

    def neighborhood_cell_ids(self, anchor_ids: np.ndarray) -> np.ndarray:
        """``(U, 7)``: the anchor followed by its six canonical neighbours.

        Column ``j`` is exactly the beam slot ``j`` of SDD §4A.2.  A missing
        neighbour (edge of the lattice) stays ``-1`` and the mask must
        exclude it — it is never silently replaced.
        """
        anchors = np.asarray(anchor_ids, dtype=np.int64)
        if anchors.ndim != 1:
            raise ValueError("anchor_ids must be one-dimensional")
        if np.any(anchors < 0) or np.any(anchors >= self.count):
            raise MCRLContractError("anchor cell id out of range")
        return np.concatenate(
            [anchors[:, None], self.neighbor_ids[anchors]], axis=1
        )


def _axial_to_local_km(q: np.ndarray, r: np.ndarray, radius_km: float) -> np.ndarray:
    x = radius_km * math.sqrt(3.0) * (q + r / 2.0)
    y = radius_km * 1.5 * r
    return np.stack([x, y], axis=1)


def build_cell_grid(
    *,
    altitude_km: float | None = None,
    cell_radius_km_override: float | None = None,
    guard_rings: int = 1,
) -> CellGrid:
    """Build the pointing lattice for one altitude.

    Exactly one of ``altitude_km`` / ``cell_radius_km_override`` is required;
    the altitude form is preferred so the dependence stays visible.
    """
    if (altitude_km is None) == (cell_radius_km_override is None):
        raise ValueError(
            "pass exactly one of altitude_km or cell_radius_km_override"
        )
    radius = (
        float(cell_radius_km_override)
        if cell_radius_km_override is not None
        else cell_radius_km(float(altitude_km))
    )
    if guard_rings < 0:
        raise ValueError("guard_rings must be >= 0")

    pitch = math.sqrt(3.0) * radius
    guard_km = guard_rings * pitch + radius
    half_ew = AREA_EW_KM / 2.0 + guard_km
    half_ns = AREA_NS_KM / 2.0 + guard_km

    q_span = (
        int(math.ceil(half_ew / (radius * math.sqrt(3.0))))
        + int(math.ceil(half_ns / (radius * 1.5)))
        + 2
    )
    r_span = int(math.ceil(half_ns / (radius * 1.5))) + 2

    qq, rr = np.meshgrid(
        np.arange(-q_span, q_span + 1), np.arange(-r_span, r_span + 1)
    )
    q, r = qq.ravel(), rr.ravel()
    xy = _axial_to_local_km(q, r, radius)
    keep = (np.abs(xy[:, 0]) <= half_ew) & (np.abs(xy[:, 1]) <= half_ns)
    q, r, xy = q[keep], r[keep], xy[keep]

    in_area = (np.abs(xy[:, 0]) <= AREA_EW_KM / 2.0) & (
        np.abs(xy[:, 1]) <= AREA_NS_KM / 2.0
    )
    dx = np.maximum(np.abs(xy[:, 0]) - AREA_EW_KM / 2.0, 0.0)
    dy = np.maximum(np.abs(xy[:, 1]) - AREA_NS_KM / 2.0, 0.0)
    serves = np.hypot(dx, dy) <= radius + 1e-9

    key = {
        (int(qi), int(ri)): index for index, (qi, ri) in enumerate(zip(q, r))
    }
    neighbor_ids = np.full((xy.shape[0], NUM_NEIGHBORS), -1, dtype=np.int64)
    for index in range(xy.shape[0]):
        for direction, (dq, dr) in enumerate(AXIAL_NEIGHBOR_DIRS):
            neighbor_ids[index, direction] = key.get(
                (int(q[index]) + dq, int(r[index]) + dr), -1
            )

    missing = serves & (neighbor_ids == -1).any(axis=1)
    if missing.any():
        raise MCRLContractError(
            f"{int(missing.sum())} area-serving cells lack a full "
            f"6-neighbourhood; increase guard_rings (= {guard_rings})"
        )

    lat, lon = local_km_to_geodetic(
        xy[:, 0],
        xy[:, 1],
        center_lat_deg=AREA_CENTER_LAT_DEG,
        center_lon_deg=AREA_CENTER_LON_DEG,
    )
    return CellGrid(
        cell_radius_km=radius,
        pitch_km=pitch,
        axial=np.stack([q, r], axis=1).astype(np.int64),
        centers_km=xy,
        centers_ecef_km=geodetic_to_ecef(lat, lon),
        colors=((q - r) % 3).astype(np.int64),
        in_area=in_area,
        serves_area=serves,
        neighbor_ids=neighbor_ids,
    )


def service_area_sample(
    *, east_points: int = 401, north_points: int = 181
) -> np.ndarray:
    """Dense local-km sample of the 200 × 90 km service area."""
    east = np.linspace(-AREA_EW_KM / 2.0, AREA_EW_KM / 2.0, east_points)
    north = np.linspace(-AREA_NS_KM / 2.0, AREA_NS_KM / 2.0, north_points)
    grid_e, grid_n = np.meshgrid(east, north)
    return np.stack([grid_e.ravel(), grid_n.ravel()], axis=1)


def coverage_fraction(
    grid: CellGrid,
    cell_ids: np.ndarray,
    *,
    samples: np.ndarray | None = None,
) -> float:
    """Fraction of the service area inside the 3 dB footprint of some cell.

    "Covered" means within ``R_b`` of a selected cell centre — the same
    3 dB contour the cell radius is defined by.
    """
    points = service_area_sample() if samples is None else np.asarray(samples)
    centers = grid.centers_km[np.asarray(cell_ids, dtype=np.int64)]
    if centers.size == 0:
        return 0.0
    distance = np.linalg.norm(points[:, None, :] - centers[None, :, :], axis=2)
    return float(np.mean(distance.min(axis=1) <= grid.cell_radius_km))


def greedy_coverage_order(
    grid: CellGrid,
    *,
    max_cells: int | None = None,
    samples: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Greedy max-coverage cell ordering and the coverage it achieves.

    Returns ``(cell_ids, coverage_after_each)``.  This is how "how many
    pointing cells does 95% coverage need?" gets answered by measurement
    rather than by the area-ratio heuristic, which ignores edge overhang and
    under-counts by roughly 15%.
    """
    points = service_area_sample() if samples is None else np.asarray(samples)
    distance = np.linalg.norm(
        points[:, None, :] - grid.centers_km[None, :, :], axis=2
    )
    covers = distance <= grid.cell_radius_km

    limit = grid.count if max_cells is None else min(max_cells, grid.count)
    uncovered = np.ones(points.shape[0], dtype=bool)
    available = np.ones(grid.count, dtype=bool)
    chosen: list[int] = []
    curve: list[float] = []
    for _ in range(limit):
        gain = covers[uncovered].sum(axis=0) * available
        best = int(gain.argmax())
        if gain[best] == 0:
            break
        chosen.append(best)
        available[best] = False
        uncovered &= ~covers[:, best]
        curve.append(1.0 - float(uncovered.mean()))
    return np.array(chosen, dtype=np.int64), np.array(curve, dtype=np.float64)
