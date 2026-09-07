from __future__ import annotations

import hashlib
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_stage0_receipt_adapter as ADAPTER  # noqa: E402
import c2_temporal_fork_core as C2  # noqa: E402


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def authority():
    return C2.ForecastAuthority(
        schema=C2.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=digest("anchor"),
        reference_checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward"),
        live_rng_state_sha256=digest("live"),
        forecast_rng_state_sha256=digest("forecast"),
        forecast_request_sha256=digest("forecast-request"),
        forecast_payload_sha256=digest("forecast-payload"),
        forecast_namespace="c2-v03/stage0-bridge-fixture",
        fading_mode="disabled",
        generated_preoutcome=True,
        adapter_version="stage0-bridge-v1",
    )


def bindings():
    return (
        C2.ActionBinding(3, (56355, 30)),
        C2.ActionBinding(11, (56355, 31)),
    )


def replay_lineage():
    return ADAPTER.LegacyReplayLineage(
        opening_state_sha256=digest("opening-state"),
        opening_mask_sha256=digest("opening-mask"),
        reference_branch_trace_sha256=digest("reference-trace"),
        candidate_branch_trace_sha256=digest("candidate-trace"),
    )


def receipt(**changes):
    value = SimpleNamespace(
        focal_user=10,
        incumbent_id=(56355, 29),
        reference_departure_id=(56355, 31),
        candidate_id=(56355, 30),
        certified=True,
        first_failed_layer=None,
        reasons=(),
        hold_system_r2_delta=0.5,
        full_system_r2_delta=0.5,
        reference_energy_j=100.0,
        candidate_energy_j=90.0,
        reference_useful_bits=1000.0,
        candidate_useful_bits=1000.0,
        beam_pulses=((56355, 31),),
        satellite_pulses=(),
    )
    for field, change in changes.items():
        setattr(value, field, change)
    return value


def adapt(value):
    return ADAPTER.adapt_certified_stage0_receipt(
        value,
        authority=authority(),
        user_count=100,
        reference_action=11,
        candidate_action=3,
        opening_action_bindings=bindings(),
        replay_lineage=replay_lineage(),
    )


def test_old_certified_candidate_is_segregated_from_policy_aligned_fork():
    result = adapt(receipt())

    assert result.legacy_certified
    assert not result.certificate.passed
    assert result.certificate.support_actions == (11,)
    assert C2.ForkFailure.NONFOCAL_POLICY_ALIGNMENT in result.certificate.failures
    assert result.certificate.hold_r2_margin == 0.5
    assert result.certificate.full_r2_margin == 0.5


def test_old_failed_candidate_is_never_rescued_by_bridge():
    result = adapt(
        receipt(
            certified=False,
            first_failed_layer="service_and_binary_proxies",
            reasons=("useful_bits_loss",),
            candidate_useful_bits=900.0,
        )
    )

    assert not result.legacy_certified
    assert not result.certificate.passed
    assert C2.ForkFailure.STRUCTURAL in result.certificate.failures
    assert result.certificate.support_actions == (11,)


def test_energy_only_mechanism_is_preserved_without_pulse():
    result = adapt(receipt(beam_pulses=(), satellite_pulses=()))
    assert result.evidence.activation_or_energy_path
    assert not result.certificate.passed
    assert C2.ForkFailure.NONFOCAL_POLICY_ALIGNMENT in result.certificate.failures


def test_legacy_certified_but_incompatible_metrics_fail_loudly():
    with pytest.raises(C2.C2ContractError, match="failures beyond"):
        adapt(
            receipt(
                candidate_energy_j=110.0,
                beam_pulses=(),
                satellite_pulses=(),
            )
        )


def test_lossy_json_summary_is_rejected():
    lossy = SimpleNamespace(
        focal_user=10,
        reference_departure_id=(56355, 31),
        candidate_id=(56355, 30),
        certified=True,
        reasons=(),
        hold_system_r2_delta=0.5,
        full_system_r2_delta=0.5,
    )
    with pytest.raises(C2.C2ContractError, match="reference_energy_j"):
        adapt(lossy)
