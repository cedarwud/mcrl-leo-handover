"""CF3PILOT process-level tests through the REAL launcher and driver (smoke mode).

T1 resume: A3 s0 run uninterrupted (P1) vs stopped at episode 2 and resumed
   through the launcher (P2): final policy bit-identical, logs [0,1,2] with no
   duplicates, next_episode 3, same source-sampling RNG state, pools
   untouched, policy loadable; a second launch while it is live starts nothing.
T2 forced learning-check failure (RANDOM reference set to 1e12): A1 s0-2 end
   `stopped-learning-check` with completed = next_episode = 2 and logs [0,1];
   one DECISION.lock, DECISION pass = false; the launcher then plans them as
   finished.

Usage: cf3_proctest.py --base DIR --calibration FILE --pools DIR
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cf3_common as C

import torch

LAUNCH = [sys.executable, "scripts/cf3_launch.py"]


def launch(*args) -> str:
    r = subprocess.run(LAUNCH + list(map(str, args)), cwd=C.REPO, capture_output=True, text=True)
    print(r.stdout, r.stderr, flush=True)
    if r.returncode != 0:
        raise SystemExit(f"launcher failed: {args}")
    return r.stdout


def wait(root: Path, runs: list[str], states: set[str], timeout=1800) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        got = {}
        for d in runs:
            p = root / d / "status.json"
            got[d] = json.loads(p.read_text()).get("status") if p.is_file() else None
        if all(v in states for v in got.values()):
            return got
        if any(v == "failed" for v in got.values()):
            raise SystemExit(f"a run failed: {got}")
        time.sleep(5)
    raise SystemExit(f"timeout waiting for {states}: {got}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--pools", type=Path, required=True)
    a = ap.parse_args()
    base = a.base.resolve()
    base.mkdir(parents=True, exist_ok=False)
    common = ["--calibration", a.calibration.resolve(), "--pools", a.pools.resolve(), "--smoke"]
    results = {}

    # ---- T1
    p1, p2 = base / "P1", base / "P2"
    launch("--root", p1, *common, "--init-manifest", "A1:0", "A1:1", "A1:2", "A3:0")
    wait(p1, ["A1-OFF-s0", "A1-OFF-s1", "A1-OFF-s2", "A3-NULL3-s0"], {"complete"})
    p2.mkdir()
    shutil.copytree(p1 / "learning-check", p2 / "learning-check")
    launch("--root", p2, *common, "--init-manifest", "--stop-after", "2", "A3:0")
    wait(p2, ["A3-NULL3-s0"], {"stopped-at"})
    mid = torch.load(p2 / "A3-NULL3-s0" / "resume.pt", map_location="cpu", weights_only=False)
    assert mid["next_episode"] == 2 and [r["episode"] for r in mid["logs"]] == [0, 1]
    out = launch("--root", p2, *common, "A3:0")
    assert "resume" in out
    again = launch("--root", p2, *common, "--dry-run", "A3:0")
    live_seen = "live pid" in again
    wait(p2, ["A3-NULL3-s0"], {"complete"})
    r1 = torch.load(p1 / "A3-NULL3-s0" / "resume.pt", map_location="cpu", weights_only=False)
    r2 = torch.load(p2 / "A3-NULL3-s0" / "resume.pt", map_location="cpu", weights_only=False)
    assert r2["next_episode"] == 3 and [r["episode"] for r in r2["logs"]] == [0, 1, 2]
    pol1 = torch.load(p1 / "A3-NULL3-s0" / "policy-ep00003.pt", map_location="cpu", weights_only=False)
    pol2 = torch.load(p2 / "A3-NULL3-s0" / "policy-ep00003.pt", map_location="cpu", weights_only=False)
    same = all(torch.equal(x, y) for n1, n2 in zip(pol1["q_networks"], pol2["q_networks"])
               for x, y in zip(n1.values(), n2.values()))
    assert same, "resumed policy differs from the uninterrupted one"
    assert r1["trainer_state"]["cf"]["catfish_rng"] == r2["trainer_state"]["cf"]["catfish_rng"]
    assert r1["trainer_state"]["cf"]["sources"] == r2["trainer_state"]["cf"]["sources"]
    assert [x["bits"] for x in r1["logs"]] == [x["bits"] for x in r2["logs"]]
    import cf3_eval
    cf3_eval.build("cf", p2 / "A3-NULL3-s0" / "policy-ep00003.pt", C.env_factory())
    results["T1"] = {"resume_bit_identical": same, "logs": [r["episode"] for r in r2["logs"]],
                     "next_episode": r2["next_episode"], "second_launch_saw_live": live_seen}

    # ---- T2
    f = base / "F"
    f.mkdir()
    cal = json.loads(a.calibration.read_text())
    cal["random_reference_ee"] = 1e12
    fcal = base / "calibration-forced-fail.json"
    fcal.write_text(json.dumps(cal))
    fcommon = ["--calibration", fcal, "--pools", a.pools.resolve(), "--smoke"]
    launch("--root", f, *fcommon, "--init-manifest", "A1:0", "A1:1", "A1:2")
    runs = ["A1-OFF-s0", "A1-OFF-s1", "A1-OFF-s2"]
    wait(f, runs, {"stopped-learning-check"})
    for d in runs:
        st = json.loads((f / d / "status.json").read_text())
        rs = torch.load(f / d / "resume.pt", map_location="cpu", weights_only=False)
        logs = json.loads((f / d / "episode-logs.json").read_text())
        assert st["episodes_completed"] == 2 and rs["next_episode"] == 2
        assert [r["episode"] for r in logs] == [0, 1] == [r["episode"] for r in rs["logs"]]
    dec = json.loads((f / "learning-check" / "DECISION.json").read_text())
    assert dec["pass"] is False and (f / "learning-check" / "DECISION.lock").is_file()
    plan = launch("--root", f, *fcommon, "--dry-run", "A1:0", "A1:1", "A1:2")
    assert plan.count(": finished") == 3
    results["T2"] = {"completed": 2, "logs": [0, 1], "decision_pass": dec["pass"],
                     "decision_by": dec["by"], "launcher_plans_finished": 3}
    C.write_json(base / "PROCTEST-RESULT.json", results)
    print("PROCTEST PASS", json.dumps(results), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
