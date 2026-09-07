"""Producer-derived tests for the non-formal two-route rehearsal package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FACTORY_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-provider-factory-v3"
for _directory in (HERE, FACTORY_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import rehearsal_real_shard_provider as PROVIDER
import rehearsal_two_route_training_real_shards as REHEARSAL
import test_v023_c1c2_provider_factory_v3 as FACTORY_HELPERS


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _write_producer_shard(root: Path, *, mode: str, world: int) -> Path:
    """Use the producer writer, factory-v3 helpers, and real excerpt row."""

    generator, controller, _sealer = FACTORY_HELPERS._producer_modules()
    c1_dataset = FACTORY_HELPERS._c1_dataset(mode=mode, world=world)
    c1_binding = FACTORY_HELPERS._c1_binding(
        c1_dataset, mode=mode, world=world
    )
    c2_dataset, c2_binding = FACTORY_HELPERS._c2_dataset_and_binding(
        mode=mode, world=world
    )
    schedule = {
        f"{mode}:{world}": {
            "mode": mode,
            "world": world,
            "C1": [FACTORY_HELPERS._schedule_row(c1_binding, route="C1")],
            "C2": [FACTORY_HELPERS._schedule_row(c2_binding, route="C2")],
        }
    }
    sealed = SimpleNamespace(
        capture_path=root.parent / "capture.json",
        capture_sha256=_digest("rehearsal-capture"),
        materialization_dir=root.parent / "materialization",
        materialization_manifest_sha256=_digest("rehearsal-materialization"),
        pool_sha256=_digest("rehearsal-pool"),
        source_manifest_sha256=_digest("successor-target-source-manifest"),
        checkpoint_sha256=_digest("successor-target-checkpoint"),
    )
    ctx = SimpleNamespace(
        modules=SimpleNamespace(
            opening_dataset=SimpleNamespace(
                write_opening_dataset=FACTORY_HELPERS.write_opening_dataset
            )
        ),
        source_family="producer-built-rehearsal-fixture",
        lambda_bits_per_j=float.fromhex(
            FACTORY_HELPERS.FACTORY.EXPECTED_LAMBDA_HEX
        ),
        kappa_bits=float.fromhex(
            FACTORY_HELPERS.FACTORY.EXPECTED_KAPPA_HEX
        ),
        interval_s=float.fromhex(
            FACTORY_HELPERS.FACTORY.EXPECTED_INTERVAL_HEX
        ),
    )
    generator._write_outputs(
        root,
        sealed=sealed,
        ctx=ctx,
        schedule=schedule,
        c1_datasets={(mode, world): c1_dataset},
        c2_datasets={(mode, world): c2_dataset},
        c1_bindings=(c1_binding,),
        c2_bindings=(c2_binding,),
    )
    status = {
        "schema": controller.SHARD_STATUS_SCHEMA,
        "event": "terminal",
        "state": "PASS",
        "mode": mode,
        "world": world,
        "recorded_unix_s": 0.0,
        "returncode": 0,
        "receipt_sha256": PROVIDER._file_sha256(root / "receipt.json"),
        "manifest_sha256": PROVIDER._file_sha256(root / "MANIFEST.sha256"),
        "log": f"{mode}-world-{world}.log",
    }
    status_path = (
        root.parent.parent
        / "shard-status"
        / f"{mode}-world-{world}.terminal.json"
    )
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_bytes(controller._canonical(status))
    assert not (root / "COMPLETE").exists()
    return root


def _write_shard_panel(root: Path) -> Path:
    (root / "informed").mkdir(parents=True)
    (root / "neutral").mkdir()
    _write_producer_shard(
        root / "informed" / "world-2026121705", mode="informed", world=2026121705
    )
    _write_producer_shard(
        root / "informed" / "world-2026121706", mode="informed", world=2026121706
    )
    _write_producer_shard(
        root / "neutral" / "world-2026121706", mode="neutral", world=2026121706
    )
    # A live-but-not-completed directory is not a real shard and is recorded,
    # not consumed.
    (root / "neutral" / "world-2026121707-incomplete").mkdir()
    return root


@pytest.fixture(scope="module")
def shard_panel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _write_shard_panel(tmp_path_factory.mktemp("rehearsal-shards"))


@pytest.fixture(scope="module", autouse=True)
def _single_torch_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def _adapter_aggregate(root: Path, *, mode: str, route: str):
    route_batches: list[Any] = []
    for shard in sorted((root / mode).iterdir()):
        if not (shard / "MANIFEST.sha256").is_file():
            continue
        loaded = PROVIDER._load_authenticated_shard(
            shard, expected_mode=mode
        )
        if loaded is None:
            continue
        inputs, _receipt, _snapshot = loaded
        route_batches.extend(
            inputs.c1_route_batches if route == "C1" else inputs.c2_route_batches
        )
    return PROVIDER._TARGET._aggregate_pair_batches(route_batches, route=route)


def _assert_batch_bitwise_equal(actual: object, expected: object) -> None:
    assert type(actual) is type(expected)
    fields = (
        "states",
        "reference_actions",
        "candidate_actions",
        "target_surplus_bits"
        if hasattr(expected, "target_surplus_bits")
        else "normalized_target_deltas",
        "action_masks",
    )
    for field in fields:
        left = np.asarray(getattr(actual, field))
        right = np.asarray(getattr(expected, field))
        assert left.dtype == right.dtype
        assert left.shape == right.shape
        assert left.tobytes(order="C") == right.tobytes(order="C")


def test_provider_identity_batches_c2_units_and_skip_missing(shard_panel: Path) -> None:
    provider = PROVIDER.RehearsalRealShardProvider(
        shard_panel, planned_epoch_budget=3
    )
    identity = provider.provider_identity_payload
    assert identity["formal"] is False
    assert identity["rehearsal"] is True
    assert identity["claim_ceiling"] == PROVIDER.CLAIM_CEILING
    assert identity["planned_epoch_budget"] == 3
    assert identity["worlds_used_by_mode"] == {
        "informed": [2026121705, 2026121706],
        "neutral": [2026121706],
    }
    assert len(identity["shard_digests_used"]) == 3
    assert identity["skipped_incomplete_shard_dirs"] == [
        "neutral/world-2026121707-incomplete"
    ]
    assert identity["skipped_shards"] == [
        {
            "shard_dir": "neutral/world-2026121707-incomplete",
            "reason": "missing regular MANIFEST.sha256 or receipt.json",
        }
    ]
    assert all(not shard["is_symlink"] for shard in identity["shard_digests_used"])
    assert all("status_path" in shard for shard in identity["shard_digests_used"])
    assert all("status_sha256" in shard for shard in identity["shard_digests_used"])
    assert all("complete_sha256" not in shard for shard in identity["shard_digests_used"])
    assert all(
        shard["entry_path"] == shard["resolved_path"]
        for shard in identity["shard_digests_used"]
    )

    c1_neutral = provider.next_batch(
        route="C1", source="neutral", update_cursor=0
    )
    c1_informed = provider.next_batch(
        route="C1", source="informed", update_cursor=0
    )
    _assert_batch_bitwise_equal(
        c1_neutral.batch, _adapter_aggregate(shard_panel, mode="neutral", route="C1")
    )
    _assert_batch_bitwise_equal(
        c1_informed.batch,
        _adapter_aggregate(shard_panel, mode="informed", route="C1"),
    )

    c2_neutral = provider.next_batch(
        route="C2", source="neutral", update_cursor=1
    )
    c2_informed = provider.next_batch(
        route="C2", source="informed", update_cursor=1
    )
    expected_neutral = _adapter_aggregate(shard_panel, mode="neutral", route="C2")
    expected_informed = _adapter_aggregate(shard_panel, mode="informed", route="C2")
    _assert_batch_bitwise_equal(c2_neutral.batch, expected_neutral)
    _assert_batch_bitwise_equal(c2_informed.batch, expected_informed)

    c2_document = json.loads(
        (
            shard_panel
            / "neutral/world-2026121706/c2-neutral-world-2026121706.json"
        ).read_text(encoding="ascii")
    )
    target_delta = float(c2_document["rows"][0]["target_delta"])
    kappa = float.fromhex(c2_document["kappa_bits"])
    actual = float(c2_neutral.batch.normalized_target_deltas[0])
    assert actual == target_delta
    assert actual != target_delta / kappa


def test_symlink_farm_shards_load_and_record_entry_and_resolved_paths(
    tmp_path: Path,
) -> None:
    producer_root = tmp_path / "producer-shards"
    informed = _write_producer_shard(
        producer_root / "informed/world-2026121705",
        mode="informed",
        world=2026121705,
    )
    neutral = _write_producer_shard(
        producer_root / "neutral/world-2026121705",
        mode="neutral",
        world=2026121705,
    )
    rehearsal_root = tmp_path / "rehearsal-shards"
    (rehearsal_root / "informed").mkdir(parents=True)
    (rehearsal_root / "neutral").mkdir()
    (rehearsal_root / "informed/world-2026121705-r5").symlink_to(
        informed, target_is_directory=True
    )
    (rehearsal_root / "neutral/world-2026121705-r5").symlink_to(
        neutral, target_is_directory=True
    )

    provider = PROVIDER.RehearsalRealShardProvider(
        rehearsal_root, planned_epoch_budget=2
    )
    catalogue = provider.provider_identity_payload["shard_digests_used"]
    expected = {
        "informed": (
            rehearsal_root / "informed/world-2026121705-r5",
            informed,
        ),
        "neutral": (
            rehearsal_root / "neutral/world-2026121705-r5",
            neutral,
        ),
    }
    assert provider.worlds_used_by_mode == {
        "informed": (2026121705,),
        "neutral": (2026121705,),
    }
    for shard in catalogue:
        entry_path, resolved_path = expected[shard["mode"]]
        assert shard["entry_path"] == str(entry_path)
        assert shard["resolved_path"] == str(resolved_path.resolve(strict=True))
        assert shard["is_symlink"] is True

    output = tmp_path / "symlink-farm-REHEARSAL-NONFORMAL-run"
    receipt = REHEARSAL.run_rehearsal(
        shard_root=rehearsal_root,
        output_root=output,
        epochs=1,
        train_seed=2927175120652069826,
    )
    assert receipt["provider_identity_payload"]["shard_digests_used"] == catalogue
    assert receipt["shard_catalogue"] == catalogue


def test_sampler_state_shape_and_exact_restore_matches_factory_v3(
    shard_panel: Path,
) -> None:
    first = PROVIDER.RehearsalRealShardProvider(
        shard_panel, planned_epoch_budget=3
    )
    first.next_batch(route="C1", source="neutral", update_cursor=0)
    first.next_batch(route="C1", source="informed", update_cursor=0)
    state = first.sampler_state()
    assert set(state) == {
        "schema",
        "routes",
        "sources",
        "epoch_budget",
        "provider_identity",
        "source_files",
        "source_members",
        "cursors",
        "next_update_cursor",
        "next_source_index",
        "consumed_file_order",
    }
    restored = PROVIDER.RehearsalRealShardProvider(
        shard_panel, planned_epoch_budget=3
    )
    restored.load_sampler_state(state)
    expected = first.next_batch(route="C2", source="neutral", update_cursor=1)
    actual = restored.next_batch(route="C2", source="neutral", update_cursor=1)
    assert expected.file_id == actual.file_id
    _assert_batch_bitwise_equal(actual.batch, expected.batch)


def test_individual_shard_authentication_mutation_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "mutated-panel"
    (root / "informed").mkdir(parents=True)
    (root / "neutral").mkdir()
    _write_producer_shard(root / "informed/s1", mode="informed", world=2026121705)
    neutral = _write_producer_shard(
        root / "neutral/s1", mode="neutral", world=2026121705
    )
    dataset = neutral / "c2-neutral-world-2026121705.json"
    dataset.write_bytes(dataset.read_bytes() + b" ")
    with pytest.raises(
        PROVIDER.RehearsalShardProviderError, match="mode manifest hash drifted"
    ):
        PROVIDER.RehearsalRealShardProvider(root, planned_epoch_budget=2)


def test_producer_shard_without_complete_and_with_status_loads(tmp_path: Path) -> None:
    root = tmp_path / "unsealed-producer-panel"
    (root / "informed").mkdir(parents=True)
    (root / "neutral").mkdir()
    _write_producer_shard(
        root / "informed/world-2026121705",
        mode="informed",
        world=2026121705,
    )
    _write_producer_shard(
        root / "neutral/world-2026121705",
        mode="neutral",
        world=2026121705,
    )

    provider = PROVIDER.RehearsalRealShardProvider(root, planned_epoch_budget=1)

    assert provider.worlds_used_by_mode == {
        "informed": (2026121705,),
        "neutral": (2026121705,),
    }
    assert not any((shard / "COMPLETE").exists() for shard in root.glob("*/*"))


def test_producer_shard_missing_status_is_skipped_with_reason(tmp_path: Path) -> None:
    root = _write_shard_panel(tmp_path / "missing-status-panel")
    missing = _write_producer_shard(
        root / "neutral/world-2026121708",
        mode="neutral",
        world=2026121708,
    )
    status = (
        root
        / "shard-status"
        / "neutral-world-2026121708.terminal.json"
    )
    status.unlink()

    provider = PROVIDER.RehearsalRealShardProvider(root, planned_epoch_budget=1)

    assert missing.is_dir()
    assert provider.provider_identity_payload["skipped_shards"][-1] == {
        "shard_dir": "neutral/world-2026121708",
        "reason": "missing sibling shard terminal status file",
    }


def test_rehearsal_writes_no_complete_and_prints_nonformal_pass(
    shard_panel: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "tiny-REHEARSAL-NONFORMAL-run"
    exit_code = REHEARSAL.main(
        [
            "--shard-root",
            str(shard_panel),
            "--output-root",
            str(output),
            "--epochs",
            "1",
            "--train-seed",
            "2927175120652069826",
        ]
    )
    assert exit_code == 0
    final_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert final_line.startswith("REHEARSAL_TWO_ROUTE_PASS ")
    receipt = json.loads(
        (output / "REHEARSAL-RECEIPT.json").read_text(encoding="ascii")
    )
    assert receipt["formal"] is False
    assert receipt["scientific_claim"] is False
    assert receipt["episode_training"] is False
    assert receipt["claim_ceiling"] == REHEARSAL.CLAIM_CEILING
    assert receipt["exact_continuation_verified"] is True
    assert receipt["finite_loss_checks"]["all_finite"] is True
    assert receipt["complete_marker_written"] is False
    assert not any(path.name == "COMPLETE" for path in output.rglob("*"))


def test_output_root_naming_and_absence_rules_are_enforced(tmp_path: Path) -> None:
    with pytest.raises(REHEARSAL.RehearsalTrainingError, match="basename"):
        REHEARSAL._validate_output_root(tmp_path / "ordinary-run")
    existing = tmp_path / "existing-REHEARSAL-NONFORMAL-run"
    existing.mkdir()
    with pytest.raises(REHEARSAL.RehearsalTrainingError, match="must not exist"):
        REHEARSAL._validate_output_root(existing)
