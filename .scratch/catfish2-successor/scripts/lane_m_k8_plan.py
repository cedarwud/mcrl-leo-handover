"""LANE-M: build and CHECK the five prospective k = 8 manifests.  Launches nothing.

Controller record ``CONTROLLER-K8-NULL-AND-READY-2026-09-12.md`` (``716f104e``).
The five cells of the Amendment 15 section 7 pairwise causal matrix at fresh k = 8:

    D0            arm 1                     (shared baseline)
    T0-only       arm 4  D3-T0              (the frozen single-teacher arm)
    T_NEXT-only   arm 8  {T_NEXT}           (the GENERIC singleton -- no new mechanism)
    FULL          arm 8  {T0, T_NEXT}
    2-null        arm 9  Bernoulli matched, p_singleton = 9395/24000

Everything this prints is prospective: config hashes, run-manifest keys, run
directories and the exact driver command lines, plus the fail-closed assertions
that the schedule is 300 / stop-after 100 / read depth 100 and that the REJECTED
fixed two-proposal null cannot be selected by accident.

Usage::

    lane_m_k8_plan.py --calibration FILE --root DIR --out PLAN.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(TREE / "src"))
sys.path.insert(0, str(TREE / "scripts"))

import cf3_common as C  # noqa: E402
import dev_e0_common as D  # noqa: E402
from mcrl.algorithms import cf_multi_sources as cfmulti  # noqa: E402
from mcrl.algorithms import cf_teacher as cft  # noqa: E402
from mcrl.runtime import training_pipeline as tp  # noqa: E402

K8 = 8
EPISODES = 300
STOP_AFTER = 100
READ_DEPTH = 100

CELLS = (
    ("D0", 1, None, None, False),
    ("T0-only", 4, None, None, False),
    ("T_NEXT-only", 8, ("T_NEXT",), None, False),
    ("FULL{T0,T_NEXT}", 8, ("T0", "T_NEXT"), None, False),
    ("2-null-bernoulli", 9, None, 2, True),
)


def build(calibration: Path, root: Path) -> dict:
    cfmulti.register_candidate_sources(replace=True)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    calib = json.loads(calibration.read_text())
    calib_sha = C.sha256_file(calibration)
    code = D.code_manifest()

    # --- the schedule, asserted before anything is planned -----------------
    cfg = D.e0_config(record, EPISODES)
    assert cfg.episodes == EPISODES, cfg.episodes
    assert cfg.epsilon_decay_episodes == D.epsilon_decay_episodes(EPISODES) == 67
    assert D.epsilon_decay_episodes(STOP_AFTER) != cfg.epsilon_decay_episodes, (
        "shortening the CONFIGURED budget would silently change the learner"
    )
    assert READ_DEPTH in D.devval_at(EPISODES)

    cells = []
    for name, arm, teachers, n_proposals, bern in CELLS:
        payload = D.arm_config_payload(
            record, calib, arm, K8, episodes=EPISODES, devval_episodes=D.N_DEVVAL,
            calibration_sha256=calib_sha, teachers=teachers,
            n_proposals=n_proposals, bernoulli=bern,
        )
        key = D.spec_key(arm, K8, teachers, n_proposals=n_proposals, bernoulli=bern)
        run_name = D.arm_name(arm, teachers, n_proposals=n_proposals, bernoulli=bern)
        cmd = ["scripts/run_dev_e0.py", "--arm", str(arm), "--seed-index", str(K8),
               "--root", str(root), "--calibration", str(calibration),
               "--episodes", str(EPISODES), "--stop-after", str(STOP_AFTER),
               "--devval-episodes", str(D.N_DEVVAL)]
        if teachers is not None:
            cmd += ["--teachers", "+".join(teachers)]
        if n_proposals is not None:
            cmd += ["--n-proposals", str(n_proposals)]
        if bern:
            cmd += ["--bernoulli-null"]
        cells.append({
            "cell": name, "arm": arm, "spec_key": key, "run_name": run_name,
            "run_dir": str(root / f"{run_name}-k{K8}"),
            "config_hash": D.config_hash(payload),
            "multi_spec": payload.get("multi_spec"),
            "seeds": payload["seeds"],
            "launcher_spec": (f"{arm}:{K8}" if arm not in D.MULTI_ARMS else
                              f"{arm}:{K8}:" + (("+".join(teachers)) if teachers
                                                else f"n{n_proposals}" + ("b" if bern else ""))),
            "command": cmd,
            "payload": payload,
        })

    hashes = {c["cell"]: c["config_hash"] for c in cells}
    keys = {c["cell"]: c["spec_key"] for c in cells}
    assert len(set(hashes.values())) == len(cells), f"config hash collision: {hashes}"
    assert len(set(keys.values())) == len(cells), f"manifest key collision: {keys}"
    assert len(set(c["run_dir"] for c in cells)) == len(cells), "run dir collision"

    # T_NEXT-only is the GENERIC singleton, not a new mechanism
    solo = next(c for c in cells if c["cell"] == "T_NEXT-only")
    full = next(c for c in cells if c["cell"] == "FULL{T0,T_NEXT}")
    assert solo["payload"]["mechanism"] == full["payload"]["mechanism"] == "D3-multi"
    assert "D3-T_NEXT" not in cft.MECHANISMS
    assert tuple(solo["multi_spec"]["teachers"]) == ("T_NEXT",)
    assert tuple(full["multi_spec"]["teachers"]) == ("T0", "T_NEXT")
    assert solo["multi_spec"]["mechanism_id"] == cft.MULTI_MECHANISM_ID

    # the selected null, and the rejected one, cannot be confused
    null = next(c for c in cells if c["cell"] == "2-null-bernoulli")
    assert null["multi_spec"]["null_id"] == cft.MULTI_NULL_BERNOULLI_ID
    assert null["multi_spec"]["p_singleton_rational"] == "9395/24000"
    assert null["multi_spec"]["p_singleton"] == 9395 / 24000
    assert null["multi_spec"]["n_proposals"] == 2
    rejected = D.arm_config_payload(
        record, calib, 9, K8, episodes=EPISODES, devval_episodes=D.N_DEVVAL,
        calibration_sha256=calib_sha, n_proposals=2)
    assert D.config_hash(rejected) != null["config_hash"]
    assert D.spec_key(9, K8, n_proposals=2) != null["spec_key"]
    assert "bernoulli" in null["run_name"] and "bernoulli" not in rejected["arm_name"]

    # the shared scientific identities really are shared
    assert all(c["payload"]["prereg_digest"] == record.digest for c in cells)
    assert all(c["payload"]["calibration_sha256"] == calib_sha for c in cells)
    assert all(c["payload"]["tle_file_set_sha256"] == D.TLE_FILE_SET_SHA256
               for c in cells)
    assert all(c["seeds"] == {"train": 9_201_008, "env": 9_202_008,
                              "mobility": 9_203_008} for c in cells)
    assert all(c["payload"]["episodes"] == EPISODES for c in cells)
    assert all(c["payload"]["devval_seeds"] == cells[0]["payload"]["devval_seeds"]
               for c in cells)

    return {
        "lane": "CF2S-LANE-M k = 8 prospective plan (development lane, NOT launched)",
        "governing": "CONTROLLER-K8-NULL-AND-READY-2026-09-12.md (716f104e)",
        "seed_index": K8,
        "episodes_configured": EPISODES,
        "stop_after": STOP_AFTER,
        "read_depth": READ_DEPTH,
        "epsilon_decay_episodes": cfg.epsilon_decay_episodes,
        "root": str(root),
        "calibration": str(calibration),
        "calibration_sha256": calib_sha,
        "code_digest": D.manifest_digest(code),
        "code_commit": code["commit"],
        "tnext_source_identity": cfmulti.tnext_identity(),
        "p0_dataset_sha256": D.P0_DATASET_SHA256,
        "lane_n_action_trace_sha256": D.TNEXT_ACTION_TRACE_SHA256,
        "matched_null_arm": D.MATCHED_NULL_ARM,
        "cells": cells,
        "launcher_specs": [c["launcher_spec"] for c in cells],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    plan = build(a.calibration, a.root)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(plan, indent=2, default=str) + "\n")
    print(f"k = {plan['seed_index']}  episodes={plan['episodes_configured']} "
          f"stop_after={plan['stop_after']} read_depth={plan['read_depth']} "
          f"eps_decay={plan['epsilon_decay_episodes']}")
    print(f"code commit {plan['code_commit']}  digest {plan['code_digest'][:12]}")
    for c in plan["cells"]:
        print(f"  {c['cell']:<18} spec {c['launcher_spec']:<20} "
              f"cfg {c['config_hash'][:12]}  {c['run_name']}")
    print("ALL PROSPECTIVE CHECKS PASSED; nothing was launched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
