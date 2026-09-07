#!/usr/bin/env python3
"""Validate two V0.3A 1,500EP matrices and close the LR decision.

This is a post-run developmental evidence adapter.  It does not launch
training, select a checkpoint, authorize 3,000EP, or upgrade the evidence to
Chapter 5.  The input matrices remain the authority; this tool independently
checks their final Main-only EE sweeps before applying the frozen LR rule.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LEGACY_DIR = REPO / ".scratch" / "smc-er-short-ep"
for path in (HERE, LEGACY_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_v03a_lr_selector as lr_selector  # noqa: E402
import c2_v03a_trend_arm as arm_runner  # noqa: E402
from c2_v03a_trend_authority import (  # noqa: E402
    ALLOWED_ARMS,
    CLAIM_CEILING,
)
from c2_v03a_trend_matrix import (  # noqa: E402
    ARM_LABELS,
    SCHEMA as MATRIX_SCHEMA,
)
from mcrl.artifacts import read_checkpoint  # noqa: E402
from pilot100_sweep_verifier import verify_pilot100_sweep  # noqa: E402
from render_sweep_svg import render_sweep  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-postrun-bundle-v1"
CONTRAST_SCHEMA = "multi-catfish-mcrl-c2-v03a-ablation-contrasts-v1"
MATRIX_EPISODES = 1500
CHECKPOINT_EVERY_EPISODES = 100
EXPECTED_LEARNING_RATES = (0.001, 0.01)
POSTRUN_CLAIM_CEILING = (
    "TWO_ONE_SEED_1500EP_DEVELOPMENTAL_TRENDS_NOT_CHAPTER5_"
    "NOT_FORMAL_EFFICACY_NOT_9000_NOT_DEPLOYMENT_NOT_AUCTION_NOT_COORDINATION"
)
TELEMETRY_SCHEMA = "multi-catfish-c2-v03-run-telemetry-v1"
EXPECTED_ACTIVE_SOURCES = {
    "B000": (),
    "F111": ("C1", "C2", "C3"),
    "A011": ("C2", "C3"),
    "A101": ("C1", "C3"),
    "A110": ("C1", "C2"),
}


class V03APostrunError(RuntimeError):
    """Raised when post-run evidence is incomplete, inconsistent, or drifted."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V03APostrunError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise V03APostrunError(f"{label} must be a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _same_float(value: Any, expected: float) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and math.isclose(float(value), expected, rel_tol=0.0, abs_tol=1e-15)
    )


def _resolved_recorded_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return Path(value).expanduser().resolve()
    except (OSError, RuntimeError):
        return None


def _repo_file(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise V03APostrunError(f"validated authority lacks {field}")
    raw = Path(value).expanduser()
    path = raw.resolve() if raw.is_absolute() else (REPO / raw).resolve()
    if not path.is_file():
        raise V03APostrunError(f"validated {field} is missing: {path}")
    return path


def _canonical_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as error:
        raise V03APostrunError("value cannot form a canonical JSON identity") from error
    return hashlib.sha256(encoded).hexdigest()


def _digest_state_value(digest: Any, value: Any) -> None:
    """Hash nested tensor state without relying on torch serialization bytes."""

    if isinstance(value, Mapping):
        digest.update(b"{")
        for key in sorted(value, key=str):
            digest.update(str(key).encode("utf-8"))
            digest.update(b"\0")
            _digest_state_value(digest, value[key])
        digest.update(b"}")
        return
    if isinstance(value, (list, tuple)):
        digest.update(b"[")
        for item in value:
            _digest_state_value(digest, item)
        digest.update(b"]")
        return
    if hasattr(value, "detach") and hasattr(value, "cpu"):
        array = np.asarray(value.detach().cpu())
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(str(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
        return
    if isinstance(value, np.ndarray):
        array = np.ascontiguousarray(value)
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(str(tuple(array.shape)).encode("ascii"))
        digest.update(array.tobytes(order="C"))
        return
    try:
        digest.update(
            json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")
        )
    except (TypeError, ValueError, OverflowError) as error:
        raise V03APostrunError(
            f"checkpoint state contains unsupported {type(value).__name__}"
        ) from error


def checkpoint_policy_sha256(payload: Any) -> str:
    networks = getattr(payload, "q_networks", None)
    if not isinstance(networks, list) or len(networks) != 3:
        raise V03APostrunError("checkpoint must contain exactly three Main Q networks")
    digest = hashlib.sha256()
    digest.update(b"multi-catfish-main-online-policy-v1\0")
    _digest_state_value(digest, networks)
    return digest.hexdigest()


def _validate_checkpoint_payload(
    payload: Any,
    *,
    validated: Mapping[str, Any],
    trainer_config: Mapping[str, Any],
    episode_index: int,
    checkpoint_kind: str,
    label: str,
) -> dict[str, Any]:
    seeds = validated["seeds"]
    exact = {
        "episode": episode_index,
        "checkpoint_kind": checkpoint_kind,
        "train_seed": seeds["training"],
        "env_seed": seeds["environment"],
        "mobility_seed": seeds["mobility"],
    }
    for field, expected in exact.items():
        if getattr(payload, field, None) != expected:
            raise V03APostrunError(f"{label} payload {field} mismatch")
    if (
        type(getattr(payload, "state_dim", None)) is not int
        or payload.state_dim < 1
        or type(getattr(payload, "action_dim", None)) is not int
        or payload.action_dim < 1
    ):
        raise V03APostrunError(f"{label} payload dimensions are invalid")
    if getattr(payload, "optimizers", None) is None:
        raise V03APostrunError(f"{label} lacks optimizer state")
    targets = getattr(payload, "target_networks", None)
    if not isinstance(targets, list) or len(targets) != 3:
        raise V03APostrunError(f"{label} must contain exactly three target networks")
    payload_config = getattr(payload, "trainer_config", None)
    if not isinstance(payload_config, Mapping):
        raise V03APostrunError(f"{label} trainer config is missing")
    if _canonical_sha256(payload_config) != _canonical_sha256(trainer_config):
        raise V03APostrunError(f"{label} trainer config identity mismatch")
    if not _same_float(
        payload_config.get("learning_rate"), float(validated["learning_rate"])
    ):
        raise V03APostrunError(f"{label} learning rate mismatch")
    return {
        "episode_index": episode_index,
        "checkpoint_kind": checkpoint_kind,
        "train_seed": int(payload.train_seed),
        "env_seed": int(payload.env_seed),
        "mobility_seed": int(payload.mobility_seed),
        "state_dim": int(payload.state_dim),
        "action_dim": int(payload.action_dim),
        "trainer_config_sha256": _canonical_sha256(payload_config),
        "online_policy_sha256": checkpoint_policy_sha256(payload),
    }


def _finite_number(value: Any, *, field: str, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V03APostrunError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0.0):
        raise V03APostrunError(f"{field} is invalid")
    return result


def _validate_telemetry(
    telemetry: Any,
    *,
    episodes: int,
    users: int,
    label: str,
) -> dict[str, Any]:
    if not isinstance(telemetry, Mapping) or telemetry.get("schema") != TELEMETRY_SCHEMA:
        raise V03APostrunError(f"{label} telemetry schema mismatch")
    main = telemetry.get("main")
    c2 = telemetry.get("c2")
    if not isinstance(main, Mapping) or not isinstance(c2, Mapping):
        raise V03APostrunError(f"{label} telemetry ledgers are missing")
    steps = main.get("steps")
    expected_steps = episodes * 10
    if steps != expected_steps:
        raise V03APostrunError(f"{label} telemetry Main step count mismatch")
    bits = _finite_number(
        main.get("useful_bits"), field=f"{label}.main.useful_bits", nonnegative=True
    )
    energy = _finite_number(
        main.get("energy_j"), field=f"{label}.main.energy_j", nonnegative=True
    )
    if energy <= 0.0:
        raise V03APostrunError(f"{label} telemetry has nonpositive system energy")
    ee = _finite_number(
        main.get("ratio_of_sums_ee_bits_per_j"),
        field=f"{label}.main.ratio_of_sums_ee_bits_per_j",
        nonnegative=True,
    )
    if not math.isclose(ee, bits / energy, rel_tol=1e-12, abs_tol=1e-8):
        raise V03APostrunError(f"{label} telemetry EE is not ratio-of-sums")
    served = main.get("served_user_intervals")
    intervals = main.get("user_intervals")
    if (
        type(served) is not int
        or type(intervals) is not int
        or intervals != expected_steps * users
        or not 0 <= served <= intervals
    ):
        raise V03APostrunError(f"{label} telemetry service counts are invalid")
    served_fraction = _finite_number(
        main.get("served_fraction"),
        field=f"{label}.main.served_fraction",
        nonnegative=True,
    )
    if served_fraction > 1.0 or not math.isclose(
        served_fraction, served / intervals, rel_tol=1e-12, abs_tol=1e-12
    ):
        raise V03APostrunError(f"{label} telemetry served fraction mismatch")
    rewards = main.get("canonical_reward_sum")
    if (
        not isinstance(rewards, list)
        or len(rewards) != 3
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in rewards
        )
    ):
        raise V03APostrunError(f"{label} direct r1/r2/r3 totals are invalid")

    integer_fields = (
        "schedules",
        "empty_anchor_attempts",
        "scheduled_candidates",
        "options_executed",
        "option_primitive_steps",
        "admitted_options",
        "q2f_updates",
        "joint_commits",
    )
    for field in integer_fields:
        if type(c2.get(field)) is not int or int(c2[field]) < 0:
            raise V03APostrunError(f"{label}.c2.{field} is invalid")
    outcomes = c2.get("candidate_outcomes")
    choices = c2.get("choice_counts")
    if not isinstance(outcomes, Mapping) or not isinstance(choices, Mapping):
        raise V03APostrunError(f"{label} C2 outcome/choice ledgers are missing")
    outcome_values: dict[str, int] = {}
    for field in ("certificate_pass", "certificate_fail", "support_rejection", "contract_error"):
        value = outcomes.get(field)
        if type(value) is not int or value < 0:
            raise V03APostrunError(f"{label}.c2.candidate_outcomes.{field} is invalid")
        outcome_values[field] = value
    if outcome_values["contract_error"] != 0:
        raise V03APostrunError(f"{label} C2 contract errors are nonzero")
    if sum(outcome_values.values()) != c2["scheduled_candidates"]:
        raise V03APostrunError(f"{label} C2 candidate outcome totals mismatch")
    choice_values: list[int] = []
    for field in ("K0", "K1", "K>=2"):
        value = choices.get(field)
        if type(value) is not int or value < 0:
            raise V03APostrunError(f"{label}.c2.choice_counts.{field} is invalid")
        choice_values.append(value)
    if sum(choice_values) != c2["schedules"]:
        raise V03APostrunError(f"{label} C2 choice totals mismatch")
    forecast = _finite_number(
        c2.get("forecast_wall_time_s"),
        field=f"{label}.c2.forecast_wall_time_s",
        nonnegative=True,
    )
    if not (
        c2["joint_commits"] <= c2["q2f_updates"] <= c2["admitted_options"]
        <= c2["options_executed"]
    ):
        raise V03APostrunError(f"{label} C2 dose ordering is impossible")
    return {
        "main_steps": steps,
        "useful_bits": bits,
        "system_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": ee,
        "served_fraction": served_fraction,
        "canonical_reward_sum": [float(value) for value in rewards],
        "c2_schedules": int(c2["schedules"]),
        "c2_choice_counts": dict(choices),
        "c2_candidate_outcomes": dict(outcomes),
        "c2_forecast_wall_time_s": forecast,
        "c2_options_executed": int(c2["options_executed"]),
        "c2_q2f_updates": int(c2["q2f_updates"]),
        "c2_joint_commits": int(c2["joint_commits"]),
    }


def _validate_sweep_csv_exports(output_dir: Path) -> dict[str, Any]:
    """Prove that the convenience CSVs are exact projections of verified JSON."""

    root = Path(output_dir).expanduser().resolve()
    try:
        raw_json = json.loads((root / "sweep-raw.json").read_text(encoding="utf-8"))
        summary_payload = json.loads(
            (root / "sweep-summary.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V03APostrunError("verified sweep JSON cannot be reopened for CSV QA") from error
    if not isinstance(raw_json, list) or not isinstance(summary_payload, Mapping):
        raise V03APostrunError("verified sweep JSON shape drifted during CSV QA")
    summary_rows = summary_payload.get("summary")
    if not isinstance(summary_rows, list):
        raise V03APostrunError("verified sweep summary rows are missing during CSV QA")
    projections = (
        (root / "sweep-raw.csv", raw_json),
        (
            root / "sweep-summary.csv",
            [
                {key: value for key, value in row.items() if key != "seed_rows"}
                for row in summary_rows
                if isinstance(row, Mapping)
            ],
        ),
    )
    receipts: dict[str, Any] = {}
    for csv_path, expected_rows in projections:
        try:
            with csv_path.open(newline="", encoding="utf-8") as stream:
                reader = csv.DictReader(stream)
                observed_rows = list(reader)
                fieldnames = reader.fieldnames
        except (OSError, UnicodeError, csv.Error) as error:
            raise V03APostrunError(f"sweep CSV is unreadable: {csv_path}") from error
        if len(observed_rows) != len(expected_rows):
            raise V03APostrunError(f"sweep CSV row count mismatch: {csv_path.name}")
        if expected_rows:
            expected_fields = set(expected_rows[0])
            if fieldnames is None or set(fieldnames) != expected_fields:
                raise V03APostrunError(f"sweep CSV field set mismatch: {csv_path.name}")
        for index, (observed, expected) in enumerate(
            zip(observed_rows, expected_rows, strict=True)
        ):
            if not isinstance(expected, Mapping) or any(
                observed.get(field) != ("" if value is None else str(value))
                for field, value in expected.items()
            ):
                raise V03APostrunError(
                    f"sweep CSV row {index} disagrees with JSON: {csv_path.name}"
                )
        receipts[csv_path.name] = {
            "path": str(csv_path),
            "sha256": sha256_file(csv_path),
            "rows": len(observed_rows),
            "status": "PASS",
        }
    return receipts


def _require_file_receipt(
    *, path: Path, recorded_path: Any, recorded_sha256: Any, label: str
) -> str:
    expected = Path(path).expanduser().resolve()
    if not expected.is_file() or expected.stat().st_size <= 0:
        raise V03APostrunError(f"{label} is missing or empty: {expected}")
    if _resolved_recorded_path(recorded_path) != expected:
        raise V03APostrunError(f"{label} recorded path mismatch")
    observed = sha256_file(expected)
    if recorded_sha256 != observed:
        raise V03APostrunError(f"{label} SHA-256 mismatch")
    return observed


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _validate_resume_source(
    result: Mapping[str, Any],
    *,
    start_episode: int,
    loop_config: Mapping[str, Any],
    trainer_config: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    source = result.get("resume_source")
    if not isinstance(source, Mapping):
        raise V03APostrunError(f"{label} resume source receipt is missing")
    source_path = _resolved_recorded_path(source.get("path"))
    if source_path is None:
        raise V03APostrunError(f"{label} resume source path is malformed")
    source_sha = _require_file_receipt(
        path=source_path,
        recorded_path=source.get("path"),
        recorded_sha256=source.get("sha256"),
        label=f"{label} resume source",
    )
    if (
        source.get("artifact_scope") != "new continuation segment"
        or source.get("episodes_completed") != start_episode
    ):
        raise V03APostrunError(f"{label} resume source boundary is inconsistent")
    try:
        payload = arm_runner.c2_runner._torch_load_runtime_state(source_path)
    except Exception as error:
        raise V03APostrunError(f"{label} resume source is not loadable") from error
    exact = {
        "schema": arm_runner.c2_runner.RUNTIME_STATE_SCHEMA,
        "format_version": arm_runner.c2_runner.RUNTIME_STATE_FORMAT_VERSION,
        "boundary": "episode",
        "episodes_completed": start_episode,
        "source_order": ["Main", "C1", "C2", "C3"],
        "loop_config": dict(loop_config),
        "trainer_config": dict(trainer_config),
    }
    for field, expected in exact.items():
        if payload.get(field) != expected:
            raise V03APostrunError(f"{label} resume snapshot {field} mismatch")
    main_state = payload.get("main_training_state")
    if (
        not isinstance(main_state, Mapping)
        or main_state.get("trainer_config") != dict(trainer_config)
    ):
        raise V03APostrunError(
            f"{label} resume snapshot Main trainer config mismatch"
        )
    snapshot_authority = payload.get("authority")
    result_authority = result.get("mechanism_authority")
    if not isinstance(snapshot_authority, Mapping) or not isinstance(
        result_authority, Mapping
    ):
        raise V03APostrunError(f"{label} resume mechanism authority is missing")
    if not _is_sha256(snapshot_authority.get("checkpoint_sha256")):
        raise V03APostrunError(f"{label} resume checkpoint authority is malformed")
    for field in ("environment_source_sha256", "reward_source_sha256"):
        expected = result_authority.get(field)
        if not _is_sha256(expected) or snapshot_authority.get(field) != expected:
            raise V03APostrunError(f"{label} resume {field} authority mismatch")
    return {
        "path": str(source_path),
        "sha256": source_sha,
        "episodes_completed": start_episode,
        "schema": payload["schema"],
        "format_version": payload["format_version"],
        "boundary": payload["boundary"],
        "environment_source_sha256": snapshot_authority[
            "environment_source_sha256"
        ],
        "reward_source_sha256": snapshot_authority["reward_source_sha256"],
    }


def validate_matrix(
    matrix_root: Path,
    *,
    tle_root: Path,
    expected_learning_rate: float,
) -> dict[str, Any]:
    """Validate one completed current-layout V0.3A matrix and its EE sweep."""

    root = Path(matrix_root).expanduser().resolve()
    matrix_path = root / "matrix-status.json"
    matrix = _read_object(matrix_path, label="matrix status")
    exact_matrix = {
        "schema": MATRIX_SCHEMA,
        "status": "complete",
        "episodes": MATRIX_EPISODES,
        "formal_training_authorized": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    for field, expected in exact_matrix.items():
        if matrix.get(field) != expected:
            raise V03APostrunError(f"matrix {field} mismatch: {root}")
    if not _same_float(matrix.get("learning_rate"), expected_learning_rate):
        raise V03APostrunError(f"matrix learning-rate mismatch: {root}")

    authority_path = _resolved_recorded_path(matrix.get("authority"))
    if authority_path is None or not authority_path.is_file():
        raise V03APostrunError("matrix authority path is missing")
    authority_sha = sha256_file(authority_path)
    if matrix.get("authority_sha256") != authority_sha:
        raise V03APostrunError("matrix authority SHA-256 mismatch")
    try:
        validated = arm_runner.load_and_validate_authority(
            authority_path, tle_root=Path(tle_root).expanduser().resolve()
        )
    except Exception as error:
        raise V03APostrunError(
            f"matrix authority no longer validates: {authority_path}"
        ) from error
    if validated.get("episodes") != MATRIX_EPISODES:
        raise V03APostrunError("validated authority is not the 1,500EP screen")
    if not _same_float(validated.get("learning_rate"), expected_learning_rate):
        raise V03APostrunError("validated authority learning rate mismatch")
    normalized_authority = dict(validated)
    normalized_authority.pop("learning_rate", None)
    normalized_authority_sha = _canonical_sha256(normalized_authority)

    runs = matrix.get("runs")
    verifications = matrix.get("verifications")
    if (
        not isinstance(runs, Mapping)
        or len(runs) != len(ALLOWED_ARMS)
        or set(runs) != set(ALLOWED_ARMS)
    ):
        raise V03APostrunError("matrix runs must contain the exact five arms")
    if (
        not isinstance(verifications, Mapping)
        or len(verifications) != len(ALLOWED_ARMS)
        or set(verifications) != set(ALLOWED_ARMS)
    ):
        raise V03APostrunError(
            "matrix verifications must contain the exact five arms"
        )

    checkpoints: dict[str, Path] = {}
    mechanism_hashes: set[str] = set()
    arm_receipts: list[dict[str, Any]] = []
    for arm in ALLOWED_ARMS:
        run = runs.get(arm)
        verification = verifications.get(arm)
        if not isinstance(run, Mapping) or not isinstance(verification, Mapping):
            raise V03APostrunError(f"{arm} run/verification receipt is missing")
        if (
            run.get("arm") != arm
            or run.get("status") != "process_complete"
            or run.get("exit_code") != 0
        ):
            raise V03APostrunError(f"{arm} process did not close successfully")
        log = _resolved_recorded_path(run.get("log"))
        if log is None:
            raise V03APostrunError(f"{arm} log path is malformed")
        log_sha = _require_file_receipt(
            path=log,
            recorded_path=run.get("log"),
            recorded_sha256=run.get("log_sha256"),
            label=f"{arm} log",
        )
        if (
            verification.get("arm") != arm
            or verification.get("status") != "PASS"
            or verification.get("failures") != []
            or verification.get("episodes_completed") != MATRIX_EPISODES
            or verification.get("c2_contract_errors") != 0
        ):
            raise V03APostrunError(f"{arm} training verification drifted or failed")
        status_path = (root / "arms" / arm / "status.json").resolve()
        status_sha = _require_file_receipt(
            path=status_path,
            recorded_path=verification.get("status_path"),
            recorded_sha256=verification.get("status_sha256"),
            label=f"{arm} status",
        )
        status = _read_object(status_path, label=f"{arm} status")
        exact_status = {
            "schema": arm_runner.STATUS_SCHEMA,
            "status": "complete",
            "arm": arm,
            "label": ARM_LABELS[arm],
            "episodes_planned": MATRIX_EPISODES,
            "users": int(validated["users"]),
            "seeds": validated["seeds"],
            "formal_training_authorized": False,
            "claim_ceiling": CLAIM_CEILING,
        }
        for field, expected in exact_status.items():
            if status.get(field) != expected:
                raise V03APostrunError(f"{arm} status {field} mismatch")
        if _resolved_recorded_path(status.get("authority_path")) != authority_path:
            raise V03APostrunError(f"{arm} authority path mismatch")
        status_authority = status.get("authority")
        if not isinstance(status_authority, Mapping) or _canonical_sha256(
            status_authority
        ) != _canonical_sha256(validated):
            raise V03APostrunError(f"{arm} validated authority identity mismatch")
        loop_config = status.get("loop_config")
        if not isinstance(loop_config, Mapping):
            raise V03APostrunError(f"{arm} loop config is missing")
        loop_exact = {
            "arm": arm,
            "episodes": MATRIX_EPISODES,
            "users": int(validated["users"]),
            "train_seed": int(validated["seeds"]["training"]),
            "env_seed": int(validated["seeds"]["environment"]),
            "mobility_seed": int(validated["seeds"]["mobility"]),
            "checkpoint_every": CHECKPOINT_EVERY_EPISODES,
        }
        for field, expected in loop_exact.items():
            if loop_config.get(field) != expected:
                raise V03APostrunError(f"{arm} loop config {field} mismatch")
        trainer_config = status.get("trainer_config")
        if not isinstance(trainer_config, Mapping) or not _same_float(
            trainer_config.get("learning_rate"), expected_learning_rate
        ):
            raise V03APostrunError(f"{arm} trainer config learning rate mismatch")
        result = status.get("result")
        if not isinstance(result, Mapping):
            raise V03APostrunError(f"{arm} result is missing")
        result_config = result.get("trainer_config")
        if not isinstance(result_config, Mapping) or _canonical_sha256(
            result_config
        ) != _canonical_sha256(trainer_config):
            raise V03APostrunError(f"{arm} result trainer config mismatch")
        completed = result.get("episodes_completed", result.get("episodes"))
        if completed != MATRIX_EPISODES:
            raise V03APostrunError(f"{arm} result episode boundary mismatch")
        start_episode = result.get("start_episode", 0)
        if (
            type(start_episode) is not int
            or start_episode < 0
            or start_episode >= MATRIX_EPISODES
        ):
            raise V03APostrunError(f"{arm} start episode is invalid")
        segment_episodes = MATRIX_EPISODES - start_episode
        run_mode = status.get("run_mode")
        resume_source_receipt: dict[str, Any] | None = None
        if arm == "B000":
            if start_episode != 0 or run_mode != "fresh_intermediate_trend":
                raise V03APostrunError("B000 must remain a fresh complete baseline")
            artifact_history_scope = "fresh_complete"
            checkpoint_trajectory_eligible = True
        elif start_episode == 0:
            if (
                run_mode != "fresh_intermediate_trend"
                or result.get("artifact_scope") != "complete_run"
                or result.get("resume_source") is not None
            ):
                raise V03APostrunError(f"{arm} fresh-run artifact scope is inconsistent")
            artifact_history_scope = "fresh_complete"
            checkpoint_trajectory_eligible = True
        else:
            if (
                run_mode != "resume_intermediate_trend"
                or result.get("artifact_scope") != "resume_segment_only"
            ):
                raise V03APostrunError(f"{arm} resume-run artifact scope is inconsistent")
            resume_source_receipt = _validate_resume_source(
                result,
                start_episode=start_episode,
                loop_config=loop_config,
                trainer_config=trainer_config,
                label=arm,
            )
            artifact_history_scope = "resume_segment_only"
            checkpoint_trajectory_eligible = False
        if (
            status.get("episodes_executed") != segment_episodes
            or result.get("episodes_executed", segment_episodes) != segment_episodes
            or verification.get("start_episode") != start_episode
        ):
            raise V03APostrunError(f"{arm} segment episode accounting mismatch")
        expected_schedule = tuple(
            episode
            for episode in range(start_episode + 1, MATRIX_EPISODES + 1)
            if episode % CHECKPOINT_EVERY_EPISODES == 0
        )
        expected_periodic = len(expected_schedule)
        if verification.get("periodic_checkpoint_count") != expected_periodic:
            raise V03APostrunError(f"{arm} segment checkpoint count mismatch")
        observed_active = tuple(result.get("active_sources", ()))
        if observed_active != EXPECTED_ACTIVE_SOURCES[arm]:
            raise V03APostrunError(f"{arm} active-source identity mismatch")

        periodic_rows = result.get("periodic_checkpoints")
        if not isinstance(periodic_rows, list) or len(periodic_rows) != expected_periodic:
            raise V03APostrunError(f"{arm} periodic checkpoint grid is incomplete")
        periodic_receipts: list[dict[str, Any]] = []
        observed_schedule: list[int] = []
        for row in periodic_rows:
            if not isinstance(row, Mapping):
                raise V03APostrunError(f"{arm} periodic checkpoint row is malformed")
            episode = row.get("episodes_completed")
            if type(episode) is not int:
                raise V03APostrunError(f"{arm} periodic episode is malformed")
            observed_schedule.append(episode)
            periodic_path = (
                root
                / "arms"
                / arm
                / "checkpoints"
                / f"ep-{episode:06d}-main.pt"
            ).resolve()
            periodic_sha = _require_file_receipt(
                path=periodic_path,
                recorded_path=row.get("path"),
                recorded_sha256=row.get("sha256"),
                label=f"{arm} periodic checkpoint {episode}",
            )
            if (
                row.get("episode_index") != episode - 1
                or row.get("checkpoint_kind") != "periodic-main-policy-trend"
                or row.get("load_round_trip") != "PASS"
            ):
                raise V03APostrunError(f"{arm} periodic checkpoint {episode} receipt drifted")
            try:
                periodic_payload = read_checkpoint(periodic_path, map_location="cpu")
            except Exception as error:
                raise V03APostrunError(
                    f"{arm} periodic checkpoint {episode} is not loadable"
                ) from error
            identity = _validate_checkpoint_payload(
                periodic_payload,
                validated=validated,
                trainer_config=trainer_config,
                episode_index=episode - 1,
                checkpoint_kind="periodic-main-policy-trend",
                label=f"{arm} periodic checkpoint {episode}",
            )
            periodic_receipts.append(
                {
                    "episodes_completed": episode,
                    "path": str(periodic_path),
                    "sha256": periodic_sha,
                    **identity,
                }
            )
        if tuple(observed_schedule) != expected_schedule:
            raise V03APostrunError(f"{arm} periodic checkpoint sequence is incomplete")
        checkpoint_dir = (root / "arms" / arm / "checkpoints").resolve()
        observed_checkpoint_files = {
            path.resolve() for path in checkpoint_dir.glob("ep-*-main.pt") if path.is_file()
        }
        expected_checkpoint_files = {
            Path(row["path"]).resolve() for row in periodic_receipts
        }
        if observed_checkpoint_files != expected_checkpoint_files:
            raise V03APostrunError(
                f"{arm} periodic checkpoint directory contains an unexpected history"
            )

        checkpoint = (root / "arms" / arm / "final-checkpoint.pt").resolve()
        checkpoint_sha = _require_file_receipt(
            path=checkpoint,
            recorded_path=verification.get("checkpoint"),
            recorded_sha256=verification.get("checkpoint_sha256"),
            label=f"{arm} final checkpoint",
        )
        if (
            _resolved_recorded_path(result.get("checkpoint")) != checkpoint
            or result.get("checkpoint_sha256") != checkpoint_sha
        ):
            raise V03APostrunError(f"{arm} result final-checkpoint receipt mismatch")
        try:
            final_payload = read_checkpoint(checkpoint, map_location="cpu")
        except Exception as error:
            raise V03APostrunError(f"{arm} final checkpoint is not loadable") from error
        final_identity = _validate_checkpoint_payload(
            final_payload,
            validated=validated,
            trainer_config=trainer_config,
            episode_index=MATRIX_EPISODES - 1,
            checkpoint_kind="final-episode-policy",
            label=f"{arm} final checkpoint",
        )
        if (
            periodic_receipts[-1]["online_policy_sha256"]
            != final_identity["online_policy_sha256"]
        ):
            raise V03APostrunError(
                f"{arm} EP1500 periodic and final evaluation policies differ"
            )

        telemetry = result.get("telemetry")
        telemetry_receipt = _validate_telemetry(
            telemetry,
            episodes=segment_episodes,
            users=int(validated["users"]),
            label=arm,
        )
        telemetry_path = (root / "arms" / arm / "run-telemetry.json").resolve()
        telemetry_sha = _require_file_receipt(
            path=telemetry_path,
            recorded_path=result.get("telemetry_path"),
            recorded_sha256=result.get("telemetry_sha256"),
            label=f"{arm} telemetry",
        )
        telemetry_file = _read_object(telemetry_path, label=f"{arm} telemetry file")
        if _canonical_sha256(telemetry_file) != _canonical_sha256(telemetry):
            raise V03APostrunError(f"{arm} telemetry file/result mismatch")

        source_dose: dict[str, Any] = {
            "active_sources": list(EXPECTED_ACTIVE_SOURCES[arm]),
            "consumed_bundle_count": result.get("consumed_bundle_count", 0),
            "joint_transaction_count": result.get("joint_transaction_count", 0),
            "main_update_receipt_rows": 0,
            "carrier_source_offer_counts": {"C1": 0, "C3": 0},
            "formal_c2_owned_main_updates": 0,
        }
        if arm != "B000":
            for field in ("consumed_bundle_count", "joint_transaction_count"):
                value = result.get(field)
                if type(value) is not int or value < 0:
                    raise V03APostrunError(f"{arm} {field} is invalid")
            update_path = (root / "arms" / arm / "main-update-receipts.json").resolve()
            try:
                update_rows = json.loads(update_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise V03APostrunError(f"{arm} Main-update receipts are unreadable") from error
            if not isinstance(update_rows, list) or len(update_rows) != segment_episodes * 10:
                raise V03APostrunError(f"{arm} Main-update receipt grid is incomplete")
            offers = {"C1": 0, "C3": 0}
            formal_c2 = 0
            for index, row in enumerate(update_rows):
                if not isinstance(row, Mapping) or row.get("main_update_calls") != 1:
                    raise V03APostrunError(f"{arm} Main-update row {index} is malformed")
                if (
                    row.get("episode") != start_episode + index // 10
                    or row.get("step") != index % 10
                ):
                    raise V03APostrunError(f"{arm} Main-update row {index} clock mismatch")
                carrier = row.get("main_carrier")
                if isinstance(carrier, Mapping):
                    active_sources = carrier.get("active_sources", [])
                    if isinstance(active_sources, (list, tuple)):
                        if not set(active_sources).issubset(EXPECTED_ACTIVE_SOURCES[arm]):
                            raise V03APostrunError(
                                f"{arm} Main-update row {index} has an unexpected source"
                            )
                        for source in offers:
                            offers[source] += int(source in active_sources)
                formal_c2 += int(row.get("formal_c2_owned_main_update") is True)
            if formal_c2 != telemetry_receipt["c2_joint_commits"]:
                raise V03APostrunError(
                    f"{arm} C2 joint-commit dose disagrees with Main-update receipts"
                )
            source_dose.update(
                {
                    "main_update_receipt_rows": len(update_rows),
                    "main_update_receipts_path": str(update_path),
                    "main_update_receipts_sha256": sha256_file(update_path),
                    "carrier_source_offer_counts": offers,
                    "formal_c2_owned_main_updates": formal_c2,
                }
            )

        mechanism_sha = verification.get("mechanism_environment_source_sha256")
        result_mechanism = result.get("mechanism_authority")
        result_mechanism_sha = (
            result_mechanism.get("environment_source_sha256")
            if isinstance(result_mechanism, Mapping)
            else None
        )
        if not isinstance(mechanism_sha, str) or len(mechanism_sha) != 64:
            raise V03APostrunError(f"{arm} mechanism source authority is missing")
        if result_mechanism_sha != mechanism_sha:
            raise V03APostrunError(f"{arm} mechanism source receipt mismatch")
        mechanism_hashes.add(mechanism_sha)
        checkpoints[arm] = checkpoint
        arm_receipts.append(
            {
                "arm": arm,
                "log_sha256": log_sha,
                "status_sha256": status_sha,
                "checkpoint_sha256": checkpoint_sha,
                "final_checkpoint_identity": final_identity,
                "periodic_checkpoint_count": expected_periodic,
                "periodic_checkpoints": periodic_receipts,
                "start_episode": start_episode,
                "episodes_executed": segment_episodes,
                "artifact_history_scope": artifact_history_scope,
                "checkpoint_trajectory_eligible": checkpoint_trajectory_eligible,
                "resume_source": resume_source_receipt,
                "c2_contract_errors": 0,
                "training_telemetry_path": str(telemetry_path),
                "training_telemetry_sha256": telemetry_sha,
                "training_telemetry": telemetry_receipt,
                "source_dose": source_dose,
                "mechanism_environment_source_sha256": mechanism_sha,
            }
        )

    consistency = matrix.get("mechanism_consistency")
    if (
        len(mechanism_hashes) != 1
        or not isinstance(consistency, Mapping)
        or consistency.get("status") != "PASS"
        or consistency.get("observed_environment_source_sha256")
        != sorted(mechanism_hashes)
    ):
        raise V03APostrunError("matrix mechanism-source consistency failed")

    sweep = matrix.get("main_only_sweep")
    if not isinstance(sweep, Mapping) or sweep.get("exit_code") != 0:
        raise V03APostrunError("matrix Main-only sweep did not exit successfully")
    sweep_log = _resolved_recorded_path(sweep.get("log"))
    if sweep_log is None:
        raise V03APostrunError("matrix sweep log path is malformed")
    sweep_log_sha = _require_file_receipt(
        path=sweep_log,
        recorded_path=sweep.get("log"),
        recorded_sha256=sweep.get("log_sha256"),
        label="Main-only sweep log",
    )
    summary_path = (root / "evaluation" / "sweep-summary.json").resolve()
    summary_sha = _require_file_receipt(
        path=summary_path,
        recorded_path=sweep.get("summary"),
        recorded_sha256=sweep.get("summary_sha256"),
        label="Main-only sweep summary",
    )

    prereg_path = _repo_file(validated.get("canonical_prereg"), field="canonical_prereg")
    prereg_sha = sha256_file(prereg_path)
    sweep_verification = verify_pilot100_sweep(
        output_dir=root / "evaluation",
        training_seed=int(validated["seeds"]["training"]),
        evaluation_users=validated["evaluation_users"],
        evaluation_seeds=validated["evaluation_seeds"],
        checkpoints=checkpoints,
        expected_tle_hash=str(validated["tle_file_set_sha256"]),
        expected_tle_count=int(validated["tle_file_count"]),
        expected_prereg_sha256=prereg_sha,
        expected_episode_index=MATRIX_EPISODES - 1,
    )
    if sweep_verification.get("status") != "PASS":
        failures = sweep_verification.get("failures")
        detail = "; ".join(str(value) for value in failures) if failures else "unknown"
        raise V03APostrunError(f"Main-only sweep verification failed: {detail}")
    if sweep_verification.get("zero_power_longer_run_gate") != "PASS":
        raise V03APostrunError(
            "Main-only sweep contains zero-power intervals; LR selection is blocked"
        )
    sweep_csv_verification = _validate_sweep_csv_exports(root / "evaluation")

    return {
        "status": "PASS",
        "matrix_root": str(root),
        "matrix_status": str(matrix_path),
        "matrix_status_sha256": sha256_file(matrix_path),
        "authority": str(authority_path),
        "authority_sha256": authority_sha,
        "normalized_authority_excluding_learning_rate_sha256": normalized_authority_sha,
        "learning_rate": float(expected_learning_rate),
        "episodes": MATRIX_EPISODES,
        "arms": arm_receipts,
        "mechanism_environment_source_sha256": next(iter(mechanism_hashes)),
        "sweep_log_sha256": sweep_log_sha,
        "sweep_summary": str(summary_path),
        "sweep_summary_sha256": summary_sha,
        "sweep_verification": sweep_verification,
        "sweep_csv_verification": sweep_csv_verification,
    }


def _write_u100_csv(path: Path, selection: Mapping[str, Any]) -> None:
    assessments = selection.get("assessments")
    if not isinstance(assessments, Mapping):
        raise V03APostrunError("LR selection assessments are missing")
    rows: list[dict[str, Any]] = []
    for learning_rate in EXPECTED_LEARNING_RATES:
        assessment = assessments.get(str(learning_rate))
        if not isinstance(assessment, Mapping):
            raise V03APostrunError("LR selection assessment grid is incomplete")
        comparisons = assessment.get("comparisons")
        if not isinstance(comparisons, Mapping):
            raise V03APostrunError("LR selection comparison block is missing")
        rows.append(
            {
                "learning_rate": learning_rate,
                "f111_ee_bits_per_j_at_u100": assessment.get("endpoint_ee_bits_per_j"),
                "full_vs_baseline_percent": comparisons.get("full_vs_baseline_percent"),
                "c1_marginal_percent": comparisons.get("c1_marginal_percent"),
                "c2_marginal_percent": comparisons.get("c2_marginal_percent"),
                "c3_marginal_percent": comparisons.get("c3_marginal_percent"),
                "eligible": assessment.get("eligible"),
            }
        )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _ablation_contrast_rows(
    validations: Mapping[float, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Convert verified five-line sweeps into direct Catfish EE marginals."""

    rows: list[dict[str, Any]] = []
    for learning_rate in EXPECTED_LEARNING_RATES:
        summary_path = Path(str(validations[learning_rate]["sweep_summary"]))
        summary = _read_object(summary_path, label="verified sweep summary")
        raw_rows = summary.get("summary")
        if not isinstance(raw_rows, list):
            raise V03APostrunError("verified sweep summary rows are missing")
        by_cell: dict[tuple[str, int], Mapping[str, Any]] = {}
        for row in raw_rows:
            if not isinstance(row, Mapping):
                raise V03APostrunError("verified sweep summary row is malformed")
            arm = row.get("arm")
            users = row.get("users")
            if not isinstance(arm, str) or type(users) is not int:
                raise V03APostrunError("verified sweep cell identity is malformed")
            by_cell[(arm, users)] = row
        for users in (60, 80, 100, 120, 140):
            cells = {
                arm: by_cell.get((label, users)) for arm, label in ARM_LABELS.items()
            }
            if any(value is None for value in cells.values()):
                raise V03APostrunError(
                    f"verified sweep lacks one or more arms at U={users}"
                )
            ee = {
                arm: float(cells[arm]["mean_ee_bits_per_j"])  # type: ignore[index]
                for arm in ALLOWED_ARMS
            }
            if any(not math.isfinite(value) or value <= 0.0 for value in ee.values()):
                raise V03APostrunError(
                    f"verified sweep has invalid EE at U={users}"
                )
            served: dict[str, float] = {}
            for arm in ALLOWED_ARMS:
                seed_rows = cells[arm].get("seed_rows")  # type: ignore[union-attr]
                if (
                    not isinstance(seed_rows, list)
                    or len(seed_rows) != 1
                    or not isinstance(seed_rows[0], Mapping)
                ):
                    raise V03APostrunError(
                        f"verified sweep lacks served-fraction receipt at U={users}"
                    )
                value = seed_rows[0].get("served_fraction")
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or not 0.0 <= float(value) <= 1.0
                ):
                    raise V03APostrunError(
                        f"verified sweep has invalid served fraction at U={users}"
                    )
                served[arm] = float(value)
            deltas = {
                "full_vs_baseline_percent": 100.0 * (ee["F111"] / ee["B000"] - 1.0),
                "c1_marginal_percent": 100.0 * (ee["F111"] / ee["A011"] - 1.0),
                "c2_marginal_percent": 100.0 * (ee["F111"] / ee["A101"] - 1.0),
                "c3_marginal_percent": 100.0 * (ee["F111"] / ee["A110"] - 1.0),
            }
            rows.append(
                {
                    "learning_rate": learning_rate,
                    "users": users,
                    "baseline_ee_bits_per_j": ee["B000"],
                    "full_ee_bits_per_j": ee["F111"],
                    "without_c1_ee_bits_per_j": ee["A011"],
                    "without_c2_ee_bits_per_j": ee["A101"],
                    "without_c3_ee_bits_per_j": ee["A110"],
                    "baseline_served_fraction": served["B000"],
                    "full_served_fraction": served["F111"],
                    "without_c1_served_fraction": served["A011"],
                    "without_c2_served_fraction": served["A101"],
                    "without_c3_served_fraction": served["A110"],
                    "full_vs_baseline_served_pp": 100.0
                    * (served["F111"] - served["B000"]),
                    "c1_served_marginal_pp": 100.0
                    * (served["F111"] - served["A011"]),
                    "c2_served_marginal_pp": 100.0
                    * (served["F111"] - served["A101"]),
                    "c3_served_marginal_pp": 100.0
                    * (served["F111"] - served["A110"]),
                    **deltas,
                    "all_four_comparisons_positive": all(
                        value > 0.0 for value in deltas.values()
                    ),
                }
            )
    return rows


def _write_ablation_contrasts(
    output: Path,
    validations: Mapping[float, Mapping[str, Any]],
) -> tuple[Path, Path]:
    rows = _ablation_contrast_rows(validations)
    json_path = output / "ablation-contrasts.json"
    csv_path = output / "ablation-contrasts.csv"
    _write_json(
        json_path,
        {
            "schema": CONTRAST_SCHEMA,
            "status": "PASS",
            "definition": {
                "full_vs_baseline_percent": "100*(F111/B000-1)",
                "c1_marginal_percent": "100*(F111/A011-1)",
                "c2_marginal_percent": "100*(F111/A101-1)",
                "c3_marginal_percent": "100*(F111/A110-1)",
            },
            "rows": rows,
            "claim_ceiling": POSTRUN_CLAIM_CEILING,
        },
    )
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def build_postrun_bundle(
    *,
    lr0p001_root: Path,
    lr0p01_root: Path,
    tle_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Close the two-rate screen only after both matrices verify independently."""

    roots = {
        0.001: Path(lr0p001_root).expanduser().resolve(),
        0.01: Path(lr0p01_root).expanduser().resolve(),
    }
    validations = {
        learning_rate: validate_matrix(
            root,
            tle_root=tle_root,
            expected_learning_rate=learning_rate,
        )
        for learning_rate, root in roots.items()
    }
    mechanism_hashes = {
        row["mechanism_environment_source_sha256"] for row in validations.values()
    }
    if len(mechanism_hashes) != 1:
        raise V03APostrunError("learning-rate matrices used different mechanism sources")
    normalized_authority_hashes = {
        row["normalized_authority_excluding_learning_rate_sha256"]
        for row in validations.values()
    }
    if len(normalized_authority_hashes) != 1:
        raise V03APostrunError(
            "learning-rate matrices differ beyond the declared learning rate"
        )

    selection = lr_selector.select_learning_rate(
        Path(validations[0.001]["sweep_summary"]),
        Path(validations[0.01]["sweep_summary"]),
    )
    output = Path(output_dir).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite post-run bundle: {output}")
    output.mkdir(parents=True, exist_ok=False)

    svg_receipts: dict[str, dict[str, str]] = {}
    for learning_rate, slug in ((0.001, "lr0p001"), (0.01, "lr0p01")):
        summary_path = Path(validations[learning_rate]["sweep_summary"])
        svg_path = output / f"{slug}-ee-vs-users.svg"
        render_sweep(summary_path, svg_path)
        svg_receipts[str(learning_rate)] = {
            "path": str(svg_path),
            "sha256": sha256_file(svg_path),
        }

    selection_path = output / "lr-selection.json"
    _write_json(selection_path, selection)
    comparison_path = output / "u100-lr-comparisons.csv"
    _write_u100_csv(comparison_path, selection)
    contrast_json, contrast_csv = _write_ablation_contrasts(output, validations)
    receipt = {
        "schema": SCHEMA,
        "status": "PASS",
        "decision": selection["decision"],
        "selected_learning_rate": selection["selected_learning_rate"],
        "formal_training_authorized": False,
        "fresh_3000_launch_performed": False,
        "matrices": {str(key): value for key, value in validations.items()},
        "cross_lr_mechanism_consistency": {
            "status": "PASS",
            "environment_source_sha256": next(iter(mechanism_hashes)),
            "normalized_authority_excluding_learning_rate_sha256": next(
                iter(normalized_authority_hashes)
            ),
        },
        "lr_selection": {
            "path": str(selection_path),
            "sha256": sha256_file(selection_path),
        },
        "u100_comparisons_csv": {
            "path": str(comparison_path),
            "sha256": sha256_file(comparison_path),
        },
        "ablation_contrasts": {
            "json": str(contrast_json),
            "json_sha256": sha256_file(contrast_json),
            "csv": str(contrast_csv),
            "csv_sha256": sha256_file(contrast_csv),
        },
        "editable_sweep_svgs": svg_receipts,
        "next_action": (
            "PREPARE_FRESH_3000_AUTHORITY_BUT_DO_NOT_LAUNCH_WITHOUT_USER_NOTICE"
            if selection["decision"] == "SELECT_AND_RUN_FRESH_3000"
            else "STOP_BEFORE_3000_AND_ADJUDICATE_DESIGN"
        ),
        "claim_ceiling": POSTRUN_CLAIM_CEILING,
    }
    _write_json(output / "postrun-receipt.json", receipt)
    return receipt


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lr0p001-root", type=Path, required=True)
    parser.add_argument("--lr0p01-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        build_postrun_bundle(
            lr0p001_root=args.lr0p001_root,
            lr0p01_root=args.lr0p01_root,
            tle_root=args.tle_root,
            output_dir=args.output_dir,
        )
    except V03APostrunError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(Path(args.output_dir).expanduser().resolve() / "postrun-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
