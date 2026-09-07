#!/usr/bin/env python3
"""Independently verify the 4/3/0 action-shared source supplement.

The inherited base verifier is necessary but insufficient because its return
schema assumes a 3/1/2 publication.  This verifier authenticates the external
pre-C2 authority, recomputes 40/30 route coverage and C2 release coverage,
and emits an explicit no-test metadata overlay.
"""

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
    "e1_action_shared_sources",
    HERE / "run_v03_e1_action_shared_sources.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load action-shared source runner")
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
wrapper._install_protocol()
source = wrapper.source

from mcrl.runtime.ee_axis_e1_split import verify_full_sibling_groups  # noqa: E402
from mcrl.runtime.ee_axis_opening_dataset import read_opening_dataset  # noqa: E402
from mcrl.runtime.ee_axis_temporal_dataset import read_temporal_dataset  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v03-e1-action-shared-independent-source-verification-v1"
VALIDATION_PREOUTCOME_SCHEMA = (
    "multi-catfish-mcrl-v03-e1-action-shared-validation-preoutcome-authority-v1"
)


class IndependentSourceVerificationError(RuntimeError):
    """The source supplement does not satisfy the pre-outcome authority."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    return source._read_canonical_json(path)


def _read_hash_bound_json(path: Path) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in pairs:
            if key in payload:
                raise IndependentSourceVerificationError(
                    f"duplicate JSON key in hash-bound authority: {key}"
                )
            payload[key] = value
        return payload

    try:
        payload = json.loads(
            path.read_text(encoding="ascii"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IndependentSourceVerificationError(
            f"cannot parse hash-bound authority: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise IndependentSourceVerificationError("hash-bound authority is not an object")
    return payload


def _validation_preoutcome_authority(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    if path.is_symlink() or _sha256(path) != expected_sha256:
        raise IndependentSourceVerificationError(
            "validation pre-outcome authority changed"
        )
    authority = _read_hash_bound_json(path)
    verifier_relative = (
        ".scratch/ee-axis-redesign/verify_v03_e1_action_shared_sources.py"
    )
    manifest = authority.get("code_manifest")
    if (
        authority.get("schema") != VALIDATION_PREOUTCOME_SCHEMA
        or authority.get("status")
        != "SEALED_AFTER_COLLECTION_BEFORE_ANY_OUTCOME_INSPECTION"
        or authority.get("test_outcomes_authorized") is not False
        or authority.get("held_out_ee_authorized") is not False
        or not isinstance(authority.get("validation_gate_contract"), dict)
        or not isinstance(manifest, dict)
        or manifest.get(verifier_relative) != _sha256(Path(__file__))
    ):
        raise IndependentSourceVerificationError(
            "validation pre-outcome verifier closure changed"
        )
    return authority


def _coverage(source_root: Path, prereg: dict[str, Any]) -> tuple[dict[str, Any], list[Any]]:
    data_root = source_root / "source-data"
    index = _read(data_root / "ladder-index.json")
    expected_split = {
        str(seed): split_name
        for seed, split_name in sorted(wrapper.SOURCE_SEED_SPLIT.items())
    }
    if index.get("seed_split") != expected_split:
        raise IndependentSourceVerificationError("ladder split is not sealed 4/3/0")
    datasets = index.get("datasets")
    if not isinstance(datasets, dict) or set(datasets) != set(expected_split):
        raise IndependentSourceVerificationError("ladder datasets are incomplete")
    rows: list[Any] = []
    temporal_rows: list[Any] = []
    for seed_text in expected_split:
        seed = int(seed_text)
        entry = datasets[seed_text]
        opening_path = data_root / f"opening-{seed}.json"
        temporal_path = data_root / f"temporal-{seed}.json"
        if (
            entry.get("opening_path") != opening_path.name
            or entry.get("temporal_path") != temporal_path.name
            or opening_path.is_symlink()
            or temporal_path.is_symlink()
        ):
            raise IndependentSourceVerificationError("dataset path changed")
        opening = read_opening_dataset(opening_path)
        temporal = read_temporal_dataset(temporal_path)
        if (
            opening.verify() != entry.get("opening_dataset_sha256")
            or temporal.verify() != entry.get("temporal_dataset_sha256")
            or opening.source_manifest_sha256 != prereg["source_manifest_sha256"]
            or temporal.source_manifest_sha256 != prereg["source_manifest_sha256"]
        ):
            raise IndependentSourceVerificationError("dataset content or lineage changed")
        rows.extend(source._index_opening(opening, source_seed=seed))
        indexed_temporal = source._index_temporal(temporal)
        rows.extend(indexed_temporal)
        temporal_rows.extend(temporal.rows)
    verify_full_sibling_groups(rows, route="C1")
    verify_full_sibling_groups(rows, route="C3")
    coverage: dict[str, Any] = {}
    for route in ("C1", "C2", "C3"):
        route_rows = [row for row in rows if row.route == route]
        route_result: dict[str, Any] = {}
        for split_name in ("train", "validation"):
            selected = [
                row
                for row in route_rows
                if wrapper.SOURCE_SEED_SPLIT[row.source_seed] == split_name
            ]
            route_result[split_name] = {
                "rows": len(selected),
                "intervention_clusters": len({row.cluster_key for row in selected}),
                "inference_anchors": len(
                    {row.inference_cluster_key for row in selected}
                ),
            }
            required_clusters = wrapper.MINIMUM_CLUSTERS[split_name]
            required_anchors = wrapper.MINIMUM_INFERENCE_ANCHORS[route][split_name]
            if (
                route_result[split_name]["intervention_clusters"] < required_clusters
                or route_result[split_name]["inference_anchors"] < required_anchors
            ):
                raise IndependentSourceVerificationError(
                    f"{route}/{split_name} does not meet 4/3/0 coverage"
                )
        coverage[route] = route_result
    return coverage, temporal_rows


def verify(
    *,
    source_root: Path,
    output_dir: Path,
    expected_preoutcome_authority_sha256: str,
    validation_preoutcome_authority_path: Path,
    expected_validation_preoutcome_authority_sha256: str,
) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("refusing to overwrite independent source verification")
    authority_path = source_root / "e1-action-shared-preoutcome-authority-20260901.json"
    authority_seal_path = (
        source_root / "e1-action-shared-preoutcome-authority-seal-20260901.json"
    )
    authority = _read_hash_bound_json(authority_path)
    authority_seal = _read_hash_bound_json(authority_seal_path)
    validation_authority = _validation_preoutcome_authority(
        validation_preoutcome_authority_path,
        expected_sha256=expected_validation_preoutcome_authority_sha256,
    )
    if (
        _sha256(authority_path) != expected_preoutcome_authority_sha256
        or authority_seal.get("authority_file_sha256") != _sha256(authority_path)
        or authority.get("status") != "SEALED_DURING_OPENING_BEFORE_ANY_C2_OUTCOME"
        or authority.get("new_test_outcomes_authorized") is not False
        or validation_authority.get("source_preoutcome_authority_file_sha256")
        != expected_preoutcome_authority_sha256
    ):
        raise IndependentSourceVerificationError("pre-C2 authority or seal changed")
    manifest, prereg, _schedule_seals = source._load_authority(source_root)
    if (
        prereg["prereg_sha256"] != authority["source_prereg_sha256"]
        or manifest["source_manifest_sha256"] != authority["source_manifest_sha256"]
        or prereg["source_seed_split"] != authority["source_seed_split"]
        or _sha256(HERE / "run_v03_e1_action_shared_sources.py")
        != authority["source_runner_sha256"]
    ):
        raise IndependentSourceVerificationError("source authority differs from pre-C2 seal")

    base_verification = source.verify_published(source_root)
    if base_verification.get("status") != "PASS":
        raise IndependentSourceVerificationError("inherited base verification failed")
    data_root = source_root / "source-data"
    public_receipt = _read(data_root / "receipt.json")
    supplement_path = source_root / "action-shared-supplement-receipt.json"
    supplement_seal_path = source_root / "action-shared-supplement-receipt-seal.json"
    supplement = _read(supplement_path)
    supplement_seal = _read(supplement_seal_path)
    if (
        supplement.get("status") != "PASS"
        or supplement.get("test_outcomes_generated") is not False
        or supplement.get("test_split_opened") is not False
        or supplement_seal.get("receipt_file_sha256") != _sha256(supplement_path)
    ):
        raise IndependentSourceVerificationError("supplement receipt or seal failed")

    test_index = _read(data_root / "test-index.json")
    test_details = _read(data_root / "test-generation-details.json")
    if (
        test_index.get("seed_split") != {}
        or test_index.get("datasets") != {}
        or test_details.get("source_seeds") != []
        or test_details.get("opening_receipts") != []
        or test_details.get("temporal_receipts") != []
        or any(row.get("split") == "test" for row in public_receipt["coverage_by_seed"])
    ):
        raise IndependentSourceVerificationError("publication contains a new test outcome")

    coverage, temporal_rows = _coverage(source_root, prereg)
    validation_seeds = {
        seed
        for seed, split_name in wrapper.SOURCE_SEED_SPLIT.items()
        if split_name == "validation"
    }
    anchors_by_reason: dict[str, set[tuple[int, int]]] = {}
    for row in temporal_rows:
        if int(row.seed) in validation_seeds:
            anchors_by_reason.setdefault(str(row.release_reason), set()).add(
                (int(row.seed), int(row.step_index))
            )
    release_counts = {
        reason: len(anchors) for reason, anchors in sorted(anchors_by_reason.items())
    }
    required_release = authority["c2_release_reason_minimum_world_anchors"]
    if any(
        release_counts.get(reason, 0) < int(minimum)
        for reason, minimum in required_release.items()
    ):
        raise IndependentSourceVerificationError("C2 release-reason coverage is insufficient")
    recorded_release = supplement.get("release_coverage", {}).get(
        "validation_release_reason_world_anchors"
    )
    if recorded_release != release_counts:
        raise IndependentSourceVerificationError("supplement release coverage was not reproducible")

    metadata_overlay = {
        "schema": "multi-catfish-mcrl-v03-e1-action-shared-no-test-overlay-v1",
        "base_ladder_test_split_present_field": True,
        "effective_test_split_present": False,
        "reason": "inherited v1 field with empty test seed and dataset maps",
        "test_index_file_sha256": _sha256(data_root / "test-index.json"),
        "test_generation_details_file_sha256": _sha256(
            data_root / "test-generation-details.json"
        ),
        "new_test_outcomes_generated": False,
    }
    output_dir.mkdir(parents=True)
    overlay_sha256 = source._write_once_json(
        output_dir / "no-test-metadata-overlay.json", metadata_overlay
    )
    result = {
        "schema": SCHEMA,
        "status": "PASS_INDEPENDENT_4_3_0_NO_TEST",
        "claim_ceiling": "FRESH_TRAIN_VALIDATION_SOURCE_ONLY_NO_TEST_NO_EE",
        "preoutcome_authority_file_sha256": _sha256(authority_path),
        "validation_preoutcome_authority_file_sha256": (
            expected_validation_preoutcome_authority_sha256
        ),
        "source_receipt_file_sha256": _sha256(data_root / "receipt.json"),
        "supplement_receipt_file_sha256": _sha256(supplement_path),
        "coverage": coverage,
        "validation_release_reason_world_anchors": release_counts,
        "no_test_metadata_overlay_file_sha256": overlay_sha256,
        "base_verification_status": base_verification["status"],
        "test_outcomes_generated": False,
        "test_dataset_documents_opened": False,
        "held_out_ee_evaluated": False,
    }
    result_sha256 = source._write_once_json(output_dir / "result.json", result)
    seal_sha256 = source._write_once_json(
        output_dir / "result-seal.json",
        {
            "schema": f"{SCHEMA}-seal",
            "result_file_sha256": result_sha256,
            "preoutcome_authority_file_sha256": _sha256(authority_path),
            "validation_preoutcome_authority_file_sha256": (
                expected_validation_preoutcome_authority_sha256
            ),
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-preoutcome-authority-sha256", required=True)
    parser.add_argument("--validation-preoutcome-authority", type=Path, required=True)
    parser.add_argument(
        "--expected-validation-preoutcome-authority-sha256", required=True
    )
    args = parser.parse_args(argv)
    payload = verify(
        source_root=args.source_root,
        output_dir=args.output_dir,
        expected_preoutcome_authority_sha256=args.expected_preoutcome_authority_sha256,
        validation_preoutcome_authority_path=args.validation_preoutcome_authority,
        expected_validation_preoutcome_authority_sha256=(
            args.expected_validation_preoutcome_authority_sha256
        ),
    )
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
