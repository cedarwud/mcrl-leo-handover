"""Outage and mask attrition under the FROZEN scenario (dt=30.08 s, warm start)."""
import datetime as dt, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import TLE_ROOT_DEFAULT, DECISION_STEP_S
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE

USERS, EPISODES = 100, 12
ARCHIVE = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)
for label, cfg in (("warm start ON (frozen)", PhysicsConfig()),
                   ("warm start OFF", PhysicsConfig(segment_warm_start="none"))):
    driver = ScenarioDriver(ARCHIVE, ScenarioConfig(mobility=MobilityConfig(num_users=USERS)))
    env = StepEnvironment(driver, physics=cfg)
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    # Three independent streams, matching what MODQNTrainer supplies:
    # env_rng (fading), mobility_rng (users), and the policy's own draw.
    # With one generator a fading change shifts the users and the entry
    # ages too, and nothing measured here is an ablation of one thing.
    rng = np.random.default_rng(0)
    mob = np.random.default_rng(1000)
    act = np.random.default_rng(2000)
    tot = dict(steps=0, served=0, outage=0, noop=0); sinr=[]; valid=[]; pw=[]
    for ep in range(EPISODES):
        obs = env.reset(BASE + dt.timedelta(hours=17*ep), rng, mobility_rng=mob)
        policy.reset()
        while True:
            valid.extend(obs.masks.sum(axis=1).tolist())
            out = env.step(policy.act(obs.candidates, act), rng)
            r = out.resolution
            tot["steps"] += USERS; tot["served"] += r.served_count
            tot["outage"] += int(np.count_nonzero(r.outage_infeasible))
            tot["noop"] += int(np.count_nonzero(r.no_op_users))
            if r.served.any():
                sinr += (10*np.log10(out.link_sinr[r.served])).tolist()
                pw += out.link_power_w[r.served].tolist()
            obs = out.observation
            if out.done: break
    n = tot["steps"]; s = np.array(sinr); v = np.array(valid); q = np.array(pw)
    print(f"--- {label}   ({n} decision steps, dt={DECISION_STEP_S:.2f} s)")
    print(f"    served {tot['served']/n:.4f}   outage {tot['outage']/n:.4f}   "
          f"no-op {tot['noop']/n:.4f}")
    print(f"    |A_u| p05/p50 {np.percentile(v,5):.1f}/{np.percentile(v,50):.1f}   "
          f"link power p50/p95/max {np.percentile(q,50):.3f}/{np.percentile(q,95):.3f}/{q.max():.3f} W")
    print(f"    SINR dB p05/p50/p95 {np.percentile(s,5):.1f}/{np.percentile(s,50):.1f}/{np.percentile(s,95):.1f}\n")
