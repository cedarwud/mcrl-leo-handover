"""CF3PILOT 100-episode diagnostic (Amendment 1): a check, not a result.

For each given run directory (resume.pt at an episode boundary) reports:
per-head Q scale on 2,000 main-replay states (legal actions), each term's
share of the transformed score at the greedy action, C2 activation (lambda,
fraction of sampled states whose argmax changes without -lambda Q_H), and
batch composition by source with each source buffer's raw reward means.

Usage: cf3_diag100.py --out FILE RUN_DIR [RUN_DIR ...]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cf3_common as C

import numpy as np
import torch

from mcrl.algorithms import cf_ratio as cfr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("runs", nargs="+", type=Path)
    a = ap.parse_args()
    torch.set_num_threads(1)
    factory = C.env_factory()
    report = {}
    for run in a.runs:
        payload = torch.load(run / "resume.pt", map_location="cpu", weights_only=False)
        fp = payload["fingerprint"]
        from mcrl.runtime.trainer_spec import TrainerConfig
        cfgd = dict(fp["config"])
        for k in ("hidden_layers", "objective_weights", "reward_calibration_scales"):
            cfgd[k] = tuple(cfgd[k])
        st = cfr.CFRatioSettings(**fp["settings"])
        seeds = fp["seeds"]
        tr = cfr.CFRatioTrainer(factory(), TrainerConfig(**cfgd), st, env_factory=factory,
                                train_seed=seeds[0], env_seed=seeds[1], mobility_seed=seeds[2])
        # Runs made before Amendment 2 carry settings without ``dual_ascent``;
        # every key they do carry must match, then the new field is filled in
        # (read-only diagnostic; nothing is resumed or trained).
        import dataclasses
        stored = payload["trainer_state"]["cf"]["settings"]
        now = dataclasses.asdict(st)
        assert all(now[k2] == v for k2, v in stored.items()), "settings differ"
        payload["trainer_state"]["cf"]["settings"] = now
        tr.load_training_state_dict(payload["trainer_state"])
        rng = np.random.default_rng(0)
        buf = list(tr.replay._buf)
        idx = rng.choice(len(buf), size=min(2000, len(buf)), replace=False)
        S = np.array([buf[i][0] for i in idx], dtype=np.float32)
        M = np.array([buf[i][4] for i in idx], dtype=bool)
        q = tr._predict_objective_q_values(S)
        scale = {}
        for h, name in enumerate(("Q_B", "Q_E", "Q_H")):
            v = q[h][M]
            scale[name] = {"mean": float(v.mean()), "mean_abs": float(np.abs(v).mean()),
                           "std": float(v.std())}
        comb = tr._combine(q[0], q[1], q[2])
        comb0 = tr._combine(q[0], q[1], q[2], lam=0.0)
        comb_m = np.where(M, comb, -np.inf)
        comb0_m = np.where(M, comb0, -np.inf)
        a_star = comb_m.argmax(1)
        rows = np.arange(len(a_star))
        tb = np.abs(q[0][rows, a_star])
        te = np.abs(tr.eta_tilde * q[1][rows, a_star])
        th = np.abs(tr.lam * q[2][rows, a_star])
        tot = tb + te + th
        logs = payload["logs"]
        comp = np.sum([r["batch_rows_by_source"] for r in logs], axis=0).tolist()
        src = []
        for s in tr.sources:
            R = np.array([t[2] for t in s.buffer._buf])
            src.append({"name": s.name, "size": len(s.buffer),
                        "raw_mean_B_E_H": R.mean(0).tolist(),
                        "ee_of_buffer": float(R[:, 0].sum() / R[:, 1].sum())})
        Rm = np.array([t[2] for t in tr.replay._buf])
        report[run.name] = {
            "episode": payload["next_episode"], "eta": tr.eta, "lambda": tr.lam,
            "eta_tilde": tr.eta_tilde, "q_scale": scale,
            "term_share_at_greedy": {"B": float(np.mean(tb / tot)), "E": float(np.mean(te / tot)),
                                     "H": float(np.mean(th / tot))},
            "c2_argmax_changed_without_QH": float(np.mean(comb0_m.argmax(1) != a_star)),
            "batch_rows_by_source_main_first": comp,
            "sources": src,
            "main_replay_raw_mean_B_E_H": Rm.mean(0).tolist(),
            "main_replay_ee": float(Rm[:, 0].sum() / Rm[:, 1].sum()),
            "last_losses": logs[-1]["losses"],
            "episodes_with_lambda_pos": int(sum(r["lambda"] > 0 for r in logs)),
            "behaviour_ee_last10": float(np.mean([r["ee_behaviour"] for r in logs[-10:]])),
        }
    C.write_json(a.out, report)
    print(json.dumps(report, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
