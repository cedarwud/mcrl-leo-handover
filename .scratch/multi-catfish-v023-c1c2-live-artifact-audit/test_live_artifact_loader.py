"""Focused tests for the read-only V0.20 background attestation."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("live_artifact_loader.py")
SPEC = importlib.util.spec_from_file_location("v023_live_artifact_loader", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
loader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(loader)


def test_current_background_is_authenticated_and_selector_readiness_is_fail_closed() -> None:
    result = loader.attest()

    assert result["status"] == "VERIFIED_V020_BACKGROUND_ONLY"
    assert result["lineage"] == 2026092101
    assert result["q1"]["admitted_c1_rows"] == 1680
    assert result["q1"]["train_rows"] == 968
    assert result["q1"]["validation_rows"] == 712
    assert result["q2"]["source_panel_shards"] == 21
    assert result["q2"]["selected_source_closure_sha256"] == (
        "c6b6b93b36dbbda5123ff7603c675dc5f95e6d4b6c2cb1fa03b1e7b73c853736"
    )
    assert result["fit"]["q1_updates"] == 10
    assert result["fit"]["fixed_deployment_rungs"] == {"q1": 10, "q2": 3000}
    assert result["fit"]["deployment_checkpoint_sha256"] == loader.DEPLOYMENT_CHECKPOINT_SHA256
    assert result["c1_informed_selector_ready"] is False
    assert result["c2_informed_selector_ready"] is False
    assert result["equal_budget_neutral_materialization"] == (
        "BLOCKED_UNTIL_V023_PREDECISION_SOURCE_CAPTURE"
    )


def test_attestation_does_not_call_selectors_or_write_artifacts() -> None:
    effects = loader.attest()["side_effects"]

    assert effects == {
        "simulator_imported": False,
        "selector_called": False,
        "neutral_source_generated": False,
        "learner_run": False,
        "files_written": False,
    }


def test_hash_verification_fails_closed_without_mutating_the_target() -> None:
    path = loader.V023_CONTRACT
    before = loader.file_sha256(path)

    with pytest.raises(loader.LiveArtifactError, match="hash mismatch"):
        loader.verify_file(path, "0" * 64)

    assert loader.file_sha256(path) == before == loader.V023_CONTRACT_SHA256


def test_manifest_digest_uses_the_frozen_canonical_body() -> None:
    payload = loader.read_json(loader.E1_SOURCE_MANIFEST)
    body = {key: value for key, value in payload.items() if key != "source_manifest_sha256"}

    assert payload["source_manifest_sha256"] == loader.E1_SOURCE_MANIFEST_SHA256
    assert loader.canonical_sha256(body) == loader.E1_SOURCE_MANIFEST_SHA256
