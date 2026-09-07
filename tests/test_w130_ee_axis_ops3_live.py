"""W-130 -- bounded live OPS-3 TLE/D2 adapter mechanics.

These tests stop at the detached projection and formula-surface boundary.  A
real TLE reset and one ordinary environment step are enough to exercise the
adapter; no outcome panel, training run, or efficacy claim is opened here.
"""

from __future__ import annotations

from collections.abc import Mapping
import copy
import dataclasses
import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.d2 import D2Config
from mcrl.env.link_budget import BEAM_POWER_MAX_W, SEGMENT_START_POWER_W, recurrence_power_w
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime import ee_axis_ops3_live as live
from mcrl.runtime.ee_axis_ops3_live import (
    OPS3AnchorSnapshot,
    OPS3LiveError,
    OPS3ProjectionReceipt,
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
_START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
_D2_PER_DECISION = 47


def _environment(
    *,
    users: int = 2,
    steps: int = 4,
    seed: int = 2026090201,
    segment_warm_start: str = "none",
) -> tuple[StepEnvironment, object, np.random.Generator]:
    """Create a small real-TLE environment with deterministic live mechanics."""

    driver = ScenarioDriver(
        TleArchive(_ARCHIVE),
        ScenarioConfig(
            steps_per_episode=steps,
            mobility=MobilityConfig(num_users=users),
        ),
    )
    environment = StepEnvironment(
        driver,
        # The live projection itself must be median/no-fading.  Keeping the
        # current smoke deterministic also makes exact state comparisons
        # independent of a second random draw in the ordinary observation.
        physics=PhysicsConfig(
            fading_enabled=False, segment_warm_start=segment_warm_start
        ),
    )
    rng = np.random.default_rng(seed)
    observation = environment.reset(_START, rng)
    return environment, observation, rng


def _first_low_angle_actions(observation: object) -> np.ndarray:
    candidates = observation.candidates  # type: ignore[attr-defined]
    masks = np.asarray(observation.masks, dtype=np.bool_)  # type: ignore[attr-defined]
    angles = np.asarray(candidates.off_axis_deg, dtype=np.float64).reshape(
        masks.shape
    )
    actions: list[int] = []
    for uid, mask in enumerate(masks):
        legal = np.flatnonzero(mask & np.isfinite(angles[uid]))
        if legal.size == 0:
            actions.append(-1)
            continue
        actions.append(int(legal[np.argmin(angles[uid, legal])]))
    return np.asarray(actions, dtype=np.int64)


def _canonical(value: object) -> object:
    """Turn the selected live/private state into an exact comparable value."""

    if isinstance(value, np.ndarray):
        return (
            "ndarray",
            value.dtype.str,
            tuple(value.shape),
            value.tobytes(order="C"),
        )
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                ((_canonical(key), _canonical(item)) for key, item in value.items()),
                key=repr,
            )
        )
    if isinstance(value, (tuple, list)):
        return tuple(_canonical(item) for item in value)
    if dataclasses.is_dataclass(value):
        return (
            type(value).__name__,
            tuple(
                (field.name, _canonical(getattr(value, field.name)))
                for field in dataclasses.fields(value)
            ),
        )
    if isinstance(value, dt.datetime):
        return ("datetime", value.isoformat())
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if hasattr(value, "__dict__"):
        return (
            type(value).__name__,
            _canonical(
                {
                    key: item
                    for key, item in vars(value).items()
                    if key not in {"_array", "_satrecs"}
                }
            ),
        )
    return repr(value)


def _live_state(environment: StepEnvironment, rng: np.random.Generator) -> object:
    driver = environment.driver
    tracker = driver._tracker
    satellites = driver._satellites
    radiating = environment._previous_radiating
    return _canonical(
        {
            "environment": {
                "step_index": environment._step_index,
                "started": environment._started,
                "candidate_id": id(environment._candidates),
                "candidates": environment._candidates,
                "segments": environment._segments,
                "ledgers": environment._ledgers,
                "previous_association": environment._previous_association,
                "previous_link_power_w": environment._previous_link_power_w,
                "previous_served_rate_bps": environment._previous_served_rate_bps,
                "previous_demand": environment._previous_demand,
                "previous_radiating": radiating,
                "pending_segment_age": environment._pending_segment_age,
            },
            "driver": {
                "step_index": driver.step_index,
                "start_utc": driver._start_utc,
                "frozen_window": driver._frozen_window_norad_ids,
                "users": driver._users,
                "dwell": driver._dwell,
                "tracker": tracker,
                "satellite_id": id(satellites),
                "satellite_records": None if satellites is None else satellites.records,
            },
            "rng": copy.deepcopy(rng.bit_generator.state),
            "mobility_rng": (
                None
                if environment._mobility_rng is None
                else copy.deepcopy(environment._mobility_rng.bit_generator.state)
            ),
            "age_rng": (
                None
                if environment._age_rng is None
                else copy.deepcopy(environment._age_rng.bit_generator.state)
            ),
        }
    )


def _assert_projection_equal(
    first: OPS3ProjectionReceipt, second: OPS3ProjectionReceipt
) -> None:
    assert first.horizon == second.horizon
    assert first.future_d2_indices == second.future_d2_indices
    assert first.sample_times_utc == second.sample_times_utc
    assert first.offset_times_utc == second.offset_times_utc
    assert first.anchor_sha256 == second.anchor_sha256
    assert first.tracker_seed_sha256 == second.tracker_seed_sha256
    assert first.projection_sha256 == second.projection_sha256
    assert len(first.offsets_by_user) == len(second.offsets_by_user)
    for first_user, second_user in zip(
        first.offsets_by_user, second.offsets_by_user, strict=True
    ):
        assert len(first_user) == len(second_user)
        for first_offset, second_offset in zip(
            first_user, second_user, strict=True
        ):
            for name in (
                "projected_gain_linear",
                "d2_eligible",
                "cell_visible",
                "focal_rate_bps",
                "focal_sinr_linear",
            ):
                np.testing.assert_array_equal(
                    getattr(first_offset, name), getattr(second_offset, name)
                )


def _surfaces(result: tuple[object, ...], users: int) -> tuple[object, ...]:
    assert isinstance(result, tuple)
    assert len(result) == users
    return result


@pytest.fixture(scope="module")
def real_t0() -> tuple[StepEnvironment, object, np.random.Generator, OPS3AnchorSnapshot, OPS3ProjectionReceipt]:
    if not _ARCHIVE.is_dir():
        pytest.skip("TLE archive not present")
    environment, observation, rng = _environment(users=2, steps=4)
    snapshot = snapshot_ops3_anchor(environment, observation)
    assert isinstance(snapshot, OPS3AnchorSnapshot)
    projection = project_ops3_anchor(snapshot)
    assert isinstance(projection, OPS3ProjectionReceipt)
    return environment, observation, rng, snapshot, projection


@requires_archive
def test_real_tle_t0_projection_has_three_horizon_blocks_and_native_d2_schedule(real_t0) -> None:
    _environment, _observation, _rng, snapshot, projection = real_t0

    assert snapshot.step_index == 0
    assert snapshot.horizon == 3
    assert projection.horizon == 3
    assert len(projection.offsets_by_user) == snapshot.num_users
    assert all(len(offsets) == 3 for offsets in projection.offsets_by_user)

    indices = np.asarray(projection.future_d2_indices, dtype=np.int64)
    assert indices.shape == (3 * _D2_PER_DECISION,)
    expected = np.arange(
        (snapshot.step_index + 1) * _D2_PER_DECISION,
        (snapshot.step_index + 1 + projection.horizon) * _D2_PER_DECISION,
        dtype=np.int64,
    )
    np.testing.assert_array_equal(indices, expected)
    for block in range(projection.horizon):
        block_indices = indices[
            block * _D2_PER_DECISION : (block + 1) * _D2_PER_DECISION
        ]
        assert block_indices.size == _D2_PER_DECISION
        assert block_indices[0] == (snapshot.step_index + 1 + block) * _D2_PER_DECISION


@pytest.mark.usefixtures("real_t0")
@requires_archive
def test_real_tle_projection_preserves_native_action_identities_and_is_deterministic(real_t0) -> None:
    environment, observation, _rng, snapshot, projection = real_t0
    expected_norads = np.stack(
        [table.norad_ids for table in observation.candidates.slot_tables]
    )
    expected_cells = np.stack(
        [table.cell_ids for table in observation.candidates.slot_tables]
    )
    np.testing.assert_array_equal(snapshot.candidate_norad_ids, expected_norads)
    np.testing.assert_array_equal(snapshot.candidate_cell_ids, expected_cells)
    np.testing.assert_array_equal(snapshot.legal_mask, observation.masks)
    assert snapshot.candidate_norad_ids.shape == (snapshot.num_users, NUM_ACTIONS)
    assert snapshot.candidate_cell_ids.shape == (snapshot.num_users, NUM_ACTIONS)

    for uid, offsets in enumerate(projection.offsets_by_user):
        assert len(offsets) == projection.horizon
        for offset in offsets:
            assert offset.projected_gain_linear.shape == (NUM_ACTIONS,)
            assert offset.d2_eligible.shape == (NUM_ACTIONS,)
            assert offset.cell_visible.shape == (NUM_ACTIONS,)
            # Offset rows are action aligned with the frozen (NORAD, cell)
            # table; no future policy is allowed to rename them.
            assert np.all(offset.d2_eligible <= snapshot.legal_mask[uid])
            assert np.all(offset.cell_visible <= snapshot.legal_mask[uid])

    repeated = project_ops3_anchor(snapshot)
    _assert_projection_equal(projection, repeated)
    assert environment.driver.step_index == snapshot.step_index


@pytest.mark.usefixtures("real_t0")
@requires_archive
def test_snapshot_and_projection_leave_live_driver_tracker_environment_and_rng_unchanged(real_t0) -> None:
    environment, observation, rng, snapshot, _projection = real_t0
    before = _live_state(environment, rng)
    snapshot_again = snapshot_ops3_anchor(environment, observation)
    _assert_projection_equal(
        project_ops3_anchor(snapshot), project_ops3_anchor(snapshot_again)
    )
    after = _live_state(environment, rng)
    assert after == before


@requires_archive
def test_live_surfaces_have_exact_reference_zero_and_native_mask_safety(real_t0) -> None:
    environment, observation, _rng, snapshot, projection = real_t0
    references = _first_low_angle_actions(observation)
    surfaces = _surfaces(
        build_ops3_live_surfaces(snapshot, projection, references),
        snapshot.num_users,
    )
    for uid, surface in enumerate(surfaces):
        assert surface.reference_action == int(references[uid])
        assert surface.horizon == 3
        np.testing.assert_array_equal(surface.legal_mask, observation.masks[uid])
        assert surface.q2_values[int(references[uid])] == 0.0
        assert np.all(np.isfinite(surface.q2_values[observation.masks[uid]]))
        assert np.all(surface.q2_values[~observation.masks[uid]] == 0.0)
        assert np.all(np.isfinite(surface.features))
        assert np.all(np.isfinite(surface.z2_bits))


@requires_archive
def test_t0_warm_start_opening_gate_matches_execution_for_every_legal_action(
    monkeypatch,
) -> None:
    """The h=0 OPS-3 gate must use the simulator's per-user warm age."""

    forced_age = np.array([3], dtype=np.int64)
    monkeypatch.setattr(
        StepEnvironment,
        "_draw_segment_ages",
        lambda _self, _rng: forced_age.copy(),
    )
    environment, observation, rng = _environment(
        users=1,
        steps=4,
        seed=2026090211,
        segment_warm_start="uniform-episode-length",
    )
    before = _live_state(environment, rng)
    snapshot = snapshot_ops3_anchor(environment, observation)
    projection = project_ops3_anchor(snapshot)
    references = _first_low_angle_actions(observation)
    surface = _surfaces(
        build_ops3_live_surfaces(snapshot, projection, references), 1
    )[0]

    legal = np.flatnonzero(observation.masks[0])
    assert legal.size > 0
    for action in legal.tolist():
        actions = np.asarray([action], dtype=np.int64)
        evaluation = environment.evaluate_actions(actions, rng)
        current = float(snapshot.current_gain_linear[0, action])
        start = float(snapshot.segment_start_gain_linear[0, action])
        opening_power = 0.0
        if current > 0.0 and start > 0.0:
            opening_power = float(
                recurrence_power_w(
                    np.asarray([start]),
                    np.asarray([current]),
                    p0_w=SEGMENT_START_POWER_W,
                )[0]
            )
        # The live evaluation retains the raw required power even when the
        # ceiling rejects service, so this checks the h=0 recurrence itself.
        assert float(evaluation.link_power_w[0]) == opening_power
        assert bool(surface.opening_service_feasible[action]) == bool(
            evaluation.resolution.served[0]
        )
        assert bool(surface.opening_service_feasible[action]) == (
            opening_power <= BEAM_POWER_MAX_W and current > 0.0 and start > 0.0
        )

    after = _live_state(environment, rng)
    assert after == before


@requires_archive
def test_distinct_physical_cells_retain_distinct_projected_gain_geometry(real_t0) -> None:
    _environment, _observation, _rng, snapshot, projection = real_t0
    witnessed = False
    for uid, offsets in enumerate(projection.offsets_by_user):
        legal = snapshot.legal_mask[uid]
        norads = snapshot.candidate_norad_ids[uid]
        cells = snapshot.candidate_cell_ids[uid]
        for norad in np.unique(norads[legal]).tolist():
            rows = np.flatnonzero(legal & (norads == norad))
            if rows.size < 2 or np.unique(cells[rows]).size < 2:
                continue
            signatures = np.stack(
                [offset.projected_gain_linear[rows] for offset in offsets], axis=1
            )
            if np.unique(signatures, axis=0).shape[0] > 1:
                witnessed = True
                break
        if witnessed:
            break
    assert witnessed, "real-TLE projection collapsed every distinct cell geometry"


@requires_archive
def test_background_is_from_previous_served_association_and_link_power_not_previous_demand() -> None:
    environment, opening, rng = _environment(users=2, steps=5, seed=2026090202)
    opening_actions = _first_low_angle_actions(opening)
    assert np.all(opening_actions >= 0)
    outcome = environment.step(opening_actions, rng)
    observation = outcome.observation
    served = np.asarray(outcome.resolution.served, dtype=np.bool_)
    if not np.any(served):
        pytest.skip("real-TLE smoke anchor produced no served user")

    snapshot = snapshot_ops3_anchor(environment, observation)
    projection = project_ops3_anchor(snapshot)
    references = _first_low_angle_actions(observation)
    baseline = _surfaces(
        build_ops3_live_surfaces(snapshot, projection, references),
        snapshot.num_users,
    )

    # Construct the expected per-focal frozen background from only the
    # committed served associations and link powers.  The live observation's
    # ungated demand is deliberately poisoned below and must not affect it.
    associations = tuple(environment._previous_association)
    powers = np.asarray(environment._previous_link_power_w, dtype=np.float64)
    for focal, background in enumerate(snapshot.backgrounds):
        grouped: dict[tuple[int, int], tuple[int, float]] = {}
        for uid, association in enumerate(associations):
            if uid == focal or association is None:
                continue
            key = (int(association.norad_id), int(association.cell_id))
            count, maximum = grouped.get(key, (0, 0.0))
            grouped[key] = (count + 1, max(maximum, float(powers[uid])))
        pairs = sorted(grouped)
        np.testing.assert_array_equal(
            background.norad_ids,
            np.asarray([pair[0] for pair in pairs], dtype=np.int64),
        )
        np.testing.assert_array_equal(
            background.cell_ids,
            np.asarray([pair[1] for pair in pairs], dtype=np.int64),
        )
        np.testing.assert_array_equal(
            background.load,
            np.asarray([grouped[pair][0] for pair in pairs], dtype=np.int64),
        )
        np.testing.assert_array_equal(
            background.power_w,
            np.asarray([grouped[pair][1] for pair in pairs], dtype=np.float64),
        )

    poison: dict[tuple[int, int], int] = {}
    for uid, mask in enumerate(observation.masks):
        for action in np.flatnonzero(mask).tolist():
            poison[
                (
                    int(snapshot.candidate_norad_ids[uid, action]),
                    int(snapshot.candidate_cell_ids[uid, action]),
                )
            ] = 10_000
    environment._previous_demand = poison
    poisoned_snapshot = snapshot_ops3_anchor(environment, observation)
    poisoned_projection = project_ops3_anchor(poisoned_snapshot)
    poisoned = _surfaces(
        build_ops3_live_surfaces(poisoned_snapshot, poisoned_projection, references),
        snapshot.num_users,
    )
    assert poisoned_snapshot.anchor_sha256 == snapshot.anchor_sha256
    for first, second in zip(baseline, poisoned, strict=True):
        np.testing.assert_array_equal(first.features, second.features)
        np.testing.assert_array_equal(first.q2_values, second.q2_values)
        np.testing.assert_array_equal(first.z2_bits, second.z2_bits)


@requires_archive
def test_terminal_horizon_zero_does_not_propagate_and_emits_zero_surfaces(monkeypatch) -> None:
    environment, observation, _rng = _environment(users=2, steps=1, seed=2026090203)
    snapshot = snapshot_ops3_anchor(environment, observation)
    assert snapshot.horizon == 0

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("terminal OPS-3 projection attempted propagation")

    # H=0 must return before constructing/propagating a TLE set or asking for
    # native-clock times.  Patching these module seams makes that invariant
    # observable without changing the real environment.
    monkeypatch.setattr(live, "SatelliteSet", forbidden)
    monkeypatch.setattr(live, "step_times", forbidden)
    projection = project_ops3_anchor(snapshot)
    assert projection.horizon == 0
    assert projection.offsets_by_user == ((), ())
    assert projection.future_d2_indices == ()
    assert projection.sample_times_utc == ()
    assert projection.offset_times_utc == ()

    references = _first_low_angle_actions(observation)
    surfaces = _surfaces(
        build_ops3_live_surfaces(snapshot, projection, references),
        snapshot.num_users,
    )
    for surface in surfaces:
        assert np.all(surface.q2_values == 0.0)
        assert np.all(surface.z2_bits == 0.0)
        assert np.all(surface.features == 0.0)
        assert np.all(surface.required_power_w == 0.0)
        assert np.all(surface.persistence == 0.0)
        assert np.all(surface.rate_bps == 0.0)
        assert np.all(surface.marginal_power_w == 0.0)
        assert np.all(surface.sinr_linear == 0.0)


@requires_archive
def test_live_adapter_rejects_non_native_d2_clock_even_when_product_closes() -> None:
    driver = ScenarioDriver(
        TleArchive(_ARCHIVE),
        ScenarioConfig(
            steps_per_episode=4,
            mobility=MobilityConfig(num_users=2),
            d2=D2Config(time_step_s=0.32),
            d2_measurement_step_s=0.32,
            d2_substeps_per_decision=94,
        ),
    )
    environment = StepEnvironment(
        driver,
        physics=PhysicsConfig(fading_enabled=False, segment_warm_start="none"),
    )
    with pytest.raises(OPS3LiveError, match="canonical D2 measurement interval"):
        live._assert_canonical_physics(environment)


@pytest.mark.parametrize("users", [2, 3, 4])
@requires_archive
def test_surface_population_stays_small_and_each_current_legal_row_is_finite(users: int) -> None:
    environment, observation, _rng = _environment(
        users=users, steps=4, seed=2026090210 + users
    )
    snapshot = snapshot_ops3_anchor(environment, observation)
    projection = project_ops3_anchor(snapshot)
    references = _first_low_angle_actions(observation)
    surfaces = _surfaces(
        build_ops3_live_surfaces(snapshot, projection, references), users
    )
    assert len(surfaces) == users
    for uid, surface in enumerate(surfaces):
        legal = observation.masks[uid]
        assert np.all(np.isfinite(surface.q2_values[legal]))
        assert np.all(surface.q2_values[~legal] == 0.0)


__all__ = ["OPS3LiveError"]
