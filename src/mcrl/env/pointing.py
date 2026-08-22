"""Beam-pointing geometry: off-axis angle and slant range (§3.1.2).

Paper equations, verbatim:

    (3.5)  d_{u,s,v}(t) = sqrt(R_E² sin²α + h_s² + 2 R_E h_s) − R_E sin α
    (3.6)  θ_{u,s,v}(t) = arccos( v_{s,v}·r_{u,s} / (|v_{s,v}| |r_{u,s}|) )

``v_{s,v}`` is the beam-centre direction and ``r_{u,s}`` the
satellite-to-user direction, so ``θ`` is the angle **at the satellite**
between where the beam points and where the user is.  Since a beam points
at an earth-fixed cell (§4A.2), the boresight is simply
``cell_centre − satellite``.

Two properties the paper states explicitly and that this module preserves:

* ``d`` carries no beam index in practice — "對同一顆衛星的不同波束,它的
  數值可以相同" — because the slant range is a property of the (user,
  satellite) pair.  The three-subscript name is kept for the link-layer
  bookkeeping, but nothing here makes it depend on ``v``.
* ``θ`` is where the geometry enters energy efficiency.  It is the **only**
  route by which the angle reaches the reward: it feeds ``G^T(θ)``, and
  through that the SINR and the rate.

⚠ Both are returned in the units the downstream layer expects: ``θ`` in
**degrees**, because the S.465 receive envelope and ``mu_of`` are defined on
degrees, and passing radians there inflates gain by ~44 dB (G-7).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError
from .constants import R_E_KM
from .geometry import angle_between_deg


def slant_range_from_elevation_km(
    elevation_deg: np.ndarray, altitude_km: np.ndarray
) -> np.ndarray:
    """Paper eq. (3.5), elementwise.

    Algebraically identical to ``d = |r_sat − r_user|`` on the spherical
    Earth; kept in the paper's closed form so the implementation can be read
    straight off the manuscript.  ``tests`` check the two against each other.
    """
    elevation = np.asarray(elevation_deg, dtype=np.float64)
    altitude = np.asarray(altitude_km, dtype=np.float64)
    if np.any(altitude <= 0.0):
        raise MCRLContractError("altitude must be positive")
    sin_elevation = np.sin(np.radians(elevation))
    return (
        np.sqrt(
            (R_E_KM * sin_elevation) ** 2 + altitude**2 + 2.0 * R_E_KM * altitude
        )
        - R_E_KM * sin_elevation
    )


def off_axis_angle_deg(
    satellite_ecef_km: np.ndarray,
    beam_centre_ecef_km: np.ndarray,
    user_ecef_km: np.ndarray,
) -> np.ndarray:
    """Paper eq. (3.6): the angle at the satellite, in **degrees**.

    All three arguments broadcast against each other on their leading axes.
    """
    return angle_between_deg(
        satellite_ecef_km, beam_centre_ecef_km, user_ecef_km
    )


@dataclass(frozen=True)
class CandidateGeometry:
    """Per (user, satellite slot, beam slot) geometry for one step."""

    off_axis_deg: np.ndarray
    """``(U, L, J)`` — eq. (3.6), the angle that carries EE."""

    slant_range_km: np.ndarray
    """``(U, L)`` — eq. (3.5).  No beam index: it is a (user, satellite) property."""

    elevation_deg: np.ndarray
    """``(U, L)`` — used by the atmospheric term and by D2 disclosure."""

    cell_ids: np.ndarray
    """``(U, J)`` — which physical cell each beam slot names (§4A.2)."""

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.off_axis_deg.shape


def candidate_geometry(
    *,
    user_ecef_km: np.ndarray,
    satellite_ecef_km: np.ndarray,
    cell_centres_ecef_km: np.ndarray,
    neighborhood_cell_ids: np.ndarray,
) -> CandidateGeometry:
    """Assemble the ``(U, L, J)`` candidate geometry for one step.

    ``satellite_ecef_km`` is ``(U, L, 3)`` — **each user has their own window**.
    The paper's candidate map is written ``b_u(c,t)`` with a ``u`` subscript
    for exactly this reason: slot assignment ranks by D2 margin (§4A.3), and
    margin is a per-user distance, so two users 100 km apart can order the
    same satellites differently.  A shared ``(L, 3)`` is accepted and
    broadcast, but only as a convenience for tests.

    ``neighborhood_cell_ids`` is ``(U, J)`` from
    ``CellGrid.neighborhood_cell_ids``; ``-1`` marks a beam slot with no
    lattice cell, and its angle comes back as NaN so that a caller which
    forgets to mask it fails loudly rather than pointing at cell 0.
    """
    users = np.asarray(user_ecef_km, dtype=np.float64)
    satellites = np.asarray(satellite_ecef_km, dtype=np.float64)
    centres = np.asarray(cell_centres_ecef_km, dtype=np.float64)
    cells = np.asarray(neighborhood_cell_ids, dtype=np.int64)

    if users.ndim != 2 or users.shape[1] != 3:
        raise MCRLContractError("user_ecef_km must be (U, 3)")
    if satellites.ndim == 2 and satellites.shape[1] == 3:
        satellites = np.broadcast_to(
            satellites[None, :, :], (users.shape[0],) + satellites.shape
        )
    if satellites.ndim != 3 or satellites.shape[2] != 3:
        raise MCRLContractError("satellite_ecef_km must be (U, L, 3) or (L, 3)")
    if satellites.shape[0] != users.shape[0]:
        raise MCRLContractError("satellite_ecef_km and user_ecef_km disagree on U")
    if centres.ndim != 2 or centres.shape[1] != 3:
        raise MCRLContractError("cell_centres_ecef_km must be (C, 3)")
    if cells.ndim != 2 or cells.shape[0] != users.shape[0]:
        raise MCRLContractError("neighborhood_cell_ids must be (U, J)")
    if np.any(cells >= centres.shape[0]):
        raise MCRLContractError("a cell id exceeds the lattice")

    num_users, num_slots, num_beams = users.shape[0], satellites.shape[1], cells.shape[1]

    # (U, L): slant range and elevation, independent of the beam index.
    delta = satellites - users[:, None, :]
    slant = np.linalg.norm(delta, axis=-1)
    up = users / np.maximum(
        np.linalg.norm(users, axis=1, keepdims=True), 1e-12
    )
    sin_elevation = np.sum(delta * up[:, None, :], axis=-1) / np.maximum(slant, 1e-12)
    elevation = np.degrees(np.arcsin(np.clip(sin_elevation, -1.0, 1.0)))

    # (U, L, J): the off-axis angle of every candidate beam.
    present = cells >= 0
    safe_cells = np.where(present, cells, 0)
    # (U, J, 3) -> broadcast against (1, L, 1, 3)
    beam_centres = centres[safe_cells]
    off_axis = np.full((num_users, num_slots, num_beams), np.nan, dtype=np.float64)
    for slot in range(num_slots):
        angles = angle_between_deg(
            satellites[:, slot, :][:, None, :],
            beam_centres,
            users[:, None, :],
        )
        off_axis[:, slot, :] = np.where(present, angles, np.nan)

    return CandidateGeometry(
        off_axis_deg=off_axis,
        slant_range_km=slant,
        elevation_deg=elevation,
        cell_ids=cells,
    )


def beam_off_axis_deg(
    *,
    user_ecef_km: np.ndarray,
    satellite_ecef_km: np.ndarray,
    beam_centre_ecef_km: np.ndarray,
) -> np.ndarray:
    """``(U, B)`` off-axis angles for an explicit list of radiating beams.

    This is the interference-side companion to :func:`candidate_geometry`:
    eq. (3.12a)/(3.12b) evaluate every *active* beam's own ``θ`` toward the
    victim user, not the victim's candidate angles.  "每一項都以該干擾波束
    自己的偏軸角與線性鏈路因子計算".
    """
    users = np.asarray(user_ecef_km, dtype=np.float64)
    satellites = np.asarray(satellite_ecef_km, dtype=np.float64)
    centres = np.asarray(beam_centre_ecef_km, dtype=np.float64)
    if satellites.shape != centres.shape:
        raise MCRLContractError(
            "satellite_ecef_km and beam_centre_ecef_km must both be (B, 3)"
        )
    if users.ndim != 2 or users.shape[1] != 3:
        raise MCRLContractError("user_ecef_km must be (U, 3)")
    return angle_between_deg(
        satellites[None, :, :], centres[None, :, :], users[:, None, :]
    )
