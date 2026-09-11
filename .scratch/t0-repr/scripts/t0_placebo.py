#!/usr/bin/env python3
"""T0-REPR step 1 -- placebo (no training).

On one episode set (24 episodes, fresh env per episode, per-episode reseeding, greedy):
  (a) my T0 rollout (t0_common.rollout + t0_common.t0_scores) must equal the LP probe's
      LP-prev(1,0) JSON bit-for-bit on every field (targets/LP-prev-<set>-c1-m0.json);
      on every decision my T0 action must equal lp_common.lp_prev_rule_factory(1, 0)'s;
  (b) `A m=2dB` (cf_sources C1_A_m2dB) re-rolled through the same loop must equal
      targets/REF-C1_A_m2dB-<set>.json bit-for-bit (the R_repr reference);
  (c) instrument check on T0's own trajectory: the student's 113-dim observation decodes to the raw
      loads exactly and to the raw SINR within float32 rounding, and T0's action recomputed from the
      observation alone (decoder) equals T0's action; the decoder-from-observation POLICY, rolled
      through the clone code path, must reproduce (a) bit-for-bit.
Exit 3 if any check fails.  Usage: t0_placebo.py --set evaluation|calibration
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tree" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import t0_common as T  # noqa: E402

import json  # noqa: E402
import numpy as np  # noqa: E402

import lp_common as L  # noqa: E402  (LP probe code, staged verbatim)

FIELDS = ("beams", "bits", "ee", "ee_ep", "h_inter", "h_intra", "ho_per_user_min", "joules", "n_episodes",
          "per_served_user_rate_mean_bps", "per_served_user_rate_min_bps", "per_served_user_rate_p10_bps",
          "served", "served_user_steps", "user_steps")


def compare(mine: dict, theirs: dict, fields) -> dict:
    out = {k: bool(mine[k] == theirs[k]) for k in fields}
    out["all_bit_identical"] = all(out.values())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="tag", choices=("evaluation", "calibration"), required=True)
    a = ap.parse_args()
    tle = T.boot()
    ws = T.WS
    out_path = ws / "results" / f"PLACEBO-{a.tag}.json"
    if out_path.exists():
        print(f"[skip:exists] {out_path}", flush=True)
        return 0
    cfg = T.learner_config()
    factory = T.C.env_factory()
    probe_env = factory()
    users, steps = probe_env.config.num_users, probe_env.config.steps_per_episode
    del probe_env
    encode = T.make_encoder(cfg, users, steps)
    seeds = T.seeds_for(a.tag)
    lp_rule = L.lp_prev_rule_factory(1.0, 0.0)
    chk = {"decisions": 0, "lp_rule_mismatch": 0, "decoder_mismatch": 0, "load_decode_mismatch": 0,
           "snr_max_rel_err": 0.0, "rem_mismatch": 0, "empty_mask": 0}

    def observer(i, t, enc, masks, states, actions):
        lp_a = np.asarray(lp_rule(states, masks))
        dec_a = T.C.masked_argmax(T.decoder_scores_from_obs(enc), masks)
        acts = np.asarray(actions)
        chk["decisions"] += len(acts)
        chk["lp_rule_mismatch"] += int((lp_a != acts).sum())
        chk["decoder_mismatch"] += int((np.asarray(dec_a) != acts).sum())
        chk["empty_mask"] += int(sum(1 for m in masks if not np.asarray(m.mask).any()))
        for u, s in enumerate(states):
            load = np.asarray(s.beam_loads, dtype=np.float64)
            if not np.array_equal((enc[u, T.B_LOAD].astype(np.float64) * users), load):
                # loads/U in float32 -> compare the zero pattern and the rounded count
                if not (np.array_equal(enc[u, T.B_LOAD] == 0.0, load == 0.0)
                        and np.array_equal(np.rint(enc[u, T.B_LOAD].astype(np.float64) * users), load)):
                    chk["load_decode_mismatch"] += 1
            g = np.maximum(np.asarray(s.channel_quality, dtype=np.float64), 0.0)
            dec = np.expm1(enc[u, T.B_SNR].astype(np.float64))
            rel = np.abs(dec - g) / np.maximum(np.abs(g), 1e-30)
            rel[g == 0.0] = np.abs(dec[g == 0.0])
            chk["snr_max_rel_err"] = max(chk["snr_max_rel_err"], float(rel.max()))
            if float(enc[u, T.B_REM]) != np.float32((steps - t) / steps):
                chk["rem_mismatch"] += 1

    t0 = time.time()
    mine = T.rollout(lambda i: T.t0_policy(), env_factory=factory, encode=encode, seeds=seeds, observer=observer)
    mine["wall_s"] = time.time() - t0
    lp_target = json.loads((ws / "targets" / f"LP-prev-{a.tag}-c1-m0.json").read_text())
    cmp_t0 = compare(mine, lp_target, FIELDS)
    print(f"T0 {a.tag}: ee={mine['ee']!r} target={lp_target['ee']!r} {cmp_t0}", flush=True)
    print(f"T0 {a.tag} decision checks: {chk}", flush=True)

    t1 = time.time()
    rule = T.cfs.cf3_policies()["C1_A_m2dB"]
    ref = T.rollout(lambda i: (lambda enc, masks, states: rule(states, masks)),
                    env_factory=factory, encode=encode, seeds=seeds)
    ref["wall_s"] = time.time() - t1
    ref_target = json.loads((ws / "targets" / f"REF-C1_A_m2dB-{a.tag}.json").read_text())
    cmp_ref = compare(ref, ref_target, FIELDS)
    print(f"A m=2dB {a.tag}: ee={ref['ee']!r} target={ref_target['ee']!r} {cmp_ref}", flush=True)

    t2 = time.time()
    dec = T.rollout(lambda i: T.decoder_policy(), env_factory=factory, encode=encode, seeds=seeds)
    dec["wall_s"] = time.time() - t2
    cmp_dec = compare(dec, mine, FIELDS)
    cmp_dec["episodes_identical"] = bool(
        [(r["bits"], r["joules"], r["epoch"], r["t0_obs112_sha256"]) for r in dec["episodes"]]
        == [(r["bits"], r["joules"], r["epoch"], r["t0_obs112_sha256"]) for r in mine["episodes"]])
    print(f"decoder-from-observation {a.tag}: ee={dec['ee']!r} vs T0 {cmp_dec}", flush=True)

    ok = (cmp_t0["all_bit_identical"] and cmp_ref["all_bit_identical"] and cmp_dec["all_bit_identical"]
          and cmp_dec["episodes_identical"] and chk["lp_rule_mismatch"] == 0 and chk["decoder_mismatch"] == 0
          and chk["load_decode_mismatch"] == 0 and chk["rem_mismatch"] == 0)
    payload = {"ok": bool(ok), "episode_set": a.tag, "seeds": [list(s) for s in seeds], "tle_file_set_sha256": tle,
               "T0": mine, "T0_vs_LP_target": cmp_t0, "T0_decision_checks": chk,
               "REF_A_m2dB": ref, "REF_vs_target": cmp_ref,
               "DECODER_policy": dec, "DECODER_vs_T0": cmp_dec,
               "targets_sha256": {p.name: T.sha256_file(p) for p in sorted((ws / "targets").glob("*.json"))},
               "code": T.code_ident()}
    T.write_json(out_path, payload)
    print("PLACEBO " + ("PASSED" if ok else "FAILED"), flush=True)
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
