#!/usr/bin/env python3
"""B2-REPR step 1-2: the placebo gate, and the training corpus it produces.

Nothing below counts until this passes.

  ref       : re-roll `A m=2dB` on both episode sets through THIS report's own loop and compare 15
              fields bitwise with the LP probe's `REF-C1_A_m2dB-<set>.json`.
  teacher   : aggregate the 24 floored B-real R1 cell JSONs per set (pooled Sigma bits / Sigma J,
              divided once) -> EE(T_SEQ); replay the saved joint actions of the CALIBRATION set
              (all 24) and of two EVALUATION episodes, asserting at every step that
                (a) the reference rule reproduces the stored `joint_ref`,
                (b) the re-encoded 113-dim observation equals the saved npz rows bitwise,
                (c) the committed bits / joules equal the stored ones bitwise;
              and, on the calibration replay, build the declared ctx28 block (PROGRESS.md D1) from
              the env's own slot tables -> `data/B2-train-calibration.npz` (the training corpus).

Usage: b2_placebo.py [--only ref|teacher]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_common as B  # noqa: E402

import numpy as np  # noqa: E402

import cf3_common as C  # noqa: E402
from mcrl.algorithms import cf_ratio as cfr  # noqa: E402

SETS = ("evaluation", "calibration")


def roll_reference(tag, factory, cfg, tle):
    out = B.WS / "results" / f"PLACEBO-REF-{tag}.json"
    if out.exists():
        print(f"[skip:exists] {out.name}", flush=True)
        return json.loads(out.read_text())
    seeds = B.seeds_for(tag)
    t0 = time.time()
    r = B.rollout(B.ref_decider(), env_factory=factory,
                  encode=lambda s, t: cfr.encode_with_time(s, t, 100, cfg, 10), seeds=seeds)
    target = json.loads((B.LP_DIR / f"REF-C1_A_m2dB-{tag}.json").read_text())
    rec = {"arm": "C1_A_m2dB", "episode_set": tag, "wall_s": time.time() - t0,
           "target_file": str(B.LP_DIR / f"REF-C1_A_m2dB-{tag}.json"),
           "target_sha256": B.sha256_file(B.LP_DIR / f"REF-C1_A_m2dB-{tag}.json"),
           "comparison": B.compare(r, target), "result": r,
           "tle_file_set_sha256": tle, "code": B.code_ident()}
    B.write_json(out, rec)
    print(f"REF {tag}: ee={r['ee']!r} all_equal={rec['comparison']['all_equal']} "
          f"wall={rec['wall_s']:.1f}s", flush=True)
    return rec


def teacher_cells(tag):
    recs = []
    for i in range(24):
        p = B.ORACLE_DIR / f"{B.TEACHER_STEM.format(tag=tag, i=i)}.json"
        recs.append(json.loads(p.read_text()))
    return recs


def aggregate_teacher(tag):
    recs = teacher_cells(tag)
    bits = joules = beams = 0.0
    served = us = hi = hj = 0
    steps = 0
    rates: list[float] = []
    for r in recs:
        bits += r["bits"]
        joules += r["joules"]
        beams += r["beams"]
        served += r["served"]
        us += r["user_steps"]
        hi += r["h_inter"]
        hj += r["h_intra"]
        steps += r["steps"]
        rates.extend(r["rates_bps"])
    a = np.asarray(rates, dtype=np.float64)
    out = {"arm": "B-real-floor-R1 (T_SEQ)", "episode_set": tag,
           "bits": bits, "joules": joules, "ee": bits / joules,
           "served": served / us, "beams": beams / steps, "user_steps": us,
           "h_inter": hi / us, "h_intra": hj / us,
           "ee_ep": [r["bits"] / r["joules"] for r in recs], "n_episodes": len(recs),
           "per_served_user_rate_mean_bps": float(a.mean()),
           "per_served_user_rate_p10_bps": float(np.percentile(a, 10)),
           "per_served_user_rate_min_bps": float(a.min()),
           "served_user_steps": int(a.size),
           "parity_max_abs_dbits": max(r["parity_max_abs_dbits"] for r in recs),
           "parity_max_abs_djoules": max(r["parity_max_abs_djoules"] for r in recs),
           "n_moved_total": sum(r["n_moved"] for r in recs),
           "cell_sha256": {f"ep{i:02d}": B.sha256_file(B.ORACLE_DIR / f"{B.TEACHER_STEM.format(tag=tag, i=i)}.json")
                           for i in range(24)}}
    out["ho_per_user_min"] = (out["h_inter"] + out["h_intra"]) * 60.0 / B.LP_GRID_DT_S
    return out


def replay_set(tag, episodes, factory, cfg, tle, build_ctx):
    """Commit the stored joint actions; assert reference / observation / energy reproduction."""
    recs = teacher_cells(tag)
    seeds = B.seeds_for(tag)
    rule = B.ref_policy()
    checks = {"ref_reproduced": 0, "ref_steps": 0, "obs_identical_steps": 0, "obs_mismatch_steps": 0,
              "max_abs_dbits": 0.0, "max_abs_djoules": 0.0, "empty_masks": 0, "noop_actions": 0}
    ctx_rows, idx_rows = [], []
    joint = {i: recs[i]["joint_chosen"] for i in episodes}
    per_ep = {}

    def decide(ep, t, env, sim, enc, masks, states):
        users = len(masks)
        rec = recs[ep]
        ref_now = rule(states, masks)
        checks["ref_steps"] += 1
        checks["ref_reproduced"] += int([int(x) for x in ref_now] == rec["joint_ref"][t])
        npz = np.load(B.ORACLE_DIR / f"{B.TEACHER_STEM.format(tag=tag, i=ep)}-obs-actions.npz")
        sel = npz["step"] == t
        if np.array_equal(np.asarray(enc), npz["obs"][sel]):
            checks["obs_identical_steps"] += 1
        else:
            checks["obs_mismatch_steps"] += 1
        acts = np.asarray(rec["joint_chosen"][t], dtype=np.int32)
        if not np.array_equal(acts.astype(np.int16), npz["action"][sel]):
            raise RuntimeError(f"{tag} ep{ep} t{t}: joint_chosen != npz action")
        checks["empty_masks"] += int(sum(1 for m in masks if not m.mask.any()))
        checks["noop_actions"] += int((acts < 0).sum())
        if build_ctx:
            ctx_rows.append(B.ctx_block(sim, users, acts, "fwd"))
            idx_rows.append(np.stack([np.full(users, ep), np.full(users, t), np.arange(users)], axis=1))
        return acts

    def observer(ep, t, env, sim, enc, masks, states, actions):
        pass

    # one rollout per requested episode so the seed pairing stays exact
    for ep in episodes:
        r = B.rollout(lambda e, t, env, sim, enc, masks, states, _ep=ep: decide(_ep, t, env, sim, enc, masks, states),
                      env_factory=factory,
                      encode=lambda s, t: cfr.encode_with_time(s, t, 100, cfg, 10),
                      seeds=[seeds[ep]], observer=observer)
        rec = recs[ep]
        db = abs(r["bits"] - rec["bits"])
        dj = abs(r["joules"] - rec["joules"])
        checks["max_abs_dbits"] = max(checks["max_abs_dbits"], db)
        checks["max_abs_djoules"] = max(checks["max_abs_djoules"], dj)
        per_ep[f"ep{ep:02d}"] = {"bits_mine": r["bits"], "bits_stored": rec["bits"],
                                 "joules_mine": r["joules"], "joules_stored": rec["joules"],
                                 "ee_mine": r["ee"], "ee_stored": rec["ee"],
                                 "bitwise_equal": bool(r["bits"] == rec["bits"] and r["joules"] == rec["joules"])}
    payload = {"episode_set": tag, "episodes": list(episodes), "checks": checks, "per_episode": per_ep,
               "tle_file_set_sha256": tle, "code": B.code_ident()}
    ctx = None
    if build_ctx:
        ctx = {"ctx": np.concatenate(ctx_rows).astype(np.float32),
               "episode": np.concatenate(idx_rows)[:, 0].astype(np.int16),
               "step": np.concatenate(idx_rows)[:, 1].astype(np.int16),
               "user": np.concatenate(idx_rows)[:, 2].astype(np.int16)}
    return payload, ctx


def build_corpus(tag, ctx, tle):
    """Join the ctx block to the saved oracle rows -> the training corpus."""
    parts = [np.load(B.ORACLE_DIR / f"{B.TEACHER_STEM.format(tag=tag, i=i)}-obs-actions.npz") for i in range(24)]
    d = {k: np.concatenate([p[k] for p in parts]) for k in
         ("obs", "action", "ref_action", "mask", "adv", "adv_disallowed", "adv_disallowed_floor",
          "episode", "step", "user")}
    for k in ("episode", "step", "user"):
        if not np.array_equal(d[k], ctx[k]):
            raise RuntimeError(f"ctx index mismatch on {k}")
    d["ctx"] = ctx["ctx"]
    recs = teacher_cells(tag)
    ref_bits = np.zeros(len(d["action"]), dtype=np.float64)
    for i, r in enumerate(recs):
        for t, sd in enumerate(r["steps_detail"]):
            ref_bits[(d["episode"] == i) & (d["step"] == t)] = sd["ref_bits"]
    d["ref_bits"] = ref_bits
    out = B.WS / "data" / f"B2-train-{tag}.npz"
    tmp = out.with_suffix(".tmp.npz")
    np.savez_compressed(tmp, **d)
    tmp.replace(out)
    meta = {"episode_set": tag, "rows": int(len(d["action"])), "sha256": B.sha256_file(out),
            "ctx_nonzero_frac": float((d["ctx"] > 0).mean()),
            "ctx_max": float(d["ctx"].max()),
            "ctx_row_sum_mean": float(d["ctx"].sum(1).mean()),
            "action_eq_ref_frac": float((d["action"] == d["ref_action"]).mean()),
            "legal_mean": float(d["mask"].sum(1).mean()),
            "empty_mask_rows": int((~d["mask"].any(1)).sum()),
            "noop_actions": int((d["action"] < 0).sum()),
            "tle_file_set_sha256": tle}
    B.write_json(B.WS / "data" / f"B2-train-{tag}-meta.json", meta)
    print(f"CORPUS {tag}: {meta}", flush=True)
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=("ref", "teacher"), default=None)
    a = ap.parse_args()
    tle = B.boot()
    cfg = B.learner_config()
    factory = C.env_factory()

    if a.only in (None, "ref"):
        ok = True
        for tag in SETS:
            rec = roll_reference(tag, factory, cfg, tle)
            ok = ok and rec["comparison"]["all_equal"]
        print(f"PLACEBO REF all_equal_both_sets={ok}", flush=True)

    if a.only in (None, "teacher"):
        for tag in SETS:
            out = B.WS / "results" / f"TEACHER-{tag}.json"
            if not out.exists():
                agg = aggregate_teacher(tag)
                agg["tle_file_set_sha256"] = tle
                B.write_json(out, agg)
                print(f"TEACHER {tag}: ee={agg['ee']:.2f} served={agg['served']:.5f} "
                      f"p10={agg['per_served_user_rate_p10_bps']/1e6:.2f}M", flush=True)
            else:
                print(f"[skip:exists] {out.name}", flush=True)

        out = B.WS / "results" / "PLACEBO-TEACHER-calibration.json"
        if not out.exists():
            t0 = time.time()
            payload, ctx = replay_set("calibration", range(24), factory, cfg, tle, build_ctx=True)
            payload["wall_s"] = time.time() - t0
            B.write_json(out, payload)
            print(f"PLACEBO TEACHER calibration: {payload['checks']}", flush=True)
            build_corpus("calibration", ctx, tle)
        else:
            print(f"[skip:exists] {out.name}", flush=True)

        out = B.WS / "results" / "PLACEBO-TEACHER-evaluation.json"
        if not out.exists():
            t0 = time.time()
            payload, _ = replay_set("evaluation", [0, 1], factory, cfg, tle, build_ctx=False)
            payload["wall_s"] = time.time() - t0
            B.write_json(out, payload)
            print(f"PLACEBO TEACHER evaluation (2 ep): {payload['checks']}", flush=True)
        else:
            print(f"[skip:exists] {out.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
