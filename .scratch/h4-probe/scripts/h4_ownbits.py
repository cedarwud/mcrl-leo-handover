#!/usr/bin/env python3
"""H4 probe (measurement only, no training): an explicit OWN-BITS greedy
rule, implemented the same way cf_sources.py's rules are (reads only the raw
observation fields, never the trained networks), rolled out on both the
calibration and evaluation episode sets. Also rolls out MAX_NOMINAL_GAIN and
C1_A_m2dB ("A m=2dB") on both sets as cheap references.

own-bits score for legal candidate a:  (1 / (load_a + 1)) * log2(1 + gamma_a)

  gamma_a = UserState.channel_quality[a]  -- RAW nominal SINR/gain.
            state_encoding.encode_state() applies log1p to this field ONLY
            when building the 112-dim NN input (block 2); this rule bypasses
            that, exactly like cf_sources.make_rule's
            `gain = np.asarray(s.channel_quality, dtype=np.float64)`.
  load_a  = UserState.beam_loads[a]  -- RAW previous-step user COUNT on beam
            a. state_encoding.encode_state() divides this by num_users ONLY
            when building the NN's block-4 input; this rule does NOT divide,
            exactly like cf_sources.r_no_new_beam's
            `load = np.asarray(s.beam_loads, dtype=np.float64)`, and matching
            the task wording "previous-step user count."
  Negative gamma_a (if any is observed) is floored at 0 before log2(1+.),
  mirroring state_encoding.py's own `np.maximum(snr, 0.0)` precedent before
  ITS log1p. Observed min/max of gamma and load are logged (see
  `own_bits_diagnostics` in each OWN_BITS output file) rather than assumed.
  Ties broken by first index (np.argmax), matching the project-wide
  masked-argmax convention.

Per-served-user rate mean: NOT derived from pooled_rollout's aggregates
(that would silently assume system_throughput_bps decomposes exactly into
sum(rewards[u].r1_throughput for u served), which this script does not
assume). Instead `pooled_rollout_with_user_rate` below duplicates
cf_ratio.pooled_rollout's loop verbatim (same env.step() calls, same
bits/joules/h_inter/h_intra/served/beams accounting) and ADDITIONALLY
accumulates result.rewards[uid].r1_throughput (bit/s) over steps where
result.served[uid] is True -- the same fields cf_ratio.cf_reward_matrix
already reads for its B_u head. Its shared fields are cross-checked
bit-for-bit against calibration.json (computed by the unmodified
cf3_premeasure.py/cf_ratio.pooled_rollout pipeline) for MAX_NOMINAL_GAIN and
C1_A_m2dB on the calibration seeds.

Usage: h4_ownbits.py --results-dir DIR
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = HERE.parent / "tree"
sys.path.insert(0, str(TREE / "src"))
sys.path.insert(0, str(TREE / "scripts"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

import cf3_common as C  # noqa: E402
from mcrl.algorithms import cf_ratio as cfr  # noqa: E402
from mcrl.algorithms import cf_sources as cfs  # noqa: E402
from mcrl.env.action_contract import no_op_actions  # noqa: E402
from mcrl.runtime import training_pipeline as tp  # noqa: E402

EXPECTED_TLE_SHA = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
CAL_JSON = Path("/home/sat/mcrl-v025-cf3-pilot-ws/premeasure/calibration.json")
ROLLOUT_FIELDS = ("ee", "bits", "joules", "served", "h_inter", "h_intra", "beams")


def own_bits_rule_factory(diag: dict):
    def fn(states, masks):
        out = no_op_actions(len(states))
        for u, s in enumerate(states):
            legal = np.asarray(masks[u].mask, dtype=bool)
            valid = np.flatnonzero(legal)
            if valid.size == 0:
                continue
            gain_raw = np.asarray(s.channel_quality, dtype=np.float64)
            load = np.asarray(s.beam_loads, dtype=np.float64)
            diag["n_gain_obs"] += int(gain_raw.size)
            diag["n_gain_negative"] += int(np.sum(gain_raw < 0.0))
            diag["min_gain"] = min(diag["min_gain"], float(gain_raw.min()))
            diag["max_gain"] = max(diag["max_gain"], float(gain_raw.max()))
            diag["min_load"] = min(diag["min_load"], float(load.min()))
            diag["max_load"] = max(diag["max_load"], float(load.max()))
            gain = np.maximum(gain_raw, 0.0)
            score = np.log2(1.0 + gain) / (load + 1.0)
            out[u] = int(valid[int(np.argmax(score[valid]))])
        return out

    return fn


def make_probe_encode(factory):
    """Same throwaway-MODQNTrainer encode cf3_premeasure.py's run_arm uses for
    rule-based (non-CF) policies. pooled_rollout requires SOME `encode`, but
    every rule here reads raw `states` directly and ignores the encoded
    array; this only exists to satisfy that plumbing requirement."""
    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.runtime.trainer_spec import TrainerConfig

    cfg = TrainerConfig(learning_rate=0.001, episodes=1)
    probe = MODQNTrainer(factory(), cfg, train_seed=42, env_seed=1337, mobility_seed=7)
    return lambda states, t: probe._encode_states(states)


def pooled_rollout_with_user_rate(policy_factory, *, env_factory, encode, seeds):
    """cf_ratio.pooled_rollout's loop, extended ONLY to also accumulate the
    per-served-user r1_throughput mean. See module docstring."""
    from mcrl.env.action_contract import HandoverClass

    rows = []
    rate_sum = 0.0
    served_user_steps = 0
    for i in range(len(seeds)):
        env = env_factory()
        env_rng = np.random.default_rng(seeds[i][0])
        mobility_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        policy = policy_factory(i)
        states, masks, _ = env.reset(env_rng, mobility_rng)
        enc = encode(states, 0)
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "h_inter": 0, "h_intra": 0, "beams": 0.0, "steps": 0}
        for t in range(steps):
            actions = policy(enc, masks, states)
            res = env.step(actions, env_rng)
            out = env.last_outcome
            e = out.energy
            row["bits"] += float(e.system_throughput_bps) * cfr.DT_S
            row["joules"] += float(e.system_consumed_power_w) * cfr.DT_S
            row["served"] += int(e.served)
            row["beams"] += float(e.eff_beams)
            row["steps"] += 1
            row["user_steps"] += users
            for cls in out.handovers:
                row["h_inter"] += int(cls is HandoverClass.INTER_SATELLITE)
                row["h_intra"] += int(cls is HandoverClass.INTRA_SATELLITE)
            if res.served is not None:
                for uid in range(users):
                    if bool(res.served[uid]):
                        rate_sum += float(res.rewards[uid].r1_throughput)
                        served_user_steps += 1
            states, masks = res.user_states, res.action_masks
            enc = encode(states, t + 1)
            if res.done:
                break
        rows.append(row)
    bits = joules = beams_total = 0.0
    for r in rows:
        bits += r["bits"]
        joules += r["joules"]
        beams_total += r["beams"]
    us = sum(r["user_steps"] for r in rows)
    return {
        "bits": bits,
        "joules": joules,
        "ee": bits / joules,
        "h_inter": sum(r["h_inter"] for r in rows) / us,
        "h_intra": sum(r["h_intra"] for r in rows) / us,
        "served": sum(r["served"] for r in rows) / us,
        "beams": beams_total / sum(r["steps"] for r in rows),
        "user_steps": us,
        "per_served_user_rate_mean_bps": rate_sum / served_user_steps if served_user_steps else float("nan"),
        "served_user_steps": served_user_steps,
    }


def run_rule(name, policy_fn, seeds, factory, encode, results_dir, tag, extra=None):
    out_path = results_dir / f"{name}-{tag}-h4ownbits.json"
    if out_path.exists():
        print(f"[skip:exists] {name} {tag}", flush=True)
        return json.loads(out_path.read_text())
    t0 = time.time()
    res = pooled_rollout_with_user_rate(
        lambda i: (lambda enc, masks, states: policy_fn(states, masks)),
        env_factory=factory, encode=encode, seeds=seeds,
    )
    res["name"] = name
    res["episode_set"] = tag
    if extra:
        res.update(extra)
    res["wall_s"] = time.time() - t0
    C.write_json(out_path, res)
    print(
        f"{name} {tag} ee={res['ee']} served={res['served']} "
        f"rate_mean_bps={res['per_served_user_rate_mean_bps']} wall_s={res['wall_s']:.1f}",
        flush=True,
    )
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", type=Path, required=True)
    a = ap.parse_args()
    a.results_dir.mkdir(parents=True, exist_ok=True)

    torch.set_num_threads(1)
    tle = tp.assert_tle_archive_pinned()
    if tle != EXPECTED_TLE_SHA:
        raise RuntimeError(f"TLE mismatch: {tle} != {EXPECTED_TLE_SHA}")

    factory = C.env_factory()
    encode = make_probe_encode(factory)

    max_nom = cfs.max_nominal_gain
    c1_m2db = cfs.cf3_policies()["C1_A_m2dB"]

    results = {}
    for tag, seeds in (("calibration", C.cal_seeds()), ("evaluation", C.eval_seeds())):
        diag = {
            "n_gain_obs": 0, "n_gain_negative": 0,
            "min_gain": float("inf"), "max_gain": float("-inf"),
            "min_load": float("inf"), "max_load": float("-inf"),
        }
        own_bits = own_bits_rule_factory(diag)
        results[("OWN_BITS", tag)] = run_rule(
            "OWN_BITS", own_bits, seeds, factory, encode, a.results_dir, tag,
            extra={"own_bits_diagnostics": diag},
        )
        results[("MAX_NOMINAL_GAIN", tag)] = run_rule(
            "MAX_NOMINAL_GAIN", max_nom, seeds, factory, encode, a.results_dir, tag
        )
        results[("C1_A_m2dB", tag)] = run_rule(
            "C1_A_m2dB", c1_m2db, seeds, factory, encode, a.results_dir, tag
        )

    # cross-check vs calibration.json (bit-for-bit) for the two references on calibration seeds
    cal = json.loads(CAL_JSON.read_text())
    checks = {}
    for name in ("MAX_NOMINAL_GAIN", "C1_A_m2dB"):
        mine = results[(name, "calibration")]
        theirs = cal["arms"][name]
        checks[name] = {k: bool(mine[k] == theirs[k]) for k in ROLLOUT_FIELDS}
        checks[name]["all_bit_identical"] = all(checks[name].values())
    checks_path = a.results_dir / "calibration_cross_check.json"
    if not checks_path.exists():
        C.write_json(checks_path, checks)
    print("calibration.json cross-check:", json.dumps(checks), flush=True)

    any_bad = any(not v["all_bit_identical"] for v in checks.values())
    print(f"DONE any_cross_check_failed={any_bad}", flush=True)
    return 1 if any_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
