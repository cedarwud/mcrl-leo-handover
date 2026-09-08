from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import build_c3s_confirm_preflight as preflight
import build_c3s_confirm_world_plan as plan_builder
import c3s_full2_policy_adapter as adapter
import run_v023_c3s_confirmatory as runner


SHA = "1" * 64


class FakeFrozen:
    arm = "FULL2"

    def verify(self) -> None:
        return None

    def binding(self) -> dict[str, object]:
        return {
            "checkpoint_path": "/sealed/FULL2.pt", "checkpoint_sha256": "2" * 64,
            "q1_parameter_sha256": "3" * 64, "q2_parameter_sha256": "4" * 64,
            "update_count": 200, "routes": ["C1", "C2"],
        }


def decision(arm: str, step: int, *, configuration: str = "LITE", active: bool = True) -> dict[str, object]:
    metric = {"total_bits_hex": (100.0).hex(), "total_energy_j_hex": (10.0).hex(), "served": 100, "opportunities": 100}
    return {
        "decision_index": step, "step_index": step, "arm": arm,
        "coordinator_configuration": configuration, "pre_decision_state_sha256": SHA,
        "full2_proposal": [0] * 100, "full2_proposal_sha256": SHA,
        "full2_proposal_physical_associations": [[1, 1]] * 100, "committed_profile_id": "BASE",
        "committed_actions": [0] * 100, "committed_actions_sha256": SHA,
        "committed_physical_associations": [[1, 1]] * 100, "selected_nominal": metric,
        "full2_proposal_nominal": metric, "catalog_size": 1,
        "unique_nominal_evaluations": 1, "profile_counts": {"base": 1, "unilateral": 0, "joint": 0},
        "coordinator_active_step": active, "full_decision_wall_seconds_hex": (2.0).hex(),
        "phase_wall_seconds_hex": {"q_inference": (1.0).hex()}, "eta_sensitivity": [],
        "policy_state_after": {"decision_index": step + 1, "blocked_through": {}},
        "process_lifetime_peak_rss_kib": 1, "realised": metric,
    }


def episode(
    arm: str, index: int, *, bits: float = 3000.0, energy: float = 300.0,
    served: int = 3000, configuration: str = "LITE",
) -> dict[str, object]:
    domain = f"C3S_CONFIRM/world/{index}"
    records = [decision(arm, step, configuration=configuration, active=configuration != "V-C" or step % 3 == 0) for step in range(30)]
    return {
        "schema": f"{runner.SCHEMA}-episode-receipt", "status": "COMPLETE",
        "arm": arm, "episode_index": index, "world_id": f"c3s-confirm-world-{index:06d}",
        "world_domain": domain, "world_seed": plan_builder.derive_seed(domain),
        "field_root_digest": SHA, "initial_state_sha256": SHA,
        "policy_binding_sha256": ("2" if arm == "FULL2" else "3") * 64,
        "total_bits": bits, "total_energy_j": energy,
        "served_user_steps": served, "service_opportunities": 3000,
        "action_trace_sha256": SHA, "plan_sha256": "4" * 64,
        "decision_records": records, "decision_records_sha256": runner.canonical_sha256(records),
    }


def matrix(*, supporters: tuple[str, ...] = (), status: str = "COMPLETE") -> dict[str, object]:
    decisions = {arm: {"outcome": "SUPPORT" if arm in supporters else "NO_SUPPORT", "reasons": []} for arm in runner.MATRIX_TIE_ORDER}
    latency = {arm: {"mean_hex": float(index + 1).hex()} for index, arm in enumerate(runner.MATRIX_TIE_ORDER)}
    return {
        "status": status, "outcome": "C3S_VARIANT_MATRIX_COMPLETE", "integrity": status == "COMPLETE",
        "pooled": {"decisions": decisions, "latency_by_arm": latency},
        "lite_equivalence_audit": {"status": "PASS_BITWISE_LITE_EQUIVALENCE", "unexplained_same_panel_disagreement": False},
    }


def v1(*, lite_support: bool = True) -> dict[str, object]:
    return {
        "status": "COMPLETE", "outcome": "C3S_THREE_ARM_SCREEN_COMPLETE", "integrity": True,
        "decisions": {"LITE": {"outcome": "C3S_LITE_SCREEN_SUPPORT" if lite_support else "C3S_LITE_SCREEN_NO_SUPPORT"}},
    }


def test_30_step_accounting_and_all_configurations() -> None:
    assert adapter.STEPS == 30
    assert runner.validate_episode(episode("FULL2", 1))["service_opportunities"] == 3000
    bad = episode("FULL2", 1); bad["service_opportunities"] = 1000
    with pytest.raises(runner.ConfirmatoryError, match="coverage"):
        runner.validate_episode(bad)
    assert set(adapter.COORDINATOR_CONFIGURATIONS) == {"LITE", "V-J", "V-U", "V-M", "V-C", "V-H", "V-P", "V-L2", "FULL"}


def test_cadence_inactive_and_control_use_full2_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    nominal = {"total_bits": 100.0, "total_energy_j": 10.0, "served": 100, "opportunities": 100}
    snapshot = SimpleNamespace(
        q_inference_seconds=0.1, base_actions=np.zeros(100, dtype=np.int64),
        slot_physical_keys=np.zeros((100, 1, 2), dtype=np.int64),
    )
    catalog = ({"profile_id": "BASE", "kind": "base", "tie_key": (0,), "actions": snapshot.base_actions.copy(), "nominal": nominal},)
    monkeypatch.setattr(adapter.c3s_policy, "_live_neutrality_fingerprint", lambda _env, _rng: SHA)
    monkeypatch.setattr(adapter.c3s_policy, "_snapshot_inputs", lambda _policy, _env, _obs: (snapshot, object()))
    monkeypatch.setattr(adapter.variant_policy, "_base_only_catalog", lambda _snapshot, _evaluator, phases: (phases.update({"unique_nominal_evaluations": 1.0}) or catalog))
    control = adapter.C3SFull2PolicyAdapter(frozen_full2=FakeFrozen(), coordinator_enabled=False, configuration="V-C")
    cadence = adapter.C3SFull2PolicyAdapter(frozen_full2=FakeFrozen(), coordinator_enabled=True, configuration="V-C")
    observation = SimpleNamespace(step_index=1)
    assert control.select_actions(object(), observation, np.random.default_rng(1)).tolist() == [0] * 100
    assert cadence.select_actions(object(), observation, np.random.default_rng(2)).tolist() == [0] * 100
    cadence.complete_nondecisional_diagnostics()
    assert control.decision_records[0]["committed_profile_id"] == "BASE"
    assert cadence.decision_records[0]["coordinator_active_step"] is False


def test_arm_resolution_winner_fallback_and_unresolved() -> None:
    receipt = matrix(supporters=("V-U", "V-J"))
    receipt["pooled"]["latency_by_arm"]["V-U"]["mean_hex"] = (0.5).hex()
    assert runner.resolve_confirmatory_arm(receipt, v1()) == "V-U"
    tied = matrix(supporters=("V-J", "V-U"))
    tied["pooled"]["latency_by_arm"]["V-U"]["mean_hex"] = tied["pooled"]["latency_by_arm"]["V-J"]["mean_hex"]
    assert runner.resolve_confirmatory_arm(tied, v1()) == "V-J"
    assert runner.resolve_confirmatory_arm(matrix(), v1()) == "LITE"
    assert runner.resolve_confirmatory_arm(matrix(status="INCOMPLETE"), v1()) == runner.ARM_UNRESOLVED
    broken = matrix(supporters=("V-J",)); broken["lite_equivalence_audit"]["unexplained_same_panel_disagreement"] = True
    assert runner.resolve_confirmatory_arm(broken, v1()) == runner.ARM_UNRESOLVED
    with pytest.raises(runner.ConfirmatoryError, match="ARM_UNRESOLVED"):
        preflight.selected_catalog(broken, v1())


def pooled(n: int, *, c3s_ee: float, c3s_served: int | None = None) -> dict[str, object]:
    opportunities = n * 3000
    return {
        "FULL2": {"episodes": n, "ee_bits_per_j": 10.0, "served_user_steps": opportunities, "service_opportunities": opportunities},
        "FULL2+C3-S": {"episodes": n, "ee_bits_per_j": c3s_ee, "served_user_steps": opportunities if c3s_served is None else c3s_served, "service_opportunities": opportunities},
    }


@pytest.mark.parametrize("boundary", [100, 500])
def test_early_futility_and_rung_held(boundary: int) -> None:
    failed = runner.adjudicate(pooled(boundary, c3s_ee=10.0), completed_episodes=boundary)
    assert failed["overall_token"] == runner.FALSIFIED and failed["rung_status"] == "EARLY_FUTILITY"
    assert failed["progression_closed"] is True
    held = runner.adjudicate(pooled(boundary, c3s_ee=10.01), completed_episodes=boundary)
    assert held["overall_token"] is None and held["rung_status"] == runner.RUNG_HELD
    assert held["next_interval_released"] is True


def test_1500_is_nonterminal_and_3000_is_terminal() -> None:
    descriptive = runner.adjudicate(pooled(1500, c3s_ee=9.0), completed_episodes=1500)
    assert descriptive["rung_status"] == runner.RUNG_HELD and descriptive["scientific_disposition_emitted"] is False
    held = runner.adjudicate(pooled(3000, c3s_ee=10.01, c3s_served=8_991_000), completed_episodes=3000)
    assert held["overall_token"] == runner.HELD and held["rung_status"] == "CONTRIBUTION_HELD"
    failed = runner.adjudicate(pooled(3000, c3s_ee=10.01, c3s_served=8_990_999), completed_episodes=3000)
    assert failed["overall_token"] == runner.FALSIFIED and failed["reasons"] == ["SERVICE_MARGIN_FAILED"]


def test_decision_records_are_persisted_in_chunk(tmp_path: Path) -> None:
    rows = [episode("FULL2", index) for index in range(1, 101)]
    boundaries = []
    for boundary in (0, 100):
        value = {"schema": f"{runner.SCHEMA}-boundary-state", "arm": "FULL2", "episode_index": boundary}
        value["boundary_state_sha256"] = runner.canonical_sha256(value); boundaries.append(value)
    output = tmp_path / "chunk"
    runner.publish_chunk(arm="FULL2", start=0, rows=rows, output=output, start_boundary=boundaries[0], end_boundary=boundaries[1], authority_sha256="6" * 64)
    saved = runner.read_json(output / "episodes/episode-000001.json")
    assert len(saved["decision_records"]) == 30
    assert saved["decision_records"][0]["pre_decision_state_sha256"] == SHA
    assert saved["decision_records_sha256"] == runner.canonical_sha256(saved["decision_records"])


def test_equivalence_receipt_verification(tmp_path: Path) -> None:
    old, new, archive = tmp_path / "old.py", tmp_path / "new.py", tmp_path / "archive.json"
    old.write_text("old", encoding="ascii"); new.write_text("new", encoding="ascii"); archive.write_text("{}", encoding="ascii")
    replayed = {
        "committed_actions": [1], "committed_profile_id": "BASE", "tie_key": [0],
        "policy_state_after": {}, "information_access_sha256": SHA,
        "rng_before_sha256": SHA, "rng_after_sha256": SHA,
    }
    payload = runner.verify_equivalence(old, new, [archive], reviewer="independent", replay=lambda _code, _archive: replayed)
    target = tmp_path / "equivalence.json"; runner.write_once(target, payload)
    assert runner.verify_equivalence_receipt(target, old_sha256=runner.file_sha256(old), new_sha256=runner.file_sha256(new))["sha256"] == runner.file_sha256(target)


def test_estimator_uses_complete_v1_and_matrix_timing_schema(tmp_path: Path) -> None:
    v1_path, matrix_path = tmp_path / "v1.json", tmp_path / "matrix.json"
    v1_path.write_text(json.dumps({"per_arm_decision_wall_timing": {
        "BASE": {"mean_hex": (1.9).hex()}, "LITE": {"mean_hex": (49.4).hex()}, "FULL": {"mean_hex": (66.8).hex()},
    }}), encoding="ascii")
    matrix_path.write_text(json.dumps({"pooled": {"latency_by_arm": {"V-C": {"mean_hex": (12.5).hex()}}}}), encoding="ascii")
    lite = runner.estimate("LITE", episodes=100, screen_timing=v1_path)
    assert lite["decisions_per_episode"] == 30
    assert lite["complete_mean_seconds_per_decision"] == {"FULL2": 1.9, "FULL2+C3-S": 49.4}
    assert lite["coordinator_only_worker_hours"] == pytest.approx(41.1666666667)
    variant = runner.estimate("V-C", episodes=100, screen_timing=v1_path, matrix_timing=matrix_path)
    assert variant["complete_mean_seconds_per_decision"]["FULL2+C3-S"] == 12.5


def test_failure_decomposition_identity_and_no_progression_feedback() -> None:
    coordinator, full2 = decision("FULL2+C3-S", 0), decision("FULL2", 0)
    coordinator["realised"] = {"total_bits_hex": (100.0).hex(), "total_energy_j_hex": (10.0).hex(), "served": 99, "opportunities": 100}
    full2["realised"] = {"total_bits_hex": (80.0).hex(), "total_energy_j_hex": (7.0).hex(), "served": 100, "opportunities": 100}
    pair = {
        "coordinator": coordinator, "full2": full2,
        "isolated_full2_replay_realised": {"total_bits_hex": (90.0).hex(), "total_energy_j_hex": (8.0).hex(), "served": 100, "opportunities": 100},
    }
    result = runner.failure_decomposition([pair], eta_full2=10.0)
    assert result["I_plus_R"] == result["delta_bits_minus_p_delta_energy"]
    assert result["identity_residual"] == 0.0
    assert result["progression_effect"] is False and result["rescue_permitted"] is False


def test_write_once_and_dry_run() -> None:
    assert runner.RUNG_BOUNDARIES == (100, 500, 1500, 3000)
    assert "configuration=V-H" in runner.dry_run("V-H")
