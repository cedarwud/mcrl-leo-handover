#!/usr/bin/env python3
"""Fail-closed Ubuntu source/runtime gate for R7 source-prefix evaluation."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO / "src"):
    if str(path) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(path))

import r7_500_authority as authority  # noqa: E402
import r7_500_prefix_bridge as bridge  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-evaluation-gate-v3"


class R7500ServerPreflightError(RuntimeError):
    """Raised when the current host cannot safely run an R7 evaluation."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise R7500ServerPreflightError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise R7500ServerPreflightError(f"{label} must be a JSON object")
    return value


def _available_memory_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise R7500ServerPreflightError("MemAvailable is missing from /proc/meminfo")


SOURCE_RUNNER_NAMES = {
    "c2_v03a_trend_matrix.py",
    "c2_v03a_trend_arm.py",
    "c2_v03a_trend_matrix",
    "c2_v03a_trend_arm",
}
R7_EVALUATOR_NAMES = {
    "r7_500_evaluate.py",
    "r7_500_ablation_evaluate.py",
    "r7_500_evaluate",
    "r7_500_ablation_evaluate",
}
PROCESS_PATH_FLAGS = {
    "--authority",
    "--output-root",
    "--output-dir",
    "--bridge-receipt",
    "--reconciliation-receipt",
    "--selection-receipt",
}


def _process_cmdlines() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for child in Path("/proc").iterdir():
        if not child.name.isdigit() or int(child.name) == os.getpid():
            continue
        try:
            raw = (child / "cmdline").read_bytes()
        except OSError:
            continue
        if raw:
            argv = [
                token.decode("utf-8", "replace")
                for token in raw.split(b"\0")
                if token
            ]
            try:
                cwd = str((child / "cwd").resolve(strict=True))
            except OSError:
                cwd = None
            rows.append({"pid": int(child.name), "argv": argv, "cwd": cwd})
    return rows


def _normalize_process_record(value: Any) -> tuple[int, list[str], Path | None]:
    if isinstance(value, Mapping):
        pid = value.get("pid")
        argv = value.get("argv")
        cwd_value = value.get("cwd")
        if type(pid) is not int or not isinstance(argv, Sequence) or isinstance(argv, str):
            raise R7500ServerPreflightError("process record is malformed")
        if any(not isinstance(token, str) for token in argv):
            raise R7500ServerPreflightError("process argv record is malformed")
        cwd = Path(cwd_value).resolve() if isinstance(cwd_value, str) else None
        return pid, list(argv), cwd
    if isinstance(value, tuple) and len(value) in (2, 3) and type(value[0]) is int:
        command = value[1]
        argv = shlex.split(command) if isinstance(command, str) else list(command)
        cwd = Path(value[2]).resolve() if len(value) == 3 and value[2] is not None else None
        return value[0], argv, cwd
    raise R7500ServerPreflightError("process record is malformed")


def _resolved_process_paths(argv: Sequence[str], cwd: Path | None) -> list[Path]:
    paths: list[Path] = []
    for index, token in enumerate(argv[:-1]):
        if token not in PROCESS_PATH_FLAGS:
            continue
        candidate = Path(argv[index + 1]).expanduser()
        if not candidate.is_absolute():
            if cwd is None:
                continue
            candidate = cwd / candidate
        paths.append(candidate.resolve())
    return paths


def assess_resource_state(
    *,
    resource_policy: Mapping[str, Any],
    source_matrix_roots: Sequence[Path],
    logical_cpus: int,
    available_memory_bytes: int,
    kernel_text: str,
    process_cmdlines: Sequence[Any],
) -> dict[str, Any]:
    failures: list[str] = []
    if "microsoft" in kernel_text.lower():
        failures.append("WSL is not the authorized Ubuntu server host role")
    if logical_cpus < int(resource_policy["minimum_logical_cpus"]):
        failures.append("logical CPU capacity is below the frozen minimum")
    if available_memory_bytes < int(resource_policy["minimum_available_memory_bytes"]):
        failures.append("available memory is below the frozen minimum")
    active: list[dict[str, Any]] = []
    source_roots = [Path(path).resolve() for path in source_matrix_roots]
    for record in process_cmdlines:
        pid, argv, cwd = _normalize_process_record(record)
        names = {Path(token).name.lower() for token in argv}
        known_runner = bool(names & (SOURCE_RUNNER_NAMES | R7_EVALUATOR_NAMES))
        relevant_path = any(
            any(path == root or path.is_relative_to(root) for root in source_roots)
            for path in _resolved_process_paths(argv, cwd)
        )
        if known_runner or relevant_path:
            active.append(
                {
                    "pid": int(pid),
                    "argv": list(argv),
                    "cwd": str(cwd) if cwd is not None else None,
                    "command": shlex.join(argv),
                }
            )
    if active:
        failures.append("source or R7 evaluation process is still active")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "logical_cpus": int(logical_cpus),
        "available_memory_bytes": int(available_memory_bytes),
        "active_training_processes": active,
    }


def assert_source_matrices_complete(
    *, validated: Mapping[str, Any], repo: Path
) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for lr_key, relative in validated["source_matrix_paths"].items():
        path = (repo / relative / "matrix-status.json").resolve()
        matrix = _read_object(path, label=f"source matrix {lr_key}")
        base = validated["validated_base_authorities"][lr_key]
        runs = matrix.get("runs")
        verifications = matrix.get("verifications")
        expected_arms = list(base["arms"])
        if (
            matrix.get("schema") != bridge.MATRIX_SCHEMA
            or matrix.get("status") != "complete"
            or matrix.get("episodes") != 1500
            or matrix.get("learning_rate") != float(lr_key)
            or matrix.get("authority_sha256") != base["authority_sha256"]
            or not isinstance(runs, Mapping)
            or set(runs) != set(expected_arms)
            or not isinstance(verifications, Mapping)
            or set(verifications) != set(expected_arms)
        ):
            raise R7500ServerPreflightError(
                f"source matrix {lr_key} has not reached exact complete state"
            )
        for arm in expected_arms:
            run = runs[arm]
            verification = verifications[arm]
            if (
                not isinstance(run, Mapping)
                or run.get("status") != "process_complete"
                or run.get("exit_code") != 0
                or not isinstance(verification, Mapping)
                or verification.get("status") != "PASS"
                or verification.get("episodes_completed") != 1500
            ):
                raise R7500ServerPreflightError(
                    f"source matrix {lr_key} arm {arm} is not verified complete"
                )
        receipts.append(
            {
                "learning_rate": float(lr_key),
                "path": str(path),
                "sha256": authority.sha256_file(path),
                "status": "complete",
                "verified_arm_count": len(expected_arms),
            }
        )
    return receipts


def current_host_identity() -> dict[str, str]:
    return {
        "hostname": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }


def current_runtime_identity() -> dict[str, Any]:
    packages: dict[str, str] = {}
    for name in sorted(authority.RUNTIME_PACKAGES):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise R7500ServerPreflightError(
                f"required runtime package is missing: {name}"
            ) from error
    return {"python": platform.python_version(), "packages": packages}


def live_resource_assessment(
    *, validated: Mapping[str, Any], repo: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_receipts = assert_source_matrices_complete(validated=validated, repo=repo)
    kernel_text = " ".join(
        (
            platform.system(),
            platform.release(),
            Path("/proc/version").read_text(encoding="utf-8"),
        )
    )
    assessment = assess_resource_state(
        resource_policy=validated["resource_policy"],
        source_matrix_roots=[repo / value for value in validated["source_matrix_paths"].values()],
        logical_cpus=os.cpu_count() or 0,
        available_memory_bytes=_available_memory_bytes(),
        kernel_text=kernel_text,
        process_cmdlines=_process_cmdlines(),
    )
    if platform.node() != validated["resource_policy"]["authorized_hostname"]:
        assessment["failures"].append("host is not the frozen Ubuntu server")
        assessment["status"] = "FAIL"
    runtime = current_runtime_identity()
    if (
        runtime["python"] != validated["runtime_python_version"]
        or runtime["packages"] != validated["runtime_packages"]
    ):
        assessment["failures"].append("runtime Python/package identity drifted")
        assessment["status"] = "FAIL"
    assessment["runtime"] = runtime
    return assessment, source_receipts


def assert_evaluation_ready(
    *, authority_path: Path, tle_root: Path, repo: Path = REPO
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    validated, authority_sha = bridge.load_and_validate_authority(
        authority_path, repo=repo, tle_root=tle_root
    )
    assessment, source_receipts = live_resource_assessment(
        validated=validated, repo=repo
    )
    if assessment["status"] != "PASS":
        raise R7500ServerPreflightError("; ".join(assessment["failures"]))
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "authority_sha256": authority_sha,
        "resource_policy": validated["resource_policy"],
        "host": current_host_identity(),
        "runtime": current_runtime_identity(),
        "assessment": assessment,
        "source_matrices": source_receipts,
        "source_checkpoint_evaluation_authorized": True,
        "new_r7_training_authorized": False,
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    result = assert_evaluation_ready(
        authority_path=args.authority,
        tle_root=args.tle_root,
    )
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
