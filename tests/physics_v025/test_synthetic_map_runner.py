from __future__ import annotations

from probe.run_v025_synthetic_map import (
    LABEL,
    _bind_provider,
    _budget_gate_path,
    _calibrate,
    _estimated_unit_execution_seconds,
    _load_stage2,
    _provider,
    _signed,
    grid_cells,
    read_once,
    write_once,
)
from mcrl.physics_v025.tapes import PROBE_WORLD_DOMAINS, REFERENCE_CARRIERS, build_world_tape


def test_budget_estimate_counts_every_reference_carrier_and_prefers_correction(
    tmp_path,
) -> None:
    assert _estimated_unit_execution_seconds(2.0, 19) == (
        2.0 * 19 * len(REFERENCE_CARRIERS)
    )
    original = tmp_path / "estimate.json"
    corrected = tmp_path / "corrected-estimate.json"
    original.touch()
    assert _budget_gate_path(tmp_path) == original
    corrected.touch()
    assert _budget_gate_path(tmp_path) == corrected


def test_synthetic_map_uses_stage4b_complete_cartesian_catalogue_when_bounded() -> None:
    runner = _load_stage2()
    cell = next(row for row in grid_cells() if row["id"] == "LOW-DENSE-WEAK")
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=_provider(cell, 1),
        steps=1,
        start_time_s=435.0,
    )
    base = runner._base_configuration(tape, 0, "nearest-eligible")
    rows = runner._catalogue(tape, 0, base)
    assert sum(row.changed_users == 0 for row in rows) == 1
    assert sum(row.changed_users == 1 for row in rows) == 3 * (4 - 1)
    assert len(rows) == 4**3


def test_s0_nominal_service_guard_and_power_ledger_are_receipted() -> None:
    runner = _load_stage2()
    cell = next(row for row in grid_cells() if row["id"] == "LOW-DENSE-STRONG")
    calibration = _calibrate(runner, cell, "a-r0")
    _bind_provider(runner, cell, 1)
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=_provider(cell, 1),
        steps=19,
        start_time_s=0.0,
    )
    step = runner.execute_step(
        tape=tape,
        setting=runner._setting("a-r0"),
        step_index=15,
        carrier="nearest-eligible",
        calibration=calibration,
        counter=runner.EvaluationCounter(),
    )
    assert step["s0_certificate"]["nominal_rank_noninferior_to_base"] is True
    assert step["architecture_dispatch"] == {
        "requested_code": "a-r",
        "implementation": "AngleRateTPC_TDM",
    }
    power = step["successor_usable_energy_range"]["required_rf_power_distribution"]
    assert power["sample_count"] > 0
    assert 0.0 <= power["mean_w"] <= power["beam_cap_w"]


def test_rate_target_fdm_dispatch_differs_from_tdm_when_beam_has_multiple_users() -> None:
    runner = _load_stage2()
    cell = next(row for row in grid_cells() if row["id"] == "LOW-DENSE-STRONG")
    _bind_provider(runner, cell, 1)
    tape = build_world_tape(
        domain=PROBE_WORLD_DOMAINS[0],
        provider=_provider(cell, 1),
        steps=1,
        start_time_s=435.0,
    )
    base = runner._base_configuration(tape, 0, "nearest-eligible")
    tdm = runner.StepEvaluator(
        tape, runner._setting("a-r0"), 0, transition_from=base
    ).evaluate(base)
    fdm = runner.StepEvaluator(
        tape, runner._setting("a′-r0"), 0, transition_from=base
    ).evaluate(base)
    assert tdm.acm_mode_counts != fdm.acm_mode_counts
    assert (tdm.bits, tdm.joules, tdm.acm_mode_counts) != (
        fdm.bits,
        fdm.joules,
        fdm.acm_mode_counts,
    )


def test_synthetic_receipts_are_labelled_write_once_and_self_verifying(tmp_path) -> None:
    payload = _signed(
        {
            "schema": "test",
            "status": "PASS",
            "experiment_label": LABEL,
        }
    )
    path = tmp_path / "receipt.json"
    write_once(path, payload)
    assert read_once(path) == payload
    assert path.stat().st_mode & 0o777 == 0o444
