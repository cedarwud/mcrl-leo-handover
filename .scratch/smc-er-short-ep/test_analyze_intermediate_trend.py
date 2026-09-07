from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "analyze_intermediate_trend_under_test", HERE / "analyze_intermediate_trend.py"
)
assert SPEC is not None and SPEC.loader is not None
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


CANONICAL_PREREG = M.REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
CANONICAL_C1 = M.DEFAULT_C1_MANIFEST
TRAINING_SEED = 2026082901
ENVIRONMENT_SEED = 2026082902
MOBILITY_SEED = 2026082903


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _authority(monkeypatch, tmp_path: Path, *, episodes: int, learning_rate: float):
    """Bind the synthetic receipt to real canonical prereg/C1 bytes.

    The authority validator itself is exercised by its own focused test file;
    this fixture isolates the post-run arithmetic while still checking all
    path/hash bindings made by the analyzer.
    """

    tle_root = tmp_path / "tle"
    tle_root.mkdir(parents=True)
    (tle_root / "starlink_20260801.tle").write_bytes(b"synthetic TLE")
    monkeypatch.setattr(
        M,
        "canonical_tle_file_set_hash",
        lambda _root: (M.CANONICAL_TLE_FILE_SET_SHA256, 1),
    )
    authority_path = tmp_path / "authority.json"
    authority_path.write_text("{}\n", encoding="utf-8")
    validated = {
        "status": "PASS",
        "episodes": episodes,
        "learning_rate": learning_rate,
        "seeds": {
            "training": TRAINING_SEED,
            "environment": ENVIRONMENT_SEED,
            "mobility": MOBILITY_SEED,
            "evaluation_seeds": list(M.EXPECTED_EVALUATION_SEEDS),
        },
        "config": {
            "users": M.TREND_USERS,
            "evaluation_users": list(M.EXPECTED_EVALUATION_USERS),
            "epsilon_decay_episodes": M.TREND_EPSILON_DECAY_EPISODES,
            "target_update_every": M.TREND_TARGET_UPDATE_EVERY,
            "checkpoint_every_episodes": M.TREND_CHECKPOINT_EVERY_EPISODES,
            "specialist_bundle_replay_capacity": M.TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
            "acrm_eta": M.TREND_ACRM_ETA,
            "donor_beta": M.TREND_DONOR_BETA,
        },
        "authority": {
            "canonical_prereg": str(CANONICAL_PREREG.resolve()),
            "c1_exp_corpus_manifest": str(CANONICAL_C1.resolve()),
            "tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256,
        },
    }
    monkeypatch.setattr(
        M,
        "_load_authority",
        lambda _path, *, tle_root: validated,
    )
    return authority_path, tle_root


def _write_matrix(
    monkeypatch,
    tmp_path: Path,
    *,
    episodes: int = 3000,
    learning_rate: float = 0.001,
    ee_by_arm: dict[str, float] | None = None,
    full_service: float = 1.0,
) -> Path:
    authority_path, tle_root = _authority(
        monkeypatch,
        tmp_path,
        episodes=episodes,
        learning_rate=learning_rate,
    )
    root = tmp_path / f"matrix-{episodes}-{learning_rate}"
    root.mkdir()
    logs = root / "logs"
    logs.mkdir()
    checkpoint_receipts: dict[str, dict[str, str | Path]] = {}
    arm_runs: list[dict[str, object]] = []

    for arm in M.EXPECTED_ARMS:
        arm_dir = root / arm
        arm_dir.mkdir()
        checkpoint = arm_dir / "final-checkpoint.pt"
        checkpoint.write_bytes(f"checkpoint-{arm}".encode("ascii"))
        status_path = arm_dir / "status.json"
        log_path = logs / f"{arm}.log"
        log_path.write_text(f"log-{arm}\n", encoding="utf-8")
        checkpoint_sha = _sha(checkpoint)
        status = {
            "status": "complete",
            "arm": arm,
            "label": M.ARM_LABELS[arm],
            "episodes": episodes,
            "users": M.TREND_USERS,
            "seeds": {
                "training": TRAINING_SEED,
                "environment": ENVIRONMENT_SEED,
                "mobility": MOBILITY_SEED,
            },
            "config": {
                "episodes": episodes,
                "users": M.TREND_USERS,
                "learning_rate": learning_rate,
                "epsilon_decay_episodes": M.TREND_EPSILON_DECAY_EPISODES,
                "target_update_every_episodes": M.TREND_TARGET_UPDATE_EVERY,
            },
            "checkpointing": {
                "every_episodes": M.TREND_CHECKPOINT_EVERY_EPISODES,
                "specialist_bundle_replay_capacity": M.TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
            },
            "authority": {
                "prereg_path": str(CANONICAL_PREREG.resolve()),
                "prereg_sha256": _sha(CANONICAL_PREREG),
                "tle_root_path": str(tle_root.resolve()),
                "tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256,
                "tle_file_count": 1,
            },
            "gate_manifest": {"validated": {"config": {"acrm_eta": M.TREND_ACRM_ETA}}},
            "result": {
                "episodes": episodes,
                "checkpoint": str(checkpoint.resolve()),
                "checkpoint_sha256": checkpoint_sha,
            },
        }
        status_path.write_text(
            json.dumps(status, sort_keys=True) + "\n", encoding="utf-8"
        )
        checkpoint_receipts[arm] = {
            "path": checkpoint,
            "sha256": checkpoint_sha,
        }
        arm_runs.append(
            {
                "arm": arm,
                "attempt": 1,
                "status": "PASS",
                "command": [
                    "python",
                    "run_short_ep.py",
                    "--arm",
                    arm,
                    "--output-dir",
                    str(arm_dir.resolve()),
                    "--episodes",
                    str(episodes),
                    "--users",
                    str(M.TREND_USERS),
                    "--train-seed",
                    str(TRAINING_SEED),
                    "--env-seed",
                    str(ENVIRONMENT_SEED),
                    "--mobility-seed",
                    str(MOBILITY_SEED),
                    "--epsilon-decay-episodes",
                    str(M.TREND_EPSILON_DECAY_EPISODES),
                    "--target-update-every",
                    str(M.TREND_TARGET_UPDATE_EVERY),
                    "--checkpoint-every",
                    str(M.TREND_CHECKPOINT_EVERY_EPISODES),
                    "--learning-rate",
                    str(learning_rate),
                    "--acrm-eta",
                    str(M.TREND_ACRM_ETA),
                    "--intermediate-trend-authority",
                    str(authority_path.resolve()),
                    "--prereg",
                    str(CANONICAL_PREREG.resolve()),
                    "--tle-root",
                    str(tle_root.resolve()),
                ],
                "started_utc": "2026-08-28T00:00:00+00:00",
                "ended_utc": "2026-08-28T00:00:01+00:00",
                "elapsed_s": 1.0,
                "exit_code": 0,
                "log": str(log_path.resolve()),
                "log_sha256": _sha(log_path),
                "verification": {
                    "status": "PASS",
                    "status_path": str(status_path.resolve()),
                    "status_sha256": _sha(status_path),
                    "checkpoint_path": str(checkpoint.resolve()),
                    "checkpoint_sha256": checkpoint_sha,
                },
            }
        )
        if arm != "B000":
            arm_runs[-1]["command"].extend(
                ["--c1-exp-corpus-manifest", str(CANONICAL_C1.resolve())]
            )

    labels = {arm: M.ARM_LABELS[arm] for arm in M.EXPECTED_ARMS}
    if ee_by_arm is None:
        ee_by_arm = {
            "B000": 100.0,
            "F111": 110.0,
            "A011": 105.0,
            "A101": 106.0,
            "A110": 107.0,
        }
    raw_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for arm in M.EXPECTED_ARMS:
        checkpoint_sha = str(checkpoint_receipts[arm]["sha256"])
        label = labels[arm]
        for users in M.EXPECTED_EVALUATION_USERS:
            ee = float(ee_by_arm[arm]) + (users - 100) / 1000.0
            total = 10 * users
            served = round(total * (full_service if arm == "F111" else 1.0))
            for evaluation_seed in M.EXPECTED_EVALUATION_SEEDS:
                bits = ee * 10.0
                raw_rows.append(
                    {
                        "arm": label,
                        "checkpoint_sha256": checkpoint_sha,
                        "training_seed": TRAINING_SEED,
                        "evaluation_seed": evaluation_seed,
                        "users": users,
                        "steps": 10,
                        "duration_s": 10.0,
                        "useful_bits": bits,
                        "system_energy_j": 10.0,
                        "system_ee_bits_per_j": ee,
                        "mean_system_power_w": 1.0,
                        "mean_system_throughput_bps": ee,
                        "served_user_intervals": served,
                        "total_user_intervals": total,
                        "served_fraction": served / total,
                        "zero_power_intervals": 0,
                        "zero_service_intervals": 0,
                        "r1_sum": 1.0,
                        "r2_sum": -2.0,
                        "r3_sum": -3.0,
                    }
                )
            pooled_bits = bits * len(M.EXPECTED_EVALUATION_SEEDS)
            pooled_energy = 10.0 * len(M.EXPECTED_EVALUATION_SEEDS)
            pooled_total = total * len(M.EXPECTED_EVALUATION_SEEDS)
            pooled_served = served * len(M.EXPECTED_EVALUATION_SEEDS)
            seed_row = {
                "arm": label,
                "users": users,
                "training_seed": TRAINING_SEED,
                "evaluation_seeds": list(M.EXPECTED_EVALUATION_SEEDS),
                "useful_bits": pooled_bits,
                "system_energy_j": pooled_energy,
                "system_ee_bits_per_j": pooled_bits / pooled_energy,
                "mean_system_power_w": 1.0,
                "mean_system_throughput_bps": pooled_bits / 50.0,
                "served_fraction": pooled_served / pooled_total,
                "zero_power_intervals": 0,
                "zero_service_intervals": 0,
            }
            summary_rows.append(
                {
                    "arm": label,
                    "users": users,
                    "training_seed_count": 1,
                    "mean_ee_bits_per_j": ee,
                    "median_ee_bits_per_j": ee,
                    "min_ee_bits_per_j": ee,
                    "max_ee_bits_per_j": ee,
                    "seed_rows": [seed_row],
                }
            )

    plot = root / "ee-sweep" / "ee-vs-users-short-ep.png"
    plot.parent.mkdir()
    plot.write_bytes(b"synthetic plot")
    plot_status_path = plot.parent / "plot-status.json"
    plot_status_path.write_text(
        json.dumps({"status": "complete", "path": str(plot.resolve())}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    summary_path = plot.parent / "sweep-summary.json"
    raw_path = plot.parent / "sweep-raw.json"
    sweep_summary = {
        "schema": M.SWEEP_SCHEMA,
        "method_family": "Multi-Catfish MCRL",
        "evaluation_policy": "Main-only masked-greedy MODQN",
        "evaluation_partition": "TEST",
        "ee_aggregation": "per-training-seed ratio-of-sums, then equal-weight training-seed mean",
        "users": list(M.EXPECTED_EVALUATION_USERS),
        "evaluation_seeds": list(M.EXPECTED_EVALUATION_SEEDS),
        "authority": {
            "prereg_path": str(CANONICAL_PREREG.resolve()),
            "prereg_sha256": _sha(CANONICAL_PREREG),
            "tle_root_path": str(tle_root.resolve()),
            "tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256,
            "tle_file_count": 1,
        },
        "checkpoints": [
            {
                "arm": labels[arm],
                "path": str(checkpoint_receipts[arm]["path"]),
                "sha256": checkpoint_receipts[arm]["sha256"],
                "episode": episodes - 1,
                "training_seed": TRAINING_SEED,
            }
            for arm in M.EXPECTED_ARMS
        ],
        "summary": summary_rows,
    }
    summary_path.write_text(
        json.dumps(sweep_summary, sort_keys=True) + "\n", encoding="utf-8"
    )
    raw_path.write_text(json.dumps(raw_rows, sort_keys=True) + "\n", encoding="utf-8")

    receipt = {
        "schema": M.MATRIX_SCHEMA,
        "status": "complete",
        "claim_ceiling": M.CLAIM_CEILING,
        "formal_training_authorized": False,
        "authority_manifest": str(authority_path.resolve()),
        "authority_manifest_sha256": _sha(authority_path),
        "episodes": episodes,
        "learning_rate": learning_rate,
        "arms": list(M.EXPECTED_ARMS),
        "max_parallel": 1,
        "no_retry": True,
        "training": {
            "users": M.TREND_USERS,
            "training_seed": TRAINING_SEED,
            "environment_seed": ENVIRONMENT_SEED,
            "mobility_seed": MOBILITY_SEED,
            "epsilon_decay_episodes": M.TREND_EPSILON_DECAY_EPISODES,
            "target_update_every": M.TREND_TARGET_UPDATE_EVERY,
            "checkpoint_every_episodes": M.TREND_CHECKPOINT_EVERY_EPISODES,
            "specialist_bundle_replay_capacity": M.TREND_SPECIALIST_BUNDLE_REPLAY_CAPACITY,
            "acrm_eta": M.TREND_ACRM_ETA,
            "donor_beta": 0.25,
        },
        "evaluation": {
            "users": list(M.EXPECTED_EVALUATION_USERS),
            "seeds": list(M.EXPECTED_EVALUATION_SEEDS),
            "policy": "Main-only masked-greedy MODQN",
            "partition": "TEST",
            "ee_aggregation": "ratio-of-sums per training seed, then equal-weight mean",
        },
        "canonical_inputs": {
            "prereg": str(CANONICAL_PREREG.resolve()),
            "prereg_sha256": _sha(CANONICAL_PREREG),
            "c1_exp_corpus_manifest": str(CANONICAL_C1.resolve()),
            "c1_exp_corpus_manifest_sha256": _sha(CANONICAL_C1),
            "tle_root": str(tle_root.resolve()),
            "tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256,
            "tle_file_count": 1,
        },
        "arm_runs": arm_runs,
        "sweep": {
            "status": "PASS",
            "verification": {
                "status": "PASS",
                "summary_path": str(summary_path.resolve()),
                "summary_sha256": _sha(summary_path),
                "raw_path": str(raw_path.resolve()),
                "raw_sha256": _sha(raw_path),
                "plot_status_path": str(plot_status_path.resolve()),
                "plot_status_sha256": _sha(plot_status_path),
            },
        },
    }
    (root / "matrix-receipt.json").write_text(
        json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8"
    )
    return root


def test_3000_analysis_reconstructs_ratio_contrasts_and_directional_gate(
    monkeypatch, tmp_path
):
    root = _write_matrix(monkeypatch, tmp_path)
    result = M.analyse_matrix_roots([root], output_dir=tmp_path / "analysis")

    assert result["status"] == "complete"
    matrix = result["matrices"][0]
    assert matrix["mean_contrasts_percent"]["d_full"] == pytest.approx(10.0)
    assert matrix["mean_contrasts_percent"]["d_C1"] == pytest.approx(
        100.0 * (110.0 - 105.0) / 105.0
    )
    assert matrix["contrast_signs"] == {
        "d_full": "positive",
        "d_C1": "positive",
        "d_C2": "positive",
        "d_C3": "positive",
    }
    assert matrix["directional_3000"]["label"] == (
        "ALL_THREE_DIRECTIONALLY_EE_POSITIVE"
    )
    assert matrix["directional_3000"]["pass"] is True
    assert matrix["guards"]["complete_5_arm_5_load_5_seed_grid"] is True


def test_unfavourable_role_sign_is_preserved_and_gate_fails(monkeypatch, tmp_path):
    root = _write_matrix(
        monkeypatch,
        tmp_path,
        ee_by_arm={
            "B000": 100.0,
            "F111": 110.0,
            "A011": 105.0,
            "A101": 120.0,
            "A110": 107.0,
        },
    )
    result = M.analyse_matrix_roots([root], output_dir=tmp_path / "analysis")
    matrix = result["matrices"][0]

    assert matrix["mean_contrasts_percent"]["d_C2"] == pytest.approx(
        100.0 * (110.0 - 120.0) / 120.0
    )
    assert matrix["contrast_signs"]["d_C2"] == "negative"
    assert matrix["directional_3000"]["pass"] is False
    assert any("d_C2 mean is not positive" in item for item in matrix["directional_3000"]["reasons"])


def test_lr_score_tie_rule_selects_001_and_ineligible_candidate_is_excluded():
    def matrix(lr: float, *, eligible: bool, score: float | None):
        return {
            "episodes": 1500,
            "learning_rate": lr,
            "matrix_root": f"/matrix/{lr}",
            "eligible_for_3000": eligible,
            "lr_score_min_mean_catfish_contrast": score,
        }

    selected = M._select_learning_rate(
        [matrix(0.01, eligible=True, score=1.20), matrix(0.001, eligible=True, score=1.00)]
    )
    assert selected["status"] == "SELECTED"
    assert selected["selected_learning_rate"] == 0.001
    assert selected["tie_rule_percentage_points"] == 0.25

    only = M._select_learning_rate(
        [matrix(0.01, eligible=False, score=None), matrix(0.001, eligible=True, score=-2.0)]
    )
    assert only["selected_learning_rate"] == 0.001
    assert only["reason"] == "only one learning rate passed eligibility"


def test_hash_drift_and_duplicate_arm_command_fail_closed(monkeypatch, tmp_path):
    root = _write_matrix(monkeypatch, tmp_path)
    receipt_path = root / "matrix-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["arm_runs"][0]["command"] = [
        "python",
        "run_short_ep.py",
        "--arm",
        "--arm",
        "B000",
    ]
    receipt_path.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(M.IntermediateTrendAnalysisError, match="command is malformed"):
        M.analyse_matrix_roots([root], output_dir=tmp_path / "analysis")

    root = _write_matrix(monkeypatch, tmp_path / "second")
    summary = root / "ee-sweep" / "sweep-summary.json"
    payload = json.loads(summary.read_text(encoding="utf-8"))
    payload["summary"][0]["mean_ee_bits_per_j"] = 999.0
    summary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(M.IntermediateTrendAnalysisError, match="artifact hash mismatch"):
        M.analyse_matrix_roots([root], output_dir=tmp_path / "analysis-second")


def test_optional_checkpoint_trend_summary_is_bound_but_not_used_as_final_endpoint(
    monkeypatch, tmp_path
):
    root = _write_matrix(monkeypatch, tmp_path)
    receipt_path = root / "matrix-receipt.json"
    trajectory_path = tmp_path / "checkpoint-trend-summary.json"
    rows = []
    for arm in M.EXPECTED_ARMS:
        for completed in range(
            M.TREND_CHECKPOINT_EVERY_EPISODES,
            3000 + 1,
            M.TREND_CHECKPOINT_EVERY_EPISODES,
        ):
            rows.append(
                {
                    "arm": arm,
                    "arm_label": M.ARM_LABELS[arm],
                    "episodes_completed": completed,
                    "users": M.TREND_USERS,
                    "evaluation_seeds": list(M.EXPECTED_EVALUATION_SEEDS),
                    "useful_bits": 100.0,
                    "system_energy_j": 10.0,
                    "system_ee_bits_per_j": 10.0,
                    "zero_power_intervals": 0,
                    "zero_service_intervals": 0,
                }
            )
    payload = {
        "schema": M.TRAJECTORY_SCHEMA,
        "status": "complete",
        "claim_ceiling": M.TRAJECTORY_CLAIM_CEILING,
        "episodes": 3000,
        "checkpoint_every_episodes": M.TREND_CHECKPOINT_EVERY_EPISODES,
        "training_seed": TRAINING_SEED,
        "users": M.TREND_USERS,
        "evaluation_seeds": list(M.EXPECTED_EVALUATION_SEEDS),
        "evaluation_partition": "TEST",
        "evaluation_policy": "Main-only masked-greedy MODQN",
        "ee_aggregation": "ratio of pooled useful bits to pooled system energy within each arm/checkpoint cell",
        "authority": {
            "prereg_path": str(CANONICAL_PREREG.resolve()),
            "prereg_sha256": _sha(CANONICAL_PREREG),
            "tle_root_path": str((tmp_path / "tle").resolve()),
            "tle_file_set_sha256": M.CANONICAL_TLE_FILE_SET_SHA256,
            "tle_file_count": 1,
        },
        "matrix_receipt": str(receipt_path.resolve()),
        "matrix_receipt_sha256": _sha(receipt_path),
        "summary": rows,
    }
    trajectory_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
    )
    result = M.analyse_matrix_roots(
        [root],
        output_dir=tmp_path / "analysis",
        trajectory_summaries=[trajectory_path],
    )
    assert result["trajectory_summaries"][0]["rows"] == 150
    assert result["matrices"][0]["directional_3000"]["pass"] is True
