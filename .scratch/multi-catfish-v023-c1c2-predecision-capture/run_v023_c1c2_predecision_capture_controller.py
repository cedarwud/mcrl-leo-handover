#!/usr/bin/env python3
"""TRAIN-only controller for the bounded V0.23 C1/C2 source capture.

The controller is an orchestration boundary, not a simulator implementation.
It invokes the existing per-world runner at most once for each frozen world,
then invokes the existing panel merger exactly once and the V2 materializer
exactly once.  All output targets are write-once.  A failed or partial output
root is intentionally not resumable: use a new fresh server root.

Importing this module is inert and standard-library only.  No simulator,
learner, TEST split, evaluation, or target code is imported here.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CODE_MANIFEST = HERE / "CODE-MANIFEST.json"
PREFLIGHT = HERE / "preflight_v023_c1c2_predecision.py"
PER_WORLD_RUNNER = HERE / "run_v023_c1c2_predecision_capture_server.py"
PANEL_MERGER = HERE / "merge_v023_c1c2_predecision_captures.py"
MATERIALIZER = (
    REPO / ".scratch" / "multi-catfish-v023-c1c2-neutral-materialization" / "materialize_v023_c1c2.py"
)
V023_MANIFEST = (
    REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "PREFLIGHT-MANIFEST.json"
)
V023_MANIFEST_DIGEST = V023_MANIFEST.with_name("PREFLIGHT-MANIFEST.sha256")
V023_PREFLIGHT = V023_MANIFEST.with_name("preflight_v023_lcsrs_r6.py")
EXECUTION_ADDENDUM = (
    REPO / "docs" / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"
)
PREREGISTRATION = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"

SCHEMA = "multi-catfish-mcrl-v023-c1-c2-predecision-server-capture-receipt-v1"
COMPLETE_SCHEMA = "multi-catfish-mcrl-v023-c1-c2-predecision-server-complete-v1"
FROZEN_WORLDS = tuple(range(2026121705, 2026121713))
SOURCE_CONCURRENCY = 4
C1_NEUTRAL_SEED = 3733296141
C2_NEUTRAL_SEED = 3936591716
C1_SEED_DOMAIN = (
    "mcrl-v023-c1c2-neutral-seed-v1|route=C1|"
    "panel=v023-train-panel-2026121705-2026121712-predecision"
)
C2_SEED_DOMAIN = (
    "mcrl-v023-c1c2-neutral-seed-v1|route=C2|"
    "panel=v023-train-panel-2026121705-2026121712-predecision"
)
CLAIM_CEILING = "TRAIN_SIMULATOR_SOURCE_TRAVERSAL_C1_DULL_EE_C2_PREDECISION_SINR_NO_LEARNER_NO_TEST_NO_EFFICACY"


class ControllerError(RuntimeError):
    """The bounded server sequence failed closed."""


def file_sha256(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ControllerError(f"expected a regular file: {target}")
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ControllerError("receipt is not canonical ASCII JSON") from error


def _require_regular(path: Path, *, field: str) -> Path:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise ControllerError(f"{field} is missing or symlinked: {target}")
    return target.resolve()


def _require_directory(path: Path, *, field: str) -> Path:
    target = Path(path)
    if target.is_symlink() or not target.is_dir():
        raise ControllerError(f"{field} is missing or symlinked: {target}")
    return target.resolve()


def _require_executable(path: Path, *, field: str) -> Path:
    """Accept a normal interpreter symlink but require its resolved binary."""

    target = Path(path)
    if not target.is_file() or not os.access(target, os.X_OK):
        raise ControllerError(f"{field} is missing or not executable: {target}")
    return target.resolve()


def _assert_fresh_target(path: Path, *, field: str) -> Path:
    target = Path(path)
    if not target.is_absolute():
        raise ControllerError(f"{field} must be absolute")
    if target.exists() or target.is_symlink():
        raise ControllerError(f"refusing to overwrite existing {field}: {target}")
    return target


def _create_fresh_directory(path: Path, *, field: str) -> Path:
    target = _assert_fresh_target(path, field=field)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir()
    except FileExistsError as error:
        raise ControllerError(f"refusing to overwrite raced {field}: {target}") from error
    return target


def _write_once(path: Path, payload: bytes, *, field: str) -> str:
    target = _assert_fresh_target(path, field=field)
    try:
        with target.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise ControllerError(f"refusing to overwrite raced {field}: {target}") from error
    return hashlib.sha256(payload).hexdigest()


def _run_checked(command: Sequence[str], *, cwd: Path, env: dict[str, str]) -> str:
    try:
        result = subprocess.run(
            [str(item) for item in command],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ControllerError(f"could not execute {' '.join(map(str, command))}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no subprocess detail").strip()
        raise ControllerError(
            f"subprocess failed ({result.returncode}): {' '.join(map(str, command))}: {detail[-2000:]}"
        )
    return result.stdout


def _preflight(args: argparse.Namespace, *, repo: Path) -> dict[str, Any]:
    command = [
        str(args.python),
        str(PREFLIGHT),
        "--manifest",
        str(args.code_manifest),
        "--code-manifest-sha256",
        str(args.code_manifest_sha256),
        "--repo",
        str(repo),
        "--v023-manifest",
        str(args.v023_manifest),
        "--v023-manifest-digest",
        str(args.v023_manifest_digest),
        "--v023-preflight",
        str(args.v023_preflight),
        "--prereg",
        str(args.prereg),
    ]
    output = _run_checked(command, cwd=repo, env=_server_environment())
    try:
        receipt = json.loads(output)
    except json.JSONDecodeError as error:
        raise ControllerError("preflight did not return JSON") from error
    if not isinstance(receipt, dict) or receipt.get("status") != "PASS":
        raise ControllerError("predecision preflight did not return PASS")
    inherited = receipt.get("inherited_v023_preflight")
    if not isinstance(inherited, dict) or inherited.get("status") != "PASS":
        raise ControllerError("inherited V0.23 preflight receipt is absent")
    return receipt


def _server_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )
    return environment


def _world_command(
    args: argparse.Namespace,
    *,
    world: int,
    output: Path,
    inherited_manifest_sha256: str,
) -> list[str]:
    return [
        str(args.python),
        str(PER_WORLD_RUNNER),
        "--world",
        str(world),
        "--tle-root",
        str(args.tle_root),
        "--prereg",
        str(args.prereg),
        "--manifest",
        str(args.v023_manifest),
        "--manifest-digest",
        str(args.v023_manifest_digest),
        "--execution-addendum",
        str(args.execution_addendum),
        "--preflight-sha256",
        inherited_manifest_sha256,
        "--c1-neutral-seed",
        str(C1_NEUTRAL_SEED),
        "--c2-neutral-seed",
        str(C2_NEUTRAL_SEED),
        "--output",
        str(output),
    ]


def _capture_worlds(
    args: argparse.Namespace,
    *,
    repo: Path,
    capture_dir: Path,
    inherited_manifest_sha256: str,
) -> dict[str, str]:
    paths = {
        world: capture_dir / f"world-{world}.json" for world in FROZEN_WORLDS
    }
    for world, path in paths.items():
        _assert_fresh_target(path, field=f"world {world} capture")

    def run_one(world: int) -> tuple[int, str]:
        output = _run_checked(
            _world_command(
                args,
                world=world,
                output=paths[world],
                inherited_manifest_sha256=inherited_manifest_sha256,
            ),
            cwd=repo,
            env=_server_environment(),
        )
        _require_regular(paths[world], field=f"world {world} capture")
        return world, file_sha256(paths[world])

    completed: dict[int, str] = {}
    # Four is only compute concurrency.  The world set, per-world seed, and
    # deterministic file names remain frozen and the merger sorts the panel.
    with ThreadPoolExecutor(max_workers=SOURCE_CONCURRENCY) as executor:
        futures = {executor.submit(run_one, world): world for world in FROZEN_WORLDS}
        for future in as_completed(futures):
            world = futures[future]
            try:
                returned_world, digest = future.result()
            except Exception as error:
                raise ControllerError(
                    f"world {world} capture failed: "
                    f"{type(error).__name__}: {error}"
                ) from error
            if returned_world != world:
                raise ControllerError("world capture future identity drifted")
            completed[world] = digest
    if tuple(sorted(completed)) != FROZEN_WORLDS:
        raise ControllerError("not all eight frozen world captures completed")
    return {f"world-captures/world-{world}.json": completed[world] for world in FROZEN_WORLDS}


def _merge_panel(
    args: argparse.Namespace,
    *,
    repo: Path,
    capture_dir: Path,
    panel_path: Path,
) -> str:
    _assert_fresh_target(panel_path, field="panel capture")
    command: list[str] = [str(args.python), str(PANEL_MERGER)]
    for world in FROZEN_WORLDS:
        command.extend(["--capture", str(capture_dir / f"world-{world}.json")])
    command.extend(
        [
            "--c1-neutral-seed",
            str(C1_NEUTRAL_SEED),
            "--c2-neutral-seed",
            str(C2_NEUTRAL_SEED),
            "--output",
            str(panel_path),
        ]
    )
    _run_checked(command, cwd=repo, env=_server_environment())
    return file_sha256(_require_regular(panel_path, field="panel capture"))


def _materialize(
    args: argparse.Namespace,
    *,
    repo: Path,
    panel_path: Path,
    materialized_dir: Path,
) -> dict[str, str]:
    _assert_fresh_target(materialized_dir, field="materialized source directory")
    _run_checked(
        [
            str(args.python),
            str(MATERIALIZER),
            "--capture",
            str(panel_path),
            "--output",
            str(materialized_dir),
        ],
        cwd=repo,
        env=_server_environment(),
    )
    expected = {
        "c1-informed.json",
        "c1-neutral.json",
        "c2-informed.json",
        "c2-neutral.json",
        "receipt.json",
        "MANIFEST.sha256",
    }
    if materialized_dir.is_symlink() or not materialized_dir.is_dir():
        raise ControllerError("materializer did not create a regular output directory")
    actual_names = {
        item.name for item in materialized_dir.iterdir() if item.is_file() or item.is_symlink()
    }
    if actual_names != expected:
        raise ControllerError(
            f"materializer output set drifted: missing={sorted(expected - actual_names)}, "
            f"extra={sorted(actual_names - expected)}"
        )
    files: dict[str, str] = {}
    for name in sorted(expected):
        files[f"materialized-source/{name}"] = file_sha256(
            _require_regular(materialized_dir / name, field=f"materialized {name}")
        )
    return files


def _seal(
    output_root: Path,
    *,
    world_files: dict[str, str],
    panel_sha256: str,
    materialized_files: dict[str, str],
    preflight_receipt: Mapping[str, Any],
    code_manifest_sha256: str,
    inherited_manifest_sha256: str,
    repo: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    files = dict(world_files)
    files["panel-capture.json"] = panel_sha256
    files.update(materialized_files)
    receipt_payload: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "TRAIN_PREDECISION_SOURCE_CAPTURE_COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "worlds": list(FROZEN_WORLDS),
        "world_count": len(FROZEN_WORLDS),
        "source_concurrency": SOURCE_CONCURRENCY,
        "panel_neutral_seeds": {
            "C1": {"seed": C1_NEUTRAL_SEED, "derivation_domain": C1_SEED_DOMAIN},
            "C2": {"seed": C2_NEUTRAL_SEED, "derivation_domain": C2_SEED_DOMAIN},
        },
        "code_manifest_sha256": code_manifest_sha256,
        "inherited_v023_preflight_manifest_sha256": inherited_manifest_sha256,
        "inherited_v023_preflight_status": preflight_receipt["status"],
        "v023_provenance": {
            "manifest": str(Path(args.v023_manifest).resolve()),
            "manifest_sha256": inherited_manifest_sha256,
            "manifest_digest": str(Path(args.v023_manifest_digest).resolve()),
            "manifest_digest_sha256": file_sha256(Path(args.v023_manifest_digest)),
            "preregistration": str(Path(args.prereg).resolve()),
            "preregistration_sha256": file_sha256(Path(args.prereg)),
            "tle": {
                "file_set_sha256": preflight_receipt["inherited_v023_preflight"][
                    "tle_file_set_sha256"
                ],
                "root_argument": preflight_receipt["inherited_v023_preflight"][
                    "tle_root_argument"
                ],
                "root_default": preflight_receipt["inherited_v023_preflight"][
                    "tle_root_default"
                ],
                "runtime_root": str(Path(args.tle_root).resolve()),
            },
        },
        "tle_root": str(Path(args.tle_root).resolve(strict=False)),
        "preregistration": str(Path(args.prereg).resolve()),
        "stage_counts": {
            "per_world_write_once_captures": 8,
            "panel_merge": 1,
            "v2_materialization": 1,
            "hash_seal": 1,
            "complete_marker": 1,
        },
        "controls": {
            "source_split": "TRAIN",
            "learner_update": False,
            "episode_policy_training": False,
            "test_split_opened": False,
            "evaluation": False,
            "efficacy_claim": False,
            "target_outcomes_persisted": False,
        },
        "files": files,
    }
    receipt_path = output_root / "receipt.json"
    receipt_sha256 = _write_once(
        receipt_path, canonical_bytes(receipt_payload), field="capture receipt"
    )
    files["receipt.json"] = receipt_sha256
    manifest_lines = [f"{files[name]}  {name}" for name in sorted(files)]
    manifest_bytes = ("\n".join(manifest_lines) + "\n").encode("ascii")
    manifest_path = output_root / "MANIFEST.sha256"
    manifest_sha256 = _write_once(
        manifest_path, manifest_bytes, field="capture seal manifest"
    )
    complete_payload = {
        "schema": COMPLETE_SCHEMA,
        "status": "COMPLETE",
        "claim_ceiling": CLAIM_CEILING,
        "worlds": list(FROZEN_WORLDS),
        "receipt_sha256": receipt_sha256,
        "manifest_sha256": manifest_sha256,
        "code_manifest_sha256": code_manifest_sha256,
        "inherited_v023_preflight_manifest_sha256": inherited_manifest_sha256,
    }
    complete_sha256 = _write_once(
        output_root / "COMPLETE",
        canonical_bytes(complete_payload),
        field="capture complete marker",
    )
    return {
        "receipt_sha256": receipt_sha256,
        "manifest_sha256": manifest_sha256,
        "complete_sha256": complete_sha256,
        "files": files,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--code-manifest", type=Path, default=CODE_MANIFEST)
    parser.add_argument("--code-manifest-sha256", required=True)
    parser.add_argument("--v023-manifest", type=Path, default=V023_MANIFEST)
    parser.add_argument("--v023-manifest-digest", type=Path, default=V023_MANIFEST_DIGEST)
    parser.add_argument("--v023-preflight", type=Path, default=V023_PREFLIGHT)
    parser.add_argument("--prereg", type=Path, default=PREREGISTRATION)
    parser.add_argument("--execution-addendum", type=Path, default=EXECUTION_ADDENDUM)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo = _require_directory(Path(args.repo), field="repository root")
    _require_directory(Path(args.tle_root), field="external TRAIN TLE root")
    _require_executable(Path(args.python), field="server Python")
    _require_regular(Path(args.code_manifest), field="code manifest")
    _require_regular(Path(args.prereg), field="preregistration")
    _require_regular(Path(args.execution_addendum), field="execution addendum")
    _assert_fresh_target(Path(args.output_root), field="capture output root")

    preflight_receipt = _preflight(args, repo=repo)
    inherited_manifest_sha256 = str(
        preflight_receipt["inherited_v023_preflight"]["manifest_sha256"]
    )
    code_manifest_sha256 = file_sha256(Path(args.code_manifest))
    output_root = _create_fresh_directory(
        Path(args.output_root), field="capture output root"
    )
    capture_dir = output_root / "world-captures"
    capture_dir.mkdir()
    world_files = _capture_worlds(
        args,
        repo=repo,
        capture_dir=capture_dir,
        inherited_manifest_sha256=inherited_manifest_sha256,
    )
    panel_path = output_root / "panel-capture.json"
    panel_sha256 = _merge_panel(
        args,
        repo=repo,
        capture_dir=capture_dir,
        panel_path=panel_path,
    )
    materialized_files = _materialize(
        args,
        repo=repo,
        panel_path=panel_path,
        materialized_dir=output_root / "materialized-source",
    )
    seal = _seal(
        output_root,
        world_files=world_files,
        panel_sha256=panel_sha256,
        materialized_files=materialized_files,
        preflight_receipt=preflight_receipt,
        code_manifest_sha256=code_manifest_sha256,
        inherited_manifest_sha256=inherited_manifest_sha256,
        repo=repo,
        args=args,
    )
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "world_count": len(FROZEN_WORLDS),
        "source_concurrency": SOURCE_CONCURRENCY,
        "output_root": str(output_root),
        "seal": seal,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run(args)
    except (ControllerError, OSError) as error:
        print(f"PREDECISION_CONTROLLER_BLOCKED: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
