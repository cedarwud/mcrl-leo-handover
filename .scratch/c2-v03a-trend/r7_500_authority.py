#!/usr/bin/env python3
"""Fail-closed master authority for the R7 500-episode preliminary route."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

import sys

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import c2_v03a_trend_authority as r2_authority  # noqa: E402


REQUEST_SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-authority-v5"
RESULT_SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-authority-validation-v5"
CLAIM_CEILING = (
    "ONE_TRAINED_POLICY_500EP_PRELIMINARY_MAIN_ONLY_TEST_"
    "NOT_CHAPTER5_NOT_FORMAL_EFFICACY_NOT_9000"
)
EPISODES = 500
PREFIX_ARMS = ("B000", "F111")
ABLATION_ARMS = ("A101", "A011", "A110")
ALL_R7_ARMS = PREFIX_ARMS + ABLATION_ARMS
BRIDGED_ARMS = ALL_R7_ARMS
ALLOWED_LEARNING_RATES = (0.001, 0.01)
TRAINING_SEEDS = copy.deepcopy(r2_authority.TRAINING_SEEDS)
EVALUATION_SEEDS = list(r2_authority.EVALUATION_SEEDS)
EVALUATION_USERS = list(r2_authority.EVALUATION_USERS)

BASE_AUTHORITIES = {
    "0.001": (
        "artifacts/multi-catfish-v03a-intermediate-authority-20260830-r2/"
        "1500-lr0p001.json"
    ),
    "0.01": (
        "artifacts/multi-catfish-v03a-intermediate-authority-20260830-r2/"
        "1500-lr0p01.json"
    ),
}
SOURCE_MATRICES = {
    "0.001": "artifacts/multi-catfish-v03a-1500-lr0p001-20260830-r2",
    "0.01": "artifacts/multi-catfish-v03a-1500-lr0p01-20260830-r2",
}
MASTER_AUTHORITY = (
    "artifacts/multi-catfish-v03a-r7-preliminary-authority-20260831-r5/master.json"
)
BRIDGE_OUTPUT = "artifacts/multi-catfish-v03a-r7-prefix-bridge-20260831-r5"
RECONCILIATION_OUTPUT = (
    "artifacts/multi-catfish-v03a-r7-prefix-reconciliation-20260831-r5"
)
ABLATION_OUTPUT_ROOT = (
    "artifacts/multi-catfish-v03a-r7-preliminary-500-20260831-r5"
)
RECONCILIATION_RECEIPT = f"{RECONCILIATION_OUTPUT}/prefix-reconciliation.json"
REQUIRED_LABELS = [
    "500-EP PRELIMINARY",
    "ONE TRAINED POLICY",
    "MAIN-ONLY HELD-OUT TEST EVALUATION",
    "NOT A CHAPTER 5 RESULT",
    "NOT FORMAL EFFICACY",
]
RESOURCE_POLICY = {
    "execution_host_role": "UBUNTU_SERVER_ONLY",
    "authorized_hostname": "5090",
    "minimum_logical_cpus": 20,
    "minimum_available_memory_bytes": 8 * 1024**3,
    "max_parallel_r7_evaluation_processes": 1,
    "forbid_evaluation_until_both_source_matrices_complete": True,
    "global_evaluation_lock": f"{ABLATION_OUTPUT_ROOT}/.r7-evaluation.lock",
    "source_checkpoint_reuse_only": True,
    "new_r7_training_authorized": False,
}
RUNTIME_PYTHON_VERSION = "3.13.3"
RUNTIME_PACKAGES = {
    "numpy": "2.5.2",
    "sgp4": "2.27",
    "torch": "2.13.0",
}
ROUTING_RULE = {
    "endpoint_episodes": 500,
    "endpoint_users": 100,
    "endpoint_metric": "mean_ee_bits_per_j",
    "contrast": "100*(F111-B000)/B000",
    "eligibility": "D_FULL_GT_0_AND_SERVICE_LOSS_LE_2PP_AND_ALL_GUARDS_PASS",
    "service_loss_limit_percentage_points": 2.0,
    "tie_metric": "D_full",
    "tie_band_relative_percent": 4.0,
    "tie_preference": 0.001,
    "neither_eligible_action": "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY",
    "eligible_action": "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS",
    "checkpoint_selection_performed": False,
    "reconciliation_required_before_routing": True,
    "source_checkpoint_reuse_only": True,
    "new_training_required": False,
    "zero_service_guard": "REJECT_EVALUATION_EPISODE_WITH_ZERO_TOTAL_USEFUL_BITS",
}

REQUIRED_R7_PINNED_FILES = frozenset(
    {
        ".scratch/c2-v03a-trend/r7_500_runtime_closure.txt",
        ".scratch/c2-v03a-trend/r7_500_authority.py",
        ".scratch/c2-v03a-trend/r7_500_checkpoint.py",
        ".scratch/c2-v03a-trend/freeze_r7_500_authority.py",
        ".scratch/c2-v03a-trend/r7_500_prefix_bridge.py",
        ".scratch/c2-v03a-trend/r7_500_prefix_reconcile.py",
        ".scratch/c2-v03a-trend/r7_500_evaluate.py",
        ".scratch/c2-v03a-trend/r7_500_lr_router.py",
        ".scratch/c2-v03a-trend/r7_500_output.py",
        ".scratch/c2-v03a-trend/r7_500_server_preflight.py",
        ".scratch/c2-v03a-trend/r7_500_ablation_evaluate.py",
        ".scratch/c2-v03a-trend/test_r7_500_control_plane.py",
        "tests/test_w33_r7_500_control_plane.py",
        "docs/MULTI-CATFISH-500EP-PRE-REVEAL-RUNTIME-AMENDMENT-"
        "R7-2026-08-30.md",
        "docs/MULTI-CATFISH-500EP-PRE-REVEAL-RUNTIME-AMENDMENT-"
        "R7-R5-2026-08-31.md",
    }
)
RUNTIME_CLOSURE_MANIFEST = ".scratch/c2-v03a-trend/r7_500_runtime_closure.txt"
RUNTIME_CLOSURE_FILE_COUNT = 55
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00$")

EXPECTED_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "created_utc",
        "decision_document",
        "claim_ceiling",
        "formal_training_authorized",
        "developmental_training_authorized",
        "developmental_training_condition",
        "new_r7_training_authorized",
        "source_checkpoint_reuse_only",
        "prefix_evaluation_authorized",
        "prefix_evaluation_condition",
        "selection_state",
        "selected_learning_rate",
        "episodes",
        "fresh_training_required",
        "resume_allowed",
        "prefix_arms",
        "bridged_arms",
        "ablation_arms",
        "ablation_order",
        "seeds",
        "evaluation_seeds",
        "users",
        "evaluation_users",
        "evaluation_partition",
        "evaluation_policy",
        "ee_aggregation",
        "epsilon_decay_episodes",
        "target_update_every",
        "checkpoint_every_episodes",
        "specialist_bundle_replay_capacity",
        "donor_beta",
        "acrm_eta",
        "max_c2_candidates",
        "routing_rule",
        "base_authorities",
        "source_matrix_paths",
        "master_authority_path",
        "bridge_output",
        "reconciliation_receipt",
        "ablation_output_root",
        "resource_policy",
        "runtime_python_version",
        "runtime_packages",
        "required_labels",
        "cached_c2_implementation",
        "outcome_values_used_to_freeze",
        "pinned_files",
    }
)


class R7500AuthorityError(ValueError):
    """Raised when the R7 master authority drifts from its frozen protocol."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _relative_path(repo: Path, value: Any, *, field: str, file: bool) -> Path:
    if not isinstance(value, str) or not value:
        raise R7500AuthorityError(f"{field} must be a repository-relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise R7500AuthorityError(f"{field} escapes the repository")
    path = (repo / Path(*pure.parts)).resolve()
    if not path.is_relative_to(repo):
        raise R7500AuthorityError(f"{field} escapes the repository")
    if file and not path.is_file():
        raise R7500AuthorityError(f"{field} is missing: {value}")
    return path


def _validate_exact_protocol(request: Mapping[str, Any]) -> None:
    if set(request) != EXPECTED_TOP_LEVEL_FIELDS:
        missing = sorted(EXPECTED_TOP_LEVEL_FIELDS - set(request))
        unknown = sorted(set(request) - EXPECTED_TOP_LEVEL_FIELDS)
        raise R7500AuthorityError(
            f"top-level authority fields drifted; missing={missing}, unknown={unknown}"
        )
    created_utc = request.get("created_utc")
    if not isinstance(created_utc, str) or not UTC_RE.fullmatch(created_utc):
        raise R7500AuthorityError("created_utc must be an explicit UTC ISO-8601 timestamp")
    try:
        created = datetime.fromisoformat(created_utc)
    except ValueError as error:
        raise R7500AuthorityError("created_utc is not a real calendar timestamp") from error
    if created.tzinfo is None or created.utcoffset() != timezone.utc.utcoffset(created):
        raise R7500AuthorityError("created_utc must use the +00:00 UTC offset")
    exact = {
        "decision_document": (
            "docs/MULTI-CATFISH-500EP-PRE-REVEAL-RUNTIME-AMENDMENT-"
            "R7-R5-2026-08-31.md"
        ),
        "claim_ceiling": CLAIM_CEILING,
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
        "episodes": EPISODES,
        "fresh_training_required": False,
        "resume_allowed": False,
        "prefix_arms": list(PREFIX_ARMS),
        "bridged_arms": list(BRIDGED_ARMS),
        "ablation_arms": list(ABLATION_ARMS),
        "ablation_order": list(ABLATION_ARMS),
        "seeds": TRAINING_SEEDS,
        "evaluation_seeds": EVALUATION_SEEDS,
        "users": 100,
        "evaluation_users": EVALUATION_USERS,
        "evaluation_partition": "TEST",
        "evaluation_policy": "MAIN_ONLY_MASKED_GREEDY",
        "ee_aggregation": "RATIO_OF_POOLED_USEFUL_BITS_TO_POOLED_SYSTEM_ENERGY",
        "epsilon_decay_episodes": 2000,
        "target_update_every": 50,
        "checkpoint_every_episodes": 100,
        "specialist_bundle_replay_capacity": 2000,
        "max_c2_candidates": 9,
        "routing_rule": ROUTING_RULE,
        "source_matrix_paths": SOURCE_MATRICES,
        "master_authority_path": MASTER_AUTHORITY,
        "bridge_output": BRIDGE_OUTPUT,
        "reconciliation_receipt": RECONCILIATION_RECEIPT,
        "ablation_output_root": ABLATION_OUTPUT_ROOT,
        "resource_policy": RESOURCE_POLICY,
        "runtime_python_version": RUNTIME_PYTHON_VERSION,
        "runtime_packages": RUNTIME_PACKAGES,
        "required_labels": REQUIRED_LABELS,
        "cached_c2_implementation": False,
        "outcome_values_used_to_freeze": False,
    }
    for field, expected in exact.items():
        if request.get(field) != expected:
            raise R7500AuthorityError(f"{field} drifted from the R7 protocol")
    for field, expected in (("donor_beta", 0.25), ("acrm_eta", 1.0)):
        value = request.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not math.isclose(float(value), expected, rel_tol=0.0, abs_tol=1e-15)
        ):
            raise R7500AuthorityError(f"{field} drifted from {expected}")


def _validate_base_authorities(
    request: Mapping[str, Any], *, repo: Path, tle_root: Path
) -> tuple[dict[str, dict[str, Any]], str]:
    rows = request.get("base_authorities")
    if not isinstance(rows, Mapping) or set(rows) != set(BASE_AUTHORITIES):
        raise R7500AuthorityError("base_authorities must contain the exact two LR rows")
    validated: dict[str, dict[str, Any]] = {}
    normalized: list[str] = []
    for key, expected_relative in BASE_AUTHORITIES.items():
        row = rows.get(key)
        if not isinstance(row, Mapping) or row.get("path") != expected_relative:
            raise R7500AuthorityError(f"base authority path drifted for lr={key}")
        path = _relative_path(
            repo, expected_relative, field=f"base_authorities[{key}].path", file=True
        )
        observed_sha = sha256_file(path)
        if row.get("sha256") != observed_sha:
            raise R7500AuthorityError(f"base authority SHA drifted for lr={key}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = r2_authority.validate_v03a_trend_authority(
                payload, repo=repo, tle_root=tle_root
            )
        except Exception as error:
            raise R7500AuthorityError(
                f"base R2 authority no longer validates for lr={key}"
            ) from error
        expected_lr = float(key)
        if result.get("episodes") != 1500 or not math.isclose(
            float(result.get("learning_rate", float("nan"))),
            expected_lr,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise R7500AuthorityError(f"base R2 authority identity drifted for lr={key}")
        if result.get("arms") != list(r2_authority.ALLOWED_ARMS):
            raise R7500AuthorityError(f"base R2 arm set drifted for lr={key}")
        result["authority_path"] = str(path)
        result["authority_sha256"] = observed_sha
        validated[key] = result
        comparable = copy.deepcopy(dict(payload))
        comparable.pop("learning_rate", None)
        normalized.append(canonical_json_sha256(comparable))
    if len(set(normalized)) != 1:
        raise R7500AuthorityError(
            "the two base authorities differ beyond their learning rate"
        )
    return validated, normalized[0]


def _validate_r7_pins(request: Mapping[str, Any], *, repo: Path) -> dict[str, str]:
    pins = request.get("pinned_files")
    expected_paths = set(REQUIRED_R7_PINNED_FILES) | set(BASE_AUTHORITIES.values())
    if not isinstance(pins, Mapping) or set(pins) != expected_paths:
        raise R7500AuthorityError("pinned_files is not the exact R7 runtime closure")
    validated: dict[str, str] = {}
    for relative in sorted(expected_paths):
        path = _relative_path(
            repo, relative, field=f"pinned_files[{relative!r}]", file=True
        )
        expected = pins.get(relative)
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            raise R7500AuthorityError(f"invalid SHA-256 pin for {relative}")
        observed = sha256_file(path)
        if observed != expected:
            raise R7500AuthorityError(f"R7 pinned file drifted: {relative}")
        validated[relative] = observed
    return validated


def _validate_runtime_closure(
    *,
    repo: Path,
    r7_pins: Mapping[str, str],
    bases: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    manifest_path = (repo / RUNTIME_CLOSURE_MANIFEST).resolve()
    try:
        rows = manifest_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise R7500AuthorityError("R7 runtime closure manifest is unreadable") from error
    if (
        len(rows) != RUNTIME_CLOSURE_FILE_COUNT
        or rows != sorted(rows)
        or len(set(rows)) != len(rows)
        or any(not row or row.strip() != row for row in rows)
    ):
        raise R7500AuthorityError("R7 runtime closure manifest shape drifted")
    inherited: list[str] = []
    direct: list[str] = []
    for relative in rows:
        path = _relative_path(
            repo, relative, field=f"runtime_closure[{relative!r}]", file=True
        )
        observed = sha256_file(path)
        if r7_pins.get(relative) == observed:
            direct.append(relative)
            continue
        if all(
            isinstance(base.get("pinned_files"), Mapping)
            and base["pinned_files"].get(relative) == observed
            for base in bases.values()
        ):
            inherited.append(relative)
            continue
        raise R7500AuthorityError(
            f"runtime closure file is not pinned by R7 or both base authorities: {relative}"
        )
    return {
        "manifest": RUNTIME_CLOSURE_MANIFEST,
        "manifest_sha256": sha256_file(manifest_path),
        "file_count": len(rows),
        "r7_direct_count": len(direct),
        "r2_inherited_count": len(inherited),
        "status": "PASS",
    }


def validate_r7_500_authority(
    request: Mapping[str, Any], *, repo: Path = REPO, tle_root: Path
) -> dict[str, Any]:
    """Validate the outcome-blind master authority without reading EE results."""

    if not isinstance(request, Mapping):
        raise R7500AuthorityError("R7 authority must be a mapping")
    if request.get("schema") != REQUEST_SCHEMA:
        raise R7500AuthorityError("unsupported R7 authority schema")
    repo = Path(repo).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    _validate_exact_protocol(request)
    bases, normalized_base_sha = _validate_base_authorities(
        request, repo=repo, tle_root=tle_root
    )
    pins = _validate_r7_pins(request, repo=repo)
    runtime_closure = _validate_runtime_closure(
        repo=repo, r7_pins=pins, bases=bases
    )
    result = copy.deepcopy(dict(request))
    result.update(
        {
            "schema": RESULT_SCHEMA,
            "status": "PASS",
            "repo_root": str(repo),
            "tle_root": str(tle_root),
            "validated_base_authorities": bases,
            "normalized_base_authority_sha256": normalized_base_sha,
            "pinned_files": pins,
            "pin_map_sha256": canonical_json_sha256(pins),
            "runtime_closure": runtime_closure,
        }
    )
    return result


__all__ = [
    "ABLATION_ARMS",
    "ABLATION_OUTPUT_ROOT",
    "ALLOWED_LEARNING_RATES",
    "ALL_R7_ARMS",
    "BRIDGED_ARMS",
    "BASE_AUTHORITIES",
    "BRIDGE_OUTPUT",
    "CLAIM_CEILING",
    "EPISODES",
    "EVALUATION_SEEDS",
    "EVALUATION_USERS",
    "EXPECTED_TOP_LEVEL_FIELDS",
    "MASTER_AUTHORITY",
    "PREFIX_ARMS",
    "REQUEST_SCHEMA",
    "REQUIRED_R7_PINNED_FILES",
    "REQUIRED_LABELS",
    "RECONCILIATION_RECEIPT",
    "RECONCILIATION_OUTPUT",
    "RESOURCE_POLICY",
    "RUNTIME_PACKAGES",
    "RUNTIME_PYTHON_VERSION",
    "RESULT_SCHEMA",
    "RUNTIME_CLOSURE_FILE_COUNT",
    "RUNTIME_CLOSURE_MANIFEST",
    "ROUTING_RULE",
    "R7500AuthorityError",
    "SOURCE_MATRICES",
    "TRAINING_SEEDS",
    "canonical_json_sha256",
    "sha256_file",
    "validate_r7_500_authority",
]
