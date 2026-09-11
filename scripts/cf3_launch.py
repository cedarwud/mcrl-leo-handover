"""CF3PILOT launcher (replaces launch.sh; coordinator review item 6).

* Code identity: computes the code manifest of THIS tree and the calibration
  hash; with ``--init-manifest`` writes ``<root>/RUN-MANIFEST.json`` if
  absent; otherwise the existing manifest must match exactly (fail closed).
* Plans every requested run (exactly the expected unique set), classifying
  each as finished / live / to-launch.  "Live" = the PID in the pid file
  exists AND its command line is this driver with the same --arm,
  --seed-index and --root AND its cwd is this tree (a stale pid file is not
  enough).  The plan is printed before anything starts.
* Launches with ``systemd-run --user --scope -p MemoryMax=...``, ``nice -n 10``,
  one BLAS/OMP thread, new session, stdin from /dev/null; then checks every
  launched process is alive with the right command line, and fails loudly if
  not.  ``--verify`` waits for every run's status.json and checks that all
  fingerprints carry the manifest's code identity.

Usage::

    cf3_launch.py --root DIR --calibration FILE [--init-manifest] [--smoke]
                  [--stop-after N] [--expect N] [--memory-max 5G]
                  [--memory-max-cf 6G] [--verify] [--dry-run] [SPEC ...]
    SPEC = ARM:K (A0:0 ... A3:4); default = the declared 18.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cf3_common as C

NAMES = {"A0": "BASELINE", "A1": "OFF", "A2": "CF3", "A3": "NULL3"}
DEFAULT_SPECS = [f"A0:{k}" for k in C.A0_SEEDS] + [
    f"{a}:{k}" for a in ("A1", "A2", "A3") for k in range(len(C.TRAIN_SEEDS))
]
DRIVER = "scripts/run_cf3_pilot.py"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_live(pidfile: Path, arm: str, k: int, root: Path) -> int | None:
    if not pidfile.is_file():
        return None
    try:
        pid = int(pidfile.read_text().strip())
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        cwd = os.readlink(f"/proc/{pid}/cwd")
    except (OSError, ValueError):
        return None
    args = [c.decode() for c in cmd if c]
    want = [DRIVER, "--arm", arm, "--seed-index", str(k), "--root", str(root)]
    joined = " ".join(args)
    if all(w in args for w in want) and f"--arm {arm} --seed-index {k} --root {root}" in joined \
            and Path(cwd) == C.REPO:
        return pid
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--init-manifest", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--expect", type=int, default=None)
    ap.add_argument("--memory-max", default="5G")
    ap.add_argument("--memory-max-cf", default=None,
                    help="MemoryMax for A2/A3 (default = --memory-max)")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("specs", nargs="*")
    a = ap.parse_args()
    root = a.root.resolve()
    specs = a.specs or DEFAULT_SPECS
    if len(set(specs)) != len(specs):
        raise SystemExit(f"duplicate specs: {specs}")
    expect = a.expect if a.expect is not None else len(specs)
    if len(specs) != expect:
        raise SystemExit(f"planned {len(specs)} runs, expected exactly {expect}")
    for s in specs:
        arm, k = s.split(":")
        if arm not in NAMES or (arm == "A0" and int(k) not in C.A0_SEEDS) or not 0 <= int(k) < len(C.TRAIN_SEEDS):
            raise SystemExit(f"bad spec {s}")

    code = C.code_manifest()
    calib_sha = C.sha256_file(a.calibration)
    root.mkdir(parents=True, exist_ok=True)
    mpath = root / "RUN-MANIFEST.json"
    wanted = {"code": code, "code_digest": C.manifest_digest(code),
              "calibration": str(a.calibration.resolve()), "calibration_sha256": calib_sha,
              "smoke": bool(a.smoke), "tle_root": os.environ.get("MCRL_TLE_ROOT"),
              "train_seeds": [list(t) for t in C.TRAIN_SEEDS], "specs": sorted(specs)}
    if mpath.is_file():
        have = json.loads(mpath.read_text())
        diff = [k2 for k2 in ("code", "calibration_sha256", "smoke") if have.get(k2) != wanted[k2]]
        if diff:
            raise SystemExit(f"RUN-MANIFEST.json mismatch in {diff}; refusing (fail closed)")
    elif a.init_manifest:
        wanted["created_utc"] = utc()
        C.write_json(mpath, wanted)
        print(f"wrote {mpath} (commit {code['commit']}, code digest {wanted['code_digest'][:12]})")
    else:
        raise SystemExit(f"no {mpath}; pass --init-manifest for a fresh root")

    plan = []
    for s in specs:
        arm, k = s.split(":")
        k = int(k)
        d = root / f"{arm}-{NAMES[arm]}-s{k}"
        pidf = root / f"{arm}-s{k}.pid"
        st = json.loads((d / "status.json").read_text()) if (d / "status.json").is_file() else {}
        live = is_live(pidf, arm, k, root)
        if st.get("status") in ("complete", "stopped-learning-check"):
            state = "finished"
        elif live:
            state = f"live pid {live}"
        else:
            state = "resume" if (d / "resume.pt").is_file() else "fresh"
        plan.append((arm, k, d, pidf, state))
    print(f"[{utc()}] plan for {root} (commit {code['commit']}):")
    for arm, k, _d, _p, state in plan:
        print(f"  {arm} s{k}: {state}")
    if a.dry_run:
        return 0

    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    if not env.get("MCRL_TLE_ROOT"):
        raise SystemExit("MCRL_TLE_ROOT must point at the pinned archive copy")
    launched = []
    for arm, k, d, pidf, state in plan:
        if state not in ("fresh", "resume"):
            continue
        mm = a.memory_max_cf if (a.memory_max_cf and arm in ("A2", "A3")) else a.memory_max
        cmd = ["systemd-run", "--user", "--scope", "-p", f"MemoryMax={mm}", "--quiet",
               "nice", "-n", "10", sys.executable, DRIVER, "--arm", arm, "--seed-index", str(k),
               "--root", str(root), "--calibration", str(a.calibration.resolve())]
        if a.smoke:
            cmd.append("--smoke")
        if a.stop_after is not None:
            cmd += ["--stop-after", str(a.stop_after)]
        log = open(root / f"{arm}-s{k}.log", "ab")
        p = subprocess.Popen(cmd, cwd=C.REPO, env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        pidf.write_text(str(p.pid))
        launched.append((arm, k, p.pid))
        print(f"  launched {arm} s{k} pid {p.pid} MemoryMax={mm}")
    time.sleep(10)
    dead = [(arm, k, pid) for arm, k, pid in launched
            if is_live(root / f"{arm}-s{k}.pid", arm, k, root) != pid]
    if dead:
        raise SystemExit(f"FAILED TO START (or died within 10 s): {dead}")
    print(f"[{utc()}] all {len(launched)} launched processes alive")
    if a.verify:
        deadline = time.time() + 600
        want_digest = C.manifest_digest(code)
        pending = [(arm, k) for arm, k, *_ in plan]
        while pending and time.time() < deadline:
            nxt = []
            for arm, k in pending:
                sp = root / f"{arm}-{NAMES[arm]}-s{k}" / "status.json"
                try:
                    fp = json.loads(sp.read_text())["fingerprint"]
                except (OSError, KeyError, ValueError):
                    nxt.append((arm, k)); continue
                if fp.get("code_digest") != want_digest:
                    raise SystemExit(f"{arm} s{k} fingerprint code digest differs")
            pending = nxt
            if pending:
                time.sleep(10)
        if pending:
            raise SystemExit(f"no status fingerprint after 10 min: {pending}")
        print(f"[{utc()}] verified: all {len(plan)} status fingerprints carry code digest {want_digest[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
