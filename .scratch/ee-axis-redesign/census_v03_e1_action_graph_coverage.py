#!/usr/bin/env python3
"""Census train-to-validation action-graph coverage without emitting targets."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (REPO, REPO / "src", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

spec = importlib.util.spec_from_file_location(
    "e1_action_shared_sources_for_graph_census",
    HERE / "run_v03_e1_action_shared_sources.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load action-shared source authority")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
wrapper._install_protocol()
source = wrapper.source

from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-e1-action-graph-coverage-census-v1"


class ActionGraphCensusError(RuntimeError):
    """The target-free structural census failed closed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return source._read_canonical_json(path)


def _authenticate_independent(
    root: Path,
    *,
    expected_result_sha256: str,
    expected_result_seal_sha256: str,
) -> dict[str, Any]:
    result_path = root / "result.json"
    seal_path = root / "result-seal.json"
    if (
        result_path.is_symlink()
        or seal_path.is_symlink()
        or _sha256(result_path) != expected_result_sha256
        or _sha256(seal_path) != expected_result_seal_sha256
    ):
        raise ActionGraphCensusError("independent source receipt bytes changed")
    result = _read(result_path)
    seal = _read(seal_path)
    if (
        result.get("status") != "PASS_INDEPENDENT_4_3_0_NO_TEST"
        or result.get("test_outcomes_generated") is not False
        or result.get("test_dataset_documents_opened") is not False
        or result.get("held_out_ee_evaluated") is not False
        or seal.get("result_file_sha256") != expected_result_sha256
    ):
        raise ActionGraphCensusError("independent no-test source verification is invalid")
    return result


def _route_graph_report(
    train_rows: Sequence[Any],
    validation_rows: Sequence[Any],
    *,
    action_dim: int,
) -> dict[str, Any]:
    adjacency = [set() for _ in range(action_dim)]
    for row in train_rows:
        reference = int(row.reference_action)
        candidate = int(row.candidate_action)
        adjacency[reference].add(candidate)
        adjacency[candidate].add(reference)
    component = [-1] * action_dim
    components: list[list[int]] = []
    for start in range(action_dim):
        if component[start] >= 0 or not adjacency[start]:
            continue
        component_id = len(components)
        stack = [start]
        component[start] = component_id
        members: list[int] = []
        while stack:
            current = stack.pop()
            members.append(current)
            for neighbor in sorted(adjacency[current]):
                if component[neighbor] < 0:
                    component[neighbor] = component_id
                    stack.append(neighbor)
        components.append(sorted(members))
    unsupported = [
        row
        for row in validation_rows
        if component[int(row.reference_action)] < 0
        or component[int(row.reference_action)]
        != component[int(row.candidate_action)]
    ]
    unsupported_pairs = sorted(
        {
            (int(row.reference_action), int(row.candidate_action))
            for row in unsupported
        }
    )
    active_train_actions = sorted(
        {int(row.reference_action) for row in train_rows}
        | {int(row.candidate_action) for row in train_rows}
    )
    active_validation_actions = sorted(
        {int(row.reference_action) for row in validation_rows}
        | {int(row.candidate_action) for row in validation_rows}
    )
    return {
        "action_dim": action_dim,
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "active_train_actions": active_train_actions,
        "active_validation_actions": active_validation_actions,
        "connected_components_with_edges": components,
        "isolated_actions": [
            action for action in range(action_dim) if not adjacency[action]
        ],
        "unsupported_validation_rows": len(unsupported),
        "unsupported_validation_fraction": (
            len(unsupported) / len(validation_rows) if validation_rows else None
        ),
        "unsupported_validation_action_pairs": [
            {"reference_action": reference, "candidate_action": candidate}
            for reference, candidate in unsupported_pairs
        ],
        "affected_validation_source_seeds": sorted(
            {int(row.source_seed) for row in unsupported}
        ),
        "affected_validation_intervention_clusters": len(
            {row.cluster_key for row in unsupported}
        ),
        "affected_validation_inference_anchors": len(
            {row.inference_cluster_key for row in unsupported}
        ),
        "all_validation_contrasts_identified": not unsupported,
    }


def run(
    *,
    source_root: Path,
    independent_verification_root: Path,
    output_dir: Path,
    expected_independent_result_sha256: str,
    expected_independent_result_seal_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite action-graph census")
    independent = _authenticate_independent(
        independent_verification_root,
        expected_result_sha256=expected_independent_result_sha256,
        expected_result_seal_sha256=expected_independent_result_seal_sha256,
    )
    data_root = source_root / "source-data"
    receipt_path = data_root / "receipt.json"
    receipt = _read(receipt_path)
    index = _read(data_root / "ladder-index.json")
    prereg = _read(source_root / "prereg.json")
    expected_split = {
        str(seed): split_name
        for seed, split_name in sorted(wrapper.SOURCE_SEED_SPLIT.items())
    }
    if (
        _sha256(receipt_path) != independent.get("source_receipt_file_sha256")
        or receipt.get("status") != "PASS"
        or index.get("seed_split") != expected_split
        or prereg.get("source_seed_split") != expected_split
        or "test" in expected_split.values()
    ):
        raise ActionGraphCensusError("source split or independent receipt changed")
    rows_by_split_route: dict[str, dict[str, list[Any]]] = {
        split_name: {route: [] for route in ("C1", "C2", "C3")}
        for split_name in ("train", "validation")
    }
    datasets = index.get("datasets")
    if not isinstance(datasets, dict) or set(datasets) != set(expected_split):
        raise ActionGraphCensusError("source dataset index is incomplete")
    opened_paths: list[str] = []
    for seed_text, split_name in expected_split.items():
        seed = int(seed_text)
        entry = datasets[seed_text]
        opening_path = data_root / f"opening-{seed}.json"
        temporal_path = data_root / f"temporal-{seed}.json"
        if (
            entry.get("opening_path") != opening_path.name
            or entry.get("temporal_path") != temporal_path.name
            or _sha256(opening_path)
            != receipt["opening_dataset_file_sha256s"][seed_text]
            or _sha256(temporal_path)
            != receipt["temporal_dataset_file_sha256s"][seed_text]
        ):
            raise ActionGraphCensusError("source dataset path or digest changed")
        opening = read_opening_dataset(opening_path)
        temporal = read_temporal_dataset(temporal_path)
        indexed = source._index_opening(opening, source_seed=seed)
        indexed.extend(source._index_temporal(temporal))
        for row in indexed:
            rows_by_split_route[split_name][row.route].append(row)
        opened_paths.extend((opening_path.name, temporal_path.name))
    action_dims = {
        len(row.action_mask)
        for split_rows in rows_by_split_route.values()
        for route_rows in split_rows.values()
        for row in route_rows
    }
    if len(action_dims) != 1:
        raise ActionGraphCensusError("source rows do not share one action dimension")
    action_dim = action_dims.pop()
    routes = {
        route: _route_graph_report(
            rows_by_split_route["train"][route],
            rows_by_split_route["validation"][route],
            action_dim=action_dim,
        )
        for route in ("C1", "C2", "C3")
    }
    status = (
        "PASS_ACTION_GRAPH_COVERAGE"
        if all(row["all_validation_contrasts_identified"] for row in routes.values())
        else "INSUFFICIENT_COVERAGE"
    )
    result = {
        "schema": SCHEMA,
        "status": status,
        "decision_basis": "action-identifiers-and-train-comparison-graph-only",
        "target_values_emitted": False,
        "model_predictions_or_mae_computed": False,
        "independent_source_result_sha256": expected_independent_result_sha256,
        "independent_source_result_seal_sha256": (
            expected_independent_result_seal_sha256
        ),
        "source_prereg_sha256": prereg["prereg_sha256"],
        "source_manifest_sha256": prereg["source_manifest_sha256"],
        "routes": routes,
        "opened_train_validation_dataset_paths": opened_paths,
        "opened_test_dataset_paths": [],
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "census_runner_file_sha256": _sha256(Path(__file__)),
    }
    output_dir.mkdir(parents=True)
    result_sha256 = source._write_once_json(output_dir / "result.json", result)
    seal_sha256 = source._write_once_json(
        output_dir / "result-seal.json",
        {
            "schema": f"{SCHEMA}-seal",
            "result_file_sha256": result_sha256,
            "census_runner_file_sha256": _sha256(Path(__file__)),
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-independent-result-sha256", required=True)
    parser.add_argument("--expected-independent-result-seal-sha256", required=True)
    args = parser.parse_args(argv)
    payload = run(
        source_root=args.source_root,
        independent_verification_root=args.independent_source_verification_root,
        output_dir=args.output_dir,
        expected_independent_result_sha256=args.expected_independent_result_sha256,
        expected_independent_result_seal_sha256=(
            args.expected_independent_result_seal_sha256
        ),
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
