"""S1 formal screen driver (one arm, one S1 seed index).

**FORMAL LANE (Amendment 13).**  This spends the formal evaluation episodes
``9_111_000+i / 9_112_000+i``.  It trains on the ``S1-TRAIN`` triple and, for
``D3-null``, draws from ``S1-NULL = (9_261_000, k)``; no development stream is
reused.  ``D3-XEP`` keeps the sealed DEV-NULL reference trajectory of Amendment 12.

Idempotent and resumable exactly like ``run_dev_e0.py``: a ``status.json`` marked
``complete`` exits 0; a ``resume.pt`` continues from its episode boundary after
checking the whole fingerprint.  Evaluation is read ONCE, at the final episode.

``--construct-only`` builds everything -- config, seeds, trainer, teacher, reference
trajectory -- asserts the seed contract on every generator the trainer created, and
exits WITHOUT training, evaluating, resetting an environment or writing a run
directory.  It is how the harness is preflighted without touching a formal episode.

Usage::

    run_s1.py --arm 1 --seed-index 0 --root DIR --calibration FILE
              [--episodes 1000] [--stop-after N] [--construct-only]
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
import s1_common as S

import torch

from mcrl.algorithms import cf_dev as cfd
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


def build_trainer(record, calib, arm: int, k: int, episodes: int, eval_episodes: int,
                  factory):
    """Construct one S1 arm's trainer.  No reset, no step, no optimizer."""
    spec = S.ARMS[int(arm)]
    config = S.s1_config(record, arm, episodes)
    train_seed, env_seed, mob_seed = S.s1_triple(k)
    env = factory()
    if spec.kind == "modqn":
        from mcrl.algorithms.modqn import MODQNTrainer
        trainer = MODQNTrainer(env, config, train_seed=train_seed, env_seed=env_seed,
                               mobility_seed=mob_seed, device="cpu")
        return trainer, config, None, None, None
    settings = S.s1_cf_settings(calib)
    if abs(settings.eta0 - S.ETA0_EXPECTED) > 1e-6:
        raise SystemExit(f"eta_0 {settings.eta0} is not the declared {S.ETA0_EXPECTED}")
    dev = S.s1_dev_settings(arm, k, eval_episodes=eval_episodes)
    xep_ref = D.load_xep_reference() if dev.mechanism == "D3-XEP" else None
    trainer = cfd.CFDevTrainer(env, config, settings, dev, env_factory=factory,
                               train_seed=train_seed, env_seed=env_seed,
                               mobility_seed=mob_seed, xep_reference=xep_ref)
    return trainer, config, settings, dev, xep_ref


def trainer_streams(trainer) -> dict[str, int | list[int]]:
    """Every integer seed this trainer derived, for the seed-isolation check."""
    out: dict[str, int | list[int]] = {
        "train": int(trainer.train_seed),
        "env": int(trainer.env_seed),
        "mobility": int(trainer.mobility_seed),
        "penalty_torch": int(trainer.train_seed) + 90_211,
    }
    if hasattr(trainer, "_catfish_rng"):
        out["catfish_sampling"] = int(trainer.train_seed) + 70_001
    return out


def assert_seed_isolation(trainer, dev) -> dict:
    """Fail closed unless every stream this run builds is in the S1 whitelist."""
    streams = trainer_streams(trainer)
    for name, seed in streams.items():
        cfd.assert_s1_seed(seed, f"S1 derived stream {name}")
    if dev is not None and dev.null_key is not None:
        cfd.assert_s1_null_key(dev.null_key, "S1-NULL key")
    if dev is not None:
        cfd.assert_lane_seed_pairs(
            [(dev.devval_env_base, dev.devval_mobility_base)],
            "S1 evaluation bases", lane=cfd.S1_LANE,
        )
    return streams


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", type=int, choices=sorted(S.ARMS), required=True)
    ap.add_argument("--seed-index", type=int, choices=S.SEED_INDICES, required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--episodes", type=int, default=S.EPISODES)
    ap.add_argument("--eval-episodes", type=int, default=S.N_EVAL)
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--construct-only", action="store_true",
                    help="build and check, train nothing, write nothing")
    ap.add_argument("--rss-cap-gb", type=float, default=4.5)
    a = ap.parse_args()

    torch.set_num_threads(1)
    tle_sha = S.assert_environment()
    arm, k = int(a.arm), int(a.seed_index)
    spec = S.ARMS[arm]
    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    code = S.code_manifest()
    code_digest = S.manifest_digest(code)
    episodes, n_eval = int(a.episodes), int(a.eval_episodes)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    cfg_payload = S.arm_config_payload(record, calib, arm, k, episodes=episodes,
                                       eval_episodes=n_eval,
                                       calibration_sha256=calib_sha)
    cfg_hash = S.config_hash(cfg_payload)
    factory = C.env_factory()

    if a.construct_only:
        trainer, config, settings, dev, xep_ref = build_trainer(
            record, calib, arm, k, episodes, n_eval, factory)
        streams = assert_seed_isolation(trainer, dev)
        print(json.dumps({
            "construct_only": True, "arm": arm, "arm_name": S.arm_name(arm),
            "kind": spec.kind, "seed_index": k, "episodes": episodes,
            "config_hash": cfg_hash, "code_digest": code_digest,
            "td_bootstrap_mode": config.td_bootstrap_mode,
            "discount_factor": config.discount_factor,
            "epsilon_decay_episodes": config.epsilon_decay_episodes,
            "derived_streams": streams,
            "eval_seeds_first_last": [list(S.eval_seeds(n_eval)[0]),
                                      list(S.eval_seeds(n_eval)[-1])],
            "null_key": (None if dev is None else dev.null_key),
            "xep_reference_sha256": (None if xep_ref is None else xep_ref.sha256),
            "tle_file_set_sha256": tle_sha,
        }, indent=2, default=str))
        return 0

    out = a.root / f"{S.arm_name(arm)}-k{k}"
    out.mkdir(parents=True, exist_ok=True)
    status_path, logs_path = out / "status.json", out / "episode-logs.json"
    resume_path, eval_path = out / "resume.pt", out / "evaluation.jsonl"
    if status_path.is_file():
        prev = json.loads(status_path.read_text())
        if prev.get("status") == "complete":
            print(f"[{S.arm_name(arm)} k{k}] already complete; nothing to do")
            return 0

    run_manifest_path = a.root / "S1-MANIFEST.json"
    if not run_manifest_path.is_file():
        raise SystemExit(f"no {run_manifest_path}; launch through scripts/s1_launch.py")
    run_manifest = json.loads(run_manifest_path.read_text())
    if (run_manifest.get("code") != code
            or run_manifest.get("calibration_sha256") != calib_sha
            or run_manifest.get("episodes") != episodes
            or run_manifest.get("arm_configs", {}).get(f"{arm}:{k}") != cfg_hash):
        raise SystemExit("S1-MANIFEST.json does not match this code / calibration / "
                         "config; refusing to run (fail closed)")

    trainer, config, settings, dev, xep_ref = build_trainer(
        record, calib, arm, k, episodes, n_eval, factory)
    streams = assert_seed_isolation(trainer, dev)
    trainer.env.assert_ready_to_train()
    train_seed, env_seed, mob_seed = S.s1_triple(k)

    fingerprint = {
        "lane": cfd.S1_LANE, "arm": arm, "arm_name": S.arm_name(arm),
        "arm_label": spec.name, "kind": spec.kind, "mechanism": spec.mechanism,
        "credit_mode": (S.CREDIT_MODE if spec.kind == "cf" else None),
        "seed_index": k, "seeds": [train_seed, env_seed, mob_seed],
        "derived_streams": streams,
        "config": asdict(config),
        "settings": (None if settings is None else asdict(settings)),
        "dev_settings": (None if dev is None else asdict(dev)),
        "config_hash": cfg_hash, "calibration_sha256": calib_sha,
        "tle_file_set_sha256": tle_sha, "prereg_digest": record.digest,
        "code": code, "code_digest": code_digest,
    }
    if xep_ref is not None:
        fingerprint["xep_reference"] = xep_ref.identity()
    status = {
        "status": "running", "lane": cfd.S1_LANE, "arm": arm,
        "arm_name": S.arm_name(arm), "seed_index": k,
        "episodes_target": episodes, "pid": os.getpid(), "started_utc": utc(),
        "fingerprint": fingerprint, "tle_root": str(tp.resolve_tle_root()),
        "eval_at": list(S.eval_at(episodes)), "checkpoints": {},
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
        status["checkpoints"] = json.loads(status_path.read_text()).get("checkpoints", {}) \
            if status_path.is_file() else {}
        status["resumed_from_episode"] = start
        print(f"[{S.arm_name(arm)} k{k}] resuming at episode {start}", flush=True)
    C.write_json(status_path, status)
    t0 = time.time()

    def as_row(log):
        return log if isinstance(log, dict) else asdict(log)

    def save(episode_done: int) -> None:
        payload = {"schema": "s1-resume-v1", "next_episode": episode_done,
                   "fingerprint": fingerprint, "logs": logs,
                   "trainer_state": trainer.training_state_dict()}
        tmp = resume_path.with_suffix(".pt.tmp")
        torch.save(payload, tmp)
        tmp.replace(resume_path)
        pol = out / f"policy-ep{episode_done:05d}.pt"
        if spec.kind == "cf":
            trainer.save_policy(pol, episode_done - 1)
        else:
            trainer.save_checkpoint(pol, episode=episode_done - 1,
                                    checkpoint_kind=config.checkpoint_primary_report,
                                    logs=logs)
        C.write_json(logs_path, [as_row(x) for x in logs])
        status["checkpoints"][str(episode_done)] = {"path": str(pol),
                                                    "sha256": C.sha256_file(pol)}
        status.update(episodes_completed=episode_done, rss_gb=rss_gb(),
                      wall_s=time.time() - t0, updated_utc=utc())
        C.write_json(status_path, status)

    def evaluation_reading(episode_done: int) -> None:
        """The ONE formal evaluation read.  Greedy, fresh env per episode, no RNG."""
        if spec.kind == "cf":
            res = trainer.devval()
        else:
            policy = C.modqn_greedy(trainer)
            res = cfd.dev_rollout(
                lambda i: policy, env_factory=factory,
                encode=lambda states, t: trainer.encode_states(states),
                seeds=S.eval_seeds(n_eval), t0_agreement=True, lane=cfd.S1_LANE)
        full = dict(res, episode=episode_done, lane=cfd.S1_LANE, arm=arm,
                    arm_name=S.arm_name(arm), arm_label=spec.name, kind=spec.kind,
                    mechanism=spec.mechanism, seed_index=k, config_hash=cfg_hash,
                    eval_seeds=[list(x) for x in S.eval_seeds(n_eval)],
                    set="S1-FORMAL-EVALUATION",
                    tle_file_set_sha256=tle_sha, utc=utc())
        C.write_json(out / f"evaluation-ep{episode_done:05d}.json", full)
        row = {kk: vv for kk, vv in full.items()
               if kk not in ("episodes", "ee_ep", "eval_seeds")}
        with open(eval_path, "a") as f:
            f.write(json.dumps(row, default=str) + "\n")
        print(f"[{S.arm_name(arm)} k{k}] EVAL ep {episode_done}: ee={res['ee']:.6e} "
              f"served={res['served']:.5f} agreeT0={res['t0_agreement']:.4f}", flush=True)

    reads = set(S.eval_at(episodes))

    def on_episode(log) -> None:
        row = as_row(log)
        episode_done = int(row["episode"]) + 1
        if rss_gb() > a.rss_cap_gb:
            raise MemoryError(f"RSS {rss_gb():.2f} GB > cap {a.rss_cap_gb}")
        if episode_done in reads:
            evaluation_reading(episode_done)
        if (episode_done % S.CHECKPOINT_EVERY == 0 or episode_done == episodes
                or episode_done == a.stop_after):
            save(episode_done)
            print(f"[{S.arm_name(arm)} k{k}] ep {episode_done} saved; "
                  f"rss {rss_gb():.2f} GB; wall {time.time() - t0:.0f}s", flush=True)
        if a.stop_after is not None and episode_done >= a.stop_after:
            raise StopAfter

    def cb(log):
        logs.append(log)
        on_episode(log)

    try:
        if spec.kind == "cf":
            trainer.train_cf(start_episode=start, initial_logs=list(logs),
                             episode_callback=cb, progress_every=50)
        else:
            trainer.train(progress_every=50, start_episode=start,
                          initial_logs=list(logs), episode_callback=cb)
    except StopAfter:
        status.update(status="stopped-at", stopped_at=a.stop_after, stopped_utc=utc())
        C.write_json(status_path, status)
        print(f"[{S.arm_name(arm)} k{k}] stopped cleanly at {a.stop_after}", flush=True)
        return 0
    except Exception as err:
        status.update(status="failed", error_type=type(err).__name__, error=str(err),
                      failed_utc=utc())
        C.write_json(status_path, status)
        raise

    C.write_json(logs_path, [as_row(x) for x in logs])
    status.update(status="complete", episodes_completed=len(logs), finished_utc=utc(),
                  wall_s=time.time() - t0,
                  final_policy=str(out / f"policy-ep{episodes:05d}.pt"),
                  masking_diagnostics=trainer.get_masking_diagnostics())
    C.write_json(status_path, status)
    print(f"[{S.arm_name(arm)} k{k}] complete: {len(logs)} episodes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
