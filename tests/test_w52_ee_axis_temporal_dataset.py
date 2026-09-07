"""W-52 -- deterministic, raw-trace-preserving C2 D^t persistence."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from mcrl.runtime.ee_axis_temporal_dataset import (
    EEAxisTemporalDataset,
    TemporalDatasetContractError,
    read_temporal_dataset,
    write_temporal_dataset,
)
from mcrl.runtime.ee_axis_temporal_pairs import build_temporal_pair


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _pair(
    *,
    label: str = "a",
    step_index: int = 10,
    source_manifest_sha256: str | None = None,
):
    reference_rates = np.asarray(
        [[100.0, 50.0], [110.0, 45.0], [115.0, 48.0], [120.0, 50.0]],
        dtype=np.float64,
    )
    candidate_rates = np.asarray(
        [[100.0, 50.0], [125.0, 44.0], [130.0, 50.0], [118.0, 55.0]],
        dtype=np.float64,
    )
    return build_temporal_pair(
        c2_policy_version="C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE",
        source_rule="incumbent-hold",
        anchor_sha256=_digest(f"anchor-{label}"),
        anchor_schedule_sha256=_digest(f"schedule-{label}"),
        seed=2026090101,
        step_index=step_index,
        source_manifest_sha256=(
            _digest("manifest")
            if source_manifest_sha256 is None
            else source_manifest_sha256
        ),
        checkpoint_sha256=_digest("checkpoint"),
        common_random_field_sha256=_digest(f"field-{label}"),
        forecast_payload_sha256=_digest(f"forecast-{label}"),
        reference_trace_sha256=_digest(f"reference-{label}"),
        candidate_trace_sha256=_digest(f"candidate-{label}"),
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=_digest(f"state-{label}"),
        focal_user=0,
        state=np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32),
        action_mask=np.asarray(
            [index in {3, 11} for index in range(NUM_ACTIONS)], dtype=np.bool_
        ),
        reference_action=11,
        candidate_action=3,
        held_physical_key=(50123, 1),
        held_key_match_counts=(1, 1, 1, 1),
        release_offset=3,
        release_reason="horizon",
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=np.asarray([10.0, 10.5, 11.0, 11.5]),
        candidate_system_power_w=np.asarray([10.0, 10.0, 10.5, 11.0]),
        reference_served=np.ones((4, 2), dtype=np.bool_),
        candidate_served=np.ones((4, 2), dtype=np.bool_),
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        offset_surplus_bits=np.asarray([15.0, 18.0, 4.0]),
        zeta2_temporal_surplus_bits=37.0,
    )


def test_temporal_dataset_round_trip_preserves_raw_rows_and_q2_batch(tmp_path):
    first = _pair(label="a", step_index=10)
    second = _pair(label="b", step_index=11)
    dataset = EEAxisTemporalDataset.from_pairs([second, first])
    destination = tmp_path / "dt.json"

    write_temporal_dataset(destination, dataset)
    restored = read_temporal_dataset(destination)

    assert restored.verify() == dataset.verify()
    assert [row.comparison_sha256 for row in restored.rows] == sorted(
        [first.comparison_sha256, second.comparison_sha256]
    )
    assert restored.route_batch().route == "C2"
    assert restored.route_batch().pair_batch.states.shape == (2, EE_AXIS_STATE_DIM)
    assert restored.route_batch().pair_batch.target_surplus_bits.tolist() == [37.0, 37.0]


def test_temporal_dataset_rejects_duplicates_and_mixed_lineage():
    pair = _pair()
    with pytest.raises(TemporalDatasetContractError, match="duplicate"):
        EEAxisTemporalDataset.from_pairs([pair, pair])
    with pytest.raises(TemporalDatasetContractError, match="source manifests"):
        EEAxisTemporalDataset.from_pairs(
            [pair, _pair(label="b", source_manifest_sha256=_digest("other"))]
        )


def test_temporal_dataset_is_write_once_and_detects_tampering(tmp_path):
    destination = tmp_path / "dt.json"
    dataset = EEAxisTemporalDataset.from_pairs([_pair()])
    write_temporal_dataset(destination, dataset)
    with pytest.raises(TemporalDatasetContractError, match="write-once"):
        write_temporal_dataset(destination, dataset)

    payload = json.loads(destination.read_text(encoding="ascii"))
    payload["rows"][0]["zeta2_temporal_surplus_bits"] = float(99.0).hex()
    destination.write_text(json.dumps(payload), encoding="ascii")
    with pytest.raises(TemporalDatasetContractError, match="digest"):
        read_temporal_dataset(destination)
