#!/usr/bin/env python3
"""Snapshot and validate all ten R2 EP500 prefixes used by the R7 route."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r7_500_authority as authority  # noqa: E402
import r7_500_checkpoint as checkpoint_tools  # noqa: E402
import r7_500_output as output_tools  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-prefix-bridge-v5"
CHECKPOINT_NAME = "ep-000500-main.pt"
MATRIX_SCHEMA = "multi-catfish-mcrl-c2-v03a-trend-matrix-v1"
JOURNAL_SCHEMA = "c2-v03-bounded-run-journal-v2"
ARM_RUNNER_RELATIVE = ".scratch/c2-v03a-trend/c2_v03a_trend_arm.py"
SOURCE_STATUS_SCHEMA = "multi-catfish-mcrl-c2-v03a-trend-arm-v1"
STATUS_SIDECAR_SCHEMA = (
    "multi-catfish-mcrl-c2-v03a-trend-arm-structural-sidecar-v1"
)
STATUS_SIDECAR_NAME = "status-structural-sidecar.json"

# The status file is intentionally outcome-bearing.  Only this fixed structural
# projection is allowed to cross the prefix bridge.  In particular, do not add
# ``result.episode_rows``, telemetry, reward, service, EE, or power fields here.
STATUS_SIDECAR_FIELDS = frozenset(
    {
        "schema",
        "source_status_schema",
        "source_status_sha256",
        "status",
        "run_mode",
        "arm",
        "label",
        "episodes_planned",
        "episodes_executed",
        "users",
        "seeds",
        "trainer_config",
        "authority_path",
        "runtime_authority",
        "runtime",
        "formal_training_authorized",
        "claim_ceiling",
        "result",
    }
)
STATUS_RESULT_SIDECAR_FIELDS = frozenset(
    {
        "episodes",
        "start_episode",
        "episodes_executed",
        "episodes_completed",
        "artifact_scope",
        "checkpoint_sha256",
        "checkpoint_every_episodes",
        "periodic_checkpoint_count",
        "periodic_checkpoints",
    }
)
PERIODIC_CHECKPOINT_FIELDS = frozenset(
    {
        "episodes_completed",
        "episode_index",
        "path",
        "sha256",
        "checkpoint_kind",
        "load_round_trip",
    }
)
RUNTIME_AUTHORITY_FIELDS = frozenset(
    {
        "prereg_path",
        "prereg_sha256",
        "tle_file_count",
        "tle_file_set_sha256",
        "tle_root_path",
    }
)
RUNTIME_FIELDS = frozenset({"python", "numpy", "torch"})
TRAINER_CONFIG_FIELDS = frozenset(
    {
        "activation",
        "batch_size",
        "checkpoint_assumption_id",
        "checkpoint_primary_report",
        "checkpoint_secondary_report",
        "comparison_role",
        "device",
        "discount_factor",
        "episodes",
        "epsilon_decay_episodes",
        "epsilon_end",
        "epsilon_start",
        "hidden_layers",
        "learning_rate",
        "load_balance_calibration_mode",
        "load_normalization",
        "method_family",
        "objective_weights",
        "offset_scale_km",
        "phase",
        "policy_sharing_mode",
        "r1_reward_label",
        "r1_reward_provenance",
        "replay_capacity",
        "reward_calibration_enabled",
        "reward_calibration_mode",
        "reward_calibration_scales",
        "reward_calibration_source",
        "reward_normalization_mode",
        "snr_encoding",
        "target_update_every_episodes",
        "theta_encoding",
        "training_experiment_id",
        "training_experiment_kind",
    }
)


class R7500PrefixBridgeError(RuntimeError):
    """Raised when an R2 checkpoint cannot be admitted as an R7 EP500 prefix."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise R7500PrefixBridgeError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise R7500PrefixBridgeError(f"{label} must be a JSON object")
    return value


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_sha256(value: Any, *, field: str) -> str:
    if not _is_sha256(value):
        raise R7500PrefixBridgeError(f"{field} is not a lowercase SHA-256 digest")
    return str(value)


def _require_int(value: Any, *, field: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise R7500PrefixBridgeError(f"{field} is not an integer")
    if minimum is not None and value < minimum:
        raise R7500PrefixBridgeError(f"{field} is below its minimum")
    return int(value)


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise R7500PrefixBridgeError(f"{field} is missing or is not an object")
    return value


def _structural_json_value(value: Any, *, field: str) -> Any:
    """Copy only finite JSON scalars/lists; nested open-ended objects are forbidden."""

    if value is None or isinstance(value, (bool, str)) or type(value) is int:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise R7500PrefixBridgeError(f"{field} is not finite")
        return value
    if isinstance(value, list):
        return [
            _structural_json_value(item, field=f"{field}[{index}]")
            for index, item in enumerate(value)
        ]
    raise R7500PrefixBridgeError(
        f"{field} contains a non-whitelisted structural value"
    )


def _closed_mapping_projection(
    value: Any, *, allowed_fields: frozenset[str], field: str
) -> dict[str, Any]:
    mapping = _require_mapping(value, field=field)
    unknown = set(mapping) - allowed_fields
    missing = allowed_fields - set(mapping)
    if unknown or missing:
        raise R7500PrefixBridgeError(
            f"{field} fields drifted; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    return {
        key: _structural_json_value(mapping[key], field=f"{field}.{key}")
        for key in sorted(allowed_fields)
    }


def _periodic_checkpoint_projection(value: Any, *, field: str) -> dict[str, Any]:
    row = _require_mapping(value, field=field)
    unknown = set(row) - PERIODIC_CHECKPOINT_FIELDS
    missing = PERIODIC_CHECKPOINT_FIELDS - set(row)
    if unknown:
        raise R7500PrefixBridgeError(
            f"{field} contains unknown structural fields: {sorted(unknown)}"
        )
    if missing:
        raise R7500PrefixBridgeError(
            f"{field} lacks structural fields: {sorted(missing)}"
        )
    episodes_completed = _require_int(
        row.get("episodes_completed"),
        field=f"{field}.episodes_completed",
        minimum=1,
    )
    episode_index = _require_int(
        row.get("episode_index"), field=f"{field}.episode_index", minimum=0
    )
    if episode_index != episodes_completed - 1:
        raise R7500PrefixBridgeError(f"{field} episode index is inconsistent")
    if not isinstance(row.get("path"), str) or not row.get("path"):
        raise R7500PrefixBridgeError(f"{field}.path is missing")
    if row.get("checkpoint_kind") != "periodic-main-policy-trend":
        raise R7500PrefixBridgeError(f"{field}.checkpoint_kind is not periodic-main-policy-trend")
    if row.get("load_round_trip") != "PASS":
        raise R7500PrefixBridgeError(f"{field}.load_round_trip is not PASS")
    return {
        "episodes_completed": episodes_completed,
        "episode_index": episode_index,
        "path": str(row["path"]),
        "sha256": _require_sha256(row.get("sha256"), field=f"{field}.sha256"),
        "checkpoint_kind": "periodic-main-policy-trend",
        "load_round_trip": "PASS",
    }


def extract_structural_status(
    status: Mapping[str, Any],
    *,
    source_status_sha256: str,
    expected_arm: str,
) -> dict[str, Any]:
    """Extract the only status fields admissible in a bridge snapshot.

    ``status`` has already been parsed once by the bridge.  This function is a
    deliberately closed-world projection: it validates every structural field
    that it emits and copies exactly one EP500 periodic checkpoint row.  The
    outcome-bearing arrays and telemetry remain in the source file and are
    neither copied nor represented in the returned object.
    """

    if not isinstance(status, Mapping):  # pragma: no cover - _read_object guards this
        raise R7500PrefixBridgeError("source status must be an object")
    source_sha = _require_sha256(source_status_sha256, field="source_status_sha256")
    if status.get("schema") != SOURCE_STATUS_SCHEMA:
        raise R7500PrefixBridgeError("source status schema is not the canonical trend schema")
    if status.get("status") != "complete":
        raise R7500PrefixBridgeError("source status is not complete")
    if status.get("arm") != expected_arm:
        raise R7500PrefixBridgeError("source status arm identity drifted")

    required_scalars = (
        "run_mode",
        "label",
        "authority_path",
        "claim_ceiling",
    )
    for field in required_scalars:
        if not isinstance(status.get(field), str) or not status.get(field):
            raise R7500PrefixBridgeError(f"source status {field} is missing")
    episodes_planned = _require_int(
        status.get("episodes_planned"), field="source status episodes_planned", minimum=1
    )
    episodes_executed = _require_int(
        status.get("episodes_executed"),
        field="source status episodes_executed",
        minimum=0,
    )
    users = _require_int(status.get("users"), field="source status users", minimum=1)
    seeds = _require_mapping(status.get("seeds"), field="source status seeds")
    if set(seeds) != {"training", "environment", "mobility"}:
        raise R7500PrefixBridgeError("source status seeds have unknown or missing fields")
    canonical_seeds: dict[str, int] = {}
    for field in ("training", "environment", "mobility"):
        canonical_seeds[field] = _require_int(
            seeds.get(field), field=f"source status seeds.{field}"
        )
    trainer_config = _closed_mapping_projection(
        status.get("trainer_config"),
        allowed_fields=TRAINER_CONFIG_FIELDS,
        field="source status trainer_config",
    )
    runtime_authority = _closed_mapping_projection(
        status.get("runtime_authority"),
        allowed_fields=RUNTIME_AUTHORITY_FIELDS,
        field="source status runtime_authority",
    )
    runtime = _closed_mapping_projection(
        status.get("runtime"),
        allowed_fields=RUNTIME_FIELDS,
        field="source status runtime",
    )
    for field in ("prereg_path", "tle_root_path"):
        if not isinstance(runtime_authority[field], str) or not runtime_authority[field]:
            raise R7500PrefixBridgeError(
                f"source status runtime_authority.{field} is missing"
            )
    for field in ("prereg_sha256", "tle_file_set_sha256"):
        _require_sha256(
            runtime_authority[field],
            field=f"source status runtime_authority.{field}",
        )
    _require_int(
        runtime_authority["tle_file_count"],
        field="source status runtime_authority.tle_file_count",
        minimum=1,
    )
    for field in RUNTIME_FIELDS:
        if not isinstance(runtime[field], str) or not runtime[field]:
            raise R7500PrefixBridgeError(f"source status runtime.{field} is missing")
    if status.get("formal_training_authorized") is not False:
        raise R7500PrefixBridgeError("source status formal training authorization drifted")

    result = _require_mapping(status.get("result"), field="source status result")
    result_required = {
        "episodes",
        "checkpoint_sha256",
        "checkpoint_every_episodes",
        "periodic_checkpoint_count",
        "periodic_checkpoints",
    }
    if result_required - set(result):
        raise R7500PrefixBridgeError(
            "source status result lacks structural fields: "
            f"{sorted(result_required - set(result))}"
        )
    result_episodes = _require_int(
        result.get("episodes"), field="source status result.episodes", minimum=1
    )
    checkpoint_every = _require_int(
        result.get("checkpoint_every_episodes"),
        field="source status result.checkpoint_every_episodes",
        minimum=1,
    )
    periodic_count = _require_int(
        result.get("periodic_checkpoint_count"),
        field="source status result.periodic_checkpoint_count",
        minimum=1,
    )
    periodic = result.get("periodic_checkpoints")
    if not isinstance(periodic, list) or len(periodic) != periodic_count:
        raise R7500PrefixBridgeError("source status periodic checkpoint count is inconsistent")
    periodic_episode_numbers = []
    for index, row in enumerate(periodic):
        row = _require_mapping(
            row, field=f"source status periodic_checkpoints[{index}]"
        )
        periodic_episode_numbers.append(
            _require_int(
                row.get("episodes_completed"),
                field=(
                    f"source status periodic_checkpoints[{index}].episodes_completed"
                ),
                minimum=1,
            )
        )
    expected_periodic_episode_numbers = list(
        range(checkpoint_every, result_episodes + 1, checkpoint_every)
    )
    if periodic_episode_numbers != expected_periodic_episode_numbers:
        raise R7500PrefixBridgeError(
            "source status periodic checkpoint cadence is incomplete or reordered"
        )
    ep500_rows = [
        _periodic_checkpoint_projection(row, field=f"source status periodic_checkpoints[{index}]")
        for index, row in enumerate(periodic)
        if isinstance(row, Mapping) and row.get("episodes_completed") == 500
    ]
    if len(ep500_rows) != 1:
        raise R7500PrefixBridgeError("source status lacks one exact EP500 checkpoint row")
    # Preserve completion fields needed to reject partial/resumed treatment runs;
    # baseline legitimately has no result-level start/completion scope.
    optional_result = {
        field: result.get(field)
        for field in (
            "start_episode",
            "episodes_executed",
            "episodes_completed",
            "artifact_scope",
        )
    }
    for field in ("start_episode", "episodes_executed", "episodes_completed"):
        value = optional_result[field]
        if value is not None:
            _require_int(value, field=f"source status result.{field}", minimum=0)
    if optional_result["artifact_scope"] is not None and not isinstance(
        optional_result["artifact_scope"], str
    ):
        raise R7500PrefixBridgeError("source status result.artifact_scope is malformed")

    return {
        "schema": STATUS_SIDECAR_SCHEMA,
        "source_status_schema": SOURCE_STATUS_SCHEMA,
        "source_status_sha256": source_sha,
        "status": "complete",
        "run_mode": str(status["run_mode"]),
        "arm": expected_arm,
        "label": str(status["label"]),
        "episodes_planned": episodes_planned,
        "episodes_executed": episodes_executed,
        "users": users,
        "seeds": canonical_seeds,
        "trainer_config": trainer_config,
        "authority_path": str(status["authority_path"]),
        "runtime_authority": runtime_authority,
        "runtime": runtime,
        "formal_training_authorized": False,
        "claim_ceiling": str(status["claim_ceiling"]),
        "result": {
            "episodes": result_episodes,
            **optional_result,
            "checkpoint_sha256": _require_sha256(
                result.get("checkpoint_sha256"),
                field="source status result.checkpoint_sha256",
            ),
            "checkpoint_every_episodes": checkpoint_every,
            "periodic_checkpoint_count": periodic_count,
            # One row is sufficient for EP500 reconciliation and avoids
            # emitting the remaining outcome-adjacent checkpoint history.
            "periodic_checkpoints": ep500_rows,
        },
    }


def validate_structural_status_sidecar(
    sidecar: Mapping[str, Any],
    *,
    expected_source_sha256: str | None = None,
    expected_arm: str | None = None,
) -> Mapping[str, Any]:
    """Validate a redacted sidecar without opening its full source status."""

    if not isinstance(sidecar, Mapping):
        raise R7500PrefixBridgeError("status sidecar must be an object")
    unknown = set(sidecar) - STATUS_SIDECAR_FIELDS
    missing = STATUS_SIDECAR_FIELDS - set(sidecar)
    if unknown:
        raise R7500PrefixBridgeError(
            f"status sidecar contains unknown structural fields: {sorted(unknown)}"
        )
    if missing:
        raise R7500PrefixBridgeError(
            f"status sidecar lacks structural fields: {sorted(missing)}"
        )
    if sidecar.get("schema") != STATUS_SIDECAR_SCHEMA:
        raise R7500PrefixBridgeError("status sidecar schema drifted")
    if sidecar.get("source_status_schema") != SOURCE_STATUS_SCHEMA:
        raise R7500PrefixBridgeError("status sidecar source schema drifted")
    source_sha = _require_sha256(
        sidecar.get("source_status_sha256"), field="status sidecar source_status_sha256"
    )
    if expected_source_sha256 is not None and source_sha != _require_sha256(
        expected_source_sha256, field="expected source_status_sha256"
    ):
        raise R7500PrefixBridgeError("status sidecar source SHA drifted")
    if sidecar.get("status") != "complete":
        raise R7500PrefixBridgeError("status sidecar completion status drifted")
    arm = sidecar.get("arm")
    if not isinstance(arm, str) or not arm:
        raise R7500PrefixBridgeError("status sidecar arm is missing")
    if expected_arm is not None and arm != expected_arm:
        raise R7500PrefixBridgeError("status sidecar arm identity drifted")
    for field in ("run_mode", "label", "authority_path", "claim_ceiling"):
        if not isinstance(sidecar.get(field), str) or not sidecar.get(field):
            raise R7500PrefixBridgeError(f"status sidecar {field} is missing")
    for field in ("episodes_planned", "episodes_executed", "users"):
        _require_int(sidecar.get(field), field=f"status sidecar {field}", minimum=0)
    if not isinstance(sidecar.get("seeds"), Mapping) or set(sidecar["seeds"]) != {
        "training",
        "environment",
        "mobility",
    }:
        raise R7500PrefixBridgeError("status sidecar seeds have unknown or missing fields")
    for field in ("training", "environment", "mobility"):
        _require_int(sidecar["seeds"].get(field), field=f"status sidecar seeds.{field}")
    _closed_mapping_projection(
        sidecar.get("trainer_config"),
        allowed_fields=TRAINER_CONFIG_FIELDS,
        field="status sidecar trainer_config",
    )
    runtime_authority = _closed_mapping_projection(
        sidecar.get("runtime_authority"),
        allowed_fields=RUNTIME_AUTHORITY_FIELDS,
        field="status sidecar runtime_authority",
    )
    runtime = _closed_mapping_projection(
        sidecar.get("runtime"),
        allowed_fields=RUNTIME_FIELDS,
        field="status sidecar runtime",
    )
    for field in ("prereg_path", "tle_root_path"):
        if not isinstance(runtime_authority[field], str) or not runtime_authority[field]:
            raise R7500PrefixBridgeError(
                f"status sidecar runtime_authority.{field} is missing"
            )
    for field in ("prereg_sha256", "tle_file_set_sha256"):
        _require_sha256(
            runtime_authority[field],
            field=f"status sidecar runtime_authority.{field}",
        )
    _require_int(
        runtime_authority["tle_file_count"],
        field="status sidecar runtime_authority.tle_file_count",
        minimum=1,
    )
    for field in RUNTIME_FIELDS:
        if not isinstance(runtime[field], str) or not runtime[field]:
            raise R7500PrefixBridgeError(f"status sidecar runtime.{field} is missing")
    if sidecar.get("formal_training_authorized") is not False:
        raise R7500PrefixBridgeError("status sidecar formal training authorization drifted")
    result = sidecar.get("result")
    if not isinstance(result, Mapping):
        raise R7500PrefixBridgeError("status sidecar result is missing")
    result_unknown = set(result) - STATUS_RESULT_SIDECAR_FIELDS
    result_missing = STATUS_RESULT_SIDECAR_FIELDS - set(result)
    if result_unknown:
        raise R7500PrefixBridgeError(
            "status sidecar result contains unknown structural fields: "
            f"{sorted(result_unknown)}"
        )
    if result_missing:
        raise R7500PrefixBridgeError(
            "status sidecar result lacks structural fields: "
            f"{sorted(result_missing)}"
        )
    for field in ("episodes", "checkpoint_every_episodes", "periodic_checkpoint_count"):
        _require_int(result.get(field), field=f"status sidecar result.{field}", minimum=1)
    for field in ("start_episode", "episodes_executed", "episodes_completed"):
        if result.get(field) is not None:
            _require_int(result[field], field=f"status sidecar result.{field}", minimum=0)
    if result.get("artifact_scope") is not None and not isinstance(
        result.get("artifact_scope"), str
    ):
        raise R7500PrefixBridgeError("status sidecar result.artifact_scope is malformed")
    _require_sha256(
        result.get("checkpoint_sha256"),
        field="status sidecar result.checkpoint_sha256",
    )
    periodic = result.get("periodic_checkpoints")
    if not isinstance(periodic, list) or len(periodic) != 1:
        raise R7500PrefixBridgeError("status sidecar must contain one EP500 checkpoint row")
    projected = _periodic_checkpoint_projection(
        periodic[0], field="status sidecar result.periodic_checkpoints[0]"
    )
    if projected["episodes_completed"] != 500:
        raise R7500PrefixBridgeError("status sidecar periodic row is not EP500")
    return sidecar


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _copy_stable(source: Path, target: Path, *, label: str) -> str:
    source = Path(source).resolve()
    if not source.is_file():
        raise R7500PrefixBridgeError(f"{label} is missing: {source}")
    before = authority.sha256_file(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    copied = authority.sha256_file(target)
    after = authority.sha256_file(source)
    if before != copied or before != after:
        raise R7500PrefixBridgeError(f"{label} changed while it was being snapshotted")
    return copied


def load_and_validate_authority(
    path: Path, *, repo: Path = REPO, tle_root: Path
) -> tuple[dict[str, Any], str]:
    authority_path = Path(path).expanduser().resolve()
    request = _read_object(authority_path, label="R7 authority")
    try:
        validated = authority.validate_r7_500_authority(
            request, repo=repo, tle_root=tle_root
        )
    except Exception as error:
        raise R7500PrefixBridgeError("R7 authority failed validation") from error
    return validated, authority.sha256_file(authority_path)


def _validate_canonical_command(
    command: Any,
    *,
    arm: str,
    authority_path: Path,
    arm_root: Path,
    tle_root: Path,
    repo: Path,
) -> list[str]:
    if not isinstance(command, list) or any(not isinstance(item, str) for item in command):
        raise R7500PrefixBridgeError(f"{arm} command is malformed")
    expected_tail = [
        str((repo / ARM_RUNNER_RELATIVE).resolve()),
        "--authority",
        str(authority_path.resolve()),
        "--arm",
        arm,
        "--output-dir",
        str(arm_root.resolve()),
        "--tle-root",
        str(tle_root.resolve()),
    ]
    if len(command) != 1 + len(expected_tail):
        raise R7500PrefixBridgeError(f"{arm} command has noncanonical arguments")
    if Path(command[0]).expanduser().resolve() != Path(sys.executable).resolve():
        raise R7500PrefixBridgeError(f"{arm} command Python interpreter drifted")
    normalized_tail = [str(Path(command[1]).expanduser().resolve()), *command[2:]]
    if normalized_tail != expected_tail:
        raise R7500PrefixBridgeError(f"{arm} command identity drifted")
    return list(command)


def _snapshot_one(
    *,
    validated: Mapping[str, Any],
    lr_key: str,
    arm: str,
    repo: Path,
    tle_root: Path,
    staging: Path,
) -> dict[str, Any]:
    base = validated["validated_base_authorities"][lr_key]
    matrix_root = (repo / validated["source_matrix_paths"][lr_key]).resolve()
    arm_root = matrix_root / "arms" / arm
    matrix_status_source = matrix_root / "matrix-status.json"
    journal_source = arm_root / "run-journal.json"
    checkpoint_source = arm_root / "checkpoints" / CHECKPOINT_NAME
    destination = staging / "inputs" / f"lr-{lr_key}" / arm

    matrix_sha = _copy_stable(
        matrix_status_source, destination / "matrix-status.json", label="matrix status"
    )
    journal_sha = _copy_stable(
        journal_source, destination / "run-journal.json", label=f"{arm} run journal"
    )
    checkpoint_snapshot = destination / CHECKPOINT_NAME
    checkpoint_sha = _copy_stable(
        checkpoint_source, checkpoint_snapshot, label=f"{arm} EP500 checkpoint"
    )

    matrix = _read_object(destination / "matrix-status.json", label="matrix status snapshot")
    journal = _read_object(destination / "run-journal.json", label=f"{arm} journal snapshot")
    status_source = arm_root / "status.json"
    if not status_source.is_file():
        raise R7500PrefixBridgeError(f"{arm} completed process lacks status.json")
    # Parse the outcome-bearing source exactly once, and immediately project it
    # into a closed structural sidecar.  The source bytes themselves never enter
    # the bridge staging tree.
    status_sha_before = authority.sha256_file(status_source)
    status = _read_object(status_source, label=f"{arm} completed status")
    status_sha_after = authority.sha256_file(status_source)
    if status_sha_before != status_sha_after:
        raise R7500PrefixBridgeError(f"{arm} status changed while it was being parsed")
    status_sha = status_sha_before
    status_sidecar = extract_structural_status(
        status,
        source_status_sha256=status_sha,
        expected_arm=arm,
    )
    status_snapshot = destination / STATUS_SIDECAR_NAME
    _write_json(status_snapshot, status_sidecar)
    status_sidecar_sha = authority.sha256_file(status_snapshot)
    expected_authority = Path(str(base["authority_path"])).resolve()
    recorded_authority = Path(str(matrix.get("authority"))).expanduser().resolve()
    if recorded_authority != expected_authority:
        raise R7500PrefixBridgeError(f"{arm} matrix authority path mismatch")
    if authority.sha256_file(expected_authority) != base["authority_sha256"]:
        raise R7500PrefixBridgeError(f"{arm} source authority bytes drifted")
    if matrix.get("schema") != MATRIX_SCHEMA:
        raise R7500PrefixBridgeError(f"{arm} matrix schema drifted")
    if (
        matrix.get("status") != "complete"
        or matrix.get("authority_sha256") != base["authority_sha256"]
        or matrix.get("episodes") != 1500
        or matrix.get("learning_rate") != float(lr_key)
    ):
        raise R7500PrefixBridgeError(f"{arm} source matrix is not complete")
    runs = matrix.get("runs")
    verifications = matrix.get("verifications")
    expected_arms = list(base["arms"])
    if (
        not isinstance(runs, Mapping)
        or set(runs) != set(expected_arms)
        or not isinstance(verifications, Mapping)
        or set(verifications) != set(expected_arms)
    ):
        raise R7500PrefixBridgeError(f"{arm} complete matrix grid drifted")
    for source_arm in expected_arms:
        source_run = runs[source_arm]
        source_verification = verifications[source_arm]
        if (
            not isinstance(source_run, Mapping)
            or source_run.get("status") != "process_complete"
            or source_run.get("exit_code") != 0
            or not isinstance(source_verification, Mapping)
            or source_verification.get("status") != "PASS"
            or source_verification.get("episodes_completed") != 1500
        ):
            raise R7500PrefixBridgeError(
                f"{arm} source matrix arm {source_arm} is not verified complete"
            )
    selected_verification = verifications.get(arm)
    if (
        not isinstance(selected_verification, Mapping)
        or selected_verification.get("status_sha256") != status_sha
    ):
        raise R7500PrefixBridgeError(
            f"{arm} matrix verification is not bound to the live source status SHA"
        )
    run = runs.get(arm) if isinstance(runs, Mapping) else None
    if not isinstance(run, Mapping) or run.get("arm") != arm:
        raise R7500PrefixBridgeError(f"{arm} matrix run entry is missing")
    run_status = run.get("status")
    if run_status != "process_complete" or run.get("exit_code") != 0:
        raise R7500PrefixBridgeError(f"{arm} source run status is not admissible")
    command = _validate_canonical_command(
        run.get("command"),
        arm=arm,
        authority_path=expected_authority,
        arm_root=arm_root,
        tle_root=tle_root,
        repo=repo,
    )

    config = journal.get("config")
    trainer_config = journal.get("trainer_config")
    if not isinstance(config, Mapping) or not isinstance(trainer_config, Mapping):
        raise R7500PrefixBridgeError(f"{arm} journal configuration is missing")
    if journal.get("schema") != JOURNAL_SCHEMA:
        raise R7500PrefixBridgeError(f"{arm} journal schema drifted")
    if journal.get("status") != "complete":
        raise R7500PrefixBridgeError(f"{arm} journal status disagrees with matrix run")
    exact_config = {
        "arm": arm,
        "episodes": 1500,
        "users": 100,
        "train_seed": authority.TRAINING_SEEDS["training"],
        "env_seed": authority.TRAINING_SEEDS["environment"],
        "mobility_seed": authority.TRAINING_SEEDS["mobility"],
        "checkpoint_every": 100,
        "max_c2_candidates": 9,
        "beta": 0.25,
        "acrm_eta": 1.0,
    }
    for field, expected in exact_config.items():
        if config.get(field) != expected:
            raise R7500PrefixBridgeError(f"{arm} journal {field} drifted")

    try:
        payload = read_checkpoint(checkpoint_snapshot, map_location="cpu")
        identity = checkpoint_tools.validate_checkpoint_payload(
            payload,
            validated=base,
            trainer_config=trainer_config,
            episode_index=499,
            checkpoint_kind="periodic-main-policy-trend",
            label=f"lr={lr_key} {arm} EP500",
        )
    except Exception as error:
        raise R7500PrefixBridgeError(f"{arm} EP500 checkpoint identity failed") from error
    if checkpoint_sha == identity["online_policy_sha256"]:
        raise R7500PrefixBridgeError(
            f"{arm} checkpoint artifact SHA unexpectedly aliases its policy digest"
        )
    return {
        "learning_rate": float(lr_key),
        "arm": arm,
        "source_status": "completed_source_ep500_pending_reconciliation",
        "source_matrix_root": str(matrix_root),
        "source_arm_root": str(arm_root),
        "source_authority": {
            "path": str(expected_authority),
            "sha256": base["authority_sha256"],
            "pin_map_sha256": authority.canonical_json_sha256(base["pinned_files"]),
        },
        "matrix_status": {
            "source": str(matrix_status_source),
            "snapshot": str((destination / "matrix-status.json").relative_to(staging)),
            "sha256": matrix_sha,
            "status": matrix.get("status"),
        },
        "run": {
            "status": run_status,
            "command": list(command),
            "journal_source": str(journal_source),
            "journal_snapshot": str((destination / "run-journal.json").relative_to(staging)),
            "journal_sha256": journal_sha,
        },
        "checkpoint": {
            "source": str(checkpoint_source),
            "snapshot": str(checkpoint_snapshot.relative_to(staging)),
            "artifact_sha256": checkpoint_sha,
            "episodes_completed": 500,
            **identity,
            "finite_state": "PASS",
            "load_round_trip": "PASS",
        },
        "completion_status": {
            "source": str(status_source),
            "snapshot": str(status_snapshot.relative_to(staging)),
            "source_status_sha256": status_sha,
            "sidecar_sha256": status_sidecar_sha,
            "sidecar_schema": STATUS_SIDECAR_SCHEMA,
            "outcome_bearing_source_status_parsed_by_whitelist_extractor": True,
            "outcome_metric_fields_copied": False,
            "outcome_metric_fields_emitted": False,
            "outcome_metric_fields_used_for_admission": False,
            "outcome_metric_fields_admitted": False,
        },
        "reconciled": False,
    }


def build_prefix_bridge(
    *,
    authority_path: Path,
    output_dir: Path,
    tle_root: Path,
    repo: Path = REPO,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    validated, authority_sha = load_and_validate_authority(
        authority_path, repo=repo, tle_root=tle_root
    )
    output = Path(output_dir).expanduser().resolve()
    expected_output = (repo / validated["bridge_output"]).resolve()
    if output != expected_output:
        raise R7500PrefixBridgeError("bridge output path drifted from the R7 authority")
    try:
        output, staging = output_tools.reserve_output_directory(
            output,
            marker={
                "schema": "r7-output-reservation-v1",
                "artifact": "prefix-bridge",
                "required_labels": authority.REQUIRED_LABELS,
            },
        )
    except FileExistsError as error:
        raise FileExistsError(f"refusing to overwrite R7 prefix bridge: {output}") from error
    try:
        master_snapshot = staging / "inputs" / "r7-authority.json"
        master_sha = _copy_stable(
            Path(authority_path).expanduser().resolve(),
            master_snapshot,
            label="R7 master authority",
        )
        if master_sha != authority_sha:
            raise R7500PrefixBridgeError("R7 authority changed after validation")
        prefixes = [
            _snapshot_one(
                validated=validated,
                lr_key=lr_key,
                arm=arm,
                repo=repo,
                tle_root=tle_root,
                staging=staging,
            )
            for lr_key in ("0.001", "0.01")
            for arm in authority.BRIDGED_ARMS
        ]
        receipt = {
            "schema": SCHEMA,
            "status": "PASS",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "authority": {
                "source": str(Path(authority_path).expanduser().resolve()),
                "snapshot": str(master_snapshot.relative_to(staging)),
                "sha256": authority_sha,
                "pin_map_sha256": validated["pin_map_sha256"],
            },
            "endpoint_episodes": 500,
            "prefix_arms": list(authority.PREFIX_ARMS),
            "bridged_arms": list(authority.BRIDGED_ARMS),
            "learning_rates": list(authority.ALLOWED_LEARNING_RATES),
            "outcome_bearing_source_status_parsed_by_whitelist_extractor": True,
            "outcome_metric_fields_copied": False,
            "outcome_metric_fields_emitted": False,
            "outcome_metric_fields_used_for_admission": False,
            "outcome_metric_fields_admitted": False,
            "checkpoint_selection_performed": False,
            "evaluation_authorized": False,
            "routing_authorized": False,
            "reconciliation_required": True,
            "prefixes": prefixes,
        }
        _write_json(staging / "prefix-bridge-receipt.json", receipt)
        output_tools.publish_receipt_last(
            staging=staging,
            output=output,
            receipt_name="prefix-bridge-receipt.json",
        )
        output_tools.finalize_publication(
            output=output,
            receipt_name="prefix-bridge-receipt.json",
        )
        return receipt
    except Exception:
        output_tools.abort_reserved_output(staging=staging, output=output)
        raise


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    build_prefix_bridge(
        authority_path=args.authority,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
    )
    print(Path(args.output_dir).expanduser().resolve() / "prefix-bridge-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
