#!/usr/bin/env python3
"""Apply the frozen R7 two-arm EP500 machine gate and route A101 first."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (HERE, REPO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r7_500_authority as authority  # noqa: E402
import r7_500_evaluate as evaluator  # noqa: E402
import r7_500_prefix_bridge as bridge  # noqa: E402


SCHEMA = "multi-catfish-mcrl-c2-v03a-r7-500-lr-routing-receipt-v3"


class R7500LRRoutingError(RuntimeError):
    """Raised when the two prefix evaluations cannot support the frozen gate."""


def _read_object(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise R7500LRRoutingError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, Mapping):
        raise R7500LRRoutingError(f"{label} must be a JSON object")
    return value


def _finite(value: Any, *, field: str, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise R7500LRRoutingError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0.0):
        raise R7500LRRoutingError(f"{field} is invalid")
    return number


def _recompute_from_raw(
    raw_path: Path,
    *,
    expected_learning_rate: float,
    authority_sha256: str,
    bridge_row: Mapping[str, Any],
    reconciliation_row: Mapping[str, Any],
    checkpoint_bindings: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], list[dict[str, Any]]]:
    raw = _read_object(raw_path, label="R7 evaluation raw episode totals")
    exact = {
        "schema": evaluator.RAW_SCHEMA,
        "status": "complete",
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "endpoint_episodes": 500,
        "authority_sha256": authority_sha256,
        "bridge_receipt": dict(bridge_row),
        "reconciliation_receipt": dict(reconciliation_row),
        "evaluation_policy": "MAIN_ONLY_MASKED_GREEDY",
        "evaluation_partition": "TEST",
        "ee_aggregation": "RATIO_OF_POOLED_USEFUL_BITS_TO_POOLED_SYSTEM_ENERGY",
        "users": authority.EVALUATION_USERS,
        "evaluation_seeds": authority.EVALUATION_SEEDS,
        "checkpoints": list(checkpoint_bindings),
    }
    for field_name, expected in exact.items():
        if raw.get(field_name) != expected:
            raise R7500LRRoutingError(f"R7 raw evaluation {field_name} drifted")
    if not math.isclose(
        float(raw.get("learning_rate", float("nan"))),
        expected_learning_rate,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise R7500LRRoutingError("R7 raw evaluation learning rate drifted")
    ephemeris = raw.get("ephemeris_authority")
    if not isinstance(ephemeris, Mapping):
        raise R7500LRRoutingError("R7 raw ephemeris authority is missing")
    gate = raw.get("evaluation_gate")
    gate_host = gate.get("host") if isinstance(gate, Mapping) else None
    gate_runtime = gate.get("runtime") if isinstance(gate, Mapping) else None
    gate_sources = gate.get("source_matrices") if isinstance(gate, Mapping) else None
    gate_assessment = gate.get("assessment") if isinstance(gate, Mapping) else None
    if (
        not isinstance(gate, Mapping)
        or gate.get("schema") != evaluator.preflight.SCHEMA
        or gate.get("status") != "PASS"
        or gate.get("claim_ceiling") != authority.CLAIM_CEILING
        or gate.get("required_labels") != authority.REQUIRED_LABELS
        or gate.get("authority_sha256") != authority_sha256
        or gate.get("source_checkpoint_evaluation_authorized") is not True
        or gate.get("new_r7_training_authorized") is not False
        or gate.get("resource_policy") != authority.RESOURCE_POLICY
        or not isinstance(gate_host, Mapping)
        or gate_host.get("hostname") != authority.RESOURCE_POLICY["authorized_hostname"]
        or gate_runtime
        != {
            "python": authority.RUNTIME_PYTHON_VERSION,
            "packages": authority.RUNTIME_PACKAGES,
        }
        or not isinstance(gate_sources, list)
        or len(gate_sources) != 2
        or [row.get("learning_rate") for row in gate_sources if isinstance(row, Mapping)]
        != list(authority.ALLOWED_LEARNING_RATES)
        or any(
            not isinstance(row, Mapping)
            or row.get("status") != "complete"
            or row.get("verified_arm_count") != len(authority.BRIDGED_ARMS)
            for row in gate_sources
        )
        or not isinstance(gate_assessment, Mapping)
        or gate_assessment.get("status") != "PASS"
        or gate_assessment.get("failures") != []
        or gate_assessment.get("active_training_processes") != []
        or gate_assessment.get("runtime") != gate_runtime
    ):
        raise R7500LRRoutingError("R7 raw evaluation gate is inadmissible")
    rows = raw.get("rows")
    if not isinstance(rows, list):
        raise R7500LRRoutingError("R7 raw episode grid is missing")
    expected_fields = {field.name for field in fields(evaluator.sweep.EpisodeTotals)}
    checkpoint_by_label = {
        str(row["label"]): str(row["sha256"])
        for row in checkpoint_bindings
        if isinstance(row, Mapping)
    }
    if set(checkpoint_by_label) != set(evaluator.ROUTING_LABELS.values()):
        raise R7500LRRoutingError("R7 raw checkpoint bindings are incomplete")
    expected_grid = [
        (label, users, seed)
        for label in evaluator.ROUTING_LABELS.values()
        for users in authority.EVALUATION_USERS
        for seed in authority.EVALUATION_SEEDS
    ]
    observed_grid: list[tuple[str, int, int]] = []
    materialized = []
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
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != expected_fields:
            raise R7500LRRoutingError("R7 raw episode row fields drifted")
        label = row.get("arm")
        users = row.get("users")
        seed = row.get("evaluation_seed")
        if type(users) is not int or type(seed) is not int:
            raise R7500LRRoutingError("R7 raw episode identity is malformed")
        observed_grid.append((str(label), users, seed))
        if row.get("checkpoint_sha256") != checkpoint_by_label.get(str(label)):
            raise R7500LRRoutingError("R7 raw checkpoint SHA binding drifted")
        if row.get("training_seed") != authority.TRAINING_SEEDS["training"]:
            raise R7500LRRoutingError("R7 raw training seed drifted")
        for name in integer_fields:
            if type(row.get(name)) is not int:
                raise R7500LRRoutingError(f"R7 raw row {index} {name} is not an integer")
        for name in numeric_fields:
            _finite(row.get(name), field=f"raw[{index}].{name}")
        duration = float(row["duration_s"])
        useful_bits = float(row["useful_bits"])
        energy = float(row["system_energy_j"])
        total_intervals = int(row["total_user_intervals"])
        served_intervals = int(row["served_user_intervals"])
        zero_service = int(row["zero_service_intervals"])
        if (
            int(row["steps"]) <= 0
            or duration <= 0.0
            or useful_bits <= 0.0
            or energy <= 0.0
            or total_intervals <= 0
            or not 0 <= served_intervals <= total_intervals
            or not 0 <= zero_service <= int(row["steps"])
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
            raise R7500LRRoutingError("R7 raw episode physical invariants failed")
        try:
            materialized.append(evaluator.sweep.EpisodeTotals(**dict(row)))
        except (TypeError, ValueError) as error:
            raise R7500LRRoutingError("R7 raw episode row cannot be reconstructed") from error
    if observed_grid != expected_grid:
        raise R7500LRRoutingError("R7 raw episode grid is incomplete or reordered")
    try:
        evaluator.validate_evaluation_rows(rows, expected_count=50)
        recomputed = evaluator.sweep.aggregate_rows(materialized)
    except Exception as error:
        raise R7500LRRoutingError("R7 raw episode safeguards or aggregation failed") from error
    if len(recomputed) != 10:
        raise R7500LRRoutingError("R7 raw aggregation grid is incomplete")
    return raw, recomputed


def _assessment(
    receipt_path: Path,
    *,
    expected_learning_rate: float,
    authority_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(receipt_path).expanduser().resolve()
    if (path.parent / evaluator.output_tools.INCOMPLETE_MARKER).exists():
        raise R7500LRRoutingError("R7 evaluation publication is incomplete")
    receipt_sha_before = authority.sha256_file(path)
    receipt = _read_object(path, label="R7 evaluation receipt")
    receipt_sha = authority.sha256_file(path)
    if receipt_sha != receipt_sha_before:
        raise R7500LRRoutingError("R7 evaluation receipt changed while being read")
    if (
        receipt.get("schema") != evaluator.RECEIPT_SCHEMA
        or receipt.get("status") != "PASS"
        or receipt.get("claim_ceiling") != authority.CLAIM_CEILING
        or receipt.get("authority_sha256") != authority_sha256
        or receipt.get("required_labels") != authority.REQUIRED_LABELS
        or not math.isclose(
            float(receipt.get("learning_rate", float("nan"))),
            expected_learning_rate,
            rel_tol=0.0,
            abs_tol=1e-15,
        )
    ):
        raise R7500LRRoutingError("R7 evaluation receipt identity drifted")
    bridge_row = receipt.get("bridge_receipt")
    reconciliation_row = receipt.get("reconciliation_receipt")
    checkpoint_bindings = receipt.get("checkpoint_bindings")
    if (
        not isinstance(bridge_row, Mapping)
        or not isinstance(reconciliation_row, Mapping)
        or reconciliation_row.get("status") != "PASS"
        or not isinstance(checkpoint_bindings, list)
        or len(checkpoint_bindings) != len(authority.PREFIX_ARMS)
        or any(not isinstance(row, Mapping) for row in checkpoint_bindings)
        or [row.get("arm") for row in checkpoint_bindings if isinstance(row, Mapping)]
        != list(authority.PREFIX_ARMS)
    ):
        raise R7500LRRoutingError("R7 evaluation lineage receipt is incomplete")
    for label, row in (("bridge", bridge_row), ("reconciliation", reconciliation_row)):
        lineage_path = Path(str(row.get("path"))).expanduser().resolve()
        if (
            not lineage_path.is_file()
            or row.get("sha256") != authority.sha256_file(lineage_path)
        ):
            raise R7500LRRoutingError(f"R7 {label} lineage SHA drifted")
    bridge_root = Path(str(bridge_row.get("path"))).expanduser().resolve().parent
    for expected_arm, row in zip(authority.PREFIX_ARMS, checkpoint_bindings, strict=True):
        checkpoint_path = Path(str(row.get("path"))).expanduser().resolve()
        if (
            row.get("arm") != expected_arm
            or row.get("label") != evaluator.ROUTING_LABELS[expected_arm]
            or not checkpoint_path.is_relative_to(bridge_root)
            or not checkpoint_path.is_file()
            or row.get("sha256") != authority.sha256_file(checkpoint_path)
            or not isinstance(row.get("online_policy_sha256"), str)
            or not authority.SHA256_RE.fullmatch(str(row.get("online_policy_sha256")))
        ):
            raise R7500LRRoutingError("R7 evaluation checkpoint binding drifted")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, Mapping) or set(artifacts) != {"raw", "summary", "plot"}:
        raise R7500LRRoutingError("R7 evaluation artifact receipt set drifted")
    summary_row = artifacts.get("summary")
    raw_row = artifacts.get("raw") if isinstance(artifacts, Mapping) else None
    if not isinstance(summary_row, Mapping) or not isinstance(raw_row, Mapping):
        raise R7500LRRoutingError("R7 evaluation raw/summary receipts are missing")
    summary_path = Path(str(summary_row.get("path"))).expanduser().resolve()
    raw_path = Path(str(raw_row.get("path"))).expanduser().resolve()
    if summary_path != path.with_name("sweep-summary.json"):
        raise R7500LRRoutingError("R7 evaluation summary path drifted")
    if not summary_path.is_file() or summary_row.get("sha256") != authority.sha256_file(summary_path):
        raise R7500LRRoutingError("R7 evaluation summary SHA drifted")
    if not raw_path.is_file() or raw_row.get("sha256") != authority.sha256_file(raw_path):
        raise R7500LRRoutingError("R7 evaluation raw SHA drifted")
    if raw_path != summary_path.with_name("sweep-raw.json"):
        raise R7500LRRoutingError("R7 evaluation raw path drifted")
    plot_row = artifacts["plot"]
    if not isinstance(plot_row, Mapping):
        raise R7500LRRoutingError("R7 evaluation plot receipt is malformed")
    plot_path = Path(str(plot_row.get("path"))).expanduser().resolve()
    if (
        plot_path != path.with_name("ee-vs-users-r7-500.svg")
        or not plot_path.is_file()
        or plot_row.get("sha256") != authority.sha256_file(plot_path)
    ):
        raise R7500LRRoutingError("R7 evaluation SVG receipt drifted")
    summary = _read_object(summary_path, label="R7 evaluation summary")
    raw, recomputed_rows = _recompute_from_raw(
        raw_path,
        expected_learning_rate=expected_learning_rate,
        authority_sha256=authority_sha256,
        bridge_row=bridge_row,
        reconciliation_row=reconciliation_row,
        checkpoint_bindings=checkpoint_bindings,
    )
    exact = {
        "schema": evaluator.SCHEMA,
        "status": "complete",
        "claim_ceiling": authority.CLAIM_CEILING,
        "endpoint_episodes": 500,
        "authority_sha256": authority_sha256,
        "evaluation_policy": "MAIN_ONLY_MASKED_GREEDY",
        "evaluation_partition": "TEST",
        "ee_aggregation": "RATIO_OF_POOLED_USEFUL_BITS_TO_POOLED_SYSTEM_ENERGY",
        "users": authority.EVALUATION_USERS,
        "evaluation_seeds": authority.EVALUATION_SEEDS,
        "required_labels": authority.REQUIRED_LABELS,
        "bridge_receipt": dict(bridge_row),
        "reconciliation_receipt": dict(reconciliation_row),
        "checkpoints": checkpoint_bindings,
        "guards": {
            "zero_power_intervals": 0,
            "all_evaluation_episodes_have_positive_useful_bits": True,
        },
        "ephemeris_authority": raw["ephemeris_authority"],
        "evaluation_gate": raw["evaluation_gate"],
        "created_utc": raw.get("created_utc"),
    }
    for field, expected in exact.items():
        if summary.get(field) != expected:
            raise R7500LRRoutingError(f"R7 evaluation {field} drifted")
    if not math.isclose(
        float(summary.get("learning_rate", float("nan"))),
        expected_learning_rate,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise R7500LRRoutingError("R7 evaluation learning rate drifted")
    checkpoints = summary.get("checkpoints")
    if not isinstance(checkpoints, list) or [
        row.get("arm") for row in checkpoints if isinstance(row, Mapping)
    ] != list(authority.PREFIX_ARMS):
        raise R7500LRRoutingError("R7 evaluation checkpoint pair drifted")

    rows = summary.get("summary")
    if not isinstance(rows, list) or len(rows) != 10:
        raise R7500LRRoutingError("R7 evaluation grid must contain 2 arms x 5 loads")
    if rows != recomputed_rows:
        raise R7500LRRoutingError("R7 evaluation summary does not reproduce from raw rows")
    indexed: dict[tuple[str, int], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise R7500LRRoutingError("R7 evaluation row is malformed")
        label = str(row.get("arm"))
        users = row.get("users")
        if label not in evaluator.ROUTING_LABELS.values() or users not in authority.EVALUATION_USERS:
            raise R7500LRRoutingError("R7 evaluation arm/load identity drifted")
        key = (label, int(users))
        if key in indexed:
            raise R7500LRRoutingError("R7 evaluation contains duplicate arm/load rows")
        if row.get("training_seed_count") != 1:
            raise R7500LRRoutingError("R7 evaluation is not one trained policy per arm")
        seed_rows = row.get("seed_rows")
        if not isinstance(seed_rows, list) or len(seed_rows) != 1:
            raise R7500LRRoutingError("R7 evaluation seed aggregation drifted")
        seed_row = seed_rows[0]
        if (
            not isinstance(seed_row, Mapping)
            or seed_row.get("training_seed") != authority.TRAINING_SEEDS["training"]
            or seed_row.get("evaluation_seeds") != authority.EVALUATION_SEEDS
            or seed_row.get("zero_power_intervals") != 0
            or _finite(seed_row.get("useful_bits"), field=f"{label}.useful_bits") <= 0.0
        ):
            raise R7500LRRoutingError("R7 evaluation seed safeguards failed")
        zero_service = seed_row.get("zero_service_intervals")
        if type(zero_service) is not int or zero_service < 0:
            raise R7500LRRoutingError("R7 zero-service interval receipt is invalid")
        _finite(row.get("mean_ee_bits_per_j"), field=f"{label}.EE", positive=True)
        served = _finite(seed_row.get("served_fraction"), field=f"{label}.served")
        if not 0.0 <= served <= 1.0:
            raise R7500LRRoutingError("R7 served fraction is outside [0,1]")
        indexed[key] = row
    expected_grid = {
        (label, users)
        for label in evaluator.ROUTING_LABELS.values()
        for users in authority.EVALUATION_USERS
    }
    if set(indexed) != expected_grid:
        raise R7500LRRoutingError("R7 evaluation grid is incomplete")

    baseline = indexed[(evaluator.ROUTING_LABELS["B000"], 100)]
    full = indexed[(evaluator.ROUTING_LABELS["F111"], 100)]
    baseline_ee = float(baseline["mean_ee_bits_per_j"])
    full_ee = float(full["mean_ee_bits_per_j"])
    baseline_served = float(baseline["seed_rows"][0]["served_fraction"])
    full_served = float(full["seed_rows"][0]["served_fraction"])
    d_full = 100.0 * (full_ee / baseline_ee - 1.0)
    service_loss_pp = 100.0 * (baseline_served - full_served)
    all_guards_pass = True
    service_limit = float(authority.ROUTING_RULE["service_loss_limit_percentage_points"])
    eligible = (
        d_full > 0.0
        and service_loss_pp <= service_limit + 1e-9
        and all_guards_pass
    )
    assessment = {
        "learning_rate": expected_learning_rate,
        "endpoint_episodes": 500,
        "endpoint_users": 100,
        "baseline_ee_bits_per_j": baseline_ee,
        "full_ee_bits_per_j": full_ee,
        "d_full_percent": d_full,
        "baseline_served_fraction": baseline_served,
        "full_served_fraction": full_served,
        "service_loss_percentage_points": service_loss_pp,
        "all_guards_pass": all_guards_pass,
        "eligible": eligible,
    }
    input_receipt = {
        "path": str(path),
        "sha256": receipt_sha,
        "summary_path": str(summary_path),
        "summary_sha256": str(summary_row["sha256"]),
        "raw_path": str(raw_path),
        "raw_sha256": str(raw_row["sha256"]),
        "bridge_receipt": dict(bridge_row),
        "reconciliation_receipt": dict(reconciliation_row),
        "checkpoint_bindings": checkpoint_bindings,
    }
    stable_paths = [
        (path, receipt_sha),
        (summary_path, str(summary_row["sha256"])),
        (raw_path, str(raw_row["sha256"])),
        (plot_path, str(plot_row["sha256"])),
        *[
            (
                Path(str(row.get("path"))).expanduser().resolve(),
                str(row.get("sha256")),
            )
            for row in (bridge_row, reconciliation_row, *checkpoint_bindings)
        ],
    ]
    if any(
        not stable_path.is_file()
        or authority.sha256_file(stable_path) != expected_sha
        for stable_path, expected_sha in stable_paths
    ):
        raise R7500LRRoutingError("R7 evaluation lineage changed during routing")
    return assessment, input_receipt


def _decision_core(assessments: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in assessments.values() if row.get("eligible") is True]
    tie_relative_percent = None
    if len(eligible) == 1:
        selected = float(eligible[0]["learning_rate"])
        decision = "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS"
        allowed = list(authority.ABLATION_ARMS)
    elif len(eligible) == 2:
        first = float(assessments["0.001"]["d_full_percent"])
        second = float(assessments["0.01"]["d_full_percent"])
        tie_relative_percent = 100.0 * abs(first - second) / max(first, second)
        selected = (
            0.001
            if tie_relative_percent <= authority.ROUTING_RULE["tie_band_relative_percent"]
            else float(max(eligible, key=lambda row: row["d_full_percent"])["learning_rate"])
        )
        decision = "REVEAL_SELECTED_LR_SOURCE_EP500_ABLATIONS"
        allowed = list(authority.ABLATION_ARMS)
    else:
        selected_row = max(
            assessments.values(),
            key=lambda row: (
                float(row["d_full_percent"]),
                1 if math.isclose(float(row["learning_rate"]), 0.001) else 0,
            ),
        )
        selected = float(selected_row["learning_rate"])
        decision = "REVEAL_A101_SOURCE_EP500_FAILURE_ANALYSIS_ONLY"
        allowed = ["A101"]
    return {
        "decision": decision,
        "selected_learning_rate": selected,
        "tie_relative_percent": tie_relative_percent,
        "first_ablation": "A101",
        "allowed_ablation_arms": allowed,
        "fresh_training_required": False,
        "resume_allowed": False,
        "source_checkpoint_reuse_only": True,
        "new_r7_training_authorized": False,
    }


def select_learning_rate(
    *,
    authority_path: Path,
    lr0p001_evaluation_receipt: Path,
    lr0p01_evaluation_receipt: Path,
    output: Path,
    tle_root: Path,
    repo: Path = REPO,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    validated, authority_sha = bridge.load_and_validate_authority(
        authority_path, repo=repo, tle_root=tle_root
    )
    inputs = {
        "0.001": Path(lr0p001_evaluation_receipt),
        "0.01": Path(lr0p01_evaluation_receipt),
    }
    assessments: dict[str, dict[str, Any]] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for key, path in inputs.items():
        suffix = "lr0p001-prefix" if key == "0.001" else "lr0p01-prefix"
        expected_input = (
            repo
            / validated["ablation_output_root"]
            / "evaluation"
            / suffix
            / "evaluation-receipt.json"
        ).resolve()
        if Path(path).expanduser().resolve() != expected_input:
            raise R7500LRRoutingError("R7 evaluation receipt path drifted")
        assessment, receipt = _assessment(
            path,
            expected_learning_rate=float(key),
            authority_sha256=authority_sha,
        )
        assessments[key] = assessment
        receipts[key] = receipt
    bridge_identities = {
        authority.canonical_json_sha256(row["bridge_receipt"])
        for row in receipts.values()
    }
    reconciliation_identities = {
        authority.canonical_json_sha256(row["reconciliation_receipt"])
        for row in receipts.values()
    }
    if len(bridge_identities) != 1 or len(reconciliation_identities) != 1:
        raise R7500LRRoutingError(
            "the two LR evaluations do not share one bridge and reconciliation receipt"
        )
    decision = _decision_core(assessments)
    result = {
        "schema": SCHEMA,
        "status": "PASS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "claim_ceiling": authority.CLAIM_CEILING,
        "required_labels": authority.REQUIRED_LABELS,
        "authority": {
            "path": str(Path(authority_path).expanduser().resolve()),
            "sha256": authority_sha,
            "pin_map_sha256": validated["pin_map_sha256"],
        },
        "rule": authority.ROUTING_RULE,
        "assessments": assessments,
        "input_evaluations": receipts,
        "decision": decision,
        "formal_training_authorized": False,
        "source_prefix_evaluation_authorized": True,
        "new_r7_training_authorized": False,
    }
    output = Path(output).expanduser().resolve()
    expected_output = (repo / validated["ablation_output_root"] / "lr-selection.json").resolve()
    if output != expected_output:
        raise R7500LRRoutingError("LR receipt path drifted from the R7 authority")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite R7 LR receipt: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    )
    # Do not place unpublished bytes inside the accepted R7 artifact directory.
    # A hard kill may strand the sibling temporary, but cannot make that
    # directory appear to contain a partially published selection receipt.
    temporary_parent = output.parent.parent
    temporary_parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{output.parent.name}-{output.name}.",
        suffix=".tmp",
        dir=temporary_parent,
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return result


def validate_selection_receipt(
    path: Path,
    *,
    authority_path: Path,
    tle_root: Path,
    repo: Path = REPO,
) -> dict[str, Any]:
    repo = Path(repo).expanduser().resolve()
    validated, authority_sha = bridge.load_and_validate_authority(
        authority_path, repo=repo, tle_root=tle_root
    )
    receipt_path = Path(path).expanduser().resolve()
    expected_receipt_path = (
        repo / validated["ablation_output_root"] / "lr-selection.json"
    ).resolve()
    if receipt_path != expected_receipt_path:
        raise R7500LRRoutingError("R7 LR receipt path drifted from the authority")
    receipt_sha_before = authority.sha256_file(receipt_path)
    receipt = _read_object(receipt_path, label="R7 LR receipt")
    if authority.sha256_file(receipt_path) != receipt_sha_before:
        raise R7500LRRoutingError("R7 LR receipt changed while being read")
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("status") != "PASS"
        or receipt.get("claim_ceiling") != authority.CLAIM_CEILING
        or receipt.get("required_labels") != authority.REQUIRED_LABELS
        or receipt.get("rule") != authority.ROUTING_RULE
        or receipt.get("formal_training_authorized") is not False
        or receipt.get("source_prefix_evaluation_authorized") is not True
        or receipt.get("new_r7_training_authorized") is not False
    ):
        raise R7500LRRoutingError("R7 LR receipt identity drifted")
    authority_row = receipt.get("authority")
    if (
        not isinstance(authority_row, Mapping)
        or Path(str(authority_row.get("path"))).expanduser().resolve()
        != Path(authority_path).expanduser().resolve()
        or authority_row.get("sha256") != authority_sha
        or authority_row.get("pin_map_sha256") != validated["pin_map_sha256"]
    ):
        raise R7500LRRoutingError("R7 LR receipt authority drifted")
    inputs = receipt.get("input_evaluations")
    if not isinstance(inputs, Mapping) or set(inputs) != {"0.001", "0.01"}:
        raise R7500LRRoutingError("R7 LR receipt input grid drifted")
    recomputed: dict[str, dict[str, Any]] = {}
    for key in ("0.001", "0.01"):
        row = inputs[key]
        if not isinstance(row, Mapping):
            raise R7500LRRoutingError("R7 LR receipt input row is malformed")
        input_path = Path(str(row.get("path"))).expanduser().resolve()
        suffix = "lr0p001-prefix" if key == "0.001" else "lr0p01-prefix"
        expected_input = (
            repo
            / validated["ablation_output_root"]
            / "evaluation"
            / suffix
            / "evaluation-receipt.json"
        ).resolve()
        if not input_path.is_file() or row.get("sha256") != authority.sha256_file(input_path):
            raise R7500LRRoutingError("R7 LR receipt input SHA drifted")
        if input_path != expected_input:
            raise R7500LRRoutingError("R7 LR receipt input path drifted")
        assessment, observed_row = _assessment(
            input_path,
            expected_learning_rate=float(key),
            authority_sha256=authority_sha,
        )
        if dict(row) != observed_row:
            raise R7500LRRoutingError("R7 LR input receipt no longer reproduces")
        recomputed[key] = assessment
    if receipt.get("assessments") != recomputed:
        raise R7500LRRoutingError("R7 LR assessments no longer reproduce")
    decision = _decision_core(recomputed)
    if receipt.get("decision") != decision:
        raise R7500LRRoutingError("R7 LR decision no longer reproduces")
    # Close the sequential-validation race: after both LR graphs and the
    # decision have been recomputed, take one final hash-only pass across every
    # file reachable from the two immutable evaluation receipts.  The
    # ablation evaluator calls this routine immediately before publication.
    expected_files: dict[Path, str] = {
        receipt_path: receipt_sha_before,
        Path(authority_path).expanduser().resolve(): authority_sha,
    }

    def bind_file(path_value: Any, sha_value: Any, *, label: str) -> None:
        path_value = Path(str(path_value)).expanduser().resolve()
        if not isinstance(sha_value, str) or not authority.SHA256_RE.fullmatch(
            sha_value
        ):
            raise R7500LRRoutingError(f"R7 LR {label} SHA is malformed")
        prior = expected_files.get(path_value)
        if prior is not None and prior != sha_value:
            raise R7500LRRoutingError(
                f"R7 LR {label} has conflicting file identities"
            )
        expected_files[path_value] = sha_value

    for key in ("0.001", "0.01"):
        row = inputs[key]
        evaluation_path = Path(str(row["path"])).expanduser().resolve()
        bind_file(evaluation_path, row["sha256"], label=f"{key} evaluation")
        evaluation_receipt = _read_object(
            evaluation_path, label=f"R7 {key} evaluation receipt final graph"
        )
        artifacts = evaluation_receipt.get("artifacts")
        if not isinstance(artifacts, Mapping) or set(artifacts) != {
            "raw",
            "summary",
            "plot",
        }:
            raise R7500LRRoutingError("R7 LR final artifact graph drifted")
        for artifact_name, artifact_row in artifacts.items():
            if not isinstance(artifact_row, Mapping):
                raise R7500LRRoutingError("R7 LR final artifact row is malformed")
            bind_file(
                artifact_row.get("path"),
                artifact_row.get("sha256"),
                label=f"{key} {artifact_name}",
            )
        for lineage_name in ("bridge_receipt", "reconciliation_receipt"):
            lineage_row = evaluation_receipt.get(lineage_name)
            if not isinstance(lineage_row, Mapping):
                raise R7500LRRoutingError("R7 LR final lineage graph is malformed")
            bind_file(
                lineage_row.get("path"),
                lineage_row.get("sha256"),
                label=f"{key} {lineage_name}",
            )
        checkpoint_rows = evaluation_receipt.get("checkpoint_bindings")
        if not isinstance(checkpoint_rows, list) or len(checkpoint_rows) != len(
            authority.PREFIX_ARMS
        ):
            raise R7500LRRoutingError("R7 LR final checkpoint graph is malformed")
        for checkpoint_row in checkpoint_rows:
            if not isinstance(checkpoint_row, Mapping):
                raise R7500LRRoutingError(
                    "R7 LR final checkpoint binding is malformed"
                )
            bind_file(
                checkpoint_row.get("path"),
                checkpoint_row.get("sha256"),
                label=f"{key} checkpoint",
            )
    if any(
        not path.is_file() or authority.sha256_file(path) != expected_sha
        for path, expected_sha in expected_files.items()
    ):
        raise R7500LRRoutingError(
            "R7 LR receipt or complete input graph changed during revalidation"
        )
    return dict(receipt)


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--lr0p001-evaluation-receipt", type=Path, required=True)
    parser.add_argument("--lr0p01-evaluation-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tle-root", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    select_learning_rate(
        authority_path=args.authority,
        lr0p001_evaluation_receipt=args.lr0p001_evaluation_receipt,
        lr0p01_evaluation_receipt=args.lr0p01_evaluation_receipt,
        output=args.output,
        tle_root=args.tle_root,
    )
    print(Path(args.output).expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
