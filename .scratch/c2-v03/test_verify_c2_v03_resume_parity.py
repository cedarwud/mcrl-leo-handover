from __future__ import annotations

import sys

import numpy as np
import pytest
import torch


HERE = __import__("pathlib").Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_c2_v03_resume_parity as verifier  # noqa: E402


def test_exact_comparator_accepts_independent_equal_nested_state():
    left = {
        "tensor": torch.tensor([[1.0, 2.0]]),
        "array": np.asarray([True, False]),
        "nested": [(1, {"x": 2.0})],
    }
    right = {
        "tensor": left["tensor"].clone(),
        "array": left["array"].copy(),
        "nested": [(1, {"x": 2.0})],
    }
    assert verifier.exact_differences(left, right) == []


def test_exact_comparator_names_a_changed_tensor_path():
    left = {"specialists": {"C2": {"weight": torch.tensor([1.0])}}}
    right = {"specialists": {"C2": {"weight": torch.tensor([2.0])}}}
    differences = verifier.exact_differences(left, right)
    assert differences == ["$['specialists']['C2']['weight']: tensor bytes differ"]


def test_state_difference_classifier_allows_only_clock_bound_ledger_hashes():
    differences = [
        "$['c2_option_ledger']['records'][0]['sequence_sha256']: value differs",
        "$['joint_transaction_ledger']['records'][3]['transition_sha256']: value differs",
        "$['joint_transaction_ledger']['records'][3]['primitive_sequence_sha256']: value differs",
        "$['joint_transaction_ledger']['records'][3]['record_sha256']: value differs",
        "$['main_training_state']['q_nets'][0]: tensor bytes differ",
    ]
    allowed, unexpected = verifier._state_difference_classes(differences)
    assert allowed == differences[:4]
    assert unexpected == differences[4:]


def _chronology_receipt(times=(10, 11, 12, 13)):
    return {
        "schema": "c2-v03-preoutcome-chronology-receipt-v1",
        "option_id": "option-1",
        "anchor_sha256": "a" * 64,
        "live_rng_before_sha256": "b" * 64,
        "live_rng_after_forecast_sha256": "b" * 64,
        "forecast_rng_sha256": "c" * 64,
        "forecast_request_sha256": "d" * 64,
        "forecast_payload_sha256": "e" * 64,
        "forecast_started_ns": times[0],
        "forecast_completed_ns": times[1],
        "live_step_started_ns": times[2],
        "live_step_completed_ns": times[3],
        "forecast_sequence": ["forecast", "live"],
        "live_rng_unchanged_during_forecast": True,
        "claim_ceiling": "ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY",
    }


def test_clock_excluded_digest_is_stable_but_full_chronology_digest_is_not():
    first = _chronology_receipt((10, 11, 12, 13))
    second = _chronology_receipt((20, 21, 22, 23))
    assert verifier._chronology_digest(first) != verifier._chronology_digest(second)
    assert verifier._clock_excluded_digest(first) == verifier._clock_excluded_digest(
        second
    )


def test_chronology_digest_rejects_out_of_order_times():
    with pytest.raises(ValueError, match="out of order"):
        verifier._chronology_digest(_chronology_receipt((10, 9, 11, 12)))
