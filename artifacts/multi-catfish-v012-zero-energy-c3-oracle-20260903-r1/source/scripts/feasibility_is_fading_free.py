"""W-22 §4: is the feasibility verdict independent of the fading draw?

Required power is p0 * G(tau)/G(t) -- transmit pattern only.  L_s and the
Rician gain live in H, which enters the SINR, not the recurrence.  So the
outage count should be identical with fading on and off, given the same
seed: segment ages are drawn at reset BEFORE any fading draw, so switching
fading off cannot shift the age stream either.

If that holds, 95/12000 is reproducible for a fixed geometry and ch5 may
quote it as such.
"""
import datetime as dt, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE

USERS, EPISODES = 100, 12
ARCHIVE = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)

def run(cfg, seed):
    driver = ScenarioDriver(ARCHIVE, ScenarioConfig(mobility=MobilityConfig(num_users=USERS)))
    env = StepEnvironment(driver, physics=cfg)
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    # Three independent streams.  With one, turning fading off also shifts
    # the mobility and the ages, and the "ablation" stops being one.
    rng = np.random.default_rng(seed)
    mob = np.random.default_rng(seed + 1000)
    act = np.random.default_rng(seed + 2000)
    outage = steps = 0; ages = []; sinr = []
    for ep in range(EPISODES):
        obs = env.reset(BASE + dt.timedelta(hours=17*ep), rng, mobility_rng=mob)
        policy.reset()
        ages += list(env._pending_segment_age)
        while True:
            out = env.step(policy.act(obs.candidates, act), rng)
            r = out.resolution
            steps += USERS; outage += int(np.count_nonzero(r.outage_infeasible))
            if r.served.any():
                sinr += out.link_sinr[r.served].tolist()
            obs = out.observation
            if out.done: break
    return outage, steps, np.array(ages), np.array(sinr)

on  = run(PhysicsConfig(), 0)
off = run(PhysicsConfig(fading_enabled=False), 0)
print(f"fading ON   outage {on[0]}/{on[1]}   mean age {on[2].mean():.4f}   "
      f"median SINR {np.median(on[3]):.6g}")
print(f"fading OFF  outage {off[0]}/{off[1]}   mean age {off[2].mean():.4f}   "
      f"median SINR {np.median(off[3]):.6g}")
print()
print(f"segment ages identical:   {np.array_equal(on[2], off[2])}")
print(f"outage count identical:   {on[0] == off[0]}")
print(f"SINR distribution moved:  {not np.allclose(np.median(on[3]), np.median(off[3]))}")
print()
if on[0] == off[0] and np.array_equal(on[2], off[2]):
    print("=> CONFIRMED: the feasibility verdict does not see the fading draw.")
    print("   95/12000 is reproducible for a fixed geometry, as ch5 assumes.")
else:
    print("=> NOT confirmed -- report to the controller.")
