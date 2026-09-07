#!/usr/bin/env python3
"""Run one authority-derived arm of the independent 100EP pilot.

This adapter intentionally exposes no knobs for episode count, learning rate,
seeds, schedules, or Catfish routing.  Those values are derived only from the
validated pilot authority.  The frozen training kernel remains
``run_short_ep.py``; this module is a narrow authority-to-kernel adapter.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run_short_ep as frozen  # noqa: E402
from pilot100_authority import (  # noqa: E402
    CANONICAL_AUTHORITY_RELATIVE,
    CLAIM_CEILING,
    PILOT_EPISODES,
    PILOT_OUTPUT_RELATIVE,
    validate_pilot100_authority,
)


SCHEMA = "multi-catfish-mcrl-pilot100-one-arm-v1"


class Pilot100ArmError(RuntimeError):
    """Raised when a pilot arm fails before or during bounded execution."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Pilot100ArmError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise Pilot100ArmError(f"{label} must be a JSON object: {path}")
    return value


def load_and_validate_authority(path: Path, *, tle_root: Path) -> dict[str, Any]:
    authority_path = Path(path).expanduser().resolve()
    canonical = (REPO / CANONICAL_AUTHORITY_RELATIVE).resolve()
    if authority_path != canonical:
        raise Pilot100ArmError(
            f"canonical pilot authority path required: {canonical}"
        )
    request = _read_object(authority_path, label="pilot100 authority")
    try:
        validated = validate_pilot100_authority(
            request,
            tle_root=Path(tle_root).expanduser().resolve(),
            repo=REPO,
        )
    except Exception as error:
        raise Pilot100ArmError(f"pilot100 authority rejected: {error}") from error
    if validated.get("status") != "PASS":
        raise Pilot100ArmError("pilot100 authority validator did not return PASS")
    return dict(validated)


def _gate_ledger(arm: str) -> frozen.GateLedger:
    if arm == "B000":
        return frozen.GateLedger()
    active = frozen.ARM_ACTIVE_SOURCES[arm]
    return frozen.GateLedger(
        **{
            source: "route" if source in active else "shadow"
            for source in ("C1", "C2", "C3")
        }
    )


def _source_hashes(validated: Mapping[str, Any]) -> dict[str, str]:
    authority = validated.get("authority")
    if not isinstance(authority, Mapping):
        raise Pilot100ArmError("validated source authority is missing")
    protected = authority.get("protected_source_sha256")
    pilot = authority.get("pilot_route_source_sha256")
    if not isinstance(protected, Mapping) or not isinstance(pilot, Mapping):
        raise Pilot100ArmError("validated source bindings are missing")
    return {
        **{str(path): str(digest) for path, digest in protected.items()},
        **{str(path): str(digest) for path, digest in pilot.items()},
    }


def run_arm(
    *,
    authority_path: Path,
    arm: str,
    output_dir: Path,
    tle_root: Path,
) -> dict[str, Any]:
    """Validate, derive, and execute exactly one 100EP pilot arm."""

    if arm not in frozen.ARM_LANES or arm not in ("B000", "F111", "A011", "A101", "A110"):
        raise Pilot100ArmError(f"arm is outside the five-arm pilot: {arm}")
    output = Path(output_dir).expanduser().resolve()
    expected_output = (REPO / PILOT_OUTPUT_RELATIVE / arm).resolve()
    if output != expected_output:
        raise Pilot100ArmError(
            f"canonical pilot arm output required: {expected_output}"
        )
    if output.exists():
        raise Pilot100ArmError(f"output directory must be absent before launch: {output}")

    authority_file = Path(authority_path).expanduser().resolve()
    validated = load_and_validate_authority(authority_file, tle_root=tle_root)
    config_authority = validated["config"]
    seeds = validated["seeds"]
    prereg_path = Path(validated["authority"]["canonical_prereg"])
    corpus_path = Path(validated["authority"]["c1_exp_corpus_manifest"])

    prereg, archive, ephemeris_authority = frozen._canonical_ephemeris_authority(
        prereg_path,
        Path(tle_root).expanduser().resolve(),
    )
    if (
        ephemeris_authority["tle_file_set_sha256"]
        != validated["authority"]["tle_file_set_sha256"]
    ):
        raise Pilot100ArmError("runtime TLE archive drifted from pilot authority")

    # Creation is deliberately delayed until every authority/TLE check passes.
    output.mkdir(parents=True, exist_ok=False)
    trainer_config = frozen._short_config(
        prereg,
        arm=arm,
        episodes=PILOT_EPISODES,
        epsilon_decay_episodes=config_authority["epsilon_decay_episodes"],
        target_update_every=config_authority["target_update_every"],
        learning_rate=validated["learning_rate"],
    )
    common = {
        "output_dir": output,
        "archive": archive,
        "config": trainer_config,
        "users": config_authority["users"],
        "train_seed": seeds["training"],
        "env_seed": seeds["environment"],
        "mobility_seed": seeds["mobility"],
        "checkpoint_every": config_authority["checkpoint_every_episodes"],
    }
    gates = _gate_ledger(arm)
    if arm == "B000":
        result = frozen.run_baseline(**common)
    else:
        result = frozen.run_treatment(
            arm=arm,
            gates=gates,
            acrm_eta=config_authority["acrm_eta"],
            c1_corpus_manifest=corpus_path,
            **common,
        )

    gate_payload = {
        "schema": validated["schema"],
        "status": "AUTHORIZED_FOR_BOUNDED_100EP_PILOT",
        "authority_manifest": str(authority_file),
        "authority_manifest_sha256": frozen.sha256_file(authority_file),
        "validated": validated,
        "active_sources": sorted(frozen.ARM_ACTIVE_SOURCES.get(arm, ())),
        "formal_training_authorized": False,
        "automatic_longer_run_authorized": False,
        "9000_authorized": False,
    }
    status = {
        "schema": SCHEMA,
        "status": "complete",
        "arm": arm,
        "label": frozen.ARM_LABELS[arm],
        "episodes": PILOT_EPISODES,
        "users": config_authority["users"],
        "seeds": {
            "training": seeds["training"],
            "environment": seeds["environment"],
            "mobility": seeds["mobility"],
        },
        "config": asdict(trainer_config),
        "checkpointing": {
            "every_episodes": config_authority["checkpoint_every_episodes"],
            "trend_snapshots": "all-periodic-Main-only-policy",
            "exact_resume_state": "rolling-latest-only",
            "specialist_bundle_replay_capacity": config_authority[
                "specialist_bundle_replay_capacity"
            ],
        },
        "gate_manifest": gate_payload,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
        },
        "authority": ephemeris_authority,
        "source_files_sha256": _source_hashes(validated),
        "result": result,
        "claim_ceiling": CLAIM_CEILING,
        "formal_training_authorized": False,
        "automatic_longer_run_authorized": False,
        "9000_authorized": False,
    }
    frozen._write_json(output / "status.json", status)
    return status


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument(
        "--arm",
        choices=("B000", "F111", "A011", "A101", "A110"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        status = run_arm(
            authority_path=args.authority,
            arm=args.arm,
            output_dir=args.output_dir,
            tle_root=args.tle_root,
        )
    except Pilot100ArmError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(Path(status["result"]["checkpoint"]).parent / "status.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
