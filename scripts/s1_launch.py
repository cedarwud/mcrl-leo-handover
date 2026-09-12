"""S1 formal screen launcher -- the complete 6 x 3 matrix, or nothing.

**FORMAL LANE (Amendment 13).**  Launching this spends the formal evaluation
episodes.  Amendment 13 section 7: "Do not partially open the formal set with only a
subset of arms", so the launcher refuses any spec list that is not the full 18 unless
``--dry-run`` (which starts nothing) or an explicit ``--i-am-resuming`` for a restart
after a crash.

It writes ``<root>/S1-MANIFEST.json`` (the full frozen declaration plus one
configuration hash per run) with ``--init-manifest``; afterwards the manifest must
match exactly and every driver re-checks its own hash before training.

Usage::

    s1_launch.py --root DIR --calibration FILE [--init-manifest] [--dry-run]
                 [--episodes 1000] [--memory-max 5G] [SPEC ...]
    SPEC = ARM:K  (arms 1-6, k = 0,1,2); default = all 18.
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
import s1_common as S

DRIVER = "scripts/run_s1.py"


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


def assert_complete_matrix(specs, *, dry_run: bool = False,
                           resuming: bool = False) -> None:
    """Amendment 13 section 7: the formal set opens with all 18 runs, or not at all.

    ``--dry-run`` starts nothing, and ``--i-am-resuming`` restarts a root whose formal
    set is already open; every other partial spec list is refused BEFORE the manifest
    is written and before any process is started.
    """
    if len(set(specs)) != len(specs):
        raise SystemExit(f"duplicate specs: {specs}")
    if sorted(specs) == sorted(S.SPECS) or dry_run or resuming:
        return
    raise SystemExit(
        "Amendment 13 section 7: the formal set is opened with the complete "
        f"{len(S.SPECS)}-run matrix or not at all; got {sorted(specs)}"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--init-manifest", action="store_true")
    ap.add_argument("--episodes", type=int, default=S.EPISODES)
    ap.add_argument("--eval-episodes", type=int, default=S.N_EVAL)
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--memory-max", default="5G")
    ap.add_argument("--rss-cap-gb", type=float, default=4.5)
    ap.add_argument("--max-processes", type=int, default=18)
    ap.add_argument("--i-am-resuming", action="store_true",
                    help="a restart after a crash: allow a partial spec list because "
                         "the formal set is already open for this root")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("specs", nargs="*")
    a = ap.parse_args()

    root = a.root.resolve()
    specs = list(a.specs) or list(S.SPECS)
    assert_complete_matrix(specs, dry_run=a.dry_run, resuming=a.i_am_resuming)
    if len(specs) > a.max_processes:
        raise SystemExit(f"{len(specs)} runs exceeds --max-processes {a.max_processes}")
    parsed = []
    for s in specs:
        arm_s, k_s = s.split(":")
        arm, k = int(arm_s), int(k_s)
        if arm not in S.ARMS or k not in S.SEED_INDICES:
            raise SystemExit(f"bad spec {s}")
        parsed.append((arm, k))

    S.assert_environment()
    ref = D.load_xep_reference()
    print(f"T0-XEP reference verified: sha256 {ref.sha256}, key {ref.key}, "
          f"policy {ref.policy}, {ref.steps} steps x {ref.users} users")

    from mcrl.runtime import training_pipeline as tp
    episodes, n_eval = int(a.episodes), int(a.eval_episodes)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    wanted = S.declared_manifest(record, calib, calib_sha, episodes=episodes,
                                 eval_episodes=n_eval)
    wanted["calibration"] = str(a.calibration.resolve())
    wanted["tle_root"] = os.environ.get("MCRL_TLE_ROOT")
    arm_configs = wanted["arm_configs"]

    root.mkdir(parents=True, exist_ok=True)
    mpath = root / "S1-MANIFEST.json"
    if mpath.is_file():
        have = json.loads(mpath.read_text())
        diff = [key for key in ("code", "calibration_sha256", "arm_configs",
                                "episodes", "eval_episodes", "namespaces",
                                "frozen_hyperparameters", "arms")
                if have.get(key) != wanted[key]]
        if diff:
            raise SystemExit(f"S1-MANIFEST.json mismatch in {diff}; refusing (fail closed)")
    elif a.init_manifest:
        wanted["created_utc"] = utc()
        C.write_json(mpath, wanted)
        print(f"wrote {mpath} (commit {wanted['code']['commit']}, "
              f"code digest {wanted['code_digest'][:12]})")
    else:
        raise SystemExit(f"no {mpath}; pass --init-manifest for a fresh root")

    plan = []
    for arm, k in parsed:
        d = root / f"{S.arm_name(arm)}-k{k}"
        pidf = root / f"S1-{arm}-k{k}.pid"
        st = json.loads((d / "status.json").read_text()) if (d / "status.json").is_file() else {}
        live = is_live(pidf, arm, k, root)
        if st.get("status") == "complete":
            state = "finished"
        elif live:
            state = f"live pid {live}"
        else:
            state = "resume" if (d / "resume.pt").is_file() else "fresh"
        plan.append((arm, k, d, pidf, state))
    print(f"[{utc()}] S1 plan for {root} (commit {wanted['code']['commit']}):")
    for arm, k, _d, _p, state in plan:
        print(f"  {S.arm_name(arm)} k{k} [cfg {arm_configs[f'{arm}:{k}'][:12]}]: {state}")
    if a.dry_run:
        print("--dry-run: nothing started, no formal episode touched")
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
               "--episodes", str(episodes), "--eval-episodes", str(n_eval),
               "--rss-cap-gb", str(a.rss_cap_gb)]
        if a.stop_after is not None:
            cmd += ["--stop-after", str(a.stop_after)]
        log = open(root / f"S1-{arm}-k{k}.log", "ab")
        p = subprocess.Popen(cmd, cwd=C.REPO, env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        pidf.write_text(str(p.pid))
        launched.append((arm, k, p.pid))
        print(f"  launched {S.arm_name(arm)} k{k} pid {p.pid} MemoryMax={a.memory_max}")
    time.sleep(10)
    dead = [(arm, k, pid) for arm, k, pid in launched
            if is_live(root / f"S1-{arm}-k{k}.pid", arm, k, root) != pid]
    if dead:
        raise SystemExit(f"FAILED TO START (or died within 10 s): {dead}")
    print(f"[{utc()}] all {len(launched)} launched processes alive")
    if a.verify:
        deadline = time.time() + 900
        pending = [(arm, k) for arm, k, *_ in plan]
        while pending and time.time() < deadline:
            nxt = []
            for arm, k in pending:
                sp = root / f"{S.arm_name(arm)}-k{k}" / "status.json"
                try:
                    fp = json.loads(sp.read_text())["fingerprint"]
                except (OSError, KeyError, ValueError):
                    nxt.append((arm, k))
                    continue
                if fp.get("code_digest") != wanted["code_digest"]:
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
