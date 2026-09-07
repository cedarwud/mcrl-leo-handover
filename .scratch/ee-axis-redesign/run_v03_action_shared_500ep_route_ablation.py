#!/usr/bin/env python3
"""Run the bounded 500-source-epoch deployment-head-drop diagnostic.

This is a TRAIN-partition exploratory matched EE screen, not the canonical
equal-budget neutral-source ablation and not Chapter 5 efficacy evidence. At
every 100 source-training epochs it evaluates FULL and three deployment-only
leave-one-head-out views of the same trained checkpoint. MAIN_REFERENCE is
reported separately as context. It never reads validation or test datasets.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_V03 = REPO / ".scratch/c2-v03"
for path in (REPO, REPO / "src", HERE, C2_V03):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

source_spec = importlib.util.spec_from_file_location(
    "e1_action_shared_sources_for_500",
    HERE / "run_v03_e1_action_shared_sources.py",
)
if source_spec is None or source_spec.loader is None:
    raise RuntimeError("cannot load source publication helpers")
sources_v2 = importlib.util.module_from_spec(source_spec)
source_spec.loader.exec_module(sources_v2)
sources = sources_v2.source

# The 500-epoch screen is downstream of the *formal* C2 expansion and V3
# validation consumer.  Keep those readers isolated from the source publisher
# so a base-only source directory cannot accidentally masquerade as the
# expanded TRAIN corpus.
expansion_spec = importlib.util.spec_from_file_location(
    "e1_action_balanced_expansion_for_500",
    HERE / "run_v03_e1_c2_train_action_balanced_expansion.py",
)
if expansion_spec is None or expansion_spec.loader is None:
    raise RuntimeError("cannot load formal C2 action-balanced expansion helpers")
expansion_v2 = importlib.util.module_from_spec(expansion_spec)
expansion_spec.loader.exec_module(expansion_v2)

import run_c2_v03_deterministic_plumbing_probe as c2_probe  # noqa: E402
import run_c2_v03_real_backend_smoke as c2_backend_smoke  # noqa: E402
import scripts.run_head_pivotality_probe as loader  # noqa: E402
from mcrl.algorithms.ee_axis_action_shared import (  # noqa: E402
    ACTION_SHARED_ALGORITHM,
    EEAxisActionSharedConfig,
    EEAxisActionSharedTrainer,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch, ROUTE_NAMES  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.keyed_fading import KeyedFadingField  # noqa: E402
from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_opening_pairs import build_opening_route_batch  # noqa: E402
from mcrl.runtime.ee_axis_state import EE_AXIS_STATE_DIM, encode_ee_axis_state  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402
from mcrl.runtime.ee_axis_temporal_pairs import build_temporal_route_batch  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import _default_code_paths  # noqa: E402


SCHEMA = (
    "multi-catfish-mcrl-v03-action-shared-500-source-epoch-"
    "deployment-head-drop-diagnostic-v2"
)
AUTHORITY_SCHEMA = f"{SCHEMA}-authority"
CHECKPOINT_SCHEMA = f"{SCHEMA}-checkpoint"
RESULT_SCHEMA = f"{SCHEMA}-result"
RESULT_SEAL_SCHEMA = f"{SCHEMA}-result-seal"
V3_VALIDATION_RESULT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-validation-v3-result-v1"
)
V3_EXECUTION_AUTHORITY_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-validation-v3-execution-authority-v1"
)
V3_EXECUTION_AUTHORITY_SEAL_SCHEMA = f"{V3_EXECUTION_AUTHORITY_SCHEMA}-seal"
V3_PREOUTCOME_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-validation-v3-preoutcome-authority-v1"
)
V3_PREOUTCOME_SEAL_SCHEMA = f"{V3_PREOUTCOME_SCHEMA}-seal"
EXPANSION_AUTHORITY_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-authority-v2"
)
EXPANSION_RESULT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-result-v1"
)
EXPANSION_RESULT_SEAL_SCHEMA = f"{EXPANSION_RESULT_SCHEMA}-seal"
FORMAL_EXPANSION_RUNNER = (
    HERE / "run_v03_e1_c2_train_action_balanced_expansion.py"
)
STABLE_VALIDATION_RUNNER = HERE / "run_v03_e1_action_shared_validation.py"
V3_VALIDATION_RUNNER = HERE / "run_v03_e1_action_shared_validation_v3.py"
SOURCE_RUNNER = HERE / "run_v03_e1_action_shared_sources.py"
DETERMINISTIC_PROBE = HERE / "run_c2_v03_deterministic_plumbing_probe.py"
C2_BACKEND_SMOKE = C2_V03 / "run_c2_v03_real_backend_smoke.py"
MAIN_PREREG = sources.BASE_PREREG
MAIN_CHECKPOINT_DIR = sources.BASE_CHECKPOINT_DIR
CLAIM_CEILING = (
    "TRAIN_PARTITION_DEPLOYMENT_HEAD_DROP_DIAGNOSTIC_NOT_CANONICAL_ABLATION_"
    "NOT_CHAPTER5_EFFICACY"
)
SOURCE_EPOCHS = 500
CHECKPOINT_EPOCHS = (100, 200, 300, 400, 500)
TRAINING_SEEDS = (2026093101, 2026093102, 2026093103)
EVALUATION_SEEDS = (2026094001, 2026094002)
POLICY_ROUTES = {
    "FULL": ("C1", "C2", "C3"),
    "DROP_C1": ("C2", "C3"),
    "DROP_C2": ("C1", "C3"),
    "DROP_C3": ("C1", "C2"),
}
MAIN_REFERENCE = "MAIN_REFERENCE"


class ActionShared500Error(RuntimeError):
    """The bounded 500-source-epoch sweep violated its sealed authority."""


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ActionShared500Error(
            f"sealed file is missing, non-regular, or a symlink: {path}"
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(payload: object) -> str:
    return sources._canonical_sha256(payload)


def _read(path: Path) -> dict[str, Any]:
    _sha256(path)
    return sources._read_canonical_json(path)


def _write_once(path: Path, payload: object) -> str:
    return sources._write_once_json(path, payload)


def _write_status(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _regular_directory(path: Path, *, label: str) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ActionShared500Error(f"{label} is not a regular directory")
    return path.resolve(strict=True)


def _read_exact(path: Path, expected_sha256: str, *, label: str) -> dict[str, Any]:
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise ActionShared500Error(f"{label} expected digest is malformed")
    if _sha256(path) != expected_sha256:
        raise ActionShared500Error(f"{label} bytes changed")
    try:
        payload = sources._read_canonical_json(path)
    except Exception as error:
        raise ActionShared500Error(f"{label} is not canonical JSON") from error
    if not isinstance(payload, dict):
        raise ActionShared500Error(f"{label} is not an object")
    return payload


def _assert_false_boundary(payload: Mapping[str, Any], *, label: str) -> None:
    for field in (
        "test_split_opened",
        "held_out_ee_evaluated",
        "validation_dataset_bytes_opened",
        "validation_metrics_computed",
        "targets_or_validation_metrics_computed",
    ):
        if field in payload and payload.get(field) is not False:
            raise ActionShared500Error(f"{label} crossed prohibited {field} boundary")


def _assert_digest(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ActionShared500Error(f"{label} is not a lowercase SHA-256 digest")
    return value


def _config(prereg: Mapping[str, Any]) -> EEAxisActionSharedConfig:
    learner = prereg.get("learner")
    if (
        not isinstance(learner, dict)
        or learner.get("algorithm") != ACTION_SHARED_ALGORITHM
        or learner.get("scorer") != "local-action-shared-8-plus-4"
    ):
        raise ActionShared500Error("source prereg is not action-shared")
    return EEAxisActionSharedConfig(
        state_dim=EE_AXIS_STATE_DIM,
        action_dim=NUM_ACTIONS,
        hidden_layers=tuple(int(value) for value in learner["hidden_layers"]),
        activation=str(learner["activation"]),
        learning_rate=float.fromhex(learner["learning_rate_hex"]),
        kappa_bits=float.fromhex(learner["kappa_bits_hex"]),
        beta=float.fromhex(learner["beta_hex"]),
        loss_weights=tuple(float.fromhex(value) for value in learner["loss_weights_hex"]),
    )


def _sealed_result(
    root: Path,
    *,
    expected_result_sha256: str,
    expected_status: str,
) -> dict[str, Any]:
    result_path = root / "result.json"
    seal = _read(root / "result-seal.json")
    result = _read(result_path)
    if (
        _sha256(result_path) != expected_result_sha256
        or seal.get("result_file_sha256") != expected_result_sha256
        or result.get("status") != expected_status
        or result.get("test_split_opened") not in {False, None}
        or result.get("held_out_ee_evaluated") not in {False, None}
    ):
        raise ActionShared500Error(f"required sealed result is not {expected_status}")
    return result


def _validate_current_code_manifest(
    manifest: object, *, label: str
) -> dict[str, str]:
    """Revalidate a producer's sealed source manifest before consuming it."""

    if not isinstance(manifest, dict) or not manifest:
        raise ActionShared500Error(f"{label} code manifest is missing")
    normalized: dict[str, str] = {}
    for relative, expected in manifest.items():
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise ActionShared500Error(f"{label} code manifest path is unsafe")
        expected_digest = _assert_digest(expected, label=f"{label}.{relative}")
        path = REPO / relative
        if _sha256(path) != expected_digest:
            raise ActionShared500Error(f"{label} code bytes changed: {relative}")
        normalized[relative] = expected_digest
    return normalized


def _authenticate_v3_go(
    *,
    validation_root: Path,
    expected_result_sha256: str,
    expected_result_seal_sha256: str,
    expected_authority_sha256: str,
    expected_authority_seal_sha256: str,
    preoutcome_authority_path: Path,
    preoutcome_authority_seal_path: Path,
    expected_preoutcome_authority_sha256: str,
    expected_preoutcome_authority_seal_sha256: str,
    expected_expansion_authority_sha256: str,
    expected_expansion_authority_seal_sha256: str,
    expected_expansion_result_sha256: str,
    expected_expansion_result_seal_sha256: str,
) -> dict[str, Any]:
    """Authenticate the final V3 GO and its pre-metric dependency chain.

    A status string alone is not authority.  This function requires the V3
    execution authority, its seal, the pre-outcome authority, and the exact
    formal C2 expansion digests to agree before the 500EP trainer can create
    even its own output directory.
    """

    root = _regular_directory(validation_root, label="V3 validation root")
    authority_path = root / "authority.json"
    authority = _read_exact(
        authority_path, expected_authority_sha256, label="V3 execution authority"
    )
    authority_seal = _read_exact(
        root / "authority-seal.json",
        expected_authority_seal_sha256,
        label="V3 execution authority seal",
    )
    result_path = root / "result.json"
    result = _read_exact(
        result_path, expected_result_sha256, label="V3 validation result"
    )
    result_seal = _read_exact(
        root / "result-seal.json",
        expected_result_seal_sha256,
        label="V3 validation result seal",
    )
    authority_sha = _assert_digest(
        authority.get("authority_sha256"), label="V3 authority_sha256"
    )
    expected_authority_sha = _assert_digest(
        expected_authority_sha256, label="expected V3 authority_sha256"
    )
    if authority_sha != expected_authority_sha:
        raise ActionShared500Error("V3 authority internal digest changed")
    preoutcome = _read_exact(
        preoutcome_authority_path,
        expected_preoutcome_authority_sha256,
        label="V3 preoutcome authority",
    )
    preoutcome_seal = _read_exact(
        preoutcome_authority_seal_path,
        expected_preoutcome_authority_seal_sha256,
        label="V3 preoutcome authority seal",
    )
    _assert_digest(
        expected_preoutcome_authority_sha256,
        label="expected V3 preoutcome authority_sha256",
    )
    _assert_digest(
        expected_preoutcome_authority_seal_sha256,
        label="expected V3 preoutcome authority seal_sha256",
    )
    if (
        authority.get("schema") != V3_EXECUTION_AUTHORITY_SCHEMA
        or authority.get("status") != "SEALED_BEFORE_ANY_VALIDATION_METRIC"
        or authority.get("claim_ceiling") != "GO_500EP_SCREEN_ONLY_NO_TEST_NO_EE"
        or authority.get("preoutcome_authority_sha256")
        != expected_preoutcome_authority_sha256
        or authority.get("preoutcome_authority_seal_sha256")
        != expected_preoutcome_authority_seal_sha256
        or authority_seal.get("schema") != V3_EXECUTION_AUTHORITY_SEAL_SCHEMA
        or authority_seal.get("authority_sha256") != authority_sha
        or authority_seal.get("authority_file_sha256")
        != _sha256(authority_path)
        or result.get("schema") != V3_VALIDATION_RESULT_SCHEMA
        or result.get("status") != "GO_500EP_SCREEN_ONLY"
        or result.get("claim_ceiling") != "GO_500EP_SCREEN_ONLY_NO_TEST_NO_EE"
        or result.get("authority_sha256") != authority_sha
        or result.get("preoutcome_authority_sha256")
        != expected_preoutcome_authority_sha256
        or result.get("source_partition_expanded") != "TRAIN"
        or result.get("expanded_route") != "C2"
        or result.get("base_validation_batches_unchanged") is not True
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result.get("test_dataset_paths_opened") != []
        or result_seal.get("schema") != f"{V3_VALIDATION_RESULT_SCHEMA}-seal"
        or result_seal.get("authority_sha256") != authority_sha
        or result_seal.get("result_file_sha256") != expected_result_sha256
    ):
        raise ActionShared500Error("V3 validation result is not an authentic final GO")
    if (
        preoutcome.get("schema") != V3_PREOUTCOME_SCHEMA
        or preoutcome.get("status")
        != "SEALED_AFTER_C2_TRAIN_EXPANSION_BEFORE_ANY_VALIDATION_METRIC"
        or preoutcome.get("claim_ceiling") != "GO_500EP_SCREEN_ONLY_NO_TEST_NO_EE"
        or preoutcome.get("expansion_authority_sha256")
        != expected_expansion_authority_sha256
        or preoutcome.get("expansion_authority_seal_sha256")
        != expected_expansion_authority_seal_sha256
        or preoutcome.get("expansion_result_sha256")
        != expected_expansion_result_sha256
        or preoutcome.get("expansion_result_seal_sha256")
        != expected_expansion_result_seal_sha256
        or preoutcome.get("validation_dataset_bytes_opened") is not False
        or preoutcome.get("test_split_opened") is not False
        or preoutcome.get("held_out_ee_evaluated") is not False
        or preoutcome_seal.get("schema") != V3_PREOUTCOME_SEAL_SCHEMA
        or preoutcome_seal.get("authority_file_sha256")
        != expected_preoutcome_authority_sha256
    ):
        raise ActionShared500Error("V3 preoutcome dependency closure is invalid")
    _validate_current_code_manifest(
        authority.get("code_manifest"), label="V3 execution authority"
    )
    gate = result.get("gate")
    if not isinstance(gate, dict) or gate.get("status") != "GO_500EP_SCREEN_ONLY":
        raise ActionShared500Error("V3 result gate is not final GO")
    return {
        "authority": authority,
        "authority_seal": authority_seal,
        "result": result,
        "result_seal": result_seal,
        "preoutcome": preoutcome,
        "preoutcome_seal": preoutcome_seal,
        "authority_sha256": expected_authority_sha256,
        "authority_seal_sha256": expected_authority_seal_sha256,
        "result_sha256": expected_result_sha256,
        "result_seal_sha256": expected_result_seal_sha256,
        "preoutcome_authority_sha256": expected_preoutcome_authority_sha256,
        "preoutcome_authority_seal_sha256": expected_preoutcome_authority_seal_sha256,
    }


def _load_formal_expanded_c2(
    *,
    expansion_root: Path,
    expected_authority_sha256: str,
    expected_authority_seal_sha256: str,
    expected_result_sha256: str,
    expected_result_seal_sha256: str,
    source_access: Mapping[str, Any],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Load only the authenticated formal C2 TRAIN datasets."""

    root = _regular_directory(expansion_root, label="formal C2 expansion root")
    authority_path = root / "authority.json"
    authority = _read_exact(
        authority_path, expected_authority_sha256, label="formal C2 authority"
    )
    authority_seal = _read_exact(
        root / "authority-seal.json",
        expected_authority_seal_sha256,
        label="formal C2 authority seal",
    )
    result_path = root / "result.json"
    result = _read_exact(
        result_path, expected_result_sha256, label="formal C2 result"
    )
    result_seal = _read_exact(
        root / "result-seal.json",
        expected_result_seal_sha256,
        label="formal C2 result seal",
    )
    authority_sha = _assert_digest(
        expected_authority_sha256, label="formal C2 authority_sha256"
    )
    if (
        authority.get("schema") != EXPANSION_AUTHORITY_SCHEMA
        or authority.get("status") != "SEALED_BEFORE_SCHEDULE_TOPOLOGY_INSPECTION"
        or authority_seal.get("schema") != f"{EXPANSION_AUTHORITY_SCHEMA}-seal"
        or authority_seal.get("authority_sha256") != authority_sha
        or result.get("schema") != EXPANSION_RESULT_SCHEMA
        or result.get("status") != "PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION"
        or result.get("completion_status") != result.get("status")
        or result.get("authority_sha256") != authority_sha
        or result_seal.get("schema") != EXPANSION_RESULT_SEAL_SCHEMA
        or result_seal.get("authority_sha256") != authority_sha
        or result_seal.get("result_file_sha256") != expected_result_sha256
    ):
        raise ActionShared500Error("formal C2 expansion is not an authentic final PASS")
    _assert_false_boundary(authority, label="formal C2 authority")
    _assert_false_boundary(result, label="formal C2 result")
    if (
        authority.get("source_prereg_sha256") != source_access["source_prereg_sha256"]
        or authority.get("source_manifest_sha256")
        != source_access["source_manifest_sha256"]
        or authority.get("checkpoint_sha256") != source_access["checkpoint_sha256"]
        or result.get("source_prereg_sha256") != source_access["source_prereg_sha256"]
        or result.get("source_manifest_sha256")
        != source_access["source_manifest_sha256"]
        or result.get("checkpoint_sha256") != source_access["checkpoint_sha256"]
        or result.get("source_partition") != "TRAIN"
        or result.get("held_out") is not False
        or result.get("replacement_seed_pool_used") is not False
        or result.get("second_seed_pool_used") is not False
        or result.get("validation_dataset_bytes_opened") is not False
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result.get("targets_or_validation_metrics_computed") is not False
    ):
        raise ActionShared500Error("formal C2 expansion lineage or partition changed")
    implementation = authority.get("implementation_file_sha256s")
    _validate_current_code_manifest(implementation, label="formal C2 expansion")
    selected = result.get("selected_seed_order")
    candidate_order = list(expansion_v2.CANDIDATE_SEED_ORDER)
    if (
        not isinstance(selected, list)
        or not selected
        or any(type(seed) is not int for seed in selected)
        or len(set(selected)) != len(selected)
        or selected != candidate_order[: len(selected)]
    ):
        raise ActionShared500Error("formal C2 selected seed prefix is invalid")
    selected_keys = {str(seed) for seed in selected}
    paths = result.get("temporal_dataset_paths")
    files = result.get("temporal_dataset_file_sha256s")
    datasets = result.get("temporal_datasets")
    dataset_digests = result.get("temporal_dataset_sha256s")
    schedules = result.get("selected_schedule_file_sha256s")
    if not all(isinstance(value, dict) for value in (paths, files, datasets, dataset_digests, schedules)):
        raise ActionShared500Error("formal C2 dataset metadata is malformed")
    if any(set(value) != selected_keys for value in (paths, files, datasets, dataset_digests, schedules)):
        raise ActionShared500Error("formal C2 dataset metadata keys are incomplete")
    graph = result.get("final_c2_graph_report")
    if (
        not isinstance(graph, dict)
        or graph.get("coverage_sufficient") is not True
        or graph.get("remaining_unsupported_validation_action_pairs") != []
        or graph.get("target_or_outcome_values_used_for_coverage_decision") is not False
        or graph.get("generated_outcomes_materialized") is not True
    ):
        raise ActionShared500Error("formal C2 final graph is not a complete TRAIN pass")
    rows: list[Any] = []
    access: dict[str, Any] = {
        "authority_sha256": authority_sha,
        "authority_seal_sha256": expected_authority_seal_sha256,
        "result_sha256": expected_result_sha256,
        "result_seal_sha256": expected_result_seal_sha256,
        "selected_seed_order": list(selected),
        "temporal_datasets": {},
        "final_c2_graph_report": graph,
        "source_partition": "TRAIN",
        "held_out": False,
    }
    for seed in selected:
        key = str(seed)
        expected_name = f"temporal-datasets/c2-train-{seed}.json"
        relative = paths.get(key)
        if relative != expected_name:
            raise ActionShared500Error("formal C2 temporal dataset path changed")
        path = root / expected_name
        temporal_root = (root / "temporal-datasets").resolve(strict=True)
        if path.resolve(strict=True).parent != temporal_root:
            raise ActionShared500Error("formal C2 temporal dataset escapes root")
        file_sha = _assert_digest(files.get(key), label=f"formal C2 file {key}")
        if _sha256(path) != file_sha:
            raise ActionShared500Error("formal C2 temporal dataset bytes changed")
        dataset = read_temporal_dataset(path)
        dataset_sha = _assert_digest(
            dataset_digests.get(key), label=f"formal C2 dataset {key}"
        )
        if (
            dataset.verify() != dataset_sha
            or dataset.source_manifest_sha256 != source_access["source_manifest_sha256"]
            or dataset.checkpoint_sha256 != source_access["checkpoint_sha256"]
            or any(int(row.seed) != seed for row in dataset.rows)
            or not dataset.rows
        ):
            raise ActionShared500Error("formal C2 temporal dataset lineage changed")
        metadata = datasets.get(key)
        if (
            not isinstance(metadata, dict)
            or metadata.get("path") != expected_name
            or metadata.get("file_sha256") != file_sha
            or metadata.get("dataset_sha256") != dataset_sha
            or metadata.get("source_partition") != "TRAIN"
            or metadata.get("held_out") is not False
        ):
            raise ActionShared500Error("formal C2 temporal dataset metadata changed")
        rows.extend(dataset.rows)
        access["temporal_datasets"][key] = {
            "path": expected_name,
            "file_sha256": file_sha,
            "dataset_sha256": dataset_sha,
            "rows": len(dataset.rows),
        }
    if not rows:
        raise ActionShared500Error("formal expanded C2 TRAIN source is empty")
    return tuple(rows), access


def _load_train_batches(
    *,
    source_root: Path,
    independent_verification: Mapping[str, Any],
    expansion_root: Path,
    expected_expansion_authority_sha256: str,
    expected_expansion_authority_seal_sha256: str,
    expected_expansion_result_sha256: str,
    expected_expansion_result_seal_sha256: str,
) -> tuple[EEAxisActionSharedConfig, dict[str, EEAxisPairBatch], dict[str, Any]]:
    source_root = _regular_directory(source_root, label="base action-shared source root")
    prereg = _read(source_root / "prereg.json")
    prereg_body = dict(prereg)
    supplied_prereg = prereg_body.pop("prereg_sha256", None)
    if supplied_prereg != _canonical_sha256(prereg_body):
        raise ActionShared500Error("source prereg digest changed")
    manifest_path = source_root / "source-manifest.json"
    manifest = _read(manifest_path)
    manifest_body = dict(manifest)
    supplied_manifest = manifest_body.pop("source_manifest_sha256", None)
    if (
        supplied_manifest != _canonical_sha256(manifest_body)
        or prereg.get("source_manifest_sha256") != supplied_manifest
    ):
        raise ActionShared500Error("source manifest digest changed")
    config = _config(prereg)
    data_root = source_root / "source-data"
    receipt_path = data_root / "receipt.json"
    receipt = _read(receipt_path)
    if (
        _sha256(receipt_path)
        != independent_verification.get("source_receipt_file_sha256")
        or receipt.get("status") != "PASS"
    ):
        raise ActionShared500Error("source receipt is not independently authenticated")
    index_path = data_root / "ladder-index.json"
    index = _read(index_path)
    if (
        _sha256(index_path) != receipt.get("ladder_index_file_sha256")
        or index.get("test_split_opened") is not False
    ):
        raise ActionShared500Error("source ladder index changed")
    seed_split = {
        int(seed): split_name for seed, split_name in prereg["source_seed_split"].items()
    }
    train_seeds = {seed for seed, split_name in seed_split.items() if split_name == "train"}
    if len(train_seeds) != 4 or any(split_name == "test" for split_name in seed_split.values()):
        raise ActionShared500Error("500EP requires the independently verified 4/3/0 source")
    datasets = index.get("datasets")
    if not isinstance(datasets, dict):
        raise ActionShared500Error("source dataset index is malformed")
    opening_c1: list[Any] = []
    opening_c3: list[Any] = []
    temporal_c2: list[Any] = []
    opened_paths: list[str] = []
    for seed in sorted(train_seeds):
        entry = datasets.get(str(seed))
        if not isinstance(entry, dict):
            raise ActionShared500Error("train dataset index row is missing")
        opening_path = data_root / f"opening-{seed}.json"
        temporal_path = data_root / f"temporal-{seed}.json"
        if (
            entry.get("opening_path") != opening_path.name
            or entry.get("temporal_path") != temporal_path.name
            or opening_path.is_symlink()
            or temporal_path.is_symlink()
            or _sha256(opening_path) != receipt["opening_dataset_file_sha256s"][str(seed)]
            or _sha256(temporal_path) != receipt["temporal_dataset_file_sha256s"][str(seed)]
        ):
            raise ActionShared500Error("train dataset path or bytes changed")
        opening = read_opening_dataset(opening_path)
        temporal = read_temporal_dataset(temporal_path)
        if (
            opening.verify() != entry["opening_dataset_sha256"]
            or temporal.verify() != entry["temporal_dataset_sha256"]
            or opening.source_manifest_sha256 != prereg["source_manifest_sha256"]
            or temporal.source_manifest_sha256 != prereg["source_manifest_sha256"]
            or opening.checkpoint_sha256 != prereg["checkpoint_sha256"]
            or temporal.checkpoint_sha256 != prereg["checkpoint_sha256"]
        ):
            raise ActionShared500Error("train dataset lineage changed")
        opening_c1.extend(opening.c1_pairs)
        opening_c3.extend(opening.c3_pairs)
        temporal_c2.extend(temporal.rows)
        opened_paths.extend((opening_path.name, temporal_path.name))
    expanded_c2, expanded_access = _load_formal_expanded_c2(
        expansion_root=expansion_root,
        expected_authority_sha256=expected_expansion_authority_sha256,
        expected_authority_seal_sha256=expected_expansion_authority_seal_sha256,
        expected_result_sha256=expected_expansion_result_sha256,
        expected_result_seal_sha256=expected_expansion_result_seal_sha256,
        source_access={
            "source_prereg_sha256": prereg["prereg_sha256"],
            "source_manifest_sha256": prereg["source_manifest_sha256"],
            "checkpoint_sha256": prereg["checkpoint_sha256"],
        },
    )
    temporal_c2.extend(expanded_c2)
    batches = {
        "C1": build_opening_route_batch(opening_c1).pair_batch,
        "C2": build_temporal_route_batch(temporal_c2).pair_batch,
        "C3": build_opening_route_batch(opening_c3).pair_batch,
    }
    for batch in batches.values():
        batch.validate(state_dim=config.state_dim, action_dim=config.action_dim)
    return config, batches, {
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "checkpoint_sha256": prereg["checkpoint_sha256"],
        "environment_source_sha256": prereg.get("environment_source_sha256"),
        "reward_source_sha256": prereg.get("reward_source_sha256"),
        "base_prereg_file_sha256": _sha256(MAIN_PREREG),
        "base_source_manifest_file_sha256": _sha256(manifest_path),
        "opened_train_dataset_paths": opened_paths,
        "opened_validation_dataset_paths": [],
        "opened_test_dataset_paths": [],
        "expanded_c2": expanded_access,
        "expanded_c2_rows": len(expanded_c2),
    }


def _active_actions(
    trainer: EEAxisActionSharedTrainer,
    states: np.ndarray,
    masks: np.ndarray,
    active_routes: tuple[str, ...],
) -> np.ndarray:
    if not active_routes or any(route not in ROUTE_NAMES for route in active_routes):
        raise ActionShared500Error("active route set is invalid")
    surfaces = trainer.q_values(states)
    if (
        not isinstance(surfaces, tuple)
        or len(surfaces) != len(ROUTE_NAMES)
        or any(
            np.asarray(surface).ndim != 2
            or np.asarray(surface).shape[0] != np.asarray(states).shape[0]
            or not np.all(np.isfinite(np.asarray(surface)))
            for surface in surfaces
        )
    ):
        raise ActionShared500Error("action-shared Q surfaces are malformed or non-finite")
    scores = np.zeros_like(surfaces[0])
    for route in active_routes:
        scores += surfaces[ROUTE_NAMES.index(route)]
    valid = np.asarray(masks)
    if valid.dtype != np.bool_ or valid.shape != scores.shape:
        raise ActionShared500Error("deployment masks do not match action-shared scores")
    actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(valid, axis=1)
    actions[eligible] = np.argmax(
        np.where(valid[eligible], scores[eligible], -np.inf), axis=1
    )
    return actions


def _catfish_episode(
    trainer: EEAxisActionSharedTrainer,
    archive: Any,
    *,
    active_routes: tuple[str, ...],
    label: str,
    epoch: int,
    initialization_seed: int,
    evaluation_seed: int,
    checkpoint_sha256: str,
) -> dict[str, Any]:
    wrapped = loader._make_environment(archive, users=100)
    field = KeyedFadingField.from_components(
        "multi-catfish-v03-action-shared-500ep-matched-evaluation-v1",
        checkpoint_sha256,
        evaluation_seed,
    )
    wrapped.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
        evaluation_seed
    )
    _states, _masks, observation = wrapped.reset(env_rng, mobility_rng)
    interval_s = float(wrapped.environment.driver.config.ephemeris.time_step_s)
    bits = 0.0
    energy = 0.0
    served = 0
    steps = 0
    action_trace: list[list[int]] = []
    while True:
        encoded = encode_ee_axis_state(wrapped.environment, observation)
        actions = _active_actions(
            trainer,
            encoded.state_matrix,
            encoded.action_masks,
            active_routes,
        )
        action_trace.append([int(value) for value in actions.tolist()])
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        if (
            rates.shape != (100,)
            or not np.all(np.isfinite(rates))
            or np.any(rates < 0.0)
            or not math.isfinite(power)
            or power < 0.0
        ):
            raise ActionShared500Error("Catfish evaluation produced malformed physics")
        bits += float(math.fsum(float(value) for value in rates)) * interval_s
        energy += power * interval_s
        served += int(outcome.resolution.served_count)
        steps += 1
        if result.done:
            break
        observation = outcome.observation
    decisions = steps * 100
    return {
        "policy": label,
        "active_routes": list(active_routes),
        "source_epoch": epoch,
        "initialization_seed": initialization_seed,
        "evaluation_seed": evaluation_seed,
        "fading_field_sha256": field.root_digest,
        "steps": steps,
        "decision_count": decisions,
        "served_user_steps": served,
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy if energy else 0.0,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
        "action_trace": action_trace,
        "action_trace_sha256": _canonical_sha256(action_trace),
    }


def _m0_episode(
    trainer: Any,
    archive: Any,
    *,
    evaluation_seed: int,
    checkpoint_sha256: str,
) -> dict[str, Any]:
    wrapped = loader._make_environment(archive, users=100)
    field = KeyedFadingField.from_components(
        "multi-catfish-v03-action-shared-500ep-matched-evaluation-v1",
        checkpoint_sha256,
        evaluation_seed,
    )
    wrapped.environment._fading_field = field
    env_rng, mobility_rng, _action_rng, _control_rng = loader._evaluation_rngs(
        evaluation_seed
    )
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    interval_s = float(wrapped.environment.driver.config.ephemeris.time_step_s)
    bits = 0.0
    energy = 0.0
    served = 0
    steps = 0
    trace: list[list[int]] = []
    while True:
        actions, _physical = c2_backend_smoke._main_decision(
            trainer, wrapped, states, masks, observation, env_rng
        )
        actions = np.asarray(actions, dtype=np.int64)
        trace.append([int(value) for value in actions.tolist()])
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
        power = float(outcome.system_power_w)
        if (
            rates.shape != (100,)
            or not np.all(np.isfinite(rates))
            or np.any(rates < 0.0)
            or not math.isfinite(power)
            or power < 0.0
        ):
            raise ActionShared500Error("M0 evaluation produced malformed physics")
        bits += float(math.fsum(float(value) for value in rates)) * interval_s
        energy += power * interval_s
        served += int(outcome.resolution.served_count)
        steps += 1
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        observation = outcome.observation
    decisions = steps * 100
    return {
        "policy": MAIN_REFERENCE,
        "source_epoch": 0,
        "initialization_seed": None,
        "evaluation_seed": evaluation_seed,
        "fading_field_sha256": field.root_digest,
        "steps": steps,
        "decision_count": decisions,
        "served_user_steps": served,
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy if energy else 0.0,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
        "action_trace": trace,
        "action_trace_sha256": _canonical_sha256(trace),
    }


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    if not rows:
        raise ActionShared500Error("cannot aggregate an empty EE arm")
    bits = float(math.fsum(float(row["total_bits"]) for row in rows))
    energy = float(math.fsum(float(row["total_energy_j"]) for row in rows))
    decisions = int(sum(int(row["decision_count"]) for row in rows))
    served = int(sum(int(row["served_user_steps"]) for row in rows))
    if (
        not math.isfinite(bits)
        or not math.isfinite(energy)
        or energy <= 0.0
        or decisions <= 0
        or served < 0
        or served > decisions
    ):
        raise ActionShared500Error("EE arm aggregate is non-physical")
    return {
        "runs": len(rows),
        "pooled_ratio_of_sums_ee_bits_per_j": bits / energy,
        "mean_run_ee_bits_per_j": float(
            np.mean([float(row["ratio_of_sums_ee_bits_per_j"]) for row in rows])
        ),
        "total_bits": bits,
        "total_energy_j": energy,
        "served_fraction": served / decisions,
        "outage_fraction": 1.0 - served / decisions,
    }


def _save_checkpoint(
    path: Path,
    *,
    authority_sha256: str,
    source_epoch: int,
    trainer: EEAxisActionSharedTrainer,
) -> str:
    if path.exists() or path.is_symlink():
        raise ActionShared500Error("refusing to overwrite 500EP checkpoint")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        torch.save(
            {
                "schema": CHECKPOINT_SCHEMA,
                "authority_sha256": authority_sha256,
                "source_epoch": source_epoch,
                "training_seed": trainer.train_seed,
                "trainer": trainer.checkpoint_state(update_count=source_epoch * 3),
            },
            temporary,
        )
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return _sha256(path)


def _load_checkpoint_for_evaluation(
    path: Path,
    *,
    expected_file_sha256: str,
    authority_sha256: str,
    source_epoch: int,
    training_seed: int,
    config: EEAxisActionSharedConfig,
) -> EEAxisActionSharedTrainer:
    if path.is_symlink() or not path.is_file() or _sha256(path) != expected_file_sha256:
        raise ActionShared500Error("500EP learner checkpoint bytes changed")
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("schema") != CHECKPOINT_SCHEMA
        or checkpoint.get("authority_sha256") != authority_sha256
        or checkpoint.get("source_epoch") != source_epoch
        or checkpoint.get("training_seed") != training_seed
    ):
        raise ActionShared500Error("500EP learner checkpoint identity changed")
    trainer = EEAxisActionSharedTrainer(config, train_seed=training_seed, device="cpu")
    if trainer.load_checkpoint_state(checkpoint.get("trainer")) != source_epoch * 3:
        raise ActionShared500Error("500EP learner checkpoint update count changed")
    return trainer


def _paired_differences(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[int, int, int], dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        key = (
            int(row["source_epoch"]),
            int(row["initialization_seed"]),
            int(row["evaluation_seed"]),
        )
        label = str(row["policy"])
        if label not in POLICY_ROUTES or label in by_key.setdefault(key, {}):
            raise ActionShared500Error("paired diagnostic has an unknown or duplicate view")
        by_key[key][label] = row
    result: list[dict[str, Any]] = []
    expected = set(POLICY_ROUTES)
    for key, views in sorted(by_key.items()):
        if set(views) != expected:
            raise ActionShared500Error("paired diagnostic is missing a deployment view")
        full = views["FULL"]
        full_trace = full.get("action_trace")
        if not isinstance(full_trace, list):
            raise ActionShared500Error("FULL action trace is absent")
        for dropped in ("DROP_C1", "DROP_C2", "DROP_C3"):
            other = views[dropped]
            if (
                other.get("fading_field_sha256") != full.get("fading_field_sha256")
                or other.get("steps") != full.get("steps")
                or other.get("decision_count") != full.get("decision_count")
            ):
                raise ActionShared500Error("paired diagnostic common randomness changed")
            other_trace = other.get("action_trace")
            if (
                not isinstance(other_trace, list)
                or len(other_trace) != len(full_trace)
                or any(len(a) != len(b) for a, b in zip(full_trace, other_trace, strict=True))
            ):
                raise ActionShared500Error("paired diagnostic action traces do not align")
            mismatch_by_step = [
                sum(int(left != right) for left, right in zip(a, b, strict=True))
                for a, b in zip(full_trace, other_trace, strict=True)
            ]
            mismatch = sum(mismatch_by_step)
            decisions = int(full["decision_count"])
            result.append(
                {
                    "source_epoch": key[0],
                    "initialization_seed": key[1],
                    "evaluation_seed": key[2],
                    "contrast": f"FULL_minus_{dropped}",
                    "fading_field_sha256": full["fading_field_sha256"],
                    "ee_difference_bits_per_j": float(
                        full["ratio_of_sums_ee_bits_per_j"]
                    )
                    - float(other["ratio_of_sums_ee_bits_per_j"]),
                    "total_bits_difference": float(full["total_bits"])
                    - float(other["total_bits"]),
                    "total_energy_difference_j": float(full["total_energy_j"])
                    - float(other["total_energy_j"]),
                    "served_user_step_difference": int(full["served_user_steps"])
                    - int(other["served_user_steps"]),
                    "served_fraction_difference": float(full["served_fraction"])
                    - float(other["served_fraction"]),
                    "outage_fraction_difference": float(full["outage_fraction"])
                    - float(other["outage_fraction"]),
                    "action_mismatch_count": mismatch,
                    "action_mismatch_fraction": mismatch / decisions,
                    "action_mismatch_count_by_step": mismatch_by_step,
                }
            )
    return result


def run(
    *,
    source_root: Path,
    independent_verification_root: Path,
    validation_root: Path,
    output_dir: Path,
    tle_root: Path,
    expected_independent_result_sha256: str,
    expected_validation_result_sha256: str,
    expansion_root: Path | None = None,
    expected_expansion_authority_sha256: str | None = None,
    expected_expansion_authority_seal_sha256: str | None = None,
    expected_expansion_result_sha256: str | None = None,
    expected_expansion_result_seal_sha256: str | None = None,
) -> dict[str, Any]:
    # This runner must remain fail-closed while the one-time masked mean/max
    # fallback is under evaluation.  In particular, the historical CLI shape
    # must not silently fall back to the base-only 4/3/0 TRAIN source.
    expansion_arguments = (
        expansion_root,
        expected_expansion_authority_sha256,
        expected_expansion_authority_seal_sha256,
        expected_expansion_result_sha256,
        expected_expansion_result_seal_sha256,
    )
    if any(value is None for value in expansion_arguments):
        raise ActionShared500Error(
            "500EP is fail-closed: formal expanded C2 TRAIN and authenticated "
            "V3 GO digests are required before launch"
        )
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite 500EP route ablation")
    independent = _sealed_result(
        independent_verification_root,
        expected_result_sha256=expected_independent_result_sha256,
        expected_status="PASS_INDEPENDENT_4_3_0_NO_TEST",
    )
    validation = _sealed_result(
        validation_root,
        expected_result_sha256=expected_validation_result_sha256,
        expected_status="GO_500EP_SCREEN_ONLY",
    )
    config, batches, source_access = _load_train_batches(
        source_root=source_root,
        independent_verification=independent,
    )
    if any(seed in set(sources_v2.SOURCE_SEED_SPLIT) for seed in (*TRAINING_SEEDS, *EVALUATION_SEEDS)):
        raise ActionShared500Error("training/evaluation seeds overlap source seeds")
    code_paths = tuple(_default_code_paths()) + (Path(__file__),)
    code_manifest = {
        str(path.resolve().relative_to(REPO.resolve())): _sha256(path)
        for path in sorted(set(code_paths), key=lambda item: str(item))
    }
    authority = {
        "schema": AUTHORITY_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "source_epochs": SOURCE_EPOCHS,
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "checkpoint_every_source_epochs": 100,
        "training_seeds": list(TRAINING_SEEDS),
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "policy_routes": {label: list(routes) for label, routes in POLICY_ROUTES.items()},
        "diagnostic_semantics": (
            "same-fully-trained-checkpoint-leave-one-head-out-at-deployment;"
            "not-equal-budget-neutral-source-ablation"
        ),
        "main_reference_label": MAIN_REFERENCE,
        "config": asdict(config),
        "source_access": source_access,
        "independent_source_result_sha256": expected_independent_result_sha256,
        "validation_result_sha256": expected_validation_result_sha256,
        "code_manifest": code_manifest,
        "source_data_partition": "train",
        "ephemeris_evaluation_partition": "TRAIN",
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    authority["authority_sha256"] = _canonical_sha256(authority)
    output_dir.mkdir(parents=True)
    checkpoints = output_dir / "checkpoints"
    checkpoints.mkdir()
    _write_once(output_dir / "authority.json", authority)
    _write_status(
        output_dir / "status.json",
        {
            "schema": SCHEMA,
            "status": "running",
            "source_epoch_completed": 0,
            "authority_sha256": authority["authority_sha256"],
        },
    )

    base_record = read_prereg(REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="mcrl-v03-action-shared-500-eval-") as temporary:
        archive = c2_probe._frozen_archive(
            base_record,
            tle_root,
            Path(temporary) / "frozen-tle",
        )
        main, checkpoint = loader._verify_and_load_trainer(
            base_record,
            archive,
            run_dir=REPO / "artifacts/training-2026-08-25-rerun01/main",
            users=100,
        )
        checkpoint_sha256 = str(checkpoint["checkpoint_sha256"])
        if checkpoint_sha256 != source_access["checkpoint_sha256"]:
            raise ActionShared500Error("M0 and Catfish source checkpoint disagree")
        main_before = c2_backend_smoke._network_snapshot(main)
        m0_rows = [
            _m0_episode(
                main,
                archive,
                evaluation_seed=seed,
                checkpoint_sha256=checkpoint_sha256,
            )
            for seed in EVALUATION_SEEDS
        ]
        trainers = {
            seed: EEAxisActionSharedTrainer(config, train_seed=seed, device="cpu")
            for seed in TRAINING_SEEDS
        }
        checkpoint_digests: dict[str, str] = {}
        evaluation_rows: list[dict[str, Any]] = []
        sweep: dict[str, Any] = {}
        last_losses: dict[str, Any] = {}
        for epoch in range(1, SOURCE_EPOCHS + 1):
            for seed, trainer in trainers.items():
                last_losses[str(seed)] = {
                    route: trainer.update_route(route, batches[route])
                    for route in ROUTE_NAMES
                }
            if epoch not in CHECKPOINT_EPOCHS:
                if epoch % 10 == 0:
                    _write_status(
                        output_dir / "status.json",
                        {
                            "schema": SCHEMA,
                            "status": "running",
                            "source_epoch_completed": epoch,
                            "last_losses": last_losses,
                            "authority_sha256": authority["authority_sha256"],
                            "elapsed_s": time.perf_counter() - started,
                        },
                    )
                continue
            for seed, trainer in trainers.items():
                filename = f"init-{seed}-source-epoch-{epoch:06d}.pt"
                checkpoint_path = checkpoints / filename
                checkpoint_digests[filename] = _save_checkpoint(
                    checkpoint_path,
                    authority_sha256=authority["authority_sha256"],
                    source_epoch=epoch,
                    trainer=trainer,
                )
                evaluation_trainer = _load_checkpoint_for_evaluation(
                    checkpoint_path,
                    expected_file_sha256=checkpoint_digests[filename],
                    authority_sha256=authority["authority_sha256"],
                    source_epoch=epoch,
                    training_seed=seed,
                    config=config,
                )
                for label, active_routes in POLICY_ROUTES.items():
                    for evaluation_seed in EVALUATION_SEEDS:
                        evaluation_rows.append(
                            _catfish_episode(
                                evaluation_trainer,
                                archive,
                                active_routes=active_routes,
                                label=label,
                                epoch=epoch,
                                initialization_seed=seed,
                                evaluation_seed=evaluation_seed,
                                checkpoint_sha256=checkpoint_sha256,
                            )
                        )
            epoch_rows = [
                row for row in evaluation_rows if int(row["source_epoch"]) == epoch
            ]
            aggregates = {
                label: _aggregate([row for row in epoch_rows if row["policy"] == label])
                for label in POLICY_ROUTES
            }
            aggregates[MAIN_REFERENCE] = _aggregate(m0_rows)
            ee = {
                label: float(values["pooled_ratio_of_sums_ee_bits_per_j"])
                for label, values in aggregates.items()
            }
            sweep[str(epoch)] = {
                "aggregate": aggregates,
                "ee_contrasts_bits_per_j": {
                    "FULL_minus_MAIN_REFERENCE": ee["FULL"] - ee[MAIN_REFERENCE],
                    "C1_FULL_minus_DROP_C1": ee["FULL"] - ee["DROP_C1"],
                    "C2_FULL_minus_DROP_C2": ee["FULL"] - ee["DROP_C2"],
                    "C3_FULL_minus_DROP_C3": ee["FULL"] - ee["DROP_C3"],
                },
            }
            _write_status(
                output_dir / "status.json",
                {
                    "schema": SCHEMA,
                    "status": "running",
                    "source_epoch_completed": epoch,
                    "last_losses": last_losses,
                    "sweep": sweep,
                    "checkpoint_file_sha256s": checkpoint_digests,
                    "authority_sha256": authority["authority_sha256"],
                    "elapsed_s": time.perf_counter() - started,
                },
            )
        if not c2_backend_smoke._networks_equal(main, main_before):
            raise ActionShared500Error("matched evaluation mutated M0 networks")

    result = {
        "schema": RESULT_SCHEMA,
        "status": (
            "COMPLETE_500_SOURCE_EPOCH_TRAIN_PARTITION_"
            "DEPLOYMENT_HEAD_DROP_DIAGNOSTIC"
        ),
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": authority["authority_sha256"],
        "source_epochs": SOURCE_EPOCHS,
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "sweep": sweep,
        "m0_rows": m0_rows,
        "catfish_evaluation_rows": evaluation_rows,
        "paired_deployment_head_drop_differences": _paired_differences(
            evaluation_rows
        ),
        "checkpoint_file_sha256s": checkpoint_digests,
        "elapsed_s": time.perf_counter() - started,
        "source_data_partition": "train",
        "ephemeris_evaluation_partition": "TRAIN",
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    if {
        str(path.resolve().relative_to(REPO.resolve())): _sha256(path)
        for path in sorted(set(code_paths), key=lambda item: str(item))
    } != code_manifest:
        raise ActionShared500Error("500EP code changed during execution")
    result_sha256 = _write_once(output_dir / "result.json", result)
    seal_sha256 = _write_once(
        output_dir / "result-seal.json",
        {
            "schema": RESULT_SEAL_SCHEMA,
            "authority_sha256": authority["authority_sha256"],
            "result_file_sha256": result_sha256,
        },
    )
    _write_status(
        output_dir / "status.json",
        {
            "schema": SCHEMA,
            "status": "complete",
            "source_epoch_completed": SOURCE_EPOCHS,
            "authority_sha256": authority["authority_sha256"],
            "result_file_sha256": result_sha256,
            "result_seal_file_sha256": seal_sha256,
            "elapsed_s": time.perf_counter() - started,
        },
    )
    return {
        **result,
        "result_file_sha256": result_sha256,
        "result_seal_file_sha256": seal_sha256,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--independent-source-verification-root", type=Path, required=True)
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-independent-result-sha256", required=True)
    parser.add_argument("--expected-validation-result-sha256", required=True)
    parser.add_argument("--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser())
    args = parser.parse_args(argv)
    payload = run(
        source_root=args.source_root,
        independent_verification_root=args.independent_source_verification_root,
        validation_root=args.validation_root,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
        expected_independent_result_sha256=args.expected_independent_result_sha256,
        expected_validation_result_sha256=args.expected_validation_result_sha256,
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
