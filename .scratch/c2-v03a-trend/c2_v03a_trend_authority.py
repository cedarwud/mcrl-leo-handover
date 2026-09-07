#!/usr/bin/env python3
"""Fail-closed authority for C2 V0.3A intermediate trend screens."""

from __future__ import annotations

import copy
import hashlib
import math
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

REQUEST_SCHEMA = "multi-catfish-mcrl-c2-v03a-trend-request-v1"
RESULT_SCHEMA = "multi-catfish-mcrl-c2-v03a-trend-authority-v1"
CLAIM_CEILING = (
    "ONE_SEED_C2_V03A_INTERMEDIATE_TREND_NOT_CHAPTER5_"
    "NOT_FORMAL_EFFICACY_NOT_9000_NOT_DEPLOYMENT_NOT_AUCTION_NOT_COORDINATION"
)
C3_ROUTE_STATUS = "DEVELOPMENT_ONLY_PENDING_MAIN_CONSUMER_GATE"
C1_ROUTE_STATUS = "DEVELOPMENT_ONLY_PENDING_V03A_CONSUMER_GATE"
C2_ROUTE_STATUS = (
    "DEVELOPMENT_ONLY_V03A_POLICY_ALIGNED_MECHANICS_PASS_EFFICACY_OPEN"
)
ALLOWED_ARMS = ("B000", "F111", "A011", "A101", "A110")
ALLOWED_EPISODES = (1500, 3000)
ALLOWED_LEARNING_RATES = (0.001, 0.01)
TRAINING_SEEDS = {
    "training": 2026082901,
    "environment": 2026082902,
    "mobility": 2026082903,
}
EVALUATION_SEEDS = [
    2026082904,
    2026082905,
    2026082906,
    2026082907,
    2026082908,
]
EVALUATION_USERS = [60, 80, 100, 120, 140]
TLE_FILE_RE = re.compile(r"^starlink_\d{8}\.tle$")
LR_SELECTION_RULE = {
    "endpoint_arm": "F111",
    "endpoint_users": 100,
    "endpoint_metric": "mean_ee_bits_per_j",
    "eligibility": (
        "F111_GT_B000_AND_F111_GT_EACH_LEAVE_ONE_OUT_AT_U100"
    ),
    "tie_band_relative_percent": 4.0,
    "tie_preference": 0.001,
    "neither_eligible_action": "STOP_BEFORE_3000",
    "fresh_3000_required": True,
}
RUNTIME_REQUIRED_PINNED_FILES = frozenset(
    {
        ".scratch/c2-v03/c2_stage0_receipt_adapter.py",
        ".scratch/c2-v03/c2_temporal_fork_chronology.py",
        ".scratch/c2-v03/c2_temporal_fork_combined_carrier.py",
        ".scratch/c2-v03/c2_temporal_fork_core.py",
        ".scratch/c2-v03/c2_temporal_fork_episode_runner.py",
        ".scratch/c2-v03/c2_temporal_fork_forecast_adapter.py",
        ".scratch/c2-v03/c2_temporal_fork_joint_transaction.py",
        ".scratch/c2-v03/c2_temporal_fork_learning_adapter.py",
        ".scratch/c2-v03/c2_temporal_fork_option_runner.py",
        ".scratch/c2-v03/c2_temporal_fork_runtime_adapter.py",
        ".scratch/c2-v03/c2_temporal_fork_selection.py",
        ".scratch/c2-v03/c2_temporal_fork_telemetry.py",
        ".scratch/c2-v03/c2_temporal_fork_torch_adapter.py",
        ".scratch/c2-v03/c2_temporal_fork_trainer_backend.py",
        ".scratch/c2-v03/c2_temporal_fork_training_step.py",
        ".scratch/catfish-stage0/c3_reward_aligned_v3_core.py",
        ".scratch/catfish-stage0/c3_reward_aligned_v3_runtime_adapter.py",
        ".scratch/catfish-stage0/c3_reward_aligned_v3_shadow_runner.py",
        ".scratch/catfish-stage0/c3_reward_aligned_v3_trainer_backend.py",
        ".scratch/catfish-stage0/run_c3_stage0.py",
        ".scratch/catfish-oracle-gate/run_oracle_gate.py",
        ".scratch/smc-er-short-ep/c1_exp_corpus.py",
        ".scratch/smc-er-short-ep/c1_pretransfer_gate_validator.py",
        ".scratch/smc-er-short-ep/gate_receipt_validator.py",
        ".scratch/smc-er-short-ep/intermediate_trend_authority.py",
        ".scratch/smc-er-short-ep/run_short_ep.py",
        ".scratch/smc-er-short-ep/smc_er_core.py",
        ".scratch/smc-er-short-ep/smc_er_roles.py",
        ".scratch/smc-er-short-ep/sweep_evaluation.py",
        ".scratch/c2-v03a-trend/c2_v03a_trend_arm.py",
        ".scratch/c2-v03a-trend/c2_v03a_trend_authority.py",
        ".scratch/c2-v03a-trend/c2_v03a_lr_selector.py",
        ".scratch/c2-v03a-trend/c2_v03a_trend_matrix.py",
        "scripts/run_head_pivotality_probe.py",
    }
)
REQUIRED_PINNED_FILES = frozenset(
    {
        "docs/C2-TEMPORAL-FORK-CANDIDATE-V0.3-2026-08-29.md",
        "docs/MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md",
        "docs/THREE-CATFISH-EE-POSITIVE-ACCEPTANCE-CONTRACT-V0.1-2026-08-28.md",
    }
) | RUNTIME_REQUIRED_PINNED_FILES


class V03ATrendAuthorityError(ValueError):
    """Raised when a long-run request drifts from the frozen trend screen."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_tle_file_set(tle_root: Path) -> tuple[str, int]:
    root = Path(tle_root).expanduser().resolve()
    if not root.is_dir():
        raise V03ATrendAuthorityError(f"TLE root is not a directory: {root}")
    files = sorted(
        path
        for path in root.iterdir()
        if path.is_file() and TLE_FILE_RE.fullmatch(path.name)
    )
    if not files:
        raise V03ATrendAuthorityError("TLE root has no canonical dated files")
    rows = [f"{path.name}:{sha256_file(path)}" for path in files]
    digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
    return digest, len(files)


def _exact_float(value: Any, expected: float, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V03ATrendAuthorityError(f"{field} must be numeric")
    if not math.isfinite(float(value)) or not math.isclose(
        float(value), expected, rel_tol=0.0, abs_tol=1e-15
    ):
        raise V03ATrendAuthorityError(f"{field} drifted from {expected}")


def _relative_file(repo: Path, relative: Any, *, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise V03ATrendAuthorityError(f"{field} must be a relative file path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise V03ATrendAuthorityError(f"{field} escapes the repository")
    path = (repo / Path(*pure.parts)).resolve()
    if not path.is_relative_to(repo) or not path.is_file():
        raise V03ATrendAuthorityError(f"{field} is missing: {relative}")
    return path


def _validate_pins(request: Mapping[str, Any], *, repo: Path) -> dict[str, str]:
    pins = request.get("pinned_files")
    if not isinstance(pins, Mapping) or not pins:
        raise V03ATrendAuthorityError("pinned_files must be a nonempty mapping")
    prereg = request.get("canonical_prereg")
    corpus = request.get("c1_exp_corpus_manifest")
    required = set(REQUIRED_PINNED_FILES)
    if isinstance(prereg, str):
        required.add(prereg)
    if isinstance(corpus, str):
        required.add(corpus)
    missing = required - set(pins)
    if missing:
        raise V03ATrendAuthorityError(
            "pinned_files is missing required paths: " + ", ".join(sorted(missing))
        )
    validated: dict[str, str] = {}
    for relative, expected in pins.items():
        path = _relative_file(repo, relative, field=f"pinned_files[{relative!r}]")
        if not isinstance(expected, str) or len(expected) != 64:
            raise V03ATrendAuthorityError(f"invalid SHA-256 pin for {relative}")
        observed = sha256_file(path)
        if observed != expected:
            raise V03ATrendAuthorityError(f"pinned file drifted: {relative}")
        validated[str(relative)] = observed
    _relative_file(repo, prereg, field="canonical_prereg")
    _relative_file(repo, corpus, field="c1_exp_corpus_manifest")
    return validated


def validate_v03a_trend_authority(
    request: Mapping[str, Any], *, repo: Path = REPO, tle_root: Path
) -> dict[str, Any]:
    """Validate one exact 1,500/3,000-episode five-arm trend request."""

    if not isinstance(request, Mapping):
        raise V03ATrendAuthorityError("trend request must be a mapping")
    repo = Path(repo).expanduser().resolve()
    if request.get("schema") != REQUEST_SCHEMA:
        raise V03ATrendAuthorityError("unsupported C2 V0.3A trend schema")
    if request.get("claim_ceiling") != CLAIM_CEILING:
        raise V03ATrendAuthorityError("trend claim ceiling drifted")
    if request.get("formal_training_authorized") is not False:
        raise V03ATrendAuthorityError("intermediate trend cannot authorize formal training")
    if request.get("c1_route_status") != C1_ROUTE_STATUS:
        raise V03ATrendAuthorityError("C1 route status hides its V0.3A consumer gate")
    if request.get("c2_route_status") != C2_ROUTE_STATUS:
        raise V03ATrendAuthorityError("C2 route status drifted from V0.3A mechanics")
    if request.get("c3_route_status") != C3_ROUTE_STATUS:
        raise V03ATrendAuthorityError("C3 route status hides its open consumer gate")
    if request.get("lr_selection_rule") != LR_SELECTION_RULE:
        raise V03ATrendAuthorityError("LR selection rule is missing or drifted")
    if request.get("episodes") not in ALLOWED_EPISODES:
        raise V03ATrendAuthorityError("episodes must be exactly 1500 or 3000")
    learning_rate = request.get("learning_rate")
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise V03ATrendAuthorityError("learning_rate must be numeric")
    if not any(
        math.isclose(float(learning_rate), value, rel_tol=0.0, abs_tol=1e-15)
        for value in ALLOWED_LEARNING_RATES
    ):
        raise V03ATrendAuthorityError("learning_rate must be 0.001 or 0.01")
    if request.get("arms") != list(ALLOWED_ARMS):
        raise V03ATrendAuthorityError("five-arm order drifted")
    if request.get("seeds") != TRAINING_SEEDS:
        raise V03ATrendAuthorityError("matched training seeds drifted")
    if request.get("evaluation_seeds") != EVALUATION_SEEDS:
        raise V03ATrendAuthorityError("evaluation seeds drifted")
    exact = {
        "users": 100,
        "evaluation_users": EVALUATION_USERS,
        "epsilon_decay_episodes": 2000,
        "target_update_every": 50,
        "checkpoint_every_episodes": 100,
        "specialist_bundle_replay_capacity": 2000,
        "max_c2_candidates": 9,
    }
    for field, expected in exact.items():
        if request.get(field) != expected:
            raise V03ATrendAuthorityError(f"{field} drifted")
    _exact_float(request.get("donor_beta"), 0.25, field="donor_beta")
    _exact_float(request.get("acrm_eta"), 1.0, field="acrm_eta")
    tle_sha, tle_count = canonical_tle_file_set(tle_root)
    if request.get("tle_file_set_sha256") != tle_sha:
        raise V03ATrendAuthorityError("TLE file-set SHA drifted")
    if request.get("tle_file_count") != tle_count:
        raise V03ATrendAuthorityError("TLE file count drifted")
    pins = _validate_pins(request, repo=repo)
    validated = copy.deepcopy(dict(request))
    validated.update(
        {
            "schema": RESULT_SCHEMA,
            "status": "PASS",
            "learning_rate": float(learning_rate),
            "pinned_files": pins,
            "tle_root": str(Path(tle_root).expanduser().resolve()),
        }
    )
    return validated


__all__ = [
    "ALLOWED_ARMS",
    "ALLOWED_EPISODES",
    "ALLOWED_LEARNING_RATES",
    "C1_ROUTE_STATUS",
    "C2_ROUTE_STATUS",
    "C3_ROUTE_STATUS",
    "CLAIM_CEILING",
    "LR_SELECTION_RULE",
    "REQUEST_SCHEMA",
    "RUNTIME_REQUIRED_PINNED_FILES",
    "RESULT_SCHEMA",
    "V03ATrendAuthorityError",
    "canonical_tle_file_set",
    "sha256_file",
    "validate_v03a_trend_authority",
]
