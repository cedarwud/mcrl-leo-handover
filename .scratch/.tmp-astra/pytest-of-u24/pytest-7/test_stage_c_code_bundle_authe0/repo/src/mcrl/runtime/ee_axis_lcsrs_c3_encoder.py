"""V0.23 LC-SRS deterministic relational C3 descriptor encoder.

This module is the physical, predecision half of the LC-SRS C3 seam.  It
captures the native candidate/mask surface, committed state, current geometry,
cell colours, and a detached Q1+Q2 surface once, then builds an immutable
``C3View``.  It deliberately does not evaluate a branch, read an observation
SINR, draw randomness, or inspect an outcome.

The encoder is intentionally a small adapter around :mod:`ee_axis_lcsrs_c3_state`.
The latter owns the public schema and digest; this module owns only the
physical-to-feature mapping.  All numeric identifiers are used as dictionary
keys/equality predicates and never enter a feature value.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import math
from types import MappingProxyType
import numpy as np

from ..env.action_contract import (
    NUM_ACTIONS,
    Association,
    SlotTable,
    UNSERVED,
)
from ..env.antenna import RX_GAIN_MAX_DBI, receive_gain_linear, transmit_gain_linear
from ..env.geometry import angle_between_deg, look_angles
from ..env.link_budget import (
    BEAM_POWER_MAX_W,
    SEGMENT_START_POWER_W,
    link_power_factor,
    noise_power_w,
)
from ..env.keyed_fading import KEYED_FADING_VERSION, KeyedFadingField
from ..env.observation_provenance import NativeObservationProvenance
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_lcsrs_c3_state import (
    C3View,
    assemble_c3_view,
)
from .ee_axis_lcsrs_c3_topology import (
    LCSRSC3AnchorCapture,
    LCSRSC3AnchorTopologyReceipt,
    enumerate_lcsrs_c3_anchor,
)
from .ee_axis_ops3 import (
    opening_service_feasibility_surface,
    segment_start_gain_surface,
)
from .ee_axis_state import encode_ee_axis_state


class LCSRSC3EncoderError(MCRLContractError):
    """A predecision LC-SRS descriptor input is malformed or incomplete."""


_EARTH_RADIUS_KM = 6371.0
_RX_MAX_LINEAR = 10.0 ** (float(RX_GAIN_MAX_DBI) / 10.0)


def _readonly_copy(value: object, *, dtype: np.dtype) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class _CapturedSegment:
    """Scalar-only copy of a live power segment."""

    norad_id: int
    cell_id: int
    start_transmit_gain: float
    age_steps: int


def _as_float(value: object, *, field: str, default: float | None = None) -> float:
    if value is None:
        if default is None:
            raise LCSRSC3EncoderError(f"{field} is required")
        return float(default)
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3EncoderError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise LCSRSC3EncoderError(f"{field} must be finite")
    return result


def _array(value: object, *, field: str, dtype: np.dtype[Any]) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=dtype)
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3EncoderError(f"{field} cannot be materialised") from error
    return np.array(result, copy=True, order="C")


def _bool_matrix(value: object, *, field: str, shape: tuple[int, ...]) -> np.ndarray:
    result = _array(value, field=field, dtype=np.dtype(np.bool_))
    if result.shape != shape:
        raise LCSRSC3EncoderError(f"{field} must be Boolean shape {shape}")
    # np.asarray(..., dtype=bool) would silently coerce strings/float values;
    # reject those at the boundary instead of making a hidden mask.
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype != np.bool_:
        raise LCSRSC3EncoderError(f"{field} must have Boolean dtype")
    return result


def _int_vector(value: object, *, field: str, size: int) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != (size,) or raw.dtype == np.bool_ or not np.issubdtype(raw.dtype, np.integer):
        raise LCSRSC3EncoderError(f"{field} must be integer shape ({size},)")
    return np.array(raw, dtype=np.int64, copy=True, order="C")


def _bounded_nonnegative(value: float) -> float:
    if not math.isfinite(value) or value < 0.0:
        raise LCSRSC3EncoderError("a non-negative descriptor is malformed")
    return value / (1.0 + value)


def _distance_bound(value: float) -> float:
    if not math.isfinite(value) or value < 0.0:
        raise LCSRSC3EncoderError("distance must be finite and non-negative")
    return value / (value + _EARTH_RADIUS_KM)


def _angle_bound(value_deg: float) -> float:
    if not math.isfinite(value_deg) or value_deg < 0.0:
        raise LCSRSC3EncoderError("angle must be finite and non-negative")
    return math.radians(value_deg) / math.pi


def _elevation_bound(value_deg: float) -> float:
    if not math.isfinite(value_deg) or value_deg < -90.0 or value_deg > 90.0:
        raise LCSRSC3EncoderError("elevation must lie in [-90,90] degrees")
    return value_deg / 90.0


def _key(norad: int, cell: int) -> tuple[int, int]:
    return int(norad), int(cell)


def _key_from_action(table: SlotTable, action: int) -> tuple[int, int] | None:
    if not bool(table.mask[action]):
        return None
    norad = int(table.norad_ids[action])
    cell = int(table.cell_ids[action])
    if norad < 0 or cell < 0:
        raise LCSRSC3EncoderError("a legal action lacks a physical key")
    return _key(norad, cell)


def _copy_slot_table(table: SlotTable) -> SlotTable:
    """Detach the mutable ndarray payloads hidden inside frozen SlotTable."""

    return SlotTable(
        norad_ids=_readonly_copy(table.norad_ids, dtype=np.dtype(np.int64)),
        cell_ids=_readonly_copy(table.cell_ids, dtype=np.dtype(np.int64)),
        mask=_readonly_copy(table.mask, dtype=np.dtype(np.bool_)),
    )


def _cochannel(
    first: tuple[int, int] | None,
    second: tuple[int, int] | None,
    colors: Mapping[int, int],
) -> bool:
    if first is None or second is None:
        return False
    sat_a, cell_a = first
    sat_b, cell_b = second
    if cell_a not in colors or cell_b not in colors:
        return False
    if int(colors[cell_a]) != int(colors[cell_b]):
        return False
    return (sat_a == sat_b and cell_a != cell_b) or sat_a != sat_b


@dataclass(frozen=True)
class _Snapshot:
    """Captured values used after the live environment boundary."""

    users: int
    step_index: int
    legal: np.ndarray
    opening: np.ndarray
    tables: tuple[SlotTable, ...]
    q12: np.ndarray
    q12_snapshot_digest: str
    q12_source_state_digest: str
    q12_native_observation_event_digest: str
    q12_model_digest: str
    native_observation_provenance: NativeObservationProvenance
    state_schema: str
    state_schema_sha256: str
    state_sha256: str
    refs: np.ndarray
    user_ecef: np.ndarray
    centers: np.ndarray
    colors: np.ndarray
    positions: Mapping[int, np.ndarray]
    candidate_theta_deg: np.ndarray
    candidate_slant_km: np.ndarray
    candidate_elevation_deg: np.ndarray
    committed_associations: tuple[tuple[int, int] | None, ...]
    committed_load: Mapping[tuple[int, int], int]
    committed_power: Mapping[tuple[int, int], float]
    committed_satellites: frozenset[int]
    previous_link_power: np.ndarray
    segments: tuple[_CapturedSegment | None, ...]
    power_max: float
    p0: float
    noise: float
    episode_length: int
    active_beam_count_denominator: int


@dataclass(frozen=True)
class LCSRSC3PredecisionCapture:
    """One immutable topology receipt and the feature view derived from it."""

    topology: LCSRSC3AnchorTopologyReceipt
    view: C3View
    native_observation_provenance: NativeObservationProvenance
    state_schema: str
    state_schema_sha256: str
    state_sha256: str
    content_digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.topology, LCSRSC3AnchorTopologyReceipt):
            raise LCSRSC3EncoderError("predecision capture needs a topology receipt")
        if not isinstance(self.view, C3View):
            raise LCSRSC3EncoderError("predecision capture needs a C3View")
        if not isinstance(
            self.native_observation_provenance,
            NativeObservationProvenance,
        ):
            raise LCSRSC3EncoderError(
                "predecision capture needs native observation provenance"
            )
        self.native_observation_provenance.verify()
        if (
            self.native_observation_provenance.field_mode
            != KEYED_FADING_VERSION
            or self.native_observation_provenance.field_version
            != KEYED_FADING_VERSION
            or self.native_observation_provenance.field_root_digest is None
        ):
            raise LCSRSC3EncoderError(
                "V0.23 predecision capture requires canonical keyed observation provenance"
            )
        self.topology.verify()
        self.view.verify()
        capture = self.topology.capture
        if not np.array_equal(capture.action_mask, self.view.action_mask):
            raise LCSRSC3EncoderError("topology and C3View native masks disagree")
        if not np.array_equal(
            capture.reference_actions,
            self.view.reference_actions,
        ):
            raise LCSRSC3EncoderError("topology and C3View references disagree")
        for name, value in (
            ("state_schema", self.state_schema),
            ("state_schema_sha256", self.state_schema_sha256),
            ("state_sha256", self.state_sha256),
        ):
            if not isinstance(value, str) or not value:
                raise LCSRSC3EncoderError(f"{name} must be a nonempty string")
        if capture.q12_snapshot.source_state_digest != self.state_sha256:
            raise LCSRSC3EncoderError(
                "predecision state disagrees with detached Q12 ancestry"
            )
        if (
            capture.q12_snapshot.native_observation_event_digest
            != self.native_observation_provenance.content_digest
        ):
            raise LCSRSC3EncoderError(
                "predecision event disagrees with detached Q12 ancestry"
            )
        digest = hashlib.sha256()
        digest.update(b"multi-catfish-mcrl-v023-lcsrs-predecision-v1")
        digest.update(self.topology.content_digest.encode("ascii"))
        digest.update(self.view.content_digest.encode("ascii"))
        digest.update(
            self.native_observation_provenance.content_digest.encode("ascii")
        )
        digest.update(self.state_schema.encode("utf-8"))
        digest.update(self.state_schema_sha256.encode("ascii"))
        digest.update(self.state_sha256.encode("ascii"))
        expected = digest.hexdigest()
        if self.content_digest not in {"", expected}:
            raise LCSRSC3EncoderError("predecision capture digest mismatch")
        object.__setattr__(self, "content_digest", expected)

    def verify(self) -> str:
        digest = hashlib.sha256()
        digest.update(b"multi-catfish-mcrl-v023-lcsrs-predecision-v1")
        digest.update(self.topology.content_digest.encode("ascii"))
        digest.update(self.view.content_digest.encode("ascii"))
        digest.update(
            self.native_observation_provenance.content_digest.encode("ascii")
        )
        digest.update(self.state_schema.encode("utf-8"))
        digest.update(self.state_schema_sha256.encode("ascii"))
        digest.update(self.state_sha256.encode("ascii"))
        expected = digest.hexdigest()
        if self.content_digest != expected:
            raise LCSRSC3EncoderError("predecision capture digest mismatch")
        return expected


def _read_grid(environment: StepEnvironment, candidates: object, used_cells: set[int]) -> tuple[np.ndarray, np.ndarray]:
    driver = getattr(environment, "driver", None)
    grid = getattr(driver, "grid", None)
    colors_value = getattr(grid, "colors", None)
    if colors_value is None:
        colors_value = getattr(candidates, "cell_colors", None)
    centers_value = getattr(grid, "centers_ecef_km", None)
    if centers_value is None:
        centers_value = getattr(candidates, "cell_centres_ecef_km", None)
    if colors_value is None or centers_value is None:
        raise LCSRSC3EncoderError("LC-SRS needs a cell colour map and ECEF centres")
    colors = np.asarray(colors_value)
    if colors.ndim != 1 or colors.dtype == np.bool_ or not np.issubdtype(colors.dtype, np.integer):
        raise LCSRSC3EncoderError("cell colour map is malformed")
    centers = np.asarray(centers_value, dtype=np.float64)
    if centers.ndim != 2 or centers.shape[1] != 3 or not np.all(np.isfinite(centers)):
        raise LCSRSC3EncoderError("cell centre map is malformed")
    if used_cells and (min(used_cells) < 0 or max(used_cells) >= colors.size or max(used_cells) >= centers.shape[0]):
        raise LCSRSC3EncoderError("a physical cell is outside the grid")
    return (
        _readonly_copy(centers, dtype=np.dtype(np.float64)),
        _readonly_copy(colors, dtype=np.dtype(np.int64)),
    )


def _capture_positions(
    environment: StepEnvironment,
    candidates: object,
    needed: set[int],
) -> Mapping[int, np.ndarray]:
    result: dict[int, np.ndarray] = {}
    driver = getattr(environment, "driver", None)
    position_method = getattr(driver, "satellite_ecef_at", None)
    if callable(position_method):
        current = position_method(0)
        if not isinstance(current, Mapping):
            raise LCSRSC3EncoderError(
                "satellite_ecef_at did not return an identity map"
            )
        for norad in sorted(needed):
            if norad not in current:
                continue
            position = np.asarray(current[norad], dtype=np.float64)
            if position.shape != (3,) or not np.all(np.isfinite(position)):
                raise LCSRSC3EncoderError("current satellite position is malformed")
            result[norad] = _readonly_copy(
                position, dtype=np.dtype(np.float64)
            )

    # Candidate window coordinates are not used as the authority when the
    # physical driver is available.  They are checked as a stale-slot trap.
    window_ids_value = getattr(candidates, "window_norad_ids", None)
    window_ecef_value = getattr(candidates, "window_satellite_ecef_km", None)
    if window_ids_value is not None and window_ecef_value is not None:
        ids = np.asarray(window_ids_value)
        ecef = np.asarray(window_ecef_value, dtype=np.float64)
        if ids.ndim != 2 or ids.dtype == np.bool_ or not np.issubdtype(ids.dtype, np.integer) or ecef.shape != ids.shape + (3,):
            raise LCSRSC3EncoderError("candidate satellite window positions are malformed")
        for uid in range(ids.shape[0]):
            for slot in range(ids.shape[1]):
                norad = int(ids[uid, slot])
                if norad < 0:
                    continue
                position = ecef[uid, slot]
                if not np.all(np.isfinite(position)):
                    raise LCSRSC3EncoderError("candidate satellite positions must be finite")
                if norad in result and not np.allclose(
                    result[norad], position, rtol=0.0, atol=1e-9
                ):
                    raise LCSRSC3EncoderError("one NORAD id has inconsistent captured positions")
                result.setdefault(
                    norad,
                    _readonly_copy(position, dtype=np.dtype(np.float64)),
                )
    missing = sorted(needed - set(result))
    if missing and callable(position_method):
        current = position_method(0)
        if not isinstance(current, Mapping):
            raise LCSRSC3EncoderError("satellite_ecef_at did not return an identity map")
        for norad in missing:
            if norad in current:
                position = np.asarray(current[norad], dtype=np.float64)
                if position.shape != (3,) or not np.all(np.isfinite(position)):
                    raise LCSRSC3EncoderError("current satellite position is malformed")
                result[norad] = _readonly_copy(
                    position, dtype=np.dtype(np.float64)
                )
    missing = sorted(needed - set(result))
    if missing:
        raise LCSRSC3EncoderError(f"missing current position for satellites {missing}")
    return MappingProxyType(dict(result))


def _capture_users(environment: StepEnvironment, users: int) -> np.ndarray:
    driver = getattr(environment, "driver", None)
    method = getattr(driver, "user_ecef_km", None)
    value = method() if callable(method) else getattr(environment, "user_ecef_km", None)
    if value is None:
        raise LCSRSC3EncoderError("LC-SRS needs current user ECEF positions")
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (users, 3) or not np.all(np.isfinite(result)):
        raise LCSRSC3EncoderError("current user ECEF positions are malformed")
    return _readonly_copy(result, dtype=np.dtype(np.float64))


def _capture_candidate_geometry(
    tables: tuple[SlotTable, ...],
    positions: Mapping[int, np.ndarray],
    centers: np.ndarray,
    users_ecef: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Derive geometry from physical keys; never trust slot-index sidecars."""

    users = len(tables)
    theta = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    slant = np.zeros_like(theta)
    elevation = np.zeros_like(theta)

    for uid, table in enumerate(tables):
        for action in np.flatnonzero(table.mask).tolist():
            action = int(action)
            key = _key_from_action(table, action)
            assert key is not None
            norad, cell = key
            satellite = positions[norad]
            center = centers[cell]
            theta[uid, action] = float(
                angle_between_deg(satellite, center, users_ecef[uid])
            )
            range_value, elevation_value, _ = look_angles(
                satellite, users_ecef[uid]
            )
            slant[uid, action] = float(range_value)
            elevation[uid, action] = float(elevation_value)
            if (
                not np.isfinite(theta[uid, action])
                or not np.isfinite(slant[uid, action])
                or not np.isfinite(elevation[uid, action])
                or theta[uid, action] < 0.0
                or theta[uid, action] > 180.0
                or slant[uid, action] <= 0.0
                or elevation[uid, action] < -90.0
                or elevation[uid, action] > 90.0
            ):
                raise LCSRSC3EncoderError("legal candidate geometry is invalid")
    return (
        _readonly_copy(theta, dtype=np.dtype(np.float64)),
        _readonly_copy(slant, dtype=np.dtype(np.float64)),
        _readonly_copy(elevation, dtype=np.dtype(np.float64)),
    )


def _recompute_opening_surface(
    environment: StepEnvironment,
    *,
    step_index: int,
    tables: tuple[SlotTable, ...],
    theta_deg: np.ndarray,
    user_ecef: np.ndarray,
    associations: tuple[tuple[int, int] | None, ...],
    segments: tuple[_CapturedSegment | None, ...],
    p0: float,
    power_max: float,
) -> np.ndarray:
    """Build the execution-equivalent opening predicate from captured physics."""

    users = len(tables)
    legal = np.stack([table.mask for table in tables])
    current = np.where(legal, transmit_gain_linear(theta_deg), 0.0)
    starts = np.zeros_like(current)
    candidate_norads = np.stack([table.norad_ids for table in tables])
    candidate_cells = np.stack([table.cell_ids for table in tables])
    for uid in range(users):
        segment = segments[uid]
        starts[uid] = segment_start_gain_surface(
            candidate_norad_ids=candidate_norads[uid],
            candidate_cell_ids=candidate_cells[uid],
            current_gain_linear=current[uid],
            current_association=associations[uid],
            committed_start_gain_linear=(
                None if segment is None else segment.start_transmit_gain
            ),
            legal_mask=legal[uid],
        )
    if step_index == 0:
        # Reuse the canonical episode-boundary warm-start reconstruction.
        from .ee_axis_ops3_live import _opening_segment_start_gain_surface

        starts = _opening_segment_start_gain_surface(
            environment=environment,
            candidate_norad_ids=candidate_norads,
            candidate_cell_ids=candidate_cells,
            legal_mask=legal,
            current_gain_linear=starts,
            user_ecef_km=user_ecef,
        )
    opening = np.zeros_like(legal)
    for uid in range(users):
        opening[uid] = opening_service_feasibility_surface(
            legal_mask=legal[uid],
            segment_start_gain_linear=starts[uid],
            current_gain_linear=current[uid],
            p0_w=p0,
            pmax_w=power_max,
        )
    return _readonly_copy(opening, dtype=np.dtype(np.bool_))


def _association_key(value: object) -> tuple[int, int] | None:
    if value is None or value is UNSERVED:
        return None
    if isinstance(value, Association):
        return _key(value.norad_id, value.cell_id)
    norad = getattr(value, "norad_id", None)
    cell = getattr(value, "cell_id", None)
    if norad is None or cell is None:
        raise LCSRSC3EncoderError("previous association is malformed")
    try:
        norad_i, cell_i = int(norad), int(cell)
    except (TypeError, ValueError, OverflowError) as error:
        raise LCSRSC3EncoderError("previous association is malformed") from error
    if norad_i < 0 or cell_i < 0:
        raise LCSRSC3EncoderError("previous association is malformed")
    return _key(norad_i, cell_i)


def _capture_committed(environment: StepEnvironment, users: int, power_max: float) -> tuple[
    tuple[tuple[int, int] | None, ...],
    Mapping[tuple[int, int], int],
    Mapping[tuple[int, int], float],
    frozenset[int],
    np.ndarray,
    tuple[_CapturedSegment | None, ...],
]:
    previous_value = getattr(environment, "_previous_association", None)
    previous = [None] * users if previous_value is None else list(previous_value)
    if len(previous) != users:
        raise LCSRSC3EncoderError("previous associations are malformed")
    associations = tuple(_association_key(value) for value in previous)

    load: dict[tuple[int, int], int] = {}
    # The committed load is the load of the actual previous-slot associations,
    # matching ``ee_axis_state``'s eligible-served context.  Do not use the
    # environment's ungated ``_previous_demand`` here: it can include users
    # whose previous link was rejected by the power/service gate.
    for key in associations:
        if key is not None:
            load[key] = load.get(key, 0) + 1

    radiating = getattr(environment, "_previous_radiating", None)
    power_by_key: dict[tuple[int, int], float] = {}
    active_sats: set[int] = set()
    if radiating is not None:
        norads = np.asarray(getattr(radiating, "norad_ids", ()))
        cells = np.asarray(getattr(radiating, "cell_ids", ()))
        powers = np.asarray(getattr(radiating, "power_w", ()), dtype=np.float64)
        if norads.ndim != 1 or cells.shape != norads.shape or powers.shape != norads.shape:
            raise LCSRSC3EncoderError("previous radiating arrays disagree")
        if norads.dtype == np.bool_ or cells.dtype == np.bool_ or not np.issubdtype(norads.dtype, np.integer) or not np.issubdtype(cells.dtype, np.integer):
            raise LCSRSC3EncoderError("previous radiating identities are malformed")
        if not np.all(np.isfinite(powers)) or np.any(powers < 0.0) or np.any(powers > power_max):
            raise LCSRSC3EncoderError("previous radiating power is outside budget")
        for norad, cell, power in zip(norads.tolist(), cells.tolist(), powers.tolist(), strict=True):
            key = _key(norad, cell)
            if key in power_by_key:
                raise LCSRSC3EncoderError("previous radiating beam identities repeat")
            power_by_key[key] = float(power)
            active_sats.add(key[0])

    previous_power_value = getattr(environment, "_previous_link_power_w", None)
    previous_power = np.zeros(users, dtype=np.float64) if previous_power_value is None else np.asarray(previous_power_value, dtype=np.float64)
    if previous_power.shape != (users,) or not np.all(np.isfinite(previous_power)) or np.any(previous_power < 0.0) or np.any(previous_power > power_max):
        raise LCSRSC3EncoderError("previous recurrence powers are malformed")
    previous_power = _readonly_copy(previous_power, dtype=np.dtype(np.float64))

    segments_value = getattr(environment, "_segments", None)
    live_segments = tuple(
        [None] * users if segments_value is None else segments_value
    )
    if len(live_segments) != users:
        raise LCSRSC3EncoderError("previous segments are malformed")
    captured_segments: list[_CapturedSegment | None] = []
    for uid, (association, segment) in enumerate(
        zip(associations, live_segments, strict=True)
    ):
        if association is None:
            if segment is not None or previous_power[uid] != 0.0:
                raise LCSRSC3EncoderError("unserved previous state retains committed power")
            captured_segments.append(None)
        elif segment is None:
            raise LCSRSC3EncoderError("served incumbent lacks a power segment")
        else:
            segment_key = _association_key(segment)
            if segment_key != association:
                raise LCSRSC3EncoderError("incumbent and segment identities disagree")
            start_gain = _as_float(
                getattr(segment, "start_transmit_gain", None),
                field="segment.start_transmit_gain",
            )
            age_raw = getattr(segment, "age_steps", None)
            if (
                isinstance(age_raw, bool)
                or not isinstance(age_raw, (int, np.integer))
                or int(age_raw) < 0
            ):
                raise LCSRSC3EncoderError("segment age is malformed")
            if start_gain <= 0.0:
                raise LCSRSC3EncoderError("segment start gain must be positive")
            captured_segments.append(
                _CapturedSegment(
                    norad_id=association[0],
                    cell_id=association[1],
                    start_transmit_gain=start_gain,
                    age_steps=int(age_raw),
                )
            )
    return (
        associations,
        MappingProxyType(dict(load)),
        MappingProxyType(dict(power_by_key)),
        frozenset(active_sats),
        previous_power,
        tuple(captured_segments),
    )


def _read_q12(
    value: object,
    *,
    users: int,
) -> tuple[np.ndarray, str, str, str, str]:
    # Local import keeps the runtime schema independent while still requiring
    # the one authenticated producer type at the public capture boundary.
    from ..algorithms.ee_axis_lcsrs_three_route import DetachedQ12Snapshot

    if not isinstance(value, DetachedQ12Snapshot):
        raise LCSRSC3EncoderError(
            "q12 input must be an authenticated DetachedQ12Snapshot"
        )
    result = np.asarray(value.q12, dtype=np.float64)
    if result.shape != (users, NUM_ACTIONS) or not np.all(np.isfinite(result)):
        raise LCSRSC3EncoderError(f"detached Q12 must be finite shape ({users},28)")
    return (
        _readonly_copy(result, dtype=np.dtype(np.float64)),
        value.content_digest,
        value.source_state_digest,
        value.native_observation_event_digest,
        value.model_digest,
    )


def _prepare_snapshot(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    detached_q12: object,
    reference_actions: object,
    opening_feasibility_surface: object,
) -> _Snapshot:
    candidates = getattr(observation, "candidates", None)
    if candidates is None:
        raise LCSRSC3EncoderError("observation lacks candidate tables")
    users = int(getattr(observation, "num_users", 0))
    if users <= 0:
        user_states = getattr(observation, "user_states", None)
        users = len(user_states) if user_states is not None else 0
    if users <= 0:
        raise LCSRSC3EncoderError("LC-SRS needs at least one user")
    env_users = getattr(environment, "num_users", users)
    if int(env_users) != users:
        raise LCSRSC3EncoderError("environment and observation user counts disagree")
    step_index = int(getattr(observation, "step_index", -1))
    if step_index < 0:
        raise LCSRSC3EncoderError("observation step index is malformed")
    environment_step = getattr(environment, "_step_index", step_index)
    if int(environment_step) != step_index:
        raise LCSRSC3EncoderError(
            "environment and observation step indices disagree"
        )
    bound_candidates = getattr(environment, "_candidates", None)
    if bound_candidates is not None and bound_candidates is not candidates:
        raise LCSRSC3EncoderError("observation is not the environment's current candidate surface")

    tables_value = getattr(candidates, "slot_tables", None)
    if tables_value is None:
        raise LCSRSC3EncoderError("candidate surface lacks native slot tables")
    live_tables = tuple(tables_value)
    if len(live_tables) != users or any(
        not isinstance(table, SlotTable) for table in live_tables
    ):
        raise LCSRSC3EncoderError("candidate slot tables are malformed")
    tables = tuple(_copy_slot_table(table) for table in live_tables)
    legal = _readonly_copy(
        np.stack([table.mask for table in tables]),
        dtype=np.dtype(np.bool_),
    )
    native_masks_raw = np.asarray(getattr(observation, "masks", legal))
    if native_masks_raw.dtype != np.bool_:
        raise LCSRSC3EncoderError("observation masks must have Boolean dtype")
    native_masks = np.array(native_masks_raw, dtype=np.bool_, copy=True)
    if native_masks.shape != legal.shape or not np.array_equal(native_masks, legal):
        raise LCSRSC3EncoderError("observation masks disagree with native slot tables")
    if np.any(~np.any(legal, axis=1)):
        raise LCSRSC3EncoderError("LC-SRS C3 requires one legal action per user")

    opening = _bool_matrix(
        opening_feasibility_surface,
        field="opening_feasibility_surface",
        shape=(users, NUM_ACTIONS),
    )
    if np.any(opening & ~legal):
        raise LCSRSC3EncoderError("opening feasibility must be a subset of the native mask")
    (
        q12,
        q12_digest,
        q12_state_digest,
        q12_event_digest,
        q12_model_digest,
    ) = _read_q12(
        detached_q12,
        users=users,
    )
    current_q12_state = encode_ee_axis_state(environment, observation)
    if q12_state_digest != current_q12_state.state_sha256:
        raise LCSRSC3EncoderError(
            "detached Q12 belongs to a different native predecision state"
        )
    provenance = getattr(observation, "observation_provenance", None)
    if not isinstance(provenance, NativeObservationProvenance):
        raise LCSRSC3EncoderError(
            "V0.23 C3 requires native observation event provenance"
        )
    provenance.verify()
    if provenance.step_index != step_index:
        raise LCSRSC3EncoderError(
            "native observation provenance belongs to a different step"
        )
    if provenance.sinr_provenance != getattr(observation, "sinr_provenance", None):
        raise LCSRSC3EncoderError(
            "native observation SINR provenance label drifted"
        )
    field = getattr(environment, "_fading_field", None)
    if not isinstance(field, KeyedFadingField):
        raise LCSRSC3EncoderError(
            "V0.23 C3 requires the canonical keyed observation field"
        )
    if (
        provenance.field_root_digest != field.root_digest
        or provenance.field_mode != field.version
        or provenance.field_version != field.version
    ):
        raise LCSRSC3EncoderError(
            "native observation provenance disagrees with the keyed field"
        )
    if q12_event_digest != provenance.content_digest:
        raise LCSRSC3EncoderError(
            "detached Q12 belongs to a different native observation event"
        )

    refs = _int_vector(reference_actions, field="reference_actions", size=users)
    if np.any(refs < 0) or np.any(refs >= NUM_ACTIONS) or not np.all(legal[np.arange(users), refs]):
        raise LCSRSC3EncoderError("reference action is outside the native mask")
    expected = np.empty(users, dtype=np.int64)
    for uid in range(users):
        legal_actions = np.flatnonzero(legal[uid])
        expected[uid] = int(legal_actions[np.argmax(q12[uid, legal_actions])])
    if not np.array_equal(refs, expected):
        raise LCSRSC3EncoderError("reference_actions must be the native masked Q1+Q2 argmax")

    keys = [[_key_from_action(table, action) for action in range(NUM_ACTIONS)] for table in tables]
    all_keys = {key for row in keys for key in row if key is not None}
    centers, colors_array = _read_grid(environment, candidates, {key[1] for key in all_keys})
    positions = _capture_positions(environment, candidates, {key[0] for key in all_keys})
    users_ecef = _capture_users(environment, users)
    theta, slant, elevation = _capture_candidate_geometry(
        tables,
        positions,
        centers,
        users_ecef,
    )

    power_max = _as_float(getattr(getattr(environment, "physics", None), "beam_power_max_w", BEAM_POWER_MAX_W), field="beam_power_max_w")
    p0 = _as_float(getattr(getattr(environment, "physics", None), "segment_start_power_w", SEGMENT_START_POWER_W), field="segment_start_power_w")
    noise_value = getattr(getattr(environment, "physics", None), "noise_power_w", None)
    if callable(noise_value):
        noise_value = noise_value()
    noise = _as_float(noise_value, field="noise_power_w", default=noise_power_w())
    if power_max <= 0.0 or p0 <= 0.0 or noise <= 0.0 or p0 > power_max:
        raise LCSRSC3EncoderError("LC-SRS power/noise constants are inconsistent")
    (
        associations,
        committed_load,
        committed_power,
        committed_sats,
        previous_power,
        segments,
    ) = _capture_committed(environment, users, power_max)
    expected_opening = _recompute_opening_surface(
        environment,
        step_index=step_index,
        tables=tables,
        theta_deg=theta,
        user_ecef=users_ecef,
        associations=associations,
        segments=segments,
        p0=p0,
        power_max=power_max,
    )
    if not np.array_equal(opening, expected_opening):
        raise LCSRSC3EncoderError(
            "opening feasibility differs from the pure predecision predicate"
        )
    opening = expected_opening
    driver_config = getattr(getattr(getattr(environment, "driver", None), "config", None), "steps_per_episode", None)
    episode_length = int(driver_config if driver_config is not None else getattr(environment, "steps_per_episode", 1))
    if episode_length <= 0:
        raise LCSRSC3EncoderError("episode length must be positive")
    active_denominator = int(colors_array.size)
    if active_denominator <= 0:
        raise LCSRSC3EncoderError("cell map must contain at least one cell")

    return _Snapshot(
        users=users,
        step_index=step_index,
        legal=legal,
        opening=opening,
        tables=tables,
        q12=q12,
        q12_snapshot_digest=q12_digest,
        q12_source_state_digest=q12_state_digest,
        q12_native_observation_event_digest=q12_event_digest,
        q12_model_digest=q12_model_digest,
        native_observation_provenance=provenance,
        state_schema=current_q12_state.schema,
        state_schema_sha256=current_q12_state.schema_sha256,
        state_sha256=current_q12_state.state_sha256,
        refs=_readonly_copy(refs, dtype=np.dtype(np.int64)),
        user_ecef=users_ecef,
        centers=centers,
        colors=colors_array,
        positions=positions,
        candidate_theta_deg=theta,
        candidate_slant_km=slant,
        candidate_elevation_deg=elevation,
        committed_associations=associations,
        committed_load=committed_load,
        committed_power=committed_power,
        committed_satellites=committed_sats,
        previous_link_power=previous_power,
        segments=segments,
        power_max=power_max,
        p0=p0,
        noise=noise,
        episode_length=episode_length,
        active_beam_count_denominator=active_denominator,
    )


def _geometry_for_key(snapshot: _Snapshot, user: int, key: tuple[int, int] | None) -> tuple[float, float, float]:
    if key is None:
        return 0.0, 0.0, 0.0
    norad, cell = key
    satellite = snapshot.positions.get(norad)
    if satellite is None or cell < 0 or cell >= snapshot.centers.shape[0]:
        raise LCSRSC3EncoderError("geometry endpoint is outside the captured snapshot")
    theta = float(angle_between_deg(satellite, snapshot.centers[cell], snapshot.user_ecef[user]))
    slant, elevation, _ = look_angles(satellite, snapshot.user_ecef[user])
    return _angle_bound(theta), _distance_bound(float(slant)), _elevation_bound(float(elevation))


def _reference_geometry(snapshot: _Snapshot, user: int) -> tuple[float, float, float]:
    action = int(snapshot.refs[user])
    return (
        _angle_bound(float(snapshot.candidate_theta_deg[user, action])),
        _distance_bound(float(snapshot.candidate_slant_km[user, action])),
        _elevation_bound(float(snapshot.candidate_elevation_deg[user, action])),
    )


def _relation_one_hot(
    candidate: tuple[int, int] | None,
    reference: tuple[int, int] | None,
    colors: Mapping[int, int],
) -> list[float]:
    if candidate is None or reference is None:
        return [0.0] * 6
    sat_a, cell_a = candidate
    sat_b, cell_b = reference
    if candidate == reference:
        return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    same_sat = sat_a == sat_b
    same_cell = cell_a == cell_b
    same_color = int(colors[cell_a]) == int(colors[cell_b])
    if same_sat and not same_cell and same_color:
        return [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    if same_sat and not same_cell and not same_color:
        return [0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    if not same_sat and same_cell:
        return [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    if not same_sat and not same_cell and same_color:
        return [0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    return [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def _legal_rank(snapshot: _Snapshot, user: int, action: int) -> float:
    legal = np.flatnonzero(snapshot.legal[user])
    ordered = sorted((int(a) for a in legal.tolist()), key=lambda a: (-snapshot.q12[user, a], a))
    rank = ordered.index(action)
    return float(rank) / float(max(1, len(ordered) - 1))


def _committed_temporal(
    snapshot: _Snapshot,
    user: int,
) -> tuple[float, float, float, float]:
    """Return committed temporal state, independent of candidate action.

    These three fields describe the actual incumbent carried into the current
    decision.  They are repeated across a user's legal action rows; treating
    every non-incumbent candidate as a missing incumbent would instead encode
    a hypothetical action outcome and invert the frozen schema semantics.
    """

    association = snapshot.committed_associations[user]
    segment = snapshot.segments[user]
    if association is None:
        return 0.0, 0.0, 0.0, 1.0
    if segment is None:
        raise LCSRSC3EncoderError("served incumbent lacks a segment")
    seg_norad = int(getattr(segment, "norad_id", -1))
    seg_cell = int(getattr(segment, "cell_id", -1))
    if (seg_norad, seg_cell) != association:
        raise LCSRSC3EncoderError("incumbent and segment identities disagree")
    start_gain = _as_float(getattr(segment, "start_transmit_gain", None), field="segment.start_transmit_gain")
    if start_gain <= 0.0:
        raise LCSRSC3EncoderError("segment start gain must be positive")
    age_raw = getattr(segment, "age_steps", None)
    if isinstance(age_raw, bool) or not isinstance(age_raw, (int, np.integer)) or int(age_raw) < 0:
        raise LCSRSC3EncoderError("segment age is malformed")
    age = int(age_raw)
    # A warm-start segment may predate the current episode.  Preserve age/H
    # for ordinary values but saturate older valid segments so C3View remains
    # within its frozen [-1, 1] feature domain.
    bounded_age = min(age, snapshot.episode_length)
    # The current candidate geometry is looked up from the captured table,
    # never from a post-action object.
    current_theta = None
    for action in np.flatnonzero(snapshot.legal[user]).tolist():
        if _key_from_action(snapshot.tables[user], int(action)) == association:
            if current_theta is not None:
                raise LCSRSC3EncoderError("incumbent physical identity repeats in candidate table")
            current_theta = float(snapshot.candidate_theta_deg[user, int(action)])
    if current_theta is None:
        return 0.0, 0.0, 0.0, 1.0
    current_gain = float(transmit_gain_linear(np.asarray([current_theta], dtype=np.float64))[0])
    if not math.isfinite(current_gain) or current_gain < 0.0:
        raise LCSRSC3EncoderError("current incumbent transmit gain is malformed")
    power = float(snapshot.previous_link_power[user]) / snapshot.power_max
    if power < 0.0 or power > 1.0:
        raise LCSRSC3EncoderError("previous recurrence power exceeds its bound")
    return (
        power,
        _bounded_nonnegative(current_gain / start_gain),
        float(bounded_age) / float(snapshot.episode_length),
        0.0,
    )


def _endpoint_coupling(snapshot: _Snapshot, victim: int, key: tuple[int, int] | None, reference_key: tuple[int, int] | None) -> float:
    """Deterministic received coupling per segment-start watt."""
    if key is None or reference_key is None:
        return 0.0
    norad, cell = key
    satellite = snapshot.positions.get(norad)
    if satellite is None:
        return 0.0
    theta = float(angle_between_deg(satellite, snapshot.centers[cell], snapshot.user_ecef[victim]))
    slant, elevation, _ = look_angles(satellite, snapshot.user_ecef[victim])
    path = float(link_power_factor(np.asarray(slant), np.asarray(elevation), np.asarray(1.0), shadow_fading_db=0.0))
    wanted_norad = reference_key[0]
    if wanted_norad == norad:
        receive = _RX_MAX_LINEAR
    else:
        serving_satellite = snapshot.positions.get(wanted_norad)
        if serving_satellite is None:
            return 0.0
        separation = float(angle_between_deg(snapshot.user_ecef[victim], serving_satellite, satellite))
        receive = float(receive_gain_linear(np.asarray(separation)))
    coupling = float(transmit_gain_linear(np.asarray(theta)) * path * receive)
    if not math.isfinite(coupling) or coupling < 0.0:
        raise LCSRSC3EncoderError("deterministic coupling is malformed")
    return coupling


def _source_maps(snapshot: _Snapshot) -> tuple[dict[tuple[int, int], list[int]], dict[tuple[int, int], int], dict[tuple[int, int], int]]:
    users_by_key: dict[tuple[int, int], list[int]] = {}
    for uid, action in enumerate(snapshot.refs.tolist()):
        physical = _key_from_action(snapshot.tables[uid], int(action))
        assert physical is not None
        users_by_key.setdefault(physical, []).append(uid)
    occupancy = {key: len(value) for key, value in users_by_key.items()}
    ready = {key: sum(bool(snapshot.opening[uid, snapshot.refs[uid]]) for uid in users) for key, users in users_by_key.items()}
    return users_by_key, occupancy, ready


def _nonmember_count(users_by_key: Mapping[tuple[int, int], Sequence[int]], key: tuple[int, int] | None, pair: tuple[int, int]) -> int:
    if key is None:
        return 0
    return sum(uid not in pair for uid in users_by_key.get(key, ()))


def _other_active_fraction(snapshot: _Snapshot, key: tuple[int, int] | None) -> float:
    if key is None:
        return 0.0
    sat, _cell = key
    count = sum(1 for active_key in snapshot.committed_power if active_key[0] == sat and active_key != key)
    return float(count) / float(snapshot.active_beam_count_denominator)


def _committed_fields(snapshot: _Snapshot, key: tuple[int, int] | None) -> tuple[float, float, float, float]:
    if key is None:
        return 0.0, 0.0, 0.0, 0.0
    load = float(snapshot.committed_load.get(key, 0)) / float(snapshot.users)
    active = float(key in snapshot.committed_power)
    satellite_active = float(key[0] in snapshot.committed_satellites)
    power = float(snapshot.committed_power.get(key, 0.0)) / snapshot.power_max
    if load < 0.0 or load > 1.0 or power < 0.0 or power > 1.0:
        raise LCSRSC3EncoderError("committed descriptor exceeds its normalization bound")
    return load, active, satellite_active, power


def _action_context(snapshot: _Snapshot, users_by_key: Mapping[tuple[int, int], Sequence[int]], occupancy: Mapping[tuple[int, int], int], ready: Mapping[tuple[int, int], int]) -> np.ndarray:
    context = np.zeros((snapshot.users, NUM_ACTIONS, 29), dtype=np.float32)
    for uid, table in enumerate(snapshot.tables):
        reference = _key_from_action(table, int(snapshot.refs[uid]))
        for action in np.flatnonzero(snapshot.legal[uid]).tolist():
            action = int(action)
            candidate = _key_from_action(table, action)
            assert candidate is not None
            row = context[uid, action]
            row[0] = _angle_bound(float(snapshot.candidate_theta_deg[uid, action]))
            row[1] = _distance_bound(float(snapshot.candidate_slant_km[uid, action]))
            row[2] = _elevation_bound(float(snapshot.candidate_elevation_deg[uid, action]))
            row[3] = float(snapshot.opening[uid, action])
            row[4:10] = _relation_one_hot(candidate, reference, {int(i): int(value) for i, value in enumerate(snapshot.colors.tolist())})
            incumbent = snapshot.committed_associations[uid]
            row[10] = float(candidate == incumbent and incumbent is not None)
            row[11:15] = _committed_fields(snapshot, candidate)
            row[15:19] = _committed_fields(snapshot, reference)
            row[19:23] = _committed_temporal(snapshot, uid)
            row[23] = math.tanh(float(snapshot.q12[uid, action] - snapshot.q12[uid, snapshot.refs[uid]]))
            row[24] = _legal_rank(snapshot, uid, action)
            source_occupancy = occupancy.get(reference, 0) if reference is not None else 0
            source_ready = ready.get(reference, 0) if reference is not None else 0
            destination_occupancy = occupancy.get(candidate, 0)
            destination_ready = ready.get(candidate, 0)
            row[25] = float(source_occupancy) / float(snapshot.users)
            row[26] = float(source_ready) / float(snapshot.users)
            row[27] = float(destination_occupancy) / float(snapshot.users)
            row[28] = float(destination_ready) / float(snapshot.users)
    return context


def _pair_info(
    snapshot: _Snapshot,
    topology: LCSRSC3AnchorTopologyReceipt,
) -> tuple[
    dict[int, int],
    dict[int, tuple[int, int] | None],
    dict[int, np.ndarray],
]:
    """Read designated moves only from the predeclared topology receipt."""

    designated_action = {uid: -1 for uid in range(snapshot.users)}
    designated_key: dict[int, tuple[int, int] | None] = {
        uid: None for uid in range(snapshot.users)
    }
    partner_margins = {
        uid: np.zeros(0, dtype=np.float64) for uid in range(snapshot.users)
    }
    for pair in topology.pairs:
        for index, uid in enumerate(pair.member_users):
            action = int(pair.designated_actions[index])
            designated_action[uid] = action
            designated_key[uid] = pair.destination_keys[index]
            eligible = pair.eligible_actions_by_member[index]
            partner_margins[uid] = np.asarray(
                [
                    snapshot.q12[uid, candidate]
                    - snapshot.q12[uid, snapshot.refs[uid]]
                    for candidate in eligible
                ],
                dtype=np.float64,
            )
    return designated_action, designated_key, partner_margins


def _victim_set(snapshot: _Snapshot, focal: int, *, reference_key: tuple[int, int], candidate_key: tuple[int, int], partner: int | None, partner_destination: tuple[int, int] | None) -> set[int]:
    changed: set[tuple[int, int]] = {reference_key, candidate_key}
    if partner is not None and partner_destination is not None:
        changed.add(partner_destination)
    result: set[int] = {focal}
    if partner is not None:
        result.add(partner)
    colors = {int(i): int(value) for i, value in enumerate(snapshot.colors.tolist())}
    for victim in range(snapshot.users):
        victim_key = _key_from_action(snapshot.tables[victim], int(snapshot.refs[victim]))
        assert victim_key is not None
        if any(victim_key == key or _cochannel(victim_key, key, colors) for key in changed):
            result.add(victim)
    return result


def _ordinary_token(snapshot: _Snapshot, focal: int, action: int, victim: int, *, reference_key: tuple[int, int], candidate_key: tuple[int, int], partner: int | None, partner_destination: tuple[int, int] | None, users_by_key: Mapping[tuple[int, int], Sequence[int]]) -> np.ndarray:
    token = np.zeros(38, dtype=np.float32)
    token[0:2] = (1.0, 0.0)
    token[2] = float(victim == focal)
    token[3] = float(partner is not None and victim == partner)
    victim_ref = _key_from_action(snapshot.tables[victim], int(snapshot.refs[victim]))
    assert victim_ref is not None
    partner_destination_value = partner_destination
    token[4] = float(victim_ref == reference_key)
    token[5] = float(victim_ref == candidate_key)
    token[6] = float(partner_destination_value is not None and victim_ref == partner_destination_value)
    token[7] = float(snapshot.opening[victim, snapshot.refs[victim]])
    token[8] = float(len(users_by_key.get(victim_ref, ()))) / float(snapshot.users)
    token[9] = float(sum(bool(snapshot.opening[u, snapshot.refs[u]]) for u in users_by_key.get(victim_ref, ()))) / float(snapshot.users)
    token[10:13] = _reference_geometry(snapshot, victim)
    token[13:16] = _geometry_for_key(snapshot, victim, reference_key)
    token[16:19] = _geometry_for_key(snapshot, victim, candidate_key)
    token[19:22] = _geometry_for_key(snapshot, victim, partner_destination_value)
    colors = {int(i): int(value) for i, value in enumerate(snapshot.colors.tolist())}
    token[22] = float(_cochannel(reference_key, victim_ref, colors))
    token[23] = float(_cochannel(candidate_key, victim_ref, colors))
    token[24] = float(partner_destination_value is not None and _cochannel(partner_destination_value, victim_ref, colors))
    token[25] = float(reference_key == victim_ref)
    token[26] = float(candidate_key == victim_ref)
    token[27] = float(partner_destination_value is not None and partner_destination_value == victim_ref)
    token[28] = float((candidate_key == victim_ref) - (reference_key == victim_ref)) / float(snapshot.users)
    if partner is not None and partner_destination_value is not None:
        token[29] = float((partner_destination_value == victim_ref) + (candidate_key == victim_ref) - 2 * (reference_key == victim_ref)) / float(snapshot.users)
    token[30] = float(snapshot.opening[focal, snapshot.refs[focal]])
    token[31] = float(snapshot.opening[focal, action])
    if partner is not None:
        partner_action = -1
        for candidate_action in np.flatnonzero(snapshot.legal[partner]).tolist():
            if _key_from_action(snapshot.tables[partner], int(candidate_action)) == partner_destination_value:
                partner_action = int(candidate_action)
                break
        token[32] = float(partner_action >= 0 and snapshot.opening[partner, partner_action])
    token[33] = _bounded_nonnegative(snapshot.p0 * _endpoint_coupling(snapshot, victim, reference_key, victim_ref) / snapshot.noise)
    token[34] = _bounded_nonnegative(snapshot.p0 * _endpoint_coupling(snapshot, victim, candidate_key, victim_ref) / snapshot.noise)
    token[35] = _bounded_nonnegative(snapshot.p0 * _endpoint_coupling(snapshot, victim, partner_destination_value, victim_ref) / snapshot.noise)
    token[36] = _bounded_nonnegative(snapshot.p0 * _endpoint_coupling(snapshot, victim, victim_ref, victim_ref) / snapshot.noise)
    legal = np.flatnonzero(snapshot.legal[victim])
    legal_mean = float(np.mean(snapshot.q12[victim, legal]))
    token[37] = math.tanh(float(snapshot.q12[victim, snapshot.refs[victim]] - legal_mean))
    return token


def _pair_token(snapshot: _Snapshot, focal: int, action: int, partner: int | None, source_key: tuple[int, int], focal_destination: tuple[int, int] | None, partner_destination: tuple[int, int] | None, users_by_key: Mapping[tuple[int, int], Sequence[int]], occupancy: Mapping[tuple[int, int], int], designated_action: Mapping[int, int], partner_margins: Mapping[int, np.ndarray]) -> np.ndarray:
    token = np.zeros(38, dtype=np.float32)
    token[0:2] = (0.0, 1.0)
    if partner is None:
        return token
    pair = (focal, partner)
    source_two = occupancy.get(source_key, 0) == 2
    da_focal = int(designated_action.get(focal, -1))
    da_partner = int(designated_action.get(partner, -1))
    supported = source_two and da_focal >= 0 and da_partner >= 0
    token[2] = float(source_two)
    token[3] = float(supported)
    if not supported:
        # C3View's unsupported sentinel is exactly [type, (1,0,0)] with a
        # zero tail; no other pair evidence may leak through this path.
        return token
    current_key = _key_from_action(snapshot.tables[focal], action)
    designated_focal_key = _key_from_action(snapshot.tables[focal], da_focal)
    token[4] = float(current_key == designated_focal_key)
    token[5] = float(snapshot.opening[focal, da_focal])
    token[6] = float(snapshot.opening[partner, da_partner])
    token[7] = float(focal_destination == partner_destination)
    token[8] = float(occupancy.get(source_key, 0)) / float(snapshot.users)
    token[9] = float(_nonmember_count(users_by_key, focal_destination, pair)) / float(snapshot.users)
    token[10] = float(_nonmember_count(users_by_key, partner_destination, pair)) / float(snapshot.users)
    token[11] = float(sum(bool(snapshot.opening[u, snapshot.refs[u]]) for u in users_by_key.get(focal_destination, ()) if u not in pair)) / float(snapshot.users)
    token[12] = float(sum(bool(snapshot.opening[u, snapshot.refs[u]]) for u in users_by_key.get(partner_destination, ()) if u not in pair)) / float(snapshot.users)
    token[13] = _other_active_fraction(snapshot, source_key)
    token[14] = _other_active_fraction(snapshot, focal_destination)
    token[15] = _other_active_fraction(snapshot, partner_destination)
    for offset, key in enumerate((source_key, focal_destination, partner_destination)):
        load, active, sat_active, power = _committed_fields(snapshot, key)
        del load
        token[16 + offset] = active
        token[19 + offset] = power
        token[22 + offset] = sat_active
    token[25:28] = _geometry_for_key(snapshot, partner, partner_destination)
    token[28:31] = _geometry_for_key(snapshot, focal, partner_destination)
    ref_focal = snapshot.q12[focal, snapshot.refs[focal]]
    ref_partner = snapshot.q12[partner, snapshot.refs[partner]]
    focal_margin = snapshot.q12[focal, da_focal] - ref_focal
    partner_margin = snapshot.q12[partner, da_partner] - ref_partner
    margins = partner_margins.get(partner, np.zeros(0, dtype=np.float64))
    token[31] = math.tanh(float(focal_margin))
    token[32] = math.tanh(float(partner_margin))
    token[33] = math.tanh(float(np.min(margins))) if margins.size else 0.0
    token[34] = math.tanh(float(np.max(margins))) if margins.size else 0.0
    token[35] = math.tanh(float(np.mean(margins))) if margins.size else 0.0
    token[36] = math.tanh(float(ref_focal))
    token[37] = math.tanh(float(ref_partner))
    return token


def _physical_key_surface(snapshot: _Snapshot) -> np.ndarray:
    keys = np.full((snapshot.users, NUM_ACTIONS, 2), -1, dtype=np.int64)
    for uid, table in enumerate(snapshot.tables):
        keys[uid, :, 0] = table.norad_ids
        keys[uid, :, 1] = table.cell_ids
    return keys


def _verify_topology_binding(
    snapshot: _Snapshot,
    topology: LCSRSC3AnchorTopologyReceipt,
) -> None:
    topology.verify()
    capture = topology.capture
    if capture.phase != snapshot.step_index:
        raise LCSRSC3EncoderError("topology phase differs from captured anchor")
    if capture.q12_snapshot.content_digest != snapshot.q12_snapshot_digest:
        raise LCSRSC3EncoderError("topology uses a different detached Q12 snapshot")
    if not np.array_equal(capture.action_mask, snapshot.legal):
        raise LCSRSC3EncoderError("topology native mask differs from encoder capture")
    if not np.array_equal(capture.opening_feasibility, snapshot.opening):
        raise LCSRSC3EncoderError("topology opening surface differs from encoder capture")
    if not np.array_equal(capture.reference_actions, snapshot.refs):
        raise LCSRSC3EncoderError("topology references differ from encoder capture")
    if not np.array_equal(capture.physical_keys, _physical_key_surface(snapshot)):
        raise LCSRSC3EncoderError("topology physical keys differ from encoder capture")


def _build_view(
    snapshot: _Snapshot,
    topology: LCSRSC3AnchorTopologyReceipt,
) -> C3View:
    _verify_topology_binding(snapshot, topology)
    users_by_key, occupancy, ready = _source_maps(snapshot)
    context = _action_context(snapshot, users_by_key, occupancy, ready)
    designated_action, designated_key, partner_margins = _pair_info(
        snapshot,
        topology,
    )
    tokens = np.zeros((snapshot.users, NUM_ACTIONS, snapshot.users + 1, 38), dtype=np.float32)
    token_mask = np.zeros((snapshot.users, NUM_ACTIONS, snapshot.users + 1), dtype=np.bool_)
    for focal, table in enumerate(snapshot.tables):
        source_key = _key_from_action(table, int(snapshot.refs[focal]))
        assert source_key is not None
        members = users_by_key.get(source_key, ())
        partner = None
        if occupancy.get(source_key, 0) == 2:
            partner = int(members[0] if int(members[1]) == focal else members[1])
        pair_is_supported = partner is not None and designated_action.get(focal, -1) >= 0 and designated_action.get(partner, -1) >= 0
        for action in np.flatnonzero(snapshot.legal[focal]).tolist():
            action = int(action)
            candidate_key = _key_from_action(table, action)
            assert candidate_key is not None
            focal_destination = designated_key.get(focal) if pair_is_supported else candidate_key
            partner_destination = designated_key.get(partner) if pair_is_supported and partner is not None else None
            relation = _victim_set(snapshot, focal, reference_key=source_key, candidate_key=candidate_key, partner=partner if pair_is_supported else None, partner_destination=partner_destination)
            for victim in sorted(relation):
                tokens[focal, action, victim] = _ordinary_token(snapshot, focal, action, victim, reference_key=source_key, candidate_key=candidate_key, partner=partner if pair_is_supported else None, partner_destination=partner_destination, users_by_key=users_by_key)
                token_mask[focal, action, victim] = True
            tokens[focal, action, snapshot.users] = _pair_token(snapshot, focal, action, partner if occupancy.get(source_key, 0) == 2 else None, source_key, candidate_key if not pair_is_supported else designated_key.get(focal), designated_key.get(partner) if pair_is_supported and partner is not None else None, users_by_key, occupancy, designated_action, partner_margins)
            token_mask[focal, action, snapshot.users] = True
    return assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=snapshot.legal,
        reference_actions=snapshot.refs,
    )


def capture_lcsrs_c3_predecision(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    world_id: int,
    anchor_id: str,
    detached_q12: object,
    reference_actions: object,
    opening_feasibility_surface: object,
) -> LCSRSC3PredecisionCapture:
    """Freeze topology first, then encode one outcome-blind C3 view.

    The caller must supply the immutable ``DetachedQ12Snapshot`` and its
    already selected native masked references.  This feature encoder verifies
    those references but never selects an action itself.  All environment
    reads happen during the initial snapshot boundary; descriptor construction
    below is pure.
    """

    snapshot = _prepare_snapshot(
        environment,
        observation,
        detached_q12=detached_q12,
        reference_actions=reference_actions,
        opening_feasibility_surface=opening_feasibility_surface,
    )
    topology_capture = LCSRSC3AnchorCapture(
        world_id=world_id,
        phase=snapshot.step_index,
        anchor_id=anchor_id,
        q12_snapshot=detached_q12,
        action_mask=snapshot.legal,
        opening_feasibility=snapshot.opening,
        physical_keys=_physical_key_surface(snapshot),
        reference_actions=snapshot.refs,
    )
    topology = enumerate_lcsrs_c3_anchor(topology_capture)
    view = _build_view(snapshot, topology)
    return LCSRSC3PredecisionCapture(
        topology=topology,
        view=view,
        native_observation_provenance=snapshot.native_observation_provenance,
        state_schema=snapshot.state_schema,
        state_schema_sha256=snapshot.state_schema_sha256,
        state_sha256=snapshot.state_sha256,
    )


def encode_lcsrs_c3_view(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    world_id: int,
    anchor_id: str,
    detached_q12: object,
    reference_actions: object,
    opening_feasibility_surface: object,
) -> C3View:
    """Compatibility projection of the authenticated predecision capture."""

    return capture_lcsrs_c3_predecision(
        environment,
        observation,
        world_id=world_id,
        anchor_id=anchor_id,
        detached_q12=detached_q12,
        reference_actions=reference_actions,
        opening_feasibility_surface=opening_feasibility_surface,
    ).view


# Explicit alias used by different V0.23 adapters and test harnesses.
encode_ee_axis_lcsrs_c3_view = encode_lcsrs_c3_view


__all__ = [
    "LCSRSC3EncoderError",
    "LCSRSC3PredecisionCapture",
    "encode_lcsrs_c3_view",
    "capture_lcsrs_c3_predecision",
    "encode_ee_axis_lcsrs_c3_view",
]
