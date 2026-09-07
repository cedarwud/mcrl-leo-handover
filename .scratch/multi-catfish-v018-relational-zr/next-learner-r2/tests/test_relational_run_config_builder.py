from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve()
R2 = HERE.parents[1]
sys.path.insert(0, str(R2))

import relational_run_config_builder as builder  # noqa: E402
from relational_learner_runner import read_run_config  # noqa: E402


def _plan() -> dict[str, object]:
    train = [2026120501, 2026120502, 2026120503, 2026120504]
    validation = [2026120505, 2026120506, 2026120507]
    inits = [(2026120511, 2026092101), (2026120512, 2026092102), (2026120513, 2026092103)]
    return {
        "schema": builder.PLAN_SCHEMA,
        "schema_version": builder.PLAN_VERSION,
        "contract_sha256": "a" * 64,
        "code_manifest_sha256": "b" * 64,
        "train_worlds": train,
        "validation_worlds": validation,
        "initialization_lineages": [
            {"initialization_seed": seed, "lineage": lineage, "schedule_seed": seed + 100}
            for seed, lineage in inits
        ],
        "q1_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": "c" * 64} for _seed, lineage in inits
        ],
        "q2_checkpoint_sha256_by_lineage": [
            {"lineage": lineage, "sha256": "d" * 64} for _seed, lineage in inits
        ],
        "train_source_paths": [
            f"sources/TRAIN/{world}-{lineage}" for world in train for _seed, lineage in inits
        ],
        "validation_source_paths": [
            f"sources/VALIDATION/{world}-{lineage}" for world in validation for _seed, lineage in inits
        ],
        "rows_per_source": 1000,
        "batch_size": 512,
        "update_count": 100,
        "schedule_algorithm": builder.SCHEDULE_ALGORITHM,
        "network": {
            "action_dim": 28,
            "action_context_dim": 7,
            "victim_token_dim": 6,
            "hidden_layers": [100, 50, 50],
            "activation": "tanh",
            "learning_rate": 0.001,
            "kappa_bits_hex": "0x1.2cea89d260f2ap+33",
            "beta": 0.0,
        },
        "outcome_opened": False,
        "test_split_opened": False,
        "episode_training": False,
    }


def test_materialized_schedule_is_exact_balanced_and_deterministic(tmp_path: Path) -> None:
    first = builder.materialize_plan(_plan())
    second = builder.materialize_plan(_plan())
    assert first == second
    batches = first["batch_schedule"]
    assert len(batches) == 300
    for seed in (2026120511, 2026120512, 2026120513):
        selected = [item for item in batches if item["initialization_seed"] == seed]
        assert len(selected) == 100
        assert {world: sum(item["world_seed"] == world for item in selected) for world in _plan()["train_worlds"]} == {
            world: 25 for world in _plan()["train_worlds"]
        }
        assert all(len(item["row_indices"]) == 512 for item in selected)
        assert all(len(set(item["row_indices"])) == 512 for item in selected)
        assert all(min(item["row_indices"]) >= 0 and max(item["row_indices"]) < 1000 for item in selected)

    plan_path = tmp_path / "plan.json"
    plan_path.write_bytes(builder._canonical_bytes(_plan()))
    config_path = tmp_path / "config.json"
    receipt = builder.write_materialized_plan(plan_path, config_path)
    assert receipt["batch_count"] == 300
    config, train_paths, validation_paths = read_run_config(config_path)
    assert len(config.initialization_lineages) == 3
    assert len(train_paths) == 12
    assert len(validation_paths) == 9
    with pytest.raises(builder.RelationalRunPlanError, match="overwrite"):
        builder.write_materialized_plan(plan_path, config_path)


def test_read_run_config_resolves_source_paths_from_config_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "run" / "learner-run-config.json"
    config_path.parent.mkdir()
    config_path.write_bytes(builder._canonical_bytes(builder.materialize_plan(_plan())))
    unrelated_cwd = tmp_path / "elsewhere"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    _config, train_paths, validation_paths = read_run_config(config_path)

    assert train_paths[0] == str(
        config_path.parent / "sources/TRAIN/2026120501-2026092101"
    )
    assert validation_paths[0] == str(
        config_path.parent / "sources/VALIDATION/2026120505-2026092101"
    )
    assert all(Path(path).is_absolute() for path in (*train_paths, *validation_paths))


def test_plan_fails_closed_on_profile_or_boundary_drift() -> None:
    for field, value in (
        ("outcome_opened", True),
        ("test_split_opened", True),
        ("episode_training", True),
        ("batch_size", 511),
        ("update_count", 99),
        ("rows_per_source", 999),
    ):
        plan = deepcopy(_plan())
        plan[field] = value
        with pytest.raises(builder.RelationalRunPlanError):
            builder.materialize_plan(plan)

    plan = deepcopy(_plan())
    plan["network"]["learning_rate"] = 0.01
    with pytest.raises(builder.RelationalRunPlanError, match="network profile"):
        builder.materialize_plan(plan)

    plan = deepcopy(_plan())
    plan["validation_worlds"][0] = plan["train_worlds"][0]
    with pytest.raises(builder.RelationalRunPlanError, match="overlap"):
        builder.materialize_plan(plan)
