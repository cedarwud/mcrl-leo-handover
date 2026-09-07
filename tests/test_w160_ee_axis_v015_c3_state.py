"""W-160 -- causal V0.15 current-global C3 state boundary."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.interference import RadiatingBeams
from mcrl.env.step import StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v014_q3_state import V014_Q3_STATE_DIM
from mcrl.runtime.ee_axis_v015_c3_state import (
    EEAxisV015C3StateError,
    V015_C3_ACTION_BLOCKS,
    V015_C3_CURRENT_BEAM_START,
    V015_C3_CURRENT_SATELLITE_START,
    V015_C3_STATE_DIM,
    encode_ee_axis_v015_c3_state,
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


def _fixture() -> tuple[StepEnvironment, StepObservation]:
    tables = (
        _table({0: (101, 1), 1: (202, 2), 2: (101, 2)}),
        # Action 0 and action 1 intentionally repeat one physical key.  A
        # peer must be counted once, not once per slot occurrence.
        _table({0: (101, 1), 1: (101, 1), 2: (303, 3), 3: (202, 2)}),
        _table({0: (101, 1), 1: (101, 2), 2: (404, 4)}),
    )
    candidates = SimpleNamespace(slot_tables=tables)
    masks = np.stack([table.mask for table in tables])
    observation = StepObservation(
        step_index=4,
        candidates=candidates,
        user_states=(object(), object(), object()),
        state_matrix=np.zeros((3, EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((3, NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = 3
    environment._candidates = candidates
    environment._previous_association = [None, None, None]
    environment._previous_served_rate_bps = np.zeros(3, dtype=np.float64)
    environment._previous_link_power_w = np.zeros(3, dtype=np.float64)
    environment._segments = [None, None, None]
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


def _blocks(encoded):
    return (
        encoded.state_matrix[
            :, V015_C3_CURRENT_BEAM_START : V015_C3_CURRENT_BEAM_START + NUM_ACTIONS
        ],
        encoded.state_matrix[
            :,
            V015_C3_CURRENT_SATELLITE_START : V015_C3_CURRENT_SATELLITE_START
            + NUM_ACTIONS,
        ],
    )


def test_layout_is_287d_plus_exactly_two_action_aligned_blocks() -> None:
    environment, observation = _fixture()
    encoded = encode_ee_axis_v015_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )

    assert V015_C3_ACTION_BLOCKS == (
        "current_same_beam_user_fraction",
        "current_same_satellite_user_fraction",
    )
    assert V015_C3_STATE_DIM == V014_Q3_STATE_DIM + 2 * NUM_ACTIONS == 343
    assert encoded.state_matrix.shape == (3, V015_C3_STATE_DIM)
    assert encoded.action_masks.shape == (3, NUM_ACTIONS)
    assert V015_C3_CURRENT_BEAM_START == 10 * NUM_ACTIONS
    assert V015_C3_CURRENT_SATELLITE_START == 11 * NUM_ACTIONS
    assert encoded.verify() == encoded.state_sha256


def test_current_physical_user_fractions_exclude_focal_and_count_each_peer_once() -> None:
    environment, observation = _fixture()
    encoded = encode_ee_axis_v015_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    beam, satellite = _blocks(encoded)

    # Fractions are over the two non-focal users.  User 0's (101,1) action
    # sees both peers; user 0's (202,2) sees only user 1; and the repeated
    # (101,1) slots of user 1 still count user 0 and user 2 once each.
    assert beam[0, 0] == pytest.approx(1.0)
    assert satellite[0, 0] == pytest.approx(1.0)
    assert beam[0, 1] == pytest.approx(0.5)
    assert satellite[0, 1] == pytest.approx(0.5)
    assert beam[0, 2] == pytest.approx(0.5)
    assert satellite[0, 2] == pytest.approx(1.0)
    assert beam[1, 0] == pytest.approx(1.0)
    assert satellite[1, 0] == pytest.approx(1.0)
    assert beam[1, 2] == pytest.approx(0.0)
    assert satellite[1, 2] == pytest.approx(0.0)


def test_illegal_actions_are_zero_and_encoder_is_preoutcome_deterministic_immutable() -> None:
    environment, observation = _fixture()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("state encoder must not evaluate an outcome")

    environment.evaluate_actions = fail_if_called
    first = encode_ee_axis_v015_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    second = encode_ee_axis_v015_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    beam, satellite = _blocks(first)
    assert np.all(beam[~observation.masks] == 0.0)
    assert np.all(satellite[~observation.masks] == 0.0)
    assert first.state_sha256 == second.state_sha256
    assert not first.state_matrix.flags.writeable
    assert not first.action_masks.flags.writeable
    with pytest.raises(ValueError):
        first.state_matrix[0, V014_Q3_STATE_DIM] = 1.0


def test_encoder_rejects_mask_drift_and_nonpositive_constants() -> None:
    environment, observation = _fixture()
    observation.masks[0, 0] = False
    with pytest.raises(EEAxisV015C3StateError, match="mask"):
        encode_ee_axis_v015_c3_state(
            environment, observation, interval_s=2.0, kappa_bits=100.0
        )

    environment, observation = _fixture()
    with pytest.raises(EEAxisV015C3StateError, match="interval_s"):
        encode_ee_axis_v015_c3_state(
            environment, observation, interval_s=0.0, kappa_bits=100.0
        )
