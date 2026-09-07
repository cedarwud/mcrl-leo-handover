"""W-88 -- frozen V0.4 C3 confirmatory consumer contracts.

These tests exercise only receipt, matching, endpoint, bootstrap, and state
guard seams with synthetic rows.  They deliberately do not open TLE/source
bytes, construct a simulator, load a selected hybrid, or run an episode.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest
import torch


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "c3-v04" / "run_v04_c3_confirmatory.py"
AUTHORITY = "a" * 64


def _module():
    spec = importlib.util.spec_from_file_location("v04_c3_confirmatory_w88", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(runner, *, policy: str, seed: int, init: int, bits: float, energy: float, served: int):
    field = runner.common_field_receipt(
        gate_authority_sha256=AUTHORITY,
        evaluation_seed=seed,
    )
    world_digest = hashlib.sha256(f"world:{seed}".encode("ascii")).hexdigest()
    mask_digest = hashlib.sha256(f"mask:{seed}".encode("ascii")).hexdigest()
    return {
        "schema": "multi-catfish-mcrl-v04-confirmatory-episode-v1",
        "policy_label": policy,
        "evaluation_split": "TRAIN",
        "initialization_seed": init,
        "evaluation_seed": seed,
        "selected_q3_rung": 100,
        "total_q3_update_count": 100,
        "steps": 10,
        "users": 100,
        "decision_count": 1000,
        "start_epoch": "2026-01-01T00:00:00+00:00",
        "initial_state_sha256": world_digest,
        "initial_mask_sha256": mask_digest,
        "fading_field_sha256": field["root_digest"],
        "fading_field_components": field["components"],
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_fraction": served / 1000.0,
        "outage_fraction": 1.0 - served / 1000.0,
        "action_trace_sha256": hashlib.sha256(
            f"{policy}:{seed}:{init}".encode("ascii")
        ).hexdigest(),
        "test_split_opened": False,
        "held_out_ee_evaluated": True,
        "episode_training": False,
    }


def _rows(runner, *, full_delta: float = 1.0, service_loss_seed: int | None = None):
    full = []
    drop = []
    for seed in runner.EVALUATION_SEEDS:
        for index, init in enumerate(runner.INITIALIZATION_SEEDS):
            full_served = 900
            drop_served = 900
            if service_loss_seed == seed and index == 0:
                full_served = 899
            full.append(
                _row(
                    runner,
                    policy="FULL",
                    seed=seed,
                    init=init,
                    bits=100.0 + full_delta + index,
                    energy=10.0,
                    served=full_served,
                )
            )
            drop.append(
                _row(
                    runner,
                    policy="DROP_C3",
                    seed=seed,
                    init=init,
                    bits=100.0 + index,
                    energy=10.0,
                    served=drop_served,
                )
            )
    return full, drop


def test_protocol_is_frozen_to_fresh_train_block_and_no_episode_training():
    runner = _module()
    assert runner.EVALUATION_SEEDS == tuple(range(2026092501, 2026092531))
    assert runner.INITIALIZATION_SEEDS == (2026092101, 2026092102, 2026092103)
    assert runner.SELECTED_Q3_RUNG == 100
    assert runner.ARMS == ("FULL", "DROP_C3")
    assert runner.BOOTSTRAP_REPLICATES == 10_000
    assert runner.BOOTSTRAP_SEED == 2026092599
    assert runner.EVALUATION_SPLIT == "TRAIN"
    assert runner.TEST_SPLIT_OPENED is False
    assert runner.EPISODE_TRAINING is False
    assert runner.PRIOR_SCREEN_RESULT_SEAL_SCHEMA == (
        "multi-catfish-mcrl-v04-c3-500-update-screen-result-seal-v1"
    )


def test_common_field_root_excludes_initialization_and_policy():
    runner = _module()
    first = runner.common_field_receipt(
        gate_authority_sha256=AUTHORITY,
        evaluation_seed=2026092501,
    )
    second = runner.common_field_receipt(
        gate_authority_sha256=AUTHORITY,
        evaluation_seed=2026092501,
    )
    other_world = runner.common_field_receipt(
        gate_authority_sha256=AUTHORITY,
        evaluation_seed=2026092502,
    )
    assert first["root_digest"] == second["root_digest"]
    assert first["root_digest"] != other_world["root_digest"]
    assert first["excluded_components"] == ["initialization_seed", "policy_label"]
    assert first["components"] == [runner.FIELD_COMPONENT, AUTHORITY, 2026092501]


def test_pooled_ratio_of_sums_pairing_and_world_identity_are_explicit():
    runner = _module()
    full, drop = _rows(runner, full_delta=2.0)
    assert len(full) == len(drop) == 90
    assert runner.aggregate_policy_rows(full)["pooled_ratio_of_sums_ee_bits_per_j"] > runner.aggregate_policy_rows(drop)["pooled_ratio_of_sums_ee_bits_per_j"]
    runner._pair_rows(full, drop, gate_authority_sha256=AUTHORITY)
    runner._validate_common_world_identity(
        [*full, *drop],
        gate_authority_sha256=AUTHORITY,
    )
    broken = copy.deepcopy(drop)
    broken[0]["initial_state_sha256"] = "f" * 64
    with pytest.raises(runner.V04C3ConfirmatoryError, match="initial_state_sha256"):
        runner._pair_rows(full, broken, gate_authority_sha256=AUTHORITY)


def test_decision_rule_allows_nonfatal_per_world_service_diagnostic():
    runner = _module()
    full, drop = _rows(runner, full_delta=2.0, service_loss_seed=runner.EVALUATION_SEEDS[0])
    # Offset the one physical-world loss elsewhere so the predeclared pooled
    # service non-inferiority condition remains true.  The world-level loss is
    # still retained as a diagnostic and is not silently discarded.
    full[-1]["served_user_steps"] = 901
    full_summary = runner.aggregate_policy_rows(full)
    drop_summary = runner.aggregate_policy_rows(drop)
    per_init = runner._per_initialization(full, drop)
    per_world = runner._per_world(full, drop)
    decision = runner.apply_decision_rule(
        full_summary=full_summary,
        drop_summary=drop_summary,
        per_initialization=per_init,
        per_world=per_world,
        bootstrap={"lower_percent": 1.0},
    )
    assert decision["status"] == runner.STATUS_CONFIRM
    assert decision["per_world_service_loss_count"] == 1
    assert decision["positive_per_world_ee_count"] == 30
    assert decision["checks"]["pooled_service_noninferior"] is True


def test_each_predeclared_decision_condition_can_fail_closed():
    runner = _module()
    base = {
        "full": {
            "pooled_ratio_of_sums_ee_bits_per_j": 2.0,
            "served_fraction": 0.9,
        },
        "drop": {
            "pooled_ratio_of_sums_ee_bits_per_j": 1.0,
            "served_fraction": 0.9,
        },
        "per_initialization": {
            str(seed): {
                "ee_difference_bits_per_j": 1.0,
                "served_fraction_difference": 0.0,
            }
            for seed in runner.INITIALIZATION_SEEDS
        },
        "per_world": [
            {"ee_difference_bits_per_j": 1.0, "served_difference": 0.0}
            for _ in runner.EVALUATION_SEEDS
        ],
        "bootstrap": {"lower_percent": 1.0},
    }
    failures = []
    failed_pooled_ee = copy.deepcopy(base)
    failed_pooled_ee["full"]["pooled_ratio_of_sums_ee_bits_per_j"] = 0.5
    failures.append(failed_pooled_ee)
    failed_init_ee = copy.deepcopy(base)
    failed_init_ee["per_initialization"][str(runner.INITIALIZATION_SEEDS[1])][
        "ee_difference_bits_per_j"
    ] = -1.0
    failed_init_ee["per_initialization"][str(runner.INITIALIZATION_SEEDS[2])][
        "ee_difference_bits_per_j"
    ] = -1.0
    failures.append(failed_init_ee)
    failed_median_world = copy.deepcopy(base)
    for row in failed_median_world["per_world"][:15]:
        row["ee_difference_bits_per_j"] = -1.0
    failures.append(failed_median_world)
    failed_bootstrap = copy.deepcopy(base)
    failed_bootstrap["bootstrap"]["lower_percent"] = 0.0
    failures.append(failed_bootstrap)
    failed_pooled_service = copy.deepcopy(base)
    failed_pooled_service["full"]["served_fraction"] = 0.8
    failures.append(failed_pooled_service)
    failed_init_service = copy.deepcopy(base)
    failed_init_service["per_initialization"][str(runner.INITIALIZATION_SEEDS[1])][
        "served_fraction_difference"
    ] = -1.0
    failed_init_service["per_initialization"][str(runner.INITIALIZATION_SEEDS[2])][
        "served_fraction_difference"
    ] = -1.0
    failures.append(failed_init_service)
    for failure in failures:
        decision = runner.apply_decision_rule(
            full_summary=failure["full"],
            drop_summary=failure["drop"],
            per_initialization=failure["per_initialization"],
            per_world=failure["per_world"],
            bootstrap=failure["bootstrap"],
        )
        assert decision["status"] == runner.STATUS_NOT_CONFIRMED


def test_result_payload_requires_exactly_90_rows_per_arm():
    runner = _module()
    authority = runner.AuthorityContext(
        gate_authority_sha256=AUTHORITY,
        gate_result_file_sha256="b" * 64,
        gate_result_seal_file_sha256="c" * 64,
        source_manifest_sha256="d" * 64,
        schedule_sha256="e" * 64,
        train_surface_sha256="f" * 64,
        selected_q3_rung=100,
        prior_screen_result_file_sha256="1" * 64,
        prior_screen_result_seal_file_sha256="2" * 64,
        prior_primary_receipt_file_sha256="3" * 64,
    )
    with pytest.raises(runner.V04C3ConfirmatoryError, match="90 rows per arm"):
        runner._result_payload(
            prepare={
                "evaluator_code_manifest_file_sha256": "4" * 64,
                "evaluator_code_manifest_sha256": "5" * 64,
            },
            authority=authority,
            full_rows=[],
            drop_rows=[],
            elapsed_s=0.0,
        )


def test_bootstrap_is_deterministic_and_resamples_physical_world_clusters():
    runner = _module()
    full, drop = _rows(runner, full_delta=2.0)
    first = runner.paired_world_bootstrap(full, drop)
    second = runner.paired_world_bootstrap(full, drop)
    assert first == second
    assert first["replicates"] == 10_000
    assert first["seed"] == 2026092599
    assert first["world_count"] == 30
    assert first["lower_percent"] > 0.0


def test_code_manifest_is_self_authenticated_and_detects_tampering():
    runner = _module()
    manifest = runner.build_evaluator_code_manifest()
    assert manifest["schema"] == runner.CODE_MANIFEST_SCHEMA
    assert ".scratch/c3-v04/run_v04_c3_confirmatory.py" in manifest["files"]
    assert runner._validate_code_manifest(manifest, current=True) == manifest["manifest_sha256"]
    tampered = copy.deepcopy(manifest)
    tampered["files"][".scratch/c3-v04/run_v04_c3_confirmatory.py"] = "f" * 64
    tampered["manifest_sha256"] = runner.canonical_sha256(
        {"schema": tampered["schema"], "files": tampered["files"]}
    )
    with pytest.raises(runner.V04C3ConfirmatoryError, match="code changed"):
        runner._validate_code_manifest(tampered, current=True)


def test_positive_energy_and_bootstrap_denominator_guards():
    runner = _module()
    full, drop = _rows(runner, full_delta=2.0)
    full[0]["total_energy_j"] = 0.0
    with pytest.raises(runner.V04C3ConfirmatoryError, match="positive total energy"):
        runner.aggregate_policy_rows(full)

    full, drop = _rows(runner, full_delta=2.0)
    for row in drop:
        if row["evaluation_seed"] == runner.EVALUATION_SEEDS[0]:
            row["total_energy_j"] = 0.0
    # The row guard normally catches this first.  Bypass only that synthetic
    # row-schema layer to exercise the independent bootstrap world-energy
    # guard as well.
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(runner, "_validate_row", lambda _row: None)
    try:
        with pytest.raises(runner.V04C3ConfirmatoryError, match="world energies"):
            runner.paired_world_bootstrap(full, drop)
        full, drop = _rows(runner, full_delta=2.0)
        for row in drop:
            row["total_bits"] = 0.0
            row["ratio_of_sums_ee_bits_per_j"] = 0.0
        with pytest.raises(runner.V04C3ConfirmatoryError, match="denominator"):
            runner.paired_world_bootstrap(full, drop)
    finally:
        monkeypatch.undo()


def test_prepare_writes_only_pre_episode_receipts_and_is_write_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runner = _module()
    fake_authority = runner.AuthorityContext(
        gate_authority_sha256=AUTHORITY,
        gate_result_file_sha256="b" * 64,
        gate_result_seal_file_sha256="c" * 64,
        source_manifest_sha256="d" * 64,
        schedule_sha256="e" * 64,
        train_surface_sha256="f" * 64,
        selected_q3_rung=100,
        prior_screen_result_file_sha256="1" * 64,
        prior_screen_result_seal_file_sha256="2" * 64,
        prior_primary_receipt_file_sha256="3" * 64,
    )
    monkeypatch.setattr(runner, "authenticate_current_authority", lambda **_: fake_authority)
    prereg = tmp_path / "prereg.json"
    prereg.write_bytes(b"synthetic prereg bytes")
    output = tmp_path / "confirmatory"
    result = runner.prepare_confirmatory(
        gate_dir=tmp_path / runner.EXPECTED_GATE_BASENAME,
        source_dir=tmp_path / runner.EXPECTED_SOURCE_BASENAME,
        prior_screen_dir=tmp_path / runner.EXPECTED_PRIOR_SCREEN_BASENAME,
        prereg_path=prereg,
        output_dir=output,
    )
    assert result["status"] == runner.STATUS_PREPARED
    assert result["episode_opened"] is False
    assert (output / "prepare.json").is_file()
    assert (output / "prepare-seal.json").is_file()
    assert not (output / "result.json").exists()
    with pytest.raises(runner.V04C3ConfirmatoryError, match="overwrite"):
        runner.prepare_confirmatory(
            gate_dir=tmp_path / runner.EXPECTED_GATE_BASENAME,
            source_dir=tmp_path / runner.EXPECTED_SOURCE_BASENAME,
            prior_screen_dir=tmp_path / runner.EXPECTED_PRIOR_SCREEN_BASENAME,
            prereg_path=prereg,
            output_dir=output,
        )


def test_trainer_snapshot_guard_detects_parameter_or_optimizer_mutation():
    runner = _module()
    networks = torch.nn.ModuleList(
        [torch.nn.Linear(3, 2), torch.nn.Linear(3, 2), torch.nn.Linear(3, 2)]
    )

    class FakeTrainer:
        q_nets = networks
        q3_optimizer = torch.optim.Adam(networks[2].parameters(), lr=0.001)
        q3_update_count = 100

    trainer = FakeTrainer()
    networks.eval()
    before = runner._snapshot_trainer(trainer)
    runner._assert_trainer_unchanged(trainer, before)
    with torch.no_grad():
        networks[2].weight[0, 0] += 1.0
    with pytest.raises(runner.V04C3ConfirmatoryError, match="q_networks"):
        runner._assert_trainer_unchanged(trainer, before)

    networks[2].weight.data.copy_(before["q_networks"][2]["weight"])
    networks[2].bias.data.copy_(before["q_networks"][2]["bias"])
    networks[0].train()
    with pytest.raises(runner.V04C3ConfirmatoryError, match="training_flags"):
        runner._assert_trainer_unchanged(trainer, before)


def test_verify_is_receipt_only_for_a_synthetic_complete_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runner = _module()
    fake_authority = runner.AuthorityContext(
        gate_authority_sha256=AUTHORITY,
        gate_result_file_sha256="b" * 64,
        gate_result_seal_file_sha256="c" * 64,
        source_manifest_sha256="d" * 64,
        schedule_sha256="e" * 64,
        train_surface_sha256="f" * 64,
        selected_q3_rung=100,
        prior_screen_result_file_sha256="1" * 64,
        prior_screen_result_seal_file_sha256="2" * 64,
        prior_primary_receipt_file_sha256="3" * 64,
    )
    monkeypatch.setattr(runner, "authenticate_current_authority", lambda **_: fake_authority)
    prereg = tmp_path / "prereg.json"
    prereg.write_bytes(b"synthetic prereg bytes")
    output = tmp_path / "confirmatory"
    runner.prepare_confirmatory(
        gate_dir=tmp_path / runner.EXPECTED_GATE_BASENAME,
        source_dir=tmp_path / runner.EXPECTED_SOURCE_BASENAME,
        prior_screen_dir=tmp_path / runner.EXPECTED_PRIOR_SCREEN_BASENAME,
        prereg_path=prereg,
        output_dir=output,
    )
    prepare = runner._read_canonical_json(output / "prepare.json")
    full, drop = _rows(runner, full_delta=2.0)
    result = runner._result_payload(
        prepare=prepare,
        authority=fake_authority,
        full_rows=full,
        drop_rows=drop,
        elapsed_s=0.0,
    )
    result_sha = runner._write_once_json(output / "result.json", result)
    runner._write_once_json(
        output / "result-seal.json",
        {
            "schema": runner.RESULT_SEAL_SCHEMA,
            "result_file_sha256": result_sha,
            "prepare_file_sha256": runner._file_sha256(output / "prepare.json"),
            "prepare_seal_file_sha256": runner._file_sha256(output / "prepare-seal.json"),
            "evaluator_code_manifest_file_sha256": prepare["evaluator_code_manifest_file_sha256"],
            "evaluator_code_manifest_sha256": prepare["evaluator_code_manifest_sha256"],
            "test_split_opened": False,
            "held_out_ee_evaluated": True,
            "episode_training": False,
        },
    )
    monkeypatch.setattr(runner, "_make_environment", lambda *_: pytest.fail("verify opened environment"))
    monkeypatch.setattr(runner, "_frozen_archive", lambda *_: pytest.fail("verify opened TLE"))
    monkeypatch.setattr(runner.screen, "load_gate_selected_hybrid", lambda *_args, **_kwargs: pytest.fail("verify loaded trainer"))
    verified = runner.verify_confirmatory(output)
    assert verified["receipt_only"] is True
    assert verified["rows_per_arm"] == 90
