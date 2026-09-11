"""Aggregate the CATFISH2-DISCOVERY Stage-0 shards into the report table."""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

R = Path("/home/sat/mcrl-v025-catfish2-ws/results")

refs = json.load(open(R / "DEVVAL-REFERENCES.json"))["arms"]
ctrl = json.load(open(R / "DEVVAL-CONTROLS.json"))["arms"]
modqn = json.load(open(R / "DEVVAL-BASELINE-MODQN.json"))

stand = {}
stand["T0_LP_prev_c1_m0"] = refs["LP_prev_c1_m0"]
stand["MAX_NOMINAL_GAIN"] = refs["MAX_NOMINAL_GAIN"]
stand["A_m2dB"] = refs["A_m2dB"]
stand["RANDOM"] = refs["RANDOM"]
stand.update(ctrl)
stand["MODQN_eq16"] = modqn

shards = sorted(glob.glob(str(R / "DIAG-CF2-s*.json")))
data = [json.load(open(f)) for f in shards]
names = list(data[0]["candidates"])
agg = {}
for n in names:
    d = np.concatenate([np.asarray(x["candidates"][n]["deltas"], dtype=np.float64) for x in data])
    db = np.concatenate([np.asarray(x["candidates"][n]["d_bits"], dtype=np.float64) for x in data])
    dj = np.concatenate([np.asarray(x["candidates"][n]["d_joules"], dtype=np.float64) for x in data])
    tot = lambda k: sum(x["candidates"][n][k] for x in data)  # noqa: E731
    pos = float(d[d > 0].sum()) if d.size else 0.0
    neg = float(-d[d < 0].sum()) if d.size else 0.0
    agg[n] = {
        "n_decisions": tot("n_decisions"),
        "n_disagree": tot("n_disagree"),
        "disagreement": tot("n_disagree") / tot("n_decisions"),
        "agreement_T0": 1.0 - tot("n_disagree") / tot("n_decisions"),
        "disagreement_MAXGAIN": 1.0 - tot("n_agree_maxgain") / tot("n_decisions"),
        "cand_better_frac": float((d > 0).mean()) if d.size else float("nan"),
        "t0_better_frac": float((d < 0).mean()) if d.size else float("nan"),
        "tie_frac": float((d == 0).mean()) if d.size else float("nan"),
        "CR": pos / neg if neg > 0 else float("inf"),
        "delta_median": float(np.median(d)) if d.size else float("nan"),
        "delta_p10": float(np.percentile(d, 10)) if d.size else float("nan"),
        "delta_p90": float(np.percentile(d, 90)) if d.size else float("nan"),
        "delta_mean": float(d.mean()) if d.size else float("nan"),
        "sum_delta": float(d.sum()) if d.size else float("nan"),
        "d_bits_mean": float(db.mean()) if db.size else float("nan"),
        "d_joules_mean": float(dj.mean()) if dj.size else float("nan"),
        "rhat_up_frac": tot("rhat_up") / max(tot("n_disagree"), 1),
        "qos_invalid_frac": tot("qos_invalid") / max(tot("n_disagree"), 1),
        "n_evaluate_actions": sum(x["n_evaluate_actions"] for x in data),
    }

T0 = stand["T0_LP_prev_c1_m0"]
A2 = stand["A_m2dB"]
print("=" * 128)
hdr = ("%-18s %12s %9s %11s %11s %8s %8s %8s | %7s %7s %7s %7s %7s" %
       ("arm", "EE bit/J", "served", "p10 bit/s", "min bit/s", "beams", "EE/T0", "p10/T0",
        "disT0", "disMG", "better", "CR", "qosinv"))
print(hdr)
print("-" * 128)
for n, v in stand.items():
    a = agg.get(n, {})
    print("%-18s %12.6e %9.5f %11.4e %11.4e %8.3f %8.4f %8.4f | %7s %7s %7s %7s %7s" % (
        n, v["ee"], v["served"], v["per_served_user_rate_p10_bps"],
        v["per_served_user_rate_min_bps"], v["beams"],
        v["ee"] / T0["ee"], v["per_served_user_rate_p10_bps"] / T0["per_served_user_rate_p10_bps"],
        ("%.4f" % a["disagreement"]) if a else "-",
        ("%.4f" % a["disagreement_MAXGAIN"]) if a else "-",
        ("%.4f" % a["cand_better_frac"]) if a else "-",
        ("%.4f" % a["CR"]) if a else "-",
        ("%.4f" % a["qos_invalid_frac"]) if a else "-"))
print("=" * 128)
print("p10 / (0.5 x A_m2dB p10) --- condition 5 rate floor")
for n, v in stand.items():
    print("  %-18s %8.4f  (p10 = %.4e, 0.5 x A_m2dB p10 = %.4e)" % (
        n, v["per_served_user_rate_p10_bps"] / (0.5 * A2["per_served_user_rate_p10_bps"]),
        v["per_served_user_rate_p10_bps"], 0.5 * A2["per_served_user_rate_p10_bps"]))
print()
print("value-weighted complementarity detail (T0 trajectory, unilateral, eta0-priced)")
for n, a in agg.items():
    print("  %-18s dis=%5d/%5d (%.4f) better=%.4f t0better=%.4f tie=%.4f CR=%.4f "
          "med=%+.4e p10=%+.4e p90=%+.4e sum=%+.4e rhat_up=%.4f qosinv=%.4f" % (
              n, a["n_disagree"], a["n_decisions"], a["disagreement"], a["cand_better_frac"],
              a["t0_better_frac"], a["tie_frac"], a["CR"], a["delta_median"], a["delta_p10"],
              a["delta_p90"], a["sum_delta"], a["rhat_up_frac"], a["qos_invalid_frac"]))
print()
print("H_inter / H_intra per user-step")
for n, v in stand.items():
    print("  %-18s h_inter=%.5f h_intra=%.5f bits=%.6e joules=%.6e" % (
        n, v["h_inter"], v["h_intra"], v["bits"], v["joules"]))

json.dump({"standalone": {k: {kk: vv for kk, vv in v.items() if kk not in ("episodes", "ee_ep")}
                          for k, v in stand.items()},
           "complementarity": agg},
          open(R / "STAGE0-AGGREGATE.json", "w"), indent=2, sort_keys=True, default=str)
print("\nwrote", R / "STAGE0-AGGREGATE.json")
