"""Validate and analyse the corrected R2 P6/main artifact set.

This command never trains or updates a checkpoint.  Its default mode checks
the frozen provenance and derives the pre-result collapse criterion plus
reward diagnostics from the complete episode logs.  ``--replay`` additionally
loads the final checkpoints and performs a deterministic, greedy, train-split
evaluation replay to recover the physical G-8 quantities that EpisodeLog does
not retain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.action_contract import HANDOVER_COST, no_op_actions  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
)
from mcrl.env.mobility import MobilityConfig  # noqa: E402
from mcrl.env.reference_policy import (  # noqa: E402
    REFERENCE_POLICY_NAMES,
    build_reference_policy,
)
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver  # noqa: E402
from mcrl.env.step import StepEnvironment  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.collapse_metrics import compute_collapse_metrics  # noqa: E402
from mcrl.runtime.objective_math import (  # noqa: E402
    apply_reward_calibration,
    scalarize_objectives,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.probe_p6 import (  # noqa: E402
    MAIN_ENV_SEED,
    MAIN_MOBILITY_SEED,
    MAIN_TRAIN_SEED,
    P6_ENV_SEED,
    P6_EVALUATION_SEEDS,
    P6_LEARNING_RATES,
    P6_MOBILITY_SEED,
    P6_TRAIN_SEED,
    choose_learning_rate,
)
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG_BYTE_SHA256,
    CANONICAL_PREREG_RECORD_DIGEST,
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
    _installed_dependency_versions,
    _json_sha256,
    _trainer_config,
    assert_ephemeris_matches_record,
)


DEFAULT_INPUT = REPO / "artifacts" / "training-2026-08-25-rerun01"
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
RUN_DIRS: tuple[tuple[str, str], ...] = (
    ("p6-lr-0.01", "0.01"),
    ("p6-lr-0.003", "0.003"),
    ("p6-lr-0.001", "0.001"),
    ("main", "main"),
)
COLLAPSE_FIELDS = (
    "active_beam_count",
    "argmax_agreement",
    "q_margin",
    "q_entropy",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_finite(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, list):
        return all(_all_finite(item) for item in value)
    if isinstance(value, dict):
        return all(_all_finite(item) for item in value.values())
    return False


def _mean(values: Iterable[float]) -> float:
    materialised = [float(value) for value in values]
    return float(statistics.fmean(materialised)) if materialised else 0.0


def _distribution(values: Iterable[float]) -> dict[str, float]:
    data = np.asarray(list(values), dtype=np.float64)
    if data.size == 0:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": float(np.mean(data)),
        "p50": float(np.quantile(data, 0.50)),
        "p95": float(np.quantile(data, 0.95)),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
    }


def _load_and_verify_runs(
    input_dir: Path,
    record: Any,
    *,
    analysis_source_drift_reason: str | None = None,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    dict[str, Any],
]:
    pipeline = _read_json(input_dir / "pipeline-status.json")
    if pipeline.get("status") != "complete" or pipeline.get("phase") != "complete":
        raise RuntimeError("pipeline-status.json is not complete")
    if pipeline.get("prereg_digest") != CANONICAL_PREREG_RECORD_DIGEST:
        raise RuntimeError("pipeline prereg digest is not the canonical R2 digest")

    statuses: dict[str, dict[str, Any]] = {}
    logs_by_run: dict[str, list[dict[str, Any]]] = {}
    launched_code_sha = None
    recorded_dependencies: dict[str, str] | None = None
    expected_frozen_seed_sets = {
        "p6_matched": {
            "train": P6_TRAIN_SEED,
            "environment": P6_ENV_SEED,
            "mobility": P6_MOBILITY_SEED,
        },
        "p6_evaluation": list(P6_EVALUATION_SEEDS),
        "main": {
            "train": MAIN_TRAIN_SEED,
            "environment": MAIN_ENV_SEED,
            "mobility": MAIN_MOBILITY_SEED,
        },
    }
    for dirname, label in RUN_DIRS:
        run_dir = input_dir / dirname
        status = _read_json(run_dir / "status.json")
        logs = _read_json(run_dir / "episode-logs.json")
        if status.get("status") != "complete":
            raise RuntimeError(f"{label}: status is not complete")
        if status.get("episodes_completed") != 9000:
            raise RuntimeError(f"{label}: expected 9000 completed episodes")
        if not isinstance(logs, list) or len(logs) != 9000:
            raise RuntimeError(f"{label}: episode log does not contain 9000 rows")
        if any(row.get("episode") != index for index, row in enumerate(logs)):
            raise RuntimeError(f"{label}: episode sequence is not contiguous")
        if not _all_finite(logs):
            raise RuntimeError(f"{label}: episode log contains non-finite data")
        for row in logs:
            for point in ("collapse_first", "collapse_last"):
                sample = row.get(point)
                if not isinstance(sample, dict) or any(
                    field not in sample for field in COLLAPSE_FIELDS
                ):
                    raise RuntimeError(f"{label}: incomplete {point} collapse sample")

        log_path = run_dir / "episode-logs.json"
        if _sha256(log_path) != status.get("episode_logs_sha256"):
            raise RuntimeError(f"{label}: episode-log SHA-256 mismatch")
        checkpoint_path = run_dir / "final-checkpoint.pt"
        if not checkpoint_path.is_file():
            raise RuntimeError(f"{label}: local final checkpoint is missing")
        if _sha256(checkpoint_path) != status.get("checkpoint_sha256"):
            raise RuntimeError(f"{label}: final-checkpoint SHA-256 mismatch")

        fingerprint = status.get("run_fingerprint", {})
        expected_learning_rate = 0.001 if label == "main" else float(label)
        if label == "main":
            expected_role = "main-training"
            expected_seeds = {
                "train": MAIN_TRAIN_SEED,
                "environment": MAIN_ENV_SEED,
                "mobility": MAIN_MOBILITY_SEED,
            }
        else:
            expected_role = "P6-learning-rate-arm"
            expected_seeds = {
                "train": P6_TRAIN_SEED,
                "environment": P6_ENV_SEED,
                "mobility": P6_MOBILITY_SEED,
            }
        expected_run = {
            "role": expected_role,
            "learning_rate": expected_learning_rate,
            "train_seed": expected_seeds["train"],
            "environment_seed": expected_seeds["environment"],
            "mobility_seed": expected_seeds["mobility"],
        }
        if (
            status.get("role") != expected_role
            or float(status.get("learning_rate")) != expected_learning_rate
            or status.get("seeds") != expected_seeds
            or fingerprint.get("run") != expected_run
        ):
            raise RuntimeError(f"{label}: role, learning rate, or seeds drifted")
        code_sha = fingerprint.get("code_sha256")
        if not isinstance(code_sha, str):
            raise RuntimeError(f"{label}: missing launched code SHA-256")
        launched_code_sha = launched_code_sha or code_sha
        if code_sha != launched_code_sha:
            raise RuntimeError("run statuses disagree on launched source SHA-256")
        if fingerprint.get("prereg_digest") != CANONICAL_PREREG_RECORD_DIGEST:
            raise RuntimeError(f"{label}: run fingerprint has wrong prereg digest")
        if (
            fingerprint.get("ephemeris_file_set_sha256")
            != record.sections["ephemeris"]["file_set_sha256"]
        ):
            raise RuntimeError(f"{label}: fingerprint has wrong TLE file-set hash")
        if fingerprint.get("frozen_seed_sets") != expected_frozen_seed_sets:
            raise RuntimeError(f"{label}: fingerprint has wrong frozen seed sets")
        expected_config = _trainer_config(
            record, learning_rate=expected_learning_rate
        )
        expected_config_sha = _json_sha256(asdict(expected_config))
        if fingerprint.get("trainer_config_sha256") != expected_config_sha:
            raise RuntimeError(f"{label}: trainer-config fingerprint mismatch")
        if fingerprint.get("reward_calibration_scales") != list(
            expected_config.reward_calibration_scales
        ):
            raise RuntimeError(f"{label}: reward calibration scales drifted")
        fingerprint_hashable = dict(fingerprint)
        fingerprint_digest = fingerprint_hashable.pop("fingerprint_sha256", None)
        if fingerprint_digest != _json_sha256(fingerprint_hashable):
            raise RuntimeError(f"{label}: run fingerprint self-hash mismatch")
        dependencies = fingerprint.get("dependencies")
        if not isinstance(dependencies, dict):
            raise RuntimeError(f"{label}: recorded training dependencies are missing")
        recorded_dependencies = recorded_dependencies or dict(dependencies)
        if dependencies != recorded_dependencies:
            raise RuntimeError(f"{label}: recorded training dependencies disagree")

        checkpoint = read_checkpoint(checkpoint_path, map_location="cpu")
        if (
            checkpoint.episode != 8999
            or checkpoint.train_seed != expected_seeds["train"]
            or checkpoint.env_seed != expected_seeds["environment"]
            or checkpoint.mobility_seed != expected_seeds["mobility"]
            or float(checkpoint.trainer_config["learning_rate"])
            != expected_learning_rate
            or _json_sha256(checkpoint.trainer_config) != expected_config_sha
        ):
            raise RuntimeError(f"{label}: checkpoint provenance metadata mismatch")
        if label != "main":
            if status.get("evaluation_seeds") != list(P6_EVALUATION_SEEDS):
                raise RuntimeError(f"{label}: P6 evaluation seed set drifted")
            for key in (
                "calibrated_scalar_reward_by_seed",
                "greedy",
                "random_near_tie",
                "paired_control_deltas",
            ):
                rows = status.get(key)
                if not isinstance(rows, list) or len(rows) != len(
                    P6_EVALUATION_SEEDS
                ):
                    raise RuntimeError(f"{label}: incomplete P6 {key} rows")
        statuses[label] = status
        logs_by_run[label] = logs

    current_code_sha = _code_sha256(_default_code_paths())
    source_matches_launched = current_code_sha == launched_code_sha
    if not source_matches_launched and not analysis_source_drift_reason:
        raise RuntimeError(
            "current analysis source differs from launched training source: "
            f"{current_code_sha} != {launched_code_sha}; provide an explicit "
            "--analysis-source-drift-reason only for a post-run diagnostic replay"
        )
    analysis_dependencies = _installed_dependency_versions()
    assert recorded_dependencies is not None
    return statuses, logs_by_run, {
        "pipeline_status": "complete",
        "pipeline_phase": "complete",
        "pipeline_finished_utc": pipeline.get("finished_utc"),
        "selected_learning_rate": float(pipeline["selected_learning_rate"]),
        "prereg_digest": pipeline["prereg_digest"],
        "launched_code_sha256": launched_code_sha,
        "current_code_sha256": current_code_sha,
        "current_source_matches_launched": source_matches_launched,
        "analysis_source_drift_reason": analysis_source_drift_reason,
        "runs_complete": 4,
        "episodes_total": 36000,
        "episode_log_hashes_match": True,
        "final_checkpoint_hashes_match": True,
        "run_fingerprint_self_hashes_match": True,
        "roles_learning_rates_and_seeds_match": True,
        "trainer_config_hashes_match": True,
        "checkpoint_provenance_metadata_match": True,
        "p6_evaluation_rows_complete": True,
        "recorded_training_dependencies": recorded_dependencies,
        "analysis_dependencies": analysis_dependencies,
        "analysis_dependencies_match_training": (
            analysis_dependencies == recorded_dependencies
        ),
    }


def _collapse_movement(value: float, null: float, field: str) -> float:
    saturation = {
        "active_beam_count": 1.0,
        "argmax_agreement": 1.0,
        "q_margin": 1.0,
        "q_entropy": 0.0,
    }[field]
    denominator = saturation - null
    if denominator == 0.0:
        raise ZeroDivisionError(f"{field} null is already at saturation")
    return float((value - null) / denominator)


def _collapse_report(logs: list[dict[str, Any]]) -> dict[str, Any]:
    null = {field: float(logs[0]["collapse_first"][field]) for field in COLLAPSE_FIELDS}
    executed_random_proxy = {
        "active_beam_count": float(
            logs[0]["collapse_first"]["active_beam_count_executed"]
        ),
        "argmax_agreement": float(
            logs[0]["collapse_first"]["argmax_agreement_executed"]
        ),
    }
    tail = logs[-1000:]
    movements: dict[str, float | None] = {}
    raw_tail_medians: dict[str, float] = {}
    unreadable_exact_saturation: list[str] = []
    for field in COLLAPSE_FIELDS:
        raw = [float(row["collapse_first"][field]) for row in tail]
        raw_tail_medians[field] = float(np.median(raw))
        try:
            movement = [
                _collapse_movement(value, null[field], field) for value in raw
            ]
            movements[field] = float(np.median(movement))
        except ZeroDivisionError:
            movements[field] = None
            unreadable_exact_saturation.append(field)

    numeric_verdict = "unreadable"
    if not unreadable_exact_saturation:
        numeric = {key: float(value) for key, value in movements.items()}
        action_050 = (
            numeric["active_beam_count"] >= 0.50
            and numeric["argmax_agreement"] >= 0.50
        )
        q_050 = numeric["q_margin"] >= 0.50 and numeric["q_entropy"] >= 0.50
        if action_050 and q_050:
            numeric_verdict = "necessary"
        elif all(value < 0.20 for value in numeric.values()):
            numeric_verdict = "unnecessary"
        else:
            numeric_verdict = "uncertain"

    return {
        "criterion_window": "last-1000 collapse_first median movement",
        "null_episode": 0,
        "null_greedy": null,
        "episode0_executed_random_proxy": executed_random_proxy,
        "null_minus_executed_proxy": {
            key: null[key] - executed_random_proxy[key]
            for key in executed_random_proxy
        },
        "tail_raw_median": raw_tail_medians,
        "tail_median_movement": movements,
        "numeric_verdict_if_null_is_readable": numeric_verdict,
        "exact_saturation_denominator_failures": unreadable_exact_saturation,
        "final_verdict_requires_null_readability": True,
        "near_saturation_threshold_was_frozen": False,
    }


def _window_diagnostics(
    logs: list[dict[str, Any]], weights: Sequence[float]
) -> dict[str, Any]:
    raw = np.asarray(
        [[row[f"r{index}_mean"] for index in (1, 2, 3)] for row in logs],
        dtype=np.float64,
    )
    calibrated = np.asarray(
        [
            [row[f"r{index}_mean_calibrated"] for index in (1, 2, 3)]
            for row in logs
        ],
        dtype=np.float64,
    )
    weight_array = np.asarray(weights, dtype=np.float64)
    contribution = weight_array * np.mean(np.abs(calibrated), axis=0)
    shares = contribution / contribution.sum()
    # Each r1_mean is sum over the episode's ten steps and 100 users, divided
    # by 100 users.  Multiplying by U / T = 10 recovers that episode's mean
    # per-step system EE.  Physical replay is still required for G-8 context.
    derived_episode_mean_ee = raw[:, 0] * 10.0
    return {
        "episodes": len(logs),
        "signed_raw_means": [float(value) for value in np.mean(raw, axis=0)],
        "signed_calibrated_means": [
            float(value) for value in np.mean(calibrated, axis=0)
        ],
        "magnitude_contributions": [float(value) for value in contribution],
        "magnitude_shares": [float(value) for value in shares],
        "derived_episode_mean_system_ee_bits_per_j": _distribution(
            derived_episode_mean_ee
        ),
        "total_handovers_per_episode": _distribution(
            float(row["total_handovers"]) for row in logs
        ),
        "weighted_handover_penalty_per_episode": _distribution(-100.0 * raw[:, 1]),
        "r3_load_penalty_per_user_episode": _distribution(-raw[:, 2]),
    }


def _reward_reports(
    logs_by_run: Mapping[str, list[dict[str, Any]]], weights: Sequence[float]
) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for label, logs in logs_by_run.items():
        reports[label] = {
            "all_9000": _window_diagnostics(logs, weights),
            "tail_1000": _window_diagnostics(logs[-1000:], weights),
            "tail_100": _window_diagnostics(logs[-100:], weights),
        }
    return reports


def _kendall_w(score_rows: np.ndarray) -> float:
    judges, items = score_rows.shape
    ranks = np.empty_like(score_rows, dtype=np.float64)
    for row_index, row in enumerate(score_rows):
        order = np.argsort(row)
        ranks[row_index, order] = np.arange(1, items + 1, dtype=np.float64)
    rank_sums = np.sum(ranks, axis=0)
    centered = rank_sums - judges * (items + 1) / 2.0
    numerator = 12.0 * float(np.sum(centered**2))
    denominator = float(judges**2 * (items**3 - items))
    return numerator / denominator


def _p6_report(statuses: Mapping[str, dict[str, Any]], selected: float) -> dict[str, Any]:
    arms = {float(label): statuses[label] for label in ("0.01", "0.003", "0.001")}
    chosen, selection = choose_learning_rate(arms)
    if chosen != selected:
        raise RuntimeError(f"frozen selector reproduced {chosen}, pipeline says {selected}")

    ordered_lrs = (0.01, 0.003, 0.001)
    score_rows = np.asarray(
        [arms[lr]["calibrated_scalar_reward_by_seed"] for lr in ordered_lrs],
        dtype=np.float64,
    ).T
    target_order = [0.001, 0.003, 0.01]
    observed_orders = [
        [ordered_lrs[index] for index in np.argsort(row)[::-1]]
        for row in score_rows
    ]
    arms_report: dict[str, Any] = {}
    for learning_rate in ordered_lrs:
        status = arms[learning_rate]
        scores = [float(value) for value in status["calibrated_scalar_reward_by_seed"]]
        deltas = status["paired_control_deltas"]
        arms_report[str(learning_rate)] = {
            "mean_calibrated_scalar_reward": _mean(scores),
            "sample_sd_calibrated_scalar_reward": float(statistics.stdev(scores)),
            "near_tie_fraction_mean": _mean(
                row["near_tie_fraction"] for row in status["greedy"]
            ),
            "random_control_intervention_fraction_mean": _mean(
                row["intervention_fraction"] for row in status["random_near_tie"]
            ),
            "random_minus_greedy_system_ee_mean": _mean(
                row["delta_system_ee_random_minus_greedy"] for row in deltas
            ),
            "random_minus_greedy_calibrated_scalar_mean": _mean(
                row["delta_calibrated_scalar_random_minus_greedy"] for row in deltas
            ),
            "perturbation_greedy_action_retention": status[
                "perturbation_greedy_action_retention"
            ],
            "perturbation_kendall_tau": status["perturbation_kendall_tau"],
        }
    return {
        "selected_learning_rate": chosen,
        "selection_receipt": selection,
        "arms": arms_report,
        "selected_beats_0.003_seeds": int(
            np.count_nonzero(score_rows[:, 2] > score_rows[:, 1])
        ),
        "selected_beats_0.01_seeds": int(
            np.count_nonzero(score_rows[:, 2] > score_rows[:, 0])
        ),
        "modal_target_order_fraction": float(
            sum(order == target_order for order in observed_orders) / len(observed_orders)
        ),
        "kendall_w": _kendall_w(score_rows),
    }


def _make_environment(archive: TleArchive, *, users: int = 100) -> TrainerEnvironment:
    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=users)),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def _frozen_archive(record: Any, source_root: Path, temporary_root: Path) -> TleArchive:
    rows = record.sections["ephemeris"]["frozen_files"]
    temporary_root.mkdir(parents=True, exist_ok=False)
    for row in rows:
        source = source_root / str(row["file"])
        target = temporary_root / str(row["file"])
        if not source.is_file():
            raise RuntimeError(f"frozen TLE source file is missing: {source}")
        try:
            os.link(source, target)
        except OSError:
            target.symlink_to(source)
    archive = TleArchive(temporary_root)
    assert_ephemeris_matches_record(record, archive=archive)
    return archive


def _load_trainer(
    record: Any,
    archive: TleArchive,
    status: Mapping[str, Any],
    checkpoint_path: Path,
) -> MODQNTrainer:
    environment = _make_environment(archive)
    seeds = status["seeds"]
    trainer = MODQNTrainer(
        environment,
        _trainer_config(record, learning_rate=float(status["learning_rate"])),
        train_seed=int(seeds["train"]),
        env_seed=int(seeds["environment"]),
        mobility_seed=int(seeds["mobility"]),
        device="cpu",
    )
    loaded = trainer.load_checkpoint(checkpoint_path, load_optimizers=False)
    if loaded["episode"] != 8999:
        raise RuntimeError(f"checkpoint is episode {loaded['episode']}, expected 8999")
    return trainer


def _compare_float(expected: float, observed: float) -> tuple[bool, float]:
    difference = abs(float(expected) - float(observed))
    return difference == 0.0, difference


def _physical_step_row(
    outcome: Any,
    *,
    evaluation_seed: int,
    previous_served: np.ndarray | None,
    num_users: int,
) -> tuple[dict[str, Any], np.ndarray]:
    reward_matrix = outcome.reward_matrix
    if not math.isclose(
        float(np.sum(reward_matrix[:, 0])),
        outcome.energy.system_ee_bits_per_j,
        rel_tol=1e-12,
    ):
        raise RuntimeError("replay lost the additive system-EE identity")
    if not np.array_equal(
        reward_matrix[:, 2], -outcome.resolution.user_beam_load()
    ):
        raise RuntimeError("replay r3 differs from physical eligible load")
    expected_r2 = np.asarray(
        [-HANDOVER_COST[item] for item in outcome.handovers], dtype=np.float64
    )
    if not np.array_equal(reward_matrix[:, 1], expected_r2):
        raise RuntimeError("replay r2 differs from identity handover class")

    current_served = outcome.resolution.served.copy()
    reentries = 0
    if previous_served is not None:
        reentries = int(np.count_nonzero((~previous_served) & current_served))
    handovers = Counter(item.value for item in outcome.handovers)
    loads = np.asarray(
        list(outcome.resolution.eligible_load_by_beam.values()),
        dtype=np.float64,
    )
    served = outcome.energy.served
    return (
        {
            "evaluation_seed": int(evaluation_seed),
            "step_index": int(outcome.step_index),
            "system_ee_bits_per_j": float(outcome.energy.system_ee_bits_per_j),
            "served": int(served),
            "service_fraction": float(served / num_users),
            "eff_beams": int(outcome.energy.eff_beams),
            "system_throughput_bps": float(outcome.energy.system_throughput_bps),
            "system_power_w": float(outcome.energy.system_consumed_power_w),
            "no_op_users": int(np.count_nonzero(outcome.resolution.no_op_users)),
            "outage_infeasible": int(
                np.count_nonzero(outcome.resolution.outage_infeasible)
            ),
            "physical_beam_max_load": float(np.max(loads)) if loads.size else 0.0,
            "physical_beam_mean_load": float(np.mean(loads)) if loads.size else 0.0,
            "physical_beam_max_share": (
                float(np.max(loads) / served) if loads.size and served else 0.0
            ),
            "handover_none": int(handovers.get("none", 0)),
            "handover_phi1": int(handovers.get("phi1", 0)),
            "handover_phi2": int(handovers.get("phi2", 0)),
            "phi2_reentry": int(reentries),
            "phi2_served_to_served": int(handovers.get("phi2", 0) - reentries),
            "zero_over_zero": bool(outcome.energy.zero_over_zero),
        },
        current_served,
    )


def _greedy_replay(
    trainer: MODQNTrainer,
    archive: TleArchive,
    *,
    evaluation_seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    environment = _make_environment(archive)
    env_rng, mobility_rng, _action_rng, _perturb_rng = _evaluation_rngs(
        evaluation_seed
    )
    states, masks, _observation = environment.reset(env_rng, mobility_rng)
    encoded = trainer.encode_states(states)
    raw_reward = np.zeros(3, dtype=np.float64)
    calibrated_reward = np.zeros(3, dtype=np.float64)
    decisions = 0
    steps: list[dict[str, Any]] = []
    collapse_first: dict[str, Any] | None = None
    collapse_last: dict[str, Any] | None = None
    previous_served: np.ndarray | None = None

    while True:
        scalarized = trainer.scalarized_q_values(encoded)
        actions = no_op_actions(environment.num_users)
        for uid, wrapped_mask in enumerate(masks):
            valid = np.flatnonzero(wrapped_mask.mask)
            if valid.size == 0:
                continue
            decisions += 1
            actions[uid] = int(valid[np.argmax(scalarized[uid, valid])])

        mask_block = np.stack([wrapped.mask for wrapped in masks])
        collapse_metrics = compute_collapse_metrics(
            scalarized,
            mask_block,
            actions,
        )
        collapse_sample: dict[str, Any] = collapse_metrics.as_dict() | {
            "active_action_slot_count": (
                collapse_metrics.active_action_slot_count
            ),
            "active_beam_count_semantics": "distinct_relative_action_slots",
            "q_margin_aggregation": "mean_of_per_user_normalised_margins",
        }

        result = environment.step(actions, env_rng)
        outcome = environment.last_outcome
        for uid in range(environment.num_users):
            vector = np.asarray(
                trainer.reward_vector_from_step_result(result, uid, is_eval=True),
                dtype=np.float64,
            )
            raw_reward += vector
            calibrated_reward += apply_reward_calibration(vector, trainer.config)

        physical_row, current_served = _physical_step_row(
            outcome,
            evaluation_seed=evaluation_seed,
            previous_served=previous_served,
            num_users=environment.num_users,
        )
        collapse_sample |= {
            "physical_effective_beams": physical_row["eff_beams"],
            "physical_beam_max_share": physical_row["physical_beam_max_share"],
        }
        if collapse_first is None:
            collapse_first = dict(collapse_sample)
        collapse_last = dict(collapse_sample)
        steps.append(physical_row)
        previous_served = current_served
        if result.done:
            break
        states = result.user_states
        masks = result.action_masks
        encoded = trainer.encode_states(states)

    raw_mean = raw_reward / environment.num_users
    calibrated_mean = calibrated_reward / environment.num_users
    if collapse_first is None or collapse_last is None:
        raise RuntimeError("checkpoint replay produced no collapse samples")
    replay_row = {
        "evaluation_seed": int(evaluation_seed),
        "objective_reward_mean_raw": [float(value) for value in raw_mean],
        "objective_reward_mean_calibrated": [
            float(value) for value in calibrated_mean
        ],
        "scalar_reward_raw": float(
            scalarize_objectives(raw_mean, trainer.config.objective_weights)
        ),
        "scalar_reward_calibrated": float(
            scalarize_objectives(calibrated_mean, trainer.config.objective_weights)
        ),
        "system_ee_reward_r1": float(raw_mean[0]),
        "decisions": int(decisions),
        "collapse_first": collapse_first,
        "collapse_last": collapse_last,
    }
    return replay_row, steps


def _reference_replay(
    trainer: MODQNTrainer,
    archive: TleArchive,
    *,
    evaluation_seed: int,
    policy_name: str,
    declaration_seed: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    environment = _make_environment(archive)
    env_rng, mobility_rng, action_rng, _perturb_rng = _evaluation_rngs(
        evaluation_seed
    )
    _states, _masks, observation = environment.reset(env_rng, mobility_rng)
    policy = build_reference_policy(policy_name, declaration_seed)
    policy.reset()
    raw_reward = np.zeros(3, dtype=np.float64)
    steps: list[dict[str, Any]] = []
    previous_served: np.ndarray | None = None

    while True:
        actions = policy.act(observation.candidates, action_rng)
        result = environment.step(actions, env_rng)
        outcome = environment.last_outcome
        raw_reward += np.sum(outcome.reward_matrix, axis=0)
        physical_row, current_served = _physical_step_row(
            outcome,
            evaluation_seed=evaluation_seed,
            previous_served=previous_served,
            num_users=environment.num_users,
        )
        steps.append(physical_row)
        previous_served = current_served
        if result.done:
            break
        observation = outcome.observation

    raw_mean = raw_reward / environment.num_users
    calibrated_mean = apply_reward_calibration(raw_mean, trainer.config)
    return (
        {
            "evaluation_seed": int(evaluation_seed),
            "policy": policy_name,
            "objective_reward_mean_raw": [float(value) for value in raw_mean],
            "objective_reward_mean_calibrated": [
                float(value) for value in calibrated_mean
            ],
            "scalar_reward_calibrated": float(
                scalarize_objectives(
                    calibrated_mean, trainer.config.objective_weights
                )
            ),
        },
        steps,
    )


def _replay_summary(steps: list[dict[str, Any]]) -> dict[str, Any]:
    total_user_decisions = len(steps) * 100
    return {
        "steps": len(steps),
        "user_decisions": total_user_decisions,
        "system_ee_bits_per_j": _distribution(
            row["system_ee_bits_per_j"] for row in steps
        ),
        "served_users": _distribution(row["served"] for row in steps),
        "service_fraction": _distribution(row["service_fraction"] for row in steps),
        "effective_physical_beams": _distribution(row["eff_beams"] for row in steps),
        "system_throughput_bps": _distribution(
            row["system_throughput_bps"] for row in steps
        ),
        "system_power_w": _distribution(row["system_power_w"] for row in steps),
        "physical_beam_max_load": _distribution(
            row["physical_beam_max_load"] for row in steps
        ),
        "physical_beam_mean_load": _distribution(
            row["physical_beam_mean_load"] for row in steps
        ),
        "physical_beam_max_share": _distribution(
            row["physical_beam_max_share"] for row in steps
        ),
        "handover_counts": {
            key: int(sum(row[key] for row in steps))
            for key in (
                "handover_none",
                "handover_phi1",
                "handover_phi2",
                "phi2_reentry",
                "phi2_served_to_served",
            )
        },
        "no_op_fraction": float(
            sum(row["no_op_users"] for row in steps) / total_user_decisions
        ),
        "outage_infeasible_fraction": float(
            sum(row["outage_infeasible"] for row in steps) / total_user_decisions
        ),
        "zero_over_zero_steps": int(sum(row["zero_over_zero"] for row in steps)),
    }


def _checkpoint_collapse_summary(
    replay_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Describe repaired final-checkpoint metrics across evaluation seeds.

    This is deliberately not the frozen episode-0-to-tail-1000 criterion:
    the old logs did not retain per-user Q margins, so that historical series
    cannot be repaired from aggregates.  The checkpoint replay is a new,
    prospective diagnostic over the fixed ten evaluation seeds.
    """
    fields = (
        "active_action_slot_count",
        "argmax_agreement",
        "q_margin",
        "q_entropy",
        "physical_effective_beams",
        "physical_beam_max_share",
    )
    summary: dict[str, Any] = {
        "scope": "post-run final-checkpoint diagnostic",
        "formal_frozen_tail_criterion_reconstructed": False,
        "q_margin_aggregation": "mean_of_per_user_normalised_margins",
        "action_metric_semantics": "distinct_relative_action_slots",
        "physical_beam_metrics_reported_separately": True,
        "evaluation_seed_count": len(replay_rows),
    }
    for point in ("collapse_first", "collapse_last"):
        summary[point] = {
            field: _distribution(row[point][field] for row in replay_rows)
            for field in fields
        }
    return summary


def _paired_seed_ee_summary(
    main_rows: Sequence[Mapping[str, Any]],
    reference_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare episode-mean system EE at the frozen evaluation-seed level.

    An evaluation episode has ten steps and 100 users.  The stored raw r1
    mean is the sum of the ten step-level system-EE values divided by 100, so
    multiplying it by ten recovers the episode's mean step-level system EE.
    Treating the ten frozen seeds as the comparison units avoids pretending
    that the 100 temporally nested replay steps are independent replicates.
    """
    main_by_seed = {
        int(row["evaluation_seed"]): float(row["objective_reward_mean_raw"][0])
        * 10.0
        for row in main_rows
    }
    reference_by_seed = {
        int(row["evaluation_seed"]): float(row["objective_reward_mean_raw"][0])
        * 10.0
        for row in reference_rows
    }
    if main_by_seed.keys() != reference_by_seed.keys():
        raise RuntimeError("main and reference replay seed sets differ")
    seeds = sorted(main_by_seed)
    differences = [
        main_by_seed[seed] - reference_by_seed[seed] for seed in seeds
    ]
    ratios = [main_by_seed[seed] / reference_by_seed[seed] for seed in seeds]
    return {
        "estimand": "paired evaluation-seed episode-mean system EE",
        "seed_pairs": len(seeds),
        "main_better_seed_pairs": int(sum(value > 0.0 for value in differences)),
        "main_minus_reference_bits_per_j": _distribution(differences),
        "main_to_reference_ratio": _distribution(ratios),
        "main_minus_reference_sample_sd_bits_per_j": float(
            statistics.stdev(differences)
        ),
    }


def _run_replay(
    record: Any,
    input_dir: Path,
    statuses: Mapping[str, dict[str, Any]],
    source_tle_root: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="mcrl-r2-tle-") as temporary:
        archive = _frozen_archive(record, source_tle_root, Path(temporary) / "tle")
        reports: dict[str, Any] = {}
        for dirname, label in RUN_DIRS:
            trainer = _load_trainer(
                record,
                archive,
                statuses[label],
                input_dir / dirname / "final-checkpoint.pt",
            )
            replay_rows: list[dict[str, Any]] = []
            physical_steps: list[dict[str, Any]] = []
            exact_matches: list[bool] = []
            max_differences: list[float] = []
            stored_rows = {
                int(row["evaluation_seed"]): row
                for row in statuses[label].get("greedy", [])
            }
            for seed in P6_EVALUATION_SEEDS:
                replay_row, steps = _greedy_replay(
                    trainer, archive, evaluation_seed=seed
                )
                replay_rows.append(replay_row)
                physical_steps.extend(steps)
                if stored_rows:
                    stored = stored_rows[int(seed)]
                    comparisons: list[tuple[bool, float]] = []
                    for key in (
                        "scalar_reward_raw",
                        "scalar_reward_calibrated",
                        "system_ee_reward_r1",
                    ):
                        comparisons.append(_compare_float(stored[key], replay_row[key]))
                    for key in (
                        "objective_reward_mean_raw",
                        "objective_reward_mean_calibrated",
                    ):
                        comparisons.extend(
                            _compare_float(expected, observed)
                            for expected, observed in zip(
                                stored[key], replay_row[key], strict=True
                            )
                        )
                    comparisons.append(
                        (stored["decisions"] == replay_row["decisions"], 0.0)
                    )
                    exact_matches.append(all(item[0] for item in comparisons))
                    max_differences.append(max(item[1] for item in comparisons))
            if stored_rows and not all(exact_matches):
                raise RuntimeError(
                    f"{label}: deterministic P6 greedy replay did not exactly match "
                    f"stored evaluation (max diff {max(max_differences)})"
                )
            reports[label] = {
                "stored_p6_greedy_replay_exact": (
                    all(exact_matches) if stored_rows else None
                ),
                "stored_p6_greedy_replay_max_abs_diff": (
                    max(max_differences) if max_differences else None
                ),
                "evaluation_seeds": list(P6_EVALUATION_SEEDS),
                "split": "train",
                "physical": _replay_summary(physical_steps),
                "checkpoint_collapse_repaired": _checkpoint_collapse_summary(
                    replay_rows
                ),
                "greedy_rows": replay_rows,
            }

        main_trainer = _load_trainer(
            record,
            archive,
            statuses["main"],
            input_dir / "main" / "final-checkpoint.pt",
        )
        declaration_seed = int(record.sections["reference_policy"]["seed"])
        references: dict[str, Any] = {}
        for policy_name in REFERENCE_POLICY_NAMES:
            policy_rows: list[dict[str, Any]] = []
            physical_steps: list[dict[str, Any]] = []
            for seed in P6_EVALUATION_SEEDS:
                policy_row, steps = _reference_replay(
                    main_trainer,
                    archive,
                    evaluation_seed=seed,
                    policy_name=policy_name,
                    declaration_seed=declaration_seed,
                )
                policy_rows.append(policy_row)
                physical_steps.extend(steps)
            references[policy_name] = {
                "declaration_seed": declaration_seed,
                "evaluation_seeds": list(P6_EVALUATION_SEEDS),
                "split": "train",
                "physical": _replay_summary(physical_steps),
                "rows": policy_rows,
            }

        main_physical = reports["main"]["physical"]
        comparisons: dict[str, Any] = {}
        for policy_name, reference in references.items():
            reference_physical = reference["physical"]
            main_ee = main_physical["system_ee_bits_per_j"]["mean"]
            reference_ee = reference_physical["system_ee_bits_per_j"]["mean"]
            comparisons[policy_name] = {
                "main_to_reference_ee_ratio": float(main_ee / reference_ee),
                "main_minus_reference_ee_bits_per_j": float(main_ee - reference_ee),
                "main_minus_reference_service_fraction": float(
                    main_physical["service_fraction"]["mean"]
                    - reference_physical["service_fraction"]["mean"]
                ),
                "main_minus_reference_throughput_bps": float(
                    main_physical["system_throughput_bps"]["mean"]
                    - reference_physical["system_throughput_bps"]["mean"]
                ),
                "main_minus_reference_power_w": float(
                    main_physical["system_power_w"]["mean"]
                    - reference_physical["system_power_w"]["mean"]
                ),
                "paired_seed_ee": _paired_seed_ee_summary(
                    reports["main"]["greedy_rows"], reference["rows"]
                ),
            }
        return {
            "determinism_scope": "final-checkpoint greedy evaluation replay only",
            "full_training_reproduced": False,
            "frozen_tle_file_count": len(record.sections["ephemeris"]["frozen_files"]),
            "runs": reports,
            "matched_reference_policies": references,
            "main_vs_matched_references": comparisons,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--replay",
        action="store_true",
        help="load final checkpoints and recover physical G-8 quantities",
    )
    parser.add_argument(
        "--source-tle-root",
        type=Path,
        help="live superset containing every file named by the frozen manifest",
    )
    parser.add_argument(
        "--analysis-source-drift-reason",
        help=(
            "explicit audit reason permitting a post-run diagnostic source "
            "to differ from the immutable launched training fingerprint"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = read_prereg(args.prereg)
    record.verify()
    if record.digest != CANONICAL_PREREG_RECORD_DIGEST:
        raise RuntimeError("analysis prereg is not canonical corrected R2")
    if _sha256(args.prereg) != CANONICAL_PREREG_BYTE_SHA256:
        raise RuntimeError("analysis prereg byte SHA-256 mismatch")

    statuses, logs_by_run, integrity = _load_and_verify_runs(
        args.input_dir,
        record,
        analysis_source_drift_reason=args.analysis_source_drift_reason,
    )
    weights = tuple(float(value) for value in record.sections["training"]["objective_weights"])
    report: dict[str, Any] = {
        "schema": "mcrl-corrected-postrun-analysis-v2",
        "verification_status": "ANALYZED",
        "analysis_provenance": {
            "script": "scripts/analyze_corrected_postrun.py",
            "script_sha256": _sha256(Path(__file__)),
            "input_dir": str(args.input_dir),
            "prereg": str(args.prereg),
            "replay_requested": bool(args.replay),
            "analysis_source_drift_reason": args.analysis_source_drift_reason,
        },
        "integrity": integrity,
        "p6": _p6_report(statuses, integrity["selected_learning_rate"]),
        "collapse": {
            label: _collapse_report(logs) for label, logs in logs_by_run.items()
        },
        "reward_diagnostics": _reward_reports(logs_by_run, weights),
        "claim_limits": [
            "collapse numeric branch is conditional on the criterion's qualitative null-readability precondition",
            "reward magnitude shares are not causal objective effects",
            "P6 and replay use the train split, not held-out generalisation data",
            "matched reference-policy replay is a post-run descriptive comparison, not a preregistered causal ablation",
            "full 15-hour training reproducibility is not established by checkpoint replay",
            "the repaired per-user q_margin cannot reconstruct the old tail-1000 series because per-user rows were not logged",
            "checkpoint collapse rows are post-run diagnostics and do not replace the frozen formal criterion",
        ],
    }
    if args.replay:
        source_root = args.source_tle_root
        if source_root is None:
            source_root = Path(record.sections["ephemeris"]["config"]["tle_root"])
        report["replay"] = _run_replay(
            record,
            args.input_dir,
            statuses,
            source_root.expanduser(),
        )
        report["verification_status"] = (
            "ANALYZED_WITH_EXACT_EVALUATION_REPLAY_AND_POSTRUN_METRIC_REPAIR"
        )

    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(rendered + "\n", encoding="utf-8")
        temporary.replace(args.output)
        print(
            "corrected post-run analysis PASS: "
            f"status={report['verification_status']} output={args.output}"
        )
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
