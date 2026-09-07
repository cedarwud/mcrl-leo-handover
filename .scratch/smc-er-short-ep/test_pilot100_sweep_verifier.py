from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pilot100_sweep_verifier", HERE / "pilot100_sweep_verifier.py"
)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)


TRAINING_SEED = 2026082911
EVALUATION_USERS = (60, 80, 100, 120, 140)
EVALUATION_SEEDS = (2026082914, 2026082915, 2026082916, 2026082917, 2026082918)
TLE_SHA256 = "a" * 64
PREREG_SHA256 = "b" * 64


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _sweep_fixture(tmp_path: Path) -> dict[str, object]:
    output = tmp_path / "ee-sweep"
    output.mkdir()
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    checkpoints: dict[str, Path] = {}
    checkpoint_rows: list[dict[str, object]] = []
    raw: list[dict[str, object]] = []

    for arm_index, (arm, label) in enumerate(V.ARM_LABELS.items(), start=1):
        checkpoint = checkpoint_root / f"{arm}.pt"
        checkpoint.write_bytes(f"checkpoint-{arm}".encode("ascii"))
        checkpoints[arm] = checkpoint
        checkpoint_sha = V.sha256_file(checkpoint)
        checkpoint_rows.append(
            {
                "arm": label,
                "path": str(checkpoint.resolve()),
                "sha256": checkpoint_sha,
                "episode": 99,
                "training_seed": TRAINING_SEED,
                "checkpoint_kind": "final-episode-policy",
            }
        )
        for users in EVALUATION_USERS:
            for seed_index, evaluation_seed in enumerate(EVALUATION_SEEDS, start=1):
                duration = 300.8
                useful_bits = float(users * 1_000_000 + seed_index * 10_000 + arm_index)
                system_energy_j = float(1_000 + users + seed_index + arm_index)
                total = users * 10
                served = total - seed_index
                raw.append(
                    {
                        "arm": label,
                        "checkpoint_sha256": checkpoint_sha,
                        "training_seed": TRAINING_SEED,
                        "evaluation_seed": evaluation_seed,
                        "users": users,
                        "steps": 10,
                        "duration_s": duration,
                        "useful_bits": useful_bits,
                        "system_energy_j": system_energy_j,
                        "system_ee_bits_per_j": useful_bits / system_energy_j,
                        "mean_system_power_w": system_energy_j / duration,
                        "mean_system_throughput_bps": useful_bits / duration,
                        "served_user_intervals": served,
                        "total_user_intervals": total,
                        "served_fraction": served / total,
                        "zero_power_intervals": 0,
                        "zero_service_intervals": 0,
                        "r1_sum": useful_bits / 1_000.0,
                        "r2_sum": -float(seed_index),
                        "r3_sum": -float(users),
                    }
                )

    summary_rows: list[dict[str, object]] = []
    for _arm, label in V.ARM_LABELS.items():
        for users in EVALUATION_USERS:
            group = [
                row for row in raw if row["arm"] == label and row["users"] == users
            ]
            bits = math.fsum(float(row["useful_bits"]) for row in group)
            energy = math.fsum(float(row["system_energy_j"]) for row in group)
            duration = math.fsum(float(row["duration_s"]) for row in group)
            served = sum(int(row["served_user_intervals"]) for row in group)
            total = sum(int(row["total_user_intervals"]) for row in group)
            ee = bits / energy
            seed_row = {
                "arm": label,
                "users": users,
                "training_seed": TRAINING_SEED,
                "evaluation_seeds": list(EVALUATION_SEEDS),
                "useful_bits": bits,
                "system_energy_j": energy,
                "system_ee_bits_per_j": ee,
                "mean_system_power_w": energy / duration,
                "mean_system_throughput_bps": bits / duration,
                "served_fraction": served / total,
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

    summary = {
        "schema": V.SWEEP_SCHEMA,
        "method_family": "Multi-Catfish MCRL",
        "evaluation_policy": V.EVALUATION_POLICY,
        "evaluation_partition": V.EVALUATION_PARTITION,
        "ee_aggregation": V.EE_AGGREGATION,
        "users": list(EVALUATION_USERS),
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "authority": {
            "tle_file_set_sha256": TLE_SHA256,
            "tle_file_count": 373,
            "prereg_sha256": PREREG_SHA256,
        },
        "checkpoints": checkpoint_rows,
        "summary": summary_rows,
    }
    _write_json(output / "sweep-raw.json", raw)
    _write_json(output / "sweep-summary.json", summary)
    _write_json(
        output / "plot-status.json",
        {"status": "data-complete-plot-dependency-missing", "path": None},
    )
    (output / "sweep-raw.csv").write_text("header\n", encoding="utf-8")
    (output / "sweep-summary.csv").write_text("header\n", encoding="utf-8")
    return {
        "output_dir": output,
        "training_seed": TRAINING_SEED,
        "evaluation_users": EVALUATION_USERS,
        "evaluation_seeds": EVALUATION_SEEDS,
        "checkpoints": checkpoints,
        "expected_tle_hash": TLE_SHA256,
        "expected_tle_count": 373,
        "expected_prereg_sha256": PREREG_SHA256,
        "expected_episode_index": 99,
    }


def _mutate_raw(output_dir: Path, mutation: str) -> None:
    path = output_dir / "sweep-raw.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "empty":
        raw = []
    elif mutation == "malformed":
        raw = {"not": "a row list"}
    elif mutation == "missing_field":
        del raw[0]["useful_bits"]
    elif mutation == "nonfinite":
        raw[0]["useful_bits"] = float("nan")
    elif mutation == "duplicate":
        raw[-1] = dict(raw[0])
    elif mutation == "ratio_mismatch":
        raw[0]["system_ee_bits_per_j"] *= 2.0
    else:  # pragma: no cover - test helper guard
        raise AssertionError(mutation)
    _write_json(path, raw)


def test_complete_125_row_sweep_passes(tmp_path):
    arguments = _sweep_fixture(tmp_path)

    receipt = V.verify_pilot100_sweep(**arguments)

    assert receipt["status"] == "PASS"
    assert receipt["expected_raw_rows"] == receipt["observed_raw_rows"] == 125
    assert receipt["expected_summary_rows"] == receipt["observed_summary_rows"] == 25
    assert receipt["zero_power_longer_run_gate"] == "PASS"
    assert receipt["failures"] == []


@pytest.mark.parametrize(
    "mutation,needle",
    [
        ("empty", "exactly 125 rows"),
        ("malformed", "exactly 125 rows"),
        ("missing_field", "exact field set"),
        ("nonfinite", "non-finite numeric field"),
        ("duplicate", "duplicate cell"),
        ("ratio_mismatch", "EE is not ratio-of-sums"),
    ],
)
def test_bad_sweep_data_returns_fail_without_raising(tmp_path, mutation, needle):
    arguments = _sweep_fixture(tmp_path)
    _mutate_raw(Path(arguments["output_dir"]), mutation)

    receipt = V.verify_pilot100_sweep(**arguments)

    assert receipt["status"] == "FAIL"
    assert any(needle in failure for failure in receipt["failures"])

