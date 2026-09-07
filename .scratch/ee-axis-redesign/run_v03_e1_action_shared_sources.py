#!/usr/bin/env python3
"""Fresh train/validation source supplement for the action-shared E1 repair.

This runner deliberately generates no new test outcomes.  It reuses the
audited physical C1/C2/C3 source machinery while expanding the design split
to four train seeds and three validation seeds.  The previously generated E1
test split remains opaque and unopened.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (REPO, REPO / "src", HERE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

spec = importlib.util.spec_from_file_location(
    "e1_source_v1", HERE / "run_v03_e1_fresh_sources.py"
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load the audited E1 source runner")
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)

from mcrl.runtime.ee_axis_e1_split import (  # noqa: E402
    E1RouteCoverage,
    E1SplitReceipt,
    verify_full_sibling_groups,
)


SOURCE_SEED_SPLIT = {
    2026092001: "train",
    2026092002: "train",
    2026092003: "train",
    2026092004: "train",
    2026092005: "validation",
    2026092006: "validation",
    2026092007: "validation",
}
INITIALIZATION_SEEDS = (2026092101, 2026092102, 2026092103)
MINIMUM_CLUSTERS = {"train": 40, "validation": 30, "test": 0}
MINIMUM_INFERENCE_ANCHORS = {
    "C1": {"train": 20, "validation": 15, "test": 0},
    "C2": {"train": 12, "validation": 9, "test": 0},
    "C3": {"train": 20, "validation": 15, "test": 0},
}
OLD_SOURCE_SEEDS = tuple(source.SOURCE_SEED_SPLIT)
BURNED_SOURCE_SEEDS = tuple(sorted(set(source.BURNED_SOURCE_SEEDS) | set(OLD_SOURCE_SEEDS)))
SUPPLEMENT_RECEIPT_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-source-supplement-receipt-v1"
)


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _verify_design_seed_split(
    seed_split: Mapping[int, str], *, burned_seeds: Sequence[int]
) -> dict[int, str]:
    normalized = dict(seed_split)
    if normalized != SOURCE_SEED_SPLIT:
        raise source.E1FreshSourceError("action-shared source split must be sealed 4/3/0")
    if any(type(seed) is not int or seed < 0 for seed in normalized):
        raise source.E1FreshSourceError("source seeds must be nonnegative integers")
    if set(normalized.values()) != {"train", "validation"}:
        raise source.E1FreshSourceError("source supplement may contain only train/validation")
    if set(normalized) & set(burned_seeds):
        raise source.E1FreshSourceError("source supplement overlaps a burned seed")
    return normalized


def _verify_design_partition(
    rows: Sequence[Any],
    *,
    seed_split: Mapping[int, str],
    burned_seeds: Sequence[int],
    minimum_clusters: Mapping[str, int] | None = None,
    minimum_inference_anchors: Mapping[str, Mapping[str, int]] | None = None,
) -> E1SplitReceipt:
    split = _verify_design_seed_split(seed_split, burned_seeds=burned_seeds)
    if not rows:
        raise source.E1FreshSourceError("source supplement has no rows")
    for row in rows:
        row.verify()
        if row.source_seed not in split:
            raise source.E1FreshSourceError("row seed is absent from sealed supplement")
    anchor_owner: dict[str, str] = {}
    inference_owner: dict[str, str] = {}
    for row in rows:
        split_name = split[row.source_seed]
        if anchor_owner.setdefault(row.anchor_sha256, split_name) != split_name:
            raise source.E1FreshSourceError("physical anchor crosses design splits")
        if (
            inference_owner.setdefault(row.inference_anchor_sha256, split_name)
            != split_name
        ):
            raise source.E1FreshSourceError("inference anchor crosses design splits")
    verify_full_sibling_groups(rows, route="C1")
    verify_full_sibling_groups(rows, route="C3")
    cluster_minimum = dict(minimum_clusters or MINIMUM_CLUSTERS)
    inference_minimum = {
        route: dict(values)
        for route, values in (
            minimum_inference_anchors or MINIMUM_INFERENCE_ANCHORS
        ).items()
    }
    coverage: list[E1RouteCoverage] = []
    for route in ("C1", "C2", "C3"):
        selected = [row for row in rows if row.route == route]
        cluster_sets = {
            split_name: {
                row.cluster_key
                for row in selected
                if split[row.source_seed] == split_name
            }
            for split_name in ("train", "validation")
        }
        inference_sets = {
            split_name: {
                row.inference_cluster_key
                for row in selected
                if split[row.source_seed] == split_name
            }
            for split_name in ("train", "validation")
        }
        row_counts = {
            split_name: sum(
                split[row.source_seed] == split_name for row in selected
            )
            for split_name in ("train", "validation")
        }
        for split_name in ("train", "validation"):
            if len(cluster_sets[split_name]) < cluster_minimum[split_name]:
                raise source.E1FreshSourceError(
                    f"{route}/{split_name} intervention coverage is insufficient"
                )
            if (
                len(inference_sets[split_name])
                < inference_minimum[route][split_name]
            ):
                raise source.E1FreshSourceError(
                    f"{route}/{split_name} inference coverage is insufficient"
                )
        coverage.append(
            E1RouteCoverage(
                route=route,
                train_clusters=len(cluster_sets["train"]),
                validation_clusters=len(cluster_sets["validation"]),
                test_clusters=0,
                train_inference_anchors=len(inference_sets["train"]),
                validation_inference_anchors=len(inference_sets["validation"]),
                test_inference_anchors=0,
                train_rows=row_counts["train"],
                validation_rows=row_counts["validation"],
                test_rows=0,
            )
        )
    return E1SplitReceipt(
        seed_split=dict(split),
        coverage=tuple(coverage),  # type: ignore[arg-type]
        rows=len(rows),
    )


_original_learner_contract = source._learner_contract
_original_build_preregistration = source._build_preregistration
_original_source_paths = source._source_paths
_original_source_index_payloads = source._source_index_payloads


def _action_shared_learner_contract(*, checkpoint_sha256: str) -> dict[str, Any]:
    payload = _original_learner_contract(checkpoint_sha256=checkpoint_sha256)
    return {
        **payload,
        "algorithm": "multi-catfish-mcrl-ee-axis-v03-action-shared",
        "scorer": "local-action-shared-8-plus-4",
        "selection_baseline_family": ["action-only", "zero", "train-median"],
    }


def _action_shared_preregistration(**kwargs: Any) -> dict[str, Any]:
    payload = _original_build_preregistration(**kwargs)
    body = dict(payload)
    body.pop("prereg_sha256", None)
    body.update(
        {
            "minimum_clusters": MINIMUM_CLUSTERS,
            "minimum_inference_anchors": MINIMUM_INFERENCE_ANCHORS,
            "test_opening_rule": "design-only-supplement-generates-no-test-outcomes",
            "old_e1_validation_status": "DESIGN_ONLY_BURNED_FOR_ARCHITECTURE_SELECTION",
            "existing_e1_test_status": "SEALED_UNOPENED_OUTSIDE_THIS_SUPPLEMENT",
            "validation_release_reason_minimum_world_anchors": {
                "horizon": 3,
                "support_expired": 3,
            },
        }
    )
    return {**body, "prereg_sha256": _canonical_sha256(body)}


def _action_shared_source_paths() -> tuple[Path, ...]:
    additions = (
        Path(__file__).resolve(),
        (REPO / "src/mcrl/algorithms/ee_axis_action_shared.py").resolve(),
        (REPO / "src/mcrl/runtime/ee_axis_instrument_validity.py").resolve(),
    )
    return tuple(sorted(set(_original_source_paths()) | set(additions), key=str))


def _action_shared_source_index_payloads(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    ladder, test = _original_source_index_payloads(**kwargs)
    ladder = {
        **ladder,
        "test_split_present": False,
        "test_split_opened": False,
    }
    return ladder, test


def _install_protocol() -> None:
    source.SOURCE_MANIFEST_SCHEMA = (
        "multi-catfish-mcrl-v03-e1-action-shared-source-manifest-v1"
    )
    source.PREREG_SCHEMA = "multi-catfish-mcrl-v03-e1-action-shared-source-prereg-v1"
    source.PREPARE_RECEIPT_SCHEMA = (
        "multi-catfish-mcrl-v03-e1-action-shared-prepare-receipt-v1"
    )
    source.SOURCE_RECEIPT_SCHEMA = (
        "multi-catfish-mcrl-v03-e1-action-shared-source-receipt-v1"
    )
    source.LADDER_INDEX_SCHEMA = (
        "multi-catfish-mcrl-v03-e1-action-shared-ladder-source-index-v1"
    )
    source.TEST_INDEX_SCHEMA = (
        "multi-catfish-mcrl-v03-e1-action-shared-empty-test-index-v1"
    )
    source.SOURCE_SEED_SPLIT = SOURCE_SEED_SPLIT
    source.INITIALIZATION_SEEDS = INITIALIZATION_SEEDS
    source.BURNED_SOURCE_SEEDS = BURNED_SOURCE_SEEDS
    source.MINIMUM_INFERENCE_ANCHORS = MINIMUM_INFERENCE_ANCHORS
    source.verify_e1_seed_split = _verify_design_seed_split
    source.verify_e1_partition = _verify_design_partition
    source._learner_contract = _action_shared_learner_contract
    source._build_preregistration = _action_shared_preregistration
    source._source_paths = _action_shared_source_paths
    source._source_index_payloads = _action_shared_source_index_payloads


def _release_coverage(output_dir: Path) -> dict[str, object]:
    details = source._read_canonical_json(
        output_dir / "source-data" / "ladder-generation-details.json"
    )
    validation_seeds = {
        seed for seed, split_name in SOURCE_SEED_SPLIT.items() if split_name == "validation"
    }
    anchors_by_reason: dict[str, set[str]] = {}
    for receipt in details.get("temporal_receipts", []):
        if int(receipt.get("source_seed", -1)) not in validation_seeds:
            continue
        for row in receipt.get("rows", []):
            if row.get("outcome") != "COMPLETE_PAIR":
                continue
            reason = str(row.get("release_reason"))
            anchor = source.e1_c2_world_anchor_sha256(
                source_seed=int(row["source_seed"]),
                anchor_step=int(row["anchor_step"]),
            )
            anchors_by_reason.setdefault(reason, set()).add(anchor)
    counts = {reason: len(anchors) for reason, anchors in sorted(anchors_by_reason.items())}
    required = {"horizon": 3, "support_expired": 3}
    sufficient = all(counts.get(reason, 0) >= minimum for reason, minimum in required.items())
    return {
        "validation_release_reason_world_anchors": counts,
        "required_minimum_world_anchors": required,
        "coverage_sufficient": sufficient,
    }


def generate(*, output_dir: Path, tle_root: Path) -> dict[str, Any]:
    result = source.generate(output_dir=output_dir, tle_root=tle_root)
    coverage = _release_coverage(output_dir)
    receipt = {
        "schema": SUPPLEMENT_RECEIPT_SCHEMA,
        "status": "PASS" if coverage["coverage_sufficient"] else "INSUFFICIENT_COVERAGE",
        "claim_ceiling": "FRESH_TRAIN_VALIDATION_SOURCE_ONLY_NO_TEST_NO_EE",
        "source_seed_split": {
            str(seed): split_name for seed, split_name in SOURCE_SEED_SPLIT.items()
        },
        "source_publication_summary": result,
        "release_coverage": coverage,
        "test_outcomes_generated": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    receipt_sha256 = source._write_once_json(
        output_dir / "action-shared-supplement-receipt.json", receipt
    )
    source._write_once_json(
        output_dir / "action-shared-supplement-receipt-seal.json",
        {
            "schema": "multi-catfish-mcrl-v03-e1-action-shared-source-supplement-seal-v1",
            "receipt_file_sha256": receipt_sha256,
        },
    )
    if not coverage["coverage_sufficient"]:
        raise source.E1FreshSourceError(
            "INSUFFICIENT_COVERAGE: validation C2 release-reason geometry"
        )
    return receipt


def verify_supplement(output_dir: Path) -> dict[str, Any]:
    """Authenticate the wrapper receipt in addition to inherited v1 checks.

    This remains a publication-integrity check. The separate independent
    verifier is the only authority for aggregate 40/30 coverage and the
    no-test metadata overlay.
    """

    base = source.verify_published(output_dir)
    receipt_path = output_dir / "action-shared-supplement-receipt.json"
    seal = source._read_canonical_json(
        output_dir / "action-shared-supplement-receipt-seal.json"
    )
    receipt = source._read_canonical_json(receipt_path)
    recomputed = _release_coverage(output_dir)
    if (
        receipt.get("status") != "PASS"
        or receipt.get("test_outcomes_generated") is not False
        or receipt.get("test_split_opened") is not False
        or seal.get("receipt_file_sha256") != source._file_sha256(receipt_path)
        or receipt.get("release_coverage") != recomputed
        or not recomputed["coverage_sufficient"]
    ):
        raise source.E1FreshSourceError("action-shared supplement verification failed")
    return {
        **base,
        "status": "PASS_WRAPPER_INTEGRITY_INDEPENDENT_4_3_0_VERIFY_STILL_REQUIRED",
        "authoritative_4_3_0_pass": False,
        "supplement_receipt_file_sha256": source._file_sha256(receipt_path),
        "test_outcomes_generated": False,
        "test_split_opened": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    _install_protocol()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "generate", "verify"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(source.TLE_ROOT_DEFAULT).expanduser()
    )
    args = parser.parse_args(argv)
    if args.phase == "prepare":
        payload = source.prepare(output_dir=args.output_dir, tle_root=args.tle_root)
    elif args.phase == "generate":
        payload = generate(output_dir=args.output_dir, tle_root=args.tle_root)
    else:
        payload = verify_supplement(args.output_dir)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
