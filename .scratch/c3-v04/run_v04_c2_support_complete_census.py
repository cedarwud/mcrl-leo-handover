#!/usr/bin/env python3
"""Prepare and evaluate the V0.4 support-complete C2 census.

This runner is intentionally an import-safe, two-phase boundary:

``prepare``
    consumes a *predecision topology scanner* and seals the first three
    eligible worlds from the fixed design-only seed order.  It constructs no
    counterfactual branch and never asks a trainer, Q head, or forecast
    backend to evaluate an action.

``phase-a`` (also exposed as ``generate``)
    authenticates a prepared artifact and consumes already materialized
    Main-continuation row receipts.  It retains all 324 scheduled siblings,
    including row failures and support-expired rows, and computes the frozen
    G-S/G-R/G-V gates plus the three old Q2 rung-10 rankings per cluster.

The real TLE/Main scanner and the real matched-fork materializer are loaded
only by the server-facing CLI.  Contract tests can exercise the data layer
without torch, the simulator, training, TEST, or held-out EE evaluation.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import sys
import tempfile
import time
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (HERE, REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402
from mcrl.runtime.ee_axis_v04_c2_sibling_schedule import (  # noqa: E402
    C2_V04_ROW_FAILURE,
    C2_V04_ROW_READY,
    C2_V04_ROW_SUPPORT_EXPIRED,
    C2_V04_SCHEDULE_SCHEMA,
    C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
    C2V04AnchorSchedule,
    C2V04SiblingRow,
    C2V04SiblingScheduleContractError,
    C2V04SupportCompleteSchedule,
    build_c2_v04_support_complete_schedule,
    read_c2_v04_support_complete_schedule,
    write_c2_v04_support_complete_schedule,
)


# Frozen preregistration constants -----------------------------------------

C2_V04_CENSUS_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-census-v1"
C2_V04_PREPARE_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-prepare-v1"
C2_V04_PREPARE_ARTIFACT_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-prepare-artifact-v1"
)
C2_V04_PHASE_A_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-phase-a-v1"
C2_V04_PHASE_A_ROW_SCHEMA = (
    "multi-catfish-mcrl-v04-c2-support-complete-phase-a-row-v1"
)

DESIGN_ONLY_SOURCE_SEEDS = tuple(range(2026092801, 2026092811))
Q2_INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
SELECTED_WORLDS = 3
FOCAL_USERS_PER_WORLD = 4
SIBLINGS_PER_CLUSTER = NUM_ACTIONS - 1
EXPECTED_CLUSTERS = SELECTED_WORLDS * FOCAL_USERS_PER_WORLD
EXPECTED_SIBLINGS = EXPECTED_CLUSTERS * SIBLINGS_PER_CLUSTER
KAPPA_BITS = float.fromhex("0x1.2cea89d260f2ap+33")

CLAIM_CEILING = "FRESH_TRAIN_DESIGN_PROBE_ONLY_NO_TRAINING_NO_TEST_NO_EE_EFFICACY"
V04_PHASE_A_DECISION = "AUTHORIZE_PHASE_B_CONTINUATION_PROBE"
V04_POLICY_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-policy-v1"
V04_SOURCE_MANIFEST_SCHEMA = "multi-catfish-mcrl-v04-c2-support-complete-source-manifest-v1"
DEFAULT_MAIN_CHECKPOINT_DIR = REPO / "artifacts" / "training-2026-08-25-rerun01" / "main"
DEFAULT_CALIBRATION_RECEIPT = (
    REPO
    / "artifacts"
    / "multi-catfish-v03-three-route-real-smoke-20260831"
    / "receipt.json"
)


class C2V04CensusRunnerError(RuntimeError):
    """The V0.4 census runner or its sealed inputs failed closed."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii") + b"\n"
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise C2V04CensusRunnerError(
            "payload is not finite canonical JSON"
        ) from error


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2V04CensusRunnerError(f"{field} must be lowercase SHA-256")
    return value


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise C2V04CensusRunnerError(
            f"{field} must be a nonnegative exact integer"
        )
    return value


def _action(value: object, *, field: str) -> int:
    action = _exact_nonnegative_int(value, field=field)
    if action >= NUM_ACTIONS:
        raise C2V04CensusRunnerError(
            f"{field} must lie in [0, {NUM_ACTIONS})"
        )
    return action


def _physical_key(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise C2V04CensusRunnerError(f"{field} must be a two-integer physical key")
    return (
        _exact_nonnegative_int(value[0], field=f"{field}[0]"),
        _exact_nonnegative_int(value[1], field=f"{field}[1]"),
    )


def _bool_mask(value: object, *, field: str) -> tuple[bool, ...]:
    if not isinstance(value, (tuple, list)):
        raise C2V04CensusRunnerError(f"{field} must be a Boolean sequence")
    result = tuple(value)
    if len(result) != NUM_ACTIONS or any(type(item) is not bool for item in result):
        raise C2V04CensusRunnerError(
            f"{field} must contain exactly {NUM_ACTIONS} exact Booleans"
        )
    return result


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise C2V04CensusRunnerError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise C2V04CensusRunnerError(f"{field} must be finite")
    return result


def _json_mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise C2V04CensusRunnerError(f"{field} must be a mapping")
    return value


def _status(value: object) -> str:
    if value == "row_failure":
        value = C2_V04_ROW_FAILURE
    elif value == "support_expired":
        value = C2_V04_ROW_SUPPORT_EXPIRED
    if value not in {C2_V04_ROW_READY, C2_V04_ROW_FAILURE, C2_V04_ROW_SUPPORT_EXPIRED}:
        raise C2V04CensusRunnerError(
            "row_status must be ready, row-failure, or support-expired"
        )
    return str(value)


def _status_code(value: object, *, status: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise C2V04CensusRunnerError("failure_code must be a nonempty string")
    if status == C2_V04_ROW_READY:
        raise C2V04CensusRunnerError("ready row cannot carry failure_code")
    return value


def _raw_trace_matrix(
    value: object,
    *,
    field: str,
    boolean: bool = False,
) -> tuple[tuple[float | bool, ...], ...]:
    """Validate one persisted four-offset raw trace matrix.

    Phase-A keeps the full physical traces in its receipt.  This helper is
    deliberately independent of the simulator so a verifier can recompute
    the downstream delivered-bit and surplus arithmetic from JSON alone.
    """

    if not isinstance(value, (tuple, list)) or len(value) != 4:
        raise C2V04CensusRunnerError(f"{field} must contain four offsets")
    rows: list[tuple[float | bool, ...]] = []
    width: int | None = None
    for offset, raw_row in enumerate(value):
        if not isinstance(raw_row, (tuple, list)) or not raw_row:
            raise C2V04CensusRunnerError(f"{field}[{offset}] is malformed")
        current: list[float | bool] = []
        for index, item in enumerate(raw_row):
            if boolean:
                if type(item) is not bool:
                    raise C2V04CensusRunnerError(
                        f"{field}[{offset}][{index}] must be Boolean"
                    )
                current.append(item)
            else:
                current.append(_finite(item, field=f"{field}[{offset}][{index}]"))
        if width is None:
            width = len(current)
        elif len(current) != width:
            raise C2V04CensusRunnerError(f"{field} user width changes across offsets")
        rows.append(tuple(current))
    return tuple(rows)


def _validate_raw_trace(
    sibling: C2V04SiblingRow,
    *,
    status: str,
    zeta2: float | None,
    delivered: float | None,
    raw_trace: Mapping[str, object],
) -> None:
    """Recompute Phase-A metrics from persisted rate/power/served traces."""

    required = {
        "reference_rates_bps",
        "candidate_rates_bps",
        "reference_system_power_w",
        "candidate_system_power_w",
        "reference_served",
        "candidate_served",
        "lambda_bits_per_j",
        "interval_s",
        "offset_surplus_bits",
    }
    missing = sorted(required - set(raw_trace))
    if missing:
        raise C2V04CensusRunnerError(
            "raw_trace is missing required physical fields: " + ", ".join(missing)
        )
    reference_rates = _raw_trace_matrix(
        raw_trace["reference_rates_bps"], field="raw_trace.reference_rates_bps"
    )
    candidate_rates = _raw_trace_matrix(
        raw_trace["candidate_rates_bps"], field="raw_trace.candidate_rates_bps"
    )
    reference_served = _raw_trace_matrix(
        raw_trace["reference_served"],
        field="raw_trace.reference_served",
        boolean=True,
    )
    candidate_served = _raw_trace_matrix(
        raw_trace["candidate_served"],
        field="raw_trace.candidate_served",
        boolean=True,
    )
    if (
        len(reference_rates) != len(candidate_rates)
        or len(reference_rates) != len(reference_served)
        or len(reference_rates) != len(candidate_served)
        or any(
            len(left) != len(right)
            for left, right in zip(reference_rates, candidate_rates, strict=True)
        )
        or any(
            len(left) != len(right)
            for left, right in zip(reference_rates, reference_served, strict=True)
        )
        or any(
            len(left) != len(right)
            for left, right in zip(reference_rates, candidate_served, strict=True)
        )
    ):
        raise C2V04CensusRunnerError("raw_trace rate/served axes disagree")
    if any(any(float(value) < 0.0 for value in row) for row in reference_rates + candidate_rates):
        raise C2V04CensusRunnerError("raw_trace rates must be nonnegative")
    reference_power = tuple(
        _finite(value, field="raw_trace.reference_system_power_w")
        for value in _json_sequence(raw_trace["reference_system_power_w"], field="raw_trace.reference_system_power_w")
    )
    candidate_power = tuple(
        _finite(value, field="raw_trace.candidate_system_power_w")
        for value in _json_sequence(raw_trace["candidate_system_power_w"], field="raw_trace.candidate_system_power_w")
    )
    if len(reference_power) != 4 or len(candidate_power) != 4:
        raise C2V04CensusRunnerError("raw_trace powers must contain four offsets")
    if any(value <= 0.0 for value in reference_power + candidate_power):
        raise C2V04CensusRunnerError("raw_trace powers must be strictly positive")
    interval = _finite(raw_trace["interval_s"], field="raw_trace.interval_s")
    multiplier = _finite(
        raw_trace["lambda_bits_per_j"], field="raw_trace.lambda_bits_per_j"
    )
    if interval <= 0.0 or multiplier <= 0.0:
        raise C2V04CensusRunnerError("raw_trace interval/lambda must be positive")
    supplied_offsets = tuple(
        _finite(value, field="raw_trace.offset_surplus_bits")
        for value in _json_sequence(
            raw_trace["offset_surplus_bits"], field="raw_trace.offset_surplus_bits"
        )
    )
    if len(supplied_offsets) != 3:
        raise C2V04CensusRunnerError("raw_trace offset surplus must contain k=1..3")
    expected_offsets = tuple(
        interval
        * math.fsum(
            float(candidate_rates[offset][user] - reference_rates[offset][user])
            for user in range(len(reference_rates[offset]))
        )
        - multiplier * interval * (candidate_power[offset] - reference_power[offset])
        for offset in range(1, 4)
    )
    if not all(
        math.isclose(left, right, rel_tol=0.0, abs_tol=1e-6)
        for left, right in zip(supplied_offsets, expected_offsets, strict=True)
    ):
        raise C2V04CensusRunnerError("raw_trace offset surplus disagrees with rates/power")
    expected_zeta = math.fsum(expected_offsets)
    if zeta2 is None or not math.isclose(zeta2, expected_zeta, rel_tol=0.0, abs_tol=1e-6):
        raise C2V04CensusRunnerError("zeta2 disagrees with persisted raw trace")
    expected_delivered = interval * math.fsum(
        float(candidate_rates[offset][user] - reference_rates[offset][user])
        for offset in range(1, 4)
        for user in range(len(reference_rates[offset]))
    )
    if delivered is None or not math.isclose(
        delivered, expected_delivered, rel_tol=0.0, abs_tol=1e-6
    ):
        raise C2V04CensusRunnerError(
            "delivered_bit_delta disagrees with downstream raw rates"
        )


def _json_sequence(value: object, *, field: str) -> tuple[object, ...]:
    if not isinstance(value, (tuple, list)):
        raise C2V04CensusRunnerError(f"{field} must be a JSON sequence")
    return tuple(value)


def _production_modules() -> dict[str, Any]:
    """Load the real simulator seams lazily, after contract-only imports.

    Keeping these imports behind the server CLI is intentional: W92 contract
    tests must remain runnable without torch, a checkpoint, or a TLE archive.
    """

    import importlib

    paths = (
        REPO / ".scratch" / "ee-axis-redesign",
        REPO / ".scratch" / "c2-v03",
        REPO / ".scratch" / "catfish-stage0",
    )
    for path in paths:
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return {
        "legacy_source": importlib.import_module("run_v03_e1_fresh_sources"),
        "c2_probe": importlib.import_module(
            "run_c2_v03_deterministic_plumbing_probe"
        ),
        "backend_smoke": importlib.import_module("run_c2_v03_real_backend_smoke"),
        "pair_smoke": importlib.import_module(
            "run_c2_v03_real_temporal_pair_smoke"
        ),
        "loader": importlib.import_module("scripts.run_head_pivotality_probe"),
        "backend": importlib.import_module("c2_temporal_fork_trainer_backend"),
        "neutral": __import__(
            "mcrl.runtime.ee_axis_c2_neutral_source",
            fromlist=["*"],
        ),
        "capture": __import__(
            "mcrl.runtime.ee_axis_temporal_capture",
            fromlist=["*"],
        ),
        "e1_schedule": __import__(
            "mcrl.runtime.ee_axis_e1_c2_schedule",
            fromlist=["*"],
        ),
        "temporal_pairs": __import__(
            "mcrl.runtime.ee_axis_temporal_pairs",
            fromlist=["*"],
        ),
        "ee_axis_state": __import__(
            "mcrl.runtime.ee_axis_state",
            fromlist=["*"],
        ),
        "keyed_fading": __import__(
            "mcrl.env.keyed_fading",
            fromlist=["*"],
        ),
        "training_pipeline": __import__(
            "mcrl.runtime.training_pipeline",
            fromlist=["*"],
        ),
        "forensics": importlib.import_module("run_v04_c2_failure_forensics"),
    }


def _production_source_paths(modules: Mapping[str, Any]) -> tuple[Path, ...]:
    """Return the explicit V0.4 code closure used by both CLI phases."""

    training_pipeline = modules["training_pipeline"]
    paths: list[Path] = [
        Path(__file__),
        REPO / ".scratch" / "ee-axis-redesign" / "run_v03_e1_fresh_sources.py",
        REPO / ".scratch" / "c2-v03" / "c2_temporal_fork_trainer_backend.py",
        REPO / ".scratch" / "c2-v03" / "c2_temporal_fork_chronology.py",
        REPO / ".scratch" / "c2-v03" / "c2_temporal_fork_core.py",
        REPO / ".scratch" / "c2-v03" / "c2_temporal_fork_forecast_adapter.py",
        REPO / ".scratch" / "c2-v03" / "c2_temporal_fork_runtime_adapter.py",
        REPO / ".scratch" / "c2-v03" / "run_c2_v03_real_backend_smoke.py",
        REPO / ".scratch" / "c2-v03" / "run_c2_v03_real_temporal_pair_smoke.py",
        REPO / ".scratch" / "ee-axis-redesign" / "run_c2_v03_deterministic_plumbing_probe.py",
        REPO / ".scratch" / "c3-v04" / "run_v04_c2_failure_forensics.py",
        REPO / "scripts" / "run_head_pivotality_probe.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_v04_c2_sibling_schedule.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_c2_neutral_source.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_capture.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_temporal_pairs.py",
        REPO / "src" / "mcrl" / "runtime" / "ee_axis_e1_c2_schedule.py",
    ]
    paths.extend(Path(path) for path in training_pipeline._default_code_paths())
    for name in ("legacy_source", "c2_probe", "backend_smoke", "pair_smoke", "loader", "backend", "forensics"):
        module_path = getattr(modules[name], "__file__", None)
        if module_path:
            paths.append(Path(module_path))
    unique = tuple(sorted({path.resolve() for path in paths}, key=lambda value: str(value)))
    missing = [path for path in unique if path.is_symlink() or not path.is_file()]
    if missing:
        raise C2V04CensusRunnerError(
            "V0.4 source manifest has missing/non-regular files: "
            + ", ".join(str(path) for path in missing)
        )
    return unique


def _production_source_manifest(modules: Mapping[str, Any]) -> dict[str, object]:
    files = [
        {
            "path": path.relative_to(REPO).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in _production_source_paths(modules)
    ]
    body = {"schema": V04_SOURCE_MANIFEST_SCHEMA, "files": files}
    return body | {"source_manifest_sha256": _canonical_sha256(body)}


def _production_policy_sha256(modules: Mapping[str, Any]) -> str:
    backend = modules["backend"]
    temporal = modules["temporal_pairs"]
    return _canonical_sha256(
        {
            "schema": V04_POLICY_SCHEMA,
            "source_rule": C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
            "c2_policy_version": temporal.C2_POLICY_VERSION,
            "release_grammar": temporal.C2_POLICY_VERSION,
            "compositor_version": backend.POLICY_COMPOSITOR_VERSION,
            "forecast_schema": backend.FORECAST_SCHEMA,
            "fading_mode": "keyed-branch-independent-v1",
        }
    )


def _production_calibration(modules: Mapping[str, Any]) -> tuple[float, float, str]:
    """Read the existing frozen calibration receipt, without recalibrating."""

    legacy = modules["legacy_source"]
    path = Path(getattr(legacy, "CALIBRATION_RECEIPT", DEFAULT_CALIBRATION_RECEIPT))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        calibration = payload["temporal_source_receipt"]["calibration"]
        multiplier = float(calibration["lambda_bits_per_j"])
        interval = float(calibration["interval_s"])
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise C2V04CensusRunnerError("frozen C2 calibration receipt is malformed") from error
    if not math.isfinite(multiplier) or multiplier <= 0.0 or not math.isfinite(interval) or interval <= 0.0:
        raise C2V04CensusRunnerError("frozen C2 calibration is not positive finite")
    return multiplier, interval, hashlib.sha256(path.read_bytes()).hexdigest()


def _production_main_context(
    *,
    modules: Mapping[str, Any],
    prereg_path: Path,
    tle_root: Path,
    temporary: Path,
) -> dict[str, Any]:
    from mcrl.runtime.prereg import read_prereg

    record = read_prereg(prereg_path)
    archive = modules["c2_probe"]._frozen_archive(
        record, tle_root, temporary / "frozen-tle"
    )
    legacy = modules["legacy_source"]
    loader = modules["loader"]
    trainer, checkpoint = loader._verify_and_load_trainer(
        record,
        archive,
        run_dir=Path(getattr(legacy, "BASE_CHECKPOINT_DIR", DEFAULT_MAIN_CHECKPOINT_DIR)),
        users=100,
    )
    training_pipeline = modules["training_pipeline"]
    checkpoint_sha256 = _digest(
        checkpoint.get("checkpoint_sha256"), field="checkpoint_sha256"
    )
    environment_source_sha256 = _digest(
        training_pipeline._code_sha256(training_pipeline._default_code_paths()),
        field="environment_source_sha256",
    )
    reward_path = REPO / "src" / "mcrl" / "env" / "step.py"
    reward_source_sha256 = hashlib.sha256(reward_path.read_bytes()).hexdigest()
    source_manifest = _production_source_manifest(modules)
    source_manifest_sha256 = _digest(
        source_manifest["source_manifest_sha256"], field="source_manifest_sha256"
    )
    return {
        "record": record,
        "archive": archive,
        "trainer": trainer,
        "checkpoint": checkpoint,
        "checkpoint_sha256": checkpoint_sha256,
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "source_manifest": source_manifest,
        "source_manifest_sha256": source_manifest_sha256,
        "policy_sha256": _production_policy_sha256(modules),
    }


def _write_once_json(path: Path, payload: object) -> str:
    """Write one canonical JSON file without replacing an existing file."""

    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite V0.4 artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(payload)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        # ``link`` gives the write-once boundary a no-clobber race outcome.
        os.link(temporary, path)
    except FileExistsError as error:
        raise FileExistsError(f"refusing to overwrite V0.4 artifact: {path}") from error
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _read_canonical_json(path: Path) -> tuple[dict[str, object], str]:
    """Read one regular canonical JSON object and return its file digest."""

    if path.is_symlink() or not path.is_file():
        raise C2V04CensusRunnerError(f"V0.4 artifact is missing or not regular: {path}")
    encoded = path.read_bytes()
    try:
        payload = json.loads(
            encoded.decode("ascii"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise C2V04CensusRunnerError(f"V0.4 artifact is invalid JSON: {path}") from error
    if not isinstance(payload, dict) or encoded != _canonical_bytes(payload):
        raise C2V04CensusRunnerError(f"V0.4 artifact is not canonical JSON: {path}")
    return payload, hashlib.sha256(encoded).hexdigest()


def _failure_text(error: BaseException) -> str:
    """Make a deterministic, nonempty row failure label from an exception."""

    detail = " ".join(str(error).split())
    if not detail:
        detail = "unspecified"
    return f"{type(error).__name__}:{detail}"


def _average_percentile(values: Sequence[float]) -> dict[int, float]:
    ordered = sorted((float(value), index) for index, value in enumerate(values))
    result: dict[int, float] = {}
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end][0] == ordered[position][0]:
            end += 1
        # Use a stable 0..1 average rank; ties receive their average rank.
        percentile = ((position + 1) + end) / (2.0 * len(ordered))
        for _, index in ordered[position:end]:
            result[index] = percentile
        position = end
    return result


def _production_ee_axis_anchor(
    *,
    modules: Mapping[str, Any],
    wrapped: Any,
    observation: Any,
    focal_user: int,
) -> tuple[Any, Any]:
    """Return the authoritative 228-D causal state and 28-D mask.

    ``C2TemporalForkTrainerBackend._anchor_payload`` intentionally preserves
    the simulator's legacy 112-D observation for physical replay lineage.  It
    is therefore not a learner-state authority.  Every heuristic and frozen
    Q2 read in this runner must instead use the same EE-axis encoder as the
    deployed three-head policy.
    """

    import numpy as np

    if type(focal_user) is not int or focal_user < 0:
        raise C2V04CensusRunnerError("EE-axis anchor focal user is invalid")
    try:
        encoded = modules["ee_axis_state"].encode_ee_axis_state(
            wrapped.environment,
            observation,
        )
        state = np.asarray(encoded.state_matrix[focal_user], dtype=np.float32)
        mask = np.asarray(encoded.action_masks[focal_user], dtype=np.bool_)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        raise C2V04CensusRunnerError(
            "failed to encode the causal EE-axis anchor"
        ) from error
    if state.shape != (228,) or mask.shape != (NUM_ACTIONS,):
        raise C2V04CensusRunnerError(
            "encoded EE-axis anchor must have 228 state and 28 mask entries"
        )
    if not np.all(np.isfinite(state)):
        raise C2V04CensusRunnerError("encoded EE-axis anchor is nonfinite")
    return state, mask


def _predecision_heuristic_scores(
    *,
    observation: Any,
    state_row: Sequence[float],
    focal_user: int,
    candidate_actions: Sequence[int],
) -> tuple[float, ...]:
    """Compute and seal the preregistered, outcome-blind h(a) diagnostic."""

    import numpy as np

    sinr = np.asarray(getattr(observation, "candidate_sinr", None), dtype=np.float64)
    if sinr.ndim != 2 or sinr.shape[1] != NUM_ACTIONS:
        raise C2V04CensusRunnerError(
            "predecision heuristic requires candidate_sinr shape (U,28)"
        )
    state = np.asarray(state_row, dtype=np.float64)
    base_dim = 112
    load_start = base_dim
    power_start = base_dim + 3 * NUM_ACTIONS
    if state.shape != (base_dim + 4 * NUM_ACTIONS + 4,):
        raise C2V04CensusRunnerError(
            "predecision heuristic requires the 228-D causal state"
        )
    actions = tuple(int(action) for action in candidate_actions)
    # The scores are rank-only diagnostics.  All 28 legal entries, including
    # the Main reference, define each within-cluster percentile distribution.
    # The caller supplies candidates in the same sorted (physical, action)
    # order that enters the sealed V0.4 anchor.
    legal = np.flatnonzero(np.ones(NUM_ACTIONS, dtype=bool)).tolist()
    if type(focal_user) is not int or not 0 <= focal_user < sinr.shape[0]:
        raise C2V04CensusRunnerError("predecision heuristic focal user is out of range")
    log_sinr = np.log1p(np.maximum(sinr[focal_user, :], 0.0))
    load = state[load_start : load_start + NUM_ACTIONS]
    power = state[power_start : power_start + NUM_ACTIONS]
    if not np.all(np.isfinite(log_sinr)) or not np.all(np.isfinite(load)) or not np.all(np.isfinite(power)):
        raise C2V04CensusRunnerError("predecision heuristic inputs are nonfinite")
    sinr_rank = _average_percentile([float(log_sinr[action]) for action in legal])
    load_rank = _average_percentile([float(load[action]) for action in legal])
    power_rank = _average_percentile([float(power[action]) for action in legal])
    scores = tuple(
        sinr_rank[action] - load_rank[action] - power_rank[action]
        for action in actions
    )
    return tuple(_finite(value, field="predecision_heuristic_score") for value in scores)


def _real_seed_topology(
    *,
    source_seed: int,
    modules: Mapping[str, Any],
    context: Mapping[str, Any],
) -> tuple[C2V04TopologyAnchor, ...]:
    """Scan one frozen Main/TLE world without running any forecast.

    The scanner deliberately constructs every candidate through
    ``prepare_one_candidate`` only.  That call seals the physical source
    identity and chronology gate, but it does not call ``run_forecast``.  A
    focal user enters the topology only when its contemporaneous table has
    all 28 legal actions and every one of the 27 physical siblings is
    executable under the V0.4 source rule.
    """

    import numpy as np

    loader = modules["loader"]
    backend_smoke = modules["backend_smoke"]
    pair_smoke = modules["pair_smoke"]
    backend = modules["backend"]
    neutral = modules["neutral"]
    e1_schedule = modules["e1_schedule"]
    keyed_fading = modules["keyed_fading"]
    core = pair_smoke.core
    archive = context["archive"]
    trainer = context["trainer"]
    wrapped = loader._make_environment(archive, users=100)
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
        int(source_seed)
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    steps_per_episode = int(wrapped.environment.driver.config.steps_per_episode)
    network_before = backend_smoke._network_snapshot(trainer)
    replay_before = len(trainer.replay)
    discovered: list[C2V04TopologyAnchor] = []

    while not bool(getattr(observation, "done", False)):
        main_actions, main_physical = backend_smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        step_index = int(observation.step_index)
        departures = tuple(
            sorted(
                int(value)
                for value in pair_smoke._departure_users(wrapped, main_physical)
            )
        )
        remaining = steps_per_episode - step_index
        if (
            step_index >= 1
            and departures
            and remaining >= int(core.HOLD_STEPS) + 1
        ):
            world_anchor_sha256 = e1_schedule.e1_c2_world_anchor_sha256(
                source_seed=int(source_seed), anchor_step=step_index
            )
            focal_records: list[C2V04TopologyFocal] = []
            for focal_user in departures:
                try:
                    reference_action = int(main_actions[focal_user])
                    reference_key = main_physical[focal_user]
                    if reference_key is None:
                        raise C2V04CensusRunnerError(
                            "departure focal has no physical Main reference"
                        )
                    reference_key = (int(reference_key[0]), int(reference_key[1]))
                    service = backend.C2TemporalForkTrainerBackend(
                        wrapped=wrapped,
                        states=states,
                        masks=masks,
                        observation=observation,
                        env_rng=env_rng,
                        trainer=trainer,
                        checkpoint_sha256=context["checkpoint_sha256"],
                        environment_source_sha256=context[
                            "environment_source_sha256"
                        ],
                        reward_source_sha256=context["reward_source_sha256"],
                        evaluation_seed=int(source_seed),
                        focal_user=focal_user,
                        forecast_fading_mode=pair_smoke.KEYED_FADING,
                    )
                    if service.anchor_sha256 != service._anchor_sha256:
                        raise C2V04CensusRunnerError(
                            "backend anchor digest is not self-consistent"
                        )
                    if service._main_actions[focal_user] != reference_action:
                        raise C2V04CensusRunnerError(
                            "service Main reference action disagrees with scan"
                        )
                    if service._main_physical_actions[focal_user] != reference_key:
                        raise C2V04CensusRunnerError(
                            "service Main physical reference disagrees with scan"
                        )
                    incumbent_key = backend._incumbent_key(
                        wrapped, focal_user=focal_user
                    )
                    predecision = neutral.predecision_anchor_from_observation(
                        anchor_sha256=service.anchor_sha256,
                        step_index=step_index,
                        focal_user=focal_user,
                        reference_action=reference_action,
                        observation=observation,
                    )
                    table = observation.candidates.slot_tables[focal_user]
                    legal_mask = np.asarray(table.mask)
                    if legal_mask.dtype != np.bool_ or legal_mask.shape != (
                        NUM_ACTIONS,
                    ) or not bool(np.all(legal_mask)):
                        continue
                    alternatives = tuple(predecision.legal_alternatives)
                    if len(alternatives) != SIBLINGS_PER_CLUSTER:
                        continue
                    candidate_actions = tuple(int(row.action) for row in alternatives)
                    candidate_keys = tuple(
                        (int(row.physical_key[0]), int(row.physical_key[1]))
                        for row in alternatives
                    )
                    if len(set(candidate_actions)) != SIBLINGS_PER_CLUSTER:
                        raise C2V04CensusRunnerError(
                            "predecision topology contains duplicate candidate actions"
                        )
                    if len(set(candidate_keys)) != SIBLINGS_PER_CLUSTER:
                        raise C2V04CensusRunnerError(
                            "predecision topology contains duplicate physical siblings"
                        )
                    if tuple(zip(candidate_keys, candidate_actions)) != tuple(
                        sorted(zip(candidate_keys, candidate_actions))
                    ):
                        raise C2V04CensusRunnerError(
                            "predecision topology is not canonically sorted"
                        )
                    causal_state, _causal_mask = _production_ee_axis_anchor(
                        modules=modules,
                        wrapped=wrapped,
                        observation=observation,
                        focal_user=focal_user,
                    )
                    heuristic = _predecision_heuristic_scores(
                        observation=observation,
                        state_row=causal_state,
                        focal_user=focal_user,
                        candidate_actions=candidate_actions,
                    )
                    field = keyed_fading.KeyedFadingField.from_components(
                        backend.FORECAST_SCHEMA,
                        context["checkpoint_sha256"],
                        service.anchor_sha256,
                        focal_user,
                        int(source_seed),
                    )
                    common_random_field_sha256 = field.root_digest
                    # Preparing all siblings is still pre-outcome: it only
                    # maps each physical key to the sealed opening slot and
                    # creates a chronology gate.  It must never forecast here.
                    for candidate_key in candidate_keys:
                        prepared = service.prepare_one_candidate(
                            focal_user=focal_user,
                            candidate_key=candidate_key,
                            source_rule=C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
                        )
                        if (
                            prepared.source_rule
                            != C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
                            or prepared.phase != "anchor"
                            or prepared.build is not None
                            or tuple(prepared.candidate_key) != candidate_key
                            or prepared.anchor.anchor_sha256 != service.anchor_sha256
                        ):
                            raise C2V04CensusRunnerError(
                                "candidate preparation crossed the pre-outcome boundary"
                            )
                    legacy_root = modules["legacy_source"]._cluster_field_sha256(
                        prepared
                    )
                    if legacy_root != common_random_field_sha256:
                        raise C2V04CensusRunnerError(
                            "legacy/source-control CRF helper disagrees with V0.4 root"
                        )
                    focal_records.append(
                        C2V04TopologyFocal(
                            focal_user=focal_user,
                            anchor_sha256=service.anchor_sha256,
                            reference_action=reference_action,
                            reference_physical_key=reference_key,
                            incumbent_physical_key=tuple(incumbent_key),
                            common_random_field_sha256=common_random_field_sha256,
                            predecision_heuristic_scores=heuristic,
                            legal_action_mask=tuple(bool(value) for value in legal_mask),
                            candidate_actions=candidate_actions,
                            candidate_physical_keys=candidate_keys,
                        )
                    )
                except C2V04CensusRunnerError:
                    raise
                except Exception:
                    # A focal is eligible only if its complete 27-sibling
                    # topology can be sealed.  The world scan continues to
                    # the next focal/step; no outcome is used to rescue it.
                    continue
            if len(focal_records) >= FOCAL_USERS_PER_WORLD:
                discovered.append(
                    C2V04TopologyAnchor(
                        source_seed=int(source_seed),
                        step_index=step_index,
                        world_anchor_sha256=world_anchor_sha256,
                        focal_candidates=tuple(
                            sorted(focal_records, key=lambda row: row.focal_user)
                        ),
                        physical_main_departures=departures,
                        checkpoint_sha256=context["checkpoint_sha256"],
                        source_manifest_sha256=context["source_manifest_sha256"],
                        policy_sha256=context["policy_sha256"],
                        evaluation_seed=int(source_seed),
                        common_random_field_root_sha256=_canonical_sha256(
                            {
                                "schema": "multi-catfish-mcrl-v04-c2-world-field-summary-v1",
                                "source_seed": int(source_seed),
                                "world_anchor_sha256": world_anchor_sha256,
                                "intervention_roots": [
                                    [
                                        row.focal_user,
                                        row.common_random_field_sha256,
                                    ]
                                    for row in sorted(
                                        focal_records,
                                        key=lambda item: item.focal_user,
                                    )
                                ],
                            }
                        ),
                        complete_forecast_horizon=True,
                    )
                )
                # The first complete step is the earliest eligible anchor;
                # no later topology can change the sealed choice.
                break
        result = wrapped.step(main_actions, env_rng)
        if bool(result.done):
            break
        states = result.user_states
        masks = result.action_masks
        if wrapped.last_outcome is None:
            raise C2V04CensusRunnerError(
                "Main replay step did not expose the next observation"
            )
        observation = wrapped.last_outcome.observation

    if not backend_smoke._networks_equal(trainer, network_before):
        raise C2V04CensusRunnerError(
            f"predecision topology scan mutated Main networks for seed {source_seed}"
        )
    if len(trainer.replay) != replay_before:
        raise C2V04CensusRunnerError(
            f"predecision topology scan mutated Main replay for seed {source_seed}"
        )
    return tuple(discovered)


def _real_tle_topology_scanner(
    *, modules: Mapping[str, Any], context: Mapping[str, Any]
) -> Callable[[int], Iterable[C2V04TopologyAnchor]]:
    """Return the server-side scanner bound to frozen Main/TLE inputs."""

    def scan(source_seed: int) -> Iterable[C2V04TopologyAnchor]:
        if type(source_seed) is not int or source_seed not in DESIGN_ONLY_SOURCE_SEEDS:
            raise C2V04CensusRunnerError("topology scan received a non-design source seed")
        return _real_seed_topology(
            source_seed=source_seed,
            modules=modules,
            context=context,
        )

    return scan


@dataclass(frozen=True)
class C2V04TopologyFocal:
    """One focal user's outcome-blind opening topology at a candidate anchor."""

    focal_user: int
    anchor_sha256: str
    reference_action: int
    reference_physical_key: tuple[int, int]
    incumbent_physical_key: tuple[int, int]
    common_random_field_sha256: str
    predecision_heuristic_scores: tuple[float, ...]
    legal_action_mask: tuple[bool, ...]
    candidate_actions: tuple[int, ...]
    candidate_physical_keys: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "focal_user", _exact_nonnegative_int(self.focal_user, field="focal_user"))
        object.__setattr__(self, "anchor_sha256", _digest(self.anchor_sha256, field="anchor_sha256"))
        object.__setattr__(self, "reference_action", _action(self.reference_action, field="reference_action"))
        object.__setattr__(self, "reference_physical_key", _physical_key(self.reference_physical_key, field="reference_physical_key"))
        object.__setattr__(self, "incumbent_physical_key", _physical_key(self.incumbent_physical_key, field="incumbent_physical_key"))
        object.__setattr__(self, "common_random_field_sha256", _digest(self.common_random_field_sha256, field="common_random_field_sha256"))
        scores = tuple(
            _finite(value, field=f"predecision_heuristic_scores[{index}]")
            for index, value in enumerate(self.predecision_heuristic_scores)
        )
        object.__setattr__(self, "predecision_heuristic_scores", scores)
        mask = _bool_mask(self.legal_action_mask, field="legal_action_mask")
        object.__setattr__(self, "legal_action_mask", mask)
        actions = tuple(_action(value, field=f"candidate_actions[{i}]") for i, value in enumerate(self.candidate_actions))
        keys = tuple(_physical_key(value, field=f"candidate_physical_keys[{i}]") for i, value in enumerate(self.candidate_physical_keys))
        object.__setattr__(self, "candidate_actions", actions)
        object.__setattr__(self, "candidate_physical_keys", keys)

    @property
    def complete_28_action_census(self) -> bool:
        """Whether this focal has exactly the preregistered legal topology."""

        if sum(self.legal_action_mask) != NUM_ACTIONS:
            return False
        if not self.legal_action_mask[self.reference_action]:
            return False
        if len(self.candidate_actions) != SIBLINGS_PER_CLUSTER:
            return False
        if len(self.candidate_physical_keys) != SIBLINGS_PER_CLUSTER:
            return False
        if len(self.predecision_heuristic_scores) != SIBLINGS_PER_CLUSTER:
            return False
        if len(set(self.candidate_actions)) != SIBLINGS_PER_CLUSTER:
            return False
        if len(set(self.candidate_physical_keys)) != SIBLINGS_PER_CLUSTER:
            return False
        if self.reference_action in self.candidate_actions:
            return False
        if self.reference_physical_key in self.candidate_physical_keys:
            return False
        expected = {action for action in range(NUM_ACTIONS) if action != self.reference_action}
        return set(self.candidate_actions) == expected


@dataclass(frozen=True)
class C2V04TopologyAnchor:
    """Predecision scan result supplied by the real or synthetic scanner."""

    source_seed: int
    step_index: int
    world_anchor_sha256: str
    focal_candidates: tuple[C2V04TopologyFocal, ...]
    physical_main_departures: tuple[int, ...]
    checkpoint_sha256: str
    source_manifest_sha256: str
    policy_sha256: str
    evaluation_seed: int
    common_random_field_root_sha256: str
    complete_forecast_horizon: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_seed", _exact_nonnegative_int(self.source_seed, field="source_seed"))
        object.__setattr__(self, "step_index", _exact_nonnegative_int(self.step_index, field="step_index"))
        if self.step_index < 1:
            raise C2V04CensusRunnerError("source anchor search starts at step 1")
        object.__setattr__(self, "world_anchor_sha256", _digest(self.world_anchor_sha256, field="world_anchor_sha256"))
        object.__setattr__(self, "physical_main_departures", tuple(sorted(set(_exact_nonnegative_int(value, field="physical_main_departures") for value in self.physical_main_departures))))
        for field in ("checkpoint_sha256", "source_manifest_sha256", "policy_sha256", "common_random_field_root_sha256"):
            object.__setattr__(self, field, _digest(getattr(self, field), field=field))
        object.__setattr__(self, "evaluation_seed", _exact_nonnegative_int(self.evaluation_seed, field="evaluation_seed"))
        focals = tuple(self.focal_candidates)
        if any(not isinstance(value, C2V04TopologyFocal) for value in focals):
            raise C2V04CensusRunnerError("focal_candidates contain a non-topology record")
        if tuple(sorted(focals, key=lambda value: value.focal_user)) != focals:
            raise C2V04CensusRunnerError("focal_candidates must be sorted by focal_user")
        if len({value.focal_user for value in focals}) != len(focals):
            raise C2V04CensusRunnerError("focal_candidates contain duplicate focal users")
        object.__setattr__(self, "focal_candidates", focals)
        if type(self.complete_forecast_horizon) is not bool:
            raise C2V04CensusRunnerError("complete_forecast_horizon must be Boolean")

    @property
    def eligible_focal_users(self) -> tuple[int, ...]:
        departure_users = set(self.physical_main_departures)
        return tuple(
            focal.focal_user
            for focal in self.focal_candidates
            if focal.focal_user in departure_users and focal.complete_28_action_census
        )

    @property
    def eligible(self) -> bool:
        return (
            self.complete_forecast_horizon
            and len(self.physical_main_departures) >= FOCAL_USERS_PER_WORLD
            and len(self.eligible_focal_users) >= FOCAL_USERS_PER_WORLD
        )

    def selected_anchor_schedules(self) -> tuple[C2V04AnchorSchedule, ...]:
        if not self.eligible:
            raise C2V04CensusRunnerError("cannot project an ineligible topology anchor")
        selected = self.eligible_focal_users[:FOCAL_USERS_PER_WORLD]
        by_user = {focal.focal_user: focal for focal in self.focal_candidates}
        return tuple(
            C2V04AnchorSchedule(
                source_seed=self.source_seed,
                anchor_step=self.step_index,
                world_anchor_sha256=self.world_anchor_sha256,
                anchor_sha256=by_user[user].anchor_sha256,
                focal_user=user,
                reference_action=by_user[user].reference_action,
                reference_physical_key=by_user[user].reference_physical_key,
                incumbent_physical_key=by_user[user].incumbent_physical_key,
                common_random_field_sha256=by_user[user].common_random_field_sha256,
                predecision_heuristic_scores=by_user[user].predecision_heuristic_scores,
                legal_action_mask=by_user[user].legal_action_mask,
                candidate_actions=by_user[user].candidate_actions,
                candidate_physical_keys=by_user[user].candidate_physical_keys,
                checkpoint_sha256=self.checkpoint_sha256,
                source_manifest_sha256=self.source_manifest_sha256,
                policy_sha256=self.policy_sha256,
                evaluation_seed=self.evaluation_seed,
                source_rule=C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
            )
            for user in selected
        )


@dataclass(frozen=True)
class C2V04PrepareResult:
    """Outcome-free prepare receipt plus its sealed complete schedule."""

    schedule: C2V04SupportCompleteSchedule
    scanned_source_seeds: tuple[int, ...]
    selected_source_seeds: tuple[int, ...]
    common_random_field_roots: tuple[tuple[tuple[int, str, str, int], str], ...]
    prepare_sha256: str
    schema: str = C2_V04_PREPARE_SCHEMA
    claim_ceiling: str = CLAIM_CEILING
    counterfactual_outcomes_evaluated: bool = False
    training_run: bool = False
    test_opened: bool = False
    held_out_ee_evaluated: bool = False

    def __post_init__(self) -> None:
        if self.schema != C2_V04_PREPARE_SCHEMA:
            raise C2V04CensusRunnerError("prepare schema is stale")
        if self.claim_ceiling != CLAIM_CEILING:
            raise C2V04CensusRunnerError("prepare claim ceiling drifted")
        for field in ("counterfactual_outcomes_evaluated", "training_run", "test_opened", "held_out_ee_evaluated"):
            if getattr(self, field) is not False:
                raise C2V04CensusRunnerError(f"prepare.{field} must be false")
        scanned = tuple(self.scanned_source_seeds)
        if scanned != DESIGN_ONLY_SOURCE_SEEDS[: len(scanned)] or not scanned:
            raise C2V04CensusRunnerError("prepare scanned seeds are not an ordered prefix")
        selected = tuple(self.selected_source_seeds)
        if len(selected) != SELECTED_WORLDS or selected != tuple(sorted(selected)):
            raise C2V04CensusRunnerError("prepare must select exactly three ordered worlds")
        if any(seed not in scanned for seed in selected):
            raise C2V04CensusRunnerError("selected world was not scanned")
        roots = tuple(self.common_random_field_roots)
        if tuple(sorted(roots)) != roots or len(roots) != EXPECTED_CLUSTERS:
            raise C2V04CensusRunnerError(
                "prepare must retain one keyed fading root per selected intervention"
            )
        expected_interventions = {
            anchor.intervention_key for anchor in self.schedule.anchors
        }
        observed_interventions: set[tuple[int, str, str, int]] = set()
        for intervention, root in roots:
            if not isinstance(intervention, tuple) or len(intervention) != 4:
                raise C2V04CensusRunnerError(
                    "fading-root intervention identity is malformed"
                )
            seed, world, anchor, focal = intervention
            _exact_nonnegative_int(seed, field="fading_root.source_seed")
            _digest(world, field="fading_root.world_anchor_sha256")
            _digest(anchor, field="fading_root.anchor_sha256")
            _exact_nonnegative_int(focal, field="fading_root.focal_user")
            if seed not in selected:
                raise C2V04CensusRunnerError(
                    "fading root belongs to an unselected world"
                )
            if intervention in observed_interventions:
                raise C2V04CensusRunnerError("duplicate fading-root intervention")
            observed_interventions.add(intervention)
            expected = next(
                (
                    item.common_random_field_sha256
                    for item in self.schedule.anchors
                    if item.intervention_key == intervention
                ),
                None,
            )
            if expected is None or expected != root:
                raise C2V04CensusRunnerError(
                    "fading root disagrees with its sealed intervention"
                )
            _digest(root, field="common_random_field_sha256")
        if observed_interventions != expected_interventions:
            raise C2V04CensusRunnerError(
                "prepare fading-root receipt does not cover exactly 12 interventions"
            )
        _digest(self.prepare_sha256, field="prepare_sha256")
        if len(self.schedule.anchors) != EXPECTED_CLUSTERS or len(self.schedule.rows) != EXPECTED_SIBLINGS:
            raise C2V04CensusRunnerError("prepare schedule does not have 12 clusters and 324 siblings")

    def to_mapping(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "claim_ceiling": self.claim_ceiling,
            "counterfactual_outcomes_evaluated": False,
            "training_run": False,
            "test_opened": False,
            "held_out_ee_evaluated": False,
            "scanned_source_seeds": list(self.scanned_source_seeds),
            "selected_source_seeds": list(self.selected_source_seeds),
            "common_random_field_roots": [
                [[key[0], key[1], key[2], key[3]], root]
                for key, root in self.common_random_field_roots
            ],
            "schedule": self.schedule.to_mapping(),
        }
        return body | {"prepare_sha256": self.prepare_sha256}


def _prepare_body(
    *,
    schedule: C2V04SupportCompleteSchedule,
    scanned_source_seeds: tuple[int, ...],
    selected_source_seeds: tuple[int, ...],
    common_random_field_roots: tuple[tuple[tuple[int, str, str, int], str], ...],
) -> dict[str, object]:
    return {
        "schema": C2_V04_PREPARE_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "counterfactual_outcomes_evaluated": False,
        "training_run": False,
        "test_opened": False,
        "held_out_ee_evaluated": False,
        "scanned_source_seeds": list(scanned_source_seeds),
        "selected_source_seeds": list(selected_source_seeds),
        "common_random_field_roots": [
            [[key[0], key[1], key[2], key[3]], root]
            for key, root in common_random_field_roots
        ],
        "schedule": schedule.to_mapping(),
    }


def prepare_c2_v04_census(
    topology_scanner: Callable[[int], Iterable[C2V04TopologyAnchor]],
    *,
    source_seeds: Sequence[int] = DESIGN_ONLY_SOURCE_SEEDS,
) -> C2V04PrepareResult:
    """Scan topology only and seal the first three eligible worlds.

    The scanner is an explicit predecision-only seam.  It must return anchors
    in increasing step order; this function sorts and then chooses the first
    eligible step, so a scanner cannot make the result depend on discovery
    iteration order.  No method on the returned topology records can evaluate
    a branch because the records contain only masks, physical keys, and
    lineage.
    """

    ordered_seeds = tuple(source_seeds)
    if ordered_seeds != DESIGN_ONLY_SOURCE_SEEDS:
        raise C2V04CensusRunnerError(
            "source seeds must be exactly the ordered design-only pool 2026092801..2810"
        )
    selected_schedules: list[C2V04AnchorSchedule] = []
    selected_seeds: list[int] = []
    roots: list[tuple[tuple[int, str, str, int], str]] = []
    scanned: list[int] = []
    for seed in ordered_seeds:
        scanned.append(seed)
        try:
            candidates = tuple(topology_scanner(seed))
        except Exception as error:
            raise C2V04CensusRunnerError(
                f"predecision topology scan failed for seed {seed}"
            ) from error
        for anchor in candidates:
            if not isinstance(anchor, C2V04TopologyAnchor):
                raise C2V04CensusRunnerError("topology scanner returned a non-anchor record")
            if anchor.source_seed != seed:
                raise C2V04CensusRunnerError("topology anchor source seed disagrees with scan seed")
        eligible = sorted(
            (anchor for anchor in candidates if anchor.eligible),
            key=lambda anchor: (anchor.step_index, anchor.world_anchor_sha256),
        )
        if not eligible:
            continue
        chosen = eligible[0]
        selected_schedules.extend(chosen.selected_anchor_schedules())
        selected_seeds.append(seed)
        roots.extend(
            (
                schedule.intervention_key,
                schedule.common_random_field_sha256,
            )
            for schedule in chosen.selected_anchor_schedules()
        )
        if len(selected_seeds) == SELECTED_WORLDS:
            break
    if len(selected_seeds) != SELECTED_WORLDS:
        raise C2V04CensusRunnerError(
            "fewer than three eligible worlds were found in the fixed design-only seed pool"
        )
    if len(selected_schedules) != EXPECTED_CLUSTERS:
        raise C2V04CensusRunnerError("selected topology did not yield exactly 12 focal clusters")
    schedule = build_c2_v04_support_complete_schedule(selected_schedules)
    roots = sorted(roots)
    body = _prepare_body(
        schedule=schedule,
        scanned_source_seeds=tuple(scanned),
        selected_source_seeds=tuple(selected_seeds),
        common_random_field_roots=tuple(roots),
    )
    result = C2V04PrepareResult(
        schedule=schedule,
        scanned_source_seeds=tuple(scanned),
        selected_source_seeds=tuple(selected_seeds),
        common_random_field_roots=tuple(roots),
        prepare_sha256=_canonical_sha256(body),
    )
    # Construction above checks the exact 12/324 cardinality and all lineage.
    if result.prepare_sha256 != _canonical_sha256(body):
        raise C2V04CensusRunnerError("prepare digest is not deterministic")
    return result


def _read_prepare_mapping(payload: object) -> C2V04PrepareResult:
    value = _json_mapping(payload, field="prepare artifact")
    required = {
        "schema",
        "claim_ceiling",
        "counterfactual_outcomes_evaluated",
        "training_run",
        "test_opened",
        "held_out_ee_evaluated",
        "scanned_source_seeds",
        "selected_source_seeds",
        "common_random_field_roots",
        "schedule",
        "prepare_sha256",
    }
    if set(value) != required:
        raise C2V04CensusRunnerError("prepare artifact schema is unexpected")
    try:
        roots = tuple(
            (
                (
                    int(row[0][0]),
                    str(row[0][1]),
                    str(row[0][2]),
                    int(row[0][3]),
                ),
                str(row[1]),
            )
            for row in value["common_random_field_roots"]  # type: ignore[index]
        )
        scanned = tuple(int(seed) for seed in value["scanned_source_seeds"])  # type: ignore[arg-type]
        selected = tuple(int(seed) for seed in value["selected_source_seeds"])  # type: ignore[arg-type]
    except (TypeError, ValueError, IndexError) as error:
        raise C2V04CensusRunnerError("prepare seed/root vectors are malformed") from error
    schedule = C2V04SupportCompleteSchedule.from_mapping(value["schedule"])
    result = C2V04PrepareResult(
        schedule=schedule,
        scanned_source_seeds=scanned,
        selected_source_seeds=selected,
        common_random_field_roots=roots,
        prepare_sha256=value["prepare_sha256"],  # type: ignore[arg-type]
        schema=value["schema"],  # type: ignore[arg-type]
        claim_ceiling=value["claim_ceiling"],  # type: ignore[arg-type]
        counterfactual_outcomes_evaluated=value["counterfactual_outcomes_evaluated"],  # type: ignore[arg-type]
        training_run=value["training_run"],  # type: ignore[arg-type]
        test_opened=value["test_opened"],  # type: ignore[arg-type]
        held_out_ee_evaluated=value["held_out_ee_evaluated"],  # type: ignore[arg-type]
    )
    body = _prepare_body(
        schedule=result.schedule,
        scanned_source_seeds=result.scanned_source_seeds,
        selected_source_seeds=result.selected_source_seeds,
        common_random_field_roots=result.common_random_field_roots,
    )
    if result.prepare_sha256 != _canonical_sha256(body):
        raise C2V04CensusRunnerError("prepare_sha256 disagrees with sealed contents")
    return result


def write_c2_v04_prepare_artifact(path: str | Path, result: C2V04PrepareResult) -> str:
    """Write a canonical, no-overwrite prepare artifact."""

    result = _read_prepare_mapping(result.to_mapping())
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite prepare artifact: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical_bytes(result.to_mapping())
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(encoded)
        handle.flush()
    try:
        temporary.replace(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return hashlib.sha256(encoded).hexdigest()


def read_c2_v04_prepare_artifact(
    path: str | Path, *, expected_file_sha256: str | None = None
) -> C2V04PrepareResult:
    destination = Path(path)
    if destination.is_symlink() or not destination.is_file():
        raise C2V04CensusRunnerError("prepare artifact must be a regular file")
    encoded = destination.read_bytes()
    file_sha = hashlib.sha256(encoded).hexdigest()
    if expected_file_sha256 is not None and file_sha != _digest(expected_file_sha256, field="expected_file_sha256"):
        raise C2V04CensusRunnerError("prepare artifact file digest disagrees")
    try:
        payload = json.loads(
            encoded.decode("ascii"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise C2V04CensusRunnerError("prepare artifact is invalid JSON") from error
    if encoded != _canonical_bytes(payload):
        raise C2V04CensusRunnerError("prepare artifact is not canonical JSON")
    return _read_prepare_mapping(payload)


# Phase-A deterministic metric layer --------------------------------------

@dataclass(frozen=True)
class C2V04OldQ2Ranking:
    """One frozen rung-10 Q2 legal-action ranking at one cluster."""

    initialization_seed: int
    ranked_actions: tuple[int, ...]
    supervised_candidate_action: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "initialization_seed", _exact_nonnegative_int(self.initialization_seed, field="initialization_seed"))
        ranking = tuple(_action(value, field=f"ranked_actions[{i}]") for i, value in enumerate(self.ranked_actions))
        if len(ranking) != NUM_ACTIONS or set(ranking) != set(range(NUM_ACTIONS)):
            raise C2V04CensusRunnerError("old Q2 ranking must be a 28-action permutation")
        object.__setattr__(self, "ranked_actions", ranking)
        object.__setattr__(self, "supervised_candidate_action", _action(self.supervised_candidate_action, field="supervised_candidate_action"))

    @property
    def selected_action(self) -> int:
        return self.ranked_actions[0]

    def to_mapping(self) -> dict[str, object]:
        return {
            "initialization_seed": self.initialization_seed,
            "ranked_actions": list(self.ranked_actions),
            "selected_action": self.selected_action,
            "supervised_candidate_action": self.supervised_candidate_action,
        }


@dataclass(frozen=True)
class C2V04PhaseARow:
    """One scheduled Main-continuation row, including source failures."""

    sibling_key: tuple[int, str, str, int, tuple[int, int]]
    candidate_action: int
    candidate_physical_key: tuple[int, int]
    row_status: str
    failure_code: str | None
    non_incumbent: bool | None
    release_offset: int | None
    zeta2_temporal_surplus_bits: float | None
    delivered_bit_delta: float | None
    common_random_field_sha256: str | None = None
    raw_trace: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sibling_key, tuple) or len(self.sibling_key) != 5:
            raise C2V04CensusRunnerError("phase-A sibling_key is malformed")
        _exact_nonnegative_int(self.sibling_key[0], field="sibling_key.source_seed")
        _digest(self.sibling_key[1], field="sibling_key.world_anchor_sha256")
        _digest(self.sibling_key[2], field="sibling_key.anchor_sha256")
        _exact_nonnegative_int(self.sibling_key[3], field="sibling_key.focal_user")
        _physical_key(self.sibling_key[4], field="sibling_key.candidate_physical_key")
        object.__setattr__(self, "candidate_action", _action(self.candidate_action, field="candidate_action"))
        object.__setattr__(self, "candidate_physical_key", _physical_key(self.candidate_physical_key, field="candidate_physical_key"))
        status = _status(self.row_status)
        object.__setattr__(self, "row_status", status)
        object.__setattr__(self, "failure_code", _status_code(self.failure_code, status=status))
        if self.non_incumbent is not None and type(self.non_incumbent) is not bool:
            raise C2V04CensusRunnerError("non_incumbent must be Boolean or null")
        if self.release_offset is not None:
            offset = _exact_nonnegative_int(self.release_offset, field="release_offset")
            if offset < 1 or offset > 3:
                raise C2V04CensusRunnerError("release_offset must lie in 1..3")
            object.__setattr__(self, "release_offset", offset)
        for field in ("zeta2_temporal_surplus_bits", "delivered_bit_delta"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _finite(value, field=field))
        if self.common_random_field_sha256 is not None:
            object.__setattr__(
                self,
                "common_random_field_sha256",
                _digest(
                    self.common_random_field_sha256,
                    field="common_random_field_sha256",
                ),
            )
        if self.raw_trace is not None and not isinstance(self.raw_trace, Mapping):
            raise C2V04CensusRunnerError("raw_trace must be a mapping or null")
        if self.row_status == C2_V04_ROW_READY and any(
            value is None
            for value in (self.non_incumbent, self.release_offset, self.zeta2_temporal_surplus_bits, self.delivered_bit_delta)
        ):
            raise C2V04CensusRunnerError("ready phase-A rows require all physical metrics")

    @property
    def normalized_target(self) -> float | None:
        if self.zeta2_temporal_surplus_bits is None:
            return None
        return self.zeta2_temporal_surplus_bits / KAPPA_BITS

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema": C2_V04_PHASE_A_ROW_SCHEMA,
            "sibling_key": [
                self.sibling_key[0],
                self.sibling_key[1],
                self.sibling_key[2],
                self.sibling_key[3],
                list(self.sibling_key[4]),
            ],
            "candidate_action": self.candidate_action,
            "candidate_physical_key": list(self.candidate_physical_key),
            "row_status": self.row_status,
            "failure_code": self.failure_code,
            "non_incumbent": self.non_incumbent,
            "release_offset": self.release_offset,
            "zeta2_temporal_surplus_bits": self.zeta2_temporal_surplus_bits,
            "delivered_bit_delta": self.delivered_bit_delta,
            "common_random_field_sha256": self.common_random_field_sha256,
            "raw_trace": None if self.raw_trace is None else dict(self.raw_trace),
        }


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise C2V04CensusRunnerError("percentile requires nonempty values")
    if fraction <= 0.0:
        return ordered[0]
    if fraction >= 1.0:
        return ordered[-1]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _iqr(values: Sequence[float]) -> float:
    return _percentile(values, 0.75) - _percentile(values, 0.25)


def _rank(values: Sequence[float]) -> tuple[float, ...]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    result = [0.0] * len(values)
    position = 0
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end][0] == ordered[position][0]:
            end += 1
        average = (position + 1 + end) / 2.0
        for _, index in ordered[position:end]:
            result[index] = average
        position = end
    return tuple(result)


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    mean_left = statistics.fmean(left)
    mean_right = statistics.fmean(right)
    numerator = math.fsum((a - mean_left) * (b - mean_right) for a, b in zip(left, right, strict=True))
    denominator_left = math.sqrt(math.fsum((a - mean_left) ** 2 for a in left))
    denominator_right = math.sqrt(math.fsum((b - mean_right) ** 2 for b in right))
    if denominator_left == 0.0 or denominator_right == 0.0:
        return None
    return numerator / (denominator_left * denominator_right)


def _spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    return _pearson(_rank(left), _rank(right))


def _intervention_key_from_row(row: C2V04PhaseARow) -> tuple[int, str, str, int]:
    return row.sibling_key[:4]


def _row_for_sibling(
    sibling: C2V04SiblingRow,
    outcome: Mapping[str, object] | None,
) -> C2V04PhaseARow:
    if outcome is None:
        return C2V04PhaseARow(
            sibling_key=sibling.sibling_key,
            candidate_action=sibling.candidate_action,
            candidate_physical_key=sibling.candidate_physical_key,
            row_status=C2_V04_ROW_FAILURE,
            failure_code="missing_main_continuation_outcome",
            non_incumbent=(
                sibling.candidate_physical_key != sibling.incumbent_physical_key
            ),
            release_offset=None,
            zeta2_temporal_surplus_bits=None,
            delivered_bit_delta=None,
            common_random_field_sha256=sibling.common_random_field_sha256,
            raw_trace=None,
        )
    payload = _json_mapping(outcome, field="phase-A outcome")
    status = _status(payload.get("row_status", C2_V04_ROW_READY))
    failure_code = _status_code(payload.get("failure_code"), status=status)
    non_incumbent = (
        sibling.candidate_physical_key != sibling.incumbent_physical_key
    )
    supplied_non_incumbent = payload.get("non_incumbent")
    if supplied_non_incumbent is not None and supplied_non_incumbent != non_incumbent:
        raise C2V04CensusRunnerError(
            "physical outcome non_incumbent classification disagrees with sealed incumbent"
        )
    supplied_field = payload.get("common_random_field_sha256")
    if status != C2_V04_ROW_FAILURE and supplied_field is None:
        raise C2V04CensusRunnerError(
            "physical outcome lacks its sealed common-random-field root"
        )
    if supplied_field is not None and supplied_field != sibling.common_random_field_sha256:
        raise C2V04CensusRunnerError(
            "physical outcome common-random-field root disagrees with sealed intervention"
        )
    raw_trace = payload.get("raw_trace")
    if raw_trace is not None and not isinstance(raw_trace, Mapping):
        raise C2V04CensusRunnerError("phase-A raw_trace must be a mapping")
    def optional(name: str) -> float | None:
        raw = payload.get(name)
        return None if raw is None else _finite(raw, field=name)
    zeta2_value = optional("zeta2_temporal_surplus_bits")
    delivered_value = optional("delivered_bit_delta")
    if raw_trace is not None:
        if supplied_field is None:
            raise C2V04CensusRunnerError(
                "physical outcome with raw trace lacks its common-random-field root"
            )
        # Validate before constructing the row so no unverified physical
        # result can enter a Phase-A receipt.
        provisional = C2V04SiblingRow.from_anchor(
            C2V04AnchorSchedule(
                source_seed=sibling.source_seed,
                anchor_step=sibling.anchor_step,
                world_anchor_sha256=sibling.world_anchor_sha256,
                anchor_sha256=sibling.anchor_sha256,
                focal_user=sibling.focal_user,
                reference_action=sibling.reference_action,
                reference_physical_key=sibling.reference_physical_key,
                incumbent_physical_key=sibling.incumbent_physical_key,
                common_random_field_sha256=sibling.common_random_field_sha256,
                predecision_heuristic_scores=sibling.predecision_heuristic_scores,
                legal_action_mask=sibling.legal_action_mask,
                candidate_actions=sibling.candidate_actions,
                candidate_physical_keys=sibling.candidate_physical_keys,
                checkpoint_sha256=sibling.checkpoint_sha256,
                source_manifest_sha256=sibling.source_manifest_sha256,
                policy_sha256=sibling.policy_sha256,
                evaluation_seed=sibling.evaluation_seed,
                source_rule=sibling.source_rule,
                anchor_schedule_sha256=sibling.anchor_schedule_sha256,
            ),
            candidate_action=sibling.candidate_action,
            candidate_physical_key=sibling.candidate_physical_key,
        )
        _validate_raw_trace(
            provisional,
            status=status,
            zeta2=zeta2_value,
            delivered=delivered_value,
            raw_trace=raw_trace,
        )
    return C2V04PhaseARow(
        sibling_key=sibling.sibling_key,
        candidate_action=sibling.candidate_action,
        candidate_physical_key=sibling.candidate_physical_key,
        row_status=status,
        failure_code=failure_code,
        non_incumbent=non_incumbent,
        release_offset=None if payload.get("release_offset") is None else payload.get("release_offset"),  # type: ignore[arg-type]
        zeta2_temporal_surplus_bits=zeta2_value,
        delivered_bit_delta=delivered_value,
        common_random_field_sha256=sibling.common_random_field_sha256,
        raw_trace=raw_trace,
    )


def _rankings_for_cluster(
    value: Sequence[C2V04OldQ2Ranking],
) -> tuple[C2V04OldQ2Ranking, ...]:
    rankings = tuple(value)
    if tuple(row.initialization_seed for row in rankings) != Q2_INITIALIZATION_SEEDS:
        raise C2V04CensusRunnerError(
            "old Q2 rankings must contain exactly the three ordered rung-10 initialization seeds"
        )
    return rankings


def _validate_schedule_for_phase_a(result: C2V04PrepareResult) -> None:
    if not isinstance(result, C2V04PrepareResult):
        raise C2V04CensusRunnerError("phase-A input must be C2V04PrepareResult")
    result.schedule.verify()
    if result.schedule.schema != C2_V04_SCHEDULE_SCHEMA:
        raise C2V04CensusRunnerError("phase-A schedule schema is stale")
    if len(result.schedule.anchors) != EXPECTED_CLUSTERS or len(result.schedule.rows) != EXPECTED_SIBLINGS:
        raise C2V04CensusRunnerError("phase-A requires exactly 12 clusters and 324 siblings")
    if any(anchor.source_seed not in DESIGN_ONLY_SOURCE_SEEDS for anchor in result.schedule.anchors):
        raise C2V04CensusRunnerError("phase-A schedule contains a non-design seed")


def _gate_gs(rows: Sequence[C2V04PhaseARow], clusters: Sequence[C2V04AnchorSchedule]) -> dict[str, object]:
    by_cluster: dict[tuple[int, str, str, int], list[C2V04PhaseARow]] = {anchor.intervention_key: [] for anchor in clusters}
    for row in rows:
        by_cluster.setdefault(_intervention_key_from_row(row), []).append(row)
    missing = [row for row in rows if row.zeta2_temporal_surplus_bits is None or row.release_offset is None or row.non_incumbent is None]
    non_incumbent = [row for row in rows if row.non_incumbent is True]
    pooled_survival = [row for row in non_incumbent if row.release_offset is not None and row.release_offset >= 2]
    world_counts: dict[int, tuple[int, int]] = {}
    for seed in sorted({anchor.source_seed for anchor in clusters}):
        world_rows = [row for row in non_incumbent if row.sibling_key[0] == seed]
        world_good = sum(row.release_offset is not None and row.release_offset >= 2 for row in world_rows)
        world_counts[seed] = (world_good, len(world_rows))
    target_values = [float(row.normalized_target) for row in non_incumbent if row.normalized_target is not None]
    cluster_iqrs = {
        str(key): _iqr([float(row.normalized_target) for row in cluster_rows if row.normalized_target is not None])
        if all(row.normalized_target is not None for row in cluster_rows) and cluster_rows
        else None
        for key, cluster_rows in by_cluster.items()
    }
    pooled_fraction = (len(pooled_survival) / len(non_incumbent)) if non_incumbent else 0.0
    world_fractions = {
        str(seed): (good / total if total else 0.0)
        for seed, (good, total) in world_counts.items()
    }
    passing_iqr_clusters = sum(value is not None and value >= 0.5 for value in cluster_iqrs.values())
    passed = bool(
        not missing
        and pooled_fraction >= 0.70
        and all(value >= 0.60 for value in world_fractions.values())
        and target_values
        and statistics.median(abs(value) for value in target_values) >= 0.5
        and passing_iqr_clusters >= 9
    )
    return {
        "passed": passed,
        "missing_outcome_count": len(missing),
        "non_incumbent_count": len(non_incumbent),
        "pooled_release_ge_2_fraction": pooled_fraction,
        "world_release_ge_2_fraction": world_fractions,
        "pooled_median_abs_normalized_zeta2": statistics.median(abs(value) for value in target_values) if target_values else None,
        "cluster_target_iqr": cluster_iqrs,
        "clusters_iqr_ge_0p5": passing_iqr_clusters,
    }


def _gate_gr(
    rows: Sequence[C2V04PhaseARow],
    clusters: Sequence[C2V04AnchorSchedule],
    rankings: Mapping[tuple[int, str, str, int], Sequence[C2V04OldQ2Ranking]],
) -> dict[str, object]:
    rows_by_cluster: dict[tuple[int, str, str, int], list[C2V04PhaseARow]] = {anchor.intervention_key: [] for anchor in clusters}
    anchors_by_key = {anchor.intervention_key: anchor for anchor in clusters}
    for row in rows:
        rows_by_cluster.setdefault(_intervention_key_from_row(row), []).append(row)
    observations: list[dict[str, object]] = []
    for key, anchor in anchors_by_key.items():
        cluster_rows = rows_by_cluster.get(key, [])
        targets = {anchor.reference_action: 0.0}
        for row in cluster_rows:
            if row.normalized_target is not None:
                targets[row.candidate_action] = row.normalized_target
        valid = len(targets) == NUM_ACTIONS
        physical_best_action = max(targets, key=lambda action: (targets[action], -action)) if targets else None
        cluster_rankings = tuple(rankings.get(key, ()))
        for ranking in cluster_rankings:
            selected_value = targets.get(ranking.selected_action)
            best_value = max(targets.values()) if targets else None
            if selected_value is None or best_value is None:
                regret = None
            else:
                regret = best_value - selected_value
            pair_actions = {anchor.reference_action, ranking.supervised_candidate_action}
            pair_best = max((targets.get(action, float("nan")) for action in pair_actions))
            outside_pair = physical_best_action is not None and physical_best_action not in pair_actions
            gap = None if physical_best_action is None else targets[physical_best_action] - pair_best
            observations.append({
                "intervention_key": list(key[:3]) + [key[3]],
                "initialization_seed": ranking.initialization_seed,
                "selected_action": ranking.selected_action,
                "supervised_candidate_action": ranking.supervised_candidate_action,
                "physical_best_action": physical_best_action,
                "regret": regret,
                "physical_best_outside_supervised_pair": outside_pair,
                "physical_best_gap_over_pair": gap,
            })
    regrets = [float(value["regret"]) for value in observations if value["regret"] is not None]
    positive = [value for value in regrets if value > 0.0]
    by_init = {
        seed: [value for value in observations if value["initialization_seed"] == seed and value["regret"] is not None]
        for seed in Q2_INITIALIZATION_SEEDS
    }
    positive_by_init = {seed: sum(float(value["regret"]) > 0.0 for value in values) for seed, values in by_init.items()}
    cluster_outside_gap = {
        str(key): max(
            (bool(value["physical_best_outside_supervised_pair"]) and value["physical_best_gap_over_pair"] is not None and float(value["physical_best_gap_over_pair"]) >= 0.5)
            for value in observations
            if tuple(value["intervention_key"][:3]) + (value["intervention_key"][3],) == key
        )
        if any(tuple(value["intervention_key"][:3]) + (value["intervention_key"][3],) == key for value in observations)
        else False
        for key in anchors_by_key
    }
    passed = bool(
        len(observations) == len(clusters) * len(Q2_INITIALIZATION_SEEDS)
        and len(regrets) == len(observations)
        and len(regrets) >= 36
        and statistics.median(regrets) >= 1.0
        and len(positive) >= 27
        and all(positive_by_init[seed] >= 8 for seed in Q2_INITIALIZATION_SEEDS)
        and sum(cluster_outside_gap.values()) >= 8
    )
    return {
        "passed": passed,
        "observation_count": len(observations),
        "median_regret": statistics.median(regrets) if regrets else None,
        "positive_regret_count": len(positive),
        "positive_regret_count_by_initialization": positive_by_init,
        "clusters_physical_best_outside_pair_gap_ge_0p5": cluster_outside_gap,
        "clusters_passing_outside_pair_gap": sum(cluster_outside_gap.values()),
        "old_q2_rankings": observations,
        "valid_complete_action_targets": all(
            len([row for row in rows_by_cluster.get(key, []) if row.normalized_target is not None]) == SIBLINGS_PER_CLUSTER
            for key in anchors_by_key
        ),
    }


def _gate_gv(rows: Sequence[C2V04PhaseARow], clusters: Sequence[C2V04AnchorSchedule]) -> dict[str, object]:
    by_cluster: dict[tuple[int, str, str, int], list[C2V04PhaseARow]] = {anchor.intervention_key: [] for anchor in clusters}
    for row in rows:
        by_cluster.setdefault(_intervention_key_from_row(row), []).append(row)
    cluster_pass: dict[tuple[int, str, str, int], bool] = {}
    for key, cluster_rows in by_cluster.items():
        ranked = sorted(
            (row for row in cluster_rows if row.normalized_target is not None and row.delivered_bit_delta is not None),
            key=lambda row: (-float(row.normalized_target), row.candidate_action),
        )[:3]
        cluster_pass[key] = len(ranked) == 3 and any(float(row.delivered_bit_delta) >= 0.0 for row in ranked)
    world_counts: dict[int, tuple[int, int]] = {}
    for seed in sorted({anchor.source_seed for anchor in clusters}):
        values = [passed for key, passed in cluster_pass.items() if key[0] == seed]
        world_counts[seed] = (sum(values), len(values))
    world_cluster_pass = {str(seed): count for seed, count in world_counts.items()}
    passing_worlds = sum(good >= 3 for good, total in world_counts.values())
    passed = bool(
        len(cluster_pass) == len(clusters)
        and sum(cluster_pass.values()) >= 9
        and passing_worlds >= 2
    )
    return {
        "passed": passed,
        "clusters_top3_with_nonnegative_delivered_delta": {
            str(key): value for key, value in cluster_pass.items()
        },
        "clusters_passing": sum(cluster_pass.values()),
        "world_cluster_pass_counts": world_cluster_pass,
        "worlds_with_at_least_three_passing_clusters": passing_worlds,
    }


def _heuristic_diagnostic(
    rows: Sequence[C2V04PhaseARow], clusters: Sequence[C2V04AnchorSchedule]
) -> dict[str, object]:
    """Report non-blocking Spearman agreement with sealed predecision h(a)."""

    by_cluster: dict[tuple[int, str, str, int], list[C2V04PhaseARow]] = {
        anchor.intervention_key: [] for anchor in clusters
    }
    for row in rows:
        by_cluster.setdefault(_intervention_key_from_row(row), []).append(row)
    per_cluster: dict[str, float | None] = {}
    for anchor in clusters:
        target_by_action = {anchor.reference_action: 0.0}
        for row in by_cluster.get(anchor.intervention_key, ()):
            if row.normalized_target is not None:
                target_by_action[row.candidate_action] = row.normalized_target
        h_by_action = {
            anchor.reference_action: 0.0,
            **dict(zip(anchor.candidate_actions, anchor.predecision_heuristic_scores, strict=True)),
        }
        if set(target_by_action) != set(range(NUM_ACTIONS)):
            per_cluster[str(anchor.intervention_key)] = None
            continue
        actions = tuple(range(NUM_ACTIONS))
        per_cluster[str(anchor.intervention_key)] = _spearman(
            [float(target_by_action[action]) for action in actions],
            [float(h_by_action[action]) for action in actions],
        )
    observed = [value for value in per_cluster.values() if value is not None]
    return {
        "formula": "within-cluster percentile-ranked log1p-SINR minus eligible-load minus maximum-required-link-power",
        "per_cluster_spearman": per_cluster,
        "complete_cluster_count": len(observed),
        "median_spearman": statistics.median(observed) if observed else None,
    }


def phase_a_census(
    prepared: C2V04PrepareResult,
    outcomes: Mapping[object, Mapping[str, object]],
    old_q2_rankings: Mapping[tuple[int, str, str, int], Sequence[C2V04OldQ2Ranking]],
) -> dict[str, object]:
    """Evaluate sealed Main-continuation receipts without training or TEST."""

    _validate_schedule_for_phase_a(prepared)
    schedule = prepared.schedule
    expected_sibling_keys = {row.sibling_key for row in schedule.rows}
    observed_sibling_keys: set[tuple[int, str, str, int, tuple[int, int]]] = set()
    for raw_key in outcomes:
        parsed_key: object = raw_key
        if isinstance(raw_key, str):
            try:
                parsed_key = json.loads(raw_key)
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise C2V04CensusRunnerError(
                    "outcome map contains an invalid canonical sibling key"
                ) from error
        try:
            if not isinstance(parsed_key, (tuple, list)) or len(parsed_key) != 5:
                raise ValueError
            parsed = (
                int(parsed_key[0]),
                str(parsed_key[1]),
                str(parsed_key[2]),
                int(parsed_key[3]),
                _physical_key(parsed_key[4], field="outcome.sibling_key"),
            )
        except (TypeError, ValueError, IndexError, C2V04CensusRunnerError) as error:
            raise C2V04CensusRunnerError(
                "outcome map contains an invalid sibling identity"
            ) from error
        if parsed not in expected_sibling_keys:
            raise C2V04CensusRunnerError(
                "outcome map contains an unscheduled extra sibling"
            )
        if parsed in observed_sibling_keys:
            raise C2V04CensusRunnerError(
                "outcome map contains duplicate tuple/text sibling identities"
            )
        observed_sibling_keys.add(parsed)
    expected_intervention_keys = {
        anchor.intervention_key for anchor in schedule.anchors
    }
    observed_intervention_keys = set(old_q2_rankings)
    extra_rankings = observed_intervention_keys - expected_intervention_keys
    missing_rankings = expected_intervention_keys - observed_intervention_keys
    if extra_rankings:
        raise C2V04CensusRunnerError(
            "old Q2 ranking map contains an unscheduled extra cluster"
        )
    if missing_rankings:
        raise C2V04CensusRunnerError(
            "old Q2 ranking map is missing a scheduled cluster"
        )
    rows: list[C2V04PhaseARow] = []
    for sibling in schedule.rows:
        outcome = outcomes.get(sibling.sibling_key)
        if outcome is None:
            # JSON callers may use the canonical text key; accepting it does
            # not relax the identity because it is parsed and matched below.
            outcome = outcomes.get(sibling_key_text(sibling.sibling_key))
        rows.append(_row_for_sibling(sibling, outcome))
    rows = sorted(rows, key=lambda row: row.sibling_key)
    ranking_map: dict[tuple[int, str, str, int], tuple[C2V04OldQ2Ranking, ...]] = {}
    for key in {anchor.intervention_key for anchor in schedule.anchors}:
        ranking_map[key] = _rankings_for_cluster(tuple(old_q2_rankings.get(key, ())))
    gs = _gate_gs(rows, schedule.anchors)
    gr = _gate_gr(rows, schedule.anchors, ranking_map)
    gv = _gate_gv(rows, schedule.anchors)
    heuristic = _heuristic_diagnostic(rows, schedule.anchors)
    result_body: dict[str, object] = {
        "schema": C2_V04_PHASE_A_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "source_rule": C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
        "schedule_sha256": schedule.schedule_sha256,
        "prepare_sha256": prepared.prepare_sha256,
        "row_count": len(rows),
        "expected_row_count": EXPECTED_SIBLINGS,
        "counterfactual_outcomes_evaluated": True,
        "training_run": False,
        "test_opened": False,
        "held_out_ee_evaluated": False,
        "gates": {"G-S": gs, "G-R": gr, "G-V": gv},
        "diagnostics": {"target_vs_predecision_heuristic": heuristic},
        "decision": (
            V04_PHASE_A_DECISION
            if gs["passed"] and gr["passed"] and gv["passed"]
            else "FORMULATION_REDESIGN_REQUIRED"
        ),
        "rows": [row.to_mapping() for row in rows],
    }
    result_body["phase_a_sha256"] = _canonical_sha256(result_body)
    return result_body


def _replay_main_to_step(
    *,
    source_seed: int,
    target_step: int,
    modules: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay frozen Main actions to one sealed predecision anchor."""

    if type(target_step) is not int or target_step < 1:
        raise C2V04CensusRunnerError("sealed anchor step must be a positive integer")
    loader = modules["loader"]
    backend_smoke = modules["backend_smoke"]
    wrapped = loader._make_environment(context["archive"], users=100)
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
        int(source_seed)
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    for _ in range(target_step + 1):
        current_step = int(observation.step_index)
        if current_step == target_step:
            main_actions, main_physical = backend_smoke._main_decision(
                context["trainer"], wrapped, states, masks, observation, env_rng
            )
            return {
                "wrapped": wrapped,
                "env_rng": env_rng,
                "mobility_rng": mobility_rng,
                "states": states,
                "masks": masks,
                "observation": observation,
                "main_actions": main_actions,
                "main_physical": main_physical,
            }
        if current_step > target_step:
            raise C2V04CensusRunnerError(
                "Main replay stepped past the sealed anchor"
            )
        main_actions, _main_physical = backend_smoke._main_decision(
            context["trainer"], wrapped, states, masks, observation, env_rng
        )
        result = wrapped.step(main_actions, env_rng)
        if bool(result.done):
            raise C2V04CensusRunnerError(
                "Main replay ended before the sealed anchor step"
            )
        states = result.user_states
        masks = result.action_masks
        if wrapped.last_outcome is None:
            raise C2V04CensusRunnerError(
                "Main replay did not expose the next observation"
            )
        observation = wrapped.last_outcome.observation
    raise C2V04CensusRunnerError(
        "Main replay exceeded its deterministic step budget"
    )


def _real_service_for_sealed_anchor(
    *,
    anchor: C2V04AnchorSchedule,
    replay: Mapping[str, Any],
    modules: Mapping[str, Any],
    context: Mapping[str, Any],
) -> Any:
    """Rebuild one sealed service anchor and verify every shared field."""

    import numpy as np

    backend = modules["backend"]
    backend_smoke = modules["backend_smoke"]
    pair_smoke = modules["pair_smoke"]
    neutral = modules["neutral"]
    e1_schedule = modules["e1_schedule"]
    keyed_fading = modules["keyed_fading"]
    observation = replay["observation"]
    focal_user = int(anchor.focal_user)
    main_actions = replay["main_actions"]
    main_physical = replay["main_physical"]
    if int(main_actions[focal_user]) != anchor.reference_action:
        raise C2V04CensusRunnerError(
            "sealed reference action disagrees with deterministic Main replay"
        )
    if main_physical[focal_user] is None or tuple(main_physical[focal_user]) != anchor.reference_physical_key:
        raise C2V04CensusRunnerError(
            "sealed reference physical key disagrees with deterministic Main replay"
        )
    expected_world = e1_schedule.e1_c2_world_anchor_sha256(
        source_seed=anchor.source_seed,
        anchor_step=int(observation.step_index),
    )
    if expected_world != anchor.world_anchor_sha256:
        raise C2V04CensusRunnerError(
            "sealed world anchor does not match its source seed and step"
        )
    service = backend.C2TemporalForkTrainerBackend(
        wrapped=replay["wrapped"],
        states=replay["states"],
        masks=replay["masks"],
        observation=observation,
        env_rng=replay["env_rng"],
        trainer=context["trainer"],
        checkpoint_sha256=context["checkpoint_sha256"],
        environment_source_sha256=context["environment_source_sha256"],
        reward_source_sha256=context["reward_source_sha256"],
        evaluation_seed=anchor.evaluation_seed,
        focal_user=focal_user,
        forecast_fading_mode=pair_smoke.KEYED_FADING,
    )
    if service.anchor_sha256 != anchor.anchor_sha256:
        raise C2V04CensusRunnerError(
            "sealed anchor_sha256 disagrees with replayed backend anchor"
        )
    if service._main_actions[focal_user] != anchor.reference_action:
        raise C2V04CensusRunnerError(
            "replayed service Main action disagrees with sealed anchor"
        )
    if tuple(service._main_physical_actions[focal_user] or ()) != anchor.reference_physical_key:
        raise C2V04CensusRunnerError(
            "replayed service Main physical key disagrees with sealed anchor"
        )
    if service._anchor_payload.get("checkpoint_sha256") != anchor.checkpoint_sha256:
        raise C2V04CensusRunnerError("sealed checkpoint lineage disagrees with service")
    if service._anchor_payload.get("environment_source_sha256") != context[
        "environment_source_sha256"
    ] or service._anchor_payload.get("reward_source_sha256") != context[
        "reward_source_sha256"
    ]:
        raise C2V04CensusRunnerError("sealed source lineage disagrees with service")
    incumbent = backend._incumbent_key(replay["wrapped"], focal_user=focal_user)
    if tuple(incumbent) != anchor.incumbent_physical_key:
        raise C2V04CensusRunnerError(
            "sealed incumbent physical key disagrees with replayed environment"
        )
    table = observation.candidates.slot_tables[focal_user]
    mask = np.asarray(table.mask)
    if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,) or not bool(np.all(mask)):
        raise C2V04CensusRunnerError(
            "sealed support-complete anchor no longer has 28 legal actions"
        )
    predecision = neutral.predecision_anchor_from_observation(
        anchor_sha256=service.anchor_sha256,
        step_index=int(observation.step_index),
        focal_user=focal_user,
        reference_action=anchor.reference_action,
        observation=observation,
    )
    candidate_actions = tuple(int(row.action) for row in predecision.legal_alternatives)
    candidate_keys = tuple(
        (int(row.physical_key[0]), int(row.physical_key[1]))
        for row in predecision.legal_alternatives
    )
    if candidate_actions != anchor.candidate_actions or candidate_keys != anchor.candidate_physical_keys:
        raise C2V04CensusRunnerError(
            "sealed complete sibling census disagrees with replayed slot topology"
        )
    causal_state, _causal_mask = _production_ee_axis_anchor(
        modules=modules,
        wrapped=replay["wrapped"],
        observation=observation,
        focal_user=focal_user,
    )
    heuristic = _predecision_heuristic_scores(
        observation=observation,
        state_row=causal_state,
        focal_user=focal_user,
        candidate_actions=candidate_actions,
    )
    if any(
        not math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)
        for left, right in zip(heuristic, anchor.predecision_heuristic_scores, strict=True)
    ):
        raise C2V04CensusRunnerError(
            "sealed predecision heuristic does not match replayed topology"
        )
    field = keyed_fading.KeyedFadingField.from_components(
        backend.FORECAST_SCHEMA,
        context["checkpoint_sha256"],
        service.anchor_sha256,
        focal_user,
        anchor.evaluation_seed,
    )
    if field.root_digest != anchor.common_random_field_sha256:
        raise C2V04CensusRunnerError(
            "sealed common-random-field root disagrees with replayed intervention"
        )
    return service


def _old_q2_rankings_for_anchor(
    *,
    anchor: C2V04AnchorSchedule,
    service: Any,
    q2_heads: Mapping[int, tuple[Any, Mapping[str, Any]]],
    modules: Mapping[str, Any],
) -> tuple[C2V04OldQ2Ranking, ...]:
    """Evaluate the three frozen rung-10 Q2 heads at one sealed cluster."""

    import numpy as np
    import torch

    backend = modules["backend"]
    state, mask = _production_ee_axis_anchor(
        modules=modules,
        wrapped=service.wrapped,
        observation=service.observation,
        focal_user=anchor.focal_user,
    )
    if state.shape != (228,) or mask.shape != (NUM_ACTIONS,) or not bool(np.all(mask)):
        raise C2V04CensusRunnerError("old Q2 ranking requires a complete 228/28 anchor")
    table = service.observation.candidates.slot_tables[anchor.focal_user]
    try:
        supervised_key = backend._incumbent_key(
            service.wrapped, focal_user=anchor.focal_user
        )
        supervised_action = backend._action_for_physical(table, supervised_key)
    except Exception:
        supervised_key = backend._max_lagged_gain_rival(
            service.observation,
            focal_user=anchor.focal_user,
            main_key=anchor.reference_physical_key,
        )
        supervised_action = backend._action_for_physical(table, supervised_key)
    if supervised_action == anchor.reference_action:
        raise C2V04CensusRunnerError(
            "old Q2 supervised pair candidate equals the Main reference"
        )
    state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
    mask_tensor = torch.tensor(mask, dtype=torch.bool).unsqueeze(0)
    rankings: list[C2V04OldQ2Ranking] = []
    for initialization_seed in Q2_INITIALIZATION_SEEDS:
        network, _config = q2_heads[initialization_seed]
        with torch.no_grad():
            values = network(state_tensor, mask_tensor)
        q_values = np.asarray(values.detach().cpu().numpy(), dtype=np.float64)
        if q_values.shape == (1, NUM_ACTIONS):
            q_values = q_values[0]
        if q_values.shape != (NUM_ACTIONS,) or not np.all(np.isfinite(q_values)):
            raise C2V04CensusRunnerError(
                "frozen old Q2 head returned a malformed legal-action vector"
            )
        ranked = tuple(
            sorted(range(NUM_ACTIONS), key=lambda action: (-float(q_values[action]), action))
        )
        rankings.append(
            C2V04OldQ2Ranking(
                initialization_seed=initialization_seed,
                ranked_actions=ranked,
                supervised_candidate_action=int(supervised_action),
            )
        )
    return tuple(rankings)


def _phase_a_ready_outcome(
    *, pair: Any, sibling: C2V04SiblingRow
) -> dict[str, object]:
    """Project one verified physical pair into a retained Phase-A row."""

    import numpy as np

    if pair.source_route != "C2" or pair.source_rule != C2_V04_SUPPORT_COMPLETE_SOURCE_RULE:
        raise C2V04CensusRunnerError("materialized pair is not the V0.4 C2 source rule")
    for field, expected in (
        ("anchor_sha256", sibling.anchor_sha256),
        ("anchor_schedule_sha256", sibling.anchor_schedule_sha256),
        ("source_manifest_sha256", sibling.source_manifest_sha256),
        ("checkpoint_sha256", sibling.checkpoint_sha256),
        ("common_random_field_sha256", sibling.common_random_field_sha256),
    ):
        if getattr(pair, field) != expected:
            raise C2V04CensusRunnerError(
                f"materialized pair {field} disagrees with sealed sibling"
            )
    if (
        int(pair.reference_action) != sibling.reference_action
        or int(pair.candidate_action) != sibling.candidate_action
        or tuple(pair.held_physical_key) != sibling.candidate_physical_key
    ):
        raise C2V04CensusRunnerError(
            "materialized pair actions/physical key disagree with sealed sibling"
        )
    reference_rates = np.asarray(pair.reference_rates_bps, dtype=np.float64)
    candidate_rates = np.asarray(pair.candidate_rates_bps, dtype=np.float64)
    reference_power = np.asarray(pair.reference_system_power_w, dtype=np.float64)
    candidate_power = np.asarray(pair.candidate_system_power_w, dtype=np.float64)
    reference_served = np.asarray(pair.reference_served, dtype=np.bool_)
    candidate_served = np.asarray(pair.candidate_served, dtype=np.bool_)
    offsets = np.asarray(pair.offset_surplus_bits, dtype=np.float64)
    if (
        reference_rates.shape != (4, 100)
        or candidate_rates.shape != (4, 100)
        or reference_power.shape != (4,)
        or candidate_power.shape != (4,)
        or reference_served.shape != (4, 100)
        or candidate_served.shape != (4, 100)
        or offsets.shape != (3,)
    ):
        raise C2V04CensusRunnerError("materialized pair trace shape is not 4xU/3")
    delivered = float(
        pair.interval_s
        * math.fsum(
            float(candidate_rates[offset, user] - reference_rates[offset, user])
            for offset in range(1, 4)
            for user in range(reference_rates.shape[1])
        )
    )
    status = (
        C2_V04_ROW_SUPPORT_EXPIRED
        if pair.release_reason == "support_expired"
        else C2_V04_ROW_READY
    )
    return {
        "row_status": status,
        "failure_code": (
            None
            if status == C2_V04_ROW_READY
            else f"support_expired_at_offset_{int(pair.release_offset)}"
        ),
        "non_incumbent": sibling.candidate_physical_key != sibling.incumbent_physical_key,
        "release_offset": int(pair.release_offset),
        "zeta2_temporal_surplus_bits": float(pair.zeta2_temporal_surplus_bits),
        "delivered_bit_delta": delivered,
        "common_random_field_sha256": str(pair.common_random_field_sha256),
        "raw_trace": {
            "reference_rates_bps": reference_rates.tolist(),
            "candidate_rates_bps": candidate_rates.tolist(),
            "reference_system_power_w": reference_power.tolist(),
            "candidate_system_power_w": candidate_power.tolist(),
            "reference_served": reference_served.tolist(),
            "candidate_served": candidate_served.tolist(),
            "lambda_bits_per_j": float(pair.lambda_bits_per_j),
            "interval_s": float(pair.interval_s),
            "offset_surplus_bits": offsets.tolist(),
        },
    }


def _phase_a_failure_outcome(
    *, sibling: C2V04SiblingRow, error: BaseException
) -> dict[str, object]:
    """Retain a candidate failure without fabricating a target."""

    reason = getattr(error, "reason", None)
    offset = getattr(error, "forecast_offset", None)
    if isinstance(reason, str) and isinstance(offset, int) and 1 <= offset <= 3:
        return {
            "row_status": C2_V04_ROW_SUPPORT_EXPIRED,
            "failure_code": f"{reason}_at_offset_{offset}",
            "non_incumbent": sibling.candidate_physical_key != sibling.incumbent_physical_key,
            "release_offset": offset,
            "zeta2_temporal_surplus_bits": None,
            "delivered_bit_delta": None,
            "common_random_field_sha256": sibling.common_random_field_sha256,
            "raw_trace": None,
        }
    return {
        "row_status": C2_V04_ROW_FAILURE,
        "failure_code": _failure_text(error),
        "non_incumbent": sibling.candidate_physical_key != sibling.incumbent_physical_key,
        "release_offset": None,
        "zeta2_temporal_surplus_bits": None,
        "delivered_bit_delta": None,
        "common_random_field_sha256": sibling.common_random_field_sha256,
        "raw_trace": None,
    }


def _real_phase_a(
    *,
    prepared: C2V04PrepareResult,
    modules: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, object]:
    """Replay and materialize every sealed sibling, retaining all outcomes."""

    _validate_schedule_for_phase_a(prepared)
    backend_smoke = modules["backend_smoke"]
    trainer = context["trainer"]
    network_before = backend_smoke._network_snapshot(trainer)
    replay_before = len(trainer.replay)
    lambda_bits_per_j, interval_s, _calibration_file_sha256 = _production_calibration(
        modules
    )
    forensics = modules["forensics"]
    q2_heads = {
        seed: forensics._load_q2(seed) for seed in Q2_INITIALIZATION_SEEDS
    }
    anchors_by_seed = {
        seed: tuple(
            sorted(
                (anchor for anchor in prepared.schedule.anchors if anchor.source_seed == seed),
                key=lambda anchor: (anchor.anchor_step, anchor.focal_user, anchor.anchor_sha256),
            )
        )
        for seed in prepared.selected_source_seeds
    }
    outcomes: dict[object, Mapping[str, object]] = {}
    rankings: dict[tuple[int, str, str, int], tuple[C2V04OldQ2Ranking, ...]] = {}
    for source_seed in prepared.selected_source_seeds:
        for anchor in anchors_by_seed.get(source_seed, ()):
            replay = _replay_main_to_step(
                source_seed=source_seed,
                target_step=anchor.anchor_step,
                modules=modules,
                context=context,
            )
            if int(replay["observation"].step_index) != anchor.anchor_step:
                raise C2V04CensusRunnerError("replayed anchor step changed")
            service = _real_service_for_sealed_anchor(
                anchor=anchor,
                replay=replay,
                modules=modules,
                context=context,
            )
            rankings[anchor.intervention_key] = _old_q2_rankings_for_anchor(
                anchor=anchor,
                service=service,
                q2_heads=q2_heads,
                modules=modules,
            )
            for sibling in prepared.schedule.rows:
                if sibling.intervention_key != anchor.intervention_key:
                    continue
                try:
                    candidate = service.prepare_one_candidate(
                        focal_user=anchor.focal_user,
                        candidate_key=sibling.candidate_physical_key,
                        source_rule=C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
                    )
                    if (
                        candidate.source_rule != C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
                        or candidate.phase != "anchor"
                        or candidate.build is not None
                        or tuple(candidate.candidate_key) != sibling.candidate_physical_key
                    ):
                        raise C2V04CensusRunnerError(
                            "prepared candidate crossed the pre-forecast boundary"
                        )
                    materialized = real_main_continuation_materializer(
                        candidate,
                        modules=modules,
                        anchor_schedule_sha256=anchor.anchor_schedule_sha256,
                        source_manifest_sha256=context["source_manifest_sha256"],
                        lambda_bits_per_j=lambda_bits_per_j,
                        interval_s=interval_s,
                    )
                    outcomes[sibling.sibling_key] = _phase_a_ready_outcome(
                        pair=materialized["pair"],
                        sibling=sibling,
                    )
                except C2V04CensusRunnerError:
                    raise
                except Exception as error:
                    # A candidate-level physical/forecast failure is retained
                    # as a row, while the schedule and its lineage remain
                    # immutable.  No alternative candidate is substituted.
                    outcomes[sibling.sibling_key] = _phase_a_failure_outcome(
                        sibling=sibling, error=error
                    )
    expected = {row.sibling_key for row in prepared.schedule.rows}
    if set(outcomes) != expected:
        raise C2V04CensusRunnerError(
            "phase-A production did not retain exactly the 324 scheduled siblings"
        )
    if set(rankings) != {anchor.intervention_key for anchor in prepared.schedule.anchors}:
        raise C2V04CensusRunnerError(
            "phase-A production did not retain exactly one old-Q2 ranking cluster per anchor"
        )
    if not backend_smoke._networks_equal(trainer, network_before):
        raise C2V04CensusRunnerError("phase-A materialization mutated Main networks")
    if len(trainer.replay) != replay_before:
        raise C2V04CensusRunnerError("phase-A materialization mutated Main replay")
    return phase_a_census(prepared, outcomes, rankings)


def _production_prepare_receipt(
    *,
    prepared: C2V04PrepareResult,
    context: Mapping[str, Any],
    prereg_path: Path,
    tle_root: Path,
    source_manifest_file_sha256: str,
    prepare_file_sha256: str,
    schedule_file_sha256: str,
) -> dict[str, object]:
    """Build the write-once receipt that authenticates a V0.4 prepare."""

    return {
        "schema": "multi-catfish-mcrl-v04-c2-support-complete-prepare-receipt-v1",
        "status": "PREPARED",
        "claim_ceiling": CLAIM_CEILING,
        "source_rule": C2_V04_SUPPORT_COMPLETE_SOURCE_RULE,
        "prereg_path": str(prereg_path.resolve()),
        "prereg_file_sha256": hashlib.sha256(prereg_path.read_bytes()).hexdigest(),
        "prereg_sha256": str(context["record"].digest),
        "tle_root": str(tle_root.resolve()),
        "source_manifest_sha256": str(context["source_manifest_sha256"]),
        "source_manifest_file_sha256": source_manifest_file_sha256,
        "checkpoint_sha256": str(context["checkpoint_sha256"]),
        "environment_source_sha256": str(context["environment_source_sha256"]),
        "reward_source_sha256": str(context["reward_source_sha256"]),
        "policy_sha256": str(context["policy_sha256"]),
        "prepare_sha256": prepared.prepare_sha256,
        "prepare_file_sha256": prepare_file_sha256,
        "schedule_sha256": prepared.schedule.schedule_sha256,
        "schedule_file_sha256": schedule_file_sha256,
        "scanned_source_seeds": list(prepared.scanned_source_seeds),
        "selected_source_seeds": list(prepared.selected_source_seeds),
        "common_random_field_roots": prepared.to_mapping()[
            "common_random_field_roots"
        ],
        "counterfactual_outcomes_evaluated": False,
        "training_run": False,
        "test_opened": False,
        "held_out_ee_evaluated": False,
    }


def _authenticate_production_prepare(
    *,
    output_dir: Path,
    prereg_path: Path,
    modules: Mapping[str, Any],
) -> tuple[C2V04PrepareResult, dict[str, object]]:
    """Authenticate all prepare bytes before any Phase-A replay."""

    from mcrl.runtime.prereg import read_prereg

    if output_dir.is_symlink() or not output_dir.is_dir():
        raise C2V04CensusRunnerError(
            "phase-A output-dir must be the regular sealed prepare directory"
        )
    source_payload, source_file_sha256 = _read_canonical_json(
        output_dir / "source-manifest.json"
    )
    expected_source = _production_source_manifest(modules)
    if source_payload != expected_source:
        raise C2V04CensusRunnerError(
            "current V0.4 source closure differs from the sealed prepare manifest"
        )
    receipt, receipt_file_sha256 = _read_canonical_json(
        output_dir / "prepare-receipt.json"
    )
    seal, _seal_file_sha256 = _read_canonical_json(
        output_dir / "prepare-receipt-seal.json"
    )
    if (
        receipt.get("schema")
        != "multi-catfish-mcrl-v04-c2-support-complete-prepare-receipt-v1"
        or receipt.get("status") != "PREPARED"
        or receipt.get("claim_ceiling") != CLAIM_CEILING
        or receipt.get("source_rule") != C2_V04_SUPPORT_COMPLETE_SOURCE_RULE
        or receipt.get("source_manifest_sha256")
        != expected_source["source_manifest_sha256"]
        or receipt.get("source_manifest_file_sha256") != source_file_sha256
        or receipt.get("counterfactual_outcomes_evaluated") is not False
        or receipt.get("training_run") is not False
        or receipt.get("test_opened") is not False
        or receipt.get("held_out_ee_evaluated") is not False
    ):
        raise C2V04CensusRunnerError("prepare receipt is stale or unsafe")
    if (
        seal.get("schema")
        != "multi-catfish-mcrl-v04-c2-support-complete-prepare-receipt-seal-v1"
        or seal.get("receipt_file_sha256") != receipt_file_sha256
        or seal.get("receipt_body_sha256") != _canonical_sha256(receipt)
        or seal.get("claim_ceiling") != CLAIM_CEILING
        or seal.get("status") != "PREPARED"
    ):
        raise C2V04CensusRunnerError("prepare receipt seal is invalid")
    try:
        actual_prereg_sha256 = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
        record = read_prereg(prereg_path)
    except (OSError, ValueError) as error:
        raise C2V04CensusRunnerError("phase-A preregistration is unreadable") from error
    if (
        record.digest != receipt.get("prereg_sha256")
        or actual_prereg_sha256 != receipt.get("prereg_file_sha256")
    ):
        raise C2V04CensusRunnerError(
            "phase-A preregistration bytes differ from the sealed prepare"
        )
    prepare_path = output_dir / "prepare.json"
    try:
        prepared = read_c2_v04_prepare_artifact(
            prepare_path,
            expected_file_sha256=receipt.get("prepare_file_sha256"),  # type: ignore[arg-type]
        )
    except Exception as error:
        # Keep every malformed/missing prepare byte behind the server-facing
        # runner error boundary.  In particular, the data-only schedule
        # contract raises its own versioned exception type.
        raise C2V04CensusRunnerError("sealed V0.4 prepare artifact is invalid") from error
    schedule_path = output_dir / "schedule.json"
    try:
        schedule = read_c2_v04_support_complete_schedule(
            schedule_path,
            expected_file_sha256=receipt.get("schedule_file_sha256"),  # type: ignore[arg-type]
        )
    except C2V04SiblingScheduleContractError as error:
        raise C2V04CensusRunnerError("sealed V0.4 schedule is invalid") from error
    if (
        schedule != prepared.schedule
        or schedule.schedule_sha256 != receipt.get("schedule_sha256")
        or prepared.prepare_sha256 != receipt.get("prepare_sha256")
        or prepared.to_mapping().get("common_random_field_roots")
        != receipt.get("common_random_field_roots")
        or tuple(prepared.scanned_source_seeds)
        != tuple(receipt.get("scanned_source_seeds", ()))
        or tuple(prepared.selected_source_seeds)
        != tuple(receipt.get("selected_source_seeds", ()))
    ):
        raise C2V04CensusRunnerError(
            "prepare/schedule bytes disagree with the authenticated receipt"
        )
    # Receipt lineage is not merely metadata: every sealed intervention must
    # be tied to the exact checkpoint, source closure, and policy that the
    # server is about to replay.  Check all 12 anchors instead of trusting the
    # first one, so a mixed-lineage schedule cannot pass authentication.
    for anchor in prepared.schedule.anchors:
        if (
            anchor.checkpoint_sha256 != receipt.get("checkpoint_sha256")
            or anchor.source_manifest_sha256
            != receipt.get("source_manifest_sha256")
            or anchor.policy_sha256 != receipt.get("policy_sha256")
        ):
            raise C2V04CensusRunnerError(
                "sealed anchor lineage disagrees with the prepare receipt"
            )
    return prepared, receipt


def _run_production_prepare(
    *, prereg_path: Path, tle_root: Path, output_dir: Path
) -> dict[str, object]:
    """Server-facing prepare command; no forecast is reachable in this phase."""

    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite V0.4 authority: {output_dir}")
    modules = _production_modules()
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.prepare-", dir=output_dir.parent)
    )
    try:
        with tempfile.TemporaryDirectory(prefix="mcrl-v04-prepare-runtime-") as temporary:
            context = _production_main_context(
                modules=modules,
                prereg_path=prereg_path,
                tle_root=tle_root,
                temporary=Path(temporary),
            )
            network_before = modules["backend_smoke"]._network_snapshot(
                context["trainer"]
            )
            replay_before = len(context["trainer"].replay)
            scanner = _real_tle_topology_scanner(
                modules=modules, context=context
            )
            prepared = prepare_c2_v04_census(scanner)
            if not modules["backend_smoke"]._networks_equal(
                context["trainer"], network_before
            ) or len(context["trainer"].replay) != replay_before:
                raise C2V04CensusRunnerError(
                    "prepare topology scan mutated Main state or replay"
                )
        source_manifest_file_sha256 = _write_once_json(
            staging / "source-manifest.json", context["source_manifest"]
        )
        prepare_file_sha256 = write_c2_v04_prepare_artifact(
            staging / "prepare.json", prepared
        )
        schedule_file_sha256 = write_c2_v04_support_complete_schedule(
            staging / "schedule.json", prepared.schedule
        )
        receipt = _production_prepare_receipt(
            prepared=prepared,
            context=context,
            prereg_path=prereg_path,
            tle_root=tle_root,
            source_manifest_file_sha256=source_manifest_file_sha256,
            prepare_file_sha256=prepare_file_sha256,
            schedule_file_sha256=schedule_file_sha256,
        )
        receipt_file_sha256 = _write_once_json(
            staging / "prepare-receipt.json", receipt
        )
        _write_once_json(
            staging / "prepare-receipt-seal.json",
            {
                "schema": "multi-catfish-mcrl-v04-c2-support-complete-prepare-receipt-seal-v1",
                "status": "PREPARED",
                "claim_ceiling": CLAIM_CEILING,
                "receipt_file_sha256": receipt_file_sha256,
                "receipt_body_sha256": _canonical_sha256(receipt),
                "prepare_sha256": prepared.prepare_sha256,
                "schedule_sha256": prepared.schedule.schedule_sha256,
            },
        )
        if output_dir.exists() or output_dir.is_symlink():
            raise FileExistsError(f"refusing to overwrite V0.4 authority: {output_dir}")
        staging.replace(output_dir)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "status": "PREPARED",
        "schema": C2_V04_PREPARE_ARTIFACT_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "prepare_sha256": prepared.prepare_sha256,
        "schedule_sha256": prepared.schedule.schedule_sha256,
        "selected_source_seeds": list(prepared.selected_source_seeds),
        "row_count": len(prepared.schedule.rows),
        "counterfactual_outcomes_evaluated": False,
        "training_run": False,
        "test_opened": False,
        "held_out_ee_evaluated": False,
    }


def _run_production_phase_a(
    *, prereg_path: Path, tle_root: Path, output_dir: Path
) -> dict[str, object]:
    """Server-facing Phase-A command for all 324 sealed siblings."""

    modules = _production_modules()
    prepared, receipt = _authenticate_production_prepare(
        output_dir=output_dir, prereg_path=prereg_path, modules=modules
    )
    result_path = output_dir / "phase-a-result.json"
    seal_path = output_dir / "phase-a-seal.json"
    if result_path.exists() or result_path.is_symlink() or seal_path.exists() or seal_path.is_symlink():
        raise FileExistsError("refusing to overwrite an existing V0.4 Phase-A result")
    with tempfile.TemporaryDirectory(prefix="mcrl-v04-phase-a-runtime-") as temporary:
        context = _production_main_context(
            modules=modules,
            prereg_path=prereg_path,
            tle_root=tle_root,
            temporary=Path(temporary),
        )
        for field in (
            "checkpoint_sha256",
            "environment_source_sha256",
            "reward_source_sha256",
            "policy_sha256",
            "source_manifest_sha256",
        ):
            if context[field] != receipt.get(field):
                raise C2V04CensusRunnerError(
                    f"phase-A live {field} disagrees with prepare receipt"
                )
        result = _real_phase_a(
            prepared=prepared,
            modules=modules,
            context=context,
        )
    phase_a_file_sha256 = _write_once_json(output_dir / "phase-a-result.json", result)
    _write_once_json(
        output_dir / "phase-a-seal.json",
        {
            "schema": "multi-catfish-mcrl-v04-c2-support-complete-phase-a-seal-v1",
            "status": "PHASE_A_COMPLETE",
            "claim_ceiling": CLAIM_CEILING,
            "phase_a_sha256": result["phase_a_sha256"],
            "phase_a_file_sha256": phase_a_file_sha256,
            "prepare_sha256": prepared.prepare_sha256,
            "schedule_sha256": prepared.schedule.schedule_sha256,
            "row_count": result["row_count"],
            "decision": result["decision"],
            "training_run": False,
            "test_opened": False,
            "held_out_ee_evaluated": False,
        },
    )
    return {
        "status": "PHASE_A_COMPLETE",
        "schema": C2_V04_PHASE_A_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "phase_a_sha256": result["phase_a_sha256"],
        "phase_a_file_sha256": phase_a_file_sha256,
        "row_count": result["row_count"],
        "decision": result["decision"],
        "training_run": False,
        "test_opened": False,
        "held_out_ee_evaluated": False,
    }


def sibling_key_text(key: tuple[int, str, str, int, tuple[int, int]]) -> str:
    """Canonical JSON key for outcome maps crossing a JSON boundary."""

    return json.dumps(
        [key[0], key[1], key[2], key[3], [key[4][0], key[4][1]]],
        separators=(",", ":"),
    )


def real_tle_topology_scanner(
    source_seed: int,
    *,
    modules: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> Iterable[C2V04TopologyAnchor]:
    """Materialize one real seed's topology through explicit injected seams.

    The keyword-only ``modules`` and ``context`` arguments are intentional:
    importing this module never loads torch or a checkpoint, and callers must
    bind the frozen Main/TLE context before asking for a scan.
    """

    if modules is None or context is None:
        raise C2V04CensusRunnerError(
            "real_tle_topology_scanner requires an authenticated production context"
        )
    return _real_tle_topology_scanner(modules=modules, context=context)(source_seed)


def real_main_continuation_materializer(
    prepared: Any,
    *,
    modules: Mapping[str, Any] | None = None,
    anchor_schedule_sha256: str | None = None,
    source_manifest_sha256: str | None = None,
    lambda_bits_per_j: float | None = None,
    interval_s: float | None = None,
) -> Mapping[str, object]:
    """Run the proven capture -> forecast -> materialize sequence once.

    Every production argument is keyword-only and required together.  The
    one-argument compatibility form fails closed rather than allowing an old
    caller to materialize an unauthenticated row.
    """

    if (
        modules is None
        or anchor_schedule_sha256 is None
        or source_manifest_sha256 is None
        or lambda_bits_per_j is None
        or interval_s is None
    ):
        raise C2V04CensusRunnerError(
            "real_main_continuation_materializer requires an authenticated production context"
        )
    if getattr(prepared, "source_rule", None) != C2_V04_SUPPORT_COMPLETE_SOURCE_RULE:
        raise C2V04CensusRunnerError(
            "materializer received a non-V0.4 C2 source rule"
        )
    pair_smoke = modules["pair_smoke"]
    materialized = pair_smoke.capture_and_materialize_q2_pair(
        prepared,
        anchor_schedule_sha256=anchor_schedule_sha256,
        source_manifest_sha256=source_manifest_sha256,
        lambda_bits_per_j=float(lambda_bits_per_j),
        interval_s=float(interval_s),
    )
    pair = materialized.pair
    return {"materialized": materialized, "pair": pair}


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--prereg", type=Path, required=True)
    prepare_parser.add_argument("--tle-root", type=Path, required=True)
    prepare_parser.add_argument("--output-dir", type=Path, required=True)
    phase_parser = subparsers.add_parser("phase-a", aliases=("generate",))
    phase_parser.add_argument("--prereg", type=Path, required=True)
    phase_parser.add_argument("--tle-root", type=Path, required=True)
    phase_parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = _run_production_prepare(
            prereg_path=args.prereg,
            tle_root=args.tle_root,
            output_dir=args.output_dir,
        )
    elif args.command in {"phase-a", "generate"}:
        result = _run_production_phase_a(
            prereg_path=args.prereg,
            tle_root=args.tle_root,
            output_dir=args.output_dir,
        )
    else:  # pragma: no cover - argparse enforces the subcommand set
        raise C2V04CensusRunnerError("unknown V0.4 command")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI is a guarded seam
    raise SystemExit(_cli())


__all__ = [
    "C2_V04_CENSUS_SCHEMA",
    "C2_V04_PHASE_A_ROW_SCHEMA",
    "C2_V04_PHASE_A_SCHEMA",
    "C2_V04_PREPARE_ARTIFACT_SCHEMA",
    "C2_V04_PREPARE_SCHEMA",
    "C2V04CensusRunnerError",
    "C2V04OldQ2Ranking",
    "C2V04PhaseARow",
    "C2V04PrepareResult",
    "C2V04TopologyAnchor",
    "C2V04TopologyFocal",
    "DESIGN_ONLY_SOURCE_SEEDS",
    "EXPECTED_CLUSTERS",
    "EXPECTED_SIBLINGS",
    "KAPPA_BITS",
    "Q2_INITIALIZATION_SEEDS",
    "build_c2_v04_support_complete_schedule",
    "phase_a_census",
    "prepare_c2_v04_census",
    "read_c2_v04_prepare_artifact",
    "_real_phase_a",
    "_real_tle_topology_scanner",
    "real_main_continuation_materializer",
    "real_tle_topology_scanner",
    "sibling_key_text",
    "write_c2_v04_prepare_artifact",
]
