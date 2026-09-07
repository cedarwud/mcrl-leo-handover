"""W-144 -- V0.13 fresh-world ZR oracle control-plane tests.

These tests exercise only the frozen panel, source contract plumbing, and the
result-level acceptance rule.  They do not open the simulator, read a result,
launch a shard, or train a learner.
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO / ".scratch" / "zero-energy-c3-v013" / "run_v013_zero_energy_c3_oracle.py"
)
SPEC = importlib.util.spec_from_file_location(
    "run_v013_zero_energy_c3_oracle", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def test_contract_freezes_four_fresh_worlds_one_zr_arm_and_twenty_four_episodes() -> None:
    contract = RUNNER.contract_receipt()
    assert RUNNER.WORLD_SEEDS == (
        2026104901,
        2026104902,
        2026104903,
        2026104904,
    )
    assert RUNNER.LINEAGES == (2026092101, 2026092102, 2026092103)
    assert RUNNER.ARMS == ("DROP_C3", "FULL_ZR")
    assert contract["episodes"] == 24
    assert contract["candidate_order"] == ["ZR"]
    assert contract["arm_heads"] == {
        "DROP_C3": ["Q1", "O2_OPS3"],
        "FULL_ZR": ["Q1", "O2_OPS3", "O3_ZR"],
    }
    assert contract["split"] == "TRAIN"
    assert contract["test_split_opened"] is False
    assert contract["episode_training"] is False
    assert contract["learner_update"] is False
    assert RUNNER.CONTRACT_PATH.name == (
        "MULTI-CATFISH-MCRL-V013-ZR-C3-FRESH-CONFIRMATION-PREREG-2026-09-03.md"
    )
    assert contract["gate"][
        "exact_total_trajectory_energy_nonincrease_pooled_or_world"
    ] is True
    assert contract["gate"]["executed_joint_adds_no_beam_or_satellite"] is True
    assert contract["gate"]["executed_joint_network_power_nonincrease"] is True
    assert contract["gate"]["active_beam_steps_not_above_pooled_or_world"] == (
        "diagnostic_only"
    )
    assert contract["gate"]["active_satellite_steps_not_above_pooled_or_world"] == (
        "diagnostic_only"
    )


def test_draft_prereg_matches_the_executable_panel_and_decision_table() -> None:
    text = RUNNER.CONTRACT_PATH.read_text(encoding="utf-8")
    statuses = [line.rstrip() for line in text.splitlines() if line.startswith("Status:")]
    assert len(statuses) == 1
    assert statuses[0] in {
        "Status: **DRAFT — DO NOT OPEN OUTCOMES**",
        RUNNER.FROZEN_STATUS,
    }
    if statuses[0] == RUNNER.FROZEN_STATUS:
        binding = (
            f"{RUNNER.CONTRACT_RECEIPT_PREFIX}"
            f"{RUNNER.canonical_sha256(RUNNER.contract_receipt())}`"
        )
        assert text.splitlines().count(binding) == 1
    for world in RUNNER.WORLD_SEEDS:
        assert f"`{world}`" in text
    for lineage in RUNNER.LINEAGES:
        assert f"`{lineage}`" in text
    assert "`DROP_C3`, `FULL_ZR`" in text
    assert "24 episodes total" in text
    assert f"`{RUNNER.FIELD_COMPONENT}`" in text
    assert "exact total trajectory energy is no greater" in text
    assert "Beam-step and satellite-step totals are intentionally demoted together" in text
    assert "`GO_ZR_C3_LEARNABILITY_PREREG_ONLY`" in text
    assert "`STOP_ZR_C3_ORACLE`" in text


def test_world_fields_are_distinct_deterministic_and_arm_independent() -> None:
    fields = [RUNNER.field_for_world(seed) for seed in RUNNER.WORLD_SEEDS]
    assert [field.root_digest for field in fields] == [
        RUNNER.field_for_world(seed).root_digest for seed in RUNNER.WORLD_SEEDS
    ]
    assert len({field.root_digest for field in fields}) == len(fields)
    assert RUNNER.FIELD_COMPONENT == "MCRL_V013_ZR_ACCEPTANCE_CONFIRMATION_V1"
    assert "arm" in RUNNER.FIELD_EXCLUDES
    assert "initialization_seed" in RUNNER.FIELD_EXCLUDES
    with pytest.raises(RUNNER.V013OracleError, match="outside"):
        RUNNER.field_for_world(1)


def test_ordered_decision_has_only_the_zr_learnability_transition() -> None:
    assert (
        RUNNER.ordered_decision(passed_zr=True)
        == "GO_ZR_C3_LEARNABILITY_PREREG_ONLY"
    )
    assert (
        RUNNER.ordered_decision(passed_zr=False)
        == "STOP_ZR_C3_ORACLE"
    )
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "FULL_HR" not in source
    assert "build_hr_surface" not in source


def _rows(*, energy_increase: bool = False) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for world in RUNNER.WORLD_SEEDS:
        for arm in RUNNER.ARMS:
            for lineage in RUNNER.LINEAGES:
                is_drop = arm == "DROP_C3"
                total_energy = 10.0 if is_drop or not energy_increase else 10.5
                rows.append(
                    {
                        "world_seed": world,
                        "arm": arm,
                        "initialization_seed": lineage,
                        "total_bits": 100.0 if is_drop else 110.0,
                        "total_energy_j": total_energy,
                        "ratio_of_sums_ee_bits_per_j": (100.0 if is_drop else 110.0)
                        / total_energy,
                        "served_user_steps": 1000,
                        # Deliberately increase both proxy counts in FULL_ZR;
                        # V0.13 exposes them as diagnostics, not hard gates.
                        "active_beam_steps": 100 if is_drop else 101,
                        "active_satellite_steps": 30 if is_drop else 31,
                        "c3_legal_spread_count": 0 if is_drop else 10,
                        "supported_positive_target_count": 0 if is_drop else 5,
                        "compatible_action_count": 0 if is_drop else 20,
                        "action_exposure": 0 if is_drop else 2,
                        "changed_actions_compatible": True,
                        "joint_support_passed": True,
                        "method_passed": True,
                        "candidate_specific_identity_passed": True,
                        "mechanics_passed": True,
                    }
                )
    return rows


def _pools(rows: list[dict[str, object]]):
    by_arm = {
        arm: RUNNER._pool([row for row in rows if row["arm"] == arm])
        for arm in RUNNER.ARMS
    }
    by_world = {
        str(world): {
            arm: RUNNER._pool(
                [
                    row
                    for row in rows
                    if row["world_seed"] == world and row["arm"] == arm
                ]
            )
            for arm in RUNNER.ARMS
        }
        for world in RUNNER.WORLD_SEEDS
    }
    return by_arm, by_world


def _gate(rows: list[dict[str, object]]):
    by_arm, by_world = _pools(rows)
    return RUNNER._pair_gate(
        label="ZR",
        full_arm="FULL_ZR",
        rows=rows,
        pooled_by_arm=by_arm,
        pooled_by_world_and_arm=by_world,
    )


def test_pair_gate_uses_exact_trajectory_energy_and_ignores_proxy_count_increases() -> None:
    gate = _gate(_rows())
    assert gate["passed"] is True
    assert gate["pooled"]["relative_delta_ee"] == pytest.approx(0.1)
    assert gate["pooled_total_trajectory_energy_nonincrease"] is True
    assert gate["per_world_total_trajectory_energy_nonincrease"] is True
    assert gate["pooled_active_beam_steps_not_above_diagnostic"] is False
    assert gate["pooled_active_satellite_steps_not_above_diagnostic"] is False
    assert all(
        value["active_beam_steps_not_above_diagnostic"] is False
        for value in gate["by_world"].values()
    )
    assert all(value["positive_lineages"] == 3 for value in gate["by_world"].values())


def test_pair_gate_rejects_pooled_and_per_world_energy_increase() -> None:
    gate = _gate(_rows(energy_increase=True))
    assert gate["passed"] is False
    assert gate["pooled_total_trajectory_energy_nonincrease"] is False
    assert gate["per_world_total_trajectory_energy_nonincrease"] is False
    assert any("pooled trajectory energy increased" in stop for stop in gate["hard_stops"])
    assert any("per-world trajectory energy increased" in stop for stop in gate["hard_stops"])


def test_pair_gate_rejects_a_bad_world_even_when_pooled_ee_is_positive() -> None:
    rows = _rows()
    for row in rows:
        if row["world_seed"] == RUNNER.WORLD_SEEDS[0] and row["arm"] == "FULL_ZR":
            row["total_bits"] = 90.0
            row["ratio_of_sums_ee_bits_per_j"] = 9.0
    gate = _gate(rows)
    assert gate["pooled"]["delta_ee_bits_per_j"] > 0.0
    assert gate["passed"] is False
    assert any("not EE-positive in every frozen world" in stop for stop in gate["hard_stops"])


def test_pair_gate_requires_two_positive_lineages_in_every_world() -> None:
    rows = _rows()
    target_world = RUNNER.WORLD_SEEDS[0]
    for row in rows:
        if row["world_seed"] != target_world or row["arm"] != "FULL_ZR":
            continue
        if row["initialization_seed"] in RUNNER.LINEAGES[:2]:
            row["total_bits"] = 99.0
            row["ratio_of_sums_ee_bits_per_j"] = 9.9
        else:
            row["total_bits"] = 130.0
            row["ratio_of_sums_ee_bits_per_j"] = 13.0
    gate = _gate(rows)
    assert gate["by_world"][str(target_world)]["delta_ee_bits_per_j"] > 0.0
    assert gate["by_world"][str(target_world)]["positive_lineages"] == 1
    assert gate["passed"] is False
    assert any("fewer than two positive lineages" in stop for stop in gate["hard_stops"])


def test_pair_gate_fails_service_joint_support_and_zero_exposure() -> None:
    rows = _rows()
    full_rows = [row for row in rows if row["arm"] == "FULL_ZR"]
    full_rows[0]["served_user_steps"] = 999
    full_rows[0]["joint_support_passed"] = False
    for row in full_rows:
        row["action_exposure"] = 0
    gate = _gate(rows)
    assert gate["passed"] is False
    assert gate["joint_support_passed"] is False
    assert gate["action_exposure"] == 0
    assert any("joint action expanded current energy support" in stop for stop in gate["hard_stops"])
    assert any("zero executed-action exposure" in stop for stop in gate["hard_stops"])
    assert any("pooled service guard failed" in stop for stop in gate["hard_stops"])


def test_contract_path_is_injectable_and_requires_frozen_marker(tmp_path: Path) -> None:
    contract = tmp_path / "v013-contract.md"
    contract.write_text("Status: **DRAFT**\n", encoding="utf-8")
    with pytest.raises(RUNNER.V013OracleError, match="frozen status"):
        RUNNER.assert_contract_frozen(contract)
    contract.write_text(
        "Status: **FROZEN BEFORE OUTCOME ACCESS**\n"
        f"{RUNNER.CONTRACT_RECEIPT_PREFIX}"
        f"{RUNNER.canonical_sha256(RUNNER.contract_receipt())}`\n",
        encoding="utf-8",
    )
    RUNNER.assert_contract_frozen(contract)
    contract.write_text(
        "Status: **DRAFT — DO NOT OPEN OUTCOMES**\n"
        "Status: **FROZEN BEFORE OUTCOME ACCESS**\n"
        f"{RUNNER.CONTRACT_RECEIPT_PREFIX}"
        f"{RUNNER.canonical_sha256(RUNNER.contract_receipt())}`\n",
        encoding="utf-8",
    )
    with pytest.raises(RUNNER.V013OracleError, match="exactly one"):
        RUNNER.assert_contract_frozen(contract)


def test_execution_environment_is_frozen_to_the_server_build(monkeypatch) -> None:
    assert RUNNER.EXPECTED_EXECUTION_ENVIRONMENT["python"] == "3.13.3"
    assert RUNNER.EXPECTED_EXECUTION_ENVIRONMENT["numpy"] == "2.5.2"
    assert RUNNER.EXPECTED_EXECUTION_ENVIRONMENT["torch"] == "2.13.0+cu130"
    monkeypatch.setattr(
        RUNNER,
        "execution_environment_receipt",
        lambda: dict(RUNNER.EXPECTED_EXECUTION_ENVIRONMENT),
    )
    RUNNER.assert_execution_environment()
    drifted = dict(RUNNER.EXPECTED_EXECUTION_ENVIRONMENT)
    drifted["numpy"] = "9.9.9"
    monkeypatch.setattr(RUNNER, "execution_environment_receipt", lambda: drifted)
    with pytest.raises(RUNNER.V013OracleError, match="numeric execution environment"):
        RUNNER.assert_execution_environment()


def test_source_authority_covers_every_shipped_import_surface() -> None:
    assert RUNNER.REPO / "src" in RUNNER.PYTHON_SOURCE_ROOTS
    assert (
        RUNNER.REPO / ".scratch" / "zero-energy-c3-v013"
        in RUNNER.PYTHON_SOURCE_ROOTS
    )
    assert {".py", ".so", ".pth"} <= RUNNER.PYTHON_SOURCE_SUFFIXES


def test_frozen_authority_write_is_atomic_and_never_overwrites(
    tmp_path: Path, monkeypatch
) -> None:
    destination = tmp_path / "authority.json"
    monkeypatch.setattr(RUNNER, "assert_contract_frozen", lambda _path: None)
    monkeypatch.setattr(
        RUNNER,
        "executable_authority_snapshot",
        lambda **_kwargs: {"schema": RUNNER.AUTHORITY_SCHEMA, "sealed": True},
    )
    RUNNER.write_frozen_authority(
        destination,
        contract_path=tmp_path / "contract.md",
        prereg_path=tmp_path / "prereg.json",
        v03_root=tmp_path / "v03",
    )
    assert destination.read_bytes() == RUNNER._canonical_bytes(
        {"schema": RUNNER.AUTHORITY_SCHEMA, "sealed": True}
    )
    with pytest.raises(RUNNER.V013OracleError, match="refusing to overwrite"):
        RUNNER.write_frozen_authority(
            destination,
            contract_path=tmp_path / "contract.md",
            prereg_path=tmp_path / "prereg.json",
            v03_root=tmp_path / "v03",
        )


def _valid_drop_step(step_index: int) -> dict[str, object]:
    digest = "0" * 64
    selected = [0] * RUNNER.USERS
    background = RUNNER.array_sha256(np.asarray(selected, dtype=np.int64))
    return {
        "step_index": step_index,
        "total_bits": 1.0,
        "total_energy_j": 2.0,
        "served_user_steps": RUNNER.USERS,
        "active_beam_count": 10,
        "active_satellite_count": 3,
        "action_exposure": 0,
        "c3_legal_spread_count": 0,
        "selected_actions": selected,
        "surface_sha256": {
            "q1": digest,
            "o2": digest,
            "o3": digest,
            "mask": digest,
            "q1_reference": digest,
            "background": background,
        },
        "mechanics": {
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
        },
        "method": {
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
        },
        "joint_support": {
            "status": "NO_EXPOSURE",
            "changed_users": 0,
            "no_new_active_beam": True,
            "no_new_active_satellite": True,
            "network_power_nonincrease": True,
            "passed": True,
        },
    }


def _valid_drop_row() -> dict[str, object]:
    digest = "0" * 64
    steps = [_valid_drop_step(index) for index in range(RUNNER.STEPS_PER_EPISODE)]
    return {
        "schema": RUNNER.EPISODE_SCHEMA,
        "arm": "DROP_C3",
        "initialization_seed": RUNNER.LINEAGES[0],
        "world_seed": RUNNER.WORLD_SEEDS[0],
        "split": "TRAIN",
        "test_split_opened": False,
        "episode_training": False,
        "learner_update": False,
        "users": RUNNER.USERS,
        "steps": RUNNER.STEPS_PER_EPISODE,
        "initial_world_sha256": digest,
        "field_root_digest": digest,
        "q1_checkpoint": {
            "checkpoint_path": f"/sealed/init-{RUNNER.LINEAGES[0]}-rung-000010.pt",
            "checkpoint_sha256": digest,
            "parameter_sha256": digest,
            "authority_sha256": digest,
            "initialization_seed": RUNNER.LINEAGES[0],
            "rung": 10,
            "head_index": 0,
            "trainer_algorithm": "sealed-three-head",
            "config_sha256": digest,
        },
        "q1_parameter_sha256_before": digest,
        "q1_parameter_sha256_after": digest,
        "total_bits": 10.0,
        "total_energy_j": 20.0,
        "ratio_of_sums_ee_bits_per_j": 0.5,
        "served_user_steps": 1000,
        "served_fraction": 1.0,
        "active_beam_steps": 100,
        "active_satellite_steps": 30,
        "c3_legal_spread_count": 0,
        "positive_target_count": 0,
        "supported_positive_target_count": 0,
        "compatible_action_count": 0,
        "action_exposure": 0,
        "changed_actions_compatible": True,
        "joint_support_passed": True,
        "method_passed": True,
        "candidate_specific_identity_passed": True,
        "mechanics_passed": True,
        "per_step": steps,
        "elapsed_s": 1.0,
    }


def test_row_validator_recomputes_totals_and_rejects_truthy_strings() -> None:
    row = _valid_drop_row()
    RUNNER._validate_row_receipt(row, row_index=0)
    forged = copy.deepcopy(row)
    forged["total_bits"] = 11.0
    forged["ratio_of_sums_ee_bits_per_j"] = 11.0 / 20.0
    with pytest.raises(RUNNER.V013OracleError, match="ten step"):
        RUNNER._validate_row_receipt(forged, row_index=0)
    truthy = copy.deepcopy(row)
    truthy["per_step"][0]["mechanics"]["common_mask"] = "false"
    with pytest.raises(RUNNER.V013OracleError, match="not Boolean"):
        RUNNER._validate_row_receipt(truthy, row_index=0)


def test_row_validator_requires_exact_ten_step_coverage() -> None:
    row = _valid_drop_row()
    row["per_step"] = row["per_step"][:-1]
    with pytest.raises(RUNNER.V013OracleError, match="exactly ten"):
        RUNNER._validate_row_receipt(row, row_index=0)


def test_canonical_reader_rejects_duplicate_keys_and_noncanonical_bytes(
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(b'{"a":1,"a":1}')
    with pytest.raises(RUNNER.V013OracleError, match="duplicate JSON key"):
        RUNNER.read_canonical_json(duplicate)
    pretty = tmp_path / "pretty.json"
    pretty.write_bytes(b'{\n  "a": 1\n}\n')
    with pytest.raises(RUNNER.V013OracleError, match="not canonical"):
        RUNNER.read_canonical_json(pretty)


def test_cli_has_no_training_or_test_subcommands() -> None:
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert 'add_parser("shard")' in source
    assert 'add_parser("merge")' in source
    assert 'add_parser("train")' not in source
    assert 'add_parser("test")' not in source


def test_server_launcher_uses_a_bounded_parallel_controller() -> None:
    launch = (
        REPO
        / ".scratch"
        / "zero-energy-c3-v013"
        / "launch_v013_zero_energy_c3_server.sh"
    ).read_text(encoding="utf-8")
    panel = (
        REPO
        / ".scratch"
        / "zero-energy-c3-v013"
        / "run_v013_zero_energy_c3_panel_server.sh"
    ).read_text(encoding="utf-8")
    assert "v013-controller" in launch
    assert "V013_MAX_PARALLEL:-18" in launch
    assert 'if [[ ! -d "${run_root}" || -L "${run_root}" ]]' in launch
    assert 'if [[ -e "${run_dir}" || -L "${run_dir}" ]]' in launch
    assert 'controller.complete" || -L "${run_dir}/controller.complete"' in launch
    assert "controller.log" not in launch
    assert 'max_parallel > 20' in panel
    assert 'xargs -0 -n 3 -P "${max_parallel}"' in panel
    assert 'if [[ -e "${run_dir}" || -L "${run_dir}" ]]' in panel
    assert 'if [[ -e "${output}" || -L "${output}" || -e "${log}" || -L "${log}" ]]' in panel
    assert "worlds=(2026104901 2026104902 2026104903 2026104904)" in panel
    assert "arms=(DROP_C3 FULL_ZR)" in panel
    assert "lineages=(2026092101 2026092102 2026092103)" in panel
    assert "task_count=$((" in panel
    assert "schema=multi-catfish-mcrl-v013-panel-complete-v1" in panel
    assert "task_count=%s" in panel
    assert "max_parallel=%s" in panel
    finalizer = (
        REPO
        / ".scratch"
        / "zero-energy-c3-v013"
        / "finalize_v013_zero_energy_c3_server.sh"
    ).read_text(encoding="utf-8")
    assert "controller.complete" in finalizer
    assert "schema=multi-catfish-mcrl-v013-panel-complete-v1" in finalizer
    assert '"${marker_lines[1]}" != "task_count=24"' in finalizer
    assert '"${#shard_dirs[@]}" != "24"' in finalizer
    assert '"${#log_entries[@]}" != "24"' in finalizer
    assert "! -s \"${log_file}\"" in finalizer


def test_server_sync_is_new_root_only_and_requires_the_frozen_marker() -> None:
    sync = (
        REPO
        / ".scratch"
        / "zero-energy-c3-v013"
        / "sync_v013_zero_energy_c3_server.sh"
    ).read_text(encoding="utf-8")
    assert "FROZEN BEFORE OUTCOME ACCESS" in sync
    assert "refusing to overwrite existing" in sync
    assert "rsync -aR" in sync
    assert "--delete" not in sync
    assert "run_v013_zero_energy_c3_oracle.py verify-authority" in sync
    assert "FROZEN-AUTHORITY.json" in sync
