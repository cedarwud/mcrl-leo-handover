#!/usr/bin/env python3
"""T0-REPR step 3 -- the two measurement clones of T0 (NOT the learner; no MODQN update, no env).

Architecture: the learner's Q-network class and config, DQNNetwork(113 -> 100 -> 50 -> 50 -> 28, tanh)
(pilot config: hidden (100, 50, 50), tanh), input = the ratio learner's own observation (112 + remaining
steps), raw (no z-scoring).  Illegal logits -> -1e9 (masked softmax).
  bc   : cross-entropy on T0's action (one-hot behaviour cloning, CFSCREEN §1b method)
  soft : cross-entropy toward softmax(T0 score / tau) over the legal actions (soft distillation)
Split BY EPISODE (declared in PROGRESS.md before any fit): collected episode k of every triple is
TEST if k % 5 == 4, VAL if k % 5 == 3, TRAIN otherwise.  Empty-mask decisions excluded (counted).
Recipe (identical for every clone): Adam lr 1e-3, batch 256, 100 epochs, torch seed 1000 (init and
shuffle).  Epoch selection on VAL: min mean T0-score regret (score_T0[a_T0] - score_T0[a_clone]),
tie -> max VAL top-1 -> earliest epoch.  TEST is evaluated once, at the selected epoch, never used to select.
Usage: t0_clone.py --kind bc            |  t0_clone.py --kind soft --taus 0.01,0.03,0.1
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tree" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import t0_common as T  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as Fnn  # noqa: E402

EPOCHS, BS, LR, SEED = 100, 256, 1e-3, 1000
# SENSITIVITY (declared 2026-09-11 ~18:00 UTC, after reading the declared fits' best epochs 96-98/100 and
# BEFORE any closed-loop run): --epochs 400 refits with everything else identical; name suffix "-e400".


def load_data():
    parts = [np.load(T.WS / "data" / f"T0-collect-triple{j}.npz") for j in range(3)]
    d = {k: np.concatenate([p[k] for p in parts]) for k in parts[0].files}
    keep = d["mask"].any(1)
    n_empty = int((~keep).sum())
    d = {k: v[keep] for k, v in d.items()}
    kmod = d["k"].astype(np.int64) % 5
    split = np.where(kmod == 4, "TEST", np.where(kmod == 3, "VAL", "TRAIN"))
    return d, split, n_empty


def soft_targets(S, M, tau):
    Z = np.where(M, S / tau, -np.inf)
    Z = Z - Z.max(1, keepdims=True)
    P = np.where(M, np.exp(Z), 0.0)
    P /= P.sum(1, keepdims=True)
    return P.astype(np.float32)


def metrics(logits, y, M, S, a_mg):
    lg = np.where(M, logits.astype(np.float64), -np.inf)
    pred = lg.argmax(1)                                   # first index on ties
    n = len(y)
    top1 = pred == y
    ly = lg[np.arange(n), y]
    top3 = (lg > ly[:, None]).sum(1) <= 2
    regret = S[np.arange(n), y] - S[np.arange(n), pred]
    # held-out cross-entropy of the clone's masked softmax at T0's action (bits): upper bound on H(a|o)
    z = lg - lg.max(1, keepdims=True)
    logq = z - np.log(np.where(M, np.exp(z), 0.0).sum(1, keepdims=True))
    ce_bits = -logq[np.arange(n), y] / np.log(2.0)
    act = y != a_mg                                       # price-active: T0 differs from MAX_NOMINAL_GAIN
    return {"n": int(n), "top1": float(top1.mean()), "top3": float(top3.mean()),
            "regret_mean": float(regret.mean()), "regret_p95": float(np.percentile(regret, 95)),
            "regret_gt0_frac": float((regret > 0).mean()),
            "ce_bits_mean": float(ce_bits.mean()),
            "price_active_frac": float(act.mean()),
            "top1_price_active": float(top1[act].mean()) if act.any() else float("nan"),
            "top1_price_inactive": float(top1[~act].mean()) if (~act).any() else float("nan"),
            "regret_mean_price_active": float(regret[act].mean()) if act.any() else float("nan"),
            "chance_top1": float((1.0 / M.sum(1)).mean())}


def fit(cfg, X, M, y, P, Xv, Mv, yv, Sv, amgv, kind):
    torch.manual_seed(SEED)
    net = T.build_clone(cfg, X.shape[1])
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    Xt, Mt, yt = torch.as_tensor(X), torch.as_tensor(M), torch.as_tensor(y)
    Pt = torch.as_tensor(P) if P is not None else None
    Xvt, Mvt = torch.as_tensor(Xv), torch.as_tensor(Mv)
    g = torch.Generator().manual_seed(SEED)
    best_key, best_state, best_ep, curve = None, None, -1, []
    for e in range(EPOCHS):
        net.train()
        perm = torch.randperm(len(yt), generator=g)
        tot, nb = 0.0, 0
        for i in range(0, len(yt), BS):
            b = perm[i:i + BS]
            logit = net(Xt[b]).masked_fill(~Mt[b], -1e9)
            if kind == "bc":
                loss = Fnn.cross_entropy(logit, yt[b])
            else:
                loss = -(Pt[b] * Fnn.log_softmax(logit, dim=1)).sum(1).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += float(loss.item())
            nb += 1
        net.eval()
        with torch.no_grad():
            lv = net(Xvt).masked_fill(~Mvt, -1e9).numpy()
        m = metrics(lv, yv, Mv, Sv, amgv)
        m["epoch"], m["train_loss"] = e, tot / nb
        curve.append(m)
        key = (m["regret_mean"], -m["top1"], e)
        if best_key is None or key < best_key:
            best_key, best_ep = key, e
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
    net.load_state_dict(best_state)
    net.eval()
    return net, best_ep, curve


def main() -> int:
    global EPOCHS
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=("bc", "soft"), required=True)
    ap.add_argument("--taus", default="")
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    a = ap.parse_args()
    EPOCHS = a.epochs
    suffix = "" if EPOCHS == 100 else f"-e{EPOCHS}"
    tle = T.boot()
    cfg = T.learner_config()
    d, split, n_empty = load_data()
    tr, va, te = split == "TRAIN", split == "VAL", split == "TEST"
    counts = {"TRAIN": int(tr.sum()), "VAL": int(va.sum()), "TEST": int(te.sum()), "empty_mask_excluded": n_empty,
              "episodes": {s: int(len({(int(j), int(k)) for j, k in zip(d["triple"][split == s], d["k"][split == s])}))
                           for s in ("TRAIN", "VAL", "TEST")}}
    print(f"data: {counts}", flush=True)
    X, M, y, S, amg = d["obs"].astype(np.float32), d["mask"], d["act"].astype(np.int64), d["score"], d["a_mg"]
    jobs = [("bc", None)] if a.kind == "bc" else [("soft", float(t)) for t in a.taus.split(",")]
    for kind, tau in jobs:
        name = ("BC" if kind == "bc" else f"SOFT-tau{tau:g}") + suffix
        mpath = T.WS / "models" / f"{name}.pt"
        rpath = T.WS / "results" / f"CLONE-{name}.json"
        if mpath.exists() and rpath.exists():
            print(f"[skip:exists] {name}", flush=True)
            continue
        t0 = time.time()
        P = soft_targets(S[tr], M[tr], tau) if kind == "soft" else None
        net, best_ep, curve = fit(cfg, X[tr], M[tr], y[tr], P, X[va], M[va], y[va], S[va], amg[va], kind)
        with torch.no_grad():
            lt = net(torch.as_tensor(X[te])).masked_fill(~torch.as_tensor(M[te]), -1e9).numpy()
            ltr = net(torch.as_tensor(X[tr])).masked_fill(~torch.as_tensor(M[tr]), -1e9).numpy()
        test_m = metrics(lt, y[te], M[te], S[te], amg[te])
        train_m = metrics(ltr, y[tr], M[tr], S[tr], amg[tr])
        torch.save({"state": net.state_dict(), "state_dim": int(X.shape[1]), "kind": kind, "tau": tau,
                    "best_epoch": best_ep, "hidden": tuple(cfg.hidden_layers), "activation": cfg.activation,
                    "recipe": {"epochs": EPOCHS, "batch": BS, "lr": LR, "seed": SEED}}, mpath.with_suffix(".pt.tmp"))
        mpath.with_suffix(".pt.tmp").replace(mpath)
        res = {"name": name, "kind": kind, "tau": tau, "best_epoch": best_ep, "val_at_best": curve[best_ep],
               "test": test_m, "train": train_m, "val_curve": curve, "counts": counts,
               "model_sha256": T.sha256_file(mpath), "tle_file_set_sha256": tle, "code": T.code_ident(),
               "wall_s": time.time() - t0}
        T.write_json(rpath, res)
        print(f"{name}: best_epoch={best_ep} VAL regret={curve[best_ep]['regret_mean']:.5f} "
              f"top1={curve[best_ep]['top1']:.4f} | TEST top1={test_m['top1']:.4f} top3={test_m['top3']:.4f} "
              f"regret={test_m['regret_mean']:.5f} wall={res['wall_s']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
