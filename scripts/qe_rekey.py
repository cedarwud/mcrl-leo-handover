"""The decisive number for Q-E: the measured re-key rate."""
import datetime as dt, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.d2 import D2Config
from mcrl.env.dwell import DwellConfig
from mcrl.env.ephemeris import EphemerisConfig
from mcrl.env.mobility import MobilityConfig
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.tle import TleArchive

USERS, EPISODES = 60, 8
ARCHIVE = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)

print(f"{'dt':>4} | " + " | ".join(f"N={n}: rekeys/boundary" for n in (2,3,4)))
print("-"*70)
for delta_t in (1.0, 5.0, 10.0, 30.0, 60.0):
    cells = []
    for n in (2, 3, 4):
        driver = ScenarioDriver(ARCHIVE, ScenarioConfig(
            ephemeris=EphemerisConfig(time_step_s=delta_t),
            mobility=MobilityConfig(num_users=USERS, time_step_s=delta_t),
            d2=D2Config(time_step_s=delta_t), dwell=DwellConfig(steps=n)))
        rng = np.random.default_rng(0)
        rekeys = boundaries = 0
        for ep in range(EPISODES):
            cand = driver.reset(BASE + dt.timedelta(hours=17*ep), rng)
            for _ in range(driver.config.steps_per_episode - 1):
                cand = driver.step(rng)
                if cand.dwell.is_boundary:
                    boundaries += USERS
                    rekeys += cand.dwell.rekey_count
        cells.append(f"{rekeys:5d}/{boundaries:6d} = {rekeys/max(boundaries,1):.5f}")
    print(f"{delta_t:4.0f} | " + " | ".join(cells))
