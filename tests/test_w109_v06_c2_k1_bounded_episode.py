"""W-109 -- bounded DESIGN-EVAL arm semantics without physical artifacts."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import torch


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/c3-v04/run_v06_c2_k1_bounded_learner.py"
)
SPEC = importlib.util.spec_from_file_location(
    "v06_c2_k1_bounded_runner_w109", RUNNER
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


class _Observation:
    def __init__(self) -> None:
        self.masks = np.ones((100, 28), dtype=np.bool_)


class _Environment:
    driver = type(
        "Driver",
        (),
        {"config": type("Config", (), {"ephemeris": type("E", (), {"time_step_s": 1.0})()})()},
    )()


class _Wrapped:
    def __init__(self) -> None:
        self.environment = _Environment()
        self.observation = _Observation()
        self.last_outcome = None
        self.steps = 0
        self.actions: list[np.ndarray] = []

    def reset(self, *_args: object) -> tuple[None, None, _Observation]:
        return None, None, self.observation

    def step(self, actions: np.ndarray, _rng: np.random.Generator) -> object:
        self.actions.append(np.asarray(actions, dtype=np.int64).copy())
        self.steps += 1
        self.observation = _Observation()
        self.last_outcome = type(
            "Outcome",
            (),
            {
                "link_rate_bps": np.ones(100, dtype=np.float64),
                "system_power_w": 10.0,
                "resolution": type("Resolution", (), {"served_count": 100})(),
                "observation": self.observation,
            },
        )()
        return type("Result", (), {"done": self.steps == 10})()


class _Runtime:
    archive = object()

    def __init__(self) -> None:
        self.last: _Wrapped | None = None

    def make_environment(self, _archive: object, *, users: int) -> _Wrapped:
        assert users == 100
        self.last = _Wrapped()
        return self.last

    def bind_field(self, _wrapped: _Wrapped, _field: object) -> None:
        return None

    def evaluation_rngs(self, seed: int) -> tuple[np.random.Generator, ...]:
        return (np.random.default_rng(seed), np.random.default_rng(seed + 1))


class _Trainer:
    lineage = "q13-a"

    def __init__(self) -> None:
        self.q2_calls = 0

    def q2_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray:
        assert states.shape == (100, 228)
        assert masks.shape == (100, 28)
        self.q2_calls += 1
        result = np.full((100, 28), 0.1, dtype=np.float64)
        result[:, 1] = 2.0
        return result


def test_q13_immutability_snapshot_never_reads_or_copies_resident_q2() -> None:
    class Route:
        def __init__(self, value: float) -> None:
            self.weight = torch.tensor([value], dtype=torch.float32)

        def state_dict(self) -> dict[str, torch.Tensor]:
            return {"weight": self.weight}

    class ForbiddenQ2:
        def state_dict(self) -> dict[str, torch.Tensor]:
            raise AssertionError("resident legacy Q2 was read or copied")

    hybrid = type(
        "Hybrid",
        (),
        {"q1": Route(1.0), "q2": ForbiddenQ2(), "q3": Route(3.0)},
    )()

    before = runner._snapshot_q13_networks(hybrid)

    assert set(before) == {"q1", "q3"}
    assert runner._same_q13_networks(hybrid, before) is True
    hybrid.q1.weight += 1.0
    assert runner._same_q13_networks(hybrid, before) is False


def _patch_views(monkeypatch: object) -> None:
    encoded = type(
        "Encoded", (), {"state_matrix": np.zeros((100, 228), dtype=np.float32)}
    )()
    monkeypatch.setattr(runner, "encode_ee_axis_state", lambda *_args: encoded)
    monkeypatch.setattr(runner, "encode_ee_axis_v04_c3_state", lambda *_args, **_kwargs: encoded)

    def q13(*_args: object) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        # Keep the median magnitude nonzero.  This catches a DROP_C2 bug where
        # an empty q2 sample was divided by a valid Q1+Q3 median and became NaN.
        q1 = np.full((100, 28), 0.5, dtype=np.float64)
        q1[:, 0] = 1.0
        return q1, np.zeros_like(q1), np.ones((100, 28), dtype=np.bool_)

    monkeypatch.setattr(runner, "q13_surfaces_without_q2", q13)
    monkeypatch.setattr(
        runner,
        "_design_field",
        lambda *_args, **_kwargs: type("Field", (), {"root_digest": "f" * 64})(),
    )


def test_drop_c2_never_calls_fresh_q2_and_full_calls_it_once_per_step(
    monkeypatch: object,
) -> None:
    _patch_views(monkeypatch)
    prepare = {"formula_contract": {"kappa_bits": 1.0}}

    drop_runtime = _Runtime()
    drop_trainer = _Trainer()
    drop = runner._episode(
        live=object(),
        runtime=drop_runtime,
        hybrid=object(),
        trainer=drop_trainer,
        prepare=prepare,
        evaluation_seed=7,
        arm="DROP_C2",
    )
    assert drop_trainer.q2_calls == 0
    assert all(np.array_equal(actions, np.zeros(100)) for actions in drop_runtime.last.actions)
    assert drop["q2_surface_median_abs"] == 0.0
    assert drop["q13_surface_median_abs"] == 0.5
    assert drop["q2_to_q13_magnitude"] == 0.0

    full_runtime = _Runtime()
    full_trainer = _Trainer()
    full = runner._episode(
        live=object(),
        runtime=full_runtime,
        hybrid=object(),
        trainer=full_trainer,
        prepare=prepare,
        evaluation_seed=7,
        arm="FULL",
    )
    assert full_trainer.q2_calls == 10
    assert all(np.array_equal(actions, np.ones(100)) for actions in full_runtime.last.actions)
    assert full["q2_surface_median_abs"] > 0.0
