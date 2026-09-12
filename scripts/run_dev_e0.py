"""DEVHARNESS E0 development-training driver (one arm, one DEV seed index).

Development lane (Amendment 6): an E0 run is an engineering run.  It is not
Amendment 4 screening evidence, it supports no statistical claim, and it never
reads a formal evaluation, calibration or CONFIRM episode.

Idempotent and resumable: a ``status.json`` marked ``complete`` exits 0; a
``resume.pt`` continues from its episode boundary after checking that the run's
whole fingerprint (code manifest, config hash, seeds, calibration) is unchanged.
Every 100 episodes: resume state, a preserved policy checkpoint, logs, status.
DEVVAL (24 episodes, fresh env per episode, greedy, no training RNG) is read at
episodes 100, 200 and 300.

Usage::

    run_dev_e0.py --arm 1 --seed-index 0 --root DIR --calibration FILE
                  [--episodes 300] [--stop-after N] [--smoke]
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import cf3_common as C
import dev_e0_common as D

import torch

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_multi_sources as cfmulti
from mcrl.runtime import training_pipeline as tp


class StopAfter(Exception):
    """The declared --stop-after boundary (never StopIteration)."""


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
    ap.add_argument("--arm", type=int, choices=sorted(D.ARMS), required=True)
    ap.add_argument("--seed-index", type=int, default=0)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--episodes", type=int, default=D.EPISODES)
    ap.add_argument("--devval-episodes", type=int, default=D.N_DEVVAL)
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--tau", type=float, default=None,
                    help="teacher temperature override (E0b tau sweep); a different "
                         "tau is a different version and a different config hash")
    ap.add_argument("--teachers", default=None,
                    help="MULTI-D3 FULL arm only: the '+'-separated canonical teacher "
                         "set, e.g. T0+T_DELTA.  Order is irrelevant (the set is "
                         "canonicalised); the identities are in the config hash.")
    ap.add_argument("--n-proposals", type=int, default=None,
                    help="MULTI-D3 matched null only: the set cardinality it is "
                         "matched to (2 for a two-teacher FULL arm)")
    ap.add_argument("--bernoulli-null", action="store_true",
                    help="MULTI-D3 matched null only: use the SELECTED Bernoulli "
                         "cardinality-matched null at the frozen p_singleton "
                         "9395/24000 (controller record 716f104e).  Without it the "
                         "rejected fixed two-proposal null is used, which is "
                         "engineering history and not a k = 8 comparator.")
    ap.add_argument("--smoke", action="store_true",
                    help="SMOKE ONLY: 3 episodes, 2 DEVVAL episodes, read at episode 1")
    ap.add_argument("--rss-cap-gb", type=float, default=4.5)
    a = ap.parse_args()

    torch.set_num_threads(1)
    tle_sha = D.assert_environment()
    arm, k = int(a.arm), int(a.seed_index)
    mech, credit = D.ARMS[arm]
    teachers = None if a.teachers is None else tuple(a.teachers.split("+"))
    if teachers is not None and cfmulti.T_NEXT_ID in teachers:
        cfmulti.register_candidate_sources(replace=True)
    spec = D.multi_spec(arm, teachers, n_proposals=a.n_proposals,
                        bernoulli=a.bernoulli_null)
    name = D.arm_name(arm, teachers, n_proposals=a.n_proposals,
                      bernoulli=a.bernoulli_null)
    out = a.root / f"{name}-k{k}"
    out.mkdir(parents=True, exist_ok=True)
    status_path, logs_path = out / "status.json", out / "episode-logs.json"
    resume_path, devval_path = out / "resume.pt", out / "devval.jsonl"
    if status_path.is_file():
        prev = json.loads(status_path.read_text())
        if prev.get("status") == "complete":
            print(f"[{name} k{k}] already complete; nothing to do")
            return 0

    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    code = D.code_manifest()
    code_digest = D.manifest_digest(code)
    episodes = 3 if a.smoke else int(a.episodes)
    n_devval = 2 if a.smoke else int(a.devval_episodes)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    cfg_payload = D.arm_config_payload(record, calib, arm, k, episodes=episodes,
                                       devval_episodes=n_devval,
                                       calibration_sha256=calib_sha, tau=a.tau,
                                       teachers=teachers, n_proposals=a.n_proposals,
                                       bernoulli=a.bernoulli_null)
    cfg_hash = D.config_hash(cfg_payload)

    run_manifest_path = a.root / "RUN-MANIFEST.json"
    if not run_manifest_path.is_file():
        raise SystemExit(f"no {run_manifest_path}; launch through scripts/dev_e0_launch.py")
    run_manifest = json.loads(run_manifest_path.read_text())
    if (run_manifest.get("code") != code
            or run_manifest.get("calibration_sha256") != calib_sha
            or bool(run_manifest.get("smoke")) != bool(a.smoke)
            or run_manifest.get("arm_configs", {}).get(
                D.spec_key(arm, k, teachers, n_proposals=a.n_proposals,
                           bernoulli=a.bernoulli_null)) != cfg_hash):
        raise SystemExit("RUN-MANIFEST.json does not match this code / calibration / "
                         "config; refusing to run (fail closed)")

    config = D.e0_config(record, episodes)
    settings = D.e0_cf_settings(calib, credit)
    dev = D.e0_dev_settings(mech, k, devval_episodes=n_devval, tau=a.tau)
    if abs(settings.eta0 - D.ETA0_EXPECTED) > 1e-6:
        raise SystemExit(f"eta_0 {settings.eta0} is not the declared {D.ETA0_EXPECTED}")
    train_seed, env_seed, mob_seed = D.dev_triple(k)
    factory = C.env_factory()
    env = factory()
    env.assert_ready_to_train()
    trainer = cfd.CFDevTrainer(env, config, settings, dev, multi=spec,
                               env_factory=factory,
                               train_seed=train_seed, env_seed=env_seed,
                               mobility_seed=mob_seed)

    fingerprint = {
        "arm": arm,
        "arm_name": name,
        "multi_spec": (None if spec is None else asdict(spec)),
        "mechanism": mech,
        "credit_mode": credit, "seed_index": k,
        "seeds": [train_seed, env_seed, mob_seed],
        "config": asdict(config), "settings": asdict(settings),
        "dev_settings": asdict(dev), "config_hash": cfg_hash,
        "calibration_sha256": calib_sha, "tle_file_set_sha256": tle_sha,
        "prereg_digest": record.digest, "smoke": bool(a.smoke),
        "code": code, "code_digest": code_digest,
        "lane": "E0-development (Amendment 6): not formal evidence",
    }
    status = {
        "status": "running", "arm": arm, "arm_name": name,
        "mechanism": mech, "credit_mode": credit, "seed_index": k,
        "episodes_target": episodes, "pid": os.getpid(), "started_utc": utc(),
        "fingerprint": fingerprint, "tle_root": str(tp.resolve_tle_root()),
        "devval_at": list(D.devval_at(episodes, smoke=a.smoke)), "checkpoints": {},
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
        print(f"[{name} k{k}] resuming at episode {start}", flush=True)
    C.write_json(status_path, status)
    t0 = time.time()

    def save(episode_done: int) -> None:
        payload = {"schema": "dev-e0-resume-v1", "next_episode": episode_done,
                   "fingerprint": fingerprint, "logs": logs,
                   "trainer_state": trainer.training_state_dict()}
        tmp = resume_path.with_suffix(".pt.tmp")
        torch.save(payload, tmp)
        tmp.replace(resume_path)
        pol = out / f"policy-ep{episode_done:05d}.pt"
        trainer.save_policy(pol, episode_done - 1)
        C.write_json(logs_path, logs)
        status["checkpoints"][str(episode_done)] = {"path": str(pol),
                                                    "sha256": C.sha256_file(pol)}
        status.update(episodes_completed=episode_done, rss_gb=rss_gb(),
                      wall_s=time.time() - t0, updated_utc=utc(),
                      eta=trainer.eta, lam=trainer.lam)
        C.write_json(status_path, status)

    def devval_reading(episode_done: int) -> None:
        """DEVVAL (greedy, fresh env per episode, no training RNG consumed)."""
        res = trainer.devval()
        full = dict(res, episode=episode_done, arm=arm, arm_name=name,
                    mechanism=mech, credit_mode=credit, seed_index=k,
                    eta=trainer.eta, lam=trainer.lam, config_hash=cfg_hash,
                    devval_seeds=[list(x) for x in trainer.devval_seeds()],
                    tle_file_set_sha256=tle_sha, kind="devval", utc=utc())
        C.write_json(out / f"devval-ep{episode_done:05d}.json", full)
        row = {kk: vv for kk, vv in full.items()
               if kk not in ("episodes", "ee_ep", "devval_seeds")}
        with open(devval_path, "a") as f:
            f.write(json.dumps(row, default=str) + "\n")
        print(f"[{name} k{k}] DEVVAL ep {episode_done}: ee={res['ee']:.6e} "
              f"served={res['served']:.5f} beams={res['beams']:.3f} "
              f"agreeT0={res['t0_agreement']:.4f}", flush=True)

    reads = set(D.devval_at(episodes, smoke=a.smoke))
    every = 1 if a.smoke else D.CHECKPOINT_EVERY

    def on_episode(log: dict) -> None:
        episode_done = int(log["episode"]) + 1
        if rss_gb() > a.rss_cap_gb:
            raise MemoryError(f"RSS {rss_gb():.2f} GB > cap {a.rss_cap_gb}")
        if episode_done in reads:
            devval_reading(episode_done)
        if (episode_done % every == 0 or episode_done == episodes
                or episode_done == a.stop_after):
            save(episode_done)
            print(f"[{name} k{k}] ep {episode_done} saved; "
                  f"rss {rss_gb():.2f} GB; wall {time.time() - t0:.0f}s", flush=True)
        if a.stop_after is not None and episode_done >= a.stop_after:
            raise StopAfter

    try:
        logs_ref = logs

        def cb(log):
            logs_ref.append(log)
            on_episode(log)

        trainer.train_cf(start_episode=start, initial_logs=list(logs),
                         episode_callback=cb, progress_every=25)
    except StopAfter:
        status.update(status="stopped-at", stopped_at=a.stop_after, stopped_utc=utc())
        C.write_json(status_path, status)
        print(f"[{name} k{k}] stopped cleanly at {a.stop_after}", flush=True)
        return 0
    except Exception as err:
        status.update(status="failed", error_type=type(err).__name__, error=str(err),
                      failed_utc=utc())
        C.write_json(status_path, status)
        raise

    C.write_json(logs_path, logs)
    status.update(status="complete", episodes_completed=len(logs), finished_utc=utc(),
                  wall_s=time.time() - t0,
                  final_policy=str(out / f"policy-ep{episodes:05d}.pt"),
                  masking_diagnostics=trainer.get_masking_diagnostics())
    C.write_json(status_path, status)
    print(f"[{name} k{k}] complete: {len(logs)} episodes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
