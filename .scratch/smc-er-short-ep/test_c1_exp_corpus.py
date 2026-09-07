from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("c1_exp_corpus", HERE / "c1_exp_corpus.py")
assert SPEC is not None and SPEC.loader is not None
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)

REPO = HERE.parents[1]
PORTABLE_MANIFEST = (
    REPO
    / "artifacts/smc-er-c1-authority-20260828"
    / "smc-er-c1-exp-corpus-canonical-tle-20260829-v4"
    / "c1-exp-corpus-manifest.json"
)
TLE_ROOT = Path(
    os.environ.get("MCRL_V02_TLE_ROOT", "/tmp/mcrl-tle-frozen-20260820-v1")
).expanduser()


def test_expected_strata_are_deterministic_and_have_frozen_denominator():
    ee = np.asarray([float(index // 2) for index in range(50)])
    seeds = np.repeat(np.arange(5), 10)
    steps = np.tile(np.arange(10), 5)
    ids = np.asarray([f"b{index:02d}" for index in range(50)])
    strata = C._expected_strata(ee, seeds, steps, ids)
    assert np.count_nonzero(strata == "high") == 17
    assert np.count_nonzero(strata == "mid") == 17
    assert np.count_nonzero(strata == "low") == 16
    assert strata[48] == "high"


def test_digest_validator_rejects_uppercase_and_non_hex():
    assert C._is_digest("a" * 64)
    assert not C._is_digest("A" * 64)
    assert not C._is_digest("z" * 64)


def test_missing_manifest_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        C.load_verified_c1_corpus(tmp_path / "missing.json")


def test_repository_bound_path_survives_relocation_and_rejects_escape(tmp_path):
    repo = tmp_path / "relocated-repo"
    manifest = repo / "artifacts" / "c1" / "manifest.json"
    checkpoint = repo / "artifacts" / "training" / "checkpoint.pt"
    manifest.parent.mkdir(parents=True)
    checkpoint.parent.mkdir(parents=True)
    manifest.write_text("{}\n", encoding="utf-8")
    checkpoint.write_bytes(b"checkpoint")

    resolved = C._resolve_repository_path(
        repo,
        "artifacts/training/checkpoint.pt",
        field="checkpoint_path",
        kind="file",
    )
    assert resolved == checkpoint.resolve()

    for unsafe in (
        str(checkpoint.resolve()),
        "../outside.pt",
        "artifacts\\training\\checkpoint.pt",
    ):
        with pytest.raises(RuntimeError, match="repository-relative"):
            C._resolve_repository_path(
                repo,
                unsafe,
                field="checkpoint_path",
                kind="file",
            )

    outside = tmp_path / "outside.pt"
    outside.write_bytes(b"outside")
    link = repo / "artifacts" / "escape.pt"
    link.symlink_to(outside)
    with pytest.raises(RuntimeError, match="escapes repository"):
        C._resolve_repository_path(
            repo,
            "artifacts/escape.pt",
            field="checkpoint_path",
            kind="file",
        )


def test_real_corpus_prefill_uses_exact_shared_high_mid_contexts():
    if not PORTABLE_MANIFEST.is_file() or not TLE_ROOT.is_dir():
        pytest.skip("sealed C1 corpus is not present")
    corpus = C.load_verified_c1_corpus(
        PORTABLE_MANIFEST,
        tle_root=TLE_ROOT,
    )
    local = corpus.prefill_bundles(informed=True)
    control = corpus.prefill_bundles(informed=False)
    local_contexts = [tuple(row.provenance["matched_context"]) for row in local]
    control_contexts = [tuple(row.provenance["matched_context"]) for row in control]

    assert len(local) == len(control) == C.EXPECTED_MATCHED_PREFILL == 31
    assert local_contexts == control_contexts
    assert {
        name: sum(row.provenance["stratum"] == name for row in local)
        for name in C.EXPECTED_MATCHED_PREFILL_STRATA
    } == C.EXPECTED_MATCHED_PREFILL_STRATA
    assert {
        name: sum(row.provenance["stratum"] == name for row in control)
        for name in C.EXPECTED_MATCHED_PREFILL_STRATA
    } == C.EXPECTED_MATCHED_PREFILL_STRATA


def test_portable_manifest_requires_explicit_runtime_tle_root():
    if not PORTABLE_MANIFEST.is_file():
        pytest.skip("sealed C1 corpus is not present")
    with pytest.raises(RuntimeError, match="requires runtime tle_root"):
        C.load_verified_c1_corpus(PORTABLE_MANIFEST)
