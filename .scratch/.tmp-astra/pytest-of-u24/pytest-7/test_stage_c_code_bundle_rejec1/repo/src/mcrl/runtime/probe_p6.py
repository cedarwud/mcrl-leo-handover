"""Operational P6 protocol: near ties, perturbations and LR selection.

The sealed 2026-08-23 record named these obligations but did not define
them well enough to execute.  The corrected re-freeze makes the choices in
this module literal: every diagnostic is dimensionless relative to the
valid-action Q range, evaluation seeds are shared by all learning-rate arms,
and the selection rule is fixed before any arm runs.

This module deliberately keeps the statistical core independent of Torch
and the environment.  The long-running server launcher consumes these
functions; the behavior tests can force fragile and stable Q surfaces
without spending an episode on real ephemeris.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

import numpy as np

from ..errors import MCRLContractError, P6NonFiniteEvaluationError

P6_LEARNING_RATES: tuple[float, ...] = (0.01, 0.003, 0.001)
"""C-13's three controlled arms, in the declared execution order."""

P6_EVALUATION_SEEDS: tuple[int, ...] = (
    2026082401,
    2026082402,
    2026082403,
    2026082404,
    2026082405,
    2026082406,
    2026082407,
    2026082408,
    2026082409,
    2026082410,
)
"""Ten matched train-split evaluation seeds shared by every LR arm."""

P6_TRAIN_SEED: int = 2026082411
P6_ENV_SEED: int = 2026082412
P6_MOBILITY_SEED: int = 2026082413

MAIN_TRAIN_SEED: int = 42
MAIN_ENV_SEED: int = 1337
MAIN_MOBILITY_SEED: int = 7

P6_NEAR_TIE_FRACTION: float = 0.01
"""A valid action is near-top when its gap is at most 1% of the Q range."""

P6_PERTURBATION_STD_FRACTION: float = 0.01
"""Gaussian perturbation sigma, as a fraction of the valid-action Q range."""

P6_PERTURBATION_REPLICATES: int = 32
"""Fixed Monte-Carlo replicates per user/decision Q surface."""

P6_SELECTION_RULE: str = (
    "exclude non-finite or incomplete arms; maximize the mean final-policy "
    "calibrated scalar reward across the ten shared train-split evaluation "
    "seeds; exact ties follow the declared sweep order (0.01, 0.003, 0.001); "
    "near-tie, perturbation, and cross-seed ranking statistics are diagnostic "
    "only and never override this selection"
)


def _valid_q_values(
    scalarized_q: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    q = np.asarray(scalarized_q, dtype=np.float64)
    valid_mask = np.asarray(mask, dtype=bool)
    if q.ndim != 1 or valid_mask.shape != q.shape:
        raise MCRLContractError("scalarized_q and mask must be equal-length 1-D arrays")
    valid = np.flatnonzero(valid_mask)
    values = q[valid]
    if values.size and not np.all(np.isfinite(values)):
        raise P6NonFiniteEvaluationError(
            "P6 evaluation requires finite valid-action Q values"
        )
    return valid, values


def near_tie_actions(
    scalarized_q: np.ndarray,
    mask: np.ndarray,
    *,
    fraction: float = P6_NEAR_TIE_FRACTION,
) -> np.ndarray:
    """Return valid actions within ``fraction * Q_range`` of the top action.

    The comparison is scale-free.  A flat valid Q surface has range zero and
    therefore puts every valid action in the random-control set; an empty
    mask returns an empty set and remains the environment's declared no-op.
    """
    if not np.isfinite(fraction) or fraction < 0.0:
        raise ValueError("near-tie fraction must be finite and non-negative")
    valid, values = _valid_q_values(scalarized_q, mask)
    if valid.size <= 1:
        return valid.astype(np.int64, copy=True)
    q_range = float(values.max() - values.min())
    if q_range <= 0.0:
        return valid.astype(np.int64, copy=True)
    cutoff = float(values.max() - fraction * q_range)
    tolerance = np.finfo(np.float64).eps * max(1.0, abs(cutoff)) * 8.0
    return valid[values >= cutoff - tolerance].astype(np.int64, copy=False)


def perturbation_stability(
    scalarized_q: np.ndarray,
    mask: np.ndarray,
    rng: np.random.Generator,
    *,
    std_fraction: float = P6_PERTURBATION_STD_FRACTION,
    replicates: int = P6_PERTURBATION_REPLICATES,
) -> dict[str, float] | None:
    """Measure ranking stability under iid Gaussian Q perturbations.

    Noise is applied only to valid scalarized-Q entries with
    ``sigma = std_fraction * (Q_max - Q_min)``.  The reported action-retention
    rate asks whether the greedy choice survives.  Kendall tau asks whether
    all originally ordered valid pairs survive; exact base ties are excluded
    from the pair denominator rather than assigned an arbitrary order.
    """
    if not np.isfinite(std_fraction) or std_fraction < 0.0:
        raise ValueError("perturbation std fraction must be finite and non-negative")
    if replicates < 1:
        raise ValueError("perturbation replicates must be positive")
    valid, values = _valid_q_values(scalarized_q, mask)
    if valid.size < 2:
        return None

    q_range = float(values.max() - values.min())
    sigma = float(std_fraction * q_range)
    base_greedy_local = int(np.argmax(values))
    noise = rng.normal(0.0, sigma, size=(replicates, values.size))
    perturbed = values[None, :] + noise
    greedy_retention = float(
        np.mean(np.argmax(perturbed, axis=1) == base_greedy_local)
    )

    left, right = np.triu_indices(values.size, k=1)
    base_diff = values[left] - values[right]
    comparable = base_diff != 0.0
    comparable_pairs = int(np.count_nonzero(comparable))
    if comparable_pairs == 0:
        mean_tau = 1.0
    else:
        perturbed_diff = perturbed[:, left] - perturbed[:, right]
        products = np.sign(base_diff[comparable])[None, :] * np.sign(
            perturbed_diff[:, comparable]
        )
        mean_tau = float(np.mean(products))

    return {
        "greedy_action_retention": greedy_retention,
        "kendall_tau": mean_tau,
        "q_range": q_range,
        "noise_std": sigma,
        "replicates": float(replicates),
        "comparable_pairs": float(comparable_pairs),
    }


def cross_seed_rank_consistency(
    calibrated_scalar_reward_by_lr: Mapping[float, Sequence[float]],
) -> dict[str, Any]:
    """Rank LR arms independently on each shared seed and report agreement."""
    if not calibrated_scalar_reward_by_lr:
        raise MCRLContractError("cross-seed ranking needs at least one finite arm")
    supplied = {float(lr) for lr in calibrated_scalar_reward_by_lr}
    unknown = sorted(supplied - set(P6_LEARNING_RATES), reverse=True)
    if unknown:
        raise MCRLContractError(
            f"cross-seed ranking received undeclared learning rates: {unknown}"
        )
    learning_rates = tuple(lr for lr in P6_LEARNING_RATES if lr in supplied)
    sweep_index = {lr: index for index, lr in enumerate(P6_LEARNING_RATES)}
    rows = {
        float(lr): np.asarray(values, dtype=np.float64)
        for lr, values in calibrated_scalar_reward_by_lr.items()
    }
    lengths = {values.size for values in rows.values()}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) < 1:
        raise MCRLContractError("every LR arm must have the same non-empty seed scores")
    if any(not np.all(np.isfinite(values)) for values in rows.values()):
        raise MCRLContractError("cross-seed ranking scores must be finite")

    num_seeds = next(iter(lengths))
    orders: list[tuple[float, ...]] = []
    rank_rows: list[list[int]] = []
    for seed_index in range(num_seeds):
        order = tuple(
            sorted(
                learning_rates,
                key=lambda lr: (
                    -float(rows[lr][seed_index]),
                    sweep_index[lr],
                ),
            )
        )
        orders.append(order)
        rank_of = {lr: rank + 1 for rank, lr in enumerate(order)}
        rank_rows.append([rank_of[lr] for lr in learning_rates])

    counts = Counter(orders)
    modal_order, modal_count = min(
        counts.items(),
        key=lambda item: (
            -item[1],
            tuple(sweep_index[lr] for lr in item[0]),
        ),
    )
    num_arms = len(learning_rates)
    if num_arms == 1:
        kendall_w = 1.0
    else:
        rank_matrix = np.asarray(rank_rows, dtype=np.float64)
        rank_sums = rank_matrix.sum(axis=0)
        expected = num_seeds * (num_arms + 1.0) / 2.0
        spread = float(np.sum((rank_sums - expected) ** 2))
        denominator = float(num_seeds**2 * (num_arms**3 - num_arms))
        kendall_w = float(12.0 * spread / denominator)

    return {
        "num_seeds": int(num_seeds),
        "num_arms": int(num_arms),
        "modal_order": [float(lr) for lr in modal_order],
        "modal_order_fraction": float(modal_count / num_seeds),
        "kendall_w": float(np.clip(kendall_w, 0.0, 1.0)),
        "mean_rank": {
            str(lr): float(np.mean([row[index] for row in rank_rows]))
            for index, lr in enumerate(learning_rates)
        },
        "per_seed_orders": [[float(lr) for lr in order] for order in orders],
    }


def choose_learning_rate(
    arm_results: Mapping[float, Mapping[str, Any]],
) -> tuple[float, dict[str, Any]]:
    """Apply the frozen mean-score rule and declared-order exact tie break."""
    unknown = sorted(
        {float(lr) for lr in arm_results} - set(P6_LEARNING_RATES),
        reverse=True,
    )
    if unknown:
        raise MCRLContractError(f"P6 received undeclared learning-rate arms: {unknown}")

    excluded: list[float] = []
    eligible: list[dict[str, Any]] = []
    scores_for_consistency: dict[float, list[float]] = {}
    for lr in P6_LEARNING_RATES:
        arm = arm_results.get(lr)
        if arm is None:
            excluded.append(lr)
            continue
        if arm.get("status") != "complete":
            excluded.append(lr)
            continue
        scores = np.asarray(
            arm.get("calibrated_scalar_reward_by_seed", ()), dtype=np.float64
        )
        if (
            scores.size != len(P6_EVALUATION_SEEDS)
            or not np.all(np.isfinite(scores))
        ):
            excluded.append(lr)
            continue
        raw_retention = arm.get("perturbation_greedy_action_retention")
        retention = (
            float(raw_retention)
            if raw_retention is not None and np.isfinite(float(raw_retention))
            else None
        )
        row = {
            "learning_rate": lr,
            "mean_calibrated_scalar_reward": float(np.mean(scores)),
            "perturbation_greedy_action_retention": retention,
        }
        eligible.append(row)
        scores_for_consistency[lr] = [float(value) for value in scores.tolist()]

    if not eligible:
        raise MCRLContractError("P6 produced no finite, complete learning-rate arm")
    sweep_index = {lr: index for index, lr in enumerate(P6_LEARNING_RATES)}
    eligible.sort(
        key=lambda row: (
            -row["mean_calibrated_scalar_reward"],
            sweep_index[row["learning_rate"]],
        )
    )
    selected = float(eligible[0]["learning_rate"])
    report = {
        "rule": P6_SELECTION_RULE,
        "selected_learning_rate": selected,
        "excluded_nonfinite_or_incomplete": excluded,
        "eligible_ranking": eligible,
        "cross_seed_ranking_consistency": cross_seed_rank_consistency(
            scores_for_consistency
        ),
    }
    return selected, report
