"""Public queue tests for the C2 V0.3A matched five-arm matrix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_v03a_trend_matrix as matrix  # noqa: E402


def test_arm_command_uses_only_v03a_authority_bound_runner(tmp_path):
    authority = tmp_path / "1500-lr0p001.json"
    output = tmp_path / "matrix" / "F111"
    tle_root = tmp_path / "tle"

    command = matrix.arm_command(
        authority_path=authority,
        arm="F111",
        output_dir=output,
        tle_root=tle_root,
    )

    assert command[0] == sys.executable
    assert Path(command[1]).name == "c2_v03a_trend_arm.py"
    assert "run_short_ep.py" not in " ".join(command)
    assert command[-8:] == [
        "--authority",
        str(authority.resolve()),
        "--arm",
        "F111",
        "--output-dir",
        str(output.resolve()),
        "--tle-root",
        str(tle_root.resolve()),
    ]


def test_arm_command_exposes_fresh_output_resume_state(tmp_path):
    resume = tmp_path / "previous" / "latest.pt"
    command = matrix.arm_command(
        authority_path=tmp_path / "authority.json",
        arm="F111",
        output_dir=tmp_path / "new-segment",
        tle_root=tmp_path / "tle",
        resume_state=resume,
    )

    assert command[-2:] == ["--resume-state", str(resume.resolve())]


def _arm_plan(tmp_path: Path, *, contract_errors: int = 0) -> matrix.ArmPlan:
    output = tmp_path / "arms" / "F111"
    output.mkdir(parents=True)
    checkpoint = output / "final-checkpoint.pt"
    checkpoint.write_bytes(b"checkpoint")
    checkpoint_sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    status = {
        "status": "complete",
        "arm": "F111",
        "episodes_planned": 1500,
        "formal_training_authorized": False,
        "result": {
            "start_episode": 0,
            "episodes_completed": 1500,
            "checkpoint_sha256": checkpoint_sha,
            "checkpoint_every_episodes": 100,
            "periodic_checkpoint_count": 15,
            "c1_prefill": {"enters_main": False},
            "telemetry": {
                "c2": {"candidate_outcomes": {"contract_error": contract_errors}}
            },
            "mechanism_authority": {
                "environment_source_sha256": "a" * 64
            },
        },
    }
    (output / "status.json").write_text(json.dumps(status), encoding="utf-8")
    return matrix.ArmPlan(
        arm="F111",
        output_dir=output,
        log_path=tmp_path / "F111.log",
        command=("python", "arm.py"),
    )


def test_verify_arm_rejects_nonzero_c2_contract_errors(tmp_path):
    result = matrix.verify_arm(
        _arm_plan(tmp_path, contract_errors=1), planned_episodes=1500
    )

    assert result["status"] == "FAIL"
    assert "C2 runtime contract errors" in " ".join(result["failures"])


def test_verify_arm_accepts_resume_segment_checkpoint_count(tmp_path):
    plan = _arm_plan(tmp_path)
    status_path = plan.output_dir / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["result"]["start_episode"] = 700
    status["result"]["periodic_checkpoint_count"] = 8
    status_path.write_text(json.dumps(status), encoding="utf-8")

    result = matrix.verify_arm(plan, planned_episodes=1500)

    assert result["status"] == "PASS"
    assert result["start_episode"] == 700


def test_resume_state_parser_rejects_baseline_and_duplicates(tmp_path):
    try:
        matrix._resume_states([f"B000={tmp_path / 'state.pt'}"])
    except matrix.V03ATrendMatrixError as error:
        assert "B000" in str(error)
    else:  # pragma: no cover
        raise AssertionError("baseline resume was accepted")

    try:
        matrix._resume_states(
            [f"F111={tmp_path / 'one.pt'}", f"F111={tmp_path / 'two.pt'}"]
        )
    except matrix.V03ATrendMatrixError as error:
        assert "unique" in str(error)
    else:  # pragma: no cover
        raise AssertionError("duplicate resume binding was accepted")
