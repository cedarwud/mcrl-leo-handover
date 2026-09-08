#!/usr/bin/env python3
"""Two-arm FULL2+C3-S confirmatory ladder; never launches implicitly."""

from __future__ import annotations

import argparse
import errno
from fractions import Fraction
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent  # Provenance: confirmatory package location.
REPO = HERE.parents[1]  # Provenance: workspace package layout.
SCREEN_DIR = REPO / ".scratch/multi-catfish-v023-c3s-screen"  # Provenance: sealed v1 package.
VARIANT_DIR = REPO / ".scratch" / "multi-catfish-v023-c3s-variants"  # Provenance: sealed matrix package.
STAGEC_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-successor-stagec-launch"  # Provenance: stage-C R2 machinery.
STAGEC_PHYSICAL_DIR = REPO / ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation"  # Provenance: stage-C physical adapter.
for _path in (HERE, SCREEN_DIR, STAGEC_DIR, STAGEC_PHYSICAL_DIR, REPO / "src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import build_c3s_confirm_world_plan as world_plan  # noqa: E402
from c3s_full2_policy_adapter import (  # noqa: E402
    ARMS, COORDINATOR_CONFIGURATIONS, STEPS, USERS, C3SFull2PolicyAdapter,
    FixedPolicyEpisodeAdapter, load_full2_export,
)
import stagec_common as _stagec_common  # noqa: E402
import accept_stage_c_chunk_equivalence as _stagec_acceptance  # noqa: E402
import v023_c1c2_successor_physical_runner as _stagec_boundary  # noqa: E402
import variant_policy  # noqa: E402


SCHEMA = "multi-catfish-mcrl-v023-c3s-confirmatory-v2"  # Provenance: astra sealing-review implementation revision.
CLAIM_CEILING = "TRAIN_DEVELOPMENT_FULL2_C3S_CONFIRMATION_NO_LEARNER_NO_TEST_NO_EFFICACY"  # Provenance: amended A-plan section 6.
CHECKPOINT_EVERY = 100  # Provenance: astra D and stage-C R2 chunk cadence.
RUNG_BOUNDARIES = (100, 500, 1500, 3000)  # Provenance: astra C/D confirmatory ladder.
FUTILITY_BOUNDARIES = (100, 500)  # Provenance: astra D early-futility amendment.
TERMINAL_BOUNDARY = 3000  # Provenance: astra C exact estimand.
SERVICE_MARGIN = Fraction(1, 1000)  # Provenance: astra C declared service criterion.
HELD = "C3S_CONTRIBUTION_HELD"  # Provenance: astra C terminal token.
RUNG_HELD = "RUNG_HELD"  # Provenance: astra D interval-release token.
FALSIFIED = "C3S_CONTRIBUTION_FALSIFIED"  # Provenance: astra C terminal token.
ARM_UNRESOLVED = "ARM_UNRESOLVED"  # Provenance: astra B(i) invalid/incomplete rule.
MATRIX_TIE_ORDER = ("V-J", "V-U", "V-M", "V-C", "V-H", "V-P", "V-L2", "LITE")  # Provenance: sealed matrix contract tie order.
THREAD_ENV = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")  # Provenance: stage-C R2 single-thread rule.
CANONICAL_INTERPRETER = Path("/home/sat/mcrl-leo-handover/.venv/bin/python")  # Provenance: existing formal runtime binding.
PLAN_CONTRACT_PLACEHOLDER = HERE / "DRAFT-C3S-FULL2-CONFIRMATORY-PLAN-V2-2026-09-08.md"  # Provenance: requested plan-v2 deliverable.
DEFAULT_WORLD_PLAN = HERE / "C3S-CONFIRM-WORLD-PLAN-9000.json"  # Provenance: amended A plan's 9,000-world allocation.
DEFAULT_PREFLIGHT = HERE / "C3S-CONFIRM-PREFLIGHT.json"  # Provenance: confirmatory builder interface.
BOUNDARY_DONOR = STAGEC_PHYSICAL_DIR / "v023_c1c2_successor_physical_runner.py"  # Provenance: stage-C receipt convention.
ACCEPTANCE_DONOR = STAGEC_DIR / "accept_stage_c_chunk_equivalence.py"  # Provenance: stage-C equivalence convention.
COMMON_DONOR = STAGEC_DIR / "stagec_common.py"  # Provenance: stage-C exclusion vocabulary.


class ConfirmatoryError(RuntimeError):
    """Provenance, matching, publication, or analysis integrity failed."""


class ConfirmatoryIncomplete(ConfirmatoryError):
    """Required coverage is absent without evidence of scientific invalidity."""


def canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as error:
        raise ConfirmatoryError("artifact is not finite canonical ASCII JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: str | Path) -> str:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ConfirmatoryError(f"required regular file is absent or symlinked: {source}")
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: str | Path, *, field: str = "JSON artifact") -> dict[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ConfirmatoryError(f"cannot read {field}: {source}") from error
    if not isinstance(value, dict):
        raise ConfirmatoryError(f"{field} root is not an object")
    return value


def _valid_v1_lite_support(receipt: Mapping[str, object]) -> bool:
    decisions = receipt.get("decisions")
    return bool(
        receipt.get("status") == "COMPLETE"
        and receipt.get("outcome") == "C3S_THREE_ARM_SCREEN_COMPLETE"
        and receipt.get("integrity") is True
        and isinstance(decisions, Mapping)
        and isinstance(decisions.get("LITE"), Mapping)
        and decisions["LITE"].get("outcome") == "C3S_LITE_SCREEN_SUPPORT"  # type: ignore[index]
    )


def _matrix_mean_total_latency(receipt: Mapping[str, object], arm: str) -> float:
    pooled = receipt.get("pooled")
    latency = pooled.get("latency_by_arm") if isinstance(pooled, Mapping) else None
    row = latency.get(arm) if isinstance(latency, Mapping) else None
    if not isinstance(row, Mapping):
        raise ConfirmatoryError(f"matrix receipt lacks total-decision latency for {arm}")
    raw = row.get("mean_hex", row.get("mean_total_decision_wall_seconds_hex"))
    return _float(raw, field=f"matrix {arm} mean total latency", positive=True)


def resolve_confirmatory_arm(
    matrix_terminal_receipt: Mapping[str, object],
    v1_terminal_receipt: Mapping[str, object],
) -> str:
    """Apply astra B(i) literally and return a configuration id or ARM_UNRESOLVED."""

    if matrix_terminal_receipt.get("status") in ("INVALID_RUN", "INCOMPLETE"):
        return ARM_UNRESOLVED
    pooled = matrix_terminal_receipt.get("pooled")
    decisions = pooled.get("decisions") if isinstance(pooled, Mapping) else None
    audit = matrix_terminal_receipt.get("lite_equivalence_audit")
    valid_matrix = (
        matrix_terminal_receipt.get("status") == "COMPLETE"
        and matrix_terminal_receipt.get("outcome") == "C3S_VARIANT_MATRIX_COMPLETE"
        and matrix_terminal_receipt.get("integrity") is True
        and isinstance(decisions, Mapping)
        and set(decisions) == set(MATRIX_TIE_ORDER)
        and isinstance(audit, Mapping)
        and audit.get("status") == "PASS_BITWISE_LITE_EQUIVALENCE"
        and audit.get("unexplained_same_panel_disagreement") is False
    )
    if not valid_matrix:
        return ARM_UNRESOLVED
    supporters: list[str] = []
    for arm in MATRIX_TIE_ORDER:
        row = decisions[arm]  # type: ignore[index]
        if not isinstance(row, Mapping) or row.get("outcome") not in ("SUPPORT", "NO_SUPPORT"):
            return ARM_UNRESOLVED
        if row.get("outcome") == "SUPPORT":
            supporters.append(arm)
    if supporters:
        order = {arm: index for index, arm in enumerate(MATRIX_TIE_ORDER)}
        return min(supporters, key=lambda arm: (_matrix_mean_total_latency(matrix_terminal_receipt, arm), order[arm]))
    return "LITE" if _valid_v1_lite_support(v1_terminal_receipt) else ARM_UNRESOLVED


def write_once(path: str | Path, payload: Mapping[str, object]) -> str:
    """Atomically publish immutable JSON plus a sibling digest sidecar."""

    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    if target.exists() or target.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ConfirmatoryError(f"refusing to overwrite write-once artifact: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_bytes(payload) + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    except FileExistsError as error:
        raise ConfirmatoryError(f"artifact was published concurrently: {target}") from error
    finally:
        Path(temporary).unlink(missing_ok=True)
    digest = file_sha256(target)
    sidecar.write_text(f"{digest}  {target.name}\n", encoding="ascii")
    target.chmod(0o444)
    sidecar.chmod(0o444)
    if file_sha256(target) != digest:
        raise ConfirmatoryError("write-once artifact changed after publication")
    return digest


def validate_sealed_file(path: str | Path, expected_sha256: str | None = None) -> dict[str, str]:
    target = Path(path)
    sidecar = Path(f"{target}.sha256")
    try:
        if target.is_symlink() or sidecar.is_symlink() or not target.is_file() or not sidecar.is_file():
            raise OSError("sealed artifact must be regular files")
        digest = file_sha256(target)
        words = sidecar.read_text(encoding="ascii").split()
    except (OSError, UnicodeError, ConfirmatoryError):
        raise ConfirmatoryError(f"sealed file or sidecar is invalid: {target}") from None
    # Git transports content, executable bits, and sidecars but not a read-only
    # mode bit. The named SHA-256 sidecar is therefore the portable seal.
    if words != [digest, target.name] or (expected_sha256 is not None and digest != expected_sha256):
        raise ConfirmatoryError(f"sealed file or sidecar is invalid: {target}")
    return {"path": str(target.resolve()), "sha256": digest}


def pin_runtime() -> dict[str, object]:
    if Path(sys.executable).resolve() != CANONICAL_INTERPRETER.resolve():
        raise ConfirmatoryError(f"formal execution requires interpreter {CANONICAL_INTERPRETER}")
    if any(os.environ.get(name) != "1" for name in THREAD_ENV):
        raise ConfirmatoryError("all OMP/BLAS thread variables must equal 1")
    if not os.environ.get("MCRL_C3S_WORKER_CONCURRENCY") or not os.environ.get("MCRL_C3S_CACHE_CONDITIONS"):
        raise ConfirmatoryError("formal timing requires worker-concurrency and cache-condition fields")
    import torch

    try:
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    except RuntimeError:
        if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
            raise ConfirmatoryError("Torch could not be pinned to one thread") from None
    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise ConfirmatoryError("Torch one-thread pins did not take effect")
    return {
        "interpreter": str(Path(sys.executable).resolve()),
        "threads": {name: 1 for name in THREAD_ENV},
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "hardware": {"platform": platform.platform(), "machine": platform.machine(), "processor": platform.processor(), "logical_cpu_count": os.cpu_count()},
        "worker_concurrency": os.environ.get("MCRL_C3S_WORKER_CONCURRENCY", "UNRECORDED"),
        "cache_scope_and_condition": os.environ.get("MCRL_C3S_CACHE_CONDITIONS", "UNRECORDED"),
    }


def _float(value: object, *, field: str, positive: bool = False) -> float:
    if isinstance(value, str) and value.startswith(("0x", "-0x")):
        parsed = float.fromhex(value)
    else:
        try:
            parsed = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ConfirmatoryError(f"{field} is not a float") from error
    if not math.isfinite(parsed) or (positive and parsed <= 0) or (not positive and parsed < 0):
        raise ConfirmatoryError(f"{field} is outside its domain")
    return parsed


def validate_decision_records(value: object, *, arm: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) != STEPS:
        raise ConfirmatoryError("episode must persist exactly 30 decision records")
    records: list[dict[str, object]] = []
    required = {
        "decision_index", "step_index", "arm", "coordinator_configuration",
        "pre_decision_state_sha256", "full2_proposal", "full2_proposal_sha256",
        "full2_proposal_physical_associations", "committed_profile_id",
        "committed_actions", "committed_actions_sha256",
        "committed_physical_associations", "selected_nominal",
        "full2_proposal_nominal", "catalog_size", "unique_nominal_evaluations",
        "profile_counts", "coordinator_active_step", "full_decision_wall_seconds_hex",
        "phase_wall_seconds_hex", "eta_sensitivity", "policy_state_after",
        "process_lifetime_peak_rss_kib", "realised",
    }
    for step, raw in enumerate(value):
        if not isinstance(raw, Mapping) or set(raw) != required:
            raise ConfirmatoryError("decision-record schema drifted")
        if raw.get("step_index") != step or raw.get("arm") != arm:
            raise ConfirmatoryError("decision-record step/arm drifted")
        if raw.get("coordinator_configuration") not in COORDINATOR_CONFIGURATIONS:
            raise ConfirmatoryError("decision-record coordinator configuration drifted")
        for name in ("full2_proposal", "committed_actions", "full2_proposal_physical_associations", "committed_physical_associations"):
            if not isinstance(raw.get(name), list) or len(raw[name]) != USERS:
                raise ConfirmatoryError(f"decision-record {name} does not cover 100 users")
        for name in ("pre_decision_state_sha256", "full2_proposal_sha256", "committed_actions_sha256"):
            if not isinstance(raw.get(name), str) or len(str(raw[name])) != 64:
                raise ConfirmatoryError(f"decision-record {name} is not a SHA-256")
        _float(raw.get("full_decision_wall_seconds_hex"), field="full decision wall")
        if not isinstance(raw.get("coordinator_active_step"), bool):
            raise ConfirmatoryError("decision-record active-step flag is malformed")
        realised = raw.get("realised")
        nominal = raw.get("selected_nominal")
        proposal_nominal = raw.get("full2_proposal_nominal")
        if not all(isinstance(row, Mapping) for row in (realised, nominal, proposal_nominal)):
            raise ConfirmatoryError("decision-record nominal/realised metrics are absent")
        for label, row in (("realised", realised), ("nominal", nominal), ("proposal nominal", proposal_nominal)):
            _float(row.get("total_bits_hex"), field=f"{label} bits")  # type: ignore[union-attr]
            _float(row.get("total_energy_j_hex"), field=f"{label} energy", positive=True)  # type: ignore[union-attr]
            row_served, row_opportunities = row.get("served"), row.get("opportunities")  # type: ignore[union-attr]
            if type(row_served) is not int or type(row_opportunities) is not int or row_opportunities != USERS or not 0 <= row_served <= row_opportunities:
                raise ConfirmatoryError(f"decision-record {label} service coverage drifted")
        records.append(dict(raw))
    return records


def validate_episode(receipt: Mapping[str, object], *, arm: str | None = None) -> dict[str, Any]:
    expected_arm = receipt.get("arm") if arm is None else arm
    required = {
        "schema", "status", "arm", "episode_index", "world_id", "world_seed",
        "world_domain",
        "field_root_digest", "initial_state_sha256", "policy_binding_sha256",
        "total_bits", "total_energy_j", "served_user_steps",
        "service_opportunities", "action_trace_sha256", "plan_sha256",
        "decision_records", "decision_records_sha256",
    }
    if set(receipt) != required or receipt.get("schema") != f"{SCHEMA}-episode-receipt" or receipt.get("status") != "COMPLETE":
        raise ConfirmatoryError("episode receipt schema/status drifted")
    if expected_arm not in ARMS or receipt.get("arm") != expected_arm:
        raise ConfirmatoryError("episode arm drifted")
    index = receipt.get("episode_index")
    domain = receipt.get("world_domain")
    opportunities = receipt.get("service_opportunities")
    served = receipt.get("served_user_steps")
    if (
        type(index) is not int or index < 1
        or not isinstance(domain, str)
        or type(receipt.get("world_seed")) is not int
        or type(opportunities) is not int or opportunities != USERS * STEPS
        or type(served) is not int or not 0 <= served <= opportunities
    ):
        raise ConfirmatoryError("episode identity or service coverage drifted")
    if domain == f"C3S_CONFIRM/world/{index}":
        expected_world_id = f"c3s-confirm-world-{index:06d}"
    elif domain == f"C3S_CONFIRM_ACCEPT/world/{index}":
        expected_world_id = f"c3s-confirm-accept-world-{index:06d}"
    else:
        raise ConfirmatoryError("episode world domain is outside the sealed panels")
    if receipt.get("world_id") != expected_world_id or receipt.get("world_seed") != world_plan.derive_seed(domain):
        raise ConfirmatoryError("episode identity or world seed differs from its domain rule")
    for name in ("field_root_digest", "initial_state_sha256", "policy_binding_sha256", "action_trace_sha256", "plan_sha256"):
        value = receipt.get(name)
        if not isinstance(value, str) or len(value) != 64:
            raise ConfirmatoryError(f"episode {name} is not a SHA-256")
    _float(receipt.get("total_bits"), field="total_bits")
    _float(receipt.get("total_energy_j"), field="total_energy_j", positive=True)
    decisions = validate_decision_records(receipt.get("decision_records"), arm=str(expected_arm))
    if receipt.get("decision_records_sha256") != canonical_sha256(decisions):
        raise ConfirmatoryError("episode decision-record digest drifted")
    realised_bits = math.fsum(_float(row["realised"]["total_bits_hex"], field="decision realised bits") for row in decisions)  # type: ignore[index]
    realised_energy = math.fsum(_float(row["realised"]["total_energy_j_hex"], field="decision realised energy", positive=True) for row in decisions)  # type: ignore[index]
    realised_served = sum(int(row["realised"]["served"]) for row in decisions)  # type: ignore[index]
    if realised_bits != float(receipt["total_bits"]) or realised_energy != float(receipt["total_energy_j"]) or realised_served != served:
        raise ConfirmatoryError("episode totals disagree with persistent decision records")
    return dict(receipt)


def pool_episodes(receipts: Sequence[Mapping[str, object]], *, arm: str) -> dict[str, object]:
    ordered = sorted((validate_episode(row, arm=arm) for row in receipts), key=lambda row: row["episode_index"])
    if [row["episode_index"] for row in ordered] != list(range(1, len(ordered) + 1)):
        raise ConfirmatoryError("episode coverage is not one contiguous prefix")
    bits = math.fsum(_float(row["total_bits"], field="total_bits") for row in ordered)
    energy = math.fsum(_float(row["total_energy_j"], field="total_energy_j", positive=True) for row in ordered)
    served = sum(int(row["served_user_steps"]) for row in ordered)
    opportunities = sum(int(row["service_opportunities"]) for row in ordered)
    if energy <= 0 or opportunities <= 0:
        raise ConfirmatoryError("pooled denominator is non-positive")
    return {
        "episodes": len(ordered),
        "total_bits": bits,
        "total_bits_hex": bits.hex(),
        "total_energy_j": energy,
        "total_energy_j_hex": energy.hex(),
        "ee_bits_per_j": bits / energy,
        "ee_bits_per_j_hex": (bits / energy).hex(),
        "served_user_steps": served,
        "service_opportunities": opportunities,
        "service_fraction": served / opportunities,
        "service_fraction_hex": (served / opportunities).hex(),
    }


def _timing_stats(values: Sequence[float], *, threshold: float = 30.08) -> dict[str, object]:
    if not values:
        return {"count": 0, "mean_hex": None, "median_hex": None, "p95_nearest_rank_hex": None, "maximum_hex": None,
                "mean_over_control_interval": None,
                "deadline_seconds": threshold, "deadline_miss_count": 0, "deadline_denominator": 0}
    ordered = sorted(values)
    return {
        "count": len(values), "mean_hex": (math.fsum(values) / len(values)).hex(),
        "median_hex": statistics.median(ordered).hex(),
        "p95_nearest_rank_hex": ordered[math.ceil(0.95 * len(ordered)) - 1].hex(),
        "maximum_hex": ordered[-1].hex(), "mean_over_control_interval": (math.fsum(values) / len(values)) / threshold,
        "deadline_seconds": threshold,
        "deadline_miss_count": sum(value > threshold for value in values),
        "deadline_denominator": len(values),
    }


def latency_summary(receipts: Sequence[Mapping[str, object]], *, arm: str) -> dict[str, object]:
    records = [record for receipt in receipts for record in validate_decision_records(receipt.get("decision_records"), arm=arm)]
    all_values = [_float(row["full_decision_wall_seconds_hex"], field="full decision wall") for row in records]
    active_values = [value for row, value in zip(records, all_values, strict=True) if row["coordinator_active_step"]]
    phase_names = sorted({str(name) for row in records for name in row["phase_wall_seconds_hex"]})  # type: ignore[union-attr]
    phases = {
        name: _timing_stats([
            _float(row["phase_wall_seconds_hex"][name], field=f"phase {name}")  # type: ignore[index]
            for row in records if name in row["phase_wall_seconds_hex"]  # type: ignore[operator]
        ]) for name in phase_names
    }


def eta_sensitivity_summary(receipts: Sequence[Mapping[str, object]], *, arm: str) -> dict[str, object]:
    decisions = [record for receipt in receipts[:100] for record in validate_decision_records(receipt.get("decision_records"), arm=arm)]
    rows = [item for record in decisions for item in record["eta_sensitivity"]]  # type: ignore[union-attr]
    by_multiplier: dict[str, dict[str, object]] = {}
    for item in rows:
        multiplier = item["eta_multiplier"]["numerator"] + "/" + item["eta_multiplier"]["denominator"]  # type: ignore[index]
        bucket = by_multiplier.setdefault(multiplier, {"decisions": 0, "choice_agreements": 0, "values": []})
        bucket["decisions"] = int(bucket["decisions"]) + 1
        bucket["choice_agreements"] = int(bucket["choice_agreements"]) + int(bool(item["choice_agrees_with_primary"]))
        bucket["values"].append(item)  # type: ignore[union-attr]
    for bucket in by_multiplier.values():
        bucket["choice_agreement_fraction"] = int(bucket["choice_agreements"]) / int(bucket["decisions"])
    return {
        "role": "NON_DECISIONAL_CACHED_CANDIDATE_CHOICE_STABILITY",
        "closed_loop_ee_sensitivity": False, "progression_effect": False,
        "covered_worlds": min(100, len(receipts)), "covered_decisions": len(decisions),
        "by_multiplier": by_multiplier,
    }


def physical_event_summary(receipts: Sequence[Mapping[str, object]], *, arm: str) -> dict[str, object]:
    reversals = 0
    handovers: dict[str, int] = {}
    for receipt in receipts:
        records = validate_decision_records(receipt.get("decision_records"), arm=arm)
        trace = []
        for record in records:
            realised = record["realised"]
            associations = realised.get("physical_associations", record["committed_physical_associations"])  # type: ignore[union-attr]
            trace.append([None if item is None else (int(item[0]), int(item[1])) for item in associations])
            for name in realised.get("handover_classes", []):  # type: ignore[union-attr]
                handovers[str(name)] = handovers.get(str(name), 0) + 1
        reversals += variant_policy.association_reversals(trace, window=3)
    return {
        "association_reversals_within_3_steps": reversals,
        "handover_classes": handovers, "association_source": "REALISED_NATIVE_RESOLUTION",
    }
    catalog_sizes = [int(row["catalog_size"]) for row in records]
    unique_counts = [int(row["unique_nominal_evaluations"]) for row in records]
    return {
        "timer_scope": "STATE_ACQUISITION_THROUGH_COMPLETE_ACTION_RETURN",
        "all_steps": _timing_stats(all_values), "coordinator_active_steps": _timing_stats(active_values),
        "phases": phases, "cadence_variant": any(not bool(row["coordinator_active_step"]) for row in records),
        "catalog_size": {"minimum": min(catalog_sizes), "mean": math.fsum(catalog_sizes) / len(catalog_sizes), "maximum": max(catalog_sizes)},
        "unique_nominal_evaluations": {"minimum": min(unique_counts), "mean": math.fsum(unique_counts) / len(unique_counts), "maximum": max(unique_counts)},
        "cache_hits": sum(max(0, size - unique) for size, unique in zip(catalog_sizes, unique_counts, strict=True)),
        "process_lifetime_peak_rss_kib_max": max(int(row["process_lifetime_peak_rss_kib"]) for row in records),
        "hardware": {
            "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "logical_cpu_count": os.cpu_count(),
        },
        "threads": {name: os.environ.get(name) for name in THREAD_ENV},
        "worker_concurrency": os.environ.get("MCRL_C3S_WORKER_CONCURRENCY", "UNRECORDED"),
        "cache_conditions": os.environ.get("MCRL_C3S_CACHE_CONDITIONS", "UNRECORDED"),
    }


def adjudicate(
    pooled_by_arm: Mapping[str, object], *, completed_episodes: int,
    independently_verified: bool = True,
) -> dict[str, object]:
    """Apply the two endpoint criteria and the sealed 100/500 futility rule."""

    if completed_episodes not in RUNG_BOUNDARIES:
        raise ConfirmatoryError("adjudication is permitted only at a declared rung")
    if not independently_verified:
        return {
            "scientific_disposition_emitted": False, "overall_token": None,
            "rung_status": "AWAITING_INDEPENDENT_VERIFICATION", "reasons": [],
            "progression_closed": False, "next_interval_released": False,
        }
    if set(pooled_by_arm) != set(ARMS):
        raise ConfirmatoryError("rung adjudication lacks both arms")
    base = pooled_by_arm["FULL2"]
    c3s = pooled_by_arm["FULL2+C3-S"]
    if not isinstance(base, Mapping) or not isinstance(c3s, Mapping):
        raise ConfirmatoryError("terminal pooled endpoints are malformed")
    if base.get("episodes") != completed_episodes or c3s.get("episodes") != completed_episodes:
        raise ConfirmatoryIncomplete("rung matched coverage is incomplete")
    expected_opportunities = USERS * STEPS * completed_episodes
    if base.get("service_opportunities") != expected_opportunities or c3s.get("service_opportunities") != expected_opportunities:
        raise ConfirmatoryIncomplete("rung service-opportunity coverage is incomplete")
    reasons: list[str] = []
    if _float(c3s.get("ee_bits_per_j"), field="C3S EE") <= _float(base.get("ee_bits_per_j"), field="FULL2 EE"):
        reasons.append("EE_NOT_STRICTLY_ABOVE_FULL2")
    c3s_service = Fraction(int(c3s["served_user_steps"]), int(c3s["service_opportunities"]))
    base_service = Fraction(int(base["served_user_steps"]), int(base["service_opportunities"]))
    if c3s_service < base_service - SERVICE_MARGIN:
        reasons.append("SERVICE_MARGIN_FAILED")
    if completed_episodes in FUTILITY_BOUNDARIES:
        if reasons:
            return {
                "scientific_disposition_emitted": True, "overall_token": FALSIFIED,
                "rung_status": "EARLY_FUTILITY", "reasons": reasons,
                "progression_closed": True, "next_interval_released": False,
            }
        return {
            "scientific_disposition_emitted": False, "overall_token": None,
            "rung_status": RUNG_HELD, "reasons": [], "progression_closed": False,
            "next_interval_released": True,
        }
    if completed_episodes == 1500:
        return {
            "scientific_disposition_emitted": False, "overall_token": None,
            "rung_status": RUNG_HELD, "reasons": reasons,
            "progression_closed": False, "next_interval_released": True,
        }
    return {
        "scientific_disposition_emitted": True,
        "overall_token": HELD if not reasons else FALSIFIED,
        "rung_status": "CONTRIBUTION_HELD" if not reasons else "TERMINAL_FALSIFIED",
        "reasons": reasons, "progression_closed": bool(reasons),
        "next_interval_released": False,
    }


def boundary_table(
    *, plan: Mapping[str, object], arm: str, policy_binding: Mapping[str, object],
    boundaries: Sequence[int], rng_factory: Callable[[int], Sequence[np.random.Generator]],
) -> dict[int, dict[str, object]]:
    """Import the stage-C boundary body and reuse its real age-draw replay."""

    if arm not in ARMS:
        raise ConfirmatoryError("boundary arm is invalid")
    requested = tuple(boundaries)
    if not requested or requested[0] != 0 or tuple(sorted(set(requested))) != requested or any(
        type(value) is not int or value < 0 or value % 100 for value in requested
    ):
        raise ConfirmatoryError("boundaries must be sorted unique 100-aligned values from zero")
    worlds = plan.get("worlds")
    if not isinstance(worlds, list) or requested[-1] > min(len(worlds), 3000):
        raise ConfirmatoryError("boundary exceeds the admitted 3000 prefix")
    proxy_worlds = [SimpleNamespace(**row) for row in worlds]
    proxy_plan = SimpleNamespace(worlds=proxy_worlds, plan_sha256=plan["plan_sha256"])
    try:
        rngs = tuple(rng_factory(int(worlds[0]["world_seed"])))
        age_rng = rngs[0].spawn(1)[0]
    except (IndexError, TypeError, ValueError, AttributeError) as error:
        raise ConfirmatoryError("cannot construct the stage-C age stream") from error
    result: dict[int, dict[str, object]] = {}
    requested_set = set(requested)
    states = {0: {"format_version": 1, "age_rng_state": None}}
    for episode in range(1, requested[-1] + 1):
        age_rng.integers(0, 10, size=100)
        if episode in requested_set:
            states[episode] = {
                "format_version": 1,
                "age_rng_state": json.loads(json.dumps(age_rng.bit_generator.state)),
            }
    for boundary in requested:
        donor_payload = _stagec_boundary._boundary_body(
            arm=arm, boundary=boundary, plan=proxy_plan,
            schedule_sha256=canonical_sha256({"rungs": list(RUNG_BOUNDARIES), "chunk": 100}),
            policy_binding=policy_binding,
            environment_training_state=states[boundary],
            rng_algorithm=type(age_rng.bit_generator).__name__,
        )
        result[boundary] = {
            "schema": f"{SCHEMA}-boundary-state",
            "arm": arm,
            "episode_index": boundary,
            "source_stage_c_boundary": donor_payload,
            "source_builder": {"path": str(BOUNDARY_DONOR.resolve()), "sha256": file_sha256(BOUNDARY_DONOR)},
        }
        result[boundary]["boundary_state_sha256"] = canonical_sha256(result[boundary])
    return result


def publish_chunk(
    *, arm: str, start: int, rows: Sequence[Mapping[str, object]], output: Path,
    start_boundary: Mapping[str, object], end_boundary: Mapping[str, object],
    authority_sha256: str,
    authority_path: str | None = None,
    runtime: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Publish one completed 100-episode chunk from an episode executor."""

    if arm not in ARMS or type(start) is not int or start < 0 or start % 100 or len(rows) != 100:
        raise ConfirmatoryError("formal chunks are exactly 100 episodes and 100-aligned")
    if output.exists() or output.is_symlink():
        raise ConfirmatoryError("chunk output must be absent")
    ordered = [validate_episode(row, arm=arm) for row in rows]
    if [row["episode_index"] for row in ordered] != list(range(start + 1, start + 101)):
        raise ConfirmatoryError("chunk rows do not match the declared range")
    if start_boundary.get("episode_index") != start or end_boundary.get("episode_index") != start + 100:
        raise ConfirmatoryError("chunk boundary states do not bind its range")
    if start_boundary.get("arm") != arm or end_boundary.get("arm") != arm:
        raise ConfirmatoryError("chunk boundary arm drifted")
    output.mkdir(parents=True, exist_ok=False)
    write_once(output / "boundary-start.json", start_boundary)
    write_once(output / "boundary-end.json", end_boundary)
    for row in ordered:
        write_once(output / "episodes" / f"episode-{row['episode_index']:06d}.json", row)
    payload = {
        "schema": f"{SCHEMA}-chunk-receipt", "status": "COMPLETE", "arm": arm,
        "chunk_id": f"{arm}-{start:06d}-{start + 100:06d}",
        "start_boundary": start, "end_boundary": start + 100,
        "start_boundary_state_sha256": start_boundary.get("boundary_state_sha256"),
        "end_boundary_state_sha256": end_boundary.get("boundary_state_sha256"),
        "ordered_episode_digest": canonical_sha256(ordered),
        "authority_sha256": authority_sha256,
        "authority": None if authority_path is None else {"path": authority_path, "sha256": authority_sha256},
        "runtime": None if runtime is None else dict(runtime),
    }
    write_once(output / "chunk-receipt.json", payload)
    return payload


def _make_environment(archive: Any) -> Any:
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.runtime.trainer_env import TrainerEnvironment

    driver = ScenarioDriver(
        archive,
        ScenarioConfig(mobility=MobilityConfig(num_users=USERS), steps_per_episode=STEPS),
    )
    split = BlockAlternatingSplit.for_archive(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, TRAIN)
    return TrainerEnvironment(StepEnvironment(driver), sampler)


def execute_formal_chunk(
    *, arm: str, start: int, end: int, output: Path,
    authority: Mapping[str, object],
) -> dict[str, object]:
    """Execute one authority-bound 100-episode arm chunk."""

    if arm not in ARMS or end != start + 100 or start < 0 or start % 100:
        raise ConfirmatoryError("formal execution requires one 100-aligned 100-episode chunk")
    release = authority.get("release")
    if not isinstance(release, Mapping) or release.get("chunk_start") != start or release.get("chunk_end") != end:
        raise ConfirmatoryError("formal execution is not bound to this released chunk")
    formal_root = Path(str(authority.get("output_root", ""))).resolve()
    if not output.resolve().is_relative_to(formal_root):
        raise ConfirmatoryError("chunk output escapes the authority-bound output root")
    runtime = pin_runtime()
    plan_record = authority.get("world_plan")
    coordinator = authority.get("coordinator")
    stage_a = authority.get("stage_a_full2_export")
    physical = authority.get("physical_inputs")
    if not all(isinstance(record, Mapping) for record in (plan_record, coordinator, stage_a, physical)):
        raise ConfirmatoryError("launch authority lacks execution inputs")
    plan = world_plan.read_world_plan(Path(str(plan_record["path"])))
    if end > 3000:
        raise ConfirmatoryError("this authority never permits execution above episode 3000")
    frozen = load_full2_export(stage_a["path"], str(stage_a["sha256"]))
    configuration = str(coordinator.get("configuration"))
    policy = C3SFull2PolicyAdapter(
        frozen_full2=frozen, coordinator_enabled=arm == "FULL2+C3-S",
        configuration=configuration, decision_offset=start * STEPS,
    )
    binding = policy.binding()
    binding_sha = canonical_sha256(binding)
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.env.tle import TleArchive
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    archive = TleArchive(Path(str(physical["tle_root"])))
    boundaries = boundary_table(
        plan=plan, arm=arm, policy_binding=binding,
        boundaries=(0, start, end) if start else (0, end),
        rng_factory=_evaluation_rngs,
    )
    start_state = boundaries[start]["source_stage_c_boundary"]["environment_training_state"]
    state: Mapping[str, object] | None = None if start == 0 else start_state
    episode_adapter = FixedPolicyEpisodeAdapter(policy)
    rows: list[dict[str, object]] = []
    for index in range(start + 1, end + 1):
        world = plan["worlds"][index - 1]
        environment = _make_environment(archive)
        environment.environment._fading_field = KeyedFadingField.from_components(
            world_plan.FIELD_COMPONENT, int(world["world_seed"])
        )
        if state is not None:
            environment.load_training_state_dict(state)
        rngs = tuple(_evaluation_rngs(int(world["world_seed"])))
        execution = episode_adapter.run_episode(
            environment, environment_rng=rngs[0], mobility_rng=rngs[1],
        )
        state = environment.training_state_dict()
        rows.append({
            "schema": f"{SCHEMA}-episode-receipt", "status": "COMPLETE",
            "arm": arm, "episode_index": index, "world_id": world["world_id"],
            "world_domain": world["domain"],
            "world_seed": world["world_seed"], "field_root_digest": world["field_root_digest"],
            "initial_state_sha256": execution.initial_state_sha256,
            "policy_binding_sha256": binding_sha,
            "total_bits": execution.total_bits, "total_energy_j": execution.total_energy_j,
            "served_user_steps": execution.served_user_steps,
            "service_opportunities": execution.service_opportunities,
            "action_trace_sha256": execution.action_trace_sha256,
            "plan_sha256": plan["plan_sha256"],
            "decision_records": list(execution.decision_records),
            "decision_records_sha256": canonical_sha256(list(execution.decision_records)),
        })
    payload = publish_chunk(
        arm=arm, start=start, rows=rows, output=output,
        start_boundary=boundaries[start], end_boundary=boundaries[end],
        authority_sha256=str(authority["authority_sha256"]),
        authority_path=str(authority.get("authority_path")),
        runtime=runtime,
    )
    return payload


def _execute_series(
    *, arm: str, worlds: Sequence[Mapping[str, object]], plan_sha256: str,
    authority: Mapping[str, object], initial_state: Mapping[str, object] | None,
) -> tuple[list[dict[str, object]], Mapping[str, object] | None]:
    coordinator = authority["coordinator"]
    stage_a = authority["stage_a_full2_export"]
    physical = authority["physical_inputs"]
    if not isinstance(coordinator, Mapping) or not isinstance(stage_a, Mapping) or not isinstance(physical, Mapping):
        raise ConfirmatoryError("authority execution bindings are malformed")
    frozen = load_full2_export(stage_a["path"], str(stage_a["sha256"]))
    policy = C3SFull2PolicyAdapter(
        frozen_full2=frozen, coordinator_enabled=arm == "FULL2+C3-S",
        configuration=str(coordinator["configuration"]),
        decision_offset=3000 * STEPS,
    )
    binding_sha = canonical_sha256(policy.binding())
    episode_adapter = FixedPolicyEpisodeAdapter(policy)
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.env.tle import TleArchive
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    archive = TleArchive(Path(str(physical["tle_root"])))
    state = initial_state
    rows: list[dict[str, object]] = []
    for world in worlds:
        index = int(world["episode_index"])
        environment = _make_environment(archive)
        environment.environment._fading_field = KeyedFadingField.from_components(
            world_plan.FIELD_COMPONENT, int(world["world_seed"])
        )
        if state is not None:
            environment.load_training_state_dict(state)
        rngs = tuple(_evaluation_rngs(int(world["world_seed"])))
        execution = episode_adapter.run_episode(
            environment, environment_rng=rngs[0], mobility_rng=rngs[1],
        )
        state = environment.training_state_dict()
        rows.append({
            "schema": f"{SCHEMA}-episode-receipt", "status": "COMPLETE",
            "arm": arm, "episode_index": index, "world_id": world["world_id"],
            "world_domain": world["domain"], "world_seed": world["world_seed"],
            "field_root_digest": world["field_root_digest"],
            "initial_state_sha256": execution.initial_state_sha256,
            "policy_binding_sha256": binding_sha,
            "total_bits": execution.total_bits, "total_energy_j": execution.total_energy_j,
            "served_user_steps": execution.served_user_steps,
            "service_opportunities": execution.service_opportunities,
            "action_trace_sha256": execution.action_trace_sha256,
            "plan_sha256": plan_sha256,
            "decision_records": list(execution.decision_records),
            "decision_records_sha256": canonical_sha256(list(execution.decision_records)),
        })
    return rows, state


def execute_acceptance(
    *, arm: str, output: Path, authority: Mapping[str, object], preflight_sha256: str,
) -> dict[str, object]:
    """Run the mandatory independent-domain sequential-200/2x100 check."""

    if arm not in ARMS:
        raise ConfirmatoryError("acceptance arm is invalid")
    pin_runtime()
    worlds = []
    from mcrl.env.keyed_fading import KeyedFadingField
    for index in range(1, 201):
        domain = f"C3S_CONFIRM_ACCEPT/world/{index}"
        seed = world_plan.derive_seed(domain)
        worlds.append({
            "episode_index": index, "world_id": f"c3s-confirm-accept-world-{index:06d}",
            "domain": domain, "world_seed": seed,
            "field_root_digest": KeyedFadingField.from_components(world_plan.FIELD_COMPONENT, seed).root_digest,
        })
    plan_sha = canonical_sha256({
        "domain": "C3S_CONFIRM_ACCEPT/world/{i}", "worlds": worlds,
        "arms": list(ARMS), "steps": STEPS,
    })
    direct, _direct_end = _execute_series(
        arm=arm, worlds=worlds, plan_sha256=plan_sha,
        authority=authority, initial_state=None,
    )
    first, first_state = _execute_series(
        arm=arm, worlds=worlds[:100], plan_sha256=plan_sha,
        authority=authority, initial_state=None,
    )
    second, _second_state = _execute_series(
        arm=arm, worlds=worlds[100:], plan_sha256=plan_sha,
        authority=authority, initial_state=first_state,
    )
    # Boundary tables are produced independently for the two paths and then
    # compared through the imported stage-C semantics.
    from mcrl.runtime.training_pipeline import _evaluation_rngs
    binding = {"arm": arm, "acceptance_plan_sha256": plan_sha}
    accept_plan = {"worlds": worlds, "plan_sha256": plan_sha}
    direct_boundaries = boundary_table(
        plan=accept_plan, arm=arm, policy_binding=binding,
        boundaries=(0, 100, 200), rng_factory=_evaluation_rngs,
    )
    chunk_boundaries = boundary_table(
        plan=accept_plan, arm=arm, policy_binding=binding,
        boundaries=(0, 100, 200), rng_factory=_evaluation_rngs,
    )
    return build_acceptance_receipt(
        arm=arm, direct_rows=direct, first_chunk_rows=first,
        second_chunk_rows=second, direct_boundary_states=direct_boundaries,
        chunk_boundary_states=chunk_boundaries, preflight_sha256=preflight_sha256,
        output=output,
    )


def build_acceptance_receipt(
    *, arm: str, direct_rows: Sequence[Mapping[str, object]],
    first_chunk_rows: Sequence[Mapping[str, object]],
    second_chunk_rows: Sequence[Mapping[str, object]],
    direct_boundary_states: Mapping[int, object],
    chunk_boundary_states: Mapping[int, object],
    preflight_sha256: str, output: Path,
) -> dict[str, object]:
    """Require direct 200 versus 2x100 bitwise equivalence for one arm."""

    if arm not in ARMS or len(direct_rows) != 200 or len(first_chunk_rows) != 100 or len(second_chunk_rows) != 100:
        raise ConfirmatoryError("acceptance requires sequential 200 versus exactly 2x100")
    chunked = [*first_chunk_rows, *second_chunk_rows]
    for index, row in enumerate(direct_rows, 1):
        parsed = validate_episode(row, arm=arm)
        if parsed["world_domain"] != f"C3S_CONFIRM_ACCEPT/world/{index}":
            raise ConfirmatoryError("acceptance receipt uses a non-acceptance world")
    for index, row in enumerate(chunked, 1):
        parsed = validate_episode(row, arm=arm)
        if parsed["world_domain"] != f"C3S_CONFIRM_ACCEPT/world/{index}":
            raise ConfirmatoryError("chunked acceptance uses a non-acceptance world")
    acceptance_comparison(list(direct_rows), chunked, artifact="receipts")
    for boundary in (0, 100, 200):
        if boundary not in direct_boundary_states or boundary not in chunk_boundary_states:
            raise ConfirmatoryError("acceptance lacks a required boundary state")
        acceptance_comparison(
            direct_boundary_states[boundary], chunk_boundary_states[boundary],
            artifact=f"resume_states[{boundary}]",
        )
    for boundary in (100, 200):
        acceptance_comparison(
            pool_episodes(direct_rows[:boundary], arm=arm),
            pool_episodes(chunked[:boundary], arm=arm),
            artifact=f"rungs[{boundary}]",
        )
    direct_pools = {
        str(boundary): pool_episodes(direct_rows[:boundary], arm=arm)
        for boundary in (100, 200)
    }
    chunk_pools = {
        str(boundary): pool_episodes(chunked[:boundary], arm=arm)
        for boundary in (100, 200)
    }
    evidence = {
        "sequential": {
            "episodes": list(direct_rows),
            "resume_states": {str(key): value for key, value in direct_boundary_states.items()},
            "checkpoints": direct_pools, "rungs": direct_pools,
        },
        "two_by_100": {
            "episodes": chunked,
            "resume_states": {str(key): value for key, value in chunk_boundary_states.items()},
            "checkpoints": chunk_pools, "rungs": chunk_pools,
        },
    }
    payload = {
        "schema": f"{SCHEMA}-chunk-equivalence",
        "status": "PASS_BITWISE_CHUNK_EQUIVALENCE",
        "arm": arm, "episodes": 200, "chunks": [[1, 100], [101, 200]],
        "preflight_sha256": preflight_sha256,
        "episode_digest": canonical_sha256(chunked),
        "excluded_fields": list(_equivalence_exclusions()),
        "comparison_source": {"path": str(ACCEPTANCE_DONOR.resolve()), "sha256": file_sha256(ACCEPTANCE_DONOR)},
        "merged_artifacts_compared": ["receipts", "checkpoints", "rungs", "resume_states"],
        "evidence": evidence,
    }
    write_once(output, payload)
    return payload


def authenticate_launch_authority(
    path: Path, *, mode: str, launch_arguments: Sequence[str],
) -> dict[str, Any]:
    binding = validate_sealed_file(path)
    payload = read_json(path, field="launch authority")
    if (
        payload.get("schema") != f"{SCHEMA}-launch-authority"
        or payload.get("status") != "FROZEN_LAUNCH_AUTHORITY"
        or payload.get("mode") != mode
        or payload.get("authority_path") != str(path.resolve())
        or payload.get("launch_arguments") != list(launch_arguments)
    ):
        raise ConfirmatoryError("launch authority does not bind this exact invocation")
    preflight = payload.get("preflight")
    if not isinstance(preflight, Mapping):
        raise ConfirmatoryError("launch authority lacks preflight binding")
    validate_sealed_file(str(preflight.get("path", "")), str(preflight.get("sha256", "")))
    manifest = read_json(str(preflight["path"]), field="bound preflight")
    for record in manifest.get("code_files", []):
        if not isinstance(record, Mapping) or file_sha256(str(record.get("path", ""))) != record.get("sha256"):
            raise ConfirmatoryError("preflight code bytes drifted")
    for record in (
        payload.get("plan_contract"), payload.get("stage_a_full2_export"),
        payload.get("coordinator", {}).get("code"), payload.get("coordinator", {}).get("config"),
        payload.get("coordinator", {}).get("variant_hooks"),
        payload.get("world_plan"), payload.get("physical_inputs", {}).get("prereg"),
        payload.get("physical_inputs", {}).get("tle_manifest"),
    ):
        if not isinstance(record, Mapping) or file_sha256(str(record.get("path", ""))) != record.get("sha256"):
            raise ConfirmatoryError("launch input bytes drifted")
    coordinator = payload.get("coordinator")
    if not isinstance(coordinator, Mapping) or coordinator.get("configuration") not in COORDINATOR_CONFIGURATIONS:
        raise ConfirmatoryError("launch authority lacks the resolved frozen configuration")
    if mode == "formal":
        release = payload.get("release")
        if not isinstance(release, Mapping) or release.get("rung_boundary") not in RUNG_BOUNDARIES:
            raise ConfirmatoryError("formal launch authority lacks a rung release")
        verify_acceptance_receipts(
            [Path(str(row["path"])) for row in payload.get("acceptance_receipts", [])],
            preflight_sha256=str(preflight["sha256"]),
        )
    return {**payload, "authority_sha256": binding["sha256"]}


def _read_chunk(root: Path, *, arm: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    receipt = read_json(root / "chunk-receipt.json", field="chunk receipt")
    start, end = receipt.get("start_boundary"), receipt.get("end_boundary")
    if (
        receipt.get("schema") != f"{SCHEMA}-chunk-receipt"
        or receipt.get("status") != "COMPLETE"
        or receipt.get("arm") != arm
        or type(start) is not int or type(end) is not int
        or start < 0 or end != start + 100
        or receipt.get("chunk_id") != f"{arm}-{start:06d}-{end:06d}"
    ):
        raise ConfirmatoryError("chunk receipt identity drifted")
    boundaries: dict[str, dict[str, Any]] = {}
    for name, expected_episode, receipt_field in (
        ("boundary-start.json", start, "start_boundary_state_sha256"),
        ("boundary-end.json", end, "end_boundary_state_sha256"),
    ):
        value = read_json(root / name, field=name)
        body = dict(value)
        claimed = body.pop("boundary_state_sha256", None)
        if (
            value.get("schema") != f"{SCHEMA}-boundary-state"
            or value.get("arm") != arm
            or value.get("episode_index") != expected_episode
            or claimed != canonical_sha256(body)
            or receipt.get(receipt_field) != claimed
        ):
            raise ConfirmatoryError("chunk boundary-state provenance drifted")
        boundaries[name] = value
    authority_sha = receipt.get("authority_sha256")
    if not isinstance(authority_sha, str) or len(authority_sha) != 64:
        raise ConfirmatoryError("chunk authority digest is absent")
    authority = receipt.get("authority")
    if authority is not None:
        if not isinstance(authority, Mapping) or authority.get("sha256") != authority_sha:
            raise ConfirmatoryError("chunk authority binding is malformed")
        validate_sealed_file(str(authority.get("path", "")), str(authority_sha))
    paths = [root / "episodes" / f"episode-{index:06d}.json" for index in range(start + 1, end + 1)]
    if any(not path.is_file() for path in paths):
        raise ConfirmatoryIncomplete("chunk episode coverage is incomplete")
    rows = [validate_episode(read_json(path, field="chunk episode"), arm=arm) for path in paths]
    if canonical_sha256(rows) != receipt.get("ordered_episode_digest"):
        raise ConfirmatoryError("chunk ordered episode digest drifted")
    receipt["_boundary_start"] = boundaries["boundary-start.json"]
    receipt["_boundary_end"] = boundaries["boundary-end.json"]
    return receipt, rows


def merge_arm_chunks(arm: str, chunk_roots: Sequence[Path], output: Path) -> dict[str, object]:
    if arm not in ARMS:
        raise ConfirmatoryError("unknown arm")
    if output.exists() or output.is_symlink():
        raise ConfirmatoryError("arm merge output must be absent")
    chunks = [_read_chunk(Path(root), arm=arm) for root in chunk_roots]
    chunks.sort(key=lambda item: int(item[0]["start_boundary"]))
    cursor = 0
    rows: list[dict[str, Any]] = []
    plan_digests: set[str] = set()
    policy_digests: set[str] = set()
    authority_digests: set[str] = set()
    previous_end_digest: str | None = None
    for receipt, block in chunks:
        if receipt["start_boundary"] != cursor:
            raise ConfirmatoryIncomplete("chunks are not one contiguous prefix")
        cursor = int(receipt["end_boundary"])
        if previous_end_digest is not None and receipt["start_boundary_state_sha256"] != previous_end_digest:
            raise ConfirmatoryError("adjacent chunks disagree at their boundary state")
        previous_end_digest = str(receipt["end_boundary_state_sha256"])
        rows.extend(block)
        plan_digests.update(str(row["plan_sha256"]) for row in block)
        policy_digests.update(str(row["policy_binding_sha256"]) for row in block)
        authority_digests.add(str(receipt["authority_sha256"]))
    if cursor not in RUNG_BOUNDARIES or len(plan_digests) != 1 or len(policy_digests) != 1 or not authority_digests:
        raise ConfirmatoryError("arm merge boundary or provenance drifted")
    output.mkdir(parents=True, exist_ok=False)
    for row in rows:
        write_once(output / "episodes" / f"episode-{row['episode_index']:06d}.json", row)
    for boundary in range(100, cursor + 1, 100):
        pooled = pool_episodes(rows[:boundary], arm=arm)
        checkpoint = {
            "schema": f"{SCHEMA}-arm-checkpoint", "status": "COMPLETE",
            "arm": arm, "completed_episode": boundary,
            "plan_sha256": next(iter(plan_digests)),
            "policy_binding_sha256": next(iter(policy_digests)),
            "pooled": pooled, "scientific_disposition_emitted": False,
        }
        write_once(output / "checkpoints" / f"checkpoint-{boundary:06d}.json", checkpoint)
        if boundary in RUNG_BOUNDARIES:
            write_once(output / "rungs" / f"rung-{boundary:06d}.json", {
                **checkpoint, "schema": f"{SCHEMA}-arm-rung",
            })
    payload = {
        "schema": f"{SCHEMA}-arm-merge", "status": "COMPLETE_ARM_MERGE",
        "arm": arm, "arm_order": list(ARMS), "completed_episode": cursor,
        "plan_sha256": next(iter(plan_digests)),
        "policy_binding_sha256": next(iter(policy_digests)),
        "chunk_authority_sha256s": sorted(authority_digests),
        "ordered_episode_digest": canonical_sha256(rows),
        "pooled": pool_episodes(rows, arm=arm),
        "latency": latency_summary(rows, arm=arm),
        "eta_sensitivity": eta_sensitivity_summary(rows, arm=arm),
        "physical_events": physical_event_summary(rows, arm=arm),
        "chunk_receipts": [
            {"path": str((Path(root) / "chunk-receipt.json").resolve()), "sha256": file_sha256(Path(root) / "chunk-receipt.json")}
            for root in chunk_roots
        ],
        "execution_conditions": [receipt.get("runtime") for receipt, _block in chunks],
        "scientific_disposition_emitted": False,
    }
    write_once(output / "arm-merge.json", payload)
    return payload


def _read_arm_merge(root: Path, arm: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    merge = read_json(root / "arm-merge.json", field=f"{arm} arm merge")
    completed = merge.get("completed_episode")
    if merge.get("status") != "COMPLETE_ARM_MERGE" or merge.get("arm") != arm or completed not in RUNG_BOUNDARIES:
        raise ConfirmatoryError(f"{arm} merge identity drifted")
    rows = [
        validate_episode(read_json(root / "episodes" / f"episode-{index:06d}.json"), arm=arm)
        for index in range(1, int(completed) + 1)
    ]
    if canonical_sha256(rows) != merge.get("ordered_episode_digest") or pool_episodes(rows, arm=arm) != merge.get("pooled"):
        raise ConfirmatoryError(f"{arm} merge contents drifted")
    return merge, rows


def merge_two_arms(arm_roots: Mapping[str, Path], output: Path) -> dict[str, object]:
    if tuple(arm_roots) != ARMS:
        raise ConfirmatoryError("two-arm merge requires frozen arm order")
    if output.exists() or output.is_symlink():
        raise ConfirmatoryError("two-arm merge output must be absent")
    loaded = {arm: _read_arm_merge(Path(arm_roots[arm]), arm) for arm in ARMS}
    completed = {int(loaded[arm][0]["completed_episode"]) for arm in ARMS}
    plans = {str(loaded[arm][0]["plan_sha256"]) for arm in ARMS}
    if len(completed) != 1 or len(plans) != 1:
        raise ConfirmatoryError("two arms disagree on boundary or plan")
    boundary = next(iter(completed))
    for index in range(boundary):
        base = loaded["FULL2"][1][index]
        c3s = loaded["FULL2+C3-S"][1][index]
        for name in ("episode_index", "world_id", "world_domain", "world_seed", "field_root_digest", "initial_state_sha256", "plan_sha256"):
            if base[name] != c3s[name]:
                raise ConfirmatoryError(f"matched episode differs at {name} for episode {index + 1}")
    output.mkdir(parents=True, exist_ok=False)
    for checkpoint_boundary in range(100, boundary + 1, 100):
        pooled = {
            arm: pool_episodes(loaded[arm][1][:checkpoint_boundary], arm=arm)
            for arm in ARMS
        }
        checkpoint = {
            "schema": f"{SCHEMA}-checkpoint", "status": "COMPLETE",
            "completed_episode": checkpoint_boundary, "arms": list(ARMS),
            "plan_sha256": next(iter(plans)), "pooled_by_arm": pooled,
            "scientific_disposition_emitted": False,
        }
        write_once(output / "checkpoints" / f"checkpoint-{checkpoint_boundary:06d}.json", checkpoint)
        if checkpoint_boundary in RUNG_BOUNDARIES:
            write_once(output / "rungs" / f"rung-{checkpoint_boundary:06d}.json", {
                **checkpoint, "schema": f"{SCHEMA}-rung",
            })
    pooled_final = {arm: loaded[arm][0]["pooled"] for arm in ARMS}
    disposition = adjudicate(pooled_final, completed_episodes=boundary, independently_verified=True)
    result: dict[str, object] = {
        "schema": f"{SCHEMA}-two-arm-merge", "status": "COMPLETE",
        "completed_episode": boundary, "arms": list(ARMS),
        "plan_sha256": next(iter(plans)), "pooled_by_arm": pooled_final,
        "claim_ceiling": CLAIM_CEILING,
        "latency_by_arm": {arm: loaded[arm][0]["latency"] for arm in ARMS},
        "eta_sensitivity": loaded["FULL2+C3-S"][0]["eta_sensitivity"],
        "independently_verified_matched_coverage": True,
        "arm_merge_provenance": {
            arm: {"path": str((Path(arm_roots[arm]) / "arm-merge.json").resolve()), "sha256": file_sha256(Path(arm_roots[arm]) / "arm-merge.json")}
            for arm in ARMS
        },
        **disposition,
    }
    write_once(output / "merge-receipt.json", result)
    if boundary == TERMINAL_BOUNDARY or disposition.get("overall_token") == FALSIFIED:
        write_once(output / "result.json", {
            **result, "schema": f"{SCHEMA}-scientific-result", "terminal_boundary": 3000,
        })
    return result


def acceptance_comparison(
    direct: object, chunked: object, *, artifact: str,
) -> None:
    """Use the stage-C comparison implementation and exclusion list verbatim."""

    if tuple(_stagec_acceptance.common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS) != tuple(
        _stagec_common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS
    ):
        raise ConfirmatoryError("stage-C equivalence exclusion list import drifted")
    _stagec_acceptance._assert_equivalent(direct, chunked, artifact=artifact)


def verify_acceptance_receipts(paths: Sequence[Path], *, preflight_sha256: str) -> list[dict[str, object]]:
    if len(paths) != 2:
        raise ConfirmatoryError("formal launch requires two arm acceptance receipts")
    records = []
    for arm, path in zip(ARMS, paths, strict=True):
        sealed = validate_sealed_file(path)
        payload = read_json(path, field=f"{arm} acceptance")
        if (
            payload.get("schema") != f"{SCHEMA}-chunk-equivalence"
            or payload.get("status") != "PASS_BITWISE_CHUNK_EQUIVALENCE"
            or payload.get("arm") != arm
            or payload.get("episodes") != 200
            or payload.get("chunks") != [[1, 100], [101, 200]]
            or payload.get("preflight_sha256") != preflight_sha256
            or payload.get("excluded_fields") != list(_equivalence_exclusions())
        ):
            raise ConfirmatoryError(f"{arm} acceptance receipt drifted")
        evidence = payload.get("evidence")
        if not isinstance(evidence, Mapping):
            raise ConfirmatoryError(f"{arm} acceptance evidence is absent")
        direct = evidence.get("sequential")
        chunked = evidence.get("two_by_100")
        if not isinstance(direct, Mapping) or not isinstance(chunked, Mapping):
            raise ConfirmatoryError(f"{arm} acceptance paths are malformed")
        for artifact in ("episodes", "resume_states", "checkpoints", "rungs"):
            acceptance_comparison(
                direct.get(artifact), chunked.get(artifact),
                artifact=f"{arm}.{artifact}",
            )
        records.append(sealed)
    return records


def _equivalence_exclusions() -> tuple[str, ...]:
    return tuple(_stagec_common.CHUNK_EQUIVALENCE_PROVENANCE_ONLY_FIELDS)


def _receipt_mean(receipt: Mapping[str, object], arm: str) -> float:
    timing = receipt.get("per_arm_decision_wall_timing")
    row = timing.get(arm) if isinstance(timing, Mapping) else None
    if isinstance(row, Mapping) and row.get("mean_hex") is not None:
        return _float(row["mean_hex"], field=f"{arm} complete timing", positive=True)
    raise ConfirmatoryError(f"timing receipt lacks the complete-decision schema for {arm}")


def estimate(
    configuration: str, *, episodes: int = 3000,
    screen_timing: Path | None = None, matrix_timing: Path | None = None,
) -> dict[str, object]:
    configuration = configuration.upper()
    if configuration not in COORDINATOR_CONFIGURATIONS or type(episodes) is not int or episodes < 1:
        raise ConfirmatoryError("estimate requires a frozen configuration id and positive episodes")
    if screen_timing is None:
        configured = os.environ.get("MCRL_C3S_SCREEN_TIMING_RECEIPT")
        screen_timing = Path(configured) if configured else SCREEN_DIR / "runs/c3s-20260908-r1/terminal/terminal-receipt.json"
    screen = read_json(screen_timing, field="v1 complete timing receipt")
    base_tau = _receipt_mean(screen, "BASE")
    basis = {"v1": {"path": str(screen_timing.resolve()), "sha256": file_sha256(screen_timing)}}
    if configuration in ("LITE", "FULL"):
        coordinator_tau = _receipt_mean(screen, configuration)
    else:
        if matrix_timing is None:
            configured_matrix = os.environ.get("MCRL_C3S_MATRIX_TIMING_RECEIPT")
            matrix_timing = Path(configured_matrix) if configured_matrix else None
        if matrix_timing is None:
            raise ConfirmatoryError("variant-specific estimate requires --matrix-timing")
        matrix = read_json(matrix_timing, field="matrix complete timing receipt")
        coordinator_tau = _matrix_mean_total_latency(matrix, configuration)
        basis["matrix"] = {"path": str(matrix_timing.resolve()), "sha256": file_sha256(matrix_timing)}
    coordinator_hours = episodes * STEPS * coordinator_tau / 3600.0
    control_hours = episodes * STEPS * base_tau / 3600.0
    main_hours = coordinator_hours + control_hours
    acceptance_coordinator_hours = 400 * STEPS * coordinator_tau / 3600.0
    acceptance_control_hours = 400 * STEPS * base_tau / 3600.0
    acceptance_hours = acceptance_coordinator_hours + acceptance_control_hours
    return {
        "schema": f"{SCHEMA}-estimate", "configuration": configuration,
        "episodes_per_arm": episodes, "arm_episodes": episodes * 2,
        "decisions_per_episode": STEPS, "opportunities_per_episode": USERS * STEPS,
        "complete_mean_seconds_per_decision": {"FULL2": base_tau, "FULL2+C3-S": coordinator_tau},
        "coordinator_only_worker_hours": coordinator_hours,
        "control_worker_hours": control_hours, "main_panel_worker_hours": main_hours,
        "acceptance_coordinator_worker_hours": acceptance_coordinator_hours,
        "acceptance_control_worker_hours": acceptance_control_hours,
        "acceptance_worker_hours": acceptance_hours,
        "total_worker_hours": main_hours + acceptance_hours,
        "formula": "main=N*30*(tau_FULL2+tau_c)/3600; acceptance=400*30*(tau_FULL2+tau_c)/3600 worker-hours",
        "basis": basis,
    }


def dry_run(configuration: str) -> str:
    configuration = configuration.upper()
    if configuration not in COORDINATOR_CONFIGURATIONS:
        raise ConfirmatoryError("dry-run configuration is not frozen")
    return (
        f"C3S_CONFIRM_DRY_RUN configuration={configuration} arms=FULL2,FULL2+C3-S "
        "chunks=100 rungs=100,500,1500,3000 terminal=3000 execution=NOT_STARTED"
    )


def _subprocess_replay(code_path: Path, record_path: Path) -> dict[str, object]:
    completed = subprocess.run(
        [str(CANONICAL_INTERPRETER), str(code_path), "--replay-archived-decision", str(record_path)],
        check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise ConfirmatoryError(f"replay code failed for {record_path}: {completed.stderr.strip()}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ConfirmatoryError("replay code did not emit one JSON decision") from error
    if not isinstance(payload, dict):
        raise ConfirmatoryError("replay result is not an object")
    return payload


def verify_equivalence(
    old: Path, new: Path, record_paths: Sequence[Path], *, reviewer: str,
    replay: Callable[[Path, Path], Mapping[str, object]] = _subprocess_replay,
) -> dict[str, object]:
    """Replay fixed archives through OLD/NEW and build an append-only receipt body."""

    if not reviewer.strip() or not record_paths:
        raise ConfirmatoryError("equivalence verification requires a reviewer and archived decisions")
    comparison_fields = (
        "committed_actions", "committed_profile_id", "tie_key", "policy_state_after",
        "information_access_sha256", "rng_before_sha256", "rng_after_sha256",
    )
    comparisons = []
    for path in record_paths:
        left, right = dict(replay(old, path)), dict(replay(new, path))
        missing = [name for name in comparison_fields if name not in left or name not in right]
        if missing:
            raise ConfirmatoryError(f"equivalence replay lacks fields: {','.join(missing)}")
        if any(left[name] != right[name] for name in comparison_fields):
            raise ConfirmatoryError(f"semantic equivalence failed for archive {path}")
        comparisons.append({
            "archive": {"path": str(path.resolve()), "sha256": file_sha256(path)},
            "comparison_sha256": canonical_sha256({name: left[name] for name in comparison_fields}),
        })
    return {
        "schema": f"{SCHEMA}-engineering-equivalence-receipt-v1",
        "status": "PASS_BIT_IDENTICAL_SEMANTIC_EQUIVALENCE",
        "old_code": {"path": str(old.resolve()), "sha256": file_sha256(old)},
        "new_code": {"path": str(new.resolve()), "sha256": file_sha256(new)},
        "decision_archives": comparisons, "decisions_replayed": len(comparisons),
        "comparison_fields": list(comparison_fields),
        "unchanged_information_access": True, "unchanged_rng_effects": True,
        "reviewer": reviewer.strip(), "matrix_winner_reranked": False,
    }


def verify_equivalence_receipt(path: Path, *, old_sha256: str, new_sha256: str) -> dict[str, str]:
    binding = validate_sealed_file(path)
    payload = read_json(path, field="engineering equivalence receipt")
    if (
        payload.get("schema") != f"{SCHEMA}-engineering-equivalence-receipt-v1"
        or payload.get("status") != "PASS_BIT_IDENTICAL_SEMANTIC_EQUIVALENCE"
        or payload.get("old_code", {}).get("sha256") != old_sha256  # type: ignore[union-attr]
        or payload.get("new_code", {}).get("sha256") != new_sha256  # type: ignore[union-attr]
        or payload.get("unchanged_information_access") is not True
        or payload.get("unchanged_rng_effects") is not True
        or payload.get("matrix_winner_reranked") is not False
        or type(payload.get("decisions_replayed")) is not int
        or int(payload["decisions_replayed"]) < 1
        or not isinstance(payload.get("reviewer"), str) or not str(payload["reviewer"]).strip()
    ):
        raise ConfirmatoryError("engineering equivalence receipt is not admissible")
    return binding


def benchmark_uncontended(
    code_path: Path, record_paths: Sequence[Path], *,
    replay: Callable[[Path, Path], Mapping[str, object]] = _subprocess_replay,
) -> dict[str, object]:
    if len(record_paths) != 30:
        raise ConfirmatoryError("uncontended benchmark requires the prospectively fixed 30 decisions")
    if os.environ.get("MCRL_C3S_WORKER_CONCURRENCY") != "0":
        raise ConfirmatoryError("uncontended benchmark requires MCRL_C3S_WORKER_CONCURRENCY=0")
    if not os.environ.get("MCRL_C3S_CACHE_CONDITIONS"):
        raise ConfirmatoryError("uncontended benchmark requires prospectively fixed cache conditions")
    pin_runtime()
    elapsed: list[float] = []
    active: list[float] = []
    archives = []
    for path in record_paths:
        record = read_json(path, field="benchmark decision archive")
        started = time.perf_counter()
        replay(code_path, path)
        wall = time.perf_counter() - started
        elapsed.append(wall)
        if record.get("coordinator_active_step") is True:
            active.append(wall)
        archives.append({"path": str(path.resolve()), "sha256": file_sha256(path)})
    return {
        "schema": f"{SCHEMA}-uncontended-benchmark-v1", "status": "COMPLETE",
        "prospectively_fixed_decisions": 30, "competing_workers": 0,
        "code": {"path": str(code_path.resolve()), "sha256": file_sha256(code_path)},
        "archives": archives, "all_steps": _timing_stats(elapsed),
        "coordinator_active_steps": _timing_stats(active),
        "hardware": {"platform": platform.platform(), "machine": platform.machine(), "logical_cpu_count": os.cpu_count()},
        "threads": {name: os.environ.get(name) for name in THREAD_ENV},
        "cache_conditions": os.environ.get("MCRL_C3S_CACHE_CONDITIONS", "UNRECORDED"),
    }


def _metric_hex(record: Mapping[str, object], *, field: str) -> tuple[float, float, int]:
    value = record.get(field)
    if not isinstance(value, Mapping):
        raise ConfirmatoryError(f"decomposition record lacks {field}")
    return (
        _float(value.get("total_bits_hex"), field=f"{field} bits"),
        _float(value.get("total_energy_j_hex"), field=f"{field} energy", positive=True),
        int(value.get("served", -1)),
    )


def failure_decomposition(
    paired_archives: Sequence[Mapping[str, object]], *, eta_full2: float,
) -> dict[str, object]:
    """Compute astra's I/R identity from isolated archived-state replays."""

    if not paired_archives or not math.isfinite(eta_full2) or eta_full2 <= 0:
        raise ConfirmatoryError("failure decomposition requires a positive matched prefix")
    intervention: list[float] = []
    response: list[float] = []
    service_differences: list[int] = []
    paired_residuals: list[dict[str, object]] = []
    association_trace: list[list[tuple[int, int] | None]] = []
    for pair in paired_archives:
        coordinator, full2 = pair.get("coordinator"), pair.get("full2")
        if not isinstance(coordinator, Mapping) or not isinstance(full2, Mapping):
            raise ConfirmatoryError("decomposition archive lacks paired arm records")
        c_bits, c_energy, c_served = _metric_hex(coordinator, field="realised")
        f_bits, f_energy, f_served = _metric_hex(full2, field="realised")
        replay_bits, replay_energy, replay_served = _metric_hex(pair, field="isolated_full2_replay_realised")
        intervention.append((c_bits - eta_full2 * c_energy) - (replay_bits - eta_full2 * replay_energy))
        response.append((replay_bits - eta_full2 * replay_energy) - (f_bits - eta_full2 * f_energy))
        service_differences.append(c_served - f_served)
        c_nom_b, c_nom_e, c_nom_served = _metric_hex(coordinator, field="selected_nominal")
        b_nom_b, b_nom_e, b_nom_served = _metric_hex(coordinator, field="full2_proposal_nominal")
        eta_ref = float.fromhex("0x1.d94fb72305d6ap+26")
        nominal_score_delta = (c_nom_b - b_nom_b) - eta_ref * (c_nom_e - b_nom_e)
        realised_score_delta = (c_bits - replay_bits) - eta_ref * (c_energy - replay_energy)
        paired_residuals.append({
            "nominal_delta_bits": c_nom_b - b_nom_b, "nominal_delta_energy_j": c_nom_e - b_nom_e,
            "nominal_delta_served": c_nom_served - b_nom_served, "nominal_delta_score": nominal_score_delta,
            "realised_delta_bits": c_bits - replay_bits, "realised_delta_energy_j": c_energy - replay_energy,
            "realised_delta_served": c_served - replay_served, "realised_delta_score": realised_score_delta,
            "realised_minus_nominal_score_residual": realised_score_delta - nominal_score_delta,
        })
        realised_record = coordinator.get("realised")
        associations = realised_record.get("physical_associations") if isinstance(realised_record, Mapping) else None
        if associations is None:
            associations = coordinator.get("committed_physical_associations")
        if not isinstance(associations, list):
            raise ConfirmatoryError("decomposition archive lacks physical associations")
        association_trace.append([None if item is None else (int(item[0]), int(item[1])) for item in associations])
    import variant_policy
    i_value, r_value = math.fsum(intervention), math.fsum(response)
    delta_score = math.fsum(intervention[index] + response[index] for index in range(len(intervention)))
    return {
        "schema": f"{SCHEMA}-failure-decomposition-v1", "status": "COMPLETE_NON_DECISIONAL",
        "eta_full2": eta_full2, "eta_full2_hex": eta_full2.hex(),
        "matched_decisions": len(paired_archives), "I": i_value, "R": r_value,
        "I_plus_R": i_value + r_value, "delta_bits_minus_p_delta_energy": delta_score,
        "identity_residual": (i_value + r_value) - delta_score,
        "nominal_realised_paired_residuals_at_eta_ref": paired_residuals,
        "service_differences": service_differences,
        "association_reversals_within_3_steps": variant_policy.association_reversals(association_trace, window=3),
        "progression_effect": False, "rescue_permitted": False,
    }


def decompose_failure(
    result_path: Path, archive_paths: Sequence[Path], *, replay_code: Path,
    replay: Callable[[Path, Path], Mapping[str, object]] = _subprocess_replay,
) -> dict[str, object]:
    result = read_json(result_path, field="FALSIFIED result")
    if result.get("overall_token") != FALSIFIED or result.get("scientific_disposition_emitted") is not True:
        raise ConfirmatoryError("--decompose requires a valid FALSIFIED result")
    pooled = result.get("pooled_by_arm")
    full2 = pooled.get("FULL2") if isinstance(pooled, Mapping) else None
    if not isinstance(full2, Mapping):
        raise ConfirmatoryError("FALSIFIED result lacks FULL2 prefix totals")
    eta_full2 = _float(full2.get("ee_bits_per_j"), field="FULL2 prefix EE", positive=True)
    archives = []
    for path in archive_paths:
        pair = read_json(path, field="isolated paired decision archive")
        replay_result = replay(replay_code, path)
        realised = replay_result.get("isolated_full2_replay_realised")
        if not isinstance(realised, Mapping):
            raise ConfirmatoryError("isolated replay did not return FULL2 realised metrics")
        pair["isolated_full2_replay_realised"] = dict(realised)
        archives.append(pair)
    payload = failure_decomposition(archives, eta_full2=eta_full2)
    payload["source_result"] = {"path": str(result_path.resolve()), "sha256": file_sha256(result_path)}
    payload["archive_bindings"] = [{"path": str(path.resolve()), "sha256": file_sha256(path)} for path in archive_paths]
    payload["isolated_replay_code"] = {"path": str(replay_code.resolve()), "sha256": file_sha256(replay_code)}
    return payload


def publish_failure(output: Path, error: BaseException, *, scope: str) -> dict[str, object]:
    incomplete = isinstance(error, (ConfirmatoryIncomplete, KeyboardInterrupt, MemoryError)) or (
        isinstance(error, OSError)
        and error.errno in (errno.ENOSPC, errno.EDQUOT, errno.EMFILE, errno.ENFILE)
    )
    status = "INCOMPLETE" if incomplete else "INVALID_RUN"
    payload = {
        "schema": f"{SCHEMA}-failure", "status": status, "scope": scope,
        "error_type": type(error).__name__, "message": str(error),
        "overall_token": None, "scientific_disposition_emitted": False,
    }
    write_once(output / ("INCOMPLETE.json" if incomplete else "INVALID_RUN.json"), payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--estimate", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--accept", action="store_true")
    mode.add_argument("--run-chunk", action="store_true")
    mode.add_argument("--merge-arm", action="store_true")
    mode.add_argument("--merge-two", action="store_true")
    mode.add_argument("--decompose", action="store_true")
    mode.add_argument("--benchmark-uncontended", action="store_true")
    mode.add_argument("--verify-equivalence", nargs=2, type=Path, metavar=("OLD", "NEW"))
    parser.add_argument("--configuration", choices=COORDINATOR_CONFIGURATIONS, default="LITE")
    parser.add_argument("--episodes", type=int, default=3000)
    parser.add_argument("--screen-timing", type=Path)
    parser.add_argument("--matrix-timing", type=Path)
    parser.add_argument("--arm", choices=ARMS)
    parser.add_argument("--chunk-root", type=Path, action="append", default=[])
    parser.add_argument("--arm-root", type=Path, action="append", default=[])
    parser.add_argument("--decision-record", type=Path, action="append", default=[])
    parser.add_argument("--code-path", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--equivalence-reviewer")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--launch-authority", type=Path)
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    launch_arguments = list(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(launch_arguments)
    try:
        if args.estimate:
            print(json.dumps(estimate(args.configuration, episodes=args.episodes, screen_timing=args.screen_timing, matrix_timing=args.matrix_timing), sort_keys=True, separators=(",", ":")))
        elif args.dry_run:
            print(dry_run(args.configuration))
        elif args.verify_equivalence:
            if args.output is None or args.equivalence_reviewer is None:
                raise ConfirmatoryError("--verify-equivalence requires --output and --equivalence-reviewer")
            payload = verify_equivalence(
                args.verify_equivalence[0], args.verify_equivalence[1], args.decision_record,
                reviewer=args.equivalence_reviewer,
            )
            write_once(args.output, payload)
            print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        elif args.benchmark_uncontended:
            if args.output is None or args.code_path is None:
                raise ConfirmatoryError("--benchmark-uncontended requires --code-path and --output")
            payload = benchmark_uncontended(args.code_path, args.decision_record)
            write_once(args.output, payload)
            print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        elif args.decompose:
            if args.output is None or args.result is None or args.code_path is None:
                raise ConfirmatoryError("--decompose requires --result, --code-path, --decision-record, and --output")
            payload = decompose_failure(args.result, args.decision_record, replay_code=args.code_path)
            write_once(args.output, payload)
            print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        elif args.accept:
            if args.arm is None or args.output is None or args.launch_authority is None:
                raise ConfirmatoryError("--accept requires arm/output/launch-authority")
            authority = authenticate_launch_authority(
                args.launch_authority, mode="acceptance", launch_arguments=launch_arguments,
            )
            preflight = authority["preflight"]
            print(json.dumps(execute_acceptance(
                arm=args.arm, output=args.output, authority=authority,
                preflight_sha256=str(preflight["sha256"]),
            ), sort_keys=True, separators=(",", ":")))
        elif args.run_chunk:
            if args.arm is None or args.start is None or args.end is None or args.output is None or args.launch_authority is None:
                raise ConfirmatoryError("--run-chunk requires arm/start/end/output/launch-authority")
            authority = authenticate_launch_authority(
                args.launch_authority, mode="formal", launch_arguments=launch_arguments,
            )
            print(json.dumps(execute_formal_chunk(
                arm=args.arm, start=args.start, end=args.end,
                output=args.output, authority=authority,
            ), sort_keys=True, separators=(",", ":")))
        elif args.merge_arm:
            if args.arm is None or args.output is None:
                raise ConfirmatoryError("--merge-arm requires --arm and --output")
            if args.launch_authority is None:
                raise ConfirmatoryError("formal merge requires --launch-authority")
            authenticate_launch_authority(
                args.launch_authority, mode="formal", launch_arguments=launch_arguments,
            )
            print(json.dumps(merge_arm_chunks(args.arm, args.chunk_root, args.output), sort_keys=True, separators=(",", ":")))
        elif args.merge_two:
            if len(args.arm_root) != 2 or args.output is None:
                raise ConfirmatoryError("--merge-two requires two ordered --arm-root values and --output")
            if args.launch_authority is None:
                raise ConfirmatoryError("formal merge requires --launch-authority")
            authenticate_launch_authority(
                args.launch_authority, mode="formal", launch_arguments=launch_arguments,
            )
            roots = {arm: root for arm, root in zip(ARMS, args.arm_root, strict=True)}
            print(json.dumps(merge_two_arms(roots, args.output), sort_keys=True, separators=(",", ":")))
        else:
            raise ConfirmatoryError("unhandled runner mode")
    except (ConfirmatoryIncomplete, KeyboardInterrupt) as error:
        if args.output is not None:
            try:
                publish_failure(args.output, error, scope="runner")
            except Exception:
                pass
        print(f"INCOMPLETE: {error}", file=sys.stderr)
        return 3
    except Exception as error:
        if args.output is not None and not (args.estimate or args.dry_run or args.verify_equivalence or args.benchmark_uncontended or args.decompose):
            try:
                publish_failure(args.output, error, scope="runner")
            except Exception:
                pass
        print(f"INVALID_RUN: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ARMS", "ARM_UNRESOLVED", "FALSIFIED", "HELD", "RUNG_HELD", "RUNG_BOUNDARIES", "ConfirmatoryError",
    "ConfirmatoryIncomplete", "acceptance_comparison", "adjudicate", "boundary_table",
    "benchmark_uncontended", "build_acceptance_receipt", "decompose_failure", "dry_run", "estimate",
    "failure_decomposition", "merge_arm_chunks",
    "merge_two_arms", "pool_episodes", "publish_chunk",
    "resolve_confirmatory_arm", "validate_sealed_file", "verify_equivalence",
    "verify_equivalence_receipt", "write_once",
]
