"""Evaluation-only objective-head pivotality with common random numbers.

The probe asks a deliberately narrow question about an already-trained
checkpoint: does removing the Q2 or Q3 contribution from scalarized greedy
selection change the *physical* joint action, and what is the immediate
physics difference under the same fading/shadowing draw?

It does not retrain, alter a reward, or roll a counterfactual trajectory
forward.  Every alternative is scored at the same pre-decision state and is
discarded before the baseline action advances the real episode.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Sequence
from typing import Any

import numpy as np

from ..algorithms.modqn import MODQNTrainer
from ..env.action_contract import (
    Association,
    HandoverClass,
    SlotTable,
    no_op_actions,
)
from ..env.link_budget import BEAM_BANDWIDTH_HZ
from ..env.step import ActionEvaluation, StepOutcome
from .trainer_env import TrainerEnvironment


HEAD_INDICES: dict[str, int] = {"r2": 1, "r3": 2}

EFFECT_METRICS: tuple[str, ...] = (
    "system_ee_bits_per_j",
    "system_throughput_bps",
    "system_power_w",
    "served",
    "service_fraction",
    "eff_beams",
    "active_satellites",
    "mean_beam_load",
    "max_beam_load",
    "sum_squared_beam_load",
    "sum_sqrt_beam_power_w",
    "mean_beam_power_w",
    "mean_served_sinr",
    "mean_served_spectral_efficiency_bits_per_hz",
    "aggregate_spectral_efficiency_per_active_beam",
    "mean_served_interference_w",
    "r2_total",
    "r3_total",
    "handover_phi1",
    "handover_phi2",
)


def weights_without_head(
    objective_weights: Sequence[float], head_index: int
) -> tuple[float, float, float]:
    """Zero one head and renormalize the remaining deployed weights."""
    weights = np.asarray(tuple(objective_weights), dtype=np.float64)
    if weights.shape != (3,):
        raise ValueError("objective_weights must contain exactly three values")
    if not 0 <= int(head_index) < 3:
        raise ValueError("head_index must be 0, 1, or 2")
    if np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
        raise ValueError("objective weights must be finite and non-negative")
    weights[int(head_index)] = 0.0
    remaining = float(weights.sum())
    if remaining <= 0.0:
        raise ValueError("at least one non-ablated objective needs positive weight")
    weights /= remaining
    return tuple(float(value) for value in weights)  # type: ignore[return-value]


def masked_greedy_actions(
    scalarized_q: np.ndarray, masks: np.ndarray
) -> np.ndarray:
    """Greedy action per user, with the environment's no-op sentinel."""
    values = np.asarray(scalarized_q, dtype=np.float64)
    valid_masks = np.asarray(masks, dtype=bool)
    if values.ndim != 2 or valid_masks.shape != values.shape:
        raise ValueError("scalarized_q and masks must have the same (U, C) shape")
    actions = no_op_actions(values.shape[0])
    for uid, mask in enumerate(valid_masks):
        valid = np.flatnonzero(mask)
        if valid.size:
            actions[uid] = int(valid[np.argmax(values[uid, valid])])
    return actions


def physical_action_keys(
    actions: np.ndarray, slot_tables: Sequence[SlotTable]
) -> tuple[tuple[int, int] | None, ...]:
    """Map relative action indices to physical ``(NORAD, cell)`` identities."""
    chosen = np.asarray(actions)
    if chosen.shape != (len(slot_tables),):
        raise ValueError("actions and slot_tables disagree on user count")
    keys: list[tuple[int, int] | None] = []
    for action, table in zip(chosen.tolist(), slot_tables, strict=True):
        association = table.association(int(action))
        keys.append(
            (association.norad_id, association.cell_id)
            if isinstance(association, Association)
            else None
        )
    return tuple(keys)


def pivotality_counts(
    full_actions: np.ndarray,
    ablated_actions: np.ndarray,
    slot_tables: Sequence[SlotTable],
) -> dict[str, Any]:
    """Count index changes separately from real physical-action changes."""
    full = np.asarray(full_actions)
    ablated = np.asarray(ablated_actions)
    if full.shape != ablated.shape or full.shape != (len(slot_tables),):
        raise ValueError("action vectors and slot_tables disagree on user count")
    index_flip = full != ablated
    full_keys = physical_action_keys(full, slot_tables)
    ablated_keys = physical_action_keys(ablated, slot_tables)
    physical_ids = [
        uid
        for uid, (baseline, alternative) in enumerate(
            zip(full_keys, ablated_keys, strict=True)
        )
        if baseline != alternative
    ]
    action_index_flips = int(np.count_nonzero(index_flip))
    physical_action_flips = len(physical_ids)
    return {
        "action_index_flips": action_index_flips,
        "physical_action_flips": physical_action_flips,
        "index_only_flips": action_index_flips - physical_action_flips,
        "physical_flip_user_ids": physical_ids,
    }


def action_evaluation_metrics(
    evaluation: ActionEvaluation,
    *,
    num_users: int,
    beam_bandwidth_hz: float = BEAM_BANDWIDTH_HZ,
) -> dict[str, float | int]:
    """Project immediate physics onto EE and its main mediators."""
    energy = evaluation.energy
    loads = np.asarray(
        list(evaluation.resolution.eligible_load_by_beam.values()),
        dtype=np.float64,
    )
    powers = np.asarray(evaluation.radiating.power_w, dtype=np.float64)
    served = np.asarray(evaluation.resolution.served, dtype=bool)
    sinr = np.asarray(evaluation.link_sinr[served], dtype=np.float64)
    interference = np.asarray(
        evaluation.interference.total_w[served], dtype=np.float64
    )
    handovers = Counter(item.value for item in evaluation.handovers)
    reward_matrix = evaluation.reward_matrix
    active_beams = max(int(energy.eff_beams), 1)

    return {
        "system_ee_bits_per_j": float(energy.system_ee_bits_per_j),
        "system_throughput_bps": float(energy.system_throughput_bps),
        "system_power_w": float(energy.system_consumed_power_w),
        "served": int(energy.served),
        "service_fraction": float(energy.served / num_users),
        "eff_beams": int(energy.eff_beams),
        "active_satellites": int(len(set(evaluation.radiating.norad_ids.tolist()))),
        "mean_beam_load": float(np.mean(loads)) if loads.size else 0.0,
        "max_beam_load": float(np.max(loads)) if loads.size else 0.0,
        "sum_squared_beam_load": float(np.square(loads).sum()),
        "sum_sqrt_beam_power_w": float(np.sqrt(powers).sum()),
        "mean_beam_power_w": float(np.mean(powers)) if powers.size else 0.0,
        "mean_served_sinr": float(np.mean(sinr)) if sinr.size else 0.0,
        "mean_served_spectral_efficiency_bits_per_hz": (
            float(np.mean(np.log2(1.0 + sinr))) if sinr.size else 0.0
        ),
        "aggregate_spectral_efficiency_per_active_beam": (
            float(energy.system_throughput_bps)
            / (float(beam_bandwidth_hz) * active_beams)
            if energy.eff_beams
            else 0.0
        ),
        "mean_served_interference_w": (
            float(np.mean(interference)) if interference.size else 0.0
        ),
        "r2_total": float(reward_matrix[:, 1].sum()),
        "r3_total": float(reward_matrix[:, 2].sum()),
        "handover_phi1": int(handovers.get(HandoverClass.INTRA_SATELLITE.value, 0)),
        "handover_phi2": int(handovers.get(HandoverClass.INTER_SATELLITE.value, 0)),
    }


def full_minus_ablated(
    full: dict[str, float | int], ablated: dict[str, float | int]
) -> dict[str, float]:
    """Positive EE means the deployed head helped in this one-step contrast."""
    return {
        key: float(full[key]) - float(ablated[key]) for key in EFFECT_METRICS
    }


def run_head_pivotality_rollout(
    trainer: MODQNTrainer,
    environment: TrainerEnvironment,
    *,
    evaluation_seed: int,
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
) -> dict[str, Any]:
    """Run one normal baseline rollout with discarded Q2/Q3 ablations."""
    states, wrapped_masks, observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    deployed_weights = tuple(float(value) for value in trainer.config.objective_weights)
    ablated_weights = {
        head: weights_without_head(deployed_weights, index)
        for head, index in HEAD_INDICES.items()
    }
    steps: list[dict[str, Any]] = []

    while True:
        masks = np.stack([wrapped.mask for wrapped in wrapped_masks])
        surfaces = {
            "full": trainer.scalarized_q_values(
                encoded, objective_weights=deployed_weights
            )
        }
        for head, weights in ablated_weights.items():
            surfaces[head] = trainer.scalarized_q_values(
                encoded, objective_weights=weights
            )
        actions = {
            name: masked_greedy_actions(surface, masks)
            for name, surface in surfaces.items()
        }

        step_environment = environment.environment
        evaluations = {
            name: step_environment.evaluate_actions(action, env_rng)
            for name, action in actions.items()
        }
        metrics = {
            name: action_evaluation_metrics(
                evaluation,
                num_users=environment.num_users,
                beam_bandwidth_hz=step_environment.physics.beam_bandwidth_hz,
            )
            for name, evaluation in evaluations.items()
        }

        head_rows: dict[str, Any] = {}
        for head in HEAD_INDICES:
            counts = pivotality_counts(
                actions["full"], actions[head], observation.candidates.slot_tables
            )
            head_rows[head] = counts | {
                "ablated_weights": list(ablated_weights[head]),
                "ablated_metrics": metrics[head],
                "full_minus_ablated": full_minus_ablated(
                    metrics["full"], metrics[head]
                ),
            }

        result = environment.step(actions["full"], env_rng)
        outcome = environment.last_outcome
        _assert_preview_matches_outcome(evaluations["full"], outcome)
        steps.append(
            {
                "step_index": int(outcome.step_index),
                "decision_users": int(np.count_nonzero(np.any(masks, axis=1))),
                "full_metrics": metrics["full"],
                "heads": head_rows,
            }
        )
        if result.done:
            break
        states = result.user_states
        wrapped_masks = result.action_masks
        observation = outcome.observation
        encoded = trainer.encode_states(states)

    return {
        "schema": "mcrl-head-pivotality-v1",
        "evaluation_seed": int(evaluation_seed),
        "estimand": (
            "full policy minus renormalized policy with one objective-Q head "
            "removed, at the same pre-decision state and same current-slot "
            "fading/shadowing draw"
        ),
        "trajectory": (
            "only the deployed full policy advances the episode; every ablated "
            "evaluation is immediate and discarded"
        ),
        "deployed_weights": list(deployed_weights),
        "ablated_weights": {
            head: list(weights) for head, weights in ablated_weights.items()
        },
        "summary": _summarize_steps(steps),
        "steps": steps,
    }


def _assert_preview_matches_outcome(
    preview: ActionEvaluation, outcome: StepOutcome
) -> None:
    """Runtime trip-wire proving the probe did not disturb the real step."""
    arrays = (
        (preview.reward_matrix, outcome.reward_matrix, "reward_matrix"),
        (preview.link_power_w, outcome.link_power_w, "link_power_w"),
        (preview.link_sinr, outcome.link_sinr, "link_sinr"),
        (preview.link_rate_bps, outcome.link_rate_bps, "link_rate_bps"),
        (preview.radiating.norad_ids, outcome.radiating.norad_ids, "beam_norads"),
        (preview.radiating.cell_ids, outcome.radiating.cell_ids, "beam_cells"),
        (preview.radiating.power_w, outcome.radiating.power_w, "beam_power_w"),
        (
            preview.interference.total_w,
            outcome.interference.total_w,
            "interference_w",
        ),
    )
    for expected, observed, name in arrays:
        if not np.array_equal(expected, observed):
            raise RuntimeError(f"counterfactual preview changed baseline {name}")
    if preview.handovers != outcome.handovers or preview.energy != outcome.energy:
        raise RuntimeError("counterfactual preview changed baseline reward physics")


def _mean_rows(rows: Sequence[dict[str, float | int]]) -> dict[str, float]:
    if not rows:
        return {key: 0.0 for key in EFFECT_METRICS}
    return {
        key: float(statistics.fmean(float(row[key]) for row in rows))
        for key in EFFECT_METRICS
    }


def _summarize_steps(steps: Sequence[dict[str, Any]]) -> dict[str, Any]:
    decision_user_steps = sum(int(row["decision_users"]) for row in steps)
    full_rows = [row["full_metrics"] for row in steps]
    heads: dict[str, Any] = {}
    for head in HEAD_INDICES:
        rows = [row["heads"][head] for row in steps]
        physical_flips = sum(int(row["physical_action_flips"]) for row in rows)
        changed = [row for row in rows if int(row["physical_action_flips"]) > 0]
        heads[head] = {
            "total_action_index_flips": sum(
                int(row["action_index_flips"]) for row in rows
            ),
            "total_physical_action_flips": physical_flips,
            "total_index_only_flips": sum(int(row["index_only_flips"]) for row in rows),
            "physical_pivotality_rate": (
                float(physical_flips / decision_user_steps)
                if decision_user_steps
                else 0.0
            ),
            "steps_with_physical_flips": len(changed),
            "mean_ablated_metrics": _mean_rows(
                [row["ablated_metrics"] for row in rows]
            ),
            "mean_full_minus_ablated": _mean_rows(
                [row["full_minus_ablated"] for row in rows]
            ),
            "changed_steps_mean_full_minus_ablated": _mean_rows(
                [row["full_minus_ablated"] for row in changed]
            ),
        }
    return {
        "steps": len(steps),
        "decision_user_steps": decision_user_steps,
        "mean_full_metrics": _mean_rows(full_rows),
        "heads": heads,
    }
