"""Compact held-out metrics for the V0.14 Q2/Q3 learner gate."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..errors import MCRLContractError
from .ee_axis_v04_c3_learnability import (
    C3V04BalancedGeneralization,
    compute_anchor_seed_balanced_generalization,
)


class EEAxisV014LearnabilityError(MCRLContractError):
    """A compact surface dataset or joint diagnostic is malformed."""


def _readonly(value: np.ndarray) -> np.ndarray:
    result = np.array(value, copy=True, order="C")
    result.setflags(write=False)
    return result


def _anchor(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise EEAxisV014LearnabilityError(
            "anchor_sha256s must contain lowercase SHA-256 values"
        )
    return value


@dataclass(frozen=True)
class CompactHeadSurfaceDataset:
    """One compact row per focal-user anchor, not per action comparison."""

    states: np.ndarray
    masks: np.ndarray
    reference_actions: np.ndarray
    target_surfaces_bits: np.ndarray
    source_seeds: np.ndarray
    anchor_sha256s: np.ndarray

    def __post_init__(self) -> None:
        states = np.asarray(self.states, dtype=np.float32)
        masks = np.asarray(self.masks)
        references = np.asarray(self.reference_actions)
        targets = np.asarray(self.target_surfaces_bits, dtype=np.float64)
        seeds = np.asarray(self.source_seeds)
        anchors = np.asarray(self.anchor_sha256s, dtype=str)
        if states.ndim != 2 or states.shape[0] < 1 or states.shape[1] < 1:
            raise EEAxisV014LearnabilityError("states must be a nonempty matrix")
        rows = int(states.shape[0])
        if not np.all(np.isfinite(states)):
            raise EEAxisV014LearnabilityError("states must be finite")
        if (
            masks.ndim != 2
            or masks.dtype != np.bool_
            or masks.shape[0] != rows
            or masks.shape[1] < 2
            or not np.all(np.any(masks, axis=1))
        ):
            raise EEAxisV014LearnabilityError(
                "masks must be Boolean, action-aligned, and admit a legal action"
            )
        actions = int(masks.shape[1])
        if (
            references.shape != (rows,)
            or not np.issubdtype(references.dtype, np.integer)
            or np.any(references < 0)
            or np.any(references >= actions)
            or not np.all(masks[np.arange(rows), references])
        ):
            raise EEAxisV014LearnabilityError(
                "reference_actions must identify one legal action per row"
            )
        comparison_counts = masks.sum(axis=1) - 1
        if np.any(comparison_counts < 1):
            raise EEAxisV014LearnabilityError(
                "every compact row needs a non-reference legal comparison"
            )
        if targets.shape != (rows, actions) or not np.all(np.isfinite(targets)):
            raise EEAxisV014LearnabilityError(
                "target_surfaces_bits must be finite and action-aligned"
            )
        if (
            seeds.shape != (rows,)
            or not np.issubdtype(seeds.dtype, np.integer)
            or np.any(seeds < 0)
            or anchors.shape != (rows,)
        ):
            raise EEAxisV014LearnabilityError("compact source metadata is malformed")
        for value in anchors.tolist():
            _anchor(value)
        object.__setattr__(self, "states", _readonly(states))
        object.__setattr__(self, "masks", _readonly(masks.astype(np.bool_)))
        object.__setattr__(
            self, "reference_actions", _readonly(references.astype(np.int64))
        )
        object.__setattr__(self, "target_surfaces_bits", _readonly(targets))
        object.__setattr__(self, "source_seeds", _readonly(seeds.astype(np.int64)))
        object.__setattr__(self, "anchor_sha256s", _readonly(anchors.astype("U64")))

    @property
    def rows(self) -> int:
        return int(self.states.shape[0])

    @property
    def action_dim(self) -> int:
        return int(self.masks.shape[1])

    def subset(self, indices: np.ndarray) -> "CompactHeadSurfaceDataset":
        selected = np.asarray(indices)
        if (
            selected.ndim != 1
            or selected.size < 1
            or not np.issubdtype(selected.dtype, np.integer)
            or np.any(selected < 0)
            or np.any(selected >= self.rows)
        ):
            raise EEAxisV014LearnabilityError("subset indices are invalid")
        return CompactHeadSurfaceDataset(
            states=self.states[selected],
            masks=self.masks[selected],
            reference_actions=self.reference_actions[selected],
            target_surfaces_bits=self.target_surfaces_bits[selected],
            source_seeds=self.source_seeds[selected],
            anchor_sha256s=self.anchor_sha256s[selected],
        )


def _expanded_metric_batch(
    dataset: CompactHeadSurfaceDataset,
) -> tuple[EEAxisPairBatch, np.ndarray, np.ndarray, np.ndarray]:
    comparison = np.array(dataset.masks, copy=True)
    comparison[np.arange(dataset.rows), dataset.reference_actions] = False
    anchor_rows, candidates = np.nonzero(comparison)
    references = dataset.reference_actions[anchor_rows]
    targets = (
        dataset.target_surfaces_bits[anchor_rows, candidates]
        - dataset.target_surfaces_bits[anchor_rows, references]
    )
    batch = EEAxisPairBatch(
        states=np.zeros((anchor_rows.size, 1), dtype=np.float32),
        reference_actions=references.astype(np.int64, copy=False),
        candidate_actions=candidates.astype(np.int64, copy=False),
        target_surplus_bits=targets,
        action_masks=dataset.masks[anchor_rows],
    )
    return (
        batch,
        anchor_rows,
        dataset.source_seeds[anchor_rows],
        dataset.anchor_sha256s[anchor_rows],
    )


def compact_balanced_generalization(
    *,
    train: CompactHeadSurfaceDataset,
    validation: CompactHeadSurfaceDataset,
    validation_q_surface: np.ndarray,
    kappa_bits: float,
) -> C3V04BalancedGeneralization:
    """Reuse the frozen V0.4 strong-null metric without repeating states."""

    if train.action_dim != validation.action_dim:
        raise EEAxisV014LearnabilityError("train/validation action dimensions differ")
    if not math.isfinite(float(kappa_bits)) or float(kappa_bits) <= 0.0:
        raise EEAxisV014LearnabilityError("kappa_bits must be finite and positive")
    q = np.asarray(validation_q_surface, dtype=np.float64)
    if q.shape != (validation.rows, validation.action_dim) or not np.all(
        np.isfinite(q)
    ):
        raise EEAxisV014LearnabilityError(
            "validation_q_surface must align with compact validation rows"
        )
    train_batch, _train_rows, _train_seeds, _train_anchors = (
        _expanded_metric_batch(train)
    )
    validation_batch, validation_rows, validation_seeds, validation_anchors = (
        _expanded_metric_batch(validation)
    )
    return compute_anchor_seed_balanced_generalization(
        train_batch=train_batch,
        validation_batch=validation_batch,
        validation_source_seeds=validation_seeds,
        validation_anchor_sha256s=validation_anchors,
        heldout_q_surface=q[validation_rows],
        state_dim=1,
        action_dim=train.action_dim,
        kappa_bits=float(kappa_bits),
    )


def _joint_array(value: object, *, field: str, shape: tuple[int, int]) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != shape or not np.all(np.isfinite(result)):
        raise EEAxisV014LearnabilityError(f"{field} must be finite shape {shape}")
    return result


def joint_teacher_student_diagnostics(
    *,
    q1_values: np.ndarray,
    q2_target_bits: np.ndarray,
    q3_target_bits: np.ndarray,
    q2_hat: np.ndarray,
    q3_hat: np.ndarray,
    masks: np.ndarray,
    q3_compatibility: np.ndarray,
    kappa_bits: float,
) -> dict[str, float | int]:
    """Compare learned and oracle summed decisions without running a rollout."""

    mask = np.asarray(masks)
    if (
        mask.ndim != 2
        or mask.dtype != np.bool_
        or mask.shape[0] < 1
        or mask.shape[1] < 2
        or not np.all(np.any(mask, axis=1))
    ):
        raise EEAxisV014LearnabilityError(
            "joint masks must admit at least one legal action per anchor"
        )
    shape = (int(mask.shape[0]), int(mask.shape[1]))
    q1 = _joint_array(q1_values, field="q1_values", shape=shape)
    q2 = _joint_array(q2_target_bits, field="q2_target_bits", shape=shape)
    q3 = _joint_array(q3_target_bits, field="q3_target_bits", shape=shape)
    learned_q2 = _joint_array(q2_hat, field="q2_hat", shape=shape)
    learned_q3 = _joint_array(q3_hat, field="q3_hat", shape=shape)
    compatibility = np.asarray(q3_compatibility)
    if compatibility.dtype != np.bool_ or compatibility.shape != shape:
        raise EEAxisV014LearnabilityError(
            "q3_compatibility must be Boolean and action-aligned"
        )
    if np.any(compatibility[~mask]):
        raise EEAxisV014LearnabilityError("compatibility is true on an illegal action")
    scale = float(kappa_bits)
    if not math.isfinite(scale) or scale <= 0.0:
        raise EEAxisV014LearnabilityError("kappa_bits must be finite and positive")

    background_scores = q1 + q2 / scale
    teacher_scores = background_scores + q3 / scale
    student_scores = q1 + learned_q2 + learned_q3

    def select(scores: np.ndarray) -> np.ndarray:
        return np.argmax(np.where(mask, scores, -np.inf), axis=1)

    background = select(background_scores)
    teacher = select(teacher_scores)
    student = select(student_scores)
    teacher_change = teacher != background
    student_change = student != background
    teacher_exposure = int(np.count_nonzero(teacher_change))
    student_exposure = int(np.count_nonzero(student_change))
    rows = np.arange(shape[0])
    agreement = student == teacher
    supported = compatibility[rows, student] & (q3[rows, student] > 0.0)
    all_agreement_count = int(np.count_nonzero(agreement))
    background_agreement_count = int(np.count_nonzero(background == teacher))
    teacher_change_agreement_count = int(
        np.count_nonzero(agreement & teacher_change)
    )
    student_supported_change_count = int(
        np.count_nonzero(supported & student_change)
    )
    return {
        "anchors": shape[0],
        "all_anchor_argmax_agreement_count": all_agreement_count,
        "all_anchor_argmax_agreement": float(np.mean(agreement)),
        "background_teacher_argmax_agreement_count": background_agreement_count,
        "background_teacher_argmax_agreement": float(np.mean(background == teacher)),
        "teacher_change_exposure": teacher_exposure,
        "teacher_change_agreement_count": teacher_change_agreement_count,
        "teacher_change_conditional_agreement": float(
            np.mean(agreement[teacher_change]) if teacher_exposure else 0.0
        ),
        "student_change_exposure": student_exposure,
        "student_supported_change_count": student_supported_change_count,
        "student_changed_action_positive_support_rate": float(
            np.mean(supported[student_change]) if student_exposure else 0.0
        ),
    }


__all__ = [
    "CompactHeadSurfaceDataset",
    "EEAxisV014LearnabilityError",
    "compact_balanced_generalization",
    "joint_teacher_student_diagnostics",
]
