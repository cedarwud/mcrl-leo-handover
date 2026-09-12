"""The frozen 9000-episode MODQN eq-(16) checkpoint, rolled ONCE on the S1 formal
evaluation episodes (Amendment 13 section 2).

**No training, no optimizer.**  Greedy deployed rule on the same 24 formal evaluation
episodes ``9_111_000+i / 9_112_000+i`` every S1 cell is read on, under the same
estimand and through the same rollout function, so the published reference and the
trained cells are comparable.  The read runs with every Catfish source unregistered
and the judge disabled, exactly as the trained cells' reads do.

Amendment 13 section 2: this is the **published / frozen reference**, labelled
separately.  It is **not** a conjunctive S1 veto, because its training budget differs
from S1's; superiority over it may be claimed only if that comparison also succeeds.

Usage: s1_reference.py --out FILE [--checkpoint PATH] [--n 24]
"""

from __future__ import annotations

import argparse
import dataclasses
import time
from pathlib import Path

import cf3_common as C
import s1_common as S

import torch

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_s1 as cfs1

DEFAULT_CHECKPOINT = (
    "/home/sat/mcrl-v025-cf3-pilot-ws/tree/artifacts/training-2026-08-25-rerun01/"
    "main/final-checkpoint.pt"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, default=Path(DEFAULT_CHECKPOINT))
    ap.add_argument("--n", type=int, default=S.N_EVAL)
    a = ap.parse_args()
    torch.set_num_threads(1)
    tle = S.assert_environment()
    if a.out.is_file():
        print(f"[skip:exists] {a.out}")
        return 0
    digest = C.sha256_file(a.checkpoint)
    if digest != S.FROZEN_MODQN_SHA256:
        raise SystemExit(
            f"checkpoint {a.checkpoint} has sha256 {digest}, not the frozen published "
            f"reference {S.FROZEN_MODQN_SHA256}"
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

    seeds = S.eval_seeds(a.n)
    t0 = time.time()
    with cfs1.sources_unregistered(), cfs1.judge_disabled():
        res = cfd.dev_rollout(lambda i: policy, env_factory=factory,
                              encode=lambda states, t: trainer.encode_states(states),
                              seeds=seeds, t0_agreement=True, lane=S.S1_LANE)
    res.update(
        label=S.ROLLED_REFERENCE["label"], kind="published-reference",
        lane=S.S1_LANE, training="none (rolled once, no optimizer)",
        checkpoint=str(a.checkpoint), checkpoint_sha256=digest,
        episode=raw.episode, train_seed=raw.train_seed, env_seed=raw.env_seed,
        mobility_seed=raw.mobility_seed,
        trainer_config=dataclasses.asdict(cfg),
        objective_weights=list(cfg.objective_weights),
        td_bootstrap_mode=cfg.td_bootstrap_mode,
        set="S1-FORMAL-EVALUATION", n_episodes=a.n,
        eval_seeds=[list(x) for x in seeds],
        deployment="masked argmax; sources unregistered and judge disabled",
        tle_file_set_sha256=tle, code=S.code_manifest(), wall_s=time.time() - t0,
        note=S.ROLLED_REFERENCE["role"] + "; its training budget differs from S1's.",
    )
    C.write_json(a.out, res)
    print(f"FROZEN MODQN eq16 @9000 ee={res['ee']:.6e} served={res['served']:.5f} "
          f"rate_p10={res['per_served_user_rate_p10_bps']:.4e} "
          f"agreeT0={res['t0_agreement']:.4f} wall={res['wall_s']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
