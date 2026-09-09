from __future__ import annotations

from dataclasses import replace
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


generator = _load(
    "mcrl_v023_c1c2_target_generation_test_module",
    HERE / "generate_v023_c1c2_targets.py",
)
materializer_test = _load(
    "mcrl_v023_c1c2_materializer_fixture_test_module",
    REPO
    / ".scratch"
    / "multi-catfish-v023-c1c2-neutral-materialization"
    / "test_materialize_v023_c1c2.py",
)
target_batch_test = _load(
    "mcrl_v023_target_batch_fixture_test_module",
    REPO
    / ".scratch"
    / "multi-catfish-v023-target-batch-adapter"
    / "test_target_batch_adapter.py",
)


def _write_fixture(tmp_path: Path):
    materializer = materializer_test.module
    payload = materializer_test._payload()
    capture = tmp_path / "capture.json"
    capture.write_bytes(materializer.canonical_bytes(payload) + b"\n")
    bundle = materializer.materialize_capture(payload)
    materialization = tmp_path / "materialized"
    materializer.write_materialization(bundle, materialization)
    return capture, materialization


def test_sealed_loader_reuses_exact_v2_materialization_and_budgets(tmp_path: Path) -> None:
    capture, materialization = _write_fixture(tmp_path)
    sealed = generator.load_sealed_inputs(capture, materialization)

    assert sealed.bundle.c1_informed.budget == sealed.bundle.c1_neutral.budget
    assert sealed.bundle.c2_informed.budget == sealed.bundle.c2_neutral.budget
    assert sealed.capture_sha256 == generator._sha256_file(capture)
    assert set(generator._group_c1_by_world(sealed, sealed.bundle.c1_informed)) == {
        1000,
        1001,
    }
    assert set(generator._group_c2_by_world(sealed, sealed.bundle.c2_informed)) == {
        2026121705,
        2026121706,
        2026121707,
        2026121708,
    }


def test_loader_retains_c1_state_digest_outside_typed_source_record(tmp_path: Path) -> None:
    """The runtime C1 record intentionally omits the captured state digest."""

    capture, materialization = _write_fixture(tmp_path)
    sealed = generator.load_sealed_inputs(capture, materialization)
    payload = materializer_test.module.read_canonical_json(capture)
    expected = {
        row["anchor_sha256"]: row["state_sha256"]
        for row in payload["c1"]["records"]
    }

    assert sealed.c1_state_sha256_by_anchor == expected
    assert all(not hasattr(record, "state_sha256") for record in sealed.c1_records)


def test_loader_rejects_route_file_hash_or_payload_drift(tmp_path: Path) -> None:
    capture, materialization = _write_fixture(tmp_path)
    route = materialization / "c1-informed.json"
    route.write_bytes(route.read_bytes() + b"\n")
    with pytest.raises(generator.TargetGenerationError, match="hash drifted"):
        generator.load_sealed_inputs(capture, materialization)


def test_loader_rejects_cluster_match_audit_drift(tmp_path: Path) -> None:
    capture, materialization = _write_fixture(tmp_path)
    receipt_path = materialization / "receipt.json"
    receipt = materializer_test.module.read_canonical_json(receipt_path)
    receipt["c1_cluster_match_audit"] = dict(receipt["c1_cluster_match_audit"])
    receipt["c1_cluster_match_audit"]["anchor_overlap_count"] += 1
    receipt_path.write_bytes(
        materializer_test.module.canonical_bytes(receipt) + b"\n"
    )
    manifest_path = materialization / "MANIFEST.sha256"
    entries = generator._manifest_entries(manifest_path)
    entries["receipt.json"] = generator._sha256_file(receipt_path)
    manifest_path.write_text(
        "".join(f"{entries[name]}  {name}\n" for name in sorted(entries)),
        encoding="ascii",
    )
    with pytest.raises(generator.TargetGenerationError, match="receipt disagrees"):
        generator.load_sealed_inputs(capture, materialization)


def test_loader_rejects_equal_budget_violation_before_runtime(monkeypatch, tmp_path: Path) -> None:
    capture, materialization = _write_fixture(tmp_path)
    original = generator._expected_materialization_payloads

    def altered(bundle, materializer):
        payloads = original(bundle, materializer)
        payloads["c1-neutral.json"] = dict(payloads["c1-neutral.json"])
        payloads["c1-neutral.json"]["row_budget"] = 999
        return payloads

    monkeypatch.setattr(generator, "_expected_materialization_payloads", altered)
    with pytest.raises(generator.TargetGenerationError, match="not the sealed source selection"):
        generator.load_sealed_inputs(capture, materialization)


def test_grouping_rejects_c2_world_seed_mismatch(tmp_path: Path) -> None:
    capture, materialization = _write_fixture(tmp_path)
    sealed = generator.load_sealed_inputs(capture, materialization)
    key = next(iter(sealed.c2_anchor_by_key))
    anchor = sealed.c2_anchor_by_key[key]
    altered_anchor = replace(anchor, world_id=int(anchor.source_seed) + 1)
    altered_map = dict(sealed.c2_anchor_by_key)
    altered_map[key] = altered_anchor
    altered = replace(sealed, c2_anchor_by_key=altered_map)

    with pytest.raises(generator.TargetGenerationError, match="world_id and source_seed"):
        generator._group_c2_by_world(altered, altered.bundle.c2_informed)


def test_mode_world_schedule_partitions_are_disjoint_and_complete(tmp_path: Path) -> None:
    capture, materialization = _write_fixture(tmp_path)
    sealed = generator.load_sealed_inputs(capture, materialization)

    original = generator.build_schedule(sealed)
    partitions: dict[str, dict[str, object]] = {}
    for key in original:
        mode, world_text = key.split(":", 1)
        partitions.update(
            generator.build_schedule(
                sealed, modes=(mode,), worlds=(int(world_text),)
            )
        )

    assert set(partitions) == set(original)
    assert partitions == original

    def row_keys(schedule: dict[str, dict[str, object]]) -> set[tuple[str, str, bytes]]:
        return {
            (shard_key, family, generator._canonical_bytes(row))
            for shard_key, shard in schedule.items()
            for family in ("C1", "C2")
            for row in shard[family]
        }

    all_rows = row_keys(original)
    partition_rows = row_keys(partitions)
    assert partition_rows == all_rows
    assert len(partition_rows) == sum(
        len(shard[family])
        for shard in original.values()
        for family in ("C1", "C2")
    )


def test_world_schedule_rejects_an_unselected_world(tmp_path: Path) -> None:
    capture, materialization = _write_fixture(tmp_path)
    sealed = generator.load_sealed_inputs(capture, materialization)

    with pytest.raises(generator.TargetGenerationError, match="has no selected rows"):
        generator.build_schedule(sealed, modes=("informed",), worlds=(999999,))


def test_target_generation_is_fixed_to_100_users(tmp_path: Path) -> None:
    with pytest.raises(generator.TargetGenerationError, match="exactly 100 users"):
        generator.generate_targets(
            capture_path=tmp_path / "capture.json",
            materialization_dir=tmp_path / "materialized",
            output=tmp_path / "output",
            tle_root=tmp_path / "tle",
            prereg=tmp_path / "prereg.json",
            manifest=tmp_path / "manifest.json",
            manifest_digest=tmp_path / "manifest.sha256",
            execution_addendum=tmp_path / "addendum.md",
            users=99,
        )


def test_cli_parser_requires_explicit_server_inputs() -> None:
    parser = generator._parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_cli_parser_accepts_one_world_shard() -> None:
    parser = generator._parser()
    args = parser.parse_args(
        [
            "--capture",
            "capture.json",
            "--materialization-dir",
            "materialized",
            "--output",
            "targets",
            "--tle-root",
            "tle",
            "--prereg",
            "prereg.json",
            "--manifest",
            "manifest.json",
            "--manifest-digest",
            "manifest.sha256",
            "--execution-addendum",
            "addendum.md",
            "--mode",
            "neutral",
            "--world",
            "2026121705",
        ]
    )
    assert args.mode == "neutral"
    assert args.world == 2026121705


def test_ops3_schedule_uses_current_ops3_provenance_not_legacy_backend(
) -> None:
    row = SimpleNamespace(
        focal_user=7,
        candidate_physical_key=(123, 45),
        source_rule="informed",
    )

    result = generator._ops3_schedule_sha256(
        native_data={
            "ops3_anchor_sha256": "a" * 64,
            "ops3_projection_sha256": "c" * 64,
        },
        source_anchor_sha256="b" * 64,
        selected_rows=(row,),
        mode="informed",
    )

    assert len(result) == 64


def test_generator_c2_path_has_no_temporal_backend_or_materializer_dependency() -> None:
    source = (HERE / "generate_v023_c1c2_targets.py").read_text(encoding="utf-8")
    assert "C2TemporalForkTrainerBackend" not in source
    assert "ee_axis_temporal_capture" not in source
    assert "ee_axis_temporal_dataset" not in source
    assert "c2_temporal_fork" not in source
    assert "multi-catfish-v023-r7-launch-ready" in source


def test_output_closure_binds_exact_ops3_producer_and_d40_checkpoint() -> None:
    closure = generator._output_code_closure()
    producer = generator.OPS3_PRODUCER_PATH.relative_to(generator.REPO).as_posix()
    adapter = generator.D40_ADAPTER_PATH.relative_to(generator.REPO).as_posix()
    checkpoint = generator.D40_CHECKPOINT_PATH.relative_to(generator.REPO).as_posix()
    assert closure[producer] == generator._sha256_file(generator.OPS3_PRODUCER_PATH)
    assert closure[adapter] == generator._sha256_file(generator.D40_ADAPTER_PATH)
    assert closure[checkpoint] == generator._sha256_file(generator.D40_CHECKPOINT_PATH)


def test_ops3_selected_pair_preserves_exact_normalized_target_delta_and_provenance() -> None:
    """C2 labels are already normalized by the authoritative OPS-3 producer."""

    row = SimpleNamespace(
        anchor_sha256="a" * 64,
        step_index=8,
        focal_user=1,
        reference_action=2,
        candidate_action=4,
        candidate_physical_key=(77, 3),
        source_rule="informed",
    )
    native_data = {
        "masks": __import__("numpy").array([[True] * 5, [True] * 5]),
        "q2_context": {
            "state_matrix": __import__("numpy").zeros((2, 80), dtype="float32"),
            "features": __import__("numpy").zeros((2, 5, 16)),
            "persistence": __import__("numpy").zeros((2, 3, 5)),
            "rate_bps": __import__("numpy").zeros((2, 3, 5)),
            "marginal_power_w": __import__("numpy").zeros((2, 3, 5)),
            "required_power_w": __import__("numpy").zeros((2, 3, 5)),
            "target_values": __import__("numpy").array(
                [[0.0] * 5, [0.25, -0.5, 0.125, 0.0, 1.5]], dtype="float64"
            ),
            "horizon": 1,
        },
        "q1_reference": __import__("numpy").array([0, 1]),
        "ops3_anchor_sha256": "b" * 64,
        "ops3_tracker_seed_sha256": "c" * 64,
        "ops3_projection_sha256": "d" * 64,
        "ops3_future_d2_indices": [12],
        "ops3_sample_times_utc": ["2026-09-07T00:00:00+00:00"],
        "ops3_offset_times_utc": ["2026-09-07T00:00:01+00:00"],
    }

    record = generator._ops3_selected_pair_record(
        row,
        world=2026121707,
        mode="informed",
        native_data=native_data,
        schedule_sha256="e" * 64,
    )

    assert record["schema"] == generator.OPS3_SELECTED_PAIR_SCHEMA
    assert record["target_unit"] == "normalized-repriced-ops3-delta-over-kappa"
    assert record["target_reference_value"] == 0.125
    assert record["target_candidate_value"] == 1.5
    assert record["target_delta"] == 1.375
    assert record["q2_state"] == [0.0] * 80
    assert record["action_mask"] == [True] * 5
    assert record["provenance"]["ops3_projection_sha256"] == "d" * 64


def test_ops3_selected_pair_rejects_hash_drift_and_illegal_candidate() -> None:
    row = SimpleNamespace(
        anchor_sha256="a" * 64,
        step_index=9,
        focal_user=0,
        reference_action=0,
        candidate_action=1,
        candidate_physical_key=(1, 1),
        source_rule="neutral",
    )
    context = {
        "state_matrix": __import__("numpy").zeros((1, 32), dtype="float32"),
        "features": __import__("numpy").zeros((1, 2, 16)),
        "persistence": __import__("numpy").zeros((1, 3, 2)),
        "rate_bps": __import__("numpy").zeros((1, 3, 2)),
        "marginal_power_w": __import__("numpy").zeros((1, 3, 2)),
        "required_power_w": __import__("numpy").zeros((1, 3, 2)),
        "target_values": __import__("numpy").zeros((1, 2)),
        "horizon": 0,
    }
    base = {
        "masks": __import__("numpy").array([[True, True]]),
        "q2_context": context,
        "q1_reference": __import__("numpy").array([0]),
        "ops3_anchor_sha256": "b" * 64,
        "ops3_tracker_seed_sha256": "c" * 64,
        "ops3_projection_sha256": "d" * 64,
        "ops3_future_d2_indices": [],
        "ops3_sample_times_utc": [],
        "ops3_offset_times_utc": [],
    }
    with pytest.raises(generator.TargetGenerationError, match="SHA-256"):
        generator._ops3_selected_pair_record(
            row, world=1, mode="neutral", native_data={**base, "ops3_projection_sha256": "not-a-digest"}, schedule_sha256="e" * 64
        )
    illegal = {**base, "masks": __import__("numpy").array([[True, False]])}
    with pytest.raises(generator.TargetGenerationError, match="candidate action is illegal"):
        generator._ops3_selected_pair_record(
            row, world=1, mode="neutral", native_data=illegal, schedule_sha256="e" * 64
        )


@pytest.mark.parametrize(("step", "horizon"), ((7, 2), (8, 1), (9, 0)))
def test_ops3_selected_pair_accepts_predeclared_late_anchor_truncation(
    step: int, horizon: int
) -> None:
    row = SimpleNamespace(
        anchor_sha256="a" * 64,
        step_index=step,
        focal_user=0,
        reference_action=0,
        candidate_action=1,
        candidate_physical_key=(1, 1),
        source_rule="informed",
    )
    context = {
        "state_matrix": __import__("numpy").zeros((1, 32), dtype="float32"),
        "features": __import__("numpy").zeros((1, 2, 16)),
        "persistence": __import__("numpy").zeros((1, 3, 2)),
        "rate_bps": __import__("numpy").zeros((1, 3, 2)),
        "marginal_power_w": __import__("numpy").zeros((1, 3, 2)),
        "required_power_w": __import__("numpy").zeros((1, 3, 2)),
        "target_values": __import__("numpy").zeros((1, 2)),
        "horizon": horizon,
    }
    native_data = {
        "masks": __import__("numpy").array([[True, True]]),
        "q2_context": context,
        "q1_reference": __import__("numpy").array([0]),
        "ops3_anchor_sha256": "b" * 64,
        "ops3_tracker_seed_sha256": "c" * 64,
        "ops3_projection_sha256": "d" * 64,
        "ops3_future_d2_indices": list(range(horizon)),
        "ops3_sample_times_utc": ["2026-09-07T00:00:00+00:00"] * horizon,
        "ops3_offset_times_utc": ["2026-09-07T00:00:01+00:00"] * horizon,
    }
    record = generator._ops3_selected_pair_record(
        row, world=1, mode="informed", native_data=native_data, schedule_sha256="e" * 64
    )
    assert record["step_index"] == step
    assert record["horizon"] == horizon


def test_write_outputs_counts_object_and_ops3_mapping_rows(tmp_path: Path) -> None:
    c1_dataset = target_batch_test._c1_dataset(mode="informed", world=7)
    c2_dataset = {
        "schema": generator.OPS3_SELECTED_PAIR_SCHEMA,
        "source_manifest_sha256": c1_dataset.source_manifest_sha256,
        "rows": [{"fixture": "ops3-row-1"}, {"fixture": "ops3-row-2"}],
    }
    sealed = SimpleNamespace(
        capture_path=tmp_path / "capture.json",
        capture_sha256="a" * 64,
        materialization_dir=tmp_path / "materialized",
        materialization_manifest_sha256="b" * 64,
        pool_sha256="c" * 64,
        source_manifest_sha256=c1_dataset.source_manifest_sha256,
        checkpoint_sha256=c1_dataset.checkpoint_sha256,
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
    schedule = {
        "informed:7": {
            "mode": "informed",
            "world": 7,
            "C1": [],
            "C2": [],
        }
    }

    output = tmp_path / "targets"
    summary = generator._write_outputs(
        output,
        sealed=sealed,
        ctx=ctx,
        schedule=schedule,
        c1_datasets={("informed", 7): c1_dataset},
        c2_datasets={("informed", 7): c2_dataset},
        c1_bindings=(),
        c2_bindings=(),
    )

    assert {path.name for path in output.iterdir()} == {
        "c1-informed-world-7.json",
        "c2-informed-world-7.json",
        "receipt.json",
        "MANIFEST.sha256",
    }
    assert {
        line.split("  ", 1)[1]
        for line in (output / "MANIFEST.sha256").read_text(encoding="ascii").splitlines()
    } == {
        "c1-informed-world-7.json",
        "c2-informed-world-7.json",
        "receipt.json",
    }
    assert summary["row_counts"] == {"C1": 1, "C2": 2}

    with pytest.raises(
        generator.TargetGenerationError,
        match="mapping dataset is missing required 'rows'",
    ):
        generator._write_outputs(
            tmp_path / "missing-rows",
            sealed=sealed,
            ctx=ctx,
            schedule=schedule,
            c1_datasets={("informed", 7): c1_dataset},
            c2_datasets={
                ("informed", 7): {
                    key: value for key, value in c2_dataset.items() if key != "rows"
                }
            },
            c1_bindings=(),
            c2_bindings=(),
        )
