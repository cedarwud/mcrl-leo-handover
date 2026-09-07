"""Focused positive and mutation-negative tests for the formal launch bundle."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNNER_DIR = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
for path in (HERE, REPO / "src", RUNNER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import run_v023_c1c2_successor_one_epoch_diagnostic as DIAGNOSTIC
import successor_launch_common as COMMON
import verify_v023_c1c2_successor as VERIFY


def test_stage_a_placeholder_left_unresolved_makes_binding_fail():
    declarations = "\n".join(
        f"<<BIND_AT_FREEZE:{key}>>" for key in sorted(COMMON.STAGE_A_PLACEHOLDERS)
    ) + "\n## 2. next\n"
    resolved = {key: "bound" for key in COMMON.STAGE_A_PLACEHOLDERS}
    resolved.pop("runner_manifest_sha256")
    with pytest.raises(COMMON.SuccessorLaunchError, match="unresolved"):
        COMMON.assert_stage_a_placeholders(declarations, resolved)


def test_forbidden_predecessor_token_in_provider_config_is_rejected():
    payload = {
        "schema": COMMON.PROVIDER_CONFIG_SCHEMA,
        "target_root": "/home/sat/clean-" + "r" + "7",
    }
    with pytest.raises(COMMON.SuccessorLaunchError, match="forbidden"):
        COMMON.reject_forbidden_config(payload)


def test_circular_digest_attempt_is_rejected():
    mutation = {"authority": {"launch_manifest_sha256": "a" * 64}}
    with pytest.raises(COMMON.SuccessorLaunchError, match="circular"):
        COMMON.validate_no_circular_digest(mutation)


def test_diagnostic_failure_receipt_makes_launcher_refuse(tmp_path: Path):
    root = tmp_path / "diagnostic"
    root.mkdir()
    DIAGNOSTIC._write_receipt(
        root,
        {
            "schema": DIAGNOSTIC.SCHEMA,
            "status": DIAGNOSTIC.STATUS_FAIL,
            "formal": False,
            "failed_checks": ["mutation-negative"],
        },
    )
    result = subprocess.run(
        [
            "bash", str(HERE / "sync_launch_v023_c1c2_successor_server.sh"),
            "--check-diagnostic-receipt", str(root / DIAGNOSTIC.RECEIPT_NAME),
        ],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 2
    assert "LAUNCH_REFUSED" in result.stderr


@pytest.fixture(scope="module")
def producer_output(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, Path]:
    """Create the fixture through the real two-route runner/writer."""

    root = tmp_path_factory.mktemp("producer-output")
    provider_module = root / "successor_fixture_provider.py"
    provider_module.write_text(
        "from v023_two_route_test_helpers import stub_provider\n"
        "def make_provider():\n"
        "    return stub_provider()\n",
        encoding="ascii",
    )
    preflight = root / "preflight.json"
    identity = "c1c2-stub-provider-v1"
    preflight.write_bytes(
        COMMON.canonical_bytes(
            {
                "schema": "multi-catfish-mcrl-v023-c1c2-successor-preflight-v1",
                "status": "PASS_FROZEN_C1C2_SUCCESSOR_PREFLIGHT",
                "formal": True,
                "authority_sha256": "a" * 64,
                "code_sha256": "b" * 64,
                "input_sha256": "c" * 64,
                "input_binding": {
                    "provider_identity": identity,
                    "provider_identity_payload": {"routes": ["C1", "C2"]},
                },
            }
        )
    )
    preflight_sha = COMMON.file_sha256(preflight)
    COMMON.sidecar_path(preflight).write_text(
        f"{preflight_sha}  {preflight.name}\n", encoding="ascii"
    )
    output = root / "formal-output"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root), str(REPO / "src"), str(RUNNER_DIR), str(HERE)]
    )
    env.update(
        {
            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        }
    )
    result = subprocess.run(
        [
            str(REPO / ".venv/bin/python"),
            str(HERE / "run_v023_c1c2_successor_formal.py"),
            "--output-root", str(output), "--epochs", "100",
            "--provider-factory", "successor_fixture_provider:make_provider",
            "--model-config-json", str(REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME),
            "--train-seed", str(COMMON.TRAIN_SEED),
            "--authority-sha256", "a" * 64, "--code-sha256", "b" * 64,
            "--input-sha256", "c" * 64, "--preflight-receipt", str(preflight),
            "--execute",
        ],
        cwd=REPO, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=180,
    )
    assert result.returncode == 0, result.stderr
    provider_config = root / "provider-config.json"
    provider_config.write_text("{}\n", encoding="ascii")
    return output, preflight, provider_config


def test_fourth_arm_mutation_produces_integrity_stop(
    producer_output: tuple[Path, Path, Path],
):
    output, preflight, provider_config = producer_output
    path = output / "exports/epoch-0100.json"
    manifest = json.loads(path.read_text(encoding="ascii"))
    manifest["arm_order"].append("FOURTH_ARM")
    extra = dict(manifest["exports"][-1])
    extra["arm"] = "FOURTH_ARM"
    manifest["exports"].append(extra)
    path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        encoding="ascii",
    )
    result = VERIFY.decision_for_output(
        repo=REPO,
        output_root=output,
        provider_config_path=provider_config,
        model_config_path=REPO / COMMON.SUCCESSOR_REL / COMMON.MODEL_CONFIG_NAME,
        preflight_receipt_path=preflight,
        reconstruct=False,
    )
    assert result["status"] == VERIFY.STOP
    assert "fourth arm" in result["error"]


def test_launcher_orders_freeze_manifest_sync_diagnostic_and_tmux():
    text = (HERE / "sync_launch_v023_c1c2_successor_server.sh").read_text(encoding="utf-8")
    assert text.index('"${local_bind_cmd[@]}"') < text.index('"${local_manifest_cmd[@]}"')
    assert text.index("rsync_args=(rsync") < text.rindex("--verify-learner-manifest-only")
    assert text.index("preflight_command=") < text.index("diagnostic_command=")
    assert text.index("diagnostic_command=") < text.rindex("tmux new-session")
    assert "OMP_NUM_THREADS=1" in text
    assert "120 s" in text
