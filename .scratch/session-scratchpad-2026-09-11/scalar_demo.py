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
                r += tr.reward_vector_from_step_result(res, uid)
                v = res.rewards[uid].r2_handover
                steps += 1
                if v < 0:
                    ho += 1
                    if abs(v) < 0.75:
                        ho1 += 1
                    else:
                        ho2 += 1
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
    avg = r / U / n_ep
    cal = [avg[0] / SC[0], avg[1] / SC[1], avg[2] / SC[2]]
    scalar = sum(W[i] * cal[i] for i in range(3))
    return dict(r1=avg[0], r2=avg[1], r3=avg[2], scalar=scalar,
                ho_rate=ho / steps, ho1=ho1 / steps, ho2=ho2 / steps)


# ---- kappa* calibration: one pilot episode, median legal r1_hat_raw -------
tr0 = fresh()
st0, mk0, _ = env.reset(tr0._env_rng, tr0._mobility_rng)
p1, _, _ = preds(st0)
vals = np.concatenate([p1[u][np.where(mk0[u].mask)[0]] for u in range(U)
                       if mk0[u].mask.any()])
med = float(np.median(vals))
KAPPA_STAR = TARGET_R1C_PER_STEP / med
print(f"# median legal r1_hat_raw = {med:.6e} bit/s ; "
      f"kappa* = {KAPPA_STAR:.6e} (sets the median calibrated r1 term to "
      f"{TARGET_R1C_PER_STEP} per user-step)")
print(f"# B = {B:.6e} Hz ; PHI1={PHI1} PHI2={PHI2} ; users={U} steps/ep={T}")

MULTS = [0.0, 0.1, 0.3, 1.0, 3.0, 10.0, 100.0, 1.0e4]
SWEEP_EP = 3
FINAL_EP = 8

t0 = time.time()
print(f"\n## kappa sweep (GREEDY_SCALARIZED, {SWEEP_EP} episodes each)")
print(f"{'m':>8s} {'r1_mean':>14s} {'r2_mean':>9s} {'r3_mean':>9s} "
      f"{'scalar':>9s} {'ho_rate':>8s}")
best = (None, -1e9)
for m in MULTS:
    o = run(make_scalar_arm(KAPPA_STAR * m), SWEEP_EP)
    print(f"{m:8g} {o['r1']:14.6e} {o['r2']:9.3f} {o['r3']:9.3f} "
          f"{o['scalar']:9.4f} {o['ho_rate']:8.4f}", flush=True)
    if o["scalar"] > best[1]:
        best = (m, o["scalar"])
MSTAR = best[0]
print(f"# best multiplier m* = {MSTAR} (sweep scalar {best[1]:.4f})")

print(f"\n## final arms ({FINAL_EP} episodes each, m* = {MSTAR})")
ARMS = {
    "RANDOM_MASKED (harness check)": arm_random,
    "MAX_NOMINAL_GAIN": arm_maxgain,
    "GREEDY_SCALARIZED (r1+r2+r3)": make_scalar_arm(KAPPA_STAR * MSTAR),
    "GREEDY_R1R2": make_scalar_arm(KAPPA_STAR * MSTAR, use_r3=False),
    "GREEDY_R1R3": make_scalar_arm(KAPPA_STAR * MSTAR, use_r2=False),
}
print(f"{'arm':32s} {'r1_mean':>14s} {'r2_mean':>9s} {'r3_mean':>9s} "
      f"{'scalar':>9s} {'ho_rate':>8s} {'phi1':>7s} {'phi2':>7s}")
res = {}
for k, f in ARMS.items():
    o = run(f, FINAL_EP)
    res[k] = o
    print(f"{k:32s} {o['r1']:14.6e} {o['r2']:9.3f} {o['r3']:9.3f} "
          f"{o['scalar']:9.4f} {o['ho_rate']:8.4f} {o['ho1']:7.4f} "
          f"{o['ho2']:7.4f}", flush=True)

rnd = res["RANDOM_MASKED (harness check)"]["r1"]
print(f"\n# ratio-controlled r1 vs RANDOM ({rnd:.6e}):")
for k, o in res.items():
    print(f"#   {k:32s} {o['r1'] / rnd:6.3f}")
print("# trained checkpoint last-100: r1=8.938629e+06 r2=-2.322 r3=-18.598 "
      "calibrated scalar=+0.8859 ; learned/random(ep0-7)=1.650")
print(f"\n# total wall {time.time() - t0:.1f} s")
