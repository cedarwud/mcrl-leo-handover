"""W-50 — end-to-end route admission into the three-Q learner."""

from __future__ import annotations

import hashlib

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_pairwise import (
    EEAxisPairwiseConfig,
    EEAxisPairwiseTrainer,
)
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_opening_pairs import (
    build_opening_pair,
    build_opening_route_batch,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from mcrl.runtime.ee_axis_temporal_pairs import (
    C2_POLICY_VERSION,
    build_temporal_pair,
    build_temporal_route_batch,
)
from mcrl.runtime.ee_axis_training_schedule import (
    EEAxisThreeRouteBatches,
    EEAxisTrainingScheduleError,
    update_three_route_cycle,
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _mask() -> np.ndarray:
    value = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    value[:2] = True
    return value


def _opening(route: str):
    return build_opening_pair(
        source_route=route,
        source_rule=f"{route.lower()}-test-source",
        source_policy_version=1,
        anchor_sha256=_digest("opening-anchor"),
        source_manifest_sha256=_digest("manifest"),
        checkpoint_sha256=_digest("checkpoint"),
        common_random_field_sha256=_digest("field"),
        focal_user=0,
        state=np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32),
        action_mask=_mask(),
        reference_action=0,
        candidate_action=1,
        reference_joint_actions=np.asarray([0, 0], dtype=np.int64),
        candidate_joint_actions=np.asarray([1, 0], dtype=np.int64),
        reference_rates_bps=np.asarray([100.0, 50.0]),
        candidate_rates_bps=np.asarray([120.0, 55.0]),
        reference_system_power_w=10.0,
        candidate_system_power_w=10.0,
        lambda_bits_per_j=2.0,
        interval_s=1.0,
    )


def _temporal():
    reference_rates = np.asarray(
        [[100.0, 50.0], [100.0, 50.0], [100.0, 50.0], [100.0, 50.0]],
        dtype=np.float64,
    )
    candidate_rates = np.asarray(
        [[120.0, 55.0], [105.0, 50.0], [105.0, 50.0], [105.0, 50.0]],
        dtype=np.float64,
    )
    power = np.full(4, 10.0, dtype=np.float64)
    served = np.ones((4, 2), dtype=np.bool_)
    return build_temporal_pair(
        c2_policy_version=C2_POLICY_VERSION,
        source_rule="incumbent-hold",
        anchor_sha256=_digest("temporal-anchor"),
        anchor_schedule_sha256=_digest("schedule"),
        seed=1,
        step_index=3,
        source_manifest_sha256=_digest("manifest"),
        checkpoint_sha256=_digest("checkpoint"),
        common_random_field_sha256=_digest("field"),
        forecast_payload_sha256=_digest("forecast"),
        reference_trace_sha256=_digest("reference-trace"),
        candidate_trace_sha256=_digest("candidate-trace"),
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=_digest("state"),
        focal_user=0,
        state=np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32),
        action_mask=_mask(),
        reference_action=0,
        candidate_action=1,
        held_physical_key=(50001, 1),
        held_key_match_counts=(1, 1, 1, 1),
        release_offset=3,
        release_reason="horizon",
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=power,
        candidate_system_power_w=power,
        reference_served=served,
        candidate_served=served,
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        offset_surplus_bits=np.asarray([5.0, 5.0, 5.0], dtype=np.float64),
        zeta2_temporal_surplus_bits=15.0,
    )


def _batches() -> EEAxisThreeRouteBatches:
    return EEAxisThreeRouteBatches(
        c1=build_opening_route_batch([_opening("C1")]),
        c2=build_temporal_route_batch([_temporal()]),
        c3=build_opening_route_batch([_opening("C3")]),
    )


def _trainer() -> EEAxisPairwiseTrainer:
    return EEAxisPairwiseTrainer(
        EEAxisPairwiseConfig(
            state_dim=EE_AXIS_STATE_DIM,
            action_dim=NUM_ACTIONS,
            hidden_layers=(8,),
            activation="tanh",
            learning_rate=0.01,
            kappa_bits=10.0,
            beta=0.1,
            loss_weights=(1.0, 1.0, 1.0),
        ),
        train_seed=20260831,
    )


def _snapshot(trainer: EEAxisPairwiseTrainer):
    return [
        {name: value.detach().clone() for name, value in network.state_dict().items()}
        for network in trainer.q_nets
    ]


def _network_changed(before, after, index: int) -> bool:
    return any(
        not torch.equal(before[index][name], after[index][name])
        for name in before[index]
    )


def test_real_route_adapters_update_exactly_three_independent_q_functions() -> None:
    trainer = _trainer()
    before = _snapshot(trainer)
    receipts = update_three_route_cycle(trainer, _batches())
    after = _snapshot(trainer)
    assert [receipt["route"] for receipt in receipts] == ["C1", "C2", "C3"]
    assert all(_network_changed(before, after, index) for index in range(3))
    state = np.zeros((1, EE_AXIS_STATE_DIM), dtype=np.float32)
    q1, q2, q3 = trainer.q_values(state)
    assert np.array_equal(trainer.deployment_scores(state), q1 + q2 + q3)


def test_schedule_rejects_route_swap_omission_and_stale_trainer_state() -> None:
    trainer = _trainer()
    batches = _batches()
    with pytest.raises(EEAxisTrainingScheduleError, match="c1 must be"):
        EEAxisThreeRouteBatches(
            c1=batches.c3,
            c2=batches.c2,
            c3=batches.c1,
        ).verify(trainer)
    with pytest.raises(EEAxisTrainingScheduleError, match="exactly once"):
        update_three_route_cycle(trainer, batches, order=("C1", "C1", "C3"))

    stale = EEAxisPairwiseTrainer(
        EEAxisPairwiseConfig(
            state_dim=112,
            action_dim=NUM_ACTIONS,
            hidden_layers=(8,),
            activation="tanh",
            learning_rate=0.01,
            kappa_bits=10.0,
            beta=0.1,
            loss_weights=(1.0, 1.0, 1.0),
        ),
        train_seed=1,
    )
    with pytest.raises(EEAxisTrainingScheduleError, match="228-D"):
        batches.verify(stale)
