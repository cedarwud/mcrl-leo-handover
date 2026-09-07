"""SUPERSEDED by ceiling_and_segments.py -- see the warning below.

Ruling §5: the SIGNED in-segment gain drop at Delta-t = 30 s.

⚠ Its "peak drop" is 10log10(g0/g_t) with g0 the gain at the step the
segment was first SEEN inside the episode.  That was the segment start
until segments began being warm-started; afterwards the true tau is before
the episode and this quantity under-reports the recurrence.  It produced
88.1% where the authoritative figure -- 10log10(p/p0) from the link power
the environment actually computed -- is 100.0%.  Kept so the discrepancy
can be reproduced, not for use.

Distinguishes "the ceiling is satisfied by the policy" from "the ceiling is
never approached at all" -- which read differently in the paper.
"""
import datetime as dt, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.action_contract import decode_action
from mcrl.env.antenna import transmit_gain_linear
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.ephemeris import EphemerisConfig
from mcrl.env.link_budget import SEGMENT_GAIN_BUDGET_DB
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE

USERS, EPISODES = 60, 12
ARCHIVE = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)

from mcrl.env.constants import DECISION_STEP_S
for label, cfg in (("frozen scenario, warm start ON", PhysicsConfig()),
                   ("same, warm start OFF (cold p(0) = p0)",
                    PhysicsConfig(segment_warm_start="none"))):
    delta_t = DECISION_STEP_S
    driver = ScenarioDriver(ARCHIVE, ScenarioConfig(
        mobility=MobilityConfig(num_users=USERS)))
    env = StepEnvironment(driver, physics=cfg)
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    rng = np.random.default_rng(0)
    drop, peak, pmax = [], [], []
    for ep in range(EPISODES):
        obs = env.reset(BASE + dt.timedelta(hours=17*ep), rng)
        policy.reset()
        key0, g0, track, ptrack = {}, {}, {}, {}
        while True:
            actions = policy.act(obs.candidates, rng); cand = obs.candidates
            out = env.step(actions, rng)
            for u in range(USERS):
                served = out.resolution.served[u]
                key = ((int(out.resolution.serving_satellite[u]),
                        int(out.resolution.serving_cell[u])) if served else None)
                a = int(actions[u])
                g = 1.0
                if a >= 0:
                    l, j = decode_action(a)
                    g = float(transmit_gain_linear(np.array([cand.off_axis_deg[u,l,j]]))[0])
                if u in key0 and key0[u] is not None and key != key0[u]:
                    drop.append(10*np.log10(g0[u]/max(track[u][-1],1e-300)))
                    peak.append(max(10*np.log10(g0[u]/max(x,1e-300)) for x in track[u]))
                    pmax.append(max(ptrack[u]))
                if key is not None and (u not in key0 or key0[u] != key):
                    g0[u], track[u], ptrack[u] = g, [g], [float(out.link_power_w[u])]
                elif key is not None:
                    track[u].append(g); ptrack[u].append(float(out.link_power_w[u]))
                key0[u] = key
            obs = out.observation
            if out.done:
                for u in range(USERS):
                    if key0.get(u) is not None:
                        drop.append(10*np.log10(g0[u]/max(track[u][-1],1e-300)))
                        peak.append(max(10*np.log10(g0[u]/max(x,1e-300)) for x in track[u]))
                        pmax.append(max(ptrack[u]))
                break
    d, pk, pm = np.array(drop), np.array(peak), np.array(pmax)
    B = SEGMENT_GAIN_BUDGET_DB
    print(f"=== {label}   Delta-t = {delta_t:.2f} s   ({d.size} segments) ===")
    print(f"  signed end-of-segment drop, dB   p50 {np.percentile(d,50):+7.4f}  "
          f"p95 {np.percentile(d,95):+7.4f}  max {d.max():+7.4f}   "
          f"({100*d.max()/B:.1f}% of the {B:.3f} dB budget)")
    print(f"  PEAK drop reached within a seg    p50 {np.percentile(pk,50):+7.4f}  "
          f"p95 {np.percentile(pk,95):+7.4f}  max {pk.max():+7.4f}   "
          f"({100*pk.max()/B:.1f}% of budget)")
    print(f"  peak link power reached, W        p50 {np.percentile(pm,50):7.4f}  "
          f"p95 {np.percentile(pm,95):7.4f}  max {pm.max():7.4f}   (p_max = 1.65)")
    print(f"  fraction of segments whose peak drop exceeded 50% of budget: "
          f"{np.mean(pk > 0.5*B):.4f}")
    print(f"  fraction that exceeded 90%:  {np.mean(pk > 0.9*B):.4f}\n")
