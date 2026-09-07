#!/usr/bin/env python3
"""Analyse one or two completed intermediate Multi-Catfish MCRL matrices.

The analyser is intentionally post-run and fail-closed.  It consumes only
completed matrix receipts and their held-out Main-only sweeps; it never trains,
reruns an arm, or changes a sign to make a result look favourable.  The
primary endpoint is reconstructed as a ratio of pooled useful bits to pooled
system energy for each arm/load cell before the four preregistered percentage
contrasts are calculated.

The output is a deterministic JSON/CSV/Markdown bundle.  It reports the
1500-episode learning-rate selection rule and the 3000-episode directional
gate, but neither result is a significance claim or a 9000-episode
authorisation.  A separately produced 100EP checkpoint-trend summary may be
bound with ``--trajectory-summary``; it is validated and recorded as a
diagnostic, never substituted for the final-checkpoint sweep.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from intermediate_trend_authority import (  # noqa: E402
    ALLOWED_ARMS,
    ALLOWED_EPISODES,
    ALLOWED_LEARNING_RATES,
    CANONICAL_PREREG_SHA256,
    CANONICAL_TLE_FILE_SET_SHA256,
    CLAIM_CEILING,
    DEFAULT_C1_MANIFEST,
    TREND_ACRM_ETA,
    TREND_CHECKPOINT_EVERY_EPISODES,
    TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
    TREND_DONOR_BETA,
    TREND_EPSILON_DECAY_EPISODES,
    TREND_TARGET_UPDATE_EVERY,
    TREND_USERS,
    TREND_EVALUATION_USERS,
    TREND_EVALUATION_SEEDS,
    validate_intermediate_trend_authority,
)


SCHEMA = "multi-catfish-mcrl-intermediate-trend-analysis-v1"
MATRIX_SCHEMA = "multi-catfish-mcrl-intermediate-trend-matrix-v1"
SWEEP_SCHEMA = "multi-catfish-mcrl-short-ep-ee-users-sweep-v2"
TRAJECTORY_SCHEMA = "multi-catfish-mcrl-checkpoint-ee-trajectory-v1"
TRAJECTORY_CLAIM_CEILING = "ONE_SEED_100EP_MAIN_ONLY_EE_TRAJECTORY_NOT_CHAPTER5"
EXPECTED_ARMS = tuple(ALLOWED_ARMS)
EXPECTED_EVALUATION_USERS = tuple(TREND_EVALUATION_USERS)
EXPECTED_EVALUATION_SEEDS = tuple(TREND_EVALUATION_SEEDS)
TLE_FILE_RE = re.compile(r"^starlink_\d{8}\.tle$")
ARM_LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A011": "Full - C1",
    "A101": "Full - C2",
    "A110": "Full - C3",
}
ARM_BY_LABEL = {label: arm for arm, label in ARM_LABELS.items()}
CONTRAST_DENOMINATORS = {
    "d_full": "B000",
    "d_C1": "A011",
    "d_C2": "A101",
    "d_C3": "A110",
}
CONTRASTS = tuple(CONTRAST_DENOMINATORS)
STAGE1_SERVICE_LOSS_PP = 2.0
STAGE2_SERVICE_LOSS_PP = 0.5
LR_TIE_PP = 0.25


class IntermediateTrendAnalysisError(RuntimeError):
    """Raised when a matrix or analysis output is not safe to accept."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise IntermediateTrendAnalysisError(
            f"{label} is unreadable: {path}"
        ) from error
    if not isinstance(value, Mapping):
        raise IntermediateTrendAnalysisError(f"{label} must be a JSON object: {path}")
    return value


def _read_list(path: Path, *, label: str) -> list[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise IntermediateTrendAnalysisError(
            f"{label} is unreadable: {path}"
        ) from error
    if not isinstance(value, list):
        raise IntermediateTrendAnalysisError(f"{label} must be a JSON array: {path}")
    return value


def _path(value: Any, *, base: Path, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise IntermediateTrendAnalysisError(f"{label}: path missing")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


def _finite(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _number(value: Any, *, label: str, minimum: float | None = None) -> float:
    if not _finite(value):
        raise IntermediateTrendAnalysisError(f"{label}: finite number required")
    result = float(value)
    if minimum is not None and result < minimum:
        raise IntermediateTrendAnalysisError(f"{label}: value below {minimum}")
    return result


def _integer(value: Any, *, label: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise IntermediateTrendAnalysisError(f"{label}: integer required")
    if minimum is not None and value < minimum:
        raise IntermediateTrendAnalysisError(f"{label}: value below {minimum}")
    return int(value)


def _close(left: Any, right: float, *, rel: float = 1e-12, absolute: float = 1e-9) -> bool:
    if not _finite(left):
        return False
    return math.isclose(float(left), float(right), rel_tol=rel, abs_tol=absolute)


def _digest(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise IntermediateTrendAnalysisError(f"{label}: lowercase SHA-256 required")
    return value


def canonical_tle_file_set_hash(tle_root: Path) -> tuple[str, int]:
    """Reproduce the frozen ``filename:sha256(bytes)`` TLE-set hash."""

    root = Path(tle_root).expanduser().resolve()
    if not root.is_dir():
        raise IntermediateTrendAnalysisError(f"TLE root is not a directory: {root}")
    files = sorted(
        path
        for path in root.iterdir()
        if path.is_file() and TLE_FILE_RE.fullmatch(path.name)
    )
    if not files:
        raise IntermediateTrendAnalysisError(f"no canonical TLE files under {root}")
    rows = [f"{path.name}:{sha256_file(path)}" for path in files]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest(), len(files)


def _load_authority(path: Path, *, tle_root: Path) -> dict[str, Any]:
    """Read one authority JSON and invoke the canonical validator."""

    authority_path = Path(path).expanduser().resolve()
    request = _read_object(authority_path, label="authority manifest")
    try:
        validated = validate_intermediate_trend_authority(
            request,
            repo=REPO,
            tle_root=Path(tle_root).expanduser().resolve(),
        )
    except Exception as error:
        raise IntermediateTrendAnalysisError(
            f"authority validation failed for {authority_path}: {error}"
        ) from error
    if not isinstance(validated, Mapping) or validated.get("status") != "PASS":
        raise IntermediateTrendAnalysisError(
            f"authority validator did not return PASS: {authority_path}"
        )
    return dict(validated)


def _require_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise IntermediateTrendAnalysisError(f"{label}: object required")
    return value


def _validate_authority_binding(
    receipt: Mapping[str, Any],
    *,
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, Path]:
    authority_path = _path(
        receipt.get("authority_manifest"),
        base=receipt_path.parent,
        label="matrix authority_manifest",
    )
    if not authority_path.is_file():
        raise IntermediateTrendAnalysisError(
            f"matrix authority manifest is missing: {authority_path}"
        )
    expected_authority_sha = _digest(
        receipt.get("authority_manifest_sha256"),
        label="matrix authority_manifest_sha256",
    )
    actual_authority_sha = sha256_file(authority_path)
    if actual_authority_sha != expected_authority_sha:
        raise IntermediateTrendAnalysisError("matrix authority manifest hash mismatch")
    canonical = _require_mapping(
        receipt.get("canonical_inputs"), label="matrix canonical_inputs"
    )
    prereg_path = _path(
        canonical.get("prereg"),
        base=receipt_path.parent,
        label="matrix canonical_inputs.prereg",
    )
    c1_path = _path(
        canonical.get("c1_exp_corpus_manifest"),
        base=receipt_path.parent,
        label="matrix canonical_inputs.c1_exp_corpus_manifest",
    )
    tle_path = _path(
        canonical.get("tle_root"),
        base=receipt_path.parent,
        label="matrix canonical_inputs.tle_root",
    )
    if not prereg_path.is_file() or not c1_path.is_file():
        raise IntermediateTrendAnalysisError(
            "matrix canonical preregistration or C1 corpus is missing"
        )
    if sha256_file(prereg_path) != CANONICAL_PREREG_SHA256:
        raise IntermediateTrendAnalysisError("matrix canonical preregistration hash mismatch")
    if _digest(canonical.get("prereg_sha256"), label="matrix prereg_sha256") != CANONICAL_PREREG_SHA256:
        raise IntermediateTrendAnalysisError("matrix declared preregistration hash mismatch")
    c1_sha = _digest(
        canonical.get("c1_exp_corpus_manifest_sha256"),
        label="matrix c1_exp_corpus_manifest_sha256",
    )
    if sha256_file(c1_path) != c1_sha:
        raise IntermediateTrendAnalysisError("matrix C1 corpus manifest hash mismatch")
    if c1_path != DEFAULT_C1_MANIFEST.resolve():
        raise IntermediateTrendAnalysisError("matrix C1 corpus manifest is not canonical")
    tle_sha = _digest(
        canonical.get("tle_file_set_sha256"),
        label="matrix tle_file_set_sha256",
    )
    if tle_sha != CANONICAL_TLE_FILE_SET_SHA256:
        raise IntermediateTrendAnalysisError("matrix TLE hash is not canonical")
    actual_tle_sha, actual_tle_count = canonical_tle_file_set_hash(tle_path)
    if actual_tle_sha != tle_sha:
        raise IntermediateTrendAnalysisError("matrix TLE root hash mismatch")
    if type(canonical.get("tle_file_count")) is not int or canonical.get("tle_file_count") != actual_tle_count:
        raise IntermediateTrendAnalysisError("matrix TLE file count mismatch")

    validated = _load_authority(authority_path, tle_root=tle_path)

    authority = _require_mapping(
        validated.get("authority"), label="validated authority"
    )
    if authority.get("canonical_prereg") != str(prereg_path):
        raise IntermediateTrendAnalysisError("validated authority preregistration drifted")
    if authority.get("c1_exp_corpus_manifest") != str(c1_path):
        raise IntermediateTrendAnalysisError("validated authority C1 manifest drifted")
    if authority.get("tle_file_set_sha256") != tle_sha:
        raise IntermediateTrendAnalysisError("validated authority TLE hash drifted")
    return validated, authority_path, prereg_path, c1_path


def _validate_matrix_header(
    receipt: Mapping[str, Any],
    *,
    receipt_path: Path,
) -> tuple[dict[str, Any], Path, Path, Path, Path]:
    if receipt.get("schema") != MATRIX_SCHEMA:
        raise IntermediateTrendAnalysisError("matrix receipt schema mismatch")
    if receipt.get("status") != "complete":
        raise IntermediateTrendAnalysisError("matrix receipt is not complete")
    if receipt.get("formal_training_authorized") is not False:
        raise IntermediateTrendAnalysisError("matrix formal_training_authorized must be false")
    if type(receipt.get("max_parallel")) is not int or receipt["max_parallel"] not in (1, 2):
        raise IntermediateTrendAnalysisError("matrix max_parallel must be 1 or 2")
    if receipt.get("no_retry") is not True:
        raise IntermediateTrendAnalysisError("matrix no_retry must be true")
    if receipt.get("claim_ceiling") != CLAIM_CEILING:
        raise IntermediateTrendAnalysisError("matrix claim ceiling mismatch")
    if list(receipt.get("arms", ())) != list(EXPECTED_ARMS):
        raise IntermediateTrendAnalysisError("matrix must contain the exact five arms")
    episodes = _integer(receipt.get("episodes"), label="matrix episodes")
    if episodes not in ALLOWED_EPISODES:
        raise IntermediateTrendAnalysisError("matrix episodes are not 1500 or 3000")
    learning_rate = _number(receipt.get("learning_rate"), label="matrix learning_rate")
    if not any(math.isclose(learning_rate, value, abs_tol=1e-15, rel_tol=0.0) for value in ALLOWED_LEARNING_RATES):
        raise IntermediateTrendAnalysisError("matrix learning_rate is not 0.001 or 0.01")

    training = _require_mapping(receipt.get("training"), label="matrix training")
    if training.get("users") != TREND_USERS:
        raise IntermediateTrendAnalysisError("matrix training users mismatch")
    for field in ("training_seed", "environment_seed", "mobility_seed"):
        _integer(training.get(field), label=f"matrix training.{field}")
    if training.get("epsilon_decay_episodes") != TREND_EPSILON_DECAY_EPISODES:
        raise IntermediateTrendAnalysisError("matrix epsilon schedule mismatch")
    if training.get("target_update_every") != TREND_TARGET_UPDATE_EVERY:
        raise IntermediateTrendAnalysisError("matrix target-sync schedule mismatch")
    if training.get("checkpoint_every_episodes") != TREND_CHECKPOINT_EVERY_EPISODES:
        raise IntermediateTrendAnalysisError("matrix checkpoint cadence mismatch")
    if (
        training.get("specialist_bundle_replay_capacity")
        != TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY
    ):
        raise IntermediateTrendAnalysisError("matrix bundle replay capacity mismatch")
    if not _close(training.get("acrm_eta"), TREND_ACRM_ETA):
        raise IntermediateTrendAnalysisError("matrix ACRM eta mismatch")
    if not _close(training.get("donor_beta"), TREND_DONOR_BETA):
        raise IntermediateTrendAnalysisError("matrix donor beta mismatch")

    evaluation = _require_mapping(receipt.get("evaluation"), label="matrix evaluation")
    if tuple(evaluation.get("users", ())) != EXPECTED_EVALUATION_USERS:
        raise IntermediateTrendAnalysisError("matrix evaluation users mismatch")
    if tuple(evaluation.get("seeds", ())) != EXPECTED_EVALUATION_SEEDS:
        raise IntermediateTrendAnalysisError("matrix evaluation seeds mismatch")
    if evaluation.get("policy") != "Main-only masked-greedy MODQN":
        raise IntermediateTrendAnalysisError("matrix evaluation policy mismatch")
    if evaluation.get("partition") != "TEST":
        raise IntermediateTrendAnalysisError("matrix evaluation partition mismatch")
    if evaluation.get("ee_aggregation") != "ratio-of-sums per training seed, then equal-weight mean":
        raise IntermediateTrendAnalysisError("matrix EE aggregation mismatch")

    validated, authority_path, prereg_path, c1_path = _validate_authority_binding(
        receipt, receipt_path=receipt_path
    )
    if validated.get("episodes") != episodes:
        raise IntermediateTrendAnalysisError("authority episodes disagree with matrix")
    if not math.isclose(float(validated.get("learning_rate")), learning_rate, abs_tol=1e-15, rel_tol=0.0):
        raise IntermediateTrendAnalysisError("authority learning rate disagrees with matrix")
    authority_seeds = _require_mapping(validated.get("seeds"), label="validated authority seeds")
    expected_seeds = {
        "training_seed": authority_seeds.get("training"),
        "environment_seed": authority_seeds.get("environment"),
        "mobility_seed": authority_seeds.get("mobility"),
    }
    for field, expected in expected_seeds.items():
        if training.get(field) != expected:
            raise IntermediateTrendAnalysisError(f"authority {field} disagrees with matrix")
    authority_config = _require_mapping(validated.get("config"), label="validated authority config")
    for field in (
        "users",
        "epsilon_decay_episodes",
        "target_update_every",
        "checkpoint_every_episodes",
        "specialist_bundle_replay_capacity",
    ):
        if authority_config.get(field) != training.get(field):
            raise IntermediateTrendAnalysisError(f"authority {field} disagrees with matrix")
    if not _close(authority_config.get("acrm_eta"), training.get("acrm_eta"), absolute=1e-15):
        raise IntermediateTrendAnalysisError("authority ACRM eta disagrees with matrix")
    if not _close(authority_config.get("donor_beta"), training.get("donor_beta"), absolute=1e-15):
        raise IntermediateTrendAnalysisError("authority donor beta disagrees with matrix")
    return (
        {
            "episodes": episodes,
            "learning_rate": learning_rate,
            "training": dict(training),
            "evaluation": dict(evaluation),
            "claim_ceiling": receipt["claim_ceiling"],
            "authority_validation": validated,
        },
        authority_path,
        prereg_path,
        c1_path,
        _path(
            _require_mapping(receipt.get("canonical_inputs"), label="matrix canonical_inputs").get("tle_root"),
            base=receipt_path.parent,
            label="matrix canonical_inputs.tle_root",
        ),
    )


def _command_values(command: Sequence[Any], *, arm: str) -> dict[str, str]:
    """Parse the runner command while rejecting duplicate/missing values."""

    values: dict[str, str] = {}
    for index, token in enumerate(command):
        if not isinstance(token, str) or not token.startswith("--"):
            continue
        if token in values:
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} command contains duplicate {token}"
            )
        if index + 1 >= len(command) or not isinstance(command[index + 1], str):
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} command value is missing for {token}"
            )
        if command[index + 1].startswith("--"):
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} command value is missing for {token}"
            )
        values[token] = command[index + 1]
    return values


def _verify_arm_runs(
    receipt: Mapping[str, Any],
    *,
    receipt_path: Path,
    header: Mapping[str, Any],
    authority_path: Path,
    prereg_path: Path,
    c1_path: Path,
    tle_path: Path,
    tle_file_count: int,
) -> dict[str, dict[str, Any]]:
    rows = receipt.get("arm_runs")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_ARMS):
        raise IntermediateTrendAnalysisError("matrix arm_runs must contain exactly five rows")
    by_arm: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        row = _require_mapping(raw, label=f"matrix arm_runs[{index}]")
        arm = row.get("arm")
        if arm not in EXPECTED_ARMS or arm in by_arm:
            raise IntermediateTrendAnalysisError("matrix arm_runs has duplicate or unknown arm")
        if row.get("status") != "PASS" or row.get("attempt") != 1:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} is not a single successful attempt")
        command = row.get("command")
        if not isinstance(command, list) or command.count("--arm") != 1:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} command is malformed")
        arm_index = command.index("--arm")
        if arm_index + 1 >= len(command) or command[arm_index + 1] != arm:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} command identity mismatch")
        command_values = _command_values(command, arm=arm)
        expected_command_values = {
            "--output-dir": str((receipt_path.parent / arm).resolve()),
            "--episodes": str(header["episodes"]),
            "--users": str(TREND_USERS),
            "--train-seed": str(header["training"]["training_seed"]),
            "--env-seed": str(header["training"]["environment_seed"]),
            "--mobility-seed": str(header["training"]["mobility_seed"]),
            "--epsilon-decay-episodes": str(TREND_EPSILON_DECAY_EPISODES),
            "--target-update-every": str(TREND_TARGET_UPDATE_EVERY),
            "--checkpoint-every": str(TREND_CHECKPOINT_EVERY_EPISODES),
            "--learning-rate": str(header["learning_rate"]),
            "--acrm-eta": str(TREND_ACRM_ETA),
            "--intermediate-trend-authority": str(authority_path),
            "--prereg": str(prereg_path),
            "--tle-root": str(tle_path),
        }
        for flag, expected in expected_command_values.items():
            if command_values.get(flag) != expected:
                raise IntermediateTrendAnalysisError(
                    f"matrix arm {arm} command {flag} mismatch"
                )
        if arm == "B000":
            if "--c1-exp-corpus-manifest" in command_values:
                raise IntermediateTrendAnalysisError(
                    "matrix baseline command must not consume the C1 corpus"
                )
        elif command_values.get("--c1-exp-corpus-manifest") != str(c1_path):
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} command C1 corpus mismatch"
            )
        for field in ("started_utc", "ended_utc", "elapsed_s", "exit_code", "log", "log_sha256"):
            if field not in row:
                raise IntermediateTrendAnalysisError(f"matrix arm {arm} missing {field}")
        try:
            started = dt.datetime.fromisoformat(str(row["started_utc"]))
            ended = dt.datetime.fromisoformat(str(row["ended_utc"]))
        except (TypeError, ValueError) as error:
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} timestamps are malformed"
            ) from error
        if ended < started:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} ended before it started")
        elapsed = _number(row.get("elapsed_s"), label=f"matrix arm {arm} elapsed_s", minimum=0.0)
        if not _close(elapsed, (ended - started).total_seconds(), absolute=1e-3):
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} elapsed time mismatch")
        if type(row.get("exit_code")) is not int or row["exit_code"] != 0:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} exit code mismatch")
        log_path = _path(row.get("log"), base=receipt_path.parent, label=f"matrix arm {arm} log")
        log_sha = _digest(row.get("log_sha256"), label=f"matrix arm {arm} log_sha256")
        if not log_path.is_file() or sha256_file(log_path) != log_sha:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} log hash mismatch")
        verification = _require_mapping(row.get("verification"), label=f"matrix arm {arm} verification")
        if verification.get("status") != "PASS":
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} checkpoint verification is not PASS")
        status_path = _path(verification.get("status_path"), base=receipt_path.parent, label=f"matrix arm {arm} status")
        checkpoint_path = _path(verification.get("checkpoint_path"), base=receipt_path.parent, label=f"matrix arm {arm} checkpoint")
        status_sha = _digest(verification.get("status_sha256"), label=f"matrix arm {arm} status_sha256")
        checkpoint_sha = _digest(verification.get("checkpoint_sha256"), label=f"matrix arm {arm} checkpoint_sha256")
        if not status_path.is_file() or sha256_file(status_path) != status_sha:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status hash mismatch")
        if not checkpoint_path.is_file() or sha256_file(checkpoint_path) != checkpoint_sha:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} checkpoint hash mismatch")
        status = _read_object(status_path, label=f"matrix arm {arm} status")
        if (
            status.get("status") != "complete"
            or status.get("arm") != arm
            or status.get("label") != ARM_LABELS[arm]
        ):
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status identity mismatch")
        if status.get("episodes") != header["episodes"] or status.get("users") != TREND_USERS:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status schedule mismatch")
        if status.get("seeds") != {
            "training": header["training"]["training_seed"],
            "environment": header["training"]["environment_seed"],
            "mobility": header["training"]["mobility_seed"],
        }:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status seeds mismatch")
        status_config = _require_mapping(
            status.get("config"), label=f"matrix arm {arm} status config"
        )
        expected_config = {
            "episodes": header["episodes"],
            "learning_rate": header["learning_rate"],
            "epsilon_decay_episodes": TREND_EPSILON_DECAY_EPISODES,
            "target_update_every_episodes": TREND_TARGET_UPDATE_EVERY,
        }
        for field, expected in expected_config.items():
            observed = status_config.get(field)
            if isinstance(expected, float):
                matches = _close(observed, expected, absolute=1e-15)
            else:
                matches = observed == expected and type(observed) is type(expected)
            if not matches:
                raise IntermediateTrendAnalysisError(
                    f"matrix arm {arm} status config {field} mismatch"
                )
        checkpointing = _require_mapping(
            status.get("checkpointing"), label=f"matrix arm {arm} checkpointing"
        )
        if checkpointing.get("every_episodes") != TREND_CHECKPOINT_EVERY_EPISODES:
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} checkpoint cadence mismatch"
            )
        if (
            checkpointing.get("specialist_bundle_replay_capacity")
            != TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY
        ):
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} bundle replay capacity mismatch"
            )
        status_authority = _require_mapping(status.get("authority"), label=f"matrix arm {arm} status authority")
        if status_authority.get("prereg_path") != str(prereg_path):
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status preregistration mismatch")
        if status_authority.get("prereg_sha256") != CANONICAL_PREREG_SHA256:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status preregistration hash mismatch")
        if status_authority.get("tle_root_path") != str(tle_path):
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status TLE root mismatch")
        if status_authority.get("tle_file_set_sha256") != CANONICAL_TLE_FILE_SET_SHA256:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status TLE hash mismatch")
        if (
            type(status_authority.get("tle_file_count")) is not int
            or status_authority.get("tle_file_count") != tle_file_count
        ):
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} status TLE count mismatch")
        gate = _require_mapping(status.get("gate_manifest"), label=f"matrix arm {arm} gate manifest")
        validated_gate = _require_mapping(
            gate.get("validated"), label=f"matrix arm {arm} validated gate"
        )
        gate_config = _require_mapping(
            validated_gate.get("config"), label=f"matrix arm {arm} gate config"
        )
        if not _close(gate_config.get("acrm_eta"), TREND_ACRM_ETA, absolute=1e-15):
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} gate ACRM eta mismatch")
        result = _require_mapping(status.get("result"), label=f"matrix arm {arm} result")
        if result.get("episodes") != header["episodes"]:
            raise IntermediateTrendAnalysisError(
                f"matrix arm {arm} result episode count mismatch"
            )
        if _path(result.get("checkpoint"), base=status_path.parent, label=f"matrix arm {arm} result checkpoint") != checkpoint_path:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} result checkpoint mismatch")
        if result.get("checkpoint_sha256") != checkpoint_sha:
            raise IntermediateTrendAnalysisError(f"matrix arm {arm} result checkpoint digest mismatch")
        by_arm[arm] = {
            "checkpoint_path": checkpoint_path,
            "checkpoint_sha256": checkpoint_sha,
            "status_path": status_path,
            "log_path": log_path,
        }
    if tuple(by_arm) != EXPECTED_ARMS:
        raise IntermediateTrendAnalysisError("matrix arm order drifted")
    return by_arm


def _verify_sweep_header(
    summary: Mapping[str, Any],
    *,
    header: Mapping[str, Any],
    prereg_path: Path,
    tle_path: Path,
    tle_file_count: int,
) -> None:
    if summary.get("schema") != SWEEP_SCHEMA:
        raise IntermediateTrendAnalysisError("sweep schema mismatch")
    if summary.get("method_family") != "Multi-Catfish MCRL":
        raise IntermediateTrendAnalysisError("sweep method family mismatch")
    if summary.get("evaluation_policy") != "Main-only masked-greedy MODQN":
        raise IntermediateTrendAnalysisError("sweep policy mismatch")
    if summary.get("evaluation_partition") != "TEST":
        raise IntermediateTrendAnalysisError("sweep partition mismatch")
    if summary.get("ee_aggregation") != (
        "per-training-seed ratio-of-sums, then equal-weight training-seed mean"
    ):
        raise IntermediateTrendAnalysisError("sweep EE aggregation mismatch")
    if summary.get("users") != list(EXPECTED_EVALUATION_USERS):
        raise IntermediateTrendAnalysisError("sweep user sweep mismatch")
    if summary.get("evaluation_seeds") != list(EXPECTED_EVALUATION_SEEDS):
        raise IntermediateTrendAnalysisError("sweep seed sweep mismatch")
    authority = _require_mapping(summary.get("authority"), label="sweep authority")
    if authority.get("prereg_path") != str(prereg_path):
        raise IntermediateTrendAnalysisError("sweep authority preregistration mismatch")
    if authority.get("prereg_sha256") != CANONICAL_PREREG_SHA256:
        raise IntermediateTrendAnalysisError("sweep authority preregistration hash mismatch")
    if authority.get("tle_root_path") != str(tle_path):
        raise IntermediateTrendAnalysisError("sweep authority TLE root mismatch")
    if authority.get("tle_file_set_sha256") != CANONICAL_TLE_FILE_SET_SHA256:
        raise IntermediateTrendAnalysisError("sweep authority TLE hash mismatch")
    if (
        type(authority.get("tle_file_count")) is not int
        or authority.get("tle_file_count") != tle_file_count
    ):
        raise IntermediateTrendAnalysisError("sweep authority TLE file count mismatch")
    checkpoints = summary.get("checkpoints")
    if not isinstance(checkpoints, list) or len(checkpoints) != len(EXPECTED_ARMS):
        raise IntermediateTrendAnalysisError("sweep checkpoints must contain five rows")


def _validate_raw_row(
    raw: Mapping[str, Any],
    *,
    expected_arm_label: str,
    expected_training_seed: int,
    expected_checkpoint_sha: str,
) -> dict[str, Any]:
    label = f"sweep raw {expected_arm_label}"
    if raw.get("arm") != expected_arm_label:
        raise IntermediateTrendAnalysisError(f"{label}: arm identity mismatch")
    if raw.get("checkpoint_sha256") != expected_checkpoint_sha:
        raise IntermediateTrendAnalysisError(f"{label}: checkpoint identity mismatch")
    if raw.get("training_seed") != expected_training_seed:
        raise IntermediateTrendAnalysisError(f"{label}: training seed mismatch")
    evaluation_seed = _integer(raw.get("evaluation_seed"), label=f"{label}.evaluation_seed")
    users = _integer(raw.get("users"), label=f"{label}.users", minimum=1)
    steps = _integer(raw.get("steps"), label=f"{label}.steps", minimum=1)
    duration = _number(raw.get("duration_s"), label=f"{label}.duration_s", minimum=0.0)
    if duration <= 0.0:
        raise IntermediateTrendAnalysisError(f"{label}: positive duration required")
    bits = _number(raw.get("useful_bits"), label=f"{label}.useful_bits", minimum=0.0)
    energy = _number(raw.get("system_energy_j"), label=f"{label}.system_energy_j", minimum=0.0)
    if energy <= 0.0:
        raise IntermediateTrendAnalysisError(f"{label}: zero system energy")
    served = _integer(raw.get("served_user_intervals"), label=f"{label}.served_user_intervals", minimum=0)
    total = _integer(raw.get("total_user_intervals"), label=f"{label}.total_user_intervals", minimum=1)
    if total != steps * users or served > total:
        raise IntermediateTrendAnalysisError(f"{label}: service denominator mismatch")
    zero_power = _integer(raw.get("zero_power_intervals"), label=f"{label}.zero_power_intervals", minimum=0)
    zero_service = _integer(raw.get("zero_service_intervals"), label=f"{label}.zero_service_intervals", minimum=0)
    if zero_power > steps or zero_service > steps:
        raise IntermediateTrendAnalysisError(f"{label}: interval count exceeds episode length")
    if zero_power != 0:
        raise IntermediateTrendAnalysisError(f"{label}: zero-power guard failed")
    expected_ee = bits / energy
    expected_service = served / total
    if not _close(raw.get("system_ee_bits_per_j"), expected_ee, absolute=1e-6):
        raise IntermediateTrendAnalysisError(f"{label}: EE ratio identity mismatch")
    if not _close(raw.get("mean_system_power_w"), energy / duration, absolute=1e-9):
        raise IntermediateTrendAnalysisError(f"{label}: power identity mismatch")
    if not _close(raw.get("mean_system_throughput_bps"), bits / duration, absolute=1e-6):
        raise IntermediateTrendAnalysisError(f"{label}: throughput identity mismatch")
    if not _close(raw.get("served_fraction"), expected_service, absolute=1e-12):
        raise IntermediateTrendAnalysisError(f"{label}: served fraction identity mismatch")
    for field in ("r1_sum", "r2_sum", "r3_sum"):
        _number(raw.get(field), label=f"{label}.{field}")
    return {
        "evaluation_seed": evaluation_seed,
        "users": users,
        "steps": steps,
        "duration_s": duration,
        "useful_bits": bits,
        "system_energy_j": energy,
        "served_user_intervals": served,
        "total_user_intervals": total,
        "served_fraction": expected_service,
        "zero_power_intervals": zero_power,
        "zero_service_intervals": zero_service,
        "system_ee_bits_per_j": expected_ee,
    }


def _validate_summary_and_raw(
    *,
    summary: Mapping[str, Any],
    raw_rows: list[Any],
    header: Mapping[str, Any],
    arm_receipts: Mapping[str, Mapping[str, Any]],
    prereg_path: Path,
    tle_path: Path,
    tle_file_count: int,
) -> dict[int, dict[str, dict[str, Any]]]:
    _verify_sweep_header(
        summary,
        header=header,
        prereg_path=prereg_path,
        tle_path=tle_path,
        tle_file_count=tle_file_count,
    )
    expected_training_seed = int(header["training"]["training_seed"])
    expected_keys = {
        (ARM_LABELS[arm], users, seed)
        for arm in EXPECTED_ARMS
        for users in EXPECTED_EVALUATION_USERS
        for seed in EXPECTED_EVALUATION_SEEDS
    }
    seen: set[tuple[str, int, int]] = set()
    by_arm_users: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    if len(raw_rows) != len(expected_keys):
        raise IntermediateTrendAnalysisError("sweep raw row count must be exactly 125")
    for index, item in enumerate(raw_rows):
        raw = _require_mapping(item, label=f"sweep-raw[{index}]")
        arm_label = raw.get("arm")
        if arm_label not in ARM_BY_LABEL:
            raise IntermediateTrendAnalysisError(f"sweep-raw[{index}] has unknown arm")
        arm = ARM_BY_LABEL[arm_label]
        parsed = _validate_raw_row(
            raw,
            expected_arm_label=arm_label,
            expected_training_seed=expected_training_seed,
            expected_checkpoint_sha=str(arm_receipts[arm]["checkpoint_sha256"]),
        )
        key = (arm_label, parsed["users"], parsed["evaluation_seed"])
        if key in seen or key not in expected_keys:
            raise IntermediateTrendAnalysisError("sweep raw cells are incomplete or duplicated")
        seen.add(key)
        by_arm_users[(arm, parsed["users"])].append(parsed)
    if seen != expected_keys:
        raise IntermediateTrendAnalysisError("sweep raw cells do not match the exact arm/load/seed grid")

    summary_rows = summary.get("summary")
    if not isinstance(summary_rows, list) or len(summary_rows) != len(EXPECTED_ARMS) * len(EXPECTED_EVALUATION_USERS):
        raise IntermediateTrendAnalysisError("sweep summary must contain exactly 25 cells")
    summary_map: dict[tuple[str, int], Mapping[str, Any]] = {}
    for index, item in enumerate(summary_rows):
        row = _require_mapping(item, label=f"sweep summary[{index}]")
        label = row.get("arm")
        if label not in ARM_BY_LABEL:
            raise IntermediateTrendAnalysisError("sweep summary has unknown arm")
        users = _integer(row.get("users"), label=f"sweep summary[{index}].users")
        key = (ARM_BY_LABEL[label], users)
        if key in summary_map or users not in EXPECTED_EVALUATION_USERS:
            raise IntermediateTrendAnalysisError("sweep summary cells are incomplete or duplicated")
        if type(row.get("training_seed_count")) is not int or row["training_seed_count"] != 1:
            raise IntermediateTrendAnalysisError("sweep summary must contain one training seed per cell")
        seed_rows = row.get("seed_rows")
        if not isinstance(seed_rows, list) or len(seed_rows) != 1:
            raise IntermediateTrendAnalysisError("sweep summary seed_rows must contain one row")
        seed_row = _require_mapping(seed_rows[0], label=f"sweep summary[{index}].seed_rows[0]")
        if seed_row.get("arm") != label or seed_row.get("users") != users or seed_row.get("training_seed") != expected_training_seed:
            raise IntermediateTrendAnalysisError("sweep summary seed identity mismatch")
        if seed_row.get("evaluation_seeds") != list(EXPECTED_EVALUATION_SEEDS):
            raise IntermediateTrendAnalysisError("sweep summary seed list mismatch")
        cell = by_arm_users[key]
        bits = math.fsum(item["useful_bits"] for item in cell)
        energy = math.fsum(item["system_energy_j"] for item in cell)
        duration = math.fsum(item["duration_s"] for item in cell)
        served = sum(item["served_user_intervals"] for item in cell)
        total = sum(item["total_user_intervals"] for item in cell)
        ee = bits / energy
        service = served / total
        for source, value in (
            (seed_row.get("system_ee_bits_per_j"), ee),
            (seed_row.get("served_fraction"), service),
            (seed_row.get("mean_system_power_w"), energy / duration),
            (seed_row.get("mean_system_throughput_bps"), bits / duration),
            (row.get("mean_ee_bits_per_j"), ee),
            (row.get("median_ee_bits_per_j"), ee),
            (row.get("min_ee_bits_per_j"), ee),
            (row.get("max_ee_bits_per_j"), ee),
        ):
            if not _close(source, value, absolute=1e-6):
                raise IntermediateTrendAnalysisError("sweep summary is inconsistent with ratio-of-sums raw data")
        for field, value in (
            ("zero_power_intervals", sum(item["zero_power_intervals"] for item in cell)),
            ("zero_service_intervals", sum(item["zero_service_intervals"] for item in cell)),
        ):
            if seed_row.get(field) != value:
                raise IntermediateTrendAnalysisError(f"sweep summary {field} mismatch")
        summary_map[key] = {
            "ee_bits_per_j": ee,
            "served_fraction": service,
            "useful_bits": bits,
            "system_energy_j": energy,
            "zero_power_intervals": 0,
            "zero_service_intervals": sum(item["zero_service_intervals"] for item in cell),
        }
    expected_summary_keys = {
        (arm, users) for arm in EXPECTED_ARMS for users in EXPECTED_EVALUATION_USERS
    }
    if set(summary_map) != expected_summary_keys:
        raise IntermediateTrendAnalysisError("sweep summary cells do not match the exact grid")
    return {
        users: {arm: summary_map[(arm, users)] for arm in EXPECTED_ARMS}
        for users in EXPECTED_EVALUATION_USERS
    }


def _verify_sweep_checkpoints(
    summary: Mapping[str, Any],
    *,
    arm_receipts: Mapping[str, Mapping[str, Any]],
    header: Mapping[str, Any],
) -> None:
    rows = summary.get("checkpoints")
    seen: list[str] = []
    for index, item in enumerate(rows):
        row = _require_mapping(item, label=f"sweep checkpoints[{index}]")
        label = row.get("arm")
        if label not in ARM_BY_LABEL:
            raise IntermediateTrendAnalysisError("sweep checkpoint label unknown")
        arm = ARM_BY_LABEL[label]
        if arm in seen:
            raise IntermediateTrendAnalysisError("sweep checkpoint label duplicated")
        seen.append(arm)
        checkpoint_path = _path(row.get("path"), base=HERE, label=f"sweep checkpoint {arm}")
        expected_path = Path(arm_receipts[arm]["checkpoint_path"]).resolve()
        if checkpoint_path != expected_path:
            raise IntermediateTrendAnalysisError(f"sweep checkpoint {arm} path mismatch")
        checkpoint_sha = _digest(row.get("sha256"), label=f"sweep checkpoint {arm} sha256")
        if checkpoint_sha != arm_receipts[arm]["checkpoint_sha256"] or sha256_file(checkpoint_path) != checkpoint_sha:
            raise IntermediateTrendAnalysisError(f"sweep checkpoint {arm} hash mismatch")
        if row.get("episode") != header["episodes"] - 1 or row.get("training_seed") != header["training"]["training_seed"]:
            raise IntermediateTrendAnalysisError(f"sweep checkpoint {arm} metadata mismatch")
    if tuple(seen) != EXPECTED_ARMS:
        raise IntermediateTrendAnalysisError("sweep checkpoints do not contain exact five-arm order")


def _validate_trajectory_summary(
    path: Path,
    *,
    matrix: Mapping[str, Any],
    matrix_receipt_path: Path,
    prereg_path: Path,
    tle_path: Path,
    tle_file_count: int,
) -> dict[str, Any]:
    """Validate an optional 100EP checkpoint-trend summary.

    This is deliberately a separate diagnostic surface.  It is bound to the
    matrix and its authority, but it never replaces the final-checkpoint
    five-load endpoint used for the contrasts below.
    """

    summary_path = Path(path).expanduser().resolve()
    payload = _read_object(summary_path, label="checkpoint-trend summary")
    if payload.get("schema") != TRAJECTORY_SCHEMA:
        raise IntermediateTrendAnalysisError("checkpoint-trend schema mismatch")
    if payload.get("status") != "complete":
        raise IntermediateTrendAnalysisError("checkpoint-trend summary is not complete")
    if payload.get("claim_ceiling") != TRAJECTORY_CLAIM_CEILING:
        raise IntermediateTrendAnalysisError("checkpoint-trend claim ceiling mismatch")
    if payload.get("episodes") != matrix["episodes"]:
        raise IntermediateTrendAnalysisError("checkpoint-trend episode count mismatch")
    if payload.get("checkpoint_every_episodes") != TREND_CHECKPOINT_EVERY_EPISODES:
        raise IntermediateTrendAnalysisError("checkpoint-trend cadence mismatch")
    if payload.get("training_seed") != matrix["training"]["training_seed"]:
        raise IntermediateTrendAnalysisError("checkpoint-trend training seed mismatch")
    if payload.get("users") != TREND_USERS:
        raise IntermediateTrendAnalysisError("checkpoint-trend users mismatch")
    if payload.get("evaluation_seeds") != list(EXPECTED_EVALUATION_SEEDS):
        raise IntermediateTrendAnalysisError("checkpoint-trend evaluation seeds mismatch")
    if payload.get("evaluation_partition") != "TEST":
        raise IntermediateTrendAnalysisError("checkpoint-trend partition mismatch")
    if payload.get("evaluation_policy") != "Main-only masked-greedy MODQN":
        raise IntermediateTrendAnalysisError("checkpoint-trend policy mismatch")
    if payload.get("ee_aggregation") != (
        "ratio of pooled useful bits to pooled system energy within each arm/checkpoint cell"
    ):
        raise IntermediateTrendAnalysisError("checkpoint-trend EE aggregation mismatch")
    authority = _require_mapping(payload.get("authority"), label="checkpoint-trend authority")
    if authority.get("prereg_path") != str(prereg_path):
        raise IntermediateTrendAnalysisError("checkpoint-trend preregistration mismatch")
    if authority.get("prereg_sha256") != CANONICAL_PREREG_SHA256:
        raise IntermediateTrendAnalysisError("checkpoint-trend preregistration hash mismatch")
    if authority.get("tle_root_path") != str(tle_path):
        raise IntermediateTrendAnalysisError("checkpoint-trend TLE root mismatch")
    if authority.get("tle_file_set_sha256") != CANONICAL_TLE_FILE_SET_SHA256:
        raise IntermediateTrendAnalysisError("checkpoint-trend TLE hash mismatch")
    if (
        type(authority.get("tle_file_count")) is not int
        or authority.get("tle_file_count") != tle_file_count
    ):
        raise IntermediateTrendAnalysisError("checkpoint-trend TLE file count mismatch")
    matrix_ref = _path(
        payload.get("matrix_receipt"),
        base=summary_path.parent,
        label="checkpoint-trend matrix receipt",
    )
    if matrix_ref != matrix_receipt_path:
        raise IntermediateTrendAnalysisError("checkpoint-trend matrix receipt mismatch")
    if payload.get("matrix_receipt_sha256") != sha256_file(matrix_receipt_path):
        raise IntermediateTrendAnalysisError("checkpoint-trend matrix receipt hash mismatch")

    schedule = tuple(
        range(
            TREND_CHECKPOINT_EVERY_EPISODES,
            int(matrix["episodes"]) + 1,
            TREND_CHECKPOINT_EVERY_EPISODES,
        )
    )
    rows = payload.get("summary")
    expected_count = len(EXPECTED_ARMS) * len(schedule)
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise IntermediateTrendAnalysisError("checkpoint-trend summary grid is incomplete")
    expected_keys = {
        (arm, completed) for arm in EXPECTED_ARMS for completed in schedule
    }
    seen: set[tuple[str, int]] = set()
    for index, item in enumerate(rows):
        row = _require_mapping(item, label=f"checkpoint-trend summary[{index}]")
        arm = row.get("arm")
        completed = row.get("episodes_completed")
        key = (arm, completed)
        if arm not in EXPECTED_ARMS or type(completed) is not int or key in seen:
            raise IntermediateTrendAnalysisError("checkpoint-trend summary has duplicate or unknown cell")
        if key not in expected_keys:
            raise IntermediateTrendAnalysisError("checkpoint-trend summary episode is outside the cadence")
        if row.get("arm_label") != ARM_LABELS[arm] or row.get("users") != TREND_USERS:
            raise IntermediateTrendAnalysisError("checkpoint-trend summary identity mismatch")
        if row.get("evaluation_seeds") != list(EXPECTED_EVALUATION_SEEDS):
            raise IntermediateTrendAnalysisError("checkpoint-trend cell seed list mismatch")
        bits = _number(row.get("useful_bits"), label=f"checkpoint-trend summary[{index}].useful_bits", minimum=0.0)
        energy = _number(row.get("system_energy_j"), label=f"checkpoint-trend summary[{index}].system_energy_j", minimum=0.0)
        if energy <= 0.0:
            raise IntermediateTrendAnalysisError("checkpoint-trend cell has zero system energy")
        if not _close(row.get("system_ee_bits_per_j"), bits / energy, absolute=1e-6):
            raise IntermediateTrendAnalysisError("checkpoint-trend EE identity mismatch")
        for field in ("zero_power_intervals", "zero_service_intervals"):
            _integer(row.get(field), label=f"checkpoint-trend summary[{index}].{field}", minimum=0)
        seen.add(key)
    if seen != expected_keys:
        raise IntermediateTrendAnalysisError("checkpoint-trend summary cells do not match exact grid")
    return {
        "path": str(summary_path),
        "sha256": sha256_file(summary_path),
        "matrix_receipt": str(matrix_receipt_path),
        "matrix_receipt_sha256": sha256_file(matrix_receipt_path),
        "episodes": matrix["episodes"],
        "checkpoint_every_episodes": TREND_CHECKPOINT_EVERY_EPISODES,
        "rows": expected_count,
    }


def _contrast_row(cell: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    values = {arm: float(cell[arm]["ee_bits_per_j"]) for arm in EXPECTED_ARMS}
    if any(
        not _finite(values[arm]) or values[arm] <= 0.0
        for arm in ("B000", "A011", "A101", "A110")
    ):
        raise IntermediateTrendAnalysisError(
            "non-positive comparator EE cell prevents contrast calculation"
        )
    if not _finite(values["F111"]) or values["F111"] < 0.0:
        raise IntermediateTrendAnalysisError("negative or non-finite full EE cell")
    return {
        name: 100.0 * (values["F111"] - values[denominator]) / values[denominator]
        for name, denominator in CONTRAST_DENOMINATORS.items()
    }


def _mean(values: Sequence[float]) -> float:
    return math.fsum(float(value) for value in values) / len(values)


def _sign(mean: float, positive_loads: int) -> str:
    if mean > 0.0 and positive_loads == len(EXPECTED_EVALUATION_USERS):
        return "positive"
    if mean < 0.0 and positive_loads == 0:
        return "negative"
    return "mixed"


def _analyse_one_matrix(root: Path) -> dict[str, Any]:
    matrix_root = Path(root).expanduser().resolve()
    receipt_path = matrix_root / "matrix-receipt.json"
    receipt = _read_object(receipt_path, label="matrix receipt")
    header, authority_path, prereg_path, c1_path, tle_path = _validate_matrix_header(
        receipt, receipt_path=receipt_path
    )
    tle_digest, tle_file_count = canonical_tle_file_set_hash(tle_path)
    if tle_digest != CANONICAL_TLE_FILE_SET_SHA256:
        raise IntermediateTrendAnalysisError("matrix TLE hash changed during analysis")
    arm_receipts = _verify_arm_runs(
        receipt,
        receipt_path=receipt_path,
        header=header,
        authority_path=authority_path,
        prereg_path=prereg_path,
        c1_path=c1_path,
        tle_path=tle_path,
        tle_file_count=tle_file_count,
    )
    sweep_receipt = _require_mapping(receipt.get("sweep"), label="matrix sweep receipt")
    if sweep_receipt.get("status") != "PASS":
        raise IntermediateTrendAnalysisError("matrix sweep receipt is not PASS")
    sweep_verification = _require_mapping(
        sweep_receipt.get("verification"), label="matrix sweep verification"
    )
    if sweep_verification.get("status") != "PASS":
        raise IntermediateTrendAnalysisError("matrix sweep verification is not PASS")
    summary_path = _path(
        sweep_verification.get("summary_path"),
        base=receipt_path.parent,
        label="matrix sweep summary",
    )
    raw_path = _path(
        sweep_verification.get("raw_path"),
        base=receipt_path.parent,
        label="matrix sweep raw",
    )
    plot_status_path = _path(
        sweep_verification.get("plot_status_path"),
        base=receipt_path.parent,
        label="matrix sweep plot status",
    )
    for path, field in (
        (summary_path, "summary_sha256"),
        (raw_path, "raw_sha256"),
        (plot_status_path, "plot_status_sha256"),
    ):
        if not path.is_file():
            raise IntermediateTrendAnalysisError(f"matrix sweep artifact is missing: {path}")
        digest = _digest(sweep_verification.get(field), label=f"matrix sweep {field}")
        if sha256_file(path) != digest:
            raise IntermediateTrendAnalysisError(f"matrix sweep artifact hash mismatch: {path}")
    plot_status = _read_object(plot_status_path, label="sweep plot status")
    if plot_status.get("status") == "complete":
        plot_path = _path(
            plot_status.get("path"),
            base=plot_status_path.parent,
            label="sweep plot",
        )
        if not plot_path.is_file():
            raise IntermediateTrendAnalysisError(f"sweep plot is missing: {plot_path}")
    elif plot_status.get("status") != "data-complete-plot-dependency-missing":
        raise IntermediateTrendAnalysisError("sweep plot status is not accepted")
    summary = _read_object(summary_path, label="sweep summary")
    raw_rows = _read_list(raw_path, label="sweep raw")
    _verify_sweep_checkpoints(summary, arm_receipts=arm_receipts, header=header)
    cells = _validate_summary_and_raw(
        summary=summary,
        raw_rows=raw_rows,
        header=header,
        arm_receipts=arm_receipts,
        prereg_path=prereg_path,
        tle_path=tle_path,
        tle_file_count=tle_file_count,
    )
    loads: list[dict[str, Any]] = []
    contrasts_by_name: dict[str, list[float]] = {name: [] for name in CONTRASTS}
    served_deltas: list[float] = []
    service_limit = (
        STAGE1_SERVICE_LOSS_PP if header["episodes"] == 1500 else STAGE2_SERVICE_LOSS_PP
    )
    for users in EXPECTED_EVALUATION_USERS:
        cell = cells[users]
        contrasts = _contrast_row(cell)
        for name, value in contrasts.items():
            contrasts_by_name[name].append(value)
        served_delta_pp = 100.0 * (
            cell["F111"]["served_fraction"] - cell["B000"]["served_fraction"]
        )
        served_deltas.append(served_delta_pp)
        loads.append(
            {
                "users": users,
                "ee_bits_per_j": {
                    arm: cell[arm]["ee_bits_per_j"] for arm in EXPECTED_ARMS
                },
                "served_fraction": {
                    arm: cell[arm]["served_fraction"] for arm in EXPECTED_ARMS
                },
                "served_fraction_full_minus_baseline_pp": served_delta_pp,
                "contrasts_percent": contrasts,
                "contrasts": dict(contrasts),
            }
        )
    means = {name: _mean(values) for name, values in contrasts_by_name.items()}
    positive_load_counts = {
        name: sum(value > 0.0 for value in values)
        for name, values in contrasts_by_name.items()
    }
    contrast_signs = {
        name: _sign(means[name], positive_load_counts[name]) for name in CONTRASTS
    }
    service_guard_pass = all(
        delta > -service_limit
        or math.isclose(delta, -service_limit, abs_tol=1e-12, rel_tol=0.0)
        for delta in served_deltas
    )
    eligibility_failures: list[str] = []
    if not service_guard_pass:
        eligibility_failures.append(
            f"full served fraction loses more than {service_limit:.1f} percentage points"
        )
    # All numeric, zero-power, completeness, identity, and authority checks
    # have already failed closed above.  Keep this explicit in the receipt so
    # downstream consumers can see what was actually checked.
    guards = {
        "finite_values": True,
        "zero_power_intervals": True,
        "complete_5_arm_5_load_5_seed_grid": True,
        "checkpoint_and_status_hashes": True,
        "authority_hashes": True,
        "served_fraction": service_guard_pass,
    }
    eligible = not eligibility_failures
    score = min(means["d_C1"], means["d_C2"], means["d_C3"]) if eligible else None
    directional: dict[str, Any] | None = None
    if header["episodes"] == 3000:
        directional_pass = (
            eligible
            and all(means[name] > 0.0 for name in CONTRASTS)
            and all(positive_load_counts[name] >= 4 for name in CONTRASTS)
            and service_guard_pass
        )
        reasons: list[str] = []
        if not eligible:
            reasons.extend(eligibility_failures)
        for name in CONTRASTS:
            if means[name] <= 0.0:
                reasons.append(f"{name} mean is not positive")
            if positive_load_counts[name] < 4:
                reasons.append(f"{name} positive at only {positive_load_counts[name]}/5 loads")
        if not service_guard_pass:
            reasons.append("served-fraction guard failed")
        directional = {
            "label": (
                "ALL_THREE_DIRECTIONALLY_EE_POSITIVE"
                if directional_pass
                else "NOT_ALL_THREE_DIRECTIONALLY_EE_POSITIVE"
            ),
            "pass": directional_pass,
            "reasons": list(dict.fromkeys(reasons)),
            "contrast_signs": contrast_signs,
            "positive_load_counts": positive_load_counts,
            "served_fraction_guard_pass": service_guard_pass,
        }

    return {
        "matrix_root": str(matrix_root),
        "matrix_receipt": str(receipt_path),
        "authority_manifest": str(authority_path),
        "authority_manifest_sha256": sha256_file(authority_path),
        "authority_validation": header["authority_validation"],
        "episodes": header["episodes"],
        "learning_rate": header["learning_rate"],
        "training": header["training"],
        "evaluation": header["evaluation"],
        "canonical_inputs": {
            "prereg": str(prereg_path),
            "prereg_sha256": sha256_file(prereg_path),
            "c1_exp_corpus_manifest": str(c1_path),
            "c1_exp_corpus_manifest_sha256": sha256_file(c1_path),
            "tle_root": str(tle_path),
            "tle_file_set_sha256": CANONICAL_TLE_FILE_SET_SHA256,
            "tle_file_count": tle_file_count,
        },
        "sweep_artifacts": {
            "summary": str(summary_path),
            "summary_sha256": sha256_file(summary_path),
            "raw": str(raw_path),
            "raw_sha256": sha256_file(raw_path),
            "plot_status": str(plot_status_path),
            "plot_status_sha256": sha256_file(plot_status_path),
            "plot_status_value": plot_status.get("status"),
        },
        "loads": loads,
        "mean_contrasts_percent": means,
        "mean_contrasts": dict(means),
        "positive_load_counts": positive_load_counts,
        "contrast_signs": contrast_signs,
        "served_fraction_full_minus_baseline_pp": {
            "by_load": served_deltas,
            "minimum": min(served_deltas),
            "guard_limit_loss_pp": service_limit,
            "guard_pass": service_guard_pass,
        },
        "guards": guards,
        "eligible_for_3000": eligible,
        "lr_score_min_mean_catfish_contrast": score,
        "directional_3000": directional,
    }


def _select_learning_rate(matrices: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    candidates = [
        matrix
        for matrix in matrices
        if matrix["episodes"] == 1500
    ]
    if not candidates:
        return {
            "status": "NOT_APPLICABLE",
            "reason": "no 1500-episode matrix was supplied",
            "tie_rule_percentage_points": LR_TIE_PP,
            "candidates": [],
            "selected_learning_rate": None,
        }
    by_lr: dict[float, Mapping[str, Any]] = {}
    for matrix in candidates:
        lr = float(matrix["learning_rate"])
        if lr in by_lr:
            raise IntermediateTrendAnalysisError(
                "two 1500-episode matrices use the same learning rate"
            )
        by_lr[lr] = matrix
    candidate_rows = [
        {
            "learning_rate": lr,
            "matrix_root": matrix["matrix_root"],
            "eligible": matrix["eligible_for_3000"],
            "score": matrix["lr_score_min_mean_catfish_contrast"],
        }
        for lr, matrix in sorted(by_lr.items())
    ]
    eligible = [
        (lr, matrix)
        for lr, matrix in sorted(by_lr.items())
        if matrix["eligible_for_3000"]
    ]
    if len(candidates) == 1:
        return {
            "status": "NEEDS_SECOND_1500_LR",
            "reason": "one 1500-episode learning-rate matrix is insufficient for selection",
            "tie_rule_percentage_points": LR_TIE_PP,
            "candidates": candidate_rows,
            "selected_learning_rate": None,
        }
    if not eligible:
        return {
            "status": "STOP_NO_ELIGIBLE_LR",
            "reason": "neither 1500-episode learning-rate matrix passed eligibility",
            "tie_rule_percentage_points": LR_TIE_PP,
            "candidates": candidate_rows,
            "selected_learning_rate": None,
        }
    if len(eligible) == 1:
        selected = eligible[0][0]
        reason = "only one learning rate passed eligibility"
    else:
        left_lr, left = eligible[0]
        right_lr, right = eligible[1]
        left_score = float(left["lr_score_min_mean_catfish_contrast"])
        right_score = float(right["lr_score_min_mean_catfish_contrast"])
        if abs(left_score - right_score) <= LR_TIE_PP:
            if 0.001 not in (left_lr, right_lr):
                raise IntermediateTrendAnalysisError("tie rule requires the 0.001 candidate")
            selected = 0.001
            reason = "score difference is within the 0.25 percentage-point tie rule"
        else:
            selected = left_lr if left_score > right_score else right_lr
            reason = "larger minimum Catfish contrast score"
    return {
        "status": "SELECTED",
        "reason": reason,
        "tie_rule_percentage_points": LR_TIE_PP,
        "score_definition": "min(mean(d_C1), mean(d_C2), mean(d_C3))",
        "candidates": candidate_rows,
        "selected_learning_rate": selected,
    }


def _write_csv(path: Path, matrices: Sequence[Mapping[str, Any]]) -> None:
    import csv

    fields = [
        "matrix_root",
        "episodes",
        "learning_rate",
        "users",
        "E_B000_bits_per_j",
        "E_F111_bits_per_j",
        "E_A011_bits_per_j",
        "E_A101_bits_per_j",
        "E_A110_bits_per_j",
        "d_full_percent",
        "d_C1_percent",
        "d_C2_percent",
        "d_C3_percent",
        "d_full",
        "d_C1",
        "d_C2",
        "d_C3",
        "served_B000",
        "served_F111",
        "served_full_minus_baseline_pp",
        "eligible_for_3000",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for matrix in matrices:
            for row in matrix["loads"]:
                writer.writerow(
                    {
                        "matrix_root": matrix["matrix_root"],
                        "episodes": matrix["episodes"],
                        "learning_rate": matrix["learning_rate"],
                        "users": row["users"],
                        "E_B000_bits_per_j": row["ee_bits_per_j"]["B000"],
                        "E_F111_bits_per_j": row["ee_bits_per_j"]["F111"],
                        "E_A011_bits_per_j": row["ee_bits_per_j"]["A011"],
                        "E_A101_bits_per_j": row["ee_bits_per_j"]["A101"],
                        "E_A110_bits_per_j": row["ee_bits_per_j"]["A110"],
                        "d_full_percent": row["contrasts_percent"]["d_full"],
                        "d_C1_percent": row["contrasts_percent"]["d_C1"],
                        "d_C2_percent": row["contrasts_percent"]["d_C2"],
                        "d_C3_percent": row["contrasts_percent"]["d_C3"],
                        "d_full": row["contrasts_percent"]["d_full"],
                        "d_C1": row["contrasts_percent"]["d_C1"],
                        "d_C2": row["contrasts_percent"]["d_C2"],
                        "d_C3": row["contrasts_percent"]["d_C3"],
                        "served_B000": row["served_fraction"]["B000"],
                        "served_F111": row["served_fraction"]["F111"],
                        "served_full_minus_baseline_pp": row["served_fraction_full_minus_baseline_pp"],
                        "eligible_for_3000": matrix["eligible_for_3000"],
                    }
                )


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _write_markdown(path: Path, result: Mapping[str, Any]) -> None:
    lines = [
        "# Intermediate Multi-Catfish MCRL trend analysis",
        "",
        f"Claim ceiling: `{result['claim_ceiling']}`.",
        "",
        "This is a held-out Main-only ratio-of-sums trend screen. It contains no significance claim and does not authorize 9000EP.",
        "",
        "## Learning-rate decision",
        "",
        f"Status: `{result['learning_rate_selection']['status']}`; selected learning rate: `{_fmt(result['learning_rate_selection'].get('selected_learning_rate'))}`.",
        f"Rule: `{result['learning_rate_selection'].get('score_definition', 'eligible-only comparison')}`; tie threshold: `{LR_TIE_PP:.2f}` percentage points, with `0.001` selected on a tie.",
        f"Optional 100EP checkpoint-trend summaries bound: `{len(result.get('trajectory_summaries', ()))}`.",
        "",
    ]
    for matrix in result["matrices"]:
        lines.extend(
            [
                f"## {matrix['episodes']}EP, lr={matrix['learning_rate']}",
                "",
                f"Eligibility for 3000EP selection: `{_fmt(matrix['eligible_for_3000'])}`. LR score `S(lr) = {_fmt(matrix['lr_score_min_mean_catfish_contrast'])}` percentage points.",
                "",
                "| Users | E(B000) | E(F111) | d_full | d_C1 | d_C2 | d_C3 | Δserved(F−B), pp |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in matrix["loads"]:
            ee = row["ee_bits_per_j"]
            d = row["contrasts_percent"]
            lines.append(
                "| {users} | {b:.4f} | {f:.4f} | {df:.4f} | {d1:.4f} | {d2:.4f} | {d3:.4f} | {s:.4f} |".format(
                    users=row["users"],
                    b=ee["B000"] / 1e6,
                    f=ee["F111"] / 1e6,
                    df=d["d_full"],
                    d1=d["d_C1"],
                    d2=d["d_C2"],
                    d3=d["d_C3"],
                    s=row["served_fraction_full_minus_baseline_pp"],
                )
            )
        lines.extend(
            [
                "",
                "Mean contrasts: "
                + ", ".join(
                    f"{name}={_fmt(matrix['mean_contrasts_percent'][name])}%"
                    for name in CONTRASTS
                )
                + ".",
                "Signs are preserved exactly; negative or mixed contrasts are not relabelled.",
                "",
            ]
        )
        if matrix["directional_3000"] is not None:
            directional = matrix["directional_3000"]
            lines.extend(
                [
                    f"3000EP directional gate: `{directional['label']}`.",
                    "Reasons: " + ("; ".join(directional["reasons"]) or "none") + ".",
                    "",
                ]
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyse_matrix_roots(
    matrix_roots: Sequence[Path],
    *,
    output_dir: Path,
    trajectory_summaries: Sequence[Path] | None = None,
) -> dict[str, Any]:
    """Analyse one or two completed matrix roots and emit three files."""

    if not 1 <= len(matrix_roots) <= 2:
        raise IntermediateTrendAnalysisError("provide one or two matrix roots")
    resolved = [Path(item).expanduser().resolve() for item in matrix_roots]
    if len(set(resolved)) != len(resolved):
        raise IntermediateTrendAnalysisError("duplicate matrix roots are forbidden")
    output = Path(output_dir).expanduser().resolve()
    if output.exists():
        raise IntermediateTrendAnalysisError(
            f"analysis output directory must be absent: {output}"
        )
    matrices = [_analyse_one_matrix(root) for root in resolved]
    matrix_keys = [(int(row["episodes"]), float(row["learning_rate"])) for row in matrices]
    if len(set(matrix_keys)) != len(matrix_keys):
        raise IntermediateTrendAnalysisError(
            "duplicate (episodes, learning_rate) matrices are forbidden"
        )
    if sum(row["episodes"] == 3000 for row in matrices) > 1:
        raise IntermediateTrendAnalysisError("at most one 3000-episode matrix may be supplied")
    matrices.sort(key=lambda row: (int(row["episodes"]), float(row["learning_rate"]), row["matrix_root"]))
    trajectory_receipts: list[dict[str, Any]] = []
    trajectory_paths = list(trajectory_summaries or ())
    if len(trajectory_paths) > len(matrices):
        raise IntermediateTrendAnalysisError(
            "at most one checkpoint-trend summary may be supplied per matrix"
        )
    if len({Path(item).expanduser().resolve() for item in trajectory_paths}) != len(trajectory_paths):
        raise IntermediateTrendAnalysisError("duplicate checkpoint-trend summaries are forbidden")
    matrix_by_receipt = {
        Path(matrix["matrix_receipt"]).resolve(): matrix for matrix in matrices
    }
    for trajectory_path in trajectory_paths:
        raw_trajectory_path = Path(trajectory_path).expanduser().resolve()
        payload = _read_object(raw_trajectory_path, label="checkpoint-trend summary")
        matrix_ref = _path(
            payload.get("matrix_receipt"),
            base=raw_trajectory_path.parent,
            label="checkpoint-trend matrix receipt",
        )
        matrix = matrix_by_receipt.get(matrix_ref)
        if matrix is None:
            raise IntermediateTrendAnalysisError(
                "checkpoint-trend summary does not reference a supplied matrix"
            )
        trajectory_receipts.append(
            _validate_trajectory_summary(
                raw_trajectory_path,
                matrix=matrix,
                matrix_receipt_path=matrix_ref,
                prereg_path=Path(matrix["canonical_inputs"]["prereg"]).resolve(),
                tle_path=Path(matrix["canonical_inputs"]["tle_root"]).resolve(),
                tle_file_count=int(matrix["canonical_inputs"]["tle_file_count"]),
            )
        )
    trajectory_receipts.sort(key=lambda item: item["matrix_receipt"])
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "complete",
        "claim_ceiling": CLAIM_CEILING,
        "evidence_ceiling": "Intermediate 1500/3000-episode trend screen only: not Chapter 5, not formal efficacy, and not 9000-episode training authorization.",
        "formal_training_authorized": False,
        "no_significance_claim": True,
        "matrices": matrices,
        "learning_rate_selection": _select_learning_rate(matrices),
        "directional_3000_results": [
            {
                "matrix_root": matrix["matrix_root"],
                "learning_rate": matrix["learning_rate"],
                "result": matrix["directional_3000"],
            }
            for matrix in matrices
            if matrix["directional_3000"] is not None
        ],
        "trajectory_summaries": trajectory_receipts,
    }
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "intermediate-trend-analysis.json", result)
    _write_csv(output / "intermediate-trend-analysis.csv", matrices)
    _write_markdown(output / "intermediate-trend-analysis.md", result)
    return result


# Keep the public spelling discoverable to callers using American English;
# the CLI and the original plan use the British ``analyse`` spelling.
analyze_matrix_roots = analyse_matrix_roots


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matrix-root",
        "--matrix",
        dest="matrix_roots",
        type=Path,
        action="append",
        required=True,
        help="completed matrix root; repeat at most twice",
    )
    parser.add_argument(
        "--trajectory-summary",
        dest="trajectory_summaries",
        type=Path,
        action="append",
        help="optional validated checkpoint-trend-summary.json; repeat per matrix",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if len(args.matrix_roots) > 2:
        parser.error("--matrix-root may be supplied at most twice")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        analyse_matrix_roots(
            args.matrix_roots,
            output_dir=args.output_dir,
            trajectory_summaries=args.trajectory_summaries,
        )
    except IntermediateTrendAnalysisError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(Path(args.output_dir).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
