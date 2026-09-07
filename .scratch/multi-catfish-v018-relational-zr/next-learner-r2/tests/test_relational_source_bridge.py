"""Pure/provenance tests for the V0.18 learned-Q3 source bridge.

These tests use only synthetic immutable observations.  They do not construct a
simulator, open a world, evaluate an action, read TEST, or invoke a teacher.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve()
BRIDGE_ROOT = HERE.parents[1]
REPO = BRIDGE_ROOT.parents[4]
sys.path.insert(0, str(BRIDGE_ROOT))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / ".scratch/multi-catfish-v018-relational-zr/next-learner-draft"))

from mcrl.runtime.ee_axis_relational_zr_c3 import (  # noqa: E402
    RELATIONAL_ZR_C3_SCHEMA,
    RelationalZRC3Observation,
)
import relational_source_bridge as bridge_module  # noqa: E402
from relational_source_bridge import (  # noqa: E402
    BRIDGE_METADATA_FILENAME,
    BRIDGE_RECEIPT_FILENAME,
    CAPTURE_ORDER,
    COMPATIBILITY_ROLE,
    ENCODER_NAME,
    IMPLEMENTATION_STATUS,
    TARGET_SEMANTICS,
    RelationalSourceBridgeError,
    attach_exact_zr_target,
    capture_anchor_source,
    capture_predecision,
    read_source_closure,
    write_source_closure,
)


def make_observation() -> tuple[RelationalZRC3Observation, np.ndarray]:
    users = 3
    actions = 28
    rng = np.random.default_rng(20260904)
    action_context = rng.normal(size=(users, actions, 7))
    victim_tokens = rng.normal(size=(users, actions, users, 6))
    action_mask = np.ones((users, actions), dtype=np.bool_)
    action_mask[1, 4] = False
    action_mask[2, 6] = False
    victim_mask = np.ones((users, actions, users), dtype=np.bool_)
    victim_mask[np.arange(users), :, np.arange(users)] = False
    victim_mask[1, 4] = False
    victim_mask[2, 6] = False
    compatible = np.zeros((users, actions), dtype=np.bool_)
    compatible[:, 1] = True
    compatible[1, 4] = False
    compatible[2, 6] = False
    references = np.array([0, 2, 3], dtype=np.int64)
    action_context[~action_mask] = 0.0
    victim_tokens[~victim_mask] = 0.0
    observation = RelationalZRC3Observation(
        action_context=action_context,
        victim_tokens=victim_tokens,
        action_mask=action_mask,
        victim_mask=victim_mask,
        positive_credit_compatible=compatible,
        reference_actions=references,
    )
    target = rng.normal(size=(users, actions))
    target[~action_mask] = 0.0
    target[np.arange(users), references] = 0.0
    return observation, target


def capture(*, target_provider=None):
    observation, target = make_observation()
    return capture_anchor_source(
        predecision_encoder=lambda: observation,
        exact_target_provider=target_provider
        or (lambda _capture: target),
        world_seed=2026120401,
        lineage=2026092101,
        split="TRAIN",
        field_root_digest="b" * 64,
        kappa_bits=float.fromhex("0x1.2cea89d260f2ap+33"),
    )


def test_exact_target_provider_runs_only_after_authenticated_predecision_capture() -> None:
    observation, target = make_observation()
    events: list[str] = []

    def encoder() -> RelationalZRC3Observation:
        events.append("predecision")
        return observation

    def target_provider(capture_record) -> np.ndarray:
        events.append("exact-target")
        assert capture_record.predecision_observation_sha256 == observation.state_sha256
        assert capture_record.observation.schema == RELATIONAL_ZR_C3_SCHEMA
        assert capture_record.observation.action_context.flags.writeable is False
        return target

    result = capture_anchor_source(
        predecision_encoder=encoder,
        exact_target_provider=target_provider,
        world_seed=2026120401,
        lineage=2026092101,
        split="TRAIN",
        field_root_digest="b" * 64,
        kappa_bits=float.fromhex("0x1.2cea89d260f2ap+33"),
    )
    assert events == ["predecision", "exact-target"]
    np.testing.assert_array_equal(result.source.action_context, observation.action_context)
    np.testing.assert_array_equal(
        result.source.positive_credit_compatible,
        observation.positive_credit_compatible,
    )
    np.testing.assert_array_equal(result.source.target_surface_bits, target)
    assert result.capture_order == CAPTURE_ORDER


def test_environment_adapter_reuses_current_v018_encoder_before_target(monkeypatch) -> None:
    observation, target = make_observation()
    events: list[str] = []

    def fake_encoder(*args, **kwargs) -> RelationalZRC3Observation:
        events.append("v018-encoder")
        assert kwargs["reference_actions"] is not None
        return observation

    monkeypatch.setattr(bridge_module, "encode_relational_zr_c3_state", fake_encoder)
    result = bridge_module.harvest_v018_relational_anchor(
        environment=object(),
        observation=object(),
        reference_actions=observation.reference_actions,
        required_power_surface=np.ones_like(observation.action_mask, dtype=np.float64),
        opening_feasibility_surface=observation.action_mask,
        pmax_w=1.0,
        exact_target_provider=lambda _capture: events.append("exact-target") or target,
        world_seed=2026120401,
        lineage=2026092101,
        split="TRAIN",
        field_root_digest="b" * 64,
        kappa_bits=1.0,
    )
    assert events == ["v018-encoder", "exact-target"]
    assert result.source.schema == "multi-catfish-mcrl-v018-relational-zr-source-v1"


def test_exact_target_adapter_cannot_smuggle_a_teacher_or_realised_outcome_mapping() -> None:
    observation, target = make_observation()
    predecision = capture_predecision(
        encoder=lambda: observation,
        world_seed=2026120401,
        lineage=2026092101,
        split="TRAIN",
        field_root_digest="b" * 64,
        kappa_bits=1.0,
    )
    with pytest.raises(RelationalSourceBridgeError, match="target_surface_bits only"):
        attach_exact_zr_target(
            predecision,
            {
                "target_surface_bits": target,
                "realized_energy": np.ones_like(target),
            },
        )


def test_target_surface_is_native_bits_and_respects_mask_and_reference() -> None:
    observation, target = make_observation()
    predecision = capture_predecision(
        encoder=lambda: observation,
        world_seed=2026120401,
        lineage=2026092101,
        split="TRAIN",
        field_root_digest="b" * 64,
        kappa_bits=1.0,
    )
    captured = attach_exact_zr_target(predecision, target)
    assert captured.target_semantics == TARGET_SEMANTICS
    assert captured.source.target_surface_bits.dtype == np.float64
    assert captured.source.target_surface_bits.flags.writeable is False
    bad_reference = np.array(target, copy=True)
    bad_reference[0, 0] = 1.0
    with pytest.raises(RelationalSourceBridgeError, match="reference action"):
        attach_exact_zr_target(predecision, bad_reference)
    bad_mask = np.array(target, copy=True)
    bad_mask[1, 4] = 1.0
    with pytest.raises(RelationalSourceBridgeError, match="outside the native mask"):
        attach_exact_zr_target(predecision, bad_mask)


def test_source_closure_writes_and_reauthenticates_bridge_provenance(tmp_path: Path) -> None:
    captured = capture()
    output = tmp_path / "source-2026120401-2026092101"
    receipt = write_source_closure(output, captured)
    assert (output / "source.npz").is_file()
    assert (output / "metadata.json").is_file()
    assert (output / "source.sha256").is_file()
    assert (output / BRIDGE_METADATA_FILENAME).is_file()
    assert (output / BRIDGE_RECEIPT_FILENAME).is_file()
    source, bridge = read_source_closure(output)
    assert source.arrays_sha256() == captured.source.arrays_sha256()
    assert bridge["schema"] == "multi-catfish-mcrl-v018-relational-zr-source-bridge-v1"
    assert bridge["status"] == IMPLEMENTATION_STATUS
    assert bridge["capture_order"] == CAPTURE_ORDER
    assert bridge["compatibility_role"] == COMPATIBILITY_ROLE
    assert bridge["feature_fields"] == ["action_context", "victim_tokens"]
    assert bridge["label_fields"] == ["positive_credit_compatible", "target_surface_bits"]
    assert bridge["test_split_opened"] is False
    assert bridge["episode_training"] is False
    assert bridge["learner_update"] is False
    assert receipt["bridge_payload_sha256"] == bridge["bridge_metadata_sha256"]


def test_bridge_detects_metadata_or_npz_tampering(tmp_path: Path) -> None:
    output = tmp_path / "source-tamper"
    write_source_closure(output, capture())
    metadata = output / BRIDGE_METADATA_FILENAME
    metadata.write_bytes(
        metadata.read_bytes().replace(
            b"IMPLEMENTATION_ONLY_NO_OUTCOME", b"tampered"
        )
    )
    with pytest.raises(RelationalSourceBridgeError, match="canonical JSON|self-digest"):
        read_source_closure(output)


def test_bridge_identity_is_closed_and_does_not_declare_a_scientific_contract() -> None:
    result = capture()
    assert result.predecision.encoder == ENCODER_NAME
    assert result.predecision.status == IMPLEMENTATION_STATUS
    assert result.source.feature_fields == ("action_context", "victim_tokens")
    assert "FROZEN_BEFORE_OUTCOME" not in result.predecision.status
