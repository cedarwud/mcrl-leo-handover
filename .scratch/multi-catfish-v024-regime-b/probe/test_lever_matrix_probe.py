"""Synthetic, simulator-inert tests for the Track-B lever matrix probe."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import rate_target_sum_power
import run_v024_lever_matrix_probe as matrix
import run_v024_regime_probe as finite
from levers.common import LeverError, RegenerationRequired, TODO_CONTROLLER_DECLARE
from levers.lever_l2_pa_curve import (
    BACKOFF_KNEE_RATIO,
    BIAS_FLOOR_W,
    PAE_AT_6DB,
    pa_dc_power_w,
)
from levers.lever_l4_handover_energy import (
    BEAM_SETUP_ENERGY_J,
    USER_EVENT_ENERGY_J,
    event_ledger,
)
from levers.registry import LEVER_PRIORITY, LEVERS, apply_profile
from mcrl.env.link_budget import PA_SATURATION_POWER_W


def physical_profile(*, power: tuple[float, ...] = (1.0, 0.5)) -> dict[str, object]:
    return {
        "active_beams": [],
        "capacity_bits": [10.0.hex(), 20.0.hex()],
        "fixed_power_w": 0.876.hex(),
        "interval_s": finite.INTERVAL_S.hex(),
        "link_power_w": [value.hex() for value in power],
        "link_rate_bps": [1.0.hex(), 2.0.hex()],
        "rate_semantics": "UNBOUNDED_SHANNON_CAPACITY_BITS_PER_S",
        "schema": "fixture",
        "served": [True, True],
        "serving_cell": [5, 5],
        "serving_satellite": [10, 10],
        "system_power_w": 5.0.hex(),
    }


def finite_raw_fixture() -> dict[str, object]:
    step = {
        "step_index": 0,
        "state_sha256": "a" * 64,
        "action_masks": [[True]],
        "action_physical_keys": [[[10, 5]]],
        "reference_actions": [0],
        "reference_profile": physical_profile(),
        "unilateral_profiles": [],
        "joint_profiles": [],
    }
    return {
        "schema": finite.RAW_TAPE_SCHEMA,
        "status": "COMPLETE_IMMUTABLE_TAPE",
        "claim_ceiling": finite.CLAIM_CEILING,
        "unit": finite.ALL_UNITS[0].as_dict(),
        "panel_bindings": finite.panel_bindings(),
        "preflight_sha256": "b" * 64,
        "steps": [{**step, "step_index": index} for index in range(finite.STEPS)],
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "efficacy_claim": False,
    }


def target_profile(bits: tuple[float, ...], energy: float) -> dict[str, object]:
    return {"bits": [value.hex() for value in bits], "energy_j": energy.hex(), "served": [True] * len(bits)}


def test_registry_matches_astra_priority_and_shared_runner() -> None:
    assert LEVER_PRIORITY == ("L1", "L12", "L2", "L4")
    assert tuple(LEVERS) == LEVER_PRIORITY
    assert LEVERS["L1"].identity == "B2_L1_RATE_TARGET_SUM_POWER"
    assert LEVERS["L12"].identity == "B2_L12_RATE_TARGET_DEVICE_PA"
    assert LEVERS["L2"].identity == "B2_L2_PIACIBELLO_SURROGATE"
    assert LEVERS["L4"].identity == "B2_L4_CONTROL_EVENT_ENERGY_PROXY"


def test_no_lever_is_byte_identical_to_existing_finite_demand_output() -> None:
    raw = finite_raw_fixture()
    before = finite.derive_grid_tape(raw, grid="G2", raw_sha256="c" * 64)
    after_raw = apply_profile(None, raw)
    after = finite.derive_grid_tape(after_raw, grid="G2", raw_sha256="c" * 64)
    assert after_raw is raw
    assert matrix.canonical_bytes(after) == matrix.canonical_bytes(before)


def test_l1_fixed_point_and_regeneration_hook_preserve_physics_field_name() -> None:
    one = rate_target_sum_power.solve_sum_power(
        desired_gain=[1e-10], cross_gain=[[1e-10]], serving_beam=[0], beam_colors=[0],
        config=rate_target_sum_power.RateTargetConfig(beam_power_cap_w=1e12),
    )
    two = rate_target_sum_power.solve_sum_power(
        desired_gain=[1e-10, 1e-10], cross_gain=[[1e-10], [1e-10]],
        serving_beam=[0, 0], beam_colors=[0],
        config=rate_target_sum_power.RateTargetConfig(beam_power_cap_w=1e12),
    )
    assert two.beam_power_w[0] > one.beam_power_w[0]
    observed: dict[str, object] = {}

    def adapter(**kwargs: object) -> str:
        observed.update(kwargs)
        return "acquired"

    assert LEVERS["L1"].regeneration_hook(adapter, key="fixture") == "acquired"
    assert observed["keyed_fading_event"] == "physics"
    assert observed["continuation"] == "ORIGINAL_PHYSICS_REFERENCE_ONLY"
    with pytest.raises(RegenerationRequired, match="no tape was synthesized"):
        LEVERS["L1"].regeneration_hook()


def test_l2_curve_and_profile_repricing_leave_rf_rate_fields_unchanged() -> None:
    knee_power = PA_SATURATION_POWER_W * BACKOFF_KNEE_RATIO
    expected = max(BIAS_FLOOR_W, knee_power * 0.99 / PAE_AT_6DB)
    assert pa_dc_power_w(knee_power) == pytest.approx(expected)
    assert pa_dc_power_w(0.0) == 0.0
    with pytest.raises(LeverError, match="outside"):
        pa_dc_power_w(PA_SATURATION_POWER_W + 1.0)
    original = physical_profile()
    repriced = apply_profile("L2", original)
    for field in ("capacity_bits", "link_power_w", "link_rate_bps", "served", "serving_cell", "serving_satellite"):
        assert repriced[field] == original[field]
    assert repriced["system_power_w"] != original["system_power_w"]
    assert repriced["energy_override"]["rf_rate_rows_unchanged"] is True


def test_l4_counts_physical_transitions_shared_setup_and_failed_attempts() -> None:
    ledger = event_ledger(
        predecision_physical_keys=[[1, 1], [2, 2], [3, 3]],
        selected_actions=[0, 0, -1],
        action_physical_keys=[[[9, 9]], [[9, 9]], [[4, 4]]],
        served=[True, False, False],
        initial_state_authenticated=True,
    )
    assert ledger["handover_count"] == 2
    assert ledger["distinct_setup_count"] == 1
    assert ledger["failed_attempt_count"] == 1
    assert ledger["event_energy_j"] == pytest.approx(BEAM_SETUP_ENERGY_J + 2 * USER_EVENT_ENERGY_J)
    with pytest.raises(LeverError, match="authenticated"):
        event_ledger(
            predecision_physical_keys=[[1, 1]], selected_actions=[0],
            action_physical_keys=[[[2, 2]]], served=[True],
            initial_state_authenticated=False,
        )


def test_l12_inherits_l2_verify_source_todos_and_requires_regeneration() -> None:
    assert LEVERS["L12"].regeneration_required is True
    assert LEVERS["L12"].controller_todos == LEVERS["L2"].controller_todos
    with pytest.raises(RegenerationRequired):
        apply_profile("L12", physical_profile())


def test_estimate_marks_regeneration_and_verify_source_without_opening_simulator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(matrix, "r2_bindings", lambda: [{"path": "/x/world-a/physical-tape.json", "sha256": "d" * 64}])
    result = matrix.estimate()
    assert result["priority"] == list(LEVER_PRIORITY)
    assert result["levers"]["L1"]["unit_status"] == "REGEN_REQUIRED"
    assert result["levers"]["L12"]["unit_status"] == "REGEN_REQUIRED"
    assert result["levers"]["L2"]["unit_status"] == TODO_CONTROLLER_DECLARE
    assert result["levers"]["L4"]["unit_status"] == TODO_CONTROLLER_DECLARE
    assert result["levers"]["L2"]["r2_raw_tapes_reused"] is True


def test_verify_source_todos_refuse_runner_start_before_preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(matrix, "pin_single_thread_runtime", lambda: None)
    assert matrix.main(["--lever", "L2", "--merge", "--dry-run", "--preflight", str(tmp_path / "absent")]) == 2
    assert TODO_CONTROLLER_DECLARE in capsys.readouterr().err


def test_exact_targets_literal_drops_and_nominal_set_decoder() -> None:
    masks = np.ones((2, 4), dtype=np.bool_)
    unilateral = [
        {"focal_user": 0, "candidate_action": 1, "profile": target_profile((12.0, 10.0), 10.0)},
        {"focal_user": 1, "candidate_action": 2, "profile": target_profile((10.0, 13.0), 10.0)},
    ]
    pair = {
        "member_users": [0, 1],
        "proposed_actions": [1, 2],
        "profiles": [
            target_profile((10.0, 10.0), 10.0), target_profile((12.0, 10.0), 10.0),
            target_profile((10.0, 13.0), 10.0), target_profile((14.0, 15.0), 10.0),
        ],
    }
    surfaces = matrix.target_surfaces(
        reference_actions=[0, 0], masks=masks,
        reference_profile=target_profile((10.0, 10.0), 10.0),
        unilateral_profiles=unilateral,
        c2_surface=np.array([[0.0, 0.0, 5.0, 0.0], [0.0, 0.0, 0.0, 5.0]]),
        lcsrs_pairs=[pair], lambda_bits_per_j=1.0, kappa_bits=1.0,
    )
    assert surfaces["C3"][0, 1] == 2.0
    assert surfaces["C3"][1, 2] == 2.0
    arms = matrix.compose_arms(surfaces, masks)
    assert set(arms) == {"O1", "O2", "O12", "O123", "DROP_C1_O23", "DROP_C2_O13", "DROP_C3_O12"}
    catalog = [
        {"configuration_id": "reference", "configuration_kind": "reference", "profile": target_profile((10.0,), 10.0), "q2_delta": 0.0, "nominal_score": 0.0, "nominal_uses_realized_profile": False, "served": 1, "nominal_served": 1, "opportunities": 1},
        {"configuration_id": "a", "configuration_kind": "top2_unilateral", "proposal_membership_verified": True, "profile": target_profile((12.0,), 10.0), "q2_delta": 0.0, "nominal_score": 2.0, "nominal_uses_realized_profile": False, "served": 1, "nominal_served": 1, "opportunities": 1},
        {"configuration_id": "b", "configuration_kind": "complete_evacuation", "proposal_membership_verified": True, "profile": target_profile((12.0,), 10.0), "q2_delta": 0.0, "nominal_score": 2.0, "nominal_uses_realized_profile": False, "served": 1, "nominal_served": 1, "opportunities": 1},
    ]
    assert matrix.set_decode(catalog, lambda_bits_per_j=1.0, kappa_bits=1.0, privileged=True)["configuration_id"] == "a"
    assert matrix.set_decode(catalog, lambda_bits_per_j=1.0, kappa_bits=1.0, privileged=False)["configuration_id"] == "a"


def arm_row(arm: str, world: int, carrier: str, value: float) -> dict[str, object]:
    return {
        "arm": arm, "world": world, "carrier": carrier,
        "bits": value, "energy_j": 1.0, "served": 100, "opportunities": 100,
        "attainment_applicable": True, "target_attained": 100,
        "energy_components": {"pa_j": 0.8, "fixed_circuit_j": 0.2, "event_j": 0.0, "other_j": 0.0},
    }


def test_failure_analysis_has_global_world_carrier_marginals_and_energy_decomposition() -> None:
    values = {arm: 100.0 + index for index, arm in enumerate(matrix.ARMS)}
    values.update({"O123": 110.0, "DROP_C1_O23": 109.0, "DROP_C2_O13": 108.0, "DROP_C3_O12": 107.0})
    rows = [arm_row(arm, world, carrier, values[arm]) for world in matrix.WORLDS for carrier in matrix.CARRIERS for arm in matrix.ARMS]
    qualification = matrix.map_qualification(
        eta_ref=100.0, u1=104.0, j1=105.0, interaction_fraction=0.005,
        world_contrasts={str(world): 1.0 if index < 3 else -1.0 for index, world in enumerate(matrix.WORLDS)},
        service_guards_pass=True, additional_guards_pass=True,
    )
    mechanism = [{
        "occupancy": 1, "allocated_bandwidth_hz": 1.0, "target_sinr": 1.0,
        "requested_power_w": 1.0, "allocated_power_w": 1.0, "cap_hits": 0,
        "interference_w": 0.0, "attainment": 1.0, "solver_residual_w": 0.0,
        "interaction_decomposition": {"bits": 1.0, "pa_energy_j": -0.2, "fixed_circuit_energy_j": 0.0, "event_energy_j": 0.0, "other_energy_j": 0.0},
    }]
    block = matrix.build_failure_analysis(
        lever_id="L1", arm_rows=rows, regime_map={"qualification": qualification},
        mechanism_rows=mechanism,
        composition_rows=[{"intended_surplus": 2.0, "realized_surplus": 1.0, "changed_users": 1, "action_disagreement": 0, "service_losses": 0, "set_vs_additive_conversion": 0.5}],
    )
    assert len(block["four_world_tables"]) == 4
    assert set(block["carrier_strata_diagnostic_only"]) == set(matrix.CARRIERS)
    assert block["global_arm_and_marginal_table"]["marginals"]["C3"]["energy_moved"] is False
    assert block["energy_decomposition_pa_vs_rest"]["pa_energy_j"] == -0.2
    assert block["missing_mechanism_fields"] == []


def test_failure_analysis_refuses_missing_or_inconsistent_energy_decomposition() -> None:
    rows = [arm_row("REFERENCE", matrix.WORLDS[0], matrix.CARRIERS[0], 100.0)]
    mechanism = [{"interaction_decomposition": {
        "bits": 1.0, "pa_energy_j": 0.0, "fixed_circuit_energy_j": 0.0,
        "event_energy_j": 0.0, "other_energy_j": 0.0,
    }}]
    matrix._validate_failure_energy_decomposition(rows, mechanism)
    del rows[0]["energy_components"]
    with pytest.raises(matrix.MatrixProbeError, match="PA-versus-rest"):
        matrix._validate_failure_energy_decomposition(rows, mechanism)
    rows = [arm_row("REFERENCE", matrix.WORLDS[0], matrix.CARRIERS[0], 100.0)]
    rows[0]["energy_components"]["pa_j"] = 0.7  # type: ignore[index]
    with pytest.raises(matrix.MatrixProbeError, match="do not sum"):
        matrix._validate_failure_energy_decomposition(rows, mechanism)
    rows = [arm_row("REFERENCE", matrix.WORLDS[0], matrix.CARRIERS[0], 100.0)]
    del mechanism[0]["interaction_decomposition"]
    with pytest.raises(matrix.MatrixProbeError, match="interaction decomposition"):
        matrix._validate_failure_energy_decomposition(rows, mechanism)


def test_immutable_receipt_uses_companion_digest_only_in_temp(tmp_path: Path) -> None:
    target, sidecar, digest = matrix.write_once_with_sidecar(tmp_path / "receipt.json", {"status": "COMPLETE"})
    assert target.stat().st_mode & 0o777 == 0o444
    assert sidecar.stat().st_mode & 0o777 == 0o444
    assert matrix.file_sha256(target) == digest
    with pytest.raises(matrix.MatrixProbeError, match="overwrite"):
        matrix.write_once_with_sidecar(target, {"status": "COMPLETE"})


def test_matrix_adjudication_waits_for_every_lever_and_uses_priority() -> None:
    assert matrix.adjudicate_matrix({}) == {
        "status": "WAITING_FOR_ALL_LEVERS", "selected_lever": None,
        "missing": ["L1", "L12", "L2", "L4"],
    }
    terminals = {lever: {"status": "COMPLETE", "outcome": "NO_SUPPORT"} for lever in LEVER_PRIORITY}
    terminals["L12"]["outcome"] = "SUPPORT"
    terminals["L2"]["outcome"] = "SUPPORT"
    assert matrix.adjudicate_matrix(terminals)["selected_lever"] == "L12"
    terminals["L1"] = {"status": "INCOMPLETE", "outcome": None}
    assert matrix.adjudicate_matrix(terminals)["status"] == "INCOMPLETE"
    assert matrix.adjudicate_matrix(terminals)["selected_lever"] is None


def test_merge_rejects_unit_from_different_preflight(tmp_path: Path) -> None:
    key = matrix.ALL_UNITS[0]
    path = tmp_path / "levers" / "L1" / "units" / key.slug / "receipt.json"
    matrix.write_once_with_sidecar(path, {
        "schema": matrix.UNIT_RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "lever": "L1",
        "unit": key.as_dict(),
        "preflight_sha256": "a" * 64,
        "launch_authority_sha256": "b" * 64,
    })
    with pytest.raises(matrix.MatrixProbeError, match="different preflight"):
        matrix.execute_merge(
            lever_id="L1", output=tmp_path, preflight_sha256="c" * 64,
            launch_authority_sha256="d" * 64,
        )
