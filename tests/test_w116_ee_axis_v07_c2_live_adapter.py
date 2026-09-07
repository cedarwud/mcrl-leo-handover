"""W-116 -- V0.7 matched focal-next live-adapter mechanics."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM
from mcrl.runtime.ee_axis_v07_c2_policy import V07C2BehaviorDecision


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / ".scratch" / "c3-v04" / "v07_c2_focal_next_live_adapter.py"
SPEC = importlib.util.spec_from_file_location("v07_c2_live_adapter", LIVE)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class _Observation:
    def __init__(self, step: int) -> None:
        self.step_index = step
        self.masks = np.zeros((2, NUM_ACTIONS), dtype=np.bool_)
        self.masks[0, [0, 2, 5]] = True
        self.masks[1, [1, 3]] = True


class _Evaluation:
    def __init__(self, rates: np.ndarray, power: float) -> None:
        self.link_rate_bps = rates
        self.system_power_w = power


class _Wrapped:
    def __init__(self, runtime: "_Runtime") -> None:
        self.runtime = runtime
        self.environment = self
        self.opening: np.ndarray | None = None
        self.last_outcome = type("Outcome", (), {"observation": _Observation(0)})()

    def reset(self, _env_rng: object, _mobility_rng: object):
        self.opening = None
        observation = _Observation(0)
        self.last_outcome = type("Outcome", (), {"observation": observation})()
        return [], [], observation

    def step(self, actions: np.ndarray, _rng: object):
        self.opening = np.asarray(actions, dtype=np.int64).copy()
        observation = _Observation(1)
        self.last_outcome = type("Outcome", (), {"observation": observation})()
        self.runtime.openings.append(self.opening.tolist())
        return type("Result", (), {"done": self.runtime.terminal})()

    def evaluate_actions(self, actions: np.ndarray, _rng: object) -> _Evaluation:
        assert self.opening is not None
        selected = np.asarray(actions, dtype=np.int64)
        self.runtime.full_calls.append(selected.tolist())
        focal_rate = 20.0 * float(self.opening[0]) + float(selected[0]) + 10.0
        rates = np.asarray([focal_rate, 7.0], dtype=np.float64)
        power = 50.0 + 2.0 * float(self.opening[0]) + float(np.sum(selected))
        return _Evaluation(rates, power)

    def evaluate_actions_without_user(
        self, actions: np.ndarray, _rng: object, *, focal_user: int
    ) -> _Evaluation:
        assert self.opening is not None and focal_user == 0
        selected = np.asarray(actions, dtype=np.int64)
        self.runtime.removed_calls.append(selected.tolist())
        # Other users stay fixed; only focal rate/power are removed.
        rates = np.asarray([0.0, 7.0], dtype=np.float64)
        power = 45.0 + float(selected[1])
        return _Evaluation(rates, power)


class _Runtime:
    users = 2

    def __init__(self, *, terminal: bool = False) -> None:
        self.terminal = terminal
        self.openings: list[list[int]] = []
        self.full_calls: list[list[int]] = []
        self.removed_calls: list[list[int]] = []

    def make_environment(self, _archive: object, *, users: int) -> _Wrapped:
        assert users == self.users
        return _Wrapped(self)

    def bind_field(self, _wrapped: _Wrapped, _field: KeyedFadingField) -> None:
        return None

    def evaluation_rngs(self, seed: int):
        return (np.random.default_rng(seed), np.random.default_rng(seed + 1))


def _decision_for(wrapped: _Wrapped, observation: _Observation) -> tuple[V07C2BehaviorDecision, np.ndarray]:
    masks = np.asarray(observation.masks, dtype=np.bool_)
    q1 = np.zeros((2, NUM_ACTIONS), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q3 = np.zeros_like(q1)
    if observation.step_index == 0:
        actions = np.asarray([2, 1], dtype=np.int64)
    else:
        assert wrapped.opening is not None
        actions = np.asarray([int(wrapped.opening[0] + 1), 1], dtype=np.int64)
        # Keep this synthetic successor legal for every opening in {0,2,5}.
        actions[0] = {0: 2, 2: 5, 5: 0}[int(wrapped.opening[0])]
    scores = q1 + q2 + q3
    state = np.zeros((2, EE_AXIS_STATE_DIM), dtype=np.float32)
    state[:, 0] = float(observation.step_index)
    return (
        V07C2BehaviorDecision(
            actions=actions,
            q1=q1,
            q2=q2,
            q3=q3,
            scores=scores,
            masks=masks,
        ),
        state,
    )


def _capture(monkeypatch, runtime: _Runtime, *, focal: int = 0):
    def fake_decision(_hybrid, _fresh_q2, wrapped, observation, **_kwargs):
        return _decision_for(wrapped, observation)

    monkeypatch.setattr(mod, "_decision", fake_decision)
    field = KeyedFadingField.from_components("test-v07", "a" * 64, 7)
    return mod.capture_one_decision(
        runtime,
        object(),
        object(),
        None,
        lineage="q13-a",
        refresh_round="bootstrap",
        world_id=7,
        source_seed=7,
        target_step=0,
        focal_user=focal,
        history=[np.asarray([2, 1], dtype=np.int64)],
        field=field,
        interval_s=1.0,
        kappa_bits=100.0,
        lambda_bits_per_j=2.0,
    )


def test_all_native_actions_use_focal_only_opening_and_branch_local_successor(monkeypatch) -> None:
    runtime = _Runtime()
    capture = _capture(monkeypatch, runtime)

    assert capture.coverage.legal_actions == (0, 2, 5)
    assert [row.candidate_action for row in capture.rows] == [0, 2, 5]
    assert [entry[0] for entry in runtime.openings] == [2, 0, 5]
    assert all(entry[1] == 1 for entry in runtime.openings)
    # Reference opening 2 is measured once and reused; each other branch gets
    # its own successor decision (2->5, 0->2, 5->0).
    assert [entry[0] for entry in runtime.full_calls] == [5, 2, 0]
    assert runtime.removed_calls == runtime.full_calls
    reference = next(row for row in capture.rows if row.candidate_action == 2)
    assert reference.z2_focal_next_surplus_bits == 0.0
    assert any(row.z2_focal_next_surplus_bits < 0.0 for row in capture.rows)
    assert any(row.z2_focal_next_surplus_bits > 0.0 for row in capture.rows)
    assert all(
        item["opening_focal_difference_count"] in {0, 1}
        for item in capture.receipt["branch_rows"]
    )
    assert capture.verify() == capture.receipt["receipt_sha256"]


def test_terminal_anchor_emits_explicit_absorbing_zero_rows(monkeypatch) -> None:
    runtime = _Runtime(terminal=True)
    capture = _capture(monkeypatch, runtime)

    assert len(capture.rows) == 3
    assert all(row.z2_focal_next_surplus_bits == 0.0 for row in capture.rows)
    assert runtime.full_calls == []
    assert runtime.removed_calls == []
    assert all(
        item["candidate"]["terminal_absorbing_zero"] is True
        for item in capture.receipt["branch_rows"]
    )


def test_empty_focal_mask_is_coverage_only_and_runs_no_branch(monkeypatch) -> None:
    runtime = _Runtime()

    def empty_decision(_hybrid, _fresh_q2, _wrapped, observation, **_kwargs):
        masks = np.asarray(observation.masks, dtype=np.bool_).copy()
        masks[0] = False
        zeros = np.zeros((2, NUM_ACTIONS), dtype=np.float64)
        state = np.zeros((2, EE_AXIS_STATE_DIM), dtype=np.float32)
        return (
            V07C2BehaviorDecision(
                actions=np.asarray([-1, 1], dtype=np.int64),
                q1=zeros,
                q2=zeros,
                q3=zeros,
                scores=zeros,
                masks=masks,
            ),
            state,
        )

    monkeypatch.setattr(mod, "_decision", empty_decision)
    field = KeyedFadingField.from_components("test-v07-empty", "a" * 64, 7)
    capture = mod.capture_one_decision(
        runtime,
        object(),
        object(),
        None,
        lineage="q13-a",
        refresh_round="bootstrap",
        world_id=7,
        source_seed=7,
        target_step=0,
        focal_user=0,
        history=[np.asarray([-1, 1], dtype=np.int64)],
        field=field,
        interval_s=1.0,
        kappa_bits=100.0,
        lambda_bits_per_j=2.0,
    )
    assert capture.coverage.mask_count == 0
    assert capture.rows == ()
    assert runtime.openings == []
    assert capture.receipt["empty_mask"] is True
    capture.verify()


def test_carrier_prefix_is_preserved_but_unexecuted_anchor_action_is_rebound(monkeypatch) -> None:
    runtime = _Runtime()

    def fake_decision(_hybrid, _fresh_q2, wrapped, observation, **_kwargs):
        return _decision_for(wrapped, observation)

    monkeypatch.setattr(mod, "_decision", fake_decision)
    field = KeyedFadingField.from_components("test-v07-carrier", "a" * 64, 8)
    carrier = (
        np.asarray([0, 1], dtype=np.int64),
        np.asarray([3, 3], dtype=np.int64),
    )
    bound, decision, state = mod.bind_behavior_action_at_anchor(
        runtime,
        object(),
        object(),
        None,
        source_seed=8,
        field=field,
        carrier_history=carrier,
        target_step=1,
        interval_s=1.0,
        kappa_bits=100.0,
    )
    assert np.array_equal(bound[0], carrier[0])
    assert not np.array_equal(bound[1], carrier[1])
    assert np.array_equal(bound[1], decision.actions)
    assert state.shape == (2, EE_AXIS_STATE_DIM)


def test_adapter_source_forbids_legacy_three_route_or_outcome_selection_symbols() -> None:
    source = LIVE.read_text(encoding="utf-8")
    assert "q_values_by_route" not in source
    assert "oracle_and_drop_scores" not in source
    assert "main_actions(" not in source
    assert '"target_or_ee_selected": False' in source
