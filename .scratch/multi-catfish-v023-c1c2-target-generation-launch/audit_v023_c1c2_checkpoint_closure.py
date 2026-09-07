#!/usr/bin/env python3
"""Audit the V0.23 C1/C2 launch bundle's d40 checkpoint closure.

This is a read-only, local closure audit.  It proves that R4 capture and R5
target generation both select the current repriced V0.20 d40 Q1/Q2 checkpoint
through the launch-local runtime adapter.  It never opens SSH, creates a
server root, starts tmux, or loads a simulator.

The legacy e6 MODQN checkpoint may remain in the workspace as historical
evidence, but it must not be an active manifest binding or a target-generator
input.  The audit therefore fails closed on either a stale legacy binding or a
missing d40 adapter dispatch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

R6_MANIFEST = REPO / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json"
R6_CHECKPOINT_RELATIVE = (
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/"
    "lineage-2026092101/checkpoints/"
    "lineage-2026092101-q2init-2026108101-rung-003000.pt"
)
R6_CHECKPOINT_SHA256 = "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
LEGACY_MAIN_RELATIVE = "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"
LEGACY_MAIN_SHA256 = "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
TARGET_GENERATOR = REPO / ".scratch/multi-catfish-v023-c1c2-target-generation/generate_v023_c1c2_targets.py"
LAUNCHER = HERE / "sync_launch_v023_c1c2_targets_server.sh"
CODE_MANIFEST = HERE / "CODE-MANIFEST.json"
TARGET_ADAPTER = HERE / "d40_checkpoint_runtime_adapter.py"


class CheckpointClosureError(RuntimeError):
    """The launch bundle cannot prove one checkpoint authority."""


def sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CheckpointClosureError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CheckpointClosureError(f"missing JSON file: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckpointClosureError(f"malformed ASCII JSON: {path}") from error
    if not isinstance(payload, dict):
        raise CheckpointClosureError(f"JSON root is not an object: {path}")
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii") + b"\n"
    if raw != canonical:
        raise CheckpointClosureError(f"JSON is not canonical: {path}")
    return payload


def _binding(payload: Mapping[str, Any], role: str) -> Mapping[str, Any]:
    rows = payload.get("bindings")
    if not isinstance(rows, list):
        raise CheckpointClosureError("CODE-MANIFEST bindings are missing")
    for row in rows:
        if isinstance(row, Mapping) and row.get("role") == role:
            return row
    raise CheckpointClosureError(f"CODE-MANIFEST lacks role: {role}")


def audit(repo: Path = REPO) -> dict[str, Any]:
    """Return a fail-closed d40 checkpoint-closure receipt without remote access."""

    root = Path(repo).resolve()
    r6_path = root / R6_MANIFEST.relative_to(REPO)
    r6 = _canonical_json(r6_path)
    configuration = r6.get("configuration")
    if not isinstance(configuration, Mapping):
        raise CheckpointClosureError("R6 configuration is missing")
    selected = configuration.get("selected_checkpoint")
    if not isinstance(selected, Mapping):
        raise CheckpointClosureError("R6 selected checkpoint is missing")
    selected_path = selected.get("path")
    selected_sha = selected.get("sha256")
    if selected_path != R6_CHECKPOINT_RELATIVE or selected_sha != R6_CHECKPOINT_SHA256:
        raise CheckpointClosureError("R6 selected checkpoint is not the sealed d40 authority")
    r6_binding = _binding(r6, "selected_q1_q2_checkpoint")
    if r6_binding.get("path") != R6_CHECKPOINT_RELATIVE or r6_binding.get("sha256") != R6_CHECKPOINT_SHA256:
        raise CheckpointClosureError("R6 checkpoint binding disagrees with configuration")

    code_manifest_path = root / CODE_MANIFEST.relative_to(REPO)
    code_manifest = _canonical_json(code_manifest_path)
    active_paths = [
        str(row.get("path", "")).lower()
        for row in code_manifest.get("bindings", ())
        if isinstance(row, Mapping)
    ]
    if any(
        marker in path
        for path in active_paths
        for marker in (".scratch/c2-v03", "ee_axis_temporal", "temporal_fork")
    ):
        raise CheckpointClosureError(
            "legacy Temporal-Fork producer remains an active CODE-MANIFEST binding"
        )
    if any(
        isinstance(row, Mapping) and row.get("role") == "main_training_input"
        for row in code_manifest.get("bindings", ())
    ):
        raise CheckpointClosureError(
            "legacy main-training checkpoint remains an active binding"
        )
    d40_binding = _binding(code_manifest, "d40_checkpoint")
    if (
        d40_binding.get("path") != R6_CHECKPOINT_RELATIVE
        or d40_binding.get("sha256") != R6_CHECKPOINT_SHA256
    ):
        raise CheckpointClosureError("CODE-MANIFEST d40 checkpoint binding disagrees")
    adapter_binding = _binding(code_manifest, "runtime_d40_checkpoint_adapter")
    if adapter_binding.get("path") != TARGET_ADAPTER.relative_to(REPO).as_posix():
        raise CheckpointClosureError("CODE-MANIFEST d40 adapter path disagrees")
    sealed_file = root / R6_CHECKPOINT_RELATIVE
    if sha256_file(sealed_file) != R6_CHECKPOINT_SHA256:
        raise CheckpointClosureError("sealed Q1/Q2 checkpoint bytes drifted")

    generator = (root / TARGET_GENERATOR.relative_to(REPO)).read_text(encoding="utf-8")
    launcher = (root / LAUNCHER.relative_to(REPO)).read_text(encoding="utf-8")
    adapter = (root / TARGET_ADAPTER.relative_to(REPO)).read_text(encoding="utf-8")
    if "D40_CHECKPOINT_PATH" not in generator or "authenticate_d40_checkpoint" not in generator:
        raise CheckpointClosureError("target generator lacks d40 checkpoint authentication")
    if "D40CheckpointRuntimeAdapter" not in generator:
        raise CheckpointClosureError("target generator lacks d40 runtime adapter")
    if "_verify_and_load_trainer" in generator or "input_dir" in generator:
        raise CheckpointClosureError("target generator still exposes the legacy e6 loader seam")
    if "OPS3_PRODUCER_PATH" not in generator or "_native_q12_anchor" not in generator:
        raise CheckpointClosureError("target generator lacks the current repriced OPS-3 producer")
    if "OPS3_SELECTED_PAIR_SCHEMA" not in generator or "target_unit" not in generator:
        raise CheckpointClosureError("target generator lacks the typed normalized OPS-3 dataset seam")
    if any(
        marker in generator
        for marker in (
            "C2TemporalForkTrainerBackend",
            "ee_axis_temporal_capture",
            "ee_axis_temporal_dataset",
            "c2_temporal_fork",
        )
    ):
        raise CheckpointClosureError("target generator still reaches the legacy Temporal-Fork producer")
    if "--input-dir" in launcher or "artifacts/training-2026-08-25-rerun01" in launcher:
        raise CheckpointClosureError("launcher still exposes the legacy e6 input path")

    return {
        "schema": "multi-catfish-mcrl-v023-c1c2-checkpoint-closure-audit-v1",
        "status": "PASS_D40_CHECKPOINT_RUNTIME_ADAPTER",
        "sealed_capture_checkpoint": {
            "role": "R6 selected_q1_q2_checkpoint / R4 capture provenance",
            "path": R6_CHECKPOINT_RELATIVE,
            "sha256": R6_CHECKPOINT_SHA256,
        },
        "target_generation_checkpoint": {
            "role": "R5 d40_checkpoint / launch-local adapter",
            "path": R6_CHECKPOINT_RELATIVE,
            "sha256": R6_CHECKPOINT_SHA256,
            "adapter": TARGET_ADAPTER.relative_to(REPO).as_posix(),
        },
        "runtime_chain": {
            "source_authentication": "R6 source adapter _authenticate -> V0.20 load_repriced_heads",
            "target_generator_authentication": "d40_checkpoint_runtime_adapter.authenticate_d40_checkpoint",
            "main_policy": "D40CheckpointRuntimeAdapter native Q1+Q2 -> repriced OPS-3 selected-pair projection",
            "sealed_compare": True,
        },
        "ready_to_relaunch": True,
        "required_scope": "TRAIN physical target generation only; no learner, episode training, or TEST split",
        "ssh_or_launch_performed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="return nonzero unless the d40 runtime closure is ready",
    )
    args = parser.parse_args(argv)
    try:
        receipt = audit(args.repo)
    except CheckpointClosureError as error:
        print(f"V023_C1C2_CHECKPOINT_CLOSURE_BLOCKED: {error}")
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    return 0 if not args.require_ready or receipt["ready_to_relaunch"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
