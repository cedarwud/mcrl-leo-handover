from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest


RUNNER = Path(__file__).with_name("run_v020_repriced_c3_gate.py")
SPEC = importlib.util.spec_from_file_location("v020_serializer_test_runner", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_numpy_scalars_are_canonical_json_values() -> None:
    payload = {
        "flag": np.bool_(True),
        "count": np.int64(7),
        "score": np.float64(2.5),
    }
    encoded = MODULE._canonical_bytes(payload)
    assert json.loads(encoded) == {"count": 7, "flag": True, "score": 2.5}
    assert encoded == MODULE._canonical_bytes(payload)


def test_nonfinite_numpy_float_is_rejected() -> None:
    with pytest.raises(ValueError):
        MODULE._canonical_bytes({"score": np.float64(np.inf)})
