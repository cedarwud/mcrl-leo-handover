"""Fast actual-class tests for the isolated V0.23 learner seam."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import (
    EEAxisLCSRSThreeRoute,
    LCSRSThreeRouteConfig,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import EEAxisV014NormalizedPairBatch
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_REFERENCE,
    LCSRSPairTargets,
    LCSRSAnchorSurface,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_heterogeneous_trainer_under_test",
    HERE / "v023_heterogeneous_trainer.py",
)
assert SPEC is not None and SPEC.loader is not None
API = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = API
SPEC.loader.exec_module(API)


def _config() -> LCSRSThreeRouteConfig:
    return LCSRSThreeRouteConfig(
        q12=EEAxisActionSharedConfig(
            state_dim=228,
            action_dim=28,
            hidden_layers=(8,),
            activation="relu",
            learning_rate=1.0e-2,
            kappa_bits=10.0,
            beta=0.2,
            loss_weights=(1.0, 2.0, 3.0),
        )
    )


def _model(seed: int = 17) -> EEAxisLCSRSThreeRoute:
    return EEAxisLCSRSThreeRoute(_config(), train_seed=seed)


def _pair_batch(*, bad_state_width: int | None = None) -> EEAxisPairBatch:
    width = 228 if bad_state_width is None else bad_state_width
    rows = 4
    states = np.zeros((rows, width), dtype=np.float32)
    states[:, 0] = np.asarray([0.1, -0.2, 0.3, -0.4], dtype=np.float32)
    states[:, 1] = np.asarray([0.5, 0.2, -0.1, 0.4], dtype=np.float32)
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray([0, 0, 1, 2], dtype=np.int64),
        candidate_actions=np.asarray([1, 2, 2, 3], dtype=np.int64),
        target_surplus_bits=np.asarray([5.0, -3.0, 1.0, 2.0], dtype=np.float64),
        action_masks=np.ones((rows, 28), dtype=np.bool_),
    )


def _normalized_pair_batch(
    *, bad_state_width: int | None = None
) -> EEAxisV014NormalizedPairBatch:
    rows = 4
    width = 448 if bad_state_width is None else bad_state_width
    states = np.zeros((rows, width), dtype=np.float32)
    states[:, 0] = np.asarray([0.1, -0.2, 0.3, -0.4], dtype=np.float32)
    states[:, 1] = np.asarray([0.5, 0.2, -0.1, 0.4], dtype=np.float32)
    return EEAxisV014NormalizedPairBatch(
        states=states,
        reference_actions=np.asarray([0, 0, 1, 2], dtype=np.int64),
        candidate_actions=np.asarray([1, 2, 2, 3], dtype=np.int64),
        normalized_target_deltas=np.asarray(
            [0.5, -0.3, 0.1, 0.2], dtype=np.float64
        ),
        action_masks=np.ones((rows, 28), dtype=np.bool_),
    )


def _surface() -> LCSRSAnchorSurface:
    users, actions = 3, 28
    context = np.zeros((users, actions, 29), dtype=np.float32)
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    action_mask = np.zeros((users, actions), dtype=np.bool_)
    action_mask[:, :3] = True
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0
    tokens[0, 1, users, 2:5] = 1.0
    tokens[1, 1, users, 2:5] = 1.0
    context[0, 1, 0] = 0.2
    context[1, 1, 0] = -0.2
    view = assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )
    draws = np.tile(np.asarray([[1.0, -1.0]], dtype=np.float64), (LCSRS_DRAW_COUNT, 1))
    pair = LCSRSPairTargets(
        pair_id="p0",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    return assemble_lcsrs_anchor_surface(view, [pair])


def _c3_batch() -> LCSRSC3SampledBatch:
    return LCSRSC3SampledBatch(
        anchor_indices=np.zeros(3, dtype=np.int64),
        row_classes=np.asarray([3, 3, LCSRS_ROW_REFERENCE], dtype=np.uint8),
        user_indices=np.asarray([0, 1, 2], dtype=np.int64),
        action_indices=np.asarray([1, 1, 0], dtype=np.int64),
        normalized_targets=np.asarray([1.0, -1.0, 0.0], dtype=np.float32),
    )


def _snapshot(model: EEAxisLCSRSThreeRoute) -> tuple[tuple[torch.Tensor, ...], ...]:
    return tuple(
        tuple(parameter.detach().clone() for parameter in network.parameters())
        for network in model.q_networks
    )


def _changed_routes(
    before: tuple[tuple[torch.Tensor, ...], ...],
    model: EEAxisLCSRSThreeRoute,
) -> set[int]:
    changed: set[int] = set()
    for index, (old, network) in enumerate(zip(before, model.q_networks, strict=True)):
        if any(
            not torch.equal(previous, current.detach())
            for previous, current in zip(old, network.parameters(), strict=True)
        ):
            changed.add(index)
    return changed


def _assert_off_route_grads_are_empty(model: EEAxisLCSRSThreeRoute, route: int) -> None:
    for index, network in enumerate(model.q_networks):
        if index == route:
            continue
        assert all(parameter.grad is None for parameter in network.parameters())


@pytest.mark.parametrize(
    ("route", "route_index"),
    [("C1", 0), ("C2", 1)],
)
def test_c1_c2_pair_updates_are_finite_and_diagonal(route: str, route_index: int) -> None:
    model = _model()
    trainer = API.V023HeterogeneousTrainer(model)
    before = _snapshot(model)
    batch = _pair_batch() if route == "C1" else _normalized_pair_batch()
    result = trainer.update_route(route, batch)

    assert result["route"] == route
    assert np.isfinite(float(result["loss"]))
    assert np.isfinite(float(result["pair_mse"]))
    assert np.isfinite(float(result["gauge_mse"]))
    assert _changed_routes(before, model) == {route_index}
    _assert_off_route_grads_are_empty(model, route_index)


def test_c3_structured_update_is_finite_and_diagonal() -> None:
    model = _model()
    trainer = API.V023HeterogeneousTrainer(model)
    before = _snapshot(model)
    surface = _surface()
    result = trainer.update_c3(_c3_batch(), [surface])

    assert result["route"] == "C3"
    assert np.isfinite(float(result["loss"]))
    assert _changed_routes(before, model) == {2}
    _assert_off_route_grads_are_empty(model, 2)


def test_malformed_action_shared_and_structured_batches_are_rejected() -> None:
    model = _model()
    trainer = API.V023HeterogeneousTrainer(model)
    with pytest.raises(TypeError, match="EEAxisPairBatch"):
        trainer.update_c1(_c3_batch())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="states must have shape"):
        trainer.update_c2(_normalized_pair_batch(bad_state_width=447))
    with pytest.raises(TypeError, match="LCSRSC3SampledBatch"):
        trainer.update_c3(_pair_batch(), [_surface()])  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="LCSRSAnchorSurface"):
        trainer.update_c3(_c3_batch(), [object()])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="outside S/R/C"):
        LCSRSC3SampledBatch(
            anchor_indices=np.asarray([0], dtype=np.int64),
            row_classes=np.asarray([99], dtype=np.uint8),
            user_indices=np.asarray([0], dtype=np.int64),
            action_indices=np.asarray([0], dtype=np.int64),
            normalized_targets=np.asarray([0.0], dtype=np.float32),
        )


def test_c3_requires_explicit_surfaces_and_pair_routes_reject_them() -> None:
    model = _model()
    trainer = API.V023HeterogeneousTrainer(model)
    with pytest.raises(API.V023HeterogeneousTrainerError, match="requires explicit"):
        trainer.update_route("C3", _c3_batch())
    with pytest.raises(API.V023HeterogeneousTrainerError, match="does not accept"):
        trainer.update_route("C1", _pair_batch(), surfaces=[_surface()])


def _resume_sequence(trainer: API.V023HeterogeneousTrainer, surface: LCSRSAnchorSurface) -> tuple[dict[str, object], ...]:
    return (
        trainer.update_c1(_pair_batch()),
        trainer.update_c2(_normalized_pair_batch()),
        trainer.update_c3(_c3_batch(), [surface]),
    )


def test_existing_three_route_checkpoint_and_resume_have_exact_parity() -> None:
    surface = _surface()
    uninterrupted_model = _model(seed=31)
    uninterrupted = API.V023HeterogeneousTrainer(uninterrupted_model)
    _resume_sequence(uninterrupted, surface)
    checkpoint = deepcopy(uninterrupted.checkpoint_state(update_count=3))

    expected_results = _resume_sequence(uninterrupted, surface)
    expected_state = _snapshot(uninterrupted_model)

    resumed_model = _model(seed=31)
    resumed = API.V023HeterogeneousTrainer(resumed_model)
    assert resumed.load_checkpoint_state(checkpoint) == 3
    actual_results = _resume_sequence(resumed, surface)

    assert actual_results == expected_results
    for expected_network, actual_network in zip(expected_state, resumed_model.q_networks, strict=True):
        for expected, actual in zip(expected_network, actual_network.parameters(), strict=True):
            torch.testing.assert_close(actual, expected, rtol=0.0, atol=0.0)

    restored_checkpoint = resumed.checkpoint_state(update_count=6)
    assert restored_checkpoint["algorithm"] == checkpoint["algorithm"]
    assert restored_checkpoint["format_version"] == checkpoint["format_version"]
