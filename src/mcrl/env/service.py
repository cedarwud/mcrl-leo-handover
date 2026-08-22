"""Execution-time service resolution and load accounting (W-07).

Guardrails P-5 and P-6, gates G-4 and G-12.

**Two load quantities, deliberately different, never interchangeable.**

``demand`` is the global, **ungated, pre-admission** count: how many users
selected each cell.  It is what the state exposes (ASSUME-MODQN-REP-013's
``beam_loads``), because a user has to be able to see that a beam is busy
*before* deciding to pile onto it.

``eligible_load`` is the count **after** the execution-time mask ``m^e``:
how many users the beam actually serves.  It is what drives activation,
transmit power, ``γ_req(U)``, and B13's ``r3 = −U_{b_u}``.

Conflating them is exactly the "two incompatible load semantics" P-5 and
P-6 exist to prevent, and it is not hypothetical: an action is chosen
against the mask at decision time, and by execution time the user and the
satellite have both moved.  A link that has just gone invalid must not
count toward ``U_{b_u}`` while being assigned no serving beam — ``r3`` would
be charging the user for service nobody delivered.

**On ``m^e`` (SDD §2.2, revised 2026-08-22).**  B10 originally deleted the
execution mask; the revision keeps it as environment-side accounting and
removes only the contribution claim.  B10 predated B13, and once ``r3``
became a count of who is served, the thing ``m^e`` gates became load-bearing
for reward correctness.  The connection identity keeps all three gates,
``x = a · m^e · z`` (paper eq. 4.5a).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ..errors import MCRLContractError
from .action_contract import NO_OP_ACTION, NUM_ACTIONS, SlotTable

R3_SCALE_IS_FROZEN: bool = False
"""Whether the ``r3`` calibration scale has been decided.  **False.**

Q-D ("``r3`` 重新校準的尺度取法") is open, and B13 changed ``r3``'s units
entirely — the old scale was fitted to a normalised gap, the new one is a
raw user count.  A machine-checkable flag, like ``DWELL_N_IS_FROZEN``, so
the W-13 freezer cannot emit a PREREG carrying a stale scale.
"""


@dataclass(frozen=True)
class ServiceResolution:
    """Who is actually served this step, and both load quantities."""

    served: np.ndarray
    """``(U,)`` bool — chose an action AND it survived the execution mask."""

    serving_cell: np.ndarray
    """``(U,)`` global cell id, or ``-1`` when unserved."""

    serving_satellite: np.ndarray
    """``(U,)`` NORAD id, or ``-1`` when unserved."""

    demand_by_cell: dict[int, int]
    """Ungated pre-admission count per cell — the **state** quantity."""

    eligible_load_by_cell: dict[int, int]
    """Post-``m^e`` count per cell — the **reward and physics** quantity."""

    no_op_users: np.ndarray
    """``(U,)`` bool — had no valid action at decision time (§4A.5a)."""

    execution_dropped: np.ndarray
    """``(U,)`` bool — action was valid when chosen, invalid when executed.

    This is the population P-5 exists for.  Its rate must be reported: a
    large one means decision and execution have drifted far enough apart
    that the policy is being graded on a different world than it acted in.
    """

    @property
    def served_count(self) -> int:
        return int(np.count_nonzero(self.served))

    @property
    def active_cells(self) -> tuple[int, ...]:
        """Cells with positive eligible load — activation ⟺ positive load."""
        return tuple(sorted(self.eligible_load_by_cell))

    def user_beam_load(self) -> np.ndarray:
        """``U_{b_u}`` per user: the eligible load of the beam serving them.

        Zero for an unserved user — they are on no beam, so they contribute
        nothing and are charged nothing (consistent with ``Ψ = 0`` and
        ``r1 ≈ 0`` for the same step).
        """
        loads = np.zeros(self.served.size, dtype=np.float64)
        for uid in range(self.served.size):
            if self.served[uid]:
                loads[uid] = float(
                    self.eligible_load_by_cell[int(self.serving_cell[uid])]
                )
        return loads


def resolve_service(
    actions: np.ndarray,
    decision_tables: Sequence[SlotTable],
    execution_masks: np.ndarray,
) -> ServiceResolution:
    """Apply the execution-time mask and split the two load quantities.

    ``decision_tables`` are the slot tables the actions were chosen against.
    ``execution_masks`` is ``(U, 28)`` — the mask re-evaluated *after*
    mobility, at the moment of execution.  A user whose chosen action has
    gone invalid is excluded from load, activation and power (P-5), while
    their pre-admission demand still appears in ``demand_by_cell``.
    """
    selected = np.asarray(actions)
    if selected.dtype.kind not in "iu":
        raise MCRLContractError("actions must be integers")
    users = selected.size
    if len(decision_tables) != users:
        raise MCRLContractError("one decision slot table per user is required")
    masks = np.asarray(execution_masks, dtype=bool)
    if masks.shape != (users, NUM_ACTIONS):
        raise MCRLContractError(
            f"execution_masks must have shape ({users}, {NUM_ACTIONS}), "
            f"got {masks.shape}"
        )

    served = np.zeros(users, dtype=bool)
    no_op = np.zeros(users, dtype=bool)
    dropped = np.zeros(users, dtype=bool)
    serving_cell = np.full(users, -1, dtype=np.int64)
    serving_satellite = np.full(users, -1, dtype=np.int64)
    demand: dict[int, int] = {}
    eligible: dict[int, int] = {}

    for uid in range(users):
        action = int(selected[uid])
        if action == NO_OP_ACTION:
            no_op[uid] = True
            continue
        if not 0 <= action < NUM_ACTIONS:
            raise MCRLContractError(f"user {uid} action {action} out of range")
        table = decision_tables[uid]
        if not bool(table.mask[action]):
            raise MCRLContractError(
                f"user {uid} action {action} was invalid at decision time; "
                "P-4 should have caught this before execution"
            )

        association = table.association(action)
        cell = association.cell_id
        # Pre-admission demand counts every intent, gated or not.
        demand[cell] = demand.get(cell, 0) + 1

        if not bool(masks[uid, action]):
            # P-5: the link died between decision and execution.
            dropped[uid] = True
            continue

        served[uid] = True
        serving_cell[uid] = cell
        serving_satellite[uid] = association.norad_id
        eligible[cell] = eligible.get(cell, 0) + 1

    return ServiceResolution(
        served=served,
        serving_cell=serving_cell,
        serving_satellite=serving_satellite,
        demand_by_cell=demand,
        eligible_load_by_cell=eligible,
        no_op_users=no_op,
        execution_dropped=dropped,
    )


def r3_counting(resolution: ServiceResolution) -> np.ndarray:
    """B13: ``r3,u(t) = −U_{b_u}(t)``.

    G-4 (decomposability): each user's value depends **only** on the load of
    the beam they chose.  No global scalar appears, so one user's reward
    cannot move because a beam they are not on got busier.

    Algebraically ``Σ_u U_{b_u} = Σ_b U_b²``, which for a fixed total is
    minimised by a perfectly even spread — so maximising ``Σ_u r3,u`` is
    load balancing, and with empty beams present it degenerates to min-max
    balancing.  Both are legitimate objectives; the old form was blind to
    load because ``U_{s,v}`` cancelled out of it entirely.
    """
    return -resolution.user_beam_load()


def load_balance_identity(resolution: ServiceResolution) -> tuple[float, float]:
    """Return ``(Σ_u U_{b_u}, Σ_b U_b²)`` — equal by construction."""
    per_user = float(resolution.user_beam_load().sum())
    per_beam = float(
        sum(count * count for count in resolution.eligible_load_by_cell.values())
    )
    return per_user, per_beam


def required_sinr(
    load: np.ndarray,
    *,
    minimum_rate_bps: float,
    beam_bandwidth_hz: float,
) -> np.ndarray:
    """``γ_req(U)`` — the SINR that meets the QoS floor at this beam load.

    The beam's bandwidth is shared by its ``U`` served users, so the
    requirement rises with load.  ``U`` here must be the **eligible** load
    (P-5/P-6): using the ungated demand would demand extra SINR on behalf of
    users the beam is not serving.
    """
    counts = np.asarray(load, dtype=np.float64)
    if np.any(counts < 0.0):
        raise MCRLContractError("loads must be non-negative")
    if minimum_rate_bps < 0.0 or beam_bandwidth_hz <= 0.0:
        raise ValueError("rate must be non-negative and bandwidth positive")
    with np.errstate(over="ignore"):
        return np.where(
            counts > 0.0,
            np.power(2.0, minimum_rate_bps * np.maximum(counts, 1.0) / beam_bandwidth_hz)
            - 1.0,
            0.0,
        )


@dataclass(frozen=True)
class R3CalibrationSample:
    """One step's ``r3`` statistics, for the Q-D scale decision."""

    served: int
    mean_abs_r3: float
    max_abs_r3: float
    spread: float
    """Width of ``U_{b_u}`` across the population — P3's discriminability input."""


def sample_r3_calibration(resolution: ServiceResolution) -> R3CalibrationSample:
    """Collect what Q-D needs, without choosing the scale.

    Q-D is open.  This deliberately reports statistics rather than returning
    a scale: picking one from data the probe has already seen is exactly the
    adaptive-leak §7.1 forbids.
    """
    values = np.abs(r3_counting(resolution))
    served = resolution.served_count
    if served == 0:
        return R3CalibrationSample(0, 0.0, 0.0, 0.0)
    served_values = values[resolution.served]
    return R3CalibrationSample(
        served=served,
        mean_abs_r3=float(served_values.mean()),
        max_abs_r3=float(served_values.max()),
        spread=float(served_values.max() - served_values.min()),
    )


def old_r3_is_load_blind(
    loads: Sequence[float], *, spectral_efficiency: float = 1.0
) -> bool:
    """Demonstrate the defect B13 fixed: ``U_{s,v}`` cancels out of the old form.

    The old ``r3`` was ``R̃ = B^w · mean_u log₂(1 + γ_u)``.  Per-user rate is
    ``(B/U)·log₂(1+γ)`` and the mean over the beam's ``U`` users multiplies
    it straight back by ``U``, so the load disappears and the reward cannot
    see it.  Returns True when the old form gives the same value for every
    load — which it always does.
    """
    values = set()
    for load in loads:
        if load <= 0:
            continue
        per_user_rate = spectral_efficiency / load
        values.add(round(per_user_rate * load, 12))
    return len(values) <= 1
