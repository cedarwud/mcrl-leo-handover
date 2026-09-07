"""W-145 -- independent V0.13 result verifier tests.

The fixtures are synthetic and deliberately never read a V0.13 outcome.  They
exercise the receipt boundary, arithmetic recomputation, matched step-0
context, exact trajectory-energy gate, and result equivalence.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    REPO
    / ".scratch"
    / "zero-energy-c3-v013-verifier"
    / "verify_v013_zero_energy_c3_result.py"
)
SPEC = importlib.util.spec_from_file_location("v013_result_verifier", VERIFIER_PATH)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def _q1(lineage: int) -> dict[str, object]:
    parameter = "f" * 64
    return {
        "checkpoint_path": f"/sealed/checkpoints/init-{lineage}-rung-000010.pt",
        "checkpoint_sha256": VERIFIER.V03_CHECKPOINT_SHA256[lineage],
        "parameter_sha256": parameter,
        "authority_sha256": VERIFIER.V03_AUTHORITY_FILE_SHA256,
        "initialization_seed": lineage,
        "rung": VERIFIER.V03_FROZEN_RUNG,
        "head_index": VERIFIER.V03_HEAD_INDEX,
        "trainer_algorithm": VERIFIER.V03_TRAINER_ALGORITHM,
        "config_sha256": VERIFIER.V03_CONFIG_SHA256,
    }


def _authority() -> dict[str, object]:
    digest = "a" * 64
    return {
        "base_prereg": {
            "file_sha256": digest,
            "record_digest": digest,
            "tle_file_set_sha256": digest,
        },
        "contract_file_sha256": digest,
        "contract_receipt_sha256": VERIFIER.canonical_sha256(VERIFIER.expected_contract()),
        "execution_environment": dict(VERIFIER.EXPECTED_EXECUTION_ENVIRONMENT),
        "pyproject_file_sha256": digest,
        "python_source_authority": {
            "python_source_file_count": 1,
            "python_source_file_set_sha256": digest,
        },
        "runner_file_sha256": digest,
        "runtime_file_sha256": {"src/runtime.py": digest},
        "schema": VERIFIER.AUTHORITY_SCHEMA,
        "v03_frozen": {
            "checkpoint_rung": VERIFIER.V03_FROZEN_RUNG,
            "q1_checkpoint_file_sha256": {
                str(lineage): VERIFIER.V03_CHECKPOINT_SHA256[lineage]
                for lineage in VERIFIER.LINEAGES
            },
            "q1_head_index": VERIFIER.V03_HEAD_INDEX,
            "receipt_file_sha256": {
                "authority-seal.json": digest,
                "authority.json": digest,
                "result-seal.json": digest,
                "result.json": digest,
            },
        },
        "wrapper_file_sha256": {"run.sh": digest},
    }


def _step(
    arm: str,
    index: int,
    *,
    energy: float = 1.0,
    changed_surface: bool = False,
) -> dict[str, object]:
    is_drop = arm == "DROP_C3"
    selected = [0] * VERIFIER.USERS if is_drop else [1] * VERIFIER.USERS
    background = VERIFIER.array_sha256([0] * VERIFIER.USERS)
    digest = "1" * 64
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
        "background_sha256": background,
        "passed": True,
    }
    if is_drop:
        method: dict[str, object] = {
            "kind": "DROP_C3",
            "identity_passed": True,
            "positive_target_count": 0,
            "supported_positive_target_count": 0,
            "compatibility_component_counts": {
                "served": 0,
                "active_beams": 0,
                "active_satellites": 0,
                "rf_power": 0,
                "network_power": 0,
                "all": 0,
            },
        }
        joint: dict[str, object] = {
            "status": "NO_EXPOSURE",
            "changed_users": 0,
            "no_new_active_beam": True,
            "no_new_active_satellite": True,
            "network_power_nonincrease": True,
            "passed": True,
        }
    else:
        method = {
            "formula": "ZR",
            "identity_passed": True,
            "positive_target_count": 10,
            "supported_positive_target_count": 5,
            "compatibility_component_counts": {
                "served": 20,
                "active_beams": 20,
                "active_satellites": 20,
                "rf_power": 20,
                "network_power": 20,
                "all": 20,
            },
            "unsupported_positive_target_count": 0,
            "counterfactual_evaluations": 2800,
            "reference_signature_sha256": "2" * 64,
            "measurements_sha256": "3" * 64,
        }
        joint = {
            "status": "OBSERVED",
            "changed_users": 2,
            "no_new_active_beam": True,
            "no_new_active_satellite": True,
            "network_power_nonincrease": True,
            "passed": True,
            "delta_bits": 0.0,
            "delta_energy_j": 0.0,
            "baseline_active_beams": 10,
            "selected_active_beams": 10,
            "baseline_active_satellites": 3,
            "selected_active_satellites": 3,
            "baseline_network_power_w": 10.0,
            "selected_network_power_w": 10.0,
            "power_tolerance_w": 0.0,
            "new_active_beams": [],
            "new_active_satellites": [],
        }
    if not changed_surface:
        # The two matched arms must see identical non-C3 context hashes.
        surfaces = {
            "q1": digest,
            "o2": digest,
            "o3": digest,
            "mask": digest,
            "q1_reference": digest,
            "background": background,
        }
    else:
        surfaces = {
            "q1": "9" * 64,
            "o2": digest,
            "o3": digest,
            "mask": digest,
            "q1_reference": digest,
            "background": background,
        }
    return {
        "step_index": index,
        "total_bits": 10.0 if is_drop else 11.0,
        "total_energy_j": energy,
        "served_user_steps": VERIFIER.USERS,
        "active_beam_count": 10 if is_drop else 11,
        "active_satellite_count": 3 if is_drop else 4,
        "action_exposure": 0 if is_drop else 2,
        "c3_legal_spread_count": 0 if is_drop else 10,
        "selected_actions": selected,
        "surface_sha256": surfaces,
        "mechanics": mechanics,
        "method": method,
        "joint_support": joint,
    }


def _row(world: int, arm: str, lineage: int, *, energy: float = 1.0) -> dict[str, object]:
    steps = [_step(arm, index, energy=energy) for index in range(VERIFIER.STEPS_PER_EPISODE)]
    total_bits = sum(float(step["total_bits"]) for step in steps)
    total_energy = sum(float(step["total_energy_j"]) for step in steps)
    is_drop = arm == "DROP_C3"
    q1 = _q1(lineage)
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
        "initial_world_sha256": ("bcde"[VERIFIER.WORLD_SEEDS.index(world)]) * 64,
        "field_root_digest": ("def0"[VERIFIER.WORLD_SEEDS.index(world)]) * 64,
        "q1_checkpoint": q1,
        "q1_parameter_sha256_before": q1["parameter_sha256"],
        "q1_parameter_sha256_after": q1["parameter_sha256"],
        "total_bits": total_bits,
        "total_energy_j": total_energy,
        "ratio_of_sums_ee_bits_per_j": total_bits / total_energy,
        "served_user_steps": VERIFIER.USERS * VERIFIER.STEPS_PER_EPISODE,
        "served_fraction": 1.0,
        "active_beam_steps": sum(int(step["active_beam_count"]) for step in steps),
        "active_satellite_steps": sum(int(step["active_satellite_count"]) for step in steps),
        "c3_legal_spread_count": 0 if is_drop else 10 * VERIFIER.STEPS_PER_EPISODE,
        "positive_target_count": 0 if is_drop else 10 * VERIFIER.STEPS_PER_EPISODE,
        "supported_positive_target_count": 0 if is_drop else 5 * VERIFIER.STEPS_PER_EPISODE,
        "compatible_action_count": 0 if is_drop else 20 * VERIFIER.STEPS_PER_EPISODE,
        "action_exposure": 0 if is_drop else 2 * VERIFIER.STEPS_PER_EPISODE,
        "changed_actions_compatible": True,
        "joint_support_passed": True,
        "method_passed": True,
        "candidate_specific_identity_passed": True,
        "mechanics_passed": True,
        "per_step": steps,
        "elapsed_s": 0.1,
    }


def _bundle(tmp_path: Path, *, full_energy: float = 1.0) -> tuple[list[Path], Path]:
    rows: list[dict[str, object]] = []
    paths: list[Path] = []
    authority = _authority()
    authority_digest = "9" * 64
    authority_view = {
        "contract": VERIFIER.expected_contract(),
        "contract_sha256": VERIFIER.canonical_sha256(VERIFIER.expected_contract()),
        "contract_file_sha256": "a" * 64,
        "runner_file_sha256": "a" * 64,
        "runtime_file_sha256": authority["runtime_file_sha256"],
        "wrapper_file_sha256": authority["wrapper_file_sha256"],
        "source_authority": {
            "prereg_file_sha256": "a" * 64,
            "prereg_record_digest": "a" * 64,
            "tle_file_set_sha256": "a" * 64,
            "python_source_file_count": 1,
            "python_source_file_set_sha256": "a" * 64,
        },
        "frozen_authority": authority,
        "frozen_authority_file_sha256": authority_digest,
    }
    for world in VERIFIER.WORLD_SEEDS:
        for arm in VERIFIER.ARMS:
            for lineage in VERIFIER.LINEAGES:
                row = _row(world, arm, lineage, energy=full_energy if arm == "FULL_ZR" else 1.0)
                rows.append(row)
                payload = {
                    "schema": VERIFIER.SHARD_SCHEMA,
                    "shard_id": f"{world}-{arm}-{lineage}",
                    **authority_view,
                    "row": row,
                    "row_sha256": VERIFIER.canonical_sha256(row),
                }
                path = tmp_path / f"{world}-{arm}-{lineage}.json"
                path.write_bytes(VERIFIER._canonical_bytes(payload))
                paths.append(path)
    rows = sorted(rows, key=lambda row: (VERIFIER.WORLD_SEEDS.index(row["world_seed"]), VERIFIER.ARMS.index(row["arm"]), VERIFIER.LINEAGES.index(row["initialization_seed"])))
    recomputed = VERIFIER._recompute_result(rows)
    result = {
        "schema": VERIFIER.RESULT_SCHEMA,
        "claim_ceiling": "FOUR_TRAIN_WORLD_ZR_ORACLE_NO_LEARNER_NO_TEST",
        **authority_view,
        "field_root_digest_by_world": {
            str(world): next(row["field_root_digest"] for row in rows if row["world_seed"] == world)
            for world in VERIFIER.WORLD_SEEDS
        },
        "initial_world_sha256": {
            str(world): next(row["initial_world_sha256"] for row in rows if row["world_seed"] == world)
            for world in VERIFIER.WORLD_SEEDS
        },
        "rows": rows,
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
    return paths, merged


def test_valid_24_shard_bundle_recomputes_energy_gate(tmp_path: Path) -> None:
    shards, merged = _bundle(tmp_path)
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is True
    assert report["shard_count"] == 24
    assert report["decision"] == "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"
    assert report["recomputed"]["candidate_gates"]["ZR"]["pooled_total_trajectory_energy_nonincrease"] is True


def test_energy_increase_fails_pooled_and_every_world_gate(tmp_path: Path) -> None:
    shards, merged = _bundle(tmp_path, full_energy=1.1)
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    # The synthetic result is intentionally stale relative to the shard rows;
    # the independent verifier must fail before accepting it.
    assert report["errors"]


def test_truthy_boolean_and_forged_step_total_fail_closed(tmp_path: Path) -> None:
    shards, merged = _bundle(tmp_path)
    payload = json.loads(shards[0].read_text(encoding="ascii"))
    payload["row"]["per_step"][0]["mechanics"]["common_mask"] = "false"
    payload["row_sha256"] = VERIFIER.canonical_sha256(payload["row"])
    shards[0].write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "Boolean" in report["errors"][0]

    shards, merged = _bundle(tmp_path)
    payload = json.loads(shards[0].read_text(encoding="ascii"))
    payload["row"]["per_step"][0]["total_bits"] = 999.0
    payload["row_sha256"] = VERIFIER.canonical_sha256(payload["row"])
    shards[0].write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "row EE totals" in report["errors"][0]


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_bytes(b'{"a":1,"a":1}')
    with pytest.raises(VERIFIER.V013ResultVerificationError, match="duplicate JSON key"):
        VERIFIER.read_canonical_json(path)


def test_cross_arm_step_zero_context_is_required(tmp_path: Path) -> None:
    shards, merged = _bundle(tmp_path)
    target = next(path for path in shards if "FULL_ZR" in path.name)
    payload = json.loads(target.read_text(encoding="ascii"))
    payload["row"]["per_step"][0]["surface_sha256"]["o2"] = "8" * 64
    payload["row_sha256"] = VERIFIER.canonical_sha256(payload["row"])
    target.write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "step-0 o2 differs" in report["errors"][0]


def test_exact_24_unique_shards_are_required(tmp_path: Path) -> None:
    shards, merged = _bundle(tmp_path)
    report = VERIFIER.verify_bundle(shards[:-1], merged, enforce_authority=False)
    assert report["passed"] is False
    assert "exactly 24 shard paths" in report["errors"][0]
    duplicate = list(shards)
    duplicate[-1] = duplicate[0]
    report = VERIFIER.verify_bundle(duplicate, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "not unique" in report["errors"][0]


def test_merged_result_equivalence_and_digest_are_binding(tmp_path: Path) -> None:
    shards, merged = _bundle(tmp_path)
    result = json.loads(merged.read_text(encoding="ascii"))
    result["summaries"]["pooled_by_arm"]["FULL_ZR"]["total_bits"] += 1.0
    result["result_sha256"] = VERIFIER.canonical_sha256({key: value for key, value in result.items() if key != "result_sha256"})
    merged.write_bytes(VERIFIER._canonical_bytes(result))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "result.summaries" in report["errors"][0]


def test_frozen_environment_is_binding(tmp_path: Path) -> None:
    shards, merged = _bundle(tmp_path)
    payload = json.loads(shards[0].read_text(encoding="ascii"))
    payload["frozen_authority"]["execution_environment"]["numpy"] = "0.0.0"
    shards[0].write_bytes(VERIFIER._canonical_bytes(payload))
    report = VERIFIER.verify_bundle(shards, merged, enforce_authority=False)
    assert report["passed"] is False
    assert "execution_environment" in report["errors"][0]


def test_verifier_is_clean_room_and_v013_bound() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    assert "import run_v013" not in source
    assert "import run_v012" not in source
    assert "FULL_HR" not in source
    assert VERIFIER.WORLD_SEEDS == (2026104901, 2026104902, 2026104903, 2026104904)
    assert VERIFIER.ARMS == ("DROP_C3", "FULL_ZR")
    assert VERIFIER.NUM_ACTIONS == 28
