"""W-204 -- immutable result-directory closure for the V0.23 LC-SRS gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
OBS = REPO / ".scratch" / "multi-catfish-v023-c3-observability"
MODULE_PATH = OBS / "seal_v023_lcsrs_result_directory.py"
CONTRACT = REPO / "docs" / "MULTI-CATFISH-MCRL-V023-LC-SRS-OBSERVABILITY-GATE-CONTRACT-2026-09-05.md"
ADDENDUM = REPO / "docs" / "MULTI-CATFISH-MCRL-V023-EXECUTION-PARAMETER-ADDENDUM-2026-09-05.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("test_w204_result_seal", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="ascii",
    )


def _run_root(tmp_path: Path) -> Path:
    root = tmp_path / "run"
    _write_json(
        root / "LAUNCH-METADATA.json",
        {
            "schema": "multi-catfish-mcrl-v023-lcsrs-server-run-v1",
            "split": "TRAIN_DEVELOPMENT",
            "test_split_opened": False,
            "episode_training": False,
        },
    )
    return root


def _prepare(module, root: Path, tmp_path: Path) -> None:
    manifest = tmp_path / "PREFLIGHT-MANIFEST.json"
    _write_json(manifest, {"bindings": [], "configuration": {}})
    digest = tmp_path / "PREFLIGHT-MANIFEST.sha256"
    digest.write_text(
        f"{module.file_sha256(manifest)}  PREFLIGHT-MANIFEST.json\n",
        encoding="ascii",
    )
    module.prepare_authority(
        run_root=root,
        contract=CONTRACT,
        addendum=ADDENDUM,
        preflight_manifest=manifest,
        preflight_digest=digest,
    )


def test_full_result_seal_hashes_every_result_before_complete(tmp_path: Path) -> None:
    module = _load_module()
    root = _run_root(tmp_path)
    _prepare(module, root, tmp_path)
    source = root / "final-verification.json"
    _write_json(
        source,
        {
            "status": "PASS_FINAL_INTEGRITY",
            "integrity_status": "VERIFIED",
            "source_count": 8,
            "fit_count": 48,
            "composition_count": 48,
            "contract_sha256": module.CONTRACT_SHA256,
            "execution_addendum_sha256": module.ADDENDUM_SHA256,
            "preflight_manifest_sha256": module.file_sha256(
                root / "authority" / "PREFLIGHT-MANIFEST.json"
            ),
            "scientific_claim": False,
            "c3_decision": "STOP_OBSERVABILITY",
            "test_split_opened": False,
            "episode_training": False,
        },
    )
    manifest, complete = module.seal_result_directory(
        run_root=root,
        verification_path=source,
        kind="full",
    )
    lines = manifest.read_text(encoding="ascii").splitlines()
    names = {line.split("  ", 1)[1] for line in lines}
    expected = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"MANIFEST.sha256", "COMPLETE"}
    }
    assert names == expected
    assert "result.json" in names
    assert "verification.json" in names
    assert "authority/AUTHORITY.json" in names
    assert complete.read_text(encoding="ascii").split()[0] == module.file_sha256(manifest)
    result = json.loads((root / "result.json").read_text(encoding="ascii"))
    assert result["thresholds"] == module.FROZEN_THRESHOLDS
    assert result["design_basis"] == module.FROZEN_DESIGN_BASIS
    verification = json.loads((root / "verification.json").read_text(encoding="ascii"))
    core = dict(result)
    core.pop("thresholds")
    core.pop("design_basis")
    assert core == verification


def test_insufficient_pairs_seals_without_fit_or_composition(tmp_path: Path) -> None:
    module = _load_module()
    root = _run_root(tmp_path)
    _prepare(module, root, tmp_path)
    source = root / "source-stage-verification.json"
    _write_json(
        source,
        {
            "status": "VERIFIED_SOURCE_STAGE",
            "decision": "INSUFFICIENT_PAIRS",
            "claim_ceiling": "SOURCE_ONLY",
            "contract_sha256": module.CONTRACT_SHA256,
            "preflight_manifest_sha256": module.file_sha256(
                root / "authority" / "PREFLIGHT-MANIFEST.json"
            ),
            "source_count": 8,
            "fit_launched": False,
            "learner_update": False,
            "test_split_opened": False,
            "episode_training": False,
            "source_panel": {
                "context_status": "CONTEXT_DIAGNOSTICS_PASS",
                "c1": {"passes": True},
                "c2": {"passes": True},
                "predicates": {
                    "pair_coverage": False,
                    "mechanics": True,
                    "physical_signature": True,
                    "target_support": False,
                },
                "pair_count": 23,
                "mechanics_pass_count": 23,
                "target_support_count": 23,
                "placebo_folds": [{"held_out_world": 2026121705, "passed": False}],
                "world_results": [{"world": 2026121705, "pair_count": 0}],
            },
        },
    )
    module.seal_result_directory(
        run_root=root,
        verification_path=source,
        kind="source-insufficient",
    )
    result = json.loads((root / "result.json").read_text(encoding="ascii"))
    assert result["c3_decision"] == "INSUFFICIENT_PAIRS"
    assert result["fit_count"] == 0
    assert result["composition_count"] == 0
    assert result["episode_training"] is False
    assert result["context_status"] == "CONTEXT_DIAGNOSTICS_PASS"
    assert result["denominators"]["pair_count"] == 23
    assert result["predicates"]["held_out_learner"] == "NOT_EVALUATED_SOURCE_STAGE_STOP"
    assert result["predicates"]["target_support"] is False
    assert result["thresholds"] == module.FROZEN_THRESHOLDS


def test_seal_is_write_once_and_rejects_invalid_full_receipt(tmp_path: Path) -> None:
    module = _load_module()
    root = _run_root(tmp_path)
    _prepare(module, root, tmp_path)
    source = root / "final-verification.json"
    _write_json(
        source,
        {
            "status": "INVALID_RUN",
            "integrity_status": "INVALID",
            "source_count": 8,
            "fit_count": 48,
            "composition_count": 48,
            "contract_sha256": module.CONTRACT_SHA256,
            "execution_addendum_sha256": module.ADDENDUM_SHA256,
            "preflight_manifest_sha256": module.file_sha256(
                root / "authority" / "PREFLIGHT-MANIFEST.json"
            ),
            "scientific_claim": False,
            "test_split_opened": False,
            "episode_training": False,
        },
    )
    with pytest.raises(module.V023ResultSealError, match="did not pass integrity"):
        module.seal_result_directory(
            run_root=root,
            verification_path=source,
            kind="full",
        )


def test_prepare_rejects_symlinked_authority_directory(tmp_path: Path) -> None:
    module = _load_module()
    root = _run_root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "authority").symlink_to(outside, target_is_directory=True)
    manifest = tmp_path / "PREFLIGHT-MANIFEST.json"
    _write_json(manifest, {"bindings": [], "configuration": {}})
    digest = tmp_path / "PREFLIGHT-MANIFEST.sha256"
    digest.write_text(
        f"{module.file_sha256(manifest)}  PREFLIGHT-MANIFEST.json\n",
        encoding="ascii",
    )
    with pytest.raises(module.V023ResultSealError, match="authority snapshot directory"):
        module.prepare_authority(
            run_root=root,
            contract=CONTRACT,
            addendum=ADDENDUM,
            preflight_manifest=manifest,
            preflight_digest=digest,
        )
    assert list(outside.iterdir()) == []


def test_seal_reauthenticates_every_copied_authority_file(tmp_path: Path) -> None:
    module = _load_module()
    root = _run_root(tmp_path)
    _prepare(module, root, tmp_path)
    copied_contract = root / "authority" / CONTRACT.name
    copied_contract.write_bytes(copied_contract.read_bytes() + b"tamper")
    verification = root / "final-verification.json"
    _write_json(
        verification,
        {
            "status": "PASS_FINAL_INTEGRITY",
            "integrity_status": "VERIFIED",
            "source_count": 8,
            "fit_count": 48,
            "composition_count": 48,
            "contract_sha256": module.CONTRACT_SHA256,
            "execution_addendum_sha256": module.ADDENDUM_SHA256,
            "preflight_manifest_sha256": module.file_sha256(
                root / "authority" / "PREFLIGHT-MANIFEST.json"
            ),
            "scientific_claim": False,
            "test_split_opened": False,
            "episode_training": False,
        },
    )
    with pytest.raises(module.V023ResultSealError, match="authority snapshot digest"):
        module.seal_result_directory(
            run_root=root,
            verification_path=verification,
            kind="full",
        )
