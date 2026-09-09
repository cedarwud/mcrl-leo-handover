#!/usr/bin/env python3
"""Run and validate the bounded C2 short-benchmark gradient.

The runner deliberately wraps the existing read-only benchmark instead of
changing its implementation.  Each case is an independent process and gets
an immutable receipt.  The launcher may continue to target generation only
when all six receipts are PASS:

* informed/neutral single-candidate;
* informed/neutral double-candidate;
* informed/neutral full-step cohort.

No target output is opened by this module.  A failed case is recorded as a
terminal receipt and the command exits nonzero; hash drift is never converted
into a timing result.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BENCHMARK = (
    HERE.parent
    / "multi-catfish-v023-c1c2-target-generation"
    / "benchmark_v023_c1c2_targets.py"
)
BENCHMARK_RELATIVE = (
    ".scratch/multi-catfish-v023-c1c2-target-generation/"
    "benchmark_v023_c1c2_targets.py"
)
RUNNER_RELATIVE = (
    ".scratch/multi-catfish-v023-c1c2-target-generation-launch/"
    "run_v023_c1c2_short_benchmarks.py"
)
GENERATOR_RELATIVE = (
    ".scratch/multi-catfish-v023-c1c2-target-generation/"
    "generate_v023_c1c2_targets.py"
)
CODE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-preflight-v2"
R6_MANIFEST_RELATIVE = ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json"
R6_DIGEST_RELATIVE = ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256"
D40_CHECKPOINT_RELATIVE = (
    ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/"
    "lineage-2026092101/checkpoints/"
    "lineage-2026092101-q2init-2026108101-rung-003000.pt"
)
D40_CHECKPOINT_SHA256 = "d40a0f3095f9bb9010d0146a88a77b3c8a824fb9bd3e5aee2205f3ae8be592dc"
OPS3_BINDINGS = (
    (
        "runtime_ops3_producer",
        ".scratch/multi-catfish-v023-r7-launch-ready/v023_lcsrs_source_adapter.py",
    ),
    ("runtime_ops3_formula", "src/mcrl/runtime/ee_axis_ops3.py"),
    ("runtime_ops3_live", "src/mcrl/runtime/ee_axis_ops3_live.py"),
    ("runtime_q2_state", "src/mcrl/runtime/ee_axis_v014_q2_state.py"),
)
LEGACY_C2_PATH_MARKERS = (".scratch/c2-v03", "ee_axis_temporal", "temporal_fork")
SCHEMA = "multi-catfish-mcrl-v023-c1c2-short-benchmark-receipt-v1"
SUMMARY_SCHEMA = "multi-catfish-mcrl-v023-c1c2-short-benchmark-summary-v1"
BENCHMARK_SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-benchmark-v1"
BENCHMARK_CLAIM_CEILING = (
    "TRAIN_C2_PHYSICAL_TARGET_GENERATION_BENCHMARK_ONLY_NO_LEARNER_"
    "NO_REPLAY_WRITE_NO_EPISODE_TRAINING_NO_TEST"
)
CLAIM_CEILING = (
    "TRAIN_C2_SHORT_GRADIENT_ONLY_NO_LEARNER_NO_REPLAY_WRITE_"
    "NO_EPISODE_TRAINING_NO_TEST"
)
TRAIN = "TRAIN"
USERS = 100
MAX_STEP = 2
MAX_TIMEOUT_S = 600.0
DEFAULT_TIMEOUT_S = 540.0
EXTERNAL_GRACE_S = 5.0
MODES = ("informed", "neutral")
LEVELS = ("single", "double", "full-step")


class ShortBenchmarkError(RuntimeError):
    """A short benchmark cannot produce a trusted receipt."""


@dataclass(frozen=True)
class BenchmarkCase:
    mode: str
    level: str
    anchor_count: int | None
    full_step_cohort: bool

    @property
    def name(self) -> str:
        return f"c2-{self.mode}-{self.level}"


def benchmark_cases() -> tuple[BenchmarkCase, ...]:
    """Return the fixed six-case gradient in deterministic order."""

    return tuple(
        BenchmarkCase(
            mode=mode,
            level=level,
            anchor_count=(1 if level == "single" else 2 if level == "double" else None),
            full_step_cohort=level == "full-step",
        )
        for mode in MODES
        for level in LEVELS
    )


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


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _sha(path: Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ShortBenchmarkError(f"expected regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ShortBenchmarkError(f"{field} is not a lowercase SHA-256")
    return value


def _read_canonical(path: Path) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ShortBenchmarkError(f"canonical JSON is missing or symlinked: {source}")
    raw = source.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"), parse_constant=_reject_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ShortBenchmarkError(f"canonical JSON is malformed: {source}") from error
    if not isinstance(payload, dict) or raw not in (_canonical(payload), _canonical(payload).rstrip(b"\n")):
        raise ShortBenchmarkError(f"canonical JSON is not canonical: {source}")
    return payload


def _relative_binding(value: object, *, field: str, repo: Path) -> tuple[str, Path]:
    if not isinstance(value, str) or not value:
        raise ShortBenchmarkError(f"{field}.path is empty")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ShortBenchmarkError(f"{field}.path is unsafe")
    resolved = (repo / relative).resolve()
    if not resolved.is_relative_to(repo.resolve()):
        raise ShortBenchmarkError(f"{field}.path escapes repository")
    return relative.as_posix(), resolved


def _binding(payload: Mapping[str, object], role: str) -> Mapping[str, object]:
    rows = payload.get("bindings")
    if not isinstance(rows, list):
        raise ShortBenchmarkError("CODE-MANIFEST bindings are missing")
    matches = [row for row in rows if isinstance(row, Mapping) and row.get("role") == role]
    if len(matches) != 1:
        raise ShortBenchmarkError(f"CODE-MANIFEST role is not unique: {role}")
    return matches[0]


def _read_sidecar(path: Path, *, expected_sha256: str, expected_name: str) -> None:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ShortBenchmarkError(f"digest sidecar is missing or symlinked: {source}")
    lines = source.read_text(encoding="ascii").splitlines()
    if len(lines) != 1 or lines[0].split() != [expected_sha256, expected_name]:
        raise ShortBenchmarkError(f"digest sidecar disagrees: {source}")


def _load_code_context(
    code_manifest: Path,
    code_manifest_digest: Path,
    *,
    repo: Path = REPO,
) -> dict[str, object]:
    """Authenticate the code manifest and all paths needed by the receipt."""

    manifest = Path(code_manifest).resolve()
    digest_path = Path(code_manifest_digest).resolve()
    if manifest.name != "CODE-MANIFEST.json" or digest_path.name != "CODE-MANIFEST.sha256":
        raise ShortBenchmarkError("CODE-MANIFEST sidecar names are not canonical")
    manifest_payload = _read_canonical(manifest)
    if (
        manifest_payload.get("schema") != CODE_MANIFEST_SCHEMA
        or manifest_payload.get("manifest_version") != 2
    ):
        raise ShortBenchmarkError("CODE-MANIFEST schema/version is stale")
    configuration = manifest_payload.get("configuration")
    if not isinstance(configuration, Mapping):
        raise ShortBenchmarkError("CODE-MANIFEST TRAIN configuration is missing")
    if (
        configuration.get("split") != TRAIN
        or configuration.get("learner_update") is not False
        or configuration.get("episode_training") is not False
        or configuration.get("test_split_opened") is not False
    ):
        raise ShortBenchmarkError("CODE-MANIFEST crosses the TRAIN-only boundary")
    bindings = manifest_payload.get("bindings")
    if not isinstance(bindings, list):
        raise ShortBenchmarkError("CODE-MANIFEST bindings are missing")
    if any(
        any(marker in str(row.get("path", "")).lower() for marker in LEGACY_C2_PATH_MARKERS)
        for row in bindings
        if isinstance(row, Mapping)
    ):
        raise ShortBenchmarkError("CODE-MANIFEST still binds the legacy Temporal-Fork producer")
    manifest_sha256 = _sha(manifest)
    _read_sidecar(
        digest_path,
        expected_sha256=manifest_sha256,
        expected_name="CODE-MANIFEST.json",
    )
    code_manifest_digest_sha256 = _sha(digest_path)

    generator_binding = _binding(manifest_payload, "target_generator")
    generator_relative, generator_path = _relative_binding(
        generator_binding.get("path"), field="target_generator", repo=repo
    )
    if generator_relative != GENERATOR_RELATIVE:
        raise ShortBenchmarkError("target_generator binding points at an unexpected path")
    generator_sha256 = _digest(
        generator_binding.get("sha256"), field="target_generator.sha256"
    )
    if _sha(generator_path) != generator_sha256:
        raise ShortBenchmarkError("target generator hash drifted from CODE-MANIFEST")

    ops3_bindings: dict[str, dict[str, object]] = {}
    for role, expected_relative in OPS3_BINDINGS:
        binding = _binding(manifest_payload, role)
        relative, path = _relative_binding(binding.get("path"), field=role, repo=repo)
        if relative != expected_relative:
            raise ShortBenchmarkError(f"{role} binding points at an unexpected path")
        digest = _digest(binding.get("sha256"), field=f"{role}.sha256")
        if _sha(path) != digest:
            raise ShortBenchmarkError(f"{role} hash drifted from CODE-MANIFEST")
        ops3_bindings[role] = {"path": path, "sha256": digest}

    benchmark_binding = _binding(manifest_payload, "short_benchmark")
    benchmark_relative, benchmark_path = _relative_binding(
        benchmark_binding.get("path"), field="short_benchmark", repo=repo
    )
    if benchmark_relative != BENCHMARK_RELATIVE:
        raise ShortBenchmarkError("short benchmark binding points at an unexpected path")
    benchmark_sha256 = _digest(
        benchmark_binding.get("sha256"), field="short_benchmark.sha256"
    )
    if _sha(benchmark_path) != benchmark_sha256:
        raise ShortBenchmarkError("short benchmark hash drifted from CODE-MANIFEST")

    runner_binding = _binding(manifest_payload, "short_benchmark_runner")
    runner_relative, runner_path = _relative_binding(
        runner_binding.get("path"), field="short_benchmark_runner", repo=repo
    )
    if runner_relative != RUNNER_RELATIVE:
        raise ShortBenchmarkError("short benchmark runner binding points at an unexpected path")
    runner_sha256 = _digest(
        runner_binding.get("sha256"), field="short_benchmark_runner.sha256"
    )
    if _sha(runner_path) != runner_sha256:
        raise ShortBenchmarkError("short benchmark runner hash drifted from CODE-MANIFEST")

    checkpoint_binding = _binding(manifest_payload, "d40_checkpoint")
    checkpoint_relative, checkpoint_path = _relative_binding(
        checkpoint_binding.get("path"), field="d40_checkpoint", repo=repo
    )
    checkpoint_sha256 = _digest(
        checkpoint_binding.get("sha256"), field="d40_checkpoint.sha256"
    )
    if _sha(checkpoint_path) != checkpoint_sha256:
        raise ShortBenchmarkError("d40 checkpoint hash drifted from CODE-MANIFEST")

    source_binding = _binding(manifest_payload, "r6_preflight_manifest")
    source_relative, source_path = _relative_binding(
        source_binding.get("path"), field="r6_preflight_manifest", repo=repo
    )
    if source_relative != R6_MANIFEST_RELATIVE:
        raise ShortBenchmarkError("R6 source manifest binding points at an unexpected path")
    source_sha256 = _digest(
        source_binding.get("sha256"), field="r6_preflight_manifest.sha256"
    )
    if _sha(source_path) != source_sha256:
        raise ShortBenchmarkError("source manifest hash drifted from CODE-MANIFEST")

    source_digest_binding = _binding(manifest_payload, "r6_preflight_digest")
    source_digest_relative, source_digest_path = _relative_binding(
        source_digest_binding.get("path"),
        field="r6_preflight_digest",
        repo=repo,
    )
    if source_digest_relative != R6_DIGEST_RELATIVE:
        raise ShortBenchmarkError("R6 source digest binding points at an unexpected path")
    source_digest_sha256 = _digest(
        source_digest_binding.get("sha256"), field="r6_preflight_digest.sha256"
    )
    if _sha(source_digest_path) != source_digest_sha256:
        raise ShortBenchmarkError("source manifest digest sidecar hash drifted")
    _read_sidecar(
        source_digest_path,
        expected_sha256=source_sha256,
        expected_name="PREFLIGHT-MANIFEST.json",
    )
    if manifest_payload.get("r6_manifest_sha256") != source_sha256:
        raise ShortBenchmarkError("CODE-MANIFEST does not bind the current R6 source hash")
    if configuration.get("checkpoint_path") != checkpoint_relative:
        raise ShortBenchmarkError("CODE-MANIFEST checkpoint path is not the current D40 binding")
    if configuration.get("checkpoint_sha256") != checkpoint_sha256:
        raise ShortBenchmarkError("CODE-MANIFEST checkpoint hash is not the current D40 binding")
    if checkpoint_relative != D40_CHECKPOINT_RELATIVE or checkpoint_sha256 != D40_CHECKPOINT_SHA256:
        raise ShortBenchmarkError("D40 checkpoint binding is not the current authority")

    return {
        "code_manifest_path": manifest,
        "code_manifest_digest_path": digest_path,
        "code_manifest_sha256": manifest_sha256,
        "code_manifest_digest_sha256": code_manifest_digest_sha256,
        "generator_path": generator_path,
        "generator_relative": generator_relative,
        "generator_sha256": generator_sha256,
        "ops3_bindings": ops3_bindings,
        "benchmark_path": benchmark_path,
        "benchmark_relative": benchmark_relative,
        "benchmark_sha256": benchmark_sha256,
        "runner_path": runner_path,
        "runner_relative": runner_relative,
        "runner_sha256": runner_sha256,
        "checkpoint_path": checkpoint_path,
        "checkpoint_relative": checkpoint_relative,
        "checkpoint_sha256": checkpoint_sha256,
        "source_manifest_path": source_path,
        "source_manifest_relative": source_relative,
        "source_manifest_sha256": source_sha256,
        "source_manifest_digest_path": source_digest_path,
        "source_manifest_digest_relative": source_digest_relative,
        "source_manifest_digest_sha256": source_digest_sha256,
    }


def _materialization_snapshot(materialization_dir: Path) -> tuple[str, dict[str, str]]:
    root = Path(materialization_dir).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ShortBenchmarkError(f"materialization directory is not regular: {root}")
    manifest = root / "MANIFEST.sha256"
    if manifest.is_symlink() or not manifest.is_file():
        raise ShortBenchmarkError(f"materialization manifest is missing: {manifest}")
    entries: dict[str, str] = {}
    for line_number, line in enumerate(manifest.read_text(encoding="ascii").splitlines(), start=1):
        parts = line.split("  ", 1)
        if len(parts) != 2 or not parts[1] or parts[1] in entries:
            raise ShortBenchmarkError(f"materialization manifest line {line_number} is malformed")
        digest, name = parts
        entries[name] = _digest(digest, field=f"materialization[{line_number}]")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "/" in name or name.startswith("."):
            raise ShortBenchmarkError(f"materialization manifest path is unsafe: {name}")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ShortBenchmarkError(f"materialization contains a symlink: {path}")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(entries) | {"MANIFEST.sha256"}:
        raise ShortBenchmarkError(
            "materialization manifest closure drifted: "
            f"extra={sorted(actual - (set(entries) | {'MANIFEST.sha256'}))}, "
            f"missing={sorted((set(entries) | {'MANIFEST.sha256'}) - actual)}"
        )
    for name, expected in entries.items():
        if _sha(root / name) != expected:
            raise ShortBenchmarkError(f"materialization file hash drifted: {name}")
    return _sha(manifest), dict(sorted(entries.items()))


def _input_snapshot(
    *,
    context: Mapping[str, object],
    capture_path: Path,
    materialization_dir: Path,
    source_manifest: Path,
) -> dict[str, object]:
    capture = Path(capture_path).resolve()
    source = Path(source_manifest).resolve()
    if _sha(context["code_manifest_path"]) != context["code_manifest_sha256"]:
        raise ShortBenchmarkError("CODE-MANIFEST changed during short benchmark")
    if _sha(context["code_manifest_digest_path"]) != context["code_manifest_digest_sha256"]:
        raise ShortBenchmarkError("CODE-MANIFEST digest sidecar changed during short benchmark")
    if _sha(context["generator_path"]) != context["generator_sha256"]:
        raise ShortBenchmarkError("target generator changed during short benchmark")
    if _sha(context["benchmark_path"]) != context["benchmark_sha256"]:
        raise ShortBenchmarkError("short benchmark changed during short benchmark")
    if _sha(context["runner_path"]) != context["runner_sha256"]:
        raise ShortBenchmarkError("short benchmark runner changed during short benchmark")
    if _sha(context["checkpoint_path"]) != context["checkpoint_sha256"]:
        raise ShortBenchmarkError("d40 checkpoint changed during short benchmark")
    if _sha(source) != context["source_manifest_sha256"]:
        raise ShortBenchmarkError("source manifest changed during short benchmark")
    if _sha(context["source_manifest_digest_path"]) != context["source_manifest_digest_sha256"]:
        raise ShortBenchmarkError("source manifest digest sidecar changed during short benchmark")
    materialization_sha256, materialization_files = _materialization_snapshot(
        Path(materialization_dir)
    )
    return {
        "code_manifest_sha256": str(context["code_manifest_sha256"]),
        "code_manifest_digest_sha256": str(context["code_manifest_digest_sha256"]),
        "generator_sha256": str(context["generator_sha256"]),
        "benchmark_sha256": str(context["benchmark_sha256"]),
        "short_benchmark_runner_sha256": str(context["runner_sha256"]),
        "capture_sha256": _sha(capture),
        "materialization_manifest_sha256": materialization_sha256,
        "materialization_files_sha256": materialization_files,
        "source_manifest_sha256": str(context["source_manifest_sha256"]),
        "source_manifest_digest_sha256": str(context["source_manifest_digest_sha256"]),
        "checkpoint_sha256": str(context["checkpoint_sha256"]),
    }


def _receipt_inputs(
    *,
    context: Mapping[str, object],
    snapshot: Mapping[str, object],
    capture_path: Path,
    materialization_dir: Path,
    source_manifest: Path,
) -> dict[str, object]:
    return {
        **dict(snapshot),
        "code_manifest_path": str(Path(context["code_manifest_path"]).resolve()),
        "generator_path": str(Path(context["generator_path"]).resolve()),
        "capture_path": str(Path(capture_path).resolve()),
        "materialization_dir": str(Path(materialization_dir).resolve()),
        "source_manifest_path": str(Path(source_manifest).resolve()),
        "checkpoint_path": str(Path(context["checkpoint_path"]).resolve()),
        "users": USERS,
        "split": TRAIN,
    }


def _guards() -> dict[str, bool]:
    return {
        "training_or_replay_write": False,
        "learner_update": False,
        "episode_training": False,
        "test_split_opened": False,
        "persistent_target_output_created": False,
        "main_network_unchanged": True,
        "main_replay_unchanged": True,
        "sealed_train_inputs_unchanged": True,
    }


def _validate_benchmark_payload(
    payload: Mapping[str, object],
    *,
    case: BenchmarkCase,
    context: Mapping[str, object],
    snapshot: Mapping[str, object],
    capture_path: Path,
    materialization_dir: Path,
    timeout_s: float,
) -> None:
    if payload.get("schema") != BENCHMARK_SCHEMA or payload.get("status") != "BENCHMARK_PASS":
        raise ShortBenchmarkError("short benchmark did not return BENCHMARK_PASS")
    if payload.get("claim_ceiling") != BENCHMARK_CLAIM_CEILING:
        raise ShortBenchmarkError("short benchmark claim ceiling drifted")
    if payload.get("scope") != (
        "C2 repriced OPS-3 selected-pair generation only; no C1 timing, learner, TEST, or efficacy claim"
    ):
        raise ShortBenchmarkError("short benchmark scope drifted")

    inputs = payload.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ShortBenchmarkError("short benchmark inputs are missing")
    expected_paths = {
        "capture": str(Path(capture_path).resolve()),
        "materialization_dir": str(Path(materialization_dir).resolve()),
    }
    for field, expected in expected_paths.items():
        if inputs.get(field) != expected:
            raise ShortBenchmarkError(f"short benchmark {field} binding drifted")
    expected_values = {
        "frozen_generator_sha256": context["generator_sha256"],
        "capture_sha256": snapshot["capture_sha256"],
        "materialization_manifest_sha256": snapshot["materialization_manifest_sha256"],
        "source_manifest_sha256": context["source_manifest_sha256"],
        "checkpoint_sha256": context["checkpoint_sha256"],
        "split": TRAIN,
        "users": USERS,
    }
    for field, expected in expected_values.items():
        if inputs.get(field) != expected:
            raise ShortBenchmarkError(f"short benchmark input hash/guard drifted: {field}")

    selection = payload.get("selection")
    if not isinstance(selection, Mapping):
        raise ShortBenchmarkError("short benchmark selection is missing")
    if selection.get("modes") != [case.mode]:
        raise ShortBenchmarkError("short benchmark mode binding drifted")
    if selection.get("max_step") != MAX_STEP:
        raise ShortBenchmarkError("short benchmark max-step binding drifted")
    if selection.get("full_step_cohort") is not case.full_step_cohort:
        raise ShortBenchmarkError("short benchmark full-step binding drifted")
    expected_anchor_count = case.anchor_count if case.anchor_count is not None else 1
    if selection.get("anchor_count_requested") != expected_anchor_count:
        raise ShortBenchmarkError("short benchmark anchor-count binding drifted")
    rows_by_mode = selection.get("rows_by_mode")
    if not isinstance(rows_by_mode, Mapping) or set(rows_by_mode) != {case.mode}:
        raise ShortBenchmarkError("short benchmark selected rows are missing")
    selected_rows = rows_by_mode[case.mode]
    if not isinstance(selected_rows, list) or not selected_rows:
        raise ShortBenchmarkError("short benchmark selected no rows")
    if case.anchor_count is not None and len(selected_rows) != case.anchor_count:
        raise ShortBenchmarkError("short benchmark selected the wrong row count")
    world = selection.get("world")
    step = selection.get("step")
    if type(world) is not int or world <= 0 or type(step) is not int or not 0 <= step <= MAX_STEP:
        raise ShortBenchmarkError("short benchmark cohort identity is malformed")
    for index, row in enumerate(selected_rows):
        if not isinstance(row, Mapping):
            raise ShortBenchmarkError(f"short benchmark row is malformed: {case.name}/{index}")
        if set(row) != {"anchor_sha256", "focal_user", "candidate_physical_key"}:
            raise ShortBenchmarkError(f"short benchmark row fields drifted: {case.name}/{index}")
        _digest(row["anchor_sha256"], field=f"short benchmark row {case.name}/{index} anchor")
        if type(row["focal_user"]) is not int or not 0 <= row["focal_user"] < USERS:
            raise ShortBenchmarkError(f"short benchmark focal user is malformed: {case.name}/{index}")
        physical_key = row["candidate_physical_key"]
        if (
            not isinstance(physical_key, list)
            or len(physical_key) != 2
            or any(type(value) is not int for value in physical_key)
        ):
            raise ShortBenchmarkError(
                f"short benchmark physical key is malformed: {case.name}/{index}"
            )

    timing = payload.get("timing")
    if not isinstance(timing, Mapping) or timing.get("strict_unit_timeout_s") != round(timeout_s, 6):
        raise ShortBenchmarkError("short benchmark timeout receipt drifted")
    mode_timings = timing.get("modes")
    if not isinstance(mode_timings, Mapping) or set(mode_timings) != {case.mode}:
        raise ShortBenchmarkError("short benchmark mode timing is missing")
    mode_summary = mode_timings.get(case.mode)
    if not isinstance(mode_summary, Mapping):
        raise ShortBenchmarkError("short benchmark mode timing is malformed")
    if mode_summary.get("selected_rows") != len(selected_rows):
        raise ShortBenchmarkError("short benchmark timing row count disagrees")
    if (
        mode_summary.get("selected_unique_anchors") != len(
            {row["anchor_sha256"] for row in selected_rows}
        )
        or mode_summary.get("dataset_rows_verified_in_memory") != len(selected_rows)
        or mode_summary.get("bindings_verified_in_memory") != len(selected_rows)
    ):
        raise ShortBenchmarkError("short benchmark in-memory row verification drifted")
    if (
        type(mode_summary.get("full_route_rows")) is not int
        or mode_summary["full_route_rows"] < len(selected_rows)
    ):
        raise ShortBenchmarkError("short benchmark full-route row count is malformed")
    try:
        elapsed = float(mode_summary["elapsed_s"])
    except (KeyError, TypeError, ValueError) as error:
        raise ShortBenchmarkError("short benchmark elapsed time is malformed") from error
    if not (0.0 <= elapsed < MAX_TIMEOUT_S):
        raise ShortBenchmarkError("short benchmark elapsed time is outside the bound")

    guards = payload.get("guards")
    if not isinstance(guards, Mapping):
        raise ShortBenchmarkError("short benchmark guards are missing")
    expected_guards = _guards()
    if any(guards.get(field) is not expected for field, expected in expected_guards.items()):
        raise ShortBenchmarkError("short benchmark TRAIN-only guard drifted")


def _write_once(path: Path, data: bytes) -> None:
    target = Path(path)
    if target.exists() or target.is_symlink():
        raise ShortBenchmarkError(f"refusing to overwrite short receipt: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        target.unlink(missing_ok=True)
        raise


def _write_receipt(path: Path, payload: Mapping[str, object]) -> str:
    encoded = _canonical(payload)
    _write_once(path, encoded)
    return hashlib.sha256(encoded).hexdigest()


def _command(
    *,
    case: BenchmarkCase,
    python: Path,
    capture_path: Path,
    materialization_dir: Path,
    tle_root: Path,
    prereg: Path,
    source_manifest: Path,
    source_manifest_digest: Path,
    execution_addendum: Path,
    timeout_s: float,
) -> list[str]:
    command = [
        str(python),
        str(BENCHMARK),
        "--capture",
        str(capture_path),
        "--materialization-dir",
        str(materialization_dir),
        "--tle-root",
        str(tle_root),
        "--prereg",
        str(prereg),
        "--manifest",
        str(source_manifest),
        "--manifest-digest",
        str(source_manifest_digest),
        "--execution-addendum",
        str(execution_addendum),
        "--mode",
        case.mode,
        "--users",
        str(USERS),
        "--max-step",
        str(MAX_STEP),
        "--timeout-s",
        str(timeout_s),
    ]
    if case.anchor_count is not None:
        command.extend(("--anchor-count", str(case.anchor_count)))
    if case.full_step_cohort:
        command.append("--full-step-cohort")
    return command


def _run_process(
    command: Sequence[str], *, env: Mapping[str, str], cwd: Path, timeout_s: float
) -> subprocess.CompletedProcess[bytes]:
    """Small seam kept separate so tests never enter the physical runtime."""

    return subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout_s,
    )


def _parse_stdout(stdout: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(
            stdout.decode("ascii"), parse_constant=_reject_constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ShortBenchmarkError("short benchmark stdout is not one ASCII JSON object") from error
    if not isinstance(payload, dict):
        raise ShortBenchmarkError("short benchmark stdout root is not an object")
    return payload


def _error_payload(error: BaseException) -> dict[str, str]:
    return {
        "type": type(error).__name__,
        "message": str(error).replace("\n", " ")[:2000],
    }


def _pass_receipt(
    *,
    case: BenchmarkCase,
    timeout_s: float,
    external_timeout_s: float,
    inputs: Mapping[str, object],
    benchmark_payload: Mapping[str, object],
    elapsed_s: float,
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "status": "SHORT_BENCHMARK_PASS",
        "claim_ceiling": CLAIM_CEILING,
        "case": {
            "name": case.name,
            "mode": case.mode,
            "level": case.level,
            "anchor_count": case.anchor_count,
            "full_step_cohort": case.full_step_cohort,
            "max_step": MAX_STEP,
        },
        "timeout_s": round(timeout_s, 6),
        "external_timeout_s": round(external_timeout_s, 6),
        "elapsed_s": round(elapsed_s, 6),
        "inputs": dict(inputs),
        "benchmark": dict(benchmark_payload),
        "guards": _guards(),
    }


def _failed_receipt(
    *,
    case: BenchmarkCase,
    timeout_s: float,
    external_timeout_s: float,
    inputs: Mapping[str, object],
    error: BaseException,
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "status": "SHORT_BENCHMARK_FAILED",
        "claim_ceiling": CLAIM_CEILING,
        "case": {
            "name": case.name,
            "mode": case.mode,
            "level": case.level,
            "anchor_count": case.anchor_count,
            "full_step_cohort": case.full_step_cohort,
            "max_step": MAX_STEP,
        },
        "timeout_s": round(timeout_s, 6),
        "external_timeout_s": round(external_timeout_s, 6),
        "inputs": dict(inputs),
        "error": _error_payload(error),
        "guards": {**_guards(), "validation_passed": False},
    }


def _blocked_receipt(
    *,
    case: BenchmarkCase,
    timeout_s: float,
    external_timeout_s: float,
    inputs: Mapping[str, object],
    reason: str,
) -> dict[str, object]:
    return _failed_receipt(
        case=case,
        timeout_s=timeout_s,
        external_timeout_s=external_timeout_s,
        inputs=inputs,
        error=ShortBenchmarkError(reason),
    ) | {"status": "SHORT_BENCHMARK_BLOCKED"}


def _validate_case_metadata(
    payload: Mapping[str, object], *, case: BenchmarkCase, timeout_s: float
) -> None:
    if payload.get("schema") != SCHEMA or payload.get("status") != "SHORT_BENCHMARK_PASS":
        raise ShortBenchmarkError("short receipt is not PASS")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise ShortBenchmarkError("short receipt claim ceiling drifted")
    if payload.get("timeout_s") != round(timeout_s, 6):
        raise ShortBenchmarkError("short receipt timeout drifted")
    expected_external_timeout = min(
        timeout_s + EXTERNAL_GRACE_S, MAX_TIMEOUT_S - 1e-3
    )
    if payload.get("external_timeout_s") != round(expected_external_timeout, 6):
        raise ShortBenchmarkError("short receipt external timeout drifted")
    try:
        elapsed_s = float(payload["elapsed_s"])
    except (KeyError, TypeError, ValueError) as error:
        raise ShortBenchmarkError("short receipt elapsed time is malformed") from error
    if not (0.0 <= elapsed_s < MAX_TIMEOUT_S):
        raise ShortBenchmarkError("short receipt elapsed time is outside the bound")
    case_payload = payload.get("case")
    if not isinstance(case_payload, Mapping):
        raise ShortBenchmarkError("short receipt case is missing")
    expected = {
        "name": case.name,
        "mode": case.mode,
        "level": case.level,
        "anchor_count": case.anchor_count,
        "full_step_cohort": case.full_step_cohort,
        "max_step": MAX_STEP,
    }
    if dict(case_payload) != expected:
        raise ShortBenchmarkError(f"short receipt case metadata drifted: {case.name}")
    if payload.get("guards") != _guards():
        raise ShortBenchmarkError(f"short receipt TRAIN-only guards drifted: {case.name}")


def validate_receipt(
    receipt_path: Path,
    *,
    case: BenchmarkCase,
    capture_path: Path,
    materialization_dir: Path,
    source_manifest: Path,
    code_manifest: Path,
    code_manifest_digest: Path,
    timeout_s: float,
) -> dict[str, Any]:
    """Recompute all bound hashes and validate one immutable PASS receipt."""

    _validate_timeout(timeout_s)
    context = _load_code_context(code_manifest, code_manifest_digest)
    if Path(source_manifest).resolve() != context["source_manifest_path"]:
        raise ShortBenchmarkError("receipt source manifest path is not the current R6 binding")
    snapshot = _input_snapshot(
        context=context,
        capture_path=capture_path,
        materialization_dir=materialization_dir,
        source_manifest=source_manifest,
    )
    payload = _read_canonical(Path(receipt_path))
    _validate_case_metadata(payload, case=case, timeout_s=timeout_s)
    inputs = payload.get("inputs")
    expected_inputs = _receipt_inputs(
        context=context,
        snapshot=snapshot,
        capture_path=capture_path,
        materialization_dir=materialization_dir,
        source_manifest=source_manifest,
    )
    if inputs != expected_inputs:
        raise ShortBenchmarkError(f"short receipt input hash/path drifted: {case.name}")
    benchmark_payload = payload.get("benchmark")
    if not isinstance(benchmark_payload, Mapping):
        raise ShortBenchmarkError(f"short receipt benchmark payload is missing: {case.name}")
    _validate_benchmark_payload(
        benchmark_payload,
        case=case,
        context=context,
        snapshot=snapshot,
        capture_path=capture_path,
        materialization_dir=materialization_dir,
        timeout_s=timeout_s,
    )
    return payload


def validate_all(
    output: Path,
    *,
    capture_path: Path,
    materialization_dir: Path,
    source_manifest: Path,
    code_manifest: Path,
    code_manifest_digest: Path,
    timeout_s: float,
) -> dict[str, Any]:
    """Validate the complete six-receipt gradient and its summary."""

    _validate_timeout(timeout_s)
    root = Path(output).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ShortBenchmarkError(f"short benchmark receipt root is missing: {root}")
    summary_path = root / "SUMMARY.json"
    summary = _read_canonical(summary_path)
    if summary.get("schema") != SUMMARY_SCHEMA or summary.get("status") != "SHORT_BENCHMARKS_PASS":
        raise ShortBenchmarkError("short benchmark summary is not PASS")
    cases_payload = summary.get("cases")
    if not isinstance(cases_payload, Mapping):
        raise ShortBenchmarkError("short benchmark summary cases are missing")
    cases = benchmark_cases()
    if set(cases_payload) != {case.name for case in cases}:
        raise ShortBenchmarkError("short benchmark summary case set drifted")
    expected_names = {f"{case.name}.json" for case in cases}
    entries = list(root.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in entries):
        raise ShortBenchmarkError(
            "short benchmark receipt closure contains a non-regular entry"
        )
    actual_names = {path.name for path in entries} - {"SUMMARY.json"}
    if actual_names != expected_names:
        raise ShortBenchmarkError(
            f"short benchmark receipt closure drifted: extra={sorted(actual_names - expected_names)}, "
            f"missing={sorted(expected_names - actual_names)}"
        )
    context = _load_code_context(code_manifest, code_manifest_digest)
    snapshot = _input_snapshot(
        context=context,
        capture_path=capture_path,
        materialization_dir=materialization_dir,
        source_manifest=source_manifest,
    )
    expected_inputs = _receipt_inputs(
        context=context,
        snapshot=snapshot,
        capture_path=capture_path,
        materialization_dir=materialization_dir,
        source_manifest=source_manifest,
    )
    if (
        summary.get("inputs") != expected_inputs
        or summary.get("users") != USERS
        or summary.get("split") != TRAIN
        or summary.get("timeout_s") != round(timeout_s, 6)
        or summary.get("external_timeout_s")
        != round(min(timeout_s + EXTERNAL_GRACE_S, MAX_TIMEOUT_S - 1e-3), 6)
    ):
        raise ShortBenchmarkError("short benchmark summary input binding drifted")
    if summary.get("claim_ceiling") != CLAIM_CEILING or summary.get("guards") != _guards():
        raise ShortBenchmarkError("short benchmark summary guard drifted")
    for case in cases:
        name = f"{case.name}.json"
        receipt_path = root / name
        receipt = validate_receipt(
            receipt_path,
            case=case,
            capture_path=capture_path,
            materialization_dir=materialization_dir,
            source_manifest=source_manifest,
            code_manifest=code_manifest,
            code_manifest_digest=code_manifest_digest,
            timeout_s=timeout_s,
        )
        declared = cases_payload.get(case.name)
        if not isinstance(declared, Mapping):
            raise ShortBenchmarkError(f"short benchmark summary omits case: {case.name}")
        if declared.get("status") != "SHORT_BENCHMARK_PASS":
            raise ShortBenchmarkError(f"short benchmark summary case is not PASS: {case.name}")
        if declared.get("receipt_sha256") != _sha(receipt_path):
            raise ShortBenchmarkError(f"short benchmark summary receipt hash drifted: {case.name}")
        if receipt.get("case", {}).get("name") != case.name:
            raise ShortBenchmarkError(f"short benchmark receipt name drifted: {case.name}")
    return summary


def _validate_timeout(timeout_s: float) -> None:
    if not isinstance(timeout_s, (int, float)) or isinstance(timeout_s, bool):
        raise ShortBenchmarkError("short benchmark timeout must be numeric")
    try:
        finite = math.isfinite(float(timeout_s))
    except (OverflowError, ValueError):
        finite = False
    if not finite:
        raise ShortBenchmarkError("short benchmark timeout must be finite")
    if timeout_s <= 0.0 or timeout_s >= MAX_TIMEOUT_S:
        raise ShortBenchmarkError(
            f"short benchmark timeout must be strictly between 0 and {MAX_TIMEOUT_S:g}s"
        )


def run_all(
    *,
    capture_path: Path,
    materialization_dir: Path,
    tle_root: Path,
    prereg: Path,
    source_manifest: Path,
    source_manifest_digest: Path,
    execution_addendum: Path,
    code_manifest: Path,
    code_manifest_digest: Path,
    output: Path,
    python: Path = Path(sys.executable),
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict[str, object]:
    """Run all six cases and write terminal receipts, stopping on input drift."""

    _validate_timeout(timeout_s)
    external_timeout_s = min(timeout_s + EXTERNAL_GRACE_S, MAX_TIMEOUT_S - 1e-3)
    context = _load_code_context(code_manifest, code_manifest_digest)
    if Path(source_manifest).resolve() != context["source_manifest_path"]:
        raise ShortBenchmarkError("source manifest is not the current R6 binding")
    if Path(source_manifest_digest).resolve() != context["source_manifest_digest_path"]:
        raise ShortBenchmarkError("source manifest digest is not the current R6 binding")
    baseline = _input_snapshot(
        context=context,
        capture_path=capture_path,
        materialization_dir=materialization_dir,
        source_manifest=source_manifest,
    )
    output_root = Path(output).resolve()
    if output_root.exists() or output_root.is_symlink():
        raise ShortBenchmarkError(f"refusing to overwrite short benchmark root: {output_root}")
    output_root.mkdir(parents=True)
    inputs = _receipt_inputs(
        context=context,
        snapshot=baseline,
        capture_path=capture_path,
        materialization_dir=materialization_dir,
        source_manifest=source_manifest,
    )
    env = dict(os.environ)
    env.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    case_records: dict[str, dict[str, object]] = {}
    failed = False
    stop_after_drift = False
    for index, case in enumerate(benchmark_cases()):
        receipt_path = output_root / f"{case.name}.json"
        if stop_after_drift:
            receipt = _blocked_receipt(
                case=case,
                timeout_s=timeout_s,
                external_timeout_s=external_timeout_s,
                inputs=inputs,
                reason="blocked after bound input drift in an earlier case",
            )
            receipt_sha256 = _write_receipt(receipt_path, receipt)
            case_records[case.name] = {
                "mode": case.mode,
                "level": case.level,
                "status": receipt["status"],
                "receipt_sha256": receipt_sha256,
            }
            failed = True
            continue

        started = time.perf_counter()
        before = baseline
        try:
            command = _command(
                case=case,
                python=Path(python),
                capture_path=Path(capture_path),
                materialization_dir=Path(materialization_dir),
                tle_root=Path(tle_root),
                prereg=Path(prereg),
                source_manifest=Path(source_manifest),
                source_manifest_digest=Path(source_manifest_digest),
                execution_addendum=Path(execution_addendum),
                timeout_s=timeout_s,
            )
            completed = _run_process(
                command,
                env=env,
                cwd=REPO,
                timeout_s=external_timeout_s,
            )
            after = _input_snapshot(
                context=context,
                capture_path=capture_path,
                materialization_dir=materialization_dir,
                source_manifest=source_manifest,
            )
            if after != before:
                raise ShortBenchmarkError("bound input hashes changed during short benchmark")
            if completed.returncode != 0:
                stderr = completed.stderr.decode("utf-8", errors="replace").strip()
                raise ShortBenchmarkError(
                    f"{case.name} benchmark exited {completed.returncode}: {stderr[-1200:]}"
                )
            benchmark_payload = _parse_stdout(completed.stdout)
            _validate_benchmark_payload(
                benchmark_payload,
                case=case,
                context=context,
                snapshot=after,
                capture_path=capture_path,
                materialization_dir=materialization_dir,
                timeout_s=timeout_s,
            )
            receipt = _pass_receipt(
                case=case,
                timeout_s=timeout_s,
                external_timeout_s=external_timeout_s,
                inputs=inputs,
                benchmark_payload=benchmark_payload,
                elapsed_s=time.perf_counter() - started,
            )
        except subprocess.TimeoutExpired as error:
            receipt = _failed_receipt(
                case=case,
                timeout_s=timeout_s,
                external_timeout_s=external_timeout_s,
                inputs=inputs,
                error=ShortBenchmarkError(
                    f"{case.name} exceeded external timeout {external_timeout_s:.3f}s"
                ),
            )
            failed = True
        except Exception as error:
            receipt = _failed_receipt(
                case=case,
                timeout_s=timeout_s,
                external_timeout_s=external_timeout_s,
                inputs=inputs,
                error=error,
            )
            failed = True
            if "hash" in str(error).lower() or "input" in str(error).lower():
                stop_after_drift = True
        receipt_sha256 = _write_receipt(receipt_path, receipt)
        case_records[case.name] = {
            "mode": case.mode,
            "level": case.level,
            "status": receipt["status"],
            "receipt_sha256": receipt_sha256,
        }
        if receipt["status"] != "SHORT_BENCHMARK_PASS":
            failed = True

        # Recheck the same baseline before admitting another case.  A changed
        # source must never become the next case's new authority.
        if not stop_after_drift:
            try:
                current_snapshot = _input_snapshot(
                    context=context,
                    capture_path=capture_path,
                    materialization_dir=materialization_dir,
                    source_manifest=source_manifest,
                )
                if current_snapshot != before:
                    stop_after_drift = True
                    failed = True
            except Exception:
                stop_after_drift = True
                failed = True

    try:
        final_snapshot = _input_snapshot(
            context=context,
            capture_path=capture_path,
            materialization_dir=materialization_dir,
            source_manifest=source_manifest,
        )
        if final_snapshot != baseline:
            failed = True
    except Exception:
        failed = True

    status = "SHORT_BENCHMARKS_PASS" if not failed and all(
        record["status"] == "SHORT_BENCHMARK_PASS" for record in case_records.values()
    ) else "SHORT_BENCHMARKS_FAILED"
    summary = {
        "schema": SUMMARY_SCHEMA,
        "status": status,
        "claim_ceiling": CLAIM_CEILING,
        "users": USERS,
        "split": TRAIN,
        "timeout_s": round(timeout_s, 6),
        "external_timeout_s": round(external_timeout_s, 6),
        "inputs": inputs,
        "cases": {name: case_records[name] for name in sorted(case_records)},
        "guards": _guards(),
    }
    _write_receipt(output_root / "SUMMARY.json", summary)
    if status == "SHORT_BENCHMARKS_PASS":
        validate_all(
            output_root,
            capture_path=capture_path,
            materialization_dir=materialization_dir,
            source_manifest=source_manifest,
            code_manifest=code_manifest,
            code_manifest_digest=code_manifest_digest,
            timeout_s=timeout_s,
        )
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--materialization-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-digest", type=Path, required=True)
    parser.add_argument("--execution-addendum", type=Path, required=True)
    parser.add_argument("--code-manifest", type=Path, required=True)
    parser.add_argument("--code-manifest-digest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help="strict per-case timeout, strictly below 600 seconds",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="validate an existing complete receipt root without running probes",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.validate:
            summary = validate_all(
                args.output,
                capture_path=args.capture,
                materialization_dir=args.materialization_dir,
                source_manifest=args.manifest,
                code_manifest=args.code_manifest,
                code_manifest_digest=args.code_manifest_digest,
                timeout_s=args.timeout_s,
            )
        else:
            summary = run_all(
                capture_path=args.capture,
                materialization_dir=args.materialization_dir,
                tle_root=args.tle_root,
                prereg=args.prereg,
                source_manifest=args.manifest,
                source_manifest_digest=args.manifest_digest,
                execution_addendum=args.execution_addendum,
                code_manifest=args.code_manifest,
                code_manifest_digest=args.code_manifest_digest,
                output=args.output,
                python=args.python,
                timeout_s=args.timeout_s,
            )
    except Exception as error:
        print(f"V023_C1C2_SHORT_BENCHMARK_BLOCKED: {error}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "SHORT_BENCHMARKS_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
