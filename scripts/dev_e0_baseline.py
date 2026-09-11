"""The frozen baseline MODQN eq-(16) checkpoint, rolled once on DEVVAL (development reference).

Controller directive 2026-09-11 22:15 UTC: the development champion has to be read against
the actual paper baseline, not only against the one-line rules.  This is a DEVELOPMENT
reference: greedy, no training, no optimiser, on the 24 DEVVAL episodes only -- never on the
formal evaluation, calibration or CONFIRM sets.

The checkpoint is the frozen main run's final checkpoint
(``artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt``, sha256 ``e6b063ef...c28b``),
112-dim observation, eq-(16) per-head max bootstrap, gamma 0.9, deployed rule
``argmax_legal sum_i omega_i Q_i`` with the frozen weights (0.5, 0.3, 0.2) -- exactly
``cf3_eval.build("modqn", ...)`` / ``cf3_common.modqn_greedy``.

Usage: dev_e0_baseline.py --out FILE [--checkpoint PATH] [--n 24]
"""

from __future__ import annotations

import argparse
import dataclasses
import time
from pathlib import Path

import cf3_common as C
import dev_e0_common as D

import torch

from mcrl.algorithms import cf_dev as cfd

EXPECTED_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
DEFAULT_CHECKPOINT = (
    "/home/sat/mcrl-v025-cf3-pilot-ws/tree/artifacts/training-2026-08-25-rerun01/"
    "main/final-checkpoint.pt"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, default=Path(DEFAULT_CHECKPOINT))
    ap.add_argument("--n", type=int, default=D.N_DEVVAL)
    ap.add_argument("--allow-other-checkpoint", action="store_true")
    a = ap.parse_args()
    torch.set_num_threads(1)
    tle = D.assert_environment()
    if a.out.is_file():
        print(f"[skip:exists] {a.out}")
        return 0
    digest = C.sha256_file(a.checkpoint)
    if digest != EXPECTED_CHECKPOINT_SHA256 and not a.allow_other_checkpoint:
        raise SystemExit(
            f"checkpoint {a.checkpoint} has sha256 {digest}, not the frozen baseline "
            f"{EXPECTED_CHECKPOINT_SHA256}"
        )

    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.artifacts import read_checkpoint
    from mcrl.runtime.trainer_spec import TrainerConfig

    raw = read_checkpoint(a.checkpoint, map_location="cpu")
    cfgd = dict(raw.trainer_config)
    for key in ("hidden_layers", "objective_weights", "reward_calibration_scales"):
        cfgd[key] = tuple(cfgd[key])
    cfg = TrainerConfig(**cfgd)
    factory = C.env_factory()
    trainer = MODQNTrainer(factory(), cfg, train_seed=raw.train_seed,
                           env_seed=raw.env_seed, mobility_seed=raw.mobility_seed)
    trainer.load_checkpoint(a.checkpoint, load_optimizers=False)
    policy = C.modqn_greedy(trainer)
    encode = lambda states, t: trainer._encode_states(states)  # noqa: E731

    seeds = D.devval_seeds(a.n)
    t0 = time.time()
    res = cfd.dev_rollout(lambda i: policy, env_factory=factory, encode=encode,
                          seeds=seeds, t0_agreement=True)
    res.update(
        label="BASELINE_MODQN_eq16", kind="development-reference",
        checkpoint=str(a.checkpoint), checkpoint_sha256=digest,
        episode=raw.episode, train_seed=raw.train_seed, env_seed=raw.env_seed,
        mobility_seed=raw.mobility_seed,
        trainer_config=dataclasses.asdict(cfg),
        objective_weights=list(cfg.objective_weights),
        td_bootstrap_mode=cfg.td_bootstrap_mode,
        set="DEVVAL", n_episodes=a.n, seeds=[list(x) for x in seeds],
        tle_file_set_sha256=tle, code=D.code_manifest(), wall_s=time.time() - t0,
        lane="E0-development reference (Amendment 6): not formal evidence",
    )
    C.write_json(a.out, res)
    print(f"BASELINE_MODQN_eq16 ee={res['ee']:.6e} served={res['served']:.5f} "
          f"beams={res['beams']:.3f} h_inter={res['h_inter']:.5f} "
          f"rate_p10={res['per_served_user_rate_p10_bps']:.4e} "
          f"agreeT0={res['t0_agreement']:.4f} wall={res['wall_s']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
