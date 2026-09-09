"""Fail-closed adapter for the V0.23 heterogeneous learner inputs.

This directory is intentionally an integration seam, not another target
producer.  It authenticates the completed output of the V0.23 C1/C2 target
generation controller, delegates JSON decoding to the current typed dataset
classes, and projects the resulting rows onto the existing
``EEAxisPairBatch`` surface.  LC-SRS C3 inputs are accepted only as the
current typed anchor/sampled-batch classes.

No target formula, simulator call, learner update, or episode execution lives
here.  In particular, ``build_route_schedule`` returns dispatch metadata only;
it never calls the training schedule's update function.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, TypeAlias

import numpy as np

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v014_head import (
    EEAxisV014HeadConfig,
    EEAxisV014NormalizedPairBatch,
)
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_c1_selector import (
    C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    C1_INFORMED_SOURCE_RULE,
)
from mcrl.runtime.ee_axis_lcsrs_c3_dataset import (
    LCSRS_ROW_SUPPORTED,
    LCSRSAnchorRecord,
    LCSRSAnchorSurface,
)
from mcrl.runtime.ee_axis_lcsrs_c3_learner import LCSRSC3SampledBatch
from mcrl.runtime.ee_axis_opening_dataset import (
    EEAxisOpeningDataset,
    EEAxisOpeningDatasetRow,
    read_opening_dataset,
)
from mcrl.runtime.ee_axis_opening_pairs import EEAxisOpeningRouteBatch
from mcrl.runtime.ee_axis_opening_runner import C3_NEUTRAL_SOURCE_RULE
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM
from mcrl.runtime.ee_axis_v014_q2_state import V014_Q2_STATE_DIM


TARGET_GENERATION_SCHEMA = "multi-catfish-mcrl-v023-c1c2-target-generation-v1"
TARGET_CLAIM_CEILING = (
    "TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_NO_EPISODE_TRAINING_"
    "NO_EFFICACY_NO_TEST"
)
TARGET_STATUS = "TARGETS_MATERIALIZED_TRAIN"
TARGET_MODES = ("informed", "neutral")
TARGET_ROUTES = ("C1", "C2", "C3")
OPS3_SELECTED_PAIR_SCHEMA = "multi-catfish-mcrl-v023-repriced-ops3-selected-pair-dataset-v1"
OPS3_TARGET_UNIT = "normalized-repriced-ops3-delta-over-kappa"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_WORLD_KEY_RE = re.compile(r"^(informed|neutral):([0-9]+)$")
_TARGET_DATASET_META = {
    "C1": frozenset(
        {
            "path",
            "rows",
            "source_manifest_sha256",
            "common_random_field_sha256",
            "dataset_sha256",
        }
    ),
    "C2": frozenset(
        {"path", "schema", "rows", "source_manifest_sha256", "dataset_sha256"}
    ),
}
_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "status",
        "claim_ceiling",
        "training_or_replay_write",
        "learner_update",
        "test_split_opened",
        "source",
        "formula_constants",
        "datasets",
        "row_bindings",
        "code_closure",
        "code_closure_sha256",
        "schedule",
    }
)
_SHARD_RECEIPT_FIELDS = frozenset({"shard"})
_MERGED_RECEIPT_FIELDS = frozenset(
    {"parallel_modes", "parallel_worlds", "parallel_shards", "shards"}
)
_SOURCE_FIELDS = frozenset(
    {
        "capture_path",
        "capture_sha256",
        "materialization_dir",
        "materialization_manifest_sha256",
        "pool_sha256",
        "source_family",
        "source_manifest_sha256",
        "checkpoint_sha256",
    }
)
_FORMULA_FIELDS = frozenset(
    {
        "lambda_bits_per_j",
        "kappa_bits",
        "interval_s",
        "c2_schema",
        "c2_target_unit",
        "c2_horizon_steps",
        "c2_terminal_rule",
    }
)
_C1_BINDING_FIELDS = frozenset(
    {
        "mode",
        "source_anchor_sha256",
        "source_record_sha256",
        "world",
        "step_index",
        "focal_user",
        "reference_action",
        "candidate_action",
        "candidate_physical_key",
        "source_rule",
        "source_seed",
        "common_random_field_sha256",
        "comparison_sha256",
    }
)
_C2_BINDING_FIELDS = frozenset(
    {
        "mode",
        "source_anchor_sha256",
        "world",
        "step_index",
        "focal_user",
        "reference_action",
        "candidate_action",
        "candidate_physical_key",
        "source_rule",
        "schedule_sha256",
        "ops3_anchor_sha256",
        "ops3_projection_sha256",
        "target_delta",
        "target_unit",
    }
)
_SHARD_FIELDS = frozenset(
    {"mode", "world", "path", "receipt_sha256", "manifest_sha256"}
)


class V023TargetBatchAdapterError(MCRLContractError):
    """A completed target root or heterogeneous input is not admissible."""


def _error(message: str, *, cause: BaseException | None = None) -> None:
    if cause is None:
        raise V023TargetBatchAdapterError(message)
    raise V023TargetBatchAdapterError(message) from cause


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        _error(f"{field} must be a lowercase SHA-256 digest")
    return value


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        _error(f"{field} must be a nonempty trimmed string")
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _error(f"{field} must be an exact integer >= {minimum}")
    return value


def _hex_float(value: object, *, field: str, positive: bool = False) -> float:
    if not isinstance(value, str):
        _error(f"{field} must be a hexadecimal float")
    try:
        decoded = float.fromhex(value)
    except ValueError as cause:
        _error(f"{field} must be a hexadecimal float", cause=cause)
    if not np.isfinite(decoded) or (positive and decoded <= 0.0):
        qualifier = "positive finite" if positive else "finite"
        _error(f"{field} must be a {qualifier} hexadecimal float")
    return decoded


def _canonical_bytes(payload: object) -> bytes:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as cause:
        _error("payload cannot be canonically encoded", cause=cause)
    return encoded + b"\n"


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)[:-1]).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as cause:
        _error(f"cannot hash authenticated file: {path.name}", cause=cause)
    return digest.hexdigest()


def _regular_file(path: Path, *, field: str) -> None:
    if path.is_symlink() or not path.is_file():
        _error(f"{field} must be a regular non-symlink file")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _error(f"canonical JSON contains duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    _error(f"canonical JSON contains non-standard constant: {value}")


def _read_canonical_json(path: Path, *, field: str) -> dict[str, object]:
    _regular_file(path, field=field)
    raw = path.read_bytes()
    try:
        payload = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except V023TargetBatchAdapterError:
        raise
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as cause:
        _error(f"{field} is not canonical ASCII JSON", cause=cause)
    if not isinstance(payload, dict):
        _error(f"{field} JSON root must be an object")
    if raw != _canonical_bytes(payload):
        _error(f"{field} is not canonical JSON")
    return payload


def _safe_basename(value: object, *, field: str) -> str:
    name = _text(value, field=field)
    path = Path(name)
    if (
        path.name != name
        or name in {".", ".."}
        or "\x00" in name
        or "/" in name
        or "\\" in name
    ):
        _error(f"{field} must be a safe flat filename")
    return name


def _authenticate_root(root: str | Path) -> tuple[Path, dict[str, object], dict[str, str]]:
    destination = Path(root)
    if destination.is_symlink() or not destination.is_dir():
        _error("target output root is missing or is a symlink")
    failed = destination / "FAILED"
    if failed.exists() or failed.is_symlink():
        _error("target output root carries a FAILED marker")
    complete = destination / "COMPLETE"
    manifest = destination / "MANIFEST.sha256"
    receipt_path = destination / "receipt.json"
    _regular_file(complete, field="COMPLETE")
    _regular_file(manifest, field="MANIFEST.sha256")
    _regular_file(receipt_path, field="receipt.json")

    manifest_raw = manifest.read_bytes()
    try:
        manifest_text = manifest_raw.decode("ascii")
    except UnicodeDecodeError as cause:
        _error("MANIFEST.sha256 is not ASCII", cause=cause)
    if not manifest_raw or not manifest_raw.endswith(b"\n"):
        _error("MANIFEST.sha256 must end with one newline")
    if b"\r" in manifest_raw:
        _error("MANIFEST.sha256 must use LF line endings")
    listed: dict[str, str] = {}
    names: list[str] = []
    for line_number, line in enumerate(manifest_text.splitlines(), start=1):
        if line.count("  ") != 1:
            _error(f"MANIFEST.sha256 line {line_number} is malformed")
        digest_raw, name_raw = line.split("  ", 1)
        digest = _digest(digest_raw, field=f"manifest line {line_number} digest")
        name = _safe_basename(name_raw, field=f"manifest line {line_number} name")
        if name in listed:
            _error(f"MANIFEST.sha256 repeats {name}")
        listed[name] = digest
        names.append(name)
    if tuple(names) != tuple(sorted(names)):
        _error("MANIFEST.sha256 entries must be filename sorted")
    if "receipt.json" not in listed or listed["receipt.json"] != _file_sha256(receipt_path):
        _error("MANIFEST.sha256 does not authenticate receipt.json")

    for path in destination.rglob("*"):
        if path.is_symlink():
            _error(f"target output contains a symlink: {path.name}")
    actual = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    actual -= {"MANIFEST.sha256", "COMPLETE"}
    if actual != set(listed):
        _error("MANIFEST.sha256 file closure disagrees with target output")
    for name, expected in listed.items():
        path = destination / name
        _regular_file(path, field=f"manifest file {name}")
        if _file_sha256(path) != expected:
            _error(f"MANIFEST.sha256 hash drifted for {name}")
    manifest_sha256 = _file_sha256(manifest)
    if complete.read_bytes() != f"{manifest_sha256}  MANIFEST.sha256\n".encode("ascii"):
        _error("COMPLETE does not authenticate MANIFEST.sha256")

    receipt = _read_canonical_json(receipt_path, field="receipt.json")
    return destination, receipt, listed


def _validate_receipt_header(receipt: Mapping[str, object]) -> tuple[dict[str, object], dict[str, object], float, float]:
    receipt_fields = set(receipt)
    receipt_variant = frozenset(receipt_fields - _RECEIPT_FIELDS)
    if not _RECEIPT_FIELDS.issubset(receipt_fields) or receipt_variant not in {
        frozenset(),
        _SHARD_RECEIPT_FIELDS,
        _MERGED_RECEIPT_FIELDS,
    }:
        _error("receipt.json schema is missing or has unexpected fields")
    if receipt["schema"] != TARGET_GENERATION_SCHEMA:
        _error("receipt.json schema is stale")
    if receipt["status"] != TARGET_STATUS:
        _error("receipt.json status is not completed target materialization")
    if receipt["claim_ceiling"] != TARGET_CLAIM_CEILING:
        _error("receipt.json claim ceiling drifted")
    for field in ("training_or_replay_write", "learner_update", "test_split_opened"):
        if receipt[field] is not False:
            _error(f"receipt.json crosses closed boundary: {field}")
    source = receipt["source"]
    if not isinstance(source, dict) or set(source) != _SOURCE_FIELDS:
        _error("receipt source provenance is malformed")
    for field in ("capture_path", "materialization_dir", "source_family"):
        _text(source[field], field=f"source.{field}")
    source_manifest = _digest(
        source["source_manifest_sha256"], field="source.source_manifest_sha256"
    )
    checkpoint = _digest(source["checkpoint_sha256"], field="source.checkpoint_sha256")
    for field in (
        "capture_sha256",
        "materialization_manifest_sha256",
        "pool_sha256",
    ):
        _digest(source[field], field=f"source.{field}")
    formula = receipt["formula_constants"]
    if not isinstance(formula, dict) or set(formula) != _FORMULA_FIELDS:
        _error("receipt formula constants are malformed")
    lambda_bits = _hex_float(
        formula["lambda_bits_per_j"], field="formula_constants.lambda_bits_per_j", positive=True
    )
    _hex_float(formula["kappa_bits"], field="formula_constants.kappa_bits", positive=True)
    interval = _hex_float(
        formula["interval_s"], field="formula_constants.interval_s", positive=True
    )
    if formula["c2_schema"] != OPS3_SELECTED_PAIR_SCHEMA:
        _error("receipt C2 schema is not the selected-pair OPS-3 schema")
    if formula["c2_target_unit"] != OPS3_TARGET_UNIT:
        _error("receipt C2 target unit is not already-normalized OPS-3")
    if formula["c2_horizon_steps"] != 3:
        _error("receipt C2 horizon drifted")
    if formula["c2_terminal_rule"] != "PREDECLARED_H_T_TRUNCATION_TERMINAL_ZERO":
        _error("receipt C2 terminal rule drifted")
    schedule = receipt["schedule"]
    if not isinstance(schedule, dict) or set(schedule) != {"schema", "shards", "sha256"}:
        _error("receipt selected-pair schedule is malformed")
    _text(schedule["schema"], field="schedule.schema")
    _digest(schedule["sha256"], field="schedule.sha256")
    if not isinstance(schedule["shards"], dict) or not schedule["shards"]:
        _error("receipt selected-pair schedule shards are malformed")
    schedule_shards = schedule["shards"]
    if receipt_variant == _MERGED_RECEIPT_FIELDS:
        ordered_shards: list[str] = []
        ordered_worlds: set[int] = set()
        for key, value in schedule_shards.items():
            mode, world = _parse_dataset_key(key, route="schedule")
            if (
                not isinstance(value, dict)
                or value.get("mode") != mode
                or value.get("world") != world
            ):
                _error("receipt selected-pair schedule shard identity drifted")
            ordered_shards.append(key)
            ordered_worlds.add(world)
        ordered_shards.sort(
            key=lambda key: (
                TARGET_MODES.index(key.split(":", 1)[0]),
                int(key.split(":", 1)[1]),
            )
        )
        if receipt["parallel_modes"] != list(TARGET_MODES):
            _error("receipt parallel mode identity drifted")
        if receipt["parallel_worlds"] != sorted(ordered_worlds):
            _error("receipt parallel world identity drifted")
        if receipt["parallel_shards"] != ordered_shards:
            _error("receipt parallel shard order drifted")
        shards = receipt["shards"]
        if not isinstance(shards, dict) or set(shards) != set(ordered_shards):
            _error("receipt merged shard closure drifted")
        for key in ordered_shards:
            mode, world = _parse_dataset_key(key, route="shards")
            metadata = shards[key]
            if not isinstance(metadata, dict) or set(metadata) != _SHARD_FIELDS:
                _error("receipt merged shard metadata is malformed")
            if (
                metadata["mode"] != mode
                or metadata["world"] != world
                or metadata["path"] != f"{mode}/world-{world}"
            ):
                _error("receipt merged shard metadata identity drifted")
            for field in ("receipt_sha256", "manifest_sha256"):
                _digest(metadata[field], field=f"shards[{key}].{field}")
    code_closure = receipt["code_closure"]
    if not isinstance(code_closure, dict) or not code_closure:
        _error("receipt code_closure must be nonempty")
    for name, digest in code_closure.items():
        if (
            not isinstance(name, str)
            or not name
            or name.startswith("/")
            or "\\" in name
            or any(part in {"", ".", ".."} for part in name.split("/"))
        ):
            _error("code_closure paths must be safe relative paths")
        _digest(digest, field=f"code_closure[{name}]")
    if receipt["code_closure_sha256"] != _canonical_sha256(code_closure):
        _error("receipt code_closure_sha256 disagrees")
    return source, formula, lambda_bits, interval


@dataclass(frozen=True, slots=True)
class V023DatasetEntry:
    """One authenticated per-mode/per-world typed target dataset."""

    route: str
    mode: str
    world: int
    path: Path
    dataset: EEAxisOpeningDataset | "V023OPS3SelectedPairDataset"
    route_batch: "RouteBatch"


@dataclass(frozen=True, slots=True)
class V023OPS3SelectedPairDataset:
    """Authenticated selected-pair rows emitted by the repriced OPS-3 producer."""

    rows: tuple[Mapping[str, object], ...]
    source_manifest_sha256: str
    checkpoint_sha256: str
    kappa_bits: float
    content_sha256: str


@dataclass(frozen=True, slots=True)
class V023OPS3RouteBatch:
    """The typed, already-normalized Q2 batch for one source file."""

    route: str
    pair_batch: EEAxisV014NormalizedPairBatch

    def verify(self) -> None:
        if self.route != "C2":
            _error("OPS-3 route batch must retain C2 identity")
        self.pair_batch.validate(config=_ops3_head_config(self.pair_batch))


RouteBatch: TypeAlias = EEAxisOpeningRouteBatch | V023OPS3RouteBatch


def _ops3_head_config(batch: EEAxisV014NormalizedPairBatch) -> EEAxisV014HeadConfig:
    return EEAxisV014HeadConfig(
        action_dim=NUM_ACTIONS,
        local_feature_dim=16,
        global_feature_dim=0,
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=1.0e-3,
        # Batch validation needs only its state/action dimensions.  The actual
        # kappa is authenticated from the receipt and used by no C2 update.
        kappa_bits=1.0,
        beta=0.1,
    )


def _parse_dataset_key(key: object, *, route: str) -> tuple[str, int]:
    if not isinstance(key, str):
        _error(f"datasets.{route} key must be mode:world")
    match = _WORLD_KEY_RE.fullmatch(key)
    if match is None:
        _error(f"datasets.{route} key is not mode:world")
    mode, world_text = match.groups()
    world = int(world_text)
    if str(world) != world_text:
        _error(f"datasets.{route} key has a noncanonical world")
    return mode, world


def _candidate_key(value: object, *, field: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(component) is not int or component < 0 for component in value)
    ):
        _error(f"{field} must be [nonnegative_norad, nonnegative_cell]")
    return int(value[0]), int(value[1])


def _finite_float(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        _error(f"{field} must be finite numeric")
    try:
        decoded = float(value)
    except (TypeError, ValueError, OverflowError) as cause:
        _error(f"{field} must be finite numeric", cause=cause)
    if not np.isfinite(decoded):
        _error(f"{field} must be finite numeric")
    return decoded


def _ops3_route_batch(rows: Sequence[Mapping[str, object]]) -> V023OPS3RouteBatch:
    states: list[np.ndarray] = []
    reference: list[int] = []
    candidate: list[int] = []
    targets: list[float] = []
    masks: list[np.ndarray] = []
    required = {
        "schema", "world", "mode", "source_anchor_sha256", "step_index",
        "focal_user", "reference_action", "candidate_action",
        "candidate_physical_key", "source_rule", "schedule_sha256",
        "target_unit", "target_reference_value", "target_candidate_value",
        "target_delta", "q1_reference_action", "action_mask", "q2_state",
        "q2_features", "persistence", "rate_bps", "marginal_power_w",
        "required_power_w", "horizon", "provenance",
    }
    if not rows:
        _error("OPS-3 selected-pair dataset has no rows")
    for index, row in enumerate(rows):
        if set(row) != required:
            _error(f"OPS-3 selected-pair row {index} schema drifted")
        if row["schema"] != OPS3_SELECTED_PAIR_SCHEMA:
            _error("OPS-3 selected-pair row schema is stale")
        if row["target_unit"] != OPS3_TARGET_UNIT:
            _error("OPS-3 selected-pair row target is not already normalized")
        if row["mode"] not in TARGET_MODES:
            _error("OPS-3 selected-pair row mode is malformed")
        for field in ("source_anchor_sha256", "schedule_sha256"):
            _digest(row[field], field=f"OPS-3 row {field}")
        _exact_int(row["world"], field="OPS-3 row world", minimum=1)
        _exact_int(row["step_index"], field="OPS-3 row step_index")
        _exact_int(row["focal_user"], field="OPS-3 row focal_user")
        _candidate_key(row["candidate_physical_key"], field="OPS-3 row candidate_physical_key")
        _text(row["source_rule"], field="OPS-3 row source_rule")
        mask = np.asarray(row["action_mask"])
        state = np.asarray(row["q2_state"], dtype=np.float32)
        features = np.asarray(row["q2_features"], dtype=np.float64)
        if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,) or not np.any(mask):
            _error("OPS-3 selected-pair action mask is malformed")
        if state.shape != (V014_Q2_STATE_DIM,) or not np.all(np.isfinite(state)):
            _error("OPS-3 selected-pair Q2 state must be finite feature-major 448-D")
        if features.shape != (NUM_ACTIONS, 16) or not np.all(np.isfinite(features)):
            _error("OPS-3 selected-pair Q2 features must be finite 28x16")
        if not np.array_equal(state, features.astype(np.float32).T.reshape(-1)):
            _error("OPS-3 selected-pair Q2 state is not feature-major 16x28")
        ref = _exact_int(row["reference_action"], field="OPS-3 reference action")
        cand = _exact_int(row["candidate_action"], field="OPS-3 candidate action")
        if ref >= NUM_ACTIONS or cand >= NUM_ACTIONS or not mask[ref] or not mask[cand]:
            _error("OPS-3 selected-pair actions must be legal")
        reference_value = _finite_float(row["target_reference_value"], field="OPS-3 target reference")
        candidate_value = _finite_float(row["target_candidate_value"], field="OPS-3 target candidate")
        delta = _finite_float(row["target_delta"], field="OPS-3 target delta")
        if delta != candidate_value - reference_value:
            _error("OPS-3 selected-pair target delta disagrees with normalized endpoints")
        if _exact_int(row["horizon"], field="OPS-3 horizon") > 3:
            _error("OPS-3 selected-pair horizon drifted")
        for field in ("persistence", "rate_bps", "marginal_power_w", "required_power_w"):
            values = np.asarray(row[field], dtype=np.float64)
            if values.shape != (3, NUM_ACTIONS) or not np.all(np.isfinite(values)):
                _error(f"OPS-3 selected-pair {field} is malformed")
        provenance = row["provenance"]
        required_provenance = {
            "ops3_anchor_sha256", "ops3_tracker_seed_sha256", "ops3_projection_sha256",
            "ops3_future_d2_indices", "ops3_sample_times_utc", "ops3_offset_times_utc",
        }
        if not isinstance(provenance, dict) or set(provenance) != required_provenance:
            _error("OPS-3 selected-pair provenance is malformed")
        for field in ("ops3_anchor_sha256", "ops3_tracker_seed_sha256", "ops3_projection_sha256"):
            _digest(provenance[field], field=f"OPS-3 provenance {field}")
        if any(not isinstance(provenance[field], list) for field in required_provenance - {
            "ops3_anchor_sha256", "ops3_tracker_seed_sha256", "ops3_projection_sha256"
        }):
            _error("OPS-3 selected-pair provenance arrays are malformed")
        states.append(state)
        reference.append(ref)
        candidate.append(cand)
        targets.append(delta)
        masks.append(mask)
    # Each row contributes one 1-D state (448,) and one 1-D mask (28,); they must be
    # stacked into (rows, 448) / (rows, 28).  Concatenating 1-D rows would silently
    # flatten the panel and fail the head validation on the first real shard.
    batch = EEAxisV014NormalizedPairBatch(
        states=_readonly_concat([np.stack(states, axis=0)], dtype=np.dtype(np.float32)),
        reference_actions=_readonly_concat([np.asarray(reference)], dtype=np.dtype(np.int64)),
        candidate_actions=_readonly_concat([np.asarray(candidate)], dtype=np.dtype(np.int64)),
        normalized_target_deltas=_readonly_concat([np.asarray(targets)], dtype=np.dtype(np.float64)),
        action_masks=_readonly_concat([np.stack(masks, axis=0)], dtype=np.dtype(np.bool_)),
    )
    batch.validate(config=_ops3_head_config(batch))
    return V023OPS3RouteBatch(route="C2", pair_batch=batch)


def _validate_common_binding(binding: object, *, fields: frozenset[str], mode: str, route: str) -> dict[str, object]:
    if not isinstance(binding, dict) or set(binding) != fields:
        _error(f"{route} row binding has an unexpected schema")
    if binding["mode"] != mode:
        _error(f"{route} row binding mode disagrees with its list")
    for field in (
        "source_anchor_sha256",
        "common_random_field_sha256",
        "comparison_sha256",
    ):
        _digest(binding[field], field=f"{route} binding {field}")
    _exact_int(binding["world"], field=f"{route} binding world")
    _exact_int(binding["step_index"], field=f"{route} binding step_index")
    _exact_int(binding["focal_user"], field=f"{route} binding focal_user")
    _candidate_key(binding["candidate_physical_key"], field=f"{route} binding candidate_physical_key")
    return binding


def _typed_dataset(
    *,
    destination: Path,
    listed: Mapping[str, str],
    route: str,
    mode: str,
    world: int,
    metadata: object,
    source_manifest: str,
    checkpoint: str,
    lambda_bits: float,
    interval: float,
) -> V023DatasetEntry:
    if not isinstance(metadata, dict) or set(metadata) != _TARGET_DATASET_META[route]:
        _error(f"datasets.{route}[{mode}:{world}] metadata is malformed")
    expected_name = f"{route.lower()}-{mode}-world-{world}.json"
    name = _safe_basename(metadata["path"], field=f"datasets.{route}.path")
    if name != expected_name:
        _error(f"datasets.{route}[{mode}:{world}] path is not canonical")
    if name not in listed:
        _error(f"datasets.{route}[{mode}:{world}] is not manifest-listed")
    rows = _exact_int(metadata["rows"], field=f"datasets.{route}[{mode}:{world}].rows", minimum=1)
    _digest(metadata["source_manifest_sha256"], field=f"datasets.{route}[{mode}:{world}].source_manifest_sha256")
    if metadata["source_manifest_sha256"] != source_manifest:
        _error(f"datasets.{route}[{mode}:{world}] source manifest differs")
    expected_digest = _digest(metadata["dataset_sha256"], field=f"datasets.{route}[{mode}:{world}].dataset_sha256")
    path = destination / name
    try:
        if route == "C1":
            if metadata["common_random_field_sha256"] is None:
                _error("C1 dataset common random field is missing")
            common_field = _digest(
                metadata["common_random_field_sha256"],
                field=f"datasets.C1[{mode}:{world}].common_random_field_sha256",
            )
            dataset = read_opening_dataset(path)
            if dataset.common_random_field_sha256 != common_field:
                _error(f"C1 dataset {name} common random field disagrees")
            if any(row.admitted_route != "C1" for row in dataset.rows):
                _error(f"C1 dataset {name} contains a non-C1 row")
            route_batch = dataset.c1_batch()
        else:
            raw_document = _read_canonical_json(path, field=f"C2 dataset {name}")
            if set(raw_document) != {
                "schema", "source_manifest_sha256", "checkpoint_sha256",
                "lambda_bits_per_j", "kappa_bits", "target_unit", "rows",
            }:
                _error(f"C2 dataset {name} is not the selected-pair schema")
            if raw_document["schema"] != OPS3_SELECTED_PAIR_SCHEMA or metadata["schema"] != OPS3_SELECTED_PAIR_SCHEMA:
                _error(f"C2 dataset {name} has a stale or legacy schema")
            if raw_document["target_unit"] != OPS3_TARGET_UNIT:
                _error(f"C2 dataset {name} target unit is not already normalized")
            if raw_document["source_manifest_sha256"] != source_manifest or raw_document["checkpoint_sha256"] != checkpoint:
                _error(f"C2 dataset {name} provenance disagrees with receipt")
            kappa = _hex_float(raw_document["kappa_bits"], field=f"C2 dataset {name}.kappa_bits", positive=True)
            if _hex_float(raw_document["lambda_bits_per_j"], field=f"C2 dataset {name}.lambda_bits_per_j", positive=True) != lambda_bits:
                _error(f"C2 dataset {name} lambda drifted")
            raw_rows = raw_document["rows"]
            if not isinstance(raw_rows, list) or not raw_rows or any(not isinstance(row, dict) for row in raw_rows):
                _error(f"C2 dataset {name} selected-pair rows are malformed")
            rows_typed = tuple(raw_rows)
            route_batch = _ops3_route_batch(rows_typed)
            dataset = V023OPS3SelectedPairDataset(
                rows=rows_typed,
                source_manifest_sha256=source_manifest,
                checkpoint_sha256=checkpoint,
                kappa_bits=kappa,
                content_sha256=_canonical_sha256(raw_document),
            )
    except V023TargetBatchAdapterError:
        raise
    except Exception as cause:
        _error(f"typed {route} dataset {name} failed verification", cause=cause)
    if len(dataset.rows) != rows:
        _error(f"dataset {name} row count disagrees with receipt")
    actual_digest = dataset.verify() if route == "C1" else dataset.content_sha256
    if actual_digest != expected_digest:
        _error(f"dataset {name} body digest disagrees with receipt")
    if dataset.source_manifest_sha256 != source_manifest:
        _error(f"dataset {name} source manifest disagrees with receipt")
    if dataset.checkpoint_sha256 != checkpoint:
        _error(f"dataset {name} checkpoint disagrees with receipt")
    if route == "C1":
        assert isinstance(dataset, EEAxisOpeningDataset)
        for row in dataset.rows:
            if row.raw_pair.lambda_bits_per_j != lambda_bits or row.raw_pair.interval_s != interval:
                _error(f"C1 dataset {name} formula constants drifted")
    else:
        assert isinstance(dataset, V023OPS3SelectedPairDataset)
        if dataset.kappa_bits <= 0.0:
            _error(f"C2 dataset {name} kappa is malformed")
    return V023DatasetEntry(
        route=route,
        mode=mode,
        world=world,
        path=path,
        dataset=dataset,
        route_batch=route_batch,
    )


def _validate_mode_route_identity(entry: V023DatasetEntry) -> None:
    if entry.route == "C1":
        assert isinstance(entry.dataset, EEAxisOpeningDataset)
        expected = C1_INFORMED_SOURCE_RULE if entry.mode == "informed" else C1_CLUSTER_NEUTRAL_SOURCE_RULE
        for row in entry.dataset.rows:
            if row.c1_source_rule != expected:
                _error(
                    f"C1 {entry.mode} dataset {entry.path.name} has mixed source identity"
                )
            if row.c3_source_rule != C3_NEUTRAL_SOURCE_RULE:
                _error(f"C1 dataset {entry.path.name} has stale C3 projection identity")
    else:
        assert isinstance(entry.dataset, V023OPS3SelectedPairDataset)
        for row in entry.dataset.rows:
            if row["mode"] != entry.mode:
                _error(f"C2 dataset {entry.path.name} row mode disagrees with filename")


def _validate_bindings(
    *,
    receipt: Mapping[str, object],
    entries: Sequence[V023DatasetEntry],
    mode: str,
    route: str,
) -> None:
    grouped = [entry for entry in entries if entry.mode == mode and entry.route == route]
    by_world = {entry.world: entry for entry in grouped}
    if len(by_world) != len(grouped):
        _error(f"{route} {mode} datasets repeat a world")
    bindings_payload = receipt["row_bindings"]
    if not isinstance(bindings_payload, dict) or set(bindings_payload) != {"C1", "C2"}:
        _error("receipt row_bindings must contain C1 and C2")
    raw_bindings = bindings_payload[route]
    if not isinstance(raw_bindings, list) or not raw_bindings:
        _error(f"receipt row_bindings.{route} must be nonempty")
    fields = _C1_BINDING_FIELDS if route == "C1" else _C2_BINDING_FIELDS
    bindings: dict[tuple[int, str], dict[str, object]] = {}
    for raw in raw_bindings:
        if not isinstance(raw, dict) or set(raw) != fields:
            _error(f"{route} row binding has an unexpected schema")
        if route == "C1":
            raw_mode = raw.get("mode")
            if raw_mode not in TARGET_MODES:
                _error("C1 row binding mode is malformed")
            binding = _validate_common_binding(raw, fields=fields, mode=str(raw_mode), route=route)
            if raw_mode != mode:
                continue
            _digest(binding["source_record_sha256"], field="C1 binding source_record_sha256")
            for field in ("reference_action", "candidate_action", "source_seed"):
                _exact_int(binding[field], field=f"C1 binding {field}")
            _text(binding["source_rule"], field="C1 binding source_rule")
        else:
            binding = dict(raw)
            raw_mode = binding.get("mode")
            if raw_mode not in TARGET_MODES:
                _error("C2 row binding mode is malformed")
            if raw_mode != mode:
                continue
            for field in ("source_anchor_sha256", "schedule_sha256", "ops3_anchor_sha256", "ops3_projection_sha256"):
                _digest(binding[field], field=f"C2 binding {field}")
            for field in ("world", "step_index", "focal_user", "reference_action", "candidate_action"):
                _exact_int(binding[field], field=f"C2 binding {field}")
            _candidate_key(binding["candidate_physical_key"], field="C2 binding candidate_physical_key")
            _text(binding["source_rule"], field="C2 binding source_rule")
            if binding["target_unit"] != OPS3_TARGET_UNIT:
                _error("C2 binding target unit is not already normalized")
            _finite_float(binding["target_delta"], field="C2 binding target_delta")
            _digest(binding["schedule_sha256"], field="C2 binding schedule_sha256")
        comparison = (
            str(binding["comparison_sha256"])
            if route == "C1"
            else _canonical_sha256(
                {key: binding[key] for key in sorted(binding) if key != "mode"}
            )
        )
        key = (int(binding["world"]), comparison)
        if key in bindings:
            _error(f"{route} row bindings repeat world/comparison identity")
        bindings[key] = binding
    expected_rows = sum(len(entry.dataset.rows) for entry in grouped)
    if route == "C1" and len(bindings) != expected_rows:
        _error(f"{route} {mode} row-binding count disagrees with datasets")
    expected_keys: set[tuple[int, str]] = set()
    for entry in grouped:
        if route == "C1":
            assert isinstance(entry.dataset, EEAxisOpeningDataset)
            rows: Iterable[EEAxisOpeningDatasetRow] = entry.dataset.rows
        else:
            assert isinstance(entry.dataset, V023OPS3SelectedPairDataset)
            rows = entry.dataset.rows
        for row in rows:
            if route == "C1":
                assert isinstance(row, EEAxisOpeningDatasetRow)
                comparison = row.raw_pair.comparison_sha256
                anchor = row.raw_pair.anchor_sha256
                common = row.raw_pair.common_random_field_sha256
                focal = row.raw_pair.focal_user
                candidate = row.raw_pair.candidate_physical_keys[focal]
                if candidate is None:
                    _error("C1 row binding candidate key is missing from raw pair")
                binding = bindings.get((entry.world, comparison))
                if binding is None:
                    _error(f"C1 row {comparison} is missing its authenticated binding")
                if (
                    binding["source_anchor_sha256"] != anchor
                    or binding["common_random_field_sha256"] != common
                    or binding["focal_user"] != focal
                    or binding["reference_action"] != row.raw_pair.reference_action
                    or binding["candidate_action"] != row.raw_pair.candidate_action
                    or tuple(binding["candidate_physical_key"]) != tuple(candidate)
                    or binding["source_rule"] != row.c1_source_rule
                    or binding["source_seed"] != entry.world
                ):
                    _error(f"C1 binding disagrees with typed row {comparison}")
            else:
                comparison = _canonical_sha256({
                    "source_anchor_sha256": row["source_anchor_sha256"],
                    "world": row["world"], "step_index": row["step_index"],
                    "focal_user": row["focal_user"], "reference_action": row["reference_action"],
                    "candidate_action": row["candidate_action"], "candidate_physical_key": row["candidate_physical_key"],
                    "source_rule": row["source_rule"], "schedule_sha256": row["schedule_sha256"],
                    "ops3_anchor_sha256": row["provenance"]["ops3_anchor_sha256"],
                    "ops3_projection_sha256": row["provenance"]["ops3_projection_sha256"],
                    "target_delta": row["target_delta"], "target_unit": row["target_unit"],
                })
                binding = bindings.get((entry.world, comparison))
                if binding is None:
                    _error("C2 selected-pair row is missing its authenticated binding")
                expected_binding = {
                    "mode": entry.mode,
                    "source_anchor_sha256": row["source_anchor_sha256"], "world": row["world"],
                    "step_index": row["step_index"], "focal_user": row["focal_user"],
                    "reference_action": row["reference_action"], "candidate_action": row["candidate_action"],
                    "candidate_physical_key": row["candidate_physical_key"], "source_rule": row["source_rule"],
                    "schedule_sha256": row["schedule_sha256"], "ops3_anchor_sha256": row["provenance"]["ops3_anchor_sha256"],
                    "ops3_projection_sha256": row["provenance"]["ops3_projection_sha256"],
                    "target_delta": row["target_delta"], "target_unit": row["target_unit"],
                }
                if binding != expected_binding:
                    _error(f"C2 binding disagrees with typed row {comparison}")
            expected_keys.add((entry.world, comparison))
    if route == "C1" and set(bindings) != expected_keys:
        _error(f"{route} row bindings contain an unknown comparison")
    if route == "C2" and not expected_keys.issubset(bindings):
        _error("C2 selected-pair bindings do not cover this mode's rows")


def _readonly_concat(arrays: Sequence[np.ndarray], *, dtype: np.dtype[Any]) -> np.ndarray:
    try:
        result = np.concatenate([np.asarray(array, dtype=dtype) for array in arrays], axis=0)
    except (TypeError, ValueError) as cause:
        _error("route batches have incompatible array shapes", cause=cause)
    result = np.array(result, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _aggregate_pair_batches(
    batches: Sequence[RouteBatch], *, route: str
) -> EEAxisPairBatch | EEAxisV014NormalizedPairBatch:
    if not batches:
        _error(f"{route} requires at least one typed route batch")
    pair_batches = [batch.pair_batch for batch in batches]
    if route == "C2":
        if any(not isinstance(batch, EEAxisV014NormalizedPairBatch) for batch in pair_batches):
            _error("aggregated C2 batches lost their normalized OPS-3 type")
        c2_batches = [batch for batch in pair_batches if isinstance(batch, EEAxisV014NormalizedPairBatch)]
        result_c2 = EEAxisV014NormalizedPairBatch(
            states=_readonly_concat([batch.states for batch in c2_batches], dtype=np.dtype(np.float32)),
            reference_actions=_readonly_concat([batch.reference_actions for batch in c2_batches], dtype=np.dtype(np.int64)),
            candidate_actions=_readonly_concat([batch.candidate_actions for batch in c2_batches], dtype=np.dtype(np.int64)),
            normalized_target_deltas=_readonly_concat([batch.normalized_target_deltas for batch in c2_batches], dtype=np.dtype(np.float64)),
            action_masks=_readonly_concat([batch.action_masks for batch in c2_batches], dtype=np.dtype(np.bool_)),
        )
        try:
            result_c2.validate(config=_ops3_head_config(result_c2))
        except (TypeError, ValueError, MCRLContractError) as cause:
            _error("aggregated C2 normalized batch is malformed", cause=cause)
        return result_c2
    if any(not isinstance(batch, EEAxisPairBatch) for batch in pair_batches):
        _error("aggregated C1 batches lost their raw-bit type")
    c1_batches = [batch for batch in pair_batches if isinstance(batch, EEAxisPairBatch)]
    result = EEAxisPairBatch(
        states=_readonly_concat([batch.states for batch in c1_batches], dtype=np.dtype(np.float32)),
        reference_actions=_readonly_concat([batch.reference_actions for batch in c1_batches], dtype=np.dtype(np.int64)),
        candidate_actions=_readonly_concat([batch.candidate_actions for batch in c1_batches], dtype=np.dtype(np.int64)),
        target_surplus_bits=_readonly_concat([batch.target_surplus_bits for batch in c1_batches], dtype=np.dtype(np.float64)),
        action_masks=_readonly_concat([batch.action_masks for batch in c1_batches], dtype=np.dtype(np.bool_)),
    )
    try:
        result.validate(state_dim=EE_AXIS_STATE_DIM, action_dim=NUM_ACTIONS)
    except (TypeError, ValueError, MCRLContractError) as cause:
        _error(f"aggregated {route} pair batch is malformed", cause=cause)
    return result


@dataclass(frozen=True, slots=True)
class V023ModeInputs:
    """All authenticated C1/C2 learner inputs for exactly one mode."""

    mode: str
    c1_datasets: tuple[V023DatasetEntry, ...]
    c2_datasets: tuple[V023DatasetEntry, ...]
    c1_route_batches: tuple[RouteBatch, ...]
    c2_route_batches: tuple[RouteBatch, ...]
    c1_pair_batch: EEAxisPairBatch
    c2_pair_batch: EEAxisV014NormalizedPairBatch

    @property
    def c1(self) -> EEAxisPairBatch:
        return self.c1_pair_batch

    @property
    def c2(self) -> EEAxisV014NormalizedPairBatch:
        return self.c2_pair_batch

    def route_batches(self, route: str) -> tuple[RouteBatch, ...]:
        if route == "C1":
            return self.c1_route_batches
        if route == "C2":
            return self.c2_route_batches
        _error("V023 mode inputs expose only C1 and C2 target batches")


@dataclass(frozen=True, slots=True)
class V023TargetArtifact:
    """The sealed final target root and its two route-separated mode views."""

    root: Path
    receipt: Mapping[str, object]
    modes: tuple[V023ModeInputs, ...]

    def for_mode(self, mode: str) -> V023ModeInputs:
        if mode not in TARGET_MODES:
            _error("mode must be informed or neutral")
        for inputs in self.modes:
            if inputs.mode == mode:
                return inputs
        _error(f"target root does not contain completed {mode} inputs")

    def pair_batch(
        self, route: str, *, mode: str = "informed"
    ) -> EEAxisPairBatch | EEAxisV014NormalizedPairBatch:
        inputs = self.for_mode(mode)
        if route == "C1":
            return inputs.c1_pair_batch
        if route == "C2":
            return inputs.c2_pair_batch
        _error("target artifact pair_batch route must be C1 or C2")


def _load_mode(
    *,
    destination: Path,
    listed: Mapping[str, str],
    receipt: Mapping[str, object],
    source: Mapping[str, object],
    lambda_bits: float,
    interval: float,
    mode: str,
) -> V023ModeInputs:
    datasets = receipt["datasets"]
    if not isinstance(datasets, dict) or set(datasets) != {"C1", "C2"}:
        _error("receipt datasets must contain C1 and C2")
    entries: dict[str, list[V023DatasetEntry]] = {"C1": [], "C2": []}
    source_manifest = _digest(source["source_manifest_sha256"], field="source.source_manifest_sha256")
    checkpoint = _digest(source["checkpoint_sha256"], field="source.checkpoint_sha256")
    for route in ("C1", "C2"):
        family = datasets[route]
        if not isinstance(family, dict) or not family:
            _error(f"receipt datasets.{route} must be nonempty")
        for key, metadata in family.items():
            key_mode, world = _parse_dataset_key(key, route=route)
            if key_mode != mode:
                continue
            entry = _typed_dataset(
                destination=destination,
                listed=listed,
                route=route,
                mode=mode,
                world=world,
                metadata=metadata,
                source_manifest=source_manifest,
                checkpoint=checkpoint,
                lambda_bits=lambda_bits,
                interval=interval,
            )
            _validate_mode_route_identity(entry)
            entries[route].append(entry)
        if not entries[route]:
            _error(f"receipt contains no completed {route} dataset for {mode}")
        entries[route].sort(key=lambda entry: (entry.world, entry.path.name))
    all_dataset_names = {
        entry.path.name for route_entries in entries.values() for entry in route_entries
    }
    for route in ("C1", "C2"):
        family = datasets[route]
        assert isinstance(family, dict)
        for key in family:
            key_mode, _world = _parse_dataset_key(key, route=route)
            expected_name = f"{route.lower()}-{key_mode}-world-{key.split(':', 1)[1]}.json"
            if expected_name not in listed:
                _error(f"receipt dataset {expected_name} is not manifest-listed")
            if key_mode == mode and expected_name not in all_dataset_names:
                _error(f"receipt dataset {expected_name} was not loaded")
    c1 = tuple(entries["C1"])
    c2 = tuple(entries["C2"])
    _validate_bindings(receipt=receipt, entries=(*c1, *c2), mode=mode, route="C1")
    _validate_bindings(receipt=receipt, entries=(*c1, *c2), mode=mode, route="C2")
    c1_batches = tuple(entry.route_batch for entry in c1)
    c2_batches = tuple(entry.route_batch for entry in c2)
    for batch in (*c1_batches, *c2_batches):
        try:
            batch.verify()
        except Exception as cause:
            _error("typed route batch failed verification", cause=cause)
    c1_pair_batch = _aggregate_pair_batches(c1_batches, route="C1")
    c2_pair_batch = _aggregate_pair_batches(c2_batches, route="C2")
    assert isinstance(c2_pair_batch, EEAxisV014NormalizedPairBatch)
    return V023ModeInputs(
        mode=mode,
        c1_datasets=c1,
        c2_datasets=c2,
        c1_route_batches=tuple(c1_batches),
        c2_route_batches=tuple(c2_batches),
        c1_pair_batch=c1_pair_batch,
        c2_pair_batch=c2_pair_batch,
    )


def load_completed_target_artifact(root: str | Path) -> V023TargetArtifact:
    """Authenticate and load one final ``COMPLETE`` C1/C2 target root.

    The returned modes stay separate.  A caller must choose a mode explicitly
    before obtaining a pair batch, so informed and neutral rows cannot be
    accidentally concatenated into one learner input.
    """

    destination, receipt, listed = _authenticate_root(root)
    source, formula, lambda_bits, interval = _validate_receipt_header(receipt)
    datasets = receipt["datasets"]
    assert isinstance(datasets, dict)
    expected_names = {"receipt.json"}
    for route in ("C1", "C2"):
        family = datasets[route]
        if not isinstance(family, dict):
            _error(f"receipt datasets.{route} is malformed")
        for key in family:
            mode, world = _parse_dataset_key(key, route=route)
            expected_names.add(f"{route.lower()}-{mode}-world-{world}.json")
    if set(listed) != expected_names:
        _error("manifest contains files outside the C1/C2 receipt closure")
    modes = tuple(
        _load_mode(
            destination=destination,
            listed=listed,
            receipt=receipt,
            source=source,
            lambda_bits=lambda_bits,
            interval=interval,
            mode=mode,
        )
        for mode in TARGET_MODES
    )
    c1_policy_versions = {
        entry.dataset.source_policy_version
        for inputs in modes
        for entry in inputs.c1_datasets
        if isinstance(entry.dataset, EEAxisOpeningDataset)
    }
    if len(c1_policy_versions) != 1:
        _error("C1 datasets mix source policy versions")
    return V023TargetArtifact(
        root=destination,
        receipt=MappingProxyType(dict(receipt)),
        modes=modes,
    )


def load_completed_target_batches(
    root: str | Path, *, mode: str = "informed"
) -> V023ModeInputs:
    """Convenience wrapper returning one explicitly selected mode."""

    return load_completed_target_artifact(root).for_mode(mode)


@dataclass(frozen=True, slots=True)
class V023C3Inputs:
    """Typed LC-SRS surfaces, selected labels, and sampled mini-batches.

    ``normalized_targets_by_anchor`` is deliberately separate from
    ``surfaces``.  A neutral/matched-placebo source may select different
    labels for the same physical surface, but it must retain the original
    surface (and therefore the original feature/class/action universe).
    Entries are positional: entry ``i`` belongs to ``surfaces[i]``.
    """

    surfaces: tuple[LCSRSAnchorSurface, ...]
    sampled_batches: tuple[LCSRSC3SampledBatch, ...]
    # Keep the original two positional constructor arguments valid for
    # informed/legacy callers.  The loader always materializes this as a
    # validated tuple; a direct legacy construction receives physical targets
    # through ``__post_init__`` below.
    normalized_targets_by_anchor: tuple[np.ndarray, ...] | None = None

    def __post_init__(self) -> None:
        if self.normalized_targets_by_anchor is None:
            targets = tuple(surface.normalized_targets for surface in self.surfaces)
            object.__setattr__(self, "normalized_targets_by_anchor", targets)


def _selected_c3_targets(
    surfaces: tuple[LCSRSAnchorSurface, ...],
    normalized_targets_by_anchor: Sequence[np.ndarray]
    | Mapping[int, np.ndarray]
    | None,
) -> tuple[np.ndarray, ...]:
    """Materialize and validate the selected target surface for each anchor.

    The default is the physical/informed target on each retained surface.
    An explicit mapping is accepted only with exact positional integer keys;
    this prevents insertion order or an anchor digest typo from silently
    retargeting a sampled row to a different surface.
    """

    if normalized_targets_by_anchor is None:
        raw_targets: tuple[object, ...] = tuple(
            surface.normalized_targets for surface in surfaces
        )
    elif isinstance(normalized_targets_by_anchor, Mapping):
        keys = tuple(normalized_targets_by_anchor.keys())
        if any(type(key) is not int for key in keys):
            _error("C3 target override mapping keys must be exact anchor integers")
        expected_keys = set(range(len(surfaces)))
        if set(keys) != expected_keys:
            _error("C3 target override mapping keys must exactly cover anchor order")
        raw_targets = tuple(
            normalized_targets_by_anchor[index] for index in range(len(surfaces))
        )
    else:
        if isinstance(normalized_targets_by_anchor, (str, bytes, bytearray)):
            _error("C3 target overrides must be an ordered sequence or mapping")
        try:
            raw_targets = tuple(normalized_targets_by_anchor)
        except TypeError as cause:
            _error("C3 target overrides must be an ordered sequence or mapping", cause=cause)
    if len(raw_targets) != len(surfaces):
        _error("C3 target override count must equal anchor count")

    selected: list[np.ndarray] = []
    for index, (surface, value) in enumerate(zip(surfaces, raw_targets, strict=True)):
        try:
            target = np.array(value, dtype=np.dtype(np.float32), copy=True, order="C")
        except (TypeError, ValueError, OverflowError) as cause:
            _error(f"C3 target override {index} cannot be materialized as float32", cause=cause)
        if target.shape != surface.normalized_targets.shape:
            _error(f"C3 target override {index} shape disagrees with its surface")
        if not np.all(np.isfinite(target)):
            _error(f"C3 target override {index} contains non-finite values")
        if np.any(target[surface.row_class != LCSRS_ROW_SUPPORTED] != np.float32(0.0)):
            _error(
                f"C3 target override {index} may be nonzero only on SUPPORTED cells"
            )
        target.setflags(write=False)
        selected.append(target)
    return tuple(selected)


def load_lcsrs_c3_inputs(
    surfaces_or_records: Sequence[LCSRSAnchorSurface] | Sequence[LCSRSAnchorRecord],
    sampled_batches: Sequence[LCSRSC3SampledBatch] = (),
    *,
    normalized_targets_by_anchor: Sequence[np.ndarray]
    | Mapping[int, np.ndarray]
    | None = None,
) -> V023C3Inputs:
    """Validate current typed C3 surfaces and sampled batches.

    Anchor indices in ``LCSRSC3SampledBatch`` are positional.  Therefore the
    supplied surface order is retained exactly; callers loading a source
    artifact should pass its already deterministic record order.
    """

    try:
        source = tuple(surfaces_or_records)
    except TypeError as cause:
        _error("C3 surfaces must be a sequence", cause=cause)
    if not source:
        _error("LC-SRS C3 input needs at least one anchor surface")
    if all(isinstance(item, LCSRSAnchorRecord) for item in source):
        surfaces = tuple(item.surface for item in source)  # type: ignore[union-attr]
    elif all(isinstance(item, LCSRSAnchorSurface) for item in source):
        surfaces = tuple(source)  # type: ignore[assignment]
    else:
        _error("C3 inputs cannot mix anchor records and surfaces")
    if len({surface.content_digest for surface in surfaces}) != len(surfaces):
        _error("C3 inputs contain duplicate anchor surfaces")
    for index, surface in enumerate(surfaces):
        if not isinstance(surface, LCSRSAnchorSurface):
            _error(f"C3 surface {index} has the wrong typed class")
        try:
            surface.view.verify()
        except Exception as cause:
            _error(f"C3 surface {index} view verification failed", cause=cause)
    selected_targets = _selected_c3_targets(
        surfaces, normalized_targets_by_anchor
    )
    try:
        batches = tuple(sampled_batches)
    except TypeError as cause:
        _error("C3 sampled batches must be a sequence", cause=cause)
    for batch_index, batch in enumerate(batches):
        if not isinstance(batch, LCSRSC3SampledBatch):
            _error(f"C3 sampled batch {batch_index} has the wrong typed class")
        for row, (anchor, row_class, user, action, target) in enumerate(
            zip(
                batch.anchor_indices.tolist(),
                batch.row_classes.tolist(),
                batch.user_indices.tolist(),
                batch.action_indices.tolist(),
                batch.normalized_targets.tolist(),
                strict=True,
            )
        ):
            if anchor >= len(surfaces):
                _error(f"C3 sampled batch {batch_index} anchor is outside surfaces")
            surface = surfaces[int(anchor)]
            users, actions = surface.row_class.shape
            if user >= users or action >= actions:
                _error(f"C3 sampled batch {batch_index} row {row} cell is outside surface")
            if not surface.view.action_mask[int(user), int(action)]:
                _error(f"C3 sampled batch {batch_index} row {row} selects an illegal cell")
            if int(surface.row_class[int(user), int(action)]) != int(row_class):
                _error(f"C3 sampled batch {batch_index} row {row} class disagrees with surface")
            if np.float32(target) != selected_targets[int(anchor)][int(user), int(action)]:
                _error(
                    f"C3 sampled batch {batch_index} row {row} target disagrees with selected target"
                )
    return V023C3Inputs(
        surfaces=surfaces,
        normalized_targets_by_anchor=selected_targets,
        sampled_batches=batches,
    )


def load_lcsrs_c3_source_artifact(
    index_path: str | Path,
    *,
    expected_world: int | None = None,
    expected_preflight_sha256: str | None = None,
    sampled_batches: Sequence[LCSRSC3SampledBatch] = (),
    normalized_targets_by_anchor: Sequence[np.ndarray]
    | Mapping[int, np.ndarray]
    | None = None,
) -> V023C3Inputs:
    """Load an existing typed C3 source shard, then validate sampled inputs.

    The source-artifact module owns its index/NPZ authentication and
    reconstruction.  This wrapper deliberately does not duplicate that
    serializer; it only projects the returned typed anchor records through
    :func:`load_lcsrs_c3_inputs`.
    """

    try:
        from mcrl.runtime.ee_axis_lcsrs_c3_source_artifact import (
            load_v023_world_source_artifact,
        )

        artifact = load_v023_world_source_artifact(
            Path(index_path),
            expected_world=expected_world,
            expected_preflight_sha256=expected_preflight_sha256,
        )
    except V023TargetBatchAdapterError:
        raise
    except Exception as cause:
        _error("LC-SRS C3 source artifact failed typed authentication", cause=cause)
    return load_lcsrs_c3_inputs(
        artifact.records,
        sampled_batches,
        normalized_targets_by_anchor=normalized_targets_by_anchor,
    )


@dataclass(frozen=True, slots=True)
class RouteDispatch:
    """One read-only route/batch dispatch in a deterministic episode plan."""

    episode_index: int
    route: str
    batch_index: int


@dataclass(frozen=True, slots=True)
class V023RouteSchedule:
    """Deterministic dispatch metadata for plumbing or a later runner."""

    episodes: int
    route_order: tuple[str, ...]
    dispatches: tuple[RouteDispatch, ...]

    def verify(
        self,
        *,
        c1_batch_count: int,
        c2_batch_count: int,
        c3_batch_count: int,
    ) -> None:
        if type(self.episodes) is not int or self.episodes < 1:
            _error("route schedule episodes must be positive")
        if self.route_order != TARGET_ROUTES:
            _error("route schedule order must be C1, C2, C3")
        counts = {"C1": c1_batch_count, "C2": c2_batch_count, "C3": c3_batch_count}
        if any(type(value) is not int or value < 1 for value in counts.values()):
            _error("route schedule requires nonempty route batch counts")
        expected = tuple(
            RouteDispatch(episode_index=episode, route=route, batch_index=batch_index)
            for episode in range(self.episodes)
            for route in self.route_order
            for batch_index in range(counts[route])
        )
        if self.dispatches != expected:
            _error("route schedule dispatch order is not deterministic")


def build_route_schedule(
    mode_inputs: V023ModeInputs,
    c3_inputs: V023C3Inputs,
    *,
    episodes: int = 1,
) -> V023RouteSchedule:
    """Build dispatch metadata without updating a network or running physics."""

    if not isinstance(mode_inputs, V023ModeInputs) or not isinstance(c3_inputs, V023C3Inputs):
        _error("route schedule requires typed C1/C2 and C3 inputs")
    _exact_int(episodes, field="episodes", minimum=1)
    if not mode_inputs.c1_route_batches or not mode_inputs.c2_route_batches:
        _error("route schedule requires nonempty C1 and C2 route batches")
    if not c3_inputs.sampled_batches:
        _error("route schedule requires at least one sampled C3 batch")
    dispatches = tuple(
        RouteDispatch(episode_index=episode, route=route, batch_index=batch_index)
        for episode in range(episodes)
        for route, batch_count in (
            ("C1", len(mode_inputs.c1_route_batches)),
            ("C2", len(mode_inputs.c2_route_batches)),
            ("C3", len(c3_inputs.sampled_batches)),
        )
        for batch_index in range(batch_count)
    )
    schedule = V023RouteSchedule(
        episodes=episodes,
        route_order=TARGET_ROUTES,
        dispatches=dispatches,
    )
    schedule.verify(
        c1_batch_count=len(mode_inputs.c1_route_batches),
        c2_batch_count=len(mode_inputs.c2_route_batches),
        c3_batch_count=len(c3_inputs.sampled_batches),
    )
    return schedule


__all__ = [
    "OPS3_SELECTED_PAIR_SCHEMA",
    "OPS3_TARGET_UNIT",
    "RouteDispatch",
    "TARGET_CLAIM_CEILING",
    "TARGET_GENERATION_SCHEMA",
    "TARGET_MODES",
    "TARGET_ROUTES",
    "V023C3Inputs",
    "V023DatasetEntry",
    "V023ModeInputs",
    "V023OPS3RouteBatch",
    "V023OPS3SelectedPairDataset",
    "V023RouteSchedule",
    "V023TargetArtifact",
    "V023TargetBatchAdapterError",
    "build_route_schedule",
    "load_completed_target_artifact",
    "load_completed_target_batches",
    "load_lcsrs_c3_inputs",
    "load_lcsrs_c3_source_artifact",
]
