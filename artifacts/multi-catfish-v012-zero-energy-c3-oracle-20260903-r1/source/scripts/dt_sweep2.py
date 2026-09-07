"""Ruling §1.3, cleanly: Delta-t in {1,5,10,30,60} s.  H and beta untouched."""
import collections, datetime as dt, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.action_contract import decode_action
from mcrl.env.antenna import transmit_gain_linear
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.d2 import D2Config
from mcrl.env.ephemeris import EphemerisConfig
from mcrl.env.link_budget import SEGMENT_GAIN_BUDGET_DB
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE

USERS, EPISODES, PASS_S = 60, 8, 378.0
ARCHIVE = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)
TTT_MAX_MS = 5120.0

def gains_of(cand, actions):
    out = np.ones(USERS)
    for u in range(USERS):
        a = int(actions[u])
        if a >= 0:
            l, j = decode_action(a)
            out[u] = float(transmit_gain_linear(np.array([cand.off_axis_deg[u, l, j]]))[0])
    return out

def run(delta_t):
    driver = ScenarioDriver(ARCHIVE, ScenarioConfig(
        ephemeris=EphemerisConfig(time_step_s=delta_t),
        mobility=MobilityConfig(num_users=USERS, time_step_s=delta_t),
        d2=D2Config(time_step_s=delta_t)))
    env = StepEnvironment(driver, physics=PhysicsConfig())
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    rng = np.random.default_rng(0)
    drop, swing, ho, why, outage, steps, valid, seglen = [], [], 0, collections.Counter(), 0, 0, [], []
    for ep in range(EPISODES):
        obs = env.reset(BASE + dt.timedelta(hours=17 * ep), rng)
        policy.reset()
        key0, g0, gprev, track, run_len = {}, {}, {}, {}, {}
        while True:
            actions = policy.act(obs.candidates, rng)
            valid.extend(obs.masks.sum(axis=1).tolist())
            g = gains_of(obs.candidates, actions)
            out = env.step(actions, rng); steps += USERS
            outage += int(np.count_nonzero(out.resolution.outage_infeasible))
            for u in range(USERS):
                served = out.resolution.served[u]
                key = ((int(out.resolution.serving_satellite[u]),
                        int(out.resolution.serving_cell[u])) if served else None)
                if u in key0 and key0[u] is not None and key != key0[u]:
                    drop.append(10*np.log10(g0[u]/max(gprev[u],1e-300)))
                    swing.append(max(track[u]) - min(track[u]))
                    seglen.append(run_len[u])
                    why["handover" if key is not None else
                        ("outage" if out.resolution.outage_infeasible[u] else "unserved")] += 1
                if key is not None and (u not in key0 or key0[u] != key):
                    g0[u], track[u], run_len[u] = g[u], [10*np.log10(g[u])], 1
                elif key is not None:
                    track[u].append(10*np.log10(g[u])); run_len[u] += 1
                key0[u], gprev[u] = key, g[u]
            obs = out.observation
            if out.done:
                for u in range(USERS):
                    if key0.get(u) is not None:
                        drop.append(10*np.log10(g0[u]/max(gprev[u],1e-300)))
                        swing.append(max(track[u]) - min(track[u]))
                        seglen.append(run_len[u]); why["episode reset"] += 1
                break
    return (np.array(drop), np.array(swing), ho or why["handover"],
            why, outage/steps, np.array(valid), np.array(seglen))

rows = []
print(f"{'dt':>4} {'ep_s':>5} {'pass%':>6} | {'signed drop p50':>15} {'|swing| p50':>11} "
      f"{'swing p95':>9} {'%budget':>8} | {'HO/u/ep':>8} | {'outage':>7} {'|A_u|':>6} | TTT")
print("-"*118)
for delta_t in (1.0, 5.0, 10.0, 30.0, 60.0):
    d, sw, ho, why, outage, valid, seglen = run(delta_t)
    ho_rate = why["handover"] / (USERS*EPISODES); ep_s = 10*delta_t
    ttt = "in-set" if delta_t*1000 <= TTT_MAX_MS else f"{delta_t*1000/TTT_MAX_MS:.0f}x over"
    rows.append((delta_t, np.percentile(sw,50), ho_rate, outage))
    print(f"{delta_t:4.0f} {ep_s:5.0f} {100*ep_s/PASS_S:5.1f}% | {np.percentile(d,50):15.4f} "
          f"{np.percentile(sw,50):11.4f} {np.percentile(sw,95):9.4f} "
          f"{100*np.percentile(sw,50)/SEGMENT_GAIN_BUDGET_DB:7.1f}% | {ho_rate:8.3f} | "
          f"{outage:7.4f} {np.percentile(valid,50):6.1f} | {ttt}")
    print(f"     seg len p50 {np.percentile(seglen,50):.0f} steps; ends: "
          + ", ".join(f"{k} {v}" for k,v in why.most_common()))

print("\ncriteria (fixed before the numbers): r1 p50 >= 0.3 dB, HO/u/ep >= 0.5, outage <= 0.05")
print("  read as the MAGNITUDE of the in-segment gain excursion (see note):")
first = None
for delta_t, sw50, hor, outr in rows:
    ok = (sw50 >= 0.3, hor >= 0.5, outr <= 0.05)
    mark = ""
    if all(ok) and first is None:
        first, mark = delta_t, "   <== smallest dt meeting all three"
    print(f"  dt={delta_t:4.0f}  r1 {'PASS' if ok[0] else 'fail'}  "
          f"r2 {'PASS' if ok[1] else 'fail'}  outage {'PASS' if ok[2] else 'fail'}{mark}")
