#!/usr/bin/env python3
"""Run the bounded post-gate V0.14 Q3 support-detectability probe.

This is a source-only diagnostic.  It reuses the already opened V0.14
TRAIN/VALIDATION source panel and never advances the simulator, opens TEST,
or claims deployed efficacy.  Arm A keeps the deployable 287-dimensional Q3
state.  Arm B appends the route reference's ten local features and is an
explicitly non-deployable observability diagnostic.

Both arms replace uniform surface MSE with a class-balanced support
classifier plus a positive-amplitude regressor.  The classifier's balanced
posterior is corrected back to the natural TRAIN prior before forming the
expected Q3 surplus.  Unsupported amplitude is the frozen TRAIN conditional
mean; the route reference is gauged to exactly zero.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for _path in (REPO, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from mcrl.algorithms.ee_axis_v014_head import (  # noqa: E402
    EEAxisV014HeadConfig,
    EEAxisV014PairwiseLearner,
    V014ActionSetQNetwork,
)
from mcrl.errors import MCRLContractError  # noqa: E402
from mcrl.runtime.ee_axis_ops3 import OPS3_KAPPA_BITS  # noqa: E402


GATE_RUNNER_PATH = HERE / "run_v014_learner_gate.py"
_GATE_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v014_learner_gate_for_support_probe", GATE_RUNNER_PATH
)
if _GATE_SPEC is None or _GATE_SPEC.loader is None:
    raise RuntimeError(f"cannot load V0.14 gate runner: {GATE_RUNNER_PATH}")
_GATE_MODULE = importlib.util.module_from_spec(_GATE_SPEC)
sys.modules[_GATE_SPEC.name] = _GATE_MODULE
_GATE_SPEC.loader.exec_module(_GATE_MODULE)

load_source_shards = _GATE_MODULE.load_source_shards


RUNNER_SCHEMA = "multi-catfish-mcrl-v014-q3-support-probe-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-v014-q3-support-probe-result-v1"
CLAIM_CEILING = "SOURCE_ONLY_POST_GATE_DIAGNOSTIC_NO_EFFICACY_CLAIM"
ACTION_DIM = 28
LOCAL_FEATURE_DIM = 10
DEPLOYABLE_GLOBAL_DIM = 7
DIAGNOSTIC_GLOBAL_DIM = 17
DEFAULT_UPDATES = 3000
DEFAULT_BATCH_SIZE = 512
DEFAULT_HIDDEN_LAYERS = (100, 50, 50)
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_TRAIN_WORLDS = (2026108001, 2026108002, 2026108003, 2026108004)
DEFAULT_VALIDATION_WORLDS = (2026108005, 2026108006, 2026108007)
DEFAULT_INITIALIZATIONS = (2026108101, 2026108102, 2026108103)
DEFAULT_LINEAGES = (2026092101, 2026092102, 2026092103)
COMMON_Q2_RUNG = 3000


class V014Q3SupportProbeError(MCRLContractError):
    """The bounded source-only support probe violated its contract."""


def _canonical_bytes(payload: object) -> bytes:
    try:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise V014Q3SupportProbeError("payload is not finite canonical JSON") from error


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise V014Q3SupportProbeError(f"expected a regular file: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def append_reference_context(
    states: np.ndarray, reference_actions: np.ndarray
) -> np.ndarray:
    """Append the reference action's ten local features for diagnostic arm B."""

    values = np.asarray(states, dtype=np.float32)
    references = np.asarray(reference_actions)
    expected = LOCAL_FEATURE_DIM * ACTION_DIM + DEPLOYABLE_GLOBAL_DIM
    if values.ndim != 2 or values.shape[1] != expected:
        raise V014Q3SupportProbeError(
            f"Q3 states must have shape (rows,{expected})"
        )
    if (
        references.shape != (values.shape[0],)
        or not np.issubdtype(references.dtype, np.integer)
        or np.any(references < 0)
        or np.any(references >= ACTION_DIM)
    ):
        raise V014Q3SupportProbeError("reference actions are malformed")
    local = values[:, : LOCAL_FEATURE_DIM * ACTION_DIM].reshape(
        values.shape[0], LOCAL_FEATURE_DIM, ACTION_DIM
    )
    reference_local = local[np.arange(values.shape[0]), :, references]
    return np.ascontiguousarray(
        np.concatenate((values, reference_local), axis=1), dtype=np.float32
    )


def natural_probability_from_balanced_logit(
    balanced_logit: torch.Tensor, *, positive_prior: float
) -> torch.Tensor:
    """Undo equal-class BCE's prior shift without tuning a threshold."""

    prior = float(positive_prior)
    if not math.isfinite(prior) or not 0.0 < prior < 1.0:
        raise V014Q3SupportProbeError("positive_prior must lie strictly in (0,1)")
    offset = math.log(prior) - math.log1p(-prior)
    return torch.sigmoid(balanced_logit + offset)


def binary_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    """Return tie-aware ROC AUC using the Mann-Whitney rank identity."""

    truth = np.asarray(labels, dtype=np.bool_).reshape(-1)
    value = np.asarray(scores, dtype=np.float64).reshape(-1)
    if truth.shape != value.shape or not np.all(np.isfinite(value)):
        raise V014Q3SupportProbeError("AUC labels/scores are malformed")
    positives = int(np.count_nonzero(truth))
    negatives = int(truth.size - positives)
    if positives == 0 or negatives == 0:
        raise V014Q3SupportProbeError("AUC requires both classes")
    order = np.argsort(value, kind="mergesort")
    sorted_values = value[order]
    ranks = np.empty(value.size, dtype=np.float64)
    start = 0
    while start < value.size:
        end = start + 1
        while end < value.size and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = 0.5 * ((start + 1) + end)
        start = end
    rank_sum = float(np.sum(ranks[truth], dtype=np.float64))
    return (rank_sum - positives * (positives + 1) / 2.0) / (
        positives * negatives
    )


@dataclass(frozen=True)
class SupportProbeSpec:
    """Choices fixed before opening a probe model outcome."""

    updates: int = DEFAULT_UPDATES
    batch_size: int = DEFAULT_BATCH_SIZE
    hidden_layers: tuple[int, ...] = DEFAULT_HIDDEN_LAYERS
    learning_rate: float = DEFAULT_LEARNING_RATE
    kappa_bits: float = OPS3_KAPPA_BITS

    def verify(self) -> None:
        if self.updates < 1 or self.batch_size < 1:
            raise V014Q3SupportProbeError("updates and batch_size must be positive")
        if not self.hidden_layers or any(width < 1 for width in self.hidden_layers):
            raise V014Q3SupportProbeError("hidden layers must be positive")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0.0:
            raise V014Q3SupportProbeError("learning rate must be finite and positive")
        if float(self.kappa_bits).hex() != float(OPS3_KAPPA_BITS).hex():
            raise V014Q3SupportProbeError("probe must use the frozen OPS3 kappa")


class Q3SupportMixtureLearner:
    """Balanced support classifier plus supported positive-amplitude regressor."""

    def __init__(
        self,
        *,
        global_feature_dim: int,
        positive_prior: float,
        unsupported_mean: float,
        spec: SupportProbeSpec,
        seed: int,
    ) -> None:
        spec.verify()
        if global_feature_dim not in {DEPLOYABLE_GLOBAL_DIM, DIAGNOSTIC_GLOBAL_DIM}:
            raise V014Q3SupportProbeError("unsupported probe state width")
        if not math.isfinite(unsupported_mean) or unsupported_mean > 0.0:
            raise V014Q3SupportProbeError(
                "unsupported conditional mean must be finite and nonpositive"
            )
        if not 0.0 < positive_prior < 1.0:
            raise V014Q3SupportProbeError("probe needs both support classes")
        torch.manual_seed(int(seed))
        config = EEAxisV014HeadConfig(
            action_dim=ACTION_DIM,
            local_feature_dim=LOCAL_FEATURE_DIM,
            global_feature_dim=global_feature_dim,
            hidden_layers=tuple(spec.hidden_layers),
            activation="tanh",
            learning_rate=float(spec.learning_rate),
            kappa_bits=float(spec.kappa_bits),
            beta=0.0,
        )
        self.classifier = V014ActionSetQNetwork(config)
        self.positive_amplitude = V014ActionSetQNetwork(config)
        self.optimizer = optim.Adam(
            tuple(self.classifier.parameters())
            + tuple(self.positive_amplitude.parameters()),
            lr=float(spec.learning_rate),
        )
        self.config = config
        self.positive_prior = float(positive_prior)
        self.unsupported_mean = float(unsupported_mean)
        self.spec = spec

    def update(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        references: np.ndarray,
        targets_bits: np.ndarray,
        compatibility: np.ndarray,
    ) -> dict[str, float]:
        values = torch.as_tensor(np.asarray(states), dtype=torch.float32)
        legal = torch.as_tensor(np.asarray(masks), dtype=torch.bool)
        refs = torch.as_tensor(np.asarray(references), dtype=torch.int64)
        targets = torch.as_tensor(
            np.asarray(targets_bits, dtype=np.float32) / float(self.spec.kappa_bits),
            dtype=torch.float32,
        )
        compatible = torch.as_tensor(np.asarray(compatibility), dtype=torch.bool)
        comparisons = legal.clone()
        rows = torch.arange(values.shape[0])
        comparisons[rows, refs] = False
        target_delta = targets - targets[rows, refs][:, None]
        support = compatible & (target_delta > 0.0) & comparisons
        labels = support.to(torch.float32)
        logits = self.classifier(values, legal)
        raw_amplitude = self.positive_amplitude(values, legal)
        positive_weight = (1.0 - self.positive_prior) / self.positive_prior
        bce = F.binary_cross_entropy_with_logits(
            logits[comparisons],
            labels[comparisons],
            pos_weight=torch.tensor(positive_weight, dtype=torch.float32),
        )
        if bool(torch.any(support)):
            amplitude = F.softplus(raw_amplitude[support])
            amplitude_mse = torch.mean((amplitude - target_delta[support]).square())
        else:
            amplitude_mse = raw_amplitude.sum() * 0.0
        loss = bce + amplitude_mse
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        self.optimizer.step()
        if not bool(torch.isfinite(loss)):
            raise V014Q3SupportProbeError("probe loss became non-finite")
        return {
            "loss": float(loss.detach()),
            "balanced_bce": float(bce.detach()),
            "positive_amplitude_mse": float(amplitude_mse.detach()),
        }

    def predict(
        self,
        states: np.ndarray,
        masks: np.ndarray,
        references: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        values = torch.as_tensor(np.asarray(states), dtype=torch.float32)
        legal = torch.as_tensor(np.asarray(masks), dtype=torch.bool)
        refs = np.asarray(references, dtype=np.int64)
        self.classifier.eval()
        self.positive_amplitude.eval()
        with torch.no_grad():
            logits = self.classifier(values, legal)
            probability = natural_probability_from_balanced_logit(
                logits, positive_prior=self.positive_prior
            )
            positive = F.softplus(self.positive_amplitude(values, legal))
            expected = probability * positive + (1.0 - probability) * float(
                self.unsupported_mean
            )
        probability_np = probability.cpu().numpy()
        positive_np = positive.cpu().numpy()
        expected_np = expected.cpu().numpy()
        expected_np[np.arange(expected_np.shape[0]), refs] = 0.0
        return probability_np, positive_np, expected_np


def _comparison_arrays(
    *,
    masks: np.ndarray,
    references: np.ndarray,
    targets_bits: np.ndarray,
    compatibility: np.ndarray,
    kappa_bits: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    legal = np.asarray(masks, dtype=np.bool_)
    refs = np.asarray(references, dtype=np.int64)
    targets = np.asarray(targets_bits, dtype=np.float64) / float(kappa_bits)
    compatible = np.asarray(compatibility, dtype=np.bool_)
    comparisons = np.array(legal, copy=True)
    comparisons[np.arange(comparisons.shape[0]), refs] = False
    target_delta = targets - targets[np.arange(targets.shape[0]), refs][:, None]
    support = comparisons & compatible & (target_delta > 0.0)
    if not np.any(support) or not np.any(comparisons & ~support):
        raise V014Q3SupportProbeError("probe source lacks both support classes")
    return comparisons, support, target_delta


def _argmax(scores: np.ndarray, masks: np.ndarray) -> np.ndarray:
    return np.argmax(np.where(masks, scores, -np.inf), axis=1)


def joint_counts(
    *,
    q1: np.ndarray,
    q2: np.ndarray,
    q3_true: np.ndarray,
    q3_hat: np.ndarray,
    masks: np.ndarray,
    compatibility: np.ndarray,
) -> dict[str, int | float]:
    background_scores = np.asarray(q1, dtype=np.float64) + np.asarray(
        q2, dtype=np.float64
    )
    legal = np.asarray(masks, dtype=np.bool_)
    background = _argmax(background_scores, legal)
    teacher = _argmax(background_scores + np.asarray(q3_true), legal)
    student = _argmax(background_scores + np.asarray(q3_hat), legal)
    rows = np.arange(background.shape[0])
    changed = student != background
    teacher_changed = teacher != background
    supported = (
        np.asarray(compatibility, dtype=np.bool_)[rows, student]
        & (np.asarray(q3_true, dtype=np.float64)[rows, student] > 0.0)
    )
    changed_count = int(np.count_nonzero(changed))
    supported_count = int(np.count_nonzero(changed & supported))
    teacher_changed_count = int(np.count_nonzero(teacher_changed))
    recovered_count = int(np.count_nonzero(teacher_changed & (student == teacher)))
    return {
        "anchors": int(background.shape[0]),
        "changed": changed_count,
        "supported_changed": supported_count,
        "support_rate": (
            float(supported_count / changed_count) if changed_count else 0.0
        ),
        "teacher_changed": teacher_changed_count,
        "teacher_recovered": recovered_count,
        "teacher_recovery_rate": (
            float(recovered_count / teacher_changed_count)
            if teacher_changed_count
            else 0.0
        ),
    }


def adjudicate_probe(
    exact_rows: Sequence[Mapping[str, int | float]],
    learned_rows: Sequence[Mapping[str, int | float]],
) -> dict[str, object]:
    def pooled(rows: Sequence[Mapping[str, int | float]]) -> dict[str, object]:
        changed = sum(int(row["changed"]) for row in rows)
        supported = sum(int(row["supported_changed"]) for row in rows)
        exposed = sum(int(row["changed"]) > 0 for row in rows)
        return {
            "changed": changed,
            "supported_changed": supported,
            "support_rate": float(supported / changed) if changed else 0.0,
            "exposed_lineages": exposed,
        }

    exact = pooled(exact_rows)
    learned = pooled(learned_rows)
    passed = bool(
        float(exact["support_rate"]) >= 0.5
        and float(learned["support_rate"]) >= 0.5
        and int(exact["exposed_lineages"]) >= 2
        and int(learned["exposed_lineages"]) >= 2
    )
    return {
        "exact_o2": exact,
        "learned_q2": learned,
        "passed": passed,
        "decision": "GO_REBALANCED_Q3_GATE" if passed else "STOP_THREE_HEAD",
    }


def _load_q2(
    *, checkpoint_path: Path, initialization_seed: int
) -> EEAxisV014PairwiseLearner:
    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        inner = payload["q2"]
        config = EEAxisV014HeadConfig(**dict(inner["config"]))
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as error:
        raise V014Q3SupportProbeError("cannot load frozen Q2 checkpoint") from error
    if int(payload.get("initialization_seed", -1)) != initialization_seed:
        raise V014Q3SupportProbeError("Q2 checkpoint initialization drifted")
    if int(payload.get("update_rung", -1)) != COMMON_Q2_RUNG:
        raise V014Q3SupportProbeError("Q2 checkpoint is not rung 3000")
    learner = EEAxisV014PairwiseLearner(
        config, train_seed=initialization_seed, device="cpu"
    )
    if learner.load_checkpoint_state(inner) != COMMON_Q2_RUNG:
        raise V014Q3SupportProbeError("Q2 inner checkpoint rung drifted")
    return learner


def _train_arm(
    *,
    arm: str,
    train: Any,
    validation: Any,
    seed: int,
    spec: SupportProbeSpec,
) -> tuple[dict[str, object], np.ndarray, dict[str, np.ndarray]]:
    train_states = np.asarray(train.q3.states)
    validation_states = np.asarray(validation.q3.states)
    global_dim = DEPLOYABLE_GLOBAL_DIM
    if arm == "B_REFERENCE_CONTEXT_DIAGNOSTIC":
        train_states = append_reference_context(
            train_states, train.q3.reference_actions
        )
        validation_states = append_reference_context(
            validation_states, validation.q3.reference_actions
        )
        global_dim = DIAGNOSTIC_GLOBAL_DIM
    elif arm != "A_DEPLOYABLE_STATE":
        raise V014Q3SupportProbeError(f"unknown arm: {arm}")

    comparisons, support, targets = _comparison_arrays(
        masks=train.q3.masks,
        references=train.q3.reference_actions,
        targets_bits=train.q3.target_surfaces_bits,
        compatibility=train.q3_compatibility,
        kappa_bits=spec.kappa_bits,
    )
    positive_prior = float(np.mean(support[comparisons]))
    unsupported_mean = float(np.mean(targets[comparisons & ~support]))
    learner = Q3SupportMixtureLearner(
        global_feature_dim=global_dim,
        positive_prior=positive_prior,
        unsupported_mean=unsupported_mean,
        spec=spec,
        seed=seed + (0 if arm == "A_DEPLOYABLE_STATE" else 100_000),
    )
    final_loss: dict[str, float] = {}
    rows = int(train_states.shape[0])
    for update in range(1, spec.updates + 1):
        start = ((update - 1) * spec.batch_size) % rows
        indices = (start + np.arange(spec.batch_size, dtype=np.int64)) % rows
        final_loss = learner.update(
            train_states[indices],
            train.q3.masks[indices],
            train.q3.reference_actions[indices],
            train.q3.target_surfaces_bits[indices],
            train.q3_compatibility[indices],
        )

    probability, positive_hat, q3_hat = learner.predict(
        validation_states,
        validation.q3.masks,
        validation.q3.reference_actions,
    )
    val_comparisons, val_support, val_targets = _comparison_arrays(
        masks=validation.q3.masks,
        references=validation.q3.reference_actions,
        targets_bits=validation.q3.target_surfaces_bits,
        compatibility=validation.q3_compatibility,
        kappa_bits=spec.kappa_bits,
    )
    action_prior = np.full(ACTION_DIM, positive_prior, dtype=np.float64)
    for action in range(ACTION_DIM):
        action_rows = comparisons[:, action]
        if np.any(action_rows):
            action_prior[action] = float(np.mean(support[action_rows, action]))
    prior_surface = np.broadcast_to(action_prior, probability.shape)
    positive_error = positive_hat[val_support] - val_targets[val_support]
    report = {
        "arm": arm,
        "positive_prior": positive_prior,
        "unsupported_conditional_mean_kappa": unsupported_mean,
        "validation_support_auc": binary_auc(
            val_support[val_comparisons], probability[val_comparisons]
        ),
        "validation_action_prior_null_auc": binary_auc(
            val_support[val_comparisons], prior_surface[val_comparisons]
        ),
        "validation_positive_amplitude_mae_kappa": float(
            np.mean(np.abs(positive_error), dtype=np.float64)
        ),
        "validation_positive_amplitude_rmse_kappa": float(
            np.sqrt(np.mean(np.square(positive_error), dtype=np.float64))
        ),
        "final_train_loss": final_loss,
    }
    auc_payload = {
        "labels": np.asarray(val_support[val_comparisons], dtype=np.bool_),
        "probability": np.asarray(probability[val_comparisons], dtype=np.float64),
        "action_prior": np.asarray(prior_surface[val_comparisons], dtype=np.float64),
    }
    return report, q3_hat, auc_payload


def run(
    *,
    source_paths: Sequence[str | Path],
    checkpoint_paths: Mapping[int, str | Path],
    output_path: str | Path,
    spec: SupportProbeSpec | None = None,
) -> dict[str, object]:
    """Run both source-only arms and write one immutable JSON receipt."""

    probe_spec = spec or SupportProbeSpec()
    probe_spec.verify()
    destination = Path(output_path)
    if destination.exists() or destination.is_symlink():
        raise V014Q3SupportProbeError(f"refusing to overwrite {destination}")
    if set(checkpoint_paths) != set(DEFAULT_INITIALIZATIONS):
        raise V014Q3SupportProbeError("exactly three frozen Q2 checkpoints are required")

    per_lineage: list[dict[str, object]] = []
    a_exact: list[Mapping[str, int | float]] = []
    a_learned: list[Mapping[str, int | float]] = []
    pooled_auc: dict[str, dict[str, list[np.ndarray]]] = {
        arm: {"labels": [], "probability": [], "action_prior": []}
        for arm in ("A_DEPLOYABLE_STATE", "B_REFERENCE_CONTEXT_DIAGNOSTIC")
    }
    for seed, lineage in zip(
        DEFAULT_INITIALIZATIONS, DEFAULT_LINEAGES, strict=True
    ):
        loaded = load_source_shards(
            source_paths,
            train_world_seeds=DEFAULT_TRAIN_WORLDS,
            validation_world_seeds=DEFAULT_VALIDATION_WORLDS,
            kappa_bits=probe_spec.kappa_bits,
            lineage=lineage,
        )
        train = loaded.train
        validation = loaded.validation
        checkpoint = Path(checkpoint_paths[seed])
        q2 = _load_q2(checkpoint_path=checkpoint, initialization_seed=seed)
        q2_hat = q2.q_values(validation.q2.states, validation.q2.masks)
        exact_q2 = (
            np.asarray(validation.q2.target_surfaces_bits, dtype=np.float64)
            / float(probe_spec.kappa_bits)
        )
        q3_true = (
            np.asarray(validation.q3.target_surfaces_bits, dtype=np.float64)
            / float(probe_spec.kappa_bits)
        )
        arms: dict[str, object] = {}
        for arm in ("A_DEPLOYABLE_STATE", "B_REFERENCE_CONTEXT_DIAGNOSTIC"):
            report, q3_hat, auc_payload = _train_arm(
                arm=arm,
                train=train,
                validation=validation,
                seed=seed,
                spec=probe_spec,
            )
            exact_counts = joint_counts(
                q1=validation.q1_values,
                q2=exact_q2,
                q3_true=q3_true,
                q3_hat=q3_hat,
                masks=validation.q3.masks,
                compatibility=validation.q3_compatibility,
            )
            learned_counts = joint_counts(
                q1=validation.q1_values,
                q2=q2_hat,
                q3_true=q3_true,
                q3_hat=q3_hat,
                masks=validation.q3.masks,
                compatibility=validation.q3_compatibility,
            )
            report["exact_o2_joint"] = exact_counts
            report["learned_q2_joint"] = learned_counts
            arms[arm] = report
            for field, values in auc_payload.items():
                pooled_auc[arm][field].append(values)
            if arm == "A_DEPLOYABLE_STATE":
                a_exact.append(exact_counts)
                a_learned.append(learned_counts)
        per_lineage.append(
            {
                "initialization_seed": seed,
                "lineage": lineage,
                "source_sha256": loaded.source_sha256,
                "q2_checkpoint": str(checkpoint),
                "q2_checkpoint_sha256": file_sha256(checkpoint),
                "arms": arms,
            }
        )

    decision = adjudicate_probe(a_exact, a_learned)
    pooled_auc_report = {}
    for arm, fields in pooled_auc.items():
        labels = np.concatenate(fields["labels"])
        probability = np.concatenate(fields["probability"])
        action_prior = np.concatenate(fields["action_prior"])
        pooled_auc_report[arm] = {
            "validation_support_auc": binary_auc(labels, probability),
            "validation_action_prior_null_auc": binary_auc(labels, action_prior),
        }
    result: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "runner_schema": RUNNER_SCHEMA,
        "claim_ceiling": CLAIM_CEILING,
        "spec": asdict(probe_spec),
        "source_paths": [str(Path(path)) for path in source_paths],
        "per_lineage": per_lineage,
        "pooled_auc": pooled_auc_report,
        "binding_decision": decision,
        "test_split_opened": False,
        "simulator_advanced": False,
        "episode_training": False,
        "held_out_ee_evaluated": False,
    }
    result["content_sha256"] = canonical_sha256(result)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(_canonical_bytes(result) + b"\n")
    return result


def _parse_checkpoint(values: Sequence[str]) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for value in values:
        try:
            seed_raw, path_raw = value.split("=", 1)
            seed = int(seed_raw)
        except (ValueError, TypeError) as error:
            raise V014Q3SupportProbeError(
                "--checkpoint must use SEED=PATH"
            ) from error
        result[seed] = Path(path_raw)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--checkpoint", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = run(
        source_paths=args.source,
        checkpoint_paths=_parse_checkpoint(args.checkpoint),
        output_path=args.output,
    )
    print(json.dumps(result["binding_decision"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
