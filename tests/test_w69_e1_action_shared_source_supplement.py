from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/ee-axis-redesign/run_v03_e1_action_shared_sources.py"
)
SPEC = importlib.util.spec_from_file_location("e1_action_shared_sources", RUNNER)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_supplement_uses_four_train_three_validation_and_no_test_seeds() -> None:
    assert list(runner.SOURCE_SEED_SPLIT.values()).count("train") == 4
    assert list(runner.SOURCE_SEED_SPLIT.values()).count("validation") == 3
    assert "test" not in runner.SOURCE_SEED_SPLIT.values()
    assert not set(runner.SOURCE_SEED_SPLIT) & set(runner.BURNED_SOURCE_SEEDS)


def test_supplement_seed_verifier_fails_closed_on_drift_or_burned_seed() -> None:
    assert runner._verify_design_seed_split(
        runner.SOURCE_SEED_SPLIT, burned_seeds=runner.BURNED_SOURCE_SEEDS
    ) == runner.SOURCE_SEED_SPLIT
    with pytest.raises(runner.source.E1FreshSourceError, match="sealed 4/3/0"):
        runner._verify_design_seed_split(
            {**runner.SOURCE_SEED_SPLIT, 2026092007: "train"},
            burned_seeds=runner.BURNED_SOURCE_SEEDS,
        )
    with pytest.raises(runner.source.E1FreshSourceError, match="burned"):
        runner._verify_design_seed_split(
            runner.SOURCE_SEED_SPLIT,
            burned_seeds=(*runner.BURNED_SOURCE_SEEDS, 2026092001),
        )


def test_action_shared_prereg_has_no_test_generation_authority() -> None:
    runner._install_protocol()
    assert runner.source.SOURCE_SEED_SPLIT == runner.SOURCE_SEED_SPLIT
    assert runner.source.MINIMUM_INFERENCE_ANCHORS["C2"] == {
        "train": 12,
        "validation": 9,
        "test": 0,
    }
    assert runner.source._learner_contract.__name__ == (
        "_action_shared_learner_contract"
    )
