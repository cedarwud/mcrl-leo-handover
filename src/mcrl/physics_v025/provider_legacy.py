"""Primitive V0.25 worlds backed by the read-only legacy scenario stack.

The binding deliberately has only one interpretation of a physical beam:
``(NORAD, cell_id)``.  ``cell_id`` is the legacy earth-fixed hex-cell index;
its reuse colour is ``CellGrid.colors[cell_id]``.  Thus a beam/RF-chain is
stable when action slots or a user's seven-cell neighbourhood are re-keyed.

An episode start is drawn exactly as in the C3-S screen: a world seed is
expanded by ``SeedSequence.spawn(4)``, child zero draws a TRAIN epoch and
child one scatters/moves the 100 users.  Element sets are selected once at
that epoch.  For each NORAD the closest epoch in the available files at
date-1/date/date+1 is retained, subject to the legacy 24-hour age ceiling;
the selected TLE is then propagated for the whole tape (it is not reselected
at each boundary).

Returned boundaries contain immutable Python scalars and tuples only.  The
provider may keep NumPy geometry caches, but never exposes an environment,
``SatelliteSet`` or sgp4 ``Satrec`` through the primitive seam.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import datetime as dt
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from mcrl.errors import MCRLContractError
from mcrl.env.constants import AREA_CENTER_LAT_DEG, AREA_CENTER_LON_DEG, R_E_KM
from mcrl.env.d2 import elevation_for_slant_range
from mcrl.env.ephemeris import (
    TEST,
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
    select_elements,
    step_times,
)
from mcrl.env.geometry import angle_between_deg, local_km_to_geodetic
from mcrl.env.link_budget import link_power_factor
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.tle import TleArchive
from mcrl.runtime.training_pipeline import _evaluation_rngs

from .channel import (
    interference_receive_gain_linear,
    keyed_fading_gain,
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
)
from .tapes import PrimitiveBoundary, PrimitiveCandidate, UserLayout


DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle")
CANONICAL_STEPS = 30
_FUTURE_SECONDS = 900.0
_TIME_TOLERANCE_S = 2.0e-10


@dataclass(frozen=True)
class _StepState:
    user_ecef_km: np.ndarray
    user_xy_km: np.ndarray
    norad_ids: np.ndarray
    cell_ids: np.ndarray
    occupied: np.ndarray
    ttt_elapsed: np.ndarray
    reachable: np.ndarray


@dataclass(frozen=True)
class _WorldState:
    start_utc: dt.datetime
    training_seed: int
    grid: object
    steps: tuple[_StepState, ...]
    tracked_norads: np.ndarray
    positions_ecef_km: np.ndarray
    inventory: tuple[tuple[int, int], ...]
    layout: tuple[UserLayout, ...]
    tle_files: tuple[tuple[str, str], ...]


def _readonly(value: np.ndarray) -> np.ndarray:
    result = np.array(value, copy=True)
    result.setflags(write=False)
    return result


def _parse_start(value: dt.datetime | dt.date | str) -> dt.datetime:
    if isinstance(value, str):
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("start_utc must be ISO-8601") from error
    elif isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, dt.date):
        parsed = dt.datetime.combine(value, dt.time(), tzinfo=dt.timezone.utc)
    else:
        raise TypeError("start_utc must be a date, datetime, ISO string, or None")
    if parsed.tzinfo is None:
        raise ValueError("start_utc must be timezone-aware")
    return parsed.astimezone(dt.timezone.utc)


class _TrainOnlyArchive(TleArchive):
    """Archive view that fails closed before opening a TEST daily file."""

    def __init__(self, root: str | Path) -> None:
        super().__init__(root)
        split = BlockAlternatingSplit.for_archive(self)
        self._test_dates = frozenset(split.available_dates(self, TEST))

    def load(self, file_date: dt.date):
        if file_date in self._test_dates:
            raise MCRLContractError(
                f"refusing to read TEST TLE date {file_date} through TRAIN provider"
            )
        return super().load(file_date)


class LegacyWorldProvider:
    """Real TRAIN-only primitive provider using the legacy world generator.

    ``start_utc`` is a test/audit seam.  Normal worlds leave it unset and the
    legacy TRAIN sampler derives the epoch from ``world_seed``.  A supplied
    TEST or embargo date is rejected before a TLE file is loaded.
    """

    _STATE_CACHE: OrderedDict[
        tuple[str, str | None, int, int], _WorldState
    ] = OrderedDict()
    _STATE_CACHE_SIZE = 2

    def __init__(
        self,
        *,
        tle_root: str | Path = DEFAULT_TLE_ROOT,
        start_utc: dt.datetime | dt.date | str | None = None,
        steps: int = CANONICAL_STEPS,
    ) -> None:
        if type(steps) is not int or steps < 1:
            raise ValueError("steps must be a positive exact integer")
        self.tle_root = Path(tle_root).expanduser()
        self.requested_steps = steps
        # Controller T6: a shortened rehearsal truncates a canonical world;
        # it must never change the 30-step shortlist/inventory universe.
        self.steps = CANONICAL_STEPS
        self._forced_start = None if start_utc is None else _parse_start(start_utc)
        self._archive = _TrainOnlyArchive(self.tle_root)
        self._split = BlockAlternatingSplit.for_archive(self._archive)
        if self._forced_start is not None:
            part = self._split.part_for(self._forced_start.date())
            if part != TRAIN or not self._archive.has(self._forced_start.date()):
                raise MCRLContractError(
                    f"legacy provider is TRAIN-only; {self._forced_start.date()} is {part}"
                )
        self._world_seed: int | None = None
        self._world: _WorldState | None = None
        self._boundary_cache: dict[tuple[int, int], PrimitiveBoundary] = {}

    def _cache_key(self, world_seed: int) -> tuple[str, str | None, int, int]:
        return (
            str(self.tle_root.resolve()),
            None if self._forced_start is None else self._forced_start.isoformat(),
            int(world_seed),
            self.steps,
        )

    def _start_for(self, world_seed: int) -> dt.datetime:
        if self._forced_start is not None:
            return self._forced_start
        env_rng = _evaluation_rngs(world_seed)[0]
        sampler = EpisodeStartSampler.for_archive(
            self._archive, self._split, TRAIN, time_step_s=DECISION_INTERVAL_S
        )
        result = sampler.draw(env_rng)
        if self._split.part_for(result.date()) != TRAIN:
            raise MCRLContractError("TRAIN sampler returned a non-TRAIN date")
        return result

    def _ensure(self, world_seed: int) -> _WorldState:
        seed = int(world_seed)
        if seed != world_seed or seed < 0:
            raise MCRLContractError("world_seed must be a nonnegative exact integer")
        if self._world is not None:
            if self._world_seed != seed:
                raise MCRLContractError("one provider instance binds exactly one world seed")
            return self._world

        cache_key = self._cache_key(seed)
        cached = self._STATE_CACHE.get(cache_key)
        if cached is not None:
            self._STATE_CACHE.move_to_end(cache_key)
            self._world_seed = seed
            self._world = cached
            return cached

        start = self._start_for(seed)
        # Recreate both streams so the epoch draw and user scatter have the
        # exact C3-S ancestry.  The epoch draw on child zero is intentionally
        # repeated before child one is handed to ScenarioDriver.
        env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
        if self._forced_start is None:
            sampled = EpisodeStartSampler.for_archive(
                self._archive, self._split, TRAIN,
                time_step_s=DECISION_INTERVAL_S,
            ).draw(env_rng)
            if sampled != start:
                raise RuntimeError("legacy TRAIN epoch replay drifted")

        config = ScenarioConfig(
            mobility=MobilityConfig(num_users=100),
            steps_per_episode=self.steps,
        )
        driver = ScenarioDriver(self._archive, config)
        decisions = []
        candidate = driver.reset(start, mobility_rng)
        selection = select_elements(
            self._archive,
            start,
            max_age_h=config.ephemeris.max_tle_age_h,
            search_days=config.ephemeris.epoch_search_days,
        )
        tle_files = tuple(
            (
                self._archive.load(file_date).path.name,
                self._archive.load(file_date).sha256,
            )
            for file_date in selection.source_dates
        )
        for index in range(self.steps):
            if index:
                candidate = driver.step(mobility_rng)
            flat_norads = np.repeat(candidate.window_norad_ids, 7, axis=1)
            flat_cells = np.tile(
                np.stack([table.cell_ids for table in candidate.slot_tables]),
                (1, 1),
            )
            decisions.append(
                _StepState(
                    _readonly(driver.user_ecef_km()),
                    _readonly(driver.user_xy_km),
                    _readonly(flat_norads),
                    _readonly(flat_cells),
                    _readonly(np.repeat(candidate.slot_occupied, 7, axis=1)),
                    _readonly(
                        np.repeat(
                            np.stack(
                                [assignment.ttt_counter for assignment in candidate.assignments]
                            ),
                            7,
                            axis=1,
                        )
                    ),
                    _readonly(candidate.cell_reachable.reshape(100, -1)),
                )
            )

        satellites = driver._satellites
        if satellites is None:  # pragma: no cover - guarded by reset
            raise RuntimeError("legacy scenario did not install a satellite set")
        tracked = satellites.norad_ids
        future_samples = int(math.ceil(_FUTURE_SECONDS / D2_MEASUREMENT_STEP_S))
        tape_samples = (self.steps - 1) * D2_SUBINTERVALS + D2_SUBINTERVALS + 1
        jd, fr = step_times(
            start,
            tape_samples + future_samples,
            time_step_s=D2_MEASUREMENT_STEP_S,
        )
        positions = satellites.propagate_ecef(jd, fr, require_all_healthy=True)
        if not np.all(np.isfinite(positions)):
            raise MCRLContractError("sgp4 produced a non-finite ECEF primitive")

        visible_satellites: set[int] = set()
        for step_index, state in enumerate(decisions):
            begin = step_index * D2_SUBINTERVALS
            block = positions[:, begin : begin + D2_SUBINTERVALS + 1, :]
            # Chunk users to avoid a (100,S,48,3) temporary.
            for users in np.array_split(state.user_ecef_km, 10):
                delta = block[None, :, :, :] - users[:, None, None, :]
                slant = np.linalg.norm(delta, axis=-1)
                up = users / np.linalg.norm(users, axis=1, keepdims=True)
                sine = np.einsum("ustc,uc->ust", delta, up) / slant
                seen = np.any(
                    sine >= math.sin(math.radians(MINIMUM_ELEVATION_DEG)),
                    axis=(0, 2),
                )
                visible_satellites.update(int(value) for value in tracked[seen])

        # A chain is the legacy global earth-fixed cell id.  Enumerate every
        # cell family actually addressable by this world's moving users, then
        # pair that frozen set with every satellite passing the exact 10° scan.
        chains = sorted(
            {
                int(cell)
                for state in decisions
                for cell in state.cell_ids.ravel().tolist()
                if int(cell) >= 0
            }
        )
        inventory = tuple(
            (norad, chain)
            for norad in sorted(visible_satellites)
            for chain in chains
        )
        if not inventory:
            raise MCRLContractError("canonical TRAIN world has an empty inventory")

        xy0 = decisions[0].user_xy_km
        lat, lon = local_km_to_geodetic(
            xy0[:, 0], xy0[:, 1],
            center_lat_deg=AREA_CENTER_LAT_DEG,
            center_lon_deg=AREA_CENTER_LON_DEG,
        )
        layout = tuple(
            UserLayout(index, float(lat[index]), float(lon[index]))
            for index in range(100)
        )
        self._world_seed = seed
        self._world = _WorldState(
            start,
            seed,
            driver.grid,
            tuple(decisions),
            _readonly(tracked),
            _readonly(positions),
            inventory,
            layout,
            tle_files,
        )
        self._STATE_CACHE[cache_key] = self._world
        self._STATE_CACHE.move_to_end(cache_key)
        while len(self._STATE_CACHE) > self._STATE_CACHE_SIZE:
            self._STATE_CACHE.popitem(last=False)
        # ``satellites`` and ``driver`` now fall out of scope; no Satrec is
        # retained by the provider or any returned primitive object.
        return self._world

    def cluster_identity(self, *, world_seed: int) -> tuple[str, int]:
        world = self._ensure(world_seed)
        return world.start_utc.date().isoformat(), world.training_seed

    def tle_binding(self, *, world_seed: int) -> tuple[tuple[str, str], ...]:
        """Daily filename/SHA-256 inputs used by nearest-epoch selection."""

        return self._ensure(world_seed).tle_files

    def user_layout_at_step(
        self, *, world_seed: int, step_index: int
    ) -> tuple[UserLayout, ...]:
        """Audit-only per-step user positions; users are fixed within a step."""

        world = self._ensure(world_seed)
        self._indices(world, step_index, 0)
        xy = world.steps[step_index].user_xy_km
        lat, lon = local_km_to_geodetic(
            xy[:, 0],
            xy[:, 1],
            center_lat_deg=AREA_CENTER_LAT_DEG,
            center_lon_deg=AREA_CENTER_LON_DEG,
        )
        return tuple(
            UserLayout(index, float(lat[index]), float(lon[index]))
            for index in range(100)
        )

    def user_layout(self, *, world_seed: int) -> Iterable[UserLayout]:
        return self._ensure(world_seed).layout

    def inventory(self, *, world_seed: int) -> Iterable[tuple[int, int]]:
        return self._ensure(world_seed).inventory

    def satellite_ecef_km(
        self, *, world_seed: int, step_index: int, boundary_index: int
    ) -> tuple[tuple[int, tuple[float, float, float]], ...]:
        """Audit seam returning detached ECEF positions for the exact boundary."""

        world = self._ensure(world_seed)
        self._indices(world, step_index, boundary_index)
        time_index = step_index * D2_SUBINTERVALS + boundary_index
        return tuple(
            (int(norad), tuple(float(value) for value in world.positions_ecef_km[row, time_index]))
            for row, norad in enumerate(world.tracked_norads.tolist())
        )

    def _indices(self, world: _WorldState, step: int, boundary: int) -> None:
        if type(step) is not int or not 0 <= step < len(world.steps):
            raise MCRLContractError("step_index is outside the prepared canonical world")
        if type(boundary) is not int or not 0 <= boundary <= D2_SUBINTERVALS:
            raise MCRLContractError("boundary_index must be in 0..47")

    def boundary(
        self,
        *,
        world_seed: int,
        step_index: int,
        boundary_index: int,
        absolute_time_s: float,
    ) -> PrimitiveBoundary:
        world = self._ensure(world_seed)
        self._indices(world, step_index, boundary_index)
        expected = step_index * DECISION_INTERVAL_S + boundary_index * D2_MEASUREMENT_STEP_S
        if not math.isclose(float(absolute_time_s), expected, rel_tol=0.0, abs_tol=_TIME_TOLERANCE_S):
            raise MCRLContractError("absolute boundary time disagrees with t+k*0.640 s")
        cache_key = (step_index, boundary_index)
        cached = self._boundary_cache.get(cache_key)
        if cached is not None:
            return cached

        state = world.steps[step_index]
        time_index = step_index * D2_SUBINTERVALS + boundary_index
        positions = world.positions_ecef_km[:, time_index, :]
        column_of = {int(n): i for i, n in enumerate(world.tracked_norads.tolist())}
        grid = world.grid
        peak_receive = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
        absolute_ns = int(round(expected * 1.0e9))

        rows: list[PrimitiveCandidate] = []
        for user in range(100):
            user_ecef = state.user_ecef_km[user]
            by_identity = {
                (int(norad), int(cell)): (
                    bool(occupied), int(ttt_elapsed), bool(reachable)
                )
                for norad, cell, occupied, ttt_elapsed, reachable in zip(
                    state.norad_ids[user].tolist(),
                    state.cell_ids[user].tolist(),
                    state.occupied[user].tolist(),
                    state.ttt_elapsed[user].tolist(),
                    state.reachable[user].tolist(),
                )
                if int(norad) >= 0 and int(cell) >= 0
            }
            identities = [
                (norad, cell, *by_identity[(norad, cell)])
                for norad, cell in sorted(by_identity)
            ]
            candidate_norads = sorted({identity[0] for identity in identities})
            sat_rows = np.asarray([column_of[norad] for norad in candidate_norads], dtype=np.int64)
            sat_positions = positions[sat_rows]
            delta = sat_positions - user_ecef
            slants = np.linalg.norm(delta, axis=1)
            up = user_ecef / np.linalg.norm(user_ecef)
            elevations = np.degrees(np.arcsin(np.clip((delta @ up) / slants, -1.0, 1.0)))
            sat_index = {norad: index for index, norad in enumerate(candidate_norads)}
            fading = np.asarray(
                [
                    keyed_fading_gain(
                        world=int(world_seed), user=user, norad=norad,
                        absolute_time_ns=absolute_ns,
                        elevation_deg=float(elevations[index]),
                    )
                    for index, norad in enumerate(candidate_norads)
                ],
                dtype=np.float64,
            )
            remaining: dict[tuple[int, bool], tuple[float, float]] = {}

            row_norads = np.asarray([row[0] for row in identities], dtype=np.int64)
            row_cells = np.asarray([row[1] for row in identities], dtype=np.int64)
            wanted_columns = np.asarray([sat_index[int(n)] for n in row_norads], dtype=np.int64)
            wanted_positions = sat_positions[wanted_columns]
            centres = grid.centers_ecef_km[row_cells]
            direct_angles = angle_between_deg(wanted_positions, centres, user_ecef)
            direct_tx = transmit_gain_linear(direct_angles)
            direct_path = link_power_factor(
                slants[wanted_columns], elevations[wanted_columns],
                np.full(len(identities), peak_receive),
            )

            # Cross rows use the aggressor's beam pointed at the victim row's
            # earth-fixed cell.  This is one co-colour beam per NORAD, so no
            # across-beam aggregation is hidden in the NORAD-keyed map.
            other_positions = np.broadcast_to(
                sat_positions[None, :, :], (len(identities), len(candidate_norads), 3)
            )
            cross_angles = angle_between_deg(
                other_positions,
                centres[:, None, :],
                np.broadcast_to(
                    user_ecef, (len(identities), len(candidate_norads), 3)
                ),
            )
            cross_tx = transmit_gain_linear(cross_angles)
            separations = angle_between_deg(
                np.broadcast_to(user_ecef, other_positions.shape),
                wanted_positions[:, None, :],
                other_positions,
            )
            receive = interference_receive_gain_linear(
                separations, same_satellite=False
            )
            cross_path = link_power_factor(
                np.broadcast_to(slants, receive.shape),
                np.broadcast_to(elevations, receive.shape),
                receive,
            )
            cross_gain = cross_tx * cross_path

            for row_index, (norad, cell, occupied0, ttt0, _reachable0) in enumerate(identities):
                column = wanted_columns[row_index]
                satellite = wanted_positions[row_index]
                slant = float(slants[column])
                elevation = float(elevations[column])
                nominal = float(direct_tx[row_index] * direct_path[row_index])
                visible = elevation >= MINIMUM_ELEVATION_DEG
                d2_eligible = self._d2_at(
                    world,
                    state,
                    user,
                    column_of[norad],
                    step_index * D2_SUBINTERVALS,
                    boundary_index,
                    latched0=occupied0,
                    ttt_elapsed0=ttt0,
                )

                cross_nominal = tuple(
                    (aggressor, float(cross_gain[row_index, other_index]))
                    for other_index, aggressor in enumerate(candidate_norads)
                    if aggressor != norad
                )
                cross_realised = tuple(
                    (
                        aggressor,
                        float(cross_gain[row_index, other_index] * fading[other_index]),
                    )
                    for other_index, aggressor in enumerate(candidate_norads)
                    if aggressor != norad
                )

                altitude = float(np.linalg.norm(satellite) - R_E_KM)
                entry_elevation = elevation_for_slant_range(
                    D2_THRESHOLD_KM - D2_HYSTERESIS_KM, altitude
                )
                remaining_key = (norad, d2_eligible)
                if remaining_key not in remaining:
                    remaining[remaining_key] = self._remaining(
                        world,
                        state,
                        user,
                        column_of[norad],
                        time_index,
                        visible=visible,
                        d2_eligible=d2_eligible,
                    )
                remaining_visibility, remaining_d2 = remaining[remaining_key]
                rows.append(
                    PrimitiveCandidate(
                        user,
                        (norad, cell),
                        int(grid.colors[cell]),
                        elevation,
                        float(entry_elevation),
                        slant,
                        slant,
                        visible,
                        d2_eligible,
                        nominal,
                        nominal * float(fading[column]),
                        cross_nominal,
                        cross_realised,
                        remaining_visibility,
                        remaining_d2,
                    )
                )

        result = PrimitiveBoundary(float(absolute_time_s), tuple(rows))
        self._boundary_cache[cache_key] = result
        return result

    def _remaining(
        self,
        world: _WorldState,
        state: _StepState,
        user: int,
        sat_column: int,
        time_index: int,
        *,
        visible: bool,
        d2_eligible: bool,
    ) -> tuple[float, float]:
        future = world.positions_ecef_km[sat_column, time_index:, :]
        user_ecef = state.user_ecef_km[user]
        delta = future - user_ecef
        slant = np.linalg.norm(delta, axis=1)
        up = user_ecef / np.linalg.norm(user_ecef)
        elevation = np.degrees(np.arcsin(np.clip((delta @ up) / slant, -1.0, 1.0)))

        def duration(mask: np.ndarray, active: bool) -> float:
            if not active:
                return 0.0
            failures = np.flatnonzero(~mask)
            count = int(failures[0]) if failures.size else len(mask) - 1
            return float(count * D2_MEASUREMENT_STEP_S)

        visibility_s = duration(elevation >= MINIMUM_ELEVATION_DEG, visible)
        d2_s = duration(
            slant - D2_HYSTERESIS_KM <= D2_THRESHOLD_KM,
            d2_eligible,
        )
        return visibility_s, d2_s

    def _d2_at(
        self,
        world: _WorldState,
        state: _StepState,
        user: int,
        sat_column: int,
        step_start_index: int,
        boundary_index: int,
        *,
        latched0: bool,
        ttt_elapsed0: int,
    ) -> bool:
        """Advance the legacy candidate-side Schmitt latch within one step."""

        if boundary_index == 0:
            return bool(latched0)
        positions = world.positions_ecef_km[
            sat_column,
            step_start_index : step_start_index + boundary_index + 1,
            :,
        ]
        slant = np.linalg.norm(positions - state.user_ecef_km[user], axis=1)
        latched = bool(latched0)
        elapsed = int(ttt_elapsed0)
        active = bool(slant[0] + D2_HYSTERESIS_KM < D2_THRESHOLD_KM)
        for distance in slant[1:]:
            entering = bool(distance + D2_HYSTERESIS_KM < D2_THRESHOLD_KM)
            releasing = bool(distance - D2_HYSTERESIS_KM > D2_THRESHOLD_KM)
            if entering:
                elapsed = elapsed + 1 if active else 0
            else:
                elapsed = 0
            active = entering
            if entering and elapsed >= 2:
                latched = True
            if releasing:
                latched = False
        return latched


def factory() -> LegacyWorldProvider:
    """CLI-compatible zero-argument provider factory."""

    return LegacyWorldProvider()


__all__ = ["CANONICAL_STEPS", "DEFAULT_TLE_ROOT", "LegacyWorldProvider", "factory"]
