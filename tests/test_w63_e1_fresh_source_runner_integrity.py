"""W-63 -- E1 fresh-source runner sealing and no-overwrite integrity."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcrl.env.keyed_fading import KeyedFadingField


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "ee-axis-redesign" / "run_v03_e1_fresh_sources.py"


def _module():
    spec = importlib.util.spec_from_file_location("run_v03_e1_fresh_sources_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_binds_runner_and_current_c2_schedule_source() -> None:
    runner = _module()
    manifest = runner._build_source_manifest()
    paths = {row["path"] for row in manifest["files"]}
    assert ".scratch/ee-axis-redesign/run_v03_e1_fresh_sources.py" in paths
    assert "src/mcrl/runtime/ee_axis_e1_c2_schedule.py" in paths
    assert runner._validate_source_manifest(manifest) == manifest["source_manifest_sha256"]


def test_prereg_is_six_fresh_seeds_three_one_two_and_no_ee() -> None:
    runner = _module()
    payload = runner._build_preregistration(
        source_manifest_sha256="a" * 64,
        checkpoint_sha256="b" * 64,
        environment_source_sha256="c" * 64,
        reward_source_sha256="d" * 64,
        learner_contract={"learning_rate_hex": float(0.001).hex()},
    )
    assert list(payload["source_seed_split"].values()).count("train") == 3
    assert list(payload["source_seed_split"].values()).count("validation") == 1
    assert list(payload["source_seed_split"].values()).count("test") == 2
    assert payload["endpoint"] == "NO_EE_ENDPOINT_IN_E1_SOURCE_OR_LADDER"
    assert payload["learner"]["learning_rate_hex"] == float(0.001).hex()
    body = dict(payload)
    digest = body.pop("prereg_sha256")
    assert runner._canonical_sha256(body) == digest


def test_learner_contract_binds_frozen_calibration_and_lr() -> None:
    runner = _module()
    checkpoint = json.loads(runner.CALIBRATION_RECEIPT.read_text(encoding="utf-8"))[
        "checkpoint_sha256"
    ]
    contract = runner._learner_contract(checkpoint_sha256=checkpoint)
    assert contract["learning_rate_hex"] == float(0.001).hex()
    assert contract["hidden_layers"] == [100, 50, 50]
    assert contract["activation"] == "tanh"
    assert len(contract["calibration_receipt_file_sha256"]) == 64


def test_candidate_action_and_cluster_fading_digest_are_preoutcome() -> None:
    runner = _module()
    anchor = SimpleNamespace(
        focal_user=1,
        action_bindings_by_user=(
            (),
            (
                SimpleNamespace(action=3, physical_key=(100, 1)),
                SimpleNamespace(action=7, physical_key=(100, 2)),
            ),
        ),
        checkpoint_sha256="a" * 64,
        anchor_sha256="b" * 64,
        evaluation_seed=2026091001,
    )
    prepared = SimpleNamespace(anchor=anchor, candidate_key=(100, 2))
    assert runner._candidate_action(prepared) == 7
    expected = KeyedFadingField.from_components(
        runner.c2_pair_smoke.backend.FORECAST_SCHEMA,
        "a" * 64,
        "b" * 64,
        1,
        2026091001,
    ).root_digest
    assert runner._cluster_field_sha256(prepared) == expected


def test_anchor_schedule_digest_is_recomputed_from_all_preoutcome_fields() -> None:
    runner = _module()
    cluster = SimpleNamespace(
        source_seed=2026091001,
        anchor_sha256="a" * 64,
        world_anchor_sha256=runner.e1_c2_world_anchor_sha256(
            source_seed=2026091001, anchor_step=3
        ),
        anchor_step=3,
        focal_user=7,
        reference_action=11,
        candidate_action=3,
        reference_physical_key=(100, 1),
        candidate_physical_key=(100, 2),
        candidate_source_rule="incumbent-hold",
    )
    first = runner._anchor_schedule_sha256_from_cluster(cluster)
    cluster.candidate_action = 4
    second = runner._anchor_schedule_sha256_from_cluster(cluster)
    assert first != second


def test_canonical_write_is_no_overwrite(tmp_path: Path) -> None:
    runner = _module()
    path = tmp_path / "sealed.json"
    digest = runner._write_once_json(path, {"b": 2, "a": 1})
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.read_bytes() == b'{"a":1,"b":2}\n'
    with pytest.raises(FileExistsError, match="overwrite"):
        runner._write_once_json(path, {"a": 1, "b": 2})


def test_prepare_refuses_existing_namespace_before_loading_physics(tmp_path: Path) -> None:
    runner = _module()
    output = tmp_path / "already-there"
    output.mkdir()
    with pytest.raises(FileExistsError, match="overwrite"):
        runner.prepare(output_dir=output, tle_root=tmp_path / "unused")


def test_valid_public_receipt_authenticates_ladder_index_without_targets(
    tmp_path: Path,
) -> None:
    runner = _module()
    data_root = tmp_path / "source-data"
    data_root.mkdir()
    opening = {str(seed): "b" * 64 for seed in runner.SOURCE_SEED_SPLIT}
    temporal = {str(seed): "c" * 64 for seed in runner.SOURCE_SEED_SPLIT}
    ladder_index, test_index = runner._source_index_payloads(
        source_manifest_sha256="a" * 64,
        checkpoint_sha256="9" * 64,
        opening_sha256s=opening,
        temporal_sha256s=temporal,
    )
    ladder_sha = runner._write_once_json(
        data_root / "ladder-index.json", ladder_index
    )
    test_sha = runner._write_once_json(data_root / "test-index.json", test_index)
    receipt = {
        "schema": runner.SOURCE_RECEIPT_SCHEMA,
        "status": "PASS",
        "claim_ceiling": runner.CLAIM_CEILING,
        "training": False,
        "held_out_ee_evaluated": False,
        "source_manifest_sha256": "a" * 64,
        "checkpoint_sha256": "9" * 64,
        "opening_dataset_sha256s": opening,
        "temporal_dataset_sha256s": temporal,
        "opening_dataset_file_sha256s": {
            str(seed): "d" * 64 for seed in runner.SOURCE_SEED_SPLIT
        },
        "temporal_dataset_file_sha256s": {
            str(seed): "e" * 64 for seed in runner.SOURCE_SEED_SPLIT
        },
        "ladder_index_file_sha256": ladder_sha,
        "test_index_file_sha256": test_sha,
        "ladder_generation_details_file_sha256": "f" * 64,
        "test_generation_details_file_sha256": "1" * 64,
        "coverage_by_seed": [
            {
                "source_seed": seed,
                "split": split,
                "c1_rows": 1,
                "c3_rows": 1,
                "c2_scheduled_clusters": 15,
                "c2_scheduled_anchors": 3,
                "c2_complete_clusters": 10,
                "c2_complete_anchors": 3,
                "c2_censored_clusters": 5,
            }
            for seed, split in sorted(runner.SOURCE_SEED_SPLIT.items())
        ],
        "split_receipt": {},
        "elapsed_s": 0.0,
    }
    prereg = {
        "source_manifest_sha256": "a" * 64,
        "checkpoint_sha256": "9" * 64,
    }
    assert runner._validate_published_index(
        data_root=data_root,
        prereg=prereg,
        receipt=receipt,
        kind="ladder",
    ) == ladder_index
    assert b"target_surplus_bits" not in runner._canonical_bytes(receipt)
