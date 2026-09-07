"""Synthetic-only tests for the V0.18 source harvester.

No simulator, exact physics helper, learner update, TEST split, or training
run is opened here.  Every adapter is an in-memory callback.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest


R2_ROOT = Path(__file__).resolve().parents[1]
REPO = R2_ROOT.parents[2]
sys.path.insert(0, str(R2_ROOT))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / ".scratch/multi-catfish-v018-relational-zr/next-learner-draft"))

from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402
from mcrl.runtime.ee_axis_relational_zr_c3 import (  # noqa: E402
    RelationalZRC3Observation,
)
from relational_source_harvester import (  # noqa: E402
    ACTION_DIM,
    AnchorInput,
    DECISION_CONTEXT_NPZ_FILENAME,
    EXPECTED_ROWS,
    ExactZ3Label,
    SourceHarvestConfig,
    SourceHarvesterError,
    harvest_source_shard,
    read_harvest_closure,
)
from relational_learner_runner import load_verified_source_panel  # noqa: E402
from relational_validation_report import (  # noqa: E402
    read_background_surface_package,
    write_background_surface_package,
)


def make_config(**changes: object) -> SourceHarvestConfig:
    values: dict[str, object] = {
        "contract_sha256": "a" * 64,
        "config_sha256": "b" * 64,
        "code_manifest_sha256": "2" * 64,
        "world_seed": 2026120501,
        "lineage": 2026092101,
        "split": "TRAIN",
        "field_root_digest": "c" * 64,
        "q1_checkpoint_sha256": "d" * 64,
        "q2_checkpoint_sha256": "e" * 64,
        "q1_parameter_sha256": "f" * 64,
        "q2_parameter_sha256": "1" * 64,
        "kappa_bits": float(OPS3_KAPPA_BITS),
        "declared_worlds": (2026120501,),
        "declared_lineages": (2026092101,),
    }
    values.update(changes)
    return SourceHarvestConfig(**values)


def make_anchor(
    config: SourceHarvestConfig,
    step: int,
    *,
    events: list[str] | None = None,
    live_digest: str = "9" * 64,
    incompatible: bool = False,
    mutate_live: bool = False,
) -> AnchorInput:
    users = 100
    rng = np.random.default_rng(1000 + step)
    context = rng.normal(size=(users, ACTION_DIM, 7))
    # The production relational observation keeps one token slot per focal
    # user.  Zero-valued synthetic tokens keep the ten-anchor test small on
    # disk while exercising the real (100,28,100,6) shape.
    victims = np.zeros((users, ACTION_DIM, users, 6), dtype=np.float64)
    mask = np.ones((users, ACTION_DIM), dtype=np.bool_)
    victim_mask = np.ones((users, ACTION_DIM, users), dtype=np.bool_)
    victim_mask[np.arange(users), :, np.arange(users)] = False
    compatible = np.zeros((users, ACTION_DIM), dtype=np.bool_)
    compatible[:, 1] = True
    references = np.zeros(users, dtype=np.int64)
    context[~mask] = 0.0
    victims[~victim_mask] = 0.0
    observation = RelationalZRC3Observation(
        action_context=context,
        victim_tokens=victims,
        action_mask=mask,
        victim_mask=victim_mask,
        positive_credit_compatible=compatible,
        reference_actions=references,
    )
    target = np.zeros((users, ACTION_DIM), dtype=np.float64)
    target[:, 1] = float(2**40)
    q1 = np.zeros((users, ACTION_DIM), dtype=np.float64)
    q2 = np.zeros((users, ACTION_DIM), dtype=np.float64)
    mutable_live = [live_digest]

    def record(name: str) -> None:
        if events is not None:
            events.append(name)

    def encode(reference_actions: np.ndarray) -> RelationalZRC3Observation:
        record("predecision")
        np.testing.assert_array_equal(reference_actions, references)
        return observation

    def exact(_capture) -> ExactZ3Label:
        record("exact")
        exact_compatible = np.array(compatible, copy=True)
        if incompatible:
            exact_compatible[:, 1] = False
        return ExactZ3Label(target, exact_compatible)

    def live() -> str:
        if mutate_live:
            mutable_live[0] = "8" * 64 if mutable_live[0] == live_digest else live_digest
        return mutable_live[0]

    def digests() -> tuple[str, str]:
        return config.q1_checkpoint_sha256, config.q2_checkpoint_sha256

    def parameters() -> tuple[str, str]:
        return config.q1_parameter_sha256, config.q2_parameter_sha256

    def execute(actions: np.ndarray) -> None:
        record("execute")
        assert actions.flags.writeable is False
        np.testing.assert_array_equal(actions, references)

    return AnchorInput(
        step_index=step,
        q1=q1,
        learned_q2=q2,
        action_mask=mask,
        predecision_encoder=encode,
        exact_target_provider=exact,
        live_rng_digest=live,
        checkpoint_digests=digests,
        parameter_digests=parameters,
        execute_background_action=execute,
    )


def test_harvest_orders_capture_before_target_and_action_after_target(tmp_path: Path) -> None:
    config = make_config()
    events: list[str] = []
    result = harvest_source_shard(
        config,
        lambda step: make_anchor(config, step, events=events),
        tmp_path / "shard",
    )
    assert events[:3] == ["predecision", "exact", "execute"]
    assert len(events) == 30
    assert result.source.rows == EXPECTED_ROWS
    assert [item["step_index"] for item in result.sequence["records"]] == list(range(10))


def test_harvest_aggregates_all_ten_by_one_hundred_rows_and_native_bits(tmp_path: Path) -> None:
    config = make_config()
    result = harvest_source_shard(
        config,
        lambda step: make_anchor(config, step),
        tmp_path / "shard",
    )
    assert result.source.rows == 1000
    assert np.count_nonzero(result.source.target_surface_bits == float(2**40)) == 1000
    assert result.metadata["target_field"] == "z3_bits"
    assert result.metadata["target_scale"] == "native_bits"
    assert result.metadata["target_normalized"] is False
    assert result.metadata["filtering"] == "none"


def test_decision_sidecar_is_evaluation_only_and_shares_row_identity(tmp_path: Path) -> None:
    config = make_config()
    output = tmp_path / "shard"
    result = harvest_source_shard(config, lambda step: make_anchor(config, step), output)
    assert set(result.sidecar) == {
        "background_q12",
        "action_mask",
        "reference_actions",
        "step_indices",
        "user_indices",
    }
    assert np.array_equal(result.sidecar["action_mask"], result.source.action_mask)
    assert np.array_equal(result.sidecar["reference_actions"], result.source.reference_actions)
    assert np.array_equal(
        result.sidecar["step_indices"], np.repeat(np.arange(10), 100)
    )
    assert np.array_equal(
        result.sidecar["user_indices"], np.tile(np.arange(100), 10)
    )
    with np.load(output / DECISION_CONTEXT_NPZ_FILENAME, allow_pickle=False) as loaded:
        assert set(loaded.files) == set(result.sidecar)
        assert "target_surface_bits" not in loaded.files


def test_aggregate_closure_loads_into_learner_and_validation_background(
    tmp_path: Path,
) -> None:
    train_config = make_config()
    train_output = tmp_path / "train"
    harvest_source_shard(
        train_config, lambda step: make_anchor(train_config, step), train_output
    )
    validation_config = make_config(
        split="VALIDATION",
        world_seed=2026120502,
        declared_worlds=(2026120502,),
    )
    validation_output = tmp_path / "validation"
    harvest_source_shard(
        validation_config,
        lambda step: make_anchor(validation_config, step),
        validation_output,
    )

    panel = load_verified_source_panel(
        [train_output],
        [validation_output],
        train_worlds=[train_config.world_seed],
        validation_worlds=[validation_config.world_seed],
        lineages=[train_config.lineage],
    )
    validation_source = panel.lookup(
        split="VALIDATION",
        world_seed=validation_config.world_seed,
        lineage=validation_config.lineage,
    ).source
    assert validation_source.rows == EXPECTED_ROWS

    q1 = np.zeros((EXPECTED_ROWS, ACTION_DIM), dtype=np.float64)
    q2 = np.zeros_like(q1)
    background_output = tmp_path / "background"
    write_background_surface_package(
        background_output,
        initialization_seed=2026092201,
        lineage=validation_config.lineage,
        source_sha256=panel.source_sha256,
        q1_checkpoint_sha256=validation_config.q1_checkpoint_sha256,
        q2_checkpoint_sha256=validation_config.q2_checkpoint_sha256,
        arrays={
            ("VALIDATION", validation_config.world_seed, validation_config.lineage): (
                q1,
                q2,
            )
        },
    )
    background = read_background_surface_package(
        background_output,
        expected_source_sha256=panel.source_sha256,
        expected_lineage=validation_config.lineage,
        expected_q1_checkpoint_sha256=validation_config.q1_checkpoint_sha256,
        expected_q2_checkpoint_sha256=validation_config.q2_checkpoint_sha256,
    )
    assert background.arrays[("VALIDATION", validation_config.world_seed, validation_config.lineage)][0].shape == (
        EXPECTED_ROWS,
        ACTION_DIM,
    )


def test_harvester_fails_closed_for_config_identity_and_kappa() -> None:
    config = make_config()
    with pytest.raises(SourceHarvesterError, match="not declared"):
        replace(config, world_seed=2026120502)
    with pytest.raises(SourceHarvesterError, match="not declared"):
        replace(config, lineage=2026092102)
    with pytest.raises(SourceHarvesterError, match="split"):
        replace(config, split="TEST")
    with pytest.raises(SourceHarvesterError, match="kappa"):
        replace(config, kappa_bits=1.0)
    with pytest.raises(SourceHarvesterError, match="contract is not frozen"):
        replace(config, contract_status="DRAFT_NOT_FROZEN_NO_OUTCOME_OPENED")


def test_harvester_rejects_compatibility_mismatch_and_live_mutation(tmp_path: Path) -> None:
    config = make_config()
    with pytest.raises(SourceHarvesterError, match="compatibility"):
        harvest_source_shard(
            config,
            lambda step: make_anchor(config, step, incompatible=True),
            tmp_path / "bad-compatibility",
        )
    with pytest.raises(SourceHarvesterError, match="live state or RNG"):
        harvest_source_shard(
            config,
            lambda step: make_anchor(config, step, mutate_live=True),
            tmp_path / "bad-live",
        )


def test_harvester_rejects_nonfinite_q_surface_and_write_once(tmp_path: Path) -> None:
    config = make_config()
    bad = make_anchor(config, 0)
    bad_q1 = np.array(bad.q1, copy=True)
    bad_q1[0, 0] = np.nan
    bad = replace(bad, q1=bad_q1)
    with pytest.raises(SourceHarvesterError, match="q1"):
        harvest_source_shard(
            config,
            lambda step: bad if step == 0 else make_anchor(config, step),
            tmp_path / "bad-finite",
        )
    bad_checkpoint = replace(
        make_anchor(config, 0),
        checkpoint_digests=lambda: ("0" * 64, config.q2_checkpoint_sha256),
    )
    with pytest.raises(SourceHarvesterError, match="checkpoint"):
        harvest_source_shard(
            config,
            lambda step: bad_checkpoint if step == 0 else make_anchor(config, step),
            tmp_path / "bad-checkpoint",
        )
    output = tmp_path / "once"
    harvest_source_shard(config, lambda step: make_anchor(config, step), output)
    with pytest.raises(SourceHarvesterError, match="overwrite"):
        harvest_source_shard(config, lambda step: make_anchor(config, step), output)


def test_reader_rejects_tampered_sequence_and_duplicate_or_missing_steps(tmp_path: Path) -> None:
    config = make_config()
    output = tmp_path / "tamper"
    harvest_source_shard(config, lambda step: make_anchor(config, step), output)
    sequence = output / "capture-sequence.json"
    raw = sequence.read_text(encoding="ascii")
    sequence.write_text(raw.replace('"step_index":0', '"step_index":9', 1), encoding="ascii")
    with pytest.raises(SourceHarvesterError):
        read_harvest_closure(output)

    output2 = tmp_path / "missing"
    captures = [make_anchor(config, step) for step in range(10)]
    captures[9] = replace(captures[9], step_index=8)
    with pytest.raises(SourceHarvesterError, match="duplicate or missing"):
        harvest_source_shard(config, lambda step: captures[step], output2)
