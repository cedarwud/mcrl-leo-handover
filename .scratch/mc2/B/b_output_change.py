#!/usr/bin/env python3
"""Lane B: did the overrides land in the learner's greedy policy?  (development lane)

Read-only, no training.  Loads an ep-100 policy checkpoint (``policy-epNNNNN.pt``
from ``scripts/run_dev_e0.py``), rolls the 24 DEVVAL episodes greedily -- fresh env
per episode, ``default_rng(9_211_000+i)`` / ``default_rng(9_212_000+i)``, the
deployed masked argmax of ``S = Q_B - eta~ Q_E - lambda Q_H`` (first index on ties),
no training generator -- and at every decision row (a user with >= 1 legal action)
computes

* ``a^A`` = T0 on the RAW state (``cf_teacher.t0_scores``), every ``t``;
* ``a^B`` (the controller's ``a^F``) = T_NEXT with the live driver and the current
  ``StepObservation.candidates``; B ABSTAINS at ``t = T-1``, so every B statistic is
  over ``t < T-1`` only,

and reports greedy agreement with ``a^A``, with ``a^B``, and on the rows where
``a^A != a^B`` which of the two the learner follows (or neither).

``--also OTHER.pt`` scores a SECOND checkpoint's greedy action on the SAME host
trajectory, so two policies are compared on identical states (each policy's own
roll-out diverges after the first differing action, so this is the only literal
"same states" comparison).

``--judge`` additionally reconstructs the v1 gate on the visited states: inside
``cf_credit.frozen_driver_positions``, with a deep-copied generator, it scores
``kappa(a^A)`` and ``kappa(a^B)`` of the unilateral deviations against the rolled
joint action and marks a row "would override" iff ``kappa(a^B) > kappa(a^A)``
strictly.  This is side-effect-free by the same contract the training judge uses;
the script PROVES it per step by comparing the env generator state before/after and
by ``assert_committed_parity`` against the committed step.  The background is the
GREEDY joint action, not training's epsilon-greedy one, so this is the gate at
deployment, not a replay of the training decisions.

Identity: the pooled EE of the host roll-out is recomputed exactly as
``cf_dev.dev_rollout`` does and must EQUAL the ``ee`` / ``ee_ep`` of the DEVVAL file
of the same checkpoint (``--devval``).

Usage::

    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \\
    python b_output_change.py --repo /path/to/tree --policy RUN/policy-ep00100.pt \\
        [--also OTHER/policy-ep00100.pt] [--devval RUN/devval-ep00100.json] \\
        [--judge] [--episodes 24] [--out OUT.json]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

TLE = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
TLE_DEFAULT = "/home/u24/mcrl-runtime/tle-pinned-427e6a91"
DEVVAL_ENV, DEVVAL_MOB = 9_211_000, 9_212_000


def _counter() -> dict:
    return {"rows": 0, "agree_A": 0, "rows_B": 0, "agree_B": 0, "agree_A_tB": 0,
            "dis": 0, "dis_A": 0, "dis_B": 0, "dis_neither": 0,
            "same": 0, "same_follow": 0,
            "ovr": 0, "ovr_A": 0, "ovr_B": 0, "ovr_neither": 0,
            "rej": 0, "rej_A": 0, "rej_B": 0, "rej_neither": 0}


def _score(c: dict, g: int, aa: int, ab: int | None, would: bool | None) -> None:
    c["rows"] += 1
    c["agree_A"] += g == aa
    if ab is None:
        return
    c["rows_B"] += 1
    c["agree_B"] += g == ab
    c["agree_A_tB"] += g == aa
    if aa != ab:
        c["dis"] += 1
        c["dis_A"] += g == aa
        c["dis_B"] += g == ab
        c["dis_neither"] += g not in (aa, ab)
        if would is not None:
            key = "ovr" if would else "rej"
            c[key] += 1
            c[key + "_A"] += g == aa
            c[key + "_B"] += g == ab
            c[key + "_neither"] += g not in (aa, ab)
    else:
        c["same"] += 1
        c["same_follow"] += g == aa


def _report(c: dict) -> dict:
    f = lambda n, d: (n / d if d else None)            # noqa: E731
    return {
        "decision_rows": c["rows"], "rows_t_lt_T1": c["rows_B"],
        "agreement_with_A_all_t": f(c["agree_A"], c["rows"]),
        "agreement_with_A_t_lt_T1": f(c["agree_A_tB"], c["rows_B"]),
        "agreement_with_B_t_lt_T1": f(c["agree_B"], c["rows_B"]),
        "A_B_disagreement_rate": f(c["dis"], c["rows_B"]),
        "on_disagreement_follows_A": f(c["dis_A"], c["dis"]),
        "on_disagreement_follows_B": f(c["dis_B"], c["dis"]),
        "on_disagreement_follows_neither": f(c["dis_neither"], c["dis"]),
        "on_agreement_follows_both": f(c["same_follow"], c["same"]),
        "judge_would_override_rows": c["ovr"],
        "override_rows_follows_A": f(c["ovr_A"], c["ovr"]),
        "override_rows_follows_B": f(c["ovr_B"], c["ovr"]),
        "override_rows_follows_neither": f(c["ovr_neither"], c["ovr"]),
        "gate_rejected_rows": c["rej"],
        "rejected_rows_follows_A": f(c["rej_A"], c["rej"]),
        "rejected_rows_follows_B": f(c["rej_B"], c["rej"]),
        "counts": c,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--also", type=Path, default=None,
                    help="a second checkpoint scored on the HOST trajectory (same states)")
    ap.add_argument("--devval", type=Path, default=None)
    ap.add_argument("--judge", action="store_true",
                    help="reconstruct the v1 gate on the visited states (side-effect-free)")
    ap.add_argument("--episodes", type=int, default=24)
    ap.add_argument("--tle-root", default=TLE_DEFAULT)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    import os
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        if os.environ.get(key) != "1":
            raise SystemExit(f"{key} must be 1")
    os.environ.setdefault("MCRL_TLE_ROOT", str(a.tle_root))
    repo = a.repo.resolve()
    sys.path.insert(0, str(repo / "scripts"))
    sys.path.insert(0, str(repo / "src"))

    import numpy as np
    import torch

    import mcrl
    if not str(Path(mcrl.__file__).resolve()).startswith(str((repo / "src").resolve())):
        raise SystemExit(f"wrong mcrl tree: {mcrl.__file__}")
    import cf3_common as C
    from mcrl.algorithms import cf_judge as cfj
    from mcrl.algorithms import cf_teacher as cft
    from mcrl.algorithms import cf_tnext as cftn
    from mcrl.algorithms.cf_ratio import DT_S, encode_with_time, trainer_config_from_payload
    from mcrl.algorithms.cf_sources import HEAD_B, HEAD_E, HEAD_H
    from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS, no_op_actions
    from mcrl.runtime import training_pipeline as tp
    from mcrl.runtime.q_network import DQNNetwork

    torch.set_num_threads(1)
    tle = tp.assert_tle_archive_pinned()
    if tle != TLE:
        raise SystemExit(f"TLE file set {tle} is not the pinned archive")

    def load(path: Path):
        raw = path.read_bytes()
        payload = torch.load(path, map_location="cpu", weights_only=False)
        if payload.get("schema") not in ("cf-dev-policy-v1", "cf-ratio-policy-v1"):
            raise SystemExit(f"not a cf policy checkpoint: {payload.get('schema')!r}")
        cfg = trainer_config_from_payload(payload)
        st = payload["settings"]
        eta, lam = float(payload["eta"]), float(payload["lambda"])
        eta_tilde = eta * float(st["joules_scale"]) / float(st["bits_scale"])
        if "eta_tilde" in payload and float(payload["eta_tilde"]) != eta_tilde:
            raise SystemExit("eta_tilde in the payload does not match eta * s_E / s_B")
        nets = []
        for sd in payload["q_networks"]:
            net = DQNNetwork(int(payload["state_dim"]), NUM_ACTIONS,
                             tuple(cfg.hidden_layers), cfg.activation)
            net.load_state_dict(sd)
            net.eval()
            nets.append(net)
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                "cfg": cfg, "eta_tilde": eta_tilde, "lam": lam, "nets": nets,
                "dev_settings": payload.get("dev_settings"),
                "judge_spec": payload.get("judge_spec"), "episode": payload.get("episode")}

    host = load(a.policy)
    other = load(a.also) if a.also else None
    if other and other["cfg"] != host["cfg"]:
        print("NOTE: the two checkpoints carry different trainer configs")

    def greedy(model, enc, masks):
        """``CFRatioTrainer.greedy_actions``, statement for statement."""
        with torch.no_grad():
            st = torch.tensor(enc, dtype=torch.float32)
            q = [model["nets"][i](st).cpu().numpy() for i in range(3)]
        combined = q[HEAD_B] - model["eta_tilde"] * q[HEAD_E] - model["lam"] * q[HEAD_H]
        out = no_op_actions(len(masks))
        for uid in range(len(masks)):
            mask = masks[uid].mask
            if np.flatnonzero(mask).size == 0:
                out[uid] = NO_OP_ACTION
                continue
            row = combined[uid].copy()
            row[~mask] = -np.inf
            out[uid] = int(np.argmax(row))
        return out

    factory = C.env_factory()
    host_c, other_c = _counter(), _counter()
    rows_ep, judge_evals, steps_T = [], 0, None
    for i in range(int(a.episodes)):
        env = factory()
        env_rng = np.random.default_rng(DEVVAL_ENV + i)
        mob_rng = np.random.default_rng(DEVVAL_MOB + i)
        users, T = env.config.num_users, env.config.steps_per_episode
        steps_T = T
        states, masks, observation = env.reset(env_rng, mob_rng)
        enc = encode_with_time(states, 0, users, host["cfg"], T)
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "epoch": str(getattr(env, "epoch", None)),
               "t0_obs112_sha256": hashlib.sha256(
                   np.ascontiguousarray(np.asarray(enc)[:, :112]).tobytes()).hexdigest()}
        for t in range(T):
            g = greedy(host, enc, masks)
            g2 = greedy(other, enc, masks) if other else None
            _scores, a_a, legal = cft.t0_scores(states, masks)
            final = t >= T - 1
            a_b = None
            if not final:
                a_b, _diag, _geo = cftn.tnext_actions(
                    states, masks, driver=env.environment.driver,
                    candidates=observation.candidates, is_final_step=False)
            would: dict[int, bool] = {}
            judge = None
            if a.judge and not final:
                before = copy.deepcopy(env_rng.bit_generator.state)
                with cfj.StepJudge(env, g, env_rng) as judge:
                    judge.base()
                    for u in range(users):
                        if not bool(legal[u].any()):
                            continue
                        aa, ab = int(a_a[u]), int(a_b[u])
                        if aa == ab:
                            continue
                        would[u] = cfj.strictly_better(judge.kappa(u, ab),
                                                      judge.kappa(u, aa))
                judge_evals += judge.evaluations
                if env_rng.bit_generator.state != before:
                    raise SystemExit("the judge advanced env_rng -- NOT side-effect-free")
            for u in range(users):
                if not bool(legal[u].any()):
                    continue
                aa = int(a_a[u])
                ab = None if a_b is None else int(a_b[u])
                w = would.get(u) if (a.judge and not final and ab is not None and aa != ab) else None
                _score(host_c, int(g[u]), aa, ab, w)
                if other:
                    _score(other_c, int(g2[u]), aa, ab, w)
            res = env.step(g, env_rng)
            out = env.last_outcome
            if judge is not None:
                judge.assert_committed_parity(out)
            row["bits"] += float(out.energy.system_throughput_bps) * DT_S
            row["joules"] += float(out.energy.system_consumed_power_w) * DT_S
            row["served"] += int(out.energy.served)
            row["user_steps"] += users
            observation = out.observation
            states, masks = res.user_states, res.action_masks
            enc = encode_with_time(states, t + 1, users, host["cfg"], T)
            if res.done:
                break
        rows_ep.append(row)

    bits = joules = 0.0
    for r in rows_ep:
        bits += r["bits"]
        joules += r["joules"]
    ee = bits / joules
    ee_ep = [r["bits"] / r["joules"] if r["joules"] > 0 else float("nan") for r in rows_ep]

    report = {
        "host": {k: host[k] for k in ("path", "sha256", "episode", "dev_settings", "judge_spec")},
        "also": (None if not other else
                 {k: other[k] for k in ("path", "sha256", "episode", "dev_settings", "judge_spec")}),
        "tle": tle, "episodes": int(a.episodes), "steps_per_episode": steps_T,
        "judge_reconstructed": bool(a.judge), "judge_evaluations": judge_evals,
        "host_ee": ee, "host_bits": bits, "host_joules": joules,
        "host_served": sum(r["served"] for r in rows_ep) / sum(r["user_steps"] for r in rows_ep),
        "host_stats": _report(host_c),
        "also_stats": (_report(other_c) if other else None),
        "ee_ep": ee_ep, "epochs": [r["epoch"] for r in rows_ep],
        "obs0": [r["t0_obs112_sha256"] for r in rows_ep],
    }
    if a.devval is not None:
        dv = json.loads(a.devval.read_text())
        report["identity"] = {
            "devval_file": str(a.devval),
            "ee_equals_devval": ee == dv["ee"],
            "ee_ep_equals_devval": ee_ep == dv["ee_ep"],
            "epochs_equal": report["epochs"] == [r.get("epoch") for r in dv["episodes"]],
            "obs0_equal": report["obs0"] == [r.get("t0_obs112_sha256") for r in dv["episodes"]],
            "devval_config_hash": dv.get("config_hash"), "devval_episode": dv.get("episode"),
        }
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("ee_ep", "epochs", "obs0")}, indent=2, default=str))
    if a.out:
        a.out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str))
    ident = report.get("identity")
    if ident and not all(ident[k] for k in ("ee_equals_devval", "ee_ep_equals_devval",
                                            "epochs_equal", "obs0_equal")):
        print("IDENTITY FAIL: this roll-out is not the DEVVAL reading of the checkpoint",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
