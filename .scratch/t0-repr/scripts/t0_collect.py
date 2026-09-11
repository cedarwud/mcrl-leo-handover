#!/usr/bin/env python3
"""T0-REPR step 2 -- collect T0 decisions on training-like episodes (no training).

SEED RULE (training triple j = (train, env, mobility) in (42,1337,7), (43,1338,8), (44,1339,9)):
  exactly the pilot trainer's episode schedule (MODQNTrainer.__init__: env_rng = default_rng(env),
  mobility_rng = default_rng(mobility); CFRatioTrainer.train_cf: env.reset(env_rng, mobility_rng) at every
  episode, env.step(actions, env_rng) at every step), with T0 as the behaviour policy.  Episode k runs on a
  FRESH env object; the env's only cross-episode state (the warm-start age stream `_age_rng`) is carried from
  episode k-1's env through the env's own resume seam (training_state_dict / load_training_state_dict), the
  path the trainer's resume uses.  `train` (42/43/44) seeds only the learner's own generators (epsilon, replay,
  init), which T0 does not consume -- recorded, unused.  Episodes k >= 1 differ from the pilot's own training
  episodes because the stream position after an episode depends on the actions taken (fading draw count).
  --seed-rule-check K: first K episodes of the triple run BOTH ways (one env carried vs fresh env + carried
  age state); they must be bit-identical (epoch, t=0 hash, per-step actions, bits, joules) or exit 3.

Per decision: obs (113 float32 = encode_with_time), legal mask (28), T0 action, T0 score (28 float64, every
slot), MAX_NOMINAL_GAIN action (for the price-active subset), triple j, episode k, step t, user u.
Usage: t0_collect.py --triple J --episodes N [--seed-rule-check K]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tree" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import t0_common as T  # noqa: E402

import io  # noqa: E402
import numpy as np  # noqa: E402


def run_episode(env, env_rng, mob_rng, encode, record: bool):
    states, masks, _ = env.reset(env_rng, mob_rng)
    users, steps = env.config.num_users, env.config.steps_per_episode
    epoch = str(env.epoch)
    cols = {"obs": [], "mask": [], "act": [], "score": [], "a_mg": [], "t": [], "u": []}
    row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0, "beams": 0.0, "steps": 0,
           "h_inter": 0, "h_intra": 0, "epoch": epoch}
    acts_hash = hashlib.sha256()
    enc0 = None
    for t in range(steps):
        enc = encode(states, t)
        if enc0 is None:
            enc0 = hashlib.sha256(np.ascontiguousarray(enc[:, :112]).tobytes()).hexdigest()
        S, acts, M = T.t0_scores(states, masks)
        acts_hash.update(np.asarray(acts, dtype=np.int64).tobytes())
        if record:
            cols["obs"].append(enc.astype(np.float32))
            cols["mask"].append(M)
            cols["act"].append(np.asarray(acts, dtype=np.int64))
            cols["score"].append(S)
            cols["a_mg"].append(np.asarray(T.max_gain_actions(states, masks), dtype=np.int64))
            cols["t"].append(np.full(users, t, dtype=np.int16))
            cols["u"].append(np.arange(users, dtype=np.int16))
        res = env.step(acts, env_rng)
        e = env.last_outcome.energy
        row["bits"] += float(e.system_throughput_bps) * T.cfr.DT_S
        row["joules"] += float(e.system_consumed_power_w) * T.cfr.DT_S
        row["served"] += int(e.served)
        row["beams"] += float(e.eff_beams)
        row["steps"] += 1
        row["user_steps"] += users
        for cls in env.last_outcome.handovers:
            row["h_inter"] += int(cls is T.HandoverClass.INTER_SATELLITE)
            row["h_intra"] += int(cls is T.HandoverClass.INTRA_SATELLITE)
        states, masks = res.user_states, res.action_masks
        if res.done:
            break
    row["t0_obs112_sha256"] = enc0
    row["actions_sha256"] = acts_hash.hexdigest()
    return row, cols


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--triple", type=int, choices=(0, 1, 2), required=True)
    ap.add_argument("--episodes", type=int, required=True)
    ap.add_argument("--seed-rule-check", type=int, default=0)
    a = ap.parse_args()
    tle = T.boot()
    out_npz = T.WS / "data" / f"T0-collect-triple{a.triple}.npz"
    out_json = out_npz.with_suffix(".json")
    if out_npz.exists() and out_json.exists():
        print(f"[skip:exists] {out_npz}", flush=True)
        return 0
    train_seed, env_seed, mob_seed = T.TRAIN_TRIPLES[a.triple]
    cfg = T.learner_config()
    factory = T.C.env_factory()
    probe = factory()
    users, steps = probe.config.num_users, probe.config.steps_per_episode
    del probe
    encode = T.make_encoder(cfg, users, steps)
    t_start = time.time()

    seed_rule = None
    if a.seed_rule_check:
        K = a.seed_rule_check
        env = factory()
        er, mr = np.random.default_rng(env_seed), np.random.default_rng(mob_seed)
        single = [run_episode(env, er, mr, encode, False)[0] for _ in range(K)]
        er, mr = np.random.default_rng(env_seed), np.random.default_rng(mob_seed)
        fresh, state = [], None
        for _ in range(K):
            env = factory()
            if state is not None:
                env.load_training_state_dict(state)
            fresh.append(run_episode(env, er, mr, encode, False)[0])
            state = env.training_state_dict()
        keys = ("epoch", "t0_obs112_sha256", "actions_sha256", "bits", "joules", "served", "h_inter", "h_intra")
        same = all(all(s[k] == f[k] for k in keys) for s, f in zip(single, fresh))
        # negative control: a fresh env WITHOUT the carried age state must differ from episode 1 on
        er, mr = np.random.default_rng(env_seed), np.random.default_rng(mob_seed)
        nocarry = [run_episode(factory(), er, mr, encode, False)[0] for _ in range(K)]
        nocarry_diff = [any(s[k] != f[k] for k in keys) for s, f in zip(single, nocarry)]
        seed_rule = {"K": K, "single_env_vs_fresh_env_with_carried_age_state_identical": bool(same),
                     "single": single, "fresh": fresh,
                     "negative_control_fresh_env_no_carry_differs_per_episode": nocarry_diff}
        print(f"seed-rule check triple {a.triple}: identical={same} no-carry differs={nocarry_diff}", flush=True)
        if not same:
            T.write_json(T.WS / "data" / f"SEED-RULE-CHECK-FAILED-triple{a.triple}.json", seed_rule)
            print("SEED RULE CHECK FAILED", flush=True)
            return 3

    env_rng, mob_rng = np.random.default_rng(env_seed), np.random.default_rng(mob_seed)
    state = None
    rows, allc = [], {k: [] for k in ("obs", "mask", "act", "score", "a_mg", "t", "u", "k")}
    for k in range(a.episodes):
        env = factory()
        if state is not None:
            env.load_training_state_dict(state)
        row, cols = run_episode(env, env_rng, mob_rng, encode, True)
        state = env.training_state_dict()
        rows.append(row)
        for c in ("obs", "mask", "act", "score", "a_mg", "t", "u"):
            allc[c].append(np.concatenate(cols[c]))
        allc["k"].append(np.full(len(allc["act"][-1]), k, dtype=np.int16))
        if (k + 1) % 10 == 0:
            print(f"triple {a.triple} ep {k + 1}/{a.episodes} ee_ep={row['bits'] / row['joules']:.2f} "
                  f"epoch={row['epoch']} t={time.time() - t_start:.0f}s", flush=True)
    arrays = {c: np.concatenate(v) for c, v in allc.items()}
    arrays["triple"] = np.full(len(arrays["act"]), a.triple, dtype=np.int16)
    buf = io.BytesIO()
    np.savez(buf, **arrays)
    tmp = out_npz.with_suffix(".npz.tmp")
    tmp.write_bytes(buf.getvalue())
    tmp.replace(out_npz)
    bits = joules = 0.0
    for r in rows:
        bits += r["bits"]
        joules += r["joules"]
    meta = {"triple": a.triple, "train_seed_unused": train_seed, "env_seed": env_seed, "mobility_seed": mob_seed,
            "episodes": a.episodes, "decisions": int(len(arrays["act"])),
            "empty_mask_decisions": int((~arrays["mask"].any(1)).sum()),
            "episode_rows": rows, "T0_pooled_ee_on_these_episodes": bits / joules,
            "npz_sha256": T.sha256_file(out_npz), "seed_rule_check": seed_rule,
            "tle_file_set_sha256": tle, "code": T.code_ident(), "wall_s": time.time() - t_start,
            "seed_rule": ("pilot trainer schedule: one carried generator pair default_rng(env_seed), "
                          "default_rng(mobility_seed) across episodes; fresh env per episode with the "
                          "env's _age_rng carried via training_state_dict/load_training_state_dict; "
                          "T0 is the behaviour policy")}
    T.write_json(out_json, meta)
    print(f"DONE triple {a.triple}: {meta['decisions']} decisions, T0 pooled EE {meta['T0_pooled_ee_on_these_episodes']:.2f}, "
          f"wall {meta['wall_s']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
