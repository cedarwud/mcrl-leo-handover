"""W-108 -- the V0.6 Q1+Q3 seam never evaluates resident legacy Q2."""

from __future__ import annotations

import numpy as np
import pytest
import torch
import torch.nn as nn

from mcrl.runtime.ee_axis_v06_c2_k1_q13 import (
    C2K1Q13Error,
    q13_surfaces_without_q2,
)


class _Q1(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[int] = []

    def forward(self, states: torch.Tensor, masks: torch.Tensor) -> torch.Tensor:
        self.rows.append(int(states.shape[0]))
        assert torch.all(torch.any(masks, dim=1))
        return torch.ones((states.shape[0], 28), dtype=torch.float32)


class _ForbiddenQ2(nn.Module):
    def forward(self, *_args: object, **_kwargs: object) -> torch.Tensor:
        raise AssertionError("resident legacy Q2 was evaluated")


class _Q3(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[int] = []

    def forward(self, states: torch.Tensor) -> torch.Tensor:
        self.rows.append(int(states.shape[0]))
        return torch.full((states.shape[0], 28), 3.0, dtype=torch.float32)


class _Hybrid:
    initialization_seed = 2026092101
    selected_q3_rung = 100
    device = torch.device("cpu")

    def __init__(self) -> None:
        self.q1 = _Q1()
        self.q2 = _ForbiddenQ2()
        self.q3 = _Q3()
        self.q_nets = (self.q1, self.q2, self.q3)


def test_only_eligible_rows_reach_q1_q3_and_q2_is_never_called() -> None:
    hybrid = _Hybrid()
    states = np.zeros((3, 228), dtype=np.float32)
    masks = np.asarray(
        [[True] * 28, [False] * 28, [False, True] + [False] * 26],
        dtype=np.bool_,
    )

    q1, q3, returned_masks = q13_surfaces_without_q2(
        hybrid, states, states, masks
    )

    assert hybrid.q1.rows == [2]
    assert hybrid.q3.rows == [2]
    assert np.array_equal(returned_masks, masks)
    assert np.array_equal(q1[1], np.zeros(28))
    assert np.array_equal(q3[1], np.zeros(28))
    assert np.array_equal(q1[[0, 2]], np.ones((2, 28)))
    assert np.array_equal(q3[[0, 2]], np.full((2, 28), 3.0))


def test_all_empty_masks_return_noop_surfaces_without_any_network_forward() -> None:
    hybrid = _Hybrid()
    states = np.zeros((2, 228), dtype=np.float32)
    masks = np.zeros((2, 28), dtype=np.bool_)

    q1, q3, _ = q13_surfaces_without_q2(hybrid, states, states, masks)

    assert hybrid.q1.rows == []
    assert hybrid.q3.rows == []
    assert np.array_equal(q1, np.zeros((2, 28)))
    assert np.array_equal(q3, np.zeros((2, 28)))


def test_malformed_route_inputs_fail_closed() -> None:
    hybrid = _Hybrid()
    states = np.zeros((1, 228), dtype=np.float32)
    with pytest.raises(C2K1Q13Error, match="malformed"):
        q13_surfaces_without_q2(
            hybrid,
            states,
            states,
            np.ones((1, 27), dtype=np.bool_),
        )

