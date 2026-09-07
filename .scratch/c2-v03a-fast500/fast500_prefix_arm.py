#!/usr/bin/env python3
"""Run one exact EP500 treatment prefix from a frozen 1500-EP authority.

This is a preliminary scheduling seam, not a new algorithm configuration.  It
keeps the validated 1500-episode trainer and loop configuration byte-for-byte
identical and stops the treatment loop at the absolute EP500 boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TREND_DIR = REPO / ".scratch" / "c2-v03a-trend"
for path in (HERE, TREND_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import c2_v03a_trend_arm as trend_arm  # noqa: E402
import r7_500_checkpoint as checkpoint_tools  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-fast500-prefix-arm-v1"
CLAIM_CEILING = (
    "ONE_SEED_EP500_PRELIMINARY_TREND_NOT_CHAPTER5_NOT_FORMAL_EFFICACY_"
    "NOT_DEPLOYMENT_NOT_AUCTION_NOT_COORDINATION"
)
PREFIX_EPISODES = 500
SOURCE_EPISODES = 1500
ALLOWED_ARMS = ("A011", "A101", "A110")


class Fast500PrefixError(RuntimeError):
    """Raised before publishing a noncanonical or incomplete EP500 prefix."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _assert_digest(value: str, *, field: str) -> str:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise Fast500PrefixError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _canonical_inputs(
    *, authority_path: Path, tle_root: Path
) -> tuple[dict[str, Any], Any, Any, Path]:
    validated = trend_arm.load_and_validate_authority(
        authority_path, tle_root=tle_root
    )
    if validated.get("episodes") != SOURCE_EPISODES:
        raise Fast500PrefixError("source authority must retain the 1500-episode schedule")
    prereg_path = trend_arm._repo_file(
        validated["canonical_prereg"], field="canonical_prereg"
    )
    c1_manifest = trend_arm._repo_file(
        validated["c1_exp_corpus_manifest"], field="c1_exp_corpus_manifest"
    )
    prereg, archive, runtime_authority = trend_arm.legacy._canonical_ephemeris_authority(
        prereg_path, tle_root
    )
    if runtime_authority.get("tle_file_set_sha256") != validated["tle_file_set_sha256"]:
        raise Fast500PrefixError("runtime TLE SHA drifted after authority validation")
    if runtime_authority.get("tle_file_count") != validated["tle_file_count"]:
        raise Fast500PrefixError("runtime TLE file count drifted after authority validation")
    return validated, prereg, archive, c1_manifest


def execute_prefix(
    *,
    authority_path: Path,
    expected_authority_sha256: str,
    expected_runner_sha256: str,
    arm: str,
    output_dir: Path,
    tle_root: Path,
) -> dict[str, Any]:
    """Run one fresh treatment arm and stop cleanly at absolute EP500."""

    runner_path = Path(__file__).resolve()
    authority_path = Path(authority_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    expected_authority_sha256 = _assert_digest(
        expected_authority_sha256, field="expected_authority_sha256"
    )
    expected_runner_sha256 = _assert_digest(
        expected_runner_sha256, field="expected_runner_sha256"
    )
    if sha256_file(runner_path) != expected_runner_sha256:
        raise Fast500PrefixError("fast500 runner SHA drifted")
    if sha256_file(authority_path) != expected_authority_sha256:
        raise Fast500PrefixError("source authority SHA drifted")
    if arm not in ALLOWED_ARMS:
        raise Fast500PrefixError("fast500 prefix runner accepts treatment ablations only")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite prefix output: {output_dir}")

    validated, prereg, archive, c1_manifest = _canonical_inputs(
        authority_path=authority_path, tle_root=tle_root
    )
    if arm not in validated["arms"]:
        raise Fast500PrefixError("arm is absent from the frozen source authority")

    trainer_config = trend_arm.legacy._short_config(
        prereg,
        arm=arm,
        episodes=SOURCE_EPISODES,
        epsilon_decay_episodes=int(validated["epsilon_decay_episodes"]),
        target_update_every=int(validated["target_update_every"]),
        learning_rate=float(validated["learning_rate"]),
    )
    loop_config = trend_arm.c2_runner.C2EpisodeLoopConfig(
        arm=arm,
        episodes=SOURCE_EPISODES,
        users=int(validated["users"]),
        train_seed=int(validated["seeds"]["training"]),
        env_seed=int(validated["seeds"]["environment"]),
        mobility_seed=int(validated["seeds"]["mobility"]),
        checkpoint_every=int(validated["checkpoint_every_episodes"]),
        beta=float(validated["donor_beta"]),
        max_c2_candidates=int(validated["max_c2_candidates"]),
        acrm_eta=float(validated["acrm_eta"]),
    )
    result = trend_arm.c2_runner.run_c2_v03_episode_loop(
        config=loop_config,
        output_dir=output_dir,
        archive=archive,
        trainer_config=trainer_config,
        c1_corpus_manifest=c1_manifest,
        resume_state=None,
        stop_episode=PREFIX_EPISODES,
    )
    if result.get("episodes") != SOURCE_EPISODES:
        raise Fast500PrefixError("runner changed the source training schedule")
    if result.get("episodes_completed") != PREFIX_EPISODES:
        raise Fast500PrefixError("runner did not stop at exact EP500")
    if result.get("checkpoint_every_episodes") != 100:
        raise Fast500PrefixError("checkpoint cadence drifted from 100 episodes")
    if result.get("artifact_scope") not in {
        "bounded_initial_segment",
        "resume_segment_only",
    }:
        raise Fast500PrefixError("runner returned an invalid prefix artifact scope")

    checkpoint_path = output_dir / "checkpoints" / "ep-000500-main.pt"
    if not checkpoint_path.is_file():
        raise Fast500PrefixError("exact EP500 periodic Main checkpoint is missing")
    rows = result.get("periodic_checkpoints")
    matching_rows = [
        row
        for row in rows
        if isinstance(rows, list)
        and isinstance(row, Mapping)
        and row.get("episodes_completed") == PREFIX_EPISODES
    ] if isinstance(rows, list) else []
    if len(matching_rows) != 1:
        raise Fast500PrefixError("result lacks exactly one EP500 checkpoint receipt")
    checkpoint_sha256 = sha256_file(checkpoint_path)
    if matching_rows[0].get("sha256") != checkpoint_sha256:
        raise Fast500PrefixError("EP500 checkpoint receipt SHA drifted")

    canonical_trainer_config = trend_arm.c2_runner._canonical_trainer_config(
        trainer_config, field="trainer_config"
    )
    payload = trend_arm.legacy.read_checkpoint(checkpoint_path, map_location="cpu")
    checkpoint_identity = checkpoint_tools.validate_checkpoint_payload(
        payload,
        validated=validated,
        trainer_config=canonical_trainer_config,
        episode_index=PREFIX_EPISODES - 1,
        checkpoint_kind="periodic-main-policy-trend",
        label=f"lr={validated['learning_rate']} {arm} EP500",
    )
    status = {
        "schema": SCHEMA,
        "status": "complete",
        "claim_ceiling": CLAIM_CEILING,
        "formal_training_authorized": False,
        "arm": arm,
        "learning_rate": float(validated["learning_rate"]),
        "source_schedule_episodes": SOURCE_EPISODES,
        "prefix_episodes_completed": PREFIX_EPISODES,
        "checkpoint_every_episodes": 100,
        "authority": str(authority_path),
        "authority_sha256": expected_authority_sha256,
        "runner": str(runner_path),
        "runner_sha256": expected_runner_sha256,
        "resume_source": None,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_identity": checkpoint_identity,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
        },
    }
    _write_json(output_dir / "prefix-status.json", status)
    return status


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--expected-authority-sha256", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--arm", choices=ALLOWED_ARMS, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    status = execute_prefix(
        authority_path=args.authority,
        expected_authority_sha256=args.expected_authority_sha256,
        expected_runner_sha256=args.expected_runner_sha256,
        arm=args.arm,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
    )
    print(status["checkpoint"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
