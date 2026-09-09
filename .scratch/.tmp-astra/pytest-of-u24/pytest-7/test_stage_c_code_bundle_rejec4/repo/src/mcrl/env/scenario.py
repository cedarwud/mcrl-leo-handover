"""Episode driver: turns an epoch into a stream of candidate tables.

This is the glue between the layers that are settled — ephemeris, mobility,
D2, dwell, cells, pointing — and :func:`mcrl.env.candidates.resolve_candidates`.
It stops where the physics begins, so probe P1 can run end to end while the
power model is still open.

Two things it does that are easy to get wrong:

**The tracked universe is fixed for the whole episode.**  D2 latches are
per-NORAD state (§4A.6 r7) and must survive a satellite leaving the
four-slot window, so the set of satellites the tracker knows about cannot
change mid-episode.  It is chosen once, by a coarse visibility screen that
also keeps the propagation from being ten thousand satellites wide.

**D2 is primed before step 0.**  A cold latch leaves every user with an
empty mask at the first step of every episode, which under PATCH P-03 would
discard 10% of an ``H = 10`` episode for a reason that is an artefact of the
episode boundary rather than the geometry (W-04).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np

from ..errors import MCRLContractError
from .candidates import StepCandidates, resolve_candidates
from .cells import CellGrid, build_cell_grid
from .constants import (
    AREA_CENTER_LAT_DEG,
    AREA_CENTER_LON_DEG,
    D2_MEASUREMENT_STEP_S,
    D2_SUBSTEPS_PER_DECISION,
    R_E_KM,
    STEPS_PER_EPISODE,
)
from .d2 import D2Config, D2Tracker
from .dwell import DwellConfig, DwellController
from .ephemeris import (
    EphemerisConfig,
    SatelliteSet,
    select_elements,
    shortlist_visible,
    step_times,
)
from .geometry import local_km_to_ecef
from .mobility import MobilityConfig, RandomWanderingUsers
from .tle import TleArchive

NOMINAL_GRID_ALTITUDE_KM: float = 483.0
"""**S, PROVISIONAL** — the altitude that sizes the single earth-fixed lattice.

The corpus median (§5.1 table 5-1).  ⚠ Which altitude sizes the lattice, and
what to do about the footprint mismatch it implies for satellites above and
below it, is decision C-2 in ``docs/CONTROLLER-QUESTIONS-2026-08-22.md``.
"""

SCREEN_MIN_ELEVATION_DEG: float = 0.0
"""**S** — a satellite enters the tracked universe if it clears the horizon."""


@dataclass(frozen=True)
class ScenarioConfig:
    """Everything the driver needs that is not already frozen elsewhere."""

    ephemeris: EphemerisConfig = field(default_factory=EphemerisConfig)
    d2: D2Config = field(default_factory=D2Config)
    dwell: DwellConfig = field(default_factory=DwellConfig)
    mobility: MobilityConfig = field(default_factory=MobilityConfig)
    grid_altitude_km: float = NOMINAL_GRID_ALTITUDE_KM
    steps_per_episode: int = STEPS_PER_EPISODE
    screen_min_elevation_deg: float = SCREEN_MIN_ELEVATION_DEG
    screen_coarse_step_s: float = 30.0

    d2_measurement_step_s: float = D2_MEASUREMENT_STEP_S
    """The clock D2's entry/release conditions and TTT are evaluated on."""

    d2_substeps_per_decision: int = D2_SUBSTEPS_PER_DECISION
    """How many of those fall inside one decision step."""

    def __post_init__(self) -> None:
        if self.d2_substeps_per_decision < 1:
            raise ValueError("d2_substeps_per_decision must be >= 1")
        if self.d2_measurement_step_s <= 0.0:
            raise ValueError("d2_measurement_step_s must be positive")
        implied = self.d2_substeps_per_decision * self.d2_measurement_step_s
        if abs(implied - self.ephemeris.time_step_s) > 1e-9:
            raise MCRLContractError(
                "the two clocks disagree: "
                f"{self.d2_substeps_per_decision} x "
                f"{self.d2_measurement_step_s} s = {implied} s, but the "
                f"decision step is {self.ephemeris.time_step_s} s.  A "
                "sub-step loop that counts on the wrong clock is silent, so "
                "the relation is checked rather than assumed."
            )

    def as_dict(self) -> dict[str, object]:
        return {
            "ephemeris": self.ephemeris.as_dict(),
            "d2": self.d2.as_dict(),
            "dwell": {"steps": self.dwell.steps},
            "mobility": self.mobility.as_dict(),
            "grid_altitude_km": self.grid_altitude_km,
            "steps_per_episode": self.steps_per_episode,
            "screen_min_elevation_deg": self.screen_min_elevation_deg,
            "d2_measurement_step_s": self.d2_measurement_step_s,
            "d2_substeps_per_decision": self.d2_substeps_per_decision,
            "decision_step_s": self.ephemeris.time_step_s,
        }


class ScenarioDriver:
    """One episode at a time: reset to an epoch, then step."""

    def __init__(
        self,
        archive: TleArchive,
        config: ScenarioConfig | None = None,
        grid: CellGrid | None = None,
    ) -> None:
        self.config = config or ScenarioConfig()
        self.archive = archive
        self.grid = grid or build_cell_grid(
            altitude_km=self.config.grid_altitude_km
        )
        self._users = RandomWanderingUsers(self.config.mobility)
        self._dwell = DwellController(
            self.grid, self.config.mobility.num_users, self.config.dwell
        )
        self._tracker: D2Tracker | None = None
        self._satellites: SatelliteSet | None = None
        self._start_utc: dt.datetime | None = None
        self._step_index = 0
        self._frozen_window_norad_ids: np.ndarray | None = None

    # -- episode -----------------------------------------------------------

    def reset(
        self,
        start_utc: dt.datetime,
        rng: np.random.Generator,
        *,
        incumbent_norads: np.ndarray | None = None,
    ) -> StepCandidates:
        """Start an episode at ``start_utc`` and return the step-0 candidates."""
        if start_utc.tzinfo is None:
            raise ValueError("start_utc must be timezone-aware")
        config = self.config
        warmup = config.d2.warmup_steps

        selection = select_elements(
            self.archive,
            start_utc,
            max_age_h=config.ephemeris.max_tle_age_h,
            search_days=config.ephemeris.epoch_search_days,
        )
        everything = SatelliteSet(selection.records)
        duration_s = config.steps_per_episode * config.ephemeris.time_step_s
        shortlist = shortlist_visible(
            everything,
            start_utc,
            duration_s=duration_s,
            coarse_step_s=config.screen_coarse_step_s,
            min_elevation_deg=config.screen_min_elevation_deg,
        )
        if shortlist.size == 0:
            raise MCRLContractError(
                f"no satellite is visible from the service area at {start_utc}"
            )
        self._satellites = everything.subset(shortlist)
        self._start_utc = start_utc
        self._step_index = 0
        self._frozen_window_norad_ids = None

        self._users.reset(rng)
        self._dwell.reset()
        self._tracker = D2Tracker(
            self._satellites.norad_ids, config.mobility.num_users, config.d2
        )

        # Prime the D2 latches over the MEASUREMENT steps immediately BEFORE
        # step 0.  The warm-up window is a TTT-sized quantity (``warmup_steps
        # = max(ttt_steps, 1)``), and TTT now lives on the measurement clock,
        # so the window does too — priming on the decision clock would settle
        # the latches over 47x more time than the TTT they exist to serve.
        origin = start_utc - dt.timedelta(
            seconds=warmup * config.d2_measurement_step_s
        )
        jd, fr = step_times(
            origin, warmup, time_step_s=config.d2_measurement_step_s
        )
        position, velocity = self._satellites.propagate_ecef_state(
            jd, fr, require_all_healthy=False
        )
        users_ecef = self._user_ecef()
        slant, rate = _measure(users_ecef, position, velocity)
        altitude = np.linalg.norm(position, axis=-1) - R_E_KM
        self._tracker.prime(
            slant_range_km=slant,
            altitude_km=altitude,
            range_rate_km_s=rate,
        )
        return self._resolve(incumbent_norads)

    def step(
        self,
        rng: np.random.Generator,
        *,
        incumbent_norads: np.ndarray | None = None,
    ) -> StepCandidates:
        """Advance one slot and return the new candidate table."""
        if self._tracker is None or self._start_utc is None:
            raise MCRLContractError("the driver has not been reset")
        self._step_index += 1
        self._users.step(rng)
        return self._resolve(incumbent_norads)

    def episode(
        self, start_utc: dt.datetime, rng: np.random.Generator
    ):
        """Yield one episode's candidate tables, incumbent-free.

        Convenience for probes with a memoryless reference policy.  A driver
        used with an incumbent-tracking policy must call ``reset``/``step``
        so it can feed the incumbents back in.
        """
        yield self.reset(start_utc, rng)
        for _ in range(self.config.steps_per_episode - 1):
            yield self.step(rng)

    # -- internals ---------------------------------------------------------

    @property
    def step_index(self) -> int:
        return self._step_index

    @property
    def tracked_norad_ids(self) -> np.ndarray:
        if self._satellites is None:
            raise MCRLContractError("the driver has not been reset")
        return self._satellites.norad_ids

    def user_ecef_km(self) -> np.ndarray:
        """``(U, 3)`` — where the users are right now.

        Public because the physics layer needs it for every interference
        term: (3.12b) is evaluated at the victim, not at the service-area
        centre.  ``user_xy_km`` stays on the mobility model; this is the
        same population expressed in the frame the geometry uses.
        """
        return self._user_ecef()

    @property
    def user_xy_km(self) -> np.ndarray:
        """``(U, 2)`` local east/north km — the mobility model's own frame."""
        return self._users.positions_km

    def _user_ecef(self) -> np.ndarray:
        positions = self._users.positions_km
        return local_km_to_ecef(
            positions[:, 0],
            positions[:, 1],
            center_lat_deg=AREA_CENTER_LAT_DEG,
            center_lon_deg=AREA_CENTER_LON_DEG,
        )

    def satellite_ecef_at(self, offset_steps: int) -> dict[int, np.ndarray]:
        """Tracked satellite positions ``offset_steps`` DECISION steps away.

        Negative offsets look backwards, which is what the ``τ`` warm start
        needs: it asks what off-axis angle a link *would have had* when its
        segment started, before the episode began.

        Keyed by NORAD id because the caller works in identities — the
        four-slot window is per user and its ordering is not this array's.
        """
        if self._satellites is None or self._start_utc is None:
            raise MCRLContractError("the driver has not been reset")
        when = self._start_utc + dt.timedelta(
            seconds=(self._step_index + offset_steps)
            * self.config.ephemeris.time_step_s
        )
        jd, fr = step_times(when, 1, time_step_s=self.config.ephemeris.time_step_s)
        position, _ = self._satellites.propagate_ecef_state(
            jd, fr, require_all_healthy=False
        )
        return {
            int(norad): position[index, 0, :]
            for index, norad in enumerate(self._satellites.norad_ids.tolist())
        }

    def _resolve(self, incumbent_norads: np.ndarray | None) -> StepCandidates:
        assert self._tracker is not None and self._satellites is not None
        assert self._start_utc is not None
        config = self.config

        # ── the two clocks meet here ──────────────────────────────────────
        #
        # D2 is advanced once per MEASUREMENT step, the agent decides once per
        # DECISION step.  So one decision costs M tracker updates, evaluated
        # at 640 ms spacing across the interval that ends at this decision
        # point.  That is what makes TTT mean "the condition held for 1280 ms"
        # instead of "the condition held at the last decision", which at
        # Δt = 30 s would have been a degenerate TTT and a 5.9x excursion
        # outside TS 38.331's discrete set.
        #
        # The loop itself is not new: prime() has run exactly this loop since
        # W-04, to settle the latches before step 0.  Sub-stepping is that
        # same loop moved inside the episode.
        substeps = config.d2_substeps_per_decision
        measurement_step = config.d2_measurement_step_s
        decision_time = self._start_utc + dt.timedelta(
            seconds=self._step_index * config.ephemeris.time_step_s
        )
        # The sub-steps END at the decision point: the last measurement is
        # the decision instant itself, so the mask reflects the geometry the
        # action is taken against.
        first = decision_time - dt.timedelta(
            seconds=(substeps - 1) * measurement_step
        )
        jd, fr = step_times(first, substeps, time_step_s=measurement_step)
        position, velocity = self._satellites.propagate_ecef_state(
            jd, fr, require_all_healthy=False
        )
        users_ecef = self._user_ecef()
        altitude = np.linalg.norm(position, axis=-1) - R_E_KM

        # Sub-steps need the slant range only.  The range rate feeds
        # D2Snapshot.range_rate_km_s, which is a §4A.6 contract field and
        # therefore OFF by default since ruling C-1 — so it is computed once,
        # at the decision instant, rather than 47 times.
        #
        # ⚠ That is a live dependency, not just an optimisation: if
        # radial_rate ever returns to the state, the sub-steps must compute
        # rate too, or the snapshot's rate and its latch will describe
        # different instants.
        slant = _slant_only(users_ecef, position)
        _, rate = _measure(users_ecef, position[:, -1:, :], velocity[:, -1:, :])

        base = self._step_index * substeps
        for offset in range(substeps):
            snapshot = self._tracker.update(
                base + offset,
                slant_range_km=slant[:, :, offset],
                altitude_km=altitude[:, offset],
                range_rate_km_s=rate[:, :, 0],
            )
        position = position[:, -1:, :]
        dwell_snapshot = self._dwell.step(
            self._step_index, self._users.positions_km
        )
        incumbents = (
            np.full(config.mobility.num_users, -1, dtype=np.int64)
            if incumbent_norads is None
            else np.asarray(incumbent_norads, dtype=np.int64)
        )
        # B6 freezes the action-slot identities for the same dwell that
        # freezes j -> cell_id.  The D2 tracker above still advances at every
        # 640 ms measurement; only its admission into the four-slot identity
        # window is deferred.  Current eligibility and geometry are refreshed
        # below, so a stale identity cannot remain selectable merely because
        # its name is cached.
        frozen_window = (
            None
            if dwell_snapshot.is_boundary
            else self._frozen_window_norad_ids
        )
        if not dwell_snapshot.is_boundary and frozen_window is None:
            raise MCRLContractError(
                "a non-boundary decision has no frozen candidate window"
            )
        resolved = resolve_candidates(
            step_index=self._step_index,
            user_xy_km=self._users.positions_km,
            user_ecef_km=users_ecef,
            tracked_satellite_ecef_km=position[:, 0, :],
            grid=self.grid,
            dwell=self._dwell,
            d2_snapshot=snapshot,
            dwell_snapshot=dwell_snapshot,
            incumbent_norads=incumbents,
            frozen_window_norad_ids=frozen_window,
        )
        if dwell_snapshot.is_boundary:
            self._frozen_window_norad_ids = resolved.window_norad_ids.copy()
        return resolved


def _slant_only(users_ecef: np.ndarray, position: np.ndarray) -> np.ndarray:
    """``(U, S, T)`` slant range, without the range rate.

    3.6x cheaper than :func:`_measure` at ``T = 47`` because it skips the
    unit vector and the dot product.  D2's entry and release conditions are
    functions of the slant range alone, so the sub-steps need nothing else.

    ⚠ **Only correct while ``radial_rate`` is off the live path** (ruling
    C-1 made the §4A.6 contract block an ablation, default off).  If it
    returns, this function is no longer sufficient and the sub-steps must
    compute the rate as well — otherwise the snapshot's rate would describe
    the decision instant while its latch describes 47 of them.
    """
    delta = position[None, :, :, :] - users_ecef[:, None, None, :]
    return np.sqrt(np.einsum("uskc,uskc->usk", delta, delta))


def _measure(
    users_ecef: np.ndarray, position: np.ndarray, velocity: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """``(U, S, T)`` slant range and signed range rate."""
    delta = position[None, :, :, :] - users_ecef[:, None, None, :]
    slant = np.linalg.norm(delta, axis=-1)
    unit = delta / np.maximum(slant[..., None], 1e-12)
    rate = np.sum(velocity[None, :, :, :] * unit, axis=-1)
    return slant, rate
