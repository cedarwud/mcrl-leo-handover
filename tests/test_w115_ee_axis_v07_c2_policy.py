"""W-115 -- V0.7 direct Q123 behavior and focal-only intervention."""

from __future__ import annotations

import numpy as np
import pytest
import torch
import torch.nn as nn

from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_v07_c2_policy import (
    behavior_decision,
    direct_three_surface_actions,
    focal_candidate_vector,
    motion_opportunity_user,
)
from mcrl.runtime.ee_axis_state import EE_AXIS_BASE_STATE_DIM
from mcrl.runtime.ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)


class _Q1(nn.Module):
    def forward(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        result = torch.zeros((states.shape[0], 28), dtype=states.dtype)
        result[:, 1] = 1.0
        return result


class _Q3(nn.Module):
    def forward(self, states: torch.Tensor) -> torch.Tensor:
        result = torch.zeros((states.shape[0], 28), dtype=states.dtype)
        result[:, 2] = 2.0
        return result


class _Hybrid:
    selected_q3_rung = 100
    initialization_seed = 123
    device = torch.device("cpu")

    def __init__(self) -> None:
        self._q1 = _Q1()
        self._q3 = _Q3()
        self.q_nets = (self._q1, object(), self._q3)

    @property
    def q1(self) -> nn.Module:
        return self._q1

    @property
    def q2(self) -> object:
        raise AssertionError("resident legacy Q2 must not be read")

    @property
    def q3(self) -> nn.Module:
        return self._q3

    def q_values_by_route(self, *args: object) -> object:
        raise AssertionError("three-route legacy inference must not be called")


class _FreshQ2:
    state_schema = V07_C2_Q2_STATE_SCHEMA
    state_schema_sha256 = V07_C2_Q2_STATE_SCHEMA_SHA256

    def __init__(self, *, corrupt_center: bool = False) -> None:
        self.calls = 0
        self.rows_seen: list[int] = []
        self.corrupt_center = corrupt_center

    def q2_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        self.calls += 1
        self.rows_seen.append(states.shape[0])
        assert np.all(np.any(masks, axis=1))
        result = np.zeros((states.shape[0], 28), dtype=np.float32)
        result[:, 1] = -2.5
        result[:, 2] = -2.5
        result[:, 5] = 5.0
        if self.corrupt_center:
            result[:, 5] = 6.0
        return result


def _inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    v03 = np.zeros((2, 8), dtype=np.float32)
    v04 = np.ones((2, 8), dtype=np.float32)
    q2 = np.full((2, 228), 2.0, dtype=np.float32)
    masks = np.zeros((2, 28), dtype=np.bool_)
    masks[0, [1, 2, 5]] = True
    return v03, v04, q2, masks


def test_bootstrap_and_refresh_use_one_direct_sum_and_one_native_mask_argmax() -> None:
    v03, v04, q2, masks = _inputs()
    bootstrap = behavior_decision(
        hybrid=_Hybrid(), fresh_q2=None,
        states_v03=v03, states_v04_c3=v04, states_v07_c2_q2=q2, masks=masks,
    )
    assert bootstrap.actions.tolist() == [2, -1]
    assert np.array_equal(bootstrap.q2, np.zeros((2, 28)))

    fresh = _FreshQ2()
    refresh = behavior_decision(
        hybrid=_Hybrid(), fresh_q2=fresh,
        states_v03=v03, states_v04_c3=v04, states_v07_c2_q2=q2, masks=masks,
    )
    assert fresh.calls == 1
    assert fresh.rows_seen == [1]
    assert refresh.actions.tolist() == [5, -1]
    assert np.array_equal(refresh.scores, refresh.q1 + refresh.q2 + refresh.q3)


def test_direct_composition_is_unweighted_and_ties_choose_first_legal_slot() -> None:
    zeros = np.zeros((1, 28), dtype=np.float64)
    mask = np.zeros((1, 28), dtype=np.bool_)
    mask[0, [3, 7]] = True
    actions, scores = direct_three_surface_actions(
        q1=zeros, q2=zeros, q3=zeros, masks=mask
    )
    assert actions.tolist() == [3]
    assert np.array_equal(scores, zeros)


def test_focal_candidate_changes_exactly_one_legal_action() -> None:
    reference = np.asarray([1, 2, -1], dtype=np.int64)
    masks = np.zeros((3, 28), dtype=np.bool_)
    masks[0, [1, 4]] = True
    masks[1, [2, 5]] = True
    candidate = focal_candidate_vector(
        reference_actions=reference,
        masks=masks,
        focal_user=1,
        candidate_action=5,
    )
    assert candidate.tolist() == [1, 5, -1]
    assert np.count_nonzero(candidate != reference) == 1
    with pytest.raises(MCRLContractError, match="illegal"):
        focal_candidate_vector(
            reference_actions=reference,
            masks=masks,
            focal_user=1,
            candidate_action=6,
        )


def test_refresh_fails_closed_if_q2_is_not_legal_set_centered() -> None:
    v03, v04, q2, masks = _inputs()
    with pytest.raises(MCRLContractError, match="centered"):
        behavior_decision(
            hybrid=_Hybrid(), fresh_q2=_FreshQ2(corrupt_center=True),
            states_v03=v03, states_v04_c3=v04,
            states_v07_c2_q2=q2, masks=masks,
        )


def test_refresh_rejects_missing_or_stale_q2_state_schema() -> None:
    v03, v04, q2, masks = _inputs()
    with pytest.raises(MCRLContractError, match="Q2 state"):
        behavior_decision(
            hybrid=_Hybrid(), fresh_q2=_FreshQ2(),
            states_v03=v03, states_v04_c3=v04,
            states_v07_c2_q2=q2[:, :-1], masks=masks,
        )

    stale = _FreshQ2()
    stale.state_schema = "stale"
    with pytest.raises(MCRLContractError, match="schema"):
        behavior_decision(
            hybrid=_Hybrid(), fresh_q2=stale,
            states_v03=v03, states_v04_c3=v04,
            states_v07_c2_q2=q2, masks=masks,
        )


def test_focal_candidate_rejects_any_invalid_reference_action() -> None:
    reference = np.asarray([1, 99, -1], dtype=np.int64)
    masks = np.zeros((3, 28), dtype=np.bool_)
    masks[0, [1, 4]] = True
    masks[1, [2, 5]] = True
    with pytest.raises(MCRLContractError, match="reference action"):
        focal_candidate_vector(
            reference_actions=reference,
            masks=masks,
            focal_user=0,
            candidate_action=4,
        )


def test_motion_scoped_q2_evaluates_only_the_greatest_opportunity_user() -> None:
    v03 = np.zeros((3, 8), dtype=np.float32)
    v04 = np.ones((3, 8), dtype=np.float32)
    q2 = np.zeros((3, 228), dtype=np.float32)
    masks = np.zeros((3, 28), dtype=np.bool_)
    masks[0, [1, 2, 5]] = True
    masks[1, [1, 2, 5]] = True
    radial_start = EE_AXIS_BASE_STATE_DIM + 28
    q2[0, radial_start + np.asarray([1, 2, 5])] = [-1.0, 0.0, 1.0]
    q2[1, radial_start + np.asarray([1, 2, 5])] = [-3.0, 0.0, 1.0]

    fresh = _FreshQ2()
    decision = behavior_decision(
        hybrid=_Hybrid(),
        fresh_q2=fresh,
        states_v03=v03,
        states_v04_c3=v04,
        states_v07_c2_q2=q2,
        masks=masks,
        q2_user_scope="motion-one",
    )

    assert fresh.rows_seen == [1]
    assert decision.actions.tolist() == [2, 5, -1]
    assert np.array_equal(decision.q2[0], np.zeros(28))
    assert np.count_nonzero(decision.q2[1]) == 3
    assert motion_opportunity_user(
        states_v07_c2_q2=q2,
        masks=masks,
        reference_actions=np.asarray([2, 2, -1], dtype=np.int64),
    ) == 1
