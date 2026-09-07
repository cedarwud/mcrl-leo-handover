#!/usr/bin/env python3
"""Fit the frozen Q-head-shaped proxy and adjudicate untouched held-out rows."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import torch
from torch import nn


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import run_oracle_gate as v1  # noqa: E402
import run_state_learnability_dataset as dataset  # noqa: E402
import verify_state_learnability_dataset as dataset_verify  # noqa: E402
from mcrl.runtime.q_network import DQNNetwork  # noqa: E402


FIT_SEEDS = dataset.DEVELOPMENT_SEEDS[:8]
CALIBRATION_SEEDS = dataset.DEVELOPMENT_SEEDS[8:]
ENSEMBLE_SEEDS = (730001, 730002, 730003)
HIDDEN_LAYERS = (100, 50, 50)
EPOCHS = 300
BATCH_SIZE = 128
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
CALIBRATION_QUANTILE = 0.80
T975_DF9 = 2.2621571628540993


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--heldout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _sorted_evaluated_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for rollout in payload["rollouts"]
        for row in rollout["proposal_rows"]
        if row["status"] == "evaluated"
    ]
    return sorted(
        rows,
        key=lambda row: (
            int(row["evaluation_seed"]),
            int(row["step_index"]),
            int(row["focal_user"]),
            int(row["proposal_action"]),
        ),
    )


def _model_tensors(
    rows: Sequence[dict[str, Any]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Build the only three tensors exposed to supervised fitting/scoring."""
    states = np.asarray(
        [row["focal_encoded_state"] for row in rows], dtype=np.float32
    )
    actions = np.asarray([row["proposal_action"] for row in rows], dtype=np.int64)
    labels = np.asarray(
        [float(bool(row["jointly_positive"])) for row in rows], dtype=np.float32
    )
    if states.shape != (len(rows), dataset.STATE_DIM):
        raise RuntimeError("model input is not an N x 112 focal-state tensor")
    if not np.all(np.isfinite(states)):
        raise RuntimeError("model input contains non-finite focal state")
    if actions.shape != (len(rows),) or np.any((actions < 0) | (actions >= 28)):
        raise RuntimeError("model proposal actions are invalid")
    if labels.shape != (len(rows),) or not set(np.unique(labels)).issubset({0.0, 1.0}):
        raise RuntimeError("model labels are not binary")
    return (
        torch.from_numpy(states),
        torch.from_numpy(actions),
        torch.from_numpy(labels),
    )


def _selected_logits(
    network: DQNNetwork, states: torch.Tensor, actions: torch.Tensor
) -> torch.Tensor:
    outputs = network(states)
    return outputs[torch.arange(actions.shape[0]), actions]


def _fit_member(
    rows: Sequence[dict[str, Any]],
    *,
    seed: int,
    epochs: int = EPOCHS,
) -> tuple[DQNNetwork, dict[str, Any]]:
    states, actions, labels = _model_tensors(rows)
    positives = int(labels.sum().item())
    negatives = int(labels.numel() - positives)
    if positives == 0 or negatives == 0:
        raise RuntimeError("fit partition must contain both labels")
    torch.manual_seed(seed)
    network = DQNNetwork(
        dataset.STATE_DIM, 28, HIDDEN_LAYERS, activation="tanh"
    ).cpu()
    optimizer = torch.optim.Adam(
        network.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor(float(negatives / positives), dtype=torch.float32)
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    final_loss = math.nan
    network.train()
    for _epoch in range(epochs):
        permutation = torch.randperm(states.shape[0], generator=generator)
        weighted_loss_sum = 0.0
        for start in range(0, states.shape[0], BATCH_SIZE):
            indices = permutation[start : start + BATCH_SIZE]
            optimizer.zero_grad(set_to_none=True)
            logits = _selected_logits(network, states[indices], actions[indices])
            loss = criterion(logits, labels[indices])
            loss.backward()
            optimizer.step()
            weighted_loss_sum += float(loss.item()) * int(indices.numel())
        final_loss = weighted_loss_sum / states.shape[0]
    buffer = io.BytesIO()
    torch.save(network.state_dict(), buffer)
    return network, {
        "seed": seed,
        "epochs": epochs,
        "final_weighted_bce": final_loss,
        "state_dict_sha256": hashlib.sha256(buffer.getvalue()).hexdigest(),
    }


def _scores(network: DQNNetwork, rows: Sequence[dict[str, Any]]) -> np.ndarray:
    states, actions, _labels = _model_tensors(rows)
    network.eval()
    with torch.no_grad():
        return torch.sigmoid(_selected_logits(network, states, actions)).numpy()


def _rankdata_average(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = 0.5 * ((start + 1) + end)
        ranks[order[start:end]] = average_rank
        start = end
    return ranks


def _auroc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive = labels.astype(bool)
    n_positive = int(positive.sum())
    n_negative = int(labels.size - n_positive)
    if n_positive == 0 or n_negative == 0:
        raise RuntimeError("AUROC requires both classes")
    ranks = _rankdata_average(scores)
    return float(
        (ranks[positive].sum() - n_positive * (n_positive + 1) / 2)
        / (n_positive * n_negative)
    )


def _average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    positive_count = int(labels.sum())
    if positive_count == 0:
        raise RuntimeError("average precision requires a positive example")
    order = np.argsort(-scores, kind="mergesort")
    ordered = labels[order].astype(np.float64)
    precision = np.cumsum(ordered) / np.arange(1, ordered.size + 1)
    return float((precision * ordered).sum() / positive_count)


def _classification_metrics(
    rows: Sequence[dict[str, Any]], scores: np.ndarray
) -> dict[str, float | int]:
    labels = np.asarray(
        [float(bool(row["jointly_positive"])) for row in rows], dtype=np.float64
    )
    return {
        "rows": len(rows),
        "prevalence": float(labels.mean()),
        "auroc": _auroc(labels, scores),
        "average_precision": _average_precision(labels, scores),
    }


def _accepted_metrics(
    rows: Sequence[dict[str, Any]], accepted: np.ndarray
) -> dict[str, Any]:
    if accepted.shape != (len(rows),):
        raise RuntimeError("acceptance mask shape mismatch")
    selected = [row for row, keep in zip(rows, accepted, strict=True) if bool(keep)]
    positives = sum(bool(row["jointly_positive"]) for row in selected)
    total_positives = sum(bool(row["jointly_positive"]) for row in rows)
    prevalence = float(total_positives / len(rows)) if rows else 0.0
    precision = float(positives / len(selected)) if selected else 0.0
    delta_ee = [float(row["delta_ee_bits_per_j"]) / 1e6 for row in selected]
    return {
        "eligible_rows": len(rows),
        "accepted_rows": len(selected),
        "coverage": float(len(selected) / len(rows)) if rows else 0.0,
        "jointly_positive": positives,
        "joint_prevalence": prevalence,
        "joint_precision": precision,
        "joint_precision_lift_over_prevalence": (
            float(precision / prevalence) if prevalence > 0.0 else None
        ),
        "joint_recall": float(positives / total_positives) if total_positives else 0.0,
        "mean_delta_ee_mbit_per_j": (
            statistics.fmean(delta_ee) if delta_ee else None
        ),
        "median_delta_ee_mbit_per_j": (
            statistics.median(delta_ee) if delta_ee else None
        ),
        "mean_delta_throughput_gbit_per_s": (
            statistics.fmean(
                float(row["delta_throughput_bps"]) / 1e9 for row in selected
            )
            if selected
            else None
        ),
        "mean_delta_power_w": (
            statistics.fmean(float(row["delta_power_w"]) for row in selected)
            if selected
            else None
        ),
        "service_unsafe": sum(not bool(row["service_safe"]) for row in selected),
        "service_unsafe_rate": (
            sum(not bool(row["service_safe"]) for row in selected) / len(selected)
            if selected
            else 0.0
        ),
    }


def _per_seed_metrics(
    rows: Sequence[dict[str, Any]], scores: np.ndarray, threshold: float
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for seed in dataset.HELDOUT_SEEDS:
        indices = [
            index
            for index, row in enumerate(rows)
            if int(row["evaluation_seed"]) == seed
        ]
        seed_rows = [rows[index] for index in indices]
        accepted = np.asarray([scores[index] >= threshold for index in indices])
        output[str(seed)] = _accepted_metrics(seed_rows, accepted)
    return output


def _seed_t_interval(per_seed: dict[str, Any]) -> dict[str, Any]:
    means = [row["mean_delta_ee_mbit_per_j"] for row in per_seed.values()]
    if any(value is None for value in means):
        return {"available": False, "reason": "a held-out seed accepted no rows"}
    numeric = [float(value) for value in means]
    mean = statistics.fmean(numeric)
    standard_error = statistics.stdev(numeric) / math.sqrt(len(numeric))
    return {
        "available": True,
        "seed_means_mbit_per_j": numeric,
        "mean_mbit_per_j": mean,
        "descriptive_t95_low_mbit_per_j": mean - T975_DF9 * standard_error,
        "descriptive_t95_high_mbit_per_j": mean + T975_DF9 * standard_error,
    }


def _condition(observed: Any, rule: str, passed: bool) -> dict[str, Any]:
    return {"observed": observed, "rule": rule, "passed": bool(passed)}


def main() -> int:
    args = _arguments()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {args.output}")
    if _sha256(dataset.SPEC) != dataset.SPEC_SHA256:
        raise RuntimeError("base v3 spec digest changed")
    if _sha256(dataset.AMENDMENT) != dataset.AMENDMENT_SHA256:
        raise RuntimeError("v3.1 amendment digest changed")
    development = json.loads(args.development.read_text(encoding="utf-8"))
    heldout = json.loads(args.heldout.read_text(encoding="utf-8"))
    development_verification = dataset_verify.verify(
        development, partition="development"
    )
    heldout_verification = dataset_verify.verify(heldout, partition="heldout")
    development_rows = _sorted_evaluated_rows(development)
    heldout_rows = _sorted_evaluated_rows(heldout)
    fit_rows = [
        row for row in development_rows if int(row["evaluation_seed"]) in FIT_SEEDS
    ]
    calibration_rows = [
        row
        for row in development_rows
        if int(row["evaluation_seed"]) in CALIBRATION_SEEDS
    ]
    if len(fit_rows) != 800 or len(calibration_rows) != 200:
        raise RuntimeError("development fit/calibration row counts changed")

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    networks: list[DQNNetwork] = []
    member_receipts: list[dict[str, Any]] = []
    for seed in ENSEMBLE_SEEDS:
        network, receipt = _fit_member(fit_rows, seed=seed)
        networks.append(network)
        member_receipts.append(receipt)

    calibration_member_scores = [
        _scores(network, calibration_rows) for network in networks
    ]
    calibration_scores = np.mean(calibration_member_scores, axis=0)
    threshold = float(
        np.quantile(calibration_scores, CALIBRATION_QUANTILE, method="linear")
    )
    heldout_member_scores = [_scores(network, heldout_rows) for network in networks]
    heldout_scores = np.mean(heldout_member_scores, axis=0)
    classification = _classification_metrics(heldout_rows, heldout_scores)
    member_metrics = [
        _classification_metrics(heldout_rows, scores)
        for scores in heldout_member_scores
    ]
    sinr_scores = np.asarray(
        [float(row["proposal_candidate_sinr"]) for row in heldout_rows],
        dtype=np.float64,
    )
    sinr_baseline = _classification_metrics(heldout_rows, sinr_scores)
    always = _accepted_metrics(
        heldout_rows, np.ones(len(heldout_rows), dtype=bool)
    )
    accepted_mask = heldout_scores >= threshold
    accepted = _accepted_metrics(heldout_rows, accepted_mask)
    per_seed = _per_seed_metrics(heldout_rows, heldout_scores, threshold)
    seed_interval = _seed_t_interval(per_seed)

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
    conditions = {
        "engineering": _condition(
            {
                "development": development_verification,
                "heldout": heldout_verification,
            },
            "both dataset verifiers pass",
            True,
        ),
        "auroc": _condition(
            classification["auroc"], ">= 0.65", classification["auroc"] >= 0.65
        ),
        "average_precision": _condition(
            classification["average_precision"],
            f">= max(0.30, prevalence+0.05, 1.25*prevalence) = {ap_required}",
            classification["average_precision"] >= ap_required,
        ),
        "coverage": _condition(
            {"accepted": accepted["accepted_rows"], "coverage": accepted["coverage"]},
            "accepted >= 100 and coverage in [0.10, 0.30]",
            int(accepted["accepted_rows"]) >= 100
            and 0.10 <= float(accepted["coverage"]) <= 0.30,
        ),
        "precision": _condition(
            accepted["joint_precision"],
            f">= max(0.30, 1.5*prevalence) = {precision_required}",
            accepted["joint_precision"] >= precision_required,
        ),
        "positive_selected_ee": _condition(
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
        "seed_joint_coverage": _condition(
            seeds_with_joint,
            ">= 8/10 seeds contain an accepted joint-positive row",
            seeds_with_joint >= 8,
        ),
        "service_safety": _condition(
            accepted["service_unsafe_rate"],
            f"<= max(1%, always unsafe+0.5pp) = {unsafe_limit}",
            accepted["service_unsafe_rate"] <= unsafe_limit,
        ),
        "per_seed_selection": _condition(
            seeds_meeting_selection,
            ">= 8/10 seeds each precision>=0.30, recall>=0.20, coverage 0.05..0.50",
            seeds_meeting_selection >= 8,
        ),
    }
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
    payload = {
        "schema": "mcrl-catfish-r3-heldout-state-learnability-gate-v3.1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "decision": (
            "PASS_STATE_SUFFICIENCY_ONLY" if passed else "FAIL_BLOCK_R3_REWARD_TRAINING"
        ),
        "threshold_pass": passed,
        "claim_boundary": (
            "discarded supervised state-sufficiency probe only; not a runtime "
            "coordinator, TD/RL result, composition result, or long-horizon result"
        ),
        "spec_path": str(dataset.SPEC),
        "spec_sha256": dataset.SPEC_SHA256,
        "amendment_path": str(dataset.AMENDMENT),
        "amendment_sha256": dataset.AMENDMENT_SHA256,
        "analysis_path": str(Path(__file__).resolve()),
        "analysis_sha256": _sha256(Path(__file__).resolve()),
        "development_path": str(args.development),
        "development_sha256": _sha256(args.development),
        "heldout_path": str(args.heldout),
        "heldout_sha256": _sha256(args.heldout),
        "development_verification": development_verification,
        "heldout_verification": heldout_verification,
        "model_input_contract": (
            "only focal_encoded_state enters each network; proposal_action indexes "
            "its 28-output row; Q1 and outcome fields never enter scoring"
        ),
        "model_config": {
            "architecture": [dataset.STATE_DIM, *HIDDEN_LAYERS, 28],
            "activation": "tanh",
            "fit_seeds": list(FIT_SEEDS),
            "calibration_seeds": list(CALIBRATION_SEEDS),
            "heldout_seeds": list(dataset.HELDOUT_SEEDS),
            "ensemble_seeds": list(ENSEMBLE_SEEDS),
            "epochs": EPOCHS,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "positive_class_weight": "fit_negative_count / fit_positive_count",
            "threshold_rule": "linear 80th percentile of calibration scores",
            "threshold": threshold,
        },
        "member_receipts": member_receipts,
        "member_heldout_metrics": member_metrics,
        "calibration_metrics": _classification_metrics(
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
