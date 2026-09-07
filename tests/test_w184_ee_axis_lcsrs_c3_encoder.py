"""W-184 -- V0.23 LC-SRS physical predecision descriptor encoder.

The fixtures use only captured geometry and native tables.  In particular,
``candidate_sinr`` is a trap property: touching it makes the test fail.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable
from mcrl.algorithms.ee_axis_lcsrs_three_route import DetachedQ12Snapshot
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.observation_provenance import (
    build_native_observation_provenance,
    numpy_rng_state_sha256,
)
from mcrl.env.step import Segment, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_lcsrs_c3_encoder import (
    LCSRSC3EncoderError,
    capture_lcsrs_c3_predecision,
    encode_lcsrs_c3_view,
)
from mcrl.runtime.ee_axis_state import encode_ee_axis_state


@dataclass
class _Fixture:
    environment: StepEnvironment
    observation: StepObservation
    q12: DetachedQ12Snapshot
    opening: np.ndarray


def _detached_q12(
    values: np.ndarray,
    *,
    source_state_digest: str,
    native_observation_event_digest: str,
) -> DetachedQ12Snapshot:
    q1 = np.asarray(values, dtype=np.float32)
    q2 = np.zeros_like(q1)
    model_digest = hashlib.sha256(q1.tobytes(order="C") + b"model").hexdigest()
    return DetachedQ12Snapshot(
        q1=q1,
        q2=q2,
        source_state_digest=source_state_digest,
        native_observation_event_digest=native_observation_event_digest,
        model_digest=model_digest,
    )


def _table(items: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in items.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _fixture(
    *,
    occupancy_three: bool = False,
    trap_sinr: bool = False,
    unsupported_pair: bool = False,
) -> _Fixture:
    # Users 0/1 share (10,0), user 2 occupies (30,2), and user 3 occupies
    # (40,3).  Both members can move to the non-member (30,2) destination.
    tables = [
        _table(
            {
                0: (10, 0),
                1: ((70, 6) if unsupported_pair else (30, 2)),
                2: ((80, 7) if unsupported_pair else (50, 4)),
            }
        ),
        _table({0: (10, 0), 1: (30, 2), 2: (50, 4)}),
        _table({0: (30, 2), 1: (10, 0), 2: (70, 6)}),
        _table(
            {
                0: ((10 if occupancy_three else 50), (0 if occupancy_three else 4)),
                1: (30, 2),
                2: (80, 7),
            }
        ),
    ]
    users = len(tables)
    legal = np.stack([table.mask for table in tables])
    opening = legal.copy()
    q12 = np.full((users, NUM_ACTIONS), -100.0, dtype=np.float64)
    for uid in range(users):
        q12[uid, 0] = 10.0
        q12[uid, 1] = 4.0
        q12[uid, 2] = 4.0

    class _Candidates(SimpleNamespace):
        @property
        def candidate_sinr(self):  # pragma: no cover - must never be touched
            if trap_sinr:
                raise AssertionError("LC-SRS encoder read forbidden candidate_sinr")
            return np.full((users, NUM_ACTIONS), 7.0)

    satellites = np.asarray(
        [
            [7000.0, 0.0, 0.0],
            [0.0, 7000.0, 0.0],
            [-7000.0, 0.0, 0.0],
            [0.0, -7000.0, 0.0],
        ],
        dtype=np.float64,
    )
    all_norads = (10, 30, 40, 50, 60, 70, 80)
    position_map = {
        int(norad): np.asarray(
            satellites[index % len(satellites)]
            + np.asarray([0.0, 0.0, 15.0 * index]),
            dtype=np.float64,
        )
        for index, norad in enumerate(all_norads)
    }
    window_norads = (10, 30, 50, 60)
    window_positions = np.asarray(
        [position_map[norad] for norad in window_norads],
        dtype=np.float64,
    )
    candidates = _Candidates(
        slot_tables=tuple(tables),
        off_axis_deg=np.zeros((users, 4, 7), dtype=np.float64),
        slant_range_km=np.full((users, 4), 600.0, dtype=np.float64),
        elevation_deg=np.full((users, 4), 60.0, dtype=np.float64),
        window_norad_ids=np.asarray([window_norads] * users, dtype=np.int64),
        window_satellite_ecef_km=np.asarray(
            [window_positions] * users,
            dtype=np.float64,
        ),
        cell_colors=np.asarray([0, 0, 0, 1, 1, 2, 2, 1], dtype=np.int64),
        cell_centres_ecef_km=np.asarray(
            [
                [6371.0, 0.0, 0.0],
                [6368.0, 100.0, 0.0],
                [6368.0, -100.0, 0.0],
                [6368.0, 0.0, 100.0],
                [6368.0, 0.0, -100.0],
                [6365.0, 100.0, 100.0],
                [6365.0, -100.0, -100.0],
                [6365.0, 100.0, -100.0],
            ],
            dtype=np.float64,
        ),
    )
    observation_sinr = np.full((users, NUM_ACTIONS), 9.0, dtype=np.float64)
    field = KeyedFadingField.from_components("w184", 7, 4)
    receipt_rng = np.random.default_rng(184)
    provenance = build_native_observation_provenance(
        step_index=4,
        candidate_sinr=observation_sinr,
        rng=receipt_rng,
        rng_pre_state_sha256=numpy_rng_state_sha256(receipt_rng),
        fading_field=field,
        sinr_provenance="theta-current-interference-previous-step",
    )
    observation = StepObservation(
        step_index=4,
        candidates=candidates,
        user_states=(object(),) * users,
        state_matrix=np.zeros((users, 112), dtype=np.float32),
        masks=legal,
        candidate_sinr=observation_sinr,
        observation_provenance=provenance,
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = users
    environment._step_index = 4
    environment._candidates = candidates
    environment._fading_field = field
    environment._previous_association = [None] * users
    environment._previous_radiating = SimpleNamespace(
        norad_ids=np.zeros(0, dtype=np.int64),
        cell_ids=np.zeros(0, dtype=np.int64),
        power_w=np.zeros(0, dtype=np.float64),
    )
    environment._previous_link_power_w = np.zeros(users, dtype=np.float64)
    environment._segments = [None] * users
    environment._previous_demand = {}
    environment.physics = SimpleNamespace(
        beam_power_max_w=2.0,
        segment_start_power_w=1.0,
        beam_bandwidth_hz=1.0e6,
        noise_power_w=1.0e-9,
    )
    environment.driver = SimpleNamespace(
        grid=SimpleNamespace(
            colors=candidates.cell_colors,
            centers_ecef_km=candidates.cell_centres_ecef_km,
        ),
        config=SimpleNamespace(steps_per_episode=10),
        user_ecef_km=lambda: np.asarray(
            [
                [6371.0, 0.0, 0.0],
                [6368.0, 100.0, 0.0],
                [6368.0, -100.0, 0.0],
                [6368.0, 0.0, 100.0],
            ],
            dtype=np.float64,
        ),
        satellite_ecef_at=lambda _offset: {
            norad: np.array(position, copy=True)
            for norad, position in position_map.items()
        },
    )
    source_state = encode_ee_axis_state(environment, observation)
    return _Fixture(
        environment,
        observation,
        _detached_q12(
            q12,
            source_state_digest=source_state.state_sha256,
            native_observation_event_digest=provenance.content_digest,
        ),
        opening,
    )


def _encode(fixture: _Fixture):
    references = np.argmax(
        np.where(fixture.observation.masks, fixture.q12.q12, -np.inf),
        axis=1,
    ).astype(np.int64)
    return encode_lcsrs_c3_view(
        fixture.environment,
        fixture.observation,
        world_id=7,
        anchor_id="fixture-t4",
        detached_q12=fixture.q12,
        reference_actions=references,
        opening_feasibility_surface=fixture.opening,
    )


def _capture(fixture: _Fixture):
    references = np.argmax(
        np.where(fixture.observation.masks, fixture.q12.q12, -np.inf),
        axis=1,
    ).astype(np.int64)
    return capture_lcsrs_c3_predecision(
        fixture.environment,
        fixture.observation,
        world_id=7,
        anchor_id="fixture-t4",
        detached_q12=fixture.q12,
        reference_actions=references,
        opening_feasibility_surface=fixture.opening,
    )


def test_encoder_emits_exact_shapes_bounded_immutable_and_digest_stable() -> None:
    fixture = _fixture(trap_sinr=True)
    first = _encode(fixture)
    second = _encode(fixture)
    assert first.action_context.shape == (4, 28, 29)
    assert first.tokens.shape == (4, 28, 5, 38)
    assert first.token_mask.shape == (4, 28, 5)
    assert first.action_mask.shape == (4, 28)
    assert first.reference_actions.tolist() == [0, 0, 0, 0]
    assert first.content_digest == second.content_digest
    np.testing.assert_array_equal(first.action_context, second.action_context)
    np.testing.assert_array_equal(first.tokens, second.tokens)
    assert np.all(np.abs(first.action_context) <= 1.0)
    assert np.all(np.abs(first.tokens) <= 1.0)
    for name in ("action_context", "tokens", "token_mask", "action_mask", "reference_actions"):
        assert not getattr(first, name).flags.writeable


def test_predecision_capture_binds_topology_before_pair_features() -> None:
    captured = _capture(_fixture())
    assert captured.verify() == captured.content_digest
    assert captured.topology.pair_count == 1
    pair = captured.topology.pairs[0]
    assert pair.member_users == (0, 1)
    assert pair.designated_actions == (1, 1)
    pair_tokens = captured.view.tokens[:, :, 4, :]
    assert pair_tokens[0, pair.designated_actions[0], 3] == 1.0
    assert pair_tokens[0, pair.designated_actions[0], 4] == 1.0
    assert pair_tokens[1, pair.designated_actions[1], 3] == 1.0
    assert pair_tokens[1, pair.designated_actions[1], 4] == 1.0


def test_physical_pair_destination_tie_and_occupancy_sentinels() -> None:
    fixture = _fixture()
    view = _encode(fixture)
    pair = view.tokens[:, :, 4, :]
    # Source occupancy is exactly two and both users have a designated move.
    assert pair[0, 1, 2:8].tolist() == [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    assert pair[1, 1, 2:8].tolist() == [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    # The designated destination is the lowest native action among equal Q12
    # values; action 1 is therefore marked, and action 2 is not.
    assert pair[0, 1, 4] == 1.0
    assert pair[0, 2, 4] == 0.0
    # User 2 has source occupancy one, so every legal pair tail is exactly the
    # no-partner sentinel.  User 3 makes the source occupancy three variant.
    assert np.array_equal(pair[2, 0], np.asarray([0.0, 1.0] + [0.0] * 36, dtype=np.float32))
    three = _encode(_fixture(occupancy_three=True))
    assert np.array_equal(three.tokens[0, 0, 4], np.asarray([0.0, 1.0] + [0.0] * 36, dtype=np.float32))

    unsupported = _encode(_fixture(unsupported_pair=True))
    expected = np.asarray([0.0, 1.0, 1.0] + [0.0] * 35, dtype=np.float32)
    assert np.array_equal(unsupported.tokens[0, 0, 4], expected)
    assert np.array_equal(unsupported.tokens[1, 0, 4], expected)


def test_relation_mask_has_focal_partner_and_physical_union() -> None:
    view = _encode(_fixture())
    # Pair members are always present.  User 2 shares the designated
    # destination, while user 3 has a different colour/beam and is absent.
    assert view.token_mask[0, 1, :4].tolist() == [True, True, True, False]
    # Unsupported/no-partner row still has focal context but never invents a
    # partner token.
    assert view.token_mask[2, 0, 2]
    # Its source (30,2) is occupied by the first pair, so those users are
    # physical victims too; the focal row itself is always retained.
    assert view.token_mask[2, 0, 0]
    assert view.token_mask[2, 0, 1]


def test_candidate_sinr_and_rng_or_live_state_do_not_change_view() -> None:
    fixture = _fixture(trap_sinr=True)
    first = _encode(fixture)
    fixture.observation.candidate_sinr[:] = -999.0
    fixture.environment._mobility_rng = np.random.default_rng(123)
    second = _encode(fixture)
    assert first.content_digest == second.content_digest


def test_native_observation_event_is_bound_to_q12_and_outer_capture() -> None:
    fixture = _fixture()
    captured = _capture(fixture)
    assert (
        captured.native_observation_provenance.content_digest
        == fixture.q12.native_observation_event_digest
    )
    assert captured.state_sha256 == fixture.q12.source_state_digest

    wrong_event = replace(
        fixture.q12,
        native_observation_event_digest="0" * 64,
        content_digest="",
    )
    with pytest.raises(LCSRSC3EncoderError, match="different native observation event"):
        encode_lcsrs_c3_view(
            fixture.environment,
            fixture.observation,
            world_id=7,
            anchor_id="fixture-t4",
            detached_q12=wrong_event,
            reference_actions=np.zeros(4, dtype=np.int64),
            opening_feasibility_surface=fixture.opening,
        )

    missing = replace(fixture.observation, observation_provenance=None)
    with pytest.raises(LCSRSC3EncoderError, match="event provenance"):
        encode_lcsrs_c3_view(
            fixture.environment,
            missing,
            world_id=7,
            anchor_id="fixture-t4",
            detached_q12=fixture.q12,
            reference_actions=np.zeros(4, dtype=np.int64),
            opening_feasibility_surface=fixture.opening,
        )


def test_temporal_context_is_candidate_independent_and_missing_is_exact() -> None:
    fixture = _fixture()
    unserved = _encode(fixture)
    for user in range(unserved.action_mask.shape[0]):
        np.testing.assert_array_equal(
            unserved.action_context[user, unserved.action_mask[user], 19:23],
            np.tile(
                np.asarray([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
                (int(np.count_nonzero(unserved.action_mask[user])), 1),
            ),
        )

    fixture = _fixture()
    fixture.environment._previous_association[0] = Association(10, 0)
    fixture.environment._segments[0] = Segment(
        norad_id=10,
        cell_id=0,
        start_transmit_gain=1.0,
        age_steps=2,
    )
    fixture.environment._previous_link_power_w[0] = 0.5
    state = encode_ee_axis_state(fixture.environment, fixture.observation)
    fixture.q12 = _detached_q12(
        fixture.q12.q12,
        source_state_digest=state.state_sha256,
        native_observation_event_digest=(
            fixture.observation.observation_provenance.content_digest
        ),
    )
    served = _encode(fixture)
    temporal = served.action_context[0, served.action_mask[0], 19:23]
    np.testing.assert_array_equal(
        temporal,
        np.tile(temporal[0], (temporal.shape[0], 1)),
    )
    assert temporal[0, 0] == pytest.approx(0.25)
    assert temporal[0, 2] == pytest.approx(0.2)
    assert temporal[0, 3] == 0.0

    fixture.environment._previous_association[0] = Association(999, 9)
    fixture.environment._segments[0] = Segment(
        norad_id=999,
        cell_id=9,
        start_transmit_gain=1.0,
        age_steps=2,
    )
    state = encode_ee_axis_state(fixture.environment, fixture.observation)
    fixture.q12 = _detached_q12(
        fixture.q12.q12,
        source_state_digest=state.state_sha256,
        native_observation_event_digest=(
            fixture.observation.observation_provenance.content_digest
        ),
    )
    missing = _encode(fixture)
    np.testing.assert_array_equal(
        missing.action_context[0, missing.action_mask[0], 19:23],
        np.tile(
            np.asarray([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
            (int(np.count_nonzero(missing.action_mask[0])), 1),
        ),
    )


@pytest.mark.parametrize(
    ("age_steps", "expected"),
    (
        (0, 0.0),
        (2, 0.2),
        (9, 0.9),
        (10, 1.0),
        (11, 1.0),
        (18, 1.0),
    ),
)
def test_warm_started_segment_age_saturates_at_episode_length(
    age_steps: int | np.integer,
    expected: float,
) -> None:
    fixture = _fixture()
    fixture.environment._previous_association[0] = Association(10, 0)
    fixture.environment._segments[0] = Segment(
        norad_id=10,
        cell_id=0,
        start_transmit_gain=1.0,
        age_steps=age_steps,
    )
    fixture.environment._previous_link_power_w[0] = 0.5
    state = encode_ee_axis_state(fixture.environment, fixture.observation)
    fixture.q12 = _detached_q12(
        fixture.q12.q12,
        source_state_digest=state.state_sha256,
        native_observation_event_digest=(
            fixture.observation.observation_provenance.content_digest
        ),
    )

    segment_before = fixture.environment._segments[0]
    first = _encode(fixture)
    second = _encode(fixture)
    temporal = first.action_context[0, first.action_mask[0], 19:23]

    np.testing.assert_array_equal(
        temporal,
        np.tile(temporal[0], (temporal.shape[0], 1)),
    )
    assert temporal[0, 2] == pytest.approx(expected)
    assert first.verify() == first.content_digest
    assert first.content_digest == second.content_digest
    np.testing.assert_array_equal(first.action_context, second.action_context)
    assert fixture.environment._segments[0] is segment_before
    assert fixture.environment._segments[0].age_steps == age_steps


def test_old_incumbent_missing_from_candidate_surface_keeps_exact_sentinel() -> None:
    fixture = _fixture()
    fixture.environment._previous_association[0] = Association(999, 9)
    fixture.environment._segments[0] = Segment(
        norad_id=999,
        cell_id=9,
        start_transmit_gain=1.0,
        age_steps=18,
    )
    fixture.environment._previous_link_power_w[0] = 0.5
    state = encode_ee_axis_state(fixture.environment, fixture.observation)
    fixture.q12 = _detached_q12(
        fixture.q12.q12,
        source_state_digest=state.state_sha256,
        native_observation_event_digest=(
            fixture.observation.observation_provenance.content_digest
        ),
    )
    view = _encode(fixture)
    np.testing.assert_array_equal(
        view.action_context[0, view.action_mask[0], 19:23],
        np.tile(
            np.asarray([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
            (int(np.count_nonzero(view.action_mask[0])), 1),
        ),
    )


def test_stale_slot_index_geometry_is_rejected_against_physical_driver() -> None:
    fixture = _fixture()
    fixture.observation.candidates.window_satellite_ecef_km[0, 0, 2] += 1.0
    with pytest.raises(LCSRSC3EncoderError, match="inconsistent captured positions"):
        _encode(fixture)


def test_same_occupancy_but_changed_victim_geometry_changes_relational_physics() -> None:
    fixture = _fixture()
    first = _encode(fixture)

    moved_users = np.array(fixture.environment.driver.user_ecef_km(), copy=True)
    moved_users[2, 2] += 1.0
    fixture.environment.driver.user_ecef_km = lambda: np.array(
        moved_users, copy=True
    )
    state = encode_ee_axis_state(fixture.environment, fixture.observation)
    fixture.q12 = _detached_q12(
        fixture.q12.q12,
        source_state_digest=state.state_sha256,
        native_observation_event_digest=(
            fixture.observation.observation_provenance.content_digest
        ),
    )
    second = _encode(fixture)

    np.testing.assert_array_equal(first.action_mask, second.action_mask)
    np.testing.assert_array_equal(first.reference_actions, second.reference_actions)
    np.testing.assert_array_equal(first.token_mask, second.token_mask)
    # User 2 remains the same physical victim of user 0's designated move, but
    # its deterministic endpoint couplings must reflect the changed geometry.
    assert first.token_mask[0, 1, 2]
    assert not np.array_equal(
        first.tokens[0, 1, 2, 33:37],
        second.tokens[0, 1, 2, 33:37],
    )


def test_slot_permutation_preserves_physical_features_and_lowest_native_tie() -> None:
    fixture = _fixture()
    first = _encode(fixture)
    permutation = np.asarray([2, 0, 1] + list(range(3, NUM_ACTIONS)), dtype=np.int64)
    inverse = np.argsort(permutation)
    perm_tables = []
    for table in fixture.observation.candidates.slot_tables:
        perm_tables.append(SlotTable(table.norad_ids[permutation], table.cell_ids[permutation], table.mask[permutation]))
    fixture.observation.candidates.slot_tables = tuple(perm_tables)
    fixture.observation = StepObservation(
        step_index=fixture.observation.step_index,
        candidates=fixture.observation.candidates,
        user_states=fixture.observation.user_states,
        state_matrix=fixture.observation.state_matrix,
        masks=fixture.observation.masks[:, permutation],
        candidate_sinr=fixture.observation.candidate_sinr,
        observation_provenance=fixture.observation.observation_provenance,
    )
    fixture.opening = fixture.opening[:, permutation]
    fixture.environment._candidates = fixture.observation.candidates
    source_state = encode_ee_axis_state(fixture.environment, fixture.observation)
    fixture.q12 = _detached_q12(
        fixture.q12.q12[:, permutation],
        source_state_digest=source_state.state_sha256,
        native_observation_event_digest=(
            fixture.observation.observation_provenance.content_digest
        ),
    )
    second = _encode(fixture)
    np.testing.assert_array_equal(second.reference_actions, inverse[first.reference_actions])
    physical_features = [index for index in range(29) if index != 24]
    np.testing.assert_allclose(
        second.action_context[:, :, physical_features],
        first.action_context[:, permutation][:, :, physical_features],
        rtol=0.0,
        atol=0.0,
    )
    # Feature 24 is the declared native-index tie-broken Q12 rank, so it is
    # expected to change when equal-score native slots are permuted.
    assert not np.array_equal(
        second.action_context[:, :, 24],
        first.action_context[:, permutation, 24],
    )
    assert second.content_digest != first.content_digest


def test_rejects_opening_mask_drift_and_illegal_reference() -> None:
    fixture = _fixture()
    bad_opening = fixture.opening.copy()
    bad_opening[0, 27] = True
    with pytest.raises(LCSRSC3EncoderError, match="subset"):
        encode_lcsrs_c3_view(
            fixture.environment,
            fixture.observation,
            world_id=7,
            anchor_id="fixture-t4",
            detached_q12=fixture.q12,
            reference_actions=np.zeros(4, dtype=np.int64),
            opening_feasibility_surface=bad_opening,
        )
    bad_q12 = fixture.q12.q12.copy()
    bad_q12[0, 1] = 20.0
    # This is still a legal detached reference only if reference actions are
    # omitted; an explicitly stale reference must fail closed.
    with pytest.raises(LCSRSC3EncoderError, match="argmax"):
        encode_lcsrs_c3_view(
            fixture.environment,
            fixture.observation,
            world_id=7,
            anchor_id="fixture-t4",
            detached_q12=_detached_q12(
                bad_q12,
                source_state_digest=fixture.q12.source_state_digest,
                native_observation_event_digest=(
                    fixture.q12.native_observation_event_digest
                ),
            ),
            reference_actions=np.zeros(4, dtype=np.int64),
            opening_feasibility_surface=fixture.opening,
        )


def test_rejects_raw_q12_and_a_forged_opening_subset() -> None:
    fixture = _fixture()
    references = np.zeros(4, dtype=np.int64)
    with pytest.raises(LCSRSC3EncoderError, match="DetachedQ12Snapshot"):
        encode_lcsrs_c3_view(
            fixture.environment,
            fixture.observation,
            world_id=7,
            anchor_id="fixture-t4",
            detached_q12=fixture.q12.q12,
            reference_actions=references,
            opening_feasibility_surface=fixture.opening,
        )

    forged = fixture.opening.copy()
    forged[0, 1] = False
    with pytest.raises(LCSRSC3EncoderError, match="pure predecision predicate"):
        encode_lcsrs_c3_view(
            fixture.environment,
            fixture.observation,
            world_id=7,
            anchor_id="fixture-t4",
            detached_q12=fixture.q12,
            reference_actions=references,
            opening_feasibility_surface=forged,
        )
