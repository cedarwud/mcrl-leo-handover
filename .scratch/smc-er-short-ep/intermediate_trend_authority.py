#!/usr/bin/env python3
"""Fail-closed authority checks for the bounded intermediate trend screen.

This module is deliberately narrower than the formal 9,000-episode protocol.
It authorises only a *one-training-seed, matched five-arm* screen at 1,500 or
3,000 episodes and at one of two predeclared learning rates.  The screen is a
trend diagnostic; its result is never a Chapter 5 result, formal efficacy
claim, or 9,000-episode training authorisation.

The validator does not edit or launch the runner.  A harness calls
``validate_intermediate_trend_authority(request)`` before it launches any
arm.  Evidence is accepted only when the current V0.2 freeze, a current PASS
support census, and an independently replayed PASS zero-dose parity receipt
all bind the same canonical preregistration, TLE file-set hash, and C1 EXP
manifest.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


SCHEMA = "multi-catfish-mcrl-intermediate-trend-authority-v1"
FREEZE_SCHEMA = "multi-catfish-mcrl-v0.2-observable-support-freeze-v1"
FREEZE_STATUS = "FROZEN_BEFORE_SUPPORT_CENSUS"
SUPPORT_SCHEMA = "multi-catfish-mcrl-v0.2-support-census-v2"
ZERO_DOSE_SCHEMA = "multi-catfish-mcrl-zero-dose-parity-v5"
PUBLIC_METHOD_NAME = "Multi-Catfish MCRL"
SUPPORT_VERSION = "V0.2_OBSERVABLE_ELIGIBILITY"
CLAIM_CEILING = (
    "ONE_SEED_INTERMEDIATE_TREND_SCREEN_NOT_CHAPTER5_"
    "NOT_FORMAL_EFFICACY_NOT_9000"
)
EVIDENCE_CEILING = (
    "Intermediate 1500/3000-episode trend screen only: not Chapter 5, "
    "not formal efficacy, and not 9000-episode training authorization."
)

ALLOWED_ARMS = ("B000", "F111", "A011", "A101", "A110")
ALLOWED_EPISODES = (1500, 3000)
ALLOWED_LEARNING_RATES = (0.001, 0.01)

# These seeds are intentionally separate from the V0.2 support-census pairs,
# the zero-dose parity run, the C1 corpus/source gates, and the old P6 seeds.
# They are the sole one-seed trend-screen binding; a harness may not replace
# them after looking at any result.
TREND_TRAINING_SEED = 2026082901
TREND_ENVIRONMENT_SEED = 2026082902
TREND_MOBILITY_SEED = 2026082903
TREND_EVALUATION_SEEDS = (
    2026082904,
    2026082905,
    2026082906,
    2026082907,
    2026082908,
)
TREND_USERS = 100
TREND_EVALUATION_USERS = (60, 80, 100, 120, 140)
TREND_EPSILON_DECAY_EPISODES = 2000
TREND_TARGET_UPDATE_EVERY = 50
TREND_CHECKPOINT_EVERY_EPISODES = 100
TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY = 2000
TREND_DONOR_BETA = 0.25
TREND_ACRM_ETA = 1.0

CANONICAL_PREREG_RELATIVE = "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
CANONICAL_PREREG_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
CANONICAL_TLE_FILE_SET_SHA256 = (
    "427e6a91774b0ebf3d9b5a13dd783fdaa3f107666f9e9a6cb2a08d5c92b38fe9"
)
CANONICAL_TLE_FILE_COUNT = 373
CANONICAL_BASELINE_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
REPOSITORY_PATH_BINDING = "repository_relative_posix_v1"
RUNTIME_TLE_ROOT_BINDING = "runtime_argument"
FREEZE_RELATIVE = (
    "docs/CATFISH-V0.2-OBSERVABLE-SUPPORT-FREEZE-2026-08-28.json"
)
SPEC_RELATIVE = "docs/CATFISH-V0.2-OBSERVABLE-SUPPORT-SPEC-2026-08-28.md"
RUNNER_RELATIVE = ".scratch/smc-er-short-ep/run_short_ep.py"
C1_MANIFEST_RELATIVE = (
    "artifacts/smc-er-c1-authority-20260828/"
    "smc-er-c1-exp-corpus-canonical-tle-20260829-v4/"
    "c1-exp-corpus-manifest.json"
)
SELECTION_PLAN_RELATIVE = (
    "docs/MULTI-CATFISH-V02-INTERMEDIATE-TREND-PLAN-2026-08-28.md"
)
SELECTION_PLAN_SHA256 = (
    "edaf262bec53b64905b4cec229d131e48c26068fd9b64c4a15034d96b2bd4e10"
)

DEFAULT_FREEZE = REPO / FREEZE_RELATIVE
DEFAULT_PREREG = REPO / CANONICAL_PREREG_RELATIVE
DEFAULT_C1_MANIFEST = REPO / C1_MANIFEST_RELATIVE

# The checker is imported lazily so unit tests can exercise request and
# receipt guards without loading the simulator.  Production calls use the
# existing independent replay checker, not a self-attested status flag.
validate_zero_dose_receipt: Callable[[Path], Mapping[str, Any]] | None = None
load_verified_c1_corpus: Callable[..., Any] | None = None


class IntermediateTrendAuthorityError(RuntimeError):
    """Raised when an intermediate trend run cannot be authorised."""

    def __init__(
        self,
        failures: Sequence[str],
        *,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        self.failures = tuple(dict.fromkeys(str(item) for item in failures))
        self.evidence = dict(evidence or {})
        super().__init__(
            "intermediate trend authority validation failed: "
            + "; ".join(self.failures)
        )


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_nested_c1_corpus(
    manifest_path: Path,
    *,
    tle_root: Path,
    repo: Path,
    failures: list[str],
) -> None:
    """Exercise every hash-bound C1 manifest reference before arm launch."""

    global load_verified_c1_corpus
    checker = load_verified_c1_corpus
    if checker is None:
        from c1_exp_corpus import load_verified_c1_corpus as checker
    try:
        checker(
            manifest_path,
            expected_checkpoint_sha256=CANONICAL_BASELINE_CHECKPOINT_SHA256,
            expected_state_dim=112,
            expected_action_dim=28,
            tle_root=Path(tle_root).expanduser().resolve(),
            repo=Path(repo).expanduser().resolve(),
        )
    except Exception as error:
        failures.append(f"C1 EXP nested authority: rejected ({error})")


def _digest(value: Any, *, label: str, failures: list[str]) -> str | None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        failures.append(f"{label}: lowercase SHA-256 required")
        return None
    return value


def _mapping(value: Any, *, label: str, failures: list[str]) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        failures.append(f"{label}: object required")
        return None
    return value


def _path(value: Any, *, base: Path, label: str, failures: list[str]) -> Path | None:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value).expanduser()
    else:
        failures.append(f"{label}: path missing")
        return None
    if not candidate.is_absolute():
        candidate = base / candidate
    return candidate.resolve()


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


def _bound_file(
    value: Any,
    expected_digest: Any,
    *,
    base: Path,
    label: str,
    failures: list[str],
) -> Path | None:
    target = _path(value, base=base, label=label, failures=failures)
    expected = _digest(expected_digest, label=f"{label} expected hash", failures=failures)
    if target is None or expected is None:
        return None
    if not target.is_file():
        failures.append(f"{label}: file missing")
        return None
    actual = sha256_file(target)
    if actual != expected:
        failures.append(f"{label}: hash mismatch")
        return None
    return target


def _close(left: Any, right: float) -> bool:
    if isinstance(left, bool):
        return False
    try:
        value = float(left)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(value) and math.isclose(
        value, right, rel_tol=0.0, abs_tol=1e-15
    )


def _require_exact_path(
    raw: Any,
    expected: Path,
    *,
    base: Path,
    label: str,
    failures: list[str],
) -> Path | None:
    target = _path(raw, base=base, label=label, failures=failures)
    if target is None:
        return None
    if target != expected.resolve():
        failures.append(f"{label}: canonical path mismatch")
        return None
    return target


def _strict_repo_receipt_path(
    raw: Any,
    *,
    repo: Path,
    label: str,
    failures: list[str],
) -> Path | None:
    """Resolve a receipt-owned repository path without ambient checkout paths."""

    if not isinstance(raw, str) or not raw or raw.startswith("~") or "\\" in raw:
        failures.append(f"{label}: repository-relative POSIX path required")
        return None
    portable = PurePosixPath(raw)
    if portable.is_absolute() or any(part in ("", ".", "..") for part in portable.parts):
        failures.append(f"{label}: repository-relative POSIX path required")
        return None
    if portable.as_posix() != raw:
        failures.append(f"{label}: canonical POSIX path required")
        return None
    root = Path(repo).expanduser().resolve()
    target = (root / Path(*portable.parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        failures.append(f"{label}: repository path escapes checkout")
        return None
    return target


def _require_exact_repo_receipt_path(
    raw: Any,
    expected: Path,
    *,
    repo: Path,
    label: str,
    failures: list[str],
) -> Path | None:
    target = _strict_repo_receipt_path(
        raw, repo=repo, label=label, failures=failures
    )
    if target is not None and target != expected.resolve():
        failures.append(f"{label}: canonical path mismatch")
        return None
    return target


def _request_seed(request: Mapping[str, Any], name: str) -> Any:
    seeds = request.get("seeds")
    if isinstance(seeds, Mapping) and name in seeds:
        return seeds[name]
    aliases = {
        "training": "train_seed",
        "environment": "env_seed",
        "mobility": "mobility_seed",
    }
    return request.get(aliases[name])


def _validate_request_shape(request: Mapping[str, Any], failures: list[str]) -> tuple[int | None, float | None]:
    raw_episodes = request.get("episodes")
    if type(raw_episodes) is not int:
        failures.append("episodes: integer required")
        episodes = None
    elif raw_episodes not in ALLOWED_EPISODES:
        failures.append(
            f"episodes: only {ALLOWED_EPISODES} are authorised; 9000 is forbidden"
        )
        episodes = None
    else:
        episodes = int(raw_episodes)

    raw_lr = request.get("learning_rate")
    if not any(_close(raw_lr, rate) for rate in ALLOWED_LEARNING_RATES):
        failures.append("learning_rate: only 0.001 or 0.01 is authorised")
        learning_rate = None
    else:
        learning_rate = float(raw_lr)

    arms = request.get("arms")
    if not isinstance(arms, (list, tuple)) or any(
        not isinstance(arm, str) for arm in arms
    ):
        failures.append("arms: ordered list of five arm labels required")
    elif tuple(arms) != ALLOWED_ARMS:
        failures.append(
            "arms: exact matched order B000/F111/A011/A101/A110 required"
        )

    declared_claim = request.get("claim_ceiling")
    if declared_claim != CLAIM_CEILING:
        failures.append("claim_ceiling: trend-screen ceiling has drifted")

    if request.get("formal_training_authorized") is not False:
        failures.append("formal_training_authorized: explicit false required")

    exact_integer_fields = {
        "users": TREND_USERS,
        "epsilon_decay_episodes": TREND_EPSILON_DECAY_EPISODES,
        "target_update_every": TREND_TARGET_UPDATE_EVERY,
        "checkpoint_every_episodes": TREND_CHECKPOINT_EVERY_EPISODES,
        "specialist_bundle_replay_capacity": TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
    }
    for field, expected in exact_integer_fields.items():
        if type(request.get(field)) is not int or request.get(field) != expected:
            failures.append(f"{field}: fixed value {expected} required")

    evaluation_users = request.get("evaluation_users")
    if not isinstance(evaluation_users, (list, tuple)) or tuple(
        evaluation_users
    ) != TREND_EVALUATION_USERS:
        failures.append(
            "evaluation_users: fixed sweep 60/80/100/120/140 required"
        )
    if not _close(request.get("donor_beta"), TREND_DONOR_BETA):
        failures.append("donor_beta: fixed value 0.25 required")
    if not _close(request.get("acrm_eta"), TREND_ACRM_ETA):
        failures.append("acrm_eta: fixed value 1.0 required")

    return episodes, learning_rate


def _validate_fixed_seeds(request: Mapping[str, Any], failures: list[str]) -> dict[str, Any]:
    expected = {
        "training": TREND_TRAINING_SEED,
        "environment": TREND_ENVIRONMENT_SEED,
        "mobility": TREND_MOBILITY_SEED,
    }
    actual: dict[str, Any] = {}
    for name, value in expected.items():
        observed = _request_seed(request, name)
        if type(observed) is not int or observed != value:
            failures.append(f"seeds.{name}: fixed trend seed mismatch")
        actual[name] = observed

    raw_evaluation = request.get("evaluation_seeds")
    if not isinstance(raw_evaluation, (list, tuple)) or any(
        type(seed) is not int for seed in raw_evaluation
    ):
        failures.append("evaluation_seeds: five fixed integer seeds required")
        values: tuple[Any, ...] = tuple(raw_evaluation or ()) if isinstance(raw_evaluation, (list, tuple)) else ()
    else:
        values = tuple(raw_evaluation)
    if values != TREND_EVALUATION_SEEDS:
        failures.append("evaluation_seeds: fixed trend evaluation set mismatch")
    if len(set(values)) != len(values):
        failures.append("evaluation_seeds: duplicates are forbidden")
    actual["evaluation_seeds"] = list(values)
    return actual


def _validate_freeze(
    freeze_path: Path,
    *,
    repo: Path,
    failures: list[str],
) -> tuple[Mapping[str, Any] | None, str | None, Path | None, Path | None, Path | None]:
    if not freeze_path.is_file():
        failures.append(f"freeze manifest: file missing ({freeze_path})")
        return None, None, None, None, None
    freeze_sha = sha256_file(freeze_path)
    freeze = _json(freeze_path, label="freeze manifest", failures=failures)
    if freeze is None:
        return None, freeze_sha, None, None, None
    if freeze.get("schema") != FREEZE_SCHEMA:
        failures.append("freeze manifest: wrong V0.2 schema")
    if freeze.get("status") != FREEZE_STATUS:
        failures.append("freeze manifest: not frozen before support census")
    if freeze.get("public_method_name") != PUBLIC_METHOD_NAME:
        failures.append("freeze manifest: public method name drifted")
    if freeze.get("support_version") != SUPPORT_VERSION:
        failures.append("freeze manifest: support version drifted")
    if freeze.get("formal_training_authorized") is not False:
        failures.append("freeze manifest: formal training must remain false")

    spec_block = _mapping(freeze.get("spec"), label="freeze.spec", failures=failures)
    spec_path: Path | None = None
    if spec_block is not None:
        spec_path = _require_exact_path(
            spec_block.get("path"),
            repo / SPEC_RELATIVE,
            base=repo,
            label="freeze.spec",
            failures=failures,
        )
        if spec_path is not None:
            _bound_file(
                spec_path,
                spec_block.get("sha256"),
                base=repo,
                label="freeze.spec",
                failures=failures,
            )

    fixed = _mapping(freeze.get("fixed_inputs"), label="freeze.fixed_inputs", failures=failures)
    corpus_path: Path | None = None
    prereg_path = repo / CANONICAL_PREREG_RELATIVE
    if fixed is not None:
        tle_hash = fixed.get("tle_file_set_sha256")
        if tle_hash != CANONICAL_TLE_FILE_SET_SHA256:
            failures.append("freeze.fixed_inputs.tle_file_set_sha256: canonical hash mismatch")
        corpus = _mapping(
            fixed.get("c1_exp_corpus_manifest"),
            label="freeze.fixed_inputs.c1_exp_corpus_manifest",
            failures=failures,
        )
        if corpus is not None:
            corpus_path = _require_exact_path(
                corpus.get("path"),
                repo / C1_MANIFEST_RELATIVE,
                base=repo,
                label="freeze C1 EXP corpus manifest",
                failures=failures,
            )
            if corpus_path is not None:
                _bound_file(
                    corpus_path,
                    corpus.get("sha256"),
                    base=repo,
                    label="freeze C1 EXP corpus manifest",
                    failures=failures,
                )
        checkpoint = _mapping(
            fixed.get("baseline_checkpoint"),
            label="freeze.fixed_inputs.baseline_checkpoint",
            failures=failures,
        )
        if checkpoint is not None:
            _bound_file(
                checkpoint.get("path"),
                checkpoint.get("sha256"),
                base=repo,
                label="freeze baseline checkpoint",
                failures=failures,
            )

    if not prereg_path.is_file():
        failures.append(f"canonical preregistration: file missing ({prereg_path})")
    elif sha256_file(prereg_path) != CANONICAL_PREREG_SHA256:
        failures.append("canonical preregistration: fixed hash mismatch")
    return freeze, freeze_sha, spec_path, corpus_path, prereg_path


def _validate_support_receipt(
    support_path: Path,
    *,
    freeze_path: Path,
    freeze_sha: str | None,
    spec_path: Path,
    corpus_path: Path,
    prereg_path: Path,
    repo: Path,
    failures: list[str],
) -> tuple[Mapping[str, Any] | None, str | None]:
    if not support_path.is_file():
        failures.append(f"support census receipt: file missing ({support_path})")
        return None, None
    support_sha = sha256_file(support_path)
    payload = _json(support_path, label="support census receipt", failures=failures)
    if payload is None:
        return None, support_sha
    if payload.get("schema") != SUPPORT_SCHEMA:
        failures.append("support census receipt: wrong schema")
    if payload.get("status") != "PASS":
        failures.append("support census receipt: PASS required")
    if payload.get("support_version") != SUPPORT_VERSION:
        failures.append("support census receipt: V0.2 support version required")
    if payload.get("partition") != "TRAIN":
        failures.append("support census receipt: TRAIN partition required")
    ceiling = str(payload.get("evidence_ceiling", ""))
    if not ceiling.startswith("Pre-outcome support census only:"):
        failures.append("support census receipt: evidence ceiling drifted")
    roles = _mapping(payload.get("roles"), label="support census roles", failures=failures)
    if roles is not None:
        for role in ("C2", "C3"):
            row = _mapping(roles.get(role), label=f"support census roles.{role}", failures=failures)
            if row is None or row.get("floor_pass") is not True:
                failures.append(f"support census roles.{role}: PASS floor required")
    contract = _mapping(
        payload.get("eligibility_contract"),
        label="support census eligibility_contract",
        failures=failures,
    )
    if contract is not None:
        for field in (
            "reward_used",
            "successor_outcome_used",
            "counterfactual_used",
            "forecast_used",
            "specialist_outcome_used",
        ):
            if contract.get(field) is not False:
                failures.append(f"support census eligibility_contract.{field}: must be false")

    authority = _mapping(
        payload.get("authority"), label="support census authority", failures=failures
    )
    if authority is not None:
        if authority.get("path_binding") != REPOSITORY_PATH_BINDING:
            failures.append("support census authority.path_binding: portable binding required")
        bound_freeze = _require_exact_repo_receipt_path(
            authority.get("freeze_manifest"),
            freeze_path,
            repo=repo,
            label="support census authority.freeze_manifest",
            failures=failures,
        )
        if bound_freeze is not None and authority.get("freeze_manifest_sha256") != freeze_sha:
            failures.append("support census authority.freeze_manifest_sha256: current freeze mismatch")
        for raw, expected, label in (
            (authority.get("spec"), spec_path, "support census authority.spec"),
            (
                authority.get("c1_exp_corpus_manifest"),
                corpus_path,
                "support census authority.c1_exp_corpus_manifest",
            ),
            (authority.get("canonical_prereg"), prereg_path, "support census authority.canonical_prereg"),
        ):
            bound = _require_exact_repo_receipt_path(
                raw,
                expected,
                repo=repo,
                label=label,
                failures=failures,
            )
            if bound is not None:
                digest_field = {
                    "support census authority.spec": "spec_sha256",
                    "support census authority.c1_exp_corpus_manifest": "c1_exp_corpus_manifest_sha256",
                    "support census authority.canonical_prereg": "canonical_prereg_sha256",
                }[label]
                expected_hash = sha256_file(expected)
                if authority.get(digest_field) != expected_hash:
                    failures.append(f"{label}.{digest_field}: hash mismatch")
        if authority.get("tle_file_set_sha256") != CANONICAL_TLE_FILE_SET_SHA256:
            failures.append("support census authority.tle_file_set_sha256: fixed hash mismatch")
        if authority.get("tle_file_count") != CANONICAL_TLE_FILE_COUNT:
            failures.append("support census authority.tle_file_count: fixed count mismatch")
        if authority.get("tle_root_binding") != RUNTIME_TLE_ROOT_BINDING:
            failures.append("support census authority.tle_root_binding: runtime argument required")
        if "tle_root" in authority:
            failures.append("support census authority.tle_root: physical path forbidden")
        baseline = _strict_repo_receipt_path(
            authority.get("baseline_checkpoint"),
            repo=repo,
            label="support census authority.baseline_checkpoint",
            failures=failures,
        )
        if baseline is not None:
            _bound_file(
                baseline,
                authority.get("baseline_checkpoint_sha256"),
                base=repo,
                label="support census authority.baseline_checkpoint",
                failures=failures,
            )
        if authority.get("baseline_checkpoint_detached") is not True:
            failures.append("support census authority.baseline_checkpoint_detached: must be true")
        if authority.get("baseline_checkpoint_updated") is not False:
            failures.append("support census authority.baseline_checkpoint_updated: must be false")
    return payload, support_sha


def _validate_zero_dose_receipt(
    parity_path: Path,
    *,
    prereg_path: Path,
    tle_root: Path,
    repo: Path,
    freeze: Mapping[str, Any] | None,
    failures: list[str],
) -> tuple[Mapping[str, Any] | None, str | None]:
    if not parity_path.is_file():
        failures.append(f"zero-dose parity receipt: file missing ({parity_path})")
        return None, None
    parity_sha = sha256_file(parity_path)
    payload = _json(parity_path, label="zero-dose parity receipt", failures=failures)
    if payload is None:
        return None, parity_sha

    global validate_zero_dose_receipt
    checker = validate_zero_dose_receipt
    if checker is None:
        try:
            from check_zero_dose_parity import validate_receipt as checker
        except Exception as error:  # pragma: no cover - import depends on runtime env
            failures.append(
                "zero-dose parity receipt: independent checker unavailable "
                f"({type(error).__name__})"
            )
            checker = None
    if checker is not None:
        try:
            replayed = checker(parity_path, tle_root=tle_root)
        except Exception as error:
            failures.append(
                "zero-dose parity receipt: independent replay failed "
                f"({type(error).__name__})"
            )
            replayed = None
        if not isinstance(replayed, Mapping):
            failures.append("zero-dose parity receipt: replay must return an object")
        elif dict(replayed) != dict(payload):
            failures.append("zero-dose parity receipt: replay does not reproduce receipt")

    if payload.get("schema") != ZERO_DOSE_SCHEMA:
        failures.append("zero-dose parity receipt: wrong schema")
    if payload.get("status") != "PASS":
        failures.append("zero-dose parity receipt: PASS required")
    if payload.get("exact_after_descriptive_metadata_normalisation") is not True:
        failures.append("zero-dose parity receipt: exact parity required")
    if payload.get("first_difference") is not None:
        failures.append("zero-dose parity receipt: first_difference must be null")
    authority = _mapping(
        payload.get("authority"), label="zero-dose parity authority", failures=failures
    )
    if authority is not None:
        bound_prereg = _require_exact_repo_receipt_path(
            authority.get("prereg_path"),
            prereg_path,
            repo=repo,
            label="zero-dose parity authority.prereg_path",
            failures=failures,
        )
        if bound_prereg is not None and authority.get("prereg_sha256") != CANONICAL_PREREG_SHA256:
            failures.append("zero-dose parity authority.prereg_sha256: fixed hash mismatch")
        if authority.get("tle_file_set_sha256") != CANONICAL_TLE_FILE_SET_SHA256:
            failures.append("zero-dose parity authority.tle_file_set_sha256: fixed hash mismatch")
        if authority.get("tle_file_count") != CANONICAL_TLE_FILE_COUNT:
            failures.append("zero-dose parity authority.tle_file_count: fixed count mismatch")
        if authority.get("tle_root_binding") != RUNTIME_TLE_ROOT_BINDING:
            failures.append("zero-dose parity authority.tle_root_binding: runtime argument required")
        if "tle_root_path" in authority:
            failures.append("zero-dose parity authority.tle_root_path: physical path forbidden")
        runner = _require_exact_repo_receipt_path(
            authority.get("run_short_ep_path"),
            repo / RUNNER_RELATIVE,
            repo=repo,
            label="zero-dose parity authority.run_short_ep_path",
            failures=failures,
        )
        if runner is not None:
            actual_runner_sha = sha256_file(runner)
            if authority.get("run_short_ep_sha256") != actual_runner_sha:
                failures.append("zero-dose parity authority.run_short_ep_sha256: hash mismatch")
            implementation = _mapping(
                (freeze or {}).get("implementation"),
                label="freeze.implementation",
                failures=failures,
            )
            if implementation is not None and implementation.get(RUNNER_RELATIVE) != actual_runner_sha:
                failures.append("zero-dose parity authority.run_short_ep_sha256: freeze binding mismatch")
    return payload, parity_sha


def validate_intermediate_trend_authority(
    request: Mapping[str, Any],
    *,
    tle_root: Path,
    repo: Path = REPO,
) -> dict[str, Any]:
    """Validate and return the immutable authority for one trend screen.

    Required request fields are ``episodes``, ``learning_rate``, ``arms``,
    ``seeds`` (or the three top-level seed aliases), ``evaluation_seeds``,
    ``support_census_receipt``, and ``zero_dose_parity_receipt``.  The freeze,
    preregistration, and C1 manifest default to the current canonical files,
    but explicit paths are accepted only when they resolve to those same
    canonical files.

    The function returns a JSON-serialisable receipt-like dictionary.  It does
    not authorise a run if any evidence is absent, stale, or inconsistent.
    """

    if not isinstance(request, Mapping):
        raise IntermediateTrendAuthorityError(["request: object required"])
    root = Path(repo).expanduser().resolve()
    failures: list[str] = []
    episodes, learning_rate = _validate_request_shape(request, failures)
    seeds = _validate_fixed_seeds(request, failures)

    freeze_path = _path(
        request.get("freeze_manifest", DEFAULT_FREEZE),
        base=root,
        label="freeze manifest",
        failures=failures,
    )
    if freeze_path is None:
        freeze_path = (root / FREEZE_RELATIVE).resolve()
    expected_freeze = (root / FREEZE_RELATIVE).resolve()
    if freeze_path != expected_freeze:
        failures.append("freeze manifest: current V0.2 canonical path required")
    freeze, freeze_sha, spec_path, corpus_from_freeze, prereg_from_freeze = _validate_freeze(
        freeze_path,
        repo=root,
        failures=failures,
    )
    spec_path = spec_path or (root / SPEC_RELATIVE).resolve()
    corpus_path = corpus_from_freeze or (root / C1_MANIFEST_RELATIVE).resolve()
    prereg_path = prereg_from_freeze or (root / CANONICAL_PREREG_RELATIVE).resolve()

    requested_prereg = _path(
        request.get("prereg", prereg_path),
        base=root,
        label="canonical preregistration",
        failures=failures,
    )
    if requested_prereg != prereg_path.resolve():
        failures.append("canonical preregistration: current canonical path required")
    if requested_prereg is not None and requested_prereg.is_file() and sha256_file(requested_prereg) != CANONICAL_PREREG_SHA256:
        failures.append("canonical preregistration: fixed hash mismatch")
    prereg_path = requested_prereg or prereg_path

    requested_corpus = _path(
        request.get("c1_exp_corpus_manifest", corpus_path),
        base=root,
        label="C1 EXP corpus manifest",
        failures=failures,
    )
    if requested_corpus != corpus_path.resolve():
        failures.append("C1 EXP corpus manifest: current frozen path required")
    if requested_corpus is not None and not requested_corpus.is_file():
        failures.append("C1 EXP corpus manifest: file missing")
    corpus_path = requested_corpus or corpus_path

    raw_tle_hash = request.get("tle_file_set_sha256", CANONICAL_TLE_FILE_SET_SHA256)
    if raw_tle_hash != CANONICAL_TLE_FILE_SET_SHA256:
        failures.append("tle_file_set_sha256: fixed canonical TLE hash required")
    if requested_corpus is not None and requested_corpus.is_file():
        _validate_nested_c1_corpus(
            requested_corpus,
            tle_root=Path(tle_root),
            repo=root,
            failures=failures,
        )

    selection = _mapping(
        request.get("selection_plan"),
        label="selection_plan",
        failures=failures,
    )
    selection_path: Path | None = None
    if selection is not None:
        selection_path = _require_exact_path(
            selection.get("path"),
            root / SELECTION_PLAN_RELATIVE,
            base=root,
            label="selection_plan.path",
            failures=failures,
        )
        if selection.get("sha256") != SELECTION_PLAN_SHA256:
            failures.append("selection_plan.sha256: frozen plan hash mismatch")
        if selection_path is not None:
            _bound_file(
                selection_path,
                SELECTION_PLAN_SHA256,
                base=root,
                label="selection_plan",
                failures=failures,
            )

    support_path = _path(
        request.get("support_census_receipt"),
        base=root,
        label="support census receipt",
        failures=failures,
    )
    if support_path is None:
        support_sha = None
        support_payload = None
    else:
        support_payload, support_sha = _validate_support_receipt(
            support_path,
            freeze_path=freeze_path,
            freeze_sha=freeze_sha,
            spec_path=spec_path,
            corpus_path=corpus_path,
            prereg_path=prereg_path,
            repo=root,
            failures=failures,
        )

    parity_path = _path(
        request.get("zero_dose_parity_receipt"),
        base=root,
        label="zero-dose parity receipt",
        failures=failures,
    )
    if parity_path is None:
        parity_sha = None
        parity_payload = None
    else:
        parity_payload, parity_sha = _validate_zero_dose_receipt(
            parity_path,
            prereg_path=prereg_path,
            tle_root=Path(tle_root).expanduser().resolve(),
            repo=root,
            freeze=freeze,
            failures=failures,
        )

    evidence = {
        "freeze_manifest_sha256": freeze_sha,
        "support_census_receipt_sha256": support_sha,
        "zero_dose_parity_receipt_sha256": parity_sha,
        "support_status": support_payload.get("status") if support_payload else None,
        "zero_dose_status": parity_payload.get("status") if parity_payload else None,
    }
    if failures:
        raise IntermediateTrendAuthorityError(failures, evidence=evidence)

    assert episodes is not None
    assert learning_rate is not None
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "claim_ceiling": CLAIM_CEILING,
        "evidence_ceiling": EVIDENCE_CEILING,
        "episodes": episodes,
        "learning_rate": learning_rate,
        "arms": list(ALLOWED_ARMS),
        "seeds": seeds,
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
        "authority": {
            "freeze_manifest": str(freeze_path),
            "freeze_manifest_sha256": freeze_sha,
            "support_census_receipt": str(support_path) if support_path else None,
            "support_census_receipt_sha256": support_sha,
            "zero_dose_parity_receipt": str(parity_path) if parity_path else None,
            "zero_dose_parity_receipt_sha256": parity_sha,
            "canonical_prereg": str(prereg_path),
            "canonical_prereg_sha256": CANONICAL_PREREG_SHA256,
            "tle_file_set_sha256": CANONICAL_TLE_FILE_SET_SHA256,
            "c1_exp_corpus_manifest": str(corpus_path),
            "c1_exp_corpus_manifest_sha256": sha256_file(corpus_path),
            "selection_plan": str(selection_path),
            "selection_plan_sha256": SELECTION_PLAN_SHA256,
        },
    }


# Short alias for harnesses that prefer the noun used by the launch gate.
validate_trend_authority = validate_intermediate_trend_authority


__all__ = [
    "ALLOWED_ARMS",
    "ALLOWED_EPISODES",
    "ALLOWED_LEARNING_RATES",
    "CANONICAL_PREREG_SHA256",
    "CANONICAL_TLE_FILE_SET_SHA256",
    "CLAIM_CEILING",
    "EVIDENCE_CEILING",
    "IntermediateTrendAuthorityError",
    "SCHEMA",
    "SELECTION_PLAN_RELATIVE",
    "SELECTION_PLAN_SHA256",
    "TREND_ENVIRONMENT_SEED",
    "TREND_EPSILON_DECAY_EPISODES",
    "TREND_CHECKPOINT_EVERY_EPISODES",
    "TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY",
    "TREND_EVALUATION_SEEDS",
    "TREND_EVALUATION_USERS",
    "TREND_DONOR_BETA",
    "TREND_ACRM_ETA",
    "TREND_MOBILITY_SEED",
    "TREND_TARGET_UPDATE_EVERY",
    "TREND_TRAINING_SEED",
    "TREND_USERS",
    "sha256_file",
    "validate_intermediate_trend_authority",
    "validate_trend_authority",
]
