"""Live deterministic projection adapter for the PNFE C3 oracle.

The adapter shares exact OPS-3's detached predecision anchor, native future
TLE/D2 projection, opening-service rule, and focal persistence surface.  It
then freezes every non-focal user's committed physical segment and evaluates
two branches at each offset: the common focal-removed background and that
same background plus exactly one focal candidate segment.

Only non-focal delivered rates leave this module.  Future learned actions,
realised successor outcomes, network-energy terms, and reward terms are not
read.  Unit fading and zero shadowing match the deterministic OPS-3 oracle
convention; this is a bounded development shadow, not a second simulator.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import hashlib
import math
from typing import Sequence

import numpy as np

from ..env.action_contract import NUM_ACTIONS, Association
from ..env.antenna import RX_GAIN_MAX_DBI
from ..env.ephemeris import SatelliteSet, step_times
from ..env.interference import (
    beam_field_at_users,
    build_radiating_beams,
    co_channel_interference,
    received_power_terms,
)
from ..env.link_budget import (
    BEAM_POWER_MAX_W,
    SEGMENT_START_POWER_W,
    classify_link_power_feasibility,
    recurrence_power_w,
    shannon_rate_bps,
)
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_ops3 import OPS3_HORIZON, OPS3Surface
from .ee_axis_ops3_live import OPS3AnchorSnapshot, OPS3ProjectionReceipt
from .ee_axis_pnfe import PNFEOffset, PNFESurface, build_pnfe_surface


PNFE_LIVE_SCHEMA = "multi-catfish-mcrl-v09-c3-pnfe-live-anchor-v1"
PNFE_LIVE_RECEIPT_SCHEMA = "multi-catfish-mcrl-v09-c3-pnfe-live-receipt-v1"
_RX_GAIN_MAX_LINEAR = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)


class PNFELiveError(MCRLContractError):
    """The PNFE committed-background or shared-projection contract failed."""


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _hash_array(digest: "hashlib._Hash", name: str, value: object) -> None:
    array = np.ascontiguousarray(np.asarray(value))
    digest.update(name.encode("ascii"))
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(array.shape).encode("ascii"))
    digest.update(array.tobytes(order="C"))


@dataclass(frozen=True)
class PNFEAnchorSnapshot:
    """Detached committed service state bound to one OPS-3 anchor."""

    committed: np.ndarray
    committed_actions: np.ndarray
    committed_norad_ids: np.ndarray
    committed_cell_ids: np.ndarray
    segment_start_gain_linear: np.ndarray
    ops3_anchor_sha256: str
    snapshot_sha256: str
    schema: str = PNFE_LIVE_SCHEMA

    def __post_init__(self) -> None:
        committed = np.asarray(self.committed)
        if committed.dtype != np.bool_ or committed.ndim != 1:
            raise PNFELiveError("committed must be a Boolean user vector")
        users = int(committed.size)
        for field in (
            "committed_actions",
            "committed_norad_ids",
            "committed_cell_ids",
        ):
            value = np.asarray(getattr(self, field))
            if value.shape != (users,) or value.dtype == np.bool_ or not np.issubdtype(
                value.dtype, np.integer
            ):
                raise PNFELiveError(f"{field} must be an integer user vector")
            object.__setattr__(self, field, _readonly(value, dtype=np.int64))
        start = np.asarray(self.segment_start_gain_linear, dtype=np.float64)
        if start.shape != (users,) or not np.all(np.isfinite(start)) or np.any(start < 0.0):
            raise PNFELiveError(
                "segment_start_gain_linear must be a finite non-negative user vector"
            )
        if np.any(committed & (start <= 0.0)):
            raise PNFELiveError("every committed segment needs positive start gain")
        if np.any(committed & (self.committed_actions < 0)):
            raise PNFELiveError("every committed segment must map to a live legal action")
        if self.schema != PNFE_LIVE_SCHEMA:
            raise PNFELiveError("PNFEAnchorSnapshot schema is stale")
        for field in ("ops3_anchor_sha256", "snapshot_sha256"):
            value = getattr(self, field)
            if not isinstance(value, str) or len(value) != 64:
                raise PNFELiveError(f"{field} must be a SHA-256 digest")
        object.__setattr__(self, "committed", _readonly(committed, dtype=np.bool_))
        object.__setattr__(
            self,
            "segment_start_gain_linear",
            _readonly(start, dtype=np.float64),
        )

    @property
    def num_users(self) -> int:
        return int(self.committed.size)


@dataclass(frozen=True)
class PNFELiveReceipt:
    """Authenticated C3 surfaces constructed from one shared C2 projection."""

    surfaces: tuple[PNFESurface, ...]
    ops3_anchor_sha256: str
    ops3_projection_sha256: str
    pnfe_anchor_sha256: str
    receipt_sha256: str
    schema: str = PNFE_LIVE_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if not isinstance(self.surfaces, tuple) or not self.surfaces or any(
            not isinstance(surface, PNFESurface) for surface in self.surfaces
        ):
            raise PNFELiveError("receipt must contain PNFE surfaces")
        for field in (
            "ops3_anchor_sha256",
            "ops3_projection_sha256",
            "pnfe_anchor_sha256",
            "receipt_sha256",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or len(value) != 64:
                raise PNFELiveError(f"{field} must be a SHA-256 digest")
        if self.schema != PNFE_LIVE_RECEIPT_SCHEMA:
            raise PNFELiveError("PNFELiveReceipt schema is stale")
        self.verify()

    def verify(self) -> str:
        actual = _receipt_digest(
            anchor_sha256=self.ops3_anchor_sha256,
            projection_sha256=self.ops3_projection_sha256,
            pnfe_sha256=self.pnfe_anchor_sha256,
            surfaces=self.surfaces,
        )
        if actual != self.receipt_sha256:
            raise PNFELiveError("PNFE live receipt was modified")
        return actual


def _snapshot_digest(
    *,
    ops3_anchor_sha256: str,
    committed: np.ndarray,
    actions: np.ndarray,
    norads: np.ndarray,
    cells: np.ndarray,
    starts: np.ndarray,
) -> str:
    digest = hashlib.sha256(ops3_anchor_sha256.encode("ascii"))
    for name, value in (
        ("committed", committed),
        ("actions", actions),
        ("norads", norads),
        ("cells", cells),
        ("starts", starts),
    ):
        _hash_array(digest, name, value)
    return digest.hexdigest()


def snapshot_pnfe_anchor(
    environment: StepEnvironment,
    observation: StepObservation,
    ops3_anchor: OPS3AnchorSnapshot,
) -> PNFEAnchorSnapshot:
    """Freeze the committed segment universe without reading an outcome sign."""

    if not isinstance(environment, StepEnvironment) or not isinstance(
        observation, StepObservation
    ):
        raise PNFELiveError("environment and observation have stale types")
    if not isinstance(ops3_anchor, OPS3AnchorSnapshot):
        raise PNFELiveError("ops3_anchor must be an OPS3AnchorSnapshot")
    if observation.candidates is not environment._candidates:
        raise PNFELiveError("observation is not the live predecision anchor")
    if observation.step_index != ops3_anchor.step_index:
        raise PNFELiveError("PNFE and OPS-3 step indices disagree")
    users = environment.num_users
    if ops3_anchor.num_users != users:
        raise PNFELiveError("PNFE and OPS-3 user universes disagree")

    committed = np.zeros(users, dtype=np.bool_)
    actions = np.full(users, -1, dtype=np.int64)
    norads = np.full(users, -1, dtype=np.int64)
    cells = np.full(users, -1, dtype=np.int64)
    starts = np.zeros(users, dtype=np.float64)
    for uid, (association, segment) in enumerate(
        zip(environment._previous_association, environment._segments, strict=True)
    ):
        if association is None:
            if segment is not None:
                raise PNFELiveError("unserved user carries a committed segment")
            continue
        if not isinstance(association, Association):
            raise PNFELiveError("committed association has a stale type")
        if segment is None or not segment.continues(association):
            raise PNFELiveError("committed association and segment disagree")
        pair = (int(association.norad_id), int(association.cell_id))
        matches = np.flatnonzero(
            ops3_anchor.legal_mask[uid]
            & (ops3_anchor.candidate_norad_ids[uid] == pair[0])
            & (ops3_anchor.candidate_cell_ids[uid] == pair[1])
        )
        # A frozen committed background is fail-closed: if the incumbent is
        # absent from the current legal action table, it cannot be projected
        # as a serviceable victim segment.
        if matches.size == 0:
            continue
        if matches.size != 1:
            raise PNFELiveError("committed physical association is not unique")
        action = int(matches[0])
        committed[uid] = True
        actions[uid] = action
        norads[uid], cells[uid] = pair
        starts[uid] = float(segment.start_transmit_gain)

    snapshot_sha = _snapshot_digest(
        ops3_anchor_sha256=ops3_anchor.anchor_sha256,
        committed=committed,
        actions=actions,
        norads=norads,
        cells=cells,
        starts=starts,
    )
    return PNFEAnchorSnapshot(
        committed=committed,
        committed_actions=actions,
        committed_norad_ids=norads,
        committed_cell_ids=cells,
        segment_start_gain_linear=starts,
        ops3_anchor_sha256=ops3_anchor.anchor_sha256,
        snapshot_sha256=snapshot_sha,
    )


def _position_maps(
    anchor: OPS3AnchorSnapshot,
    projection: OPS3ProjectionReceipt,
) -> tuple[dict[int, np.ndarray], ...]:
    times: list[dt.datetime] = [
        anchor.start_utc
        + dt.timedelta(seconds=anchor.step_index * anchor.decision_step_s)
    ]
    times.extend(projection.offset_times_utc[: projection.horizon])
    satellites = SatelliteSet(anchor._satellite_records)
    result: list[dict[int, np.ndarray]] = []
    for when in times:
        jd, fr = step_times(when, 1, time_step_s=anchor.decision_step_s)
        positions, _ = satellites.propagate_ecef_state(
            jd, fr, require_all_healthy=False
        )
        if positions.shape != (anchor.tracked_norad_ids.size, 1, 3):
            raise PNFELiveError("projected satellite positions have the wrong shape")
        result.append(
            {
                int(norad): np.asarray(positions[index, 0], dtype=np.float64)
                for index, norad in enumerate(anchor.tracked_norad_ids.tolist())
            }
        )
    return tuple(result)


def _committed_service_states(
    pnfe: PNFEAnchorSnapshot,
    anchor: OPS3AnchorSnapshot,
    projection: OPS3ProjectionReceipt,
) -> tuple[tuple[np.ndarray, np.ndarray], ...]:
    """Return absorbing served/power vectors at h=0..Ht."""

    users = pnfe.num_users
    alive = np.array(pnfe.committed, dtype=np.bool_, copy=True)
    power = np.zeros(users, dtype=np.float64)
    for uid in np.flatnonzero(alive).tolist():
        action = int(pnfe.committed_actions[uid])
        gain = float(anchor.current_gain_linear[uid, action])
        if gain <= 0.0:
            alive[uid] = False
            continue
        value = float(
            recurrence_power_w(
                pnfe.segment_start_gain_linear[uid],
                gain,
                p0_w=SEGMENT_START_POWER_W,
            )
        )
        if not math.isfinite(value) or bool(
            classify_link_power_feasibility(
                np.asarray([value]), max_power_w=BEAM_POWER_MAX_W
            )[0]
        ):
            alive[uid] = False
            continue
        power[uid] = value
    states: list[tuple[np.ndarray, np.ndarray]] = [
        (_readonly(alive, dtype=np.bool_), _readonly(power, dtype=np.float64))
    ]
    for offset_index in range(projection.horizon):
        next_power = np.zeros(users, dtype=np.float64)
        for uid in np.flatnonzero(alive).tolist():
            action = int(pnfe.committed_actions[uid])
            offset = projection.offsets_by_user[uid][offset_index]
            gain = float(offset.projected_gain_linear[action])
            support = bool(
                offset.d2_eligible[action]
                and offset.cell_visible[action]
                and gain > 0.0
            )
            if not support:
                alive[uid] = False
                continue
            value = float(
                recurrence_power_w(
                    pnfe.segment_start_gain_linear[uid],
                    gain,
                    p0_w=SEGMENT_START_POWER_W,
                )
            )
            if not math.isfinite(value) or bool(
                classify_link_power_feasibility(
                    np.asarray([value]), max_power_w=BEAM_POWER_MAX_W
                )[0]
            ):
                alive[uid] = False
                continue
            next_power[uid] = value
        power = next_power
        states.append(
            (_readonly(alive, dtype=np.bool_), _readonly(power, dtype=np.float64))
        )
    return tuple(states)


def _rates_for_branch(
    *,
    anchor: OPS3AnchorSnapshot,
    pnfe: PNFEAnchorSnapshot,
    positions: dict[int, np.ndarray],
    served: np.ndarray,
    link_power_w: np.ndarray,
    focal_user: int,
    focal_action: int | None,
    focal_power_w: float,
) -> np.ndarray:
    """Evaluate deterministic non-focal rates for one frozen branch."""

    users = pnfe.num_users
    active = np.asarray(served, dtype=np.bool_).copy()
    power = np.asarray(link_power_w, dtype=np.float64).copy()
    active[focal_user] = False
    power[focal_user] = 0.0

    norads = np.array(pnfe.committed_norad_ids, copy=True)
    cells = np.array(pnfe.committed_cell_ids, copy=True)
    extra_pair: tuple[int, int] | None = None
    if focal_action is not None:
        extra_pair = (
            int(anchor.candidate_norad_ids[focal_user, focal_action]),
            int(anchor.candidate_cell_ids[focal_user, focal_action]),
        )
        if extra_pair[0] not in positions or extra_pair[1] < 0:
            raise PNFELiveError("active focal insertion lacks projected identity")

    beam_members: dict[tuple[int, int], list[float]] = {}
    for uid in np.flatnonzero(active).tolist():
        pair = (int(norads[uid]), int(cells[uid]))
        if pair[0] not in positions or pair[1] < 0 or power[uid] <= 0.0:
            raise PNFELiveError("active committed victim has stale service state")
        beam_members.setdefault(pair, []).append(float(power[uid]))
    if extra_pair is not None:
        if not math.isfinite(focal_power_w) or focal_power_w <= 0.0:
            raise PNFELiveError("active focal insertion needs positive finite power")
        beam_members.setdefault(extra_pair, []).append(float(focal_power_w))

    if not beam_members:
        return np.zeros(users, dtype=np.float64)
    pairs = sorted(beam_members)
    radiating = build_radiating_beams(
        beam_norad_ids=np.asarray([pair[0] for pair in pairs], dtype=np.int64),
        beam_cell_ids=np.asarray([pair[1] for pair in pairs], dtype=np.int64),
        beam_power_w=np.asarray(
            [max(beam_members[pair]) for pair in pairs], dtype=np.float64
        ),
        satellite_ecef_by_norad=positions,
        grid=anchor._grid,
    )
    field = beam_field_at_users(
        user_ecef_km=anchor.user_ecef_km,
        radiating=radiating,
    )
    boresight = np.array(anchor.user_ecef_km, copy=True)
    boresight_ids = np.full(users, -1, dtype=np.int64)
    for uid in np.flatnonzero(active).tolist():
        boresight[uid] = positions[int(norads[uid])]
        boresight_ids[uid] = int(norads[uid])
    terms = received_power_terms(
        field,
        radiating,
        user_ecef_km=anchor.user_ecef_km,
        boresight_satellite_ecef_km=boresight,
        boresight_norad_ids=boresight_ids,
    )
    colors = np.where(active, anchor._grid.colors[np.maximum(cells, 0)], -1)
    interference = co_channel_interference(
        terms,
        radiating,
        wanted_norad_ids=np.where(active, norads, -1),
        wanted_cell_ids=np.where(active, cells, -1),
        wanted_colors=colors,
    )
    pair_index = {pair: index for index, pair in enumerate(pairs)}
    wanted = np.zeros(users, dtype=np.float64)
    load = np.zeros(users, dtype=np.float64)
    for uid in np.flatnonzero(active).tolist():
        pair = (int(norads[uid]), int(cells[uid]))
        column = pair_index[pair]
        wanted[uid] = (
            power[uid]
            * field.transmit_gain[uid, column]
            * field.path_gain[uid, column]
            * field.fading_gain[uid, column]
            * _RX_GAIN_MAX_LINEAR
        )
        load[uid] = float(len(beam_members[pair]))
    gamma = np.where(
        active,
        wanted / (interference.total_w + anchor.noise_power_w),
        0.0,
    )
    rates = np.where(
        active,
        shannon_rate_bps(
            gamma,
            beam_load=np.where(active, load, 1.0),
            bandwidth_hz=anchor.beam_bandwidth_hz,
        ),
        0.0,
    )
    rates[focal_user] = 0.0
    if not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
        raise PNFELiveError("PNFE branch produced malformed non-focal rates")
    return rates


def _opening_focal_state(
    anchor: OPS3AnchorSnapshot,
    focal_user: int,
    c2_surface: OPS3Surface,
) -> tuple[np.ndarray, np.ndarray]:
    legal = np.asarray(anchor.legal_mask[focal_user], dtype=np.bool_)
    gain = np.asarray(anchor.current_gain_linear[focal_user], dtype=np.float64)
    start = np.asarray(
        anchor.segment_start_gain_linear[focal_user], dtype=np.float64
    )
    power = np.zeros(NUM_ACTIONS, dtype=np.float64)
    positive = legal & (gain > 0.0)
    if np.any(positive):
        power[positive] = recurrence_power_w(
            start[positive], gain[positive], p0_w=SEGMENT_START_POWER_W
        )
    infeasible = classify_link_power_feasibility(
        power, max_power_w=BEAM_POWER_MAX_W
    )
    active = legal & positive & np.isfinite(power) & ~infeasible
    if not np.array_equal(active, c2_surface.opening_service_feasible):
        raise PNFELiveError(
            "PNFE opening gate disagrees with the exact C2 receipt"
        )
    power = np.where(active, power, 0.0)
    return active, power


def _offset_for_focal(
    *,
    anchor: OPS3AnchorSnapshot,
    pnfe: PNFEAnchorSnapshot,
    positions: dict[int, np.ndarray],
    served: np.ndarray,
    link_power_w: np.ndarray,
    focal_user: int,
    focal_active: np.ndarray,
    focal_power_w: np.ndarray,
) -> PNFEOffset:
    """Build one offset with a vectorised single-beam insertion delta.

    The non-focal wanted signals never change between branches.  A focal
    insertion can only (a) add one user to the same-beam load and (b) add or
    raise one radiating beam's co-channel field.  Computing those two deltas
    for all actions at once is algebraically identical to rebuilding the
    whole network for each action and avoids an action-by-network loop.
    """

    users = pnfe.num_users
    active = np.asarray(served, dtype=np.bool_).copy()
    power = np.asarray(link_power_w, dtype=np.float64).copy()
    active[focal_user] = False
    power[focal_user] = 0.0
    norads = np.asarray(pnfe.committed_norad_ids, dtype=np.int64)
    cells = np.asarray(pnfe.committed_cell_ids, dtype=np.int64)

    beam_members: dict[tuple[int, int], list[float]] = {}
    for uid in np.flatnonzero(active).tolist():
        pair = (int(norads[uid]), int(cells[uid]))
        if pair[0] not in positions or pair[1] < 0 or power[uid] <= 0.0:
            raise PNFELiveError("active committed victim has stale service state")
        beam_members.setdefault(pair, []).append(float(power[uid]))

    wanted = np.zeros(users, dtype=np.float64)
    base_interference = np.zeros(users, dtype=np.float64)
    base_load = np.zeros(users, dtype=np.float64)
    boresight = np.array(anchor.user_ecef_km, copy=True)
    boresight_ids = np.full(users, -1, dtype=np.int64)
    if beam_members:
        pairs = sorted(beam_members)
        radiating = build_radiating_beams(
            beam_norad_ids=np.asarray([pair[0] for pair in pairs], dtype=np.int64),
            beam_cell_ids=np.asarray([pair[1] for pair in pairs], dtype=np.int64),
            beam_power_w=np.asarray(
                [max(beam_members[pair]) for pair in pairs], dtype=np.float64
            ),
            satellite_ecef_by_norad=positions,
            grid=anchor._grid,
        )
        field = beam_field_at_users(
            user_ecef_km=anchor.user_ecef_km,
            radiating=radiating,
        )
        for uid in np.flatnonzero(active).tolist():
            boresight[uid] = positions[int(norads[uid])]
            boresight_ids[uid] = int(norads[uid])
        terms = received_power_terms(
            field,
            radiating,
            user_ecef_km=anchor.user_ecef_km,
            boresight_satellite_ecef_km=boresight,
            boresight_norad_ids=boresight_ids,
        )
        colors = np.where(active, anchor._grid.colors[np.maximum(cells, 0)], -1)
        interference = co_channel_interference(
            terms,
            radiating,
            wanted_norad_ids=np.where(active, norads, -1),
            wanted_cell_ids=np.where(active, cells, -1),
            wanted_colors=colors,
        )
        base_interference = interference.total_w
        pair_index = {pair: index for index, pair in enumerate(pairs)}
        for uid in np.flatnonzero(active).tolist():
            pair = (int(norads[uid]), int(cells[uid]))
            column = pair_index[pair]
            wanted[uid] = (
                power[uid]
                * field.transmit_gain[uid, column]
                * field.path_gain[uid, column]
                * field.fading_gain[uid, column]
                * _RX_GAIN_MAX_LINEAR
            )
            base_load[uid] = float(len(beam_members[pair]))

    base_gamma = np.where(
        active,
        wanted / (base_interference + anchor.noise_power_w),
        0.0,
    )
    background_all = np.where(
        active,
        shannon_rate_bps(
            base_gamma,
            beam_load=np.where(active, base_load, 1.0),
            bandwidth_hz=anchor.beam_bandwidth_hz,
        ),
        0.0,
    )

    if not bool(np.any(active)):
        victims = np.arange(users, dtype=np.int64) != focal_user
        background = np.zeros(int(np.count_nonzero(victims)), dtype=np.float64)
        return PNFEOffset(
            background_rate_bps=background,
            inserted_rate_bps=np.zeros(
                (NUM_ACTIONS, background.size), dtype=np.float64
            ),
            focal_active=np.asarray(focal_active, dtype=np.bool_),
        )

    inserted_all = np.tile(background_all[:, None], (1, NUM_ACTIONS))
    active_actions = np.flatnonzero(focal_active)
    if active_actions.size:
        candidate_norads = np.asarray(
            anchor.candidate_norad_ids[focal_user], dtype=np.int64
        )
        candidate_cells = np.asarray(
            anchor.candidate_cell_ids[focal_user], dtype=np.int64
        )
        candidate_colors = anchor._grid.colors[
            np.maximum(candidate_cells[active_actions], 0)
        ]
        background_max = {
            pair: max(values) for pair, values in beam_members.items()
        }
        delta_power = np.asarray(
            [
                max(
                    0.0,
                    float(focal_power_w[action])
                    - float(
                        background_max.get(
                            (int(candidate_norads[action]), int(candidate_cells[action])),
                            0.0,
                        )
                    ),
                )
                for action in active_actions.tolist()
            ],
            dtype=np.float64,
        )

        delta_interference = np.zeros((users, active_actions.size), dtype=np.float64)
        positive_columns = np.flatnonzero(delta_power > 0.0)
        if positive_columns.size:
            positive_actions = active_actions[positive_columns]
            delta_beams = build_radiating_beams(
                beam_norad_ids=candidate_norads[positive_actions],
                beam_cell_ids=candidate_cells[positive_actions],
                beam_power_w=delta_power[positive_columns],
                satellite_ecef_by_norad=positions,
                grid=anchor._grid,
            )
            delta_field = beam_field_at_users(
                user_ecef_km=anchor.user_ecef_km,
                radiating=delta_beams,
            )
            delta_terms = received_power_terms(
                delta_field,
                delta_beams,
                user_ecef_km=anchor.user_ecef_km,
                boresight_satellite_ecef_km=boresight,
                boresight_norad_ids=boresight_ids,
            )
            victim_colors = np.where(
                active, anchor._grid.colors[np.maximum(cells, 0)], -1
            )
            same_satellite = (
                norads[:, None]
                == candidate_norads[positive_actions][None, :]
            )
            same_cell = (
                cells[:, None]
                == candidate_cells[positive_actions][None, :]
            )
            co_colour = (
                victim_colors[:, None]
                == anchor._grid.colors[
                    np.maximum(candidate_cells[positive_actions], 0)
                ][None, :]
            )
            contributes = active[:, None] & co_colour & (
                (same_satellite & ~same_cell) | ~same_satellite
            )
            delta_interference[:, positive_columns] = np.where(
                contributes, delta_terms, 0.0
            )

        load = np.tile(base_load[:, None], (1, active_actions.size))
        same_beam = active[:, None] & (
            norads[:, None] == candidate_norads[active_actions][None, :]
        ) & (
            cells[:, None] == candidate_cells[active_actions][None, :]
        )
        load += same_beam.astype(np.float64)
        gamma = np.where(
            active[:, None],
            wanted[:, None]
            / (
                base_interference[:, None]
                + delta_interference
                + anchor.noise_power_w
            ),
            0.0,
        )
        new_rates = np.where(
            active[:, None],
            shannon_rate_bps(
                gamma,
                beam_load=np.where(active[:, None], load, 1.0),
                bandwidth_hz=anchor.beam_bandwidth_hz,
            ),
            0.0,
        )
        inserted_all[:, active_actions] = new_rates

    victims = np.arange(pnfe.num_users, dtype=np.int64) != focal_user
    background = background_all[victims]
    inserted = inserted_all[victims].T
    return PNFEOffset(
        background_rate_bps=background,
        inserted_rate_bps=inserted,
        focal_active=np.asarray(focal_active, dtype=np.bool_),
    )


def _receipt_digest(
    *,
    anchor_sha256: str,
    projection_sha256: str,
    pnfe_sha256: str,
    surfaces: Sequence[PNFESurface],
) -> str:
    digest = hashlib.sha256()
    for value in (anchor_sha256, projection_sha256, pnfe_sha256):
        digest.update(value.encode("ascii"))
    for uid, surface in enumerate(surfaces):
        digest.update(f"u={uid}".encode("ascii"))
        for name in ("x3_bits", "z3_bits", "q3_values", "externality_bits"):
            _hash_array(digest, name, getattr(surface, name))
    return digest.hexdigest()


def build_pnfe_live_surfaces(
    pnfe: PNFEAnchorSnapshot,
    anchor: OPS3AnchorSnapshot,
    projection: OPS3ProjectionReceipt,
    c2_surfaces: Sequence[OPS3Surface],
    reference_actions: Sequence[int] | np.ndarray,
) -> PNFELiveReceipt:
    """Build all users' PNFE oracle surfaces from one shared C2 projection."""

    if not isinstance(pnfe, PNFEAnchorSnapshot) or not isinstance(
        anchor, OPS3AnchorSnapshot
    ):
        raise PNFELiveError("PNFE/OPS-3 anchors have stale types")
    if not isinstance(projection, OPS3ProjectionReceipt):
        raise PNFELiveError("projection has a stale type")
    if pnfe.ops3_anchor_sha256 != anchor.anchor_sha256:
        raise PNFELiveError("PNFE snapshot belongs to another OPS-3 anchor")
    expected_pnfe_sha = _snapshot_digest(
        ops3_anchor_sha256=pnfe.ops3_anchor_sha256,
        committed=pnfe.committed,
        actions=pnfe.committed_actions,
        norads=pnfe.committed_norad_ids,
        cells=pnfe.committed_cell_ids,
        starts=pnfe.segment_start_gain_linear,
    )
    if expected_pnfe_sha != pnfe.snapshot_sha256:
        raise PNFELiveError("PNFE committed-background snapshot was modified")
    if projection.anchor_sha256 != anchor.anchor_sha256:
        raise PNFELiveError("projection belongs to another OPS-3 anchor")
    c2 = tuple(c2_surfaces)
    if len(c2) != anchor.num_users or any(
        not isinstance(surface, OPS3Surface) for surface in c2
    ):
        raise PNFELiveError("one exact C2 surface is required per user")
    reference = np.asarray(reference_actions)
    if reference.dtype == np.bool_ or not np.issubdtype(reference.dtype, np.integer):
        raise PNFELiveError("reference actions must be integers")
    if reference.shape != (anchor.num_users,):
        raise PNFELiveError("reference actions must be a user vector")

    positions = _position_maps(anchor, projection)
    services = _committed_service_states(pnfe, anchor, projection)
    surfaces: list[PNFESurface] = []
    for uid in range(anchor.num_users):
        if not np.array_equal(c2[uid].legal_mask, anchor.legal_mask[uid]):
            raise PNFELiveError("C2 and C3 legal masks disagree")
        if c2[uid].reference_action != int(reference[uid]):
            raise PNFELiveError("C2 and C3 reference actions disagree")
        if c2[uid].horizon != projection.horizon:
            raise PNFELiveError("C2 and C3 horizons disagree")
        opening_active, opening_power = _opening_focal_state(anchor, uid, c2[uid])
        opening = _offset_for_focal(
            anchor=anchor,
            pnfe=pnfe,
            positions=positions[0],
            served=services[0][0],
            link_power_w=services[0][1],
            focal_user=uid,
            focal_active=opening_active,
            focal_power_w=opening_power,
        )
        future: list[PNFEOffset] = []
        for offset_index in range(projection.horizon):
            c2_surface = c2[uid]
            active = np.asarray(
                c2_surface.persistence[offset_index] > 0.0, dtype=np.bool_
            )
            power = np.asarray(
                c2_surface.required_power_w[offset_index], dtype=np.float64
            )
            future.append(
                _offset_for_focal(
                    anchor=anchor,
                    pnfe=pnfe,
                    positions=positions[offset_index + 1],
                    served=services[offset_index + 1][0],
                    link_power_w=services[offset_index + 1][1],
                    focal_user=uid,
                    focal_active=active,
                    focal_power_w=power,
                )
            )
        surfaces.append(
            build_pnfe_surface(
                legal_mask=anchor.legal_mask[uid],
                reference_action=int(reference[uid]),
                opening=opening,
                future=tuple(future),
                step_index=anchor.step_index,
                total_steps=anchor.total_steps,
            )
        )
    receipt_sha = _receipt_digest(
        anchor_sha256=anchor.anchor_sha256,
        projection_sha256=projection.projection_sha256,
        pnfe_sha256=pnfe.snapshot_sha256,
        surfaces=surfaces,
    )
    return PNFELiveReceipt(
        surfaces=tuple(surfaces),
        ops3_anchor_sha256=anchor.anchor_sha256,
        ops3_projection_sha256=projection.projection_sha256,
        pnfe_anchor_sha256=pnfe.snapshot_sha256,
        receipt_sha256=receipt_sha,
    )


__all__ = [
    "PNFE_LIVE_RECEIPT_SCHEMA",
    "PNFE_LIVE_SCHEMA",
    "PNFEAnchorSnapshot",
    "PNFELiveError",
    "PNFELiveReceipt",
    "build_pnfe_live_surfaces",
    "snapshot_pnfe_anchor",
]
