"""Synthetic mechanical tests for the V0.18 relational-Q3 runner.

These tests exercise only the prepared source/learner seam.  They do not open
a simulator, generate a source outcome, read TEST, or launch a learner job.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve()
R2_ROOT = HERE.parents[1]
REPO = R2_ROOT.parents[2]
sys.path.insert(0, str(R2_ROOT))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / ".scratch/multi-catfish-v018-relational-zr/next-learner-draft"))

from mcrl.runtime.ee_axis_relational_zr_c3 import (  # noqa: E402
    RelationalZRC3Observation,
)
import relational_learner_runner as runner_module  # noqa: E402
from relational_learner_runner import (  # noqa: E402
    CONFIG_SCHEMA,
    CONFIG_VERSION,
    LearnerBatchSpec,
    RelationalLearnerRunConfig,
    RelationalLearnerRunnerError,
    load_verified_source_panel,
    read_validation_predictions,
    run_initialization,
)
from relational_source_bridge import (  # noqa: E402
    capture_anchor_source,
    write_source_closure,
)


def make_observation(seed: int) -> tuple[RelationalZRC3Observation, np.ndarray]:
    rows = 3
    actions = 28
    victims = 3
    rng = np.random.default_rng(seed)
    action_context = rng.normal(size=(rows, actions, 7))
    victim_tokens = rng.normal(size=(rows, actions, victims, 6))
    action_mask = np.ones((rows, actions), dtype=np.bool_)
    action_mask[1, 4] = False
    action_mask[2, 6] = False
    victim_mask = np.ones((rows, actions, victims), dtype=np.bool_)
    victim_mask[np.arange(rows), :, np.arange(rows)] = False
    victim_mask[1, 4] = False
    victim_mask[2, 6] = False
    compatible = np.zeros((rows, actions), dtype=np.bool_)
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
    target = rng.normal(size=(rows, actions))
    target[~action_mask] = 0.0
    target[np.arange(rows), references] = 0.0
    return observation, target


def write_closure(
    root: Path,
    *,
    world_seed: int,
    lineage: int,
    split: str,
) -> Path:
    observation, target = make_observation(world_seed + lineage)
    captured = capture_anchor_source(
        predecision_encoder=lambda: observation,
        exact_target_provider=lambda _capture: target,
        world_seed=world_seed,
        lineage=lineage,
        split=split,
        field_root_digest="e" * 64,
        kappa_bits=1.0,
    )
    write_source_closure(root, captured)
    return root


def make_config(
    *,
    initialization_lineages: tuple[tuple[int, int], ...] = ((31, 41),),
    train_worlds: tuple[int, ...] = (101, 102),
    validation_worlds: tuple[int, ...] = (201,),
) -> RelationalLearnerRunConfig:
    batches: list[LearnerBatchSpec] = []
    for seed, lineage in initialization_lineages:
        for update in range(100):
            batches.append(
                LearnerBatchSpec(
                    initialization_seed=seed,
                    world_seed=train_worlds[update % len(train_worlds)],
                    lineage=lineage,
                    row_indices=(0, 1, 2),
                )
            )
    lineages = tuple(lineage for _seed, lineage in initialization_lineages)
    return RelationalLearnerRunConfig(
        contract_sha256="a" * 64,
        code_manifest_sha256="b" * 64,
        train_worlds=train_worlds,
        validation_worlds=validation_worlds,
        initialization_lineages=initialization_lineages,
        q1_checkpoint_sha256_by_lineage=tuple(
            (lineage, "c" * 64) for lineage in lineages
        ),
        q2_checkpoint_sha256_by_lineage=tuple(
            (lineage, "d" * 64) for lineage in lineages
        ),
        batch_schedule=tuple(batches),
        batch_size=3,
        update_count=100,
        action_dim=28,
        action_context_dim=7,
        victim_token_dim=6,
        hidden_layers=(4,),
        activation="tanh",
        learning_rate=0.001,
        kappa_bits=1.0,
        beta=0.0,
    )


def make_panel(tmp_path: Path, *, lineage: int = 41):
    train = [
        write_closure(
            tmp_path / f"train-{world}",
            world_seed=world,
            lineage=lineage,
            split="TRAIN",
        )
        for world in (101, 102)
    ]
    validation = [
        write_closure(
            tmp_path / "validation-201",
            world_seed=201,
            lineage=lineage,
            split="VALIDATION",
        )
    ]
    return load_verified_source_panel(
        train,
        validation,
        train_worlds=(101, 102),
        validation_worlds=(201,),
        lineages=(lineage,),
    )


def test_config_requires_one_hundred_batches_per_initialization() -> None:
    config = make_config()
    batches = config.batch_schedule[:-1]
    with pytest.raises(RelationalLearnerRunnerError, match="exactly 100 batches"):
        replace(config, batch_schedule=batches)


def test_config_keeps_each_initialization_schedule_external_and_separate() -> None:
    config = make_config(initialization_lineages=((31, 41), (32, 42)))
    assert len(config.batch_schedule) == 200
    assert len(config.batch_schedule_for(31)) == 100
    assert len(config.batch_schedule_for(32)) == 100
    assert {batch.lineage for batch in config.batch_schedule_for(31)} == {41}
    assert {batch.lineage for batch in config.batch_schedule_for(32)} == {42}


def test_runner_writes_exact_100_update_q3_artifacts_and_bitwise_reload(
    tmp_path: Path,
) -> None:
    panel = make_panel(tmp_path / "sources")
    config = make_config()
    result = run_initialization(
        panel,
        config,
        initialization_seed=31,
        output_dir=tmp_path / "run" / "init-31",
    )

    output = tmp_path / "run" / "init-31"
    assert result["status"] == "MECHANICAL_ARTIFACT_WRITTEN"
    assert result["update_count"] == 100
    assert result["restored_update_count"] == 100
    assert result["reload_bitwise_equal"] is True
    assert result["parameter_sha256"] == result["reloaded_parameter_sha256"]
    assert (
        result["validation_prediction_digest"]
        == result["reloaded_validation_prediction_digest"]
    )
    assert result["q1_q2_digest_binding"] == {
        "q1_checkpoint_sha256": "c" * 64,
        "q2_checkpoint_sha256": "d" * 64,
        "loaded": False,
        "modified": False,
    }
    assert result["scientific_gate_evaluated"] is False
    assert (output / "checkpoint.pt").is_file()
    assert (output / "validation-predictions.npz").is_file()
    assert (output / "validation-predictions.json").is_file()
    assert (output / "validation-predictions.sha256").is_file()
    assert (output / "result.json").is_file()

    arrays, metadata = read_validation_predictions(output)
    assert set(arrays) == {"q_values_0000"}
    assert metadata["learner_update"] is True
    assert metadata["test_split_opened"] is False
    assert metadata["episode_training"] is False


def test_runner_rejects_batch_from_another_initialization_before_update(
    tmp_path: Path,
) -> None:
    panel = make_panel(tmp_path / "sources")
    config = make_config()
    bad_batch = LearnerBatchSpec(99, 101, 41, (0, 1, 2))
    with pytest.raises(RelationalLearnerRunnerError, match="undeclared initialization"):
        RelationalLearnerRunConfig(
            **{
                **config.__dict__,
                "batch_schedule": (bad_batch,) + config.batch_schedule[1:],
            }
        )

    with pytest.raises(RelationalLearnerRunnerError, match="not present"):
        run_initialization(
            panel,
            config,
            initialization_seed=99,
            output_dir=tmp_path / "run" / "init-99",
        )


def test_runner_refuses_second_write_and_prediction_reader_authenticates(
    tmp_path: Path,
) -> None:
    panel = make_panel(tmp_path / "sources")
    config = make_config()
    output = tmp_path / "run" / "init-31"
    run_initialization(panel, config, initialization_seed=31, output_dir=output)
    with pytest.raises(RelationalLearnerRunnerError, match="refusing to overwrite"):
        run_initialization(panel, config, initialization_seed=31, output_dir=output)
    metadata = output / "validation-predictions.json"
    metadata.write_text(metadata.read_text(encoding="ascii").replace("q_values_0000", "q_values_bad"), encoding="ascii")
    with pytest.raises(RelationalLearnerRunnerError):
        read_validation_predictions(output)


def test_external_config_file_is_strict_and_drives_panel_without_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel_root = tmp_path / "sources"
    make_panel(panel_root)
    contract = tmp_path / "learner-contract.md"
    contract.write_text("Status: FROZEN_BEFORE_OUTCOME\n", encoding="utf-8")
    config = make_config()
    config_body = config.as_dict()
    config_body.update(
        {
            "schema": CONFIG_SCHEMA,
            "schema_version": CONFIG_VERSION,
            "contract_sha256": runner_module._file_sha256(contract),
            "train_source_paths": [
                "sources/train-101",
                "sources/train-102",
            ],
            "validation_source_paths": ["sources/validation-201"],
        }
    )
    config_path = tmp_path / "run-config.json"
    config_path.write_bytes(runner_module._canonical_bytes(config_body))
    monkeypatch.setattr(
        runner_module,
        "verify_harvest_source_panel_bindings",
        lambda _panel, _config, _paths: "f" * 64,
    )
    monkeypatch.chdir(tmp_path)
    result = runner_module.run_from_config_file(
        contract_path=contract,
        config_path=config_path,
        output_root=tmp_path / "run",
    )
    assert result["status"] == "MECHANICAL_ARTIFACT_WRITTEN"
    assert result["harvest_bindings_sha256"] == "f" * 64
    assert (tmp_path / "run" / "result.json").is_file()


def test_production_harvest_bindings_are_checked_before_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    panel = make_panel(tmp_path / "sources")
    config = make_config()
    closures = (*panel.train, *panel.validation)
    by_path: dict[Path, object] = {}
    for closure in closures:
        lineage = closure.source.lineage
        metadata = {
            "contract_sha256": config.contract_sha256,
            "config_sha256": "9" * 64,
            "code_manifest_sha256": config.code_manifest_sha256,
            "field_root_digest": "e" * 64,
            "q1_checkpoint_sha256": config.q1_digest_map[lineage],
            "q2_checkpoint_sha256": config.q2_digest_map[lineage],
            "q1_parameter_sha256": "7" * 64,
            "q2_parameter_sha256": "8" * 64,
            "kappa_bits_hex": float(config.kappa_bits).hex(),
            "harvest_metadata_sha256": "6" * 64,
        }
        by_path[closure.path.absolute()] = SimpleNamespace(
            source=closure.source,
            metadata=metadata,
        )

    import relational_source_harvester as harvester_module

    monkeypatch.setattr(
        harvester_module,
        "read_harvest_closure",
        lambda root: by_path[Path(root).absolute()],
    )
    paths = tuple(closure.path for closure in closures)
    digest = runner_module.verify_harvest_source_panel_bindings(
        panel, config, paths
    )
    assert len(digest) == 64

    bad = by_path[paths[0].absolute()]
    bad.metadata["q2_checkpoint_sha256"] = "0" * 64
    with pytest.raises(RelationalLearnerRunnerError, match="Q2 checkpoint"):
        runner_module.verify_harvest_source_panel_bindings(panel, config, paths)

    bad.metadata["q2_checkpoint_sha256"] = config.q2_digest_map[
        bad.source.lineage
    ]
    bad.metadata["code_manifest_sha256"] = "0" * 64
    with pytest.raises(RelationalLearnerRunnerError, match="code manifest"):
        runner_module.verify_harvest_source_panel_bindings(panel, config, paths)
