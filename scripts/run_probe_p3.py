"""Run P3 against a freshly built (unfrozen-content) PREREG record.

⚠ This does NOT write a frozen PREREG to disk.  It builds the record in
memory so P3's gate has something to verify, runs the probe, and prints the
result.  The real freeze is a separate deliberate act (W-24 §4 order).
"""
import datetime as dt, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.prereg_draft import freeze
from mcrl.runtime.probe_p3 import run_probe_p3

USERS, EPISODES = 100, 12
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)
epochs = [BASE + dt.timedelta(hours=17 * k) for k in range(EPISODES)]

record = freeze()                      # in memory only
driver = ScenarioDriver(TleArchive(Path(TLE_ROOT_DEFAULT).expanduser()),
                        ScenarioConfig(mobility=MobilityConfig(num_users=USERS)))
env = StepEnvironment(driver, physics=PhysicsConfig())
policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)

result = run_probe_p3(
    prereg=record, policy=policy, environment=env, epochs=epochs,
    env_rng=np.random.default_rng(0),
    mobility_rng=np.random.default_rng(1000),
    action_rng=np.random.default_rng(2000),
)
for key in ("decision_steps", "degenerate_step_fraction",
            "r1_r3_argmax_agreement_rate", "argmax_comparisons",
            "qd_scale_p95_rounded", "r1_r3_step_correlation"):
    print(f"{key:32s} {result[key]}")
print()
for key in ("candidate_load_width", "candidate_load_distinct_values",
            "abs_r3_over_served_steps"):
    q = result[key]
    print(f"{key:32s} p05 {q['p05']:.2f}  p50 {q['p50']:.2f}  "
          f"p95 {q['p95']:.2f}  max {q['max']:.2f}  mean {q['mean']:.3f}")
print()
for key in ("r1", "r2", "r3"):
    q = result[key]
    print(f"{key:32s} p05 {q['p05']:.4g}  p50 {q['p50']:.4g}  "
          f"p95 {q['p95']:.4g}  mean {q['mean']:.4g}")
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/probe-p3-2026-08-23.json").write_text(
    json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
print("\nwritten: artifacts/probe-p3-2026-08-23.json")
