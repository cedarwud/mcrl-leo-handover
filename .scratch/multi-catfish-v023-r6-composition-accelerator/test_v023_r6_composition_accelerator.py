"""Focused, non-heavy tests for the R6 composition accelerator guardrails.

These tests use synthetic JSON/NPZ/proc fixtures only.  They never connect to
the Ubuntu server, import production composition code, construct a simulator,
fit a model, or launch a worker.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType
import zipfile

import pytest


REPO = Path(__file__).resolve().parents[2]
HERE = REPO / ".scratch" / "multi-catfish-v023-r6-composition-accelerator"
PREFLIGHT_PATH = HERE / "preflight_v023_r6_composition_accelerator.py"
LAUNCH_PATH = HERE / "launch_v023_r6_composition_accelerator.sh"
FULL_RUNNER_PATH = REPO / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "run_v023_lcsrs_full_gate_server.sh"


def _load_preflight() -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_v023_r6_accelerator_preflight", PREFLIGHT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves postponed annotations through sys.modules while
    # executing the module; register the fixture module before exec_module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def preflight() -> ModuleType:
    return _load_preflight()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(value) + b"\n")


def _write_proc(proc_root: Path, pid: int, argv: list[str]) -> None:
    directory = proc_root / str(pid)
    directory.mkdir(parents=True)
    (directory / "cmdline").write_bytes(b"\0".join(item.encode() for item in argv) + b"\0")


def test_tail_panel_is_exact_and_disjoint_from_the_full_runner_schedule(preflight: ModuleType) -> None:
    assert preflight.TARGETS == (
        (2026121712, 2026135102, "INFORMED"),
        (2026121712, 2026135102, "MATCHED_PLACEBO"),
        (2026121712, 2026135103, "INFORMED"),
        (2026121712, 2026135103, "MATCHED_PLACEBO"),
    )
    assert len(set(preflight.TARGETS)) == 4
    full_text = FULL_RUNNER_PATH.read_text(encoding="utf-8")
    assert "for world in \"${WORLDS[@]}\"" in full_text
    assert "for seed in \"${STUDENT_SEEDS[@]}\"" in full_text
    assert "for arm in \"${ARMS[@]}\"" in full_text
    assert "--composition-jobs 2" not in full_text
    assert "COMPOSITION_JOBS=2" in full_text


def test_wrapper_reuses_the_full_runner_composition_command_and_closed_boundaries() -> None:
    text = LAUNCH_PATH.read_text(encoding="utf-8")
    for token in (
        "run_v023_lcsrs_composition_server.py",
        "--fit-receipt-sha256",
        "--model-bytes-sha256",
        "--model-sha256",
        "--contract-sha256",
        "--preflight-sha256",
        "--source-manifest-sha256",
        "--runtime-module",
        "--runtime-factory",
        "ACCELERATOR_JOBS=4",
        "Main jobs=2 + accelerator jobs=4 = 6",
    ):
        assert token in text
    assert "ssh " not in text
    assert "run_v023_lcsrs_full_gate_server.sh" not in text.split("start_job", 1)[1]
    full_text = FULL_RUNNER_PATH.read_text(encoding="utf-8")
    command_slice = full_text[full_text.index('start_job "$PYTHON" "$COMPOSITION_SERVER"'):]
    wrapper_slice = text[text.index('start_job "$PYTHON" "$COMPOSITION_SERVER"'):]
    for token in (
        "--held-out-world",
        "--student-seed",
        "--arm",
        "--source-directory",
        "--source-manifest",
        "--preflight-sha256",
        "--source-manifest-sha256",
        "--fit-receipt",
        "--fit-receipt-sha256",
        "--model-bytes-sha256",
        "--model-sha256",
        "--contract-sha256",
        "--output",
        "--device",
        "--runtime-module",
        "--runtime-factory",
    ):
        assert token in command_slice
        assert token in wrapper_slice


def test_wrapper_and_preflight_help_are_non_destructive() -> None:
    shell = subprocess.run(
        ["bash", "-n", str(LAUNCH_PATH)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert shell.returncode == 0, shell.stderr
    result = subprocess.run(
        ["bash", str(LAUNCH_PATH), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "world 2026121712" in result.stdout
    assert "total_max=6" in result.stdout or "Main jobs=2 + accelerator jobs=4 = 6" in result.stdout


def test_live_process_guard_requires_the_exact_controller_and_main_job_cap(
    preflight: ModuleType, tmp_path: Path
) -> None:
    server_root = tmp_path / "server"
    run_root = server_root / "artifacts" / "multi-catfish-v023-lcsrs-gate-20260906-r6" / "server-run"
    run_root.mkdir(parents=True)
    proc_root = tmp_path / "proc"
    controller = server_root / "v023_lcsrs_gate_controller.sh"
    runner = server_root / ".scratch" / "multi-catfish-v023-r6-fit-binding-fix" / "run_v023_lcsrs_full_gate_server.sh"
    _write_proc(proc_root, 100, ["/bin/bash", str(controller)])
    _write_proc(
        proc_root,
        101,
        [
            "/bin/bash",
            str(runner),
            "--run-root",
            str(run_root),
            "--tle-root",
            "/home/sat/mcrl-runtime/tle-frozen-20260820",
            "--source-jobs",
            "4",
            "--fit-jobs",
            "4",
            "--composition-jobs",
            "2",
        ],
    )
    _write_proc(
        proc_root,
        102,
        [
            "/home/sat/.venv/bin/python",
            str(server_root / ".scratch/multi-catfish-v023-r6-fit-binding-fix/run_v023_lcsrs_composition_server.py"),
            "--output",
            str(run_root / "composition/world-2026121705/seed-2026135101/informed.json"),
        ],
    )
    live = preflight.validate_live_controller(
        server_root=server_root,
        run_root=run_root,
        controller_pid=100,
        proc_root=proc_root,
    )
    assert live["main_active_composition_workers"] == 1
    assert live["max_total_composition_workers"] == 6
    target = preflight.Target(2026121712, 2026135102, "INFORMED")
    preflight.validate_no_target_worker(
        run_root=run_root,
        target=target,
        proc_root=proc_root,
    )
    _write_proc(
        proc_root,
        103,
        [
            "/home/sat/.venv/bin/python",
            str(server_root / ".scratch/multi-catfish-v023-r6-fit-binding-fix/run_v023_lcsrs_composition_server.py"),
            "--output",
            str(run_root / target.output_relative()),
        ],
    )
    with pytest.raises(preflight.AcceleratorPreflightError, match="already active"):
        preflight.validate_no_target_worker(
            run_root=run_root,
            target=target,
            proc_root=proc_root,
        )


def test_memory_proof_is_explicit_and_conservative(preflight: ModuleType, tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    proof = tmp_path / "memory-proof.json"
    _write_json(
        proof,
        {
            "schema": preflight.MEMORY_PROOF_SCHEMA,
            "contract_sha256": preflight.CONTRACT_SHA256,
            "preflight_manifest_sha256": preflight.PREFLIGHT_MANIFEST_SHA256,
            "run_root": str(run_root.resolve()),
            "main_composition_jobs": 2,
            "accelerator_composition_jobs": 4,
            "max_total_composition_workers": 6,
            "worker_count": 6,
            "device": "cpu",
            "bound_kind": "upper_bound",
            "per_worker_peak_rss_bytes": 100 * 1024 * 1024,
            "reserve_bytes": 100 * 1024 * 1024,
        },
    )
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable: 1000000 kB\n", encoding="ascii")
    receipt = preflight.validate_memory_proof(
        proof,
        meminfo=meminfo,
        run_root=run_root,
        preflight_sha256=preflight.PREFLIGHT_MANIFEST_SHA256,
    )
    assert receipt["status"] == "MEMORY_PROOF_PASS"
    assert receipt["required_bytes"] == 700 * 1024 * 1024
    meminfo.write_text("MemAvailable: 1000 kB\n", encoding="ascii")
    with pytest.raises(preflight.AcceleratorPreflightError, match="headroom"):
        preflight.validate_memory_proof(
            proof,
            meminfo=meminfo,
            run_root=run_root,
            preflight_sha256=preflight.PREFLIGHT_MANIFEST_SHA256,
        )


def _write_existing_composition(
    preflight: ModuleType,
    run_root: Path,
    target: ModuleType,
    *,
    fit_hashes: dict[str, str],
) -> tuple[Path, Path, Path]:
    target_paths = preflight.target_paths(run_root, target)
    index, arrays, sidecar = target_paths
    arrays.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(arrays, mode="w") as archive:
        archive.writestr("array.npy", b"synthetic-npy-payload")
    arrays_sha = preflight.file_sha256(arrays)
    sidecar.write_bytes(f"{arrays_sha}  {arrays.name}\n".encode("ascii"))
    body: dict[str, object] = {
        "schema": preflight.COMPOSITION_SCHEMA,
        "status": "PASS_COMPOSITION_EVIDENCE",
        "claim_ceiling": preflight.CLAIM_CEILING,
        "contract_sha256": preflight.CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight.PREFLIGHT_MANIFEST_SHA256,
        "source_manifest_sha256": "b" * 64,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": target.world,
        "student_seed": target.seed,
        "arm": target.arm,
        "fit_receipt_sha256": fit_hashes["fit_receipt_sha256"],
        "fit_model_bytes_sha256": fit_hashes["model_bytes_sha256"],
        "fit_model_sha256": fit_hashes["model_sha256"],
        "fit_update_count": preflight.FIT_UPDATES,
        "fit_already_completed": True,
        "test_split_opened": False,
        "test_worlds": [],
        "episode_training": False,
        "learner_update": False,
        "scientific_decision_opened": False,
        "c3_decision": None,
        "arrays": {
            "npz_relative_path": arrays.name,
            "npz_sha256": arrays_sha,
            "npz_sha256_file": sidecar.name,
            "allow_pickle": False,
        },
    }
    body["receipt_sha256"] = preflight.hashlib.sha256(preflight.canonical_bytes(body)).hexdigest()
    _write_json(index, body)
    return index, arrays, sidecar


def test_existing_output_is_safe_to_skip_only_when_all_sidecars_are_valid(
    preflight: ModuleType, tmp_path: Path
) -> None:
    run_root = tmp_path / "run"
    target = preflight.Target(2026121712, 2026135102, "INFORMED")
    fit_hashes = {
        "fit_receipt_sha256": "a" * 64,
        "model_bytes_sha256": "b" * 64,
        "model_sha256": "c" * 64,
    }
    index, arrays, sidecar = _write_existing_composition(
        preflight, run_root, target, fit_hashes=fit_hashes
    )
    result = preflight.validate_existing_composition(
        run_root,
        target,
        preflight_sha256=preflight.PREFLIGHT_MANIFEST_SHA256,
        source_manifest_sha256="b" * 64,
        fit_hashes=fit_hashes,
    )
    assert result["status"] == "SKIP_EXISTING"
    arrays.write_bytes(arrays.read_bytes() + b"tamper")
    with pytest.raises(preflight.AcceleratorPreflightError, match="NPZ hash"):
        preflight.validate_existing_composition(
            run_root,
            target,
            preflight_sha256=preflight.PREFLIGHT_MANIFEST_SHA256,
            source_manifest_sha256="b" * 64,
            fit_hashes=fit_hashes,
        )
    arrays.unlink()
    with pytest.raises(preflight.AcceleratorPreflightError, match="partial"):
        preflight.validate_existing_composition(
            run_root,
            target,
            preflight_sha256=preflight.PREFLIGHT_MANIFEST_SHA256,
            source_manifest_sha256="b" * 64,
            fit_hashes=fit_hashes,
        )
    assert index.is_file()
    assert sidecar.is_file()


def test_receipts_are_write_once(preflight: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    payload = {"status": "NO-GO", "scientific_claim": False}
    preflight._write_once(path, payload)
    assert path.read_bytes() == _canonical(payload) + b"\n"
    with pytest.raises(preflight.AcceleratorPreflightError, match="overwrite"):
        preflight._write_once(path, payload)
