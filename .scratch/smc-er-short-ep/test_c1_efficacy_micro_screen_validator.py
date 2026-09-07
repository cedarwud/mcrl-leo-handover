from __future__ import annotations

import importlib.util
import json
from dataclasses import asdict
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import torch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "c1_efficacy_micro_screen_validator",
    HERE / "c1_efficacy_micro_screen_validator.py",
)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)

from test_c1_consumer_gate import write_schedule_fixture  # noqa: E402


def endpoint(ee: float, service: float) -> dict:
    duration = 300.8
    energy = 100.0
    bits = ee * energy
    total = 1000
    served = int(service * total)
    return {
        "arm": "informed",
        "checkpoint_sha256": "a" * 64,
        "training_seed": 7,
        "evaluation_seed": 11,
        "users": 100,
        "steps": 10,
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
        "r1_sum": 1.0,
        "r2_sum": -1.0,
        "r3_sum": -2.0,
    }


def test_minimal_self_attested_continue_receipt_is_rejected(tmp_path):
    path = tmp_path / "result.json"
    path.write_text(
        json.dumps(
            {
                "schema": V.RESULT_SCHEMA,
                "source": "C1",
                "status": "PASS",
                "decision": "CONTINUE_10EP",
                "claim_ceiling": V.CLAIM_CEILING,
                "routing_authority": False,
                "authority": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(V.C1EfficacyScreenValidationError):
        V.validate_c1_efficacy_screen_result(path)


def test_endpoint_validator_recomputes_physical_identities():
    failures: list[str] = []
    value = endpoint(10.0, 0.95)
    result = V._validate_endpoint(
        value,
        label="fixture",
        branch="informed",
        checkpoint_sha="a" * 64,
        training_seed=7,
        evaluation_seed=11,
        failures=failures,
    )
    assert result == value
    assert failures == []
    value["system_ee_bits_per_j"] = 999.0
    V._validate_endpoint(
        value,
        label="tampered",
        branch="informed",
        checkpoint_sha="a" * 64,
        training_seed=7,
        evaluation_seed=11,
        failures=failures,
    )
    assert "tampered.system_ee_bits_per_j: identity mismatch" in failures


def test_decision_recomputation_preserves_paired_delta_rule():
    paired = []
    for index, delta in enumerate((2.0, 1.0, 3.0, 1.0, -0.5)):
        informed = endpoint(10.0 + delta, 0.95)
        neutral = endpoint(10.0, 0.95)
        informed["evaluation_seed"] = neutral["evaluation_seed"] = index
        neutral["arm"] = "neutral"
        paired.append(
            {
                "evaluation_seed": index,
                "delta_ee_bits_per_j": delta,
                "informed": informed,
                "neutral": neutral,
            }
        )
    checks, metrics = V._recompute_decision(paired, ())
    assert all(checks.values())
    assert metrics["positive_seed_count"] == 4


def test_authority_surface_binds_sweep_parity_and_both_validators():
    authorities = V._canonical_authorities(V.REPO)
    assert authorities["sweep_evaluator"].name == "sweep_evaluation.py"
    assert authorities["parity_checker"].name == "check_zero_dose_parity.py"
    assert authorities["validator"].name == "c1_efficacy_micro_screen_validator.py"
    assert authorities["pretransfer_validator"].name == "c1_pretransfer_gate_validator.py"
    assert authorities["source_gate_verifier"].name == "verify_c1_source_gate.py"


def test_validator_requires_source_gate_verification_as_bound_artifact():
    assert "source_gate_verification" in V.BOUND_ARTIFACT_STEMS


def test_validator_rejects_rehashed_nonreplayed_source_verification(
    tmp_path, monkeypatch
):
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"schema": "fixture"}), encoding="utf-8")
    expected = {"schema": "verification", "status": "PASS", "failures": []}
    verification = tmp_path / "verification.json"
    verification.write_text(json.dumps(expected), encoding="utf-8")
    replayed = dict(expected)
    monkeypatch.setattr(
        V,
        "verify_c1_source_gate",
        lambda _payload, **_kwargs: dict(replayed),
    )
    failures: list[str] = []
    assert V._validate_source_gate_verification(source, verification, failures)
    assert failures == []

    expected["failures"] = ["tampered"]
    verification.write_text(json.dumps(expected), encoding="utf-8")
    failures = []
    assert not V._validate_source_gate_verification(source, verification, failures)
    assert "source_gate_verification: exact current replay mismatch" in failures


def test_validator_hashes_the_complete_closure_test_set():
    digest, count = V._closure_test_tree_binding(V.REPO)
    assert len(digest) == 64
    assert count == 12


def test_independent_schedule_validator_accepts_admission_only_warmup(tmp_path):
    branch, result, _ = write_schedule_fixture(tmp_path)
    declared = {
        "branch": "informed",
        "status": "PASS",
        "logical_steps": 40,
        "warmup_steps": 1,
        "warmup_indices": [0],
        "source_unit_updates": 39,
        "source_unit_update_indices": list(range(1, 40)),
        "unique_admitted_c1_bundle_ids": 40,
        "unique_applied_c1_bundle_ids": 39,
        "main_update_receipts_path": str(branch / "main-update-receipts.json"),
        "main_update_receipts_sha256": V.sha256_file(
            branch / "main-update-receipts.json"
        ),
        "episode_logs_path": str(branch / "episode-logs.json"),
        "episode_logs_sha256": V.sha256_file(branch / "episode-logs.json"),
        "specialist_replay_receipts_path": str(
            branch / "specialist-replay-receipts.json"
        ),
        "specialist_replay_receipts_sha256": V.sha256_file(
            branch / "specialist-replay-receipts.json"
        ),
        "failures": [],
    }
    failures: list[str] = []
    schedule = V._validate_schedule(
        branch_dir=branch,
        result=result,
        declared=declared,
        label="informed",
        failures=failures,
    )

    assert failures == []
    assert schedule["admitted_bundle_ids"] == [
        f"informed-c1-{index}" for index in range(40)
    ]
    assert schedule["applied_bundle_ids"] == [
        f"informed-c1-{index}" for index in range(1, 40)
    ]


def test_branch_artifact_validator_checks_checkpoint_and_carrier_state(
    tmp_path, monkeypatch
):
    from mcrl.runtime.trainer_spec import TrainerConfig

    config = TrainerConfig(
        episodes=V.EPISODES,
        training_experiment_kind="smc-er-short-ep",
        training_experiment_id="F111",
        method_family="SMC-ER-developmental",
        phase="developmental-short-ep",
        comparison_role="Full SMC-ER",
        device="cpu",
    )
    config_payload = asdict(config)
    q_networks = [{"weight": torch.tensor([float(index)])} for index in range(3)]
    target_networks = [
        {"weight": torch.tensor([float(index + 10)])} for index in range(3)
    ]
    optimizers = [{"state": {}, "param_groups": []} for _ in range(3)]
    checkpoint = SimpleNamespace(
        train_seed=101,
        env_seed=102,
        mobility_seed=103,
        checkpoint_kind="final-episode-policy",
        episode=V.EPISODES - 1,
        trainer_config=config_payload,
        q_networks=q_networks,
        target_networks=target_networks,
        optimizers=optimizers,
    )
    checkpoint_path = tmp_path / "final-checkpoint.pt"
    checkpoint_path.write_bytes(b"bound-checkpoint")
    admitted = [f"informed-c1-{index}" for index in range(40)]
    runtime = {
        "C1_specialist": 10_102,
        "C2_specialist": 20_104,
        "C3_specialist": 30_108,
    }
    carrier = {
        "schema": "smc-er-carrier-state-v1",
        "episodes_completed": V.EPISODES,
        "gates": {"C1": "route", "C2": "shadow", "C3": "shadow"},
        "main_training_state": {
            "train_seed": 101,
            "env_seed": 102,
            "mobility_seed": 103,
            "trainer_config": config_payload,
            "q_networks": q_networks,
            "target_networks": target_networks,
            "optimizers": optimizers,
        },
        "specialists": {
            source: {
                "objective_index": objective,
                "seed": runtime[source + "_specialist"],
                "rng_state": {},
                "replay_rng_state": {},
            }
            for source, objective in {"C1": 0, "C2": 1, "C3": 2}.items()
        },
        "bundle_replays": {
            source: {"format_version": 1, "items": [], "seen": []}
            for source in ("Main", "C1", "C2", "C3")
        },
        "main_consumed_specialist_bundles": {
            "format_version": 1,
            "seen_bundle_ids": sorted(admitted),
        },
        "source_rng_states": {
            source: {"environment": {}, "mobility": {}}
            for source in ("Main", "C1", "C2", "C3")
        },
    }
    carrier_path = tmp_path / "carrier-state.pt"
    torch.save(carrier, carrier_path)
    branch = {
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": V.sha256_file(checkpoint_path),
        "carrier_state": str(carrier_path),
        "carrier_state_sha256": V.sha256_file(carrier_path),
    }
    monkeypatch.setattr(V, "read_checkpoint", lambda *_args, **_kwargs: checkpoint)
    failures: list[str] = []
    returned_path, returned_checkpoint = V._validate_branch_artifacts(
        label="informed",
        expected_arm="F111",
        expected_config=config,
        branch=branch,
        raw_dir=tmp_path,
        training_seed=101,
        environment_seed=102,
        mobility_seed=103,
        runtime_derived_seeds=runtime,
        schedule={"admitted_bundle_ids": admitted},
        failures=failures,
    )

    assert failures == []
    assert returned_path == checkpoint_path
    assert returned_checkpoint is checkpoint

    carrier["main_consumed_specialist_bundles"]["seen_bundle_ids"] = admitted[:-1]
    torch.save(carrier, carrier_path)
    branch["carrier_state_sha256"] = V.sha256_file(carrier_path)
    tampered_failures: list[str] = []
    V._validate_branch_artifacts(
        label="informed",
        expected_arm="F111",
        expected_config=config,
        branch=branch,
        raw_dir=tmp_path,
        training_seed=101,
        environment_seed=102,
        mobility_seed=103,
        runtime_derived_seeds=runtime,
        schedule={"admitted_bundle_ids": admitted},
        failures=tampered_failures,
    )
    assert "raw.branch_results.informed: consumed ledger mismatch" in tampered_failures
