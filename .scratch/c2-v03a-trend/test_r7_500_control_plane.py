"""Negative, lineage, routing, and publication tests for the R7-r5 control plane."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import sys
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from typing import Mapping

import pytest
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import freeze_r7_500_authority as freezer  # noqa: E402
import r7_500_ablation_evaluate as ablation_evaluator  # noqa: E402
import r7_500_authority as authority  # noqa: E402
import r7_500_checkpoint as checkpoint_tools  # noqa: E402
import r7_500_evaluate as evaluator  # noqa: E402
import r7_500_lr_router as router  # noqa: E402
import r7_500_output as output_tools  # noqa: E402
import r7_500_prefix_bridge as bridge  # noqa: E402
import r7_500_prefix_reconcile as reconcile  # noqa: E402
import r7_500_server_preflight as preflight  # noqa: E402


LOCAL_TLE = REPO / ".scratch" / "tle-frozen-20260820-authority-v1"
MASTER = REPO / authority.MASTER_AUTHORITY


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


@pytest.mark.skipif(not MASTER.is_file(), reason="R7-r5 master is not frozen yet")
def test_frozen_master_file_validates_and_is_the_exact_r5_path_and_schema():
    assert MASTER.is_file()
    request = json.loads(MASTER.read_text(encoding="utf-8"))
    validated = authority.validate_r7_500_authority(
        request, repo=REPO, tle_root=LOCAL_TLE
    )
    assert validated["status"] == "PASS"
    assert request["schema"] == authority.REQUEST_SCHEMA
    assert validated["schema"] == authority.RESULT_SCHEMA
    assert validated["master_authority_path"] == authority.MASTER_AUTHORITY
    assert authority.MASTER_AUTHORITY.endswith("20260831-r5/master.json")
    assert validated["developmental_training_condition"] == (
        "NO_NEW_R7_TRAINING_SOURCE_EP500_PREFIX_REUSE_ONLY"
    )
    assert validated["source_checkpoint_reuse_only"] is True
    assert validated["new_r7_training_authorized"] is False
    assert validated["fresh_training_required"] is False
    assert validated["resource_policy"] == authority.RESOURCE_POLICY


def test_r5_request_is_source_checkpoint_reuse_only_and_forbids_new_training():
    request = freezer.build_request()
    assert request["schema"] == authority.REQUEST_SCHEMA
    assert request["master_authority_path"].endswith("20260831-r5/master.json")
    assert request["prefix_arms"] == ["B000", "F111"]
    assert request["bridged_arms"] == ["B000", "F111", "A101", "A011", "A110"]
    assert request["source_checkpoint_reuse_only"] is True
    assert request["new_r7_training_authorized"] is False
    assert request["fresh_training_required"] is False
    assert request["reconciliation_receipt"].startswith(
        "artifacts/multi-catfish-v03a-r7-prefix-reconciliation-"
    )
    assert not request["reconciliation_receipt"].startswith(request["bridge_output"])
    assert request["routing_rule"]["source_checkpoint_reuse_only"] is True
    assert request["routing_rule"]["new_training_required"] is False
    assert request["resource_policy"]["source_checkpoint_reuse_only"] is True
    assert request["resource_policy"]["new_r7_training_authorized"] is False
    assert not any("r7_500_arm.py" in path for path in request["pinned_files"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("episodes", 1500),
        ("resume_allowed", True),
        ("source_checkpoint_reuse_only", False),
        ("new_r7_training_authorized", True),
        ("fresh_training_required", True),
        ("selected_learning_rate", 0.001),
        ("ablation_order", ["A011", "A101", "A110"]),
        ("resource_policy", {}),
        ("outcome_values_used_to_freeze", True),
    ],
)
def test_master_authority_rejects_protocol_drift(field, value):
    request = freezer.build_request()
    request[field] = value
    with pytest.raises(authority.R7500AuthorityError, match=field):
        authority.validate_r7_500_authority(request, repo=REPO, tle_root=LOCAL_TLE)


def test_master_authority_rejects_unknown_field_and_false_timestamp():
    request = freezer.build_request()
    request["post_reveal_payload"] = {"redacted": True}
    with pytest.raises(authority.R7500AuthorityError, match="unknown"):
        authority.validate_r7_500_authority(request, repo=REPO, tle_root=LOCAL_TLE)
    request = freezer.build_request()
    request["created_utc"] = "not-a-utc-timestamp"
    with pytest.raises(authority.R7500AuthorityError, match="created_utc"):
        authority.validate_r7_500_authority(request, repo=REPO, tle_root=LOCAL_TLE)


def test_master_authority_rejects_changed_runtime_pin():
    request = freezer.build_request()
    request["pinned_files"][".scratch/c2-v03a-trend/r7_500_checkpoint.py"] = "0" * 64
    with pytest.raises(authority.R7500AuthorityError, match="pinned file drifted"):
        authority.validate_r7_500_authority(request, repo=REPO, tle_root=LOCAL_TLE)


def test_freezer_refuses_wrong_path(tmp_path):
    with pytest.raises(ValueError, match="must be frozen"):
        freezer.freeze(output=tmp_path / "master.json", tle_root=LOCAL_TLE)


@pytest.mark.skipif(not MASTER.is_file(), reason="R7-r5 master is not frozen yet")
def test_freezer_refuses_existing_master():
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        freezer.freeze(output=MASTER, tle_root=LOCAL_TLE)


def _checkpoint_payload(*, learning_rate: float = 0.001, episode: int = 499):
    trainer = {"learning_rate": learning_rate, "episodes": 500}
    return SimpleNamespace(
        episode=episode,
        checkpoint_kind="periodic-main-policy-trend",
        train_seed=authority.TRAINING_SEEDS["training"],
        env_seed=authority.TRAINING_SEEDS["environment"],
        mobility_seed=authority.TRAINING_SEEDS["mobility"],
        state_dim=4,
        action_dim=3,
        trainer_config=trainer,
        q_networks=[{"w": torch.ones(2)} for _ in range(3)],
        target_networks=[{"w": torch.ones(2)} for _ in range(3)],
        optimizers=[{"state": torch.ones(1)}],
    ), trainer


def test_checkpoint_identity_rejects_wrong_episode_and_nonfinite_state():
    payload, trainer = _checkpoint_payload()
    base = {"seeds": authority.TRAINING_SEEDS, "learning_rate": 0.001}
    identity = checkpoint_tools.validate_checkpoint_payload(
        payload,
        validated=base,
        trainer_config=trainer,
        episode_index=499,
        checkpoint_kind="periodic-main-policy-trend",
        label="fixture",
    )
    assert identity["finite_state"] == "PASS"
    payload.episode = 498
    with pytest.raises(checkpoint_tools.R7500CheckpointError, match="episode"):
        checkpoint_tools.validate_checkpoint_payload(
            payload,
            validated=base,
            trainer_config=trainer,
            episode_index=499,
            checkpoint_kind="periodic-main-policy-trend",
            label="fixture",
        )
    payload.episode = 499
    payload.q_networks[0]["w"] = torch.tensor([float("nan")])
    with pytest.raises(checkpoint_tools.R7500CheckpointError, match="non-finite"):
        checkpoint_tools.validate_checkpoint_payload(
            payload,
            validated=base,
            trainer_config=trainer,
            episode_index=499,
            checkpoint_kind="periodic-main-policy-trend",
            label="fixture",
        )


def test_bridge_requires_canonical_command(tmp_path):
    repo = tmp_path / "repo"
    runner = repo / bridge.ARM_RUNNER_RELATIVE
    runner.parent.mkdir(parents=True)
    runner.write_text("# fixture\n", encoding="utf-8")
    authority_path = repo / "base.json"
    arm_root = repo / "matrix" / "arms" / "F111"
    tle_root = repo / "tle"
    command = [
        sys.executable,
        str(runner.resolve()),
        "--authority",
        str(authority_path.resolve()),
        "--arm",
        "F111",
        "--output-dir",
        str(arm_root.resolve()),
        "--tle-root",
        str(tle_root.resolve()),
    ]
    assert bridge._validate_canonical_command(
        command,
        arm="F111",
        authority_path=authority_path,
        arm_root=arm_root,
        tle_root=tle_root,
        repo=repo,
    ) == command
    with pytest.raises(bridge.R7500PrefixBridgeError, match="noncanonical"):
        bridge._validate_canonical_command(
            [*command, "--resume-state", "forbidden.pt"],
            arm="F111",
            authority_path=authority_path,
            arm_root=arm_root,
            tle_root=tle_root,
            repo=repo,
        )


def test_bridge_materializes_exact_two_lr_by_five_arm_grid(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    authority_path = repo / "authority.json"
    authority_path.parent.mkdir(parents=True)
    authority_path.write_text("{}\n", encoding="utf-8")
    authority_sha = authority.sha256_file(authority_path)
    validated = {
        "bridge_output": "artifacts/r7-prefix-bridge",
        "pin_map_sha256": "d" * 64,
    }
    monkeypatch.setattr(
        bridge,
        "load_and_validate_authority",
        lambda *args, **kwargs: (validated, authority_sha),
    )
    observed = []

    def snapshot_one(**kwargs):
        observed.append((kwargs["lr_key"], kwargs["arm"]))
        return {
            "learning_rate": float(kwargs["lr_key"]),
            "arm": kwargs["arm"],
            "reconciled": False,
        }

    monkeypatch.setattr(bridge, "_snapshot_one", snapshot_one)
    receipt = bridge.build_prefix_bridge(
        authority_path=authority_path,
        output_dir=repo / validated["bridge_output"],
        tle_root=repo / "tle",
        repo=repo,
    )
    expected = [
        (lr_key, arm)
        for lr_key in ("0.001", "0.01")
        for arm in authority.BRIDGED_ARMS
    ]
    assert observed == expected
    assert len(receipt["prefixes"]) == 10
    assert receipt["prefix_arms"] == list(authority.PREFIX_ARMS)
    assert receipt["bridged_arms"] == list(authority.BRIDGED_ARMS)
    assert receipt["learning_rates"] == list(authority.ALLOWED_LEARNING_RATES)
    assert receipt[
        "outcome_bearing_source_status_parsed_by_whitelist_extractor"
    ] is True
    assert receipt["outcome_metric_fields_copied"] is False
    assert receipt["outcome_metric_fields_emitted"] is False
    assert receipt["outcome_metric_fields_used_for_admission"] is False
    assert receipt["outcome_metric_fields_admitted"] is False
    assert receipt["checkpoint_selection_performed"] is False
    assert receipt["evaluation_authorized"] is False
    assert receipt["routing_authorized"] is False
    output = repo / validated["bridge_output"]
    assert (output / "prefix-bridge-receipt.json").is_file()
    assert not (output / output_tools.INCOMPLETE_MARKER).exists()


def _structural_status_fixture(*, arm: str = "F111") -> dict:
    """Build a synthetic source status containing deliberately hidden outcomes."""

    return {
        "schema": bridge.SOURCE_STATUS_SCHEMA,
        "status": "complete",
        "run_mode": "fresh_intermediate_trend",
        "arm": arm,
        "label": f"synthetic-{arm}",
        "episodes_planned": 1500,
        "episodes_executed": 1500,
        "users": 100,
        "seeds": dict(authority.TRAINING_SEEDS),
        "trainer_config": {
            field: (
                [1]
                if field in {"hidden_layers", "objective_weights", "reward_calibration_scales"}
                else False
                if field in {"reward_calibration_enabled"}
                else "synthetic"
                if field
                in {
                    "activation",
                    "checkpoint_assumption_id",
                    "checkpoint_primary_report",
                    "checkpoint_secondary_report",
                    "comparison_role",
                    "device",
                    "load_balance_calibration_mode",
                    "load_normalization",
                    "method_family",
                    "phase",
                    "policy_sharing_mode",
                    "r1_reward_label",
                    "r1_reward_provenance",
                    "reward_calibration_mode",
                    "reward_calibration_source",
                    "reward_normalization_mode",
                    "snr_encoding",
                    "theta_encoding",
                    "training_experiment_id",
                    "training_experiment_kind",
                }
                else 0.0
            )
            for field in bridge.TRAINER_CONFIG_FIELDS
        },
        "authority_path": "/synthetic/r2-authority.json",
        "runtime_authority": {
            "prereg_path": "/synthetic/prereg.json",
            "prereg_sha256": "d" * 64,
            "tle_file_count": 1,
            "tle_file_set_sha256": "e" * 64,
            "tle_root_path": "/synthetic/tle",
        },
        "runtime": {
            "python": "synthetic",
            "numpy": "synthetic",
            "torch": "synthetic",
        },
        "formal_training_authorized": False,
        "claim_ceiling": authority.CLAIM_CEILING,
        "result": {
            "episodes": 1500,
            "start_episode": 0,
            "episodes_executed": 1500,
            "episodes_completed": 1500,
            "artifact_scope": "complete_run",
            "checkpoint_sha256": "b" * 64,
            "checkpoint_every_episodes": 100,
            "periodic_checkpoint_count": 15,
            "periodic_checkpoints": [
                {
                    "episodes_completed": episodes,
                    "episode_index": episodes - 1,
                    "path": f"/synthetic/ep-{episodes:06d}-main.pt",
                    "sha256": f"{episodes:064x}",
                    "checkpoint_kind": "periodic-main-policy-trend",
                    "load_round_trip": "PASS",
                }
                for episodes in range(100, 1501, 100)
            ],
            # These are outcome-bearing source fields and must not cross the bridge.
            "episode_rows": [{"reward": "synthetic", "ee": "synthetic"}],
            "mean_ee_bits_per_j": "synthetic-outcome",
            "power_trace": ["synthetic-outcome"],
            "reward_trace": ["synthetic-outcome"],
        },
        "outcome_metric": "synthetic-outcome",
        "telemetry": {"throughput": "synthetic-outcome"},
    }


def _contains_key(value, forbidden: set[str]) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in forbidden or _contains_key(nested, forbidden)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_contains_key(nested, forbidden) for nested in value)
    return False


def test_bridge_structural_sidecar_is_redacted_and_bound_to_live_status_sha(tmp_path):
    status_path = tmp_path / "status.json"
    _write_json(status_path, _structural_status_fixture())
    source_sha = authority.sha256_file(status_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    sidecar = bridge.extract_structural_status(
        status,
        source_status_sha256=source_sha,
        expected_arm="F111",
    )
    sidecar_path = tmp_path / bridge.STATUS_SIDECAR_NAME
    _write_json(sidecar_path, sidecar)

    assert sidecar_path.name != status_path.name
    assert sidecar["source_status_sha256"] == source_sha
    assert sidecar["schema"] == bridge.STATUS_SIDECAR_SCHEMA
    assert sidecar != status
    assert not _contains_key(
        sidecar,
        {
            "episode_rows",
            "mean_ee_bits_per_j",
            "power_trace",
            "reward_trace",
            "outcome_metric",
            "telemetry",
        },
    )
    assert json.loads(sidecar_path.read_text(encoding="utf-8")) == sidecar
    bridge.validate_structural_status_sidecar(
        sidecar,
        expected_source_sha256=source_sha,
        expected_arm="F111",
    )
    with pytest.raises(bridge.R7500PrefixBridgeError, match="source SHA"):
        bridge.validate_structural_status_sidecar(
            sidecar,
            expected_source_sha256="d" * 64,
            expected_arm="F111",
        )
    status_with_nested_outcome = _structural_status_fixture()
    status_with_nested_outcome["trainer_config"]["mean_ee_bits_per_j"] = 1.0
    with pytest.raises(bridge.R7500PrefixBridgeError, match="fields drifted"):
        bridge.extract_structural_status(
            status_with_nested_outcome,
            source_status_sha256=source_sha,
            expected_arm="F111",
        )


def test_reconciliation_source_only_hashes_full_status_and_uses_sidecar_projection():
    source = Path(reconcile.__file__).read_text(encoding="utf-8")
    assert "validate_structural_status_sidecar" in source
    assert "authority.sha256_file(status_path)" in source
    assert "status = _read_object(status_path" not in source
    assert "_periodic_row(status)" not in source


def test_reconciliation_requires_one_exact_ep500_periodic_row():
    row = {
        "episodes_completed": 500,
        "episode_index": 499,
        "checkpoint_kind": "periodic-main-policy-trend",
    }
    assert reconcile._periodic_row({"result": {"periodic_checkpoints": [row]}}) == row
    with pytest.raises(reconcile.R7500ReconciliationError, match="one exact"):
        reconcile._periodic_row({"result": {"periodic_checkpoints": [row, row]}})


def test_evaluation_guard_rejects_zero_power_zero_total_service_and_bad_count():
    valid = {"zero_power_intervals": 0, "zero_service_intervals": 3, "useful_bits": 1.0}
    evaluator.validate_evaluation_rows([valid], expected_count=1)
    with pytest.raises(evaluator.R7500EvaluationError, match="zero-power"):
        evaluator.validate_evaluation_rows(
            [{**valid, "zero_power_intervals": 1}], expected_count=1
        )
    with pytest.raises(evaluator.R7500EvaluationError, match="all-zero-service"):
        evaluator.validate_evaluation_rows([{**valid, "useful_bits": 0.0}], expected_count=1)
    with pytest.raises(evaluator.R7500EvaluationError, match="incomplete"):
        evaluator.validate_evaluation_rows([valid], expected_count=2)


def _lineage_files(root: Path, *, suffix: str = "") -> tuple[dict, dict]:
    bridge_path = root / f"bridge{suffix}.json"
    reconciliation_path = root / f"reconciliation{suffix}.json"
    _write_json(bridge_path, {"schema": bridge.SCHEMA, "status": "PASS"})
    _write_json(reconciliation_path, {"schema": reconcile.SCHEMA, "status": "PASS"})
    return (
        {
            "path": str(bridge_path.resolve()),
            "sha256": authority.sha256_file(bridge_path),
            "reconciliation_required": True,
        },
        {
            "path": str(reconciliation_path.resolve()),
            "sha256": authority.sha256_file(reconciliation_path),
            "status": "PASS",
        },
    )


def _evaluation_gate(*, authority_sha: str = "a" * 64) -> dict:
    runtime = {
        "python": authority.RUNTIME_PYTHON_VERSION,
        "packages": authority.RUNTIME_PACKAGES,
    }
    return {
        "schema": preflight.SCHEMA,
        "status": "PASS",
        "created_utc": "2026-08-30T14:59:00+00:00",
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "authority_sha256": authority_sha,
        "resource_policy": authority.RESOURCE_POLICY,
        "host": {
            "hostname": authority.RESOURCE_POLICY["authorized_hostname"],
            "system": "Linux",
            "release": "fixture",
            "machine": "x86_64",
            "python": authority.RUNTIME_PYTHON_VERSION,
        },
        "runtime": runtime,
        "assessment": {
            "status": "PASS",
            "failures": [],
            "active_training_processes": [],
            "runtime": runtime,
        },
        "source_matrices": [
            {
                "learning_rate": learning_rate,
                "status": "complete",
                "verified_arm_count": len(authority.BRIDGED_ARMS),
            }
            for learning_rate in authority.ALLOWED_LEARNING_RATES
        ],
        "source_checkpoint_evaluation_authorized": True,
        "new_r7_training_authorized": False,
    }


def _evaluation_fixture(
    repo: Path,
    *,
    learning_rate: float,
    baseline_ee: float,
    full_ee: float,
    baseline_served: float = 0.90,
    full_served: float = 0.90,
    authority_sha: str = "a" * 64,
    lineage: tuple[dict, dict] | None = None,
) -> Path:
    bridge_row, reconciliation_row = lineage or _lineage_files(repo)
    checkpoint_root = Path(bridge_row["path"]).resolve().parent / "inputs" / "checkpoints"
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    checkpoint_paths = {
        "B000": checkpoint_root / "B000.pt",
        "F111": checkpoint_root / "F111.pt",
    }
    checkpoint_paths["B000"].write_bytes(b"synthetic-b000-checkpoint\n")
    checkpoint_paths["F111"].write_bytes(b"synthetic-f111-checkpoint\n")
    checkpoint_shas = {
        arm: authority.sha256_file(path) for arm, path in checkpoint_paths.items()
    }
    bindings = [
        {
            "arm": "B000",
            "label": evaluator.ARM_LABELS["B000"],
            "path": str(checkpoint_paths["B000"].resolve()),
            "sha256": checkpoint_shas["B000"],
            "source_status": "reconciled_ep500_periodic",
            "online_policy_sha256": "d" * 64,
        },
        {
            "arm": "F111",
            "label": evaluator.ARM_LABELS["F111"],
            "path": str(checkpoint_paths["F111"].resolve()),
            "sha256": checkpoint_shas["F111"],
            "source_status": "reconciled_ep500_periodic",
            "online_policy_sha256": "e" * 64,
        },
    ]
    raw_rows = []
    for label, checkpoint_sha, ee, served in (
        (
            evaluator.ARM_LABELS["B000"],
            checkpoint_shas["B000"],
            baseline_ee,
            baseline_served,
        ),
        (
            evaluator.ARM_LABELS["F111"],
            checkpoint_shas["F111"],
            full_ee,
            full_served,
        ),
    ):
        for users in authority.EVALUATION_USERS:
            for evaluation_seed in authority.EVALUATION_SEEDS:
                total_user_intervals = 100_000
                served_user_intervals = round(served * total_user_intervals)
                raw_rows.append(
                    {
                        "arm": label,
                        "checkpoint_sha256": checkpoint_sha,
                        "training_seed": authority.TRAINING_SEEDS["training"],
                        "evaluation_seed": evaluation_seed,
                        "users": users,
                        "steps": 10,
                        "duration_s": 10.0,
                        "useful_bits": ee * 100.0,
                        "system_energy_j": 100.0,
                        "system_ee_bits_per_j": ee,
                        "mean_system_power_w": 10.0,
                        "mean_system_throughput_bps": ee * 10.0,
                        "served_user_intervals": served_user_intervals,
                        "total_user_intervals": total_user_intervals,
                        "served_fraction": served_user_intervals / total_user_intervals,
                        "zero_power_intervals": 0,
                        "zero_service_intervals": 0,
                        "r1_sum": 0.0,
                        "r2_sum": 0.0,
                        "r3_sum": 0.0,
                    }
                )
    rows = evaluator.sweep.aggregate_rows(
        [evaluator.sweep.EpisodeTotals(**row) for row in raw_rows]
    )
    assert len(raw_rows) == 50
    assert len(rows) == 10
    suffix = "lr0p001-prefix" if learning_rate == 0.001 else "lr0p01-prefix"
    output = repo / "artifacts" / "r7" / "evaluation" / suffix
    raw_path = output / "sweep-raw.json"
    summary_path = output / "sweep-summary.json"
    plot_path = output / "ee-vs-users-r7-500.svg"
    created_utc = "2026-08-30T15:00:00+00:00"
    ephemeris = {"fixture": "synthetic-control-plane-only"}
    common = {
        "status": "complete",
        "created_utc": created_utc,
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "endpoint_episodes": 500,
        "authority_sha256": authority_sha,
        "learning_rate": learning_rate,
        "bridge_receipt": bridge_row,
        "reconciliation_receipt": reconciliation_row,
        "evaluation_policy": "MAIN_ONLY_MASKED_GREEDY",
        "evaluation_partition": "TEST",
        "ee_aggregation": "RATIO_OF_POOLED_USEFUL_BITS_TO_POOLED_SYSTEM_ENERGY",
        "users": authority.EVALUATION_USERS,
        "evaluation_seeds": authority.EVALUATION_SEEDS,
        "ephemeris_authority": ephemeris,
        "evaluation_gate": _evaluation_gate(authority_sha=authority_sha),
        "checkpoints": bindings,
    }
    raw = {
        "schema": evaluator.RAW_SCHEMA,
        **common,
        "rows": raw_rows,
    }
    summary = {
        "schema": evaluator.SCHEMA,
        **common,
        "guards": {
            "zero_power_intervals": 0,
            "all_evaluation_episodes_have_positive_useful_bits": True,
        },
        "summary": rows,
    }
    _write_json(raw_path, raw)
    _write_json(summary_path, summary)
    plot_path.write_text("<svg><!-- synthetic control-plane fixture --></svg>\n", encoding="utf-8")
    receipt = {
        "schema": evaluator.RECEIPT_SCHEMA,
        "status": "PASS",
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "learning_rate": learning_rate,
        "authority_sha256": authority_sha,
        "bridge_receipt": bridge_row,
        "reconciliation_receipt": reconciliation_row,
        "checkpoint_bindings": bindings,
        "artifacts": {
            "raw": {
                "path": str(raw_path.resolve()),
                "sha256": authority.sha256_file(raw_path),
            },
            "summary": {
                "path": str(summary_path.resolve()),
                "sha256": authority.sha256_file(summary_path),
            },
            "plot": {
                "path": str(plot_path.resolve()),
                "sha256": authority.sha256_file(plot_path),
            },
        },
    }
    receipt_path = output / "evaluation-receipt.json"
    _write_json(receipt_path, receipt)
    return receipt_path


def _patch_master(monkeypatch, *, authority_sha: str = "a" * 64):
    monkeypatch.setattr(
        bridge,
        "load_and_validate_authority",
        lambda *args, **kwargs: (
            {"pin_map_sha256": "d" * 64, "ablation_output_root": "artifacts/r7"},
            authority_sha,
        ),
    )


def _routing_assessment(learning_rate: float, d_full: float, *, eligible: bool) -> dict:
    return {
        "learning_rate": learning_rate,
        "d_full_percent": d_full,
        "eligible": eligible,
    }


@pytest.mark.parametrize(
    ("first", "second", "expected_lr", "expected_decision", "expected_tie"),
    [
        ((10.0, True), (30.0, False), 0.001, "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS", None),
        ((10.0, False), (30.0, True), 0.01, "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS", None),
        ((100.0, True), (100.0, True), 0.001, "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS", 0.0),
        ((96.0, True), (100.0, True), 0.001, "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS", 4.0),
        ((95.0, True), (100.0, True), 0.01, "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS", 5.0),
        ((100.0, True), (95.0, True), 0.001, "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS", 5.0),
        ((-2.0, False), (-1.0, False), 0.01, "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY", None),
        ((-1.0, False), (-1.0, False), 0.001, "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY", None),
    ],
)
def test_lr_decision_core_covers_every_eligibility_and_tie_branch(
    first, second, expected_lr, expected_decision, expected_tie
):
    decision = router._decision_core(
        {
            "0.001": _routing_assessment(0.001, first[0], eligible=first[1]),
            "0.01": _routing_assessment(0.01, second[0], eligible=second[1]),
        }
    )
    assert decision["selected_learning_rate"] == expected_lr
    assert decision["decision"] == expected_decision
    if expected_tie is None:
        assert decision["tie_relative_percent"] is None
    else:
        assert decision["tie_relative_percent"] == pytest.approx(expected_tie)
    assert decision["first_ablation"] == "A101"
    assert decision["allowed_ablation_arms"] == (
        ["A101"]
        if expected_decision == "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY"
        else list(authority.ABLATION_ARMS)
    )
    assert decision["fresh_training_required"] is False
    assert decision["source_checkpoint_reuse_only"] is True
    assert decision["new_r7_training_authorized"] is False


def test_router_service_loss_boundary_is_inclusive_at_two_percentage_points(tmp_path):
    receipt = _evaluation_fixture(
        tmp_path / "at-boundary",
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=101.0,
        baseline_served=0.90,
        full_served=0.88,
    )
    assessment, _ = router._assessment(
        receipt, expected_learning_rate=0.001, authority_sha256="a" * 64
    )
    assert assessment["service_loss_percentage_points"] == pytest.approx(2.0)
    assert assessment["eligible"] is True

    receipt = _evaluation_fixture(
        tmp_path / "over-boundary",
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=101.0,
        baseline_served=0.90,
        full_served=0.87999,
    )
    assessment, _ = router._assessment(
        receipt, expected_learning_rate=0.001, authority_sha256="a" * 64
    )
    assert assessment["service_loss_percentage_points"] > 2.0
    assert assessment["eligible"] is False


def test_router_recomputes_summary_from_raw_and_carries_raw_lineage(tmp_path):
    receipt_path = _evaluation_fixture(
        tmp_path,
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
    )
    assessment, input_receipt = router._assessment(
        receipt_path, expected_learning_rate=0.001, authority_sha256="a" * 64
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw = receipt["artifacts"]["raw"]
    assert assessment["d_full_percent"] == pytest.approx(10.0)
    assert input_receipt["raw_path"] == raw["path"]
    assert input_receipt["raw_sha256"] == raw["sha256"]


def test_router_rejects_checkpoint_snapshot_drift(tmp_path):
    receipt_path = _evaluation_fixture(
        tmp_path,
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checkpoint = Path(receipt["checkpoint_bindings"][0]["path"])
    checkpoint.write_bytes(b"drifted-after-evaluation\n")
    with pytest.raises(router.R7500LRRoutingError, match="checkpoint binding"):
        router._assessment(
            receipt_path,
            expected_learning_rate=0.001,
            authority_sha256="a" * 64,
        )


def test_router_requires_exact_b000_f111_pair_and_ubuntu_gate_metadata(tmp_path):
    receipt_path = _evaluation_fixture(
        tmp_path,
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw_path = Path(receipt["artifacts"]["raw"]["path"])
    summary_path = Path(receipt["artifacts"]["summary"]["path"])
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert [row["arm"] for row in receipt["checkpoint_bindings"]] == [
        "B000",
        "F111",
    ]
    assert set(evaluator.ROUTING_LABELS) == {"B000", "F111"}
    assert raw["evaluation_gate"] == summary["evaluation_gate"]
    gate = raw["evaluation_gate"]
    assert gate["schema"] == preflight.SCHEMA
    assert gate["status"] == "PASS"
    assert gate["host"]["hostname"] == authority.RESOURCE_POLICY["authorized_hostname"]
    assert gate["runtime"] == {
        "python": authority.RUNTIME_PYTHON_VERSION,
        "packages": authority.RUNTIME_PACKAGES,
    }
    assert len(gate["source_matrices"]) == 2
    assert gate["source_checkpoint_evaluation_authorized"] is True
    assert gate["new_r7_training_authorized"] is False

    receipt["checkpoint_bindings"].append(
        {
            "arm": "A101",
            "label": evaluator.ARM_LABELS["A101"],
            "path": str((tmp_path / "A101.pt").resolve()),
            "sha256": "9" * 64,
        }
    )
    _write_json(receipt_path, receipt)
    with pytest.raises(router.R7500LRRoutingError, match="lineage|pair"):
        router._assessment(
            receipt_path,
            expected_learning_rate=0.001,
            authority_sha256="a" * 64,
        )


@pytest.mark.parametrize("artifact_name", ["raw", "summary"])
def test_router_rejects_missing_or_drifted_ubuntu_gate_metadata(tmp_path, artifact_name):
    receipt_path = _evaluation_fixture(
        tmp_path,
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    artifact = receipt["artifacts"][artifact_name]
    artifact_path = Path(artifact["path"])
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact_name == "raw":
        payload["evaluation_gate"]["host"]["hostname"] = "not-5090"
    else:
        payload.pop("evaluation_gate")
    _write_json(artifact_path, payload)
    artifact["sha256"] = authority.sha256_file(artifact_path)
    _write_json(receipt_path, receipt)
    with pytest.raises(router.R7500LRRoutingError, match="gate|evaluation_gate"):
        router._assessment(
            receipt_path,
            expected_learning_rate=0.001,
            authority_sha256="a" * 64,
        )


@pytest.mark.parametrize("tampered_artifact", ["raw", "summary"])
def test_router_rejects_hash_consistent_raw_summary_disagreement(
    tmp_path, tampered_artifact
):
    receipt_path = _evaluation_fixture(
        tmp_path,
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    artifact = receipt["artifacts"][tampered_artifact]
    artifact_path = Path(artifact["path"])
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if tampered_artifact == "raw":
        payload["rows"][0]["useful_bits"] *= 2.0
    else:
        endpoint = next(
            row
            for row in payload["summary"]
            if row["arm"] == evaluator.ARM_LABELS["F111"] and row["users"] == 100
        )
        endpoint["mean_ee_bits_per_j"] += 7.0
    _write_json(artifact_path, payload)
    artifact["sha256"] = authority.sha256_file(artifact_path)
    _write_json(receipt_path, receipt)
    with pytest.raises(router.R7500LRRoutingError, match="raw|summary|reproduc"):
        router._assessment(
            receipt_path,
            expected_learning_rate=0.001,
            authority_sha256="a" * 64,
        )


def _serialized_ablation_rows_fixture() -> tuple[list[dict], list[dict]]:
    labels = [ablation_evaluator.LABELS[arm] for arm in authority.ALL_R7_ARMS]
    bindings = [
        {"label": label, "sha256": f"{index + 1:064x}"}
        for index, label in enumerate(labels)
    ]
    rows = []
    for arm_index, label in enumerate(labels):
        for users in authority.EVALUATION_USERS:
            for evaluation_seed in authority.EVALUATION_SEEDS:
                useful_bits = 1000.0 + arm_index + float(users)
                energy = 100.0
                duration = 10.0
                rows.append(
                    {
                        "arm": label,
                        "checkpoint_sha256": bindings[arm_index]["sha256"],
                        "training_seed": authority.TRAINING_SEEDS["training"],
                        "evaluation_seed": evaluation_seed,
                        "users": users,
                        "steps": 1,
                        "duration_s": duration,
                        "useful_bits": useful_bits,
                        "system_energy_j": energy,
                        "system_ee_bits_per_j": useful_bits / energy,
                        "mean_system_power_w": energy / duration,
                        "mean_system_throughput_bps": useful_bits / duration,
                        "served_user_intervals": users,
                        "total_user_intervals": users,
                        "served_fraction": 1.0,
                        "zero_power_intervals": 0,
                        "zero_service_intervals": 0,
                        "r1_sum": 0.0,
                        "r2_sum": 0.0,
                        "r3_sum": 0.0,
                    }
                )
    return rows, bindings


def test_generic_serialized_ablation_recomputation_rejects_raw_summary_tampering_and_gaps(
    tmp_path,
):
    rows, bindings = _serialized_ablation_rows_fixture()
    labels = [ablation_evaluator.LABELS[arm] for arm in authority.ALL_R7_ARMS]
    recomputed = evaluator.recompute_serialized_evaluation_rows(
        rows,
        ordered_labels=labels,
        checkpoint_bindings=bindings,
    )
    assert len(recomputed) == len(labels) * len(authority.EVALUATION_USERS)

    tampered_raw = [dict(row) for row in rows]
    tampered_raw[0]["useful_bits"] *= 2.0
    with pytest.raises(evaluator.R7500EvaluationError, match="physical invariants"):
        evaluator.recompute_serialized_evaluation_rows(
            tampered_raw,
            ordered_labels=labels,
            checkpoint_bindings=bindings,
        )

    with pytest.raises(evaluator.R7500EvaluationError, match="incomplete"):
        evaluator.recompute_serialized_evaluation_rows(
            rows[:-1],
            ordered_labels=labels,
            checkpoint_bindings=bindings,
        )

    tampered_summary = [dict(row) for row in recomputed]
    tampered_summary[0]["mean_ee_bits_per_j"] += 1.0
    # The ablation writer's exact serialized-summary comparison is the second
    # half of the guard: a summary that no longer equals the independent raw
    # reconstruction must not be publishable.
    assert tampered_summary != recomputed
    summary_path = tmp_path / "tampered-summary.json"
    _write_json(summary_path, {"summary": tampered_summary})
    assert json.loads(summary_path.read_text(encoding="utf-8"))["summary"] != recomputed
    assert "serialized_summary.get(\"summary\") != recomputed_summary" in Path(
        ablation_evaluator.__file__
    ).read_text(encoding="utf-8")


def test_router_tie_rule_service_boundary_and_neither_branch(tmp_path, monkeypatch):
    _patch_master(monkeypatch)
    lineage = _lineage_files(tmp_path)
    first = _evaluation_fixture(
        tmp_path,
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
        baseline_served=0.90,
        full_served=0.88,
        lineage=lineage,
    )
    second = _evaluation_fixture(
        tmp_path,
        learning_rate=0.01,
        baseline_ee=100.0,
        full_ee=110.3,
        lineage=lineage,
    )
    result = router.select_learning_rate(
        authority_path=tmp_path / "authority.json",
        lr0p001_evaluation_receipt=first,
        lr0p01_evaluation_receipt=second,
        output=tmp_path / "artifacts" / "r7" / "lr-selection.json",
        tle_root=tmp_path,
        repo=tmp_path,
    )
    assert result["decision"]["selected_learning_rate"] == 0.001
    assert result["assessments"]["0.001"]["eligible"] is True
    assert result["input_evaluations"]["0.001"]["raw_path"].endswith(
        "sweep-raw.json"
    )

    other = tmp_path / "other"
    lineage = _lineage_files(other)
    first = _evaluation_fixture(
        other, learning_rate=0.001, baseline_ee=100.0, full_ee=99.0, lineage=lineage
    )
    second = _evaluation_fixture(
        other, learning_rate=0.01, baseline_ee=100.0, full_ee=98.0, lineage=lineage
    )
    result = router.select_learning_rate(
        authority_path=other / "authority.json",
        lr0p001_evaluation_receipt=first,
        lr0p01_evaluation_receipt=second,
        output=other / "artifacts" / "r7" / "lr-selection.json",
        tle_root=other,
        repo=other,
    )
    assert result["decision"]["decision"] == (
        "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY"
    )
    assert result["decision"]["allowed_ablation_arms"] == ["A101"]


def test_router_rejects_mixed_bridge_lineage(tmp_path, monkeypatch):
    _patch_master(monkeypatch)
    first = _evaluation_fixture(
        tmp_path,
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
        lineage=_lineage_files(tmp_path, suffix="-one"),
    )
    second = _evaluation_fixture(
        tmp_path,
        learning_rate=0.01,
        baseline_ee=100.0,
        full_ee=111.0,
        lineage=_lineage_files(tmp_path, suffix="-two"),
    )
    with pytest.raises(router.R7500LRRoutingError, match="do not share"):
        router.select_learning_rate(
            authority_path=tmp_path / "authority.json",
            lr0p001_evaluation_receipt=first,
            lr0p01_evaluation_receipt=second,
            output=tmp_path / "artifacts" / "r7" / "lr-selection.json",
            tle_root=tmp_path,
            repo=tmp_path,
        )


def _prefix_lineage_fixture(repo: Path, monkeypatch) -> tuple[dict, Path, Path, Path]:
    authority_path = repo / "authority.json"
    authority_path.parent.mkdir(parents=True, exist_ok=True)
    authority_path.write_text("{\"fixture\": true}\n", encoding="utf-8")
    authority_sha = authority.sha256_file(authority_path)
    bridge_root = repo / "bridge"
    bridge_root.mkdir(parents=True)
    authority_snapshot = bridge_root / "inputs" / "r7-authority.json"
    authority_snapshot.parent.mkdir(parents=True)
    authority_snapshot.write_bytes(authority_path.read_bytes())
    validated = {
        "bridge_output": "bridge",
        "reconciliation_receipt": "bridge/prefix-reconciliation.json",
        "pin_map_sha256": "d" * 64,
        "validated_base_authorities": {
            lr_key: {"learning_rate": float(lr_key)}
            for lr_key in ("0.001", "0.01")
        },
    }
    rows = []
    reconciled_rows = []
    for index, (lr_key, arm) in enumerate(
        (lr_key, arm)
        for lr_key in ("0.001", "0.01")
        for arm in authority.BRIDGED_ARMS
    ):
        prefix_root = bridge_root / "inputs" / f"lr-{lr_key}" / arm
        checkpoint = prefix_root / bridge.CHECKPOINT_NAME
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_bytes(f"fixture-{lr_key}-{arm}".encode("utf-8"))
        journal = prefix_root / "run-journal.json"
        _write_json(journal, {"trainer_config": {"learning_rate": float(lr_key)}})
        artifact_sha = authority.sha256_file(checkpoint)
        policy_sha = f"{index + 1:064x}"
        rows.append(
            {
                "learning_rate": float(lr_key),
                "arm": arm,
                "source_status": "completed_source_ep500_pending_reconciliation",
                "run": {
                    "journal_snapshot": str(journal.relative_to(bridge_root)),
                },
                "checkpoint": {
                    "snapshot": str(checkpoint.relative_to(bridge_root)),
                    "artifact_sha256": artifact_sha,
                    "online_policy_sha256": policy_sha,
                },
            }
        )
        reconciled_rows.append(
            {
                "learning_rate": float(lr_key),
                "arm": arm,
                "artifact_sha256": artifact_sha,
                "online_policy_sha256": policy_sha,
            }
        )
    bridge_receipt_path = bridge_root / "prefix-bridge-receipt.json"
    bridge_receipt = {
        "schema": bridge.SCHEMA,
        "status": "PASS",
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "endpoint_episodes": 500,
        "prefix_arms": list(authority.PREFIX_ARMS),
        "bridged_arms": list(authority.BRIDGED_ARMS),
        "learning_rates": list(authority.ALLOWED_LEARNING_RATES),
        "outcome_bearing_source_status_parsed_by_whitelist_extractor": True,
        "outcome_metric_fields_copied": False,
        "outcome_metric_fields_emitted": False,
        "outcome_metric_fields_used_for_admission": False,
        "outcome_metric_fields_admitted": False,
        "checkpoint_selection_performed": False,
        "evaluation_authorized": False,
        "routing_authorized": False,
        "reconciliation_required": True,
        "authority": {
            "snapshot": str(authority_snapshot.relative_to(bridge_root)),
            "sha256": authority_sha,
            "pin_map_sha256": validated["pin_map_sha256"],
        },
        "prefixes": rows,
    }
    _write_json(bridge_receipt_path, bridge_receipt)
    reconciliation_path = bridge_root / "prefix-reconciliation.json"
    reconciliation_receipt = {
        "schema": reconcile.SCHEMA,
        "status": "PASS",
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "authority_sha256": authority_sha,
        "bridge_receipt": {
            "path": str(bridge_receipt_path.resolve()),
            "sha256": authority.sha256_file(bridge_receipt_path),
        },
        "evaluation_authorized": True,
        "routing_authorized": True,
        "routing_arms": list(authority.PREFIX_ARMS),
        "bridged_arms": list(authority.BRIDGED_ARMS),
        "outcome_bearing_source_status_parsed_by_whitelist_extractor": True,
        "outcome_metric_fields_copied": False,
        "outcome_metric_fields_emitted": False,
        "outcome_metric_fields_used_for_admission": False,
        "outcome_metric_fields_admitted": False,
        "selected_lr_ablation_reveal_authorized": False,
        "selected_lr_ablation_reveal_eligible_after_valid_selection": True,
        "new_r7_training_authorized": False,
        "prefixes": reconciled_rows,
    }
    _write_json(reconciliation_path, reconciliation_receipt)
    monkeypatch.setattr(
        bridge,
        "load_and_validate_authority",
        lambda *args, **kwargs: (validated, authority_sha),
    )
    monkeypatch.setattr(
        evaluator,
        "read_checkpoint",
        lambda path, **kwargs: SimpleNamespace(
            online_policy_sha256=next(
                row["checkpoint"]["online_policy_sha256"]
                for row in rows
                if Path(row["checkpoint"]["snapshot"]).name == Path(path).name
                and str(path).endswith(row["checkpoint"]["snapshot"])
            )
        ),
    )
    monkeypatch.setattr(
        checkpoint_tools,
        "validate_checkpoint_payload",
        lambda payload, **kwargs: {
            "online_policy_sha256": payload.online_policy_sha256,
        },
    )
    return validated, authority_path, bridge_receipt_path, reconciliation_path


def test_reconciled_source_grid_is_exactly_ten_and_routing_exposes_only_b_f(
    tmp_path, monkeypatch
):
    _, authority_path, bridge_path, reconciliation_path = _prefix_lineage_fixture(
        tmp_path, monkeypatch
    )
    loaded = evaluator._load_inputs(
        authority_path=authority_path,
        bridge_receipt_path=bridge_path,
        reconciliation_receipt_path=reconciliation_path,
        learning_rate=0.001,
        tle_root=tmp_path / "tle",
        repo=tmp_path,
    )[-1]
    assert [row["arm"] for row in loaded] == ["B000", "F111"]
    bridge_receipt = json.loads(bridge_path.read_text(encoding="utf-8"))
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    assert len(bridge_receipt["prefixes"]) == 10
    assert len(reconciliation["prefixes"]) == 10
    expected_grid = [
        (float(lr_key), arm)
        for lr_key in ("0.001", "0.01")
        for arm in authority.BRIDGED_ARMS
    ]
    assert [
        (row["learning_rate"], row["arm"]) for row in reconciliation["prefixes"]
    ] == expected_grid


def test_routing_fails_closed_if_reconciliation_lacks_an_unselected_a_arm(
    tmp_path, monkeypatch
):
    _, authority_path, bridge_path, reconciliation_path = _prefix_lineage_fixture(
        tmp_path, monkeypatch
    )
    bridge_receipt = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge_receipt["prefixes"] = [
        row
        for row in bridge_receipt["prefixes"]
        if not (row["learning_rate"] == 0.01 and row["arm"] == "A110")
    ]
    _write_json(bridge_path, bridge_receipt)
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    reconciliation["prefixes"] = [
        row
        for row in reconciliation["prefixes"]
        if not (row["learning_rate"] == 0.01 and row["arm"] == "A110")
    ]
    reconciliation["bridge_receipt"]["sha256"] = authority.sha256_file(bridge_path)
    _write_json(reconciliation_path, reconciliation)
    with pytest.raises(evaluator.R7500EvaluationError, match="ten|grid|prefix"):
        evaluator._load_inputs(
            authority_path=authority_path,
            bridge_receipt_path=bridge_path,
            reconciliation_receipt_path=reconciliation_path,
            learning_rate=0.001,
            tle_root=tmp_path / "tle",
            repo=tmp_path,
        )


def test_incomplete_marker_blocks_reconciliation_evaluation_and_routing(
    tmp_path, monkeypatch
):
    _, authority_path, bridge_path, reconciliation_path = _prefix_lineage_fixture(
        tmp_path / "lineage", monkeypatch
    )
    marker = bridge_path.parent / output_tools.INCOMPLETE_MARKER
    _write_json(marker, {"status": "INCOMPLETE"})
    with pytest.raises(reconcile.R7500ReconciliationError, match="incomplete"):
        reconcile.reconcile_prefixes(
            authority_path=authority_path,
            bridge_receipt_path=bridge_path,
            tle_root=tmp_path / "tle",
            repo=tmp_path / "lineage",
        )
    with pytest.raises(evaluator.R7500EvaluationError, match="incomplete"):
        evaluator._load_inputs(
            authority_path=authority_path,
            bridge_receipt_path=bridge_path,
            reconciliation_receipt_path=reconciliation_path,
            learning_rate=0.001,
            tle_root=tmp_path / "tle",
            repo=tmp_path / "lineage",
        )

    evaluation_receipt = _evaluation_fixture(
        tmp_path / "evaluation",
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
    )
    _write_json(
        evaluation_receipt.parent / output_tools.INCOMPLETE_MARKER,
        {"status": "INCOMPLETE"},
    )
    with pytest.raises(router.R7500LRRoutingError, match="incomplete"):
        router._assessment(
            evaluation_receipt,
            expected_learning_rate=0.001,
            authority_sha256="a" * 64,
        )


def test_evaluation_resource_assessment_blocks_wsl_low_resources_and_active_source(
    tmp_path,
):
    roots = [tmp_path / "matrix"]
    passed = preflight.assess_resource_state(
        resource_policy=authority.RESOURCE_POLICY,
        source_matrix_roots=roots,
        logical_cpus=20,
        available_memory_bytes=16 * 1024**3,
        kernel_text="Linux Ubuntu",
        process_cmdlines=[],
    )
    assert passed["status"] == "PASS"
    failed = preflight.assess_resource_state(
        resource_policy=authority.RESOURCE_POLICY,
        source_matrix_roots=roots,
        logical_cpus=8,
        available_memory_bytes=1024,
        kernel_text="Linux microsoft WSL2",
        process_cmdlines=[
            (42, f"/opt/venv/bin/python arm.py --output-dir {roots[0]}/arms/A101")
        ],
    )
    assert failed["status"] == "FAIL"
    assert len(failed["failures"]) == 4
    assert failed["active_training_processes"][0]["pid"] == 42


@pytest.mark.parametrize(
    "process_record",
    [
        {
            "pid": 101,
            "argv": [
                "/usr/bin/python3",
                "/srv/mcrl/.scratch/c2-v03a-trend/c2_v03a_trend_matrix.py",
                "--output-root",
                "/srv/mcrl/source-matrix",
            ],
            "cwd": "/srv/mcrl",
        },
        {
            "pid": 102,
            "argv": [
                "python3",
                "wrapper.py",
                "--output-dir",
                "matrix/arms/A101",
            ],
            "cwd": "/tmp/r7-preflight",
        },
        {
            "pid": 103,
            "argv": [
                "env",
                "PYTHONUNBUFFERED=1",
                "python3",
                "/srv/mcrl/.scratch/c2-v03a-trend/r7_500_evaluate.py",
                "--output-dir",
                "/srv/mcrl/r7/evaluation",
            ],
            "cwd": "/srv/mcrl",
        },
    ],
)
def test_preflight_detects_absolute_relative_and_env_wrapped_r7_processes(
    tmp_path, process_record
):
    source_root = tmp_path / "matrix"
    source_root.mkdir()
    record = dict(process_record)
    if record["pid"] == 102:
        record["cwd"] = str(tmp_path)
        record["argv"][-1] = "matrix/arms/A101"
    else:
        # The absolute-path cases must still be recognised even when they do not
        # point at this fixture root; the process identity itself is sufficient.
        record["cwd"] = str(tmp_path)
    assessment = preflight.assess_resource_state(
        resource_policy=authority.RESOURCE_POLICY,
        source_matrix_roots=[source_root],
        logical_cpus=20,
        available_memory_bytes=16 * 1024**3,
        kernel_text="Linux Ubuntu",
        process_cmdlines=[record],
    )
    assert assessment["status"] == "FAIL"
    assert assessment["active_training_processes"]
    active = assessment["active_training_processes"][0]
    assert active["pid"] == record["pid"]
    assert active["argv"] == record["argv"]
    assert active["cwd"] == str(Path(record["cwd"]).resolve())


def _source_matrix_fixture(repo: Path) -> tuple[dict, list[str]]:
    arms = list(authority.BRIDGED_ARMS)
    source_matrix_paths = {
        "0.001": "source/lr0p001",
        "0.01": "source/lr0p01",
    }
    bases = {
        key: {
            "arms": arms,
            "authority_sha256": ("1" if key == "0.001" else "2") * 64,
        }
        for key in source_matrix_paths
    }
    for key, relative in source_matrix_paths.items():
        _write_json(
            repo / relative / "matrix-status.json",
            {
                "schema": bridge.MATRIX_SCHEMA,
                "status": "complete",
                "episodes": 1500,
                "learning_rate": float(key),
                "authority_sha256": bases[key]["authority_sha256"],
                "runs": {
                    arm: {"status": "process_complete", "exit_code": 0}
                    for arm in arms
                },
                "verifications": {
                    arm: {"status": "PASS", "episodes_completed": 1500}
                    for arm in arms
                },
            },
        )
    return {
        "source_matrix_paths": source_matrix_paths,
        "validated_base_authorities": bases,
    }, arms


def test_source_completion_gate_requires_all_five_arms_in_both_matrices(tmp_path):
    validated, arms = _source_matrix_fixture(tmp_path)
    receipts = preflight.assert_source_matrices_complete(
        validated=validated, repo=tmp_path
    )
    assert [row["verified_arm_count"] for row in receipts] == [5, 5]
    assert arms == ["B000", "F111", "A101", "A011", "A110"]


def test_source_completion_gate_rejects_active_nonprefix_arm(tmp_path):
    validated, _ = _source_matrix_fixture(tmp_path)
    matrix_path = tmp_path / validated["source_matrix_paths"]["0.001"] / "matrix-status.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["runs"]["A101"] = {"status": "running", "exit_code": None}
    _write_json(matrix_path, matrix)
    with pytest.raises(preflight.R7500ServerPreflightError, match="A101"):
        preflight.assert_source_matrices_complete(validated=validated, repo=tmp_path)


@pytest.mark.parametrize(
    "allowed",
    [list(authority.ABLATION_ARMS), ["A101"]],
)
def test_ablation_evaluation_validates_selection_before_exposing_only_allowed_arms(
    tmp_path, monkeypatch, allowed
):
    validated = {
        "ablation_output_root": "artifacts/r7",
        "validated_base_authorities": {"0.001": {}},
    }
    monkeypatch.setattr(
        bridge,
        "load_and_validate_authority",
        lambda *args, **kwargs: (validated, "a" * 64),
    )
    events = []
    selection = {
        "decision": {
            "decision": (
                "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY"
                if allowed == ["A101"]
                else "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS"
            ),
            "selected_learning_rate": 0.001,
            "allowed_ablation_arms": allowed,
            "fresh_training_required": False,
            "source_checkpoint_reuse_only": True,
            "new_r7_training_authorized": False,
        }
    }

    def validate_selection(*args, **kwargs):
        events.append("selection-validated")
        return selection

    class InputsObserved(RuntimeError):
        pass

    def load_inputs(**kwargs):
        assert events == ["selection-validated"]
        assert kwargs["learning_rate"] == 0.001
        assert kwargs["selected_arms"] == [*authority.PREFIX_ARMS, *allowed]
        assert all(arm in authority.ABLATION_ARMS for arm in allowed)
        events.append("allowed-source-prefixes-exposed")
        raise InputsObserved

    monkeypatch.setattr(router, "validate_selection_receipt", validate_selection)
    monkeypatch.setattr(evaluator, "_load_inputs", load_inputs)
    with pytest.raises(InputsObserved):
        ablation_evaluator.evaluate_ablations(
            authority_path=tmp_path / "authority.json",
            bridge_receipt_path=tmp_path / "bridge.json",
            reconciliation_receipt_path=tmp_path / "reconciliation.json",
            selection_receipt_path=tmp_path / "selection.json",
            output_dir=tmp_path / "artifacts" / "r7" / "evaluation" / "selected-lr-ablation",
            tle_root=tmp_path / "tle",
            repo=tmp_path,
        )
    assert events == ["selection-validated", "allowed-source-prefixes-exposed"]


def test_ablation_evaluation_exposes_no_checkpoint_when_selection_is_invalid(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        bridge,
        "load_and_validate_authority",
        lambda *args, **kwargs: ({"ablation_output_root": "artifacts/r7"}, "a" * 64),
    )

    def reject_selection(*args, **kwargs):
        raise router.R7500LRRoutingError("invalid selection receipt")

    monkeypatch.setattr(router, "validate_selection_receipt", reject_selection)
    monkeypatch.setattr(
        evaluator,
        "_load_inputs",
        lambda **kwargs: pytest.fail("checkpoint inputs were exposed before selection"),
    )
    with pytest.raises(router.R7500LRRoutingError, match="invalid selection"):
        ablation_evaluator.evaluate_ablations(
            authority_path=tmp_path / "authority.json",
            bridge_receipt_path=tmp_path / "bridge.json",
            reconciliation_receipt_path=tmp_path / "reconciliation.json",
            selection_receipt_path=tmp_path / "selection.json",
            output_dir=tmp_path / "artifacts" / "r7" / "evaluation" / "selected-lr-ablation",
            tle_root=tmp_path / "tle",
            repo=tmp_path,
        )


def test_ablation_revalidates_selection_immediately_before_publish_and_blocks_drift(
    tmp_path, monkeypatch
):
    (
        authority_path,
        bridge_path,
        reconciliation_path,
        selection_path,
        validated,
        checkpoints,
    ) = _failure_evaluation_fixture(tmp_path, ablation=True)
    authority_sha = authority.sha256_file(authority_path)
    decision = {
        "decision": "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS",
        "selected_learning_rate": 0.001,
        "allowed_ablation_arms": list(authority.ABLATION_ARMS),
        "fresh_training_required": False,
        "resume_allowed": False,
        "source_checkpoint_reuse_only": True,
        "new_r7_training_authorized": False,
    }
    selection = {"decision": decision}
    drifted_selection = {
        "decision": {**decision, "selected_learning_rate": 0.01}
    }
    validations = []

    def validate_selection(*args, **kwargs):
        validations.append("selection-validated")
        return selection if len(validations) == 1 else drifted_selection

    monkeypatch.setattr(
        ablation_evaluator.bridge,
        "load_and_validate_authority",
        lambda *args, **kwargs: (validated, authority_sha),
    )
    monkeypatch.setattr(
        ablation_evaluator.router,
        "validate_selection_receipt",
        validate_selection,
    )
    monkeypatch.setattr(
        ablation_evaluator.prefix_evaluator,
        "_load_inputs",
        lambda **kwargs: (
            validated,
            authority_sha,
            {"fixture": "bridge"},
            {"fixture": "reconciliation"},
            checkpoints,
        ),
    )
    monkeypatch.setattr(
        ablation_evaluator.preflight,
        "assert_evaluation_ready",
        lambda **kwargs: {"status": "PASS"},
    )
    monkeypatch.setattr(
        ablation_evaluator.sweep,
        "canonical_ephemeris_authority",
        lambda *args, **kwargs: (object(), {"fixture": "ephemeris"}),
    )

    def fake_evaluate_checkpoint_point(
        *, arm, checkpoint_sha256, users, evaluation_seed, **kwargs
    ):
        useful_bits = 1000.0 + float(users)
        energy = 100.0
        duration = 10.0
        return ablation_evaluator.sweep.EpisodeTotals(
            arm=arm,
            checkpoint_sha256=checkpoint_sha256,
            training_seed=authority.TRAINING_SEEDS["training"],
            evaluation_seed=evaluation_seed,
            users=users,
            steps=1,
            duration_s=duration,
            useful_bits=useful_bits,
            system_energy_j=energy,
            system_ee_bits_per_j=useful_bits / energy,
            mean_system_power_w=energy / duration,
            mean_system_throughput_bps=useful_bits / duration,
            served_user_intervals=users,
            total_user_intervals=users,
            served_fraction=1.0,
            zero_power_intervals=0,
            zero_service_intervals=0,
            r1_sum=0.0,
            r2_sum=0.0,
            r3_sum=0.0,
        )

    monkeypatch.setattr(
        ablation_evaluator.sweep,
        "evaluate_checkpoint_point",
        fake_evaluate_checkpoint_point,
    )
    published = []
    monkeypatch.setattr(
        ablation_evaluator.output_tools,
        "publish_receipt_last",
        lambda **kwargs: published.append(kwargs),
    )
    output = tmp_path / "artifacts" / "r7" / "evaluation" / "selected-lr-ablation"
    with pytest.raises(
        ablation_evaluator.R7500AblationEvaluationError,
        match="lineage changed before publication",
    ):
        ablation_evaluator.evaluate_ablations(
            authority_path=authority_path,
            bridge_receipt_path=bridge_path,
            reconciliation_receipt_path=reconciliation_path,
            selection_receipt_path=selection_path,
            output_dir=output,
            tle_root=tmp_path / "tle",
            repo=tmp_path,
        )
    assert validations == ["selection-validated", "selection-validated"]
    assert published == []
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    assert not (output / "evaluation-receipt.json").exists()
    assert not (
        tmp_path / validated["resource_policy"]["global_evaluation_lock"]
    ).exists()


def _contrast_summary(*, c1_positive_loads: int = 4) -> list[dict]:
    rows = []
    for index, users in enumerate(authority.EVALUATION_USERS):
        rows.extend(
            [
                {"arm": ablation_evaluator.LABELS["F111"], "users": users, "mean_ee_bits_per_j": 101.0},
                {
                    "arm": ablation_evaluator.LABELS["A011"],
                    "users": users,
                    "mean_ee_bits_per_j": 100.0 if index < c1_positive_loads else 102.0,
                },
                {"arm": ablation_evaluator.LABELS["A101"], "users": users, "mean_ee_bits_per_j": 100.0},
                {"arm": ablation_evaluator.LABELS["A110"], "users": users, "mean_ee_bits_per_j": 100.0},
            ]
        )
    return rows


def test_ablation_contrast_requires_four_of_five_and_positive_mean():
    receipt = ablation_evaluator._contrast_receipt(
        _contrast_summary(c1_positive_loads=4),
        available_arms=["A101", "A011", "A110"],
        failure_only=False,
    )
    assert set(receipt["roles"]) == {"C1", "C2", "C3"}
    assert receipt["failure_analysis_only"] is False
    assert receipt["roles"]["C1"]["preliminarily_ee_positive"] is True
    receipt = ablation_evaluator._contrast_receipt(
        _contrast_summary(c1_positive_loads=3),
        available_arms=["A101", "A011", "A110"],
        failure_only=False,
    )
    assert receipt["roles"]["C1"]["preliminarily_ee_positive"] is False
    failure = ablation_evaluator._contrast_receipt(
        _contrast_summary(), available_arms=["A101"], failure_only=True
    )
    assert set(failure["roles"]) == {"C2"}
    assert failure["roles"]["C2"]["classification"] == (
        "FAILURE_ANALYSIS_ONLY_C2_DIAGNOSTIC"
    )
    assert failure["roles"]["C2"]["preliminarily_ee_positive"] is False


def test_failure_only_svg_has_conspicuous_failure_analysis_only_label(tmp_path):
    summary = _contrast_summary()
    failure_label = "FAILURE-ANALYSIS-ONLY C2 DIAGNOSTIC"
    output = tmp_path / "failure-only.svg"
    evaluator.write_svg_plot(
        output,
        summary,
        learning_rate=0.001,
        title="500-EP Failure-Analysis-Only C2 Diagnostic",
        labels=[
            ablation_evaluator.LABELS["F111"],
            ablation_evaluator.LABELS["A011"],
            ablation_evaluator.LABELS["A101"],
            ablation_evaluator.LABELS["A110"],
        ],
        footer_labels=[*authority.REQUIRED_LABELS, failure_label],
    )
    svg = output.read_text(encoding="utf-8")
    assert failure_label in svg
    assert "500-EP Failure-Analysis-Only C2 Diagnostic" in svg


def test_output_reservation_is_create_only_under_a_two_writer_race(tmp_path):
    output = tmp_path / "evaluation"
    barrier = Barrier(2)

    def attempt(writer: str):
        barrier.wait()
        try:
            _, staging = output_tools.reserve_output_directory(
                output, marker={"writer": writer}
            )
        except FileExistsError:
            return "lost", None
        return "won", staging

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["one", "two"]))
    assert sorted(status for status, _ in results) == ["lost", "won"]
    winner_staging = next(staging for status, staging in results if status == "won")
    assert winner_staging is not None
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    output_tools.abort_reserved_output(staging=winner_staging, output=output)
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()


def test_reservation_loser_preserves_preexisting_empty_winner_directory(tmp_path):
    output = tmp_path / "evaluation"
    output.mkdir(parents=True)
    with pytest.raises(FileExistsError):
        output_tools.reserve_output_directory(
            output,
            marker={"writer": "loser"},
        )
    # A loser must not remove a directory that was created by the winner.  This
    # covers the critical race window even when the winner has not written its
    # reservation marker yet.
    assert output.is_dir()
    assert list(output.iterdir()) == []


def _failure_evaluation_fixture(tmp_path: Path, *, ablation: bool) -> tuple[
    Path, Path, Path, Path, dict, list[dict]
]:
    authority_path = tmp_path / "authority.json"
    bridge_path = tmp_path / "bridge.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    selection_path = tmp_path / "selection.json"
    for path, payload in (
        (authority_path, {"fixture": "authority"}),
        (bridge_path, {"fixture": "bridge"}),
        (reconciliation_path, {"fixture": "reconciliation"}),
        (selection_path, {"fixture": "selection"}),
    ):
        _write_json(path, payload)
    validated = {
        "ablation_output_root": "artifacts/r7",
        "validated_base_authorities": {
            "0.001": {"canonical_prereg": "synthetic-prereg.json"}
        },
        "resource_policy": {
            "global_evaluation_lock": "artifacts/r7/.r7-evaluation.lock"
        },
    }
    checkpoints = []
    if ablation:
        for index, arm in enumerate(authority.ALL_R7_ARMS):
            checkpoint = tmp_path / f"{arm}.pt"
            checkpoint.write_bytes(f"checkpoint-{arm}".encode("utf-8"))
            checkpoints.append(
                {
                    "arm": arm,
                    "label": ablation_evaluator.LABELS[arm],
                    "path": checkpoint,
                    "sha256": authority.sha256_file(checkpoint),
                    "online_policy_sha256": f"{index + 1:064x}",
                    "payload": SimpleNamespace(
                        train_seed=authority.TRAINING_SEEDS["training"]
                    ),
                }
            )
    return (
        authority_path,
        bridge_path,
        reconciliation_path,
        selection_path,
        validated,
        checkpoints,
    )


def test_handled_prefix_failure_releases_owned_lock_and_keeps_incomplete_marker(
    tmp_path, monkeypatch
):
    (
        authority_path,
        bridge_path,
        reconciliation_path,
        _selection_path,
        validated,
        _checkpoints,
    ) = _failure_evaluation_fixture(tmp_path, ablation=False)
    authority_sha = authority.sha256_file(authority_path)
    monkeypatch.setattr(
        evaluator,
        "_load_inputs",
        lambda **kwargs: (
            validated,
            authority_sha,
            {"reconciliation_required": True},
            {"status": "PASS"},
            [],
        ),
    )
    monkeypatch.setattr(
        evaluator.preflight,
        "assert_evaluation_ready",
        lambda **kwargs: {"status": "PASS"},
    )

    def fail_before_rollout(*args, **kwargs):
        raise RuntimeError("synthetic prefix evaluator failure")

    monkeypatch.setattr(
        evaluator.sweep,
        "canonical_ephemeris_authority",
        fail_before_rollout,
    )
    output = tmp_path / "artifacts" / "r7" / "evaluation" / "lr0p001-prefix"
    with pytest.raises(RuntimeError, match="synthetic prefix evaluator failure"):
        evaluator.evaluate_prefixes(
            authority_path=authority_path,
            bridge_receipt_path=bridge_path,
            reconciliation_receipt_path=reconciliation_path,
            learning_rate=0.001,
            output_dir=output,
            tle_root=tmp_path / "tle",
            repo=tmp_path,
        )
    lock = tmp_path / validated["resource_policy"]["global_evaluation_lock"]
    assert not lock.exists()
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    assert not (output / "evaluation-receipt.json").exists()


def test_handled_ablation_failure_releases_owned_lock_and_keeps_incomplete_marker(
    tmp_path, monkeypatch
):
    (
        authority_path,
        bridge_path,
        reconciliation_path,
        selection_path,
        validated,
        checkpoints,
    ) = _failure_evaluation_fixture(tmp_path, ablation=True)
    authority_sha = authority.sha256_file(authority_path)
    selection = {
        "decision": {
            "decision": "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS",
            "selected_learning_rate": 0.001,
            "allowed_ablation_arms": list(authority.ABLATION_ARMS),
        }
    }
    monkeypatch.setattr(
        ablation_evaluator.bridge,
        "load_and_validate_authority",
        lambda *args, **kwargs: (validated, authority_sha),
    )
    monkeypatch.setattr(
        ablation_evaluator.router,
        "validate_selection_receipt",
        lambda *args, **kwargs: selection,
    )
    monkeypatch.setattr(
        ablation_evaluator.prefix_evaluator,
        "_load_inputs",
        lambda **kwargs: (
            validated,
            authority_sha,
            {"fixture": "bridge"},
            {"fixture": "reconciliation"},
            checkpoints,
        ),
    )
    monkeypatch.setattr(
        ablation_evaluator.preflight,
        "assert_evaluation_ready",
        lambda **kwargs: {"status": "PASS"},
    )

    def fail_before_rollout(*args, **kwargs):
        raise RuntimeError("synthetic ablation evaluator failure")

    monkeypatch.setattr(
        ablation_evaluator.sweep,
        "canonical_ephemeris_authority",
        fail_before_rollout,
    )
    output = tmp_path / "artifacts" / "r7" / "evaluation" / "selected-lr-ablation"
    with pytest.raises(RuntimeError, match="synthetic ablation evaluator failure"):
        ablation_evaluator.evaluate_ablations(
            authority_path=authority_path,
            bridge_receipt_path=bridge_path,
            reconciliation_receipt_path=reconciliation_path,
            selection_receipt_path=selection_path,
            output_dir=output,
            tle_root=tmp_path / "tle",
            repo=tmp_path,
        )
    lock = tmp_path / validated["resource_policy"]["global_evaluation_lock"]
    assert not lock.exists()
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    assert not (output / "evaluation-receipt.json").exists()


def test_publish_unlock_finalize_lifecycle_helpers_are_explicit_and_ordered(
    tmp_path, monkeypatch
):
    output, staging = output_tools.reserve_output_directory(
        tmp_path / "evaluation",
        marker={"schema": "fixture", "required_labels": authority.REQUIRED_LABELS},
    )
    lock_marker = {
        "artifact": "fixture-evaluation",
        "authority_sha256": "a" * 64,
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
    }
    lock = output_tools.acquire_evaluation_lock(
        tmp_path / ".r7-evaluation.lock", marker=lock_marker
    )
    _write_json(staging / "artifact.json", {"complete": True})
    _write_json(staging / "evaluation-receipt.json", {"status": "PASS"})
    observed_publications = []
    original_rename = output_tools._rename_noreplace

    def tracked_rename(source, target):
        result = original_rename(source, target)
        observed_publications.append(Path(target).name)
        return result

    monkeypatch.setattr(output_tools, "_rename_noreplace", tracked_rename)
    assert not (output / "evaluation-receipt.json").exists()
    assert (output / output_tools.INCOMPLETE_MARKER).exists()
    assert lock.is_file()
    output_tools.publish_receipt_last(
        staging=staging,
        output=output,
        receipt_name="evaluation-receipt.json",
    )
    assert observed_publications == ["artifact.json", "evaluation-receipt.json"]
    assert (output / "artifact.json").is_file()
    assert (output / "evaluation-receipt.json").is_file()
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    assert lock.is_file()
    assert not staging.exists()
    output_tools.release_evaluation_lock(lock, expected_marker=lock_marker)
    assert not lock.exists()
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    output_tools.finalize_publication(
        output=output,
        receipt_name="evaluation-receipt.json",
    )
    assert not (output / output_tools.INCOMPLETE_MARKER).exists()


def test_evaluation_lock_release_preserves_owner_or_marker_mismatch(tmp_path):
    expected_marker = {
        "artifact": "fixture-evaluation",
        "authority_sha256": "a" * 64,
    }
    lock = output_tools.acquire_evaluation_lock(
        tmp_path / ".r7-evaluation.lock", marker=expected_marker
    )
    original = json.loads(lock.read_text(encoding="utf-8"))
    wrong_owner = {**original, "pid": -1}
    _write_json(lock, wrong_owner)
    with pytest.raises(RuntimeError, match="another work item"):
        output_tools.release_evaluation_lock(
            lock,
            expected_marker=expected_marker,
        )
    assert json.loads(lock.read_text(encoding="utf-8")) == wrong_owner

    _write_json(lock, original)
    with pytest.raises(RuntimeError, match="another work item"):
        output_tools.release_evaluation_lock(
            lock,
            expected_marker={**expected_marker, "artifact": "foreign-evaluation"},
        )
    assert json.loads(lock.read_text(encoding="utf-8")) == original
    output_tools.release_evaluation_lock(lock, expected_marker=expected_marker)
    assert not lock.exists()


def test_atomic_rename_noreplace_collision_preserves_foreign_receipt_and_marker(
    tmp_path, monkeypatch
):
    output, staging = output_tools.reserve_output_directory(
        tmp_path / "evaluation",
        marker={"schema": "fixture", "required_labels": authority.REQUIRED_LABELS},
    )
    receipt_name = "evaluation-receipt.json"
    _write_json(staging / receipt_name, {"status": "PASS", "writer": "reserved"})
    foreign_bytes = b'{"status":"FOREIGN"}\n'
    original_rename = output_tools._rename_noreplace
    injected = False

    def collide_after_reservation(source, destination):
        nonlocal injected
        if not injected:
            Path(destination).write_bytes(foreign_bytes)
            injected = True
        return original_rename(source, destination)

    monkeypatch.setattr(output_tools, "_rename_noreplace", collide_after_reservation)
    with pytest.raises(FileExistsError):
        output_tools.publish_receipt_last(
            staging=staging,
            output=output,
            receipt_name=receipt_name,
        )
    assert injected is True
    assert (output / receipt_name).read_bytes() == foreign_bytes
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    assert (staging / receipt_name).is_file()
    with pytest.raises(router.R7500LRRoutingError, match="incomplete"):
        router._assessment(
            output / receipt_name,
            expected_learning_rate=0.001,
            authority_sha256="a" * 64,
        )
    output_tools.abort_reserved_output(staging=staging, output=output)
    assert not staging.exists()
    assert (output / receipt_name).read_bytes() == foreign_bytes
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()


def test_output_publication_without_receipt_stays_visibly_incomplete(tmp_path):
    output, staging = output_tools.reserve_output_directory(
        tmp_path / "evaluation", marker={"schema": "fixture"}
    )
    _write_json(staging / "artifact.json", {"complete": True})
    with pytest.raises(FileNotFoundError, match="receipt is missing"):
        output_tools.publish_receipt_last(
            staging=staging,
            output=output,
            receipt_name="evaluation-receipt.json",
        )
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()
    assert not (output / "artifact.json").exists()
    output_tools.abort_reserved_output(staging=staging, output=output)
    assert not staging.exists()
    assert (output / output_tools.INCOMPLETE_MARKER).is_file()


def test_required_five_labels_are_exact_and_present_in_the_svg_and_claim_artifacts(
    tmp_path, monkeypatch
):
    assert authority.REQUIRED_LABELS == [
        "500-EP PRELIMINARY",
        "ONE TRAINED POLICY",
        "MAIN-ONLY HELD-OUT TEST EVALUATION",
        "NOT A CHAPTER 5 RESULT",
        "NOT FORMAL EFFICACY",
    ]
    assert len(set(authority.REQUIRED_LABELS)) == 5
    summary = [
        {"arm": label, "users": users, "mean_ee_bits_per_j": 1_000_000.0}
        for label in evaluator.ARM_LABELS.values()
        for users in authority.EVALUATION_USERS
    ]
    output = tmp_path / "fixture.svg"
    evaluator.write_svg_plot(
        output,
        summary,
        learning_rate=0.001,
        title="Synthetic control-plane fixture",
        labels=list(evaluator.ARM_LABELS.values()),
    )
    svg = output.read_text(encoding="utf-8")
    for label in authority.REQUIRED_LABELS:
        assert label in svg

    _, _, bridge_path, reconciliation_path = _prefix_lineage_fixture(
        tmp_path / "lineage", monkeypatch
    )
    evaluation_path = _evaluation_fixture(
        tmp_path / "evaluation",
        learning_rate=0.001,
        baseline_ee=100.0,
        full_ee=110.0,
    )
    evaluation_receipt = json.loads(evaluation_path.read_text(encoding="utf-8"))
    claim_artifacts = [
        freezer.build_request(),
        json.loads(bridge_path.read_text(encoding="utf-8")),
        json.loads(reconciliation_path.read_text(encoding="utf-8")),
        evaluation_receipt,
        json.loads(
            Path(evaluation_receipt["artifacts"]["raw"]["path"]).read_text(
                encoding="utf-8"
            )
        ),
        json.loads(
            Path(evaluation_receipt["artifacts"]["summary"]["path"]).read_text(
                encoding="utf-8"
            )
        ),
        _evaluation_gate(),
    ]
    assert all(
        artifact["required_labels"] == authority.REQUIRED_LABELS
        for artifact in claim_artifacts
    )


def test_runtime_closure_has_55_unique_source_reuse_files_and_package_initializers():
    manifest = REPO / authority.RUNTIME_CLOSURE_MANIFEST
    rows = manifest.read_text(encoding="utf-8").splitlines()
    assert len(rows) == authority.RUNTIME_CLOSURE_FILE_COUNT == 55
    assert rows == sorted(set(rows))
    request = freezer.build_request()
    validated = authority.validate_r7_500_authority(
        request, repo=REPO, tle_root=LOCAL_TLE
    )
    closure = validated["runtime_closure"]
    assert closure["status"] == "PASS"
    assert closure["file_count"] == 55
    assert closure["r7_direct_count"] + closure["r2_inherited_count"] == 55
    assert {
        "src/mcrl/__init__.py",
        "src/mcrl/algorithms/__init__.py",
        "src/mcrl/artifacts/__init__.py",
        "src/mcrl/env/__init__.py",
        "src/mcrl/runtime/__init__.py",
    }.issubset(rows)
    assert not any("r7_500_arm.py" in row or "capacity" in row for row in rows)
    assert not any("matplotlib" in row for row in rows)
    assert all((REPO / relative).is_file() for relative in rows)
