from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
OBSERVABILITY = REPO / ".scratch" / "multi-catfish-v023-c3-observability"


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("module_name", "filename"),
    [
        ("test_w205_source_adapter", "v023_lcsrs_source_adapter.py"),
        ("test_w205_composition_runtime", "v023_lcsrs_composition_runtime.py"),
    ],
)
def test_step_result_observation_comes_from_full_last_outcome(
    module_name: str,
    filename: str,
) -> None:
    module = _load_module(module_name, OBSERVABILITY / filename)
    expected = object()
    environment = SimpleNamespace(
        last_outcome=SimpleNamespace(observation=expected),
    )
    # TrainerEnvironment.step() returns StepResult, which intentionally has
    # no ``observation`` field.  The complete StepOutcome is exposed through
    # the wrapper's last_outcome property.
    result = SimpleNamespace(done=False)

    assert module._step_result_observation(environment, result) is expected


@pytest.mark.parametrize(
    ("module_name", "filename"),
    [
        ("test_w205_source_adapter_fallback", "v023_lcsrs_source_adapter.py"),
        ("test_w205_composition_runtime_fallback", "v023_lcsrs_composition_runtime.py"),
    ],
)
def test_step_result_observation_keeps_direct_outcome_compatibility(
    module_name: str,
    filename: str,
) -> None:
    module = _load_module(module_name, OBSERVABILITY / filename)
    expected = object()
    result = SimpleNamespace(observation=expected)

    assert module._step_result_observation(SimpleNamespace(), result) is expected
