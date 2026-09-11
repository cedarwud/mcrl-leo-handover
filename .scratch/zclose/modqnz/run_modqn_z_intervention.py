#!/usr/bin/env python3
"""Matched legacy-MODQN observation-transform intervention.

This file lives outside the legacy checkout.  It imports the exact corrected
legacy source tree read-only and changes only the matrix returned by the
trainer's state encoder.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import resource
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

LEGACY_ROOT = Path("/home/sat/mcrl-leo-handover-20260825-corrected")
MANDATED_PYTHON = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")
FROZEN_CHECKPOINT = Path(
    "/home/sat/mcrl-v025-retrain-ws/artifacts/"
    "training-2026-08-25-rerun01/main/final-checkpoint.pt"
)
FROZEN_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
LEGACY_CODE_SHA256 = (
    "544fcf078f7e0d74c38e79288081c60357bc64b59540120dbe4e30bffe014ec4"
)
THREAD_ENV = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)
ARMS = (
    "MODQN_RAW",
    "MODQN_Z_INPLACE",
    "MODQN_Z_CONCAT",
    "MODQN_RAW_DUP",
)
Z_EPS = 1e-6
TRAIN_SEED = 42
ENV_SEED = 1337
MOBILITY_SEED = 7
EVAL_SEEDS = tuple(2026082401 + index for index in range(10))
SOURCE_DIR = LEGACY_ROOT / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.env.constants import DECISION_STEP_S  # noqa: E402
from mcrl.runtime.q_network import DQNNetwork  # noqa: E402
from mcrl.runtime.replay_buffer import ReplayBuffer  # noqa: E402
from mcrl.runtime.state_encoding import encode_state  # noqa: E402
from mcrl.runtime.trainer_spec import EpisodeLog, TrainerConfig  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    make_training_environment,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    # Linux reports ru_maxrss in KiB.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def enforce_runtime_contract() -> dict[str, Any]:
    actual_python = Path(sys.executable).resolve()
    expected_python = MANDATED_PYTHON.resolve()
    if actual_python != expected_python:
        raise RuntimeError(f"wrong interpreter: {actual_python} != {expected_python}")
    thread_values = {name: os.environ.get(name) for name in THREAD_ENV}
    if any(value != "1" for value in thread_values.values()):
        raise RuntimeError(f"BLAS thread controls are not all 1: {thread_values}")
    nice_value = os.nice(0)
    if nice_value < 15:
        raise RuntimeError(f"nice value must be at least 15, got {nice_value}")
    checkpoint_sha = sha256_file(FROZEN_CHECKPOINT)
    if checkpoint_sha != FROZEN_CHECKPOINT_SHA256:
        raise RuntimeError(
            f"frozen checkpoint drifted: {checkpoint_sha} != {FROZEN_CHECKPOINT_SHA256}"
        )
    code_sha = _code_sha256(_default_code_paths())
    if code_sha != LEGACY_CODE_SHA256:
        raise RuntimeError(f"legacy source drifted: {code_sha} != {LEGACY_CODE_SHA256}")
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    return {
        "python": str(actual_python),
        "nice": nice_value,
        "thread_env": thread_values,
        "torch_num_threads": torch.get_num_threads(),
        "checkpoint_sha256_before": checkpoint_sha,
        "legacy_code_sha256": code_sha,
    }


def zscore_over_users(raw: np.ndarray, eps: float = Z_EPS) -> np.ndarray:
    """Sibling-compatible per-feature population z-score over axis 0."""
    value = np.asarray(raw, dtype=np.float64)
    if value.ndim != 2 or value.shape[0] < 1:
        raise ValueError(f"expected a non-empty (users, features) matrix, got {value.shape}")
    mean = value.mean(axis=0, dtype=np.float64)
    std = value.std(axis=0, dtype=np.float64, ddof=0)
    transformed = (value - mean) / (std + float(eps))
    result = transformed.astype(np.float32)
    if not np.isfinite(result).all():
        raise RuntimeError("z-score produced a non-finite value")
    return result


def transform_encoded(raw: np.ndarray, arm: str) -> np.ndarray:
    raw32 = np.asarray(raw, dtype=np.float32)
    if raw32.ndim != 2 or raw32.shape[1] != 112:
        raise ValueError(f"authentic raw state must be (U,112), got {raw32.shape}")
    if arm == "MODQN_RAW":
        result = raw32.copy()
    elif arm == "MODQN_Z_INPLACE":
        result = zscore_over_users(raw32)
    elif arm == "MODQN_Z_CONCAT":
        result = np.concatenate((raw32, zscore_over_users(raw32)), axis=1)
    elif arm == "MODQN_RAW_DUP":
        result = np.concatenate((raw32, raw32), axis=1)
    else:
        raise ValueError(f"unknown arm {arm!r}")
    return np.ascontiguousarray(result, dtype=np.float32)


def network_sha256(networks: nn.ModuleList) -> str:
    digest = hashlib.sha256()
    for network in networks:
        for name, tensor in network.state_dict().items():
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
            digest.update(b"\0")
    return digest.hexdigest()


class InterventionTrainer(MODQNTrainer):
    """Legacy trainer with one explicit, shape-checked observation transform."""

    def __init__(self, env, config: TrainerConfig, *, arm: str) -> None:
        if arm not in ARMS:
            raise ValueError(arm)
        self.arm = arm
        super().__init__(
            env,
            config,
            train_seed=TRAIN_SEED,
            env_seed=ENV_SEED,
            mobility_seed=MOBILITY_SEED,
            device="cpu",
        )
        wanted_dim = 224 if arm in {"MODQN_Z_CONCAT", "MODQN_RAW_DUP"} else 112
        if wanted_dim != self.state_dim:
            # Re-seed so the two width-224 arms have byte-identical initial
            # parameters.  The legacy initializer and all hidden/output widths
            # remain unchanged; only the admitted input width differs.
            torch.manual_seed(TRAIN_SEED)
            self.state_dim = wanted_dim
            self.q_nets = nn.ModuleList(
                [
                    DQNNetwork(
                        self.state_dim,
                        self.action_dim,
                        config.hidden_layers,
                        config.activation,
                    ).to(self.device)
                    for _ in range(3)
                ]
            )
            self.target_nets = nn.ModuleList(
                [__import__("copy").deepcopy(network).to(self.device) for network in self.q_nets]
            )
            for target in self.target_nets:
                target.eval()
            self.optimizers = [
                optim.Adam(network.parameters(), lr=config.learning_rate)
                for network in self.q_nets
            ]
            self.replay = ReplayBuffer(config.replay_capacity)
        self.initial_network_sha256 = network_sha256(self.q_nets)

    def _encode_states(self, states) -> np.ndarray:
        raw = np.array(
            [encode_state(state, self.num_users, self.config) for state in states],
            dtype=np.float32,
        )
        return transform_encoded(raw, self.arm)


def trainer_config(episodes: int) -> TrainerConfig:
    return TrainerConfig(
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        discount_factor=0.9,
        batch_size=128,
        episodes=int(episodes),
        objective_weights=(0.5, 0.3, 0.2),
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay_episodes=2000,
        target_update_every_episodes=50,
        replay_capacity=50_000,
        policy_sharing_mode="shared",
        snr_encoding="log1p",
        theta_encoding="raw_radians",
        offset_scale_km=100.0,
        load_normalization="divide_by_num_users",
        checkpoint_assumption_id="ASSUME-MODQN-REP-015",
        checkpoint_primary_report="final-episode-policy",
        checkpoint_secondary_report="best-weighted-reward-on-eval",
        training_experiment_kind="baseline",
        training_experiment_id="modqn-z-intervention-2026-09-10",
        method_family="MODQN-baseline",
        phase="baseline",
        comparison_role="observation-transform-intervention",
        r1_reward_label="system-energy-efficiency",
        r1_reward_provenance="paper eq. (3.25): r1 = sum_{s,v} x * eta",
        reward_calibration_enabled=True,
        reward_calibration_mode="divide-by-fixed-scales",
        reward_calibration_source="probe-P3-and-analytic-bound",
        reward_calibration_scales=(2029238.4328742754, 1.0, 6.0),
        reward_normalization_mode="raw-unscaled",
        load_balance_calibration_mode="baseline-paper-weight",
        device="cpu",
    )


def log_endpoint(logs: list[EpisodeLog], *, width: int = 100) -> dict[str, Any]:
    def summarise(rows: list[EpisodeLog]) -> dict[str, float]:
        return {
            "r1_mean": float(np.mean([row.r1_mean for row in rows])),
            "r2_mean": float(np.mean([row.r2_mean for row in rows])),
            "r3_mean": float(np.mean([row.r3_mean for row in rows])),
            "scalar_reward": float(np.mean([row.scalar_reward for row in rows])),
        }

    take = min(width, len(logs))
    return {
        "window_episodes": take,
        "first": summarise(logs[:take]),
        "last": summarise(logs[-take:]),
    }


def evaluate(trainer: InterventionTrainer) -> dict[str, Any]:
    pooled_bits = 0.0
    pooled_joules = 0.0
    served = 0
    assigned = 0
    modal_count = 0
    active_beams_total = 0
    active_satellites_total = 0
    argmax_distinct_total = 0
    occupancy_histogram: Counter[int] = Counter()
    scenario_rows: list[dict[str, Any]] = []
    total_steps = 0

    for scenario_index, seed in enumerate(EVAL_SEEDS, start=1):
        print(f"scenario {scenario_index}/{len(EVAL_SEEDS)} seed={seed}", flush=True)
        children = np.random.SeedSequence(seed).spawn(2)
        env_rng = np.random.default_rng(children[0])
        mobility_rng = np.random.default_rng(children[1])
        environment = make_training_environment(users=100)
        states, masks, observation = environment.reset(env_rng, mobility_rng)
        row_bits = row_joules = 0.0
        row_served = row_assigned = row_modal = 0
        row_active_beams = row_active_satellites = row_argmax_distinct = 0
        row_steps = 0

        while True:
            encoded = trainer.encode_states(states)
            actions = trainer.select_actions(
                encoded, masks, eps=0.0, raw_states=states
            )
            action_values = [int(value) for value in actions if int(value) != NO_OP_ACTION]
            row_argmax_distinct += len(set(action_values))

            selected_keys: list[tuple[int, int]] = []
            for uid, action in enumerate(actions.tolist()):
                if int(action) == NO_OP_ACTION:
                    continue
                table = observation.candidates.slot_tables[uid]
                selected_keys.append(
                    (int(table.norad_ids[int(action)]), int(table.cell_ids[int(action)]))
                )
            selected_counts = Counter(selected_keys)
            row_assigned += len(selected_keys)
            row_modal += max(selected_counts.values(), default=0)
            occupancy_histogram.update(selected_counts.values())

            result = environment.step(actions, env_rng)
            outcome = environment.last_outcome
            step_bits = outcome.energy.system_throughput_bps * DECISION_STEP_S
            step_joules = outcome.energy.system_consumed_power_w * DECISION_STEP_S
            row_bits += float(step_bits)
            row_joules += float(step_joules)
            row_served += outcome.resolution.served_count
            active_keys = outcome.resolution.active_beams
            row_active_beams += len(active_keys)
            row_active_satellites += len({key[0] for key in active_keys})
            row_steps += 1

            if result.done:
                break
            states = result.user_states
            masks = result.action_masks
            observation = outcome.observation

        pooled_bits += row_bits
        pooled_joules += row_joules
        served += row_served
        assigned += row_assigned
        modal_count += row_modal
        active_beams_total += row_active_beams
        active_satellites_total += row_active_satellites
        argmax_distinct_total += row_argmax_distinct
        total_steps += row_steps
        scenario_rows.append(
            {
                "scenario_index": scenario_index,
                "seed": seed,
                "steps": row_steps,
                "bits": row_bits,
                "joules": row_joules,
                "ee_bits_per_j": row_bits / row_joules,
                "served": row_served,
                "assigned": row_assigned,
                "modal_frac": row_modal / row_assigned,
                "mean_active_beams": row_active_beams / row_steps,
                "mean_active_satellites": row_active_satellites / row_steps,
                "mean_argmax_distinct": row_argmax_distinct / row_steps,
            }
        )

    tail = [
        {"occupancy": occupancy, "beam_steps": count}
        for occupancy, count in sorted(occupancy_histogram.items())
        if occupancy >= 5
    ]
    return {
        "split": "TRAIN/development",
        "evaluation_seeds": list(EVAL_SEEDS),
        "scenarios": len(EVAL_SEEDS),
        "steps": total_steps,
        "user_steps": total_steps * trainer.num_users,
        "pooled_bits": pooled_bits,
        "pooled_joules": pooled_joules,
        "pooled_ee_bits_per_j": pooled_bits / pooled_joules,
        "served": served,
        "served_fraction": served / (total_steps * trainer.num_users),
        "assigned": assigned,
        "modal_count_sum": modal_count,
        "modal_frac": modal_count / assigned,
        "mean_active_beams": active_beams_total / total_steps,
        "mean_active_satellites": active_satellites_total / total_steps,
        "mean_argmax_distinct": argmax_distinct_total / total_steps,
        "occupancy_histogram": {
            str(key): value for key, value in sorted(occupancy_histogram.items())
        },
        "occupancy_histogram_tail_ge_5": tail,
        "scenario_rows": scenario_rows,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def save_resume_bundle(
    path: Path,
    *,
    trainer: InterventionTrainer,
    logs: list[EpisodeLog],
    arm: str,
    episodes: int,
) -> None:
    """Atomically persist the exact episode-boundary continuation state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "format_version": 1,
            "arm": arm,
            "episodes": episodes,
            "logs": list(logs),
            "trainer_state": trainer.training_state_dict(),
        },
        temporary,
    )
    temporary.replace(path)


def run(arm: str, episodes: int, output_dir: Path, *, evaluate_final: bool) -> dict[str, Any]:
    runtime = enforce_runtime_contract()
    started = time.monotonic()
    environment = make_training_environment(users=100)
    environment.assert_ready_to_train()
    config = trainer_config(episodes)
    trainer = InterventionTrainer(environment, config, arm=arm)
    logs: list[EpisodeLog] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "result.json"
    if result_path.exists():
        raise FileExistsError(f"refusing to overwrite completed result {result_path}")
    resume_path = output_dir / "resume-state.pt"
    start_episode = 0
    if resume_path.exists():
        bundle = torch.load(resume_path, map_location="cpu", weights_only=False)
        if not isinstance(bundle, dict) or bundle.get("format_version") != 1:
            raise ValueError("invalid resume bundle")
        if bundle.get("arm") != arm or bundle.get("episodes") != episodes:
            raise ValueError("resume bundle belongs to a different arm/protocol")
        prior_logs = bundle.get("logs")
        if not isinstance(prior_logs, list) or not all(
            isinstance(item, EpisodeLog) for item in prior_logs
        ):
            raise TypeError("resume bundle logs are invalid")
        trainer.load_training_state_dict(bundle.get("trainer_state"))
        logs.extend(prior_logs)
        start_episode = len(logs)
        print(
            f"resume arm={arm} episode={start_episode}/{episodes} "
            f"peak_rss_bytes={peak_rss_bytes()}",
            flush=True,
        )

    def observe(log: EpisodeLog) -> None:
        logs.append(log)
        completed = log.episode + 1
        if completed % 100 == 0 or completed == episodes:
            elapsed = time.monotonic() - started
            print(
                f"episode {completed}/{episodes} arm={arm} elapsed_s={elapsed:.3f} "
                f"peak_rss_bytes={peak_rss_bytes()}",
                flush=True,
            )
            write_json(
                output_dir / "progress.json",
                {
                    "arm": arm,
                    "episodes_completed": completed,
                    "elapsed_seconds": elapsed,
                    "peak_rss_bytes": peak_rss_bytes(),
                    "last_log": dataclasses.asdict(log),
                },
            )
            save_resume_bundle(
                resume_path,
                trainer=trainer,
                logs=logs,
                arm=arm,
                episodes=episodes,
            )

    returned = trainer.train(
        progress_every=0,
        start_episode=start_episode,
        initial_logs=logs,
        episode_callback=observe,
    )
    if returned != logs or len(logs) != episodes:
        raise RuntimeError("training log callback disagreed with trainer return")
    checkpoint = output_dir / f"{arm.lower()}-final-checkpoint.pt"
    if checkpoint.exists():
        raise FileExistsError(f"refusing to overwrite {checkpoint}")
    trainer.save_checkpoint(
        checkpoint,
        episode=episodes - 1,
        checkpoint_kind="final-episode-policy",
        logs=logs,
    )
    evaluation = evaluate(trainer) if evaluate_final else None
    elapsed = time.monotonic() - started
    checkpoint_after = sha256_file(FROZEN_CHECKPOINT)
    if checkpoint_after != FROZEN_CHECKPOINT_SHA256:
        raise RuntimeError("frozen checkpoint changed during run")
    payload = {
        "arm": arm,
        "episodes": episodes,
        "state_dim": trainer.state_dim,
        "action_dim": trainer.action_dim,
        "online_parameter_count": sum(
            parameter.numel() for network in trainer.q_nets for parameter in network.parameters()
        ),
        "initial_network_sha256": trainer.initial_network_sha256,
        "final_network_sha256": network_sha256(trainer.q_nets),
        "new_checkpoint": str(checkpoint),
        "new_checkpoint_sha256": sha256_file(checkpoint),
        "frozen_checkpoint_sha256_after": checkpoint_after,
        "elapsed_seconds": elapsed,
        "seconds_per_100_episodes": elapsed * 100.0 / episodes,
        "peak_rss_bytes": peak_rss_bytes(),
        "runtime": runtime,
        "transform": {
            "zscore_user_axis": 0,
            "zscore_ddof": 0,
            "zscore_eps": Z_EPS,
            "zscore_accumulation_dtype": "float64",
            "network_dtype": "float32",
            "raw_block_order": [
                "access_vector[0:28]",
                "log1p(channel_quality)[28:56]",
                "beam_offsets_raw_radians[56:84]",
                "beam_loads_divide_by_num_users[84:112]",
            ],
        },
        "learning_curve_endpoints": log_endpoint(logs),
        "evaluation": evaluation,
    }
    write_json(result_path, payload)
    print(f"peak RSS: {peak_rss_bytes()} bytes ({peak_rss_bytes() / 2**20:.2f} MiB)", flush=True)
    print(f"result: {output_dir / 'result.json'}", flush=True)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--episodes", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evaluate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.episodes < 1:
        raise ValueError("episodes must be positive")
    run(args.arm, args.episodes, args.output_dir, evaluate_final=args.evaluate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
