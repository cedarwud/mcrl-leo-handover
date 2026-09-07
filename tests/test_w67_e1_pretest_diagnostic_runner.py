"""W-67 -- sealed train/validation diagnostic runner never opens E1 test."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest

from mcrl.runtime.ee_axis_e1_split import E1PairIndexRow


REPO = Path(__file__).resolve().parents[1]
RUNNER = (
    REPO / ".scratch" / "ee-axis-redesign" / "run_v03_e1_pretest_diagnostics.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("w67_e1_pretest_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(
    runner,
    *,
    split: str,
    route: str,
    seed: int,
    anchor: int,
    inference_anchor: int,
    focal: int,
    target: float,
    candidate: int = 1,
):
    index = E1PairIndexRow(
        route=route,
        source_seed=seed,
        anchor_sha256=f"{anchor:064x}",
        inference_anchor_sha256=f"{inference_anchor:064x}",
        focal_user=focal,
        reference_action=0,
        candidate_action=candidate,
        action_mask=(True, True, True),
    )
    return runner.E1DiagnosticPairRow(
        split=split,
        index=index,
        state=np.asarray([float(anchor), float(focal)], dtype=np.float32),
        action_mask=np.asarray([True, True, True], dtype=np.bool_),
        normalized_target=target,
        policy_sha256="a" * 64,
        comparison_sha256=f"{1000 + anchor + focal + candidate:064x}",
    )


def test_runner_has_no_test_index_or_opener_seam() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert "test-index.json" not in source
    assert "open_test_split" not in source
    runner = _module()
    assert "test" not in inspect.signature(runner.run).parameters
    assert runner.DIAGNOSTIC_CPU_THREADS == 1


def test_ladder_index_rejects_test_seed_before_any_dataset_reader() -> None:
    runner = _module()
    index = {
        "schema": "multi-catfish-mcrl-v03-e1-ladder-source-index-v1",
        "test_split_opened": False,
        "seed_split": {"1": "train", "2": "validation", "3": "test"},
        "datasets": {
            "1": {"opening_path": "opening-1.json", "temporal_path": "temporal-1.json"},
            "2": {"opening_path": "opening-2.json", "temporal_path": "temporal-2.json"},
            "3": {"opening_path": "forbidden.json", "temporal_path": "forbidden-too.json"},
        },
    }
    with pytest.raises(runner.E1PretestDiagnosticError, match="train/validation"):
        runner._validated_train_validation_entries(
            index=index,
            expected_seed_split={1: "train", 2: "validation"},
        )


def test_persistent_collision_census_combines_train_and_validation_per_route() -> None:
    runner = _module()
    rows = tuple(
        _row(
            runner,
            split="train" if index < 2 else "validation",
            route="C1",
            seed=1 if index < 2 else 2,
            anchor=index + 1,
            inference_anchor=index + 1,
            focal=0,
            target=target,
        )
        for index, target in enumerate((0.06, 0.08, -0.06, -0.09))
    )
    # Exact model input and policy key collide even though sealed provenance
    # anchors differ between the train and validation source seeds.
    aligned = tuple(
        runner.E1DiagnosticPairRow(
            split=row.split,
            index=row.index,
            state=np.asarray([1.0, 0.0], dtype=np.float32),
            action_mask=row.action_mask,
            normalized_target=row.normalized_target,
            policy_sha256=row.policy_sha256,
            comparison_sha256=row.comparison_sha256,
        )
        for row in rows
    )
    report = runner.persistent_collision_report(aligned, route="C1")
    assert report.rows == 4
    assert report.conflicting_sign_groups == 1
    assert report.conflicting_sign_rows == 4


def test_probe_keeps_focal_examples_but_resamples_c1_world_anchor(monkeypatch) -> None:
    runner = _module()
    train = tuple(
        _row(
            runner,
            split="train",
            route="C1",
            seed=1,
            anchor=10 + focal,
            inference_anchor=10 + focal,
            focal=focal,
            target=0.1,
        )
        for focal in range(2)
    )
    validation = []
    for focal in range(2):
        for candidate in (1, 2):
            validation.append(
                _row(
                    runner,
                    split="validation",
                    route="C1",
                    seed=2,
                    anchor=20,
                    inference_anchor=20,
                    focal=focal,
                    target=0.1,
                    candidate=candidate,
                )
            )
    captured = {}

    def fake_probe(**kwargs):
        captured.update(kwargs)
        return "probe-result"

    monkeypatch.setattr(runner, "run_reference_action_probe", fake_probe)
    result = runner.run_route_reference_action_probe(
        train_rows=train,
        validation_rows=tuple(validation),
        route="C1",
        config=object(),
        train_seed=7,
        bootstrap_seed=8,
    )
    assert result == "probe-result"
    assert captured["test_states"].shape[0] == 2
    assert len(captured["test_cluster_ids"]) == 2
    assert len(set(captured["test_cluster_ids"])) == 1


def test_checkpoint_payload_authentication_binds_seed_rung_and_no_test_flags() -> None:
    runner = _module()
    expected_spec = {"run_id": "sealed", "route_order": ["C1", "C2", "C3"]}
    expected_batches = {"train": {"C1": "a"}, "validation": {"C1": "b"}}
    payload = {
        "schema": runner.E1_LADDER_CHECKPOINT_SCHEMA,
        # torch checkpoint state retains tuples while canonical JSON authority
        # serializes them as arrays; the authenticated values are equivalent.
        "spec": {"run_id": "sealed", "route_order": ("C1", "C2", "C3")},
        "batch_digests": expected_batches,
        "initialization_seed": 11,
        "completed_updates_per_head": 10,
        "validation_metrics": {"C1": {}},
        "trainer": {"train_seed": 11, "update_count": 30},
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
    }
    assert runner._verify_checkpoint_payload(
        payload,
        expected_spec=expected_spec,
        expected_batch_digests=expected_batches,
        initialization_seed=11,
        rung=10,
    ) is payload["trainer"]
    bad = {**payload, "test_split_opened": True}
    with pytest.raises(runner.E1PretestDiagnosticError, match="test"):
        runner._verify_checkpoint_payload(
            bad,
            expected_spec=expected_spec,
            expected_batch_digests=expected_batches,
            initialization_seed=11,
            rung=10,
        )


def test_diagnostic_code_manifest_binds_runner_and_numeric_dependencies() -> None:
    runner = _module()
    manifest = runner._diagnostic_code_manifest()
    paths = {row["path"] for row in manifest["files"]}
    assert ".scratch/ee-axis-redesign/run_v03_e1_pretest_diagnostics.py" in paths
    assert "src/mcrl/runtime/ee_axis_e1_statistics.py" in paths
    assert "src/mcrl/runtime/ee_axis_reference_probe.py" in paths
    assert len(manifest["manifest_sha256"]) == 64


def test_probe_bootstrap_degeneracy_is_reported_as_insufficient_coverage(
    monkeypatch,
) -> None:
    runner = _module()
    rows = tuple(
        _row(
            runner,
            split=split,
            route=route,
            seed=1 if split == "train" else 2,
            anchor=10 + route_index,
            inference_anchor=10 + route_index,
            focal=0,
            target=0.1,
        )
        for route_index, route in enumerate(("C1", "C2", "C3"))
        for split in ("train", "validation")
    )

    def degenerate(**_kwargs):
        raise runner.E1StatisticsError(
            "bootstrap statistic produced non-finite values"
        )

    monkeypatch.setattr(runner, "run_route_reference_action_probe", degenerate)
    config = runner.EEAxisPairwiseConfig(
        state_dim=2,
        action_dim=3,
        hidden_layers=(4,),
        activation="tanh",
        learning_rate=1e-3,
        kappa_bits=1.0,
        beta=0.1,
        loss_weights=(1.0, 1.0, 1.0),
    )
    result = runner._probe_diagnostics(
        rows=rows,
        config=config,
        initialization_seeds=(7,),
        updates=1,
        bootstrap_replications=100,
    )
    assert all(result[route]["7"]["status"] == "INSUFFICIENT_COVERAGE" for route in ("C1", "C2", "C3"))
    assert all(not result[route]["7"]["passes_contract_point_and_interval_gate"] for route in ("C1", "C2", "C3"))
