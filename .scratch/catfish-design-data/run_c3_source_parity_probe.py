#!/usr/bin/env python3
"""Emit a deterministic two-step Q1 receipt for one selected source tree.

The caller runs this once against the launched source snapshot and once against
the analysis checkout.  This probe does not call the post-training
``evaluate_actions`` seam, so equal receipts test the unchanged deployed path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026082801)
    parser.add_argument("--steps", type=int, default=2)
    return parser.parse_args()


ARGS = _arguments()
SOURCE_ROOT = ARGS.source_root.resolve()
REPO = ARGS.repo.resolve()
TLE_ROOT = ARGS.tle_root.resolve()
sys.path.insert(0, str(SOURCE_ROOT / "src"))

from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.action_contract import no_op_actions  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TRAIN,
    BlockAlternatingSplit,
    EpisodeStartSampler,
)
from mcrl.env.mobility import MobilityConfig  # noqa: E402
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver  # noqa: E402
from mcrl.env.step import StepEnvironment  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.trainer_env import TrainerEnvironment  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _evaluation_rngs,
    _trainer_config,
    assert_ephemeris_matches_record,
)


PREREG = REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
RUN_DIR = REPO / "artifacts/training-2026-08-25-rerun01/main"
USERS = 100


def _sha_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
    digest.update(array.tobytes())
    return digest.hexdigest()


def _candidate_sha(observation: object) -> str:
    digest = hashlib.sha256()
    for uid, table in enumerate(observation.candidates.slot_tables):
        digest.update(int(uid).to_bytes(4, "little", signed=False))
        for values in (table.norad_ids, table.cell_ids, table.mask):
            array = np.ascontiguousarray(values)
            digest.update(str(array.dtype).encode("ascii"))
            digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
            digest.update(array.tobytes())
    return digest.hexdigest()


def _masked_greedy(values: np.ndarray, masks: np.ndarray) -> np.ndarray:
    actions = no_op_actions(values.shape[0])
    for uid, mask in enumerate(masks):
        valid = np.flatnonzero(mask)
        if valid.size:
            actions[uid] = int(valid[np.argmax(values[uid, valid])])
    return actions


record = read_prereg(PREREG)
status = json.loads((RUN_DIR / "status.json").read_text(encoding="utf-8"))
checkpoint_path = RUN_DIR / "final-checkpoint.pt"
checkpoint = read_checkpoint(checkpoint_path, map_location="cpu")

with tempfile.TemporaryDirectory(prefix="mcrl-source-parity-") as temporary:
    frozen = Path(temporary) / "frozen-tle"
    frozen.mkdir()
    for row in record.sections["ephemeris"]["frozen_files"]:
        source = TLE_ROOT / str(row["file"])
        target = frozen / str(row["file"])
        try:
            os.link(source, target)
        except OSError:
            target.symlink_to(source)
    archive = TleArchive(frozen)
    assert_ephemeris_matches_record(record, archive=archive)

    def make_environment() -> TrainerEnvironment:
        driver = ScenarioDriver(
            archive,
            ScenarioConfig(mobility=MobilityConfig(num_users=USERS)),
        )
        split = BlockAlternatingSplit.for_archive(archive)
        sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
        return TrainerEnvironment(StepEnvironment(driver), sampler)

    trainer = MODQNTrainer(
        make_environment(),
        _trainer_config(record, learning_rate=float(status["learning_rate"])),
        train_seed=int(status["seeds"]["train"]),
        env_seed=int(status["seeds"]["environment"]),
        mobility_seed=int(status["seeds"]["mobility"]),
        device="cpu",
    )
    loaded = trainer.load_checkpoint(checkpoint_path, load_optimizers=False)
    if int(loaded["episode"]) != int(checkpoint.episode):
        raise RuntimeError("checkpoint load metadata mismatch")

    wrapped = make_environment()
    env_rng, mobility_rng, _action_rng, _perturb_rng = _evaluation_rngs(ARGS.seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    rows: list[dict[str, object]] = []
    for step in range(ARGS.steps):
        encoded = trainer.encode_states(states)
        mask_array = np.stack([item.mask for item in masks])
        q1 = trainer.scalarized_q_values(
            encoded, objective_weights=(1.0, 0.0, 0.0)
        )
        actions = _masked_greedy(q1, mask_array)
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        rows.append(
            {
                "step": step,
                "candidate_sha256": _candidate_sha(observation),
                "encoded_sha256": _sha_array(encoded),
                "q1_sha256": _sha_array(q1),
                "actions_sha256": _sha_array(actions),
                "served_sha256": _sha_array(outcome.resolution.served),
                "link_power_sha256": _sha_array(outcome.link_power_w),
                "link_rate_sha256": _sha_array(outcome.link_rate_bps),
                "reward_matrix_sha256": _sha_array(outcome.reward_matrix),
                "system_power_w": float(outcome.system_power_w),
                "system_throughput_bps": float(
                    outcome.energy.system_throughput_bps
                ),
                "system_ee_bits_per_j": float(outcome.energy.system_ee_bits_per_j),
                "active_beams": sorted(
                    [list(map(int, key)) for key in outcome.resolution.active_beams]
                ),
            }
        )
        states = result.user_states
        masks = result.action_masks
        observation = outcome.observation

print(
    json.dumps(
        {
            "schema": "mcrl-c3-source-parity-probe-v1",
            "seed": int(ARGS.seed),
            "users": USERS,
            "steps": int(ARGS.steps),
            "rows": rows,
        },
        sort_keys=True,
        allow_nan=False,
    )
)
