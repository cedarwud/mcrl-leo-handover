#!/usr/bin/env python3
"""Leave-one-anchor-out diagnosis for the V0.7 motion-scoped C2 source.

This is a development-only falsification instrument.  It reuses the already
opened six-anchor native-28 source for each Q1/Q3 lineage, trains the same
100-update rapid Q2 on five anchors, and scores the omitted anchor.  It opens
no new simulator world, DESIGN-EVAL split, or TEST split and writes no
deployable checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
from typing import Any, Iterable, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch  # noqa: E402
from mcrl.algorithms.ee_axis_v07_c2_fast_q2 import (  # noqa: E402
    FAST_Q2_ACTION_DIM,
    FAST_Q2_KAPPA_BITS,
    FreshQ2,
)
from mcrl.runtime.ee_axis_v07_c2_state import (  # noqa: E402
    V07_C2_Q2_STATE_DIM,
)


LINEAGES = ("q13-a", "q13-b", "q13-c")
TRAIN_SEEDS = {
    "q13-a": 2026104401,
    "q13-b": 2026104402,
    "q13-c": 2026104403,
}
DEFAULT_SOURCES = {
    lineage: REPO
    / "artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1"
    / f"p0-motion-native28-sixanchor-{lineage}-r11.json"
    for lineage in LINEAGES
}
DEFAULT_OUTPUT = (
    REPO
    / "artifacts/multi-catfish-v07-c2-fast-iteration-20260902-r1"
    / "p0-motion-native28-sixanchor-loao-r14.json"
)
UPDATES = 100


class MotionLoaoError(RuntimeError):
    """The development-only leave-one-anchor-out input is not comparable."""


def _canonical_sha256(payload: object) -> str:
    raw = json.dumps(
        payload,
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


def _calibration_slope(prediction: np.ndarray, target: np.ndarray) -> float | None:
    centered = prediction - np.mean(prediction)
    denominator = float(np.dot(centered, centered))
    if denominator == 0.0:
        return None
    centered_target = target - np.mean(target)
    return float(np.dot(centered, centered_target) / denominator)


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


def _action_only_fit(
    references: np.ndarray,
    candidates: np.ndarray,
    targets: np.ndarray,
) -> np.ndarray:
    design = np.zeros((targets.shape[0] + 1, FAST_Q2_ACTION_DIM), dtype=np.float64)
    rows = np.arange(targets.shape[0])
    design[rows, candidates] += 1.0
    design[rows, references] -= 1.0
    design[-1, :] = 1.0
    response = np.concatenate((targets, np.asarray([0.0], dtype=np.float64)))
    surface, *_ = np.linalg.lstsq(design, response, rcond=None)
    return surface


def _predict_action_only(
    surface: np.ndarray,
    references: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray:
    return surface[candidates] - surface[references]


def _quantiles(values: Iterable[float]) -> dict[str, float]:
    array = np.sort(np.asarray(tuple(values), dtype=np.float64))
    if array.size == 0:
        raise MotionLoaoError("cannot summarize an empty metric")
    return {
        "minimum": float(array[0]),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.quantile(array, 0.5)),
        "q75": float(np.quantile(array, 0.75)),
        "maximum": float(array[-1]),
        "mean": float(np.mean(array)),
    }


def _decode_state(raw: object) -> np.ndarray:
    if not isinstance(raw, list) or len(raw) != V07_C2_Q2_STATE_DIM:
        raise MotionLoaoError("anchor state is not the V0.7 228-D hexadecimal state")
    try:
        state = np.asarray([float.fromhex(value) for value in raw], dtype=np.float32)
    except (TypeError, ValueError, OverflowError) as error:
        raise MotionLoaoError("anchor state contains malformed hexadecimal values") from error
    if not np.all(np.isfinite(state)):
        raise MotionLoaoError("anchor state is non-finite")
    return state


def _read_source(path: Path, *, lineage: str) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise MotionLoaoError(f"cannot read {path}") from error
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "COMPLETE"
        or payload.get("lineage") != lineage
        or payload.get("training") is not False
        or payload.get("heldout_evaluation") is not False
        or payload.get("action_panel_mode") != "native28"
    ):
        raise MotionLoaoError(f"source for {lineage} is incomplete or not native28")
    anchors = payload.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != 6:
        raise MotionLoaoError(f"source for {lineage} must contain exactly six anchors")
    return payload


def _anchor_batch(anchor: Mapping[str, object]) -> EEAxisPairBatch:
    state = _decode_state(anchor.get("q2_state_float32_hex"))
    mask = np.asarray(anchor.get("action_mask"))
    reference = anchor.get("reference_action")
    rows = anchor.get("rows")
    if (
        mask.shape != (FAST_Q2_ACTION_DIM,)
        or mask.dtype != np.bool_
        or type(reference) is not int
        or not bool(mask[reference])
        or not isinstance(rows, list)
    ):
        raise MotionLoaoError("anchor mask/reference/rows are malformed")
    candidates: list[int] = []
    targets: list[float] = []
    for row in rows:
        if not isinstance(row, dict) or type(row.get("opening_action")) is not int:
            raise MotionLoaoError("source row is malformed")
        candidate = int(row["opening_action"])
        if candidate == reference:
            if float(row.get("p0_surplus_bits")) != 0.0:
                raise MotionLoaoError("candidate-equals-reference target is not exact zero")
            continue
        if not 0 <= candidate < FAST_Q2_ACTION_DIM or not bool(mask[candidate]):
            raise MotionLoaoError("source contains an illegal candidate")
        try:
            target = float(row["p0_surplus_bits"])
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise MotionLoaoError("source target is malformed") from error
        if not np.isfinite(target):
            raise MotionLoaoError("source target is non-finite")
        candidates.append(candidate)
        targets.append(target)
    expected = int(np.count_nonzero(mask)) - 1
    if len(candidates) != expected or len(set(candidates)) != expected:
        raise MotionLoaoError("source does not cover every non-reference legal action once")
    batch = EEAxisPairBatch(
        states=np.repeat(state[None, :], len(candidates), axis=0),
        reference_actions=np.full(len(candidates), reference, dtype=np.int64),
        candidate_actions=np.asarray(candidates, dtype=np.int64),
        target_surplus_bits=np.asarray(targets, dtype=np.float64),
        action_masks=np.repeat(mask[None, :], len(candidates), axis=0),
    )
    batch.validate(state_dim=V07_C2_Q2_STATE_DIM, action_dim=FAST_Q2_ACTION_DIM)
    return batch


def _concatenate(batches: list[EEAxisPairBatch]) -> EEAxisPairBatch:
    return EEAxisPairBatch(
        states=np.concatenate([np.asarray(batch.states) for batch in batches]),
        reference_actions=np.concatenate(
            [np.asarray(batch.reference_actions) for batch in batches]
        ),
        candidate_actions=np.concatenate(
            [np.asarray(batch.candidate_actions) for batch in batches]
        ),
        target_surplus_bits=np.concatenate(
            [np.asarray(batch.target_surplus_bits) for batch in batches]
        ),
        action_masks=np.concatenate(
            [np.asarray(batch.action_masks) for batch in batches]
        ),
    )


def diagnose(sources: Mapping[str, tuple[Path, Mapping[str, object]]]) -> dict[str, Any]:
    by_lineage: dict[str, Any] = {}
    source_receipts: dict[str, Any] = {}
    for lineage in LINEAGES:
        path, source = sources[lineage]
        anchors_raw = source["anchors"]
        assert isinstance(anchors_raw, list)
        anchor_batches = [_anchor_batch(anchor) for anchor in anchors_raw]
        model_predictions: list[np.ndarray] = []
        action_predictions: list[np.ndarray] = []
        targets_all: list[np.ndarray] = []
        folds: list[dict[str, Any]] = []
        for fold, validation_batch in enumerate(anchor_batches):
            training_batch = _concatenate(
                [batch for index, batch in enumerate(anchor_batches) if index != fold]
            )
            trainer = FreshQ2(train_seed=TRAIN_SEEDS[lineage])
            training = trainer.fit(training_batch, updates=UPDATES)
            states = np.asarray(validation_batch.states, dtype=np.float32)
            masks = np.asarray(validation_batch.action_masks, dtype=np.bool_)
            references = np.asarray(validation_batch.reference_actions, dtype=np.int64)
            candidates = np.asarray(validation_batch.candidate_actions, dtype=np.int64)
            targets = (
                np.asarray(validation_batch.target_surplus_bits, dtype=np.float64)
                / FAST_Q2_KAPPA_BITS
            )
            surface = np.asarray(trainer.q2_values(states, masks), dtype=np.float64)
            model = surface[np.arange(states.shape[0]), candidates] - surface[
                np.arange(states.shape[0]), references
            ]
            train_references = np.asarray(training_batch.reference_actions, dtype=np.int64)
            train_candidates = np.asarray(training_batch.candidate_actions, dtype=np.int64)
            train_targets = (
                np.asarray(training_batch.target_surplus_bits, dtype=np.float64)
                / FAST_Q2_KAPPA_BITS
            )
            action_surface = _action_only_fit(
                train_references, train_candidates, train_targets
            )
            action = _predict_action_only(action_surface, references, candidates)
            model_predictions.append(model)
            action_predictions.append(action)
            targets_all.append(targets)
            anchor = anchors_raw[fold]
            folds.append(
                {
                    "fold": fold,
                    "source_seed": anchor["source_seed"],
                    "window": anchor["window"],
                    "target_step": anchor["target_step"],
                    "focal_user": anchor["focal_user"],
                    "rows": int(targets.size),
                    "model": _metrics(model, targets),
                    "action_only": _metrics(action, targets),
                    "zero": _metrics(np.zeros_like(targets), targets),
                    "train_initial_loss": training["initial_loss"],
                    "train_final_loss": training["final_loss"],
                }
            )
        model_all = np.concatenate(model_predictions)
        action_all = np.concatenate(action_predictions)
        target_all = np.concatenate(targets_all)
        model_metrics = _metrics(model_all, target_all)
        action_metrics = _metrics(action_all, target_all)
        zero_metrics = _metrics(np.zeros_like(target_all), target_all)
        model_mse = float(model_metrics["mse"])
        action_mse = float(action_metrics["mse"])
        zero_mse = float(zero_metrics["mse"])
        strongest_name, strongest_mse = min(
            (("action_only", action_mse), ("zero", zero_mse)),
            key=lambda item: (item[1], item[0]),
        )
        by_lineage[lineage] = {
            "model": model_metrics,
            "action_only": action_metrics,
            "zero": zero_metrics,
            "strongest_null": strongest_name,
            "skill_vs_action_only": 1.0 - model_mse / action_mse,
            "skill_vs_zero": 1.0 - model_mse / zero_mse,
            "skill_vs_strongest_null": 1.0 - model_mse / strongest_mse,
            "folds_model_better_than_action_only": sum(
                float(fold["model"]["mse"]) < float(fold["action_only"]["mse"])
                for fold in folds
            ),
            "folds_model_better_than_zero": sum(
                float(fold["model"]["mse"]) < float(fold["zero"]["mse"])
                for fold in folds
            ),
            "folds": folds,
        }
        source_receipts[lineage] = {
            "path": str(path.resolve()),
            "file_sha256": _file_sha256(path),
            "anchors": len(anchor_batches),
            "nonreference_rows": int(target_all.size),
        }
    positive_action = sum(
        float(result["skill_vs_action_only"]) > 0.0
        for result in by_lineage.values()
    )
    positive_strongest = sum(
        float(result["skill_vs_strongest_null"]) > 0.0
        for result in by_lineage.values()
    )
    report: dict[str, Any] = {
        "schema": "multi-catfish-mcrl-v07-c2-motion-loao-diagnostic-v1",
        "status": "DEVELOPMENT_DIAGNOSTIC_ONLY_NOT_A_GATE",
        "claim_ceiling": "EXISTING_SOURCE_LEARNABILITY_FALSIFICATION_ONLY",
        "method": {
            "split": "leave_one_of_six_motion_selected_anchors_out",
            "folds_per_lineage": 6,
            "updates_per_fold": UPDATES,
            "model": "v07_fast_masked_meanmax_centered_q2",
            "nulls": ["train_fold_action_only_sum_zero", "zero"],
            "target_unit": "p0_focal_next_bits_over_kappa",
        },
        "sources": source_receipts,
        "by_lineage": by_lineage,
        "summary": {
            "positive_skill_vs_action_only_lineages": positive_action,
            "positive_skill_vs_strongest_null_lineages": positive_strongest,
            "median_skill_vs_action_only": median(
                float(result["skill_vs_action_only"])
                for result in by_lineage.values()
            ),
            "median_skill_vs_strongest_null": median(
                float(result["skill_vs_strongest_null"])
                for result in by_lineage.values()
            ),
            "lineage_skill_vs_action_only": {
                lineage: float(by_lineage[lineage]["skill_vs_action_only"])
                for lineage in LINEAGES
            },
            "lineage_skill_vs_strongest_null": {
                lineage: float(by_lineage[lineage]["skill_vs_strongest_null"])
                for lineage in LINEAGES
            },
        },
        "boundaries": {
            "new_simulator_worlds": False,
            "heldout_test_opened": False,
            "deployable_checkpoint_written": False,
            "policy_or_hyperparameter_selection": False,
        },
    }
    report["diagnostic_sha256"] = _canonical_sha256(report)
    return report


def _sources(values: list[str] | None) -> dict[str, tuple[Path, Mapping[str, object]]]:
    paths = dict(DEFAULT_SOURCES)
    if values:
        paths = {}
        for item in values:
            try:
                lineage, raw_path = item.split("=", 1)
            except ValueError as error:
                raise MotionLoaoError("--source must be LINEAGE=PATH") from error
            if lineage not in LINEAGES or lineage in paths:
                raise MotionLoaoError("--source lineages must be unique q13-a/b/c")
            paths[lineage] = Path(raw_path)
    if set(paths) != set(LINEAGES):
        raise MotionLoaoError("exactly one source is required for every lineage")
    return {
        lineage: (path, _read_source(path, lineage=lineage))
        for lineage, path in paths.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = diagnose(_sources(args.source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "MOTION_LOAO_COMPLETE",
                "output": str(args.output),
                "summary": report["summary"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
