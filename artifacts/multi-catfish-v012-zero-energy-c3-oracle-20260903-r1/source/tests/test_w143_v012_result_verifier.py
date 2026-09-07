"""W-143 -- independent V0.12 oracle receipt verification."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    REPO
    / ".scratch"
    / "zero-energy-c3-v012"
    / "verify_v012_zero_energy_c3_result.py"
)
SPEC = importlib.util.spec_from_file_location("v012_result_verifier", VERIFIER_PATH)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def _row(world: int, arm: str, lineage: int, *, bad: bool = False) -> dict[str, object]:
    is_drop = arm == "DROP_C3"
    step_bits = 1000.0 if is_drop else (900.0 if bad else 1100.0)
    step_energy = 100.0
    step_served = 100
    step_beams = 10 if is_drop else 9
    step_sats = 4 if is_drop else 3
    step_exposure = 0 if is_drop else 2
    mechanics = {
        "live_state_and_rng_unchanged": True,
        "common_mask": True,
        "reference_rows_exact_zero": True,
        "illegal_rows_exact_zero": True,
        "opening_service_gate_equal": True,
        "o2_immutable": True,
        "changed_actions_compatible": True,
        "changed_actions_strictly_positive_c3": True,
        "joint_support_passed": True,
        "background_sha256": "a" * 64,
        "passed": True,
    }
    method = {
        "kind": "DROP_C3" if is_drop else ("ZR" if arm == "FULL_ZR" else "HR"),
        "identity_passed": True,
        "positive_target_count": 0 if is_drop else 10,
        "supported_positive_target_count": 0 if is_drop else 5,
        "compatibility_component_counts": {
            "served": 0 if is_drop else 20,
            "active_beams": 0 if is_drop else 20,
            "active_satellites": 0 if is_drop else 20,
            "rf_power": 0 if is_drop else 20,
            "network_power": 0 if is_drop else 20,
            "all": 0 if is_drop else 20,
        },
    }
    if not is_drop:
        method["formula"] = "ZR" if arm == "FULL_ZR" else "HR"
    joint = {
        "status": "NO_EXPOSURE" if is_drop else "OBSERVED",
        "changed_users": 0 if is_drop else 2,
        "no_new_active_beam": True,
        "no_new_active_satellite": True,
        "network_power_nonincrease": True,
        "passed": True,
    }
    steps = []
    for index in range(VERIFIER.STEPS_PER_EPISODE):
        steps.append(
            {
                "step_index": index,
                "total_bits": step_bits,
                "total_energy_j": step_energy,
                "served_user_steps": step_served,
                "active_beam_count": step_beams,
                "active_satellite_count": step_sats,
                "action_exposure": step_exposure,
                "selected_actions": [0] * VERIFIER.USERS,
                "surface_sha256": {
                    "q1": "1" * 64,
                    "o2": "2" * 64,
                    "o3": "3" * 64,
                    "mask": "4" * 64,
                    "q1_reference": "5" * 64,
                    "background": "6" * 64,
                },
                "mechanics": mechanics,
                "method": method,
                "joint_support": joint,
            }
        )
    total_bits = step_bits * VERIFIER.STEPS_PER_EPISODE
    total_energy = step_energy * VERIFIER.STEPS_PER_EPISODE
    return {
        "schema": VERIFIER.EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": lineage,
        "world_seed": world,
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "users": VERIFIER.USERS,
        "steps": VERIFIER.STEPS_PER_EPISODE,
        "initial_world_sha256": "b" * 64 if world == VERIFIER.WORLD_SEEDS[0] else "c" * 64,
        "field_root_digest": "d" * 64 if world == VERIFIER.WORLD_SEEDS[0] else "e" * 64,
        "q1_checkpoint": {
            "checkpoint_path": f"/sealed/checkpoints/init-{lineage}-rung-000010.pt",
            "checkpoint_sha256": VERIFIER.V03_CHECKPOINT_SHA256[lineage],
            "parameter_sha256": "f" * 64,
            "authority_sha256": VERIFIER.V03_AUTHORITY_FILE_SHA256,
            "initialization_seed": lineage,
            "rung": VERIFIER.V03_FROZEN_RUNG,
            "head_index": VERIFIER.V03_HEAD_INDEX,
            "trainer_algorithm": VERIFIER.V03_TRAINER_ALGORITHM,
            "config_sha256": VERIFIER.V03_CONFIG_SHA256,
        },
        "q1_parameter_sha256_before": "f" * 64,
        "q1_parameter_sha256_after": "f" * 64,
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": step_served * VERIFIER.STEPS_PER_EPISODE,
        "served_fraction": 1.0,
        "active_beam_steps": step_beams * VERIFIER.STEPS_PER_EPISODE,
        "active_satellite_steps": step_sats * VERIFIER.STEPS_PER_EPISODE,
        "c3_legal_spread_count": 0 if is_drop else 10,
        "positive_target_count": 0 if is_drop else 10 * VERIFIER.STEPS_PER_EPISODE,
        "supported_positive_target_count": 0 if is_drop else 5 * VERIFIER.STEPS_PER_EPISODE,
        "compatible_action_count": 0 if is_drop else 20 * VERIFIER.STEPS_PER_EPISODE,
        "action_exposure": step_exposure * VERIFIER.STEPS_PER_EPISODE,
        "changed_actions_compatible": True,
        "joint_support_passed": True,
        "method_passed": True,
        "candidate_specific_identity_passed": True,
        "mechanics_passed": True,
        "per_step": steps,
        "elapsed_s": 0.01,
    }


def _write_bundle(tmp_path: Path, *, fail_zr: bool = False) -> tuple[list[Path], Path]:
    shard_paths: list[Path] = []
    rows: list[dict[str, object]] = []
    for world in VERIFIER.WORLD_SEEDS:
        for arm in VERIFIER.ARMS:
            for lineage in VERIFIER.LINEAGES:
                bad = fail_zr and arm == "FULL_ZR" and lineage != VERIFIER.LINEAGES[-1]
                row = _row(world, arm, lineage, bad=bad)
                rows.append(row)
                payload = {
                    "schema": VERIFIER.SHARD_SCHEMA,
                    "shard_id": f"{world}-{arm}-{lineage}",
                    "row": row,
                    "row_sha256": VERIFIER.canonical_sha256(row),
                }
                path = tmp_path / f"{world}-{arm}-{lineage}.json"
                path.write_bytes(VERIFIER._canonical_bytes(payload))
                shard_paths.append(path)
    rows = sorted(
        rows,
        key=lambda row: (
            VERIFIER.WORLD_SEEDS.index(int(row["world_seed"])),
            VERIFIER.ARMS.index(str(row["arm"])),
            VERIFIER.LINEAGES.index(int(row["initialization_seed"])),
        ),
    )
    recomputed = VERIFIER._recompute_result(rows)
    result: dict[str, object] = {
        "schema": VERIFIER.RESULT_SCHEMA,
        "claim_ceiling": "TWO_TRAIN_WORLD_ORDERED_ORACLE_NO_LEARNER_NO_TEST",
        "contract": VERIFIER.expected_contract(),
        "contract_sha256": VERIFIER.canonical_sha256(VERIFIER.expected_contract()),
        "rows": rows,
        "field_root_digest_by_world": {
            str(world): next(
                str(row["field_root_digest"]) for row in rows if int(row["world_seed"]) == world
            )
            for world in VERIFIER.WORLD_SEEDS
        },
        "initial_world_sha256": {
            str(world): next(
                str(row["initial_world_sha256"]) for row in rows if int(row["world_seed"]) == world
            )
            for world in VERIFIER.WORLD_SEEDS
        },
        "summaries": {
            "pooled_by_arm": recomputed["pooled_by_arm"],
            "pooled_by_world_and_arm": recomputed["pooled_by_world_and_arm"],
            "candidate_gates": recomputed["candidate_gates"],
        },
        "gate": recomputed["gate"],
    }
    result["result_sha256"] = VERIFIER.canonical_sha256(result)
    merged = tmp_path / "result.json"
    merged.write_bytes(VERIFIER._canonical_bytes(result))
    return shard_paths, merged


def test_complete_bundle_recomputes_both_gates_and_prefers_zr(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is True
    assert report["decision"] == "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"
    assert report["pass_zr"] is True
    assert report["pass_hr"] is True
    assert report["coverage"]["exact"] is True


def test_failed_zr_is_not_rescued_by_hr_and_order_is_recomputed(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path, fail_zr=True)
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is True
    assert report["pass_zr"] is False
    assert report["pass_hr"] is True
    assert report["decision"] == "GO_HR_C3_LEARNABILITY_PREREG_ONLY"


def test_tampered_row_digest_fails_closed(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    payload = json.loads(shards[0].read_text(encoding="ascii"))
    payload["row"]["total_bits"] = 999.0
    shards[0].write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "row digest failed" in report["errors"][0]


def test_mechanics_passed_is_recomputed_from_constituents(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    payload = json.loads(shards[0].read_text(encoding="ascii"))
    payload["row"]["per_step"][0]["mechanics"]["common_mask"] = False
    payload["row"]["per_step"][0]["mechanics"]["passed"] = True
    payload["row_sha256"] = VERIFIER.canonical_sha256(payload["row"])
    shards[0].write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "mechanics.passed is inconsistent" in report["errors"][0]


def test_joint_support_passed_is_recomputed_from_three_components(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    payload = json.loads(shards[0].read_text(encoding="ascii"))
    payload["row"]["per_step"][0]["joint_support"]["no_new_active_beam"] = False
    payload["row"]["per_step"][0]["joint_support"]["passed"] = True
    payload["row_sha256"] = VERIFIER.canonical_sha256(payload["row"])
    shards[0].write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "joint_support.passed is inconsistent" in report["errors"][0]


def test_production_direct_api_requires_tle_root(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    report = VERIFIER.verify_bundle(
        shards,
        merged,
        v03_root=REPO
        / "artifacts"
        / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1",
        enforce_authority=True,
    )
    assert report["passed"] is False
    assert "requires --tle-root" in report["errors"][0]


def test_q1_checkpoint_parameter_sha_is_bound_to_row_hashes(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    payload = json.loads(shards[0].read_text(encoding="ascii"))
    payload["row"]["q1_checkpoint"]["parameter_sha256"] = "0" * 64
    payload["row_sha256"] = VERIFIER.canonical_sha256(payload["row"])
    shards[0].write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "parameter SHA disagrees" in report["errors"][0]


def test_missing_or_duplicate_coverage_fails_closed(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    report = VERIFIER.verify_bundle(shards[:-1], merged, enforce_authority=False)
    assert report["passed"] is False
    assert "exactly 18 shard paths" in report["errors"][0]
    duplicate = list(shards)
    duplicate[-1] = duplicate[0]
    report = VERIFIER.verify_bundle(duplicate, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "coverage is not exact" in report["errors"][0]


def test_merged_result_digest_and_pool_mismatch_fail_closed(tmp_path: Path) -> None:
    shards, merged = _write_bundle(tmp_path)
    result = json.loads(merged.read_text(encoding="ascii"))
    result["summaries"]["pooled_by_arm"]["FULL_ZR"]["total_bits"] += 1.0
    result["result_sha256"] = VERIFIER.canonical_sha256(
        {key: value for key, value in result.items() if key != "result_sha256"}
    )
    merged.write_bytes(VERIFIER._canonical_bytes(result))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "result.summaries" in report["errors"][0]


def test_current_contract_is_explicit_and_verifier_does_not_import_runner() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    assert "import run_v012" not in source
    assert "importlib" not in source
    assert "_pair_gate(" in source
    assert VERIFIER.expected_contract()["candidate_order"] == ["ZR", "HR"]


def test_authority_check_calls_independent_contract_builder_without_shadowing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = {
        "contract_file_sha256": "a" * 64,
        "runner_file_sha256": "b" * 64,
        "runtime_file_sha256": {"runtime.py": "c" * 64},
        "source_authority": {
            "prereg_file_sha256": "d" * 64,
            "prereg_record_digest": "e" * 64,
            "tle_file_set_sha256": "f" * 64,
            "python_source_file_count": 1,
            "python_source_file_set_sha256": "1" * 64,
        },
        "tle_source_checked": True,
    }
    monkeypatch.setattr(VERIFIER, "current_authority", lambda **_kwargs: current)
    contract = VERIFIER.expected_contract()
    payload = {
        "contract": contract,
        "contract_sha256": VERIFIER.canonical_sha256(contract),
        "contract_file_sha256": current["contract_file_sha256"],
        "runner_file_sha256": current["runner_file_sha256"],
        "runtime_file_sha256": current["runtime_file_sha256"],
        "source_authority": current["source_authority"],
    }
    report = VERIFIER._check_authority(
        [payload],
        repo=tmp_path,
        contract_path=None,
        runner_path=None,
        prereg_path=None,
        runtime_paths=None,
        tle_root=tmp_path,
    )
    assert report["checked"] is True
    assert report["contract_sha256"] == VERIFIER.canonical_sha256(contract)


def test_q1_source_authority_checks_sealed_rung_head_and_checkpoint_bytes() -> None:
    rows = [
        _row(world, arm, lineage)
        for world in VERIFIER.WORLD_SEEDS
        for arm in VERIFIER.ARMS
        for lineage in VERIFIER.LINEAGES
    ]
    authority = VERIFIER._check_q1_sources(
        rows,
        v03_root=REPO
        / "artifacts"
        / "multi-catfish-v03-e1-masked-meanmax-fallback-20260901-r1",
    )
    assert authority["checked"] is True
    assert authority["rung"] == 10
    assert authority["head_index"] == 0
    assert set(authority["checkpoint_file_sha256s"]) == {
        str(seed) for seed in VERIFIER.LINEAGES
    }
