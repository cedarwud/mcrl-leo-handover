"""Pooled EE (ratio of sums) for every arm on the MODQN harness.

READ-ONLY / NO TRAINING: update() is never called, no gradient step, no
optimizer step.  The trained arm LOADS the frozen checkpoint read-only.

Estimand, per the project declaration (pooled bits over pooled joules, a
ratio of sums, never a mean of ratios):

    pooled_EE = ( sum over steps of  system_throughput_bps * dt )
              / ( sum over steps of  system_consumed_power_w * dt )

accumulated as two running totals and divided once at the end.  Both come
from the environment's own per-step SystemEnergyEfficiency
(energy_efficiency.py:37-49), reached through `env.last_outcome`
(trainer_env.py:239-248), not reconstructed.

Numerator convention: FULL-BUFFER Shannon, no demand cap.
  link_budget.py:590-615 -- R = (B^w / U_{s,v}) * log2(1 + gamma), eq. (3.14)
  step.py:964-970        -- rate = where(served, shannon_rate_bps(...), 0.0)
  grep for demand_cap|rate_target|nominal_rate|setpoint|target_rate|min_rate|
  qos_rate over src/mcrl/env/ returns ZERO hits, so there is no demand cap and
  no nominal rate setpoint -- "rate attainment" has no referent here.
"""
import statistics as st
import sys
import time

sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, NUM_BEAM_SLOTS, PHI1, PHI2, no_op_actions
from mcrl.env.constants import DECISION_STEP_S
from mcrl.env.link_budget import BEAM_BANDWIDTH_HZ
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

W = (0.5, 0.3, 0.2)
SC = (2029238.4328742754, 1.0, 6.0)
B = float(BEAM_BANDWIDTH_HZ)
KAPPA = 8.394622e-10 * 0.1          # kappa* x m*, frozen from scalar_demo.py
DT = float(DECISION_STEP_S)
N_EP = 24
CKPT = ("/home/u24/papers/mcrl-leo-handover/artifacts/"
        "training-2026-08-25-rerun01/main/final-checkpoint.pt")

cfg = TrainerConfig(learning_rate=0.001, episodes=1)
env = make_training_environment(users=100)
U, T = env.config.num_users, env.config.steps_per_episode


def preds(states):
    n = len(states)
    r1 = np.zeros((n, 28)); r2 = np.zeros((n, 28)); r3 = np.zeros((n, 28))
    for u, s in enumerate(states):
        load = np.asarray(s.beam_loads, dtype=np.float64)
        sinr = np.maximum(np.asarray(s.channel_quality, dtype=np.float64), 0.0)
        r1[u] = (B / (load + 1.0)) * np.log2(1.0 + sinr)
        r3[u] = -(load + 1.0)
        inc = np.flatnonzero(np.asarray(s.access_vector) > 0.5)
        if inc.size == 0:
            r2[u] = -PHI2
        else:
            i = int(inc[0]); ls = i // NUM_BEAM_SLOTS
            row = np.full(28, -PHI2)
            row[ls * NUM_BEAM_SLOTS:(ls + 1) * NUM_BEAM_SLOTS] = -PHI1
            row[i] = 0.0
            r2[u] = row
    return r1, r2, r3


def argmax_masked(score, masks):
    out = no_op_actions(len(masks))
    for u in range(len(masks)):
        v = np.where(masks[u].mask)[0]
        out[u] = int(v[int(np.argmax(score[u][v]))]) if v.size else NO_OP_ACTION
    return out


def scalar_arm(use_r2=True, use_r3=True):
    def pick(tr, enc, masks, states):
        r1, r2, r3 = preds(states)
        s = W[0] * KAPPA * r1
        if use_r2:
            s = s + W[1] * (r2 / SC[1])
        if use_r3:
            s = s + W[2] * (r3 / SC[2])
        return argmax_masked(s, masks)
    return pick


def arm_maxgain(tr, enc, masks, states):
    return argmax_masked([s.channel_quality for s in states], masks)


def arm_random(tr, enc, masks, states):
    return tr.select_actions(enc, masks, 1.0)


def arm_trained(tr, enc, masks, states):
    return tr.select_actions(enc, masks, 0.0)          # deployed = greedy


def run(fn, load_ckpt=False):
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    if load_ckpt:
        tr.load_checkpoint(CKPT, load_optimizers=False)
    bits = 0.0; joules = 0.0
    served = 0; usersteps = 0; ho = 0
    per_ep_scalar = []
    per_ep_ee = []
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        r = np.zeros(3); eb = 0.0; ej = 0.0
        for _t in range(T):
            a = fn(tr, enc, masks, states)
            res = env.step(a, tr._env_rng)
            e = env.last_outcome.energy
            eb += float(e.system_throughput_bps) * DT
            ej += float(e.system_consumed_power_w) * DT
            served += int(e.served)
            for uid in range(U):
                r += tr.reward_vector_from_step_result(res, uid)
                usersteps += 1
                if res.rewards[uid].r2_handover < 0:
                    ho += 1
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        bits += eb; joules += ej
        avg = r / U
        per_ep_scalar.append(sum(W[i] * avg[i] / SC[i] for i in range(3)))
        per_ep_ee.append(eb / ej if ej > 0 else float("nan"))
    return dict(bits=bits, joules=joules, ee=bits / joules,
                served_rate=served / usersteps, ho_rate=ho / usersteps,
                scalar=st.mean(per_ep_scalar),
                scalar_sem=st.pstdev(per_ep_scalar) / len(per_ep_scalar) ** 0.5,
                ee_ep=per_ep_ee)


t0 = time.time()
print(f"# N_EP={N_EP}/arm, frozen seeds (42/1337/7), dt={DT} s, "
      f"no update() call. Estimand = sum(bits)/sum(joules), divided once.")
print(f"# numerator: full-buffer Shannon eq.(3.14), NO demand cap "
      f"(link_budget.py:590-615, step.py:964-970); no rate setpoint exists "
      f"in this env, so rate attainment has no referent.")
print(f"# trained arm loads {CKPT} (sha256 e6b063ef...1b09c28b), greedy eps=0.")
print()
hdr = (f"{'arm':30s} {'pooled bits':>14s} {'pooled joules':>14s} "
       f"{'pooled EE bit/J':>16s} {'served':>7s} {'ho':>7s} {'scalar':>9s}")
print(hdr)
ARMS = [
    ("RANDOM_MASKED (harness check)", arm_random, False),
    ("MAX_NOMINAL_GAIN", arm_maxgain, False),
    ("GREEDY_SCALARIZED", scalar_arm(), False),
    ("GREEDY_R1R2", scalar_arm(use_r3=False), False),
    ("TRAINED e6b063ef (greedy)", arm_trained, True),
]
res = {}
for name, fn, ck in ARMS:
    o = run(fn, load_ckpt=ck)
    res[name] = o
    print(f"{name:30s} {o['bits']:14.6e} {o['joules']:14.6e} "
          f"{o['ee']:16.6f} {o['served_rate']:7.4f} {o['ho_rate']:7.4f} "
          f"{o['scalar']:9.4f}", flush=True)

print("\n# per-episode pooled EE spread (each episode's own bits/joules), "
      "for a resolvability read only:")
for k, o in res.items():
    v = o["ee_ep"]
    print(f"#   {k:30s} mean {st.mean(v):10.4f}  sd {st.pstdev(v):8.4f}  "
          f"sem {st.pstdev(v) / len(v) ** 0.5:7.4f}")

tr_ee = res["TRAINED e6b063ef (greedy)"]["ee"]
mg_ee = res["MAX_NOMINAL_GAIN"]["ee"]
print(f"\n# MAX_NOMINAL_GAIN pooled EE {mg_ee:.6f} vs TRAINED {tr_ee:.6f} "
      f"-> ratio {mg_ee / tr_ee:.4f}, delta {mg_ee - tr_ee:+.6f} bit/J")
print(f"\n# total wall {time.time() - t0:.1f} s")
