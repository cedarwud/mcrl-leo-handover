"""W-48 -- strict V0.3 C2/Q2 temporal-pair adapter."""

from __future__ import annotations

from dataclasses import replace
import hashlib

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.runtime.ee_axis_state import (
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
)
from mcrl.runtime.ee_axis_temporal_pairs import (
    TEMPORAL_HORIZON_STEPS,
    TemporalPairContractError,
    build_temporal_pair,
    build_temporal_route_batch,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _trace() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    reference_rates = np.asarray(
        [[100.0, 50.0], [110.0, 45.0], [115.0, 48.0], [120.0, 50.0]],
        dtype=np.float64,
    )
    candidate_rates = np.asarray(
        [[100.0, 50.0], [125.0, 44.0], [130.0, 50.0], [118.0, 55.0]],
        dtype=np.float64,
    )
    reference_power = np.asarray([10.0, 10.5, 11.0, 11.5], dtype=np.float64)
    candidate_power = np.asarray([10.0, 10.0, 10.5, 11.0], dtype=np.float64)
    reference_served = np.ones((TEMPORAL_HORIZON_STEPS, 2), dtype=np.bool_)
    candidate_served = np.ones((TEMPORAL_HORIZON_STEPS, 2), dtype=np.bool_)
    return (
        reference_rates,
        candidate_rates,
        reference_power,
        candidate_power,
        reference_served,
        candidate_served,
    )


def _pair(**overrides):
    (
        reference_rates,
        candidate_rates,
        reference_power,
        candidate_power,
        reference_served,
        candidate_served,
    ) = _trace()
    values = dict(
        c2_policy_version="C2_V0.3B_HOLD_WHILE_LEGAL_MONOTONE_RELEASE",
        source_rule="incumbent-hold",
        anchor_sha256=digest("anchor"),
        anchor_schedule_sha256=digest("schedule"),
        seed=2026090101,
        step_index=10,
        source_manifest_sha256=digest("manifest"),
        checkpoint_sha256=digest("checkpoint"),
        common_random_field_sha256=digest("field"),
        forecast_payload_sha256=digest("forecast"),
        reference_trace_sha256=digest("reference-trace"),
        candidate_trace_sha256=digest("candidate-trace"),
        state_schema=EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=digest("state-observation"),
        focal_user=0,
        state=np.zeros(EE_AXIS_STATE_DIM, dtype=np.float32),
        action_mask=np.asarray([index in {3, 11} for index in range(NUM_ACTIONS)], dtype=np.bool_),
        reference_action=11,
        candidate_action=3,
        held_physical_key=(50123, 1),
        held_key_match_counts=(1, 1, 1, 1),
        release_offset=3,
        release_reason="horizon",
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=reference_power,
        candidate_system_power_w=candidate_power,
        reference_served=reference_served,
        candidate_served=candidate_served,
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        offset_surplus_bits=np.asarray([15.0, 18.0, 4.0], dtype=np.float64),
        zeta2_temporal_surplus_bits=37.0,
    )
    values.update(overrides)
    return build_temporal_pair(**values)


def test_valid_temporal_pair_is_q2_only_and_converts_to_common_pair_batch():
    pair = _pair()

    assert pair.source_route == "C2"
    assert pair.state.shape == (EE_AXIS_STATE_DIM,)
    assert pair.zeta2_temporal_surplus_bits == pytest.approx(37.0)
    assert pair.verify() == pair.comparison_sha256

    batch = build_temporal_route_batch([pair])
    assert batch.route == "C2"
    assert batch.pair_batch.states.shape == (1, EE_AXIS_STATE_DIM)
    assert batch.pair_batch.reference_actions.tolist() == [11]
    assert batch.pair_batch.candidate_actions.tolist() == [3]
    assert batch.pair_batch.target_surplus_bits.tolist() == [37.0]
    assert batch.verify() == batch.batch_sha256


def test_z2_and_each_downstream_surplus_are_recomputed_from_raw_trace():
    with pytest.raises(TemporalPairContractError, match="offset surplus"):
        _pair(offset_surplus_bits=np.asarray([15.0, 18.0, -1.0]))

    with pytest.raises(TemporalPairContractError, match="zeta2|temporal surplus"):
        _pair(zeta2_temporal_surplus_bits=31.0)


@pytest.mark.parametrize(
    "field, value, pattern",
    [
        ("state", np.zeros(EE_AXIS_STATE_DIM - 1, dtype=np.float32), "228"),
        ("state_schema", "multi-catfish-mcrl-v03-causal-state-v1", "state schema"),
        ("state_schema_sha256", "f" * 64, "state schema digest"),
        ("action_mask", np.zeros(NUM_ACTIONS, dtype=np.int64), "Boolean"),
        ("reference_action", 4, "reference_action"),
        ("candidate_action", 11, "differ"),
    ],
)
def test_stale_or_invalid_state_and_action_lineage_fails_closed(field, value, pattern):
    with pytest.raises(TemporalPairContractError, match=pattern):
        _pair(**{field: value})


def test_release_metadata_and_support_counts_are_causal_and_complete():
    with pytest.raises(TemporalPairContractError, match="support-expired"):
        _pair(release_reason="support_expired", release_offset=3)

    with pytest.raises(TemporalPairContractError, match="first support loss"):
        _pair(
            held_key_match_counts=(1, 1, 1, 0),
            release_offset=2,
            release_reason="support_expired",
        )

    with pytest.raises(TemporalPairContractError, match="hold support"):
        _pair(
            held_key_match_counts=(1, 0, 0, 0),
            release_offset=2,
            release_reason="support_expired",
        )

    # A support-expired row may report zero support after the latched release;
    # those counts are observations, not a claim that the candidate reacquired
    # the held key.
    assert _pair(
        held_key_match_counts=(1, 1, 0, 0),
        release_offset=2,
        release_reason="support_expired",
    ).verify()
    # Reappearance of the physical key is also allowed: the release latch is
    # proven by the runner's executed-action trace, not by support-count data.
    assert _pair(
        held_key_match_counts=(1, 1, 0, 1),
        release_offset=2,
        release_reason="support_expired",
    ).verify()


def test_trace_and_provenance_digest_fields_are_required_and_bound():
    with pytest.raises(TemporalPairContractError, match="SHA-256"):
        _pair(candidate_trace_sha256="not-a-digest")

    pair = _pair()
    with pytest.raises(TemporalPairContractError, match="disagrees"):
        replace(pair, zeta2_temporal_surplus_bits=123.0).verify()


def test_arrays_are_owned_read_only_and_batch_rejects_duplicate_rows():
    pair = _pair()
    assert not pair.state.flags.writeable
    assert not pair.reference_rates_bps.flags.writeable
    with pytest.raises(ValueError):
        pair.state[0] = 1.0

    with pytest.raises(TemporalPairContractError, match="duplicate"):
        build_temporal_route_batch([pair, pair])

    batch = build_temporal_route_batch([pair])
    tampered = batch.pair_batch.target_surplus_bits.copy()
    tampered[0] = -999.0
    tampered_batch = replace(
        batch,
        pair_batch=replace(batch.pair_batch, target_surplus_bits=tampered),
    )
    with pytest.raises(TemporalPairContractError, match="must be immutable"):
        tampered_batch.verify()
