#!/usr/bin/env python3
"""Non-simulator preflight for the V0.23 C1/C2 target-generation launch.

The preflight authenticates the exact local code closure and the R6 source
authority before an SSH boundary is opened.  It intentionally does not read
the server-only R4 capture, TLEs, or a learner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-preflight-v2"
R6_MANIFEST_PATH = ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json"
R6_DIGEST_PATH = ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256"
TARGET_GENERATOR_PATH = ".scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py"
OPS3_PRODUCER_PATH = ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py"
SHORT_BENCHMARK_PATH = (
    ".scratch/multi-catfish-v023-c1c2-target-generation/benchmark_v023_c1c2_targets.py"
)
SHORT_BENCHMARK_RUNNER_PATH = (
    ".scratch/multi-catfish-v023-c1c2-target-generation-launch/"
    "run_v023_c1c2_short_benchmarks.py"
)
D40_ADAPTER_PATH = ".scratch/multi-catfish-v023-c1c2-target-generation-launch/d40_checkpoint_runtime_adapter.py"
D40_CHECKPOINT_PATH = (
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/"
    "lineage-2026092101/checkpoints/"
    "lineage-2026092101-q2init-2026108101-rung-003000.pt"
)
D40_CHECKPOINT_SHA256 = "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
FORBIDDEN_PATH_MARKERS = ("r5", "test_split", "episode_training")
LEGACY_C2_PATH_MARKERS = (".scratch/c2-v03", "ee_axis_temporal", "temporal_fork")

# C2 is the current repriced OPS-3 selected-pair producer.  The old Temporal-
# Fork backend was a different formula and is intentionally absent from this
# active closure.  The R7 adapter owns the source-side projection; these
# direct dependencies make that contract auditable without treating a broad
# synced directory as an integrity binding.
RUNTIME_IMPORT_BINDINGS = (
    ("runtime_ops3_producer", OPS3_PRODUCER_PATH),
    ("runtime_ops3_formula", "src/mcrl/runtime/ee_axis_ops3.py"),
    ("runtime_ops3_live", "src/mcrl/runtime/ee_axis_ops3_live.py"),
    ("runtime_q2_state", "src/mcrl/runtime/ee_axis_v014_q2_state.py"),
    ("runtime_d40_checkpoint_adapter", D40_ADAPTER_PATH),
    ("d40_checkpoint", D40_CHECKPOINT_PATH),
)


class PreflightError(RuntimeError):
    """The launch closure is missing, stale, or crosses the split boundary."""


def sha256_file(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise PreflightError(f"expected regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise PreflightError(f"manifest is missing or symlinked: {source}")
    raw = source.read_bytes()
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreflightError(f"manifest is not ASCII JSON: {source}") from error
    if not isinstance(value, dict):
        raise PreflightError("manifest root is not an object")
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")
    if raw not in (encoded, encoded + b"\n"):
        raise PreflightError(f"manifest is not canonical: {source}")
    return value


def _digest(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PreflightError(f"{field} is not a lowercase SHA-256")
    return value


def _relative_path(value: object, field: str, repo: Path) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise PreflightError(f"{field}.path is empty")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PreflightError(f"{field}.path must be repository-relative")
    resolved = (repo / relative).resolve()
    if not resolved.is_relative_to(repo):
        raise PreflightError(f"{field}.path escapes repository")
    return relative.as_posix(), resolved


def validate_nested_r6_runtime_closure(
    r6_payload: Mapping[str, object], *, repo: Path
) -> dict[str, str]:
    """Authenticate every file frozen by the nested R6 source authority.

    The live checkout may legitimately contain a newer learner integration,
    so this check is opt-in for the immutable server-side source snapshot used
    by target generation.  It must run before even the one-anchor benchmark.
    """

    repo_root = Path(repo).resolve()
    bindings = r6_payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise PreflightError("R6 authority has no runtime bindings")
    verified: dict[str, str] = {}
    for index, raw in enumerate(bindings):
        if not isinstance(raw, Mapping):
            raise PreflightError(f"R6 bindings[{index}] is not an object")
        relative, resolved = _relative_path(
            raw.get("path"), f"R6 bindings[{index}]", repo_root
        )
        expected = _digest(raw.get("sha256"), f"R6 bindings[{index}].sha256")
        actual = sha256_file(resolved)
        if actual != expected:
            raise PreflightError(
                f"nested R6 binding drifted for {relative}: "
                f"expected {expected}, got {actual}"
            )
        verified[relative] = actual
    return verified


def validate_manifest(
    manifest_path: Path,
    *,
    manifest_digest_path: Path | None = None,
    repo: Path = REPO,
    require_r6_runtime_closure: bool = False,
) -> dict[str, Any]:
    """Validate exact code bindings and the current R6 authority binding."""

    repo_root = Path(repo).resolve()
    payload = canonical_json(manifest_path)
    if payload.get("schema") != SCHEMA or payload.get("manifest_version") != 2:
        raise PreflightError("target-generation manifest schema/version is stale")
    bindings = payload.get("bindings")
    if not isinstance(bindings, list) or not bindings:
        raise PreflightError("target-generation manifest has no bindings")
    seen_paths: set[str] = set()
    seen_roles: set[str] = set()
    actual_by_role: dict[str, dict[str, str]] = {}
    for index, raw in enumerate(bindings):
        if not isinstance(raw, Mapping):
            raise PreflightError(f"bindings[{index}] is not an object")
        role = raw.get("role")
        if not isinstance(role, str) or not role:
            raise PreflightError(f"bindings[{index}] role is empty")
        if role in seen_roles:
            raise PreflightError(f"binding role repeats: {role}")
        seen_roles.add(role)
        relative, resolved = _relative_path(raw.get("path"), f"bindings[{index}]", repo_root)
        if relative in seen_paths:
            raise PreflightError(f"binding path repeats: {relative}")
        seen_paths.add(relative)
        if any(marker in relative.lower() for marker in FORBIDDEN_PATH_MARKERS):
            raise PreflightError(f"forbidden stale/runtime path in code manifest: {relative}")
        if any(marker in relative.lower() for marker in LEGACY_C2_PATH_MARKERS):
            raise PreflightError(
                f"legacy Temporal-Fork producer remains an active binding: {relative}"
            )
        expected = _digest(raw.get("sha256"), f"bindings[{index}].sha256")
        actual = sha256_file(resolved)
        if actual != expected:
            raise PreflightError(f"binding drifted for {relative}")
        actual_by_role[role] = {"role": role, "path": relative, "sha256": actual}

    required = {
        "launcher",
        "controller",
        "sealer",
        "target_generator",
    "short_benchmark",
    "short_benchmark_runner",
    "short_benchmark_tests",
    "checkpoint_closure_audit",
        "materializer",
        "capture_bridge",
        "r6_preflight_manifest",
        "r6_preflight_digest",
        "r6_source_adapter",
        "execution_addendum",
        "preregistration",
        "launch_tests",
    }
    required.update(role for role, _ in RUNTIME_IMPORT_BINDINGS)
    missing = required - set(actual_by_role)
    if missing:
        raise PreflightError(f"required code bindings are missing: {sorted(missing)}")
    for role, expected_path in RUNTIME_IMPORT_BINDINGS:
        if actual_by_role[role]["path"] != expected_path:
            raise PreflightError(f"runtime import binding points at an unexpected path: {role}")
    generator_path = actual_by_role["target_generator"]["path"]
    if generator_path != TARGET_GENERATOR_PATH:
        raise PreflightError("target generator binding points at an unexpected path")
    if actual_by_role["short_benchmark"]["path"] != SHORT_BENCHMARK_PATH:
        raise PreflightError("short benchmark binding points at an unexpected path")
    if actual_by_role["short_benchmark_runner"]["path"] != SHORT_BENCHMARK_RUNNER_PATH:
        raise PreflightError("short benchmark runner binding points at an unexpected path")
    if actual_by_role["r6_preflight_manifest"]["path"] != R6_MANIFEST_PATH:
        raise PreflightError("R6 preflight manifest path is not bound")
    if actual_by_role["r6_preflight_digest"]["path"] != R6_DIGEST_PATH:
        raise PreflightError("R6 preflight digest path is not bound")
    if actual_by_role["runtime_d40_checkpoint_adapter"]["path"] != D40_ADAPTER_PATH:
        raise PreflightError("d40 runtime adapter path is not bound")
    if actual_by_role["d40_checkpoint"]["path"] != D40_CHECKPOINT_PATH:
        raise PreflightError("d40 checkpoint path is not bound")
    if actual_by_role["d40_checkpoint"]["sha256"] != D40_CHECKPOINT_SHA256:
        raise PreflightError("d40 checkpoint digest is not the current binding")
    if "main_training_input" in actual_by_role:
        raise PreflightError("legacy main-training checkpoint remains an active binding")

    r6_manifest = repo_root / R6_MANIFEST_PATH
    r6_digest = repo_root / R6_DIGEST_PATH
    manifest_sha = sha256_file(r6_manifest)
    digest_lines = r6_digest.read_text(encoding="ascii").splitlines()
    if len(digest_lines) != 1 or digest_lines[0].split() != [manifest_sha, "PREFLIGHT-MANIFEST.json"]:
        raise PreflightError("R6 manifest digest sidecar disagrees")
    r6_payload = canonical_json(r6_manifest)
    if not str(r6_payload.get("schema", "")).startswith(
        "multi-catfish-mcrl-v023-lcsrs-observability-preflight-r6-"
    ):
        raise PreflightError("R6 binding is not the current fit-binding preflight")
    configuration = r6_payload.get("configuration")
    if not isinstance(configuration, Mapping):
        raise PreflightError("R6 configuration is missing")
    if configuration.get("test_split_opened") is not False or configuration.get("episode_training") is not False:
        raise PreflightError("R6 authority crosses the TRAIN-only boundary")
    declared = payload.get("configuration")
    if not isinstance(declared, Mapping):
        raise PreflightError("target-generation configuration is missing")
    if declared.get("split") != "TRAIN" or declared.get("learner_update") is not False:
        raise PreflightError("target-generation configuration is not TRAIN-only")
    if declared.get("episode_training") is not False or declared.get("test_split_opened") is not False:
        raise PreflightError("target-generation configuration opens a forbidden boundary")
    if payload.get("r6_manifest_sha256") != manifest_sha:
        raise PreflightError("target-generation manifest does not bind current R6 digest")
    nested_r6_binding_count = None
    if require_r6_runtime_closure:
        nested_r6_binding_count = len(
            validate_nested_r6_runtime_closure(r6_payload, repo=repo_root)
        )
    return {
        "schema": SCHEMA,
        "status": "PASS_LOCAL_CODE_AND_R6_D40_BINDING",
        "manifest_sha256": sha256_file(manifest_path),
        "r6_manifest_sha256": manifest_sha,
        "d40_checkpoint": {
            "path": D40_CHECKPOINT_PATH,
            "sha256": D40_CHECKPOINT_SHA256,
        },
        "binding_count": len(actual_by_role),
        "nested_r6_binding_count": nested_r6_binding_count,
        "claim_ceiling": "TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_NO_EPISODE_TRAINING_NO_TEST",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-digest", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument(
        "--require-r6-runtime-closure",
        action="store_true",
        help="authenticate every R6 runtime binding in this immutable source snapshot",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest_sha = sha256_file(args.manifest)
        lines = args.manifest_digest.read_text(encoding="ascii").splitlines()
        if len(lines) != 1 or lines[0].split() != [manifest_sha, "CODE-MANIFEST.json"]:
            raise PreflightError("target-generation manifest digest sidecar disagrees")
        receipt = validate_manifest(
            args.manifest,
            manifest_digest_path=args.manifest_digest,
            repo=args.repo,
            require_r6_runtime_closure=args.require_r6_runtime_closure,
        )
    except Exception as error:
        print(f"V023_C1C2_TARGET_PREFLIGHT_BLOCKED: {error}")
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
