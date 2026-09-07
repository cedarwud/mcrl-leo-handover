"""W-86 -- V0.4 C3 learnability gate contracts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.runtime.ee_axis_v04_c3_learnability import (
    C3V04BalancedGeneralization,
)


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "c3-v04" / "run_v04_c3_learnability_gate.py"


def _module():
    spec = importlib.util.spec_from_file_location("v04_c3_gate_w86", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _surface(runner, *, targets: list[float], duplicate: bool = False):
    rows = len(targets)
    states = np.zeros((rows, runner.STATE_DIM), dtype=np.float32)
    states[:, 0] = np.arange(rows, dtype=np.float32)
    references = np.zeros(rows, dtype=np.int64)
    candidates = np.ones(rows, dtype=np.int64)
    masks = np.ones((rows, runner.ACTION_DIM), dtype=np.bool_)
    batch = EEAxisPairBatch(
        states=states,
        reference_actions=references,
        candidate_actions=candidates,
        target_surplus_bits=np.asarray(targets, dtype=np.float64),
        action_masks=masks,
    )
    if duplicate:
        batch = EEAxisPairBatch(
            states=np.repeat(states[:1], rows, axis=0),
            reference_actions=np.repeat(references[:1], rows),
            candidate_actions=np.repeat(candidates[:1], rows),
            target_surplus_bits=np.asarray(targets, dtype=np.float64),
            action_masks=np.repeat(masks[:1], rows, axis=0),
        )
    batch.validate(state_dim=runner.STATE_DIM, action_dim=runner.ACTION_DIM)
    return runner.C3DatasetSurface(
        batch=batch,
        source_seeds=tuple(1 for _ in range(rows)),
        anchor_sha256s=tuple(
            (chr(97 + index) * 64) for index in range(rows)
        ),
        comparison_sha256s=tuple(
            (chr(65 + index) * 64) for index in range(rows)
        ),
    )


def _report(runner, ratio: float, skill: float):
    return C3V04BalancedGeneralization(
        train_pairs=4,
        heldout_pairs=3,
        active_train_actions=28,
        validation_seeds=3,
        validation_anchors=3,
        model_mae=ratio,
        action_only_baseline_mae=1.0,
        zero_baseline_mae=1.0,
        train_median_value=0.0,
        train_median_baseline_mae=1.0,
        strongest_baseline_name="zero",
        strongest_state_independent_baseline_mae=1.0,
        model_to_strongest_null_mae_ratio=ratio,
        skill_vs_strongest_null=skill,
        model_mae_by_seed=((1, ratio), (2, ratio), (3, ratio)),
        anchor_counts_by_seed=((1, 1), (2, 1), (3, 1)),
    )


def test_collision_census_only_fails_on_conflicting_duplicate_target():
    runner = _module()
    consistent = runner.collision_census(
        _surface(runner, targets=[2.0, 2.0], duplicate=True)
    )
    assert consistent["duplicate_rows"] == 1
    assert consistent["conflicting_target_groups"] == 0
    assert consistent["pass"] is True

    conflicting = runner.collision_census(
        _surface(runner, targets=[2.0, 3.0], duplicate=True)
    )
    assert conflicting["conflicting_target_groups"] == 1
    assert conflicting["conflict_floor_bits"] == 1.0
    assert conflicting["pass"] is False


def test_rung_selection_is_mean_ratio_with_small_rung_tie_break():
    runner = _module()
    reports = {
        seed: {
            rung: _report(runner, ratio=0.8 if rung in (10, 30) else 0.9, skill=0.1)
            for rung in runner.UPDATE_RUNGS
        }
        for seed in runner.INITIALIZATION_SEEDS
    }
    selected, means = runner.select_q3_rung(reports)
    assert selected == 10
    assert means[10] == pytest.approx(0.8)
    assert means[30] == pytest.approx(0.8)


def test_adjudication_requires_two_positive_initializations_and_zero_collision():
    runner = _module()
    reports = {
        seed: {
            10: _report(
                runner,
                ratio=0.9 if index < 2 else 1.1,
                skill=0.1 if index < 2 else -0.1,
            )
        }
        for index, seed in enumerate(runner.INITIALIZATION_SEEDS)
    }
    passed = runner.adjudicate_gate(
        reports=reports,
        selected_q3_rung=10,
        collision_censuses={
            "train": {"pass": True, "conflicting_target_groups": 0, "conflict_floor_bits": 0.0},
            "validation": {"pass": True, "conflicting_target_groups": 0, "conflict_floor_bits": 0.0},
        },
        authority_authenticated=True,
    )
    assert passed["status"] == runner.SUCCESS_STATUS
    assert passed["positive_initializations"] == 2
    assert passed["training"] is True
    assert passed["training_scope"] == "Q3_PAIRWISE_LEARNABILITY_GATE_ONLY"
    assert passed["episode_training"] is False

    blocked = runner.adjudicate_gate(
        reports=reports,
        selected_q3_rung=10,
        collision_censuses={
            "train": {"pass": False, "conflicting_target_groups": 1, "conflict_floor_bits": 1.0},
            "validation": {"pass": True, "conflicting_target_groups": 0, "conflict_floor_bits": 0.0},
        },
        authority_authenticated=True,
    )
    assert blocked["status"] == runner.FAILURE_STATUS
    assert blocked["test_split_opened"] is False
    assert blocked["held_out_ee_evaluated"] is False


def test_combined_collision_census_catches_cross_split_alias():
    runner = _module()
    train = _surface(runner, targets=[2.0])
    validation = _surface(runner, targets=[3.0])
    combined = runner.combine_surfaces(train, validation)
    census = runner.collision_census(combined)
    assert census["rows"] == 2
    assert census["conflicting_target_groups"] == 1
    assert census["pass"] is False


def test_gate_authority_binds_real_v03_result_and_code_manifest(tmp_path: Path):
    runner = _module()
    digest = "b" * 64
    source = runner.SourceAuthority(
        source_dir=REPO / "artifacts" / "not-opened-source",
        source_manifest_sha256=digest,
        source_manifest_file_sha256=digest,
        prereg_file_sha256=digest,
        prereg_digest=digest,
        ephemeris_file_set_sha256=digest,
        main_status_file_sha256=digest,
        main_episode_logs_file_sha256=digest,
        main_checkpoint_sha256=digest,
        smoke_receipt_file_sha256=digest,
        smoke_receipt_seal_file_sha256=digest,
        prepare_receipt_file_sha256=digest,
        prepare_receipt_seal_file_sha256=digest,
        schedule_sha256=digest,
        schedule_file_sha256=digest,
        generate_receipt_file_sha256=digest,
        generate_receipt_seal_file_sha256=digest,
        dataset_file_sha256s={str(seed): digest for seed in runner.EXPECTED_SEED_SPLIT},
        dataset_sha256s={str(seed): digest for seed in runner.EXPECTED_SEED_SPLIT},
        seed_split=runner.EXPECTED_SEED_SPLIT,
    )
    authority = runner.build_gate_authority(
        source=source,
        v03_root=(
            REPO
            / "artifacts"
            / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1"
        ),
        output_dir=tmp_path / "gate",
    )
    assert authority["v03_frozen"]["result_status"] == (
        "STOP_MASKED_MEANMAX_VALIDATION"
    )
    assert authority["v03_frozen"]["carried_routes"] == ["C1", "C2"]
    assert authority["v03_frozen"]["discarded_route"] == "C3"
    assert ".scratch/c3-v04/run_v04_c3_learnability_gate.py" in authority[
        "gate_code_manifest"
    ]
    assert "src/mcrl/runtime/ee_axis_v04_c3_learnability.py" in authority[
        "gate_code_manifest"
    ]
