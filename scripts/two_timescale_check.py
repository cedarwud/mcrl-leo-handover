"""(C) is live: verify the clocks and measure the real 47-sub-step cost."""
import datetime as dt, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import (D2_MEASUREMENT_STEP_S, D2_SUBSTEPS_PER_DECISION,
                                DECISION_STEP_S, TLE_ROOT_DEFAULT)
from mcrl.env.d2 import D2Config
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE

d2 = D2Config()
print(f"measurement clock   {D2_MEASUREMENT_STEP_S*1000:.0f} ms")
print(f"sub-steps/decision  {D2_SUBSTEPS_PER_DECISION}")
print(f"decision clock      {DECISION_STEP_S:.2f} s")
print(f"TTT                 {d2.ttt_steps} substeps = {d2.ttt_steps*D2_MEASUREMENT_STEP_S*1000:.0f} ms")
TTT_SET = (0,40,64,80,100,128,160,256,320,480,512,640,1024,1280,2560,5120)
ttt_ms = d2.ttt_steps*D2_MEASUREMENT_STEP_S*1000
print(f"in TS 38.331 set?   {'YES (exact)' if round(ttt_ms) in TTT_SET else 'NO'}\n")

for users in (20, 100):
    driver = ScenarioDriver(TleArchive(Path(TLE_ROOT_DEFAULT).expanduser()),
                            ScenarioConfig(mobility=MobilityConfig(num_users=users)))
    env = StepEnvironment(driver, physics=PhysicsConfig())
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    rng = np.random.default_rng(0)
    t0 = time.perf_counter()
    obs = env.reset(dt.datetime(2026,8,8,6,0,tzinfo=dt.timezone.utc), rng)
    policy.reset()
    while True:
        out = env.step(policy.act(obs.candidates, rng), rng)
        obs = out.observation
        if out.done:
            break
    dt_s = time.perf_counter()-t0
    print(f"U={users:3d}  one episode: {dt_s:5.2f} s   "
          f"=> 9000 episodes = {dt_s*9000/3600:5.2f} h   "
          f"(tracked satellites: {driver.tracked_norad_ids.size})")
