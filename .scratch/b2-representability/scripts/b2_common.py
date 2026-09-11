"""B2-REPR (measurement only, no learner training): shared code.

Teacher  T_SEQ = B-real-floor R1 = the rate-floored one-sequential-sweep realised-information oracle
(`.scratch/h4-probe/scripts/oracle_cells.py`, kind "Bf", ref R1 = `A m=2dB`, order fwd = users 0..99).
Reference = `A m=2dB` = `cf_sources.cf3_policies()["C1_A_m2dB"]`.

The B2 student observation (declared in PROGRESS.md S2/D1, 141 dims):
    obs_B2[u] = [ encode_with_time(...)[u] (113) , ctx28[u] (28) ]
    ctx28[u,a] = (# earlier-deciding users this step whose chosen action realises the SAME physical beam
                  (norad_id, cell_id) as user u's slot a) / num_users
Beam identity comes from the environment's own slot tables, because action indices are per-user slots.

The rollout accumulation copies `lp_common.pooled_rollout_rates` statement for statement (plain
left-to-right sums, divided once), as the T0 screen's `t0_common.rollout` does; the only additions are the
per-episode epoch / t=0 hash, the sequential per-user decision seam and an optional observer hook.
"""
from __future__ import annotations

import hashlib
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
from mcrl.env.action_contract import NO_OP_ACTION, HandoverClass, no_op_actions  # noqa: E402
from mcrl.runtime import training_pipeline as tp  # noqa: E402

EXPECTED_TLE_SHA = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
LP_GRID_DT_S = 30.08   # lp_grid.py literal, used ONLY for the derived ho_per_user_min display field
N_ACT = 28
ORACLE_DIR = Path("/home/sat/mcrl-v025-h4-probe-ws/results-oracle")   # READ ONLY
LP_DIR = Path("/home/sat/mcrl-v025-h4-probe-ws/results-lp")           # READ ONLY
TEACHER_STEM = "B-real-floor-R1-{tag}-fwd-ep{i:02d}"
REF_RULE = "C1_A_m2dB"

CMP_FIELDS = ("ee", "bits", "joules", "served", "h_inter", "h_intra", "beams", "user_steps",
              "n_episodes", "served_user_steps", "ho_per_user_min",
              "per_served_user_rate_mean_bps", "per_served_user_rate_p10_bps",
              "per_served_user_rate_min_bps")


def boot() -> str:
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


def seeds_for(tag: str):
    return C.cal_seeds() if tag == "calibration" else C.eval_seeds()


def ref_policy():
    return cfs.cf3_policies()[REF_RULE]


# --------------------------------------------------------------- beam identity / context block
def beam_ids(sim, users: int) -> np.ndarray:
    """(U, 28) int64 global beam key from the env's own slot tables; -1 where there is no beam."""
    tables = sim._candidates.slot_tables
    if len(tables) != users:
        raise RuntimeError("slot table count != users")
    norad = np.stack([np.asarray(t.norad_ids, dtype=np.int64) for t in tables])
    cell = np.stack([np.asarray(t.cell_ids, dtype=np.int64) for t in tables])
    ok = (norad >= 0) & (cell >= 0)
    key = np.where(ok, norad * 1_000_000 + cell, -1)
    return key


class Ctx:
    """Running per-beam count of THIS step's already-decided users, mapped to each user's 28 slots."""

    def __init__(self, key: np.ndarray, users: int):
        self.key = key
        self.users = users
        flat = key.reshape(-1)
        uniq, inv = np.unique(flat, return_inverse=True)
        self.uniq = uniq
        self.slot_id = inv.reshape(key.shape)            # (U, 28) index into uniq
        self.invalid = uniq < 0
        self.count = np.zeros(uniq.size, dtype=np.float64)

    def row(self, u: int) -> np.ndarray:
        """ctx28 for user u: counts / users, 0 on slots without a beam identity."""
        ids = self.slot_id[u]
        v = self.count[ids] / self.users
        v[self.invalid[ids]] = 0.0
        return v.astype(np.float32)

    def commit(self, u: int, action: int) -> None:
        if int(action) == NO_OP_ACTION:
            return
        k = int(self.key[u, int(action)])
        if k < 0:
            raise RuntimeError(f"user {u} chose slot {action} with no beam identity")
        self.count[int(self.slot_id[u, int(action)])] += 1.0


def user_order(order: str, users: int):
    return range(users) if order == "fwd" else range(users - 1, -1, -1)


def ctx_block(sim, users: int, actions, order: str) -> np.ndarray:
    """(U, 28) float32 ctx block for a FIXED set of actions (teacher replay): user u sees only the
    users that decide before it in `order`."""
    ctx = Ctx(beam_ids(sim, users), users)
    out = np.zeros((users, N_ACT), dtype=np.float32)
    for u in user_order(order, users):
        out[u] = ctx.row(u)
        ctx.commit(u, int(actions[u]))
    return out


# --------------------------------------------------------------- rollout
def _rate_stats(rates):
    arr = np.asarray(rates, dtype=np.float64)
    if arr.size == 0:
        return {"per_served_user_rate_mean_bps": float("nan"), "per_served_user_rate_p10_bps": float("nan"),
                "per_served_user_rate_min_bps": float("nan"), "served_user_steps": 0}
    return {"per_served_user_rate_mean_bps": float(arr.mean()),
            "per_served_user_rate_p10_bps": float(np.percentile(arr, 10)),
            "per_served_user_rate_min_bps": float(arr.min()),
            "served_user_steps": int(arr.size)}


def rollout(decide, *, env_factory, encode, seeds, observer=None):
    """`decide(ep, t, env, sim, enc, masks, states) -> actions (U,)`.

    Accumulation identical to lp_common.pooled_rollout_rates / t0_common.rollout.
    `observer(ep, t, env, sim, enc, masks, states, actions)` runs after `decide` and BEFORE env.step;
    it must not touch the env or any generator."""
    rows = []
    rates: list[float] = []
    for i in range(len(seeds)):
        env = env_factory()
        sim = env.environment
        env_rng = np.random.default_rng(seeds[i][0])
        mobility_rng = np.random.default_rng(seeds[i][1])
        users, steps = env.config.num_users, env.config.steps_per_episode
        states, masks, _ = env.reset(env_rng, mobility_rng)
        enc = encode(states, 0)
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "h_inter": 0, "h_intra": 0, "beams": 0.0, "steps": 0,
               "epoch": str(env.epoch),
               "t0_obs112_sha256": hashlib.sha256(
                   np.ascontiguousarray(np.asarray(enc)[:, :112]).tobytes()).hexdigest()}
        for t in range(steps):
            actions = decide(i, t, env, sim, enc, masks, states)
            if observer is not None:
                observer(i, t, env, sim, enc, masks, states, actions)
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
        "bits": bits, "joules": joules, "ee": bits / joules,
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
    out_d["ho_per_user_min"] = (out_d["h_inter"] + out_d["h_intra"]) * 60.0 / LP_GRID_DT_S
    return out_d


def ref_decider():
    rule = ref_policy()

    def decide(ep, t, env, sim, enc, masks, states):
        return rule(states, masks)
    return decide


def fixed_decider(joint):
    """Commit a stored joint action sequence: joint[ep][t] -> (U,) actions."""
    def decide(ep, t, env, sim, enc, masks, states):
        return np.asarray(joint[ep][t], dtype=np.int32)
    return decide


def clone_decider(net, order: str, use_ctx: bool):
    """Sequential greedy clone: user u decides seeing only the earlier users' choices this step."""
    def decide(ep, t, env, sim, enc, masks, states):
        users = len(masks)
        enc = np.asarray(enc, dtype=np.float32)
        acts = no_op_actions(users)
        if not use_ctx:
            with torch.no_grad():
                lg = net(torch.as_tensor(enc)).numpy().astype(np.float64)
            return C.masked_argmax(lg, masks)
        ctx = Ctx(beam_ids(sim, users), users)
        for u in user_order(order, users):
            legal = np.flatnonzero(masks[u].mask)
            if legal.size == 0:
                acts[u] = NO_OP_ACTION
                continue
            x = np.concatenate([enc[u], ctx.row(u)]).astype(np.float32)
            with torch.no_grad():
                lg = net(torch.as_tensor(x[None, :])).numpy().astype(np.float64)[0]
            a = int(legal[int(np.argmax(lg[legal]))])
            acts[u] = a
            ctx.commit(u, a)
        return acts
    return decide


# --------------------------------------------------------------- clone plumbing
def build_clone(cfg, state_dim: int):
    from mcrl.runtime.q_network import DQNNetwork
    return DQNNetwork(state_dim, N_ACT, tuple(cfg.hidden_layers), cfg.activation)


def load_clone(path: Path, cfg):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    net = build_clone(cfg, int(ck["state_dim"]))
    net.load_state_dict(ck["state"])
    net.eval()
    return net, ck


def sha256_file(p) -> str:
    return C.sha256_file(Path(p))


def write_json(path, payload):
    C.write_json(Path(path), payload)


def code_ident() -> dict:
    here = Path(__file__).resolve().parent
    return {"scripts": {p.name: sha256_file(p) for p in sorted(here.glob("*.py"))},
            "tree_commit": (TREE / "COMMIT").read_text().strip()}


def compare(mine: dict, target: dict) -> dict:
    """Bitwise field comparison (the placebo gate)."""
    out = {}
    for k in CMP_FIELDS:
        a, b = mine.get(k), target.get(k)
        out[k] = {"mine": a, "target": b, "equal": bool(a == b)}
    ma, tb = mine.get("ee_ep", []), target.get("ee_ep", [])
    out["ee_ep"] = {"n": len(tb), "equal": bool(len(ma) == len(tb) and all(x == y for x, y in zip(ma, tb)))}
    out["all_equal"] = all(v["equal"] for v in out.values())
    return out
