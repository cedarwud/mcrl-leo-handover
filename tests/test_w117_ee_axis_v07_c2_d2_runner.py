"""W-117 -- V0.7 D2 development-calibration runner boundaries."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".scratch" / "c3-v04" / "run_v07_c2_d2.py"
SPEC = importlib.util.spec_from_file_location("v07_c2_d2_runner", RUNNER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class _Observation:
    def __init__(self, step: int, masks: np.ndarray) -> None:
        self.step_index = step
        self.masks = masks


class _Wrapped:
    def __init__(self, masks_by_step: list[np.ndarray]) -> None:
        self.masks_by_step = masks_by_step
        self.step_index = 0
        self.last_outcome = type(
            "Outcome", (), {"observation": _Observation(0, masks_by_step[0])}
        )()

    def reset(self, _env_rng: object, _mobility_rng: object):
        self.step_index = 0
        observation = _Observation(0, self.masks_by_step[0])
        self.last_outcome = type("Outcome", (), {"observation": observation})()
        return [], [], observation

    def step(self, _actions: np.ndarray, _rng: object):
        self.step_index += 1
        observation = _Observation(
            self.step_index, self.masks_by_step[self.step_index]
        )
        self.last_outcome = type("Outcome", (), {"observation": observation})()
        return type(
            "Result",
            (),
            {"done": False, "user_states": [], "action_masks": []},
        )()


class _Runtime:
    users = 3
    archive = object()
    trainer = object()

    def __init__(self, masks_by_step: list[np.ndarray]) -> None:
        self.wrapped = _Wrapped(masks_by_step)
        self.main_calls = 0

    def make_environment(self, _archive: object, *, users: int) -> _Wrapped:
        assert users == self.users
        return self.wrapped

    def bind_field(self, _wrapped: _Wrapped, _field: object) -> None:
        return None

    def evaluation_rngs(self, seed: int):
        return (np.random.default_rng(seed), np.random.default_rng(seed + 1))

    def main_actions(self, *_args: object) -> np.ndarray:
        self.main_calls += 1
        return np.asarray([1, 2, 3], dtype=np.int64)


def _masks(*counts: int) -> np.ndarray:
    value = np.zeros((len(counts), 28), dtype=np.bool_)
    for user, count in enumerate(counts):
        value[user, :count] = True
    return value


def test_calibration_seed_is_disjoint_and_command_cannot_adjudicate_d2() -> None:
    assert mod.CALIBRATION_SEED not in mod.D2_SEEDS
    assert mod.D2_SEEDS == tuple(range(2026104001, 2026104011))
    source = RUNNER.read_text(encoding="utf-8")
    assert 'sub.add_parser("calibrate")' in source
    assert 'sub.add_parser("run")' not in source
    assert 'sub.add_parser("prepare")' in source
    assert 'sub.add_parser("shard")' in source
    assert 'sub.add_parser("adjudicate")' in source
    assert "ee_axis_v07_c2_d2.py" in source
    assert '"d2_authorized": False' in source
    assert '"training": False' in source
    assert '"test_split_opened": False' in source


def test_evidence_commands_fail_until_prereg_is_frozen(tmp_path: Path) -> None:
    prereg = tmp_path / "draft.md"
    prereg.write_text("Status: `PREOUTCOME_DRAFT__DO_NOT_LAUNCH`\n", encoding="utf-8")
    assert mod.EXPECTED_D2_PREREG_SHA256 == ""
    with pytest.raises(mod.V07D2RunnerError, match="not been frozen"):
        mod._require_frozen_d2_prereg(prereg)


def test_carrier_selection_uses_first_chronological_mask_only_anchor() -> None:
    runtime = _Runtime(
        [
            _masks(1, 1, 1),
            _masks(2, 4, 5),
            _masks(8, 8, 8),
        ]
    )
    scan = mod._scan_carrier_anchor(
        runtime,
        source_seed=mod.CALIBRATION_SEED,
        field=object(),
    )
    step, focal, history = scan
    assert step == 1
    assert focal == 1
    assert len(history) == 2
    assert runtime.main_calls == 2
    assert scan.eligible_users_by_step == ((1, (1, 2)),)


def test_missing_eligible_window_fails_without_replacement() -> None:
    runtime = _Runtime([_masks(1, 1, 1)] * 3)
    with pytest.raises(mod.V07D2RunnerError, match="no early"):
        mod._scan_carrier_anchor(
            runtime,
            source_seed=mod.CALIBRATION_SEED,
            field=object(),
        )


def test_carrier_selection_allows_one_eligible_user_with_three_actions() -> None:
    runtime = _Runtime(
        [
            _masks(1, 1, 1),
            _masks(4, 1, 1),
            _masks(1, 1, 1),
        ]
    )
    scan = mod._scan_carrier_anchor(
        runtime,
        source_seed=mod.CALIBRATION_SEED,
        field=object(),
    )
    assert scan.target_step == 1
    assert scan.focal_user == 0
    assert scan.eligible_users_by_step == ((1, (0,)),)


def test_calibration_output_is_write_once(tmp_path: Path) -> None:
    target = tmp_path / "calibration.json"
    mod._canonical_write_once(target, {"finite": 1.0})
    with pytest.raises(mod.V07D2RunnerError, match="overwrite"):
        mod._canonical_write_once(target, {"finite": 2.0})
