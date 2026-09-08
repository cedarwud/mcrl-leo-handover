"""Primitive V0.25 worlds backed by the read-only legacy scenario stack.

The binding deliberately has only one interpretation of a physical beam:
``(NORAD, cell_id)``.  ``cell_id`` is the legacy earth-fixed hex-cell index;
its reuse colour is ``CellGrid.colors[cell_id]``.  Thus a beam identity is
stable when action slots or a user's seven-cell neighbourhood are re-keyed.

An episode start is drawn exactly as in the C3-S screen: a world seed is
expanded by ``SeedSequence.spawn(4)``, child zero draws a TRAIN epoch and
child one scatters/moves the 100 users.  Element sets are selected once at
that epoch.  For each NORAD the closest epoch in the available files at
date-1/date/date+1 is retained, subject to the legacy 24-hour age ceiling;
the selected TLE is then propagated for the whole tape (it is not reselected
at each boundary).

The legacy D2/TTT history uses 47 samples spanning 46 measurement intervals
backward and ending at each decision instant.  V0.25 integration instead
uses 48 boundaries spanning 47 intervals forward from that instant.  The
provider takes boundary-zero eligibility from the legacy backward history,
then advances it only for k=1..47; no forward sample can admit a candidate at
the decision instant.

Engine boundaries are immutable NumPy arrays.  Python candidate objects are
created only by the audit view.  No environment, ``SatelliteSet``, sgp4
``Satrec``, or process-global world cache crosses the primitive seam.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import hashlib
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from mcrl.errors import MCRLContractError
from mcrl.env.constants import AREA_CENTER_LAT_DEG, AREA_CENTER_LON_DEG, R_E_KM
from mcrl.env.d2 import elevation_for_slant_range
from mcrl.env.action_contract import NUM_BEAM_SLOTS, NUM_SATELLITE_SLOTS
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
    scintillation_loss_db,
    transmit_gain_linear,
)
from .constants_v025 import (
    D2_HYSTERESIS_KM,
    D2_MEASUREMENT_STEP_S,
    D2_SUBINTERVALS,
    D2_THRESHOLD_KM,
    D2_TTT_S,
    DECISION_INTERVAL_S,
    IDENTITY_REFRESH_DECISIONS,
    MINIMUM_ALTITUDE_KM,
    MINIMUM_ELEVATION_DEG,
    RX_GAIN_MAX_DBI,
    constant_manifest,
)
from .tapes import (
    PrimitiveBoundary,
    PrimitiveStepArrays,
    ProviderAttestation,
    UserLayout,
    canonical_bytes,
)


DEFAULT_TLE_ROOT = Path("~/demo/tle_data/starlink/tle")
CANONICAL_STEPS = 30
FORECAST_STEPS = 3
CANONICAL_TAPE_STEPS = CANONICAL_STEPS + FORECAST_STEPS
_FUTURE_SECONDS = 900.0
_FUTURE_INTERVALS = int(math.ceil(_FUTURE_SECONDS / D2_MEASUREMENT_STEP_S))
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
    legacy_mask: np.ndarray


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
        self._opened_dates: set[dt.date] = set()

    def load(self, file_date: dt.date):
        if file_date in self._test_dates:
            raise MCRLContractError(
                f"refusing to read TEST TLE date {file_date} through TRAIN provider"
            )
        daily = super().load(file_date)
        self._opened_dates.add(file_date)
        return daily

    @property
    def opened_dates(self) -> tuple[dt.date, ...]:
        return tuple(sorted(self._opened_dates))

    def index_sha256(self) -> str:
        """Bind the frozen archive index without reading TEST file contents."""

        return hashlib.sha256(
            canonical_bytes(
                [
                    [file_date.isoformat(), path.name]
                    for file_date, path in sorted(self._paths.items())
                ]
            )
        ).hexdigest()


class LegacyWorldProvider:
    """Real TRAIN-only primitive provider using the legacy world generator.

    ``start_utc`` is a test/audit seam.  Normal worlds leave it unset and the
    legacy TRAIN sampler derives the epoch from ``world_seed``.  A supplied
    TEST or embargo date is rejected before a TLE file is loaded.
    """

    def __init__(
        self,
        *,
        tle_root: str | Path = DEFAULT_TLE_ROOT,
        start_utc: dt.datetime | dt.date | str | None = None,
        steps: int = CANONICAL_STEPS,
        role: str = "physics-matrix",
        learner_seed: int | None = None,
    ) -> None:
        if type(steps) is not int or steps < 1:
            raise ValueError("steps must be a positive exact integer")
        self.tle_root = Path(tle_root).expanduser()
        self.requested_steps = steps
        if not role:
            raise ValueError("role must be nonempty")
        if learner_seed is not None and (type(learner_seed) is not int or learner_seed < 0):
            raise ValueError("learner_seed must be None or a nonnegative exact integer")
        if role == "physics-matrix" and learner_seed is not None:
            raise MCRLContractError("the learner-free physics matrix must attest learner_seed=None")
        self.role = role
        self.learner_seed = learner_seed
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
        self._time_origin_s: float | None = None

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

        start = self._start_for(seed)
        # Child zero owns the exact TRAIN epoch draw in _start_for; child one
        # owns mobility.  There is deliberately no fresh-stream replay check:
        # such a check is true by construction and cannot detect seed drift.
        _env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)

        mobility = MobilityConfig(num_users=MobilityConfig().num_users)
        config = ScenarioConfig(
            mobility=mobility,
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
        for index in range(CANONICAL_TAPE_STEPS):
            if index:
                candidate = driver.step(mobility_rng)
            flat_norads = np.repeat(
                candidate.window_norad_ids, NUM_BEAM_SLOTS, axis=1
            )
            # SlotTable intentionally erases identities when any mask term is
            # false.  The provider must preserve them, so use the frozen dwell
            # neighbourhood and carry each predicate separately.
            flat_cells = np.tile(
                candidate.dwell.neighborhood_cell_ids,
                (1, NUM_SATELLITE_SLOTS),
            )
            decisions.append(
                _StepState(
                    _readonly(driver.user_ecef_km()),
                    _readonly(driver.user_xy_km),
                    _readonly(flat_norads),
                    _readonly(flat_cells),
                    _readonly(
                        np.repeat(
                            candidate.slot_occupied, NUM_BEAM_SLOTS, axis=1
                        )
                    ),
                    _readonly(
                        np.repeat(
                            np.stack(
                                [assignment.ttt_counter for assignment in candidate.assignments]
                            ),
                            NUM_BEAM_SLOTS,
                            axis=1,
                        )
                    ),
                    _readonly(
                        candidate.cell_reachable.reshape(
                            config.mobility.num_users, -1
                        )
                    ),
                    _readonly(candidate.masks),
                )
            )

        satellites = driver._satellites
        if satellites is None:  # pragma: no cover - guarded by reset
            raise RuntimeError("legacy scenario did not install a satellite set")
        tracked = satellites.norad_ids
        tape_samples = (
            (CANONICAL_TAPE_STEPS - 1) * D2_SUBINTERVALS + D2_SUBINTERVALS + 1
        )
        jd, fr = step_times(
            start,
            tape_samples + _FUTURE_INTERVALS,
            time_step_s=D2_MEASUREMENT_STEP_S,
        )
        positions = satellites.propagate_ecef(jd, fr, require_all_healthy=True)
        self._validate_propagation(positions)

        # Hardware identities are only the pairs realised by at least one
        # legal legacy action at a canonical decision instant.  This is the
        # union of actual masks, never NORAD x cell Cartesian multiplication.
        inventory = tuple(
            sorted(
                {
                    (int(norad), int(cell))
                    for state in decisions[:CANONICAL_STEPS]
                    for norad, cell, legal in zip(
                        state.norad_ids.ravel().tolist(),
                        state.cell_ids.ravel().tolist(),
                        state.legacy_mask.ravel().tolist(),
                        strict=True,
                    )
                    if bool(legal) and int(norad) >= 0 and int(cell) >= 0
                }
            )
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
            for index in range(config.mobility.num_users)
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
        # ``satellites`` and ``driver`` now fall out of scope; no Satrec is
        # retained by the provider or any returned primitive object.
        return self._world

    @staticmethod
    def _validate_propagation(positions: np.ndarray) -> None:
        """Fail closed on NaN and finite sub-surface sgp4 garbage."""

        values = np.asarray(positions, dtype=np.float64)
        if values.ndim != 3 or values.shape[-1] != 3 or not np.all(np.isfinite(values)):
            raise MCRLContractError("sgp4 produced a non-finite ECEF primitive")
        altitude = np.linalg.norm(values, axis=-1) - R_E_KM
        if np.any(altitude < 0.0):
            raise MCRLContractError("sgp4 produced a finite sub-surface primitive")

    def cluster_identity(self, *, world_seed: int) -> tuple[str, int]:
        world = self._ensure(world_seed)
        return world.start_utc.date().isoformat(), world.training_seed

    def tle_binding(self, *, world_seed: int) -> tuple[tuple[str, str], ...]:
        """Daily filename/SHA-256 inputs used by nearest-epoch selection."""

        return self._ensure(world_seed).tle_files

    def start_utc(self, *, world_seed: int) -> dt.datetime:
        """Exact sampled instant, including the independently drawn offset."""

        return self._ensure(world_seed).start_utc

    def split_binding(self) -> tuple[str, str]:
        """Source file/hash for the inherited block-alternating split rule."""

        import mcrl.env.ephemeris as ephemeris

        path = Path(ephemeris.__file__).resolve()
        return path.name, hashlib.sha256(path.read_bytes()).hexdigest()

    def attestation(self, *, world_seed: int, steps: int) -> ProviderAttestation:
        """Issue the complete stage-4b identity for one retained tape prefix."""

        if type(steps) is not int or not 1 <= steps <= CANONICAL_TAPE_STEPS:
            raise MCRLContractError("attested steps are outside the 30+3 canonical tape")
        world = self._ensure(world_seed)
        realised_split = self._split.part_for(world.start_utc.date())
        opened_dates = self._archive.opened_dates
        if realised_split != TRAIN or any(
            self._split.part_for(file_date) == TEST for file_date in opened_dates
        ):
            raise MCRLContractError("provider attestation split mismatch")
        split_file, split_digest = self.split_binding()
        executed = min(steps, CANONICAL_STEPS)
        forecast = steps - executed
        return ProviderAttestation(
            split=realised_split,
            expected_split=TRAIN,
            split_identity=tuple(sorted(self._split.as_dict().items())),
            split_rule_file=split_file,
            split_rule_sha256=split_digest,
            start_utc=world.start_utc.isoformat(),
            tle_files=world.tle_files,
            opened_tle_dates=tuple(date.isoformat() for date in opened_dates),
            opened_tle_splits=tuple(
                (date.isoformat(), self._split.part_for(date)) for date in opened_dates
            ),
            archive_sha256=self._archive.index_sha256(),
            provider_source_file=Path(__file__).name,
            provider_source_sha256=self.provider_source_sha256(),
            role=self.role,
            learner_seed=self.learner_seed,
            world_seed=int(world_seed),
            mobility_stream_identity=(
                f"numpy.SeedSequence({int(world_seed)}).spawn(4)[1]:mobility"
            ),
            fading_stream_identity=(
                f"sha256-keyed:{int(world_seed)}|user|norad|absolute_time_ns|component"
            ),
            candidate_refresh_period_n=IDENTITY_REFRESH_DECISIONS,
            executed_steps=executed,
            forecast_steps=forecast,
            production_factory="mcrl.physics_v025.provider_legacy.factory",
            date_panel_policy=(
                "allocation manifest must assert role-wise date disjointness before units open"
            ),
            primary_resampling=(
                "one-way bootstrap over TLE dates"
                if self.learner_seed is None
                else "two-way pigeonhole bootstrap over TLE dates x learner seeds"
            ),
            world_pooling="pool worlds within each TLE-date x learner-seed cell",
        )

    def step_user_layouts(
        self, *, world_seed: int, steps: int
    ) -> tuple[tuple[UserLayout, ...], ...]:
        world = self._ensure(world_seed)
        if type(steps) is not int or not 1 <= steps <= CANONICAL_TAPE_STEPS:
            raise MCRLContractError("step layout count is outside the canonical world")
        return tuple(
            self.user_layout_at_step(world_seed=world_seed, step_index=index)
            for index in range(steps)
        )

    @staticmethod
    def _nominal_path_without_scintillation(
        slant_km: np.ndarray,
        elevation_deg: np.ndarray,
        receive_gain: np.ndarray,
    ) -> np.ndarray:
        """Legacy path factor with L_c removed; keyed fading owns L_c once."""

        legacy = link_power_factor(slant_km, elevation_deg, receive_gain)
        return legacy * 10.0 ** (scintillation_loss_db(elevation_deg) / 10.0)

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
            for index in range(xy.shape[0])
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

    @staticmethod
    def _row_metadata(state: _StepState) -> tuple[np.ndarray, ...]:
        present = (state.norad_ids >= 0) & (state.cell_ids >= 0)
        row_user, row_action = np.nonzero(present)
        identities = np.stack(
            (state.norad_ids[present], state.cell_ids[present]), axis=1
        ).astype(np.int64)
        keys = [
            (int(row_user[index]), int(identity[0]), int(identity[1]))
            for index, identity in enumerate(identities)
        ]
        if len(keys) != len(set(keys)):
            raise MCRLContractError("candidate action rows contain duplicate identities")
        return (
            row_user.astype(np.int64),
            row_action.astype(np.int64),
            identities,
            (row_action // NUM_BEAM_SLOTS).astype(np.int64),
        )

    def _forward_d2_slots(
        self,
        *,
        world: _WorldState,
        state: _StepState,
        step_index: int,
        position_columns: dict[int, int],
    ) -> np.ndarray:
        """Advance from the legacy decision latch; boundary zero never looks ahead."""

        users = state.user_ecef_km.shape[0]
        result = np.zeros((48, users, NUM_SATELLITE_SLOTS), dtype=bool)
        result[0] = state.occupied[:, ::NUM_BEAM_SLOTS]
        elapsed = state.ttt_elapsed[:, ::NUM_BEAM_SLOTS].astype(np.int64).copy()
        active = np.zeros((users, NUM_SATELLITE_SLOTS), dtype=bool)
        threshold_steps = int(round(D2_TTT_S / D2_MEASUREMENT_STEP_S))
        if not math.isclose(
            threshold_steps * D2_MEASUREMENT_STEP_S,
            D2_TTT_S,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise MCRLContractError("D2 TTT is not an integer measurement count")
        begin = step_index * D2_SUBINTERVALS
        slot_norads = state.norad_ids[:, ::NUM_BEAM_SLOTS]
        for boundary in range(48):
            for user in range(users):
                for slot in range(NUM_SATELLITE_SLOTS):
                    norad = int(slot_norads[user, slot])
                    if norad < 0:
                        continue
                    position = world.positions_ecef_km[
                        position_columns[norad], begin + boundary
                    ]
                    distance = float(np.linalg.norm(position - state.user_ecef_km[user]))
                    altitude = float(np.linalg.norm(position) - R_E_KM)
                    entering = (
                        distance + D2_HYSTERESIS_KM < D2_THRESHOLD_KM
                        and altitude >= MINIMUM_ALTITUDE_KM
                    )
                    if boundary == 0:
                        active[user, slot] = entering
                        continue
                    releasing = distance - D2_HYSTERESIS_KM > D2_THRESHOLD_KM
                    elapsed[user, slot] = (
                        elapsed[user, slot] + 1
                        if entering and active[user, slot]
                        else 0
                    )
                    active[user, slot] = entering
                    latched = bool(result[boundary - 1, user, slot])
                    if entering and elapsed[user, slot] >= threshold_steps:
                        latched = True
                    if releasing or altitude < MINIMUM_ALTITUDE_KM:
                        latched = False
                    result[boundary, user, slot] = latched
        return result

    @staticmethod
    def _durations_from_mask(
        mask: np.ndarray, active: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        durations = np.zeros((48,) + active.shape[1:], dtype=np.float64)
        censored = np.zeros_like(durations, dtype=bool)
        for boundary in range(48):
            for index in np.ndindex(active.shape[1:]):
                if not bool(active[(boundary,) + index]):
                    continue
                series = mask[(slice(boundary, boundary + _FUTURE_INTERVALS + 1),) + index]
                failures = np.flatnonzero(~series)
                intervals = int(failures[0]) if failures.size else _FUTURE_INTERVALS
                durations[(boundary,) + index] = intervals * D2_MEASUREMENT_STEP_S
                censored[(boundary,) + index] = not bool(failures.size)
        return durations, censored

    def step_arrays(
        self,
        *,
        world_seed: int,
        step_index: int,
        start_time_s: float = 0.0,
    ) -> PrimitiveStepArrays:
        """Return one recomputable 48-boundary engine snapshot as arrays."""

        world = self._ensure(world_seed)
        self._indices(world, step_index, 0)
        if not math.isfinite(start_time_s):
            raise MCRLContractError("start_time_s must be finite")
        state = world.steps[step_index]
        users = np.arange(state.user_ecef_km.shape[0], dtype=np.int64)
        row_user, row_action, identities, row_slot = self._row_metadata(state)
        # Keep one genuine tracked-but-ineligible row per user.  The legacy
        # four-slot action table erases these identities; the primitive mask
        # seam must expose false D2/visibility values rather than make those
        # predicates vacuous.  The lowest-elevation tracked satellite is a
        # deterministic, non-action audit row (legacy_action_index == -1).
        begin = step_index * D2_SUBINTERVALS
        tracked_now = world.positions_ecef_km[:, begin, :]
        user_delta = tracked_now[None, :, :] - state.user_ecef_km[:, None, :]
        user_slant = np.linalg.norm(user_delta, axis=-1)
        user_up_all = state.user_ecef_km / np.linalg.norm(
            state.user_ecef_km, axis=1, keepdims=True
        )
        tracked_elevation = np.degrees(
            np.arcsin(
                np.clip(
                    np.einsum("usc,uc->us", user_delta, user_up_all) / user_slant,
                    -1.0,
                    1.0,
                )
            )
        )
        extra_satellite_column = np.argmin(tracked_elevation, axis=1)
        extra_norads = world.tracked_norads[extra_satellite_column].astype(np.int64)
        extra_cells = np.asarray(
            [
                next(int(cell) for cell in state.cell_ids[user].tolist() if int(cell) >= 0)
                for user in range(users.size)
            ],
            dtype=np.int64,
        )
        extra_identities = np.stack((extra_norads, extra_cells), axis=1)
        identities = np.concatenate((identities, extra_identities), axis=0)
        row_user = np.concatenate((row_user, users), axis=0)
        row_action = np.concatenate(
            (row_action, np.full(users.size, -1, dtype=np.int64)), axis=0
        )
        row_slot = np.concatenate(
            (row_slot, np.full(users.size, NUM_SATELLITE_SLOTS, dtype=np.int64)),
            axis=0,
        )
        row_cells = identities[:, 1]
        grid = world.grid
        colors = np.asarray(grid.colors[row_cells], dtype=np.int64)
        tracked_column = {
            int(norad): index
            for index, norad in enumerate(world.tracked_norads.tolist())
        }
        satellite_norads = np.asarray(
            sorted({int(value) for value in identities[:, 0]}), dtype=np.int64
        )
        satellite_column = {
            int(norad): index for index, norad in enumerate(satellite_norads.tolist())
        }
        tracked_rows = np.asarray(
            [tracked_column[int(norad)] for norad in satellite_norads], dtype=np.int64
        )
        positions = world.positions_ecef_km[tracked_rows, begin : begin + 48, :].transpose(1, 0, 2)
        row_satellite = np.asarray(
            [satellite_column[int(norad)] for norad in identities[:, 0]], dtype=np.int64
        )
        row_positions = positions[:, row_satellite, :]
        row_users = state.user_ecef_km[row_user]
        row_centres = grid.centers_ecef_km[row_cells]
        delta = row_positions - row_users[None, :, :]
        slants = np.linalg.norm(delta, axis=-1)
        up = row_users / np.linalg.norm(row_users, axis=1, keepdims=True)
        elevations = np.degrees(
            np.arcsin(
                np.clip(np.einsum("brc,rc->br", delta, up) / slants, -1.0, 1.0)
            )
        )
        direct_angles = angle_between_deg(
            row_positions,
            np.broadcast_to(row_centres, row_positions.shape),
            np.broadcast_to(row_users, row_positions.shape),
        )
        peak_receive = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
        direct_path = self._nominal_path_without_scintillation(
            slants, elevations, np.full_like(slants, peak_receive)
        )
        nominal = transmit_gain_linear(direct_angles) * direct_path

        fading = np.empty(
            (48, users.size, satellite_norads.size), dtype=np.float64
        )
        times = (
            float(start_time_s)
            + step_index * DECISION_INTERVAL_S
            + np.arange(48, dtype=np.float64) * D2_MEASUREMENT_STEP_S
        )
        for boundary in range(48):
            absolute_ns = int(round(float(times[boundary]) * 1.0e9))
            for user in range(users.size):
                user_position = state.user_ecef_km[user]
                for sat_column, norad in enumerate(satellite_norads.tolist()):
                    sat_position = positions[boundary, sat_column]
                    sat_delta = sat_position - user_position
                    sat_slant = float(np.linalg.norm(sat_delta))
                    sat_up = user_position / np.linalg.norm(user_position)
                    sat_elevation = math.degrees(
                        math.asin(float(np.clip(np.dot(sat_delta, sat_up) / sat_slant, -1.0, 1.0)))
                    )
                    fading[boundary, user, sat_column] = keyed_fading_gain(
                        world=int(world_seed),
                        user=user,
                        norad=int(norad),
                        absolute_time_ns=absolute_ns,
                        elevation_deg=sat_elevation,
                    )
        realised = nominal * fading[:, row_user, row_satellite]

        d2_slots = self._forward_d2_slots(
            world=world,
            state=state,
            step_index=step_index,
            position_columns=tracked_column,
        )
        d2_slots = np.concatenate(
            (
                d2_slots,
                np.zeros((48, users.size, 1), dtype=bool),
            ),
            axis=2,
        )
        d2_eligible = d2_slots[:, row_user, row_slot]
        visible = elevations >= MINIMUM_ELEVATION_DEG
        cell_delta = row_positions - row_centres[None, :, :]
        cell_slant = np.linalg.norm(cell_delta, axis=-1)
        cell_up = row_centres / np.linalg.norm(row_centres, axis=1, keepdims=True)
        cell_elevation = np.degrees(
            np.arcsin(
                np.clip(
                    np.einsum("brc,rc->br", cell_delta, cell_up) / cell_slant,
                    -1.0,
                    1.0,
                )
            )
        )
        cell_reachable = cell_elevation >= 0.0

        altitude = np.linalg.norm(row_positions, axis=-1) - R_E_KM
        entry = np.empty_like(altitude)
        for index in np.ndindex(entry.shape):
            entry[index] = elevation_for_slant_range(
                D2_THRESHOLD_KM - D2_HYSTERESIS_KM,
                float(altitude[index]),
            )

        aggressor_identities = np.asarray(
            sorted(
                {
                    (int(norad), int(cell))
                    for norad, cell in identities[row_action >= 0].tolist()
                }
            ),
            dtype=np.int64,
        )
        aggressor_colors = np.asarray(
            grid.colors[aggressor_identities[:, 1]], dtype=np.int64
        )
        aggressor_satellite = np.asarray(
            [satellite_column[int(norad)] for norad in aggressor_identities[:, 0]],
            dtype=np.int64,
        )
        aggressor_positions = positions[:, aggressor_satellite, :]
        aggressor_centres = grid.centers_ecef_km[aggressor_identities[:, 1]]
        cross_vertex = np.broadcast_to(
            aggressor_positions[:, None, :, :],
            (48, users.size, aggressor_identities.shape[0], 3),
        )
        cross_angles = angle_between_deg(
            cross_vertex,
            np.broadcast_to(aggressor_centres[None, None, :, :], cross_vertex.shape),
            np.broadcast_to(state.user_ecef_km[None, :, None, :], cross_vertex.shape),
        )
        cross_delta = cross_vertex - state.user_ecef_km[None, :, None, :]
        cross_slant = np.linalg.norm(cross_delta, axis=-1)
        user_up = state.user_ecef_km / np.linalg.norm(
            state.user_ecef_km, axis=1, keepdims=True
        )
        cross_elevation = np.degrees(
            np.arcsin(
                np.clip(
                    np.einsum("buac,uc->bua", cross_delta, user_up) / cross_slant,
                    -1.0,
                    1.0,
                )
            )
        )
        cross_base = transmit_gain_linear(cross_angles) * self._nominal_path_without_scintillation(
            cross_slant, cross_elevation, np.ones_like(cross_slant)
        )

        # Terminal receive gain is indexed by the victim's four frozen
        # satellite slots and the physical aggressor satellite.  The
        # same-satellite P-10 override is applied here before per-beam colour
        # and self masks are applied by PrimitiveStepArrays.
        window_norads = np.concatenate(
            (
                state.norad_ids[:, ::NUM_BEAM_SLOTS],
                extra_norads[:, None],
            ),
            axis=1,
        )
        wanted_slots = window_norads.shape[1]
        wanted_positions = np.zeros(
            (48, users.size, wanted_slots, 3), dtype=np.float64
        )
        wanted_valid = window_norads >= 0
        for user in range(users.size):
            for slot in range(wanted_slots):
                norad = int(window_norads[user, slot])
                if norad >= 0:
                    wanted_positions[:, user, slot] = positions[:, satellite_column[norad]]
        receive_vertex = np.broadcast_to(
            state.user_ecef_km[None, :, None, None, :],
            (48, users.size, wanted_slots, satellite_norads.size, 3),
        )
        receive_angles = angle_between_deg(
            receive_vertex,
            np.broadcast_to(
                wanted_positions[:, :, :, None, :], receive_vertex.shape
            ),
            np.broadcast_to(
                positions[:, None, None, :, :], receive_vertex.shape
            ),
        )
        same_satellite = (
            window_norads[:, :, None] == satellite_norads[None, None, :]
        ) & wanted_valid[:, :, None]
        receive_gain = interference_receive_gain_linear(
            receive_angles,
            same_satellite=np.broadcast_to(same_satellite[None, :, :, :], receive_angles.shape),
        )

        # Fixed 900.48-s sampled horizon at every boundary.  A no-crossing
        # duration is explicitly right-censored instead of masquerading as a
        # measured expiry.
        horizon_positions = world.positions_ecef_km[
            tracked_rows,
            begin : begin + 48 + _FUTURE_INTERVALS,
            :,
        ].transpose(1, 0, 2)
        visibility_duration = np.zeros((48, users.size, wanted_slots))
        d2_duration = np.zeros_like(visibility_duration)
        visibility_censored = np.zeros_like(visibility_duration, dtype=bool)
        d2_censored = np.zeros_like(visibility_duration, dtype=bool)
        for user in range(users.size):
            user_position = state.user_ecef_km[user]
            user_up_vector = user_position / np.linalg.norm(user_position)
            for slot in range(wanted_slots):
                norad = int(window_norads[user, slot])
                if norad < 0:
                    continue
                sat_column = satellite_column[norad]
                future_delta = horizon_positions[:, sat_column] - user_position
                future_slant = np.linalg.norm(future_delta, axis=1)
                future_elevation = np.degrees(
                    np.arcsin(
                        np.clip(
                            (future_delta @ user_up_vector) / future_slant,
                            -1.0,
                            1.0,
                        )
                    )
                )
                visible_mask = future_elevation >= MINIMUM_ELEVATION_DEG
                release_mask = (
                    future_slant - D2_HYSTERESIS_KM <= D2_THRESHOLD_KM
                )
                for boundary_index in range(48):
                    stop = boundary_index + _FUTURE_INTERVALS + 1
                    vis_window = visible_mask[boundary_index:stop]
                    d2_window = release_mask[boundary_index:stop]
                    if bool(visible_mask[boundary_index]):
                        failures = np.flatnonzero(~vis_window)
                        visibility_censored[boundary_index, user, slot] = failures.size == 0
                        count = _FUTURE_INTERVALS if failures.size == 0 else int(failures[0])
                        visibility_duration[boundary_index, user, slot] = count * D2_MEASUREMENT_STEP_S
                    if d2_slots[boundary_index, user, slot]:
                        failures = np.flatnonzero(~d2_window)
                        d2_censored[boundary_index, user, slot] = failures.size == 0
                        count = _FUTURE_INTERVALS if failures.size == 0 else int(failures[0])
                        d2_duration[boundary_index, user, slot] = count * D2_MEASUREMENT_STEP_S

        return PrimitiveStepArrays(
            absolute_time_s=times,
            users=users,
            row_user_column=row_user,
            legacy_action_index=row_action,
            identities=identities,
            colors=colors,
            elevations_deg=elevations,
            d2_entry_elevations_deg=entry,
            slants_km=slants,
            d2_distances_km=slants,
            visible=visible,
            d2_eligible=d2_eligible,
            cell_reachable=cell_reachable,
            nominal_gain=nominal,
            realised_gain=realised,
            remaining_visibility_s=visibility_duration[:, row_user, row_slot],
            remaining_d2_s=d2_duration[:, row_user, row_slot],
            visibility_right_censored=visibility_censored[:, row_user, row_slot],
            d2_right_censored=d2_censored[:, row_user, row_slot],
            aggressor_identities=aggressor_identities,
            aggressor_colors=aggressor_colors,
            aggressor_satellite_column=aggressor_satellite,
            row_wanted_slot=row_slot,
            cross_base_nominal=cross_base,
            fading_by_satellite=fading,
            receive_gain_by_wanted_slot=receive_gain,
        )

    def provider_source_sha256(self) -> str:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

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
        relative = (
            step_index * DECISION_INTERVAL_S
            + boundary_index * D2_MEASUREMENT_STEP_S
        )
        inferred_origin = float(absolute_time_s) - relative
        if self._time_origin_s is None:
            self._time_origin_s = inferred_origin
        elif not math.isclose(
            inferred_origin,
            self._time_origin_s,
            rel_tol=0.0,
            abs_tol=_TIME_TOLERANCE_S,
        ):
            raise MCRLContractError(
                "absolute boundary time disagrees with the bound tape origin"
            )
        return self.step_arrays(
            world_seed=world_seed,
            step_index=step_index,
            start_time_s=self._time_origin_s,
        ).boundary_view(boundary_index)


def factory() -> LegacyWorldProvider:
    """CLI-compatible zero-argument provider factory."""

    return LegacyWorldProvider()


__all__ = [
    "CANONICAL_STEPS",
    "CANONICAL_TAPE_STEPS",
    "DEFAULT_TLE_ROOT",
    "FORECAST_STEPS",
    "LegacyWorldProvider",
    "factory",
]
