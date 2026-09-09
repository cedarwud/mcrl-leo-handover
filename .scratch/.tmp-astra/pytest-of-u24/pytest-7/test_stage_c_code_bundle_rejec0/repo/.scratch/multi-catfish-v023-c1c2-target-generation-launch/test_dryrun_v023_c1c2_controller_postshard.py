from __future__ import annotations

import hashlib
import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


dryrun = _load(
    "mcrl_v023_c1c2_postshard_dryrun_test_module",
    HERE / "dryrun_v023_c1c2_controller_postshard.py",
)
controller = dryrun._load_controller(REPO)
generator = controller._load_generator()
target_batch_test = _load(
    "mcrl_v023_c1c2_postshard_target_batch_fixture",
    REPO
    / ".scratch"
    / "multi-catfish-v023-target-batch-adapter"
    / "test_target_batch_adapter.py",
)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _schedule() -> dict[str, dict[str, object]]:
    schedule: dict[str, dict[str, object]] = {}
    for mode in ("informed", "neutral"):
        for world in range(1000, 1008):
            key = f"{mode}:{world}"
            schedule[key] = {
                "mode": mode,
                "world": world,
                "C1": [
                    {
                        "source_anchor_sha256": _digest(f"anchor-{key}"),
                        "source_record_sha256": _digest(f"record-{key}"),
                        "source_seed": world,
                        "world": world,
                        "step_index": 1,
                        "focal_user": 0,
                        "reference_action": 0,
                        "candidate_action": 1,
                        "candidate_physical_key": [501, 1],
                        "source_rule": f"fixture-{mode}",
                    }
                ],
                "C2": [],
            }
    return schedule


def _write_generator_shard(
    root: Path,
    key: str,
    entry: dict[str, object],
) -> None:
    mode = str(entry["mode"])
    world = int(entry["world"])
    dataset = target_batch_test._c1_dataset(mode=mode, world=world)
    identity = dict(entry["C1"][0])
    binding = {
        **identity,
        "mode": mode,
        "common_random_field_sha256": _digest(f"field-{key}"),
        "comparison_sha256": _digest(f"comparison-{key}"),
    }
    sealed = SimpleNamespace(
        capture_path=Path("/authority/panel-capture.json"),
        capture_sha256=_digest("capture"),
        materialization_dir=Path("/authority/materialized-source"),
        materialization_manifest_sha256=_digest("materialization"),
        pool_sha256=_digest("pool"),
        source_manifest_sha256=dataset.source_manifest_sha256,
        checkpoint_sha256=dataset.checkpoint_sha256,
    )
    ctx = SimpleNamespace(
        modules=SimpleNamespace(
            opening_dataset=SimpleNamespace(
                write_opening_dataset=target_batch_test.write_opening_dataset
            )
        ),
        source_family="fixture-source-family",
        lambda_bits_per_j=2.0,
        kappa_bits=3.0,
        interval_s=1.0,
    )
    generator._write_outputs(
        root,
        sealed=sealed,
        ctx=ctx,
        schedule={key: entry},
        c1_datasets={(mode, world): dataset},
        c2_datasets={},
        c1_bindings=(binding,),
        c2_bindings=(),
    )


def _tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        if path.is_symlink():
            kind = b"L"
            content = str(path.readlink()).encode("utf-8")
        elif path.is_dir():
            kind = b"D"
            content = b""
        else:
            kind = b"F"
            content = path.read_bytes()
        digest.update(kind + b"\0" + relative + b"\0" + content + b"\0")
    return digest.hexdigest()


def _args(tmp_path: Path, staging: Path, output: Path) -> SimpleNamespace:
    return SimpleNamespace(
        staging=staging,
        output=output,
        repo=REPO,
        capture=tmp_path / "capture.json",
        materialization_dir=tmp_path / "materialized-source",
        tle_root=tmp_path / "tle",
        prereg=tmp_path / "prereg.json",
        manifest=tmp_path / "manifest.json",
        manifest_digest=tmp_path / "manifest.sha256",
        execution_addendum=tmp_path / "execution-addendum.md",
        python=REPO / ".venv/bin/python",
        users=100,
    )


def test_two_real_generator_shards_authenticate_then_block_on_14_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = _schedule()
    staging = tmp_path / "staging"
    for key in ("informed:1000", "neutral:1000"):
        mode, world = key.split(":", 1)
        _write_generator_shard(
            staging / mode / f"world-{world}", key, schedule[key]
        )
    before = _tree_sha256(staging)
    output = tmp_path / "dryrun-output"
    monkeypatch.setattr(dryrun, "_load_controller", lambda _repo: controller)
    monkeypatch.setattr(controller, "_expected_schedule", lambda _args: schedule)

    assert dryrun.run(_args(tmp_path, staging, output)) == 3

    assert _tree_sha256(staging) == before
    report = json.loads((output / dryrun.REPORT_NAME).read_text(encoding="ascii"))
    assert report["summary"] == {
        "verdict": "BLOCKED",
        "scheduled_shards": 16,
        "present_shards": 2,
        "passed_shards": 2,
        "failed_shards": 0,
        "missing_shards": 14,
    }
    assert report["findings"][-1]["status"] == "BLOCKED_MISSING_SHARDS"
    assert not any(path.name == "COMPLETE" for path in staging.rglob("*"))
    assert capsys.readouterr().out.strip() == (
        "DRYRUN_C1C2_POSTSHARD_BLOCKED "
        "scheduled=16 present=2 passed=2 failed=0 missing=14"
    )


def test_complete_generator_schedule_reaches_and_passes_sealer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = _schedule()
    staging = tmp_path / "staging"
    for key, entry in schedule.items():
        mode, world = key.split(":", 1)
        _write_generator_shard(
            staging / mode / f"world-{world}", key, entry
        )
    before = _tree_sha256(staging)
    output = tmp_path / "dryrun-output"
    monkeypatch.setattr(dryrun, "_load_controller", lambda _repo: controller)
    monkeypatch.setattr(controller, "_expected_schedule", lambda _args: schedule)

    assert dryrun.run(_args(tmp_path, staging, output)) == 0

    assert _tree_sha256(staging) == before
    report = json.loads((output / dryrun.REPORT_NAME).read_text(encoding="ascii"))
    assert report["summary"] == {
        "verdict": "PASS",
        "scheduled_shards": 16,
        "present_shards": 16,
        "passed_shards": 16,
        "failed_shards": 0,
        "missing_shards": 0,
    }
    assert report["findings"][-1]["status"] == "PASS"
    merged = output / "merged-output"
    assert (merged / "COMPLETE").is_file()
    receipt = json.loads((merged / "receipt.json").read_text(encoding="ascii"))
    assert receipt["claim_ceiling"] == generator.CLAIM_CEILING
    assert capsys.readouterr().out.strip() == (
        "DRYRUN_C1C2_POSTSHARD_PASS "
        "scheduled=16 present=16 passed=16 failed=0 missing=0"
    )


def test_tampered_receipt_reports_exact_controller_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    schedule = _schedule()
    staging = tmp_path / "staging"
    key = "informed:1000"
    shard = staging / "informed" / "world-1000"
    _write_generator_shard(shard, key, schedule[key])
    receipt_path = shard / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="ascii"))
    receipt["claim_ceiling"] = (
        "TRAIN_PHYSICAL_TARGET_GENERATION_ONLY_NO_LEARNER_"
        "NO_EPISODE_TRAINING_NO_TEST"
    )
    receipt_path.write_bytes(controller._canonical(receipt))
    before = _tree_sha256(staging)
    output = tmp_path / "dryrun-output"
    monkeypatch.setattr(dryrun, "_load_controller", lambda _repo: controller)
    monkeypatch.setattr(controller, "_expected_schedule", lambda _args: schedule)

    assert dryrun.run(_args(tmp_path, staging, output)) == 2

    assert _tree_sha256(staging) == before
    report = json.loads((output / dryrun.REPORT_NAME).read_text(encoding="ascii"))
    failure = next(
        finding
        for finding in report["findings"]
        if finding["phase"] == "shard_authentication"
    )
    assert failure["status"] == "FAIL"
    assert failure["message"] == "mode receipt claim ceiling drifted"
    assert report["summary"]["failed_shards"] == 1
    assert capsys.readouterr().out.startswith("DRYRUN_C1C2_POSTSHARD_FAIL ")
