from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/ee-axis-redesign/run_v03_action_shared_500ep_route_ablation.py"
)
SPEC = importlib.util.spec_from_file_location("action_shared_500", RUNNER)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class _Trainer:
    def q_values(self, states):
        rows = np.asarray(states).shape[0]
        return (
            np.tile([0.0, 3.0, 0.0], (rows, 1)),
            np.tile([0.0, 0.0, 2.0], (rows, 1)),
            np.tile([0.0, 0.0, 2.0], (rows, 1)),
        )


def test_route_ablation_is_one_masked_argmax_without_coordination() -> None:
    states = np.zeros((2, 1), dtype=np.float32)
    masks = np.array([[True, True, True], [True, True, False]], dtype=np.bool_)
    full = runner._active_actions(_Trainer(), states, masks, ("C1", "C2", "C3"))
    without_c1 = runner._active_actions(_Trainer(), states, masks, ("C2", "C3"))
    assert full.tolist() == [2, 1]
    assert without_c1.tolist() == [2, 0]


def test_route_ablation_rejects_nonfinite_q_surface() -> None:
    class Broken(_Trainer):
        def q_values(self, states):
            surfaces = list(super().q_values(states))
            surfaces[1][0, 0] = np.nan
            return tuple(surfaces)

    with pytest.raises(runner.ActionShared500Error, match="non-finite"):
        runner._active_actions(
            Broken(),
            np.zeros((1, 1), dtype=np.float32),
            np.ones((1, 3), dtype=np.bool_),
            ("C1", "C2", "C3"),
        )


def test_sweep_is_exactly_500_with_100_epoch_checkpoints_and_four_views() -> None:
    assert runner.SOURCE_EPOCHS == 500
    assert runner.CHECKPOINT_EPOCHS == (100, 200, 300, 400, 500)
    assert set(runner.POLICY_ROUTES) == {
        "FULL",
        "DROP_C1",
        "DROP_C2",
        "DROP_C3",
    }
    assert runner.MAIN_REFERENCE == "MAIN_REFERENCE"
    assert len(runner.EVALUATION_SEEDS) == 2
    assert len(runner.TRAINING_SEEDS) == 3


def test_aggregate_uses_ratio_of_sums() -> None:
    result = runner._aggregate(
        [
            {
                "total_bits": 10.0,
                "total_energy_j": 2.0,
                "ratio_of_sums_ee_bits_per_j": 5.0,
                "decision_count": 10,
                "served_user_steps": 5,
            },
            {
                "total_bits": 30.0,
                "total_energy_j": 10.0,
                "ratio_of_sums_ee_bits_per_j": 3.0,
                "decision_count": 10,
                "served_user_steps": 7,
            },
        ]
    )
    assert result["pooled_ratio_of_sums_ee_bits_per_j"] == 40.0 / 12.0
    assert result["served_fraction"] == 0.6


def test_paired_differences_require_all_views_and_identical_crn() -> None:
    rows = []
    traces = {
        "FULL": [[0, 1], [2, 2]],
        "DROP_C1": [[0, 0], [2, 1]],
        "DROP_C2": [[0, 1], [2, 2]],
        "DROP_C3": [[1, 1], [2, 2]],
    }
    for index, label in enumerate(runner.POLICY_ROUTES):
        rows.append(
            {
                "policy": label,
                "source_epoch": 100,
                "initialization_seed": 11,
                "evaluation_seed": 22,
                "fading_field_sha256": "a" * 64,
                "steps": 2,
                "decision_count": 4,
                "served_user_steps": 3 - index,
                "total_bits": 10.0 - index,
                "total_energy_j": 2.0 + index,
                "ratio_of_sums_ee_bits_per_j": (10.0 - index) / (2.0 + index),
                "served_fraction": (3 - index) / 4,
                "outage_fraction": 1.0 - (3 - index) / 4,
                "action_trace": traces[label],
            }
        )
    result = runner._paired_differences(rows)
    assert len(result) == 3
    c1 = next(row for row in result if row["contrast"] == "FULL_minus_DROP_C1")
    assert c1["action_mismatch_count"] == 2
    assert c1["action_mismatch_fraction"] == 0.5
    assert c1["action_mismatch_count_by_step"] == [1, 1]


def test_run_fails_closed_without_formal_expanded_c2_and_v3_go_digests(
    tmp_path: Path,
) -> None:
    with pytest.raises(runner.ActionShared500Error, match="formal expanded C2 TRAIN"):
        runner.run(
            source_root=tmp_path / "source",
            independent_verification_root=tmp_path / "independent",
            validation_root=tmp_path / "validation",
            output_dir=tmp_path / "output",
            tle_root=tmp_path / "tle",
            expected_independent_result_sha256="a" * 64,
            expected_validation_result_sha256="b" * 64,
        )
