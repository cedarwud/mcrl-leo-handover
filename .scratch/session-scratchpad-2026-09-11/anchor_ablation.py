"""Segment-anchor ablation: pooled EE, anchored (`none`) vs `ablate_anchor`.

READ-ONLY / NO TRAINING: update() is never called; the trained arm LOADS the
frozen checkpoint read-only; src/ is never edited or import-time patched.

The ablation is diag2's, reused verbatim, not reinvented:
  spec  .scratch/multi-catfish-v023-controller-handoff-20260907/prompts/
        codex-sol-c3s-churn-null.md:16 -- "ablate_anchor: refresh the segment
        anchor every step (equivalently make recurrence_power_w return
        p0 = 0.825 W at every step and let the wanted signal use the CURRENT
        transmit gain instead of the segment-start value)"
  impl  c3s_physics_override.py, fetched read-only from
        /home/sat/mcrl-v023-codex-ws-c3s-baselines/.scratch/
        multi-catfish-v023-c3s-screen/c3s_physics_override.py
        sha256 a534244755f1df55ebc12b96a67fce93fe34e91c9b7d886aef4ae6276378f03a
  It is written against THIS repo's mcrl.env.step.StepEnvironment, so it
  applies to the MODQN harness unchanged.

Matched-construction note: StepEnvironment spawns `_age_rng` from the env_rng
on first reset (step.py:534-536) and then carries it across episodes.  A
single shared env therefore gives different segment-age draws to whichever
arm runs second.  Here every (override, arm) cell builds a FRESH environment,
so `_age_rng` is spawned from the same env_rng state in every cell.
"""
import statistics as st
import sys
import time

SCRATCH = "/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/e9fba164-4724-465f-8afa-7891b4efee90/scratchpad"
sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")
sys.path.insert(0, SCRATCH)

import numpy as np

from c3s_physics_override import DiagnosticStepEnvironment, get_physics_override
from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, NUM_BEAM_SLOTS, PHI1, PHI2, no_op_actions
from mcrl.env.constants import DECISION_STEP_S
from mcrl.env.link_budget import BEAM_BANDWIDTH_HZ
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

W = (0.5, 0.3, 0.2)
SC = (2029238.4328742754, 1.0, 6.0)
B = float(BEAM_BANDWIDTH_HZ)
KAPPA = 8.394622e-10 * 0.1
DT = float(DECISION_STEP_S)
N_EP = 24
CKPT = ("/home/u24/papers/mcrl-leo-handover/artifacts/"
        "training-2026-08-25-rerun01/main/final-checkpoint.pt")

cfg = TrainerConfig(learning_rate=0.001, episodes=1)


def build_env(override_name):
    e = make_training_environment(users=100)
    e.environment = DiagnosticStepEnvironment.construct(
        e.environment.driver, physics_override=get_physics_override(override_name)
    )
    return e


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
    return tr.select_actions(enc, masks, 0.0)


ARMS = [
    ("RANDOM_MASKED", arm_random, False),
    ("MAX_NOMINAL_GAIN", arm_maxgain, False),
    ("GREEDY_R1R2", scalar_arm(use_r3=False), False),
    ("TRAINED e6b063ef", arm_trained, True),
]


def run(override_name, fn, load_ckpt):
    env = build_env(override_name)
    U, T = env.config.num_users, env.config.steps_per_episode
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    if load_ckpt:
        tr.load_checkpoint(CKPT, load_optimizers=False)
    bits = joules = 0.0
    served = usersteps = ho = 0
    ee_ep = []
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        eb = ej = 0.0
        for _t in range(T):
            a = fn(tr, enc, masks, states)
            res = env.step(a, tr._env_rng)
            e = env.last_outcome.energy
            eb += float(e.system_throughput_bps) * DT
            ej += float(e.system_consumed_power_w) * DT
            served += int(e.served)
            for uid in range(U):
                usersteps += 1
                if res.rewards[uid].r2_handover < 0:
                    ho += 1
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        bits += eb; joules += ej
        ee_ep.append(eb / ej if ej > 0 else float("nan"))
    return dict(bits=bits, joules=joules, ee=bits / joules,
                served=served / usersteps, ho=ho / usersteps,
                sem=st.pstdev(ee_ep) / len(ee_ep) ** 0.5)


t0 = time.time()
print(f"# N_EP={N_EP}/cell, frozen seeds (42/1337/7), dt={DT}s, no update().")
print("# pooled EE = sum(bits)/sum(joules), two running totals divided once.")
print("# override impl sha256 a534244755f1df55ebc12b96a67fce93fe34e91c9b7d886aef4ae6276378f03a")
print("# every cell builds a FRESH env so _age_rng is matched across arms.\n")
out = {}
for ov in ("none", "ablate_anchor"):
    print(f"## physics = {ov}")
    print(f"{'arm':22s} {'pooled bits':>14s} {'pooled joules':>14s} "
          f"{'pooled EE':>16s} {'sem':>12s} {'served':>7s} {'ho':>7s}")
    for name, fn, ck in ARMS:
        o = run(ov, fn, ck)
        out[(ov, name)] = o
        print(f"{name:22s} {o['bits']:14.6e} {o['joules']:14.6e} "
              f"{o['ee']:16.6f} {o['sem']:12.1f} {o['served']:7.4f} "
              f"{o['ho']:7.4f}", flush=True)
    print()

for ov in ("none", "ablate_anchor"):
    mg = out[(ov, "MAX_NOMINAL_GAIN")]["ee"]
    tre = out[(ov, "TRAINED e6b063ef")]["ee"]
    c = (out[(ov, "MAX_NOMINAL_GAIN")]["sem"] ** 2
         + out[(ov, "TRAINED e6b063ef")]["sem"] ** 2) ** 0.5
    print(f"# {ov:14s} MAX_NOMINAL_GAIN / TRAINED = {mg / tre:.4f}  "
          f"(delta {mg - tre:+.6e} bit/J, {abs(mg - tre) / c:.1f} sem)")
print(f"\n# previous shared-env anchored run: MAX 111553182.845841, "
      f"TRAINED 93137893.020321, ratio 1.1977")
print(f"\n# total wall {time.time() - t0:.1f} s")
