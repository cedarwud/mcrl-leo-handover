#!/usr/bin/env python3
"""Independently replay and verify the frozen R3 learnability result."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch


HERE = Path(__file__).resolve().parent

import sys

sys.path.insert(0, str(HERE))

import run_oracle_gate as v1  # noqa: E402
import run_state_learnability_dataset as dataset  # noqa: E402
import run_state_learnability_gate as gate  # noqa: E402
import verify_state_learnability_dataset as dataset_verify  # noqa: E402


EXPECTED_DATASET_RUNNER_SHA256 = (
    "feabafcf3f707446062296fc98a0e01ecc45ea534cf645d2ad4d4cb21cddb547"
)
EXPECTED_DATASET_VERIFIER_SHA256 = (
    "6f8eca4c31a23d926d366e4dde971f9b0c25374de654087ddac1b10f1f882479"
)
EXPECTED_GATE_SHA256 = (
    "9f471f25794689d40ffb091a8e246aa78d028d28e9dabe6a0326bf0bac16a013"
)
EXPECTED_SCHEMA = "mcrl-catfish-r3-heldout-state-learnability-gate-v3.1"
EXPECTED_CLAIM_BOUNDARY = (
    "discarded supervised state-sufficiency probe only; not a runtime "
    "coordinator, TD/RL result, composition result, or long-horizon result"
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--heldout", type=Path, required=True)
    return parser.parse_args()


def _assert_same(actual: Any, expected: Any, *, path: str) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise RuntimeError(f"{path}: mapping keys differ")
        for key, value in expected.items():
            _assert_same(actual[key], value, path=f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise RuntimeError(f"{path}: list shape differs")
        for index, value in enumerate(expected):
            _assert_same(actual[index], value, path=f"{path}[{index}]")
        return
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if actual != expected:
            raise RuntimeError(f"{path}: value differs")
        return
    if isinstance(expected, (float, np.floating)):
        try:
            observed = float(actual)
        except (TypeError, ValueError) as error:
            raise RuntimeError(f"{path}: expected a numeric value") from error
        if not math.isclose(observed, float(expected), rel_tol=1e-11, abs_tol=1e-12):
            raise RuntimeError(
                f"{path}: numeric value differs ({observed!r} != {expected!r})"
            )
        return
    if actual != expected:
        raise RuntimeError(f"{path}: value differs")


def _recompute_conditions(
    *,
    development_verification: dict[str, Any],
    heldout_verification: dict[str, Any],
    classification: dict[str, float | int],
    always: dict[str, Any],
    accepted: dict[str, Any],
    per_seed: dict[str, Any],
    seed_interval: dict[str, Any],
) -> dict[str, Any]:
    prevalence = float(classification["prevalence"])
    ap_required = max(0.30, prevalence + 0.05, 1.25 * prevalence)
    precision_required = max(0.30, 1.5 * prevalence)
    unsafe_limit = max(0.01, float(always["service_unsafe_rate"]) + 0.005)
    seeds_positive_mean = sum(
        row["mean_delta_ee_mbit_per_j"] is not None
        and float(row["mean_delta_ee_mbit_per_j"]) > 0.0
        for row in per_seed.values()
    )
    seeds_with_joint = sum(
        int(row["jointly_positive"]) > 0 for row in per_seed.values()
    )
    seeds_meeting_selection = sum(
        float(row["joint_precision"]) >= 0.30
        and float(row["joint_recall"]) >= 0.20
        and 0.05 <= float(row["coverage"]) <= 0.50
        for row in per_seed.values()
    )
    return {
        "engineering": gate._condition(
            {
                "development": development_verification,
                "heldout": heldout_verification,
            },
            "both dataset verifiers pass",
            True,
        ),
        "auroc": gate._condition(
            classification["auroc"], ">= 0.65", classification["auroc"] >= 0.65
        ),
        "average_precision": gate._condition(
            classification["average_precision"],
            f">= max(0.30, prevalence+0.05, 1.25*prevalence) = {ap_required}",
            classification["average_precision"] >= ap_required,
        ),
        "coverage": gate._condition(
            {"accepted": accepted["accepted_rows"], "coverage": accepted["coverage"]},
            "accepted >= 100 and coverage in [0.10, 0.30]",
            int(accepted["accepted_rows"]) >= 100
            and 0.10 <= float(accepted["coverage"]) <= 0.30,
        ),
        "precision": gate._condition(
            accepted["joint_precision"],
            f">= max(0.30, 1.5*prevalence) = {precision_required}",
            accepted["joint_precision"] >= precision_required,
        ),
        "positive_selected_ee": gate._condition(
            {
                "mean_mbit_per_j": accepted["mean_delta_ee_mbit_per_j"],
                "seed_t95": seed_interval,
                "seeds_positive_mean": seeds_positive_mean,
            },
            "mean > 0, seed-t95 lower > 0, and >=8/10 seeds positive",
            accepted["mean_delta_ee_mbit_per_j"] is not None
            and float(accepted["mean_delta_ee_mbit_per_j"]) > 0.0
            and bool(seed_interval.get("available"))
            and float(seed_interval["descriptive_t95_low_mbit_per_j"]) > 0.0
            and seeds_positive_mean >= 8,
        ),
        "seed_joint_coverage": gate._condition(
            seeds_with_joint,
            ">= 8/10 seeds contain an accepted joint-positive row",
            seeds_with_joint >= 8,
        ),
        "service_safety": gate._condition(
            accepted["service_unsafe_rate"],
            f"<= max(1%, always unsafe+0.5pp) = {unsafe_limit}",
            accepted["service_unsafe_rate"] <= unsafe_limit,
        ),
        "per_seed_selection": gate._condition(
            seeds_meeting_selection,
            ">= 8/10 seeds each precision>=0.30, recall>=0.20, coverage 0.05..0.50",
            seeds_meeting_selection >= 8,
        ),
    }


def verify(
    payload: dict[str, Any],
    *,
    development_path: Path,
    heldout_path: Path,
) -> dict[str, Any]:
    file_contracts = {
        HERE / "run_state_learnability_dataset.py": EXPECTED_DATASET_RUNNER_SHA256,
        HERE / "verify_state_learnability_dataset.py": (
            EXPECTED_DATASET_VERIFIER_SHA256
        ),
        HERE / "run_state_learnability_gate.py": EXPECTED_GATE_SHA256,
    }
    for path, expected_sha256 in file_contracts.items():
        if v1._sha256(path) != expected_sha256:
            raise RuntimeError(f"frozen file digest changed: {path.name}")

    if payload.get("schema") != EXPECTED_SCHEMA or payload.get("status") != "complete":
        raise RuntimeError("learnability result schema/status mismatch")
    if payload.get("claim_boundary") != EXPECTED_CLAIM_BOUNDARY:
        raise RuntimeError("learnability result claim boundary changed")
    if payload.get("spec_sha256") != dataset.SPEC_SHA256:
        raise RuntimeError("learnability result base-spec digest changed")
    if payload.get("amendment_sha256") != dataset.AMENDMENT_SHA256:
        raise RuntimeError("learnability result amendment digest changed")
    if payload.get("analysis_sha256") != EXPECTED_GATE_SHA256:
        raise RuntimeError("learnability result fitter digest changed")
    if payload.get("development_sha256") != v1._sha256(development_path):
        raise RuntimeError("learnability result development receipt differs")
    if payload.get("heldout_sha256") != v1._sha256(heldout_path):
        raise RuntimeError("learnability result heldout receipt differs")

    development = json.loads(development_path.read_text(encoding="utf-8"))
    heldout = json.loads(heldout_path.read_text(encoding="utf-8"))
    development_verification = dataset_verify.verify(
        development, partition="development"
    )
    heldout_verification = dataset_verify.verify(heldout, partition="heldout")
    development_rows = gate._sorted_evaluated_rows(development)
    heldout_rows = gate._sorted_evaluated_rows(heldout)
    fit_rows = [
        row
        for row in development_rows
        if int(row["evaluation_seed"]) in gate.FIT_SEEDS
    ]
    calibration_rows = [
        row
        for row in development_rows
        if int(row["evaluation_seed"]) in gate.CALIBRATION_SEEDS
    ]
    if len(fit_rows) != 800 or len(calibration_rows) != 200:
        raise RuntimeError("learnability result development partitions changed")
    if len(heldout_rows) != 1000:
        raise RuntimeError("learnability result heldout row count changed")

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    networks = []
    member_receipts = []
    for seed in gate.ENSEMBLE_SEEDS:
        network, receipt = gate._fit_member(fit_rows, seed=seed)
        networks.append(network)
        member_receipts.append(receipt)
    calibration_member_scores = [
        gate._scores(network, calibration_rows) for network in networks
    ]
    calibration_scores = np.mean(calibration_member_scores, axis=0)
    threshold = float(
        np.quantile(
            calibration_scores, gate.CALIBRATION_QUANTILE, method="linear"
        )
    )
    heldout_member_scores = [
        gate._scores(network, heldout_rows) for network in networks
    ]
    heldout_scores = np.mean(heldout_member_scores, axis=0)
    classification = gate._classification_metrics(heldout_rows, heldout_scores)
    member_metrics = [
        gate._classification_metrics(heldout_rows, scores)
        for scores in heldout_member_scores
    ]
    sinr_scores = np.asarray(
        [float(row["proposal_candidate_sinr"]) for row in heldout_rows],
        dtype=np.float64,
    )
    sinr_baseline = gate._classification_metrics(heldout_rows, sinr_scores)
    always = gate._accepted_metrics(
        heldout_rows, np.ones(len(heldout_rows), dtype=bool)
    )
    accepted_mask = heldout_scores >= threshold
    accepted = gate._accepted_metrics(heldout_rows, accepted_mask)
    per_seed = gate._per_seed_metrics(heldout_rows, heldout_scores, threshold)
    seed_interval = gate._seed_t_interval(per_seed)
    conditions = _recompute_conditions(
        development_verification=development_verification,
        heldout_verification=heldout_verification,
        classification=classification,
        always=always,
        accepted=accepted,
        per_seed=per_seed,
        seed_interval=seed_interval,
    )
    passed = all(bool(condition["passed"]) for condition in conditions.values())
    predictions = [
        {
            "evaluation_seed": int(row["evaluation_seed"]),
            "step_index": int(row["step_index"]),
            "focal_user": int(row["focal_user"]),
            "proposal_action": int(row["proposal_action"]),
            "score": float(score),
            "accepted": bool(score >= threshold),
            "jointly_positive": bool(row["jointly_positive"]),
            "delta_ee_mbit_per_j": float(row["delta_ee_bits_per_j"]) / 1e6,
            "service_safe": bool(row["service_safe"]),
        }
        for row, score in zip(heldout_rows, heldout_scores, strict=True)
    ]
    model_config = {
        "architecture": [dataset.STATE_DIM, *gate.HIDDEN_LAYERS, 28],
        "activation": "tanh",
        "fit_seeds": list(gate.FIT_SEEDS),
        "calibration_seeds": list(gate.CALIBRATION_SEEDS),
        "heldout_seeds": list(dataset.HELDOUT_SEEDS),
        "ensemble_seeds": list(gate.ENSEMBLE_SEEDS),
        "epochs": gate.EPOCHS,
        "batch_size": gate.BATCH_SIZE,
        "learning_rate": gate.LEARNING_RATE,
        "weight_decay": gate.WEIGHT_DECAY,
        "positive_class_weight": "fit_negative_count / fit_positive_count",
        "threshold_rule": "linear 80th percentile of calibration scores",
        "threshold": threshold,
    }
    expected_sections = {
        "development_verification": development_verification,
        "heldout_verification": heldout_verification,
        "model_config": model_config,
        "member_receipts": member_receipts,
        "member_heldout_metrics": member_metrics,
        "calibration_metrics": gate._classification_metrics(
            calibration_rows, calibration_scores
        ),
        "heldout_classification": classification,
        "sinr_only_baseline": sinr_baseline,
        "always_propose_baseline": always,
        "accepted_metrics": accepted,
        "per_seed_accepted_metrics": per_seed,
        "accepted_seed_t95": seed_interval,
        "pass_conditions": conditions,
        "heldout_predictions": predictions,
    }
    for name, expected in expected_sections.items():
        _assert_same(payload.get(name), expected, path=name)
    expected_decision = (
        "PASS_STATE_SUFFICIENCY_ONLY" if passed else "FAIL_BLOCK_R3_REWARD_TRAINING"
    )
    if payload.get("threshold_pass") is not passed:
        raise RuntimeError("learnability result threshold-pass flag differs")
    if payload.get("decision") != expected_decision:
        raise RuntimeError("learnability result decision differs")
    return {
        "status": "verified",
        "decision": expected_decision,
        "threshold_pass": passed,
        "heldout_rows": len(heldout_rows),
        "heldout_jointly_positive": int(
            sum(bool(row["jointly_positive"]) for row in heldout_rows)
        ),
        "accepted_rows": int(accepted["accepted_rows"]),
        "accepted_jointly_positive": int(accepted["jointly_positive"]),
    }


def main() -> int:
    args = _arguments()
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    result = verify(
        payload,
        development_path=args.development,
        heldout_path=args.heldout,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
