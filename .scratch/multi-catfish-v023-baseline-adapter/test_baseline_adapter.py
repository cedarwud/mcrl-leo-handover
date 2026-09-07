"""Focused tests for the isolated pre-Catfish baseline adapter."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch

import baseline_adapter as adapter_module
from baseline_adapter import (
    BaselineAdapter,
    BaselineAdapterError,
    CONTRACT_FIELDS_EXCLUDED,
    EXPECTED_ACTION_DIM,
    EXPECTED_CHECKPOINT_SHA256,
    EXPECTED_EPISODES,
    EXPECTED_OBJECTIVE_WEIGHTS,
    EXPECTED_STATE_DIM,
)
from mcrl.env.action_contract import CONTRACT_STATE_DIM, NO_OP_ACTION
from mcrl.env.step_types import ActionMask, UserState


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = (
    ROOT
    / "artifacts"
    / "training-2026-08-25-rerun01"
    / "main"
    / "final-checkpoint.pt"
)
STATUS = CHECKPOINT.with_name("status.json")
OWNED_DIR = Path(__file__).parent


@pytest.fixture
def adapter() -> BaselineAdapter:
    return BaselineAdapter.from_artifacts(CHECKPOINT, STATUS)


@pytest.fixture
def owned_tmp_dir():
    with tempfile.TemporaryDirectory(prefix=".test-", dir=OWNED_DIR) as raw:
        yield Path(raw)


def _synthetic_state() -> UserState:
    access = np.zeros(EXPECTED_ACTION_DIM, dtype=np.float32)
    access[4] = 1.0
    return UserState(
        access_vector=access,
        channel_quality=np.linspace(0.0, 2.0, EXPECTED_ACTION_DIM),
        beam_offsets=np.linspace(-0.2, 0.2, EXPECTED_ACTION_DIM),
        beam_loads=np.full(EXPECTED_ACTION_DIM, 4.0, dtype=np.float32),
    )


def _with_contract_fields(
    state: UserState, contract_fields: np.ndarray | None
) -> UserState:
    return UserState(
        access_vector=state.access_vector,
        channel_quality=state.channel_quality,
        beam_offsets=state.beam_offsets,
        beam_loads=state.beam_loads,
        contract_fields=contract_fields,
    )


def _mask(*valid_actions: int) -> ActionMask:
    values = np.zeros(EXPECTED_ACTION_DIM, dtype=bool)
    values[list(valid_actions)] = True
    return ActionMask(mask=values)


def test_real_checkpoint_load_is_authenticated_and_read_only():
    before_bytes = CHECKPOINT.read_bytes()
    before_stat = CHECKPOINT.stat()

    loaded = BaselineAdapter.from_artifacts(CHECKPOINT, STATUS)

    assert loaded.checkpoint_sha256 == EXPECTED_CHECKPOINT_SHA256
    assert loaded.state_dim == EXPECTED_STATE_DIM
    assert loaded.action_dim == EXPECTED_ACTION_DIM
    assert loaded.objective_weights == EXPECTED_OBJECTIVE_WEIGHTS
    assert loaded.trainer_config["episodes"] == EXPECTED_EPISODES
    assert loaded.trainer_config["hidden_layers"] == (100, 50, 50)
    assert loaded.trainer_config["activation"] == "tanh"
    assert loaded.contract_fields_excluded is CONTRACT_FIELDS_EXCLUDED is True
    assert loaded.binding() == {
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "state_dim": EXPECTED_STATE_DIM,
        "action_dim": EXPECTED_ACTION_DIM,
        "training_episodes": EXPECTED_EPISODES,
        "contract_fields_excluded": True,
    }
    assert hashlib.sha256(CHECKPOINT.read_bytes()).hexdigest() == (
        EXPECTED_CHECKPOINT_SHA256
    )
    assert CHECKPOINT.read_bytes() == before_bytes
    after_stat = CHECKPOINT.stat()
    assert (after_stat.st_size, after_stat.st_mtime_ns) == (
        before_stat.st_size,
        before_stat.st_mtime_ns,
    )

    public_names = {name for name in dir(loaded) if not name.startswith("_")}
    assert not public_names.intersection({"train", "update", "optimizer", "optimizers"})
    assert "q_networks" not in public_names


def test_native_112d_encoding_and_weighted_masked_selection(adapter):
    state = _synthetic_state()
    encoded = adapter.encode_states([state, state])
    expected = np.concatenate(
        [
            state.access_vector,
            np.log1p(state.channel_quality).astype(np.float32),
            state.beam_offsets,
            state.beam_loads / 2.0,
        ]
    ).astype(np.float32)
    assert encoded.shape == (2, EXPECTED_STATE_DIM)
    np.testing.assert_array_equal(encoded[0], expected)

    first_mask = _mask(0, 7, 19)
    second_mask = ActionMask(
        mask=np.zeros(EXPECTED_ACTION_DIM, dtype=bool)
    )
    actions = adapter.select_actions([state, state], [first_mask, second_mask])

    with torch.inference_mode():
        state_tensor = torch.tensor(encoded, dtype=torch.float32)
        q_values = np.stack(
            [
                network(state_tensor).detach().cpu().numpy()
                for network in adapter._q_networks
            ],
            axis=0,
        )
    scalarized = sum(
        weight * q_values[index]
        for index, weight in enumerate(EXPECTED_OBJECTIVE_WEIGHTS)
    )
    valid = first_mask.mask
    masked = scalarized[0].copy()
    masked[~valid] = -np.inf
    assert int(actions[0]) == int(np.argmax(masked))
    assert bool(first_mask.mask[actions[0]])
    assert int(actions[1]) == NO_OP_ACTION
    assert adapter.select_action(state, first_mask, num_users=2) == int(actions[0])


def test_random_native_encodings_are_bit_identical_with_contract_fields(adapter):
    rng = np.random.default_rng(2927175120652069826)
    for _ in range(64):
        num_users = int(rng.integers(1, 257))
        access = np.zeros(EXPECTED_ACTION_DIM, dtype=np.float32)
        if bool(rng.integers(0, 2)):
            access[int(rng.integers(0, EXPECTED_ACTION_DIM))] = 1.0
        state = UserState(
            access_vector=access,
            channel_quality=rng.uniform(
                0.0, 1.0e4, EXPECTED_ACTION_DIM
            ).astype(np.float32),
            beam_offsets=rng.uniform(
                -np.pi, np.pi, EXPECTED_ACTION_DIM
            ).astype(np.float32),
            beam_loads=rng.integers(
                0, num_users + 1, EXPECTED_ACTION_DIM
            ).astype(np.float32),
            contract_fields=None,
        )
        populated = _with_contract_fields(
            state, rng.normal(size=CONTRACT_STATE_DIM).astype(np.float32)
        )

        absent_encoding = adapter.encode_user_state(state, num_users=num_users)
        populated_encoding = adapter.encode_user_state(
            populated, num_users=num_users
        )

        assert absent_encoding.shape == (EXPECTED_STATE_DIM,)
        assert absent_encoding.tobytes(order="C") == populated_encoding.tobytes(
            order="C"
        )


def test_contract_block_inclusion_mutation_changes_the_encoding(adapter):
    state = _synthetic_state()
    zero_contract = _with_contract_fields(
        state, np.zeros(CONTRACT_STATE_DIM, dtype=np.float32)
    )
    signal_contract = _with_contract_fields(
        state,
        np.arange(1.0, CONTRACT_STATE_DIM + 1.0, dtype=np.float32),
    )

    zero_included = adapter_module.encode_state(
        zero_contract,
        5,
        adapter._encoding_config,
        include_contract_block=True,
    )
    signal_included = adapter_module.encode_state(
        signal_contract,
        5,
        adapter._encoding_config,
        include_contract_block=True,
    )

    assert zero_included.shape == signal_included.shape == (
        EXPECTED_STATE_DIM + CONTRACT_STATE_DIM,
    )
    assert zero_included.tobytes(order="C") != signal_included.tobytes(order="C")


def test_policy_construction_executes_contract_exclusion_check(monkeypatch):
    calls = 0
    original = adapter_module._assert_contract_fields_excluded

    def counted(config):
        nonlocal calls
        calls += 1
        original(config)

    monkeypatch.setattr(adapter_module, "_assert_contract_fields_excluded", counted)
    BaselineAdapter.from_artifacts(CHECKPOINT, STATUS)
    assert calls == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("channel_quality", np.array([np.nan] + [0.0] * 27, dtype=np.float32)),
        ("beam_loads", np.array([-1.0] + [0.0] * 27, dtype=np.float32)),
    ],
)
def test_state_drift_fails_closed(adapter, field, value):
    state = _synthetic_state()
    object.__setattr__(state, field, value)
    with pytest.raises(BaselineAdapterError, match="state"):
        adapter.encode_user_state(state, num_users=1)


def test_mask_shape_and_dtype_drift_fail_closed(adapter):
    state = _synthetic_state()
    with pytest.raises(BaselineAdapterError, match="mask"):
        adapter.select_action(
            state,
            ActionMask(mask=np.ones(EXPECTED_ACTION_DIM - 1, dtype=bool)),
            num_users=1,
        )
    with pytest.raises(BaselineAdapterError, match="boolean"):
        adapter.select_action(
            state,
            ActionMask(mask=np.ones(EXPECTED_ACTION_DIM, dtype=np.float32)),
            num_users=1,
        )


def test_nonfinite_network_output_fails_closed(adapter):
    with torch.no_grad():
        adapter._q_networks[0].net[0].weight[0, 0] = float("nan")
    with pytest.raises(BaselineAdapterError, match="nonfinite"):
        adapter.select_action(_synthetic_state(), _mask(3), num_users=1)


def test_hash_drift_and_symlink_fail_closed(adapter, owned_tmp_dir):
    del adapter
    modified = owned_tmp_dir / CHECKPOINT.name
    checkpoint_bytes = bytearray(CHECKPOINT.read_bytes())
    checkpoint_bytes[0] ^= 1
    modified.write_bytes(checkpoint_bytes)
    with pytest.raises(BaselineAdapterError, match="SHA-256"):
        BaselineAdapter.from_artifacts(modified, STATUS)

    link = owned_tmp_dir / "checkpoint-link.pt"
    try:
        os.symlink(CHECKPOINT, link)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(BaselineAdapterError, match="symlink"):
        BaselineAdapter.from_artifacts(link, STATUS)


def test_incomplete_status_fails_closed(owned_tmp_dir):
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    status["episodes_completed"] = EXPECTED_EPISODES - 1
    status_copy = owned_tmp_dir / STATUS.name
    status_copy.write_text(json.dumps(status), encoding="utf-8")
    with pytest.raises(BaselineAdapterError, match="episodes_completed"):
        BaselineAdapter.from_artifacts(CHECKPOINT, status_copy)


def test_config_and_nonfinite_payload_drift_fail_closed():
    payload = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)

    config_drift = copy.deepcopy(payload)
    config_drift["trainer_config"]["objective_weights"] = (0.6, 0.2, 0.2)
    with pytest.raises(BaselineAdapterError, match="trainer_config"):
        adapter_module._validate_payload(config_drift)

    nonfinite_drift = copy.deepcopy(payload)
    nonfinite_drift["q_networks"][1]["net.6.bias"][0] = float("nan")
    with pytest.raises(BaselineAdapterError, match="nonfinite"):
        adapter_module._validate_payload(nonfinite_drift)
