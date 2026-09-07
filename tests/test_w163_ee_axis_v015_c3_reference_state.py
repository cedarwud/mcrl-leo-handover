"""W-163 -- V0.15 reference-conditioned C3 state boundary."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.env.interference import RadiatingBeams
from mcrl.env.step import StepEnvironment, StepObservation
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v014_q3_state import (
    encode_ee_axis_v014_q3_state,
)
from mcrl.runtime.ee_axis_v015_c3_reference_state import (
    EEAxisV015C3ReferenceStateError,
    V015_C3_REFERENCE_BEAM_START,
    V015_C3_REFERENCE_GLOBAL_START,
    V015_C3_REFERENCE_LOCAL_FEATURES,
    V015_C3_REFERENCE_LOCAL_PREFIX_DIM,
    V015_C3_REFERENCE_POWER_GAP_START,
    V015_C3_REFERENCE_SATELLITE_START,
    V015_C3_REFERENCE_STATE_DIM,
    encode_ee_axis_v015_c3_reference_state,
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
        # The peer has the same physical beam in two different slots.  The
        # reference vector chooses one of them, so it must count once.
        _table({0: (101, 1), 1: (101, 1), 2: (303, 3), 3: (202, 2)}),
        # Action 1 is deliberately the same physical beam as user 0's action
        # 2, while its flat index is different.
        _table({0: (404, 4), 1: (101, 2), 2: (505, 5)}),
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


def _inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # c_0=0=(101,1), c_1=0=(101,1), c_2=1=(101,2).  User 0 action 2
    # matches user 2 physically despite the different slot index.
    references = np.asarray([0, 0, 1], dtype=np.int64)
    opening = np.zeros((3, NUM_ACTIONS), dtype=np.bool_)
    opening[np.arange(3), references] = True
    powers = np.zeros((3, NUM_ACTIONS), dtype=np.float64)
    powers[0, 0] = 0.5
    powers[0, 1] = 0.9
    powers[0, 2] = 0.8
    powers[1, 0] = 0.3
    powers[1, 1] = 0.4
    powers[1, 3] = 0.7
    powers[2, 1] = 0.9
    return references, opening, powers


def _encode(
    environment: StepEnvironment,
    observation: StepObservation,
    references: object,
    opening: object,
    powers: object,
):
    return encode_ee_axis_v015_c3_reference_state(
        environment,
        observation,
        reference_actions=references,
        current_required_power_w=powers,
        opening_service_feasible=opening,
        interval_s=2.0,
        kappa_bits=100.0,
        pmax_w=1.0,
    )


def test_layout_preserves_v014_locals_and_globals_around_three_action_blocks() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    encoded = _encode(environment, observation, references, opening, powers)
    base = encode_ee_axis_v014_q3_state(
        environment, observation, interval_s=2.0, kappa_bits=100.0
    )

    assert V015_C3_REFERENCE_LOCAL_FEATURES == 13
    assert V015_C3_REFERENCE_STATE_DIM == 287 + 3 * NUM_ACTIONS == 371
    assert encoded.state_matrix.shape == (3, V015_C3_REFERENCE_STATE_DIM)
    assert V015_C3_REFERENCE_LOCAL_PREFIX_DIM == 10 * NUM_ACTIONS == 280
    np.testing.assert_array_equal(
        encoded.state_matrix[:, :V015_C3_REFERENCE_LOCAL_PREFIX_DIM],
        base.state_matrix[:, :V015_C3_REFERENCE_LOCAL_PREFIX_DIM],
    )
    np.testing.assert_array_equal(
        encoded.state_matrix[:, V015_C3_REFERENCE_GLOBAL_START:],
        base.state_matrix[:, V015_C3_REFERENCE_LOCAL_PREFIX_DIM:],
    )
    assert V015_C3_REFERENCE_BEAM_START == 280
    assert V015_C3_REFERENCE_SATELLITE_START == 280 + NUM_ACTIONS
    assert V015_C3_REFERENCE_POWER_GAP_START == 280 + 2 * NUM_ACTIONS
    assert V015_C3_REFERENCE_GLOBAL_START == 13 * NUM_ACTIONS == 364
    assert encoded.verify() == encoded.state_sha256


def test_physical_matches_are_not_flat_index_matches_and_peer_is_counted_once() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    encoded = _encode(environment, observation, references, opening, powers)
    beam = encoded.state_matrix[
        :, V015_C3_REFERENCE_BEAM_START : V015_C3_REFERENCE_SATELLITE_START
    ]
    satellite = encoded.state_matrix[
        :, V015_C3_REFERENCE_SATELLITE_START : V015_C3_REFERENCE_POWER_GAP_START
    ]
    gap = encoded.state_matrix[:, V015_C3_REFERENCE_POWER_GAP_START :]

    # User 0's (101,1) candidate sees user 1's repeated (101,1) physical
    # slots through its one reference, hence 1/2 rather than 2/2.  Its
    # satellite fraction sees user 0's two peers on satellite 101.
    assert beam[0, 0] == pytest.approx(0.5)
    assert satellite[0, 0] == pytest.approx(1.0)
    assert gap[0, 0] == pytest.approx(0.2)

    # User 0's action 2 and user 2's reference action 1 are a physical match
    # despite different flat indices.  The power gap is 0.8 - 0.9.
    assert beam[0, 2] == pytest.approx(0.5)
    assert satellite[0, 2] == pytest.approx(1.0)
    assert gap[0, 2] == pytest.approx(-0.1)


def test_infeasible_reference_is_excluded_from_every_peer_aggregate() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    opening[1, 0] = False
    encoded = _encode(environment, observation, references, opening, powers)
    beam = encoded.state_matrix[
        :, V015_C3_REFERENCE_BEAM_START : V015_C3_REFERENCE_SATELLITE_START
    ]
    satellite = encoded.state_matrix[
        :, V015_C3_REFERENCE_SATELLITE_START : V015_C3_REFERENCE_POWER_GAP_START
    ]
    gap = encoded.state_matrix[:, V015_C3_REFERENCE_POWER_GAP_START :]

    # The only same-beam peer of user 0's (101,1) was user 1, and it is not
    # opening-service-feasible.  The other peer remains on satellite 101.
    assert beam[0, 0] == pytest.approx(0.0)
    assert satellite[0, 0] == pytest.approx(0.5)
    assert gap[0, 0] == pytest.approx(0.5)


def test_illegal_focal_entries_are_zero_and_values_are_bounded() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    powers[0, 1] = 20.0
    powers[1, 0] = 20.0
    encoded = _encode(environment, observation, references, opening, powers)
    blocks = encoded.state_matrix[
        :, V015_C3_REFERENCE_BEAM_START : V015_C3_REFERENCE_GLOBAL_START
    ]
    assert np.all(blocks[:, : 3 * NUM_ACTIONS] <= 1.0)
    assert np.all(blocks[:, : 2 * NUM_ACTIONS] >= 0.0)
    assert np.all(blocks[:, 2 * NUM_ACTIONS :] <= 1.0)
    assert np.all(blocks[:, 2 * NUM_ACTIONS :] >= -1.0)
    block_matrix = blocks.reshape(3, 3, NUM_ACTIONS)
    for user in range(3):
        for block in block_matrix[user]:
            assert np.all(block[~observation.masks[user]] == 0.0)


def test_reference_pass_is_preoutcome_deterministic_and_immutable() -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("state encoder must not evaluate an outcome")

    environment.evaluate_actions = fail_if_called
    first = _encode(environment, observation, references, opening, powers)
    second = _encode(environment, observation, references, opening, powers)
    assert first.state_sha256 == second.state_sha256
    assert not first.state_matrix.flags.writeable
    assert not first.action_masks.flags.writeable
    with pytest.raises(ValueError):
        first.state_matrix[0, V015_C3_REFERENCE_BEAM_START] = 1.0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("reference", np.asarray([0.0, 0.0, 1.0]), "reference_actions"),
        ("reference", np.asarray([-1, 0, 1]), "only for an all-empty"),
        (
            "opening",
            np.ones((3, NUM_ACTIONS), dtype=np.bool_),
            "opening_service_feasible",
        ),
        ("power", np.full((3, NUM_ACTIONS), -1.0), "current_required_power_w"),
        ("pmax", 0.0, "pmax_w"),
    ),
)
def test_input_validation_rejects_noncontract_values(
    field: str, value: object, message: str
) -> None:
    environment, observation = _fixture()
    references, opening, powers = _inputs()
    if field == "reference":
        references = value
    elif field == "opening":
        opening = value
    elif field == "power":
        powers = value
    with pytest.raises(EEAxisV015C3ReferenceStateError, match=message):
        if field == "pmax":
            encode_ee_axis_v015_c3_reference_state(
                environment,
                observation,
                reference_actions=references,
                current_required_power_w=powers,
                opening_service_feasible=opening,
                interval_s=2.0,
                kappa_bits=100.0,
                pmax_w=value,
            )
        else:
            _encode(environment, observation, references, opening, powers)
