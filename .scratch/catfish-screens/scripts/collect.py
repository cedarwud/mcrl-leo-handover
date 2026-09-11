"""CFSCREEN collection: roll each catfish source rule (and the trained learner) on the
FEASFRONT harness and log, per (episode, step, user) decision, the learner's own
observation, the legal mask, the source's action, and what every OTHER source rule and
the trained learner would choose on that same state.

READ-ONLY / NO TRAINING: update() is never called, no optimizer is touched, no gradient
step on any Q-network.  The checkpoint is loaded read-only in every cell so that the
learner can be QUERIED on the source's states (load_checkpoint does not touch the RNG
streams, modqn.py:1076-1095 / FEASFRONT JSRL placebo h=10).

HARNESS REUSE, NOT REIMPLEMENTATION: frontier.py is exec'd verbatim up to (not including)
its main loop (`t0 = time.time()`), so the rules (`make_rule`, `pick`, `r_no_new_beam`,
`r_prefer_shared`, `arm_hold`, `arm_trained`), `build_env`, the trainer config and the
`run()` rollout loop are frontier.py's own objects.  Logging is a wrapper around the arm
function; `run()` itself is called unchanged, so its pooled-EE / handover output must
reproduce frontier.out bit-for-bit (placebo).

Usage:  collect.py N_EP TAG[,TAG...] [OUTPREFIX]
  TAG in A0 A2 A9 A12 B1 B2 TR
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FRONTIER = ("/home/u24/papers/mcrl-leo-handover/.scratch/feasible-frontier/"
            "scripts/frontier.py")

N_EP = int(sys.argv[1])
TAGS = sys.argv[2].split(",")
PREFIX = sys.argv[3] if len(sys.argv) > 3 else ""

# ---- exec frontier.py's definitions verbatim -------------------------------------
_src = open(FRONTIER).read()
_cut = _src.index("\nt0 = time.time()\n")
_argv = sys.argv
sys.argv = [FRONTIER, str(N_EP)]          # frontier reads N_EP from argv[1]
sys.path.insert(0, str(HERE))             # identical-bytes copy of c3s_physics_override
F = {"__name__": "frontier_defs", "__file__": FRONTIER}
exec(compile(_src[:_cut], FRONTIER, "exec"), F)
sys.argv = _argv
assert F["N_EP"] == N_EP

import torch  # noqa: E402  (after frontier's own imports)
torch.set_num_threads(1)

ARM = {name: (fn, ck) for name, fn, ck in F["ARMS"]}
NAME = {"A0": "A m=0dB", "A2": "A m=2dB", "A9": "A m=9dB", "A12": "A m=12dB",
        "B1": "B1_NO_NEW_BEAM", "B2": "B2_PREFER_SHARED", "TR": "TRAINED e6b063ef"}
# query columns: every rule evaluated on the rolled source's states, plus the
# always-incumbent baseline (HOLD_WHILE_LEGAL) and the learner's greedy action.
QCOLS = ["A0", "A2", "A9", "A12", "B1", "B2", "HOLD", "TR"]
QFN = {k: ARM[NAME[k]][0] for k in ["A0", "A2", "A9", "A12", "B1", "B2"]}
QFN["HOLD"] = ARM["D_HOLD_WHILE_LEGAL"][0]
NO_OP = F["NO_OP_ACTION"]


def learner_greedy(q, mask):
    """Masked argmax of the scalarized Q -- the same composition as
    MODQNTrainer._select_masked_greedy_action, computed WITHOUT touching _train_rng."""
    out = np.full(q.shape[0], NO_OP, dtype=np.int64)
    for u in range(q.shape[0]):
        if mask[u].any():
            row = q[u].astype(np.float64).copy()
            row[~mask[u]] = -np.inf
            out[u] = int(np.argmax(row))
    return out


def collect(tag):
    fn, _ = ARM[NAME[tag]]
    log = {k: [] for k in ("obs", "mask", "gain", "load", "inc", "act", "q", "qry")}
    calls = [0]

    def wrapped(tr, enc, masks, states):
        a = fn(tr, enc, masks, states)
        mask = np.stack([np.asarray(m.mask, dtype=bool) for m in masks])
        q = tr.scalarized_q_values(enc)                      # (U, 28), no RNG
        qry = np.stack([np.asarray(QFN[k](tr, enc, masks, states), dtype=np.int64)
                        for k in QCOLS[:-1]] + [learner_greedy(q, mask)], axis=1)
        log["obs"].append(np.asarray(enc, dtype=np.float32).copy())
        log["mask"].append(mask)
        log["gain"].append(np.stack([np.asarray(s.channel_quality, dtype=np.float64)
                                     for s in states]))
        log["load"].append(np.stack([np.asarray(s.beam_loads, dtype=np.float64)
                                     for s in states]))
        log["inc"].append(np.array([F["incumbent_slot"](s) for s in states]))
        log["act"].append(np.asarray(a, dtype=np.int64).copy())
        log["q"].append(np.asarray(q, dtype=np.float32))
        log["qry"].append(qry)
        calls[0] += 1
        return a

    t0 = time.time()
    o = F["run"](wrapped, True)          # frontier.run, unchanged; ckpt loaded read-only
    U = log["act"][0].shape[0]
    T = calls[0] // N_EP
    assert calls[0] == N_EP * T, (calls[0], N_EP)
    n = calls[0]
    ep = np.repeat(np.arange(n) // T, U)
    st = np.repeat(np.arange(n) % T, U)
    us = np.tile(np.arange(U), n)
    arr = {k: np.concatenate(v, axis=0) for k, v in log.items()}
    self_col = QCOLS.index(tag)
    # the source's own action must equal its own query column (purity check)
    mism = int((arr["act"] != arr["qry"][:, self_col]).sum())
    out = ROOT / "raw" / f"{PREFIX}{tag}.npz"
    np.savez_compressed(out, ep=ep, t=st, u=us, qcols=np.array(QCOLS), **arr)
    o = {k: v for k, v in o.items()}
    o.update(tag=tag, arm=NAME[tag], n_ep=N_EP, T=T, U=U, rows=int(arr["act"].size),
             self_query_mismatch=mism, wall_s=time.time() - t0)
    (ROOT / "raw" / f"{PREFIX}{tag}.json").write_text(json.dumps(o, indent=1))
    print(f"{NAME[tag]:22s} {o['bits']:14.6e} {o['joules']:14.6e} {o['ee']:16.6f} "
          f"{o['sem']:11.1f} {o['ho']:7.4f} {o['ho1']:8.4f} {o['ho2']:8.4f} "
          f"{o['served']:7.4f} {o['beams']:7.3f} {o['scalar']:8.4f}  "
          f"self_mismatch={mism} wall={o['wall_s']:.0f}s", flush=True)


for tag in TAGS:
    if (ROOT / "raw" / f"{PREFIX}{tag}.npz").exists():
        print(f"# {tag}: exists, skipped", flush=True)
        continue
    collect(tag)
