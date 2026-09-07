#!/usr/bin/env python3
"""Consume one sealed C2 TRAIN expansion in the action-shared validation.

The stable V2 validator remains untouched.  This V3 consumer authenticates a
separately sealed pre-metric authority, reloads the original 4/3/0 batches,
and appends only the independently authenticated expansion rows to TRAIN/C2.
The original validation batches and their source bytes/digests are invariant.
No test split or EE endpoint is available to this runner.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
import importlib.util
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

stable_spec = importlib.util.spec_from_file_location(
    "e1_action_shared_validation_stable_v2",
    HERE / "run_v03_e1_action_shared_validation.py",
)
if stable_spec is None or stable_spec.loader is None:
    raise RuntimeError("cannot load stable action-shared validator")
stable = importlib.util.module_from_spec(stable_spec)
stable_spec.loader.exec_module(stable)

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch, ROUTE_NAMES  # noqa: E402
from mcrl.runtime.ee_axis_e1_ladder import E1LadderBatches, pair_batch_digest  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402
from mcrl.runtime.ee_axis_temporal_pairs import build_temporal_route_batch  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-e1-action-shared-validation-v3"
PREOUTCOME_SCHEMA = f"{SCHEMA}-preoutcome-authority-v1"
PREOUTCOME_SEAL_SCHEMA = f"{PREOUTCOME_SCHEMA}-seal"
EXECUTION_AUTHORITY_SCHEMA = f"{SCHEMA}-execution-authority-v1"
RESULT_SCHEMA = f"{SCHEMA}-result-v1"
RESULT_SEAL_SCHEMA = f"{RESULT_SCHEMA}-seal"
INDEPENDENT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-independent-source-verification-v1"
)
CENSUS_SCHEMA = "multi-catfish-mcrl-v03-e1-action-graph-coverage-census-v1"
EXPANSION_AUTHORITY_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-authority-v2"
)
EXPANSION_RESULT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-result-v1"
)
EXPANSION_SEED_ORDER = tuple(range(2026092201, 2026092221))
MIN_CLUSTERS_PER_NEEDED_ACTION = 3
MIN_SEEDS_PER_NEEDED_ACTION = 2
EXPANSION_CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED = 50
EXPANSION_MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR = 5
EXPANSION_ACTION_FIRST_CLUSTERS_PER_SEED = 2
EXPANSION_PUBLISHED_MINIMUM_CLUSTERS_PER_SEED = 12
EXPANSION_PUBLISHED_MINIMUM_WORLD_ANCHORS_PER_SEED = 3
EXPANSION_CHANGE_CLASS = "SOURCE_SELECTOR_REDESIGN_NOT_THRESHOLD_AMENDMENT"
EXPANSION_EXHAUSTED_STATUS = (
    "EXHAUSTED_CONNECTIVITY_RESTORED_REDUNDANCY_UNMET"
)
EXPANSION_SEALED_RECEIPT_DIGESTS = {
    "failed_expansion_authority_sha256": (
        "feaddcc8b5ada02cc09f8bedf56cb7f0823bf422031f9235a371c89c39140ffa"
    ),
    "failed_expansion_authority_seal_sha256": (
        "ea4f12b9efb6bcc361c9d3fa15a5116b8d72ac398aee6cdaa5659f0e3f4c3131"
    ),
    "failed_expansion_prepare_result_sha256": (
        "ffc9a2cb9b89413f9f4be70991f2b3aa978a9476251e8b0e30718f5d7392e87d"
    ),
    "failed_expansion_prepare_result_seal_sha256": (
        "055cf6be00221c355e2a03f70f36ca1b0b8822618ee5ee8983cd15c32072cdcd"
    ),
    "legal_probe_receipt_file_sha256": (
        "265dec78460ac22b81159cf9dba968319ac2774642599c8d6eb5cc8a62643044"
    ),
}
CLAIM_CEILING = "GO_500EP_SCREEN_ONLY_NO_TEST_NO_EE"
FALSE_BOUNDARY = {
    "test_split_opened": False,
    "held_out_ee_evaluated": False,
    "validation_metrics_computed": False,
}
CODE_MANIFEST_PATHS = (
    ".scratch/ee-axis-redesign/build_v03_e1_action_shared_validation_v3_authority.py",
    ".scratch/ee-axis-redesign/run_v03_e1_action_shared_validation_v3.py",
    ".scratch/ee-axis-redesign/run_v03_e1_action_shared_validation.py",
    ".scratch/ee-axis-redesign/run_v03_e1_action_shared_sources.py",
    ".scratch/ee-axis-redesign/verify_v03_e1_action_shared_sources.py",
    ".scratch/ee-axis-redesign/census_v03_e1_action_graph_coverage.py",
    ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_graph_expansion.py",
    ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_balanced_expansion.py",
    "src/mcrl/algorithms/ee_axis_action_shared.py",
    "src/mcrl/runtime/ee_axis_e1_c2_schedule.py",
    "src/mcrl/runtime/ee_axis_instrument_validity.py",
    "src/mcrl/runtime/ee_axis_temporal_dataset.py",
    "docs/MULTI-CATFISH-MCRL-V03-E1-ACTION-SHARED-AMENDMENT-2026-09-01.md",
)


class ActionSharedValidationV3Error(RuntimeError):
    """The sealed V3 consumer or its train-only expansion failed closed."""


def _digest(value: object, *, field: str) -> str:
    try:
        return stable.sources._digest(value, field=field)
    except Exception as error:
        raise ActionSharedValidationV3Error(str(error)) from error


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ActionSharedValidationV3Error(
            f"sealed file is missing, non-regular, or a symlink: {path}"
        )
    return stable.sources._file_sha256(path)


def _read_exact(path: Path, expected_sha256: str, *, label: str) -> dict[str, Any]:
    expected = _digest(expected_sha256, field=f"expected_{label}_sha256")
    if _sha256(path) != expected:
        raise ActionSharedValidationV3Error(f"{label} bytes changed")
    try:
        payload = stable.sources._read_canonical_json(path)
    except Exception as error:
        raise ActionSharedValidationV3Error(f"{label} is not canonical JSON") from error
    if not isinstance(payload, dict):
        raise ActionSharedValidationV3Error(f"{label} is not an object")
    return payload


def _code_manifest() -> dict[str, str]:
    return {relative: _sha256(REPO / relative) for relative in CODE_MANIFEST_PATHS}


def _authenticate_independent(
    root: Path, *, expected_result_sha256: str, expected_seal_sha256: str
) -> dict[str, Any]:
    result = _read_exact(
        root / "result.json", expected_result_sha256, label="independent_result"
    )
    seal = _read_exact(
        root / "result-seal.json",
        expected_seal_sha256,
        label="independent_result_seal",
    )
    if (
        result.get("schema") != INDEPENDENT_SCHEMA
        or result.get("status") != "PASS_INDEPENDENT_4_3_0_NO_TEST"
        or result.get("test_outcomes_generated") is not False
        or result.get("test_dataset_documents_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or seal.get("schema") != f"{INDEPENDENT_SCHEMA}-seal"
        or seal.get("result_file_sha256") != expected_result_sha256
    ):
        raise ActionSharedValidationV3Error("base independent verifier is invalid")
    return {
        **result,
        "result_file_sha256": expected_result_sha256,
        "result_seal_file_sha256": expected_seal_sha256,
    }


def _authenticate_census(
    root: Path,
    *,
    expected_result_sha256: str,
    expected_seal_sha256: str,
    independent: Mapping[str, Any],
) -> dict[str, Any]:
    result = _read_exact(root / "result.json", expected_result_sha256, label="census_result")
    seal = _read_exact(
        root / "result-seal.json", expected_seal_sha256, label="census_result_seal"
    )
    routes = result.get("routes")
    if (
        result.get("schema") != CENSUS_SCHEMA
        or result.get("status") != "INSUFFICIENT_COVERAGE"
        or result.get("decision_basis")
        != "action-identifiers-and-train-comparison-graph-only"
        or result.get("target_values_emitted") is not False
        or result.get("model_predictions_or_mae_computed") is not False
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result.get("independent_source_result_sha256")
        != independent["result_file_sha256"]
        or result.get("independent_source_result_seal_sha256")
        != independent["result_seal_file_sha256"]
        or not isinstance(routes, dict)
        or set(routes) != {"C1", "C2", "C3"}
        or routes["C1"].get("all_validation_contrasts_identified") is not True
        or routes["C2"].get("all_validation_contrasts_identified") is not False
        or routes["C3"].get("all_validation_contrasts_identified") is not True
        or seal.get("schema") != f"{CENSUS_SCHEMA}-seal"
        or seal.get("result_file_sha256") != expected_result_sha256
    ):
        raise ActionSharedValidationV3Error("target-free census authority is invalid")
    return {
        **result,
        "result_file_sha256": expected_result_sha256,
        "result_seal_file_sha256": expected_seal_sha256,
    }


def _source_metadata(
    source_root: Path, *, independent: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Freeze metadata only; never open an opening/temporal dataset here."""

    if source_root.is_symlink() or not source_root.is_dir():
        raise ActionSharedValidationV3Error("source root is not a regular directory")
    manifest = stable.sources._read_canonical_json(source_root / "source-manifest.json")
    prereg = stable.sources._read_canonical_json(source_root / "prereg.json")
    manifest_body = dict(manifest)
    manifest_sha256 = manifest_body.pop("source_manifest_sha256", None)
    prereg_body = dict(prereg)
    prereg_sha256 = prereg_body.pop("prereg_sha256", None)
    expected_split = {
        str(seed): split_name
        for seed, split_name in sorted(stable.sources_v2.SOURCE_SEED_SPLIT.items())
    }
    if (
        manifest_sha256 != stable.sources._canonical_sha256(manifest_body)
        or prereg_sha256 != stable.sources._canonical_sha256(prereg_body)
        or prereg.get("source_manifest_sha256") != manifest_sha256
        or prereg.get("source_seed_split") != expected_split
        or "test" in expected_split.values()
    ):
        raise ActionSharedValidationV3Error("base manifest/prereg or 4/3/0 split changed")

    data_root = source_root / "source-data"
    receipt_path = data_root / "receipt.json"
    index_path = data_root / "ladder-index.json"
    receipt_sha256 = _sha256(receipt_path)
    receipt = stable.sources._read_canonical_json(receipt_path)
    index_sha256 = _sha256(index_path)
    index = stable.sources._read_canonical_json(index_path)
    if (
        independent.get("source_receipt_file_sha256") != receipt_sha256
        or receipt.get("status") != "PASS"
        or receipt.get("held_out_ee_evaluated") is not False
        or index.get("schema") != stable.sources.LADDER_INDEX_SCHEMA
        or index.get("seed_split") != expected_split
        or index.get("test_split_opened") is not False
        or receipt.get("ladder_index_file_sha256") != index_sha256
    ):
        raise ActionSharedValidationV3Error("base source receipt/index authority changed")
    datasets = index.get("datasets")
    if not isinstance(datasets, dict) or set(datasets) != set(expected_split):
        raise ActionSharedValidationV3Error("base ladder dataset index is incomplete")

    validation: dict[str, dict[str, Any]] = {}
    for seed_text, split_name in expected_split.items():
        if split_name != "validation":
            continue
        row = datasets[seed_text]
        if not isinstance(row, dict):
            raise ActionSharedValidationV3Error("base validation index row is malformed")
        seed = int(seed_text)
        opening_name = f"opening-{seed}.json"
        temporal_name = f"temporal-{seed}.json"
        if row.get("opening_path") != opening_name or row.get("temporal_path") != temporal_name:
            raise ActionSharedValidationV3Error("base validation dataset path changed")
        validation[seed_text] = {
            "opening_path": opening_name,
            "opening_file_sha256": receipt["opening_dataset_file_sha256s"][seed_text],
            "opening_dataset_sha256": receipt["opening_dataset_sha256s"][seed_text],
            "temporal_path": temporal_name,
            "temporal_file_sha256": receipt["temporal_dataset_file_sha256s"][seed_text],
            "temporal_dataset_sha256": receipt["temporal_dataset_sha256s"][seed_text],
        }
        for field in (
            "opening_file_sha256",
            "opening_dataset_sha256",
            "temporal_file_sha256",
            "temporal_dataset_sha256",
        ):
            _digest(validation[seed_text][field], field=f"validation.{seed_text}.{field}")
        for name in (opening_name, temporal_name):
            path = data_root / name
            if path.is_symlink() or not path.is_file():
                raise ActionSharedValidationV3Error(
                    "base validation dataset is missing, non-regular, or a symlink"
                )
        if (
            row.get("opening_dataset_sha256")
            != validation[seed_text]["opening_dataset_sha256"]
            or row.get("temporal_dataset_sha256")
            != validation[seed_text]["temporal_dataset_sha256"]
        ):
            raise ActionSharedValidationV3Error("base validation dataset digest changed")
    if len(validation) != 3:
        raise ActionSharedValidationV3Error("base source no longer has three validation seeds")

    supplement_path = source_root / "action-shared-supplement-receipt.json"
    supplement_seal_path = source_root / "action-shared-supplement-receipt-seal.json"
    supplement_sha256 = _sha256(supplement_path)
    supplement_seal_sha256 = _sha256(supplement_seal_path)
    supplement = stable.sources._read_canonical_json(supplement_path)
    supplement_seal = stable.sources._read_canonical_json(supplement_seal_path)
    if (
        independent.get("supplement_receipt_file_sha256") != supplement_sha256
        or supplement.get("status") != "PASS"
        or supplement.get("test_outcomes_generated") is not False
        or supplement.get("test_split_opened") is not False
        or supplement.get("held_out_ee_evaluated") is not False
        or supplement_seal.get("schema")
        != "multi-catfish-mcrl-v03-e1-action-shared-source-supplement-seal-v1"
        or supplement_seal.get("receipt_file_sha256") != supplement_sha256
    ):
        raise ActionSharedValidationV3Error("base supplement result/seal changed")
    return prereg, {
        "source_manifest_sha256": manifest_sha256,
        "source_prereg_sha256": prereg_sha256,
        "source_receipt_file_sha256": receipt_sha256,
        "ladder_index_file_sha256": index_sha256,
        "supplement_result_sha256": supplement_sha256,
        "supplement_result_seal_sha256": supplement_seal_sha256,
        "source_seed_split": expected_split,
        "validation_datasets": validation,
        "validation_dataset_bytes_opened": False,
    }


def _authenticate_expansion(
    root: Path,
    *,
    expected_authority_sha256: str,
    expected_authority_seal_sha256: str,
    expected_result_sha256: str,
    expected_result_seal_sha256: str,
    independent: Mapping[str, Any],
    census: Mapping[str, Any],
    prereg: Mapping[str, Any],
    source_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    authority = _read_exact(
        root / "authority.json", expected_authority_sha256, label="expansion_authority"
    )
    authority_seal = _read_exact(
        root / "authority-seal.json",
        expected_authority_seal_sha256,
        label="expansion_authority_seal",
    )
    result = _read_exact(
        root / "result.json", expected_result_sha256, label="expansion_result"
    )
    result_seal = _read_exact(
        root / "result-seal.json",
        expected_result_seal_sha256,
        label="expansion_result_seal",
    )
    dependency_pairs = {
        "independent_result_sha256": independent["result_file_sha256"],
        "independent_result_seal_sha256": independent["result_seal_file_sha256"],
        "census_result_sha256": census["result_file_sha256"],
        "census_result_seal_sha256": census["result_seal_file_sha256"],
    }
    census_c2 = census.get("routes", {}).get("C2", {})
    census_components = census_c2.get("connected_components_with_edges")
    census_pairs = census_c2.get("unsupported_validation_action_pairs")
    census_action_dim = census_c2.get("action_dim")
    selected = result.get("selected_seed_order")
    candidate_order = authority.get("candidate_seed_order")
    if (
        candidate_order != list(EXPANSION_SEED_ORDER)
        or not isinstance(selected, list)
        or not selected
        or any(type(seed) is not int or seed < 0 for seed in selected)
        or len(set(selected)) != len(selected)
        or selected != candidate_order[: len(selected)]
    ):
        raise ActionSharedValidationV3Error("expansion selected seed order is invalid")
    selected_tuple = tuple(selected)
    temporal_paths = result.get("temporal_dataset_paths")
    temporal_file_sha256s = result.get("temporal_dataset_file_sha256s")
    temporal_dataset_sha256s = result.get("temporal_dataset_sha256s")
    temporal_grouped = result.get("temporal_datasets")
    selected_keys = {str(seed) for seed in selected_tuple}
    if (
        authority.get("schema") != EXPANSION_AUTHORITY_SCHEMA
        or authority.get("status") != "SEALED_BEFORE_SCHEDULE_TOPOLOGY_INSPECTION"
        or authority.get("scope")
        != "C2_TRAIN_ONLY_ACTION_BALANCED_SOURCE_REDESIGN_ONCE"
        or authority.get("change_class") != EXPANSION_CHANGE_CLASS
        or authority.get("bounded_supplement_status") != EXPANSION_EXHAUSTED_STATUS
        or authority.get("candidate_seed_partition") != "TRAIN"
        or authority.get("selection_rule")
        != (
            "shortest-prefix-of-deterministic-action-balanced-train-schedules-"
            "by-action-topology-only"
        )
        or authority.get("candidate_schedule_maximum_clusters_per_seed")
        != EXPANSION_CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED
        or authority.get("maximum_focal_users_per_world_anchor")
        != EXPANSION_MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR
        or authority.get("action_first_clusters_per_needed_action_per_seed")
        != EXPANSION_ACTION_FIRST_CLUSTERS_PER_SEED
        or authority.get("published_schedule_minimum_clusters_per_seed")
        != EXPANSION_PUBLISHED_MINIMUM_CLUSTERS_PER_SEED
        or authority.get("published_schedule_minimum_world_anchors_per_seed")
        != EXPANSION_PUBLISHED_MINIMUM_WORLD_ANCHORS_PER_SEED
        or authority.get("minimum_clusters_per_needed_action")
        != MIN_CLUSTERS_PER_NEEDED_ACTION
        or authority.get("minimum_seeds_per_needed_action")
        != MIN_SEEDS_PER_NEEDED_ACTION
        or authority.get("replacement_seed_pool_authorized") is not False
        or authority.get("second_seed_pool_authorized") is not False
        or authority.get("outcome_or_target_fields_permitted_in_prepare") is not False
        or authority.get("original_c2_components") != census_components
        or authority.get("original_unsupported_c2_pairs") != census_pairs
        or authority.get("validation_dataset_bytes_opened") is not False
        or authority.get("test_split_opened") is not False
        or authority.get("held_out_ee_evaluated") is not False
        or authority.get("source_prereg_sha256") != prereg.get("prereg_sha256")
        or authority.get("source_manifest_sha256") != prereg.get("source_manifest_sha256")
        or authority.get("checkpoint_sha256") != prereg.get("checkpoint_sha256")
        or authority.get("base_source_receipt_sha256")
        != source_metadata["source_receipt_file_sha256"]
        or authority.get("base_source_result_sha256")
        != source_metadata["supplement_result_sha256"]
        or authority.get("base_source_result_seal_sha256")
        != source_metadata["supplement_result_seal_sha256"]
        or any(authority.get(key) != value for key, value in dependency_pairs.items())
        or authority_seal.get("schema") != f"{EXPANSION_AUTHORITY_SCHEMA}-seal"
        or authority_seal.get("authority_sha256") != expected_authority_sha256
        or result.get("schema") != EXPANSION_RESULT_SCHEMA
        or result.get("status") != "PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION"
        or result.get("completion_status") != result.get("status")
        or result.get("authority_sha256") != expected_authority_sha256
        or any(result.get(key) != value for key, value in dependency_pairs.items())
        or result.get("base_source_receipt_sha256")
        != source_metadata["source_receipt_file_sha256"]
        or result.get("source_prereg_sha256") != prereg.get("prereg_sha256")
        or result.get("source_manifest_sha256") != prereg.get("source_manifest_sha256")
        or result.get("checkpoint_sha256") != prereg.get("checkpoint_sha256")
        or result.get("environment_source_sha256")
        != prereg.get("environment_source_sha256")
        or result.get("reward_source_sha256") != prereg.get("reward_source_sha256")
        or result.get("source_partition") != "TRAIN"
        or result.get("held_out") is not False
        or result.get("replacement_seed_pool_used") is not False
        or result.get("second_seed_pool_used") is not False
        or result.get("validation_dataset_bytes_opened") is not False
        or result.get("test_split_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or result.get("targets_or_validation_metrics_computed") is not False
        or set(result.get("selected_schedule_file_sha256s", {})) != selected_keys
        or not isinstance(temporal_paths, dict)
        or not isinstance(temporal_file_sha256s, dict)
        or not isinstance(temporal_dataset_sha256s, dict)
        or not isinstance(temporal_grouped, dict)
        or set(temporal_paths) != selected_keys
        or set(temporal_file_sha256s) != selected_keys
        or set(temporal_dataset_sha256s) != selected_keys
        or set(temporal_grouped) != selected_keys
        or result_seal.get("schema") != f"{EXPANSION_RESULT_SCHEMA}-seal"
        or result_seal.get("result_file_sha256") != expected_result_sha256
        or result_seal.get("authority_sha256") != expected_authority_sha256
    ):
        raise ActionSharedValidationV3Error("C2 expansion authority/result closure is invalid")
    formal_runner_sha256 = _sha256(
        REPO
        / ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_balanced_expansion.py"
    )
    expected_implementation_manifest = {
        "formal_action_balanced_runner": formal_runner_sha256,
        "exhausted_expansion_runner": _sha256(
            REPO
            / ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_graph_expansion.py"
        ),
        "action_shared_source_runner": _sha256(
            REPO / ".scratch/ee-axis-redesign/run_v03_e1_action_shared_sources.py"
        ),
        "c2_preoutcome_schedule_helper": _sha256(
            REPO / "src/mcrl/runtime/ee_axis_e1_c2_schedule.py"
        ),
        "temporal_dataset_helper": _sha256(
            REPO / "src/mcrl/runtime/ee_axis_temporal_dataset.py"
        ),
    }
    if (
        authority.get("runner_file_sha256") != formal_runner_sha256
        or authority.get("implementation_file_sha256s")
        != expected_implementation_manifest
    ):
        raise ActionSharedValidationV3Error(
            "C2 expansion is not closed over the formal v2 implementation"
        )
    for field in (
        "failed_expansion_authority_sha256",
        "failed_expansion_authority_seal_sha256",
        "failed_expansion_prepare_result_sha256",
        "failed_expansion_prepare_result_seal_sha256",
        "legal_probe_receipt_file_sha256",
    ):
        value = _digest(authority.get(field), field=f"expansion.{field}")
        if (
            value != EXPANSION_SEALED_RECEIPT_DIGESTS[field]
            or result.get(field) != value
        ):
            raise ActionSharedValidationV3Error(
                "C2 expansion result lost the failed-supplement/probe closure"
            )
    graph = result.get("final_c2_graph_report")
    if (
        not isinstance(graph, dict)
        or graph.get("action_dim") != census_action_dim
        or graph.get("original_unsupported_validation_action_pairs") != census_pairs
        or graph.get("coverage_sufficient") is not True
        or graph.get("remaining_unsupported_validation_action_pairs") != []
        or graph.get("target_or_outcome_values_used_for_coverage_decision") is not False
    ):
        raise ActionSharedValidationV3Error("C2 expansion final graph did not pass")
    for field, mapping in (
        ("selected_schedule_file_sha256s", result["selected_schedule_file_sha256s"]),
        ("temporal_dataset_file_sha256s", temporal_file_sha256s),
        ("temporal_dataset_sha256s", temporal_dataset_sha256s),
    ):
        for key, value in mapping.items():
            _digest(value, field=f"{field}.{key}")
    for seed in selected_tuple:
        key = str(seed)
        expected_path = f"temporal-datasets/c2-train-{seed}.json"
        row = temporal_grouped[key]
        if (
            temporal_paths[key] != expected_path
            or not isinstance(row, dict)
            or row.get("path") != expected_path
            or row.get("file_sha256") != temporal_file_sha256s[key]
            or row.get("dataset_sha256") != temporal_dataset_sha256s[key]
            or row.get("source_partition") != "TRAIN"
            or row.get("held_out") is not False
        ):
            raise ActionSharedValidationV3Error("expansion temporal metadata is inconsistent")
    return {
        "authority": authority,
        "result": result,
        "selected_seed_order": list(selected_tuple),
        "authority_sha256": expected_authority_sha256,
        "authority_seal_sha256": expected_authority_seal_sha256,
        "result_sha256": expected_result_sha256,
        "result_seal_sha256": expected_result_seal_sha256,
    }


def collect_preoutcome_dependencies(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    expansion_root: Path,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
    expected_census_result_sha256: str,
    expected_census_result_seal_sha256: str,
    expected_expansion_authority_sha256: str,
    expected_expansion_authority_seal_sha256: str,
    expected_expansion_result_sha256: str,
    expected_expansion_result_seal_sha256: str,
) -> dict[str, Any]:
    independent = _authenticate_independent(
        independent_root,
        expected_result_sha256=expected_independent_result_sha256,
        expected_seal_sha256=expected_independent_result_seal_sha256,
    )
    census = _authenticate_census(
        census_root,
        expected_result_sha256=expected_census_result_sha256,
        expected_seal_sha256=expected_census_result_seal_sha256,
        independent=independent,
    )
    prereg, source_metadata = _source_metadata(source_root, independent=independent)
    if (
        census.get("source_prereg_sha256") != prereg.get("prereg_sha256")
        or census.get("source_manifest_sha256") != prereg.get("source_manifest_sha256")
    ):
        raise ActionSharedValidationV3Error("census and base source lineage disagree")
    expansion = _authenticate_expansion(
        expansion_root,
        expected_authority_sha256=expected_expansion_authority_sha256,
        expected_authority_seal_sha256=expected_expansion_authority_seal_sha256,
        expected_result_sha256=expected_expansion_result_sha256,
        expected_result_seal_sha256=expected_expansion_result_seal_sha256,
        independent=independent,
        census=census,
        prereg=prereg,
        source_metadata=source_metadata,
    )
    return {
        "independent": independent,
        "census": census,
        "prereg": prereg,
        "source_metadata": source_metadata,
        "expansion": expansion,
    }


def preoutcome_authority_payload(dependencies: Mapping[str, Any]) -> dict[str, Any]:
    independent = dependencies["independent"]
    census = dependencies["census"]
    source_metadata = dependencies["source_metadata"]
    expansion = dependencies["expansion"]
    return {
        "schema": PREOUTCOME_SCHEMA,
        "status": "SEALED_AFTER_C2_TRAIN_EXPANSION_BEFORE_ANY_VALIDATION_METRIC",
        "claim_ceiling": CLAIM_CEILING,
        "base_independent_verifier_result_sha256": independent["result_file_sha256"],
        "base_independent_verifier_result_seal_sha256": independent[
            "result_seal_file_sha256"
        ],
        "census_result_sha256": census["result_file_sha256"],
        "census_result_seal_sha256": census["result_seal_file_sha256"],
        "expansion_authority_sha256": expansion["authority_sha256"],
        "expansion_authority_seal_sha256": expansion["authority_seal_sha256"],
        "expansion_result_sha256": expansion["result_sha256"],
        "expansion_result_seal_sha256": expansion["result_seal_sha256"],
        "expansion_authority_schema": EXPANSION_AUTHORITY_SCHEMA,
        "expansion_change_class": EXPANSION_CHANGE_CLASS,
        "expansion_runner_file_sha256": expansion["authority"][
            "runner_file_sha256"
        ],
        "base_source": dict(source_metadata),
        "selected_expansion_seed_order": expansion["selected_seed_order"],
        "code_manifest": _code_manifest(),
        "augmentation_contract": {
            "only_partition_mutated": "TRAIN",
            "only_route_mutated": "C2",
            "operation": "append-expansion-temporal-rows",
            "base_validation_batches_must_retain_identity": True,
            "base_validation_batch_digests_must_be_unchanged": True,
            "base_validation_dataset_file_and_dataset_digests_must_be_unchanged": True,
        },
        "validation_gate_contract": stable.VALIDATION_GATE_CONTRACT,
        "validation_dataset_bytes_opened": False,
        **FALSE_BOUNDARY,
    }


def _load_preoutcome_authority(
    authority_path: Path,
    seal_path: Path,
    *,
    expected_authority_sha256: str,
    expected_seal_sha256: str,
) -> dict[str, Any]:
    authority = _read_exact(
        authority_path, expected_authority_sha256, label="v3_preoutcome_authority"
    )
    seal = _read_exact(
        seal_path, expected_seal_sha256, label="v3_preoutcome_authority_seal"
    )
    if (
        authority.get("schema") != PREOUTCOME_SCHEMA
        or authority.get("status")
        != "SEALED_AFTER_C2_TRAIN_EXPANSION_BEFORE_ANY_VALIDATION_METRIC"
        or authority.get("claim_ceiling") != CLAIM_CEILING
        or authority.get("validation_dataset_bytes_opened") is not False
        or authority.get("validation_metrics_computed") is not False
        or authority.get("test_split_opened") is not False
        or authority.get("held_out_ee_evaluated") is not False
        or authority.get("validation_gate_contract") != stable.VALIDATION_GATE_CONTRACT
        or authority.get("code_manifest") != _code_manifest()
        or seal.get("schema") != PREOUTCOME_SEAL_SCHEMA
        or seal.get("authority_file_sha256") != expected_authority_sha256
    ):
        raise ActionSharedValidationV3Error("V3 preoutcome authority/seal is invalid")
    return authority


def _canonical_expansion_path(root: Path, relative: object, *, expected: str) -> Path:
    if relative != expected:
        raise ActionSharedValidationV3Error("expansion temporal path changed")
    path = root / expected
    if path.is_symlink() or not path.is_file():
        raise ActionSharedValidationV3Error("expansion temporal dataset is not regular")
    if path.resolve(strict=True).parent != (root / "temporal-datasets").resolve(strict=True):
        raise ActionSharedValidationV3Error("expansion temporal path escapes publication")
    return path


def _graph_report_from_rows(
    *,
    authority: Mapping[str, Any],
    rows_by_seed: Mapping[int, Sequence[Any]],
    action_dim: int,
) -> dict[str, Any]:
    original_components = authority.get("original_c2_components")
    original_pairs = authority.get("original_unsupported_c2_pairs")
    if type(action_dim) is not int or action_dim < 2:
        raise ActionSharedValidationV3Error("expansion graph action dimension is invalid")
    parent = list(range(action_dim))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    active: set[int] = set()
    for component in original_components:
        members = tuple(int(value) for value in component)
        active.update(members)
        for action in members[1:]:
            union(members[0], action)
    pairs = tuple(
        (int(row["reference_action"]), int(row["candidate_action"]))
        for row in original_pairs
    )
    needed = sorted({action for pair in pairs for action in pair})
    clusters: dict[int, set[tuple[int, str]]] = defaultdict(set)
    seeds: dict[int, set[int]] = defaultdict(set)
    identities: set[tuple[int, str]] = set()
    edge_count = 0
    for seed, rows in rows_by_seed.items():
        for row in rows:
            identity = str(row.verify())
            key = (seed, identity)
            if key in identities or int(row.seed) != seed:
                raise ActionSharedValidationV3Error("expansion row identity/seed duplicated")
            identities.add(key)
            reference = int(row.reference_action)
            candidate = int(row.candidate_action)
            if not 0 <= reference < action_dim or not 0 <= candidate < action_dim:
                raise ActionSharedValidationV3Error("expansion row action is out of range")
            edge_count += 1
            active.update((reference, candidate))
            union(reference, candidate)
            for action in (reference, candidate):
                if action in needed:
                    clusters[action].add(key)
                    seeds[action].add(seed)
    remaining = sorted(pair for pair in pairs if find(pair[0]) != find(pair[1]))
    components: dict[int, list[int]] = defaultdict(list)
    for action in sorted(active):
        components[find(action)].append(action)
    evidence = {
        str(action): {
            "clusters": len(clusters[action]),
            "seeds": sorted(seeds[action]),
            "meets_minimum_clusters": len(clusters[action])
            >= MIN_CLUSTERS_PER_NEEDED_ACTION,
            "meets_minimum_seeds": len(seeds[action]) >= MIN_SEEDS_PER_NEEDED_ACTION,
        }
        for action in needed
    }
    sufficient = not remaining and all(
        row["meets_minimum_clusters"] and row["meets_minimum_seeds"]
        for row in evidence.values()
    )
    return {
        "decision_basis": "completed-train-row-action-topology-only",
        "action_dim": action_dim,
        "original_unsupported_validation_action_pairs": [
            {"reference_action": left, "candidate_action": right}
            for left, right in pairs
        ],
        "remaining_unsupported_validation_action_pairs": [
            {"reference_action": left, "candidate_action": right}
            for left, right in remaining
        ],
        "needed_actions": needed,
        "needed_action_evidence": evidence,
        "expansion_clusters": edge_count,
        "connected_components_with_edges": sorted(
            (sorted(members) for members in components.values()),
            key=lambda row: (row[0], len(row), row),
        ),
        "minimum_clusters_per_needed_action": MIN_CLUSTERS_PER_NEEDED_ACTION,
        "minimum_seeds_per_needed_action": MIN_SEEDS_PER_NEEDED_ACTION,
        "coverage_sufficient": sufficient,
        "target_or_outcome_values_used_for_coverage_decision": False,
        "generated_outcomes_materialized": True,
    }


def _load_expansion_rows(
    expansion_root: Path,
    expansion: Mapping[str, Any],
    *,
    prereg: Mapping[str, Any],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    result = expansion["result"]
    authority = expansion["authority"]
    selected = tuple(int(seed) for seed in expansion["selected_seed_order"])
    if set(selected).intersection(stable.sources_v2.SOURCE_SEED_SPLIT):
        raise ActionSharedValidationV3Error("expansion seed collides with base 4/3/0 source")
    rows_by_seed: dict[int, tuple[Any, ...]] = {}
    access: dict[str, dict[str, Any]] = {}
    for seed in selected:
        key = str(seed)
        expected_path = f"temporal-datasets/c2-train-{seed}.json"
        path = _canonical_expansion_path(
            expansion_root,
            result["temporal_dataset_paths"][key],
            expected=expected_path,
        )
        if _sha256(path) != result["temporal_dataset_file_sha256s"][key]:
            raise ActionSharedValidationV3Error("expansion temporal file digest changed")
        dataset = read_temporal_dataset(path)
        if (
            dataset.verify() != result["temporal_dataset_sha256s"][key]
            or dataset.source_manifest_sha256 != prereg.get("source_manifest_sha256")
            or dataset.checkpoint_sha256 != prereg.get("checkpoint_sha256")
            or any(int(row.seed) != seed for row in dataset.rows)
            or len(dataset.rows) != result["temporal_datasets"][key]["rows"]
        ):
            raise ActionSharedValidationV3Error("expansion temporal lineage changed")
        rows_by_seed[seed] = tuple(dataset.rows)
        access[key] = {
            "path": expected_path,
            "file_sha256": result["temporal_dataset_file_sha256s"][key],
            "dataset_sha256": result["temporal_dataset_sha256s"][key],
            "rows": len(dataset.rows),
        }
    recomputed = _graph_report_from_rows(
        authority=authority,
        rows_by_seed=rows_by_seed,
        action_dim=int(result["final_c2_graph_report"]["action_dim"]),
    )
    if recomputed != result.get("final_c2_graph_report") or not recomputed["coverage_sufficient"]:
        raise ActionSharedValidationV3Error("expansion final C2 graph was not reproducible")
    rows = tuple(row for seed in selected for row in rows_by_seed[seed])
    return rows, {
        "selected_seed_order": list(selected),
        "temporal_datasets": access,
        "recomputed_final_c2_graph_report": recomputed,
        "source_partition": "TRAIN",
        "held_out": False,
        "validation_dataset_bytes_opened": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }


def _append_pair_batches(base: EEAxisPairBatch, extra: EEAxisPairBatch) -> EEAxisPairBatch:
    return EEAxisPairBatch(
        states=np.concatenate((base.states, extra.states), axis=0),
        reference_actions=np.concatenate(
            (base.reference_actions, extra.reference_actions), axis=0
        ),
        candidate_actions=np.concatenate(
            (base.candidate_actions, extra.candidate_actions), axis=0
        ),
        target_surplus_bits=np.concatenate(
            (base.target_surplus_bits, extra.target_surplus_bits), axis=0
        ),
        action_masks=np.concatenate((base.action_masks, extra.action_masks), axis=0),
    )


def _append_train_c2_only(
    base: E1LadderBatches,
    expansion_rows: Sequence[Any],
    *,
    config: Any,
) -> tuple[E1LadderBatches, dict[str, Any]]:
    if not expansion_rows:
        raise ActionSharedValidationV3Error("C2 expansion contains no rows")
    base_validation_objects = tuple(id(batch) for batch in base.validation)
    base_validation_digests = {
        route: pair_batch_digest(base.batch("validation", route)) for route in ROUTE_NAMES
    }
    base_train_digests = {
        route: pair_batch_digest(base.batch("train", route)) for route in ROUTE_NAMES
    }
    extra = build_temporal_route_batch(tuple(expansion_rows)).pair_batch
    merged_c2 = _append_pair_batches(base.batch("train", "C2"), extra)
    augmented = E1LadderBatches(
        train=(base.train[0], merged_c2, base.train[2]),
        validation=base.validation,
    )
    for split_name in ("train", "validation"):
        for route in ROUTE_NAMES:
            augmented.batch(split_name, route).validate(
                state_dim=config.state_dim, action_dim=config.action_dim
            )
    after_validation_digests = {
        route: pair_batch_digest(augmented.batch("validation", route))
        for route in ROUTE_NAMES
    }
    if (
        tuple(id(batch) for batch in augmented.validation) != base_validation_objects
        or after_validation_digests != base_validation_digests
        or augmented.train[0] is not base.train[0]
        or augmented.train[2] is not base.train[2]
        or pair_batch_digest(augmented.batch("train", "C1")) != base_train_digests["C1"]
        or pair_batch_digest(augmented.batch("train", "C3")) != base_train_digests["C3"]
    ):
        raise ActionSharedValidationV3Error("augmentation changed a non-TRAIN/C2 batch")
    return augmented, {
        "operation": "append-expansion-temporal-rows",
        "base_train_batch_digests": base_train_digests,
        "expansion_c2_batch_digest": pair_batch_digest(extra),
        "augmented_train_batch_digests": {
            route: pair_batch_digest(augmented.batch("train", route))
            for route in ROUTE_NAMES
        },
        "base_validation_batch_digests": base_validation_digests,
        "post_augmentation_validation_batch_digests": after_validation_digests,
        "validation_batch_objects_retained": True,
        "base_c2_rows": int(base.batch("train", "C2").states.shape[0]),
        "appended_c2_rows": int(extra.states.shape[0]),
        "augmented_c2_rows": int(merged_c2.states.shape[0]),
        "only_partition_mutated": "TRAIN",
        "only_route_mutated": "C2",
    }


def _execute_metrics(
    *,
    output_dir: Path,
    execution_authority: Mapping[str, Any],
    prereg: Mapping[str, Any],
    config: Any,
    batches: E1LadderBatches,
    validation_temporal_rows: tuple[Any, ...],
) -> dict[str, Any]:
    """Run the unchanged stable metric logic after both authorities are sealed."""

    started = time.perf_counter()
    checkpoints = output_dir / "checkpoints"
    checkpoints.mkdir()
    receipts: dict[int, dict[int, dict[str, dict[str, Any]]]] = {}
    checkpoint_digests: dict[str, str] = {}
    for raw_seed in prereg["initialization_seeds"]:
        seed = int(raw_seed)
        trainer = stable.EEAxisActionSharedTrainer(config, train_seed=seed, device="cpu")
        completed = 0
        seed_receipts: dict[int, dict[str, dict[str, Any]]] = {}
        for rung in stable.UPDATE_RUNGS:
            for _update in range(completed, rung):
                for route in ROUTE_NAMES:
                    trainer.update_route(route, batches.batch("train", route))
            completed = rung
            seed_receipts[rung] = {
                route: stable._route_metrics(trainer, batches, route_index)
                for route_index, route in enumerate(ROUTE_NAMES)
            }
            checkpoint_name = f"init-{seed}-rung-{rung:06d}.pt"
            checkpoint_digests[checkpoint_name] = stable._save_checkpoint(
                checkpoints / checkpoint_name,
                {
                    "schema": f"{SCHEMA}-checkpoint-v1",
                    "authority_sha256": execution_authority["authority_sha256"],
                    "initialization_seed": seed,
                    "rung": rung,
                    "validation_metrics": seed_receipts[rung],
                    "trainer": trainer.checkpoint_state(update_count=rung * 3),
                    "test_split_opened": False,
                    "held_out_ee_evaluated": False,
                },
            )
        receipts[seed] = seed_receipts
    initialization_seeds = tuple(int(seed) for seed in prereg["initialization_seeds"])
    if len(initialization_seeds) != 3:
        raise ActionSharedValidationV3Error("validation requires three initializations")
    selected_rung, mean_ratios = stable.select_common_rung(
        receipts, initialization_seeds=initialization_seeds
    )
    trainers: dict[int, Any] = {}
    for seed in initialization_seeds:
        checkpoint_name = f"init-{seed}-rung-{selected_rung:06d}.pt"
        checkpoint_path = checkpoints / checkpoint_name
        if _sha256(checkpoint_path) != checkpoint_digests[checkpoint_name]:
            raise ActionSharedValidationV3Error("selected checkpoint digest changed")
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        if (
            checkpoint.get("schema") != f"{SCHEMA}-checkpoint-v1"
            or checkpoint.get("authority_sha256") != execution_authority["authority_sha256"]
            or checkpoint.get("initialization_seed") != seed
            or checkpoint.get("rung") != selected_rung
            or checkpoint.get("validation_metrics") != receipts[seed][selected_rung]
            or checkpoint.get("test_split_opened") is not False
            or checkpoint.get("held_out_ee_evaluated") is not False
        ):
            raise ActionSharedValidationV3Error("selected checkpoint identity changed")
        trainer = stable.EEAxisActionSharedTrainer(config, train_seed=seed, device="cpu")
        if trainer.load_checkpoint_state(checkpoint["trainer"]) != selected_rung * 3:
            raise ActionSharedValidationV3Error("selected checkpoint update count changed")
        trainers[seed] = trainer
    action_effects = stable._action_main_effect(trainers, batches)
    collisions = stable._collision_census(
        batches,
        kappa_bits=config.kappa_bits,
        policy_digest=str(prereg["checkpoint_sha256"]),
    )
    c2_sensitivity = stable._c2_anchor_sensitivity(
        trainers, batches, validation_temporal_rows
    )
    gate = stable._gate(
        selected_rung=selected_rung,
        receipts=receipts,
        action_main_effects=action_effects,
        collisions=collisions,
        c2_sensitivity=c2_sensitivity,
    )
    result = {
        "schema": RESULT_SCHEMA,
        "status": gate["status"],
        "claim_ceiling": CLAIM_CEILING,
        "authority_sha256": execution_authority["authority_sha256"],
        "preoutcome_authority_sha256": execution_authority[
            "preoutcome_authority_sha256"
        ],
        "selected_common_rung": selected_rung,
        "mean_model_to_strongest_null_ratio_by_rung": {
            str(rung): value for rung, value in mean_ratios.items()
        },
        "validation_receipts": {
            str(seed): {str(rung): values for rung, values in rows.items()}
            for seed, rows in receipts.items()
        },
        "deployment_action_main_effect_by_initialization": action_effects,
        "observability_collisions": collisions,
        "c2_anchor_sensitivity": c2_sensitivity,
        "gate": gate,
        "checkpoint_file_sha256s": checkpoint_digests,
        "selected_checkpoint_files": {
            str(seed): f"checkpoints/init-{seed}-rung-{selected_rung:06d}.pt"
            for seed in initialization_seeds
        },
        "source_partition_expanded": "TRAIN",
        "expanded_route": "C2",
        "base_validation_batches_unchanged": True,
        "elapsed_s": time.perf_counter() - started,
        "test_dataset_paths_opened": [],
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    result_sha256 = stable.sources._write_once_json(output_dir / "result.json", result)
    result_seal_sha256 = stable.sources._write_once_json(
        output_dir / "result-seal.json",
        {
            "schema": RESULT_SEAL_SCHEMA,
            "authority_sha256": execution_authority["authority_sha256"],
            "preoutcome_authority_sha256": execution_authority[
                "preoutcome_authority_sha256"
            ],
            "result_file_sha256": result_sha256,
        },
    )
    return {
        **result,
        "result_file_sha256": result_sha256,
        "result_seal_file_sha256": result_seal_sha256,
    }


def run(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    expansion_root: Path,
    preoutcome_authority_path: Path,
    preoutcome_authority_seal_path: Path,
    output_dir: Path,
    expected_preoutcome_authority_sha256: str,
    expected_preoutcome_authority_seal_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite V3 validation output")
    # This authentication is intentionally first and precedes every source
    # dataset open, target access, training update, prediction, or metric.
    preoutcome = _load_preoutcome_authority(
        preoutcome_authority_path,
        preoutcome_authority_seal_path,
        expected_authority_sha256=expected_preoutcome_authority_sha256,
        expected_seal_sha256=expected_preoutcome_authority_seal_sha256,
    )
    dependencies = collect_preoutcome_dependencies(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        expansion_root=expansion_root,
        expected_independent_result_sha256=preoutcome[
            "base_independent_verifier_result_sha256"
        ],
        expected_independent_result_seal_sha256=preoutcome[
            "base_independent_verifier_result_seal_sha256"
        ],
        expected_census_result_sha256=preoutcome["census_result_sha256"],
        expected_census_result_seal_sha256=preoutcome[
            "census_result_seal_sha256"
        ],
        expected_expansion_authority_sha256=preoutcome[
            "expansion_authority_sha256"
        ],
        expected_expansion_authority_seal_sha256=preoutcome[
            "expansion_authority_seal_sha256"
        ],
        expected_expansion_result_sha256=preoutcome["expansion_result_sha256"],
        expected_expansion_result_seal_sha256=preoutcome[
            "expansion_result_seal_sha256"
        ],
    )
    if preoutcome != preoutcome_authority_payload(dependencies):
        raise ActionSharedValidationV3Error("preoutcome dependency closure changed")
    prereg = dependencies["prereg"]
    independent = dependencies["independent"]
    config = stable._config_from_prereg(prereg)
    base_batches, validation_temporal_rows, source_access = stable._load_batches(
        source_root=source_root,
        prereg=prereg,
        config=config,
        expected_source_receipt_sha256=dependencies["source_metadata"][
            "source_receipt_file_sha256"
        ],
        independent_verification=independent,
    )
    expansion_rows, expansion_access = _load_expansion_rows(
        expansion_root,
        dependencies["expansion"],
        prereg=prereg,
    )
    batches, augmentation = _append_train_c2_only(
        base_batches, expansion_rows, config=config
    )
    if dependencies["source_metadata"]["validation_datasets"] != preoutcome[
        "base_source"
    ]["validation_datasets"]:
        raise ActionSharedValidationV3Error("base validation file/dataset digests changed")

    output_dir.mkdir(parents=True)
    execution_authority = {
        "schema": EXECUTION_AUTHORITY_SCHEMA,
        "status": "SEALED_BEFORE_ANY_VALIDATION_METRIC",
        "claim_ceiling": CLAIM_CEILING,
        "preoutcome_authority_sha256": expected_preoutcome_authority_sha256,
        "preoutcome_authority_seal_sha256": expected_preoutcome_authority_seal_sha256,
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "source_access": source_access,
        "expansion_access": expansion_access,
        "config": asdict(config),
        "initialization_seeds": prereg["initialization_seeds"],
        "update_rungs": list(stable.UPDATE_RUNGS),
        "validation_gate_contract": stable.VALIDATION_GATE_CONTRACT,
        "augmentation": augmentation,
        "base_validation_datasets": dependencies["source_metadata"][
            "validation_datasets"
        ],
        "code_manifest": _code_manifest(),
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "validation_metrics_computed": False,
    }
    execution_authority["authority_sha256"] = stable.sources._canonical_sha256(
        execution_authority
    )
    authority_file_sha256 = stable.sources._write_once_json(
        output_dir / "authority.json", execution_authority
    )
    stable.sources._write_once_json(
        output_dir / "authority-seal.json",
        {
            "schema": f"{EXECUTION_AUTHORITY_SCHEMA}-seal",
            "authority_sha256": execution_authority["authority_sha256"],
            "authority_file_sha256": authority_file_sha256,
            "preoutcome_authority_sha256": expected_preoutcome_authority_sha256,
        },
    )
    return _execute_metrics(
        output_dir=output_dir,
        execution_authority=execution_authority,
        prereg=prereg,
        config=config,
        batches=batches,
        validation_temporal_rows=validation_temporal_rows,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--independent-root", type=Path, required=True)
    parser.add_argument("--census-root", type=Path, required=True)
    parser.add_argument("--expansion-root", type=Path, required=True)
    parser.add_argument("--preoutcome-authority", type=Path, required=True)
    parser.add_argument("--preoutcome-authority-seal", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-preoutcome-authority-sha256", required=True)
    parser.add_argument("--expected-preoutcome-authority-seal-sha256", required=True)
    args = parser.parse_args(argv)
    payload = run(
        source_root=args.source_root,
        independent_root=args.independent_root,
        census_root=args.census_root,
        expansion_root=args.expansion_root,
        preoutcome_authority_path=args.preoutcome_authority,
        preoutcome_authority_seal_path=args.preoutcome_authority_seal,
        output_dir=args.output_dir,
        expected_preoutcome_authority_sha256=args.expected_preoutcome_authority_sha256,
        expected_preoutcome_authority_seal_sha256=(
            args.expected_preoutcome_authority_seal_sha256
        ),
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
