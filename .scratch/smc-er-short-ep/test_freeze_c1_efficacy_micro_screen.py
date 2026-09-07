from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "freeze_c1_efficacy_micro_screen",
    HERE / "freeze_c1_efficacy_micro_screen.py",
)
assert SPEC is not None and SPEC.loader is not None
F = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = F
SPEC.loader.exec_module(F)


SOURCE_GATE = Path(
    "/tmp/smc-er-c1-source-gate-a-canonical-tle-20260828-v3/"
    "c1-source-gate-a-result.json"
)
SOURCE_VERIFICATION = Path(
    "/tmp/smc-er-c1-source-gate-a-canonical-tle-20260828-v3/verification-v2.json"
)
CORPUS_MANIFEST = Path(
    "/tmp/smc-er-c1-exp-corpus-canonical-tle-20260828-v3/"
    "c1-exp-corpus-manifest.json"
)
CHECKPOINT = Path("artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt")
PRETRANSFER_GATE = Path(
    "/tmp/smc-er-c1-pretransfer-gate2-canonical-tle-20260828-v4/"
    "c1-pretransfer-consumer-gate-result.json"
)


def test_candidate_derivation_is_repeatable_and_uint32():
    closure = "a" * 64
    first = [F._derive_candidate(closure, index) for index in range(12)]
    second = [F._derive_candidate(closure, index) for index in range(12)]
    assert first == second
    assert len(set(first)) == len(first)
    assert all(0 <= value < 2**32 for value in first)


def test_prior_set_explicitly_contains_corrected_checkpoint_seeds():
    if not all(
        path.is_file()
        for path in (SOURCE_GATE, CORPUS_MANIFEST, PRETRANSFER_GATE, CHECKPOINT)
    ):
        pytest.fail("canonical Source/corpus/Gate2/checkpoint authority is missing")
    prior, checkpoint, gate1 = F._prior_seeds(
        source_gate=SOURCE_GATE,
        corpus_manifest=CORPUS_MANIFEST,
        pretransfer_gate=PRETRANSFER_GATE,
        checkpoint=CHECKPOINT,
    )
    assert checkpoint == {42, 1337, 7}
    assert checkpoint.issubset(prior)
    assert gate1.issubset(prior)


def test_repository_search_includes_hidden_ignored_seed_authority():
    authority = F.HERE / "c1-source-gate-a-seeds-v1.json"
    seed = json.loads(authority.read_text(encoding="utf-8"))["seeds"][0]
    matches = {Path(path).resolve() for path in F._repo_matches(seed)}
    assert authority.resolve() in matches


def test_disjoint_seed_derivation_binds_runtime_specialist_seeds(monkeypatch):
    monkeypatch.setattr(F, "_repo_matches", lambda _seed: ())
    seeds, attempts, runtime = F.derive_disjoint_seeds(
        closure_sha256="b" * 64,
        prior={1, 2, 3},
    )

    assert len(seeds) == F.SEED_COUNT
    assert len(set(seeds)) == F.SEED_COUNT
    assert attempts[-1]["accepted"] is True
    assert runtime == F._runtime_derived_seeds(seeds[0])
    assert not (set(runtime.values()) & set(seeds))


def test_all_three_surfaces_hash_the_same_complete_main_source_tree():
    import c1_efficacy_micro_screen_validator as validator
    import run_c1_consumer_gate as runner

    assert F._main_source_tree_binding() == runner._main_source_tree_binding()
    assert F._main_source_tree_binding() == validator._main_source_tree_binding()


def test_freeze_and_runner_share_one_complete_closure_test_set():
    assert F.TEST_FILES == F.screen.CLOSURE_TEST_FILES
    digest, count = F.screen._closure_test_tree_binding()
    assert len(digest) == 64
    assert count == len(F.TEST_FILES)


def test_source_gate_verification_must_be_exact_current_replay(tmp_path):
    if not all(path.is_file() for path in (SOURCE_GATE, SOURCE_VERIFICATION)):
        pytest.fail("canonical Source Gate result or verification is missing")
    replay = F._validate_source_gate_verification(SOURCE_GATE, SOURCE_VERIFICATION)
    assert replay["status"] == "PASS"

    tampered = dict(replay)
    tampered["paired_rows"] = int(tampered["paired_rows"]) - 1
    tampered_path = tmp_path / "tampered-source-verification.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(RuntimeError, match="exact current-authority replay"):
        F._validate_source_gate_verification(SOURCE_GATE, tampered_path)


def test_pytest_elapsed_time_is_removed_from_seed_material():
    left = F._normalise_pytest_stdout("41 passed in 4.92s")
    right = F._normalise_pytest_stdout("41 passed in 5.31s")
    assert left == right == "41 passed in <elapsed>s"


def test_single_freeze_lock_is_atomic(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "FREEZE_LOCK", tmp_path / "freeze.lock")
    first = F._acquire_freeze_lock()
    try:
        with pytest.raises(RuntimeError, match="another C1 efficacy freeze"):
            F._acquire_freeze_lock()
    finally:
        first.close()
    second = F._acquire_freeze_lock()
    second.close()
