#!/usr/bin/env python3
"""Evaluate one LR's admitted R7 EP500 B000/F111 prefixes on held-out TEST."""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from dataclasses import asdict, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LEGACY_DIR = REPO / ".scratch" / "smc-er-short-ep"
for path in (HERE, LEGACY_DIR, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r7_500_authority as authority  # noqa: E402
import r7_500_checkpoint as checkpoint_tools  # noqa: E402
import r7_500_output as output_tools  # noqa: E402
import r7_500_prefix_bridge as bridge  # noqa: E402
import r7_500_prefix_reconcile as reconcile  # noqa: E402
import r7_500_server_preflight as preflight  # noqa: E402
import sweep_evaluation as sweep  # noqa: E402
from mcrl.artifacts import read_checkpoint  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-prefix-evaluation-v4"
RAW_SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-prefix-evaluation-raw-v1"
RECEIPT_SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-prefix-evaluation-receipt-v4"
ARM_LABELS = {
    "B000": "Baseline MODQN",
    "F111": "Full Multi-Catfish MCRL",
    "A101": "Full minus C2 (A101)",
    "A011": "Full minus C1 (A011)",
    "A110": "Full minus C3 (A110)",
}
ROUTING_LABELS = {arm: ARM_LABELS[arm] for arm in authority.PREFIX_ARMS}


class R7500EvaluationError(RuntimeError):
    """Raised when an evaluation input is not bound to the R7 prefix bridge."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise R7500EvaluationError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise R7500EvaluationError(f"{label} must be a JSON object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def _lr_key(learning_rate: float) -> str:
    for value in authority.ALLOWED_LEARNING_RATES:
        if math.isclose(float(learning_rate), value, rel_tol=0.0, abs_tol=1e-15):
            return str(value)
    raise R7500EvaluationError("learning rate must be exactly 0.001 or 0.01")


def _assert_exact_global_prefix_grid(
    rows: Any, *, label: str
) -> list[Mapping[str, Any]]:
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise R7500EvaluationError(f"{label} grid is missing or malformed")
    observed: list[tuple[float, str]] = []
    try:
        for row in rows:
            learning_rate = row.get("learning_rate")
            if isinstance(learning_rate, bool):
                raise ValueError
            observed.append((float(learning_rate), str(row.get("arm"))))
    except (TypeError, ValueError, OverflowError) as error:
        raise R7500EvaluationError(f"{label} grid identity is malformed") from error
    expected = [
        (learning_rate, arm)
        for learning_rate in authority.ALLOWED_LEARNING_RATES
        for arm in authority.BRIDGED_ARMS
    ]
    if observed != expected:
        raise R7500EvaluationError(
            f"{label} must contain the exact ordered 2-LR x 5-arm grid"
        )
    return rows


def validate_evaluation_rows(
    rows: Sequence[Mapping[str, Any]], *, expected_count: int
) -> None:
    if len(rows) != expected_count:
        raise R7500EvaluationError("R7 evaluation raw grid is incomplete")
    for row in rows:
        if int(row.get("zero_power_intervals", -1)) != 0:
            raise R7500EvaluationError("R7 evaluation contains zero-power intervals")
        useful_bits = row.get("useful_bits")
        if (
            isinstance(useful_bits, bool)
            or not isinstance(useful_bits, (int, float))
            or not math.isfinite(float(useful_bits))
            or float(useful_bits) <= 0.0
        ):
            raise R7500EvaluationError(
                "R7 evaluation contains an all-zero-service evaluation episode"
            )
        zero_service = row.get("zero_service_intervals")
        if type(zero_service) is not int or zero_service < 0:
            raise R7500EvaluationError("R7 zero-service interval receipt is invalid")


def recompute_serialized_evaluation_rows(
    rows: Any,
    *,
    ordered_labels: Sequence[str],
    checkpoint_bindings: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Independently rebuild a serialized evaluation grid and pooled summary."""

    labels = list(ordered_labels)
    if not labels or len(set(labels)) != len(labels):
        raise R7500EvaluationError("serialized evaluation labels are invalid")
    if (
        len(checkpoint_bindings) != len(labels)
        or any(not isinstance(row, Mapping) for row in checkpoint_bindings)
        or [str(row.get("label")) for row in checkpoint_bindings] != labels
    ):
        raise R7500EvaluationError("serialized checkpoint bindings are incomplete")
    checkpoint_by_label = {
        str(row["label"]): str(row["sha256"]) for row in checkpoint_bindings
    }
    expected_count = len(labels) * len(authority.EVALUATION_USERS) * len(
        authority.EVALUATION_SEEDS
    )
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise R7500EvaluationError("serialized evaluation raw grid is incomplete")
    expected_fields = {field.name for field in fields(sweep.EpisodeTotals)}
    integer_fields = {
        "training_seed",
        "evaluation_seed",
        "users",
        "steps",
        "served_user_intervals",
        "total_user_intervals",
        "zero_power_intervals",
        "zero_service_intervals",
    }
    numeric_fields = expected_fields - integer_fields - {"arm", "checkpoint_sha256"}
    expected_grid = [
        (label, users, seed)
        for label in labels
        for users in authority.EVALUATION_USERS
        for seed in authority.EVALUATION_SEEDS
    ]
    observed_grid: list[tuple[str, int, int]] = []
    materialized = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != expected_fields:
            raise R7500EvaluationError("serialized evaluation row fields drifted")
        for name in integer_fields:
            if type(row.get(name)) is not int:
                raise R7500EvaluationError(
                    f"serialized row {index} {name} is not an integer"
                )
        for name in numeric_fields:
            value = row.get(name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise R7500EvaluationError(
                    f"serialized row {index} {name} is not finite"
                )
        label = str(row["arm"])
        observed_grid.append(
            (label, int(row["users"]), int(row["evaluation_seed"]))
        )
        if row.get("checkpoint_sha256") != checkpoint_by_label.get(label):
            raise R7500EvaluationError("serialized checkpoint SHA binding drifted")
        if row.get("training_seed") != authority.TRAINING_SEEDS["training"]:
            raise R7500EvaluationError("serialized training seed drifted")
        duration = float(row["duration_s"])
        useful_bits = float(row["useful_bits"])
        energy = float(row["system_energy_j"])
        steps = int(row["steps"])
        total_intervals = int(row["total_user_intervals"])
        served_intervals = int(row["served_user_intervals"])
        zero_service = int(row["zero_service_intervals"])
        if (
            steps <= 0
            or duration <= 0.0
            or useful_bits <= 0.0
            or energy <= 0.0
            or total_intervals <= 0
            or not 0 <= served_intervals <= total_intervals
            or not 0 <= zero_service <= steps
            or not 0.0 <= float(row["served_fraction"]) <= 1.0
            or not math.isclose(
                float(row["system_ee_bits_per_j"]),
                useful_bits / energy,
                rel_tol=1e-12,
                abs_tol=0.0,
            )
            or not math.isclose(
                float(row["mean_system_power_w"]),
                energy / duration,
                rel_tol=1e-12,
                abs_tol=0.0,
            )
            or not math.isclose(
                float(row["mean_system_throughput_bps"]),
                useful_bits / duration,
                rel_tol=1e-12,
                abs_tol=0.0,
            )
            or not math.isclose(
                float(row["served_fraction"]),
                served_intervals / total_intervals,
                rel_tol=1e-12,
                abs_tol=0.0,
            )
        ):
            raise R7500EvaluationError(
                "serialized evaluation physical invariants failed"
            )
        try:
            materialized.append(sweep.EpisodeTotals(**dict(row)))
        except (TypeError, ValueError) as error:
            raise R7500EvaluationError(
                "serialized evaluation row cannot be reconstructed"
            ) from error
    if observed_grid != expected_grid:
        raise R7500EvaluationError(
            "serialized evaluation grid is incomplete or reordered"
        )
    validate_evaluation_rows(rows, expected_count=expected_count)
    recomputed = sweep.aggregate_rows(materialized)
    if len(recomputed) != len(labels) * len(authority.EVALUATION_USERS):
        raise R7500EvaluationError("serialized pooled summary grid is incomplete")
    return recomputed


def _load_inputs(
    *,
    authority_path: Path,
    bridge_receipt_path: Path,
    reconciliation_receipt_path: Path,
    learning_rate: float,
    tle_root: Path,
    repo: Path,
    selected_arms: Sequence[str] = authority.PREFIX_ARMS,
) -> tuple[
    dict[str, Any], str, Mapping[str, Any], Mapping[str, Any], list[dict[str, Any]]
]:
    validated, authority_sha = bridge.load_and_validate_authority(
        authority_path, repo=repo, tle_root=tle_root
    )
    receipt_path = Path(bridge_receipt_path).expanduser().resolve()
    expected_bridge_path = (repo / validated["bridge_output"] / "prefix-bridge-receipt.json").resolve()
    if receipt_path != expected_bridge_path:
        raise R7500EvaluationError("prefix bridge receipt path drifted")
    if (receipt_path.parent / output_tools.INCOMPLETE_MARKER).exists():
        raise R7500EvaluationError("prefix bridge publication is incomplete")
    bridge_sha_before = authority.sha256_file(receipt_path)
    receipt = _read_object(receipt_path, label="prefix bridge receipt")
    bridge_sha = authority.sha256_file(receipt_path)
    if bridge_sha != bridge_sha_before:
        raise R7500EvaluationError("prefix bridge receipt changed while being read")
    if (
        receipt.get("schema") != bridge.SCHEMA
        or receipt.get("status") != "PASS"
        or receipt.get("claim_ceiling") != authority.CLAIM_CEILING
        or receipt.get("required_labels") != authority.REQUIRED_LABELS
        or receipt.get("endpoint_episodes") != 500
        or receipt.get("prefix_arms") != list(authority.PREFIX_ARMS)
        or receipt.get("bridged_arms") != list(authority.BRIDGED_ARMS)
        or receipt.get("learning_rates") != list(authority.ALLOWED_LEARNING_RATES)
        or receipt.get("outcome_bearing_source_status_parsed_by_whitelist_extractor")
        is not True
        or receipt.get("outcome_metric_fields_copied") is not False
        or receipt.get("outcome_metric_fields_emitted") is not False
        or receipt.get("outcome_metric_fields_used_for_admission") is not False
        or receipt.get("outcome_metric_fields_admitted") is not False
        or receipt.get("checkpoint_selection_performed") is not False
        or receipt.get("evaluation_authorized") is not False
        or receipt.get("routing_authorized") is not False
        or receipt.get("reconciliation_required") is not True
    ):
        raise R7500EvaluationError("prefix bridge receipt is not admissible")
    bridge_authority = receipt.get("authority")
    if (
        not isinstance(bridge_authority, Mapping)
        or bridge_authority.get("sha256") != authority_sha
        or bridge_authority.get("pin_map_sha256") != validated["pin_map_sha256"]
    ):
        raise R7500EvaluationError("prefix bridge authority identity drifted")
    bridge_root = receipt_path.parent
    authority_snapshot = (
        bridge_root / str(bridge_authority.get("snapshot"))
    ).resolve()
    if (
        not authority_snapshot.is_relative_to(bridge_root)
        or not authority_snapshot.is_file()
        or authority.sha256_file(authority_snapshot) != authority_sha
    ):
        raise R7500EvaluationError("prefix bridge authority snapshot drifted")
    reconciliation_path = Path(reconciliation_receipt_path).expanduser().resolve()
    if reconciliation_path != (repo / validated["reconciliation_receipt"]).resolve():
        raise R7500EvaluationError("prefix reconciliation receipt path drifted")
    reconciliation_sha_before = authority.sha256_file(reconciliation_path)
    reconciliation = _read_object(reconciliation_path, label="prefix reconciliation receipt")
    reconciliation_sha = authority.sha256_file(reconciliation_path)
    if reconciliation_sha != reconciliation_sha_before:
        raise R7500EvaluationError("prefix reconciliation receipt changed while being read")
    reconciliation_bridge = reconciliation.get("bridge_receipt")
    if (
        reconciliation.get("schema") != reconcile.SCHEMA
        or reconciliation.get("status") != "PASS"
        or reconciliation.get("claim_ceiling") != authority.CLAIM_CEILING
        or reconciliation.get("required_labels") != authority.REQUIRED_LABELS
        or reconciliation.get("authority_sha256") != authority_sha
        or reconciliation.get("evaluation_authorized") is not True
        or reconciliation.get("routing_authorized") is not True
        or reconciliation.get("routing_arms") != list(authority.PREFIX_ARMS)
        or reconciliation.get("bridged_arms") != list(authority.BRIDGED_ARMS)
        or reconciliation.get("outcome_bearing_source_status_parsed_by_whitelist_extractor")
        is not True
        or reconciliation.get("outcome_metric_fields_copied") is not False
        or reconciliation.get("outcome_metric_fields_emitted") is not False
        or reconciliation.get("outcome_metric_fields_used_for_admission") is not False
        or reconciliation.get("outcome_metric_fields_admitted") is not False
        or reconciliation.get("selected_lr_ablation_reveal_authorized") is not False
        or reconciliation.get(
            "selected_lr_ablation_reveal_eligible_after_valid_selection"
        )
        is not True
        or reconciliation.get("new_r7_training_authorized") is not False
        or not isinstance(reconciliation_bridge, Mapping)
        or Path(str(reconciliation_bridge.get("path"))).expanduser().resolve() != receipt_path
        or reconciliation_bridge.get("sha256") != bridge_sha
    ):
        raise R7500EvaluationError("prefix reconciliation receipt is not admissible")
    lr_key = _lr_key(learning_rate)
    selected_arm_list = list(selected_arms)
    if (
        not selected_arm_list
        or len(set(selected_arm_list)) != len(selected_arm_list)
        or any(arm not in authority.BRIDGED_ARMS for arm in selected_arm_list)
    ):
        raise R7500EvaluationError("requested bridge arm set is not admissible")
    rows = _assert_exact_global_prefix_grid(
        receipt.get("prefixes"), label="prefix bridge"
    )
    selected = [
        dict(row)
        for row in rows
        if isinstance(row, Mapping)
        and row.get("arm") in selected_arm_list
        and math.isclose(
            float(row.get("learning_rate", float("nan"))),
            float(lr_key),
            rel_tol=0.0,
            abs_tol=1e-15,
        )
    ]
    selected.sort(key=lambda row: selected_arm_list.index(str(row.get("arm"))))
    if [row.get("arm") for row in selected] != selected_arm_list:
        raise R7500EvaluationError("bridge lacks the exact requested LR prefix set")
    reconciled_rows = _assert_exact_global_prefix_grid(
        reconciliation.get("prefixes"), label="prefix reconciliation"
    )
    materialized: list[dict[str, Any]] = []
    for row in selected:
        checkpoint = row.get("checkpoint")
        if not isinstance(checkpoint, Mapping):
            raise R7500EvaluationError("bridge checkpoint row is malformed")
        path = (bridge_root / str(checkpoint.get("snapshot"))).resolve()
        if not path.is_relative_to(bridge_root) or not path.is_file():
            raise R7500EvaluationError("bridge checkpoint snapshot is missing")
        artifact_sha = authority.sha256_file(path)
        if checkpoint.get("artifact_sha256") != artifact_sha:
            raise R7500EvaluationError("bridge checkpoint snapshot SHA drifted")
        run = row.get("run")
        journal_path = (
            bridge_root / str(run.get("journal_snapshot"))
            if isinstance(run, Mapping)
            else Path()
        ).resolve()
        if not journal_path.is_relative_to(bridge_root) or not journal_path.is_file():
            raise R7500EvaluationError("bridge run journal snapshot is missing")
        journal = _read_object(journal_path, label="bridge run journal snapshot")
        trainer_config = journal.get("trainer_config")
        if not isinstance(trainer_config, Mapping):
            raise R7500EvaluationError("bridge trainer config is missing")
        payload = read_checkpoint(path, map_location="cpu")
        try:
            identity = checkpoint_tools.validate_checkpoint_payload(
                payload,
                validated=validated["validated_base_authorities"][lr_key],
                trainer_config=trainer_config,
                episode_index=499,
                checkpoint_kind="periodic-main-policy-trend",
                label=f"lr={lr_key} {row['arm']} EP500 evaluation input",
            )
        except Exception as error:
            raise R7500EvaluationError("bridge checkpoint identity drifted") from error
        reconciled = [
            candidate
            for candidate in reconciled_rows
            if isinstance(candidate, Mapping)
            and candidate.get("arm") == row.get("arm")
            and math.isclose(
                float(candidate.get("learning_rate", float("nan"))),
                float(lr_key),
                rel_tol=0.0,
                abs_tol=1e-15,
            )
        ]
        if (
            len(reconciled) != 1
            or reconciled[0].get("artifact_sha256") != artifact_sha
            or reconciled[0].get("online_policy_sha256") != identity["online_policy_sha256"]
            or checkpoint.get("online_policy_sha256") != identity["online_policy_sha256"]
        ):
            raise R7500EvaluationError("reconciled checkpoint binding drifted")
        materialized.append(
            {
                "arm": str(row["arm"]),
                "label": ARM_LABELS[str(row["arm"])],
                "path": path,
                "sha256": artifact_sha,
                "payload": payload,
                "source_status": row.get("source_status"),
                "online_policy_sha256": identity["online_policy_sha256"],
            }
        )
    return validated, authority_sha, receipt, reconciliation, materialized


def write_svg_plot(
    path: Path,
    summary: Sequence[Mapping[str, Any]],
    *,
    learning_rate: float,
    title: str,
    labels: Sequence[str],
    footer_labels: Sequence[str] | None = None,
) -> None:
    """Write a deterministic dependency-free EE/load plot as SVG."""

    width, height = 1200, 560
    left, right, top, bottom = 105.0, 310.0, 78.0, 92.0
    plot_width = width - left - right
    plot_height = height - top - bottom
    users = list(authority.EVALUATION_USERS)
    indexed = {
        (str(row["arm"]), int(row["users"])): float(row["mean_ee_bits_per_j"]) / 1e6
        for row in summary
    }
    expected = {(label, users_value) for label in labels for users_value in users}
    if set(indexed) != expected:
        raise R7500EvaluationError("SVG plot input grid is incomplete")
    values = list(indexed.values())
    if any(not math.isfinite(value) or value <= 0.0 for value in values):
        raise R7500EvaluationError("SVG plot contains invalid EE values")
    displayed_footer_labels = list(
        authority.REQUIRED_LABELS if footer_labels is None else footer_labels
    )
    if any(label not in displayed_footer_labels for label in authority.REQUIRED_LABELS):
        raise R7500EvaluationError("SVG footer omits a required R7 claim label")
    footer = html.escape(" | ".join(displayed_footer_labels))
    lower = min(values)
    upper = max(values)
    padding = max((upper - lower) * 0.12, upper * 0.02, 1e-9)
    y_min = max(0.0, lower - padding)
    y_max = upper + padding
    if not y_max > y_min:
        y_max = y_min + 1.0

    def x_position(value: int) -> float:
        return left + users.index(value) * plot_width / max(len(users) - 1, 1)

    def y_position(value: float) -> float:
        return top + (y_max - value) * plot_height / (y_max - y_min)

    colours = ("#6E7278", "#1F6FB4", "#D97706", "#2F855A", "#8B5CF6")
    dashes = ("10 7", "", "7 4", "4 3", "2 3")
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g font-family="Times New Roman, Times, serif" fill="#20242a">',
        f'<text x="{width/2:.1f}" y="38" text-anchor="middle" font-size="25">{html.escape(title)} (lr={learning_rate:g})</text>',
    ]
    for tick in range(6):
        value = y_min + (y_max - y_min) * tick / 5
        y = y_position(value)
        parts.extend(
            [
                f'<line x1="{left:.1f}" y1="{y:.1f}" x2="{left+plot_width:.1f}" y2="{y:.1f}" stroke="#d9dde2" stroke-width="1" stroke-dasharray="3 5"/>',
                f'<text x="{left-12:.1f}" y="{y+5:.1f}" text-anchor="end" font-size="16">{value:.3g}</text>',
            ]
        )
    parts.extend(
        [
            f'<line x1="{left:.1f}" y1="{top:.1f}" x2="{left:.1f}" y2="{top+plot_height:.1f}" stroke="#30343a" stroke-width="1.5"/>',
            f'<line x1="{left:.1f}" y1="{top+plot_height:.1f}" x2="{left+plot_width:.1f}" y2="{top+plot_height:.1f}" stroke="#30343a" stroke-width="1.5"/>',
        ]
    )
    for user_count in users:
        x = x_position(user_count)
        parts.append(
            f'<text x="{x:.1f}" y="{top+plot_height+28:.1f}" text-anchor="middle" font-size="17">{user_count}</text>'
        )
    for index, label in enumerate(labels):
        colour = colours[index]
        points = " ".join(
            f"{x_position(user_count):.1f},{y_position(indexed[(label, user_count)]):.1f}"
            for user_count in users
        )
        dash = f' stroke-dasharray="{dashes[index]}"' if dashes[index] else ""
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="3"{dash}/>'
        )
        for user_count in users:
            x = x_position(user_count)
            y = y_position(indexed[(label, user_count)])
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#ffffff" stroke="{colour}" stroke-width="3"/>'
            )
        legend_y = top + 25 + index * 34
        legend_x = left + plot_width + 35
        parts.extend(
            [
                f'<line x1="{legend_x:.1f}" y1="{legend_y:.1f}" x2="{legend_x+36:.1f}" y2="{legend_y:.1f}" stroke="{colour}" stroke-width="3"{dash}/>',
                f'<circle cx="{legend_x+18:.1f}" cy="{legend_y:.1f}" r="4" fill="#ffffff" stroke="{colour}" stroke-width="2.5"/>',
                f'<text x="{legend_x+48:.1f}" y="{legend_y+5:.1f}" font-size="15">{html.escape(label)}</text>',
            ]
        )
    parts.extend(
        [
            f'<text x="{left+plot_width/2:.1f}" y="{height-48:.1f}" text-anchor="middle" font-size="19">Number of users</text>',
            f'<text x="28" y="{top+plot_height/2:.1f}" text-anchor="middle" font-size="19" transform="rotate(-90 28 {top+plot_height/2:.1f})">Held-out EE (Mbits/J)</text>',
            f'<text x="{width-14}" y="{height-12}" text-anchor="end" font-size="10.5" font-style="italic">{footer}</text>',
            "</g>",
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def evaluate_prefixes(
    *,
    authority_path: Path,
    bridge_receipt_path: Path,
    reconciliation_receipt_path: Path,
    learning_rate: float,
    output_dir: Path,
    tle_root: Path,
    repo: Path = REPO,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    tle_root = Path(tle_root).expanduser().resolve()
    lr_key = _lr_key(learning_rate)
    validated, authority_sha, bridge_receipt, reconciliation_receipt, checkpoints = _load_inputs(
        authority_path=authority_path,
        bridge_receipt_path=bridge_receipt_path,
        reconciliation_receipt_path=reconciliation_receipt_path,
        learning_rate=float(lr_key),
        tle_root=tle_root,
        repo=repo,
    )
    bridge_receipt_path = Path(bridge_receipt_path).expanduser().resolve()
    reconciliation_receipt_path = Path(reconciliation_receipt_path).expanduser().resolve()
    bridge_receipt_sha = authority.sha256_file(bridge_receipt_path)
    reconciliation_receipt_sha = authority.sha256_file(reconciliation_receipt_path)
    evaluation_gate = preflight.assert_evaluation_ready(
        authority_path=authority_path,
        tle_root=tle_root,
        repo=repo,
    )
    expected_output = (
        repo
        / validated["ablation_output_root"]
        / "evaluation"
        / ("lr0p001-prefix" if lr_key == "0.001" else "lr0p01-prefix")
    ).resolve()
    output = Path(output_dir).expanduser().resolve()
    if output != expected_output:
        raise R7500EvaluationError("evaluation output path drifted from authority")
    try:
        output, staging = output_tools.reserve_output_directory(
            output,
            marker={
                "schema": "r7-output-reservation-v1",
                "artifact": "prefix-evaluation",
                "required_labels": authority.REQUIRED_LABELS,
            },
        )
    except FileExistsError as error:
        raise FileExistsError(
            f"refusing to overwrite R7 evaluation output: {output}"
        ) from error

    lock_path = (repo / validated["resource_policy"]["global_evaluation_lock"]).resolve()
    lock_marker = {
        "artifact": f"prefix-evaluation-lr-{lr_key}",
        "authority_sha256": authority_sha,
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
    }
    lock_acquired = False
    try:
        output_tools.acquire_evaluation_lock(
            lock_path,
            marker=lock_marker,
        )
        lock_acquired = True
        prereg = (
            repo
            / str(validated["validated_base_authorities"][lr_key]["canonical_prereg"])
        ).resolve()
        archive, ephemeris = sweep.canonical_ephemeris_authority(prereg, tle_root)
        raw = []
        for item in checkpoints:
            for users in authority.EVALUATION_USERS:
                for seed in authority.EVALUATION_SEEDS:
                    raw.append(
                        sweep.evaluate_checkpoint_point(
                            archive=archive,
                            checkpoint_path=item["path"],
                            checkpoint_payload=item["payload"],
                            arm=item["label"],
                            checkpoint_sha256=item["sha256"],
                            users=users,
                            evaluation_seed=seed,
                        )
                    )
        raw_rows = [asdict(row) for row in raw]
        validate_evaluation_rows(raw_rows, expected_count=50)
        summary = sweep.aggregate_rows(raw)
        if len(raw_rows) != 50 or len(summary) != 10:
            raise R7500EvaluationError("R7 prefix evaluation grid is incomplete")
        payload = {
            "schema": SCHEMA,
            "status": "complete",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "learning_rate": float(lr_key),
            "endpoint_episodes": 500,
            "authority_sha256": authority_sha,
            "bridge_receipt": {
                "path": str(bridge_receipt_path),
                "sha256": bridge_receipt_sha,
                "reconciliation_required": bridge_receipt.get("reconciliation_required"),
            },
            "reconciliation_receipt": {
                "path": str(reconciliation_receipt_path),
                "sha256": reconciliation_receipt_sha,
                "status": reconciliation_receipt.get("status"),
            },
            "evaluation_policy": "MAIN_ONLY_MASKED_GREEDY",
            "evaluation_partition": "TEST",
            "ee_aggregation": "RATIO_OF_POOLED_USEFUL_BITS_TO_POOLED_SYSTEM_ENERGY",
            "users": authority.EVALUATION_USERS,
            "evaluation_seeds": authority.EVALUATION_SEEDS,
            "ephemeris_authority": ephemeris,
            "evaluation_gate": evaluation_gate,
            "guards": {
                "zero_power_intervals": 0,
                "all_evaluation_episodes_have_positive_useful_bits": True,
            },
            "checkpoints": [
                {
                    "arm": item["arm"],
                    "label": item["label"],
                    "path": str(item["path"]),
                    "sha256": item["sha256"],
                    "source_status": item["source_status"],
                    "online_policy_sha256": item["online_policy_sha256"],
                }
                for item in checkpoints
            ],
            "summary": summary,
        }
        raw_payload = {
            "schema": RAW_SCHEMA,
            "status": "complete",
            "created_utc": payload["created_utc"],
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "learning_rate": float(lr_key),
            "endpoint_episodes": 500,
            "authority_sha256": authority_sha,
            "bridge_receipt": payload["bridge_receipt"],
            "reconciliation_receipt": payload["reconciliation_receipt"],
            "evaluation_policy": payload["evaluation_policy"],
            "evaluation_partition": payload["evaluation_partition"],
            "ee_aggregation": payload["ee_aggregation"],
            "users": authority.EVALUATION_USERS,
            "evaluation_seeds": authority.EVALUATION_SEEDS,
            "ephemeris_authority": ephemeris,
            "evaluation_gate": evaluation_gate,
            "checkpoints": payload["checkpoints"],
            "rows": raw_rows,
        }
        raw_path = staging / "sweep-raw.json"
        summary_path = staging / "sweep-summary.json"
        _write_json(raw_path, raw_payload)
        _write_json(summary_path, payload)
        plot_path = staging / "ee-vs-users-r7-500.svg"
        write_svg_plot(
            plot_path,
            summary,
            learning_rate=float(lr_key),
            title="500-EP Preliminary EE Trend",
            labels=list(ROUTING_LABELS.values()),
        )
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": "PASS",
            "claim_ceiling": authority.CLAIM_CEILING,
            "required_labels": authority.REQUIRED_LABELS,
            "learning_rate": float(lr_key),
            "authority_sha256": authority_sha,
            "bridge_receipt": payload["bridge_receipt"],
            "reconciliation_receipt": payload["reconciliation_receipt"],
            "checkpoint_bindings": payload["checkpoints"],
            "artifacts": {
                "raw": {
                    "path": str(output / "sweep-raw.json"),
                    "sha256": authority.sha256_file(raw_path),
                },
                "summary": {
                    "path": str(output / "sweep-summary.json"),
                    "sha256": authority.sha256_file(summary_path),
                },
                "plot": {
                    "path": str(output / "ee-vs-users-r7-500.svg"),
                    "sha256": authority.sha256_file(plot_path),
                },
            },
        }
        _write_json(staging / "evaluation-receipt.json", receipt)
        if (
            authority.sha256_file(Path(authority_path).expanduser().resolve())
            != authority_sha
            or authority.sha256_file(bridge_receipt_path) != bridge_receipt_sha
            or authority.sha256_file(reconciliation_receipt_path)
            != reconciliation_receipt_sha
            or any(
                not item["path"].is_file()
                or authority.sha256_file(item["path"]) != item["sha256"]
                for item in checkpoints
            )
        ):
            raise R7500EvaluationError("R7 evaluation lineage changed before publication")
        output_tools.publish_receipt_last(
            staging=staging,
            output=output,
            receipt_name="evaluation-receipt.json",
        )
        output_tools.release_evaluation_lock(
            lock_path,
            expected_marker=lock_marker,
        )
        lock_acquired = False
        output_tools.finalize_publication(
            output=output,
            receipt_name="evaluation-receipt.json",
        )
        return receipt
    except BaseException as error:
        output_tools.abort_reserved_output(staging=staging, output=output)
        if lock_acquired:
            try:
                output_tools.release_evaluation_lock(
                    lock_path,
                    expected_marker=lock_marker,
                )
            except Exception as lock_error:
                error.add_note(
                    "R7 owned evaluation lock cleanup failed; lock was preserved: "
                    f"{lock_error}"
                )
        raise


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--bridge-receipt", type=Path, required=True)
    parser.add_argument("--reconciliation-receipt", type=Path, required=True)
    parser.add_argument("--learning-rate", type=float, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    evaluate_prefixes(
        authority_path=args.authority,
        bridge_receipt_path=args.bridge_receipt,
        reconciliation_receipt_path=args.reconciliation_receipt,
        learning_rate=args.learning_rate,
        output_dir=args.output_dir,
        tle_root=args.tle_root,
    )
    print(Path(args.output_dir).expanduser().resolve() / "evaluation-receipt.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
