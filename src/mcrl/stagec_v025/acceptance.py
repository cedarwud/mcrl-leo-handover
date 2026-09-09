"""Synthetic-only acceptance helpers for contract-v1 T1--T3."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from .learner import ARM_ORDER
from .evaluation import EvaluationRunner
from .merge import AdditiveTotals, DROP_ARMS, merge_receipts


def _binomial_uncertainty(successes: int, trials: int) -> dict[str, float | int]:
    rate = successes / trials
    half_width = 1.96 * math.sqrt(max(rate * (1.0 - rate), 0.25 / trials) / trials)
    return {
        "successes": successes,
        "trials": trials,
        "estimate": rate,
        "normal_95_half_width": half_width,
    }


def synthetic_crossed_clusters(
    *,
    date_count: int,
    seed_count: int,
    date_sd: float,
    seed_sd: float,
    true_relative_gain: Sequence[float],
    rng: np.random.Generator,
    qos_failure: bool = False,
) -> dict[tuple[str, int], dict[str, AdditiveTotals]]:
    """Generate paired date×seed totals representing two unequal-energy worlds."""

    if len(true_relative_gain) != 3:
        raise ValueError("three primary contrast alternatives are required")
    date_effect = rng.normal(0.0, date_sd, (3, date_count))
    seed_effect = rng.normal(0.0, seed_sd, (3, seed_count))
    clusters: dict[tuple[str, int], dict[str, AdditiveTotals]] = {}
    for date_index in range(date_count):
        date = f"D{date_index:03d}"
        for seed_index in range(seed_count):
            # This is the sum of two raw worlds with deliberately unequal
            # energy/opportunity weights.  The receipt-path test separately
            # proves the same aggregation from raw rows.
            energy = 2.0 + 0.25 * ((date_index + 2 * seed_index) % 5)
            common = {
                "joules": energy,
                "complete_num": 200,
                "complete_den": 200,
                "handover_num": 10,
                "handover_den": 200,
                "phi_num": 10,
                "phi_den": 400,
            }
            arms: dict[str, AdditiveTotals] = {
                "FULL": AdditiveTotals(
                    bits=100.0 * energy,
                    **{
                        **common,
                        "complete_num": 0 if qos_failure and date_index == 0 else 200,
                    },
                )
            }
            for contrast_index, arm in enumerate(DROP_ARMS):
                log_effect = (
                    math.log1p(true_relative_gain[contrast_index])
                    + date_effect[contrast_index, date_index]
                    + seed_effect[contrast_index, seed_index]
                )
                drop_ee = 100.0 / math.exp(log_effect)
                arms[arm] = AdditiveTotals(bits=drop_ee * energy, **common)
            # Non-primary policies are present so these clusters can also be
            # fed to report inventory paths without changing primary inference.
            for arm in (*ARM_ORDER[4:], "S0", "S_UNI"):
                arms[arm] = AdditiveTotals(bits=98.0 * energy, **common)
            clusters[(date, 1000 + seed_index)] = arms
    return clusters


def crossed_inference_calibration(
    *,
    repetitions: int = 200,
    bootstrap_draws: int = 99,
    rng_seed: int = 20260908,
) -> dict[str, object]:
    """T3 Monte Carlo calibration from raw EvaluationRunner receipts."""

    if repetitions < 200:
        raise ValueError("T3 calibration requires at least 200 Monte Carlo replications")

    rng = np.random.default_rng(rng_seed)
    scenarios: dict[str, object] = {}
    total_raw_receipts = 0
    total_raw_steps = 0
    for date_sd in (0.05, 0.03):
        scenario_name = f"date_sd_{date_sd:.2f}_seed_sd_0.01"
        scenarios[scenario_name] = {}
        for seed_count in (5, 12, 16, 24):
            conjunction_successes = 0
            covered = 0
            for repetition in range(repetitions):
                date_effect = rng.normal(0.0, date_sd, (3, 160))
                seed_effect = rng.normal(0.0, 0.01, (3, seed_count))
                receipts: list[dict[str, object]] = []
                for date_index in range(160):
                    for seed_index in range(seed_count):
                        for world in (0, 1):
                            energy = (0.75, 1.25)[world] * (
                                1.0 + 0.05 * ((date_index + seed_index) % 3)
                            )
                            endpoints = {"FULL": (100.0 * energy, energy)}
                            for contrast_index, arm in enumerate(DROP_ARMS):
                                log_effect = (
                                    math.log1p(0.02)
                                    + date_effect[contrast_index, date_index]
                                    + seed_effect[contrast_index, seed_index]
                                )
                                endpoints[arm] = (
                                    100.0 * energy / math.exp(log_effect),
                                    energy,
                                )
                            receipts.append(
                                EvaluationRunner.build_calibration_receipt(
                                    tle_date=f"D{date_index:03d}",
                                    learner_seed=1000 + seed_index,
                                    world_id=(
                                        f"{scenario_name}/r{repetition}/d{date_index}/"
                                        f"s{seed_index}/w{world}"
                                    ),
                                    arm_endpoints=endpoints,
                                )
                            )
                merged = merge_receipts(
                    receipts,
                    bootstrap_draws=bootstrap_draws,
                    bootstrap_seed=(
                        rng_seed
                        + int(date_sd * 1000) * 1_000_000
                        + seed_count * 10_000
                        + repetition
                    ),
                )
                total_raw_receipts += int(merged["raw_receipt_count"])
                total_raw_steps += int(merged["raw_step_count"])
                contrasts = merged["contrasts"]
                claim = merged["claim"]
                passed = tuple(
                    bool(claim["per_contrast"][arm]) for arm in DROP_ARMS
                )
                conjunction_successes += int(all(passed))
                for arm in DROP_ARMS:
                    interval = contrasts[arm]["bootstrap"][
                        "central_95_percentile_intervals"
                    ]["ee_relative"]
                    covered += int(
                        interval is not None and interval[0] <= 0.02 <= interval[1]
                    )
            scenarios[scenario_name][str(seed_count)] = {
                "interval_coverage": _binomial_uncertainty(covered, repetitions * 3),
                "conjunction_power": _binomial_uncertainty(
                    conjunction_successes, repetitions
                ),
            }

    return {
        "schema": "mcrl-v025-stagec-t3-calibration-v2",
        "repetitions": repetitions,
        "bootstrap_draws": bootstrap_draws,
        "date_count": 160,
        "seed_sd": 0.01,
        "planning_alternative_relative": 0.02,
        "claim_margin_relative": 0.005,
        "scenarios": scenarios,
        "seed_counts": [5, 12, 16, 24],
        "raw_path": {
            "emitter": "EvaluationRunner.build_calibration_receipt",
            "validator_and_merger": "merge_receipts",
            "reaggregation": "reaggregate_steps",
            "raw_receipts_processed": total_raw_receipts,
            "raw_steps_processed": total_raw_steps,
        },
        "simulation_uncertainty": (
            "Binomial Monte Carlo uncertainty is reported as an approximate normal 95% half-width; "
            "bootstrap Monte Carlo error is additionally limited by the declared draw count."
        ),
    }


__all__ = ["crossed_inference_calibration", "synthetic_crossed_clusters"]
