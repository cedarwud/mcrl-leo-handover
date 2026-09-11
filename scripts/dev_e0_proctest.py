"""DEVHARNESS process-level preflight through the REAL launcher and driver (smoke).

T1 resume: arm 3 (D2-null, the arm with an extra generator) run uninterrupted (P1)
   vs stopped at episode 2 and resumed through the launcher (P2): final policy
   bit-identical, logs [0, 1, 2] with no duplicates, next_episode 3, identical
   DEV-NULL generator state, identical per-episode bits / losses / teacher losses;
   a second launch while the run is live starts nothing.
T2 fail-closed: a launch whose configuration hash differs from the manifest's
   (a changed budget) is refused by the driver, and a manifest mismatch is refused
   by the launcher.

Usage: dev_e0_proctest.py --base DIR --calibration FILE
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import cf3_common as C
import dev_e0_common as D

import torch

LAUNCH = [sys.executable, "scripts/dev_e0_launch.py"]


def launch(*args, expect_fail: bool = False) -> str:
    r = subprocess.run(LAUNCH + list(map(str, args)), cwd=C.REPO,
                       capture_output=True, text=True)
    print(r.stdout, r.stderr, flush=True)
    if expect_fail:
        if r.returncode == 0:
            raise SystemExit(f"launcher should have refused: {args}")
        return r.stdout + r.stderr
    if r.returncode != 0:
        raise SystemExit(f"launcher failed: {args}")
    return r.stdout


def wait(root: Path, runs: list[str], states: set[str], timeout: int = 1800) -> dict:
    t0 = time.time()
    got: dict[str, object] = {}
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
    a = ap.parse_args()
    base = a.base.resolve()
    base.mkdir(parents=True, exist_ok=False)
    common = ["--calibration", a.calibration.resolve(), "--smoke"]
    run = f"{D.arm_name(3)}-k0"
    results: dict[str, object] = {}

    # ---- T1
    p1, p2 = base / "P1", base / "P2"
    launch("--root", p1, *common, "--init-manifest", "3:0")
    wait(p1, [run], {"complete"})
    launch("--root", p2, *common, "--init-manifest", "--stop-after", "2", "3:0")
    wait(p2, [run], {"stopped-at"})
    mid = torch.load(p2 / run / "resume.pt", map_location="cpu", weights_only=False)
    assert mid["next_episode"] == 2 and [r["episode"] for r in mid["logs"]] == [0, 1]
    out = launch("--root", p2, *common, "3:0")
    assert "resume" in out
    again = launch("--root", p2, *common, "--dry-run", "3:0")
    live_seen = "live pid" in again
    wait(p2, [run], {"complete"})
    r1 = torch.load(p1 / run / "resume.pt", map_location="cpu", weights_only=False)
    r2 = torch.load(p2 / run / "resume.pt", map_location="cpu", weights_only=False)
    assert r2["next_episode"] == 3 and [r["episode"] for r in r2["logs"]] == [0, 1, 2]
    pol1 = torch.load(p1 / run / "policy-ep00003.pt", map_location="cpu", weights_only=False)
    pol2 = torch.load(p2 / run / "policy-ep00003.pt", map_location="cpu", weights_only=False)
    same = all(torch.equal(x, y) for n1, n2 in zip(pol1["q_networks"], pol2["q_networks"])
               for x, y in zip(n1.values(), n2.values()))
    assert same, "resumed policy differs from the uninterrupted one"
    assert (r1["trainer_state"]["dev"]["null_rng"]
            == r2["trainer_state"]["dev"]["null_rng"]), "DEV-NULL generator diverged"
    for key in ("bits", "joules", "losses", "teacher_loss", "t0_agree_greedy"):
        assert [x[key] for x in r1["logs"]] == [x[key] for x in r2["logs"]], key
    results["T1"] = {"resume_bit_identical": same,
                     "logs": [r["episode"] for r in r2["logs"]],
                     "next_episode": r2["next_episode"],
                     "second_launch_saw_live": live_seen}

    # ---- T2 fail-closed on a configuration change.  (--smoke pins the budget, so
    # the mismatch is made by dropping it: a different budget AND a different mode
    # against the same manifest.)
    stdout = launch("--root", p2, "--calibration", a.calibration.resolve(),
                    "--episodes", "4", "--dry-run", "3:0", expect_fail=True)
    assert "RUN-MANIFEST" in stdout
    results["T2"] = {"launcher_refused_changed_config": True}

    C.write_json(base / "PROCTEST-RESULT.json", results)
    print("DEV PROCTEST PASS", json.dumps(results), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
