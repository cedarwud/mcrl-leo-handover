from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_c1_exp_corpus", HERE / "build_c1_exp_corpus.py"
)
assert SPEC is not None and SPEC.loader is not None
B = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = B
SPEC.loader.exec_module(B)


def rows():
    return [
        {
            "bundle_id": f"b{index:02d}",
            "system_ee_bits_per_j": float(index // 2),
            "seed": index // 10,
            "step": index % 10,
        }
        for index in range(50)
    ]


def test_strata_have_frozen_counts_and_tie_order():
    strata = B.assign_strata(rows())
    assert list(strata.values()).count("high") == 17
    assert list(strata.values()).count("mid") == 17
    assert list(strata.values()).count("low") == 16
    # b48 and b49 tie on EE; lower seed/step lineage ranks first.
    assert strata["b48"] == "high"


def test_strata_reject_wrong_denominator_and_duplicate_ids():
    with pytest.raises(ValueError, match="exactly 50"):
        B.assign_strata(rows()[:-1])
    duplicate = rows()
    duplicate[-1]["bundle_id"] = duplicate[0]["bundle_id"]
    with pytest.raises(ValueError, match="unique"):
        B.assign_strata(duplicate)


def test_build_control_rng_is_repeatable_but_fresh():
    first = B.control_rng(4)
    second = B.control_rng(4)
    assert first is not second
    assert first.integers(0, 10_000) == second.integers(0, 10_000)


def test_repository_relative_path_is_canonical_and_rejects_external_file(tmp_path):
    inside = B.REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
    assert B._repository_relative_posix(inside, label="checkpoint") == (
        "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
    )

    outside = tmp_path / "checkpoint.pt"
    outside.write_bytes(b"outside")
    with pytest.raises(RuntimeError, match="checkpoint.*repository-relative"):
        B._repository_relative_posix(outside, label="checkpoint")


def test_manifest_authority_declares_portable_file_and_runtime_tle_bindings(tmp_path):
    paths = {
        "checkpoint": B.REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
        "source_gate": B.REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
        "seed_manifest": B.REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
        "prereg": B.REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
    }
    authority = B._manifest_authority(
        checkpoint=paths["checkpoint"],
        checkpoint_sha256="a" * 64,
        source_gate=paths["source_gate"],
        source_gate_sha256="b" * 64,
        seed_manifest=paths["seed_manifest"],
        seed_manifest_sha256="c" * 64,
        prereg=paths["prereg"],
        prereg_sha256="d" * 64,
        ephemeris={"file_set_sha256": "e" * 64, "archive": {"file_count": 373}},
    )

    assert B.MANIFEST_SCHEMA == "smc-er-c1-exp-corpus-manifest-v2"
    assert B.PATH_BINDING == "repository_relative_posix_v1"
    assert B.TLE_ROOT_BINDING == "runtime_argument"
    assert "tle_root_path" not in authority
    assert all(
        isinstance(authority[field], str)
        and not authority[field].startswith("/")
        for field in (
            "checkpoint_path",
            "source_gate_result_path",
            "seed_manifest_path",
            "prereg_path",
        )
    )

    external = tmp_path / "source-gate.json"
    external.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="source gate.*repository-relative"):
        B._manifest_authority(
            checkpoint=paths["checkpoint"],
            checkpoint_sha256="a" * 64,
            source_gate=external,
            source_gate_sha256="b" * 64,
            seed_manifest=paths["seed_manifest"],
            seed_manifest_sha256="c" * 64,
            prereg=paths["prereg"],
            prereg_sha256="d" * 64,
            ephemeris={"file_set_sha256": "e" * 64, "archive": {"file_count": 373}},
        )


def test_build_path_validation_rejects_external_bound_input_and_output(tmp_path):
    inside = B.REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
    common = {
        "checkpoint": inside,
        "source_gate": inside,
        "seed_manifest": inside,
        "prereg": inside,
        "output_dir": B.REPO / "artifacts" / "c1-test-output",
    }

    outside_input = tmp_path / "source-gate.json"
    outside_input.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="source gate.*repository-relative"):
        B._validate_repository_paths(**{**common, "source_gate": outside_input})

    with pytest.raises(RuntimeError, match="output directory.*repository-relative"):
        B._validate_repository_paths(
            **{**common, "output_dir": tmp_path / "c1-output"}
        )
