#!/usr/bin/env python3
"""Run isolated TRAIN C1/C2 target-generation mode/world shards.

Each authenticated mode/world shard is an independent source-generation job.
They run concurrently, then are authenticated and merged by schedule identity;
no learner, episode policy, or TEST split is opened.  A final output directory
is write-once and receives either COMPLETE or FAILED.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
GENERATOR = HERE.parent / "multi-catfish-v023-c1c2-target-generation" / "generate_v023_c1c2_targets.py"
SEALER = HERE / "seal_v023_c1c2_target_output.py"
SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-v1"
SCHEDULE_SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-schedule-v1"
SHARD_STATUS_SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-shard-status-v1"
USERS = 100
SHARD_MODES = ("informed", "neutral")
SHARD_FAMILIES = ("C1", "C2")
OPS3_SELECTED_PAIR_SCHEMA = "multi-catfish-mcrl-v023-repriced-ops3-selected-pair-dataset-v1"
OPS3_TARGET_UNIT = "normalized-repriced-ops3-delta-over-kappa"
OPS3_HORIZON = 3
OPS3_FEATURE_DIM = 16


class ControllerError(RuntimeError):
    pass


def _canonical(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"


def _canonical_payload(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _schedule_sha256(schedule: Mapping[str, Mapping[str, object]]) -> str:
    payload = {"schema": SCHEDULE_SCHEMA, "shards": dict(schedule)}
    return hashlib.sha256(_canonical_payload(payload)).hexdigest()


def _sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ControllerError(f"expected regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_receipt(root: Path) -> dict[str, Any]:
    receipt_path = root / "receipt.json"
    manifest = root / "MANIFEST.sha256"
    if receipt_path.is_symlink() or manifest.is_symlink() or not receipt_path.is_file() or not manifest.is_file():
        raise ControllerError(f"mode shard is missing receipt/manifest: {root}")
    raw = receipt_path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ControllerError(f"mode receipt is malformed: {root}") from error
    if raw != _canonical(payload) or not isinstance(payload, dict):
        raise ControllerError(f"mode receipt is not canonical: {root}")
    if payload.get("schema") != SCHEMA or payload.get("status") != "TARGETS_MATERIALIZED_TRAIN":
        raise ControllerError(f"mode receipt has an unexpected schema/status: {root}")
    if payload.get("claim_ceiling") != CLAIM_CEILING:
        raise ControllerError("mode receipt claim ceiling drifted")
    if any(payload.get(field) is not False for field in ("training_or_replay_write", "learner_update", "test_split_opened")):
        raise ControllerError("mode receipt crosses the no-training boundary")
    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64 or parts[1] in listed:
            raise ControllerError("mode manifest is malformed")
        listed[parts[1]] = parts[0]
    if listed.get("receipt.json") != _sha(receipt_path):
        raise ControllerError("mode manifest does not authenticate receipt")
    for relative, expected in listed.items():
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or _sha(path) != expected:
            raise ControllerError(f"mode manifest hash drifted: {relative}")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    } - {"MANIFEST.sha256"}
    if actual != set(listed):
        raise ControllerError("mode manifest closure drifted")
    return payload


def _load_generator() -> Any:
    name = "mcrl_v023_c1c2_target_generation_controller_schedule"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, GENERATOR)
    if spec is None or spec.loader is None:
        raise ControllerError(f"target generator is unavailable: {GENERATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        sys.modules.pop(name, None)
        raise ControllerError("target generator schedule module failed to import") from error
    return module


# The frozen producer owns the shard receipt contract.  Import this value from
# the same path-bound generator module used for schedule and code-closure
# authentication so a consumer-local literal cannot silently drift again.
CLAIM_CEILING = _load_generator().CLAIM_CEILING


def _load_ops3_samples_per_step() -> int:
    """Read the native D2 sample count from the authoritative live producer."""

    src = HERE.parents[1] / "src"
    src_text = str(src)
    inserted = src_text not in sys.path
    if inserted:
        sys.path.insert(0, src_text)
    try:
        module = importlib.import_module("mcrl.runtime.ee_axis_ops3_live")
        value = module.D2_SUBSTEPS_PER_DECISION
    except Exception as error:
        raise ControllerError("OPS-3 live sample cadence is unavailable") from error
    finally:
        if inserted:
            sys.path.remove(src_text)
    if type(value) is not int or value <= 0:
        raise ControllerError("OPS-3 live sample cadence is malformed")
    return value


# project_ops3_anchor defines its native window as
# ``samples = horizon * anchor.d2_substeps_per_decision`` and populates both
# future_d2_indices and sample_times_utc over that window.  Import the canonical
# substep count through that producer module instead of duplicating its value.
OPS3_SAMPLES_PER_STEP = _load_ops3_samples_per_step()


def _expected_schedule(args: argparse.Namespace) -> dict[str, dict[str, object]]:
    """Authenticate the sealed source plan and derive every mode/world shard."""

    generator = _load_generator()
    sealed = generator.load_sealed_inputs(
        Path(args.capture), Path(args.materialization_dir)
    )
    return generator.build_schedule(sealed, modes=SHARD_MODES)


def _validate_output_code_closure(receipt: Mapping[str, object]) -> None:
    """Require every target receipt to bind the live OPS-3/D40 closure."""

    closure = receipt.get("code_closure")
    if not isinstance(closure, Mapping):
        raise ControllerError("target receipt omits its output code closure")
    expected = _load_generator()._output_code_closure()
    if dict(closure) != expected:
        raise ControllerError("target receipt output code closure drifted from the live OPS-3/D40 closure")
    closure_sha256 = receipt.get("code_closure_sha256")
    if closure_sha256 != hashlib.sha256(_canonical_payload(expected)).hexdigest():
        raise ControllerError("target receipt output code closure digest drifted")


def _shard_sort_key(key: str) -> tuple[int, int]:
    try:
        mode, world_text = key.split(":", 1)
        world = int(world_text)
    except (AttributeError, TypeError, ValueError) as error:
        raise ControllerError(f"invalid mode/world shard key: {key!r}") from error
    if mode not in SHARD_MODES:
        raise ControllerError(f"invalid mode/world shard mode: {key!r}")
    return SHARD_MODES.index(mode), world


def _binding_identity(family: str, binding: Mapping[str, object]) -> dict[str, object]:
    fields = (
        (
            "source_anchor_sha256",
            "source_record_sha256",
            "source_seed",
            "world",
            "step_index",
            "focal_user",
            "reference_action",
            "candidate_action",
            "candidate_physical_key",
            "source_rule",
        )
        if family == "C1"
        else (
            "source_anchor_sha256",
            "world",
            "step_index",
            "focal_user",
            "reference_action",
            "candidate_action",
            "candidate_physical_key",
            "source_rule",
        )
    )
    if any(field not in binding for field in fields):
        raise ControllerError(f"{family} row binding omits an authenticated identity field")
    return {field: binding[field] for field in fields}


def _binding_sort_key(
    family: str, binding: Mapping[str, object]
) -> tuple[int, int, tuple[int, ...], str]:
    identity = _binding_identity(family, binding)
    return (
        int(identity["step_index"]),
        int(identity["focal_user"]),
        tuple(int(value) for value in identity["candidate_physical_key"]),
        str(identity["source_anchor_sha256"]),
    )


def _finite_number(value: object, *, field: str) -> float:
    """Return one finite JSON number, rejecting bools and string coercion."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ControllerError(f"OPS-3 {field} is not a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ControllerError(f"OPS-3 {field} is not finite")
    return result


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ControllerError(f"OPS-3 {field} is not a lowercase SHA-256")
    return value


def _ops3_row(
    row: object,
    *,
    binding: Mapping[str, object],
    mode: str,
    world: int,
) -> None:
    """Authenticate one already-normalized OPS-3 selected pair.

    This is deliberately a consumer-side schema check.  It does not recreate
    the physical target, and therefore cannot introduce a second kappa
    normalization.  The sole admissible unit is the producer's declared
    normalized surface, where ``target_delta = candidate - reference``.
    """

    if not isinstance(row, Mapping):
        raise ControllerError("OPS-3 selected-pair row is malformed")
    if row.get("schema") != OPS3_SELECTED_PAIR_SCHEMA:
        raise ControllerError("C2 dataset is not the current OPS-3 selected-pair schema")
    if row.get("mode") != mode or row.get("world") != world:
        raise ControllerError("OPS-3 selected-pair mode/world drifted")
    if row.get("target_unit") != OPS3_TARGET_UNIT:
        raise ControllerError("OPS-3 selected-pair target unit would permit a second kappa normalization")
    for field in (
        "source_anchor_sha256",
        "schedule_sha256",
    ):
        _digest(row.get(field), field=field)
    for field in (
        "source_anchor_sha256",
        "world",
        "step_index",
        "focal_user",
        "reference_action",
        "candidate_action",
        "candidate_physical_key",
        "source_rule",
        "schedule_sha256",
        "target_delta",
        "target_unit",
    ):
        if row.get(field) != binding.get(field):
            raise ControllerError(f"OPS-3 selected-pair/binding disagreement: {field}")

    mask = row.get("action_mask")
    features = row.get("q2_features")
    state = row.get("q2_state")
    if not isinstance(mask, list) or not mask or any(type(value) is not bool for value in mask):
        raise ControllerError("OPS-3 action mask is malformed")
    action_count = len(mask)
    if not isinstance(features, list) or len(features) != action_count:
        raise ControllerError("OPS-3 feature surface/action mask drifted")
    if not isinstance(state, list) or len(state) != action_count * OPS3_FEATURE_DIM:
        raise ControllerError("OPS-3 state dimension does not match its feature surface")
    feature_surface: list[list[float]] = []
    for action, feature_row in enumerate(features):
        if not isinstance(feature_row, list) or len(feature_row) != OPS3_FEATURE_DIM:
            raise ControllerError("OPS-3 feature row width drifted")
        feature_surface.append(
            [
                _finite_number(value, field=f"features[{action}]")
                for value in feature_row
            ]
        )
    # The producer writes q2_state after a float32 feature projection.  Do not
    # use a loose allclose: a changed action ordering would otherwise pass.
    import struct

    expected_state = [
        struct.unpack("!f", struct.pack("!f", feature_surface[action][feature]))[0]
        for feature in range(OPS3_FEATURE_DIM)
        for action in range(action_count)
    ]
    actual_state = [_finite_number(value, field="q2_state") for value in state]
    if actual_state != expected_state:
        raise ControllerError("OPS-3 q2_state is not the target-free feature projection")

    reference = row.get("reference_action")
    candidate = row.get("candidate_action")
    q1_reference = row.get("q1_reference_action")
    if any(type(value) is not int for value in (reference, candidate, q1_reference)):
        raise ControllerError("OPS-3 action indices are malformed")
    if not (0 <= reference < action_count and 0 <= candidate < action_count):
        raise ControllerError("OPS-3 selected-pair action is out of range")
    if not bool(mask[reference]) or not bool(mask[candidate]):
        raise ControllerError("OPS-3 selected-pair action is not legal under its mask")
    if not 0 <= q1_reference < action_count:
        raise ControllerError("OPS-3 Q1 reference action is out of range")

    target_reference = _finite_number(row.get("target_reference_value"), field="target_reference_value")
    target_candidate = _finite_number(row.get("target_candidate_value"), field="target_candidate_value")
    target_delta = _finite_number(row.get("target_delta"), field="target_delta")
    if target_delta != target_candidate - target_reference:
        raise ControllerError("OPS-3 target delta is not the exact normalized surface difference")

    horizon = row.get("horizon")
    if type(horizon) is not int or not 0 <= horizon <= OPS3_HORIZON:
        raise ControllerError("OPS-3 terminal horizon drifted")
    for field in ("persistence", "rate_bps", "marginal_power_w", "required_power_w"):
        values = row.get(field)
        if not isinstance(values, list) or len(values) != OPS3_HORIZON:
            raise ControllerError(f"OPS-3 {field} horizon surface drifted")
        for offset, values_at_offset in enumerate(values):
            if not isinstance(values_at_offset, list) or len(values_at_offset) != action_count:
                raise ControllerError(f"OPS-3 {field} action surface drifted")
            for value in values_at_offset:
                numeric = _finite_number(value, field=field)
                if offset >= horizon and numeric != 0.0:
                    raise ControllerError("OPS-3 terminal H_t truncation leaked a future term")

    provenance = row.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ControllerError("OPS-3 selected-pair provenance is missing")
    for field in (
        "ops3_anchor_sha256",
        "ops3_tracker_seed_sha256",
        "ops3_projection_sha256",
    ):
        _digest(provenance.get(field), field=field)
    future_d2 = provenance.get("ops3_future_d2_indices")
    sample_times = provenance.get("ops3_sample_times_utc")
    offset_times = provenance.get("ops3_offset_times_utc")
    if any(not isinstance(value, list) for value in (future_d2, sample_times, offset_times)):
        raise ControllerError("OPS-3 native D2 provenance is malformed")
    if (
        len(offset_times) != horizon
        or len(future_d2) != len(sample_times)
        or len(future_d2) != horizon * OPS3_SAMPLES_PER_STEP
    ):
        raise ControllerError("OPS-3 native D2 provenance does not align with H_t")
    if any(type(value) is not int for value in future_d2):
        raise ControllerError("OPS-3 future D2 index is malformed")
    for field, values in (
        ("sample time", sample_times),
        ("offset time", offset_times),
    ):
        for value in values:
            if not isinstance(value, str):
                raise ControllerError(f"OPS-3 {field} is not an ISO string")
            try:
                dt.datetime.fromisoformat(value)
            except ValueError as error:
                raise ControllerError(f"OPS-3 {field} is not an ISO string") from error
    if binding.get("ops3_anchor_sha256") != provenance.get("ops3_anchor_sha256"):
        raise ControllerError("OPS-3 anchor provenance disagrees with row binding")
    if binding.get("ops3_projection_sha256") != provenance.get("ops3_projection_sha256"):
        raise ControllerError("OPS-3 projection provenance disagrees with row binding")


def _validate_ops3_dataset(
    root: Path,
    metadata: Mapping[str, object],
    bindings: list[object],
    *,
    mode: str,
    world: int,
    source_manifest_sha256: object,
) -> None:
    """Validate a C2 file before a shard may enter the merged output."""

    relative = Path(str(metadata.get("path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative.name != relative.as_posix():
        raise ControllerError("OPS-3 dataset path is unsafe")
    path = root / relative
    try:
        raw = path.read_bytes()
        dataset = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ControllerError("OPS-3 dataset is not canonical ASCII JSON") from error
    if raw != _canonical(dataset) or not isinstance(dataset, Mapping):
        raise ControllerError("OPS-3 dataset is not canonical")
    if dataset.get("schema") != OPS3_SELECTED_PAIR_SCHEMA:
        raise ControllerError("C2 dataset schema is stale")
    if dataset.get("target_unit") != OPS3_TARGET_UNIT:
        raise ControllerError("C2 dataset target unit is stale")
    if dataset.get("source_manifest_sha256") != source_manifest_sha256:
        raise ControllerError("OPS-3 dataset source manifest drifted")
    _digest(dataset.get("checkpoint_sha256"), field="checkpoint_sha256")
    for field in ("lambda_bits_per_j", "kappa_bits"):
        value = dataset.get(field)
        if not isinstance(value, str):
            raise ControllerError(f"OPS-3 dataset {field} is not an authenticated hex scalar")
        try:
            parsed = float.fromhex(value)
        except ValueError as error:
            raise ControllerError(f"OPS-3 dataset {field} is not a float hex scalar") from error
        if not math.isfinite(parsed) or parsed <= 0.0:
            raise ControllerError(f"OPS-3 dataset {field} is not positive")
    rows = dataset.get("rows")
    if not isinstance(rows, list) or len(rows) != len(bindings):
        raise ControllerError("OPS-3 dataset row count disagrees with bindings")
    if metadata.get("schema") != OPS3_SELECTED_PAIR_SCHEMA:
        raise ControllerError("OPS-3 dataset metadata schema drifted")
    if metadata.get("dataset_sha256") != hashlib.sha256(_canonical_payload(dataset)).hexdigest():
        raise ControllerError("OPS-3 dataset metadata canonical digest drifted")
    for row, binding in zip(rows, bindings, strict=True):
        if not isinstance(binding, Mapping):
            raise ControllerError("OPS-3 row binding is malformed")
        _ops3_row(row, binding=binding, mode=mode, world=world)


def _validate_shard(
    key: str,
    root: Path,
    receipt: Mapping[str, object],
    expected: Mapping[str, object],
) -> None:
    mode, world_text = key.split(":", 1)
    world = int(world_text)
    if receipt.get("shard") != {"mode": mode, "world": world}:
        raise ControllerError(f"mode/world shard identity drifted: {key}")
    schedule = receipt.get("schedule")
    if not isinstance(schedule, Mapping):
        raise ControllerError(f"mode/world shard schedule is missing: {key}")
    if schedule.get("schema") != SCHEDULE_SCHEMA:
        raise ControllerError(f"mode/world shard schedule schema drifted: {key}")
    shard_schedule = schedule.get("shards")
    if not isinstance(shard_schedule, Mapping) or dict(shard_schedule) != {key: dict(expected)}:
        raise ControllerError(f"mode/world shard schedule drifted: {key}")
    if schedule.get("sha256") != _schedule_sha256({key: expected}):
        raise ControllerError(f"mode/world shard schedule hash drifted: {key}")

    datasets = receipt.get("datasets")
    row_bindings = receipt.get("row_bindings")
    if not isinstance(datasets, Mapping) or not isinstance(row_bindings, Mapping):
        raise ControllerError(f"mode/world shard datasets/bindings are missing: {key}")
    source = receipt.get("source")
    if not isinstance(source, Mapping):
        raise ControllerError(f"mode/world shard source receipt is missing: {key}")
    _validate_output_code_closure(receipt)
    source_manifest = source.get("source_manifest_sha256")
    for family in SHARD_FAMILIES:
        expected_rows = expected.get(family)
        if not isinstance(expected_rows, list):
            raise ControllerError(f"mode/world expected schedule is malformed: {key}/{family}")
        family_datasets = datasets.get(family)
        family_bindings = row_bindings.get(family)
        if not isinstance(family_datasets, Mapping) or not isinstance(family_bindings, list):
            raise ControllerError(f"mode/world shard {family} payload is malformed: {key}")
        identities: list[dict[str, object]] = []
        for binding in family_bindings:
            if not isinstance(binding, Mapping):
                raise ControllerError(
                    f"mode/world shard row binding is malformed: {key}/{family}"
                )
            if binding.get("mode") != mode:
                raise ControllerError(
                    f"mode/world shard row binding mode drifted: {key}/{family}"
                )
            identities.append(_binding_identity(family, binding))
        if list(family_bindings) != sorted(
            family_bindings, key=lambda binding: _binding_sort_key(family, binding)
        ):
            raise ControllerError(
                f"mode/world shard row binding order is not canonical: {key}/{family}"
            )
        if identities != expected_rows:
            raise ControllerError(f"mode/world shard row schedule disagrees: {key}/{family}")
        if expected_rows:
            if set(family_datasets) != {key}:
                raise ControllerError(f"mode/world shard dataset closure drifted: {key}/{family}")
            dataset = family_datasets.get(key)
            if not isinstance(dataset, Mapping):
                raise ControllerError(f"mode/world shard dataset metadata is malformed: {key}/{family}")
            expected_name = f"{family.lower()}-{mode}-world-{world}.json"
            if (
                dataset.get("path") != expected_name
                or dataset.get("rows") != len(expected_rows)
                or dataset.get("source_manifest_sha256") != source_manifest
                or not isinstance(dataset.get("dataset_sha256"), str)
                or len(dataset["dataset_sha256"]) != 64
            ):
                raise ControllerError(f"mode/world shard dataset metadata drifted: {key}/{family}")
            if family == "C2":
                _validate_ops3_dataset(
                    root,
                    dataset,
                    list(family_bindings),
                    mode=mode,
                    world=world,
                    source_manifest_sha256=source_manifest,
                )
        elif family_datasets:
            raise ControllerError(f"empty mode/world family unexpectedly has a dataset: {key}/{family}")


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ControllerError(f"refusing to overwrite: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _shard_status_path(staging: Path, key: str, event: str) -> Path:
    mode, world_text = key.split(":", 1)
    world = int(world_text)
    if event not in {"started", "terminal"}:
        raise ControllerError(f"invalid shard status event: {event}")
    return Path(staging) / "shard-status" / f"{mode}-world-{world}.{event}.json"


def _write_shard_status(
    staging: Path,
    key: str,
    *,
    event: str,
    state: str,
    **fields: object,
) -> Path:
    """Write one immutable lifecycle receipt for one mode/world shard."""

    mode, world_text = key.split(":", 1)
    world = int(world_text)
    payload: dict[str, object] = {
        "schema": SHARD_STATUS_SCHEMA,
        "event": event,
        "state": state,
        "mode": mode,
        "world": world,
        "recorded_unix_s": round(time.time(), 3),
        **fields,
    }
    path = _shard_status_path(staging, key, event)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_once(path, _canonical(payload))
    return path


def _failed(output: Path, status: int, message: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    marker = f"status=FAILED\nexit_status={int(status)}\nmessage={message}\n".encode("utf-8")
    if not (output / "FAILED").exists() and not (output / "FAILED").is_symlink():
        _write_once(output / "FAILED", marker)


def _merge(
    shards: Mapping[str, Path],
    output: Path,
    *,
    expected_schedule: Mapping[str, Mapping[str, object]],
) -> None:
    """Authenticate and deterministically merge every mode/world shard.

    The source-derived schedule and row bindings are the merge authority.  A
    filename collision or matching filename alone is never sufficient to
    admit a target file into the final output.
    """

    ordered_keys = sorted(expected_schedule, key=_shard_sort_key)
    if not ordered_keys or set(shards) != set(ordered_keys):
        raise ControllerError(
            "mode/world shard set disagrees with the authenticated schedule"
        )
    receipts = {key: _read_receipt(shards[key]) for key in ordered_keys}
    for key in ordered_keys:
        _validate_shard(key, shards[key], receipts[key], expected_schedule[key])
    first = receipts[ordered_keys[0]]
    for key in ordered_keys:
        receipt = receipts[key]
        for field in ("source", "formula_constants", "code_closure_sha256"):
            if receipt.get(field) != first.get(field):
                raise ControllerError(f"mode/world {field} differs: {key}")

    expected_schedule_sorted = {
        key: dict(expected_schedule[key]) for key in ordered_keys
    }
    schedule_payload = {
        "schema": SCHEDULE_SCHEMA,
        "shards": expected_schedule_sorted,
        "sha256": _schedule_sha256(expected_schedule_sorted),
    }
    datasets: dict[str, dict[str, Any]] = {family: {} for family in SHARD_FAMILIES}
    row_bindings: dict[str, list[Any]] = {family: [] for family in SHARD_FAMILIES}
    for key in ordered_keys:
        receipt = receipts[key]
        for family in SHARD_FAMILIES:
            expected_rows = expected_schedule[key][family]
            if expected_rows:
                datasets[family][key] = dict(receipt["datasets"][family][key])
                row_bindings[family].extend(receipt["row_bindings"][family])
    for family in SHARD_FAMILIES:
        row_bindings[family].sort(
            key=lambda binding: (
                _shard_sort_key(f"{binding['mode']}:{binding['world']}"),
                _binding_sort_key(family, binding),
            )
        )
        merged_identities = [
            _binding_identity(family, binding) for binding in row_bindings[family]
        ]
        expected_identities = [
            row
            for key in ordered_keys
            for row in expected_schedule[key][family]
        ]
        if merged_identities != expected_identities:
            raise ControllerError(f"merged {family} row schedule is incomplete")

    if output.exists() or output.is_symlink():
        raise ControllerError(f"refusing to overwrite final output: {output}")
    output.mkdir(parents=True)
    files: dict[str, str] = {}
    for key in ordered_keys:
        shard = shards[key]
        for family in SHARD_FAMILIES:
            expected_rows = expected_schedule[key][family]
            if not expected_rows:
                continue
            metadata = receipts[key]["datasets"][family][key]
            relative = Path(str(metadata["path"]))
            source = shard / relative
            destination = output / relative
            if relative.is_absolute() or ".." in relative.parts:
                raise ControllerError(f"unsafe dataset path in shard receipt: {key}/{family}")
            if source.is_symlink() or not source.is_file():
                raise ControllerError(f"authenticated dataset is missing: {key}/{family}")
            if destination.name in files:
                raise ControllerError(f"dataset destination collision: {destination.name}")
            _write_once(destination, source.read_bytes())
            files[destination.name] = _sha(destination)

    merged = dict(first)
    # Every child receipt is tagged as a one-shard output.  The merged root
    # represents the complete schedule, so retaining the first child's
    # ``shard`` claim would misstate provenance when more than one shard ran.
    merged.pop("shard", None)
    merged["parallel_modes"] = list(SHARD_MODES)
    merged["parallel_worlds"] = sorted(
        {int(expected_schedule[key]["world"]) for key in ordered_keys}
    )
    merged["parallel_shards"] = ordered_keys
    merged["schedule"] = schedule_payload
    merged["datasets"] = datasets
    merged["row_bindings"] = row_bindings
    merged["shards"] = {
        key: {
            "mode": expected_schedule[key]["mode"],
            "world": expected_schedule[key]["world"],
            # Keep the receipt independent of temporary staging locations.
            "path": f"{expected_schedule[key]['mode']}/world-{expected_schedule[key]['world']}",
            "receipt_sha256": _sha(shards[key] / "receipt.json"),
            "manifest_sha256": _sha(shards[key] / "MANIFEST.sha256"),
        }
        for key in ordered_keys
    }
    receipt_path = output / "receipt.json"
    _write_once(receipt_path, _canonical(merged))
    files["receipt.json"] = _sha(receipt_path)
    manifest_path = output / "MANIFEST.sha256"
    _write_once(
        manifest_path,
        "".join(
            f"{files[name]}  {name}\n" for name in sorted(files)
        ).encode("ascii"),
    )


def run(args: argparse.Namespace) -> int:
    if type(args.users) is not int or args.users != USERS:
        raise ControllerError(f"target-generation runtime is fixed at exactly {USERS} users")
    output = Path(args.output).resolve()
    if output.exists() or output.is_symlink():
        raise ControllerError(f"refusing to overwrite output root: {output}")
    staging = Path(args.staging).resolve() if args.staging else output.parent / (output.name + "-mode-shards")
    if staging.exists() or staging.is_symlink():
        raise ControllerError(f"refusing to overwrite staging root: {staging}")
    expected_schedule = _expected_schedule(args)
    ordered_keys = sorted(expected_schedule, key=_shard_sort_key)
    worker_limit = int(args.max_workers)
    if worker_limit <= 0:
        worker_limit = len(ordered_keys)
    if worker_limit <= 0:
        raise ControllerError("authenticated target schedule is empty")
    staging.mkdir(parents=True)
    common = [
        str(args.python), str(GENERATOR),
        "--capture", str(args.capture), "--materialization-dir", str(args.materialization_dir),
        "--tle-root", str(args.tle_root), "--prereg", str(args.prereg),
        "--manifest", str(args.manifest), "--manifest-digest", str(args.manifest_digest),
        "--execution-addendum", str(args.execution_addendum), "--users", str(args.users),
    ]
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
    # Lifecycle receipts live beside (not inside) each child output root, so
    # they cannot invalidate that child's authenticated MANIFEST.sha256.  The
    # start and terminal events are separate write-once files: a controller
    # crash cannot overwrite a prior state or make a partial shard look done.
    status_root = staging / "shard-status"
    status_root.mkdir()
    processes: dict[str, tuple[subprocess.Popen[bytes], Path]] = {}
    terminal_keys: set[str] = set()
    pending: list[str] = list(ordered_keys)
    try:
        while pending or processes:
            while pending and len(processes) < worker_limit:
                key = pending.pop(0)
                mode, world_text = key.split(":", 1)
                world = int(world_text)
                shard_root = staging / mode / f"world-{world}"
                shard_root.parent.mkdir(exist_ok=True)
                log_path = staging / f"{mode}-world-{world}.log"
                log = log_path.open("wb")
                command = common + [
                    "--mode",
                    mode,
                    "--world",
                    str(world),
                    "--output",
                    str(shard_root),
                ]
                start_path = _write_shard_status(
                    staging,
                    key,
                    event="started",
                    state="RUNNING",
                    output=str(shard_root),
                    log=str(log_path.name),
                    command_sha256=hashlib.sha256(_canonical(command)).hexdigest(),
                )
                try:
                    process = subprocess.Popen(
                        command,
                        cwd=HERE.parents[1],
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                except Exception as error:
                    log.close()
                    _write_shard_status(
                        staging,
                        key,
                        event="terminal",
                        state="FAILED",
                        returncode=None,
                        error=str(error).replace("\n", " "),
                        start_receipt=str(start_path.name),
                        log=str(log_path.name),
                    )
                    terminal_keys.add(key)
                    raise
                log.close()
                processes[key] = (process, log_path)
            while True:
                for key, (process, log_path) in processes.items():
                    if process.poll() is not None:
                        break
                else:
                    time.sleep(2.0)
                    continue
                break
            try:
                status = process.wait()
            except Exception as error:
                _write_shard_status(
                    staging,
                    key,
                    event="terminal",
                    state="FAILED",
                    returncode=None,
                    error=str(error).replace("\n", " "),
                    log=str(log_path.name),
                )
                terminal_keys.add(key)
                del processes[key]
                raise
            del processes[key]
            if status != 0:
                _write_shard_status(
                    staging,
                    key,
                    event="terminal",
                    state="FAILED",
                    returncode=status,
                    error=f"mode/world shard exited with status {status}",
                    log=str(log_path.name),
                )
                terminal_keys.add(key)
                raise ControllerError(f"mode/world shard failed: {key} status={status}")
            shard_root = staging / key.split(":", 1)[0] / f"world-{key.split(':', 1)[1]}"
            try:
                # Admit a child as shard-level PASS only after its own
                # receipt/manifest and authenticated row schedule have been
                # checked.  A successful process exit alone is not enough to
                # hide a malformed or substituted shard behind a later merge
                # failure.
                shard_receipt = _read_receipt(shard_root)
                _validate_shard(
                    key,
                    shard_root,
                    shard_receipt,
                    expected_schedule[key],
                )
                receipt_sha256 = _sha(shard_root / "receipt.json")
                manifest_sha256 = _sha(shard_root / "MANIFEST.sha256")
            except Exception as error:
                _write_shard_status(
                    staging,
                    key,
                    event="terminal",
                    state="FAILED",
                    returncode=status,
                    error=str(error).replace("\n", " "),
                    log=str(log_path.name),
                )
                terminal_keys.add(key)
                raise
            _write_shard_status(
                staging,
                key,
                event="terminal",
                state="PASS",
                returncode=status,
                receipt_sha256=receipt_sha256,
                manifest_sha256=manifest_sha256,
                log=str(log_path.name),
            )
            terminal_keys.add(key)
        _merge(
            {
                key: staging / key.split(":", 1)[0] / f"world-{key.split(':', 1)[1]}"
                for key in ordered_keys
            },
            output,
            expected_schedule=expected_schedule,
        )
        subprocess.run([str(args.python), str(SEALER), str(output)], check=True)
        return 0
    except Exception as error:
        # Preserve a terminal event for every child that was started, and a
        # BLOCKED event for queued shards that were never allowed to run.
        for process, _log in processes.values():
            if process.poll() is None:
                process.terminate()
        for key, (process, log_path) in list(processes.items()):
            status = process.wait()
            if key not in terminal_keys:
                _write_shard_status(
                    staging,
                    key,
                    event="terminal",
                    state="FAILED",
                    returncode=status,
                    error="controller aborted this shard after another failure",
                    log=str(log_path.name),
                )
                terminal_keys.add(key)
        for key in pending:
            if key not in terminal_keys:
                _write_shard_status(
                    staging,
                    key,
                    event="terminal",
                    state="BLOCKED",
                    returncode=None,
                    error="controller stopped before this shard was started",
                )
                terminal_keys.add(key)
        _failed(output, 1, str(error).replace("\n", " "))
        print(f"V023_C1C2_TARGET_CONTROLLER_FAILED: {error}", file=sys.stderr)
        return 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture", type=Path, required=True)
    p.add_argument("--materialization-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--staging", type=Path)
    p.add_argument("--tle-root", type=Path, required=True)
    p.add_argument("--prereg", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--manifest-digest", type=Path, required=True)
    p.add_argument("--execution-addendum", type=Path, required=True)
    p.add_argument("--python", type=Path, default=Path(sys.executable))
    p.add_argument("--users", type=int, default=100)
    p.add_argument(
        "--max-workers",
        type=int,
        default=0,
        help="maximum concurrent mode/world shards; zero means all authenticated shards",
    )
    return p


if __name__ == "__main__":
    try:
        raise SystemExit(run(parser().parse_args()))
    except Exception as error:
        print(f"V023_C1C2_TARGET_CONTROLLER_BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
