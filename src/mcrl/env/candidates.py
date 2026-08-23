"""Per-step candidate assembly: slots, cells, geometry and mask (§4A).

This is everything the environment computes **before** any physics: which
four satellites occupy a user's slots, which seven cells their beam slots
name, the off-axis angle of each of the 28 candidates, and which of them are
selectable.  It stops exactly where the power model begins, because that is
still open (``docs/CONTROLLER-QUESTIONS-2026-08-22.md``).

**Windows are per user.**  The paper writes the candidate map as
``b_u(c,t)`` — with a ``u`` subscript — and §4A.3 ranks slots by D2 margin,
which is a per-user distance.  Two users 100 km apart across the service
area can therefore order the same satellites differently, and a shared
window would silently give some of them somebody else's four.

**Mask (§4A.5).**  Three geometric terms are determined and applied here::

    mask[a] = slot l occupied         (D2 eligibility, W-04)
            ∧ cell j exists           (the lattice has that neighbour)
            ∧ cell j sees satellite l (geometric visibility)

The fourth term §4A.5 names — link feasibility — depends on the power model
and is **not** applied yet.  It can only narrow the mask, so what is built
here is an upper bound on the true candidate set, and that is stated rather
than left for a reader to discover.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError
from .action_contract import (
    CONTRACT_STATE_DIM,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
    SlotAssignment,
    SlotTable,
    assign_satellite_slots,
    build_slot_table,
    contract_state_fields,
    normalise_candidates,
)
from .cells import CellGrid
from .d2 import D2Snapshot, D2Tracker
from .dwell import DwellController, DwellSnapshot
from .pointing import candidate_geometry

CELL_VISIBILITY_MIN_ELEVATION_DEG: float = 0.0
"""**S** — a cell may be pointed at while the satellite is above its horizon.

Pure geometric visibility.  A stricter limit — an off-nadir pointing bound
such as ITU-R S.1528's 60°, say — would be a modelling decision that neither
the paper nor the SDD states, so none is imposed here.
"""


@dataclass(frozen=True)
class StepCandidates:
    """One step's candidate table for every user."""

    slot_tables: tuple[SlotTable, ...]
    assignments: tuple[SlotAssignment, ...]
    off_axis_deg: np.ndarray
    """``(U, L, J)`` — eq. (3.6); NaN where the beam slot has no cell."""
    slant_range_km: np.ndarray
    """``(U, L)`` — eq. (3.5)."""
    elevation_deg: np.ndarray
    """``(U, L)``."""
    window_satellite_ecef_km: np.ndarray
    """``(U, L, 3)``; NaN rows where a slot is unoccupied."""
    window_norad_ids: np.ndarray
    """``(U, L)`` int64; ``-1`` where a slot is unoccupied."""
    contract_fields: np.ndarray
    """``(U, 13)`` — §4A.6's block, ready for the state encoder."""
    slot_occupied: np.ndarray
    """``(U, L)`` — §4A.5 term 1: does a D2-eligible satellite hold the slot?"""
    cell_exists: np.ndarray
    """``(U, J)`` — term 2: does the lattice have that neighbour?"""
    cell_reachable: np.ndarray
    """``(U, L, J)`` — term 3: is the cell above satellite ``l``'s horizon?

    The three terms are kept apart because ``mask`` is their AND and an AND
    cannot be attributed: probe P7 has to report which term contracts the
    action set, and "28/28 valid" says nothing about which of the three was
    responsible for the zero attrition.
    """
    dwell: DwellSnapshot
    d2: D2Snapshot

    @property
    def masks(self) -> np.ndarray:
        """``(U, 28)`` boolean."""
        return np.stack([table.mask for table in self.slot_tables])

    @property
    def num_valid(self) -> np.ndarray:
        return self.masks.sum(axis=1)

    @property
    def starved_users(self) -> np.ndarray:
        """Users with an empty mask — §4A.5a's no-op population."""
        return self.num_valid == 0


def resolve_candidates(
    *,
    step_index: int,
    user_xy_km: np.ndarray,
    user_ecef_km: np.ndarray,
    tracked_satellite_ecef_km: np.ndarray,
    grid: CellGrid,
    dwell: DwellController,
    d2_snapshot: D2Snapshot,
    dwell_snapshot: DwellSnapshot,
    incumbent_norads: np.ndarray,
    min_cell_elevation_deg: float = CELL_VISIBILITY_MIN_ELEVATION_DEG,
) -> StepCandidates:
    """Assemble the candidate table from an already-updated D2 and dwell state.

    The D2 and dwell updates are taken as arguments rather than performed
    here so their step ordering stays visible at the call site: D2 must be
    primed before step 0 (W-04), and dwell re-keys only on its boundaries
    (W-05).
    """
    users = np.asarray(user_ecef_km, dtype=np.float64)
    positions = np.asarray(user_xy_km, dtype=np.float64)
    tracked = np.asarray(tracked_satellite_ecef_km, dtype=np.float64)
    incumbents = np.asarray(incumbent_norads, dtype=np.int64)

    num_users = users.shape[0]
    if users.ndim != 2 or users.shape[1] != 3:
        raise MCRLContractError("user_ecef_km must be (U, 3)")
    if positions.shape != (num_users, 2):
        raise MCRLContractError("user_xy_km must be (U, 2)")
    if tracked.ndim != 2 or tracked.shape[1] != 3:
        raise MCRLContractError("tracked_satellite_ecef_km must be (S, 3)")
    if tracked.shape[0] != d2_snapshot.norad_ids.size:
        raise MCRLContractError(
            "tracked satellites and the D2 snapshot disagree on S"
        )
    if incumbents.shape != (num_users,):
        raise MCRLContractError("incumbent_norads must be (U,)")
    if dwell_snapshot.neighborhood_cell_ids.shape != (num_users, NUM_BEAM_SLOTS):
        raise MCRLContractError("the dwell snapshot is for a different population")
    del step_index, dwell  # kept in the signature so the ordering reads at the call site

    column_of = {
        int(norad): index
        for index, norad in enumerate(d2_snapshot.norad_ids.tolist())
    }

    assignments: list[SlotAssignment] = []
    window_ecef = np.full(
        (num_users, NUM_SATELLITE_SLOTS, 3), np.nan, dtype=np.float64
    )
    window_norads = np.full(
        (num_users, NUM_SATELLITE_SLOTS), -1, dtype=np.int64
    )
    for uid in range(num_users):
        incumbent = int(incumbents[uid])
        assignment = assign_satellite_slots(
            normalise_candidates(d2_snapshot.candidates_for_user(uid)),
            incumbent_norad=None if incumbent < 0 else incumbent,
        )
        assignments.append(assignment)
        for slot in range(NUM_SATELLITE_SLOTS):
            if not assignment.occupied[slot]:
                continue
            norad = int(assignment.norad_ids[slot])
            window_norads[uid, slot] = norad
            window_ecef[uid, slot] = tracked[column_of[norad]]

    # Geometry needs a finite position in every slot; unoccupied slots are
    # masked out below, so any placeholder works — but it must not be NaN,
    # which would poison the arccos for the occupied slots' broadcast.
    geometry_input = np.where(
        np.isnan(window_ecef), tracked[0][None, None, :], window_ecef
    )
    geometry = candidate_geometry(
        user_ecef_km=users,
        satellite_ecef_km=geometry_input,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=dwell_snapshot.neighborhood_cell_ids,
    )

    reachable = _cell_visibility(
        grid=grid,
        neighborhood_cell_ids=dwell_snapshot.neighborhood_cell_ids,
        window_satellite_ecef_km=window_ecef,
        min_elevation_deg=min_cell_elevation_deg,
    )

    slot_tables = tuple(
        build_slot_table(
            assignments[uid],
            dwell_snapshot.neighborhood_cell_ids[uid],
            cell_reachable=reachable[uid],
        )
        for uid in range(num_users)
    )
    contract = np.stack(
        [
            contract_state_fields(assignments[uid], dwell_phase=dwell_snapshot.phase)
            for uid in range(num_users)
        ]
    )
    if contract.shape != (num_users, CONTRACT_STATE_DIM):
        raise MCRLContractError("contract block has the wrong shape")

    return StepCandidates(
        slot_tables=slot_tables,
        assignments=tuple(assignments),
        off_axis_deg=np.where(
            window_norads[:, :, None] >= 0, geometry.off_axis_deg, np.nan
        ),
        slant_range_km=np.where(
            window_norads >= 0, geometry.slant_range_km, np.nan
        ),
        elevation_deg=np.where(
            window_norads >= 0, geometry.elevation_deg, np.nan
        ),
        window_satellite_ecef_km=window_ecef,
        window_norad_ids=window_norads,
        contract_fields=contract.astype(np.float32),
        slot_occupied=np.stack(
            [assignment.occupancy for assignment in assignments]
        ),
        cell_exists=dwell_snapshot.neighborhood_cell_ids >= 0,
        cell_reachable=reachable,
        dwell=dwell_snapshot,
        d2=d2_snapshot,
    )


def _cell_visibility(
    *,
    grid: CellGrid,
    neighborhood_cell_ids: np.ndarray,
    window_satellite_ecef_km: np.ndarray,
    min_elevation_deg: float,
) -> np.ndarray:
    """``(U, L, J)`` — is cell ``j`` above the horizon from satellite ``l``?

    Elevation is evaluated **at the cell**, not at the user: a beam points
    at the cell, so the cell is what has to see the satellite.
    """
    cells = np.asarray(neighborhood_cell_ids, dtype=np.int64)
    present = cells >= 0
    centres = grid.centers_ecef_km[np.where(present, cells, 0)]  # (U, J, 3)

    satellites = window_satellite_ecef_km  # (U, L, 3)
    delta = satellites[:, :, None, :] - centres[:, None, :, :]  # (U, L, J, 3)
    distance = np.linalg.norm(delta, axis=-1)
    up = centres / np.maximum(
        np.linalg.norm(centres, axis=-1, keepdims=True), 1e-12
    )
    sine = np.sum(delta * up[:, None, :, :], axis=-1) / np.maximum(distance, 1e-12)
    elevation = np.degrees(np.arcsin(np.clip(sine, -1.0, 1.0)))

    visible = elevation >= min_elevation_deg
    visible &= present[:, None, :]
    return np.where(np.isnan(elevation), False, visible)
