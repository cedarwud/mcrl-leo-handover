"""W-185 -- heterogeneous Q1/Q2 plus structured LC-SRS Q3 integration."""

from __future__ import annotations

from copy import deepcopy
import hashlib

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import (
    EEAxisActionSharedConfig,
    EEAxisActionSharedTrainer,
)
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    DetachedQ12Snapshot,
    EEAxisLCSRSThreeRoute,
    LCSRSThreeRouteConfig,
)
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


def _config() -> LCSRSThreeRouteConfig:
    return LCSRSThreeRouteConfig(
        q12=EEAxisActionSharedConfig(
            state_dim=228,
            action_dim=28,
            hidden_layers=(16,),
            activation="relu",
            learning_rate=1.0e-3,
            kappa_bits=10_097_071_012.757404,
            beta=0.1,
            loss_weights=(1.0, 1.0, 1.0),
        )
    )


_NATIVE_EVENT_DIGEST = hashlib.sha256(
    b"w185-native-observation-event"
).hexdigest()


def _capture_q12(model: EEAxisLCSRSThreeRoute, states: object) -> DetachedQ12Snapshot:
    return model.capture_q12(
        states,
        native_observation_event_digest=_NATIVE_EVENT_DIGEST,
    )


def _view(snapshot: DetachedQ12Snapshot, *, ordinary_on_action: int | None = None):
    users, actions = snapshot.q12.shape
    action_mask = np.ones((users, actions), dtype=np.bool_)
    references = np.argmax(snapshot.q12, axis=1).astype(np.int64)
    context = np.zeros((users, actions, 29), dtype=np.float32)
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1] = 1.0
    if ordinary_on_action is not None:
        token_mask[0, ordinary_on_action, 1] = True
        tokens[0, ordinary_on_action, 1, 0] = 1.0
    return assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=references,
    )


def _constant_q3(model: EEAxisLCSRSThreeRoute, value: float) -> None:
    with torch.no_grad():
        for module in model.q3.token_scorer:
            if isinstance(module, torch.nn.Linear):
                module.weight.zero_()
                module.bias.zero_()
        final = model.q3.token_scorer[-1]
        assert isinstance(final, torch.nn.Linear)
        final.bias.fill_(value)


def test_exactly_three_independent_networks_optimizers_and_route_shapes() -> None:
    model = EEAxisLCSRSThreeRoute(_config(), train_seed=17)
    assert len(model.q_networks) == 3
    assert len(model.optimizers) == 3
    parameter_ids = [
        {id(parameter) for parameter in network.parameters()}
        for network in model.q_networks
    ]
    assert not parameter_ids[0] & parameter_ids[1]
    assert not parameter_ids[0] & parameter_ids[2]
    assert not parameter_ids[1] & parameter_ids[2]

    states = np.zeros((3, 228), dtype=np.float32)
    snapshot = _capture_q12(model, states)
    view = _view(snapshot)
    q1, q2, q3 = model.q_values(snapshot, view)
    assert q1.shape == q2.shape == q3.shape == (3, 28)
    assert not snapshot.q1.flags.writeable
    assert not snapshot.q2.flags.writeable
    assert not snapshot.q12.flags.writeable


def test_one_sum_one_argmax_uses_snapshot_without_recomputing_q12() -> None:
    model = EEAxisLCSRSThreeRoute(_config(), train_seed=23)
    snapshot = _capture_q12(model, np.zeros((2, 228), dtype=np.float32))
    view = _view(snapshot, ordinary_on_action=1)
    _constant_q3(model, 0.25)
    expected_scores = snapshot.q12 + model.q3.forward_view(view).detach().numpy()
    expected = np.argmax(expected_scores, axis=1)
    np.testing.assert_array_equal(model.select_greedy_actions(snapshot, view), expected)

    # Later Q1/Q2 mutation cannot alter the already captured decision snapshot.
    with torch.no_grad():
        for network in (model.q1, model.q2):
            for parameter in network.parameters():
                parameter.add_(100.0)
    np.testing.assert_array_equal(model.deployment_scores(snapshot, view), expected_scores)


def test_q12_snapshot_binds_source_state_and_model_digests() -> None:
    model = EEAxisLCSRSThreeRoute(_config(), train_seed=24)
    first_states = np.zeros((2, 228), dtype=np.float32)
    first = _capture_q12(model, first_states)
    repeat = _capture_q12(model, first_states.copy())
    assert first.source_state_digest == repeat.source_state_digest
    assert first.model_digest == repeat.model_digest
    assert first.content_digest == repeat.content_digest

    second_states = first_states.copy()
    second_states[0, 0] = 1.0
    changed_state = _capture_q12(model, second_states)
    assert changed_state.source_state_digest != first.source_state_digest

    with torch.no_grad():
        next(model.q1.parameters()).add_(1.0)
    changed_model = _capture_q12(model, first_states)
    assert changed_model.model_digest != first.model_digest
    assert changed_model.content_digest != first.content_digest


def test_c3_view_reference_must_equal_snapshot_masked_q12_argmax() -> None:
    model = EEAxisLCSRSThreeRoute(_config(), train_seed=29)
    snapshot = _capture_q12(model, np.zeros((2, 228), dtype=np.float32))
    valid = _view(snapshot)
    bad_references = (valid.reference_actions + 1) % 28
    bad = assemble_c3_view(
        action_context=valid.action_context,
        tokens=valid.tokens,
        token_mask=valid.token_mask,
        action_mask=valid.action_mask,
        reference_actions=bad_references,
    )
    with pytest.raises(MCRLContractError, match=r"masked Q1\+Q2 argmax"):
        model.q_values(snapshot, bad)


def test_loads_only_q1_q2_from_legacy_background() -> None:
    config = _config()
    legacy = EEAxisActionSharedTrainer(config.q12, train_seed=31)
    model = EEAxisLCSRSThreeRoute(config, train_seed=37)
    q3_before = deepcopy(model.q3.state_dict())
    model.load_q12_background(legacy.checkpoint_state(update_count=3000))

    states = np.arange(2 * 228, dtype=np.float32).reshape(2, 228) / 1000.0
    legacy_q1, legacy_q2, _legacy_q3 = legacy.q_values(states)
    snapshot = _capture_q12(model, states)
    np.testing.assert_array_equal(snapshot.q1, legacy_q1)
    np.testing.assert_array_equal(snapshot.q2, legacy_q2)
    for name, value in model.q3.state_dict().items():
        torch.testing.assert_close(value, q3_before[name], rtol=0.0, atol=0.0)


def test_three_route_checkpoint_round_trip_and_schema_guard() -> None:
    config = _config()
    source = EEAxisLCSRSThreeRoute(config, train_seed=41)
    state = source.checkpoint_state(update_count=12)
    target = EEAxisLCSRSThreeRoute(config, train_seed=41)
    assert target.load_checkpoint_state(state) == 12
    probe = np.ones((2, 228), dtype=np.float32)
    first = _capture_q12(source, probe)
    second = _capture_q12(target, probe)
    np.testing.assert_array_equal(first.q12, second.q12)

    tampered = deepcopy(state)
    tampered["c3_schema_sha256"] = "0" * 64
    with pytest.raises(MCRLContractError, match="schema"):
        target.load_checkpoint_state(tampered)
