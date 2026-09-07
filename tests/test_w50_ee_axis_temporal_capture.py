"""W-50 -- pre-forecast C2 capture and complete Q2 pair materialization."""

from __future__ import annotations

from types import SimpleNamespace
import hashlib

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
import mcrl.runtime.ee_axis_temporal_capture as capture_module
from mcrl.runtime.ee_axis_temporal_capture import (
    TemporalCaptureContractError,
    capture_temporal_anchor,
    materialize_temporal_pair,
)
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    _matrix_sha256,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _slot_table(*, duplicate_candidate: bool = False) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    norads[11], cells[11], mask[11] = 50123, 1, True
    norads[3], cells[3], mask[3] = 50234, 2, True
    if duplicate_candidate:
        norads[4], cells[4], mask[4] = 50234, 2, True
    return SlotTable(norads, cells, mask)


class _State:
    def __init__(self, value: float = 0.0, users: int = 2) -> None:
        self.schema = EE_AXIS_STATE_SCHEMA
        self.schema_sha256 = EE_AXIS_STATE_SCHEMA_SHA256
        self.state_matrix = np.full((users, EE_AXIS_STATE_DIM), value, dtype=np.float32)
        self.action_masks = np.asarray(
            [[index in {3, 11} for index in range(NUM_ACTIONS)] for _ in range(users)],
            dtype=np.bool_,
        )
        self.state_sha256 = _matrix_sha256(self.state_matrix, self.action_masks)

    def verify(self) -> str:
        return self.state_sha256


def _prepared(*, duplicate_candidate: bool = False):
    observation = SimpleNamespace(
        num_users=2,
        step_index=10,
        candidates=SimpleNamespace(
            slot_tables=tuple(
                _slot_table(duplicate_candidate=duplicate_candidate) for _ in range(2)
            )
        ),
    )
    anchor = SimpleNamespace(
        wrapped=SimpleNamespace(environment=object()),
        observation=observation,
        focal_user=0,
        main_actions=(11, 11),
        anchor_sha256=digest("anchor"),
        evaluation_seed=2026090101,
        checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward"),
    )
    return SimpleNamespace(
        anchor=anchor,
        candidate_key=(50234, 2),
        source_rule="incumbent-hold",
        gate=SimpleNamespace(phase="anchor"),
        build=None,
        reference_trace=(),
        candidate_trace=(),
        forecast_rng_state={
            "fading_field_receipt": {
                "mode": "keyed-branch-independent-v1",
                "root_digest": digest("field"),
            }
        },
    )


def _state_encoder(monkeypatch, state: _State) -> None:
    monkeypatch.setattr(capture_module, "encode_ee_axis_state", lambda *_args: state)


def _traces():
    reference_rates = np.asarray(
        [[100.0, 50.0], [110.0, 45.0], [115.0, 48.0], [120.0, 50.0]],
        dtype=np.float64,
    )
    candidate_rates = np.asarray(
        [[100.0, 50.0], [125.0, 44.0], [130.0, 50.0], [118.0, 55.0]],
        dtype=np.float64,
    )
    reference_power = [10.0, 10.5, 11.0, 11.5]
    candidate_power = [10.0, 10.0, 10.5, 11.0]
    reference = tuple(
        SimpleNamespace(
            offset=offset,
            link_rate_bps=reference_rates[offset].tolist(),
            system_power_w=reference_power[offset],
            served=[True, True],
        )
        for offset in range(4)
    )
    candidate = tuple(
        SimpleNamespace(
            offset=offset,
            link_rate_bps=candidate_rates[offset].tolist(),
            system_power_w=candidate_power[offset],
            served=[True, True],
            held_physical_key=(50234, 2),
            held_key_match_count=1,
            release_offset=3,
            release_reason="horizon",
        )
        for offset in range(4)
    )
    return reference, candidate


def _build(prepared, reference, candidate):
    anchor = prepared.anchor
    authority = SimpleNamespace(
        anchor_sha256=anchor.anchor_sha256,
        reference_checkpoint_sha256=anchor.checkpoint_sha256,
        environment_source_sha256=anchor.environment_source_sha256,
        reward_source_sha256=anchor.reward_source_sha256,
        forecast_payload_sha256=digest("forecast"),
    )
    certificate = SimpleNamespace(
        version="C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE",
        reference_action=11,
        candidate_action=3,
        reference_key=(50123, 1),
        candidate_key=(50234, 2),
        release_offset=3,
        release_reason="horizon",
    )
    return SimpleNamespace(
        authority=authority,
        certificate=certificate,
        reference_trace_sha256=digest("reference-trace"),
        candidate_trace_sha256=digest("candidate-trace"),
        forecast_payload_sha256=digest("forecast"),
    )


def _complete(prepared, capture, monkeypatch):
    reference, candidate = _traces()
    build = _build(prepared, reference, candidate)
    prepared.reference_trace = reference
    prepared.candidate_trace = candidate
    prepared.build = build
    prepared.gate.phase = "forecast_complete"
    pair = materialize_temporal_pair(
        capture,
        prepared,
        lambda_bits_per_j=2.0,
        interval_s=1.0,
    )
    return pair


def test_capture_is_pre_forecast_and_materializes_q2_from_offsets_one_to_three(monkeypatch):
    prepared = _prepared()
    state = _State()
    _state_encoder(monkeypatch, state)
    anchor_capture = capture_temporal_anchor(
        prepared,
        anchor_schedule_sha256=digest("schedule"),
        source_manifest_sha256=digest("manifest"),
    )
    assert anchor_capture.state.shape == (EE_AXIS_STATE_DIM,)
    assert anchor_capture.reference_action == 11
    assert anchor_capture.candidate_action == 3

    pair = _complete(prepared, anchor_capture, monkeypatch)
    # Offset zero has no effect on zeta2.  The downstream surplus is
    # 15 + 18 + 4 = 37 bits under the fixed multiplier.
    assert pair.offset_surplus_bits.tolist() == pytest.approx([15.0, 18.0, 4.0])
    assert pair.zeta2_temporal_surplus_bits == pytest.approx(37.0)
    assert pair.as_pair_batch().states.shape == (1, EE_AXIS_STATE_DIM)


def test_capture_rejects_nonunique_candidate_physical_slot(monkeypatch):
    prepared = _prepared(duplicate_candidate=True)
    monkeypatch.setattr(capture_module, "encode_ee_axis_state", lambda *_args: _State())
    with pytest.raises(TemporalCaptureContractError, match="non-unique"):
        capture_temporal_anchor(
            prepared,
            anchor_schedule_sha256=digest("schedule"),
            source_manifest_sha256=digest("manifest"),
        )


def test_capture_rejects_after_forecast_and_materialization_rejects_stale_state(monkeypatch):
    prepared = _prepared()
    state = _State()
    _state_encoder(monkeypatch, state)
    anchor_capture = capture_temporal_anchor(
        prepared,
        anchor_schedule_sha256=digest("schedule"),
        source_manifest_sha256=digest("manifest"),
    )
    prepared.gate.phase = "forecast_complete"
    with pytest.raises(TemporalCaptureContractError, match="before C2 forecast"):
        capture_temporal_anchor(
            prepared,
            anchor_schedule_sha256=digest("schedule"),
            source_manifest_sha256=digest("manifest"),
        )

    reference, candidate = _traces()
    prepared.reference_trace = reference
    prepared.candidate_trace = candidate
    prepared.build = _build(prepared, reference, candidate)
    stale = _State(1.0)
    _state_encoder(monkeypatch, stale)
    with pytest.raises(TemporalCaptureContractError, match="stale"):
        materialize_temporal_pair(
            anchor_capture,
            prepared,
            lambda_bits_per_j=2.0,
            interval_s=1.0,
        )


def test_materialization_rejects_incomplete_or_unkeyed_forecast(monkeypatch):
    prepared = _prepared()
    # Capture uses the lightweight fake encoder only to isolate this contract
    # test from the simulator/TLE archive.
    monkeypatch.setattr(capture_module, "encode_ee_axis_state", lambda *_args: _State())
    anchor_capture = capture_temporal_anchor(
        prepared,
        anchor_schedule_sha256=digest("schedule"),
        source_manifest_sha256=digest("manifest"),
    )
    reference, candidate = _traces()
    prepared.reference_trace = reference[:-1]
    prepared.candidate_trace = candidate
    prepared.build = _build(prepared, reference, candidate)
    prepared.gate.phase = "forecast_complete"
    with pytest.raises(TemporalCaptureContractError, match="complete ordered offsets"):
        materialize_temporal_pair(
            anchor_capture,
            prepared,
            lambda_bits_per_j=2.0,
            interval_s=1.0,
        )
    prepared.reference_trace = reference
    prepared.candidate_trace = candidate
    prepared.forecast_rng_state = {"fading_field_receipt": {"mode": "disabled"}}
    with pytest.raises(TemporalCaptureContractError, match="keyed common-random"):
        materialize_temporal_pair(
            anchor_capture,
            prepared,
            lambda_bits_per_j=2.0,
            interval_s=1.0,
        )
