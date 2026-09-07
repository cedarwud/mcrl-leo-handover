"""W-54 -- bounded three-route pilot runtime and checkpoint round-trip."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairwiseTrainer
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_calibration import calibrate_ee_axis_pilot
from mcrl.runtime.ee_axis_opening_pairs import (
    build_opening_pair,
    build_opening_route_batch,
)
from mcrl.runtime.ee_axis_pilot_runner import (
    EEAxisPilotRunSpec,
    EEAxisPilotRunnerError,
    load_pairwise_pilot_checkpoint,
    run_pairwise_pilot,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from mcrl.runtime.ee_axis_temporal_pairs import (
    build_temporal_pair,
    build_temporal_route_batch,
)
from mcrl.runtime.ee_axis_training_schedule import EEAxisThreeRouteBatches


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _mask():
    return np.asarray([index in {3, 11} for index in range(NUM_ACTIONS)], dtype=np.bool_)


def _opening(route: str):
    reference_rates = np.asarray([100.0, 50.0])
    candidate_rates = np.asarray([115.0, 51.0])
    return build_opening_pair(
        source_route=route,
        source_rule=f"{route.lower()}-source",
        source_policy_version=1,
        anchor_sha256=_digest(f"anchor-{route}"),
        source_manifest_sha256=_digest("manifest"),
        checkpoint_sha256=_digest("checkpoint"),
        common_random_field_sha256=_digest("field"),
        focal_user=0,
        state=np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32),
        action_mask=_mask(),
        reference_action=11,
        candidate_action=3,
        reference_joint_actions=np.asarray([11, 11]),
        candidate_joint_actions=np.asarray([3, 11]),
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=10.0,
        candidate_system_power_w=10.5,
        lambda_bits_per_j=2.0,
        interval_s=1.0,
    )


def _temporal():
    reference_rates = np.asarray([[100.0, 50.0]] * 4)
    candidate_rates = np.asarray([[100.0, 50.0], [110.0, 50.0], [110.0, 50.0], [110.0, 50.0]])
    return build_temporal_pair(
        c2_policy_version="C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE",
        source_rule="incumbent-hold",
        anchor_sha256=_digest("anchor-C2"),
        anchor_schedule_sha256=_digest("schedule-C2"),
        seed=1,
        step_index=1,
        source_manifest_sha256=_digest("manifest"),
        checkpoint_sha256=_digest("checkpoint"),
        common_random_field_sha256=_digest("field-C2"),
        forecast_payload_sha256=_digest("forecast-C2"),
        reference_trace_sha256=_digest("reference-C2"),
        candidate_trace_sha256=_digest("candidate-C2"),
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=_digest("state-C2"),
        focal_user=0,
        state=np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32),
        action_mask=_mask(),
        reference_action=11,
        candidate_action=3,
        held_physical_key=(50123, 1),
        held_key_match_counts=(1, 1, 1, 1),
        release_offset=3,
        release_reason="horizon",
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=np.asarray([10.0] * 4),
        candidate_system_power_w=np.asarray([10.0] * 4),
        reference_served=np.ones((4, 2), dtype=np.bool_),
        candidate_served=np.ones((4, 2), dtype=np.bool_),
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        offset_surplus_bits=np.asarray([10.0, 10.0, 10.0]),
        zeta2_temporal_surplus_bits=30.0,
    )


def _batches():
    return EEAxisThreeRouteBatches(
        c1=build_opening_route_batch([_opening("C1")]),
        c2=build_temporal_route_batch([_temporal()]),
        c3=build_opening_route_batch([_opening("C3")]),
    )


def _trainer(seed: int = 7):
    calibration = calibrate_ee_axis_pilot(
        calibration_seed=1,
        useful_bits=1000.0,
        energy_j=10.0,
        steps=2,
        users=5,
    )
    return EEAxisPairwiseTrainer(
        calibration.pairwise_config(
            learning_rate=0.01,
            hidden_layers=(8,),
        ),
        train_seed=seed,
    )


def test_bounded_pilot_runs_three_diagonal_updates_per_episode_and_resumes(tmp_path):
    trainer = _trainer()
    batches = _batches()
    spec = EEAxisPilotRunSpec(
        run_id="unit-pilot",
        episodes=3,
        checkpoint_every_episodes=2,
    )
    output = tmp_path / "pilot"
    status = run_pairwise_pilot(trainer, batches, spec=spec, output_dir=output)
    assert status["status"] == "complete"
    assert status["episodes_completed"] == 3
    assert status["updates_completed"] == 9
    assert status["held_out_ee_evaluated"] is False
    assert (output / "checkpoints" / "checkpoint-episode-000002.pt").is_file()
    final = output / "checkpoints" / "checkpoint-episode-000003.pt"

    restored = _trainer()
    completed = load_pairwise_pilot_checkpoint(
        final,
        trainer=restored,
        expected_spec=spec,
        expected_batch_digests={
            "C1": batches.c1.verify(),
            "C2": batches.c2.verify(),
            "C3": batches.c3.verify(),
        },
    )
    assert completed == 3
    states = np.zeros((1, EE_AXIS_STATE_DIM), dtype=np.float32)
    assert np.array_equal(trainer.deployment_scores(states), restored.deployment_scores(states))


def test_bounded_pilot_refuses_overwrite_and_more_than_twenty_episodes(tmp_path):
    with pytest.raises(EEAxisPilotRunnerError, match=r"\[1,20\]"):
        EEAxisPilotRunSpec(run_id="too-long", episodes=21).verify()
    output = tmp_path / "pilot"
    output.mkdir()
    with pytest.raises(EEAxisPilotRunnerError, match="already exists"):
        run_pairwise_pilot(
            _trainer(),
            _batches(),
            spec=EEAxisPilotRunSpec(run_id="unit", episodes=1),
            output_dir=output,
        )
