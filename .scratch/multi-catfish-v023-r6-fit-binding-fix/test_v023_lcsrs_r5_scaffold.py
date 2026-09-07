"""Cheap structural tests for the V0.23 staged gate scaffold.

These tests intentionally use synthetic receipts only.  They never construct a
simulator, read TLE data, fit a learner, or open TEST.  The purpose is to keep
the shard/manifest boundaries executable before a separately authorized
server run.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


preflight = _load("v023_test_preflight", HERE / "preflight_v023_lcsrs_r6.py")
runner = _load("v023_test_runner", HERE / "run_v023_lcsrs_observability_gate.py")
verifier = _load("v023_test_verifier", HERE / "verify_v023_lcsrs_observability_gate.py")


MANIFEST = HERE / "PREFLIGHT-MANIFEST.json"
MANIFEST_DIGEST = HERE / "PREFLIGHT-MANIFEST.sha256"
SYNC_LAUNCHER = HERE / "sync_launch_v023_lcsrs_gate_server_r6.sh"
PREFLIGHT_SHA256 = preflight.file_sha256(MANIFEST)
ZERO_SHA = "0" * 64
ONE_SHA = "1" * 64


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(payload))


def _source_payload(world: int) -> dict[str, object]:
    return {
        "schema": runner.SOURCE_SCHEMA,
        "status": "PASS",
        "claim_ceiling": runner.CLAIM_CEILING,
        "contract_sha256": runner.CONTRACT_SHA256,
        "preflight_manifest_sha256": PREFLIGHT_SHA256,
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


def _fit_payload(world: int, seed: int, arm: str, source_sha: str) -> dict[str, object]:
    return {
        "schema": runner.FIT_SCHEMA,
        "status": "PASS",
        "claim_ceiling": runner.CLAIM_CEILING,
        "contract_sha256": runner.CONTRACT_SHA256,
        "preflight_manifest_sha256": PREFLIGHT_SHA256,
        "split": "TRAIN_DEVELOPMENT",
        "held_out_world": world,
        "student_seed": seed,
        "arm": arm,
        "source_manifest_sha256": source_sha,
        "update_count": runner.FIT_UPDATES,
        "model_sha256": ONE_SHA,
        "metrics_sha256": ONE_SHA,
        "test_worlds": [],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": True,
    }


def test_preflight_passes_and_missing_binding_fails(tmp_path: Path) -> None:
    receipt = preflight.validate_manifest(
        MANIFEST,
        manifest_digest_path=MANIFEST_DIGEST,
        repo=REPO,
        prereg_path=REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
    )
    assert receipt["status"] == "PASS"
    roles = {entry["role"] for entry in receipt["bindings"]}
    assert "defect_decision_r6" in roles
    assert "relaunch_decision_r4" not in roles
    assert "relaunch_decision_r3" not in roles
    assert "relaunch_decision_r2" not in roles

    tampered = json.loads(MANIFEST.read_text(encoding="ascii"))
    tampered["bindings"] = [
        item
        for item in tampered["bindings"]
        if item["role"] != "runtime_observation_provenance"
    ]
    tampered_manifest = tmp_path / "PREFLIGHT-MANIFEST.json"
    tampered_digest = tmp_path / "PREFLIGHT-MANIFEST.sha256"
    _write_json(tampered_manifest, tampered)
    tampered_digest.write_text(
        f"{hashlib.sha256(tampered_manifest.read_bytes()).hexdigest()}  PREFLIGHT-MANIFEST.json\n",
        encoding="ascii",
    )
    with pytest.raises(preflight.V023PreflightError, match="runtime_observation_provenance"):
        preflight.validate_manifest(
            tampered_manifest,
            manifest_digest_path=tampered_digest,
            repo=REPO,
        )


def test_every_manifest_binding_is_in_the_fresh_server_sync_closure() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="ascii"))
    launcher = SYNC_LAUNCHER.read_text(encoding="utf-8")
    sync_block = launcher.split("sync_paths=(", 1)[1].split("\n)", 1)[0]
    synced_paths = {
        line.strip()
        for line in sync_block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    manifest_paths = {entry["path"] for entry in payload["bindings"]}

    def is_synced(path: str) -> bool:
        for synced in synced_paths:
            if path == synced:
                return True
            if (REPO / synced).is_dir() and path.startswith(synced.rstrip("/") + "/"):
                return True
        return False

    missing = sorted(path for path in manifest_paths if not is_synced(path))
    assert not missing, missing


def test_historical_path_regression_suite_is_in_server_sync_closure() -> None:
    """W196--W205 load the original scaffold paths in an isolated checkout."""

    launcher = SYNC_LAUNCHER.read_text(encoding="utf-8")
    sync_block = launcher.split("sync_paths=(", 1)[1].split("\n)", 1)[0]
    compatibility = ".scratch/multi-catfish-v023-c3-observability"
    assert compatibility in {
        line.strip()
        for line in sync_block.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    for filename in (
        "v023_lcsrs_fit_adapter.py",
        "v023_lcsrs_composition_adapter.py",
        "verify_v023_lcsrs_scientific.py",
        "verify_v023_lcsrs_fit_independent.py",
        "verify_v023_lcsrs_final.py",
    ):
        assert (REPO / compatibility / filename).read_bytes() == (HERE / filename).read_bytes()


def test_preflight_freezes_full_learner_config_and_each_initial_digest(
    tmp_path: Path,
) -> None:
    baseline = json.loads(MANIFEST.read_text(encoding="ascii"))
    assert baseline["configuration"]["learner"] == preflight.EXPECTED_LEARNER

    for field, replacement in (
        ("updates", 1999),
        ("learning_rate", 0.002),
        ("config_sha256", ZERO_SHA),
    ):
        tampered = json.loads(MANIFEST.read_text(encoding="ascii"))
        tampered["configuration"]["learner"][field] = replacement
        manifest = tmp_path / field / "PREFLIGHT-MANIFEST.json"
        digest = tmp_path / field / "PREFLIGHT-MANIFEST.sha256"
        _write_json(manifest, tampered)
        digest.write_text(
            f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  PREFLIGHT-MANIFEST.json\n",
            encoding="ascii",
        )
        with pytest.raises(preflight.V023PreflightError, match="initial parameter"):
            preflight.validate_manifest(
                manifest,
                manifest_digest_path=digest,
                repo=REPO,
            )

    tampered = json.loads(MANIFEST.read_text(encoding="ascii"))
    tampered["configuration"]["learner"]["initial_network_sha256_by_seed"][
        str(runner.STUDENT_SEEDS[1])
    ] = ONE_SHA
    manifest = tmp_path / "initial" / "PREFLIGHT-MANIFEST.json"
    digest = tmp_path / "initial" / "PREFLIGHT-MANIFEST.sha256"
    _write_json(manifest, tampered)
    digest.write_text(
        f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  PREFLIGHT-MANIFEST.json\n",
        encoding="ascii",
    )
    with pytest.raises(preflight.V023PreflightError, match="initial parameter"):
        preflight.validate_manifest(
            manifest,
            manifest_digest_path=digest,
            repo=REPO,
        )


def test_plan_is_exact_and_atomic(tmp_path: Path) -> None:
    output = tmp_path / "plan.json"
    payload = runner.emit_plan(output)
    report = verifier.verify_file(output, kind="plan")
    assert report["status"] == "PASS_STRUCTURAL_PLAN"
    assert len(payload["source_shards"]) == 8
    assert len(payload["fit_shards"]) == 48
    with pytest.raises(runner.V023GateError, match="overwrite"):
        runner.emit_plan(output)


def test_source_manifest_fit_and_root_aware_merge(tmp_path: Path) -> None:
    source_root = tmp_path
    fit_root = tmp_path
    for world in runner.WORLDS:
        runner.write_source_shard(
            runner.SourceShardSpec(world, source_root / "source" / f"world-{world}.json"),
            payload=_source_payload(world),
            preflight_sha256=PREFLIGHT_SHA256,
        )
    source_manifest_path = tmp_path / "source-manifest.json"
    source_manifest = runner.emit_source_manifest(
        source_directory=source_root,
        output=source_manifest_path,
        preflight_sha256=PREFLIGHT_SHA256,
    )
    source_report = verifier.verify_file(
        source_manifest_path,
        kind="source-manifest",
        preflight_sha256=PREFLIGHT_SHA256,
    )
    assert source_report["status"] == "PASS_STRUCTURAL_SOURCE_MANIFEST"
    source_sha = source_manifest["source_manifest_sha256"]

    for world in runner.WORLDS:
        for seed in runner.STUDENT_SEEDS:
            for arm in runner.ARMS:
                runner.write_fit_shard(
                    runner.FitShardSpec(
                        world,
                        seed,
                        arm,
                        source_root,
                        fit_root / "fit" / f"world-{world}" / f"seed-{seed}" / f"{arm.lower()}.json",
                        source_manifest=source_manifest_path,
                    ),
                    payload=_fit_payload(world, seed, arm, source_sha),
                    preflight_sha256=PREFLIGHT_SHA256,
                    source_manifest_sha256=source_sha,
                )
    merge_path = tmp_path / "merge.json"
    merged = runner.merge_shards(
        source_directory=source_root,
        fit_directory=fit_root,
        source_manifest=source_manifest_path,
        output=merge_path,
        preflight_sha256=PREFLIGHT_SHA256,
    )
    report = verifier.verify_file(
        merge_path,
        kind="merge",
        source_root=source_root,
        fit_root=fit_root,
    )
    assert report["status"] == "PASS_STRUCTURAL_MERGE"
    assert merged["decision"] is None

    tampered_merge = dict(merged)
    tampered_merge["fit_shards"] = list(merged["fit_shards"])
    tampered_merge["fit_shards"][0] = dict(tampered_merge["fit_shards"][0])
    tampered_merge["fit_shards"][0]["path"] = "fit/world-9999/seed-0/informed.json"
    with pytest.raises(verifier.V023VerificationError, match="fit shard path"):
        verifier.verify_merge_payload(tampered_merge)

    source_file = source_root / "source" / f"world-{runner.WORLDS[0]}.json"
    source_file.write_bytes(source_file.read_bytes().replace(b'"pair_count":1', b'"pair_count":2'))
    with pytest.raises(verifier.V023VerificationError, match="source child hash"):
        verifier.verify_merge_payload(
            merged,
            source_root=source_root,
            fit_root=fit_root,
        )


def test_adapter_seam_is_live_but_cli_without_adapter_is_closed(tmp_path: Path) -> None:
    class SourceAdapter:
        def generate_source_shard(self, spec):
            return _source_payload(spec.world)

    destination = tmp_path / "source" / f"world-{runner.WORLDS[0]}.json"
    result = runner.run_source_stage(
        runner.SourceShardSpec(
            runner.WORLDS[0],
            destination,
            preflight_manifest_sha256=PREFLIGHT_SHA256,
        ),
        adapter=SourceAdapter(),
    )
    assert result == destination
    persisted = json.loads(destination.read_text(encoding="ascii"))
    verifier.verify_source_payload(
        persisted,
        world=runner.WORLDS[0],
        preflight_sha256=PREFLIGHT_SHA256,
    )
    with pytest.raises(runner.V023GateError, match="no physical adapter"):
        runner.run_source_stage(
            runner.SourceShardSpec(runner.WORLDS[0], tmp_path / "closed.json"),
            adapter=None,
        )
