"""Fast actual-class checks for the V0.23 provider/orchestrator bridge."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRSThreeRouteConfig


HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# The sibling fixture writes a tiny *authenticated* C1/C2 target root with the
# production dataset writers.  It is test-only data; the bridge never creates
# an artifact or translates JSON itself.
TARGET_FIXTURE = _load_module(
    "v023_target_batch_adapter_fixture_for_provider_bridge",
    SCRATCH
    / "multi-catfish-v023-target-batch-adapter"
    / "test_target_batch_adapter.py",
)
BRIDGE = _load_module(
    "v023_provider_orchestrator_bridge_under_test",
    HERE / "v023_provider_orchestrator_bridge.py",
)
ORCHESTRATOR = BRIDGE._ORCHESTRATOR


def _c3_binding(
    source: str,
    *,
    epochs: int = 1,
    normalized_targets_by_anchor: tuple[np.ndarray, ...] | None = None,
) -> object:
    base = TARGET_FIXTURE._c3_inputs()
    selected = normalized_targets_by_anchor
    batches = base.sampled_batches * epochs
    if selected is not None:
        batches = tuple(
            replace(
                batch,
                normalized_targets=np.asarray(
                    [
                        selected[int(anchor)][int(user), int(action)]
                        for anchor, user, action in zip(
                            batch.anchor_indices.tolist(),
                            batch.user_indices.tolist(),
                            batch.action_indices.tolist(),
                            strict=True,
                        )
                    ],
                    dtype=np.float32,
                ),
            )
            for batch in batches
        )
    return BRIDGE.C3SourceBinding(
        source=source,
        source_id=f"fixture-c3-{source}-source-artifact-v1",
        inputs=BRIDGE.load_lcsrs_c3_inputs(
            base.surfaces,
            batches,
            normalized_targets_by_anchor=selected,
        ),
    )


def _provider(tmp_path: Path, *, epochs: int = 1):
    artifact = BRIDGE.load_completed_target_artifact(
        TARGET_FIXTURE._write_artifact(tmp_path / "authenticated-targets")
    )
    neutral = _c3_binding("neutral", epochs=epochs)
    informed = _c3_binding("informed", epochs=epochs)
    return (
        BRIDGE.V023ProviderOrchestratorBridge(
            artifact,
            c3_neutral=neutral,
            c3_informed=informed,
            planned_source_training_epochs=epochs,
        ),
        artifact,
        neutral,
        informed,
    )


def _config() -> LCSRSThreeRouteConfig:
    return LCSRSThreeRouteConfig(
        q12=EEAxisActionSharedConfig(
            state_dim=228,
            action_dim=28,
            hidden_layers=(8,),
            activation="relu",
            learning_rate=1.0e-2,
            kappa_bits=10.0,
            beta=0.2,
            loss_weights=(1.0, 2.0, 3.0),
        )
    )


def _provided_signature(provided: object) -> tuple[object, ...]:
    assert isinstance(provided, BRIDGE.ProvidedRouteBatch)
    if provided.route in {"C1", "C2"}:
        batch = provided.batch
        return (
            provided.route,
            provided.source,
            provided.file_id,
            tuple(np.asarray(batch.states).tobytes() for _ in range(1)),
            np.asarray(batch.reference_actions).tobytes(),
            np.asarray(batch.candidate_actions).tobytes(),
            np.asarray(batch.target_surplus_bits).tobytes(),
            np.asarray(batch.action_masks).tobytes(),
        )
    batch = provided.batch
    return (
        provided.route,
        provided.source,
        provided.file_id,
        np.asarray(batch.anchor_indices).tobytes(),
        np.asarray(batch.row_classes).tobytes(),
        np.asarray(batch.user_indices).tobytes(),
        np.asarray(batch.action_indices).tobytes(),
        np.asarray(batch.normalized_targets).tobytes(),
        tuple(surface.content_digest for surface in provided.c3_surfaces),
    )


def _next_cycle_tail(provider: object) -> tuple[object, ...]:
    return (
        provider.next_batch(route="C2", source="neutral", update_cursor=1),
        provider.next_batch(route="C2", source="informed", update_cursor=1),
        provider.next_batch(route="C3", source="neutral", update_cursor=2),
        provider.next_batch(route="C3", source="informed", update_cursor=2),
    )


def test_actual_authenticated_inputs_satisfy_protocol_and_consume_one_full_cycle(tmp_path):
    provider, _artifact, _neutral, _informed = _provider(tmp_path)
    assert isinstance(provider, BRIDGE.DeterministicRouteBatchProvider)
    learner = ORCHESTRATOR.V023FiveArmLearnerOrchestrator(
        ORCHESTRATOR.V023FiveArmOrchestratorConfig(
            model_config=_config(), train_seed=73
        ),
        provider,
    )

    receipts = learner.advance_many(3)
    assert [receipt.route for receipt in receipts] == ["C1", "C2", "C3"]
    assert receipts[0].source_files[0][1].startswith("c1-neutral-panel-")
    assert receipts[0].source_files[1][1].startswith("c1-informed-panel-")
    assert receipts[1].source_files[0][1].startswith("c2-neutral-panel-")
    assert receipts[1].source_files[1][1].startswith("c2-informed-panel-")
    assert receipts[2].source_files == (
        ("neutral", "fixture-c3-neutral-source-artifact-v1"),
        ("informed", "fixture-c3-informed-source-artifact-v1"),
    )
    for receipt in receipts:
        assert [(item.arm, item.source) for item in receipt.arm_updates] == [
            (arm, ORCHESTRATOR.SOURCE_ABLATION_MAP[arm][receipt.route])
            for arm in ORCHESTRATOR.ARMS
        ]


def test_route_and_source_cursors_are_isolated_and_requests_cannot_be_retagged(tmp_path):
    provider, _artifact, _neutral, _informed = _provider(tmp_path)
    provider.next_batch(route="C1", source="neutral", update_cursor=0)
    state = provider.sampler_state()
    assert state["cursors"] == {
        "C1:neutral": 1,
        "C1:informed": 0,
        "C2:neutral": 0,
        "C2:informed": 0,
        "C3:neutral": 0,
        "C3:informed": 0,
    }
    provider.next_batch(route="C1", source="informed", update_cursor=0)
    provider.next_batch(route="C2", source="neutral", update_cursor=1)
    state = provider.sampler_state()
    assert state["cursors"]["C1:neutral"] == state["cursors"]["C1:informed"] == 1
    assert state["cursors"]["C2:neutral"] == 1
    assert state["cursors"]["C2:informed"] == 0
    assert state["cursors"]["C3:neutral"] == state["cursors"]["C3:informed"] == 0

    with pytest.raises(BRIDGE.V023ProviderBridgeError, match="route/source cursor order"):
        provider.next_batch(route="C3", source="neutral", update_cursor=2)


def test_sampler_state_round_trip_returns_bit_identical_c1_c2_c3_batches(tmp_path):
    provider, artifact, _neutral, _informed = _provider(tmp_path)
    provider.next_batch(route="C1", source="neutral", update_cursor=0)
    provider.next_batch(route="C1", source="informed", update_cursor=0)
    checkpoint = provider.sampler_state()

    expected = _next_cycle_tail(provider)
    expected_state = provider.sampler_state()

    resumed = BRIDGE.V023ProviderOrchestratorBridge(
        artifact,
        c3_neutral=_c3_binding("neutral"),
        c3_informed=_c3_binding("informed"),
        planned_source_training_epochs=1,
    )
    resumed.load_sampler_state(checkpoint)
    actual = _next_cycle_tail(resumed)
    assert [_provided_signature(item) for item in actual] == [
        _provided_signature(item) for item in expected
    ]
    assert resumed.sampler_state() == expected_state


def test_missing_or_aliased_c3_identities_fail_closed(tmp_path):
    artifact = BRIDGE.load_completed_target_artifact(
        TARGET_FIXTURE._write_artifact(tmp_path / "authenticated-targets")
    )
    with pytest.raises(BRIDGE.V023ProviderBridgeError, match="must be distinct"):
        BRIDGE.V023ProviderOrchestratorBridge(
            artifact,
            c3_neutral=BRIDGE.C3SourceBinding(
                source="neutral",
                source_id="one-c3-source",
                inputs=TARGET_FIXTURE._c3_inputs(),
            ),
            c3_informed=BRIDGE.C3SourceBinding(
                source="informed",
                source_id="one-c3-source",
                inputs=TARGET_FIXTURE._c3_inputs(),
            ),
            planned_source_training_epochs=1,
        )
    with pytest.raises(TypeError, match="V023C3Inputs"):
        BRIDGE.V023ProviderOrchestratorBridge(
            artifact,
            c3_neutral=BRIDGE.C3SourceBinding(
                source="neutral", source_id="c3-neutral", inputs=object()
            ),
            c3_informed=_c3_binding("informed"),
            planned_source_training_epochs=1,
        )


def test_returned_typed_batches_do_not_share_mutable_storage_with_sources(tmp_path):
    provider, _artifact, neutral, _informed = _provider(tmp_path)
    c1 = provider.next_batch(route="C1", source="neutral", update_cursor=0)
    source_c1 = provider._entries[("C1", "neutral")][0].batch
    assert isinstance(c1.batch, type(source_c1))
    for field in (
        "states",
        "reference_actions",
        "candidate_actions",
        "target_surplus_bits",
        "action_masks",
    ):
        returned = np.asarray(getattr(c1.batch, field))
        original = np.asarray(getattr(source_c1, field))
        assert not returned.flags.writeable
        assert not np.shares_memory(returned, original)

    provider.next_batch(route="C1", source="informed", update_cursor=0)
    provider.next_batch(route="C2", source="neutral", update_cursor=1)
    provider.next_batch(route="C2", source="informed", update_cursor=1)
    c3 = provider.next_batch(route="C3", source="neutral", update_cursor=2)
    source_c3 = neutral.inputs.sampled_batches[0]
    for field in (
        "anchor_indices",
        "row_classes",
        "user_indices",
        "action_indices",
        "normalized_targets",
    ):
        returned = np.asarray(getattr(c3.batch, field))
        original = np.asarray(getattr(source_c3, field))
        assert not returned.flags.writeable
        assert not np.shares_memory(returned, original)


def test_full_panels_repeat_for_exact_declared_epochs_then_exhaust(tmp_path):
    provider, artifact, _neutral, _informed = _provider(tmp_path, epochs=2)
    learner = ORCHESTRATOR.V023FiveArmLearnerOrchestrator(
        ORCHESTRATOR.V023FiveArmOrchestratorConfig(
            model_config=_config(), train_seed=73
        ),
        provider,
    )
    receipts = learner.advance_many(6)
    assert learner.completed_source_training_epochs == 2
    assert receipts[0].source_files == receipts[3].source_files
    assert receipts[1].source_files == receipts[4].source_files
    state = provider.sampler_state()
    assert state["planned_source_training_epochs"] == 2
    for route in ("C1", "C2", "C3"):
        for source in ("neutral", "informed"):
            assert state["cursors"][f"{route}:{source}"] == 2
    with pytest.raises(BRIDGE.V023ProviderBridgeError, match="schedule exhausted"):
        learner.advance()

    for route in ("C1", "C2"):
        for source in ("neutral", "informed"):
            inputs = artifact.for_mode(source)
            expected = inputs.c1_pair_batch if route == "C1" else inputs.c2_pair_batch
            actual = provider._entries[(route, source)][0].batch
            assert np.asarray(actual.states).shape == np.asarray(expected.states).shape


def test_c3_schedule_must_cover_declared_epoch_budget(tmp_path):
    artifact = BRIDGE.load_completed_target_artifact(
        TARGET_FIXTURE._write_artifact(tmp_path / "authenticated-targets")
    )
    with pytest.raises(BRIDGE.V023ProviderBridgeError, match="count must equal"):
        BRIDGE.V023ProviderOrchestratorBridge(
            artifact,
            c3_neutral=_c3_binding("neutral", epochs=1),
            c3_informed=_c3_binding("informed", epochs=1),
            planned_source_training_epochs=2,
        )


def test_formal_100_epoch_schedule_reaches_one_checkpoint_without_exhaustion(tmp_path):
    provider, _artifact, _neutral, _informed = _provider(tmp_path, epochs=100)
    learner = ORCHESTRATOR.V023FiveArmLearnerOrchestrator(
        ORCHESTRATOR.V023FiveArmOrchestratorConfig.formal(
            model_config=_config(), train_seed=73
        ),
        provider,
    )
    learner.advance_many(300)
    assert learner.completed_source_training_epochs == 100
    assert learner.checkpoint_due()
    checkpoint = learner.checkpoint_state()
    assert checkpoint["completed_source_training_epochs"] == 100
    assert checkpoint["provider_sampler_state"]["planned_source_training_epochs"] == 100


def test_c3_provider_revalidates_and_retains_neutral_target_selection(tmp_path):
    base = TARGET_FIXTURE._c3_inputs()
    selected = np.array(
        base.surfaces[0].normalized_targets, dtype=np.float32, copy=True, order="C"
    )
    selected[base.surfaces[0].row_class == 3] = np.float32(0.25)
    artifact = BRIDGE.load_completed_target_artifact(
        TARGET_FIXTURE._write_artifact(tmp_path / "authenticated-targets")
    )
    neutral = _c3_binding("neutral", normalized_targets_by_anchor=(selected,))
    informed = _c3_binding("informed")
    provider = BRIDGE.V023ProviderOrchestratorBridge(
        artifact,
        c3_neutral=neutral,
        c3_informed=informed,
        planned_source_training_epochs=1,
    )
    entry = provider._entries[("C3", "neutral")][0]
    assert np.array_equal(entry.c3_targets[0], selected)
    assert not np.shares_memory(entry.c3_targets[0], selected)
    for _route, _source, _cursor in (
        ("C1", "neutral", 0),
        ("C1", "informed", 0),
        ("C2", "neutral", 1),
        ("C2", "informed", 1),
    ):
        provider.next_batch(route=_route, source=_source, update_cursor=_cursor)
    provided = provider.next_batch(route="C3", source="neutral", update_cursor=2)
    assert np.array_equal(provided.batch.normalized_targets, entry.batch.normalized_targets)
    assert np.array_equal(provided.c3_surfaces[0].normalized_targets, base.surfaces[0].normalized_targets)
