#!/usr/bin/env python3
"""Run one authority-bound C2 V0.3A intermediate-trend arm."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
C2_DIR = REPO / ".scratch" / "c2-v03"
LEGACY_DIR = REPO / ".scratch" / "smc-er-short-ep"
for path in (HERE, C2_DIR, LEGACY_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_temporal_fork_episode_runner as c2_runner  # noqa: E402
import run_short_ep as legacy  # noqa: E402
from c2_v03a_trend_authority import (  # noqa: E402
    ALLOWED_ARMS,
    C1_ROUTE_STATUS,
    C2_ROUTE_STATUS,
    C3_ROUTE_STATUS,
    CLAIM_CEILING,
    validate_v03a_trend_authority,
)


STATUS_SCHEMA = "multi-catfish-mcrl-c2-v03a-trend-arm-v1"
THROUGHPUT_SMOKE_MAX_EPISODES = 24


class V03ATrendArmError(RuntimeError):
    """Raised before training when the requested arm drifts from authority."""


def _execution_controls(
    *,
    arm: str,
    stop_after_episodes: int | None,
    checkpoint_every_override: int | None,
    resume_state: Path | None,
) -> None:
    """Validate controls that may alter execution but never the frozen schedule."""

    if stop_after_episodes is not None and (
        type(stop_after_episodes) is not int
        or stop_after_episodes < 1
        or stop_after_episodes > THROUGHPUT_SMOKE_MAX_EPISODES
    ):
        raise V03ATrendArmError(
            "throughput smoke must stop at 1..24 absolute episodes"
        )
    if checkpoint_every_override is not None:
        if stop_after_episodes is None:
            raise V03ATrendArmError(
                "checkpoint override is permitted only for a bounded throughput smoke"
            )
        if (
            type(checkpoint_every_override) is not int
            or checkpoint_every_override < 1
            or checkpoint_every_override > stop_after_episodes
        ):
            raise V03ATrendArmError(
                "smoke checkpoint override must be in 1..stop-after-episodes"
            )
    if resume_state is not None and arm == "B000":
        raise V03ATrendArmError(
            "this V0.3A resume seam is treatment-only; restart B000 from its "
            "unchanged MODQN training state"
        )
    if resume_state is not None and stop_after_episodes is not None:
        raise V03ATrendArmError(
            "resume and bounded throughput smoke are separate execution modes"
        )


def _smoke_checkpoint_gate(
    *, output: Path, arm: str, result: Mapping[str, Any], expected_count: int
) -> dict[str, Any]:
    """Read back smoke checkpoint artifacts before declaring the path healthy."""

    periodic = result.get("periodic_checkpoints")
    if not isinstance(periodic, list) or len(periodic) != expected_count:
        raise V03ATrendArmError("smoke periodic checkpoint count mismatch")
    if result.get("periodic_checkpoint_count") != expected_count:
        raise V03ATrendArmError("smoke periodic checkpoint receipt mismatch")
    if any(row.get("load_round_trip") != "PASS" for row in periodic):
        raise V03ATrendArmError("smoke periodic Main checkpoint failed load round-trip")
    if arm == "B000":
        resume_path = output / "resume" / "latest-training-state.pt"
        try:
            payload = c2_runner._torch_load_runtime_state(resume_path)
        except Exception as error:
            raise V03ATrendArmError(
                f"baseline smoke resume state failed load round-trip: {error}"
            ) from error
        if not payload:
            raise V03ATrendArmError("baseline smoke resume state is empty")
        schema = payload.get("format_version")
    else:
        resume_path = output / "resume" / "latest-c2-v03-training-state.pt"
        try:
            payload = c2_runner._torch_load_runtime_state(resume_path)
        except Exception as error:
            raise V03ATrendArmError(
                f"C2 smoke resume state failed load round-trip: {error}"
            ) from error
        if payload.get("schema") != c2_runner.RUNTIME_STATE_SCHEMA:
            raise V03ATrendArmError("C2 smoke resume state schema drifted")
        schema = payload.get("schema")
    return {
        "status": "PASS",
        "periodic_checkpoint_count": expected_count,
        "resume_state": str(resume_path),
        "resume_state_sha256": c2_runner._sha256_file(resume_path),
        "resume_state_schema": schema,
        "load_round_trip": "PASS",
    }


def _read_object(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise V03ATrendArmError(f"trend authority is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise V03ATrendArmError("trend authority must be a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _repo_file(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise V03ATrendArmError(f"validated authority lacks {field}")
    raw = Path(value).expanduser()
    path = raw.resolve() if raw.is_absolute() else (REPO / raw).resolve()
    if not path.is_file():
        raise V03ATrendArmError(f"validated {field} is missing: {path}")
    return path


def load_and_validate_authority(
    authority_path: Path, *, tle_root: Path
) -> dict[str, Any]:
    path = Path(authority_path).expanduser().resolve()
    request = _read_object(path)
    try:
        return validate_v03a_trend_authority(
            request,
            repo=REPO,
            tle_root=Path(tle_root).expanduser().resolve(),
        )
    except Exception as error:
        raise V03ATrendArmError(f"C2 V0.3A trend authority rejected: {error}") from error


def execute_arm(
    *,
    authority_path: Path,
    arm: str,
    output_dir: Path,
    tle_root: Path,
    stop_after_episodes: int | None = None,
    checkpoint_every_override: int | None = None,
    resume_state: Path | None = None,
) -> dict[str, Any]:
    """Execute one fresh arm or a bounded same-path throughput segment."""

    validated = load_and_validate_authority(authority_path, tle_root=tle_root)
    if arm not in ALLOWED_ARMS or arm not in validated["arms"]:
        raise V03ATrendArmError(f"arm is not in the exact five-arm authority: {arm}")
    _execution_controls(
        arm=arm,
        stop_after_episodes=stop_after_episodes,
        checkpoint_every_override=checkpoint_every_override,
        resume_state=resume_state,
    )

    prereg_path = _repo_file(validated["canonical_prereg"], field="canonical_prereg")
    c1_manifest = _repo_file(
        validated["c1_exp_corpus_manifest"], field="c1_exp_corpus_manifest"
    )
    prereg, archive, runtime_authority = legacy._canonical_ephemeris_authority(
        prereg_path, Path(tle_root).expanduser().resolve()
    )
    if runtime_authority.get("tle_file_set_sha256") != validated["tle_file_set_sha256"]:
        raise V03ATrendArmError("runtime TLE SHA drifted after authority validation")
    if runtime_authority.get("tle_file_count") != validated["tle_file_count"]:
        raise V03ATrendArmError("runtime TLE file count drifted after validation")

    episodes = int(validated["episodes"])
    trainer_config = legacy._short_config(
        prereg,
        arm=arm,
        episodes=episodes,
        epsilon_decay_episodes=int(validated["epsilon_decay_episodes"]),
        target_update_every=int(validated["target_update_every"]),
        learning_rate=float(validated["learning_rate"]),
    )
    if arm == "B000" and stop_after_episodes is not None:
        trainer_config = replace(trainer_config, episodes=stop_after_episodes)
    checkpoint_every = (
        int(validated["checkpoint_every_episodes"])
        if checkpoint_every_override is None
        else checkpoint_every_override
    )
    loop_config = c2_runner.C2EpisodeLoopConfig(
        arm=arm,
        episodes=episodes,
        users=int(validated["users"]),
        train_seed=int(validated["seeds"]["training"]),
        env_seed=int(validated["seeds"]["environment"]),
        mobility_seed=int(validated["seeds"]["mobility"]),
        checkpoint_every=checkpoint_every,
        beta=float(validated["donor_beta"]),
        max_c2_candidates=int(validated["max_c2_candidates"]),
        acrm_eta=float(validated["acrm_eta"]),
    )
    output = Path(output_dir).expanduser().resolve()
    result = c2_runner.run_c2_v03_episode_loop(
        config=loop_config,
        output_dir=output,
        archive=archive,
        trainer_config=trainer_config,
        c1_corpus_manifest=None if arm == "B000" else c1_manifest,
        resume_state=resume_state,
        stop_episode=(None if arm == "B000" else stop_after_episodes),
    )
    smoke_checkpoint_gate = None
    if stop_after_episodes is not None and checkpoint_every_override is not None:
        smoke_checkpoint_gate = _smoke_checkpoint_gate(
            output=output,
            arm=arm,
            result=result,
            expected_count=stop_after_episodes // checkpoint_every,
        )
    output.mkdir(parents=True, exist_ok=True)
    status = {
        "schema": STATUS_SCHEMA,
        "status": "complete",
        "run_mode": (
            "authority_path_throughput_smoke"
            if stop_after_episodes is not None
            else "resume_intermediate_trend"
            if resume_state is not None
            else "fresh_intermediate_trend"
        ),
        "arm": arm,
        "label": c2_runner.ARM_LABELS[arm],
        "episodes_planned": episodes,
        "episodes_executed": int(
            result.get("episodes_executed", result.get("episodes", episodes))
        ),
        "users": int(validated["users"]),
        "seeds": dict(validated["seeds"]),
        "loop_config": asdict(loop_config),
        "trainer_config": c2_runner._canonical_trainer_config(
            trainer_config, field="trainer_config"
        ),
        "authority_path": str(Path(authority_path).expanduser().resolve()),
        "authority": validated,
        "runtime_authority": runtime_authority,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
        },
        "c3_route_status": C3_ROUTE_STATUS,
        "role_route_status": {
            "C1": C1_ROUTE_STATUS,
            "C2": C2_ROUTE_STATUS,
            "C3": C3_ROUTE_STATUS,
        },
        "formal_training_authorized": False,
        "result": result,
        "smoke_checkpoint_gate": smoke_checkpoint_gate,
        "claim_ceiling": CLAIM_CEILING,
    }
    _write_json(output / "status.json", status)
    return status


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--arm", choices=ALLOWED_ARMS, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    parser.add_argument("--stop-after-episodes", type=int)
    parser.add_argument("--checkpoint-every-override", type=int)
    parser.add_argument("--resume-state", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    status = execute_arm(
        authority_path=args.authority,
        arm=args.arm,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
        stop_after_episodes=args.stop_after_episodes,
        checkpoint_every_override=args.checkpoint_every_override,
        resume_state=args.resume_state,
    )
    print(Path(args.output_dir).expanduser().resolve() / "status.json")
    if status.get("status") != "complete":  # pragma: no cover - fail-closed guard
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
