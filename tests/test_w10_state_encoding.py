"""W-10 — the 125-dimensional state encoding (SDD §3.6, §4A.6)."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import (
    CONTRACT_STATE_DIM,
    NUM_ACTIONS,
    STATE_DIM,
    SatelliteCandidate,
    assign_satellite_slots,
    contract_state_fields,
)
from mcrl.env.step_types import UserState
from mcrl.errors import MCRLContractError
from mcrl.runtime.state_encoding import encode_state, state_dim_for
from mcrl.runtime.trainer_spec import TrainerConfig

CONFIG = TrainerConfig()


def _state(num_beams=NUM_ACTIONS, contract=None):
    return UserState(
        access_vector=np.zeros(num_beams),
        channel_quality=np.full(num_beams, 3.0),
        beam_offsets=np.linspace(0.0, 0.1, num_beams),
        beam_loads=np.arange(num_beams, dtype=float),
        contract_fields=(
            np.zeros(CONTRACT_STATE_DIM, dtype=np.float32)
            if contract is None
            else contract
        ),
    )


# -- the authoritative dimension ------------------------------------------


def test_the_state_dimension_is_125():
    assert state_dim_for(NUM_ACTIONS) == 125
    assert state_dim_for(NUM_ACTIONS) == 4 * NUM_ACTIONS + CONTRACT_STATE_DIM
    assert state_dim_for(NUM_ACTIONS) == STATE_DIM


def test_the_encoder_agrees_with_the_declared_dimension():
    encoded = encode_state(_state(), num_users=100, config=CONFIG)
    assert encoded.shape == (state_dim_for(NUM_ACTIONS),)
    assert encoded.dtype == np.float32


def test_the_two_declarations_of_125_cannot_drift_apart():
    """``action_contract.STATE_DIM`` and ``state_dim_for`` are both quoted."""
    assert STATE_DIM == state_dim_for(NUM_ACTIONS)


# -- block layout ----------------------------------------------------------


def test_the_four_blocks_keep_their_order_and_the_contract_comes_last():
    contract = np.arange(CONTRACT_STATE_DIM, dtype=np.float32)
    state = _state(contract=contract)
    encoded = encode_state(state, num_users=4, config=CONFIG)

    n = NUM_ACTIONS
    assert np.allclose(encoded[:n], state.access_vector)
    assert np.allclose(encoded[n : 2 * n], np.log1p(state.channel_quality))
    assert np.allclose(encoded[2 * n : 3 * n], state.beam_offsets)
    assert np.allclose(encoded[3 * n : 4 * n], state.beam_loads / 4)
    assert np.allclose(encoded[4 * n :], contract)


def test_the_contract_block_is_the_one_the_action_contract_builds():
    assignment = assign_satellite_slots(
        [
            SatelliteCandidate(44714, True, 300.0, -6.1, 3),
            SatelliteCandidate(44718, True, 200.0, 4.2, 1),
        ],
        incumbent_norad=44714,
    )
    contract = contract_state_fields(assignment, dwell_phase=0.25)
    encoded = encode_state(
        _state(contract=contract), num_users=10, config=CONFIG
    )
    assert np.allclose(encoded[4 * NUM_ACTIONS :], contract)
    # is_incumbent, ttt, radial rate, dwell phase — in that order.
    tail = encoded[4 * NUM_ACTIONS :]
    assert tail[0] == 1.0 and tail[1] == 0.0
    assert tail[4] == 3.0 and tail[5] == 1.0
    assert tail[8] < 0.0 < tail[9]
    assert tail[12] == pytest.approx(0.25)


def test_state_and_action_stay_aligned_by_construction():
    """§4A.1: the per-beam blocks use the same (l, j) order as the index."""
    access = np.zeros(NUM_ACTIONS)
    access[9] = 1.0  # satellite slot 1, beam slot 2
    state = UserState(
        access_vector=access,
        channel_quality=np.zeros(NUM_ACTIONS),
        beam_offsets=np.zeros(NUM_ACTIONS),
        beam_loads=np.zeros(NUM_ACTIONS),
        contract_fields=np.zeros(CONTRACT_STATE_DIM, dtype=np.float32),
    )
    encoded = encode_state(state, num_users=1, config=CONFIG)
    assert encoded[9] == 1.0
    assert int(np.argmax(encoded[:NUM_ACTIONS])) == 9


# -- fail loud rather than emit a short vector ----------------------------


def test_a_missing_contract_block_raises():
    """The failure this guards: a silent 112-vector that fits no network."""
    state = UserState(
        access_vector=np.zeros(NUM_ACTIONS),
        channel_quality=np.zeros(NUM_ACTIONS),
        beam_offsets=np.zeros(NUM_ACTIONS),
        beam_loads=np.zeros(NUM_ACTIONS),
    )
    assert state.contract_fields is None
    with pytest.raises(MCRLContractError, match="contract_fields is required"):
        encode_state(state, num_users=1, config=CONFIG)


@pytest.mark.parametrize("bad_length", [0, 12, 14, 28])
def test_a_wrong_length_contract_block_raises(bad_length):
    with pytest.raises(MCRLContractError, match="must have shape"):
        encode_state(
            _state(contract=np.zeros(bad_length, dtype=np.float32)),
            num_users=1,
            config=CONFIG,
        )


def test_mismatched_beam_blocks_still_raise():
    state = UserState(
        access_vector=np.zeros(NUM_ACTIONS),
        channel_quality=np.zeros(NUM_ACTIONS - 1),
        beam_offsets=np.zeros(NUM_ACTIONS),
        beam_loads=np.zeros(NUM_ACTIONS),
        contract_fields=np.zeros(CONTRACT_STATE_DIM, dtype=np.float32),
    )
    with pytest.raises(ValueError, match="equal lengths"):
        encode_state(state, num_users=1, config=CONFIG)


# -- the W-01 import gap is closed ----------------------------------------


def test_user_state_is_imported_from_its_canonical_home():
    """PROVENANCE's last open port item: state_encoding pointed at env.step."""
    import mcrl.runtime.state_encoding as module

    assert module.UserState.__module__ == "mcrl.env.step_types"


def test_the_algorithm_no_longer_imports_the_old_environment_at_runtime():
    import sys

    import mcrl.algorithms.modqn as trainer

    assert trainer.UserState.__module__ == "mcrl.env.step_types"
    assert trainer.ActionMask.__module__ == "mcrl.env.step_types"
    assert trainer.RewardComponents.__module__ == "mcrl.env.step_types"

    # The test shim no longer installs a stand-in for the old environment
    # module, and nothing imports it, so it must be absent entirely.
    assert "mcrl.env.step" not in sys.modules

    source = __import__("pathlib").Path(trainer.__file__).read_text()
    assert "from ..env.step_types import" in source
    assert "if TYPE_CHECKING:" in source
