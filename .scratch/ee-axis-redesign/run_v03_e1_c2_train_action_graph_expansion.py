#!/usr/bin/env python3
"""One-shot, train-only C2 action-graph coverage expansion.

``prepare`` authenticates the existing 4/3/0 source publication and the
target-free action-graph census, seals one fixed candidate pool, and inspects
only pre-outcome C2 schedule topology.  It selects the shortest seed prefix
that connects every originally unsupported validation contrast and gives
each needed action at least three scheduled clusters from at least two seeds.

``generate`` may be invoked once after a successful prepare.  It replays only
the selected schedules through the already-audited C2 generator and publishes
separate train-only temporal datasets.  It never opens a validation dataset,
test split, target metric, model metric, or held-out EE endpoint.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
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

spec = importlib.util.spec_from_file_location(
    "e1_action_shared_sources_for_c2_expansion",
    HERE / "run_v03_e1_action_shared_sources.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load action-shared source authority")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
wrapper._install_protocol()
source = wrapper.source

from mcrl.runtime.ee_axis_e1_c2_schedule import (  # noqa: E402
    E1C2PreOutcomeSchedule,
    load_e1_c2_schedule,
    seal_e1_c2_schedule,
)
from mcrl.runtime.ee_axis_temporal_dataset import (  # noqa: E402
    read_temporal_dataset,
    write_temporal_dataset,
)


AUTHORITY_SCHEMA = "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-authority-v1"
PREPARE_RESULT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-prepare-result-v1"
)
RESULT_SCHEMA = "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-result-v1"
SEAL_SUFFIX = "-seal"
INDEPENDENT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-independent-source-verification-v1"
)
CENSUS_SCHEMA = "multi-catfish-mcrl-v03-e1-action-graph-coverage-census-v1"
BASE_RESULT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-source-supplement-receipt-v1"
)
CANDIDATE_SEED_ORDER = tuple(range(2026092201, 2026092221))
MIN_CLUSTERS_PER_NEEDED_ACTION = 3
MIN_SEEDS_PER_NEEDED_ACTION = 2
FALSE_BOUNDARY = {
    "validation_dataset_bytes_opened": False,
    "test_split_opened": False,
    "held_out_ee_evaluated": False,
}
SOURCE_DATA_CONTROL_FILES = frozenset(
    {"receipt.json", "ladder-index.json", "test-index.json"}
)


class C2TrainGraphExpansionError(RuntimeError):
    """The one-shot structural expansion failed closed."""


def _digest(value: object, *, field: str) -> str:
    try:
        return source._digest(value, field=field)
    except Exception as error:
        raise C2TrainGraphExpansionError(str(error)) from error


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise C2TrainGraphExpansionError(
            f"sealed input is missing, non-regular, or a symlink: {path}"
        )
    return source._file_sha256(path)


def _read_sealed(path: Path, expected_sha256: str, *, label: str) -> dict[str, Any]:
    expected = _digest(expected_sha256, field=f"expected_{label}_sha256")
    if _sha256(path) != expected:
        raise C2TrainGraphExpansionError(f"{label} bytes changed")
    payload = source._read_canonical_json(path)
    if not isinstance(payload, dict):
        raise C2TrainGraphExpansionError(f"{label} is not a JSON object")
    return payload


def _control_file_manifest(root: Path) -> dict[str, str]:
    """Hash authority/control files without reading a source dataset byte."""

    if root.is_symlink() or not root.is_dir():
        raise C2TrainGraphExpansionError("base source root must be a regular directory")
    manifest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise C2TrainGraphExpansionError(f"base source contains symlink: {path}")
        if path.is_file():
            relative = path.relative_to(root)
            if (
                relative.parts
                and relative.parts[0] == "source-data"
                and relative.name not in SOURCE_DATA_CONTROL_FILES
            ):
                continue
            manifest[relative.as_posix()] = source._file_sha256(path)
    if not manifest:
        raise C2TrainGraphExpansionError("base source publication is empty")
    return manifest


def _normalize_components(value: object, *, action_dim: int) -> tuple[tuple[int, ...], ...]:
    if not isinstance(value, list):
        raise C2TrainGraphExpansionError("C2 census components are malformed")
    components: list[tuple[int, ...]] = []
    seen: set[int] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, list) or not raw:
            raise C2TrainGraphExpansionError(f"C2 component {index} is malformed")
        members = tuple(sorted(raw))
        if any(type(action) is not int or not 0 <= action < action_dim for action in members):
            raise C2TrainGraphExpansionError("C2 component action is out of range")
        if len(set(members)) != len(members) or seen.intersection(members):
            raise C2TrainGraphExpansionError("C2 census components overlap or duplicate")
        seen.update(members)
        components.append(members)
    return tuple(components)


def _normalize_pairs(value: object, *, action_dim: int) -> tuple[tuple[int, int], ...]:
    if not isinstance(value, list):
        raise C2TrainGraphExpansionError("unsupported C2 pairs are malformed")
    pairs: list[tuple[int, int]] = []
    for raw in value:
        if not isinstance(raw, dict):
            raise C2TrainGraphExpansionError("unsupported C2 pair is malformed")
        pair = (raw.get("reference_action"), raw.get("candidate_action"))
        if any(type(action) is not int or not 0 <= action < action_dim for action in pair):
            raise C2TrainGraphExpansionError("unsupported C2 action is out of range")
        if pair[0] == pair[1]:
            raise C2TrainGraphExpansionError("unsupported C2 pair is self-comparison")
        pairs.append((int(pair[0]), int(pair[1])))
    normalized = tuple(sorted(set(pairs)))
    if not normalized:
        raise C2TrainGraphExpansionError("C2 census has no unsupported contrast to repair")
    return normalized


def _cluster_fields(cluster: object, *, expected_seed: int) -> tuple[str, int, int]:
    if isinstance(cluster, Mapping):
        seed = cluster.get("source_seed")
        identity = cluster.get("cluster_sha256")
        reference = cluster.get("reference_action")
        candidate = cluster.get("candidate_action")
    else:
        seed = getattr(cluster, "source_seed", None)
        identity = getattr(cluster, "cluster_sha256", None)
        reference = getattr(cluster, "reference_action", None)
        candidate = getattr(cluster, "candidate_action", None)
    if seed != expected_seed or not isinstance(identity, str) or not identity:
        raise C2TrainGraphExpansionError("schedule cluster identity or seed is malformed")
    if type(reference) is not int or type(candidate) is not int or reference == candidate:
        raise C2TrainGraphExpansionError("schedule cluster action edge is malformed")
    return identity, reference, candidate


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def _coverage_report(
    *,
    action_dim: int,
    original_components: Sequence[Sequence[int]],
    unsupported_pairs: Sequence[tuple[int, int]],
    clusters_by_seed: Mapping[int, Iterable[object]],
    decision_basis: str = "schedule-action-topology-only",
    generated_outcomes_materialized: bool = False,
) -> dict[str, Any]:
    dsu = _DisjointSet(action_dim)
    active_actions: set[int] = set()
    for component in original_components:
        members = tuple(component)
        active_actions.update(members)
        for action in members[1:]:
            dsu.union(members[0], action)
    needed_actions = sorted({action for pair in unsupported_pairs for action in pair})
    identities: set[tuple[int, str]] = set()
    clusters_by_action: dict[int, set[tuple[int, str]]] = defaultdict(set)
    seeds_by_action: dict[int, set[int]] = defaultdict(set)
    edge_count = 0
    for seed, clusters in clusters_by_seed.items():
        if type(seed) is not int:
            raise C2TrainGraphExpansionError("schedule seed key is not an integer")
        for cluster in clusters:
            identity, reference, candidate = _cluster_fields(cluster, expected_seed=seed)
            if not 0 <= reference < action_dim or not 0 <= candidate < action_dim:
                raise C2TrainGraphExpansionError("schedule action lies outside census action_dim")
            key = (seed, identity)
            if key in identities:
                raise C2TrainGraphExpansionError("duplicate expansion cluster identity")
            identities.add(key)
            edge_count += 1
            active_actions.update((reference, candidate))
            dsu.union(reference, candidate)
            for action in (reference, candidate):
                if action in needed_actions:
                    clusters_by_action[action].add(key)
                    seeds_by_action[action].add(seed)
    remaining = sorted(
        pair for pair in unsupported_pairs if dsu.find(pair[0]) != dsu.find(pair[1])
    )
    components: dict[int, list[int]] = defaultdict(list)
    for action in sorted(active_actions):
        components[dsu.find(action)].append(action)
    evidence = {
        str(action): {
            "clusters": len(clusters_by_action[action]),
            "seeds": sorted(seeds_by_action[action]),
            "meets_minimum_clusters": (
                len(clusters_by_action[action]) >= MIN_CLUSTERS_PER_NEEDED_ACTION
            ),
            "meets_minimum_seeds": (
                len(seeds_by_action[action]) >= MIN_SEEDS_PER_NEEDED_ACTION
            ),
        }
        for action in needed_actions
    }
    sufficient = not remaining and all(
        row["meets_minimum_clusters"] and row["meets_minimum_seeds"]
        for row in evidence.values()
    )
    return {
        "decision_basis": decision_basis,
        "action_dim": action_dim,
        "original_unsupported_validation_action_pairs": [
            {"reference_action": pair[0], "candidate_action": pair[1]}
            for pair in unsupported_pairs
        ],
        "remaining_unsupported_validation_action_pairs": [
            {"reference_action": pair[0], "candidate_action": pair[1]}
            for pair in remaining
        ],
        "needed_actions": needed_actions,
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
        "generated_outcomes_materialized": generated_outcomes_materialized,
    }


def _select_shortest_prefix(
    *,
    action_dim: int,
    original_components: Sequence[Sequence[int]],
    unsupported_pairs: Sequence[tuple[int, int]],
    schedules: Mapping[int, Iterable[object]],
    candidate_seed_order: Sequence[int] = CANDIDATE_SEED_ORDER,
) -> tuple[tuple[int, ...], dict[str, Any]]:
    order = tuple(candidate_seed_order)
    if order != CANDIDATE_SEED_ORDER:
        raise C2TrainGraphExpansionError("candidate seed pool/order is not the sealed pool")
    unknown = set(schedules) - set(order)
    if unknown:
        raise C2TrainGraphExpansionError("schedule mapping contains an unauthorized seed")
    accumulated: dict[int, Iterable[object]] = {}
    last_report: dict[str, Any] | None = None
    for seed in order:
        if seed not in schedules:
            break
        accumulated[seed] = schedules[seed]
        last_report = _coverage_report(
            action_dim=action_dim,
            original_components=original_components,
            unsupported_pairs=unsupported_pairs,
            clusters_by_seed=accumulated,
        )
        if last_report["coverage_sufficient"]:
            return tuple(accumulated), last_report
    if last_report is None:
        last_report = _coverage_report(
            action_dim=action_dim,
            original_components=original_components,
            unsupported_pairs=unsupported_pairs,
            clusters_by_seed={},
        )
    return (), last_report


def _authenticate_inputs(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    expected_base_source_result_sha256: str,
    expected_base_source_result_seal_sha256: str,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
    expected_census_result_sha256: str,
    expected_census_result_seal_sha256: str,
) -> dict[str, Any]:
    independent = _read_sealed(
        independent_root / "result.json",
        expected_independent_result_sha256,
        label="independent_result",
    )
    independent_seal = _read_sealed(
        independent_root / "result-seal.json",
        expected_independent_result_seal_sha256,
        label="independent_result_seal",
    )
    if (
        independent.get("schema") != INDEPENDENT_SCHEMA
        or independent.get("status") != "PASS_INDEPENDENT_4_3_0_NO_TEST"
        or independent.get("test_outcomes_generated") is not False
        or independent.get("test_dataset_documents_opened") is not False
        or independent.get("held_out_ee_evaluated") is not False
        or independent_seal.get("schema") != f"{INDEPENDENT_SCHEMA}-seal"
        or independent_seal.get("result_file_sha256")
        != expected_independent_result_sha256
    ):
        raise C2TrainGraphExpansionError("independent 4/3/0 authority is invalid")

    base_result = _read_sealed(
        source_root / "action-shared-supplement-receipt.json",
        expected_base_source_result_sha256,
        label="base_source_result",
    )
    base_seal = _read_sealed(
        source_root / "action-shared-supplement-receipt-seal.json",
        expected_base_source_result_seal_sha256,
        label="base_source_result_seal",
    )
    if (
        base_result.get("schema") != BASE_RESULT_SCHEMA
        or base_result.get("status") != "PASS"
        or base_result.get("test_outcomes_generated") is not False
        or base_result.get("test_split_opened") is not False
        or base_result.get("held_out_ee_evaluated") is not False
        or base_seal.get("schema")
        != "multi-catfish-mcrl-v03-e1-action-shared-source-supplement-seal-v1"
        or base_seal.get("receipt_file_sha256") != expected_base_source_result_sha256
        or independent.get("supplement_receipt_file_sha256")
        != expected_base_source_result_sha256
    ):
        raise C2TrainGraphExpansionError("base source result/seal is invalid")
    source_receipt_sha256 = _sha256(source_root / "source-data" / "receipt.json")
    publication_summary = base_result.get("source_publication_summary")
    if (
        not isinstance(publication_summary, dict)
        or publication_summary.get("source_receipt_file_sha256")
        != source_receipt_sha256
        or independent.get("source_receipt_file_sha256") != source_receipt_sha256
    ):
        raise C2TrainGraphExpansionError("base source and independent authority disagree")

    _manifest, prereg, _schedule_seals = source._load_authority(source_root)
    expected_split = {
        str(seed): split_name for seed, split_name in sorted(wrapper.SOURCE_SEED_SPLIT.items())
    }
    if prereg.get("source_seed_split") != expected_split or "test" in expected_split.values():
        raise C2TrainGraphExpansionError("base source is not the sealed 4/3/0 design")

    census = _read_sealed(
        census_root / "result.json", expected_census_result_sha256, label="census_result"
    )
    census_seal = _read_sealed(
        census_root / "result-seal.json",
        expected_census_result_seal_sha256,
        label="census_result_seal",
    )
    routes = census.get("routes")
    if not isinstance(routes, dict) or set(routes) != {"C1", "C2", "C3"}:
        raise C2TrainGraphExpansionError("census route report is incomplete")
    if (
        census.get("schema") != CENSUS_SCHEMA
        or census.get("status") != "INSUFFICIENT_COVERAGE"
        or census.get("decision_basis")
        != "action-identifiers-and-train-comparison-graph-only"
        or census.get("target_values_emitted") is not False
        or census.get("model_predictions_or_mae_computed") is not False
        or census.get("test_split_opened") is not False
        or census.get("held_out_ee_evaluated") is not False
        or census.get("independent_source_result_sha256")
        != expected_independent_result_sha256
        or census.get("independent_source_result_seal_sha256")
        != expected_independent_result_seal_sha256
        or census.get("source_prereg_sha256") != prereg.get("prereg_sha256")
        or census.get("source_manifest_sha256") != prereg.get("source_manifest_sha256")
        or census_seal.get("schema") != f"{CENSUS_SCHEMA}-seal"
        or census_seal.get("result_file_sha256") != expected_census_result_sha256
        or routes["C1"].get("all_validation_contrasts_identified") is not True
        or routes["C3"].get("all_validation_contrasts_identified") is not True
        or routes["C2"].get("all_validation_contrasts_identified") is not False
    ):
        raise C2TrainGraphExpansionError("census authority or cross-bindings are invalid")
    action_dim = routes["C2"].get("action_dim")
    if type(action_dim) is not int or action_dim <= 1:
        raise C2TrainGraphExpansionError("C2 census action_dim is invalid")
    components = _normalize_components(
        routes["C2"].get("connected_components_with_edges"), action_dim=action_dim
    )
    unsupported = _normalize_pairs(
        routes["C2"].get("unsupported_validation_action_pairs"), action_dim=action_dim
    )
    return {
        "base_result": base_result,
        "independent": independent,
        "census": census,
        "prereg": prereg,
        "action_dim": action_dim,
        "components": components,
        "unsupported_pairs": unsupported,
        "source_receipt_sha256": source_receipt_sha256,
        "source_control_file_sha256s": _control_file_manifest(source_root),
    }


def _dependency_digests(
    *,
    expected_base_source_result_sha256: str,
    expected_base_source_result_seal_sha256: str,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
    expected_census_result_sha256: str,
    expected_census_result_seal_sha256: str,
) -> dict[str, str]:
    return {
        "base_source_result_sha256": expected_base_source_result_sha256,
        "base_source_result_seal_sha256": expected_base_source_result_seal_sha256,
        "independent_result_sha256": expected_independent_result_sha256,
        "independent_result_seal_sha256": expected_independent_result_seal_sha256,
        "census_result_sha256": expected_census_result_sha256,
        "census_result_seal_sha256": expected_census_result_seal_sha256,
    }


def _sealed_formula_constants(
    prereg: Mapping[str, Any], base_record: Any
) -> tuple[float, float]:
    learner = prereg.get("learner")
    try:
        multiplier = float.fromhex(learner["lambda_bits_per_j_hex"])
        interval_s = float(
            base_record.sections["ephemeris"]["config"]["time_step_s"]
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise C2TrainGraphExpansionError(
            "sealed source formula constants are malformed"
        ) from error
    if (
        not math.isfinite(multiplier)
        or not math.isfinite(interval_s)
        or multiplier <= 0.0
        or interval_s <= 0.0
    ):
        raise C2TrainGraphExpansionError("sealed source formula constants are invalid")
    return multiplier, interval_s


def prepare(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    output_dir: Path,
    tle_root: Path,
    expected_base_source_result_sha256: str,
    expected_base_source_result_seal_sha256: str,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
    expected_census_result_sha256: str,
    expected_census_result_seal_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to reuse one-shot C2 expansion directory")
    source_root_resolved = source_root.resolve(strict=True)
    output_resolved = output_dir.resolve(strict=False)
    if output_resolved == source_root_resolved or output_resolved.is_relative_to(
        source_root_resolved
    ):
        raise C2TrainGraphExpansionError(
            "expansion output must be outside the immutable base source root"
        )
    authenticated = _authenticate_inputs(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        expected_base_source_result_sha256=expected_base_source_result_sha256,
        expected_base_source_result_seal_sha256=expected_base_source_result_seal_sha256,
        expected_independent_result_sha256=expected_independent_result_sha256,
        expected_independent_result_seal_sha256=expected_independent_result_seal_sha256,
        expected_census_result_sha256=expected_census_result_sha256,
        expected_census_result_seal_sha256=expected_census_result_seal_sha256,
    )
    prereg = authenticated["prereg"]
    source_manifest_sha256 = _digest(
        prereg.get("source_manifest_sha256"), field="source_manifest_sha256"
    )
    checkpoint_sha256 = _digest(prereg.get("checkpoint_sha256"), field="checkpoint_sha256")
    environment_source_sha256 = _digest(
        prereg.get("environment_source_sha256"), field="environment_source_sha256"
    )
    reward_source_sha256 = _digest(
        prereg.get("reward_source_sha256"), field="reward_source_sha256"
    )
    if set(CANDIDATE_SEED_ORDER).intersection(wrapper.BURNED_SOURCE_SEEDS):
        raise C2TrainGraphExpansionError("fixed expansion pool overlaps burned seeds")

    output_dir.mkdir(parents=True)
    dependency_digests = _dependency_digests(
        expected_base_source_result_sha256=expected_base_source_result_sha256,
        expected_base_source_result_seal_sha256=expected_base_source_result_seal_sha256,
        expected_independent_result_sha256=expected_independent_result_sha256,
        expected_independent_result_seal_sha256=expected_independent_result_seal_sha256,
        expected_census_result_sha256=expected_census_result_sha256,
        expected_census_result_seal_sha256=expected_census_result_seal_sha256,
    )
    base_record = source.read_prereg(source.BASE_PREREG)
    multiplier, interval_s = _sealed_formula_constants(prereg, base_record)
    authority = {
        "schema": AUTHORITY_SCHEMA,
        "status": "SEALED_BEFORE_SCHEDULE_TOPOLOGY_INSPECTION",
        "scope": "C2_TRAIN_ONLY_ACTION_GRAPH_COVERAGE_EXPANSION_ONCE",
        "runner_file_sha256": _sha256(Path(__file__)),
        **dependency_digests,
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
        "selection_rule": "shortest-prefix-by-schedule-action-topology-only",
        "minimum_clusters_per_needed_action": MIN_CLUSTERS_PER_NEEDED_ACTION,
        "minimum_seeds_per_needed_action": MIN_SEEDS_PER_NEEDED_ACTION,
        "replacement_seed_pool_authorized": False,
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
    schedule_hashes: dict[str, str] = {}
    discovery: list[dict[str, Any]] = []
    selected: tuple[int, ...] = ()
    report: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory(prefix="mcrl-c2-train-graph-prepare-") as temporary:
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
            raise C2TrainGraphExpansionError("loaded Main differs from base source authority")
        network_before = source.c2_backend_smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)
        for seed in CANDIDATE_SEED_ORDER:
            try:
                schedule, receipt = source._discover_c2_schedule(
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
                schedule = None
                receipt = {
                    "source_seed": seed,
                    "status": "INSUFFICIENT_SCHEDULE",
                    "reason": str(error),
                    "forecast_outcomes_read": False,
                }
            discovery.append(receipt)
            if schedule is None:
                # Prefix selection is strict: a missing seed cannot be skipped.
                break
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
            raise C2TrainGraphExpansionError("schedule discovery mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise C2TrainGraphExpansionError("schedule discovery wrote Main replay")
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
        "selected_seed_order": list(selected),
        "selected_schedule_file_sha256s": {
            str(seed): schedule_hashes[str(seed)] for seed in selected
        },
        "all_inspected_schedule_file_sha256s": schedule_hashes,
        "temporal_datasets": {},
        "temporal_dataset_paths": {},
        "temporal_dataset_file_sha256s": {},
        "temporal_dataset_sha256s": {},
        "final_c2_graph_report": report,
        "schedule_discovery_receipts": discovery,
        "candidate_seed_order": list(CANDIDATE_SEED_ORDER),
        "replacement_seed_pool_used": False,
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
    seal = source._read_canonical_json(output_dir / "prepare-result-seal.json")
    if (
        authority.get("schema") != AUTHORITY_SCHEMA
        or authority_seal.get("authority_sha256") != authority_sha256
        or result.get("schema") != PREPARE_RESULT_SCHEMA
        or seal.get("result_file_sha256") != _sha256(result_path)
        or seal.get("authority_sha256") != authority_sha256
        or result.get("authority_sha256") != authority_sha256
    ):
        raise C2TrainGraphExpansionError("prepare authority/result/seals are invalid")
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
        "authority_sha256": authority_sha256,
        **{
            key: authority[key]
            for key in (
                "base_source_result_sha256",
                "base_source_result_seal_sha256",
                "independent_result_sha256",
                "independent_result_seal_sha256",
                "census_result_sha256",
                "census_result_seal_sha256",
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
        "temporal_dataset_paths": {
            seed: row["path"] for seed, row in temporal.items()
        },
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
        "completion_status": status,
        "replacement_seed_pool_used": False,
        "targets_or_validation_metrics_computed": False,
        **FALSE_BOUNDARY,
    }


def generate(
    *,
    source_root: Path,
    independent_root: Path,
    census_root: Path,
    output_dir: Path,
    tle_root: Path,
) -> dict[str, Any]:
    authority, prepared, authority_sha256 = _load_prepare(output_dir)
    if (
        authority.get("runner_file_sha256") != _sha256(Path(__file__))
        or authority.get("base_prereg_file_sha256") != _sha256(source.BASE_PREREG)
        or authority.get("tle_root_supplied") != str(tle_root.resolve(strict=True))
    ):
        raise C2TrainGraphExpansionError(
            "runner, base prereg, or frozen TLE root changed after prepare"
        )
    if prepared.get("status") != "READY_FOR_ONE_TIME_GENERATION":
        raise C2TrainGraphExpansionError("prepare did not authorize generation")
    attempt_path = output_dir / "generation-attempt.json"
    if attempt_path.exists() or attempt_path.is_symlink() or (output_dir / "result.json").exists():
        raise FileExistsError("C2 train expansion generation is one-shot and was already attempted")
    selected = tuple(prepared.get("selected_seed_order", ()))
    if not selected or selected != CANDIDATE_SEED_ORDER[: len(selected)]:
        raise C2TrainGraphExpansionError("prepared selection is not a fixed-pool prefix")
    schedule_hashes = prepared.get("selected_schedule_file_sha256s")
    if not isinstance(schedule_hashes, dict) or set(schedule_hashes) != {
        str(seed) for seed in selected
    }:
        raise C2TrainGraphExpansionError("prepared selected schedules are incomplete")
    reauthenticated = _authenticate_inputs(
        source_root=source_root,
        independent_root=independent_root,
        census_root=census_root,
        expected_base_source_result_sha256=authority["base_source_result_sha256"],
        expected_base_source_result_seal_sha256=(
            authority["base_source_result_seal_sha256"]
        ),
        expected_independent_result_sha256=authority["independent_result_sha256"],
        expected_independent_result_seal_sha256=(
            authority["independent_result_seal_sha256"]
        ),
        expected_census_result_sha256=authority["census_result_sha256"],
        expected_census_result_seal_sha256=authority["census_result_seal_sha256"],
    )
    if reauthenticated["source_control_file_sha256s"] != authority.get(
        "base_source_control_file_sha256s"
    ):
        raise C2TrainGraphExpansionError(
            "base 4/3/0 source authority/control bytes changed after prepare"
        )
    source._write_once_json(
        attempt_path,
        {
            "schema": f"{RESULT_SCHEMA}-generation-attempt-v1",
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
        raise C2TrainGraphExpansionError("source prereg changed after prepare")
    schedules: dict[int, E1C2PreOutcomeSchedule] = {}
    for seed in selected:
        schedules[seed] = load_e1_c2_schedule(
            output_dir / "schedules" / f"c2-{seed}.json",
            expected_file_sha256=schedule_hashes[str(seed)],
            source_seed=seed,
            policy_sha256=source._policy_sha256(),
            source_manifest_sha256=source_manifest_sha256,
            checkpoint_sha256=checkpoint_sha256,
        )

    temporal_meta: dict[str, dict[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    final_clusters: dict[int, list[dict[str, Any]]] = {}
    generation_insufficient_reason: str | None = None
    base_record = source.read_prereg(source.BASE_PREREG)
    with tempfile.TemporaryDirectory(prefix="mcrl-c2-train-graph-generate-") as temporary:
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
            raise C2TrainGraphExpansionError("loaded Main differs from sealed expansion")
        networks_before = source.c2_backend_smoke._network_snapshot(trainer)
        replay_before = len(trainer.replay)
        try:
            multiplier = float.fromhex(authority["lambda_bits_per_j_hex"])
            interval_s = float.fromhex(authority["interval_s_hex"])
        except (KeyError, TypeError, ValueError) as error:
            raise C2TrainGraphExpansionError(
                "sealed expansion formula constants are malformed"
            ) from error
        if (
            not math.isfinite(multiplier)
            or not math.isfinite(interval_s)
            or multiplier <= 0.0
            or interval_s <= 0.0
        ):
            raise C2TrainGraphExpansionError("frozen C2 calibration is invalid")
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
                raise C2TrainGraphExpansionError("published temporal dataset failed lineage check")
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
            raise C2TrainGraphExpansionError("C2 expansion mutated Main networks")
        if len(trainer.replay) != replay_before:
            raise C2TrainGraphExpansionError("C2 expansion wrote Main replay")
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


def _add_common_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expected-base-source-result-sha256", required=True)
    parser.add_argument("--expected-base-source-result-seal-sha256", required=True)
    parser.add_argument("--expected-independent-result-sha256", required=True)
    parser.add_argument("--expected-independent-result-seal-sha256", required=True)
    parser.add_argument("--expected-census-result-sha256", required=True)
    parser.add_argument("--expected-census-result-seal-sha256", required=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    _add_common_auth_args(prepare_parser)
    prepare_parser.add_argument("--independent-root", type=Path, required=True)
    prepare_parser.add_argument("--census-root", type=Path, required=True)
    prepare_parser.add_argument("--output-dir", type=Path, required=True)
    prepare_parser.add_argument(
        "--tle-root", type=Path, default=Path(source.TLE_ROOT_DEFAULT).expanduser()
    )
    generate_parser = subparsers.add_parser("generate")
    generate_parser.add_argument("--source-root", type=Path, required=True)
    generate_parser.add_argument("--independent-root", type=Path, required=True)
    generate_parser.add_argument("--census-root", type=Path, required=True)
    generate_parser.add_argument("--output-dir", type=Path, required=True)
    generate_parser.add_argument(
        "--tle-root", type=Path, default=Path(source.TLE_ROOT_DEFAULT).expanduser()
    )
    args = parser.parse_args(argv)
    if args.phase == "prepare":
        payload = prepare(
            source_root=args.source_root,
            independent_root=args.independent_root,
            census_root=args.census_root,
            output_dir=args.output_dir,
            tle_root=args.tle_root,
            expected_base_source_result_sha256=args.expected_base_source_result_sha256,
            expected_base_source_result_seal_sha256=(
                args.expected_base_source_result_seal_sha256
            ),
            expected_independent_result_sha256=args.expected_independent_result_sha256,
            expected_independent_result_seal_sha256=(
                args.expected_independent_result_seal_sha256
            ),
            expected_census_result_sha256=args.expected_census_result_sha256,
            expected_census_result_seal_sha256=args.expected_census_result_seal_sha256,
        )
    else:
        payload = generate(
            source_root=args.source_root,
            independent_root=args.independent_root,
            census_root=args.census_root,
            output_dir=args.output_dir,
            tle_root=args.tle_root,
        )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
