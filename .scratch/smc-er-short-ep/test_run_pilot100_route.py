from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ARM = _load("run_pilot100_arm", "run_pilot100_arm.py")
MATRIX = _load("run_pilot100_matrix", "run_pilot100_matrix.py")


def test_arm_command_has_no_numeric_or_routing_knobs(tmp_path):
    command = MATRIX.arm_command(
        authority_path=MATRIX.REPO / MATRIX.CANONICAL_AUTHORITY_RELATIVE,
        arm="F111",
        output_dir=MATRIX.REPO / MATRIX.PILOT_OUTPUT_RELATIVE / "F111",
        tle_root=tmp_path / "tle",
    )
    assert command.count("--arm") == 1
    assert command[command.index("--arm") + 1] == "F111"
    for forbidden in (
        "--episodes",
        "--learning-rate",
        "--train-seed",
        "--env-seed",
        "--mobility-seed",
        "--development-route-all",
        "--gate-manifest",
        "--checkpoint-every",
    ):
        assert forbidden not in command


def test_arm_cli_rejects_attempted_episode_override(tmp_path):
    with pytest.raises(SystemExit):
        ARM._arguments(
            [
                "--authority",
                str(tmp_path / "authority.json"),
                "--arm",
                "B000",
                "--output-dir",
                str(tmp_path / "B000"),
                "--tle-root",
                str(tmp_path / "tle"),
                "--episodes",
                "101",
            ]
        )


def test_gate_ledger_matches_each_ablation_identity():
    assert ARM._gate_ledger("B000").C1 == "shadow"
    assert vars(ARM._gate_ledger("F111")) == {
        "C1": "route",
        "C2": "route",
        "C3": "route",
    }
    assert vars(ARM._gate_ledger("A011")) == {
        "C1": "shadow",
        "C2": "route",
        "C3": "route",
    }
    assert vars(ARM._gate_ledger("A101")) == {
        "C1": "route",
        "C2": "shadow",
        "C3": "route",
    }
    assert vars(ARM._gate_ledger("A110")) == {
        "C1": "route",
        "C2": "route",
        "C3": "shadow",
    }


def test_wrong_output_root_is_rejected_before_authority_loading(monkeypatch, tmp_path):
    called = False

    def should_not_load(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("authority must not load")

    monkeypatch.setattr(MATRIX, "load_and_validate_authority", should_not_load)
    with pytest.raises(MATRIX.Pilot100MatrixError, match="canonical pilot output"):
        MATRIX._preflight(
            authority_path=tmp_path / "authority.json",
            output_root=tmp_path / "wrong",
            tle_root=tmp_path / "tle",
            max_parallel=1,
        )
    assert called is False


def test_existing_canonical_output_is_rejected_before_authority_loading(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(MATRIX, "REPO", tmp_path)
    output = tmp_path / MATRIX.PILOT_OUTPUT_RELATIVE
    output.mkdir(parents=True)
    called = False

    def should_not_load(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("authority must not load")

    monkeypatch.setattr(MATRIX, "load_and_validate_authority", should_not_load)
    with pytest.raises(MATRIX.Pilot100MatrixError, match="must be absent"):
        MATRIX._preflight(
            authority_path=tmp_path / "authority.json",
            output_root=output,
            tle_root=tmp_path / "tle",
            max_parallel=1,
        )
    assert called is False


def test_drift_check_is_total_when_authority_disappears(monkeypatch, tmp_path):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(
        MATRIX,
        "load_and_validate_authority",
        lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("gone")),
    )
    monkeypatch.setattr(
        MATRIX.matrix,
        "canonical_tle_file_set_hash",
        lambda _path: ("a" * 64, 373),
    )
    result = MATRIX._drift_check(
        {
            "authority_file": missing,
            "authority_sha256": "b" * 64,
            "tle_root": tmp_path / "tle",
            "expected_tle_hash": "a" * 64,
            "tle_file_count": 373,
            "validated": {},
        },
        phase="test",
    )
    assert result["status"] == "FAIL"
    assert result["authority_manifest_sha256_current"] is None
    assert any("disappeared" in item for item in result["failures"])


def test_preflight_receipt_is_no_write_no_launch(monkeypatch, tmp_path):
    output = tmp_path / "pilot"
    plans = [
        MATRIX.matrix.ArmPlan(
            arm=arm,
            output_dir=output / arm,
            command=("python", "runner.py", "--arm", arm),
            log_path=output / "logs" / f"{arm}.log",
            usage_path=output / "logs" / f"{arm}.time",
        )
        for arm in MATRIX.matrix.ALLOWED_ARMS
    ]
    monkeypatch.setattr(
        MATRIX,
        "_preflight",
        lambda **kwargs: {
            "authority_file": tmp_path / "authority.json",
            "authority_sha256": "c" * 64,
            "validated": {"learning_rate": 0.001},
            "actual_tle_hash": "d" * 64,
            "tle_file_count": 373,
            "plans": plans,
        },
    )
    result = MATRIX.preflight_receipt(
        authority_path=tmp_path / "authority.json",
        output_root=output,
        tle_root=tmp_path / "tle",
        max_parallel=2,
    )
    assert result["status"] == "PASS"
    assert result["no_process_launched"] is True
    assert result["episodes"] == 100
    assert [row[-1] for row in result["commands"]] == list(
        MATRIX.matrix.ALLOWED_ARMS
    )
    assert not output.exists()
