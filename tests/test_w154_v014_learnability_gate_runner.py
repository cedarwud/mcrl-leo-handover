"""W-154 -- source-merge and synthetic V0.14 supervised-gate runner tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO / ".scratch" / "multi-catfish-v014-learner" / "run_v014_learner_gate.py"
SPEC = importlib.util.spec_from_file_location("mcrl_v014_learnability_gate_w154", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def _source(*, world: int, lineage: int, rows: int = 4, q3_reference: int = 0):
    source_runner = RUNNER._SOURCE_MODULE
    masks = np.ones((rows, 28), dtype=np.bool_)
    q2_targets = np.zeros((rows, 28), dtype=np.float64)
    q3_targets = np.zeros((rows, 28), dtype=np.float64)
    for row in range(rows):
        q2_targets[row, 1] = float(row + 1)
        q2_targets[row, 2] = float(-row - 1)
        q3_targets[row, 1] = float((row % 2) + 1)
        q3_targets[row, 2] = float(-((row % 2) + 1))
    if q3_reference != 0:
        q3_targets[:, q3_reference] = 0.0
        q3_targets[:, 3] = np.arange(1, rows + 1, dtype=np.float64)
    compatibility = np.zeros((rows, 28), dtype=np.bool_)
    compatibility[:, [0, 1]] = True
    anchors = np.asarray(
        [format(world * 1000 + lineage * 10 + row + 1, "064x") for row in range(rows)],
        dtype="S64",
    )
    return source_runner.assemble_source_arrays(
        q1_values=np.zeros((rows, 28), dtype=np.float64),
        q2_states=np.arange(rows * RUNNER.V014_Q2_STATE_DIM, dtype=np.float32).reshape(
            rows, RUNNER.V014_Q2_STATE_DIM
        )
        / 1000.0,
        q2_masks=masks,
        q2_reference_actions=np.zeros(rows, dtype=np.int64),
        q2_target_bits=q2_targets,
        q3_states=np.arange(rows * RUNNER.V014_Q3_STATE_DIM, dtype=np.float32).reshape(
            rows, RUNNER.V014_Q3_STATE_DIM
        )
        / 1000.0,
        q3_masks=masks.copy(),
        q3_reference_actions=np.full(rows, q3_reference, dtype=np.int64),
        q3_target_bits=q3_targets,
        q3_compatibility=compatibility,
        source_seeds=np.full(rows, world, dtype=np.int64),
        anchor_sha256s=anchors,
        step_indices=np.arange(rows, dtype=np.int64),
        user_indices=np.zeros(rows, dtype=np.int64),
        world_seed=world,
        lineage=lineage,
        field_root_digest=format(world + lineage, "064x"),
        kappa_bits=RUNNER.OPS3_KAPPA_BITS,
    )


def _write_shards(tmp_path: Path):
    paths = []
    for world in (11, 12, 13):
        for lineage in (1, 2, 3):
            path = tmp_path / f"w{world}-l{lineage}"
            RUNNER._SOURCE_MODULE.write_source_shard(path, _source(world=world, lineage=lineage))
            paths.append(path)
    return paths


def test_loader_keeps_whole_worlds_and_preserves_label_only_compatibility(tmp_path: Path) -> None:
    paths = _write_shards(tmp_path)
    loaded = RUNNER.load_source_shards(
        list(reversed(paths)),
        train_world_seeds=(11, 12),
        validation_world_seeds=(13,),
        lineage=1,
    )
    assert loaded.train.q2.rows == 8
    assert loaded.validation.q2.rows == 4
    assert loaded.train.world_seeds.tolist() == [11, 11, 11, 11, 12, 12, 12, 12]
    assert loaded.validation.world_seeds.tolist() == [13, 13, 13, 13]
    assert loaded.train.q3_compatibility[:, 1].all()
    assert not loaded.train.q3_compatibility[:, 2].any()
    assert loaded.source_sha256 == RUNNER.canonical_sha256(list(loaded.shard_receipts))


def test_loader_rejects_duplicate_world_lineage_and_missing_world(tmp_path: Path) -> None:
    paths = _write_shards(tmp_path)
    duplicate = tmp_path / "duplicate"
    RUNNER._SOURCE_MODULE.write_source_shard(duplicate, _source(world=11, lineage=1))
    with pytest.raises(RUNNER.V014GateRunnerError, match="duplicate"):
        RUNNER.load_source_shards(
            [paths[0], duplicate, paths[3], paths[6]],
            train_world_seeds=(11, 12),
            validation_world_seeds=(13,),
            lineage=1,
        )
    with pytest.raises(RUNNER.V014GateRunnerError, match="cover"):
        RUNNER.load_source_shards(
            [paths[0], paths[6]],
            train_world_seeds=(11, 12),
            validation_world_seeds=(13,),
            lineage=1,
        )


def test_loader_preserves_distinct_route_local_reference_actions(tmp_path: Path) -> None:
    paths = []
    for world in (11, 12):
        path = tmp_path / f"w{world}-l1"
        RUNNER._SOURCE_MODULE.write_source_shard(
            path, _source(world=world, lineage=1, q3_reference=1)
        )
        paths.append(path)
    loaded = RUNNER.load_source_shards(
        paths,
        train_world_seeds=(11,),
        validation_world_seeds=(12,),
        lineage=1,
    )
    assert np.all(loaded.train.q2.reference_actions == 0)
    assert np.all(loaded.train.q3.reference_actions == 1)


def test_synthetic_gate_fits_both_independent_heads_at_each_rung(tmp_path: Path) -> None:
    paths = _write_shards(tmp_path / "sources")
    spec = RUNNER.V014GateSpec(
        initialization_seeds=(101, 102, 103),
        source_lineages=(1, 2, 3),
        update_rungs=(1, 2),
        train_world_seeds=(11, 12),
        validation_world_seeds=(13,),
        batch_size=4,
        q2_hidden_layers=(4,),
        q3_hidden_layers=(4,),
    )
    output = tmp_path / "gate"
    result = RUNNER.run(source_paths=paths, output_dir=output, spec=spec)
    assert result["schema"] == RUNNER.RESULT_SCHEMA
    assert result["status"] in {"PASS_LEARNABILITY_GATE", "STOP_LEARNABILITY_GATE"}
    assert result["test_split_opened"] is False
    assert result["held_out_ee_evaluated"] is False
    assert result["episode_training"] is False
    assert set(result["q2_reports"]) == {"101", "102", "103"}
    assert set(result["q3_reports"]) == {"101", "102", "103"}
    assert all(set(rows) == {"1", "2"} for rows in result["q2_reports"].values())
    assert all(set(rows) == {"1", "2"} for rows in result["q3_reports"].values())
    assert len(list((output / "checkpoints").glob("*.pt"))) == 6
    assert result["selection"]["deployment_rung"] == result["selection"]["common_joint_rung"]
    assert result["q2_decision"]["selected_rung"] == result["selection"]["deployment_rung"]
    assert result["q3_decision"]["selected_rung"] == result["selection"]["deployment_rung"]
    assert (output / "authority.json").is_file()
    assert (output / "result.json").is_file()
    assert (output / "result-seal.json").is_file()
    with pytest.raises(RUNNER.V014GateRunnerError, match="overwrite"):
        RUNNER.run(source_paths=paths, output_dir=output, spec=spec)
