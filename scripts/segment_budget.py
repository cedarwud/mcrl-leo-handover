"""Item 2c: how long must a segment be before the 3.010 dB budget is spent?"""
import datetime as dt, sys, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE
from mcrl.env.action_contract import decode_action
from mcrl.env.antenna import transmit_gain_linear
from mcrl.env.link_budget import SEGMENT_GAIN_BUDGET_DB

USERS, EPISODES = 100, 10
driver = ScenarioDriver(TleArchive(Path(TLE_ROOT_DEFAULT).expanduser()),
                        ScenarioConfig(mobility=MobilityConfig(num_users=USERS)))
env = StepEnvironment(driver, physics=PhysicsConfig())
policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
rng = np.random.default_rng(0)
base = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)

dtheta, dgain_db, why = [], [], collections.Counter()
seg_len, held = [], {}
for ep in range(EPISODES):
    obs = env.reset(base + dt.timedelta(hours=19 * ep), rng)
    policy.reset()
    prev_theta, prev_gain, prev_key, run = {}, {}, {}, {}
    step = 0
    while True:
        actions = policy.act(obs.candidates, rng); cand = obs.candidates
        out = env.step(actions, rng); step += 1
        for uid in range(USERS):
            a = int(actions[uid])
            served = out.resolution.served[uid]
            key = ((int(out.resolution.serving_satellite[uid]),
                    int(out.resolution.serving_cell[uid])) if served else None)
            if a >= 0:
                l, j = decode_action(a)
                th = float(cand.off_axis_deg[uid, l, j])
                g = float(transmit_gain_linear(np.array([th]))[0])
            else:
                th = g = None
            if uid in prev_key and prev_key[uid] is not None:
                if key == prev_key[uid] and th is not None:
                    dtheta.append(abs(th - prev_theta[uid]))
                    dgain_db.append(10*np.log10(prev_gain[uid]/max(g, 1e-300)))
                    run[uid] = run.get(uid, 1) + 1
                else:
                    seg_len.append(run.get(uid, 1)); run[uid] = 1
                    if not served and int(actions[uid]) < 0:      why["unserved (no-op)"] += 1
                    elif out.resolution.outage_infeasible[uid]:   why["outage (infeasible)"] += 1
                    elif key is not None:                          why["handover"] += 1
                    else:                                          why["other unserved"] += 1
            prev_key[uid], prev_theta[uid], prev_gain[uid] = key, th, g
        obs = out.observation
        if out.done:
            for uid in range(USERS):
                if prev_key.get(uid) is not None:
                    seg_len.append(run.get(uid, 1)); why["episode reset"] += 1
            break

dt_a, dg = np.array(dtheta), np.array(dgain_db)
print(f"samples: {dt_a.size} consecutive in-segment step pairs, {len(seg_len)} segments\n")
print("per-step change while a segment is held:")
print(f"  |d theta|  deg   p50 {np.percentile(dt_a,50):.4f}  p95 {np.percentile(dt_a,95):.4f}  max {dt_a.max():.4f}")
print(f"  d gain     dB    p50 {np.percentile(dg,50):+.4f}  p95 {np.percentile(dg,95):+.4f}  max {dg.max():+.4f}")

pos = dg[dg > 0]
print(f"\n  steps with gain DECREASING: {100*pos.size/dg.size:.1f}%")
for label, rate in (("p50 of decreasing", np.percentile(pos,50)),
                    ("p95 of decreasing", np.percentile(pos,95)),
                    ("max", pos.max())):
    print(f"  at the {label:20s} rate ({rate:.4f} dB/step): "
          f"{SEGMENT_GAIN_BUDGET_DB/rate:9.0f} steps = {SEGMENT_GAIN_BUDGET_DB/rate:8.0f} s "
          f"= {SEGMENT_GAIN_BUDGET_DB/rate/60:6.1f} min")

sl = np.array(seg_len)
print(f"\nsegment length (steps): p50 {np.percentile(sl,50):.0f}  p95 {np.percentile(sl,95):.0f}  max {sl.max()}")
print("why segments ended:")
for k, v in why.most_common():
    print(f"  {k:24s} {v:5d}  {100*v/sum(why.values()):5.1f}%")
