#!/usr/bin/env python3
"""Leave-one-anchor-out learnability diagnosis for the sealed V0.6 Q2 target.

The run is post-outcome and diagnostic only.  It reuses only the sealed 12x28
TRAIN source and target-free sidecar, never opens DESIGN-EVAL or TEST worlds,
and never writes a deployable checkpoint.  Each fold trains the frozen V0.6
network for exactly 100 updates on 11 anchors and scores the omitted anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import numpy as np
import torch
import torch.optim as optim

from mcrl.algorithms.ee_axis_action_shared_meanmax import MaskedMeanMaxQNetwork
from mcrl.algorithms.ee_axis_v06_c2_k1 import (
    V06_C2_K1_ADAM,
    V06_C2_K1_BETA,
    V06_C2_K1_KAPPA_BITS,
    V06_C2_K1_LINEAGES,
    V06_C2_K1_SEED_BY_LINEAGE,
    frozen_q2_config,
)
from mcrl.runtime.ee_axis_v06_c2_k1_learner import build_lineage_batch


DEFAULT_SOURCE = Path(
    "artifacts/multi-catfish-v06-c2-k1-t1-source-gate-20260902-r1/"
    "merged/source.json"
)
DEFAULT_SIDECAR = Path(
    "artifacts/multi-catfish-v06-c2-k1-bounded-screen-20260902-r1/"
    "state-sidecar/state-sidecar.json"
)
ACTIONS = 28
ANCHORS = 12
UPDATES = 100


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quantiles(values: Iterable[float]) -> dict[str, float]:
    array = np.sort(np.asarray(list(values), dtype=np.float64))
    if array.size == 0:
        raise ValueError("cannot summarize an empty collection")
    return {
        "min": float(array[0]),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.quantile(array, 0.5)),
        "q75": float(np.quantile(array, 0.75)),
        "max": float(array[-1]),
        "mean": float(np.mean(array)),
    }


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.shape[0], dtype=np.float64)
    start = 0
    while start < order.size:
        stop = start + 1
        while stop < order.size and values[order[stop]] == values[order[start]]:
            stop += 1
        ranks[order[start:stop]] = 0.5 * ((start + 1) + stop)
        start = stop
    return ranks


def _spearman(left: np.ndarray, right: np.ndarray) -> float | None:
    left_rank = _rankdata(np.asarray(left, dtype=np.float64))
    right_rank = _rankdata(np.asarray(right, dtype=np.float64))
    if np.std(left_rank) == 0.0 or np.std(right_rank) == 0.0:
        return None
    return float(np.corrcoef(left_rank, right_rank)[0, 1])


def _action_only_fit(
    references: np.ndarray,
    candidates: np.ndarray,
    targets: np.ndarray,
) -> np.ndarray:
    design = np.zeros((targets.shape[0] + 1, ACTIONS), dtype=np.float64)
    rows = np.arange(targets.shape[0])
    design[rows, candidates] += 1.0
    design[rows, references] -= 1.0
    # One exact sum-to-zero gauge row makes the least-squares solution unique
    # without altering any action difference.
    design[-1, :] = 1.0
    response = np.concatenate((targets, np.asarray([0.0], dtype=np.float64)))
    solution, *_ = np.linalg.lstsq(design, response, rcond=None)
    return solution


def _predict_action_only(
    surface: np.ndarray,
    references: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray:
    return surface[candidates] - surface[references]


def _calibration_slope(prediction: np.ndarray, target: np.ndarray) -> float | None:
    centered_prediction = prediction - np.mean(prediction)
    denominator = float(np.dot(centered_prediction, centered_prediction))
    if denominator == 0.0:
        return None
    centered_target = target - np.mean(target)
    return float(np.dot(centered_prediction, centered_target) / denominator)


def _metrics(prediction: np.ndarray, target: np.ndarray) -> dict[str, float | None]:
    error = prediction - target
    nonzero = np.abs(target) > 1e-12
    return {
        "mse": float(np.mean(error * error)),
        "mae": float(np.mean(np.abs(error))),
        "spearman": _spearman(prediction, target),
        "calibration_slope": _calibration_slope(prediction, target),
        "sign_accuracy_nonzero": (
            float(np.mean(np.sign(prediction[nonzero]) == np.sign(target[nonzero])))
            if bool(np.any(nonzero))
            else None
        ),
    }


def _train_fold(
    *,
    states: np.ndarray,
    masks: np.ndarray,
    references: np.ndarray,
    candidates: np.ndarray,
    targets: np.ndarray,
    train_rows: np.ndarray,
    validation_rows: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, dict[str, float]]:
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)
    torch.manual_seed(seed)
    network = MaskedMeanMaxQNetwork(frozen_q2_config()).to("cpu")
    optimizer = optim.Adam(
        network.parameters(),
        lr=V06_C2_K1_ADAM["lr"],
        betas=V06_C2_K1_ADAM["betas"],
        eps=V06_C2_K1_ADAM["eps"],
        weight_decay=V06_C2_K1_ADAM["weight_decay"],
        amsgrad=V06_C2_K1_ADAM["amsgrad"],
    )
    train_states = torch.tensor(states[train_rows], dtype=torch.float32)
    train_masks = torch.tensor(masks[train_rows], dtype=torch.bool)
    train_reference = torch.tensor(references[train_rows], dtype=torch.int64)
    train_candidate = torch.tensor(candidates[train_rows], dtype=torch.int64)
    train_target = torch.tensor(targets[train_rows], dtype=torch.float32)
    first_loss = 0.0
    final_loss = 0.0
    for update in range(UPDATES):
        surface = network(train_states, train_masks)
        q_reference = surface.gather(1, train_reference[:, None]).squeeze(1)
        q_candidate = surface.gather(1, train_candidate[:, None]).squeeze(1)
        residual = q_candidate - q_reference - train_target
        pair_mse = torch.mean(residual.square())
        gauge_mse = torch.mean(q_reference.square())
        loss = pair_mse + V06_C2_K1_BETA * gauge_mse
        if update == 0:
            first_loss = float(loss.detach())
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        final_loss = float(loss.detach())
    with torch.no_grad():
        validation_surface = network(
            torch.tensor(states[validation_rows], dtype=torch.float32),
            torch.tensor(masks[validation_rows], dtype=torch.bool),
        ).cpu().numpy()
    validation_prediction = (
        validation_surface[np.arange(validation_rows.size), candidates[validation_rows]]
        - validation_surface[np.arange(validation_rows.size), references[validation_rows]]
    )
    return validation_prediction.astype(np.float64), {
        "train_loss_first": first_loss,
        "train_loss_final": final_loss,
    }


def diagnose(
    source: dict[str, Any],
    sidecar: dict[str, Any],
    *,
    source_file_sha256: str,
    sidecar_file_sha256: str,
) -> dict[str, Any]:
    by_lineage: dict[str, Any] = {}
    for lineage in V06_C2_K1_LINEAGES:
        batch, receipt = build_lineage_batch(
            source=source,
            sidecar=sidecar,
            lineage=lineage,
        )
        states = np.asarray(batch.states, dtype=np.float32)
        masks = np.asarray(batch.action_masks, dtype=np.bool_)
        references = np.asarray(batch.reference_actions, dtype=np.int64)
        candidates = np.asarray(batch.candidate_actions, dtype=np.int64)
        targets = (
            np.asarray(batch.target_surplus_bits, dtype=np.float64)
            / V06_C2_K1_KAPPA_BITS
        )
        model_prediction = np.empty_like(targets)
        action_prediction = np.empty_like(targets)
        fold_metrics: list[dict[str, Any]] = []
        for fold in range(ANCHORS):
            start = fold * ACTIONS
            stop = start + ACTIONS
            validation_rows = np.arange(start, stop)
            train_rows = np.concatenate((np.arange(0, start), np.arange(stop, targets.size)))
            prediction, training = _train_fold(
                states=states,
                masks=masks,
                references=references,
                candidates=candidates,
                targets=targets,
                train_rows=train_rows,
                validation_rows=validation_rows,
                seed=int(V06_C2_K1_SEED_BY_LINEAGE[lineage]),
            )
            action_surface = _action_only_fit(
                references[train_rows], candidates[train_rows], targets[train_rows]
            )
            action_fold = _predict_action_only(
                action_surface,
                references[validation_rows],
                candidates[validation_rows],
            )
            model_prediction[validation_rows] = prediction
            action_prediction[validation_rows] = action_fold
            fold_metrics.append(
                {
                    "fold": fold,
                    "anchor_key": sidecar["anchors"][fold]["anchor_key"],
                    "model": _metrics(prediction, targets[validation_rows]),
                    "action_only": _metrics(action_fold, targets[validation_rows]),
                    "zero": _metrics(np.zeros_like(prediction), targets[validation_rows]),
                    **training,
                }
            )
        model = _metrics(model_prediction, targets)
        action_only = _metrics(action_prediction, targets)
        zero = _metrics(np.zeros_like(targets), targets)
        model_mse = float(model["mse"])
        action_mse = float(action_only["mse"])
        zero_mse = float(zero["mse"])
        by_lineage[lineage] = {
            "batch_receipt_sha256": receipt["batch_receipt_sha256"],
            "model": model,
            "action_only": action_only,
            "zero": zero,
            "skill_vs_action_only": 1.0 - model_mse / action_mse,
            "skill_vs_zero": 1.0 - model_mse / zero_mse,
            "folds_model_better_than_action_only": sum(
                float(fold["model"]["mse"]) < float(fold["action_only"]["mse"])
                for fold in fold_metrics
            ),
            "folds_model_better_than_zero": sum(
                float(fold["model"]["mse"]) < float(fold["zero"]["mse"])
                for fold in fold_metrics
            ),
            "fold_metrics": fold_metrics,
        }
    positive_action_skill = sum(
        float(result["skill_vs_action_only"]) > 0.0 for result in by_lineage.values()
    )
    positive_zero_skill = sum(
        float(result["skill_vs_zero"]) > 0.0 for result in by_lineage.values()
    )
    report: dict[str, Any] = {
        "schema": "multi-catfish-mcrl-v06-c2-k1-loowo-diagnostic-v1",
        "status": "POSTOUTCOME_DIAGNOSTIC_ONLY_NOT_A_GATE",
        "method": {
            "split": "leave_one_of_12_anchors_out",
            "updates_per_fold": UPDATES,
            "folds_per_lineage": ANCHORS,
            "model": "frozen_v06_masked_meanmax",
            "action_only_null": "train_fold_pairwise_least_squares_with_sum_zero_gauge",
            "target_unit": "z2_k1_bits_over_kappa",
        },
        "source": {
            "source_file_sha256": source_file_sha256,
            "sidecar_file_sha256": sidecar_file_sha256,
            "test_split_opened": False,
            "design_eval_opened_by_this_script": False,
        },
        "by_lineage": by_lineage,
        "summary": {
            "positive_skill_vs_action_only_lineages": positive_action_skill,
            "positive_skill_vs_zero_lineages": positive_zero_skill,
            "median_skill_vs_action_only": median(
                float(result["skill_vs_action_only"])
                for result in by_lineage.values()
            ),
            "median_skill_vs_zero": median(
                float(result["skill_vs_zero"])
                for result in by_lineage.values()
            ),
        },
        "interpretation_boundary": {
            "training_is_diagnostic_only": True,
            "deployable_checkpoint_written": False,
            "new_worlds": False,
            "policy_selection": False,
            "replacement_gate": False,
        },
    }
    report["diagnostic_sha256"] = _canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--sidecar", type=Path, default=DEFAULT_SIDECAR)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    sidecar = json.loads(args.sidecar.read_text(encoding="utf-8"))
    report = diagnose(
        source,
        sidecar,
        source_file_sha256=_file_sha256(args.source),
        sidecar_file_sha256=_file_sha256(args.sidecar),
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
