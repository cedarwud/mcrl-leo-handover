"""W-45 — causal, action-aligned V0.3 state schema."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable
from mcrl.env.interference import RadiatingBeams
from mcrl.env.antenna import transmit_gain_linear
from mcrl.env.step import Segment, StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_BASE_STATE_DIM,
    EE_AXIS_C2_CONTEXT_FEATURES,
    EE_AXIS_STATE_DIM,
    EEAxisStateContractError,
    encode_ee_axis_state,
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
        _table({0: (101, 1), 1: (202, 2), 2: (303, 3)}),
        _table({0: (101, 1), 1: (404, 4)}),
    )
    candidates = SimpleNamespace(slot_tables=tables)
    masks = np.stack([table.mask for table in tables])
    observation = StepObservation(
        step_index=2,
        candidates=candidates,
        user_states=(object(), object()),
        state_matrix=np.zeros((2, EE_AXIS_BASE_STATE_DIM), dtype=np.float32),
        masks=masks,
        candidate_sinr=np.zeros((2, NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = 2
    environment._candidates = candidates
    environment._previous_association = [
        Association(norad_id=101, cell_id=1),
        Association(norad_id=101, cell_id=1),
    ]
    start_gain = float(transmit_gain_linear(np.asarray([0.0]))[0])
    environment._segments = [
        Segment(101, 1, start_gain, age_steps=2),
        Segment(101, 1, start_gain, age_steps=3),
    ]
    environment._previous_link_power_w = np.array([1.1, 0.55], dtype=np.float64)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.array([101, 202], dtype=np.int64),
        cell_ids=np.array([1, 9], dtype=np.int64),
        satellite_ecef_km=np.zeros((2, 3), dtype=np.float64),
        cell_centre_ecef_km=np.zeros((2, 3), dtype=np.float64),
        colors=np.array([0, 1], dtype=np.int64),
        power_w=np.array([1.1, 0.55], dtype=np.float64),
    )
    environment.physics = SimpleNamespace(beam_power_max_w=2.2)
    environment.driver = SimpleNamespace(config=SimpleNamespace(steps_per_episode=10))
    return environment, observation


def test_v03_state_appends_exact_causal_action_aligned_blocks() -> None:
    environment, observation = _fixture()
    encoded = encode_ee_axis_state(environment, observation)
    assert encoded.state_matrix.shape == (2, EE_AXIS_STATE_DIM)
    base = EE_AXIS_BASE_STATE_DIM
    load = encoded.state_matrix[:, base : base + NUM_ACTIONS]
    beam = encoded.state_matrix[:, base + NUM_ACTIONS : base + 2 * NUM_ACTIONS]
    satellite = encoded.state_matrix[:, base + 2 * NUM_ACTIONS : base + 3 * NUM_ACTIONS]
    power = encoded.state_matrix[
        :, base + 3 * NUM_ACTIONS : base + 4 * NUM_ACTIONS
    ]

    assert load[0, 0] == 1.0
    assert load[1, 0] == 1.0
    assert beam[0, 0] == 1.0
    assert beam[0, 1] == 0.0
    assert satellite[0, 1] == 1.0
    assert power[0, 0] == 0.5
    assert power[0, 1] == 0.0
    assert np.all(load[~observation.masks] == 0.0)
    assert not encoded.state_matrix.flags.writeable
    assert not encoded.action_masks.flags.writeable
    assert encoded.verify() == encoded.state_sha256


def test_v03_state_appends_minimal_c2_observability_features() -> None:
    environment, observation = _fixture()
    encoded = encode_ee_axis_state(environment, observation)
    c2 = encoded.state_matrix[:, -len(EE_AXIS_C2_CONTEXT_FEATURES) :]

    assert EE_AXIS_C2_CONTEXT_FEATURES == (
        "previous_recurrence_power",
        "current_to_segment_start_gain_ratio",
        "segment_age",
        "missing_incumbent",
    )
    assert c2[:, 0].tolist() == pytest.approx([0.5, 0.25])
    assert c2[:, 1].tolist() == pytest.approx([1.0, 1.0])
    assert c2[:, 2].tolist() == pytest.approx([0.2, 0.3])
    assert c2[:, 3].tolist() == [0.0, 0.0]

    environment._previous_association[1] = Association(999, 9)
    environment._segments[1] = Segment(999, 9, 1.0, age_steps=3)
    missing = encode_ee_axis_state(environment, observation).state_matrix[
        :, -len(EE_AXIS_C2_CONTEXT_FEATURES) :
    ]
    assert missing[1, 1] == 0.0
    assert missing[1, 3] == 1.0


def test_v03_state_reads_committed_previous_service_not_ungated_demand() -> None:
    environment, observation = _fixture()
    environment._previous_demand = {(202, 2): 99}
    encoded = encode_ee_axis_state(environment, observation)
    load = encoded.state_matrix[
        :, EE_AXIS_BASE_STATE_DIM : EE_AXIS_BASE_STATE_DIM + NUM_ACTIONS
    ]
    assert load[0, 1] == 0.0


def test_v03_state_is_deterministic_and_does_not_mutate_environment() -> None:
    environment, observation = _fixture()
    before = tuple(environment._previous_association)
    first = encode_ee_axis_state(environment, observation)
    second = encode_ee_axis_state(environment, observation)
    assert first.state_sha256 == second.state_sha256
    assert np.array_equal(first.state_matrix, second.state_matrix)
    assert tuple(environment._previous_association) == before


def test_v03_state_rejects_stale_anchor_and_malformed_previous_state() -> None:
    environment, observation = _fixture()
    stale = StepObservation(
        step_index=observation.step_index,
        candidates=SimpleNamespace(slot_tables=observation.candidates.slot_tables),
        user_states=observation.user_states,
        state_matrix=observation.state_matrix,
        masks=observation.masks,
        candidate_sinr=observation.candidate_sinr,
    )
    with pytest.raises(EEAxisStateContractError, match="current predecision"):
        encode_ee_axis_state(environment, stale)
    environment._previous_association = [Association(101, 1)]
    with pytest.raises(EEAxisStateContractError, match="associations"):
        encode_ee_axis_state(environment, observation)
