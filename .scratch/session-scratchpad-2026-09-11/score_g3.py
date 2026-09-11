#!/usr/bin/env python3
"""Compute the four G-3 collapse indicators on existing MODQN-family checkpoints.

Read-only.  No training, no new artefacts written into any protected tree.
Rollout uses the frozen P6 development seeds, TRAIN split, greedy (eps=0),
exactly as `measure_modqn_collapse.py` did, so the numbers are comparable to
MODQN-COLLAPSE-2026-09-10.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
import torch

LEGACY_ROOT = Path("/home/sat/mcrl-leo-handover-20260825-corrected")
SRC = LEGACY_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FROZEN = LEGACY_ROOT / "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"
FROZEN_SHA = "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
MQZ = Path("/home/sat/mcrl-v025-mqz-ws/artifacts")

OUT = Path(sys.argv[1])

torch.set_num_threads(1)
try:
    torch.set_num_interop_threads(1)
except RuntimeError:
    pass

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.env.action_contract import NO_OP_ACTION  # noqa: E402
from mcrl.runtime import probe_p6  # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402
from mcrl.runtime.training_pipeline import make_training_environment  # noqa: E402


def sha256(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            d.update(block)
    return d.hexdigest()


def peak_rss() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


# ---------------------------------------------------------------------------
# The two normalisation aggregations, computed side by side.
#   CURRENT  = /home/u24/.../src/mcrl/runtime/collapse_metrics.py (mean of
#              per-user ratios; the definition the mandate names)
#   LEGACY   = the 2026-08-25 frozen tree's form (ratio of the two means)
# Everything else in the two files is identical.
# ---------------------------------------------------------------------------
def four_indicators(q: np.ndarray, valid: np.ndarray, actions: np.ndarray) -> dict:
    q = np.asarray(q, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool)
    actions = np.asarray(actions, dtype=np.int64)
    num_users, num_actions = q.shape
    served = actions >= 0

    active_beam_count = float(np.unique(actions[served]).size) if served.any() else 0.0
    if served.any():
        counts = np.bincount(actions[served], minlength=num_actions)
        argmax_agreement = float(counts.max()) / float(np.count_nonzero(served))
    else:
        argmax_agreement = 0.0

    margins_raw, ranges, margins_norm, entropies = [], [], [], []
    for uid in range(num_users):
        row_mask = valid[uid]
        if int(np.count_nonzero(row_mask)) < 2:
            continue
        row = q[uid][row_mask]
        ordered = np.sort(row)[::-1]
        m_raw = float(ordered[0] - ordered[1])
        rng = float(ordered[0] - ordered[-1])
        margins_raw.append(m_raw)
        ranges.append(rng)
        margins_norm.append(m_raw / rng if rng > 0.0 else 0.0)
        shifted = row - row.max()
        w = np.exp(shifted)
        w /= w.sum()
        pos = w[w > 0.0]
        entropies.append(float(-(pos * np.log(pos)).sum()) / float(np.log(row.size)))

    q_margin_raw = float(np.mean(margins_raw)) if margins_raw else 0.0
    q_range = float(np.mean(ranges)) if ranges else 0.0
    return {
        "active_beam_count": active_beam_count,
        "argmax_agreement": argmax_agreement,
        "q_margin": float(np.mean(margins_norm)) if margins_norm else 0.0,
        "q_margin_legacy_ratio_of_means": (
            q_margin_raw / q_range if q_range > 0.0 else 0.0
        ),
        "q_entropy": float(np.mean(entropies)) if entropies else 0.0,
        "q_margin_raw": q_margin_raw,
        "q_range": q_range,
        "users_with_ge2_candidates": len(margins_raw),
        "num_users": num_users,
        "num_actions": num_actions,
    }


def zscore_over_users(raw: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    v = np.asarray(raw, dtype=np.float64)
    mean = v.mean(axis=0, dtype=np.float64)
    std = v.std(axis=0, dtype=np.float64, ddof=0)
    return ((v - mean) / (std + float(eps))).astype(np.float32)


def trainer_config(episodes: int = 9000) -> TrainerConfig:
    return TrainerConfig(
        hidden_layers=(100, 50, 50),
        activation="tanh",
        learning_rate=0.001,
        discount_factor=0.9,
        batch_size=128,
        episodes=episodes,
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
        training_experiment_id="g3-indicator-readout-2026-09-11",
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


class Scorer(MODQNTrainer):
    def __init__(self, env, config, *, transform: str) -> None:
        self.transform = transform
        super().__init__(
            env, config, train_seed=42, env_seed=1337, mobility_seed=7, device="cpu"
        )

    def _encode_states(self, states):
        from mcrl.runtime.state_encoding import encode_state

        raw = np.array(
            [encode_state(s, self.num_users, self.config) for s in states],
            dtype=np.float32,
        )
        if self.transform == "raw":
            return np.ascontiguousarray(raw, dtype=np.float32)
        if self.transform == "z_inplace":
            return np.ascontiguousarray(zscore_over_users(raw), dtype=np.float32)
        raise ValueError(self.transform)


def rollout(label: str, checkpoint: Path | None, transform: str, seeds, steps=10, users=100):
    env = make_training_environment(users=users)
    cfg = trainer_config()
    trainer = Scorer(env, cfg, transform=transform)
    if checkpoint is not None:
        trainer.load_checkpoint(checkpoint, load_optimizers=False)
    for net in trainer.q_nets:
        net.eval()

    rows = []
    for scenario_index, seed in enumerate(seeds, start=1):
        environment = make_training_environment(users=users)
        children = np.random.SeedSequence(seed).spawn(2)
        env_rng = np.random.default_rng(children[0])
        mob_rng = np.random.default_rng(children[1])
        states, masks, _obs = environment.reset(env_rng, mob_rng)
        for step_index in range(steps):
            encoded = trainer.encode_states(states)
            scalarized = trainer._scalarize_q_values(
                trainer._predict_objective_q_values(encoded), cfg.objective_weights
            )
            mask_block = np.stack([m.mask for m in masks])
            greedy = trainer._select_unconstrained_actions(scalarized, masks, 0.0)
            row = four_indicators(scalarized, mask_block, greedy)
            row.update(
                {
                    "scenario_index": scenario_index,
                    "seed": int(seed),
                    "step_index": step_index,
                    "no_op_users": int(np.count_nonzero(greedy == NO_OP_ACTION)),
                }
            )
            rows.append(row)
            result = environment.step(greedy, env_rng)
            if bool(result.done) != (step_index == steps - 1):
                raise RuntimeError("episode length drifted")
            if result.done:
                break
            states = list(result.user_states)
            masks = list(result.action_masks)
        print(
            f"  {label}: scenario {scenario_index}/{len(seeds)} rss={peak_rss()}",
            file=sys.stderr,
            flush=True,
        )
    return rows


FIELDS = (
    "active_beam_count",
    "argmax_agreement",
    "q_margin",
    "q_entropy",
    "q_margin_legacy_ratio_of_means",
    "q_margin_raw",
    "q_range",
    "no_op_users",
)


def summarise(rows):
    def group(sub):
        out = {}
        for f in FIELDS:
            v = np.asarray([r[f] for r in sub], dtype=np.float64)
            out[f] = {
                "mean": float(v.mean()),
                "min": float(v.min()),
                "max": float(v.max()),
            }
        out["n_profiles"] = len(sub)
        return out

    first = [r for r in rows if r["step_index"] == 0]
    last = [r for r in rows if r["step_index"] == 9]
    return {
        "pooled_all_steps": group(rows),
        "step_first": group(first),
        "step_last": group(last),
        "drift_last_minus_first": {
            f: group(last)[f]["mean"] - group(first)[f]["mean"] for f in FIELDS
        },
    }


def main() -> int:
    started = time.monotonic()
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    ):
        if os.environ.get(name) != "1":
            raise RuntimeError(f"{name} must be 1")

    pre = sha256(FROZEN)
    if pre != FROZEN_SHA:
        raise RuntimeError(f"frozen checkpoint drifted: {pre}")

    seeds = tuple(int(s) for s in probe_p6.P6_EVALUATION_SEEDS)
    assert len(seeds) == 10, seeds

    targets = [
        ("FROZEN_MODQN", FROZEN, "raw"),
        ("UNTRAINED_INIT_SEED42", None, "raw"),
        ("MODQNZ_MODQN_RAW", MQZ / "MODQN_RAW/modqn_raw-final-checkpoint.pt", "raw"),
        (
            "MODQNZ_MODQN_Z_INPLACE",
            MQZ / "MODQN_Z_INPLACE/modqn_z_inplace-final-checkpoint.pt",
            "z_inplace",
        ),
    ]

    results = {}
    for label, ckpt, transform in targets:
        if ckpt is not None and not ckpt.exists():
            results[label] = {"error": f"missing checkpoint {ckpt}"}
            continue
        print(f"== {label}", file=sys.stderr, flush=True)
        rows = rollout(label, ckpt, transform, seeds)
        results[label] = {
            "checkpoint": str(ckpt) if ckpt else None,
            "checkpoint_sha256": sha256(ckpt) if ckpt else None,
            "observation_transform": transform,
            "summary": summarise(rows),
            "rows": rows,
        }

    post = sha256(FROZEN)
    if post != pre:
        raise RuntimeError("frozen checkpoint changed during scoring")

    payload = {
        "schema": "g3-four-indicator-readout-v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "legacy_root": str(LEGACY_ROOT),
        "frozen_checkpoint_sha256_before": pre,
        "frozen_checkpoint_sha256_after": post,
        "split": "TRAIN/development",
        "seeds": list(seeds),
        "users": 100,
        "steps_per_scenario": 10,
        "selection": "greedy masked argmax, eps=0, lowest-index tie-break",
        "objective_weights": [0.5, 0.3, 0.2],
        "q_margin_definitions": {
            "q_margin": "mean over users of (top1-top2)/(top1-min) -- current "
            "src/mcrl/runtime/collapse_metrics.py:190-207",
            "q_margin_legacy_ratio_of_means": "mean(top1-top2)/mean(top1-min) -- "
            "the 2026-08-25 frozen tree's form",
        },
        "elapsed_seconds": time.monotonic() - started,
        "peak_rss_bytes": peak_rss(),
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT}  peak_rss={peak_rss()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
