"""Focused tests for C3 development-smoke candidate entry semantics."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_c3_h3_backend_smoke", HERE / "run_c3_h3_backend_smoke.py"
)
assert SPEC is not None and SPEC.loader is not None
S = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = S
SPEC.loader.exec_module(S)


def _baseline(loads):
    return SimpleNamespace(
        resolution=SimpleNamespace(eligible_load_by_beam=loads)
    )


def test_candidate_entry_requires_strict_canonical_r3_gain_and_active_destination():
    source = (10, 1)
    candidates = ((10, 2), (10, 3), (10, 4))
    selected = S._strict_load_candidates(
        _baseline({source: 4, (10, 2): 1, (10, 3): 3, (10, 4): 0}),
        source_id=source,
        candidate_ids=candidates,
    )

    assert selected == ((10, 2),)


def test_gap_of_one_is_rejected_before_h3_rollout():
    source = (10, 1)
    selected = S._strict_load_candidates(
        _baseline({source: 2, (10, 2): 1}),
        source_id=source,
        candidate_ids=((10, 2),),
    )

    assert selected == ()
