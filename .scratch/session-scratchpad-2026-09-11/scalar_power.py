"""Higher-n rerun of the two candidate arms with per-episode scalars.

READ-ONLY / NO TRAINING: update() is never called.  Same construction and
same kappa* as scalar_demo.py; only the episode count and the per-episode
bookkeeping change, so a paired comparison and a standard error are possible.
"""
import statistics as st
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
KAPPA = 8.394622e-10 * 0.1          # kappa* x m*, frozen from scalar_demo.py
N_EP = 24

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


def run(fn):
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    per = []
    ho = 0; steps = 0
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        r = np.zeros(3)
        for _t in range(T):
            a = fn(tr, enc, masks, states)
            res = env.step(a, tr._env_rng)
            for uid in range(U):
                r += tr.reward_vector_from_step_result(res, uid)
                steps += 1
                if res.rewards[uid].r2_handover < 0:
                    ho += 1
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        avg = r / U
        per.append(sum(W[i] * avg[i] / SC[i] for i in range(3)))
    return per, ho / steps


t0 = time.time()
print(f"# N_EP={N_EP} per arm, frozen seeds (42/1337/7), no update() call, "
      f"kappa = {KAPPA:.6e}")
print(f"{'arm':30s} {'scalar mean':>12s} {'sd':>8s} {'sem':>8s} {'ho_rate':>8s}")
out = {}
for name, fn in (("GREEDY_SCALARIZED", scalar_arm()),
                 ("GREEDY_R1R2", scalar_arm(use_r3=False)),
                 ("MAX_NOMINAL_GAIN", arm_maxgain)):
    per, hr = run(fn)
    out[name] = per
    print(f"{name:30s} {st.mean(per):12.4f} {st.pstdev(per):8.4f} "
          f"{st.pstdev(per) / len(per) ** 0.5:8.4f} {hr:8.4f}", flush=True)

d = [a - b for a, b in zip(out["GREEDY_R1R2"], out["GREEDY_SCALARIZED"])]
print(f"\n# paired GREEDY_R1R2 - GREEDY_SCALARIZED (same seeds, same episodes): "
      f"mean {st.mean(d):+.4f} sd {st.pstdev(d):.4f} "
      f"sem {st.pstdev(d) / len(d) ** 0.5:.4f}")
print("# trained checkpoint last-100 calibrated scalar: mean +0.8859 "
      "sd 0.1898 sem 0.0190 (n=100), handover rate 0.2490")
best = max(st.mean(out['GREEDY_R1R2']), st.mean(out['GREEDY_SCALARIZED']))
print(f"# best scripted arm mean {best:+.4f} vs trained +0.8859 -> "
      f"delta {best - 0.8859:+.4f}")
print(f"\n# total wall {time.time() - t0:.1f} s")
