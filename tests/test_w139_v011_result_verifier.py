"""W-139 -- outcome-independent V0.11 result receipt verification."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
VERIFIER_PATH = REPO / ".scratch" / "joint-c3-v011" / "verify_v011_result.py"


def _module():
    spec = importlib.util.spec_from_file_location("v011_result_verifier_w139", VERIFIER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _method(verifier, arm: str) -> dict[str, object]:
    digest = "a" * 64
    if arm == "DROP_C3":
        return {"kind": "DROP_C3", "status": "BASE"}
    if arm == "FULL_M1D":
        return {
            "kind": "M1D",
            "status": "CONVERGED",
            "sweep_count": 1,
            "changed_per_sweep": [0],
            "final_iterate_sha256": digest,
            "production_sha256": digest,
            "cycles_detected": False,
            "identity_passed": True,
            "q1_vs_exact_o1": {},
            "g_bm_minus_g_b0_bits": 0.0,
        }
    if arm == "FULL_AP":
        return {
            "kind": "AP_MONE",
            "status": "CONSTRUCTED",
            "permutation_sha256": digest,
            "proposal_sha256": digest,
            "proposal_flips_from_background": 0,
            "selected_flips_from_proposal": 0,
            "identity_passed": True,
            "order_credited_sum_bits": [0.0, 0.0],
            "order_joint_surplus_bits": [0.0, 0.0],
            "order_identity_residual_bits": [0.0, 0.0],
            "executed_flips_from_background": 1,
            "executed_flips_from_proposal": 1,
            "executed_antithetic_credited_sum_bits": 0.0,
            "executed_joint_surplus_bits": 1.0,
            "executed_joint_minus_credited_bits": 1.0,
        }
    if arm == "DIAG_O_DROP":
        return {
            "kind": "EXACT_O1_DROP",
            "drop_status": "CONVERGED",
            "drop_sweep_count": 1,
            "drop_changed_per_sweep": [0],
            "identity_passed": True,
        }
    assert arm == "DIAG_O_FULL"
    return {
        "kind": "EXACT_O1_FULL",
        "drop_status": "CONVERGED",
        "drop_sweep_count": 1,
        "drop_changed_per_sweep": [0],
        "full_status": "CONVERGED",
        "full_sweep_count": 1,
        "full_changed_per_sweep": [0],
        "monotonicity_violations": 0,
        "identity_passed": True,
    }


def _step(verifier, arm: str, index: int, *, bits: float, energy: float) -> dict[str, object]:
    exposed = arm != "DROP_C3"
    opening = {
        "status": "OBSERVED" if exposed else "NO_EXPOSURE",
        "changed_users": 1 if exposed else 0,
        "delta_bits": 1.0 if exposed else 0.0,
        "delta_energy_j": 0.0,
        "fixed_lambda_surplus_bits": 1.0 if exposed else 0.0,
    }
    mechanics = {
        "live_state_unchanged": True,
        "common_mask": True,
        "reference_rows_exact_zero": True,
        "opening_service_gate_equal": True,
        "background_sha256": "b" * 64,
        "passed": True,
    }
    return {
        "step_index": index,
        "total_bits": bits,
        "total_energy_j": energy,
        "served_user_steps": 100,
        "hold_rate": None,
        "active_beam_count": 1,
        "action_exposure": 1 if exposed else 0,
        "selected_actions": [0] * verifier.USERS,
        "surface_sha256": {
            "q1": "a" * 64,
            "o2": "a" * 64,
            "o1": "a" * 64,
            "o3": "a" * 64,
            "mask": "a" * 64,
            "q1_reference": "a" * 64,
            "background": "a" * 64,
        },
        "mechanics": mechanics,
        "method": _method(verifier, arm),
        "joint_opening": opening,
    }


def _row(verifier, arm: str, lineage: int, *, total_bits: float) -> dict[str, object]:
    q1 = verifier.EXPECTED_Q1_CHECKPOINTS[lineage]
    per_step_bits = total_bits / verifier.STEPS_PER_EPISODE
    per_step_energy = 10.0
    steps = [
        _step(verifier, arm, index, bits=per_step_bits, energy=per_step_energy)
        for index in range(verifier.STEPS_PER_EPISODE)
    ]
    return {
        "schema": verifier.EPISODE_SCHEMA,
        "arm": arm,
        "initialization_seed": lineage,
        "world_seed": verifier.WORLD_SEED,
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "users": verifier.USERS,
        "steps": verifier.STEPS_PER_EPISODE,
        "initial_world_sha256": "d" * 64,
        "field_root_digest": verifier.EXPECTED_FIELD_ROOT_DIGEST,
        "q1_checkpoint": {
            "checkpoint_path": "frozen-q1.ckpt",
            "checkpoint_sha256": q1["checkpoint_sha256"],
            "authority_sha256": "e" * 64,
            "initialization_seed": lineage,
            "rung": 10,
            "head_index": 0,
            "trainer_algorithm": "synthetic-frozen-meanmax",
            "config_sha256": "f" * 64,
            "parameter_sha256": q1["parameter_sha256"],
        },
        "q1_parameter_sha256_before": q1["parameter_sha256"],
        "q1_parameter_sha256_after": q1["parameter_sha256"],
        "total_bits": total_bits,
        "total_energy_j": per_step_energy * verifier.STEPS_PER_EPISODE,
        "ratio_of_sums_ee_bits_per_j": total_bits / (per_step_energy * verifier.STEPS_PER_EPISODE),
        "served_user_steps": verifier.USERS * verifier.STEPS_PER_EPISODE,
        "served_fraction": 1.0,
        "c3_legal_spread_count": verifier.STEPS_PER_EPISODE if arm != "DROP_C3" else 0,
        "action_exposure": verifier.STEPS_PER_EPISODE if arm != "DROP_C3" else 0,
        "joint_opening_exposed_count": verifier.STEPS_PER_EPISODE if arm != "DROP_C3" else 0,
        "joint_opening_negative_count": 0,
        "method_passed": True,
        "candidate_specific_identity_passed": True,
        "mechanics_passed": True,
        "per_step": steps,
        "elapsed_s": 0.0,
    }


def _result(verifier, *, ap_bits: float = 120.0, m1d_bits: float = 110.0, o_bits: float = 110.0) -> dict[str, object]:
    bits_by_arm = {
        "DROP_C3": 100.0,
        "FULL_M1D": m1d_bits,
        "FULL_AP": ap_bits,
        "DIAG_O_DROP": 100.0,
        "DIAG_O_FULL": o_bits,
    }
    rows = [
        _row(verifier, arm, lineage, total_bits=bits_by_arm[arm])
        for arm in verifier.ARMS
        for lineage in verifier.LINEAGES
    ]
    contract = verifier._frozen_contract()
    result: dict[str, object] = {
        "schema": verifier.RESULT_SCHEMA,
        "claim_ceiling": verifier.CLAIM_CEILING,
        "contract": contract,
        "contract_sha256": verifier.EXPECTED_CONTRACT_SHA256,
        "contract_file_sha256": verifier.EXPECTED_CONTRACT_FILE_SHA256,
        "runner_file_sha256": verifier.EXPECTED_RUNNER_FILE_SHA256,
        "runtime_file_sha256": dict(verifier.EXPECTED_RUNTIME_FILE_SHA256),
        "field_root_digest": verifier.EXPECTED_FIELD_ROOT_DIGEST,
        "initial_world_sha256": "d" * 64,
        "rows": rows,
    }
    # The producer's merge payload is authenticated by the same independent
    # recomputation used by the verifier.  Calling the gate code here would
    # make this fixture accidentally test the implementation under test.
    by_arm = {arm: [row for row in rows if row["arm"] == arm] for arm in verifier.ARMS}
    pooled = {
        arm: {
            "row_count": 3,
            "total_bits": sum(float(row["total_bits"]) for row in by_arm[arm]),
            "total_energy_j": sum(float(row["total_energy_j"]) for row in by_arm[arm]),
            "ratio_of_sums_ee_bits_per_j": sum(float(row["total_bits"]) for row in by_arm[arm])
            / sum(float(row["total_energy_j"]) for row in by_arm[arm]),
            "served_user_steps": sum(int(row["served_user_steps"]) for row in by_arm[arm]),
            "served_fraction": 1.0,
        }
        for arm in verifier.ARMS
    }

    def pair(label: str, full_arm: str, drop_arm: str) -> dict[str, object]:
        full = pooled[full_arm]
        drop = pooled[drop_arm]
        by_lineage: dict[str, object] = {}
        for lineage in verifier.LINEAGES:
            f = next(row for row in rows if row["arm"] == full_arm and row["initialization_seed"] == lineage)
            d = next(row for row in rows if row["arm"] == drop_arm and row["initialization_seed"] == lineage)
            delta = float(f["ratio_of_sums_ee_bits_per_j"]) - float(d["ratio_of_sums_ee_bits_per_j"])
            by_lineage[str(lineage)] = {
                "delta_ee_bits_per_j": delta,
                "relative_delta_ee": delta / float(d["ratio_of_sums_ee_bits_per_j"]),
                "delta_served_user_steps": 0,
            }
        full_rows = by_arm[full_arm]
        drop_rows = by_arm[drop_arm]
        spread = sum(int(row["c3_legal_spread_count"]) for row in full_rows)
        exposure = sum(int(row["action_exposure"]) for row in full_rows)
        exposed = sum(int(row["joint_opening_exposed_count"]) for row in full_rows)
        negative = sum(int(row["joint_opening_negative_count"]) for row in full_rows)
        hard_stops: list[str] = []
        if not float(full["ratio_of_sums_ee_bits_per_j"]) > float(drop["ratio_of_sums_ee_bits_per_j"]):
            hard_stops.append(f"{label} pooled EE is not strictly positive")
        positive = sum(float(by_lineage[str(lineage)]["delta_ee_bits_per_j"]) > 0.0 for lineage in verifier.LINEAGES)
        service = sum(int(by_lineage[str(lineage)]["delta_served_user_steps"]) >= 0 for lineage in verifier.LINEAGES)
        return {
            "label": label,
            "full_arm": full_arm,
            "drop_arm": drop_arm,
            "passed": not hard_stops,
            "pooled": {
                "delta_ee_bits_per_j": float(full["ratio_of_sums_ee_bits_per_j"]) - float(drop["ratio_of_sums_ee_bits_per_j"]),
                "relative_delta_ee": (float(full["ratio_of_sums_ee_bits_per_j"]) - float(drop["ratio_of_sums_ee_bits_per_j"])) / float(drop["ratio_of_sums_ee_bits_per_j"]),
                "delta_served_user_steps": 0,
            },
            "by_lineage": by_lineage,
            "positive_lineages": positive,
            "service_noninferior_lineages": service,
            "pooled_service_noninferior": True,
            "mechanics_passed": all(bool(row["mechanics_passed"]) for row in (*full_rows, *drop_rows)),
            "method_passed": all(bool(row["method_passed"]) for row in (*full_rows, *drop_rows)),
            "candidate_specific_identity_passed": all(bool(row["candidate_specific_identity_passed"]) for row in (*full_rows, *drop_rows)),
            "c3_legal_spread_count": spread,
            "action_exposure": exposure,
            "joint_opening_exposed_count": exposed,
            "joint_opening_negative_count": negative,
            "hard_stops": hard_stops,
        }

    gates = {
        "AP": pair("AP", "FULL_AP", "DROP_C3"),
        "M1D": pair("M1D", "FULL_M1D", "DROP_C3"),
        "O": pair("O", "DIAG_O_FULL", "DIAG_O_DROP"),
    }
    decision = verifier.ordered_decision(
        passed_ap=bool(gates["AP"]["passed"]),
        passed_m1d=bool(gates["M1D"]["passed"]),
        passed_o=bool(gates["O"]["passed"]),
    )
    result["summaries"] = {"pooled_by_arm": pooled, "candidate_gates": gates}
    result["gate"] = {
        "decision": decision,
        "pass_ap": bool(gates["AP"]["passed"]),
        "pass_m1d": bool(gates["M1D"]["passed"]),
        "pass_exact_o": bool(gates["O"]["passed"]),
        "ordered_selection_ap_before_m1d": True,
    }
    result["result_sha256"] = verifier.canonical_sha256(result)
    return result


def _write_canonical(verifier, path: Path, payload: dict[str, object]) -> None:
    path.write_bytes(verifier._canonical_bytes(payload))


def test_verifier_is_standalone_and_does_not_import_v011_runner() -> None:
    source = VERIFIER_PATH.read_text(encoding="utf-8")
    assert "import run_v011_joint_c3_ordered_oracle" not in source
    assert "spec_from_file_location" not in source
    assert "merge_shards" not in source


def test_synthetic_complete_result_passes_and_cli_emits_compact_summary(tmp_path, capsys) -> None:
    verifier = _module()
    path = tmp_path / "result.json"
    _write_canonical(verifier, path, _result(verifier))

    summary = verifier.verify_result(path)
    assert summary["status"] == "PASS"
    assert summary["rows"] == 15
    assert summary["decision"] == "GO_AP_MONE_LEARNABILITY_PREREG_ONLY"
    assert verifier.main([str(path)]) == 0
    output = capsys.readouterr().out.strip()
    assert json.loads(output)["result_sha256"] == summary["result_sha256"]
    assert "\n" not in output


def test_result_digest_and_summary_are_independently_authenticated(tmp_path) -> None:
    verifier = _module()
    path = tmp_path / "result.json"
    payload = _result(verifier)
    payload["result_sha256"] = "f" * 64
    _write_canonical(verifier, path, payload)
    with pytest.raises(verifier.V011ResultVerificationError, match="result_sha256"):
        verifier.verify_result(path)

    payload = _result(verifier)
    payload["summaries"]["pooled_by_arm"]["DROP_C3"]["served_user_steps"] += 1
    payload["result_sha256"] = verifier.canonical_sha256({k: v for k, v in payload.items() if k != "result_sha256"})
    _write_canonical(verifier, path, payload)
    with pytest.raises(verifier.V011ResultVerificationError, match="summaries"):
        verifier.verify_result(path)


def test_coverage_and_gate_mismatches_fail_closed(tmp_path) -> None:
    verifier = _module()
    path = tmp_path / "result.json"
    payload = _result(verifier)
    payload["rows"] = payload["rows"][:-1]
    payload["result_sha256"] = verifier.canonical_sha256({k: v for k, v in payload.items() if k != "result_sha256"})
    _write_canonical(verifier, path, payload)
    with pytest.raises(verifier.V011ResultVerificationError, match="15 rows"):
        verifier.verify_result(path)

    payload = _result(verifier)
    # Recompute only the producer receipt's summaries/gate through the
    # verifier's independent helpers, then exercise a stale ordered decision.
    payload["gate"]["decision"] = "GO_M1D_LEARNABILITY_PREREG_ONLY"
    payload["result_sha256"] = verifier.canonical_sha256({k: v for k, v in payload.items() if k != "result_sha256"})
    _write_canonical(verifier, path, payload)
    with pytest.raises(verifier.V011ResultVerificationError, match="gate"):
        verifier.verify_result(path)


@pytest.mark.parametrize(
    ("ap", "m1d", "o", "expected"),
    [
        (True, True, True, "GO_AP_MONE_LEARNABILITY_PREREG_ONLY"),
        (True, False, False, "INCONSISTENT_AP_ONLY_NO_LEARNER_REVIEW"),
        (False, True, False, "GO_M1D_LEARNABILITY_PREREG_ONLY"),
        (False, False, True, "C1_ALIGNMENT_BLOCKS_C3_NO_LEARNER"),
        (False, False, False, "JOINT_C3_STRUCTURAL_REDESIGN_REQUIRED"),
    ],
)
def test_ordered_decision_is_the_frozen_table(ap, m1d, o, expected) -> None:
    verifier = _module()
    assert verifier.ordered_decision(passed_ap=ap, passed_m1d=m1d, passed_o=o) == expected
