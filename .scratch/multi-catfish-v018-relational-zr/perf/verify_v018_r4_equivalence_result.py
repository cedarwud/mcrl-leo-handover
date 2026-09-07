#!/usr/bin/env python3
"""Independently validate one V0.18 R4 cache-equivalence result.

This checker is intentionally result-only and standard-library-only.  It does
not import the simulator, open a TLE, run a test, or infer scientific efficacy
from an implementation-equivalence receipt.  A mechanically valid STOP is
returned as a verified STOP; it is never upgraded to PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping


REPO = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO / (
    ".scratch/multi-catfish-v018-relational-zr/contracts/"
    "MULTI-CATFISH-MCRL-V018-R4-SCALE-AWARE-CACHE-EQUIVALENCE-2026-09-04.md"
)
DEFAULT_CODE_MANIFEST = REPO / (
    ".scratch/multi-catfish-v018-relational-zr/contracts/"
    "code-manifest-r4-equivalence.sha256"
)

EXPECTED_SCHEMA = "multi-catfish-mcrl-v018-r4-scale-aware-cache-equivalence-v1"
EXPECTED_RECEIPT_SCHEMA = "multi-catfish-mcrl-v018-r4-equivalence-receipt-v1"
EXPECTED_EXECUTION_ATTEMPT = "r4"
EXPECTED_CONTRACT_STATUS = "Status: `FROZEN_BEFORE_CHECK`"
EXPECTED_CONTRACT_SHA256 = (
    "0367b4fec0695e480b519a891e114551137afdbf4aa360b4a449f193bd7eb96c"
)
EXPECTED_CODE_MANIFEST_SHA256 = (
    "0fd88169d63ce02b87534d4f3c0a81559e17df444a2c2c8f556aac3d901382c1"
)
EXPECTED_WORLD = 2026104901
EXPECTED_LINEAGE = 2026092101
EXPECTED_USERS = 100
EXPECTED_CONTEXTS = (12, 1, 2)
EXPECTED_MAX_WORKERS = 18
EXPECTED_PREREG_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)

R1_RELATIVE = (
    ".scratch/multi-catfish-v018-relational-zr/r1-abort/"
    "ee_axis_relational_zr_c3-r1.py"
)
R2_RELATIVE = "src/mcrl/runtime/ee_axis_relational_zr_c3.py"
RUNNER_RELATIVE = (
    ".scratch/multi-catfish-v018-relational-zr/perf/"
    "verify_v018_r4_cache_equivalence.py"
)
SYNC_RELATIVE = (
    ".scratch/multi-catfish-v018-relational-zr/perf/"
    "sync_v018_r4_equivalence_server.sh"
)
RUN_RELATIVE = (
    ".scratch/multi-catfish-v018-relational-zr/perf/"
    "run_v018_r4_equivalence_server.sh"
)
W178_RELATIVE = "tests/test_w178_ee_axis_relational_zr_c3_r4_bounds.py"
CONTRACT_RELATIVE = (
    ".scratch/multi-catfish-v018-relational-zr/contracts/"
    "MULTI-CATFISH-MCRL-V018-R4-SCALE-AWARE-CACHE-EQUIVALENCE-2026-09-04.md"
)
PREREG_RELATIVE = "artifacts/PREREG-FROZEN-2026-08-25-R2.json"

EXPECTED_IDENTITIES = {
    R1_RELATIVE: "6a3d61940175f0e4e422fa4ac9818fd64652dd4f6e699408f6189cec164425a2",
    R2_RELATIVE: "e66f61d7ad8833115eb0542ca2b4ea6718a23ecc26aa0729f5cf879c64cf6166",
    RUNNER_RELATIVE: "dfe68dc863ae73afaa6c39141249b72df410057e543cef1eda6c32bc68ad2fe4",
    SYNC_RELATIVE: "145759b05d08256ecacbc3f3e16d32f80cf4cd9c9b8cad188b7bb9202e2dede7",
    RUN_RELATIVE: "8f7b9e377e4166276be5a3dfd9e127a537207a46a91b9fbc2850ce88b134c982",
    W178_RELATIVE: "699750e47e1df9985366528216702b21b480433e543d9e7954e501eed59f7c1a",
    CONTRACT_RELATIVE: EXPECTED_CONTRACT_SHA256,
    PREREG_RELATIVE: EXPECTED_PREREG_SHA256,
}

PASS_DECISION = "PASS_R2_CACHE_EQUIVALENCE"
STOP_DECISION = "STOP_R2_CACHE_EQUIVALENCE"


class VerificationError(RuntimeError):
    """The persisted receipt is not consistent with the frozen closure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def regular_file(path: Path, description: str) -> Path:
    require(
        path.exists() and not path.is_symlink() and path.is_file(),
        f"missing, symlinked, or non-regular {description}: {path}",
    )
    return path


def sha_field(value: object, field: str) -> str:
    require(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
        f"{field} must be a lowercase SHA-256",
    )
    return value


def finite_number(value: object, field: str, *, nonnegative: bool = False) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        f"{field} must be numeric",
    )
    number = float(value)
    require(math.isfinite(number), f"{field} must be finite")
    if nonnegative:
        require(number >= 0.0, f"{field} must be non-negative")
    return number


def optional_finite(value: object, field: str, *, nonnegative: bool = False) -> None:
    if value is None:
        return
    finite_number(value, field, nonnegative=nonnegative)


def nonnegative_int(value: object, field: str) -> int:
    require(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0,
        f"{field} must be a non-negative integer",
    )
    return int(value)


def parse_manifest(path: Path) -> dict[str, str]:
    """Read a sha256sum-style manifest without executing shell commands."""

    entries: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
        require(match is not None, f"malformed code-manifest line {number}")
        assert match is not None
        digest, relative = match.groups()
        require(not Path(relative).is_absolute(), f"absolute code-manifest path: {relative}")
        require(relative not in entries, f"duplicate code-manifest path: {relative}")
        entries[relative] = digest
    require(entries, "code manifest is empty")
    return entries


def resolve_repo_path(repo_root: Path, relative: str) -> Path:
    candidate = repo_root / relative
    root = repo_root.resolve()
    resolved = candidate.resolve()
    require(resolved.is_relative_to(root), f"repository path escapes root: {relative}")
    return resolved


def reject_json_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def load_json(path: Path, description: str) -> object:
    regular_file(path, description)
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_json_constant,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(f"invalid {description} JSON: {error}") from error


def verify_code_closure(
    *,
    repo_root: Path,
    contract_path: Path,
    code_manifest_path: Path,
    expected_code_manifest_sha256: str,
) -> dict[str, str]:
    contract = regular_file(contract_path, "frozen R4 equivalence contract")
    manifest_path = regular_file(code_manifest_path, "R4 code manifest")
    require(
        sha256(contract) == EXPECTED_CONTRACT_SHA256,
        "frozen R4 contract digest mismatch",
    )
    require(
        expected_code_manifest_sha256 == EXPECTED_CODE_MANIFEST_SHA256,
        "expected R4 code-manifest digest is not the frozen digest",
    )
    require(
        sha256(manifest_path) == EXPECTED_CODE_MANIFEST_SHA256,
        "R4 code-manifest digest mismatch",
    )
    contract_text = contract.read_text(encoding="utf-8")
    require(EXPECTED_CONTRACT_STATUS in contract_text, "R4 contract is not frozen before check")
    manifest = parse_manifest(manifest_path)
    for relative, expected in EXPECTED_IDENTITIES.items():
        require(relative in manifest, f"code manifest omits required file: {relative}")
        require(
            manifest[relative] == expected,
            f"code manifest identity disagrees for {relative}",
        )
        file_path = regular_file(resolve_repo_path(repo_root, relative), relative)
        require(sha256(file_path) == expected, f"current file hash mismatch: {relative}")
        # The contract cannot contain its own digest without becoming
        # self-referential.  Every other sealed identity must be visible in
        # the frozen contract text.
        if relative != CONTRACT_RELATIVE:
            require(expected in contract_text, f"frozen contract omits identity for {relative}")
    return {
        "contract_sha256": EXPECTED_CONTRACT_SHA256,
        "code_manifest_sha256": EXPECTED_CODE_MANIFEST_SHA256,
        "r1_source_sha256": EXPECTED_IDENTITIES[R1_RELATIVE],
        "r2_source_sha256": EXPECTED_IDENTITIES[R2_RELATIVE],
        "runner_sha256": EXPECTED_IDENTITIES[RUNNER_RELATIVE],
        "prereg_sha256": EXPECTED_PREREG_SHA256,
    }


def verify_preflight(
    *,
    preflight_receipt_path: Path,
    preflight_log_path: Path,
    expected_manifest_sha256: str,
) -> dict[str, str]:
    receipt_path = regular_file(preflight_receipt_path, "server preflight receipt")
    log_path = regular_file(preflight_log_path, "server preflight log")
    lines = receipt_path.read_text(encoding="utf-8").splitlines()
    require(len(lines) == 4, "server preflight receipt is malformed")
    require(
        lines[0] == "schema=multi-catfish-mcrl-v018-r4-equivalence-preflight-v1",
        "server preflight receipt schema mismatch",
    )
    require(
        lines[1] == f"manifest_sha256={expected_manifest_sha256}",
        "server preflight receipt manifest mismatch",
    )
    require(lines[2] == "pytest_exit=0", "server preflight does not attest pytest success")
    match = re.fullmatch(r"log_sha256=([0-9a-f]{64})", lines[3])
    require(match is not None, "server preflight log digest is malformed")
    assert match is not None
    log_digest = sha256(log_path)
    require(log_digest == match.group(1), "server preflight log digest mismatch")
    return {
        "preflight_receipt_sha256": sha256(receipt_path),
        "preflight_log_sha256": log_digest,
    }


def comparison_report(report: object, label: str) -> bool:
    require(isinstance(report, dict), f"{label} is not an object")
    required = {
        "shape_left",
        "shape_right",
        "eligible_count",
        "violation_count",
        "max_abs_deviation",
        "max_normalized_deviation",
        "worst",
        "pass",
    }
    require(required.issubset(report), f"{label} is missing comparison fields")
    for field in ("shape_left", "shape_right"):
        shape = report[field]
        require(isinstance(shape, list), f"{label}.{field} is not a shape list")
        for index, value in enumerate(shape):
            require(
                isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                f"{label}.{field}[{index}] is not a non-negative integer",
            )
    eligible = nonnegative_int(report["eligible_count"], f"{label}.eligible_count")
    violations = nonnegative_int(report["violation_count"], f"{label}.violation_count")
    optional_finite(report["max_abs_deviation"], f"{label}.max_abs_deviation", nonnegative=True)
    optional_finite(
        report["max_normalized_deviation"],
        f"{label}.max_normalized_deviation",
        nonnegative=True,
    )
    if "scale" in report:
        optional_finite(report["scale"], f"{label}.scale", nonnegative=True)
    require(isinstance(report["worst"], list), f"{label}.worst is not a list")
    for index, item in enumerate(report["worst"]):
        require(isinstance(item, dict), f"{label}.worst[{index}] is not an object")
        require(isinstance(item.get("index"), list), f"{label}.worst[{index}] lacks index")
        if "reason" not in item:
            for field in ("absolute_deviation", "normalized_deviation", "threshold"):
                optional_finite(item.get(field), f"{label}.worst[{index}].{field}", nonnegative=True)
    require(isinstance(report["pass"], bool), f"{label}.pass is not boolean")
    if report["pass"]:
        require(violations == 0, f"{label} claims pass with violations")
        require(not report["worst"], f"{label} claims pass with worst violations")
    else:
        require(violations > 0 or report["worst"], f"{label} fails without a violation diagnostic")
    # ``eligible`` is intentionally read above even when a shape mismatch
    # reports one structural violation against an empty eligible set.
    del eligible
    return bool(report["pass"])


def aggregate_report(report: object, label: str) -> bool:
    """Validate a non-array aggregate emitted by the R4 accumulator.

    Reference surfaces are reported by ``_comparison_report`` and therefore
    carry shapes.  Candidate surfaces are merged across all branches by
    ``_merge_aggregate`` and deliberately carry only aggregate diagnostics.
    Keeping these schemas separate prevents a valid R4 PASS from being
    rejected merely because an aggregate has no artificial array shape.
    """

    require(isinstance(report, dict), f"{label} is not an object")
    required = {
        "eligible_count",
        "violation_count",
        "max_abs_deviation",
        "max_normalized_deviation",
        "max_scale",
        "worst",
        "pass",
    }
    require(required.issubset(report), f"{label} is missing aggregate fields")
    nonnegative_int(report["eligible_count"], f"{label}.eligible_count")
    violations = nonnegative_int(report["violation_count"], f"{label}.violation_count")
    optional_finite(report["max_abs_deviation"], f"{label}.max_abs_deviation", nonnegative=True)
    optional_finite(
        report["max_normalized_deviation"],
        f"{label}.max_normalized_deviation",
        nonnegative=True,
    )
    optional_finite(report["max_scale"], f"{label}.max_scale", nonnegative=True)
    require(isinstance(report["worst"], list), f"{label}.worst is not a list")
    for index, item in enumerate(report["worst"]):
        require(isinstance(item, dict), f"{label}.worst[{index}] is not an object")
        require(isinstance(item.get("index"), list), f"{label}.worst[{index}] lacks index")
        if "reason" not in item:
            for field in ("absolute_deviation", "normalized_deviation", "threshold"):
                optional_finite(item.get(field), f"{label}.worst[{index}].{field}", nonnegative=True)
    require(isinstance(report["pass"], bool), f"{label}.pass is not boolean")
    if report["pass"]:
        require(violations == 0, f"{label} claims pass with violations")
        require(not report["worst"], f"{label} claims pass with worst violations")
    else:
        require(violations > 0 or report["worst"], f"{label} fails without an aggregate diagnostic")
    return bool(report["pass"])


def validate_checkpoint(value: object, label: str) -> None:
    require(isinstance(value, dict), f"{label} is not an object")
    sha_field(value.get("checkpoint_sha256"), f"{label}.checkpoint_sha256")
    for field in ("test_split_opened", "held_out_ee_evaluated", "episode_training", "learner_update"):
        if field in value:
            require(value[field] is False, f"{label}.{field} crosses a forbidden boundary")


def validate_sensitivity(value: object, label: str) -> None:
    require(isinstance(value, dict), f"{label} is not an object")
    expected_constants = {"1", "8", "64", "512", "4096"}
    require(set(value) == expected_constants, f"{label} constants drifted")
    for constant in sorted(expected_constants, key=int):
        item = value[constant]
        require(isinstance(item, dict), f"{label}[{constant}] is not an object")
        required = {"max_normalized_deviation", "violation_count", "max_absolute_deviation", "bound_max_bits"}
        require(required.issubset(item), f"{label}[{constant}] is incomplete")
        optional_finite(item["max_normalized_deviation"], f"{label}[{constant}].max_normalized_deviation", nonnegative=True)
        nonnegative_int(item["violation_count"], f"{label}[{constant}].violation_count")
        optional_finite(item["max_absolute_deviation"], f"{label}[{constant}].max_absolute_deviation", nonnegative=True)
        optional_finite(item["bound_max_bits"], f"{label}[{constant}].bound_max_bits", nonnegative=True)


def validate_full_context(report: object, context: int) -> bool:
    label = f"context {context}"
    require(isinstance(report, dict), f"{label} report is not an object")
    required = {
        "pass",
        "legal_branch_count",
        "unique_branch_vector_count",
        "reference_reconstruction_elapsed_s",
        "checked_nonfocal_rate_and_interference_values",
        "maximum_nonfocal_rate_deviation_bps",
        "maximum_nonfocal_interference_deviation_w",
        "maximum_absolute_deviation",
        "state_content_digest_equal",
        "selected_actions_equal",
        "selected_action_sha256",
        "maximum_score_deviation",
        "minimum_top_two_margin",
        "margin_to_deviation_ratio",
        "score_check",
        "primitive_checks",
        "delta_bound",
        "q3_check",
        "state_exact_checks",
        "focal_exclusion",
        "branch_maps",
        "clamp_invariant",
        "coupling_coverage",
        "victim_predicate",
    }
    require(required.issubset(report), f"{label} report omits one or more acceptance gates")
    require(isinstance(report["pass"], bool), f"{label}.pass is not boolean")
    legal = nonnegative_int(report["legal_branch_count"], f"{label}.legal_branch_count")
    require(legal > 0, f"{label}.legal_branch_count is zero")
    unique = nonnegative_int(report["unique_branch_vector_count"], f"{label}.unique_branch_vector_count")
    require(1 <= unique <= legal + 1, f"{label}.unique_branch_vector_count is invalid")
    finite_number(report["reference_reconstruction_elapsed_s"], f"{label}.reconstruction_time", nonnegative=True)
    checked = nonnegative_int(
        report["checked_nonfocal_rate_and_interference_values"],
        f"{label}.checked_nonfocal_rate_and_interference_values",
    )
    require(checked == legal * (EXPECTED_USERS - 1), f"{label} non-focal count is inconsistent")
    finite_number(report["maximum_nonfocal_rate_deviation_bps"], f"{label}.rate_deviation", nonnegative=True)
    finite_number(report["maximum_nonfocal_interference_deviation_w"], f"{label}.interference_deviation", nonnegative=True)
    deviations = report["maximum_absolute_deviation"]
    require(isinstance(deviations, dict), f"{label}.maximum_absolute_deviation is not an object")
    require(set(deviations) == {"delta", "q3", "action_context", "victim_tokens"}, f"{label} deviation fields drifted")
    for field, value in deviations.items():
        optional_finite(value, f"{label}.maximum_absolute_deviation.{field}", nonnegative=True)
    require(isinstance(report["state_content_digest_equal"], bool), f"{label}.state_content_digest_equal is not boolean")
    require(isinstance(report["selected_actions_equal"], bool), f"{label}.selected_actions_equal is not boolean")
    selected_digest = report["selected_action_sha256"]
    if selected_digest is not None:
        sha_field(selected_digest, f"{label}.selected_action_sha256")
    optional_finite(report["maximum_score_deviation"], f"{label}.maximum_score_deviation", nonnegative=True)
    optional_finite(report["minimum_top_two_margin"], f"{label}.minimum_top_two_margin", nonnegative=True)
    optional_finite(report["margin_to_deviation_ratio"], f"{label}.margin_to_deviation_ratio", nonnegative=True)
    if report["maximum_score_deviation"] == 0.0:
        require(report["margin_to_deviation_ratio"] is None, f"{label} zero score deviation must report null ratio")

    score_check = report["score_check"]
    require(isinstance(score_check, dict), f"{label}.score_check is not an object")
    require({"scores_finite_on_legal_actions", "nonfinite_legal_score_count"}.issubset(score_check), f"{label}.score_check is incomplete")
    require(isinstance(score_check["scores_finite_on_legal_actions"], bool), f"{label}.score_check finite flag is not boolean")
    nonfinite_scores = nonnegative_int(score_check["nonfinite_legal_score_count"], f"{label}.score_check.nonfinite_legal_score_count")
    if score_check["scores_finite_on_legal_actions"]:
        require(nonfinite_scores == 0, f"{label} claims finite scores with non-finite score count")
    else:
        require(nonfinite_scores > 0, f"{label} claims non-finite scores with zero count")

    primitive = report["primitive_checks"]
    require(isinstance(primitive, dict), f"{label}.primitive_checks is not an object")
    reference_names = ("reference_rate", "reference_interference")
    aggregate_names = ("candidate_rate", "candidate_interference")
    require(set(reference_names + aggregate_names).issubset(primitive), f"{label}.primitive_checks is incomplete")
    primitive_results = [
        comparison_report(primitive[name], f"{label}.primitive_checks.{name}")
        for name in reference_names
    ]
    primitive_results.extend(
        aggregate_report(primitive[name], f"{label}.primitive_checks.{name}")
        for name in aggregate_names
    )
    primitive_pass = all(primitive_results)

    delta = report["delta_bound"]
    require(isinstance(delta, dict), f"{label}.delta_bound is not an object")
    require({"mechanical_c", "hard_ceiling_bits", "comparison", "hard_ceiling", "structural_exact", "structural_zero", "sensitivity"}.issubset(delta), f"{label}.delta_bound is incomplete")
    require(delta["mechanical_c"] == 64, f"{label} mechanical C drifted")
    require(delta["hard_ceiling_bits"] == 1e-3, f"{label} hard ceiling drifted")
    delta_results = [
        comparison_report(delta[name], f"{label}.delta_bound.{name}")
        for name in ("comparison", "hard_ceiling", "structural_exact", "structural_zero")
    ]
    delta_pass = all(delta_results)
    validate_sensitivity(delta["sensitivity"], f"{label}.delta_bound.sensitivity")

    q3_pass = comparison_report(report["q3_check"], f"{label}.q3_check")

    state = report["state_exact_checks"]
    require(isinstance(state, dict), f"{label}.state_exact_checks is not an object")
    state_names = {
        "action_context",
        "victim_tokens_columns_0_4",
        "victim_tokens_column_5",
        "victim_tokens_column_5_masked_exact",
        "action_mask",
        "victim_mask",
        "positive_credit_compatible",
        "reference_actions",
    }
    require(state_names.issubset(state), f"{label}.state_exact_checks omits a state gate")
    state_results = [
        comparison_report(state[name], f"{label}.state_exact_checks.{name}")
        for name in sorted(state_names)
    ]
    state_pass = all(state_results)

    focal = report["focal_exclusion"]
    require(isinstance(focal, dict), f"{label}.focal_exclusion is not an object")
    focal_count = nonnegative_int(focal.get("cached_focal_rate_zero_violations"), f"{label}.focal_exclusion.cached_focal_rate_zero_violations")
    require(isinstance(focal.get("delta_diagonal_exact_zero"), bool), f"{label}.focal_exclusion delta flag is not boolean")
    require(isinstance(focal.get("victim_diagonal_r1_exact_false"), bool), f"{label}.focal_exclusion R1 victim flag is not boolean")
    require(isinstance(focal.get("victim_diagonal_r2_exact_false"), bool), f"{label}.focal_exclusion R2 victim flag is not boolean")
    focal_pass = focal_count == 0 and focal["delta_diagonal_exact_zero"] and focal["victim_diagonal_r1_exact_false"] and focal["victim_diagonal_r2_exact_false"]

    branches = report["branch_maps"]
    require(isinstance(branches, dict), f"{label}.branch_maps is not an object")
    branch_violations = nonnegative_int(branches.get("violations"), f"{label}.branch_maps.violations")
    duplicate_count = nonnegative_int(branches.get("duplicate_branch_vector_count"), f"{label}.branch_maps.duplicate_branch_vector_count")
    inconsistent_count = nonnegative_int(branches.get("inconsistent_duplicate_array_count"), f"{label}.branch_maps.inconsistent_duplicate_array_count")
    require(isinstance(branches.get("worst"), list), f"{label}.branch_maps.worst is not a list")
    branch_pass = branch_violations == 0 and inconsistent_count == 0
    del duplicate_count

    clamp = report["clamp_invariant"]
    require(isinstance(clamp, dict), f"{label}.clamp_invariant is not an object")
    nonnegative_int(clamp.get("activation_count"), f"{label}.clamp_invariant.activation_count")
    clamp_violations = nonnegative_int(clamp.get("violations"), f"{label}.clamp_invariant.violations")
    require(isinstance(clamp.get("worst"), list), f"{label}.clamp_invariant.worst is not a list")
    clamp_pass = clamp_violations == 0

    coupling = report["coupling_coverage"]
    require(isinstance(coupling, dict), f"{label}.coupling_coverage is not an object")
    for field in ("coupled_entries", "zero_coupling_entries", "zero_coupling_load_unchanged_entries", "changed_key_checks", "changed_key_missing_from_cache"):
        nonnegative_int(coupling.get(field), f"{label}.coupling_coverage.{field}")
    require(isinstance(coupling.get("changed_key_missing_from_cache"), int), f"{label}.coupling missing count is invalid")
    coupling_reports = [
        comparison_report(coupling.get("zero_coupling_delta_exact"), f"{label}.coupling.zero_coupling_delta_exact"),
        comparison_report(coupling.get("zero_coupling_delta_zero"), f"{label}.coupling.zero_coupling_delta_zero"),
        comparison_report(coupling.get("zero_coupling_interference_exact"), f"{label}.coupling.zero_coupling_interference_exact"),
    ]
    coupling_pass = coupling["changed_key_missing_from_cache"] == 0 and all(coupling_reports)

    victim = report["victim_predicate"]
    require(isinstance(victim, dict), f"{label}.victim_predicate is not an object")
    victim_independent = comparison_report(victim.get("independent_match"), f"{label}.victim_predicate.independent_match")
    same_cell_checks = nonnegative_int(victim.get("same_cell_checks"), f"{label}.victim_predicate.same_cell_checks")
    same_cell_violations = nonnegative_int(victim.get("same_cell_cochannel_violations"), f"{label}.victim_predicate.same_cell_cochannel_violations")
    colour_checks = nonnegative_int(victim.get("different_colour_checks"), f"{label}.victim_predicate.different_colour_checks")
    colour_violations = nonnegative_int(victim.get("different_colour_cochannel_violations"), f"{label}.victim_predicate.different_colour_cochannel_violations")
    require(isinstance(victim.get("same_cell_checks"), int), f"{label}.victim same-cell count is invalid")
    require(isinstance(victim.get("different_colour_checks"), int), f"{label}.victim colour count is invalid")
    require(isinstance(victim.get("same_cell_cochannel_violations"), int), f"{label}.victim same-cell violations are invalid")
    require(isinstance(victim.get("different_colour_cochannel_violations"), int), f"{label}.victim colour violations are invalid")
    victim_pass = victim_independent and same_cell_violations == 0 and colour_violations == 0
    del same_cell_checks, colour_checks

    computed = bool(
        primitive_pass
        and delta_pass
        and q3_pass
        and state_pass
        and focal_pass
        and branch_pass
        and clamp_pass
        and coupling_pass
        and victim_pass
        and score_check["scores_finite_on_legal_actions"]
        and report["selected_actions_equal"]
    )
    require(report["pass"] is computed, f"{label}.pass does not match its nested acceptance gates")
    return computed


def validate_context_error(report: object, context: int) -> None:
    label = f"context {context} error report"
    require(isinstance(report, dict), f"{label} is not an object")
    require(report.get("pass") is False, f"{label} must be STOP")
    require(report.get("context_code") == context, f"{label} context code mismatch")
    require(report.get("comparison_completed") is False, f"{label} completion flag is not false")
    require(isinstance(report.get("error_type"), str) and report["error_type"], f"{label} error type is missing")
    require(isinstance(report.get("error"), str) and report["error"], f"{label} error text is missing")
    require(isinstance(report.get("traceback"), str) and report["traceback"], f"{label} traceback is missing")


def _derived_preflight_paths(result_path: Path) -> tuple[Path | None, Path | None]:
    if result_path.parent.name != "result":
        return None, None
    root = result_path.parent.parent
    return root / "server-preflight.receipt", root / "server-preflight.log"


def verify(
    result_location: Path,
    *,
    repo_root: Path,
    contract_path: Path,
    code_manifest_path: Path,
    expected_code_manifest_sha256: str,
    preflight_receipt_path: Path | None = None,
    preflight_log_path: Path | None = None,
) -> dict[str, Any]:
    location = result_location
    require(location.exists() and not location.is_symlink(), "result location is missing or symlinked")
    result_path = location / "result.json" if location.is_dir() else location
    require(result_path.name == "result.json", "result path must be result.json or its containing directory")
    regular_file(result_path, "R4 equivalence result")
    receipt_path = result_path.with_name("receipt.json")
    result = load_json(result_path, "R4 result")
    receipt = load_json(receipt_path, "R4 receipt")
    require(isinstance(result, dict), "R4 result is not an object")
    require(isinstance(receipt, dict), "R4 receipt is not an object")
    result_digest = sha256(result_path)
    require(receipt.get("result_sha256") == result_digest, "receipt result SHA-256 mismatch")
    require(receipt.get("schema") == EXPECTED_RECEIPT_SCHEMA, "receipt schema drifted")
    require(result.get("schema") == EXPECTED_SCHEMA, "result schema drifted")
    require(result.get("execution_attempt") == EXPECTED_EXECUTION_ATTEMPT, "execution attempt is not R4")
    decision = result.get("decision")
    require(decision in {PASS_DECISION, STOP_DECISION}, "unexpected R4 decision")
    require(isinstance(result.get("passed"), bool), "R4 passed flag is not boolean")
    require(result.get("split") == "TRAIN_PREVIOUSLY_OPENED", "split boundary drifted")
    for field in ("test_split_opened", "action_executed", "exact_teacher_opened", "learner_update", "episode_training"):
        require(result.get(field) is False, f"forbidden execution flag is true: {field}")
    require(result.get("world_seed") == EXPECTED_WORLD, "world seed drifted")
    require(result.get("lineage") == EXPECTED_LINEAGE, "lineage drifted")
    require(result.get("users") == EXPECTED_USERS, "user count drifted")
    require(tuple(result.get("contexts", ())) == EXPECTED_CONTEXTS, "context set/order drifted")
    workers = result.get("workers")
    require(isinstance(workers, int) and not isinstance(workers, bool) and 1 <= workers <= EXPECTED_MAX_WORKERS, "worker count is invalid")
    tle_root = result.get("tle_root")
    require(isinstance(tle_root, str) and tle_root.startswith("/"), "TLE root is not absolute")
    if "live_state_rng_unchanged" in result:
        require(result["live_state_rng_unchanged"] is True, "result records changed live state/RNG")
    if decision == PASS_DECISION:
        require(result.get("field_component"), "PASS result is missing the keyed fading field component")
        for field in ("tle_file_set_sha256", "initial_world_sha256", "initial_live_state_rng_sha256"):
            sha_field(result.get(field), f"result.{field}")
    else:
        for field in ("tle_file_set_sha256", "initial_world_sha256", "initial_live_state_rng_sha256"):
            if field in result and result[field] is not None:
                sha_field(result[field], f"result.{field}")

    closure = verify_code_closure(
        repo_root=repo_root,
        contract_path=contract_path,
        code_manifest_path=code_manifest_path,
        expected_code_manifest_sha256=expected_code_manifest_sha256,
    )
    for field, expected in closure.items():
        if field not in result:
            if field == "prereg_sha256" and decision == STOP_DECISION:
                continue
            require(False, f"R4 result omits {field}")
        value = result.get(field)
        if value is None and decision == STOP_DECISION and field == "prereg_sha256":
            continue
        require(sha_field(value, f"result.{field}") == expected, f"result.{field} disagrees with frozen closure")
    if "code_manifest_sha256_expected" in result:
        require(result["code_manifest_sha256_expected"] == EXPECTED_CODE_MANIFEST_SHA256, "expected code-manifest field drifted")

    # The runner binds these external hashes after the server preflight.  When
    # validating a direct early STOP without those files, null hashes are
    # retained as an execution failure; a finalized artifact must include and
    # authenticate the preflight pair.
    derived_receipt, derived_log = _derived_preflight_paths(result_path)
    preflight_receipt_path = preflight_receipt_path or derived_receipt
    preflight_log_path = preflight_log_path or derived_log
    have_receipt = preflight_receipt_path is not None and preflight_receipt_path.exists()
    have_log = preflight_log_path is not None and preflight_log_path.exists()
    require(have_receipt == have_log, "preflight receipt/log presence is asymmetric")
    external: dict[str, str] = {}
    if have_receipt:
        assert preflight_receipt_path is not None and preflight_log_path is not None
        external = verify_preflight(
            preflight_receipt_path=preflight_receipt_path,
            preflight_log_path=preflight_log_path,
            expected_manifest_sha256=EXPECTED_CODE_MANIFEST_SHA256,
        )
        for field, expected in external.items():
            require(result.get(field) == expected, f"result.{field} does not authenticate preflight closure")
            require(receipt.get(field) == expected, f"receipt.{field} does not authenticate preflight closure")
    elif decision == PASS_DECISION:
        raise VerificationError("PASS result has no authenticated server preflight closure")

    common_receipt_fields = (
        "contract_sha256",
        "code_manifest_sha256",
        "runner_sha256",
        "r1_source_sha256",
        "r2_source_sha256",
        "prereg_sha256",
        "world_seed",
        "lineage",
        "test_split_opened",
        "action_executed",
        "learner_update",
        "episode_training",
        "decision",
    )
    for field in common_receipt_fields:
        if field in receipt:
            if field in result:
                require(receipt[field] == result[field], f"receipt.{field} disagrees with result")
        elif decision == PASS_DECISION or field in {"contract_sha256", "code_manifest_sha256", "runner_sha256", "r1_source_sha256", "r2_source_sha256", "decision"}:
            require(False, f"receipt omits {field}")
    for field in ("preflight_receipt_sha256", "preflight_log_sha256"):
        if field in receipt and field in result:
            require(receipt[field] == result[field], f"receipt.{field} disagrees with result")

    for field in ("q1_checkpoint", "q2_checkpoint"):
        if field in result:
            validate_checkpoint(result[field], f"result.{field}")
        elif decision == PASS_DECISION:
            raise VerificationError(f"PASS result omits {field}")

    reports = result.get("reports")
    context_passes: dict[str, bool] = {}
    if reports is None:
        require(decision == STOP_DECISION, "result without context reports cannot PASS")
        require(isinstance(result.get("error"), str) and result["error"], "STOP without reports lacks error")
    else:
        require(isinstance(reports, dict), "reports is not an object")
        expected_keys = {str(context) for context in EXPECTED_CONTEXTS}
        require(set(reports) == expected_keys, "reports must contain exactly the three frozen contexts")
        for context in EXPECTED_CONTEXTS:
            report = reports[str(context)]
            if isinstance(report, dict) and report.get("comparison_completed") is False:
                validate_context_error(report, context)
                context_passes[str(context)] = False
            else:
                context_passes[str(context)] = validate_full_context(report, context)
    all_contexts_pass = bool(context_passes) and all(context_passes.values())
    expected_decision = PASS_DECISION if all_contexts_pass else STOP_DECISION
    require(decision == expected_decision, "PASS/STOP decision is inconsistent with context gates")
    require(result["passed"] is all_contexts_pass, "passed flag is inconsistent with context gates")

    # A STOP is a valid negative execution receipt, but it remains explicitly
    # negative in this independent report and never becomes an efficacy claim.
    return {
        "verified": True,
        "decision": decision,
        "passed": result["passed"],
        "result_sha256": result_digest,
        "contract_sha256": EXPECTED_CONTRACT_SHA256,
        "code_manifest_sha256": EXPECTED_CODE_MANIFEST_SHA256,
        "world_seed": EXPECTED_WORLD,
        "lineage": EXPECTED_LINEAGE,
        "users": EXPECTED_USERS,
        "contexts": list(EXPECTED_CONTEXTS),
        "preflight_authenticated": bool(external),
        "context_passes": context_passes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="result directory or result.json")
    parser.add_argument("--repo-root", type=Path, default=REPO)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--code-manifest", type=Path, default=DEFAULT_CODE_MANIFEST)
    parser.add_argument("--preflight-receipt", type=Path, default=None)
    parser.add_argument("--preflight-log", type=Path, default=None)
    parser.add_argument(
        "--code-manifest-sha256",
        default=os.environ.get("V018E_MANIFEST_SHA256", EXPECTED_CODE_MANIFEST_SHA256),
        help="explicit SHA-256 of the frozen R4 code manifest",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract if args.contract.is_absolute() else repo_root / args.contract
    code_manifest_path = args.code_manifest if args.code_manifest.is_absolute() else repo_root / args.code_manifest
    try:
        sha_field(args.code_manifest_sha256, "expected code-manifest digest")
        report = verify(
            args.result,
            repo_root=repo_root,
            contract_path=contract_path,
            code_manifest_path=code_manifest_path,
            expected_code_manifest_sha256=args.code_manifest_sha256,
            preflight_receipt_path=args.preflight_receipt,
            preflight_log_path=args.preflight_log,
        )
    except (OSError, VerificationError, ValueError) as error:
        print(json.dumps({"verified": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
