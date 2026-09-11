"""EEGAP bridge: score this project's MODQN harness on the SIBLING's estimand.

READ-ONLY / NO TRAINING: update() is never called; the trained arm LOADS the
frozen checkpoint read-only; src/ is never edited or patched.

Arms: RANDOM_MASKED, TRAINED e6b063ef (greedy eps=0). 24 episodes each, frozen
seeds 42/1337/7, a FRESH environment per arm (matches the anchor-ablation
placebo construction, which reproduced RANDOM 53,060,175.561473 bit-identically
and TRAINED at 93,110,907.973748).

Estimands computed on the SAME rollouts (all from env.last_outcome, not rebuilt
from reward fields):

  A  POOLED_CONSUMED  sum_t sum_u R_u dt / sum_t P^N dt          (this project)
  B  POOLED_RF        sum_t sum_u R_u dt / sum_t sum_b p_b dt    (radiated only)
  C  SIB_JULY_RF      mean_ep mean_t mean_u eta_u,  eta_u = R_u / (p_b / N_b)
                      (0 for unserved) -- the sibling's family_b_eta_r1 as of
                      commit 211a71a3 (2026-07-04 .. 2026-08-05), the scorer
                      score_argmax_endpoint.py:110,119,120,121 -- then / 1e6.
  C' SIB_JULY_CONS    same, but beam power -> this project's consumed per-beam
                      power  p_b/xi(p_b) + P_cir + P_BB / (beams on that sat)
  D  SIB_NOW          mean_ep mean_t mean_u (R_u / P^N)  = system EE / U
                      (the sibling's CURRENT family_b_system_ee_contribution)
  E  STEP_MEAN_CONS   mean over steps of (sum_u R_u / P^N)
  F  STEP_MEAN_RF     mean over steps of (sum_u R_u / sum_b p_b)
"""
import math
import statistics as st
import sys
import time

sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")

import numpy as np
import torch

torch.set_num_threads(1)

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.env.constants import DECISION_STEP_S
from mcrl.env.link_budget import (
    BASEBAND_POWER_PER_SATELLITE_W,
    BEAM_BANDWIDTH_HZ,
    CIRCUIT_POWER_PER_BEAM_W,
    pa_efficiency,
    supply_power_w,
)
from mcrl.runtime.trainer_spec import TrainerConfig
from mcrl.runtime.training_pipeline import make_training_environment

DT = float(DECISION_STEP_S)
N_EP = 24
CKPT = ("/home/u24/papers/mcrl-leo-handover/artifacts/"
        "training-2026-08-25-rerun01/main/final-checkpoint.pt")
cfg = TrainerConfig(learning_rate=0.001, episodes=1)


def arm_random(tr, enc, masks):
    return tr.select_actions(enc, masks, 1.0)


def arm_trained(tr, enc, masks):
    return tr.select_actions(enc, masks, 0.0)


def run(fn, load_ckpt):
    env = make_training_environment(users=100)
    U, T = env.config.num_users, env.config.steps_per_episode
    tr = MODQNTrainer(env, cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    if load_ckpt:
        tr.load_checkpoint(CKPT, load_optimizers=False)
    acc = dict(bits=0.0, joules=0.0, rf_joules=0.0, supply_j=0.0, fixed_j=0.0)
    ep_rows = []
    step_rows = []
    max_abs_checks = dict(pn=0.0, thr=0.0, load=0)
    for _ in range(N_EP):
        states, masks, _ = env.reset(tr._env_rng, tr._mobility_rng)
        enc = tr._encode_states(states)
        ep_c, ep_cc, ep_d = [], [], []
        for _t in range(T):
            a = fn(tr, enc, masks)
            res = env.step(a, tr._env_rng)
            o = env.last_outcome
            e = o.energy
            rs = o.resolution
            rad = o.radiating
            p_b = np.asarray(rad.power_w, dtype=np.float64)
            nor = np.asarray(rad.norad_ids, dtype=np.int64)
            cel = np.asarray(rad.cell_ids, dtype=np.int64)
            idx = {(int(n), int(c)): i for i, (n, c) in enumerate(zip(nor, cel))}
            xi = pa_efficiency(p_b)
            sup = supply_power_w(p_b, xi)
            sat_ids, sat_counts = np.unique(nor, return_counts=True)
            per_sat = dict(zip(sat_ids.tolist(), sat_counts.tolist()))
            p_cons_b = np.array([
                sup[i] + CIRCUIT_POWER_PER_BEAM_W
                + BASEBAND_POWER_PER_SATELLITE_W / per_sat[int(nor[i])]
                for i in range(p_b.size)])
            PN = float(o.system_power_w)
            rate = np.asarray(o.link_rate_bps, dtype=np.float64)
            sinr = np.asarray(o.link_sinr, dtype=np.float64)
            served = np.asarray(rs.served, dtype=bool)
            # consistency checks against the env's own accounting
            max_abs_checks["pn"] = max(max_abs_checks["pn"], abs(PN - float(e.system_consumed_power_w)),
                                       abs(PN - (float(o.fixed_power_w) + float(sup.sum()))))
            max_abs_checks["thr"] = max(max_abs_checks["thr"], abs(float(rate.sum()) - float(e.system_throughput_bps)))
            eta_rf = np.zeros(U); eta_cons = np.zeros(U); se = []
            loads_seen = {}
            for u in range(U):
                if not served[u]:
                    continue
                key = (int(rs.serving_satellite[u]), int(rs.serving_cell[u]))
                b = idx[key]
                N = float(rs.eligible_load_by_beam[key])
                loads_seen[key] = loads_seen.get(key, 0) + 1
                eta_rf[u] = rate[u] * N / p_b[b]
                eta_cons[u] = rate[u] * N / p_cons_b[b]
                se.append(math.log2(1.0 + sinr[u]))
            for key, n in loads_seen.items():
                if n != int(rs.eligible_load_by_beam[key]):
                    max_abs_checks["load"] += 1
            thr = float(rate.sum())
            acc["bits"] += thr * DT
            acc["joules"] += PN * DT
            acc["rf_joules"] += float(p_b.sum()) * DT
            acc["supply_j"] += float(sup.sum()) * DT
            acc["fixed_j"] += float(o.fixed_power_w) * DT
            ep_c.append(float(eta_rf.mean()))
            ep_cc.append(float(eta_cons.mean()))
            ep_d.append((thr / PN) / U if PN > 0 else 0.0)
            step_rows.append(dict(
                beams=int(p_b.size), sats=int(sat_ids.size), served=int(served.sum()),
                load=float(served.sum()) / max(p_b.size, 1),
                p_b=float(p_b.mean()) if p_b.size else 0.0,
                sup_b=float(sup.mean()) if p_b.size else 0.0,
                xi=float(xi.mean()) if p_b.size else 0.0,
                se=float(np.mean(se)) if se else 0.0,
                ee_cons=thr / PN if PN > 0 else 0.0,
                ee_rf=thr / float(p_b.sum()) if p_b.sum() > 0 else 0.0,
                pn=PN, thr=thr))
            states = res.user_states
            enc = tr._encode_states(states)
            masks = res.action_masks
            if res.done:
                break
        ep_rows.append(dict(c=st.mean(ep_c), cc=st.mean(ep_cc), d=st.mean(ep_d)))
    out = dict(
        A_pooled_consumed=acc["bits"] / acc["joules"],
        B_pooled_rf=acc["bits"] / acc["rf_joules"],
        C_sib_july_rf=st.mean(r["c"] for r in ep_rows),
        Cp_sib_july_cons=st.mean(r["cc"] for r in ep_rows),
        D_sib_now=st.mean(r["d"] for r in ep_rows),
        E_step_mean_cons=st.mean(r["ee_cons"] for r in step_rows),
        F_step_mean_rf=st.mean(r["ee_rf"] for r in step_rows),
        C_ep_sd=st.pstdev([r["c"] for r in ep_rows]),
        pa_share=acc["supply_j"] / acc["joules"],
        fixed_share=acc["fixed_j"] / acc["joules"],
        consumed_over_rf=acc["joules"] / acc["rf_joules"],
        checks=max_abs_checks,
    )
    for k in ("beams", "sats", "served", "load", "p_b", "sup_b", "xi", "se", "pn", "thr"):
        out["mean_" + k] = st.mean(r[k] for r in step_rows)
    return out


t0 = time.time()
print(f"# EEGAP bridge. N_EP={N_EP}/arm, seeds 42/1337/7, fresh env per arm, dt={DT} s, no update().")
print(f"# B/3 = {BEAM_BANDWIDTH_HZ:.6e} Hz, P_cir = {CIRCUIT_POWER_PER_BEAM_W} W, P_BB = {BASEBAND_POWER_PER_SATELLITE_W} W")
res = {}
for name, fn, ck in (("RANDOM_MASKED", arm_random, False), ("TRAINED_e6b063ef", arm_trained, True)):
    t1 = time.time()
    o = run(fn, ck)
    res[name] = o
    print(f"\n## {name}  (wall {time.time() - t1:.1f} s)")
    for k, v in o.items():
        if isinstance(v, float):
            print(f"  {k:22s} {v:.9e}")
        else:
            print(f"  {k:22s} {v}")
    print(f"  -> A [Mbit/J] {o['A_pooled_consumed']/1e6:.4f} | B {o['B_pooled_rf']/1e6:.4f} | "
          f"C (sibling-July argmax_EE) {o['C_sib_july_rf']/1e6:.4f} | C' {o['Cp_sib_july_cons']/1e6:.4f} | "
          f"D (sibling-now argmax_EE) {o['D_sib_now']/1e6:.6f}")
    print(f"  -> B/A {o['B_pooled_rf']/o['A_pooled_consumed']:.4f} | C/B {o['C_sib_july_rf']/o['B_pooled_rf']:.4f} | "
          f"C/(served_frac*B) {o['C_sib_july_rf']/((o['mean_served']/100)*o['B_pooled_rf']):.4f} | "
          f"C/A {o['C_sib_july_rf']/o['A_pooled_consumed']:.4f} | C'/A {o['Cp_sib_july_cons']/o['A_pooled_consumed']:.4f}")
print(f"\n# total wall {time.time() - t0:.1f} s")
