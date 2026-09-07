"""W-206 -- synthetic V0.23 episode-screen first-slice seam."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcrl.runtime.ee_axis_v023_episode_screen import (
    PRIMARY_ARMS,
    SEALED_PENDING_GATE,
    CHECKPOINT_PERIOD,
    EpisodeScreen,
    ScreenRequest,
    SyntheticDeterministicAdapter,
)


def _request() -> ScreenRequest:
    return ScreenRequest(
        screen_id="w206-first-slice",
        arms=PRIMARY_ARMS,
        episode_count=200,
        split="TRAIN",
        world_ids=("synthetic-train-world",),
        training_seeds=(20260905,),
        common_random_field_binding="synthetic-crf-v1",
        sweep_grid=(
            {"load": "low"},
            {"load": "high"},
        ),
        checkpoint_period=CHECKPOINT_PERIOD,
        bindings={arm: "synthetic-fixed-binding-v1" for arm in PRIMARY_ARMS},
        execution_admission_token="synthetic-first-slice-admitted",
    )


def test_first_slice_runs_all_arms_and_resume_is_byte_identical(tmp_path: Path) -> None:
    plan = EpisodeScreen.plan(_request())
    adapter = SyntheticDeterministicAdapter()

    uninterrupted = EpisodeScreen.execute(
        plan,
        adapter,
        checkpoint_dir=tmp_path / "uninterrupted",
    )
    paused = EpisodeScreen.execute(
        plan,
        adapter,
        checkpoint_dir=tmp_path / "resumed",
        stop_after=100,
    )
    resumed = EpisodeScreen.resume(paused.checkpoint, adapter)

    assert plan.arms == PRIMARY_ARMS
    assert plan.episode_count == 200
    assert {path.name for path in (tmp_path / "uninterrupted").glob("checkpoint-*.json")} == {
        "checkpoint-000100.json",
        "checkpoint-000200.json",
    }
    assert {path.name for path in (tmp_path / "resumed").glob("checkpoint-*.json")} == {
        "checkpoint-000100.json",
        "checkpoint-000200.json",
    }
    assert resumed.episode_end == uninterrupted.episode_end == 200
    assert resumed.arm_receipt_bytes == uninterrupted.arm_receipt_bytes
    assert resumed.receipt_sha256 == uninterrupted.receipt_sha256
    assert resumed.final_checkpoint.checkpoint_sha256 == uninterrupted.final_checkpoint.checkpoint_sha256
    assert EpisodeScreen.digest(resumed).status == SEALED_PENDING_GATE
    assert EpisodeScreen.digest(resumed).receipt_sha256 == resumed.receipt_sha256

    for arm in PRIMARY_ARMS:
        assert resumed.arm_receipts[arm].receipt_sha256 == uninterrupted.arm_receipts[arm].receipt_sha256
        for row in resumed.arm_receipts[arm].sweep_receipts:
            assert row.total_bits_B > 0.0
            assert row.total_energy_E > 0.0
            assert row.ee_ratio_of_sums_eta == pytest.approx(
                row.total_bits_B / row.total_energy_E
            )
            assert 0.0 <= row.service_fraction_S <= 1.0
            assert row.status == SEALED_PENDING_GATE


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("split", "TEST", "TRAIN"),
        ("episode_count", 9000, "200"),
        ("checkpoint_period", 50, "100"),
    ],
)
def test_plan_rejects_unsafe_first_slice_configuration(
    field: str, value: object, message: str
) -> None:
    values = _request().__dict__
    values[field] = value
    with pytest.raises(ValueError, match=message):
        EpisodeScreen.plan(ScreenRequest(**values))


def test_plan_rejects_missing_arm_binding() -> None:
    values = _request().__dict__
    values["bindings"] = {
        arm: "synthetic-fixed-binding-v1"
        for arm in PRIMARY_ARMS
        if arm != "DROP_C3"
    }
    with pytest.raises(ValueError, match="binding"):
        EpisodeScreen.plan(ScreenRequest(**values))
