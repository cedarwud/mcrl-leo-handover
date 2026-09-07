"""W-191 -- native observation RNG/event provenance receipts."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.env.keyed_fading import KeyedFadingField
from mcrl.env.observation_provenance import (
    NativeObservationProvenanceError,
    build_native_observation_provenance,
    numpy_rng_state_sha256,
)


def test_keyed_receipt_is_stable_and_does_not_consume_sequential_rng() -> None:
    field = KeyedFadingField.from_components("w191", 1)
    rng = np.random.default_rng(191)
    before = numpy_rng_state_sha256(rng)
    sinr = np.arange(56, dtype=np.float64).reshape(2, 28)
    first = build_native_observation_provenance(
        step_index=4,
        candidate_sinr=sinr,
        rng=rng,
        rng_pre_state_sha256=before,
        fading_field=field,
        sinr_provenance="theta-current-interference-previous-step",
    )
    second = build_native_observation_provenance(
        step_index=4,
        candidate_sinr=sinr.copy(),
        rng=rng,
        rng_pre_state_sha256=before,
        fading_field=field,
        sinr_provenance="theta-current-interference-previous-step",
    )
    assert first.verify() == first.content_digest == second.content_digest
    assert first.rng_pre_state_sha256 == first.rng_post_state_sha256
    assert first.field_root_digest == field.root_digest
    assert first.verify_candidate_sinr(sinr) == first.candidate_sinr_sha256


def test_sequential_receipt_records_rng_consumption_without_raw_state() -> None:
    rng = np.random.default_rng(192)
    before = numpy_rng_state_sha256(rng)
    sinr = rng.random((2, 28), dtype=np.float64)
    receipt = build_native_observation_provenance(
        step_index=1,
        candidate_sinr=sinr,
        rng=rng,
        rng_pre_state_sha256=before,
        fading_field=None,
        sinr_provenance="theta-current-interference-previous-step",
    )
    assert receipt.rng_pre_state_sha256 != receipt.rng_post_state_sha256
    assert receipt.field_root_digest is None


def test_candidate_and_receipt_tampering_fail_closed() -> None:
    field = KeyedFadingField.from_components("w191", 3)
    rng = np.random.default_rng(193)
    before = numpy_rng_state_sha256(rng)
    sinr = np.ones((2, 28), dtype=np.float64)
    receipt = build_native_observation_provenance(
        step_index=2,
        candidate_sinr=sinr,
        rng=rng,
        rng_pre_state_sha256=before,
        fading_field=field,
        sinr_provenance="theta-current-interference-previous-step",
    )
    with pytest.raises(NativeObservationProvenanceError, match="candidate SINR"):
        receipt.verify_candidate_sinr(sinr + 1.0)
    with pytest.raises(NativeObservationProvenanceError, match="digest mismatch"):
        replace(receipt, step_index=3)
    with pytest.raises(NativeObservationProvenanceError, match="must not consume"):
        replace(
            receipt,
            rng_post_state_sha256="0" * 64,
            content_digest="",
        )
