#!/usr/bin/env python3
"""Independently validate a C1 post-gate 4EP efficacy micro-screen receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from c1_exp_corpus import load_verified_c1_corpus, sha256_file  # noqa: E402
from c1_pretransfer_gate_validator import (  # noqa: E402
    C1PretransferGateValidationError,
    validate_c1_pretransfer_result,
)
from verify_c1_source_gate import verify_payload as verify_c1_source_gate  # noqa: E402
from check_zero_dose_parity import (  # noqa: E402
    _first_difference,
    compare_states,
    validate_receipt as validate_zero_dose_receipt,
)
from run_short_ep import (  # noqa: E402
    DEFAULT_ACRM_ETA,
    DEFAULT_LEARNING_RATE,
    _make_environment,
    _short_config,
)
from sweep_evaluation import evaluate_checkpoint_point  # noqa: E402
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)


RESULT_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-result-v1"
RAW_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-raw-v1"
SEED_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-seeds-v1"
CLOSURE_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-closure-v1"
DISJOINTNESS_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-disjointness-v1"
INVENTORY_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-pre-reveal-inventory-v1"
CAMPAIGN_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-single-campaign-v1"
EXECUTION_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-single-execution-v1"
CAMPAIGN_LEDGER = HERE / "c1-efficacy-microscreen-campaign-v1.json"
EXECUTION_LEDGER = HERE / "c1-efficacy-microscreen-execution-v1.json"
CLAIM_CEILING = "ONE_SEED_4EP_DIRECTIONAL_SCREEN_NOT_ROUTING_AUTHORITY_NOT_CHAPTER5"
SEED_NAMESPACE = "SMC-ER-C1-POSTGATE-EFFICACY-MICROSCREEN-V1"
EPISODES = 4
USERS = 100
EVALUATION_SEEDS = 5
SERVICE_GUARD = 0.005
MAIN_BATCH_SIZE = 128
EXPECTED_CHECKS = {
    "all_structural_guards",
    "mean_paired_delta_positive",
    "positive_on_at_least_four_seeds",
    "aggregate_ratio_of_sums_delta_positive",
    "served_fraction_guard",
}
BOUND_ARTIFACT_STEMS = (
    "prereg",
    "source_gate_result",
    "source_gate_verification",
    "corpus_manifest",
    "corpus_verification",
    "pretransfer_gate_result",
    "checkpoint",
    "seed_manifest",
    "execution_ledger",
    "raw_rows",
)
CLOSURE_TEST_RELATIVE_PATHS = (
    ".scratch/smc-er-short-ep/test_build_c1_exp_corpus.py",
    ".scratch/smc-er-short-ep/test_c1_exp_corpus.py",
    ".scratch/smc-er-short-ep/test_c1_consumer_gate.py",
    ".scratch/smc-er-short-ep/test_c1_efficacy_micro_screen_validator.py",
    ".scratch/smc-er-short-ep/test_c1_pretransfer_consumer_gate.py",
    ".scratch/smc-er-short-ep/test_c1_pretransfer_gate_validator.py",
    ".scratch/smc-er-short-ep/test_run_short_ep.py",
    ".scratch/smc-er-short-ep/test_smc_er_core.py",
    ".scratch/smc-er-short-ep/test_sweep_evaluation.py",
    ".scratch/smc-er-short-ep/test_verify_c1_source_gate.py",
    ".scratch/smc-er-short-ep/test_verify_c1_corrective_replay_addendum.py",
    ".scratch/smc-er-short-ep/test_freeze_c1_efficacy_micro_screen.py",
)


class C1EfficacyScreenValidationError(RuntimeError):
    def __init__(self, failures: Sequence[str], *, evidence: Mapping[str, Any] | None = None):
        self.failures = tuple(dict.fromkeys(map(str, failures)))
        self.evidence = dict(evidence or {})
        super().__init__("C1 efficacy-screen validation failed: " + "; ".join(self.failures))


def _json(path: Path, label: str, failures: list[str]) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: unreadable ({type(exc).__name__})")
        return None
    if not isinstance(value, Mapping):
        failures.append(f"{label}: object required")
        return None
    return value


def _resolve(value: Any, *, base: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _digest(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _close(left: Any, right: Any) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-9)
    except (TypeError, ValueError, OverflowError):
        return False


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _main_source_tree_binding(repo: Path = REPO) -> tuple[str, int]:
    """Independently hash the complete Python implementation under src/mcrl."""

    root = Path(repo).resolve() / "src" / "mcrl"
    rows = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]
    if not rows:
        raise C1EfficacyScreenValidationError(["Main source-tree authority is empty"])
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest(), len(rows)


def _closure_test_tree_binding(repo: Path = REPO) -> tuple[str, int]:
    """Independently hash the exact closure-test authority."""

    root = Path(repo).resolve()
    paths = [root / relative for relative in CLOSURE_TEST_RELATIVE_PATHS]
    if any(not path.is_file() for path in paths):
        raise C1EfficacyScreenValidationError(
            ["C1 closure-test authority is incomplete"]
        )
    rows = [
        {"path": relative, "sha256": sha256_file(path)}
        for relative, path in zip(CLOSURE_TEST_RELATIVE_PATHS, paths, strict=True)
    ]
    return hashlib.sha256(_canonical_bytes(rows)).hexdigest(), len(rows)


def _gate1_prior_seeds(pretransfer_gate: Path) -> set[int]:
    """Recover authenticated matched Gate-1 roots through exact zero-dose replay."""

    payload = json.loads(pretransfer_gate.read_text(encoding="utf-8"))
    authority = payload.get("authority") if isinstance(payload, Mapping) else None
    if not isinstance(authority, Mapping):
        raise RuntimeError("Gate 2 lacks authority")
    parity = _resolve(
        authority.get("zero_dose_parity_path"), base=pretransfer_gate.parent
    )
    if (
        parity is None
        or not parity.is_file()
        or authority.get("zero_dose_parity_sha256") != sha256_file(parity)
    ):
        raise RuntimeError("Gate 2 zero-dose authority mismatch")
    replayed = validate_zero_dose_receipt(parity)
    parity_authority = replayed.get("authority")
    if not isinstance(parity_authority, Mapping):
        raise RuntimeError("zero-dose replay lacks state authority")
    baseline = _resolve(
        parity_authority.get("baseline_state_path"), base=parity.parent
    )
    if (
        baseline is None
        or not baseline.is_file()
        or parity_authority.get("baseline_state_sha256") != sha256_file(baseline)
    ):
        raise RuntimeError("zero-dose baseline authority mismatch")
    state = torch.load(baseline, map_location="cpu", weights_only=False)
    if not isinstance(state, Mapping):
        raise RuntimeError("zero-dose baseline state malformed")
    values = [state.get(name) for name in ("train_seed", "env_seed", "mobility_seed")]
    if any(type(value) is not int or value < 0 for value in values):
        raise RuntimeError("zero-dose baseline seeds malformed")
    return set(map(int, values))


def _derive_candidate(closure_sha256: str, counter: int) -> int:
    return int.from_bytes(
        hashlib.sha256(
            _canonical_bytes([SEED_NAMESPACE, closure_sha256, int(counter)])
        ).digest()[:4],
        "big",
    )


def _runtime_derived_seeds(training_seed: int) -> dict[str, int]:
    return {
        "C1_specialist": int(training_seed) + 10_001,
        "C2_specialist": int(training_seed) + 20_003,
        "C3_specialist": int(training_seed) + 30_007,
    }


def _repo_matches(seed: int, repo: Path = REPO) -> tuple[str, ...]:
    completed = subprocess.run(
        [
            "rg", "-l", "--hidden", "--no-ignore",
            "--glob", "!.git/**", "--glob", "!.venv/**",
            "--glob", "!.pytest_cache/**", "--glob", "!.mypy_cache/**",
            "--glob", "!.ruff_cache/**", "--glob", "!__pycache__/**",
            "--glob", "!*.pyc",
            "--glob", "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-campaign-v1.json",
            "--glob", "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-execution-v1.json",
            "--pcre2", rf"(?<![0-9]){int(seed)}(?![0-9])", str(Path(repo).resolve()),
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise C1EfficacyScreenValidationError(
            [f"repository disjointness search failed: {completed.stderr}"]
        )
    return tuple(line for line in completed.stdout.splitlines() if line)


def _numeric_inventory(repo: Path = REPO) -> tuple[str, int]:
    completed = subprocess.run(
        [
            "rg", "-o", "--no-filename", "--hidden", "--no-ignore",
            "--glob", "!.git/**", "--glob", "!.venv/**",
            "--glob", "!.pytest_cache/**", "--glob", "!.mypy_cache/**",
            "--glob", "!.ruff_cache/**", "--glob", "!__pycache__/**",
            "--glob", "!*.pyc",
            "--glob", "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-campaign-v1.json",
            "--glob", "!.scratch/smc-er-short-ep/c1-efficacy-microscreen-execution-v1.json",
            "--pcre2", r"(?<![0-9])[0-9]{1,20}(?![0-9])", str(Path(repo).resolve()),
        ],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise C1EfficacyScreenValidationError(
            [f"repository numeric inventory failed: {completed.stderr}"]
        )
    tokens = sorted({int(line) for line in completed.stdout.splitlines() if line})
    return hashlib.sha256(_canonical_bytes(tokens)).hexdigest(), len(tokens)


def _canonical_authorities(repo: Path) -> dict[str, Path]:
    short = repo / ".scratch" / "smc-er-short-ep"
    return {
        "spec": short / "C1-MAIN-CONSUMER-GATE-V1-SPEC-2026-08-28.md",
        "runner": short / "run_c1_consumer_gate.py",
        "test": short / "test_c1_consumer_gate.py",
        "validator": short / "c1_efficacy_micro_screen_validator.py",
        "validator_test": short / "test_c1_efficacy_micro_screen_validator.py",
        "freeze": short / "freeze_c1_efficacy_micro_screen.py",
        "freeze_test": short / "test_freeze_c1_efficacy_micro_screen.py",
        "method": repo / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md",
        "concept": repo / "docs" / "MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md",
        "run_short_ep": short / "run_short_ep.py",
        "routing_core": short / "smc_er_core.py",
        "roles": short / "smc_er_roles.py",
        "corpus_loader": short / "c1_exp_corpus.py",
        "sweep_evaluator": short / "sweep_evaluation.py",
        "parity_checker": short / "check_zero_dose_parity.py",
        "pretransfer_validator": short / "c1_pretransfer_gate_validator.py",
        "source_gate_verifier": short / "verify_c1_source_gate.py",
        "corrective_replay_addendum": short
        / "C1-CANONICAL-TLE-CORRECTIVE-REPLAY-ADDENDUM-V1-2026-08-28.json",
        "corrective_replay_verifier": short
        / "verify_c1_corrective_replay_addendum.py",
        "corrective_replay_verifier_test": short
        / "test_verify_c1_corrective_replay_addendum.py",
        "source_seed_provenance_correction": short
        / "C1-SOURCE-GATE-A-SEED-PROVENANCE-CORRECTION-V1-2026-08-28.json",
    }


def _validate_source_gate_verification(
    source_gate: Path,
    source_gate_verification: Path,
    failures: list[str],
) -> bool:
    """Independently replay Source Gate A and compare the whole receipt."""

    source_payload = _json(source_gate, "source_gate_result", failures)
    recorded = _json(
        source_gate_verification, "source_gate_verification", failures
    )
    if source_payload is None or recorded is None:
        return False
    addendum_path = _resolve(
        recorded.get("corrective_replay_addendum_path"),
        base=source_gate_verification.parent,
    )
    corrective_verification_path = _resolve(
        recorded.get("corrective_replay_verification_path"),
        base=source_gate_verification.parent,
    )
    seed_correction_path = _resolve(
        recorded.get("source_seed_provenance_correction_path"),
        base=source_gate_verification.parent,
    )
    try:
        reproduced = verify_c1_source_gate(
            source_payload,
            source_gate_path=source_gate,
            corrective_addendum=addendum_path,
            corrective_replay_verification=corrective_verification_path,
            source_seed_provenance_correction=seed_correction_path,
        )
    except Exception as exc:
        failures.append(
            "source_gate_verification: independent replay failed "
            f"({type(exc).__name__}: {exc})"
        )
        return False
    if recorded.get("status") != "PASS" or dict(recorded) != reproduced:
        failures.append("source_gate_verification: exact current replay mismatch")
        return False
    return True


def _bound_file(
    authority: Mapping[str, Any],
    stem: str,
    *,
    base: Path,
    result_path: Path,
    failures: list[str],
) -> Path | None:
    path = _resolve(authority.get(stem + "_path"), base=base)
    expected = authority.get(stem + "_sha256")
    if path is None or not path.is_file():
        failures.append(f"authority.{stem}_path: missing")
        return None
    if path == result_path:
        failures.append(f"authority.{stem}_path: self-reference forbidden")
        return None
    if not _digest(expected) or sha256_file(path) != expected:
        failures.append(f"authority.{stem}_sha256: mismatch")
        return None
    return path


def _validate_endpoint(
    value: Any,
    *,
    label: str,
    branch: str,
    checkpoint_sha: str,
    training_seed: int,
    evaluation_seed: int,
    failures: list[str],
) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        failures.append(f"{label}: missing")
        return None
    integer_fields = (
        "training_seed",
        "evaluation_seed",
        "users",
        "steps",
        "served_user_intervals",
        "total_user_intervals",
        "zero_power_intervals",
        "zero_service_intervals",
    )
    finite_fields = (
        "duration_s",
        "useful_bits",
        "system_energy_j",
        "system_ee_bits_per_j",
        "mean_system_power_w",
        "mean_system_throughput_bps",
        "served_fraction",
        "r1_sum",
        "r2_sum",
        "r3_sum",
    )
    if value.get("arm") != branch:
        failures.append(f"{label}.arm: mismatch")
    if value.get("checkpoint_sha256") != checkpoint_sha:
        failures.append(f"{label}.checkpoint_sha256: mismatch")
    if value.get("training_seed") != training_seed:
        failures.append(f"{label}.training_seed: mismatch")
    if value.get("evaluation_seed") != evaluation_seed:
        failures.append(f"{label}.evaluation_seed: mismatch")
    if value.get("users") != USERS:
        failures.append(f"{label}.users: mismatch")
    if any(type(value.get(field)) is not int for field in integer_fields):
        failures.append(f"{label}: integer surface malformed")
    if any(not _finite(value.get(field)) for field in finite_fields):
        failures.append(f"{label}: non-finite surface")
        return value
    steps = int(value.get("steps", 0))
    users = int(value.get("users", 0))
    duration = float(value.get("duration_s", 0.0))
    bits = float(value.get("useful_bits", 0.0))
    energy = float(value.get("system_energy_j", 0.0))
    served = int(value.get("served_user_intervals", 0))
    total = int(value.get("total_user_intervals", 0))
    if steps != 10 or duration <= 0.0 or bits < 0.0 or energy < 0.0:
        failures.append(f"{label}: physical denominator mismatch")
    if total != steps * users or not 0 <= served <= total:
        failures.append(f"{label}: service denominator mismatch")
    expected_ee = bits / energy if energy else 0.0
    expected_service = served / total if total else 0.0
    if energy == 0.0 and bits != 0.0:
        failures.append(f"{label}: positive bits with zero energy")
    for field, expected in (
        ("system_ee_bits_per_j", expected_ee),
        ("mean_system_power_w", energy / duration if duration else 0.0),
        ("mean_system_throughput_bps", bits / duration if duration else 0.0),
        ("served_fraction", expected_service),
    ):
        if not _close(value.get(field), expected):
            failures.append(f"{label}.{field}: identity mismatch")
    return value


def _initial_state(
    *,
    archive: TleArchive,
    config: Any,
    train_seed: int,
    env_seed: int,
    mobility_seed: int,
) -> Mapping[str, Any]:
    environment = _make_environment(archive, users=USERS)
    trainer = MODQNTrainer(
        environment,
        config,
        train_seed=train_seed,
        env_seed=env_seed,
        mobility_seed=mobility_seed,
        device="cpu",
    )
    return trainer.training_state_dict()


def _compare_endpoint_payloads(
    declared: Mapping[str, Any],
    replayed: Mapping[str, Any],
    *,
    label: str,
    failures: list[str],
) -> None:
    if set(declared) != set(replayed):
        failures.append(f"{label}: endpoint field surface mismatch")
        return
    for field, expected in replayed.items():
        actual = declared.get(field)
        if isinstance(expected, float):
            if not _close(actual, expected):
                failures.append(f"{label}.{field}: deterministic replay mismatch")
        elif actual != expected:
            failures.append(f"{label}.{field}: deterministic replay mismatch")


def _validate_schedule(
    *,
    branch_dir: Path,
    result: Mapping[str, Any],
    declared: Any,
    label: str,
    failures: list[str],
) -> dict[str, Any]:
    receipt_path = branch_dir / "main-update-receipts.json"
    episode_path = branch_dir / "episode-logs.json"
    specialist_path = branch_dir / "specialist-replay-receipts.json"
    receipt_payload = _json_list(receipt_path, f"{label}.main_receipts", failures)
    episode_payload = _json_list(episode_path, f"{label}.episode_logs", failures)
    specialist_payload = _json_list(
        specialist_path, f"{label}.specialist_receipts", failures
    )
    expected_count = EPISODES * 10
    admitted_bundle_ids: list[str] = []
    applied_bundle_ids: list[str] = []
    warmup_indices: list[int] = []
    update_indices: list[int] = []
    if len(receipt_payload) != expected_count:
        failures.append(f"{label}.main_receipts: denominator mismatch")
    for index, row in enumerate(receipt_payload):
        if not isinstance(row, Mapping):
            failures.append(f"{label}.main_receipts[{index}]: malformed")
            continue
        if row.get("episode") != index // 10 or row.get("step") != index % 10:
            failures.append(f"{label}.main_receipts[{index}]: order mismatch")
        quota = row.get("quota_receipt")
        if not isinstance(quota, Mapping):
            failures.append(f"{label}.main_receipts[{index}].quota: missing")
            continue
        ids = quota.get("specialist_bundle_ids")
        admitted = quota.get("admitted_specialist_bundle_ids")
        if (
            not isinstance(admitted, list)
            or len(admitted) != 1
            or not isinstance(admitted[0], str)
            or not admitted[0]
        ):
            failures.append(f"{label}.main_receipts[{index}]: C1 admission mismatch")
        else:
            admitted_bundle_ids.append(admitted[0])
        replay_size = quota.get("main_replay_size_before_update")
        batch_size = quota.get("main_batch_size")
        if (
            type(replay_size) is not int
            or replay_size < 0
            or batch_size != MAIN_BATCH_SIZE
            or quota.get("requested_source_units") != ["Main", "C1"]
            or quota.get("main_bundle_id") != row.get("main_bundle_id")
            or quota.get("missing_source_ids") != []
        ):
            failures.append(f"{label}.main_receipts[{index}]: quota surface mismatch")
            continue
        if replay_size < batch_size:
            warmup_indices.append(index)
            if (
                quota.get("mode") != "warmup_no_update"
                or quota.get("source_units") != []
                or ids != []
                or quota.get("canonical_replay_rng_sample_consumed") is not False
                or quota.get("unusable_specialist_bundle_ids") != []
            ):
                failures.append(f"{label}.main_receipts[{index}]: warmup mismatch")
        else:
            update_indices.append(index)
            if (
                quota.get("mode") != "source_unit_mean"
                or quota.get("source_units") != ["Main", "C1"]
                or quota.get("unit_definition") != "one_complete_atomic_bundle_per_source"
                or ids != admitted
                or quota.get("unusable_specialist_bundle_ids") != []
                or quota.get("canonical_replay_rng_sample_consumed") is not True
            ):
                failures.append(f"{label}.main_receipts[{index}]: unit schedule mismatch")
            elif isinstance(ids, list) and ids:
                applied_bundle_ids.append(ids[0])
    if (
        not warmup_indices
        or warmup_indices != list(range(len(warmup_indices)))
        or update_indices != list(range(len(warmup_indices), expected_count))
    ):
        failures.append(f"{label}.main_receipts: warmup must be one prefix")
    if (
        len(admitted_bundle_ids) != expected_count
        or len(set(admitted_bundle_ids)) != expected_count
    ):
        failures.append(f"{label}.main_receipts: admitted bundle IDs not unique")
    if (
        len(applied_bundle_ids) != len(update_indices)
        or len(set(applied_bundle_ids)) != len(update_indices)
        or applied_bundle_ids
        != [admitted_bundle_ids[index] for index in update_indices]
    ):
        failures.append(f"{label}.main_receipts: applied bundle lineage mismatch")
    expected_ledger = {"C1": "route", "C2": "shadow", "C3": "shadow"}
    if len(episode_payload) != EPISODES:
        failures.append(f"{label}.episode_logs: denominator mismatch")
    comparator_by_episode: dict[int, str] = {}
    for index, row in enumerate(episode_payload):
        comparator = row.get("frozen_main_comparator_sha256") if isinstance(row, Mapping) else None
        if (
            not isinstance(row, Mapping)
            or row.get("episode") != index
            or row.get("main_update_count") != 10
            or row.get("gate_ledger") != expected_ledger
            or not _digest(comparator)
        ):
            failures.append(f"{label}.episode_logs[{index}]: schedule mismatch")
        else:
            comparator_by_episode[index] = str(comparator)
    if len(set(comparator_by_episode.values())) != EPISODES:
        failures.append(f"{label}.episode_logs: comparator must be per block")
    c1_receipts = [
        row
        for row in specialist_payload
        if isinstance(row, Mapping) and row.get("source") == "C1"
    ]
    if len(c1_receipts) != expected_count:
        failures.append(f"{label}.specialist_receipts: C1 denominator mismatch")
    for index, row in enumerate(c1_receipts):
        episode = index // 10
        step = index % 10
        expected_id = (
            admitted_bundle_ids[index]
            if index < len(admitted_bundle_ids)
            else None
        )
        if (
            row.get("episode") != episode
            or row.get("step") != step
            or row.get("collected_bundle_id") != expected_id
            or row.get("comparator_block") != episode
            or row.get("frozen_main_comparator_sha256")
            != comparator_by_episode.get(episode)
        ):
            failures.append(f"{label}.specialist_receipts[{index}]: comparator lineage mismatch")
    dashboard = result.get("source_dashboard")
    if not isinstance(dashboard, Mapping):
        failures.append(f"{label}.source_dashboard: missing")
    else:
        if not isinstance(dashboard.get("C1"), Mapping) or dashboard["C1"].get("routed_bundles") != expected_count:
            failures.append(f"{label}.source_dashboard.C1: routed denominator mismatch")
        for source in ("C2", "C3"):
            if not isinstance(dashboard.get(source), Mapping) or dashboard[source].get("routed_bundles") != 0:
                failures.append(f"{label}.source_dashboard.{source}: must remain shadow")
    if result.get("consumed_specialist_bundle_count") != expected_count:
        failures.append(f"{label}.consumed_specialist_bundle_count: mismatch")
    if not isinstance(declared, Mapping):
        failures.append(f"raw.schedule_receipts.{label}: missing")
    else:
        expected_declared = {
            "branch": label,
            "status": "PASS",
            "logical_steps": expected_count,
            "warmup_steps": len(warmup_indices),
            "warmup_indices": warmup_indices,
            "source_unit_updates": len(update_indices),
            "source_unit_update_indices": update_indices,
            "unique_admitted_c1_bundle_ids": len(set(admitted_bundle_ids)),
            "unique_applied_c1_bundle_ids": len(set(applied_bundle_ids)),
            "main_update_receipts_path": str(receipt_path),
            "main_update_receipts_sha256": sha256_file(receipt_path) if receipt_path.is_file() else None,
            "episode_logs_path": str(episode_path),
            "episode_logs_sha256": sha256_file(episode_path) if episode_path.is_file() else None,
            "specialist_replay_receipts_path": str(specialist_path),
            "specialist_replay_receipts_sha256": sha256_file(specialist_path) if specialist_path.is_file() else None,
            "failures": [],
        }
        if dict(declared) != expected_declared:
            failures.append(f"raw.schedule_receipts.{label}: recomputation mismatch")
    return {
        "admitted_bundle_ids": admitted_bundle_ids,
        "applied_bundle_ids": applied_bundle_ids,
        "warmup_indices": warmup_indices,
        "update_indices": update_indices,
    }


def _validate_branch_artifacts(
    *,
    label: str,
    expected_arm: str,
    expected_config: Any,
    branch: Mapping[str, Any],
    raw_dir: Path,
    training_seed: int,
    environment_seed: int,
    mobility_seed: int,
    runtime_derived_seeds: Mapping[str, int],
    schedule: Mapping[str, Any],
    failures: list[str],
) -> tuple[Path | None, Any | None]:
    """Authenticate a final policy and the richer resumable carrier state."""

    checkpoint_path = _resolve(branch.get("checkpoint"), base=raw_dir)
    if (
        checkpoint_path is None
        or not checkpoint_path.is_file()
        or branch.get("checkpoint_sha256") != sha256_file(checkpoint_path)
    ):
        failures.append(f"raw.branch_results.{label}: checkpoint mismatch")
        return None, None
    try:
        checkpoint = read_checkpoint(checkpoint_path, map_location="cpu")
    except Exception as exc:
        failures.append(
            f"raw.branch_results.{label}: checkpoint unreadable "
            f"({type(exc).__name__}: {exc})"
        )
        return checkpoint_path, None

    expected_config_payload = asdict(expected_config)
    if (
        int(checkpoint.train_seed) != training_seed
        or int(checkpoint.env_seed) != environment_seed
        or int(checkpoint.mobility_seed) != mobility_seed
        or checkpoint.checkpoint_kind != "final-episode-policy"
        or int(checkpoint.episode) != EPISODES - 1
        or checkpoint.trainer_config != expected_config_payload
        or checkpoint.trainer_config.get("training_experiment_id") != expected_arm
        or not isinstance(checkpoint.q_networks, list)
        or len(checkpoint.q_networks) != 3
        or not isinstance(checkpoint.target_networks, list)
        or len(checkpoint.target_networks) != 3
        or not isinstance(checkpoint.optimizers, list)
        or len(checkpoint.optimizers) != 3
    ):
        failures.append(f"raw.branch_results.{label}: checkpoint contract mismatch")

    carrier_path = _resolve(branch.get("carrier_state"), base=raw_dir)
    if (
        carrier_path is None
        or not carrier_path.is_file()
        or branch.get("carrier_state_sha256") != sha256_file(carrier_path)
    ):
        failures.append(f"raw.branch_results.{label}: carrier-state mismatch")
        return checkpoint_path, checkpoint
    try:
        carrier = torch.load(carrier_path, map_location="cpu", weights_only=False)
    except Exception as exc:
        failures.append(
            f"raw.branch_results.{label}: carrier-state unreadable "
            f"({type(exc).__name__}: {exc})"
        )
        return checkpoint_path, checkpoint
    expected_gates = {"C1": "route", "C2": "shadow", "C3": "shadow"}
    if (
        not isinstance(carrier, Mapping)
        or carrier.get("schema") != "smc-er-carrier-state-v1"
        or carrier.get("episodes_completed") != EPISODES
        or carrier.get("gates") != expected_gates
    ):
        failures.append(f"raw.branch_results.{label}: carrier-state header mismatch")
        return checkpoint_path, checkpoint

    main_state = carrier.get("main_training_state")
    if not isinstance(main_state, Mapping) or (
        main_state.get("train_seed") != training_seed
        or main_state.get("env_seed") != environment_seed
        or main_state.get("mobility_seed") != mobility_seed
        or main_state.get("trainer_config") != expected_config_payload
    ):
        failures.append(f"raw.branch_results.{label}: carrier Main state mismatch")
    else:
        for field in ("q_networks", "target_networks", "optimizers"):
            difference = _first_difference(
                main_state.get(field), getattr(checkpoint, field), f"root.{field}"
            )
            if difference is not None:
                failures.append(
                    f"raw.branch_results.{label}: carrier/checkpoint drift ({difference})"
                )

    specialists = carrier.get("specialists")
    expected_objectives = {"C1": 0, "C2": 1, "C3": 2}
    if not isinstance(specialists, Mapping) or set(specialists) != set(expected_objectives):
        failures.append(f"raw.branch_results.{label}: specialist state surface mismatch")
    else:
        for source, objective in expected_objectives.items():
            state = specialists.get(source)
            if (
                not isinstance(state, Mapping)
                or state.get("objective_index") != objective
                or state.get("seed") != runtime_derived_seeds.get(source + "_specialist")
                or "rng_state" not in state
                or "replay_rng_state" not in state
            ):
                failures.append(
                    f"raw.branch_results.{label}: {source} specialist lineage mismatch"
                )

    bundle_replays = carrier.get("bundle_replays")
    expected_replay_sources = {"Main", *expected_objectives}
    if (
        not isinstance(bundle_replays, Mapping)
        or set(bundle_replays) != expected_replay_sources
    ):
        failures.append(f"raw.branch_results.{label}: bundle replay surface mismatch")
    else:
        for source, state in bundle_replays.items():
            if (
                not isinstance(state, Mapping)
                or state.get("format_version") != 1
                or not isinstance(state.get("items"), list)
                or not isinstance(state.get("seen"), list)
            ):
                failures.append(
                    f"raw.branch_results.{label}: {source} bundle replay malformed"
                )

    consumed = carrier.get("main_consumed_specialist_bundles")
    admitted = schedule.get("admitted_bundle_ids")
    if (
        not isinstance(consumed, Mapping)
        or consumed.get("format_version") != 1
        or not isinstance(admitted, list)
        or consumed.get("seen_bundle_ids") != sorted(admitted)
        or len(set(admitted)) != EPISODES * 10
    ):
        failures.append(f"raw.branch_results.{label}: consumed ledger mismatch")

    source_rng_states = carrier.get("source_rng_states")
    if not isinstance(source_rng_states, Mapping) or set(source_rng_states) != {
        "Main", "C1", "C2", "C3"
    }:
        failures.append(f"raw.branch_results.{label}: source RNG surface mismatch")
    else:
        for source, state in source_rng_states.items():
            if not isinstance(state, Mapping) or set(state) != {"environment", "mobility"}:
                failures.append(
                    f"raw.branch_results.{label}: {source} source RNG state malformed"
                )
    return checkpoint_path, checkpoint


def _json_list(path: Path, label: str, failures: list[str]) -> list[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: unreadable ({type(exc).__name__})")
        return []
    if not isinstance(value, list):
        failures.append(f"{label}: list required")
        return []
    return value


def _recompute_decision(
    paired: Sequence[Mapping[str, Any]], guard_failures: Sequence[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    deltas = [
        float(row["informed"]["system_ee_bits_per_j"])
        - float(row["neutral"]["system_ee_bits_per_j"])
        for row in paired
    ]
    informed_bits = math.fsum(float(row["informed"]["useful_bits"]) for row in paired)
    informed_energy = math.fsum(float(row["informed"]["system_energy_j"]) for row in paired)
    neutral_bits = math.fsum(float(row["neutral"]["useful_bits"]) for row in paired)
    neutral_energy = math.fsum(float(row["neutral"]["system_energy_j"]) for row in paired)
    informed_served = sum(int(row["informed"]["served_user_intervals"]) for row in paired)
    informed_total = sum(int(row["informed"]["total_user_intervals"]) for row in paired)
    neutral_served = sum(int(row["neutral"]["served_user_intervals"]) for row in paired)
    neutral_total = sum(int(row["neutral"]["total_user_intervals"]) for row in paired)
    informed_ee = informed_bits / informed_energy if informed_energy else 0.0
    neutral_ee = neutral_bits / neutral_energy if neutral_energy else 0.0
    informed_service = informed_served / informed_total if informed_total else 0.0
    neutral_service = neutral_served / neutral_total if neutral_total else 0.0
    checks = {
        "all_structural_guards": not guard_failures,
        "mean_paired_delta_positive": math.fsum(deltas) / EVALUATION_SEEDS > 0.0,
        "positive_on_at_least_four_seeds": sum(delta > 0.0 for delta in deltas) >= 4,
        "aggregate_ratio_of_sums_delta_positive": informed_ee > neutral_ee,
        "served_fraction_guard": informed_service >= neutral_service - SERVICE_GUARD,
    }
    metrics = {
        "paired_deltas_bits_per_j": deltas,
        "mean_paired_delta_bits_per_j": math.fsum(deltas) / EVALUATION_SEEDS,
        "positive_seed_count": sum(delta > 0.0 for delta in deltas),
        "informed_ratio_of_sums_ee_bits_per_j": informed_ee,
        "neutral_ratio_of_sums_ee_bits_per_j": neutral_ee,
        "aggregate_delta_bits_per_j": informed_ee - neutral_ee,
        "informed_served_fraction": informed_service,
        "neutral_served_fraction": neutral_service,
        "served_fraction_delta": informed_service - neutral_service,
    }
    return checks, metrics


def _validate_seed_provenance(
    *,
    seed_path: Path,
    seed_manifest: Mapping[str, Any],
    expected_bindings: Mapping[str, Any],
    known_prior_seeds: set[int],
    checkpoint_seeds: set[int],
    gate1_seeds: set[int],
    failures: list[str],
) -> tuple[int, list[int]]:
    """Independently authenticate closure, search, and all eight seed roots."""

    scalar = [
        seed_manifest.get(name)
        for name in ("training_seed", "environment_seed", "mobility_seed")
    ]
    evaluation = seed_manifest.get("evaluation_seeds")
    if (
        any(type(value) is not int or value < 0 for value in scalar)
        or not isinstance(evaluation, list)
        or len(evaluation) != EVALUATION_SEEDS
        or any(type(value) is not int or value < 0 for value in evaluation)
    ):
        failures.append("seed_manifest: seed denominator malformed")
        return -1, []
    all_seeds = [*map(int, scalar), *map(int, evaluation)]
    if (
        seed_manifest.get("seed_count") != 8
        or len(set(all_seeds)) != 8
        or set(all_seeds) & known_prior_seeds
        or seed_manifest.get("forbidden_checkpoint_seeds")
        != sorted(checkpoint_seeds)
        or seed_manifest.get("forbidden_gate1_seeds") != sorted(gate1_seeds)
        or seed_manifest.get("derivation")
        != "first eight collision-free uint32 values from closure-bound counter-separated SHA-256"
        or seed_manifest.get("repository_disjointness_checked_before_reveal") is not True
    ):
        failures.append("seed_manifest: denominator, exclusion, or derivation mismatch")
    runtime_derived = _runtime_derived_seeds(all_seeds[0])
    if (
        seed_manifest.get("runtime_derived_seeds") != runtime_derived
        or len(set(runtime_derived.values())) != 3
        or set(runtime_derived.values()) & (known_prior_seeds | set(all_seeds))
    ):
        failures.append("seed_manifest: runtime-derived seed collision")

    def bound_json(path_field: str, sha_field: str) -> tuple[Path | None, Mapping[str, Any] | None]:
        target = _resolve(seed_manifest.get(path_field), base=seed_path.parent)
        if (
            target is None
            or not target.is_file()
            or seed_manifest.get(sha_field) != sha256_file(target)
        ):
            failures.append(f"seed_manifest.{path_field}: missing or hash mismatch")
            return None, None
        return target, _json(target, path_field, failures)

    closure_path, closure = bound_json(
        "closure_manifest_path", "closure_manifest_sha256"
    )
    inventory_path, inventory = bound_json(
        "pre_reveal_inventory_path", "pre_reveal_inventory_sha256"
    )
    search_path, search = bound_json(
        "disjointness_search_receipt_path", "disjointness_search_receipt_sha256"
    )
    campaign_path, campaign = bound_json(
        "campaign_ledger_path", "campaign_ledger_sha256"
    )
    if campaign_path != CAMPAIGN_LEDGER.resolve():
        failures.append("seed_manifest.campaign_ledger_path: noncanonical")
    if closure is None or closure_path is None or (
        closure.get("schema") != CLOSURE_SCHEMA
        or closure.get("status") != "CLOSED_BEFORE_SEED_DERIVATION"
        or closure.get("claim_ceiling") != CLAIM_CEILING
        or closure.get("bindings") != dict(expected_bindings)
    ):
        failures.append("closure_manifest: invalid")
    else:
        test_receipt = closure.get("test_receipt")
        if (
            not isinstance(test_receipt, Mapping)
            or test_receipt.get("exit_code") != 0
            or test_receipt.get("wall_clock_text_excluded_from_seed_material") is not True
            or not isinstance(test_receipt.get("normalised_stdout"), str)
            or test_receipt.get("normalised_stdout_sha256")
            != hashlib.sha256(
                test_receipt.get("normalised_stdout", "").encode("utf-8")
            ).hexdigest()
        ):
            failures.append("closure_manifest.test_receipt: invalid")
    live_inventory_sha, live_inventory_count = _numeric_inventory()
    inventory_ref = closure.get("pre_reveal_inventory") if closure else None
    if inventory is None or inventory_path is None or (
        inventory.get("schema") != INVENTORY_SCHEMA
        or inventory.get("status") != "CAPTURED_BEFORE_SEED_DERIVATION"
        or inventory.get("claim_ceiling") != CLAIM_CEILING
        or inventory.get("numeric_token_set_sha256") != live_inventory_sha
        or inventory.get("numeric_token_count") != live_inventory_count
        or not isinstance(inventory_ref, Mapping)
        or _resolve(inventory_ref.get("path"), base=closure_path.parent if closure_path else seed_path.parent)
        != inventory_path
        or inventory_ref.get("sha256") != sha256_file(inventory_path)
        or inventory_ref.get("numeric_token_set_sha256") != live_inventory_sha
        or inventory_ref.get("numeric_token_count") != live_inventory_count
    ):
        failures.append("pre_reveal_inventory: not independently reproducible")
    if campaign is None or closure_path is None or campaign_path is None or (
        campaign.get("schema") != CAMPAIGN_SCHEMA
        or campaign.get("status") != "SEALED_SINGLE_CAMPAIGN_BEFORE_SEED_REVEAL"
        or campaign.get("claim_ceiling") != CLAIM_CEILING
        or _resolve(campaign.get("closure_manifest_path"), base=campaign_path.parent)
        != closure_path
        or campaign.get("closure_manifest_sha256") != sha256_file(closure_path)
        or _resolve(campaign.get("seed_manifest_path"), base=campaign_path.parent)
        != seed_path
        or _resolve(campaign.get("execution_ledger_path"), base=campaign_path.parent)
        != EXECUTION_LEDGER.resolve()
        or campaign.get("no_second_freeze_or_execution_is_authorised") is not True
    ):
        failures.append("campaign_ledger: invalid")
    if _resolve(seed_manifest.get("execution_ledger_path"), base=seed_path.parent) != EXECUTION_LEDGER.resolve():
        failures.append("seed_manifest.execution_ledger_path: noncanonical")
    if search is None or search_path is None or closure_path is None or inventory_path is None:
        failures.append("disjointness_receipt: missing prerequisites")
        return all_seeds[0], list(map(int, evaluation))
    if (
        search.get("schema") != DISJOINTNESS_SCHEMA
        or search.get("status") != "PASS"
        or search.get("seed_namespace") != SEED_NAMESPACE
        or search.get("closure_manifest_sha256") != sha256_file(closure_path)
        or search.get("selected_seeds") != all_seeds
        or search.get("runtime_derived_seeds") != runtime_derived
        or search.get("known_prior_seed_values") != sorted(known_prior_seeds)
        or search.get("known_prior_seed_values_sha256")
        != hashlib.sha256(_canonical_bytes(sorted(known_prior_seeds))).hexdigest()
        or _resolve(search.get("pre_reveal_inventory_path"), base=search_path.parent)
        != inventory_path
        or search.get("pre_reveal_inventory_sha256") != sha256_file(inventory_path)
        or search.get("all_selected_have_zero_pre_reveal_matches") is not True
    ):
        failures.append("disjointness_receipt: metadata mismatch")
    selected: list[int] = []
    attempts: list[dict[str, Any]] = []
    derived_reserved: dict[str, int] = {}
    counter = 0
    while len(selected) < 8:
        candidate = _derive_candidate(sha256_file(closure_path), counter)
        matches = _repo_matches(candidate)
        proposed = _runtime_derived_seeds(candidate) if not selected else {}
        proposed_matches = {
            name: list(_repo_matches(value)) for name, value in proposed.items()
        }
        accepted = bool(
            candidate not in known_prior_seeds
            and candidate not in selected
            and candidate not in set(derived_reserved.values())
            and not matches
            and not (set(proposed.values()) & known_prior_seeds)
            and not (set(proposed.values()) & set(selected))
            and len(set(proposed.values())) == len(proposed)
            and all(not value for value in proposed_matches.values())
        )
        attempts.append(
            {
                "counter": counter,
                "candidate": candidate,
                "accepted": accepted,
                "known_prior_collision": candidate in known_prior_seeds,
                "selected_collision": candidate in selected,
                "runtime_derived_collision": candidate in set(derived_reserved.values()),
                "repository_matches": list(matches),
                "proposed_runtime_derived_seeds": proposed,
                "proposed_runtime_derived_repository_matches": proposed_matches,
            }
        )
        if accepted:
            selected.append(candidate)
            if len(selected) == 1:
                derived_reserved = proposed
        counter += 1
        if counter > 10_000:
            failures.append("disjointness_receipt: derivation did not terminate")
            break
    if selected != all_seeds or search.get("candidate_attempts") != attempts:
        failures.append("disjointness_receipt: candidate derivation mismatch")
    return all_seeds[0], list(map(int, evaluation))


def validate_c1_efficacy_screen_result(
    result_path: Path, *, repo_root: Path = REPO
) -> dict[str, Any]:
    result_path = Path(result_path).expanduser().resolve()
    failures: list[str] = []
    result = _json(result_path, "result", failures)
    if result is None:
        raise C1EfficacyScreenValidationError(failures)
    if result.get("schema") != RESULT_SCHEMA or result.get("source") != "C1":
        failures.append("result.schema/source: mismatch")
    if result.get("claim_ceiling") != CLAIM_CEILING:
        failures.append("result.claim_ceiling: mismatch")
    if result.get("screen_type") != "postgate-directional-efficacy":
        failures.append("result.screen_type: mismatch")
    if result.get("routing_authority") is not False:
        failures.append("result.routing_authority: must be false")
    if result.get("prerequisites_closed") is not True:
        failures.append("result.prerequisites_closed: must be true")
    protocol = result.get("protocol")
    if not isinstance(protocol, Mapping) or (
        protocol.get("episodes") != EPISODES
        or protocol.get("training_users") != USERS
        or protocol.get("evaluation_users") != USERS
        or protocol.get("evaluation_seed_count") != EVALUATION_SEEDS
        or protocol.get("evaluation_partition") != "TRAIN"
        or protocol.get("evaluation_seed_role")
        != "fresh_disjoint_developmental_not_held_out"
        or protocol.get("main_only_evaluation") is not True
        or protocol.get("routed_sources") != ["C1"]
        or protocol.get("neutral_source") != "matched_uniform_C1"
        or not _close(protocol.get("service_guard"), SERVICE_GUARD)
        or protocol.get("decision_rule")
        != "directional_continuation_not_significance_test"
        or not _close(protocol.get("sign_component_null_probability"), 6.0 / 32.0)
        or protocol.get("outcome_use") != "CONTINUE_10EP_OR_STOP_AND_REDESIGN_C1"
    ):
        failures.append("result.protocol: mismatch")

    authority = result.get("authority")
    if not isinstance(authority, Mapping):
        failures.append("result.authority: missing")
        raise C1EfficacyScreenValidationError(failures, evidence={"result": dict(result)})
    repo = Path(repo_root).expanduser().resolve()
    recomputed_hashes: dict[str, str] = {}
    for stem, path in _canonical_authorities(repo).items():
        declared_path = _resolve(authority.get(stem + "_path"), base=result_path.parent)
        if declared_path != path.resolve():
            failures.append(f"authority.{stem}_path: canonical mismatch")
        if not path.is_file():
            failures.append(f"authority.{stem}_path: missing")
            continue
        recomputed_hashes[stem] = sha256_file(path)
        if authority.get(stem + "_sha256") != recomputed_hashes[stem]:
            failures.append(f"authority.{stem}_sha256: mismatch")
    main_source_tree_sha256, main_source_file_count = _main_source_tree_binding(repo)
    if authority.get("main_source_tree_sha256") != main_source_tree_sha256:
        failures.append("authority.main_source_tree_sha256: mismatch")
    if authority.get("main_source_file_count") != main_source_file_count:
        failures.append("authority.main_source_file_count: mismatch")
    closure_test_tree_sha256, closure_test_file_count = _closure_test_tree_binding(repo)
    if authority.get("closure_test_tree_sha256") != closure_test_tree_sha256:
        failures.append("authority.closure_test_tree_sha256: mismatch")
    if authority.get("closure_test_file_count") != closure_test_file_count:
        failures.append("authority.closure_test_file_count: mismatch")

    bound = {
        stem: _bound_file(
            authority,
            stem,
            base=result_path.parent,
            result_path=result_path,
            failures=failures,
        )
        for stem in BOUND_ARTIFACT_STEMS
    }

    prereg_record = None
    if bound["prereg"] is not None:
        if (
            bound["prereg"] != Path(CANONICAL_PREREG).resolve()
            or sha256_file(bound["prereg"]) != CANONICAL_PREREG_BYTE_SHA256
        ):
            failures.append("prereg: canonical sealed authority required")
        else:
            try:
                prereg_record = read_prereg(bound["prereg"])
            except Exception as exc:
                failures.append(f"prereg: unreadable ({type(exc).__name__})")
    archive_for_validation: TleArchive | None = None
    tle_root = _resolve(authority.get("tle_root_path"), base=result_path.parent)
    if tle_root is None or not tle_root.is_dir():
        failures.append("authority.tle_root_path: missing")
    elif prereg_record is not None:
        try:
            archive_for_validation = TleArchive(tle_root)
            ephemeris = assert_ephemeris_matches_record(
                prereg_record, archive=archive_for_validation
            )
        except Exception as exc:
            failures.append(f"ephemeris: frozen authority mismatch ({type(exc).__name__}: {exc})")
        else:
            if authority.get("tle_file_set_sha256") != ephemeris.get("file_set_sha256"):
                failures.append("authority.tle_file_set_sha256: mismatch")
            archive_receipt = ephemeris.get("archive")
            if (
                not isinstance(archive_receipt, Mapping)
                or authority.get("tle_file_count") != archive_receipt.get("file_count")
            ):
                failures.append("authority.tle_file_count: mismatch")

    checkpoint = None
    corpus = None
    if bound["checkpoint"] is not None:
        try:
            checkpoint = read_checkpoint(bound["checkpoint"], map_location="cpu")
        except Exception as exc:
            failures.append(f"checkpoint: unreadable ({type(exc).__name__})")
    if checkpoint is not None and bound["corpus_manifest"] is not None:
        try:
            corpus = load_verified_c1_corpus(
                bound["corpus_manifest"],
                expected_checkpoint_sha256=sha256_file(bound["checkpoint"]),
                expected_state_dim=checkpoint.state_dim,
                expected_action_dim=checkpoint.action_dim,
            )
        except Exception as exc:
            failures.append(f"corpus: independent verification failed ({type(exc).__name__}: {exc})")
    if corpus is not None and authority.get("c1_exp_corpus_sha256") != corpus.corpus_sha256:
        failures.append("authority.c1_exp_corpus_sha256: mismatch")
    if (
        bound["source_gate_result"] is not None
        and bound["source_gate_verification"] is not None
    ):
        _validate_source_gate_verification(
            bound["source_gate_result"],
            bound["source_gate_verification"],
            failures,
        )
    if corpus is not None and bound["corpus_manifest"] is not None:
        manifest = _json(bound["corpus_manifest"], "corpus_manifest", failures)
        manifest_authority = manifest.get("authority") if manifest is not None else None
        if not isinstance(manifest_authority, Mapping) or (
            _resolve(
                manifest_authority.get("source_gate_result_path"),
                base=bound["corpus_manifest"].parent,
            )
            != bound["source_gate_result"]
            or manifest_authority.get("source_gate_result_sha256")
            != authority.get("source_gate_result_sha256")
        ):
            failures.append("corpus_manifest: supplied Source Gate A is not its predecessor")
    if bound["corpus_verification"] is not None and corpus is not None:
        verification = _json(bound["corpus_verification"], "corpus_verification", failures)
        if verification is not None and (
            verification.get("status") != "PASS"
            or verification.get("manifest_sha256") != corpus.manifest_sha256
            or verification.get("corpus_sha256") != corpus.corpus_sha256
        ):
            failures.append("corpus_verification: lineage mismatch")

    pretransfer_evidence: Mapping[str, Any] | None = None
    if bound["pretransfer_gate_result"] is not None:
        try:
            pretransfer_evidence = validate_c1_pretransfer_result(
                bound["pretransfer_gate_result"]
            )
        except C1PretransferGateValidationError as exc:
            failures.append(f"pretransfer Gate 2: independent validation failed ({exc})")
        pretransfer_payload = _json(
            bound["pretransfer_gate_result"], "pretransfer_gate_result", failures
        )
        pretransfer_authority = (
            pretransfer_payload.get("authority")
            if pretransfer_payload is not None
            else None
        )
        if not isinstance(pretransfer_authority, Mapping):
            failures.append("pretransfer Gate 2: authority missing")
        else:
            for stem in ("checkpoint", "corpus_manifest"):
                supplied = bound.get(stem)
                declared = _resolve(
                    pretransfer_authority.get(stem + "_path"),
                    base=bound["pretransfer_gate_result"].parent,
                )
                if (
                    supplied is None
                    or declared != supplied
                    or pretransfer_authority.get(stem + "_sha256")
                    != sha256_file(supplied)
                ):
                    failures.append(
                        f"pretransfer Gate 2: supplied {stem} lineage mismatch"
                    )

    seed_manifest = _json(bound["seed_manifest"], "seed_manifest", failures) if bound["seed_manifest"] else None
    training_seed = -1
    evaluation_seeds: list[int] = []
    known_prior_seeds: set[int] = {
        20260822,
        20260823,
        *range(2026082401, 2026082431),
        *range(2026082601, 2026082611),
        *range(2026082701, 2026082711),
        *range(2026082801, 2026082831),
    }
    checkpoint_seeds: set[int] = set()
    gate1_seeds: set[int] = set()
    if checkpoint is not None:
        checkpoint_seeds = {
            int(checkpoint.train_seed),
            int(checkpoint.env_seed),
            int(checkpoint.mobility_seed),
        }
        known_prior_seeds |= checkpoint_seeds
    if bound["pretransfer_gate_result"] is not None:
        try:
            gate1_seeds = _gate1_prior_seeds(bound["pretransfer_gate_result"])
        except Exception as exc:
            failures.append(
                "Gate-1 prior seeds: authentication failed "
                f"({type(exc).__name__}: {exc})"
            )
        else:
            known_prior_seeds |= gate1_seeds
    for label, parent_path in (
        ("source", bound.get("source_gate_result")),
        ("build", bound.get("corpus_manifest")),
    ):
        if parent_path is None:
            failures.append(f"{label}_seed_manifest: parent missing")
            continue
        parent = _json(parent_path, f"{label}_seed_parent", failures)
        parent_authority = parent.get("authority") if parent is not None else None
        seed_authority_path = (
            _resolve(parent_authority.get("seed_manifest_path"), base=parent_path.parent)
            if isinstance(parent_authority, Mapping)
            else None
        )
        if (
            seed_authority_path is None
            or not seed_authority_path.is_file()
            or parent_authority.get("seed_manifest_sha256")
            != sha256_file(seed_authority_path)
        ):
            failures.append(f"{label}_seed_manifest: authority hash mismatch")
            continue
        seed_authority = _json(seed_authority_path, f"{label}_seed_manifest", failures)
        values = seed_authority.get("seeds") if seed_authority is not None else None
        if not isinstance(values, list) or any(type(value) is not int for value in values):
            failures.append(f"{label}_seed_manifest: malformed seeds")
            continue
        known_prior_seeds |= set(map(int, values))
    if seed_manifest is not None:
        if (
            seed_manifest.get("schema") != SEED_SCHEMA
            or seed_manifest.get("status") != "frozen"
            or seed_manifest.get("seed_namespace") != SEED_NAMESPACE
        ):
            failures.append("seed_manifest.schema/status/namespace: mismatch")
        for field, path in _canonical_authorities(repo).items():
            if seed_manifest.get(field + "_sha256") != sha256_file(path):
                failures.append(f"seed_manifest.{field}_sha256: mismatch")
        for stem in (
            "prereg",
            "source_gate_result",
            "source_gate_verification",
            "corpus_manifest",
            "corpus_verification",
            "pretransfer_gate_result",
            "checkpoint",
        ):
            path = bound.get(stem)
            if path is not None and seed_manifest.get(stem + "_sha256") != sha256_file(path):
                failures.append(f"seed_manifest.{stem}_sha256: mismatch")
        for field in (
            "main_source_tree_sha256",
            "main_source_file_count",
            "closure_test_tree_sha256",
            "closure_test_file_count",
            "tle_root_path",
            "tle_file_set_sha256",
            "tle_file_count",
        ):
            if seed_manifest.get(field) != authority.get(field):
                failures.append(f"seed_manifest.{field}: mismatch")
        expected_bindings: dict[str, Any] = {
            f"{stem}_sha256": digest for stem, digest in recomputed_hashes.items()
        }
        for stem in (
            "prereg",
            "source_gate_result",
            "source_gate_verification",
            "corpus_manifest",
            "corpus_verification",
            "pretransfer_gate_result",
            "checkpoint",
        ):
            artifact = bound.get(stem)
            if artifact is not None:
                expected_bindings[stem + "_sha256"] = sha256_file(artifact)
        expected_bindings.update(
            {
                "main_source_tree_sha256": main_source_tree_sha256,
                "main_source_file_count": main_source_file_count,
                "closure_test_tree_sha256": closure_test_tree_sha256,
                "closure_test_file_count": closure_test_file_count,
                "tle_root_path": authority.get("tle_root_path"),
                "tle_file_set_sha256": authority.get("tle_file_set_sha256"),
                "tle_file_count": authority.get("tle_file_count"),
            }
        )
        training_seed, evaluation_seeds = _validate_seed_provenance(
            seed_path=bound["seed_manifest"],
            seed_manifest=seed_manifest,
            expected_bindings=expected_bindings,
            known_prior_seeds=known_prior_seeds,
            checkpoint_seeds=checkpoint_seeds,
            gate1_seeds=gate1_seeds,
            failures=failures,
        )

    execution = (
        _json(bound["execution_ledger"], "execution_ledger", failures)
        if bound["execution_ledger"] is not None
        else None
    )
    if (
        bound["execution_ledger"] != EXECUTION_LEDGER.resolve()
        or execution is None
        or execution.get("schema") != EXECUTION_SCHEMA
        or execution.get("status") != "SEALED_SINGLE_EXECUTION_BEFORE_OUTCOME"
        or execution.get("claim_ceiling") != CLAIM_CEILING
        or _resolve(execution.get("seed_manifest_path"), base=EXECUTION_LEDGER.parent)
        != bound["seed_manifest"]
        or execution.get("seed_manifest_sha256")
        != (sha256_file(bound["seed_manifest"]) if bound["seed_manifest"] else None)
        or _resolve(execution.get("campaign_ledger_path"), base=EXECUTION_LEDGER.parent)
        != CAMPAIGN_LEDGER.resolve()
        or execution.get("campaign_ledger_sha256")
        != (sha256_file(CAMPAIGN_LEDGER.resolve()) if CAMPAIGN_LEDGER.is_file() else None)
        or _resolve(execution.get("output_dir"), base=EXECUTION_LEDGER.parent)
        != result_path.parent
        or execution.get("no_second_execution_is_authorised") is not True
    ):
        failures.append("execution_ledger: invalid single-run authority")

    raw = _json(bound["raw_rows"], "raw", failures) if bound["raw_rows"] else None
    paired: list[Mapping[str, Any]] = []
    initial_parity_independently_replayed = False
    evaluation_points_independently_replayed = 0
    branch_checkpoints: dict[str, tuple[Path, Any]] = {}
    if raw is not None:
        if (
            raw.get("schema") != RAW_SCHEMA
            or raw.get("status") != "complete"
            or raw.get("claim_ceiling") != CLAIM_CEILING
        ):
            failures.append("raw.schema/status/claim: mismatch")
        if (
            _resolve(raw.get("execution_ledger_path"), base=bound["raw_rows"].parent)
            != bound["execution_ledger"]
            or raw.get("execution_ledger_sha256")
            != (
                sha256_file(bound["execution_ledger"])
                if bound["execution_ledger"] is not None
                else None
            )
        ):
            failures.append("raw.execution_ledger: mismatch")
        parity = raw.get("initial_main_parity")
        if (
            not isinstance(parity, Mapping)
            or parity.get("status") != "PASS"
            or parity.get("exact_after_descriptive_metadata_normalisation") is not True
            or parity.get("first_difference") is not None
        ):
            failures.append("raw.initial_main_parity: exact PASS required")
        if (
            archive_for_validation is not None
            and bound["prereg"] is not None
            and seed_manifest is not None
            and training_seed >= 0
        ):
            try:
                parity_configs = {
                    "informed": _short_config(
                        bound["prereg"],
                        arm="F111",
                        episodes=EPISODES,
                        epsilon_decay_episodes=3,
                        target_update_every=2,
                        learning_rate=DEFAULT_LEARNING_RATE,
                    ),
                    "neutral": _short_config(
                        bound["prereg"],
                        arm="A011",
                        episodes=EPISODES,
                        epsilon_decay_episodes=3,
                        target_update_every=2,
                        learning_rate=DEFAULT_LEARNING_RATE,
                    ),
                }
                replayed_parity = compare_states(
                    _initial_state(
                        archive=archive_for_validation,
                        config=parity_configs["informed"],
                        train_seed=training_seed,
                        env_seed=int(seed_manifest["environment_seed"]),
                        mobility_seed=int(seed_manifest["mobility_seed"]),
                    ),
                    _initial_state(
                        archive=archive_for_validation,
                        config=parity_configs["neutral"],
                        train_seed=training_seed,
                        env_seed=int(seed_manifest["environment_seed"]),
                        mobility_seed=int(seed_manifest["mobility_seed"]),
                    ),
                )
            except Exception as exc:
                failures.append(
                    f"raw.initial_main_parity: independent rerun failed ({type(exc).__name__}: {exc})"
                )
            else:
                if dict(parity) != replayed_parity:
                    failures.append("raw.initial_main_parity: independent rerun mismatch")
                else:
                    initial_parity_independently_replayed = True
        branches = raw.get("branch_results")
        schedules = raw.get("schedule_receipts")
        if not isinstance(branches, Mapping) or not isinstance(schedules, Mapping):
            failures.append("raw.branch_results/schedule_receipts: missing")
        else:
            for label, expected_arm, expected_corpus_branch in (
                ("informed", "F111", "local"),
                ("neutral", "A011", "control"),
            ):
                branch = branches.get(label)
                if not isinstance(branch, Mapping):
                    failures.append(f"raw.branch_results.{label}: missing")
                    continue
                if (
                    branch.get("episodes") != EPISODES
                    or branch.get("gates") != {"C1": "route", "C2": "shadow", "C3": "shadow"}
                    or branch.get("lanes_informed", {}).get("C1") != (label == "informed")
                ):
                    failures.append(f"raw.branch_results.{label}: schedule mismatch")
                prefill = branch.get("c1_prefill")
                if (
                    not isinstance(prefill, Mapping)
                    or prefill.get("bundles") != 31
                    or prefill.get("corpus_branch") != expected_corpus_branch
                    or prefill.get("selection")
                    != "paired_high_mid_context_intersection"
                    or not isinstance(prefill.get("matched_contexts"), list)
                    or len(prefill["matched_contexts"]) != 31
                    or prefill.get("enters_main") is not False
                ):
                    failures.append(f"raw.branch_results.{label}: prefill mismatch")
                schedule_evidence = _validate_schedule(
                    branch_dir=bound["raw_rows"].parent / label,
                    result=branch,
                    declared=schedules.get(label),
                    label=label,
                    failures=failures,
                )
                expected_config = _short_config(
                    bound["prereg"],
                    arm=expected_arm,
                    episodes=EPISODES,
                    epsilon_decay_episodes=3,
                    target_update_every=2,
                    learning_rate=DEFAULT_LEARNING_RATE,
                )
                seed_payload = seed_manifest if isinstance(seed_manifest, Mapping) else {}
                checkpoint_path, branch_checkpoint = _validate_branch_artifacts(
                    label=label,
                    expected_arm=expected_arm,
                    expected_config=expected_config,
                    branch=branch,
                    raw_dir=bound["raw_rows"].parent,
                    training_seed=training_seed,
                    environment_seed=int(seed_payload.get("environment_seed", -1)),
                    mobility_seed=int(seed_payload.get("mobility_seed", -1)),
                    runtime_derived_seeds=(
                        seed_payload.get("runtime_derived_seeds", {})
                        if isinstance(seed_payload.get("runtime_derived_seeds"), Mapping)
                        else {}
                    ),
                    schedule=schedule_evidence,
                    failures=failures,
                )
                if checkpoint_path is not None and branch_checkpoint is not None:
                    branch_checkpoints[label] = (checkpoint_path, branch_checkpoint)
            informed_schedule = schedules.get("informed")
            neutral_schedule = schedules.get("neutral")
            informed_branch = branches.get("informed")
            neutral_branch = branches.get("neutral")
            informed_prefill = (
                informed_branch.get("c1_prefill", {})
                if isinstance(informed_branch, Mapping)
                else {}
            )
            neutral_prefill = (
                neutral_branch.get("c1_prefill", {})
                if isinstance(neutral_branch, Mapping)
                else {}
            )
            if (
                not isinstance(informed_prefill, Mapping)
                or not isinstance(neutral_prefill, Mapping)
                or informed_prefill.get("matched_contexts")
                != neutral_prefill.get("matched_contexts")
            ):
                failures.append("raw.branch_results: prefill context mismatch")
            if (
                not isinstance(informed_schedule, Mapping)
                or not isinstance(neutral_schedule, Mapping)
                or informed_schedule.get("warmup_indices")
                != neutral_schedule.get("warmup_indices")
                or informed_schedule.get("source_unit_update_indices")
                != neutral_schedule.get("source_unit_update_indices")
            ):
                failures.append("raw.schedule_receipts: branch update schedule mismatch")
        values = raw.get("paired_rows")
        if not isinstance(values, list) or len(values) != EVALUATION_SEEDS:
            failures.append("raw.paired_rows: denominator mismatch")
        else:
            paired = [row for row in values if isinstance(row, Mapping)]
            if len(paired) != len(values):
                failures.append("raw.paired_rows: malformed row")
        branches = raw.get("branch_results")
        if isinstance(branches, Mapping) and len(paired) == EVALUATION_SEEDS:
            checkpoint_hashes = {
                label: branches[label].get("checkpoint_sha256")
                for label in ("informed", "neutral")
                if isinstance(branches.get(label), Mapping)
            }
            for index, row in enumerate(paired):
                seed = row.get("evaluation_seed")
                if type(seed) is not int or index >= len(evaluation_seeds) or seed != evaluation_seeds[index]:
                    failures.append(f"raw.paired_rows[{index}].evaluation_seed: mismatch")
                    continue
                informed = _validate_endpoint(
                    row.get("informed"),
                    label=f"paired[{index}].informed",
                    branch="informed",
                    checkpoint_sha=str(checkpoint_hashes.get("informed")),
                    training_seed=training_seed,
                    evaluation_seed=seed,
                    failures=failures,
                )
                neutral = _validate_endpoint(
                    row.get("neutral"),
                    label=f"paired[{index}].neutral",
                    branch="neutral",
                    checkpoint_sha=str(checkpoint_hashes.get("neutral")),
                    training_seed=training_seed,
                    evaluation_seed=seed,
                    failures=failures,
                )
                if informed is not None and neutral is not None:
                    expected_delta = float(informed["system_ee_bits_per_j"]) - float(neutral["system_ee_bits_per_j"])
                    if not _close(row.get("delta_ee_bits_per_j"), expected_delta):
                        failures.append(f"raw.paired_rows[{index}].delta_ee_bits_per_j: mismatch")
                if (
                    archive_for_validation is not None
                    and informed is not None
                    and neutral is not None
                    and set(branch_checkpoints) == {"informed", "neutral"}
                ):
                    for label, declared_endpoint in (
                        ("informed", informed),
                        ("neutral", neutral),
                    ):
                        checkpoint_path, checkpoint_payload = branch_checkpoints[label]
                        try:
                            replayed_endpoint = asdict(
                                evaluate_checkpoint_point(
                                    archive=archive_for_validation,
                                    checkpoint_path=checkpoint_path,
                                    checkpoint_payload=checkpoint_payload,
                                    arm=label,
                                    checkpoint_sha256=sha256_file(checkpoint_path),
                                    users=USERS,
                                    evaluation_seed=seed,
                                )
                            )
                        except Exception as exc:
                            failures.append(
                                f"raw.paired_rows[{index}].{label}: independent "
                                f"evaluation replay failed ({type(exc).__name__}: {exc})"
                            )
                        else:
                            before = len(failures)
                            _compare_endpoint_payloads(
                                declared_endpoint,
                                replayed_endpoint,
                                label=f"raw.paired_rows[{index}].{label}",
                                failures=failures,
                            )
                            if len(failures) == before:
                                evaluation_points_independently_replayed += 1
        embedded = raw.get("pretransfer_gate_evidence")
        if pretransfer_evidence is None or not isinstance(embedded, Mapping) or (
            embedded.get("status") != "PASS"
            or embedded.get("decision") != "ROUTE"
            or embedded.get("checkpoint_sha256") != pretransfer_evidence.get("checkpoint_sha256")
            or embedded.get("corpus_sha256") != pretransfer_evidence.get("corpus_sha256")
        ):
            failures.append("raw.pretransfer_gate_evidence: mismatch")

    if not initial_parity_independently_replayed:
        failures.append("raw.initial_main_parity: independent replay evidence missing")
    if evaluation_points_independently_replayed != 2 * EVALUATION_SEEDS:
        failures.append(
            "raw.paired_rows: all ten deterministic evaluation points must replay exactly"
        )

    guard_failures = result.get("guard_failures")
    if not isinstance(guard_failures, list) or any(not isinstance(item, str) for item in guard_failures):
        failures.append("result.guard_failures: malformed")
        guard_failures = []
    if len(paired) == EVALUATION_SEEDS:
        checks, metrics = _recompute_decision(paired, guard_failures)
    else:
        checks = {name: False for name in EXPECTED_CHECKS}
        metrics = {}
    if result.get("checks") != checks:
        failures.append("result.checks: independent recomputation mismatch")
    declared_metrics = result.get("metrics")
    if not isinstance(declared_metrics, Mapping) or set(declared_metrics) != set(metrics):
        failures.append("result.metrics: surface mismatch")
    else:
        for key, value in metrics.items():
            declared = declared_metrics.get(key)
            if isinstance(value, list):
                if not isinstance(declared, list) or len(declared) != len(value) or any(
                    not _close(left, right) for left, right in zip(declared, value, strict=True)
                ):
                    failures.append(f"result.metrics.{key}: mismatch")
            elif not _close(declared, value):
                failures.append(f"result.metrics.{key}: mismatch")
    passed = all(checks.values())
    expected_status = "PASS" if passed else "FAIL"
    expected_decision = "CONTINUE_10EP" if passed else "STOP_AND_REDESIGN_C1"
    if result.get("status") != expected_status or result.get("decision") != expected_decision:
        failures.append("result.status/decision: mismatch")

    evidence = {
        "result_path": str(result_path),
        "receipt_valid": not failures,
        "screen_status": result.get("status"),
        "screen_decision": result.get("decision"),
        "routing_authority": False,
        "canonical_hashes_recomputed": recomputed_hashes,
        "paired_rows": len(paired),
        "initial_parity_independently_replayed": initial_parity_independently_replayed,
        "evaluation_points_independently_replayed": evaluation_points_independently_replayed,
        "pretransfer_gate_status": pretransfer_evidence.get("status") if pretransfer_evidence else None,
        "checks_recomputed": checks,
        "metrics_recomputed": metrics,
    }
    if failures:
        raise C1EfficacyScreenValidationError(failures, evidence=evidence)
    return evidence


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    evidence = validate_c1_efficacy_screen_result(args.result)
    serialized = json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        if args.output.exists():
            raise FileExistsError(f"refusing to overwrite {args.output}")
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "C1EfficacyScreenValidationError",
    "validate_c1_efficacy_screen_result",
]
