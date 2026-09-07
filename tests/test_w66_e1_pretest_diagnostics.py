"""W-66 -- train/validation-only diagnostics for possible E1 false skill."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.runtime.ee_axis_e1_split import E1PairIndexRow


REPO = Path(__file__).resolve().parents[1]
RUNNER = (
    REPO / ".scratch" / "ee-axis-redesign" / "run_v03_e1_pretest_diagnostics.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("w66_e1_pretest_diagnostics", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _batch(
    references: list[int],
    candidates: list[int],
    targets: list[float],
    *,
    action_dim: int = 3,
) -> EEAxisPairBatch:
    rows = len(targets)
    states = np.arange(rows * 2, dtype=np.float32).reshape(rows, 2)
    masks = np.ones((rows, action_dim), dtype=np.bool_)
    batch = EEAxisPairBatch(
        states=states,
        reference_actions=np.asarray(references, dtype=np.int64),
        candidate_actions=np.asarray(candidates, dtype=np.int64),
        target_surplus_bits=np.asarray(targets, dtype=np.float64),
        action_masks=masks,
    )
    batch.validate(state_dim=2, action_dim=action_dim)
    return batch


def _row(runner, *, route: str, anchor: str, focal: int) -> object:
    index = E1PairIndexRow(
        route=route,
        source_seed=11,
        anchor_sha256=anchor,
        inference_anchor_sha256=anchor,
        focal_user=focal,
        reference_action=0,
        candidate_action=1,
        action_mask=(True, True),
    )
    return runner.E1DiagnosticPairRow(
        split="validation",
        index=index,
        state=np.asarray([float(focal), 1.0], dtype=np.float32),
        action_mask=np.asarray([True, True], dtype=np.bool_),
        normalized_target=0.25,
        policy_sha256="a" * 64,
        comparison_sha256=f"{focal + 1:064x}",
    )


def test_action_incidence_reports_rank_components_residual_df_and_gauge_invariance() -> None:
    runner = _module()
    train = _batch(
        references=[0, 0, 1, 1, 0, 1],
        candidates=[1, 1, 2, 2, 1, 2],
        targets=[1.0, 1.2, 0.5, 0.7, 0.8, 0.6],
    )
    validation = _batch(
        references=[0, 2, 0],
        candidates=[2, 1, 1],
        targets=[1.6, -0.5, 1.0],
    )
    result = runner.action_only_design_diagnostics(
        train_batch=train,
        validation_batch=validation,
        kappa_bits=1.0,
        ridge_penalties=(1e-8, 1e-4, 1e-2),
    )
    assert result.train_rows == 6
    assert result.incidence_rank == 2
    assert result.active_actions == 3
    assert result.connected_components == 1
    assert result.gauge_nullity == 1
    assert result.residual_degrees_of_freedom == 4
    assert result.validation_supported_rows == 3
    assert result.gauge_fixed_max_prediction_delta < 1e-12
    assert len(result.ridge_sensitivity) == 3


def test_saturated_action_baseline_exposes_zero_residual_df_and_ridge_sensitivity() -> None:
    runner = _module()
    train = _batch(
        references=[0, 1],
        candidates=[1, 2],
        targets=[2.0, -1.0],
    )
    validation = _batch(
        references=[0, 0],
        candidates=[2, 1],
        targets=[0.2, 1.5],
    )
    result = runner.action_only_design_diagnostics(
        train_batch=train,
        validation_batch=validation,
        kappa_bits=1.0,
        ridge_penalties=(1e-6, 1.0),
    )
    assert result.incidence_rank == 2
    assert result.residual_degrees_of_freedom == 0
    assert result.low_residual_df
    assert result.ridge_sensitivity[-1].validation_mae != pytest.approx(
        result.minimum_norm_validation_mae
    )


def test_constant_zero_and_action_only_are_reported_beside_model_not_hidden() -> None:
    runner = _module()
    train = _batch(
        references=[0, 0, 1, 1],
        candidates=[1, 2, 2, 0],
        targets=[1.0, 3.0, 2.0, -1.0],
    )
    validation = _batch(
        references=[0, 2],
        candidates=[2, 1],
        targets=[4.0, -1.0],
    )
    design = runner.action_only_design_diagnostics(
        train_batch=train,
        validation_batch=validation,
        kappa_bits=1.0,
        ridge_penalties=(1e-6,),
    )
    q_surface = np.asarray([[0.0, 0.0, 4.0], [0.0, 0.0, 1.0]])
    score = runner.score_validation_surface(
        validation_batch=validation,
        q_surface=q_surface,
        action_only_prediction=design.minimum_norm_validation_prediction,
        kappa_bits=1.0,
    )
    assert score.model_mae == pytest.approx(0.0)
    assert score.constant_zero_mae == pytest.approx(2.5)
    assert score.action_only_mae == pytest.approx(1.0)
    assert score.skill_vs_constant_zero == pytest.approx(1.0)
    assert score.skill_vs_action_only == pytest.approx(1.0)


def test_every_rung_is_compared_to_same_seed_rung_zero() -> None:
    runner = _module()
    scores = {
        0: runner.E1ValidationScore(1.0, 2.0, 1.5, 0.5, 1.0 / 3.0),
        10: runner.E1ValidationScore(0.9, 2.0, 1.5, 0.55, 0.4),
        100: runner.E1ValidationScore(1.2, 2.0, 1.5, 0.4, 0.2),
    }
    compared = runner.compare_rungs_to_untrained(scores)
    assert compared[0].is_untrained
    assert compared[0].model_mae_delta_from_untrained == pytest.approx(0.0)
    assert compared[10].model_mae_delta_from_untrained == pytest.approx(-0.1)
    assert compared[10].skill_vs_action_delta_from_untrained == pytest.approx(
        0.4 - 1.0 / 3.0
    )
    assert compared[100].model_mae_delta_from_untrained == pytest.approx(0.2)


def test_route_aware_cluster_ids_are_derived_from_rows_not_accepted_from_caller() -> None:
    runner = _module()
    c1 = tuple(_row(runner, route="C1", anchor=f"{index + 1:064x}", focal=index) for index in range(3))
    c2 = []
    for focal in range(3):
        index = E1PairIndexRow(
            route="C2",
            source_seed=11,
            anchor_sha256=f"{10 + focal:064x}",
            inference_anchor_sha256="f" * 64,
            focal_user=focal,
            reference_action=0,
            candidate_action=1,
            action_mask=(True, True),
        )
        c2.append(
            runner.E1DiagnosticPairRow(
                split="validation",
                index=index,
                state=np.asarray([float(focal), 1.0], dtype=np.float32),
                action_mask=np.asarray([True, True], dtype=np.bool_),
                normalized_target=0.25,
                policy_sha256="a" * 64,
                comparison_sha256=f"{20 + focal:064x}",
            )
        )
    assert len(set(runner.derive_route_cluster_ids(c1, route="C1"))) == 3
    assert len(set(runner.derive_route_cluster_ids(c2, route="C2"))) == 3
    assert "cluster_ids" not in inspect.signature(
        runner.run_route_reference_action_probe
    ).parameters

