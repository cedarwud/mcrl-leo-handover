"""W-166 -- V0.16 reference-origin C3 state boundary."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.interference import RadiatingBeams
from mcrl.env.step import StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v015_c3_reference_state import (
    V015_C3_REFERENCE_BEAM_START,
    V015_C3_REFERENCE_GLOBAL_START,
    V015_C3_REFERENCE_POWER_GAP_START,
    V015_C3_REFERENCE_SATELLITE_START,
    V015_C3_REFERENCE_STATE_DIM,
    encode_ee_axis_v015_c3_reference_state,
)
from mcrl.runtime.ee_axis_v016_c3_origin_state import (
    EEAxisV016C3OriginStateError,
    V016_C3_GLOBAL_FEATURES,
    V016_C3_GLOBAL_START,
    V016_C3_LOCAL_FEATURES,
    V016_C3_ORIGIN_BEAM_START,
    V016_C3_REFERENCE_BEAM_GLOBAL_START,
    V016_C3_REFERENCE_POWER_GAP_GLOBAL_START,
    V016_C3_REFERENCE_SATELLITE_GLOBAL_START,
    V016_C3_STATE_DIM,
    encode_ee_axis_v016_c3_origin_state,
)


def _table(keys: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in keys.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _fixture(
    tables: tuple[SlotTable, ...] | None = None,
) -> tuple[StepEnvironment, StepObservation]:
    tables = tables or (
        _table({0: (101, 1), 1: (202, 2), 2: (101, 2)}),
        # Duplicate physical slots must still denote one physical reference
        # identity, while both candidate slots may match the origin block.
        _table({0: (101, 1), 1: (101, 1), 2: (303, 3), 3: (202, 2)}),
        _table({0: (404, 4), 1: (101, 2), 2: (505, 5)}),
    )
    candidates = SimpleNamespace(slot_tables=tables)
    masks = np.stack([table.mask for table in tables])
    observation = StepObservation(
        step_index=4,
        candidates=candidates,
        user_states=(object(),) * len(tables),
        state_matrix=np.zeros((len(tables), EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((len(tables), NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = len(tables)
    environment._candidates = candidates
    environment._previous_association = [None] * len(tables)
    environment._previous_served_rate_bps = np.zeros(len(tables), dtype=np.float64)
    environment._previous_link_power_w = np.zeros(len(tables), dtype=np.float64)
    environment._segments = [None] * len(tables)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.empty(0, dtype=np.int64),
        cell_ids=np.empty(0, dtype=np.int64),
        satellite_ecef_km=np.empty((0, 3), dtype=np.float64),
        cell_centre_ecef_km=np.empty((0, 3), dtype=np.float64),
        colors=np.empty(0, dtype=np.int64),
        power_w=np.empty(0, dtype=np.float64),
    )
    environment.physics = SimpleNamespace(beam_power_max_w=2.2)
    environment.driver = SimpleNamespace(config=SimpleNamespace(steps_per_episode=10))
    return environment, observation


def _inputs(
    *,
    references: np.ndarray | None = None,
    opening: np.ndarray | None = None,
    powers: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    references = (
        np.asarray([0, 0, 1], dtype=np.int64)
        if references is None
        else references
    )
    if opening is None:
        opening = np.zeros((len(references), NUM_ACTIONS), dtype=np.bool_)
        opening[np.arange(len(references)), references] = True
    powers = (
        np.zeros((len(references), NUM_ACTIONS), dtype=np.float64)
        if powers is None
        else powers
    )
    powers[0, 0] = 0.5
    powers[0, 1] = 0.9
    powers[0, 2] = 0.8
    powers[1, 0] = 0.3
    powers[1, 1] = 0.4
    powers[1, 3] = 0.7
    if len(references) > 2:
        powers[2, 1] = 0.9
    return references, opening, powers


def _encode(
    environment: StepEnvironment,
    observation: StepObservation,
    references: object,
    opening: object,
    powers: object,
):
    return encode_ee_axis_v016_c3_origin_state(
        environment,
        observation,
        reference_actions=references,
        current_required_power_w=powers,
        opening_service_feasible=opening,
        interval_s=2.0,
        kappa_bits=100.0,
        pmax_w=1.0,
    )


def test_layout_is_14_action_blocks_plus_10_globals() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    encoded = _encode(environment, observation, references, opening, powers)

    assert V016_C3_LOCAL_FEATURES == 14
    assert V016_C3_GLOBAL_FEATURES == 10
    assert V016_C3_STATE_DIM == 14 * NUM_ACTIONS + 10 == 402
    assert encoded.state_matrix.shape == (3, V016_C3_STATE_DIM)
    assert encoded.action_masks.shape == (3, NUM_ACTIONS)
    assert V016_C3_ORIGIN_BEAM_START == 13 * NUM_ACTIONS == 364
    assert V016_C3_GLOBAL_START == 14 * NUM_ACTIONS == 392
    assert encoded.verify() == encoded.state_sha256


def test_v015_371_values_are_preserved_exactly_around_new_origin_block() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    encoded = _encode(environment, observation, references, opening, powers)
    base = encode_ee_axis_v015_c3_reference_state(
        environment,
        observation,
        reference_actions=references,
        current_required_power_w=powers,
        opening_service_feasible=opening,
        interval_s=2.0,
        kappa_bits=100.0,
        pmax_w=1.0,
    )

    assert V015_C3_REFERENCE_STATE_DIM == 371
    np.testing.assert_array_equal(
        encoded.state_matrix[:, :V015_C3_REFERENCE_GLOBAL_START],
        base.state_matrix[:, :V015_C3_REFERENCE_GLOBAL_START],
    )
    np.testing.assert_array_equal(
        encoded.state_matrix[:, V016_C3_GLOBAL_START:V016_C3_GLOBAL_START + 7],
        base.state_matrix[:, V015_C3_REFERENCE_GLOBAL_START:],
    )
    np.testing.assert_array_equal(encoded.action_masks, base.action_masks)


def test_origin_block_uses_physical_identity_and_matches_duplicate_slots() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    encoded = _encode(environment, observation, references, opening, powers)
    origin = encoded.state_matrix[:, V016_C3_ORIGIN_BEAM_START:V016_C3_GLOBAL_START]

    # User 1's reference is action 0=(101,1); action 1 is the same physical
    # beam, so both slots are marked even though their flat indices differ.
    assert origin[1, 0] == 1.0
    assert origin[1, 1] == 1.0
    assert origin[1, 2] == 0.0
    # User 0's reference is action 0=(101,1); its action 2=(101,2) is a
    # different physical beam even though the satellite is the same.
    assert origin[0, 0] == 1.0
    assert origin[0, 2] == 0.0
    assert np.all(origin[~observation.masks] == 0.0)


def test_reference_global_summary_is_extracted_at_focal_reference_action() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    encoded = _encode(environment, observation, references, opening, powers)
    base = encode_ee_axis_v015_c3_reference_state(
        environment,
        observation,
        reference_actions=references,
        current_required_power_w=powers,
        opening_service_feasible=opening,
        interval_s=2.0,
        kappa_bits=100.0,
        pmax_w=1.0,
    )

    new_globals = encoded.state_matrix[:, V016_C3_GLOBAL_START:]
    for user, reference in enumerate(references.tolist()):
        expected = (
            base.state_matrix[user, V015_C3_REFERENCE_BEAM_START + reference],
            base.state_matrix[user, V015_C3_REFERENCE_SATELLITE_START + reference],
            base.state_matrix[user, V015_C3_REFERENCE_POWER_GAP_START + reference],
        )
        assert new_globals[user, V016_C3_REFERENCE_BEAM_GLOBAL_START - V016_C3_GLOBAL_START] == pytest.approx(expected[0])
        assert new_globals[user, V016_C3_REFERENCE_SATELLITE_GLOBAL_START - V016_C3_GLOBAL_START] == pytest.approx(expected[1])
        assert new_globals[user, V016_C3_REFERENCE_POWER_GAP_GLOBAL_START - V016_C3_GLOBAL_START] == pytest.approx(expected[2])


def test_empty_reference_row_has_zero_origin_and_reference_globals() -> None:
    tables = (
        _table({0: (101, 1)}),
        _table({0: (202, 2)}),
        _table({}),
    )
    environment, observation = _fixture(tables)
    references, opening, powers = _inputs(
        references=np.asarray([0, 0, -1], dtype=np.int64),
        opening=np.zeros((3, NUM_ACTIONS), dtype=np.bool_),
    )
    opening[0, 0] = True
    opening[1, 0] = True
    encoded = _encode(environment, observation, references, opening, powers)

    assert np.all(encoded.state_matrix[2, V016_C3_ORIGIN_BEAM_START:V016_C3_GLOBAL_START] == 0.0)
    assert np.all(encoded.state_matrix[2, V016_C3_GLOBAL_START + 7:] == 0.0)


@pytest.mark.parametrize(
    ("references", "message"),
    (
        (np.asarray([-1, 0, 1], dtype=np.int64), "all-empty"),
        (np.asarray([99, 0, 1], dtype=np.int64), "not legal"),
    ),
)
def test_illegal_reference_actions_fail_loudly(
    references: np.ndarray, message: str
) -> None:
    environment, observation = _fixture()
    _references, opening, powers = _inputs()
    with pytest.raises(EEAxisV016C3OriginStateError, match=message):
        _encode(environment, observation, references, opening, powers)


def test_encoder_does_not_call_evaluator_and_returns_immutable_arrays() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("V0.16 state must not evaluate an outcome")

    environment.evaluate_actions = forbidden
    environment.q_values = forbidden
    environment.rng = forbidden
    first = _encode(environment, observation, references, opening, powers)
    second = _encode(environment, observation, references, opening, powers)
    assert first.state_sha256 == second.state_sha256
    assert not first.state_matrix.flags.writeable
    assert not first.action_masks.flags.writeable
    with pytest.raises(ValueError):
        first.state_matrix[0, V016_C3_ORIGIN_BEAM_START] = 0.0


def test_origin_semantics_follow_physical_permutation_not_flat_action_index() -> None:
    tables_left = (
        _table({0: (101, 1), 1: (202, 2), 2: (101, 2)}),
        _table({0: (101, 1), 1: (101, 1)}),
        _table({0: (404, 4), 1: (101, 2)}),
    )
    tables_right = (
        _table({0: (202, 2), 1: (101, 2), 2: (101, 1)}),
        tables_left[1],
        tables_left[2],
    )
    left_env, left_obs = _fixture(tables_left)
    right_env, right_obs = _fixture(tables_right)
    left_ref, left_opening, left_power = _inputs(
        references=np.asarray([2, 0, 1], dtype=np.int64)
    )
    right_ref, right_opening, right_power = _inputs(
        references=np.asarray([1, 0, 1], dtype=np.int64)
    )
    left = _encode(left_env, left_obs, left_ref, left_opening, left_power)
    right = _encode(right_env, right_obs, right_ref, right_opening, right_power)
    left_origin = left.state_matrix[0, V016_C3_ORIGIN_BEAM_START:V016_C3_GLOBAL_START]
    right_origin = right.state_matrix[0, V016_C3_ORIGIN_BEAM_START:V016_C3_GLOBAL_START]
    # The reference is (101,2) in both fixtures; only its flat slot changed.
    assert left_origin[2] == right_origin[1] == 1.0
    assert left_origin[0] == right_origin[2] == 0.0


def test_verify_rejects_schema_digest_or_array_digest_drift() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    encoded = _encode(environment, observation, references, opening, powers)

    with pytest.raises(EEAxisV016C3OriginStateError, match="schema"):
        replace(encoded, schema="wrong").verify()
    with pytest.raises(EEAxisV016C3OriginStateError, match="schema digest"):
        replace(encoded, schema_sha256="0" * 64).verify()
    damaged = np.array(encoded.state_matrix, copy=True)
    damaged[0, V016_C3_ORIGIN_BEAM_START] = 0.0
    damaged.setflags(write=False)
    with pytest.raises(EEAxisV016C3OriginStateError, match="digest"):
        replace(encoded, state_matrix=damaged).verify()
