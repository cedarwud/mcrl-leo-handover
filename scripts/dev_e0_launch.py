"""DEVHARNESS E0 launcher (the cf3_launch pattern, development lane).

* Code identity: the code manifest of THIS tree, the calibration hash and ONE
  configuration hash per arm (seeds, trainer config, CF settings, development
  settings, budget, DEVVAL seeds, prereg digest, TLE file set).  With
  ``--init-manifest`` it writes ``<root>/RUN-MANIFEST.json`` if absent; otherwise
  the existing manifest must match exactly and every driver re-checks its own
  arm's configuration hash before training (fail closed on both sides).
* Plans every requested run as finished / live / resume / fresh and prints the
  plan before anything starts.  "Live" = the PID in the pid file exists AND its
  command line is this driver with the same --arm, --seed-index and --root AND
  its cwd is this tree.
* Launches with ``systemd-run --user --scope -p MemoryMax=...``, ``nice -n 10``,
  one BLAS thread, a new session and stdin from /dev/null, then verifies every
  launched process is alive with the right command line.

Usage::

    dev_e0_launch.py --root DIR --calibration FILE [--init-manifest] [--smoke]
                     [--episodes 300] [--stop-after N] [--expect N]
                     [--memory-max 5G] [--dry-run] [--verify] [SPEC ...]
    SPEC = ARM:K  (1:0 .. 6:0);  default = arms 1-4 on DEV triple k = 0.
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
import dev_e0_common as D

DRIVER = "scripts/run_dev_e0.py"
DEFAULT_SPECS = [f"{arm}:0" for arm in (1, 2, 3, 4)]


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_live(pidfile: Path, arm: int, k: int, root: Path) -> int | None:
    if not pidfile.is_file():
        return None
    try:
        pid = int(pidfile.read_text().strip())
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        cwd = os.readlink(f"/proc/{pid}/cwd")
    except (OSError, ValueError):
        return None
    args = [c.decode() for c in cmd if c]
    want = [DRIVER, "--arm", str(arm), "--seed-index", str(k), "--root", str(root)]
    joined = " ".join(args)
    if (all(w in args for w in want)
            and f"--arm {arm} --seed-index {k} --root {root}" in joined
            and Path(cwd) == C.REPO):
        return pid
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--init-manifest", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--episodes", type=int, default=D.EPISODES)
    ap.add_argument("--devval-episodes", type=int, default=D.N_DEVVAL)
    ap.add_argument("--tau", type=float, default=None,
                    help="teacher temperature override (E0b tau sweep); a different "
                         "tau is a different version and a different config hash")
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--expect", type=int, default=None)
    ap.add_argument("--memory-max", default="5G")
    ap.add_argument("--rss-cap-gb", type=float, default=4.5)
    ap.add_argument("--max-processes", type=int, default=6)
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
    if len(specs) > a.max_processes:
        raise SystemExit(f"{len(specs)} runs exceeds --max-processes {a.max_processes}")
    parsed = []
    for s in specs:
        arm_s, k_s = s.split(":")
        arm, k = int(arm_s), int(k_s)
        if arm not in D.ARMS or not 0 <= k <= 9:
            raise SystemExit(f"bad spec {s}")
        parsed.append((arm, k))

    from mcrl.runtime import training_pipeline as tp
    episodes = 3 if a.smoke else int(a.episodes)
    n_devval = 2 if a.smoke else int(a.devval_episodes)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    code = D.code_manifest()
    arm_configs = {}
    arm_payloads = {}
    for arm, k in parsed:
        payload = D.arm_config_payload(record, calib, arm, k, episodes=episodes,
                                       devval_episodes=n_devval,
                                       calibration_sha256=calib_sha, tau=a.tau)
        arm_payloads[f"{arm}:{k}"] = payload
        arm_configs[f"{arm}:{k}"] = D.config_hash(payload)

    root.mkdir(parents=True, exist_ok=True)
    mpath = root / "RUN-MANIFEST.json"
    wanted = {
        "lane": "E0-development (Amendment 6): not formal evidence",
        "code": code, "code_digest": D.manifest_digest(code),
        "calibration": str(a.calibration.resolve()), "calibration_sha256": calib_sha,
        "smoke": bool(a.smoke), "episodes": episodes, "devval_episodes": n_devval,
        "tle_root": os.environ.get("MCRL_TLE_ROOT"),
        "tle_file_set_sha256": D.TLE_FILE_SET_SHA256,
        "specs": sorted(specs), "arm_configs": arm_configs,
        "arm_payloads": arm_payloads,
        "dev_seed_namespaces": {
            "DEV": [D.DEV_TRAIN_BASE, D.DEV_ENV_BASE, D.DEV_MOB_BASE],
            "DEVVAL": [D.DEVVAL_ENV_BASE, D.DEVVAL_MOB_BASE],
            "DEVVAL_RANDOM": D.DEVVAL_RANDOM_BASE,
            "DEV_NULL_D2": D.DEV_NULL_D2_BASE,
        },
    }
    if mpath.is_file():
        have = json.loads(mpath.read_text())
        diff = [key for key in ("code", "calibration_sha256", "smoke", "arm_configs",
                                "episodes", "devval_episodes")
                if have.get(key) != wanted[key]]
        if diff:
            raise SystemExit(f"RUN-MANIFEST.json mismatch in {diff}; refusing (fail closed)")
    elif a.init_manifest:
        wanted["created_utc"] = utc()
        C.write_json(mpath, wanted)
        print(f"wrote {mpath} (commit {code['commit']}, "
              f"code digest {wanted['code_digest'][:12]})")
    else:
        raise SystemExit(f"no {mpath}; pass --init-manifest for a fresh root")

    plan = []
    for arm, k in parsed:
        d = root / f"{D.arm_name(arm)}-k{k}"
        pidf = root / f"E0-{arm}-k{k}.pid"
        st = json.loads((d / "status.json").read_text()) if (d / "status.json").is_file() else {}
        live = is_live(pidf, arm, k, root)
        if st.get("status") == "complete":
            state = "finished"
        elif live:
            state = f"live pid {live}"
        else:
            state = "resume" if (d / "resume.pt").is_file() else "fresh"
        plan.append((arm, k, d, pidf, state))
    print(f"[{utc()}] plan for {root} (commit {code['commit']}):")
    for arm, k, _d, _p, state in plan:
        print(f"  {D.arm_name(arm)} k{k} [cfg {arm_configs[f'{arm}:{k}'][:12]}]: {state}")
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
        cmd = ["systemd-run", "--user", "--scope", "-p", f"MemoryMax={a.memory_max}",
               "--quiet", "nice", "-n", "10", sys.executable, DRIVER,
               "--arm", str(arm), "--seed-index", str(k), "--root", str(root),
               "--calibration", str(a.calibration.resolve()),
               "--episodes", str(episodes), "--devval-episodes", str(n_devval),
               "--rss-cap-gb", str(a.rss_cap_gb)]
        if a.tau is not None:
            cmd += ["--tau", repr(float(a.tau))]
        if a.smoke:
            cmd.append("--smoke")
        if a.stop_after is not None:
            cmd += ["--stop-after", str(a.stop_after)]
        log = open(root / f"E0-{arm}-k{k}.log", "ab")
        p = subprocess.Popen(cmd, cwd=C.REPO, env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        pidf.write_text(str(p.pid))
        launched.append((arm, k, p.pid))
        print(f"  launched {D.arm_name(arm)} k{k} pid {p.pid} MemoryMax={a.memory_max}")
    time.sleep(10)
    dead = [(arm, k, pid) for arm, k, pid in launched
            if is_live(root / f"E0-{arm}-k{k}.pid", arm, k, root) != pid]
    if dead:
        raise SystemExit(f"FAILED TO START (or died within 10 s): {dead}")
    print(f"[{utc()}] all {len(launched)} launched processes alive")
    if a.verify:
        deadline = time.time() + 900
        want_digest = D.manifest_digest(code)
        pending = [(arm, k) for arm, k, *_ in plan]
        while pending and time.time() < deadline:
            nxt = []
            for arm, k in pending:
                sp = root / f"{D.arm_name(arm)}-k{k}" / "status.json"
                try:
                    fp = json.loads(sp.read_text())["fingerprint"]
                except (OSError, KeyError, ValueError):
                    nxt.append((arm, k))
                    continue
                if fp.get("code_digest") != want_digest:
                    raise SystemExit(f"arm {arm} k{k} fingerprint code digest differs")
                if fp.get("config_hash") != arm_configs[f"{arm}:{k}"]:
                    raise SystemExit(f"arm {arm} k{k} fingerprint config hash differs")
            pending = nxt
            if pending:
                time.sleep(10)
        if pending:
            raise SystemExit(f"no status fingerprint after 15 min: {pending}")
        print(f"[{utc()}] verified: {len(plan)} fingerprints carry this code and config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
