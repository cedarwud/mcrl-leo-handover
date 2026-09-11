"""CF3REVIEW probe (read-only, no training): how much can the equal-share energy
label move ONE user's myopic argmax, compared with its own bits?

For each step of a few calibration episodes under MAX_NOMINAL_GAIN, for a
sample of users, score every legal alternative of that user with the
counterfactual evaluate_actions (CRN), others fixed.  In the CF learner's
normalised units (eta~ = 1 at eta_0):
  own_dB(a) = (R_u(a) - R_u(base)) * dt / s_B
  own_dE(a) = (P(a) - P(base)) * dt / U / s_E        (the user's own E_u label)
  sys_dB(a) = (sum R(a) - sum R(base)) * dt / s_B    (all users' bits)
  sys_dE(a) = (P(a) - P(base)) * dt / s_E            (all users' joules)
Reports spreads and how often argmax_a[own_dB - own_dE] != argmax_a own_dB,
and how often argmax_a[own] != argmax_a[sys_dB - sys_dE].
"""
import os
import sys

sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover-cf3/src")
sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover-cf3/scripts")
os.environ.setdefault("MCRL_TLE_ROOT", "/home/u24/mcrl-runtime/tle-pinned-427e6a91")

import numpy as np  # noqa: E402

import cf3_common as C  # noqa: E402
from mcrl.algorithms import cf_sources as cfs  # noqa: E402
from mcrl.algorithms.cf_ratio import DT_S  # noqa: E402

S_B = 13_329_082_278.45065
S_E = 120.61728174105066
EPISODES = int(sys.argv[1]) if len(sys.argv) > 1 else 2
USERS_PER_STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 15

factory = C.env_factory()
own_b, own_e, flip_own, flip_sys, n_dec = [], [], 0, 0, 0
flip_sys_vs_bits = 0
for env_seed, mob_seed in C.cal_seeds(EPISODES):
    env = factory()
    U = env.config.num_users
    er, mr = np.random.default_rng(env_seed), np.random.default_rng(mob_seed)
    states, masks, _ = env.reset(er, mr)
    pick_rng = np.random.default_rng(env_seed + 5)
    for _t in range(env.config.steps_per_episode):
        acts = cfs.max_nominal_gain(states, masks)
        base = env.environment.evaluate_actions(acts, er)
        rb = np.array([r.r1_throughput for r in base.rewards])
        pb = float(base.energy.system_consumed_power_w)
        cand = [u for u in range(U) if masks[u].mask.sum() >= 2]
        for u in pick_rng.choice(cand, size=min(USERS_PER_STEP, len(cand)), replace=False):
            legal = np.flatnonzero(masks[u].mask)
            ob, oe, sb, se = [], [], [], []
            for a in legal:
                alt = np.array(acts, copy=True)
                alt[u] = a
                ev = env.environment.evaluate_actions(alt, er)
                r = np.array([x.r1_throughput for x in ev.rewards])
                p = float(ev.energy.system_consumed_power_w)
                ob.append((r[u] - rb[u]) * DT_S / S_B)
                oe.append((p - pb) * DT_S / U / S_E)
                sb.append((r.sum() - rb.sum()) * DT_S / S_B)
                se.append((p - pb) * DT_S / S_E)
            ob, oe, sb, se = map(np.array, (ob, oe, sb, se))
            own_b.append(ob.max() - ob.min())
            own_e.append(oe.max() - oe.min())
            n_dec += 1
            flip_own += int(np.argmax(ob - oe) != np.argmax(ob))
            flip_sys += int(np.argmax(ob - oe) != np.argmax(sb - se))
            flip_sys_vs_bits += int(np.argmax(ob) != np.argmax(sb - se))
        res = env.step(acts, er)
        states, masks = res.user_states, res.action_masks

own_b, own_e = np.array(own_b), np.array(own_e)
print(f"decisions sampled: {n_dec}")
print("spread over legal actions of own_dB (normalised bits): median %.4f  p90 %.4f"
      % (np.median(own_b), np.quantile(own_b, 0.9)))
print("spread over legal actions of own_dE (normalised, eta~=1): median %.5f  p90 %.5f  max %.5f"
      % (np.median(own_e), np.quantile(own_e, 0.9), own_e.max()))
print("median ratio own_dE spread / own_dB spread: %.4f"
      % np.median(own_e / np.maximum(own_b, 1e-12)))
print(f"myopic argmax changed by the E term (own B vs own B-E): {flip_own}/{n_dec} = {flip_own / n_dec:.3f}")
print(f"per-user objective argmax != system objective argmax (one-step): {flip_sys}/{n_dec} = {flip_sys / n_dec:.3f}")
print(f"own-bits argmax != system objective argmax (one-step): {flip_sys_vs_bits}/{n_dec} = {flip_sys_vs_bits / n_dec:.3f}")
