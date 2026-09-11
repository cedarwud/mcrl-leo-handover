"""FEASFRONT: does a non-learned rule with memory dominate the trained policy?

READ-ONLY / NO TRAINING: update() is never called, no optimizer is touched, no
gradient step happens.  The trained arm LOADS the frozen checkpoint read-only.
src/ is never edited or import-time patched.

Harness, estimand and the fresh-env-per-cell discipline are reused verbatim from
.scratch/catfish-surface/CATFISH-ATTACHMENT-SURFACE-2026-09-11.md:
  - pooled EE = (sum over all steps of throughput_bps*dt) / (sum of power_w*dt),
    two running totals divided ONCE.  dt = DECISION_STEP_S = 30.08 s.
  - both per-step quantities are the environment's own, read off
    env.last_outcome.energy (SystemEnergyEfficiency), not reconstructed.
  - `_age_rng` spawns once per StepEnvironment and carries across episodes
    (env/step.py:534-536), so every cell builds a FRESH environment.
  - DiagnosticStepEnvironment.construct with physics_override=None ("none") is
    the wrapper the previous round proved transparent; it is used here so this
    run is comparable cell-for-cell with that one.

DECLARED GRID (fixed before the run, not extended and not re-centred):
  Family A hysteresis margins m in {0, 0.5, 1, 2, 3, 4, 6, 9, 12} dB
  Family B B1_NO_NEW_BEAM, B2_PREFER_SHARED
  Family C C1_SAT_LOCK, C2_SAT_LOCK_3DB
  Family D A m=0 (= unrestricted MAX_NOMINAL_GAIN) and HOLD_WHILE_LEGAL
  plus RANDOM_MASKED (harness check) and TRAINED e6b063ef (reference).
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
from mcrl.env.action_contract import (NO_OP_ACTION, NUM_BEAM_SLOTS, PHI1, PHI2,
                                      no_op_actions)
from mcrl.env.constants import DECISION_STEP_S
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

W = (0.5, 0.3, 0.2)
SC = (2029238.4328742754, 1.0, 6.0)
DT = float(DECISION_STEP_S)
N_EP = int(sys.argv[1]) if len(sys.argv) > 1 else 24
ONLY = sys.argv[2] if len(sys.argv) > 2 else None
CKPT = ("/home/u24/papers/mcrl-leo-handover/artifacts/"
        "training-2026-08-25-rerun01/main/final-checkpoint.pt")

cfg = TrainerConfig(learning_rate=0.001, episodes=1)


def build_env():
    e = make_training_environment(users=100)
    e.environment = DiagnosticStepEnvironment.construct(
        e.environment.driver, physics_override=get_physics_override("none")
    )
    return e


# ---------------------------------------------------------------- primitives
def incumbent_slot(state):
    """Slot index of the incumbent association in the CURRENT candidate
    ordering, or -1 when block 1 (`access_vector`) is all-zero, which means the
    incumbent has left the candidate table (or the user was unserved)."""
    inc = np.flatnonzero(np.asarray(state.access_vector) > 0.5)
    return int(inc[0]) if inc.size else -1


def pick(gain, legal, allowed, inc, margin_db):
    """One user's choice.

    `allowed` is the family restriction (a boolean over 28 slots); `legal` the
    action mask.  Hysteresis: the incumbent is held unless some allowed legal
    challenger's nominal gain exceeds the incumbent's by `margin_db` dB.
    Fallback order is declared, not discovered: restricted-and-legal, then
    incumbent, then legal-unrestricted.
    """
    ok = np.flatnonzero(legal & allowed)
    if ok.size == 0:
        ok = np.flatnonzero(legal)
        if ok.size == 0:
            return NO_OP_ACTION
    best = int(ok[int(np.argmax(gain[ok]))])
    if margin_db <= 0.0:
        # m = 0 is the plain restricted argmax, with NO incumbent preference,
        # so that A m=0 reproduces MAX_NOMINAL_GAIN bit-for-bit and so that a
        # family restriction is never silently undone by an incumbent hold.
        return best
    if inc >= 0 and legal[inc]:
        if gain[best] > gain[inc] * (10.0 ** (margin_db / 10.0)):
            return best
        return inc
    return best


def make_rule(margin_db=0.0, restrict=None):
    """restrict(gain, load, inc, legal) -> boolean allow-mask over 28 slots."""

    def fn(tr, enc, masks, states):
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            gain = np.asarray(s.channel_quality, dtype=np.float64)
            load = np.asarray(s.beam_loads, dtype=np.float64)
            legal = np.asarray(masks[u].mask, dtype=bool)
            inc = incumbent_slot(s)
            allowed = (np.ones(28, dtype=bool) if restrict is None
                       else restrict(gain, load, inc, legal))
            out[u] = pick(gain, legal, allowed, inc, margin_db)
        return out

    return fn


# ------------------------------------------------------- family restrictions
def r_no_new_beam(gain, load, inc, legal):
    """Options whose physical beam already carried demand last step, so
    selecting them lights no new beam.  Block 4 is N_u(t-1) (step.py:1163-1174),
    i.e. one step stale — unavoidably, no user can see this step's choices."""
    return load > 0.5


def r_prefer_shared(gain, load, inc, legal):
    """Beams whose occupancy is non-zero EXCLUDING this user itself.  The
    incumbent's own beam carries this user in N_u(t-1), so one is subtracted
    there; every other candidate's load counts other users only."""
    occ = load.copy()
    if inc >= 0:
        occ[inc] -= 1.0
    strong = occ > 0.5
    if (strong & legal).any():
        return strong
    return load > 0.5            # declared fallback: B1's set, then unrestricted


def r_sat_lock(gain, load, inc, legal):
    """Incumbent satellite only; beam changes within it are still allowed."""
    if inc < 0:
        return np.ones(28, dtype=bool)
    a = np.zeros(28, dtype=bool)
    ls = inc // NUM_BEAM_SLOTS
    a[ls * NUM_BEAM_SLOTS:(ls + 1) * NUM_BEAM_SLOTS] = True
    return a


def arm_hold(tr, enc, masks, states):
    """HOLD_WHILE_LEGAL: never move unless the incumbent becomes illegal."""
    out = no_op_actions(len(states))
    for u, s in enumerate(states):
        legal = np.asarray(masks[u].mask, dtype=bool)
        inc = incumbent_slot(s)
        if inc >= 0 and legal[inc]:
            out[u] = inc
        else:
            gain = np.asarray(s.channel_quality, dtype=np.float64)
            ok = np.flatnonzero(legal)
            out[u] = int(ok[int(np.argmax(gain[ok]))]) if ok.size else NO_OP_ACTION
    return out


def arm_random(tr, enc, masks, states):
    return tr.select_actions(enc, masks, 1.0)


def arm_trained(tr, enc, masks, states):
    return tr.select_actions(enc, masks, 0.0)


MARGINS = (0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 9.0, 12.0)

ARMS = [("RANDOM_MASKED", arm_random, False)]
ARMS += [(f"A m={m:g}dB", make_rule(margin_db=m), False) for m in MARGINS]
ARMS += [
    ("B1_NO_NEW_BEAM", make_rule(restrict=r_no_new_beam), False),
    ("B2_PREFER_SHARED", make_rule(restrict=r_prefer_shared), False),
    ("C1_SAT_LOCK", make_rule(restrict=r_sat_lock), False),
    ("C2_SAT_LOCK_3DB", make_rule(margin_db=3.0, restrict=r_sat_lock), False),
    ("D_HOLD_WHILE_LEGAL", arm_hold, False),
    ("TRAINED e6b063ef", arm_trained, True),
]


def run(fn, load_ckpt):
    env = build_env()
    U, T = env.config.num_users, env.config.steps_per_episode
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    if load_ckpt:
        tr.load_checkpoint(CKPT, load_optimizers=False)
    bits = joules = 0.0
    served = usersteps = ho1 = ho2 = 0
    beams = 0.0
    nsteps = 0
    ee_ep = []
    sc_ep = []
    ho_ep = []
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        eb = ej = 0.0
        eho = eus = 0
        r = np.zeros(3)
        for _t in range(T):
            a = fn(tr, enc, masks, states)
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
                eus += 1
                h = res.rewards[uid].r2_handover
                if h < 0:
                    eho += 1
                    if abs(h + PHI1) < 1e-9:
                        ho1 += 1
                    elif abs(h + PHI2) < 1e-9:
                        ho2 += 1
                    else:                       # must not happen; fail loud
                        raise SystemExit(f"unexpected r2_handover {h!r}")
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        bits += eb
        joules += ej
        ee_ep.append(eb / ej if ej > 0 else float("nan"))
        ho_ep.append(eho / eus)
        avg = r / U
        sc_ep.append(sum(W[i] * avg[i] / SC[i] for i in range(3)))
    return dict(ho_sem=st.pstdev(ho_ep) / len(ho_ep) ** 0.5,
                bits=bits, joules=joules, ee=bits / joules,
                served=served / usersteps,
                ho=(ho1 + ho2) / usersteps, ho1=ho1 / usersteps,
                ho2=ho2 / usersteps, beams=beams / nsteps,
                scalar=st.mean(sc_ep),
                sem=st.pstdev(ee_ep) / len(ee_ep) ** 0.5)


t0 = time.time()
print(f"# FEASFRONT  N_EP={N_EP}/cell, frozen seeds (42/1337/7), dt={DT} s.")
print("# pooled EE = sum(bits)/sum(joules), two running totals divided once.")
print("# fresh env per cell (_age_rng matched); no update(), no gradient step.")
print(f"# {'arm':20s} {'pooled bits':>14s} {'pooled J':>14s} {'pooled EE':>16s} "
      f"{'sem':>11s} {'ho':>7s} {'ho_phi1':>8s} {'ho_phi2':>8s} {'served':>7s} "
      f"{'beams':>7s} {'scalar':>8s}", flush=True)
res = {}
for name, fn, ck in ARMS:
    if ONLY and not any(k in name for k in ONLY.split(",")):
        continue
    o = run(fn, ck)
    res[name] = o
    print(f"{name:22s} {o['bits']:14.6e} {o['joules']:14.6e} {o['ee']:16.6f} "
          f"{o['sem']:11.1f} {o['ho']:7.4f} {o['ho1']:8.4f} {o['ho2']:8.4f} "
          f"{o['served']:7.4f} {o['beams']:7.3f} {o['scalar']:8.4f}"
          f"   ho_sem={o['ho_sem']:.5f}", flush=True)

print(f"\n# reference (previous round, shared env): MAX_NOMINAL_GAIN 111553182.85 "
      f"ho 0.7117 served 0.9981 | TRAINED 93137893.02 ho 0.2796 served 0.9988")
print(f"# reference (previous round, fresh env via this wrapper): "
      f"MAX 111504571.39 ho 0.7120 | TRAINED 93110907.97 ho 0.2799")
print(f"# total wall {time.time() - t0:.1f} s")
