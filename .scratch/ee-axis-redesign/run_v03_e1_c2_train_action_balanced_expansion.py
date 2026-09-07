#!/usr/bin/env python3
"""Formal one-shot C2 TRAIN source-selector redesign.

The original fixed-pool supplement restored graph connectivity but exhausted
all twenty preregistered seeds without satisfying the unchanged three-cluster,
two-seed redundancy gate.  This runner authenticates that failed receipt and a
target-free legal design probe, seals a new source-design authority, and only
then discovers new schedule topology.

``prepare`` raises only the per-seed discovery ceiling from 12 to 50 clusters.
It keeps the five-focal-per-world-anchor cap, deterministically publishes the
first two clusters for every available needed action, fills each published
seed schedule to at least twelve clusters across at least three world anchors,
and selects the shortest passing prefix of the same fixed seed pool.

``generate`` is one-shot.  It reloads the sealed Main checkpoint and selected
schedules, invokes only the existing C2 generator and temporal-dataset writer,
and publishes TRAIN/C2 rows.  Neither phase opens validation/test bytes or
computes a target, validation metric, held-out EE value, or test result.
"""

from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_base_spec = importlib.util.spec_from_file_location(
    "c2_train_graph_expansion_v1_dependency",
    HERE / "run_v03_e1_c2_train_action_graph_expansion.py",
)
if _base_spec is None or _base_spec.loader is None:
    raise RuntimeError("cannot load the exhausted C2 expansion contract")
base = importlib.util.module_from_spec(_base_spec)
_base_spec.loader.exec_module(base)

source = base.source
wrapper = base.wrapper
E1C2PreOutcomeSchedule = base.E1C2PreOutcomeSchedule
load_e1_c2_schedule = base.load_e1_c2_schedule
seal_e1_c2_schedule = base.seal_e1_c2_schedule
read_temporal_dataset = base.read_temporal_dataset
write_temporal_dataset = base.write_temporal_dataset


AUTHORITY_SCHEMA = "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-authority-v2"
PREPARE_RESULT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-c2-train-action-balanced-expansion-prepare-result-v1"
)
# Keep the established consumer-facing final-result interface.  V3 rejects the
# failed v1 authority and admits this schema only when paired with v2 authority.
RESULT_SCHEMA = base.RESULT_SCHEMA
SEAL_SUFFIX = "-seal"
FAILED_AUTHORITY_SCHEMA = base.AUTHORITY_SCHEMA
FAILED_PREPARE_RESULT_SCHEMA = base.PREPARE_RESULT_SCHEMA
LEGAL_PROBE_SCHEMA = "multi-catfish-mcrl-v03-c2-action-balanced-topology-probe-v1"

CANDIDATE_SEED_ORDER = base.CANDIDATE_SEED_ORDER
MIN_CLUSTERS_PER_NEEDED_ACTION = base.MIN_CLUSTERS_PER_NEEDED_ACTION
MIN_SEEDS_PER_NEEDED_ACTION = base.MIN_SEEDS_PER_NEEDED_ACTION
CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED = 50
MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR = 5
ACTION_FIRST_CLUSTERS_PER_SEED = 2
PUBLISHED_MINIMUM_CLUSTERS_PER_SEED = 12
PUBLISHED_MINIMUM_WORLD_ANCHORS_PER_SEED = 3
FALSE_BOUNDARY = dict(base.FALSE_BOUNDARY)

BASE_EXPANSION_RUNNER = HERE / "run_v03_e1_c2_train_action_graph_expansion.py"
SOURCE_RUNNER = HERE / "run_v03_e1_action_shared_sources.py"
C2_SCHEDULE_HELPER = REPO / "src/mcrl/runtime/ee_axis_e1_c2_schedule.py"
TEMPORAL_DATASET_HELPER = REPO / "src/mcrl/runtime/ee_axis_temporal_dataset.py"

SEALED_FAILED_AUTHORITY_SHA256 = (
    "feaddcc8b5ada02cc09f8bedf56cb7f0823bf422031f9235a371c89c39140ffa"
)
SEALED_FAILED_AUTHORITY_SEAL_SHA256 = (
    "ea4f12b9efb6bcc361c9d3fa15a5116b8d72ac398aee6cdaa5659f0e3f4c3131"
)
SEALED_FAILED_PREPARE_RESULT_SHA256 = (
    "ffc9a2cb9b89413f9f4be70991f2b3aa978a9476251e8b0e30718f5d7392e87d"
)
SEALED_FAILED_PREPARE_RESULT_SEAL_SHA256 = (
    "055cf6be00221c355e2a03f70f36ca1b0b8822618ee5ee8983cd15c32072cdcd"
)
SEALED_LEGAL_PROBE_RECEIPT_SHA256 = (
    "265dec78460ac22b81159cf9dba968319ac2774642599c8d6eb5cc8a62643044"
)


# Reuse the audited error and graph logic so the unchanged redundancy gate is
# literally the same implementation used by the exhausted supplement.
C2ActionBalancedExpansionError = base.C2TrainGraphExpansionError
_digest = base._digest
_sha256 = base._sha256
_read_sealed = base._read_sealed
_coverage_report = base._coverage_report
_select_shortest_prefix = base._select_shortest_prefix


def _implementation_manifest() -> dict[str, str]:
    return {
        "formal_action_balanced_runner": _sha256(Path(__file__)),
        "exhausted_expansion_runner": _sha256(BASE_EXPANSION_RUNNER),
        "action_shared_source_runner": _sha256(SOURCE_RUNNER),
        "c2_preoutcome_schedule_helper": _sha256(C2_SCHEDULE_HELPER),
        "temporal_dataset_helper": _sha256(TEMPORAL_DATASET_HELPER),
    }


def _dependency_fields(authority: Mapping[str, Any]) -> dict[str, str]:
    fields = (
        "base_source_result_sha256",
        "base_source_result_seal_sha256",
        "independent_result_sha256",
        "independent_result_seal_sha256",
        "census_result_sha256",
        "census_result_seal_sha256",
    )
    return {field: _digest(authority.get(field), field=field) for field in fields}


def _authenticate_failed_expansion(
    root: Path,
    *,
    expected_authority_sha256: str,
    expected_authority_seal_sha256: str,
    expected_prepare_result_sha256: str,
    expected_prepare_result_seal_sha256: str,
) -> dict[str, Any]:
    """Authenticate the one exhausted supplement; never accept a GO receipt."""

    authority_sha256 = _digest(
        expected_authority_sha256, field="expected_failed_authority_sha256"
    )
    authority_seal_sha256 = _digest(
        expected_authority_seal_sha256,
        field="expected_failed_authority_seal_sha256",
    )
    prepare_sha256 = _digest(
        expected_prepare_result_sha256,
        field="expected_failed_prepare_result_sha256",
    )
    prepare_seal_sha256 = _digest(
        expected_prepare_result_seal_sha256,
        field="expected_failed_prepare_result_seal_sha256",
    )
    authority = _read_sealed(
        root / "authority.json", authority_sha256, label="failed_expansion_authority"
    )
    authority_seal = _read_sealed(
        root / "authority-seal.json",
        authority_seal_sha256,
        label="failed_expansion_authority_seal",
    )
    prepared = _read_sealed(
        root / "prepare-result.json",
        prepare_sha256,
        label="failed_expansion_prepare_result",
    )
    prepared_seal = _read_sealed(
        root / "prepare-result-seal.json",
        prepare_seal_sha256,
        label="failed_expansion_prepare_result_seal",
    )
    dependencies = _dependency_fields(authority)
    if (
        authority.get("schema") != FAILED_AUTHORITY_SCHEMA
        or authority.get("status")
        != "SEALED_BEFORE_SCHEDULE_TOPOLOGY_INSPECTION"
        or authority.get("scope")
        != "C2_TRAIN_ONLY_ACTION_GRAPH_COVERAGE_EXPANSION_ONCE"
        or authority.get("runner_file_sha256") != _sha256(BASE_EXPANSION_RUNNER)
        or authority.get("base_prereg_file_sha256") != _sha256(source.BASE_PREREG)
        or authority.get("candidate_seed_order") != list(CANDIDATE_SEED_ORDER)
        or authority.get("candidate_seed_partition") != "TRAIN"
        or authority.get("selection_rule")
        != "shortest-prefix-by-schedule-action-topology-only"
        or authority.get("minimum_clusters_per_needed_action")
        != MIN_CLUSTERS_PER_NEEDED_ACTION
        or authority.get("minimum_seeds_per_needed_action")
        != MIN_SEEDS_PER_NEEDED_ACTION
        or authority.get("replacement_seed_pool_authorized") is not False
        or authority.get("outcome_or_target_fields_permitted_in_prepare") is not False
        or any(authority.get(field) is not False for field in FALSE_BOUNDARY)
        or authority_seal.get("schema") != f"{FAILED_AUTHORITY_SCHEMA}{SEAL_SUFFIX}"
        or authority_seal.get("authority_sha256") != authority_sha256
        or prepared.get("schema") != FAILED_PREPARE_RESULT_SCHEMA
        or prepared.get("status") != "INSUFFICIENT_COVERAGE"
        or prepared.get("authority_sha256") != authority_sha256
        or prepared.get("candidate_seed_order") != list(CANDIDATE_SEED_ORDER)
        or prepared.get("selected_seed_order") != []
        or prepared.get("selected_schedule_file_sha256s") != {}
        or prepared.get("replacement_seed_pool_used") is not False
        or prepared.get("main_networks_bitwise_unchanged") is not True
        or prepared.get("main_replay_unchanged") is not True
        or prepared.get("generation_attempted") is not False
        or any(prepared.get(field) is not False for field in FALSE_BOUNDARY)
        or any(prepared.get(field) != value for field, value in dependencies.items())
        or prepared_seal.get("schema")
        != f"{FAILED_PREPARE_RESULT_SCHEMA}{SEAL_SUFFIX}"
        or prepared_seal.get("result_file_sha256") != prepare_sha256
        or prepared_seal.get("authority_sha256") != authority_sha256
    ):
        raise C2ActionBalancedExpansionError(
            "failed expansion authority/prepare closure is invalid"
        )

    inspected = prepared.get("all_inspected_schedule_file_sha256s")
    expected_keys = {str(seed) for seed in CANDIDATE_SEED_ORDER}
    if not isinstance(inspected, dict) or set(inspected) != expected_keys:
        raise C2ActionBalancedExpansionError(
            "failed expansion did not exhaust the one fixed seed pool"
        )
    for key, value in inspected.items():
        _digest(value, field=f"failed.all_inspected_schedule_file_sha256s.{key}")
    if any(
        (root / name).exists() or (root / name).is_symlink()
        for name in ("generation-attempt.json", "result.json", "result-seal.json")
    ) or (root / "temporal-datasets").exists():
        raise C2ActionBalancedExpansionError(
            "failed expansion unexpectedly materialized generated outcomes"
        )
    for field in (
        "temporal_datasets",
        "temporal_dataset_paths",
        "temporal_dataset_file_sha256s",
        "temporal_dataset_sha256s",
    ):
        if prepared.get(field) != {}:
            raise C2ActionBalancedExpansionError(
                "failed expansion prepare contains temporal dataset metadata"
            )

    graph = prepared.get("final_c2_graph_report")
    original_pairs = authority.get("original_unsupported_c2_pairs")
    if not isinstance(original_pairs, list):
        raise C2ActionBalancedExpansionError("failed expansion pairs are malformed")
    needed_actions = sorted(
        {
            int(action)
            for pair in original_pairs
            if isinstance(pair, dict)
            for action in (pair.get("reference_action"), pair.get("candidate_action"))
            if type(action) is int
        }
    )
    if not isinstance(graph, dict):
        raise C2ActionBalancedExpansionError("failed expansion graph is absent")
    evidence = graph.get("needed_action_evidence")
    if (
        graph.get("decision_basis") != "schedule-action-topology-only"
        or graph.get("original_unsupported_validation_action_pairs") != original_pairs
        or graph.get("remaining_unsupported_validation_action_pairs") != []
        or graph.get("needed_actions") != needed_actions
        or graph.get("minimum_clusters_per_needed_action")
        != MIN_CLUSTERS_PER_NEEDED_ACTION
        or graph.get("minimum_seeds_per_needed_action")
        != MIN_SEEDS_PER_NEEDED_ACTION
        or graph.get("coverage_sufficient") is not False
        or graph.get("target_or_outcome_values_used_for_coverage_decision") is not False
        or graph.get("generated_outcomes_materialized") is not False
        or not isinstance(evidence, dict)
        or set(evidence) != {str(action) for action in needed_actions}
    ):
        raise C2ActionBalancedExpansionError(
            "failed expansion was not the sealed connectivity-only redundancy failure"
        )
    cluster_gate_failed = False
    for action in needed_actions:
        row = evidence[str(action)]
        if not isinstance(row, dict):
            raise C2ActionBalancedExpansionError("failed action evidence is malformed")
        clusters = row.get("clusters")
        seeds = row.get("seeds")
        if (
            type(clusters) is not int
            or clusters < 0
            or not isinstance(seeds, list)
            or any(type(seed) is not int or seed not in CANDIDATE_SEED_ORDER for seed in seeds)
            or len(set(seeds)) != len(seeds)
            or row.get("meets_minimum_clusters")
            is not (clusters >= MIN_CLUSTERS_PER_NEEDED_ACTION)
            or row.get("meets_minimum_seeds")
            is not (len(seeds) >= MIN_SEEDS_PER_NEEDED_ACTION)
            or row.get("meets_minimum_seeds") is not True
        ):
            raise C2ActionBalancedExpansionError(
                "failed expansion redundancy evidence is malformed"
            )
        cluster_gate_failed |= row.get("meets_minimum_clusters") is False
    if not cluster_gate_failed:
        raise C2ActionBalancedExpansionError(
            "failed expansion did not fail the unchanged cluster-redundancy gate"
        )
    return {
        "authority": authority,
        "prepared": prepared,
        "authority_sha256": authority_sha256,
        "authority_seal_sha256": authority_seal_sha256,
        "prepare_result_sha256": prepare_sha256,
        "prepare_result_seal_sha256": prepare_seal_sha256,
        "dependencies": dependencies,
    }


def _authenticate_legal_probe(
    path: Path,
    expected_sha256: str,
    *,
    needed_actions: Sequence[int],
) -> dict[str, Any]:
    expected = _digest(
        expected_sha256, field="expected_legal_action_balanced_probe_sha256"
    )
    if _sha256(path) != expected:
        raise C2ActionBalancedExpansionError("legal topology probe bytes changed")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise C2ActionBalancedExpansionError(
                    f"legal topology probe repeats JSON key {key!r}"
                )
            payload[key] = value
        return payload

    def reject_nonfinite(value: str) -> object:
        raise C2ActionBalancedExpansionError(
            f"legal topology probe contains non-finite value {value!r}"
        )

    try:
        receipt = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise C2ActionBalancedExpansionError(
            "legal topology probe is not a strict JSON document"
        ) from error
    if not isinstance(receipt, dict):
        raise C2ActionBalancedExpansionError("legal topology probe is not an object")
    evidence = receipt.get("needed_action_evidence")
    receipts = receipt.get("receipts")
    if (
        receipt.get("schema") != LEGAL_PROBE_SCHEMA
        or receipt.get("status") != "DESIGN_DIAGNOSTIC_ONLY"
        or receipt.get("source_seeds") != list(CANDIDATE_SEED_ORDER)
        or receipt.get("maximum_focal_users_per_world_anchor")
        != MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR
        or receipt.get("maximum_scheduled_clusters_per_seed")
        != CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED
        or receipt.get("target_values_read") is not False
        or receipt.get("pair_outcomes_materialized") is not False
        or receipt.get("validation_dataset_documents_opened") is not False
        or receipt.get("test_split_opened") is not False
        or receipt.get("held_out_ee_evaluated") is not False
        or not isinstance(evidence, dict)
        or set(evidence) != {str(action) for action in needed_actions}
        or not isinstance(receipts, list)
        or len(receipts) != len(CANDIDATE_SEED_ORDER)
        or [row.get("source_seed") for row in receipts if isinstance(row, dict)]
        != list(CANDIDATE_SEED_ORDER)
    ):
        raise C2ActionBalancedExpansionError(
            "legal topology probe receipt is invalid or not the fixed-pool cap-50 probe"
        )
    for action in needed_actions:
        row = evidence[str(action)]
        if not isinstance(row, dict):
            raise C2ActionBalancedExpansionError("legal probe action evidence is malformed")
        clusters = row.get("clusters")
        seeds = row.get("seeds")
        if (
            type(clusters) is not int
            or clusters < MIN_CLUSTERS_PER_NEEDED_ACTION
            or not isinstance(seeds, list)
            or len(set(seeds)) < MIN_SEEDS_PER_NEEDED_ACTION
            or any(type(seed) is not int or seed not in CANDIDATE_SEED_ORDER for seed in seeds)
        ):
            raise C2ActionBalancedExpansionError(
                "legal probe does not support the unchanged redundancy gate"
            )
    return receipt


def _authenticate_inputs(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    failed_expansion_root: Path,
    legal_probe_receipt: Path,
    expected_failed_authority_sha256: str,
    expected_failed_authority_seal_sha256: str,
    expected_failed_prepare_result_sha256: str,
    expected_failed_prepare_result_seal_sha256: str,
    expected_legal_probe_receipt_sha256: str,
) -> dict[str, Any]:
    failed = _authenticate_failed_expansion(
        failed_expansion_root,
        expected_authority_sha256=expected_failed_authority_sha256,
        expected_authority_seal_sha256=expected_failed_authority_seal_sha256,
        expected_prepare_result_sha256=expected_failed_prepare_result_sha256,
        expected_prepare_result_seal_sha256=expected_failed_prepare_result_seal_sha256,
    )
    authenticated = base._authenticate_inputs(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        expected_base_source_result_sha256=failed["dependencies"][
            "base_source_result_sha256"
        ],
        expected_base_source_result_seal_sha256=failed["dependencies"][
            "base_source_result_seal_sha256"
        ],
        expected_independent_result_sha256=failed["dependencies"][
            "independent_result_sha256"
        ],
        expected_independent_result_seal_sha256=failed["dependencies"][
            "independent_result_seal_sha256"
        ],
        expected_census_result_sha256=failed["dependencies"]["census_result_sha256"],
        expected_census_result_seal_sha256=failed["dependencies"][
            "census_result_seal_sha256"
        ],
    )
    failed_authority = failed["authority"]
    if (
        failed_authority.get("base_source_receipt_sha256")
        != authenticated["source_receipt_sha256"]
        or failed_authority.get("base_source_control_file_sha256s")
        != authenticated["source_control_file_sha256s"]
        or failed_authority.get("source_prereg_sha256")
        != authenticated["prereg"].get("prereg_sha256")
        or failed_authority.get("source_manifest_sha256")
        != authenticated["prereg"].get("source_manifest_sha256")
        or failed_authority.get("checkpoint_sha256")
        != authenticated["prereg"].get("checkpoint_sha256")
        or failed_authority.get("environment_source_sha256")
        != authenticated["prereg"].get("environment_source_sha256")
        or failed_authority.get("reward_source_sha256")
        != authenticated["prereg"].get("reward_source_sha256")
        or failed_authority.get("original_c2_components")
        != [list(row) for row in authenticated["components"]]
        or failed_authority.get("original_unsupported_c2_pairs")
        != [
            {"reference_action": pair[0], "candidate_action": pair[1]}
            for pair in authenticated["unsupported_pairs"]
        ]
    ):
        raise C2ActionBalancedExpansionError(
            "failed expansion is not cross-bound to the current 4/3/0 source and census"
        )
    needed_actions = sorted(
        {action for pair in authenticated["unsupported_pairs"] for action in pair}
    )
    legal_probe = _authenticate_legal_probe(
        legal_probe_receipt,
        expected_legal_probe_receipt_sha256,
        needed_actions=needed_actions,
    )
    return {
        **authenticated,
        "failed_expansion": failed,
        "legal_probe": legal_probe,
        "needed_actions": tuple(needed_actions),
    }


def _cluster_topology(
    cluster: object, *, expected_seed: int
) -> tuple[tuple[int, int, str], str, int, int, object]:
    identity, reference, candidate = base._cluster_fields(
        cluster, expected_seed=expected_seed
    )
    if isinstance(cluster, Mapping):
        anchor = cluster.get("world_anchor_sha256")
        anchor_step = cluster.get("anchor_step")
        focal_user = cluster.get("focal_user")
    else:
        anchor = getattr(cluster, "world_anchor_sha256", None)
        anchor_step = getattr(cluster, "anchor_step", None)
        focal_user = getattr(cluster, "focal_user", None)
    if (
        not isinstance(anchor, str)
        or not anchor
        or type(anchor_step) is not int
        or anchor_step < 0
        or type(focal_user) is not int
        or focal_user < 0
    ):
        raise C2ActionBalancedExpansionError(
            "candidate schedule world-anchor or focal identity is malformed"
        )
    return (anchor_step, focal_user, identity), anchor, reference, candidate, cluster


def _select_action_balanced_clusters(
    *,
    source_seed: int,
    clusters: Iterable[object],
    needed_actions: Sequence[int],
) -> tuple[tuple[object, ...], dict[str, Any]]:
    """Select target-free clusters deterministically from one cap-50 schedule."""

    records = sorted(
        (_cluster_topology(cluster, expected_seed=source_seed) for cluster in clusters),
        key=lambda row: row[0],
    )
    if not records or len(records) > CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED:
        raise C2ActionBalancedExpansionError(
            "INSUFFICIENT_COVERAGE: candidate seed schedule is empty or exceeds cap 50"
        )
    identities = [record[0][2] for record in records]
    if len(set(identities)) != len(identities):
        raise C2ActionBalancedExpansionError("duplicate candidate cluster identity")
    anchor_counts = Counter(record[1] for record in records)
    if any(count > MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR for count in anchor_counts.values()):
        raise C2ActionBalancedExpansionError(
            "candidate schedule exceeds the sealed five-focal world-anchor cap"
        )

    selected_identities: set[str] = set()
    action_receipts: dict[str, dict[str, Any]] = {}
    for action in sorted(set(needed_actions)):
        matches = [
            record
            for record in records
            if action in (record[2], record[3])
        ]
        chosen = matches[:ACTION_FIRST_CLUSTERS_PER_SEED]
        selected_identities.update(record[0][2] for record in chosen)
        action_receipts[str(action)] = {
            "available_clusters": len(matches),
            "selected_first_cluster_sha256s": [record[0][2] for record in chosen],
            "per_seed_quota": ACTION_FIRST_CLUSTERS_PER_SEED,
            "quota_filled_when_available": len(chosen)
            == min(ACTION_FIRST_CLUSTERS_PER_SEED, len(matches)),
        }

    def selection_state() -> tuple[int, set[str]]:
        selected = [record for record in records if record[0][2] in selected_identities]
        return len(selected), {record[1] for record in selected}

    for record in records:
        count, anchors = selection_state()
        if (
            count >= PUBLISHED_MINIMUM_CLUSTERS_PER_SEED
            and len(anchors) >= PUBLISHED_MINIMUM_WORLD_ANCHORS_PER_SEED
        ):
            break
        selected_identities.add(record[0][2])
    count, selected_anchors = selection_state()
    if (
        count < PUBLISHED_MINIMUM_CLUSTERS_PER_SEED
        or len(selected_anchors) < PUBLISHED_MINIMUM_WORLD_ANCHORS_PER_SEED
    ):
        raise C2ActionBalancedExpansionError(
            "INSUFFICIENT_COVERAGE: seed cannot publish 12 clusters across 3 world anchors"
        )
    selected_records = [
        record for record in records if record[0][2] in selected_identities
    ]
    selected_anchor_counts = Counter(record[1] for record in selected_records)
    if any(
        count > MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR
        for count in selected_anchor_counts.values()
    ):
        raise C2ActionBalancedExpansionError("published schedule violates focal cap")
    return tuple(record[4] for record in selected_records), {
        "source_seed": source_seed,
        "decision_basis": "schedule-action-and-world-anchor-topology-only",
        "candidate_clusters": len(records),
        "candidate_world_anchors": len(anchor_counts),
        "selected_clusters": len(selected_records),
        "selected_world_anchors": len(selected_anchor_counts),
        "selected_cluster_sha256s": [record[0][2] for record in selected_records],
        "action_selection_evidence": action_receipts,
        "target_or_outcome_values_used": False,
    }


def _select_action_balanced_schedule(
    schedule: E1C2PreOutcomeSchedule,
    *,
    needed_actions: Sequence[int],
) -> tuple[E1C2PreOutcomeSchedule, dict[str, Any]]:
    schedule.verify()
    selected, receipt = _select_action_balanced_clusters(
        source_seed=schedule.source_seed,
        clusters=schedule.clusters,
        needed_actions=needed_actions,
    )
    published = E1C2PreOutcomeSchedule(
        source_seed=schedule.source_seed,
        clusters=tuple(selected),
        policy_sha256=schedule.policy_sha256,
        source_manifest_sha256=schedule.source_manifest_sha256,
        checkpoint_sha256=schedule.checkpoint_sha256,
        policy_version=schedule.policy_version,
        horizon_offsets=schedule.horizon_offsets,
    )
    published.verify()
    return published, receipt


def _failed_digest_fields(failed: Mapping[str, Any]) -> dict[str, str]:
    return {
        "failed_expansion_authority_sha256": failed["authority_sha256"],
        "failed_expansion_authority_seal_sha256": failed["authority_seal_sha256"],
        "failed_expansion_prepare_result_sha256": failed["prepare_result_sha256"],
        "failed_expansion_prepare_result_seal_sha256": failed[
            "prepare_result_seal_sha256"
        ],
    }


def _sealed_receipt_digests() -> dict[str, str]:
    return {
        "failed_expansion_authority_sha256": SEALED_FAILED_AUTHORITY_SHA256,
        "failed_expansion_authority_seal_sha256": (
            SEALED_FAILED_AUTHORITY_SEAL_SHA256
        ),
        "failed_expansion_prepare_result_sha256": (
            SEALED_FAILED_PREPARE_RESULT_SHA256
        ),
        "failed_expansion_prepare_result_seal_sha256": (
            SEALED_FAILED_PREPARE_RESULT_SEAL_SHA256
        ),
        "legal_probe_receipt_file_sha256": SEALED_LEGAL_PROBE_RECEIPT_SHA256,
    }


def prepare(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    failed_expansion_root: Path,
    legal_probe_receipt: Path,
    output_dir: Path,
    tle_root: Path,
    expected_failed_authority_sha256: str,
    expected_failed_authority_seal_sha256: str,
    expected_failed_prepare_result_sha256: str,
    expected_failed_prepare_result_seal_sha256: str,
    expected_legal_probe_receipt_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to reuse one-shot action-balanced directory")
    source_resolved = source_root.resolve(strict=True)
    failed_resolved = failed_expansion_root.resolve(strict=True)
    output_resolved = output_dir.resolve(strict=False)
    if any(
        output_resolved == root or output_resolved.is_relative_to(root)
        for root in (source_resolved, failed_resolved)
    ):
        raise C2ActionBalancedExpansionError(
            "redesign output must be outside immutable source and failed-expansion roots"
        )
    supplied_receipts = {
        "failed_expansion_authority_sha256": expected_failed_authority_sha256,
        "failed_expansion_authority_seal_sha256": (
            expected_failed_authority_seal_sha256
        ),
        "failed_expansion_prepare_result_sha256": (
            expected_failed_prepare_result_sha256
        ),
        "failed_expansion_prepare_result_seal_sha256": (
            expected_failed_prepare_result_seal_sha256
        ),
        "legal_probe_receipt_file_sha256": expected_legal_probe_receipt_sha256,
    }
    if supplied_receipts != _sealed_receipt_digests():
        raise C2ActionBalancedExpansionError(
            "operator-supplied failed-expansion/probe digests are not the formal inputs"
        )
    authenticated = _authenticate_inputs(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        failed_expansion_root=failed_expansion_root,
        legal_probe_receipt=legal_probe_receipt,
        expected_failed_authority_sha256=expected_failed_authority_sha256,
        expected_failed_authority_seal_sha256=expected_failed_authority_seal_sha256,
        expected_failed_prepare_result_sha256=expected_failed_prepare_result_sha256,
        expected_failed_prepare_result_seal_sha256=(
            expected_failed_prepare_result_seal_sha256
        ),
        expected_legal_probe_receipt_sha256=expected_legal_probe_receipt_sha256,
    )
    if set(CANDIDATE_SEED_ORDER).intersection(wrapper.BURNED_SOURCE_SEEDS):
        raise C2ActionBalancedExpansionError("fixed redesign pool overlaps burned seeds")
    if source.C2_MAX_FOCAL_USERS_PER_ANCHOR != MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR:
        raise C2ActionBalancedExpansionError("binding focal-user cap changed")

    prereg = authenticated["prereg"]
    source_manifest_sha256 = _digest(
        prereg.get("source_manifest_sha256"), field="source_manifest_sha256"
    )
    checkpoint_sha256 = _digest(
        prereg.get("checkpoint_sha256"), field="checkpoint_sha256"
    )
    environment_source_sha256 = _digest(
        prereg.get("environment_source_sha256"), field="environment_source_sha256"
    )
    reward_source_sha256 = _digest(
        prereg.get("reward_source_sha256"), field="reward_source_sha256"
    )
    base_record = source.read_prereg(source.BASE_PREREG)
    multiplier, interval_s = base._sealed_formula_constants(prereg, base_record)
    failed = authenticated["failed_expansion"]
    dependency_digests = failed["dependencies"]
    implementation_manifest = _implementation_manifest()

    output_dir.mkdir(parents=True)
    authority = {
        "schema": AUTHORITY_SCHEMA,
        "status": "SEALED_BEFORE_SCHEDULE_TOPOLOGY_INSPECTION",
        "scope": "C2_TRAIN_ONLY_ACTION_BALANCED_SOURCE_REDESIGN_ONCE",
        "change_class": "SOURCE_SELECTOR_REDESIGN_NOT_THRESHOLD_AMENDMENT",
        "bounded_supplement_status": (
            "EXHAUSTED_CONNECTIVITY_RESTORED_REDUNDANCY_UNMET"
        ),
        "runner_file_sha256": implementation_manifest[
            "formal_action_balanced_runner"
        ],
        "implementation_file_sha256s": implementation_manifest,
        **dependency_digests,
        **_failed_digest_fields(failed),
        "failed_expansion_root_supplied": str(failed_resolved),
        "legal_probe_receipt_file_sha256": _digest(
            expected_legal_probe_receipt_sha256,
            field="expected_legal_probe_receipt_sha256",
        ),
        "legal_probe_receipt_path_supplied": str(
            legal_probe_receipt.resolve(strict=True)
        ),
        "legal_probe_needed_action_evidence": authenticated["legal_probe"][
            "needed_action_evidence"
        ],
        "base_source_receipt_sha256": authenticated["source_receipt_sha256"],
        "base_source_control_file_sha256s": authenticated[
            "source_control_file_sha256s"
        ],
        "base_prereg_file_sha256": _sha256(source.BASE_PREREG),
        "tle_root_supplied": str(tle_root.resolve(strict=True)),
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": source_manifest_sha256,
        "checkpoint_sha256": checkpoint_sha256,
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "lambda_bits_per_j_hex": multiplier.hex(),
        "interval_s_hex": interval_s.hex(),
        "candidate_seed_order": list(CANDIDATE_SEED_ORDER),
        "candidate_seed_partition": "TRAIN",
        "selection_rule": (
            "shortest-prefix-of-deterministic-action-balanced-train-schedules-"
            "by-action-topology-only"
        ),
        "candidate_schedule_maximum_clusters_per_seed": (
            CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED
        ),
        "maximum_focal_users_per_world_anchor": (
            MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR
        ),
        "action_first_clusters_per_needed_action_per_seed": (
            ACTION_FIRST_CLUSTERS_PER_SEED
        ),
        "published_schedule_minimum_clusters_per_seed": (
            PUBLISHED_MINIMUM_CLUSTERS_PER_SEED
        ),
        "published_schedule_minimum_world_anchors_per_seed": (
            PUBLISHED_MINIMUM_WORLD_ANCHORS_PER_SEED
        ),
        "minimum_clusters_per_needed_action": MIN_CLUSTERS_PER_NEEDED_ACTION,
        "minimum_seeds_per_needed_action": MIN_SEEDS_PER_NEEDED_ACTION,
        "replacement_seed_pool_authorized": False,
        "second_seed_pool_authorized": False,
        "original_c2_components": [list(row) for row in authenticated["components"]],
        "original_unsupported_c2_pairs": [
            {"reference_action": pair[0], "candidate_action": pair[1]}
            for pair in authenticated["unsupported_pairs"]
        ],
        "outcome_or_target_fields_permitted_in_prepare": False,
        **FALSE_BOUNDARY,
    }
    authority_sha256 = source._write_once_json(output_dir / "authority.json", authority)
    source._write_once_json(
        output_dir / "authority-seal.json",
        {
            "schema": f"{AUTHORITY_SCHEMA}{SEAL_SUFFIX}",
            "authority_sha256": authority_sha256,
        },
    )

    schedules: dict[int, E1C2PreOutcomeSchedule] = {}
    candidate_schedule_hashes: dict[str, str] = {}
    schedule_hashes: dict[str, str] = {}
    discovery_receipts: list[dict[str, Any]] = []
    selection_receipts: list[dict[str, Any]] = []
    selected: tuple[int, ...] = ()
    report: dict[str, Any] | None = None
    original_cluster_cap = source.C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED
    source.C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED = (
        CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED
    )
    try:
        with tempfile.TemporaryDirectory(
            prefix="mcrl-c2-action-balanced-prepare-"
        ) as temporary:
            archive = source.c2_probe._frozen_archive(
                base_record, tle_root, Path(temporary) / "frozen-tle"
            )
            trainer, checkpoint = source.loader._verify_and_load_trainer(
                base_record,
                archive,
                run_dir=source.BASE_CHECKPOINT_DIR,
                users=source.USERS,
            )
            if checkpoint.get("checkpoint_sha256") != checkpoint_sha256:
                raise C2ActionBalancedExpansionError(
                    "loaded Main differs from sealed source authority"
                )
            network_before = source.c2_backend_smoke._network_snapshot(trainer)
            replay_before = len(trainer.replay)
            for seed in CANDIDATE_SEED_ORDER:
                try:
                    candidate_schedule, discovery = source._discover_c2_schedule(
                        trainer=trainer,
                        archive=archive,
                        seed=seed,
                        prereg_sha256=prereg["prereg_sha256"],
                        source_manifest_sha256=source_manifest_sha256,
                        checkpoint_sha256=checkpoint_sha256,
                        environment_source_sha256=environment_source_sha256,
                        reward_source_sha256=reward_source_sha256,
                    )
                except source.E1FreshSourceError as error:
                    if not str(error).startswith("INSUFFICIENT_COVERAGE:"):
                        raise
                    discovery_receipts.append(
                        {
                            "source_seed": seed,
                            "status": "INSUFFICIENT_CANDIDATE_SCHEDULE",
                            "reason": str(error),
                            "forecast_outcomes_read": False,
                        }
                    )
                    break
                discovery_receipts.append(discovery)
                candidate_schedule_hashes[str(seed)] = seal_e1_c2_schedule(
                    output_dir / "candidate-schedules" / f"c2-{seed}.json",
                    candidate_schedule,
                    source_seed=seed,
                    policy_sha256=source._policy_sha256(),
                    source_manifest_sha256=source_manifest_sha256,
                    checkpoint_sha256=checkpoint_sha256,
                )
                try:
                    schedule, selection = _select_action_balanced_schedule(
                        candidate_schedule,
                        needed_actions=authenticated["needed_actions"],
                    )
                except C2ActionBalancedExpansionError as error:
                    if not str(error).startswith("INSUFFICIENT_COVERAGE:"):
                        raise
                    selection_receipts.append(
                        {
                            "source_seed": seed,
                            "status": "INSUFFICIENT_PUBLISHED_SCHEDULE",
                            "reason": str(error),
                            "target_or_outcome_values_used": False,
                        }
                    )
                    break
                selection_receipts.append(selection)
                schedules[seed] = schedule
                schedule_hashes[str(seed)] = seal_e1_c2_schedule(
                    output_dir / "schedules" / f"c2-{seed}.json",
                    schedule,
                    source_seed=seed,
                    policy_sha256=source._policy_sha256(),
                    source_manifest_sha256=source_manifest_sha256,
                    checkpoint_sha256=checkpoint_sha256,
                )
                selected, report = _select_shortest_prefix(
                    action_dim=authenticated["action_dim"],
                    original_components=authenticated["components"],
                    unsupported_pairs=authenticated["unsupported_pairs"],
                    schedules={key: value.clusters for key, value in schedules.items()},
                )
                if selected:
                    break
            if not source.c2_backend_smoke._networks_equal(trainer, network_before):
                raise C2ActionBalancedExpansionError(
                    "action-balanced schedule discovery mutated Main networks"
                )
            if len(trainer.replay) != replay_before:
                raise C2ActionBalancedExpansionError(
                    "action-balanced schedule discovery wrote Main replay"
                )
    finally:
        source.C2_MAXIMUM_SCHEDULED_CLUSTERS_PER_SEED = original_cluster_cap
    if report is None:
        report = _coverage_report(
            action_dim=authenticated["action_dim"],
            original_components=authenticated["components"],
            unsupported_pairs=authenticated["unsupported_pairs"],
            clusters_by_seed={},
        )
    status = "READY_FOR_ONE_TIME_GENERATION" if selected else "INSUFFICIENT_COVERAGE"
    result = {
        "schema": PREPARE_RESULT_SCHEMA,
        "status": status,
        "authority_sha256": authority_sha256,
        **dependency_digests,
        **_failed_digest_fields(failed),
        "legal_probe_receipt_file_sha256": authority[
            "legal_probe_receipt_file_sha256"
        ],
        "selected_seed_order": list(selected),
        "selected_schedule_file_sha256s": {
            str(seed): schedule_hashes[str(seed)] for seed in selected
        },
        "all_inspected_candidate_schedule_file_sha256s": candidate_schedule_hashes,
        "all_inspected_schedule_file_sha256s": schedule_hashes,
        "temporal_datasets": {},
        "temporal_dataset_paths": {},
        "temporal_dataset_file_sha256s": {},
        "temporal_dataset_sha256s": {},
        "final_c2_graph_report": report,
        "schedule_discovery_receipts": discovery_receipts,
        "action_balanced_selection_receipts": selection_receipts,
        "candidate_seed_order": list(CANDIDATE_SEED_ORDER),
        "candidate_schedule_maximum_clusters_per_seed": (
            CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED
        ),
        "maximum_focal_users_per_world_anchor": (
            MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR
        ),
        "replacement_seed_pool_used": False,
        "second_seed_pool_used": False,
        "main_networks_bitwise_unchanged": True,
        "main_replay_unchanged": True,
        "generation_attempted": False,
        **FALSE_BOUNDARY,
    }
    result_sha256 = source._write_once_json(output_dir / "prepare-result.json", result)
    result_seal_sha256 = source._write_once_json(
        output_dir / "prepare-result-seal.json",
        {
            "schema": f"{PREPARE_RESULT_SCHEMA}{SEAL_SUFFIX}",
            "result_file_sha256": result_sha256,
            "authority_sha256": authority_sha256,
        },
    )
    return {
        **result,
        "result_file_sha256": result_sha256,
        "result_seal_file_sha256": result_seal_sha256,
    }


def _load_prepare(output_dir: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    authority_path = output_dir / "authority.json"
    authority = source._read_canonical_json(authority_path)
    authority_sha256 = _sha256(authority_path)
    authority_seal = source._read_canonical_json(output_dir / "authority-seal.json")
    result_path = output_dir / "prepare-result.json"
    result = source._read_canonical_json(result_path)
    result_seal = source._read_canonical_json(output_dir / "prepare-result-seal.json")
    if (
        authority.get("schema") != AUTHORITY_SCHEMA
        or authority_seal.get("schema") != f"{AUTHORITY_SCHEMA}{SEAL_SUFFIX}"
        or authority_seal.get("authority_sha256") != authority_sha256
        or result.get("schema") != PREPARE_RESULT_SCHEMA
        or result.get("authority_sha256") != authority_sha256
        or result_seal.get("schema") != f"{PREPARE_RESULT_SCHEMA}{SEAL_SUFFIX}"
        or result_seal.get("result_file_sha256") != _sha256(result_path)
        or result_seal.get("authority_sha256") != authority_sha256
    ):
        raise C2ActionBalancedExpansionError(
            "action-balanced prepare authority/result/seals are invalid"
        )
    return authority, result, authority_sha256


def _result_payload(
    *,
    status: str,
    authority_sha256: str,
    authority: Mapping[str, Any],
    selected: Sequence[int],
    schedule_hashes: Mapping[str, str],
    temporal_datasets: Mapping[str, Mapping[str, Any]],
    graph_report: Mapping[str, Any],
    generation_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    temporal = {str(seed): dict(row) for seed, row in temporal_datasets.items()}
    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "completion_status": status,
        "authority_sha256": authority_sha256,
        **{field: authority[field] for field in _dependency_fields(authority)},
        **{
            field: authority[field]
            for field in (
                "failed_expansion_authority_sha256",
                "failed_expansion_authority_seal_sha256",
                "failed_expansion_prepare_result_sha256",
                "failed_expansion_prepare_result_seal_sha256",
                "legal_probe_receipt_file_sha256",
            )
        },
        "base_source_receipt_sha256": authority["base_source_receipt_sha256"],
        "source_prereg_sha256": authority["source_prereg_sha256"],
        "source_manifest_sha256": authority["source_manifest_sha256"],
        "checkpoint_sha256": authority["checkpoint_sha256"],
        "environment_source_sha256": authority["environment_source_sha256"],
        "reward_source_sha256": authority["reward_source_sha256"],
        "lambda_bits_per_j_hex": authority["lambda_bits_per_j_hex"],
        "interval_s_hex": authority["interval_s_hex"],
        "selected_seed_order": list(selected),
        "selected_schedule_file_sha256s": dict(schedule_hashes),
        "temporal_datasets": temporal,
        "temporal_dataset_paths": {seed: row["path"] for seed, row in temporal.items()},
        "temporal_dataset_file_sha256s": {
            seed: row["file_sha256"] for seed, row in temporal.items()
        },
        "temporal_dataset_sha256s": {
            seed: row["dataset_sha256"] for seed, row in temporal.items()
        },
        "final_c2_graph_report": dict(graph_report),
        "generation_receipts": list(generation_receipts),
        "source_partition": "TRAIN",
        "held_out": False,
        "replacement_seed_pool_used": False,
        "second_seed_pool_used": False,
        "targets_or_validation_metrics_computed": False,
        **FALSE_BOUNDARY,
    }


def generate(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    failed_expansion_root: Path,
    legal_probe_receipt: Path,
    output_dir: Path,
    tle_root: Path,
) -> dict[str, Any]:
    authority, prepared, authority_sha256 = _load_prepare(output_dir)
    if (
        authority.get("runner_file_sha256") != _sha256(Path(__file__))
        or authority.get("implementation_file_sha256s") != _implementation_manifest()
        or authority.get("base_prereg_file_sha256") != _sha256(source.BASE_PREREG)
        or authority.get("tle_root_supplied") != str(tle_root.resolve(strict=True))
        or authority.get("failed_expansion_root_supplied")
        != str(failed_expansion_root.resolve(strict=True))
        or authority.get("legal_probe_receipt_path_supplied")
        != str(legal_probe_receipt.resolve(strict=True))
        or any(
            authority.get(field) != value
            for field, value in _sealed_receipt_digests().items()
        )
    ):
        raise C2ActionBalancedExpansionError(
            "runner/helper/base-prereg/TLE or dependency paths changed after prepare"
        )
    if prepared.get("status") != "READY_FOR_ONE_TIME_GENERATION":
        raise C2ActionBalancedExpansionError("prepare did not authorize generation")
    attempt_path = output_dir / "generation-attempt.json"
    if attempt_path.exists() or attempt_path.is_symlink() or (output_dir / "result.json").exists():
        raise FileExistsError("action-balanced C2 generation was already attempted")
    selected = tuple(prepared.get("selected_seed_order", ()))
    if not selected or selected != CANDIDATE_SEED_ORDER[: len(selected)]:
        raise C2ActionBalancedExpansionError(
            "prepared selection is not the fixed-pool shortest prefix"
        )
    schedule_hashes = prepared.get("selected_schedule_file_sha256s")
    if not isinstance(schedule_hashes, dict) or set(schedule_hashes) != {
        str(seed) for seed in selected
    }:
        raise C2ActionBalancedExpansionError("prepared selected schedules are incomplete")

    reauthenticated = _authenticate_inputs(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        failed_expansion_root=failed_expansion_root,
        legal_probe_receipt=legal_probe_receipt,
        expected_failed_authority_sha256=authority[
            "failed_expansion_authority_sha256"
        ],
        expected_failed_authority_seal_sha256=authority[
            "failed_expansion_authority_seal_sha256"
        ],
        expected_failed_prepare_result_sha256=authority[
            "failed_expansion_prepare_result_sha256"
        ],
        expected_failed_prepare_result_seal_sha256=authority[
            "failed_expansion_prepare_result_seal_sha256"
        ],
        expected_legal_probe_receipt_sha256=authority[
            "legal_probe_receipt_file_sha256"
        ],
    )
    if (
        reauthenticated["source_control_file_sha256s"]
        != authority.get("base_source_control_file_sha256s")
        or reauthenticated["failed_expansion"]["dependencies"]
        != _dependency_fields(authority)
    ):
        raise C2ActionBalancedExpansionError(
            "source or failed-expansion closure changed after prepare"
        )
    source._write_once_json(
        attempt_path,
        {
            "schema": f"{RESULT_SCHEMA}-action-balanced-generation-attempt-v1",
            "status": "STARTED_ONCE",
            "authority_sha256": authority_sha256,
            "selected_seed_order": list(selected),
            **FALSE_BOUNDARY,
        },
    )

    source_manifest_sha256 = _digest(
        authority.get("source_manifest_sha256"), field="source_manifest_sha256"
    )
    checkpoint_sha256 = _digest(
        authority.get("checkpoint_sha256"), field="checkpoint_sha256"
    )
    environment_source_sha256 = _digest(
        authority.get("environment_source_sha256"), field="environment_source_sha256"
    )
    reward_source_sha256 = _digest(
        authority.get("reward_source_sha256"), field="reward_source_sha256"
    )
    prereg = source._read_canonical_json(source_root / "prereg.json")
    if prereg.get("prereg_sha256") != authority.get("source_prereg_sha256"):
        raise C2ActionBalancedExpansionError("source prereg changed after prepare")
    schedules = {
        seed: load_e1_c2_schedule(
            output_dir / "schedules" / f"c2-{seed}.json",
            expected_file_sha256=schedule_hashes[str(seed)],
            source_seed=seed,
            policy_sha256=source._policy_sha256(),
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
        )
        for seed in selected
    }

    temporal_meta: dict[str, dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    final_clusters: dict[int, list[dict[str, Any]]] = {}
    generation_insufficient_reason: str | None = None
    base_record = source.read_prereg(source.BASE_PREREG)
    with tempfile.TemporaryDirectory(
        prefix="mcrl-c2-action-balanced-generate-"
    ) as temporary:
        archive = source.c2_probe._frozen_archive(
            base_record, tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = source.loader._verify_and_load_trainer(
            base_record,
            archive,
            run_dir=source.BASE_CHECKPOINT_DIR,
            users=source.USERS,
        )
        if checkpoint.get("checkpoint_sha256") != checkpoint_sha256:
            raise C2ActionBalancedExpansionError(
                "loaded Main differs from sealed redesign authority"
            )
        networks_before = source.c2_backend_smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)
        try:
            multiplier = float.fromhex(authority["lambda_bits_per_j_hex"])
            interval_s = float.fromhex(authority["interval_s_hex"])
        except (KeyError, TypeError, ValueError) as error:
            raise C2ActionBalancedExpansionError(
                "sealed source formula constants are malformed"
            ) from error
        if (
            not math.isfinite(multiplier)
            or not math.isfinite(interval_s)
            or multiplier <= 0.0
            or interval_s <= 0.0
        ):
            raise C2ActionBalancedExpansionError("sealed C2 calibration is invalid")
        for seed in selected:
            try:
                dataset, receipt = source._generate_c2_for_seed(
                    trainer=trainer,
                    archive=archive,
                    schedule=schedules[seed],
                    source_manifest_sha256=source_manifest_sha256,
                    checkpoint_sha256=checkpoint_sha256,
                    environment_source_sha256=environment_source_sha256,
                    reward_source_sha256=reward_source_sha256,
                    lambda_bits_per_j=multiplier,
                    interval_s=interval_s,
                )
            except source.E1FreshSourceError as error:
                if not str(error).startswith("INSUFFICIENT_COVERAGE:"):
                    raise
                generation_insufficient_reason = str(error)
                receipts.append(
                    {
                        "source_seed": seed,
                        "status": "INSUFFICIENT_COVERAGE",
                        "reason": generation_insufficient_reason,
                    }
                )
                break
            path = output_dir / "temporal-datasets" / f"c2-train-{seed}.json"
            write_temporal_dataset(path, dataset)
            loaded = read_temporal_dataset(path)
            if (
                loaded.verify() != dataset.verify()
                or loaded.source_manifest_sha256 != source_manifest_sha256
                or loaded.checkpoint_sha256 != checkpoint_sha256
            ):
                raise C2ActionBalancedExpansionError(
                    "published temporal dataset failed lineage check"
                )
            temporal_meta[str(seed)] = {
                "path": path.relative_to(output_dir).as_posix(),
                "file_sha256": _sha256(path),
                "dataset_sha256": loaded.verify(),
                "rows": len(loaded.rows),
                "source_partition": "TRAIN",
                "held_out": False,
            }
            receipts.append(receipt)
            final_clusters[seed] = [
                {
                    "source_seed": seed,
                    "cluster_sha256": row.verify(),
                    "reference_action": int(row.reference_action),
                    "candidate_action": int(row.candidate_action),
                }
                for row in loaded.rows
            ]
        if not source.c2_backend_smoke._networks_equal(trainer, networks_before):
            raise C2ActionBalancedExpansionError("C2 redesign mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise C2ActionBalancedExpansionError("C2 redesign wrote Main replay")
    graph_report = _coverage_report(
        action_dim=int(prepared["final_c2_graph_report"]["action_dim"]),
        original_components=authority["original_c2_components"],
        unsupported_pairs=tuple(
            (int(row["reference_action"]), int(row["candidate_action"]))
            for row in authority["original_unsupported_c2_pairs"]
        ),
        clusters_by_seed=final_clusters,
        decision_basis="completed-train-row-action-topology-only",
        generated_outcomes_materialized=True,
    )
    status = (
        "PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION"
        if graph_report["coverage_sufficient"]
        and generation_insufficient_reason is None
        and set(temporal_meta) == {str(seed) for seed in selected}
        else "INSUFFICIENT_COVERAGE"
    )
    result = _result_payload(
        status=status,
        authority_sha256=authority_sha256,
        authority=authority,
        selected=selected,
        schedule_hashes=schedule_hashes,
        temporal_datasets=temporal_meta,
        graph_report=graph_report,
        generation_receipts=receipts,
    )
    if generation_insufficient_reason is not None:
        result["insufficient_coverage_reason"] = generation_insufficient_reason
    result_sha256 = source._write_once_json(output_dir / "result.json", result)
    result_seal_sha256 = source._write_once_json(
        output_dir / "result-seal.json",
        {
            "schema": f"{RESULT_SCHEMA}{SEAL_SUFFIX}",
            "result_file_sha256": result_sha256,
            "authority_sha256": authority_sha256,
        },
    )
    return {
        **result,
        "result_file_sha256": result_sha256,
        "result_seal_file_sha256": result_seal_sha256,
    }


def _add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--independent-root", type=Path, required=True)
    parser.add_argument("--census-root", type=Path, required=True)
    parser.add_argument("--failed-expansion-root", type=Path, required=True)
    parser.add_argument("--legal-probe-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(source.TLE_ROOT_DEFAULT).expanduser()
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    _add_common_paths(prepare_parser)
    prepare_parser.add_argument("--expected-failed-authority-sha256", required=True)
    prepare_parser.add_argument(
        "--expected-failed-authority-seal-sha256", required=True
    )
    prepare_parser.add_argument(
        "--expected-failed-prepare-result-sha256", required=True
    )
    prepare_parser.add_argument(
        "--expected-failed-prepare-result-seal-sha256", required=True
    )
    prepare_parser.add_argument(
        "--expected-legal-probe-receipt-sha256", required=True
    )
    generate_parser = subparsers.add_parser("generate")
    _add_common_paths(generate_parser)
    args = parser.parse_args(argv)
    if args.phase == "prepare":
        payload = prepare(
            source_root=args.source_root,
            independent_root=args.independent_root,
            census_root=args.census_root,
            failed_expansion_root=args.failed_expansion_root,
            legal_probe_receipt=args.legal_probe_receipt,
            output_dir=args.output_dir,
            tle_root=args.tle_root,
            expected_failed_authority_sha256=args.expected_failed_authority_sha256,
            expected_failed_authority_seal_sha256=(
                args.expected_failed_authority_seal_sha256
            ),
            expected_failed_prepare_result_sha256=(
                args.expected_failed_prepare_result_sha256
            ),
            expected_failed_prepare_result_seal_sha256=(
                args.expected_failed_prepare_result_seal_sha256
            ),
            expected_legal_probe_receipt_sha256=(
                args.expected_legal_probe_receipt_sha256
            ),
        )
    else:
        payload = generate(
            source_root=args.source_root,
            independent_root=args.independent_root,
            census_root=args.census_root,
            failed_expansion_root=args.failed_expansion_root,
            legal_probe_receipt=args.legal_probe_receipt,
            output_dir=args.output_dir,
            tle_root=args.tle_root,
        )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
