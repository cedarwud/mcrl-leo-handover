"""V0.4 C3 victim-burden state seam."""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import Association, NUM_ACTIONS, SlotTable
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.interference import RadiatingBeams
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import Segment, StepEnvironment, StepObservation
from mcrl.env.tle import TleArchive
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v04_c3_state import (
    EE_AXIS_V04_C3_STATE_DIM,
    EEAxisV04C3StateContractError,
    encode_ee_axis_v04_c3_state,
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
    previous: list[Association | None] | None = None,
    rates: list[float] | None = None,
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
    start_gain = 1.0
    environment._segments = [
        None if association is None else Segment(
            association.norad_id,
            association.cell_id,
            start_gain,
            age_steps=0,
        )
        for association in environment._previous_association
    ]
    environment._previous_link_power_w = np.zeros(3, dtype=np.float64)
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
    base = EE_AXIS_BASE_STATE_DIM
    beam = encoded.state_matrix[:, base : base + NUM_ACTIONS]
    satellite = encoded.state_matrix[:, base + 2 * NUM_ACTIONS : base + 3 * NUM_ACTIONS]
    return beam, satellite


def test_episode_start_burdens_are_exactly_zero_and_state_is_228d():
    environment, observation = _fixture()
    encoded = encode_ee_axis_v04_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    beam, satellite = _blocks(encoded)

    assert encoded.state_matrix.shape == (3, EE_AXIS_V04_C3_STATE_DIM)
    assert np.array_equal(beam, np.zeros_like(beam))
    assert np.array_equal(satellite, np.zeros_like(satellite))
    assert encoded.verify() == encoded.state_sha256


def test_frozen_normalization_constants_are_keyword_only():
    environment, observation = _fixture()
    with pytest.raises(TypeError):
        encode_ee_axis_v04_c3_state(environment, observation, 2.0, 100.0)


def test_committed_rate_burdens_match_both_formulas_and_exclude_focal_rate():
    environment, observation = _fixture(
        previous=[Association(101, 1), Association(101, 1), Association(101, 2)],
        rates=[100.0, 200.0, 300.0],
    )
    encoded = encode_ee_axis_v04_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    beam, satellite = _blocks(encoded)

    # interval/kappa = 2/100.  Each expected value excludes the row's own
    # previous served rate, even when the represented action is its incumbent.
    assert beam[0, 0] == pytest.approx(4.0)       # user 1 on (101, 1)
    assert satellite[0, 0] == pytest.approx(10.0) # users 1 and 2 on NORAD 101
    assert beam[1, 0] == pytest.approx(2.0)       # user 0 on (101, 1)
    assert satellite[1, 0] == pytest.approx(8.0) # users 0 and 2 on NORAD 101
    assert beam[1, 2] == pytest.approx(6.0)       # user 2 on (101, 2)
    assert satellite[1, 2] == pytest.approx(8.0)  # users 0 and 2 on NORAD 101
    assert beam[2, 0] == pytest.approx(0.0)       # no other user on (101, 2)
    assert satellite[2, 0] == pytest.approx(6.0)  # users 0 and 1 on NORAD 101


def test_illegal_actions_are_zero_and_output_is_immutable_deterministic():
    environment, observation = _fixture(
        previous=[Association(101, 1), Association(101, 1), Association(101, 2)],
        rates=[100.0, 200.0, 300.0],
    )
    first = encode_ee_axis_v04_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    second = encode_ee_axis_v04_c3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )
    beam, satellite = _blocks(first)

    assert np.all(beam[~observation.masks] == 0.0)
    assert np.all(satellite[~observation.masks] == 0.0)
    assert first.state_sha256 == second.state_sha256
    assert np.array_equal(first.state_matrix, second.state_matrix)
    assert not first.state_matrix.flags.writeable
    assert not first.action_masks.flags.writeable
    with pytest.raises(ValueError):
        first.state_matrix[0, EE_AXIS_BASE_STATE_DIM] = 0.0


def test_missing_committed_rate_vector_is_rejected():
    environment, observation = _fixture()
    del environment._previous_served_rate_bps
    with pytest.raises(EEAxisV04C3StateContractError, match="served-rate"):
        encode_ee_axis_v04_c3_state(
            environment, observation, interval_s=2.0, kappa_bits=100.0
        )


_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
_START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


def _first_valid_actions(masks: np.ndarray) -> np.ndarray:
    return np.asarray([int(np.flatnonzero(mask)[0]) for mask in masks], dtype=np.int64)


@requires_archive
def test_step_commits_served_rates_and_evaluate_actions_does_not_change_them():
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(_ARCHIVE),
            ScenarioConfig(mobility=MobilityConfig(num_users=4)),
        )
    )
    rng = np.random.default_rng(2026090101)
    observation = environment.reset(_START, rng)
    outcome = environment.step(_first_valid_actions(observation.masks), rng)

    expected = np.where(
        outcome.resolution.served,
        outcome.link_rate_bps,
        0.0,
    )
    assert np.array_equal(environment._previous_served_rate_bps, expected)

    before_rates = environment._previous_served_rate_bps.copy()
    before_state = encode_ee_axis_v04_c3_state(
        environment,
        outcome.observation,
        interval_s=environment.driver.config.ephemeris.time_step_s,
        kappa_bits=10.0,
    )
    before_digest = before_state.state_sha256
    state_before_eval = copy.deepcopy(rng.bit_generator.state)
    environment.evaluate_actions(
        _first_valid_actions(outcome.observation.masks),
        rng,
    )
    after_state = encode_ee_axis_v04_c3_state(
        environment,
        outcome.observation,
        interval_s=environment.driver.config.ephemeris.time_step_s,
        kappa_bits=10.0,
    )

    assert np.array_equal(environment._previous_served_rate_bps, before_rates)
    assert before_state.state_sha256 == after_state.state_sha256 == before_digest
    assert rng.bit_generator.state == state_before_eval
