#!/usr/bin/env python3
"""Offline replay of the V0.23 controller path after shard generation.

The staging tree is strictly read-only.  Authentication is attempted for every
mode/world directory found, and failures are accumulated before merge/seal is
considered.  A complete schedule is merged and sealed below the disposable
``--output`` root; partial schedules are reported but never given altered merge
semantics.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Mapping


sys.dont_write_bytecode = True


CONTROLLER_RELATIVE = Path(
    ".scratch/multi-catfish-v023-c1c2-target-generation-launch/"
    "run_v023_c1c2_targets_server.py"
)
REPORT_NAME = "dryrun-postshard-report.json"
REPORT_SCHEMA = "multi-catfish-mcrl-v023-c1c2-controller-postshard-dryrun-v1"


class DryRunError(RuntimeError):
    pass


def _canonical(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _load_path(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DryRunError(f"module is unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _load_controller(repo: Path) -> ModuleType:
    path = Path(repo) / CONTROLLER_RELATIVE
    if path.is_symlink() or not path.is_file():
        raise DryRunError(f"controller is missing or symlinked: {path}")
    return _load_path("mcrl_v023_c1c2_postshard_dryrun_controller", path)


def _candidate_shards(staging: Path) -> list[tuple[str, Path]]:
    """Return every direct ``<mode>/world-<id>`` directory in stable order."""

    candidates: list[tuple[str, Path]] = []
    for mode_root in sorted(staging.iterdir(), key=lambda path: path.name):
        if mode_root.name == "shard-status" or not mode_root.is_dir():
            continue
        if mode_root.is_symlink():
            candidates.append((f"{mode_root.name}:<symlink>", mode_root))
            continue
        for root in sorted(mode_root.iterdir(), key=lambda path: path.name):
            if not root.name.startswith("world-") or not root.is_dir():
                continue
            world_text = root.name.removeprefix("world-")
            try:
                world = int(world_text)
            except ValueError:
                key = f"{mode_root.name}:{world_text}"
            else:
                key = f"{mode_root.name}:{world}"
            candidates.append((key, root))
    return candidates


def _write_report(output: Path, report: Mapping[str, object]) -> None:
    path = output / REPORT_NAME
    if path.exists() or path.is_symlink():
        raise DryRunError(f"refusing to overwrite dry-run report: {path}")
    path.write_bytes(_canonical(report))


def _final_line(verdict: str, summary: Mapping[str, object]) -> str:
    return (
        f"DRYRUN_C1C2_POSTSHARD_{verdict} "
        f"scheduled={summary['scheduled_shards']} "
        f"present={summary['present_shards']} "
        f"passed={summary['passed_shards']} "
        f"failed={summary['failed_shards']} "
        f"missing={summary['missing_shards']}"
    )


def run(args: argparse.Namespace) -> int:
    staging = Path(args.staging).resolve()
    output = Path(args.output).resolve()
    repo = Path(args.repo).resolve()
    if staging.is_symlink() or not staging.is_dir():
        raise DryRunError(f"staging root is missing or symlinked: {staging}")
    if output.exists() or output.is_symlink():
        raise DryRunError(f"refusing to overwrite dry-run output root: {output}")
    if output.is_relative_to(staging):
        raise DryRunError("dry-run output root must be outside the staging tree")
    output.mkdir(parents=True)

    findings: list[dict[str, object]] = []
    passed: dict[str, Path] = {}
    present_schedule_keys: set[str] = set()
    expected_schedule: dict[str, dict[str, object]] = {}
    verdict = "FAIL"
    try:
        controller = _load_controller(repo)
        expected_schedule = controller._expected_schedule(args)
        ordered_expected = sorted(expected_schedule, key=controller._shard_sort_key)
        candidates = _candidate_shards(staging)
        seen: set[str] = set()
        for key, root in candidates:
            message = "authenticated"
            try:
                if key in seen:
                    raise controller.ControllerError(
                        f"duplicate mode/world shard directory: {key}"
                    )
                seen.add(key)
                if root.is_symlink():
                    raise controller.ControllerError(
                        f"mode/world shard directory is symlinked: {key}"
                    )
                receipt = controller._read_receipt(root)
                if key not in expected_schedule:
                    raise controller.ControllerError(
                        f"mode/world shard is outside the authenticated schedule: {key}"
                    )
                present_schedule_keys.add(key)
                controller._validate_shard(
                    key, root, receipt, expected_schedule[key]
                )
                passed[key] = root
                status = "PASS"
            except Exception as error:
                if key in expected_schedule:
                    present_schedule_keys.add(key)
                status = "FAIL"
                message = str(error).replace("\n", " ")
            findings.append(
                {
                    "phase": "shard_authentication",
                    "shard": key,
                    "path": str(root),
                    "status": status,
                    "message": message,
                }
            )

        missing = [key for key in ordered_expected if key not in present_schedule_keys]
        for key in missing:
            findings.append(
                {
                    "phase": "schedule_completeness",
                    "shard": key,
                    "status": "MISSING",
                    "message": "authenticated schedule shard directory is absent",
                }
            )

        failed_count = sum(
            finding["status"] == "FAIL"
            for finding in findings
            if finding["phase"] == "shard_authentication"
        )
        if failed_count:
            findings.append(
                {
                    "phase": "merge_seal",
                    "status": "SKIPPED_AUTHENTICATION_FAILURE",
                    "message": "merge/seal requires every present shard to authenticate",
                }
            )
            verdict = "FAIL"
        elif missing:
            # controller._merge deliberately requires exact equality between
            # the supplied shard set and the authenticated schedule.  Calling
            # it on a subset would change that safety contract, so partial
            # merge/seal is not attempted.
            findings.append(
                {
                    "phase": "merge_seal",
                    "status": "BLOCKED_MISSING_SHARDS",
                    "message": "controller merge does not admit a shard subset",
                    "missing_shards": missing,
                }
            )
            verdict = "BLOCKED"
        else:
            merged_output = output / "merged-output"
            try:
                controller._merge(
                    passed,
                    merged_output,
                    expected_schedule=expected_schedule,
                )
                sealer = _load_path(
                    "mcrl_v023_c1c2_postshard_dryrun_sealer",
                    controller.SEALER,
                )
                manifest_sha256 = sealer.seal(merged_output)
            except Exception as error:
                findings.append(
                    {
                        "phase": "merge_seal",
                        "status": "FAIL",
                        "message": str(error).replace("\n", " "),
                    }
                )
                verdict = "FAIL"
            else:
                findings.append(
                    {
                        "phase": "merge_seal",
                        "status": "PASS",
                        "message": "real controller merge and sealer completed",
                        "output": str(merged_output),
                        "manifest_sha256": manifest_sha256,
                    }
                )
                verdict = "PASS"
    except Exception as error:
        findings.append(
            {
                "phase": "authority_schedule",
                "status": "FAIL",
                "message": str(error).replace("\n", " "),
            }
        )
        verdict = "FAIL"

    shard_findings = [
        finding
        for finding in findings
        if finding["phase"] == "shard_authentication"
    ]
    missing_findings = [
        finding
        for finding in findings
        if finding["phase"] == "schedule_completeness"
    ]
    summary: dict[str, object] = {
        "verdict": verdict,
        "scheduled_shards": len(expected_schedule),
        "present_shards": len(shard_findings),
        "passed_shards": sum(row["status"] == "PASS" for row in shard_findings),
        "failed_shards": sum(row["status"] == "FAIL" for row in shard_findings),
        "missing_shards": len(missing_findings),
    }
    report = {
        "schema": REPORT_SCHEMA,
        "staging": str(staging),
        "output": str(output),
        "repo": str(repo),
        "findings": findings,
        "summary": summary,
    }
    _write_report(output, report)
    print(_final_line(verdict, summary))
    return {"PASS": 0, "BLOCKED": 3, "FAIL": 2}[verdict]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--staging", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--materialization-dir", type=Path, required=True)
    p.add_argument("--tle-root", type=Path, required=True)
    p.add_argument("--prereg", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--manifest-digest", type=Path, required=True)
    p.add_argument("--execution-addendum", type=Path, required=True)
    p.add_argument("--python", type=Path, default=Path(sys.executable))
    p.add_argument("--users", type=int, default=100)
    return p


if __name__ == "__main__":
    try:
        raise SystemExit(run(parser().parse_args()))
    except Exception as error:
        print(f"DRYRUN_C1C2_POSTSHARD_FAIL: {error}", file=sys.stderr)
        raise SystemExit(2)
