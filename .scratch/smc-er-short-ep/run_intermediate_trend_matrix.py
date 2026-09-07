#!/usr/bin/env python3
"""Run the sealed five-arm intermediate Multi-Catfish MCRL trend screen.

This launcher is the only orchestration surface for the bounded 1,500/3,000
episode screen.  It validates one authority JSON before creating the output
root, starts exactly the five preregistered arms, and then invokes the
Main-only held-out EE sweep.  The launcher deliberately has no retry path:
once an arm fails, queued arms are not started, while already-running arms are
allowed to finish so that the receipt remains an honest execution record.

The resulting matrix is an intermediate trend diagnostic.  Its claim ceiling
is copied from the validated authority and is never upgraded to Chapter 5,
formal efficacy, or 9,000-episode evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from intermediate_trend_authority import (  # noqa: E402
    ALLOWED_ARMS,
    CANONICAL_TLE_FILE_SET_SHA256,
    TREND_ACRM_ETA,
    TREND_CHECKPOINT_EVERY_EPISODES,
    TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
    TREND_EPSILON_DECAY_EPISODES,
    TREND_TARGET_UPDATE_EVERY,
    validate_intermediate_trend_authority,
)
from mcrl.artifacts import read_checkpoint  # noqa: E402


SCHEMA = "multi-catfish-mcrl-intermediate-trend-matrix-v1"
RUNNER = HERE / "run_short_ep.py"
SWEEP = HERE / "sweep_evaluation.py"
TIME_V = Path("/usr/bin/time")
TLE_FILE_RE = re.compile(r"^starlink_\d{8}\.tle$")

ARM_LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A011": "Full - C1",
    "A101": "Full - C2",
    "A110": "Full - C3",
}
SMOKE_EPISODES = 10
SMOKE_CLAIM_CEILING = "TEN_EP_ENGINEERING_SMOKE_NOT_TREND_EVIDENCE"


class IntermediateTrendMatrixError(RuntimeError):
    """Raised when a matrix cannot be authorised or completed."""


def sha256_file(path: Path) -> str:
    """Hash a file without loading it into memory all at once."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write a deterministic receipt atomically."""

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
        raise IntermediateTrendMatrixError(
            f"{label} is unreadable: {path}"
        ) from error
    if not isinstance(value, Mapping):
        raise IntermediateTrendMatrixError(f"{label} must be a JSON object: {path}")
    return value


def load_and_validate_authority(path: Path, *, tle_root: Path) -> dict[str, Any]:
    """Load one authority JSON and pass it through the canonical validator."""

    authority_path = Path(path).expanduser().resolve()
    request = _read_object(authority_path, label="intermediate trend authority")
    try:
        validated = validate_intermediate_trend_authority(
            request,
            repo=REPO,
            tle_root=Path(tle_root).expanduser().resolve(),
        )
    except Exception as error:
        raise IntermediateTrendMatrixError(
            f"intermediate trend authority rejected: {error}"
        ) from error
    if not isinstance(validated, Mapping) or validated.get("status") != "PASS":
        raise IntermediateTrendMatrixError(
            "intermediate trend authority validator did not return PASS"
        )
    if tuple(validated.get("arms", ())) != tuple(ALLOWED_ARMS):
        raise IntermediateTrendMatrixError(
            "validated authority does not contain the exact five-arm order"
        )
    return dict(validated)


def canonical_tle_file_set_hash(tle_root: Path) -> tuple[str, int]:
    """Hash canonical TLE names and bytes using the repository freeze rule.

    The freeze hash binds ``filename:sha256(file-bytes)`` rows sorted by name.
    Reading bytes directly avoids constructing a simulator or parsing millions
    of records before the subprocesses are launched.
    """

    root = Path(tle_root).expanduser().resolve()
    if not root.is_dir():
        raise IntermediateTrendMatrixError(f"TLE root is not a directory: {root}")
    files = sorted(
        path
        for path in root.iterdir()
        if path.is_file() and TLE_FILE_RE.fullmatch(path.name)
    )
    if not files:
        raise IntermediateTrendMatrixError(f"no canonical TLE files under {root}")
    rows = [f"{path.name}:{sha256_file(path)}" for path in files]
    digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
    return digest, len(files)


def _authority_paths(validated: Mapping[str, Any]) -> tuple[Path, Path]:
    authority = validated.get("authority")
    if not isinstance(authority, Mapping):
        raise IntermediateTrendMatrixError("validated authority paths are missing")
    prereg_raw = authority.get("canonical_prereg")
    corpus_raw = authority.get("c1_exp_corpus_manifest")
    if not isinstance(prereg_raw, str) or not prereg_raw:
        raise IntermediateTrendMatrixError("canonical preregistration path is missing")
    if not isinstance(corpus_raw, str) or not corpus_raw:
        raise IntermediateTrendMatrixError("C1 EXP corpus manifest path is missing")
    prereg = Path(prereg_raw).expanduser().resolve()
    corpus = Path(corpus_raw).expanduser().resolve()
    if not prereg.is_file() or not corpus.is_file():
        raise IntermediateTrendMatrixError(
            "canonical preregistration or C1 EXP corpus manifest is missing"
        )
    return prereg, corpus


def _config(validated: Mapping[str, Any]) -> dict[str, Any]:
    config = validated.get("config")
    seeds = validated.get("seeds")
    if not isinstance(config, Mapping) or not isinstance(seeds, Mapping):
        raise IntermediateTrendMatrixError("validated authority config is incomplete")
    exact = {
        "users": config.get("users"),
        "evaluation_users": config.get("evaluation_users"),
        "epsilon_decay_episodes": config.get("epsilon_decay_episodes"),
        "target_update_every": config.get("target_update_every"),
        "checkpoint_every_episodes": config.get("checkpoint_every_episodes"),
        "specialist_bundle_replay_capacity": config.get(
            "specialist_bundle_replay_capacity"
        ),
        "donor_beta": config.get("donor_beta"),
        "acrm_eta": config.get("acrm_eta"),
        "training_seed": seeds.get("training"),
        "environment_seed": seeds.get("environment"),
        "mobility_seed": seeds.get("mobility"),
        "evaluation_seeds": seeds.get("evaluation_seeds"),
    }
    if exact["users"] != 100:
        raise IntermediateTrendMatrixError("authority users must be exactly 100")
    if exact["epsilon_decay_episodes"] != TREND_EPSILON_DECAY_EPISODES:
        raise IntermediateTrendMatrixError("authority epsilon schedule drifted")
    if exact["target_update_every"] != TREND_TARGET_UPDATE_EVERY:
        raise IntermediateTrendMatrixError("authority target-sync schedule drifted")
    if exact["checkpoint_every_episodes"] != TREND_CHECKPOINT_EVERY_EPISODES:
        raise IntermediateTrendMatrixError("authority checkpoint schedule drifted")
    if (
        exact["specialist_bundle_replay_capacity"]
        != TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY
    ):
        raise IntermediateTrendMatrixError("authority bundle replay capacity drifted")
    if not math.isclose(float(exact["donor_beta"]), 0.25, abs_tol=1e-15, rel_tol=0.0):
        raise IntermediateTrendMatrixError("authority donor beta drifted")
    if not math.isclose(
        float(exact["acrm_eta"]), TREND_ACRM_ETA, abs_tol=1e-15, rel_tol=0.0
    ):
        raise IntermediateTrendMatrixError("authority ACRM eta drifted")
    if not isinstance(exact["evaluation_users"], (list, tuple)):
        raise IntermediateTrendMatrixError("authority evaluation users are missing")
    if not isinstance(exact["evaluation_seeds"], (list, tuple)):
        raise IntermediateTrendMatrixError("authority evaluation seeds are missing")
    if any(type(value) is not int for value in (exact["training_seed"], exact["environment_seed"], exact["mobility_seed"])):
        raise IntermediateTrendMatrixError("authority training seeds must be integers")
    if any(type(value) is not int for value in exact["evaluation_seeds"]):
        raise IntermediateTrendMatrixError("authority evaluation seeds must be integers")
    return exact


def runner_command(
    *,
    authority_path: Path,
    validated: Mapping[str, Any],
    arm: str,
    output_dir: Path,
    tle_root: Path,
    prereg: Path,
    c1_corpus: Path,
) -> list[str]:
    """Build the exact authority-bound command for one arm."""

    config = _config(validated)
    command = [
        sys.executable,
        str(RUNNER),
        "--arm",
        arm,
        "--output-dir",
        str(output_dir),
        "--episodes",
        str(validated["episodes"]),
        "--users",
        str(config["users"]),
        "--train-seed",
        str(config["training_seed"]),
        "--env-seed",
        str(config["environment_seed"]),
        "--mobility-seed",
        str(config["mobility_seed"]),
        "--epsilon-decay-episodes",
        str(TREND_EPSILON_DECAY_EPISODES),
        "--target-update-every",
        str(TREND_TARGET_UPDATE_EVERY),
        "--checkpoint-every",
        str(TREND_CHECKPOINT_EVERY_EPISODES),
        "--learning-rate",
        str(validated["learning_rate"]),
        "--acrm-eta",
        str(TREND_ACRM_ETA),
        "--intermediate-trend-authority",
        str(authority_path),
        "--prereg",
        str(prereg),
        "--tle-root",
        str(tle_root),
    ]
    if arm != "B000":
        command.extend(["--c1-exp-corpus-manifest", str(c1_corpus)])
    return command


def smoke_runner_command(
    *,
    validated: Mapping[str, Any],
    arm: str,
    output_dir: Path,
    tle_root: Path,
    prereg: Path,
    c1_corpus: Path,
) -> list[str]:
    """Build a bounded 10EP command that exercises the same five arm paths."""

    config = _config(validated)
    command = [
        sys.executable,
        str(RUNNER),
        "--arm",
        arm,
        "--output-dir",
        str(output_dir),
        "--episodes",
        str(SMOKE_EPISODES),
        "--users",
        str(config["users"]),
        "--train-seed",
        str(config["training_seed"]),
        "--env-seed",
        str(config["environment_seed"]),
        "--mobility-seed",
        str(config["mobility_seed"]),
        "--epsilon-decay-episodes",
        str(TREND_EPSILON_DECAY_EPISODES),
        "--target-update-every",
        str(TREND_TARGET_UPDATE_EVERY),
        "--checkpoint-every",
        str(TREND_CHECKPOINT_EVERY_EPISODES),
        "--learning-rate",
        str(validated["learning_rate"]),
        "--acrm-eta",
        str(TREND_ACRM_ETA),
        "--prereg",
        str(prereg),
        "--tle-root",
        str(tle_root),
    ]
    if arm != "B000":
        command.extend(
            [
                "--development-route-all",
                "--c1-exp-corpus-manifest",
                str(c1_corpus),
            ]
        )
    return command


def sweep_command(
    *,
    validated: Mapping[str, Any],
    checkpoints: Mapping[str, Path],
    output_dir: Path,
    tle_root: Path,
    prereg: Path,
) -> list[str]:
    """Build the exact held-out Main-only sweep command."""

    config = _config(validated)
    command = [sys.executable, str(SWEEP)]
    for arm in ALLOWED_ARMS:
        command.extend(["--arm", f"{ARM_LABELS[arm]}={checkpoints[arm]}"])
    command.extend(
        [
            "--users",
            *(str(value) for value in config["evaluation_users"]),
            "--seeds",
            *(str(value) for value in config["evaluation_seeds"]),
            "--output-dir",
            str(output_dir),
            "--prereg",
            str(prereg),
            "--tle-root",
            str(tle_root),
        ]
    )
    return command


def _time_v_available() -> bool:
    return TIME_V.is_file() and os.access(TIME_V, os.X_OK)


def timed_command(command: Sequence[str], usage_log: Path) -> tuple[list[str], bool]:
    """Wrap a subprocess with GNU ``time -v`` when available."""

    if not _time_v_available():
        return list(command), False
    return [str(TIME_V), "-v", "-o", str(usage_log), "--", *command], True


def parse_max_rss_kb(path: Path) -> int | None:
    """Extract GNU time's maximum resident set size, if present."""

    if not path.is_file():
        return None
    pattern = re.compile(r"^\s*Maximum resident set size \(kbytes\):\s*(\d+)\s*$")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            return int(match.group(1))
    return None


@dataclass(frozen=True)
class ArmPlan:
    arm: str
    output_dir: Path
    command: tuple[str, ...]
    log_path: Path
    usage_path: Path


@dataclass
class Running:
    plan: ArmPlan
    process: subprocess.Popen[Any]
    stream: Any
    timed: bool
    timed_command: tuple[str, ...]
    started: dt.datetime


def _base_run_receipt(plan: ArmPlan, *, timed: bool, wrapped: Sequence[str]) -> dict[str, Any]:
    return {
        "arm": plan.arm,
        "attempt": 1,
        "status": "running",
        "command": list(plan.command),
        "timed_command": list(wrapped),
        "started_utc": None,
        "ended_utc": None,
        "elapsed_s": None,
        "exit_code": None,
        "log": str(plan.log_path),
        "log_sha256": None,
        "resource_usage_log": str(plan.usage_path) if timed else None,
        "resource_usage_log_sha256": None,
        "maximum_resident_set_size_kb": None,
        "time_v": timed,
    }


def _finish_running(item: Running, receipt: dict[str, Any]) -> dict[str, Any]:
    ended = dt.datetime.now(dt.timezone.utc)
    item.stream.close()
    receipt["ended_utc"] = ended.isoformat()
    started_raw = receipt.get("started_utc")
    if isinstance(started_raw, str):
        started = dt.datetime.fromisoformat(started_raw)
        receipt["elapsed_s"] = (ended - started).total_seconds()
    receipt["exit_code"] = int(item.process.returncode)
    receipt["log_sha256"] = (
        sha256_file(item.plan.log_path) if item.plan.log_path.is_file() else None
    )
    if item.timed:
        receipt["resource_usage_log_sha256"] = (
            sha256_file(item.plan.usage_path)
            if item.plan.usage_path.is_file()
            else None
        )
        receipt["maximum_resident_set_size_kb"] = parse_max_rss_kb(
            item.plan.usage_path
        )
    receipt["status"] = "process_complete"
    return receipt


def _same_float(observed: Any, expected: float) -> bool:
    """Compare a receipt float without turning malformed data into a crash."""

    if isinstance(observed, bool):
        return False
    try:
        value = float(observed)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(value) and math.isclose(
        value, expected, abs_tol=1e-15, rel_tol=0.0
    )


def verify_arm_output(
    *,
    plan: ArmPlan,
    validated: Mapping[str, Any],
    config: Mapping[str, Any],
    expected_tle_hash: str,
    expected_episodes: int | None = None,
    require_periodic: bool = True,
) -> dict[str, Any]:
    """Verify a runner's status contract and final checkpoint digest."""

    failures: list[str] = []
    status_path = plan.output_dir / "status.json"
    checkpoint = plan.output_dir / "final-checkpoint.pt"
    status: Mapping[str, Any] | None = None
    episode_count = (
        int(validated["episodes"])
        if expected_episodes is None
        else int(expected_episodes)
    )
    if not status_path.is_file():
        failures.append("status.json missing")
    else:
        try:
            status = _read_object(status_path, label=f"{plan.arm} status")
        except IntermediateTrendMatrixError as error:
            failures.append(str(error))
    if status is not None:
        if status.get("status") != "complete":
            failures.append("status.status is not complete")
        if status.get("arm") != plan.arm:
            failures.append("status.arm mismatch")
        if status.get("label") != ARM_LABELS[plan.arm]:
            failures.append("status.label mismatch")
        if status.get("episodes") != episode_count:
            failures.append("status.episodes mismatch")
        if status.get("users") != config["users"]:
            failures.append("status.users mismatch")
        seeds = status.get("seeds")
        expected_seeds = {
            "training": config["training_seed"],
            "environment": config["environment_seed"],
            "mobility": config["mobility_seed"],
        }
        if seeds != expected_seeds:
            failures.append("status.seeds mismatch")
        status_config = status.get("config")
        if not isinstance(status_config, Mapping):
            failures.append("status.config missing")
        else:
            expected_config = {
                "episodes": episode_count,
                "learning_rate": validated["learning_rate"],
                "epsilon_decay_episodes": TREND_EPSILON_DECAY_EPISODES,
                "target_update_every_episodes": TREND_TARGET_UPDATE_EVERY,
            }
            for key, expected in expected_config.items():
                observed = status_config.get(key)
                if isinstance(expected, float):
                    if not _same_float(observed, expected):
                        failures.append(f"status.config.{key} mismatch")
                elif observed != expected:
                    failures.append(f"status.config.{key} mismatch")
        checkpointing = status.get("checkpointing")
        if (
            not isinstance(checkpointing, Mapping)
            or checkpointing.get("every_episodes")
            != TREND_CHECKPOINT_EVERY_EPISODES
            or checkpointing.get("specialist_bundle_replay_capacity")
            != TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY
        ):
            failures.append("status.checkpointing.every_episodes mismatch")
        authority = status.get("authority")
        if not isinstance(authority, Mapping) or authority.get("tle_file_set_sha256") != expected_tle_hash:
            failures.append("status.authority.tle_file_set_sha256 mismatch")
        gate = status.get("gate_manifest")
        if not isinstance(gate, Mapping):
            failures.append("status.gate_manifest missing")
        elif require_periodic:
            validated_gate = gate.get("validated")
            if not isinstance(validated_gate, Mapping):
                failures.append("status.gate_manifest.validated missing")
            else:
                gate_config = validated_gate.get("config")
                if not isinstance(gate_config, Mapping) or not _same_float(
                    gate_config.get("acrm_eta"), TREND_ACRM_ETA
                ):
                    failures.append("status gate ACRM eta mismatch")
        elif plan.arm == "B000":
            if gate.get("status") != "absent-fail-closed":
                failures.append("smoke baseline gate status mismatch")
        elif gate.get("status") != "DEVELOPMENT_ONLY_NOT_FORMAL_GATE":
            failures.append("smoke treatment gate status mismatch")
        result = status.get("result")
        if not isinstance(result, Mapping):
            failures.append("status.result missing")
        else:
            if result.get("episodes") != episode_count:
                failures.append("status.result.episodes mismatch")
            raw_checkpoint = result.get("checkpoint")
            try:
                result_checkpoint = Path(str(raw_checkpoint)).expanduser().resolve()
            except (OSError, RuntimeError):
                result_checkpoint = None
            if result_checkpoint != checkpoint.resolve():
                failures.append("status.result.checkpoint mismatch")
            if result.get("checkpoint_sha256") != (
                sha256_file(checkpoint) if checkpoint.is_file() else None
            ):
                failures.append("status.result.checkpoint_sha256 mismatch")
            expected_completed = (
                list(
                    range(
                        TREND_CHECKPOINT_EVERY_EPISODES,
                        episode_count + 1,
                        TREND_CHECKPOINT_EVERY_EPISODES,
                    )
                )
                if require_periodic
                else []
            )
            periodic = result.get("periodic_checkpoints")
            if not isinstance(periodic, list):
                failures.append("status.result.periodic_checkpoints missing")
                periodic = []
            observed_completed: list[int] = []
            for index, row in enumerate(periodic):
                if not isinstance(row, Mapping):
                    failures.append(
                        f"status.result.periodic_checkpoints[{index}] malformed"
                    )
                    continue
                completed = row.get("episodes_completed")
                if type(completed) is not int:
                    failures.append(
                        f"status.result.periodic_checkpoints[{index}].episodes_completed malformed"
                    )
                    continue
                observed_completed.append(completed)
                expected_path = (
                    plan.output_dir
                    / "checkpoints"
                    / f"ep-{completed:06d}-main.pt"
                ).resolve()
                try:
                    observed_path = Path(str(row.get("path"))).expanduser().resolve()
                except (OSError, RuntimeError):
                    observed_path = None
                if observed_path != expected_path or not expected_path.is_file():
                    failures.append(
                        f"periodic checkpoint {completed}: path/file mismatch"
                    )
                    continue
                if row.get("sha256") != sha256_file(expected_path):
                    failures.append(
                        f"periodic checkpoint {completed}: hash mismatch"
                    )
                try:
                    payload = read_checkpoint(expected_path, map_location="cpu")
                except Exception as error:
                    failures.append(
                        f"periodic checkpoint {completed}: reload failed ({type(error).__name__})"
                    )
                else:
                    if payload.episode != completed - 1:
                        failures.append(
                            f"periodic checkpoint {completed}: episode mismatch"
                        )
                    if payload.checkpoint_kind != "periodic-main-policy-trend":
                        failures.append(
                            f"periodic checkpoint {completed}: kind mismatch"
                        )
            if observed_completed != expected_completed:
                failures.append("periodic checkpoint episode sequence mismatch")
            if result.get("periodic_checkpoint_count") != len(expected_completed):
                failures.append("periodic checkpoint count mismatch")
            if result.get("checkpoint_every_episodes") != TREND_CHECKPOINT_EVERY_EPISODES:
                failures.append("result checkpoint cadence mismatch")
            resume = result.get("rolling_resume_state")
            if require_periodic and not isinstance(resume, Mapping):
                failures.append("rolling resume state missing")
            elif require_periodic and isinstance(resume, Mapping):
                raw_resume = resume.get("path")
                try:
                    resume_path = Path(str(raw_resume)).expanduser().resolve()
                except (OSError, RuntimeError):
                    resume_path = None
                if resume.get("episodes_completed") != expected_completed[-1]:
                    failures.append("rolling resume state episode mismatch")
                if resume_path is None or not resume_path.is_file():
                    failures.append("rolling resume state file missing")
                elif resume.get("sha256") != sha256_file(resume_path):
                    failures.append("rolling resume state hash mismatch")
    if not checkpoint.is_file():
        failures.append("final-checkpoint.pt missing")
    elif checkpoint.stat().st_size <= 0:
        failures.append("final-checkpoint.pt is empty")
    checkpoint_sha = sha256_file(checkpoint) if checkpoint.is_file() else None
    return {
        "status": "PASS" if not failures else "FAIL",
        "status_path": str(status_path),
        "status_sha256": sha256_file(status_path) if status_path.is_file() else None,
        "checkpoint_path": str(checkpoint),
        "checkpoint_sha256": checkpoint_sha,
        "failures": failures,
    }


def verify_sweep_output(
    *,
    output_dir: Path,
    validated: Mapping[str, Any],
    expected_tle_hash: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the sweep's data receipts before accepting the matrix."""

    failures: list[str] = []
    summary_path = output_dir / "sweep-summary.json"
    raw_path = output_dir / "sweep-raw.json"
    plot_status_path = output_dir / "plot-status.json"
    summary: Mapping[str, Any] | None = None
    if not summary_path.is_file():
        failures.append("sweep-summary.json missing")
    else:
        try:
            summary = _read_object(summary_path, label="sweep summary")
        except IntermediateTrendMatrixError as error:
            failures.append(str(error))
    if not raw_path.is_file():
        failures.append("sweep-raw.json missing")
    if not plot_status_path.is_file():
        failures.append("plot-status.json missing")
    if summary is not None:
        if summary.get("users") != list(config["evaluation_users"]):
            failures.append("sweep users mismatch")
        if summary.get("evaluation_seeds") != list(config["evaluation_seeds"]):
            failures.append("sweep evaluation seeds mismatch")
        authority = summary.get("authority")
        if not isinstance(authority, Mapping) or authority.get("tle_file_set_sha256") != expected_tle_hash:
            failures.append("sweep authority TLE hash mismatch")
        if summary.get("evaluation_policy") != "Main-only masked-greedy MODQN":
            failures.append("sweep evaluation policy mismatch")
    return {
        "status": "PASS" if not failures else "FAIL",
        "summary_path": str(summary_path),
        "summary_sha256": sha256_file(summary_path) if summary_path.is_file() else None,
        "raw_path": str(raw_path),
        "raw_sha256": sha256_file(raw_path) if raw_path.is_file() else None,
        "plot_status_path": str(plot_status_path),
        "plot_status_sha256": sha256_file(plot_status_path) if plot_status_path.is_file() else None,
        "failures": failures,
    }


def _launch(plan: ArmPlan) -> tuple[Running, dict[str, Any]]:
    wrapped, timed = timed_command(plan.command, plan.usage_path)
    stream = plan.log_path.open("w", encoding="utf-8")
    started = dt.datetime.now(dt.timezone.utc)
    receipt = _base_run_receipt(plan, timed=timed, wrapped=wrapped)
    receipt["started_utc"] = started.isoformat()
    try:
        process = subprocess.Popen(
            wrapped,
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        stream.close()
        raise
    return Running(plan, process, stream, timed, tuple(wrapped), started), receipt


def _collect_arm_runs(
    *,
    plans: Sequence[ArmPlan],
    max_parallel: int,
    validated: Mapping[str, Any],
    config: Mapping[str, Any],
    expected_tle_hash: str,
    expected_episodes: int | None = None,
    require_periodic: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[list[dict[str, Any]], bool]:
    """Run plans dynamically, preserving in-flight work after a failure."""

    pending = list(plans)
    running: list[tuple[Running, dict[str, Any]]] = []
    receipts: dict[str, dict[str, Any]] = {}
    failed = False

    # After the first failure, the pending queue is intentionally excluded
    # from the loop condition; only already-running children are drained.
    while running or (pending and not failed):
        completed_any = False
        for item, receipt in list(running):
            return_code = item.process.poll()
            if return_code is None:
                continue
            item.process.returncode = int(return_code)
            finished = _finish_running(item, receipt)
            verification = verify_arm_output(
                plan=item.plan,
                validated=validated,
                config=config,
                expected_tle_hash=expected_tle_hash,
                expected_episodes=expected_episodes,
                require_periodic=require_periodic,
            )
            finished["verification"] = verification
            if int(return_code) != 0 or verification["status"] != "PASS":
                finished["status"] = "failed"
                failed = True
            else:
                finished["status"] = "PASS"
            receipts[item.plan.arm] = finished
            running.remove((item, receipt))
            completed_any = True

        launched_any = False
        while not failed and pending and len(running) < max_parallel:
            plan = pending.pop(0)
            try:
                item, receipt = _launch(plan)
            except Exception as error:
                now = dt.datetime.now(dt.timezone.utc).isoformat()
                receipts[plan.arm] = {
                    "arm": plan.arm,
                    "attempt": 1,
                    "status": "launch_failed",
                    "command": list(plan.command),
                    "timed_command": None,
                    "started_utc": now,
                    "ended_utc": now,
                    "elapsed_s": 0.0,
                    "exit_code": None,
                    "log": str(plan.log_path),
                    "log_sha256": sha256_file(plan.log_path) if plan.log_path.is_file() else None,
                    "resource_usage_log": str(plan.usage_path),
                    "resource_usage_log_sha256": None,
                    "maximum_resident_set_size_kb": None,
                    "time_v": _time_v_available(),
                    "error": f"{type(error).__name__}: {error}",
                    "verification": {"status": "NOT_RUN", "failures": ["process did not start"]},
                }
                failed = True
                break
            running.append((item, receipt))
            launched_any = True
        if running and not completed_any and not launched_any:
            sleep_fn(0.2)

    for plan in pending:
        receipts[plan.arm] = {
            "arm": plan.arm,
            "attempt": 0,
            "status": "not_started_after_failure",
            "command": list(plan.command),
            "timed_command": None,
            "started_utc": None,
            "ended_utc": None,
            "elapsed_s": None,
            "exit_code": None,
            "log": str(plan.log_path),
            "log_sha256": None,
            "resource_usage_log": str(plan.usage_path),
            "resource_usage_log_sha256": None,
            "maximum_resident_set_size_kb": None,
            "time_v": _time_v_available(),
            "verification": {"status": "NOT_RUN", "failures": ["queued after prior failure"]},
        }
    return [receipts[arm] for arm in ALLOWED_ARMS if arm in receipts], failed


def _execute_sweep(
    *,
    plan: ArmPlan,
    validated: Mapping[str, Any],
    config: Mapping[str, Any],
    expected_tle_hash: str,
) -> tuple[dict[str, Any], bool]:
    try:
        item, receipt = _launch(plan)
    except Exception as error:
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        receipt = {
            "kind": "sweep",
            "status": "launch_failed",
            "attempt": 1,
            "command": list(plan.command),
            "timed_command": None,
            "started_utc": now,
            "ended_utc": now,
            "elapsed_s": 0.0,
            "exit_code": None,
            "log": str(plan.log_path),
            "log_sha256": sha256_file(plan.log_path) if plan.log_path.is_file() else None,
            "resource_usage_log": str(plan.usage_path),
            "resource_usage_log_sha256": None,
            "maximum_resident_set_size_kb": None,
            "time_v": _time_v_available(),
            "error": f"{type(error).__name__}: {error}",
        }
        return receipt, False
    item.process.wait()
    finished = _finish_running(item, receipt)
    verification = verify_sweep_output(
        output_dir=plan.output_dir,
        validated=validated,
        expected_tle_hash=expected_tle_hash,
        config=config,
    )
    finished["verification"] = verification
    success = int(finished["exit_code"]) == 0 and verification["status"] == "PASS"
    finished["status"] = "PASS" if success else "failed"
    return finished, success


def run_matrix(
    *,
    authority_path: Path,
    output_root: Path,
    tle_root: Path,
    max_parallel: int,
    smoke: bool = False,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Validate and run the complete bounded trend matrix."""

    if max_parallel not in (1, 2):
        raise IntermediateTrendMatrixError("max_parallel must be 1 or 2")
    root = Path(output_root).expanduser().resolve()
    if root.exists():
        raise IntermediateTrendMatrixError(
            f"output root must be absent before launch: {root}"
        )
    authority_file = Path(authority_path).expanduser().resolve()
    validated = load_and_validate_authority(authority_file, tle_root=tle_root)
    config = _config(validated)
    prereg, c1_corpus = _authority_paths(validated)
    expected_tle_hash = str(
        validated.get("authority", {}).get("tle_file_set_sha256", "")
    )
    if expected_tle_hash != CANONICAL_TLE_FILE_SET_SHA256:
        raise IntermediateTrendMatrixError("authority TLE file-set hash is not canonical")
    actual_tle_hash, tle_file_count = canonical_tle_file_set_hash(tle_root)
    if actual_tle_hash != expected_tle_hash:
        raise IntermediateTrendMatrixError(
            "supplied TLE root does not match the authority file-set hash"
        )
    tle_root = Path(tle_root).expanduser().resolve()

    # Creation is intentionally delayed until all preflight checks pass.
    root.mkdir(parents=True, exist_ok=False)
    logs = root / "logs"
    logs.mkdir()
    plans: list[ArmPlan] = []
    for index, arm in enumerate(ALLOWED_ARMS, start=1):
        arm_output = root / arm
        plans.append(
            ArmPlan(
                arm=arm,
                output_dir=arm_output,
                command=tuple(
                    smoke_runner_command(
                        validated=validated,
                        arm=arm,
                        output_dir=arm_output,
                        tle_root=tle_root,
                        prereg=prereg,
                        c1_corpus=c1_corpus,
                    )
                    if smoke
                    else runner_command(
                        authority_path=authority_file,
                        validated=validated,
                        arm=arm,
                        output_dir=arm_output,
                        tle_root=tle_root,
                        prereg=prereg,
                        c1_corpus=c1_corpus,
                    )
                ),
                log_path=logs / f"{index:02d}-{arm}.log",
                usage_path=logs / f"{index:02d}-{arm}.time-v.log",
            )
        )
    arm_receipts, arm_failed = _collect_arm_runs(
        plans=plans,
        max_parallel=max_parallel,
        validated=validated,
        config=config,
        expected_tle_hash=expected_tle_hash,
        expected_episodes=SMOKE_EPISODES if smoke else None,
        require_periodic=not smoke,
        sleep_fn=sleep_fn,
    )

    checkpoints: dict[str, Path] = {}
    for row in arm_receipts:
        if row.get("status") != "PASS":
            continue
        verification = row.get("verification")
        if isinstance(verification, Mapping) and verification.get("status") == "PASS":
            checkpoints[str(row["arm"])] = Path(str(verification["checkpoint_path"]))

    sweep_receipt: dict[str, Any] | None = None
    sweep_success = False
    if not arm_failed and tuple(checkpoints) == tuple(ALLOWED_ARMS):
        sweep_output = root / "ee-sweep"
        sweep_plan = ArmPlan(
            arm="EE_SWEEP",
            output_dir=sweep_output,
            command=tuple(
                sweep_command(
                    validated=validated,
                    checkpoints=checkpoints,
                    output_dir=sweep_output,
                    tle_root=tle_root,
                    prereg=prereg,
                )
            ),
            log_path=logs / "20-ee-sweep.log",
            usage_path=logs / "20-ee-sweep.time-v.log",
        )
        sweep_receipt, sweep_success = _execute_sweep(
            plan=sweep_plan,
            validated=validated,
            config=config,
            expected_tle_hash=expected_tle_hash,
        )

    complete = not arm_failed and sweep_success
    execution_episodes = SMOKE_EPISODES if smoke else int(validated["episodes"])
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "complete" if complete else "failed",
        "claim_ceiling": (
            SMOKE_CLAIM_CEILING if smoke else validated["claim_ceiling"]
        ),
        "evidence_ceiling": (
            "Ten-episode engineering smoke only; not LR selection, trend, efficacy, or Chapter 5 evidence."
            if smoke
            else validated["evidence_ceiling"]
        ),
        "authority_manifest": str(authority_file),
        "authority_manifest_sha256": sha256_file(authority_file),
        "episodes": execution_episodes,
        "smoke": bool(smoke),
        "learning_rate": validated["learning_rate"],
        "arms": list(ALLOWED_ARMS),
        "max_parallel": max_parallel,
        "training": {
            "users": config["users"],
            "training_seed": config["training_seed"],
            "environment_seed": config["environment_seed"],
            "mobility_seed": config["mobility_seed"],
            "epsilon_decay_episodes": TREND_EPSILON_DECAY_EPISODES,
            "target_update_every": TREND_TARGET_UPDATE_EVERY,
            "checkpoint_every_episodes": TREND_CHECKPOINT_EVERY_EPISODES,
            "specialist_bundle_replay_capacity": TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
            "acrm_eta": TREND_ACRM_ETA,
            "donor_beta": config["donor_beta"],
        },
        "evaluation": {
            "users": list(config["evaluation_users"]),
            "seeds": list(config["evaluation_seeds"]),
            "policy": "Main-only masked-greedy MODQN",
            "partition": "TEST",
            "ee_aggregation": "ratio-of-sums per training seed, then equal-weight mean",
        },
        "canonical_inputs": {
            "prereg": str(prereg),
            "prereg_sha256": sha256_file(prereg),
            "c1_exp_corpus_manifest": str(c1_corpus),
            "c1_exp_corpus_manifest_sha256": sha256_file(c1_corpus),
            "tle_root": str(tle_root),
            "tle_file_set_sha256": actual_tle_hash,
            "tle_file_count": tle_file_count,
        },
        "arm_runs": arm_receipts,
        "sweep": sweep_receipt,
        "no_retry": True,
        "formal_training_authorized": False,
    }
    _write_json(root / "matrix-receipt.json", receipt)
    if not complete:
        raise IntermediateTrendMatrixError(
            f"intermediate trend matrix failed; receipt: {root / 'matrix-receipt.json'}"
        )
    return receipt


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authority",
        "--intermediate-trend-authority",
        dest="authority",
        type=Path,
        required=True,
        help="one sealed intermediate trend authority JSON",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--max-parallel", type=int, choices=(1, 2), default=1)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run the same five arm paths for 10EP under development-only routing",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        run_matrix(
            authority_path=args.authority,
            output_root=args.output_root,
            tle_root=args.tle_root,
            max_parallel=args.max_parallel,
            smoke=args.smoke,
        )
    except IntermediateTrendMatrixError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(Path(args.output_root).expanduser().resolve() / "matrix-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
