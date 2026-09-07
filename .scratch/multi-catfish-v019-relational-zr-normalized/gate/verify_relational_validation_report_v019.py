#!/usr/bin/env python3
"""Clean-room verifier for a V0.19 relational-Q3 validation report.

The verifier intentionally does not import the learner runner or the report
generator.  It re-authenticates source closures and raw prediction NPZ files,
checks checkpoint/file bindings, rebuilds target-free deployable scores from
external Q1/Q2 arrays, and recomputes teacher-action agreement, nulls,
pivotal/stable agreement, and positive-support metrics from the exact-ZR
source labels.  No simulator, learner update, or TEST byte is opened.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
LEARNER = HERE.parent / "learner"
REPO = HERE.parents[2]
for _path in (HERE, LEARNER, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from relational_source_bridge import read_source_closure  # noqa: E402
from relational_source_schema import (  # noqa: E402
    ACTION_DIM,
    RelationalZRC3Source,
    validate_world_split,
)
from mcrl.algorithms.ee_axis_relational_zr_c3_head_v019 import (  # noqa: E402
    NORMALIZED_BITS_PER_KAPPA,
)
from relational_q3_learner_v019 import (  # noqa: E402
    CHECKPOINT_SCHEMA,
    CHECKPOINT_VERSION,
)


REPORT_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-validation-report-v1"
REPORT_VERSION = 1
REPORT_FILENAME = "result.json"
REPORT_SEAL_FILENAME = "result-seal.json"
RUNNER_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-mechanical-run-v1"
REQUIRED_UPDATES = 100
PREDICTION_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-validation-predictions-v1"
PREDICTION_METADATA_FILENAME = "validation-predictions.json"
PREDICTION_NPZ_FILENAME = "validation-predictions.npz"
PREDICTION_RECEIPT_FILENAME = "validation-predictions.sha256"
SURFACE_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-validation-surfaces-v1"
SURFACE_NPZ_FILENAME = "validation-surfaces.npz"
SURFACE_METADATA_FILENAME = "validation-surfaces.json"
SURFACE_RECEIPT_FILENAME = "validation-surfaces.sha256"
BACKGROUND_SCHEMA = "multi-catfish-mcrl-v019-relational-zr-background-surfaces-v1"
BACKGROUND_NPZ_FILENAME = "background.npz"
BACKGROUND_METADATA_FILENAME = "background.json"
BACKGROUND_RECEIPT_FILENAME = "background.sha256"
BACKGROUND_REPRESENTATION_SEPARATE = "SEPARATE_Q1_Q2"
BACKGROUND_REPRESENTATION_SUM_ZERO = "Q1_PLUS_Q2_SUM_WITH_ZERO_RIGHT"
BACKGROUND_REPRESENTATIONS = frozenset(
    {BACKGROUND_REPRESENTATION_SEPARATE, BACKGROUND_REPRESENTATION_SUM_ZERO}
)
FROZEN_STATUS = "FROZEN_BEFORE_OUTCOME"
EXPECTED_TRAIN_WORLD_COUNT = 4
EXPECTED_VALIDATION_WORLD_COUNT = 3
EXPECTED_INITIALIZATION_COUNT = 3
REQUIRED_NULL_KINDS = ("zero", "action_only")
_Q_VALUE_KEY = re.compile(r"^q_values_(\d{4})$")
_NULL_KINDS = frozenset({"zero", "train_median", "action_only"})


class RelationalValidationVerificationError(RuntimeError):
    """A persisted validation report does not reproduce independently."""


VerificationError = RelationalValidationVerificationError


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RelationalValidationVerificationError(
            "payload is not finite canonical JSON"
        ) from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RelationalValidationVerificationError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RelationalValidationVerificationError(f"{field} must be a positive integer")
    return value


def _finite(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalValidationVerificationError(f"{field} must be finite") from error
    if not math.isfinite(result):
        raise RelationalValidationVerificationError(f"{field} must be finite")
    return result


def _array_sha256(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    digest = hashlib.sha256()
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RelationalValidationVerificationError(f"expected a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path, *, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise RelationalValidationVerificationError(f"missing regular {label}: {path}")
    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RelationalValidationVerificationError(f"{label} is not JSON: {path}") from error
    if not isinstance(payload, dict) or raw != _canonical_bytes(payload):
        raise RelationalValidationVerificationError(f"{label} is not canonical JSON: {path}")
    return payload


def _resolve(path_value: object, *, parent: Path, field: str) -> Path:
    if not isinstance(path_value, str) or not path_value:
        raise RelationalValidationVerificationError(f"{field} path is malformed")
    path = Path(path_value)
    if not path.is_absolute():
        path = parent / path
    if path.is_symlink() or not path.is_file():
        raise RelationalValidationVerificationError(f"missing regular {field}: {path}")
    return path


def _config_body(config: object) -> dict[str, object]:
    if isinstance(config, Mapping):
        body = dict(config)
    elif hasattr(config, "as_dict"):
        value = config.as_dict()
        if not isinstance(value, Mapping):
            raise RelationalValidationVerificationError("external config as_dict is not a mapping")
        body = dict(value)
    else:
        raise RelationalValidationVerificationError("external validation config is malformed")
    expected = {
        "contract_sha256",
        "code_manifest_sha256",
        "source_panel_sha256",
        "train_worlds",
        "validation_worlds",
        "initialization_lineages",
        "q1_checkpoint_sha256_by_lineage",
        "q2_checkpoint_sha256_by_lineage",
        "kappa_bits_hex",
        "output_unit_mode",
        "null_kinds",
        "gate_config",
        "expected_checkpoint_sha256_by_initialization",
    }
    if set(body) != expected:
        raise RelationalValidationVerificationError("external config has unknown or missing fields")
    for field in ("contract_sha256", "code_manifest_sha256", "source_panel_sha256"):
        _digest(body[field], field=field)
    try:
        kappa = float.fromhex(str(body["kappa_bits_hex"]))
    except (TypeError, ValueError, OverflowError) as error:
        raise RelationalValidationVerificationError("external kappa_bits_hex is malformed") from error
    if not math.isfinite(kappa) or kappa <= 0.0:
        raise RelationalValidationVerificationError("external kappa_bits must be finite and positive")
    if body["output_unit_mode"] != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationVerificationError(
            "external validation output_unit_mode is not normalized_bits_per_kappa"
        )
    train = tuple(body["train_worlds"])
    validation = tuple(body["validation_worlds"])
    for field, values in (("train_worlds", train), ("validation_worlds", validation)):
        if not values or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values) or len(set(values)) != len(values):
            raise RelationalValidationVerificationError(f"external {field} is malformed")
    if set(train) & set(validation):
        raise RelationalValidationVerificationError("external train/validation worlds overlap")
    raw_inits = body["initialization_lineages"]
    if not isinstance(raw_inits, list) or not raw_inits:
        raise RelationalValidationVerificationError("external initialization closure is empty")
    initializations: list[tuple[int, int]] = []
    for item in raw_inits:
        if not isinstance(item, Mapping) or set(item) != {"initialization_seed", "lineage"}:
            raise RelationalValidationVerificationError("external initialization entry is malformed")
        initializations.append((_positive_int(item["initialization_seed"], field="initialization_seed"), _positive_int(item["lineage"], field="lineage")))
    if len({seed for seed, _lineage in initializations}) != len(initializations) or len({lineage for _seed, lineage in initializations}) != len(initializations):
        raise RelationalValidationVerificationError("external initialization closure has duplicates")
    for field in ("q1_checkpoint_sha256_by_lineage", "q2_checkpoint_sha256_by_lineage"):
        raw = body[field]
        if not isinstance(raw, list) or not raw:
            raise RelationalValidationVerificationError(f"external {field} is empty")
        values = []
        for item in raw:
            if not isinstance(item, Mapping) or set(item) != {"lineage", "sha256"}:
                raise RelationalValidationVerificationError(f"external {field} entry is malformed")
            values.append((_positive_int(item["lineage"], field=f"{field}.lineage"), _digest(item["sha256"], field=f"{field}.sha256")))
        if len({lineage for lineage, _digest_value in values}) != len(values) or {lineage for lineage, _digest_value in values} != {lineage for _seed, lineage in initializations}:
            raise RelationalValidationVerificationError(f"external {field} does not cover lineages")
    nulls = body["null_kinds"]
    if not isinstance(nulls, list) or not nulls or len(set(nulls)) != len(nulls) or any(kind not in _NULL_KINDS for kind in nulls):
        raise RelationalValidationVerificationError("external null_kinds is malformed")
    expected_checkpoints = body["expected_checkpoint_sha256_by_initialization"]
    if not isinstance(expected_checkpoints, list):
        raise RelationalValidationVerificationError("external checkpoint bindings are malformed")
    if expected_checkpoints:
        seen = []
        for item in expected_checkpoints:
            if not isinstance(item, Mapping) or set(item) != {"initialization_seed", "sha256"}:
                raise RelationalValidationVerificationError("external checkpoint binding entry is malformed")
            seen.append((_positive_int(item["initialization_seed"], field="checkpoint.initialization_seed"), _digest(item["sha256"], field="checkpoint.sha256")))
        if {seed for seed, _digest_value in seen} != {seed for seed, _lineage in initializations}:
            raise RelationalValidationVerificationError("external checkpoint bindings do not cover initializations")
    gate = body["gate_config"]
    if gate is not None:
        if not isinstance(gate, Mapping):
            raise RelationalValidationVerificationError("external gate_config is malformed")
        required = {"contract_sha256", "contract_status", "min_mean_skill", "min_positive_initializations", "min_supported_change_rate", "min_supported_initializations", "required_updates"}
        if set(gate) != required or gate["contract_sha256"] != body["contract_sha256"] or gate["contract_status"] != FROZEN_STATUS or gate["required_updates"] != REQUIRED_UPDATES:
            raise RelationalValidationVerificationError("external gate_config is stale or mismatched")
        skill = _finite(gate["min_mean_skill"], field="gate.min_mean_skill")
        support = _finite(gate["min_supported_change_rate"], field="gate.min_supported_change_rate")
        if not 0.0 <= support <= 1.0:
            raise RelationalValidationVerificationError("external gate support threshold is outside [0,1]")
        for field in ("min_positive_initializations", "min_supported_initializations"):
            if isinstance(gate[field], bool) or not isinstance(gate[field], int) or gate[field] < 1:
                raise RelationalValidationVerificationError(f"external {field} is malformed")
        if (
            skill != 0.0
            or support != 0.5
            or gate["min_positive_initializations"] != 2
            or gate["min_supported_initializations"] != 2
        ):
            raise RelationalValidationVerificationError(
                "external gate thresholds disagree with the frozen V0.19 acceptance rule"
            )
        if len(train) != EXPECTED_TRAIN_WORLD_COUNT:
            raise RelationalValidationVerificationError(
                f"frozen gate requires exactly {EXPECTED_TRAIN_WORLD_COUNT} TRAIN worlds"
            )
        if len(validation) != EXPECTED_VALIDATION_WORLD_COUNT:
            raise RelationalValidationVerificationError(
                f"frozen gate requires exactly {EXPECTED_VALIDATION_WORLD_COUNT} VALIDATION worlds"
            )
        if len(initializations) != EXPECTED_INITIALIZATION_COUNT:
            raise RelationalValidationVerificationError(
                f"frozen gate requires exactly {EXPECTED_INITIALIZATION_COUNT} initializations"
            )
        if tuple(nulls) != REQUIRED_NULL_KINDS:
            raise RelationalValidationVerificationError(
                "frozen gate requires ordered null_kinds zero, action_only"
            )
    body["kappa_bits"] = kappa
    body["output_unit_mode"] = NORMALIZED_BITS_PER_KAPPA
    body["initializations"] = tuple(initializations)
    body["q1_map"] = {int(item["lineage"]): item["sha256"] for item in body["q1_checkpoint_sha256_by_lineage"]}
    body["q2_map"] = {int(item["lineage"]): item["sha256"] for item in body["q2_checkpoint_sha256_by_lineage"]}
    body["checkpoint_map"] = {int(item["initialization_seed"]): item["sha256"] for item in expected_checkpoints}
    return body


def _read_receipt(path: Path, *, schema: str, fields: Sequence[str]) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise RelationalValidationVerificationError(f"missing receipt: {path}")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise RelationalValidationVerificationError("receipt is not ASCII") from error
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise RelationalValidationVerificationError("receipt contains malformed line")
        key, value = line.split("=", 1)
        if key in values or key not in fields:
            raise RelationalValidationVerificationError("receipt contains unknown or duplicate field")
        values[key] = value
    if tuple(values) != tuple(fields):
        raise RelationalValidationVerificationError("receipt fields are incomplete or reordered")
    if values["schema"] != schema:
        raise RelationalValidationVerificationError("receipt schema is stale")
    for field in fields[1:]:
        _digest(values[field], field=f"receipt.{field}")
    return values


def _read_prediction_package(root: Path) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    metadata = _read_json(root / PREDICTION_METADATA_FILENAME, label="prediction metadata")
    receipt = _read_receipt(
        root / PREDICTION_RECEIPT_FILENAME,
        schema=PREDICTION_SCHEMA,
        fields=("schema", "metadata_sha256", "npz_sha256", "arrays_sha256", "prediction_metadata_sha256"),
    )
    supplied = _digest(metadata.get("prediction_metadata_sha256"), field="prediction_metadata_sha256")
    body = {key: value for key, value in metadata.items() if key != "prediction_metadata_sha256"}
    if canonical_sha256(body) != supplied or receipt["prediction_metadata_sha256"] != supplied:
        raise RelationalValidationVerificationError("prediction metadata self-digest failed")
    expected = {"schema", "schema_version", "initialization_seed", "lineage", "source_sha256", "parameter_sha256", "output_unit_mode", "npz_filename", "npz_sha256", "arrays", "arrays_sha256", "test_split_opened", "episode_training", "learner_update", "prediction_metadata_sha256"}
    if set(metadata) != expected or metadata.get("schema") != PREDICTION_SCHEMA or metadata.get("schema_version") != 1 or metadata.get("npz_filename") != PREDICTION_NPZ_FILENAME:
        raise RelationalValidationVerificationError("prediction metadata schema is stale")
    if metadata.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationVerificationError(
            "prediction output_unit_mode is not normalized_bits_per_kappa"
        )
    if metadata.get("test_split_opened") is not False or metadata.get("episode_training") is not False or metadata.get("learner_update") is not True:
        raise RelationalValidationVerificationError("prediction metadata crosses evaluation boundary")
    npz_path = root / PREDICTION_NPZ_FILENAME
    npz_sha256 = _digest(metadata.get("npz_sha256"), field="prediction.npz_sha256")
    if _file_sha256(npz_path) != npz_sha256 or receipt["npz_sha256"] != npz_sha256:
        raise RelationalValidationVerificationError("prediction NPZ digest mismatch")
    if _file_sha256(root / PREDICTION_METADATA_FILENAME) != receipt["metadata_sha256"] or receipt["arrays_sha256"] != metadata.get("arrays_sha256"):
        raise RelationalValidationVerificationError("prediction file receipt mismatch")
    entries = metadata.get("arrays")
    if not isinstance(entries, list) or not entries or canonical_sha256(entries) != metadata.get("arrays_sha256"):
        raise RelationalValidationVerificationError("prediction array manifest is malformed")
    arrays: dict[str, np.ndarray] = {}
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            keys = set()
            for index, entry in enumerate(entries):
                if not isinstance(entry, Mapping) or set(entry) != {"key", "split", "world_seed", "lineage", "rows", "dtype", "shape", "array_sha256"}:
                    raise RelationalValidationVerificationError("prediction array manifest entry is malformed")
                key = f"q_values_{index:04d}"
                if entry["key"] != key or _Q_VALUE_KEY.fullmatch(key) is None or entry["split"] != "VALIDATION":
                    raise RelationalValidationVerificationError("prediction manifest contains unknown/reordered arrays")
                keys.add(key)
                value = np.array(loaded[key], copy=True)
                if value.dtype.str != entry["dtype"] or list(value.shape) != entry["shape"] or entry["rows"] != value.shape[0] or _array_sha256(value) != entry["array_sha256"] or not np.issubdtype(value.dtype, np.floating) or not np.all(np.isfinite(value)):
                    raise RelationalValidationVerificationError("prediction array digest, shape, or finiteness mismatch")
                arrays[key] = value
            if set(loaded.files) != keys:
                raise RelationalValidationVerificationError("prediction NPZ contains unknown arrays")
    except (OSError, KeyError, ValueError, TypeError) as error:
        if isinstance(error, RelationalValidationVerificationError):
            raise
        raise RelationalValidationVerificationError("prediction NPZ is malformed") from error
    return arrays, metadata


def _source_manifest_entry(source: RelationalZRC3Source, bridge: Mapping[str, object]) -> dict[str, object]:
    return {
        "split": source.split,
        "world_seed": source.world_seed,
        "lineage": source.lineage,
        "rows": source.rows,
        "victim_count": source.victim_count,
        "source_arrays_sha256": source.arrays_sha256(),
        "source_npz_sha256": bridge.get("source_npz_sha256"),
        "source_metadata_sha256": bridge.get("source_metadata_sha256"),
        "bridge_metadata_sha256": bridge.get("bridge_metadata_sha256"),
    }


def _load_sources(report: Mapping[str, object], config: Mapping[str, object]) -> tuple[dict[tuple[str, int, int], RelationalZRC3Source], list[dict[str, object]]]:
    raw = report.get("source_closures")
    if not isinstance(raw, list) or not raw:
        raise RelationalValidationVerificationError("report source closure is empty")
    sources: dict[tuple[str, int, int], RelationalZRC3Source] = {}
    entries: list[dict[str, object]] = []
    records_for_split = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise RelationalValidationVerificationError("report source closure entry is malformed")
        expected_keys = {"split", "world_seed", "lineage", "rows", "victim_count", "source_arrays_sha256", "source_npz_sha256", "source_metadata_sha256", "bridge_metadata_sha256", "path"}
        if set(entry) != expected_keys:
            raise RelationalValidationVerificationError("report source closure entry has unknown fields")
        path = Path(str(entry["path"]))
        if path.is_symlink() or not path.is_dir():
            raise RelationalValidationVerificationError(f"source closure is not a regular directory: {path}")
        try:
            source, bridge = read_source_closure(path)
        except Exception as error:
            raise RelationalValidationVerificationError("source closure authentication failed") from error
        identity = (source.split, source.world_seed, source.lineage)
        if identity in sources:
            raise RelationalValidationVerificationError("report source closure contains duplicate identity")
        if dict(entry) != {**_source_manifest_entry(source, bridge), "path": str(path)}:
            raise RelationalValidationVerificationError("report source closure manifest disagrees with files")
        sources[identity] = source
        entries.append(dict(entry))
        records_for_split.append(source)
    try:
        validate_world_split(records_for_split)
    except Exception as error:
        raise RelationalValidationVerificationError("source world split is invalid") from error
    train_worlds = set(config["train_worlds"])
    validation_worlds = set(config["validation_worlds"])
    lineages = {lineage for _seed, lineage in config["initializations"]}
    if {identity[1] for identity in sources if identity[0] == "TRAIN"} != train_worlds or {identity[1] for identity in sources if identity[0] == "VALIDATION"} != validation_worlds:
        raise RelationalValidationVerificationError("source world set disagrees with external configuration")
    expected = {(split, world, lineage) for split, worlds in (("TRAIN", train_worlds), ("VALIDATION", validation_worlds)) for world in worlds for lineage in lineages}
    if set(sources) != expected:
        raise RelationalValidationVerificationError("source panel is not a complete world/lineage rectangle")
    for source in sources.values():
        if float(source.kappa_bits).hex() != float(config["kappa_bits"]).hex():
            raise RelationalValidationVerificationError("source kappa disagrees with external configuration")
    manifest = {
        "schema": "multi-catfish-mcrl-v019-relational-zr-source-panel-v1",
        "train": [dict(entry, path=None) for entry in sorted(entries, key=lambda item: (item["split"], item["world_seed"], item["lineage"])) if entry["split"] == "TRAIN"],
        "validation": [dict(entry, path=None) for entry in sorted(entries, key=lambda item: (item["split"], item["world_seed"], item["lineage"])) if entry["split"] == "VALIDATION"],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }
    # VerifiedSourcePanel.manifest does not include source paths.
    for values in (manifest["train"], manifest["validation"]):
        for value in values:
            value.pop("path", None)
    if canonical_sha256(manifest) != config["source_panel_sha256"] or report.get("source_panel_sha256") != config["source_panel_sha256"]:
        raise RelationalValidationVerificationError("source panel digest mismatch")
    return sources, entries


def _verify_normalized_checkpoint(path: Path) -> None:
    """Verify the immutable scorer-unit markers in a V0.19 checkpoint."""

    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except (OSError, EOFError, RuntimeError, ValueError, TypeError) as error:
        raise RelationalValidationVerificationError(
            "learner checkpoint could not be decoded"
        ) from error
    if not isinstance(payload, Mapping):
        raise RelationalValidationVerificationError("learner checkpoint is not a mapping")
    if payload.get("schema") != CHECKPOINT_SCHEMA or payload.get("format_version") != CHECKPOINT_VERSION:
        raise RelationalValidationVerificationError("learner checkpoint schema is stale")
    if payload.get("update_count") != REQUIRED_UPDATES:
        raise RelationalValidationVerificationError(
            f"learner checkpoint must contain exactly {REQUIRED_UPDATES} updates"
        )
    if payload.get("test_split_opened") is not False or payload.get("episode_training") is not False:
        raise RelationalValidationVerificationError(
            "learner checkpoint crosses the evaluation boundary"
        )
    if payload.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationVerificationError(
            "learner checkpoint output_unit_mode is not normalized_bits_per_kappa"
        )
    config = payload.get("config")
    if not isinstance(config, Mapping) or config.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationVerificationError(
            "learner checkpoint config output_unit_mode drifted"
        )


def _read_learner_result(root: Path, *, seed: int, lineage: int, sources: Mapping[tuple[str, int, int], RelationalZRC3Source], config: Mapping[str, object]) -> tuple[dict[str, object], dict[tuple[str, int, int], np.ndarray], dict[str, object], Path, str]:
    result_path = root / "result.json"
    result = _read_json(result_path, label="learner result")
    result_digest = _digest(result.get("result_sha256"), field="learner result_sha256")
    if canonical_sha256({key: value for key, value in result.items() if key != "result_sha256"}) != result_digest:
        raise RelationalValidationVerificationError("learner result self-digest failed")
    if result.get("schema") != RUNNER_SCHEMA or result.get("status") != "MECHANICAL_ARTIFACT_WRITTEN" or result.get("initialization_seed") != seed or result.get("lineage") != lineage:
        raise RelationalValidationVerificationError("learner result identity/schema mismatch")
    if result.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationVerificationError(
            "learner result output_unit_mode is not normalized_bits_per_kappa"
        )
    result_config = result.get("config")
    if not isinstance(result_config, Mapping) or result_config.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationVerificationError(
            "learner result config output_unit_mode drifted"
        )
    if result.get("source_panel_sha256") != config["source_panel_sha256"] or result.get("update_count") != REQUIRED_UPDATES or result.get("restored_update_count") != REQUIRED_UPDATES or result.get("reload_bitwise_equal") is not True:
        raise RelationalValidationVerificationError("learner result update/source/reload binding mismatch")
    if result.get("test_split_opened") is not False or result.get("episode_training") is not False or result.get("scientific_gate_evaluated") is not False:
        raise RelationalValidationVerificationError("learner result crosses evaluation boundary")
    binding = result.get("q1_q2_digest_binding")
    if not isinstance(binding, Mapping) or binding.get("loaded") is not False or binding.get("modified") is not False or binding.get("q1_checkpoint_sha256") != config["q1_map"][lineage] or binding.get("q2_checkpoint_sha256") != config["q2_map"][lineage]:
        raise RelationalValidationVerificationError("Q1/Q2 checkpoint digest binding mismatch")
    checkpoint_record = result.get("checkpoint")
    if not isinstance(checkpoint_record, Mapping):
        raise RelationalValidationVerificationError("learner checkpoint receipt is missing")
    checkpoint_path = _resolve(checkpoint_record.get("path"), parent=root, field="learner checkpoint")
    checkpoint_digest = _digest(checkpoint_record.get("checkpoint_sha256"), field="checkpoint_sha256")
    if _file_sha256(checkpoint_path) != checkpoint_digest or (config["checkpoint_map"].get(seed) is not None and config["checkpoint_map"][seed] != checkpoint_digest):
        raise RelationalValidationVerificationError("checkpoint digest mismatch")
    _verify_normalized_checkpoint(checkpoint_path)
    arrays, metadata = _read_prediction_package(root)
    if metadata.get("source_sha256") != config["source_panel_sha256"] or metadata.get("initialization_seed") != seed or metadata.get("lineage") != lineage or metadata.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA or result.get("parameter_sha256") != metadata.get("parameter_sha256"):
        raise RelationalValidationVerificationError("prediction source/identity/parameter binding mismatch")
    prediction_record = result.get("validation_predictions")
    if not isinstance(prediction_record, Mapping):
        raise RelationalValidationVerificationError("learner result prediction receipt is missing")
    for field in ("npz_sha256", "arrays_sha256", "prediction_metadata_sha256"):
        if prediction_record.get(field) != metadata.get(field):
            raise RelationalValidationVerificationError(f"prediction receipt {field} mismatch")
    if result.get("validation_prediction_digest") != metadata.get("arrays_sha256"):
        raise RelationalValidationVerificationError("validation prediction digest mismatch")
    raw_entries = metadata["arrays"]
    surfaces: dict[tuple[str, int, int], np.ndarray] = {}
    for index, entry in enumerate(raw_entries):
        key = f"q_values_{index:04d}"
        world = _positive_int(entry["world_seed"], field="prediction.world_seed")
        identity = ("VALIDATION", world, lineage)
        if identity not in sources:
            raise RelationalValidationVerificationError("prediction contains an unknown or wrong-split world")
        source = sources[identity]
        value = arrays[key]
        if value.shape != (source.rows, ACTION_DIM):
            raise RelationalValidationVerificationError("prediction shape disagrees with source")
        rows = np.arange(source.rows, dtype=np.int64)
        if np.any(value[~source.action_mask] != 0.0) or np.any(value[rows, source.reference_actions] != 0.0):
            raise RelationalValidationVerificationError("prediction surface violates native-mask/reference centring")
        surfaces[identity] = value
    expected = {identity for identity in sources if identity[0] == "VALIDATION" and identity[2] == lineage}
    if set(surfaces) != expected:
        raise RelationalValidationVerificationError("prediction closure is missing a validation world")
    return result, surfaces, metadata, checkpoint_path, checkpoint_digest


def _pairs(source: RelationalZRC3Source, q: np.ndarray | None, *, kappa: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mask = np.asarray(source.action_mask)
    refs = np.asarray(source.reference_actions, dtype=np.int64)
    comparison = mask & ~np.eye(ACTION_DIM, dtype=np.bool_)[refs]
    rows, candidates = np.nonzero(comparison)
    if rows.size == 0:
        raise RelationalValidationVerificationError("source has no non-reference comparison")
    target = np.asarray(source.target_surface_bits, dtype=np.float64)
    target_delta = (target[rows, candidates] - target[rows, refs[rows]]) / float(kappa)
    prediction_delta = np.zeros_like(target_delta) if q is None else np.asarray(q[rows, candidates] - q[rows, refs[rows]], dtype=np.float64)
    return rows, candidates, target_delta, prediction_delta


def _fit_action_only(sources: Sequence[RelationalZRC3Source], *, kappa: float) -> tuple[np.ndarray, np.ndarray]:
    refs: list[int] = []
    candidates: list[int] = []
    targets: list[float] = []
    for source in sources:
        rows, candidate, target, _prediction = _pairs(source, None, kappa=kappa)
        refs.extend(source.reference_actions[rows].tolist())
        candidates.extend(candidate.tolist())
        targets.extend(target.tolist())
    design = np.zeros((len(targets), ACTION_DIM), dtype=np.float64)
    index = np.arange(len(targets), dtype=np.int64)
    design[index, np.asarray(candidates)] = 1.0
    design[index, np.asarray(refs)] = -1.0
    coefficients, _residuals, _rank, _singular = np.linalg.lstsq(design, np.asarray(targets), rcond=None)
    if not np.all(np.isfinite(coefficients)):
        raise RelationalValidationVerificationError("action-only null fit is nonfinite")
    adjacency = [set() for _action in range(ACTION_DIM)]
    for left, right in zip(refs, candidates, strict=True):
        adjacency[left].add(right)
        adjacency[right].add(left)
    components = np.full(ACTION_DIM, -1, dtype=np.int64)
    component = 0
    for start in range(ACTION_DIM):
        if components[start] >= 0 or not adjacency[start]:
            continue
        stack = [start]
        components[start] = component
        while stack:
            current = stack.pop()
            for neighbour in adjacency[current]:
                if components[neighbour] < 0:
                    components[neighbour] = component
                    stack.append(neighbour)
        component += 1
    return coefficients, components


def _masked_argmax(scores: np.ndarray, mask: np.ndarray) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    legal = np.asarray(mask)
    if values.shape != legal.shape or legal.dtype != np.bool_ or not np.all(np.isfinite(values)) or not np.all(np.any(legal, axis=1)):
        raise RelationalValidationVerificationError("deployable surface is malformed")
    return np.argmax(np.where(legal, values, -np.inf), axis=1).astype(np.int64)


def _mae_by_world(errors: Mapping[int, np.ndarray]) -> tuple[float, float, dict[str, float]]:
    if not errors or any(values.size == 0 for values in errors.values()):
        raise RelationalValidationVerificationError("validation error set is empty")
    by_world = {str(world): float(np.mean(values)) for world, values in sorted(errors.items())}
    return float(np.mean(tuple(by_world.values()))), float(np.mean(np.concatenate(tuple(errors.values())))), by_world


def _metrics(sources: Mapping[tuple[str, int, int], RelationalZRC3Source], surfaces: Mapping[tuple[str, int, int], np.ndarray], *, lineage: int, null_kinds: Sequence[str], kappa: float, background: Mapping[tuple[str, int, int], tuple[np.ndarray, np.ndarray]] | None) -> dict[str, object]:
    train = [source for identity, source in sources.items() if identity[0] == "TRAIN" and identity[2] == lineage]
    validation = [(identity, source) for identity, source in sources.items() if identity[0] == "VALIDATION" and identity[2] == lineage]
    if not train or not validation:
        raise RelationalValidationVerificationError("lineage source closure is incomplete")
    train_target = np.concatenate(tuple(_pairs(source, None, kappa=kappa)[2] for source in train))
    train_median = float(np.median(train_target)) if "train_median" in null_kinds else None
    coefficients = None
    components = None
    if "action_only" in null_kinds:
        coefficients, components = _fit_action_only(train, kappa=kappa)
    model_errors: dict[int, np.ndarray] = {}
    null_errors: dict[str, dict[int, np.ndarray]] = {kind: {} for kind in null_kinds}
    model_action_by_world: dict[int, np.ndarray] = {}
    null_action_by_world: dict[str, dict[int, np.ndarray]] = {kind: {} for kind in null_kinds}
    pivotal: dict[int, tuple[int, int]] = {}
    null_pivotal: dict[str, dict[int, np.ndarray]] = {kind: {} for kind in null_kinds}
    stable_correct = 0
    stable_total = 0
    changed = 0
    supported = 0
    positive_target_changes = 0
    pair_count = 0
    for identity, source in sorted(validation, key=lambda item: item[0]):
        q = surfaces[identity]
        rows, candidates, target_delta, prediction_delta = _pairs(source, q, kappa=kappa)
        pair_count += int(target_delta.size)
        row_model = []
        row_nulls = {kind: [] for kind in null_kinds}
        references = source.reference_actions[rows]
        for row in range(source.rows):
            keep = rows == row
            if not np.any(keep):
                continue
            row_model.append(float(np.mean(np.abs(prediction_delta[keep] - target_delta[keep]))))
            for kind in null_kinds:
                if kind == "zero":
                    prediction = np.zeros(int(np.count_nonzero(keep)), dtype=np.float64)
                elif kind == "train_median":
                    prediction = np.full(int(np.count_nonzero(keep)), train_median, dtype=np.float64)
                elif kind == "action_only":
                    prediction = coefficients[candidates[keep]] - coefficients[references[keep]]
                else:
                    raise RelationalValidationVerificationError(f"unknown null kind: {kind}")
                row_nulls[kind].append(float(np.mean(np.abs(prediction - target_delta[keep]))))
        model_errors[source.world_seed] = np.asarray(row_model)
        for kind in null_kinds:
            null_errors[kind][source.world_seed] = np.asarray(row_nulls[kind])
        if background is not None:
            q1, q2 = background[identity]
            base_scores = np.asarray(q1, dtype=np.float64) + np.asarray(q2, dtype=np.float64)
            base_actions = _masked_argmax(base_scores, source.action_mask)
            teacher_actions = _masked_argmax(base_scores + np.asarray(source.target_surface_bits, dtype=np.float64) / float(kappa), source.action_mask)
            model_actions = _masked_argmax(base_scores + np.asarray(q, dtype=np.float64), source.action_mask)
            model_action_by_world[source.world_seed] = np.asarray(model_actions == teacher_actions, dtype=np.float64)
            pivotal_mask = teacher_actions != base_actions
            pivotal[source.world_seed] = (int(np.count_nonzero(pivotal_mask)), int(np.count_nonzero(pivotal_mask & (model_actions == teacher_actions))))
            stable_rows = teacher_actions == base_actions
            stable_total += int(np.count_nonzero(stable_rows))
            stable_correct += int(np.count_nonzero(stable_rows & (model_actions == base_actions)))
            changed_rows = model_actions != base_actions
            target_at_model = np.asarray(source.target_surface_bits)[np.arange(source.rows), model_actions]
            compatible = np.asarray(source.positive_credit_compatible)[np.arange(source.rows), model_actions]
            changed += int(np.count_nonzero(changed_rows))
            supported += int(np.count_nonzero(changed_rows & compatible & (target_at_model > 0.0)))
            positive_target_changes += int(np.count_nonzero(changed_rows & (target_at_model > 0.0)))
            for kind in null_kinds:
                null_surface = np.zeros_like(base_scores)
                if kind == "train_median":
                    null_surface[source.action_mask] = train_median
                    null_surface[np.arange(source.rows), source.reference_actions] = 0.0
                elif kind == "action_only":
                    legal_rows, legal_candidates = np.nonzero(source.action_mask)
                    null_surface[legal_rows, legal_candidates] = coefficients[legal_candidates] - coefficients[source.reference_actions[legal_rows]]
                null_actions = _masked_argmax(base_scores + null_surface, source.action_mask)
                null_action_by_world[kind][source.world_seed] = np.asarray(
                    null_actions == teacher_actions, dtype=np.float64
                )
                null_pivotal[kind][source.world_seed] = np.asarray(
                    (null_actions == teacher_actions) & pivotal_mask,
                    dtype=np.float64,
                )
    model_mae, pooled_mae, model_mae_by_world = _mae_by_world(model_errors)
    null_metrics: dict[str, object] = {}
    for kind in null_kinds:
        mae, pooled, by_world = _mae_by_world(null_errors[kind])
        null_metrics[kind] = {"mae": mae, "pooled_pair_mae": pooled, "mae_by_world": by_world}
    if background is None:
        strongest_name = None
        strongest_mae = None
        skill = None
        model_agreement = None
        agreement_by_world: dict[str, float] = {}
        null_agreement: dict[str, object] = {}
        pivotal_agreement_by_world: dict[str, float] = {}
        pivotal_rows = 0
        pivotal_agreement = None
        stable_preservation = None
        strongest_pivotal_agreement = None
    else:
        agreement_by_world = {str(world): float(np.mean(values)) for world, values in sorted(model_action_by_world.items())}
        model_agreement = float(np.mean(tuple(agreement_by_world.values())))
        pivotal_agreement_by_world = {
            str(world): (float(value[1] / value[0]) if value[0] else 0.0)
            for world, value in sorted(pivotal.items())
        }
        pivotal_rows = sum(value[0] for value in pivotal.values())
        null_agreement = {}
        for kind in null_kinds:
            by_world = {str(world): float(np.mean(values)) for world, values in sorted(null_action_by_world[kind].items())}
            pivotal_by_world = {
                str(world): (
                    float(np.count_nonzero(values) / pivotal[world][0])
                    if pivotal[world][0]
                    else 0.0
                )
                for world, values in sorted(null_pivotal[kind].items())
            }
            null_agreement[kind] = {
                "teacher_action_agreement_by_world": by_world,
                "teacher_action_agreement": float(np.mean(tuple(by_world.values()))),
                "pivotal_agreement_by_world": pivotal_by_world,
                "pivotal_agreement": (
                    float(
                        sum(int(np.count_nonzero(values)) for values in null_pivotal[kind].values())
                        / pivotal_rows
                    )
                    if pivotal_rows
                    else 0.0
                ),
            }
        strongest_name = max(
            null_kinds,
            key=lambda kind: (
                float(null_agreement[kind]["pivotal_agreement"]),
                1 if kind == "zero" else 0,
                -tuple(null_kinds).index(kind),
            ),
        )
        strongest_pivotal_agreement = float(null_agreement[strongest_name]["pivotal_agreement"])
        pivotal_total = sum(value[0] for value in pivotal.values())
        pivotal_agreement = float(sum(value[1] for value in pivotal.values()) / pivotal_total) if pivotal_total else 0.0
        skill = float(pivotal_agreement - strongest_pivotal_agreement)
        stable_preservation = float(stable_correct / stable_total) if stable_total else 0.0
        strongest_mae = float(null_metrics[strongest_name]["mae"])
    return {
        "lineage": lineage,
        "validation_worlds": sorted(model_errors),
        "validation_rows": int(sum(values.size for values in model_errors.values())),
        "validation_pairs": pair_count,
        "model_mae": model_mae,
        "model_pooled_pair_mae": pooled_mae,
        "model_mae_by_world": model_mae_by_world,
        "nulls": null_metrics,
        "strongest_null_name": strongest_name,
        "strongest_null_mae": strongest_mae,
        "strongest_null_pivotal_agreement": strongest_pivotal_agreement,
        "validation_skill": skill,
        "skill_vs_strongest_null": skill,
        "teacher_action_agreement": model_agreement,
        "teacher_action_agreement_by_world": agreement_by_world,
        "null_teacher_action_agreement": null_agreement,
        "pivotal_rows": pivotal_rows,
        "pivotal_agreement": pivotal_agreement,
        "pivotal_agreement_by_world": pivotal_agreement_by_world,
        "stable_preservation": stable_preservation,
        "background_changed_action_count": changed if background is not None else None,
        "supported_positive_change_count": supported if background is not None else None,
        "positive_target_change_count": positive_target_changes if background is not None else None,
        "positive_support_rate": float(supported / changed) if background is not None and changed else (0.0 if background is not None else None),
        "has_change_exposure": bool(changed) if background is not None else None,
        "update_count": REQUIRED_UPDATES,
    }


def _background_change_summary(
    sources: Mapping[tuple[str, int, int], RelationalZRC3Source],
    surfaces: Mapping[tuple[str, int, int], np.ndarray],
    background: Mapping[tuple[str, int, int], tuple[np.ndarray, np.ndarray]],
    *,
    lineage: int,
    source_panel_sha256: str,
    q1_checkpoint_sha256: str,
    q2_checkpoint_sha256: str,
) -> dict[str, object]:
    """Rebuild the persisted per-world action-change/support receipt.

    This is deliberately separate from ``_metrics``: the generator persists
    this receipt alongside its decision metrics, so the clean-room verifier
    must reproduce every field before accepting the report.
    """

    worlds: dict[str, dict[str, object]] = {}
    for identity, source in sorted(sources.items()):
        if identity[0] != "VALIDATION" or identity[2] != lineage:
            continue
        if identity not in surfaces or identity not in background:
            raise RelationalValidationVerificationError(
                "background action-change closure is incomplete"
            )
        q1, q2 = background[identity]
        q3 = surfaces[identity]
        expected = (source.rows, ACTION_DIM)
        if np.asarray(q1).shape != expected or np.asarray(q2).shape != expected:
            raise RelationalValidationVerificationError(
                "background action-change shape disagrees with source"
            )
        base_action = _masked_argmax(
            np.asarray(q1, dtype=np.float64) + np.asarray(q2, dtype=np.float64),
            source.action_mask,
        )
        learned_action = _masked_argmax(
            np.asarray(q1, dtype=np.float64)
            + np.asarray(q2, dtype=np.float64)
            + np.asarray(q3, dtype=np.float64),
            source.action_mask,
        )
        changed = learned_action != base_action
        rows = np.arange(source.rows, dtype=np.int64)
        target_at_learned = np.asarray(source.target_surface_bits)[rows, learned_action]
        compatible_at_learned = np.asarray(source.positive_credit_compatible)[
            rows, learned_action
        ]
        changed_count = int(np.count_nonzero(changed))
        supported_count = int(
            np.count_nonzero(changed & compatible_at_learned & (target_at_learned > 0.0))
        )
        positive_target_count = int(
            np.count_nonzero(changed & (target_at_learned > 0.0))
        )
        worlds[str(identity[1])] = {
            "rows": source.rows,
            "background_action_count": int(
                np.count_nonzero(base_action != source.reference_actions)
            ),
            "learned_action_count": int(
                np.count_nonzero(learned_action != source.reference_actions)
            ),
            "changed_action_count": changed_count,
            "supported_positive_change_count": supported_count,
            "positive_target_change_count": positive_target_count,
            "positive_support_rate": (
                float(supported_count / changed_count) if changed_count else 0.0
            ),
            "has_change_exposure": changed_count > 0,
        }
    if not worlds:
        raise RelationalValidationVerificationError(
            "background action-change closure has no validation world"
        )
    changed = sum(int(value["changed_action_count"]) for value in worlds.values())
    supported = sum(
        int(value["supported_positive_change_count"]) for value in worlds.values()
    )
    return {
        "worlds": worlds,
        "changed_action_count": changed,
        "supported_positive_change_count": supported,
        "positive_support_rate": float(supported / changed) if changed else 0.0,
        "has_change_exposure": changed > 0,
        "q1_checkpoint_sha256": q1_checkpoint_sha256,
        "q2_checkpoint_sha256": q2_checkpoint_sha256,
        "source_panel_sha256": source_panel_sha256,
    }


def _read_background(root: Path, *, seed: int, lineage: int, sources: Mapping[tuple[str, int, int], RelationalZRC3Source], config: Mapping[str, object]) -> dict[tuple[str, int, int], tuple[np.ndarray, np.ndarray]]:
    metadata = _read_json(root / BACKGROUND_METADATA_FILENAME, label="background metadata")
    receipt = _read_receipt(root / BACKGROUND_RECEIPT_FILENAME, schema=BACKGROUND_SCHEMA, fields=("schema", "metadata_sha256", "npz_sha256", "arrays_sha256", "metadata_self_sha256"))
    supplied = _digest(metadata.get("metadata_sha256"), field="background.metadata_sha256")
    if canonical_sha256({key: value for key, value in metadata.items() if key != "metadata_sha256"}) != supplied or receipt["metadata_self_sha256"] != supplied:
        raise RelationalValidationVerificationError("background metadata self-digest failed")
    if metadata.get("schema") != BACKGROUND_SCHEMA or metadata.get("schema_version") != 1 or metadata.get("initialization_seed") != seed or metadata.get("lineage") != lineage or metadata.get("source_panel_sha256") != config["source_panel_sha256"] or metadata.get("q1_checkpoint_sha256") != config["q1_map"][lineage] or metadata.get("q2_checkpoint_sha256") != config["q2_map"][lineage]:
        raise RelationalValidationVerificationError("background identity/checkpoint binding mismatch")
    representation = str(metadata.get("representation"))
    if representation not in BACKGROUND_REPRESENTATIONS:
        raise RelationalValidationVerificationError("background representation is unknown")
    if metadata.get("npz_filename") != BACKGROUND_NPZ_FILENAME or metadata.get("test_split_opened") is not False or metadata.get("episode_training") is not False or metadata.get("learner_update") is not False:
        raise RelationalValidationVerificationError("background package crosses source-only boundary")
    entries = metadata.get("arrays")
    if not isinstance(entries, list) or not entries or canonical_sha256(entries) != metadata.get("arrays_sha256"):
        raise RelationalValidationVerificationError("background array manifest is malformed")
    npz_path = root / BACKGROUND_NPZ_FILENAME
    npz_digest = _digest(metadata.get("npz_sha256"), field="background.npz_sha256")
    if _file_sha256(npz_path) != npz_digest or receipt["npz_sha256"] != npz_digest or _file_sha256(root / BACKGROUND_METADATA_FILENAME) != receipt["metadata_sha256"] or receipt["arrays_sha256"] != metadata.get("arrays_sha256"):
        raise RelationalValidationVerificationError("background file receipt mismatch")
    arrays: dict[tuple[str, int, int], tuple[np.ndarray, np.ndarray]] = {}
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            expected_keys: set[str] = set()
            for entry in entries:
                required = {"split", "world_seed", "lineage", "q1_key", "q2_key", "rows", "shape", "q1_dtype", "q2_dtype", "q1_sha256", "q2_sha256"}
                if not isinstance(entry, Mapping) or set(entry) != required:
                    raise RelationalValidationVerificationError("background array entry is malformed")
                identity = (str(entry["split"]), _positive_int(entry["world_seed"], field="background.world_seed"), _positive_int(entry["lineage"], field="background.lineage"))
                if identity in arrays or identity not in sources or identity[0] != "VALIDATION" or identity[2] != lineage:
                    raise RelationalValidationVerificationError("background array identity is unknown or wrong split")
                q1_key = str(entry["q1_key"])
                q2_key = str(entry["q2_key"])
                expected_keys.update((q1_key, q2_key))
                q1 = np.array(loaded[q1_key], copy=True)
                q2 = np.array(loaded[q2_key], copy=True)
                if q1.dtype.str != entry["q1_dtype"] or q2.dtype.str != entry["q2_dtype"] or list(q1.shape) != entry["shape"] or q2.shape != q1.shape or entry["rows"] != q1.shape[0] or _array_sha256(q1) != entry["q1_sha256"] or _array_sha256(q2) != entry["q2_sha256"] or not np.issubdtype(q1.dtype, np.floating) or not np.issubdtype(q2.dtype, np.floating) or not np.all(np.isfinite(q1)) or not np.all(np.isfinite(q2)):
                    raise RelationalValidationVerificationError("background array digest/shape/finiteness mismatch")
                if representation == BACKGROUND_REPRESENTATION_SUM_ZERO and np.any(q2 != 0.0):
                    raise RelationalValidationVerificationError(
                        "sum-with-zero background representation has a nonzero right surface"
                    )
                source = sources[identity]
                if q1.shape != (source.rows, ACTION_DIM) or q2.shape != (source.rows, ACTION_DIM):
                    raise RelationalValidationVerificationError("background shape disagrees with source")
                arrays[identity] = (q1, q2)
            if set(loaded.files) != expected_keys:
                raise RelationalValidationVerificationError("background NPZ contains unknown arrays")
    except (OSError, KeyError, ValueError, TypeError) as error:
        if isinstance(error, RelationalValidationVerificationError):
            raise
        raise RelationalValidationVerificationError("background NPZ is malformed") from error
    expected = {identity for identity in sources if identity[0] == "VALIDATION" and identity[2] == lineage}
    if set(arrays) != expected:
        raise RelationalValidationVerificationError("background package is missing a validation world")
    return arrays


def _verify_surface_artifact(root: Path, report: Mapping[str, object], all_surfaces: Mapping[tuple[int, tuple[str, int, int]], np.ndarray], source_sha256: str) -> None:
    receipt_info = report.get("validation_surfaces")
    if not isinstance(receipt_info, Mapping):
        raise RelationalValidationVerificationError("report surface receipt is missing")
    npz_path = root / str(receipt_info.get("npz", SURFACE_NPZ_FILENAME))
    metadata_path = root / str(receipt_info.get("metadata", SURFACE_METADATA_FILENAME))
    receipt_path = root / str(receipt_info.get("receipt", SURFACE_RECEIPT_FILENAME))
    metadata = _read_json(metadata_path, label="validation surface metadata")
    receipt = _read_receipt(receipt_path, schema=SURFACE_SCHEMA, fields=("schema", "metadata_sha256", "npz_sha256", "arrays_sha256", "metadata_self_sha256"))
    supplied = _digest(metadata.get("metadata_sha256"), field="surface.metadata_sha256")
    if canonical_sha256({key: value for key, value in metadata.items() if key != "metadata_sha256"}) != supplied or receipt["metadata_self_sha256"] != supplied or metadata.get("schema") != SURFACE_SCHEMA or metadata.get("source_panel_sha256") != source_sha256 or metadata.get("npz_filename") != SURFACE_NPZ_FILENAME or metadata.get("test_split_opened") is not False or metadata.get("episode_training") is not False:
        raise RelationalValidationVerificationError("validation surface metadata binding mismatch")
    if _file_sha256(npz_path) != metadata.get("npz_sha256") or receipt["npz_sha256"] != metadata.get("npz_sha256") or _file_sha256(metadata_path) != receipt["metadata_sha256"] or receipt["arrays_sha256"] != metadata.get("arrays_sha256"):
        raise RelationalValidationVerificationError("validation surface file receipt mismatch")
    entries = metadata.get("arrays")
    if not isinstance(entries, list) or canonical_sha256(entries) != metadata.get("arrays_sha256"):
        raise RelationalValidationVerificationError("validation surface manifest is malformed")
    expected_keys: dict[str, tuple[int, tuple[str, int, int]]] = {}
    for seed in sorted({seed for seed, _identity in all_surfaces}):
        identities = sorted(identity for item_seed, identity in all_surfaces if item_seed == seed)
        for index, identity in enumerate(identities):
            expected_keys[f"init_{seed}_{index:04d}"] = (seed, identity)
    if len(entries) != len(expected_keys):
        raise RelationalValidationVerificationError("validation surface closure is incomplete")
    try:
        with np.load(npz_path, allow_pickle=False) as loaded:
            keys = set()
            for entry in entries:
                if not isinstance(entry, Mapping) or set(entry) != {"key", "split", "world_seed", "lineage", "rows", "dtype", "shape", "array_sha256"} or entry.get("split") != "VALIDATION":
                    raise RelationalValidationVerificationError("validation surface entry is malformed")
                key = str(entry["key"])
                if key in keys or key not in expected_keys:
                    raise RelationalValidationVerificationError("validation surface key is unknown or duplicated")
                keys.add(key)
                value = np.array(loaded[key], copy=True)
                if value.dtype.str != entry["dtype"] or list(value.shape) != entry["shape"] or entry["rows"] != value.shape[0] or _array_sha256(value) != entry["array_sha256"] or not np.all(np.isfinite(value)):
                    raise RelationalValidationVerificationError("validation surface array digest mismatch")
                identity = ("VALIDATION", int(entry["world_seed"]), int(entry["lineage"]))
                lookup = expected_keys[key]
                if lookup[1] != identity or value.dtype != all_surfaces[lookup].dtype or value.shape != all_surfaces[lookup].shape or value.tobytes(order="C") != all_surfaces[lookup].tobytes(order="C"):
                    raise RelationalValidationVerificationError("validation surface is not bitwise-equal to raw prediction")
            if keys != set(expected_keys) or set(loaded.files) != keys:
                raise RelationalValidationVerificationError("validation surface NPZ contains unknown arrays")
    except (OSError, KeyError, ValueError, TypeError) as error:
        if isinstance(error, RelationalValidationVerificationError):
            raise
        raise RelationalValidationVerificationError("validation surface NPZ is malformed") from error


def _gate(config: Mapping[str, object], reports: Sequence[Mapping[str, object]]) -> dict[str, object]:
    gate = config["gate_config"]
    if gate is None:
        return {"evaluated": False, "passed": False, "decision": "NO_GATE_CONFIG", "reason": "gate configuration was not supplied externally", "output_unit_mode": NORMALIZED_BITS_PER_KAPPA}
    if len(reports) != EXPECTED_INITIALIZATION_COUNT:
        raise RelationalValidationVerificationError(
            f"frozen gate requires exactly {EXPECTED_INITIALIZATION_COUNT} initialization reports"
        )
    support = [report.get("positive_support_rate") for report in reports]
    skills = [report.get("validation_skill") for report in reports]
    exposures = [report.get("background_changed_action_count") for report in reports]
    supported_counts = [report.get("supported_positive_change_count") for report in reports]
    if any(value is None for value in (*support, *skills, *exposures, *supported_counts)):
        return {"evaluated": False, "passed": False, "decision": "STOP_MISSING_AUTHENTICATED_Q1_Q2_ARRAYS", "reason": "positive-support gate requires external authenticated Q1/Q2 arrays", "required_updates": REQUIRED_UPDATES, "contract_sha256": config["contract_sha256"], "output_unit_mode": NORMALIZED_BITS_PER_KAPPA}
    exposure_values = [int(value) for value in exposures]
    supported_values = [int(value) for value in supported_counts]
    if any(value < 0 for value in exposure_values) or any(
        value < 0 or value > exposure
        for value, exposure in zip(supported_values, exposure_values, strict=True)
    ):
        raise RelationalValidationVerificationError("validation support counts are inconsistent")
    support_values = [
        float(value / exposure) if exposure else 0.0
        for value, exposure in zip(supported_values, exposure_values, strict=True)
    ]
    if any(
        float(reported) != recomputed
        for reported, recomputed in zip(support, support_values, strict=True)
    ):
        raise RelationalValidationVerificationError("validation support rate disagrees with raw counts")
    skill_values = [float(value) for value in skills]
    mean_skill = float(math.fsum(skill_values) / len(skill_values))
    mean_support = float(math.fsum(support_values) / len(support_values))
    pooled_exposure = int(sum(exposure_values))
    pooled_supported = int(sum(supported_values))
    pooled_support = float(pooled_supported / pooled_exposure) if pooled_exposure else 0.0
    positive = int(sum(value > float(gate["min_mean_skill"]) for value in skill_values))
    exposed = int(sum(value > 0 for value in exposure_values))
    supported = int(sum(value > float(gate["min_supported_change_rate"]) for value in support_values))
    passed = bool(
        mean_skill > float(gate["min_mean_skill"])
        and positive >= int(gate["min_positive_initializations"])
        and pooled_exposure > 0
        and exposed >= 2
        and pooled_support > float(gate["min_supported_change_rate"])
        and supported >= int(gate["min_supported_initializations"])
    )
    return {"evaluated": True, "passed": passed, "decision": "PASS_LEARNER_GATE" if passed else "STOP_LEARNER_GATE", "reason": "all injected 100-update validation predicates passed" if passed else "one or more injected validation predicates failed", "contract_sha256": config["contract_sha256"], "output_unit_mode": NORMALIZED_BITS_PER_KAPPA, "required_updates": REQUIRED_UPDATES, "initialization_count": len(reports), "mean_validation_skill": mean_skill, "positive_initializations": positive, "exposed_initializations": exposed, "pooled_student_change_exposure": pooled_exposure, "pooled_supported_positive_changes": pooled_supported, "pooled_supported_change_rate": pooled_support, "mean_positive_support_rate_diagnostic": mean_support, "supported_initializations": supported}


def verify(output_dir: str | Path, *, config: object, contract_path: str | Path | None = None) -> dict[str, object]:
    """Verify one report against an externally supplied frozen configuration."""

    expected = _config_body(config)
    root = Path(output_dir)
    if root.is_symlink() or not root.is_dir():
        raise RelationalValidationVerificationError(f"report output is not a regular directory: {root}")
    report = _read_json(root / REPORT_FILENAME, label="validation report")
    report_digest = _digest(report.get("result_sha256"), field="report.result_sha256")
    if canonical_sha256({key: value for key, value in report.items() if key != "result_sha256"}) != report_digest:
        raise RelationalValidationVerificationError("report self-digest failed")
    if report.get("schema") != REPORT_SCHEMA or report.get("schema_version") != REPORT_VERSION or report.get("contract_sha256") != expected["contract_sha256"] or report.get("code_manifest_sha256") != expected["code_manifest_sha256"] or report.get("source_panel_sha256") != expected["source_panel_sha256"] or report.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA:
        raise RelationalValidationVerificationError("report schema/contract/source binding mismatch")
    if report.get("claim_ceiling") != "TRAIN_VALIDATION_SOURCE_ONLY_NO_TRAJECTORY_EE_OR_EFFICACY_CLAIM" or report.get("test_split_opened") is not False or report.get("episode_training") is not False or report.get("learner_update") is not False:
        raise RelationalValidationVerificationError("report crosses source-only boundary")
    seal = _read_json(root / REPORT_SEAL_FILENAME, label="report seal")
    if seal.get("schema") != f"{REPORT_SCHEMA}-seal" or seal.get("result_sha256") != report_digest or seal.get("result_file_sha256") != _file_sha256(root / REPORT_FILENAME) or seal.get("contract_sha256") != expected["contract_sha256"] or seal.get("source_panel_sha256") != expected["source_panel_sha256"] or seal.get("output_unit_mode") != NORMALIZED_BITS_PER_KAPPA or seal.get("test_split_opened") is not False or seal.get("episode_training") is not False:
        raise RelationalValidationVerificationError("report seal mismatch")
    seal_digest = _digest(seal.get("seal_sha256"), field="seal_sha256")
    if canonical_sha256({key: value for key, value in seal.items() if key != "seal_sha256"}) != seal_digest:
        raise RelationalValidationVerificationError("report seal self-digest failed")
    if contract_path is not None:
        contract = Path(contract_path)
        if contract.is_symlink() or not contract.is_file() or _file_sha256(contract) != expected["contract_sha256"] or FROZEN_STATUS not in contract.read_text(encoding="utf-8"):
            raise RelationalValidationVerificationError("contract digest/status mismatch")
    report_config = report.get("config")
    if not isinstance(report_config, Mapping) or dict(report_config) != {key: value for key, value in expected.items() if key not in {"kappa_bits", "initializations", "q1_map", "q2_map", "checkpoint_map"}}:
        raise RelationalValidationVerificationError("report config differs from external configuration")
    sources, source_entries = _load_sources(report, expected)
    records = report.get("initializations")
    if not isinstance(records, list) or len(records) != len(expected["initializations"]):
        raise RelationalValidationVerificationError("report initialization closure is incomplete")
    by_seed = {int(record.get("initialization_seed")): record for record in records if isinstance(record, Mapping)}
    if set(by_seed) != {seed for seed, _lineage in expected["initializations"]}:
        raise RelationalValidationVerificationError("report initialization set differs from external configuration")
    computed_reports: list[dict[str, object]] = []
    all_surfaces: dict[tuple[int, tuple[str, int, int]], np.ndarray] = {}
    for seed, lineage in expected["initializations"]:
        record = by_seed[seed]
        if record.get("lineage") != lineage or record.get("update_count") != REQUIRED_UPDATES or record.get("test_split_opened") is not False or record.get("episode_training") is not False:
            raise RelationalValidationVerificationError("report initialization update/identity boundary mismatch")
        output_value = record.get("prediction", {}).get("output_dir") if isinstance(record.get("prediction"), Mapping) else None
        if not isinstance(output_value, str):
            raise RelationalValidationVerificationError("report prediction output path is missing")
        init_root = Path(output_value)
        if init_root.is_symlink() or not init_root.is_dir():
            raise RelationalValidationVerificationError("learner output directory is not regular")
        result, surfaces, metadata, checkpoint_path, checkpoint_digest = _read_learner_result(init_root, seed=seed, lineage=lineage, sources=sources, config=expected)
        checkpoint = record.get("checkpoint")
        if not isinstance(checkpoint, Mapping) or checkpoint.get("sha256") != checkpoint_digest or record.get("checkpoint_sha256") != checkpoint_digest:
            raise RelationalValidationVerificationError("report checkpoint receipt mismatch")
        prediction = record.get("prediction")
        if not isinstance(prediction, Mapping) or prediction.get("source_sha256") != metadata.get("source_sha256") or prediction.get("parameter_sha256") != metadata.get("parameter_sha256") or prediction.get("npz_sha256") != metadata.get("npz_sha256") or prediction.get("arrays_sha256") != metadata.get("arrays_sha256") or prediction.get("prediction_metadata_sha256") != metadata.get("prediction_metadata_sha256"):
            raise RelationalValidationVerificationError("report prediction receipt mismatch")
        background = None
        background_record = record.get("validation", {}).get("background_action_changes") if isinstance(record.get("validation"), Mapping) else None
        # Background arrays are referenced by the optional top-level mapping.
        # Their values are loaded below by the caller-facing extension, when
        # present in the report.  A report that has a non-null background
        # metric must carry an authenticated package path.
        background_paths = report.get("background_outputs")
        if background_paths is not None:
            expected_background_seeds = {
                str(expected_seed) for expected_seed, _lineage in expected["initializations"]
            }
            if (
                not isinstance(background_paths, Mapping)
                or set(str(key) for key in background_paths) != expected_background_seeds
                or str(seed) not in background_paths
            ):
                raise RelationalValidationVerificationError("report background package mapping is incomplete")
            background = _read_background(Path(str(background_paths[str(seed)])), seed=seed, lineage=lineage, sources=sources, config=expected)
        elif background_record is not None:
            raise RelationalValidationVerificationError("report contains background metrics without authenticated package")
        metrics = _metrics(sources, surfaces, lineage=lineage, null_kinds=expected["null_kinds"], kappa=expected["kappa_bits"], background=background)
        if background is None:
            metrics["background_action_changes"] = None
        else:
            metrics["background_action_changes"] = _background_change_summary(
                sources,
                surfaces,
                background,
                lineage=lineage,
                source_panel_sha256=expected["source_panel_sha256"],
                q1_checkpoint_sha256=expected["q1_map"][lineage],
                q2_checkpoint_sha256=expected["q2_map"][lineage],
            )
        persisted = record.get("validation")
        if not isinstance(persisted, Mapping) or dict(persisted) != metrics:
            raise RelationalValidationVerificationError("validation metrics do not reproduce")
        computed_reports.append(metrics)
        for index, identity in enumerate(sorted(surfaces)):
            all_surfaces[(seed, identity)] = surfaces[identity]
    _verify_surface_artifact(root, report, all_surfaces, expected["source_panel_sha256"])
    persisted_gate = report.get("gate")
    gate = _gate(expected, computed_reports)
    if not isinstance(persisted_gate, Mapping) or dict(persisted_gate) != gate:
        raise RelationalValidationVerificationError("gate decision does not reproduce")
    return {
        "schema": f"{REPORT_SCHEMA}-verification-v1",
        "status": "VERIFIED",
        "output_unit_mode": NORMALIZED_BITS_PER_KAPPA,
        "report_sha256": report_digest,
        "gate": gate,
        "initializations_verified": len(computed_reports),
        "source_closures_verified": len(source_entries),
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def verify_result(output_dir: str | Path, *, config: object, contract_path: str | Path | None = None) -> dict[str, object]:
    """Compatibility alias for callers naming the artifact a result."""

    return verify(output_dir, config=config, contract_path=contract_path)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="canonical JSON containing the externally frozen validation config",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        help="optional frozen contract file whose digest must match --config",
    )
    arguments = parser.parse_args(argv)
    try:
        config = _read_json(arguments.config, label="external validation config")
        result = verify(
            arguments.output_dir,
            config=config,
            contract_path=arguments.contract,
        )
    except RelationalValidationVerificationError as error:
        parser.error(str(error))
    print(_canonical_bytes(result).decode("ascii"))
    return 0


__all__ = [
    "BACKGROUND_METADATA_FILENAME",
    "BACKGROUND_NPZ_FILENAME",
    "BACKGROUND_RECEIPT_FILENAME",
    "BACKGROUND_SCHEMA",
    "REPORT_FILENAME",
    "REPORT_SCHEMA",
    "REPORT_SEAL_FILENAME",
    "RelationalValidationVerificationError",
    "VerificationError",
    "canonical_sha256",
    "verify",
    "verify_result",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
