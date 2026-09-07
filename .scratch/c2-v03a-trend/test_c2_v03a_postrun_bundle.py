"""Executable fail-closed tests for the V0.3A post-run bundle."""

from __future__ import annotations

import json
import csv
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_v03a_postrun_bundle as postrun  # noqa: E402


MECHANISM_SHA = "a" * 64
REWARD_SHA = "c" * 64


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _matrix_fixture(tmp_path: Path, *, learning_rate: float) -> tuple[Path, dict]:
    root = tmp_path / f"matrix-{learning_rate}"
    root.mkdir()
    authority = tmp_path / f"authority-{learning_rate}.json"
    _write_json(authority, {"fixture": True})
    prereg = tmp_path / "prereg.json"
    if not prereg.exists():
        _write_json(prereg, {"sealed": True})

    episodes = postrun.MATRIX_EPISODES
    schedule = tuple(range(100, episodes + 1, 100))
    validated = {
        "schema": "multi-catfish-mcrl-c2-v03a-trend-authority-v1",
        "status": "PASS",
        "episodes": episodes,
        "learning_rate": learning_rate,
        "checkpoint_every_episodes": 100,
        "users": 100,
        "seeds": {
            "training": 101,
            "environment": 102,
            "mobility": 103,
        },
        "evaluation_users": [60, 80, 100, 120, 140],
        "evaluation_seeds": [201, 202, 203, 204, 205],
        "tle_file_set_sha256": "b" * 64,
        "tle_file_count": 7,
        "canonical_prereg": str(prereg.resolve()),
        "tle_root": str(tmp_path.resolve()),
    }
    trainer_config = {"learning_rate": learning_rate, "hidden_layers": [8, 8]}
    telemetry = {
        "schema": postrun.TELEMETRY_SCHEMA,
        "main": {
            "steps": episodes * 10,
            "useful_bits": 2000.0,
            "energy_j": 1000.0,
            "ratio_of_sums_ee_bits_per_j": 2.0,
            "served_user_intervals": episodes * 10 * 90,
            "user_intervals": episodes * 10 * 100,
            "served_fraction": 0.9,
            "canonical_reward_sum": [1.0, -2.0, -3.0],
        },
        "c2": {
            "schedules": 0,
            "empty_anchor_attempts": 0,
            "scheduled_candidates": 0,
            "candidate_outcomes": {
                "certificate_pass": 0,
                "certificate_fail": 0,
                "support_rejection": 0,
                "contract_error": 0,
            },
            "choice_counts": {"K0": 0, "K1": 0, "K>=2": 0},
            "forecast_wall_time_s": 0.0,
            "options_executed": 0,
            "option_primitive_steps": 0,
            "admitted_options": 0,
            "q2f_updates": 0,
            "joint_commits": 0,
        },
    }
    runs = {}
    verifications = {}
    for arm in postrun.ALLOWED_ARMS:
        log = root / "logs" / f"{arm}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"complete {arm}\n", encoding="utf-8")
        checkpoint = root / "arms" / arm / "final-checkpoint.pt"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_bytes(f"checkpoint-{arm}".encode("ascii"))
        periodic_rows = []
        for completed in schedule:
            periodic = (
                root
                / "arms"
                / arm
                / "checkpoints"
                / f"ep-{completed:06d}-main.pt"
            )
            periodic.parent.mkdir(parents=True, exist_ok=True)
            periodic.write_bytes(f"checkpoint-{arm}-{completed}".encode("ascii"))
            periodic_rows.append(
                {
                    "episodes_completed": completed,
                    "episode_index": completed - 1,
                    "path": str(periodic.resolve()),
                    "sha256": postrun.sha256_file(periodic),
                    "checkpoint_kind": "periodic-main-policy-trend",
                    "load_round_trip": "PASS",
                }
            )
        telemetry_path = root / "arms" / arm / "run-telemetry.json"
        _write_json(telemetry_path, telemetry)
        active = list(postrun.EXPECTED_ACTIVE_SOURCES[arm])
        result = {
            "trainer_config": trainer_config,
            "episodes_completed": episodes,
            "active_sources": active,
            "checkpoint": str(checkpoint.resolve()),
            "checkpoint_sha256": postrun.sha256_file(checkpoint),
            "periodic_checkpoints": periodic_rows,
            "periodic_checkpoint_count": len(periodic_rows),
            "telemetry": telemetry,
            "telemetry_path": str(telemetry_path.resolve()),
            "telemetry_sha256": postrun.sha256_file(telemetry_path),
            "mechanism_authority": {
                "environment_source_sha256": MECHANISM_SHA
            },
        }
        if arm == "B000":
            result["episodes"] = episodes
        else:
            result.update(
                {
                    "start_episode": 0,
                    "artifact_scope": "complete_run",
                    "consumed_bundle_count": 0,
                    "joint_transaction_count": 0,
                }
            )
            update_rows = [
                {
                    "episode": index // 10,
                    "step": index % 10,
                    "main_update_calls": 1,
                    "main_carrier": {"active_sources": []},
                    "formal_c2_owned_main_update": False,
                }
                for index in range(episodes * 10)
            ]
            _write_json(
                root / "arms" / arm / "main-update-receipts.json", update_rows
            )
        status_path = root / "arms" / arm / "status.json"
        _write_json(
            status_path,
            {
                "schema": postrun.arm_runner.STATUS_SCHEMA,
                "status": "complete",
                "run_mode": "fresh_intermediate_trend",
                "arm": arm,
                "label": postrun.ARM_LABELS[arm],
                "episodes_planned": episodes,
                "episodes_executed": episodes,
                "users": 100,
                "seeds": validated["seeds"],
                "authority_path": str(authority.resolve()),
                "authority": validated,
                "loop_config": {
                    "arm": arm,
                    "episodes": episodes,
                    "users": 100,
                    "train_seed": 101,
                    "env_seed": 102,
                    "mobility_seed": 103,
                    "checkpoint_every": 100,
                },
                "trainer_config": trainer_config,
                "formal_training_authorized": False,
                "result": result,
                "claim_ceiling": postrun.CLAIM_CEILING,
            },
        )
        runs[arm] = {
            "arm": arm,
            "status": "process_complete",
            "exit_code": 0,
            "log": str(log.resolve()),
            "log_sha256": postrun.sha256_file(log),
        }
        verifications[arm] = {
            "arm": arm,
            "status": "PASS",
            "failures": [],
            "episodes_completed": episodes,
            "start_episode": 0,
            "periodic_checkpoint_count": len(schedule),
            "c2_contract_errors": 0,
            "checkpoint": str(checkpoint.resolve()),
            "checkpoint_sha256": postrun.sha256_file(checkpoint),
            "status_path": str(status_path.resolve()),
            "status_sha256": postrun.sha256_file(status_path),
            "mechanism_environment_source_sha256": MECHANISM_SHA,
        }

    evaluation = root / "evaluation"
    evaluation.mkdir()
    summary = evaluation / "sweep-summary.json"
    _write_json(summary, {"summary": []})
    sweep_log = root / "logs" / "main-only-sweep.log"
    sweep_log.write_text("complete\n", encoding="utf-8")
    matrix = {
        "schema": postrun.MATRIX_SCHEMA,
        "status": "complete",
        "authority": str(authority.resolve()),
        "authority_sha256": postrun.sha256_file(authority),
        "learning_rate": learning_rate,
        "episodes": episodes,
        "runs": runs,
        "verifications": verifications,
        "mechanism_consistency": {
            "status": "PASS",
            "observed_environment_source_sha256": [MECHANISM_SHA],
        },
        "main_only_sweep": {
            "exit_code": 0,
            "log": str(sweep_log.resolve()),
            "log_sha256": postrun.sha256_file(sweep_log),
            "summary": str(summary.resolve()),
            "summary_sha256": postrun.sha256_file(summary),
        },
        "formal_training_authorized": False,
        "claim_ceiling": postrun.CLAIM_CEILING,
    }
    _write_json(root / "matrix-status.json", matrix)
    return root, validated


def _patch_checkpoint_reader(monkeypatch, *, learning_rate: float) -> None:
    def fake_read_checkpoint(path, *, map_location):
        checkpoint = Path(path)
        arm = checkpoint.parent.parent.name if checkpoint.parent.name == "checkpoints" else checkpoint.parent.name
        completed = (
            int(checkpoint.stem.split("-")[1])
            if checkpoint.parent.name == "checkpoints"
            else postrun.MATRIX_EPISODES
        )
        return SimpleNamespace(
            episode=completed - 1,
            checkpoint_kind=(
                "periodic-main-policy-trend"
                if checkpoint.parent.name == "checkpoints"
                else "final-episode-policy"
            ),
            train_seed=101,
            env_seed=102,
            mobility_seed=103,
            state_dim=4,
            action_dim=3,
            trainer_config={"learning_rate": learning_rate, "hidden_layers": [8, 8]},
            q_networks=[{"weight": f"{arm}-{completed}-{index}"} for index in range(3)],
            target_networks=[{"weight": f"target-{arm}-{completed}-{index}"} for index in range(3)],
            optimizers=[{}],
        )

    monkeypatch.setattr(postrun, "read_checkpoint", fake_read_checkpoint)
    monkeypatch.setattr(
        postrun.arm_runner.c2_runner,
        "_torch_load_runtime_state",
        lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
    )


def _rewrite_arm_status(root: Path, arm: str, status: dict) -> None:
    status_path = root / "arms" / arm / "status.json"
    _write_json(status_path, status)
    matrix_path = root / "matrix-status.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["verifications"][arm]["status_sha256"] = postrun.sha256_file(status_path)
    _write_json(matrix_path, matrix)


def _convert_treatment_to_resume(
    root: Path,
    *,
    arm: str = "F111",
    start_episode: int = 100,
) -> dict:
    status_path = root / "arms" / arm / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    episodes = int(status["episodes_planned"])
    segment_episodes = episodes - start_episode
    result = status["result"]
    result["start_episode"] = start_episode
    result["episodes_executed"] = segment_episodes
    result["artifact_scope"] = "resume_segment_only"
    retained_checkpoints = []
    for row in result["periodic_checkpoints"]:
        if row["episodes_completed"] > start_episode:
            retained_checkpoints.append(row)
        else:
            Path(row["path"]).unlink()
    result["periodic_checkpoints"] = retained_checkpoints
    result["periodic_checkpoint_count"] = len(result["periodic_checkpoints"])
    result["mechanism_authority"]["reward_source_sha256"] = REWARD_SHA

    telemetry = result["telemetry"]
    telemetry["main"].update(
        {
            "steps": segment_episodes * 10,
            "served_user_intervals": segment_episodes * 10 * 90,
            "user_intervals": segment_episodes * 10 * 100,
        }
    )
    telemetry_path = Path(result["telemetry_path"])
    _write_json(telemetry_path, telemetry)
    result["telemetry_sha256"] = postrun.sha256_file(telemetry_path)

    update_rows = [
        {
            "episode": start_episode + index // 10,
            "step": index % 10,
            "main_update_calls": 1,
            "main_carrier": {"active_sources": []},
            "formal_c2_owned_main_update": False,
        }
        for index in range(segment_episodes * 10)
    ]
    _write_json(root / "arms" / arm / "main-update-receipts.json", update_rows)

    resume_path = root / f"{arm}-resume-source.pt"
    resume_payload = {
        "schema": postrun.arm_runner.c2_runner.RUNTIME_STATE_SCHEMA,
        "format_version": postrun.arm_runner.c2_runner.RUNTIME_STATE_FORMAT_VERSION,
        "boundary": "episode",
        "episodes_completed": start_episode,
        "source_order": ["Main", "C1", "C2", "C3"],
        "loop_config": status["loop_config"],
        "trainer_config": status["trainer_config"],
        "main_training_state": {"trainer_config": status["trainer_config"]},
        "authority": {
            "checkpoint_sha256": "d" * 64,
            "environment_source_sha256": MECHANISM_SHA,
            "reward_source_sha256": REWARD_SHA,
        },
    }
    _write_json(resume_path, resume_payload)
    result["resume_source"] = {
        "path": str(resume_path.resolve()),
        "sha256": postrun.sha256_file(resume_path),
        "episodes_completed": start_episode,
        "artifact_scope": "new continuation segment",
    }
    status["run_mode"] = "resume_intermediate_trend"
    status["episodes_executed"] = segment_episodes
    _rewrite_arm_status(root, arm, status)

    matrix_path = root / "matrix-status.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["verifications"][arm]["start_episode"] = start_episode
    matrix["verifications"][arm]["periodic_checkpoint_count"] = len(
        result["periodic_checkpoints"]
    )
    _write_json(matrix_path, matrix)
    return status


def test_validate_matrix_checks_all_arm_receipts(tmp_path, monkeypatch):
    monkeypatch.setattr(postrun, "MATRIX_EPISODES", 200)
    root, validated = _matrix_fixture(tmp_path, learning_rate=0.001)
    _patch_checkpoint_reader(monkeypatch, learning_rate=0.001)
    monkeypatch.setattr(
        postrun.arm_runner,
        "load_and_validate_authority",
        lambda _path, *, tle_root: validated,
    )
    calls = []

    def fake_sweep_verifier(**kwargs):
        calls.append(kwargs)
        return {
            "status": "PASS",
            "failures": [],
            "observed_raw_rows": 125,
            "zero_power_longer_run_gate": "PASS",
        }

    monkeypatch.setattr(postrun, "verify_pilot100_sweep", fake_sweep_verifier)
    monkeypatch.setattr(
        postrun,
        "_validate_sweep_csv_exports",
        lambda _output: {"fixture": {"status": "PASS"}},
    )

    receipt = postrun.validate_matrix(
        root, tle_root=tmp_path, expected_learning_rate=0.001
    )

    assert receipt["status"] == "PASS"
    assert len(receipt["arms"]) == 5
    assert calls[0]["expected_episode_index"] == 199
    assert calls[0]["evaluation_users"] == [60, 80, 100, 120, 140]


def test_validate_matrix_fails_on_nonzero_contract_error(tmp_path, monkeypatch):
    monkeypatch.setattr(postrun, "MATRIX_EPISODES", 200)
    root, validated = _matrix_fixture(tmp_path, learning_rate=0.001)
    _patch_checkpoint_reader(monkeypatch, learning_rate=0.001)
    matrix_path = root / "matrix-status.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["verifications"]["F111"]["c2_contract_errors"] = 1
    _write_json(matrix_path, matrix)
    monkeypatch.setattr(
        postrun.arm_runner,
        "load_and_validate_authority",
        lambda _path, *, tle_root: validated,
    )
    monkeypatch.setattr(
        postrun,
        "_validate_sweep_csv_exports",
        lambda _output: {"fixture": {"status": "PASS"}},
    )

    with pytest.raises(postrun.V03APostrunError, match="F111 training verification"):
        postrun.validate_matrix(
            root, tle_root=tmp_path, expected_learning_rate=0.001
        )


def test_validate_matrix_reloads_periodic_checkpoint_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(postrun, "MATRIX_EPISODES", 200)
    root, validated = _matrix_fixture(tmp_path, learning_rate=0.001)
    _patch_checkpoint_reader(monkeypatch, learning_rate=0.001)
    good_reader = postrun.read_checkpoint

    def drifted_reader(path, *, map_location):
        payload = good_reader(path, map_location=map_location)
        if "F111/checkpoints/ep-000100-main.pt" in str(path):
            payload.env_seed = 999
        return payload

    monkeypatch.setattr(postrun, "read_checkpoint", drifted_reader)
    monkeypatch.setattr(
        postrun.arm_runner,
        "load_and_validate_authority",
        lambda _path, *, tle_root: validated,
    )
    monkeypatch.setattr(
        postrun,
        "_validate_sweep_csv_exports",
        lambda _output: {"fixture": {"status": "PASS"}},
    )

    with pytest.raises(postrun.V03APostrunError, match="env_seed mismatch"):
        postrun.validate_matrix(
            root, tle_root=tmp_path, expected_learning_rate=0.001
        )


def _resume_validation_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(postrun, "MATRIX_EPISODES", 200)
    root, validated = _matrix_fixture(tmp_path, learning_rate=0.001)
    status = _convert_treatment_to_resume(root, start_episode=100)
    _patch_checkpoint_reader(monkeypatch, learning_rate=0.001)
    monkeypatch.setattr(
        postrun.arm_runner,
        "load_and_validate_authority",
        lambda _path, *, tle_root: validated,
    )
    monkeypatch.setattr(
        postrun,
        "verify_pilot100_sweep",
        lambda **kwargs: {
            "status": "PASS",
            "failures": [],
            "observed_raw_rows": 125,
            "zero_power_longer_run_gate": "PASS",
        },
    )
    monkeypatch.setattr(
        postrun,
        "_validate_sweep_csv_exports",
        lambda _output: {"fixture": {"status": "PASS"}},
    )
    return root, status


def test_endpoint_postrun_accepts_legal_resume_segment(tmp_path, monkeypatch):
    root, _status = _resume_validation_fixture(tmp_path, monkeypatch)

    receipt = postrun.validate_matrix(
        root, tle_root=tmp_path, expected_learning_rate=0.001
    )

    arm = next(row for row in receipt["arms"] if row["arm"] == "F111")
    assert arm["start_episode"] == 100
    assert arm["episodes_executed"] == 100
    assert arm["periodic_checkpoint_count"] == 1
    assert arm["artifact_history_scope"] == "resume_segment_only"
    assert arm["checkpoint_trajectory_eligible"] is False
    assert arm["resume_source"]["episodes_completed"] == 100


def test_endpoint_postrun_rejects_resume_mode_scope_mismatch(tmp_path, monkeypatch):
    root, status = _resume_validation_fixture(tmp_path, monkeypatch)
    status["run_mode"] = "fresh_intermediate_trend"
    _rewrite_arm_status(root, "F111", status)

    with pytest.raises(postrun.V03APostrunError, match="resume-run artifact scope"):
        postrun.validate_matrix(
            root, tle_root=tmp_path, expected_learning_rate=0.001
        )


def test_endpoint_postrun_rejects_resume_snapshot_boundary_drift(
    tmp_path, monkeypatch
):
    root, status = _resume_validation_fixture(tmp_path, monkeypatch)
    source = status["result"]["resume_source"]
    source_path = Path(source["path"])
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["episodes_completed"] = 99
    _write_json(source_path, payload)
    source["sha256"] = postrun.sha256_file(source_path)
    _rewrite_arm_status(root, "F111", status)

    with pytest.raises(postrun.V03APostrunError, match="snapshot episodes_completed"):
        postrun.validate_matrix(
            root, tle_root=tmp_path, expected_learning_rate=0.001
        )


def test_endpoint_postrun_rejects_prestart_checkpoint_in_resume_directory(
    tmp_path, monkeypatch
):
    root, _status = _resume_validation_fixture(tmp_path, monkeypatch)
    injected = root / "arms" / "F111" / "checkpoints" / "ep-000100-main.pt"
    injected.write_bytes(b"unexpected historical checkpoint")

    with pytest.raises(postrun.V03APostrunError, match="unexpected history"):
        postrun.validate_matrix(
            root, tle_root=tmp_path, expected_learning_rate=0.001
        )


def test_endpoint_postrun_rejects_resume_local_clock_or_full_run_telemetry(
    tmp_path, monkeypatch
):
    root, status = _resume_validation_fixture(tmp_path, monkeypatch)
    updates_path = root / "arms" / "F111" / "main-update-receipts.json"
    updates = json.loads(updates_path.read_text(encoding="utf-8"))
    updates[0]["episode"] = 0
    _write_json(updates_path, updates)

    with pytest.raises(postrun.V03APostrunError, match="clock mismatch"):
        postrun.validate_matrix(
            root, tle_root=tmp_path, expected_learning_rate=0.001
        )

    updates[0]["episode"] = 100
    _write_json(updates_path, updates)
    telemetry = status["result"]["telemetry"]
    telemetry["main"]["steps"] = 2000
    telemetry_path = Path(status["result"]["telemetry_path"])
    _write_json(telemetry_path, telemetry)
    status["result"]["telemetry_sha256"] = postrun.sha256_file(telemetry_path)
    _rewrite_arm_status(root, "F111", status)

    with pytest.raises(postrun.V03APostrunError, match="Main step count"):
        postrun.validate_matrix(
            root, tle_root=tmp_path, expected_learning_rate=0.001
        )


def _selector_summary(path: Path, *, full: float) -> Path:
    endpoint = {
        "Baseline MODQN": 100.0,
        "Full Multi-Catfish MCRL": full,
        "Full - C1": 105.0,
        "Full - C2": 104.0,
        "Full - C3": 103.0,
    }
    rows = []
    for label in postrun.ARM_LABELS.values():
        for users in (60, 80, 100, 120, 140):
            rows.append(
                {
                    "arm": label,
                    "users": users,
                    "mean_ee_bits_per_j": (
                        endpoint[label] if users == 100 else endpoint[label] * users / 100
                    ),
                    "seed_rows": [{"served_fraction": 0.95}],
                }
            )
    _write_json(
        path,
        {
            "schema": "multi-catfish-mcrl-short-ep-ee-users-sweep-v2",
            "users": [60, 80, 100, 120, 140],
            "summary": rows,
        },
    )
    return path


def test_bundle_renders_both_sweeps_and_applies_frozen_selector(
    tmp_path, monkeypatch
):
    first = _selector_summary(tmp_path / "first.json", full=110.0)
    second = _selector_summary(tmp_path / "second.json", full=99.0)

    def fake_validate(root, *, tle_root, expected_learning_rate):
        summary = first if expected_learning_rate == 0.001 else second
        return {
            "status": "PASS",
            "sweep_summary": str(summary),
            "mechanism_environment_source_sha256": MECHANISM_SHA,
            "normalized_authority_excluding_learning_rate_sha256": "c" * 64,
        }

    monkeypatch.setattr(postrun, "validate_matrix", fake_validate)
    output = tmp_path / "bundle"
    receipt = postrun.build_postrun_bundle(
        lr0p001_root=tmp_path / "lr1",
        lr0p01_root=tmp_path / "lr2",
        tle_root=tmp_path,
        output_dir=output,
    )

    assert receipt["status"] == "PASS"
    assert receipt["decision"] == "SELECT_AND_RUN_FRESH_3000"
    assert receipt["selected_learning_rate"] == 0.001
    assert receipt["fresh_3000_launch_performed"] is False
    assert (output / "lr0p001-ee-vs-users.svg").is_file()
    assert (output / "lr0p01-ee-vs-users.svg").is_file()
    assert (output / "u100-lr-comparisons.csv").is_file()
    assert (output / "ablation-contrasts.json").is_file()
    assert (output / "ablation-contrasts.csv").is_file()
    assert (output / "postrun-receipt.json").is_file()

    contrasts = json.loads(
        (output / "ablation-contrasts.json").read_text(encoding="utf-8")
    )
    assert len(contrasts["rows"]) == 10
    lr1_u100 = next(
        row
        for row in contrasts["rows"]
        if row["learning_rate"] == 0.001 and row["users"] == 100
    )
    assert lr1_u100["all_four_comparisons_positive"] is True


def test_bundle_rejects_cross_lr_authority_drift(tmp_path, monkeypatch):
    first = _selector_summary(tmp_path / "first.json", full=110.0)
    second = _selector_summary(tmp_path / "second.json", full=111.0)

    def fake_validate(root, *, tle_root, expected_learning_rate):
        return {
            "status": "PASS",
            "sweep_summary": str(first if expected_learning_rate == 0.001 else second),
            "mechanism_environment_source_sha256": MECHANISM_SHA,
            "normalized_authority_excluding_learning_rate_sha256": (
                "c" * 64 if expected_learning_rate == 0.001 else "d" * 64
            ),
        }

    monkeypatch.setattr(postrun, "validate_matrix", fake_validate)
    with pytest.raises(postrun.V03APostrunError, match="differ beyond"):
        postrun.build_postrun_bundle(
            lr0p001_root=tmp_path / "lr1",
            lr0p01_root=tmp_path / "lr2",
            tle_root=tmp_path,
            output_dir=tmp_path / "bundle",
        )


def test_sweep_csv_must_exactly_match_verified_json(tmp_path):
    output = tmp_path / "evaluation"
    output.mkdir()
    raw_rows = [{"arm": "F111", "users": 100, "value": 1.25}]
    summary_rows = [
        {
            "arm": "F111",
            "users": 100,
            "mean_ee_bits_per_j": 1.25,
            "seed_rows": [{"served_fraction": 1.0}],
        }
    ]
    _write_json(output / "sweep-raw.json", raw_rows)
    _write_json(output / "sweep-summary.json", {"summary": summary_rows})
    for path, rows in (
        (output / "sweep-raw.csv", raw_rows),
        (
            output / "sweep-summary.csv",
            [{key: value for key, value in summary_rows[0].items() if key != "seed_rows"}],
        ),
    ):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    receipt = postrun._validate_sweep_csv_exports(output)
    assert receipt["sweep-raw.csv"]["status"] == "PASS"

    (output / "sweep-raw.csv").write_text(
        "arm,users,value\nF111,100,9.99\n", encoding="utf-8"
    )
    with pytest.raises(postrun.V03APostrunError, match="disagrees with JSON"):
        postrun._validate_sweep_csv_exports(output)
