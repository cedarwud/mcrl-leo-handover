"""W-128 -- bounded native-28 opening panel for the C2 P0 source runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".scratch" / "c3-v04" / "run_v07_c2_fast_iteration.py"
SPEC = importlib.util.spec_from_file_location("v07_c2_fast_iteration_w128", RUNNER)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def _decision(*, legal: tuple[int, ...], reference: int) -> SimpleNamespace:
    masks = np.zeros((1, NUM_ACTIONS), dtype=np.bool_)
    masks[0, list(legal)] = True
    return SimpleNamespace(masks=masks, actions=np.asarray([reference], dtype=np.int64))


def _observation() -> SimpleNamespace:
    return SimpleNamespace(
        candidate_sinr=np.zeros((1, NUM_ACTIONS), dtype=np.float64)
    )


def test_native28_enumerates_each_legal_action_once_and_includes_reference() -> None:
    legal = (0, 3, 7, 12, 27)
    decision = _decision(legal=legal, reference=12)

    panel = mod._panel(
        _observation(),
        decision,
        np.zeros((1, mod.RADIAL_STOP), dtype=np.float32),
        focal_user=0,
        action_panel="native28",
    )

    assert panel == legal
    assert len(panel) == len(set(panel))
    assert set(panel) == set(legal)
    assert 12 in panel


def test_native28_supports_full_native_action_universe() -> None:
    decision = _decision(legal=tuple(range(NUM_ACTIONS)), reference=27)

    panel = mod._native28_action_panel(decision, focal_user=0)

    assert panel == tuple(range(NUM_ACTIONS))
    assert len(panel) == NUM_ACTIONS


def test_native28_fails_closed_for_duplicate_or_missing_actions() -> None:
    legal = np.asarray((1, 3, 7), dtype=np.int64)
    with pytest.raises(mod.FastIterationError, match="duplicate or missing"):
        mod._validate_native28_panel(
            panel=(1, 1, 7), legal_actions=legal, reference_action=1
        )
    with pytest.raises(mod.FastIterationError, match="duplicate or missing"):
        mod._validate_native28_panel(
            panel=(1, 7), legal_actions=legal, reference_action=1
        )


def test_native28_fails_closed_when_reference_is_not_legal() -> None:
    decision = _decision(legal=(1, 3, 7), reference=5)

    with pytest.raises(mod.FastIterationError, match="reference"):
        mod._native28_action_panel(decision, focal_user=0)


def test_fast4_default_panel_remains_bounded_proxy_selection() -> None:
    legal = (1, 4, 7, 13, 20)
    decision = _decision(legal=legal, reference=7)
    observation = _observation()
    q2_state = np.zeros((1, mod.RADIAL_STOP), dtype=np.float32)
    q2_state[0, mod.RADIAL_START + 13] = -2.0
    q2_state[0, mod.RADIAL_START + 20] = 3.0

    panel = mod._panel(observation, decision, q2_state, focal_user=0)

    assert panel == (7, 1, 13, 20)
    assert len(panel) <= 4

