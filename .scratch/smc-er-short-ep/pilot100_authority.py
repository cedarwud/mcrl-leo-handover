#!/usr/bin/env python3
"""Fail-closed authority for the independent 100EP Multi-Catfish pilot.

The 100-episode pilot is an append-only diagnostic route between the completed
10EP engineering smoke and the already sealed 1,500/3,000EP trend screens.  It
does not widen either route.  Validation full-loads the canonical 1,500EP
parent authority, authenticates the completed five-arm smoke receipt, and
checks that the frozen training/evaluation implementation is byte-identical.

Only pilot seeds and the 100EP budget differ.  The result can inform a later
human/cross-model decision, but it never authorises 1,500, 3,000, or 9,000EP.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from intermediate_trend_authority import (  # noqa: E402
    ALLOWED_ARMS,
    CANONICAL_PREREG_SHA256,
    CANONICAL_TLE_FILE_COUNT,
    CANONICAL_TLE_FILE_SET_SHA256,
    TREND_ACRM_ETA,
    TREND_CHECKPOINT_EVERY_EPISODES,
    TREND_DONOR_BETA,
    TREND_EPSILON_DECAY_EPISODES,
    TREND_EVALUATION_USERS,
    TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
    TREND_TARGET_UPDATE_EVERY,
    TREND_USERS,
    validate_intermediate_trend_authority,
)


REQUEST_SCHEMA = "multi-catfish-mcrl-pilot100-request-v1"
VALIDATED_SCHEMA = "multi-catfish-mcrl-pilot100-authority-v1"
SMOKE_SCHEMA = "multi-catfish-mcrl-intermediate-trend-matrix-v1"
CLAIM_CEILING = "ONE_SEED_100EP_PILOT_NOT_TREND_NOT_EFFICACY_NOT_CHAPTER5"
EVIDENCE_CEILING = (
    "One-training-seed 100EP diagnostic only: not convergence, formal trend, "
    "role efficacy, Chapter 5 evidence, or authorization for a longer run."
)

PILOT_EPISODES = 100
PILOT_LEARNING_RATE = 0.001
PILOT_TRAINING_SEED = 2026082911
PILOT_ENVIRONMENT_SEED = 2026082912
PILOT_MOBILITY_SEED = 2026082913
PILOT_EVALUATION_SEEDS = (
    2026082914,
    2026082915,
    2026082916,
    2026082917,
    2026082918,
)

CANONICAL_AUTHORITY_RELATIVE = (
    "artifacts/multi-catfish-v02-pilot100-authority-20260829/lr0p001.json"
)
PILOT_OUTPUT_RELATIVE = (
    "artifacts/multi-catfish-v02-pilot100-20260829-lr0p001"
)
PARENT_AUTHORITY_RELATIVE = (
    "artifacts/multi-catfish-v02-intermediate-authority-20260828/"
    "1500-lr0p001.json"
)
PARENT_AUTHORITY_SHA256 = (
    "84085d54b30bce3e33d203ea2e44c329cf21a8b85ac06bb05729c85adbe6742f"
)
SMOKE_RECEIPT_RELATIVE = (
    "artifacts/multi-catfish-v02-server-smoke-20260829-r2-lr0p001/"
    "matrix-receipt.json"
)
SMOKE_RECEIPT_SHA256 = (
    "0eebb582a3d4e9194f64429f75ba9c81b8aba1de67ac1abe8230052b2fe65f0c"
)
FREEZE_RELATIVE = "docs/CATFISH-V0.2-OBSERVABLE-SUPPORT-FREEZE-2026-08-28.json"
FREEZE_SHA256 = (
    "a3676e9d0cb42ed16245b3ce574e6cf1975bed4095aa877d936f679327a7047d"
)

# This is the immutable algorithm/evaluator surface inherited by the pilot.
# The pilot-specific adapter/launcher are separately content-bound by the
# request and by the launch-gate receipt because their hashes cannot be
# circularly embedded in their own source.
PROTECTED_SOURCE_SHA256 = {
    ".scratch/smc-er-short-ep/build_c1_exp_corpus.py": (
        "381eaf9c1295fff40c110822fe08008dfcd1adb4464908a27f7918d9cd8f076e"
    ),
    ".scratch/smc-er-short-ep/c1_exp_corpus.py": (
        "ddb4af1a64460111e42a86d9f21345bf2913e4353c17214c46ee2997c25684d0"
    ),
    ".scratch/smc-er-short-ep/run_short_ep.py": (
        "c2dc73c2bf9f9fc03e7c4ee7d3b336d490c5e92ac028f98a82c12422a63ce953"
    ),
    ".scratch/smc-er-short-ep/smc_er_core.py": (
        "097f550d64bf17600ad3cc86fdbc6094ff796d7782b19d6ba936b4370f6eb666"
    ),
    ".scratch/smc-er-short-ep/smc_er_roles.py": (
        "5f32873ffab4559a2695eff27b3cf76230c0a130cd12f43ae37be2f2f282dfea"
    ),
    ".scratch/smc-er-short-ep/sweep_evaluation.py": (
        "50d80c8b2ff27667bdd33bd43d2e5fb5d810420e786fef9b416ba636b84462b0"
    ),
    ".scratch/smc-er-short-ep/intermediate_trend_authority.py": (
        "a8793469fdd74a8a32e633d32c0f36e9ec1ed52367b18db1edfcc6639673a464"
    ),
    ".scratch/smc-er-short-ep/run_intermediate_trend_matrix.py": (
        "532224b278087a1948d5ea6c7532e478ac732fb6e2e4e993e4a4bddb90298075"
    ),
}
PROTECTED_AUTHORITY_SHA256 = {
    "artifacts/multi-catfish-v02-intermediate-authority-20260828/1500-lr0p001.json": (
        "84085d54b30bce3e33d203ea2e44c329cf21a8b85ac06bb05729c85adbe6742f"
    ),
    "artifacts/multi-catfish-v02-intermediate-authority-20260828/1500-lr0p01.json": (
        "ed2fbbf5e5770e24d1be6f13e8e61602da9e708e926ad0b126ab2d5a3f843b78"
    ),
    "artifacts/multi-catfish-v02-intermediate-authority-20260828/3000-lr0p001.json": (
        "92b314fc0b50e68425c17f4a0d443ce3b5ee401afb735ce6a89314a013a82803"
    ),
    "artifacts/multi-catfish-v02-intermediate-authority-20260828/3000-lr0p01.json": (
        "644595a7913c92fd0a7536ff5b43c266c82105e5bf2626764e5c0164aed6c231"
    ),
}
PILOT_ROUTE_SOURCE_PATHS = (
    ".scratch/smc-er-short-ep/pilot100_authority.py",
    ".scratch/smc-er-short-ep/run_pilot100_arm.py",
    ".scratch/smc-er-short-ep/run_pilot100_matrix.py",
    ".scratch/smc-er-short-ep/pilot100_sweep_verifier.py",
    ".scratch/smc-er-short-ep/pilot100_arm_verifier.py",
)

CONTINUATION_RULE = {
    "automatic_longer_run": False,
    "complete_all_five_arms_and_sweep_after_start": True,
    "early_stop_on_observed_ee_sign": False,
    "technical_stop": (
        "Stop queued arms only after launch/runtime/receipt verification failure; "
        "drain already-running arms and preserve the failed receipt."
    ),
    "c2_redesign_gate": (
        "If C2 marginal Full-(Full-C2) is negative at all five user loads, "
        "do not launch 1500EP before a C2 design adjudication."
    ),
    "zero_power_policy": (
        "Nonzero zero-power intervals preserve the completed diagnostic data "
        "but block longer-run eligibility pending a physics adjudication."
    ),
    "longer_run_gate": (
        "Any 1500EP decision requires a fresh post-pilot review; this authority "
        "never launches or authorises it automatically."
    ),
}


class Pilot100AuthorityError(RuntimeError):
    """Raised when the independent 100EP pilot cannot be authorised."""

    def __init__(self, failures: Sequence[str]) -> None:
        self.failures = tuple(dict.fromkeys(str(item) for item in failures))
        super().__init__("pilot100 authority validation failed: " + "; ".join(self.failures))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path, *, label: str, failures: list[str]) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        failures.append(f"{label}: unreadable ({type(error).__name__})")
        return None
    if not isinstance(value, Mapping):
        failures.append(f"{label}: object required")
        return None
    return value


def _strict_repo_path(
    raw: Any,
    *,
    repo: Path,
    expected_relative: str,
    label: str,
    failures: list[str],
) -> Path | None:
    if not isinstance(raw, str) or not raw:
        failures.append(f"{label}: repository-relative path required")
        return None
    pure = PurePosixPath(raw)
    if (
        pure.is_absolute()
        or raw.startswith("~")
        or "\\" in raw
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        failures.append(f"{label}: strict repository-relative POSIX path required")
        return None
    if pure.as_posix() != expected_relative:
        failures.append(f"{label}: canonical path mismatch")
        return None
    target = (repo / pure.as_posix()).resolve()
    try:
        target.relative_to(repo.resolve())
    except ValueError:
        failures.append(f"{label}: path escapes checkout")
        return None
    return target


def _same_float(raw: Any, expected: float) -> bool:
    if isinstance(raw, bool):
        return False
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(value) and math.isclose(
        value, expected, rel_tol=0.0, abs_tol=1e-15
    )


def _validate_source_bindings(
    request: Mapping[str, Any], *, repo: Path, failures: list[str]
) -> None:
    declared = request.get("protected_source_sha256")
    if declared != PROTECTED_SOURCE_SHA256:
        failures.append("protected_source_sha256: exact frozen source map required")
    for relative, expected in PROTECTED_SOURCE_SHA256.items():
        target = repo / relative
        if not target.is_file():
            failures.append(f"protected source missing: {relative}")
        elif sha256_file(target) != expected:
            failures.append(f"protected source hash mismatch: {relative}")

    authority_declared = request.get("protected_authority_sha256")
    if authority_declared != PROTECTED_AUTHORITY_SHA256:
        failures.append("protected_authority_sha256: exact four-authority map required")
    for relative, expected in PROTECTED_AUTHORITY_SHA256.items():
        target = repo / relative
        if not target.is_file():
            failures.append(f"protected authority missing: {relative}")
        elif sha256_file(target) != expected:
            failures.append(f"protected authority hash mismatch: {relative}")

    pilot_declared = request.get("pilot_route_source_sha256")
    if not isinstance(pilot_declared, Mapping) or tuple(sorted(pilot_declared)) != tuple(
        sorted(PILOT_ROUTE_SOURCE_PATHS)
    ):
        failures.append("pilot_route_source_sha256: exact pilot source set required")
        return
    for relative in PILOT_ROUTE_SOURCE_PATHS:
        target = repo / relative
        expected = pilot_declared.get(relative)
        if not isinstance(expected, str) or len(expected) != 64:
            failures.append(f"pilot route source hash malformed: {relative}")
        elif not target.is_file():
            failures.append(f"pilot route source missing: {relative}")
        elif sha256_file(target) != expected:
            failures.append(f"pilot route source hash mismatch: {relative}")


def _validate_smoke_receipt(
    receipt: Mapping[str, Any],
    *,
    parent: Mapping[str, Any],
    failures: list[str],
) -> None:
    if receipt.get("schema") != SMOKE_SCHEMA:
        failures.append("ten_ep_smoke_receipt: wrong schema")
    exact = {
        "status": "complete",
        "episodes": 10,
        "smoke": True,
        "learning_rate": PILOT_LEARNING_RATE,
        "arms": list(ALLOWED_ARMS),
        "no_retry": True,
        "formal_training_authorized": False,
        "authority_manifest_sha256": PARENT_AUTHORITY_SHA256,
    }
    for field, expected in exact.items():
        observed = receipt.get(field)
        if isinstance(expected, float):
            matched = _same_float(observed, expected)
        else:
            matched = observed == expected
        if not matched:
            failures.append(f"ten_ep_smoke_receipt.{field}: mismatch")

    canonical = receipt.get("canonical_inputs")
    parent_authority = parent.get("authority")
    if not isinstance(canonical, Mapping) or not isinstance(parent_authority, Mapping):
        failures.append("ten_ep_smoke_receipt: canonical inputs missing")
    else:
        bindings = {
            "prereg_sha256": parent_authority.get("canonical_prereg_sha256"),
            "c1_exp_corpus_manifest_sha256": parent_authority.get(
                "c1_exp_corpus_manifest_sha256"
            ),
            "tle_file_set_sha256": CANONICAL_TLE_FILE_SET_SHA256,
            "tle_file_count": CANONICAL_TLE_FILE_COUNT,
        }
        for field, expected in bindings.items():
            if canonical.get(field) != expected:
                failures.append(f"ten_ep_smoke_receipt canonical {field}: mismatch")

    rows = receipt.get("arm_runs")
    if not isinstance(rows, list) or [row.get("arm") for row in rows if isinstance(row, Mapping)] != list(ALLOWED_ARMS):
        failures.append("ten_ep_smoke_receipt: exact five ordered arm rows required")
    else:
        for row in rows:
            verification = row.get("verification") if isinstance(row, Mapping) else None
            if (
                row.get("attempt") != 1
                or row.get("status") != "PASS"
                or row.get("exit_code") != 0
                or not isinstance(verification, Mapping)
                or verification.get("status") != "PASS"
                or verification.get("failures") != []
            ):
                failures.append(
                    f"ten_ep_smoke_receipt arm {row.get('arm')}: clean PASS required"
                )
    sweep = receipt.get("sweep")
    verification = sweep.get("verification") if isinstance(sweep, Mapping) else None
    if (
        not isinstance(sweep, Mapping)
        or sweep.get("status") != "PASS"
        or sweep.get("exit_code") != 0
        or not isinstance(verification, Mapping)
        or verification.get("status") != "PASS"
        or verification.get("failures") != []
    ):
        failures.append("ten_ep_smoke_receipt: clean sweep PASS required")


def validate_pilot100_authority(
    request: Mapping[str, Any],
    *,
    tle_root: Path,
    repo: Path = REPO,
) -> dict[str, Any]:
    """Validate the sole immutable LR=0.001, 100EP five-arm pilot."""

    if not isinstance(request, Mapping):
        raise Pilot100AuthorityError(["request: object required"])
    root = Path(repo).expanduser().resolve()
    failures: list[str] = []

    exact = {
        "schema": REQUEST_SCHEMA,
        "episodes": PILOT_EPISODES,
        "learning_rate": PILOT_LEARNING_RATE,
        "arms": list(ALLOWED_ARMS),
        "claim_ceiling": CLAIM_CEILING,
        "formal_training_authorized": False,
        "automatic_longer_run_authorized": False,
        "9000_authorized": False,
        "output_root": PILOT_OUTPUT_RELATIVE,
        "users": TREND_USERS,
        "evaluation_users": list(TREND_EVALUATION_USERS),
        "epsilon_decay_episodes": TREND_EPSILON_DECAY_EPISODES,
        "target_update_every": TREND_TARGET_UPDATE_EVERY,
        "checkpoint_every_episodes": TREND_CHECKPOINT_EVERY_EPISODES,
        "specialist_bundle_replay_capacity": TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
        "donor_beta": TREND_DONOR_BETA,
        "acrm_eta": TREND_ACRM_ETA,
        "continuation_rule": CONTINUATION_RULE,
    }
    for field, expected in exact.items():
        observed = request.get(field)
        if isinstance(expected, float):
            matched = _same_float(observed, expected)
        else:
            matched = observed == expected
        if not matched:
            failures.append(f"{field}: fixed pilot value required")

    expected_seeds = {
        "training": PILOT_TRAINING_SEED,
        "environment": PILOT_ENVIRONMENT_SEED,
        "mobility": PILOT_MOBILITY_SEED,
    }
    if request.get("seeds") != expected_seeds:
        failures.append("seeds: exact independent pilot seeds required")
    if request.get("evaluation_seeds") != list(PILOT_EVALUATION_SEEDS):
        failures.append("evaluation_seeds: exact independent pilot set required")
    all_seeds = [*expected_seeds.values(), *PILOT_EVALUATION_SEEDS]
    if len(set(all_seeds)) != len(all_seeds):
        failures.append("pilot seeds: duplicates are forbidden")

    freeze_path = _strict_repo_path(
        request.get("freeze_manifest", {}).get("path")
        if isinstance(request.get("freeze_manifest"), Mapping)
        else None,
        repo=root,
        expected_relative=FREEZE_RELATIVE,
        label="freeze_manifest.path",
        failures=failures,
    )
    freeze_declared = request.get("freeze_manifest")
    if not isinstance(freeze_declared, Mapping) or freeze_declared.get("sha256") != FREEZE_SHA256:
        failures.append("freeze_manifest.sha256: canonical hash required")
    if freeze_path is None or not freeze_path.is_file():
        failures.append("freeze_manifest: file missing")
    elif sha256_file(freeze_path) != FREEZE_SHA256:
        failures.append("freeze_manifest: current hash mismatch")

    parent_declared = request.get("parent_intermediate_authority")
    parent_path = _strict_repo_path(
        parent_declared.get("path") if isinstance(parent_declared, Mapping) else None,
        repo=root,
        expected_relative=PARENT_AUTHORITY_RELATIVE,
        label="parent_intermediate_authority.path",
        failures=failures,
    )
    if not isinstance(parent_declared, Mapping) or parent_declared.get("sha256") != PARENT_AUTHORITY_SHA256:
        failures.append("parent_intermediate_authority.sha256: canonical hash required")
    parent_request = None
    if parent_path is None or not parent_path.is_file():
        failures.append("parent_intermediate_authority: file missing")
    elif sha256_file(parent_path) != PARENT_AUTHORITY_SHA256:
        failures.append("parent_intermediate_authority: current hash mismatch")
    else:
        parent_request = _json(
            parent_path, label="parent_intermediate_authority", failures=failures
        )

    parent: Mapping[str, Any] | None = None
    if parent_request is not None:
        try:
            parent = validate_intermediate_trend_authority(
                parent_request,
                tle_root=Path(tle_root).expanduser().resolve(),
                repo=root,
            )
        except Exception as error:
            failures.append(
                "parent_intermediate_authority: full validation rejected "
                f"({type(error).__name__}: {error})"
            )
        else:
            if (
                parent.get("status") != "PASS"
                or parent.get("episodes") != 1500
                or not _same_float(parent.get("learning_rate"), PILOT_LEARNING_RATE)
                or parent.get("arms") != list(ALLOWED_ARMS)
            ):
                failures.append("parent_intermediate_authority: wrong validated surface")

    smoke_declared = request.get("ten_ep_smoke_receipt")
    smoke_path = _strict_repo_path(
        smoke_declared.get("path") if isinstance(smoke_declared, Mapping) else None,
        repo=root,
        expected_relative=SMOKE_RECEIPT_RELATIVE,
        label="ten_ep_smoke_receipt.path",
        failures=failures,
    )
    if not isinstance(smoke_declared, Mapping) or smoke_declared.get("sha256") != SMOKE_RECEIPT_SHA256:
        failures.append("ten_ep_smoke_receipt.sha256: canonical hash required")
    smoke = None
    if smoke_path is None or not smoke_path.is_file():
        failures.append("ten_ep_smoke_receipt: file missing")
    elif sha256_file(smoke_path) != SMOKE_RECEIPT_SHA256:
        failures.append("ten_ep_smoke_receipt: current hash mismatch")
    else:
        smoke = _json(smoke_path, label="ten_ep_smoke_receipt", failures=failures)
    if smoke is not None and parent is not None:
        _validate_smoke_receipt(smoke, parent=parent, failures=failures)

    _validate_source_bindings(request, repo=root, failures=failures)

    if failures:
        raise Pilot100AuthorityError(failures)
    assert parent is not None and parent_path is not None and smoke_path is not None
    parent_authority = parent["authority"]
    return {
        "schema": VALIDATED_SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "evidence_ceiling": EVIDENCE_CEILING,
        "episodes": PILOT_EPISODES,
        "learning_rate": PILOT_LEARNING_RATE,
        "arms": list(ALLOWED_ARMS),
        "seeds": {
            **expected_seeds,
            "evaluation_seeds": list(PILOT_EVALUATION_SEEDS),
        },
        "config": {
            "users": TREND_USERS,
            "evaluation_users": list(TREND_EVALUATION_USERS),
            "epsilon_decay_episodes": TREND_EPSILON_DECAY_EPISODES,
            "target_update_every": TREND_TARGET_UPDATE_EVERY,
            "checkpoint_every_episodes": TREND_CHECKPOINT_EVERY_EPISODES,
            "specialist_bundle_replay_capacity": TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
            "donor_beta": TREND_DONOR_BETA,
            "acrm_eta": TREND_ACRM_ETA,
        },
        "continuation_rule": CONTINUATION_RULE,
        "9000_authorized": False,
        "authority": {
            "parent_intermediate_authority": str(parent_path),
            "parent_intermediate_authority_sha256": PARENT_AUTHORITY_SHA256,
            "ten_ep_smoke_receipt": str(smoke_path),
            "ten_ep_smoke_receipt_sha256": SMOKE_RECEIPT_SHA256,
            "freeze_manifest": str(freeze_path),
            "freeze_manifest_sha256": FREEZE_SHA256,
            "canonical_prereg": parent_authority["canonical_prereg"],
            "canonical_prereg_sha256": CANONICAL_PREREG_SHA256,
            "tle_file_set_sha256": CANONICAL_TLE_FILE_SET_SHA256,
            "c1_exp_corpus_manifest": parent_authority["c1_exp_corpus_manifest"],
            "c1_exp_corpus_manifest_sha256": parent_authority[
                "c1_exp_corpus_manifest_sha256"
            ],
            "protected_source_sha256": dict(PROTECTED_SOURCE_SHA256),
            "protected_authority_sha256": dict(PROTECTED_AUTHORITY_SHA256),
            "pilot_route_source_sha256": dict(request["pilot_route_source_sha256"]),
        },
    }


__all__ = [
    "CANONICAL_AUTHORITY_RELATIVE",
    "CLAIM_CEILING",
    "CONTINUATION_RULE",
    "EVIDENCE_CEILING",
    "PILOT_EPISODES",
    "PILOT_EVALUATION_SEEDS",
    "PILOT_LEARNING_RATE",
    "PILOT_OUTPUT_RELATIVE",
    "Pilot100AuthorityError",
    "REQUEST_SCHEMA",
    "VALIDATED_SCHEMA",
    "validate_pilot100_authority",
]
