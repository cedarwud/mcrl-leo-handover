"""CF3PILOT training driver: A0 BASELINE / A1 OFF / A2 CF3 / A3 NULL3.

Idempotent and resumable (``status.json`` complete -> exit 0; a resume file
-> continue from its episode boundary).  Every 100 episodes: resume state,
a PRESERVED policy checkpoint, logs, status.  At episodes 100 (read-only),
250/500/750 (quarters) and 1000 (recorded only) a greedy calibration-seed
reading is appended to ``readings.jsonl`` for every arm (A0 included,
read-only, no RNG consumed).  A1-A3: lambda fixed at 0 (Amendment 2).

Learning check (coordinator, pre-launch): at the first eta update (ep 500)
each CF process waits for the A1 seed 0-2 readings in ``<root>/learning-check``
and stops (status ``stopped-learning-check``) unless A1 beats the
RANDOM_MASKED calibration reference on >= 2 of those 3 seeds.

Usage::

    run_cf3_pilot.py --arm A2 --seed-index 0 --root DIR --calibration FILE
                     [--episodes 1000] [--stop-after N] [--smoke]
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import cf3_common as C

import numpy as np
import torch

from mcrl.algorithms import cf_ratio as cfr
from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.runtime import training_pipeline as tp
from mcrl.runtime.trainer_config_validation import TD_BOOTSTRAP_EQ16, TD_BOOTSTRAP_SHARED

ARMS = {"A0": "BASELINE", "A1": "OFF", "A2": "CF3", "A3": "NULL3"}
KIND = {"A1": "none", "A2": "cf3", "A3": "null3"}
CHECKPOINT_EVERY = 100


class StopAfter(Exception):
    """The declared --stop-after boundary (diagnostic stage) -- never StopIteration."""


class GateUnavailable(RuntimeError):
    """The A1 gate readings / decision never arrived: fail loud (status failed,
    relaunchable), NEVER a learning-check stop."""


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rss_gb() -> float:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024 / 1024
    return float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(ARMS), required=True)
    ap.add_argument("--seed-index", type=int, choices=(0, 1, 2, 3, 4), required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--episodes", type=int, default=C.EPISODES)
    ap.add_argument("--stop-after", type=int, default=None,
                    help="stop cleanly at this episode boundary (diagnostic stage)")
    ap.add_argument("--smoke", action="store_true",
                    help="SMOKE ONLY: 3 episodes, quarter=1, eta from ep 2, 2 cal episodes")
    ap.add_argument("--pools", type=Path, default=None,
                    help="Amendment 3 pools root (A2/A3); default <root>/../pools")
    ap.add_argument("--rss-cap-gb", type=float, default=5.0)
    ap.add_argument("--gate-timeout-s", type=float, default=4 * 3600)
    a = ap.parse_args()

    torch.set_num_threads(1)
    arm, k = a.arm, a.seed_index
    if arm == "A0" and k not in C.A0_SEEDS:
        raise SystemExit("A0 is declared with seeds 0-2 only")
    train_seed, env_seed, mob_seed = C.TRAIN_SEEDS[k]
    out = a.root / f"{arm}-{ARMS[arm]}-s{k}"
    out.mkdir(parents=True, exist_ok=True)
    status_path, logs_path = out / "status.json", out / "episode-logs.json"
    resume_path, readings_path = out / "resume.pt", out / "readings.jsonl"
    gate_dir = a.root / "learning-check"
    if status_path.is_file():
        prev = json.loads(status_path.read_text())
        dfile0 = gate_dir / "DECISION.json"
        real_fail = dfile0.is_file() and json.loads(dfile0.read_text()).get("pass") is False
        if prev.get("status") == "complete" or (
                prev.get("status") == "stopped-learning-check" and real_fail):
            print(f"[{arm}s{k}] already {prev['status']}; nothing to do")
            return 0

    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    code = C.code_manifest()
    code_digest = C.manifest_digest(code)
    run_manifest_path = a.root / "RUN-MANIFEST.json"
    if not run_manifest_path.is_file():
        raise SystemExit(f"no {run_manifest_path}; launch through scripts/cf3_launch.py")
    run_manifest = json.loads(run_manifest_path.read_text())
    if (run_manifest.get("code") != code or run_manifest.get("calibration_sha256") != calib_sha
            or bool(run_manifest.get("smoke")) != bool(a.smoke)):
        raise SystemExit("RUN-MANIFEST.json does not match this code / calibration / mode; "
                         "refusing to run (fail closed)")
    tle_sha = tp.assert_tle_archive_pinned()
    record = tp.validate_server_setup(tp.CANONICAL_PREREG,
                                      probe_summary_path=tp.CORRECTED_PROBE_SUMMARY)
    episodes = 3 if a.smoke else a.episodes
    cf_arm = arm != "A0"
    config = C.pilot_config(record, arm, episodes)
    n_cal = 2 if a.smoke else C.N_CAL
    quarter = 1 if a.smoke else 250
    eta_first = 2 if a.smoke else 500
    factory = C.env_factory()
    env = factory()
    env.assert_ready_to_train()

    pools, pool_shas = [], {}
    if arm in ("A2", "A3"):
        pools_root = a.pools or (a.root.parent / "pools")
        kind = KIND[arm]
        for name, head in cfr.source_names(kind):
            pth = C.pool_path(pools_root, k, name)
            meta = json.loads(pth.with_suffix(".json").read_text())
            buf = cfr.PoolBuffer.load(pth)
            want_seeds = [list(x) for x in C.pool_seeds(k)]
            if (meta["name"] != name or meta["seed_index"] != k or meta["seeds"] != want_seeds
                    or meta["episodes"] != C.POOL_EPISODES or meta["tle_file_set_sha256"] != tle_sha
                    or meta["pool_sha256"] != buf.sha256 or meta["state_dim"] != 113):
                raise SystemExit(f"pool {pth} metadata does not match this run; fail closed")
            if run_manifest.get("pools", {}).get(str(pth.relative_to(pools_root))) != buf.sha256:
                raise SystemExit(f"pool {pth} not in RUN-MANIFEST.json with this hash; fail closed")
            pools.append((name, head, buf))
            pool_shas[name] = buf.sha256

    settings = None
    if cf_arm:
        settings = cfr.CFRatioSettings(
            source_kind=KIND[arm], rho=1.0 / 9.0, alpha=1.0, h_cap_inter=0.6016,
            quarter_episodes=quarter, eta_first_update_episode=eta_first,
            catfish_buffer_capacity=C.POOL_EPISODES * 1000,
            eta0=float(calib["eta0_bit_per_J"]),
            bits_scale=float(calib["bits_scale"]),
            joules_scale=float(calib["joules_scale"]),
            calibration_env_seed_base=C.CAL_ENV_BASE,
            calibration_mobility_seed_base=C.CAL_MOB_BASE,
            calibration_episodes=n_cal,
        )
        trainer = cfr.CFRatioTrainer(env, config, settings, env_factory=factory, pools=pools,
                                     train_seed=train_seed, env_seed=env_seed,
                                     mobility_seed=mob_seed)
    else:
        trainer = MODQNTrainer(env, config, train_seed=train_seed, env_seed=env_seed,
                               mobility_seed=mob_seed)

    fingerprint = {
        "arm": arm, "seed_index": k, "seeds": [train_seed, env_seed, mob_seed],
        "config": asdict(config), "settings": None if settings is None else asdict(settings),
        "calibration_sha256": calib_sha, "tle_file_set_sha256": tle_sha,
        "prereg_digest": record.digest, "smoke": bool(a.smoke),
        "code": code, "code_digest": code_digest, "pool_sha256": pool_shas,
    }
    status = {
        "status": "running", "arm": arm, "name": ARMS[arm], "seed_index": k,
        "episodes_target": episodes, "pid": os.getpid(), "started_utc": utc(),
        "fingerprint": fingerprint, "tle_root": str(tp.resolve_tle_root()),
        "checkpoints": {},
    }

    start, logs = 0, []
    if resume_path.is_file():
        payload = torch.load(resume_path, map_location="cpu", weights_only=False)
        if payload.get("fingerprint") != fingerprint:
            raise SystemExit("resume fingerprint does not match this run")
        trainer.load_training_state_dict(payload["trainer_state"])
        start, logs = int(payload["next_episode"]), list(payload["logs"])
        if len(logs) != start:
            raise SystemExit("resume logs are not contiguous")
        if status_path.is_file():
            status["checkpoints"] = json.loads(status_path.read_text()).get("checkpoints", {})
        status["resumed_from_episode"] = start
        print(f"[{arm}s{k}] resuming at episode {start}", flush=True)
    C.write_json(status_path, status)
    t0 = time.time()
    t_last = [t0]

    def log_rows():
        return logs if cf_arm else [asdict(x) for x in logs]

    def save(episode_done: int) -> None:
        payload = {"schema": "cf3-resume-v1", "next_episode": episode_done,
                   "fingerprint": fingerprint, "logs": logs,
                   "trainer_state": trainer.training_state_dict()}
        tmp = resume_path.with_suffix(".pt.tmp")
        torch.save(payload, tmp)
        tmp.replace(resume_path)
        pol = out / f"policy-ep{episode_done:05d}.pt"
        if cf_arm:
            trainer.save_policy(pol, episode_done - 1)
        else:
            tmp = pol.with_suffix(".pt.tmp")
            trainer.save_checkpoint(tmp, episode=episode_done - 1,
                                    checkpoint_kind=config.checkpoint_primary_report,
                                    logs=logs)
            tmp.replace(pol)
        C.write_json(logs_path, log_rows())
        status["checkpoints"][str(episode_done)] = {"path": str(pol),
                                                    "sha256": C.sha256_file(pol)}
        status.update(episodes_completed=episode_done, rss_gb=rss_gb(),
                      wall_s=time.time() - t0, updated_utc=utc(),
                      eta=getattr(trainer, "eta", None), lam=getattr(trainer, "lam", None))
        C.write_json(status_path, status)

    def a0_reading(episode_done: int) -> dict:
        pol = C.modqn_greedy(trainer)
        enc = lambda states, t: trainer._encode_states(states)  # noqa: E731
        m = cfr.pooled_rollout(lambda i: pol, env_factory=factory, encode=enc,
                               seeds=C.cal_seeds(n_cal))
        return {"episode": episode_done, "measured_ee": m["ee"],
                "measured_h_inter": m["h_inter"], "measured_h_intra": m["h_intra"],
                "measured_served": m["served"], "measured_beams": m["beams"],
                "measured_bits": m["bits"], "measured_joules": m["joules"],
                "kind": "a0-reading"}

    def append_reading(row: dict) -> None:
        with open(readings_path, "a") as f:
            f.write(json.dumps({k2: row[k2] for k2 in row if k2 != "measured_ee_ep"},
                               default=str) + "\n")

    progress_eps = (1,) if a.smoke else (100,)

    def progress_reading(episode_done: int) -> None:
        """Read-only calibration reading between quarters (coordinator:
        readings at 100/250/500/750/1000).  Consumes no training RNG and
        changes no trainer state."""
        if cf_arm:
            m = trainer.measure_on_calibration()
            row = {"episode": episode_done, "measured_ee": m["ee"],
                   "measured_h_inter": m["h_inter"], "measured_h_intra": m["h_intra"],
                   "measured_served": m["served"], "measured_beams": m["beams"],
                   "measured_bits": m["bits"], "measured_joules": m["joules"],
                   "eta": trainer.eta, "lambda": trainer.lam, "kind": "progress-reading"}
        else:
            row = a0_reading(episode_done)
        append_reading(row)

    def gate(episode_done: int, row: dict) -> None:
        """Declared learning check.  A1 seeds 0-2 each publish their reading;
        ONE process (O_EXCL lock) writes DECISION.json; every process reads
        it back and rejects any file whose fingerprint is not its own."""
        gate_dir.mkdir(parents=True, exist_ok=True)
        append_reading(dict(row, gate="pending"))
        ref = float(calib["random_reference_ee"])
        gfp = {"code_digest": code_digest, "calibration_sha256": calib_sha,
               "tle_file_set_sha256": tle_sha, "gate_episode": episode_done,
               "random_reference_ee": ref, "gate_seeds": list(C.GATE_SEEDS)}
        if arm == "A1" and k in C.GATE_SEEDS:
            C.write_json(gate_dir / f"A1-s{k}.json",
                         {"seed_index": k, "measured_ee": row["measured_ee"],
                          "episode": episode_done, "utc": utc(), "gate_fingerprint": gfp})
        deadline = time.time() + a.gate_timeout_s
        files = [gate_dir / f"A1-s{j}.json" for j in C.GATE_SEEDS]
        while not all(f.is_file() for f in files):
            if time.time() > deadline:
                raise GateUnavailable("timed out waiting for the A1 gate readings")
            time.sleep(20)
        seeds = [json.loads(f.read_text()) for f in files]
        for srow in seeds:
            if srow.get("gate_fingerprint") != gfp:
                raise SystemExit(f"stale/mismatched A1 gate file {srow}; fail closed")
        dfile, lock = gate_dir / "DECISION.json", gate_dir / "DECISION.lock"
        if not dfile.is_file():
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{arm}s{k} pid {os.getpid()} {utc()}".encode())
                os.close(fd)
                vals = [srow["measured_ee"] for srow in seeds]
                wins = sum(v > ref for v in vals)
                decision = {"A1_seed_indices": list(C.GATE_SEEDS), "A1_measured_ee": vals,
                            "random_reference_ee": ref, "wins": wins, "pass": wins >= 2,
                            "decided_utc": utc(), "by": f"{arm}s{k}",
                            "gate_fingerprint": gfp, "code_commit": code["commit"]}
                tmp = gate_dir / f"DECISION.json.{os.getpid()}.tmp"
                tmp.write_text(json.dumps(decision, indent=2, sort_keys=True))
                os.replace(tmp, dfile)
            except FileExistsError:
                pass
        while not dfile.is_file():
            if time.time() > deadline:
                raise GateUnavailable("timed out waiting for DECISION.json")
            time.sleep(5)
        decision = json.loads(dfile.read_text())
        if decision.get("gate_fingerprint") != gfp:
            raise SystemExit("DECISION.json fingerprint does not match this run; fail closed")
        status["learning_check"] = decision
        if not decision["pass"]:
            raise cfr.LearningCheckStop(f"A1 beat RANDOM on {decision['wins']}/3 seeds")

    def on_episode(log) -> None:
        row = log if cf_arm else asdict(log)
        if not cf_arm:
            logs.append(log)
        episode_done = row["episode"] + 1
        if rss_gb() > a.rss_cap_gb:
            raise MemoryError(f"RSS {rss_gb():.2f} GB > cap {a.rss_cap_gb}")
        if cf_arm and row.get("quarter"):
            append_reading(row["quarter"])
        if not cf_arm and episode_done % quarter == 0:
            append_reading(a0_reading(episode_done))
        if episode_done in progress_eps:
            progress_reading(episode_done)
        if episode_done % CHECKPOINT_EVERY == 0 or episode_done == episodes or (
            a.smoke) or episode_done == a.stop_after:
            save(episode_done)
            now = time.time()
            print(f"[{arm}s{k}] ep {episode_done} saved; rss {rss_gb():.2f} GB; "
                  f"{now - t_last[0]:.0f}s since last save; wall {now - t0:.0f}s", flush=True)
            t_last[0] = now
        if a.stop_after is not None and episode_done >= a.stop_after:
            raise StopAfter

    try:
        if cf_arm:
            trainer.learning_gate = gate
            logs_ref = logs

            def cb(log):
                logs_ref.append(log)
                on_episode(log)

            trainer.train_cf(start_episode=start, initial_logs=list(logs),
                             episode_callback=cb, progress_every=50)
        else:
            from mcrl.runtime.training_pipeline import _episode_log_from_dict
            init = [_episode_log_from_dict(r) if isinstance(r, dict) else r for r in logs]
            logs[:] = init
            trainer.train(progress_every=50, start_episode=start, initial_logs=list(init),
                          episode_callback=on_episode)
    except StopAfter:
        status.update(status="stopped-at", stopped_at=a.stop_after, stopped_utc=utc())
        C.write_json(status_path, status)
        print(f"[{arm}s{k}] stopped cleanly at {a.stop_after}", flush=True)
        return 0
    except cfr.LearningCheckStop as stop:
        # train_cf appended the gate episode's log and ran the callback before
        # re-raising, so len(logs) IS the number of completed episodes.
        save(len(logs))
        status.update(status="stopped-learning-check", reason=str(stop), stopped_utc=utc())
        C.write_json(status_path, status)
        print(f"[{arm}s{k}] STOPPED by learning check: {stop}", flush=True)
        return 0
    except Exception as err:
        status.update(status="failed", error_type=type(err).__name__, error=str(err),
                      failed_utc=utc())
        C.write_json(status_path, status)
        raise

    C.write_json(logs_path, log_rows())
    status.update(status="complete", episodes_completed=len(logs), finished_utc=utc(),
                  wall_s=time.time() - t0, final_policy=str(out / f"policy-ep{episodes:05d}.pt"),
                  masking_diagnostics=trainer.get_masking_diagnostics())
    if cf_arm:
        status["dual_trajectory"] = trainer.dual_trajectory
    C.write_json(status_path, status)
    print(f"[{arm}s{k}] complete: {len(logs)} episodes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
