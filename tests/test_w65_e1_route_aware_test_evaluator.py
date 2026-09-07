"""W-65 -- route-aware E1 inference and explicit test-opening seam."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from mcrl.runtime.ee_axis_e1_split import E1PairIndexRow


REPO = Path(__file__).resolve().parents[1]
EVALUATOR = (
    REPO
    / ".scratch"
    / "ee-axis-redesign"
    / "run_v03_e1_route_aware_test_evaluator.py"
)


def _module():
    spec = importlib.util.spec_from_file_location(
        "run_v03_e1_route_aware_test_evaluator_test", EVALUATOR
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _digest(index: int) -> str:
    return f"{index:064x}"


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _opening_authority(tmp_path: Path) -> dict[str, object]:
    source_root = tmp_path / "source"
    data_root = source_root / "source-data"
    ladder_root = tmp_path / "ladder"
    test_seeds = (105, 106)
    seed_split = {
        "101": "train",
        "102": "train",
        "103": "train",
        "104": "validation",
        "105": "test",
        "106": "test",
    }
    opening_dataset_sha256s = {
        seed: _digest(1_000 + int(seed)) for seed in seed_split
    }
    temporal_dataset_sha256s = {
        seed: _digest(2_000 + int(seed)) for seed in seed_split
    }
    opening_file_sha256s = {seed: _digest(3_000 + int(seed)) for seed in seed_split}
    temporal_file_sha256s = {
        seed: _digest(4_000 + int(seed)) for seed in seed_split
    }
    for seed in test_seeds:
        opening = data_root / f"opening-{seed}.json"
        temporal = data_root / f"temporal-{seed}.json"
        opening.parent.mkdir(parents=True, exist_ok=True)
        opening.write_bytes(f"opaque-opening-{seed}\n".encode("ascii"))
        temporal.write_bytes(f"opaque-temporal-{seed}\n".encode("ascii"))
        opening_file_sha256s[str(seed)] = hashlib.sha256(opening.read_bytes()).hexdigest()
        temporal_file_sha256s[str(seed)] = hashlib.sha256(temporal.read_bytes()).hexdigest()

    test_index = {
        "schema": "multi-catfish-mcrl-v03-e1-test-source-index-v1",
        "source_manifest_sha256": "a" * 64,
        "checkpoint_sha256": "b" * 64,
        "seed_split": {str(seed): "test" for seed in test_seeds},
        "datasets": {
            str(seed): {
                "opening_path": f"opening-{seed}.json",
                "opening_dataset_sha256": opening_dataset_sha256s[str(seed)],
                "temporal_path": f"temporal-{seed}.json",
                "temporal_dataset_sha256": temporal_dataset_sha256s[str(seed)],
            }
            for seed in test_seeds
        },
        "held_out_ee_evaluated": False,
        "may_open_only_after_selected_common_rung": True,
    }
    test_index_sha256 = _write_json(data_root / "test-index.json", test_index)
    source_receipt = {
        "schema": "multi-catfish-mcrl-v03-e1-fresh-source-receipt-v1",
        "status": "PASS",
        "claim_ceiling": "FRESH_SOURCE_AND_INSTRUMENT_DATA_ONLY_NOT_EE_EFFICACY",
        "training": False,
        "held_out_ee_evaluated": False,
        "source_manifest_sha256": "a" * 64,
        "checkpoint_sha256": "b" * 64,
        "opening_dataset_sha256s": opening_dataset_sha256s,
        "temporal_dataset_sha256s": temporal_dataset_sha256s,
        "opening_dataset_file_sha256s": opening_file_sha256s,
        "temporal_dataset_file_sha256s": temporal_file_sha256s,
        "test_index_file_sha256": test_index_sha256,
        "split_receipt": {"seed_split": seed_split},
    }
    source_receipt_sha256 = _write_json(data_root / "receipt.json", source_receipt)

    checkpoint_root = ladder_root / "run" / "checkpoints"
    selected_checkpoints: dict[str, dict[str, str]] = {}
    for seed in (11, 22, 33):
        relative = f"checkpoints/init-{seed}-rung-000100.pt"
        path = ladder_root / "run" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"checkpoint-{seed}\n".encode("ascii"))
        selected_checkpoints[str(seed)] = {
            "path": relative,
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    authority_body = {
        "schema": "multi-catfish-mcrl-v03-e1-ladder-authority-v1",
        "claim_ceiling": "NO_EE_INSTRUMENT_VALIDITY_ONLY",
        "source_manifest_sha256": "a" * 64,
        "ladder_spec": {
            "initialization_seeds": [11, 22, 33],
            "source_manifest_sha256": "a" * 64,
            "checkpoint_sha256": "b" * 64,
            "source_receipt_file_sha256": source_receipt_sha256,
            "update_rungs": [10, 100, 1_000, 10_000],
        },
        "source_access_receipt": {
            "source_receipt_file_sha256": source_receipt_sha256,
            "test_dataset_paths_opened": [],
            "test_split_opened": False,
        },
        "execution_device": "cpu",
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    authority_sha256 = hashlib.sha256(
        json.dumps(
            authority_body,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()
    _write_json(
        ladder_root / "authority.json",
        {**authority_body, "authority_sha256": authority_sha256},
    )
    result = {
        "schema": "multi-catfish-mcrl-v03-e1-ladder-result-v1",
        "status": "PASS_VALIDATION_SELECTION_COMPLETE",
        "claim_ceiling": "NO_EE_INSTRUMENT_VALIDITY_ONLY",
        "authority_sha256": authority_sha256,
        "selected_common_rung": 100,
        "selected_checkpoint_files": selected_checkpoints,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    result_sha256 = _write_json(ladder_root / "result.json", result)
    result_seal_sha256 = _write_json(
        ladder_root / "result-seal.json",
        {
            "schema": "multi-catfish-mcrl-v03-e1-ladder-result-seal-v1",
            "result_file_sha256": result_sha256,
            "authority_sha256": authority_sha256,
        },
    )
    return {
        "source_root": source_root,
        "ladder_root": ladder_root,
        "source_receipt_sha256": source_receipt_sha256,
        "result_seal_sha256": result_seal_sha256,
        "test_index": data_root / "test-index.json",
        "result": ladder_root / "result.json",
    }


def _row(
    *,
    route: str,
    seed: int,
    physical_anchor: int,
    world_anchor: int,
    focal_user: int,
) -> E1PairIndexRow:
    return E1PairIndexRow(
        route=route,
        source_seed=seed,
        anchor_sha256=_digest(physical_anchor),
        inference_anchor_sha256=_digest(world_anchor),
        focal_user=focal_user,
        reference_action=0,
        candidate_action=1,
        action_mask=(True, True),
    )


@pytest.mark.parametrize("route", ("C1", "C3"))
def test_opening_resampling_identity_is_derived_from_sealed_inference_anchor(
    route: str,
) -> None:
    evaluator = _module()
    rows = tuple(
        _row(
            route=route,
            seed=101,
            physical_anchor=anchor,
            world_anchor=anchor,
            focal_user=focal,
        )
        for anchor in (1, 2)
        for focal in (10, 11)
    )

    result = evaluator.evaluate_route_pair_skill(
        index_rows=rows,
        model_absolute_errors=np.full(4, 0.5),
        baseline_absolute_errors=np.ones(4),
        point_gate=evaluator.E1PointGate(comparison="at_least", threshold=0.2),
        replications=200,
        confidence=0.95,
        bootstrap_seed=7,
    )

    assert result.route == route
    assert result.resampling_identity == "inference_anchor"
    assert result.primary.clusters == 2
    assert result.primary.estimate == 0.5
    assert result.primary_point_gate_passed is True
    assert result.anchor_balanced_estimate is None
    assert result.leave_one_world_anchor_out == ()
    assert result.evaluator_file_sha256 == hashlib.sha256(
        EVALUATOR.read_bytes()
    ).hexdigest()


def test_c2_primary_uses_interventions_and_reports_balanced_and_every_loo() -> None:
    evaluator = _module()
    rows = tuple(
        _row(
            route="C2",
            seed=105,
            physical_anchor=100 + anchor * 10 + focal,
            world_anchor=anchor,
            focal_user=focal,
        )
        for anchor in (1, 2, 3)
        for focal in (10, 11)
    )

    result = evaluator.evaluate_route_pair_skill(
        index_rows=rows,
        model_absolute_errors=np.asarray([0.2, 0.2, 0.4, 0.4, 0.6, 0.6]),
        baseline_absolute_errors=np.ones(6),
        point_gate=evaluator.E1PointGate(comparison="at_least", threshold=0.2),
        replications=200,
        confidence=0.95,
        bootstrap_seed=13,
    )

    assert result.route == "C2"
    assert result.resampling_identity == "intervention_cluster"
    assert result.primary.clusters == 6
    assert result.primary.estimate == pytest.approx(0.6)
    assert result.anchor_balanced_estimate == pytest.approx(0.6)
    assert result.anchor_balanced_point_gate_passed is True
    assert result.anchor_balanced_direction_matches_primary is True
    assert [row.world_anchor_sha256 for row in result.leave_one_world_anchor_out] == [
        _digest(1),
        _digest(2),
        _digest(3),
    ]
    assert [row.source_seed for row in result.leave_one_world_anchor_out] == [
        105,
        105,
        105,
    ]
    assert [row.estimate for row in result.leave_one_world_anchor_out] == pytest.approx(
        [0.5, 0.6, 0.7]
    )
    assert all(row.point_gate_passed for row in result.leave_one_world_anchor_out)
    assert all(row.direction_matches_primary for row in result.leave_one_world_anchor_out)


def test_c2_anchor_balanced_gate_failure_is_insufficient_coverage() -> None:
    evaluator = _module()
    geometry = (
        (1, 10),
        (1, 11),
        (1, 12),
        (1, 13),
        (2, 20),
        (3, 30),
    )
    rows = tuple(
        _row(
            route="C2",
            seed=105,
            physical_anchor=100 + index,
            world_anchor=anchor,
            focal_user=focal,
        )
        for index, (anchor, focal) in enumerate(geometry)
    )

    with pytest.raises(
        evaluator.E1InsufficientCoverageError,
        match="INSUFFICIENT_COVERAGE: C2 anchor-balanced",
    ):
        evaluator.evaluate_route_pair_skill(
            index_rows=rows,
            model_absolute_errors=np.asarray([0.1, 0.1, 0.1, 0.1, 0.9, 0.9]),
            baseline_absolute_errors=np.ones(6),
            point_gate=evaluator.E1PointGate(
                comparison="at_least", threshold=0.5
            ),
            replications=200,
            confidence=0.95,
            bootstrap_seed=17,
        )


def test_c2_rejects_more_than_five_focal_interventions_per_world_anchor() -> None:
    evaluator = _module()
    geometry = tuple((1, focal) for focal in range(6)) + ((2, 20), (3, 30))
    rows = tuple(
        _row(
            route="C2",
            seed=105,
            physical_anchor=500 + index,
            world_anchor=anchor,
            focal_user=focal,
        )
        for index, (anchor, focal) in enumerate(geometry)
    )
    with pytest.raises(
        evaluator.E1InsufficientCoverageError,
        match="at most five focal",
    ):
        evaluator.evaluate_route_pair_skill(
            index_rows=rows,
            model_absolute_errors=np.full(len(rows), 0.2),
            baseline_absolute_errors=np.ones(len(rows)),
            point_gate=evaluator.E1PointGate(
                comparison="at_least", threshold=0.2
            ),
            replications=200,
            confidence=0.95,
            bootstrap_seed=18,
        )


def test_c2_loo_gate_failure_is_insufficient_coverage() -> None:
    evaluator = _module()
    rows = tuple(
        _row(
            route="C2",
            seed=105,
            physical_anchor=100 + anchor,
            world_anchor=anchor,
            focal_user=anchor,
        )
        for anchor in (1, 2, 3)
    )
    with pytest.raises(
        evaluator.E1InsufficientCoverageError,
        match="leave-one-world-anchor-out",
    ):
        evaluator.evaluate_route_pair_skill(
            index_rows=rows,
            model_absolute_errors=np.asarray([0.2, 0.2, 1.6]),
            baseline_absolute_errors=np.ones(3),
            point_gate=evaluator.E1PointGate(
                comparison="at_least", threshold=0.2
            ),
            replications=200,
            confidence=0.95,
            bootstrap_seed=19,
        )


def test_c2_loo_direction_reversal_is_insufficient_even_if_gate_passes() -> None:
    evaluator = _module()
    rows = tuple(
        _row(
            route="C2",
            seed=105,
            physical_anchor=200 + anchor,
            world_anchor=anchor,
            focal_user=anchor,
        )
        for anchor in (1, 2, 3)
    )
    with pytest.raises(
        evaluator.E1InsufficientCoverageError,
        match="leave-one-world-anchor-out",
    ):
        evaluator.evaluate_route_pair_skill(
            index_rows=rows,
            model_absolute_errors=np.asarray([0.2, 0.2, 2.0]),
            baseline_absolute_errors=np.ones(3),
            point_gate=evaluator.E1PointGate(
                comparison="at_least", threshold=-1.0
            ),
            replications=200,
            confidence=0.95,
            bootstrap_seed=23,
        )


def test_c2_loo_recomputes_primary_intervention_weighted_estimate() -> None:
    evaluator = _module()
    geometry = ((1, 10), (1, 11), (1, 12), (2, 20), (3, 30))
    rows = tuple(
        _row(
            route="C2",
            seed=105,
            physical_anchor=600 + index,
            world_anchor=anchor,
            focal_user=focal,
        )
        for index, (anchor, focal) in enumerate(geometry)
    )
    result = evaluator.evaluate_route_pair_skill(
        index_rows=rows,
        model_absolute_errors=np.asarray([0.1, 0.1, 0.1, 0.8, 0.8]),
        baseline_absolute_errors=np.ones(5),
        point_gate=evaluator.E1PointGate(comparison="at_least", threshold=0.1),
        replications=200,
        confidence=0.95,
        bootstrap_seed=27,
    )

    assert result.primary.estimate == pytest.approx(0.62)
    assert result.anchor_balanced_estimate == pytest.approx(13.0 / 30.0)
    assert [row.estimate for row in result.leave_one_world_anchor_out] == pytest.approx(
        [0.2, 0.725, 0.725]
    )


def test_evaluator_rejects_forged_cluster_ids_and_duplicate_c2_intervention() -> None:
    evaluator = _module()
    rows = (
        _row(
            route="C2",
            seed=105,
            physical_anchor=301,
            world_anchor=1,
            focal_user=10,
        ),
        _row(
            route="C2",
            seed=105,
            physical_anchor=302,
            world_anchor=1,
            focal_user=10,
        ),
        _row(
            route="C2",
            seed=105,
            physical_anchor=303,
            world_anchor=2,
            focal_user=20,
        ),
    )
    with pytest.raises(
        evaluator.E1RouteAwareEvaluationError,
        match="one row per intervention cluster",
    ):
        evaluator.evaluate_route_pair_skill(
            index_rows=rows,
            model_absolute_errors=np.asarray([0.2, 0.2, 0.2]),
            baseline_absolute_errors=np.ones(3),
            point_gate=evaluator.E1PointGate(
                comparison="at_least", threshold=0.2
            ),
            replications=200,
            confidence=0.95,
            bootstrap_seed=29,
        )

    with pytest.raises(TypeError, match="cluster_ids"):
        evaluator.evaluate_route_pair_skill(
            index_rows=rows[:1],
            model_absolute_errors=np.asarray([0.2]),
            baseline_absolute_errors=np.ones(1),
            point_gate=evaluator.E1PointGate(
                comparison="at_least", threshold=0.2
            ),
            replications=200,
            confidence=0.95,
            bootstrap_seed=31,
            cluster_ids=["forged"],
        )


def test_opening_evaluator_rejects_incomplete_legal_sibling_group() -> None:
    evaluator = _module()
    rows = tuple(
        E1PairIndexRow(
            route="C1",
            source_seed=105,
            anchor_sha256=_digest(anchor),
            inference_anchor_sha256=_digest(anchor),
            focal_user=10,
            reference_action=0,
            candidate_action=1,
            action_mask=(True, True, True),
        )
        for anchor in (1, 2)
    )
    with pytest.raises(
        evaluator.E1RouteAwareEvaluationError,
        match="full legal-alternative sibling group",
    ):
        evaluator.evaluate_route_pair_skill(
            index_rows=rows,
            model_absolute_errors=np.asarray([0.2, 0.2]),
            baseline_absolute_errors=np.ones(2),
            point_gate=evaluator.E1PointGate(
                comparison="at_least", threshold=0.2
            ),
            replications=200,
            confidence=0.95,
            bootstrap_seed=37,
        )


def test_authorization_does_not_read_test_index_or_dataset(tmp_path: Path) -> None:
    evaluator = _module()
    authority = _opening_authority(tmp_path)
    Path(authority["test_index"]).unlink()
    for seed in (105, 106):
        (Path(authority["source_root"]) / "source-data" / f"opening-{seed}.json").unlink()
        (Path(authority["source_root"]) / "source-data" / f"temporal-{seed}.json").unlink()

    permit = evaluator.authorize_test_opening(
        source_root=authority["source_root"],
        ladder_root=authority["ladder_root"],
        expected_source_receipt_sha256=authority["source_receipt_sha256"],
        expected_ladder_result_seal_sha256=authority["result_seal_sha256"],
    )

    assert permit.selected_common_rung == 100
    assert permit.test_source_seeds == (105, 106)
    assert permit.evaluator_file_sha256 == hashlib.sha256(
        EVALUATOR.read_bytes()
    ).hexdigest()
    assert not (
        Path(authority["ladder_root"]) / "test-opening-receipt.json"
    ).exists()


def test_open_test_split_reauthorizes_before_touching_test_index(
    tmp_path: Path,
) -> None:
    evaluator = _module()
    authority = _opening_authority(tmp_path)
    permit = evaluator.authorize_test_opening(
        source_root=authority["source_root"],
        ladder_root=authority["ladder_root"],
        expected_source_receipt_sha256=authority["source_receipt_sha256"],
        expected_ladder_result_seal_sha256=authority["result_seal_sha256"],
    )
    Path(authority["result"]).write_bytes(b"{}\n")
    Path(authority["test_index"]).write_bytes(b"not-json\n")

    with pytest.raises(
        evaluator.E1TestOpeningError,
        match="ladder result",
    ):
        evaluator.open_test_split(permit)
    assert not (
        Path(authority["ladder_root"]) / "test-opening-receipt.json"
    ).exists()


def test_explicit_open_seam_authenticates_opaque_test_artifact_paths(
    tmp_path: Path,
) -> None:
    evaluator = _module()
    authority = _opening_authority(tmp_path)
    permit = evaluator.authorize_test_opening(
        source_root=authority["source_root"],
        ladder_root=authority["ladder_root"],
        expected_source_receipt_sha256=authority["source_receipt_sha256"],
        expected_ladder_result_seal_sha256=authority["result_seal_sha256"],
    )

    opening_receipt = (
        Path(authority["ladder_root"]) / "test-opening-receipt.json"
    )
    opened = evaluator.open_test_split(permit)

    assert opened.selected_common_rung == 100
    assert [item.source_seed for item in opened.datasets] == [105, 106]
    assert all(item.opening_path.is_file() for item in opened.datasets)
    assert all(item.temporal_path.is_file() for item in opened.datasets)
    assert opened.test_split_opened is True
    assert opened.held_out_ee_evaluated is False
    assert opened.evaluator_file_sha256 == permit.evaluator_file_sha256
    assert opened.opening_receipt_path == opening_receipt
    assert opened.opening_receipt_file_sha256 == hashlib.sha256(
        opening_receipt.read_bytes()
    ).hexdigest()
    with pytest.raises(evaluator.E1TestOpeningError, match="already exists"):
        evaluator.open_test_split(permit)


def test_crossing_open_seam_burns_once_receipt_before_test_file_validation(
    tmp_path: Path,
) -> None:
    evaluator = _module()
    authority = _opening_authority(tmp_path)
    permit = evaluator.authorize_test_opening(
        source_root=authority["source_root"],
        ladder_root=authority["ladder_root"],
        expected_source_receipt_sha256=authority["source_receipt_sha256"],
        expected_ladder_result_seal_sha256=authority["result_seal_sha256"],
    )
    Path(authority["test_index"]).write_bytes(b"changed-after-authorization\n")
    opening_receipt = (
        Path(authority["ladder_root"]) / "test-opening-receipt.json"
    )

    with pytest.raises(evaluator.E1TestOpeningError, match="test index"):
        evaluator.open_test_split(permit)

    assert opening_receipt.is_file()
    with pytest.raises(evaluator.E1TestOpeningError, match="already exists"):
        evaluator.open_test_split(permit)


def test_independent_evaluator_is_outside_frozen_source_manifest() -> None:
    runner_path = (
        REPO
        / ".scratch"
        / "ee-axis-redesign"
        / "run_v03_e1_fresh_sources.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_v03_e1_fresh_sources_w65_test", runner_path
    )
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    paths = {row["path"] for row in runner._build_source_manifest()["files"]}

    assert (
        ".scratch/ee-axis-redesign/run_v03_e1_route_aware_test_evaluator.py"
        not in paths
    )
