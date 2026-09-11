"""B0 greedy pooled-EE evaluation -- the catfish-surface harness, reused.

Source: ``.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md``,
section "Pooled EE -- the declared primary endpoint", script ``pooled_ee.py``
(sha256 9b469c64...).  The block between the two HARNESS-CORE markers below
is copied from that script **byte for byte** (its lines 53-143: ``preds``,
``argmax_masked``, ``scalar_arm``, ``arm_maxgain``, ``arm_random``,
``arm_trained``, ``run``), and the header constants are its own.  Only three
things differ, all outside the core:

  * the repo path is this script's own tree, not a hardcoded local path;
  * ``CKPT`` is set per arm from the command line;
  * the driver prints one JSON line per arm instead of the fixed five-arm table.

Estimand (unchanged): pooled_EE = sum(bits) / sum(joules) over all
24 episodes x 10 steps, divided ONCE; bits and joules come from
``env.last_outcome.energy``, not from the reward fields.  READ-ONLY: no
``update()``, no gradient step, no optimizer step.

Usage::

    b0_pooled_ee_eval.py LABEL=PATH [LABEL=PATH ...] [--random]
"""
import json
import statistics as st
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

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
N_EP = int(__import__("os").environ.get("B0_EVAL_N_EP_SMOKE_ONLY", "24"))  # 24 = the harness value
CKPT = None  # set per arm by the driver below

cfg = TrainerConfig(learning_rate=0.001, episodes=1)
env = make_training_environment(users=100)
U, T = env.config.num_users, env.config.steps_per_episode


# ---- HARNESS-CORE BEGIN (verbatim from pooled_ee.py lines 53-143) ----
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

# ---- HARNESS-CORE END ----


def _driver(argv):
    global CKPT
    arms = []
    if "--random" in argv:
        arms.append(("RANDOM_MASKED (harness check)", arm_random, None))
    for item in argv:
        if item.startswith("--"):
            continue
        label, _, path = item.partition("=")
        arms.append((label, arm_trained, path))
    t0 = time.time()
    print(f"# N_EP={N_EP}/arm, seeds 42/1337/7, dt={DT} s, no update() call; "
          f"estimand sum(bits)/sum(joules) divided once", flush=True)
    for label, fn, path in arms:
        CKPT = path
        t_arm = time.time()
        o = run(fn, load_ckpt=path is not None)
        ee_ep = o.pop("ee_ep")
        o.update(
            label=label,
            checkpoint=path,
            ee_ep_mean=st.mean(ee_ep),
            ee_ep_sd=st.pstdev(ee_ep),
            ee_ep_sem=st.pstdev(ee_ep) / len(ee_ep) ** 0.5,
            n_episodes=len(ee_ep),
            wall_s=time.time() - t_arm,
        )
        print("RESULT " + json.dumps(o, sort_keys=True), flush=True)
    print(f"# total wall {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    _driver(sys.argv[1:])
