#!/usr/bin/env python3
"""Run the post-Gate-2 C1-informed versus neutral 4EP efficacy micro-screen.

The legacy filename is retained for review-link compatibility.  This program
does not grant routing authority; it produces only CONTINUE_10EP or
STOP_AND_REDESIGN_C1 for the exact bound developmental carrier revision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
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
    compare_states,
    validate_receipt as validate_zero_dose_receipt,
)
from run_short_ep import (  # noqa: E402
    DEFAULT_ACRM_ETA,
    DEFAULT_LEARNING_RATE,
    _make_environment,
    _short_config,
    _write_json,
    run_treatment,
)
from smc_er_core import GateLedger  # noqa: E402
from sweep_evaluation import evaluate_checkpoint_point, ratio_of_sums  # noqa: E402
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    CANONICAL_PREREG,
    CANONICAL_PREREG_BYTE_SHA256,
    assert_ephemeris_matches_record,
)


SPEC = HERE / "C1-MAIN-CONSUMER-GATE-V1-SPEC-2026-08-28.md"
METHOD = REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md"
CONCEPT = REPO / "docs" / "MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md"
TEST_FILE = HERE / "test_c1_consumer_gate.py"
VALIDATOR = HERE / "c1_efficacy_micro_screen_validator.py"
VALIDATOR_TEST = HERE / "test_c1_efficacy_micro_screen_validator.py"
FREEZE = HERE / "freeze_c1_efficacy_micro_screen.py"
FREEZE_TEST = HERE / "test_freeze_c1_efficacy_micro_screen.py"
SWEEP_EVALUATOR = HERE / "sweep_evaluation.py"
PARITY_CHECKER = HERE / "check_zero_dose_parity.py"
PRETRANSFER_VALIDATOR = HERE / "c1_pretransfer_gate_validator.py"
SOURCE_GATE_VERIFIER = HERE / "verify_c1_source_gate.py"
CORRECTIVE_REPLAY_ADDENDUM = (
    HERE / "C1-CANONICAL-TLE-CORRECTIVE-REPLAY-ADDENDUM-V1-2026-08-28.json"
)
CORRECTIVE_REPLAY_VERIFIER = HERE / "verify_c1_corrective_replay_addendum.py"
CORRECTIVE_REPLAY_VERIFIER_TEST = (
    HERE / "test_verify_c1_corrective_replay_addendum.py"
)
SOURCE_SEED_PROVENANCE_CORRECTION = (
    HERE
    / "C1-SOURCE-GATE-A-SEED-PROVENANCE-CORRECTION-V1-2026-08-28.json"
)
CLOSURE_TEST_FILES = (
    HERE / "test_build_c1_exp_corpus.py",
    HERE / "test_c1_exp_corpus.py",
    TEST_FILE,
    VALIDATOR_TEST,
    HERE / "test_c1_pretransfer_consumer_gate.py",
    HERE / "test_c1_pretransfer_gate_validator.py",
    HERE / "test_run_short_ep.py",
    HERE / "test_smc_er_core.py",
    HERE / "test_sweep_evaluation.py",
    HERE / "test_verify_c1_source_gate.py",
    CORRECTIVE_REPLAY_VERIFIER_TEST,
    FREEZE_TEST,
)
SEED_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-seeds-v1"
CLOSURE_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-closure-v1"
DISJOINTNESS_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-disjointness-v1"
INVENTORY_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-pre-reveal-inventory-v1"
CAMPAIGN_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-single-campaign-v1"
EXECUTION_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-single-execution-v1"
CAMPAIGN_LEDGER = HERE / "c1-efficacy-microscreen-campaign-v1.json"
EXECUTION_LEDGER = HERE / "c1-efficacy-microscreen-execution-v1.json"
RESULT_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-result-v1"
RAW_SCHEMA = "smc-er-c1-postgate-efficacy-microscreen-raw-v1"
CLAIM_CEILING = "ONE_SEED_4EP_DIRECTIONAL_SCREEN_NOT_ROUTING_AUTHORITY_NOT_CHAPTER5"
SEED_NAMESPACE = "SMC-ER-C1-POSTGATE-EFFICACY-MICROSCREEN-V1"
EPISODES = 4
USERS = 100
EVALUATION_SEEDS = 5
SERVICE_GUARD = 0.005
MAIN_BATCH_SIZE = 128


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _main_source_tree_binding(repo: Path = REPO) -> tuple[str, int]:
    """Hash every Python source that can implement Main or its environment."""

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
        raise RuntimeError("Main source-tree authority is empty")
    return hashlib.sha256(_canonical_json(rows)).hexdigest(), len(rows)


def _closure_test_tree_binding(repo: Path = REPO) -> tuple[str, int]:
    """Hash the complete, ordered closure-test authority."""

    root = Path(repo).resolve()
    rows = [
        {
            "path": path.resolve().relative_to(root).as_posix(),
            "sha256": sha256_file(path.resolve()),
        }
        for path in CLOSURE_TEST_FILES
    ]
    if any(not path.resolve().is_file() for path in CLOSURE_TEST_FILES):
        raise RuntimeError("C1 closure-test authority is incomplete")
    return hashlib.sha256(_canonical_json(rows)).hexdigest(), len(rows)


def _validate_source_gate_verification(
    source_gate: Path, source_gate_verification: Path
) -> dict[str, Any]:
    """Require an exact replay under the current Source Gate verifier."""

    source_payload = json.loads(source_gate.read_text(encoding="utf-8"))
    recorded = json.loads(source_gate_verification.read_text(encoding="utf-8"))
    addendum_path = Path(
        str(recorded.get("corrective_replay_addendum_path", ""))
    ).expanduser().resolve()
    corrective_verification_path = Path(
        str(recorded.get("corrective_replay_verification_path", ""))
    ).expanduser().resolve()
    seed_correction_path = Path(
        str(recorded.get("source_seed_provenance_correction_path", ""))
    ).expanduser().resolve()
    reproduced = verify_c1_source_gate(
        source_payload,
        source_gate_path=source_gate,
        corrective_addendum=addendum_path,
        corrective_replay_verification=corrective_verification_path,
        source_seed_provenance_correction=seed_correction_path,
    )
    if recorded.get("status") != "PASS" or recorded != reproduced:
        raise RuntimeError(
            "source Gate A verification is not an exact current-authority replay"
        )
    return reproduced


def _authenticated_parent_seed_values(
    parent: Mapping[str, Any], *, label: str, base: Path | None = None
) -> set[int]:
    """Read a parent seed authority only after checking its declared hash."""

    authority = parent.get("authority")
    if not isinstance(authority, Mapping):
        raise RuntimeError(f"{label} lacks seed authority")
    raw = authority.get("seed_manifest_path")
    if not isinstance(raw, str) or not raw:
        raise RuntimeError(f"{label} lacks seed manifest path")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (base or REPO) / path
    path = path.resolve()
    if (
        not path.is_file()
        or authority.get("seed_manifest_sha256") != sha256_file(path)
    ):
        raise RuntimeError(f"{label} seed manifest hash mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("seeds") if isinstance(payload, Mapping) else None
    if (
        not isinstance(values, list)
        or any(type(value) is not int or value < 0 for value in values)
    ):
        raise RuntimeError(f"{label} seed manifest is malformed")
    return set(map(int, values))


def _validate_pretransfer_lineage(
    pretransfer_gate: Path, *, checkpoint: Path, corpus_manifest: Path
) -> Mapping[str, Any]:
    """Require Gate 2 to validate and bind these exact downstream inputs."""

    evidence = validate_c1_pretransfer_result(pretransfer_gate)
    if evidence.get("status") != "PASS" or evidence.get("decision") != "ROUTE":
        raise RuntimeError("C1 pre-transfer Gate 2 does not permit this micro-screen")
    payload = json.loads(pretransfer_gate.read_text(encoding="utf-8"))
    authority = payload.get("authority") if isinstance(payload, Mapping) else None
    if not isinstance(authority, Mapping):
        raise RuntimeError("C1 pre-transfer Gate 2 lacks authority")
    expected = (
        ("checkpoint", Path(checkpoint).resolve()),
        ("corpus_manifest", Path(corpus_manifest).resolve()),
    )
    for stem, supplied in expected:
        raw = authority.get(stem + "_path")
        bound = Path(raw).expanduser() if isinstance(raw, str) and raw else None
        if bound is not None and not bound.is_absolute():
            bound = pretransfer_gate.parent / bound
        if (
            bound is None
            or bound.resolve() != supplied
            or authority.get(stem + "_sha256") != sha256_file(supplied)
        ):
            noun = "corpus" if stem == "corpus_manifest" else stem
            raise RuntimeError(
                f"C1 pre-transfer Gate 2 does not bind the supplied {noun}"
            )
    return evidence


def _gate1_prior_seeds(pretransfer_gate: Path) -> set[int]:
    """Authenticate the three matched Gate-1 roots through zero-dose parity."""

    gate = json.loads(pretransfer_gate.read_text(encoding="utf-8"))
    authority = gate.get("authority") if isinstance(gate, Mapping) else None
    if not isinstance(authority, Mapping):
        raise RuntimeError("C1 pre-transfer Gate 2 lacks authority")
    raw = authority.get("zero_dose_parity_path")
    parity = Path(raw).expanduser() if isinstance(raw, str) and raw else None
    if parity is not None and not parity.is_absolute():
        parity = pretransfer_gate.parent / parity
    if (
        parity is None
        or not parity.resolve().is_file()
        or authority.get("zero_dose_parity_sha256")
        != sha256_file(parity.resolve())
    ):
        raise RuntimeError("C1 pre-transfer Gate 2 zero-dose authority mismatch")
    replayed = validate_zero_dose_receipt(parity.resolve())
    parity_authority = replayed.get("authority")
    if not isinstance(parity_authority, Mapping):
        raise RuntimeError("zero-dose parity lacks state authority")
    raw_state = parity_authority.get("baseline_state_path")
    state_path = (
        Path(raw_state).expanduser()
        if isinstance(raw_state, str) and raw_state
        else None
    )
    if state_path is not None and not state_path.is_absolute():
        state_path = parity.parent / state_path
    if (
        state_path is None
        or not state_path.resolve().is_file()
        or parity_authority.get("baseline_state_sha256")
        != sha256_file(state_path.resolve())
    ):
        raise RuntimeError("zero-dose parity baseline state authority mismatch")
    state = torch.load(state_path.resolve(), map_location="cpu", weights_only=False)
    if not isinstance(state, Mapping):
        raise RuntimeError("zero-dose parity baseline state is malformed")
    values = [state.get(name) for name in ("train_seed", "env_seed", "mobility_seed")]
    if any(type(value) is not int or value < 0 for value in values):
        raise RuntimeError("zero-dose parity baseline seeds are malformed")
    return set(map(int, values))


def _authority_bindings(
    *,
    prereg: Path,
    source_gate: Path,
    source_gate_verification: Path,
    corpus_manifest: Path,
    corpus_verification: Path,
    pretransfer_gate: Path,
    checkpoint: Path,
    archive: TleArchive,
    ephemeris: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the one binding schema shared by freeze and execution."""

    main_source_tree_sha256, main_source_file_count = _main_source_tree_binding()
    closure_test_tree_sha256, closure_test_file_count = _closure_test_tree_binding()
    return {
        "spec_sha256": sha256_file(SPEC),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "test_sha256": sha256_file(TEST_FILE),
        "validator_sha256": sha256_file(VALIDATOR),
        "validator_test_sha256": sha256_file(VALIDATOR_TEST),
        "freeze_sha256": sha256_file(FREEZE),
        "freeze_test_sha256": sha256_file(FREEZE_TEST),
        "method_sha256": sha256_file(METHOD),
        "concept_sha256": sha256_file(CONCEPT),
        "run_short_ep_sha256": sha256_file(HERE / "run_short_ep.py"),
        "routing_core_sha256": sha256_file(HERE / "smc_er_core.py"),
        "roles_sha256": sha256_file(HERE / "smc_er_roles.py"),
        "corpus_loader_sha256": sha256_file(HERE / "c1_exp_corpus.py"),
        "sweep_evaluator_sha256": sha256_file(SWEEP_EVALUATOR),
        "parity_checker_sha256": sha256_file(PARITY_CHECKER),
        "pretransfer_validator_sha256": sha256_file(PRETRANSFER_VALIDATOR),
        "source_gate_verifier_sha256": sha256_file(SOURCE_GATE_VERIFIER),
        "corrective_replay_addendum_sha256": sha256_file(CORRECTIVE_REPLAY_ADDENDUM),
        "corrective_replay_verifier_sha256": sha256_file(CORRECTIVE_REPLAY_VERIFIER),
        "corrective_replay_verifier_test_sha256": sha256_file(
            CORRECTIVE_REPLAY_VERIFIER_TEST
        ),
        "source_seed_provenance_correction_sha256": sha256_file(
            SOURCE_SEED_PROVENANCE_CORRECTION
        ),
        "prereg_sha256": sha256_file(prereg),
        "source_gate_result_sha256": sha256_file(source_gate),
        "source_gate_verification_sha256": sha256_file(source_gate_verification),
        "corpus_manifest_sha256": sha256_file(corpus_manifest),
        "corpus_verification_sha256": sha256_file(corpus_verification),
        "pretransfer_gate_result_sha256": sha256_file(pretransfer_gate),
        "checkpoint_sha256": sha256_file(checkpoint),
        "main_source_tree_sha256": main_source_tree_sha256,
        "main_source_file_count": main_source_file_count,
        "closure_test_tree_sha256": closure_test_tree_sha256,
        "closure_test_file_count": closure_test_file_count,
        "tle_root_path": str(archive.root.resolve()),
        "tle_file_set_sha256": ephemeris["file_set_sha256"],
        "tle_file_count": int(ephemeris["archive"]["file_count"]),
    }


def _derive_candidate(closure_sha256: str, counter: int) -> int:
    return int.from_bytes(
        hashlib.sha256(
            _canonical_json([SEED_NAMESPACE, closure_sha256, int(counter)])
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
        raise RuntimeError(f"repository disjointness search failed: {completed.stderr}")
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
        raise RuntimeError(f"repository numeric inventory failed: {completed.stderr}")
    tokens = sorted({int(line) for line in completed.stdout.splitlines() if line})
    return hashlib.sha256(_canonical_json(tokens)).hexdigest(), len(tokens)


def _validate_seed_manifest(
    path: Path,
    *,
    bindings: Mapping[str, Any],
    known_prior_seeds: set[int],
    checkpoint_seeds: set[int],
    gate1_seeds: set[int],
) -> dict[str, Any]:
    path = Path(path).resolve()
    if path.is_relative_to(REPO.resolve()):
        raise RuntimeError("C1 efficacy seed authority must live outside the repository")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema") != SEED_SCHEMA
        or payload.get("status") != "frozen"
        or payload.get("seed_namespace") != SEED_NAMESPACE
    ):
        raise RuntimeError("C1 efficacy-screen seed manifest schema/status mismatch")
    for field, expected in bindings.items():
        if payload.get(field) != expected:
            raise RuntimeError(f"C1 efficacy-screen seed manifest {field} drift")
    if (
        payload.get("seed_count") != 8
        or payload.get("derivation")
        != "first eight collision-free uint32 values from closure-bound counter-separated SHA-256"
        or payload.get("repository_disjointness_checked_before_reveal") is not True
    ):
        raise RuntimeError("C1 efficacy-screen seed derivation metadata drift")
    if payload.get("forbidden_checkpoint_seeds") != sorted(checkpoint_seeds):
        raise RuntimeError("C1 efficacy-screen checkpoint seed exclusion drift")
    if payload.get("forbidden_gate1_seeds") != sorted(gate1_seeds):
        raise RuntimeError("C1 efficacy-screen Gate-1 seed exclusion drift")
    scalar_names = ("training_seed", "environment_seed", "mobility_seed")
    scalar = [payload.get(name) for name in scalar_names]
    evaluation = payload.get("evaluation_seeds")
    if (
        any(type(seed) is not int or seed < 0 for seed in scalar)
        or not isinstance(evaluation, list)
        or len(evaluation) != EVALUATION_SEEDS
        or any(type(seed) is not int or seed < 0 for seed in evaluation)
    ):
        raise RuntimeError("C1 efficacy-screen seed denominator is invalid")
    all_seeds = [*scalar, *evaluation]
    if len(set(all_seeds)) != len(all_seeds) or set(all_seeds) & known_prior_seeds:
        raise RuntimeError("C1 efficacy-screen seeds are not pairwise disjoint")
    runtime_derived = _runtime_derived_seeds(int(scalar[0]))
    if (
        payload.get("runtime_derived_seeds") != runtime_derived
        or len(set(runtime_derived.values())) != 3
        or set(runtime_derived.values()) & (known_prior_seeds | set(all_seeds))
    ):
        raise RuntimeError("C1 efficacy-screen runtime-derived seed collision")

    def bound_json(path_field: str, sha_field: str) -> tuple[Path, Mapping[str, Any]]:
        raw_path = payload.get(path_field)
        if not isinstance(raw_path, str) or not raw_path:
            raise RuntimeError(f"C1 seed manifest lacks {path_field}")
        target = Path(raw_path).expanduser()
        if not target.is_absolute():
            target = path.parent / target
        target = target.resolve()
        if not target.is_file() or payload.get(sha_field) != sha256_file(target):
            raise RuntimeError(f"C1 seed manifest {path_field} hash drift")
        value = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise RuntimeError(f"C1 seed manifest {path_field} is not an object")
        return target, value

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
        raise RuntimeError("C1 efficacy campaign ledger is not canonical")
    if (
        closure.get("schema") != CLOSURE_SCHEMA
        or closure.get("status") != "CLOSED_BEFORE_SEED_DERIVATION"
        or closure.get("claim_ceiling") != CLAIM_CEILING
        or closure.get("bindings") != dict(bindings)
    ):
        raise RuntimeError("C1 efficacy closure manifest is invalid")
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
        raise RuntimeError("C1 efficacy closure test receipt is invalid")
    inventory_ref = closure.get("pre_reveal_inventory")
    live_inventory_sha, live_inventory_count = _numeric_inventory()
    if (
        inventory.get("schema") != INVENTORY_SCHEMA
        or inventory.get("status") != "CAPTURED_BEFORE_SEED_DERIVATION"
        or inventory.get("claim_ceiling") != CLAIM_CEILING
        or inventory.get("numeric_token_set_sha256") != live_inventory_sha
        or inventory.get("numeric_token_count") != live_inventory_count
        or not isinstance(inventory_ref, Mapping)
        or Path(str(inventory_ref.get("path"))).resolve() != inventory_path
        or inventory_ref.get("sha256") != sha256_file(inventory_path)
        or inventory_ref.get("numeric_token_set_sha256") != live_inventory_sha
        or inventory_ref.get("numeric_token_count") != live_inventory_count
    ):
        raise RuntimeError("C1 efficacy pre-reveal inventory is not reproducible")
    if (
        campaign.get("schema") != CAMPAIGN_SCHEMA
        or campaign.get("status") != "SEALED_SINGLE_CAMPAIGN_BEFORE_SEED_REVEAL"
        or campaign.get("claim_ceiling") != CLAIM_CEILING
        or Path(str(campaign.get("closure_manifest_path"))).resolve() != closure_path
        or campaign.get("closure_manifest_sha256") != sha256_file(closure_path)
        or Path(str(campaign.get("seed_manifest_path"))).resolve() != path
        or Path(str(campaign.get("execution_ledger_path"))).resolve()
        != EXECUTION_LEDGER.resolve()
        or campaign.get("no_second_freeze_or_execution_is_authorised") is not True
    ):
        raise RuntimeError("C1 efficacy single-campaign ledger is invalid")
    if Path(str(payload.get("execution_ledger_path"))).resolve() != EXECUTION_LEDGER.resolve():
        raise RuntimeError("C1 efficacy execution ledger path drift")
    if EXECUTION_LEDGER.resolve().exists():
        raise RuntimeError("the one allowed C1 efficacy execution is already reserved")
    if (
        search.get("schema") != DISJOINTNESS_SCHEMA
        or search.get("status") != "PASS"
        or search.get("seed_namespace") != SEED_NAMESPACE
        or search.get("closure_manifest_sha256") != sha256_file(closure_path)
        or search.get("selected_seeds") != all_seeds
        or search.get("runtime_derived_seeds") != runtime_derived
        or search.get("known_prior_seed_values") != sorted(known_prior_seeds)
        or search.get("known_prior_seed_values_sha256")
        != hashlib.sha256(_canonical_json(sorted(known_prior_seeds))).hexdigest()
        or Path(str(search.get("pre_reveal_inventory_path"))).resolve() != inventory_path
        or search.get("pre_reveal_inventory_sha256") != sha256_file(inventory_path)
        or search.get("all_selected_have_zero_pre_reveal_matches") is not True
    ):
        raise RuntimeError("C1 efficacy disjointness receipt is invalid")

    selected: list[int] = []
    expected_attempts: list[dict[str, Any]] = []
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
        expected_attempts.append(
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
            raise RuntimeError("unable to reproduce C1 efficacy seed derivation")
    if selected != all_seeds or search.get("candidate_attempts") != expected_attempts:
        raise RuntimeError("C1 efficacy seeds do not reproduce from the sealed closure")
    return dict(payload)


def _reserve_single_execution(*, seed_manifest: Path, output_dir: Path) -> Path:
    ledger = EXECUTION_LEDGER.resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.is_relative_to(REPO.resolve()):
        raise RuntimeError("C1 efficacy outcome artifacts must live outside the repository")
    if output_dir.exists():
        raise FileExistsError(f"refusing to reuse efficacy output: {output_dir}")
    payload = {
        "schema": EXECUTION_SCHEMA,
        "status": "SEALED_SINGLE_EXECUTION_BEFORE_OUTCOME",
        "claim_ceiling": CLAIM_CEILING,
        "seed_manifest_path": str(Path(seed_manifest).resolve()),
        "seed_manifest_sha256": sha256_file(Path(seed_manifest).resolve()),
        "campaign_ledger_path": str(CAMPAIGN_LEDGER.resolve()),
        "campaign_ledger_sha256": sha256_file(CAMPAIGN_LEDGER.resolve()),
        "output_dir": str(output_dir),
        "no_second_execution_is_authorised": True,
    }
    serialized = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with ledger.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    return ledger


def decide_c1_efficacy_screen(
    paired_rows: Sequence[Mapping[str, Any]],
    *,
    guard_failures: Sequence[str],
) -> dict[str, Any]:
    if len(paired_rows) != EVALUATION_SEEDS:
        raise ValueError("C1 efficacy screen requires exactly five paired rows")
    seeds = [int(row["evaluation_seed"]) for row in paired_rows]
    if len(set(seeds)) != EVALUATION_SEEDS:
        raise ValueError("C1 efficacy-screen evaluation seeds must be unique")
    deltas: list[float] = []
    for index, row in enumerate(paired_rows):
        recomputed = (
            float(row["informed"]["system_ee_bits_per_j"])
            - float(row["neutral"]["system_ee_bits_per_j"])
        )
        declared = row.get("delta_ee_bits_per_j")
        if declared is None or not math.isclose(
            float(declared), recomputed, rel_tol=1e-12, abs_tol=1e-9
        ):
            raise ValueError(f"paired row {index} EE delta is missing or inconsistent")
        deltas.append(recomputed)
    informed_bits = math.fsum(float(row["informed"]["useful_bits"]) for row in paired_rows)
    informed_energy = math.fsum(float(row["informed"]["system_energy_j"]) for row in paired_rows)
    neutral_bits = math.fsum(float(row["neutral"]["useful_bits"]) for row in paired_rows)
    neutral_energy = math.fsum(float(row["neutral"]["system_energy_j"]) for row in paired_rows)
    informed_intervals = sum(int(row["informed"]["total_user_intervals"]) for row in paired_rows)
    neutral_intervals = sum(int(row["neutral"]["total_user_intervals"]) for row in paired_rows)
    informed_served = sum(int(row["informed"]["served_user_intervals"]) for row in paired_rows)
    neutral_served = sum(int(row["neutral"]["served_user_intervals"]) for row in paired_rows)
    informed_ee = ratio_of_sums(informed_bits, informed_energy)
    neutral_ee = ratio_of_sums(neutral_bits, neutral_energy)
    informed_service = informed_served / informed_intervals if informed_intervals else 0.0
    neutral_service = neutral_served / neutral_intervals if neutral_intervals else 0.0
    checks = {
        "all_structural_guards": not guard_failures,
        "mean_paired_delta_positive": math.fsum(deltas) / EVALUATION_SEEDS > 0.0,
        "positive_on_at_least_four_seeds": sum(delta > 0.0 for delta in deltas) >= 4,
        "aggregate_ratio_of_sums_delta_positive": informed_ee > neutral_ee,
        "served_fraction_guard": informed_service >= neutral_service - SERVICE_GUARD,
    }
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "decision": "CONTINUE_10EP" if passed else "STOP_AND_REDESIGN_C1",
        "checks": checks,
        "guard_failures": list(guard_failures),
        "metrics": {
            "paired_deltas_bits_per_j": deltas,
            "mean_paired_delta_bits_per_j": math.fsum(deltas) / EVALUATION_SEEDS,
            "positive_seed_count": sum(delta > 0.0 for delta in deltas),
            "informed_ratio_of_sums_ee_bits_per_j": informed_ee,
            "neutral_ratio_of_sums_ee_bits_per_j": neutral_ee,
            "aggregate_delta_bits_per_j": informed_ee - neutral_ee,
            "informed_served_fraction": informed_service,
            "neutral_served_fraction": neutral_service,
            "served_fraction_delta": informed_service - neutral_service,
        },
    }


def _new_initial_state(
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


def _episode_payload(row: Any) -> dict[str, Any]:
    payload = asdict(row)
    if not all(
        math.isfinite(float(payload[field]))
        for field in (
            "useful_bits",
            "system_energy_j",
            "system_ee_bits_per_j",
            "mean_system_power_w",
            "mean_system_throughput_bps",
            "served_fraction",
        )
    ):
        raise RuntimeError("C1 consumer evaluation produced non-finite totals")
    return payload


def _valid_digest(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_branch_schedule(
    *, branch_dir: Path, result: Mapping[str, Any], label: str
) -> tuple[list[str], dict[str, Any]]:
    """Recompute the exact 4 x 10 C1-only routing schedule from receipts."""

    failures: list[str] = []
    receipt_path = branch_dir / "main-update-receipts.json"
    episode_path = branch_dir / "episode-logs.json"
    specialist_path = branch_dir / "specialist-replay-receipts.json"
    receipts = json.loads(receipt_path.read_text(encoding="utf-8"))
    episodes = json.loads(episode_path.read_text(encoding="utf-8"))
    specialist_receipts = json.loads(specialist_path.read_text(encoding="utf-8"))
    expected_count = EPISODES * 10
    if not isinstance(receipts, list) or len(receipts) != expected_count:
        failures.append(f"{label}_main_receipt_denominator")
        receipts = []
    admitted_bundle_ids: list[str] = []
    applied_bundle_ids: list[str] = []
    warmup_indices: list[int] = []
    update_indices: list[int] = []
    for index, row in enumerate(receipts):
        episode = index // 10
        step = index % 10
        if not isinstance(row, Mapping) or row.get("episode") != episode or row.get("step") != step:
            failures.append(f"{label}_main_receipt_order_{index}")
            continue
        quota = row.get("quota_receipt")
        if not isinstance(quota, Mapping):
            failures.append(f"{label}_quota_receipt_missing_{index}")
            continue
        specialist_ids = quota.get("specialist_bundle_ids")
        admitted_ids = quota.get("admitted_specialist_bundle_ids")
        if (
            not isinstance(admitted_ids, list)
            or len(admitted_ids) != 1
            or not isinstance(admitted_ids[0], str)
            or not admitted_ids[0]
        ):
            failures.append(f"{label}_c1_admission_unit_{index}")
        else:
            admitted_bundle_ids.append(admitted_ids[0])
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
            failures.append(f"{label}_quota_shortage_{index}")
            continue
        if replay_size < batch_size:
            warmup_indices.append(index)
            if (
                quota.get("mode") != "warmup_no_update"
                or quota.get("source_units") != []
                or specialist_ids != []
                or quota.get("canonical_replay_rng_sample_consumed") is not False
                or quota.get("unusable_specialist_bundle_ids") != []
            ):
                failures.append(f"{label}_warmup_schedule_{index}")
        else:
            update_indices.append(index)
            if (
                quota.get("mode") != "source_unit_mean"
                or quota.get("unit_definition")
                != "one_complete_atomic_bundle_per_source"
                or quota.get("source_units") != ["Main", "C1"]
                or specialist_ids != admitted_ids
                or quota.get("unusable_specialist_bundle_ids") != []
                or quota.get("canonical_replay_rng_sample_consumed") is not True
            ):
                failures.append(f"{label}_source_unit_schedule_{index}")
            elif isinstance(specialist_ids, list) and specialist_ids:
                applied_bundle_ids.append(specialist_ids[0])
    if (
        not warmup_indices
        or warmup_indices != list(range(len(warmup_indices)))
        or update_indices != list(range(len(warmup_indices), expected_count))
    ):
        failures.append(f"{label}_warmup_prefix")
    if (
        len(admitted_bundle_ids) != expected_count
        or len(set(admitted_bundle_ids)) != expected_count
    ):
        failures.append(f"{label}_admitted_bundle_id_uniqueness")
    if (
        len(applied_bundle_ids) != len(update_indices)
        or len(set(applied_bundle_ids)) != len(update_indices)
        or applied_bundle_ids
        != [admitted_bundle_ids[index] for index in update_indices]
    ):
        failures.append(f"{label}_applied_bundle_id_lineage")

    expected_ledger = {"C1": "route", "C2": "shadow", "C3": "shadow"}
    if not isinstance(episodes, list) or len(episodes) != EPISODES:
        failures.append(f"{label}_episode_receipt_denominator")
        episodes = []
    comparator_by_episode: dict[int, str] = {}
    for index, row in enumerate(episodes):
        comparator = (
            row.get("frozen_main_comparator_sha256")
            if isinstance(row, Mapping)
            else None
        )
        if (
            not isinstance(row, Mapping)
            or row.get("episode") != index
            or row.get("main_update_count") != 10
            or row.get("gate_ledger") != expected_ledger
            or not _valid_digest(comparator)
        ):
            failures.append(f"{label}_episode_schedule_{index}")
        else:
            comparator_by_episode[index] = str(comparator)
    if len(set(comparator_by_episode.values())) != EPISODES:
        failures.append(f"{label}_comparator_versions_not_per_block")

    if not isinstance(specialist_receipts, list):
        failures.append(f"{label}_specialist_receipts_malformed")
        specialist_receipts = []
    c1_receipts = [
        row
        for row in specialist_receipts
        if isinstance(row, Mapping) and row.get("source") == "C1"
    ]
    if len(c1_receipts) != expected_count:
        failures.append(f"{label}_c1_specialist_receipt_denominator")
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
            failures.append(f"{label}_c1_comparator_lineage_{index}")

    dashboard = result.get("source_dashboard")
    if not isinstance(dashboard, Mapping):
        failures.append(f"{label}_source_dashboard_missing")
    else:
        if not isinstance(dashboard.get("C1"), Mapping) or dashboard["C1"].get("routed_bundles") != expected_count:
            failures.append(f"{label}_c1_routed_denominator")
        for source in ("C2", "C3"):
            if not isinstance(dashboard.get(source), Mapping) or dashboard[source].get("routed_bundles") != 0:
                failures.append(f"{label}_{source.lower()}_must_remain_shadow")
    if result.get("consumed_specialist_bundle_count") != expected_count:
        failures.append(f"{label}_durable_consumed_denominator")

    return failures, {
        "branch": label,
        "status": "PASS" if not failures else "FAIL",
        "logical_steps": expected_count,
        "warmup_steps": len(warmup_indices),
        "warmup_indices": warmup_indices,
        "source_unit_updates": len(update_indices),
        "source_unit_update_indices": update_indices,
        "unique_admitted_c1_bundle_ids": len(set(admitted_bundle_ids)),
        "unique_applied_c1_bundle_ids": len(set(applied_bundle_ids)),
        "main_update_receipts_path": str(receipt_path),
        "main_update_receipts_sha256": sha256_file(receipt_path),
        "episode_logs_path": str(episode_path),
        "episode_logs_sha256": sha256_file(episode_path),
        "specialist_replay_receipts_path": str(specialist_path),
        "specialist_replay_receipts_sha256": sha256_file(specialist_path),
        "failures": failures,
    }


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--c1-exp-corpus-manifest", type=Path, required=True)
    parser.add_argument("--source-gate-result", type=Path, required=True)
    parser.add_argument("--source-gate-verification", type=Path, required=True)
    parser.add_argument("--corpus-verification", type=Path, required=True)
    parser.add_argument("--pretransfer-gate-result", type=Path, required=True)
    parser.add_argument("--prereg", type=Path, default=CANONICAL_PREREG)
    parser.add_argument("--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT))
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    output_dir = args.output_dir.expanduser().resolve()
    seed_manifest_path = args.seed_manifest.expanduser().resolve()
    corpus_manifest_path = args.c1_exp_corpus_manifest.expanduser().resolve()
    source_gate_path = args.source_gate_result.expanduser().resolve()
    source_gate_verification_path = args.source_gate_verification.expanduser().resolve()
    verification_path = args.corpus_verification.expanduser().resolve()
    pretransfer_path = args.pretransfer_gate_result.expanduser().resolve()
    prereg_path = args.prereg.expanduser().resolve()
    for path in (
        seed_manifest_path,
        corpus_manifest_path,
        source_gate_path,
        source_gate_verification_path,
        verification_path,
        pretransfer_path,
        prereg_path,
        SPEC,
        METHOD,
        CONCEPT,
        TEST_FILE,
        VALIDATOR,
        VALIDATOR_TEST,
        FREEZE,
        FREEZE_TEST,
        SWEEP_EVALUATOR,
        PARITY_CHECKER,
        PRETRANSFER_VALIDATOR,
        SOURCE_GATE_VERIFIER,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if (
        prereg_path != Path(CANONICAL_PREREG).resolve()
        or sha256_file(prereg_path) != CANONICAL_PREREG_BYTE_SHA256
    ):
        raise RuntimeError("C1 efficacy screen requires the canonical sealed preregistration")
    prereg_record = read_prereg(prereg_path)
    archive = TleArchive(args.tle_root.expanduser().resolve())
    ephemeris = assert_ephemeris_matches_record(prereg_record, archive=archive)
    source_gate = json.loads(source_gate_path.read_text(encoding="utf-8"))
    _validate_source_gate_verification(
        source_gate_path, source_gate_verification_path
    )
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    if (
        source_gate.get("status") != "PASS"
        or source_gate.get("decision") != "PASS_TO_C1_CONSUMER_GATE"
        or verification.get("status") != "PASS"
        or verification.get("claim_ceiling") != "C1_SPECIALIST_PREFILL_ONLY_NEVER_MAIN"
    ):
        raise RuntimeError("C1 efficacy-screen source/corpus prerequisites are not closed")
    try:
        pretransfer_evidence = validate_c1_pretransfer_result(pretransfer_path)
    except C1PretransferGateValidationError as exc:
        raise RuntimeError(
            f"C1 efficacy-screen pre-transfer Gate 2 prerequisite failed: {exc}"
        ) from exc
    if (
        pretransfer_evidence.get("status") != "PASS"
        or pretransfer_evidence.get("decision") != "ROUTE"
    ):
        raise RuntimeError("C1 pre-transfer Gate 2 does not permit this micro-screen")
    corpus = load_verified_c1_corpus(corpus_manifest_path)
    if verification.get("manifest_sha256") != corpus.manifest_sha256 or verification.get("corpus_sha256") != corpus.corpus_sha256:
        raise RuntimeError("C1 corpus verification does not bind the supplied corpus")

    corpus_manifest = json.loads(corpus_manifest_path.read_text(encoding="utf-8"))
    corpus_source_path = Path(
        corpus_manifest["authority"]["source_gate_result_path"]
    ).resolve()
    if (
        corpus_source_path != source_gate_path
        or corpus_manifest["authority"].get("source_gate_result_sha256")
        != sha256_file(source_gate_path)
    ):
        raise RuntimeError("supplied C1 Source Gate A is not the corpus predecessor")
    checkpoint_path = Path(corpus_manifest["authority"]["checkpoint_path"]).resolve()
    pretransfer_evidence = _validate_pretransfer_lineage(
        pretransfer_path,
        checkpoint=checkpoint_path,
        corpus_manifest=corpus_manifest_path,
    )
    checkpoint_payload = read_checkpoint(checkpoint_path, map_location="cpu")
    checkpoint_seeds = {
        int(checkpoint_payload.train_seed),
        int(checkpoint_payload.env_seed),
        int(checkpoint_payload.mobility_seed),
    }
    gate1_seeds = _gate1_prior_seeds(pretransfer_path)
    known_prior = (
        _authenticated_parent_seed_values(
            source_gate, label="C1 Source Gate", base=source_gate_path.parent
        )
        | _authenticated_parent_seed_values(
            corpus_manifest,
            label="C1 corpus build",
            base=corpus_manifest_path.parent,
        )
        | checkpoint_seeds
        | gate1_seeds
        | {
            20260822,
            20260823,
            *range(2026082401, 2026082431),
            *range(2026082601, 2026082611),
            *range(2026082701, 2026082711),
            *range(2026082801, 2026082831),
        }
    )
    bindings = _authority_bindings(
        prereg=prereg_path,
        source_gate=source_gate_path,
        source_gate_verification=source_gate_verification_path,
        corpus_manifest=corpus_manifest_path,
        corpus_verification=verification_path,
        pretransfer_gate=pretransfer_path,
        checkpoint=checkpoint_path,
        archive=archive,
        ephemeris=ephemeris,
    )
    seed_manifest = _validate_seed_manifest(
        seed_manifest_path,
        bindings=bindings,
        known_prior_seeds=known_prior,
        checkpoint_seeds=checkpoint_seeds,
        gate1_seeds=gate1_seeds,
    )
    execution_ledger = _reserve_single_execution(
        seed_manifest=seed_manifest_path,
        output_dir=output_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    common_seed = {
        "train_seed": int(seed_manifest["training_seed"]),
        "env_seed": int(seed_manifest["environment_seed"]),
        "mobility_seed": int(seed_manifest["mobility_seed"]),
    }
    configs = {
        "informed": _short_config(
            prereg_path,
            arm="F111",
            episodes=EPISODES,
            epsilon_decay_episodes=3,
            target_update_every=2,
            learning_rate=DEFAULT_LEARNING_RATE,
        ),
        "neutral": _short_config(
            prereg_path,
            arm="A011",
            episodes=EPISODES,
            epsilon_decay_episodes=3,
            target_update_every=2,
            learning_rate=DEFAULT_LEARNING_RATE,
        ),
    }
    initial_parity = compare_states(
        _new_initial_state(archive=archive, config=configs["informed"], **common_seed),
        _new_initial_state(archive=archive, config=configs["neutral"], **common_seed),
    )
    guard_failures: list[str] = []
    if (
        initial_parity.get("status") != "PASS"
        or initial_parity.get("exact_after_descriptive_metadata_normalisation")
        is not True
        or initial_parity.get("first_difference") is not None
    ):
        guard_failures.append("initial_main_state_parity")

    gates = GateLedger(C1="route", C2="shadow", C3="shadow")
    branch_results: dict[str, Any] = {}
    schedule_receipts: dict[str, Any] = {}
    for label, arm in (("informed", "F111"), ("neutral", "A011")):
        branch_dir = output_dir / label
        branch_dir.mkdir()
        branch_results[label] = run_treatment(
            arm=arm,
            output_dir=branch_dir,
            archive=archive,
            config=configs[label],
            users=USERS,
            gates=gates,
            acrm_eta=DEFAULT_ACRM_ETA,
            c1_corpus_manifest=corpus_manifest_path,
            **common_seed,
        )
        result = branch_results[label]
        if result.get("episodes") != EPISODES or result.get("gates") != asdict(gates):
            guard_failures.append(f"{label}_schedule_or_gate_ledger")
        prefill = result.get("c1_prefill", {})
        expected_branch = "local" if label == "informed" else "control"
        if (
            prefill.get("bundles") != 31
            or prefill.get("corpus_branch") != expected_branch
            or prefill.get("selection") != "paired_high_mid_context_intersection"
            or not isinstance(prefill.get("matched_contexts"), list)
            or len(prefill["matched_contexts"]) != 31
            or prefill.get("enters_main") is not False
        ):
            guard_failures.append(f"{label}_prefill_denominator")
        schedule_failures, schedule_receipt = _validate_branch_schedule(
            branch_dir=branch_dir,
            result=result,
            label=label,
        )
        guard_failures.extend(schedule_failures)
        schedule_receipts[label] = schedule_receipt

    if (
        branch_results["informed"]["c1_prefill"].get("matched_contexts")
        != branch_results["neutral"]["c1_prefill"].get("matched_contexts")
    ):
        guard_failures.append("branch_prefill_context_mismatch")
    if (
        schedule_receipts["informed"].get("warmup_indices")
        != schedule_receipts["neutral"].get("warmup_indices")
        or schedule_receipts["informed"].get("source_unit_update_indices")
        != schedule_receipts["neutral"].get("source_unit_update_indices")
    ):
        guard_failures.append("branch_warmup_or_update_schedule_mismatch")

    evaluated: dict[str, dict[int, dict[str, Any]]] = {"informed": {}, "neutral": {}}
    for label in ("informed", "neutral"):
        checkpoint = Path(branch_results[label]["checkpoint"])
        payload = read_checkpoint(checkpoint, map_location="cpu")
        checkpoint_sha = sha256_file(checkpoint)
        for seed in seed_manifest["evaluation_seeds"]:
            row = evaluate_checkpoint_point(
                archive=archive,
                checkpoint_path=checkpoint,
                checkpoint_payload=payload,
                arm=label,
                checkpoint_sha256=checkpoint_sha,
                users=USERS,
                evaluation_seed=int(seed),
            )
            evaluated[label][int(seed)] = _episode_payload(row)
    paired_rows = [
        {
            "evaluation_seed": int(seed),
            "informed": evaluated["informed"][int(seed)],
            "neutral": evaluated["neutral"][int(seed)],
            "delta_ee_bits_per_j": (
                float(evaluated["informed"][int(seed)]["system_ee_bits_per_j"])
                - float(evaluated["neutral"][int(seed)]["system_ee_bits_per_j"])
            ),
        }
        for seed in seed_manifest["evaluation_seeds"]
    ]
    raw = {
        "schema": RAW_SCHEMA,
        "status": "complete",
        "claim_ceiling": CLAIM_CEILING,
        "initial_main_parity": initial_parity,
        "paired_rows": paired_rows,
        "branch_results": branch_results,
        "schedule_receipts": schedule_receipts,
        "pretransfer_gate_evidence": pretransfer_evidence,
        "execution_ledger_path": str(execution_ledger),
        "execution_ledger_sha256": sha256_file(execution_ledger),
    }
    raw_path = output_dir / "c1-postgate-efficacy-microscreen-raw.json"
    _write_json(raw_path, raw)
    decision = decide_c1_efficacy_screen(
        paired_rows, guard_failures=guard_failures
    )
    result = {
        "schema": RESULT_SCHEMA,
        "source": "C1",
        "status": decision["status"],
        "decision": decision["decision"],
        "prerequisites_closed": True,
        "claim_ceiling": CLAIM_CEILING,
        "screen_type": "postgate-directional-efficacy",
        "routing_authority": False,
        "checks": decision["checks"],
        "guard_failures": decision["guard_failures"],
        "metrics": decision["metrics"],
        "protocol": {
            "episodes": EPISODES,
            "training_users": USERS,
            "evaluation_users": USERS,
            "evaluation_seed_count": EVALUATION_SEEDS,
            "evaluation_partition": "TRAIN",
            "evaluation_seed_role": "fresh_disjoint_developmental_not_held_out",
            "main_only_evaluation": True,
            "routed_sources": ["C1"],
            "neutral_source": "matched_uniform_C1",
            "service_guard": SERVICE_GUARD,
            "decision_rule": "directional_continuation_not_significance_test",
            "sign_component_null_probability": 6.0 / 32.0,
            "outcome_use": "CONTINUE_10EP_OR_STOP_AND_REDESIGN_C1",
        },
        "authority": {
            **bindings,
            "spec_path": str(SPEC),
            "runner_path": str(Path(__file__).resolve()),
            "test_path": str(TEST_FILE),
            "validator_path": str(VALIDATOR),
            "validator_test_path": str(VALIDATOR_TEST),
            "freeze_path": str(FREEZE),
            "freeze_test_path": str(FREEZE_TEST),
            "method_path": str(METHOD),
            "concept_path": str(CONCEPT),
            "run_short_ep_path": str(HERE / "run_short_ep.py"),
            "routing_core_path": str(HERE / "smc_er_core.py"),
            "roles_path": str(HERE / "smc_er_roles.py"),
            "corpus_loader_path": str(HERE / "c1_exp_corpus.py"),
            "sweep_evaluator_path": str(SWEEP_EVALUATOR),
            "parity_checker_path": str(PARITY_CHECKER),
            "pretransfer_validator_path": str(PRETRANSFER_VALIDATOR),
            "source_gate_verifier_path": str(SOURCE_GATE_VERIFIER),
            "corrective_replay_addendum_path": str(CORRECTIVE_REPLAY_ADDENDUM),
            "corrective_replay_verifier_path": str(CORRECTIVE_REPLAY_VERIFIER),
            "corrective_replay_verifier_test_path": str(
                CORRECTIVE_REPLAY_VERIFIER_TEST
            ),
            "source_seed_provenance_correction_path": str(
                SOURCE_SEED_PROVENANCE_CORRECTION
            ),
            "prereg_path": str(prereg_path),
            "source_gate_result_path": str(source_gate_path),
            "source_gate_verification_path": str(source_gate_verification_path),
            "corpus_manifest_path": str(corpus_manifest_path),
            "corpus_verification_path": str(verification_path),
            "pretransfer_gate_result_path": str(pretransfer_path),
            "checkpoint_path": str(checkpoint_path),
            "seed_manifest_path": str(seed_manifest_path),
            "seed_manifest_sha256": sha256_file(seed_manifest_path),
            "execution_ledger_path": str(execution_ledger),
            "execution_ledger_sha256": sha256_file(execution_ledger),
            "raw_rows_path": str(raw_path),
            "raw_rows_sha256": sha256_file(raw_path),
            "c1_exp_corpus_sha256": corpus.corpus_sha256,
        },
    }
    result_path = output_dir / "c1-postgate-efficacy-microscreen-result.json"
    _write_json(result_path, result)
    print(result_path)
    return 0 if decision["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
