"""DEVHARNESS E0 launcher (the cf3_launch pattern, development lane).

* Code identity: the code manifest of THIS tree, the calibration hash and ONE
  configuration hash per arm (seeds, trainer config, CF settings, development
  settings, budget, DEVVAL seeds, prereg digest, TLE file set).  With
  ``--init-manifest`` it writes ``<root>/RUN-MANIFEST.json`` if absent; otherwise
  the existing manifest must match exactly and every driver re-checks its own
  arm's configuration hash before training (fail closed on both sides).
* Plans every requested run as finished / live / resume / fresh and prints the
  plan before anything starts.  "Live" = the PID in the pid file exists AND its
  command line is this driver with the same --arm, --seed-index and --root (and
  --cell for an MC2 judge arm) AND its cwd is this tree.
* ``--launch-limit N`` starts at most N of the fresh / resume runs, in the order the
  specs are given, so one manifest's spec list can be filled in waves (8 + 2)
  without changing the manifest.
* Before launching it counts the LIVE scientific workers on this machine by an
  anchored ``/proc/<pid>/exe`` + ``cwd`` + ``cmdline`` scan (never ``pgrep -f``) and
  refuses to exceed ``--max-live-workers`` (default 8).
* Launches with ``systemd-run --user --scope -p MemoryMax=...``, ``nice -n 10``,
  one BLAS thread, a new session and stdin from /dev/null, then verifies every
  launched process is alive with the right command line.

Usage::

    dev_e0_launch.py --root DIR --calibration FILE [--init-manifest] [--smoke]
                     [--episodes 300] [--stop-after N] [--expect N]
                     [--launch-limit N] [--max-live-workers 8]
                     [--memory-max 5G] [--dry-run] [--verify] [SPEC ...]
    SPEC = ARM:K            for the single-teacher arms 1-7
         = ARM:K:T0+Ti      for the MULTI-D3 FULL arm 8 (order irrelevant)
         = ARM:K:nN         for the MULTI-D3 matched null arm 9 (N = cardinality)
         = ARM:K:CELL       for the MC2 judge arm 10, CELL in v1-A+B v1-A+R v2-A
                            v2-A+B v2-A+R B (B = the shared, rule-independent B-only)
    default = arms 1-4 on DEV triple k = 0.
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
LAUNCHER_NAME = "dev_e0_launch.py"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_live(pidfile: Path, arm: int, k: int, root: Path,
            cell: str | None = None) -> int | None:
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
            and (cell is None or f"--cell {cell}" in joined)
            and Path(cwd) == C.REPO):
        return pid
    return None


def live_scientific_workers(cwd_prefix: str, exclude: set[int]) -> list[dict]:
    """Every live Python SCRIPT process of this user under ``cwd_prefix``.

    Anchored, never ``pgrep -f``: ``/proc/<pid>/exe`` must resolve to THIS
    interpreter binary, ``/proc/<pid>/cwd`` must lie under ``cwd_prefix`` (a
    workspace, never ``/`` or a system daemon), and ``/proc/<pid>/cmdline`` must run
    a ``.py`` script.  Every lane's learner / screen counts -- the cap is on the
    machine, not on this root.  The launcher itself and ``exclude`` are skipped.
    """
    interp = os.path.realpath(sys.executable)
    out: list[dict] = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        pid = int(d.name)
        if pid in exclude:
            continue
        try:
            exe = os.readlink(d / "exe")
            cwd = os.readlink(d / "cwd")
            argv = [x.decode(errors="replace")
                    for x in (d / "cmdline").read_bytes().split(b"\0") if x]
        except OSError:
            continue
        if not argv or os.path.realpath(exe) != interp:
            continue
        if not (cwd == cwd_prefix.rstrip("/") or cwd.startswith(cwd_prefix.rstrip("/") + "/")):
            continue
        script = next((x for x in argv[1:] if x.endswith(".py")), None)
        if script is None or Path(script).name == LAUNCHER_NAME:
            continue
        out.append({"pid": pid, "cwd": cwd, "script": script,
                    "cmdline": " ".join(argv)[:240]})
    return sorted(out, key=lambda r: r["pid"])


def parse_spec(s: str):
    """``(arm, k, teachers, n_proposals, bernoulli, cell)`` of one SPEC."""
    parts = s.split(":")
    if not 2 <= len(parts) <= 3:
        raise SystemExit(f"bad spec {s}")
    arm, k = int(parts[0]), int(parts[1])
    if arm not in D.ARMS or not 0 <= k <= D.MAX_SEED_INDEX:
        raise SystemExit(f"bad spec {s} (arms {sorted(D.ARMS)}, k in 0..{D.MAX_SEED_INDEX})")
    if k in D.RESERVED_SEED_INDICES:
        raise SystemExit(f"k = {k} is a reserved seed index and stays unused: {s}")
    teachers, n_proposals, bernoulli, cell = None, None, False, None
    if arm in D.JUDGE_ARMS:
        if len(parts) != 3:
            raise SystemExit(
                f"arm {arm} is an MC2 judge arm: spec it as {arm}:{k}:CELL with CELL "
                f"one of {D.JUDGE_CELLS}"
            )
        cell = D.judge_cell_label(parts[2])
        if "B" in D.judge_cell(cell)[1]:
            from mcrl.algorithms import cf_multi_sources as cfmulti
            cfmulti.register_candidate_sources(replace=True)
    elif len(parts) == 3:
        if arm not in D.MULTI_ARMS:
            raise SystemExit(f"arm {arm} takes no teacher set: {s}")
        tail = parts[2]
        if D.MULTI_ARMS[arm] == "NULL":
            head = tail[:-1] if tail.endswith("b") else tail
            if not (head.startswith("n") and head[1:].isdigit()):
                raise SystemExit(
                    f"the matched null is matched to a CARDINALITY: use "
                    f"{arm}:{k}:n2b (Bernoulli-matched, the SELECTED k = 8 "
                    f"null) or {arm}:{k}:n2 (rejected fixed null), not {s}"
                )
            n_proposals = int(head[1:])
            bernoulli = tail.endswith("b")
        else:
            teachers = tuple(tail.split("+"))
            if D.MULTI_ARMS[arm] == "FULL" and "T_NEXT" in teachers:
                from mcrl.algorithms import cf_multi_sources as cfmulti
                cfmulti.register_candidate_sources(replace=True)
    elif arm in D.MULTI_ARMS:
        raise SystemExit(
            f"arm {arm} is a MULTI-D3 arm: spec it as {arm}:{k}:T0+Ti (FULL) "
            f"or {arm}:{k}:n2 (matched null)"
        )
    return arm, k, teachers, n_proposals, bernoulli, cell


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
    ap.add_argument("--max-processes", type=int, default=6,
                    help="the most runs ONE invocation may start")
    ap.add_argument("--launch-limit", type=int, default=None,
                    help="start at most N of the fresh / resume runs, in spec order")
    ap.add_argument("--max-live-workers", type=int, default=8,
                    help="refuse if live scientific workers + new runs would exceed this")
    ap.add_argument("--worker-cwd-prefix", default=str(Path.home()),
                    help="cwd prefix under which a Python script counts as a worker")
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
    if a.launch_limit is not None and a.launch_limit < 0:
        raise SystemExit("--launch-limit must be >= 0")
    if a.launch_limit is None and len(specs) > a.max_processes:
        raise SystemExit(f"{len(specs)} runs exceeds --max-processes {a.max_processes}")
    if a.launch_limit is not None and a.launch_limit > a.max_processes:
        raise SystemExit(f"--launch-limit {a.launch_limit} exceeds --max-processes "
                         f"{a.max_processes}")
    parsed = [parse_spec(s) for s in specs]

    from mcrl.runtime import training_pipeline as tp
    episodes = 3 if a.smoke else int(a.episodes)
    n_devval = 2 if a.smoke else int(a.devval_episodes)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    code = D.code_manifest()
    arm_configs = {}
    arm_payloads = {}
    for arm, k, teachers, n_proposals, bernoulli, cell in parsed:
        payload = D.arm_config_payload(record, calib, arm, k, episodes=episodes,
                                       devval_episodes=n_devval,
                                       calibration_sha256=calib_sha, tau=a.tau,
                                       teachers=teachers, n_proposals=n_proposals,
                                       bernoulli=bernoulli, cell=cell)
        key = D.spec_key(arm, k, teachers, n_proposals=n_proposals,
                         bernoulli=bernoulli, cell=cell)
        if key in arm_configs:
            raise SystemExit(f"duplicate run identity {key}")
        arm_payloads[key] = payload
        arm_configs[key] = D.config_hash(payload)

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
            "DEV_NULL_MC2": D.DEV_NULL_MC2_BASE,
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
    for arm, k, teachers, n_proposals, bernoulli, cell in parsed:
        key = D.spec_key(arm, k, teachers, n_proposals=n_proposals,
                         bernoulli=bernoulli, cell=cell)
        name = D.arm_name(arm, teachers, n_proposals=n_proposals,
                          bernoulli=bernoulli, cell=cell)
        d = root / f"{name}-k{k}"
        # pid / log tag: unchanged "E0-<arm>-k<k>" for arms 1-7, plus the MULTI-D3
        # label or the MC2 cell so two runs of one arm never share a pid file.
        if arm in D.JUDGE_ARMS:
            tag = f"E0-{arm}-{cell}-k{k}"
        elif arm in D.MULTI_ARMS:
            tag = (f"E0-{arm}-{D.multi_spec(arm, teachers, n_proposals=n_proposals, bernoulli=bernoulli).label()}"
                   f"-k{k}")
        else:
            tag = f"E0-{arm}-k{k}"
        pidf = root / f"{tag}.pid"
        st = json.loads((d / "status.json").read_text()) if (d / "status.json").is_file() else {}
        live = is_live(pidf, arm, k, root, cell)
        if st.get("status") == "complete":
            state = "finished"
        elif live:
            state = f"live pid {live}"
        elif st.get("status") == "stopped-at" and a.stop_after is not None \
                and int(st.get("stopped_at", -1)) >= int(a.stop_after):
            state = f"stopped-at {st.get('stopped_at')}"
        else:
            state = "resume" if (d / "resume.pt").is_file() else "fresh"
        plan.append((arm, k, teachers, n_proposals, bernoulli, cell, key, name, tag,
                     d, pidf, state))
    startable = [p for p in plan if p[-1] in ("fresh", "resume")]
    to_launch = (startable if a.launch_limit is None
                 else startable[:int(a.launch_limit)])
    deferred = [p for p in startable if p not in to_launch]
    print(f"[{utc()}] plan for {root} (commit {code['commit']}):")
    for p in plan:
        arm, k, key, name, state = p[0], p[1], p[6], p[7], p[-1]
        note = ("  -> launch" if p in to_launch
                else "  -> deferred (launch limit)" if p in deferred else "")
        print(f"  {name} k{k} [cfg {arm_configs[key][:12]}]: {state}{note}")
    if len(to_launch) > a.max_processes:
        raise SystemExit(f"{len(to_launch)} runs exceeds --max-processes {a.max_processes}")
    workers = live_scientific_workers(a.worker_cwd_prefix,
                                      exclude={os.getpid(), os.getppid()})
    print(f"  live scientific workers under {a.worker_cwd_prefix}: {len(workers)}")
    for w in workers:
        print(f"    pid {w['pid']} cwd {w['cwd']} :: {w['cmdline']}")
    if len(workers) + len(to_launch) > a.max_live_workers:
        raise SystemExit(
            f"{len(workers)} live workers + {len(to_launch)} new runs exceeds "
            f"--max-live-workers {a.max_live_workers}; refusing"
        )
    if a.dry_run:
        return 0

    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    if not env.get("MCRL_TLE_ROOT"):
        raise SystemExit("MCRL_TLE_ROOT must point at the pinned archive copy")
    launched = []
    for (arm, k, teachers, n_proposals, bernoulli, cell, _key, name, tag, d, pidf,
         state) in to_launch:
        cmd = ["systemd-run", "--user", "--scope", "-p", f"MemoryMax={a.memory_max}",
               "--quiet", "nice", "-n", "10", sys.executable, DRIVER,
               "--arm", str(arm), "--seed-index", str(k), "--root", str(root),
               "--calibration", str(a.calibration.resolve()),
               "--episodes", str(episodes), "--devval-episodes", str(n_devval),
               "--rss-cap-gb", str(a.rss_cap_gb)]
        if cell is not None:
            cmd += ["--cell", cell]
        if teachers is not None:
            cmd += ["--teachers", "+".join(teachers)]
        if n_proposals is not None:
            cmd += ["--n-proposals", str(n_proposals)]
        if bernoulli:
            cmd.append("--bernoulli-null")
        if a.tau is not None:
            cmd += ["--tau", repr(float(a.tau))]
        if a.smoke:
            cmd.append("--smoke")
        if a.stop_after is not None:
            cmd += ["--stop-after", str(a.stop_after)]
        log = open(root / f"{tag}.log", "ab")
        p = subprocess.Popen(cmd, cwd=C.REPO, env=env, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        pidf.write_text(str(p.pid))
        launched.append((arm, k, name, tag, p.pid, cell))
        print(f"  launched {name} k{k} pid {p.pid} MemoryMax={a.memory_max}")
    time.sleep(10)
    dead = [(name, k, pid) for arm, k, name, tag, pid, cell in launched
            if is_live(root / f"{tag}.pid", arm, k, root, cell) != pid]
    if dead:
        raise SystemExit(f"FAILED TO START (or died within 10 s): {dead}")
    print(f"[{utc()}] all {len(launched)} launched processes alive")
    for arm, k, name, tag, pid, cell in launched:
        try:
            exe = os.readlink(f"/proc/{pid}/exe")
            cwd = os.readlink(f"/proc/{pid}/cwd")
            argv = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
        except OSError as err:
            raise SystemExit(f"{name} k{k} pid {pid}: /proc unreadable: {err}")
        print(f"  /proc/{pid}: exe={exe} cwd={cwd} cmdline={argv.strip()}")
    if a.verify:
        deadline = time.time() + 900
        want_digest = D.manifest_digest(code)
        pending = [(p[0], p[1], p[6], p[7]) for p in to_launch]
        while pending and time.time() < deadline:
            nxt = []
            for arm, k, key, name in pending:
                sp = root / f"{name}-k{k}" / "status.json"
                try:
                    fp = json.loads(sp.read_text())["fingerprint"]
                except (OSError, KeyError, ValueError):
                    nxt.append((arm, k, key, name))
                    continue
                if fp.get("code_digest") != want_digest:
                    raise SystemExit(f"{name} k{k} fingerprint code digest differs")
                if fp.get("config_hash") != arm_configs[key]:
                    raise SystemExit(f"{name} k{k} fingerprint config hash differs")
            pending = nxt
            if pending:
                time.sleep(10)
        if pending:
            raise SystemExit(f"no status fingerprint after 15 min: {pending}")
        print(f"[{utc()}] verified: {len(to_launch)} fingerprints carry this code and config")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
