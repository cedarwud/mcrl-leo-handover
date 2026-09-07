"""Synthetic-only tests for the V0.18 learner preparation seam.

No simulator, production world, TEST split, or source outcome is opened here.
All files created by these tests live under pytest's temporary directory.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest


DRAFT = Path(__file__).resolve().parents[1]
REPO = DRAFT.parents[4]
sys.path.insert(0, str(DRAFT))
sys.path.insert(0, str(REPO / "src"))

from relational_q3_gate import (  # noqa: E402
    FROZEN_STATUS,
    RelationalGateError,
    RelationalZRC3GateConfig,
    adjudicate_100_update_gate,
)
from relational_q3_learner import (  # noqa: E402
    RelationalLearnerError,
    RelationalZRC3LearnerConfig,
    RelationalZRC3PairwiseLearner,
)
from relational_source_schema import (  # noqa: E402
    ACTION_CONTEXT_DIM,
    ACTION_DIM,
    FEATURE_FIELDS,
    RelationalSourceError,
    RelationalZRC3Source,
    VICTIM_TOKEN_DIM,
    canonical_sha256,
    read_source_shard,
    validate_feature_fields,
    validate_feature_manifest,
    validate_world_split,
    write_source_shard,
)


def make_source(*, world_seed: int = 101, split: str = "TRAIN") -> RelationalZRC3Source:
    rows = 3
    victims = 2
    rng = np.random.default_rng(17)
    context = rng.normal(size=(rows, ACTION_DIM, ACTION_CONTEXT_DIM))
    victim_tokens = rng.normal(size=(rows, ACTION_DIM, victims, VICTIM_TOKEN_DIM))
    action_mask = np.ones((rows, ACTION_DIM), dtype=np.bool_)
    action_mask[1, 4] = False
    action_mask[2, 6] = False
    victim_mask = np.ones((rows, ACTION_DIM, victims), dtype=np.bool_)
    victim_mask[1, 4] = False
    victim_mask[2, 6] = False
    compatible = np.zeros((rows, ACTION_DIM), dtype=np.bool_)
    compatible[:, 1] = True
    compatible[1, 4] = False
    compatible[2, 6] = False
    references = np.array([0, 2, 3], dtype=np.int64)
    targets = rng.normal(size=(rows, ACTION_DIM))
    targets[~action_mask] = 0.0
    targets[np.arange(rows), references] = 0.0
    context[~action_mask] = 0.0
    victim_tokens[~victim_mask] = 0.0
    return RelationalZRC3Source(
        action_context=context,
        victim_tokens=victim_tokens,
        action_mask=action_mask,
        victim_mask=victim_mask,
        positive_credit_compatible=compatible,
        reference_actions=references,
        target_surface_bits=targets,
        world_seed=world_seed,
        lineage=1,
        split=split,
        field_root_digest="a" * 64,
        kappa_bits=1.0,
    )


def test_source_is_immutable_and_round_trips_without_pickle(tmp_path: Path) -> None:
    source = make_source()
    with pytest.raises(ValueError):
        source.action_context[0, 0, 0] = 0.0
    output = write_source_shard(tmp_path / "source-1", source)
    loaded = read_source_shard(output["output_dir"])
    assert loaded.arrays_sha256() == source.arrays_sha256()
    assert loaded.action_context.flags.writeable is False
    assert loaded.victim_tokens.flags.writeable is False
    assert output["arrays_sha256"] == source.arrays_sha256()
    receipt_path = Path(output["receipt"])
    receipt_path.write_text(receipt_path.read_text(encoding="ascii").replace("schema=", "schema=bad-"), encoding="ascii")
    with pytest.raises(RelationalSourceError):
        read_source_shard(output["output_dir"])
    with pytest.raises(RelationalSourceError):
        write_source_shard(tmp_path / "source-1", source)


def test_source_closes_feature_names_and_world_splits() -> None:
    assert validate_feature_fields(FEATURE_FIELDS) == FEATURE_FIELDS
    assert validate_feature_manifest({"action_context": {}, "victim_tokens": {}}) == FEATURE_FIELDS
    with pytest.raises(RelationalSourceError):
        validate_feature_fields(("action_context", "future_rate"))
    with pytest.raises(RelationalSourceError):
        validate_world_split((make_source(world_seed=7, split="TRAIN"), make_source(world_seed=7, split="VALIDATION")))
    assert validate_world_split((make_source(world_seed=7), make_source(world_seed=8, split="VALIDATION"))) == {
        7: "TRAIN",
        8: "VALIDATION",
    }


def test_source_rejects_nonzero_masked_features() -> None:
    source = make_source()
    bad = np.array(source.action_context, copy=True)
    bad[1, 4, 0] = 1.0
    with pytest.raises(RelationalSourceError):
        replace(source, action_context=bad)


def test_source_rejects_reference_action_outside_native_mask() -> None:
    source = make_source()
    bad_mask = np.array(source.action_mask, copy=True)
    bad_mask[0, int(source.reference_actions[0])] = False
    with pytest.raises(RelationalSourceError, match="reference action must be legal"):
        replace(source, action_mask=bad_mask)


def test_q3_learner_updates_one_head_and_preserves_surface_masking() -> None:
    source = make_source()
    config = RelationalZRC3LearnerConfig(hidden_layers=(8,))
    learner = RelationalZRC3PairwiseLearner(config, train_seed=23)
    before_digest = learner.parameter_sha256()
    before = learner.q_values(source)
    rows = np.arange(source.rows)
    assert np.allclose(before[rows, source.reference_actions], 0.0)
    assert np.all(before[~source.action_mask] == 0.0)
    update = learner.update(source)
    assert update["update_count"] == 1
    assert update["gauge_mse"] == 0.0
    assert learner.parameter_sha256() != before_digest
    after = learner.q_values(source)
    assert np.allclose(after[rows, source.reference_actions], 0.0, atol=1e-7)
    assert np.all(after[~source.action_mask] == 0.0)


def test_q3_learner_checkpoint_round_trip_is_strict(tmp_path: Path) -> None:
    source = make_source()
    config = RelationalZRC3LearnerConfig(hidden_layers=(8,))
    learner = RelationalZRC3PairwiseLearner(config, train_seed=29)
    learner.update(source)
    contract = "b" * 64
    source_digest = "c" * 64
    code_manifest = "d" * 64
    with pytest.raises(RelationalLearnerError, match="exactly 100 updates"):
        learner.save_checkpoint(
            tmp_path / "early.pt",
            contract_sha256=contract,
            source_sha256=source_digest,
            code_manifest_sha256=code_manifest,
        )
    for _ in range(99):
        learner.update(source)
    expected_values = learner.q_values(source)
    expected_digest = learner.parameter_sha256()
    path = tmp_path / "checkpoint.pt"
    receipt = learner.save_checkpoint(
        path,
        contract_sha256=contract,
        source_sha256=source_digest,
        code_manifest_sha256=code_manifest,
    )
    assert receipt["parameter_sha256"] == expected_digest
    restored = RelationalZRC3PairwiseLearner(config, train_seed=29)
    assert restored.load_checkpoint(
        path,
        contract_sha256=contract,
        source_sha256=source_digest,
        code_manifest_sha256=code_manifest,
    ) == 100
    np.testing.assert_array_equal(restored.q_values(source), expected_values)
    assert restored.parameter_sha256() == expected_digest
    with pytest.raises(RelationalLearnerError):
        restored.load_checkpoint(
            path,
            contract_sha256="e" * 64,
            source_sha256=source_digest,
            code_manifest_sha256=code_manifest,
        )
    with pytest.raises(RelationalLearnerError):
        restored.load_checkpoint(
            path,
            contract_sha256=contract,
            source_sha256=source_digest,
            code_manifest_sha256="f" * 64,
        )
    with pytest.raises(RelationalLearnerError):
        learner.save_checkpoint(
            path,
            contract_sha256=contract,
            source_sha256=source_digest,
            code_manifest_sha256=code_manifest,
        )


def test_same_seed_100_updates_are_deterministic() -> None:
    source = make_source()
    config = RelationalZRC3LearnerConfig(hidden_layers=(8,))
    first = RelationalZRC3PairwiseLearner(config, train_seed=31)
    second = RelationalZRC3PairwiseLearner(config, train_seed=31)
    for _ in range(100):
        first.update(source)
        second.update(source)
    assert first.parameter_sha256() == second.parameter_sha256()
    np.testing.assert_array_equal(first.q_values(source), second.q_values(source))


def test_structural_reference_centring_rejects_redundant_gauge_weight() -> None:
    with pytest.raises(RelationalLearnerError, match="structurally centred"):
        RelationalZRC3LearnerConfig(beta=0.1)


def test_100_update_gate_requires_frozen_contract_and_fixed_updates() -> None:
    config = RelationalZRC3GateConfig(
        contract_sha256="e" * 64,
        contract_status=FROZEN_STATUS,
        min_mean_skill=0.5,
        min_positive_initializations=2,
        min_supported_change_rate=0.5,
        min_supported_initializations=2,
    )
    reports = {
        "init-a": {"update_count": 100, "validation_skill": 0.6, "supported_change_rate": 0.6},
        "init-b": {"update_count": 100, "validation_skill": 0.7, "supported_change_rate": 0.7},
        "init-c": {"update_count": 100, "validation_skill": 0.8, "supported_change_rate": 0.8},
    }
    result = adjudicate_100_update_gate(reports, config)
    assert result.passed is True
    assert result.decision == "PASS_LEARNER_GATE"
    assert result.required_updates == 100
    with pytest.raises(RelationalGateError):
        adjudicate_100_update_gate({**reports, "init-d": {"update_count": 99, "validation_skill": 0.9, "supported_change_rate": 0.9}}, config)
    with pytest.raises(RelationalGateError):
        RelationalZRC3GateConfig(
            contract_sha256="e" * 64,
            contract_status="PROVISIONAL",
            min_mean_skill=0.5,
            min_positive_initializations=2,
            min_supported_change_rate=0.5,
            min_supported_initializations=2,
        )


def test_gate_config_does_not_hide_threshold_defaults() -> None:
    with pytest.raises(TypeError):
        RelationalZRC3GateConfig(  # type: ignore[call-arg]
            contract_sha256="f" * 64,
            contract_status=FROZEN_STATUS,
        )


def test_canonical_digest_is_stable() -> None:
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256({"a": 1, "b": 2})
