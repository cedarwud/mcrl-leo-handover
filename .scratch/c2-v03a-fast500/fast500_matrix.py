#!/usr/bin/env python3
"""Complete a matched 2-LR x 5-arm EP500 preliminary ablation grid.

Historical EP500 checkpoints are snapshotted with before/copy/after hashes.
Missing treatment prefixes are produced by ``fast500_prefix_arm.py`` with at
most two concurrent CPU workers.  Only after all ten checkpoints validate are
the two held-out Main-only EE sweeps launched.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TREND_DIR = REPO / ".scratch" / "c2-v03a-trend"
SHORT_DIR = REPO / ".scratch" / "smc-er-short-ep"
for path in (HERE, TREND_DIR, SHORT_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import fast500_prefix_arm as prefix_arm  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-fast500-matrix-v1"
CLAIM_CEILING = prefix_arm.CLAIM_CEILING
RUNNER = HERE / "fast500_prefix_arm.py"
SWEEP_RUNNER = SHORT_DIR / "sweep_evaluation.py"
LR_KEYS = ("0.001", "0.01")
LR_DIRS = {"0.001": "lr0p001", "0.01": "lr0p01"}
ALL_ARMS = ("B000", "F111", "A011", "A101", "A110")
TRAIN_ARMS = prefix_arm.ALLOWED_ARMS
ARM_LABELS = dict(prefix_arm.trend_arm.c2_runner.ARM_LABELS)


class Fast500MatrixError(RuntimeError):
    """Raised when the preliminary grid cannot be completed exactly."""


@dataclass(frozen=True)
class Plan:
    lr: str
    arm: str
    output_dir: Path
    log_path: Path
    command: tuple[str, ...]


@dataclass
class Running:
    plan: Plan
    process: subprocess.Popen[Any]
    stream: Any
    started: dt.datetime


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _parse_reuse(values: Sequence[str]) -> dict[tuple[str, str], Path]:
    parsed: dict[tuple[str, str], Path] = {}
    for value in values:
        identity, separator, raw_path = value.partition("=")
        lr, colon, arm = identity.partition(":")
        key = (lr, arm)
        if (
            not separator
            or not colon
            or lr not in LR_KEYS
            or arm not in TRAIN_ARMS
            or not raw_path
            or key in parsed
        ):
            raise Fast500MatrixError(
                "--reuse-prefix must be a unique LR:ARM=/path binding"
            )
        parsed[key] = Path(raw_path).expanduser().resolve()
    return parsed


def _stable_snapshot(source: Path, destination: Path) -> str:
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise Fast500MatrixError(f"source EP500 checkpoint is missing: {source}")
    before = prefix_arm.sha256_file(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite snapshot: {destination}")
    shutil.copyfile(source, destination)
    copied = prefix_arm.sha256_file(destination)
    after = prefix_arm.sha256_file(source)
    if before != copied or copied != after:
        raise Fast500MatrixError(f"source changed while snapshotting: {source}")
    return copied


def _trainer_config(validated: Mapping[str, Any], prereg: Any, *, arm: str) -> Any:
    return prefix_arm.trend_arm.legacy._short_config(
        prereg,
        arm=arm,
        episodes=prefix_arm.SOURCE_EPISODES,
        epsilon_decay_episodes=int(validated["epsilon_decay_episodes"]),
        target_update_every=int(validated["target_update_every"]),
        learning_rate=float(validated["learning_rate"]),
    )


def _validate_snapshot(
    *, path: Path, validated: Mapping[str, Any], prereg: Any, arm: str, label: str
) -> dict[str, Any]:
    trainer_config = _trainer_config(validated, prereg, arm=arm)
    canonical = prefix_arm.trend_arm.c2_runner._canonical_trainer_config(
        trainer_config, field="trainer_config"
    )
    payload = prefix_arm.trend_arm.legacy.read_checkpoint(path, map_location="cpu")
    return prefix_arm.checkpoint_tools.validate_checkpoint_payload(
        payload,
        validated=validated,
        trainer_config=canonical,
        episode_index=prefix_arm.PREFIX_EPISODES - 1,
        checkpoint_kind="periodic-main-policy-trend",
        label=label,
    )


def _source_checkpoint(source_root: Path, arm: str) -> Path:
    return (
        Path(source_root).expanduser().resolve()
        / "arms"
        / arm
        / "checkpoints"
        / "ep-000500-main.pt"
    )


def execute_matrix(
    *,
    authorities: Mapping[str, Path],
    authority_shas: Mapping[str, str],
    source_roots: Mapping[str, Path],
    output_root: Path,
    tle_root: Path,
    expected_runner_sha256: str,
    max_parallel: int,
    reuse_prefixes: Mapping[tuple[str, str], Path] | None = None,
) -> dict[str, Any]:
    if type(max_parallel) is not int or not 1 <= max_parallel <= 2:
        raise Fast500MatrixError("max_parallel must be 1 or 2")
    if set(authorities) != set(LR_KEYS) or set(authority_shas) != set(LR_KEYS):
        raise Fast500MatrixError("both exact LR authorities and SHAs are required")
    if set(source_roots) != set(LR_KEYS):
        raise Fast500MatrixError("both exact source roots are required")
    if prefix_arm.sha256_file(RUNNER) != expected_runner_sha256:
        raise Fast500MatrixError("fast500 prefix runner SHA drifted")
    output_root = Path(output_root).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    if output_root.exists():
        raise FileExistsError(f"refusing to overwrite matrix output: {output_root}")
    output_root.mkdir(parents=True, exist_ok=False)
    (output_root / "logs").mkdir()

    validated_by_lr: dict[str, dict[str, Any]] = {}
    prereg_by_lr: dict[str, Any] = {}
    for lr in LR_KEYS:
        authority_path = Path(authorities[lr]).expanduser().resolve()
        expected_sha = authority_shas[lr]
        if prefix_arm.sha256_file(authority_path) != expected_sha:
            raise Fast500MatrixError(f"lr={lr} source authority SHA drifted")
        validated, prereg, _archive, _manifest = prefix_arm._canonical_inputs(
            authority_path=authority_path, tle_root=tle_root
        )
        if float(validated["learning_rate"]) != float(lr):
            raise Fast500MatrixError(f"lr={lr} authority identity drifted")
        validated_by_lr[lr] = validated
        prereg_by_lr[lr] = prereg

    reuse_prefixes = dict(reuse_prefixes or {})
    unknown_reuse = set(reuse_prefixes) - {
        (lr, arm) for lr in LR_KEYS for arm in TRAIN_ARMS
    }
    if unknown_reuse:
        raise Fast500MatrixError("reuse prefix grid contains unknown cells")

    snapshot_receipts: dict[str, dict[str, Any]] = {}
    for lr in LR_KEYS:
        for arm in ("B000", "F111"):
            source = _source_checkpoint(source_roots[lr], arm)
            destination = output_root / "snapshots" / LR_DIRS[lr] / f"{arm}.pt"
            digest = _stable_snapshot(source, destination)
            identity = _validate_snapshot(
                path=destination,
                validated=validated_by_lr[lr],
                prereg=prereg_by_lr[lr],
                arm=arm,
                label=f"lr={lr} {arm} historical EP500",
            )
            snapshot_receipts[f"{lr}:{arm}"] = {
                "source": str(source),
                "snapshot": str(destination),
                "sha256": digest,
                "provenance": "historical_1500_schedule_ep500",
                "checkpoint_identity": identity,
            }
    for (lr, arm), source in sorted(reuse_prefixes.items()):
        destination = output_root / "snapshots" / LR_DIRS[lr] / f"{arm}.pt"
        digest = _stable_snapshot(source, destination)
        identity = _validate_snapshot(
            path=destination,
            validated=validated_by_lr[lr],
            prereg=prereg_by_lr[lr],
            arm=arm,
            label=f"lr={lr} {arm} reused EP500",
        )
        snapshot_receipts[f"{lr}:{arm}"] = {
            "source": str(source),
            "snapshot": str(destination),
            "sha256": digest,
            "provenance": "reused_1500_schedule_ep500",
            "checkpoint_identity": identity,
        }

    plans: list[Plan] = []
    for arm in TRAIN_ARMS:
        for lr in LR_KEYS:
            if (lr, arm) in reuse_prefixes:
                continue
            authority_path = Path(authorities[lr]).expanduser().resolve()
            arm_output = output_root / "training" / LR_DIRS[lr] / arm
            log_path = output_root / "logs" / f"{LR_DIRS[lr]}-{arm}.log"
            command = (
                sys.executable,
                str(RUNNER),
                "--authority",
                str(authority_path),
                "--expected-authority-sha256",
                authority_shas[lr],
                "--expected-runner-sha256",
                expected_runner_sha256,
                "--arm",
                arm,
                "--output-dir",
                str(arm_output),
                "--tle-root",
                str(tle_root),
            )
            plans.append(Plan(lr, arm, arm_output, log_path, command))

    receipts: dict[str, dict[str, Any]] = {}
    pending = list(plans)
    running: dict[str, Running] = {}
    launch_failed = False
    while pending or running:
        while pending and len(running) < max_parallel and not launch_failed:
            plan = pending.pop(0)
            plan.log_path.parent.mkdir(parents=True, exist_ok=True)
            stream = plan.log_path.open("w", encoding="utf-8")
            started = dt.datetime.now(dt.timezone.utc)
            process = subprocess.Popen(
                list(plan.command),
                cwd=REPO,
                stdout=stream,
                stderr=subprocess.STDOUT,
                text=True,
            )
            key = f"{plan.lr}:{plan.arm}"
            running[key] = Running(plan, process, stream, started)
            receipts[key] = {
                "status": "running",
                "command": list(plan.command),
                "started_utc": started.isoformat(),
                "pid": int(process.pid),
            }
            _write_json(
                output_root / "matrix-status.json",
                {
                    "schema": SCHEMA,
                    "status": "training",
                    "runs": receipts,
                    "snapshots": snapshot_receipts,
                    "claim_ceiling": CLAIM_CEILING,
                },
            )
        if not running:
            break
        time.sleep(2.0)
        for key, item in list(running.items()):
            code = item.process.poll()
            if code is None:
                continue
            item.stream.close()
            ended = dt.datetime.now(dt.timezone.utc)
            status_path = item.plan.output_dir / "prefix-status.json"
            receipts[key].update(
                {
                    "status": "complete" if code == 0 else "failed",
                    "exit_code": int(code),
                    "ended_utc": ended.isoformat(),
                    "elapsed_s": (ended - item.started).total_seconds(),
                    "log": str(item.plan.log_path),
                    "log_sha256": prefix_arm.sha256_file(item.plan.log_path),
                    "prefix_status": str(status_path),
                    "prefix_status_sha256": (
                        prefix_arm.sha256_file(status_path)
                        if status_path.is_file()
                        else None
                    ),
                }
            )
            if code != 0:
                launch_failed = True
            del running[key]

    if pending:
        for plan in pending:
            receipts[f"{plan.lr}:{plan.arm}"] = {"status": "not_started_after_failure"}
    if launch_failed or any(row.get("status") != "complete" for row in receipts.values()):
        matrix = {
            "schema": SCHEMA,
            "status": "failed",
            "runs": receipts,
            "snapshots": snapshot_receipts,
            "claim_ceiling": CLAIM_CEILING,
        }
        _write_json(output_root / "matrix-status.json", matrix)
        return matrix

    for plan in plans:
        source = plan.output_dir / "checkpoints" / "ep-000500-main.pt"
        destination = output_root / "snapshots" / LR_DIRS[plan.lr] / f"{plan.arm}.pt"
        digest = _stable_snapshot(source, destination)
        identity = _validate_snapshot(
            path=destination,
            validated=validated_by_lr[plan.lr],
            prereg=prereg_by_lr[plan.lr],
            arm=plan.arm,
            label=f"lr={plan.lr} {plan.arm} new EP500",
        )
        snapshot_receipts[f"{plan.lr}:{plan.arm}"] = {
            "source": str(source),
            "snapshot": str(destination),
            "sha256": digest,
            "provenance": "clean_fast500_prefix_stop",
            "checkpoint_identity": identity,
        }
    expected_grid = {f"{lr}:{arm}" for lr in LR_KEYS for arm in ALL_ARMS}
    if set(snapshot_receipts) != expected_grid:
        raise Fast500MatrixError("snapshot grid is incomplete")

    evaluation_receipts: dict[str, dict[str, Any]] = {}
    evaluation_processes: dict[str, Running] = {}
    for lr in LR_KEYS:
        output = output_root / "evaluation" / LR_DIRS[lr]
        log = output_root / "logs" / f"{LR_DIRS[lr]}-evaluation.log"
        command = [sys.executable, str(SWEEP_RUNNER)]
        for arm in ALL_ARMS:
            checkpoint = output_root / "snapshots" / LR_DIRS[lr] / f"{arm}.pt"
            command.extend(["--arm", f"{ARM_LABELS[arm]}={checkpoint}"])
        validated = validated_by_lr[lr]
        prereg_raw = Path(str(validated["canonical_prereg"])).expanduser()
        prereg_path = prereg_raw.resolve() if prereg_raw.is_absolute() else (REPO / prereg_raw).resolve()
        command.extend(
            [
                "--users",
                *(str(value) for value in validated["evaluation_users"]),
                "--seeds",
                *(str(value) for value in validated["evaluation_seeds"]),
                "--tle-root",
                str(tle_root),
                "--prereg",
                str(prereg_path),
                "--output-dir",
                str(output),
            ]
        )
        stream = log.open("w", encoding="utf-8")
        started = dt.datetime.now(dt.timezone.utc)
        process = subprocess.Popen(
            command,
            cwd=REPO,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
        )
        plan = Plan(lr, "EVAL", output, log, tuple(command))
        evaluation_processes[lr] = Running(plan, process, stream, started)
        evaluation_receipts[lr] = {
            "status": "running",
            "command": command,
            "pid": int(process.pid),
            "started_utc": started.isoformat(),
        }
    for lr, item in evaluation_processes.items():
        code = item.process.wait()
        item.stream.close()
        ended = dt.datetime.now(dt.timezone.utc)
        summary = item.plan.output_dir / "sweep-summary.json"
        evaluation_receipts[lr].update(
            {
                "status": "complete" if code == 0 and summary.is_file() else "failed",
                "exit_code": int(code),
                "ended_utc": ended.isoformat(),
                "elapsed_s": (ended - item.started).total_seconds(),
                "log": str(item.plan.log_path),
                "log_sha256": prefix_arm.sha256_file(item.plan.log_path),
                "summary": str(summary),
                "summary_sha256": prefix_arm.sha256_file(summary) if summary.is_file() else None,
            }
        )
    complete = all(row.get("status") == "complete" for row in evaluation_receipts.values())
    matrix = {
        "schema": SCHEMA,
        "status": "complete" if complete else "failed",
        "claim_ceiling": CLAIM_CEILING,
        "formal_training_authorized": False,
        "source_schedule_episodes": prefix_arm.SOURCE_EPISODES,
        "evaluated_prefix_episodes": prefix_arm.PREFIX_EPISODES,
        "learning_rates": list(LR_KEYS),
        "arms": list(ALL_ARMS),
        "max_parallel_training": max_parallel,
        "runs": receipts,
        "snapshots": snapshot_receipts,
        "evaluations": evaluation_receipts,
    }
    _write_json(output_root / "matrix-status.json", matrix)
    return matrix


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-lr0p001", type=Path, required=True)
    parser.add_argument("--authority-sha-lr0p001", required=True)
    parser.add_argument("--source-root-lr0p001", type=Path, required=True)
    parser.add_argument("--authority-lr0p01", type=Path, required=True)
    parser.add_argument("--authority-sha-lr0p01", required=True)
    parser.add_argument("--source-root-lr0p01", type=Path, required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--max-parallel", type=int, default=2)
    parser.add_argument("--reuse-prefix", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    result = execute_matrix(
        authorities={"0.001": args.authority_lr0p001, "0.01": args.authority_lr0p01},
        authority_shas={
            "0.001": args.authority_sha_lr0p001,
            "0.01": args.authority_sha_lr0p01,
        },
        source_roots={
            "0.001": args.source_root_lr0p001,
            "0.01": args.source_root_lr0p01,
        },
        output_root=args.output_root,
        tle_root=args.tle_root,
        expected_runner_sha256=args.expected_runner_sha256,
        max_parallel=args.max_parallel,
        reuse_prefixes=_parse_reuse(args.reuse_prefix),
    )
    print(Path(args.output_root).expanduser().resolve() / "matrix-status.json")
    return 0 if result.get("status") == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
