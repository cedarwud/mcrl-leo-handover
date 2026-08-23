"""Execution-time service resolution and load accounting (W-07).

Guardrails P-5 and P-6, gates G-4 and G-12.

**Two load quantities, deliberately different, never interchangeable.**

``demand`` is the global, **ungated, pre-admission** count: how many users
selected each beam.  It is what the state exposes (ASSUME-MODQN-REP-013's
``beam_loads`` and (4.1)'s ``n_{s,v}(t−1)``), because a user has to be able
to see that a beam is busy *before* deciding to pile onto it.

**Both are keyed by the beam ``(s, v)``, never by the cell ``v`` alone.**
(3.3) is ``U_{s,v}(t) = Σ_u x_{u,s,v}(t)`` — a sum over one satellite's beam,
not over a patch of ground.  Two satellites may illuminate the same cell at
once, and (3.12b)'s inner sum has no ``v' ≠ v`` restriction precisely because
that is a legal configuration.  Keying on the cell alone merges those two
beams into one: each user is charged the other's load in ``r3``, (3.14)
divides each one's bandwidth by two when neither is sharing, and the
activation vector reports one radiating beam where two radiate.

``eligible_load`` is the count **after the per-link power feasibility
check**: how many users the beam actually serves.  It drives activation,
the beam transmit-power aggregation, and B13's ``r3 = −U_{b_u}``.

⚠ This paragraph said "after the execution-time mask ``m^e``" until
2026-08-23, and named ``γ_req(U)`` as a consumer.  **The behaviour was
right and the description was wrong**, which is the more dangerous of the
two: ``eligible[beam] += 1`` runs only after ``served[uid] = True``, i.e.
only after feasibility, so it has always computed exactly
``U_{s,v} = Σ_u x_{u,s,v}`` — eq. (3.3).  ``m^e`` was deleted by ruling
C-11 and ``γ_req`` is not on the live path at all.

Conflating them is exactly the "two incompatible load semantics" P-5 and
P-6 exist to prevent, and it is not hypothetical: an action is chosen
against the mask at decision time, and by execution time the user and the
satellite have both moved.  A link that has just gone invalid must not
count toward ``U_{b_u}`` while being assigned no serving beam — ``r3`` would
be charging the user for service nobody delivered.

**Two gates, not three (ruling C-11, 2026-08-22).**  Paper (4.5a) is
``x = a · z``.  ``m`` is the **decision-time** mask — it decides what a user
may choose — and does not enter the connection identity.  An earlier SDD
§2.2 revision recorded a three-gate ``x = a · m^e · z``; the controller has
since withdrawn it (that revision was an assistant ruling, not a user
authorisation) and the SDD is being corrected.

What survives is the *behaviour*, under its proper name: "連上之後仍須滿足
鏈路可行性:所需功率超過每波束上限者判為不可行,該使用者於該步為 outage".
So the gate between selecting and being served is **per-link power
feasibility**, not a second mask.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ..errors import MCRLContractError
from .action_contract import NO_OP_ACTION, NUM_ACTIONS, SlotTable

R3_SCALE_IS_FROZEN: bool = True
"""Whether the ``r3`` calibration scale has been decided.  **True.**

**Closed by probe P3 on 2026-08-23** — the first question in this project
closed by a probe rather than by a ruling, which is what the freeze flags
were built for.  See :data:`R3_CALIBRATION_SCALE`.
"""

R3_CALIBRATION_SCALE: int = 6
"""``r3`` enters training as ``−U_{b_u} / 6``.  **D**, from probe P3.

The frozen Q-D selection mapping, committed before P3 ran, was "the p95 of
``|r3|`` over served steps, rounded to the nearest integer".  P3 measured
``|r3|`` over 12,000 decision steps at p05/p50/p95/max = 1 / 3 / **6** / 8,
so the mapping returns **6**.  The number was not chosen after the fact;
the *rule* was frozen and this is what it selected.

Why p95 and not max: the max is one congested beam, and a divisor that
tracks a single outlier is not a scale.  Why an integer: ``U_{b_u}`` is a
head count, so its scale should stay a countable quantity rather than a
fitted one.

⚠ Applied through ``TrainerConfig.reward_calibration_*``, which is why that
surface survived P-05 when the other opt-in surfaces went.

⚠ Measured under the **reference policy** at the frozen scenario.  A trained
policy will spread load differently; the scale is frozen at this value
regardless, because re-deriving it from training output would make the
reward scale a function of the run it is scoring.
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

    demand_by_beam: dict[tuple[int, int], int]
    """``n_{s,v}(t)`` — ungated pre-admission count, keyed ``(norad_id, cell_id)``."""

    eligible_load_by_beam: dict[tuple[int, int], int]
    """``U_{s,v}(t)`` — post-feasibility count, keyed ``(norad_id, cell_id)``."""

    no_op_users: np.ndarray
    """``(U,)`` bool — had no valid action at decision time (§4A.5a)."""

    outage_infeasible: np.ndarray
    """``(U,)`` bool — selected a valid action, but the link was infeasible.

    The population (4.5a)'s follow-on sentence describes: the recurrence
    power exceeded the per-beam RF ceiling, so the user is in outage for
    this step.  Its rate must be reported — a large one means the geometry
    is outrunning the power budget rather than the policy choosing badly.
    """

    @property
    def served_count(self) -> int:
        return int(np.count_nonzero(self.served))

    @property
    def active_beams(self) -> tuple[tuple[int, int], ...]:
        """Beams with positive eligible load, as sorted ``(norad_id, cell_id)``.

        ``z_{s,v}(t) = 1{ U_{s,v}(t) > 0 }`` — activation is **derived, not
        chosen** (ruling 2026-08-22 §7.4).  There is no selection step, no
        ranking, and no ceiling: every cell with at least one served user is
        lit, always.

        The alternative was measured once already: the repo-invented
        activation ceiling of 2026-07-15 darkened beams by demand rank and
        starved 68 of 100 users, inverting the congestion incentive.  It
        would also fight ``r3 = −U_{b_u}``, which rewards moving to a
        *quieter* beam, while any demand-ranked darkening rule extinguishes
        the quiet beams first.
        """
        return tuple(sorted(self.eligible_load_by_beam))

    def activation_vector(
        self, beam_keys: Sequence[tuple[int, int]]
    ) -> np.ndarray:
        """``z`` over an explicit beam ordering, derived from the loads alone."""
        return np.array(
            [
                self.eligible_load_by_beam.get(
                    (int(norad), int(cell)), 0
                )
                > 0
                for norad, cell in beam_keys
            ],
            dtype=bool,
        )

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
                    self.eligible_load_by_beam[
                        (
                            int(self.serving_satellite[uid]),
                            int(self.serving_cell[uid]),
                        )
                    ]
                )
        return loads


def resolve_service(
    actions: np.ndarray,
    decision_tables: Sequence[SlotTable],
    link_infeasible: np.ndarray,
) -> ServiceResolution:
    """Resolve one step: ``x = a · z``, then per-link feasibility.

    ``decision_tables`` are the slot tables the actions were chosen against.
    ``link_infeasible`` is ``(U,)`` — whether each user's chosen link needs
    more power than the per-beam ceiling allows.  Infeasible users are
    excluded from load, activation and power, while their pre-admission
    demand still appears in ``demand_by_beam``.

    The ``z`` gate is satisfied by construction: a beam radiates iff someone
    selects it (3.4), so anyone who selected it and is feasible connects.
    Writing it out anyway keeps (4.5a) visible in the code.
    """
    selected = np.asarray(actions)
    if selected.dtype.kind not in "iu":
        raise MCRLContractError("actions must be integers")
    users = selected.size
    if len(decision_tables) != users:
        raise MCRLContractError("one decision slot table per user is required")
    infeasible = np.asarray(link_infeasible, dtype=bool)
    if infeasible.shape != (users,):
        raise MCRLContractError(
            f"link_infeasible must have shape ({users},), got {infeasible.shape}"
        )

    served = np.zeros(users, dtype=bool)
    no_op = np.zeros(users, dtype=bool)
    outage = np.zeros(users, dtype=bool)
    serving_cell = np.full(users, -1, dtype=np.int64)
    serving_satellite = np.full(users, -1, dtype=np.int64)
    demand: dict[tuple[int, int], int] = {}
    eligible: dict[tuple[int, int], int] = {}

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
        beam = (association.norad_id, cell)
        # Pre-admission demand counts every intent, gated or not.
        demand[beam] = demand.get(beam, 0) + 1

        if bool(infeasible[uid]):
            # (4.5a)'s follow-on: connected, but the link needs more power
            # than the beam ceiling allows, so this step is an outage.
            outage[uid] = True
            continue

        served[uid] = True
        serving_cell[uid] = cell
        serving_satellite[uid] = association.norad_id
        eligible[beam] = eligible.get(beam, 0) + 1

    return ServiceResolution(
        served=served,
        serving_cell=serving_cell,
        serving_satellite=serving_satellite,
        demand_by_beam=demand,
        eligible_load_by_beam=eligible,
        no_op_users=no_op,
        outage_infeasible=outage,
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
        sum(count * count for count in resolution.eligible_load_by_beam.values())
    )
    return per_user, per_beam


# PATCH P-22 (W-26): ``required_sinr()`` is deleted.
#
# It computed ``γ_req(U) = 2^(R^m·U/B^w) − 1``, the SINR needed to hold a
# minimum rate at a given load.  Three reasons, any one of which would do:
#
#   * **zero live consumers** — only tests called it;
#   * ``R^m = 1 Mbit/s`` is a **legacy-only** parameter (ruling C-12), and
#     the active contract "明文排除最低速率反推";
#   * ruling C-2 forbids target-SINR inversion outright, and this is its
#     first half sitting in the tree with nothing but tests holding it up.
#
# The PREREG had it frozen as a live consumer of the eligible load, which
# is how a dead surface becomes a permanent claim about the system.

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
