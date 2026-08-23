"""W-21 §3: the sensitivity arm at the corrected L = 6.

Not a probe -- frozen constants, no reward threshold, no training, no P1
output consumed.  Scenario characterisation, same as the main-arm run.
"""
import datetime as dt, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import DECISION_STEP_S, TLE_ROOT_DEFAULT
from mcrl.env.link_budget import SEGMENT_GAIN_BUDGET_DB
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE

USERS, EPISODES = 100, 12
ARCHIVE = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)
B = SEGMENT_GAIN_BUDGET_DB

ARMS = (
    ("main arm      Uniform{0..H-1}, H=10", PhysicsConfig()),
    ("sensitivity   Uniform{0..L-1}, L=6",
     PhysicsConfig(segment_warm_start="uniform-segment-length",
                   segment_age_steps=6)),
    ("(reference)   no warm start",
     PhysicsConfig(segment_warm_start="none")),
)
print(f"{'arm':38s} {'mean age':>9} | {'outage':>14} | {'feasible max W':>15} "
      f"{'%budget':>8} | {'infeasible p50':>14}")
print("-"*108)
for label, cfg in ARMS:
    driver = ScenarioDriver(ARCHIVE, ScenarioConfig(mobility=MobilityConfig(num_users=USERS)))
    env = StepEnvironment(driver, physics=cfg)
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    rng = np.random.default_rng(0)
    feas, infeas, ages = [], [], []
    steps = outage = 0
    for ep in range(EPISODES):
        obs = env.reset(BASE + dt.timedelta(hours=17*ep), rng); policy.reset()
        if env._pending_segment_age is not None:
            ages += list(env._pending_segment_age)
        while True:
            out = env.step(policy.act(obs.candidates, rng), rng)
            r = out.resolution
            steps += USERS; outage += int(np.count_nonzero(r.outage_infeasible))
            feas += out.link_power_w[r.served].tolist()
            infeas += out.link_power_w[r.outage_infeasible].tolist()
            obs = out.observation
            if out.done: break
    f = np.array(feas); i = np.array(infeas)
    p0 = cfg.segment_start_power_w
    mean_age = np.mean(ages) if ages else 0.0
    inf_txt = f"{np.percentile(i,50):.4f} W" if i.size else "-"
    print(f"{label:38s} {mean_age:9.2f} | {outage:5d}/{steps} {outage/steps:6.4f} | "
          f"{f.max():15.4f} {100*10*np.log10(f.max()/p0)/B:7.1f}% | {inf_txt:>14}")
