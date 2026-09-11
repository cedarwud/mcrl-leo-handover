"""Scalarized-objective myopic demonstrator arms on the MODQN harness.

READ-ONLY / NO TRAINING: `update()` is never called, no gradient step, no
optimizer touched.  MODQNTrainer is used only for its env-reset / encode /
reward-vector plumbing so every statistic is the trainer's own EpisodeLog
quantity and is directly comparable with
artifacts/training-2026-08-25-rerun01/main/episode-logs.json.

Myopic predictions, all from the 112-dim observation at decision time only:
  r1_hat_raw(u,a) = (B / (load[u,a] + 1)) * log2(1 + sinr[u,a])      [bit/s]
      -- eq. (3.14) R = (B^w / U) log2(1+gamma), link_budget.py:596,
         with sinr from state block 2 and load from state block 4 (t-1).
      Divided by an unobservable global P^N, so it carries ONE free positive
      constant kappa; kappa is swept over a declared grid.
  r2_hat(u,a)     = 0 if a == incumbent slot;  -PHI1 if same satellite slot;
                    -PHI2 otherwise.  Incumbent slot from state block 1;
                    satellite slot = a // 7 (action_contract.py:14).
                    If block 1 is all-zero the incumbent left the candidate
                    table -> -PHI2 for every action (constant, so it does not
                    affect the argmax for that user).
  r3_hat(u,a)     = -(load[u,a] + 1)   -- count form, step_types.py:178-180.

Score, in the trainer's own calibrated units
(objective_weights (0.5,0.3,0.2); reward_calibration_scales (2029238.43,1,6)):
  s(u,a) = 0.5*kappa*r1_hat_raw + 0.3*r2_hat + 0.2*r3_hat/6
"""
import sys
import time

sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, NUM_BEAM_SLOTS, PHI1, PHI2, no_op_actions
from mcrl.env.link_budget import BEAM_BANDWIDTH_HZ
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

W = (0.5, 0.3, 0.2)
SC = (2029238.4328742754, 1.0, 6.0)
B = float(BEAM_BANDWIDTH_HZ)
# trained checkpoint's realised calibrated r1 per user-step (last 100 episodes,
# 4.4049 per episode / 10 steps) -- the anchor for kappa*
TARGET_R1C_PER_STEP = 0.44049

cfg = TrainerConfig(learning_rate=0.001, episodes=1)
env = make_training_environment(users=100)
U = env.config.num_users
T = env.config.steps_per_episode


def fresh():
    return MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)


def preds(states):
    """(r1_hat_raw, r2_hat, r3_hat) arrays, shape (U, 28), observation-only."""
    n = len(states)
    r1 = np.zeros((n, 28))
    r2 = np.zeros((n, 28))
    r3 = np.zeros((n, 28))
    for u, s in enumerate(states):
        load = np.asarray(s.beam_loads, dtype=np.float64)
        sinr = np.maximum(np.asarray(s.channel_quality, dtype=np.float64), 0.0)
        r1[u] = (B / (load + 1.0)) * np.log2(1.0 + sinr)
        r3[u] = -(load + 1.0)
        inc = np.flatnonzero(np.asarray(s.access_vector) > 0.5)
        if inc.size == 0:
            r2[u] = -PHI2
        else:
            i = int(inc[0])
            lsat = i // NUM_BEAM_SLOTS
            row = np.full(28, -PHI2)
            row[lsat * NUM_BEAM_SLOTS:(lsat + 1) * NUM_BEAM_SLOTS] = -PHI1
            row[i] = 0.0
            r2[u] = row
    return r1, r2, r3


def argmax_masked(score, masks):
    out = no_op_actions(len(masks))
    for u in range(len(masks)):
        v = np.where(masks[u].mask)[0]
        out[u] = int(v[int(np.argmax(score[u][v]))]) if v.size else NO_OP_ACTION
    return out


def make_scalar_arm(kappa, use_r2=True, use_r3=True):
    def pick(tr, encoded, masks, states):
        r1, r2, r3 = preds(states)
        s = W[0] * kappa * r1
        if use_r2:
            s = s + W[1] * (r2 / SC[1])
        if use_r3:
            s = s + W[2] * (r3 / SC[2])
        return argmax_masked(s, masks)
    return pick


def arm_random(tr, encoded, masks, states):
    return tr.select_actions(encoded, masks, 1.0)


def arm_maxgain(tr, encoded, masks, states):
    return argmax_masked([s.channel_quality for s in states], masks)


def run(fn, n_ep):
    tr = fresh()
    r = np.zeros(3)
    ho = ho1 = ho2 = 0
    steps = 0
    for _ in range(n_ep):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        for _t in range(T):
            a = fn(tr, enc, masks, states)
            res = env.step(a, tr._env_rng)
            for uid in range(U):
