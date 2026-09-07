"""Focused red-capable tests for the V0.23 100E server/seal boundary."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_100e_source_training_sealer_under_test",
    HERE / "verify_v023_100e_source_training.py",
)
assert SPEC is not None and SPEC.loader is not None
SEALER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SEALER
SPEC.loader.exec_module(SEALER)


def test_tree_manifest_covers_nested_files_and_changes_on_tamper(tmp_path: Path):
    root = tmp_path / "run"
    (root / "exports").mkdir(parents=True)
    (root / "canonical-status.json").write_bytes(b"status")
    (root / "exports" / "arm.pt").write_bytes(b"checkpoint")

    first = SEALER._tree_manifest(root)
    lines = first.decode("ascii").splitlines()
    assert [line.split("  ", 1)[1] for line in lines] == [
        "canonical-status.json",
        "exports/arm.pt",
    ]
    assert lines[0].startswith(hashlib.sha256(b"status").hexdigest())

    (root / "exports" / "arm.pt").write_bytes(b"tampered")
    second = SEALER._tree_manifest(root)
    assert second != first


def test_tree_manifest_rejects_symlink_and_special_boundary(tmp_path: Path):
    root = tmp_path / "run"
    root.mkdir()
    target = tmp_path / "outside"
    target.write_bytes(b"outside")
    link = root / "linked"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable in this filesystem")
    with pytest.raises(SEALER.V023SourceTrainingSealError, match="symlink"):
        SEALER._tree_manifest(root)


def test_preseal_tree_uses_an_exact_source_training_allowlist(tmp_path: Path):
    root = tmp_path / "run"
    root.mkdir()
    expected = SEALER._expected_preseal_files()
    assert len(expected) == 16
    assert "canonical-status.json" in expected
    assert "canonical-receipt.json" in expected
    assert "checkpoints/epoch-0100.runner.pt" in expected
    assert "checkpoint-receipts/epoch-0100.json" in expected
    assert "exports/epoch-0100.json" in expected
    for relative in expected:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    SEALER._assert_exact_preseal_tree(root)
    (root / "unexpected-evaluation.json").write_bytes(b"forbidden")
    with pytest.raises(SEALER.V023SourceTrainingSealError, match="unexpected"):
        SEALER._assert_exact_preseal_tree(root)


def test_failure_marker_is_explicit_write_once(tmp_path: Path):
    root = tmp_path / "run"
    root.mkdir()
    error = RuntimeError("runner failed at epoch 100")
    SEALER._write_failed(root, error)
    marker = root / "FAILED"
    assert marker.is_file() and not marker.is_symlink()
    payload = json.loads(marker.read_text(encoding="ascii"))
    assert payload["status"] == "FAILED_SOURCE_TRAINING_INTEGRITY"
    assert "epoch 100" in payload["reason"]
    original = marker.read_bytes()
    SEALER._write_failed(root, RuntimeError("a different failure"))
    assert marker.read_bytes() == original
    assert stat.S_ISREG(marker.stat(follow_symlinks=False).st_mode)


def test_launcher_is_fail_closed_and_does_not_change_frozen_values():
    launcher = (HERE / "sync_launch_v023_100e_source_training_server.sh").read_text(
        encoding="utf-8"
    )
    for token in (
        "server_host=${V023_SERVER_HOST:-sat}",
        "r7_seed_root=",
        "cp -a --",
        "COMPLETE",
        "FAILED",
        "tmux new-session",
        "source-training",
        "--epochs 100",
        "--execute",
        "factory/preflight exact GO",
        "R7_SEEDED_CLOSURE_PASS",
    ):
        assert token in launcher
    assert "/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r1" in launcher
    assert "TEST" in launcher
    assert "episode" in launcher.lower()
    assert 'export MCRL_V023_POST_R7_PROVIDER_CONFIG_PATH="$PROVIDER_CONFIG"' in launcher
    assert (
        'export MCRL_V023_POST_R7_PROVIDER_CONFIG_SHA256='
        '"$PROVIDER_CONFIG_SHA256"'
    ) in launcher
    assert (
        'receipt.get("claim_ceiling") != '
        '"TRAIN_DEVELOPMENT_SOURCE_TO_LEARNER_ONLY_NO_SIMULATOR_NO_EPISODE_NO_TEST_NO_EFFICACY"'
        in launcher
    )


def test_launcher_sealed_tree_check_excludes_only_root_markers_and_rejects_symlinks():
    launcher = (HERE / "sync_launch_v023_100e_source_training_server.sh").read_text(
        encoding="utf-8"
    )
    assert 'relative not in {"MANIFEST.sha256", "COMPLETE"}' in launcher
    assert 'if path.is_symlink():' in launcher
    assert 'contains a symlink' in launcher
    assert 'path.name not in {"MANIFEST.sha256", "COMPLETE"}' not in launcher


def test_frozen_sidecar_uses_package_basename_convention():
    assert SEALER._frozen_sidecar(Path("contract.md")) == Path("contract.sha256")
    assert SEALER._frozen_sidecar(Path("model.json")) == Path("model.sha256")


def test_launcher_uses_existing_frozen_sidecar_names():
    launcher = (HERE / "sync_launch_v023_100e_source_training_server.sh").read_text(
        encoding="utf-8"
    )
    assert 'sidecar = path.with_suffix(".sha256")' in launcher


def test_launcher_and_preflight_require_external_manifest_pin():
    launcher = (HERE / "sync_launch_v023_100e_source_training_server.sh").read_text(
        encoding="utf-8"
    )
    preflight = (HERE / "preflight_v023_100e_source_training.py").read_text(
        encoding="utf-8"
    )
    assert "V023-100E-LAUNCH-MANIFEST-FROZEN.sha256" in launcher
    assert '[[ "$code_sha256" == "$pinned_code_sha256" ]]' in launcher
    assert "--manifest-sha256 '$code_sha256'" in launcher
    assert 'parser.add_argument("--manifest-sha256", required=True)' in preflight


def test_launch_manifest_is_current_and_complete():
    manifest = HERE / "V023-100E-LAUNCH-MANIFEST.sha256"
    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        digest, relative = line.split("  ", 1)
        assert relative not in listed
        listed[relative] = digest

    required = {
        ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-MODEL-CONFIG.sha256",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome/V023-100E-POST-R7-PROVIDER-CONFIG.sha256",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome/preflight_v023_100e_source_training.py",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome/verify_v023_100e_source_training.py",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome/sync_launch_v023_100e_source_training_server.sh",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome/test_v023_100e_source_training_server.py",
    }
    assert required <= set(listed)
    repo = HERE.parents[1]
    for relative, expected in listed.items():
        path = repo / relative
        assert path.is_file() and not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def test_launcher_dry_run_executes_the_current_frozen_closure():
    launcher = HERE / "sync_launch_v023_100e_source_training_server.sh"
    completed = subprocess.run(
        ["bash", str(launcher), "--dry-run"],
        cwd=HERE.parents[1],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "V023_100E_SOURCE_TRAINING_DRY_RUN_PASS" in completed.stdout


def test_final_verification_distinguishes_contract_and_preflight_claims():
    assert SEALER.CLAIM_CEILING != SEALER.PREFLIGHT_CLAIM_CEILING
    source = (HERE / "verify_v023_100e_source_training.py").read_text(encoding="utf-8")
    assert '"preflight_claim_ceiling": PREFLIGHT_CLAIM_CEILING' in source


def test_final_sealer_authenticates_exact_preflight_receipt(tmp_path: Path):
    receipt = tmp_path / "PREFLIGHT-RECEIPT.json"
    binding = {
        "schema": SEALER.PREFLIGHT_INPUT_SCHEMA,
        "provider_identity": "provider:test",
        "provider_identity_payload": {"schema": "provider-test-v1"},
        "provider_config_sha256": SEALER.EXPECTED_PROVIDER_CONFIG_SHA256,
        "model_config_sha256": SEALER.EXPECTED_MODEL_CONFIG_SHA256,
    }
    input_sha = hashlib.sha256(SEALER._canonical_bytes(binding)).hexdigest()
    payload = {
        "schema": SEALER.PREFLIGHT_SCHEMA,
        "status": SEALER.PREFLIGHT_STATUS,
        "claim_ceiling": SEALER.PREFLIGHT_CLAIM_CEILING,
        "epoch_budget": 100,
        "route_updates": 300,
        "checkpoint_epochs": [100],
        "train_seed": SEALER.EXPECTED_TRAIN_SEED,
        "schedule_seed": SEALER.EXPECTED_SCHEDULE_SEED,
        "source_split": SEALER.SOURCE_SPLIT,
        "test_split_opened": False,
        "simulator_episode_opened": False,
        "authority_sha256": SEALER.EXPECTED_CONTRACT_SHA256,
        "code_sha256": "a" * 64,
        "input_sha256": input_sha,
        "input_binding": binding,
        "output_root": str(SEALER.EXPECTED_OUTPUT_ROOT),
    }
    raw = SEALER._canonical_bytes(payload)
    receipt.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    receipt.with_suffix(".json.sha256").write_text(
        f"{digest}  {receipt.name}\n", encoding="ascii"
    )
    authenticated = SEALER._verify_preflight_receipt(
        receipt,
        expected_binding=binding,
        authority_sha256=SEALER.EXPECTED_CONTRACT_SHA256,
        code_sha256="a" * 64,
        input_sha256=input_sha,
    )
    assert authenticated["sha256"] == digest

    payload["input_sha256"] = "b" * 64
    receipt.write_bytes(SEALER._canonical_bytes(payload))
    with pytest.raises(SEALER.V023SourceTrainingSealError, match="preflight receipt"):
        SEALER._verify_preflight_receipt(
            receipt,
            expected_binding=binding,
            authority_sha256=SEALER.EXPECTED_CONTRACT_SHA256,
            code_sha256="a" * 64,
            input_sha256=input_sha,
        )


def test_sealer_has_no_simulator_or_test_runtime_imports():
    tree = ast.parse(
        (HERE / "verify_v023_100e_source_training.py").read_text(encoding="utf-8")
    )
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert all(not name.startswith("mcrl.env") for name in imported)
    assert all("evaluation" not in name and "simulator" not in name for name in imported)


def test_contract_and_preflight_keep_frozen_100e_boundary():
    contract = (HERE / "V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md").read_text(
        encoding="utf-8"
    )
    preflight = (HERE / "preflight_v023_100e_source_training.py").read_text(
        encoding="utf-8"
    )
    for text in (contract, preflight):
        assert "100" in text
        assert "300" in text
        assert "SOURCE_TRAIN" in text
        assert "TEST" in text
    assert "100-epoch" in contract
    assert '"simulator_episode_opened": False' in preflight
