"""Fast actual-current-class checks for the V0.23 paired C3 schedule."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from mcrl.runtime import ee_axis_lcsrs_c3_learner as learner_runtime
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_DRAW_COUNT,
    LCSRS_ROW_SUPPORTED,
    LCSRSAnchorRecord,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch
from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view


HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SCHEDULE = _load_module(
    "v023_c3_source_schedule_under_test", HERE / "v023_c3_source_schedule.py"
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _record(
    *,
    world: int,
    anchor: str,
    value: float,
    split_supported_strata: bool = False,
) -> LCSRSAnchorRecord:
    users, actions = 3, 28
    context = np.zeros((users, actions, 29), dtype=np.float32)
    tokens = np.zeros((users, actions, users + 1, 38), dtype=np.float32)
    action_mask = np.zeros((users, actions), dtype=np.bool_)
    action_mask[:, :3] = True
    token_mask = np.zeros((users, actions, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0
    tokens[0, 1, users, 2:5] = 1.0
    tokens[1, 1, users, 2:5] = 1.0
    context[0:2, 1, 3] = 1.0
    context[0:2, 1, 27] = np.float32(1.0 / users)
    if split_supported_strata:
        context[1, 1, 12] = 1.0
    q12 = np.zeros((users, actions), dtype=np.float64)
    q12[:, 1:] = -0.005
    context[:, :3, 23] = np.asarray(
        np.tanh(q12[:, :3] - q12[:, [0]]), dtype=np.float32
    )
    view = assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.zeros(users, dtype=np.int64),
    )
    draws = np.tile(
        np.asarray([[value, -value]], dtype=np.float64),
        (LCSRS_DRAW_COUNT, 1),
    )
    pair = LCSRSPairTargets(
        pair_id=f"{anchor}-pair",
        user_ids=np.asarray([0, 1], dtype=np.int64),
        action_ids=np.asarray([1, 1], dtype=np.int64),
        normalized_targets_by_draw=draws,
    )
    return LCSRSAnchorRecord(
        world_id=world,
        phase=1,
        anchor_id=anchor,
        surface=assemble_lcsrs_anchor_surface(view, (pair,)),
        q12_values=q12,
    )


def _records(*, split_supported_strata: bool = False) -> tuple[LCSRSAnchorRecord, ...]:
    return tuple(
        _record(
            world=world,
            anchor=f"world-{world}-phase-1",
            value=float(offset + 1),
            split_supported_strata=split_supported_strata,
        )
        for offset, world in enumerate(SCHEDULE.R7_WORLDS)
    )


def _binding(records: tuple[LCSRSAnchorRecord, ...]):
    return SCHEDULE.R7GoDecisionBinding(
        schema=SCHEDULE.R7_FINAL_SCHEMA,
        status=SCHEDULE.R7_FINAL_STATUS,
        integrity_status=SCHEDULE.R7_INTEGRITY_STATUS,
        c3_decision=SCHEDULE.R7_GO_DECISION,
        context_status="CONTEXT_DIAGNOSTICS_PASS",
        claim_ceiling=SCHEDULE.R7_CLAIM_CEILING,
        split=SCHEDULE.R7_SPLIT,
        worlds=SCHEDULE.R7_WORLDS,
        source_count=8,
        fit_count=48,
        composition_count=48,
        base_contract_sha256=SCHEDULE.R7_BASE_CONTRACT_SHA256,
        contract_sha256=SCHEDULE.R7_CONTRACT_SHA256,
        execution_addendum_sha256=SCHEDULE.R7_EXECUTION_ADDENDUM_SHA256,
        launch_decision_sha256=_digest("authenticated-r7-launch-decision"),
        code_manifest_sha256=_digest("authenticated-r7-code-manifest"),
        preflight_manifest_sha256=_digest("authenticated-r7-preflight"),
        launch_manifest_sha256=_digest("authenticated-r7-launch-manifest"),
        source_manifest_sha256=_digest("authenticated-r7-source-manifest"),
        gate_result_sha256=_digest("authenticated-r7-go-result"),
        record_panel_sha256=SCHEDULE.canonical_record_panel_sha256(records),
        test_split_opened=False,
        episode_training=False,
        scientific_claim=False,
        no_rescue=True,
        no_scientific_token_before_integrity=True,
    )


@pytest.fixture(scope="module")
def records() -> tuple[LCSRSAnchorRecord, ...]:
    return _records()


@pytest.fixture(scope="module")
def built(records: tuple[LCSRSAnchorRecord, ...]):
    return SCHEDULE.build_v023_c3_source_schedule(
        tuple(reversed(records)),
        r7_go=_binding(records),
        epoch_budget=100,
        schedule_seed=2026135301,
    )


def test_actual_typed_batches_share_draws_and_use_exact_arm_targets(
    built, records: tuple[LCSRSAnchorRecord, ...]
) -> None:
    assert built.records == records
    assert all(left is right for left, right in zip(built.surfaces, (r.surface for r in records)))
    assert len(built.informed_batches) == len(built.neutral_batches) == 100
    assert len(built.informed_targets_by_anchor) == len(records)
    assert len(built.neutral_targets_by_anchor) == len(records)
    saw_supported_difference = False

    for anchor, (record, informed_target, neutral_target) in enumerate(
        zip(
            built.records,
            built.informed_targets_by_anchor,
            built.neutral_targets_by_anchor,
            strict=True,
        )
    ):
        assert built.surfaces[anchor] is record.surface
        np.testing.assert_array_equal(informed_target, record.surface.normalized_targets)
        np.testing.assert_array_equal(
            neutral_target, built.matched_placebo.normalized_targets_by_anchor[anchor]
        )
        non_supported = record.surface.row_class != LCSRS_ROW_SUPPORTED
        np.testing.assert_array_equal(informed_target[non_supported], 0.0)
        np.testing.assert_array_equal(neutral_target[non_supported], 0.0)
        assert not informed_target.flags.writeable
        assert not neutral_target.flags.writeable
        saw_supported_difference |= bool(np.any(informed_target != neutral_target))
    assert saw_supported_difference

    for informed, neutral in zip(
        built.informed_batches, built.neutral_batches, strict=True
    ):
        assert type(informed) is type(neutral) is LCSRSC3SampledBatch
        for field in (
            "anchor_indices",
            "row_classes",
            "user_indices",
            "action_indices",
        ):
            np.testing.assert_array_equal(getattr(informed, field), getattr(neutral, field))
        for row, (anchor, row_class, user, action) in enumerate(
            zip(
                informed.anchor_indices.tolist(),
                informed.row_classes.tolist(),
                informed.user_indices.tolist(),
                informed.action_indices.tolist(),
                strict=True,
            )
        ):
            assert informed.normalized_targets[row] == (
                built.informed_targets_by_anchor[anchor][user, action]
            )
            assert neutral.normalized_targets[row] == (
                built.neutral_targets_by_anchor[anchor][user, action]
            )
            if row_class != int(LCSRS_ROW_SUPPORTED):
                assert informed.normalized_targets[row] == 0.0
                assert neutral.normalized_targets[row] == 0.0


def test_receipt_binds_every_surface_mapping_batch_gate_budget_seed_and_source(
    built,
) -> None:
    receipt = built.receipt
    seal = receipt.pop("receipt_sha256")
    assert seal == built.receipt_sha256 == SCHEDULE.canonical_sha256(receipt)
    assert len(receipt["records"]) == len(built.records)
    assert receipt["record_panel_sha256"] == built.record_panel_sha256
    assert receipt["gate_decision"]["c3_decision"] == SCHEDULE.R7_GO_DECISION
    assert receipt["gate_decision"]["contract_sha256"] == SCHEDULE.R7_CONTRACT_SHA256
    assert receipt["gate_decision"]["gate_result_sha256"] == _digest(
        "authenticated-r7-go-result"
    )
    assert receipt["matched_placebo"]["content_sha256"] == (
        built.matched_placebo.content_digest
    )
    assert receipt["matched_placebo"]["coverage"] == pytest.approx(1.0)
    assert receipt["matched_placebo"]["world_crossing_count"] == 0
    assert receipt["target_surfaces"]["neutral_lcsrs_anchor_surfaces_constructed"] is False
    assert receipt["source_training_epoch_budget"] == 100
    assert receipt["sampling"]["explicit_seed"] == 2026135301
    assert receipt["sampling"]["seed_domain"] == SCHEDULE.SCHEDULE_SEED_DOMAIN
    assert receipt["sampling"]["bit_generator"] == "PCG64"
    assert len(receipt["batch_schedule"]["entries"]) == 100
    assert receipt["batch_schedule"]["batch_count_by_source"] == {
        "informed": 100,
        "neutral": 100,
    }
    assert receipt["boundaries"] == {
        "simulator_run": False,
        "learner_update": False,
        "model_fit": False,
        "test_split_opened": False,
        "episode_training": False,
        "artifact_write": False,
    }
    assert built.informed_source_id != built.neutral_source_id
    assert built.source_id("informed") == receipt["sources"]["informed"]["source_id"]
    assert built.source_id("neutral") == receipt["sources"]["neutral"]["source_id"]


def test_exact_n_access_and_exhaustion_are_source_local(built) -> None:
    assert built.batch_for("informed", 99) is built.informed_batches[99]
    assert built.batch_for("neutral", 99) is built.neutral_batches[99]
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="exhausted"):
        built.batch_for("informed", 100)
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="exhausted"):
        built.batch_for("neutral", 100)
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="100 or 500"):
        SCHEDULE.build_v023_c3_source_schedule(
            built.records,
            r7_go=built.gate_decision,
            epoch_budget=99,
            schedule_seed=2026135301,
        )


def test_exact_500_epoch_budget_is_precomputed_and_exhausted(
    records: tuple[LCSRSAnchorRecord, ...]
) -> None:
    schedule = SCHEDULE.build_v023_c3_source_schedule(
        records,
        r7_go=_binding(records),
        epoch_budget=500,
        schedule_seed=500,
    )
    assert len(schedule.informed_batches) == 500
    assert len(schedule.neutral_batches) == 500
    assert len(schedule.receipt["batch_schedule"]["entries"]) == 500
    assert schedule.batch_for("informed", 499) is schedule.informed_batches[499]
    assert schedule.batch_for("neutral", 499) is schedule.neutral_batches[499]
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="exhausted"):
        schedule.batch_for("informed", 500)
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="exhausted"):
        schedule.batch_for("neutral", 500)


def test_deterministic_replay_and_domain_separated_seed(
    records: tuple[LCSRSAnchorRecord, ...]
) -> None:
    binding = _binding(records)
    first = SCHEDULE.build_v023_c3_source_schedule(
        records, r7_go=binding, epoch_budget=100, schedule_seed=77
    )
    replay = SCHEDULE.build_v023_c3_source_schedule(
        tuple(reversed(records)), r7_go=binding, epoch_budget=100, schedule_seed=77
    )
    changed_seed = SCHEDULE.build_v023_c3_source_schedule(
        records, r7_go=binding, epoch_budget=100, schedule_seed=78
    )
    assert first.canonical_receipt_bytes == replay.canonical_receipt_bytes
    assert first.receipt_sha256 == replay.receipt_sha256
    assert first.derived_pcg64_seed == replay.derived_pcg64_seed
    assert first.derived_pcg64_seed != 77
    assert first.paired_draw_schedule_sha256 == replay.paired_draw_schedule_sha256
    assert first.paired_draw_schedule_sha256 != changed_seed.paired_draw_schedule_sha256
    for left, right in zip(first.informed_batches, replay.informed_batches, strict=True):
        for field in (
            "anchor_indices",
            "row_classes",
            "user_indices",
            "action_indices",
            "normalized_targets",
        ):
            np.testing.assert_array_equal(getattr(left, field), getattr(right, field))


@pytest.mark.parametrize(
    ("patch", "message"),
    (
        ({"c3_decision": "STOP_OBSERVABILITY_R7"}, "c3_decision"),
        ({"status": "FROZEN_PRE_OUTCOME"}, "status"),
        ({"integrity_status": "INVALID"}, "integrity_status"),
        ({"test_split_opened": True}, "test_split_opened"),
        ({"episode_training": True}, "episode_training"),
        ({"split": "TEST"}, "split"),
        ({"worlds": tuple(range(2026121705, 2026121713))}, "worlds"),
        ({"contract_sha256": "0" * 64}, "contract_sha256"),
    ),
)
def test_rejects_non_go_test_and_gate_binding_drift(
    records: tuple[LCSRSAnchorRecord, ...], patch: dict[str, object], message: str
) -> None:
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match=message):
        SCHEDULE.build_v023_c3_source_schedule(
            records,
            r7_go=replace(_binding(records), **patch),
            epoch_budget=100,
            schedule_seed=1,
        )


def test_rejects_wrong_record_worlds_and_record_target_drift(
    records: tuple[LCSRSAnchorRecord, ...]
) -> None:
    binding = _binding(records)
    wrong_worlds = (
        *records[:-1],
        _record(world=2026121705, anchor="r6-world", value=9.0),
    )
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="exact R7 TRAIN worlds"):
        SCHEDULE.build_v023_c3_source_schedule(
            wrong_worlds,
            r7_go=binding,
            epoch_budget=100,
            schedule_seed=1,
        )

    drifted = (
        _record(
            world=records[0].world_id,
            anchor=records[0].anchor_id,
            value=99.0,
        ),
        *records[1:],
    )
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="record panel"):
        SCHEDULE.build_v023_c3_source_schedule(
            drifted,
            r7_go=binding,
            epoch_budget=100,
            schedule_seed=1,
        )


def test_rejects_global_placebo_coverage_below_frozen_threshold() -> None:
    low_coverage = _records(split_supported_strata=True)
    with pytest.raises(SCHEDULE.V023C3SourceScheduleError, match="coverage"):
        SCHEDULE.build_v023_c3_source_schedule(
            low_coverage,
            r7_go=_binding(low_coverage),
            epoch_budget=100,
            schedule_seed=1,
        )


def test_builder_never_calls_simulator_fit_or_learner_update(
    monkeypatch: pytest.MonkeyPatch, records: tuple[LCSRSAnchorRecord, ...]
) -> None:
    called: list[str] = []

    def forbidden(*_args, **_kwargs):
        called.append("forbidden")
        raise AssertionError("learner update or fit was called")

    monkeypatch.setattr(learner_runtime, "lcsrs_c3_training_step", forbidden)
    monkeypatch.setattr(learner_runtime, "fit_lcsrs_c3_source", forbidden)
    monkeypatch.setattr(learner_runtime, "make_lcsrs_c3_student", forbidden)
    result = SCHEDULE.build_v023_c3_source_schedule(
        records,
        r7_go=_binding(records),
        epoch_budget=100,
        schedule_seed=2,
    )
    assert called == []
    assert all(value is False for value in result.receipt["boundaries"].values())
    module_source = Path(SCHEDULE.__file__).read_text(encoding="utf-8")
    assert "from mcrl.env" not in module_source


def test_current_target_adapter_exposes_the_documented_neutral_override_seam(
    built,
) -> None:
    adapter = _load_module(
        "v023_target_batch_adapter_neutral_override_probe",
        SCRATCH / "multi-catfish-v023-target-batch-adapter" / "target_batch_adapter.py",
    )
    adapter.load_lcsrs_c3_inputs(built.surfaces, (built.informed_batches[0],))
    neutral_with_changed_label = next(
        batch
        for informed, batch in zip(
            built.informed_batches, built.neutral_batches, strict=True
        )
        if np.any(informed.normalized_targets != batch.normalized_targets)
    )
    with pytest.raises(adapter.V023TargetBatchAdapterError, match="target disagrees"):
        adapter.load_lcsrs_c3_inputs(built.surfaces, (neutral_with_changed_label,))


def test_receipt_bytes_are_canonical_ascii_and_self_sealed(built) -> None:
    payload = json.loads(built.canonical_receipt_bytes.decode("ascii"))
    assert built.canonical_receipt_bytes == SCHEDULE.canonical_bytes(payload)
    seal = payload.pop("receipt_sha256")
    assert seal == hashlib.sha256(SCHEDULE.canonical_bytes(payload)).hexdigest()
