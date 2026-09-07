#!/usr/bin/env python3
"""Independent, fail-closed validation for the deterministic C1 Gate 2 receipt."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from c1_exp_corpus import load_verified_c1_corpus, sha256_file  # noqa: E402
from check_zero_dose_parity import (  # noqa: E402
    SCHEMA as ZERO_DOSE_SCHEMA,
    validate_receipt as validate_zero_dose_receipt,
)
from mcrl.artifacts import read_checkpoint  # noqa: E402
from run_c1_pretransfer_consumer_gate import (  # noqa: E402
    ATOL,
    CLAIM_CEILING,
    RAW_SCHEMA,
    RESULT_SCHEMA,
    RTOL,
    evaluate_gate,
)


EXPECTED_CHECKS = {
    "zero_dose_exact_pass",
    "production_matches_independent_reference",
    "private_signal_and_provenance_invariant",
    "isolated_row_gradient_has_no_atomic_credit_reversal",
    "executed_vs_frozen_main_preference_has_no_reversal",
    "noop_row_has_zero_hidden_weight",
    "row_permutation_invariant",
    "all_admissible_rows_counted_once",
    "durable_duplicate_rejected_after_resume",
}


class C1PretransferGateValidationError(RuntimeError):
    """Raised when the C1 pre-transfer receipt cannot be established."""

    def __init__(self, failures: list[str], *, evidence: Mapping[str, Any] | None = None):
        self.failures = tuple(dict.fromkeys(failures))
        self.evidence = dict(evidence or {})
        super().__init__("C1 pre-transfer gate validation failed: " + "; ".join(self.failures))


def _json(path: Path, label: str, failures: list[str]) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: unreadable ({type(exc).__name__})")
        return None
    if not isinstance(value, Mapping):
        failures.append(f"{label}: object required")
        return None
    return value


def _digest(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _resolve(value: Any, *, base: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _close(left: Any, right: Any) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=RTOL, abs_tol=ATOL)
    except (TypeError, ValueError, OverflowError):
        return False


def _canonical_authorities(repo: Path) -> dict[str, Path]:
    short = repo / ".scratch" / "smc-er-short-ep"
    return {
        "spec": short / "C1-PRETRANSFER-CONSUMER-GATE-V1-SPEC-2026-08-28.md",
        "runner": short / "run_c1_pretransfer_consumer_gate.py",
        "test": short / "test_c1_pretransfer_consumer_gate.py",
        "validator": short / "c1_pretransfer_gate_validator.py",
        "validator_test": short / "test_c1_pretransfer_gate_validator.py",
        "method": repo / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md",
        "routing_core": short / "smc_er_core.py",
        "corpus_loader": short / "c1_exp_corpus.py",
        "parity_checker": short / "check_zero_dose_parity.py",
        "run_short_ep": short / "run_short_ep.py",
    }


def _bound_file(
    authority: Mapping[str, Any],
    stem: str,
    *,
    base: Path,
    result_path: Path,
    failures: list[str],
) -> Path | None:
    path = _resolve(authority.get(stem + "_path"), base=base)
    expected = authority.get(stem + "_sha256")
    if path is None:
        failures.append(f"authority.{stem}_path: missing")
        return None
    if path == result_path:
        failures.append(f"authority.{stem}_path: self-reference forbidden")
        return None
    if not path.is_file():
        failures.append(f"authority.{stem}_path: file missing")
        return None
    if not _digest(expected) or sha256_file(path) != expected:
        failures.append(f"authority.{stem}_sha256: mismatch")
        return None
    return path


def _validate_raw_structure(raw: Mapping[str, Any], failures: list[str]) -> None:
    if raw.get("schema") != RAW_SCHEMA or raw.get("status") != "complete":
        failures.append("raw.schema/status: mismatch")
    if raw.get("claim_ceiling") != CLAIM_CEILING:
        failures.append("raw.claim_ceiling: mismatch")
    checks = raw.get("checks")
    if not isinstance(checks, Mapping) or set(checks) != EXPECTED_CHECKS:
        failures.append("raw.checks: exact check surface required")

    reference = raw.get("reference")
    if not isinstance(reference, Mapping):
        failures.append("raw.reference: missing")
    else:
        left = reference.get("production_losses")
        right = reference.get("reference_losses")
        if (
            not isinstance(left, list)
            or not isinstance(right, list)
            or len(left) != 3
            or len(right) != 3
            or any(not _finite(value) for value in [*left, *right])
            or not np.allclose(left, right, rtol=RTOL, atol=ATOL)
            or reference.get("state_equal") is not True
            or reference.get("first_difference") is not None
        ):
            failures.append("raw.reference: independent state/loss mismatch")

    alias = raw.get("private_alias")
    if not isinstance(alias, Mapping):
        failures.append("raw.private_alias: missing")
    else:
        left = alias.get("left_losses")
        right = alias.get("right_losses")
        if (
            not isinstance(left, list)
            or not isinstance(right, list)
            or len(left) != 3
            or len(right) != 3
            or not np.allclose(left, right, rtol=0.0, atol=0.0)
            or alias.get("state_equal") is not True
            or alias.get("canonical_bundle_equal") is not True
            or alias.get("private_rewards_differ") is not True
            or alias.get("hidden_trigger_labels_differ") is not True
        ):
            failures.append("raw.private_alias: leakage or malformed fixture")

    gradient_rows = raw.get("gradient_rows")
    if (
        not isinstance(gradient_rows, list)
        or len(gradient_rows) != 3
        or [row.get("objective") for row in gradient_rows if isinstance(row, Mapping)]
        != [0, 1, 2]
    ):
        failures.append("raw.gradient_rows: exact three-objective fixture required")
    else:
        for index, row in enumerate(gradient_rows):
            if (
                not isinstance(row, Mapping)
                or not _finite(row.get("focal_delta_norm"))
                or not _finite(row.get("atomic_delta_norm"))
                or float(row.get("focal_delta_norm", 0.0)) <= ATOL
                or float(row.get("atomic_delta_norm", 0.0)) <= ATOL
                or not _finite(row.get("dot_product"))
                or float(row.get("dot_product", -1.0)) < -ATOL
                or row.get("nonnegative") is not True
            ):
                failures.append(f"raw.gradient_rows[{index}]: credit reversal/non-informative")

    preference = raw.get("preference_perturbation")
    if not isinstance(preference, Mapping):
        failures.append("raw.preference_perturbation: missing")
    else:
        focal_delta = preference.get("focal_delta")
        atomic_delta = preference.get("atomic_delta")
        product = preference.get("direction_product")
        if (
            preference.get("informative") is not True
            or preference.get("non_reversal") is not True
            or preference.get("executed_action")
            == preference.get("frozen_main_comparator_action")
            or not all(_finite(value) for value in (focal_delta, atomic_delta, product))
            or abs(float(focal_delta)) <= ATOL
            or abs(float(atomic_delta)) <= ATOL
            or not _close(product, float(focal_delta) * float(atomic_delta))
            or float(product) < -ATOL
        ):
            failures.append("raw.preference_perturbation: preference reversal/non-informative")

    noop = raw.get("noop_row")
    if not isinstance(noop, Mapping):
        failures.append("raw.noop_row: missing")
    else:
        left = noop.get("base_losses")
        right = noop.get("changed_losses")
        if (
            type(noop.get("excluded_row")) is not int
            or not isinstance(left, list)
            or not isinstance(right, list)
            or len(left) != 3
            or len(right) != 3
            or not np.allclose(left, right, rtol=0.0, atol=0.0)
            or noop.get("state_equal") is not True
        ):
            failures.append("raw.noop_row: hidden row weight detected")

    permutation = raw.get("permutation")
    if not isinstance(permutation, Mapping):
        failures.append("raw.permutation: missing")
    else:
        left = permutation.get("ordered_losses")
        right = permutation.get("permuted_losses")
        if (
            not isinstance(left, list)
            or not isinstance(right, list)
            or len(left) != 3
            or len(right) != 3
            or not np.allclose(left, right, rtol=RTOL, atol=ATOL)
            or permutation.get("state_equal") is not True
            or permutation.get("first_difference") is not None
        ):
            failures.append("raw.permutation: material order dependence")

    ledger = raw.get("duplicate_ledger")
    if not isinstance(ledger, Mapping):
        failures.append("raw.duplicate_ledger: missing")
    else:
        saved = ledger.get("saved_state")
        restored = ledger.get("restored_state")
        if (
            saved != restored
            or not isinstance(saved, Mapping)
            or saved.get("format_version") != 1
            or saved.get("seen_bundle_ids") != ["C1-GATE-V1-C1-FIXTURE"]
            or ledger.get("duplicate_rejected") is not True
        ):
            failures.append("raw.duplicate_ledger: durable rejection not established")


def validate_c1_pretransfer_result(
    result_path: Path,
    *,
    repo_root: Path = REPO,
    rerun_fixtures: bool = True,
) -> dict[str, Any]:
    """Validate all authorities and independently rerun deterministic fixtures."""

    result_path = Path(result_path).expanduser().resolve()
    failures: list[str] = []
    result = _json(result_path, "result", failures)
    if result is None:
        raise C1PretransferGateValidationError(failures)
    if result.get("schema") != RESULT_SCHEMA or result.get("source") != "C1":
        failures.append("result.schema/source: mismatch")
    if result.get("gate_type") != "pretransfer-representation-and-atomic-bundle":
        failures.append("result.gate_type: mismatch")
    if result.get("claim_ceiling") != CLAIM_CEILING:
        failures.append("result.claim_ceiling: mismatch")
    if result.get("prerequisites_closed") is not True:
        failures.append("result.prerequisites_closed: must be true")
    protocol = result.get("protocol")
    expected_protocol = {
        "deterministic_seedless_fixtures": True,
        "persistent_main_updated": False,
        "outcome_or_ee_selection": False,
        "authorized_source": "C1",
        "authorized_follow_on": "post-gate-4EP-developmental-carrier-efficacy-micro-screen",
        "loss_family": "canonical-Main-MSE",
        "bundle_weight": 1.0,
    }
    if protocol != expected_protocol:
        failures.append("result.protocol: mismatch")

    authority = result.get("authority")
    if not isinstance(authority, Mapping):
        failures.append("result.authority: missing")
        raise C1PretransferGateValidationError(failures, evidence={"result": dict(result)})
    repo = Path(repo_root).expanduser().resolve()
    canonical = _canonical_authorities(repo)
    recomputed: dict[str, str] = {}
    for stem, path in canonical.items():
        expected_path = _resolve(authority.get(stem + "_path"), base=result_path.parent)
        expected_digest = authority.get(stem + "_sha256")
        if expected_path != path.resolve():
            failures.append(f"authority.{stem}_path: canonical path mismatch")
        if not path.is_file():
            failures.append(f"authority.{stem}_path: canonical file missing")
            continue
        recomputed[stem] = sha256_file(path)
        if not _digest(expected_digest) or recomputed[stem] != expected_digest:
            failures.append(f"authority.{stem}_sha256: canonical digest mismatch")

    checkpoint_path = _bound_file(
        authority, "checkpoint", base=result_path.parent, result_path=result_path, failures=failures
    )
    corpus_path = _bound_file(
        authority, "corpus_manifest", base=result_path.parent, result_path=result_path, failures=failures
    )
    parity_path = _bound_file(
        authority, "zero_dose_parity", base=result_path.parent, result_path=result_path, failures=failures
    )
    raw_path = _bound_file(
        authority, "raw", base=result_path.parent, result_path=result_path, failures=failures
    )

    parity = _json(parity_path, "zero_dose_parity", failures) if parity_path else None
    if parity is not None:
        if parity.get("schema") != ZERO_DOSE_SCHEMA:
            failures.append("zero_dose_parity: current authenticated schema required")
        else:
            try:
                replayed_parity = validate_zero_dose_receipt(parity_path)
            except Exception as exc:
                failures.append(
                    "zero_dose_parity: authenticated exact replay failed "
                    f"({type(exc).__name__}: {exc})"
                )
            else:
                if dict(parity) != replayed_parity:
                    failures.append("zero_dose_parity: replay payload mismatch")

    checkpoint = None
    corpus = None
    if checkpoint_path is not None:
        try:
            checkpoint = read_checkpoint(checkpoint_path, map_location="cpu")
        except Exception as exc:
            failures.append(f"checkpoint: unreadable ({type(exc).__name__})")
    if checkpoint is not None and corpus_path is not None:
        try:
            corpus = load_verified_c1_corpus(
                corpus_path,
                expected_checkpoint_sha256=sha256_file(checkpoint_path),
                expected_state_dim=checkpoint.state_dim,
                expected_action_dim=checkpoint.action_dim,
            )
        except Exception as exc:
            failures.append(f"corpus: independent verification failed ({type(exc).__name__}: {exc})")

    raw = _json(raw_path, "raw", failures) if raw_path else None
    if raw is not None:
        _validate_raw_structure(raw, failures)
        fixtures = raw.get("fixtures")
        if not isinstance(fixtures, Mapping):
            failures.append("raw.fixtures: missing")
        elif checkpoint_path is not None and corpus is not None:
            if fixtures.get("checkpoint_sha256") != sha256_file(checkpoint_path):
                failures.append("raw.fixtures.checkpoint_sha256: mismatch")
            if fixtures.get("corpus_manifest_sha256") != corpus.manifest_sha256:
                failures.append("raw.fixtures.corpus_manifest_sha256: mismatch")
            if fixtures.get("corpus_sha256") != corpus.corpus_sha256:
                failures.append("raw.fixtures.corpus_sha256: mismatch")
            rows = fixtures.get("admissible_rows")
            if (
                fixtures.get("users") != 100
                or not isinstance(rows, list)
                or rows != list(range(100))
                or fixtures.get("focal_fixture_user") not in rows
            ):
                failures.append("raw.fixtures: user/row denominator mismatch")

    checks = result.get("checks")
    raw_checks = raw.get("checks") if raw is not None else None
    if checks != raw_checks or not isinstance(checks, Mapping) or set(checks) != EXPECTED_CHECKS:
        failures.append("result.checks: raw mismatch")
        expected_pass = False
    else:
        expected_pass = all(value is True for value in checks.values())
    expected_status = "PASS" if expected_pass else "FAIL"
    expected_decision = "ROUTE" if expected_pass else "SHADOW"
    if result.get("status") != expected_status or result.get("decision") != expected_decision:
        failures.append("result.status/decision: does not follow exact checks")

    rerun_equal: bool | None = None
    if (
        rerun_fixtures
        and checkpoint_path is not None
        and corpus_path is not None
        and parity_path is not None
        and raw is not None
    ):
        try:
            fresh = evaluate_gate(
                checkpoint_path=checkpoint_path,
                corpus_manifest_path=corpus_path,
                zero_dose_parity_path=parity_path,
            )
            rerun_equal = fresh == dict(raw)
            if not rerun_equal:
                failures.append("raw: deterministic fixture rerun mismatch")
        except Exception as exc:
            failures.append(f"raw: deterministic fixture rerun failed ({type(exc).__name__}: {exc})")

    evidence = {
        "result_path": str(result_path),
        "status": result.get("status"),
        "decision": result.get("decision"),
        "claim_ceiling": result.get("claim_ceiling"),
        "canonical_hashes_recomputed": recomputed,
        "checkpoint_sha256": sha256_file(checkpoint_path) if checkpoint_path else None,
        "corpus_sha256": corpus.corpus_sha256 if corpus is not None else None,
        "zero_dose_parity_status": parity.get("status") if parity is not None else None,
        "deterministic_rerun_equal": rerun_equal,
    }
    if failures:
        raise C1PretransferGateValidationError(failures, evidence=evidence)
    return evidence


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-rerun", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    evidence = validate_c1_pretransfer_result(
        args.result, rerun_fixtures=not args.no_rerun
    )
    serialized = json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        if args.output.exists():
            raise FileExistsError(f"refusing to overwrite {args.output}")
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "C1PretransferGateValidationError",
    "EXPECTED_CHECKS",
    "validate_c1_pretransfer_result",
]
