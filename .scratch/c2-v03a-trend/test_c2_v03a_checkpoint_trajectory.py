"""Current-layout checkpoint trajectory tests for C2 V0.3A."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_v03a_checkpoint_trajectory as trajectory  # noqa: E402


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _fake_payload(path: Path) -> SimpleNamespace:
    completed = int(Path(path).stem.split("-")[1])
    arm = Path(path).parent.parent.name
    return SimpleNamespace(
        episode=completed - 1,
        train_seed=trajectory.TRAINING_SEEDS["training"],
        env_seed=trajectory.TRAINING_SEEDS["environment"],
        mobility_seed=trajectory.TRAINING_SEEDS["mobility"],
        checkpoint_kind="periodic-main-policy-trend",
        state_dim=4,
        action_dim=3,
        trainer_config={"learning_rate": 0.001},
        q_networks=[{"weight": f"{arm}-{completed}-{index}"} for index in range(3)],
        target_networks=[
            {"weight": f"target-{arm}-{completed}-{index}"} for index in range(3)
        ],
        optimizers=[{}],
    )


def _selector_summary(path: Path, *, full_ee: float) -> None:
    scores = {
        "B000": 1.0,
        "F111": full_ee,
        "A011": 1.1,
        "A101": 1.1,
        "A110": 1.1,
    }
    _write_json(
        path,
        {
            "summary": [
                {
                    "arm": trajectory.ARM_LABELS[arm],
                    "users": 100,
                    "mean_ee_bits_per_j": scores[arm],
                }
                for arm in trajectory.ALLOWED_ARMS
            ]
        },
    )


def _inventory_fixture(tmp_path: Path) -> tuple[Path, dict, Path, dict[str, dict]]:
    root = tmp_path / "matrix"
    root.mkdir()
    authority_path = tmp_path / "authority.json"
    _write_json(authority_path, {"fixture": True})
    _write_json(
        root / "matrix-status.json",
        {
            "status": "complete",
            "learning_rate": 0.001,
            "authority": str(authority_path.resolve()),
        },
    )
    schedule = trajectory.checkpoint_schedule(1500)
    for arm in trajectory.ALLOWED_ARMS:
        rows = []
        for completed in schedule:
            checkpoint = (
                root
                / "arms"
                / arm
                / "checkpoints"
                / f"ep-{completed:06d}-main.pt"
            )
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_bytes(f"{arm}-{completed}".encode("ascii"))
            rows.append(
                {
                    "episodes_completed": completed,
                    "episode_index": completed - 1,
                    "path": str(checkpoint.resolve()),
                    "sha256": trajectory.sha256_file(checkpoint),
                    "checkpoint_kind": "periodic-main-policy-trend",
                    "load_round_trip": "PASS",
                }
            )
        _write_json(
            root / "arms" / arm / "status.json",
            {
                "status": "complete",
                "run_mode": "fresh_intermediate_trend",
                "arm": arm,
                "formal_training_authorized": False,
                "trainer_config": {"learning_rate": 0.001},
                "result": {
                    "start_episode": 0,
                    "periodic_checkpoints": rows,
                    **({} if arm == "B000" else {"artifact_scope": "complete_run"}),
                },
            },
        )
    validated = {
        "episodes": 1500,
        "learning_rate": 0.001,
        "checkpoint_every_episodes": 100,
        "seeds": trajectory.TRAINING_SEEDS,
        "evaluation_seeds": trajectory.EVALUATION_SEEDS,
        "canonical_prereg": "artifacts/fixture-prereg.json",
    }
    sealed_arms = []
    for arm in trajectory.ALLOWED_ARMS:
        rows = json.loads(
            (root / "arms" / arm / "status.json").read_text(encoding="utf-8")
        )["result"]["periodic_checkpoints"]
        sealed_arms.append(
            {
                "arm": arm,
                "periodic_checkpoints": [
                    {
                        "episodes_completed": row["episodes_completed"],
                        "sha256": row["sha256"],
                        "online_policy_sha256": trajectory.postrun.checkpoint_policy_sha256(
                            _fake_payload(Path(row["path"]))
                        ),
                    }
                    for row in rows
                ],
            }
        )
    other_root = tmp_path / "other-matrix"
    other_root.mkdir()
    _write_json(
        other_root / "matrix-status.json",
        {"status": "complete", "learning_rate": 0.01},
    )
    lr0p001_summary = root / "evaluation" / "sweep-summary.json"
    lr0p01_summary = other_root / "evaluation" / "sweep-summary.json"
    _selector_summary(lr0p001_summary, full_ee=0.9)
    _selector_summary(lr0p01_summary, full_ee=0.8)
    mechanism_sha = "a" * 64
    normalized_authority_sha = "b" * 64
    matrix_receipt = {
        "status": "PASS",
        "matrix_root": str(root.resolve()),
        "matrix_status": str((root / "matrix-status.json").resolve()),
        "matrix_status_sha256": trajectory.sha256_file(root / "matrix-status.json"),
        "learning_rate": 0.001,
        "arms": sealed_arms,
        "sweep_summary": str(lr0p001_summary.resolve()),
        "sweep_summary_sha256": trajectory.sha256_file(lr0p001_summary),
        "mechanism_environment_source_sha256": mechanism_sha,
        "normalized_authority_excluding_learning_rate_sha256": normalized_authority_sha,
    }
    other_matrix_receipt = {
        "status": "PASS",
        "matrix_root": str(other_root.resolve()),
        "matrix_status": str((other_root / "matrix-status.json").resolve()),
        "matrix_status_sha256": trajectory.sha256_file(
            other_root / "matrix-status.json"
        ),
        "learning_rate": 0.01,
        "arms": [{"arm": arm, "receipt": "other"} for arm in trajectory.ALLOWED_ARMS],
        "sweep_summary": str(lr0p01_summary.resolve()),
        "sweep_summary_sha256": trajectory.sha256_file(lr0p01_summary),
        "mechanism_environment_source_sha256": mechanism_sha,
        "normalized_authority_excluding_learning_rate_sha256": normalized_authority_sha,
    }
    live_validations = {
        "0.001": matrix_receipt,
        "0.01": other_matrix_receipt,
    }
    selection = trajectory.postrun.lr_selector.select_learning_rate(
        lr0p001_summary, lr0p01_summary
    )
    selection_path = tmp_path / "lr-selection.json"
    _write_json(selection_path, selection)
    postrun_path = tmp_path / "postrun-receipt.json"
    _write_json(
        postrun_path,
        {
            "schema": trajectory.postrun.SCHEMA,
            "status": "PASS",
            "decision": "STOP_BEFORE_3000",
            "selected_learning_rate": None,
            "formal_training_authorized": False,
            "fresh_3000_launch_performed": False,
            "matrices": live_validations,
            "cross_lr_mechanism_consistency": {
                "status": "PASS",
                "environment_source_sha256": mechanism_sha,
                "normalized_authority_excluding_learning_rate_sha256": normalized_authority_sha,
            },
            "lr_selection": {
                "path": str(selection_path.resolve()),
                "sha256": trajectory.sha256_file(selection_path),
            },
        },
    )
    return root, validated, postrun_path, live_validations


def _patch_validation(monkeypatch, validated, live_validations):
    def fake_validate_matrix(root, *, tle_root, expected_learning_rate):
        key = str(expected_learning_rate)
        expected = live_validations[key]
        if Path(root).resolve() != Path(expected["matrix_root"]):
            raise AssertionError("learning-rate key and matrix root disagree")
        return expected

    monkeypatch.setattr(trajectory.postrun, "validate_matrix", fake_validate_matrix)
    monkeypatch.setattr(
        trajectory.arm_runner,
        "load_and_validate_authority",
        lambda path, *, tle_root: validated,
    )

    def fake_read_checkpoint(path, *, map_location):
        return _fake_payload(Path(path))

    monkeypatch.setattr(trajectory, "read_checkpoint", fake_read_checkpoint)


def test_current_layout_inventory_requires_exact_5_by_15_grid(tmp_path, monkeypatch):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)

    authority, inventory = trajectory.load_checkpoint_inventory(
        root, tle_root=tmp_path, postrun_receipt=postrun_receipt
    )

    assert authority["episodes"] == 1500
    assert authority["evaluation_seeds"] == trajectory.EVALUATION_SEEDS
    assert len(inventory) == 75
    assert inventory[0]["episodes_completed"] == 100
    assert inventory[-1]["episodes_completed"] == 1500


def test_inventory_fails_when_one_periodic_checkpoint_is_missing(tmp_path, monkeypatch):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)
    status_path = root / "arms" / "A110" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["result"]["periodic_checkpoints"].pop()
    _write_json(status_path, status)

    with pytest.raises(trajectory.V03ATrajectoryError, match="A110 periodic"):
        trajectory.load_checkpoint_inventory(
            root, tle_root=tmp_path, postrun_receipt=postrun_receipt
        )


def test_trajectory_requires_both_matrix_receipts_to_remain_sealed(
    tmp_path, monkeypatch
):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)
    receipt = json.loads(postrun_receipt.read_text(encoding="utf-8"))
    other_status = Path(receipt["matrices"]["0.01"]["matrix_status"])
    _write_json(other_status, {"status": "failed"})

    with pytest.raises(trajectory.V03ATrajectoryError, match="0.01 status identity"):
        trajectory.load_checkpoint_inventory(
            root, tle_root=tmp_path, postrun_receipt=postrun_receipt
        )


def test_trajectory_rejects_incomplete_other_matrix_receipt(tmp_path, monkeypatch):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)
    receipt = json.loads(postrun_receipt.read_text(encoding="utf-8"))
    receipt["matrices"]["0.01"]["arms"] = []
    _write_json(postrun_receipt, receipt)

    with pytest.raises(trajectory.V03ATrajectoryError, match="0.01 receipt disagrees"):
        trajectory.load_checkpoint_inventory(
            root, tle_root=tmp_path, postrun_receipt=postrun_receipt
        )


def test_trajectory_rejects_missing_other_sweep_receipt(tmp_path, monkeypatch):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)
    receipt = json.loads(postrun_receipt.read_text(encoding="utf-8"))
    receipt["matrices"]["0.01"].pop("sweep_summary")
    _write_json(postrun_receipt, receipt)

    with pytest.raises(trajectory.V03ATrajectoryError, match="0.01 receipt disagrees"):
        trajectory.load_checkpoint_inventory(
            root, tle_root=tmp_path, postrun_receipt=postrun_receipt
        )


def test_trajectory_rejects_learning_rate_root_swap(tmp_path, monkeypatch):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)
    receipt = json.loads(postrun_receipt.read_text(encoding="utf-8"))
    receipt["matrices"]["0.001"], receipt["matrices"]["0.01"] = (
        receipt["matrices"]["0.01"],
        receipt["matrices"]["0.001"],
    )
    _write_json(postrun_receipt, receipt)

    with pytest.raises(trajectory.V03ATrajectoryError, match="0.001 failed fresh"):
        trajectory.load_checkpoint_inventory(
            root, tle_root=tmp_path, postrun_receipt=postrun_receipt
        )


def test_trajectory_rejects_selector_input_rebinding(tmp_path, monkeypatch):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)
    receipt = json.loads(postrun_receipt.read_text(encoding="utf-8"))
    selection_path = Path(receipt["lr_selection"]["path"])
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    selection["inputs"]["0.01"]["path"] = selection["inputs"]["0.001"]["path"]
    _write_json(selection_path, selection)
    receipt["lr_selection"]["sha256"] = trajectory.sha256_file(selection_path)
    _write_json(postrun_receipt, receipt)

    with pytest.raises(trajectory.V03ATrajectoryError, match="inputs or decision"):
        trajectory.load_checkpoint_inventory(
            root, tle_root=tmp_path, postrun_receipt=postrun_receipt
        )


def test_trajectory_explicitly_rejects_endpoint_only_resume_history(
    tmp_path, monkeypatch
):
    root, validated, postrun_receipt, live_validations = _inventory_fixture(tmp_path)
    _patch_validation(monkeypatch, validated, live_validations)
    status_path = root / "arms" / "F111" / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["run_mode"] = "resume_intermediate_trend"
    status["result"]["start_episode"] = 700
    status["result"]["artifact_scope"] = "resume_segment_only"
    _write_json(status_path, status)

    with pytest.raises(trajectory.V03ATrajectoryError, match="fresh complete"):
        trajectory.load_checkpoint_inventory(
            root, tle_root=tmp_path, postrun_receipt=postrun_receipt
        )


def test_trajectory_uses_ratio_of_pooled_sums_for_every_cell():
    rows = []
    for arm in trajectory.ALLOWED_ARMS:
        for completed in trajectory.checkpoint_schedule(1500):
            for index, seed in enumerate(trajectory.EVALUATION_SEEDS):
                bits = 100.0 if index == 0 else 10.0
                energy = 100.0 if index == 0 else 1.0
                rows.append(
                    {
                        "arm": arm,
                        "episodes_completed": completed,
                        "evaluation_seed": seed,
                        "useful_bits": bits,
                        "system_energy_j": energy,
                        "served_user_intervals": 1,
                        "total_user_intervals": 1,
                        "zero_power_intervals": 0,
                        "zero_service_intervals": 0,
                    }
                )

    summary = trajectory.aggregate_trajectory(rows)

    assert len(summary) == 75
    assert summary[0]["system_ee_bits_per_j"] == pytest.approx(140.0 / 104.0)
