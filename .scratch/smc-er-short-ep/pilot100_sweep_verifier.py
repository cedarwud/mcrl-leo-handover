#!/usr/bin/env python3
"""Independent structural and arithmetic verifier for a pilot100 EE sweep."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


SWEEP_SCHEMA = "multi-catfish-mcrl-short-ep-ee-users-sweep-v2"
EVALUATION_POLICY = "Main-only masked-greedy MODQN"
EVALUATION_PARTITION = "test"
EE_AGGREGATION = (
    "per-training-seed ratio-of-sums, then equal-weight training-seed mean"
)
ARM_LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A011": "Full - C1",
    "A101": "Full - C2",
    "A110": "Full - C3",
}
RAW_KEYS = {
    "arm",
    "checkpoint_sha256",
    "training_seed",
    "evaluation_seed",
    "users",
    "steps",
    "duration_s",
    "useful_bits",
    "system_energy_j",
    "system_ee_bits_per_j",
    "mean_system_power_w",
    "mean_system_throughput_bps",
    "served_user_intervals",
    "total_user_intervals",
    "served_fraction",
    "zero_power_intervals",
    "zero_service_intervals",
    "r1_sum",
    "r2_sum",
    "r3_sum",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path, *, label: str, failures: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        failures.append(f"{label}: unreadable ({type(error).__name__})")
        return None


def _finite(raw: Any) -> float | None:
    if isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _close(raw: Any, expected: float) -> bool:
    value = _finite(raw)
    return value is not None and math.isclose(
        value, float(expected), rel_tol=1e-12, abs_tol=1e-8
    )


def _row_key(row: Mapping[str, Any]) -> tuple[str, int, int] | None:
    arm = row.get("arm")
    users = row.get("users")
    seed = row.get("evaluation_seed")
    if not isinstance(arm, str) or type(users) is not int or type(seed) is not int:
        return None
    return arm, users, seed


def verify_pilot100_sweep(
    *,
    output_dir: Path,
    training_seed: int,
    evaluation_users: Sequence[int],
    evaluation_seeds: Sequence[int],
    checkpoints: Mapping[str, Path],
    expected_tle_hash: str,
    expected_tle_count: int,
    expected_prereg_sha256: str,
    expected_episode_index: int,
) -> dict[str, Any]:
    """Fail closed unless every one of the 125 EE cells is reproducible."""

    root = Path(output_dir).expanduser().resolve()
    summary_path = root / "sweep-summary.json"
    raw_path = root / "sweep-raw.json"
    raw_csv = root / "sweep-raw.csv"
    summary_csv = root / "sweep-summary.csv"
    plot_status_path = root / "plot-status.json"
    failures: list[str] = []
    summary = _json(summary_path, label="sweep summary", failures=failures)
    raw = _json(raw_path, label="sweep raw", failures=failures)
    plot_status = _json(
        plot_status_path, label="plot status", failures=failures
    )
    for path, label in ((raw_csv, "sweep raw CSV"), (summary_csv, "sweep summary CSV")):
        if not path.is_file() or path.stat().st_size <= 0:
            failures.append(f"{label}: missing or empty")
    if not isinstance(plot_status, Mapping) or plot_status.get("status") not in {
        "complete",
        "data-complete-plot-dependency-missing",
    }:
        failures.append("plot status: recognised data-complete state required")
    elif plot_status.get("status") == "complete":
        raw_plot = plot_status.get("path")
        try:
            plot_path = Path(str(raw_plot)).expanduser().resolve()
        except (OSError, RuntimeError):
            plot_path = None
        if plot_path is None or not plot_path.is_file() or plot_path.stat().st_size <= 0:
            failures.append("plot status: complete plot path missing or empty")

    expected_labels = [ARM_LABELS[arm] for arm in ARM_LABELS]
    expected_users = [int(value) for value in evaluation_users]
    expected_seeds = [int(value) for value in evaluation_seeds]
    expected_keys = {
        (label, users, seed)
        for label in expected_labels
        for users in expected_users
        for seed in expected_seeds
    }
    expected_count = len(expected_keys)

    checkpoint_by_label: dict[str, dict[str, Any]] = {}
    for arm, label in ARM_LABELS.items():
        path = Path(checkpoints[arm]).expanduser().resolve()
        if not path.is_file():
            failures.append(f"checkpoint missing: {arm}")
            continue
        checkpoint_by_label[label] = {
            "path": path,
            "sha256": sha256_file(path),
        }

    if not isinstance(summary, Mapping):
        failures.append("sweep summary: object required")
    else:
        exact = {
            "schema": SWEEP_SCHEMA,
            "method_family": "Multi-Catfish MCRL",
            "evaluation_policy": EVALUATION_POLICY,
            "evaluation_partition": EVALUATION_PARTITION,
            "ee_aggregation": EE_AGGREGATION,
            "users": expected_users,
            "evaluation_seeds": expected_seeds,
        }
        for field, expected in exact.items():
            if summary.get(field) != expected:
                failures.append(f"sweep summary.{field}: mismatch")
        authority = summary.get("authority")
        if not isinstance(authority, Mapping):
            failures.append("sweep summary.authority: missing")
        else:
            if authority.get("tle_file_set_sha256") != expected_tle_hash:
                failures.append("sweep summary authority TLE hash mismatch")
            if authority.get("tle_file_count") != expected_tle_count:
                failures.append("sweep summary authority TLE count mismatch")
            if authority.get("prereg_sha256") != expected_prereg_sha256:
                failures.append("sweep summary authority prereg hash mismatch")

        checkpoint_rows = summary.get("checkpoints")
        if not isinstance(checkpoint_rows, list) or len(checkpoint_rows) != len(
            expected_labels
        ):
            failures.append("sweep summary: exact five checkpoint rows required")
        else:
            observed_labels = []
            for index, row in enumerate(checkpoint_rows):
                if not isinstance(row, Mapping):
                    failures.append(f"checkpoint row {index}: object required")
                    continue
                label = row.get("arm")
                observed_labels.append(label)
                expected = checkpoint_by_label.get(str(label))
                if expected is None:
                    failures.append(f"checkpoint row {index}: unknown arm")
                    continue
                try:
                    observed_path = Path(str(row.get("path"))).expanduser().resolve()
                except (OSError, RuntimeError):
                    observed_path = None
                if observed_path != expected["path"]:
                    failures.append(f"checkpoint row {label}: path mismatch")
                if row.get("sha256") != expected["sha256"]:
                    failures.append(f"checkpoint row {label}: hash mismatch")
                if row.get("episode") != expected_episode_index:
                    failures.append(f"checkpoint row {label}: episode mismatch")
                if row.get("training_seed") != training_seed:
                    failures.append(f"checkpoint row {label}: training seed mismatch")
                if row.get("checkpoint_kind") != "final-episode-policy":
                    failures.append(f"checkpoint row {label}: kind mismatch")
            if observed_labels != expected_labels:
                failures.append("sweep summary: checkpoint arm order mismatch")

    raw_by_key: dict[tuple[str, int, int], Mapping[str, Any]] = {}
    seen_keys: set[tuple[str, int, int]] = set()
    zero_power_total = 0
    zero_service_total = 0
    if not isinstance(raw, list) or len(raw) != expected_count:
        failures.append(f"sweep raw: exactly {expected_count} rows required")
    if isinstance(raw, list):
        numeric_fields = (
            "duration_s",
            "mean_system_power_w",
            "mean_system_throughput_bps",
            "r1_sum",
            "r2_sum",
            "r3_sum",
            "served_fraction",
            "system_ee_bits_per_j",
            "system_energy_j",
            "useful_bits",
        )
        for index, row in enumerate(raw):
            if not isinstance(row, Mapping):
                failures.append(f"sweep raw row {index}: object required")
                continue
            row_valid = True
            if set(row) != RAW_KEYS:
                failures.append(f"sweep raw row {index}: exact field set required")
                row_valid = False
            key = _row_key(row)
            if key is None or key not in expected_keys:
                failures.append(f"sweep raw row {index}: unexpected cell identity")
                continue
            if key in seen_keys:
                failures.append(f"sweep raw row {index}: duplicate cell {key}")
                continue
            seen_keys.add(key)
            label, users, seed = key
            expected_checkpoint = checkpoint_by_label.get(label)
            if expected_checkpoint is None or row.get("checkpoint_sha256") != expected_checkpoint["sha256"]:
                failures.append(f"sweep raw cell {key}: checkpoint hash mismatch")
            if row.get("training_seed") != training_seed:
                failures.append(f"sweep raw cell {key}: training seed mismatch")
            if seed not in expected_seeds:
                failures.append(f"sweep raw cell {key}: evaluation seed mismatch")
            if any(_finite(row.get(field)) is None for field in numeric_fields):
                failures.append(f"sweep raw cell {key}: non-finite numeric field")
                continue
            duration = float(row["duration_s"])
            bits = float(row["useful_bits"])
            energy = float(row["system_energy_j"])
            if duration <= 0.0 or energy <= 0.0 or bits < 0.0:
                failures.append(f"sweep raw cell {key}: invalid additive totals")
                row_valid = False
            elif not _close(row.get("system_ee_bits_per_j"), bits / energy):
                failures.append(f"sweep raw cell {key}: EE is not ratio-of-sums")
                row_valid = False
            if duration > 0.0:
                if not _close(row.get("mean_system_power_w"), energy / duration):
                    failures.append(f"sweep raw cell {key}: mean power mismatch")
                    row_valid = False
                if not _close(row.get("mean_system_throughput_bps"), bits / duration):
                    failures.append(f"sweep raw cell {key}: mean throughput mismatch")
                    row_valid = False
            steps = row.get("steps")
            total = row.get("total_user_intervals")
            served = row.get("served_user_intervals")
            zero_power = row.get("zero_power_intervals")
            zero_service = row.get("zero_service_intervals")
            if type(steps) is not int or steps != 10:
                failures.append(f"sweep raw cell {key}: exact 10-step rollout required")
                row_valid = False
            elif not _close(duration, steps * 30.08):
                failures.append(f"sweep raw cell {key}: duration mismatch")
                row_valid = False
            elif total != users * steps:
                failures.append(f"sweep raw cell {key}: user interval count mismatch")
                row_valid = False
            if (
                type(total) is not int
                or type(served) is not int
                or served < 0
                or served > total
            ):
                failures.append(f"sweep raw cell {key}: served interval count invalid")
                row_valid = False
            elif total > 0 and not _close(row.get("served_fraction"), served / total):
                failures.append(f"sweep raw cell {key}: served fraction mismatch")
                row_valid = False
            if type(zero_power) is not int or zero_power < 0 or (
                type(steps) is int and zero_power > steps
            ):
                failures.append(f"sweep raw cell {key}: zero-power count invalid")
                row_valid = False
            else:
                zero_power_total += zero_power
            if type(zero_service) is not int or zero_service < 0 or (
                type(steps) is int and zero_service > steps
            ):
                failures.append(f"sweep raw cell {key}: zero-service count invalid")
                row_valid = False
            else:
                zero_service_total += zero_service
            nonnegative_fields = (
                "mean_system_power_w",
                "mean_system_throughput_bps",
                "served_fraction",
                "system_ee_bits_per_j",
            )
            if any(float(row[field]) < 0.0 for field in nonnegative_fields):
                failures.append(f"sweep raw cell {key}: negative physical metric")
                row_valid = False
            if row_valid:
                raw_by_key[key] = row
        missing = expected_keys.difference(seen_keys)
        if missing:
            failures.append(f"sweep raw: {len(missing)} expected cells missing")

    summary_rows = summary.get("summary") if isinstance(summary, Mapping) else None
    expected_summary_keys = {
        (label, users) for label in expected_labels for users in expected_users
    }
    observed_summary: dict[tuple[str, int], Mapping[str, Any]] = {}
    if not isinstance(summary_rows, list) or len(summary_rows) != len(expected_summary_keys):
        failures.append("sweep summary: exactly 25 arm-load rows required")
    if isinstance(summary_rows, list):
        for index, row in enumerate(summary_rows):
            if not isinstance(row, Mapping):
                failures.append(f"summary row {index}: object required")
                continue
            label = row.get("arm")
            users = row.get("users")
            key = (label, users)
            if key not in expected_summary_keys or key in observed_summary:
                failures.append(f"summary row {index}: unexpected or duplicate cell")
                continue
            observed_summary[key] = row
            group = [raw_by_key.get((label, users, seed)) for seed in expected_seeds]
            if any(item is None for item in group):
                failures.append(f"summary cell {key}: raw group incomplete")
                continue
            group_rows = [item for item in group if item is not None]
            bits = math.fsum(float(item["useful_bits"]) for item in group_rows)
            energy = math.fsum(float(item["system_energy_j"]) for item in group_rows)
            duration = math.fsum(float(item["duration_s"]) for item in group_rows)
            served = sum(int(item["served_user_intervals"]) for item in group_rows)
            total = sum(int(item["total_user_intervals"]) for item in group_rows)
            zero_power = sum(int(item["zero_power_intervals"]) for item in group_rows)
            zero_service = sum(int(item["zero_service_intervals"]) for item in group_rows)
            ee = bits / energy
            if row.get("training_seed_count") != 1:
                failures.append(f"summary cell {key}: training seed count mismatch")
            for field in (
                "mean_ee_bits_per_j",
                "median_ee_bits_per_j",
                "min_ee_bits_per_j",
                "max_ee_bits_per_j",
            ):
                if not _close(row.get(field), ee):
                    failures.append(f"summary cell {key}: {field} mismatch")
            seed_rows = row.get("seed_rows")
            if not isinstance(seed_rows, list) or len(seed_rows) != 1 or not isinstance(seed_rows[0], Mapping):
                failures.append(f"summary cell {key}: one seed row required")
                continue
            seed_row = seed_rows[0]
            exact_seed = {
                "arm": label,
                "users": users,
                "training_seed": training_seed,
                "evaluation_seeds": expected_seeds,
                "zero_power_intervals": zero_power,
                "zero_service_intervals": zero_service,
            }
            for field, expected in exact_seed.items():
                if seed_row.get(field) != expected:
                    failures.append(f"summary seed cell {key}: {field} mismatch")
            numeric_expected = {
                "useful_bits": bits,
                "system_energy_j": energy,
                "system_ee_bits_per_j": ee,
                "mean_system_power_w": energy / duration,
                "mean_system_throughput_bps": bits / duration,
                "served_fraction": served / total,
            }
            for field, expected in numeric_expected.items():
                if not _close(seed_row.get(field), expected):
                    failures.append(f"summary seed cell {key}: {field} mismatch")
        missing = expected_summary_keys.difference(observed_summary)
        if missing:
            failures.append(f"sweep summary: {len(missing)} arm-load cells missing")

    return {
        "schema": "multi-catfish-mcrl-pilot100-sweep-verification-v1",
        "status": "PASS" if not failures else "FAIL",
        "expected_raw_rows": expected_count,
        "observed_raw_rows": len(raw) if isinstance(raw, list) else None,
        "expected_summary_rows": len(expected_summary_keys),
        "observed_summary_rows": len(summary_rows) if isinstance(summary_rows, list) else None,
        "zero_power_intervals": zero_power_total,
        "zero_power_data_validity": "PASS",
        "zero_power_longer_run_gate": "PASS" if zero_power_total == 0 else "BLOCKED",
        "zero_service_intervals": zero_service_total,
        "zero_service_policy": "reported-and-arithmetically-checked-not-required-zero",
        "summary_path": str(summary_path),
        "summary_sha256": sha256_file(summary_path) if summary_path.is_file() else None,
        "raw_path": str(raw_path),
        "raw_sha256": sha256_file(raw_path) if raw_path.is_file() else None,
        "failures": failures,
    }


__all__ = ["verify_pilot100_sweep"]
