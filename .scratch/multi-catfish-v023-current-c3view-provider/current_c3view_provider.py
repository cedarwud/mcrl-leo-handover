#!/usr/bin/env python3
"""Outcome-blind current opening-feasibility provider for V0.23 plumbing.

This adapter deliberately reuses the exact predecision primitives already used
by the LC-SRS source pipeline.  It does not step the environment, draw fading,
evaluate a teacher, or inspect a post-action outcome.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE_ADAPTER = (
    REPO
    / ".scratch"
    / "multi-catfish-v023-r6-fit-binding-fix"
    / "v023_lcsrs_source_adapter.py"
)
V020_RUNTIME = (
    REPO
    / ".scratch"
    / "multi-catfish-v020-c3-source-audit"
    / "run_v020_repriced_c3_gate.py"
)


class CurrentC3ViewProviderError(RuntimeError):
    """The current predecision opening surface could not be reproduced."""


def _load_module(name: str, path: Path) -> Any:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise CurrentC3ViewProviderError(f"required source is missing: {source}")
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise CurrentC3ViewProviderError(f"cannot import required source: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise CurrentC3ViewProviderError(
            f"cannot load required source: {source}"
        ) from error
    return module


def load_current_predecision_runtime() -> Any:
    """Load the same V0.18 physical runtime reached by the current source path."""

    source = _load_module("v023_c3view_source_adapter", SOURCE_ADAPTER)
    try:
        v020 = source._load_module("v023_c3view_v020_runtime", V020_RUNTIME)
        v020._validate_global_inputs()
        v018 = v020._load_module("v023_c3view_v018_runtime", v020.V018_PATH)
        v018.validate_v018_contract()
    except Exception as error:
        raise CurrentC3ViewProviderError(
            "current LC-SRS source dependency chain cannot be loaded"
        ) from error
    for name in (
        "snapshot_ops3_anchor",
        "_current_required_power_and_opening",
        "_V015",
    ):
        if not hasattr(v018, name):
            raise CurrentC3ViewProviderError(
                f"current predecision runtime lacks {name}"
            )
    return v018


class CurrentOpeningFeasibilityProvider:
    """Callable used by the current structured-C3 view factory."""

    def __init__(self, runtime: Any | None = None) -> None:
        self._runtime = runtime if runtime is not None else load_current_predecision_runtime()

    def __call__(self, step_environment: Any, observation: Any) -> np.ndarray:
        runtime = self._runtime
        try:
            native = runtime._V015._V013.encode_ee_axis_state(
                step_environment, observation
            )
            native.verify()
            masks = np.asarray(native.action_masks, dtype=np.bool_)
            anchor = runtime.snapshot_ops3_anchor(step_environment, observation)
            _required_power, opening = runtime._current_required_power_and_opening(
                current_gain_linear=anchor.current_gain_linear,
                segment_start_gain_linear=anchor.segment_start_gain_linear,
                action_masks=masks,
            )
        except Exception as error:
            raise CurrentC3ViewProviderError(
                "current predecision opening-feasibility capture failed"
            ) from error
        result = np.array(opening, dtype=np.bool_, copy=True, order="C")
        if result.shape != masks.shape:
            raise CurrentC3ViewProviderError(
                "opening-feasibility shape disagrees with the native action mask"
            )
        if np.any(result & ~masks):
            raise CurrentC3ViewProviderError(
                "opening feasibility admits an action outside the native mask"
            )
        result.setflags(write=False)
        return result


__all__ = [
    "CurrentC3ViewProviderError",
    "CurrentOpeningFeasibilityProvider",
    "load_current_predecision_runtime",
]
