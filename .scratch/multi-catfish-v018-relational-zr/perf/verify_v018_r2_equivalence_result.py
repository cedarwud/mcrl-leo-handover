#!/usr/bin/env python3
"""Validate a completed V0.18 R3 cache-equivalence result.

This checker is deliberately independent of the equivalence runner: it uses
only the Python standard library, reads the persisted JSON/receipt and the
locally frozen contract/code manifest, and never imports the simulator or
opens a result-producing path.  A valid STOP receipt is retained as a valid
negative execution receipt; it is never converted into a PASS.
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
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT = REPO / (
    ".scratch/multi-catfish-v018-relational-zr/contracts/"
    "MULTI-CATFISH-MCRL-V018-R3-CACHE-EQUIVALENCE-CHECK-2026-09-04.md"
)
DEFAULT_CODE_MANIFEST = REPO / (
    ".scratch/multi-catfish-v018-relational-zr/contracts/"
    "code-manifest-r2-equivalence.sha256"
)

EXPECTED_SCHEMA = "multi-catfish-mcrl-v018-r2-cache-equivalence-v1"
EXPECTED_EXECUTION_ATTEMPT = "r3"
EXPECTED_CONTRACT_STATUS = "Status: `FROZEN_BEFORE_CHECK`"
EXPECTED_CONTRACT_SHA256 = (
    "2cd580080435a7809d8b9a565cd5906ad06e02d21f6cf8d16300a6f4b55d7c29"
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
    "verify_v018_r2_cache_equivalence.py"
)
CONTRACT_RELATIVE = (
    ".scratch/multi-catfish-v018-relational-zr/contracts/"
    "MULTI-CATFISH-MCRL-V018-R3-CACHE-EQUIVALENCE-CHECK-2026-09-04.md"
)
PREREG_RELATIVE = "artifacts/PREREG-FROZEN-2026-08-25-R2.json"

# The frozen runner applies both relative and absolute tolerances to the full
# arrays.  Its result persists only maximum absolute deviations, without the
# corresponding element magnitudes, so a second checker cannot correctly
# reconstruct ``atol + rtol*abs(expected)`` from those maxima alone.  The
# runner hash is authenticated below; here we validate that its persisted
# deviation diagnostics are finite and non-negative.


class VerificationError(RuntimeError):
    """The persisted result is not consistent with the frozen closure."""


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
    require(path.exists() and not path.is_symlink(), f"missing or symlinked {description}: {path}")
    require(path.is_file(), f"{description} is not a regular file: {path}")
    return path


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


def sha_field(value: object, field: str) -> str:
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
            f"{field} must be a lowercase SHA-256")
    return value


def parse_manifest(path: Path) -> dict[str, str]:
    """Read a sha256sum-style manifest without executing sha256sum."""

    entries: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
        require(match is not None, f"malformed code-manifest line {number}")
        assert match is not None
        digest, relative = match.groups()
        require(not relative.startswith("/"), f"absolute code-manifest path: {relative}")
        require(relative not in entries, f"duplicate code-manifest path: {relative}")
        entries[relative] = digest
    require(entries, "code manifest is empty")
    return entries


def resolve_repo_path(repo_root: Path, relative: str) -> Path:
    candidate = repo_root / relative
    require(candidate.parent.resolve().is_relative_to(repo_root.resolve()),
            f"repository path escapes root: {relative}")
    return candidate


def contract_identities(contract_path: Path) -> dict[str, str]:
    text = contract_path.read_text(encoding="utf-8")
    require(EXPECTED_CONTRACT_STATUS in text, "equivalence contract is not frozen before check")
    patterns = {
        "r1_source_sha256": r"independent sealed R1 source file must hash to\s*`([0-9a-f]{64})`",
        "runner_sha256": r"- equivalence runner:\s*`([0-9a-f]{64})`",
        "r2_source_sha256": r"- R2 cached runtime:\s*`([0-9a-f]{64})`",
    }
    identities: dict[str, str] = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text)
        require(match is not None, f"contract does not record {field}")
        assert match is not None
        identities[field] = match.group(1)
    return identities


def verify_code_closure(
    *,
    repo_root: Path,
    contract_path: Path,
    code_manifest_path: Path,
    expected_code_manifest_sha256: str,
    result: dict[str, Any],
) -> dict[str, str]:
    regular_file(contract_path, "frozen equivalence contract")
    regular_file(code_manifest_path, "R2 code manifest")
    require(
        sha256(code_manifest_path) == expected_code_manifest_sha256,
        "R2 code-manifest digest mismatch",
    )
    manifest = parse_manifest(code_manifest_path)
    identities = contract_identities(contract_path)
    expected = {
        CONTRACT_RELATIVE: EXPECTED_CONTRACT_SHA256,
        R1_RELATIVE: identities["r1_source_sha256"],
        R2_RELATIVE: identities["r2_source_sha256"],
        RUNNER_RELATIVE: identities["runner_sha256"],
        PREREG_RELATIVE: EXPECTED_PREREG_SHA256,
    }
    result_to_path = {
        "r1_source_sha256": R1_RELATIVE,
        "r2_source_sha256": R2_RELATIVE,
        "runner_sha256": RUNNER_RELATIVE,
        "prereg_sha256": PREREG_RELATIVE,
    }
    for relative, expected_digest in expected.items():
        require(relative in manifest, f"code manifest omits required file: {relative}")
        require(manifest[relative] == expected_digest,
                f"code manifest identity disagrees with frozen contract: {relative}")
        file_path = regular_file(resolve_repo_path(repo_root, relative), relative)
        actual = sha256(file_path)
        require(actual == expected_digest, f"current file hash mismatch: {relative}")
    for result_field, relative in result_to_path.items():
        # The runner's fail-closed STOP receipt is intentionally emitted from
        # the exception path before the preregistration has been opened, so
        # that path does not carry prereg_sha256.  A PASS receipt must carry
        # every identity; a STOP may omit only that not-opened prereg field.
        if result_field not in result:
            require(result_field == "prereg_sha256",
                    f"result omits {result_field}")
            continue
        require(sha_field(result[result_field], result_field) == expected[relative],
                f"result {result_field} disagrees with current code closure")
    return {
        "contract_sha256": sha256(contract_path),
        "code_manifest_sha256": sha256(code_manifest_path),
        **identities,
        "prereg_sha256": EXPECTED_PREREG_SHA256,
    }


def verify_report(report: object, *, context: int, users: int) -> dict[str, Any]:
    require(isinstance(report, dict), f"context {context} report is not an object")
    required = {
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
    }
    require(required.issubset(report), f"context {context} report fields are incomplete")
    legal = report["legal_branch_count"]
    unique = report["unique_branch_vector_count"]
    checked = report["checked_nonfocal_rate_and_interference_values"]
    require(isinstance(legal, int) and not isinstance(legal, bool) and legal > 0,
            f"context {context} legal branch count is invalid")
    require(isinstance(unique, int) and not isinstance(unique, bool) and 1 <= unique <= legal + 1,
            f"context {context} unique branch count is invalid")
    require(isinstance(checked, int) and not isinstance(checked, bool)
            and checked == legal * (users - 1),
            f"context {context} non-focal count is inconsistent")
    finite_number(report["reference_reconstruction_elapsed_s"],
                  f"context {context} reconstruction time", nonnegative=True)

    rate_deviation = finite_number(report["maximum_nonfocal_rate_deviation_bps"],
                                   f"context {context} rate deviation", nonnegative=True)
    interference_deviation = finite_number(
        report["maximum_nonfocal_interference_deviation_w"],
        f"context {context} interference deviation",
        nonnegative=True,
    )

    deviations = report["maximum_absolute_deviation"]
    require(isinstance(deviations, dict), f"context {context} deviation summary is not an object")
    expected_fields = {"delta", "q3", "action_context", "victim_tokens"}
    require(set(deviations) == set(expected_fields),
            f"context {context} deviation field set drifted")
    for field in expected_fields:
        value = finite_number(deviations[field], f"context {context} {field} deviation",
                              nonnegative=True)

    require(isinstance(report["state_content_digest_equal"], bool),
            f"context {context} digest diagnostic is not boolean")
    require(report["selected_actions_equal"] is True,
            f"context {context} selected actions are not equal")
    sha_field(report["selected_action_sha256"], f"context {context} selected action digest")
    finite_number(report["maximum_score_deviation"],
                  f"context {context} score deviation", nonnegative=True)

    margin = report["minimum_top_two_margin"]
    require(isinstance(margin, (int, float)) and not isinstance(margin, bool)
            and (math.isfinite(float(margin)) or float(margin) == math.inf)
            and float(margin) >= 0.0,
            f"context {context} top-two margin is invalid")
    ratio = report["margin_to_deviation_ratio"]
    require(isinstance(ratio, (int, float)) and not isinstance(ratio, bool)
            and (math.isfinite(float(ratio)) or float(ratio) == math.inf)
            and float(ratio) >= 0.0,
            f"context {context} margin ratio is invalid")
    score_deviation = float(report["maximum_score_deviation"])
    if score_deviation == 0.0:
        require(float(ratio) == math.inf,
                f"context {context} zero score deviation must report infinite ratio")
    else:
        require(math.isfinite(float(ratio)),
                f"context {context} nonzero score deviation has infinite ratio")
    return {
        "legal_branch_count": legal,
        "unique_branch_vector_count": unique,
        "checked_nonfocal_rate_and_interference_values": checked,
        "maximum_absolute_deviation": deviations,
        "selected_actions_equal": True,
    }


def verify(result_location: Path, *, repo_root: Path, contract_path: Path,
           code_manifest_path: Path, expected_code_manifest_sha256: str) -> dict[str, Any]:
    location = result_location
    require(location.exists() and not location.is_symlink(), "result location is missing or symlinked")
    result_path = location / "result.json" if location.is_dir() else location
    require(result_path.name == "result.json", "result path must be result.json or its containing directory")
    regular_file(result_path, "equivalence result")
    receipt_path = result_path.with_name("receipt.json")
    regular_file(receipt_path, "equivalence receipt")
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"invalid result or receipt JSON: {error}") from error
    require(isinstance(result, dict), "result JSON is not an object")
    require(isinstance(receipt, dict), "receipt JSON is not an object")

    result_digest = sha256(result_path)
    require(receipt.get("result_sha256") == result_digest, "result SHA-256 mismatch")
    require(receipt.get("decision") == result.get("decision"), "receipt decision mismatch")
    require(receipt.get("contract_sha256") == result.get("contract_sha256"),
            "receipt contract hash mismatch")
    require(result.get("schema") == EXPECTED_SCHEMA, "result schema drifted")
    require(result.get("execution_attempt") == EXPECTED_EXECUTION_ATTEMPT,
            "execution attempt is not the frozen R3 attempt")
    decision = result.get("decision")
    require(decision in {"PASS_R2_CACHE_EQUIVALENCE", "STOP_R2_CACHE_EQUIVALENCE"},
            "unexpected equivalence decision")
    require(isinstance(result.get("passed"), bool), "passed flag is not boolean")
    require(result["passed"] is (decision == "PASS_R2_CACHE_EQUIVALENCE"),
            "PASS/STOP decision is inconsistent with passed flag")
    require(result.get("split") == "TRAIN_PREVIOUSLY_OPENED", "split boundary drifted")

    for field in ("test_split_opened", "action_executed", "exact_teacher_opened",
                  "learner_update", "episode_training"):
        require(result.get(field) is False, f"forbidden execution flag is true: {field}")
    require(result.get("world_seed") == EXPECTED_WORLD, "world seed drifted")
    require(result.get("lineage") == EXPECTED_LINEAGE, "lineage drifted")
    require(result.get("users") == EXPECTED_USERS, "user count drifted")
    require(tuple(result.get("contexts", ())) == EXPECTED_CONTEXTS, "context set/order drifted")
    workers = result.get("workers")
    require(isinstance(workers, int) and not isinstance(workers, bool)
            and 1 <= workers <= EXPECTED_MAX_WORKERS, "worker count is invalid")
    tle_root = result.get("tle_root")
    require(isinstance(tle_root, str) and tle_root.startswith("/"), "TLE root is not absolute")
    for field in ("contract_sha256",):
        sha_field(result.get(field), field)
    optional_execution_fields = (
        "prereg_sha256",
        "tle_file_set_sha256",
        "initial_world_sha256",
        "initial_live_state_rng_sha256",
    )
    for field in optional_execution_fields:
        if field in result:
            sha_field(result[field], field)
    if decision == "PASS_R2_CACHE_EQUIVALENCE":
        for field in optional_execution_fields:
            require(field in result, f"PASS result omits {field}")
        require(result["prereg_sha256"] == EXPECTED_PREREG_SHA256,
                "preregistration hash drifted")
        require(isinstance(result.get("field_component"), str)
                and bool(result["field_component"]), "field component is missing")
    elif "prereg_sha256" in result:
        require(result["prereg_sha256"] == EXPECTED_PREREG_SHA256,
                "STOP result preregistration hash drifted")

    closure = verify_code_closure(
        repo_root=repo_root,
        contract_path=contract_path,
        code_manifest_path=code_manifest_path,
        expected_code_manifest_sha256=expected_code_manifest_sha256,
        result=result,
    )
    require(result["contract_sha256"] == closure["contract_sha256"],
            "result contract hash disagrees with current frozen contract")

    live_unchanged = result.get("live_state_rng_unchanged")
    if decision == "PASS_R2_CACHE_EQUIVALENCE":
        require(live_unchanged is True, "PASS result does not attest unchanged live state/RNG")
        reports = result.get("reports")
        require(isinstance(reports, dict), "PASS result has no reports")
        require(set(reports) == {str(code) for code in EXPECTED_CONTEXTS},
                "PASS report context set drifted")
        summaries: dict[str, Any] = {}
        expected_legal: int | None = None
        for context in EXPECTED_CONTEXTS:
            summary = verify_report(reports[str(context)], context=context, users=EXPECTED_USERS)
            if expected_legal is None:
                expected_legal = summary["legal_branch_count"]
            require(summary["legal_branch_count"] == expected_legal,
                    "legal branch count differs across contexts")
            summaries[str(context)] = summary
    else:
        # The runner's exception receipt predates its live-state assertion and
        # therefore may not contain reports.  Preserve that as an explicitly
        # unproven STOP, never as a scientific or implementation PASS.
        if live_unchanged is not None:
            require(live_unchanged is True, "STOP result records changed live state/RNG")
        reports = result.get("reports")
        summaries = {}
        if reports is not None:
            require(isinstance(reports, dict), "STOP reports are not an object")
            require(set(reports) == {str(code) for code in EXPECTED_CONTEXTS},
                    "STOP report context set drifted")
            expected_legal = None
            for context in EXPECTED_CONTEXTS:
                summary = verify_report(reports[str(context)], context=context, users=EXPECTED_USERS)
                if expected_legal is None:
                    expected_legal = summary["legal_branch_count"]
                require(summary["legal_branch_count"] == expected_legal,
                        "legal branch count differs across STOP contexts")
                summaries[str(context)] = summary
        require(isinstance(result.get("error"), str) and bool(result["error"]),
                "STOP result has neither reports nor an error reason")

    return {
        "verified": True,
        "decision": decision,
        "passed": result["passed"],
        "result_sha256": result_digest,
        "contract_sha256": closure["contract_sha256"],
        "code_manifest_sha256": closure["code_manifest_sha256"],
        "world_seed": EXPECTED_WORLD,
        "lineage": EXPECTED_LINEAGE,
        "users": EXPECTED_USERS,
        "contexts": list(EXPECTED_CONTEXTS),
        "live_state_rng_unchanged": live_unchanged is True,
        "reports": summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="result directory or result.json")
    parser.add_argument("--repo-root", type=Path, default=REPO)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--code-manifest", type=Path, default=DEFAULT_CODE_MANIFEST)
    parser.add_argument(
        "--code-manifest-sha256",
        default=os.environ.get("V018E_MANIFEST_SHA256"),
        help="explicit SHA-256 of the current frozen code manifest (or V018E_MANIFEST_SHA256)",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    contract_path = args.contract
    code_manifest_path = args.code_manifest
    if not contract_path.is_absolute():
        contract_path = repo_root / contract_path
    if not code_manifest_path.is_absolute():
        code_manifest_path = repo_root / code_manifest_path
    try:
        require(args.code_manifest_sha256 is not None,
                "an explicit code-manifest digest is required")
        sha_field(args.code_manifest_sha256, "expected code-manifest digest")
        report = verify(
            args.result,
            repo_root=repo_root,
            contract_path=contract_path,
            code_manifest_path=code_manifest_path,
            expected_code_manifest_sha256=args.code_manifest_sha256,
        )
    except (OSError, VerificationError, ValueError) as error:
        print(json.dumps({"verified": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
