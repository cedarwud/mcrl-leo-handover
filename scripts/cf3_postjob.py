"""CF3PILOT detached post-training job (agent-independent).

1. Waits until all 12 runs are terminal: ``complete``; ``failed``;
   ``stopped-learning-check`` backed by a DECISION.json with pass=false; or
   DEAD (status still ``running`` but its PID is gone / not this driver).
2. If all 12 are complete: evaluates every final checkpoint with the tree's
   ``cf3_eval.py`` (greedy, pinned archive, per-episode reseeded, --repeat),
   re-verifies pools (sidecar + npz hashes, run bindings) and generator-file
   identity, runs ``cf3_report.py`` (declared reading) and ``cf3_render.py``,
   and writes ``REPORT-DONE``.
3. If the learning check stopped A1-A3: writes LEARNING-CHECK-STOP.json/.md
   (losses, eta/lambda trajectories, per-head reward means, readings) and
   ``REPORT-DONE`` with kind learning-check-stop.
4. Anything else (a failed or dead run, a missing eval, a failed check):
   evaluates what is complete, and writes ``REPORT-FAILED`` with the reason.
   Nothing is skipped silently.

Usage: cf3_postjob.py --ws /home/sat/mcrl-v025-cf3-pilot-ws
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

NAMES = {"A0": "BASELINE", "A1": "OFF", "A2": "CF3", "A3": "NULL3"}
RUNS = [(a, k) for a in ("A0", "A1", "A2", "A3") for k in (0, 1, 2)]
PY = "/home/sat/mcrl-leo-handover/.venv/bin/python"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def alive(ws: Path, arm: str, k: int) -> bool:
    pidf = ws / "runs" / f"{arm}-s{k}.pid"
    try:
        pid = int(pidf.read_text().strip())
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
    except (OSError, ValueError):
        return False
    return "scripts/run_cf3_pilot.py" in cmd and f"--arm {arm} --seed-index {k}" in cmd


def states(ws: Path) -> dict:
    dec_p = ws / "runs" / "learning-check" / "DECISION.json"
    dec = json.loads(dec_p.read_text()) if dec_p.is_file() else None
    out = {}
    for arm, k in RUNS:
        sp = ws / "runs" / f"{arm}-{NAMES[arm]}-s{k}" / "status.json"
        st = json.loads(sp.read_text()).get("status") if sp.is_file() else None
        if st == "stopped-learning-check" and not (dec and dec.get("pass") is False):
            st = "stopped-without-failing-decision"
        if st in ("running", None, "stopped-at") and not alive(ws, arm, k):
            st = f"DEAD({st})"
        out[f"{arm}s{k}"] = st
    return out


def log(rep: Path, msg: str) -> None:
    with open(rep / "postjob.log", "a") as f:
        f.write(f"[{utc()}] {msg}\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ws", type=Path, required=True)
    ap.add_argument("--timeout-h", type=float, default=8.0)
    a = ap.parse_args()
    ws = a.ws
    rep = ws / "report"
    rep.mkdir(exist_ok=True)
    for m in ("REPORT-DONE", "REPORT-FAILED"):
        if (rep / m).exists():
            print(f"{m} already present; nothing to do")
            return 0
    log(rep, f"postjob started pid {os.getpid()}")
    deadline = time.time() + a.timeout_h * 3600
    terminal = {"complete", "failed", "stopped-learning-check"}
    while True:
        st = states(ws)
        if all(v in terminal or str(v).startswith("DEAD") or v == "stopped-without-failing-decision"
               for v in st.values()):
            break
        if time.time() > deadline:
            (rep / "REPORT-FAILED").write_text(f"{utc()} timeout waiting for runs: {st}\n")
            log(rep, "timeout")
            return 1
        time.sleep(60)
    log(rep, f"all runs terminal: {st}")
    (rep / "RUN-STATES.json").write_text(json.dumps(st, indent=2))
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               NUMEXPR_NUM_THREADS="1", MCRL_TLE_ROOT=str(ws / "tle-pinned-427e6a91"))

    complete = [r for r, v in st.items() if v == "complete"]
    stopped = [r for r, v in st.items() if v == "stopped-learning-check"]
    bad = [f"{r}={v}" for r, v in st.items() if v not in ("complete", "stopped-learning-check")]

    # ---- evaluation of every complete run (always; nothing skipped silently)
    ev = ws / "eval"
    ev.mkdir(exist_ok=True)
    procs = []
    for r in complete:
        arm, k = r[:2], int(r[3])
        out = ev / f"{r}.json"
        if out.is_file():
            continue
        ck = ws / "runs" / f"{arm}-{NAMES[arm]}-s{k}" / "policy-ep01000.pt"
        cmd = ["nice", "-n", "10", PY, "scripts/cf3_eval.py", "--label", r, "--checkpoint", str(ck),
               "--kind", "modqn" if arm == "A0" else "cf", "--out", str(out), "--repeat"]
        procs.append((r, subprocess.Popen(cmd, cwd=ws / "tree", env=env, stdin=subprocess.DEVNULL,
                                          stdout=open(ev / f"{r}.log", "ab"), stderr=subprocess.STDOUT)))
    for r, p in procs:
        rc = p.wait()
        log(rep, f"eval {r} rc={rc}")
        if rc != 0:
            bad.append(f"eval {r} rc={rc}")

    # ---- pool + generator re-verification
    rc = subprocess.run(["python3", str(ws / "diag" / "cf3_verify_pools.py"), "--pools", str(ws / "pools"),
                         "--root", str(ws / "runs"), "--out", str(rep / "POOL-VERIFY.json")]).returncode
    if rc != 0:
        bad.append("pool re-verification FAILED")
    gen_files = ["src/mcrl/algorithms/cf_ratio.py", "src/mcrl/algorithms/cf_sources.py",
                 "scripts/cf3_pools.py", "src/mcrl/runtime/state_encoding.py"]
    gen = {f: {"generator_tree": sha(ws / "tree-pools-d04d9dbe" / f), "training_tree": sha(ws / "tree" / f)}
           for f in gen_files}
    src_diff = [str(p.relative_to(ws / "tree-pools-d04d9dbe")) for p in (ws / "tree-pools-d04d9dbe" / "src").rglob("*.py")
                if sha(p) != sha(ws / "tree" / p.relative_to(ws / "tree-pools-d04d9dbe"))]
    gen_ok = all(v["generator_tree"] == v["training_tree"] for v in gen.values()) and not src_diff
    (rep / "GENERATOR-IDENTITY.json").write_text(json.dumps(
        {"ok": gen_ok, "files": gen, "src_files_differing": src_diff,
         "tree_commit": (ws / "tree" / "COMMIT").read_text().strip()}, indent=2))
    if not gen_ok:
        bad.append("generator identity FAILED")

    # ---- learning-check stop branch
    if stopped:
        summ = {}
        for r in stopped + [x for x in complete if x.startswith("A0")]:
            arm, k = r[:2], int(r[3])
            d = ws / "runs" / f"{arm}-{NAMES[arm]}-s{k}"
            logs = json.loads((d / "episode-logs.json").read_text())
            sj = json.loads((d / "status.json").read_text())
            rows = [x for x in logs if (x["episode"] + 1) % 50 == 0]
            summ[r] = {
                "status": sj.get("status"), "learning_check": sj.get("learning_check"),
                "losses_every_50": [(x["episode"] + 1, x["losses"]) for x in rows],
                "head_reward_means_every_50": [(x["episode"] + 1, x.get("head_reward_means_normalised"))
                                               for x in rows],
                "eta_lambda_every_50": [(x["episode"] + 1, x.get("eta"), x.get("lambda")) for x in rows],
                "dual_trajectory": sj.get("dual_trajectory"),
                "readings": [json.loads(l) for l in (d / "readings.jsonl").read_text().splitlines()],
            }
        (rep / "LEARNING-CHECK-STOP.json").write_text(json.dumps(summ, indent=2, default=str))
        marker = "REPORT-FAILED" if bad else "REPORT-DONE"
        (rep / marker).write_text(f"{utc()} kind=learning-check-stop stopped={stopped} problems={bad}\n")
        log(rep, marker)
        return 0 if not bad else 1

    if bad or len(complete) != 12:
        (rep / "REPORT-FAILED").write_text(f"{utc()} problems={bad} complete={complete}\n")
        log(rep, f"REPORT-FAILED {bad}")
        return 1

    # ---- declared reading
    rc1 = subprocess.run([PY, str(ws / "diag" / "cf3_report.py"), "--eval-dir", str(ev), "--root",
                          str(ws / "runs"), "--out", str(rep / "CF3-SUMMARY.json"), "--pool-verify",
                          str(rep / "POOL-VERIFY.json")], stdout=open(rep / "report.stdout", "w"),
                         stderr=subprocess.STDOUT).returncode
    rc2 = subprocess.run([PY, str(ws / "diag" / "cf3_render.py"), str(rep / "CF3-SUMMARY.json"),
                          str(rep / "CF3-TABLES.md")], stdout=subprocess.DEVNULL).returncode if rc1 == 0 else 1
    if rc1 or rc2:
        (rep / "REPORT-FAILED").write_text(f"{utc()} report rc={rc1} render rc={rc2}\n")
        return 1
    s = json.loads((rep / "CF3-SUMMARY.json").read_text())
    means = {k: v["ee"] for k, v in s["arm_means"].items()}
    (rep / "REPORT-DONE").write_text(f"{utc()} kind=complete branch={s['branch']} arm_mean_ee={means}\n")
    log(rep, "REPORT-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
