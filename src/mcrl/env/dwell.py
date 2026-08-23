"""Earth-fixed beam dwell and cell re-keying (SDD §3.4, W-05).

A beam holds an **earth-fixed** pointing for ``N`` steps, then re-anchors on
whichever cell is nearest the user at that instant.  Two consequences the
rest of the system depends on:

1. ``j → cell_id`` is rebuilt **only at a dwell boundary** (§4A.2).  Between
   boundaries the mapping is frozen, so an action index keeps naming the
   same physical cell for the whole segment.
2. A boundary can move ``j = 0`` onto a different cell while the index is
   unchanged.  The handover ledger therefore has to see the **cell**, not
   the index — test T6.  ``HandoverLedger`` already does; this module's job
   is to make the boundary explicit and its phase observable.

``dwell_phase`` enters the state (§4A.6) because the transition kernel at a
boundary genuinely differs from a non-boundary step: only there can the
mapping move under a fixed index.

**How often does a re-key actually change ``j = 0``?**  Users move at
30 km/h, so 10 s of travel is 83 m against a cell radius of ~14 km.  Within
an episode the anchor is almost always unchanged — but "almost always" is
not "never", and T6 covers the case that matters rather than assuming it
away.

**Choosing ``N`` (Q-E, probe P2).**  The feasibility argument uses the
**measured service window at ≥10° elevation, 6.3 min (p50)** — *not* the
10.5 min horizon-to-horizon figure (author ruling, 2026-08-22).  A dwell
segment must be short against that window or the earth-fixed beam is still
pointing where the satellite can no longer usefully serve.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..errors import MCRLContractError
from .cells import CellGrid

DWELL_N_CANDIDATES: tuple[int, ...] = (2, 3, 4)
"""**S** — the probe P2 sweep.  The final value is Q-E, still open."""

DWELL_N_IS_FROZEN: bool = True
"""Whether ``N`` has been decided.  **True since 2026-08-23: ``N = 3``.**

⚠ **Closed without running P2, and the reason matters.**  The frozen
selection mapping was "take the largest ``N`` whose re-key rate stays at or
under 5%".  That rule is deliberately independent of EE, throughput and
every reported metric — §4A.2 gives dwell exactly one job, freezing
``j → cell_id`` so an action index keeps naming the same cell, and its only
cost is **staleness**, which the re-key rate measures directly.

The rule needs one number, and that number is scenario characterisation
rather than probe output: the measured re-key rate at ``Δt = 30.08 s`` is
2.7% at ``N = 2``, **3.8% at ``N = 3``**, and 5.4% at ``N = 4``.  So the
mapping selects 3, and it does so from geometry that exists before any
policy is evaluated.

⚠ Note the rate depends only on the product ``N·Δt`` — users travel at most
14.3% of a cell radius within a segment at any ``(N, Δt)`` in the sweep — so
this is a live decision **only** at ``Δt ≥ 30 s``.  At the old 1 s clock
every candidate sat below 0.1% and the rule would have returned ``N = 4``
by default.  If the scenario changes, re-derive rather than inherit.
"""


@dataclass(frozen=True)
class DwellConfig:
    """Dwell segment length in steps."""

    steps: int = 3
    """**S, FROZEN 2026-08-23** — selected by the Q-E mapping, not by default.

    It was the sweep's midpoint and a placeholder; it is now the value the
    frozen rule returns (largest ``N`` with re-key rate ≤ 5%; measured 3.8%
    at ``N = 3`` versus 5.4% at ``N = 4``).  Same number, different status —
    and the status is the part that was missing.
    """

    def __post_init__(self) -> None:
        if self.steps < 1:
            raise ValueError("dwell steps must be >= 1")

    def is_boundary(self, step_index: int) -> bool:
        """True on the steps where the pointing is re-anchored."""
        return step_index % self.steps == 0

    def phase(self, step_index: int) -> float:
        """Position within the segment, normalised to [0, 1).

        0.0 marks a boundary step.  Normalised rather than raw so the state
        encoding does not change scale when ``N`` does — P2 sweeps ``N``, and
        a state feature whose range moves with the swept variable would
        confound the sweep with a representation change.
        """
        return float(step_index % self.steps) / float(self.steps)


@dataclass(frozen=True)
class DwellSnapshot:
    """The anchoring in force for one step."""

    step_index: int
    anchor_cell_ids: np.ndarray
    """``(U,)`` the cell each user's ``j = 0`` currently names."""
    neighborhood_cell_ids: np.ndarray
    """``(U, 7)`` anchor plus its six canonical neighbours."""
    phase: float
    is_boundary: bool
    rekeyed_users: np.ndarray
    """``(U,)`` bool — whose anchor actually moved at this boundary."""

    @property
    def rekey_count(self) -> int:
        return int(np.count_nonzero(self.rekeyed_users))


class DwellController:
    """Holds the earth-fixed anchoring between boundaries.

    The controller is deliberately the *only* thing that may change a user's
    anchor, so "the mapping is frozen between boundaries" is a property of
    the code rather than a convention callers must remember.
    """

    def __init__(
        self,
        grid: CellGrid,
        num_users: int,
        config: DwellConfig | None = None,
    ) -> None:
        self.grid = grid
        self.config = config or DwellConfig()
        if num_users < 1:
            raise ValueError("num_users must be >= 1")
        self.num_users = int(num_users)
        self._anchors: np.ndarray | None = None

    def reset(self) -> None:
        self._anchors = None

    @property
    def anchors(self) -> np.ndarray:
        if self._anchors is None:
            raise MCRLContractError("dwell controller has not been stepped yet")
        return self._anchors.copy()

    def step(self, step_index: int, user_xy_km: np.ndarray) -> DwellSnapshot:
        """Advance one step and return the anchoring in force.

        ``user_xy_km`` is ``(U, 2)`` in local east/north km.  It is consulted
        **only** at a boundary; between boundaries the anchoring is frozen no
        matter where the users have drifted, which is what "earth-fixed"
        means.
        """
        positions = np.asarray(user_xy_km, dtype=np.float64)
        if positions.shape != (self.num_users, 2):
            raise MCRLContractError(
                f"user_xy_km must have shape ({self.num_users}, 2), "
                f"got {positions.shape}"
            )
        if step_index < 0:
            raise ValueError("step_index must be non-negative")

        boundary = self.config.is_boundary(step_index)
        if self._anchors is None:
            if not boundary:
                raise MCRLContractError(
                    "the first step of a segment must be a dwell boundary; "
                    f"step {step_index} is not one for N={self.config.steps}"
                )
            previous = None
        else:
            previous = self._anchors

        if boundary:
            anchors = self.grid.anchor_cell_ids(positions)
            rekeyed = (
                np.zeros(self.num_users, dtype=bool)
                if previous is None
                else anchors != previous
            )
            self._anchors = anchors
        else:
            rekeyed = np.zeros(self.num_users, dtype=bool)

        assert self._anchors is not None
        return DwellSnapshot(
            step_index=step_index,
            anchor_cell_ids=self._anchors.copy(),
            neighborhood_cell_ids=self.grid.neighborhood_cell_ids(self._anchors),
            phase=self.config.phase(step_index),
            is_boundary=boundary,
            rekeyed_users=rekeyed,
        )


def segments_per_service_window(
    config: DwellConfig,
    *,
    service_window_s: float,
    time_step_s: float = 1.0,
) -> float:
    """How many dwell segments fit inside one usable service window.

    ``service_window_s`` must be the **≥10° elevation** pass duration,
    measured at 378 s (6.3 min p50) — not the horizon-to-horizon 630 s.
    Using the wrong one overstates the number of segments by 1.7×.
    """
    if service_window_s <= 0.0 or time_step_s <= 0.0:
        raise ValueError("durations must be positive")
    return service_window_s / (config.steps * time_step_s)
