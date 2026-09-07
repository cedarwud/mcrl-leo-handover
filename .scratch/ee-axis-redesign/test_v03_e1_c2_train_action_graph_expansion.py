#!/usr/bin/env python3
"""Focused contract tests for the one-shot C2 train graph expansion."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "c2_train_graph_expansion_under_test",
    HERE / "run_v03_e1_c2_train_action_graph_expansion.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load C2 train graph expansion runner")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def cluster(seed: int, identity: str, reference: int, candidate: int) -> dict[str, object]:
    return {
        "source_seed": seed,
        "cluster_sha256": identity,
        "reference_action": reference,
        "candidate_action": candidate,
    }


class C2TrainGraphExpansionTopologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.action_dim = 12
        self.components = ((0, 1), (2, 3))
        self.unsupported = ((1, 2),)
        first, second = runner.CANDIDATE_SEED_ORDER[:2]
        self.first = first
        self.second = second
        self.schedules = {
            first: (
                cluster(first, "first-a", 1, 4),
                cluster(first, "first-b", 1, 5),
                cluster(first, "first-c", 2, 6),
                cluster(first, "first-bridge", 4, 6),
            ),
            second: (
                cluster(second, "second-a", 1, 7),
                cluster(second, "second-b", 2, 8),
                cluster(second, "second-c", 2, 9),
            ),
        }

    def test_candidate_pool_is_exact_and_consecutive(self) -> None:
        self.assertEqual(
            runner.CANDIDATE_SEED_ORDER,
            tuple(range(2026092201, 2026092221)),
        )
        self.assertEqual(len(runner.CANDIDATE_SEED_ORDER), 20)

    def test_connectivity_alone_does_not_pass_redundancy_gate(self) -> None:
        report = runner._coverage_report(
            action_dim=self.action_dim,
            original_components=self.components,
            unsupported_pairs=self.unsupported,
            clusters_by_seed={self.first: self.schedules[self.first]},
        )
        self.assertEqual(report["remaining_unsupported_validation_action_pairs"], [])
        self.assertFalse(report["coverage_sufficient"])
        self.assertEqual(report["needed_action_evidence"]["1"]["clusters"], 2)
        self.assertEqual(report["needed_action_evidence"]["1"]["seeds"], [self.first])
        self.assertEqual(report["needed_action_evidence"]["2"]["clusters"], 1)

    def test_selects_shortest_fixed_prefix_with_three_clusters_two_seeds(self) -> None:
        selected, report = runner._select_shortest_prefix(
            action_dim=self.action_dim,
            original_components=self.components,
            unsupported_pairs=self.unsupported,
            schedules=self.schedules,
        )
        self.assertEqual(selected, (self.first, self.second))
        self.assertTrue(report["coverage_sufficient"])
        self.assertEqual(report["remaining_unsupported_validation_action_pairs"], [])
        for action in ("1", "2"):
            evidence = report["needed_action_evidence"][action]
            self.assertGreaterEqual(evidence["clusters"], 3)
            self.assertGreaterEqual(len(evidence["seeds"]), 2)

    def test_stops_at_first_passing_prefix_without_inspecting_later_topology(self) -> None:
        third = runner.CANDIDATE_SEED_ORDER[2]
        schedules = {**self.schedules, third: ({"malformed": True},)}
        selected, report = runner._select_shortest_prefix(
            action_dim=self.action_dim,
            original_components=self.components,
            unsupported_pairs=self.unsupported,
            schedules=schedules,
        )
        self.assertEqual(selected, (self.first, self.second))
        self.assertTrue(report["coverage_sufficient"])

    def test_rejects_any_reordered_or_replacement_pool(self) -> None:
        with self.assertRaisesRegex(
            runner.C2TrainGraphExpansionError, "pool/order"
        ):
            runner._select_shortest_prefix(
                action_dim=self.action_dim,
                original_components=self.components,
                unsupported_pairs=self.unsupported,
                schedules=self.schedules,
                candidate_seed_order=tuple(reversed(runner.CANDIDATE_SEED_ORDER)),
            )
        with self.assertRaisesRegex(
            runner.C2TrainGraphExpansionError, "unauthorized seed"
        ):
            runner._select_shortest_prefix(
                action_dim=self.action_dim,
                original_components=self.components,
                unsupported_pairs=self.unsupported,
                schedules={999: ()},
            )

    def test_exhausted_fixed_pool_returns_insufficient_without_second_pool(self) -> None:
        schedules = {seed: () for seed in runner.CANDIDATE_SEED_ORDER}
        selected, report = runner._select_shortest_prefix(
            action_dim=self.action_dim,
            original_components=self.components,
            unsupported_pairs=self.unsupported,
            schedules=schedules,
        )
        self.assertEqual(selected, ())
        self.assertFalse(report["coverage_sufficient"])
        self.assertEqual(
            report["remaining_unsupported_validation_action_pairs"],
            [{"reference_action": 1, "candidate_action": 2}],
        )

    def test_duplicate_cluster_identity_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            runner.C2TrainGraphExpansionError, "duplicate expansion cluster"
        ):
            runner._coverage_report(
                action_dim=self.action_dim,
                original_components=self.components,
                unsupported_pairs=self.unsupported,
                clusters_by_seed={
                    self.first: (
                        cluster(self.first, "same", 1, 4),
                        cluster(self.first, "same", 2, 4),
                    )
                },
            )


class C2TrainGraphExpansionArtifactTests(unittest.TestCase):
    def test_control_manifest_never_hashes_dataset_or_generation_detail_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source-data").mkdir()
            (root / "prereg.json").write_bytes(b"authority")
            for name in runner.SOURCE_DATA_CONTROL_FILES:
                (root / "source-data" / name).write_bytes(name.encode("ascii"))
            for name in (
                "opening-2026092005.json",
                "temporal-2026092005.json",
                "ladder-generation-details.json",
                "test-generation-details.json",
            ):
                (root / "source-data" / name).write_bytes(b"must-remain-opaque")
            with mock.patch.object(
                runner.source,
                "_file_sha256",
                wraps=runner.source._file_sha256,
            ) as hashed:
                manifest = runner._control_file_manifest(root)
            hashed_names = {Path(call.args[0]).name for call in hashed.call_args_list}
        self.assertIn("prereg.json", manifest)
        self.assertEqual(
            {
                path
                for path in manifest
                if path.startswith("source-data/")
            },
            {f"source-data/{name}" for name in runner.SOURCE_DATA_CONTROL_FILES},
        )
        self.assertTrue(
            {
                "opening-2026092005.json",
                "temporal-2026092005.json",
                "ladder-generation-details.json",
                "test-generation-details.json",
            }.isdisjoint(hashed_names)
        )

    def test_result_payload_has_consumer_fields_and_honest_boundaries(self) -> None:
        digest = "a" * 64
        authority = {
            "base_source_result_sha256": digest,
            "base_source_result_seal_sha256": digest,
            "independent_result_sha256": digest,
            "independent_result_seal_sha256": digest,
            "census_result_sha256": digest,
            "census_result_seal_sha256": digest,
            "base_source_receipt_sha256": digest,
            "source_prereg_sha256": digest,
            "source_manifest_sha256": digest,
            "checkpoint_sha256": digest,
            "environment_source_sha256": digest,
            "reward_source_sha256": digest,
            "lambda_bits_per_j_hex": float(2.0).hex(),
            "interval_s_hex": float(30.08).hex(),
        }
        payload = runner._result_payload(
            status="PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION",
            authority_sha256=digest,
            authority=authority,
            selected=runner.CANDIDATE_SEED_ORDER[:2],
            schedule_hashes={str(seed): digest for seed in runner.CANDIDATE_SEED_ORDER[:2]},
            temporal_datasets={
                "2026092201": {
                    "path": "temporal-datasets/c2-train-2026092201.json",
                    "file_sha256": digest,
                    "dataset_sha256": digest,
                }
            },
            graph_report={"coverage_sufficient": True},
            generation_receipts=(),
        )
        self.assertEqual(payload["schema"], runner.RESULT_SCHEMA)
        self.assertEqual(payload["authority_sha256"], digest)
        self.assertEqual(payload["source_partition"], "TRAIN")
        self.assertIs(payload["held_out"], False)
        self.assertIs(payload["validation_dataset_bytes_opened"], False)
        self.assertIs(payload["test_split_opened"], False)
        self.assertIs(payload["held_out_ee_evaluated"], False)
        self.assertIs(payload["targets_or_validation_metrics_computed"], False)
        for field in (
            "base_source_result_sha256",
            "base_source_result_seal_sha256",
            "independent_result_sha256",
            "independent_result_seal_sha256",
            "census_result_sha256",
            "census_result_seal_sha256",
            "base_source_receipt_sha256",
            "source_prereg_sha256",
            "source_manifest_sha256",
            "checkpoint_sha256",
            "selected_seed_order",
            "selected_schedule_file_sha256s",
            "temporal_datasets",
            "temporal_dataset_paths",
            "temporal_dataset_file_sha256s",
            "temporal_dataset_sha256s",
            "final_c2_graph_report",
            "completion_status",
        ):
            self.assertIn(field, payload)

    def test_prepare_seal_must_cross_bind_result_and_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = {"schema": runner.AUTHORITY_SCHEMA}
            authority_sha256 = runner.source._write_once_json(
                root / "authority.json", authority
            )
            runner.source._write_once_json(
                root / "authority-seal.json",
                {
                    "schema": f"{runner.AUTHORITY_SCHEMA}{runner.SEAL_SUFFIX}",
                    "authority_sha256": authority_sha256,
                },
            )
            result = {
                "schema": runner.PREPARE_RESULT_SCHEMA,
                "authority_sha256": authority_sha256,
            }
            result_sha256 = runner.source._write_once_json(
                root / "prepare-result.json", result
            )
            runner.source._write_once_json(
                root / "prepare-result-seal.json",
                {
                    "schema": f"{runner.PREPARE_RESULT_SCHEMA}{runner.SEAL_SUFFIX}",
                    "result_file_sha256": result_sha256,
                    "authority_sha256": authority_sha256,
                },
            )
            loaded_authority, loaded_result, loaded_sha256 = runner._load_prepare(root)
            self.assertEqual(loaded_authority, authority)
            self.assertEqual(loaded_result, result)
            self.assertEqual(loaded_sha256, authority_sha256)

    def test_generation_source_uses_only_audited_c2_materializer_and_writer(self) -> None:
        text = (HERE / "run_v03_e1_c2_train_action_graph_expansion.py").read_text(
            encoding="utf-8"
        )
        generate_body = text.split("def generate(", 1)[1].split(
            "def _add_common_auth_args", 1
        )[0]
        self.assertEqual(generate_body.count("source._generate_c2_for_seed("), 1)
        self.assertEqual(generate_body.count("write_temporal_dataset("), 1)
        self.assertNotIn("_opening_corpus(", generate_body)
        self.assertNotIn("_freeze_lambda(", generate_body)
        self.assertNotIn("validation", " ".join(
            line.strip() for line in generate_body.splitlines()
            if "validation_dataset_bytes_opened" not in line
            and "targets_or_validation_metrics_computed" not in line
        ))


if __name__ == "__main__":
    unittest.main()
