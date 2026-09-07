#!/usr/bin/env python3
"""Queue one matched five-arm C2 V0.3A intermediate-trend matrix."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO / ".scratch" / "smc-er-short-ep", REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_v03a_trend_arm as arm_runner  # noqa: E402
from c2_v03a_trend_authority import ALLOWED_ARMS, CLAIM_CEILING  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-trend-matrix-v1"
ARM_RUNNER = HERE / "c2_v03a_trend_arm.py"
SWEEP_RUNNER = REPO / ".scratch" / "smc-er-short-ep" / "sweep_evaluation.py"
ARM_LABELS = dict(arm_runner.c2_runner.ARM_LABELS)


class V03ATrendMatrixError(RuntimeError):
    """Raised when a matrix cannot launch or close honestly."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def arm_command(
    *,
    authority_path: Path,
    arm: str,
    output_dir: Path,
    tle_root: Path,
    resume_state: Path | None = None,
) -> list[str]:
    command = [
        sys.executable,
        str(ARM_RUNNER),
        "--authority",
        str(Path(authority_path).expanduser().resolve()),
        "--arm",
        arm,
        "--output-dir",
        str(Path(output_dir).expanduser().resolve()),
        "--tle-root",
        str(Path(tle_root).expanduser().resolve()),
    ]
    if resume_state is not None:
        command.extend(
            ["--resume-state", str(Path(resume_state).expanduser().resolve())]
        )
    return command


def sweep_command(
    *,
    validated: Mapping[str, Any],
    authority_path: Path,
    output_root: Path,
    tle_root: Path,
) -> list[str]:
    prereg_raw = Path(str(validated["canonical_prereg"])).expanduser()
    prereg = prereg_raw.resolve() if prereg_raw.is_absolute() else (REPO / prereg_raw).resolve()
    command = [sys.executable, str(SWEEP_RUNNER)]
    for arm in ALLOWED_ARMS:
        checkpoint = Path(output_root).resolve() / "arms" / arm / "final-checkpoint.pt"
        command.extend(["--arm", f"{ARM_LABELS[arm]}={checkpoint}"])
    command.extend(
        [
            "--users",
            *(str(value) for value in validated["evaluation_users"]),
            "--seeds",
            *(str(value) for value in validated["evaluation_seeds"]),
            "--output-dir",
            str((Path(output_root).resolve() / "evaluation").resolve()),
            "--prereg",
            str(prereg),
            "--tle-root",
            str(Path(tle_root).expanduser().resolve()),
        ]
    )
    return command


@dataclass(frozen=True)
class ArmPlan:
    arm: str
    output_dir: Path
    log_path: Path
    command: tuple[str, ...]


@dataclass
class Running:
    plan: ArmPlan
    process: subprocess.Popen[Any]
    stream: Any
    started: dt.datetime


def _read_status(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V03ATrendMatrixError(f"arm status is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise V03ATrendMatrixError(f"arm status is not an object: {path}")
    return value


def verify_arm(plan: ArmPlan, *, planned_episodes: int) -> dict[str, Any]:
    status_path = plan.output_dir / "status.json"
    status = _read_status(status_path)
    failures: list[str] = []
    if status.get("status") != "complete":
        failures.append("status is not complete")
    if status.get("arm") != plan.arm:
        failures.append("arm identity mismatch")
    if status.get("episodes_planned") != planned_episodes:
        failures.append("planned episode count mismatch")
    if status.get("formal_training_authorized") is not False:
        failures.append("intermediate arm silently claimed formal authorization")
    result = status.get("result")
    if not isinstance(result, Mapping):
        failures.append("result missing")
        result = {}
    checkpoint = plan.output_dir / "final-checkpoint.pt"
    if not checkpoint.is_file():
        failures.append("final checkpoint missing")
    observed_sha = sha256_file(checkpoint) if checkpoint.is_file() else None
    if result.get("checkpoint_sha256") != observed_sha:
        failures.append("final checkpoint SHA mismatch")
    start_episode = result.get("start_episode", 0)
    if type(start_episode) is not int or not 0 <= start_episode < planned_episodes:
        failures.append("start episode is invalid")
        start_episode = 0
    episodes_completed = result.get("episodes_completed", result.get("episodes"))
    if episodes_completed != planned_episodes:
        failures.append("arm did not reach the planned episode boundary")
    checkpoint_every = result.get("checkpoint_every_episodes")
    if checkpoint_every != 100:
        failures.append("formal checkpoint cadence drifted from 100 episodes")
        checkpoint_every = 100
    expected_periodic = sum(
        episode % checkpoint_every == 0
        for episode in range(start_episode + 1, planned_episodes + 1)
    )
    if result.get("periodic_checkpoint_count") != expected_periodic:
        failures.append("100EP periodic checkpoint count mismatch")
    telemetry = result.get("telemetry")
    c2 = telemetry.get("c2") if isinstance(telemetry, Mapping) else None
    outcomes = c2.get("candidate_outcomes") if isinstance(c2, Mapping) else None
    contract_errors = (
        outcomes.get("contract_error") if isinstance(outcomes, Mapping) else None
    )
    if contract_errors != 0:
        failures.append("C2 runtime contract errors are nonzero or missing")
    mechanism = result.get("mechanism_authority")
    mechanism_sha = (
        mechanism.get("environment_source_sha256")
        if isinstance(mechanism, Mapping)
        else None
    )
    if not isinstance(mechanism_sha, str) or len(mechanism_sha) != 64:
        failures.append("mechanism environment-source authority is missing")
    if plan.arm != "B000":
        prefill = result.get("c1_prefill")
        if not isinstance(prefill, Mapping) or prefill.get("enters_main") is not False:
            failures.append("verified C1 EXP prefill receipt missing")
    return {
        "arm": plan.arm,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "status_path": str(status_path),
        "status_sha256": sha256_file(status_path),
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": observed_sha,
        "periodic_checkpoint_count": result.get("periodic_checkpoint_count"),
        "start_episode": start_episode,
        "episodes_completed": episodes_completed,
        "c2_contract_errors": contract_errors,
        "mechanism_environment_source_sha256": mechanism_sha,
    }


def execute_matrix(
    *,
    authority_path: Path,
    output_root: Path,
    tle_root: Path,
    max_parallel: int,
    resume_states: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    if type(max_parallel) is not int or not 1 <= max_parallel <= len(ALLOWED_ARMS):
        raise V03ATrendMatrixError("max_parallel must be in 1..5")
    authority_path = Path(authority_path).expanduser().resolve()
    output_root = Path(output_root).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite matrix output: {output_root}")
    validated = arm_runner.load_and_validate_authority(
        authority_path, tle_root=tle_root
    )
    resume_states = dict(resume_states or {})
    unknown_resume_arms = set(resume_states) - set(ALLOWED_ARMS)
    if unknown_resume_arms or "B000" in resume_states:
        raise V03ATrendMatrixError(
            "resume states must name treatment arms from the exact five-arm matrix"
        )
    output_root.mkdir(parents=True, exist_ok=False)
    plans = [
        ArmPlan(
            arm=arm,
            output_dir=output_root / "arms" / arm,
            log_path=output_root / "logs" / f"{arm}.log",
            command=tuple(
                arm_command(
                    authority_path=authority_path,
                    arm=arm,
                    output_dir=output_root / "arms" / arm,
                    tle_root=tle_root,
                    resume_state=resume_states.get(arm),
                )
            ),
        )
        for arm in ALLOWED_ARMS
    ]
    (output_root / "logs").mkdir(parents=True, exist_ok=True)
    receipts: dict[str, dict[str, Any]] = {}
    pending = list(plans)
    running: dict[str, Running] = {}
    launch_failed = False

    while pending or running:
        while pending and len(running) < max_parallel and not launch_failed:
            plan = pending.pop(0)
            stream = plan.log_path.open("w", encoding="utf-8")
            started = dt.datetime.now(dt.timezone.utc)
            try:
                process = subprocess.Popen(
                    list(plan.command),
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except BaseException:
                stream.close()
                raise
            running[plan.arm] = Running(plan, process, stream, started)
            receipts[plan.arm] = {
                "arm": plan.arm,
                "status": "running",
                "command": list(plan.command),
                "started_utc": started.isoformat(),
                "ended_utc": None,
                "exit_code": None,
                "log": str(plan.log_path),
            }
            _write_json(
                output_root / "matrix-status.json",
                {
                    "schema": SCHEMA,
                    "status": "running",
                    "authority": str(authority_path),
                    "runs": receipts,
                    "claim_ceiling": CLAIM_CEILING,
                },
            )
        if not running:
            break
        time.sleep(1.0)
        for arm, item in list(running.items()):
            code = item.process.poll()
            if code is None:
                continue
            item.stream.close()
            ended = dt.datetime.now(dt.timezone.utc)
            receipt = receipts[arm]
            receipt.update(
                {
                    "status": "process_complete" if code == 0 else "process_failed",
                    "ended_utc": ended.isoformat(),
                    "elapsed_s": (ended - item.started).total_seconds(),
                    "exit_code": int(code),
                    "log_sha256": sha256_file(item.plan.log_path),
                }
            )
            if code != 0:
                launch_failed = True
            del running[arm]

    if pending:
        for plan in pending:
            receipts[plan.arm] = {
                "arm": plan.arm,
                "status": "not_started_after_failure",
                "command": list(plan.command),
            }
    verifications: dict[str, Any] = {}
    for plan in plans:
        if receipts.get(plan.arm, {}).get("exit_code") == 0:
            verifications[plan.arm] = verify_arm(
                plan, planned_episodes=int(validated["episodes"])
            )
    mechanism_hashes = {
        row.get("mechanism_environment_source_sha256")
        for row in verifications.values()
        if row.get("status") == "PASS"
    }
    mechanism_consistency = {
        "status": "PASS" if len(mechanism_hashes) == 1 else "FAIL",
        "observed_environment_source_sha256": sorted(
            value for value in mechanism_hashes if isinstance(value, str)
        ),
    }
    training_pass = (
        len(verifications) == len(ALLOWED_ARMS)
        and all(row["status"] == "PASS" for row in verifications.values())
        and mechanism_consistency["status"] == "PASS"
    )
    sweep_receipt: dict[str, Any] | None = None
    if training_pass:
        command = sweep_command(
            validated=validated,
            authority_path=authority_path,
            output_root=output_root,
            tle_root=tle_root,
        )
        log = output_root / "logs" / "main-only-sweep.log"
        started = dt.datetime.now(dt.timezone.utc)
        with log.open("w", encoding="utf-8") as stream:
            completed = subprocess.run(
                command,
                stdout=stream,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        ended = dt.datetime.now(dt.timezone.utc)
        summary = output_root / "evaluation" / "sweep-summary.json"
        sweep_receipt = {
            "command": command,
            "exit_code": int(completed.returncode),
            "elapsed_s": (ended - started).total_seconds(),
            "log": str(log),
            "log_sha256": sha256_file(log),
            "summary": str(summary),
            "summary_sha256": sha256_file(summary) if summary.is_file() else None,
        }
    complete = training_pass and sweep_receipt is not None and sweep_receipt["exit_code"] == 0
    matrix = {
        "schema": SCHEMA,
        "status": "complete" if complete else "failed",
        "authority": str(authority_path),
        "authority_sha256": sha256_file(authority_path),
        "learning_rate": float(validated["learning_rate"]),
        "episodes": int(validated["episodes"]),
        "max_parallel": max_parallel,
        "runs": receipts,
        "verifications": verifications,
        "mechanism_consistency": mechanism_consistency,
        "main_only_sweep": sweep_receipt,
        "formal_training_authorized": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    _write_json(output_root / "matrix-status.json", matrix)
    return matrix


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--max-parallel", type=int, default=2)
    parser.add_argument(
        "--resume-arm",
        action="append",
        default=[],
        metavar="ARM=STATE",
        help="resume one treatment arm into this fresh matrix output root",
    )
    return parser.parse_args(argv)


def _resume_states(values: Sequence[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        arm, separator, raw = value.partition("=")
        if not separator or arm not in ALLOWED_ARMS or not raw or arm in parsed:
            raise V03ATrendMatrixError(
                "--resume-arm must be a unique treatment ARM=STATE binding"
            )
        if arm == "B000":
            raise V03ATrendMatrixError("B000 cannot use the C2 resume seam")
        parsed[arm] = Path(raw).expanduser().resolve()
    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    result = execute_matrix(
        authority_path=args.authority,
        output_root=args.output_root,
        tle_root=args.tle_root,
        max_parallel=args.max_parallel,
        resume_states=_resume_states(args.resume_arm),
    )
    print(Path(args.output_root).expanduser().resolve() / "matrix-status.json")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
