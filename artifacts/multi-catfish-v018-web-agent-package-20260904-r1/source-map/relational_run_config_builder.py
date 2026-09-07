#!/usr/bin/env python3
"""Materialize the frozen V0.18 Q3 learner schedule from an explicit plan.

This module opens no source data and runs no learner.  Every experimental
identity and hyperparameter is supplied by a canonical JSON plan.  Its only
nontrivial operation is to materialize the already-declared balanced batch
schedule before source outcomes are opened.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import numpy as np

from relational_learner_runner import (
    CONFIG_SCHEMA,
    CONFIG_VERSION,
    LearnerBatchSpec,
    RelationalLearnerRunConfig,
    canonical_sha256,
)


PLAN_SCHEMA = "multi-catfish-mcrl-v018-relational-q3-run-plan-v1"
PLAN_VERSION = 1
SCHEDULE_ALGORITHM = "round-robin-world-independent-without-replacement-v1"
EXPECTED_TRAIN_WORLDS = 4
EXPECTED_VALIDATION_WORLDS = 3
EXPECTED_INITIALIZATIONS = 3
EXPECTED_ROWS_PER_SOURCE = 1000
EXPECTED_BATCH_SIZE = 512
EXPECTED_UPDATES = 100
EXPECTED_ACTION_DIM = 28
EXPECTED_ACTION_CONTEXT_DIM = 7
EXPECTED_VICTIM_TOKEN_DIM = 6
EXPECTED_HIDDEN_LAYERS = (100, 50, 50)
EXPECTED_ACTIVATION = "tanh"
EXPECTED_LEARNING_RATE = 0.001
EXPECTED_KAPPA_HEX = "0x1.2cea89d260f2ap+33"
EXPECTED_BETA = 0.0

_PLAN_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "contract_sha256",
        "code_manifest_sha256",
        "train_worlds",
        "validation_worlds",
        "initialization_lineages",
        "q1_checkpoint_sha256_by_lineage",
        "q2_checkpoint_sha256_by_lineage",
        "train_source_paths",
        "validation_source_paths",
        "rows_per_source",
        "batch_size",
        "update_count",
        "schedule_algorithm",
        "network",
        "outcome_opened",
        "test_split_opened",
        "episode_training",
    }
)
_NETWORK_FIELDS = frozenset(
    {
        "action_dim",
        "action_context_dim",
        "victim_token_dim",
        "hidden_layers",
        "activation",
        "learning_rate",
        "kappa_bits_hex",
        "beta",
    }
)


class RelationalRunPlanError(ValueError):
    """The pre-outcome plan or materialized schedule is malformed."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RelationalRunPlanError("plan is not finite canonical JSON") from error


def _read_canonical(path: str | Path) -> dict[str, object]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise RelationalRunPlanError(f"expected a regular plan file: {source}")
    raw = source.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RelationalRunPlanError("plan is not canonical JSON") from error
    if not isinstance(value, dict) or raw != _canonical_bytes(value):
        raise RelationalRunPlanError("plan is not canonical JSON")
    return value


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalRunPlanError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RelationalRunPlanError(f"{field} must be a positive integer")
    return value


def _identity_list(value: object, *, field: str, count: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != count:
        raise RelationalRunPlanError(f"{field} must contain exactly {count} identities")
    result = tuple(_positive_int(item, field=field) for item in value)
    if len(set(result)) != len(result):
        raise RelationalRunPlanError(f"{field} contains duplicates")
    return result


def _paths(value: object, *, field: str, count: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) != count:
        raise RelationalRunPlanError(f"{field} must contain exactly {count} paths")
    result: list[str] = []
    for raw in value:
        if not isinstance(raw, str) or not raw:
            raise RelationalRunPlanError(f"{field} contains a malformed path")
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts:
            raise RelationalRunPlanError(f"{field} must contain isolated-root relative paths")
        result.append(raw)
    if len(set(result)) != len(result):
        raise RelationalRunPlanError(f"{field} contains duplicates")
    return tuple(result)


def _digest_pairs(value: object, *, field: str) -> tuple[tuple[int, str], ...]:
    if not isinstance(value, list) or len(value) != EXPECTED_INITIALIZATIONS:
        raise RelationalRunPlanError(
            f"{field} must contain exactly {EXPECTED_INITIALIZATIONS} bindings"
        )
    result: list[tuple[int, str]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {"lineage", "sha256"}:
            raise RelationalRunPlanError(f"{field} contains a malformed binding")
        result.append(
            (
                _positive_int(item["lineage"], field=f"{field}.lineage"),
                _digest(item["sha256"], field=f"{field}.sha256"),
            )
        )
    if len({lineage for lineage, _sha in result}) != len(result):
        raise RelationalRunPlanError(f"{field} contains duplicate lineages")
    return tuple(result)


def _initializations(value: object) -> tuple[tuple[int, int, int], ...]:
    if not isinstance(value, list) or len(value) != EXPECTED_INITIALIZATIONS:
        raise RelationalRunPlanError(
            f"initialization_lineages must contain exactly {EXPECTED_INITIALIZATIONS} entries"
        )
    result: list[tuple[int, int, int]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != {
            "initialization_seed",
            "lineage",
            "schedule_seed",
        }:
            raise RelationalRunPlanError("initialization_lineages entry is malformed")
        result.append(
            (
                _positive_int(item["initialization_seed"], field="initialization_seed"),
                _positive_int(item["lineage"], field="lineage"),
                _positive_int(item["schedule_seed"], field="schedule_seed"),
            )
        )
    for index, name in ((0, "initialization seeds"), (1, "lineages"), (2, "schedule seeds")):
        if len({item[index] for item in result}) != len(result):
            raise RelationalRunPlanError(f"initialization_lineages contains duplicate {name}")
    return tuple(result)


def build_batch_schedule(
    *,
    train_worlds: Sequence[int],
    initialization_lineages: Sequence[tuple[int, int, int]],
    rows_per_source: int,
    batch_size: int,
    update_count: int,
) -> tuple[LearnerBatchSpec, ...]:
    """Build an explicit balanced schedule without reading source outcomes."""

    worlds = tuple(train_worlds)
    if len(worlds) != EXPECTED_TRAIN_WORLDS or update_count % len(worlds):
        raise RelationalRunPlanError("TRAIN worlds cannot be cycled equally")
    if rows_per_source != EXPECTED_ROWS_PER_SOURCE:
        raise RelationalRunPlanError("rows_per_source must be exactly 1000")
    if batch_size != EXPECTED_BATCH_SIZE or update_count != EXPECTED_UPDATES:
        raise RelationalRunPlanError("batch_size/update_count disagree with the frozen profile")
    batches: list[LearnerBatchSpec] = []
    for initialization_seed, lineage, schedule_seed in initialization_lineages:
        rng = np.random.default_rng(schedule_seed)
        for update in range(update_count):
            world = int(worlds[update % len(worlds)])
            indices = tuple(
                int(item)
                for item in rng.choice(rows_per_source, size=batch_size, replace=False)
            )
            batches.append(
                LearnerBatchSpec(
                    initialization_seed=initialization_seed,
                    world_seed=world,
                    lineage=lineage,
                    row_indices=indices,
                )
            )
    return tuple(batches)


def materialize_plan(plan: Mapping[str, object]) -> dict[str, object]:
    """Validate every frozen choice and return the runner's strict config."""

    if set(plan) != _PLAN_FIELDS:
        raise RelationalRunPlanError("plan contains unknown or missing fields")
    if plan["schema"] != PLAN_SCHEMA or plan["schema_version"] != PLAN_VERSION:
        raise RelationalRunPlanError("plan schema is stale")
    if any(plan[field] is not False for field in ("outcome_opened", "test_split_opened", "episode_training")):
        raise RelationalRunPlanError("plan crosses the pre-outcome source-only boundary")
    contract = _digest(plan["contract_sha256"], field="contract_sha256")
    manifest = _digest(plan["code_manifest_sha256"], field="code_manifest_sha256")
    train_worlds = _identity_list(
        plan["train_worlds"], field="train_worlds", count=EXPECTED_TRAIN_WORLDS
    )
    validation_worlds = _identity_list(
        plan["validation_worlds"],
        field="validation_worlds",
        count=EXPECTED_VALIDATION_WORLDS,
    )
    if set(train_worlds) & set(validation_worlds):
        raise RelationalRunPlanError("TRAIN and VALIDATION worlds overlap")
    initializations = _initializations(plan["initialization_lineages"])
    lineage_set = {lineage for _seed, lineage, _schedule in initializations}
    q1 = _digest_pairs(
        plan["q1_checkpoint_sha256_by_lineage"],
        field="q1_checkpoint_sha256_by_lineage",
    )
    q2 = _digest_pairs(
        plan["q2_checkpoint_sha256_by_lineage"],
        field="q2_checkpoint_sha256_by_lineage",
    )
    if {lineage for lineage, _sha in q1} != lineage_set or {
        lineage for lineage, _sha in q2
    } != lineage_set:
        raise RelationalRunPlanError("Q1/Q2 digest bindings do not cover lineages")
    train_paths = _paths(
        plan["train_source_paths"],
        field="train_source_paths",
        count=EXPECTED_TRAIN_WORLDS * EXPECTED_INITIALIZATIONS,
    )
    validation_paths = _paths(
        plan["validation_source_paths"],
        field="validation_source_paths",
        count=EXPECTED_VALIDATION_WORLDS * EXPECTED_INITIALIZATIONS,
    )
    rows = _positive_int(plan["rows_per_source"], field="rows_per_source")
    batch_size = _positive_int(plan["batch_size"], field="batch_size")
    updates = _positive_int(plan["update_count"], field="update_count")
    if plan["schedule_algorithm"] != SCHEDULE_ALGORITHM:
        raise RelationalRunPlanError("schedule_algorithm is stale")
    network = plan["network"]
    if not isinstance(network, Mapping) or set(network) != _NETWORK_FIELDS:
        raise RelationalRunPlanError("network profile is malformed")
    expected_network = {
        "action_dim": EXPECTED_ACTION_DIM,
        "action_context_dim": EXPECTED_ACTION_CONTEXT_DIM,
        "victim_token_dim": EXPECTED_VICTIM_TOKEN_DIM,
        "hidden_layers": list(EXPECTED_HIDDEN_LAYERS),
        "activation": EXPECTED_ACTIVATION,
        "learning_rate": EXPECTED_LEARNING_RATE,
        "kappa_bits_hex": EXPECTED_KAPPA_HEX,
        "beta": EXPECTED_BETA,
    }
    if dict(network) != expected_network:
        raise RelationalRunPlanError("network profile disagrees with the frozen V0.18 profile")
    kappa = float.fromhex(str(network["kappa_bits_hex"]))
    if not math.isfinite(kappa) or kappa <= 0.0:
        raise RelationalRunPlanError("kappa is nonfinite")
    schedule = build_batch_schedule(
        train_worlds=train_worlds,
        initialization_lineages=initializations,
        rows_per_source=rows,
        batch_size=batch_size,
        update_count=updates,
    )
    config = RelationalLearnerRunConfig(
        contract_sha256=contract,
        code_manifest_sha256=manifest,
        train_worlds=train_worlds,
        validation_worlds=validation_worlds,
        initialization_lineages=tuple((seed, lineage) for seed, lineage, _schedule in initializations),
        q1_checkpoint_sha256_by_lineage=q1,
        q2_checkpoint_sha256_by_lineage=q2,
        batch_schedule=schedule,
        batch_size=batch_size,
        update_count=updates,
        action_dim=EXPECTED_ACTION_DIM,
        action_context_dim=EXPECTED_ACTION_CONTEXT_DIM,
        victim_token_dim=EXPECTED_VICTIM_TOKEN_DIM,
        hidden_layers=EXPECTED_HIDDEN_LAYERS,
        activation=EXPECTED_ACTIVATION,
        learning_rate=EXPECTED_LEARNING_RATE,
        kappa_bits=kappa,
        beta=EXPECTED_BETA,
    )
    payload = config.as_dict()
    payload.update(
        {
            "schema": CONFIG_SCHEMA,
            "schema_version": CONFIG_VERSION,
            "train_source_paths": list(train_paths),
            "validation_source_paths": list(validation_paths),
        }
    )
    return payload


def write_materialized_plan(plan_path: str | Path, output_path: str | Path) -> dict[str, object]:
    plan = _read_canonical(plan_path)
    payload = materialize_plan(plan)
    destination = Path(output_path)
    if destination.exists() or destination.is_symlink():
        raise RelationalRunPlanError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(_canonical_bytes(payload))
        os.link(temporary, destination)
    except FileExistsError as error:
        raise RelationalRunPlanError(f"refusing to overwrite {destination}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "plan_sha256": hashlib.sha256(Path(plan_path).read_bytes()).hexdigest(),
        "config_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "schedule_sha256": canonical_sha256(payload["batch_schedule"]),
        "batch_count": len(payload["batch_schedule"]),
        "output": str(destination),
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(json.dumps(write_materialized_plan(args.plan, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
