#!/usr/bin/env python3
"""Freeze one outcome-blind R7 500-episode master authority."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

import sys

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import r7_500_authority as authority  # noqa: E402


def build_request(*, repo: Path = REPO) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    pin_paths = set(authority.REQUIRED_R7_PINNED_FILES) | set(
        authority.BASE_AUTHORITIES.values()
    )
    missing = [relative for relative in sorted(pin_paths) if not (repo / relative).is_file()]
    if missing:
        raise FileNotFoundError("R7 runtime pin closure is missing: " + ", ".join(missing))
    return {
        "schema": authority.REQUEST_SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "decision_document": (
            "docs/MULTI-CATFISH-500EP-PRE-REVEAL-RUNTIME-AMENDMENT-"
            "R7-R5-2026-08-31.md"
        ),
        "claim_ceiling": authority.CLAIM_CEILING,
        "formal_training_authorized": False,
        "developmental_training_authorized": False,
        "developmental_training_condition": (
            "NO_NEW_R7_TRAINING_SOURCE_EP500_PREFIX_REUSE_ONLY"
        ),
        "new_r7_training_authorized": False,
        "source_checkpoint_reuse_only": True,
        "prefix_evaluation_authorized": True,
        "prefix_evaluation_condition": "VALID_PREFIX_RECONCILIATION_RECEIPT_REQUIRED",
        "selection_state": "WAITING_FOR_MACHINE_GATE",
        "selected_learning_rate": None,
        "episodes": authority.EPISODES,
        "fresh_training_required": False,
        "resume_allowed": False,
        "prefix_arms": list(authority.PREFIX_ARMS),
        "bridged_arms": list(authority.BRIDGED_ARMS),
        "ablation_arms": list(authority.ABLATION_ARMS),
        "ablation_order": list(authority.ABLATION_ARMS),
        "seeds": authority.TRAINING_SEEDS,
        "evaluation_seeds": authority.EVALUATION_SEEDS,
        "users": 100,
        "evaluation_users": authority.EVALUATION_USERS,
        "evaluation_partition": "TEST",
        "evaluation_policy": "MAIN_ONLY_MASKED_GREEDY",
        "ee_aggregation": "RATIO_OF_POOLED_USEFUL_BITS_TO_POOLED_SYSTEM_ENERGY",
        "epsilon_decay_episodes": 2000,
        "target_update_every": 50,
        "checkpoint_every_episodes": 100,
        "specialist_bundle_replay_capacity": 2000,
        "donor_beta": 0.25,
        "acrm_eta": 1.0,
        "max_c2_candidates": 9,
        "routing_rule": authority.ROUTING_RULE,
        "base_authorities": {
            key: {
                "path": relative,
                "sha256": authority.sha256_file(repo / relative),
            }
            for key, relative in authority.BASE_AUTHORITIES.items()
        },
        "source_matrix_paths": authority.SOURCE_MATRICES,
        "master_authority_path": authority.MASTER_AUTHORITY,
        "bridge_output": authority.BRIDGE_OUTPUT,
        "reconciliation_receipt": authority.RECONCILIATION_RECEIPT,
        "ablation_output_root": authority.ABLATION_OUTPUT_ROOT,
        "resource_policy": authority.RESOURCE_POLICY,
        "runtime_python_version": authority.RUNTIME_PYTHON_VERSION,
        "runtime_packages": authority.RUNTIME_PACKAGES,
        "required_labels": authority.REQUIRED_LABELS,
        "cached_c2_implementation": False,
        "outcome_values_used_to_freeze": False,
        "pinned_files": {
            relative: authority.sha256_file(repo / relative)
            for relative in sorted(pin_paths)
        },
    }


def freeze(*, output: Path, tle_root: Path, repo: Path = REPO) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    expected = (repo / authority.MASTER_AUTHORITY).resolve()
    if output != expected:
        raise ValueError(f"R7-r5 authority must be frozen at {expected}")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite frozen R7 authority: {output}")
    request = build_request(repo=repo)
    authority.validate_r7_500_authority(request, repo=repo, tle_root=tle_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(request, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=str(output.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return request


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    freeze(output=args.output, tle_root=args.tle_root)
    print(Path(args.output).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
