#!/usr/bin/env python3
"""Lane B: "is the second source actually doing anything?"  (NOT RUN YET.)

Development lane, read-only, no training.  Loads ONE policy checkpoint
(``policy-epNNNNN.pt`` written by ``scripts/run_dev_e0.py``), rolls the 24 DEVVAL
episodes greedily -- fresh environment per episode, ``default_rng(9_211_000+i)`` /
``default_rng(9_212_000+i)``, the deployed masked argmax of
``S = Q_B - eta~ Q_E - lambda Q_H`` (first index on ties), no training generator --
and at every decision row (a user with >= 1 legal action) computes

* ``a^A`` = T0 on the RAW state (``cf_teacher.t0_scores``), every t;
* ``a^B`` = T_NEXT with a ``TeacherContext``-equivalent built on the ROLLOUT env
  (live driver, the current ``StepObservation.candidates``); B ABSTAINS at
  ``t = T-1`` (its final-step output would be T0's action), so B statistics use
  ``t < T-1`` only;

and reports greedy agreement with ``a^A``, with ``a^B``, and on rows where
``a^A != a^B`` (t < T-1) how often the learner follows A, follows B, or neither.
Run it on the FULL, A-only and B-only checkpoints of the same seed and compare:
if FULL's follow-B share on disagreement rows is not above A-only's, the second
source did not move the deployed policy.

Identity check: the pooled EE of this rollout is recomputed exactly as
``cf_dev.dev_rollout`` does and must EQUAL the ``ee`` / ``ee_ep`` of the DEVVAL
file of the same checkpoint (``--devval``).  That proves the greedy rule, the
encoding and the episodes are the ones the run read, and that the T_NEXT
lookahead did not perturb the environment (it must be side-effect-free).

Usage (on a host with the pinned TLE archive; single-threaded)::

    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \\
    python b_output_change.py --repo /path/to/tree \\
        --policy RUN/policy-ep00100.pt --devval RUN/devval-ep00100.json \\
        --out RUN-output-change-ep00100.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TLE = "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
DEVVAL_ENV, DEVVAL_MOB = 9_211_000, 9_212_000


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True,
                    help="the code tree whose src/ and scripts/ are used (sys.path first)")
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--devval", type=Path, default=None,
                    help="devval-epNNNNN.json of the SAME checkpoint (identity check)")
    ap.add_argument("--episodes", type=int, default=24)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()

    import os
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        if os.environ.get(key) != "1":
            raise SystemExit(f"{key} must be 1")
    repo = a.repo.resolve()
    # The server venv's editable install may point at a stale tree: put THIS tree first.
    sys.path.insert(0, str(repo / "scripts"))
    sys.path.insert(0, str(repo / "src"))

    import numpy as np
    import torch

    import mcrl
    if not str(Path(mcrl.__file__).resolve()).startswith(str((repo / "src").resolve())):
        raise SystemExit(f"wrong mcrl tree: {mcrl.__file__}")
    import cf3_common as C
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

    # ---------------------------------------------------------------- policy
    raw = a.policy.read_bytes()
    policy_sha = hashlib.sha256(raw).hexdigest()
    payload = torch.load(a.policy, map_location="cpu", weights_only=False)
    if payload.get("schema") not in ("cf-dev-policy-v1", "cf-ratio-policy-v1"):
        raise SystemExit(f"not a cf policy checkpoint: {payload.get('schema')!r}")
    cfg = trainer_config_from_payload(payload)
    settings = payload["settings"]
    eta, lam = float(payload["eta"]), float(payload["lambda"])
    eta_tilde = eta * float(settings["joules_scale"]) / float(settings["bits_scale"])
    if "eta_tilde" in payload and float(payload["eta_tilde"]) != eta_tilde:
        raise SystemExit("eta_tilde in the payload does not match eta * s_E / s_B")
    nets = []
    for sd in payload["q_networks"]:
        net = DQNNetwork(int(payload["state_dim"]), NUM_ACTIONS, tuple(cfg.hidden_layers),
                         cfg.activation)
        net.load_state_dict(sd)
        net.eval()
        nets.append(net)

    def greedy(enc, masks):
        """``CFRatioTrainer.greedy_actions`` statement for statement (no generator)."""
        with torch.no_grad():
            st = torch.tensor(enc, dtype=torch.float32)
            q = [nets[i](st).cpu().numpy() for i in range(3)]
        combined = q[HEAD_B] - eta_tilde * q[HEAD_E] - lam * q[HEAD_H]
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

    # ---------------------------------------------------------------- rollout
    factory = C.env_factory()
    steps_T = None
    tot = {"rows": 0, "agree_A": 0, "rows_B": 0, "agree_B": 0, "agree_A_tB": 0,
           "dis_rows": 0, "dis_follow_A": 0, "dis_follow_B": 0, "dis_neither": 0,
           "same_rows": 0, "same_follow": 0}
    per_step: list[dict] = []
    tnext_diag: dict[str, int] = {}
    rows_ep = []
    for i in range(int(a.episodes)):
        env = factory()
        env_rng = np.random.default_rng(DEVVAL_ENV + i)
        mob_rng = np.random.default_rng(DEVVAL_MOB + i)
        users, T = env.config.num_users, env.config.steps_per_episode
        steps_T = T
        if not per_step:
            per_step = [dict(rows=0, agree_A=0, rows_B=0, agree_B=0, dis_rows=0,
                             dis_follow_A=0, dis_follow_B=0) for _ in range(T)]
        states, masks, observation = env.reset(env_rng, mob_rng)
        enc = encode_with_time(states, 0, users, cfg, T)
        row = {"bits": 0.0, "joules": 0.0, "served": 0, "user_steps": 0,
               "epoch": str(getattr(env, "epoch", None)),
               "t0_obs112_sha256": hashlib.sha256(
                   np.ascontiguousarray(np.asarray(enc)[:, :112]).tobytes()).hexdigest()}
        for t in range(T):
            g = greedy(enc, masks)
            _scores, a_a, legal = cft.t0_scores(states, masks)
            final = t >= T - 1
            a_b = None
            if not final:
                a_b, diag, _geo = cftn.tnext_actions(
                    states, masks, driver=env.environment.driver,
                    candidates=observation.candidates, is_final_step=False)
                for kk, vv in diag.items():
                    tnext_diag[kk] = tnext_diag.get(kk, 0) + int(vv)
            ps = per_step[t]
            for u in range(users):
                if not bool(legal[u].any()):
                    continue
                ga, aa = int(g[u]), int(a_a[u])
                tot["rows"] += 1
                ps["rows"] += 1
                tot["agree_A"] += ga == aa
                ps["agree_A"] += ga == aa
                if a_b is None:
                    continue
                ab = int(a_b[u])
                tot["rows_B"] += 1
                ps["rows_B"] += 1
                tot["agree_B"] += ga == ab
                ps["agree_B"] += ga == ab
                tot["agree_A_tB"] += ga == aa
                if aa != ab:
                    tot["dis_rows"] += 1
                    ps["dis_rows"] += 1
                    tot["dis_follow_A"] += ga == aa
                    ps["dis_follow_A"] += ga == aa
                    tot["dis_follow_B"] += ga == ab
                    ps["dis_follow_B"] += ga == ab
                    tot["dis_neither"] += ga not in (aa, ab)
                else:
                    tot["same_rows"] += 1
                    tot["same_follow"] += ga == aa
            res = env.step(g, env_rng)
            e = env.last_outcome.energy
            row["bits"] += float(e.system_throughput_bps) * DT_S
            row["joules"] += float(e.system_consumed_power_w) * DT_S
            row["served"] += int(e.served)
            row["user_steps"] += users
            observation = env.last_outcome.observation
            states, masks = res.user_states, res.action_masks
            enc = encode_with_time(states, t + 1, users, cfg, T)
            if res.done:
                break
        rows_ep.append(row)

    bits = joules = 0.0
    for r in rows_ep:
        bits += r["bits"]
        joules += r["joules"]
    ee = bits / joules
    ee_ep = [r["bits"] / r["joules"] if r["joules"] > 0 else float("nan") for r in rows_ep]

    def frac(n, d):
        return (n / d) if d else None

    report = {
        "policy": str(a.policy), "policy_sha256": policy_sha,
        "schema": payload.get("schema"), "episode": payload.get("episode"),
        "dev_settings": payload.get("dev_settings"),
        "provenance_specs": {k: payload[k] for k in payload if k.endswith("_spec")},
        "tle": tle, "episodes": int(a.episodes), "steps_per_episode": steps_T,
        "ee": ee, "bits": bits, "joules": joules,
        "served": sum(r["served"] for r in rows_ep) / sum(r["user_steps"] for r in rows_ep),
        "agreement_with_A_all_t": frac(tot["agree_A"], tot["rows"]),
        "agreement_with_A_t_lt_T1": frac(tot["agree_A_tB"], tot["rows_B"]),
        "agreement_with_B_t_lt_T1": frac(tot["agree_B"], tot["rows_B"]),
        "A_B_disagreement_rate_t_lt_T1": frac(tot["dis_rows"], tot["rows_B"]),
        "on_disagreement_follows_A": frac(tot["dis_follow_A"], tot["dis_rows"]),
        "on_disagreement_follows_B": frac(tot["dis_follow_B"], tot["dis_rows"]),
        "on_disagreement_follows_neither": frac(tot["dis_neither"], tot["dis_rows"]),
        "on_agreement_follows_both": frac(tot["same_follow"], tot["same_rows"]),
        "counts": tot, "per_step": per_step, "tnext_diag": tnext_diag,
        "ee_ep": ee_ep,
        "epochs": [r["epoch"] for r in rows_ep],
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
            "devval_episode": dv.get("episode"),
            "devval_config_hash": dv.get("config_hash"),
            "devval_seed_index": dv.get("seed_index"),
        }
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("per_step", "ee_ep", "epochs", "obs0")},
                     indent=2, default=str))
    if a.out:
        a.out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str))
    ident = report.get("identity")
    if ident and not all(ident[k] for k in ("ee_equals_devval", "ee_ep_equals_devval",
                                            "epochs_equal", "obs0_equal")):
        print("IDENTITY FAIL: this rollout is not the DEVVAL reading of the checkpoint",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
