"""Focused red-capable tests for the V0.23 100E server/seal boundary."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
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

PREFLIGHT_SPEC = importlib.util.spec_from_file_location(
    "v023_100e_source_training_preflight_under_test",
    HERE / "preflight_v023_100e_source_training.py",
)
assert PREFLIGHT_SPEC is not None and PREFLIGHT_SPEC.loader is not None
PREFLIGHT = importlib.util.module_from_spec(PREFLIGHT_SPEC)
sys.modules[PREFLIGHT_SPEC.name] = PREFLIGHT
PREFLIGHT_SPEC.loader.exec_module(PREFLIGHT)


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
        "R7_SEED_CLOSURE_PASS",
        "LEARNER_MANIFEST_PASS",
        "FACTORY_SPEC=v023_post_r7_provider_factory_v2:make_provider",
    ):
        assert token in launcher
    assert "/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2" in launcher
    assert "/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8" in launcher
    assert "100e-r1" not in launcher
    for token in ("remote_startup_marker", "CONTROLLER_STARTED", "STARTUP_ACKNOWLEDGED", "verify_sealed(target, \"C1C2\")", "preflight-v2-input-binding"):
        assert token in launcher
    assert "targets-20260906-d40-r4" not in launcher
    stale_target_suffix = "-ops3-" + "r5"
    assert stale_target_suffix not in launcher
    assert "preflight-v1" not in launcher
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


def test_launcher_uses_the_decision_a_seed_overlay_order():
    launcher = (HERE / "sync_launch_v023_100e_source_training_server.sh").read_text(
        encoding="utf-8"
    )
    ordered = (
        "V023_100E_LOCAL_MANIFEST_CONFIG_PASS",
        'verify_sealed(target, "C1C2")',
        "resolved_paths = {",
        "V023_100E_R7_SEED_CLOSURE_PASS",
        "cp -a --",
        "rsync -aR",
        "V023_100E_LEARNER_MANIFEST_PASS",
        "# Perform the exact factory preflight",
        "PASS_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC",
        "# Build a write-once server controller",
        "tmux new-session",
        "V023_100E_SOURCE_TRAINING_STARTUP_ACKNOWLEDGED",
    )
    positions = [launcher.index(token) for token in ordered]
    assert positions == sorted(positions)
    assert '"--repo", str(seed)' in launcher
    assert '"--prereg", str(prereg)' in launcher
    assert "$r7_result_root/authority/R7-PREFLIGHT-MANIFEST.json" in launcher
    assert "seed_manifest.read_bytes() != manifest.read_bytes()" in launcher
    assert "configured_r7_code_root=" in launcher
    assert "resolve(strict=True)" in launcher
    assert '[[ "$configured_r7_code_root" == "$r7_seed_root" ]]' not in launcher
    assert "learner launch-manifest entry drifted" in launcher


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)


def _launcher_shim_environment(tmp_path: Path, *, fail_stage: str = "") -> tuple[dict[str, str], Path]:
    shim_bin = tmp_path / "bin"
    shim_bin.mkdir()
    command_log = tmp_path / "remote-commands.jsonl"
    python = sys.executable
    _write_executable(
        shim_bin / "ssh",
        f"""#!{python}
import json
import os
from pathlib import Path
import shlex
import sys

remote = sys.argv[-1]
stdin = sys.stdin.read()
stage = None
if "V023_100E_PREREQUISITE_SEALS_PASS" in stdin:
    stage = "prerequisite_seals"
elif "V023_100E_R7_SEED_CLOSURE_PASS" in stdin:
    stage = "seed_r7_preflight"
elif remote.startswith("mkdir -- "):
    stage = "mkdir_seed"
elif remote.startswith("cp -a -- "):
    stage = "copy_seed"
elif "V023_100E_LEARNER_MANIFEST_PASS" in stdin:
    stage = "learner_manifest"
elif "preflight_v023_100e_source_training.py" in remote and "--receipt" in remote:
    stage = "factory_preflight"
elif "preflight-v2-input-binding" in stdin:
    stage = "receipt_validation"
elif "test -e" in remote and "v023-100e-one-epoch-diagnostic" in remote:
    stage = "diagnostic_absence"
elif "run_v023_one_epoch_provider_diagnostic.py" in remote:
    stage = "diagnostic"
elif "PASS_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC" in stdin:
    stage = "diagnostic_validation"
elif "v023-100e-source-training-controller.sh" in remote and "target_path" in stdin:
    stage = "controller_creation"
elif "tmux new-session" in remote:
    stage = "tmux"
elif "test -f" in remote and "tmux has-session" in remote:
    stage = "ack_probe"
elif remote.startswith("cat ") and "source-training-startup.json" in remote:
    stage = "ack_read"

with Path(os.environ["V023_SHIM_LOG"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({{"tool": "ssh", "stage": stage, "remote": remote, "stdin": stdin}}, sort_keys=True) + "\\n")

fail_stage = os.environ.get("V023_FAIL_STAGE", "")
if stage == "prerequisite_seals":
    fields = shlex.split(remote)
    dash = fields.index("-")
    seed = fields[dash + 1]
    configured = fields[-1]
    if os.path.normpath(seed) != os.path.normpath(configured):
        print("resolved R7 seed root disagrees with provider config r7_code_root", file=sys.stderr)
        raise SystemExit(41)
if stage == fail_stage:
    if stage == "receipt_validation":
        print("wrong-input-sha256")
        raise SystemExit(0)
    if stage == "diagnostic":
        print(json.dumps({{"status": "FAIL_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC", "failed_checks": ["injected_diagnostic_failure"]}}), file=sys.stderr)
    elif stage == "diagnostic_validation":
        print("diagnostic failed_checks=['injected_receipt_mismatch']", file=sys.stderr)
    raise SystemExit(42)

if stage == "receipt_validation":
    print("a" * 64)
elif stage == "diagnostic":
    print(json.dumps({{"status": "PASS_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC", "failed_checks": [], "provider_identity": "provider:test"}}, sort_keys=True))
elif stage == "diagnostic_validation":
    print("V023_100E_ONE_EPOCH_DIAGNOSTIC_PASS provider_identity=provider:test")
elif stage == "ack_read":
    print(json.dumps({{"status": "CONTROLLER_STARTED"}}, sort_keys=True))
elif "test -e" in remote or "test -L" in remote or ("tmux has-session" in remote and stage != "ack_probe"):
    raise SystemExit(1)
""",
    )
    _write_executable(
        shim_bin / "rsync",
        f"""#!{python}
import json
import os
from pathlib import Path
import sys

with Path(os.environ["V023_SHIM_LOG"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({{"tool": "rsync", "stage": "rsync", "argv": sys.argv[1:]}}, sort_keys=True) + "\\n")
raise SystemExit(42 if os.environ.get("V023_FAIL_STAGE") == "rsync" else 0)
""",
    )
    _write_executable(
        shim_bin / "scp",
        f"""#!{python}
import json
import os
from pathlib import Path
import sys

with Path(os.environ["V023_SHIM_LOG"]).open("a", encoding="utf-8") as stream:
    stream.write(json.dumps({{"tool": "scp", "stage": "scp", "argv": sys.argv[1:]}}, sort_keys=True) + "\\n")
raise SystemExit(42 if os.environ.get("V023_FAIL_STAGE") == "scp" else 0)
""",
    )
    _write_executable(shim_bin / "sleep", "#!/usr/bin/env bash\nexit 0\n")
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{shim_bin}:{environment['PATH']}",
            "V023_LOCAL_PYTHON": sys.executable,
            "V023_R7_SEED_ROOT": "/home/sat/mcrl-v023-r7-launch-ready-20260906-r4/",
            "V023_SERVER_HOST": "hermetic-v023-test",
            "V023_SHIM_LOG": str(command_log),
            "V023_FAIL_STAGE": fail_stage,
        }
    )
    return environment, command_log


def _run_real_launcher_with_shims(tmp_path: Path, *, fail_stage: str = "") -> tuple[subprocess.CompletedProcess[str], list[dict[str, object]]]:
    environment, command_log = _launcher_shim_environment(tmp_path, fail_stage=fail_stage)
    completed = subprocess.run(
        ["bash", str(HERE / "sync_launch_v023_100e_source_training_server.sh")],
        cwd=HERE.parents[1],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )
    entries = (
        [json.loads(line) for line in command_log.read_text(encoding="utf-8").splitlines()]
        if command_log.exists()
        else []
    )
    return completed, entries


def test_real_launcher_remote_stage_order_is_hermetic_and_diagnostic_gated(tmp_path: Path):
    completed, entries = _run_real_launcher_with_shims(tmp_path)
    assert completed.returncode == 0, completed.stderr
    stages = [entry["stage"] for entry in entries if entry.get("stage") is not None]
    assert stages == [
        "prerequisite_seals",
        "seed_r7_preflight",
        "mkdir_seed",
        "copy_seed",
        "rsync",
        "learner_manifest",
        "factory_preflight",
        "receipt_validation",
        "diagnostic_absence",
        "diagnostic",
        "diagnostic_validation",
        "controller_creation",
        "tmux",
        "ack_probe",
        "ack_read",
    ]
    seed_entry = next(entry for entry in entries if entry.get("stage") == "seed_r7_preflight")
    assert '"--repo", str(seed)' in str(seed_entry["stdin"])
    factory_entry = next(entry for entry in entries if entry.get("stage") == "factory_preflight")
    diagnostic_entry = next(entry for entry in entries if entry.get("stage") == "diagnostic")
    for token in (
        "PYTHONUNBUFFERED=1",
        "PYTHONDONTWRITEBYTECODE=1",
        "OMP_NUM_THREADS=1",
        "OPENBLAS_NUM_THREADS=1",
        "MKL_NUM_THREADS=1",
        "NUMEXPR_NUM_THREADS=1",
        "PYTHONPATH='/home/sat/mcrl-v023-five-arm-source-training-20260907-100e-r2-checkout/src:",
    ):
        assert token in str(factory_entry["remote"])
        assert token in str(diagnostic_entry["remote"])
    diagnostic_validation = next(
        entry for entry in entries if entry.get("stage") == "diagnostic_validation"
    )
    validation_source = str(diagnostic_validation["stdin"])
    assert 'receipt.get("status") != "PASS_ONE_EPOCH_PROVIDER_PLUMBING_DIAGNOSTIC"' in validation_source
    assert "failed_checks != []" in validation_source
    assert 'receipt.get("provider_identity") != expected_identity' in validation_source
    assert "diagnostic_digest_path.read_text" in validation_source
    assert all(entry["tool"] in {"ssh", "rsync", "scp"} for entry in entries)


@pytest.mark.parametrize(
    "fail_stage",
    [
        "prerequisite_seals",
        "seed_r7_preflight",
        "mkdir_seed",
        "copy_seed",
        "rsync",
        "learner_manifest",
        "factory_preflight",
        "receipt_validation",
        "diagnostic_absence",
        "diagnostic",
        "diagnostic_validation",
    ],
)
def test_real_launcher_precontroller_failures_never_issue_controller_or_tmux(tmp_path: Path, fail_stage: str):
    completed, entries = _run_real_launcher_with_shims(tmp_path, fail_stage=fail_stage)
    assert completed.returncode != 0
    assert not any(entry.get("stage") in {"controller_creation", "tmux"} for entry in entries)
    if fail_stage.startswith("diagnostic"):
        assert "diagnostic" in completed.stderr.lower()


def test_real_launcher_rejects_a_resolved_seed_directory_mismatch(tmp_path: Path):
    environment, command_log = _launcher_shim_environment(tmp_path)
    environment["V023_R7_SEED_ROOT"] = "/home/sat/a-different-r7-seed"
    completed = subprocess.run(
        ["bash", str(HERE / "sync_launch_v023_100e_source_training_server.sh")],
        cwd=HERE.parents[1],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )
    entries = [json.loads(line) for line in command_log.read_text(encoding="utf-8").splitlines()]
    assert completed.returncode != 0
    assert "resolved R7 seed root disagrees" in completed.stderr
    assert not any(entry.get("stage") in {"controller_creation", "tmux"} for entry in entries)


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
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.sha256",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-MODEL-CONFIG.sha256",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/V023-100E-POST-R7-PROVIDER-CONFIG.sha256",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/preflight_v023_100e_source_training.py",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/verify_v023_100e_source_training.py",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/sync_launch_v023_100e_source_training_server.sh",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/test_v023_100e_source_training_server.py",
        ".scratch/multi-catfish-v023-100e-screen-preoutcome-v2/run_v023_one_epoch_provider_diagnostic.py",
        ".scratch/multi-catfish-v023-five-arm-training-runner/v023_five_arm_source_training_runner.py",
        ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory.py",
        ".scratch/multi-catfish-v023-post-r7-provider-factory/v023_post_r7_provider_factory_v2.py",
        ".scratch/multi-catfish-v023-post-r7-provider-factory/test_v023_post_r7_provider_factory_v2.py",
        "src/mcrl/algorithms/ee_axis_lcsrs_three_route.py",
        "src/mcrl/algorithms/ee_axis_v014_head.py",
        "src/mcrl/runtime/ee_axis_opening_dataset.py",
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


def test_provider_config_and_all_bundle_factory_loads_use_decision_a_v2():
    provider_config = HERE / "V023-100E-POST-R7-PROVIDER-CONFIG.json"
    payload = json.loads(provider_config.read_text(encoding="ascii"))
    assert payload == {
        "epoch_budget": 100,
        "r7_code_root": "/home/sat/mcrl-v023-r7-launch-ready-20260906-r4",
        "r7_root": "/home/sat/mcrl-v023-lcsrs-gate-20260906-r7-i1",
        "schedule_seed": 1113171504590631764,
        "schema": "multi-catfish-mcrl-v023-post-r7-provider-factory-config-v2",
        "target_root": "/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8",
    }
    canonical = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    assert provider_config.read_bytes() == canonical
    assert SEALER.EXPECTED_PROVIDER_CONFIG == payload
    preflight = (HERE / "preflight_v023_100e_source_training.py").read_text(
        encoding="utf-8"
    )
    verifier = (HERE / "verify_v023_100e_source_training.py").read_text(
        encoding="utf-8"
    )
    diagnostic = (HERE / "run_v023_one_epoch_provider_diagnostic.py").read_text(
        encoding="utf-8"
    )
    assert '"v023_post_r7_provider_factory_v2.py"' in preflight
    assert 'PROVIDER_FACTORY_MODULE = "v023_post_r7_provider_factory_v2"' in verifier
    assert '"v023_post_r7_provider_factory_v2.py"' in verifier
    assert '"v023_post_r7_provider_factory_v2.py"' in diagnostic
    for path in (
        provider_config,
        HERE / "V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md",
        HERE / "README.md",
        HERE / "preflight_v023_100e_source_training.py",
        HERE / "verify_v023_100e_source_training.py",
        HERE / "sync_launch_v023_100e_source_training_server.sh",
    ):
        stale_target_suffix = "-ops3-" + "r5"
        assert stale_target_suffix not in path.read_text(encoding="utf-8")


def _launch_bindings() -> dict[str, str]:
    return {
        relative: digest
        for digest, relative in (
            line.split("  ", 1)
            for line in (
                HERE / "V023-100E-LAUNCH-MANIFEST.sha256"
            ).read_text(encoding="ascii").splitlines()
        )
    }


def _identity_fixture(consumer, tmp_path: Path):
    repo = HERE.parents[1].resolve()
    code_root = tmp_path / "immutable-r7-code"
    code_root.mkdir()
    runtime = []
    for path, module in consumer.EXPECTED_R7_AUTHENTICATION_RUNTIME_MODULES.items():
        source = repo / path
        runtime.append(
            {
                "path": path,
                "module": module,
                "loaded_from": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    learner_runtime = []
    for path, module in sorted(
        consumer.EXPECTED_R7_BOUND_LEARNER_RUNTIME_MODULES.items(),
        key=lambda item: (item[0], item[1]),
    ):
        source = repo / path
        learner_runtime.append(
            {
                "path": path,
                "module": module,
                "loaded_from": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        )
    payload = {
        "schema": consumer.EXPECTED_PROVIDER_IDENTITY_SCHEMA,
        "target_manifest_sha256": "b" * 64,
        "c3_schedule_receipt_sha256": "c" * 64,
        "epoch_budget": 100,
        "c3_source_ids": {"neutral": "neutral-id", "informed": "informed-id"},
        "r7_code_root": str(code_root.resolve()),
        "r7_preflight_manifest_sha256": "d" * 64,
        "r7_code_manifest_sha256": "e" * 64,
        "r7_result_manifest_sha256": "f" * 64,
        "r7_gate_result_sha256": "0" * 64,
        "r7_authentication_runtime": runtime,
        "r7_authentication_runtime_sha256": consumer._canonical_compact_sha256(runtime),
        "r7_bound_learner_runtime": learner_runtime,
        "r7_bound_learner_runtime_sha256": consumer._canonical_compact_sha256(
            learner_runtime
        ),
    }
    identity = (
        f"{consumer.EXPECTED_PROVIDER_FACTORY_SCHEMA}:"
        f"{consumer._canonical_compact_sha256(payload)}"
    )
    return repo, code_root, payload, identity


@pytest.mark.parametrize(
    ("consumer", "error_type"),
    (
        (SEALER, SEALER.V023SourceTrainingSealError),
        (PREFLIGHT, PREFLIGHT.V023PreflightError),
    ),
)
def test_consumers_recompute_complete_decision_a_identity_and_runtime_digests(
    tmp_path: Path, consumer, error_type
):
    repo, code_root, payload, identity = _identity_fixture(consumer, tmp_path)
    assert consumer._validated_provider_identity(
        identity,
        payload,
        provider_config={"r7_code_root": str(code_root)},
        learner_repo=repo,
        launch_bindings=_launch_bindings(),
    ) == payload

    compact = json.dumps(
        payload["r7_bound_learner_runtime"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    assert payload["r7_bound_learner_runtime_sha256"] == hashlib.sha256(
        compact
    ).hexdigest()
    assert payload["r7_bound_learner_runtime_sha256"] != hashlib.sha256(
        compact + b"\n"
    ).hexdigest()

    tampered = dict(payload)
    tampered["r7_authentication_runtime_sha256"] = "1" * 64
    with pytest.raises(
        error_type,
    ):
        altered_identity = (
            f"{consumer.EXPECTED_PROVIDER_FACTORY_SCHEMA}:"
            f"{consumer._canonical_compact_sha256(tampered)}"
        )
        consumer._validated_provider_identity(
            altered_identity,
            tampered,
            provider_config={"r7_code_root": str(code_root)},
            learner_repo=repo,
            launch_bindings=_launch_bindings(),
        )


@pytest.mark.parametrize(
    ("consumer", "error_type"),
    (
        (SEALER, SEALER.V023SourceTrainingSealError),
        (PREFLIGHT, PREFLIGHT.V023PreflightError),
    ),
)
@pytest.mark.parametrize(
    "mutation",
    (
        "malformed_record",
        "omitted_record",
        "reclassified_record",
        "changed_origin",
        "changed_hash",
        "omitted_identity_key",
    ),
)
def test_consumers_reject_runtime_tampering_even_with_recomputed_digests(
    tmp_path: Path, consumer, error_type, mutation: str
):
    repo, code_root, original, _ = _identity_fixture(consumer, tmp_path)
    payload = copy.deepcopy(original)
    if mutation == "malformed_record":
        payload["r7_bound_learner_runtime"][0].pop("module")
    elif mutation == "omitted_record":
        payload["r7_bound_learner_runtime"].pop()
    elif mutation == "reclassified_record":
        payload["r7_authentication_runtime"].append(
            payload["r7_bound_learner_runtime"].pop(0)
        )
    elif mutation == "changed_origin":
        payload["r7_bound_learner_runtime"][0]["loaded_from"] = str(
            tmp_path / "foreign" / "module.py"
        )
    elif mutation == "changed_hash":
        payload["r7_bound_learner_runtime"][0]["sha256"] = "0" * 64
    elif mutation == "omitted_identity_key":
        payload.pop("r7_bound_learner_runtime_sha256")
    else:  # pragma: no cover - the parametrization is exhaustive
        raise AssertionError(mutation)

    for list_field, digest_field in (
        ("r7_authentication_runtime", "r7_authentication_runtime_sha256"),
        ("r7_bound_learner_runtime", "r7_bound_learner_runtime_sha256"),
    ):
        if digest_field in payload:
            payload[digest_field] = consumer._canonical_compact_sha256(
                payload[list_field]
            )
    altered_identity = (
        f"{consumer.EXPECTED_PROVIDER_FACTORY_SCHEMA}:"
        f"{consumer._canonical_compact_sha256(payload)}"
    )
    with pytest.raises(error_type):
        consumer._validated_provider_identity(
            altered_identity,
            payload,
            provider_config={"r7_code_root": str(code_root)},
            learner_repo=repo,
            launch_bindings=_launch_bindings(),
        )


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
        "code_sha256": "a" * 64,
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
        "c3_source_disclosure": SEALER.EXPECTED_C3_SOURCE_DISCLOSURE,
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


def test_launcher_top_level_hashes_match_the_real_frozen_files():
    launcher = (HERE / "sync_launch_v023_100e_source_training_server.sh").read_text(
        encoding="utf-8"
    )
    expected = {
        "expected_contract_sha256": HERE / "V023-100E-FIVE-ARM-SCREEN-CONTRACT-2026-09-07.md",
        "expected_model_config_sha256": HERE / "V023-100E-MODEL-CONFIG.json",
        "expected_provider_config_sha256": HERE / "V023-100E-POST-R7-PROVIDER-CONFIG.json",
    }
    for variable, path in expected.items():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert f"{variable}={digest}\n" in launcher, variable
        # the embedded local check must carry the same digest
        assert launcher.count(digest) >= 2, variable


def test_generated_controller_python_newlines_are_escaped_in_the_fstring_body():
    launcher = (HERE / "sync_launch_v023_100e_source_training_server.sh").read_text(
        encoding="utf-8"
    )
    body_start = launcher.index("body = f\'\'\'")
    body_end = launcher.index("\'\'\'", body_start + 12)
    body = launcher[body_start:body_end]
    # Every JSON newline terminator inside the generated controller must be
    # written as a doubled backslash so the f-string emits a literal \n.
    assert body.count('+ "\\\\n").encode("ascii")') == 2
    assert '+ "\\n").encode("ascii")' not in body.replace('"\\\\n"', "")
