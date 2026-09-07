"""Green contracts for the V0.23 OPS-3 C2 handoff.

These tests deliberately describe the selected-pair producer that is now
sealed upstream, rather than accepting the historical Temporal-Fork reader.
They must not be silently converted into a 228-D projection: that would lose
the target-free OPS-3 feature surface or reintroduce a second kappa
normalization.

This file is additive and intentionally not listed by the frozen 100E launch
manifest.  It performs no simulator, learner update, or TEST access.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRSThreeRouteConfig
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014NormalizedPairBatch,
)
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_REFERENCE,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view
from mcrl.runtime.ee_axis_v014_q2_state import V014_Q2_STATE_DIM


REPO = Path(__file__).resolve().parents[2]
ADAPTER_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-target-batch-adapter/target_batch_adapter.py"
)
HETERO_TRAINER_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-heterogeneous-trainer/v023_heterogeneous_trainer.py"
)
ORCHESTRATOR_PATH = (
    REPO
    / ".scratch/multi-catfish-v023-five-arm-learner-orchestrator"
    / "v023_five_arm_learner_orchestrator.py"
)
OPS3_SELECTED_PAIR_SCHEMA = (
    "multi-catfish-mcrl-v023-repriced-ops3-selected-pair-dataset-v1"
)
OPS3_TARGET_UNIT = "normalized-repriced-ops3-delta-over-kappa"


def _load_adapter():
    spec = importlib.util.spec_from_file_location(
        "v023_target_batch_adapter_red_contract", ADAPTER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_orchestrator():
    name = "v023_ops3_vertical_slice_orchestrator"
    spec = importlib.util.spec_from_file_location(name, ORCHESTRATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _ops3_row(*, horizon: int = 0) -> dict[str, object]:
    """A minimal selected-pair row with the producer's feature-major state."""

    features = np.arange(NUM_ACTIONS * 16, dtype=np.float64).reshape(NUM_ACTIONS, 16)
    state = features.astype(np.float32).T.reshape(-1)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    mask[[0, 1]] = True
    zeros = np.zeros((3, NUM_ACTIONS), dtype=np.float64)
    return {
        "schema": OPS3_SELECTED_PAIR_SCHEMA,
        "world": 1,
        "mode": "informed",
        "source_anchor_sha256": "a" * 64,
        "step_index": 9,
        "focal_user": 0,
        "reference_action": 0,
        "candidate_action": 1,
        "candidate_physical_key": [1, 2],
        "source_rule": "fixture-ops3-selected-pair",
        "schedule_sha256": "b" * 64,
        "target_unit": OPS3_TARGET_UNIT,
        "target_reference_value": -0.25,
        "target_candidate_value": 0.75,
        "target_delta": 1.0,
        "q1_reference_action": 0,
        "action_mask": mask.tolist(),
        "q2_state": state.astype(np.float64).tolist(),
        "q2_features": features.tolist(),
        "persistence": zeros.tolist(),
        "rate_bps": zeros.tolist(),
        "marginal_power_w": zeros.tolist(),
        "required_power_w": zeros.tolist(),
        "horizon": horizon,
        "provenance": {
            "ops3_anchor_sha256": "c" * 64,
            "ops3_tracker_seed_sha256": "d" * 64,
            "ops3_projection_sha256": "e" * 64,
            "ops3_future_d2_indices": [],
            "ops3_sample_times_utc": [],
            "ops3_offset_times_utc": [],
        },
    }


def test_selected_pair_fixture_preserves_the_producer_projection_and_unit():
    """The producer's row itself fixes 448-D state, target delta, and H_t=0."""

    row = _ops3_row(horizon=0)
    features = np.asarray(row["q2_features"], dtype=np.float64)
    state = np.asarray(row["q2_state"], dtype=np.float32)
    assert state.shape == (V014_Q2_STATE_DIM,)
    assert np.array_equal(state, features.astype(np.float32).T.reshape(-1))
    assert row["target_unit"] == OPS3_TARGET_UNIT
    assert row["target_delta"] == (
        row["target_candidate_value"] - row["target_reference_value"]
    )
    assert row["horizon"] == 0
    for field in ("persistence", "rate_bps", "marginal_power_w", "required_power_w"):
        assert np.array_equal(np.asarray(row[field]), np.zeros((3, NUM_ACTIONS)))


def test_target_adapter_declares_the_selected_pair_schema_not_temporal_c2():
    adapter = _load_adapter()
    assert adapter.OPS3_SELECTED_PAIR_SCHEMA == OPS3_SELECTED_PAIR_SCHEMA
    assert adapter.OPS3_TARGET_UNIT == OPS3_TARGET_UNIT


def test_active_target_adapter_has_no_legacy_temporal_import():
    source = ADAPTER_PATH.read_text(encoding="utf-8")
    assert "ee_axis_temporal_dataset" not in source
    assert "EEAxisTemporalDataset" not in source


def test_c2_trainer_has_an_explicit_already_normalized_target_path():
    source = HETERO_TRAINER_PATH.read_text(encoding="utf-8")
    assert "EEAxisV014NormalizedPairBatch" in source
    assert "already_normalized_target" in source
    assert "normalized_target_deltas" in source


def test_legacy_228_shared_pair_boundary_rejects_the_448_ops3_state():
    """The old state contract currently fails closed rather than truncating C2."""

    row = _ops3_row()
    batch = EEAxisPairBatch(
        states=np.asarray([row["q2_state"]], dtype=np.float32),
        reference_actions=np.asarray([row["reference_action"]], dtype=np.int64),
        candidate_actions=np.asarray([row["candidate_action"]], dtype=np.int64),
        target_surplus_bits=np.asarray([row["target_delta"]], dtype=np.float64),
        action_masks=np.asarray([row["action_mask"]], dtype=np.bool_),
    )
    with pytest.raises(ValueError, match="batch, 228"):
        batch.validate(state_dim=228, action_dim=NUM_ACTIONS)


def test_ops3_provider_orchestrator_three_updates_checkpoint_reload_and_masked_scores():
    """One synthetic, production-seam vertical slice with no replacement learner."""

    orchestrator_api = _load_orchestrator()
    q1 = EEAxisActionSharedConfig(
        state_dim=228, action_dim=28, hidden_layers=(100, 50, 50),
        activation="tanh", learning_rate=0.001, kappa_bits=10.0,
        beta=0.1, loss_weights=(1.0, 1.0, 1.0),
    )
    q2 = EEAxisV014HeadConfig(
        action_dim=28, local_feature_dim=16, global_feature_dim=0,
        hidden_layers=(100, 50, 50), activation="tanh", learning_rate=0.001,
        kappa_bits=10.0, beta=0.1,
    )
    config = orchestrator_api.V023FiveArmOrchestratorConfig(
        model_config=LCSRSThreeRouteConfig(q1=q1, q2=q2), train_seed=7,
        checkpoint_cadence_updates=3,
    )
    c1 = EEAxisPairBatch(
        states=np.zeros((1, 228), dtype=np.float32),
        reference_actions=np.asarray([0], dtype=np.int64),
        candidate_actions=np.asarray([1], dtype=np.int64),
        target_surplus_bits=np.asarray([1.0], dtype=np.float64),
        action_masks=np.ones((1, 28), dtype=np.bool_),
    )
    c2 = EEAxisV014NormalizedPairBatch(
        states=np.arange(448, dtype=np.float32).reshape(1, 448) / 100.0,
        reference_actions=np.asarray([0], dtype=np.int64),
        candidate_actions=np.asarray([1], dtype=np.int64),
        normalized_target_deltas=np.asarray([1.0], dtype=np.float64),
        action_masks=np.ones((1, 28), dtype=np.bool_),
    )
    context = np.zeros((2, 28, 29), dtype=np.float32)
    tokens = np.zeros((2, 28, 3, 38), dtype=np.float32)
    token_mask = np.zeros((2, 28, 3), dtype=np.bool_)
    token_mask[:, :, 2] = True
    tokens[:, :, 2, 1] = 1.0
    tokens[:, 1, 2, 2:5] = 1.0
    c3_view = assemble_c3_view(
        action_context=context, tokens=tokens, token_mask=token_mask,
        action_mask=np.ones((2, 28), dtype=np.bool_),
        reference_actions=np.asarray([0, 0], dtype=np.int64),
    )
    surface = assemble_lcsrs_anchor_surface(
        c3_view,
        [LCSRSPairTargets(
            pair_id="vertical", user_ids=np.asarray([0, 1], dtype=np.int64),
            action_ids=np.asarray([1, 1], dtype=np.int64),
            normalized_targets_by_draw=np.ones((LCSRS_DRAW_COUNT, 2), dtype=np.float64),
        )],
    )
    c3 = LCSRSC3SampledBatch(
        anchor_indices=np.asarray([0], dtype=np.int64),
        row_classes=np.asarray([LCSRS_ROW_REFERENCE], dtype=np.uint8),
        user_indices=np.asarray([0], dtype=np.int64), action_indices=np.asarray([0], dtype=np.int64),
        normalized_targets=np.asarray([0.0], dtype=np.float32),
    )

    class Provider:
        def __init__(self): self.cursor = 0
        def next_batch(self, *, route, source, update_cursor):
            assert update_cursor == self.cursor and route == ("C1", "C2", "C3")[self.cursor]
            if source == "informed": self.cursor += 1
            batch = {"C1": c1, "C2": c2, "C3": c3}[route]
            return orchestrator_api.ProvidedRouteBatch(
                route=route, source=source, file_id=f"{route}-{source}", batch=batch,
                c3_surfaces=(surface,) if route == "C3" else (),
            )
        def sampler_state(self): return {"cursor": self.cursor}
        def load_sampler_state(self, state): self.cursor = state["cursor"]

    provider = Provider()
    orchestrator = orchestrator_api.V023FiveArmLearnerOrchestrator(config, provider)
    assert [item.route for item in orchestrator.advance_many(3)] == ["C1", "C2", "C3"]
    state = orchestrator.checkpoint_state()
    reloaded = orchestrator_api.V023FiveArmLearnerOrchestrator(config, Provider())
    reloaded.load_checkpoint_state(state)
    model = reloaded.models["FULL"]
    snapshot = model.capture_q1_q2(
        np.zeros((2, 228), dtype=np.float32),
        q2_states=np.repeat(c2.states, 2, axis=0),
        q2_action_masks=np.repeat(c2.action_masks, 2, axis=0),
        native_observation_event_digest="a" * 64,
    )
    view = assemble_c3_view(
        action_context=context, tokens=tokens, token_mask=token_mask,
        action_mask=np.repeat(c2.action_masks, 2, axis=0),
        reference_actions=np.argmax(snapshot.q12, axis=1).astype(np.int64),
    )
    q1_scores, q2_scores, q3_scores = model.q_values(snapshot, view)
    actions = model.select_greedy_actions(snapshot, view)
    assert q1_scores.shape == q2_scores.shape == q3_scores.shape == (2, 28)
    assert c2.action_masks[0, actions[0]]
