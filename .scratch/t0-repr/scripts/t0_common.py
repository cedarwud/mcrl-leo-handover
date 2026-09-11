"""T0-REPR (measurement only, no learner training): shared code.

T0 = LP-prev(c=1, m=0) from `.scratch/h4-probe/scripts/lp_common.py`:
    score(a) = log2(1 + max(gamma_a, 0)) - c * [N_a == 0],   c = 1
gamma_a = raw `UserState.channel_quality` (nominal SINR), N_a = raw `UserState.beam_loads[a]`
(previous-step user count); masked argmax, first index on ties; m = 0 => no incumbent hold.

The student's observation is the ratio learner's: `cf_ratio.encode_with_time` = the 112-dim MODQN
encoding + (T - t)/T, built with the pilot trainer config (`cf3_common.pilot_config(record, "A1", 1000)`).

Rollout accumulation copies `lp_common.pooled_rollout_rates` statement for statement (plain
left-to-right sums, divided once), extended only with per-episode epoch / t=0 hash and an optional
per-step observer hook (which never touches the env or any generator).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
TREE = WS / "tree"
sys.path.insert(0, str(TREE / "src"))
sys.path.insert(0, str(TREE / "scripts"))

import numpy as np  # noqa: E402
import torch  # noqa: E402

import cf3_common as C  # noqa: E402
from mcrl.algorithms import cf_ratio as cfr  # noqa: E402
from mcrl.algorithms import cf_sources as cfs  # noqa: E402
from mcrl.env.action_contract import HandoverClass, NO_OP_ACTION, no_op_actions  # noqa: E402
from mcrl.runtime import training_pipeline as tp  # noqa: E402

EXPECTED_TLE_SHA = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
T0_C = 1.0
LP_GRID_DT_S = 30.08   # lp_grid.py DT_S literal, used ONLY for the derived ho_per_user_min display field
N_ACT = 28
LN2 = float(np.log(2.0))
# encoded-observation blocks (state_encoding.encode_state): access, log1p(snr), theta, loads/U, then (T-t)/T
B_ACCESS, B_SNR, B_THETA, B_LOAD, B_REM = slice(0, 28), slice(28, 56), slice(56, 84), slice(84, 112), 112

TRAIN_TRIPLES = ((42, 1337, 7), (43, 1338, 8), (44, 1339, 9))
REF_EE = {"evaluation": 107_000_983.53, "calibration": 112_195_917.54}   # A m=2dB, LP report (rounded; exact in targets/)


def boot() -> str:
    """Pin threads + assert the pinned TLE archive; returns the file_set sha256."""
    torch.set_num_threads(1)
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        if os.environ.get(k) != "1":
            raise RuntimeError(f"{k} must be 1")
    tle = tp.assert_tle_archive_pinned()
    if tle != EXPECTED_TLE_SHA:
        raise RuntimeError(f"TLE mismatch: {tle} != {EXPECTED_TLE_SHA}")
    import mcrl
    if not str(mcrl.__file__).startswith(str(TREE / "src")):
        raise RuntimeError(f"wrong mcrl tree: {mcrl.__file__}")
    return tle


def learner_config():
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    cfg = C.pilot_config(record, "A1", C.EPISODES)
    assert tuple(cfg.hidden_layers) == (100, 50, 50) and cfg.activation == "tanh", cfg
    return cfg


def make_encoder(cfg, users: int, steps: int):
    """The ratio learner's observation: encode_with_time (112 + remaining-steps)."""
    return lambda states, t: cfr.encode_with_time(states, t, users, cfg, steps)


def seeds_for(tag: str):
    return C.cal_seeds() if tag == "calibration" else C.eval_seeds()


# ------------------------------------------------------------------ T0
def t0_scores(states, masks, c: float = T0_C):
    """(U, 28) float64 T0 score for EVERY slot (legal or not), (U,) actions, (U, 28) legal mask.

    Same arithmetic as lp_common.lp_prev_rule_factory(c, 0): gain floor at 0, log2(1+g), penalty
    c*(load == 0); action = first legal index of the max (np.argmax on the legal subset)."""
    U = len(states)
    S = np.zeros((U, N_ACT), dtype=np.float64)
    M = np.zeros((U, N_ACT), dtype=bool)
    acts = no_op_actions(U)
    for u, s in enumerate(states):
        legal = np.asarray(masks[u].mask, dtype=bool)
        gain = np.asarray(s.channel_quality, dtype=np.float64)
        load = np.asarray(s.beam_loads, dtype=np.float64)
        gain_floor = np.maximum(gain, 0.0)
        penalty = c * (load == 0.0).astype(np.float64)
        score = np.log2(1.0 + gain_floor) - penalty
        S[u] = score
        M[u] = legal
        ok = np.flatnonzero(legal)
        if ok.size == 0:
            continue
        acts[u] = int(ok[int(np.argmax(score[ok]))])
    return S, acts, M


def t0_policy():
    def pol(enc, masks, states):
        return t0_scores(states, masks)[1]
    return pol


def decoder_scores_from_obs(enc: np.ndarray, c: float = T0_C) -> np.ndarray:
    """T0's score recomputed from the student's encoded observation only:
    log2(1+g) = log1p(g)/ln 2 = block_snr/ln 2 ; [N == 0] <=> block_load == 0 (exact)."""
    enc = np.asarray(enc)
    snr = enc[:, B_SNR].astype(np.float64)
    load = enc[:, B_LOAD]
    return snr / LN2 - c * (load == 0.0).astype(np.float64)


def decoder_policy():
    def pol(enc, masks, states):
        return C.masked_argmax(decoder_scores_from_obs(enc), masks)
    return pol


def max_gain_actions(states, masks):
    return cfs.max_nominal_gain(states, masks)


# ------------------------------------------------------------------ rollout
def _rate_stats(rates):
    arr = np.asarray(rates, dtype=np.float64)
    if arr.size == 0:
        return {"per_served_user_rate_mean_bps": float("nan"), "per_served_user_rate_p10_bps": float("nan"),
                "per_served_user_rate_min_bps": float("nan"), "served_user_steps": 0}
    return {"per_served_user_rate_mean_bps": float(arr.mean()),
            "per_served_user_rate_p10_bps": float(np.percentile(arr, 10)),
            "per_served_user_rate_min_bps": float(arr.min()),
            "served_user_steps": int(arr.size)}


def rollout(policy_factory, *, env_factory, encode, seeds, observer=None):
    """lp_common.pooled_rollout_rates, statement for statement, + epoch / t0 hash + observer hook.

    observer(i, t, enc, masks, states, actions) is called after the policy acts and BEFORE env.step;
    it must not touch the env or any generator."""
    rows = []
    rates: list[float] = []
    for i in range(len(seeds)):
        env = env_factory()
        env_rng = np.random.default_rng(seeds[i][0])
        mobility_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        policy = policy_factory(i)
        states, masks, _ = env.reset(env_rng, mobility_rng)
        enc = encode(states, 0)
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "h_inter": 0, "h_intra": 0, "beams": 0.0, "steps": 0,
               "epoch": str(env.epoch),
               "t0_obs112_sha256": hashlib.sha256(np.ascontiguousarray(np.asarray(enc)[:, :112]).tobytes()).hexdigest()}
        for t in range(steps):
            actions = policy(enc, masks, states)
            if observer is not None:
                observer(i, t, enc, masks, states, actions)
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
                        rates.append(float(res.rewards[uid].r1_throughput))
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
    out_d = {
        "bits": bits,
        "joules": joules,
        "ee": bits / joules,
        "h_inter": sum(r["h_inter"] for r in rows) / us,
        "h_intra": sum(r["h_intra"] for r in rows) / us,
        "served": sum(r["served"] for r in rows) / us,
        "beams": beams_total / sum(r["steps"] for r in rows),
        "user_steps": us,
        "ee_ep": [r["bits"] / r["joules"] if r["joules"] > 0 else float("nan") for r in rows],
        "n_episodes": len(rows),
        "episodes": rows,
    }
    out_d.update(_rate_stats(rates))
    # derived display field, computed exactly as lp_grid.ho_per_user_min (literal DT_S = 30.08); bits/joules use
    # cfr.DT_S = DECISION_STEP_S = 30.080000000000002 exactly as lp_common does (placebo v1 finding, PROGRESS.md)
    out_d["ho_per_user_min"] = (out_d["h_inter"] + out_d["h_intra"]) * 60.0 / LP_GRID_DT_S
    return out_d


# ------------------------------------------------------------------ clone
def build_clone(cfg, state_dim: int = 113):
    from mcrl.runtime.q_network import DQNNetwork
    return DQNNetwork(state_dim, N_ACT, tuple(cfg.hidden_layers), cfg.activation)


def load_clone(path: Path, cfg):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    net = build_clone(cfg, int(ck["state_dim"]))
    net.load_state_dict(ck["state"])
    net.eval()
    return net, ck


def clone_policy(net):
    """Greedy masked argmax of the clone's logits, first index on ties, no generator."""
    def pol(enc, masks, states):
        with torch.no_grad():
            lg = net(torch.as_tensor(np.asarray(enc, dtype=np.float32))).numpy().astype(np.float64)
        return C.masked_argmax(lg, masks)
    return pol


def sha256_file(p) -> str:
    return C.sha256_file(Path(p))


def write_json(path, payload):
    C.write_json(Path(path), payload)


def code_ident() -> dict:
    here = Path(__file__).resolve().parent
    return {"scripts": {p.name: sha256_file(p) for p in sorted(here.glob("*.py"))},
            "tree_commit": (TREE / "COMMIT").read_text().strip()}
