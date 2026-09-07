from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_intermediate_trend_matrix", HERE / "run_intermediate_trend_matrix.py"
)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def _validated(*, episodes: int = 1500, learning_rate: float = 0.001):
    return {
        "schema": "multi-catfish-mcrl-intermediate-trend-authority-v1",
        "status": "PASS",
        "claim_ceiling": "ONE_SEED_INTERMEDIATE_TREND_SCREEN_NOT_CHAPTER5_NOT_FORMAL_EFFICACY_NOT_9000",
        "evidence_ceiling": "Intermediate trend screen only",
        "episodes": episodes,
        "learning_rate": learning_rate,
        "arms": list(M.ALLOWED_ARMS),
        "seeds": {
            "training": 101,
            "environment": 102,
            "mobility": 103,
            "evaluation_seeds": [104, 105, 106, 107, 108],
        },
        "config": {
            "users": 100,
            "evaluation_users": [60, 80, 100, 120, 140],
            "epsilon_decay_episodes": 2000,
            "target_update_every": 50,
            "checkpoint_every_episodes": 100,
            "specialist_bundle_replay_capacity": 2000,
            "donor_beta": 0.25,
            "acrm_eta": 1.0,
        },
        "authority": {
            "canonical_prereg": "/tmp/prereg.json",
            "c1_exp_corpus_manifest": "/tmp/corpus.json",
            "tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256,
        },
    }


def test_runner_commands_bind_all_fixed_authority_values(monkeypatch, tmp_path):
    validated = _validated(episodes=3000, learning_rate=0.01)
    prereg = tmp_path / "prereg.json"
    corpus = tmp_path / "corpus.json"
    prereg.write_text("{}", encoding="utf-8")
    corpus.write_text("{}", encoding="utf-8")
    command = M.runner_command(
        authority_path=tmp_path / "authority.json",
        validated=validated,
        arm="F111",
        output_dir=tmp_path / "F111",
        tle_root=tmp_path / "tle",
        prereg=prereg,
        c1_corpus=corpus,
    )
    assert command.count("--arm") == 1
    assert command[command.index("--arm") + 1] == "F111"
    assert command[command.index("--episodes") + 1] == "3000"
    assert command[command.index("--learning-rate") + 1] == "0.01"
    assert command[command.index("--epsilon-decay-episodes") + 1] == "2000"
    assert command[command.index("--target-update-every") + 1] == "50"
    assert command[command.index("--checkpoint-every") + 1] == "100"
    assert command[command.index("--acrm-eta") + 1] == "1.0"
    assert "--intermediate-trend-authority" in command
    assert "--development-route-all" not in command
    assert "--gate-manifest" not in command
    assert command[command.index("--c1-exp-corpus-manifest") + 1] == str(corpus)

    baseline = M.runner_command(
        authority_path=tmp_path / "authority.json",
        validated=validated,
        arm="B000",
        output_dir=tmp_path / "B000",
        tle_root=tmp_path / "tle",
        prereg=prereg,
        c1_corpus=corpus,
    )
    assert "--c1-exp-corpus-manifest" not in baseline


def test_smoke_command_exercises_same_arm_path_without_claiming_trend(tmp_path):
    validated = _validated()
    command = M.smoke_runner_command(
        validated=validated,
        arm="F111",
        output_dir=tmp_path / "F111",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
        c1_corpus=tmp_path / "corpus.json",
    )
    assert command[command.index("--episodes") + 1] == "10"
    assert "--development-route-all" in command
    assert "--intermediate-trend-authority" not in command
    assert command[command.index("--checkpoint-every") + 1] == "100"

    baseline = M.smoke_runner_command(
        validated=validated,
        arm="B000",
        output_dir=tmp_path / "B000",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
        c1_corpus=tmp_path / "corpus.json",
    )
    assert "--development-route-all" not in baseline


def test_sweep_command_uses_authority_evaluation_users_and_seeds(tmp_path):
    validated = _validated()
    checkpoints = {arm: tmp_path / f"{arm}.pt" for arm in M.ALLOWED_ARMS}
    command = M.sweep_command(
        validated=validated,
        checkpoints=checkpoints,
        output_dir=tmp_path / "ee-sweep",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
    )
    assert command.count("--arm") == 5
    assert command[command.index("--users") + 1 : command.index("--seeds")] == [
        "60",
        "80",
        "100",
        "120",
        "140",
    ]
    assert command[command.index("--seeds") + 1 : command.index("--output-dir")] == [
        "104",
        "105",
        "106",
        "107",
        "108",
    ]
    assert [item for item in command if item.startswith("Baseline MODQN=")] == [
        f"Baseline MODQN={checkpoints['B000']}"
    ]


def test_tle_file_set_hash_matches_repository_freeze_rule(tmp_path):
    (tmp_path / "starlink_20260801.tle").write_bytes(b"one")
    (tmp_path / "starlink_20260802.tle").write_bytes(b"two")
    expected = M.sha256_file(tmp_path / "starlink_20260801.tle")
    expected_2 = M.sha256_file(tmp_path / "starlink_20260802.tle")
    import hashlib

    digest, count = M.canonical_tle_file_set_hash(tmp_path)
    manual = hashlib.sha256(
        f"starlink_20260801.tle:{expected}\nstarlink_20260802.tle:{expected_2}".encode()
    ).hexdigest()
    assert digest == manual
    assert count == 2


def test_existing_output_root_is_rejected_before_authority_or_tle_work(tmp_path, monkeypatch):
    output = tmp_path / "already-there"
    output.mkdir()
    called = False

    def should_not_load(_path):
        nonlocal called
        called = True
        raise AssertionError("authority must not be loaded")

    monkeypatch.setattr(M, "load_and_validate_authority", should_not_load)
    with pytest.raises(M.IntermediateTrendMatrixError, match="must be absent"):
        M.run_matrix(
            authority_path=tmp_path / "authority.json",
            output_root=output,
            tle_root=tmp_path / "tle",
            max_parallel=1,
        )
    assert not called


def test_authority_loader_calls_canonical_validator(monkeypatch, tmp_path):
    authority = tmp_path / "authority.json"
    authority.write_text(json.dumps({"episodes": 1500}), encoding="utf-8")
    calls = []

    def fake_validator(request, *, repo, tle_root):
        calls.append((request, repo, tle_root))
        return _validated()

    monkeypatch.setattr(M, "validate_intermediate_trend_authority", fake_validator)
    tle_root = tmp_path / "tle"
    result = M.load_and_validate_authority(authority, tle_root=tle_root)
    assert result["status"] == "PASS"
    assert calls == [({"episodes": 1500}, M.REPO, tle_root.resolve())]


def test_parse_max_rss_kb_and_time_wrapper(tmp_path, monkeypatch):
    usage = tmp_path / "time-v.log"
    usage.write_text(
        "Maximum resident set size (kbytes): 12345\n", encoding="utf-8"
    )
    assert M.parse_max_rss_kb(usage) == 12345
    monkeypatch.setattr(M, "TIME_V", Path("/usr/bin/time"))
    wrapped, enabled = M.timed_command(["python", "fake.py"], usage)
    assert enabled is (Path("/usr/bin/time").is_file() and os.access("/usr/bin/time", os.X_OK))
    if enabled:
        assert wrapped[:4] == ["/usr/bin/time", "-v", "-o", str(usage)]
        assert wrapped[-2:] == ["python", "fake.py"]


def test_sweep_output_verification_requires_main_only_data_receipts(tmp_path):
    validated = _validated()
    config = validated["config"] | {"evaluation_users": [60, 80, 100, 120, 140], "evaluation_seeds": [104, 105, 106, 107, 108]}
    out = tmp_path / "ee-sweep"
    out.mkdir()
    (out / "sweep-summary.json").write_text(
        json.dumps(
            {
                "users": config["evaluation_users"],
                "evaluation_seeds": config["evaluation_seeds"],
                "evaluation_policy": "Main-only masked-greedy MODQN",
                "authority": {"tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256},
            }
        ),
        encoding="utf-8",
    )
    (out / "sweep-raw.json").write_text("[]", encoding="utf-8")
    (out / "plot-status.json").write_text("{}", encoding="utf-8")
    result = M.verify_sweep_output(
        output_dir=out,
        validated=validated,
        expected_tle_hash=M.CANONICAL_TLE_FILE_SET_SHA256,
        config=config,
    )
    assert result["status"] == "PASS"


def test_arm_output_verification_rejects_missing_100ep_checkpoint_sequence(
    tmp_path
):
    validated = _validated()
    config = M._config(validated)
    output = tmp_path / "B000"
    output.mkdir()
    checkpoint = output / "final-checkpoint.pt"
    checkpoint.write_bytes(b"final")
    status = {
        "status": "complete",
        "arm": "B000",
        "label": M.ARM_LABELS["B000"],
        "episodes": validated["episodes"],
        "users": config["users"],
        "seeds": {
            "training": config["training_seed"],
            "environment": config["environment_seed"],
            "mobility": config["mobility_seed"],
        },
        "config": {
            "episodes": validated["episodes"],
            "users": config["users"],
            "learning_rate": validated["learning_rate"],
            "epsilon_decay_episodes": 2000,
            "target_update_every_episodes": 50,
        },
        "checkpointing": {
            "every_episodes": 100,
            "specialist_bundle_replay_capacity": 2000,
        },
        "authority": {
            "tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256
        },
        "gate_manifest": {
            "validated": {"config": {"acrm_eta": 1.0}}
        },
        "result": {
            "checkpoint": str(checkpoint),
            "checkpoint_sha256": M.sha256_file(checkpoint),
            "checkpoint_every_episodes": 100,
            "periodic_checkpoint_count": 0,
            "periodic_checkpoints": [],
            "rolling_resume_state": None,
        },
    }
    (output / "status.json").write_text(json.dumps(status), encoding="utf-8")
    plan = M.ArmPlan(
        arm="B000",
        output_dir=output,
        command=("fake",),
        log_path=tmp_path / "B000.log",
        usage_path=tmp_path / "B000.time-v.log",
    )
    result = M.verify_arm_output(
        plan=plan,
        validated=validated,
        config=config,
        expected_tle_hash=M.CANONICAL_TLE_FILE_SET_SHA256,
    )
    assert result["status"] == "FAIL"
    assert "periodic checkpoint episode sequence mismatch" in result["failures"]


def test_failure_stops_queued_arms_but_drains_already_running_arms(monkeypatch, tmp_path):
    plans = [
        M.ArmPlan(
            arm=arm,
            output_dir=tmp_path / arm,
            command=("fake", arm),
            log_path=tmp_path / f"{arm}.log",
            usage_path=tmp_path / f"{arm}.time-v.log",
        )
        for arm in M.ALLOWED_ARMS
    ]
    launched = []

    class FakeStream:
        def close(self):
            return None

    class FakeProcess:
        def __init__(self, code):
            self.code = code
            self.returncode = None

        def poll(self):
            return self.code

    def fake_launch(plan):
        launched.append(plan.arm)
        plan.log_path.write_text(plan.arm, encoding="utf-8")
        process = FakeProcess(1 if plan.arm == "B000" else 0)
        receipt = {
            "arm": plan.arm,
            "started_utc": "2026-08-28T00:00:00+00:00",
        }
        return M.Running(plan, process, FakeStream(), False, tuple(plan.command), None), receipt

    def fake_finish(item, receipt):
        receipt.update(
            {
                "status": "process_complete",
                "ended_utc": "2026-08-28T00:00:01+00:00",
                "elapsed_s": 1.0,
                "exit_code": item.process.returncode,
                "log_sha256": "a" * 64,
            }
        )
        return receipt

    monkeypatch.setattr(M, "_launch", fake_launch)
    monkeypatch.setattr(M, "_finish_running", fake_finish)
    monkeypatch.setattr(
        M,
        "verify_arm_output",
        lambda **_kwargs: {"status": "PASS", "failures": [], "checkpoint_path": "/tmp/x"},
    )
    rows, failed = M._collect_arm_runs(
        plans=plans,
        max_parallel=2,
        validated=_validated(),
        config=_validated()["config"],
        expected_tle_hash=M.CANONICAL_TLE_FILE_SET_SHA256,
        sleep_fn=lambda _seconds: None,
    )
    assert failed is True
    assert launched == ["B000", "F111"]
    assert [row["status"] for row in rows] == [
        "failed",
        "PASS",
        "not_started_after_failure",
        "not_started_after_failure",
        "not_started_after_failure",
    ]
    assert rows[0]["exit_code"] == 1
    assert rows[1]["exit_code"] == 0
