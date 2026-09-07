"""Live TLE/D2 projection adapter for the provisional OPS-3 C2 formula.

This module is deliberately an adapter, not a second simulator.  It freezes a
predecision :class:`~mcrl.env.step.StepEnvironment` anchor, clones the native
D2 latch state, propagates the already-tracked TLE set on the native 640-ms
measurement clock, and emits immutable :class:`OPS3Offset` receipts.  The
pure target, power delta, persistence, gauge, and feature equations remain in
``ee_axis_ops3.py``.

The public path has three explicit stages::

    anchor = snapshot_ops3_anchor(environment, observation)
    projection = project_ops3_anchor(anchor)
    surfaces = build_ops3_live_surfaces(anchor, projection, main_actions)

No stage advances the live environment, mobility, dwell, RNG, network, or
candidate assignment.  Future rows keep the current native physical
``(NORAD, cell)`` identity.  This is a deterministic median/no-fading shadow
used only for the bounded formula/oracle gate; it is not a hidden rollout and
does not establish C2 efficacy.
"""

from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass, field
import hashlib
import math
from typing import Sequence

import numpy as np

from ..env.action_contract import (
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
    Association,
)
from ..env.antenna import RX_GAIN_MAX_DBI, transmit_gain_linear
from ..env.candidates import (
    CELL_VISIBILITY_MIN_ELEVATION_DEG,
    _cell_visibility,
)
from ..env.cells import CellGrid
from ..env.constants import (
    D2_MEASUREMENT_STEP_S,
    D2_SUBSTEPS_PER_DECISION,
    R_E_KM,
)
from ..env.d2 import D2Snapshot, D2Tracker
from ..env.ephemeris import SatelliteSet, step_times
from ..env.interference import (
    beam_field_at_users,
    build_radiating_beams,
    candidate_interference_w,
    candidate_received_power_terms,
)
from ..env.link_budget import (
    BEAM_BANDWIDTH_HZ,
    BEAM_POWER_MAX_W,
    PA_MAX_EFFICIENCY,
    PA_SATURATION_POWER_W,
    SEGMENT_START_POWER_W,
    link_power_factor,
    recurrence_power_w,
    shannon_rate_bps,
    sinr,
)
from ..env.pointing import candidate_geometry
from ..env.scenario import _measure, _slant_only
from ..env.step import PhysicsConfig, StepEnvironment, StepObservation
from ..env.tle import TleRecord
from ..errors import MCRLContractError
from .ee_axis_ops3 import (
    OPS3_HORIZON,
    OPS3_INTERVAL_S,
    OPS3FrozenBackground,
    OPS3Offset,
    OPS3Surface,
    build_ops3_surface,
    segment_start_gain_surface,
)


OPS3_LIVE_SCHEMA = "multi-catfish-mcrl-v03-c2-ops3-live-anchor-v1"
OPS3_LIVE_PROJECTION_SCHEMA = (
    "multi-catfish-mcrl-v03-c2-ops3-live-projection-v1"
)
OPS3_CELL_VISIBILITY_MIN_ELEVATION_DEG = 0.0
_RX_GAIN_MAX_LINEAR = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
_TRACKER_ARRAY_FIELDS = (
    "_latched",
    "_condition_active",
    "_condition_started",
    "_ttt_elapsed",
)


class OPS3LiveError(MCRLContractError):
    """The live projection boundary is stale, mutable, or non-canonical."""


def _readonly(value: object, *, dtype: np.dtype | type | None = None) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _hash_array(digest: "hashlib._Hash", name: str, value: object) -> None:
    array = np.ascontiguousarray(np.asarray(value))
    digest.update(name.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))


def _tracker_sha256(tracker: D2Tracker) -> str:
    digest = hashlib.sha256()
    _hash_array(digest, "norad_ids", tracker.norad_ids)
    for name in _TRACKER_ARRAY_FIELDS:
        _hash_array(digest, name, getattr(tracker, name))
    digest.update(str(int(tracker._steps_seen)).encode("ascii"))
    digest.update(str(bool(tracker._primed)).encode("ascii"))
    config = tracker.config
    for name in (
        "thresh1_km",
        "thresh2_km",
        "hysteresis_km",
        "ttt_steps",
        "min_altitude_km",
        "time_step_s",
    ):
        value = getattr(config, name)
        encoded = float(value).hex() if isinstance(value, float) else str(value)
        digest.update(f"{name}={encoded}".encode("ascii"))
    return digest.hexdigest()


def _anchor_sha256(
    *,
    step_index: int,
    total_steps: int,
    start_utc: dt.datetime,
    arrays: Sequence[tuple[str, np.ndarray]],
    tracker_sha256: str,
    records: Sequence[TleRecord],
) -> str:
    digest = hashlib.sha256()
    digest.update(f"{step_index}/{total_steps}".encode("ascii"))
    digest.update(start_utc.isoformat().encode("ascii"))
    digest.update(tracker_sha256.encode("ascii"))
    for record in records:
        digest.update(str(int(record.norad_id)).encode("ascii"))
        digest.update(record.line1.encode("ascii"))
        digest.update(record.line2.encode("ascii"))
    for name, value in arrays:
        _hash_array(digest, name, value)
    return digest.hexdigest()


def _projection_sha256(
    *,
    anchor_sha256: str,
    indices: Sequence[int],
    sample_times: Sequence[dt.datetime],
    offsets_by_user: Sequence[Sequence[OPS3Offset]],
) -> str:
    digest = hashlib.sha256(anchor_sha256.encode("ascii"))
    digest.update(repr(tuple(int(value) for value in indices)).encode("ascii"))
    for when in sample_times:
        digest.update(when.isoformat().encode("ascii"))
    for uid, offsets in enumerate(offsets_by_user):
        digest.update(f"u={uid}".encode("ascii"))
        for offset_index, offset in enumerate(offsets, start=1):
            digest.update(f"h={offset_index}".encode("ascii"))
            for name in (
                "projected_gain_linear",
                "d2_eligible",
                "cell_visible",
                "focal_rate_bps",
                "focal_sinr_linear",
            ):
                _hash_array(digest, name, getattr(offset, name))
    return digest.hexdigest()


def _copy_grid(grid: CellGrid) -> CellGrid:
    return CellGrid(
        cell_radius_km=float(grid.cell_radius_km),
        pitch_km=float(grid.pitch_km),
        axial=_readonly(grid.axial, dtype=np.int64),
        centers_km=_readonly(grid.centers_km, dtype=np.float64),
        centers_ecef_km=_readonly(grid.centers_ecef_km, dtype=np.float64),
        colors=_readonly(grid.colors, dtype=np.int64),
        in_area=_readonly(grid.in_area, dtype=np.bool_),
        serves_area=_readonly(grid.serves_area, dtype=np.bool_),
        neighbor_ids=_readonly(grid.neighbor_ids, dtype=np.int64),
    )


def _require_exact_float(name: str, actual: float, expected: float) -> None:
    if not math.isfinite(float(actual)) or float(actual).hex() != float(expected).hex():
        raise OPS3LiveError(
            f"OPS-3 requires canonical {name}={float(expected).hex()}, got "
            f"{float(actual).hex() if math.isfinite(float(actual)) else actual!r}"
        )


def _assert_canonical_physics(environment: StepEnvironment) -> None:
    physics: PhysicsConfig = environment.physics
    for name, actual, expected in (
        ("p0", physics.segment_start_power_w, SEGMENT_START_POWER_W),
        ("pmax", physics.beam_power_max_w, BEAM_POWER_MAX_W),
        ("beam_bandwidth", physics.beam_bandwidth_hz, BEAM_BANDWIDTH_HZ),
        ("pa_max_efficiency", physics.pa_max_efficiency, PA_MAX_EFFICIENCY),
        ("pa_saturation_power", physics.pa_saturation_power_w, PA_SATURATION_POWER_W),
        (
            "decision_interval",
            environment.driver.config.ephemeris.time_step_s,
            OPS3_INTERVAL_S,
        ),
    ):
        _require_exact_float(name, float(actual), float(expected))
    config = environment.driver.config
    _require_exact_float(
        "D2 measurement interval",
        config.d2_measurement_step_s,
        D2_MEASUREMENT_STEP_S,
    )
    if config.d2_substeps_per_decision != D2_SUBSTEPS_PER_DECISION:
        raise OPS3LiveError(
            "OPS-3 requires canonical D2 substeps per decision="
            f"{D2_SUBSTEPS_PER_DECISION}, got {config.d2_substeps_per_decision}"
        )
    _require_exact_float(
        "D2 tracker interval",
        config.d2_measurement_step_s,
        config.d2.time_step_s,
    )
    if config.d2_substeps_per_decision * config.d2_measurement_step_s != (
        config.ephemeris.time_step_s
    ):
        raise OPS3LiveError("D2 measurement and decision clocks do not close exactly")
    _require_exact_float(
        "cell visibility threshold",
        CELL_VISIBILITY_MIN_ELEVATION_DEG,
        OPS3_CELL_VISIBILITY_MIN_ELEVATION_DEG,
    )


def _backgrounds_from_last_service(
    environment: StepEnvironment,
) -> tuple[OPS3FrozenBackground, ...]:
    associations = tuple(environment._previous_association)
    segments = tuple(environment._segments)
    powers = np.asarray(environment._previous_link_power_w, dtype=np.float64)
    users = environment.num_users
    if len(associations) != users or len(segments) != users or powers.shape != (users,):
        raise OPS3LiveError("last-service state has the wrong population shape")
    if not np.all(np.isfinite(powers)) or np.any(powers < 0.0):
        raise OPS3LiveError("last-service link power must be finite and non-negative")

    for uid, (association, segment, power) in enumerate(
        zip(associations, segments, powers.tolist())
    ):
        if association is None:
            if segment is not None or power != 0.0:
                raise OPS3LiveError(
                    f"user {uid} has no last served association but carries service state"
                )
            continue
        if not isinstance(association, Association):
            raise OPS3LiveError("previous association has a stale type")
        if segment is None or not segment.continues(association) or power <= 0.0:
            raise OPS3LiveError(
                f"user {uid} has an inconsistent served association/segment/power"
            )

    result: list[OPS3FrozenBackground] = []
    for focal in range(users):
        grouped: dict[tuple[int, int], tuple[int, float]] = {}
        for uid, association in enumerate(associations):
            if uid == focal or association is None:
                continue
            pair = (int(association.norad_id), int(association.cell_id))
            count, maximum = grouped.get(pair, (0, 0.0))
            grouped[pair] = (count + 1, max(maximum, float(powers[uid])))
        pairs = sorted(grouped)
        result.append(
            OPS3FrozenBackground(
                norad_ids=np.asarray([pair[0] for pair in pairs], dtype=np.int64),
                cell_ids=np.asarray([pair[1] for pair in pairs], dtype=np.int64),
                load=np.asarray([grouped[pair][0] for pair in pairs], dtype=np.int64),
                power_w=np.asarray([grouped[pair][1] for pair in pairs], dtype=np.float64),
            )
        )
    return tuple(result)


@dataclass(frozen=True)
class OPS3AnchorSnapshot:
    """Detached immutable inputs for one live predecision anchor."""

    step_index: int
    total_steps: int
    user_ecef_km: np.ndarray
    window_norad_ids: np.ndarray
    neighborhood_cell_ids: np.ndarray
    candidate_norad_ids: np.ndarray
    candidate_cell_ids: np.ndarray
    legal_mask: np.ndarray
    current_gain_linear: np.ndarray
    segment_start_gain_linear: np.ndarray
    backgrounds: tuple[OPS3FrozenBackground, ...]
    tracked_norad_ids: np.ndarray
    start_utc: dt.datetime
    d2_measurement_step_s: float
    d2_substeps_per_decision: int
    decision_step_s: float
    beam_bandwidth_hz: float
    noise_power_w: float
    tracker_seed_sha256: str
    anchor_sha256: str
    _tracker_seed: D2Tracker = field(repr=False, compare=False)
    _satellite_records: tuple[TleRecord, ...] = field(repr=False, compare=False)
    _grid: CellGrid = field(repr=False, compare=False)
    schema: str = OPS3_LIVE_SCHEMA

    @property
    def num_users(self) -> int:
        return int(self.user_ecef_km.shape[0])

    @property
    def horizon(self) -> int:
        return min(OPS3_HORIZON, max(0, self.total_steps - 1 - self.step_index))


@dataclass(frozen=True)
class OPS3ProjectionReceipt:
    """Detached native-clock projection receipts for one anchor."""

    offsets_by_user: tuple[tuple[OPS3Offset, ...], ...]
    future_d2_indices: tuple[int, ...]
    sample_times_utc: tuple[dt.datetime, ...]
    offset_times_utc: tuple[dt.datetime, ...]
    horizon: int
    anchor_sha256: str
    tracker_seed_sha256: str
    projection_sha256: str
    schema: str = OPS3_LIVE_PROJECTION_SCHEMA


def snapshot_ops3_anchor(
    environment: StepEnvironment,
    observation: StepObservation,
) -> OPS3AnchorSnapshot:
    """Detach one live predecision anchor without consuming state or RNG."""

    if not isinstance(environment, StepEnvironment):
        raise OPS3LiveError("environment must be a StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise OPS3LiveError("observation must be a StepObservation")
    if not environment._started or environment._candidates is None:
        raise OPS3LiveError("environment has not been reset")
    if observation.candidates is not environment._candidates:
        raise OPS3LiveError("observation is not the live predecision candidate table")
    if not (
        observation.step_index
        == environment._step_index
        == environment.driver.step_index
    ):
        raise OPS3LiveError("observation/environment/driver step indices disagree")
    _assert_canonical_physics(environment)

    driver = environment.driver
    tracker = driver._tracker
    satellites = driver._satellites
    start_utc = driver._start_utc
    if tracker is None or satellites is None or start_utc is None:
        raise OPS3LiveError("scenario driver has no live TLE/D2 state")
    if not tracker.primed:
        raise OPS3LiveError("live D2 tracker is not primed")
    if not np.array_equal(tracker.norad_ids, satellites.norad_ids):
        raise OPS3LiveError("D2 tracker and propagated satellite set disagree")

    candidates = observation.candidates
    users = environment.num_users
    legal = _readonly(observation.masks, dtype=np.bool_)
    if legal.shape != (users, NUM_ACTIONS):
        raise OPS3LiveError("live native mask has the wrong shape")
    candidate_norads = _readonly(
        np.stack([table.norad_ids for table in candidates.slot_tables]),
        dtype=np.int64,
    )
    candidate_cells = _readonly(
        np.stack([table.cell_ids for table in candidates.slot_tables]),
        dtype=np.int64,
    )
    if not np.array_equal(legal, candidates.masks):
        raise OPS3LiveError("observation and candidate masks disagree")

    theta = np.asarray(candidates.off_axis_deg, dtype=np.float64).reshape(
        users, NUM_ACTIONS
    )
    if np.any(legal & ~np.isfinite(theta)):
        raise OPS3LiveError("a legal current action lacks finite geometry")
    current_gain = np.where(
        legal,
        transmit_gain_linear(np.where(np.isfinite(theta), theta, 0.0)),
        0.0,
    )
    starts = np.zeros_like(current_gain)
    backgrounds = _backgrounds_from_last_service(environment)
    for uid in range(users):
        association = environment._previous_association[uid]
        segment = environment._segments[uid]
        starts[uid] = segment_start_gain_surface(
            candidate_norad_ids=candidate_norads[uid],
            candidate_cell_ids=candidate_cells[uid],
            current_gain_linear=current_gain[uid],
            current_association=(
                None
                if association is None
                else (int(association.norad_id), int(association.cell_id))
            ),
            committed_start_gain_linear=(
                None if segment is None else float(segment.start_transmit_gain)
            ),
            legal_mask=legal[uid],
        )

    user_ecef = _readonly(driver.user_ecef_km(), dtype=np.float64)
    window_norads = _readonly(candidates.window_norad_ids, dtype=np.int64)
    neighborhoods = _readonly(
        candidates.dwell.neighborhood_cell_ids, dtype=np.int64
    )
    tracked = _readonly(tracker.norad_ids, dtype=np.int64)
    tracker_seed = copy.deepcopy(tracker)
    tracker_sha = _tracker_sha256(tracker_seed)
    records = tuple(copy.deepcopy(satellites.records))
    grid = _copy_grid(driver.grid)
    start = start_utc.astimezone(dt.timezone.utc)
    anchor_sha = _anchor_sha256(
        step_index=observation.step_index,
        total_steps=driver.config.steps_per_episode,
        start_utc=start,
        arrays=(
            ("user_ecef", user_ecef),
            ("window_norads", window_norads),
            ("neighborhoods", neighborhoods),
            ("candidate_norads", candidate_norads),
            ("candidate_cells", candidate_cells),
            ("legal", legal),
            ("current_gain", current_gain),
            ("start_gain", starts),
        ),
        tracker_sha256=tracker_sha,
        records=records,
    )
    return OPS3AnchorSnapshot(
        step_index=int(observation.step_index),
        total_steps=int(driver.config.steps_per_episode),
        user_ecef_km=user_ecef,
        window_norad_ids=window_norads,
        neighborhood_cell_ids=neighborhoods,
        candidate_norad_ids=candidate_norads,
        candidate_cell_ids=candidate_cells,
        legal_mask=legal,
        current_gain_linear=_readonly(current_gain, dtype=np.float64),
        segment_start_gain_linear=_readonly(starts, dtype=np.float64),
        backgrounds=backgrounds,
        tracked_norad_ids=tracked,
        start_utc=start,
        d2_measurement_step_s=float(driver.config.d2_measurement_step_s),
        d2_substeps_per_decision=int(driver.config.d2_substeps_per_decision),
        decision_step_s=float(driver.config.ephemeris.time_step_s),
        beam_bandwidth_hz=float(environment.physics.beam_bandwidth_hz),
        noise_power_w=float(environment.physics.noise_power_w),
        tracker_seed_sha256=tracker_sha,
        anchor_sha256=anchor_sha,
        _tracker_seed=tracker_seed,
        _satellite_records=records,
        _grid=grid,
    )


def _offsets_at_endpoint(
    anchor: OPS3AnchorSnapshot,
    *,
    d2_snapshot: D2Snapshot,
    satellite_ecef_km: np.ndarray,
) -> tuple[OPS3Offset, ...]:
    users = anchor.num_users
    if satellite_ecef_km.shape != (anchor.tracked_norad_ids.size, 3):
        raise OPS3LiveError("future tracked satellite position has the wrong shape")
    by_norad = {
        int(norad): satellite_ecef_km[index]
        for index, norad in enumerate(anchor.tracked_norad_ids.tolist())
    }
    d2_column = {
        int(norad): index for index, norad in enumerate(d2_snapshot.norad_ids.tolist())
    }
    if set(by_norad) != set(d2_column):
        raise OPS3LiveError("future D2 and TLE identity universes disagree")

    result: list[OPS3Offset] = []
    for uid in range(users):
        legal = np.asarray(anchor.legal_mask[uid], dtype=np.bool_)
        slot_norads = np.asarray(anchor.window_norad_ids[uid], dtype=np.int64)
        slot_positions = np.full(
            (NUM_SATELLITE_SLOTS, 3), np.nan, dtype=np.float64
        )
        d2_slot = np.zeros(NUM_SATELLITE_SLOTS, dtype=np.bool_)
        for slot, norad in enumerate(slot_norads.tolist()):
            if norad < 0:
                continue
            if norad not in by_norad:
                raise OPS3LiveError(f"current action NORAD {norad} left tracked universe")
            slot_positions[slot] = by_norad[norad]
            d2_slot[slot] = bool(d2_snapshot.eligible[uid, d2_column[norad]])

        geometry_positions = np.where(
            np.isnan(slot_positions),
            satellite_ecef_km[0][None, :],
            slot_positions,
        )
        geometry = candidate_geometry(
            user_ecef_km=anchor.user_ecef_km[uid : uid + 1],
            satellite_ecef_km=geometry_positions[None, :, :],
            cell_centres_ecef_km=anchor._grid.centers_ecef_km,
            neighborhood_cell_ids=anchor.neighborhood_cell_ids[uid : uid + 1],
        )
        theta = geometry.off_axis_deg.reshape(NUM_ACTIONS)
        if np.any(legal & ~np.isfinite(theta)):
            raise OPS3LiveError("a current legal physical action lost future geometry")
        gain = np.where(
            legal,
            transmit_gain_linear(np.where(np.isfinite(theta), theta, 0.0)),
            0.0,
        )
        visible = _cell_visibility(
            grid=anchor._grid,
            neighborhood_cell_ids=anchor.neighborhood_cell_ids[uid : uid + 1],
            window_satellite_ecef_km=slot_positions[None, :, :],
            min_elevation_deg=OPS3_CELL_VISIBILITY_MIN_ELEVATION_DEG,
        ).reshape(NUM_ACTIONS)
        d2_action = np.repeat(d2_slot, NUM_BEAM_SLOTS)

        required = np.zeros(NUM_ACTIONS, dtype=np.float64)
        positive = legal & (gain > 0.0)
        if bool(np.any(positive)):
            required[positive] = recurrence_power_w(
                anchor.segment_start_gain_linear[uid, positive],
                gain[positive],
                p0_w=SEGMENT_START_POWER_W,
            )
        if not np.all(np.isfinite(required)):
            raise OPS3LiveError("future recurrence power is non-finite")

        background = anchor.backgrounds[uid]
        radiating = build_radiating_beams(
            beam_norad_ids=background.norad_ids,
            beam_cell_ids=background.cell_ids,
            beam_power_w=background.power_w,
            satellite_ecef_by_norad=by_norad,
            grid=anchor._grid,
        )
        field = beam_field_at_users(
            user_ecef_km=anchor.user_ecef_km[uid : uid + 1],
            radiating=radiating,
        )
        finite_candidate_positions = np.where(
            np.isnan(slot_positions),
            anchor.user_ecef_km[uid][None, :],
            slot_positions,
        )
        candidate_terms = candidate_received_power_terms(
            field,
            radiating,
            user_ecef_km=anchor.user_ecef_km[uid : uid + 1],
            candidate_satellite_ecef_km=finite_candidate_positions[None, :, :],
            candidate_norad_ids=slot_norads[None, :],
        )
        candidate_cells = np.asarray(anchor.candidate_cell_ids[uid], dtype=np.int64)
        colors = np.where(
            candidate_cells >= 0,
            anchor._grid.colors[np.maximum(candidate_cells, 0)],
            -1,
        )
        interference = candidate_interference_w(
            candidate_terms,
            radiating,
            candidate_norad_ids=anchor.candidate_norad_ids[uid : uid + 1],
            candidate_cell_ids=anchor.candidate_cell_ids[uid : uid + 1],
            candidate_colors=colors[None, :],
        )[0]

        slant = np.repeat(geometry.slant_range_km, NUM_BEAM_SLOTS, axis=1)[0]
        elevation = np.repeat(geometry.elevation_deg, NUM_BEAM_SLOTS, axis=1)[0]
        usable = legal & np.isfinite(slant) & np.isfinite(elevation) & (gain > 0.0)
        path = np.where(
            usable,
            link_power_factor(
                np.where(usable, slant, 1.0),
                np.where(usable, elevation, 0.0),
                np.full(NUM_ACTIONS, _RX_GAIN_MAX_LINEAR, dtype=np.float64),
                shadow_fading_db=0.0,
            ),
            0.0,
        )
        wanted = np.where(usable, required * gain * path, 0.0)
        projected_sinr = np.where(
            usable,
            sinr(wanted, interference, anchor.noise_power_w),
            0.0,
        )
        load = np.zeros(NUM_ACTIONS, dtype=np.float64)
        pairs = {
            (int(norad), int(cell)): int(background.load[index])
            for index, (norad, cell) in enumerate(
                zip(background.norad_ids.tolist(), background.cell_ids.tolist())
            )
        }
        for action in np.flatnonzero(legal).tolist():
            pair = (
                int(anchor.candidate_norad_ids[uid, action]),
                int(anchor.candidate_cell_ids[uid, action]),
            )
            load[action] = 1.0 + float(pairs.get(pair, 0))
        rate = np.where(
            usable,
            shannon_rate_bps(
                projected_sinr,
                beam_load=load,
                bandwidth_hz=anchor.beam_bandwidth_hz,
            ),
            0.0,
        )
        if not all(
            np.all(np.isfinite(value))
            for value in (gain, projected_sinr, rate, interference)
        ):
            raise OPS3LiveError("projected channel surface is non-finite")
        result.append(
            OPS3Offset(
                projected_gain_linear=np.where(legal, gain, 0.0),
                d2_eligible=np.asarray(d2_action & legal, dtype=np.bool_),
                cell_visible=np.asarray(visible & legal, dtype=np.bool_),
                focal_rate_bps=np.where(legal, rate, 0.0),
                focal_sinr_linear=np.where(legal, projected_sinr, 0.0),
            )
        )
    return tuple(result)


def project_ops3_anchor(anchor: OPS3AnchorSnapshot) -> OPS3ProjectionReceipt:
    """Project the detached anchor on the native D2/TLE clock."""

    if not isinstance(anchor, OPS3AnchorSnapshot) or anchor.schema != OPS3_LIVE_SCHEMA:
        raise OPS3LiveError("anchor is not a current OPS-3 live snapshot")
    if _tracker_sha256(anchor._tracker_seed) != anchor.tracker_seed_sha256:
        raise OPS3LiveError("detached D2 tracker seed was mutated")
    horizon = anchor.horizon
    if horizon == 0:
        offsets: tuple[tuple[OPS3Offset, ...], ...] = tuple(
            () for _ in range(anchor.num_users)
        )
        projection_sha = _projection_sha256(
            anchor_sha256=anchor.anchor_sha256,
            indices=(),
            sample_times=(),
            offsets_by_user=offsets,
        )
        return OPS3ProjectionReceipt(
            offsets_by_user=offsets,
            future_d2_indices=(),
            sample_times_utc=(),
            offset_times_utc=(),
            horizon=0,
            anchor_sha256=anchor.anchor_sha256,
            tracker_seed_sha256=anchor.tracker_seed_sha256,
            projection_sha256=projection_sha,
        )

    tracker = copy.deepcopy(anchor._tracker_seed)
    satellites = SatelliteSet(anchor._satellite_records)
    samples = horizon * anchor.d2_substeps_per_decision
    decision_time = anchor.start_utc + dt.timedelta(
        seconds=anchor.step_index * anchor.decision_step_s
    )
    first = decision_time + dt.timedelta(seconds=anchor.d2_measurement_step_s)
    jd, fr = step_times(
        first, samples, time_step_s=anchor.d2_measurement_step_s
    )
    position, velocity = satellites.propagate_ecef_state(
        jd, fr, require_all_healthy=False
    )
    expected = (anchor.tracked_norad_ids.size, samples, 3)
    if position.shape != expected or velocity.shape != expected:
        raise OPS3LiveError("future TLE propagation has the wrong shape")
    if not np.all(np.isfinite(position)) or not np.all(np.isfinite(velocity)):
        raise OPS3LiveError("future tracked TLE propagation is non-finite")
    slant = _slant_only(anchor.user_ecef_km, position)
    altitude = np.linalg.norm(position, axis=-1) - R_E_KM
    if not np.all(np.isfinite(slant)) or not np.all(np.isfinite(altitude)):
        raise OPS3LiveError("future D2 geometry is non-finite")

    endpoint_rates: list[np.ndarray] = []
    for h in range(1, horizon + 1):
        endpoint = h * anchor.d2_substeps_per_decision - 1
        _, rate = _measure(
            anchor.user_ecef_km,
            position[:, endpoint : endpoint + 1, :],
            velocity[:, endpoint : endpoint + 1, :],
        )
        endpoint_rates.append(rate[:, :, 0])

    base = (anchor.step_index + 1) * anchor.d2_substeps_per_decision
    indices = tuple(base + index for index in range(samples))
    times = tuple(
        first + dt.timedelta(seconds=index * anchor.d2_measurement_step_s)
        for index in range(samples)
    )
    offsets_by_user: list[list[OPS3Offset]] = [
        [] for _ in range(anchor.num_users)
    ]
    offset_times: list[dt.datetime] = []
    for index, d2_index in enumerate(indices):
        h_index = index // anchor.d2_substeps_per_decision
        snapshot = tracker.update(
            d2_index,
            slant_range_km=slant[:, :, index],
            altitude_km=altitude[:, index],
            # Reproduce ScenarioDriver._resolve exactly: one decision-endpoint
            # range rate is repeated across all native D2 measurements in that
            # decision block.
            range_rate_km_s=endpoint_rates[h_index],
        )
        if (index + 1) % anchor.d2_substeps_per_decision != 0:
            continue
        endpoint_offsets = _offsets_at_endpoint(
            anchor,
            d2_snapshot=snapshot,
            satellite_ecef_km=position[:, index, :],
        )
        for uid, offset in enumerate(endpoint_offsets):
            offsets_by_user[uid].append(offset)
        offset_times.append(times[index])

    packed = tuple(tuple(values) for values in offsets_by_user)
    if any(len(values) != horizon for values in packed):
        raise OPS3LiveError("projection did not emit every requested offset")
    if _tracker_sha256(anchor._tracker_seed) != anchor.tracker_seed_sha256:
        raise OPS3LiveError("projection mutated its detached tracker seed")
    projection_sha = _projection_sha256(
        anchor_sha256=anchor.anchor_sha256,
        indices=indices,
        sample_times=times,
        offsets_by_user=packed,
    )
    return OPS3ProjectionReceipt(
        offsets_by_user=packed,
        future_d2_indices=indices,
        sample_times_utc=times,
        offset_times_utc=tuple(offset_times),
        horizon=horizon,
        anchor_sha256=anchor.anchor_sha256,
        tracker_seed_sha256=anchor.tracker_seed_sha256,
        projection_sha256=projection_sha,
    )


def build_ops3_live_surfaces(
    anchor: OPS3AnchorSnapshot,
    projection: OPS3ProjectionReceipt,
    reference_actions: Sequence[int] | np.ndarray,
) -> tuple[OPS3Surface, ...]:
    """Apply the pure OPS-3 formula to one authenticated live projection."""

    if not isinstance(anchor, OPS3AnchorSnapshot):
        raise OPS3LiveError("anchor must be an OPS3AnchorSnapshot")
    if (
        not isinstance(projection, OPS3ProjectionReceipt)
        or projection.schema != OPS3_LIVE_PROJECTION_SCHEMA
    ):
        raise OPS3LiveError("projection is not a current OPS-3 receipt")
    if projection.anchor_sha256 != anchor.anchor_sha256:
        raise OPS3LiveError("projection belongs to a different anchor")
    if projection.tracker_seed_sha256 != anchor.tracker_seed_sha256:
        raise OPS3LiveError("projection and anchor D2 seeds disagree")
    if projection.horizon != anchor.horizon:
        raise OPS3LiveError("projection and anchor horizons disagree")
    expected_projection_sha = _projection_sha256(
        anchor_sha256=anchor.anchor_sha256,
        indices=projection.future_d2_indices,
        sample_times=projection.sample_times_utc,
        offsets_by_user=projection.offsets_by_user,
    )
    if expected_projection_sha != projection.projection_sha256:
        raise OPS3LiveError("projection receipt was modified")

    raw_references = np.asarray(reference_actions)
    if (
        raw_references.shape != (anchor.num_users,)
        or raw_references.dtype == np.bool_
        or not np.issubdtype(raw_references.dtype, np.integer)
    ):
        raise OPS3LiveError("reference_actions must be one integer per user")
    references = np.asarray(raw_references, dtype=np.int64)
    surfaces: list[OPS3Surface] = []
    for uid in range(anchor.num_users):
        reference = int(references[uid])
        legal = anchor.legal_mask[uid]
        if bool(np.any(legal)):
            if not 0 <= reference < NUM_ACTIONS or not bool(legal[reference]):
                raise OPS3LiveError(f"user {uid} reference action is not legal")
        elif reference != -1:
            raise OPS3LiveError(f"starved user {uid} requires reference action -1")
        surfaces.append(
            build_ops3_surface(
                legal_mask=legal,
                reference_action=reference,
                candidate_norad_ids=anchor.candidate_norad_ids[uid],
                candidate_cell_ids=anchor.candidate_cell_ids[uid],
                segment_start_gain_linear=anchor.segment_start_gain_linear[uid],
                offsets=projection.offsets_by_user[uid],
                background=anchor.backgrounds[uid],
                user_count=anchor.num_users,
                step_index=anchor.step_index,
                total_steps=anchor.total_steps,
            )
        )
    return tuple(surfaces)


__all__ = [
    "OPS3_CELL_VISIBILITY_MIN_ELEVATION_DEG",
    "OPS3_LIVE_PROJECTION_SCHEMA",
    "OPS3_LIVE_SCHEMA",
    "OPS3AnchorSnapshot",
    "OPS3LiveError",
    "OPS3ProjectionReceipt",
    "build_ops3_live_surfaces",
    "project_ops3_anchor",
    "snapshot_ops3_anchor",
]
