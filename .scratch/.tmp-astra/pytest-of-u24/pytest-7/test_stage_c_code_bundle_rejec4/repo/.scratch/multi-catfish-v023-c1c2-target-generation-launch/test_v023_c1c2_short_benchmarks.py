from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
runner_spec = spec_from_file_location(
    "mcrl_v023_c1c2_short_benchmark_test_module",
    HERE / "run_v023_c1c2_short_benchmarks.py",
)
assert runner_spec is not None and runner_spec.loader is not None
runner = module_from_spec(runner_spec)
sys.modules[runner_spec.name] = runner
runner_spec.loader.exec_module(runner)
controller_spec = spec_from_file_location(
    "mcrl_v023_c1c2_target_controller_status_test_module",
    HERE / "run_v023_c1c2_targets_server.py",
)
assert controller_spec is not None and controller_spec.loader is not None
controller = module_from_spec(controller_spec)
sys.modules[controller_spec.name] = controller
controller_spec.loader.exec_module(controller)


def _fixture(tmp_path: Path) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    capture = tmp_path / "capture.json"
    capture.write_bytes(b"capture\n")
    materialization = tmp_path / "materialized"
    materialization.mkdir()
    materialized_files = {
        "receipt.json": b"receipt\n",
        "c1-informed.json": b"c1-informed\n",
    }
    for name, content in materialized_files.items():
        (materialization / name).write_bytes(content)
    (materialization / "MANIFEST.sha256").write_text(
        "".join(
            f"{hashlib.sha256(content).hexdigest()}  {name}\n"
            for name, content in sorted(materialized_files.items())
        ),
        encoding="ascii",
    )

    repo = runner.REPO
    source_manifest = repo / ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json"
    source_digest = source_manifest.with_name("PREFLIGHT-MANIFEST.sha256")
    generator = repo / runner.GENERATOR_RELATIVE
    code_payload = {
        "schema": runner.CODE_MANIFEST_SCHEMA,
        "manifest_version": 2,
        "configuration": {
            "checkpoint_path": runner.D40_CHECKPOINT_RELATIVE,
            "checkpoint_schema": "multi-catfish-mcrl-v020-repriced-q1-q2-source-fit-v1-checkpoint",
            "checkpoint_sha256": runner.D40_CHECKPOINT_SHA256,
            "episode_training": False,
            "learner_update": False,
            "split": runner.TRAIN,
            "test_split_opened": False,
        },
        "r6_manifest_sha256": runner._sha(source_manifest),
        "bindings": [
            {
                "role": "target_generator",
                "path": runner.GENERATOR_RELATIVE,
                "sha256": runner._sha(generator),
            },
            {
                "role": "short_benchmark",
                "path": runner.BENCHMARK_RELATIVE,
                "sha256": runner._sha(repo / runner.BENCHMARK_RELATIVE),
            },
            {
                "role": "short_benchmark_runner",
                "path": runner.RUNNER_RELATIVE,
                "sha256": runner._sha(repo / runner.RUNNER_RELATIVE),
            },
            {
                "role": "d40_checkpoint",
                "path": ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt",
                "sha256": runner._sha(
                    repo
                    / ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt"
                ),
            },
            {
                "role": "r6_preflight_manifest",
                "path": ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.json",
                "sha256": runner._sha(source_manifest),
            },
            {
                "role": "r6_preflight_digest",
                "path": ".scratch/multi-catfish-v023-r6-fit-binding-fix/PREFLIGHT-MANIFEST.sha256",
                "sha256": runner._sha(source_digest),
            },
            *[
                {
                    "role": role,
                    "path": relative,
                    "sha256": runner._sha(repo / relative),
                }
                for role, relative in runner.OPS3_BINDINGS
            ],
        ],
    }
    code_manifest = tmp_path / "CODE-MANIFEST.json"
    code_manifest.write_bytes(runner._canonical(code_payload))
    code_manifest_digest = tmp_path / "CODE-MANIFEST.sha256"
    code_manifest_digest.write_text(
        f"{runner._sha(code_manifest)}  CODE-MANIFEST.json\n", encoding="ascii"
    )
    return {
        "capture": capture,
        "materialization": materialization,
        "source_manifest": source_manifest,
        "source_digest": source_digest,
        "code_manifest": code_manifest,
        "code_manifest_digest": code_manifest_digest,
    }


def _context(fixture: dict[str, Path]):
    context = runner._load_code_context(
        fixture["code_manifest"], fixture["code_manifest_digest"]
    )
    snapshot = runner._input_snapshot(
        context=context,
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        source_manifest=fixture["source_manifest"],
    )
    return context, snapshot


def _benchmark_payload(
    fixture: dict[str, Path],
    case: runner.BenchmarkCase,
    context: dict[str, object],
    snapshot: dict[str, object],
    timeout_s: float,
) -> dict[str, object]:
    count = case.anchor_count or 1
    rows = [
        {
            "anchor_sha256": f"{index + 1:064x}",
            "focal_user": index,
            "candidate_physical_key": [index + 1, 1],
        }
        for index in range(count)
    ]
    return {
        "schema": runner.BENCHMARK_SCHEMA,
        "status": "BENCHMARK_PASS",
        "claim_ceiling": runner.BENCHMARK_CLAIM_CEILING,
        "scope": "C2 repriced OPS-3 selected-pair generation only; no C1 timing, learner, TEST, or efficacy claim",
        "inputs": {
            "frozen_generator_sha256": context["generator_sha256"],
            "capture": str(fixture["capture"].resolve()),
            "materialization_dir": str(fixture["materialization"].resolve()),
            "split": runner.TRAIN,
            "users": runner.USERS,
            "capture_sha256": snapshot["capture_sha256"],
            "materialization_manifest_sha256": snapshot["materialization_manifest_sha256"],
            "source_manifest_sha256": context["source_manifest_sha256"],
            "checkpoint_sha256": context["checkpoint_sha256"],
        },
        "selection": {
            "modes": [case.mode],
            "anchor_count_requested": case.anchor_count or 1,
            "full_step_cohort": case.full_step_cohort,
            "max_step": runner.MAX_STEP,
            "world": 123,
            "step": 1,
            "rows_by_mode": {case.mode: rows},
        },
        "timing": {
            "strict_unit_timeout_s": round(timeout_s, 6),
            "modes": {
                case.mode: {
                    "selected_rows": len(rows),
                    "selected_unique_anchors": len(
                        {row["anchor_sha256"] for row in rows}
                    ),
                    "full_route_rows": len(rows),
                    "elapsed_s": 0.01,
                    "dataset_rows_verified_in_memory": len(rows),
                    "bindings_verified_in_memory": len(rows),
                }
            },
        },
        "guards": runner._guards(),
    }


def _write_pass_receipt(fixture: dict[str, Path], tmp_path: Path, case: runner.BenchmarkCase):
    context, snapshot = _context(fixture)
    inputs = runner._receipt_inputs(
        context=context,
        snapshot=snapshot,
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        source_manifest=fixture["source_manifest"],
    )
    timeout_s = 1.0
    payload = runner._pass_receipt(
        case=case,
        timeout_s=timeout_s,
        external_timeout_s=timeout_s + runner.EXTERNAL_GRACE_S,
        inputs=inputs,
        benchmark_payload=_benchmark_payload(
            fixture, case, context, snapshot, timeout_s
        ),
        elapsed_s=0.01,
    )
    path = tmp_path / f"{case.name}.json"
    runner._write_receipt(path, payload)
    return path


def test_case_matrix_is_exactly_two_modes_by_three_levels() -> None:
    assert [(case.mode, case.level) for case in runner.benchmark_cases()] == [
        (mode, level) for mode in runner.MODES for level in runner.LEVELS
    ]


def test_short_benchmark_context_requires_current_ops3_and_rejects_legacy_binding(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    payload = json.loads(fixture["code_manifest"].read_text(encoding="ascii"))
    payload["bindings"] = [
        row for row in payload["bindings"] if row["role"] != "runtime_ops3_producer"
    ]
    fixture["code_manifest"].write_bytes(runner._canonical(payload))
    fixture["code_manifest_digest"].write_text(
        f"{runner._sha(fixture['code_manifest'])}  CODE-MANIFEST.json\n",
        encoding="ascii",
    )
    with pytest.raises(runner.ShortBenchmarkError, match="runtime_ops3_producer"):
        runner._load_code_context(
            fixture["code_manifest"], fixture["code_manifest_digest"]
        )

    fixture = _fixture(tmp_path / "legacy")
    payload = json.loads(fixture["code_manifest"].read_text(encoding="ascii"))
    payload["bindings"].append(
        {
            "role": "legacy_temporal",
            "path": ".scratch/c2-v03/c2_temporal_fork_core.py",
            "sha256": "0" * 64,
        }
    )
    fixture["code_manifest"].write_bytes(runner._canonical(payload))
    fixture["code_manifest_digest"].write_text(
        f"{runner._sha(fixture['code_manifest'])}  CODE-MANIFEST.json\n",
        encoding="ascii",
    )
    with pytest.raises(runner.ShortBenchmarkError, match="legacy Temporal-Fork"):
        runner._load_code_context(
            fixture["code_manifest"], fixture["code_manifest_digest"]
        )
    assert [case.anchor_count for case in runner.benchmark_cases()[:3]] == [1, 2, None]


def test_receipt_validator_binds_current_hashes_and_guards(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    case = runner.benchmark_cases()[0]
    receipt_path = _write_pass_receipt(fixture, tmp_path, case)

    payload = runner.validate_receipt(
        receipt_path,
        case=case,
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        source_manifest=fixture["source_manifest"],
        code_manifest=fixture["code_manifest"],
        code_manifest_digest=fixture["code_manifest_digest"],
        timeout_s=1.0,
    )
    assert payload["status"] == "SHORT_BENCHMARK_PASS"


def test_receipt_validator_rejects_capture_hash_drift(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    case = runner.benchmark_cases()[0]
    receipt_path = _write_pass_receipt(fixture, tmp_path, case)
    fixture["capture"].write_bytes(b"drifted\n")

    with pytest.raises(runner.ShortBenchmarkError, match="input hash/path drifted"):
        runner.validate_receipt(
            receipt_path,
            case=case,
            capture_path=fixture["capture"],
            materialization_dir=fixture["materialization"],
            source_manifest=fixture["source_manifest"],
            code_manifest=fixture["code_manifest"],
            code_manifest_digest=fixture["code_manifest_digest"],
            timeout_s=1.0,
        )


def test_receipt_validator_rejects_code_manifest_drift(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    case = runner.benchmark_cases()[0]
    receipt_path = _write_pass_receipt(fixture, tmp_path, case)
    code = json.loads(fixture["code_manifest"].read_text(encoding="ascii"))
    code["drift"] = True
    fixture["code_manifest"].write_bytes(runner._canonical(code))
    fixture["code_manifest_digest"].write_text(
        f"{runner._sha(fixture['code_manifest'])}  CODE-MANIFEST.json\n",
        encoding="ascii",
    )

    with pytest.raises(runner.ShortBenchmarkError, match="input hash/path drifted"):
        runner.validate_receipt(
            receipt_path,
            case=case,
            capture_path=fixture["capture"],
            materialization_dir=fixture["materialization"],
            source_manifest=fixture["source_manifest"],
            code_manifest=fixture["code_manifest"],
            code_manifest_digest=fixture["code_manifest_digest"],
            timeout_s=1.0,
        )


def test_receipt_validator_rejects_materialization_closure_drift(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    case = runner.benchmark_cases()[0]
    receipt_path = _write_pass_receipt(fixture, tmp_path, case)
    (fixture["materialization"] / "unexpected.json").write_bytes(b"drifted\n")

    with pytest.raises(runner.ShortBenchmarkError, match="closure drifted"):
        runner.validate_receipt(
            receipt_path,
            case=case,
            capture_path=fixture["capture"],
            materialization_dir=fixture["materialization"],
            source_manifest=fixture["source_manifest"],
            code_manifest=fixture["code_manifest"],
            code_manifest_digest=fixture["code_manifest_digest"],
            timeout_s=1.0,
        )


def test_validate_all_rejects_extra_symlink_or_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = _fixture(tmp_path)
    output = tmp_path / "short-receipts"
    context, snapshot = _context(fixture)

    def fake_process(command, *, env, cwd, timeout_s):
        mode = command[command.index("--mode") + 1]
        if "--full-step-cohort" in command:
            level = "full-step"
        else:
            count = int(command[command.index("--anchor-count") + 1])
            level = "single" if count == 1 else "double"
        case = next(
            item
            for item in runner.benchmark_cases()
            if item.mode == mode and item.level == level
        )
        payload = _benchmark_payload(fixture, case, context, snapshot, 1.0)
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps(payload).encode("ascii"), stderr=b""
        )

    monkeypatch.setattr(runner, "_run_process", fake_process)
    summary = runner.run_all(
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
        source_manifest=fixture["source_manifest"],
        source_manifest_digest=fixture["source_digest"],
        execution_addendum=tmp_path / "addendum.md",
        code_manifest=fixture["code_manifest"],
        code_manifest_digest=fixture["code_manifest_digest"],
        output=output,
        python=Path(sys.executable),
        timeout_s=1.0,
    )
    assert summary["status"] == "SHORT_BENCHMARKS_PASS"
    (output / "unexpected").mkdir()
    with pytest.raises(runner.ShortBenchmarkError, match="non-regular entry"):
        runner.validate_all(
            output,
            capture_path=fixture["capture"],
            materialization_dir=fixture["materialization"],
            source_manifest=fixture["source_manifest"],
            code_manifest=fixture["code_manifest"],
            code_manifest_digest=fixture["code_manifest_digest"],
            timeout_s=1.0,
        )


def test_timeout_is_strictly_below_600_seconds() -> None:
    with pytest.raises(runner.ShortBenchmarkError, match="strictly between"):
        runner._validate_timeout(600.0)
    with pytest.raises(runner.ShortBenchmarkError, match="finite"):
        runner._validate_timeout(float("nan"))


def test_runner_writes_six_independent_pass_receipts_without_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = _fixture(tmp_path)
    output = tmp_path / "short-receipts"
    context, snapshot = _context(fixture)

    def fake_process(command, *, env, cwd, timeout_s):
        mode = command[command.index("--mode") + 1]
        if "--full-step-cohort" in command:
            level = "full-step"
        else:
            count = int(command[command.index("--anchor-count") + 1])
            level = "single" if count == 1 else "double"
        case = next(
            item
            for item in runner.benchmark_cases()
            if item.mode == mode and item.level == level
        )
        payload = _benchmark_payload(fixture, case, context, snapshot, 1.0)
        return subprocess.CompletedProcess(
            command, 0, stdout=json.dumps(payload).encode("ascii"), stderr=b""
        )

    monkeypatch.setattr(runner, "_run_process", fake_process)
    summary = runner.run_all(
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
        source_manifest=fixture["source_manifest"],
        source_manifest_digest=fixture["source_digest"],
        execution_addendum=tmp_path / "addendum.md",
        code_manifest=fixture["code_manifest"],
        code_manifest_digest=fixture["code_manifest_digest"],
        output=output,
        python=Path(sys.executable),
        timeout_s=1.0,
    )
    assert summary["status"] == "SHORT_BENCHMARKS_PASS"
    assert sorted(path.name for path in output.glob("*.json")) == sorted(
        ["SUMMARY.json"] + [f"{case.name}.json" for case in runner.benchmark_cases()]
    )
    runner.validate_all(
        output,
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        source_manifest=fixture["source_manifest"],
        code_manifest=fixture["code_manifest"],
        code_manifest_digest=fixture["code_manifest_digest"],
        timeout_s=1.0,
    )
    assert runner.main(
        [
            "--capture",
            str(fixture["capture"]),
            "--materialization-dir",
            str(fixture["materialization"]),
            "--tle-root",
            str(tmp_path / "tle"),
            "--prereg",
            str(tmp_path / "prereg.json"),
            "--manifest",
            str(fixture["source_manifest"]),
            "--manifest-digest",
            str(fixture["source_digest"]),
            "--execution-addendum",
            str(tmp_path / "addendum.md"),
            "--code-manifest",
            str(fixture["code_manifest"]),
            "--code-manifest-digest",
            str(fixture["code_manifest_digest"]),
            "--output",
            str(output),
            "--timeout-s",
            "1",
            "--validate",
        ]
    ) == 0


def test_runner_records_failed_case_and_blocks_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = _fixture(tmp_path)
    output = tmp_path / "failed-short-receipts"

    def fake_process(command, *, env, cwd, timeout_s):
        return subprocess.CompletedProcess(command, 7, stdout=b"", stderr=b"probe failed")

    monkeypatch.setattr(runner, "_run_process", fake_process)
    summary = runner.run_all(
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
        source_manifest=fixture["source_manifest"],
        source_manifest_digest=fixture["source_digest"],
        execution_addendum=tmp_path / "addendum.md",
        code_manifest=fixture["code_manifest"],
        code_manifest_digest=fixture["code_manifest_digest"],
        output=output,
        python=Path(sys.executable),
        timeout_s=1.0,
    )
    assert summary["status"] == "SHORT_BENCHMARKS_FAILED"
    first = json.loads(
        (output / f"{runner.benchmark_cases()[0].name}.json").read_text(encoding="ascii")
    )
    assert first["status"] == "SHORT_BENCHMARK_FAILED"
    assert first["error"]["message"].endswith("probe failed")
    assert (output / "SUMMARY.json").is_file()


def test_mode_world_status_events_are_independent_and_write_once(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    started = controller._write_shard_status(
        staging,
        "informed:10",
        event="started",
        state="RUNNING",
        output="informed/world-10",
    )
    terminal = controller._write_shard_status(
        staging,
        "informed:10",
        event="terminal",
        state="FAILED",
        returncode=7,
        error="synthetic failure",
    )
    assert started.name == "informed-world-10.started.json"
    assert terminal.name == "informed-world-10.terminal.json"
    assert json.loads(started.read_text(encoding="ascii"))["state"] == "RUNNING"
    assert json.loads(terminal.read_text(encoding="ascii"))["state"] == "FAILED"
    with pytest.raises(controller.ControllerError, match="overwrite"):
        controller._write_shard_status(
            staging,
            "informed:10",
            event="terminal",
            state="PASS",
        )


def test_controller_records_pass_and_queued_blocked_shards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schedule = {
        "informed:10": {"mode": "informed", "world": 10, "C1": [], "C2": [{}]},
        "neutral:10": {"mode": "neutral", "world": 10, "C1": [], "C2": [{}]},
    }

    class FakeProcess:
        def __init__(self, command, **_kwargs):
            self.returncode = 0
            output = Path(command[command.index("--output") + 1])
            output.mkdir(parents=True)
            (output / "receipt.json").write_bytes(b"receipt")
            (output / "MANIFEST.sha256").write_bytes(b"manifest")

        def poll(self):
            return self.returncode

        def wait(self):
            return self.returncode

        def terminate(self):
            self.returncode = -15

    monkeypatch.setattr(controller, "_expected_schedule", lambda _args: schedule)
    monkeypatch.setattr(controller.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(controller, "_read_receipt", lambda _root: {"status": "PASS"})
    monkeypatch.setattr(controller, "_validate_shard", lambda *_args: None)
    monkeypatch.setattr(controller, "_merge", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        controller.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    staging = tmp_path / "staging"
    output = tmp_path / "output"
    args = SimpleNamespace(
        output=output,
        staging=staging,
        capture=tmp_path / "capture",
        materialization_dir=tmp_path / "materialized",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg",
        manifest=tmp_path / "manifest",
        manifest_digest=tmp_path / "manifest.sha256",
        execution_addendum=tmp_path / "addendum",
        python=Path(sys.executable),
        users=100,
        max_workers=1,
    )

    assert controller.run(args) == 0
    status_files = sorted((staging / "shard-status").glob("*.json"))
    assert [path.name for path in status_files] == [
        "informed-world-10.started.json",
        "informed-world-10.terminal.json",
        "neutral-world-10.started.json",
        "neutral-world-10.terminal.json",
    ]
    assert json.loads(status_files[1].read_text(encoding="ascii"))["state"] == "PASS"
    assert json.loads(status_files[3].read_text(encoding="ascii"))["state"] == "PASS"


def test_controller_records_failure_and_queued_shards_without_merging(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schedule = {
        "informed:10": {"mode": "informed", "world": 10, "C1": [], "C2": [{}]},
        "neutral:10": {"mode": "neutral", "world": 10, "C1": [], "C2": [{}]},
    }

    class FailingProcess:
        def __init__(self, _command, **_kwargs):
            self.returncode = 9

        def poll(self):
            return self.returncode

        def wait(self):
            return self.returncode

        def terminate(self):
            self.returncode = -15

    merge_called = False

    def fail_if_merged(*_args, **_kwargs):
        nonlocal merge_called
        merge_called = True

    monkeypatch.setattr(controller, "_expected_schedule", lambda _args: schedule)
    monkeypatch.setattr(controller.subprocess, "Popen", FailingProcess)
    monkeypatch.setattr(controller, "_merge", fail_if_merged)
    staging = tmp_path / "staging"
    output = tmp_path / "output"
    args = SimpleNamespace(
        output=output,
        staging=staging,
        capture=tmp_path / "capture",
        materialization_dir=tmp_path / "materialized",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg",
        manifest=tmp_path / "manifest",
        manifest_digest=tmp_path / "manifest.sha256",
        execution_addendum=tmp_path / "addendum",
        python=Path(sys.executable),
        users=100,
        max_workers=1,
    )

    assert controller.run(args) == 2
    assert not merge_called
    terminal = {
        path.name: json.loads(path.read_text(encoding="ascii"))["state"]
        for path in (staging / "shard-status").glob("*.terminal.json")
    }
    assert terminal == {
        "informed-world-10.terminal.json": "FAILED",
        "neutral-world-10.terminal.json": "BLOCKED",
    }
    assert (output / "FAILED").is_file()


# --- 2026-09-07 scope-literal alignment (execution-contract correction only) ---
#
# The r4 single-anchor receipt failed with "short benchmark scope drifted"
# because the wrapper still expected the pre-OPS-3 wording while the frozen
# producer emits the more precise repriced OPS-3 selected-pair wording.  The
# wrapper literal was aligned to the producer; the producer, formula, data,
# selection, and claim ceiling were not touched.

PRODUCER_SCOPE_LITERAL = (
    "C2 repriced OPS-3 selected-pair generation only; "
    "no C1 timing, learner, TEST, or efficacy claim"
)
PREVIOUS_WRAPPER_SCOPE_LITERAL = (
    "C2 physical target generation only; no C1 timing, learner, TEST, or efficacy claim"
)


def _validate_payload_scope(tmp_path: Path, scope: object) -> None:
    fixture = _fixture(tmp_path)
    case = runner.benchmark_cases()[0]
    context, snapshot = _context(fixture)
    payload = _benchmark_payload(fixture, case, context, snapshot, 1.0)
    payload["scope"] = scope
    runner._validate_benchmark_payload(
        payload,
        case=case,
        context=context,
        snapshot=snapshot,
        capture_path=fixture["capture"],
        materialization_dir=fixture["materialization"],
        timeout_s=1.0,
    )


def test_wrapper_accepts_exact_frozen_producer_scope_literal(tmp_path: Path) -> None:
    # Positive: the literal is taken from the frozen producer source itself, so
    # this test fails if either side drifts away from the other again.
    producer_source = runner.BENCHMARK.read_text(encoding="utf-8")
    assert producer_source.count(f'"scope": "{PRODUCER_SCOPE_LITERAL}"') == 1
    assert PREVIOUS_WRAPPER_SCOPE_LITERAL not in producer_source
    _validate_payload_scope(tmp_path, PRODUCER_SCOPE_LITERAL)


@pytest.mark.parametrize(
    "scope",
    [
        PREVIOUS_WRAPPER_SCOPE_LITERAL,
        PRODUCER_SCOPE_LITERAL.replace("TEST, ", ""),
        PRODUCER_SCOPE_LITERAL.replace("no C1 timing, ", ""),
        PRODUCER_SCOPE_LITERAL.replace(" or efficacy claim", ""),
        PRODUCER_SCOPE_LITERAL + " ",
        PRODUCER_SCOPE_LITERAL.lower(),
        "C2 repriced OPS-3 selected-pair generation and learner update",
        "",
        None,
    ],
)
def test_wrapper_rejects_any_other_scope_literal(tmp_path: Path, scope: object) -> None:
    # Mutation-negative: the previous wording and every genuinely different
    # scope (dropped disclaimer, added claim, case/whitespace change, empty,
    # missing) still fail closed with the same drift error.
    with pytest.raises(runner.ShortBenchmarkError, match="scope drifted"):
        _validate_payload_scope(tmp_path, scope)
