"""S1 formal screen launcher, MC2 round -- the complete matrix, or nothing.

**FORMAL LANE (Amendment 13).**  Launching this spends the formal evaluation
episodes.  Amendment 13 section 7: "Do not partially open the formal set with only a
subset of arms", so the launcher refuses any spec list that is not the complete
declared matrix unless ``--dry-run`` (which starts nothing) or an explicit
``--i-am-resuming`` for a restart after a crash.

"The complete matrix" is about the DECLARATION, not about simultaneity: the matrix is
declared and hashed in one manifest before anything starts, and the runs then execute
in WAVES of at most ``--max-live-workers`` (default 8) single-thread workers, because
that is the machine's budget.  ``--keep-filled`` turns this script into a supervisor
that keeps the wave full until every declared run is complete; it starts nothing that
is not in the manifest and it can be re-run safely (one supervisor per root, enforced
by an anchored ``/proc`` check on its own pid file).

Before launching anything it counts the LIVE scientific workers on this machine by an
anchored ``/proc/<pid>/exe`` + ``cwd`` + ``cmdline`` scan -- never ``pgrep -f`` -- and
refuses to exceed the cap, so an S1 wave cannot quietly oversubscribe a machine that
is already running another lane's training.

Usage::

    s1_launch.py --root DIR --calibration FILE --mechanism-id MC2-JGO-v1
                 [--optional D3-null,D3-XEP] [--reading-rules FILE]
                 [--init-manifest] [--dry-run] [--preflight-dev]
                 [--max-live-workers 8] [--launch-limit N] [--keep-filled]
                 [--memory-max 5G] [SPEC ...]
    SPEC = CELL:K   (cells of the frozen mechanism id, k = 0,1,2); default = all.
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
import s1_common as S

from run_s1 import FORMAL_MANIFEST, PREFLIGHT_MANIFEST, PREFLIGHT_MAX_EPISODES

DRIVER = "scripts/run_s1.py"
LAUNCHER_NAME = "s1_launch.py"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_live(pidfile: Path, cell: str, k: int, root: Path) -> int | None:
    """The pid in ``pidfile``, if it IS this run: anchored on /proc, never pgrep."""
    if not pidfile.is_file():
        return None
    try:
        pid = int(pidfile.read_text().strip())
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        cwd = os.readlink(f"/proc/{pid}/cwd")
    except (OSError, ValueError):
        return None
    args = [c.decode() for c in cmd if c]
    want = [DRIVER, "--cell", str(cell), "--seed-index", str(k), "--root", str(root)]
    joined = " ".join(args)
    if (all(w in args for w in want)
            and f"--cell {cell} --seed-index {k} --root {root}" in joined
            and Path(cwd) == C.REPO):
        return pid
    return None


def live_scientific_workers(cwd_prefix: str, exclude: set[int]) -> list[dict]:
    """Every live Python SCRIPT process of this user under ``cwd_prefix``.

    Anchored, never ``pgrep -f``: ``/proc/<pid>/exe`` must resolve to THIS interpreter
    binary, ``/proc/<pid>/cwd`` must lie under ``cwd_prefix`` (a workspace, never
    ``/`` or a system daemon), and ``/proc/<pid>/cmdline`` must run a ``.py`` script.
    Every lane's learner counts -- the cap is on the machine, not on this root.
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
        prefix = cwd_prefix.rstrip("/")
        if not (cwd == prefix or cwd.startswith(prefix + "/")):
            continue
        script = next((x for x in argv[1:] if x.endswith(".py")), None)
        if script is None or Path(script).name == LAUNCHER_NAME:
            continue
        out.append({"pid": pid, "cwd": cwd, "script": script,
                    "cmdline": " ".join(argv)[:240]})
    return sorted(out, key=lambda r: r["pid"])


def assert_complete_matrix(specs, declared, *, dry_run: bool = False,
                           resuming: bool = False, preflight: bool = False) -> None:
    """Amendment 13 section 7: the formal set opens with every declared run, or none.

    ``--dry-run`` starts nothing and ``--i-am-resuming`` restarts a root whose formal
    set is already open; every other partial spec list is refused BEFORE the manifest
    is written and before any process is started.  Waves are NOT a partial matrix:
    the whole matrix is declared here and ``--launch-limit`` only defers starts.
    """
    if len(set(specs)) != len(specs):
        raise SystemExit(f"duplicate specs: {specs}")
    unknown = [s for s in specs if s not in set(declared)]
    if unknown:
        raise SystemExit(f"not declared cells of this mechanism id: {unknown}")
    if preflight:
        # A DEVELOPMENT-lane preflight is a wiring check on development seeds and is
        # not evidence, so a subset is legitimate there -- and ONLY there.
        return
    if sorted(specs) == sorted(declared) or dry_run or resuming:
        return
    raise SystemExit(
        "Amendment 13 section 7: the formal set is opened with the complete "
        f"{len(declared)}-run matrix or not at all; got {sorted(specs)}"
    )


def launch_priority(spec) -> tuple[int, str]:
    """Longest-first wave order.  Scheduling order changes wall time and nothing else:
    every run's seeds, data and identity are fixed by the manifest."""
    if spec.is_judge:
        return (0 if "R" in spec.sources else 1), spec.name
    return (2, spec.name)


def plan_rows(root: Path, mid: str, optional: tuple[str, ...], parsed, arm_configs):
    rows = []
    for name, k in parsed:
        spec = S.cell(mid, name, optional=optional)
        run_id = S.run_name(mid, name, optional=optional)
        d = root / f"{run_id}-k{k}"
        pidf = root / f"{run_id}-k{k}.pid"
        st = (json.loads((d / "status.json").read_text())
              if (d / "status.json").is_file() else {})
        live = is_live(pidf, name, k, root)
        if st.get("status") == "complete":
            state = "finished"
        elif live:
            state = f"live pid {live}"
        else:
            state = "resume" if (d / "resume.pt").is_file() else "fresh"
        rows.append({"cell": name, "k": k, "spec": spec, "run_id": run_id,
                     "dir": d, "pidf": pidf, "state": state,
                     "cfg": arm_configs[f"{name}:{k}"]})
    rows.sort(key=lambda r: (launch_priority(r["spec"]), r["k"]))
    return rows


def supervisor_lock(root: Path) -> Path:
    """One supervisor per root, anchored on /proc (a stale pid file never blocks)."""
    lock = root / "S1-SUPERVISOR.pid"
    if lock.is_file():
        try:
            pid = int(lock.read_text().strip())
            argv = Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace")
        except (OSError, ValueError):
            argv = ""
        if LAUNCHER_NAME in argv and str(root) in argv:
            raise SystemExit(f"a supervisor is already running for {root}: pid {pid}")
    lock.write_text(str(os.getpid()))
    return lock


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--mechanism-id", required=True, choices=S.MECHANISM_IDS)
    ap.add_argument("--optional", default=None,
                    help="OPTIONAL cells included at freeze (D3-null,D3-XEP)")
    ap.add_argument("--reading-rules", type=Path, default=None,
                    help="the controller's FROZEN reading rules; hashed into the "
                         "manifest (required for a formal manifest)")
    ap.add_argument("--init-manifest", action="store_true")
    ap.add_argument("--episodes", type=int, default=S.EPISODES)
    ap.add_argument("--eval-episodes", type=int, default=S.N_EVAL)
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--preflight-dev", action="store_true",
                    help="DEVELOPMENT-lane preflight of this harness (DEV seeds)")
    ap.add_argument("--memory-max", default="5G")
    ap.add_argument("--rss-cap-gb", type=float, default=4.5)
    ap.add_argument("--max-live-workers", type=int, default=8,
                    help="refuse if live scientific workers + new runs exceed this")
    ap.add_argument("--launch-limit", type=int, default=None,
                    help="start at most N of the startable runs, in wave order")
    ap.add_argument("--keep-filled", action="store_true",
                    help="stay alive and keep the wave full until every declared run "
                         "is complete")
    ap.add_argument("--poll", type=int, default=120, help="--keep-filled poll seconds")
    ap.add_argument("--worker-cwd-prefix", default=str(Path.home()))
    ap.add_argument("--i-am-resuming", action="store_true",
                    help="a restart after a crash: allow a partial spec list because "
                         "the formal set is already open for this root")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("specs", nargs="*")
    a = ap.parse_args()

    root = a.root.resolve()
    lane = S.DEV_LANE if a.preflight_dev else S.S1_LANE
    mid = a.mechanism_id
    optional = tuple(x for x in (p.strip() for p in (a.optional or "").split(","))
                     if x)
    declared = list(S.specs(mid, optional=optional))
    specs = list(a.specs) or list(declared)
    assert_complete_matrix(specs, declared, dry_run=a.dry_run,
                           resuming=a.i_am_resuming,
                           preflight=a.preflight_dev)
    episodes, n_eval = int(a.episodes), int(a.eval_episodes)
    if a.preflight_dev and episodes > PREFLIGHT_MAX_EPISODES:
        raise SystemExit(f"--preflight-dev caps episodes at {PREFLIGHT_MAX_EPISODES}")
    if not a.preflight_dev and episodes != S.EPISODES:
        raise SystemExit(f"the frozen S1 depth is {S.EPISODES} episodes")
    parsed = []
    for s in specs:
        name, _, k_s = s.rpartition(":")
        if not name or not k_s.isdigit() or int(k_s) not in S.SEED_INDICES:
            raise SystemExit(f"bad spec {s} (CELL:K, k in {S.SEED_INDICES})")
        S.cell(mid, name, optional=optional)
        parsed.append((name, int(k_s)))

    S.assert_environment()
    if any(S.cell(mid, n, optional=optional).uses_xep for n, _k in parsed):
        ref = S.load_xep_reference()
        print(f"T0-XEP reference verified: sha256 {ref.sha256}, key {ref.key}, "
              f"policy {ref.policy}, {ref.steps} steps x {ref.users} users")

    from mcrl.runtime import training_pipeline as tp
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    reading_rules = None
    if a.reading_rules is not None:
        reading_rules = {
            "document": str(a.reading_rules),
            "sha256": C.sha256_file(a.reading_rules),
            "frozen_before": "any formal outcome exists",
        }
    elif lane == S.S1_LANE and a.init_manifest:
        raise SystemExit(
            "a formal S1 manifest must hash the controller's FROZEN reading rules: "
            "pass --reading-rules FILE (Amendment 13 section 7 item 7)"
        )
    subset = None
    if a.preflight_dev:
        # the preflight declares exactly the cells it was asked to exercise
        seen: list[str] = []
        for name, _k in parsed:
            if name not in seen:
                seen.append(name)
        subset = tuple(seen)
    wanted = S.declared_manifest(record, calib, calib_sha, mechanism_id=mid,
                                 episodes=episodes, eval_episodes=n_eval,
                                 optional=optional, lane=lane, cell_names=subset,
                                 reading_rules=reading_rules)
    wanted["calibration"] = str(a.calibration.resolve())
    wanted["tle_root"] = os.environ.get("MCRL_TLE_ROOT")
    arm_configs = wanted["arm_configs"]
    if len(set(arm_configs.values())) != len(arm_configs):
        raise SystemExit("two declared runs share a configuration hash; refusing")

    root.mkdir(parents=True, exist_ok=True)
    manifest_name = PREFLIGHT_MANIFEST if a.preflight_dev else FORMAL_MANIFEST
    other = root / (FORMAL_MANIFEST if a.preflight_dev else PREFLIGHT_MANIFEST)
    if other.is_file():
        raise SystemExit(f"{root} already holds a {other.name}: a preflight root and "
                         "a formal root are never the same root")
    mpath = root / manifest_name
    if mpath.is_file():
        have = json.loads(mpath.read_text())
        diff = [key for key in ("code", "calibration_sha256", "arm_configs",
                                "episodes", "eval_episodes", "namespaces",
                                "frozen_hyperparameters", "cells", "mechanism_id",
                                "lane", "reading_rules", "optional_cells_included")
                if have.get(key) != wanted[key]]
        if diff:
            raise SystemExit(f"{manifest_name} mismatch in {diff}; refusing (fail closed)")
    elif a.init_manifest:
        wanted["created_utc"] = utc()
        C.write_json(mpath, wanted)
        print(f"wrote {mpath} (commit {wanted['code']['commit']}, "
              f"code digest {wanted['code_digest'][:12]}, "
              f"{len(wanted['specs'])} declared runs, cells "
              f"{wanted['declared_cells']})")
    else:
        raise SystemExit(f"no {mpath}; pass --init-manifest for a fresh root")

    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    if not env.get("MCRL_TLE_ROOT"):
        raise SystemExit("MCRL_TLE_ROOT must point at the pinned archive copy")

    def one_pass(*, start_allowed: bool) -> tuple[int, int]:
        """Plan, report, and start as many runs as the cap allows.

        Returns ``(started, outstanding)``; ``outstanding`` counts every declared run
        that is not yet complete, so a supervisor knows when it is done.
        """
        rows = plan_rows(root, mid, optional, parsed, arm_configs)
        startable = [r for r in rows if r["state"] in ("fresh", "resume")]
        workers = live_scientific_workers(a.worker_cwd_prefix,
                                          exclude={os.getpid(), os.getppid()})
        room = max(0, int(a.max_live_workers) - len(workers))
        if a.launch_limit is not None:
            room = min(room, int(a.launch_limit))
        to_launch = startable[:room] if start_allowed else []
        print(f"[{utc()}] S1 plan for {root} ({mid}, lane {lane}, "
              f"commit {wanted['code']['commit']}):")
        for r in rows:
            note = ("  -> launch" if r in to_launch
                    else "  -> waiting for a free worker slot"
                    if r in startable else "")
            print(f"  {r['run_id']} k{r['k']} [cfg {r['cfg'][:12]}]: "
                  f"{r['state']}{note}")
        print(f"  live scientific workers under {a.worker_cwd_prefix}: "
              f"{len(workers)} / cap {a.max_live_workers}")
        for w in workers:
            print(f"    pid {w['pid']} cwd {w['cwd']} :: {w['cmdline']}")
        launched = []
        for r in to_launch:
            cmd = ["systemd-run", "--user", "--scope", "-p",
                   f"MemoryMax={a.memory_max}", "--quiet", "nice", "-n", "10",
                   sys.executable, DRIVER,
                   "--cell", r["cell"], "--seed-index", str(r["k"]),
                   "--root", str(root),
                   "--calibration", str(a.calibration.resolve()),
                   "--mechanism-id", mid,
                   "--episodes", str(episodes), "--eval-episodes", str(n_eval),
                   "--rss-cap-gb", str(a.rss_cap_gb)]
            if optional:
                cmd += ["--optional", ",".join(optional)]
            if a.preflight_dev:
                cmd.append("--preflight-dev")
            if a.stop_after is not None:
                cmd += ["--stop-after", str(a.stop_after)]
            log = open(root / f"{r['run_id']}-k{r['k']}.log", "ab")
            p = subprocess.Popen(cmd, cwd=C.REPO, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
            r["pidf"].write_text(str(p.pid))
            launched.append((r, p.pid))
            print(f"  launched {r['run_id']} k{r['k']} pid {p.pid} "
                  f"MemoryMax={a.memory_max}")
        if launched:
            time.sleep(10)
            dead = [(r["run_id"], r["k"], pid) for r, pid in launched
                    if is_live(r["pidf"], r["cell"], r["k"], root) != pid]
            if dead:
                raise SystemExit(f"FAILED TO START (or died within 10 s): {dead}")
            for r, pid in launched:
                try:
                    exe = os.readlink(f"/proc/{pid}/exe")
                    cwd = os.readlink(f"/proc/{pid}/cwd")
                    argv = Path(f"/proc/{pid}/cmdline").read_bytes().replace(
                        b"\0", b" ").decode()
                except OSError as err:
                    raise SystemExit(f"{r['run_id']} k{r['k']} pid {pid}: "
                                     f"/proc unreadable: {err}") from err
                print(f"  /proc/{pid}: exe={exe} cwd={cwd} cmdline={argv.strip()}")
            print(f"[{utc()}] all {len(launched)} launched processes alive")
        outstanding = sum(1 for r in rows if r["state"] != "finished")
        return len(launched), outstanding

    if a.dry_run:
        one_pass(start_allowed=False)
        print("--dry-run: nothing started, no formal episode touched")
        return 0

    if a.keep_filled:
        lock = supervisor_lock(root)
        try:
            while True:
                _started, outstanding = one_pass(start_allowed=True)
                if outstanding == 0:
                    print(f"[{utc()}] every declared run is complete")
                    return 0
                time.sleep(max(10, int(a.poll)))
        finally:
            lock.unlink(missing_ok=True)

    one_pass(start_allowed=True)
    if a.verify:
        deadline = time.time() + 900
        pending = [(r["cell"], r["k"], r["run_id"])
                   for r in plan_rows(root, mid, optional, parsed, arm_configs)
                   if r["state"] != "finished"]
        while pending and time.time() < deadline:
            nxt = []
            for name, k, run_id in pending:
                sp = root / f"{run_id}-k{k}" / "status.json"
                try:
                    fp = json.loads(sp.read_text())["fingerprint"]
                except (OSError, KeyError, ValueError):
                    nxt.append((name, k, run_id))
                    continue
                if fp.get("code_digest") != wanted["code_digest"]:
                    raise SystemExit(f"{run_id} k{k} fingerprint code digest differs")
                if fp.get("config_hash") != arm_configs[f"{name}:{k}"]:
                    raise SystemExit(f"{run_id} k{k} fingerprint config hash differs")
            pending = nxt
            if pending:
                time.sleep(10)
        if pending:
            print(f"[{utc()}] not yet started (waiting for a worker slot): {pending}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
