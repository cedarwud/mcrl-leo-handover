"""Action index contract and environment-side accounting (SDD §4A, W-03).

**The network never changes.**  It stays a flat 28-output MLP with hidden
layers ``(100, 50, 50)`` and ``tanh``.  Everything in this module is
environment-side bookkeeping (SDD §4A preamble, §3.3).

Index layout (§4A.1)::

    a = 7·l + j        l ∈ {0,1,2,3} satellite slot,  j ∈ {0,…,6} beam slot

The four state blocks use the same ``(l, j)`` order, so state and action are
aligned by construction.

The load-bearing rule of the whole module (§4A.4)::

    handover is decided from the REALISED ASSOCIATION (norad_id, cell_id),
    never from the action index

Comparing indices fails two ways that no assertion would catch: a forced
handover after the incumbent loses eligibility keeps index 0 and reads as
"no handover" (false negative), and returning to the same satellite after it
becomes the incumbent changes the index and reads as a handover that never
happened (false positive).  Tests T1 and T2 pin both.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Iterable, Sequence, SupportsInt

import numpy as np

from ..errors import MCRLContractError

# ---------------------------------------------------------------------------
# Index layout (§4A.1)
# ---------------------------------------------------------------------------

NUM_SATELLITE_SLOTS: int = 4
"""``L_w`` — SDD B12, matching MODQN §IV's four satellites."""

NUM_BEAM_SLOTS: int = 7
"""``J_w`` — the anchor cell plus its six canonical neighbours (§4A.2).

⚠ **This 7 is not MODQN Table I's ``V = 7``.  The match is a coincidence.**

Table I's ``V = 7`` is ``|𝒱|`` at *their* granularity: how many beam
positions one satellite has in total.  In Sun-2024 a "beam" has no geometry
at all — a full-text grep finds zero hits for off-axis, boresight, pointing,
3 dB, half-power, footprint, steer, or earth-fixed — so a beam there is a
non-spatial load channel and the number could have been 7, 3 or 70 without
changing anything.

This paper adds the geometry they lacked, and once a beam has a pointing and
a 3 dB footprint it has to cover ground: at the measured 485 km, 95%
coverage needs 39 cells.  So Table I's ``V = 7`` is **superseded by this
paper's ``V`` (39, F5 pending)** — that is where it went; it was not left
homeless.

``J_w = 7`` is a different quantity entirely: how many cells one *user*
can reach (their own plus the six neighbours), from the hex-neighbourhood
argument in §3.3.  **The two must never be substituted for each other**, and
there is deliberately no per-satellite beam-count constant anywhere in this
project (ruling 2026-08-22 §7.2-7.3).
"""

NUM_ACTIONS: int = NUM_SATELLITE_SLOTS * NUM_BEAM_SLOTS
"""``C = 28`` — the flat output width.  Frozen; the network is not touched."""

NO_OP_ACTION: int = -1
"""Emitted when a user's decision mask is empty (SDD §4A.5a(1)).

Not a beam index and not maskable: it is the absence of a decision.

Obligations on the environment:

1. ``env.step`` leaves that user **unserved** — no beam activation, no power,
   no contribution to ``beam_load_b`` or ``U_{b_u}`` (P-6, the single load
   semantics the counting-form ``r3`` rests on);
2. the handover ledger records ``Ψ = 0`` for the unserved step and ``φ2`` on
   the next served step (§4A.4 boundary table; T5/T8);
3. the transition never reaches replay (§4A.5a(2); enforced trainer-side,
   ``docs/PATCH-LEDGER.md`` P-03).

The sentinel is negative on purpose — a hard trip-wire.  Any code that
treats actions as indices (``np.bincount``, ``gather``, direct indexing)
fails loudly instead of silently aliasing onto the last beam.
"""

UNSERVED_CELL: int = -1
"""Cell component of a slot entry that cannot be pointed at."""


def is_no_op(action: SupportsInt) -> bool:
    return int(action) == NO_OP_ACTION


def no_op_actions(num_users: int) -> np.ndarray:
    return np.full(int(num_users), NO_OP_ACTION, dtype=np.int32)


def served_mask(actions: np.ndarray) -> np.ndarray:
    return np.asarray(actions) != NO_OP_ACTION


def action_index(satellite_slot: int, beam_slot: int) -> int:
    """``a = 7·l + j`` with range checks."""
    if not 0 <= satellite_slot < NUM_SATELLITE_SLOTS:
        raise ValueError(f"satellite slot {satellite_slot} out of range")
    if not 0 <= beam_slot < NUM_BEAM_SLOTS:
        raise ValueError(f"beam slot {beam_slot} out of range")
    return NUM_BEAM_SLOTS * satellite_slot + beam_slot


def decode_action(action: SupportsInt) -> tuple[int, int]:
    """Inverse of :func:`action_index`.  Rejects the no-op sentinel."""
    value = int(action)
    if value == NO_OP_ACTION:
        raise MCRLContractError("NO_OP_ACTION has no (l, j) decomposition")
    if not 0 <= value < NUM_ACTIONS:
        raise ValueError(f"action {value} out of range [0,{NUM_ACTIONS})")
    return divmod(value, NUM_BEAM_SLOTS)


# ---------------------------------------------------------------------------
# Satellite slot assignment (§4A.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SatelliteCandidate:
    """One satellite's D2 state for one user at one step.

    Produced by W-04.  W-03 only consumes it, which keeps the identity and
    masking contract testable without a D2 implementation.

    ``margin_km`` is "how much room to spare", larger is better — e.g.
    ``Thresh2 − filtered_distance``.  Ordering by it is deliberate: SDD
    §4A.3 keeps relevance ordering over NORAD ordering because slot
    semantics ("slot 1 is this step's best alternative") is a normalised set
    representation, whereas NORAD ordering leaves slots meaningless and
    makes the flat MLP compare across positions itself.
    """

    norad_id: int
    eligible: bool
    margin_km: float
    radial_rate_km_s: float = 0.0
    """Signed range rate: negative approaching, positive receding (§4A.6)."""
    ttt_counter: int = 0
    """Steps the D2 entry condition has held, latched per NORAD (§4A.6)."""


@dataclass(frozen=True)
class SlotAssignment:
    """Which satellite occupies each of the four slots."""

    norad_ids: tuple[int, ...]
    """Length 4; ``-1`` where the slot is empty."""
    occupied: tuple[bool, ...]
    is_incumbent: tuple[bool, ...]
    margin_km: tuple[float, ...]
    radial_rate_km_s: tuple[float, ...]
    ttt_counter: tuple[int, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "norad_ids",
            "occupied",
            "is_incumbent",
            "margin_km",
            "radial_rate_km_s",
            "ttt_counter",
        ):
            if len(getattr(self, field_name)) != NUM_SATELLITE_SLOTS:
                raise MCRLContractError(
                    f"{field_name} must have {NUM_SATELLITE_SLOTS} entries"
                )

    @property
    def occupancy(self) -> np.ndarray:
        return np.array(self.occupied, dtype=bool)


def assign_satellite_slots(
    candidates: Sequence[SatelliteCandidate],
    *,
    incumbent_norad: int | None,
) -> SlotAssignment:
    """SDD §4A.3 — incumbent first if still eligible, then margin order.

    No hysteresis.  r4 introduced a hysteresis band for slot stability and
    review found it made the slot map depend on the previous ordering, which
    would need every candidate's previous rank in the state to stay Markov.
    Identity-based ``r2`` (§4A.4) removed the need for slot stability
    entirely, so the band went and the ordering is memoryless.
    """
    seen: set[int] = set()
    for candidate in candidates:
        if candidate.norad_id in seen:
            raise MCRLContractError(
                f"duplicate NORAD id {candidate.norad_id} in candidate list"
            )
        seen.add(candidate.norad_id)

    eligible = [candidate for candidate in candidates if candidate.eligible]
    # Decreasing margin, NORAD id breaks ties (§4A.3).
    ordered = sorted(eligible, key=lambda c: (-c.margin_km, c.norad_id))

    chosen: list[SatelliteCandidate] = []
    if incumbent_norad is not None:
        for candidate in ordered:
            if candidate.norad_id == incumbent_norad:
                chosen.append(candidate)
                ordered.remove(candidate)
                break
    chosen.extend(ordered[: NUM_SATELLITE_SLOTS - len(chosen)])

    norad_ids: list[int] = []
    occupied: list[bool] = []
    incumbent_flags: list[bool] = []
    margins: list[float] = []
    rates: list[float] = []
    counters: list[int] = []
    for slot in range(NUM_SATELLITE_SLOTS):
        if slot < len(chosen):
            candidate = chosen[slot]
            norad_ids.append(candidate.norad_id)
            occupied.append(True)
            incumbent_flags.append(candidate.norad_id == incumbent_norad)
            margins.append(float(candidate.margin_km))
            rates.append(float(candidate.radial_rate_km_s))
            counters.append(int(candidate.ttt_counter))
        else:
            norad_ids.append(-1)
            occupied.append(False)
            incumbent_flags.append(False)
            margins.append(0.0)
            rates.append(0.0)
            counters.append(0)
    return SlotAssignment(
        norad_ids=tuple(norad_ids),
        occupied=tuple(occupied),
        is_incumbent=tuple(incumbent_flags),
        margin_km=tuple(margins),
        radial_rate_km_s=tuple(rates),
        ttt_counter=tuple(counters),
    )


# ---------------------------------------------------------------------------
# Slot table and mask (§4A.4, §4A.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlotTable:
    """``slot_table[a] = (norad_id, cell_id)`` plus the mask over ``a``.

    This is the object §4A.5 requires replay to carry for **both** ends of a
    transition: it is what turns a stored action index back into the physical
    association that produced it.
    """

    norad_ids: np.ndarray
    """``(28,)`` int64; ``-1`` where the slot is empty."""
    cell_ids: np.ndarray
    """``(28,)`` int64; ``-1`` where the cell is absent or unreachable."""
    mask: np.ndarray
    """``(28,)`` bool — SDD §4A.5."""

    def __post_init__(self) -> None:
        for name in ("norad_ids", "cell_ids", "mask"):
            array = getattr(self, name)
            if array.shape != (NUM_ACTIONS,):
                raise MCRLContractError(
                    f"SlotTable.{name} must have shape ({NUM_ACTIONS},), "
                    f"got {array.shape}"
                )
        if np.any(self.mask & (self.norad_ids < 0)):
            raise MCRLContractError("a valid action has no satellite identity")
        if np.any(self.mask & (self.cell_ids < 0)):
            raise MCRLContractError("a valid action has no cell identity")

    @property
    def num_valid(self) -> int:
        return int(np.count_nonzero(self.mask))

    def association(self, action: SupportsInt) -> Association:
        """Physical association an action would realise."""
        value = int(action)
        if value == NO_OP_ACTION:
            return UNSERVED
        if not 0 <= value < NUM_ACTIONS:
            raise ValueError(f"action {value} out of range")
        if not bool(self.mask[value]):
            raise MCRLContractError(
                f"action {value} is not valid under this mask"
            )
        return Association(
            norad_id=int(self.norad_ids[value]),
            cell_id=int(self.cell_ids[value]),
        )


def build_slot_table(
    assignment: SlotAssignment,
    neighborhood_cell_ids: Sequence[int],
    *,
    cell_reachable: np.ndarray | None = None,
) -> SlotTable:
    """Assemble the slot table and mask for one user.

    ``neighborhood_cell_ids`` is the ``(7,)`` row from
    ``CellGrid.neighborhood_cell_ids`` — anchor first, then the six
    neighbours in fixed axial order.  ``-1`` means the lattice has no such
    neighbour, and that action stays masked.

    ``cell_reachable`` is the ``(4, 7)`` link-geometry predicate from W-04 /
    W-06: is cell ``j`` inside satellite ``l``'s coverage and is the link
    feasible.  Omitted means "assume reachable wherever the slot and cell
    both exist", which is only appropriate in tests.

    SDD §4A.5::

        mask[a] = 1  ⟺  slot l occupied ∧ cell j exists ∧ link feasible
    """
    cells = np.asarray(neighborhood_cell_ids, dtype=np.int64)
    if cells.shape != (NUM_BEAM_SLOTS,):
        raise MCRLContractError(
            f"neighborhood_cell_ids must have shape ({NUM_BEAM_SLOTS},), "
            f"got {cells.shape}"
        )
    if cell_reachable is None:
        reachable = np.ones((NUM_SATELLITE_SLOTS, NUM_BEAM_SLOTS), dtype=bool)
    else:
        reachable = np.asarray(cell_reachable, dtype=bool)
        if reachable.shape != (NUM_SATELLITE_SLOTS, NUM_BEAM_SLOTS):
            raise MCRLContractError(
                "cell_reachable must have shape "
                f"({NUM_SATELLITE_SLOTS}, {NUM_BEAM_SLOTS}), got {reachable.shape}"
            )

    norad_ids = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cell_ids = np.full(NUM_ACTIONS, UNSERVED_CELL, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=bool)

    cell_exists = cells >= 0
    for satellite_slot in range(NUM_SATELLITE_SLOTS):
        occupied = assignment.occupied[satellite_slot]
        for beam_slot in range(NUM_BEAM_SLOTS):
            index = action_index(satellite_slot, beam_slot)
            valid = bool(
                occupied
                and cell_exists[beam_slot]
                and reachable[satellite_slot, beam_slot]
            )
            mask[index] = valid
            if valid:
                norad_ids[index] = assignment.norad_ids[satellite_slot]
                cell_ids[index] = int(cells[beam_slot])
    return SlotTable(norad_ids=norad_ids, cell_ids=cell_ids, mask=mask)


# ---------------------------------------------------------------------------
# Handover accounting (§4A.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Association:
    """A realised (satellite, cell) pairing."""

    norad_id: int
    cell_id: int


class _Unserved:
    """Singleton for "this user was not served at this step"."""

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "UNSERVED"


UNSERVED = _Unserved()
AssociationOrUnserved = Association | _Unserved


class HandoverClass(enum.Enum):
    """The three mutually exclusive branches of paper eq. (3.27)."""

    NONE = "none"
    INTRA_SATELLITE = "phi1"
    """Same satellite, different cell."""
    INTER_SATELLITE = "phi2"
    """Different satellite — including re-entry after an outage."""


PHI1: float = 0.5
"""**S** — the paper gives only ``0 < φ1 < φ2``."""

PHI2: float = 1.0
"""**S** — same."""

HANDOVER_COST: dict[HandoverClass, float] = {
    HandoverClass.NONE: 0.0,
    HandoverClass.INTRA_SATELLITE: PHI1,
    HandoverClass.INTER_SATELLITE: PHI2,
}


def classify_handover(
    previous: AssociationOrUnserved | None,
    current: AssociationOrUnserved,
) -> HandoverClass:
    """SDD §4A.4.  ``previous is None`` means "episode start".

    ============================================  ==============
    case                                          result
    ============================================  ==============
    episode start                                 ``NONE``
    current unserved                              ``NONE``
    previous unserved, current served (re-entry)  ``INTER_SATELLITE``
    same satellite, same cell                     ``NONE``
    same satellite, different cell                ``INTRA_SATELLITE``
    different satellite                           ``INTER_SATELLITE``
    ============================================  ==============

    Re-entry is charged ``φ2`` because a full access procedure is needed.
    Scoring it 0 would let a policy **go offline on purpose to clear its
    handover cost** — an exploitable hole, so the rule is declared rather
    than convenient.

    The branches are mutually exclusive by construction: a step that changes
    both satellite and cell is exactly ``φ2``, never ``φ1 + φ2`` (T7).
    """
    if isinstance(current, _Unserved):
        return HandoverClass.NONE
    if previous is None:
        return HandoverClass.NONE
    if isinstance(previous, _Unserved):
        return HandoverClass.INTER_SATELLITE
    if previous.norad_id != current.norad_id:
        return HandoverClass.INTER_SATELLITE
    if previous.cell_id != current.cell_id:
        return HandoverClass.INTRA_SATELLITE
    return HandoverClass.NONE


class HandoverLedger:
    """Per-user handover accounting across a episode.

    Holds the previous **realised association**, never a previous index.
    ``reset()`` restores the episode-start state, which is distinct from
    "previously unserved": the first step of an episode is ``NONE``, whereas
    the step after an outage is ``φ2`` (P-8, the vacuum first step).
    """

    __slots__ = ("_previous", "_started")

    def __init__(self) -> None:
        self._previous: AssociationOrUnserved | None = None
        self._started = False

    def reset(self) -> None:
        self._previous = None
        self._started = False

    @property
    def previous(self) -> AssociationOrUnserved | None:
        return self._previous

    @property
    def incumbent_norad(self) -> int | None:
        """NORAD id of the currently serving satellite, if any."""
        if isinstance(self._previous, Association):
            return self._previous.norad_id
        return None

    def observe(self, current: AssociationOrUnserved) -> HandoverClass:
        """Record this step's association and return its handover class."""
        result = classify_handover(
            self._previous if self._started else None, current
        )
        self._previous = current
        self._started = True
        return result

    def cost(self, current: AssociationOrUnserved) -> float:
        """``-r2`` for this step: 0, ``φ1``, or ``φ2``."""
        return HANDOVER_COST[self.observe(current)]


def classify_step(
    ledgers: Sequence[HandoverLedger],
    slot_tables: Sequence[SlotTable],
    actions: np.ndarray,
) -> list[HandoverClass]:
    """Classify one step for every user, from associations not indices."""
    actions = np.asarray(actions)
    if not len(ledgers) == len(slot_tables) == actions.shape[0]:
        raise MCRLContractError(
            "ledgers, slot tables, and actions must have equal length"
        )
    return [
        ledgers[uid].observe(slot_tables[uid].association(actions[uid]))
        for uid in range(len(ledgers))
    ]


# ---------------------------------------------------------------------------
# Contract state fields (§4A.6)
# ---------------------------------------------------------------------------

CONTRACT_STATE_DIM: int = 3 * NUM_SATELLITE_SLOTS + 1
"""13 = is_incumbent(4) + d2_ttt_counter(4) + radial_rate(4) + dwell_phase(1)."""

STATE_DIM: int = 4 * NUM_ACTIONS + CONTRACT_STATE_DIM
"""125 — SDD §3.6 / §4A.6, the single authoritative value."""


def contract_state_fields(
    assignment: SlotAssignment,
    *,
    dwell_phase: float,
) -> np.ndarray:
    """The 13-dimensional block SDD §4A.6 appends to the four blocks.

    ``is_incumbent`` makes ``Ψ`` a function of ``s_t``; ``d2_ttt_counter``
    carries D2's path-dependent latch; ``radial_rate`` separates an
    approaching satellite from a receding one at equal margin (a signed
    rate, not an approaching/receding flag, because the flag throws away the
    magnitude); ``dwell_phase`` marks the re-key boundary, whose transition
    kernel differs from a non-boundary step.
    """
    if not 0.0 <= dwell_phase <= 1.0:
        raise ValueError(f"dwell_phase must be in [0,1], got {dwell_phase}")
    return np.concatenate(
        [
            np.array(assignment.is_incumbent, dtype=np.float32),
            np.array(assignment.ttt_counter, dtype=np.float32),
            np.array(assignment.radial_rate_km_s, dtype=np.float32),
            np.array([dwell_phase], dtype=np.float32),
        ]
    )


# ---------------------------------------------------------------------------
# Validation helpers (§3.7 P-4)
# ---------------------------------------------------------------------------


def assert_selected_actions_valid(
    actions: np.ndarray,
    slot_tables: Sequence[SlotTable],
) -> np.ndarray:
    """SDD §3.7 P-4: every selected action is valid, or a declared no-op.

    ``NO_OP_ACTION`` is accepted **only** when the user's mask is empty; a
    no-op emitted while a valid action existed is itself a contract
    violation, and so is any in-range action the mask forbids.
    """
    selected = np.asarray(actions)
    if selected.dtype.kind not in "iu":
        raise MCRLContractError("selected actions must be integers")
    if selected.shape != (len(slot_tables),):
        raise MCRLContractError("one selected action per user is required")
    for uid, action in enumerate(selected.tolist()):
        table = slot_tables[uid]
        if action == NO_OP_ACTION:
            if table.num_valid:
                raise MCRLContractError(
                    f"user {uid} emitted a no-op with {table.num_valid} "
                    "valid actions available"
                )
            continue
        if not 0 <= action < NUM_ACTIONS:
            raise MCRLContractError(
                f"user {uid} action {action} out of range [0,{NUM_ACTIONS})"
            )
        if not bool(table.mask[action]):
            raise MCRLContractError(
                f"user {uid} action {action} is invalid under its own mask"
            )
    out = np.array(selected, dtype=np.int64, copy=True)
    out.setflags(write=False)
    return out


def normalise_candidates(
    candidates: Iterable[SatelliteCandidate],
) -> list[SatelliteCandidate]:
    """Deterministic candidate order, independent of enumeration order.

    Test T9 shuffles the raw enumeration and requires the rebuilt ``s``,
    ``mask``, ``slot_table``, and physical action mapping to be identical.
    """
    return sorted(candidates, key=lambda c: c.norad_id)
