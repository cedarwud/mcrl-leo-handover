"""CFSCREEN screen 1b -- closed-loop rollout of the held-out behaviour-cloning probes.

Each of the 24 episodes is driven by the fold model that did NOT see that episode in
training (episode e -> fold e % 3), so every decision is out-of-sample by episode.
The probe acts; the source rule is queried on the probe's own states to give the
on-policy agreement.  Same frontier.py harness, exec'd verbatim; its run() unchanged.

READ-ONLY / NO TRAINING: no MODQN update(), no gradient step on any network (the probe is
only evaluated here, in torch.no_grad()).

Usage: bc_rollout.py TAG[,TAG...] VARIANT
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
TAGS = sys.argv[1].split(",")
VAR = sys.argv[2]
N_EP = 24

_src = open(FRONTIER).read()
_cut = _src.index("\nt0 = time.time()\n")
_argv = sys.argv
sys.argv = [FRONTIER, str(N_EP)]
sys.path.insert(0, str(HERE))
F = {"__name__": "frontier_defs", "__file__": FRONTIER}
exec(compile(_src[:_cut], FRONTIER, "exec"), F)
sys.argv = _argv

import torch  # noqa: E402
from mcrl.runtime.q_network import DQNNetwork  # noqa: E402

torch.set_num_threads(1)
ARM = {name: (fn, ck) for name, fn, ck in F["ARMS"]}
NAME = {"A0": "A m=0dB", "A2": "A m=2dB", "A9": "A m=9dB", "A12": "A m=12dB",
        "B1": "B1_NO_NEW_BEAM", "B2": "B2_PREFER_SHARED", "TR": "TRAINED e6b063ef"}
NO_OP = F["NO_OP_ACTION"]


def load_models(tag):
    out = []
    for k in range(3):
        ck = torch.load(ROOT / "raw" / f"bc_{tag}_{VAR}_fold{k}.pt", weights_only=False)
        net = DQNNetwork(112, 28, tuple(ck["hid"]), ck["act"])
        net.load_state_dict(ck["state"])
        net.eval()
        out.append((net, np.asarray(ck["mu"]), np.asarray(ck["sd"]), set(ck["test_eps"])))
    return out


def rollout(tag):
    models = load_models(tag)
    rule = ARM[NAME[tag]][0]
    calls = [0]
    agree = [0, 0]

    def fn(tr, enc, masks, states):
        ep = calls[0] // 10
        net, mu, sd, test_eps = models[ep % 3]
        assert ep in test_eps, (ep, sorted(test_eps))
        mask = np.stack([np.asarray(m.mask, dtype=bool) for m in masks])
        x = ((np.asarray(enc, dtype=np.float64) - mu) / sd).astype(np.float32)
        with torch.no_grad():
            lg = net(torch.as_tensor(x)).masked_fill(~torch.as_tensor(mask), -1e9).numpy()
        a = F["no_op_actions"](len(states))
        has = mask.any(1)
        a[has] = lg[has].argmax(1)
        if tag == "TR":
            ref = tr.select_actions(enc, masks, 0.0)
        else:
            ref = rule(tr, enc, masks, states)
        agree[0] += int((np.asarray(ref)[has] == a[has]).sum())
        agree[1] += int(has.sum())
        calls[0] += 1
        return a

    t0 = time.time()
    o = F["run"](fn, tag == "TR")
    o.update(tag=tag, variant=VAR, onpolicy_agree=agree[0] / agree[1],
             wall_s=time.time() - t0)
    (ROOT / "raw" / f"bcroll_{tag}_{VAR}.json").write_text(json.dumps(o, indent=1))
    print(f"BC[{tag},{VAR}]{'':8s} {o['bits']:14.6e} {o['joules']:14.6e} {o['ee']:16.6f} "
          f"{o['sem']:11.1f} {o['ho']:7.4f} {o['ho1']:8.4f} {o['ho2']:8.4f} "
          f"{o['served']:7.4f} {o['beams']:7.3f}  onpolicy_agree={o['onpolicy_agree']:.4f} "
          f"wall={o['wall_s']:.0f}s", flush=True)


for tag in TAGS:
    if (ROOT / "raw" / f"bcroll_{tag}_{VAR}.json").exists():
        print(f"# {tag}: exists, skipped", flush=True)
        continue
    rollout(tag)
