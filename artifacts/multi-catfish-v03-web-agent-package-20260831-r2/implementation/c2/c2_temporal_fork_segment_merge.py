#!/usr/bin/env python3
"""Fail-closed merger for bounded C2 V0.3 continuation artifacts.

This tool joins already completed, contiguous episode-boundary segments.  It
never averages energy-efficiency ratios: Main EE is recomputed as total useful
bits divided by total joules.  Forecast wall time remains descriptive and is
summed separately from deterministic training/evaluation quantities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Sequence


SCHEMA = "c2-v03-segment-artifact-merge-receipt-v1"
STATUS_SCHEMA = "multi-catfish-c2-v03-episode-loop-v2"
TELEMETRY_SCHEMA = "multi-catfish-c2-v03-run-telemetry-v1"
CLAIM_CEILING = (
    "bounded artifact-history reconstruction only; no EE efficacy, training "
    "trend, Chapter-5 result, or deployment authorization"
)
LIST_ARTIFACTS = (
    "episode-logs.json",
    "c2-training-receipts.json",
    "main-update-receipts.json",
    "c2-option-chronology-audits.json",
)
AUTHORITY_IDENTITY_FIELDS = (
    "prereg_sha256",
    "tle_file_set_sha256",
    "tle_file_count",
)
CHRONOLOGY_TIME_FIELDS = (
    "forecast_started_ns",
    "forecast_completed_ns",
    "live_step_started_ns",
    "live_step_completed_ns",
)


class SegmentMergeError(RuntimeError):
    """A segment or its claimed history is malformed or incompatible."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant {value}")
            ),
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SegmentMergeError(f"cannot read valid JSON artifact {path}: {error}") from error


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SegmentMergeError(f"{field} must be a mapping")
    return value


def _exact_nonnegative_int(value: Any, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise SegmentMergeError(f"{field} must be a nonnegative exact integer")
    return value


def _finite_nonnegative(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SegmentMergeError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise SegmentMergeError(f"{field} must be finite and nonnegative")
    return result


def _finite_numeric(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SegmentMergeError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise SegmentMergeError(f"{field} must be finite")
    return result


def _close(actual: float | None, expected: float | None, *, field: str) -> None:
    if actual is None or expected is None:
        if actual is not expected:
            raise SegmentMergeError(f"{field} disagrees with its denominator")
        return
    actual_number = _finite_numeric(actual, field=field)
    expected_number = _finite_numeric(expected, field=f"{field}.expected")
    if not math.isclose(actual_number, expected_number, rel_tol=1e-12, abs_tol=1e-9):
        raise SegmentMergeError(f"{field} disagrees with its ratio of sums")


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _compare_payloads(left: Any, right: Any, *, field: str) -> None:
    """Compare canonical JSON payloads while tolerating only float summation noise."""

    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left) != set(right):
            raise SegmentMergeError(f"payload keys drifted at {field}")
        for key in sorted(left):
            _compare_payloads(left[key], right[key], field=f"{field}.{key}")
        return
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise SegmentMergeError(f"payload length drifted at {field}")
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            _compare_payloads(left_item, right_item, field=f"{field}[{index}]")
        return
    if isinstance(left, float) or isinstance(right, float):
        left_number = _finite_numeric(left, field=field)
        right_number = _finite_numeric(right, field=f"{field}.expected")
        if not math.isclose(left_number, right_number, rel_tol=1e-12, abs_tol=1e-9):
            raise SegmentMergeError(f"payload disagrees at {field}")
        return
    if left != right:
        raise SegmentMergeError(f"payload disagrees at {field}")


def _chronology_digest(receipt: Mapping[str, Any]) -> str:
    fields = (
        "schema",
        "option_id",
        "anchor_sha256",
        "live_rng_before_sha256",
        "live_rng_after_forecast_sha256",
        "forecast_rng_sha256",
        "forecast_request_sha256",
        "forecast_payload_sha256",
        *CHRONOLOGY_TIME_FIELDS,
        "forecast_sequence",
        "live_rng_unchanged_during_forecast",
        "claim_ceiling",
    )
    if set(receipt) != set(fields):
        raise SegmentMergeError("chronology receipt fields drifted")
    times = tuple(receipt[name] for name in CHRONOLOGY_TIME_FIELDS)
    if any(type(value) is not int or value < 0 for value in times):
        raise SegmentMergeError("chronology timestamps must be nonnegative exact integers")
    if tuple(sorted(times)) != times:
        raise SegmentMergeError("chronology timestamps are out of order")
    if receipt.get("live_rng_unchanged_during_forecast") is not True:
        raise SegmentMergeError("chronology receipt does not prove RNG nonadvancement")
    if receipt.get("live_rng_before_sha256") != receipt.get(
        "live_rng_after_forecast_sha256"
    ):
        raise SegmentMergeError("chronology RNG digests disagree")
    return _canonical_json_sha256({name: receipt[name] for name in fields})


def _clock_excluded_digest(receipt: Mapping[str, Any]) -> str:
    return _canonical_json_sha256(
        {
            name: value
            for name, value in receipt.items()
            if name not in CHRONOLOGY_TIME_FIELDS
        }
    )


def _validate_telemetry(value: Any, *, field: str) -> Mapping[str, Any]:
    telemetry = _mapping(value, field=field)
    if telemetry.get("schema") != TELEMETRY_SCHEMA:
        raise SegmentMergeError(f"{field}.schema drifted")
    claim_ceiling = telemetry.get("claim_ceiling")
    if not isinstance(claim_ceiling, str) or not claim_ceiling:
        raise SegmentMergeError(f"{field}.claim_ceiling must be a nonempty string")
    main = _mapping(telemetry.get("main"), field=f"{field}.main")
    c2 = _mapping(telemetry.get("c2"), field=f"{field}.c2")

    steps = _exact_nonnegative_int(main.get("steps"), field=f"{field}.main.steps")
    useful_bits = _finite_nonnegative(
        main.get("useful_bits"), field=f"{field}.main.useful_bits"
    )
    energy_j = _finite_nonnegative(
        main.get("energy_j"), field=f"{field}.main.energy_j"
    )
    served = _exact_nonnegative_int(
        main.get("served_user_intervals"),
        field=f"{field}.main.served_user_intervals",
    )
    intervals = _exact_nonnegative_int(
        main.get("user_intervals"), field=f"{field}.main.user_intervals"
    )
    if served > intervals:
        raise SegmentMergeError(f"{field}.main served intervals exceed total")
    rewards = main.get("canonical_reward_sum")
    if not isinstance(rewards, list) or len(rewards) != 3:
        raise SegmentMergeError(f"{field}.main.canonical_reward_sum must be length 3")
    for index, reward in enumerate(rewards):
        if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(float(reward)):
            raise SegmentMergeError(
                f"{field}.main.canonical_reward_sum[{index}] must be finite numeric"
            )
    expected_ee = useful_bits / energy_j if energy_j > 0.0 else None
    expected_service = served / intervals if intervals > 0 else None
    _close(
        main.get("ratio_of_sums_ee_bits_per_j"),
        expected_ee,
        field=f"{field}.main.ratio_of_sums_ee_bits_per_j",
    )
    _close(
        main.get("served_fraction"),
        expected_service,
        field=f"{field}.main.served_fraction",
    )

    integer_fields = (
        "schedules",
        "empty_anchor_attempts",
        "scheduled_candidates",
        "options_executed",
        "option_primitive_steps",
        "admitted_options",
        "q2f_updates",
        "joint_commits",
    )
    counts = {
        name: _exact_nonnegative_int(c2.get(name), field=f"{field}.c2.{name}")
        for name in integer_fields
    }
    outcomes = _mapping(
        c2.get("candidate_outcomes"), field=f"{field}.c2.candidate_outcomes"
    )
    choices = _mapping(c2.get("choice_counts"), field=f"{field}.c2.choice_counts")
    outcome_counts = {
        name: _exact_nonnegative_int(
            outcomes.get(name), field=f"{field}.c2.candidate_outcomes.{name}"
        )
        for name in (
            "certificate_pass",
            "certificate_fail",
            "support_rejection",
            "contract_error",
        )
    }
    choice_counts = {
        name: _exact_nonnegative_int(
            choices.get(name), field=f"{field}.c2.choice_counts.{name}"
        )
        for name in ("K0", "K1", "K>=2")
    }
    if sum(outcome_counts.values()) != counts["scheduled_candidates"]:
        raise SegmentMergeError(f"{field}.c2 candidate outcome counts do not close")
    if sum(choice_counts.values()) != counts["schedules"]:
        raise SegmentMergeError(f"{field}.c2 choice counts do not close")
    if counts["scheduled_candidates"] < counts["schedules"]:
        raise SegmentMergeError(f"{field}.c2 candidate count is below schedule count")
    supported_schedules = choice_counts["K1"] + choice_counts["K>=2"]
    if counts["options_executed"] != supported_schedules:
        raise SegmentMergeError(
            f"{field}.c2 option executions disagree with supported schedules"
        )
    if counts["option_primitive_steps"] < counts["options_executed"]:
        raise SegmentMergeError(f"{field}.c2 primitive dose is below option count")
    if not (
        counts["joint_commits"]
        <= counts["q2f_updates"]
        <= counts["admitted_options"]
        <= counts["options_executed"]
    ):
        raise SegmentMergeError(f"{field}.c2 execution-dose counts are inconsistent")
    if counts["options_executed"] > outcome_counts["certificate_pass"]:
        raise SegmentMergeError(f"{field}.c2 executions exceed passed candidates")
    _finite_nonnegative(
        c2.get("forecast_wall_time_s"), field=f"{field}.c2.forecast_wall_time_s"
    )
    expected_rate = counts["joint_commits"] / steps if steps > 0 else None
    _close(
        c2.get("joint_commit_per_main_step"),
        expected_rate,
        field=f"{field}.c2.joint_commit_per_main_step",
    )
    return telemetry


def _merge_telemetries(values: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not values:
        raise SegmentMergeError("at least one telemetry payload is required")
    for index, value in enumerate(values):
        _validate_telemetry(value, field=f"telemetry[{index}]")
    mains = [value["main"] for value in values]
    c2s = [value["c2"] for value in values]
    steps = sum(int(item["steps"]) for item in mains)
    useful_bits = math.fsum(float(item["useful_bits"]) for item in mains)
    energy_j = math.fsum(float(item["energy_j"]) for item in mains)
    served = sum(int(item["served_user_intervals"]) for item in mains)
    intervals = sum(int(item["user_intervals"]) for item in mains)
    rewards = [
        math.fsum(float(item["canonical_reward_sum"][index]) for item in mains)
        for index in range(3)
    ]
    integer_fields = (
        "schedules",
        "empty_anchor_attempts",
        "scheduled_candidates",
        "options_executed",
        "option_primitive_steps",
        "admitted_options",
        "q2f_updates",
        "joint_commits",
    )
    merged_c2 = {
        name: sum(int(item[name]) for item in c2s) for name in integer_fields
    }
    outcomes = {
        name: sum(int(item["candidate_outcomes"][name]) for item in c2s)
        for name in (
            "certificate_pass",
            "certificate_fail",
            "support_rejection",
            "contract_error",
        )
    }
    choices = {
        name: sum(int(item["choice_counts"][name]) for item in c2s)
        for name in ("K0", "K1", "K>=2")
    }
    result = {
        "schema": TELEMETRY_SCHEMA,
        "claim_ceiling": values[0].get("claim_ceiling"),
        "main": {
            "steps": steps,
            "useful_bits": useful_bits,
            "energy_j": energy_j,
            "ratio_of_sums_ee_bits_per_j": (
                useful_bits / energy_j if energy_j > 0.0 else None
            ),
            "served_user_intervals": served,
            "user_intervals": intervals,
            "served_fraction": served / intervals if intervals > 0 else None,
            "canonical_reward_sum": rewards,
        },
        "c2": {
            "schedules": merged_c2["schedules"],
            "empty_anchor_attempts": merged_c2["empty_anchor_attempts"],
            "scheduled_candidates": merged_c2["scheduled_candidates"],
            "candidate_outcomes": outcomes,
            "choice_counts": choices,
            "forecast_wall_time_s": math.fsum(
                float(item["forecast_wall_time_s"]) for item in c2s
            ),
            "options_executed": merged_c2["options_executed"],
            "option_primitive_steps": merged_c2["option_primitive_steps"],
            "admitted_options": merged_c2["admitted_options"],
            "q2f_updates": merged_c2["q2f_updates"],
            "joint_commits": merged_c2["joint_commits"],
            "joint_commit_per_main_step": (
                merged_c2["joint_commits"] / steps if steps > 0 else None
            ),
        },
    }
    _validate_telemetry(result, field="merged_telemetry")
    return result


def _authority_identity(authority: Any, *, field: str) -> dict[str, Any]:
    value = _mapping(authority, field=field)
    missing = [name for name in AUTHORITY_IDENTITY_FIELDS if name not in value]
    if missing:
        raise SegmentMergeError(f"{field} lacks identity fields {missing}")
    prereg = _digest_string(value["prereg_sha256"], field=f"{field}.prereg_sha256")
    tle_set = _digest_string(
        value["tle_file_set_sha256"], field=f"{field}.tle_file_set_sha256"
    )
    count = _exact_nonnegative_int(value["tle_file_count"], field=f"{field}.tle_file_count")
    if count == 0:
        raise SegmentMergeError(f"{field}.tle_file_count must be positive")
    return {
        "prereg_sha256": prereg,
        "tle_file_set_sha256": tle_set,
        "tle_file_count": count,
    }


def _digest_string(value: Any, *, field: str, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SegmentMergeError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _candidate_outcome(row: Mapping[str, Any], *, field: str) -> str:
    _finite_nonnegative(row.get("elapsed_s", 0.0), field=f"{field}.elapsed_s")
    if "contract_error" in row:
        return "contract_error"
    if "support_rejection" in row:
        return "support_rejection"
    if row.get("passed") is True:
        return "certificate_pass"
    if row.get("passed") is False:
        return "certificate_fail"
    raise SegmentMergeError(f"{field} has no classifiable candidate outcome")


def _validate_c2_diagnostics(
    rows: Sequence[Any],
    *,
    expected_steps: set[tuple[int, int]],
    field: str,
) -> tuple[dict[tuple[int, int], Mapping[str, Any]], dict[str, Any]]:
    by_identity: dict[tuple[int, int], Mapping[str, Any]] = {}
    ordered: list[tuple[int, int]] = []
    outcomes = {
        "certificate_pass": 0,
        "certificate_fail": 0,
        "support_rejection": 0,
        "contract_error": 0,
    }
    choices = {"K0": 0, "K1": 0, "K>=2": 0}
    empty = 0
    schedules = 0
    candidates_total = 0
    forecast_wall_time_s = 0.0
    for index, raw in enumerate(rows):
        row = _mapping(raw, field=f"{field}[{index}]")
        identity = (
            _exact_nonnegative_int(row.get("episode"), field=f"{field}[{index}].episode"),
            _exact_nonnegative_int(row.get("step"), field=f"{field}[{index}].step"),
        )
        if identity not in expected_steps:
            raise SegmentMergeError(f"{field}[{index}] lies outside segment steps")
        if identity in by_identity:
            raise SegmentMergeError(f"{field} contains a duplicate identity")
        by_identity[identity] = row
        ordered.append(identity)
        candidates = row.get("candidate_rows")
        if not isinstance(candidates, list):
            raise SegmentMergeError(f"{field}[{index}].candidate_rows must be a list")
        candidate_count = _exact_nonnegative_int(
            row.get("candidate_schedule_size"),
            field=f"{field}[{index}].candidate_schedule_size",
        )
        if candidate_count != len(candidates):
            raise SegmentMergeError(f"{field}[{index}] candidate count drifted")
        _digest_string(
            row.get("candidate_schedule_sha256"),
            field=f"{field}[{index}].candidate_schedule_sha256",
        )
        _digest_string(
            row.get("selection_receipt_sha256"),
            field=f"{field}[{index}].selection_receipt_sha256",
        )
        if not candidates:
            empty += 1
            if row.get("choice_class") != "K0":
                raise SegmentMergeError(f"{field}[{index}] empty schedule is not K0")
            continue
        schedules += 1
        candidates_total += len(candidates)
        local_pass = 0
        for candidate_index, candidate_raw in enumerate(candidates):
            candidate = _mapping(
                candidate_raw,
                field=f"{field}[{index}].candidate_rows[{candidate_index}]",
            )
            outcome = _candidate_outcome(
                candidate,
                field=f"{field}[{index}].candidate_rows[{candidate_index}]",
            )
            outcomes[outcome] += 1
            local_pass += int(outcome == "certificate_pass")
            forecast_wall_time_s += float(candidate.get("elapsed_s", 0.0))
        expected_choice = "K0" if local_pass == 0 else "K1" if local_pass == 1 else "K>=2"
        if row.get("choice_class") != expected_choice:
            raise SegmentMergeError(f"{field}[{index}] choice class drifted")
        choices[expected_choice] += 1
    if ordered != sorted(ordered):
        raise SegmentMergeError(f"{field} is not in absolute episode-step order")
    return by_identity, {
        "schedules": schedules,
        "empty_anchor_attempts": empty,
        "scheduled_candidates": candidates_total,
        "candidate_outcomes": outcomes,
        "choice_counts": choices,
        "forecast_wall_time_s": forecast_wall_time_s,
    }


def _validate_option_audits(
    rows: Sequence[Any],
    *,
    expected_steps: set[tuple[int, int]],
    field: str,
) -> tuple[dict[tuple[int, int], Mapping[str, Any]], int]:
    by_identity: dict[tuple[int, int], Mapping[str, Any]] = {}
    ordered: list[tuple[int, int]] = []
    primitive_steps = 0
    required = {
        "schema",
        "episode",
        "step",
        "audit_available",
        "option_id",
        "bundle_ids",
        "selection_receipt_sha256",
        "chronology_receipt_sha256",
        "chronology_receipt",
        "clock_excluded_identity_sha256",
        "admission_plan_sha256",
        "admission_proof_sha256",
        "transition_sha256",
        "primitive_sequence_sha256",
        "joint_record_sha256",
        "claim_ceiling",
    }
    for index, raw in enumerate(rows):
        row = _mapping(raw, field=f"{field}[{index}]")
        if set(row) != required:
            raise SegmentMergeError(f"{field}[{index}] fields drifted")
        if row.get("schema") != "c2-v03-option-chronology-audit-v1":
            raise SegmentMergeError(f"{field}[{index}].schema drifted")
        if row.get("audit_available") is not True:
            raise SegmentMergeError(f"{field}[{index}] lacks a chronology preimage")
        identity = (
            _exact_nonnegative_int(row.get("episode"), field=f"{field}[{index}].episode"),
            _exact_nonnegative_int(row.get("step"), field=f"{field}[{index}].step"),
        )
        if identity not in expected_steps:
            raise SegmentMergeError(f"{field}[{index}] lies outside segment steps")
        if identity in by_identity:
            raise SegmentMergeError(f"{field} contains a duplicate identity")
        by_identity[identity] = row
        ordered.append(identity)

        option_id = _digest_string(row.get("option_id"), field=f"{field}[{index}].option_id")
        bundle_ids = row.get("bundle_ids")
        if not isinstance(bundle_ids, list) or not bundle_ids:
            raise SegmentMergeError(f"{field}[{index}].bundle_ids must be nonempty")
        if len(bundle_ids) != len(set(bundle_ids)):
            raise SegmentMergeError(f"{field}[{index}].bundle_ids contain duplicates")
        for bundle_index, bundle_id in enumerate(bundle_ids):
            _digest_string(bundle_id, field=f"{field}[{index}].bundle_ids[{bundle_index}]")
        primitive_steps += len(bundle_ids)
        for name in (
            "selection_receipt_sha256",
            "chronology_receipt_sha256",
            "clock_excluded_identity_sha256",
            "transition_sha256",
            "primitive_sequence_sha256",
        ):
            _digest_string(row.get(name), field=f"{field}[{index}].{name}")
        for name in ("admission_plan_sha256", "admission_proof_sha256", "joint_record_sha256"):
            _digest_string(row.get(name), field=f"{field}[{index}].{name}", optional=True)
        chronology = _mapping(
            row.get("chronology_receipt"),
            field=f"{field}[{index}].chronology_receipt",
        )
        if chronology.get("option_id") != option_id:
            raise SegmentMergeError(f"{field}[{index}] chronology option ID drifted")
        if _chronology_digest(chronology) != row.get("chronology_receipt_sha256"):
            raise SegmentMergeError(f"{field}[{index}] chronology digest mismatch")
        if _clock_excluded_digest(chronology) != row.get(
            "clock_excluded_identity_sha256"
        ):
            raise SegmentMergeError(f"{field}[{index}] clock-excluded digest mismatch")
    if ordered != sorted(ordered):
        raise SegmentMergeError(f"{field} is not in absolute episode-step order")
    return by_identity, primitive_steps


def _load_segment(path: Path) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    status_path = root / "status.json"
    status = _mapping(_read_json(status_path), field=f"{root}.status")
    if status.get("status") != "complete":
        raise SegmentMergeError(f"segment is not complete: {root}")
    if status.get("schema") != STATUS_SCHEMA:
        raise SegmentMergeError(f"segment status schema drifted: {root}")
    claim_ceiling = status.get("claim_ceiling")
    if not isinstance(claim_ceiling, str) or not claim_ceiling:
        raise SegmentMergeError(f"segment claim ceiling is malformed: {root}")
    config = dict(_mapping(status.get("config"), field=f"{root}.config"))
    trainer_config = dict(
        _mapping(status.get("trainer_config"), field=f"{root}.trainer_config")
    )
    if "learning_rate" not in trainer_config:
        raise SegmentMergeError(f"{root}.trainer_config lacks learning_rate")
    arm = status.get("arm")
    if not isinstance(arm, str) or config.get("arm") != arm:
        raise SegmentMergeError(f"segment arm and config disagree: {root}")
    total_episodes = _exact_nonnegative_int(
        config.get("episodes"), field=f"{root}.config.episodes"
    )
    if total_episodes == 0:
        raise SegmentMergeError(f"segment config has no episodes: {root}")
    authority_payload = dict(
        _mapping(status.get("authority"), field=f"{root}.authority")
    )
    authority = _authority_identity(authority_payload, field=f"{root}.authority")
    runtime = dict(_mapping(status.get("runtime"), field=f"{root}.runtime"))
    result = _mapping(status.get("result"), field=f"{root}.result")
    if result.get("claim_ceiling") != claim_ceiling:
        raise SegmentMergeError(f"segment result claim ceiling drifted: {root}")
    start = _exact_nonnegative_int(
        result.get("start_episode"), field=f"{root}.result.start_episode"
    )
    end = _exact_nonnegative_int(
        result.get("episodes_completed"), field=f"{root}.result.episodes_completed"
    )
    if end <= start:
        raise SegmentMergeError(f"segment has an empty or reversed episode range: {root}")
    executed = _exact_nonnegative_int(
        result.get("episodes_executed"), field=f"{root}.result.episodes_executed"
    )
    if executed != end - start:
        raise SegmentMergeError(f"segment executed count disagrees with its range: {root}")
    if result.get("episodes") != total_episodes or end > total_episodes:
        raise SegmentMergeError(f"segment range exceeds its configured run: {root}")
    active_sources = result.get("active_sources")
    if (
        not isinstance(active_sources, list)
        or not active_sources
        or any(not isinstance(item, str) for item in active_sources)
        or active_sources != sorted(set(active_sources))
    ):
        raise SegmentMergeError(f"segment active source list is malformed: {root}")
    dispatch = result.get("dispatch")
    if not isinstance(dispatch, str) or not dispatch:
        raise SegmentMergeError(f"segment dispatch is malformed: {root}")

    artifacts: dict[str, list[Any]] = {}
    hashes: dict[str, str] = {"status.json": _sha256_file(status_path)}
    for name in LIST_ARTIFACTS:
        artifact_path = root / name
        value = _read_json(artifact_path)
        if not isinstance(value, list):
            raise SegmentMergeError(f"{root}/{name} must be a JSON list")
        artifacts[name] = value
        hashes[name] = _sha256_file(artifact_path)
    telemetry_path = root / "run-telemetry.json"
    telemetry = _validate_telemetry(
        _read_json(telemetry_path), field=f"{root}.run-telemetry"
    )
    hashes["run-telemetry.json"] = _sha256_file(telemetry_path)
    if result.get("telemetry_sha256") != hashes["run-telemetry.json"]:
        raise SegmentMergeError(f"{root} status telemetry digest drifted")
    _compare_payloads(result.get("telemetry"), telemetry, field=f"{root}.result.telemetry")

    episodes = artifacts["episode-logs.json"]
    expected_episode_ids = list(range(start, end))
    actual_episode_ids: list[int] = []
    for index, raw in enumerate(episodes):
        row = _mapping(raw, field=f"{root}.episode-logs[{index}]")
        actual_episode_ids.append(
            _exact_nonnegative_int(
                row.get("episode"), field=f"{root}.episode-logs[{index}].episode"
            )
        )
    if actual_episode_ids != expected_episode_ids:
        raise SegmentMergeError(f"{root} episode logs are not contiguous and absolute")
    _compare_payloads(
        result.get("episode_rows"), episodes, field=f"{root}.result.episode_rows"
    )

    expected_steps_ordered: list[tuple[int, int]] = []
    episode_telemetries: list[Mapping[str, Any]] = []
    for row in episodes:
        episode = int(row["episode"])
        main_steps = _exact_nonnegative_int(
            row.get("main_steps"), field=f"{root}.episode[{episode}].main_steps"
        )
        if main_steps == 0:
            raise SegmentMergeError(f"{root}.episode[{episode}] has no Main steps")
        c2_steps = _exact_nonnegative_int(
            row.get("c2_environment_steps"),
            field=f"{root}.episode[{episode}].c2_environment_steps",
        )
        if c2_steps != main_steps:
            raise SegmentMergeError(f"{root}.episode[{episode}] C2 clock is incomplete")
        expected_steps_ordered.extend((episode, step) for step in range(main_steps))
        episode_telemetry = _validate_telemetry(
            row.get("telemetry"), field=f"{root}.episode[{episode}].telemetry"
        )
        episode_telemetries.append(episode_telemetry)
        if episode_telemetry["main"]["steps"] != main_steps:
            raise SegmentMergeError(f"{root}.episode[{episode}] Main step count drifted")
        _compare_payloads(
            row.get("main_source_reward_sum"),
            episode_telemetry["main"]["canonical_reward_sum"],
            field=f"{root}.episode[{episode}].main_source_reward_sum",
        )
        for row_name, telemetry_name in (
            ("c2_options", "options_executed"),
            ("c2_admitted_options", "admitted_options"),
            ("c2_updated_options", "q2f_updates"),
        ):
            if _exact_nonnegative_int(
                row.get(row_name), field=f"{root}.episode[{episode}].{row_name}"
            ) != episode_telemetry["c2"][telemetry_name]:
                raise SegmentMergeError(f"{root}.episode[{episode}] {row_name} drifted")
        if row.get("active_sources") != active_sources:
            raise SegmentMergeError(f"{root}.episode[{episode}] active sources drifted")
    expected_steps = set(expected_steps_ordered)

    diagnostics_by_identity, diagnostic_counts = _validate_c2_diagnostics(
        artifacts["c2-training-receipts.json"],
        expected_steps=expected_steps,
        field=f"{root}.c2-training-receipts",
    )
    audits_by_identity, audit_primitive_steps = _validate_option_audits(
        artifacts["c2-option-chronology-audits.json"],
        expected_steps=expected_steps,
        field=f"{root}.c2-option-chronology-audits",
    )
    if result.get("c2_option_chronology_audit_count") != len(audits_by_identity):
        raise SegmentMergeError(f"{root} status chronology audit count drifted")
    if result.get("c2_option_chronology_audit_sha256") != hashes[
        "c2-option-chronology-audits.json"
    ]:
        raise SegmentMergeError(f"{root} status chronology audit digest drifted")
    reported_steps: list[tuple[int, int]] = []
    live_identities: set[tuple[int, int]] = set()
    main_counts = {
        "options_executed": 0,
        "admitted_options": 0,
        "q2f_updates": 0,
        "joint_commits": 0,
    }
    for index, raw in enumerate(artifacts["main-update-receipts.json"]):
        row = _mapping(raw, field=f"{root}.main-update-receipts[{index}]")
        identity = (
            _exact_nonnegative_int(row.get("episode"), field="main receipt episode"),
            _exact_nonnegative_int(row.get("step"), field="main receipt step"),
        )
        reported_steps.append(identity)
        if row.get("main_update_calls") != 1:
            raise SegmentMergeError(f"{root} Main update-call cardinality drifted")
        formal = row.get("formal_c2_owned_main_update")
        if type(formal) is not bool:
            raise SegmentMergeError(f"{root} formal C2 ownership must be Boolean")
        diagnostic = diagnostics_by_identity.get(identity)
        c2_training = row.get("c2_training")
        if diagnostic is None:
            if c2_training is not None:
                raise SegmentMergeError(f"{root} unreported C2 selection at {identity}")
            if formal:
                raise SegmentMergeError(f"{root} C2 owns Main without selection at {identity}")
        else:
            c2 = _mapping(c2_training, field=f"{root}.main[{identity}].c2_training")
            if c2.get("choice_class") != diagnostic.get("choice_class"):
                raise SegmentMergeError(f"{root} C2 choice class drifted at {identity}")
            if c2.get("selection_receipt_sha256") != diagnostic.get(
                "selection_receipt_sha256"
            ):
                raise SegmentMergeError(f"{root} C2 selection hash drifted at {identity}")
            support_count = sum(
                int(
                    _candidate_outcome(
                        _mapping(candidate, field=f"{root}.main[{identity}].candidate"),
                        field=f"{root}.main[{identity}].candidate",
                    )
                    == "certificate_pass"
                )
                for candidate in diagnostic["candidate_rows"]
            )
            if _exact_nonnegative_int(
                c2.get("candidate_count"), field=f"{root}.main[{identity}].candidate_count"
            ) != support_count:
                raise SegmentMergeError(f"{root} C2 support count drifted at {identity}")
            flags: dict[str, bool] = {}
            for name in ("live_committed", "admitted", "updated", "joint_committed"):
                if type(c2.get(name)) is not bool:
                    raise SegmentMergeError(f"{root} C2 {name} must be Boolean at {identity}")
                flags[name] = c2[name]
            if flags["updated"] and not flags["admitted"]:
                raise SegmentMergeError(f"{root} C2 update lacks admission at {identity}")
            if flags["joint_committed"] and not flags["updated"]:
                raise SegmentMergeError(f"{root} joint commit lacks Q2F update at {identity}")
            if formal != flags["joint_committed"]:
                raise SegmentMergeError(f"{root} Main ownership disagrees at {identity}")
            if flags["live_committed"]:
                audit = audits_by_identity.get(identity)
                if audit is None:
                    raise SegmentMergeError(f"{root} live C2 option lacks audit at {identity}")
                live_identities.add(identity)
                if c2.get("selected_option_id") != audit.get("option_id"):
                    raise SegmentMergeError(f"{root} option ID drifted at {identity}")
                for c2_name, audit_name in (
                    ("selection_receipt_sha256", "selection_receipt_sha256"),
                    ("primitive_sequence_sha256", "primitive_sequence_sha256"),
                    ("transition_sha256", "transition_sha256"),
                    ("joint_record_sha256", "joint_record_sha256"),
                ):
                    if c2.get(c2_name) != audit.get(audit_name):
                        raise SegmentMergeError(f"{root} {c2_name} drifted at {identity}")
            elif identity in audits_by_identity:
                raise SegmentMergeError(f"{root} nonexecuted C2 selection has an audit")
            main_counts["options_executed"] += int(flags["live_committed"])
            main_counts["admitted_options"] += int(flags["admitted"])
            main_counts["q2f_updates"] += int(flags["updated"])
            main_counts["joint_commits"] += int(flags["joint_committed"])
        if formal:
            if row.get("main_carrier") is not None:
                raise SegmentMergeError(f"{root} double-owns the Main update at {identity}")
        else:
            _mapping(row.get("main_carrier"), field=f"{root}.main[{identity}].main_carrier")

    if reported_steps != expected_steps_ordered:
        raise SegmentMergeError(f"{root} Main receipt chronology or coverage drifted")
    if set(audits_by_identity) != live_identities:
        raise SegmentMergeError(f"{root} option audit coverage drifted")
    c2_telemetry = telemetry["c2"]
    for name, value in diagnostic_counts.items():
        _compare_payloads(c2_telemetry[name], value, field=f"{root}.c2.{name}")
    for name, value in main_counts.items():
        if c2_telemetry[name] != value:
            raise SegmentMergeError(f"{root}.c2.{name} disagrees with Main receipts")
    if c2_telemetry["option_primitive_steps"] != audit_primitive_steps:
        raise SegmentMergeError(f"{root}.c2.option_primitive_steps disagrees with audits")

    reconstructed = _merge_telemetries(episode_telemetries)
    _compare_payloads(telemetry, reconstructed, field=f"{root}.run-telemetry")
    periodic = result.get("periodic_checkpoints")
    if not isinstance(periodic, list) or result.get("periodic_checkpoint_count") != len(periodic):
        raise SegmentMergeError(f"{root} periodic checkpoint count drifted")

    return {
        "root": root,
        "start": start,
        "end": end,
        "arm": arm,
        "dispatch": dispatch,
        "active_sources": active_sources,
        "config": config,
        "trainer_config": trainer_config,
        "authority": authority,
        "authority_payload": authority_payload,
        "runtime": runtime,
        "claim_ceiling": claim_ceiling,
        "artifacts": artifacts,
        "telemetry": telemetry,
        "hashes": hashes,
    }


def merge_segments(segment_dirs: Sequence[Path], output_dir: Path) -> dict[str, Any]:
    if not segment_dirs:
        raise SegmentMergeError("at least one segment directory is required")
    output = Path(output_dir).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite merge output: {output}")
    segments = [_load_segment(Path(path)) for path in segment_dirs]
    first_config = segments[0]["config"]
    first_authority = segments[0]["authority"]
    compatibility_fields = (
        "arm",
        "dispatch",
        "active_sources",
        "trainer_config",
        "runtime",
        "claim_ceiling",
    )
    expected_start = segments[0]["start"]
    for index, segment in enumerate(segments):
        if segment["config"] != first_config:
            raise SegmentMergeError(f"segment[{index}] config differs")
        if segment["authority"] != first_authority:
            raise SegmentMergeError(f"segment[{index}] authority differs")
        for name in compatibility_fields:
            if segment[name] != segments[0][name]:
                raise SegmentMergeError(f"segment[{index}] {name} differs")
        if segment["start"] != expected_start:
            relation = "overlap" if segment["start"] < expected_start else "gap"
            raise SegmentMergeError(f"segment[{index}] creates an episode {relation}")
        expected_start = segment["end"]

    merged_lists = {
        name: [item for segment in segments for item in segment["artifacts"][name]]
        for name in LIST_ARTIFACTS
    }
    merged_telemetry = _merge_telemetries(
        [segment["telemetry"] for segment in segments]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )
    try:
        output_hashes: dict[str, str] = {}
        for name, value in merged_lists.items():
            path = staging / name
            _write_json(path, value)
            output_hashes[name] = _sha256_file(path)
        telemetry_path = staging / "run-telemetry.json"
        _write_json(telemetry_path, merged_telemetry)
        output_hashes["run-telemetry.json"] = _sha256_file(telemetry_path)

        receipt = {
            "schema": SCHEMA,
            "status": "PASS",
            "claim_ceiling": CLAIM_CEILING,
            "source_claim_ceiling": segments[0]["claim_ceiling"],
            "episode_range": {
                "start_episode": segments[0]["start"],
                "episodes_completed": segments[-1]["end"],
                "episode_count": segments[-1]["end"] - segments[0]["start"],
            },
            "config": first_config,
            "runtime": segments[0]["runtime"],
            "arm": segments[0]["arm"],
            "dispatch": segments[0]["dispatch"],
            "active_sources": segments[0]["active_sources"],
            "authority_identity": first_authority,
            "authority_locator_policy": (
                "prereg_path and tle_root_path are recorded per source but are host "
                "locators, not frozen-byte identity"
            ),
            "source_segments": [
                {
                    "path": str(segment["root"]),
                    "start_episode": segment["start"],
                    "episodes_completed": segment["end"],
                    "authority": segment["authority_payload"],
                    "artifact_sha256": segment["hashes"],
                }
                for segment in segments
            ],
            "merged_artifact_sha256": output_hashes,
            "telemetry_rule": (
                "sum useful_bits and energy_j, then recompute EE as sum(bits)/sum(joules); "
                "never average segment EE ratios"
            ),
            "receipt_digest_policy": (
                "receipt_path and receipt_sha256 are returned out of band to avoid a "
                "self-referential digest"
            ),
        }
        _write_json(staging / "merge-receipt.json", receipt)
        if output.exists():
            raise FileExistsError(f"refusing to overwrite merge output: {output}")
        os.rename(staging, output)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    receipt_path = output / "merge-receipt.json"
    receipt["receipt_path"] = str(receipt_path)
    receipt["receipt_sha256"] = _sha256_file(receipt_path)
    return receipt


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--segments", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    result = merge_segments(args.segments, args.output_dir)
    print(result["receipt_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
