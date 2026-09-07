#!/usr/bin/env python3
"""Fast contract tests for the formal C2 action-balanced source redesign."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "c2_action_balanced_expansion_under_test",
    HERE / "run_v03_e1_c2_train_action_balanced_expansion.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load action-balanced expansion runner")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def topology_cluster(
    seed: int,
    identity: str,
    reference: int,
    candidate: int,
    *,
    anchor_step: int,
    focal_user: int,
) -> dict[str, object]:
    return {
        "source_seed": seed,
        "cluster_sha256": identity,
        "reference_action": reference,
        "candidate_action": candidate,
        "world_anchor_sha256": f"anchor-{seed}-{anchor_step}",
        "anchor_step": anchor_step,
        "focal_user": focal_user,
    }


class ActionBalancedSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = runner.CANDIDATE_SEED_ORDER[0]
        self.needed = (0, 4, 7, 9, 14, 18)

    def balanced_candidates(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for index, action in enumerate(self.needed * 2):
            rows.append(
                topology_cluster(
                    self.seed,
                    f"needed-{action}-{index}",
                    action,
                    19 if action != 19 else 17,
                    anchor_step=index // 4,
                    focal_user=index % 4,
                )
            )
        for index in range(12, 20):
            rows.append(
                topology_cluster(
                    self.seed,
                    f"fill-{index}",
                    1,
                    2,
                    anchor_step=index // 4,
                    focal_user=index % 4,
                )
            )
        return rows

    def test_constants_keep_pool_caps_and_redundancy_gate_fixed(self) -> None:
        self.assertEqual(
            runner.CANDIDATE_SEED_ORDER,
            tuple(range(2026092201, 2026092221)),
        )
        self.assertEqual(runner.CANDIDATE_MAXIMUM_CLUSTERS_PER_SEED, 50)
        self.assertEqual(runner.MAXIMUM_FOCAL_USERS_PER_WORLD_ANCHOR, 5)
        self.assertEqual(runner.ACTION_FIRST_CLUSTERS_PER_SEED, 2)
        self.assertEqual(runner.PUBLISHED_MINIMUM_CLUSTERS_PER_SEED, 12)
        self.assertEqual(runner.PUBLISHED_MINIMUM_WORLD_ANCHORS_PER_SEED, 3)
        self.assertEqual(runner.MIN_CLUSTERS_PER_NEEDED_ACTION, 3)
        self.assertEqual(runner.MIN_SEEDS_PER_NEEDED_ACTION, 2)
        self.assertEqual(
            runner._sealed_receipt_digests(),
            {
                "failed_expansion_authority_sha256": (
                    "feaddcc8b5ada02cc09f8bedf56cb7f0823bf422031f9235a371c89c39140ffa"
                ),
                "failed_expansion_authority_seal_sha256": (
                    "ea4f12b9efb6bcc361c9d3fa15a5116b8d72ac398aee6cdaa5659f0e3f4c3131"
                ),
                "failed_expansion_prepare_result_sha256": (
                    "ffc9a2cb9b89413f9f4be70991f2b3aa978a9476251e8b0e30718f5d7392e87d"
                ),
                "failed_expansion_prepare_result_seal_sha256": (
                    "055cf6be00221c355e2a03f70f36ca1b0b8822618ee5ee8983cd15c32072cdcd"
                ),
                "legal_probe_receipt_file_sha256": (
                    "265dec78460ac22b81159cf9dba968319ac2774642599c8d6eb5cc8a62643044"
                ),
            },
        )

    def test_selector_is_deterministic_first_two_then_minimum_fill(self) -> None:
        candidates = self.balanced_candidates()
        selected, receipt = runner._select_action_balanced_clusters(
            source_seed=self.seed,
            clusters=reversed(candidates),
            needed_actions=self.needed,
        )
        selected_again, receipt_again = runner._select_action_balanced_clusters(
            source_seed=self.seed,
            clusters=candidates,
            needed_actions=self.needed,
        )
        identities = [row["cluster_sha256"] for row in selected]
        self.assertEqual(
            identities,
            [row["cluster_sha256"] for row in selected_again],
        )
        self.assertEqual(receipt, receipt_again)
        self.assertGreaterEqual(len(selected), 12)
        self.assertGreaterEqual(receipt["selected_world_anchors"], 3)
        self.assertFalse(receipt["target_or_outcome_values_used"])
        for action in self.needed:
            evidence = receipt["action_selection_evidence"][str(action)]
            self.assertEqual(len(evidence["selected_first_cluster_sha256s"]), 2)
            self.assertTrue(evidence["quota_filled_when_available"])

    def test_selector_fills_to_twelve_and_three_anchors_when_actions_overlap(self) -> None:
        rows = [
            topology_cluster(
                self.seed,
                f"row-{index}",
                0 if index < 2 else 1,
                4 if index < 2 else 2,
                anchor_step=index // 4,
                focal_user=index % 4,
            )
            for index in range(16)
        ]
        selected, receipt = runner._select_action_balanced_clusters(
            source_seed=self.seed,
            clusters=rows,
            needed_actions=(0, 4),
        )
        self.assertEqual(len(selected), 12)
        self.assertEqual(receipt["selected_world_anchors"], 3)

    def test_selector_rejects_focal_cap_violation(self) -> None:
        rows = [
            topology_cluster(
                self.seed,
                f"same-anchor-{index}",
                0,
                4,
                anchor_step=0,
                focal_user=index,
            )
            for index in range(6)
        ]
        with self.assertRaisesRegex(
            runner.C2ActionBalancedExpansionError, "five-focal"
        ):
            runner._select_action_balanced_clusters(
                source_seed=self.seed,
                clusters=rows,
                needed_actions=(0, 4),
            )

    def test_selector_rejects_candidate_schedule_over_fifty(self) -> None:
        rows = [
            topology_cluster(
                self.seed,
                f"row-{index}",
                0,
                4,
                anchor_step=index // 5,
                focal_user=index % 5,
            )
            for index in range(51)
        ]
        with self.assertRaisesRegex(
            runner.C2ActionBalancedExpansionError, "exceeds cap 50"
        ):
            runner._select_action_balanced_clusters(
                source_seed=self.seed,
                clusters=rows,
                needed_actions=(0, 4),
            )

    def test_connectivity_alone_still_fails_unchanged_redundancy_gate(self) -> None:
        first = runner.CANDIDATE_SEED_ORDER[0]
        report = runner._coverage_report(
            action_dim=6,
            original_components=((0,), (4,)),
            unsupported_pairs=((0, 4),),
            clusters_by_seed={
                first: (
                    {
                        "source_seed": first,
                        "cluster_sha256": "bridge",
                        "reference_action": 0,
                        "candidate_action": 4,
                    },
                )
            },
        )
        self.assertEqual(report["remaining_unsupported_validation_action_pairs"], [])
        self.assertFalse(report["coverage_sufficient"])
        self.assertEqual(report["minimum_clusters_per_needed_action"], 3)
        self.assertEqual(report["minimum_seeds_per_needed_action"], 2)


class FailedExpansionAuthenticationTests(unittest.TestCase):
    digest = "a" * 64

    def _write_failed_receipt(
        self,
        root: Path,
        *,
        status: str = "INSUFFICIENT_COVERAGE",
        remaining: list[dict[str, int]] | None = None,
    ) -> dict[str, str]:
        dependencies = {
            "base_source_result_sha256": self.digest,
            "base_source_result_seal_sha256": self.digest,
            "independent_result_sha256": self.digest,
            "independent_result_seal_sha256": self.digest,
            "census_result_sha256": self.digest,
            "census_result_seal_sha256": self.digest,
        }
        authority = {
            "schema": runner.FAILED_AUTHORITY_SCHEMA,
            "status": "SEALED_BEFORE_SCHEDULE_TOPOLOGY_INSPECTION",
            "scope": "C2_TRAIN_ONLY_ACTION_GRAPH_COVERAGE_EXPANSION_ONCE",
            "runner_file_sha256": runner._sha256(runner.BASE_EXPANSION_RUNNER),
            "base_prereg_file_sha256": runner._sha256(runner.source.BASE_PREREG),
            **dependencies,
            "candidate_seed_order": list(runner.CANDIDATE_SEED_ORDER),
            "candidate_seed_partition": "TRAIN",
            "selection_rule": "shortest-prefix-by-schedule-action-topology-only",
            "minimum_clusters_per_needed_action": 3,
            "minimum_seeds_per_needed_action": 2,
            "replacement_seed_pool_authorized": False,
            "outcome_or_target_fields_permitted_in_prepare": False,
            "validation_dataset_bytes_opened": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "original_c2_components": [[0], [4]],
            "original_unsupported_c2_pairs": [
                {"reference_action": 0, "candidate_action": 4}
            ],
        }
        authority_sha = runner.source._write_once_json(root / "authority.json", authority)
        authority_seal_sha = runner.source._write_once_json(
            root / "authority-seal.json",
            {
                "schema": f"{runner.FAILED_AUTHORITY_SCHEMA}-seal",
                "authority_sha256": authority_sha,
            },
        )
        graph = {
            "decision_basis": "schedule-action-topology-only",
            "action_dim": 6,
            "original_unsupported_validation_action_pairs": [
                {"reference_action": 0, "candidate_action": 4}
            ],
            "remaining_unsupported_validation_action_pairs": (
                [] if remaining is None else remaining
            ),
            "needed_actions": [0, 4],
            "needed_action_evidence": {
                "0": {
                    "clusters": 2,
                    "seeds": list(runner.CANDIDATE_SEED_ORDER[:2]),
                    "meets_minimum_clusters": False,
                    "meets_minimum_seeds": True,
                },
                "4": {
                    "clusters": 3,
                    "seeds": list(runner.CANDIDATE_SEED_ORDER[:2]),
                    "meets_minimum_clusters": True,
                    "meets_minimum_seeds": True,
                },
            },
            "minimum_clusters_per_needed_action": 3,
            "minimum_seeds_per_needed_action": 2,
            "coverage_sufficient": False,
            "target_or_outcome_values_used_for_coverage_decision": False,
            "generated_outcomes_materialized": False,
        }
        prepared = {
            "schema": runner.FAILED_PREPARE_RESULT_SCHEMA,
            "status": status,
            "authority_sha256": authority_sha,
            **dependencies,
            "selected_seed_order": [],
            "selected_schedule_file_sha256s": {},
            "all_inspected_schedule_file_sha256s": {
                str(seed): self.digest for seed in runner.CANDIDATE_SEED_ORDER
            },
            "temporal_datasets": {},
            "temporal_dataset_paths": {},
            "temporal_dataset_file_sha256s": {},
            "temporal_dataset_sha256s": {},
            "final_c2_graph_report": graph,
            "candidate_seed_order": list(runner.CANDIDATE_SEED_ORDER),
            "replacement_seed_pool_used": False,
            "main_networks_bitwise_unchanged": True,
            "main_replay_unchanged": True,
            "generation_attempted": False,
            "validation_dataset_bytes_opened": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
        }
        prepare_sha = runner.source._write_once_json(
            root / "prepare-result.json", prepared
        )
        prepare_seal_sha = runner.source._write_once_json(
            root / "prepare-result-seal.json",
            {
                "schema": f"{runner.FAILED_PREPARE_RESULT_SCHEMA}-seal",
                "result_file_sha256": prepare_sha,
                "authority_sha256": authority_sha,
            },
        )
        return {
            "authority": authority_sha,
            "authority_seal": authority_seal_sha,
            "prepare": prepare_sha,
            "prepare_seal": prepare_seal_sha,
        }

    def _authenticate(self, root: Path, hashes: dict[str, str]) -> dict[str, object]:
        return runner._authenticate_failed_expansion(
            root,
            expected_authority_sha256=hashes["authority"],
            expected_authority_seal_sha256=hashes["authority_seal"],
            expected_prepare_result_sha256=hashes["prepare"],
            expected_prepare_result_seal_sha256=hashes["prepare_seal"],
        )

    def test_accepts_only_exhausted_connectivity_restored_redundancy_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._write_failed_receipt(root)
            loaded = self._authenticate(root, hashes)
        self.assertEqual(loaded["prepared"]["status"], "INSUFFICIENT_COVERAGE")
        self.assertEqual(
            set(loaded["prepared"]["all_inspected_schedule_file_sha256s"]),
            {str(seed) for seed in runner.CANDIDATE_SEED_ORDER},
        )

    def test_rejects_old_prepare_go_or_disconnected_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._write_failed_receipt(
                root, status="READY_FOR_ONE_TIME_GENERATION"
            )
            with self.assertRaisesRegex(
                runner.C2ActionBalancedExpansionError, "closure"
            ):
                self._authenticate(root, hashes)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._write_failed_receipt(
                root,
                remaining=[{"reference_action": 0, "candidate_action": 4}],
            )
            with self.assertRaisesRegex(
                runner.C2ActionBalancedExpansionError, "connectivity-only"
            ):
                self._authenticate(root, hashes)

    def test_rejects_any_generated_outcome_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hashes = self._write_failed_receipt(root)
            (root / "generation-attempt.json").write_text("{}", encoding="ascii")
            with self.assertRaisesRegex(
                runner.C2ActionBalancedExpansionError, "generated outcomes"
            ):
                self._authenticate(root, hashes)


class LegalProbeAndArtifactTests(unittest.TestCase):
    def _probe_payload(self, needed: tuple[int, ...]) -> dict[str, object]:
        return {
            "schema": runner.LEGAL_PROBE_SCHEMA,
            "status": "DESIGN_DIAGNOSTIC_ONLY",
            "source_seeds": list(runner.CANDIDATE_SEED_ORDER),
            "maximum_focal_users_per_world_anchor": 5,
            "maximum_scheduled_clusters_per_seed": 50,
            "target_values_read": False,
            "pair_outcomes_materialized": False,
            "validation_dataset_documents_opened": False,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
            "receipts": [
                {"source_seed": seed} for seed in runner.CANDIDATE_SEED_ORDER
            ],
            "needed_action_evidence": {
                str(action): {
                    "clusters": 3,
                    "seeds": list(runner.CANDIDATE_SEED_ORDER[:2]),
                }
                for action in needed
            },
            "pair_counts": {},
        }

    def test_legal_probe_must_bind_fixed_pool_caps_and_unchanged_gate(self) -> None:
        needed = (0, 4, 7, 9, 14, 18)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "probe.json"
            digest = runner.source._write_once_json(path, self._probe_payload(needed))
            loaded = runner._authenticate_legal_probe(
                path, digest, needed_actions=needed
            )
        self.assertEqual(loaded["maximum_scheduled_clusters_per_seed"], 50)

    def test_legal_probe_accepts_exact_hash_bound_pretty_json_receipt(self) -> None:
        needed = (0, 4, 7, 9, 14, 18)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "probe.json"
            path.write_text(
                json.dumps(
                    self._probe_payload(needed),
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=True,
                )
                + "\n",
                encoding="utf-8",
            )
            digest = runner._sha256(path)
            loaded = runner._authenticate_legal_probe(
                path, digest, needed_actions=needed
            )
        self.assertEqual(loaded["status"], "DESIGN_DIAGNOSTIC_ONLY")

    def test_result_payload_is_train_only_and_binds_failed_receipt(self) -> None:
        digest = "b" * 64
        authority = {
            **{field: digest for field in (
                "base_source_result_sha256",
                "base_source_result_seal_sha256",
                "independent_result_sha256",
                "independent_result_seal_sha256",
                "census_result_sha256",
                "census_result_seal_sha256",
                "failed_expansion_authority_sha256",
                "failed_expansion_authority_seal_sha256",
                "failed_expansion_prepare_result_sha256",
                "failed_expansion_prepare_result_seal_sha256",
                "legal_probe_receipt_file_sha256",
                "base_source_receipt_sha256",
                "source_prereg_sha256",
                "source_manifest_sha256",
                "checkpoint_sha256",
                "environment_source_sha256",
                "reward_source_sha256",
            )},
            "lambda_bits_per_j_hex": float(2.0).hex(),
            "interval_s_hex": float(30.08).hex(),
        }
        seed = runner.CANDIDATE_SEED_ORDER[0]
        payload = runner._result_payload(
            status="PASS_TRAIN_ONLY_C2_GRAPH_EXPANSION",
            authority_sha256=digest,
            authority=authority,
            selected=(seed,),
            schedule_hashes={str(seed): digest},
            temporal_datasets={
                str(seed): {
                    "path": f"temporal-datasets/c2-train-{seed}.json",
                    "file_sha256": digest,
                    "dataset_sha256": digest,
                }
            },
            graph_report={"coverage_sufficient": True},
            generation_receipts=(),
        )
        self.assertEqual(payload["schema"], runner.RESULT_SCHEMA)
        self.assertEqual(payload["source_partition"], "TRAIN")
        self.assertIs(payload["held_out"], False)
        self.assertIs(payload["validation_dataset_bytes_opened"], False)
        self.assertIs(payload["test_split_opened"], False)
        self.assertIs(payload["held_out_ee_evaluated"], False)
        self.assertEqual(payload["failed_expansion_authority_sha256"], digest)

    def test_authority_is_written_before_any_formal_topology_scan(self) -> None:
        text = (
            HERE / "run_v03_e1_c2_train_action_balanced_expansion.py"
        ).read_text(encoding="utf-8")
        prepare_body = text.split("def prepare(", 1)[1].split("def _load_prepare", 1)[0]
        self.assertLess(
            prepare_body.index('source._write_once_json(output_dir / "authority.json"'),
            prepare_body.index("source._discover_c2_schedule("),
        )

    def test_generate_uses_only_existing_c2_materializer_and_writer(self) -> None:
        text = (
            HERE / "run_v03_e1_c2_train_action_balanced_expansion.py"
        ).read_text(encoding="utf-8")
        generate_body = text.split("def generate(", 1)[1].split(
            "def _add_common_paths", 1
        )[0]
        self.assertEqual(generate_body.count("source._generate_c2_for_seed("), 1)
        self.assertEqual(generate_body.count("write_temporal_dataset("), 1)
        self.assertNotIn("_opening_corpus(", generate_body)
        self.assertNotIn("_freeze_lambda(", generate_body)


if __name__ == "__main__":
    unittest.main()
