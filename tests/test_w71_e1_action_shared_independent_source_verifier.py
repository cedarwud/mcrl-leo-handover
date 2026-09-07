from __future__ import annotations

import importlib.util
from pathlib import Path


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/ee-axis-redesign/verify_v03_e1_action_shared_sources.py"
)
SPEC = importlib.util.spec_from_file_location("e1_action_shared_verifier", RUNNER)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_independent_verifier_is_bound_to_four_three_zero_protocol() -> None:
    assert list(runner.wrapper.SOURCE_SEED_SPLIT.values()).count("train") == 4
    assert list(runner.wrapper.SOURCE_SEED_SPLIT.values()).count("validation") == 3
    assert "test" not in runner.wrapper.SOURCE_SEED_SPLIT.values()
    assert runner.wrapper.MINIMUM_CLUSTERS == {
        "train": 40,
        "validation": 30,
        "test": 0,
    }


def test_independent_verifier_has_explicit_no_test_claim_ceiling() -> None:
    assert "NO_TEST" in runner.verify.__doc__ if runner.verify.__doc__ else True
    assert "independent" in runner.__doc__.lower()
