from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


RUNNER = (
    Path(__file__).resolve().parents[1]
    / ".scratch/ee-axis-redesign/run_v03_e1_action_shared_validation.py"
)
SPEC = importlib.util.spec_from_file_location("e1_action_shared_validation", RUNNER)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _receipts(skills: dict[str, float]):
    return {
        seed: {
            rung: {
                route: {
                    "model_to_strongest_null_mae_ratio": (
                        1.0 - skills[route] + rung / 10000
                    ),
                    "skill_vs_strongest_null": skills[route] - rung / 10000,
                }
                for route in runner.ROUTE_NAMES
            }
            for rung in runner.UPDATE_RUNGS
        }
        for seed in (1, 2, 3)
    }


def test_common_rung_uses_strongest_null_ratio_and_smaller_tie() -> None:
    receipts = _receipts({"C1": 0.2, "C2": 0.1, "C3": 0.05})
    selected, means = runner.select_common_rung(
        receipts, initialization_seeds=(1, 2, 3)
    )
    assert selected == 3
    assert set(means) == set(runner.UPDATE_RUNGS)


def test_gate_authorizes_only_bounded_500_when_all_routes_resolve() -> None:
    receipts = _receipts({"C1": 0.2, "C2": 0.1, "C3": 0.05})
    gate = runner._gate(
        selected_rung=3,
        receipts=receipts,
        action_main_effects={"1": 0.1, "2": 0.2, "3": 0.3},
        collisions={route: {"conflicting_sign_groups": 0} for route in runner.ROUTE_NAMES},
        c2_sensitivity={"same_positive_direction": True},
    )
    assert gate["status"] == "GO_500EP_SCREEN_ONLY"


def test_gate_allows_only_one_meanmax_fallback_for_isolated_c3_failure() -> None:
    receipts = _receipts({"C1": 0.2, "C2": 0.1, "C3": -0.05})
    gate = runner._gate(
        selected_rung=3,
        receipts=receipts,
        action_main_effects={"1": 0.1, "2": 0.2, "3": 0.3},
        collisions={route: {"conflicting_sign_groups": 0} for route in runner.ROUTE_NAMES},
        c2_sensitivity={"same_positive_direction": True},
    )
    assert gate["status"] == "EVALUATE_MASKED_MEANMAX_ONCE"

    blocked = runner._gate(
        selected_rung=3,
        receipts=receipts,
        action_main_effects={"1": 0.1, "2": 0.2, "3": 0.3},
        collisions={
            **{route: {"conflicting_sign_groups": 0} for route in runner.ROUTE_NAMES},
            "C2": {"conflicting_sign_groups": 1},
        },
        c2_sensitivity={"same_positive_direction": True},
    )
    assert blocked["status"] == "STOP_ACTION_SHARED_VALIDATION"


def test_config_rejects_free_output_or_beta_drift() -> None:
    prereg = {
        "learner": {
            "algorithm": "old-free-output",
            "scorer": "local-action-shared-8-plus-4",
        }
    }
    with pytest.raises(runner.ActionSharedValidationError, match="not local"):
        runner._config_from_prereg(prereg)


def test_c2_reselects_strongest_null_for_each_estimand() -> None:
    baselines = {
        "action_only": np.asarray([0.1, 9.0, 9.0]),
        "zero": np.asarray([1.0, 1.0, 1.0]),
        "train_median": np.asarray([2.0, 2.0, 2.0]),
    }
    models = {
        1: np.asarray([0.05, 0.5, 0.5]),
        2: np.asarray([0.05, 0.5, 0.5]),
        3: np.asarray([4.0, 4.0, 4.0]),
    }
    balanced = runner._c2_estimand_report(
        baseline_anchor_errors=baselines,
        model_anchor_errors=models,
        keep=np.asarray([True, True, True]),
    )
    first_only = runner._c2_estimand_report(
        baseline_anchor_errors=baselines,
        model_anchor_errors=models,
        keep=np.asarray([True, False, False]),
    )
    assert balanced["strongest_baseline_name"] == "zero"
    assert first_only["strongest_baseline_name"] == "action_only"


def test_c2_estimand_requires_positive_mean_as_well_as_two_positive_seeds() -> None:
    report = runner._c2_estimand_report(
        baseline_anchor_errors={
            "action_only": np.asarray([1.0, 1.0]),
            "zero": np.asarray([2.0, 2.0]),
            "train_median": np.asarray([3.0, 3.0]),
        },
        model_anchor_errors={
            1: np.asarray([0.99, 0.99]),
            2: np.asarray([0.99, 0.99]),
            3: np.asarray([4.0, 4.0]),
        },
        keep=np.asarray([True, True]),
    )
    assert report["positive_initializations"] == 2
    assert report["mean_skill"] < 0.0
    assert report["pass"] is False


def test_independent_verification_requires_external_result_and_seal_digests(
    tmp_path: Path,
) -> None:
    source_receipt = "1" * 64
    validation_authority = "2" * 64
    result = {
        "status": "PASS_INDEPENDENT_4_3_0_NO_TEST",
        "test_outcomes_generated": False,
        "test_dataset_documents_opened": False,
        "held_out_ee_evaluated": False,
        "source_receipt_file_sha256": source_receipt,
        "preoutcome_authority_file_sha256": "3" * 64,
        "validation_preoutcome_authority_file_sha256": validation_authority,
    }
    result_sha = runner.sources._write_once_json(tmp_path / "result.json", result)
    seal_sha = runner.sources._write_once_json(
        tmp_path / "result-seal.json",
        {
            "result_file_sha256": result_sha,
            "preoutcome_authority_file_sha256": "3" * 64,
            "validation_preoutcome_authority_file_sha256": validation_authority,
        },
    )
    loaded = runner._load_independent_source_verification(
        tmp_path,
        expected_source_receipt_sha256=source_receipt,
        expected_result_sha256=result_sha,
        expected_result_seal_sha256=seal_sha,
        expected_validation_preoutcome_authority_sha256=validation_authority,
    )
    assert loaded["result_file_sha256"] == result_sha
    with pytest.raises(runner.ActionSharedValidationError, match="captured digests"):
        runner._load_independent_source_verification(
            tmp_path,
            expected_source_receipt_sha256=source_receipt,
            expected_result_sha256="4" * 64,
            expected_result_seal_sha256=seal_sha,
            expected_validation_preoutcome_authority_sha256=validation_authority,
        )
