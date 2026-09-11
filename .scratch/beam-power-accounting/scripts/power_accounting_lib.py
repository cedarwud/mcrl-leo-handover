"""POWERACCT -- re-score frozen actions under three beam-power accountings.

READ-ONLY / NO TRAINING: update() is never called, no gradient step, no
optimizer step.  The trained arm LOADS the frozen checkpoint read-only.
src/ is never edited and never import-time patched.

Design: one run per arm under the CANONICAL physics.  A StepEnvironment
subclass overrides _resolve_physics only to CALL the canonical one and then
record the per-step arrays; it changes nothing.  All three accountings are
recomputed from that same recorded step, so the actions, the RNG stream, the
SINRs, the rates and the served set are identical by construction across the
three denominators.  Only the joule accounting differs.

Accountings (fixed terms identical in all three -- link_budget.py:521-547):
  P^f = sum_s ( N_act_s * P_cir ) + 1{N_act_s>0} * P_BB,
        P_cir = 0.338 W/beam (link_budget.py:270), P_BB = 0.200 W/sat (:273)

  MAX          P_PA,b = p_b / xi(p_b),  p_b = max_{u in b, served} p_u
               (link_budget.py:439-465 beam_power_w, :468-494 pa_efficiency,
                :496-519 supply_power_w)
  TDM_AIRTIME  P_PA,b = sum_{u in b, served} tau_u * ( p_u / xi(p_u) ),
               tau_u = 1 / U_b, U_b = the SAME eligible beam load the rate
               divides the bandwidth by (service.py:164-182, used at
               step.py:969-973).  Per-user RF -> per-user PA DC draw FIRST,
               then integrate over airtime.  sum_u tau_u <= 1 by construction.
  ADDITIVE     P_PA,b = p_b / xi(p_b),  p_b = sum_{u in b, served} p_u

xi(p) = min(xi_max, xi_max*sqrt(p/p_sat)), xi_max = 0.35, p_sat = 5.21804 W
(link_budget.py:254-263).  Reused verbatim from the module -- not reimplemented.
"""
import json
import math
import statistics as st
import sys
import time

SCRATCH = ("/tmp/claude-1000/-home-u24-papers-mcrl-leo-handover/"
           "e9fba164-4724-465f-8afa-7891b4efee90/scratchpad")
sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")

import numpy as np

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.action_contract import (
    NO_OP_ACTION, NUM_BEAM_SLOTS, PHI1, PHI2, no_op_actions,
)
from mcrl.env.constants import DECISION_STEP_S
from mcrl.env.link_budget import (
    BEAM_BANDWIDTH_HZ, PA_MAX_EFFICIENCY, PA_SATURATION_POWER_W,
    fixed_power_w, pa_efficiency, supply_power_w,
)
from mcrl.env.step import StepEnvironment
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

W = (0.5, 0.3, 0.2)
SC = (2029238.4328742754, 1.0, 6.0)
B = float(BEAM_BANDWIDTH_HZ)
KAPPA = 8.394622e-10 * 0.1
DT = float(DECISION_STEP_S)
N_EP = int(sys.argv[1]) if len(sys.argv) > 1 else 24
CKPT = ("/home/u24/papers/mcrl-leo-handover/artifacts/"
        "training-2026-08-25-rerun01/main/final-checkpoint.pt")

ACCTS = ("MAX", "TDM_AIRTIME", "ADDITIVE")

cfg = TrainerConfig(learning_rate=0.001, episodes=1)


def _dc_of_total(p_total):
    """RF -> PA DC draw, through the module's own xi and P^p."""
    arr = np.asarray([p_total], dtype=np.float64)
    return float(supply_power_w(arr, pa_efficiency(arr))[0])


def _dc_beam(powers, u_b, acct):
    """PA DC draw of one beam from its served members' RF powers."""
    if not powers:
        return 0.0
    if acct == "MAX":
        return _dc_of_total(max(powers))
    if acct == "ADDITIVE":
        return _dc_of_total(sum(powers))
    if acct == "TDM_AIRTIME":
        if u_b <= 0.0:
            return 0.0
        return sum(_dc_of_total(p) for p in powers) / float(u_b)
    raise ValueError(acct)


class _RecordingStepEnvironment(StepEnvironment):
    """Calls the canonical evaluator, records, changes nothing."""

    def __init__(self, driver):
        super().__init__(driver)
        self.capture = []

    def _resolve_physics(self, decision, actions, rng):
        physics = StepEnvironment._resolve_physics(self, decision, actions, rng)
        res = physics["resolution"]
        keys = list(physics["beam_keys"])
        link_power = np.asarray(physics["link_power_w"], dtype=np.float64)
        served = np.asarray(res.served, dtype=bool)
        key_of = {k: i for i, k in enumerate(keys)}
        members = [[] for _ in keys]
        for uid in range(served.size):
            if not served[uid]:
                continue
            k = (int(res.serving_satellite[uid]), int(res.serving_cell[uid]))
            members[key_of[k]].append(float(link_power[uid]))
        loads = [float(res.eligible_load_by_beam[k]) for k in keys]
        counts = np.array(
            [sum(1 for k in keys if k[0] == n) for n in sorted({k[0] for k in keys})],
            dtype=np.float64,
        )
        fixed = fixed_power_w(counts) if counts.size else 0.0
        totals = {}
        for acct in ACCTS:
            totals[acct] = fixed + sum(
                _dc_beam(members[i], loads[i], acct) for i in range(len(keys))
            )
        self.capture.append({
            "members": members,
            "loads": loads,
            "fixed": float(fixed),
            "totals": totals,
            "env_power": float(physics["system_power_w"]),
            "n_beams": len(keys),
        })
        return physics


def build_env():
    e = make_training_environment(users=100)
    e.environment = _RecordingStepEnvironment(e.environment.driver)
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


def loo_marginals(cap, store):
    """Leave-one-out marginal of one user on an already-radiating beam.

    with-u    : beam has these members and eligible load U_b
    without-u : beam has members\\{u} and eligible load U_b - 1
    Only the airtime accounting sees U_b, so only it moves on the divisor.
    """
    for mem, u_b in zip(cap["members"], cap["loads"]):
        if len(mem) < 2 or u_b < 2.0:
            continue
        for i in range(len(mem)):
            rest = mem[:i] + mem[i + 1:]
            for acct in ACCTS:
                ub_out = u_b - 1.0 if acct == "TDM_AIRTIME" else u_b
                d = _dc_beam(mem, u_b, acct) - _dc_beam(rest, ub_out, acct)
                store[acct].append(d)


def run(fn, load_ckpt, want_marginals=False):
    env = build_env()
    rec = env.environment
    U, T = env.config.num_users, env.config.steps_per_episode
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    if load_ckpt:
        tr.load_checkpoint(CKPT, load_optimizers=False)
    bits = 0.0
    joules = {a: 0.0 for a in ACCTS}
    ep_ee = {a: [] for a in ACCTS}
    served = usersteps = ho = 0
    beams_sum = 0.0
    nsteps = 0
    parity_max_abs = 0.0
    marg = {a: [] for a in ACCTS}
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        eb = 0.0
        ej = {a: 0.0 for a in ACCTS}
        for _t in range(T):
            a = fn(tr, enc, masks, states)
            rec.capture.clear()
            res = env.step(a, tr._env_rng)
            if len(rec.capture) != 1:
                raise RuntimeError(
                    f"expected 1 physics evaluation per step, got {len(rec.capture)}"
                )
            cap = rec.capture[0]
            e = env.last_outcome.energy
            # parity: the env's own P^N against my MAX recomputation
            parity_max_abs = max(
                parity_max_abs,
                abs(cap["totals"]["MAX"] - float(e.system_consumed_power_w)),
            )
            eb += float(e.system_throughput_bps) * DT
            for acct in ACCTS:
                ej[acct] += cap["totals"][acct] * DT
            served += int(e.served)
            beams_sum += float(e.eff_beams)
            nsteps += 1
            if want_marginals:
                loo_marginals(cap, marg)
            for uid in range(U):
                usersteps += 1
                if res.rewards[uid].r2_handover < 0:
                    ho += 1
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        bits += eb
        for acct in ACCTS:
            joules[acct] += ej[acct]
            ep_ee[acct].append(eb / ej[acct] if ej[acct] > 0 else float("nan"))
    out = {
        "bits": bits,
        "joules": {a: joules[a] for a in ACCTS},
        "ee": {a: bits / joules[a] for a in ACCTS},
        "sem": {a: st.pstdev(ep_ee[a]) / len(ep_ee[a]) ** 0.5 for a in ACCTS},
        "served": served / usersteps,
        "ho": ho / usersteps,
        "beams": beams_sum / nsteps,
        "parity_max_abs_w": parity_max_abs,
    }
    if want_marginals:
        out["marginals"] = {}
        for a in ACCTS:
            v = sorted(marg[a])
            n = len(v)
            out["marginals"][a] = {
                "n": n,
                "mean_w": st.mean(v) if n else float("nan"),
                "mean_abs_w": st.mean([abs(x) for x in v]) if n else float("nan"),
                "median_w": st.median(v) if n else float("nan"),
                "p10_w": v[int(0.10 * (n - 1))] if n else float("nan"),
                "p90_w": v[int(0.90 * (n - 1))] if n else float("nan"),
                "frac_exact_zero": sum(1 for x in v if x == 0.0) / n if n else float("nan"),
                "frac_negative": sum(1 for x in v if x < 0.0) / n if n else float("nan"),
            }
    return out


def canonical_instance(p_tilde, u_b):
    """One clean reproducible instance: a beam already serving u_b users each
    at p_tilde W gains one more user, also at p_tilde W.  Eligible load rises
    u_b -> u_b + 1, which only the airtime accounting sees."""
    rows = {}
    for a in ACCTS:
        before = _dc_beam([p_tilde] * u_b, float(u_b), a)
        after = _dc_beam([p_tilde] * (u_b + 1), float(u_b + 1), a)
        rows[a] = {"before_w": before, "after_w": after,
                   "delta_w": after - before, "delta_j": (after - before) * DT}
    return rows


