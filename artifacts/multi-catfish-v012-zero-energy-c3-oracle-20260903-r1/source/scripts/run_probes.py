"""Run P4 / P5 / P7 / P2 against an in-memory (unfrozen) PREREG record.

⚠ Does NOT write a frozen PREREG.  The record is built in memory so the
probe gates have something to verify; the real freeze is a separate,
deliberate act.
"""
import datetime as dt, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "src")
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.dwell import DwellConfig
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import build_reference_policy, STAY_IF_POSSIBLE, RANDOM_MASKED
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.runtime.prereg_draft import freeze
from mcrl.runtime.probe_harness import ProbeStreams
from mcrl.runtime.probe_p2 import run_probe_p2
from mcrl.runtime.probe_p4 import run_probe_p4
from mcrl.runtime.probe_p5 import run_probe_p5
from mcrl.runtime.probe_p7 import run_probe_p7

USERS, EPISODES, SEED = 100, 8, 20260823
BASE = dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc)
EPOCHS = [BASE + dt.timedelta(hours=17 * k) for k in range(EPISODES)]
ARCHIVE = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())
RECORD = freeze()
OUT = Path("artifacts"); OUT.mkdir(exist_ok=True)

def env(physics=None, dwell_steps=None):
    cfg = ScenarioConfig(mobility=MobilityConfig(num_users=USERS),
                         **({"dwell": DwellConfig(steps=dwell_steps)} if dwell_steps else {}))
    return StepEnvironment(ScenarioDriver(ARCHIVE, cfg), physics=physics or PhysicsConfig())

def save(name, result):
    (OUT / f"probe-{name}-2026-08-23.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, default=float))

# ---- P4 -----------------------------------------------------------------
p4 = run_probe_p4(prereg=RECORD, policy=build_reference_policy(STAY_IF_POSSIBLE, 7),
                  environment=env(), epochs=EPOCHS, streams=ProbeStreams.spawn(SEED))
save("p4", p4)
print("=== P4  interference ===")
print(f"  radiating beams/step p50      {p4['radiating_beams_per_step']['p50']:.0f}")
print(f"  intra fraction p05/p50/p95    {p4['intra_fraction_of_total']['p05']:.3f} / "
      f"{p4['intra_fraction_of_total']['p50']:.3f} / {p4['intra_fraction_of_total']['p95']:.3f}")
print(f"  I/N dB p05/p50/p95            {p4['interference_to_noise_db']['p05']:.1f} / "
      f"{p4['interference_to_noise_db']['p50']:.1f} / {p4['interference_to_noise_db']['p95']:.1f}")
print(f"  SINR dB with I  p50           {p4['sinr_db']['p50']:.2f}")
print(f"  SINR dB without I p50         {p4['sinr_db_without_co_colour_sum']['p50']:.2f}")
print(f"  cost of interference dB p50   {p4['sinr_cost_of_interference_db']['p50']:.2f}")
print(f"  interference is binding       {p4['interference_is_binding']}")
print(f"  two sats one cell (steps)     {p4['two_satellites_one_cell_step_fraction']:.4f}")

# ---- P5 -----------------------------------------------------------------
p5 = run_probe_p5(prereg=RECORD, policy=build_reference_policy(STAY_IF_POSSIBLE, 7),
                  environment=env(), epochs=EPOCHS, streams=ProbeStreams.spawn(SEED))
save("p5", p5)
print("\n=== P5  receive-angle vs S.465 theta^R_min ===")
print(f"  theta^R_min                   {p5['theta_r_min_deg']:.4f} deg (D = {p5['terminal_diameter_m']} m)")
print(f"  cross-sat terms               {p5['cross_satellite_terms']}  "
      f"(co-sat, excluded: {p5['co_satellite_terms']})")
print(f"  separation deg p05/p50/p95    {p5['separation_deg']['p05']:.2f} / "
      f"{p5['separation_deg']['p50']:.2f} / {p5['separation_deg']['p95']:.2f}")
print(f"  ** frac of EVALUATIONS below  {p5['fraction_of_evaluations_below_theta_r_min']:.4f}")
print(f"  ** frac of POWER below        {p5['fraction_of_interference_power_below_theta_r_min']:.4f}")

# ---- P7, both warm-start arms -------------------------------------------
print("\n=== P7  does anything constrain the action set? ===")
for label, physics in (("main arm", PhysicsConfig()),
                       ("sensitivity", PhysicsConfig(segment_warm_start="uniform-segment-length",
                                                     segment_age_steps=6)),
                       ("no warm start", PhysicsConfig(segment_warm_start="none"))):
    r = run_probe_p7(prereg=RECORD, policy=build_reference_policy(RANDOM_MASKED, 7),
                     environment=env(physics), epochs=EPOCHS, streams=ProbeStreams.spawn(SEED))
    save(f"p7-{label.replace(' ','-')}", r)
    print(f"  {label:14s} |A_u| min/p50 {r['valid_actions_per_user']['min']:.0f}/"
          f"{r['valid_actions_per_user']['p50']:.0f}  mask binding {str(r['mask_is_ever_binding']):5s}"
          f"  outage {r['outage_rate']:.4f}  gate binding {str(r['power_gate_is_binding']):5s}"
          f"  feas budget max {r['feasible_budget_fraction']['max']:.3f}")
print(f"  per-term kills (main arm, mean of 28): slot {r['slots_killed_by_unoccupied_slot']['mean']:.2f}  "
      f"cell {r['slots_killed_by_absent_cell']['mean']:.2f}  reach {r['slots_killed_by_unreachable_cell']['mean']:.2f}")

# ---- P2 -----------------------------------------------------------------
p2 = run_probe_p2(prereg=RECORD,
                  policy_factory=lambda: build_reference_policy(STAY_IF_POSSIBLE, 7),
                  environment_factory=lambda n: env(dwell_steps=n),
                  epochs=EPOCHS, seed=SEED)
save("p2", p2)
print("\n=== P2  dwell N sensitivity ===")
for name, arm in p2["arms"].items():
    print(f"  {name}  P^N swing {arm['system_power_swing_w']:7.2f} W   "
          f"EE dyn range {arm['angle_aware_ee_dynamic_range']:.3e}   "
          f"rekey {arm['rekey_rate']:.5f}   HO/dec {arm['handover_rate_per_decision']:.4f}")
print("\nartifacts written to artifacts/")
