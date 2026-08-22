"""Co-channel interference (3.12a)/(3.12b) and the unique link SINR (3.13).

This is the seam the whole physics chain was waiting on.  Everything else —
geometry, gains, path loss, the recurrence power, the load accounting — was
already in place and independently tested; what was missing is the pair of
sums that turn a set of radiating beams into one number per victim link.

**Three properties of (3.12a)/(3.12b) that are easy to get wrong.**

*Gated by ``z``, weighted by nothing.*  The paper is explicit: "求和以啟用
指示 ``z`` 為門檻,而不是以其上載有幾位使用者為權重".  A beam serving eight
users interferes exactly as hard as a beam serving one, because it radiates
one power either way.  Weighting by load would make interference track
congestion and quietly turn ``r3`` into a second SINR term.

*Every term uses the interfering beam's own angle.*  "每一項都以該干擾波束
自己的偏軸角與線性鏈路因子計算" — ``G^T(θ_{u,s',v'})`` is the angle at the
**interferer** between where *it* points and where the victim is, not the
victim's own off-axis angle and not the angle between the two beams.

*The inner sum of (3.12b) has no ``v' ≠ v``.*  Only (3.12a) excludes the
wanted beam, because only there is it in the sum's range at all.  Two
different satellites pointing at the **same cell** on the same colour is a
legal, and in fact the worst, interference case — dropping it because the
cell index matches would delete the dominant term.

**Scope: global, not the four-slot window.**  (3.12b) sums over
``s' ∈ 𝒮, s' ≠ s``.  The candidate window is a *representation* device for a
fixed-width network output (§4.1); it has no physical meaning, and an
interferer does not stop radiating because it fell out of some user's table.

**Where the colour comes from.**  ``c_{s,v} = (q − r) mod 3`` on the cell's
axial coordinates, so the colour is a property of the **cell**, not of the
satellite.  Two satellites illuminating one cell therefore always share a
colour — see above.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError
from .antenna import (
    apply_same_satellite_override,
    receive_gain_linear,
    transmit_gain_linear,
)
from .cells import CellGrid
from .geometry import angle_between_deg, look_angles
from .link_budget import link_power_factor
from .pointing import beam_off_axis_deg


@dataclass(frozen=True)
class RadiatingBeams:
    """The step's active beam set — ``z_{s,v}(t) = 1{U_{s,v}(t) > 0}`` made concrete.

    Membership *is* the ``z`` gate: a beam is in this table iff it serves at
    least one user, so the sums below need no separate activation factor.
    Derived, never chosen (ruling 2026-08-22 §7.4).
    """

    norad_ids: np.ndarray
    """``(B,)`` — which satellite radiates each beam."""
    cell_ids: np.ndarray
    """``(B,)`` — which earth-fixed cell it points at."""
    satellite_ecef_km: np.ndarray
    """``(B, 3)``."""
    cell_centre_ecef_km: np.ndarray
    """``(B, 3)`` — the beam boresight target."""
    colors: np.ndarray
    """``(B,)`` ∈ {0,1,2} — ``(q − r) mod 3`` of the cell."""
    power_w: np.ndarray
    """``(B,)`` — ``p_{s,v}(t) = max_{u served} p_{u,s,v}(t)``."""

    def __post_init__(self) -> None:
        count = self.norad_ids.shape[0]
        for name, shape in (
            ("cell_ids", (count,)),
            ("satellite_ecef_km", (count, 3)),
            ("cell_centre_ecef_km", (count, 3)),
            ("colors", (count,)),
            ("power_w", (count,)),
        ):
            array = getattr(self, name)
            if array.shape != shape:
                raise MCRLContractError(
                    f"RadiatingBeams.{name} must have shape {shape}, "
                    f"got {array.shape}"
                )
        if np.any(self.power_w < 0.0):
            raise MCRLContractError("beam powers must be non-negative")
        pairs = list(zip(self.norad_ids.tolist(), self.cell_ids.tolist()))
        if len(set(pairs)) != len(pairs):
            raise MCRLContractError(
                "a (satellite, cell) pair appears twice in the radiating set; "
                "one beam radiates one power (3.12a preamble)"
            )

    @property
    def count(self) -> int:
        return int(self.norad_ids.shape[0])


def empty_radiating_beams() -> RadiatingBeams:
    """The all-dark set.  ``I = 0`` everywhere, which is a value, not a gap."""
    return RadiatingBeams(
        norad_ids=np.zeros(0, dtype=np.int64),
        cell_ids=np.zeros(0, dtype=np.int64),
        satellite_ecef_km=np.zeros((0, 3), dtype=np.float64),
        cell_centre_ecef_km=np.zeros((0, 3), dtype=np.float64),
        colors=np.zeros(0, dtype=np.int64),
        power_w=np.zeros(0, dtype=np.float64),
    )


def build_radiating_beams(
    *,
    beam_norad_ids: np.ndarray,
    beam_cell_ids: np.ndarray,
    beam_power_w: np.ndarray,
    satellite_ecef_by_norad: dict[int, np.ndarray],
    grid: CellGrid,
) -> RadiatingBeams:
    """Assemble the active set from the served (satellite, cell) pairs."""
    norads = np.asarray(beam_norad_ids, dtype=np.int64)
    cells = np.asarray(beam_cell_ids, dtype=np.int64)
    power = np.asarray(beam_power_w, dtype=np.float64)
    if not norads.shape == cells.shape == power.shape:
        raise MCRLContractError(
            "beam norad ids, cell ids and powers must share a shape"
        )
    if norads.size == 0:
        return empty_radiating_beams()
    missing = sorted({int(n) for n in norads.tolist()} - set(satellite_ecef_by_norad))
    if missing:
        raise MCRLContractError(
            f"no position for radiating satellites {missing}; the interference "
            "sum is global and cannot silently drop a term"
        )
    return RadiatingBeams(
        norad_ids=norads,
        cell_ids=cells,
        satellite_ecef_km=np.stack(
            [np.asarray(satellite_ecef_by_norad[int(n)]) for n in norads.tolist()]
        ),
        cell_centre_ecef_km=grid.centers_ecef_km[cells],
        colors=grid.colors[cells],
        power_w=power,
    )


# ---------------------------------------------------------------------------
# The per-beam radiated term, p·G^T·H
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BeamFieldAtUsers:
    """Everything about the radiating set that a victim user needs.

    Split out from the sums because the same quantities serve both the
    realised link SINR and the state's per-candidate SINR — computing them
    twice is how the two would drift apart.
    """

    transmit_gain: np.ndarray
    """``(U, B)`` — ``G^T(θ_{u,s',v'})``, the interferer's own off-axis gain."""
    path_gain: np.ndarray
    """``(U, B)`` — ``10^(−L_{u,s'}/10)``, free space plus atmosphere."""
    fading_gain: np.ndarray
    """``(U, B)`` — the Rician draw for the ``(u, s')`` path."""
    off_axis_deg: np.ndarray
    """``(U, B)`` — kept for disclosure; it is what routes ``μ`` to Miller."""

    @property
    def shape(self) -> tuple[int, int]:
        return self.transmit_gain.shape


def beam_field_at_users(
    *,
    user_ecef_km: np.ndarray,
    radiating: RadiatingBeams,
    fading_by_norad: dict[int, np.ndarray] | None = None,
) -> BeamFieldAtUsers:
    """Evaluate every radiating beam at every user, except for ``G^R``.

    ``G^R`` is deliberately excluded: it depends on where the *terminal* is
    pointed, which differs between the realised link and each hypothetical
    candidate, whereas everything here depends only on the (user, beam) pair
    and can be computed once.

    ``fading_by_norad`` maps a NORAD id to a ``(U,)`` Rician power gain.  It
    is keyed by satellite rather than by beam on purpose: small-scale fading
    is a property of the propagation path, and every beam of one satellite
    reaches a given user over the same path.  Drawing per beam would let the
    wanted link and its own co-satellite interferers fade independently,
    which is not a channel — it is noise added to the SINR.
    """
    users = np.asarray(user_ecef_km, dtype=np.float64)
    if users.ndim != 2 or users.shape[1] != 3:
        raise MCRLContractError("user_ecef_km must be (U, 3)")
    num_users = users.shape[0]
    count = radiating.count

    if count == 0:
        empty = np.zeros((num_users, 0), dtype=np.float64)
        return BeamFieldAtUsers(empty, empty, empty, empty)

    off_axis = beam_off_axis_deg(
        user_ecef_km=users,
        satellite_ecef_km=radiating.satellite_ecef_km,
        beam_centre_ecef_km=radiating.cell_centre_ecef_km,
    )
    transmit = transmit_gain_linear(off_axis)

    slant, elevation, _ = look_angles(
        radiating.satellite_ecef_km[None, :, :], users[:, None, :]
    )
    # ``link_power_factor`` folds in G^R; here it must not, so the receive
    # gain is passed as unity and applied by the caller.
    path = link_power_factor(slant, elevation, np.ones_like(slant))

    if fading_by_norad is None:
        fading = np.ones((num_users, count), dtype=np.float64)
    else:
        columns = []
        for norad in radiating.norad_ids.tolist():
            if int(norad) not in fading_by_norad:
                raise MCRLContractError(
                    f"no fading draw for radiating satellite {int(norad)}"
                )
            column = np.asarray(fading_by_norad[int(norad)], dtype=np.float64)
            if column.shape != (num_users,):
                raise MCRLContractError("each fading column must be (U,)")
            columns.append(column)
        fading = np.stack(columns, axis=1)

    return BeamFieldAtUsers(
        transmit_gain=transmit,
        path_gain=path,
        fading_gain=fading,
        off_axis_deg=off_axis,
    )


def received_power_terms(
    field: BeamFieldAtUsers,
    radiating: RadiatingBeams,
    *,
    user_ecef_km: np.ndarray,
    boresight_satellite_ecef_km: np.ndarray,
    boresight_norad_ids: np.ndarray,
) -> np.ndarray:
    """``(U, B)`` of ``p_{s',v'}·G^T(θ_{u,s',v'})·H_{u,s',v'}``.

    ``boresight_*`` is where each user's terminal is pointed — the serving
    satellite for a realised link, the candidate's satellite when the state
    asks what a candidate would look like.  It enters only through ``G^R``,
    and P-10's same-satellite override is applied against the NORAD id
    because the radiating set is global and has no slot indices.

    ``-1`` in ``boresight_norad_ids`` marks a user with no boresight; their
    row is returned with the bare envelope, which the caller must not use as
    a wanted-link SINR.
    """
    users = np.asarray(user_ecef_km, dtype=np.float64)
    boresight = np.asarray(boresight_satellite_ecef_km, dtype=np.float64)
    boresight_ids = np.asarray(boresight_norad_ids, dtype=np.int64)
    num_users = users.shape[0]
    if radiating.count == 0:
        return np.zeros((num_users, 0), dtype=np.float64)
    if boresight.shape != (num_users, 3):
        raise MCRLContractError("boresight_satellite_ecef_km must be (U, 3)")
    if boresight_ids.shape != (num_users,):
        raise MCRLContractError("boresight_norad_ids must be (U,)")

    separation = angle_between_deg(
        users[:, None, :],
        boresight[:, None, :],
        radiating.satellite_ecef_km[None, :, :],
    )
    receive = receive_gain_linear(separation)
    receive = apply_same_satellite_override(
        receive, radiating.norad_ids, boresight_ids
    )
    return (
        radiating.power_w[None, :]
        * field.transmit_gain
        * field.path_gain
        * field.fading_gain
        * receive
    )


# ---------------------------------------------------------------------------
# The sums themselves
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InterferenceBreakdown:
    """(3.12a) and (3.12b) kept apart, because which dominates is a finding."""

    intra_w: np.ndarray
    inter_w: np.ndarray

    @property
    def total_w(self) -> np.ndarray:
        """``I = I^intra + I^inter``."""
        return self.intra_w + self.inter_w

    @property
    def intra_fraction(self) -> np.ndarray:
        total = self.total_w
        return np.where(total > 0.0, self.intra_w / np.where(total > 0.0, total, 1.0), 0.0)


def co_channel_interference(
    power_terms: np.ndarray,
    radiating: RadiatingBeams,
    *,
    wanted_norad_ids: np.ndarray,
    wanted_cell_ids: np.ndarray,
    wanted_colors: np.ndarray,
) -> InterferenceBreakdown:
    """Split the co-colour radiated power into (3.12a) and (3.12b).

    ``power_terms`` is ``(U, B)`` from :func:`received_power_terms` — already
    ``z``-gated by membership of the radiating set.  The three ``wanted_*``
    arrays are ``(U,)`` and describe each victim's own link; ``-1`` in
    ``wanted_norad_ids`` means the user has no link, and their interference
    comes back as zero rather than as the whole co-colour sum.
    """
    terms = np.asarray(power_terms, dtype=np.float64)
    norads = np.asarray(wanted_norad_ids, dtype=np.int64)
    cells = np.asarray(wanted_cell_ids, dtype=np.int64)
    colors = np.asarray(wanted_colors, dtype=np.int64)
    num_users = norads.shape[0]
    if terms.shape != (num_users, radiating.count):
        raise MCRLContractError(
            f"power_terms must be ({num_users}, {radiating.count}), "
            f"got {terms.shape}"
        )
    if cells.shape != (num_users,) or colors.shape != (num_users,):
        raise MCRLContractError("the wanted-link arrays must all be (U,)")
    if np.any(terms < 0.0):
        raise MCRLContractError("received power terms must be non-negative")

    if radiating.count == 0:
        zeros = np.zeros(num_users, dtype=np.float64)
        return InterferenceBreakdown(intra_w=zeros, inter_w=zeros.copy())

    linked = norads >= 0
    same_satellite = radiating.norad_ids[None, :] == norads[:, None]
    same_cell = radiating.cell_ids[None, :] == cells[:, None]
    co_colour = radiating.colors[None, :] == colors[:, None]

    # (3.12a): same satellite, v' != v, same colour.
    intra = co_colour & same_satellite & ~same_cell
    # (3.12b): a different satellite, EVERY co-colour beam including v' = v.
    inter = co_colour & ~same_satellite

    intra &= linked[:, None]
    inter &= linked[:, None]
    return InterferenceBreakdown(
        intra_w=(terms * intra).sum(axis=1),
        inter_w=(terms * inter).sum(axis=1),
    )


def wanted_power_w(
    *,
    link_power_w: np.ndarray,
    transmit_gain: np.ndarray,
    path_gain: np.ndarray,
    fading_gain: np.ndarray,
    receive_gain: np.ndarray,
) -> np.ndarray:
    """(3.13)'s numerator, ``p_{u,s,v}·H_{u,s,v}·G^T(θ_{u,s,v})``.

    ⚠ **The numerator uses the link power ``p_{u,s,v}``, the interference the
    beam power ``p_{s,v}``.**  That asymmetry is (3.12a)/(3.13) as written:
    the beam radiates ``max_u p_{u,s,v}``, so a user who is not the maximum
    is credited with less wanted signal than their beam actually puts out.
    It is reproduced rather than smoothed over, and it is conservative — the
    error is always in the direction of a lower reported SINR.
    """
    return (
        np.asarray(link_power_w, dtype=np.float64)
        * np.asarray(transmit_gain, dtype=np.float64)
        * np.asarray(path_gain, dtype=np.float64)
        * np.asarray(fading_gain, dtype=np.float64)
        * np.asarray(receive_gain, dtype=np.float64)
    )


# ---------------------------------------------------------------------------
# The candidate-table view (4.1)'s second block
# ---------------------------------------------------------------------------
#
# (4.1) puts ``γ_{u,s,v}(t, θ(t))`` at **every** candidate position, not just
# the realised one, and it constrains the value to "選擇動作前可取得的資訊"
# — information available before the action is chosen.  Those two demands
# pull against each other: this step's interference depends on this step's
# activations, which depend on this step's actions.
#
# The paper resolves it itself: "若實作使用 cached 或 predicted provenance,
# 該標記放在資料欄位 metadata,不改變公式中的物理符號."  So the candidate
# SINR is built from the **current** geometry ``θ(t)`` — genuinely pre-action
# — against the **previous** step's radiating set, and the provenance is
# named rather than left for a reader to infer.


CANDIDATE_SINR_PROVENANCE: str = "theta-current-interference-previous-step"
"""What the state's ``γ`` block actually is, in one string.

Carried into the PREREG and the artifacts so that "the state's SINR" is
never quoted as if it were the realised link SINR of (3.13).  They differ
whenever the activation pattern moves between steps, which is most steps.
"""


def candidate_received_power_terms(
    field: BeamFieldAtUsers,
    radiating: RadiatingBeams,
    *,
    user_ecef_km: np.ndarray,
    candidate_satellite_ecef_km: np.ndarray,
    candidate_norad_ids: np.ndarray,
) -> np.ndarray:
    """``(U, L, B)`` — the radiated terms as each candidate's boresight sees them.

    Indexed by **satellite slot** rather than by the 28 flat candidates: the
    terminal's receive gain depends on which satellite it is pointed at, and
    all seven beam slots of one slot share that satellite.  Expanding to 28
    first would compute the same seven columns seven times.
    """
    users = np.asarray(user_ecef_km, dtype=np.float64)
    satellites = np.asarray(candidate_satellite_ecef_km, dtype=np.float64)
    norads = np.asarray(candidate_norad_ids, dtype=np.int64)
    num_users = users.shape[0]
    if satellites.ndim != 3 or satellites.shape[0] != num_users or satellites.shape[2] != 3:
        raise MCRLContractError("candidate_satellite_ecef_km must be (U, L, 3)")
    slots = satellites.shape[1]
    if norads.shape != (num_users, slots):
        raise MCRLContractError("candidate_norad_ids must be (U, L)")
    if radiating.count == 0:
        return np.zeros((num_users, slots, 0), dtype=np.float64)
    if not np.all(np.isfinite(satellites)):
        raise MCRLContractError(
            "an unoccupied satellite slot must carry a finite placeholder "
            "position; NaN would propagate through arccos into every gain"
        )

    base = (
        radiating.power_w[None, :]
        * field.transmit_gain
        * field.path_gain
        * field.fading_gain
    )  # (U, B)

    terms = np.zeros((num_users, slots, radiating.count), dtype=np.float64)
    for slot in range(slots):
        separation = angle_between_deg(
            users[:, None, :],
            satellites[:, slot, :][:, None, :],
            radiating.satellite_ecef_km[None, :, :],
        )
        receive = apply_same_satellite_override(
            receive_gain_linear(separation), radiating.norad_ids, norads[:, slot]
        )
        terms[:, slot, :] = base * receive
    return terms


def candidate_interference_w(
    candidate_terms: np.ndarray,
    radiating: RadiatingBeams,
    *,
    candidate_norad_ids: np.ndarray,
    candidate_cell_ids: np.ndarray,
    candidate_colors: np.ndarray,
) -> np.ndarray:
    """``(U, C)`` interference for every candidate, same masks as (3.12a)/(3.12b).

    ``candidate_terms`` is ``(U, L, B)``; the three identity arrays are
    ``(U, C)`` over the flat 28-wide table, and ``-1`` marks a slot with no
    identity, whose interference is zero because there is no link to
    interfere with.
    """
    terms = np.asarray(candidate_terms, dtype=np.float64)
    norads = np.asarray(candidate_norad_ids, dtype=np.int64)
    cells = np.asarray(candidate_cell_ids, dtype=np.int64)
    colors = np.asarray(candidate_colors, dtype=np.int64)
    num_users, num_candidates = norads.shape
    if cells.shape != norads.shape or colors.shape != norads.shape:
        raise MCRLContractError("the candidate identity arrays must all be (U, C)")
    if radiating.count == 0:
        return np.zeros((num_users, num_candidates), dtype=np.float64)

    slots = terms.shape[1]
    if num_candidates % slots:
        raise MCRLContractError(
            f"{num_candidates} candidates do not divide into {slots} satellite slots"
        )
    beams_per_slot = num_candidates // slots
    # (U, C, B): each beam slot of a satellite slot reuses that slot's row.
    expanded = np.repeat(terms, beams_per_slot, axis=1)

    linked = norads >= 0
    same_satellite = radiating.norad_ids[None, None, :] == norads[:, :, None]
    same_cell = radiating.cell_ids[None, None, :] == cells[:, :, None]
    co_colour = radiating.colors[None, None, :] == colors[:, :, None]

    contributes = co_colour & ((same_satellite & ~same_cell) | ~same_satellite)
    contributes &= linked[:, :, None]
    return (expanded * contributes).sum(axis=2)
