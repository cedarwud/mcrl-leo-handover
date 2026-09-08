"""Synthetic-only acceptance helpers for contract-v1 T1--T3."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np

from .learner import ARM_ORDER
from .merge import AdditiveTotals, DROP_ARMS, infer_cluster_totals


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
    repetitions: int = 48,
    bootstrap_draws: int = 149,
    rng_seed: int = 20260908,
) -> dict[str, object]:
    """T3 Monte Carlo calibration using the production two-way merger core."""

    rng = np.random.default_rng(rng_seed)
    scenario_coverage: dict[str, object] = {}
    # Coverage sensitivity required by G/T3.  The 12-seed declared design is
    # used here; these are calibrations, not measurements of real performance.
    for date_sd in (0.03, 0.05, 0.10):
        covered = 0
        trials = repetitions * 3
        for repetition in range(repetitions):
            clusters = synthetic_crossed_clusters(
                date_count=160,
                seed_count=12,
                date_sd=date_sd,
                seed_sd=0.01,
                true_relative_gain=(0.02, 0.02, 0.02),
                rng=rng,
            )
            contrasts, _claim = infer_cluster_totals(
                clusters,
                bootstrap_draws=bootstrap_draws,
                bootstrap_seed=rng_seed + 10000 * repetition + int(date_sd * 1000),
                include_supplementary=False,
            )
            for arm in DROP_ARMS:
                interval = contrasts[arm]["bootstrap"]["central_95_percentile_intervals"]["ee_relative"]
                if interval is not None and interval[0] <= 0.02 <= interval[1]:
                    covered += 1
        scenario_coverage[f"date_sd_{date_sd:.2f}_seed_sd_0.01"] = _binomial_uncertainty(
            covered, trials
        )

    power: dict[str, object] = {}
    for seed_count in (5, 12):
        conjunction_successes = 0
        component_successes = 0
        covered = 0
        for repetition in range(repetitions):
            clusters = synthetic_crossed_clusters(
                date_count=160,
                seed_count=seed_count,
                date_sd=0.05,
                seed_sd=0.01,
                true_relative_gain=(0.02, 0.02, 0.02),
                rng=rng,
            )
            contrasts, claim = infer_cluster_totals(
                clusters,
                bootstrap_draws=bootstrap_draws,
                bootstrap_seed=rng_seed + seed_count * 100000 + repetition,
                include_supplementary=False,
            )
            passed = tuple(bool(claim["per_contrast"][arm]) for arm in DROP_ARMS)
            component_successes += sum(passed)
            conjunction_successes += int(all(passed))
            for arm in DROP_ARMS:
                interval = contrasts[arm]["bootstrap"]["central_95_percentile_intervals"]["ee_relative"]
                covered += int(
                    interval is not None and interval[0] <= 0.02 <= interval[1]
                )
        power[str(seed_count)] = {
            "interval_coverage": _binomial_uncertainty(covered, repetitions * 3),
            "component_power": _binomial_uncertainty(component_successes, repetitions * 3),
            "conjunction_power": _binomial_uncertainty(conjunction_successes, repetitions),
        }

    # Least-favourable IUT null: the first component is exactly at +0.5%; the
    # others use the +2% planning alternative.
    false_conjunctions = 0
    for repetition in range(repetitions):
        clusters = synthetic_crossed_clusters(
            date_count=160,
            seed_count=12,
            date_sd=0.05,
            seed_sd=0.01,
            true_relative_gain=(0.005, 0.02, 0.02),
            rng=rng,
        )
        _contrasts, claim = infer_cluster_totals(
            clusters,
            bootstrap_draws=bootstrap_draws,
            bootstrap_seed=rng_seed + 900000 + repetition,
            include_supplementary=False,
        )
        false_conjunctions += int(claim["decision"] == "CLAIM_PASS")

    return {
        "schema": "mcrl-v025-stagec-t3-calibration-v1",
        "repetitions": repetitions,
        "bootstrap_draws": bootstrap_draws,
        "date_count": 160,
        "seed_sd": 0.01,
        "planning_alternative_relative": 0.02,
        "claim_margin_relative": 0.005,
        "coverage": scenario_coverage,
        "power_date_sd_0.05_seed_sd_0.01": power,
        "least_favourable_conjunction_null": _binomial_uncertainty(
            false_conjunctions, repetitions
        ),
        "simulation_uncertainty": (
            "Binomial Monte Carlo uncertainty is reported as an approximate normal 95% half-width; "
            "bootstrap Monte Carlo error is additionally limited by the declared draw count."
        ),
    }


__all__ = ["crossed_inference_calibration", "synthetic_crossed_clusters"]
