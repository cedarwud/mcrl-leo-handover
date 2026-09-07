"""W-146 -- deployable V0.14 ZR-Q3 state boundary."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable
from mcrl.env.interference import RadiatingBeams
from mcrl.env.step import Segment, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v014_q3_state import (
    EEAxisV014Q3StateError,
    V014_Q3_GLOBAL_FEATURES,
    V014_Q3_LOCAL_FEATURES,
    V014_Q3_STATE_DIM,
    encode_ee_axis_v014_q3_state,
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
    *,
    previous: list[Association | None] | None = None,
    rates: list[float] | None = None,
    powers: list[float] | None = None,
) -> tuple[StepEnvironment, StepObservation]:
    tables = (
        _table({0: (101, 1), 1: (202, 2)}),
        _table({0: (101, 1), 1: (303, 3), 2: (101, 2)}),
        _table({0: (101, 2), 1: (404, 4)}),
    )
    candidates = SimpleNamespace(slot_tables=tables)
    masks = np.stack([table.mask for table in tables])
    observation = StepObservation(
        step_index=0,
        candidates=candidates,
        user_states=(object(), object(), object()),
        state_matrix=np.zeros((3, EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = 3
    environment._candidates = candidates
    environment._previous_association = previous or [None, None, None]
    environment._previous_served_rate_bps = np.asarray(
        rates or [0.0, 0.0, 0.0], dtype=np.float64
    )
    environment._previous_link_power_w = np.asarray(
        powers or [0.0, 0.0, 0.0], dtype=np.float64
    )
    environment._segments = [
        None
        if association is None
        else Segment(association.norad_id, association.cell_id, 1.0, age_steps=0)
        for association in environment._previous_association
    ]
    by_key: dict[tuple[int, int], float] = {}
    for association, power in zip(
        environment._previous_association,
        environment._previous_link_power_w,
        strict=True,
    ):
        if association is None:
            continue
        key = (association.norad_id, association.cell_id)
        by_key[key] = max(by_key.get(key, 0.0), float(power))
    ordered = sorted(by_key)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.asarray([key[0] for key in ordered], dtype=np.int64),
        cell_ids=np.asarray([key[1] for key in ordered], dtype=np.int64),
        satellite_ecef_km=np.zeros((len(ordered), 3), dtype=np.float64),
        cell_centre_ecef_km=np.zeros((len(ordered), 3), dtype=np.float64),
        colors=np.zeros(len(ordered), dtype=np.int64),
        power_w=np.asarray([by_key[key] for key in ordered], dtype=np.float64),
    )
    environment.physics = SimpleNamespace(beam_power_max_w=2.2)
    environment.driver = SimpleNamespace(config=SimpleNamespace(steps_per_episode=10))
    return environment, observation


def _new_blocks(state: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    old_local = 8 * NUM_ACTIONS
    continuation = state[:, old_local : old_local + NUM_ACTIONS]
    load = state[:, old_local + NUM_ACTIONS : old_local + 2 * NUM_ACTIONS]
    globals_ = state[:, V014_Q3_LOCAL_FEATURES * NUM_ACTIONS :]
    return continuation, load, globals_


def test_layout_is_ten_action_blocks_plus_seven_globals_and_start_is_zero():
    environment, observation = _fixture()
    encoded = encode_ee_axis_v014_q3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    continuation, load, globals_ = _new_blocks(encoded.state_matrix)

    assert V014_Q3_STATE_DIM == 287
    assert V014_Q3_STATE_DIM == V014_Q3_LOCAL_FEATURES * 28 + V014_Q3_GLOBAL_FEATURES
    assert encoded.state_matrix.shape == (3, 287)
    assert np.array_equal(continuation, np.zeros_like(continuation))
    assert np.array_equal(load, np.zeros_like(load))
    assert np.array_equal(globals_[:, -3:], np.zeros((3, 3), dtype=np.float32))
    assert encoded.verify() == encoded.state_sha256


def test_added_features_match_committed_incumbent_load_rate_and_power_semantics():
    environment, observation = _fixture(
        previous=[Association(101, 1), Association(101, 1), Association(101, 2)],
        rates=[100.0, 200.0, 300.0],
        powers=[1.0, 1.5, 0.7],
    )
    encoded = encode_ee_axis_v014_q3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    continuation, load, globals_ = _new_blocks(encoded.state_matrix)

    assert continuation[0, 0] == 1.0
    assert continuation[0, 1] == 0.0
    assert continuation[1, 0] == 1.0
    assert continuation[1, 2] == 0.0
    assert continuation[2, 0] == 1.0
    assert load[0, 0] == pytest.approx(1.0 / 3.0)
    assert load[1, 0] == pytest.approx(1.0 / 3.0)
    assert load[1, 2] == pytest.approx(1.0 / 3.0)
    assert load[2, 0] == 0.0

    # Last three globals: incumbent non-focal rate burden, load, power leader.
    assert globals_[0, -3] == pytest.approx(4.0)
    assert globals_[0, -2] == pytest.approx(1.0 / 3.0)
    assert globals_[0, -1] == 0.0
    assert globals_[1, -3] == pytest.approx(2.0)
    assert globals_[1, -2] == pytest.approx(1.0 / 3.0)
    assert globals_[1, -1] == 1.0
    assert globals_[2, -3] == 0.0
    assert globals_[2, -2] == 0.0
    assert globals_[2, -1] == 1.0


def test_encoder_has_no_oracle_or_evaluator_input_and_keeps_outputs_immutable():
    environment, observation = _fixture(
        previous=[Association(101, 1), Association(101, 1), Association(101, 2)],
        rates=[100.0, 200.0, 300.0],
        powers=[1.0, 1.5, 0.7],
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("the deployable state called an outcome evaluator")

    environment.evaluate_actions = forbidden
    first = encode_ee_axis_v014_q3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    second = encode_ee_axis_v014_q3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    assert first.state_sha256 == second.state_sha256
    assert np.array_equal(first.state_matrix, second.state_matrix)
    assert not first.state_matrix.flags.writeable
    assert not first.action_masks.flags.writeable
    with pytest.raises(ValueError):
        first.state_matrix[0, 0] = 1.0


def test_illegal_added_action_features_are_zero():
    environment, observation = _fixture(
        previous=[Association(101, 1), Association(101, 1), Association(101, 2)],
        rates=[100.0, 200.0, 300.0],
        powers=[1.0, 1.5, 0.7],
    )
    encoded = encode_ee_axis_v014_q3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    continuation, load, _globals = _new_blocks(encoded.state_matrix)
    assert np.all(continuation[~observation.masks] == 0.0)
    assert np.all(load[~observation.masks] == 0.0)


def test_committed_power_without_a_radiating_beam_fails_closed():
    environment, observation = _fixture(
        previous=[Association(101, 1), None, None],
        rates=[100.0, 0.0, 0.0],
        powers=[1.0, 0.0, 0.0],
    )
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.empty(0, dtype=np.int64),
        cell_ids=np.empty(0, dtype=np.int64),
        satellite_ecef_km=np.empty((0, 3), dtype=np.float64),
        cell_centre_ecef_km=np.empty((0, 3), dtype=np.float64),
        colors=np.empty(0, dtype=np.int64),
        power_w=np.empty(0, dtype=np.float64),
    )
    with pytest.raises(EEAxisV014Q3StateError, match="radiating beam"):
        encode_ee_axis_v014_q3_state(
            environment, observation, interval_s=2.0, kappa_bits=100.0
        )
