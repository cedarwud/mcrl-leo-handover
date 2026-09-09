"""Anchor-then-seed balanced validation metric for the V0.4 C3 gate.

The source schedule caps physical-anchor reuse, but row counts can still vary
because one focal context may emit one to four siblings.  This module prevents
those counts from silently weighting the promotion metric.  It fits all null
parameters on TRAIN only, then averages absolute error in the fixed order
comparison -> physical anchor -> validation seed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping, Sequence

import numpy as np

from ..algorithms.ee_axis_pairwise import EEAxisPairBatch
from ..errors import MCRLContractError


class C3V04LearnabilityMetricError(MCRLContractError):
    """The V0.4 C3 validation estimand is malformed or unidentified."""


def _positive_float(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise C3V04LearnabilityMetricError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise C3V04LearnabilityMetricError(
            f"{field} must be finite and positive"
        )
    return result


def _anchor(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3V04LearnabilityMetricError(f"{field} must be lowercase SHA-256")
    return value


def _metadata(
    *,
    rows: int,
    source_seeds: Sequence[int],
    anchor_sha256s: Sequence[str],
) -> tuple[np.ndarray, np.ndarray]:
    seeds = np.asarray(source_seeds)
    anchors = np.asarray(anchor_sha256s, dtype=object)
    if seeds.shape != (rows,) or anchors.shape != (rows,):
        raise C3V04LearnabilityMetricError(
            "validation seed/anchor metadata must align with rows"
        )
    if not np.issubdtype(seeds.dtype, np.integer) or np.any(seeds < 0):
        raise C3V04LearnabilityMetricError(
            "validation source seeds must be nonnegative integers"
        )
    normalized = np.asarray(
        [_anchor(value, field="validation anchor") for value in anchors.tolist()],
        dtype=object,
    )
    return seeds.astype(np.int64, copy=False), normalized


def anchor_then_seed_mae(
    absolute_errors: np.ndarray,
    *,
    source_seeds: Sequence[int],
    anchor_sha256s: Sequence[str],
) -> tuple[float, tuple[tuple[int, float], ...], tuple[tuple[int, int], ...]]:
    """Average row errors within anchor, anchors within seed, then seeds."""

    errors = np.asarray(absolute_errors, dtype=np.float64)
    if errors.ndim != 1 or errors.size < 1 or not np.all(np.isfinite(errors)):
        raise C3V04LearnabilityMetricError(
            "absolute_errors must be one nonempty finite vector"
        )
    if np.any(errors < 0.0):
        raise C3V04LearnabilityMetricError("absolute_errors must be nonnegative")
    seeds, anchors = _metadata(
        rows=errors.size,
        source_seeds=source_seeds,
        anchor_sha256s=anchor_sha256s,
    )
    per_seed: list[tuple[int, float]] = []
    anchor_counts: list[tuple[int, int]] = []
    for seed in sorted(int(value) for value in np.unique(seeds)):
        keep_seed = seeds == seed
        names = sorted(set(str(value) for value in anchors[keep_seed].tolist()))
        if not names:
            raise C3V04LearnabilityMetricError(
                "every validation source seed must contain an anchor"
            )
        anchor_maes = [
            float(np.mean(errors[keep_seed & (anchors == name)])) for name in names
        ]
        per_seed.append((seed, float(np.mean(anchor_maes))))
        anchor_counts.append((seed, len(names)))
    if not per_seed:
        raise C3V04LearnabilityMetricError("validation has no source seed")
    return (
        float(np.mean([value for _seed, value in per_seed])),
        tuple(per_seed),
        tuple(anchor_counts),
    )


def _pair_arrays(
    batch: EEAxisPairBatch,
    *,
    state_dim: int,
    action_dim: int,
    kappa_bits: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not isinstance(batch, EEAxisPairBatch):
        raise C3V04LearnabilityMetricError("gate input must be EEAxisPairBatch")
    try:
        batch.validate(state_dim=state_dim, action_dim=action_dim)
    except (MCRLContractError, TypeError, ValueError) as error:
        raise C3V04LearnabilityMetricError("gate pair batch is invalid") from error
    reference = np.asarray(batch.reference_actions, dtype=np.int64)
    candidate = np.asarray(batch.candidate_actions, dtype=np.int64)
    targets = (
        np.asarray(batch.target_surplus_bits, dtype=np.float64) / kappa_bits
    )
    return reference, candidate, targets


def _fit_action_only(
    reference: np.ndarray,
    candidate: np.ndarray,
    targets: np.ndarray,
    *,
    action_dim: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    design = np.zeros((targets.size, action_dim), dtype=np.float64)
    indices = np.arange(targets.size)
    design[indices, candidate] = 1.0
    design[indices, reference] = -1.0
    coefficients, _residuals, _rank, _singular = np.linalg.lstsq(
        design, targets, rcond=None
    )
    adjacency = [set() for _ in range(action_dim)]
    for left, right in zip(reference.tolist(), candidate.tolist(), strict=True):
        adjacency[left].add(right)
        adjacency[right].add(left)
    components = np.full(action_dim, -1, dtype=np.int64)
    component_id = 0
    for start in range(action_dim):
        if components[start] >= 0 or not adjacency[start]:
            continue
        stack = [start]
        components[start] = component_id
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if components[neighbor] < 0:
                    components[neighbor] = component_id
                    stack.append(neighbor)
        component_id += 1
    active = int(np.unique(np.concatenate((reference, candidate))).size)
    return coefficients, components, active


@dataclass(frozen=True)
class C3V04BalancedGeneralization:
    """One held-out Q3 receipt under the frozen hierarchical estimand."""

    train_pairs: int
    heldout_pairs: int
    active_train_actions: int
    validation_seeds: int
    validation_anchors: int
    model_mae: float
    action_only_baseline_mae: float
    zero_baseline_mae: float
    train_median_value: float
    train_median_baseline_mae: float
    strongest_baseline_name: str
    strongest_state_independent_baseline_mae: float
    model_to_strongest_null_mae_ratio: float
    skill_vs_strongest_null: float
    model_mae_by_seed: tuple[tuple[int, float], ...]
    anchor_counts_by_seed: tuple[tuple[int, int], ...]

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["model_mae_by_seed"] = {
            str(seed): value for seed, value in self.model_mae_by_seed
        }
        payload["anchor_counts_by_seed"] = {
            str(seed): value for seed, value in self.anchor_counts_by_seed
        }
        return payload


def compute_anchor_seed_balanced_generalization(
    *,
    train_batch: EEAxisPairBatch,
    validation_batch: EEAxisPairBatch,
    validation_source_seeds: Sequence[int],
    validation_anchor_sha256s: Sequence[str],
    heldout_q_surface: np.ndarray,
    state_dim: int,
    action_dim: int,
    kappa_bits: float,
) -> C3V04BalancedGeneralization:
    """Compare Q3 with the strongest TRAIN-only null under equal seed weight."""

    scale = _positive_float(kappa_bits, field="kappa_bits")
    if type(state_dim) is not int or state_dim < 1:
        raise C3V04LearnabilityMetricError("state_dim must be a positive integer")
    if type(action_dim) is not int or action_dim < 2:
        raise C3V04LearnabilityMetricError("action_dim must exceed one")
    train_r, train_c, train_y = _pair_arrays(
        train_batch,
        state_dim=state_dim,
        action_dim=action_dim,
        kappa_bits=scale,
    )
    valid_r, valid_c, valid_y = _pair_arrays(
        validation_batch,
        state_dim=state_dim,
        action_dim=action_dim,
        kappa_bits=scale,
    )
    q = np.asarray(heldout_q_surface, dtype=np.float64)
    if q.shape != (valid_y.size, action_dim) or not np.all(np.isfinite(q)):
        raise C3V04LearnabilityMetricError(
            "heldout_q_surface must be finite (heldout rows, action_dim)"
        )
    seeds, anchors = _metadata(
        rows=valid_y.size,
        source_seeds=validation_source_seeds,
        anchor_sha256s=validation_anchor_sha256s,
    )
    coefficients, components, active = _fit_action_only(
        train_r, train_c, train_y, action_dim=action_dim
    )
    if np.any(components[valid_r] < 0) or np.any(
        components[valid_r] != components[valid_c]
    ):
        raise C3V04LearnabilityMetricError(
            "validation action pair is unidentified by the TRAIN graph"
        )
    rows = np.arange(valid_y.size)
    predictions: Mapping[str, np.ndarray] = {
        "model": q[rows, valid_c] - q[rows, valid_r],
        "action_only": coefficients[valid_c] - coefficients[valid_r],
        "zero": np.zeros_like(valid_y),
        "train_median": np.full_like(valid_y, float(np.median(train_y))),
    }
    metrics: dict[str, float] = {}
    model_by_seed: tuple[tuple[int, float], ...] = ()
    anchor_counts: tuple[tuple[int, int], ...] = ()
    for name, prediction in predictions.items():
        value, by_seed, counts = anchor_then_seed_mae(
            np.abs(prediction - valid_y),
            source_seeds=seeds,
            anchor_sha256s=anchors,
        )
        metrics[name] = value
        if name == "model":
            model_by_seed = by_seed
            anchor_counts = counts
    nulls = {
        name: metrics[name] for name in ("action_only", "train_median", "zero")
    }
    strongest_name, strongest_mae = min(
        nulls.items(), key=lambda row: (row[1], row[0])
    )
    if strongest_mae <= 0.0:
        raise C3V04LearnabilityMetricError(
            "strongest state-independent null has no positive error"
        )
    ratio = metrics["model"] / strongest_mae
    return C3V04BalancedGeneralization(
        train_pairs=int(train_y.size),
        heldout_pairs=int(valid_y.size),
        active_train_actions=active,
        validation_seeds=len(set(int(value) for value in seeds.tolist())),
        validation_anchors=len(set(str(value) for value in anchors.tolist())),
        model_mae=metrics["model"],
        action_only_baseline_mae=metrics["action_only"],
        zero_baseline_mae=metrics["zero"],
        train_median_value=float(np.median(train_y)),
        train_median_baseline_mae=metrics["train_median"],
        strongest_baseline_name=strongest_name,
        strongest_state_independent_baseline_mae=strongest_mae,
        model_to_strongest_null_mae_ratio=float(ratio),
        skill_vs_strongest_null=float(1.0 - ratio),
        model_mae_by_seed=model_by_seed,
        anchor_counts_by_seed=anchor_counts,
    )


__all__ = [
    "C3V04BalancedGeneralization",
    "C3V04LearnabilityMetricError",
    "anchor_then_seed_mae",
    "compute_anchor_seed_balanced_generalization",
]
