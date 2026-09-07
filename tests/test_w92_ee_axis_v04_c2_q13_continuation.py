"""W-92 -- frozen DROP-C2 continuation inference for the C2 census."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import mcrl.runtime.ee_axis_v04_c2_q13_continuation as continuation
from mcrl.runtime.ee_axis_v04_c2_q13_continuation import (
    Q13ContinuationContractError,
    select_frozen_q13_continuation,
)


class _Network:
    def __init__(self, *, training: bool = False) -> None:
        self.training = training


class _Trainer:
    initialization_seed = 2026092101
    selected_q3_rung = 100

    def __init__(self) -> None:
        self.q_nets = [_Network(), _Network(), _Network()]
        self.calls = 0

    def q_values_by_route(self, legacy, c3, masks):
        self.calls += 1
        q1 = np.zeros((1, 28), dtype=np.float32)
        q1[0, 1] = 100.0
        q1[0, 2] = 3.0
        q1[0, 3] = 1.0
        # Q2 is deliberately dominant and must be ignored by DROP-C2.
        q2 = np.zeros((1, 28), dtype=np.float32)
        q2[0, 3] = 1000.0
        q3 = np.zeros((1, 28), dtype=np.float32)
        q3[0, 2] = 4.0
        return q1, q2, q3


def _encoded(state, mask):
    return SimpleNamespace(state_matrix=state, action_masks=mask)


def test_q13_uses_one_common_mask_and_ignores_q2(monkeypatch) -> None:
    state = np.zeros((1, 228), dtype=np.float32)
    mask = np.ones((1, 28), dtype=np.bool_)
    mask[0, 1] = False
    monkeypatch.setattr(
        continuation,
        "encode_ee_axis_state",
        lambda environment, observation: _encoded(state, mask),
    )
    monkeypatch.setattr(
        continuation,
        "encode_ee_axis_v04_c3_state",
        lambda environment, observation, **kwargs: _encoded(state + 1.0, mask),
    )
    trainer = _Trainer()
    decision = select_frozen_q13_continuation(
        trainer,
        SimpleNamespace(environment=object()),
        object(),
        interval_s=30.08,
        kappa_bits=10.0,
    )
    assert decision.actions == (2,)
    assert trainer.calls == 1
    assert len(decision.decision_sha256) == 64


def test_q13_fails_closed_on_mask_disagreement(monkeypatch) -> None:
    state = np.zeros((1, 228), dtype=np.float32)
    first = np.ones((1, 28), dtype=np.bool_)
    second = np.array(first, copy=True)
    second[0, 2] = False
    monkeypatch.setattr(
        continuation,
        "encode_ee_axis_state",
        lambda environment, observation: _encoded(state, first),
    )
    monkeypatch.setattr(
        continuation,
        "encode_ee_axis_v04_c3_state",
        lambda environment, observation, **kwargs: _encoded(state, second),
    )
    with pytest.raises(Q13ContinuationContractError, match="masks disagree"):
        select_frozen_q13_continuation(
            _Trainer(),
            SimpleNamespace(environment=object()),
            object(),
            interval_s=30.08,
            kappa_bits=10.0,
        )


def test_q13_requires_exact_three_eval_networks_and_rung() -> None:
    trainer = _Trainer()
    trainer.q_nets[1].training = True
    with pytest.raises(Q13ContinuationContractError, match="evaluation mode"):
        select_frozen_q13_continuation(
            trainer,
            SimpleNamespace(environment=object()),
            object(),
            interval_s=30.08,
            kappa_bits=10.0,
        )
    trainer.q_nets[1].training = False
    trainer.selected_q3_rung = 99
    with pytest.raises(Q13ContinuationContractError, match="rung 100"):
        select_frozen_q13_continuation(
            trainer,
            SimpleNamespace(environment=object()),
            object(),
            interval_s=30.08,
            kappa_bits=10.0,
        )
