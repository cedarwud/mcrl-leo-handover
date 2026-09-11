"""JSRL guide-horizon sweep: does the guide hand the learner new states?

READ-ONLY / NO TRAINING: update() is never called, no optimizer is touched, no
gradient step happens.  The learner LOADS the frozen checkpoint read-only.

Guide  = MAX_NOMINAL_GAIN, rolls steps 0..h-1.
Learner = trained e6b063ef..., greedy (eps = 0), rolls steps h..T-1.
h in {0,...,10}; T = 10, so h = 0 is learner-alone and h = 10 is guide-alone.

Same harness, estimand, seeds and fresh-env-per-cell discipline as frontier.py.

COVERAGE MEASURE, declared before the run
-----------------------------------------
For each h, the "handover states" are the 24 x 100 per-user 112-dim encoded
observations at step index h -- the states the learner is actually handed.
The reference pool is the 24 x 100 encoded observations at the SAME step index
h from the h = 0 rollout, i.e. states the learner reaches on its own.

Both are z-scored per dimension using the h = 0 rollout's own per-dimension
mean and sd (pooled over all step indices), so no single block dominates the
metric by its units.  For each handover state we take the Euclidean 1-nearest-
neighbour distance to the reference pool.  We report

  d(h)   = mean 1-NN distance, handover states -> h=0 pool at index h
  d0(h)  = mean LEAVE-ONE-OUT 1-NN distance within the h=0 pool at index h
           (the learner's own states' distance to each other -- the natural
           yardstick for "how far apart are states the learner already reaches")
  R(h)   = d(h) / d0(h)                  -- novelty ratio; R(0) = 1 by construction
  out95  = fraction of handover states whose 1-NN distance exceeds the 95th
           percentile of the leave-one-out distribution (so out95 = 0.05 at h=0)

LIMITATIONS, stated rather than buried: (i) the 112-dim encoding is a
user-relative candidate ordering, so two vectors can be close while naming
different physical beams -- this measures observation-space novelty, which is
what a function approximator sees, not physical-state novelty; (ii) 1-NN over
2400 points in 112 dimensions is sparse, so absolute distances are not
meaningful and only the RATIO to the learner's own spread is read here;
(iii) the reference pool is one rollout (24 episodes), not the learner's whole
reachable set, so this is a lower bound on coverage overlap.
"""
import statistics as st
import sys
import time

SCRATCH = ("/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/"
           "e9fba164-4724-465f-8afa-7891b4efee90/scratchpad")
sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")
sys.path.insert(0, SCRATCH)

import numpy as np

from c3s_physics_override import DiagnosticStepEnvironment, get_physics_override
from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import NO_OP_ACTION, PHI1, PHI2, no_op_actions
from mcrl.env.constants import DECISION_STEP_S
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

W = (0.5, 0.3, 0.2)
SC = (2029238.4328742754, 1.0, 6.0)
DT = float(DECISION_STEP_S)
N_EP = int(sys.argv[1]) if len(sys.argv) > 1 else 24
CKPT = ("/home/u24/papers/mcrl-leo-handover/artifacts/"
        "training-2026-08-25-rerun01/main/final-checkpoint.pt")

cfg = TrainerConfig(learning_rate=0.001, episodes=1)


def build_env():
    e = make_training_environment(users=100)
    e.environment = DiagnosticStepEnvironment.construct(
        e.environment.driver, physics_override=get_physics_override("none")
    )
    return e


def guide(tr, enc, masks, states):
    """MAX_NOMINAL_GAIN -- identical to frontier.py's A m=0 arm."""
    out = no_op_actions(len(states))
    for u, s in enumerate(states):
        gain = np.asarray(s.channel_quality, dtype=np.float64)
        legal = np.flatnonzero(np.asarray(masks[u].mask, dtype=bool))
        out[u] = (int(legal[int(np.argmax(gain[legal]))]) if legal.size
                  else NO_OP_ACTION)
    return out


def run(h):
    env = build_env()
    U, T = env.config.num_users, env.config.steps_per_episode
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    tr.load_checkpoint(CKPT, load_optimizers=False)   # read-only weight load
    bits = joules = 0.0
    served = usersteps = ho1 = ho2 = 0
    beams = 0.0
    nsteps = 0
    ee_ep = []
    sc_ep = []
    per_index = [[] for _ in range(T)]     # encoded states seen at each step index
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        eb = ej = 0.0
        r = np.zeros(3)
        for t in range(T):
            per_index[t].append(np.asarray(enc, dtype=np.float64).copy())
            a = guide(tr, enc, masks, states) if t < h else \
                tr.select_actions(enc, masks, 0.0)
            res = env.step(a, tr._env_rng)
            e = env.last_outcome.energy
            eb += float(e.system_throughput_bps) * DT
            ej += float(e.system_consumed_power_w) * DT
            served += int(e.served)
            beams += float(e.eff_beams)
            nsteps += 1
            for uid in range(U):
                r += tr.reward_vector_from_step_result(res, uid)
                usersteps += 1
                hv = res.rewards[uid].r2_handover
                if hv < 0:
                    if abs(hv + PHI1) < 1e-9:
                        ho1 += 1
                    elif abs(hv + PHI2) < 1e-9:
                        ho2 += 1
                    else:
                        raise SystemExit(f"unexpected r2_handover {hv!r}")
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        bits += eb
        joules += ej
        ee_ep.append(eb / ej if ej > 0 else float("nan"))
        avg = r / U
        sc_ep.append(sum(W[i] * avg[i] / SC[i] for i in range(3)))
    return dict(bits=bits, joules=joules, ee=bits / joules,
                served=served / usersteps,
                ho=(ho1 + ho2) / usersteps, ho1=ho1 / usersteps,
                ho2=ho2 / usersteps, beams=beams / nsteps,
                scalar=st.mean(sc_ep),
                sem=st.pstdev(ee_ep) / len(ee_ep) ** 0.5,
                states=[np.concatenate(v, axis=0) for v in per_index])


def nn_dist(query, pool, loo=False):
    """Euclidean 1-NN distance from every row of `query` to `pool`."""
    q2 = (query ** 2).sum(1)[:, None]
    p2 = (pool ** 2).sum(1)[None, :]
    d2 = np.maximum(q2 + p2 - 2.0 * query @ pool.T, 0.0)
    if loo:
        np.fill_diagonal(d2, np.inf)
    return np.sqrt(d2.min(axis=1))


t0 = time.time()
print(f"# JSRL sweep  N_EP={N_EP}/cell, frozen seeds (42/1337/7), dt={DT} s.")
print("# guide = MAX_NOMINAL_GAIN steps 0..h-1; learner = trained e6b063ef greedy.")
print("# fresh env per cell; no update(), no gradient step.\n")

cells = {}
for h in range(0, 11):
    cells[h] = run(h)
    o = cells[h]
    print(f"h={h:2d} bits={o['bits']:.6e} J={o['joules']:.6e} "
          f"EE={o['ee']:16.6f} sem={o['sem']:10.1f} ho={o['ho']:.4f} "
          f"phi1={o['ho1']:.4f} phi2={o['ho2']:.4f} served={o['served']:.4f} "
          f"beams={o['beams']:.3f} scalar={o['scalar']:+.4f}", flush=True)

# ---- coverage, z-scored on the h=0 rollout's own per-dimension statistics
base = cells[0]["states"]
allbase = np.concatenate(base, axis=0)
mu = allbase.mean(axis=0)
sd = allbase.std(axis=0)
sd[sd < 1e-12] = 1.0
print(f"\n# coverage: z-scored on h=0 pool (mu/sd over {allbase.shape[0]} rows, "
      f"{int((allbase.std(axis=0) < 1e-12).sum())} constant dims set to sd=1)")
print(f"# {'h':>3s} {'d(h)':>10s} {'d0(h)':>10s} {'R(h)':>8s} {'out95':>8s} "
      f"{'n_query':>8s}")
T = len(base)
for h in range(0, 11):
    if h >= T:
        print(f"  {h:>3d} {'n/a':>10s} {'n/a':>10s} {'n/a':>8s} {'n/a':>8s} "
              f"{'n/a':>8s}   (guide-alone: the learner is never handed a state)")
        continue
    pool = (base[h] - mu) / sd
    loo = nn_dist(pool, pool, loo=True)
    thr = float(np.percentile(loo, 95))
    if h == 0:
        d = loo
    else:
        d = nn_dist((cells[h]["states"][h] - mu) / sd, pool)
    print(f"  {h:>3d} {d.mean():10.4f} {loo.mean():10.4f} "
          f"{d.mean() / loo.mean():8.4f} {float((d > thr).mean()):8.4f} "
          f"{d.size:8d}", flush=True)

if len(sys.argv) > 2:          # audit dump: raw (un-z-scored) encoded states
    np.savez_compressed(
        sys.argv[2],
        base=np.stack(base, axis=0).astype(np.float32),          # (T, N, 112)
        handed=np.stack([cells[h]["states"][h] for h in range(1, T)],
                        axis=0).astype(np.float32),              # (T-1, N, 112)
        ee=np.array([cells[h]["ee"] for h in range(0, 11)]))
    print(f"# states dumped to {sys.argv[2]}")

print(f"\n# placebo targets (fresh-env, previous round): "
      f"TRAINED 93110907.97 ho 0.2799 | MAX_NOMINAL_GAIN 111504571.39 ho 0.7120")
print(f"# total wall {time.time() - t0:.1f} s")
