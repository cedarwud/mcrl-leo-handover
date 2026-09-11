"""CFSCREEN screen 1 -- representability of each source rule from the learner's own
observation, by a behaviour-cloning PROBE.

The probe is a measurement instrument.  It is trained on logged (observation, legal mask,
source action) rows written by collect.py; it never touches the MODQN learner, its
networks, replay or optimizers.  No MODQN update(), no gradient step on any Q-network.

Classifier: the Q-network architecture itself -- mcrl.runtime.q_network.DQNNetwork(112, 28,
hidden=(100, 50, 50), tanh), the same class and TrainerConfig defaults the learner's three
heads use -- trained as a classifier with a MASKED softmax (illegal logits -> -1e9) and
cross-entropy on the source's action.

Two input variants, declared before the run:
  raw : the 112-dim encoded observation exactly as the learner sees it (primary);
  z   : the same, z-scored per dimension on the TRAINING fold (diagnostic: separates
        "information present" from "input scaling").

Split by EPISODE: 3 folds, fold k = episodes with ep % 3 == k held out (8 episodes,
~8000 decisions); the other 16 train.  Of those 16, the two highest-index episodes are an
inner validation set used only to pick the epoch (max inner top-1).  Fixed recipe for
every source: Adam lr 1e-3, batch 256, 100 epochs, torch seed 1000 + k.

Controls, declared before the run:
  NULL  : labels = a uniformly random LEGAL action (numpy seed 7) on A0's states;
          held-out top-1 must sit at chance = mean(1/|legal|).
  TR    : the trained learner's own greedy actions on its own states (positive control:
          a function of exactly this observation by this architecture family).

Decisions with an empty legal mask (source action = NO_OP) are excluded and counted.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as Fnn

sys.path.insert(0, "/home/u24/papers/mcrl-leo-handover/src")
from mcrl.runtime.q_network import DQNNetwork          # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig    # noqa: E402

torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
CFG = TrainerConfig()
HID, ACT = tuple(CFG.hidden_layers), CFG.activation
import os
EPOCHS, BS, LR = int(os.environ.get("CFS_EPOCHS", "100")), 256, 1e-3
# SENSITIVITY (added after the declared 100-epoch run was read: its raw-input best epochs
# sat at 54-93 of 100, i.e. still improving): CFS_EPOCHS=400 writes keys "<var>400".
SUFFIX = "" if EPOCHS == 100 else str(EPOCHS)
TAGS = sys.argv[1].split(",") if len(sys.argv) > 1 else \
    ["A0", "A2", "A9", "A12", "B1", "B2", "TR", "NULL"]
VARIANTS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["raw", "z"]


def load(tag):
    src = "A0" if tag == "NULL" else tag
    d = np.load(RAW / f"{src}.npz")
    X, M, y, ep = d["obs"], d["mask"], d["act"].copy(), d["ep"]
    keep = M.any(1)
    if tag == "NULL":
        rng = np.random.default_rng(7)
        for i in np.flatnonzero(keep):
            y[i] = rng.choice(np.flatnonzero(M[i]))
    return X[keep], M[keep], y[keep], ep[keep], int((~keep).sum())


def fit(Xtr, Mtr, ytr, Xva, Mva, yva, seed):
    torch.manual_seed(seed)
    net = DQNNetwork(Xtr.shape[1], Mtr.shape[1], HID, ACT)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    Xt, Mt, yt = map(torch.as_tensor, (Xtr, Mtr, ytr))
    Xv, Mv, yv = map(torch.as_tensor, (Xva, Mva, yva))
    g = torch.Generator().manual_seed(seed)
    best, best_state, best_ep = -1.0, None, -1
    for e in range(EPOCHS):
        net.train()
        perm = torch.randperm(len(yt), generator=g)
        for i in range(0, len(yt), BS):
            b = perm[i:i + BS]
            logit = net(Xt[b]).masked_fill(~Mt[b], -1e9)
            loss = Fnn.cross_entropy(logit, yt[b])
            opt.zero_grad()
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            acc = (net(Xv).masked_fill(~Mv, -1e9).argmax(1) == yv).float().mean().item()
        if acc > best:
            best, best_ep = acc, e
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
    net.load_state_dict(best_state)
    net.eval()
    return net, best, best_ep


def main():
    t0 = time.time()
    res = {}
    for tag in TAGS:
        X, M, y, ep, n_empty = load(tag)
        for var in VARIANTS:
            key = f"{tag}_{var}{SUFFIX}"
            outp = RAW / f"bc_{key}.npz"
            if outp.exists():
                print(f"# {key}: exists, skipped", flush=True)
                continue
            pred = np.full(len(y), -1, dtype=np.int64)
            logits_all = np.zeros(M.shape, dtype=np.float32)
            folds = []
            for k in range(3):
                te = ep % 3 == k
                tr_eps = np.unique(ep[~te])
                inner = np.isin(ep, tr_eps[-2:])
                trn = (~te) & (~inner)
                mu = X[~te].mean(0)
                sd = X[~te].std(0)
                sd[sd < 1e-12] = 1.0
                if var == "raw":
                    mu, sd = np.zeros_like(mu), np.ones_like(sd)
                f = lambda A: ((A - mu) / sd).astype(np.float32)
                net, va, bep = fit(f(X[trn]), M[trn], y[trn], f(X[inner]), M[inner],
                                   y[inner], 1000 + k)
                with torch.no_grad():
                    lg = net(torch.as_tensor(f(X[te]))).masked_fill(
                        ~torch.as_tensor(M[te]), -1e9).numpy()
                logits_all[te] = lg
                pred[te] = lg.argmax(1)
                top1 = float((pred[te] == y[te]).mean())
                folds.append(dict(fold=k, n_test=int(te.sum()), n_train=int(trn.sum()),
                                  inner_top1=va, best_epoch=bep, test_top1=top1))
                torch.save(dict(state=net.state_dict(), mu=mu, sd=sd, hid=HID, act=ACT,
                                test_eps=np.unique(ep[te]).tolist()),
                           RAW / f"bc_{key}_fold{k}.pt")
                print(f"{key:10s} fold{k} inner={va:.4f}@{bep:3d} test_top1={top1:.4f} "
                      f"n_test={int(te.sum())} t={time.time() - t0:.0f}s", flush=True)
            np.savez_compressed(outp, pred=pred, logits=logits_all, y=y, ep=ep)
            res[key] = dict(folds=folds, n_empty_mask_excluded=n_empty,
                            top1=float((pred == y).mean()))
            (RAW / f"bc_{key}.json").write_text(json.dumps(res[key], indent=1))
    print(f"# total wall {time.time() - t0:.0f}s")


main()
