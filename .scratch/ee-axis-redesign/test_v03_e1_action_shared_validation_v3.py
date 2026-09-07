#!/usr/bin/env python3
"""Targeted, metric-free tests for the conditional V3 validation consumer."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

import numpy as np


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "action_shared_validation_v3_under_test",
    HERE / "run_v03_e1_action_shared_validation_v3.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load V3 validation consumer")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def batch(start: int, rows: int = 2) -> object:
    states = np.asarray(
        [[float(start + index), float(start + index + 1)] for index in range(rows)],
        dtype=np.float32,
    )
    reference = np.zeros(rows, dtype=np.int64)
    candidate = np.ones(rows, dtype=np.int64)
    targets = np.arange(start, start + rows, dtype=np.float64)
    masks = np.ones((rows, 4), dtype=np.bool_)
    return runner.EEAxisPairBatch(
        states=states,
        reference_actions=reference,
        candidate_actions=candidate,
        target_surplus_bits=targets,
        action_masks=masks,
    )


class FakeTemporalRow:
    def __init__(
        self, seed: int, identity: str, reference_action: int, candidate_action: int
    ) -> None:
        self.seed = seed
        self._identity = identity
        self.reference_action = reference_action
        self.candidate_action = candidate_action

    def verify(self) -> str:
        return self._identity


class V3BatchMutationTests(unittest.TestCase):
    def test_only_train_c2_is_rebuilt_and_validation_objects_are_retained(self) -> None:
        base = runner.E1LadderBatches(
            train=(batch(0), batch(10), batch(20)),
            validation=(batch(30), batch(40), batch(50)),
        )
        extra = batch(100, rows=3)
        config = SimpleNamespace(state_dim=2, action_dim=4)
        with mock.patch.object(
            runner,
            "build_temporal_route_batch",
            return_value=SimpleNamespace(pair_batch=extra),
        ):
            augmented, receipt = runner._append_train_c2_only(
                base, (object(),), config=config
            )
        self.assertIs(augmented.train[0], base.train[0])
        self.assertIs(augmented.train[2], base.train[2])
        self.assertIsNot(augmented.train[1], base.train[1])
        self.assertTrue(
            all(after is before for after, before in zip(augmented.validation, base.validation))
        )
        self.assertEqual(
            receipt["base_validation_batch_digests"],
            receipt["post_augmentation_validation_batch_digests"],
        )
        np.testing.assert_array_equal(
            augmented.train[1].states[: base.train[1].states.shape[0]],
            base.train[1].states,
        )
        np.testing.assert_array_equal(
            augmented.train[1].states[base.train[1].states.shape[0] :], extra.states
        )
        self.assertEqual(receipt["only_partition_mutated"], "TRAIN")
        self.assertEqual(receipt["only_route_mutated"], "C2")

    def test_recomputed_graph_requires_three_clusters_and_two_seeds(self) -> None:
        first, second = runner.EXPANSION_SEED_ORDER[:2]
        authority = {
            "original_c2_components": [[0, 1], [2, 3]],
            "original_unsupported_c2_pairs": [
                {"reference_action": 1, "candidate_action": 2}
            ],
        }
        rows = {
            first: (
                FakeTemporalRow(first, "a", 1, 4),
                FakeTemporalRow(first, "b", 1, 5),
                FakeTemporalRow(first, "c", 2, 6),
                FakeTemporalRow(first, "bridge", 4, 6),
            ),
            second: (
                FakeTemporalRow(second, "d", 1, 7),
                FakeTemporalRow(second, "e", 2, 8),
                FakeTemporalRow(second, "f", 2, 9),
            ),
        }
        report = runner._graph_report_from_rows(
            authority=authority, rows_by_seed=rows, action_dim=10
        )
        self.assertTrue(report["coverage_sufficient"])
        self.assertEqual(report["remaining_unsupported_validation_action_pairs"], [])
        self.assertEqual(report["needed_action_evidence"]["1"]["clusters"], 3)
        self.assertEqual(report["needed_action_evidence"]["2"]["clusters"], 3)
        one_seed = runner._graph_report_from_rows(
            authority=authority,
            rows_by_seed={first: rows[first]},
            action_dim=10,
        )
        self.assertFalse(one_seed["coverage_sufficient"])


class V3AuthorityTests(unittest.TestCase):
    def test_source_metadata_freezes_validation_digests_without_hashing_dataset_bytes(
        self,
    ) -> None:
        digest = "c" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "source-data"
            data.mkdir()
            manifest_body = {"schema": "synthetic-source-manifest-v1"}
            manifest_sha = runner.stable.sources._canonical_sha256(manifest_body)
            runner.stable.sources._write_once_json(
                root / "source-manifest.json",
                {**manifest_body, "source_manifest_sha256": manifest_sha},
            )
            split = {
                str(seed): name
                for seed, name in sorted(runner.stable.sources_v2.SOURCE_SEED_SPLIT.items())
            }
            prereg_body = {
                "schema": "synthetic-source-prereg-v1",
                "source_manifest_sha256": manifest_sha,
                "source_seed_split": split,
            }
            runner.stable.sources._write_once_json(
                root / "prereg.json",
                {
                    **prereg_body,
                    "prereg_sha256": runner.stable.sources._canonical_sha256(prereg_body),
                },
            )
            datasets = {
                seed: {
                    "opening_path": f"opening-{seed}.json",
                    "temporal_path": f"temporal-{seed}.json",
                    "opening_dataset_sha256": digest,
                    "temporal_dataset_sha256": digest,
                }
                for seed in split
            }
            index_sha = runner.stable.sources._write_once_json(
                data / "ladder-index.json",
                {
                    "schema": runner.stable.sources.LADDER_INDEX_SCHEMA,
                    "seed_split": split,
                    "datasets": datasets,
                    "test_split_opened": False,
                },
            )
            for seed, split_name in split.items():
                if split_name == "validation":
                    (data / f"opening-{seed}.json").write_bytes(b"opaque-opening")
                    (data / f"temporal-{seed}.json").write_bytes(b"opaque-temporal")
            receipt_sha = runner.stable.sources._write_once_json(
                data / "receipt.json",
                {
                    "status": "PASS",
                    "held_out_ee_evaluated": False,
                    "ladder_index_file_sha256": index_sha,
                    "opening_dataset_file_sha256s": {seed: digest for seed in split},
                    "opening_dataset_sha256s": {seed: digest for seed in split},
                    "temporal_dataset_file_sha256s": {seed: digest for seed in split},
                    "temporal_dataset_sha256s": {seed: digest for seed in split},
                },
            )
            supplement_sha = runner.stable.sources._write_once_json(
                root / "action-shared-supplement-receipt.json",
                {
                    "status": "PASS",
                    "test_outcomes_generated": False,
                    "test_split_opened": False,
                    "held_out_ee_evaluated": False,
                },
            )
            runner.stable.sources._write_once_json(
                root / "action-shared-supplement-receipt-seal.json",
                {
                    "schema": (
                        "multi-catfish-mcrl-v03-e1-action-shared-"
                        "source-supplement-seal-v1"
                    ),
                    "receipt_file_sha256": supplement_sha,
                },
            )
            independent = {
                "source_receipt_file_sha256": receipt_sha,
                "supplement_receipt_file_sha256": supplement_sha,
            }
            with mock.patch.object(
                runner, "_sha256", wraps=runner._sha256
            ) as hashed:
                _prereg, metadata = runner._source_metadata(
                    root, independent=independent
                )
            hashed_names = {Path(call.args[0]).name for call in hashed.call_args_list}
        self.assertIs(metadata["validation_dataset_bytes_opened"], False)
        self.assertEqual(len(metadata["validation_datasets"]), 3)
        self.assertFalse(
            any(name.startswith(("opening-", "temporal-")) for name in hashed_names)
        )

    def _expansion_files(
        self,
        root: Path,
        *,
        status: str,
        authority_schema: str | None = None,
        formal_runner_sha256: str | None = None,
    ) -> dict[str, str]:
        digest = "a" * 64
        first = runner.EXPANSION_SEED_ORDER[0]
        formal_sha = formal_runner_sha256 or runner._sha256(
            runner.REPO
            / ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_balanced_expansion.py"
        )
        authority = {
            "schema": authority_schema or runner.EXPANSION_AUTHORITY_SCHEMA,
            "status": "SEALED_BEFORE_SCHEDULE_TOPOLOGY_INSPECTION",
            "scope": "C2_TRAIN_ONLY_ACTION_BALANCED_SOURCE_REDESIGN_ONCE",
            "change_class": runner.EXPANSION_CHANGE_CLASS,
            "bounded_supplement_status": runner.EXPANSION_EXHAUSTED_STATUS,
            "candidate_seed_order": list(runner.EXPANSION_SEED_ORDER),
            "candidate_seed_partition": "TRAIN",
            "selection_rule": (
                "shortest-prefix-of-deterministic-action-balanced-train-schedules-"
                "by-action-topology-only"
            ),
            "candidate_schedule_maximum_clusters_per_seed": 50,
            "maximum_focal_users_per_world_anchor": 5,
            "action_first_clusters_per_needed_action_per_seed": 2,
            "published_schedule_minimum_clusters_per_seed": 12,
            "published_schedule_minimum_world_anchors_per_seed": 3,
            "minimum_clusters_per_needed_action": 3,
            "minimum_seeds_per_needed_action": 2,
            "replacement_seed_pool_authorized": False,
            "second_seed_pool_authorized": False,
            "outcome_or_target_fields_permitted_in_prepare": False,
            "runner_file_sha256": formal_sha,
            "implementation_file_sha256s": {
                "formal_action_balanced_runner": formal_sha,
                "exhausted_expansion_runner": runner._sha256(
                    runner.REPO
                    / ".scratch/ee-axis-redesign/run_v03_e1_c2_train_action_graph_expansion.py"
                ),
                "action_shared_source_runner": runner._sha256(
                    runner.REPO
                    / ".scratch/ee-axis-redesign/run_v03_e1_action_shared_sources.py"
                ),
                "c2_preoutcome_schedule_helper": runner._sha256(
                    runner.REPO / "src/mcrl/runtime/ee_axis_e1_c2_schedule.py"
                ),
                "temporal_dataset_helper": runner._sha256(
                    runner.REPO / "src/mcrl/runtime/ee_axis_temporal_dataset.py"
                ),
            },
            "original_c2_components": [[0, 1], [2, 3]],
            "original_unsupported_c2_pairs": [
                {"reference_action": 1, "candidate_action": 2}
            ],
            "validation_dataset_bytes_opened": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "source_prereg_sha256": digest,
            "source_manifest_sha256": digest,
            "checkpoint_sha256": digest,
            "base_source_receipt_sha256": digest,
            "base_source_result_sha256": digest,
            "base_source_result_seal_sha256": digest,
            "independent_result_sha256": digest,
            "independent_result_seal_sha256": digest,
            "census_result_sha256": digest,
            "census_result_seal_sha256": digest,
            "environment_source_sha256": digest,
            "reward_source_sha256": digest,
            **runner.EXPANSION_SEALED_RECEIPT_DIGESTS,
        }
        authority_sha = runner.stable.sources._write_once_json(
            root / "authority.json", authority
        )
        authority_seal_sha = runner.stable.sources._write_once_json(
            root / "authority-seal.json",
            {
                "schema": f"{authority['schema']}-seal",
                "authority_sha256": authority_sha,
            },
        )
        path = f"temporal-datasets/c2-train-{first}.json"
        graph = {
            "action_dim": 4,
            "original_unsupported_validation_action_pairs": [
                {"reference_action": 1, "candidate_action": 2}
            ],
            "coverage_sufficient": True,
            "remaining_unsupported_validation_action_pairs": [],
            "target_or_outcome_values_used_for_coverage_decision": False,
        }
        result = {
            "schema": runner.EXPANSION_RESULT_SCHEMA,
            "status": status,
            "completion_status": status,
            "authority_sha256": authority_sha,
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
            **runner.EXPANSION_SEALED_RECEIPT_DIGESTS,
            "source_partition": "TRAIN",
            "held_out": False,
            "replacement_seed_pool_used": False,
            "second_seed_pool_used": False,
            "validation_dataset_bytes_opened": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "targets_or_validation_metrics_computed": False,
            "selected_seed_order": [first],
            "selected_schedule_file_sha256s": {str(first): digest},
            "temporal_dataset_paths": {str(first): path},
            "temporal_dataset_file_sha256s": {str(first): digest},
            "temporal_dataset_sha256s": {str(first): digest},
            "temporal_datasets": {
                str(first): {
                    "path": path,
                    "file_sha256": digest,
                    "dataset_sha256": digest,
                    "rows": 10,
                    "source_partition": "TRAIN",
                    "held_out": False,
                }
            },
            "final_c2_graph_report": graph,
        }
        result_sha = runner.stable.sources._write_once_json(root / "result.json", result)
        result_seal_sha = runner.stable.sources._write_once_json(
            root / "result-seal.json",
            {
                "schema": f"{runner.EXPANSION_RESULT_SCHEMA}-seal",
                "result_file_sha256": result_sha,
                "authority_sha256": authority_sha,
            },
        )
        return {
            "authority": authority_sha,
            "authority_seal": authority_seal_sha,
            "result": result_sha,
            "result_seal": result_seal_sha,
        }

    def test_expansion_auth_is_conditional_on_final_pass_not_prepare_connectivity(self) -> None:
        digest = "a" * 64
        independent = {
            "result_file_sha256": digest,
            "result_seal_file_sha256": digest,
        }
        census = {
            "result_file_sha256": digest,
            "result_seal_file_sha256": digest,
            "routes": {
                "C2": {
                    "action_dim": 4,
                    "connected_components_with_edges": [[0, 1], [2, 3]],
                    "unsupported_validation_action_pairs": [
                        {"reference_action": 1, "candidate_action": 2}
                    ],
                }
            },
        }
        prereg = {
            "prereg_sha256": digest,
            "source_manifest_sha256": digest,
            "checkpoint_sha256": digest,
            "environment_source_sha256": digest,
            "reward_source_sha256": digest,
        }
        source_metadata = {
            "source_receipt_file_sha256": digest,
            "supplement_result_sha256": digest,
            "supplement_result_seal_sha256": digest,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._expansion_files(
                root, status="PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION"
            )
            loaded = runner._authenticate_expansion(
                root,
                expected_authority_sha256=hashes["authority"],
                expected_authority_seal_sha256=hashes["authority_seal"],
                expected_result_sha256=hashes["result"],
                expected_result_seal_sha256=hashes["result_seal"],
                independent=independent,
                census=census,
                prereg=prereg,
                source_metadata=source_metadata,
            )
            self.assertEqual(loaded["result"]["status"], "PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._expansion_files(root, status="INSUFFICIENT_COVERAGE")
            with self.assertRaisesRegex(
                runner.ActionSharedValidationV3Error, "expansion authority/result"
            ):
                runner._authenticate_expansion(
                    root,
                    expected_authority_sha256=hashes["authority"],
                    expected_authority_seal_sha256=hashes["authority_seal"],
                    expected_result_sha256=hashes["result"],
                    expected_result_seal_sha256=hashes["result_seal"],
                    independent=independent,
                    census=census,
                    prereg=prereg,
                    source_metadata=source_metadata,
                )

    def test_expansion_auth_rejects_failed_v1_authority_even_with_pass_result(self) -> None:
        digest = "a" * 64
        independent = {
            "result_file_sha256": digest,
            "result_seal_file_sha256": digest,
        }
        census = {
            "result_file_sha256": digest,
            "result_seal_file_sha256": digest,
            "routes": {
                "C2": {
                    "action_dim": 4,
                    "connected_components_with_edges": [[0, 1], [2, 3]],
                    "unsupported_validation_action_pairs": [
                        {"reference_action": 1, "candidate_action": 2}
                    ],
                }
            },
        }
        prereg = {
            "prereg_sha256": digest,
            "source_manifest_sha256": digest,
            "checkpoint_sha256": digest,
            "environment_source_sha256": digest,
            "reward_source_sha256": digest,
        }
        source_metadata = {
            "source_receipt_file_sha256": digest,
            "supplement_result_sha256": digest,
            "supplement_result_seal_sha256": digest,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._expansion_files(
                root,
                status="PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION",
                authority_schema=(
                    "multi-catfish-mcrl-v03-e1-c2-train-graph-expansion-authority-v1"
                ),
            )
            with self.assertRaisesRegex(
                runner.ActionSharedValidationV3Error, "expansion authority/result"
            ):
                runner._authenticate_expansion(
                    root,
                    expected_authority_sha256=hashes["authority"],
                    expected_authority_seal_sha256=hashes["authority_seal"],
                    expected_result_sha256=hashes["result"],
                    expected_result_seal_sha256=hashes["result_seal"],
                    independent=independent,
                    census=census,
                    prereg=prereg,
                    source_metadata=source_metadata,
                )

    def test_expansion_auth_rejects_unclosed_formal_runner_hash(self) -> None:
        digest = "a" * 64
        independent = {
            "result_file_sha256": digest,
            "result_seal_file_sha256": digest,
        }
        census = {
            "result_file_sha256": digest,
            "result_seal_file_sha256": digest,
            "routes": {
                "C2": {
                    "action_dim": 4,
                    "connected_components_with_edges": [[0, 1], [2, 3]],
                    "unsupported_validation_action_pairs": [
                        {"reference_action": 1, "candidate_action": 2}
                    ],
                }
            },
        }
        prereg = {
            "prereg_sha256": digest,
            "source_manifest_sha256": digest,
            "checkpoint_sha256": digest,
            "environment_source_sha256": digest,
            "reward_source_sha256": digest,
        }
        source_metadata = {
            "source_receipt_file_sha256": digest,
            "supplement_result_sha256": digest,
            "supplement_result_seal_sha256": digest,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._expansion_files(
                root,
                status="PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION",
                formal_runner_sha256="f" * 64,
            )
            with self.assertRaisesRegex(
                runner.ActionSharedValidationV3Error, "formal v2 implementation"
            ):
                runner._authenticate_expansion(
                    root,
                    expected_authority_sha256=hashes["authority"],
                    expected_authority_seal_sha256=hashes["authority_seal"],
                    expected_result_sha256=hashes["result"],
                    expected_result_seal_sha256=hashes["result_seal"],
                    independent=independent,
                    census=census,
                    prereg=prereg,
                    source_metadata=source_metadata,
                )

    def test_preoutcome_payload_binds_dependencies_code_and_false_boundaries(self) -> None:
        digest = "b" * 64
        dependencies = {
            "independent": {
                "result_file_sha256": digest,
                "result_seal_file_sha256": digest,
            },
            "census": {
                "result_file_sha256": digest,
                "result_seal_file_sha256": digest,
            },
            "source_metadata": {
                "source_receipt_file_sha256": digest,
                "validation_datasets": {},
            },
            "expansion": {
                "authority": {"runner_file_sha256": digest},
                "authority_sha256": digest,
                "authority_seal_sha256": digest,
                "result_sha256": digest,
                "result_seal_sha256": digest,
                "selected_seed_order": [runner.EXPANSION_SEED_ORDER[0]],
            },
        }
        manifest = {path: digest for path in runner.CODE_MANIFEST_PATHS}
        with mock.patch.object(runner, "_code_manifest", return_value=manifest):
            payload = runner.preoutcome_authority_payload(dependencies)
        self.assertEqual(payload["code_manifest"], manifest)
        self.assertEqual(payload["expansion_result_sha256"], digest)
        self.assertEqual(payload["expansion_result_seal_sha256"], digest)
        self.assertEqual(payload["expansion_runner_file_sha256"], digest)
        self.assertIs(payload["validation_dataset_bytes_opened"], False)
        self.assertIs(payload["validation_metrics_computed"], False)
        self.assertIs(payload["test_split_opened"], False)
        self.assertIs(payload["held_out_ee_evaluated"], False)

    def test_preoutcome_seal_binds_exact_authority_before_consumer_can_start(self) -> None:
        digest = "d" * 64
        dependencies = {
            "independent": {
                "result_file_sha256": digest,
                "result_seal_file_sha256": digest,
            },
            "census": {
                "result_file_sha256": digest,
                "result_seal_file_sha256": digest,
            },
            "source_metadata": {
                "source_receipt_file_sha256": digest,
                "validation_datasets": {},
            },
            "expansion": {
                "authority": {"runner_file_sha256": digest},
                "authority_sha256": digest,
                "authority_seal_sha256": digest,
                "result_sha256": digest,
                "result_seal_sha256": digest,
                "selected_seed_order": [runner.EXPANSION_SEED_ORDER[0]],
            },
        }
        manifest = {path: digest for path in runner.CODE_MANIFEST_PATHS}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(runner, "_code_manifest", return_value=manifest):
                payload = runner.preoutcome_authority_payload(dependencies)
                authority_sha = runner.stable.sources._write_once_json(
                    root / "authority.json", payload
                )
                seal_sha = runner.stable.sources._write_once_json(
                    root / "authority-seal.json",
                    {
                        "schema": runner.PREOUTCOME_SEAL_SCHEMA,
                        "authority_file_sha256": authority_sha,
                    },
                )
                loaded = runner._load_preoutcome_authority(
                    root / "authority.json",
                    root / "authority-seal.json",
                    expected_authority_sha256=authority_sha,
                    expected_seal_sha256=seal_sha,
                )
                self.assertEqual(loaded, payload)
                with self.assertRaisesRegex(
                    runner.ActionSharedValidationV3Error, "authority bytes changed"
                ):
                    runner._load_preoutcome_authority(
                        root / "authority.json",
                        root / "authority-seal.json",
                        expected_authority_sha256="e" * 64,
                        expected_seal_sha256=seal_sha,
                    )

    def test_runner_authenticates_external_authority_before_dataset_load_or_metrics(self) -> None:
        body = inspect.getsource(runner.run)
        self.assertLess(body.index("_load_preoutcome_authority("), body.index("stable._load_batches("))
        self.assertLess(body.index("_load_preoutcome_authority("), body.index("_execute_metrics("))
        self.assertLess(body.index("authority-seal.json"), body.index("_execute_metrics("))

    def test_builder_source_has_no_metric_execution(self) -> None:
        builder = (
            HERE / "build_v03_e1_action_shared_validation_v3_authority.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("_execute_metrics(", builder)
        self.assertNotIn("_route_metrics(", builder)
        self.assertNotIn("q_values(", builder)


if __name__ == "__main__":
    unittest.main()
