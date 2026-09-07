"""Fast actual-class checks for the isolated V0.23 five-arm learner seam."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRSThreeRouteConfig
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_REFERENCE,
    LCSRSAnchorSurface,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_five_arm_learner_orchestrator_under_test",
    HERE / "v023_five_arm_learner_orchestrator.py",
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


def _pair_batch(target: float) -> EEAxisPairBatch:
    rows = 4
    states = np.zeros((rows, 228), dtype=np.float32)
    states[:, 0] = np.asarray([0.1, -0.2, 0.3, -0.4], dtype=np.float32)
    states[:, 1] = np.asarray([0.5, 0.2, -0.1, 0.4], dtype=np.float32)
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray([0, 0, 1, 2], dtype=np.int64),
        candidate_actions=np.asarray([1, 2, 2, 3], dtype=np.int64),
        target_surplus_bits=np.asarray(
            [target, target + 1.0, target - 1.0, target + 0.5],
            dtype=np.float64,
        ),
        action_masks=np.ones((rows, 28), dtype=np.bool_),
    )


def _surface(target: float) -> LCSRSAnchorSurface:
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
    draws = np.tile(
        np.asarray([[target, -target]], dtype=np.float64), (LCSRS_DRAW_COUNT, 1)
    )
    pair = LCSRSPairTargets(
        pair_id=f"p-{target}",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    return assemble_lcsrs_anchor_surface(view, (pair,))


def _c3_batch() -> LCSRSC3SampledBatch:
    return LCSRSC3SampledBatch(
        anchor_indices=np.zeros(3, dtype=np.int64),
        row_classes=np.asarray([3, 3, LCSRS_ROW_REFERENCE], dtype=np.uint8),
        user_indices=np.asarray([0, 1, 2], dtype=np.int64),
        action_indices=np.asarray([1, 1, 0], dtype=np.int64),
        normalized_targets=np.asarray([1.0, -1.0, 0.0], dtype=np.float32),
    )


class _DeterministicProvider:
    """Test-only in-memory typed provider; it creates no target artifact."""

    def __init__(self, batches: dict[tuple[str, str], list[Any]]) -> None:
        self._batches = batches
        self._positions = {key: 0 for key in batches}

    def next_batch(self, *, route: str, source: str, update_cursor: int):
        key = (route, source)
        position = self._positions[key]
        batch = self._batches[key][position]
        self._positions[key] = position + 1
        return batch

    def sampler_state(self) -> dict[str, Any]:
        return {"positions": deepcopy(self._positions)}

    def load_sampler_state(self, state: dict[str, Any]) -> None:
        self._positions = deepcopy(state["positions"])


def _provided_pair(route: str, source: str, serial: int, target: float):
    return API.ProvidedRouteBatch(
        route=route,
        source=source,
        file_id=f"{route.lower()}-{source}-fixture-{serial}",
        batch=_pair_batch(target),
    )


def _provided_c3(source: str, serial: int, target: float):
    return API.ProvidedRouteBatch(
        route="C3",
        source=source,
        file_id=f"c3-{source}-fixture-{serial}",
        batch=_c3_batch(),
        c3_surfaces=(_surface(target),),
    )


def _provider(*, c1_second_distinct: bool, rounds_per_route: int = 3):
    batches: dict[tuple[str, str], list[Any]] = {}
    for source in API.SOURCE_ORDER:
        c1_targets = [2.0] * rounds_per_route
        if c1_second_distinct and rounds_per_route > 1:
            c1_targets[1] = -4.0 if source == "neutral" else 7.0
        batches[("C1", source)] = [
            _provided_pair("C1", source, index, target)
            for index, target in enumerate(c1_targets)
        ]
        batches[("C2", source)] = [
            _provided_pair("C2", source, index, 3.0)
            for index in range(rounds_per_route)
        ]
        batches[("C3", source)] = [
            _provided_c3(source, index, 1.0)
            for index in range(rounds_per_route)
        ]
    return _DeterministicProvider(batches)


def _orchestrator(provider: _DeterministicProvider, *, cadence: int = 100):
    return API.V023FiveArmLearnerOrchestrator(
        API.V023FiveArmOrchestratorConfig(
            model_config=_config(),
            train_seed=41,
            checkpoint_cadence_updates=cadence,
        ),
        provider,
    )


def _network_state(model) -> tuple[tuple[torch.Tensor, ...], ...]:
    return tuple(
        tuple(parameter.detach().clone() for parameter in network.parameters())
        for network in model.q_networks
    )


def _states_identical(left, right) -> bool:
    return all(
        torch.equal(left_tensor, right_tensor)
        for left_network, right_network in zip(left, right, strict=True)
        for left_tensor, right_tensor in zip(left_network, right_network, strict=True)
    )


def _assert_tree_identical(left: Any, right: Any) -> None:
    assert type(left) is type(right)
    if isinstance(left, torch.Tensor):
        assert torch.equal(left, right)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            _assert_tree_identical(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for first, second in zip(left, right, strict=True):
            _assert_tree_identical(first, second)
    else:
        assert left == right


def test_common_initialization_bytes_give_identical_tensors_without_shared_storage():
    orchestrator = _orchestrator(_provider(c1_second_distinct=False))
    assert orchestrator.config.checkpoint_cadence_updates == 100
    formal = API.V023FiveArmOrchestratorConfig.formal(
        model_config=_config(), train_seed=41
    )
    assert formal.formal_use is True
    assert API.FORMAL_CHECKPOINT_CADENCE_EPOCHS == 100
    assert API.UPDATES_PER_SOURCE_TRAINING_EPOCH == 3
    assert formal.checkpoint_cadence_updates == API.FORMAL_CHECKPOINT_CADENCE_UPDATES == 300

    reference = orchestrator.models[API.ARMS[0]]
    for arm in API.ARMS[1:]:
        current = orchestrator.models[arm]
        assert _states_identical(_network_state(reference), _network_state(current))
        for reference_network, current_network in zip(
            reference.q_networks, current.q_networks, strict=True
        ):
            for left, right in zip(
                reference_network.parameters(), current_network.parameters(), strict=True
            ):
                assert left.untyped_storage().data_ptr() != right.untyped_storage().data_ptr()


def test_closed_mapping_and_each_route_round_changes_only_the_expected_head():
    orchestrator = _orchestrator(_provider(c1_second_distinct=False))
    for route_index, route in enumerate(API.ROUTE_ORDER):
        before = {
            arm: _network_state(model) for arm, model in orchestrator.models.items()
        }
        receipt = orchestrator.advance()

        assert receipt.route == route
        assert receipt.claim_ceiling == API.IMPLEMENTATION_ONLY_CLAIM
        assert [(item.arm, item.source) for item in receipt.arm_updates] == [
            (arm, API.SOURCE_ABLATION_MAP[arm][route]) for arm in API.ARMS
        ]
        assert all(
            item.claim_ceiling == API.IMPLEMENTATION_ONLY_CLAIM
            for item in receipt.arm_updates
        )
        assert receipt.source_files == (
            ("neutral", f"{route.lower()}-neutral-fixture-0"),
            ("informed", f"{route.lower()}-informed-fixture-0"),
        )
        for arm, model in orchestrator.models.items():
            after = _network_state(model)
            assert not all(
                torch.equal(old, new)
                for old, new in zip(
                    before[arm][route_index], after[route_index], strict=True
                )
            )
            for untouched_index in set(range(3)) - {route_index}:
                for old, new in zip(
                    before[arm][untouched_index],
                    after[untouched_index],
                    strict=True,
                ):
                    assert torch.equal(old, new)


def test_source_arms_stay_identical_until_their_source_batch_differs():
    orchestrator = _orchestrator(_provider(c1_second_distinct=True))

    # First C1, C2, and C3 calls use equal typed data for both source labels.
    orchestrator.advance_many(3)
    common_state = _network_state(orchestrator.models[API.ARMS[0]])
    for arm in API.ARMS[1:]:
        assert _states_identical(common_state, _network_state(orchestrator.models[arm]))

    # The next scheduled C1 request is the first with source-distinct payloads.
    receipt = orchestrator.advance()
    assert receipt.route == "C1"
    neutral = _network_state(orchestrator.models[API.ARMS[0]])
    informed = _network_state(orchestrator.models["FULL"])
    assert not _states_identical(neutral, informed)
    for arm in ("DROP_C1",):
        assert _states_identical(neutral, _network_state(orchestrator.models[arm]))
    for arm in ("DROP_C2", "DROP_C3"):
        assert _states_identical(informed, _network_state(orchestrator.models[arm]))


def test_checkpoint_resume_is_bit_identical_and_restores_provider_file_cursor():
    uninterrupted = _orchestrator(_provider(c1_second_distinct=True), cadence=2)
    uninterrupted.advance_many(6)
    expected = uninterrupted.checkpoint_state()

    split_provider = _provider(c1_second_distinct=True)
    split = _orchestrator(split_provider, cadence=2)
    split.advance_many(4)
    checkpoint = split.checkpoint_state()
    assert checkpoint["update_cursor"] == 4
    assert checkpoint["next_route_index"] == 1
    assert len(checkpoint["file_order"]) == 4
    assert set(checkpoint["arms"]) == set(API.ARMS)
    for state in checkpoint["arms"].values():
        assert len(state["q_networks"]) == len(state["optimizers"]) == 3

    resumed_provider = _provider(c1_second_distinct=True)
    resumed = _orchestrator(resumed_provider, cadence=2)
    resumed.load_checkpoint_state(checkpoint)
    assert resumed.update_cursor == 4
    assert resumed.next_route == "C2"
    assert resumed_provider.sampler_state() == checkpoint["provider_sampler_state"]
    resumed.advance_many(2)

    actual = resumed.checkpoint_state()
    _assert_tree_identical(expected, actual)
    assert actual["file_order"] == expected["file_order"]


def test_checkpoint_cadence_counts_complete_source_training_epochs_not_routes():
    orchestrator = _orchestrator(
        _provider(c1_second_distinct=False), cadence=3
    )
    assert orchestrator.completed_source_training_epochs == 0
    assert orchestrator.checkpoint_due() is False

    orchestrator.advance_many(2)
    assert orchestrator.next_route == "C3"
    assert orchestrator.completed_source_training_epochs == 0
    assert orchestrator.checkpoint_due() is False

    orchestrator.advance()
    assert orchestrator.next_route == "C1"
    assert orchestrator.completed_source_training_epochs == 1
    assert orchestrator.checkpoint_due() is True

    checkpoint = orchestrator.checkpoint_state()
    assert checkpoint["formal_checkpoint_cadence_epochs"] == 100
    assert checkpoint["formal_checkpoint_cadence_updates"] == 300
    assert checkpoint["updates_per_source_training_epoch"] == 3
    assert checkpoint["completed_source_training_epochs"] == 1
