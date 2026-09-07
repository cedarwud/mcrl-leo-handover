"""W-121 -- signed-motion state for the feed-forward V0.7 Q2."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import (
    Association,
    NO_OP_ACTION,
    NUM_ACTIONS,
    SlotAssignment,
    SlotTable,
)
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.interference import RadiatingBeams
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import Segment, StepEnvironment, StepObservation
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_BASE_STATE_DIM,
    encode_ee_axis_state,
)
from mcrl.runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_CONTEXT_BLOCKS,
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
    EEAxisV07C2StateContractError,
    encode_ee_axis_v07_c2_state,
)


def _assignment(first_rate: float, second_rate: float, *, second_norad: int) -> SlotAssignment:
    return SlotAssignment(
        norad_ids=(101, second_norad, -1, -1),
        occupied=(True, True, False, False),
        is_incumbent=(True, False, False, False),
        margin_km=(100.0, 50.0, 0.0, 0.0),
        radial_rate_km_s=(first_rate, second_rate, 0.0, 0.0),
        ttt_counter=(2, 2, 0, 0),
    )


def _table(second_norad: int) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, norad, cell in (
        (0, 101, 1),
        (1, 101, 2),
        (7, second_norad, 3),
    ):
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


def _fixture(sign: float) -> tuple[StepEnvironment, StepObservation]:
    tables = (_table(202), _table(303))
    assignments = (
        _assignment(-1.25 * sign, 2.5 * sign, second_norad=202),
        _assignment(1.25 * sign, -3.0 * sign, second_norad=303),
    )
    candidates = SimpleNamespace(slot_tables=tables, assignments=assignments)
    masks = np.stack([table.mask for table in tables])
    base = np.zeros((2, EE_AXIS_BASE_STATE_DIM), dtype=np.float32)
    base[:, 0] = 1.0
    observation = StepObservation(
        step_index=2,
        candidates=candidates,
        user_states=(object(), object()),
        state_matrix=base,
        masks=masks,
        candidate_sinr=np.zeros((2, NUM_ACTIONS), dtype=np.float64),
    )
    environment = object.__new__(StepEnvironment)
    environment.num_users = 2
    environment._candidates = candidates
    environment._previous_association = [Association(101, 1), Association(101, 1)]
    environment._segments = [Segment(101, 1, 1.0, 2), Segment(101, 1, 1.0, 3)]
    environment._previous_link_power_w = np.asarray([1.1, 1.1], dtype=np.float64)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.asarray([101], dtype=np.int64),
        cell_ids=np.asarray([1], dtype=np.int64),
        satellite_ecef_km=np.zeros((1, 3), dtype=np.float64),
        cell_centre_ecef_km=np.zeros((1, 3), dtype=np.float64),
        colors=np.asarray([0], dtype=np.int64),
        power_w=np.asarray([1.1], dtype=np.float64),
    )
    environment.physics = SimpleNamespace(beam_power_max_w=2.2)
    environment.driver = SimpleNamespace(config=SimpleNamespace(steps_per_episode=10))
    return environment, observation


def test_v03_aliases_opposite_motion_but_v07_q2_state_separates_it() -> None:
    approaching_environment, approaching_observation = _fixture(1.0)
    receding_environment, receding_observation = _fixture(-1.0)

    old_approaching = encode_ee_axis_state(
        approaching_environment, approaching_observation
    )
    old_receding = encode_ee_axis_state(receding_environment, receding_observation)
    assert np.array_equal(old_approaching.state_matrix, old_receding.state_matrix)

    new_approaching = encode_ee_axis_v07_c2_state(
        approaching_environment, approaching_observation
    )
    new_receding = encode_ee_axis_v07_c2_state(
        receding_environment, receding_observation
    )
    assert not np.array_equal(new_approaching.state_matrix, new_receding.state_matrix)


def test_v07_q2_replaces_only_provably_redundant_beam_active_slice() -> None:
    environment, observation = _fixture(1.0)
    old = encode_ee_axis_state(environment, observation)
    new = encode_ee_axis_v07_c2_state(environment, observation)

    assert V07_C2_Q2_CONTEXT_BLOCKS == (
        "eligible_served_load",
        "signed_range_rate_km_s",
        "satellite_active",
        "maximum_required_link_power",
    )
    assert new.state_matrix.shape == (2, V07_C2_Q2_STATE_DIM)
    assert V07_C2_Q2_STATE_DIM == old.state_matrix.shape[1] == 228
    assert np.array_equal(
        new.state_matrix[:, :EE_AXIS_BASE_STATE_DIM],
        old.state_matrix[:, :EE_AXIS_BASE_STATE_DIM],
    )

    replaced = slice(
        EE_AXIS_BASE_STATE_DIM + NUM_ACTIONS,
        EE_AXIS_BASE_STATE_DIM + 2 * NUM_ACTIONS,
    )
    outside = np.ones(V07_C2_Q2_STATE_DIM, dtype=np.bool_)
    outside[replaced] = False
    assert np.array_equal(new.state_matrix[:, outside], old.state_matrix[:, outside])

    radial = new.state_matrix[:, replaced]
    assert radial[0, [0, 1, 7]].tolist() == pytest.approx([-1.25, -1.25, 2.5])
    assert radial[1, [0, 1, 7]].tolist() == pytest.approx([1.25, 1.25, -3.0])
    assert np.all(radial[~observation.masks] == 0.0)
    assert not new.state_matrix.flags.writeable
    assert new.verify() == new.state_sha256
    assert V07_C2_Q2_STATE_SCHEMA_SHA256 == (
        "70cef9bd525ded7df76138364afd31b2e804446b9d199d01ccef845e5a09d2c0"
    )


def test_v07_q2_fails_if_beam_active_is_not_recoverable_from_served_load() -> None:
    environment, observation = _fixture(1.0)
    environment._previous_radiating = RadiatingBeams(
        norad_ids=np.asarray([101, 202], dtype=np.int64),
        cell_ids=np.asarray([1, 3], dtype=np.int64),
        satellite_ecef_km=np.zeros((2, 3), dtype=np.float64),
        cell_centre_ecef_km=np.zeros((2, 3), dtype=np.float64),
        colors=np.asarray([0, 1], dtype=np.int64),
        power_w=np.asarray([1.1, 0.5], dtype=np.float64),
    )
    with pytest.raises(EEAxisV07C2StateContractError, match="redundant"):
        encode_ee_axis_v07_c2_state(environment, observation)


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)


@requires_archive
def test_v07_q2_encoder_accepts_a_canonical_committed_environment_step() -> None:
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=4)),
        )
    )
    rng = np.random.default_rng(2026090207)
    observation = environment.reset(
        dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc),
        rng,
    )
    actions = np.asarray(
        [
            int(np.flatnonzero(mask)[0]) if np.any(mask) else NO_OP_ACTION
            for mask in observation.masks
        ],
        dtype=np.int64,
    )
    outcome = environment.step(actions, rng)
    encoded = encode_ee_axis_v07_c2_state(environment, outcome.observation)

    assert encoded.state_matrix.shape == (4, V07_C2_Q2_STATE_DIM)
    assert encoded.verify() == encoded.state_sha256
