from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "current_c3view_provider_under_test", HERE / "current_c3view_provider.py"
)
assert SPEC is not None and SPEC.loader is not None
API = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = API
SPEC.loader.exec_module(API)


class _Native:
    def __init__(self, masks: np.ndarray) -> None:
        self.action_masks = masks
        self.verified = False

    def verify(self) -> None:
        self.verified = True


class _Runtime:
    def __init__(self, masks: np.ndarray, opening: np.ndarray) -> None:
        self.native = _Native(masks)
        self.opening = opening
        self.calls: list[str] = []
        self._V015 = SimpleNamespace(
            _V013=SimpleNamespace(encode_ee_axis_state=self._encode)
        )

    def _encode(self, environment: object, observation: object) -> _Native:
        assert environment == "env" and observation == "obs"
        self.calls.append("encode")
        return self.native

    def snapshot_ops3_anchor(self, environment: object, observation: object) -> object:
        assert environment == "env" and observation == "obs"
        self.calls.append("snapshot")
        return SimpleNamespace(
            current_gain_linear=np.ones((2, 3), dtype=np.float64),
            segment_start_gain_linear=np.ones((2, 3), dtype=np.float64),
        )

    def _current_required_power_and_opening(self, **kwargs: object) -> tuple[np.ndarray, np.ndarray]:
        self.calls.append("opening")
        assert np.array_equal(kwargs["action_masks"], self.native.action_masks)
        return np.ones((2, 3), dtype=np.float64), self.opening


def test_returns_readonly_native_mask_bounded_surface() -> None:
    masks = np.array([[1, 1, 0], [1, 0, 1]], dtype=np.bool_)
    opening = np.array([[1, 0, 0], [1, 0, 1]], dtype=np.bool_)
    runtime = _Runtime(masks, opening)
    result = API.CurrentOpeningFeasibilityProvider(runtime)("env", "obs")
    assert runtime.calls == ["encode", "snapshot", "opening"]
    assert runtime.native.verified
    assert np.array_equal(result, opening)
    assert result.dtype == np.bool_ and not result.flags.writeable


def test_rejects_opening_outside_native_mask() -> None:
    masks = np.array([[1, 0, 0], [1, 0, 1]], dtype=np.bool_)
    opening = np.array([[1, 1, 0], [1, 0, 1]], dtype=np.bool_)
    with pytest.raises(API.CurrentC3ViewProviderError, match="outside the native mask"):
        API.CurrentOpeningFeasibilityProvider(_Runtime(masks, opening))("env", "obs")


def test_rejects_shape_drift() -> None:
    masks = np.ones((2, 3), dtype=np.bool_)
    opening = np.ones((2, 2), dtype=np.bool_)
    with pytest.raises(API.CurrentC3ViewProviderError, match="shape disagrees"):
        API.CurrentOpeningFeasibilityProvider(_Runtime(masks, opening))("env", "obs")
