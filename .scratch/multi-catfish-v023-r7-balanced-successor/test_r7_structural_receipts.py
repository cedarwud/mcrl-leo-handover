"""Cheap R7 source/fit receipt structure tests; no physical or learner work."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MANIFEST = HERE / "R7-PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST = HERE / "R7-PREFLIGHT-MANIFEST.sha256"
ZERO_SHA = "0" * 64
ONE_SHA = "1" * 64


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


preflight = _load("r7_structural_preflight", "preflight_r7_balanced.py")
runner = _load("r7_structural_runner", "run_v023_lcsrs_observability_gate.py")
verifier = _load("r7_structural_verifier", "verify_v023_lcsrs_observability_gate.py")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _source_payload(world: int, preflight_sha256: str) -> dict[str, object]:
    return {
        "schema": runner.SOURCE_SCHEMA,
        "status": "PASS",
        "claim_ceiling": runner.CLAIM_CEILING,
        "contract_sha256": runner.CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "split": "TRAIN_DEVELOPMENT",
        "world": world,
        "enumeration_sha256": ZERO_SHA,
        "topology_sha256": ZERO_SHA,
        "teacher_sha256": ZERO_SHA,
        "surface_sha256": ZERO_SHA,
        "record_count": 1,
        "pair_count": 1,
        "supported_count": 2,
        "placebo_eligible_count": 2,
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
    }


def _fit_payload(
    world: int,
    seed: int,
    arm: str,
    source_sha256: str,
    preflight_sha256: str,
) -> dict[str, object]:
    return {
        "schema": runner.FIT_SCHEMA,
        "status": "PASS",
        "claim_ceiling": runner.CLAIM_CEILING,
        "contract_sha256": runner.CONTRACT_SHA256,
        "preflight_manifest_sha256": preflight_sha256,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": world,
        "student_seed": seed,
        "arm": arm,
        "source_manifest_sha256": source_sha256,
        "update_count": runner.FIT_UPDATES,
        "model_sha256": ONE_SHA,
        "metrics_sha256": ONE_SHA,
        "test_worlds": [],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": True,
    }


def test_no_launch_preflight_rejects_a_missing_r7_decision_binding(
    tmp_path: Path,
) -> None:
    receipt = preflight.validate_manifest(
        MANIFEST,
        manifest_digest_path=MANIFEST_DIGEST,
        repo=REPO,
    )
    assert receipt["status"] == "PASS_NO_LAUNCH_PREFLIGHT"
    assert receipt["manifest_status"] == "DRAFT_PRE_OUTCOME"
    assert receipt["launch"] == "NO_LAUNCH"

    payload = json.loads(MANIFEST.read_text(encoding="ascii"))
    payload["bindings"] = [
        entry for entry in payload["bindings"] if entry["role"] != "r7_decision"
    ]
    tampered = tmp_path / "R7-PREFLIGHT-MANIFEST.json"
    sidecar = tmp_path / "R7-PREFLIGHT-MANIFEST.sha256"
    tampered.write_bytes(_canonical(payload) + b"\n")
    sidecar.write_text(
        f"{hashlib.sha256(tampered.read_bytes()).hexdigest()}  {tampered.name}\n",
        encoding="ascii",
    )
    with pytest.raises(preflight.R7PreflightError, match="r7_decision"):
        preflight.validate_manifest(
            tampered,
            manifest_digest_path=sidecar,
            repo=REPO,
        )


def test_plan_contains_only_the_fresh_r7_schedule_and_is_write_once(
    tmp_path: Path,
) -> None:
    output = tmp_path / "plan.json"
    payload = runner.emit_plan(output)
    report = verifier.verify_file(output, kind="plan")
    assert report["status"] == "PASS_STRUCTURAL_PLAN"
    assert {item["world"] for item in payload["source_shards"]} == set(runner.WORLDS)
    assert {
        item["student_seed"] for item in payload["fit_shards"]
    } == set(runner.STUDENT_SEEDS)
    assert len(payload["source_shards"]) == 8
    assert len(payload["fit_shards"]) == 48
    with pytest.raises(runner.V023GateError, match="overwrite"):
        runner.emit_plan(output)


def test_synthetic_source_fit_merge_receipt_closure(tmp_path: Path) -> None:
    preflight_sha256 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    for world in runner.WORLDS:
        runner.write_source_shard(
            runner.SourceShardSpec(
                world,
                tmp_path / "source" / f"world-{world}.json",
            ),
            payload=_source_payload(world, preflight_sha256),
            preflight_sha256=preflight_sha256,
        )
    source_manifest_path = tmp_path / "source-manifest.json"
    source_manifest = runner.emit_source_manifest(
        source_directory=tmp_path,
        output=source_manifest_path,
        preflight_sha256=preflight_sha256,
    )
    source_sha256 = source_manifest["source_manifest_sha256"]

    for world in runner.WORLDS:
        for seed in runner.STUDENT_SEEDS:
            for arm in runner.ARMS:
                runner.write_fit_shard(
                    runner.FitShardSpec(
                        world,
                        seed,
                        arm,
                        tmp_path,
                        tmp_path
                        / "fit"
                        / f"world-{world}"
                        / f"seed-{seed}"
                        / f"{arm.lower()}.json",
                        source_manifest=source_manifest_path,
                    ),
                    payload=_fit_payload(
                        world,
                        seed,
                        arm,
                        source_sha256,
                        preflight_sha256,
                    ),
                    preflight_sha256=preflight_sha256,
                    source_manifest_sha256=source_sha256,
                )

    merge_path = tmp_path / "merge.json"
    merged = runner.merge_shards(
        source_directory=tmp_path,
        fit_directory=tmp_path,
        source_manifest=source_manifest_path,
        output=merge_path,
        preflight_sha256=preflight_sha256,
    )
    report = verifier.verify_file(
        merge_path,
        kind="merge",
        source_root=tmp_path,
        fit_root=tmp_path,
    )
    assert report["status"] == "PASS_STRUCTURAL_MERGE"
    assert merged["decision"] is None
    assert len(merged["source_shards"]) == 8
    assert len(merged["fit_shards"]) == 48


def test_importable_source_adapter_seam_does_not_enable_the_safe_cli(
    tmp_path: Path,
) -> None:
    preflight_sha256 = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

    class SourceAdapter:
        def generate_source_shard(self, spec):
            return _source_payload(spec.world, preflight_sha256)

    output = tmp_path / "source" / f"world-{runner.WORLDS[0]}.json"
    assert runner.run_source_stage(
        runner.SourceShardSpec(
            runner.WORLDS[0],
            output,
            preflight_manifest_sha256=preflight_sha256,
        ),
        adapter=SourceAdapter(),
    ) == output
    with pytest.raises(runner.V023GateError, match="no physical adapter"):
        runner.run_source_stage(
            runner.SourceShardSpec(runner.WORLDS[0], tmp_path / "closed.json"),
            adapter=None,
        )

