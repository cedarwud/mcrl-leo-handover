"""W-155 -- V0.14 five-arm decoder, EE pooling, and 100-EP hooks."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v014-learner"
    / "run_v014_five_arm_evaluation.py"
)
SPEC = importlib.util.spec_from_file_location("mcrl_v014_five_arm_w155", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def _surface(*, action: int, value: float, rows: int = 2) -> np.ndarray:
    result = np.zeros((rows, RUNNER.ACTION_DIM), dtype=np.float64)
    result[:, action] = value
    return result


def _mask(rows: int = 2) -> np.ndarray:
    result = np.zeros((rows, RUNNER.ACTION_DIM), dtype=np.bool_)
    result[:, :3] = True
    return result


def _receipt(arm: str, episode: int, *, bits: float = 10.0, energy: float = 2.0):
    return RUNNER.V014EpisodeReceipt(
        arm=arm,
        episode_index=episode,
        evaluation_seed=1000 + episode,
        total_bits=bits,
        total_energy_j=energy,
        decision_count=10,
        served_user_steps=10,
    )


def test_route_arms_are_literal_head_omissions_with_one_common_argmax() -> None:
    q1 = _surface(action=1, value=5.0)
    q2 = _surface(action=2, value=4.0)
    q3 = _surface(action=2, value=3.0)
    masks = _mask()

    assert RUNNER.route_actions(q1, q2, q3, masks, "FULL").tolist() == [2, 2]
    assert RUNNER.route_actions(q1, q2, q3, masks, "DROP_C1").tolist() == [2, 2]
    assert RUNNER.route_actions(q1, q2, q3, masks, "DROP_C2").tolist() == [1, 1]
    assert RUNNER.route_actions(q1, q2, q3, masks, "DROP_C3").tolist() == [1, 1]

    altered_q1 = q1.copy()
    altered_q1[:, 0] = 100.0
    # Q1 is omitted from DROP_C1, so it cannot change that arm's action.
    assert np.array_equal(
        RUNNER.route_actions(q1, q2, q3, masks, "DROP_C1"),
        RUNNER.route_actions(altered_q1, q2, q3, masks, "DROP_C1"),
    )

    main = _surface(action=0, value=7.0)
    assert RUNNER.select_arm_actions(
        q1, q2, q3, masks, "MAIN", main_values=main
    ).tolist() == [0, 0]


def test_decoder_uses_native_mask_and_lowest_index_on_ties() -> None:
    q1 = np.zeros((1, RUNNER.ACTION_DIM), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q3 = np.zeros_like(q1)
    masks = np.zeros((1, RUNNER.ACTION_DIM), dtype=np.bool_)
    masks[0, [2, 5]] = True
    assert RUNNER.route_actions(q1, q2, q3, masks, "FULL").tolist() == [2]

    invalid = masks.copy()
    invalid[0, 2] = False
    invalid[0, 5] = False
    with pytest.raises(RUNNER.V014FiveArmEvaluationError, match="admit"):
        RUNNER.route_actions(q1, q2, q3, invalid, "FULL")

    q2[0, 1] = np.nan
    with pytest.raises(RUNNER.V014FiveArmEvaluationError, match="non-finite"):
        RUNNER.route_actions(q1, q2, q3, masks, "FULL")


def test_main_requires_an_independent_baseline_surface() -> None:
    q1 = np.zeros((1, RUNNER.ACTION_DIM), dtype=np.float64)
    masks = _mask(rows=1)
    with pytest.raises(RUNNER.V014FiveArmEvaluationError, match="explicit"):
        RUNNER.select_arm_actions(q1, q1, q1, masks, "MAIN")


def test_five_arm_aggregation_uses_pooled_ratio_of_sums_and_contrasts() -> None:
    rows = {
        arm: [_receipt(arm, 1, bits=10.0, energy=2.0)]
        for arm in RUNNER.ARMS
    }
    rows["FULL"] = [_receipt("FULL", 1, bits=30.0, energy=10.0)]
    rows["DROP_C1"] = [_receipt("DROP_C1", 1, bits=20.0, energy=10.0)]
    result = RUNNER.aggregate_five_arm(rows)
    full = result["summaries"]["FULL"]
    assert full["pooled_ratio_of_sums_ee_bits_per_j"] == 3.0
    assert full["mean_episode_ee_bits_per_j"] == 3.0
    contrast = result["contrasts"]["FULL_minus_DROP_C1"]
    assert contrast["relative_delta"] == 0.5
    assert contrast["service_noninferior"] is True


def test_run_emits_each_arm_checkpoint_at_the_declared_cadence(tmp_path: Path) -> None:
    spec = RUNNER.V014FiveArmEvaluationSpec(episodes=4, checkpoint_every_episodes=2)
    episode_events: list[tuple[str, int]] = []
    checkpoint_events: list[tuple[str, int]] = []

    def episode_runner(*, arm: str, episode_index: int):
        return _receipt(arm, episode_index, bits=10.0 + episode_index, energy=2.0)

    def on_episode(receipt: RUNNER.V014EpisodeReceipt) -> None:
        episode_events.append((receipt.arm, receipt.episode_index))

    def on_checkpoint(event: RUNNER.V014CheckpointEvent):
        checkpoint_events.append((event.arm, event.episode_index))
        return {"checkpoint_kind": "synthetic-test"}

    result = RUNNER.run_five_arm_evaluation(
        episode_runner,
        spec=spec,
        output_dir=tmp_path / "evaluation",
        checkpoint_callback=on_checkpoint,
        episode_callback=on_episode,
    )
    assert result["arms"] == list(RUNNER.ARMS)
    assert len(episode_events) == 5 * 4
    assert len(checkpoint_events) == 5 * 2
    assert all(
        [episode for arm_name, episode in checkpoint_events if arm_name == arm]
        == [2, 4]
        for arm in RUNNER.ARMS
    )
    assert len(list((tmp_path / "evaluation" / "checkpoints").glob("*.json"))) == 10
    assert (tmp_path / "evaluation" / "result.json").is_file()
    with pytest.raises(RUNNER.V014FiveArmEvaluationError, match="overwrite"):
        RUNNER.run_five_arm_evaluation(
            episode_runner,
            spec=spec,
            output_dir=tmp_path / "evaluation",
        )
