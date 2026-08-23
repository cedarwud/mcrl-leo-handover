"""W-20: the budget fraction taken from the link power itself, and why
segments end.

The earlier peak-drop figure measured 10log10(G(start of episode)/G(t)).
Once segments are warm-started that is no longer the segment start, so it
under-reports the recurrence.  The authoritative quantity is the link power
the environment actually computed: 10log10(p/p0) IS the consumed budget.
"""
import collections, datetime as dt, sys
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

for label, cfg in (("warm start ON  (main arm)", PhysicsConfig()),
                   ("warm start OFF (sensitivity reference)",
                    PhysicsConfig(segment_warm_start="none"))):
    driver = ScenarioDriver(ARCHIVE, ScenarioConfig(mobility=MobilityConfig(num_users=USERS)))
    env = StepEnvironment(driver, physics=cfg)
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    rng = np.random.default_rng(0)
    feasible_p, infeasible_p, why, seglen = [], [], collections.Counter(), []
    by_reason = collections.defaultdict(list)
    steps = outage = 0
    for ep in range(EPISODES):
        obs = env.reset(BASE + dt.timedelta(hours=17*ep), rng); policy.reset()
        key0, run = {}, {}
        while True:
            out = env.step(policy.act(obs.candidates, rng), rng)
            r = out.resolution
            steps += USERS; outage += int(np.count_nonzero(r.outage_infeasible))
            feasible_p += out.link_power_w[r.served].tolist()
            infeasible_p += out.link_power_w[r.outage_infeasible].tolist()
            for u in range(USERS):
                served = r.served[u]
                key = ((int(r.serving_satellite[u]), int(r.serving_cell[u]))
                       if served else None)
                if u in key0 and key0[u] is not None and key != key0[u]:
                    seglen.append(run.get(u, 1))
                    reason = ("handover" if key is not None else
                              ("outage" if r.outage_infeasible[u] else
                               ("no-op / unserved"
                                if int(out.observation.masks[u].sum()) == 0
                                else "unserved")))
                    why[reason] += 1
                    by_reason[reason].append(run.get(u, 1))
                run[u] = 1 if (key is None or key0.get(u) != key) else run.get(u, 1) + 1
                key0[u] = key
            obs = out.observation
            if out.done:
                for u in range(USERS):
                    if key0.get(u) is not None:
                        seglen.append(run.get(u, 1)); why["episode reset"] += 1
                        by_reason["episode reset"].append(run.get(u, 1))
                break
    f = np.array(feasible_p); i = np.array(infeasible_p); sl = np.array(seglen)
    p0, pmax = cfg.segment_start_power_w, cfg.beam_power_max_w
    print(f"=== {label}   dt = {DECISION_STEP_S:.2f} s ===")
    print(f"  outage {outage}/{steps} = {outage/steps:.4f}")
    print(f"  FEASIBLE link power W   p50 {np.percentile(f,50):.4f}  "
          f"p95 {np.percentile(f,95):.4f}  max {f.max():.4f}   (p_max = {pmax})")
    print(f"    => budget consumed     p50 {100*10*np.log10(np.percentile(f,50)/p0)/B:5.1f}%  "
          f"p95 {100*10*np.log10(np.percentile(f,95)/p0)/B:5.1f}%  "
          f"max {100*10*np.log10(f.max()/p0)/B:5.1f}%")
    if i.size:
        print(f"  INFEASIBLE required W   p50 {np.percentile(i,50):.4f}  "
              f"p95 {np.percentile(i,95):.4f}  max {i.max():.4f}")
        print(f"    => would have needed   p50 {100*10*np.log10(np.percentile(i,50)/p0)/B:5.1f}%  "
              f"max {100*10*np.log10(i.max()/p0)/B:5.1f}% of budget")
    else:
        print("  INFEASIBLE required W   (none)")
    print(f"  segment length steps    p50 {np.percentile(sl,50):.0f}  "
          f"p95 {np.percentile(sl,95):.0f}  max {sl.max()}  mean {sl.mean():.2f}")
    print("  why segments ended, and how long those ones ran:")
    for k, v in why.most_common():
        lens = np.array(by_reason[k])
        print(f"    {k:20s} {v:5d}  {100*v/sum(why.values()):5.1f}%   "
              f"len p50 {np.percentile(lens,50):.1f}  mean {lens.mean():.2f}")
    nat = np.array(by_reason["handover"] + by_reason["outage"])
    print(f"  UNCENSORED segment length (ended by handover or outage, not by the")
    print(f"    episode boundary):  p50 {np.percentile(nat,50):.0f}  "
          f"p95 {np.percentile(nat,95):.0f}  mean {nat.mean():.2f}  max {nat.max()}")
    print()
