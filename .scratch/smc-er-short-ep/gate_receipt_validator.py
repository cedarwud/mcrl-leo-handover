#!/usr/bin/env python3
"""Fail-closed validation for Main-consumer gate result receipts.

The short-EP runner historically checked only a small envelope around a gate
receipt (``status``, ``decision`` and one digest).  That is not enough to make
an experiment receipt authoritative: a hand-written JSON document could make
the same self-attestation.  This module validates the receipt's complete
evidence boundary without trusting the receipt for the values it claims:

* bound source files are hashed again from their canonical repository paths;
* the raw paired rows are loaded from the bound file and all additive metrics
  are recomputed;
* the seed manifest, protocol denominators and checkpoint artifacts are
  checked independently; and
* C1 must pass the already independent Source Gate A and immutable EXP-corpus
  verification chain.

It deliberately does not modify ``run_short_ep.py``.  The integration point is
one call to :func:`validate_main_consumer_result` before constructing a
``GateLedger`` for a route verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))


RESULT_SCHEMA = "smc-er-main-consumer-gate-result-v1"
C1_RAW_SCHEMA = "smc-er-c1-main-consumer-gate-raw-v1"
C1_SEED_SCHEMA = "smc-er-c1-main-consumer-gate-seeds-v1"
C1_CORPUS_MANIFEST_SCHEMA = "smc-er-c1-exp-corpus-manifest-v1"
C1_CORPUS_VERIFICATION_SCHEMA = "smc-er-c1-exp-corpus-verification-v1"
C1_SOURCE_RESULT_SCHEMA = "smc-er-c1-source-gate-a-result-v1"
C1_SOURCE_VERIFICATION_SCHEMA = "smc-er-c1-source-gate-a-verification-v2"
C1_SOURCE_SEED_SCHEMA = "smc-er-c1-source-gate-a-seeds-v1"
C1_BUILD_SEED_SCHEMA = "smc-er-c1-exp-build-seeds-v1"

C1_CLAIM_CEILING = "C1_ROUTE_FOR_ONE_SEED_4EP_DEVELOPMENTAL_PREVIEW_ONLY"
C1_CORPUS_CLAIM_CEILING = "C1_SPECIALIST_PREFILL_ONLY_NEVER_MAIN"
C1_SOURCE_DECISION = "PASS_TO_C1_CONSUMER_GATE"
C1_SOURCE_CLAIM_CEILING = (
    "SOURCE_QUALITY_ONLY_NOT_LEARNING_NOT_MAIN_ROUTING_NOT_EE_EFFICACY"
)
C1_PREFILL_BUNDLES = 34
C1_EVALUATION_SEEDS = 5
C1_SERVICE_GUARD = 0.005
DECISION_STEP_S = 30.08

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class GateReceiptValidationError(RuntimeError):
    """Raised when a gate result cannot be independently established."""

    def __init__(self, failures: Sequence[str], *, evidence: Mapping[str, Any] | None = None):
        unique = tuple(dict.fromkeys(str(item) for item in failures))
        self.failures = unique
        self.evidence = dict(evidence or {})
        super().__init__("gate receipt validation failed: " + "; ".join(unique))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value: Any) -> bool:
    return isinstance(value, str) and _DIGEST_RE.fullmatch(value) is not None


def _int(value: Any) -> bool:
    return type(value) is int


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _close(left: Any, right: Any) -> bool:
    try:
        return math.isclose(
            float(left), float(right), rel_tol=1e-12, abs_tol=1e-9
        )
    except (TypeError, ValueError, OverflowError):
        return False


def _resolve(raw: Any, *, base: Path) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _json(path: Path, label: str, failures: list[str]) -> Mapping[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        failures.append(f"{label}: unreadable ({type(exc).__name__})")
        return None
    if not isinstance(value, Mapping):
        failures.append(f"{label}: top-level object required")
        return None
    return value


def _canonical_authority_paths(repo: Path, *, source: str = "C1") -> dict[str, Path]:
    """Return the non-self-attested path for each code authority digest."""

    short = repo / ".scratch" / "smc-er-short-ep"
    paths = {
        "spec_sha256": short / "C1-MAIN-CONSUMER-GATE-V1-SPEC-2026-08-28.md",
        "runner_sha256": short / "run_c1_consumer_gate.py",
        "method_sha256": repo / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md",
        "concept_sha256": repo / "docs" / "MULTI-CATFISH-CONCEPT-ALGORITHM-FREEZE-V0.1-2026-08-27.md",
        "run_short_ep_sha256": short / "run_short_ep.py",
        "routing_core_sha256": short / "smc_er_core.py",
        "roles_sha256": short / "smc_er_roles.py",
        "prereg_sha256": repo / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json",
    }
    if source == "C1":
        paths["corpus_loader_sha256"] = short / "c1_exp_corpus.py"
        paths["source_gate_verifier_sha256"] = short / "verify_c1_source_gate.py"
        paths["corrective_replay_addendum_sha256"] = (
            short
            / "C1-CANONICAL-TLE-CORRECTIVE-REPLAY-ADDENDUM-V1-2026-08-28.json"
        )
        paths["corrective_replay_verifier_sha256"] = (
            short / "verify_c1_corrective_replay_addendum.py"
        )
        paths["corrective_replay_verifier_test_sha256"] = (
            short / "test_verify_c1_corrective_replay_addendum.py"
        )
        paths["source_seed_provenance_correction_sha256"] = (
            short
            / "C1-SOURCE-GATE-A-SEED-PROVENANCE-CORRECTION-V1-2026-08-28.json"
        )
    return paths


def _require_bound_file(
    *,
    raw_path: Any,
    expected_digest: Any,
    base: Path,
    label: str,
    result_path: Path,
    failures: list[str],
) -> Path | None:
    path = _resolve(raw_path, base=base)
    if path is None:
        failures.append(f"{label}: path missing")
        return None
    if path == result_path.resolve():
        failures.append(f"{label}: self-referential authority is forbidden")
        return None
    if not _digest(expected_digest):
        failures.append(f"{label}: digest missing or malformed")
        return None
    if not path.is_file():
        failures.append(f"{label}: file missing")
        return None
    actual = sha256_file(path)
    if actual != expected_digest:
        failures.append(f"{label}: digest mismatch")
        return None
    return path


def _check_code_authorities(
    authority: Mapping[str, Any],
    *,
    source: str,
    repo: Path,
    failures: list[str],
    authority_paths: Mapping[str, Path] | None,
) -> dict[str, str]:
    paths = _canonical_authority_paths(repo, source=source)
    if authority_paths:
        paths.update({str(key): Path(value).resolve() for key, value in authority_paths.items()})
    actual: dict[str, str] = {}
    for field, path in paths.items():
        expected = authority.get(field)
        if not _digest(expected):
            failures.append(f"authority.{field}: digest missing or malformed")
            continue
        if not path.is_file():
            failures.append(f"authority.{field}: canonical file missing")
            continue
        actual[field] = sha256_file(path)
        if actual[field] != expected:
            failures.append(f"authority.{field}: canonical file digest mismatch")
    return actual


def _protocol(
    payload: Mapping[str, Any],
    *,
    source: str,
    failures: list[str],
) -> dict[str, Any]:
    protocol = payload.get("protocol")
    if not isinstance(protocol, Mapping):
        failures.append("protocol: missing")
        return {}
    required = (
        "episodes",
        "training_users",
        "evaluation_users",
        "evaluation_seed_count",
        "main_only_evaluation",
        "routed_sources",
        "service_guard",
    )
    for field in required:
        if field not in protocol:
            failures.append(f"protocol.{field}: missing")
    for field in ("episodes", "training_users", "evaluation_users", "evaluation_seed_count"):
        if not _int(protocol.get(field)) or int(protocol.get(field)) <= 0:
            failures.append(f"protocol.{field}: positive integer required")
    if protocol.get("main_only_evaluation") is not True:
        failures.append("protocol.main_only_evaluation: must be true")
    routed = protocol.get("routed_sources")
    if not isinstance(routed, list) or any(item not in ("C1", "C2", "C3") for item in routed):
        failures.append("protocol.routed_sources: invalid")
    elif len(set(routed)) != len(routed):
        failures.append("protocol.routed_sources: duplicate source")
    elif source not in routed:
        failures.append("protocol.routed_sources: result source is absent")
    neutral_source = protocol.get("neutral_source")
    if not isinstance(neutral_source, str) or not neutral_source:
        failures.append("protocol.neutral_source: missing")
    if not _finite(protocol.get("service_guard")) or float(protocol.get("service_guard")) < 0:
        failures.append("protocol.service_guard: finite non-negative value required")
    return dict(protocol)


_ENDPOINT_FIELDS = (
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
)


def _endpoint(
    value: Any,
    *,
    label: str,
    branch: str,
    checkpoint_digest: str | None,
    training_seed: int | None,
    evaluation_seed: int,
    evaluation_users: int,
    failures: list[str],
) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        failures.append(f"{label}: endpoint object missing")
        return None
    for field in _ENDPOINT_FIELDS:
        if field not in value:
            failures.append(f"{label}.{field}: missing")
    if value.get("arm") != branch:
        failures.append(f"{label}.arm: mismatch")
    if checkpoint_digest is None or value.get("checkpoint_sha256") != checkpoint_digest:
        failures.append(f"{label}.checkpoint_sha256: mismatch")
    if training_seed is not None and value.get("training_seed") != training_seed:
        failures.append(f"{label}.training_seed: mismatch")
    if value.get("evaluation_seed") != evaluation_seed:
        failures.append(f"{label}.evaluation_seed: mismatch")
    if value.get("users") != evaluation_users:
        failures.append(f"{label}.users: mismatch")

    for field in ("training_seed", "evaluation_seed", "users", "steps", "served_user_intervals", "total_user_intervals", "zero_power_intervals", "zero_service_intervals"):
        if not _int(value.get(field)):
            failures.append(f"{label}.{field}: integer required")
    steps = value.get("steps")
    users = value.get("users")
    if _int(steps) and int(steps) <= 0:
        failures.append(f"{label}.steps: positive required")
    if _int(users) and int(users) <= 0:
        failures.append(f"{label}.users: positive required")
    if _int(steps) and _int(users) and value.get("total_user_intervals") != int(steps) * int(users):
        failures.append(f"{label}.total_user_intervals: denominator mismatch")
    served = value.get("served_user_intervals")
    total = value.get("total_user_intervals")
    if _int(served) and _int(total) and not 0 <= int(served) <= int(total):
        failures.append(f"{label}.served_user_intervals: outside denominator")
    for field in ("zero_power_intervals", "zero_service_intervals"):
        if _int(value.get(field)) and _int(steps) and not 0 <= int(value[field]) <= int(steps):
            failures.append(f"{label}.{field}: outside episode length")

    finite_fields = (
        "duration_s",
        "useful_bits",
        "system_energy_j",
        "system_ee_bits_per_j",
        "mean_system_power_w",
        "mean_system_throughput_bps",
        "served_fraction",
        "r1_sum",
        "r2_sum",
        "r3_sum",
    )
    for field in finite_fields:
        if not _finite(value.get(field)):
            failures.append(f"{label}.{field}: finite value required")
    if _finite(value.get("useful_bits")) and float(value["useful_bits"]) < 0:
        failures.append(f"{label}.useful_bits: negative")
    if _finite(value.get("system_energy_j")) and float(value["system_energy_j"]) < 0:
        failures.append(f"{label}.system_energy_j: negative")

    if not (_int(steps) and _int(users) and _finite(value.get("system_energy_j")) and _finite(value.get("useful_bits"))):
        return dict(value)
    duration = float(steps) * DECISION_STEP_S
    energy = float(value["system_energy_j"])
    bits = float(value["useful_bits"])
    ee = bits / energy if energy > 0 else 0.0
    service = int(served) / int(total) if _int(served) and _int(total) and total else 0.0
    expected = {
        "duration_s": duration,
        "system_ee_bits_per_j": ee,
        "mean_system_power_w": energy / duration,
        "mean_system_throughput_bps": bits / duration,
        "served_fraction": service,
    }
    for field, computed in expected.items():
        if not _close(value.get(field), computed):
            failures.append(f"{label}.{field}: recomputation mismatch")
    return dict(value)


def _checkpoint_and_branch(
    raw: Mapping[str, Any],
    *,
    branch: str,
    authority: Mapping[str, Any],
    protocol: Mapping[str, Any],
    source: str,
    result_path: Path,
    failures: list[str],
) -> tuple[Path | None, str | None, Mapping[str, Any] | None]:
    branches = raw.get("branch_results")
    if not isinstance(branches, Mapping):
        failures.append("raw.branch_results: missing")
        return None, None, None
    item = branches.get(branch)
    if not isinstance(item, Mapping):
        failures.append(f"raw.branch_results.{branch}: missing")
        return None, None, None
    if item.get("episodes") != protocol.get("episodes"):
        failures.append(f"raw.branch_results.{branch}.episodes: denominator mismatch")
    gates = item.get("gates")
    expected_gates = {"C1": "shadow", "C2": "shadow", "C3": "shadow"}
    if source in expected_gates:
        expected_gates[source] = "route"
    if gates != expected_gates:
        failures.append(f"raw.branch_results.{branch}.gates: mismatch")
    checkpoint_digest = item.get("checkpoint_sha256")
    checkpoint = _require_bound_file(
        raw_path=item.get("checkpoint"),
        expected_digest=checkpoint_digest,
        base=result_path.parent,
        label=f"raw.branch_results.{branch}.checkpoint",
        result_path=result_path,
        failures=failures,
    )
    if checkpoint is None:
        checkpoint_digest = None
    prefill = item.get("c1_prefill")
    if source == "C1":
        if not isinstance(prefill, Mapping):
            failures.append(f"raw.branch_results.{branch}.c1_prefill: missing")
        else:
            if prefill.get("bundles") != C1_PREFILL_BUNDLES:
                failures.append(f"raw.branch_results.{branch}.c1_prefill.bundles: mismatch")
            expected_branch = "local" if branch == "informed" else "control"
            if prefill.get("corpus_branch") != expected_branch:
                failures.append(f"raw.branch_results.{branch}.c1_prefill.corpus_branch: mismatch")
            if prefill.get("corpus_manifest_sha256") != authority.get("corpus_manifest_sha256"):
                failures.append(f"raw.branch_results.{branch}.c1_prefill.manifest_digest: mismatch")
            if prefill.get("corpus_sha256") != authority.get("c1_exp_corpus_sha256"):
                failures.append(f"raw.branch_results.{branch}.c1_prefill.corpus_digest: mismatch")
            if prefill.get("enters_main") is not False:
                failures.append(f"raw.branch_results.{branch}.c1_prefill.enters_main: must be false")
    return checkpoint, checkpoint_digest, item


def _recompute_metrics(
    paired: Sequence[Mapping[str, Any]],
    *,
    guard_failures: Sequence[str],
    service_guard: float,
    failures: list[str],
) -> tuple[dict[str, Any], dict[str, bool]]:
    deltas: list[float] = []
    informed_bits: list[float] = []
    informed_energy: list[float] = []
    neutral_bits: list[float] = []
    neutral_energy: list[float] = []
    informed_served = 0
    informed_total = 0
    neutral_served = 0
    neutral_total = 0
    for index, row in enumerate(paired):
        informed = row.get("informed") if isinstance(row, Mapping) else None
        neutral = row.get("neutral") if isinstance(row, Mapping) else None
        if not isinstance(informed, Mapping) or not isinstance(neutral, Mapping):
            continue
        def number(endpoint: Mapping[str, Any], field: str) -> float:
            try:
                return float(endpoint.get(field, math.nan))
            except (TypeError, ValueError, OverflowError):
                return math.nan

        iee = number(informed, "system_ee_bits_per_j")
        nee = number(neutral, "system_ee_bits_per_j")
        if not _finite(iee) or not _finite(nee):
            failures.append(f"paired_rows[{index}]: non-finite EE")
            continue
        deltas.append(iee - nee)
        informed_bits.append(number(informed, "useful_bits"))
        informed_energy.append(number(informed, "system_energy_j"))
        neutral_bits.append(number(neutral, "useful_bits"))
        neutral_energy.append(number(neutral, "system_energy_j"))
        if _int(informed.get("served_user_intervals")) and _int(informed.get("total_user_intervals")):
            informed_served += int(informed["served_user_intervals"])
            informed_total += int(informed["total_user_intervals"])
        if _int(neutral.get("served_user_intervals")) and _int(neutral.get("total_user_intervals")):
            neutral_served += int(neutral["served_user_intervals"])
            neutral_total += int(neutral["total_user_intervals"])
    if len(deltas) != len(paired):
        failures.append("paired_rows: incomplete metric rows")
    ib = math.fsum(informed_bits)
    ie = math.fsum(informed_energy)
    nb = math.fsum(neutral_bits)
    ne = math.fsum(neutral_energy)
    informed_ee = ib / ie if ie > 0 else 0.0
    neutral_ee = nb / ne if ne > 0 else 0.0
    informed_service = informed_served / informed_total if informed_total else 0.0
    neutral_service = neutral_served / neutral_total if neutral_total else 0.0
    metrics = {
        "paired_deltas_bits_per_j": deltas,
        "mean_paired_delta_bits_per_j": math.fsum(deltas) / len(deltas) if deltas else math.nan,
        "positive_seed_count": sum(delta > 0.0 for delta in deltas),
        "informed_ratio_of_sums_ee_bits_per_j": informed_ee,
        "neutral_ratio_of_sums_ee_bits_per_j": neutral_ee,
        "aggregate_delta_bits_per_j": informed_ee - neutral_ee,
        "informed_served_fraction": informed_service,
        "neutral_served_fraction": neutral_service,
        "served_fraction_delta": informed_service - neutral_service,
    }
    checks = {
        "all_structural_guards": not guard_failures and not failures,
        "mean_paired_delta_positive": bool(deltas) and metrics["mean_paired_delta_bits_per_j"] > 0.0,
        "positive_on_at_least_four_seeds": sum(delta > 0.0 for delta in deltas) >= 4,
        "aggregate_ratio_of_sums_delta_positive": informed_ee > neutral_ee,
        "served_fraction_guard": informed_service >= neutral_service - float(service_guard),
    }
    return metrics, checks


def _compare_mapping(
    recorded: Any,
    expected: Mapping[str, Any],
    *,
    label: str,
    failures: list[str],
) -> None:
    if not isinstance(recorded, Mapping):
        failures.append(f"{label}: missing")
        return
    for field, value in expected.items():
        if field not in recorded:
            failures.append(f"{label}.{field}: missing")
        elif isinstance(value, float):
            if not _close(recorded[field], value):
                failures.append(f"{label}.{field}: recomputation mismatch")
        elif recorded[field] != value:
            failures.append(f"{label}.{field}: mismatch")


def _validate_seed_manifest(
    path: Path | None,
    *,
    source: str,
    result_path: Path,
    authority: Mapping[str, Any],
    protocol: Mapping[str, Any],
    forbidden_seeds: set[int],
    failures: list[str],
) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = _json(path, "seed_manifest", failures)
    if payload is None:
        return None
    expected_schema = (
        C1_SEED_SCHEMA
        if source == "C1"
        else f"smc-er-{source.lower()}-main-consumer-gate-seeds-v1"
    )
    if payload.get("schema") != expected_schema or payload.get("status") != "frozen":
        failures.append("seed_manifest: schema/status mismatch")
    binding_fields = [
        "spec_sha256",
        "runner_sha256",
        "method_sha256",
        "concept_sha256",
        "run_short_ep_sha256",
        "routing_core_sha256",
        "roles_sha256",
        "prereg_sha256",
    ]
    if source == "C1":
        binding_fields.extend(
            (
                "corpus_loader_sha256",
                "source_gate_result_sha256",
                "corpus_manifest_sha256",
                "corpus_verification_sha256",
            )
        )
    for field in binding_fields:
        if payload.get(field) != authority.get(field):
            failures.append(f"seed_manifest.{field}: authority mismatch")
    scalar = [payload.get("training_seed"), payload.get("environment_seed"), payload.get("mobility_seed")]
    evaluation = payload.get("evaluation_seeds")
    if any(not _int(seed) or int(seed) < 0 for seed in scalar):
        failures.append("seed_manifest: training seed triple invalid")
    if not isinstance(evaluation, list) or len(evaluation) != protocol.get("evaluation_seed_count"):
        failures.append("seed_manifest.evaluation_seeds: denominator mismatch")
        evaluation = []
    if any(not _int(seed) or int(seed) < 0 for seed in evaluation):
        failures.append("seed_manifest.evaluation_seeds: invalid seed")
    all_seeds = [int(seed) for seed in [*scalar, *evaluation] if _int(seed)]
    if len(set(all_seeds)) != len(all_seeds):
        failures.append("seed_manifest: duplicate seed")
    if set(all_seeds) & set(forbidden_seeds):
        failures.append("seed_manifest: overlap with prerequisite seed namespace")
    return dict(payload)


def _verify_c1_chain(
    *,
    authority: Mapping[str, Any],
    raw: Mapping[str, Any],
    result_path: Path,
    failures: list[str],
) -> dict[str, Any]:
    """Verify Source Gate A, corpus loader, and independent verification."""

    evidence: dict[str, Any] = {}
    branches = raw.get("branch_results")
    manifests: list[Path] = []
    if isinstance(branches, Mapping):
        for branch in ("informed", "neutral"):
            item = branches.get(branch)
            prefill = item.get("c1_prefill") if isinstance(item, Mapping) else None
            if isinstance(prefill, Mapping):
                manifest = _resolve(prefill.get("corpus_manifest"), base=result_path.parent)
                if manifest is not None:
                    manifests.append(manifest)
    if not manifests or len(set(manifests)) != 1:
        failures.append("C1 corpus manifest: both branches must bind one manifest")
        return evidence
    manifest_path = manifests[0]
    manifest_digest = authority.get("corpus_manifest_sha256")
    if not _digest(manifest_digest) or not manifest_path.is_file() or sha256_file(manifest_path) != manifest_digest:
        failures.append("C1 corpus manifest: missing or digest mismatch")
        return evidence
    manifest = _json(manifest_path, "C1 corpus manifest", failures)
    if manifest is None:
        return evidence
    if manifest.get("schema") != C1_CORPUS_MANIFEST_SCHEMA or manifest.get("status") != "complete":
        failures.append("C1 corpus manifest: schema/status mismatch")
    if manifest.get("claim_ceiling") != C1_CORPUS_CLAIM_CEILING:
        failures.append("C1 corpus manifest: claim ceiling mismatch")
    mauth = manifest.get("authority")
    if not isinstance(mauth, Mapping):
        failures.append("C1 corpus manifest: authority missing")
        return evidence

    source_path = _resolve(mauth.get("source_gate_result_path"), base=manifest_path.parent)
    if source_path is None or not source_path.is_file() or not _digest(mauth.get("source_gate_result_sha256")) or sha256_file(source_path) != mauth.get("source_gate_result_sha256"):
        failures.append("C1 Source Gate A: missing or manifest digest mismatch")
        return evidence
    if authority.get("source_gate_result_sha256") != sha256_file(source_path):
        failures.append("C1 Source Gate A: result authority digest mismatch")
    source_payload = _json(source_path, "C1 Source Gate A result", failures)
    if source_payload is None:
        return evidence
    if source_payload.get("schema") != C1_SOURCE_RESULT_SCHEMA or source_payload.get("status") != "PASS" or source_payload.get("decision") != C1_SOURCE_DECISION:
        failures.append("C1 Source Gate A: not an authoritative PASS_TO_C1_CONSUMER_GATE")
    if source_payload.get("claim_ceiling") != C1_SOURCE_CLAIM_CEILING:
        failures.append("C1 Source Gate A: claim ceiling mismatch")
    source_verification_path = _require_bound_file(
        raw_path=authority.get("source_gate_verification_path"),
        expected_digest=authority.get("source_gate_verification_sha256"),
        base=result_path.parent,
        label="C1 Source Gate A verification",
        result_path=result_path,
        failures=failures,
    )
    recorded_source_check = (
        _json(
            source_verification_path,
            "C1 Source Gate A verification",
            failures,
        )
        if source_verification_path is not None
        else None
    )
    if recorded_source_check is not None:
        if (
            recorded_source_check.get("schema") != C1_SOURCE_VERIFICATION_SCHEMA
            or recorded_source_check.get("status") != "PASS"
            or recorded_source_check.get("failures") != []
            or recorded_source_check.get("deterministic_raw_replay_performed")
            is not True
            or recorded_source_check.get("deterministic_raw_replay_equal") is not True
        ):
            failures.append("C1 Source Gate A: current v2 raw-replay PASS required")
        corrective_addendum = _resolve(
            recorded_source_check.get("corrective_replay_addendum_path"),
            base=source_verification_path.parent,
        )
        corrective_verification = _resolve(
            recorded_source_check.get("corrective_replay_verification_path"),
            base=source_verification_path.parent,
        )
        seed_correction = _resolve(
            recorded_source_check.get("source_seed_provenance_correction_path"),
            base=source_verification_path.parent,
        )
        canonical_addendum = _canonical_authority_paths(REPO, source="C1")[
            "corrective_replay_addendum_sha256"
        ].resolve()
        if (
            corrective_addendum != canonical_addendum
            or not corrective_addendum.is_file()
            or sha256_file(corrective_addendum)
            != authority.get("corrective_replay_addendum_sha256")
            or recorded_source_check.get("corrective_replay_addendum_sha256")
            != authority.get("corrective_replay_addendum_sha256")
        ):
            failures.append("C1 Source Gate A: corrective addendum authority mismatch")
        if (
            corrective_verification is None
            or not corrective_verification.is_file()
            or sha256_file(corrective_verification)
            != recorded_source_check.get("corrective_replay_verification_sha256")
        ):
            failures.append("C1 Source Gate A: corrective replay receipt mismatch")
        canonical_seed_correction = _canonical_authority_paths(REPO, source="C1")[
            "source_seed_provenance_correction_sha256"
        ].resolve()
        if (
            seed_correction != canonical_seed_correction
            or not seed_correction.is_file()
            or sha256_file(seed_correction)
            != authority.get("source_seed_provenance_correction_sha256")
            or recorded_source_check.get(
                "source_seed_provenance_correction_sha256"
            )
            != authority.get("source_seed_provenance_correction_sha256")
        ):
            failures.append("C1 Source Gate A: seed correction authority mismatch")
        try:
            import verify_c1_source_gate as source_verifier

            source_check = source_verifier.verify_payload(
                source_payload,
                source_gate_path=source_path,
                corrective_addendum=corrective_addendum,
                corrective_replay_verification=corrective_verification,
                source_seed_provenance_correction=seed_correction,
            )
            if (
                source_check.get("status") != "PASS"
                or dict(source_check) != dict(recorded_source_check)
            ):
                failures.append("C1 Source Gate A: independent v2 replay mismatch")
            evidence["source_gate_verification"] = source_check
        except Exception as exc:  # pragma: no cover - dependency/import failure path
            failures.append(
                f"C1 Source Gate A: verifier unavailable ({type(exc).__name__})"
            )

    source_authority = source_payload.get("authority")
    if isinstance(source_authority, Mapping):
        source_seed_path = _resolve(source_authority.get("seed_manifest_path"), base=source_path.parent)
        source_seed = None
        if source_seed_path is None or not source_seed_path.is_file() or sha256_file(source_seed_path) != source_authority.get("seed_manifest_sha256"):
            failures.append("C1 Source Gate A seed manifest: missing or digest mismatch")
        else:
            source_seed = _json(source_seed_path, "C1 Source Gate A seed manifest", failures)
        source_seed_values = source_seed.get("seeds") if source_seed is not None else None
        if source_seed is None or source_seed.get("schema") != C1_SOURCE_SEED_SCHEMA or source_seed.get("status") != "frozen" or not isinstance(source_seed_values, list) or len(source_seed_values) != 5 or any(not _int(seed) or int(seed) < 0 for seed in source_seed_values) or len(set(source_seed_values)) != 5:
            failures.append("C1 Source Gate A seed manifest: schema/status mismatch")
        else:
            evidence["source_seeds"] = list(source_seed_values)
    else:
        failures.append("C1 Source Gate A: authority missing")

    build_seed_path = _resolve(mauth.get("seed_manifest_path"), base=manifest_path.parent)
    if build_seed_path is None or not build_seed_path.is_file() or sha256_file(build_seed_path) != mauth.get("seed_manifest_sha256"):
        failures.append("C1 corpus build seed manifest: missing or digest mismatch")
    else:
        build_seed = _json(build_seed_path, "C1 corpus build seed manifest", failures)
        build_seed_values = build_seed.get("seeds") if build_seed is not None else None
        if build_seed is None or build_seed.get("schema") != C1_BUILD_SEED_SCHEMA or build_seed.get("status") != "frozen" or not isinstance(build_seed_values, list) or len(build_seed_values) != 5 or any(not _int(seed) or int(seed) < 0 for seed in build_seed_values) or len(set(build_seed_values)) != 5:
            failures.append("C1 corpus build seed manifest: schema/status mismatch")
        else:
            evidence["build_seeds"] = list(build_seed_values)

    try:
        from c1_exp_corpus import load_verified_c1_corpus

        corpus = load_verified_c1_corpus(manifest_path)
        if authority.get("c1_exp_corpus_sha256") != corpus.corpus_sha256:
            failures.append("C1 corpus: result authority digest mismatch")
        evidence["corpus"] = {
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "corpus_sha256": corpus.corpus_sha256,
            "checkpoint_sha256": corpus.checkpoint_sha256,
        }
    except Exception as exc:
        failures.append(f"C1 corpus: independent loader failed ({type(exc).__name__}: {exc})")

    # The current runner writes this verification beside the manifest.  A
    # future runner may make the path explicit; either way the result's digest
    # is checked against the actual bytes and the fields are checked below.
    verification_path = _resolve(
        authority.get("corpus_verification_path"), base=result_path.parent
    )
    if verification_path is None:
        verification_path = manifest_path.parent / "verification.json"
    verification_digest = authority.get("corpus_verification_sha256")
    if not verification_path.is_file() or not _digest(verification_digest) or sha256_file(verification_path) != verification_digest:
        failures.append("C1 corpus verification: missing or digest mismatch")
    else:
        verification = _json(verification_path, "C1 corpus verification", failures)
        if verification is not None:
            if verification.get("schema") != C1_CORPUS_VERIFICATION_SCHEMA or verification.get("status") != "PASS":
                failures.append("C1 corpus verification: schema/status mismatch")
            if verification.get("claim_ceiling") != C1_CORPUS_CLAIM_CEILING:
                failures.append("C1 corpus verification: claim ceiling mismatch")
            if _resolve(verification.get("manifest_path"), base=verification_path.parent) != manifest_path:
                failures.append("C1 corpus verification: manifest lineage mismatch")
            if verification.get("manifest_sha256") != manifest_digest:
                failures.append("C1 corpus verification: manifest digest mismatch")
            corpus_info = evidence.get("corpus", {})
            if verification.get("corpus_sha256") != corpus_info.get("corpus_sha256"):
                failures.append("C1 corpus verification: corpus digest mismatch")
            if verification.get("checkpoint_sha256") != corpus_info.get("checkpoint_sha256"):
                failures.append("C1 corpus verification: checkpoint lineage mismatch")
            if verification.get("selected_bundles") != {"control": 34, "local": 34}:
                failures.append("C1 corpus verification: prefill denominator mismatch")
            if verification.get("branch_ids_disjoint") is not True or verification.get("enters_main") is not False:
                failures.append("C1 corpus verification: branch/Main boundary mismatch")
            evidence["corpus_verification"] = dict(verification)
    return evidence


def validate_main_consumer_result(
    result_path: Path,
    *,
    expected_source: str | None = None,
    repo_root: Path = REPO,
    authority_paths: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Return independently parsed evidence, or raise a validation error.

    ``authority_paths`` exists for unit tests and future source-specific
    consumers.  Production C1 calls should use the canonical defaults so a
    receipt cannot choose replacement code files and hash them itself.
    """

    result_path = Path(result_path).expanduser().resolve()
    failures: list[str] = []
    result = _json(result_path, "result", failures)
    if result is None:
        raise GateReceiptValidationError(failures)
    if result.get("schema") != RESULT_SCHEMA:
        failures.append("result.schema: mismatch")
    source = result.get("source")
    if source not in ("C1", "C2", "C3"):
        failures.append("result.source: invalid")
    if expected_source is not None and source != expected_source:
        failures.append("result.source: unexpected")
    if result.get("status") not in ("PASS", "FAIL"):
        failures.append("result.status: invalid")
    if result.get("decision") not in ("ROUTE", "SHADOW"):
        failures.append("result.decision: invalid")
    if (result.get("status"), result.get("decision")) not in (("PASS", "ROUTE"), ("FAIL", "SHADOW")):
        failures.append("result.status/decision: inconsistent")
    if result.get("prerequisites_closed") is not True:
        failures.append("result.prerequisites_closed: must be true")
    claim = result.get("claim_ceiling")
    if not isinstance(claim, str) or not claim:
        failures.append("result.claim_ceiling: missing")
    if source == "C1" and claim != C1_CLAIM_CEILING:
        failures.append("result.claim_ceiling: C1 mismatch")

    authority = result.get("authority")
    if not isinstance(authority, Mapping):
        failures.append("authority: missing")
        raise GateReceiptValidationError(failures, evidence={"result": dict(result)})
    actual_code_hashes = _check_code_authorities(
        authority,
        source=str(source),
        repo=Path(repo_root).expanduser().resolve(),
        failures=failures,
        authority_paths=authority_paths,
    )
    raw_path = _require_bound_file(
        raw_path=authority.get("raw_rows_path"),
        expected_digest=authority.get("raw_rows_sha256"),
        base=result_path.parent,
        label="authority.raw_rows",
        result_path=result_path,
        failures=failures,
    )
    seed_path = _require_bound_file(
        raw_path=authority.get("seed_manifest_path"),
        expected_digest=authority.get("seed_manifest_sha256"),
        base=result_path.parent,
        label="authority.seed_manifest",
        result_path=result_path,
        failures=failures,
    )
    protocol = _protocol(result, source=str(source), failures=failures)
    raw = _json(raw_path, "raw_rows", failures) if raw_path is not None else None
    if raw is not None:
        expected_raw_schema = C1_RAW_SCHEMA if source == "C1" else f"smc-er-{str(source).lower()}-main-consumer-gate-raw-v1"
        if raw.get("schema") != expected_raw_schema or raw.get("status") != "complete":
            failures.append("raw_rows.schema/status: mismatch")
        if raw.get("claim_ceiling") != claim:
            failures.append("raw_rows.claim_ceiling: mismatch")
        initial_parity = raw.get("initial_main_parity")
        if (
            not isinstance(initial_parity, Mapping)
            or initial_parity.get("status") != "PASS"
            or initial_parity.get("exact_after_descriptive_metadata_normalisation")
            is not True
            or initial_parity.get("first_difference") is not None
        ):
            failures.append("raw_rows.initial_main_parity: exact PASS required")

    chain_evidence: dict[str, Any] = {}
    if source == "C1" and raw is not None:
        chain_evidence = _verify_c1_chain(
            authority=authority,
            raw=raw,
            result_path=result_path,
            failures=failures,
        )
    forbidden = set(int(seed) for seed in chain_evidence.get("source_seeds", []) if _int(seed))
    forbidden.update(int(seed) for seed in chain_evidence.get("build_seeds", []) if _int(seed))
    seed_manifest = _validate_seed_manifest(
        seed_path,
        source=str(source),
        result_path=result_path,
        authority=authority,
        protocol=protocol,
        forbidden_seeds=forbidden,
        failures=failures,
    )

    paired: list[Mapping[str, Any]] = []
    branch_evidence: dict[str, Any] = {}
    if raw is not None:
        value = raw.get("paired_rows")
        if not isinstance(value, list) or len(value) != protocol.get("evaluation_seed_count"):
            failures.append("raw_rows.paired_rows: denominator mismatch")
        else:
            paired = [row for row in value if isinstance(row, Mapping)]
            if len(paired) != len(value):
                failures.append("raw_rows.paired_rows: malformed row")
        informed_checkpoint, informed_digest, _ = _checkpoint_and_branch(
            raw,
            branch="informed",
            authority=authority,
            protocol=protocol,
            source=str(source),
            result_path=result_path,
            failures=failures,
        )
        neutral_checkpoint, neutral_digest, _ = _checkpoint_and_branch(
            raw,
            branch="neutral",
            authority=authority,
            protocol=protocol,
            source=str(source),
            result_path=result_path,
            failures=failures,
        )
        branch_evidence = {
            "informed_checkpoint": str(informed_checkpoint) if informed_checkpoint else None,
            "neutral_checkpoint": str(neutral_checkpoint) if neutral_checkpoint else None,
        }
        evaluation_seeds = seed_manifest.get("evaluation_seeds", []) if seed_manifest else []
        if len(paired) == len(value):
            seen: set[int] = set()
            for index, row in enumerate(paired):
                evaluation_seed = row.get("evaluation_seed")
                if not _int(evaluation_seed) or int(evaluation_seed) in seen:
                    failures.append(f"raw_rows.paired_rows[{index}].evaluation_seed: duplicate/invalid")
                    continue
                seen.add(int(evaluation_seed))
                if evaluation_seeds and int(evaluation_seed) != int(evaluation_seeds[index]):
                    failures.append(f"raw_rows.paired_rows[{index}].evaluation_seed: seed manifest mismatch")
                informed = _endpoint(
                    row.get("informed"),
                    label=f"paired_rows[{index}].informed",
                    branch="informed",
                    checkpoint_digest=informed_digest,
                    training_seed=seed_manifest.get("training_seed") if seed_manifest else None,
                    evaluation_seed=int(evaluation_seed) if _int(evaluation_seed) else -1,
                    evaluation_users=int(protocol.get("evaluation_users", 0)) if _int(protocol.get("evaluation_users")) else 0,
                    failures=failures,
                )
                neutral = _endpoint(
                    row.get("neutral"),
                    label=f"paired_rows[{index}].neutral",
                    branch="neutral",
                    checkpoint_digest=neutral_digest,
                    training_seed=seed_manifest.get("training_seed") if seed_manifest else None,
                    evaluation_seed=int(evaluation_seed) if _int(evaluation_seed) else -1,
                    evaluation_users=int(protocol.get("evaluation_users", 0)) if _int(protocol.get("evaluation_users")) else 0,
                    failures=failures,
                )
                if informed is not None and neutral is not None and not _close(
                    float(row.get("delta_ee_bits_per_j", math.nan)),
                    float(informed.get("system_ee_bits_per_j", math.nan)) - float(neutral.get("system_ee_bits_per_j", math.nan)),
                ):
                    failures.append(f"paired_rows[{index}].delta_ee_bits_per_j: mismatch")

    guard_failures = result.get("guard_failures")
    if not isinstance(guard_failures, list) or any(not isinstance(item, str) for item in guard_failures):
        failures.append("result.guard_failures: list of strings required")
        guard_failures = []
    metrics, checks = _recompute_metrics(
        paired,
        guard_failures=guard_failures,
        service_guard=float(protocol.get("service_guard", C1_SERVICE_GUARD)) if _finite(protocol.get("service_guard", C1_SERVICE_GUARD)) else C1_SERVICE_GUARD,
        failures=failures,
    )
    _compare_mapping(result.get("metrics"), metrics, label="result.metrics", failures=failures)
    _compare_mapping(result.get("checks"), checks, label="result.checks", failures=failures)
    expected_status = "PASS" if all(checks.values()) else "FAIL"
    expected_decision = "ROUTE" if expected_status == "PASS" else "SHADOW"
    if result.get("status") != expected_status:
        failures.append("result.status: does not match recomputed checks")
    if result.get("decision") != expected_decision:
        failures.append("result.decision: does not match recomputed checks")

    evidence = {
        "result_path": str(result_path),
        "source": source,
        "status": result.get("status"),
        "decision": result.get("decision"),
        "claim_ceiling": claim,
        "authority": dict(authority),
        "authority_hashes_recomputed": actual_code_hashes,
        "seed_manifest": seed_manifest,
        "protocol": protocol,
        "metrics_recomputed": metrics,
        "checks_recomputed": checks,
        "paired_rows": len(paired),
        "branches": branch_evidence,
        "c1_chain": chain_evidence,
    }
    if failures:
        raise GateReceiptValidationError(failures, evidence=evidence)
    return evidence


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--expected-source", choices=("C1", "C2", "C3"))
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    evidence = validate_main_consumer_result(
        args.result,
        expected_source=args.expected_source,
    )
    serialized = json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.expanduser().resolve().write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


# Short alias for callers that use the receipt terminology rather than the
# current result-schema name.  Both names intentionally share one validator.
validate_gate_result = validate_main_consumer_result


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "GateReceiptValidationError",
    "RESULT_SCHEMA",
    "validate_gate_result",
    "validate_main_consumer_result",
    "sha256_file",
]
