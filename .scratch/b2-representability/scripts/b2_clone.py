#!/usr/bin/env python3
"""B2-REPR step 3 -- the measurement clones of T_SEQ (NOT the learner; no MODQN update, no env).

Recipe declared in PROGRESS.md S2/D3-D4 before any fit:
  architecture  DQNNetwork(input -> 100 -> 50 -> 50 -> 28, tanh), raw inputs, illegal logits -> -1e9
  input         141 = 113-dim ratio-learner observation + the declared 28-slot ctx block
                (--noctx ablation: the 113 dims only)
  optimiser     Adam lr 1e-3, batch 256, 400 epochs, torch seed 1000 (init + shuffling)
  split         by episode: i % 5 == 4 -> TEST, i % 5 == 3 -> VAL, else TRAIN
  bc            cross-entropy on the teacher's committed action
  soft          cross-entropy toward softmax(adv_std / tau) over LEGAL-AND-ALLOWED slots
  adv_std       adv / ref_bits(step) / s ;  s = RMS over TRAIN legal non-base slots (written to
                results/ADV-SCALE.json before any fit)
  epoch pick    VAL only: min mean teacher-advantage regret adv_std[a_teacher] - adv_std[a_clone]
                (a_clone = masked argmax over LEGAL slots); tie -> max VAL top-1 -> earliest epoch

Usage: b2_clone.py --kind bc [--noctx] | b2_clone.py --kind soft --taus 0.01,0.03,... [--noctx]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2_common as B  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as Fnn  # noqa: E402

EPOCHS, BS, LR, SEED = 400, 256, 1e-3, 1000
TAG = "calibration"      # the training corpus (out of the evaluation set by construction)


def load_data(noctx: bool, ctxfull: bool = False):
    d = dict(np.load(B.WS / "data" / f"B2-train-{TAG}.npz"))
    keep = d["mask"].any(1)
    keep_idx = keep
    n_empty = int((~keep).sum())
    d = {k: v[keep] for k, v in d.items()}
    obs = d["obs"].astype(np.float32)
    X = obs if noctx else np.concatenate([obs, d["ctx"].astype(np.float32)], axis=1)
    if ctxfull:
        cf = np.load(B.WS / "data" / f"B2-ctxfull-{TAG}.npz")["ctxfull"].astype(np.float32)
        X = np.concatenate([X, cf[keep_idx]], axis=1)
    M = d["mask"]
    y = d["action"].astype(np.int64)
    adv_norm = d["adv"].astype(np.float64) / d["ref_bits"][:, None]
    base = d["ref_action"].astype(np.int64)
    ep = d["episode"].astype(np.int64)
    split = np.where(ep % 5 == 4, "TEST", np.where(ep % 5 == 3, "VAL", "TRAIN"))
    # declared scale s: RMS of adv_norm over TRAIN legal NON-BASE slots
    tr = split == "TRAIN"
    sel = M[tr].copy()
    sel[np.arange(sel.shape[0]), base[tr]] = False
    s = float(np.sqrt(np.nanmean(np.square(adv_norm[tr][sel]))))
    adv_std = adv_norm / s
    dis = d["adv_disallowed"]
    scale = {"s_rms_adv_norm_train_legal_nonbase": s,
             "n_train_rows": int(tr.sum()), "n_train_slots_used": int(sel.sum()),
             "adv_norm_train_absmean": float(np.nanmean(np.abs(adv_norm[tr][sel]))),
             "adv_std_train_absmean": float(np.nanmean(np.abs(adv_std[tr][sel])))}
    return dict(X=X, M=M, y=y, adv=adv_std, dis=dis, base=base, split=split, ep=ep,
                n_empty=n_empty, scale=scale, input_dim=int(X.shape[1]))


def soft_targets(A, M, dis, base, tau):
    """softmax(adv_std / tau) over legal-and-allowed slots (the base slot is never disallowed)."""
    sup = M & ~dis
    sup[np.arange(sup.shape[0]), base] = True
    Z = np.where(sup, A / tau, -np.inf)
    Z = Z - np.nanmax(np.where(sup, Z, -np.inf), axis=1, keepdims=True)
    P = np.where(sup, np.exp(Z), 0.0)
    P = np.nan_to_num(P, nan=0.0, posinf=0.0, neginf=0.0)
    P /= P.sum(1, keepdims=True)
    return P.astype(np.float32)


def metrics(logits, y, M, A, dis):
    lg = np.where(M, logits.astype(np.float64), -np.inf)
    pred = lg.argmax(1)
    n = len(y)
    top1 = pred == y
    ly = lg[np.arange(n), y]
    top3 = (lg > ly[:, None]).sum(1) <= 2
    regret = A[np.arange(n), y] - A[np.arange(n), pred]
    z = lg - lg.max(1, keepdims=True)
    logq = z - np.log(np.where(M, np.exp(z), 0.0).sum(1, keepdims=True))
    ce_bits = -logq[np.arange(n), y] / np.log(2.0)
    return {"n": int(n), "top1": float(top1.mean()), "top3": float(top3.mean()),
            "regret_mean": float(np.nanmean(regret)), "regret_p95": float(np.nanpercentile(regret, 95)),
            "regret_gt0_frac": float(np.nanmean(regret > 0)),
            "ce_bits_mean": float(ce_bits.mean()),
            "disallowed_pick_frac": float(dis[np.arange(n), pred].mean()),
            "chance_top1": float((1.0 / M.sum(1)).mean())}


def extra_metrics(logits, y, M, base):
    lg = np.where(M, logits.astype(np.float64), -np.inf)
    pred = lg.argmax(1)
    mv = y != base                      # decisions where the teacher MOVED off the reference
    return {"moved_frac": float(mv.mean()),
            "top1_moved": float((pred == y)[mv].mean()) if mv.any() else float("nan"),
            "top1_stay": float((pred == y)[~mv].mean()) if (~mv).any() else float("nan"),
            "pred_eq_ref_frac": float((pred == base).mean()),
            "teacher_eq_ref_frac": float((y == base).mean())}


def fit(cfg, X, M, y, P, Xv, Mv, yv, Av, disv, kind, input_dim):
    torch.manual_seed(SEED)
    net = B.build_clone(cfg, input_dim)
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
        m = metrics(lv, yv, Mv, Av, disv)
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
    ap.add_argument("--noctx", action="store_true")
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--train-episodes", type=int, default=0,
                    help="learning-curve sensitivity: keep only the first N TRAIN episodes")
    ap.add_argument("--seed", type=int, default=SEED,
                    help="fit-noise sensitivity: torch seed for init and shuffling")
    ap.add_argument("--ctxfull", action="store_true",
                    help="DIAGNOSTIC (non-deployable): append the 28-slot full-context block")
    a = ap.parse_args()
    EPOCHS = a.epochs
    globals()["SEED"] = a.seed
    tle = B.boot()
    cfg = B.learner_config()
    D = load_data(a.noctx, a.ctxfull)
    tr, va, te = D["split"] == "TRAIN", D["split"] == "VAL", D["split"] == "TEST"
    if a.train_episodes:
        keep = sorted({int(k) for k in D["ep"][tr]})[:a.train_episodes]
        tr = tr & np.isin(D["ep"], keep)
    counts = {"TRAIN": int(tr.sum()), "VAL": int(va.sum()), "TEST": int(te.sum()),
              "empty_mask_excluded": D["n_empty"], "input_dim": D["input_dim"],
              "episodes": {s: sorted({int(k) for k in D["ep"][D["split"] == s]})
                           for s in ("TRAIN", "VAL", "TEST")}}
    scale_path = B.WS / "results" / f"ADV-SCALE{'-noctx' if a.noctx else ''}.json"
    if not scale_path.exists():
        B.write_json(scale_path, {**D["scale"], "counts": counts, "tle": tle})
    print(f"data: {counts}\nscale: {D['scale']}", flush=True)
    X, M, y, A, dis, base = D["X"], D["M"], D["y"], D["adv"], D["dis"], D["base"]
    sfx = ("-noctx" if a.noctx else "") + ("-ctxfull" if a.ctxfull else "") + \
          (f"-tr{a.train_episodes}" if a.train_episodes else "") + \
          (f"-s{a.seed}" if a.seed != 1000 else "")
    esfx = "" if EPOCHS == 400 else f"-e{EPOCHS}"
    jobs = [("bc", None)] if a.kind == "bc" else [("soft", float(t)) for t in a.taus.split(",")]
    for kind, tau in jobs:
        name = ("BC" if kind == "bc" else f"SOFT-tau{tau:g}") + sfx + esfx
        mpath = B.WS / "models" / f"{name}.pt"
        rpath = B.WS / "results" / f"CLONE-{name}.json"
        if mpath.exists() and rpath.exists():
            print(f"[skip:exists] {name}", flush=True)
            continue
        t0 = time.time()
        P = soft_targets(A[tr], M[tr], dis[tr], base[tr], tau) if kind == "soft" else None
        net, best_ep, curve = fit(cfg, X[tr], M[tr], y[tr], P, X[va], M[va], y[va], A[va], dis[va],
                                  kind, D["input_dim"])
        with torch.no_grad():
            lt = net(torch.as_tensor(X[te])).masked_fill(~torch.as_tensor(M[te]), -1e9).numpy()
            ltr = net(torch.as_tensor(X[tr])).masked_fill(~torch.as_tensor(M[tr]), -1e9).numpy()
        test_m = {**metrics(lt, y[te], M[te], A[te], dis[te]), **extra_metrics(lt, y[te], M[te], base[te])}
        train_m = {**metrics(ltr, y[tr], M[tr], A[tr], dis[tr]), **extra_metrics(ltr, y[tr], M[tr], base[tr])}
        torch.save({"state": net.state_dict(), "state_dim": D["input_dim"], "kind": kind, "tau": tau,
                    "noctx": bool(a.noctx), "best_epoch": best_ep,
                    "hidden": tuple(cfg.hidden_layers), "activation": cfg.activation,
                    "recipe": {"epochs": EPOCHS, "batch": BS, "lr": LR, "seed": SEED}},
                   mpath.with_suffix(".pt.tmp"))
        mpath.with_suffix(".pt.tmp").replace(mpath)
        res = {"name": name, "kind": kind, "tau": tau, "noctx": bool(a.noctx), "best_epoch": best_ep,
               "input_dim": D["input_dim"], "val_at_best": curve[best_ep], "test": test_m,
               "train": train_m, "val_curve": curve, "counts": counts, "adv_scale": D["scale"],
               "model_sha256": B.sha256_file(mpath), "tle_file_set_sha256": tle,
               "code": B.code_ident(), "wall_s": time.time() - t0}
        B.write_json(rpath, res)
        print(f"{name}: best_epoch={best_ep} VAL regret={curve[best_ep]['regret_mean']:.5f} "
              f"top1={curve[best_ep]['top1']:.4f} | TEST top1={test_m['top1']:.4f} "
              f"top3={test_m['top3']:.4f} regret={test_m['regret_mean']:.5f} "
              f"dis_pick={test_m['disallowed_pick_frac']:.4f} wall={res['wall_s']:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
