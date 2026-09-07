from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "gate_receipt_validator", HERE / "gate_receipt_validator.py"
)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)


def _endpoint(
    branch: str,
    seed: int,
    ee: float,
    *,
    checkpoint: str,
    digest: str,
    training_seed: int = 700,
) -> dict:
    steps = 10
    users = 100
    duration = steps * V.DECISION_STEP_S
    bits = ee * 100.0
    energy = 100.0
    served = 950
    total = steps * users
    return {
        "arm": branch,
        "checkpoint_sha256": digest,
        "training_seed": training_seed,
        "evaluation_seed": seed,
        "users": users,
        "steps": steps,
        "duration_s": duration,
        "useful_bits": bits,
        "system_energy_j": energy,
        "system_ee_bits_per_j": ee,
        "mean_system_power_w": energy / duration,
        "mean_system_throughput_bps": bits / duration,
        "served_user_intervals": served,
        "total_user_intervals": total,
        "served_fraction": served / total,
        "zero_power_intervals": 0,
        "zero_service_intervals": 0,
        "r1_sum": ee,
        "r2_sum": -1.0,
        "r3_sum": -2.0,
    }


def _fixture(tmp_path: Path) -> tuple[Path, dict, dict]:
    """Build a complete non-C1 receipt to exercise generic validation.

    C1 chain verification is covered by production artifacts when available;
    this fixture intentionally uses C2 so the generic receipt contract can be
    tested without depending on an ephemeral /tmp corpus.
    """

    authority_paths: dict[str, Path] = {}
    authority: dict[str, str] = {}
    for field in (
        "spec_sha256",
        "runner_sha256",
        "method_sha256",
        "concept_sha256",
        "run_short_ep_sha256",
        "routing_core_sha256",
        "roles_sha256",
        "prereg_sha256",
    ):
        path = tmp_path / f"{field}.authority"
        path.write_text(field + "\n", encoding="utf-8")
        authority_paths[field] = path
        authority[field] = V.sha256_file(path)

    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"synthetic checkpoint bytes\n")
    checkpoint_sha = V.sha256_file(checkpoint)

    seeds = tmp_path / "seeds.json"
    seed_payload = {
        "schema": "smc-er-c2-main-consumer-gate-seeds-v1",
        "status": "frozen",
        **authority,
        "training_seed": 700,
        "environment_seed": 701,
        "mobility_seed": 702,
        "evaluation_seeds": [703, 704, 705, 706, 707],
    }
    seeds.write_text(json.dumps(seed_payload, sort_keys=True) + "\n", encoding="utf-8")
    authority["seed_manifest_path"] = str(seeds)
    authority["seed_manifest_sha256"] = V.sha256_file(seeds)

    paired = []
    for seed in seed_payload["evaluation_seeds"]:
        informed = _endpoint(
            "informed", seed, 11.0, checkpoint=str(checkpoint), digest=checkpoint_sha
        )
        neutral = _endpoint(
            "neutral", seed, 10.0, checkpoint=str(checkpoint), digest=checkpoint_sha
        )
        paired.append(
            {
                "evaluation_seed": seed,
                "informed": informed,
                "neutral": neutral,
                "delta_ee_bits_per_j": 1.0,
            }
        )
    raw = {
        "schema": "smc-er-c2-main-consumer-gate-raw-v1",
        "status": "complete",
        "claim_ceiling": "C2_ROUTE_FOR_ONE_SEED_4EP_DEVELOPMENTAL_PREVIEW_ONLY",
        "initial_main_parity": {
            "status": "PASS",
            "exact_after_descriptive_metadata_normalisation": True,
            "first_difference": None,
        },
        "paired_rows": paired,
        "branch_results": {
            branch: {
                "episodes": 4,
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": checkpoint_sha,
                "gates": {"C1": "shadow", "C2": "route", "C3": "shadow"},
            }
            for branch in ("informed", "neutral")
        },
    }
    raw_path = tmp_path / "raw.json"
    raw_path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    authority["raw_rows_path"] = str(raw_path)
    authority["raw_rows_sha256"] = V.sha256_file(raw_path)

    metrics = {
        "paired_deltas_bits_per_j": [1.0] * 5,
        "mean_paired_delta_bits_per_j": 1.0,
        "positive_seed_count": 5,
        "informed_ratio_of_sums_ee_bits_per_j": 11.0,
        "neutral_ratio_of_sums_ee_bits_per_j": 10.0,
        "aggregate_delta_bits_per_j": 1.0,
        "informed_served_fraction": 0.95,
        "neutral_served_fraction": 0.95,
        "served_fraction_delta": 0.0,
    }
    checks = {
        "all_structural_guards": True,
        "mean_paired_delta_positive": True,
        "positive_on_at_least_four_seeds": True,
        "aggregate_ratio_of_sums_delta_positive": True,
        "served_fraction_guard": True,
    }
    result = {
        "schema": V.RESULT_SCHEMA,
        "source": "C2",
        "status": "PASS",
        "decision": "ROUTE",
        "prerequisites_closed": True,
        "claim_ceiling": "C2_ROUTE_FOR_ONE_SEED_4EP_DEVELOPMENTAL_PREVIEW_ONLY",
        "checks": checks,
        "guard_failures": [],
        "metrics": metrics,
        "protocol": {
            "episodes": 4,
            "training_users": 100,
            "evaluation_users": 100,
            "evaluation_seed_count": 5,
            "main_only_evaluation": True,
            "routed_sources": ["C2"],
            "neutral_source": "matched_uniform_C2",
            "service_guard": 0.005,
        },
        "authority": authority,
    }
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    return result_path, result, authority_paths


def test_complete_generic_receipt_returns_parsed_evidence(tmp_path: Path):
    path, _result, authority_paths = _fixture(tmp_path)
    evidence = V.validate_main_consumer_result(
        path,
        expected_source="C2",
        repo_root=tmp_path,
        authority_paths=authority_paths,
    )
    assert evidence["source"] == "C2"
    assert evidence["decision"] == "ROUTE"
    assert evidence["metrics_recomputed"]["positive_seed_count"] == 5
    assert evidence["paired_rows"] == 5


def test_tampered_raw_values_fail_even_when_self_attested_hash_is_updated(tmp_path: Path):
    path, result, authority_paths = _fixture(tmp_path)
    raw_path = Path(result["authority"]["raw_rows_path"])
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["paired_rows"][0]["informed"]["useful_bits"] = 9999.0
    raw_path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    result["authority"]["raw_rows_sha256"] = V.sha256_file(raw_path)
    path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(V.GateReceiptValidationError) as excinfo:
        V.validate_main_consumer_result(
            path,
            expected_source="C2",
            repo_root=tmp_path,
            authority_paths=authority_paths,
        )
    assert any("recomputation mismatch" in item for item in excinfo.value.failures)


def test_missing_raw_file_fails_closed(tmp_path: Path):
    path, result, authority_paths = _fixture(tmp_path)
    Path(result["authority"]["raw_rows_path"]).unlink()
    with pytest.raises(V.GateReceiptValidationError) as excinfo:
        V.validate_main_consumer_result(
            path,
            expected_source="C2",
            repo_root=tmp_path,
            authority_paths=authority_paths,
        )
    assert any("authority.raw_rows" in item for item in excinfo.value.failures)


def test_failed_initial_main_parity_cannot_be_hidden_by_a_pass_result(tmp_path: Path):
    path, result, authority_paths = _fixture(tmp_path)
    raw_path = Path(result["authority"]["raw_rows_path"])
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["initial_main_parity"] = {
        "status": "FAIL",
        "exact_after_descriptive_metadata_normalisation": False,
        "first_difference": "q_networks.0",
    }
    raw_path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    result["authority"]["raw_rows_sha256"] = V.sha256_file(raw_path)
    path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(V.GateReceiptValidationError) as excinfo:
        V.validate_main_consumer_result(
            path,
            expected_source="C2",
            repo_root=tmp_path,
            authority_paths=authority_paths,
        )
    assert any("initial_main_parity" in item for item in excinfo.value.failures)


def test_equal_self_attested_minimal_pass_is_rejected(tmp_path: Path):
    path = tmp_path / "minimal.json"
    path.write_text(
        json.dumps(
            {
                "schema": V.RESULT_SCHEMA,
                "source": "C2",
                "status": "PASS",
                "decision": "ROUTE",
                "prerequisites_closed": True,
                "claim_ceiling": "C2_ROUTE_FOR_ONE_SEED_4EP_DEVELOPMENTAL_PREVIEW_ONLY",
                "authority": {
                    "raw_rows_path": str(path),
                    "raw_rows_sha256": "0" * 64,
                    "seed_manifest_path": str(path),
                    "seed_manifest_sha256": "0" * 64,
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(V.GateReceiptValidationError) as excinfo:
        V.validate_main_consumer_result(path, expected_source="C2", repo_root=tmp_path)
    assert any("self-referential authority" in item for item in excinfo.value.failures)
    assert any("authority.spec_sha256" in item for item in excinfo.value.failures)


def test_c1_receipt_requires_the_independent_source_and_corpus_chain(tmp_path: Path):
    source_result = Path(
        "/tmp/smc-er-c1-source-gate-a-20260827-v1/c1-source-gate-a-result.json"
    )
    corpus_manifest = Path(
        "/tmp/smc-er-c1-exp-corpus-20260827-v1/c1-exp-corpus-manifest.json"
    )
    corpus_verification = corpus_manifest.parent / "verification.json"
    checkpoint = Path(
        "/home/u24/papers/mcrl-leo-handover/artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt"
    )
    if not all(path.is_file() for path in (source_result, corpus_manifest, corpus_verification, checkpoint)):
        pytest.skip("sealed C1 source/corpus artifacts are not present in this checkout")

    code_paths = V._canonical_authority_paths(V.REPO, source="C1")
    authority = {
        field: V.sha256_file(path) for field, path in code_paths.items()
    }
    manifest = json.loads(corpus_manifest.read_text(encoding="utf-8"))
    authority.update(
        {
            "source_gate_result_sha256": V.sha256_file(source_result),
            "corpus_manifest_sha256": V.sha256_file(corpus_manifest),
            "corpus_verification_sha256": V.sha256_file(corpus_verification),
            "c1_exp_corpus_sha256": manifest["corpus_sha256"],
        }
    )
    training_seed = 9000001
    eval_seeds = [9000003, 9000004, 9000005, 9000006, 9000007]
    seed_path = tmp_path / "c1-seeds.json"
    seed_path.write_text(
        json.dumps(
            {
                "schema": V.C1_SEED_SCHEMA,
                "status": "frozen",
                **authority,
                "training_seed": training_seed,
                "environment_seed": 9000002,
                "mobility_seed": 9000008,
                "evaluation_seeds": eval_seeds,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    authority["seed_manifest_path"] = str(seed_path)
    authority["seed_manifest_sha256"] = V.sha256_file(seed_path)
    checkpoint_sha = V.sha256_file(checkpoint)
    paired = []
    for seed in eval_seeds:
        informed = _endpoint(
            "informed",
            seed,
            11.0,
            checkpoint=str(checkpoint),
            digest=checkpoint_sha,
            training_seed=training_seed,
        )
        neutral = _endpoint(
            "neutral",
            seed,
            10.0,
            checkpoint=str(checkpoint),
            digest=checkpoint_sha,
            training_seed=training_seed,
        )
        paired.append(
            {
                "evaluation_seed": seed,
                "informed": informed,
                "neutral": neutral,
                "delta_ee_bits_per_j": 1.0,
            }
        )
    prefill = {
        "bundles": 34,
        "corpus_manifest": str(corpus_manifest),
        "corpus_manifest_sha256": V.sha256_file(corpus_manifest),
        "corpus_sha256": manifest["corpus_sha256"],
        "enters_main": False,
    }
    raw = {
        "schema": V.C1_RAW_SCHEMA,
        "status": "complete",
        "claim_ceiling": V.C1_CLAIM_CEILING,
        "initial_main_parity": {
            "status": "PASS",
            "exact_after_descriptive_metadata_normalisation": True,
            "first_difference": None,
        },
        "paired_rows": paired,
        "branch_results": {
            branch: {
                "episodes": 4,
                "checkpoint": str(checkpoint),
                "checkpoint_sha256": checkpoint_sha,
                "gates": {"C1": "route", "C2": "shadow", "C3": "shadow"},
                "c1_prefill": {
                    **prefill,
                    "corpus_branch": "local" if branch == "informed" else "control",
                },
            }
            for branch in ("informed", "neutral")
        },
    }
    raw_path = tmp_path / "c1-raw.json"
    raw_path.write_text(json.dumps(raw, sort_keys=True) + "\n", encoding="utf-8")
    authority["raw_rows_path"] = str(raw_path)
    authority["raw_rows_sha256"] = V.sha256_file(raw_path)
    result = {
        "schema": V.RESULT_SCHEMA,
        "source": "C1",
        "status": "PASS",
        "decision": "ROUTE",
        "prerequisites_closed": True,
        "claim_ceiling": V.C1_CLAIM_CEILING,
        "guard_failures": [],
        "checks": {
            "all_structural_guards": True,
            "mean_paired_delta_positive": True,
            "positive_on_at_least_four_seeds": True,
            "aggregate_ratio_of_sums_delta_positive": True,
            "served_fraction_guard": True,
        },
        "metrics": {
            "paired_deltas_bits_per_j": [1.0] * 5,
            "mean_paired_delta_bits_per_j": 1.0,
            "positive_seed_count": 5,
            "informed_ratio_of_sums_ee_bits_per_j": 11.0,
            "neutral_ratio_of_sums_ee_bits_per_j": 10.0,
            "aggregate_delta_bits_per_j": 1.0,
            "informed_served_fraction": 0.95,
            "neutral_served_fraction": 0.95,
            "served_fraction_delta": 0.0,
        },
        "protocol": {
            "episodes": 4,
            "training_users": 100,
            "evaluation_users": 100,
            "evaluation_seed_count": 5,
            "main_only_evaluation": True,
            "routed_sources": ["C1"],
            "neutral_source": "matched_uniform_C1",
            "service_guard": 0.005,
        },
        "authority": authority,
    }
    result_path = tmp_path / "c1-result.json"
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    try:
        evidence = V.validate_main_consumer_result(result_path, expected_source="C1")
    except V.GateReceiptValidationError as exc:
        # This fixture points to a historical /tmp chain.  Once one of its
        # current bound authorities drifts, fail-closed rejection is the
        # expected result; it must never be silently grandfathered.
        assert any("C1 Source Gate A" in failure for failure in exc.failures)
        return
    assert evidence["c1_chain"]["source_gate_verification"]["status"] == "PASS"
    assert evidence["c1_chain"]["corpus"]["corpus_sha256"] == manifest["corpus_sha256"]
