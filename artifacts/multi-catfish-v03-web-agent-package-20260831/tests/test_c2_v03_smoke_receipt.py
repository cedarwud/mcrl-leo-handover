from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SMC_DIR = HERE.parent / "smc-er-short-ep"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SMC_DIR))

import c2_v03_smoke_receipt as receipt  # noqa: E402
import smc_er_core  # noqa: E402
import test_c2_temporal_fork_segment_merge as segment_test  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_complete_run(root: Path) -> Path:
    run = segment_test._make_segment(root, episode=0, total_episodes=1)
    status_path = run / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["config"]["max_c2_candidates"] = 2
    status["config"]["acrm_eta"] = 1.0
    result = status["result"]
    trainer_config = {
        "activation": "tanh",
        "hidden_layers": [100, 50, 50],
        "learning_rate": 0.001,
    }
    status["trainer_config"] = trainer_config
    result["trainer_config"] = trainer_config
    result.update(
        {
            "artifact_scope": "complete_run",
            "start_episode": 0,
            "episodes_completed": 1,
            "episodes_executed": 1,
            "checkpoint_every_episodes": 1,
            "telemetry_path": str(run / "run-telemetry.json"),
            "telemetry_sha256": _sha(run / "run-telemetry.json"),
            "c2_option_chronology_audit_path": str(run / "c2-option-chronology-audits.json"),
            "c2_option_chronology_audit_sha256": _sha(run / "c2-option-chronology-audits.json"),
        }
    )
    code_paths = receipt.episode_runner._c2_code_authority_paths()
    environment_source_sha256 = receipt.episode_runner._code_sha256(code_paths)
    reward_source_sha256 = "d" * 64
    result["mechanism_authority"] = {
        "candidate_version": receipt.c2_core.CANDIDATE_VERSION,
        "forecast_authority_schema": receipt.c2_core.FORECAST_AUTHORITY_SCHEMA,
        "main_policy_version": receipt.c2_backend.MAIN_POLICY_VERSION,
        "policy_compositor_version": receipt.c2_backend.POLICY_COMPOSITOR_VERSION,
        "environment_source_sha256": environment_source_sha256,
        "reward_source_sha256": reward_source_sha256,
        "code_authority_paths": [
            path.relative_to(REPO).as_posix() for path in code_paths
        ],
    }
    (run / "initial-main-checkpoint.pt").write_bytes(b"initial checkpoint")
    (run / "final-checkpoint.pt").write_bytes(b"final checkpoint")
    torch.save(
        {
            "authority": {
                "checkpoint_sha256": "a" * 64,
                "environment_source_sha256": environment_source_sha256,
                "reward_source_sha256": reward_source_sha256,
            },
            "trainer_config": trainer_config,
            "main_training_state": {"trainer_config": trainer_config},
        },
        run / "carrier-state.pt",
    )
    periodic = run / "checkpoints" / "ep-000001-main.pt"
    periodic.parent.mkdir()
    periodic.write_bytes(b"periodic checkpoint")
    result["checkpoint"] = str(run / "final-checkpoint.pt")
    result["checkpoint_sha256"] = _sha(run / "final-checkpoint.pt")
    result["carrier_state"] = str(run / "carrier-state.pt")
    result["carrier_state_sha256"] = _sha(run / "carrier-state.pt")
    result["periodic_checkpoints"] = [
        {
            "checkpoint_kind": "periodic-main-policy-trend",
            "episode_index": 0,
            "episodes_completed": 1,
            "load_round_trip": "PASS",
            "path": str(periodic),
            "sha256": _sha(periodic),
        }
    ]
    result["periodic_checkpoint_count"] = 1
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    journal = {
        "schema": receipt.JOURNAL_SCHEMA,
        "status": "complete",
        "claim_ceiling": status["claim_ceiling"],
        "config": status["config"],
        "trainer_config": trainer_config,
        "result_summary": {
            "checkpoint_sha256": result["checkpoint_sha256"],
            "dispatch": result["dispatch"],
            "episodes": 1,
            "joint_transaction_count": 0,
        },
    }
    (run / "run-journal.json").write_text(
        json.dumps(journal, indent=2) + "\n", encoding="utf-8"
    )
    return run


def test_validates_complete_run_and_emits_descriptive_dose_receipt(tmp_path: Path):
    run = _make_complete_run(tmp_path / "run")
    output = tmp_path / "receipt.json"

    result = receipt.write_smoke_receipt(run, output)

    assert result["status"] == "PASS"
    assert result["claim_ceiling"] == receipt.CLAIM_CEILING
    assert result["provenance"]["acrm_eta"] == 1.0
    assert result["provenance"]["trainer_config"]["learning_rate"] == 0.001
    assert result["provenance"]["carrier_trainer_config"] == result["provenance"]["trainer_config"]
    assert result["verification"]["checkpoint_existence_and_hashes"] == "PASS"
    assert result["verification"]["policy_code_authority"] == "PASS"
    assert result["c2"]["choice_counts"] == {"K0": 0, "K1": 0, "K>=2": 0}
    assert result["main_descriptive"]["ratio_of_sums_ee_bits_per_j"] == pytest.approx(10.0)
    assert result["checkpoint_inventory"]["periodic"][0]["sha256"] == _sha(
        run / "checkpoints" / "ep-000001-main.pt"
    )
    assert output.is_file()
    assert result["receipt_sha256"] == _sha(output)


def test_rejects_checkpoint_tamper_and_missing_periodic_checkpoint(tmp_path: Path):
    run = _make_complete_run(tmp_path / "run")
    (run / "final-checkpoint.pt").write_bytes(b"tampered")
    with pytest.raises(receipt.SmokeReceiptError, match="final checkpoint hash mismatch"):
        receipt.validate_completed_run(run)

    run = _make_complete_run(tmp_path / "run2")
    (run / "checkpoints" / "ep-000001-main.pt").unlink()
    with pytest.raises(receipt.SmokeReceiptError, match="periodic checkpoint 0"):
        receipt.validate_completed_run(run)


def test_rejects_unsafe_claim_and_candidate_cap(tmp_path: Path):
    run = _make_complete_run(tmp_path / "run")
    status_path = run / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["claim_ceiling"] = "EE efficacy is established"
    status["result"]["claim_ceiling"] = status["claim_ceiling"]
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(receipt.SmokeReceiptError, match="required bounded-claim language"):
        receipt.validate_completed_run(run)

    run = _make_complete_run(tmp_path / "run2")
    status_path = run / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["config"]["max_c2_candidates"] = 1
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(receipt.SmokeReceiptError, match="max_c2_candidates"):
        receipt.validate_completed_run(run)


def test_rejects_policy_code_authority_tamper(tmp_path: Path):
    run = _make_complete_run(tmp_path / "run")
    status_path = run / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["result"]["mechanism_authority"]["policy_compositor_version"] = (
        "forged-compositor"
    )
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(receipt.SmokeReceiptError, match="policy_compositor_version"):
        receipt.validate_completed_run(run)


def test_refuses_receipt_overwrite(tmp_path: Path):
    run = _make_complete_run(tmp_path / "run")
    output = tmp_path / "receipt.json"
    receipt.write_smoke_receipt(run, output)
    with pytest.raises(FileExistsError, match="overwrite"):
        receipt.write_smoke_receipt(run, output)


def test_cli_loads_module_bound_carrier_from_repo_root(tmp_path: Path):
    """The standalone CLI must load the same module-bound carrier as the runner."""

    run = _make_complete_run(tmp_path / "run")
    carrier_path = run / "carrier-state.pt"
    carrier = torch.load(carrier_path, map_location="cpu", weights_only=False)
    carrier["module_probe"] = smc_er_core.FrozenDict({"source": "C2"})
    torch.save(carrier, carrier_path)
    status_path = run / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["result"]["carrier_state_sha256"] = _sha(carrier_path)
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    output = tmp_path / "receipt.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(HERE / "c2_v03_smoke_receipt.py"),
            "--input-dir",
            str(run),
            "--receipt",
            str(output),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
