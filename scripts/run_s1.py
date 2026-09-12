"""S1 formal screen driver, MC2 round (one cell, one seed index).

**FORMAL LANE (Amendment 13).**  This spends the formal evaluation episodes
``9_111_000+i / 9_112_000+i``.  It trains on the ``S1-TRAIN`` triple; the optional
``D3-null`` draws from ``S1-NULL = (9_261_000, k)`` and the MC2 ``B-null`` from
``S1-NULL-MC2 = (9_263_000, k)``; no development stream is reused.  ``D3-XEP``, if
the controller included it, keeps the sealed DEV-NULL reference trajectory of
Amendment 12.

Idempotent and resumable exactly like ``run_dev_e0.py``: a ``status.json`` marked
``complete`` exits 0; a ``resume.pt`` continues from its episode boundary after
checking the whole fingerprint.  Evaluation is read ONCE, at the final episode, and
the read runs with every Catfish source unregistered and the judge disabled, so the
number that is published is the deployed rule and provably nothing else.

``--construct-only`` builds everything -- config, seeds, trainer, teacher, judge,
reference trajectory -- asserts the seed contract on every generator the trainer
created, and exits WITHOUT training, evaluating, resetting an environment or writing a
run directory.

``--preflight-dev`` runs this SAME code path in the DEVELOPMENT lane: the DEV training
triple, DEVVAL evaluation, the development null streams, at most
``PREFLIGHT_MAX_EPISODES`` episodes, into its own ``S1-PREFLIGHT-MANIFEST.json`` root.
It is how the formal driver is exercised end to end without touching a formal episode
-- the development seed guard refuses every formal, calibration and CONFIRM value on
that path, and the lane is inside the configuration hash, so a preflight
configuration can never hash to a formal one.

Usage::

    run_s1.py --cell FULL --seed-index 0 --root DIR --calibration FILE
              --mechanism-id MC2-JGO-v1 [--optional D3-null,D3-XEP]
              [--episodes 1000] [--stop-after N] [--construct-only] [--preflight-dev]
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
import s1_common as S

import torch

from mcrl.algorithms import cf_dev as cfd
from mcrl.algorithms import cf_s1 as cfs1
from mcrl.runtime import training_pipeline as tp

FORMAL_MANIFEST = "S1-MANIFEST.json"
PREFLIGHT_MANIFEST = "S1-PREFLIGHT-MANIFEST.json"
PREFLIGHT_MAX_EPISODES = 20
"""The preflight is a wiring check, not a result: it may not train longer than this."""


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


def parse_optional(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(x for x in (p.strip() for p in raw.split(",")) if x)


def register_sources(spec) -> tuple[str, ...]:
    """Register the candidate teacher sources this cell's judge will ask for."""
    if not spec.is_judge or "B" not in spec.sources:
        return ()
    from mcrl.algorithms import cf_multi_sources as cfmulti

    return cfmulti.register_candidate_sources(replace=True)


def build_trainer(record, calib, mechanism_id, name, k, episodes, eval_episodes,
                  factory, *, lane: str, optional: tuple[str, ...]):
    """Construct one S1 cell's trainer.  No reset, no step, no optimizer."""
    spec = S.cell(mechanism_id, name, optional=optional)
    config = S.s1_config(record, spec, episodes)
    train_seed, env_seed, mob_seed = S.train_triple(k, lane=lane)
    env = factory()
    if spec.kind == "modqn":
        from mcrl.algorithms.modqn import MODQNTrainer
        cfd.assert_lane_seed(train_seed, f"{lane} MODQN train seed", lane=lane)
        cfd.assert_lane_seed(env_seed, f"{lane} MODQN env seed", lane=lane)
        cfd.assert_lane_seed(mob_seed, f"{lane} MODQN mobility seed", lane=lane)
        trainer = MODQNTrainer(env, config, train_seed=train_seed, env_seed=env_seed,
                               mobility_seed=mob_seed, device="cpu")
        return trainer, config, None, None, None, None
    settings = S.s1_cf_settings(calib)
    if abs(settings.eta0 - S.ETA0_EXPECTED) > 1e-6:
        raise SystemExit(f"eta_0 {settings.eta0} is not the declared {S.ETA0_EXPECTED}")
    dev = S.s1_dev_settings(mechanism_id, name, k, eval_episodes=eval_episodes,
                            lane=lane, optional=optional)
    xep_ref = S.load_xep_reference() if dev.is_xep else None
    register_sources(spec)
    jspec = S.judge_spec(mechanism_id, name, k, lane=lane, optional=optional)
    kw = {} if jspec is None else {"judge": jspec}
    trainer = cfs1.S1Trainer(env, config, settings, dev, env_factory=factory,
                             train_seed=train_seed, env_seed=env_seed,
                             mobility_seed=mob_seed, xep_reference=xep_ref, **kw)
    return trainer, config, settings, dev, jspec, xep_ref


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


def assert_seed_isolation(trainer, dev, jspec, *, lane: str) -> dict:
    """Fail closed unless every stream this run builds is in the lane's whitelist."""
    streams = trainer_streams(trainer)
    for name, seed in streams.items():
        cfd.assert_lane_seed(seed, f"{lane} derived stream {name}", lane=lane)
    if dev is not None and dev.null_key is not None:
        cfd.assert_lane_seed(dev.null_key, f"{lane} matched-null key", lane=lane)
    if jspec is not None and getattr(jspec, "null_key", None) is not None:
        cfd.assert_lane_seed(jspec.null_key, f"{lane} MC2 B-null key", lane=lane)
    if dev is not None:
        cfd.assert_lane_seed_pairs(
            [(dev.devval_env_base, dev.devval_mobility_base)],
            f"{lane} evaluation bases", lane=lane,
        )
    # The generators the trainer actually holds, not only the declared values.
    for attr in ("_null_rng", "_judge_null_rng"):
        rng = getattr(trainer, attr, None)
        if rng is not None:
            streams[attr] = str(rng.bit_generator.state["bit_generator"])
    return streams


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell", required=True)
    ap.add_argument("--seed-index", type=int, choices=S.SEED_INDICES, required=True)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--calibration", type=Path, required=True)
    ap.add_argument("--mechanism-id", required=True, choices=S.MECHANISM_IDS)
    ap.add_argument("--optional", default=None,
                    help="the OPTIONAL cells the controller included at freeze, "
                         "comma separated (D3-null,D3-XEP)")
    ap.add_argument("--episodes", type=int, default=S.EPISODES)
    ap.add_argument("--eval-episodes", type=int, default=S.N_EVAL)
    ap.add_argument("--stop-after", type=int, default=None)
    ap.add_argument("--construct-only", action="store_true",
                    help="build and check, train nothing, write nothing")
    ap.add_argument("--preflight-dev", action="store_true",
                    help="run this code path in the DEVELOPMENT lane (DEV triple, "
                         f"DEVVAL, development nulls, <= {PREFLIGHT_MAX_EPISODES} "
                         "episodes); no formal episode is constructed")
    ap.add_argument("--rss-cap-gb", type=float, default=4.5)
    a = ap.parse_args()

    torch.set_num_threads(1)
    tle_sha = S.assert_environment()
    lane = S.DEV_LANE if a.preflight_dev else S.S1_LANE
    optional = parse_optional(a.optional)
    mid, name, k = a.mechanism_id, a.cell, int(a.seed_index)
    spec = S.cell(mid, name, optional=optional)
    episodes, n_eval = int(a.episodes), int(a.eval_episodes)
    if a.preflight_dev and episodes > PREFLIGHT_MAX_EPISODES:
        raise SystemExit(
            f"--preflight-dev trains at most {PREFLIGHT_MAX_EPISODES} episodes "
            f"(asked for {episodes}); it is a wiring check, not a result"
        )
    if not a.preflight_dev and episodes != S.EPISODES:
        raise SystemExit(
            f"the frozen S1 depth is {S.EPISODES} episodes (Amendment 13); "
            f"{episodes} would be a different declaration"
        )
    calib = json.loads(a.calibration.read_text())
    calib_sha = C.sha256_file(a.calibration)
    code = S.code_manifest()
    code_digest = S.manifest_digest(code)
    record = tp.read_prereg(tp.CANONICAL_PREREG)
    cfg_payload = S.cell_config_payload(
        record, calib, mid, name, k, episodes=episodes, eval_episodes=n_eval,
        calibration_sha256=calib_sha, lane=lane, optional=optional)
    cfg_hash = S.config_hash(cfg_payload)
    factory = C.env_factory()
    run_id = S.run_name(mid, name, optional=optional)

    if a.construct_only:
        trainer, config, settings, dev, jspec, xep_ref = build_trainer(
            record, calib, mid, name, k, episodes, n_eval, factory,
            lane=lane, optional=optional)
        streams = assert_seed_isolation(trainer, dev, jspec, lane=lane)
        print(json.dumps({
            "construct_only": True, "lane": lane, "mechanism_id": mid,
            "cell": name, "run_name": run_id, "kind": spec.kind, "seed_index": k,
            "episodes": episodes, "config_hash": cfg_hash, "code_digest": code_digest,
            "td_bootstrap_mode": config.td_bootstrap_mode,
            "discount_factor": config.discount_factor,
            "epsilon_decay_episodes": config.epsilon_decay_episodes,
            "derived_streams": streams,
            "eval_seeds_first_last": [list(S.eval_seeds(n_eval, lane=lane)[0]),
                                      list(S.eval_seeds(n_eval, lane=lane)[-1])],
            "null_key": (None if dev is None else dev.null_key),
            "judge_spec": (None if jspec is None else asdict(jspec)),
            "xep_reference_sha256": (None if xep_ref is None else xep_ref.sha256),
            "tle_file_set_sha256": tle_sha,
        }, indent=2, default=str))
        return 0

    out = a.root / f"{run_id}-k{k}"
    out.mkdir(parents=True, exist_ok=True)
    status_path, logs_path = out / "status.json", out / "episode-logs.json"
    resume_path, eval_path = out / "resume.pt", out / "evaluation.jsonl"
    if status_path.is_file():
        prev = json.loads(status_path.read_text())
        if prev.get("status") == "complete":
            print(f"[{run_id} k{k}] already complete; nothing to do")
            return 0

    manifest_name = PREFLIGHT_MANIFEST if a.preflight_dev else FORMAL_MANIFEST
    other_name = FORMAL_MANIFEST if a.preflight_dev else PREFLIGHT_MANIFEST
    if (a.root / other_name).is_file():
        raise SystemExit(
            f"{a.root} already holds a {other_name}: a preflight root and a formal "
            "root are never the same root (fail closed)"
        )
    run_manifest_path = a.root / manifest_name
    if not run_manifest_path.is_file():
        raise SystemExit(f"no {run_manifest_path}; launch through scripts/s1_launch.py")
    run_manifest = json.loads(run_manifest_path.read_text())
    if (run_manifest.get("code") != code
            or run_manifest.get("lane") != lane
            or run_manifest.get("mechanism_id") != mid
            or run_manifest.get("calibration_sha256") != calib_sha
            or run_manifest.get("episodes") != episodes
            or run_manifest.get("optional_cells_included", []) != list(optional)
            or run_manifest.get("arm_configs", {}).get(f"{name}:{k}") != cfg_hash):
        raise SystemExit(f"{manifest_name} does not match this code / calibration / "
                         "config; refusing to run (fail closed)")

    trainer, config, settings, dev, jspec, xep_ref = build_trainer(
        record, calib, mid, name, k, episodes, n_eval, factory,
        lane=lane, optional=optional)
    streams = assert_seed_isolation(trainer, dev, jspec, lane=lane)
    trainer.env.assert_ready_to_train()
    train_seed, env_seed, mob_seed = S.train_triple(k, lane=lane)

    fingerprint = {
        "lane": lane, "mechanism_id": mid, "cell": name, "run_name": run_id,
        "cell_index": S.cell_index(mid, name, optional=optional),
        "kind": spec.kind, "role": spec.role,
        "mechanism": cfg_payload["mechanism"],
        "credit_mode": cfg_payload["credit_mode"],
        "seed_index": k, "seeds": [train_seed, env_seed, mob_seed],
        "derived_streams": streams,
        "config": asdict(config),
        "settings": (None if settings is None else asdict(settings)),
        "dev_settings": (None if dev is None else asdict(dev)),
        "judge_spec": (None if jspec is None else asdict(jspec)),
        "config_hash": cfg_hash, "calibration_sha256": calib_sha,
        "tle_file_set_sha256": tle_sha, "prereg_digest": record.digest,
        "code": code, "code_digest": code_digest,
    }
    if xep_ref is not None:
        fingerprint["xep_reference"] = xep_ref.identity()
    status = {
        "status": "running", "lane": lane, "mechanism_id": mid, "cell": name,
        "run_name": run_id, "seed_index": k,
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
        status["checkpoints"] = (
            json.loads(status_path.read_text()).get("checkpoints", {})
            if status_path.is_file() else {})
        status["resumed_from_episode"] = start
        print(f"[{run_id} k{k}] resuming at episode {start}", flush=True)
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
        if spec.kind == "modqn":
            trainer.save_checkpoint(pol, episode=episode_done - 1,
                                    checkpoint_kind=config.checkpoint_primary_report,
                                    logs=logs)
        else:
            trainer.save_policy(pol, episode_done - 1)
        C.write_json(logs_path, [as_row(x) for x in logs])
        status["checkpoints"][str(episode_done)] = {"path": str(pol),
                                                    "sha256": C.sha256_file(pol)}
        status.update(episodes_completed=episode_done, rss_gb=rss_gb(),
                      wall_s=time.time() - t0, updated_utc=utc())
        C.write_json(status_path, status)

    def evaluation_reading(episode_done: int) -> None:
        """The ONE evaluation read.  Greedy deployed rule, fresh env per episode.

        Every Catfish source is unregistered and the judge is disabled for the whole
        read: the published number is the masked argmax of the three Q networks at the
        frozen eta, and a read that asked a specialist or the judge for anything would
        raise here instead of answering.
        """
        with cfs1.sources_unregistered(), cfs1.judge_disabled():
            if spec.kind == "modqn":
                policy = C.modqn_greedy(trainer)
                res = cfd.dev_rollout(
                    lambda i: policy, env_factory=factory,
                    encode=lambda states, t: trainer.encode_states(states),
                    seeds=S.eval_seeds(n_eval, lane=lane), t0_agreement=True,
                    lane=lane)
            else:
                res = trainer.devval()
        full = dict(res, episode=episode_done, lane=lane, mechanism_id=mid,
                    cell=name, run_name=run_id, kind=spec.kind,
                    mechanism=cfg_payload["mechanism"], role=spec.role,
                    seed_index=k, config_hash=cfg_hash,
                    eval_seeds=[list(x) for x in S.eval_seeds(n_eval, lane=lane)],
                    set=("S1-FORMAL-EVALUATION" if lane == S.S1_LANE
                         else "PREFLIGHT-DEVVAL (not evidence)"),
                    deployment="masked argmax of the three Q networks at eta_0; "
                               "sources unregistered and judge disabled for this read",
                    tle_file_set_sha256=tle_sha, utc=utc())
        C.write_json(out / f"evaluation-ep{episode_done:05d}.json", full)
        row = {kk: vv for kk, vv in full.items()
               if kk not in ("episodes", "ee_ep", "eval_seeds")}
        with open(eval_path, "a") as f:
            f.write(json.dumps(row, default=str) + "\n")
        print(f"[{run_id} k{k}] EVAL ep {episode_done}: ee={res['ee']:.6e} "
              f"served={res['served']:.5f} agreeT0={res['t0_agreement']:.4f}",
              flush=True)

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
            print(f"[{run_id} k{k}] ep {episode_done} saved; "
                  f"rss {rss_gb():.2f} GB; wall {time.time() - t0:.0f}s", flush=True)
        if a.stop_after is not None and episode_done >= a.stop_after:
            raise StopAfter

    def cb(log):
        logs.append(log)
        on_episode(log)

    try:
        if spec.kind == "modqn":
            trainer.train(progress_every=50, start_episode=start,
                          initial_logs=list(logs), episode_callback=cb)
        else:
            trainer.train_cf(start_episode=start, initial_logs=list(logs),
                             episode_callback=cb, progress_every=50)
    except StopAfter:
        status.update(status="stopped-at", stopped_at=a.stop_after, stopped_utc=utc())
        C.write_json(status_path, status)
        print(f"[{run_id} k{k}] stopped cleanly at {a.stop_after}", flush=True)
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
    print(f"[{run_id} k{k}] complete: {len(logs)} episodes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
